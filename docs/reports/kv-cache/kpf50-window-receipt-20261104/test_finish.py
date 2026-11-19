import hashlib, json, tempfile, unittest
from pathlib import Path
import window_custody as c

class Finish(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=Path(self.tmp.name);c.begin(self.p,'full-a','r1')
  self.evidence={}
  for key in ('outcome','cleanup','clock_before','clock_after','trace_manifest'):
   value={'window':'full-a','run_id':'r1'}
   if key=='outcome': value.update(schema='kpf50.window-outcome.v1',complete=True)
   if key=='cleanup': value.update(schema='kpf50.cleanup.v1',verified_dead=True,remaining_children=0)
   if key.startswith('clock_'):
    i=0 if key=='clock_before' else 1; offset=i*100
    rows=[{'host_before_ns':10+offset,'hsa_ticks':20+offset,'host_after_ns':11+offset},{'host_before_ns':12+offset,'hsa_ticks':21+offset,'host_after_ns':14+offset}]
    native=json.dumps({'schema':'epyc.kpf50.hsa-clock.v1','pid':1+i,'frequency_hz':1000,'samples':rows}).encode();native_name=key+'.raw.json';(self.p/native_name).write_bytes(native)
    value.update(schema='kpf50.clock-sample.v1',phase=key,hsa_tick=20+offset,hsa_hz=1000,mono_before_ns=10+offset,mono_after_ns=11+offset,pid=1+i,birth_ticks=2,process_start_bound_ns=offset,process_end_bound_ns=20+offset,producer_sha256='1'*64,native_file=native_name,native_sha256=hashlib.sha256(native).hexdigest())
   if key=='trace_manifest':
    name='full-a.r1.trace.csv';raw=b'KernelName,BeginNs,EndNs\nk,3,4\n';(self.p/name).write_bytes(raw)
    value.update(schema='kpf50.trace-manifest.v1',complete=True,files=[{'file':name,'sha256':hashlib.sha256(raw).hexdigest()}])
   name=key+'.json'; raw=json.dumps(value).encode(); (self.p/name).write_bytes(raw)
   self.evidence[key]={'file':name,'sha256':hashlib.sha256(raw).hexdigest()}
 def test_complete_advances_once(self):
  c.finish(self.p,'full-a','r1',self.evidence)
  c.begin(self.p,'mask-a','r1',c.validate_prior)
  with self.assertRaises(FileExistsError):c.finish(self.p,'full-a','r1',self.evidence)
 def test_tampered_or_missing_evidence_never_completes(self):
  for key in self.evidence:
   bad={k:dict(v) for k,v in self.evidence.items()};bad[key]['sha256']='0'*64
   with self.subTest(key=key),self.assertRaises(ValueError):c.finish(self.p,'full-a','r1',bad)
  self.assertFalse((self.p/'full-a.complete.json').exists())
 def test_wrong_lineage_and_symlink_rejected(self):
  with self.assertRaises(ValueError):c.finish(self.p,'full-a','r2',self.evidence)
  (self.p/'cleanup.json').unlink();(self.p/'cleanup.json').symlink_to('/dev/null')
  with self.assertRaises(ValueError):c.finish(self.p,'full-a','r1',self.evidence)
  self.assertFalse((self.p/'full-a.complete.json').exists())
 def test_unclean_shutdown_refused(self):
  p=self.p/'cleanup.json';v=json.loads(p.read_text());v['verified_dead']=False;raw=json.dumps(v).encode();p.write_bytes(raw);self.evidence['cleanup']['sha256']=hashlib.sha256(raw).hexdigest()
  with self.assertRaises(ValueError):c.finish(self.p,'full-a','r1',self.evidence)
 def test_bare_clock_or_trace_metadata_refused(self):
  for key in ('clock_before','clock_after','trace_manifest'):
   p=self.p/(key+'.json');original=p.read_bytes();raw=json.dumps({'window':'full-a','run_id':'r1'}).encode();p.write_bytes(raw)
   self.evidence[key]['sha256']=hashlib.sha256(raw).hexdigest()
   with self.assertRaises(ValueError):c.finish(self.p,'full-a','r1',self.evidence)
   p.write_bytes(original);self.evidence[key]['sha256']=hashlib.sha256(original).hexdigest()
 def test_nested_raw_tamper_refused(self):
  (self.p/'clock_before.raw.json').write_text('{}')
  with self.assertRaises(ValueError):c.finish(self.p,'full-a','r1',self.evidence)
 def test_partial_marker_remains_terminal(self):
  (self.p/'full-a.complete.json').write_text('{')
  with self.assertRaises(FileExistsError):c.finish(self.p,'full-a','r1',self.evidence)
  with self.assertRaises(ValueError):c.begin(self.p,'mask-a','r1',c.validate_prior)
if __name__=='__main__':unittest.main()
