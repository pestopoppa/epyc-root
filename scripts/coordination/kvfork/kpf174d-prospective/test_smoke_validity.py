import unittest
import control
from test_control import Tests

class SmokeValidity(unittest.TestCase):
    def pair(self):
        runs = Tests.numeric_runs()
        pair = [runs[0], runs[2]]
        for run in pair:
            run['during_vram_samples'] = [[1.0, 4096], [2.0, 4096]]
        return pair

    def test_complete_pair_can_be_smoke_only(self):
        self.assertEqual(control.cell_verdict(self.pair(), True)['verdict'], 'SMOKE_ONLY')

    def test_missing_tokens_or_top2_is_invalid(self):
        pair = self.pair()
        pair[0]['response']['tokens'].pop()
        self.assertEqual(control.cell_verdict(pair, True)['verdict'], 'INVALID')
        pair = self.pair()
        pair[1]['response']['probs'][0]['top_logprobs'].pop()
        self.assertEqual(control.cell_verdict(pair, True)['verdict'], 'INVALID')

    def test_less_than_two_during_samples_invalid(self):
        pair = self.pair()
        pair[1]['during_vram_samples'].pop()
        self.assertEqual(control.cell_verdict(pair, True)['verdict'], 'INVALID')
