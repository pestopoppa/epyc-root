"""Offline checks of original Q38 payloads and scorer against fake responses."""

import copy
import unittest

import q38_t7 as original
import q38_t7_isolated as coordinator
import q38_t7_payloads as successor


class FakeRuntime:
    def __init__(self): self.sent = []
    def stopping(self): return False
    def start(self, arm, recipe): return arm
    def verify(self, server, arm, recipe): assert server == arm
    def stop(self, server): return True
    def request(self, server, body, kind):
        self.sent.append((server, kind, copy.deepcopy(body)))
        timings = {'cache_n': 10, 'prompt_n': 10, 'predicted_n': 20,
                   'predicted_per_second': 5, 'draft_n': 10, 'draft_n_accepted': 5}
        if kind == 'warm':
            return {'http_status': 200, 'timings': timings}
        text = body['messages'][-1]['content']
        if body.get('stream'):
            return {'http_status': 200, 'content': 'answer', 'reasoning': 'reason',
                    'finish': 'stop', 'token_ids': [1, 2, 3], 'timings': timings}
        content = '2-4-1-9-ORCHID; Mbeki Larsen' if original.QUESTION in text else '<answer>5</answer>'
        return {'http_status': 200, 'body': {'choices': [{'message': {'content': content},
                                                           'finish_reason': 'stop'}]},
                'token_ids': [1, 2, 3], 'timings': timings}


class PayloadTest(unittest.TestCase):
    def setUp(self):
        p = 'nonce and facts: 2-4-1-9-ORCHID and Mbeki Larsen'
        self.plan = successor.build_plan([{'id': 'p1', 'suite': 's', 'prompt': 'question'}],
                                         [successor.FrozenContext(2000, 20, (p + '1', p + '2'), 5)])
        self.gt = {'p1': {'expected': '5', 'scoring_method': 'exact_match'}}
        base = {'binary': 'bound', 'model': 'bound', 'shape': {'np': 1}}
        self.recipes = {'drafted': dict(base, draft_model='draft', draft_options={'type': 'dflash'}),
                        'nodraft': dict(base, draft_model=None, draft_options={})}

    def run_fake(self):
        runtime = FakeRuntime()
        return coordinator.run_pairs(runtime, self.recipes, list(self.plan.pairs)), runtime

    def test_requests_keep_original_settings_and_independent_warmup(self):
        run, runtime = self.run_fake()
        self.assertFalse(run['partial'])
        self.assertEqual([p.key for p in self.plan.pairs],
                         ['A/p1', 'B/2000/decode/1', 'B/2000/decode/2', 'B/2000/needle'])
        a = self.plan.pairs[0].body
        self.assertEqual((a['max_tokens'], a['temperature'], a['cache_prompt']), (200, 0.0, False))
        final = self.plan.pairs[2]
        self.assertEqual((final.body['max_tokens'], final.nodraft_body['max_tokens']), (1500, 500))
        self.assertEqual(self.plan.pairs[1].arms, ('drafted',))
        self.assertTrue(all('speculative' not in str(body) for _, _, body in runtime.sent))
        self.assertEqual(sum(kind == 'warm' for _, kind, _ in runtime.sent), 5)

    def test_original_paired_scorer_and_reporting(self):
        run, _ = self.run_fake()
        report = successor.score(self.plan, run, self.gt)
        self.assertEqual(report['status'], 'COMPLETE')
        self.assertEqual(report['A']['greedy_identical'], 1)
        self.assertEqual(report['A']['paired']['regressions'], [])
        self.assertEqual(report['A']['dflash2']['token_weighted_decode_tps'], 5)
        self.assertEqual(len(report['B']['rows']), 5)
        self.assertEqual(report['verdict']['correctness'], 'PASS')
        self.assertFalse(report['historical_timing_comparable'])
        rendered = successor.render_markdown(report)
        self.assertIn('Greedy identity: 1/1', rendered)
        self.assertIn('independently warmed context probes', rendered)
        self.assertIn('historical timing is not directly comparable', rendered)

    def test_missing_or_tampered_evidence_is_unknown(self):
        run, _ = self.run_fake()
        partial = copy.deepcopy(run); partial['records'].pop()
        self.assertEqual(successor.score(self.plan, partial, self.gt)['status'], 'UNKNOWN')
        missing = copy.deepcopy(run)
        first = next(row for row in missing['records'] if row['kind'] == 'measure')
        first['response'].pop('token_ids')
        self.assertEqual(successor.score(self.plan, missing, self.gt)['status'], 'UNKNOWN')
        mutated = copy.deepcopy(run)
        next(row for row in mutated['records'] if row['kind'] == 'measure')['body_sha256'] = 'bad'
        self.assertEqual(successor.score(self.plan, mutated, self.gt)['status'], 'UNKNOWN')
        dirty = copy.deepcopy(self.plan)
        dirty.pairs[0].body['max_tokens'] = 201
        self.assertEqual(successor.score(dirty, run, self.gt)['status'], 'UNKNOWN')
        missing_speed = copy.deepcopy(run)
        first = next(row for row in missing_speed['records'] if row['kind'] == 'measure')
        first['response']['timings'].pop('predicted_per_second')
        report = successor.score(self.plan, missing_speed, self.gt)
        self.assertFalse(report['verdict']['speed_valid'])
        self.assertTrue(report['verdict']['speed_missing'])

    def test_original_regression_rule_detects_worse_drafted_output(self):
        run, _ = self.run_fake()
        drafted = next(row for row in run['records'] if row['key'] == 'A/p1' and row['arm'] == 'drafted')
        drafted['response']['body']['choices'][0]['message']['content'] = '<answer>4</answer>'
        report = successor.score(self.plan, run, self.gt)
        self.assertEqual(report['status'], 'COMPLETE')
        self.assertEqual(report['verdict']['correctness'], 'FAIL')
        self.assertTrue(report['A']['paired']['regressions'])


if __name__ == '__main__':
    unittest.main()
