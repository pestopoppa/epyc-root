"""Regression tests using real ELF exports and the full receipt validator."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('hip_build_driver', Path(__file__).with_name('driver.py'))
driver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(driver)


class ExportChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='cafe4-exports-', dir='/mnt/raid0/llm/tmp/df2')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run = self.root / 'runs' / 'build-test'
        self.bin = self.run / 'build/bin'
        self.bin.mkdir(parents=True)
        self.cpu = self.bin / 'libggml-cpu.so'
        self.hip = self.bin / 'libggml-hip.so'
        self.library(self.cpu, 'void iqk_mul_mat(void) {} void ggml_iqk_try_mul_mat(void) {}')
        self.library(self.hip, 'void ggml_backend_cuda_reg(void) {} const char *arch="gfx90a";')
        (self.bin / 'cafe4-mtp-rollback').write_bytes(b'\n'.join(driver.MARKERS))
        (self.run / 'build/CMakeCache.txt').write_text('\n'.join([
            driver.IQK_COMPAT, driver.CLANGXX, 'GGML_HIP:BOOL=ON',
            'CMAKE_HIP_ARCHITECTURES:STRING=gfx90a']))
        libraries = ('libllama.so', 'libllama-common.so', 'libggml.so',
                     'libggml-base.so', 'libggml-cpu.so', 'libggml-hip.so')
        (self.run / 'linkage.log').write_text('\n'.join(
            f'{name} => {self.bin / name} (0x123)' for name in libraries))

    def library(self, path, code):
        subprocess.run(['cc', '-x', 'c', '-shared', '-fPIC', '-o', str(path), '-'],
                       input=code, text=True, check=True, capture_output=True)

    def validate(self, omit=None):
        native = {'files': {'fixture': 'bound'}}
        record = dict(mode='build', run=str(self.run), input_files=native['files'],
                      source_commit=driver.COMMIT, patch_sha256=driver.PATCH,
                      files={str(p): driver.digest(p) for p in self.run.rglob('*')
                             if p.is_file() and p != omit})
        with patch.object(driver, 'D', self.root), patch.object(driver, 'inputs', return_value=native):
            driver.validate(record)

    def test_actual_v10_exports_pass_full_validator(self):
        self.validate()

    def test_undefined_iqk_import_does_not_prove_implementation(self):
        self.library(self.cpu, 'extern void iqk_mul_mat(void); void ggml_iqk_try_mul_mat(void) {iqk_mul_mat();}')
        with self.assertRaisesRegex(ValueError, 'compiled exports missing'):
            self.validate()

    def test_symbol_substring_is_rejected(self):
        self.library(self.hip, 'void ggml_backend_cuda_reg_wrong(void) {} const char *arch="gfx90a";')
        with self.assertRaisesRegex(ValueError, 'compiled exports missing'):
            self.validate()

    def test_old_incorrect_hip_name_is_rejected(self):
        self.library(self.hip, 'void ggml_backend_hip_reg(void) {} const char *arch="gfx90a";')
        with self.assertRaisesRegex(ValueError, 'compiled exports missing'):
            self.validate()

    def test_cpu_library_must_remain_hash_bound(self):
        with self.assertRaisesRegex(ValueError, 'IQK library not hash-bound'):
            self.validate(omit=self.cpu)

    def test_hip_library_must_remain_hash_bound(self):
        with self.assertRaisesRegex(ValueError, 'HIP library not hash-bound'):
            self.validate(omit=self.hip)

    def test_cuda_registration_without_gfx90a_is_rejected(self):
        self.library(self.hip, 'void ggml_backend_cuda_reg(void) {}')
        with self.assertRaisesRegex(ValueError, 'gfx90a image marker missing'):
            self.validate()

    def test_nonlocal_linkage_is_rejected(self):
        log = self.run / 'linkage.log'
        log.write_text(log.read_text().replace(str(self.bin / 'libllama.so'), '/elsewhere/libllama.so'))
        with self.assertRaisesRegex(ValueError, 'nonlocal library'):
            self.validate()


if __name__ == '__main__':
    unittest.main()
