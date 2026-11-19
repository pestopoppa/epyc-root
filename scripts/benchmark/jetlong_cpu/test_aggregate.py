import json
import tempfile
import unittest
from pathlib import Path
import aggregate
import ledger

class AggregateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.planfile = self.root / 'plan.json'
        self.out = self.root / 'ledger'
        items = []
        for length in aggregate.LENGTHS:
            for depth in aggregate.DEPTHS:
                for n in range(5):
                    for seed in range(3):
                        items.append({'id': f'{length}-{depth}-{n}-{seed}', 'length': length,
                                      'depth_fraction': depth, 'needle_index': n,
                                      'seed_index': seed, 'expected': 'Answer 12'})
        self.planfile.write_text(json.dumps({'items': items}))
        self.plan, self.pin = ledger.initialize(self.out, self.planfile)

    def result(self, item, arm, status, response=None):
        ledger.start(self.out, self.plan, self.pin, item['id'], arm)
        ledger.finish(self.out, self.pin, item['id'], arm, status, response,
                      {'predicted_n': 10, 'predicted_ms': 500} if status == 'ok' else None)

    def test_partial_preserves_unknowns_and_timeouts(self):
        a, b = self.plan['items'][:2]
        self.result(a, 'J', 'ok', 'The answer is ANSWER 12.')
        self.result(a, 'Y', 'timeout')
        ledger.start(self.out, self.plan, self.pin, b['id'], 'J')
        r = aggregate.report(self.planfile, self.out)
        j, y = r['summaries'][:2]
        self.assertEqual((j['planned'], j['finished'], j['unknown'], j['unstarted']), (75, 1, 1, 73))
        self.assertEqual((j['strict_correct_terminal'], j['lenient_correct_terminal']), (0, 1))
        self.assertEqual((y['timeouts'], y['lenient_correct_terminal']), (1, 0))
        self.assertIsNone(j['lenient_accuracy'])
        self.assertTrue(all(x['recall_j_ge_y'] is None for x in r['comparisons']))
        self.assertFalse(r['task_complete'])

    def test_complete_timeout_is_failure_and_rates_are_paired(self):
        for i, item in enumerate(self.plan['items']):
            for arm in ledger.ARMS:
                if i == 0 and arm == 'J':
                    self.result(item, arm, 'timeout')
                else:
                    self.result(item, arm, 'ok', 'Answer 12')
        r = aggregate.report(self.planfile, self.out)
        self.assertEqual(r['state'], 'terminal_recall_only')
        self.assertEqual(r['summaries'][0]['lenient_accuracy'], 74 / 75)
        self.assertFalse(r['comparisons'][0]['recall_j_ge_y'])
        self.assertTrue(r['comparisons'][1]['recall_j_ge_y'])
        self.assertFalse(r['task_complete'])

    def test_refuses_mutated_or_incomplete_matrix(self):
        mutated = dict(self.plan)
        mutated['items'] = self.plan['items'][:-1]
        self.planfile.write_text(json.dumps(mutated))
        with self.assertRaises(ValueError): aggregate.report(self.planfile, self.out)
        (self.out / 'plan.sha256').unlink()
        ledger.initialize(self.out, self.planfile)
        with self.assertRaisesRegex(ValueError, 'incomplete'): aggregate.report(self.planfile, self.out)

if __name__ == '__main__': unittest.main()
