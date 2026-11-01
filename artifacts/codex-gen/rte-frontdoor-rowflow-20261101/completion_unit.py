#!/usr/bin/env python3
"""Strict production-only completion check for the RTE rowflow candidate."""
import hashlib
import json
import pathlib
import sys

ROW_ID = "codex-ni-rte-frontdoor-quarter-20261031"
EXPECTED_SOURCE = "b0f8613d65f30986f147e5467b1c66892c887ce5"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def production_complete(root):
    root = pathlib.Path(root)
    manifest = root / "SOURCE-REVIEW.sha256"
    if not manifest.is_file():
        return False
    manifest_sha = sha(manifest)
    for unit_path in sorted((root / "attempts").glob("*/ROWFLOW-UNIT.json")):
        try:
            unit = json.loads(unit_path.read_text())
            if unit.get("schema") != "rte.rowflow.unit.v1" or unit.get("row_id") != ROW_ID:
                continue
            attempt_id = unit.get("attempt_id")
            if (unit.get("unit_kind") != "production_owner_acceptance" or unit.get("acceptance") is not True
                    or unit.get("attempt_mode") != "production" or unit.get("qualification_only") is not False
                    or not isinstance(attempt_id, str) or not attempt_id.startswith("production-")
                    or unit_path.parent.name != attempt_id or not unit.get("grant_sha256")):
                continue
            if unit.get("source_review_sha256") != manifest_sha or unit.get("expected_source") != EXPECTED_SOURCE:
                continue
            if unit.get("committed_live_checker_rc") != 0 or not unit.get("request_id"):
                continue
            owner_path = pathlib.Path(unit["owner_result_path"])
            try:
                owner_path.resolve().relative_to(unit_path.parent.resolve())
            except (OSError, ValueError):
                continue
            attempt_result_path = unit_path.parent / "RESULT.json"
            if (owner_path.is_symlink() or attempt_result_path.is_symlink()
                    or not owner_path.is_file() or sha(owner_path) != unit.get("owner_result_sha256")
                    or not attempt_result_path.is_file()):
                continue
            owner = json.loads(owner_path.read_text())
            attempt_result = json.loads(attempt_result_path.read_text())
            if (attempt_result.get("status") != "pass" or attempt_result.get("partial") is not False
                    or attempt_result.get("drained") is not True or attempt_result.get("survivors") != []
                    or attempt_result.get("owner_result") != str(owner_path)
                    or attempt_result.get("error")):
                continue
            if (owner.get("status") == "pass" and owner.get("request_completed") is True
                    and owner.get("owner_boundary_required") is True
                    and owner.get("expected_source") == EXPECTED_SOURCE
                    and owner.get("committed_live_checker_rc") == 0
                    and owner.get("request_id") == unit.get("request_id")):
                return True
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return False

def main(argv):
    if len(argv) != 3 or argv[1] != "--check":
        return 64
    return 0 if production_complete(argv[2]) else 1

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
