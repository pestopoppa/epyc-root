"""Zero-model acceptance tests: real isolated REPL, no server or benchmark run."""
import importlib.util
from pathlib import Path
import re
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('upfront', Path(__file__).resolve().parents[2] / 'scripts/benchmark/repl_upfront_variant.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def reply(code):
    return '```python\n' + code + '\n```'


# An independent reference program consumes only documents actually read. It
# never accesses the episode's expected answer or hidden corpus from the policy.
SOLVE = '''
import re
text = '\\n'.join(notes)
lead = re.search(r'project ' + project + r' \\| lead (.*?) \\| prev lead', text).group(1)
site, region = re.search(r'project ' + project + r' \\| site (\\S+) \\| region (\\w+)', text).groups()
budget = int(re.search(r'project ' + project + r' \\| approved budget_k (\\d+)', text).group(1))
rate = int(re.search(re.escape(lead) + r' \\| hourly_rate (\\d+)', text).group(1))
mult = int(re.search(r'region ' + region + r' \\| cost multiplier pct (\\d+)', text).group(1))
adjustments = [int(n) for n in re.findall(r'project ' + project + r' \\| audit_\\d+ adjustment_k (-?\\d+)', text)]
assert len(adjustments) == 6
FINAL(dict(lead=lead, site=site, region=region, budget_k=budget, lead_rate=rate,
           mult_pct=mult, loaded_budget_k=budget*mult//100+sum(adjustments)))
'''


class UpfrontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.driver, cls.binding = v.load_driver()
        cls.fx = cls.driver.fx

    def test_all_questions_visible_on_first_and_later_turns(self):
        ep = self.fx.build_episode(0)
        for t in (1, 4, 13):
            prompt = self.fx.build_prompt(ep, [], 'current', t)
            for question in ep['questions']:
                self.assertIn(question, prompt)
            self.assertIn('ONE read', prompt)
            self.assertNotIn('Questions so far', prompt)
        self.assertEqual(self.fx.MAX_TURNS, 16)

    def test_seeded_chain_has_no_oracle_in_prompt(self):
        ep = self.fx.build_episode(3)
        self.assertEqual(ep, self.fx.build_episode(3))
        self.assertNotEqual(ep, self.fx.build_episode(4))
        self.assertEqual(len(ep['docs']), 12)
        for j, doc in enumerate(ep['docs'][:-1]):
            self.assertIn('NEXT_DOCUMENT=' + ep['docs'][j+1]['id'], doc['text'])
        self.assertLess(max(len(d['text']) + len(d['title']) for d in ep['docs']), self.fx.OBS_CAP)
        first = self.fx.build_prompt(ep, [], 'full', 1)
        self.assertNotIn(ep['expected']['lead'], first)
        self.assertNotIn(ep['docs'][1]['id'], first)

    def test_real_retrieval_enforces_one_per_cell_and_chain(self):
        ep = self.fx.build_episode(0)
        a, b = [d['id'] for d in ep['docs'][:2]]
        blocks = [f"print(read('{a}')); print(read('{b}'))", f"print(read('{b}'))"]
        res = self.fx.exec_blocks(ep, blocks)
        self.assertIn('one document per cell', res[0]['err'])
        self.assertIsNone(res[1]['err'])
        self.assertIn('Research packet 2/12', res[1]['out'])
        for code in (f"read('{b}')", "search('roster')", "FINAL({})"):
            r = self.fx.exec_blocks(ep, [code])[0]
            self.assertFalse(r['research_complete'])
            if not code.startswith('FINAL'):
                self.assertIsNotNone(r['err'])

    def test_early_final_cannot_skip_research_even_on_late_turn(self):
        ep = self.fx.build_episode(0)
        played = self.fx.play_episode(ep, 'current', lambda p,t: reply('FINAL({})'))
        self.assertEqual((played['how'], played['n_turns']), ('no_final', 16))
        self.assertTrue(all('premature FINAL rejected' in t['obs'] for t in played['turns']))

    def test_saved_facts_solve_after_long_history_in_every_rendering(self):
        for rendering in self.fx.ALL_RENDERINGS:
            ep = self.fx.build_episode(2)
            def policy(prompt, t):
                if t <= 12:
                    doc_id = (re.search(r"Start with read\('([^']+)'", prompt).group(1) if t == 1
                              else re.findall(r'NEXT_DOCUMENT=([0-9a-f]+)', prompt)[-1])
                    init = f"notes = []\nproject = {ep['project']!r}\n" if t == 1 else ''
                    return reply(init + f"notes.append(read('{doc_id}'))\nprint(notes[-1])")
                return reply(SOLVE)
            played = self.fx.play_episode(ep, rendering, policy)
            self.assertEqual((played['how'], played['n_turns']), ('final', 13), rendering)
            self.assertEqual(self.fx.classify(played['final'], ep)['cls'], 'correct', rendering)
            self.assertIn('Research packet 1/12', played['turns'][0]['obs'])

    def test_history_only_control_loses_early_facts_under_current(self):
        ep = self.fx.build_episode(0)
        turns = [{'code': 'print(read(next_document))', 'obs': d['title']+'\n'+d['text'], 'reply': ''}
                 for d in ep['docs']]
        full = self.fx.build_prompt(ep, turns, 'full', 13)
        current = self.fx.build_prompt(ep, turns, 'current', 13)
        self.assertEqual(self.fx._facts(full, ep['project'])['lead'], ep['expected']['lead'])
        self.assertNotIn('lead', self.fx._facts(current, ep['project']))
        self.assertEqual(len(re.findall(r'project '+ep['project']+r' \| audit_\d+ adjustment_k (-?\d+)', full)), 6)

    def test_post_research_wrong_and_non_dict_submissions_keep_scoring(self):
        ep = self.fx.build_episode(0)
        for submission, how, cls in (("{}", 'final', 'wrong'), ("1", 'bad_final', 'no_answer')):
            def policy(prompt, t):
                if t <= 12:
                    doc_id = (re.search(r"Start with read\('([^']+)'", prompt).group(1) if t == 1
                              else re.findall(r'NEXT_DOCUMENT=([0-9a-f]+)', prompt)[-1])
                    return reply(f"print(read('{doc_id}'))")
                return reply('FINAL(' + submission + ')')
            played = self.fx.play_episode(ep, 'bounded_k3', policy)
            self.assertEqual((played['how'], played['n_turns']), (how, 13))
            self.assertEqual(self.fx.classify(played['final'], ep)['cls'], cls)

    def test_original_renderings_and_scoring_preserved(self):
        ns = {'__name__': 'original'}
        exec(v.base.source('repl_composite_fixture'), ns)
        ep = self.fx.build_episode(0)
        for rendering in self.fx.ALL_RENDERINGS:
            text = '\n'.join('sample line ' + str(i) for i in range(30))
            self.assertEqual(ns['render_obs'](text, rendering), self.fx.render_obs(text, rendering))
        for answer in (None, {}, ep['expected']):
            self.assertEqual(ns['classify'](answer, ep), self.fx.classify(answer, ep))
        with self.assertRaisesRegex(ValueError, 'old progressive'):
            self.fx.reference_policy('reader', ep['project'])

    def test_binding_and_stale_resume_refusal(self):
        self.assertEqual(self.binding['variant'], v.VARIANT)
        self.assertIn('upfront_wrapper_sha256', self.binding)
        self.assertEqual(self.binding, v.load_driver()[1])
        self.assertNotEqual(self.binding['variant_sha256'], v.base.load_driver()[1]['variant_sha256'])
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'contract-binding.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'different-variant'):
                v.main(['--cell-dir', d])


if __name__ == '__main__':
    unittest.main()
