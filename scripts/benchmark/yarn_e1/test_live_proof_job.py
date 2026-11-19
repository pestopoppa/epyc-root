"""Offline controls for row ownership and refusal; never loads a model."""
import json
import hashlib
import os
import signal
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import live_proof_job as job


class LiveProofTests(unittest.TestCase):
    @unittest.skipUnless((job.STORE/'bin/llama-server').exists(), 'pinned v10 store absent')
    def test_full_argv_parses_on_content_pinned_v10_without_loading_model(self):
        # Bind the parser to content, not a directory or a version string.
        expected = {
            'llama-server': '2b49713f0e3c022132393bf302dab954a1e2c1974b91c28d01ce2d192abdfa7b',
            'libllama-common.so.0.0.10303': '0f33ec5cc9967c14c8eeb2d560d6d827301c50cf42dfd701cc1752cc4a7bf9cb',
            'libllama-server-impl.so': 'd9f143d7b056c0bc24a1822fb309ddd01c96df2b63b1b1bc61791e97f519e96f',
        }
        for name, digest in expected.items():
            with (job.STORE/'bin'/name).open('rb') as stream:
                self.assertEqual(hashlib.file_digest(stream, 'sha256').hexdigest(), digest)
        env = dict(os.environ, LD_LIBRARY_PATH=f'{job.STORE}/bin:/opt/rocm/lib:/usr/lib/llvm-20/lib:/opt/AMD/aocc-compiler-5.0.0/lib')
        with tempfile.TemporaryDirectory() as slots:
            command = job.argv('/nonexistent/model.gguf', Path(slots), 4)
            self._assert_v10_parser(command, env)

    def _assert_v10_parser(self, command, env):
        # Help at the END still parses every preceding option, without loading
        # weights. The negative control proves unsupported flags cannot hide.
        bad = subprocess.run(command + ['--load-threads', '4', '--help'], env=env,
                             capture_output=True, text=True, timeout=15)
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn('invalid argument: --load-threads', bad.stdout+bad.stderr)
        good = subprocess.run(command + ['--help'], env=env, capture_output=True,
                              text=True, timeout=15)
        self.assertEqual(good.returncode, 0, good.stdout+good.stderr)
        self.assertIn('--rope-scaling', good.stdout)

    def test_v10_argv_retains_proof_settings_without_new_loader_flag(self):
        command = job.argv('unused.gguf', Path('/unused/slots'), 4)
        self.assertNotIn('--load-threads', command)
        for flag, value in (('-t', '4'), ('-tb', '4'), ('-c', '524288'),
                            ('-np', '1'), ('--rope-scaling', 'yarn'),
                            ('--verbosity', '4'), ('-ctk', 'q8_0'), ('-ctv', 'q8_0')):
            self.assertEqual(command[command.index(flag)+1], value)
        self.assertIn('--no-mmap', command)

    def test_keeper_stop_before_launch_retains_interrupted_result(self):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            (d/'INPUTS.json').write_text('{}')
            with patch.object(job.Path, 'cwd', return_value=d), \
                 patch.object(job, 'check_inputs', side_effect=job.RowStopped('keeper signal 15')), \
                 patch.dict(job.os.environ, {'FILLER_SMOKE': '1'}), \
                 patch.object(job.subprocess, 'Popen') as launch:
                self.assertEqual(job.main(), 75)
            result = json.loads((d/'out-smoke/RESULT.json').read_text())
            self.assertFalse(result['ok'])
            self.assertEqual(result['verdict'], 'PREFLIGHT_INTERRUPTED')
            self.assertTrue(result['own_server_reaped'])
            launch.assert_not_called()

    def test_keeper_sigterm_during_startup_reaps_and_records_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            (d/'INPUTS.json').write_text(json.dumps({'model': 'unused', 'model_sha256': 'prepared'}))
            child = Mock(pid=123)
            child.poll.side_effect = [None, None, -15, -15]
            def terminate(*_args, **_kwargs):
                job.request_stop(signal.SIGTERM, None)
            with patch.object(job.Path, 'cwd', return_value=d), \
                 patch.object(job, 'check_inputs'), \
                 patch.dict(job.os.environ, {'FILLER_SMOKE': '1', 'FILLER_ID': 'unit-test'}), \
                 patch.object(job.socket.socket, 'connect_ex', return_value=1), \
                 patch.object(job.urllib.request, 'urlopen', side_effect=terminate), \
                 patch.object(job.subprocess, 'Popen', return_value=child), \
                 patch.object(job.subprocess, 'check_output') as checker:
                self.assertEqual(job.main(), 75)
            result = json.loads((d/'out-smoke/RESULT.json').read_text())
            self.assertFalse(result['ok'])
            self.assertEqual(result['verdict'], 'PREFLIGHT_INTERRUPTED')
            self.assertIn('15', result['error'])
            self.assertTrue(result['own_server_reaped'])
            self.assertFalse(result['force_preflight'])
            child.terminate.assert_called_once_with()
            child.kill.assert_not_called()
            checker.assert_not_called()

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
