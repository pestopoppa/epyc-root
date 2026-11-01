#!/usr/bin/env python3
"""publish_row.py <spec.json> [--migrate] - the owner's ONE tool: publish an inference row from its launcher + spec.
Thin wrapper over rowflow.py publish (same directory). Spec fields: see rowflow.py docstring."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rowflow  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(rowflow.main(["publish"] + sys.argv[1:]))
