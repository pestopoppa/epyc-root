"""Strict projection of current retained-fixture replay; no historical capture warrant."""
from __future__ import annotations
import base64
import hashlib
import re
import importlib.util
import json
from pathlib import Path
from typing import Any
from claim_tuple import ClaimTuple, ProjectionError, register, to_frames

SOURCE_KIND = 'nemo-range-join'
ADAPTER_ID = 'vidya.adapters.nemo_range_join/v1'
AUTHORITY = 'diagnostic_observation'
CONSUMER = 'autokernel.nemo_fixture_range_join'
LIMIT = ('Current retained-fixture replay only. Original capture custody, clock identity, '
         'server-token attribution, historical boundaries and GPU behavior remain unknown.')
ROOT = Path(__file__).resolve().parents[3]
FIXTURE_MANIFEST = ROOT / 'data/vidya/nemo-range-wire-20261118/fixture-inputs.json'
FIXTURE_MANIFEST_SHA = '109c588d4b6f3a0357838b79357ad668808ccbeab8a9b24e52ff2ac04af0c8ff'
AUDIT = ROOT / 'docs/reference/autokernel/nemo-fixture-range-join-20261105/audit.py'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def unique(pairs):
    out = {}
    for k, v in pairs:
        if k in out: raise ValueError('duplicate JSON key')
        out[k] = v
    return out

