"""Model-free process-boundary tests: no native model binary is launched."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import native_runner as runner


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/df2/native-runner-tests')
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.log, self.result = root / 'server.log', root / 'result.json'
        self.stop = root / 'STOP'
        self.plan = dict(argv=['/bound/llama-server', '-t', '2'], env={'LD_LIBRARY_PATH': '/bound'})
        self.child = Mock(pid=123)
        self.child.poll.return_value = 0
        self.child.wait.return_value = 0
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, FILLER_ID='unit-cafe3-runner', FILLER_STOPFILE=str(self.stop), FILLER_DEADLINE='9999999999').start()
        self.validate = patch.object(runner.context, 'validate_launch_context', return_value=self.plan).start()
        self.spawn = patch.object(runner.subprocess, 'Popen', return_value=self.child).start()

    def run_capture(self):
        return runner.run('/bound/context.json', 'a'*64, self.plan['argv'], self.log, self.result)

    def test_exact_validated_command_and_environment_and_unassessed_receipt(self):
        record = self.run_capture()
        self.validate.assert_called_once_with('/bound/context.json', 'a'*64, self.plan['argv'])
        args, kwargs = self.spawn.call_args
        self.assertIs(args[0], self.plan['argv'])
        self.assertIs(kwargs['env'], self.plan['env'])
        self.assertEqual(kwargs['stdin'], subprocess.DEVNULL)
        self.assertTrue(kwargs['close_fds'])
        self.assertEqual(record['status'], 'UNASSESSED')
        self.assertTrue(record['child_reaped'])
        self.assertEqual(json.loads(self.result.read_text()), record)

    def test_refusal_has_no_spawn_or_outputs(self):
        self.validate.side_effect = ValueError('context refused')
        with self.assertRaisesRegex(ValueError, 'context refused'):
            self.run_capture()
        self.spawn.assert_not_called()
        self.assertFalse(self.result.exists())
        self.assertFalse(self.log.exists())

    def test_late_stop_and_deadline_refuse_spawn(self):
        self.stop.touch()
        with self.assertRaisesRegex(ValueError, 'before spawn'):
            self.run_capture()
        self.spawn.assert_not_called()

    def test_deadline_after_validation_refuses_spawn(self):
        with patch.dict(os.environ, FILLER_DEADLINE='0'):
            with self.assertRaisesRegex(ValueError, 'before spawn'):
                self.run_capture()
        self.spawn.assert_not_called()

    def test_deadline_during_run_reaps_child(self):
        self.child.poll.side_effect = [None, None, 0]
        with patch.object(runner.time, 'time', side_effect=[1, 1, 99999999999, 99999999999]), \
             patch.object(Path, 'read_text', side_effect=FileNotFoundError):
            record = self.run_capture()
        self.assertEqual(record['cutoff'], 'deadline')
        self.child.terminate.assert_called_once()

    def test_outputs_are_exclusive(self):
        self.log.touch()
        with self.assertRaises(FileExistsError):
            self.run_capture()
        self.spawn.assert_not_called()

    def test_stop_during_run_terminates_owned_child(self):
        self.child.poll.side_effect = [None, None, 0]
        original = Path.exists
        checks = 0
        def exists(path):
            nonlocal checks
            if path == self.stop:
                checks += 1
                return checks > 1
            return original(path)
        with patch.object(Path, 'exists', exists), patch.object(Path, 'read_text', side_effect=FileNotFoundError):
            record = self.run_capture()
        self.assertEqual(record['cutoff'], 'STOP')
        self.child.terminate.assert_called_once()
        self.assertTrue(record['child_reaped'])

    def test_reap_escalates_and_waits_for_death(self):
        self.child.poll.return_value = None
        self.child.wait.side_effect = [subprocess.TimeoutExpired('owned', 5), -9]
        self.assertEqual(runner.reap(self.child), -9)
        self.child.terminate.assert_called_once()
        self.child.kill.assert_called_once()
        self.assertEqual(self.child.wait.call_count, 2)

    def test_capture_exception_still_reaps_child(self):
        self.child.poll.side_effect = [None, None, 0]
        with patch.object(Path, 'read_text', side_effect=PermissionError('maps')):
            with self.assertRaises(PermissionError):
                self.run_capture()
        self.child.terminate.assert_called_once()
        self.child.wait.assert_called_once()

    def test_protocol_completion_reaps_both_owned_processes(self):
        import protocol_requests
        requester = Mock(pid=124, returncode=0)
        requester.poll.return_value = 0
        requester.wait.return_value = 0
        self.child.poll.side_effect = [None, None, 0]
        self.spawn.side_effect = [self.child, requester]
        with patch.object(protocol_requests, 'prepare'), patch.object(Path, 'read_text', side_effect=FileNotFoundError):
            record = runner.run('/bound/context.json', 'a'*64, self.plan['argv'], self.log,
                                self.result, self.log.parent / 'requests.jsonl')
        self.assertEqual(record['cutoff'], 'protocol-complete')
        self.assertEqual(record['request_rc'], 0)
        self.assertTrue(record['requester_reaped'])
        self.child.terminate.assert_called_once()
        requester.wait.assert_called_once()
        command = self.spawn.call_args_list[1].args[0]
        self.assertEqual(command[-2], '123')
        self.assertEqual(runner.exit_code(record), 0)

    def test_server_exit_does_not_mask_incomplete_protocol(self):
        import protocol_requests
        requester = Mock(pid=124)
        requester.poll.return_value = -15
        requester.wait.return_value = -15
        self.spawn.side_effect = [self.child, requester]
        with patch.object(protocol_requests, 'prepare'):
            record = runner.run('/bound/context.json', 'a'*64, self.plan['argv'], self.log,
                                self.result, self.log.parent / 'requests.jsonl')
        self.assertEqual(record['rc'], 0)
        self.assertEqual(record['cutoff'], 'server-exited')
        self.assertEqual(runner.exit_code(record), 1)

    def test_bad_request_protocol_refuses_before_server_spawn(self):
        import protocol_requests
        with patch.object(protocol_requests, 'prepare', side_effect=ValueError('request settings')):
            with self.assertRaisesRegex(ValueError, 'request settings'):
                runner.run('/bound/context.json', 'a'*64, self.plan['argv'], self.log,
                           self.result, self.log.parent / 'requests.jsonl')
        self.spawn.assert_not_called()


if __name__ == '__main__':
    unittest.main()
