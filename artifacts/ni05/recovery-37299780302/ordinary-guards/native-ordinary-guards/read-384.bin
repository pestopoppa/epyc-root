"""Retain strict GPU store refusal independently of off-host policy fixtures."""

from pathlib import Path
import subprocess
import sys


def test_fresh_gpu_lane_import_refuses_missing_store(tmp_path):
    missing_store = tmp_path / "absent-kernel-store"
    code = """
from pathlib import Path
import sys
from src.registry import kernel_paths
kernel_paths.PRODUCTION_ROOT = Path(sys.argv[1])
assert not kernel_paths.PRODUCTION_ROOT.exists()
try:
    from scripts.server import gpu_shadow_lane
except kernel_paths.KernelPathError as exc:
    assert "kernel backend 'gpu'" in str(exc)
    assert 'missing or dangling' in str(exc)
else:
    raise AssertionError('GPU lane import must refuse an absent kernel store')
assert not kernel_paths.PRODUCTION_ROOT.exists()
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(missing_store)],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
