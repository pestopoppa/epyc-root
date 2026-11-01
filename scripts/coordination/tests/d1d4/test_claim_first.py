"""Pure controls: lock custody must precede issuing an ID-bound nonce."""
import importlib.util,os,pathlib,sys,tempfile,types,unittest
from unittest.mock import patch
V=pathlib.Path(__file__).resolve().parents[2]/'qual_v2';sys.path.insert(0,str(V))
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
q=load('claim_first_q',V/'qualify_launcher.py');gate=load('claim_first_gate',V/'keeper_qual_gate.py')
class Tests(unittest.TestCase):
 def setUp(self):self.m={'production':True,'regions':'mi210_0,184-191','id':'candidate','rate_basis':{'scope':'r22-unknown-calibration'},'qualification':{'receipt':'/nonexistent/receipt'}}
 def test_no_claim_no_nonce(self):
  with patch.object(q,'load_manifest',return_value=self.m),patch.object(q,'choose_cpus'),patch.dict(os.environ,{'WS58_QUAL_GPU_HELD':'1'}),patch.object(q,'gpu_claim_ancestor',side_effect=q.Refused('absent')),patch.object(q,'issue') as issue:
   with self.assertRaises(q.Refused):q.claim_issue_run(pathlib.Path('/m'),pathlib.Path('/f'),300)
   issue.assert_not_called()
 def test_claim_then_issue_then_native(self):
  events=[]
  with patch.object(q,'load_manifest',return_value=self.m),patch.object(q,'choose_cpus',side_effect=lambda m:events.append('placement')),patch.dict(os.environ,{'WS58_QUAL_GPU_HELD':'1'}),patch.object(q,'gpu_claim_ancestor',side_effect=lambda i:events.append('held')),patch.object(q,'issue',side_effect=lambda *a:events.append('issued') or 'n'),patch.object(q,'run',side_effect=lambda *a:events.append('native') or {'ok':True}):
   self.assertEqual(q.claim_issue_run(pathlib.Path('/m'),pathlib.Path('/f'),300),{'ok':True})
  self.assertEqual(events,['placement','held','issued','native'])
 def test_signal_during_nonce_prevents_native_start(self):
  def interrupted_issue(*args):
   q.request_interrupt(q.signal.SIGTERM,None)
   return 'issued'
  with patch.object(q,'INTERRUPTED',False),patch.object(q,'load_manifest',return_value=self.m),patch.object(q,'choose_cpus'),patch.dict(os.environ,{'WS58_QUAL_GPU_HELD':'1'}),patch.object(q,'gpu_claim_ancestor'),patch.object(q,'issue',side_effect=interrupted_issue) as issue,patch.object(q,'run') as run:
   with self.assertRaisesRegex(q.Refused,'after nonce issuance'):q.claim_issue_run(pathlib.Path('/m'),pathlib.Path('/f'),300)
   issue.assert_called_once();run.assert_not_called()
 def test_cpu_claim_and_ram_before_nonce(self):
  m=dict(self.m,regions='0-95',rate_basis={'scope':q.VKQ_BOOTSTRAP_SCOPE});events=[]
  with patch.object(q,'load_manifest',return_value=m),patch.object(q,'choose_cpus'),patch.dict(os.environ,{'WS58_QUAL_GPU_HELD':'0'}),patch.object(q,'vkq_cpu_claim_ancestor',side_effect=lambda i:events.append('held')),patch.object(q.subprocess,'run',return_value=types.SimpleNamespace(returncode=1)),patch.object(q,'issue') as issue:
   with self.assertRaises(q.Refused):q.claim_issue_run(pathlib.Path('/m'),pathlib.Path('/f'),300)
   issue.assert_not_called();self.assertEqual(events,['held'])
 def test_busy_lock_preserves_fresh_id_and_returns_wait(self):
  with tempfile.TemporaryDirectory() as td:
   f=pathlib.Path(td);(f/'ready').mkdir();m=dict(self.m,hold=None,qual_timeout_s=300)
   with patch.object(gate.q,'load_manifest',return_value=m),patch.object(gate.q,'disk_wait',return_value=False),patch.object(gate.q,'verify',side_effect=gate.q.Refused('missing')),patch.object(gate,'qual_pair',return_value='122-123'),patch.object(gate,'run_under_claim',return_value=types.SimpleNamespace(returncode=75)),patch.object(gate.q,'issue') as issue:
    state,reason=gate.qualify_pending(f/'m',f,f/'rl',300)
   self.assertEqual(state,'wait-resource');self.assertIn('before nonce',reason);issue.assert_not_called();self.assertFalse((f/'qual-nonces').exists())
 def test_post_issue_failure_does_not_claim_retryable(self):
  with tempfile.TemporaryDirectory() as td:
   f=pathlib.Path(td);(f/'ready').mkdir();marker=f/'qual-nonces/by-id/candidate.json';marker.parent.mkdir(parents=True);marker.write_text('{}');m=dict(self.m,hold=None,qual_timeout_s=300)
   with patch.object(gate.q,'load_manifest',return_value=m),patch.object(gate.q,'disk_wait',return_value=False),patch.object(gate.q,'verify',side_effect=gate.q.Refused('missing')),patch.object(gate,'qual_pair',return_value='122-123'),patch.object(gate,'run_under_claim',return_value=types.SimpleNamespace(returncode=75)):
    self.assertEqual(gate.qualify_pending(f/'m',f,f/'rl',300)[0],'bad')
if __name__=='__main__':unittest.main()
