#!/usr/bin/env python3
"""Validate raw KPF-50 child JSONL rows; emits structural partial evidence only."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_SUFFIXES = {0, 1, 2, 3}
SCHEMA = "epyc.kpf50.child-evidence.partial.v1"

class EvidenceError(ValueError):
    pass


def validate(path: Path, expected_run_id: str) -> dict:
    """Validate four child rows and bind them to exact input bytes and run ID."""
    if not isinstance(expected_run_id, str) or not expected_run_id:
        raise EvidenceError("expected run ID is required")
    path = Path(path)
    raw = path.read_bytes()
    rows = []
    for lineno, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EvidenceError(f"line {lineno}: invalid JSON") from exc
        if not isinstance(row, dict):
            raise EvidenceError(f"line {lineno}: row must be an object")
        # Every row in a raw file must carry the expected identity; foreign rows
        # cannot be silently discarded as unrelated noise.
        if row.get("run_id") != expected_run_id:
            raise EvidenceError(f"line {lineno}: run identity mismatch")
        if row.get("role") == "child":
            rows.append((lineno, row))

    found = {}
    for lineno, row in rows:
        suffix = row.get("suffix")
        if type(suffix) is not int or suffix not in EXPECTED_SUFFIXES:
            raise EvidenceError(f"line {lineno}: invalid child suffix")
        if suffix in found:
            raise EvidenceError(f"line {lineno}: duplicate child suffix {suffix}")
        if row.get("http") != 200 or row.get("error") not in (None, ""):
            raise EvidenceError(f"line {lineno}: child request did not succeed")
        timings = row.get("timings")
        count = timings.get("n_fork_tokens") if isinstance(timings, dict) else None
        if type(count) is not int or count < 60000:
            raise EvidenceError(f"line {lineno}: fork token witness must be integer >= 60000")
        found[suffix] = count
    if set(found) != EXPECTED_SUFFIXES:
        raise EvidenceError("expected exactly one successful child row for each suffix 0, 1, 2, 3")
    return {
        "schema": SCHEMA,
        "status": "partial_structural_evidence",
        "complete_outcome": False,
        "run_id": expected_run_id,
        "source_jsonl": str(path.resolve()),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "child_suffixes": [0, 1, 2, 3],
        "fork_tokens": [found[i] for i in range(4)],
        "scientific_validity": "not_assessed",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("--run-id", required=True, help="expected runner run_id")
    parser.add_argument("--out", type=Path, help="write partial evidence JSON; stdout otherwise")
    args = parser.parse_args()
    try:
        result = validate(args.jsonl, args.run_id)
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
