"""AKX-ALL-26 CPU width-invariance cell table -> measurement ClaimTuples (CPU half of
VB-AKX-ALL-26-CELLS-WIRE; the HIP half is ``autokernel_width_dimension.py``).

Source: ``cells.jsonl.gz`` (schema ``akx-all-26.cell.v1``, one record per (route, nth, op, type,
shape, mode, seed, k)) beside ``group_headers.jsonl`` (per-process env/CPU echo), ``summary.json``
and the frozen ``ADDENDUM.sha256`` in one artifact directory.

STRICT READER, not a trusting one. Stored verdicts are derived values, so this reader re-derives
every one from the per-rep digests and refuses on ANY difference: cell verdict (PASS iff every rep's
batched digest equals its serial digest), A/A cleanliness (all reps byte-identical), UNSUPPORTED rows
(no reps, a stated reason), the three controls' k-patterns, the summary's cell/group counts, and the
frozen addendum hash. Every scored group must have a header whose route knobs, nth, seed and rep
count match, and every route must echo one consistent env with one build path. A cell is counted only
with its full A/A rep set and config echo; control cells and UNSUPPORTED cells stay rows (listed in
``extra``), never silently absent.

PROJECTION ONLY. ``claim_tuple.grade()`` decides every tuple; no ladder here. Observations carry an
empty ``protocol_id`` and no ``reps`` (cells are not repetitions). Scope is (route, nth) at the
recorded build; the frozen-prediction scoring is carried as provenance, not re-scored. The built
library is gone from scratch, so ``binary_sha256.txt`` is provenance, not a verified linkage.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

ADAPTER_ID = "vidya.adapters.autokernel_width_cells_cpu/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "autokernel-width-cells-cpu"
CELL_SCHEMA = "akx-all-26.cell.v1"
GROUP_SCHEMA = "akx-all-26.group.v1"
SUMMARY_SCHEMA = "akx-all-26.cpu-summary.v1"
MAX_BYTES = 256 << 20
OPS = {"mm": "MUL_MAT", "mmid": "MUL_MAT_ID", "fa": "FLASH_ATTN_EXT", "gdn": "GATED_DELTA_NET",
       "ctl": "CONTROL"}
# (outcome, metric, direction). Unsupported groups are coverage, carried in extra, not a metric.
METRICS = (
    ("fail", "width_invariance_cpu_failing_groups", "lower_better"),
    ("pass", "width_invariance_cpu_passing_groups", "higher_better"),
)
_ROUTE = re.compile(r"cpu(?:-native)?(?:\[([A-Z0-9_=,]+)\])?$")
_DATE = re.compile(r"CPU half, (\d{4}-\d{2}-\d{2})")
_SHA = re.compile(r"[0-9a-f]{64}")


def _read(path: Path) -> bytes:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
    except OSError as exc:
        raise ProjectionError(f"width cells input unreadable: {path}: {exc}") from exc
    if len(raw) > MAX_BYTES:
        raise ProjectionError(f"width cells input exceeds bound: {path}")
    return raw


def _jsonl(raw: bytes, what: str) -> list[dict]:
    rows = []
    for line in raw.decode("utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except ValueError as exc:
                raise ProjectionError(f"width cells {what} line is not JSON") from exc
    return rows


def _derive_cell(cell: dict) -> str:
    """Verdict re-derived from the rep digests alone; refuses on any internal disagreement."""
    reps = cell.get("reps")
    if not isinstance(reps, list) or cell.get("n_reps") != len(reps):
        raise ProjectionError("width cells n_reps differs from the stored reps")
    if cell.get("verdict") == "UNSUPPORTED" or not reps:
        if reps or cell.get("verdict") != "UNSUPPORTED" or not cell.get("reason") \
                or cell.get("aa_clean") is not None:
            raise ProjectionError("width cells UNSUPPORTED row is malformed")
        return "UNSUPPORTED"
    for rep in reps:
        same = rep.get("batched_digest") == rep.get("serial_digest")
        if not isinstance(rep.get("batched_digest"), str) or rep.get("equal") is not same:
            raise ProjectionError("width cells rep equal flag differs from its digests")
    identical = len({(r["serial_digest"], r["batched_digest"]) for r in reps}) == 1
    if cell.get("aa_clean") is not identical or not identical:
        raise ProjectionError("width cells A/A reps are not byte-identical or aa_clean differs")
    verdict = "PASS" if all(r["equal"] for r in reps) else "FAIL"
    if cell.get("verdict") != verdict:
        raise ProjectionError(f"width cells stored verdict {cell.get('verdict')} does not re-derive")
    return verdict


def _knobs(route: str) -> dict[str, str]:
    match = _ROUTE.match(route)
    if not match:
        raise ProjectionError(f"width cells route label is not a CPU route: {route}")
    return dict(kv.split("=", 1) for kv in match.group(1).split(",")) if match.group(1) else {}


def native_rows(path: str | Path) -> tuple[dict, ...]:
    """Strictly re-derived native rows for one ``cells.jsonl.gz``; foreign content -> ()."""
    path = Path(path)
    if path.name != "cells.jsonl.gz":
        return ()
    directory = path.parent
    raw = _read(path)
    try:
        cells = _jsonl(gzip.decompress(raw), "cells")
    except (OSError, EOFError) as exc:
        raise ProjectionError("width cells file is not gzip") from exc
    if not cells or any(c.get("schema") != CELL_SCHEMA for c in cells):
        return ()
    headers_raw = _read(directory / "group_headers.jsonl")
    headers = _jsonl(headers_raw, "group header")
    summary = json.loads(_read(directory / "summary.json"))
    if summary.get("schema") != SUMMARY_SCHEMA:
        raise ProjectionError("width cells summary schema differs")

    # frozen addendum: its hash must be the one on record
    addendum = _read(directory / "cpu_addendum_predictions.md")
    pinned = _read(directory / "ADDENDUM.sha256").decode().split()
    if hashlib.sha256(addendum).hexdigest() not in pinned:
        raise ProjectionError("width cells frozen addendum hash does not match ADDENDUM.sha256")
    readme = _read(directory / "README.md").decode("utf-8")
    dated = _DATE.search(readme)
    if not dated:
        raise ProjectionError("width cells README states no run date")

    # headers: one build path, one env per route, knobs in the label echoed in the env
    hdr: dict[tuple, dict] = {}
    route_env: dict[str, dict] = {}
    for h in headers:
        if h.get("schema") != GROUP_SCHEMA or h.get("backend") != "cpu" or h.get("op") not in OPS:
            raise ProjectionError("width cells group header is malformed")
        env = h.get("env")
        if not isinstance(env, dict) or not env.get("LD_LIBRARY_PATH"):
            raise ProjectionError("width cells group header lacks its env echo")
        set_env = {k: v for k, v in env.items() if v != "<unset>"}
        for knob, want in _knobs(h["route"]).items():
            if set_env.get(knob) != want:
                raise ProjectionError(f"width cells header env does not echo route knob {knob}")
        if route_env.setdefault(h["route"], set_env) != set_env:
            raise ProjectionError(f"width cells route {h['route']} has inconsistent env echoes")
        key = (h["route"], h["nth"], h["seed"], h["op"], str(h["type"]).upper())
        if key in hdr:
            raise ProjectionError(f"width cells duplicate group header {key}")
        hdr[key] = h
    builds = {e["LD_LIBRARY_PATH"] for e in route_env.values()}
    if len(builds) != 1:
        raise ProjectionError("width cells headers disagree on the build path")
    build_path = builds.pop()

    # fold k-rows into groups, re-deriving each cell
    groups: dict[tuple, dict] = {}
    seen = set()
    for c in cells:
        verdict = _derive_cell(c)
        short = next((s for s, o in OPS.items() if o == c.get("op")), None)
        if short is None:
            raise ProjectionError(f"width cells unknown op {c.get('op')}")
        gkey = (c["route"], c["nth"], c["seed"], c["op"], str(c["type"]).upper(), c["shape"], c["mode"])
        if (gkey, c["k"]) in seen:
            raise ProjectionError(f"width cells duplicate cell {gkey} k={c['k']}")
        seen.add((gkey, c["k"]))
        header = hdr.get((c["route"], c["nth"], c["seed"], short,
                         "-" if short == "ctl" else str(c["type"]).upper()))
        if header is None:
            raise ProjectionError(f"width cells cell has no matching group header: {gkey}")
        if verdict != "UNSUPPORTED" and c["n_reps"] != header["reps"]:
            raise ProjectionError(f"width cells rep count differs from its header: {gkey}")
        groups.setdefault(gkey, {"cells": {}, "kmax": header["kmax"]})["cells"][c["k"]] = verdict
    out_groups: list[dict] = []
    for gkey, g in groups.items():
        ks = sorted(g["cells"])
        if ks != list(range(1, g["kmax"] + 1)):
            raise ProjectionError(f"width cells group {gkey} does not cover k=1..{g['kmax']}")
        pattern = "".join({"PASS": "P", "FAIL": "F", "UNSUPPORTED": "U"}[g["cells"][k]] for k in ks)
        if "U" in pattern and set(pattern) != {"U"}:
            raise ProjectionError(f"width cells group {gkey} mixes UNSUPPORTED with measured cells")
        outcome = "unsupported" if pattern[0] == "U" else "fail" if "F" in pattern else "pass"
        out_groups.append({"route": gkey[0], "nth": gkey[1], "seed": gkey[2], "op": gkey[3],
                           "type": gkey[4], "shape": gkey[5], "mode": gkey[6], "pattern": pattern,
                           "outcome": outcome,
                           "first_fail_k": pattern.index("F") + 1 if outcome == "fail" else None})
    out_groups.sort(key=lambda g: (g["route"], g["nth"], g["op"], g["type"], g["shape"], g["mode"], g["seed"]))

    # controls: the instrument check. Re-derived patterns must equal the summary's and be as designed.
    controls = {g["shape"]: g["pattern"] for g in out_groups if g["op"] == "CONTROL"}
    designed = {"ctl-bitflip-injection": "F" * 9, "ctl-negative-width-independent": "P" * 9,
                "ctl-positive-width-dependent": "P" + "F" * 8}
    if controls != designed or summary.get("controls") != controls or summary.get("controls_ok") is not True:
        raise ProjectionError("width cells controls do not re-derive as designed")
    # summary cross-checks
    measured = sum(1 for c in cells if c["verdict"] != "UNSUPPORTED")
    if (summary.get("n_cells") != len(cells) or summary.get("n_cells_with_reps") != measured
            or summary.get("n_groups") != len(out_groups) or summary.get("n_aa_unclean") != 0
            or summary.get("err_cells") != [] or summary.get("nondet_cells") != []):
        raise ProjectionError("width cells summary counts do not re-derive from the cells")

    provenance = {"binary_sha256": _read(directory / "binary_sha256.txt").decode().split(),
                  "scoring_counts": summary.get("scoring_counts"),
                  "predicted_fail_list_sha256": hashlib.sha256(
                      _read(directory / "predicted_fail_list.jsonl")).hexdigest(),
                  "addendum_sha256": hashlib.sha256(addendum).hexdigest()}
    scored = [g for g in out_groups if g["op"] != "CONTROL"]
    scopes = sorted({(g["route"], g["nth"]) for g in scored})
    attest = hashlib.sha256(raw).hexdigest()
    natives = []
    for route, nth in scopes:
        in_scope = [g for g in scored if (g["route"], g["nth"]) == (route, nth)]
        counts = {o: sum(1 for g in in_scope if g["outcome"] == o) for o in ("fail", "pass", "unsupported")}
        for outcome, metric, direction in METRICS:
            natives.append({
                "record_path": str(path), "record_sha256": attest, "run_date": dated.group(1),
                "build_path": build_path, "route": route, "nth": nth, "env": route_env[route],
                "outcome": outcome, "metric": metric, "direction": direction,
                "value": counts[outcome], "counts": counts, "groups_in_scope": len(in_scope),
                "cells_in_scope": sum(len(g["pattern"]) for g in in_scope),
                "groups": [g for g in in_scope if g["outcome"] in (outcome, "unsupported")],
                "controls": controls, "provenance": provenance})
    return tuple(natives)


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or "record_path" not in native:
        raise ProjectionError("width cells native row must retain its record path")
    if native not in native_rows(native["record_path"]):
        raise ProjectionError("width cells projected row differs from the stored record")
    knobs = {k: v for k, v in native["env"].items() if k != "LD_LIBRARY_PATH"}
    claim = (f"AKX-ALL-26 CPU width invariance, route {native['route']} nth={native['nth']}: "
             f"{native['value']} of {native['groups_in_scope']} op/type/shape groups "
             f"{native['outcome']} batched-vs-serial byte identity across k=1..9 "
             f"({native['counts']['unsupported']} unsupported); observe-only op-level observation "
             "at the recorded build, protocol unqualified")
    applicability = {"backend": "cpu",
                     "kernel": {"build_path": native["build_path"], "route": native["route"],
                                "nth": native["nth"]}}
    if knobs:
        applicability["knobs"] = knobs
    return ClaimTuple(
        measurement_id=f"akx-width-cpu:{native['record_sha256']}:{native['route']}:nth{native['nth']}:"
                       f"{native['outcome']}",
        metric=native["metric"], value=native["value"], date=native["run_date"], category="CANDIDATE",
        claim=claim, metric_direction=native["direction"], protocol_id="", unit="groups",
        attestation_path=native["record_path"], attestation_sha256=native["record_sha256"],
        attestation_locator=f"akx-width-cpu:{native['record_path']}",
        attestation_present=True, attestation_verified=True, source_kind=SOURCE_KIND,
        applicability=applicability,
        extra={"adapter": ADAPTER_ID, "outcome": native["outcome"], "route": native["route"],
               "nth": native["nth"], "counts": native["counts"],
               "groups_in_scope": native["groups_in_scope"], "cells_in_scope": native["cells_in_scope"],
               "env": native["env"], "controls": native["controls"], "groups": native["groups"],
               "provenance": native["provenance"]},
    )


def frames_for_record(path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY))
    return frames


__all__ = ["ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "native_rows", "project", "frames_for_record"]
