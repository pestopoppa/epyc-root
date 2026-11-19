import unittest
from unittest.mock import patch
from producer import parse_output,stat_model,paired_deltas,remove_registration
from custody import validate_cpu_grant,Refusal,terminate_owned
class Controls(unittest.TestCase):
 def test_four_cpu_affinity(self):
  actual=set(range(184,192))
  def setcp(pid,value):actual.clear();actual.update(value)
  with patch('os.sched_getaffinity',side_effect=lambda pid:actual.copy()),patch('os.sched_setaffinity',side_effect=setcp):
   self.assertEqual(validate_cpu_grant('184-191',True)['affinity'],[184,185,186,187])
 def test_wrong_grant(self):
  with patch('os.sched_getaffinity',return_value=set(range(184,188))):
   with self.assertRaises(Refusal):validate_cpu_grant('0-3',True)
 def test_native_shape(self):
  s='own=128 n_act=4 draft=1 first_draft=1 kvu=1 ctk=q8_0 n_ctx=4096 : 1.000 ms/step  1000.0 steps/s  4000.0 tok/s'
  self.assertEqual(parse_output(s,1,128,2048)['ms_per_step'],1)
  self.assertEqual(parse_output(s,1,128,2048)['n_steps'],2048)
  for bad in ['',s+'\n'+s,s.replace('q8_0','f16'),s.replace('kvu=1','kvu=0')]:
   with self.assertRaises(Refusal):parse_output(bad,1,128,2)
 def test_pair_delta_is_arm_order_independent(self):
  def row(k,ms):return {'kvu':k,'metrics':{'ms_per_step':ms}}
  result=paired_deltas([row(1,115),row(0,100),row(0,200),row(1,230)])
  self.assertAlmostEqual(result[0]['unified_over_split_pct'],15)
  self.assertAlmostEqual(result[1]['unified_over_split_pct'],15)
  for bad in [[row(1,115)],[row(1,115),row(1,100)]]:
   with self.assertRaises(Refusal):paired_deltas(bad)
 def test_cleanup_refuses_reused_pid_without_signal(self):
  from unittest.mock import Mock
  proc=Mock(pid=99999999);proc.poll.return_value=None
  with patch('custody.birth_ticks',return_value=222),patch('custody.os.kill') as kill:
   with self.assertRaises(Refusal):terminate_owned(proc,111)
   kill.assert_not_called()
 def test_cleanup_exited_leader_never_signals_group(self):
  from unittest.mock import Mock
  proc=Mock(pid=99999999);proc.poll.return_value=0
  with patch('custody.proc_group_members',return_value=[123]),patch('custody.os.kill') as kill:
   with self.assertRaises(Refusal):terminate_owned(proc,111)
   kill.assert_not_called()
 def test_cleanup_registration_removes_only_verified_identity(self):
  import tempfile
  from pathlib import Path
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'pids';p.write_text('123 111\n999 888\n')
   with self.assertRaises(Refusal):remove_registration(123,222,str(p))
   self.assertEqual(p.read_text(),'123 111\n999 888\n')
   remove_registration(123,111,str(p))
   self.assertEqual(p.read_text(),'999 888\n')
 def test_belief_writer_refuses_qualification_and_missing_warrant(self):
  from belief_write import write_child
  for q in [True,False]:
   with self.assertRaises(ValueError):write_child('/does/not/exist',{}, {},qualification=q,manifest_sha='0'*64)
 def test_belief_success_binds_raw_hashes_and_one_process(self):
  from belief_write import write_child
  import tempfile,hashlib,json
  from pathlib import Path
  with tempfile.TemporaryDirectory() as tmp:
   run=Path(tmp);out=run/'stdout';err=run/'stderr';out.write_text('native output');err.write_text('native log')
   row={'index':0,'rc':0,'cleanup':{'verified_dead':True},'started_utc':'2026-11-04T00:00:00Z','completed_utc':'2026-11-04T00:00:01Z','samples':[{'own_vram_b':1,'gpu_bdf':'0000:43:00.0','mapped_libraries':{'libggml-hip.so':True}}]*2,'argv':['p3batch','model','16384','4','100'],'kvu':1,'metrics':{'ms_per_step':2},'stdout':str(out),'stderr':str(err),'raw_sha256':{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in [('stdout',out),('stderr',err)]}}
   assets={'model':{'path':'model','sha256':'0'*64},'source_commit':'1bceceb0514d423ad220888313eafcddc30e485e'}
   side=write_child(run,row,assets,qualification=False,manifest_sha='1'*64)
   tup=json.loads(Path(side).read_text())['claim_tuple']
   self.assertEqual(tup['reps'],1);self.assertEqual(tup['extra']['measured_correlated_steps'],100)
   self.assertEqual(tup['applicability']['np'],4);self.assertEqual(tup['metric_direction'],'lower_better')
   self.assertNotIn('threads',tup['applicability']);self.assertEqual(tup['extra']['host_cpu_affinity'],list(range(184,192)))
   self.assertIn('four batched sequences',tup['claim']);self.assertNotIn('independent',tup['claim'])
   warrant=json.loads((run/'child-00.json').read_text());self.assertEqual(warrant['row']['raw_sha256'],row['raw_sha256'])
   for path in [out,err]:
    old=path.read_text();path.write_text('mutated')
    with self.assertRaisesRegex(ValueError,'raw native file digest mismatch'):write_child(run,row,assets,qualification=False,manifest_sha='1'*64)
    path.write_text(old)
 def test_launcher_selects_four_before_integrity_checks(self):
  import os,subprocess
  from pathlib import Path
  launch=Path(__file__).parent/'launch.sh'
  actual=sorted(os.sched_getaffinity(0));self.assertGreaterEqual(len(actual),4)
  env=dict(os.environ,FILLER_CPUS='0-191')
  output=subprocess.check_output(['/bin/bash',str(launch),'--smoke-cpus'],env=env,text=True)
  self.assertEqual(output.strip(),','.join(map(str,actual[:4])))
  env['FILLER_CPUS']=str(actual[0])
  self.assertEqual(subprocess.run(['/bin/bash',str(launch),'--smoke-cpus'],env=env,capture_output=True).returncode,64)
 def test_changed_model_refuses(self):
  import json
  from pathlib import Path
  a=json.loads((Path(__file__).parent/'assets.json').read_text());a['model']['stat']['st_size']=0
  with self.assertRaises(Refusal):stat_model(a)
if __name__=='__main__':unittest.main()
