import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import types
import unittest

spec = importlib.util.spec_from_file_location('continuation', Path(__file__).with_name('continuation.py'))
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


class ResumeTests(unittest.TestCase):
    def test_resume_preserves_old_units_and_separates_new_output(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            old = root / 'prior.jsonl'
            row = {'item': 0, 'arm': 'FULL', 'ok': True, 'aligned': True}
            old.write_text(json.dumps(row) + '\n')
            new = {'item': 0, 'arm': 'EA', 'ok': True, 'aligned': True}
            m = types.SimpleNamespace(SMOKE=False, units=lambda: [new])
            contract = {'checkpoint': str(old), 'checkpoint_sha256': hashlib.sha256(old.read_bytes()).hexdigest(),
                        'row': 'r2', 'build_sha256': 'proof'}
            c.configure(m, root, contract)
            self.assertEqual(m.units(), [row, new])
            self.assertEqual(m.RES, str(root / 'out/results.jsonl'))
            self.assertEqual(old.read_text(), json.dumps(row) + '\n')
            self.assertEqual(m.ROW, 'r2')

    def test_corrupted_or_duplicate_checkpoint_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'checkpoint'
            row = {'item': 0, 'arm': 'L4', 'ok': True, 'aligned': True}
            p.write_text((json.dumps(row) + '\n') * 2)
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                c.checked_jsonl(p, hashlib.sha256(p.read_bytes()).hexdigest())
            with self.assertRaisesRegex(ValueError, 'digest'):
                c.checked_jsonl(p, 'wrong')

    def test_terminal_checker_accepts_native_names_and_rejects_window_end(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'RESULT.json'
            for verdict, smoke, expected in [('L4_KEEP', False, True),
                    ('L4_BELOW_EA(diff +0.0 pts, p 1.0, b 0, c 0)', False, True),
                    ('FUTILITY_CONTROL', False, True), ('STOPPED', False, False),
                    ('L4_KEEP', True, False), ('SMOKE_OK', True, False)]:
                p.write_text(json.dumps({'complete': True, 'smoke': smoke, 'verdict': verdict}))
                self.assertEqual(c.complete(p), expected)


if __name__ == '__main__':
    unittest.main()
