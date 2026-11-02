#!/usr/bin/env python3
"""Materialize pinned GPQA-CoT items for resumable, one-item runner calls.

This is offline preparation only. A rowflow job must still check its stop file
and deadline between calls, validate responses and establish GPU residency.
Each item must use its own per-question output: the v7 runner rejects and
rewrites same-suite records whose IDs are absent from the current manifest.
Combine those separate outputs only after validating every record.
"""
import argparse
import hashlib
import json
from pathlib import Path

PIN = "14e807dd11736b022f337466efc0fb5c95bf6e521a4514a09d0f25916524ecee"
SUITE = "gpqa_diamond_cot"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path, help="new output directory")
    args = parser.parse_args()
    raw = args.manifest.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PIN:
        parser.error("GPQA manifest digest does not match the pinned source")
    questions = json.loads(raw)["suites"][SUITE]
    ids = [q["id"] for q in questions]
    if len(ids) != 198 or len(set(ids)) != 198:
        parser.error("expected 198 distinct GPQA question IDs")
    args.output.mkdir(parents=True, exist_ok=False)
    for i, question in enumerate(questions):
        path = args.output / f"{i:03d}.json"
        path.write_text(json.dumps({"suites": {SUITE: [question]}}, ensure_ascii=False) + "\n")
    print("Prepared 198 single-item manifests in pinned source order")


if __name__ == "__main__":
    main()
