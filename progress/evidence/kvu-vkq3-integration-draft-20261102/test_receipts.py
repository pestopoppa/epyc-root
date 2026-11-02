import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import receipts


def result(**overrides):
    value = dict(status='completed', cleanup=True, returncode=0, input_bytes_written=5,
                 elapsed_s=0.25, started_monotonic_s=2.0, ended_monotonic_s=2.25, stdout=b'[1, 2, 30]\n', stderr=b'private')
    value.update(overrides)
    return value


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, value=None, mode='full', attempt='a'):
        return receipts.write_attempt(self.root, attempt, mode, value or result(),
                                      expected_input_bytes=5, ceiling_s=10)

    def test_success_and_mode_isolation(self):
        full = self.write()
        qual = self.write(mode='qualification')
        f = json.loads((full / 'result.json').read_text())
        q = json.loads((qual / 'unit.jsonl').read_text())
        self.assertEqual((f['status'], f['verdict'], f['validated_token_count']),
                         ('completed', 'synthetic_input_completed', 3))
        self.assertEqual(q['verdict'], 'excluded_qualification')
        self.assertEqual((f['tokenizer_started_monotonic_s'], f['tokenizer_ended_monotonic_s']), (2.0, 2.25))
        self.assertEqual(json.loads((full / 'unit.jsonl').read_text()), f)
        self.assertTrue((full / 'complete.json').exists())
        self.assertEqual(os.stat(full).st_mode & 0o777, 0o700)
        for item in full.iterdir():
            self.assertEqual(item.stat().st_mode & 0o777, 0o600)
            self.assertNotIn(b'private', item.read_bytes())
        with self.assertRaises(FileExistsError):
            self.write()

    def test_failure_cannot_claim_success(self):
        cases = [(dict(status='timeout'), 'timeout'),
                 (dict(cleanup=False), 'failed_cleanup'),
                 (dict(returncode=2), 'invalid_completion'),
                 (dict(input_bytes_written=4), 'invalid_completion'),
                 (dict(stdout=b'[1, x, 3]\n'), 'invalid_output'),
                 (dict(stdout=b'1 2 30\n'), 'invalid_output'),
                 (dict(stdout=b'[1, 2,]\n'), 'invalid_output'),
                 (dict(stdout=b''), 'invalid_output')]
        for i, (kw, expected) in enumerate(cases):
            path = self.write(result(**kw), attempt=str(i))
            data = json.loads((path / 'result.json').read_text())
            self.assertEqual((data['status'], data['verdict'], data['validated_token_count']),
                             (expected, 'inconclusive', None))

    def test_empty_native_list(self):
        path = self.write(result(stdout=b'[]\n'))
        data = json.loads((path / 'result.json').read_text())
        self.assertEqual((data['status'], data['validated_token_count']), ('completed', 0))

    def test_stderr_tail_is_bounded_private_and_sanitized(self):
        stderr = b'old-secret\n' * 2000 + b'WARNING /home/user/private-prompt\x1b[31m ERROR\n'
        path = self.write(result(stderr=stderr))
        tail = (path / 'stderr-sanitized-tail.txt').read_bytes()
        data = json.loads((path / 'result.json').read_text())
        self.assertLessEqual(len(tail.splitlines()), 32)
        self.assertIn(b'error warning', tail)
        self.assertNotIn(b'private', tail)
        self.assertNotIn(b'old-secret', tail)
        self.assertNotIn(b'\x1b', tail)
        self.assertEqual(data['stderr_captured_bytes'], len(stderr))
        self.assertEqual(data['stderr_tail_scope'], 'fully_drained_capture')
        self.assertEqual((path / 'stderr-sanitized-tail.txt').stat().st_mode & 0o777, 0o600)

    def test_interrupted_capture_cannot_claim_complete_tail(self):
        path = self.write(result(status='output_overflow', stderr=b'error sensitive'))
        data = json.loads((path / 'result.json').read_text())
        self.assertEqual(data['stderr_tail_scope'], 'captured_prefix_may_be_incomplete')
        self.assertEqual((path / 'stderr-sanitized-tail.txt').read_bytes(), b'[redacted] error\n')

    def test_unbounded_or_invalid_stderr_is_rejected_before_attempt(self):
        for value in ('text', b'a' * 65537):
            with self.assertRaises(ValueError):
                self.write(result(stderr=value))
            self.assertFalse((self.root / 'full-a').exists())

    def test_interrupted_write_has_no_marker_and_retains_partial(self):
        real = receipts._durable_file
        def fail(directory, name, data):
            if name == 'unit.jsonl':
                (directory / '.unit.jsonl.tmp').write_bytes(b'{')
                raise OSError('injected partial write')
            return real(directory, name, data)
        with mock.patch.object(receipts, '_durable_file', side_effect=fail):
            with self.assertRaises(OSError):
                self.write()
        directory = self.root / 'full-a'
        self.assertTrue((directory / 'result.json').exists())
        self.assertTrue((directory / '.unit.jsonl.tmp').exists())
        self.assertFalse((directory / 'complete.json').exists())

    def test_rejects_unsafe_inputs(self):
        for attempt in ('../x', '', '.bad', 'a/b'):
            with self.assertRaises(ValueError):
                self.write(attempt=attempt)
        os.chmod(self.root, 0o755)
        with self.assertRaises(ValueError):
            self.write()

if __name__ == '__main__':
    unittest.main()
