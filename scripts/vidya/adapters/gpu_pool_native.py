"""Prospective GPU pool capture, deliberately unregistered; native history has no hook.

Call begin() before a future run and finish() only in the native result writer.
No benchmark launch, ladder, protocol invention, or historical conversion here.
"""
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import re
import secrets
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts' / 'vidya'))
from claim_tuple import ClaimTuple, ProjectionError

SCHEMA = 'epyc.vidya.gpu_pool_capture.v1'
SOURCE_KIND = 'gpu-pool-native'
ADAPTER_ID = 'vidya.adapters.gpu_pool_native/v1'
AUTHORITY = 'measurement'
NATIVE = 'epyc.model_free_backend_correctness.v1'
FAMILIES = {'matmul': {'MUL_MAT', 'MUL_MAT_ID'},
            'attention': {'ROPE', 'SOFT_MAX', 'FLASH_ATTN_EXT'},
            'elementwise': {'ADD', 'MUL', 'SCALE', 'NORM', 'RMS_NORM', 'SUM', 'SUM_ROWS'}}
LIMIT = 'Candidate-local native reference counts only; source dirty state and shim provenance remain exactly as recorded; no performance, release, production, reproducibility, or clean-source warrant.'

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def now():
    return datetime.now(timezone.utc).isoformat()

def timestamp(value):
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.utcoffset() is None:
            raise ValueError('naive time')
        return parsed
    except (TypeError, ValueError):
        raise ProjectionError('invalid timezone-aware capture timestamp') from None


def validate_request(request):
    if not isinstance(request, dict) or set(request) != {
            'schema', 'family', 'row_id', 'started_utc', 'invocation_token',
            'identity', 'selected_ops', 'limits', 'producer'}:
        raise ProjectionError('invalid prospective request shape')
    if request['schema'] != SCHEMA or request['limits'] != LIMIT:
        raise ProjectionError('foreign capture or broadened authority')
    producer = request['producer']
    if not isinstance(producer, dict) or set(producer) != {'path', 'sha256'} or file_sha(producer['path']) != producer['sha256']:
        raise ProjectionError('producer source changed')
    family, selected = request['family'], request['selected_ops']
    if not isinstance(family, str) or family not in FAMILIES:
        raise ProjectionError('unknown operator family')
    if not isinstance(selected, list) or not selected or any(not isinstance(x, str) for x in selected) or len(selected) != len(set(selected)) or not set(selected) <= FAMILIES[family]:
        raise ProjectionError('unknown or duplicate native operator selection')
    if not isinstance(request['row_id'], str) or not re.fullmatch(r'ni-gpu-pool-' + family + r'-[0-9]{8}-v1', request['row_id']):
        raise ProjectionError('foreign family/row binding')
    if not isinstance(request['invocation_token'], str) or not re.fullmatch(r'[a-f0-9]{32}', request['invocation_token']):
        raise ProjectionError('missing prospective invocation identity')
    timestamp(request['started_utc'])
    identity = request['identity']
    if not isinstance(identity, dict) or set(identity) != {'source', 'artifacts', 'shim'}:
        raise ProjectionError('exact source/artifacts/shim identity required')
    source, artifacts, shim = (identity[k] for k in ('source', 'artifacts', 'shim'))
    if not isinstance(source, dict) or not isinstance(source.get('commit'), str) or not re.fullmatch(r'[a-f0-9]{40}', source['commit']) or source.get('removed_worktree_dirty_state') not in ('UNKNOWN', 'CLEAN', 'DIRTY'):
        raise ProjectionError('source commit and explicit native dirty state required')
    if not isinstance(artifacts, list) or not artifacts or not isinstance(shim, dict):
        raise ProjectionError('native candidate identity incomplete')
    for artifact in [*artifacts, shim]:
        if not isinstance(artifact, dict) or not isinstance(artifact.get('path'), str) or not artifact['path'] or not isinstance(artifact.get('sha256'), str) or not re.fullmatch(r'[a-f0-9]{64}', artifact['sha256']):
            raise ProjectionError('artifact/shim path and digest required')
    if not isinstance(shim.get('original_source_digest_receipt'), str) or not re.fullmatch(r'[a-f0-9]{64}', shim['original_source_digest_receipt']) or type(shim.get('later_recreated_source_matches_receipt')) is not bool:
        raise ProjectionError('explicit native shim provenance required')


def begin(family, row_id, identity, selected_ops, *, producer):
    """Producer calls BEFORE invocation; identity contains source/artifacts/shim.

    A future attention writer must first emit the complete native object; its old
    bare list is not upgraded. Tokens are binding identifiers, not attestation.
    """
    request = {'schema': SCHEMA, 'family': family, 'row_id': row_id,
               'started_utc': now(), 'invocation_token': secrets.token_hex(16),
               'identity': copy.deepcopy(identity), 'selected_ops': copy.deepcopy(selected_ops),
               'limits': LIMIT, 'producer': {'path': str(Path(producer).resolve()), 'sha256': file_sha(Path(producer).resolve())}}
    validate_request(request)
    return request

