from datetime import datetime, timedelta, timezone

import pytest

from scripts.vidya.producers.repl_shadow import ShadowAttribution, Span

T = datetime(2026, 1, 1, tzinfo=timezone.utc)
SESSION = 'a' * 16


def span(start, end, *, section='b', content='c', size=100):
    return Span(section * 64, content * 64, start, end, size)


def shadow():
    return ShadowAttribution(session=SESSION, query_digest='d' * 64, searched_at=T,
                             rankings={'shown': [span(0, 10), span(10, 20)],
                                       'hidden': [span(5, 15), span(30, 40)]},
                             shown_arm='shown')


def test_next_open_preserves_rank_and_counterfactual_overlap():
    s = shadow()
    assert all(row['next_open_overlap'] is None for rows in s.result()['arms'].values() for row in rows)
    assert not s.observe_open(session='e' * 16, opened_at=T + timedelta(seconds=1), span=span(0, 10))
    assert s.observe_open(session=SESSION, opened_at=T + timedelta(seconds=2), span=span(10, 12))
    out = s.result()
    assert out['shown_arm'] == 'shown'
    assert [x['rank'] for x in out['arms']['shown']] == [1, 2]
    assert [x['next_open_overlap'] for x in out['arms']['shown']] == [False, True]
    assert [x['next_open_overlap'] for x in out['arms']['hidden']] == [True, False]
    with pytest.raises(ValueError, match='already recorded'):
        s.observe_open(session=SESSION, opened_at=T + timedelta(seconds=3), span=span(0, 1))


def test_first_open_of_different_content_is_negative_not_skipped():
    s = shadow()
    s.observe_open(session=SESSION, opened_at=T + timedelta(seconds=1), span=span(0, 1, content='f'))
    assert all(not row['next_open_overlap'] for rows in s.result()['arms'].values() for row in rows)


def test_refuses_ambiguous_or_invalid_identity_and_time():
    with pytest.raises(ValueError): span(1, 1)
    with pytest.raises(ValueError): span(0, 101)
    with pytest.raises(ValueError): Span('raw text', 'c' * 64, 0, 1, 1)
    with pytest.raises(ValueError):
        ShadowAttribution(session=SESSION, query_digest='d' * 64, searched_at=T,
                          rankings={'a': []}, shown_arm='missing')
    s = shadow()
    with pytest.raises(ValueError): s.observe_open(session=SESSION, opened_at=T, span=span(0, 1))
    with pytest.raises(ValueError): s.observe_open(session=SESSION, opened_at=T.replace(tzinfo=None), span=span(0, 1))
    assert s.result()['opened_at'] is None


def test_does_not_retain_mutable_rankings():
    ranks = {'shown': [span(0, 10)]}
    s = ShadowAttribution(session=SESSION, query_digest='d' * 64, searched_at=T,
                          rankings=ranks, shown_arm='shown')
    ranks['shown'].clear()
    assert len(s.result()['arms']['shown']) == 1
