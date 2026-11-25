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


def test_missing_stage_still_reports_every_step(tmp_path):
    script = Path(__file__).resolve().parents[1] / 'rowflow/canary_ak_pipeline.sh'
    env = dict(os.environ, STAGE=str(tmp_path / 'missing'))
    result = subprocess.run([str(script)], text=True, capture_output=True, timeout=115, env=env)
    lines = result.stdout.splitlines()
    assert len(lines) == 13, result.stdout + result.stderr
    assert all(line.startswith(f'CANARY C{i} ') for i, line in enumerate(lines)), result.stdout
    assert any(' FAIL' in line for line in lines), result.stdout
    assert result.returncode == 1, result.stdout + result.stderr
