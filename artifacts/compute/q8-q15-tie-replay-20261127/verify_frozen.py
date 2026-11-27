#!/usr/bin/env python3
"""Validate persisted replay bytes and recompute winners without a GGUF or AVX-512."""
import argparse
from array import array
import csv
import hashlib
import json
from pathlib import Path
import sys


ARMS = ("fp32", "q8", "q15", "native_q8")


def read_records(path, delimiter):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream, delimiter=delimiter))


def validate_logit_row(blob, record):
    values = array("f")
    values.frombytes(blob)
    if sys.byteorder == "big":
        values.byteswap()
    first = max(values)
    winner = values.index(first)
    values[winner] = -float("inf")
    second = max(values)
    runner_up = values.index(second)
    assert winner == int(record["greedy_id"])
    assert runner_up == int(record["second_id"])
    assert abs(first - float(record["logit_1"])) < 5e-8
    assert abs(second - float(record["logit_2"])) < 5e-8
    assert abs(first - second - float(record["gap"])) < 5e-8


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    out = args.evidence
    result = json.loads((out / "RESULT.json").read_text())
    for name, expected in result["sha256"].items():
        with (out / name).open("rb") as stream:
            assert hashlib.file_digest(stream, "sha256").hexdigest() == expected, name

    rows = read_records(out / "decisions.csv", ",")
    records = {(r["fixture"], int(r["threads"]), r["arm"]): r for r in rows}
    fixtures = read_records(out / "fixtures.tsv", "\t")
    row_bytes = int(result["weight"]["vocab"]) * 4
    captured = {}
    with (out / "captured-logits.f32").open("rb") as stream:
        for fixture in fixtures:
            if fixture["kind"] == "stress":
                continue
            fixture_id = fixture["id"]
            blob = stream.read(row_bytes)
            assert len(blob) == row_bytes
            validate_logit_row(blob, records[(fixture_id, 8, "captured")])
            captured[fixture_id] = hashlib.sha256(blob).digest()
        assert stream.read(1) == b""

    checks = {}
    for threads in (1, 8, 24):
        native_matches_q8 = native_matches_captured = 0
        with (out / f"head-t{threads}.f32").open("rb") as stream:
            for fixture in fixtures:
                fixture_id = fixture["id"]
                blobs = {}
                for arm in ARMS:
                    blob = stream.read(row_bytes)
                    assert len(blob) == row_bytes
                    validate_logit_row(blob, records[(fixture_id, threads, arm)])
                    blobs[arm] = blob
                native_matches_q8 += blobs["native_q8"] == blobs["q8"]
                if fixture_id in captured:
                    native_matches_captured += hashlib.sha256(blobs["native_q8"]).digest() == captured[fixture_id]
            assert stream.read(1) == b""
        checks[threads] = {
            "native_vs_matched_q8_full_logit_bytes_equal": native_matches_q8,
            "native_vs_captured_full_logit_bytes_equal": native_matches_captured,
        }
    print(json.dumps({"verified_logit_rows": len(rows), "bytewise_checks": checks}, indent=2))


if __name__ == "__main__":
    main()
