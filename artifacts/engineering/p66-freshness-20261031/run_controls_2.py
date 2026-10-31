#!/usr/bin/env python3
"""Run only after R6 admission under the reviewed process-tree supervisor."""
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent / 'fixture'
os.chdir(root)
sys.path.insert(0, str(root))
import dashboard.panels as panels
import dashboard.loop_status as loop_status
import dashboard.server as server
import pytest
for mod in (panels, loop_status, server):
    path = Path(mod.__file__).resolve()
    if not path.is_relative_to(root.resolve()):
        raise RuntimeError(f'foreign dashboard import: {path}')
    print(f'import {mod.__name__}: {path}', flush=True)
pytest_path = Path(pytest.__file__).resolve()
allowed_site = Path('/mnt/raid0/llm/epyc-orchestrator/.venv/lib/python3.11/site-packages').resolve()
if not pytest_path.is_relative_to(allowed_site):
    raise RuntimeError(f'foreign pytest import: {pytest_path}')
print(f'import pytest: {pytest_path}', flush=True)
args = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
        '--basetemp', str(Path(os.environ['P66_ATTEMPT']) / 'pytest-tmp'),
        'tests/test_dashboard_loop_surface.py::Probe',
        'tests/test_dashboard_panels_redteam.py::NonGatingAlarmTest::test_a_declared_pause_stays_green']
print('argv:', repr(args), flush=True)
raise SystemExit(subprocess.run(args, cwd=root, check=False).returncode)
