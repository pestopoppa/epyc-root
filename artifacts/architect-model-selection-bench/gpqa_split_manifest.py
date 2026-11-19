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
import os
from pathlib import Path
import tempfile

PIN = "14e807dd11736b022f337466efc0fb5c95bf6e521a4514a09d0f25916524ecee"
SUITE = "gpqa_diamond_cot"


def prepare_manifest(manifest: Path, output: Path):
    """Publish a complete split, preserving existing output on every failure.

    Stage beside the destination so the final rename stays on one filesystem.
    Reserve the destination exclusively before rename, including against another
    preparer. A failed write never exposes a partially populated output directory.
    """
    raw = manifest.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PIN:
        raise ValueError("GPQA manifest digest does not match the pinned source")
    questions = json.loads(raw)["suites"][SUITE]
    ids = [q["id"] for q in questions]
    if len(ids) != 198 or any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != 198:
        raise ValueError("expected 198 distinct nonempty GPQA question IDs")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{output.name}-", dir=output.parent) as tmp:
        staged = Path(tmp) / "items"
        staged.mkdir()
        for i, question in enumerate(questions):
            path = staged / f"{i:03d}.json"
            path.write_text(json.dumps({"suites": {SUITE: [question]}}, ensure_ascii=False) + "\n", encoding="utf-8")
        output.mkdir(exist_ok=False)
        try:
            os.replace(staged, output)
        except BaseException:
            output.rmdir()  # Only our empty reservation; never remove another run's files.
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path, help="new output directory")
    args = parser.parse_args()
    try:
        prepare_manifest(args.manifest, args.output)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.error(str(exc))
    print("Prepared 198 single-item manifests in pinned source order")


if __name__ == "__main__":
    main()
