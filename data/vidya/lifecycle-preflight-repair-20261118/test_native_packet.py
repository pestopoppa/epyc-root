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


def test_original_preflight_refusal_stays_primary():
    import job

    capture = PACKET / "fixtures/original-preflight"
    refusal = job.check_seal_readiness(capture, 78)
    assert refusal["phase"] == "preflight"
    assert "contention matrix is STALE (live topology hash=560d489b" in refusal["reason"]
    assert "fresh_capture" not in refusal["reason"]
    assert "contention matrix is STALE" in (capture / "contention-matrix.txt").read_text()


def test_matrix_pin_requires_validation_fresh_measurement_and_unmodified_capture(tmp_path, monkeypatch):
    from datetime import datetime, timedelta, timezone
    import job
    import pytest

    matrix = tmp_path / "canonical.yaml"
    validator = tmp_path / "validator.py"
    validator.write_text("validator fixture")
    pin = tmp_path / "matrix-pin.json"
    monkeypatch.setattr(job, "MATRIX", matrix)
    monkeypatch.setattr(job, "MATRIX_VALIDATOR", validator)
    monkeypatch.setattr(job, "MATRIX_PIN", pin)
    transcript = "OK: contention matrix is fresh (topology_hash=560d489b)"
    monkeypatch.setattr(job.subprocess, "run", lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, transcript, ""))
    stamp = datetime.now(timezone.utc)
    old_stamp = stamp - timedelta(days=31)
    matrix.write_text(f'measured_at: "{old_stamp.isoformat()}"\ntopology_hash: "560d489bb6df16b9"\n')
    with pytest.raises(ValueError, match="measurement is outside"):
        job.matrix_witness()
    matrix.write_text(f'measured_at: "{stamp.isoformat()}"\ntopology_hash: "560d489bb6df16b9"\n')
    with pytest.raises(ValueError, match="needs owner binding"):
        job.check_matrix_admission()
    job.write(pin, job.matrix_witness())
    witness = job.check_matrix_admission()
    capture = tmp_path / "capture"
    capture.mkdir()
    copied = capture / "contention-matrix.yaml"
    copied.write_bytes(matrix.read_bytes())
    (capture / "contention-matrix.txt").write_text(transcript + "\n")
    job.verify_captured_matrix(capture, witness)
    copied.write_bytes(copied.read_bytes() + b"# drift\n")
    with pytest.raises(ValueError, match="matrix bytes differ"):
        job.verify_captured_matrix(capture, witness)
    matrix.write_bytes(copied.read_bytes())
    with pytest.raises(ValueError, match="drifted"):
        job.check_matrix_admission()


def test_fresh_replay_failure_keeps_fresh_reason(tmp_path):
    import job

    job.write(tmp_path / "capture.json", {"complete": True})
    job.write(tmp_path / "fresh-replay/capture.json", {"complete": False, "failure": "fresh cleanup unproved"})
    assert job.check_seal_readiness(tmp_path, 78) == {"phase": "fresh", "reason": "fresh cleanup unproved"}
    job.write(tmp_path / "fresh-replay/capture.json", {"complete": True})
    assert job.check_seal_readiness(tmp_path, 0) is None
