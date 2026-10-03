#!/usr/bin/env python3
"""Exact-once text replacement; aborts on 0 or >1 matches. Usage:
   edit.py <file> <old-file> <new-file>
"""
import sys
from pathlib import Path

target, old_p, new_p = map(Path, sys.argv[1:4])
src = target.read_text(encoding="utf-8")
old = old_p.read_text(encoding="utf-8")
new = new_p.read_text(encoding="utf-8")
n = src.count(old)
if n != 1:
    sys.exit(f"ABORT: {target}: anchor matched {n} times (need exactly 1)")
target.write_text(src.replace(old, new), encoding="utf-8")
print(f"edited {target}")
