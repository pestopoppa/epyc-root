"""Offline controls for row ownership and refusal; never loads a model."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import live_proof_job as job


class LiveProofTests(unittest.TestCase):
    def test_reap_escalates_only_owned_child(self):
        child = Mock()
        child.poll.side_effect = [None, -9]
        child.wait.side_effect = [subprocess.TimeoutExpired('own', 15), -9]
        job.stop_own(child)
        child.terminate.assert_called_once_with()
        child.kill.assert_called_once_with()
        self.assertEqual(child.wait.call_count, 2)

    def test_dead_child_is_not_signalled(self):
        child = Mock()
        child.poll.return_value = 0
        job.stop_own(child)
        child.terminate.assert_not_called()
        child.kill.assert_not_called()

    def test_changed_model_refuses_before_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            model = d/'model'
            model.write_bytes(b'changed')
            with self.assertRaisesRegex(RuntimeError, 'model changed'):
                job.check_inputs({'model': str(model), 'model_stat': {}})

    def test_precondition_failure_writes_refusal_without_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            (d/'INPUTS.json').write_text('{}')
            with patch.object(job.Path, 'cwd', return_value=d), \
                 patch.object(job, 'check_inputs', side_effect=RuntimeError('changed identity')), \
                 patch.dict(job.os.environ, {'FILLER_SMOKE': '1'}), \
                 patch.object(job.subprocess, 'Popen') as launch:
                self.assertEqual(job.main(), 3)
            result = json.loads((d/'out-smoke/RESULT.json').read_text())
            self.assertFalse(result['ok'])
            self.assertEqual(result['verdict'], 'PREFLIGHT_REFUSED')
            self.assertTrue(result['own_server_reaped'])
            self.assertIn('changed identity', result['error'])
            launch.assert_not_called()

    def test_passing_proof_for_other_pid_is_refused_and_own_server_reaped(self):
        checker_source = b'''import json
def main(args):
    with open(args[-1], 'w') as stream:
        json.dump({'preflight': {'pid': 999, 'kfd_gib': 40}, 'ok': True}, stream)
    return 0
'''
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            (d/'INPUTS.json').write_text(json.dumps({'model': 'unused', 'model_sha256': 'prepared'}))
            child = Mock(pid=123)
            child.poll.side_effect = [None, None, -15, -15]
            connection = Mock()
            connection.__enter__ = Mock(return_value=connection)
            connection.__exit__ = Mock()
            connection.status = 200
            with patch.object(job.Path, 'cwd', return_value=d), \
                 patch.object(job, 'check_inputs'), \
                 patch.dict(job.os.environ, {'FILLER_SMOKE': '1', 'FILLER_ID': 'unit-test'}), \
                 patch.object(job.socket.socket, 'connect_ex', return_value=1), \
                 patch.object(job.urllib.request, 'urlopen', return_value=connection), \
                 patch.object(job.subprocess, 'check_output', return_value=checker_source), \
                 patch.object(job.subprocess, 'Popen', return_value=child):
                self.assertEqual(job.main(), 3)
            result = json.loads((d/'out-smoke/RESULT.json').read_text())
            self.assertFalse(result['ok'])
            self.assertIn('PID/residency mismatch', result['error'])
            child.terminate.assert_called_once_with()
            self.assertTrue(result['own_server_reaped'])


if __name__ == '__main__':
    unittest.main()
