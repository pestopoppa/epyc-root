"""Model-free tests for the lock holder and nested qualification drain."""
import importlib.util,pathlib,subprocess,sys,tempfile,types,unittest
from unittest.mock import patch
V=pathlib.Path(__file__).resolve().parents[2]/'qual_v2';sys.path.insert(0,str(V))
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
q=load('drain_test_qualifier',V/'qualify_launcher.py');gate=load('drain_test_gate',V/'keeper_qual_gate.py')
class Tests(unittest.TestCase):
 def test_invalid_default_timeout_cannot_issue_nonce(self):
  with tempfile.TemporaryDirectory() as td:
   flags=pathlib.Path(td);m={'production':True,'hold':None,'id':'new-id','qualification':{'receipt':str(flags/'receipt.json')}}
   with patch.object(gate.q,'load_manifest',return_value=m),patch.object(gate.q,'disk_wait',return_value=False),patch.object(gate.q,'verify',side_effect=gate.q.Refused('none')),patch.object(gate.q,'issue') as issue:
    result=gate.qualify_pending(flags/'manifest.json',flags,flags/'rl',17)
   issue.assert_not_called();self.assertEqual(result[0],'bad');self.assertIn('qual_timeout_s',result[1])
 def test_slow_acquisition_has_no_outer_lock_holder_kill(self):
  # The acquisition may consume all but the final second of its own limit;
  # its nested q.run still receives its complete independent timeout.
  events=[];args=['region-lock','run','--timeout-s','345','--','qualifier','--timeout','300']
  def run(argv,**kw):events.append(('acquired-after-344s',argv,kw));self.assertNotIn('timeout',kw);return types.SimpleNamespace(returncode=0)
  with patch.object(gate.subprocess,'run',side_effect=run),patch.object(gate.os,'kill') as kill:
   self.assertEqual(gate.run_under_claim(args,pathlib.Path('/f'),{},object()).returncode,0);kill.assert_not_called()
  self.assertEqual(events[0][1],args)
 def test_active_timeout_drains_adopted_nested_session_before_return(self):
  state={'claim_held':True,'group':True,'nested':True,'attempts':0};events=[]
  class Child:
   pid=41
   def wait(self,timeout):
    events.append(('wait',timeout));self.assert_held()
    if timeout!=8:raise subprocess.TimeoutExpired('owned',timeout)
    self.assert_drained();return -9
   def assert_held(self):
    if not state['claim_held']:raise AssertionError('claim released before drain')
   def assert_drained(self):
    if state['group'] or state['nested']:raise AssertionError('owned descendant survived')
  def stop(pid,birth):
   self.assertEqual((pid,birth),(41,50));self.assertTrue(state['claim_held']);state['group']=False;events.append('group-drain')
  def drain():
   self.assertTrue(state['claim_held']);state['attempts']+=1;events.append('descendants')
   if state['attempts']==1:raise q.Refused('nested child still draining')
   state['nested']=False
  with patch.object(q,'stop_group',side_effect=stop),patch.object(q,'drain_children',side_effect=drain),patch.object(q.time,'sleep'),patch.object(q.time,'monotonic',side_effect=[0,0,0,301]),patch.object(q.os,'kill') as kill:
   with self.assertRaisesRegex(q.Refused,'qualification interrupted/timed out'):q.wait_qualification(Child(),50,300)
   kill.assert_not_called()
  self.assertFalse(state['nested']);self.assertEqual(state['attempts'],2);self.assertTrue(state['claim_held'])
 def test_catchable_signals_stop_active_owned_child(self):
  for sig in (q.signal.SIGTERM,q.signal.SIGINT,q.signal.SIGHUP):
   q.INTERRUPTED=False;state={'drained':False}
   class Child:
    pid=41
    def wait(self,timeout):
     if timeout==8:self_test.assertTrue(state['drained']);return -15
     q.request_interrupt(sig,None);raise subprocess.TimeoutExpired('owned',timeout)
   self_test=self
   def drain(pid,birth):self.assertEqual((pid,birth),(41,50));state['drained']=True
   with patch.object(q,'drain_owned_group',side_effect=drain):
    with self.assertRaisesRegex(q.Refused,'interrupted'):q.wait_qualification(Child(),50,300)
   self.assertTrue(state['drained']);q.INTERRUPTED=False
 def test_fingerprint_signal_drains_captured_child(self):
  q.INTERRUPTED=False;state={'drained':False}
  class Child:
   pid=41;returncode=-15
   def communicate(self,timeout):
    if timeout==8:self_test.assertTrue(state['drained']);return ('','')
    q.request_interrupt(q.signal.SIGTERM,None);raise subprocess.TimeoutExpired('owned',timeout)
  self_test=self
  def drain(pid,birth):self.assertEqual((pid,birth),(41,50));state['drained']=True
  with patch.object(q.subprocess,'Popen',return_value=Child()),patch.object(q,'group_birth',return_value=50),patch.object(q,'drain_owned_group',side_effect=drain):
   with self.assertRaisesRegex(q.Refused,'interrupted'):q.launcher_namespace(pathlib.Path('/m'),{'launcher':{'path':'/l'}},{})
  self.assertTrue(state['drained']);q.INTERRUPTED=False
 def test_group_identity_failure_never_signals_unowned_group(self):
  events=[]
  with patch.object(q,'stop_group',side_effect=q.Refused('reused')),patch.object(q,'drain_children',side_effect=lambda:events.append('owned-reaped')),patch.object(q.os,'killpg') as killpg:
   with self.assertRaisesRegex(q.Refused,'safely'):q.drain_owned_group(41,50)
   killpg.assert_not_called();self.assertEqual(events,['owned-reaped'])
if __name__=='__main__':unittest.main()
