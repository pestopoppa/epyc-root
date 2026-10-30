import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import entry_qualification as q

def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v));return p
class Proof(unittest.TestCase):
 def fixture(self,root):
  decl='d'*64;source='s'*64;attempt=root/'campaign-control-fixture';attempt.mkdir()
  request=write(attempt/'0-redel_delegate_wait/redel_delegate_wait/outbound-requests/0000.json',{'model':'pinned','tools':[{'function':{'name':'delegate'}},{'function':{'name':'wait'}}]})
  write(attempt/'0-redel_delegate_wait/redel_delegate_wait/entry-quiesce.json',{'schema':'evl34-entry-quiescence/v1','all_inflight_drained':True,'acknowledged':True})
  write(attempt/'capture.json',{'source_sha256':source,'declaration_sha256':decl})
  write(attempt/'result.json',{'source_sha256':source,'server_drained':True,'partial':True,'failure':None,'qualification':{'qualified':True,'scope':'entry-only'},'wire_capture':{'requests':1,'first_tools':['delegate','wait'],'tool_choice':'auto','first_wire_sha256':q.sha(request)},'statuses':{'49/production_repl':'unknown','49/redel_delegate_wait':'unknown'}})
  write(root/'campaign-supervisor.json',{'rc':0,'reason':None,'drained':True,'elapsed':42})
  write(attempt/'SERVER.json',{'pid':1,'birth_ticks':2})
  (attempt/'gpu-witness.jsonl').write_text(json.dumps({'hip_mapped':True,'pid':1,'birth':2,'bound':[{'pid':1,'start_ticks':2}]})+'\n')
  journal=root/'control-journal'
  for name,arm,status in [('a','production_repl','partial_entry_repl'),('b','redel_delegate_wait','partial_entry_redel')]:
   write(journal/(name+'.start'),{'identity':{'arm':arm,'campaign_sha256':decl,'id':'49'}})
   write(journal/(name+'.native'),{'arm':arm,'campaign_sha256':decl,'id':'49','native':{'status':status,'request_evidence':[{}],'server_usage':{'completion_tokens':2}}})
  return decl,source,attempt
 def test_receipt_missing_tamper_quiescence_and_no_delegation_required(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);decl,source,attempt=self.fixture(root);receipt=root/'receipt.json'
   with patch.object(q,'ROOT',root),patch.object(q,'RECEIPT',receipt):
    with self.assertRaises(FileNotFoundError):q.verify(decl,source)
    write(receipt,q.build(attempt,decl,source));self.assertEqual(q.verify(decl,source)['scope'],'entry-only')
    path=attempt/'0-redel_delegate_wait/redel_delegate_wait/entry-quiesce.json';write(path,{'schema':'evl34-entry-quiescence/v1','all_inflight_drained':False,'acknowledged':True})
    with self.assertRaises(ValueError):q.verify(decl,source)
 def test_child_request_budget(self):
  from repl_depth import ChildRequestBudget
  b=ChildRequestBudget()
  for _ in range(16):b.reserve()
  with self.assertRaises(RuntimeError):b.reserve()
  self.assertEqual(ChildRequestBudget().calls,0)
if __name__=='__main__':unittest.main()
