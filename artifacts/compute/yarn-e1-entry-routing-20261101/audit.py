#!/usr/bin/env python3
"""Read-only audit of the private E1 split-proof candidate's entry bindings."""
import hashlib
import json
import re
from pathlib import Path

CANDIDATE = Path('/mnt/raid0/llm/tmp/yarn-e1-proof-handoff-20261101/src')
ENGINE15 = Path('/mnt/raid0/llm/worktrees/mains/handoff-yarn/scripts/coordination/rowflow/filler_run15.sh')

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def literal(script, name):
    match = re.search(r'^' + re.escape(name) + r'=(\S+)$', script, re.M)
    if not match:
        raise ValueError(f'missing literal {name}')
    return match.group(1)

def require_binding(script, root, row, engine):
    for key, expected in [('D', str(root)), ('ID', row), ('ENGINE', str(engine))]:
        actual = literal(script, key)
        if actual != expected:
            raise ValueError(f'{key}: expected {expected}, got {actual}')

launch = (CANDIDATE/'launch.sh').read_text()
old_root = Path(literal(launch, 'D'))
old_id = literal(launch, 'ID')
old_engine = Path(literal(launch, 'ENGINE'))
assert old_root != CANDIDATE and (old_root/'run.py').is_file()
assert '"$D/run.py" "$MODE"' in launch and '$D/launch.sh --job' in launch
request = json.loads((CANDIDATE/'qualification/request_manifest.json').read_text())
assert request['runner']['path'] == str(CANDIDATE/'yarn_needle.py')
assert request['runner']['sha256'] == sha(CANDIDATE/'yarn_needle.py')
assert sha(old_root/'yarn_needle.py') != request['runner']['sha256']
source = (CANDIDATE/'SOURCE.sha256').read_text()
assert str(CANDIDATE/'launch.sh') in source and str(CANDIDATE/'yarn_needle.py') in source
run = (CANDIDATE/'run.py').read_text()
assert "ROW_ID = '"+old_id+"'" in run
assert "os.environ.get('WS58_QUAL')" in run and "os.environ['WS58_MANIFEST_PATH']" in run
engine = ENGINE15.read_text()
assert 'FILLER_DRYRUN=1' in engine and 'MINUS the keeper-qualification coupling' in engine
assert old_engine.name == 'filler_run14.sh'
controls = []
for label, root, row, eng in [
    ('wrong candidate directory', CANDIDATE, old_id, old_engine),
    ('fresh row identity', old_root, old_id+'-fresh', old_engine),
    ('v15 engine', old_root, old_id, ENGINE15),
]:
    try:
        require_binding(launch, root, row, eng)
    except ValueError as e:
        controls.append({'control': label, 'rejected': True, 'reason': str(e)})
    else:
        raise AssertionError(f'{label} unexpectedly accepted')
require_binding(launch, old_root, old_id, old_engine)
result = {'candidate':str(CANDIDATE), 'launch_sha256':sha(CANDIDATE/'launch.sh'),
          'declared_launcher_root':str(old_root), 'job_invokes_old_root':True,
          'candidate_runner_sha256':sha(CANDIDATE/'yarn_needle.py'),
          'old_runner_sha256':sha(old_root/'yarn_needle.py'), 'old_row_id':old_id,
          'old_engine':str(old_engine), 'old_engine_sha256':sha(old_engine),
          'v15_engine':str(ENGINE15), 'v15_engine_sha256':sha(ENGINE15),
          'candidate_source_manifest_covers_candidate_files':True,
          'v15_native_contract_differs_from_legacy_ws58_qual':True,
          'negative_controls':controls,
          'scope':'static source routing and negative controls only; no launch, inference, or qualification'}
print(json.dumps(result,indent=2,sort_keys=True))
