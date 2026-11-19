"""Application DSO closure and mapped-inode controls; never execute a native ELF."""
import copy
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_execution_admission import load
import test_execution_admission as fixtures


class NativeCustody(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.subject = load(HERE / 'execution_admission.py', 'native_custody_subject')
        self.proc = self.root / 'proc/123'
        self.proc.mkdir(parents=True)
        self.stat = '123 (server name) S ' + ' '.join(['0'] * 18 + ['456'] + ['0'] * 5)
        (self.proc / 'stat').write_text(self.stat)
        names = {'server_impl': 'libllama-server-impl.so', 'llama': 'libllama.so.0',
                 'llama_common': 'libllama-common.so.0', 'mtmd': 'libmtmd.so.0',
                 'ggml': 'libggml.so.0', 'ggml_base': 'libggml-base.so.0',
                 'ggml_cpu': 'libggml-cpu.so.0', 'ggml_hip': 'libggml-hip.so.0'}
        self.paths = {role: self.root / name for role, name in names.items()}
        for role, path in self.paths.items():
            path.write_text('private ' + role)
        self.seal = {'execution': {'artifacts': {k: str(v) for k, v in self.paths.items()}},
                     'sources': {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in self.paths.values()}}
        self.maps = '\n'.join(self.map_line(p) for p in self.paths.values())
        (self.proc / 'maps').write_text(self.maps)

    def map_line(self, path):
        st = path.stat()
        return f'1000-2000 r-xp 00000000 {os.major(st.st_dev):x}:{os.minor(st.st_dev):x} {st.st_ino} {path}'

    def check(self):
        return self.subject.native_mappings(self.seal, 123, self.root / 'proc')

    def test_complete_closure_and_duplicate_segments(self):
        (self.proc / 'maps').write_text(self.maps + '\n' + self.maps)
        result = self.check()
        self.assertEqual(set(result), set(self.paths))
        self.assertEqual(result['server_impl']['sha256'], self.seal['sources'][str(self.paths['server_impl'])])

    def test_each_missing_mapping_refuses(self):
        for role, path in self.paths.items():
            with self.subTest(role=role):
                (self.proc / 'maps').write_text('\n'.join(x for x in self.maps.splitlines() if not x.endswith(str(path))))
                with self.assertRaisesRegex(ValueError, 'missing or mismatched'): self.check()

    def test_each_mapped_artifact_drift_refuses(self):
        for role, path in self.paths.items():
            with self.subTest(role=role):
                raw = path.read_bytes()
                try:
                    path.write_bytes(raw + b'drift')
                    with self.assertRaisesRegex(ValueError, 'artifact drift'): self.check()
                finally: path.write_bytes(raw)

    def test_replaced_inode_deleted_and_extra_application_library_refuse(self):
        path = self.paths['server_impl']
        replacement = self.root / 'replacement'
        replacement.write_bytes(path.read_bytes())
        replacement.replace(path)
        with self.assertRaisesRegex(ValueError, 'missing or mismatched'): self.check()
        self.maps = '\n'.join(self.map_line(p) for p in self.paths.values())
        (self.proc / 'maps').write_text(self.maps.replace(str(path), str(path) + ' (deleted)'))
        with self.assertRaisesRegex(ValueError, 'deleted'): self.check()
        extra = self.root / 'libggml-foreign.so'; extra.write_text('foreign')
        (self.proc / 'maps').write_text(self.maps + '\n' + self.map_line(extra))
        with self.assertRaisesRegex(ValueError, 'unsealed'): self.check()

    def test_aliased_roles_refuse(self):
        self.seal['execution']['artifacts']['mtmd'] = str(self.paths['llama'])
        with self.assertRaisesRegex(ValueError, 'aliased'): self.check()

    def test_missing_pin_and_changed_birth_refuse(self):
        self.seal['sources'].pop(str(self.paths['server_impl']))
        with self.assertRaisesRegex(ValueError, 'artifact drift'): self.check()
        self.seal['sources'][str(self.paths['server_impl'])] = hashlib.sha256(self.paths['server_impl'].read_bytes()).hexdigest()
        original = Path.read_text
        count = 0
        def read(path, *args, **kwargs):
            nonlocal count
            if path == self.proc / 'stat':
                count += 1
                if count == 2: return self.stat.replace('456', '457')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', read):
            with self.assertRaisesRegex(ValueError, 'child changed'): self.check()

    def test_legacy_eight_role_inventory_is_refused(self):
        fixture = fixtures.ExecutionAdmission(); fixture.setUp()
        try:
            seal = copy.deepcopy(fixture.seal)
            for role in ('server_impl', 'llama', 'llama_common', 'mtmd'):
                seal['execution']['artifacts'].pop(role, None)
            with self.assertRaisesRegex(ValueError, 'complete current execution custody'):
                fixture.gate.custody(seal)
        finally: fixture.doCleanups()


if __name__ == '__main__': unittest.main()
