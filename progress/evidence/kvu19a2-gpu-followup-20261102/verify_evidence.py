#!/usr/bin/env python3
"""Deterministic offline checks for preserved KVU-19a-2 evidence only."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
H = ROOT / "historical"
PINS = {
    "historical/fa_harness.cpp": "6dd03a07406cfe26dfd4ff52de4a4067fd7229d77ee5191bbd8e2e34956fa823",
    "historical/branch-vs-loop-index.patch": "4147d2b65bbb416fdee1bf004d5447238933524bf3c087a69dcf6bbeca73b235",
    "historical/source-pair.json": "b7a97f0f8f61f8a3fbda3d319f084b044a1d8c955003a4da497b34dfbdaa548c",
    "historical/fattn-tile.loop-index.cuh": "878a3640f685e68c6c3d3102c331c43054bfb0bce81f68c3224ad271b8d9d844",
    "historical/fattn-tile.branch.cuh": "3f79373e68603691630c7dc38703411456cdf5fa12348d07812323568cdb1e82",
    "historical/exact_base2.txt": "73fb88be756494af9bc66ba45ffcce2c7c29fd4dce89f79b617a303c5ee37124",
    "historical/exact_off2.txt": "e81b7e64313f0c0c48604d2c1e7abc95b0d1f10a49acafee6f5d4718c129a15d",
    "historical/exact_on2.txt": "3f5db9992da0e13a2c6c492ade4dceb6bcb8aad903767471a10b8ab74f3e3155",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def case_hash(text: str, case_id: int) -> str:
    matches = re.findall(rf"^case\s+{case_id}\b.*?\bhash=([0-9a-f]{{16}})\b", text, re.M)
    if len(matches) != 1:
        raise AssertionError(f"expected exactly one output record for case {case_id}")
    return matches[0]


def main() -> None:
    for rel, expected in PINS.items():
        actual = sha(ROOT / rel)
        if actual != expected:
            raise AssertionError(f"SHA-256 mismatch for {rel}: {actual}")

    source_pair = json.loads((H / "source-pair.json").read_text())
    cases = json.loads((H / "cases.json").read_text())
    if source_pair["tile_sha256"] != {
        "base": PINS["historical/fattn-tile.loop-index.cuh"],
        "candidate": PINS["historical/fattn-tile.branch.cuh"],
    }:
        raise AssertionError("source-pair tile identities do not match preserved files")

    harness = (H / "fa_harness.cpp").read_text()
    for case in cases["cases"]:
        needle = (
            f'{{{case["hsk"]}, {case["hsv"]}, {case["nh"]}, {case["nr2"]}, '
            f'{case["kv"]}, {case["nb"]}, {case["nseq"]}, {case["run"]}, '
            f'{case["free"]}, GGML_TYPE_F16, 0.0f, 0.0f, -1}}'
        )
        if needle not in harness:
            raise AssertionError(f"case {case['id']} tuple missing from preserved harness")

    patch = (H / "branch-vs-loop-index.patch").read_text()
    for marker in ("next_live", "if (!KV_live_row", "if (KV_live_row &&", "continue;"):
        if marker not in patch:
            raise AssertionError(f"expected branch transition marker missing: {marker}")

    logs = {
        label: (H / f"exact_{label}2.txt").read_text()
        for label in ("base", "off", "on")
    }
    for case in cases["cases"]:
        observed = {label: case_hash(log, case["id"]) for label, log in logs.items()}
        expected = {label: case[f"{label}_hash"] for label in ("base", "off", "on")}
        if observed != expected:
            raise AssertionError(f"case {case['id']} log hashes do not match cases.json")
        if observed["base"] != observed["on"] or observed["off"] == observed["base"]:
            raise AssertionError(f"case {case['id']} does not match recorded cross-capture relation")

    print("PASS: source, patch, case tuple, and cross-capture hash structure verified")


if __name__ == "__main__":
    main()
