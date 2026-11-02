import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from native_worker import canonical, digest
from test_worker import packet
from window_capture import capture_window


class WindowCaptureTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p = packet()
        self.args = dict(packet=self.p, packet_sha256=digest(canonical(self.p)),
            window='w0', output=Path(self.tmp.name),
            keeper_args=dict(env={}, row_id='row', grant_path=Path('/grant'),
                             stop_path=Path('/stop'), guard_sha256='a'*64),
            spawn=lambda arm: None, verify_ready_and_identity=lambda p, a: {},
            port=12345, timeout_s=1, max_response_bytes=1024)

    def test_selected_window_and_no_retry(self):
        with patch('window_capture.capture_keeper_block', return_value={'state': 'CAPTURED_ONLY'}) as capture:
            result = capture_window(**self.args)
            self.assertEqual(result['blocks'], 4)
            self.assertEqual([x.kwargs['block']['window'] for x in capture.call_args_list], ['w0'] * 4)
            with self.assertRaises(FileExistsError):
                capture_window(**self.args)
            self.assertEqual(capture.call_count, 4)

    def test_tampered_other_window_rejected_before_marker(self):
        self.p['windows'][2]['blocks'][0]['prompts'][0]['prompt'] = 'tampered'
        with patch('window_capture.capture_keeper_block') as capture:
            with self.assertRaises(ValueError): capture_window(**self.args)
            capture.assert_not_called()
        self.assertEqual(list(Path(self.tmp.name).iterdir()), [])

    def test_failed_block_abandons_window(self):
        with patch('window_capture.capture_keeper_block', side_effect=[{'state': 'CAPTURED_ONLY'}, RuntimeError('stopped')]) as capture:
            with self.assertRaises(RuntimeError): capture_window(**self.args)
            self.assertEqual(capture.call_count, 2)
            with self.assertRaises(FileExistsError): capture_window(**self.args)
            self.assertEqual(capture.call_count, 2)
