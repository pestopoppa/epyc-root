"""Reject stale source, tampered artifacts and incomplete compiled features."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('cafe3_build', Path(__file__).with_name('driver.py'))
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


class BindingTest(unittest.TestCase):
    def test_smoke_binding_and_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            run = d / 'runs' / 'one'
            run.mkdir(parents=True)
            artifact = run / 'server.o'
            artifact.write_bytes(b'object')
            r = dict(inputs={'source': 'pinned'}, base=driver.BASE, run=str(run), mode='smoke',
                     files={str(artifact): driver.digest(artifact)})
            with patch.object(driver, 'D', d), patch.object(driver, 'inputs', return_value=r['inputs']), patch.object(driver.subprocess, 'check_output', return_value=b'\n'.join(driver.MARKERS)):
                driver.validate(r)
                with patch.object(driver.subprocess, 'check_output', return_value=b'old binary'):
                    with self.assertRaisesRegex(ValueError, 'marker'):
                        driver.validate(r)
                artifact.write_bytes(b'tampered')
                with self.assertRaisesRegex(ValueError, 'artifact'):
                    driver.validate(r)
                r['base'] = 'stale'
                with self.assertRaisesRegex(ValueError, 'binding'):
                    driver.validate(r)



if __name__ == '__main__':
    unittest.main()
