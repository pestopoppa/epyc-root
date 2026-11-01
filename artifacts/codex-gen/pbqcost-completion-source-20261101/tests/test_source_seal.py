"""Detached source manifest is checked by producer and consumer entrypoints."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from source_seal import verify_source_seal

def test_candidate_runtime_source_manifest_verifies():
    ok,_=verify_source_seal(ROOT)
    assert ok

def test_source_file_tamper_and_manifest_digest_drift_refuse():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); item=root/'sealed.txt'; item.write_text('original')
        expected=hashlib.sha256(item.read_bytes()).hexdigest()
        source_list=root/'SOURCE-CODE.sha256';source_list.write_text(f'{expected}  sealed.txt\n')
        manifest=root/'CANDIDATE-MANIFEST.json'
        manifest.write_text(json.dumps({'source_code_manifest_sha256':hashlib.sha256(source_list.read_bytes()).hexdigest()}))
        assert verify_source_seal(root)[0]
        item.write_text('tampered')
        assert not verify_source_seal(root)[0]
        item.write_text('original')
        manifest.write_text(json.dumps({'source_code_manifest_sha256':'0'*64}))
        assert not verify_source_seal(root)[0]

def test_launcher_and_run_path_enforce_source_seal_and_attempt_isolation():
    launch=(ROOT/'launch.sh').read_text();run=(ROOT/'run.py').read_text()
    assert 'source_seal.py' in launch
    assert 'verify_source_seal(D)' in run
    assert "D/'out'/'attempts'/row_id" in run
    assert 'D / "out" / "attempts" / str(row_id)' in (ROOT/'completion_check.py').read_text()
