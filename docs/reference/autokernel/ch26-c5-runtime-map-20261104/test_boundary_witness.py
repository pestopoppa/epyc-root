import json,pathlib,tempfile,unittest,time,itertools
from unittest.mock import patch
import boundary_witness as w
class P:
 pid=7
 def poll(self):return None
def quiet():return {'verdict':'PASS','basis':'CLAIM_WITNESS','owned':{'pids':[77],'incomplete':[]},'region_claims':[{'role':'GLOBAL','region':'q'+str(i),'held':True,'holder_pids':[77],'unattributed_holders':0} for i in range(4)]}
class T(unittest.TestCase):
 def setUp(self):
  self.d=tempfile.TemporaryDirectory();self.p=pathlib.Path(self.d.name)/'w.jsonl';self.ident={'pid':7,'start_ticks':4,'boot_id':'boot'}
  self.capture_patch=patch('runtime_linkage.capture',return_value={'target':self.ident,'status':'matching-c5-mapped-inodes','coverage':'point-in-time-only','measurement_admission':'none'});self.capture_patch.start();self.addCleanup(self.capture_patch.stop)
  self.counter=itertools.count()
  self.placement=lambda pid:{'monotonic_ns':time.monotonic_ns(),'pid':pid,'start_ticks':4,'topology':{'0':0,'1':0},'tasks':{'7':{'cpu':next(self.counter)%2,'node':0}}}
 def tearDown(self):self.d.cleanup()
 def hook(self, snapshot=None, quiet_fn=quiet, **kwargs):
  return w.Hook(P(),1,self.p,snapshot=snapshot or (lambda p:{7:set(range(96)),8:set(range(96))}),
                quiet=quiet_fn,request_context={'prompt_id':'prompt','request_sha256':'a'*64,
                'phase':'measurement','slot_index':0},launch_ordinal=1,runtime_prepared={'dummy':1},**kwargs)
 def test_boundaries_record_only_observed_facts(self):
  with patch('boundary_witness.identity',return_value=self.ident):
      h=self.hook(placement_sample=self.placement,placement_interval_s=0.005);h.begin();time.sleep(0.02);h.end()
  r=json.loads(self.p.read_text());self.assertEqual(r['status'],'observed-at-boundaries');self.assertEqual(r['placement_continuous'],'unproven');self.assertEqual(r['contention_continuous'],'unproven');self.assertEqual(r['placement_observation'],'sampled-during-request');self.assertGreaterEqual(len(r['placement_samples']),2);self.assertEqual(r['placement_continuous'],'unproven')
 def test_incomplete_or_wrong_scope_refused(self):
  for snap,qfn in [(lambda p:{7:{0}},quiet),(lambda p:{7:{0},8:{96}},quiet),(lambda p:{7:{0},8:{1}},lambda:{'verdict':'COULD_NOT_CHECK'})]:
   with self.subTest(snap=snap,quiet=qfn),patch('boundary_witness.identity',return_value=self.ident):
    h=self.hook(snapshot=snap,quiet_fn=qfn,placement_sample=self.placement,placement_interval_s=0.005)
    with self.assertRaises(ValueError):h.begin()
 def test_thread_churn_refused(self):
  steps=iter([{7:set(range(96)),8:set(range(96))},{7:set(range(96)),8:set(range(96)),9:{0}}])
  with patch('boundary_witness.identity',return_value=self.ident):
   h=self.hook(snapshot=lambda _:next(steps),placement_sample=self.placement,placement_interval_s=0.005);h.begin()
   with self.assertRaises(ValueError):h.end()
 def test_runtime_target_and_changed_inode_refused(self):
  capture=iter([{'target':self.ident,'inode':1},{'target':self.ident,'inode':2}])
  with patch('boundary_witness.identity',return_value=self.ident),patch('runtime_linkage.capture',side_effect=lambda *a:next(capture)):
   h=self.hook(placement_sample=self.placement,placement_interval_s=0.005);h.begin();h.placement.collect=lambda *a:[{},{}]
   with self.assertRaisesRegex(ValueError,'mapped binaries changed'):h.end()
  with patch('boundary_witness.identity',return_value=self.ident),patch('runtime_linkage.capture',return_value={'target':{'pid':7,'start_ticks':5,'boot_id':'boot'}}):
   h=self.hook(placement_sample=self.placement,placement_interval_s=0.005)
   with self.assertRaisesRegex(ValueError,'target identity'):h.begin()
 def test_claim_owner_change_refused(self):
  first=quiet();second=quiet();second['owned']['pids']=[77,78]
  for claim in second['region_claims']:claim['holder_pids']=[78]
  qs=iter([first,second])
  with patch('boundary_witness.identity',return_value=self.ident):
   h=self.hook(quiet_fn=lambda:next(qs),placement_sample=self.placement,placement_interval_s=0.005);h.begin()
   with self.assertRaises(ValueError):h.end()
if __name__=='__main__':unittest.main()
