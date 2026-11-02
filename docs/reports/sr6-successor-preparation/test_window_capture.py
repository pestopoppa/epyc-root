import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from native_worker import canonical, digest
from test_worker import packet
from window_capture import capture_window
from block_controller import BlockError, execute_block
from test_block_controller import FakeProcess


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

    def test_explicit_containment_drain_reaches_every_block(self):
        drain = lambda process, grace: None
        self.args['drain'] = drain
        with patch('window_capture.capture_keeper_block', return_value={'state': 'CAPTURED_ONLY'}) as capture:
            capture_window(**self.args)
        self.assertTrue(all(call.kwargs['drain'] is drain for call in capture.call_args_list))

    def test_failed_block_abandons_window(self):
        with patch('window_capture.capture_keeper_block', side_effect=[{'state': 'CAPTURED_ONLY'}, RuntimeError('stopped')]) as capture:
            with self.assertRaises(RuntimeError): capture_window(**self.args)
            self.assertEqual(capture.call_count, 2)
            with self.assertRaises(FileExistsError): capture_window(**self.args)
            self.assertEqual(capture.call_count, 2)

    def test_schedule_through_real_block_controller_with_cleanup(self):
        processes, calls = [], []
        def spawn(arm):
            process = FakeProcess()
            processes.append(process)
            return process
        def drain(process, _grace):
            process.terminate()
        def capture(**kw):
            return execute_block(output=kw['output'], block=kw['block'], sampler=kw['sampler'],
                sampler_sha256=kw['sampler_sha256'], admission_check=lambda: True,
                spawn=spawn, verify_ready_and_identity=lambda p, a: {'server_record_sha256': 'a'*64},
                post=lambda server, payload: (calls.append(server.arm) or (200, b'{}')), drain=drain)
        with patch('window_capture.capture_keeper_block', side_effect=capture):
            result = capture_window(**self.args)
        self.assertEqual(result['blocks'], 4)
        self.assertEqual(len(processes), 20)
        self.assertEqual(len(calls), 75)
        self.assertTrue(all(not process.alive for process in processes))

    def test_schedule_stop_abandons_window_and_drains_current_server(self):
        processes = []
        def spawn(arm):
            process = FakeProcess()
            processes.append(process)
            return process
        def post(server, payload):
            raise ValueError('in-flight stop')
        def capture(**kw):
            return execute_block(output=kw['output'], block=kw['block'], sampler=kw['sampler'],
                sampler_sha256=kw['sampler_sha256'], admission_check=lambda: True,
                spawn=spawn, verify_ready_and_identity=lambda p, a: {'server_record_sha256': 'a'*64},
                post=post, drain=lambda process, grace: process.terminate())
        with patch('window_capture.capture_keeper_block', side_effect=capture):
            with self.assertRaises(BlockError):
                capture_window(**self.args)
            with self.assertRaises(FileExistsError):
                capture_window(**self.args)
        self.assertEqual(len(processes), 1)
        self.assertFalse(processes[0].alive)
        self.assertEqual(len(list(Path(self.tmp.name).glob('*.exposure.json'))), 1)
