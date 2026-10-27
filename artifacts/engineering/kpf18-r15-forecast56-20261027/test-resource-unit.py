#!/usr/bin/env python3
"""Explicit ESRCH is churn; other OS errors remain failures."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('rss_watch', Path(__file__).with_name('resource-watch.py'))
watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watch)

class ProcChurn(unittest.TestCase):
    def test_vanished_process(self):
        with patch.object(Path, 'read_text', side_effect=ProcessLookupError()):
            self.assertIsNone(watch.proc(999999))

    def test_permission_failure_propagates(self):
        with patch.object(Path, 'read_text', side_effect=PermissionError()):
            with self.assertRaises(PermissionError):
                watch.proc(999999)

    def test_vanished_thread_children(self):
        def read(path):
            if path.name == 'stat':
                return '1 (fixture) S ' + ' '.join(['0'] * 18 + ['123'])
            if path.name == 'status':
                return 'VmRSS: 4 kB\n'
            raise ProcessLookupError()
        with patch.object(Path, 'read_text', read), patch.object(Path, 'iterdir', return_value=iter([Path('/fixture/task/1')])):
            self.assertEqual(watch.proc(999999), (123, 'S', 4, set()))

if __name__ == '__main__':
    unittest.main()
