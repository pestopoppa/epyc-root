"""AKX-ALL-27 width-invariance dimension record -> measurement ClaimTuples (HIP half of
VB-AKX-ALL-26-CELLS-WIRE).

Source: ``width_dimension.json`` (``epyc.autokernel.width_invariance_dimension.v1``) written by
``scripts/fillers/v11/akx27_driver.py``, which lives beside its ``DECISION.json`` and the two probe run
dirs ``parent/`` (the anchor's AKX-ALL-26 table) and ``keep/`` (the keep's), each holding
``cells.jsonl``.

STRICT READER, not a trusting one: the record's comparison is a derived verdict, so this reader
re-derives it. It loads the two HIP ``cell`` tables itself, folds them with the producer's own
relative comparison, and refuses unless every bucket equals the stored one. It also requires the
route proof in ``DECISION.json`` (``proven``), run headers whose ggml commit matches the build dir,
the same ROCm0 device in both tables, and ``coverage_complete``. Nothing is invented: counts, build
paths, commits and cell ids are copied from those files.

PROJECTION ONLY. ``claim_tuple.grade()`` decides every tuple; no ladder here. Observations carry an
empty ``protocol_id``. The record is OBSERVE-ONLY (``observe_only: true``, ``refuses: false``): it
states a relative width-invariance observation at one footprint, not a gate or a promotion claim.
The CPU half (``akx_all_26_cpu_20261020/cells.jsonl.gz``) has a different cell schema and is NOT
read here (see README).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

ADAPTER_ID = "vidya.adapters.autokernel_width_dimension/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "autokernel-width-dimension"
SCHEMA = "epyc.autokernel.width_invariance_dimension.v1"
MAX_BYTES = 64 << 20
BUCKETS = ("new_failing", "lower_first_fail_k", "higher_first_fail_k", "fixed", "unchanged_fail",
           "unchanged_pass", "indeterminate", "missing_in_keep", "absent_in_anchor")
# (bucket, metric, direction): the regression axis first. Each is one count read off the record.
METRICS = (
    ("new_failing", "width_invariance_new_failing_cells", "lower_better"),
    ("lower_first_fail_k", "width_invariance_lower_first_fail_k_cells", "lower_better"),
    ("higher_first_fail_k", "width_invariance_higher_first_fail_k_cells", "higher_better"),
    ("fixed", "width_invariance_fixed_cells", "higher_better"),
)
_SHA = re.compile(r"[0-9a-f]{64}")
_BUILD = re.compile(r"gpu-\d{8}-([0-9a-f]{7,40})$")


def _read(path: Path) -> bytes:
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    try:
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
    except OSError as exc:
        raise ProjectionError(f"width dimension input unreadable: {path}: {exc}") from exc
    if len(raw) > MAX_BYTES:
        raise ProjectionError(f"width dimension input exceeds bound: {path}")
    return raw


def _json(path: Path) -> Any:
    try:
        return json.loads(_read(path))
    except ValueError as exc:
        raise ProjectionError(f"width dimension input is not JSON: {path}") from exc


def _table(run_dir: Path) -> tuple[dict, dict, str]:
    """HIP ``cell`` records -> ({cell_key: {status, first_fail_k}}, run header, cells sha256).
    Same key and status folding as the producer's ``width_dimension.load_table``."""
    raw = _read(run_dir / "cells.jsonl")
    table: dict[str, dict] = {}
    header: dict | None = None
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except ValueError as exc:
            raise ProjectionError("width dimension cells.jsonl line is not JSON") from exc
        if rec.get("record") == "run":
            ident = lambda h: (h.get("ggml_commit"), h.get("backend_bound"), h.get("device_description"),  # noqa: E731
                               (h.get("env") or {}).get("LD_LIBRARY_PATH"))
            if header is not None and ident(header) != ident(rec):
                raise ProjectionError("width dimension cells.jsonl run headers disagree on build/device")
            header = header or rec
        elif rec.get("record") == "cell":
            status = {"OK": rec.get("verdict"), "UNSUPPORTED": "UNSUPPORTED"}.get(rec.get("status"), "ERR")
            if rec.get("unstable_ks"):
                status = "VOID_AA"
            if rec.get("err_ks"):
                status = "ERR"
            key = "|".join(str(x) for x in (rec.get("backend_bound") or rec.get("backend_row"),
                                            rec["id"], rec.get("sub", 0)))
            if key in table:
                raise ProjectionError(f"width dimension duplicate cell {key}")
            table[key] = {"status": status, "first_fail_k": rec.get("first_fail_k")}
    if not table or header is None:
        raise ProjectionError(f"width dimension {run_dir.name} table has no run header or no cells")
    return table, header, hashlib.sha256(raw).hexdigest()


