"""Strict projection of producer-sealed LSA MoE pilot timing, never quality."""
from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple, ProjectionError, register

SOURCE_KIND = 'lsa-moe-pilot'
ADAPTER_ID = 'vidya.adapters.lsa_moe_pilot/v1'
AUTHORITY = 'measurement'


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def _number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _sha(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _timing_contract(r, captured, layers, steps, training):
    """Check producer-declared identity, bounds and event joins before timing projection."""
    identity, runtime, model, limits = (r[k] for k in ('identity', 'runtime', 'actual_model', 'limits'))
    hashes = ('weights_sha256', 'config_sha256', 'tokenizer_sha256', 'corpus_sha256',
              'source_sha256', 'producer_sha256', 'capture_module_sha256')
    if not all(isinstance(x, dict) for x in (identity, runtime, model, limits)) or not _text(identity.get('model')) or any(not _sha(identity.get(k)) for k in hashes):
        raise ProjectionError('pilot identity incomplete')
    for key, limit in (('weights_sha256', 'checkpoint_sha256'), ('tokenizer_sha256', 'tokenizer_sha256'), ('corpus_sha256', 'corpus_sha256'), ('source_sha256', 'source_manifest_sha256')):
        if identity[key] != limits.get(limit):
            raise ProjectionError('pilot identity differs from declared inputs')
    if identity['model'] != limits.get('model_id'):
        raise ProjectionError('pilot model differs from declared input')
    integers = ('max_docs', 'max_tokens', 'max_seconds', 'max_queries', 'max_artifact_bytes', 'max_score_cells', 'threads')
    if any(type(limits.get(k)) is not int or limits[k] <= 0 for k in integers) or any(not _number(limits.get(k)) or limits[k] <= 0 for k in ('tau', 'learning_rate')) or type(limits.get('seed')) is not int or any(type(limits.get(k)) is not int or limits[k] < 0 for k in ('sinks', 'window')):
        raise ProjectionError('invalid declared pilot limits')
    texts = ('python', 'platform', 'torch', 'transformers', 'hf_modeling_path', 'hf_rope_utils_path')
    if any(not _text(runtime.get(k)) for k in texts) or any(not _sha(runtime.get(k)) for k in ('hf_modeling_sha256', 'hf_rope_utils_sha256')):
        raise ProjectionError('pilot runtime identity incomplete')
    affinity = runtime.get('cpu_affinity')
    if not isinstance(affinity, list) or not affinity or any(type(n) is not int or n < 0 for n in affinity) or len(set(affinity)) != len(affinity):
        raise ProjectionError('invalid runtime CPU affinity')
    if runtime.get('torch_threads') != limits['threads'] or runtime.get('torch_interop_threads') != 1 or limits['threads'] > len(affinity):
        raise ProjectionError('runtime thread count differs from limits')
    if not _text(model.get('class')) or model.get('devices') != ['cpu'] or not isinstance(model.get('parameter_dtypes'), list) or not model['parameter_dtypes'] or any(not _text(d) for d in model['parameter_dtypes']) or any(model.get(k) != runtime.get(k) for k in ('cpu_affinity', 'torch_threads', 'torch_interop_threads')):
        raise ProjectionError('actual model runtime is incomplete or inconsistent')
    fit, held = r['fit_documents'], r['heldout_documents']
    if any(not isinstance(group, list) or not group or any(not _text(x) for x in group) or len(group) != len(set(group)) for group in (fit, held)) or set(fit) & set(held):
        raise ProjectionError('invalid pilot document splits')
    docs = set(fit) | set(held)
    token_hashes = r['document_token_sha256']
    if len(docs) != r['counts']['eligible_documents'] or len(docs) > limits['max_docs'] or not isinstance(token_hashes, dict) or set(token_hashes) != docs or any(not _sha(x) for x in token_hashes.values()) or len(set(token_hashes.values())) != len(docs):
        raise ProjectionError('pilot document identity or denominator mismatch')
    valid_layers = set(range(3, 40, 4))
    def join(event, *, fit_only=False):
        doc = event.get('document')
        expected = 'fit' if doc in fit else 'heldout' if doc in held else None
        if expected is None or event.get('split') != expected or (fit_only and expected != 'fit'):
            raise ProjectionError('event document or split mismatch')
        return doc
    completed = [join(e) for e in captured]
    if len(set(completed)) != len(completed):
        raise ProjectionError('duplicate completed document')
    layer_keys, layer_artifacts = [], []
    for event in layers:
        doc = join(event)
        layer = event.get('layer')
        if type(layer) is not int or layer not in valid_layers or event.get('token_sha256') != token_hashes[doc] or event.get('artifact') not in r['artifacts']:
            raise ProjectionError('invalid layer capture identity')
        layer_keys.append((doc, layer))
        layer_artifacts.append(event['artifact']['path'])
    if len(set(layer_keys)) != len(layer_keys) or len(set(layer_artifacts)) != len(layer_artifacts) or any({layer for doc, layer in layer_keys if doc == d} != valid_layers for d in completed):
        raise ProjectionError('duplicate or incomplete document layers')
    step_keys = []
    for event in steps:
        doc = join(event, fit_only=True)
        layer = event.get('layer')
        positions = event.get('query_positions')
        if type(layer) is not int or (doc, layer) not in layer_keys or not isinstance(positions, list) or len(positions) != event['queries'] or not positions or len(positions) > limits['max_queries'] or any(type(p) is not int or p < 0 for p in positions) or len(set(positions)) != len(positions):
            raise ProjectionError('invalid projection step identity')
        step_keys.append((doc, layer))
    if len(set(step_keys)) != len(step_keys):
        raise ProjectionError('duplicate projection step')
    if training and (set(step_keys) != {(doc, layer) for doc in fit for layer in valid_layers} or set(completed) != docs):
        raise ProjectionError('completed training has incomplete document or step coverage')


def seal_native(record_path):
    """Producer-time envelope over terminal native bytes; never backfill old runs."""
    record_path = Path(record_path).resolve()
    envelope_path = record_path.with_name('producer-record.lsa-pilot.json')
    envelope = {'schema': 'epyc.lsa_moe_pilot_envelope.v1', 'record': record_path.name,
                'record_sha256': _digest(record_path.read_bytes())}
    envelope['envelope_sha256'] = _digest(_canonical(envelope))
    with envelope_path.open('x') as f:
        json.dump(envelope, f, sort_keys=True, allow_nan=False)
        f.write('\n')
    try:
        native_rows(envelope_path)
    except Exception:
        envelope_path.unlink()
        raise
    return envelope_path


def native_rows(path):
    """Revalidate terminal record and producer-hashed artifacts on every read."""
    path = Path(path).resolve()
    try:
        raw = path.read_bytes()
        envelope = json.loads(raw)
        if envelope.get('schema') != 'epyc.lsa_moe_pilot_envelope.v1' or envelope.get('envelope_sha256') != _digest(_canonical({k:v for k,v in envelope.items() if k != 'envelope_sha256'})):
            raise ProjectionError('pilot envelope seal mismatch')
        name = envelope['record']
        if not isinstance(name, str) or Path(name).name != name:
            raise ProjectionError('invalid record path')
        record_raw = (path.parent / name).read_bytes()
        if _digest(record_raw) != envelope['record_sha256']:
            raise ProjectionError('pilot native record digest mismatch')
        record = json.loads(record_raw)
        if record['schema'] != 'lsa-moe-pilot-native-v1' or record['status'] not in ('complete', 'timeout', 'capacity', 'interrupted', 'invalid'):
            raise ProjectionError('not a terminal pilot record')
        if not isinstance(record['limits'], dict) or not record['limits'] or not isinstance(record['counts'], dict):
            raise ProjectionError('limits or counts missing')
        counts = record['counts']
        keys = ('eligible_documents', 'completed_documents', 'captured_layers', 'projection_steps', 'queries')
        if any(type(counts[k]) is not int or counts[k] < 0 for k in keys) or counts['completed_documents'] > counts['eligible_documents']:
            raise ProjectionError('invalid pilot denominators')
        if not _number(record['started_unix']) or not _number(record['elapsed_seconds']):
            raise ProjectionError('invalid pilot time')
        if record['status'] != 'complete' and not record.get('error'):
            raise ProjectionError('failure must retain producer error')
        def artifact(name, expected):
            rel = Path(name)
            if rel.is_absolute() or '..' in rel.parts or not name:
                raise ProjectionError('artifact path escapes pilot directory')
            resolved = (path.parent / rel).resolve()
            if not resolved.is_relative_to(path.parent) or _digest(resolved.read_bytes()) != expected:
                raise ProjectionError('artifact digest mismatch')
            return resolved
        event_path = artifact(record['events'], record['events_sha256'])
        events = [json.loads(line) for line in event_path.read_text().splitlines()]
        if not events or any(not isinstance(e, dict) or not _number(e.get('elapsed_seconds')) for e in events):
            raise ProjectionError('invalid pilot events')
        names = [a['path'] for a in record['artifacts']]
        if len(names) != len(set(names)):
            raise ProjectionError('duplicate pilot artifacts')
        for item in record['artifacts']:
            p = artifact(item['path'], item['sha256'])
            if type(item['bytes']) is not int or p.stat().st_size != item['bytes']:
                raise ProjectionError('artifact size mismatch')
        captured = [e for e in events if e.get('event') == 'document_captured']
        layers = [e for e in events if e.get('event') == 'layer_captured']
        steps = [e for e in events if e.get('event') == 'projection_step']
        if len(captured) != counts['completed_documents'] or len(layers) != counts['captured_layers'] or len(steps) != counts['projection_steps'] or any(type(e.get('queries')) is not int or e['queries'] < 0 for e in steps) or sum(e['queries'] for e in steps) != counts['queries']:
            raise ProjectionError('event counts differ from producer denominators')
        if any(not _number(e.get('seconds')) for e in captured):
            raise ProjectionError('invalid capture duration')
        training = [e for e in events if e.get('event') == 'training_complete']
        if len(training) > 1 or (training and (not _number(training[0].get('seconds')) or training[0].get('steps') != counts['projection_steps'] or training[0].get('queries') != counts['queries'])):
            raise ProjectionError('training event differs from denominators')
        if record['status'] == 'complete' and (not training or counts['completed_documents'] != counts['eligible_documents'] or not record.get('identity') or not record.get('runtime') or not record.get('actual_model')):
            raise ProjectionError('completed pilot lacks terminal evidence')
        if captured or training:
            _timing_contract(record, captured, layers, steps, training)
        rows = []
        for metric, value in [('lsa_pilot_completed_document_capture_seconds', sum(e['seconds'] for e in captured))] if captured else []:
            rows.append({'metric': metric, 'value': value})
        if training:
            rows.append({'metric': 'lsa_pilot_projection_training_seconds', 'value': training[0]['seconds']})
        return [{'record': record, 'receipt_path': str(path), 'receipt_sha256': _digest(raw), **row} for row in rows]
    except ProjectionError:
        raise
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        raise ProjectionError(f'pilot native evidence refused: {exc}') from exc


@register('lsa-moe-pilot', source_class='measurement')
def project(native):
    if native not in native_rows(native['receipt_path']):
        raise ProjectionError('pilot record changed since read')
    r = native['record']
    metric = native['metric']
    identity = r.get('identity') or {}
    scope = ({'model_file': identity['model'], 'model_sha256': identity['weights_sha256']}
             if isinstance(identity.get('model'), str) and isinstance(identity.get('weights_sha256'), str)
             and len(identity['weights_sha256']) == 64 and all(c in '0123456789abcdef' for c in identity['weights_sha256']) else {})
    return ClaimTuple(measurement_id='lsa-pilot:' + native['receipt_sha256'] + ':' + metric,
        metric=metric, value=native['value'], unit='seconds', metric_direction='lower_better',
        date=datetime.fromtimestamp(r['started_unix'], timezone.utc).isoformat(), category='CANDIDATE',
        claim=('Sum of completed document capture durations in this bounded pilot' if 'capture' in metric else 'Projection-training duration in this bounded pilot') + '; no quality, model result, comparison, or extrapolation claim.',
        protocol_id='', reps=r['counts']['completed_documents'] if 'capture' in metric else r['counts']['projection_steps'],
        reps_basis='completed documents; failures and partial work retained in native record' if 'capture' in metric else 'completed projection steps',
        attestation_path=native['receipt_path'], attestation_sha256=native['receipt_sha256'], attestation_verified=True,
        source_kind=SOURCE_KIND, applicability=scope, observation={'outcome_native': r['status']},
        extra={'native_record': r, 'receipt_sha256': native['receipt_sha256']})
