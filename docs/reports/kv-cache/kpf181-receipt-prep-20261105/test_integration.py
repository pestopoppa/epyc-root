import ast
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent

class IntegrationTests(unittest.TestCase):
    def test_entry_is_disabled_and_receipt_guarded(self):
        source = (ROOT / 'qualification_entry.REVIEW.py').read_text()
        tree = ast.parse(source)
        run = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run')
        text = ast.get_source_segment(source, run)
        self.assertNotIn('sha(p)', text)
        self.assertIn('if RECEIPT_SHA256 is None:raise Refused', text)
        self.assertEqual(text.count('verify_model_receipt(RECEIPT_PATH, RECEIPT_SHA256)'), 2)
        self.assertIn('CUSTODY_PROVIDER=None', source)
        for name in ('launch.REVIEW-ONLY.sh', 'job.REVIEW-ONLY.sh'):
            p = subprocess.run(['/bin/bash', str(ROOT / name)], capture_output=True, timeout=3)
            self.assertEqual(p.returncode, 78)
            self.assertNotIn('exec ', (ROOT / name).read_text())

if __name__ == '__main__': unittest.main()