def _compare(anchor: dict, keep: dict) -> dict:
    """The producer's relative comparison (``width_dimension.compare_tables``), re-implemented."""
    buckets: dict[str, list] = {name: [] for name in BUCKETS}
    for key in sorted(set(anchor) | set(keep)):
        a, k = anchor.get(key), keep.get(key)
        if a is None:
            buckets["absent_in_anchor"].append({"cell": key, "keep": k["status"]})
            continue
        if k is None:
            buckets["missing_in_keep"].append({"cell": key, "anchor": a["status"]})
            continue
        sa, sk = a["status"], k["status"]
        if sa not in ("PASS", "FAIL") or sk not in ("PASS", "FAIL"):
            if sa == sk == "UNSUPPORTED":
                continue
            buckets["indeterminate"].append({"cell": key, "anchor": sa, "keep": sk})
        elif sa == "PASS" and sk == "FAIL":
            buckets["new_failing"].append({"cell": key, "keep_first_fail_k": k["first_fail_k"]})
        elif sa == "FAIL" and sk == "PASS":
            buckets["fixed"].append({"cell": key, "anchor_first_fail_k": a["first_fail_k"]})
        elif sa == "FAIL":
            fa, fk = a["first_fail_k"], k["first_fail_k"]
            if fk < fa:
                buckets["lower_first_fail_k"].append({"cell": key, "anchor": fa, "keep": fk})
            elif fk > fa:
                buckets["higher_first_fail_k"].append({"cell": key, "anchor": fa, "keep": fk})
            else:
                buckets["unchanged_fail"].append(key)
        else:
            buckets["unchanged_pass"].append(key)
    worse = bool(buckets["new_failing"] or buckets["lower_first_fail_k"])
    better = bool(buckets["fixed"] or buckets["higher_first_fail_k"])
    incomplete = bool(buckets["missing_in_keep"] or buckets["indeterminate"])
    verdict = "mixed" if worse and better else "worse" if worse else "improved" if better else "unchanged"
    return {"verdict": verdict, "coverage_complete": not incomplete,
            "counts": {name: len(v) for name, v in buckets.items()}, **buckets}


def _build_commit(build: Any, label: str) -> str:
    match = _BUILD.search(build) if isinstance(build, str) else None
    if not match:
        raise ProjectionError(f"width dimension {label} build path is not a store build dir")
    return match.group(1)


