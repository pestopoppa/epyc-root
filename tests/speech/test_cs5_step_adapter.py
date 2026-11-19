"""Regression controls for the empty-cache audio bypass and scoped hook cleanup."""
import importlib.util
import inspect
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('adapter', Path(__file__).resolve().parents[2] / 'scripts/speech/cs5_step_adapter.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


class Encoder:
    def __init__(self):
        self.hooks = []

    def register_forward_pre_hook(self, hook):
        self.hooks.append(hook)
        owner = self
        class Handle:
            def remove(self):
                owner.hooks.remove(hook)
        return Handle()

    def run(self):
        for hook in self.hooks:
            hook(self, ())


class LLM:
    def __init__(self):
        self.encoder = Encoder()

    def prepare_inputs_for_generation(self, *args, **kwargs):
        return 'original'


class Model:
    def __init__(self, audio=True, fail=False):
        self.llm = LLM()
        self.audio, self.fail = audio, fail

    def __call__(self, messages, **generation):
        self.messages, self.generation = messages, generation
        ids, wavs, lengths = object(), object(), object()
        for cache in (object(), object()):
            result = self.llm.prepare_inputs_for_generation(ids, wavs=wavs,
                wav_lens=lengths, past_key_values=cache, use_cache=True)
            assert result['input_ids'] is ids
            assert result['wavs'] is wavs
            assert result['wav_lens'] is lengths
            assert 'past_key_values' not in result
            if self.audio:
                self.llm.encoder.run()
        if self.fail:
            raise RuntimeError('generation failed')
        return [1, 2], '<英语>Hello <tool_call>x', None


class AdapterTests(unittest.TestCase):
    def test_signature_accepts_transformers_audio_kwargs_validation(self):
        params = inspect.signature(a.prepare_audio_inputs).parameters
        self.assertTrue({'input_ids', 'attention_mask', 'wavs', 'wav_lens', 'kwargs'} <= params.keys())

    def test_empty_and_populated_cache_keep_full_audio_each_step(self):
        m = Model()
        messages = [{'role': 'human', 'content': [{'type': 'audio', 'audio': 'clip.wav'}]}]
        result = a.run_reference(m, messages, expects_audio=True, max_new_tokens=12)
        self.assertIs(m.messages, messages)
        self.assertIs(m.generation['use_cache'], False)
        self.assertEqual(result['encoder_calls'], 2)
        self.assertTrue(result['audio_path_ok'])
        self.assertEqual(result['tokens'], [1, 2])
        self.assertEqual(result['raw_text'], '<英语>Hello <tool_call>x')
        self.assertEqual(result['text'], 'Hello <tool_call>x')
        self.assertNotIn('prepare_inputs_for_generation', vars(m.llm))
        self.assertEqual(m.llm.prepare_inputs_for_generation(), 'original')
        self.assertEqual(m.llm.encoder.hooks, [])

    def test_zero_encoder_calls_cannot_report_audio_success(self):
        result = a.run_reference(Model(audio=False), [], expects_audio=True)
        self.assertFalse(result['audio_path_ok'])
        self.assertEqual(result['error'], 'audio_path_never_ran')
        self.assertEqual(result['raw_text'], '<英语>Hello <tool_call>x')

    def test_text_only_does_not_require_encoder(self):
        self.assertTrue(a.run_reference(Model(audio=False), [], expects_audio=False)['audio_path_ok'])

    def test_cleanup_restores_instance_override_after_error(self):
        m = Model(fail=True)
        original = lambda **kw: None
        m.llm.prepare_inputs_for_generation = original
        with self.assertRaisesRegex(RuntimeError, 'generation failed'):
            a.run_reference(m, [], expects_audio=True)
        self.assertIs(m.llm.prepare_inputs_for_generation, original)
        self.assertEqual(m.llm.encoder.hooks, [])
        self.assertEqual(LLM().prepare_inputs_for_generation(), 'original')

    def test_reject_cache_request_before_mutating_model(self):
        m = Model()
        with self.assertRaises(ValueError):
            a.run_reference(m, [], expects_audio=True, use_cache=True)
        self.assertEqual(m.llm.encoder.hooks, [])
        self.assertNotIn('prepare_inputs_for_generation', vars(m.llm))

    def test_prefix_only_no_control_or_body_removal(self):
        for text in ('Hello <英语>', '<tool_call>x', '<|BOT|>human', ' <英语>Hello'):
            self.assertEqual(a.clean_language_prefix(text), text)
        self.assertEqual(a.clean_language_prefix('<中文>你好'), '你好')
        with self.assertRaises(TypeError):
            a.clean_language_prefix(None)

    def test_explicit_boolean_audio_expectation(self):
        with self.assertRaises(TypeError):
            a.run_reference(Model(), [], expects_audio='yes')


if __name__ == '__main__':
    unittest.main()
