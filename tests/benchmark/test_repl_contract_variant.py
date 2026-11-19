"""Zero-model contract tests against the exact producer Git objects."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('variant', Path(__file__).resolve().parents[2] / 'scripts/benchmark/repl_contract_variant.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def reply(code):
    return '```python\n' + code + '\n```'


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.driver, cls.binding = v.load_driver()
        cls.fx = cls.driver.fx

    def test_schema_and_wait_visible_from_turn_one(self):
        prompt = self.fx.build_prompt(self.fx.build_episode(0), [], 'current', 1)
        for key in self.fx.KEYS:
            self.assertIn(key, prompt)
        self.assertIn('wait until Q7', prompt)
        self.assertNotIn('Q2:', prompt)

    def test_early_final_recovery_every_rendering(self):
        ep = self.fx.build_episode(0)
        for rendering in self.fx.RENDERINGS:
            def policy(prompt, turn):
                if turn == 2:
                    self.assertIn('premature FINAL rejected', prompt)
                if turn == 7:
                    self.assertIn('Q7:', prompt)
                    return reply('FINAL(' + repr(ep['expected']) + ')')
                return reply('saved = 123\nFINAL({"Q1": "early"})' if turn == 1 else 'assert saved == 123')
            played = self.fx.play_episode(ep, rendering, policy)
            self.assertEqual(played['n_turns'], 7)
            self.assertEqual(self.fx.classify(played['final'], ep)['cls'], 'correct')
            self.assertIn('premature FINAL rejected', played['turns'][0]['obs'])

    def test_wrong_post_q7_is_scored_without_repair(self):
        ep = self.fx.build_episode(1)
        for submit_turn in (7, 8, 9):
            played = self.fx.play_episode(ep, 'current', lambda p,t: reply('FINAL({"Q1": "wrong"})' if t == submit_turn else 'pass'))
            self.assertEqual(played['n_turns'], submit_turn)
            self.assertEqual(played['how'], 'final')
            self.assertEqual(self.fx.classify(played['final'], ep)['cls'], 'wrong')

    def test_non_dict_q7_keeps_bad_final(self):
        ep = self.fx.build_episode(0)
        played = self.fx.play_episode(ep, 'current', lambda p,t: reply('FINAL(1)' if t == 7 else 'pass'))
        self.assertEqual(played['how'], 'bad_final')
        self.assertIsNone(played['final'])

    def test_never_final_hits_cap(self):
        played = self.fx.play_episode(self.fx.build_episode(0), 'current', lambda p,t: reply('FINAL({})' if t < 7 else 'pass'))
        self.assertEqual((played['how'], played['n_turns']), ('no_final', 9))

    def test_binding_and_pinned_port_helpers(self):
        self.assertEqual(self.binding['variant'], 'progressive-final-contract-v2')
        self.assertEqual(len(self.binding['variant_sha256']), 64)
        rp = self.driver._load('run_repl_preview')
        self.assertEqual(rp.parse_role('test=http://127.0.0.1:9466@123')[2], 123)
        with self.assertRaises(SystemExit):
            rp.prove_port_ownership('http://127.0.0.1:8000', 123, {8000})

    def test_unbound_cell_directory_refused(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'stale.jsonl').write_text('{}\n')
            with self.assertRaisesRegex(ValueError, 'unbound'):
                v.main(['--mock', '--cell-dir', d])

    def test_corpus_renderings_and_scorer_unchanged(self):
        original = v.source('repl_composite_fixture')
        ns = {'__name__': 'original'}
        exec(compile(original, '<pinned>', 'exec'), ns)
        for i in (0, 1, 29):
            self.assertEqual(ns['build_episode'](i), self.fx.build_episode(i))
        for rendering in self.fx.ALL_RENDERINGS:
            text = '\n'.join('line ' + str(i) for i in range(30))
            self.assertEqual(ns['render_obs'](text, rendering), self.fx.render_obs(text, rendering))
        ep = self.fx.build_episode(0)
        for final in (None, {}, ep['expected'], {'lead': ep['expected']['lead']}):
            self.assertEqual(ns['classify'](final, ep), self.fx.classify(final, ep))


if __name__ == '__main__':
    unittest.main()
