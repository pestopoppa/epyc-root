"""VB-V11-ORACLE-WRITE: V11-086 FP32-oracle rerun (FLASH_ATTN_EXT test-backend-ops) as measurement OBSERVATIONS.

Source: ``ORACLE_RERUN.json`` (schema ``epyc.v11-086v2.oracle-rerun.v1``) written by the rerun's scorer
``fa086v2_oracle_rerun.py`` (``/mnt/raid0/llm/tmp/v11-runs/086v2/fp32oracle/``). One row per scored arm
(``std_C std_Bunset std_B1 std_Bauto long_C long_Bunset long_B1 long_Bauto``): cases passed over cases run, with the
failing-cell identities, the largest error on a failed case, and the PREDECLARED clause verdicts (A1-A3, the amended
``tbo_fa_100``, the strict letter, ``prediction_met``) copied verbatim from the scorer. The attested artifact is
``ORACLE_RERUN.json``; the scorer writes the sidecar next to it (best effort, non-fatal) and this module is also a CLI
(``python3 v11_oracle_rerun.py write --results F --out-dir D``) so it can be re-run by hand.

Doctrine: PROJECTION ONLY (``claim_tuple.grade()`` decides); the clause verdicts are the scorer's words and are never
re-derived here; ``value`` must equal ``passed / total`` of the same row; an arm the scorer could not measure
(``passed`` or ``total`` null) yields NO row -- absence is recorded by its absence, never filled; ``protocol_id`` is
always empty (an amendment document is not a codified protocol, one run per arm), so the ladder caps the tuple.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ProjectionError, register, to_frames  # noqa: E402

from adapters import _native_sidecar as ns  # noqa: E402
from adapters._native_sidecar import CaptureError  # noqa: E402,F401

CAPTURE_SCHEMA = "epyc.vidya.v11_oracle_rerun_capture.v1"
SOURCE_SCHEMA = "epyc.v11-086v2.oracle-rerun.v1"
SIDECAR_NAME = "v11_oracle_rerun.beliefs.jsonl"
ADAPTER_ID = "vidya.adapters.v11_oracle_rerun/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "v11-086-oracle-rerun"
METRIC = "v11_086_fp32_oracle_tbo_pass_fraction"
UNIT = "fraction of FLASH_ATTN_EXT test-backend-ops cases within tolerance against the FP32 oracle"
ARMS = ("std_C", "std_Bunset", "std_B1", "std_Bauto", "long_C", "long_Bunset", "long_B1", "long_Bauto")
VKQ_REG = {"C": "unset", "Bunset": "unset", "B1": "1", "Bauto": "auto"}  # GGML_FA_VKQ_REG per arm
CLAUSE_KEYS = ("A1_std_100_all_arms", "A2_long_100_on_B", "A3_long_C_equals_Bunset_failset",
               "tbo_fa_100_amended", "tbo_fa_100_letter", "prediction_met", "champion_long_property", "summary")


def _jsonable(value: Any) -> Any:
    """Canonical-JSON-safe copy: non-finite floats become their text, never a silent number."""
    if isinstance(value, float) and not math.isfinite(value):
        return repr(value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise CaptureError(f"ORACLE_RERUN unreadable: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema") != SOURCE_SCHEMA or not isinstance(data.get("arms"), dict):
        raise CaptureError(f"ORACLE_RERUN must be a {SOURCE_SCHEMA} object with an 'arms' map")
    return data


def row_problems(row: Any) -> list[str]:
    p = ns.common_problems(row, schema=CAPTURE_SCHEMA, optional_text=("protocol_id",))
    if not isinstance(row, dict) or not isinstance(row.get("extra"), dict):
        return p
    e = row["extra"]
    if row.get("protocol_id") != "":
        p.append("protocol_id must be empty: no codified protocol, an OBSERVATION")
    if row.get("metric") != METRIC:
        p.append(f"metric must be {METRIC}")
    if e.get("arm") not in ARMS:
        p.append(f"extra.arm must be one of {list(ARMS)}")
    passed, total = e.get("passed"), e.get("total")
    if not (ns.nonneg_int(passed) and ns.nonneg_int(total) and total > 0 and passed <= total):
        p.append("extra.passed/total must be integers with 0 <= passed <= total, total > 0")
    else:
        if row.get("reps") != total:
            p.append("reps must equal extra.total (cases run)")
        if ns.finite(row.get("value")) and abs(row["value"] - passed / total) > 1e-9:
            p.append("value must equal extra.passed / extra.total")
    if not isinstance(e.get("fail_keys"), list):
        p.append("extra.fail_keys must be the scorer's failing-cell list")
    if not isinstance(e.get("clauses"), dict) or set(e["clauses"]) != set(CLAUSE_KEYS):
        p.append(f"extra.clauses must carry exactly the scorer's {list(CLAUSE_KEYS)}")
    if not p:
        p += ns.check_identity(row, {"run_id": row["run_id"], "arm": e["arm"], "results": row["results_sha256"]}, "v11orc")
    return p + ns.self_hash_problems(row)


validate_row = row_problems


def write_belief_measurements(out_dir: str | Path, *, run_id: str, producer: str, results_path: str | Path,
                              emitted_at: str | None = None) -> Path:
    raw = Path(results_path)
    data = _load(raw)
    digest = ns.file_sha256(raw)
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    clauses = {k: _jsonable(data.get(k)) for k in CLAUSE_KEYS}
    rows = []
    for arm in ARMS:
        cell = data["arms"].get(arm)
        if not isinstance(cell, dict) or cell.get("passed") is None or cell.get("total") is None:
            continue  # unmeasured arm: absence stays absent
        passed, total = cell["passed"], cell["total"]
        row = {
            "schema": CAPTURE_SCHEMA, "run_id": run_id, "producer": producer, "emitted_at": when,
            "date": str(data.get("written") or when), "metric": METRIC, "value": passed / total, "unit": UNIT,
            "metric_direction": "higher_better", "category": "BASELINE" if arm.endswith("_C") else "CANDIDATE",
            "claim": (f"V11-086 FP32-oracle rerun arm {arm}: {passed}/{total} FLASH_ATTN_EXT cases within tolerance "
                      f"({len(cell.get('fail_keys') or [])} failing cell(s)); scorer verdict tbo_fa_100_amended="
                      f"{data.get('tbo_fa_100_amended')!r}, strict letter {data.get('tbo_fa_100_letter')!r}; one run "
                      f"per arm, predeclared amendment, no codified protocol"),
            "protocol_id": "", "reps": total, "reps_basis": "test-backend-ops cases run (FLASH_ATTN_EXT, every case counted)",
            "results_path": str(raw), "results_sha256": digest,
            "extra": {"arm": arm, "passed": passed, "total": total, "rc": cell.get("rc"), "ok": cell.get("ok"),
                      "fail_keys": _jsonable(cell.get("fail_keys") or []),
                      "max_err_on_fail": _jsonable(cell.get("max_err_on_fail")), "oracle": data.get("oracle"),
                      "c_build": data.get("c_build"), "b_build": data.get("b_build"), "clauses": clauses},
        }
        row["measurement_id"] = "v11orc_" + ns.content_hash({"run_id": run_id, "arm": arm, "results": digest})[:24]
        ns.seal(row)
        bad = row_problems(row)
        if bad:
            raise CaptureError("refusing to emit an invalid row: " + "; ".join(bad))
        rows.append(row)
    if not rows:
        raise CaptureError("no arm was measured (every passed/total is null): nothing to project")
    return ns.write_rows_atomic(Path(out_dir) / SIDECAR_NAME, rows)


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    return ns.native_rows(sidecar_path, row_problems)


@register(SOURCE_KIND)
def project(native: Any):
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("V11 oracle native row must retain the producer row")
    row = native["row"]
    problems = row_problems(row)
    if problems:
        raise ProjectionError("V11 oracle row is not a producer-authored capture: " + "; ".join(problems))
    e = row["extra"]
    locator = f"v11orc:{row['run_id']}:{e['arm']}:{row['results_path']}"
    tup = ns.to_claim_tuple(row, source_kind=SOURCE_KIND, locator=locator, sidecar_path=native.get("sidecar_path", ""))
    mode = VKQ_REG[e["arm"].split("_", 1)[1]]
    return dataclasses.replace(
        tup,
        applicability={"scope_basis": "native", "backend": "cpu", "knob_family": "fa_vkq_reg",
                       "knobs": {"GGML_FA_VKQ_REG": mode, "op": "FLASH_ATTN_EXT", "oracle": "fp32"},
                       "varied": ["GGML_FA_VKQ_REG"]},
        observation={"outcome_native": f"tbo_fa_100_amended={e['clauses']['tbo_fa_100_amended']}"[:120]})


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY))
    return frames


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="write the V11-086 oracle-rerun belief sidecar")
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write")
    w.add_argument("--results", required=True)
    w.add_argument("--out-dir", required=True)
    w.add_argument("--run-id", default="v11-086v2-fp32oracle")
    w.add_argument("--producer", default="fillers-3c4ca599/v11drv/fa086v2_oracle_rerun.py")
    a = ap.parse_args(argv)
    try:
        path = write_belief_measurements(a.out_dir, run_id=a.run_id, producer=a.producer, results_path=a.results)
    except CaptureError as exc:  # a VOID/INCOMPLETE or unmeasured result has nothing to project: say so, no traceback
        print(f"belief sidecar NOT written: {exc}", file=sys.stderr)
        return 3
    print(json.dumps({"sidecar": str(path), "rows": len(native_rows(path))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
