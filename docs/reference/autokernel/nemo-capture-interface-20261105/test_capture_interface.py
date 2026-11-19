"""Offline producer/consumer interface test; all server and profiler events are synthetic."""
import json
from pathlib import Path
import sys
import unittest

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / 'nemo-request-producers-20261105'))
sys.path.insert(0, str(BASE / 'nemo-marker-identity-20261105'))
from capture_client import capture
from test_verify_marker_identity import fixture, run


class Response:
    status = 200
    def __init__(self, body): self.body = body
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return self.body


def mocked_send(request, timeout):
    request_data = json.loads(request.data)
    return Response(json.dumps({'nemo_request_id': request_data['nemo_request_id'], 'content': 'ok'}).encode())


class CaptureInterfaceTest(unittest.TestCase):
    def test_real_producer_record_passes_identity_consumer_with_matching_join(self):
        client = capture('http://example.invalid/completion', {'prompt': 'test'}, mocked_send)
        _, events, markers = fixture()
        events[0]['data']['request_id'] = client['requests'][0]['request_id']
        result = run(client, events, markers)
        self.assertEqual(result['status'], 'MARKER_IDENTITY_CONSISTENT_ONLY')
        self.assertEqual(result['joined_task_id'], 42)
        self.assertEqual(result['same_run_provenance'], 'NOT_ASSESSED')
        self.assertEqual(result['token_attribution'], 'NOT_ASSESSED')

    def test_join_from_another_request_is_rejected(self):
        first = capture('http://example.invalid/completion', {'prompt': 'test'}, mocked_send)
        second = capture('http://example.invalid/completion', {'prompt': 'test'}, mocked_send)
        _, events, markers = fixture()
        events[0]['data']['request_id'] = second['requests'][0]['request_id']
        with self.assertRaises(ValueError): run(first, events, markers)

if __name__ == '__main__': unittest.main()
