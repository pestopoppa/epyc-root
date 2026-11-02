import hashlib
import json

import pytest

from scripts.vidya.producers.repl_shadow import Span
from scripts.vidya.producers.repl_shadow_sink import ShadowSink


def span(start, end, content='c'):
    return Span('b' * 64, content * 64, start, end, 100)


def capture(tmp_path):
    return ShadowSink(tmp_path, run_id='test', session='a' * 16,
                      source_sha256='f' * 64,
                      arm_identities={'shown': '1' * 64, 'hidden': '2' * 64})


def search(sink):
    sink.search(query_digest='d' * 64, shown_arm='shown',
                rankings={'shown': [span(0, 10)], 'hidden': [span(5, 15)]})


def read(path):
    rows = [json.loads(s) for s in path.read_text().splitlines()]
    previous = '0' * 64
    for n, row in enumerate(rows):
        digest = row.pop('sha256')
        assert row['sequence'] == n and row['previous_sha256'] == previous
        assert hashlib.sha256(json.dumps(row, sort_keys=True, separators=(',', ':'),
                                         allow_nan=False).encode()).hexdigest() == digest
        previous = digest
    return rows


def test_observed_open_preserves_identity_and_counterfactual(tmp_path):
    s = capture(tmp_path)
    search(s)
    assert s.opened(span=span(8, 9))
    rows = read(s.close())
    result = rows[2]
    assert result['reason'] == 'observed_open'
    assert result['opened_span']['content_digest'] == 'c' * 64
    assert result['interpretation'] == {'shown': 'shown', 'hidden': 'counterfactual_span_match'}
    assert result['result']['arms']['hidden'][0]['next_open_overlap'] is True
    assert rows[-1]['kind'] == 'finish' and rows[-1]['observed_opens'] == 1


def test_unknown_on_supersession_and_nonmatching_open(tmp_path):
    s = capture(tmp_path)
    search(s)
    search(s)
    s.opened(span=span(0, 2, content='e'))
    rows = read(s.close())
    results = [r for r in rows if r['kind'] == 'result']
    assert results[0]['reason'] == 'superseded'
    assert results[0]['result']['arms']['shown'][0]['next_open_overlap'] is None
    assert results[1]['result']['arms']['shown'][0]['next_open_overlap'] is False


def test_refuses_undeclared_arms_duplicate_and_caller_timestamp(tmp_path):
    s = capture(tmp_path)
    with pytest.raises(FileExistsError):
        capture(tmp_path)
    with pytest.raises(ValueError):
        s.search(query_digest='d' * 64, shown_arm='shown', rankings={'shown': [span(0, 1)]})
    with pytest.raises(TypeError):
        s.search(query_digest='d' * 64, shown_arm='shown', rankings={}, searched_at='2020')
    assert s.opened(span=span(0, 1)) is False
    path = s.close()
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(ValueError):
        s.close()
