#!/usr/bin/env python3
"""Require exact functional APP Git trees and clean relevant paths."""
import json
from pathlib import Path
import subprocess
import sys

D = Path(__file__).resolve().parent
pins = json.loads((D / 'SOURCE-PINS.json').read_text())
repo = pins['repo']
paths = list(pins['functional_git_trees'])
head = subprocess.check_output(['git','-C',repo,'rev-parse','HEAD'], text=True).strip()
for path, expected in pins['functional_git_trees'].items():
    actual = subprocess.check_output(['git','-C',repo,'rev-parse','HEAD:'+path], text=True).strip()
    if actual != expected:
        raise SystemExit(f'functional source drift {path}: {actual} != {expected}')
dirty = subprocess.check_output(['git','-C',repo,'status','--porcelain','--',*paths], text=True)
if dirty:
    raise SystemExit('dirty functional source paths: '+dirty[:300])
print(head)
