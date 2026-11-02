import copy
import unittest
from worker import build_schedule, canonical, digest_bytes, repetition


def packet():
    sampler = {'temperature': 0.7, 'top_p': 0.9, 'n_predict': 128}
    prior = []
    seals = {k: 'a' * 64 for k in ('model', 'binary', 'libraries', 'launch', 'template', 'tokenizer', 'decision_rule')}
    seals.update(sampler=digest_bytes(canonical(sampler)), prior_prompt_hashes=digest_bytes(canonical(prior)))
    windows = []
    for w in range(3):
        blocks = []
        for b in range(4):
            n = w * 4 + b
            blocks.append({'prompts': [{'id': f'p{n}', 'seed': n, 'class': ('code', 'rag', 'prose')[n % 3],
                                       'prompt': f'prompt{n}', 'rendered': f'rendered{n}', 'rendered_tokens': [1, 2, 3, 4, n]}]})
        windows.append({'id': f'w{w}', 'blocks': blocks})
    return {'schema': 'sr6.capture-plan.v1', 'seals': seals, 'sampler': sampler, 'prior_prompt_hashes': prior, 'windows': windows}


class TestPlan(unittest.TestCase):
    def test_rotation_and_not_run(self):
        plan = build_schedule(packet())
        self.assertEqual(plan['state'], 'NOT_RUN')
        self.assertEqual({block['arm_order'][0] for block in plan['blocks']}, {'composed3','composed4','mtp3','mtp4','mtp4_repeat'})
        self.assertTrue(all(len(set(block['arm_order'])) == 5 for block in plan['blocks']))
    def test_repetition_occurrences(self):
        self.assertEqual(repetition([1,2,3,4,5,1,2,3,4,5])['numerator'], 1)
    def test_duplicate_seed_fails(self):
        p=packet();p['windows'][1]['blocks'][0]['prompts'][0]['seed']=0
        with self.assertRaises(ValueError): build_schedule(p)
    def test_prior_prompt_fails(self):
        p=packet();p['prior_prompt_hashes']=[digest_bytes(b'prompt0')];p['seals']['prior_prompt_hashes']=digest_bytes(canonical(p['prior_prompt_hashes']))
        with self.assertRaises(ValueError): build_schedule(p)
    def test_sampler_override_fails(self):
        p=packet();p['sampler']['seed']=1;p['seals']['sampler']=digest_bytes(canonical(p['sampler']))
        with self.assertRaises(ValueError): build_schedule(p)
    def test_two_windows_fails(self):
        p=packet();p['windows'].pop()
        with self.assertRaises(ValueError): build_schedule(p)
    def test_bad_seal_fails(self):
        p=packet();p['seals']['model']='missing'
        with self.assertRaises(ValueError): build_schedule(p)

if __name__ == '__main__': unittest.main()
