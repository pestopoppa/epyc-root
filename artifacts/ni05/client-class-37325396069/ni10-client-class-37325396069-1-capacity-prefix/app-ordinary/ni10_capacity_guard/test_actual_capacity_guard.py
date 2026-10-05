from pathlib import Path
import subprocess
import sys


APP_ROOT = Path(__file__).resolve().parents[1]


def test_actual_runner_capacity_guard_refuses_import_before_serving():
    result = subprocess.run(
        [sys.executable, "-c", "import scripts.server.stack_manifest"],
        cwd=APP_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode != 0, "actual runner unexpectedly passed serving-capacity import"
    assert "Declared serving_shape lineup does not fit the hardware" in output, output
    assert "device host (CPU RAM) OVERSUBSCRIBED" in output, output
