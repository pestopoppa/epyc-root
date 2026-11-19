"""Real JSON custody with mocked HTTP, listener and model-free response controls."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import launch_context as context
import protocol_requests as driver


class ProtocolTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/df2')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        path = self.root / 'corpus.jsonl'
        path.write_text('{"id":"a","prompt":"One"}\n{"id":"b","prompt":"Two"}\n')
        self.corpus = dict(path=str(path), sha256=context.sha256(path), identity=context.file_identity(str(path)))
        self.protocol = dict(schema='epyc.cafe3.protocol.v1', corpus=self.corpus, arms=['adaptive', 'static-3'], repetitions=2,
                             request_settings=dict(n_predict=8, seed=42, timeout_s=10, arm_widths={'adaptive': 3, 'static-3': 3}))
        self.plan = dict(argv=['/bound/server', '--host', '127.0.0.1', '--port', '18099'],
                         arm='adaptive', corpus=self.corpus, context_sha256='a'*64)
        self.save()
        self.output = self.root / 'requests.jsonl'
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, FILLER_STOPFILE=str(self.root / 'STOP'), FILLER_DEADLINE='9999999999').start()
        self.real_owner = driver.owns_listener
        self.owner = patch.object(driver, 'owns_listener', return_value=True).start()
        self.response = dict(stop=True, truncated=False, tokens=[4, 5], timings={'predicted_ms': 2.5})
        self.http = patch.object(driver, 'request', side_effect=lambda port, path, body, timeout:
                                 {'status': 'ok'} if path == '/health' else copy.deepcopy(self.response)).start()

    def save(self):
        path = self.root / 'protocol.json'
        path.write_text(json.dumps(self.protocol))
        self.plan['protocol'] = dict(path=str(path), sha256=context.sha256(path))

    def execute(self):
        driver.execute(self.plan, 123, self.output)

    def test_declared_repetitions_payload_and_durable_capture(self):
        self.execute()
        rows = [json.loads(line) for line in self.output.read_text().splitlines()]
        self.assertEqual([(r['repetition'], r['prompt_id']) for r in rows], [(0,'a'),(0,'b'),(1,'a'),(1,'b')])
        self.assertTrue(all(r['status'] == 'UNASSESSED' and r['context_sha256'] == 'a'*64 for r in rows))
        for row in rows:
            self.assertLess(row['unix_started_ns'], row['unix_ended_ns'])
            self.assertGreater(row['elapsed_ns'], 0)
        for call in self.http.call_args_list[1:]:
            self.assertEqual(call.args[2]['speculative.n_max'], 3)
            self.assertEqual(call.args[2]['temperature'], 0)
            self.assertFalse(call.args[2]['cache_prompt'])
            self.assertTrue(call.args[2]['return_tokens'])

    def test_static_arm_uses_declared_width(self):
        self.plan['arm'] = 'static-3'
        self.execute()
        self.assertTrue(all(json.loads(line)['arm'] == 'static-3' for line in self.output.read_text().splitlines()))

    def test_malformed_or_tampered_protocol_refused(self):
        base = copy.deepcopy(self.protocol)
        for key, value in [('seed', True), ('n_predict', 0), ('timeout_s', -1),
                           ('arm_widths', {'adaptive': 3}), ('arm_widths', {'adaptive': 3, 'static-3': 4})]:
            self.protocol = copy.deepcopy(base)
            self.protocol['request_settings'][key] = value
            self.save()
            with self.assertRaises(ValueError):
                driver.prepare(self.plan)
        Path(self.plan['protocol']['path']).write_text('{}')
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            driver.prepare(self.plan)

    def test_corpus_changed_refused_without_requests(self):
        Path(self.corpus['path']).write_text('{}')
        with self.assertRaisesRegex(ValueError, 'corpus changed'):
            self.execute()
        self.http.assert_not_called()

    def test_remote_or_ambiguous_endpoints_refused(self):
        for argv in [['--host', '0.0.0.0', '--port', '18099'], ['--host', '127.0.0.1', '--port', '80'],
                     ['--host', '127.0.0.1', '--port', '18099', '-p', '81']]:
            self.plan['argv'] = ['/bound/server'] + argv
            with self.assertRaises(ValueError):
                self.execute()
        self.http.assert_not_called()

    def test_bad_response_stops_without_retry(self):
        self.response['tokens'] = [True]
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.execute()
        self.assertEqual(self.http.call_count, 2)  # one health and exactly one POST
        self.assertEqual(self.output.read_text(), '')

    def test_lost_endpoint_owner_refuses_completion(self):
        self.owner.side_effect = [True, False]
        with self.assertRaisesRegex(ValueError, 'does not own'):
            self.execute()
        self.assertEqual(self.http.call_count, 1)

    def test_stop_before_request_and_exclusive_output(self):
        (self.root / 'STOP').touch()
        with self.assertRaisesRegex(ValueError, 'cutoff'):
            self.execute()
        self.http.assert_not_called()
        with self.assertRaises(FileExistsError):
            self.execute()

    def test_socket_owner_matches_actual_listener_inode(self):
        fd = Mock()
        fd.is_symlink.return_value = True
        fd.readlink.return_value = Path('socket:[456]')
        tcp = 'header\n0: 0100007F:46B3 00000000:0000 0A 0 0 0 0 0 456\n'
        with patch.object(Path, 'iterdir', return_value=iter([fd])), patch.object(Path, 'read_text', return_value=tcp):
            self.assertTrue(self.real_owner(123, 18099))
        with patch.object(Path, 'iterdir', return_value=iter([fd])), patch.object(Path, 'read_text', return_value=tcp.replace('456', '457')):
            self.assertFalse(self.real_owner(123, 18099))


if __name__ == '__main__':
    unittest.main()
