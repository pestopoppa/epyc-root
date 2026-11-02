"""Offline checks of original Q38 payloads and scorer against fake responses."""

import copy
import hashlib
import json
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
            event = {'choices': [{'index': 0, 'delta': {'content': 'answer',
                                                        'reasoning_content': 'reason'},
                                  'finish_reason': 'stop'}], 'timings': timings}
            raw = 'data: ' + json.dumps(event) + '\n\ndata: [DONE]\n\n'
            return {'http_status': 200, 'content': 'answer', 'reasoning': 'reason',
                    'finish': 'stop', 'token_ids': [1, 2, 3], 'timings': timings,
                    'stream_complete': True, 'raw_stream': raw,
                    'raw_stream_sha256': hashlib.sha256(raw.encode()).hexdigest(),
                    'tokenizer_provenance': self.proof('reason\nanswer', server)}
        content = '2-4-1-9-ORCHID; Mbeki Larsen' if original.QUESTION in text else '<answer>5</answer>'
        payload = {'choices': [{'message': {'content': content}, 'finish_reason': 'stop'}], 'timings': timings}
        raw = json.dumps(payload)
        return {'http_status': 200, 'body': payload, 'raw_body': raw,
                'raw_body_sha256': hashlib.sha256(raw.encode()).hexdigest(),
                'token_ids': [1, 2, 3], 'timings': timings,
                'tokenizer_provenance': self.proof(content, server)}

    @staticmethod
    def proof(text, server):
        token_raw = json.dumps({'tokens': [1, 2, 3]})
        return {'method': 'retokenized_text', 'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                'tokenizer_sha256': 'a' * 64,
                'token_ids_sha256': hashlib.sha256(b'[1,2,3]').hexdigest(),
                'model_sha256': 'b' * 64, 'pid': 123 if server == 'drafted' else 124, 'birth': '456',
                'identity_evidence_sha256': 'c' * 64, 'server_url': 'http://127.0.0.1:1234',
                'tokenizer_response': token_raw,
                'tokenizer_response_sha256': hashlib.sha256(token_raw.encode()).hexdigest()}


class PayloadTest(unittest.TestCase):
    def setUp(self):
        p = 'nonce and facts: 2-4-1-9-ORCHID and Mbeki Larsen'
        self.plan = successor.build_plan([{'id': 'p1', 'suite': 's', 'prompt': 'question'}],
                                         [successor.FrozenContext(2000, 20, (p + '1', p + '2'), 5)],
                                         tokenizer_sha256='a' * 64, model_sha256='b' * 64)
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
        comparator = json.dumps({'rows': [{'target': 2000, 'variant': 'drafted',
                                            'decode_tps': 2.5, 'draft_acc': 0.5}]}).encode()
        reference = successor.render_markdown(report, mtp_comparator=comparator)
        self.assertIn('Historical MTP reference', reference)
        self.assertIn(hashlib.sha256(comparator).hexdigest(), reference)
        self.assertIn('| 2000 | 5 | 2.5 | 2.0 |', reference)
        with self.assertRaises(ValueError):
            successor.parse_mtp_comparator(b'{"rows": [{"target": 0}]}')

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
        mutated_stream = copy.deepcopy(run)
        streaming = next(row for row in mutated_stream['records']
                         if row['kind'] == 'measure' and row['key'] == 'B/2000/decode/1')
        streaming['response']['content'] = 'not the emitted answer'
        self.assertEqual(successor.score(self.plan, mutated_stream, self.gt)['status'], 'UNKNOWN')
        wrong_tokenizer = copy.deepcopy(run)
        first = next(row for row in wrong_tokenizer['records'] if row['kind'] == 'measure')
        first['response']['tokenizer_provenance']['tokenizer_sha256'] = 'b' * 64
        self.assertEqual(successor.score(self.plan, wrong_tokenizer, self.gt)['status'], 'UNKNOWN')
        wrong_process = copy.deepcopy(run)
        drafted = next(row for row in wrong_process['records'] if row['kind'] == 'measure'
                       and row['arm'] == 'drafted' and row['key'] == 'B/2000/decode/1')
        drafted['response']['tokenizer_provenance']['pid'] = 987
        self.assertEqual(successor.score(self.plan, wrong_process, self.gt)['status'], 'UNKNOWN')
        dirty = copy.deepcopy(self.plan)
        dirty.pairs[0].body['max_tokens'] = 201
        self.assertEqual(successor.score(dirty, run, self.gt)['status'], 'UNKNOWN')
        missing_speed = copy.deepcopy(run)
        first = next(row for row in missing_speed['records'] if row['kind'] == 'measure')
        first['response']['timings'].pop('predicted_per_second')
        first['response']['body']['timings'].pop('predicted_per_second', None)
        raw = json.dumps(first['response']['body'])
        first['response']['raw_body'] = raw
        first['response']['raw_body_sha256'] = hashlib.sha256(raw.encode()).hexdigest()
        report = successor.score(self.plan, missing_speed, self.gt)
        self.assertFalse(report['verdict']['speed_valid'])
        self.assertTrue(report['verdict']['speed_missing'])

    def test_original_regression_rule_detects_worse_drafted_output(self):
        run, _ = self.run_fake()
        drafted = next(row for row in run['records'] if row['key'] == 'A/p1' and row['arm'] == 'drafted')
        drafted['response']['body']['choices'][0]['message']['content'] = '<answer>4</answer>'
        raw = json.dumps(drafted['response']['body'])
        drafted['response']['raw_body'] = raw
        drafted['response']['raw_body_sha256'] = hashlib.sha256(raw.encode()).hexdigest()
        drafted['response']['tokenizer_provenance'] = FakeRuntime.proof('<answer>4</answer>', 'drafted')
        report = successor.score(self.plan, run, self.gt)
        self.assertEqual(report['status'], 'COMPLETE')
        self.assertEqual(report['verdict']['correctness'], 'FAIL')
        self.assertTrue(report['A']['paired']['regressions'])

    def test_incomplete_stream_stops_before_the_next_arm(self):
        class Broken(FakeRuntime):
            def request(self, server, body, kind):
                response = super().request(server, body, kind)
                if body.get('stream'):
                    response['stream_complete'] = False
                return response
        rt = Broken()
        run = coordinator.run_pairs(rt, self.recipes, list(self.plan.pairs))
        self.assertTrue(run['partial'])
        self.assertEqual(run['cleanup'], {'drafted': True})
        self.assertTrue(all(arm == 'drafted' for arm, _, _ in rt.sent))
        self.assertEqual(successor.score(self.plan, run, self.gt)['status'], 'UNKNOWN')

    def test_attested_entry_rejects_unowned_transport_before_launch(self):
        rt = FakeRuntime()
        with self.assertRaisesRegex(ValueError, 'owned native transport'):
            successor.run_attested_plan(rt, self.recipes, self.plan)
        self.assertEqual(rt.sent, [])


if __name__ == '__main__':
    unittest.main()
