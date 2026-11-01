import hashlib
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('matrix_preflight', here / 'matrix_preflight.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
DRIVER = Path('/mnt/raid0/llm/worktrees/research-kvu12-run/artifacts/np_context_kvu_cpu_study_20261020/driver/kvu_cpu_matrix.py')


class Preflight(unittest.TestCase):
    def test_bound_source_selects_all_pairs(self):
        result = p.plan(DRIVER.read_bytes())
        self.assertEqual([(c['np'], c['length']) for c in result['cells']],
                         [(8, '32k'), (4, '64k'), (8, '48k'), (4, '96k'), (8, '64k'), (4, '128k')])
        self.assertEqual(result['base_driver_sha256'], p.BASE_SHA256)
        self.assertEqual(result['cells'][2]['context_tokens'], 49152)

    def test_rejects_changed_source(self):
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            p.plan(DRIVER.read_bytes() + b'\n# changed\n')

    def test_rejects_missing_matrix_cell(self):
        data = DRIVER.read_bytes()
        changed = data.replace(p.OLD.encode(), p.OLD.replace('"64k": 65536, ', '').encode())
        with patch.object(p, 'BASE_SHA256', hashlib.sha256(changed).hexdigest()):
            with self.assertRaisesRegex(ValueError, 'length map'):
                p.plan(changed)

    def test_driver_matrix_refuses_unknown_length(self):
        source = p.patched_source(DRIVER.read_bytes())
        with self.assertRaisesRegex(ValueError, 'exact cell'):
            p.driver_matrix(source, 8, 'bogus')

    def test_pool_fit_refuses_overflow(self):
        source = p.patched_source(DRIVER.read_bytes())
        with self.assertRaisesRegex(ValueError, 'exact cell'):
            p.driver_matrix(source, 8, '96k')


if __name__ == '__main__':
    unittest.main()
