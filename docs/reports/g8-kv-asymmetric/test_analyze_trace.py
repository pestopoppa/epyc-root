import copy
import unittest
from analyze_trace import analyze_pair

TRACE = '''G8_COMPARE_BEGIN rows=2
G8_COMPARE_ROW pos=0 batch=0 draft=1 target=1 match=1
G8_COMPARE_ROW pos=1 batch=1 draft=2 target=3 match=0
G8_COMPARE_END rows=2
G8_COMPARE_BEGIN rows=1
G8_COMPARE_ROW pos=0 batch=0 draft=4 target=4 match=1
G8_COMPARE_END rows=1'''


def packet():
    r = {'tokens': [9, 10], 'timings': {'draft_n': 3, 'draft_n_accepted': 2}}
    return {'greedy': True, 'single_slot': True, 'single_drafter': True,
            'control_response': copy.deepcopy(r), 'traced_response': copy.deepcopy(r), 'trace': TRACE,
            'control_request': {'temperature':0, 'cache_prompt':False, 'return_tokens':True, 'stream':False, 'n_predict':128},
            'traced_request': {'temperature':0, 'cache_prompt':False, 'return_tokens':True, 'stream':False, 'n_predict':128}}


class TestTrace(unittest.TestCase):
    def test_valid(self):
        r = analyze_pair(packet())
        self.assertEqual(r['mean_accepted_per_proposing_round'], 1)
        self.assertEqual([p['observed_proposals'] for p in r['positions']], [2, 1])
        self.assertEqual([p['agreement'] for p in r['positions']], [1, 0])

    def test_incomplete(self):
        p = packet(); p['trace'] = TRACE.rsplit('\n', 1)[0]
        with self.assertRaises(ValueError): analyze_pair(p)

    def test_forged_match(self):
        p = packet(); p['trace'] = TRACE.replace('target=3 match=0', 'target=3 match=1')
        with self.assertRaises(ValueError): analyze_pair(p)

    def test_missing_counter(self):
        p = packet(); del p['traced_response']['timings']['draft_n_accepted']
        with self.assertRaises(ValueError): analyze_pair(p)

    def test_control_mismatch(self):
        p = packet(); p['control_response']['tokens'] = [9, 11]
        with self.assertRaises(ValueError): analyze_pair(p)

    def test_setting(self):
        p = packet(); p['greedy'] = False
        with self.assertRaises(ValueError): analyze_pair(p)

    def test_prefix_accept_count(self):
        p = packet(); p['control_response']['timings']['draft_n_accepted'] = 3; p['traced_response']['timings']['draft_n_accepted'] = 3
        with self.assertRaises(ValueError): analyze_pair(p)

    def test_prompt_request_mismatch(self):
        p = packet(); p['traced_request']['n_predict'] = 129
        with self.assertRaises(ValueError): analyze_pair(p)

    def test_stray_marker(self):
        p = packet(); p['trace'] += '\nG8_COMPARE_ROW broken'
        with self.assertRaises(ValueError): analyze_pair(p)

if __name__ == '__main__': unittest.main()
