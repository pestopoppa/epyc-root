import json
from pathlib import Path
import unittest
from grammar import DECISIONS, KINDS, ORDERS, grammar


class GrammarTest(unittest.TestCase):
    def test_root_orders_and_identical_remaining_rules(self):
        d = grammar('decision-first').splitlines()
        e = grammar('evidence-first').splitlines()
        self.assertEqual(d[1:], e[1:])
        for root, order in ((d[0], ORDERS['decision-first']), (e[0], ORDERS['evidence-first'])):
            positions = [root.index(json.dumps(json.dumps(k) + ':')) for k in order]
            self.assertEqual(positions, sorted(positions))
        self.assertNotEqual(d[0], e[0])

    def test_evidence_and_feedback_always_present_same_languages(self):
        for arm in ORDERS:
            g = grammar(arm)
            self.assertIn('evidence-item', g)
            self.assertIn('advisory ::=', g)
            self.assertIn('feedback', g)
            self.assertIn('(evidence-item (ws', g)
            self.assertIn('evidence-item)*)?', g)  # evidence list accepts empty
            for value in (*DECISIONS, *KINDS):
                self.assertIn(json.dumps(json.dumps(value)), g)
        with self.assertRaises(ValueError):
            grammar('prompt-first')

    def test_subset_examples_validate_full_schema_if_available(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest('jsonschema unavailable')
        path = Path('/mnt/raid0/llm/epyc-orchestrator/orchestration/review_decision.schema.json')
        if not path.exists():
            self.skipTest('full schema unavailable')
        schema = json.loads(path.read_text())
        for evidence in ([], [{'kind': 'file_span', 'ref': 'src/a.py:1'}]):
            for decision in DECISIONS:
                data = {'decision': decision, 'confidence': 0.5, 'blocking': {'tripwire': False},
                        'evidence': evidence, 'advisory': {'feedback': 'check'}}
                jsonschema.Draft202012Validator(schema).validate(data)

if __name__ == '__main__':
    unittest.main()
