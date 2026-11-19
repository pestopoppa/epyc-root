import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/speech'))
import cs5_step_reference as r
from test_cs5_step_adapter import Model


class ReferenceTests(unittest.TestCase):
    def harness(self):
        return dict(model='synthetic-Step', quant='bf16', device='cpu',
                    host_lane='synthetic-test', llm_judged=False)

    def turn(self, model=None, vocoder=None):
        model = model or Model()
        native_call = model.__class__.__call__
        class AudioModel(Model):
            def __call__(self, messages, **kw):
                tokens, text, _ = native_call(self, messages, **kw)
                return tokens, text, [3, 4]
        wrapped = AudioModel(audio=model.audio)
        self.events = []
        def sync():
            self.events.append('sync')
        def sample():
            self.events.append('sample')
            return dict(present=False, sampled_during_row=True)
        times = iter([10., 10.25])
        return r.run_turn(wrapped, vocoder or (lambda *a, **kw: b'RIFFfake'),
            [{'role': 'human', 'content': 'native prompt'}],
            prompt_wav='prepared.wav', expects_audio=True, synchronize=sync,
            sample_co_tenant=sample, harness=self.harness(), clock=lambda: next(times))

    def test_source_pin_refuses_changed_code_before_execution(self):
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            r.placed_code(b'raise RuntimeError()', 'fake.py', '0' * 64)

    def test_placement_executes_on_explicit_device_without_global_patch(self):
        source = b'''class Decoder:
    def run(self, tensor, torch):
        x = tensor.cuda()
        y = torch.tensor([1], device='cuda')
        return x, y, torch.amp.autocast('cuda')
'''
        calls = []
        class Tensor:
            def to(self, device):
                calls.append(device)
                return 'placed'
            def cuda(self):
                raise AssertionError('global cuda called')
        class Device:
            type = 'cpu'
        device = Device()
        class Torch:
            class amp:
                @staticmethod
                def autocast(value):
                    return value
            @staticmethod
            def tensor(value, device):
                calls.append(device)
                return 'new'
        namespace = dict(_cs5_device=device)
        exec(r.placed_code(source, 'fake.py', hashlib.sha256(source).hexdigest()), namespace)
        self.assertEqual(namespace['Decoder']().run(Tensor(), Torch), ('placed', 'new', 'cpu'))
        self.assertEqual(calls, [device, device])

    def test_unexpected_cuda_signature_refused(self):
        source = b'x.cuda(1)'
        with self.assertRaisesRegex(ValueError, 'unexpected upstream'):
            r.placed_code(source, 'fake.py', hashlib.sha256(source).hexdigest())

    def test_success_roundtrips_existing_cs3_writer_and_rejects_tamper(self):
        result = self.turn()
        self.assertEqual(self.events, ['sync', 'sample', 'sync'])
        self.assertEqual(result['completion_ms'], 250.)
        self.assertEqual(result['audio_tokens'], [3, 4])
        self.assertEqual(result['text'], 'Hello <tool_call>x')
        self.assertEqual(result['harness']['runtime']['kind'], 'reference')
        with tempfile.TemporaryDirectory() as tmp:
            path, sidecar = r.write_turn(Path(tmp) / 'turn', result, run_id='synthetic', subject='fake')
            from adapters.conversation_stack_measurement import native_rows, project
            rows = native_rows(sidecar)
            self.assertEqual(len(rows), 1)
            claim = project(rows[0])
            self.assertEqual(claim.metric_direction, 'lower_better')
            self.assertEqual(claim.protocol_id, '')
            self.assertFalse(claim.extra['serving_claim'])
            native = json.loads(path.read_text())
            self.assertEqual(native['wav_sha256'], hashlib.sha256(b'RIFFfake').hexdigest())
            self.assertEqual(native['raw_text'], '<英语>Hello <tool_call>x')
            path.write_text('{}')
            self.assertFalse(project(native_rows(sidecar)[0]).attestation_present)

    def test_audio_bypass_is_preserved_without_success_sidecar_or_vocoder(self):
        def refuse(*args, **kw):
            self.fail('vocoder ran after audio bypass')
        result = self.turn(Model(audio=False), refuse)
        with tempfile.TemporaryDirectory() as tmp:
            path, sidecar = r.write_turn(Path(tmp) / 'failed', result, run_id='bad', subject='fake')
            self.assertIsNone(sidecar)
            self.assertEqual(json.loads(path.read_text())['error'], 'audio_path_never_ran')

    def test_unknown_cotenant_does_not_become_idle(self):
        result = self.turn()
        result['harness']['co_tenant'] = {}
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(Exception, 'co_tenant'):
                r.write_turn(Path(tmp) / 'bad', result, run_id='bad', subject='fake')

    def test_reusing_output_cannot_overwrite_attestation(self):
        result = self.turn()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'turn'
            path, _ = r.write_turn(out, result, run_id='one', subject='fake')
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                r.write_turn(out, result, run_id='two', subject='fake')
            self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
