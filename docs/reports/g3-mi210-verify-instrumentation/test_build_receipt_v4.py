import hashlib
import tempfile
import unittest
from pathlib import Path

from build_receipt_v4 import ReceiptError, SOURCE, bind_v4_receipt


class ReceiptTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.run = self.root / 'runs' / 'build-example'
        paths = {
            'build/bin/llama-server': b'private server',
            'build/bin/libllama-server-impl.so': b'G3_TARGET_BEGIN_V3 G3_TARGET_END_V3 time_ns=%lld',
            'build/bin/libggml-hip.so': b'G3_FATTN_DISPATCH_V3 time_ns=%lld',
            'build/bin/libllama.so': b'g3_fattn_layer_',
            'build/CMakeCache.txt': b'gfx90a',
            'receipt/source.patch': b'instrumentation patch',
            'receipt/source-after.patch': b'instrumentation patch',
            'receipt/linkage.log': b'local ggml linked',
        }
        for rel, data in paths.items():
            p = self.run / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        self.patch = hashlib.sha256(paths['receipt/source.patch']).hexdigest()
        files = {str((self.run / rel).resolve()): hashlib.sha256(data).hexdigest()
                 for rel, data in paths.items() if rel != 'receipt/source-after.patch'}
        self.record = {'schema': 'epyc.g3.build.v1', 'mode': 'build', 'source_commit': SOURCE,
                       'patch_sha256': self.patch, 'run': str(self.run), 'files': files}

    def tearDown(self):
        self.tmp.cleanup()

    def bind(self):
        return bind_v4_receipt(self.record, self.root, expected_patch=self.patch)

    def test_valid_complete_receipt(self):
        self.assertEqual(self.bind()['status'], 'BUILD_BOUND')

    def test_smoke_is_not_a_build(self):
        self.record['mode'] = 'smoke'
        with self.assertRaises(ReceiptError): self.bind()

    def test_bad_artifact_digest(self):
        (self.run / 'build/bin/llama-server').write_bytes(b'changed')
        with self.assertRaises(ReceiptError): self.bind()

    def test_changed_after_source(self):
        (self.run / 'receipt/source-after.patch').write_bytes(b'changed')
        with self.assertRaises(ReceiptError): self.bind()

    def test_missing_marker_even_when_hash_is_updated(self):
        p = self.run / 'build/bin/libggml-hip.so'
        p.write_bytes(b'no instrumentation')
        self.record['files'][str(p.resolve())] = hashlib.sha256(p.read_bytes()).hexdigest()
        with self.assertRaises(ReceiptError): self.bind()

    def test_failed_linkage_even_when_hash_is_updated(self):
        p = self.run / 'receipt/linkage.log'
        p.write_text('libggml.so not found')
        self.record['files'][str(p.resolve())] = hashlib.sha256(p.read_bytes()).hexdigest()
        with self.assertRaises(ReceiptError): self.bind()

    def test_untrusted_root(self):
        (self.root / 'other').mkdir()
        with self.assertRaises(ReceiptError):
            bind_v4_receipt(self.record, self.root / 'other', expected_patch=self.patch)


if __name__ == '__main__': unittest.main()
