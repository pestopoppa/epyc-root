#!/usr/bin/env python3
"""Model-free predicate regression: two-phase producer and all-identity closure."""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile

from df2_parity import phase_requests
from run_role import phase_specs

ROOT = pathlib.Path(__file__).resolve().parent
PRED = ROOT / 'complete_df2.py'
MANIFEST = ROOT / 'PROMPTS.json'


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


with tempfile.TemporaryDirectory(prefix='df2-complete-model-free-', dir=ROOT) as temp:
    root = pathlib.Path(temp)
    result_root = root / 'results'
    normal = result_root / 'normal/QUAL-RESULT.json'
    normal.parent.mkdir(parents=True)
    normal.write_text('{"synthetic":true}\n')
    proof = root / 'proof-normal.json'
    proof.write_text(json.dumps({'result_writer': {'ok': True, 'result_path': str(normal),
                                                  'sha256': sha(normal)}}))
    argv = [sys.executable, str(PRED), '--shape', 'frontdoor_mtp', '--out', str(root),
            '--manifest', str(MANIFEST)]
    env = dict(os.environ, FILLER_QUAL_PHASE='normal', FILLER_RESULTS_DIR=str(result_root),
               WS58_QUAL_PROOF=str(proof))
    if subprocess.run(argv, env=env, check=False).returncode:
        raise RuntimeError('normal producer predicate refused bound result')
    (result_root / 'cutoff').mkdir()
    (result_root / 'cutoff/QUAL-RESULT.json').write_text('{"synthetic":"cutoff"}\n')
    if subprocess.run(argv, env=env, check=False).returncode:
        raise RuntimeError('cutoff overwrote accepted normal producer')
    normal.write_text('{"synthetic":false}\n')
    if subprocess.run(argv, env=env, check=False).returncode == 0:
        raise RuntimeError('normal producer hash drift accepted')
    env.pop('FILLER_QUAL_PHASE')
    (root / 'TERMINAL.json').write_text(json.dumps({'state': 'COMPLETE', 'shape': 'frontdoor_mtp',
                    'manifest_sha256': sha(MANIFEST)}))
    planned = [(phase,c,request_id) for phase,c,_np,_spec in phase_specs()
               for request_id,_prompt in phase_requests(json.loads(MANIFEST.read_text()),phase,c)]
    if len(planned) != 152 or len(set(planned)) != 152:
        raise RuntimeError('fixture identity set is not the frozen 152-role protocol')
    identities = []
    for i, (phase,c,request_id) in enumerate(planned):
        status = 'error' if i == 151 else 'ok'
        folder = root / f'{phase}-c{c}/responses/BELIEF-WRITE'
        folder.mkdir(parents=True, exist_ok=True)
        binding = folder / 'NATIVE-BINDING.json'
        if not binding.exists():
            binding.write_text(json.dumps({'server_drain_pass': True}))
        responses = folder.parent
        wire = responses / 'wire'
        wire.mkdir(exist_ok=True)
        response = responses / (request_id + '.response.json')
        request = wire / (request_id + '.completion.request.bin')
        status_file = wire / (request_id + '.completion.wire.json')
        response.write_text(json.dumps({'status':status,'id':request_id}))
        request.write_bytes(b'{"prompt":"synthetic"}')
        status_file.write_text(json.dumps({'http_status':503 if status == 'error' else 200}))
        record = {'status': status, 'response_record_sha256':sha(response),
                  'completion_request_sha256':sha(request), 'completion_wire_sha256':sha(status_file),
                  'error':'simulated HTTP 503 with raw wire' if status == 'error' else None}
        path = folder / (request_id + '.json')
        path.write_text(json.dumps(record))
        identities.append({'phase':phase,'c':c,'request_id':request_id,
                           'status':status,'record_sha256':sha(path),
                           'native_binding_sha256':sha(binding)})
    closure = {'status':'COMPLETE','shape':'frontdoor_mtp','manifest_sha256':sha(MANIFEST),
               'planned_request_count':152,'identities':identities}
    (root / 'BELIEF-ROLE-CLOSURE.json').write_text(json.dumps(closure))
    if subprocess.run(argv, env=env, check=False).returncode:
        raise RuntimeError('all-attempted 152-identity synthetic closure, including HTTP error, refused')
    closure['identities'][-1] = dict(closure['identities'][0])
    (root / 'BELIEF-ROLE-CLOSURE.json').write_text(json.dumps(closure))
    if subprocess.run(argv, env=env, check=False).returncode == 0:
        raise RuntimeError('duplicated role identity hid one missing planned request')
    closure['identities'][-1] = identities[-1]
    closure['identities'][-1]['native_binding_sha256'] = None
    (root / 'BELIEF-ROLE-CLOSURE.json').write_text(json.dumps(closure))
    if subprocess.run(argv, env=env, check=False).returncode == 0:
        raise RuntimeError('missing final native binding accepted')
    print('normal SHA, all 152 planned identities incl HTTP error, duplicate/missing and unbound refusals PASS; MODEL_FREE only')
