import copy
import unittest
from check_serving_binding import check

def fixture():
    roles={}
    for role in ('architect_critic','coder_escalation','ingest_long_context'):
        roles[role]={'serving':{'server_role':'architect_critic','ports':[8083],'launch':{'requirements':{'model_path':'/model','draft_model_path':'/draft'},'runtime':{'flags':{'spec':{'enabled':role=='architect_critic','type':'draft-dflash' if role=='architect_critic' else None}}}}}}
    entries=[{'role':r,'model_path':'/model', 'baseline':{'recipe':{'extra_server_args':['-md','/draft']}},'candidate':{'recipe':{'extra_server_args':['-md','/draft']}}} for r in roles]
    return {'roles':roles},{'models':entries}

class BindingChecks(unittest.TestCase):
    def test_aliases_follow_primary_not_inert_alias_metadata(self):
        a,b=fixture();self.assertEqual(check(a,b),[])
    def test_two_aliases_without_draft_are_refused(self):
        a,b=fixture()
        for e in b['models'][1:]:
            for arm in ('baseline','candidate'):e[arm]['recipe']['extra_server_args']=[]
        self.assertEqual(len(check(a,b)),4)
    def test_scope_change_refused(self):
        a,b=fixture();a['roles']['coder_escalation']['serving']['server_role']='other'
        with self.assertRaises(ValueError):check(a,b)
    def test_cli_never_returns_success_for_unbound_scope(self):
        import json, subprocess, sys, tempfile
        from pathlib import Path
        import yaml
        a, b = fixture()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / 'p.yml').write_text(yaml.safe_dump(a)); (root / 'plan.json').write_text(json.dumps(b))
            script = Path(__file__).with_name('check_serving_binding.py')
            def run():
                return subprocess.run([sys.executable, str(script), '--priors', str(root / 'p.yml'), '--plan', str(root / 'plan.json'), '--output', str(root / 'out.json')], capture_output=True).returncode
            self.assertEqual(run(), 3)  # matching serving truth does not establish a floor or best recipe
            b['models'][1]['baseline']['recipe']['extra_server_args'] = []
            (root / 'plan.json').write_text(json.dumps(b))
            self.assertEqual(run(), 2)

    def test_primary_spec_change_refused(self):
        a,b=fixture();a['roles']['architect_critic']['serving']['launch']['runtime']['flags']['spec']['enabled']=False
        with self.assertRaises(ValueError):check(a,b)

if __name__=='__main__': unittest.main()
