import copy
import hashlib
import os
from pathlib import Path
import tempfile
import unittest

from gdb_job import validate_runtime_custody


class RuntimeCustodyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        libs = {}
        paths = [root / n for n in ('libggml.so', 'libggml-base.so', 'libggml-cpu.so', 'libllama.so', 'libllama-common.so')]
        model = root / 'model.gguf'
        for path in paths + [model]:
            path.write_bytes(path.name.encode())
        for path in paths:
            libs[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        def mapping(path):
            st = path.stat()
            return f'001-002 r--p 00000000 {os.major(st.st_dev):x}:{os.minor(st.st_dev):x} {st.st_ino} {path}\n'
        raw = ''.join(map(mapping, paths + [model]))
        self.config = dict(libraries=libs, model_path=str(model), source_commit='source', patch_sha256='patch', receipt_sha256='receipt', model_sha256='model')
        self.witness = dict(pid=123, birth_ticks=456, samples=[])
        for mode in (0, 8):
            for point in ('decode_entry', 'restore_dst_1', 'restore_dst_2'):
                self.witness['samples'].append(dict(mode=mode, point=point, pid=123, birth_ticks=456, maps_text=raw,
                    maps_sha256=hashlib.sha256(raw.encode()).hexdigest(), libraries=libs.copy(),
                    **{k:self.config[k] for k in ('source_commit','patch_sha256','receipt_sha256','model_sha256')}))
        self.addCleanup(self.tmp.cleanup)

    def test_valid_and_changed_library(self):
        validate_runtime_custody(self.witness, self.config)
        Path(next(iter(self.config['libraries']))).write_bytes(b'tampered')
        with self.assertRaises(ValueError): validate_runtime_custody(self.witness, self.config)

    def test_forged_and_incomplete_witnesses_fail(self):
        mutations = [lambda w: w['samples'][0].update(maps_sha256='0'*64),
                     lambda w: w['samples'][0].update(pid=99),
                     lambda w: w['samples'][0].update(model_sha256='wrong'),
                     lambda w: w['samples'][0].update(libraries={}),
                     lambda w: w['samples'].append(copy.deepcopy(w['samples'][0])),
                     lambda w: w['samples'][0].update(maps_text=''),
                     lambda w: w['samples'].pop()]
        for mutate in mutations:
            witness = copy.deepcopy(self.witness); mutate(witness)
            with self.subTest(mutation=mutate), self.assertRaises((ValueError, KeyError)):
                validate_runtime_custody(witness, self.config)

    def test_model_inode_is_checked(self):
        model = Path(self.config['model_path'])
        replacement = model.with_name('replacement'); replacement.write_bytes(model.read_bytes()); replacement.replace(model)
        with self.assertRaises(ValueError): validate_runtime_custody(self.witness, self.config)

if __name__ == '__main__': unittest.main()
