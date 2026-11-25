"""The AK pre-deploy canary runs every isolated step without blocking known fixes."""
import os
from pathlib import Path
import subprocess


def test_ak_canary():
    script = Path(__file__).resolve().parents[1] / 'rowflow/canary_ak_pipeline.sh'
    env = dict(os.environ)
    env.pop('STAGE', None)
    env.pop('ORIGIN', None)
    result = subprocess.run([str(script)], text=True, capture_output=True, timeout=115, env=env)
    lines = result.stdout.splitlines()
    assert len(lines) == 13, result.stdout + result.stderr
    for index, line in enumerate(lines):
        assert line.startswith(f'CANARY C{index} '), result.stdout
        assert ' FAIL' not in line, result.stdout
    assert result.returncode == 0, result.stdout + result.stderr
