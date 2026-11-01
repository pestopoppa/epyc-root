#!/usr/bin/env python3
"""Model-free check: a child outliving its launcher remains in the owned outer PGID."""
from __future__ import annotations

import json
import os
import pathlib
import signal
import subprocess
import sys
import time


OUTER = '''import os, subprocess, json
p = subprocess.Popen(["sleep", "30"])
print(json.dumps({"child": p.pid, "outer_pgid": os.getpgrp()}), flush=True)
'''
outer = subprocess.Popen([sys.executable, '-c', OUTER], stdout=subprocess.PIPE,
                         text=True, start_new_session=True)
line = outer.stdout.readline()
claim = json.loads(line)
outer.wait(timeout=5)
child = claim['child']
pgid = claim['outer_pgid']
assert pgid == outer.pid and os.getpgid(child) == pgid
birth = (pathlib.Path('/proc') / str(child) / 'stat').read_text().split()[21]
try:
    os.killpg(pgid, signal.SIGTERM)
    for _ in range(100):
        stat = pathlib.Path('/proc') / str(child) / 'stat'
        if not stat.exists() or stat.read_text().split()[2] == 'Z':
            break
        time.sleep(0.02)
    else:
        os.killpg(pgid, signal.SIGKILL)
        raise AssertionError('child survived captured group TERM')
finally:
    stat = pathlib.Path('/proc') / str(child) / 'stat'
    if stat.exists() and stat.read_text().split()[2] != 'Z':
        os.kill(child, signal.SIGKILL)
print(json.dumps({'model_free': True, 'outer_pid': outer.pid, 'child_pid': child,
                  'child_birth': birth, 'same_captured_pgid': True, 'child_running_after_drain': False}))
