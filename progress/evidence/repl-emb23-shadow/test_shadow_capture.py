import pytest
from shadow_capture import ShadowSearchCapture

A = 'a' * 64
B = 'b' * 64
Q = 'c' * 64

def span(digest, start, end):
    return {'content_sha256': digest, 'start': start, 'end': end}

def capture():
    return ShadowSearchCapture(request_id='r1', query_sha256=Q, selected_arm='shown', content_sizes={A: 30, B: 3}, arms={
        'shown': {'status': 'ok', 'hits': [span(A, 0, 10), span(B, 0, 2)]},
        'shadow': {'status': 'ok', 'hits': [span(A, 5, 15), span(A, 20, 30)]},
        'failed': {'status': 'timeout', 'hits': []},
    })

def test_selected_only_and_content_bound_follow():
    c = capture()
    shown = c.selected_hits()
    assert shown == [span(A, 0, 10), span(B, 0, 2)]
    shown[0]['start'] = 9
    c.record_open(span(A, 9, 12))
    c.record_open(span(B, 2, 3))  # adjacent is not overlapping
    result = c.finish(complete=True)
    assert [h['opened'] for h in result['arms']['shown']['hits']] == [True, False]
    assert [h['opened'] for h in result['arms']['shadow']['hits']] == [True, False]
    assert result['arms']['failed'] == {'status': 'timeout', 'hits': []}
    assert result['arms']['shown']['hits'][0]['start'] == 0
    with pytest.raises(ValueError): c.record_open(span(A, 0, 1))

def test_incomplete_capture_keeps_absence_unknown():
    c = capture()
    c.selected_hits()
    c.record_open(span(A, 1, 2))
    result = c.finish(complete=False)
    assert [h['opened'] for h in result['arms']['shown']['hits']] == [True, None]
    assert [h['opened'] for h in result['arms']['shadow']['hits']] == [None, None]

def test_rejects_invalid_arm_and_span_inputs():
    with pytest.raises(ValueError):
        ShadowSearchCapture(request_id='r', query_sha256=Q, selected_arm='x', content_sizes={A: 30}, arms={'x': {'status': 'error', 'hits': []}})
    with pytest.raises(ValueError):
        ShadowSearchCapture(request_id='r', query_sha256=Q, selected_arm='x', content_sizes={A: 30}, arms={'x': {'status': 'ok', 'hits': [span(A, True, 3)]}})
    c = capture()
    c.selected_hits()
    with pytest.raises(ValueError): c.record_open(span('raw text', 0, 1))
    with pytest.raises(ValueError): capture().finish(complete=1)

def test_follow_and_completion_require_return_of_selected_hits():
    c = capture()
    with pytest.raises(ValueError): c.record_open(span(A, 0, 1))
    with pytest.raises(ValueError): c.finish(complete=True)
    c.selected_hits()
    assert c.finish(complete=True)['arms']['shown']['hits'][0]['opened'] is False


def test_rejects_unknown_or_out_of_bounds_content():
    with pytest.raises(ValueError, match="outside declared content"):
        ShadowSearchCapture(request_id='r', query_sha256=Q, selected_arm='x',
                            content_sizes={A: 10}, arms={'x': {'status': 'ok', 'hits': [span(A, 9, 11)]}})
    c = capture()
    c.selected_hits()
    with pytest.raises(ValueError, match="outside declared content"):
        c.record_open(span(A, 29, 31))
    with pytest.raises(ValueError, match="outside declared content"):
        c.record_open(span('d' * 64, 0, 1))
    with pytest.raises(ValueError, match="invalid content size"):
        ShadowSearchCapture(request_id='r', query_sha256=Q, selected_arm='x',
                            content_sizes={A: True}, arms={'x': {'status': 'ok', 'hits': []}})
