import tempfile
import unittest
from pathlib import Path
from affinity_guard import AffinityError, verify_threads


class AffinityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.proc = self.root / '42'
        (self.proc / 'task' / '42').mkdir(parents=True)
        (self.proc / 'task' / '43').mkdir()
        # Linux stat: field 3 starts after the comm, starttime is field 22.
        (self.proc / 'stat').write_text('42 (name with spaces) ' + ' '.join(['S'] + ['0'] * 18 + ['123']) + '\n')

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, getter, ticks=123):
        return verify_threads(42, ticks, {2, 3}, proc_root=self.root, get_affinity=getter)

    def test_allowed_threads(self):
        self.assertEqual(self.check(lambda tid: {2} if tid == 42 else {2, 3}), {42: [2], 43: [2, 3]})

    def test_refuses_escape_identity_and_missing_thread(self):
        for getter, ticks in ((lambda _: {2, 4}, 123), (lambda _: set(), 123), (lambda _: {2}, 124)):
            with self.assertRaises(AffinityError):
                self.check(getter, ticks)
        with self.assertRaises(AffinityError):
            self.check(lambda _: (_ for _ in ()).throw(ProcessLookupError()))

    def test_refuses_thread_churn(self):
        def getter(tid):
            if tid == 42:
                (self.proc / 'task' / '44').mkdir()
            return {2}
        with self.assertRaises(AffinityError):
            self.check(getter)


if __name__ == '__main__':
    unittest.main()
