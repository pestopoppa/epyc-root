import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'scripts/harness'))
import hs_td1_probe as probe


class ClassificationTests(unittest.TestCase):
    def test_wrapper_supplies_all_runner_hooks(self):
        with patch.object(probe.runner, 'main', return_value=7) as run:
            self.assertEqual(probe.main(), 7)
        self.assertEqual(run.call_args.kwargs, dict(decision_fn=probe.decision,
                         summarize_fn=probe.summarize, case_payload=probe.case_payload,
                         reference_fields=probe.reference_fields, runtime_path=probe.__file__))

    def test_precondition_binds_support_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            job = Path(tmp)
            (job / 'cases.json').write_text('[]')
            manifest = dict(prepared_inputs=[], runtime_sha256=probe.runner.digest(probe.__file__),
                            support_sha256=probe.runner.digest(probe.runner.__file__),
                            cases_sha256=probe.runner.digest(job / 'cases.json'))
            (job / 'manifest.json').write_text(json.dumps(manifest))
            with patch.object(sys, 'argv', ['runtime.py', 'inputs', '--job', tmp]):
                self.assertEqual(probe.main(), 0)
                manifest['support_sha256'] = 'unprepared'
                (job / 'manifest.json').write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError, 'support source'):
                    probe.main()

    def response(self, value, finish='stop'):
        return {'choices': [{'finish_reason': finish, 'message': {'content': value}}]}

    def test_all_closed_combinations(self):
        for risk in probe.RISKS:
            for intent in probe.INTENTS:
                value = {'risk': risk, 'intent': intent, 'confidence': .8}
                self.assertEqual(probe.decision(self.response(json.dumps(value))), value)

    def test_invalid_response_is_unknown(self):
        base = {'risk': 'low', 'intent': 'read', 'confidence': .8}
        bad = [[], {}, dict(base, risk='unknown'), dict(base, intent='delete'),
               dict(base, confidence=True), dict(base, confidence=float('nan')),
               dict(base, confidence=float('inf')), dict(base, confidence=-.1),
               dict(base, confidence=1.1), dict(base, extra='ignored?')]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValueError):
                probe.decision(self.response(json.dumps(value)))
        for raw in ('{"risk":"high","risk":"low","intent":"read","confidence":1}', 'garbage'):
            with self.assertRaises(ValueError):
                probe.decision(self.response(raw))
        with self.assertRaises(ValueError):
            probe.decision(self.response(json.dumps(base), 'length'))

    def test_labels_do_not_leak(self):
        case = {'request': 'read', 'context': 'local', 'risk': 'low', 'intent': 'read',
                'decision': 'permissive', 'rationale': 'SECRET_REFERENCE'}
        self.assertEqual(set(probe.case_payload(case)), {'request', 'context'})
        self.assertNotIn('SECRET_REFERENCE', json.dumps(probe.case_payload(case)))
        self.assertIn('not an observed', probe.reference_fields(case)['reference_kind'])

    def row(self):
        return {'case_id': 'a', 'repetition': 0, 'phase': 'full', 'status': 'ok', 'elapsed_s': 2,
                'judgment': {'risk': 'low', 'intent': 'read', 'confidence': .8},
                'reference': {'risk': 'high', 'intent': 'read', 'decision': 'restrictive'}, 'record_path': 'a'}

    def test_missing_invalid_and_smoke(self):
        rows = [self.row(), dict(self.row(), case_id='b', status='unknown', elapsed_s=90),
                dict(self.row(), phase='smoke', elapsed_s=999)]
        result = probe.summarize(rows, 4)
        self.assertEqual((result['valid'], result['unknown'], result['observed']), (1, 3, 2))
        self.assertFalse(result['complete'])
        self.assertFalse(result['gate'])
        self.assertEqual(result['agreement_counts'], {'risk': 0, 'intent': 1, 'decision': 0})
        self.assertEqual(result['disagreements'], ['a'])
        self.assertEqual(result['mean_confidence_valid'], .8)
        self.assertEqual(result['all_attempt_call_s'], 92)

    def test_duplicate_and_excess_fail(self):
        with self.assertRaises(ValueError):
            probe.summarize([self.row(), self.row()], 2)
        with self.assertRaises(ValueError):
            probe.summarize([self.row()], 0)

    def test_complete_all_unknown_is_not_success(self):
        result = probe.summarize([dict(self.row(), status='unknown')], 1)
        self.assertTrue(result['complete'])
        self.assertEqual(result['unknown'], 1)
        self.assertIsNone(result['mean_confidence_valid'])

    def test_corpus_references_match_diagnostic_rule(self):
        cases = json.loads((ROOT / 'scripts/harness/hs_td1_cases.json').read_text())
        self.assertEqual(len({c['id'] for c in cases}), len(cases))
        for case in cases:
            self.assertEqual(probe.proposed_decision(case), case['decision'])


if __name__ == '__main__':
    unittest.main()
