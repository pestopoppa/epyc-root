import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
import bound_custody as bc


class BoundCustody(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.packet = Path(self.tmp.name)
        self.bin = self.packet / 'bin'
        self.bin.mkdir()
        self.paths = []
        for name in (*bc.ggml.REQUIRED, 'llama-server'):
            p = self.bin / name
            p.write_text(name)
            self.paths.append(p)
        helper = self.packet / 'verify_ggml_linkage.sh'
        helper.write_text('fixture verifier')
        self.receipt = dict(schema='epyc.kpf174d.build.v1', status='built',
                            source_commit=bc.ggml.SOURCE, parent_source=bc.ggml.PARENT,
                            linkage_pass=True, binary_sha256=bc.ggml.digest(self.bin / 'llama-server'),
                            linkage_verifier_sha256=bc.ggml.digest(helper),
                            files={str(p): bc.ggml.digest(p) for p in self.paths})
        self.save_receipt()
        manifest = bc.ggml.create_manifest(self.bin, self.packet / 'BUILD-RECEIPT.json')
        (self.packet / 'GGML-CUSTODY.json').write_text(json.dumps(manifest))
        self.proof = copy.deepcopy(self.receipt)
        self.proof.update(build_receipt_sha256=bc.ggml.digest(self.packet / 'BUILD-RECEIPT.json'),
                          ggml_custody_sha256=bc.ggml.digest(self.packet / 'GGML-CUSTODY.json'),
                          libraries={name: entry['sha256'] for name, entry in manifest['libraries'].items()})

    def save_receipt(self):
        (self.packet / 'BUILD-RECEIPT.json').write_text(json.dumps(self.receipt))

    def validate(self):
        return bc.validate_custody(self.packet, self.bin, self.proof)

    def test_bound_receipt_and_helper(self):
        self.assertEqual(self.validate()['build_receipt_sha256'], self.proof['build_receipt_sha256'])

    def test_missing_each_ggml_attestation(self):
        for name in bc.ggml.REQUIRED:
            with self.subTest(name=name):
                original = self.receipt['files'].pop(str(self.bin / name))
                self.save_receipt()
                with self.assertRaises(ValueError): self.validate()
                self.receipt['files'][str(self.bin / name)] = original

    def test_changed_manifest_receipt_helper_and_binary(self):
        for name in ('GGML-CUSTODY.json', 'BUILD-RECEIPT.json', 'verify_ggml_linkage.sh', 'bin/llama-server'):
            with self.subTest(name=name):
                p = self.packet / name
                original = p.read_bytes()
                p.write_bytes(original + b' ')
                with self.assertRaises(ValueError): self.validate()
                p.write_bytes(original)

    def test_missing_proof_pins_and_wrong_source(self):
        for key in ('build_receipt_sha256', 'ggml_custody_sha256', 'linkage_verifier_sha256', 'source_commit'):
            with self.subTest(key=key):
                value = self.proof.pop(key)
                with self.assertRaises(ValueError): self.validate()
                self.proof[key] = value

    def test_mapping_requires_all_attested_libraries(self):
        lines = []
        for p in self.paths[:-1]:
            st = p.stat()
            lines.append(f'1000-2000 r-xp 0 {os.major(st.st_dev):x}:{os.minor(st.st_dev):x} {st.st_ino} {p}')
        self.assertEqual(bc.verify_mappings(self.packet, self.bin, '\n'.join(lines))['status'], 'PASS')
        with self.assertRaises(ValueError): bc.verify_mappings(self.packet, self.bin, lines[-1])


if __name__ == '__main__': unittest.main()
