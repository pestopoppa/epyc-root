import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('journal', Path(__file__).with_name('journal.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class JournalTests(unittest.TestCase):
    def test_complete_receipt_and_exclusive_path(self):
        with tempfile.TemporaryDirectory() as root:
            j = m.BuildJournal(root, 'control.jsonl', 'qualification', 1)
            j.start(0, 'a' * 64)
            j.end(0, 0, True)
            j.complete(True)
            j.close()
            records = [json.loads(x) for x in (Path(root) / 'control.jsonl').read_text().splitlines()]
            self.assertEqual([x['event'] for x in records], ['begin', 'command-start', 'command-end', 'complete'])
            with self.assertRaises(FileExistsError):
                m.BuildJournal(root, 'control.jsonl', 'qualification', 1)

    def test_failed_cleanup_is_terminal(self):
        with tempfile.TemporaryDirectory() as root:
            j = m.BuildJournal(root, 'target.jsonl', 'target', 1)
            j.start(0, 'b' * 64)
            j.end(0, 0, False)
            with self.assertRaises(ValueError):
                j.complete(True)
            j.close()
            self.assertEqual(json.loads((Path(root) / 'target.jsonl').read_text().splitlines()[-1])['event'], 'partial')

    def test_order_evidence_and_symlink_refusal(self):
        with tempfile.TemporaryDirectory() as root:
            j = m.BuildJournal(root, 'events', 'target', 1)
            with self.assertRaises(ValueError):
                j.start(1, 'c' * 64)
            j.start(0, 'c' * 64)
            j.end(0, 0, True)
            with self.assertRaises(ValueError):
                j.complete(False)
            j.close()
            os.symlink('events', Path(root) / 'alias')
            with self.assertRaises(FileExistsError):
                m.BuildJournal(root, 'alias', 'target', 1)

    def test_refuses_unsafe_parent(self):
        with tempfile.TemporaryDirectory() as root:
            os.chmod(root, 0o777)
            with self.assertRaises(PermissionError):
                m.BuildJournal(root, 'events', 'target', 1)

    def test_fsync_failure_poison_blocks_retry_and_completion(self):
        with tempfile.TemporaryDirectory() as root:
            j = m.BuildJournal(root, 'events', 'target', 1)
            j.start(0, 'a' * 64)
            with patch.object(m.os, 'fsync', side_effect=OSError('injected')):
                with self.assertRaises(OSError):
                    j.end(0, 0, True)
            with self.assertRaisesRegex(OSError, 'poisoned'):
                j.end(0, 0, True)
            with self.assertRaises(ValueError):
                j.complete(True)
            j.close()
            records = [json.loads(x) for x in (Path(root) / 'events').read_text().splitlines()]
            self.assertNotIn('complete', [x['event'] for x in records])

    def test_constructor_fsync_failure_closes_both_descriptors(self):
        for effects in ([OSError('directory fsync')], [None, OSError('begin fsync')]):
            with self.subTest(effects=effects), tempfile.TemporaryDirectory() as root:
                real_close = os.close
                closed = []

                def record_close(fd):
                    closed.append(fd)
                    return real_close(fd)

                with patch.object(m.os, 'close', side_effect=record_close), patch.object(m.os, 'fsync', side_effect=effects):
                    with self.assertRaises(OSError):
                        m.BuildJournal(root, 'events', 'target', 1)
                self.assertEqual(len(closed), 2)
                self.assertTrue((Path(root) / 'events').exists())

    def test_partial_write_poison_blocks_next_transition(self):
        with tempfile.TemporaryDirectory() as root:
            j = m.BuildJournal(root, 'events', 'target', 1)
            real_write = os.write
            calls = []

            def partial_then_fail(fd, data):
                if calls:
                    raise OSError('injected after partial write')
                calls.append(True)
                return real_write(fd, data[:4])

            with patch.object(m.os, 'write', side_effect=partial_then_fail):
                with self.assertRaises(OSError):
                    j.start(0, 'a' * 64)
            with self.assertRaisesRegex(OSError, 'poisoned'):
                j.start(0, 'a' * 64)
            j.close()

if __name__ == '__main__':
    unittest.main()
