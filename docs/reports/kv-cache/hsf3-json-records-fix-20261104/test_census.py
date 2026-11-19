import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

P = Path(__file__).parent
spec = importlib.util.spec_from_file_location('census_candidate', P / 'census.py')
census = importlib.util.module_from_spec(spec)
spec.loader.exec_module(census)

class CensusRecordCounts(unittest.TestCase):
    def sample(self, payload):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'fixture.jsonl'
            p.write_bytes(payload)
            totals, custody = census.progress([str(p)])
            self.assertEqual(totals['bytes'], len(payload))
            self.assertTrue(custody[0]['stable_during_read'])
            return totals

    def test_mixed_records_count_every_valid_object_once(self):
        valid = [
            {'event_type': 'session_created', 'timestamp': 'x', 'data': {'session_id': 'x'}},
            {'event': 'session_resumed'},
            {'event': 'unrelated'},
            {},
        ]
        payload = b''.join(json.dumps(x).encode() + b'\n' for x in valid) + b'not-json\n[]\n{"event": "unterminated"}'
        got = self.sample(payload)
        self.assertEqual(got['json_records'], 4)
        self.assertEqual(got['invalid_json'], 2)
        self.assertEqual(got['target_events'], 2)
        self.assertEqual(got['target_with_both'], 1)
        self.assertEqual(got['session_created'], 1)
        self.assertEqual(got['session_resumed'], 1)

    def test_oversize_excluded_and_following_record_counted(self):
        payload = b'x' * (census.MAX_RECORD + 2) + b'\n' + b'{"event":"session_checkpointed"}\n'
        got = self.sample(payload)
        self.assertEqual(got['oversize_records'], 1)
        self.assertEqual(got['json_records'], 1)
        self.assertEqual(got['target_events'], 1)
        self.assertEqual(got['session_checkpointed'], 1)

    def test_incomplete_and_malformed_do_not_count_as_valid(self):
        got = self.sample(b'{oops}\nnull\n{"event":"session_created"}')
        self.assertEqual(got['invalid_json'], 2)
        self.assertEqual(got['json_records'], 0)
        self.assertEqual(got['target_events'], 0)

if __name__ == '__main__': unittest.main()
