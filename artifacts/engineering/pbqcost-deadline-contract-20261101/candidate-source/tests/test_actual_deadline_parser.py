"""Controls against the installed parser used by the full PB-QCOST CLI."""
from datetime import datetime, timezone, timedelta
import importlib.util
import math
from pathlib import Path
import sys

D = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(D / 'source'))
from deadline_contract import deadline_arg_utc

PARSER_PATH = Path('/mnt/raid0/llm/tmp/pb-hol-1/pb_hol_1.py')
spec = importlib.util.spec_from_file_location('pb_hol_1_actual', PARSER_PATH)
H = importlib.util.module_from_spec(spec)
spec.loader.exec_module(H)


def test_aware_datetime_conversion_preserves_instant_and_emits_utc_z():
    utc = datetime(2026, 11, 1, 4, 59, 30, tzinfo=timezone.utc)
    offset = datetime(2026, 10, 31, 23, 59, 30, tzinfo=timezone(timedelta(hours=-5)))
    assert utc.timestamp() == offset.timestamp()
    emitted = deadline_arg_utc(offset.timestamp())
    assert emitted == '2026-11-01T04:59:30Z'
    assert H.parse_deadline(emitted) == int(utc.timestamp())


def test_actual_parser_rejects_offset_and_malformed_forms_without_widening_contract():
    for rejected in ('2026-11-01T04:59:30+00:00',
                     '2026-11-01T09:59:30+05:00',
                     '2026-11-01T04:59:30Z+00:00',
                     'not-a-deadline', '2026-13-01T04:59:30Z'):
        try:
            H.parse_deadline(rejected)
        except SystemExit as exc:
            assert 'bad --deadline' in str(exc)
        else:
            raise AssertionError(f'actual parser unexpectedly accepted {rejected!r}')


def test_serialization_refuses_nonfinite_and_acceptance_is_parser_native():
    for epoch in (math.nan, math.inf, -math.inf):
        try:
            deadline_arg_utc(epoch)
        except ValueError as exc:
            assert 'finite' in str(exc)
        else:
            raise AssertionError(f'nonfinite deadline unexpectedly accepted: {epoch}')
    for fmt in ('%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%MZ'):
        value = datetime(2026, 11, 1, 5, 0, tzinfo=timezone.utc).strftime(fmt)
        assert H.parse_deadline(value) == int(datetime(2026, 11, 1, 5, 0, tzinfo=timezone.utc).timestamp())
