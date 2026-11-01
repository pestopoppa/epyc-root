"""Exercise the actual verdict_q CLI's source-bound producer metadata offline."""
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from completion_check import complete_verdict
from attempt_state import begin_finalization, prepare_attempt
from finalize_attempt import finalize

def test_actual_producer_emits_bound_not_run_record_and_consumer_rejects_it():
    manifest = json.loads((ROOT / 'CANDIDATE-MANIFEST.json').read_text())
    source_sha = manifest['source_code_manifest_sha256']
    candidate_sha = hashlib.sha256((ROOT / 'CANDIDATE-MANIFEST.json').read_bytes()).hexdigest()
    run_id = manifest['id'] + '-offline-producer-test'
    pre = ROOT / 'protocol' / 'PREDECLARATION.md'
    amend = ROOT / 'protocol' / 'AMENDMENT-confirm-R.md'
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / 'run'; out.mkdir()
        (out / 'pb_qcost_1.jsonl').write_text('')
        fixture = ROOT / 'tests' / 'fixtures' / 'native-capture'
        for name in ('graphs_proof_ub256.json','graphs_proof_ub512.json','graphs_proof_ub1024.json'):
            shutil.copy2(fixture / 'run' / name, out / name)
        for name in ('sibling_summary.json','sibling_load.csv'):
            shutil.copy2(fixture / 'out' / name, out.parent / name)
        verdict_path = Path(td) / 'VERDICT.json'
        proc = subprocess.run([sys.executable, '-B', str(ROOT / 'verdict_q.py'),
            '--out', str(out), '--predeclaration', str(pre), '--amendment', str(amend),
            '--write', str(verdict_path), '--row-id', manifest['id'], '--run-id', run_id,
            '--attempt-id', run_id, '--source-code-manifest-sha256', source_sha,
            '--candidate-manifest-sha256', candidate_sha], cwd=ROOT, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr + proc.stdout
        # A sealed producer may not read a sampler directory different from the six files it hashes.
        override_path = Path(td) / 'override-VERDICT.json'
        override = subprocess.run([sys.executable, '-B', str(ROOT / 'verdict_q.py'),
            '--out', str(out), '--predeclaration', str(pre), '--amendment', str(amend),
            '--sibling-dir', str(Path(td) / 'alternate-siblings'), '--write', str(override_path),
            '--row-id', manifest['id'], '--run-id', run_id, '--attempt-id', run_id,
            '--source-code-manifest-sha256', source_sha, '--candidate-manifest-sha256', candidate_sha],
            cwd=ROOT, capture_output=True, text=True)
        assert override.returncode == 64
        assert not override_path.exists()
        v = json.loads(verdict_path.read_text())
        assert v['row_id'] == manifest['id']
        assert v['run_id'] == run_id
        assert v['source_code_manifest_sha256'] == source_sha
        assert v['candidate_manifest_sha256'] == candidate_sha
        assert v['phases_done'] == []
        assert v['label'] == 'NOT_RUN'
        assert set(v['verdict_inputs_sha256']) == {'run/pb_qcost_1.jsonl','run/graphs_proof_ub256.json',
            'run/graphs_proof_ub512.json','run/graphs_proof_ub1024.json','sibling_summary.json','sibling_load.csv'}
        input_sha = hashlib.sha256((out / 'pb_qcost_1.jsonl').read_bytes()).hexdigest()
        input_path = str(out / 'pb_qcost_1.jsonl')
        run = {'status':'COMPLETE','partial':False,'exit_code':0,'cleanup_verified':True,
               'smoke':False,'protocol_requests':66,'coefficient_grade':'mechanical VERDICT.json',
               'row_id':manifest['id'],'run_id':run_id,'attempt_id':run_id,
               'source_code_manifest_sha256':source_sha,'candidate_manifest_sha256':candidate_sha,
               'input_path':input_path,'input_sha256':input_sha,
               'verdict_path':str(verdict_path),
               'predeclaration_sha256':manifest['protocol_hashes']['predeclaration_sha256'],
               'amendment_sha256':manifest['protocol_hashes']['amendment_sha256'],
               'verdict_sha256':hashlib.sha256(verdict_path.read_bytes()).hexdigest()}
        result_bytes = (json.dumps(run, indent=2) + '\n').encode()
        result_sha = hashlib.sha256(result_bytes).hexdigest()
        attempt = {'row_id':manifest['id'],'run_id':run_id,'attempt_id':run_id,'state':'COMPLETE',
                   'source_code_manifest_sha256':source_sha,'candidate_manifest_sha256':candidate_sha,
                   'input_path':input_path,'verdict_path':str(verdict_path),
                   'input_sha256':input_sha,'verdict_sha256':run['verdict_sha256'],
                   'result_sha256':result_sha}
        consumer_manifest = {**manifest,'result_path':str(verdict_path)}
        assert not complete_verdict(v,run,attempt,consumer_manifest,
            verdict_sha256=run['verdict_sha256'],result_sha256=result_sha,input_sha256=input_sha,
            source_code_manifest_sha256=source_sha,candidate_manifest_sha256=candidate_sha,
            predeclaration_sha256=manifest['protocol_hashes']['predeclaration_sha256'],
            amendment_sha256=manifest['protocol_hashes']['amendment_sha256'],
            expected_input_path=input_path,expected_verdict_path=str(verdict_path),
            verdict_inputs_sha256=None)


def test_finalizer_recovers_crash_after_verdict_or_result_without_trusting_mixed_markers():
    manifest = json.loads((ROOT / 'CANDIDATE-MANIFEST.json').read_text())
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / 'attempt'
        attempt = prepare_attempt(out, manifest['id'], manifest['source_code_manifest_sha256'],
            hashlib.sha256((ROOT / 'CANDIDATE-MANIFEST.json').read_bytes()).hexdigest(),
            manifest['protocol_hashes']['predeclaration_sha256'], manifest['protocol_hashes']['amendment_sha256'])
        raw = out / 'run' / 'pb_qcost_1.jsonl'; raw.parent.mkdir(); raw.write_text('')
        fixture = ROOT / 'tests' / 'fixtures' / 'native-capture'
        for name in ('graphs_proof_ub256.json','graphs_proof_ub512.json','graphs_proof_ub1024.json'):
            shutil.copy2(fixture / 'run' / name, out / 'run' / name)
        for name in ('sibling_summary.json','sibling_load.csv'):
            shutil.copy2(fixture / 'out' / name, out / name)
        begin_finalization(out / 'ATTEMPT.json', raw, 1.25)
        # First recovery writes the actual producer's NOT_RUN verdict, then refuses completion.
        assert not finalize(out)
        v = json.loads((out / 'VERDICT.json').read_text())
        assert v['run_id'] == attempt['run_id'] and v['label'] == 'NOT_RUN'
        assert json.loads((out / 'ATTEMPT.json').read_text())['state'] == 'FINALIZING'
        # Simulate a crash after a mixed/stale RESULT write. Recovery re-derives verdict from the pinned input,
        # and the finalizer cannot promote the mixed pair to COMPLETE.
        (out / 'RESULT.json').write_text(json.dumps({'run_id':'other-attempt','status':'COMPLETE'}))
        assert not finalize(out)
        assert json.loads((out / 'RESULT.json').read_text())['run_id'] == 'other-attempt'
        assert json.loads((out / 'ATTEMPT.json').read_text())['state'] == 'FINALIZING'
