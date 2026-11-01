"""Attempt identity and terminal-artifact lifecycle for PB-QCOST."""
import json
import os
from pathlib import Path
import uuid

class AttemptRefusal(RuntimeError):
    pass

def atomic_json(path: Path, value: object) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    os.replace(tmp, path)

def prepare_attempt(out: Path, row_id: str, source_sha: str, manifest_sha: str,
                    pre_sha: str, amendment_sha: str) -> dict:
    """Start fresh or resume only a nonterminal attempt; never reopen terminal artifacts."""
    out = Path(out)
    state_path = out / 'ATTEMPT.json'
    if out.is_symlink() or out.parent.is_symlink() or out.parent.parent.is_symlink():
        raise AttemptRefusal('symlinked attempt directory ancestry refused')
    run_dir = out / 'run'
    if run_dir.is_symlink():
        raise AttemptRefusal('symlinked raw-input directory refused')
    terminal_paths = (out / 'VERDICT.json', out / 'RESULT.json')
    if any(p.is_symlink() for p in (state_path, *terminal_paths)):
        raise AttemptRefusal('symlinked attempt state or terminal artifact refused')
    if state_path.exists():
        try:
            attempt = json.loads(state_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise AttemptRefusal(f'unreadable attempt state: {exc}') from exc
        expected = {'row_id': row_id, 'source_code_manifest_sha256': source_sha,
                    'candidate_manifest_sha256': manifest_sha,
                    'predeclaration_sha256': pre_sha, 'amendment_sha256': amendment_sha}
        if any(attempt.get(k) != v for k, v in expected.items()):
            raise AttemptRefusal('existing attempt identity/source pins differ; refusing resume')
        if attempt.get('state') not in {'ACTIVE', 'FINALIZING'}:
            raise AttemptRefusal('terminal or unknown attempt state refuses re-entry')
        if attempt.get('state') == 'ACTIVE' and any(p.exists() for p in terminal_paths):
            raise AttemptRefusal('terminal artifacts without FINALIZING record; refusing stale-result reuse')
        run_id = attempt.get('run_id')
        if not isinstance(run_id, str) or not run_id.startswith(row_id + '-'):
            raise AttemptRefusal('attempt run id malformed')
        if attempt.get('attempt_id') != run_id:
            raise AttemptRefusal('attempt id mismatch')
        return attempt
    if out.exists() and any(out.iterdir()):
        raise AttemptRefusal('unbound files exist in fresh attempt directory')
    out.mkdir(parents=True, exist_ok=True)
    run_id = row_id + '-' + uuid.uuid4().hex
    attempt = {'row_id': row_id, 'attempt_id': run_id, 'run_id': run_id,
               'source_code_manifest_sha256': source_sha,
               'candidate_manifest_sha256': manifest_sha,
               'predeclaration_sha256': pre_sha, 'amendment_sha256': amendment_sha,
               'input_path': str(out / 'run' / 'pb_qcost_1.jsonl'),
               'verdict_path': str(out / 'VERDICT.json'), 'state': 'ACTIVE'}
    atomic_json(state_path, attempt)
    return attempt

def begin_finalization(attempt_path: Path, input_path: Path, wall_s: float) -> dict:
    attempt_path = Path(attempt_path)
    attempt = json.loads(attempt_path.read_text())
    if attempt.get('state') != 'ACTIVE':
        raise AttemptRefusal('only active attempt can enter finalization')
    input_path = Path(input_path)
    if input_path.is_symlink() or not input_path.is_file():
        raise AttemptRefusal('native input missing or symlinked at finalization')
    from verdict_inputs import hash_verdict_inputs, VERDICT_INPUTS
    input_key = 'run/pb_qcost_1.jsonl'
    if input_path != Path(attempt_path.parent / input_key):
        raise AttemptRefusal('input path differs from verdict input contract')
    input_hashes = hash_verdict_inputs(attempt_path.parent)
    if input_hashes is None or set(input_hashes) != set(VERDICT_INPUTS):
        raise AttemptRefusal('one or more verdict input files are missing or symlinked')
    attempt['state'] = 'FINALIZING'
    attempt['finalization'] = {'driver_status':'COMPLETE','exit_code':0,
        'cleanup_verified':True,'wall_s':wall_s,
        'input_sha256':input_hashes[input_key],
        'verdict_inputs_sha256':input_hashes}
    atomic_json(attempt_path, attempt)
    return attempt
