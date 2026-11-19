import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/speech'))
import cs5_reference_job as j


class Backend:
    def __init__(self, fail=False, native_error=None):
        self.calls = []
        self.fail, self.native_error = fail, native_error
    def load_models(self, *args, **kwargs):
        self.calls.append(('load', args, kwargs))
        if self.fail:
            raise RuntimeError('synthetic load failure')
        if 'environment' in kwargs:
            return 'model', 'processor', 'process', 'sync'
        return 'model', 'vocoder', 'sync'
    def run_turn(self, *args, **kwargs):
        self.calls.append(('turn', args, kwargs))
        kwargs['sample_co_tenant']()
        return dict(error=self.native_error, completion_ms=12)
    def write_turn(self, out, result, **kwargs):
        out.mkdir()
        native = out / 'native.json'
        native.write_text(json.dumps(result))
        return native, out/'sidecar.jsonl' if result['error'] is None else None


class JobTests(unittest.TestCase):
    def config(self, tmp, candidate='step'):
        root = Path(tmp)
        model = root/'model'
        model.mkdir(exist_ok=True)
        wav, weight = root/'input.wav', model/'weights.safetensors'
        wav.write_bytes(b'prepared audio')
        weight.write_bytes(b'synthetic weight identity')
        files = []
        for path in (wav, weight):
            stat = path.stat()
            files.append(dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                stat=dict(size=stat.st_size, mtime_ns=stat.st_mtime_ns,
                          device=stat.st_dev, inode=stat.st_ino)))
        return dict(schema='epyc.cs5.reference_job.v1', candidate=candidate,
            run_id='synthetic', result_dir=str(root/'out'), prepared_files=files,
            expects_audio=True, input_paths=[str(wav)], prompt_wav=str(wav),
            model_dir=str(model), source_dir='/pinned/upstream', device='cpu',
            co_tenant_command=['synthetic-sampler'], generation={'max_new_tokens': 4},
            harness={'synthetic': True}, environment={'versions': dict.fromkeys(
                ['torch', 'transformers', 'qwen-omni-utils'], 'pinned')},
            messages=[{'role':'user','content':[{'type':'audio','audio':str(wav)}]}],
            subject='synthetic')
    def setUp(self):
        self.patcher = patch.object(j.importlib.metadata, 'version', return_value='pinned')
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
    def execute(self, config, backend):
        return j.execute(config, backend=backend, sampler=lambda argv: dict(
            present=False, sampled_during_row=True))
    def test_dispatch_both_candidates_and_preserve_prepared_identity(self):
        for candidate in ('step', 'qwen'):
            with self.subTest(candidate=candidate), tempfile.TemporaryDirectory() as tmp:
                config = self.config(tmp, candidate)
                backend = Backend()
                summary = self.execute(config, backend)
                self.assertEqual(summary['verdict'], 'pass')
                self.assertEqual(summary['completion_ms'], 12)
                args, kwargs = backend.calls[1][1:]
                self.assertEqual(args[0], 'model')
                self.assertEqual(kwargs['generation'], config['generation'])
                self.assertEqual('process_mm_info' in kwargs, candidate == 'qwen')
                native = json.loads(Path(summary['native_path']).read_text())
                self.assertEqual(native['prepared_job'], config)
    def test_drift_refuses_before_loading_and_rerun_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self.config(tmp)
            Path(config['input_paths'][0]).write_bytes(b'changed')
            backend = Backend()
            summary = self.execute(config, backend)
            self.assertEqual(summary['verdict'], 'inconclusive')
            self.assertEqual(backend.calls, [])
            before = Path(config['result_dir'], 'summary.json').read_bytes()
            with self.assertRaises(FileExistsError):
                self.execute(config, backend)
            self.assertEqual(Path(config['result_dir'], 'summary.json').read_bytes(), before)
    def test_failed_load_and_native_failure_retained(self):
        for backend, verdict in ((Backend(fail=True), 'inconclusive'),
                                  (Backend(native_error='audio_path_never_ran'), 'fail')):
            with tempfile.TemporaryDirectory() as tmp:
                config = self.config(tmp)
                summary = self.execute(config, backend)
                self.assertEqual(summary['verdict'], verdict)
                self.assertTrue(Path(config['result_dir'], 'request.json').is_file())
                self.assertIsNotNone(summary['error'])
    def test_message_receipt_mismatch_and_duplicates_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self.config(tmp)
            bad = copy.deepcopy(config)
            bad['messages'][0]['content'][0]['audio'] = 'https://invalid/input.wav'
            with self.assertRaisesRegex(ValueError, 'message audio differs'):
                j.admit(bad)
            bad = copy.deepcopy(config)
            bad['prepared_files'].append(bad['prepared_files'][0])
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                j.admit(bad)
    def test_config_digest_and_sampler_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'config.json'
            path.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'configuration digest'):
                j.read_config(path, '0'*64)
        with patch.object(j.subprocess, 'check_output', return_value='{}'):
            with self.assertRaisesRegex(ValueError, 'observed co-tenant'):
                j.sample_tenant(['unused'])
    def test_unreceipted_model_shard_refuses_loading_without_hashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self.config(tmp)
            Path(config['model_dir'], 'extra.safetensors').write_bytes(b'extra shard')
            backend = Backend()
            with patch.object(j.hashlib, 'sha256', side_effect=AssertionError('grant hash')):
                result = self.execute(config, backend)
            self.assertEqual(result['verdict'], 'inconclusive')
            self.assertIn('complete model file receipts', result['error'])
            self.assertEqual(backend.calls, [])

    def test_environment_drift_refuses_loading(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self.config(tmp)
            with patch.object(j.importlib.metadata, 'version', return_value='changed'):
                backend = Backend()
                result = self.execute(config, backend)
                self.assertEqual(result['verdict'], 'inconclusive')
                self.assertEqual(backend.calls, [])


if __name__ == '__main__':
    unittest.main()
