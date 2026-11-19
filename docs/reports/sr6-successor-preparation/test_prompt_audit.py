import copy
import hashlib
import unittest
import prompt_audit as audit


def rows():
    return {"prompts": [{"id": str(i), "class": cls, "window": str(i), "seed": i,
                          "prompt": f"prompt {i}", "rendered_prompt": f"rendered {i}",
                          "rendered_token_ids": [1, 2, 3, 4, 5, 1, 2, 3, 4, 5],
                          "source": "fixture", "source_kind": "non_model"}
                         for i, cls in enumerate(("code", "rag", "prose"))]}


class PromptAuditTest(unittest.TestCase):
    def test_repetition_and_pass(self):
        report = audit.audit(rows(), set(), set())
        self.assertEqual(report['prompts'][0]['repeated_5gram']['numerator'], 1)
        self.assertEqual(report['prompts'][0]['repeated_5gram']['denominator'], 6)
        self.assertEqual(report['status'], 'SCOPED_PASS_NOT_PUBLICATION_AUTHORITY')

    def test_prior_and_exposure_rejected(self):
        digest = hashlib.sha256(b'prompt 0').hexdigest()
        for prior, exposure in (({digest}, set()), (set(), {digest})):
            with self.assertRaises(ValueError):
                audit.audit(rows(), prior, exposure)

    def test_missing_and_duplicate_rejected(self):
        for mutation in ('seed', 'window', 'tokens', 'source'):
            m = copy.deepcopy(rows())
            if mutation == 'seed': m['prompts'][1]['seed'] = 0
            if mutation == 'window': m['prompts'][1]['window'] = '0'
            if mutation == 'tokens': m['prompts'][1]['rendered_token_ids'] = []
            if mutation == 'source': m['prompts'][1]['source_kind'] = 'model'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                audit.audit(m, set(), set())

    def test_inventory_formats_and_failure(self):
        d = hashlib.sha256(b'x').hexdigest()
        self.assertEqual(audit.hashes({'prompts': [{'prompt': 'x'}]}), {d})
        self.assertEqual(audit.hashes({'prompt_sha256': [d]}), {d})
        with self.assertRaises(ValueError): audit.hashes({})
        with self.assertRaises(ValueError): audit.hashes({'prompt_sha256': ['bad']})


if __name__ == '__main__': unittest.main()
