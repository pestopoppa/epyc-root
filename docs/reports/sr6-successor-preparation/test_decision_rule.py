import copy
import unittest
from decision_rule import ARMS, evaluate


def fixture(gain=1.20):
    expected, groups = {}, []
    for w in range(3):
        window = f'w{w}'
        expected[window] = []
        for cls in ('code', 'rag', 'prose'):
            for n in range(5):
                prompt = f'{window}-{cls}-{n}'
                expected[window].append(prompt)
                speeds = dict.fromkeys(ARMS, 100.0)
                speeds.update(composed3=100.0 * gain, mtp3=110.0)
                groups.append({'window': window, 'prompt_id': prompt, 'class': cls, 'tokens_per_second': speeds})
    return {'schema':'sr6.paired-analysis-draft.v1', 'status':'DESCRIPTIVE_ONLY', 'errors':[], 'groups':groups}, expected


class Tests(unittest.TestCase):
    def test_signal_is_only_candidate_and_deterministic(self):
        doc, exp = fixture()
        a = evaluate(doc, exp)
        self.assertEqual(a['candidate'], 'SIGNAL')
        self.assertIsNone(a['verdict'])
        self.assertEqual(a, evaluate(doc, exp))

    def test_below_threshold_is_inconclusive(self):
        doc, exp = fixture(1.02)
        self.assertEqual(evaluate(doc, exp)['candidate'], 'INCONCLUSIVE')

    def test_aa_variation_blocks(self):
        doc, exp = fixture()
        doc['groups'][0]['tokens_per_second']['mtp4_repeat'] = 130
        self.assertEqual(evaluate(doc, exp)['candidate'], 'INCONCLUSIVE')

    def test_incomplete_or_duplicate_unknown(self):
        doc, exp = fixture()
        doc['groups'].pop()
        self.assertEqual(evaluate(doc, exp)['status'], 'UNKNOWN')
        doc, exp = fixture()
        doc['groups'].append(copy.deepcopy(doc['groups'][0]))
        self.assertEqual(evaluate(doc, exp)['status'], 'UNKNOWN')

    def test_bad_input_and_control_fail_closed(self):
        doc, exp = fixture()
        doc['status'] = 'UNKNOWN'
        self.assertEqual(evaluate(doc, exp)['status'], 'UNKNOWN')
        doc, exp = fixture()
        for g in doc['groups']:
            g['tokens_per_second']['mtp3'] = 90
        self.assertEqual(evaluate(doc, exp)['candidate'], 'INCONCLUSIVE')

    def test_nonfinite_unknown(self):
        doc, exp = fixture()
        doc['groups'][0]['tokens_per_second']['mtp3'] = float('nan')
        self.assertEqual(evaluate(doc, exp)['status'], 'UNKNOWN')

if __name__ == '__main__':
    unittest.main()
