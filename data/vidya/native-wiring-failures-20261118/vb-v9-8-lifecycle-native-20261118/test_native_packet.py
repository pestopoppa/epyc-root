"""Exercise the packet's strict adapter check on prospective software evidence."""
import json
import subprocess
import sys
from pathlib import Path

PACKET = Path(__file__).resolve().parent
sys.path.insert(0, str(PACKET / "sources/root/tests"))
import test_kernel_promotion_evidence as fixture


def test_native_check_on_prospective_fixture(tmp_path):
    staging = fixture.fixture_pair(tmp_path, prospective=True)
    sealed = tmp_path / "sealed"
    fixture.evidence.seal(staging, sealed)
    result = subprocess.run([sys.executable, "-I", "-B", str(PACKET / "native_check.py"), str(sealed)],
                            capture_output=True, text=True, check=True)
    report = json.loads(result.stdout)
    assert report["units_projected"] == 1 and report["frames_emitted"] == 3 and not report["refused"]
