import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('complete', Path(__file__).with_name('complete.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class CompletionTests(unittest.TestCase):
    def test_required_and_tampered_artifacts_refuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / 'runs' / 'build-test'
            files = {}
            for name in (*mod.REQUIRED, 'build/bin/libggml.so'):
                path = run / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(name.encode())
                files[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
            record = dict(schema='epyc.inf75.quantizer_build.v1', status='built', source_commit=mod.COMMIT,
                          linkage_rc=0, run_dir=str(run), files=files)
            self.assertTrue(mod.valid(record, root))
            (run / 'build/bin/llama-quantize').write_bytes(b'tampered')
            self.assertFalse(mod.valid(record, root))
            del files[str(run / 'build/bin/llama-quantize')]
            self.assertFalse(mod.valid(record, root))

    def test_fabricated_result_refuses(self):
        self.assertFalse(mod.valid(dict(schema='epyc.inf75.quantizer_build.v1', status='built',
                                        source_commit=mod.COMMIT, linkage_rc=0, files={'x': 'x'})))

if __name__ == '__main__':
    unittest.main()
