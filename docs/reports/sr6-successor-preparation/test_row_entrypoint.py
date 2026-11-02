import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from row_entrypoint import _argv, _below, _model, run
from native_worker import ARMS, canonical, digest


class EntrypointValidationTest(unittest.TestCase):
    def test_pinned_argv_rejects_wrong_or_duplicate_speculation(self):
        argv = ['/bin/llama-server', '-m', '/model', '--host', '127.0.0.1',
                '--port', '1234', '-ngl', '0', '--spec-type', 'draft-mtp',
                '--spec-draft-n-max', '3']
        kw = dict(binary='/bin/llama-server', model='/model', port=1234, spec='draft-mtp', width=3)
        _argv(argv, **kw)
        _argv(['/usr/bin/numactl', '--interleave=all'] + argv, **kw)
        with self.assertRaises(ValueError):
            _argv(argv + ['--spec-type', 'none'], **kw)
        with self.assertRaises(ValueError):
            _argv(argv, **dict(kw, width=4))

    def test_model_stat_change_refuses_and_output_must_be_nested(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); output = root / 'output'; output.mkdir()
            model = root / 'model'; model.write_bytes(b'123')
            st = model.stat()
            seal = dict(dev=st.st_dev, ino=st.st_ino, size=st.st_size,
                        mtime_ns=st.st_mtime_ns, ctime_ns=st.st_ctime_ns)
            _model(str(model), seal)
            self.assertEqual(_below(root, output), output)
            model.write_bytes(b'4567')
            with self.assertRaises(ValueError): _model(str(model), seal)
            with self.assertRaises(ValueError): _below(output, root)

    def test_draft_preflight_fails_before_any_work(self):
        with self.assertRaisesRegex(ValueError, 'preflight incomplete'):
            run({'schema':'sr6.row-config.v1', 'preflight_status':'DRAFT'}, {})

    def test_interrupted_window_writes_partial_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); output = root/'output'; output.mkdir()
            arms = {arm: ['unused'] for arm in ARMS}
            packet = {'seals':{'launch':digest(canonical(arms)), 'model':'a'*64}}
            receipt = {'schema':'sr6.model-preflight.v1'}
            config = {'schema':'sr6.row-config.v1', 'preflight_status':'VERIFIED',
                'preflight_receipt':'/receipt', 'preflight_receipt_sha256':'x',
                'scratch_root':str(root), 'output':str(output), 'row_id':'row1',
                'packet_path':'/packet', 'packet_file_sha256':'x',
                'packet_sha256':digest(canonical(packet)), 'argv_by_arm':arms,
                'build_root':'/build', 'runtime_manifest_sha256':'x', 'model_path':'/model',
                'model_sha256':'a'*64, 'model_stat':{}, 'smoke_model_path':'/tiny',
                'smoke_model_sha256':'b'*64, 'smoke_model_stat':{}, 'smoke_argv':['unused'],
                'port':1234, 'guard_sha256':'x', 'guard_path':'/guard', 'window':'w1',
                'request_timeout_s':30, 'result_path':str(root/'RESULT.json')}
            for prefix in ('model','smoke_model'):
                for suffix in ('path','sha256'):
                    receipt[prefix+'_'+suffix] = config[prefix+'_'+suffix]
                receipt[prefix+'_stat_before'] = receipt[prefix+'_stat_after'] = {}
            def load(path, sha): return receipt if path == '/receipt' else packet
            with patch('row_entrypoint._load', side_effect=load), \
                 patch('row_entrypoint.build_schedule'), patch('row_entrypoint.verify_runtime_manifest'), \
                 patch('row_entrypoint._model'), patch('row_entrypoint._argv'), \
                 patch('row_entrypoint.FullHostBenchClaim'), \
                 patch('row_entrypoint.KeeperAdmission', return_value=lambda: True), \
                 patch('row_entrypoint.LifecycleAdapters'), \
                 patch('row_entrypoint.capture_window', side_effect=ValueError('stopped')):
                with self.assertRaisesRegex(ValueError, 'stopped'):
                    run(config, {'FILLER_ID':'row1', 'FILLER_STOPFILE':'/stop', 'FILLER_DEADLINE':'9999999999'})
            import json
            result = json.loads((root/'RESULT.json').read_text())
            self.assertEqual((result['state'], result['decision']), ('PARTIAL', 'UNKNOWN'))
