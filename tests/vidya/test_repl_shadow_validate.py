import hashlib
import json

import pytest

from scripts.vidya.producers.repl_shadow import Span
from scripts.vidya.producers.repl_shadow_sink import ShadowSink
from scripts.vidya.producers.repl_shadow_validate import validate_shadow_stream


def capture(tmp_path, opened=True):
    sink = ShadowSink(tmp_path, run_id='test', session='a' * 16, source_sha256='f' * 64,
                      arm_identities={'shown': '1' * 64, 'hidden': '2' * 64})
    span = Span('b' * 64, 'c' * 64, 0, 10, 100)
    sink.search(query_digest='d' * 64, rankings={'shown': [span], 'hidden': [span]}, shown_arm='shown')
    if opened:
        sink.opened(span=span)
    return sink.close()


def rewrite(path, change):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    change(rows)
    prev = '0' * 64
    lines = []
    for row in rows:
        row['previous_sha256'] = prev
        body = {k: v for k, v in row.items() if k != 'sha256'}
        prev = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        row['sha256'] = prev
        lines.append(json.dumps(row))
    path.write_text('\n'.join(lines) + '\n')


def test_valid_observed_and_unknown(tmp_path):
    p = capture(tmp_path)
    rows = validate_shadow_stream(p, expected_source_sha256='f' * 64)
    assert rows[-1]['observed_opens'] == 1
    with pytest.raises(ValueError):
        validate_shadow_stream(p, expected_source_sha256='e' * 64)
    second = tmp_path / 'second'; second.mkdir()
    rows = validate_shadow_stream(capture(second, opened=False))
    assert rows[2]['result']['arms']['hidden'][0]['next_open_overlap'] is None


def test_truncated_and_unrehashed_tampering(tmp_path):
    p = capture(tmp_path)
    original = p.read_text()
    p.write_text(original.rsplit('\n', 2)[0] + '\n')
    with pytest.raises(ValueError): validate_shadow_stream(p)
    p.write_text(original.replace('counterfactual_span_match', 'shown'))
    with pytest.raises(ValueError): validate_shadow_stream(p)


def test_rehashed_counts_result_and_source_forgery(tmp_path):
    p = capture(tmp_path)
    original = p.read_bytes()
    rewrite(p, lambda rows: rows[-1].update(searches=3))
    with pytest.raises(ValueError): validate_shadow_stream(p)
    p.write_bytes(original)
    rewrite(p, lambda rows: rows[2]['result']['arms']['hidden'][0].update(next_open_overlap=False))
    with pytest.raises(ValueError): validate_shadow_stream(p)
    p.write_bytes(original)
    rewrite(p, lambda rows: rows[0].update(source_sha256='e' * 64))
    with pytest.raises(ValueError): validate_shadow_stream(p, expected_source_sha256='f' * 64)


def test_incomplete_and_duplicate_json_keys(tmp_path):
    sink = ShadowSink(tmp_path, run_id='test', session='a'*16, source_sha256='f'*64, arm_identities={'a': '1'*64})
    with pytest.raises(ValueError): validate_shadow_stream(sink.path)
    sink.close()
    s = sink.path.read_text().replace('"kind":"start"', '"kind":"start","kind":"start"', 1)
    sink.path.write_text(s)
    with pytest.raises(ValueError): validate_shadow_stream(sink.path)
