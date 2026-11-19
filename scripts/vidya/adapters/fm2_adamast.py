"""Prospective FM-2 single-judge diagnoses, never accuracy or outcome claims."""
from __future__ import annotations
import base64
from datetime import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from claim_tuple import ClaimTuple, ProjectionError, register

SOURCE_KIND = 'fm2-adamast'
ADAPTER_ID = 'vidya.adapters.fm2_adamast/v1'
AUTHORITY = 'diagnostic_observation'
CONSUMER = 'coordination.fm2'
LIMIT = ('One judge on one selected frozen trace, descriptive code assignment only; '
         'no accuracy, faithfulness, crosswalk validation or causal fan-out conclusion.')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_bytes())

def units(path):
    path = Path(path)
    return [path] if path.is_file() else []

def native_rows(path):
    try:
        path = Path(path).resolve(strict=True)
        if path.name != 'receipt.json' or path.parent.parent.name != 'units':
            raise ValueError('expected native unit receipt')
        unit = path.parent
        root = unit.parent.parent.parent
        begin = read(unit / 'belief-begin.json')
        row = read(path)
        selection = read(root / 'code/belief-selection.json')
        if begin['schema'] != 'epyc.fm2.belief-begin.v1' or begin['scope'] != 'pilot' or row['scope'] != 'pilot':
            raise ValueError('missing prospective capture or pilot scope')
        uid = row['unit_id']
        if uid != unit.name or uid != begin['unit_id'] or uid not in selection['unit_ids']:
            raise ValueError('unit selection mismatch')
        if (row['runtime'] != begin['runtime'] or begin['packet_sha256'] != sha(root / 'SOURCE.sha256')
                or row['runtime']['packet_sha256'] != begin['packet_sha256']):
            raise ValueError('runtime or source packet mismatch')
        # SOURCE is frozen before the run, and includes selection, producer, taxonomy and all inputs.
        for line in (root / 'SOURCE.sha256').read_text().splitlines():
            digest, relative = line.split('  ', 1)
            file = (root / relative).resolve(strict=True)
            if not file.is_relative_to(root) or sha(file) != digest:
                raise ValueError('source packet mismatch')
        trace = root / 'inputs/traces' / (uid + '.jsonl')
        if sha(trace) != begin['trace_sha256'] or row['trace_sha256'] != begin['trace_sha256']:
            raise ValueError('normalized trace mismatch')
        metadata = read(trace)['metadata']
        if row['stratum'] != metadata['stratum'] or row['source_sha256'] != metadata['source_sha256']:
            raise ValueError('trace source or stratum mismatch')
        runtime = begin['runtime']
        grant_body = base64.b64decode(runtime['grant_body_b64'], validate=True)
        if (not grant_body or hashlib.sha256(grant_body).hexdigest() != runtime['grant_sha256']
                or not runtime['server_argv'] or not runtime['runtime_dsos']):
            raise ValueError('missing runtime or grant identity')
        filler = runtime['filler']
        if Path(runtime['grant_path']).name != filler['FILLER_ID'] + '.grant':
            raise ValueError('grant identity mismatch')
        fields = dict(part.split('=', 1) for part in grant_body.decode('utf-8').split() if '=' in part)
        if ('start' not in fields or 'end' not in fields or 'regions' not in fields
                or datetime.fromisoformat(fields['end'].replace('Z', '+00:00')).timestamp() != int(filler['FILLER_END'])
                or not (datetime.fromisoformat(fields['start'].replace('Z', '+00:00'))
                        <= datetime.fromisoformat(row['started_at'])
                        <= datetime.fromisoformat(fields['end'].replace('Z', '+00:00')))):
            raise ValueError('grant window mismatch')
        if not (datetime.fromisoformat(begin['started_at']) <= datetime.fromisoformat(row['started_at'])
                <= datetime.fromisoformat(row['finished_at'])):
            raise ValueError('capture time order')
        for name, digest in row['artifacts'].items():
            if name not in {'request.json', 'response.json', 'diagnosis.json', 'cli.log'} or sha(unit / name) != digest:
                raise ValueError('artifact mismatch')
        if not row['ok'] or row['status'] != 'valid':
            return ()  # terminal failure remains native and does not become a diagnosis
        if not {'request.json', 'response.json', 'diagnosis.json'} <= row['artifacts'].keys():
            raise ValueError('incomplete artifacts')
        request, response = read(unit / 'request.json'), read(unit / 'response.json')
        req = json.loads(base64.b64decode(request['body_b64'], validate=True))
        resp = json.loads(base64.b64decode(response['body_b64'], validate=True))
        if (request['method'] != 'POST' or not request['url'].startswith('http://127.0.0.1:')
                or response['status'] != 200 or req['model'] != 'local-fm2'
                or req['chat_template_kwargs']['enable_thinking'] is not False
                or resp['choices'][0]['finish_reason'] != 'stop'
                or not resp['choices'][0]['message'].get('content')
                or (resp['choices'][0]['message'].get('reasoning_content') or '').strip()):
            raise ValueError('unusable request or reply')
        if not (datetime.fromisoformat(row['started_at']) <= datetime.fromisoformat(request['sent_at'])
                <= datetime.fromisoformat(response['received_at']) <= datetime.fromisoformat(row['finished_at'])):
            raise ValueError('journal time order')
        replay = Path(__file__).resolve().parents[2] / 'experiments/fm2-adamast/belief_replay.py'
        completed = subprocess.run([sys.executable, '-I', str(replay), str(root), str(unit)],
                                   capture_output=True, text=True, timeout=30, check=False)
        if completed.returncode:
            raise ValueError('native AdaMAST replay or request/trace binding failed')
        replayed = json.loads(completed.stdout)
        diagnosis = read(unit / 'diagnosis.json')
        if diagnosis['schema_version'] != 2 or diagnosis['trace_count'] != 1 or len(diagnosis['diagnoses']) != 1:
            raise ValueError('diagnosis schema')
        d = diagnosis['diagnoses'][0]
        codes = [m['code'] for m in replayed['failure_modes']]
        if (d['trace_id'] != uid or d['none_apply'] is not (not codes)
                or d['judge_metadata']['warnings'] or len(set(codes)) != len(codes)
                or any(c not in {f'MAST-{i}' for i in range(1, 15)} for c in codes)):
            raise ValueError('invalid diagnosis')
        return ({'path': str(path), 'sha256': sha(path), 'unit_id': uid,
                 'stratum': row['stratum'], 'codes': sorted(codes),
                 'date': row['finished_at'][:10], 'trace_sha256': row['trace_sha256']},)
    except (OSError, ValueError, KeyError, TypeError, IndexError, subprocess.SubprocessError) as exc:
        raise ProjectionError(f'{SOURCE_KIND}: {exc}') from exc

@register(SOURCE_KIND)
def project(native):
    if not isinstance(native, dict) or not isinstance(native.get('path'), str) or native not in native_rows(native['path']):
        raise ProjectionError('FM-2 native row does not rederive')
    return ClaimTuple(measurement_id=f"{SOURCE_KIND}:{native['sha256']}",
        metric='fm2_single_judge_diagnosis', value=len(native['codes']), date=native['date'],
        category='CANDIDATE', claim=f"FM-2 judge assigned {native['codes']} to {native['unit_id']} in {native['stratum']}. {LIMIT}",
        protocol_id='', reps=1, reps_basis='one judge call on one selected trace', unit='assigned_codes',
        attestation_path=native['path'], attestation_sha256=native['sha256'],
        attestation_locator=native['path'], attestation_present=True, attestation_verified=True,
        source_kind=SOURCE_KIND, applicability={'consumer': CONSUMER},
        observation={'outcome_native': 'diagnosed', 'outcome_reason': LIMIT},
        extra={'adapter': ADAPTER_ID, 'codes': native['codes'], 'stratum': native['stratum'],
               'trace_sha256': native['trace_sha256']})
