import tempfile,unittest
from pathlib import Path
from budget_guard import BudgetExceeded
from request_policy import RequestPolicy
import campaign_supervisor
from campaign_supervisor import supervise

class R11Tests(unittest.TestCase):
 def test_broker_budget_384_calls_and_refusal(self):
  policy=RequestPolicy('pinned')
  request={'model':'pinned','messages':[{'role':'user','content':'fixture'}],'max_tokens':4096,'temperature':0,'seed':42}
  for _ in range(384): policy.admit('/v1/chat/completions',request)
  self.assertEqual(policy.budget.reserved,1572864)
  with self.assertRaises(BudgetExceeded):policy.admit('/v1/chat/completions',request)
 def test_repl_transport_sends_4096_through_broker(self):
  import importlib,sys,types
  from unittest.mock import patch
  base=types.ModuleType('repl_broker_primitives')
  class Broker:
   def __init__(self,sock,model):self._evl34_model=model
  base.BrokerPrimitives=Broker
  class Pool:
   def take(self):return object()
   def put(self,sock):pass
  sent=[]
  with patch.dict(sys.modules,{'repl_broker_primitives':base}):
   sys.modules.pop('repl_pool_primitives',None)
   mod=importlib.import_module('repl_pool_primitives')
   with patch.object(mod,'send',side_effect=lambda sock,body:sent.append(body)), patch.object(mod,'recv',return_value={'response':{'choices':[{'message':{'content':'ok'}}]}}):
    self.assertEqual(mod.PoolPrimitives(Pool(),'pinned')._real_call('test',None),'ok')
   self.assertEqual(sent[0]['body']['max_tokens'],4096)
   policy=RequestPolicy('pinned');self.assertEqual(policy.admit(sent[0]['path'],sent[0]['body'])['reserved'],4096)
   sys.modules.pop('repl_pool_primitives',None)
 def test_pilot_refuses_before_rows_without_qualified_control(self):
  import importlib,sys,types
  from unittest.mock import patch
  stub=types.ModuleType('control_driver');stub.sha=lambda path: 'unused'
  with patch.dict(sys.modules,{'control_driver':stub}):
   sys.modules.pop('campaign_job',None)
   job=importlib.import_module('campaign_job')
   with patch.object(job,'identities',return_value={'independent_smoke_control':{'id':'49'}}), patch.object(stub,'sha',return_value=job.MANIFEST), patch('entry_qualification.verify',side_effect=ValueError('missing receipt')), patch.object(job,'rows',side_effect=AssertionError('pilot rows accessed')), patch.object(sys,'argv',['campaign_job.py']):
    with self.assertRaisesRegex(RuntimeError,'pilot refused'):job.main()
   sys.modules.pop('campaign_job',None)
 def test_cutoff_stops_child_and_drains(self):
  with tempfile.TemporaryDirectory() as d:
   import sys
   campaign_supervisor.FLOOR=0
   result=supervise([sys.executable,'-c','import time; time.sleep(30)'],Path(d)/'child.log',seconds=1,disk_path=d,stop=lambda:True)
   self.assertEqual(result['reason'],'stop');self.assertTrue(result['drained'])
if __name__=='__main__':unittest.main()
