import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

import verify_bound as v
import verify_pair


def digest(data): return hashlib.sha256(data).hexdigest()
def pin(contract): return digest(json.dumps(contract, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode())


class BoundTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.commit = 'a' * 40
        self.selection = {'cells': [1, 2, 5], 'layers': 2, 'row_bytes': 8, 'dtype': 'f16', 'v_transposed': False}
        def write(name, data):
            (self.root / name).write_bytes(data)
            return {'file': name, 'sha256': digest(data)}
        patch, binary = write('patch', b'patch'), write('binary', b'ELF fixture')
        build = {'schema': 'kpf60.fixture-build.v1', 'source_commit': self.commit,
                 'patch_sha256': patch['sha256'], 'binary_sha256': binary['sha256'], 'status': 'built'}
        self.contract = {'schema': 'kpf60.fixture-bound-pair.v1', 'source_commit': self.commit,
                         'selection': self.selection, 'patch': patch, 'binary': binary,
                         'build_receipt': write('build.json', json.dumps(build).encode())}
        for arm in ('baseline', 'observed'):
            blob = write(arm + '.bin', verify_pair.ORACLE.EXPECTED)
            receipt = {'schema': 'kpf60.fixture-capture.v1', 'arm': arm, 'capture_id': arm,
                       'source_commit': self.commit, 'binary_sha256': binary['sha256'],
                       'selection': self.selection, 'blob_sha256': blob['sha256'], 'exit_code': 0}
            self.contract[arm] = {'blob': blob, 'receipt': write(arm + '.json', json.dumps(receipt).encode())}

    def check(self): return v.verify(self.root, self.contract, pin(self.contract))
    def test_matching_content_and_bindings(self): self.assertEqual(self.check()['status'], 'MATCH')
    def test_contract_pin_and_selection_rejected(self):
        with self.assertRaisesRegex(ValueError, 'contract digest'): v.verify(self.root, self.contract, '0' * 64)
        self.contract['selection']['cells'] = [1, 2, 6]
        with self.assertRaisesRegex(ValueError, 'selection'): self.check()
    def test_build_or_capture_tampering_rejected(self):
        (self.root / 'binary').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'digest mismatch'): self.check()
    def test_wrong_source_or_binary_in_receipt_rejected(self):
        p = self.root / 'observed.json'; receipt = json.loads(p.read_text()); receipt['source_commit'] = 'b' * 40
        p.write_text(json.dumps(receipt)); self.contract['observed']['receipt']['sha256'] = digest(p.read_bytes())
        with self.assertRaisesRegex(ValueError, 'capture receipt'): self.check()
    def test_invalid_exit_and_duplicate_identity_rejected(self):
        p = self.root / 'observed.json'; original = json.loads(p.read_text())
        for update in ({'exit_code': 1}, {'exit_code': False}, {'capture_id': 'baseline'}):
            receipt = dict(original, **update); p.write_text(json.dumps(receipt)); self.contract['observed']['receipt']['sha256'] = digest(p.read_bytes())
            with self.assertRaises(ValueError): self.check()
    def test_alias_and_symlink_rejected(self):
        p = self.root / 'observed.bin'; p.unlink(); os.link(self.root / 'baseline.bin', p)
        with self.assertRaisesRegex(ValueError, 'alias'): self.check()
        p.unlink(); p.symlink_to(self.root / 'baseline.bin')
        with self.assertRaises(OSError): self.check()
    def test_model_weight_filename_refused(self):
        self.contract['binary']['file'] = 'model.gguf'
        with self.assertRaisesRegex(ValueError, 'model weights'): self.check()


if __name__ == '__main__': unittest.main()
