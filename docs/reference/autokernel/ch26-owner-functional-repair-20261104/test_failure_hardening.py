import os
from pathlib import Path
import stat
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
import native_functional  # adds native/ to module search path
import capture_worker
import owned_capture
import perf_mmap


class FailureHardening(unittest.TestCase):
    def test_post_link_directory_fsync_failure_removes_owned_result(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d)/'result.json'; original = os.fsync
            def fail_directory(fd):
                if stat.S_ISDIR(os.fstat(fd).st_mode): raise OSError('directory fsync failure')
                return original(fd)
            with patch.object(capture_worker.os,'fsync',side_effect=fail_directory):
                with self.assertRaises(OSError): capture_worker.persist({'measurement_admission':'none','errors':[]},dest)
            self.assertFalse(dest.exists())
            self.assertEqual(list(Path(d).iterdir()),[])

    def test_preexisting_destination_is_not_removed(self):
        with tempfile.TemporaryDirectory() as d:
            dest=Path(d)/'result.json'; dest.write_text('existing')
            with self.assertRaises(FileExistsError): capture_worker.persist({'measurement_admission':'none','errors':[]},dest)
            self.assertEqual(dest.read_text(),'existing')

    def test_replaced_destination_is_not_removed_on_fsync_failure(self):
        with tempfile.TemporaryDirectory() as d:
            dest=Path(d)/'result.json'; original=os.fsync
            def swap_then_fail(fd):
                if stat.S_ISDIR(os.fstat(fd).st_mode):
                    dest.unlink(); dest.write_text('replacement'); raise OSError('directory fsync failure')
                return original(fd)
            with patch.object(capture_worker.os,'fsync',side_effect=swap_then_fail):
                with self.assertRaises(OSError): capture_worker.persist({'measurement_admission':'none','errors':[]},dest)
            self.assertEqual(dest.read_text(),'replacement')

    def test_stuck_drain_leaves_archive_fd_owned_until_process_exit(self):
        cap=owned_capture.Capture.__new__(owned_capture.Capture)
        cap.cleaned=False; cap.state='request'; cap.stop_event=Mock(); cap.thread=Mock(); cap.thread.is_alive.return_value=True
        cap.errors=[]; cap.archive=Mock()
        cap.abort()
        cap.thread.join.assert_called_once(); cap.archive.abort.assert_not_called()
        self.assertEqual(cap.state,'failed'); self.assertTrue(cap.errors)

    def test_copy_overwrite_refuses_before_tail_advance(self):
        session=perf_mmap.Session.__new__(perf_mmap.Session)
        session.state='running'; session.data_offset=0; session.data_size=64; session.mem=bytes(64)
        session.atomics=Mock(); session.atomics.acquire.side_effect=[0,0,65]; session.errors=[]
        result=session.drain()
        self.assertTrue(any('overwritten' in x for x in result['errors']))
        session.atomics.release.assert_not_called()

    def test_copy_without_overwrite_advances_to_captured_head(self):
        session=perf_mmap.Session.__new__(perf_mmap.Session)
        session.state='running'; session.data_offset=0; session.data_size=64; session.mem=bytes(64)
        session.atomics=Mock(); session.atomics.acquire.side_effect=[0,0,8]; session.errors=[]
        result=session.drain()
        self.assertEqual(result['errors'],[]); session.atomics.release.assert_called_once_with(perf_mmap.TAIL,0)

if __name__=='__main__': unittest.main()
