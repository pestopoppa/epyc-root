"""Project prospective v2 trace events as located observations.

Only the exclusive, finalized native coverage stream is admitted. The source
hash is producer-declared and is not proof of loaded code. The sealed stream
contains no originals, so query and corpus custody remain unknown: this source
reports recorded facts, not a real-session attestation, recall or follow rate.
It is ingested only from an explicitly named sidecar; no automatic discovery.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from claim_tuple import ClaimTuple, ProjectionError, register

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.vidya.producers import repl_trace_capture as producer  # noqa: E402

SOURCE_KIND = 'repl-trace-facts'
ADAPTER_ID = 'vidya.adapters.repl_trace_facts/v1'
AUTHORITY = 'measurement'


def native_rows(path):
    """Validate and enumerate a finalized capture; malformed streams refuse whole input."""
    path = Path(path).resolve()
    try:
        rows = producer.carrier.load_rows(
            path, lambda row: ['not an object'] if not isinstance(row, dict)
            else producer.validate(row))
        if rows is None or len(rows) != 1 or path.name != rows[0]['run_id'] + '.belief_measurements.jsonl':
            raise ProjectionError('invalid trace sidecar')
        row = rows[0]
        stream = Path(row['results_path'])
        # Validate already re-hashed the stream. Read it again and confirm this exact
        # byte sequence before deriving facts, so a changed file cannot be projected.
        data = stream.read_bytes()
        import hashlib
        if hashlib.sha256(data).hexdigest() != row['results_sha256']:
            raise ProjectionError('trace stream changed')
        records = [json.loads(line) for line in data.splitlines()]
        return tuple({'sidecar': str(path), 'stream_sha256': row['results_sha256'],
                      'stream_path': str(stream), 'ordinal': i, 'event': wrapper['event'],
                      'run_id': row['run_id'], 'source_sha256': row['extra']['source_sha256']}
                     for i, wrapper in enumerate(records[1:-1], 1))
    except ProjectionError:
        raise
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        raise ProjectionError('invalid trace capture') from exc


@register(SOURCE_KIND)
def project(native):
    if not isinstance(native, dict) or set(native) != {
        'sidecar', 'stream_sha256', 'stream_path', 'ordinal', 'event', 'run_id', 'source_sha256'
    } or not isinstance(native['sidecar'], str):
        raise ProjectionError('invalid native trace fact')
    if native not in native_rows(native['sidecar']):
        raise ProjectionError('trace fact does not rederive')
    event = native['event']
    locator = native['sidecar'] + '#event-' + str(native['ordinal'])
    return ClaimTuple(
        measurement_id='trace-fact-' + native['stream_sha256'] + '-' + str(native['ordinal']),
        metric='recorded_trace_event', value=1, date=event['ts'], category='CANDIDATE',
        claim=('Prospective v2 trace event recorded; source and session identity are producer-declared; '
               'original query and corpus custody are unknown; source_sha256=' + native['source_sha256'] +
               '; event=' + json.dumps(event, sort_keys=True, separators=(',', ':'))),
        metric_direction='higher_better', protocol_id='', reps=1,
        reps_basis='one recorded event, not an independent replication', unit='event',
        attestation_path=native['stream_path'],
        attestation_sha256=native['stream_sha256'], attestation_locator=locator,
        attestation_present=True, attestation_verified=True, source_kind=SOURCE_KIND,
        extra={'native_schema': producer.SCHEMA, 'source_sha256': native['source_sha256'],
               'source_identity_scope': 'producer-declared', 'run_id': native['run_id'],
               'event_ordinal': native['ordinal'], 'event': event,
               'query_and_corpus_custody': 'unknown'},
    )
