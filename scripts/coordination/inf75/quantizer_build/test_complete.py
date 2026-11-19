import hashlib
import importlib.util
import tempfile
import unittest
from unittest.mock import patch
import check_source
from pathlib import Path

spec = importlib.util.spec_from_file_location('complete', Path(__file__).with_name('complete.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run = self.root / 'runs' / 'build-test'
        self.files = {}
        for name in (*mod.REQUIRED, 'build/bin/libggml.so'):
            path = self.run / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(name.encode())
            self.files[str(path)] = digest(path)
        from prepare import ARCHIVE_SHA, MANIFEST_SHA
        self.files[str(self.run/'source.tar')] = ARCHIVE_SHA
        self.files[str(self.run/'tree-manifest.json')] = MANIFEST_SHA
        self.cc = self.root / 'gcc'
        self.cxx = self.root / 'g++'
        self.cc.write_bytes(b'compiler c')
        self.cxx.write_bytes(b'compiler c++')
        self.manifest = self.run / 'output/compiler.sha256'
        self.manifest.write_text(''.join(f'{digest(p)}  {p}\n' for p in (self.cc, self.cxx)))
        self.files[str(self.manifest)] = digest(self.manifest)
        cache = self.run / 'build/CMakeCache.txt'
        cache.write_text(f'CMAKE_HOME_DIRECTORY:INTERNAL={self.run}/src\n')
        self.files[str(cache)] = digest(cache)
        custody = patch.object(check_source, 'check')
        custody.start()
        self.addCleanup(custody.stop)
        self.record = dict(schema='epyc.inf75.quantizer_build.v1', status='built', source_commit=mod.COMMIT,
                           linkage_rc=0, run_dir=str(self.run), cc=str(self.cc), cxx=str(self.cxx), files=self.files)

    def test_required_and_tampered_artifacts_refuse(self):
        self.assertTrue(mod.valid(self.record, self.root))
        (self.run / 'build/bin/llama-quantize').write_bytes(b'tampered')
        self.assertFalse(mod.valid(self.record, self.root))
        del self.files[str(self.run / 'build/bin/llama-quantize')]
        self.assertFalse(mod.valid(self.record, self.root))

    def test_compiler_contents_and_manifest_are_bound(self):
        self.cc.write_bytes(b'changed')
        self.assertFalse(mod.valid(self.record, self.root))
        self.cc.write_bytes(b'compiler c')
        self.record['cc'] = str(self.cxx)
        self.assertFalse(mod.valid(self.record, self.root))
        self.record['cc'] = str(self.cc)
        self.manifest.write_text(self.manifest.read_text() + 'extra\n')
        self.files[str(self.manifest)] = digest(self.manifest)
        self.assertFalse(mod.valid(self.record, self.root))

    def test_run_and_intermediate_symlinks_refuse(self):
        alias = self.root / 'runs' / 'build-alias'
        alias.symlink_to(self.run, target_is_directory=True)
        self.record['run_dir'] = str(alias)
        self.assertFalse(mod.valid(self.record, self.root))
        self.record['run_dir'] = str(self.run)
        target = self.run / 'nested'
        target.mkdir()
        (target / 'artifact').write_bytes(b'extra')
        (self.run / 'alias').symlink_to(target, target_is_directory=True)
        self.files[str(self.run / 'alias/artifact')] = digest(target / 'artifact')
        self.assertFalse(mod.valid(self.record, self.root))

    def test_diagnostic_unit_never_completes_full_build(self):
        self.record['schema'] = 'epyc.inf75.quantizer_smoke.v1'
        self.record['status'] = 'diagnostic-unit'
        self.assertFalse(mod.valid(self.record, self.root))

    def test_wrong_configured_source_refuses(self):
        (self.run/'build/CMakeCache.txt').write_text('CMAKE_HOME_DIRECTORY:INTERNAL=/shared/staged/src\n')
        self.files[str(self.run/'build/CMakeCache.txt')] = digest(self.run/'build/CMakeCache.txt')
        self.assertFalse(mod.valid(self.record, self.root))

    def test_source_custody_failure_refuses(self):
        with patch.object(check_source, 'check', side_effect=ValueError('bad custody')):
            self.assertFalse(mod.valid(self.record, self.root))

    def test_fabricated_result_refuses(self):
        self.assertFalse(mod.valid(dict(schema='epyc.inf75.quantizer_build.v1', status='built',
                                        source_commit=mod.COMMIT, linkage_rc=0, files={'x': 'x'})))

if __name__ == '__main__':
    unittest.main()
