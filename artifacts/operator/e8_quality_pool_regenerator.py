#!/usr/bin/env python3
"""Deterministically replay the two E8 scorer repairs into the active pool."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import uuid

import yaml


TARGETS = {
    ("real_suite_v1", "real_suite_v1_0043"): "real_suite_v1.yaml",
    ("long_context", "needle_039"): "long_context.yaml",
}
OLD_PATTERN = r"\d+"
NEW_PATTERN = r"(\d+)"


def fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--vl-prefix", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    research = args.research.resolve()
    output = args.output.resolve()
    stage = args.stage.resolve()
    vl_prefix = args.vl_prefix.resolve()
    if any(os.environ.get(name) != "1" for name in ("HF_HUB_OFFLINE", "HF_DATASETS_OFFLINE", "TRANSFORMERS_OFFLINE")):
        raise SystemExit("pool regeneration must run fully offline")
    live_pool = research / "benchmarks/prompts/question_pool.jsonl"
    if output == live_pool.resolve():
        raise SystemExit("regenerator refuses to write the active pool directly")
    if not vl_prefix.is_dir():
        raise SystemExit(f"canonical VL prefix is missing: {vl_prefix}")

    stage.mkdir(parents=True, exist_ok=False)
    repaired_patterns: dict[tuple[str, str], str] = {}
    debug_dir = research / "benchmarks/prompts/debug"
    for key, filename in TARGETS.items():
        source = yaml.safe_load((debug_dir / filename).read_text(encoding="utf-8"))
        rows = [row for row in source.get("questions", []) if row.get("id") == key[1]]
        if len(rows) != 1:
            raise SystemExit(f"expected exactly one repaired source row for {key}")
        row = rows[0]
        pattern = row.get("scoring_config", {}).get("extract_pattern")
        if row.get("scoring_method") != "exact_match" or pattern != NEW_PATTERN:
            raise SystemExit(f"repaired source contract mismatch for {key}")
        repaired_patterns[key] = pattern

    temporary = output.with_name(f".{output.name}.tmp-{uuid.uuid4().hex}")
    seen: set[tuple[str, str]] = set()
    with live_pool.open(encoding="utf-8") as source, temporary.open(
        "x", encoding="utf-8"
    ) as destination:
        for ordinal, physical_line in enumerate(source):
            row = json.loads(physical_line)
            if ordinal == 0:
                if not row.get("__pool_metadata__"):
                    raise SystemExit("active pool metadata header is missing")
                row["generated_at"] = datetime.now(UTC).isoformat()
            else:
                key = (row.get("suite"), row.get("id"))
                if key in repaired_patterns:
                    if key in seen:
                        raise SystemExit(f"duplicate active-pool target row: {key}")
                    if (
                        row.get("scoring_method") != "exact_match"
                        or row.get("scoring_config", {}).get("extract_pattern")
                        != OLD_PATTERN
                    ):
                        raise SystemExit(f"active-pool target pre-state mismatch: {key}")
                    row["scoring_config"]["extract_pattern"] = repaired_patterns[key]
                    seen.add(key)
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")
        destination.flush()
        os.fsync(destination.fileno())
    if seen != set(TARGETS):
        temporary.unlink(missing_ok=True)
        raise SystemExit(f"active pool is missing repair targets: {set(TARGETS) - seen}")
    os.replace(temporary, output)
    fsync_dir(output.parent)
    witness = {
        "schema": "epyc.e8_quality_pool_deterministic_replay.v1",
        "source_pool": str(live_pool.resolve()),
        "output": str(output),
        "repairs": [
            {"suite": suite, "id": qid, "extract_pattern": repaired_patterns[(suite, qid)]}
            for suite, qid in sorted(TARGETS)
        ],
    }
    witness_path = stage / "replay-witness.json"
    witness_path.write_text(
        json.dumps(witness, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with witness_path.open("rb") as handle:
        os.fsync(handle.fileno())
    fsync_dir(stage)
    print(f"replayed two scorer repairs into staged pool at {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
