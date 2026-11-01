#!/usr/bin/env python3
"""Recover/finalize a successful PB-QCOST attempt using only its pinned raw input."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

D = Path(__file__).resolve().parent
sys.path.insert(0, str(D))
from attempt_state import atomic_json
from completion_check import complete_verdict, producer_labels_consistent
from source_seal import verify_source_seal
from verdict_inputs import hash_verdict_inputs


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finalize(out: Path) -> bool:
    out = Path(out)
    ok, candidate_sha = verify_source_seal(D)
    if not ok:
        return False
    manifest = json.loads((D / 'CANDIDATE-MANIFEST.json').read_text())
    source_sha = manifest['source_code_manifest_sha256']
    state_path = out / 'ATTEMPT.json'
    input_path = out / 'run' / 'pb_qcost_1.jsonl'
    verdict_path = out / 'VERDICT.json'
    result_path = out / 'RESULT.json'
    if any(p.is_symlink() for p in (out, out.parent, out.parent.parent, out / 'run', state_path,
                                    input_path, verdict_path, result_path)):
        return False
    try:
        attempt = json.loads(state_path.read_text())
        finalization = attempt['finalization']
    except (OSError, KeyError, json.JSONDecodeError, TypeError):
        return False
    expected_protocols = manifest.get('protocol_hashes', {})
    if (attempt.get('state') != 'FINALIZING' or
        attempt.get('row_id') != manifest.get('id') or
        attempt.get('source_code_manifest_sha256') != source_sha or
        attempt.get('candidate_manifest_sha256') != candidate_sha or
        attempt.get('predeclaration_sha256') != expected_protocols.get('predeclaration_sha256') or
        attempt.get('amendment_sha256') != expected_protocols.get('amendment_sha256') or
        attempt.get('input_path') != str(input_path) or
        attempt.get('verdict_path') != str(verdict_path) or
        finalization.get('driver_status') != 'COMPLETE' or
        finalization.get('exit_code') != 0 or
        finalization.get('cleanup_verified') is not True or
        finalization.get('input_sha256') != sha(input_path) or
        not finalization.get('verdict_inputs_sha256') or
        hash_verdict_inputs(out) != finalization.get('verdict_inputs_sha256')):
        return False
    run_id = attempt.get('run_id')
    if (not isinstance(run_id, str) or attempt.get('attempt_id') != run_id or
        not run_id.startswith(manifest['id'] + '-')):
        return False
    pre = D / 'protocol' / 'PREDECLARATION.md'
    amend = D / 'protocol' / 'AMENDMENT-confirm-R.md'
    if sha(pre) != expected_protocols.get('predeclaration_sha256') or sha(amend) != expected_protocols.get('amendment_sha256'):
        return False

    # Recompute from the input pinned before FINALIZING. Existing verdict/result files are never trusted.
    proc = subprocess.run([sys.executable, '-B', str(D / 'verdict_q.py'),
        '--out', str(input_path.parent), '--predeclaration', str(pre), '--amendment', str(amend),
        '--write', str(verdict_path), '--row-id', manifest['id'], '--run-id', run_id,
        '--attempt-id', run_id, '--source-code-manifest-sha256', source_sha,
        '--candidate-manifest-sha256', candidate_sha], cwd=D, capture_output=True, text=True)
    if proc.returncode != 0 or not verdict_path.is_file():
        return False
    if hash_verdict_inputs(out) != finalization.get('verdict_inputs_sha256'):
        return False
    verdict = json.loads(verdict_path.read_text())
    input_sha = sha(input_path)
    if (verdict.get('phases_done') != [256, 512, 1024] or
        not producer_labels_consistent(verdict) or
        verdict.get('row_id') != manifest['id'] or verdict.get('run_id') != run_id or
        verdict.get('input_path') != str(input_path) or verdict.get('input_sha256') != input_sha):
        return False

    verdict_sha = sha(verdict_path)
    run = {'status':'COMPLETE','partial':False,'exit_code':0,
        'wall_s':finalization['wall_s'],'smoke':False,'cleanup_verified':True,
        'measurement_instrument':'original wall-clock log-pump, 3 decimal seconds',
        'protocol_requests':66,'coefficient_grade':'mechanical VERDICT.json','error':None,
        'row_id':manifest['id'],'run_id':run_id,'attempt_id':run_id,
        'source_code_manifest_sha256':source_sha,'candidate_manifest_sha256':candidate_sha,
        'input_path':str(input_path),'input_sha256':input_sha,
        'verdict_inputs_sha256':finalization['verdict_inputs_sha256'],
        'verdict_path':str(verdict_path),'verdict_sha256':verdict_sha,
        'predeclaration_sha256':expected_protocols['predeclaration_sha256'],
        'amendment_sha256':expected_protocols['amendment_sha256']}
    atomic_json(result_path, run)
    result_sha = sha(result_path)
    completed = dict(attempt, state='COMPLETE', input_sha256=input_sha,
        verdict_sha256=verdict_sha, result_sha256=result_sha)
    if not complete_verdict(verdict, run, completed, manifest,
            verdict_sha256=verdict_sha, result_sha256=result_sha,
            input_sha256=input_sha, verdict_inputs_sha256=finalization['verdict_inputs_sha256'], source_code_manifest_sha256=source_sha,
            candidate_manifest_sha256=candidate_sha,
            predeclaration_sha256=expected_protocols['predeclaration_sha256'],
            amendment_sha256=expected_protocols['amendment_sha256'],
            expected_input_path=str(input_path), expected_verdict_path=str(verdict_path)):
        return False
    atomic_json(state_path, completed)
    return True

if __name__ == '__main__':
    raise SystemExit(0 if finalize(Path(sys.argv[1])) else 1)