def load_audit():
    spec = importlib.util.spec_from_file_location('nemo_range_audit', AUDIT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def grant_check(grant, cpus, started, ended, base):
    from datetime import datetime
    raw = base64.b64decode(grant['bytes_b64'], validate=True)
    if hashlib.sha256(raw).hexdigest() != grant['sha256'] or grant['copy'] != 'grant.copy' or (base / grant['copy']).read_bytes() != raw:
        raise ValueError('grant custody')
    fields = {}
    for token in raw.decode().split():
        if '=' in token:
            key, value = token.split('=', 1)
            if key in fields: raise ValueError('duplicate grant field')
            fields[key] = value
    def stamp(s): return datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()
    def cpuset(s):
        out = set()
        for item in s.split(','):
            parts = item.split('-')
            if not all(x.isdigit() for x in parts) or len(parts) > 2: raise ValueError('invalid grant CPUs')
            a, b = int(parts[0]), int(parts[-1])
            if b < a or b > 4095: raise ValueError('invalid grant CPUs')
            out.update(range(a, b + 1))
        return out
    allowed = cpuset(fields.get('lock', fields.get('cpus', fields['regions'])))
    if not set(cpus) <= allowed or not stamp(fields['start']) <= stamp(started) <= stamp(ended) <= stamp(fields['end']):
        raise ValueError('grant window or CPU custody')
    if int(grant['deadline']) > stamp(fields['end']) or stamp(ended) > int(grant['deadline']):
        raise ValueError('grant deadline custody')

def verify_fixture_inputs(run):
    raw = FIXTURE_MANIFEST.read_bytes()
    if hashlib.sha256(raw).hexdigest() != FIXTURE_MANIFEST_SHA: raise ValueError('fixture manifest drift')
    manifest = json.loads(raw, object_pairs_hook=unique)
    if str(run.resolve(strict=True)) != manifest['run_dir'] or len(manifest['files']) != 320:
        raise ValueError('fixture manifest identity')
    for name, expected in manifest['files'].items():
        path = run / name
        if not path.resolve(strict=True).is_relative_to(run.resolve(strict=True)) or sha(path) != expected:
            raise ValueError('fixture source drift: ' + name)

def units(path):
    p = Path(path)
    return [p] if p.is_file() else []

def native_rows(path):
    try:
        p = Path(path).resolve(strict=True)
        raw = p.read_bytes()
        record = json.loads(raw, object_pairs_hook=unique, parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
        if set(record) != {'schema','status','mode','started_at','ended_at','grant','cpus','run_dir','source_pins','result','limits'} or record['schema'] != 'nemo.range.replay.v1' or record['status'] != 'complete' or record['limits'] != LIMIT:
            raise ValueError('invalid replay envelope')
        if record['mode'] not in ('publisher_smoke', 'official'): raise ValueError('invalid mode')
        grant_path = record['grant'].get('path', '')
        if not isinstance(grant_path, str) or Path(grant_path).name != record['grant']['id'] + '.grant': raise ValueError('grant path')
        if (record['mode'] == 'official') != (Path(grant_path).parent == Path('/mnt/raid0/llm/tmp/compute-flags/grants')): raise ValueError('grant mode')
        from datetime import datetime
        start = datetime.fromisoformat(record['started_at'].replace('Z','+00:00'))
        end = datetime.fromisoformat(record['ended_at'].replace('Z','+00:00'))
        if start.utcoffset() is None or end.utcoffset() is None or end < start: raise ValueError('invalid replay window')
        if not isinstance(record['grant'], dict) or not all(isinstance(record['grant'].get(k),str) and record['grant'][k] for k in ('id','deadline','stopfile')): raise ValueError('missing grant')
        cpus = record['cpus']
        if not isinstance(cpus,list) or len(cpus)!=4 or any(type(x) is not int or x < 0 for x in cpus) or len(set(cpus))!=4: raise ValueError('invalid affinity')
        grant_check(record['grant'], cpus, record['started_at'], record['ended_at'], p.parent)
        audit = load_audit()
        files = {'audit': AUDIT, 'original_receipt': audit.SOURCE/'RESULT.json',
                 'marker_adapter': audit.SOURCE/'nemo-marker-csv-adapter-20261105/marker_csv.py',
                 'clock_join': audit.SOURCE/'nemo-fixture-clock-join-20261105/fixture_clock_join.py',
                 'writer': ROOT/'scripts/vidya/nemo_range_replay.py', 'adapter': Path(__file__).resolve(),
                 'fixture_manifest': FIXTURE_MANIFEST}
        pins = {role: sha(path) for role, path in files.items()}
        if pins != record['source_pins'] or pins['original_receipt'] != '7d6db4dea6dfed738f1fc2f223a9d9333630e86d4ec4f2bb486da781971fff1e' or pins['marker_adapter'] != '3630ad137abe4b0574554d103d724fa7b45bce6c46871d389bcda4f4c6979ff4' or pins['clock_join'] != 'a44ca3cc0a22b9d24e3597fccafe0aafc031168b148f92c38c167b125cd5e4b3': raise ValueError('source drift')
        receipt = json.loads((audit.SOURCE/'RESULT.json').read_bytes(), object_pairs_hook=unique)
        if receipt.get('status') != 'COMPLETE' or receipt.get('unit_count') != 80 or len(receipt.get('rows',[])) != 80: raise ValueError('source receipt')
        run = Path(record['run_dir']).resolve(strict=True)
        verify_fixture_inputs(run)
        dirs = sorted(run.glob('*-sdk'), key=lambda x:int(x.name.split('-')[0]))
        if [d.name for d in dirs] != [f'{i}-sdk' for i in range(80)]: raise ValueError('run census')
        observed = {}
        for i,d in enumerate(dirs):
            result = audit.audit(d); row = receipt['rows'][i]; arms = [x for x in row['arms'] if x['arm']=='sdk']
            if row['pair'] != i or len(arms)!=1: raise ValueError('receipt pair')
            arm = arms[0]; files = arm['marker_files']
            if arm['status'] != 'PASS' or len(files)!=1 or files[0]['sha256'] != result['input_sha256']['fixture-trace/'+audit.NAMES[0]] or arm['fixture_pids'] != [str(result['fixture_pid'])] or arm['graph_ids'] != [j['graph_correlation_id'] for j in result['joins']]: raise ValueError('receipt identity mismatch')
            observed[d.name] = result
        if observed != record['result']: raise ValueError('replay mismatch')
        return ({'path':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'record':record},)
    except (OSError, ValueError, KeyError, TypeError, ImportError, AttributeError) as exc:
        raise ProjectionError(f'{SOURCE_KIND}: {exc}') from exc

@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native,dict) or not isinstance(native.get('path'),str): raise ProjectionError('invalid native row')
    if native not in native_rows(native['path']): raise ProjectionError('native row does not rederive')
    return current(native)

def current(native):
    r=native['record']; p=native['path']; h=native['sha256']
    return ClaimTuple(measurement_id=f'{SOURCE_KIND}:{h}', metric='fixture_range_join_replay', value=1,
        date=r['ended_at'][:10], category='CANDIDATE', claim=f"{r['mode']} retained 80 SDK fixture runs passed the range join replay. "+LIMIT,
        protocol_id='', reps=80, reps_basis='80 retained SDK fixture runs replayed now', unit='replay_pass_indicator',
        attestation_path=p, attestation_sha256=h, attestation_locator=f'{p}#sha256={h}',
        attestation_present=True, attestation_verified=True, source_kind=SOURCE_KIND,
        applicability={}, observation={'outcome_native':'pass','outcome_reason':LIMIT},
        extra={'adapter':ADAPTER_ID, 'source_pins':r['source_pins'], 'grant':r['grant'], 'cpus':r['cpus'], 'mode':r['mode']})

def emit(path, *, as_of, limit=None):
    return [f for n in native_rows(path)[:limit] for f in to_frames(current(n), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY)]
