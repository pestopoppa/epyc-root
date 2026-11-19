import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/speech'))
import cs5_qwen_reference as q


class Tensor:
    shape = (1, 3)
    def numel(self):
        return 4
    def __getitem__(self, key):
        return self
    def tolist(self):
        return [[7, 8]]


class Inputs(dict):
    def to(self, placement):
        return self


class Processor:
    def apply_chat_template(self, messages, **kwargs):
        return 'native prompt'
    def __call__(self, **kwargs):
        assert kwargs['text'] == 'native prompt'
        return Inputs(input_ids=Tensor(), input_features=Tensor())
    def batch_decode(self, ids, **kwargs):
        return ['<native>hello' if not kwargs['skip_special_tokens'] else 'hello']


class Model:
    device = 'cpu'
    dtype = 'bf16'
    def generate(self, **kwargs):
        assert kwargs['return_audio'] is True
        assert kwargs['thinker_return_dict_in_generate'] is True
        self.kwargs = kwargs
        return type('Tokens', (), {'sequences': Tensor()})(), object()


class QwenTests(unittest.TestCase):
    def run_turn(self, tmp, **changes):
        path = Path(tmp) / 'input.wav'
        path.write_bytes(b'prepared')
        args = dict(process_mm_info=lambda *a, **kw: ([object()], None, None),
            expects_audio=True, synchronize=lambda: self.events.append('sync'),
            sample_co_tenant=lambda: self.sample(),
            harness=dict(model='synthetic-Qwen', quant='bf16', device='cpu',
                         host_lane='synthetic', llm_judged=False),
            environment={'synthetic': True}, clock=iter([2., 2.5]).__next__)
        args.update(changes)
        with patch.object(q, '_wav_bytes', return_value=b'RIFFsynthetic'):
            return q.run_turn(Model(), Processor(),
                [{'role': 'user', 'content': [{'type': 'audio', 'audio': str(path)}]}], **args)
    def setUp(self):
        self.events = []
    def sample(self):
        self.events.append('sample')
        return dict(present=False, sampled_during_row=True)
    def test_native_result_cs3_and_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_turn(tmp)
            self.assertEqual(self.events, ['sync', 'sample', 'sync'])
            self.assertEqual(result['completion_ms'], 500)
            self.assertEqual(result['raw_text'], '<native>hello')
            self.assertEqual(result['text'], 'hello')
            self.assertEqual(result['tokens'], [[7, 8]])
            path, sidecar = q.write_turn(Path(tmp)/'out', result, run_id='fake', subject='fake')
            from adapters.conversation_stack_measurement import native_rows, project
            claim = project(native_rows(sidecar)[0])
            self.assertEqual(claim.metric_direction, 'lower_better')
            self.assertFalse(claim.extra['serving_claim'])
            native = json.loads(path.read_text())
            self.assertEqual(native['upstream_commit'], q.UPSTREAM)
            self.assertEqual(native['wav_sha256'], hashlib.sha256(b'RIFFsynthetic').hexdigest())
            path.write_text('{}')
            self.assertFalse(project(native_rows(sidecar)[0]).attestation_present)
    def test_audio_bypass_refused_before_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(Processor, '__call__', return_value=Inputs(input_ids=Tensor())):
                with self.assertRaisesRegex(ValueError, 'no features'):
                    self.run_turn(tmp)
    def test_missing_generated_audio_has_no_success_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(Model, 'generate', return_value=(type('T', (), {'sequences': Tensor()})(), None)):
                result = self.run_turn(tmp)
            path, sidecar = q.write_turn(Path(tmp)/'failed', result, run_id='fake', subject='fake')
            self.assertIsNone(sidecar)
            self.assertEqual(json.loads(path.read_text())['error'], 'no_generated_audio')
    def test_generation_cannot_disable_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'cannot override'):
                self.run_turn(tmp, generation={'return_audio': False})
    def test_network_audio_and_wrong_modalities_refused(self):
        for item in ({'type': 'audio', 'audio': 'https://invalid/audio.wav'}, {'type': 'video'}):
            with self.assertRaises(ValueError):
                q._check_messages([{'content': [item]}], True)
    def test_environment_drift_refused_before_model_construction(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'README.md').write_bytes(b'fixture')
            env = {'versions': {name: 'pinned' for name in
                   ('torch', 'transformers', 'qwen-omni-utils')}, 'sources': {}}
            with patch.object(q.subprocess, 'check_output', side_effect=[q.UPSTREAM, '']), \
                 patch.object(q, 'PINS', {'README.md': hashlib.sha256(b'fixture').hexdigest()}), \
                 patch.object(q.importlib.metadata, 'version', return_value='changed'):
                with self.assertRaisesRegex(ValueError, 'version mismatch'):
                    q.verify_sources(tmp, env)
            class Distribution:
                def locate_file(self, relative):
                    return Path(tmp, 'README.md')
            relative = 'transformers/models/qwen3_omni_moe/modeling_qwen3_omni_moe.py'
            env['sources'][relative] = '0' * 64
            with patch.object(q.subprocess, 'check_output', side_effect=[q.UPSTREAM, '']), \
                 patch.object(q, 'PINS', {'README.md': hashlib.sha256(b'fixture').hexdigest()}), \
                 patch.object(q.importlib.metadata, 'version', return_value='pinned'), \
                 patch.object(q.importlib.metadata, 'distribution', return_value=Distribution()):
                with self.assertRaisesRegex(ValueError, 'source mismatch'):
                    q.verify_sources(tmp, env)

    def test_checkout_drift_refused_before_package_import(self):
        with patch.object(q.subprocess, 'check_output', return_value='wrong'):
            with self.assertRaisesRegex(ValueError, 'pinned upstream'):
                q.verify_sources('/unused', {})


if __name__ == '__main__':
    unittest.main()
