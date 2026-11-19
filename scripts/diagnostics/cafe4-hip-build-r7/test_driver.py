"""Exercise the shared ELF regressions and R7 marker rejection in both modes."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HERE = Path(__file__).parent
shared = load('shared_hip_tests', HERE.parent / 'cafe4-hip-build/test_driver.py')
driver = load('r7_driver', HERE / 'driver.py')
shared.driver = driver
ExportChecks = shared.ExportChecks


class TokenWitnessChecks(ExportChecks):
    def test_each_token_marker_required_in_build_and_smoke(self):
        for mode in ('build', 'smoke'):
            artifact = self.bin / 'cafe4-mtp-rollback' if mode == 'build' else self.run / 'candidate.o'
            (self.run / 'iqk-negative.log').write_text('enum-constexpr-conversion')
            (self.run / 'iqk-fixed.log').write_text('')
            for missing in (b'CAFE4_BOUNDARY', b'CAFE4_PROPOSAL', b'CAFE4_VERIFY_TOKEN', b'rollback-configure'):
                with self.subTest(mode=mode, missing=missing):
                    artifact.write_bytes(b'\n'.join(m for m in driver.MARKERS if m != missing))
                    native = {'files': {'fixture': 'bound'}}
                    record = dict(mode=mode, run=str(self.run), input_files=native['files'],
                                  source_commit=driver.COMMIT, patch_sha256=driver.PATCH,
                                  files={str(p): driver.digest(p) for p in self.run.rglob('*') if p.is_file()})
                    with patch.object(driver, 'D', self.root), patch.object(driver, 'inputs', return_value=native):
                        with self.assertRaisesRegex(ValueError, 'compiled option/control marker missing'):
                            driver.validate(record)


if __name__ == '__main__':
    unittest.main()
