"""Reject incomplete IQK controls, stale artifacts and undefined export lookalikes."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('cafe3_hip', Path(__file__).with_name('driver.py'))
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


class BindingTest(unittest.TestCase):
    def test_compiled_and_iqk_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            run = d / 'runs' / 'one'
            run.mkdir(parents=True)
            artifact = run / 'server.o'
            artifact.write_bytes(b'object')
            (run / 'iqk-negative.log').write_text('enum-constexpr-conversion')
            (run / 'iqk-fixed.log').write_text('')
            r = dict(inputs={'source': 'pinned'}, base=driver.BASE, run=str(run), mode='smoke',
                     files={str(p): driver.digest(p) for p in run.iterdir()})
            with patch.object(driver, 'D', d), patch.object(driver, 'inputs', return_value=r['inputs']), patch.object(driver.subprocess, 'check_output', return_value=b'\n'.join(driver.MARKERS)):
                driver.validate(r)
                with patch.object(driver.subprocess, 'check_output', return_value=b'old binary'):
                    with self.assertRaisesRegex(ValueError, 'marker'):
                        driver.validate(r)
                saved = r['files'].pop(str(artifact))
                with self.assertRaisesRegex(ValueError, 'unbound compiled'):
                    driver.validate(r)
                r['files'][str(artifact)] = saved
                artifact.write_bytes(b'tampered')
                with self.assertRaisesRegex(ValueError, 'artifact'):
                    driver.validate(r)
                artifact.write_bytes(b'object')
                for text, error in [('unexpected pass', 'negative witness'), ('enum-constexpr-conversion', None)]:
                    (run / 'iqk-negative.log').write_text(text)
                    r['files'][str(run / 'iqk-negative.log')] = driver.digest(run / 'iqk-negative.log')
                    if error:
                        with self.assertRaisesRegex(ValueError, error):
                            driver.validate(r)
                    else:
                        driver.validate(r)
                r['base'] = 'stale'
                with self.assertRaisesRegex(ValueError, 'binding'):
                    driver.validate(r)

    def test_exact_defined_code_exports(self):
        for output in ('iqk_mul_mat U\n', 'iqk_mul_mat_helper T 0\n', 'iqk_mul_mat D 0\n', ''):
            with self.subTest(output=output), patch.object(driver.subprocess, 'check_output', return_value=output):
                with self.assertRaisesRegex(ValueError, 'exports missing'):
                    driver.require_exports('cpu.so', ['iqk_mul_mat'])
        with patch.object(driver.subprocess, 'check_output', return_value='iqk_mul_mat T 10\nggml_iqk_try_mul_mat W 20\n'):
            driver.require_exports('cpu.so', ['iqk_mul_mat', 'ggml_iqk_try_mul_mat'])


if __name__ == '__main__':
    unittest.main()
