import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from build_binding import bind_receipt, BindingError, SOURCE


class TestBinding(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.run=Path(self.tmp.name)
        self.paths=['build/bin/llama-server','build/bin/libllama-server-impl.so','build/bin/libllama-common.so','build/bin/libggml-hip.so',
                    'build/bin/libllama.so','receipt/source.patch','receipt/linkage.log','build/CMakeCache.txt']
        self.files={}
        for rel in self.paths:
            p=self.run / rel; p.parent.mkdir(parents=True,exist_ok=True)
            if rel == 'receipt/linkage.log':
                p.write_text(f'  OK   libllama-common.so.0 -> {self.run / "build/bin/libllama-common.so"}\n')
            else:
                p.write_bytes(b'G8_COMPARE_BEGIN' if rel.endswith('libllama-common.so') else b'test')
            self.files[str(p.resolve())]=hashlib.sha256(p.read_bytes()).hexdigest()
        self.digest=self.files[str((self.run/'receipt/source.patch').resolve())]
        self.patcher=patch('build_binding.PATCH',self.digest); self.patcher.start()
        self.r={'schema':'epyc.g8.build.v1','mode':'build','source_commit':SOURCE,'patch_sha256':self.digest,
                'run':str(self.run),'files':self.files}
    def tearDown(self): self.patcher.stop(); self.tmp.cleanup()
    def test_valid(self): self.assertEqual(bind_receipt(self.r)['status'],'BUILD_BOUND')
    def test_mutation(self):
        (self.run/'build/bin/libggml-hip.so').write_bytes(b'mutated')
        with self.assertRaises(BindingError): bind_receipt(self.r)
    def test_smoke_is_not_build(self):
        self.r['mode']='smoke'
        with self.assertRaises(BindingError): bind_receipt(self.r)
    def test_missing_marker(self):
        p=self.run/'build/bin/libllama-common.so'; p.write_bytes(b'other')
        self.files[str(p.resolve())]=hashlib.sha256(p.read_bytes()).hexdigest()
        with self.assertRaises(BindingError): bind_receipt(self.r)
    def test_bad_linkage(self):
        p=self.run/'receipt/linkage.log'; p.write_text('not found')
        self.files[str(p.resolve())]=hashlib.sha256(p.read_bytes()).hexdigest()
        with self.assertRaises(BindingError): bind_receipt(self.r)
    def test_linkage_wrong_common(self):
        other=self.run/'other-common.so'; other.write_bytes(b'G8_COMPARE_BEGIN')
        p=self.run/'receipt/linkage.log'; p.write_text(f'  OK   libllama-common.so.0 -> {other}\n')
        self.files[str(p.resolve())]=hashlib.sha256(p.read_bytes()).hexdigest()
        with self.assertRaises(BindingError): bind_receipt(self.r)
    def test_absent_artifact(self):
        (self.run/'build/bin/libllama.so').unlink()
        with self.assertRaises(BindingError): bind_receipt(self.r)

if __name__ == '__main__': unittest.main()
