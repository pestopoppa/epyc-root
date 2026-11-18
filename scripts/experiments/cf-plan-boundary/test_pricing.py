import copy
import importlib.util
from pathlib import Path
import unittest
import tempfile

spec = importlib.util.spec_from_file_location('pricing', Path(__file__).with_name('runner.py'))
pricing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pricing)


class PricingTests(unittest.TestCase):
    def reply(self):
        return {'timings': {'cache_n': 100, 'prompt_n': 4, 'prompt_ms': 3, 'predicted_ms': 7},
                'tokens_evaluated': 104, 'tokens_predicted': 1, 'id_slot': 0, 'stop': True}

    def test_amortization_counts_rewrite_request(self):
        result = pricing.pricing([10, 10, 10, 10], [40, 5, 5, 5])
        self.assertEqual(result['rewrite_extra_ms'], 30)
        self.assertEqual(result['point_break_even_requests'], 7)
        self.assertEqual(result['measured_horizon_delta_ms'], 15)

    def test_zero_or_negative_savings_has_no_finite_extrapolation(self):
        for costs in ([40, 10, 10], [40, 12, 12]):
            self.assertIsNone(pricing.pricing([10, 10, 10], costs)['point_break_even_requests'])

    def test_asymmetric_horizons_refused(self):
        with self.assertRaises(ValueError):
            pricing.pricing([1, 2, 3], [4, 5])

    def test_fixed_ascii_generation_avoids_partial_byte_outputs(self):
        payload = pricing.payload_for([100, 101], True)
        self.assertEqual(payload['grammar'], 'root ::= "x"')
        self.assertEqual(payload['n_predict'], 1)
        self.assertTrue(payload['ignore_eos'])
        self.assertTrue(payload['cache_prompt'])
        self.assertEqual(payload['id_slot'], 0)

    def test_requalification_preserves_prior_windows_but_official_retry_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            (out / 'window-prior').mkdir()
            pricing.guard_attempt(out, True)
            self.assertTrue((out / 'window-prior').is_dir())
            with self.assertRaises(ValueError):
                pricing.guard_attempt(out, False)

    def test_warm_native_accounting(self):
        self.assertEqual(pricing.evaluate(self.reply(), 104, True)['cached_tokens'], 100)

    def test_cache_misses_cannot_be_warm_witnesses(self):
        reply = self.reply()
        reply['timings'].update(cache_n=0, prompt_n=104)
        with self.assertRaises(ValueError):
            pricing.evaluate(reply, 104, True)
        self.assertEqual(pricing.evaluate(reply, 104, False)['processed_tokens'], 104)

    def test_rewrite_must_really_invalidate_prefix(self):
        with self.assertRaises(ValueError):
            pricing.evaluate(self.reply(), 104, False)

    def test_native_integrity_controls(self):
        for field, value in [('id_slot', 1), ('tokens_predicted', 0), ('tokens_evaluated', 105), ('stop', False)]:
            reply = self.reply()
            reply[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                pricing.evaluate(reply, 104, True)
        for field, value in [('cache_n', 99), ('prompt_ms', float('nan')), ('predicted_ms', -1)]:
            reply = copy.deepcopy(self.reply())
            reply['timings'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                pricing.evaluate(reply, 104, True)

    def test_fixtures_preserve_warm_prefix_and_break_rewrite_prefix(self):
        raw = pricing.tokens(1024, 0)
        compact = pricing.tokens(256, 1)
        a = raw + pricing.tokens(32, 2)
        b = raw + pricing.tokens(64, 2)
        self.assertEqual(a, b[:len(a)])
        self.assertNotEqual(raw[0], compact[0])


if __name__ == '__main__':
    unittest.main()
