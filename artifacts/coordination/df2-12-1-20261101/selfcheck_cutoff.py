#!/usr/bin/env python3
"""Model-free forced-deadline refusal check; never a keeper-issued receipt."""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / 'fixture-cutoff-v4'
OUT.mkdir(exist_ok=True)
env = {**os.environ, 'FILLER_RESULTS_DIR': str(OUT), 'WS58_QUAL_PROOF': str(OUT / 'proof.json'),
       'FILLER_QUAL_PHASE': 'cutoff', 'FILLER_DEADLINE': '0'}
run = subprocess.run([sys.executable, str(ROOT / 'qual_fixture.py'), '--mode', 'model-free'],
                     env=env, check=False)
proof = json.loads((OUT / 'proof.json').read_text())
assert run.returncode == 75 and proof['partial'] is True and proof['deadline_reached'] is True
print('forced deadline partial rc75 proof PASS; synthetic deadline only')
