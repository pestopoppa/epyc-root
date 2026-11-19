import importlib.util,json,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest import mock
p=Path(__file__).parent
sys.path.insert(0,str(p))
spec=importlib.util.spec_from_file_location('runner',p/'r2362_runner.py'); r=importlib.util.module_from_spec(spec); spec.loader.exec_module(r)

class Lifecycle(unittest.TestCase):
 def test_owned_server_and_client_complete(self):
  with tempfile.TemporaryDirectory() as d:
   out=Path(d); child=[]; real_popen=subprocess.Popen
   class Finished:
    returncode=0
    def poll(self):return 0
   def popen(cmd,**kwargs):
    if str(cmd[1])==str(r.CLIENT):
     label=cmd[2]
     (out/(label+'.rows.jsonl')).write_text(''.join(json.dumps({'id':str(i),'sha':'hash','pred_ms':1})+'\n' for i in range(24)))
     kwargs['stdout'].write(b'warmup ok\nARM_DONE fixture\n');kwargs['stdout'].flush()
     return Finished()
    proc=real_popen(cmd,**kwargs);child.append(proc);return proc
   class Response:
    status=200
    def __enter__(self):return self
    def __exit__(self,*args):pass
   plan={'cmd':[sys.executable,'-c','import time; time.sleep(60)'],'env':{}}
   class Claim:
    def attest(self):return type('A',(),{'check':type('C',(),{'outcome':r.schemas.PASS})()})()
   with mock.patch.object(r.subprocess,'Popen',side_effect=popen),mock.patch.object(r.urllib.request,'urlopen',return_value=Response()),mock.patch.object(r.parts,'verify_runtime'),mock.patch.object(r.parts,'check_live_dso',return_value={'fake':'hash'}),mock.patch.object(r.annex_b,'validate_monitor_samples',return_value={'fixture':True}),mock.patch.object(r,'witness',return_value={'cpu_ledger':{},'competing':False}):
    result=r.run_one('old',1,out,plan,{},Claim())
   self.assertEqual(len(result),24);self.assertIsNotNone(child[0].poll())
 def test_runtime_refusal_terminates_owned_server(self):
  with tempfile.TemporaryDirectory() as d:
   out=Path(d); child=[]; real_popen=subprocess.Popen
   def popen(cmd,**kwargs):
    proc=real_popen(cmd,**kwargs);child.append(proc);return proc
   class Response:
    status=200
    def __enter__(self):return self
    def __exit__(self,*args):pass
   class Claim:
    def attest(self):return type('A',(),{'check':type('C',(),{'outcome':r.schemas.PASS})()})()
   plan={'cmd':[sys.executable,'-c','import time; time.sleep(60)'],'env':{}}
   with mock.patch.object(r.subprocess,'Popen',side_effect=popen),mock.patch.object(r.urllib.request,'urlopen',return_value=Response()),mock.patch.object(r.parts,'verify_runtime',side_effect=RuntimeError('foreign DSO')),mock.patch.object(r,'witness',return_value={'cpu_ledger':{},'competing':False}):
    with self.assertRaises(RuntimeError):r.run_one('instrument',1,out,plan,{},Claim())
   self.assertTrue(child);self.assertIsNotNone(child[0].poll())
 def test_campaign_alternates_and_aborts_on_parity(self):
  class Claim:
   def attest(self):return type('A',(),{'check':type('C',(),{'outcome':r.schemas.PASS})()})()
  with tempfile.TemporaryDirectory() as d:
   out=Path(d); calls=[]
   def arm(name,index,*args):
    calls.append((name,index));return {'p':'different' if name=='instrument' and index==2 else 'same'}
   with self.assertRaises(r.Refusal):r.campaign(out,{'old':{},'instrument':{}},{'old':{},'instrument':{}},Claim(),run_arm=arm)
   self.assertEqual(calls,[('old',1),('instrument',1),('instrument',2),('old',2)])
   self.assertTrue((out/'PARITY_FAIL.json').exists())
 def test_campaign_finishes_exactly_twelve_pairs(self):
  class Claim:
   def attest(self):return type('A',(),{'check':type('C',(),{'outcome':r.schemas.PASS})()})()
  with tempfile.TemporaryDirectory() as d:
   calls=[]
   def arm(name,index,*args):calls.append((name,index));return {'p':'same'}
   rows=r.campaign(Path(d),{'old':{},'instrument':{}},{'old':{},'instrument':{}},Claim(),run_arm=arm)
   self.assertEqual(len(rows),12);self.assertEqual(len(calls),24);self.assertEqual(calls[-2:], [('instrument',12),('old',12)])
 def test_missing_rows_refuse(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'rows';p.write_text('{}\n')
   with self.assertRaises(r.Refusal):r.rows_ok(p,p)
if __name__=='__main__':unittest.main()
