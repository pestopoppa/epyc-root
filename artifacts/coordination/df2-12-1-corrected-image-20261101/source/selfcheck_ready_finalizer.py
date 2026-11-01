#!/usr/bin/env python3
"""Model-free full-role window budget and absent-engine fail-closed checks."""
import pathlib
import subprocess
import sys

from finalize_ready_manifest import phase_budget

ROOT = pathlib.Path(__file__).resolve().parent
needed, minimum, window = phase_budget(12.0, 25.0, 50.0, 600.0)
assert needed == 53*50 + 152*96/12
assert minimum % 60 == window % 60 == 0
assert minimum >= needed and window >= needed + 600
try:
    phase_budget(12.0, 25.0, 24.0, 600.0)
except RuntimeError:
    pass
else:
    raise RuntimeError('underbound fixed phase overhead accepted')
command = [sys.executable, str(ROOT/'finalize_ready_manifest.py'),
           '--role','cpu','--native-token-proof',str(ROOT/'metadata/frontdoor_mtp/RESULT.json'),
           '--rate-evidence',str(ROOT/'metadata/frontdoor_mtp/RESULT.json'),
           '--owner-calibration-receipt',str(ROOT/'metadata/frontdoor_mtp/RESULT.json'),
           '--phase-overhead-bound-s','50','--reserve-s','600',
           '--output-reserve-gib','2']
run = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                     text=True, timeout=10)
if run.returncode != 70 or 'UNREADY:' not in run.stdout:
    raise RuntimeError('unqualified finalization did not fail closed: '+run.stdout)
if (ROOT/'finalization-ready-draft/cpu/FINAL-MANIFEST.json').exists():
    raise RuntimeError('unqualified finalizer wrote a production manifest')
print('53-load window formula and UNREADY refusal PASS; MODEL_FREE only')
