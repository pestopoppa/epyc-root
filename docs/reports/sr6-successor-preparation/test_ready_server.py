import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from ready_server import verify_ready_server


class ReadyServerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.args = dict(process=Mock(pid=1234, poll=Mock(return_value=None)), arm='mtp3',
                         expected_argv=['/kernel/llama-server', '--port', '12345'],
                         library_dir='/kernel', build_root=Path('/kernel'), port=12345,
                         admission_check=lambda: True, record_path=Path(self.tmp.name) / 'ready.json')

    def run_check(self, *, cmd=None, env=None, status=200, body=b'{"status":"ok"}',
                  admission=None):
        cmd = cmd if cmd is not None else b'/kernel/llama-server\0--port\0' + b'12345\0'
        env = env if env is not None else b'LD_LIBRARY_PATH=/kernel\0'
        response = Mock(status=status, length=0, read=Mock(return_value=body))
        conn = Mock(getresponse=Mock(return_value=response))
        self.args['admission_check'] = admission or (lambda: True)
        with patch('ready_server.process_starttime', return_value=9), \
             patch('ready_server.verify_owned_loopback_listener') as listener, \
             patch('ready_server.verify_process_linkage', return_value={'mapped': 'checked'}), \
             patch('ready_server.Path.read_bytes', side_effect=[cmd, env]), \
             patch('ready_server.http.client.HTTPConnection', return_value=conn):
            result = verify_ready_server(**self.args)
        self.assertEqual(listener.call_count, 2)
        self.assertEqual(result['starttime_ticks'], 9)
        self.assertEqual(len(result['server_record_sha256']), 64)
        conn.close.assert_called_once()
        return result

    def test_valid_witness_is_exclusive(self):
        self.run_check()
        original = self.args['record_path'].read_bytes()
        with self.assertRaisesRegex(ValueError, 'server readiness unavailable') as failure:
            self.run_check()
        self.assertIsInstance(failure.exception.__cause__, FileExistsError)
        self.assertEqual(self.args['record_path'].read_bytes(), original)

    def test_wrong_args_or_environment_fails_before_witness(self):
        for kwargs in ({'cmd': b'/unexpected\0'}, {'env': b'LD_LIBRARY_PATH=/foreign\0'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.run_check(**kwargs)
            self.assertFalse(self.args['record_path'].exists())

    def test_nonready_or_revoked_is_not_recorded(self):
        with self.assertRaises(ValueError):
            self.run_check(status=503)
        states = iter([True, False])
        with self.assertRaises(ValueError):
            self.run_check(admission=lambda: next(states))
        self.assertFalse(self.args['record_path'].exists())


if __name__ == '__main__':
    unittest.main()
