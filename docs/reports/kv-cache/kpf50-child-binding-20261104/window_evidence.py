#!/usr/bin/env python3
"""Bind child JSONL evidence to the native Run.finish record; still partial only."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import importlib.util
from pathlib import Path

_CHILD_PATH = (Path(__file__).resolve().parent.parent /
               "kpf50-child-evidence-20261104" / "child_evidence.py")
_CHILD_SPEC = importlib.util.spec_from_file_location("kpf50_child_evidence", _CHILD_PATH)
if _CHILD_SPEC is None or _CHILD_SPEC.loader is None:
    raise ImportError(f"cannot load child evidence validator at {_CHILD_PATH}")
_CHILD_MODULE = importlib.util.module_from_spec(_CHILD_SPEC)
_CHILD_SPEC.loader.exec_module(_CHILD_MODULE)
EvidenceError = _CHILD_MODULE.EvidenceError
validate_children = _CHILD_MODULE.validate

SCHEMA = "epyc.kpf50.child-window-evidence.partial.v1"


def validate(jsonl: Path, finish_record: Path) -> dict:
    """Validate child rows and bind their bytes/run identity to Run.finish output."""
    raw = Path(jsonl).read_bytes()
    record_raw = Path(finish_record).read_bytes()
    try:
        record = json.loads(record_raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError("finish record is not valid JSON") from exc
    if not isinstance(record, dict):
        raise EvidenceError("finish record must be a JSON object")
    if record.get("schema") != "epyc.kpf.run.v1":
        raise EvidenceError("finish record schema is not epyc.kpf.run.v1")
    if type(record.get("kpf18_item")) is not int or record["kpf18_item"] != 7:
        raise EvidenceError("finish record is not KPF-18 item 7")
    run_id = record.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise EvidenceError("finish record has no native run_id")
    if record.get("partial") is True:
        raise EvidenceError("partial Run.finish record is not admissible")
    if record.get("rows") != str(Path(jsonl).resolve()):
        raise EvidenceError("finish record rows path does not identify this JSONL")
    digest = hashlib.sha256(raw).hexdigest()
    claimed = record.get("rows_sha256")
    if not isinstance(claimed, str) or not re.fullmatch(r"[0-9a-f]{64}", claimed):
        raise EvidenceError("finish record has no valid rows_sha256")
    if claimed != digest:
        raise EvidenceError("raw JSONL digest does not match Run.finish rows_sha256")
    checks = record.get("checks")
    if not isinstance(checks, dict):
        raise EvidenceError("finish record has no checks summary")
    for name, check in checks.items():
        if not isinstance(check, dict):
            raise EvidenceError(f"finish record check {name!r} is malformed")
        if check.get("failed") or check.get("ok") != check.get("n"):
            raise EvidenceError(f"finish record contains failed check {name!r}")
    fork_check = checks.get("fork_expected")
    if not isinstance(fork_check, dict) or type(fork_check.get("n")) is not int or \
            type(fork_check.get("ok")) is not int or fork_check.get("n") != 4 or \
            fork_check.get("ok") != 4 or fork_check.get("failed") != []:
        raise EvidenceError("finish record must show four successful fork_expected checks")

    child = validate_children(Path(jsonl), run_id)
    if child["source_sha256"] != digest:
        raise EvidenceError("raw JSONL changed during validation")
    return {
        "schema": SCHEMA,
        "status": "partial_structural_evidence",
        "complete_outcome": False,
        "run_id": run_id,
        "source_jsonl": child["source_jsonl"],
        "source_sha256": digest,
        "finish_record": str(Path(finish_record).resolve()),
        "finish_record_sha256": hashlib.sha256(record_raw).hexdigest(),
        "child_suffixes": child["child_suffixes"],
        "fork_tokens": child["fork_tokens"],
        "scientific_validity": "not_assessed",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", type=Path, help="raw rows JSONL consumed by Run.finish")
    parser.add_argument("finish_record", type=Path, help="actual records/<run_id>.json from Run.finish")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.jsonl, args.finish_record)
    except (OSError, EvidenceError) as exc:
        parser.error(str(exc))
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
