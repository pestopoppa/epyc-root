"""Project completed shadow event streams as producer-declared observations.

The stream validates its own chain and attribution, not producer authenticity,
loaded runtime, corpus custody, recall, or hidden-arm user behavior. Only an
explicitly named file is read; an unknown outcome is never a negative outcome.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from claim_tuple import ClaimTuple, ProjectionError, register

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.vidya.producers.repl_shadow_validate import validate_shadow_stream  # noqa: E402

SOURCE_KIND = 'repl-shadow-observation'
ADAPTER_ID = 'vidya.adapters.repl_shadow_observation/v1'
AUTHORITY = 'measurement'


def native_rows(path):
    path = Path(path).resolve()
    try:
        before = path.read_bytes()
        rows = validate_shadow_stream(path)
        after = path.read_bytes()
        if before != after:
            raise ProjectionError('shadow stream changed during validation')
        digest = hashlib.sha256(after).hexdigest()
        start = rows[0]
        return tuple({'path': str(path), 'sha256': digest, 'start': start, 'event': row}
                     for row in rows if row['kind'] == 'result')
    except ProjectionError:
        raise
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ProjectionError('invalid or incomplete shadow stream') from exc


@register(SOURCE_KIND)
def project(native):
    if not isinstance(native, dict) or set(native) != {'path', 'sha256', 'start', 'event'} or not isinstance(native['path'], str):
        raise ProjectionError('invalid shadow observation')
    if native not in native_rows(native['path']):
        raise ProjectionError('shadow observation does not rederive')
    start, event = native['start'], native['event']
    result = event['result']
    timestamp = result['opened_at'] or result['searched_at']
    sequence = event['sequence']
    return ClaimTuple(
        measurement_id='shadow-observation-' + native['sha256'] + '-' + str(sequence),
        metric='recorded_shadow_result', value=1, date=timestamp, category='CANDIDATE',
        claim=('A shadow result was recorded by the declaring producer; unknown outcomes remain unknown, '
               'hidden-arm matches are counterfactual, and runtime, display and corpus custody are unverified; '
               'reason=' + event['reason']),
        metric_direction='higher_better', protocol_id='', reps=1,
        reps_basis='one recorded result; not a replicate or follow-rate denominator', unit='event',
        attestation_path=native['path'], attestation_sha256=native['sha256'],
        attestation_locator=native['path'] + '#event-' + str(sequence),
        attestation_present=True, attestation_verified=True, source_kind=SOURCE_KIND,
        extra={'native_schema':start['schema'], 'run_id':start['run_id'],
               'session':start['session'], 'source_sha256':start['source_sha256'],
               'arm_identities':start['arm_identities'], 'identity_scope':'producer-declared',
               'event':event, 'runtime_and_corpus_custody':'unknown'},
    )
