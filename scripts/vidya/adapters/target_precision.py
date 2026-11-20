"""Strict original-output precision projection; existing measurement ladder only."""
import importlib.util
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple, ProjectionError, register

PROJECTION_NAME = 'target-precision'
spec = importlib.util.spec_from_file_location(
    'precision_capture_projection',
    Path(__file__).resolve().parents[2] / 'diagnostics/target-precision/capture.py')
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)


def _read(path):
    try:
        return capture.read_precision(path)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise ProjectionError('precision retained originals refused') from exc


def native_rows(path):
    result, identity = _read(path)
    if result['plan']['origin'] != 'native_claimed':
        return ()
    return tuple({'closure_path': identity['path'], 'closure_sha256': identity['sha256'],
                  'measurement_id': row['measurement_id']} for row in result['measurements'])


@register(PROJECTION_NAME, source_class='measurement')
def project(native):
    if not isinstance(native, dict) or set(native) != {'closure_path', 'closure_sha256', 'measurement_id'}:
        raise ProjectionError('precision projection requires original closure and metric identity')
    result, identity = _read(native['closure_path'])
    if identity['sha256'] != native['closure_sha256'] or result['plan']['origin'] != 'native_claimed':
        raise ProjectionError('precision closure identity or origin refused')
    rows = [r for r in result['measurements'] if r['measurement_id'] == native['measurement_id']]
    if len(rows) != 1:
        raise ProjectionError('precision native metric missing or ambiguous')
    row = rows[0]
    labels = {key: row[key] for key in ('measurement_id', 'metric', 'value', 'date', 'category',
                                      'claim', 'metric_direction', 'unit')}
    return ClaimTuple(**labels, source_kind=PROJECTION_NAME,
                      attestation_locator=identity['path'], attestation_sha256=identity['sha256'],
                      attestation_present=True, attestation_verified=True,
                      applicability={'run_id': result['plan']['run_id'], 'backend': result['plan']['backend'],
                                     'quant': row['target_quant'], 'scope_basis': 'native'},
                      extra={'causal_gate': result['causal_gate'], 'counts': result['counts'],
                             'accepted': row['accepted'], 'drafted': row['drafted'],
                             'origin': result['plan']['origin'],
                             'limitations': 'declared fields only; no residency, matched-weight, causal or promotion proof'})
