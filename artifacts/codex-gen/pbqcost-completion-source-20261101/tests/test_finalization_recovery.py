"""Real retained PB-QCOST input exercises crash recovery without inference."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CAPTURE = ROOT / 'tests' / 'fixtures' / 'native-capture'


def copy_packet(dst: Path) -> Path:
    shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns('.pytest_cache', '__pycache__'))
    manifest_path = dst / 'CANDIDATE-MANIFEST.json'
    manifest = json.loads(manifest_path.read_text())
    attempt = dst / 'out' / 'attempts' / manifest['id']
    manifest['result_path'] = str(attempt / 'VERDICT.json')
    manifest['completion_binding']['attempt_directory'] = f"out/attempts/{manifest['id']}"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return attempt


def invoke_finalizer(packet: Path, attempt: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, '-B', str(packet / 'finalize_attempt.py'), str(attempt)],
        cwd=packet, capture_output=True, text=True)


def test_actual_capture_recovers_crash_after_verdict_and_after_result():
    raw_fixture = CAPTURE / 'run' / 'pb_qcost_1.jsonl'
    assert hashlib.sha256(raw_fixture.read_bytes()).hexdigest() == '748aea70beda5dab7934247b6d5d76cbe2b6e8e60042b784c3663f3ced871bdb'
    with tempfile.TemporaryDirectory() as td:
        packet = Path(td) / 'packet'
        attempt_dir = copy_packet(packet)
        manifest = json.loads((packet / 'CANDIDATE-MANIFEST.json').read_text())
        source_sha = manifest['source_code_manifest_sha256']
        manifest_sha = hashlib.sha256((packet / 'CANDIDATE-MANIFEST.json').read_bytes()).hexdigest()
        from attempt_state import prepare_attempt, begin_finalization
        attempt = prepare_attempt(attempt_dir, manifest['id'], source_sha, manifest_sha,
            manifest['protocol_hashes']['predeclaration_sha256'], manifest['protocol_hashes']['amendment_sha256'])
        shutil.copytree(CAPTURE / 'run', attempt_dir / 'run')
        for name in ('sibling_summary.json', 'sibling_load.csv'):
            shutil.copy2(CAPTURE / 'out' / name, attempt_dir / name)
        captured_run = json.loads((CAPTURE / 'out' / 'RESULT.json').read_text())
        begin_finalization(attempt_dir / 'ATTEMPT.json', attempt_dir / 'run' / 'pb_qcost_1.jsonl', captured_run['wall_s'])

        # Crash immediately after the real verdict producer writes VERDICT.json.
        producer = subprocess.run([sys.executable, '-B', str(packet / 'verdict_q.py'),
            '--out', str(attempt_dir / 'run'), '--predeclaration', str(packet / 'protocol/PREDECLARATION.md'),
            '--amendment', str(packet / 'protocol/AMENDMENT-confirm-R.md'), '--write', str(attempt_dir / 'VERDICT.json'),
            '--row-id', manifest['id'], '--run-id', attempt['run_id'], '--attempt-id', attempt['run_id'],
            '--source-code-manifest-sha256', source_sha, '--candidate-manifest-sha256', manifest_sha],
            cwd=packet, capture_output=True, text=True)
        assert producer.returncode == 0, producer.stderr + producer.stdout
        generated = json.loads((attempt_dir / 'VERDICT.json').read_text())
        historical = json.loads((ROOT / 'tests/fixtures/full-fail-mape/VERDICT.json').read_text())
        for key in ('label', 'confirm_overall', 'q_overall', 'grade'):
            assert generated[key] == historical[key]
        assert generated['confirm']['4']['refit_request_heldout_mape_pct'] == historical['confirm']['4']['refit_request_heldout_mape_pct']
        recovered = invoke_finalizer(packet, attempt_dir)
        assert recovered.returncode == 0, recovered.stderr + recovered.stdout
        state_path = attempt_dir / 'ATTEMPT.json'
        complete = json.loads(state_path.read_text())
        assert complete['state'] == 'COMPLETE'
        assert complete['input_sha256'] == hashlib.sha256((attempt_dir / 'run/pb_qcost_1.jsonl').read_bytes()).hexdigest()
        assert complete['verdict_sha256'] == hashlib.sha256((attempt_dir / 'VERDICT.json').read_bytes()).hexdigest()
        assert complete['result_sha256'] == hashlib.sha256((attempt_dir / 'RESULT.json').read_bytes()).hexdigest()
        gate = subprocess.run([sys.executable, '-B', str(packet / 'completion_check.py')], cwd=packet)
        assert gate.returncode == 0

        # Recreate the exact durable FINALIZING state from the crash point after RESULT but before COMPLETE.
        complete['state'] = 'FINALIZING'
        for key in ('input_sha256', 'verdict_sha256', 'result_sha256'):
            complete.pop(key, None)
        state_path.write_text(json.dumps(complete, indent=2) + '\n')
        stale = json.loads((attempt_dir / 'RESULT.json').read_text())
        stale['run_id'] = 'old-other-attempt'
        (attempt_dir / 'RESULT.json').write_text(json.dumps(stale))
        recovered = invoke_finalizer(packet, attempt_dir)
        assert recovered.returncode == 0, recovered.stderr + recovered.stdout
        repaired = json.loads((attempt_dir / 'RESULT.json').read_text())
        assert repaired['run_id'] == attempt['run_id']
        assert json.loads(state_path.read_text())['state'] == 'COMPLETE'

        # Every file the verdict producer reads is pinned. A changed raw, proof, or sampler input blocks
        # both completion and recovery until the exact captured bytes are restored.
        for rel in ('run/pb_qcost_1.jsonl','run/graphs_proof_ub256.json','run/graphs_proof_ub512.json',
                    'run/graphs_proof_ub1024.json','sibling_summary.json','sibling_load.csv'):
            state = json.loads(state_path.read_text()); state['state'] = 'FINALIZING'
            for key in ('input_sha256','verdict_sha256','result_sha256'):
                state.pop(key, None)
            state_path.write_text(json.dumps(state))
            target = attempt_dir / rel
            original = target.read_bytes()
            target.chmod(0o644)
            target.write_bytes(original + b'\n')
            gate = subprocess.run([sys.executable, '-B', str(packet / 'completion_check.py')], cwd=packet)
            assert gate.returncode != 0, rel
            refused = invoke_finalizer(packet, attempt_dir)
            assert refused.returncode != 0, rel
            target.write_bytes(original)
            recovered = invoke_finalizer(packet, attempt_dir)
            assert recovered.returncode == 0, recovered.stderr + recovered.stdout
            assert json.loads(state_path.read_text())['state'] == 'COMPLETE'
        gate = subprocess.run([sys.executable, '-B', str(packet / 'completion_check.py')], cwd=packet)
        assert gate.returncode == 0
