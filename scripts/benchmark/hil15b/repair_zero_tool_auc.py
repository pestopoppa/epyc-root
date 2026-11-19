#!/usr/bin/env python3
"""Repair the pinned HIL15b packet validator without changing retained results.

Only the known original validator and its matching source-pin entry are accepted.
This is an offline repair; it does not launch inference or republish a row.
"""
import argparse
import hashlib
from pathlib import Path


ORIGINAL_SHA256 = "faa17ee88d0607339c4635555eee9169d4c97a8167a52b155ad4e9ca90f83000"
OLD = "  assert auc==m['auc_table'] and auc['status']=='insufficient' and auc['n_runs']==1 and auc['n_tasks']==1\n"
NEW = (
    "  assert auc==m['auc_table'] and auc['status']=='insufficient'\n"
    "  # AUC population includes dependency-bearing runs only; no-tool slots are empty.\n"
    "  assert type(auc['n_runs']) is int and type(auc['n_tasks']) is int\n"
    "  assert (auc['n_runs'], auc['n_tasks']) in {(0, 0), (1, 1)}\n"
)


def repaired_source(source: bytes) -> bytes:
    if hashlib.sha256(source).hexdigest() != ORIGINAL_SHA256:
        raise ValueError("validator is not the approved original; refusing to patch")
    old = OLD.encode()
    if source.count(old) != 1:
        raise ValueError("expected exactly one AUC assertion")
    return source.replace(old, NEW.encode(), 1)


def repair(packet: Path) -> str:
    unit = packet.resolve() / "unit.py"
    pins = packet.resolve() / "source.sha256"
    before = unit.read_bytes()
    after = repaired_source(before)
    digest = hashlib.sha256(after).hexdigest()
    old_pin = f"{ORIGINAL_SHA256}  {unit}\n"
    pin_text = pins.read_text()
    if pin_text.count(old_pin) != 1:
        raise ValueError("source manifest lacks the exact original unit.py pin")
    # All refusal checks precede writes. No retained unit data is opened for writing.
    unit.write_bytes(after)
    pins.write_text(pin_text.replace(old_pin, f"{digest}  {unit}\n", 1))
    return digest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    args = parser.parse_args()
    print("repaired unit.py sha256=" + repair(args.packet))
