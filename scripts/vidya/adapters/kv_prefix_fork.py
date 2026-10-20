"""VB-KVU-PF / VB-KVU-PF.1 read side: project KPF-18 ``epyc.kpf.run.v1`` records into ClaimTuples.

Source class ``measurement``; one ladder (``claim_tuple.grade()``), no private rule. The only admissible
input is a runner-authored ``belief_measurements.jsonl`` line (``kpf18_gate.py`` ``Run.finish``). A line is
refused when its schema is wrong, its ``record_sha256`` does not re-derive, or a required field is absent;
an invalid line voids the WHOLE file (the writer appends complete records; partial validity is corruption).
Pre-extension records (no ``kpf_ext``) still project; the VB-KVU-PF.1 fields are then simply absent, never filled.

Locator: run x arm x dflash2 x prompt-set sha256 x binary sha256 x window id. Item 1's DFlash2-off record shares
window and binary with its DFlash2-on record, so ``dflash2`` is part of the locator and the arm is
``fork_on_dflash2_off`` (VB-KVU-PF.1 fix; the runner used to label it ``fork_on``).

Attestation is the per-request rows JSONL the runner hashed (``rows`` / ``rows_sha256``); it is re-hashed on read,
so a moved or mutated rows file grades DOWN through the shared ladder rather than being skipped.
Equivalence is carried as COUNTS (top-1 agreement, max-abs logit/KLD, identical greedy prefix) against the
fresh-vs-fresh control floor, never as a pass word.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

SCHEMA = "epyc.kpf.run.v1"
SIDECAR_NAME = "belief_measurements.jsonl"
ADAPTER_ID = "vidya.adapters.kv_prefix_fork/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "kv-prefix-fork-measurement"
ARMS = frozenset({"fork_off", "fork_on", "fork_on_dflash2_off"})
REQUIRED = ("run_id", "arm", "binary_sha256", "prompt_set_sha256", "window_id", "end_utc", "host", "argv",
            "equivalence", "rows", "rows_sha256", "record_sha256", "category")
EXT_KEYS = ("checkpoint_set", "hit_components", "hit_length_min", "hit_tokens", "tokens_lost_to_missing_checkpoint",
            "drafter_drop_kind", "request_lane", "cache_skip_control", "pinned_count")


def _digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_row(row: Any) -> list[str]:
    if not isinstance(row, dict):
        return ["row is not an object"]
    problems = []
    if row.get("schema") != SCHEMA:
        problems.append(f"schema is not {SCHEMA}")
    for key in REQUIRED:
        if row.get(key) in (None, "", [], {}):
            problems.append(f"missing {key}")
    if row.get("arm") not in ARMS:
        problems.append(f"arm {row.get('arm')!r} not in {sorted(ARMS)}")
    if not problems:
        body = {k: v for k, v in row.items() if k != "record_sha256"}
        if _digest(body) != row["record_sha256"]:
            problems.append("record_sha256 does not re-derive")
    return problems


def _rows_path(row: dict, sidecar: Path) -> Path:
    declared = Path(row["rows"])
    sibling = sidecar.parent / "rows" / declared.name  # the rows dir that travels with the sidecar wins
    return sibling if sibling.is_file() else declared


def _rows_present(row: dict, sidecar: Path) -> bool:
    path = _rows_path(row, sidecar)
    if not path.is_file():
        return False
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest() == row["rows_sha256"]


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    path = Path(sidecar_path)
    if not path.is_file():
        return ()
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            return ()
        if validate_row(row):
            return ()
        rows.append(row)
    if len({r["record_sha256"] for r in rows}) != len(rows):
        return ()
    return tuple({"row": r, "sidecar_path": str(path), "attestation_present": _rows_present(r, path)} for r in rows)


def _metric(row: dict) -> tuple[str, Any, str, int, str]:
    eq = (row.get("equivalence") or {}).get("vs_fresh") or {}
    n = int(eq.get("n") or 0)
    if n > 0:
        agree = eq.get("first_token_top1_agree", eq.get("top1_agree"))  # canonical name, legacy fallback
        if agree is None:
            raise ProjectionError("vs_fresh equivalence has no top-1 agreement count")
        return ("kpf_vs_fresh_first_token_top1_agree_fraction", round(agree / n, 6), "fraction", n,
                "fork-vs-fresh comparisons scored")
    ext = row.get("kpf_ext") or {}
    hit = ext.get("hit_tokens", row.get("n_fork_tokens"))
    if hit is None:
        raise ProjectionError("record has neither vs_fresh equivalence nor hit tokens to project")
    return "kpf_hit_tokens", hit, "tokens", 1, "one run total"


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("KPF native row must retain the runner record")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError("KPF row is not a runner-authored record: " + "; ".join(problems))
    sidecar = Path(native.get("sidecar_path") or ".")
    present = _rows_present(row, sidecar)
    metric, value, unit, reps, basis = _metric(row)
    dflash2 = bool(row.get("dflash2"))
    locator = (f"kpf:{row['run_id']}:{row['arm']}:dflash2={str(dflash2).lower()}:ps={row['prompt_set_sha256'][:16]}:"
               f"bin={row['binary_sha256'][:16]}:win={row['window_id']}")
    ext = row.get("kpf_ext") or {}
    return ClaimTuple(
        measurement_id="kpf-" + hashlib.sha256(row["record_sha256"].encode()).hexdigest()[:32],
        metric=metric,
        value=value,
        date=row["end_utc"],
        category=row["category"],
        claim=(f"KPF-18 item {row.get('kpf18_item')} arm {row['arm']}: {metric} = {value} "
               f"(counts against a fresh-vs-fresh control floor; n=1 per cell, no codified protocol)"),
        metric_direction="higher_better",
        protocol_id="",
        reps=reps,
        reps_basis=basis,
        unit=unit,
        attestation_path=str(_rows_path(row, sidecar)),
        attestation_sha256=row["rows_sha256"],
        attestation_locator=locator,
        attestation_present=present,
        attestation_verified=True if present else None,
        source_kind=SOURCE_KIND,
        extra={
            "schema": row["schema"], "run_id": row["run_id"], "arm": row["arm"], "dflash2": dflash2,
            "kpf18_item": row.get("kpf18_item"), "window_id": row["window_id"],
            "gpu_window_id": row.get("gpu_window_id"), "binary_sha256": row["binary_sha256"],
            "prompt_set_sha256": row["prompt_set_sha256"], "host": row["host"], "argv": row["argv"],
            "start_utc": row.get("start_utc"), "end_utc": row["end_utc"],
            "record_sha256": row["record_sha256"], "sidecar_path": native.get("sidecar_path", ""),
            "equivalence": row["equivalence"], "ttft_ms": row.get("ttft_ms"),
            "prompt_tokens_processed": row.get("prompt_tokens_processed"), "cache_n": row.get("cache_n"),
            "n_fork_tokens": row.get("n_fork_tokens"), "unique_cells_peak": row.get("unique_cells_peak"),
            "decode_tok_s": row.get("decode_tok_s"),
            "kpf_ext": {k: ext.get(k) for k in EXT_KEYS} if ext else None,
        },
    )


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY))
    return frames


__all__ = ["ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "SCHEMA", "SIDECAR_NAME", "native_rows", "project",
           "validate_row", "frames_for_sidecar"]