def file_sha(path):
    path = Path(path)
    if not path.is_absolute() or not path.is_file():
        raise ProjectionError('absolute existing evidence file required')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def log_counts(run):
    path = Path(run['log'])
    if file_sha(path) != run.get('log_sha256'):
        raise ProjectionError('raw log changed or missing digest')
    text = re.sub(r'\x1b\[[0-9;]*m', '', path.read_text())
    header = 'ARGV ' + json.dumps(run['argv'])
    if not text.splitlines() or text.splitlines()[0] != header:
        raise ProjectionError('log argv does not bind native invocation')
    lines = [line for line in text.splitlines() if line.startswith('  ' + run['op'] + '(')]
    passed = sum(line.endswith('OK') for line in lines)
    unsupported = sum('not supported' in line for line in lines)
    failed = [line for line in lines if not line.endswith('OK') and 'not supported' not in line]
    if (len(lines), passed, unsupported, failed) != (run['observed'], run['passed'], run['unsupported'], run['failed']):
        raise ProjectionError('native counts disagree with raw log')


def finish(request, native):
    """Called at write side, never by a historical reader."""
    result = {'capture': copy.deepcopy(request), 'native': copy.deepcopy(native), 'ended_utc': now()}
    result['sha256'] = digest(result)
    project(result)  # fail closed before persistence
    return result

def project(record):
    if not isinstance(record, dict) or 'capture' not in record:
        return []  # includes all pre-hook native carriers
    if set(record) != {'capture', 'native', 'ended_utc', 'sha256'} or digest({k:v for k,v in record.items() if k != 'sha256'}) != record['sha256']:
        raise ProjectionError('capture digest mismatch')
    request, native = record['capture'], record['native']
    validate_request(request)
    family = request['family']
    if timestamp(request['started_utc']) > timestamp(record['ended_utc']):
        raise ProjectionError('capture time reversed')
    if not isinstance(native, dict) or native.get('schema') != NATIVE or native.get('model_free') is not True or native.get('row_id') != request['row_id']:
        raise ProjectionError('native result does not bind prospective request')
    if native.get('invocation_token') != request['invocation_token']:
        raise ProjectionError('native writer did not bind prospective invocation token')
    if {k:native.get(k) for k in ('source','artifacts','shim')} != request['identity']:
        raise ProjectionError('native candidate identity drift')
    runs = native.get('runs')
    if not isinstance(runs, list) or not runs:
        raise ProjectionError('no native completed runs')
    selected = request.get('selected_ops')
    if not isinstance(selected,list) or not selected or len(selected) != len(set(selected)) or not set(selected) <= FAMILIES[family]:
        raise ProjectionError('invalid declared selection')
    tuples = []
    for i, run in enumerate(runs):
        if not isinstance(run, dict) or run.get('op') not in selected:
            raise ProjectionError('operator outside producer selection')
        # Explicitly incomplete/failed captures are observations too. Never turn
        # an rc=0 or a pass count into a whole-family correctness verdict.
        for key in ('observed', 'passed', 'unsupported'):
            if type(run.get(key)) is not int or run[key] < 0:
                raise ProjectionError('invalid or missing native count')
        if not isinstance(run.get('failed'),list) or run['observed'] != run['passed'] + run['unsupported'] + len(run['failed']):
            raise ProjectionError('native count partition mismatch')
        if not isinstance(run.get('argv'),list) or not run['argv'] or any(not isinstance(x, str) or not x for x in run['argv']) or not isinstance(run.get('log'),str) or not run['log']:
            raise ProjectionError('native invocation/log identity missing')
        if type(run.get('seed')) is not int or type(run.get('rc')) is not int:
            raise ProjectionError('native terminal/seed identity missing')
        if not all(isinstance(x, str) for x in run['failed']):
            raise ProjectionError('native failed cases must remain explicit')
        argv = run['argv']
        if ('-o' not in argv or argv.index('-o') + 1 >= len(argv)
                or argv[argv.index('-o') + 1] != run['op'] or '--suite-seed' not in argv
                or argv.index('--suite-seed') + 1 >= len(argv)
                or argv[argv.index('--suite-seed') + 1] != str(run['seed'])):
            raise ProjectionError('op/seed disagree with argv')
        log_counts(run)
        claim = f"{request['row_id']} {run['op']} invocation {i} records {run['passed']} native supported passes, {run['unsupported']} unsupported and {len(run['failed'])} failures. {LIMIT}"
        tuples.append(ClaimTuple(measurement_id=f"gpu-pool:{record['sha256']}:{i}",
            metric='native_supported_pass_count', value=run['passed'],
            date=record['ended_utc'], category='CANDIDATE', claim=claim,
            unit='cases', source_kind=SOURCE_KIND,
            applicability={'op':run['op'], 'run_id':request['row_id'], 'scope_basis':'native'},
            extra={'native_run':copy.deepcopy(run), 'candidate_identity':copy.deepcopy(request['identity']),
                   'native_context':copy.deepcopy({k:v for k,v in native.items() if k != 'runs'}),
                   'native_scope':native.get('scope'), 'native_proposition':native.get('proposition'),
                   'native_claim_limits':native.get('claim_limits'), 'limits':LIMIT,
                   'capture_sha256':record['sha256'], 'producer':copy.deepcopy(request['producer'])}))
    return tuples


def write_capture(path, request, native):
    """Native producer invokes after recording terminal output, before assertions.

    No history-path conversion exists. The token binds the producer's own begin()
    request; it is an identifier, never an independent attestation.
    """
    import os
    record = finish(request, native)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        stream.write(json.dumps(record, sort_keys=True, allow_nan=False) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    return record


def read_capture(path):
    """Strict future read; pre-hook native files produce zero tuples."""
    return project(json.loads(Path(path).read_text()))


def frames_for_capture(path, *, as_of):
    from claim_tuple import to_frames
    return [frame for claim in read_capture(path)
            for frame in to_frames(claim, as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY)]
