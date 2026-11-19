#!/usr/bin/env python3
"""exit 0 iff the normalized trace set exists and every trace has a judged/<id>.json (the row's --complete-cmd)."""
import pathlib
import sys

out = pathlib.Path(__file__).resolve().parent / "out"
traces = sorted((out / "traces").glob("*.jsonl"))
sys.exit(0 if traces and all((out / "judged" / (t.stem + ".json")).is_file() for t in traces) else 1)
