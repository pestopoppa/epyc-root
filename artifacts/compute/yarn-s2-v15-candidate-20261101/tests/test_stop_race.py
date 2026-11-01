"""Verify a stop arriving after todo construction but before exposure begins."""
import ast, hashlib, json, os, tempfile, types, unittest
from pathlib import Path
from unittest.mock import patch
from one_item import OneItemBudget
from test_worker_integration import FakeExposure, FakeClient

class StopRace(unittest.TestCase):
 def test_stop_already_set_before_native_call(self):
  tree=ast.parse(Path('worker.one-item.py').read_text())
  body=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='DeadlineClient']
  module=ast.fix_missing_locations(ast.Module(body=body,type_ignores=[]))
  with tempfile.TemporaryDirectory() as t:
   root=Path(t); (root/'exposures').mkdir(); stop=root/'STOP'; stop.touch()
   exposure=FakeExposure(); budget=OneItemBudget(); budget.first_pending([{'item_id':'a'}])
   env={'out':str(root),'mode':'cohort','current_item':{'item_id':'a','prompt_sha256':'p'},'arm':'A0','grant_bytes':b'x','hashlib':hashlib,'json':json,'Path':Path,'os':os,'item_budget':budget,'exposure':exposure,'r':types.SimpleNamespace(Client=FakeClient,ServerError=RuntimeError),'limited_open':lambda *a:None,'deadline':'9999999999','time':types.SimpleNamespace(time=lambda:0),'InfrastructureCutoff':RuntimeError}
   exec(compile(module,'worker.one-item.py','exec'),env)
   with patch.dict(os.environ, {'FILLER_STOPFILE':str(stop)}):
    try: env['DeadlineClient']('unused').chat([],max_tokens=1,thinking=False,timeout=1)
    except RuntimeError: pass
   self.assertEqual(exposure.starts, [], 'already signalled STOP must prevent a new exposure')
 def test_stop_arrives_during_begin_preserves_unknown_and_skips_http(self):
  tree=ast.parse(Path('worker.one-item.py').read_text())
  body=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='DeadlineClient']
  module=ast.fix_missing_locations(ast.Module(body=body,type_ignores=[]))
  with tempfile.TemporaryDirectory() as t:
   root=Path(t); (root/'exposures').mkdir(); stop=root/'STOP'
   class ExposureWithStop(FakeExposure):
    def begin(self, ledger, arm, item, prompt, grant, kind):
     super().begin(ledger,arm,item,prompt,grant,kind); stop.touch()
   class ClientSpy(FakeClient):
    calls=0
    def chat(self, *args, **kwargs): ClientSpy.calls+=1; return super().chat(*args, **kwargs)
   exposure=ExposureWithStop(); budget=OneItemBudget(); budget.first_pending([{'item_id':'a'}])
   env={'out':str(root),'mode':'cohort','current_item':{'item_id':'a','prompt_sha256':'p'},'arm':'A0','grant_bytes':b'x','hashlib':hashlib,'json':json,'Path':Path,'os':os,'item_budget':budget,'exposure':exposure,'r':types.SimpleNamespace(Client=ClientSpy,ServerError=RuntimeError),'limited_open':lambda *a:None,'deadline':'9999999999','time':types.SimpleNamespace(time=lambda:0),'InfrastructureCutoff':RuntimeError}
   exec(compile(module,'worker.one-item.py','exec'),env)
   with patch.dict(os.environ, {'FILLER_STOPFILE':str(stop)}):
    with self.assertRaisesRegex(RuntimeError,'retain unknown'):
     env['DeadlineClient']('unused').chat([],max_tokens=1,thinking=False,timeout=1)
   self.assertEqual(exposure.starts,['a']); self.assertEqual(exposure.done,set()); self.assertEqual(ClientSpy.calls,0)
 def test_smoke_retains_multi_item_behavior(self):
  tree=ast.parse(Path('worker.one-item.py').read_text())
  body=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='DeadlineClient']
  module=ast.fix_missing_locations(ast.Module(body=body,type_ignores=[]))
  with tempfile.TemporaryDirectory() as t:
   root=Path(t); (root/'exposures').mkdir(); stop=root/'STOP'; stop.touch()
   exposure=FakeExposure(); budget=OneItemBudget()
   env={'out':str(root),'mode':'smoke','current_item':{'item_id':'a','prompt_sha256':'p'},'arm':'A0','grant_bytes':b'x','hashlib':hashlib,'json':json,'Path':Path,'os':os,'item_budget':budget,'exposure':exposure,'r':types.SimpleNamespace(Client=FakeClient,ServerError=RuntimeError),'limited_open':lambda *a:None,'deadline':'9999999999','time':types.SimpleNamespace(time=lambda:0,monotonic=lambda:0),'InfrastructureCutoff':RuntimeError}
   exec(compile(module,'worker.one-item.py','exec'),env)
   with patch.dict(os.environ, {'FILLER_STOPFILE':str(stop),'YARN_SMOKE_START_DEADLINE_MONOTONIC':'10'}):
    client=env['DeadlineClient']('unused'); client.chat([],max_tokens=1,thinking=False,timeout=1)
    env['current_item'].update(item_id='b',prompt_sha256='q'); client.chat([],max_tokens=1,thinking=False,timeout=1)
   self.assertEqual(exposure.starts,['a','b']); self.assertEqual(exposure.done,{'a','b'})
if __name__=='__main__': unittest.main()
