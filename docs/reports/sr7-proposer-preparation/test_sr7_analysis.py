import copy
import unittest
from unittest.mock import patch
import sr7_analysis as a
from test_proposer_stats import line


def fixture():
    windows, records = [], []
    for w in range(3):
        entries = []
        for c in a.CLASSES:
            for i in range(5):
                pid = f'{w}-{c}-{i}'
                entries.append({'id': pid, 'class': c, 'seed': w * 100 + len(entries)})
                for mode, width in a.ARMS:
                    trace = line('draft-mtp', 10, width)
                    if mode == 'composed':
                        trace = line('ngram-mod', 10, width) + '\n' + trace
                    n = 20 if mode == 'composed' else 10
                    records.append({'window': str(w), 'prompt': pid, 'mode': mode, 'width': width,
                        'http_status': 200, 'seed': entries[-1]['seed'], 'lifecycle_verified': True, 'runtime_seal_verified': True, 'settings_verified': True,
                        'complete_response': True, 'output_token_ids': [1, 2], 'prompt_token_ids': [1, 2, 3, 4, 5], 'trace': trace,
                        'response': {'stop_type': 'eos', 'tokens_predicted': 2, 'timings': {'draft_n': n, 'draft_n_accepted': width * (2 if mode == 'composed' else 1)}}})
        windows.append({'id': str(w), 'prompts': entries})
    return {'seal_verified': True, 'windows': windows}, records


class AnalysisTest(unittest.TestCase):
    @patch.object(a, 'DRAWS', 30)
    def test_complete_and_reproducible(self):
        plan, records = fixture()
        result = a.analyze(plan, records)
        self.assertEqual(result, a.analyze(plan, records))
        self.assertEqual(result['cross_window']['2_4'], 'REPLICATED_RISE')
        self.assertEqual(result['windows']['0']['comparisons']['decomposition_2_4']['status'], 'DEFINED')

    @patch.object(a, 'DRAWS', 10)
    def test_fail_closed(self):
        plan, records = fixture()
        variants = [records[:-1], records + records[:1]]
        for mutate in ('counter', 'budget', 'lifecycle', 'trace'):
            rs = copy.deepcopy(records)
            if mutate == 'counter': rs[0]['response']['timings']['draft_n'] += 1
            if mutate == 'budget': rs[0]['response']['stop_type'] = 'limit'
            if mutate == 'lifecycle': rs[0]['lifecycle_verified'] = False
            if mutate == 'trace': rs[0]['trace'] = ''
            variants.append(rs)
        for rs in variants:
            self.assertEqual(a.analyze(plan, rs)['status'], 'UNKNOWN')
        plan['windows'][1]['prompts'][0]['seed'] = plan['windows'][0]['prompts'][0]['seed']
        self.assertEqual(a.analyze(plan, records)['status'], 'UNKNOWN')

    @patch.object(a, 'DRAWS', 10)
    def test_zero_proposer_undefined(self):
        plan, records = fixture()
        for r in records:
            if r['mode'] == 'composed':
                r['trace'] = line('ngram-mod', 0, 0, 0, 0, 0) + '\n' + line('draft-mtp', 10, r['width'])
                r['response']['timings'] = {'draft_n': 10, 'draft_n_accepted': r['width']}
        result = a.analyze(plan, records)
        self.assertEqual(result['windows']['0']['comparisons']['decomposition_2_4']['status'], 'UNDEFINED')
        self.assertIsNone(result['windows']['0']['cells']['composed_2']['proposers']['ngram-mod']['acceptance'])

if __name__ == '__main__':
    unittest.main()
