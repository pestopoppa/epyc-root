"""Both scientific dive states enforce explicit/new-era read scope; legacy/discovery unchanged."""
import importlib.util
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / '.claude/skills/research-intake/scripts/validate_intake.py'
spec = importlib.util.spec_from_file_location('read_depth_validator', PATH)
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
STATES = ('dive-verified', 'dive-overturned')

class ReadDepthScopeTests(unittest.TestCase):
    def entry(self, state, date='2026-10-06'):
        return dict(id='intake-001', arxiv_id=None, url='https://example.org/primary',
                    source_type='blog', title='Primary source', categories=['test'],
                    novelty='high', relevance='high', discovered_via='input',
                    verdict='worth_investigating', ingested_date=date,
                    verification=state, key_claims=['Bounded source statement'])

    def errors(self, entry):
        # Check the complete result: acceptance must not conceal unrelated fixture failures.
        return v.validate_index([entry], {'test'})

    def anchors(self):
        return [dict(claim_index=0, kind='html-span', locator='https://example.org/primary#claim')]

    def depth_error(self, state, value):
        return (f"intake-001: {state} requires read_depth FULL|PARTIAL (got {value!r}); "
                "DIGEST/WebFetch reads stay stage1-unverified")

    def anchor_error(self, state):
        return f"intake-001: {state} requires non-empty claim_anchors"

    def test_full_and_partial_accepted_for_both_dive_states(self):
        for state in STATES:
            for date in ('2026-10-06', '2026-10-07'):
                for depth in ('FULL', 'PARTIAL'):
                    with self.subTest(state=state, date=date, depth=depth):
                        entry = self.entry(state, date)
                        entry.update(read_depth=depth, claim_anchors=self.anchors())
                        self.assertEqual(self.errors(entry), [])

    def test_declared_digest_refused_for_both_even_legacy_date(self):
        for state in STATES:
            with self.subTest(state=state):
                entry = self.entry(state, '2026-10-06')
                entry.update(read_depth='DIGEST', claim_anchors=self.anchors())
                self.assertEqual(self.errors(entry), [self.depth_error(state, 'DIGEST')])

    def test_new_era_missing_read_scope_and_anchors_refused_for_both(self):
        for state in STATES:
            with self.subTest(state=state):
                self.assertEqual(self.errors(self.entry(state, '2026-10-07')),
                                 [self.depth_error(state, None), self.anchor_error(state)])

    def test_explicit_valid_depth_requires_anchor_for_both(self):
        for state in STATES:
            with self.subTest(state=state):
                entry = self.entry(state, '2026-10-06')
                entry['read_depth'] = 'PARTIAL'
                self.assertEqual(self.errors(entry), [self.anchor_error(state)])

    def test_legacy_without_declared_depth_grandfathered_for_both(self):
        for state in STATES:
            with self.subTest(state=state):
                self.assertEqual(self.errors(self.entry(state, '2026-10-06')), [])

    def test_stage1_digest_remains_discovery_only_outside_scientific_gate(self):
        entry = self.entry('stage1-unverified', '2026-10-07')
        entry['read_depth'] = 'DIGEST'
        self.assertEqual(self.errors(entry), [])

if __name__ == '__main__':
    unittest.main()
