"""The full receipt refuses a changed verifier or an unattested ggml library."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('pinned_complete', HERE / 'complete.py')
import sys
sys.path.insert(0, str(HERE))
complete = importlib.util.module_from_spec(spec)
spec.loader.exec_module(complete)
from custody import create_manifest

class TestFullReceipt(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root/'v3').mkdir()
        self.helper = self.root/'v3/verify_ggml_linkage.sh'
        shutil.copyfile(HERE/'verify_ggml_linkage.sh', self.helper)
        run = self.root/'runs/build-fixture'
        bin_dir = run/'build/bin'
        bin_dir.mkdir(parents=True)
        libs = ('libllama.so','libllama-common.so','libllama-server-impl.so',
                'libggml-hip.so','libggml.so','libggml-base.so','libggml-cpu.so')
        files = [run/'configure.log', run/'build.log', run/'linkage.log',
                 run/'build/CMakeCache.txt', bin_dir/'llama-server',
                 *(bin_dir/n for n in libs)]
        for i, p in enumerate(files):
            p.write_text(f'fixture {i}\n')
        digests = {str(p): complete.digest_file(p) for p in files}
        self.receipt = {'schema':'epyc.kpf174d.build.v1', 'status':'built',
            'source_commit':'6ec877068936588b6d63dbba5842bbd540b92031',
            'parent_source':'84d0a31603d495377dee24e1159bbbf02f1e2f21',
            'linkage_pass':True, 'knobs':['LLAMA_KPF_LAYOUT_TRACE','LLAMA_KPF_ITEM4_TRACE','--slot-fork-min-tokens'],
            'linkage_verifier_sha256':complete.digest_file(self.helper),
            'binary_sha256':digests[str(bin_dir/'llama-server')],
            'libraries':{n:digests[str(bin_dir/n)] for n in libs}, 'compilers':{},
            'run_dir':str(run), 'integrity':{'fixture':True}, 'files':digests}
        (self.root/'RESULT.json').write_text(json.dumps(self.receipt))
        (self.root/'CUSTODY.json').write_text(json.dumps(create_manifest(bin_dir, self.root/'RESULT.json')))
        self.orig_integrity = complete.verify_integrity
        self.orig_compilers = complete.verify_compilers
        complete.verify_integrity = lambda **kw: {'fixture':True}
        complete.verify_compilers = lambda _value: None
        self.addCleanup(setattr, complete, 'verify_integrity', self.orig_integrity)
        self.addCleanup(setattr, complete, 'verify_compilers', self.orig_compilers)
        self.lib = bin_dir/'libggml-base.so'

    def test_accepted_and_changed_verifier_refused(self):
        complete.validate_receipt(self.receipt, self.root)
        self.helper.write_text('tampered')
        with self.assertRaises(AssertionError):
            complete.validate_receipt(self.receipt, self.root)

    def test_changed_library_refused(self):
        self.lib.write_text('tampered')
        with self.assertRaises((AssertionError, ValueError)):
            complete.validate_receipt(self.receipt, self.root)

if __name__ == '__main__': unittest.main()
