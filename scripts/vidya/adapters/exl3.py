"""Strict prospective EXL3 measurement/verifier projections; no private ladder."""
from __future__ import annotations
import hashlib
import importlib.util
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple, ProjectionError, register

PRODUCER_SHA256 = '8caeb33dbb12986fadc385afe25d22bd791b036253c736f9527e67a55f85e268'
DEFAULT_PRODUCER = Path('/workspace/repos/epyc-inference-research/scripts/kernel_rnd/exl3/evidence.py')
ADAPTER_ID = 'vidya.adapters.exl3/v1'
AUTHORITY = 'experimental_no_promotion'


def _producer(path=None):
    source = Path(path or DEFAULT_PRODUCER)
    try:
        data = source.read_bytes()
    except OSError as exc:
        raise ProjectionError('reviewed EXL3 producer unavailable') from exc
    if hashlib.sha256(data).hexdigest() != PRODUCER_SHA256:
        raise ProjectionError('EXL3 producer differs from reviewed bytes')
    # Compile the same bytes that were hashed, avoiding path reload races.
    spec = importlib.util.spec_from_loader('_epyc_exl3_evidence', loader=None)
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(source)
    exec(compile(data, str(source), 'exec'), module.__dict__)
    return module


def native_rows(path, *, producer_path=None):
    module = _producer(producer_path)
    try:
        return module.native_rows(path)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        raise ProjectionError(f'EXL3 evidence refused: {exc}') from exc


def _project(row, schema, producer_path=None):
    module = _producer(producer_path)
    if row.get('schema') != schema:
        raise ProjectionError('wrong EXL3 source class')
    try:
        return ClaimTuple(**module.project(row))
    except (ValueError, TypeError, KeyError, OSError) as exc:
        raise ProjectionError(f'EXL3 evidence refused: {exc}') from exc


@register('exl3_measurement')
def project_measurement(row, *, producer_path=None):
    return _project(row, 'epyc.exl3.measurement.v1', producer_path)


@register('exl3_verifier', source_class='verifier', decided_proposition_field='decided_proposition')
def project_verifier(row):
    return _project(row, 'epyc.exl3.verifier.v1')


def measurement_rows(path):
    return [row for row in native_rows(path) if row['schema'] == 'epyc.exl3.measurement.v1']


def verifier_rows(path):
    return [row for row in native_rows(path) if row['schema'] == 'epyc.exl3.verifier.v1']
