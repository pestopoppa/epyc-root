"""Prospective dev-harness aggregate capture and projection; no historical backfill.

The producer calls publish_with_beliefs at its publication boundary. The capture binds
only explicitly declared numeric leaves of the privacy-published aggregate. Missing
provenance is never filled in on read. This is diagnostic, with no protocol claim.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'dev_harness'))
import belief_run_custody as custody
import dh_privacy as privacy
from claim_tuple import ClaimTuple, ProjectionError, register

from adapters import _native_sidecar as ns

SCHEMA = 'epyc.vidya.dev_harness_aggregate_capture.v1'
SOURCE_KIND = 'dev-harness-aggregate'
ADAPTER_ID = 'vidya.adapters.dev_harness_aggregate/v1'
AUTHORITY = 'measurement'
SIDECAR_SUFFIX = '.belief.json'
TOKEN = re.compile(r'^[A-Za-z0-9_.:-]{1,128}$')
HEX40 = re.compile(r'^[0-9a-f]{40}$')


def _fail(message):
    raise ProjectionError(message)


def _object(data, label, keys):
    if not isinstance(data, dict) or set(data) != set(keys):
        _fail(f'{label} requires exactly {sorted(keys)}')


def _token(value, label):
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        _fail(f'{label} must be a bounded identifier')


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _leaf(doc, pointer):
    # Only object keys under counts. Array indices, JSON pointer escapes and path
    # traversal are deliberately excluded; native declarations name exact keys.
    if not isinstance(pointer, str) or not pointer.startswith('/counts/'):
        _fail('pointer must select a counts leaf')
    parts = pointer.split('/')[2:]
    if not parts or any(not TOKEN.fullmatch(x) for x in parts):
        _fail('invalid counts pointer')
    node = doc.get('counts')
    for part in parts:
        if not isinstance(node, dict) or part not in node:
            _fail('counts pointer does not exist')
        node = node[part]
    if type(node) not in (int, float) or not math.isfinite(node):
        _fail('counts pointer must select a finite number')
    return node


def _validate(doc, capture):
    try:
        ns.canonical_json(doc)
    except ns.CaptureError as exc:
        _fail(f'noncanonical aggregate: {exc}')
    errors = privacy.validate_aggregate(doc)
    if errors:
        _fail('aggregate privacy validation: ' + '; '.join(errors))
    _object(capture, 'capture', ('schema', 'aggregate_name', 'aggregate_sha256', 'metadata', 'metrics', 'producer_receipts', 'capture_sha256'))
    if capture['schema'] != SCHEMA:
        _fail('foreign or legacy capture schema')
    body = {k: v for k, v in capture.items() if k != 'capture_sha256'}
    if capture['capture_sha256'] != ns.content_hash(body):
        _fail('capture hash mismatch')
    m = capture['metadata']
    _object(m, 'metadata', ('run_id', 'producer', 'declared_code_commit', 'semconv', 'source_schema_keys', 'window_start', 'window_end', 'scope'))
    for k in ('run_id', 'producer', 'semconv'):
        _token(m[k], k)
    if not isinstance(m['declared_code_commit'], str) or not HEX40.fullmatch(m['declared_code_commit']):
        _fail('declared_code_commit requires 40-hex identity')
    scope = m['scope']
    if not isinstance(scope, dict) or set(scope) - {'backend', 'device', 'model_file'}:
        _fail('scope may carry only native backend, device and model_file')
    for key, value in scope.items():
        _token(value, f'scope.{key}')
    keys = m['source_schema_keys']
    if not isinstance(keys, list) or not keys:
        _fail('source schema keys are required')
    for key in keys:
        _token(key, 'source schema key')
    if not ns.utc_timestamp(m['window_start']) or not ns.utc_timestamp(m['window_end']):
        _fail('window requires timezone-aware timestamps')
    from datetime import datetime
    if datetime.fromisoformat(m['window_start'].replace('Z', '+00:00')) > datetime.fromisoformat(m['window_end'].replace('Z', '+00:00')):
        _fail('window start follows end')
    if not ns.utc_timestamp(doc.get('generated_at')) or not doc.get('rules'):
        _fail('native generated_at and detector rules required')
    receipts = capture['producer_receipts']
    _object(receipts, 'producer_receipts', ('m1_start_sha256', 'm1_finish_sha256', 'm1_source_sha256', 'm2_start_sha256', 'm2_finish_sha256', 'm2_source_sha256'))
    if any(not isinstance(v, str) or not re.fullmatch(r'[0-9a-f]{64}', v) for v in receipts.values()):
        _fail('invalid producer receipt digest')
    metrics = capture['metrics']
    if not isinstance(metrics, list) or not metrics:
        _fail('at least one explicit metric required')
    seen = set()
    for item in metrics:
        _object(item, 'metric', ('pointer', 'metric', 'unit', 'direction', 'category', 'rule_index'))
        for key in ('metric', 'unit'):
            _token(item[key], key)
        if item['category'] not in ('BASELINE', 'CANDIDATE', 'OPTIMUM'):
            _fail('explicit native category required')
        if item['direction'] not in ('higher_better', 'lower_better'):
            _fail('explicit carrier direction required')
        index = item['rule_index']
        if type(index) is not int or index < 0 or index >= len(doc['rules']) or not doc['rules'][index].strip():
            _fail('metric must name an actual detector rule')
        _leaf(doc, item['pointer'])
        identity = (item['pointer'], item['metric'])
        if identity in seen:
            _fail('duplicate metric identity')
        seen.add(identity)


def publish_with_beliefs(doc, dest, *, metadata, metrics, private_root, orchestrator_root, run_dir, declarations_path):
    """Publish through the existing privacy gate, then seal a prospective capture.

    Sidecar metadata is separately checked by the same raw-trace preflight. This
    helper takes producer declarations at publication; never invoke on old files.
    """
    dest = Path(dest)
    if dest.exists() or Path(str(dest) + SIDECAR_SUFFIX).exists():
        _fail('destination already exists; historical capture is forbidden')
    if not isinstance(doc, dict):
        _fail('aggregate must be an object')
    from publish_mining_results import build
    try:
        starts = custody.verify(run_dir, declarations_path)
        declarations = json.loads(Path(declarations_path).read_bytes())
        if declarations != {'metadata': metadata, 'metrics': metrics} or metadata.get('run_id') != starts[0][0]['run_id']:
            _fail('declarations or run identity mismatch')
        m1_names = {str(p.relative_to(run_dir)) for p in (Path(run_dir) / 'm1/aggregates').glob('*.aggregate.json')}
        if not m1_names or 'm1/run.json' not in starts[0][1] or not m1_names <= set(starts[0][1]) or not {'aggregate.json', 'run.json'} <= set(starts[1][1]):
            _fail('native output coverage mismatch')
        if any(json.loads((Path(run_dir) / p).read_bytes()).get('run_id') != metadata['run_id'] for p in ('m1/run.json', 'run.json')):
            _fail('native run manifest identity mismatch')
        if build(Path(run_dir), allow_partial=True, include_rules=True) != doc:
            _fail('published aggregate differs from producer outputs')
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ProjectionError(f'producer custody refused: {exc}') from exc
    receipts = {}
    for phase, (start, _) in zip(('m1', 'm2'), starts):
        for part in ('start', 'finish'):
            receipts[f'{phase}_{part}_sha256'] = _sha((Path(run_dir) / f'{phase}.{part}.json').read_bytes())
        receipts[f'{phase}_source_sha256'] = start['producer_sha256']
    # Validate declarations before the publication side effect.
    raw = (json.dumps(doc, indent=2, sort_keys=True) + '\n').encode()
    cap = {'schema': SCHEMA, 'aggregate_name': dest.name, 'aggregate_sha256': _sha(raw),
           'metadata': metadata, 'metrics': metrics, 'producer_receipts': receipts}
    cap['capture_sha256'] = ns.content_hash(cap)
    _validate(doc, cap)
    import tempfile
    stage_root = privacy.private_dir(Path(private_root) / 'belief-preflight')
    stage = Path(tempfile.mkdtemp(prefix='capture-', dir=stage_root))
    candidate = privacy.private_write(stage / 'dev-harness-capture.jsonl', json.dumps(cap, sort_keys=True) + '\n')
    report = stage / 'dev-harness-capture-preflight.json'
    if privacy.run_preflight(candidate, report, Path(orchestrator_root)) != 0:
        _fail('capture privacy preflight refused')
    custody.exclusive_write(Path(run_dir) / 'belief-publish.claim.json', custody.encode({'capture_sha256': cap['capture_sha256']}))
    staged_aggregate = stage / 'aggregate.json'
    privacy.publish_aggregate(doc, staged_aggregate, private_root=private_root, orchestrator_root=orchestrator_root)
    staged_bytes = staged_aggregate.read_bytes()
    if _sha(staged_bytes) != cap['aggregate_sha256']:
        _fail('published aggregate changed during capture')
    dest.parent.mkdir(parents=True, exist_ok=True)
    custody.exclusive_write(dest, staged_bytes)
    sidecar = Path(str(dest) + SIDECAR_SUFFIX)
    custody.exclusive_write(sidecar, (json.dumps(cap, sort_keys=True) + '\n').encode())
    return sidecar


def native_rows(path):
    path = Path(path)
    if not path.exists():
        return ()
    try:
        cap = json.loads(path.read_text())
        if not isinstance(cap, dict) or cap.get('schema') != SCHEMA:
            _fail('legacy aggregate or foreign capture: no producer-time capture')
        name = cap.get('aggregate_name')
        if not isinstance(name, str) or not name or Path(name).name != name or path.name != name + SIDECAR_SUFFIX:
            _fail('aggregate namespace mismatch')
        raw = (path.parent / name).read_bytes()
        if _sha(raw) != cap.get('aggregate_sha256'):
            _fail('aggregate digest mismatch')
        doc = json.loads(raw)
        _validate(doc, cap)
        return tuple({'capture': cap, 'doc': doc, 'metric': metric, 'sidecar': str(path), 'aggregate_path': str(path.parent / name)} for metric in cap['metrics'])
    except (OSError, ValueError, TypeError, KeyError) as exc:
        if isinstance(exc, ProjectionError):
            raise
        raise ProjectionError(f'capture refused: {exc}') from exc


@register(SOURCE_KIND)
def project(native):
    if not isinstance(native, dict):
        _fail('native row required')
    rows = native_rows(native['sidecar'])
    row = next((r for r in rows if r['metric'] == native.get('metric')), None)
    if row is None:
        _fail('metric is not present in native capture')
    cap, doc, metric = row['capture'], row['doc'], row['metric']
    identity = ns.content_hash({'capture': cap['capture_sha256'], 'metric': metric})
    return ClaimTuple(measurement_id='dh_' + identity[:24], metric=metric['metric'],
                      value=_leaf(doc, metric['pointer']), date=doc['generated_at'][:10],
                      category=metric['category'], metric_direction=metric['direction'], unit=metric['unit'],
                      claim=f"dev-harness aggregate {cap['metadata']['run_id']}: {metric['metric']} ({metric['pointer']})",
                      protocol_id='', reps=None, attestation_locator=f"{row['aggregate_path']}#{metric['pointer']}",
                      attestation_sha256=cap['aggregate_sha256'], attestation_present=True,
                      attestation_verified=True, source_kind=SOURCE_KIND,
                      applicability=cap['metadata']['scope'],
                      extra={'metadata_basis': 'producer_declared_at_start', 'capture_locator': row['sidecar'], 'producer_receipts': cap['producer_receipts'], 'capture_sha256': cap['capture_sha256'], 'metadata': cap['metadata'],
                             'rule': doc['rules'][metric['rule_index']], 'pointer': metric['pointer'],
                             'diagnostic_only': True})
