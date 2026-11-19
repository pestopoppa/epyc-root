"""Model-free integrity and owned compiler-session stop regressions."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('restore', Path(__file__).resolve().parents[2] / 'scripts/speech/stt5_transcribe_restore.py')
restore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restore)


class RestoreTest(unittest.TestCase):
    def test_artifact_requires_all_native_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'binary'
            for data in (b'not ELF', b'\x7fELF' + restore.WITNESSES[0]):
                p.write_bytes(data)
                with self.assertRaises(ValueError):
                    restore.binary_evidence(p)
            p.write_bytes(b'\x7fELF' + b'\0'.join(restore.WITNESSES))
            self.assertEqual(restore.binary_evidence(p), restore.sha(p))

    def test_refuse_commit_overlay_or_untracked_source_drift(self):
        import hashlib
        cfg = dict(source='/unused', commit='approved',
                   diff_sha256=hashlib.sha256(b'patch').hexdigest(), pins={})
        for answers in ([b'wrong'], [b'approved', b'wrong'],
                        [b'approved', b'patch', b'extra-input']):
            with mock.patch.object(restore.subprocess, 'check_output', side_effect=answers):
                with self.assertRaises(ValueError):
                    restore.verify(cfg)
        with mock.patch.object(restore.subprocess, 'check_output',
                               side_effect=[b'approved', b'patch', b'']):
            restore.verify(cfg)

    def test_exclusive_start_cannot_redraw_stopped_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'START.json'
            restore.write_new(p, {'status': 'exposed'})
            with self.assertRaises(FileExistsError):
                restore.write_new(p, {'status': 'replaced'})
            self.assertIn('exposed', p.read_text())

    def test_stop_reaps_captured_compiler_session(self):
        # Simulate a build wrapper and its compiler, both resistant to SIGTERM.
        child = subprocess.Popen(['python3', '-c',
            'import os,signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); '
            'pid=os.fork(); print(pid,flush=True) if pid else None; time.sleep(60)'],
            stdout=subprocess.PIPE, text=True, start_new_session=True)
        try:
            compiler = int(child.stdout.readline())
            self.assertIn(compiler, restore.session_members(child.pid))
            restore.drain(child)
            self.assertIsNotNone(child.poll())
            self.assertEqual(restore.session_members(child.pid), [])
        finally:
            restore.drain(child)
            child.stdout.close()


if __name__ == '__main__':
    unittest.main()
