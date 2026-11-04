import unittest
from plan_guard import verify_plan, PlanError


def plan():
    return {'greedy': True, 'single_slot': True, 'single_drafter': True, 'target_k':'f16', 'target_v':'f16',
            'draft_v':'f16', 'target_model':'/m/model.gguf', 'draft_model':'/m/model.gguf',
            'cells':[{'draft_k': k, 'width': n} for k in ('q4_0','q8_0') for n in (4,8,16)],
            'control':'fresh-trace-off-and-on-token-identical',
            'metric':'teacher-forced-match-and-prefix-acceptance',
            'model_preflight': {'sha256':'a'*64}, **{k:'a'*64 for k in ('server_sha256','backend_sha256','patch_sha256','prompt_manifest_sha256')}}

class PlanTests(unittest.TestCase):
    def test_valid(self): self.assertEqual(verify_plan(plan())['cells'], 6)
    def test_reject_duplicate(self):
        p=plan(); p['cells'][5]=p['cells'][0]
        with self.assertRaises(PlanError): verify_plan(p)
    def test_reject_different_model(self):
        p=plan(); p['draft_model']='/m/other.gguf'
        with self.assertRaises(PlanError): verify_plan(p)
    def test_reject_wrong_target(self):
        p=plan(); p['target_v']='q8_0'
        with self.assertRaises(PlanError): verify_plan(p)
    def test_reject_missing_receipt(self):
        p=plan(); p['backend_sha256']=''
        with self.assertRaises(PlanError): verify_plan(p)
    def test_reject_bad_model_digest(self):
        p=plan(); p['model_preflight']['sha256']='x'
        with self.assertRaises(PlanError): verify_plan(p)
    def test_reject_missing_identity(self):
        p=plan(); p['control']='none'
        with self.assertRaises(PlanError): verify_plan(p)
    def test_reject_bool_width(self):
        p=plan(); p['cells'][0]['width']=True
        with self.assertRaises(PlanError): verify_plan(p)

if __name__ == '__main__': unittest.main()
