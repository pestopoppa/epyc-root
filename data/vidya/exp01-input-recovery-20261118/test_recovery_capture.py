"""Model-free controls for the EXP01 scratch runner's custody and failure boundaries."""
from datetime import datetime, timezone
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

import recovery_capture as capture


class RecoveryCaptureTests(unittest.TestCase):
    def test_accepts_legacy_grant_and_refuses_mismatched_fields(self):
        cpus = set(range(24))
        stamp = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
        now = int(time.time())
        with tempfile.TemporaryDirectory() as root:
            grant = Path(root) / f'{capture.ROW}.grant'
            env = dict(FILLER_ID=capture.ROW, FILLER_CPUS='0-23', FILLER_THREADS='24',
                       FILLER_DEADLINE=str(now + 300), FILLER_STOPFILE=root + '/STOP', FILLER_GRANTS_DIR=root)
            fields = f'regions=0-23 start={stamp(now - 60)} end={stamp(now + 600)} holds=q0'
            with patch.dict(os.environ, env, clear=True), patch.object(os, 'sched_getaffinity', return_value=cpus):
                grant.write_text(fields + '\n')
                self.assertIn('holds=q0', capture.allocation(False)['grant_raw'])
                for wrong in (fields.replace('0-23', '1-24'), fields + ' id=wrong',
                              fields.replace(stamp(now + 600), stamp(now + 120))):
                    grant.write_text(wrong + '\n')
                    with self.assertRaisesRegex(ValueError, 'allocator grant bytes'):
                        capture.allocation(False)
                grant.write_text(fields + '\n')
                with self.assertRaisesRegex(ValueError, 'native affinity'):
                    capture.allocation(True)

    def test_native_group_cleanup_reaps_child(self):
        proc = subprocess.Popen(['/bin/bash', '-c', 'sleep 30 & wait'], process_group=0)
        try:
            self.assertIn(proc.pid, capture.owned_members(proc.pid))
            capture.cleanup(proc)
            self.assertIn(proc.returncode, (-signal.SIGTERM, -signal.SIGKILL))
            self.assertEqual(capture.owned_members(proc.pid), set())
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()

    def test_official_precheck_failure_is_filed_and_not_complete(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            with patch.object(capture, 'P', path), patch.object(capture, 'check', side_effect=ValueError('mismatch')), patch.dict(os.environ, {}, clear=True):
                self.assertEqual(capture.run(), 4)
                result = capture.load(path / 'official/RESULT.json')
                self.assertEqual(result['state'], 'partial-or-failed')
                self.assertEqual(result, capture.load(path / 'official' / result['run_id'] / 'TERMINAL.json'))
                self.assertFalse(capture.complete())

    def test_smoke_precheck_failure_does_not_emit_allocator_result(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            native_result = path / 'allocator-result.json'
            env = dict(FILLER_DRYRUN='1', FILLER_SMOKE='1', FILLER_DRYRUN_RESULT_PATH=str(native_result))
            with patch.object(capture, 'P', path), patch.object(capture, 'check', side_effect=ValueError('mismatch')), patch.dict(os.environ, env, clear=True):
                self.assertEqual(capture.run(), 4)
                [terminal] = (path / 'smoke').glob('*/TERMINAL.json')
                self.assertEqual(capture.load(terminal)['mode'], 'smoke-native')
                self.assertFalse(native_result.exists())

    def test_custody_write_refuses_existing_result_without_altering_it(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'result.json'
            capture.write(path, {'state': 'sealed'})
            with self.assertRaises(FileExistsError):
                capture.write(path, {'state': 'rewritten'})
            self.assertEqual(capture.load(path), {'state': 'sealed'})
            self.assertEqual(list(Path(root).iterdir()), [path])


if __name__ == '__main__':
    unittest.main()