def native_rows(path: str | Path) -> tuple[dict, ...]:
    """Strictly re-derived native rows for one ``width_dimension.json``; foreign schema -> ()."""
    path = Path(path)
    raw = _read(path)
    try:
        record = json.loads(raw)
    except ValueError as exc:
        raise ProjectionError("width dimension record is not JSON") from exc
    if not isinstance(record, dict) or record.get("schema") != SCHEMA:
        return ()
    if (record.get("observe_only") is not True or record.get("refuses") is not False
            or record.get("disposition") != "measured" or not isinstance(record.get("comparison"), dict)):
        raise ProjectionError("width dimension record is not a measured observe-only comparison")
    comparison = record["comparison"]
    directory = path.parent
    decision = _json(directory / "DECISION.json")
    route = decision.get("route") if isinstance(decision, dict) else None
    builds = decision.get("builds") if isinstance(decision, dict) else None
    if (not isinstance(route, dict) or route.get("proven") is not True
            or not isinstance(builds, dict) or set(builds) != {"parent", "keep"}):
        raise ProjectionError("width dimension route proof is absent or not proven")
    anchor_table, anchor_head, anchor_sha = _table(directory / "parent")
    keep_table, keep_head, keep_sha = _table(directory / "keep")
    for label, head, table in (("parent", anchor_head, anchor_table), ("keep", keep_head, keep_table)):
        commit = _build_commit(builds[label], label)
        if (head.get("ggml_commit") != commit or head.get("backend_bound") != "ROCm0"
                or not str(head.get("env", {}).get("LD_LIBRARY_PATH", "")).startswith(builds[label])):
            raise ProjectionError(f"width dimension {label} run header does not match its build {builds[label]}")
    if anchor_head.get("device_description") != keep_head.get("device_description"):
        raise ProjectionError("width dimension parent/keep ran on different devices")
    derived = _compare(anchor_table, keep_table)
    if derived != comparison:
        raise ProjectionError("width dimension comparison does not re-derive from parent/keep cells")
    if decision.get("counts") != comparison["counts"] or decision.get("coverage_complete") is not True \
            or comparison["coverage_complete"] is not True:
        raise ProjectionError("width dimension decision/coverage differs from the comparison")
    attest = hashlib.sha256(raw).hexdigest()
    total = sum(comparison["counts"][name] for name in BUCKETS)
    common = {"record_path": str(path), "record_sha256": attest, "decided_at": decision.get("decided_at"),
              "builds": dict(builds), "ggml_commits": {"parent": anchor_head["ggml_commit"],
                                                       "keep": keep_head["ggml_commit"]},
              "device": keep_head["device_description"], "backend": keep_head["backend_bound"],
              "cells_sha256": {"parent": anchor_sha, "keep": keep_sha},
              "touched": record.get("touched"), "verdict": comparison["verdict"],
              "counts": dict(comparison["counts"]), "cells_compared": total}
    return tuple({**common, "bucket": bucket, "metric": metric, "direction": direction,
                  "value": comparison["counts"][bucket],
                  "cells": comparison[bucket] if bucket in ("higher_first_fail_k", "lower_first_fail_k",
                                                            "new_failing", "fixed") else []}
                 for bucket, metric, direction in METRICS)


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or "record_path" not in native:
        raise ProjectionError("width dimension native row must retain its record path")
    if native not in native_rows(native["record_path"]):
        raise ProjectionError("width dimension projected row differs from the stored record")
    decided = native["decided_at"]
    if not isinstance(decided, str) or not decided:
        raise ProjectionError("width dimension decision time is missing")
    builds = native["builds"]
    claim = (f"AKX-ALL-27 HIP width invariance, keep {builds['keep']} vs parent {builds['parent']} on "
             f"{native['device']}: {native['value']} of {native['cells_compared']} compared cells "
             f"{native['bucket'].replace('_', ' ')}; relative verdict {native['verdict']}; "
             "observe-only op-level observation at the stated footprint, protocol unqualified")
    return ClaimTuple(
        measurement_id=f"akx-width:{native['record_sha256']}:{native['bucket']}",
        metric=native["metric"], value=native["value"], date=decided, category="CANDIDATE",
        claim=claim, metric_direction=native["direction"], protocol_id="", unit="cells",
        attestation_path=native["record_path"], attestation_sha256=native["record_sha256"],
        attestation_locator=f"akx-width:{native['record_path']}",
        attestation_present=True, attestation_verified=True, source_kind=SOURCE_KIND,
        applicability={"backend": "hip", "device": native["device"],
                       "kernel": {"build_path": builds["keep"]}},
        extra={"adapter": ADAPTER_ID, "bucket": native["bucket"], "counts": native["counts"],
               "cells_compared": native["cells_compared"], "builds": builds,
               "ggml_commits": native["ggml_commits"], "cells_sha256": native["cells_sha256"],
               "touched": native["touched"], "cells": native["cells"]},
    )


def frames_for_record(path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY))
    return frames


__all__ = ["ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "SCHEMA", "native_rows", "project", "frames_for_record"]
