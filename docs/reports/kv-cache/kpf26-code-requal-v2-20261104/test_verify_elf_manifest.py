import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('verify_closure', Path(__file__).with_name('verify_elf_manifest.py'))
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


class ClosureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name); self.bin = self.root/'bin'; self.bin.mkdir()
        for name in ['llama-server','libllama-server-impl.so','libllama-common.so.0','libmtmd.so.0']:
            (self.bin/name).write_bytes(('ELF fixture '+name).encode())
        self.system = self.root/'libc.so.6'; self.system.write_bytes(b'system fixture')
        self.manifest = self.root/'BINARIES.sha256'
        self.manifest.write_text(''.join(f'{verify.digest(p)}  {p.name}\n' for p in self.bin.iterdir()))
        self.closure = {p.name:str(p) for p in self.bin.iterdir() if p.name.startswith('lib')}
        self.closure['libc.so.6']=str(self.system)
        self.baseline = {k:{'path':p,'sha256':verify.digest(p)} for k,p in self.closure.items()}

    def tearDown(self): self.tmp.cleanup()

    def check(self): return verify.verify(self.bin,self.manifest,self.baseline,self.closure)

    def test_complete_bin_and_loader_identity_pass(self):
        result = self.check()
        self.assertEqual(result['bin_files'],4)
        self.assertEqual(result['loader_files'],4)
        self.assertEqual(len(result['own_dsos']),3)

    def test_omitted_common_dso_is_refused(self):
        self.manifest.write_text('\n'.join(l for l in self.manifest.read_text().splitlines() if 'libllama-common' not in l)+'\n')
        with self.assertRaisesRegex(ValueError,'inventory mismatch'): self.check()

    def test_modified_server_impl_is_refused(self):
        (self.bin/'libllama-server-impl.so').write_bytes(b'different ELF fixture')
        with self.assertRaisesRegex(ValueError,'digest mismatch'): self.check()

    def test_project_library_outside_bin_is_refused_even_if_pinned(self):
        outside=self.root/'libmtmd.so.0';outside.write_bytes(b'foreign mtmd')
        self.closure[outside.name]=str(outside)
        self.baseline[outside.name]={'path':str(outside),'sha256':verify.digest(outside)}
        with self.assertRaisesRegex(ValueError,'outside manifest/bin'): self.check()

    def test_changed_external_dependency_is_refused(self):
        self.system.write_bytes(b'changed system fixture')
        with self.assertRaisesRegex(ValueError,'loader identity changed'): self.check()

    def test_extra_file_and_changed_closure_membership_are_refused(self):
        (self.bin/'libunexpected.so').write_bytes(b'extra')
        with self.assertRaisesRegex(ValueError,'inventory mismatch'): self.check()
        (self.bin/'libunexpected.so').unlink()
        self.closure.pop('libc.so.6')
        with self.assertRaisesRegex(ValueError,'membership changed'): self.check()

    def test_unresolved_loader_dependencies_are_refused(self):
        with self.assertRaisesRegex(ValueError,'unresolved'):
            verify.loader_paths('libllama-common.so.0 => not found\n')


if __name__=='__main__':unittest.main()
