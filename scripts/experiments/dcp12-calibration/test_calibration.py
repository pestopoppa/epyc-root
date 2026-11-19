import sys
from datetime import UTC, datetime

import calibration_analysis as analysis
import prepare
import pytest

sys.path.append("/mnt/raid0/llm/tmp/delegation-context-preassembly/dcp12/packet")
import runner


def test_schedule_identical_pairs():
    cases, inventory = prepare.source_corpus()
    rows = prepare.paired_schedule(cases)['coverage']
    assert len(rows) == 12
    gradeable = {x['id'] for x in inventory if x['grade_cohort']}
    for a,b in zip(rows[::3], rows[1::3]):
        assert a['case'] in gradeable
        assert all(a[k] == b[k] for k in ('case','arm','seed','repeat','pair'))
        assert (a['replicate'], b['replicate']) == (0,1)


def test_accounting_preserves_unknown_and_missing():
    rows = prepare.paired_schedule([{'id': x} for x in prepare.COVERAGE_CASES])['coverage']
    def result(row, status, correct): return {**row, 'status': status, 'correct': correct, 'first_request_sha256': 'same'}
    outcomes = [result(rows[0], 'graded', True), result(rows[1], 'NA', False),
                result(rows[3], 'grade_unavailable', None), result(rows[4], 'graded', True),
                result(rows[6], 'UNKNOWN', None), result(rows[7], 'graded', False)]
    x = analysis.summarize(rows, outcomes)
    assert (x['eligible'],x['flips'],x['NA_pairs'],x['missing_grade'],x['unknown'],x['unattempted']) == (1,1,1,1,1,1)
    with pytest.raises(ValueError): analysis.summarize(rows, outcomes + outcomes[:1])


def test_exact_power_basic():
    assert analysis.exact_power(5, .05, .05) == 0
    assert analysis.exact_power(6, 1, 0) == pytest.approx(1)
    assert analysis.exact_power(6, .5, .5) == pytest.approx(1/32)
    assert 0 < analysis.exact_power(100, .075, .025) < analysis.exact_power(200, .075, .025) < 1
    assert analysis.exact_power(10, 0, 0) == 0


def test_pairs_resolve_replicate_independent_of_order_and_reject_duplicates():
    rows = prepare.paired_schedule([{'id': x} for x in prepare.COVERAGE_CASES])['coverage']
    outcomes = [{**r, 'status': 'graded', 'correct': r['replicate'] != 1,
                 'first_request_sha256': 'a' if r['case'] != prepare.COVERAGE_CASES[1] or r['replicate'] != 1 else 'b'} for r in rows]
    actual = analysis.summarize(list(reversed(rows)), list(reversed(outcomes)))
    assert actual['eligible'] == 3 and actual['flips'] == 3
    assert actual['first_request_mismatch'] == 1
    assert analysis.summarize(rows, outcomes, rerun=2)['flips'] == 0
    duplicate = [dict(r) for r in rows]
    duplicate[1]['replicate'] = 0
    with pytest.raises(ValueError, match='duplicate case/replicate'):
        analysis.summarize(duplicate, [])


def test_quiet_grant_rejects_missing_expired_malformed(tmp_path):
    grant = tmp_path / 'row.grant'
    now = datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(ValueError): runner.verify_quiet_grant(grant, now)
    for data in ('', 'holds=q0,q1,q2,q3,gpu-quiet',
                 'holds=q0,q1,q2,q3,gpu-quiet end=bad',
                 'holds=q0,q1,q2,q3,gpu-quiet end=2025-01-01T00:00:00Z',
                 'holds=q0,q1,q2,q3 end=2027-01-01T00:00:00Z',
                 'holds=q0,q1,q2,q3,gpu-quiet end=2027-01-01T00:00:00'):
        grant.write_text(data)
        with pytest.raises(ValueError): runner.verify_quiet_grant(grant, now)
    grant.write_text('holds=q0,q1,q2,q3,gpu-quiet end=2027-01-01T00:00:00Z')
    runner.verify_quiet_grant(grant, now)
