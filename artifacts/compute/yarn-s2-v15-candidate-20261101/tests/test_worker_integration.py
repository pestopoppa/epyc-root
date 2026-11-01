"""Execute actual candidate worker pending/chat hooks against a synthetic ledger."""
import ast
import hashlib
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from one_item import OneItemBudget

class FakeExposure:
    def __init__(self): self.starts=[]; self.done=set()
    def state(self, ledger, arm, item, prompt):
        return 'started' if item in self.starts else 'unexposed'
    def begin(self, ledger, arm, item, prompt, grant, kind): self.starts.append(item)
    def key(self, arm, item, prompt): return item
    def put(self, path, obj): path.write_text(json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n')
    def response(self, ledger, arm, item, prompt, digest): self.done.add(item)

class FakeClient:
    def __init__(self, url, opener=None): pass
    def chat(self, messages, **kwargs): return {'content':'ok'}

class Integration(unittest.TestCase):
    def test_remaining_items_do_not_report_plan_exhaustion(self):
        tree=ast.parse(Path('worker.one-item.py').read_text())
        matches=[n for n in tree.body if isinstance(n,ast.If) and 'one-item-boundary' in ast.unparse(n)]
        self.assertEqual(len(matches),1)
        module=ast.Module(body=matches,type_ignores=[]); ast.fix_missing_locations(module)
        for remaining,initial,expected in [(2,'plan-exhausted','one-item-boundary'),
                                            (0,'plan-exhausted','plan-exhausted'),
                                            (2,'deadline','deadline')]:
            run={'remaining':remaining,'stop_reason':initial}
            exec(compile(module,'worker.one-item.py','exec'),{'mode':'cohort','run':run})
            self.assertEqual(run['stop_reason'],expected)

    def test_native_selection_exposure_guard_and_remaining(self):
        source = Path('worker.one-item.py').read_text()
        tree = ast.parse(source)
        selected = [n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='pending']
        selected += [n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='DeadlineClient']
        self.assertEqual(len(selected), 2)
        module = ast.Module(body=selected,type_ignores=[]); ast.fix_missing_locations(module)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'exposures').mkdir(); (root/'plan').mkdir()
            # The real hook imports sibling modules by name; these doubles simulate the
            # authoritative cohort fold and allowlist without touching live state.
            scope=Path('SCOPE-s2-conservative.json'); scope.write_text('{"predecessor_unknown": []}')
            gate=types.ModuleType('eligible_gate'); gate.eligible=lambda scope,summary,arm: {'a','b'}
            cohort=types.ModuleType('cohort_status'); cohort.read=lambda *args: {}
            old_gate=sys.modules.get('eligible_gate'); old_cohort=sys.modules.get('cohort_status')
            sys.modules['eligible_gate']=gate; sys.modules['cohort_status']=cohort
            fake=FakeExposure(); records=[{'item_id':'a','prompt_sha256':'p'},{'item_id':'b','prompt_sha256':'q'}]
            env={'__file__':str(Path.cwd()/'worker.one-item.py'), 'old_pending':lambda *a: list(records),
                 'out':str(root), 'mode':'cohort', 'shard':'2', 'json':json, 'Path':Path, 'os':os, 'selection_used':False,
                 'item_budget':OneItemBudget(), 'exposure':fake, 'current_item':{}, 'arm':'A0',
                 'grant_bytes':b'grant', 'hashlib':hashlib, 'r':types.SimpleNamespace(Client=FakeClient,ServerError=RuntimeError),
                 'limited_open':lambda *a:None, 'deadline':'9999999999', 'time':types.SimpleNamespace(time=lambda:0),
                 'InfrastructureCutoff':RuntimeError}
            old_stop=os.environ.get('FILLER_STOPFILE'); os.environ['FILLER_STOPFILE']=str(root/'STOP')
            try:
                exec(compile(module,'worker.one-item.py','exec'),env)
                initial=env['pending'](None,root,'A0'); self.assertEqual([x['item_id'] for x in initial],['a'])
                env['current_item'].update(initial[0]); client=env['DeadlineClient']('unused')
                client.chat([],max_tokens=1,thinking=False,timeout=1)
                self.assertEqual(fake.starts,['a']); self.assertEqual(fake.done,{'a'})
                env['current_item'].clear(); env['current_item'].update(records[1])
                with self.assertRaisesRegex(RuntimeError,'one-item exposure budget refused'):
                    client.chat([],max_tokens=1,thinking=False,timeout=1)
                self.assertEqual(fake.starts,['a'])
                # Subsequent pending is full and the now-exposed first item is filtered.
                remaining=env['pending'](None,root,'A0'); self.assertEqual([x['item_id'] for x in remaining],['b'])
            finally:
                if old_stop is None: os.environ.pop('FILLER_STOPFILE',None)
                else: os.environ['FILLER_STOPFILE']=old_stop
                scope.unlink()
                if old_gate is None: sys.modules.pop('eligible_gate',None)
                else: sys.modules['eligible_gate']=old_gate
                if old_cohort is None: sys.modules.pop('cohort_status',None)
                else: sys.modules['cohort_status']=old_cohort

if __name__=='__main__': unittest.main()
