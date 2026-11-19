import json, tempfile, unittest
from pathlib import Path
import clock_witness as c

class Clock(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.p=Path(self.temp.name)
  self.producer=self.p/'fake.py'
  self.producer.write_text('''import json, os, sys, time\ntime.sleep(.05)\nb=time.clock_gettime_ns(time.CLOCK_MONOTONIC)\na=time.clock_gettime_ns(time.CLOCK_MONOTONIC)\nrows=[dict(host_before_ns=b,hsa_ticks=5,host_after_ns=a),dict(host_before_ns=b,hsa_ticks=6,host_after_ns=a)]\nopen(sys.argv[sys.argv.index("--out")+1],"w").write(json.dumps(dict(schema="epyc.kpf50.hsa-clock.v1",frequency_hz=1000,samples=rows,pid=os.getpid())))\n''')
  self.sha=c.digest(self.producer)
 def test_capture_native_samples_and_binding(self):
  x=c.capture(self.p,'full-a','r1','clock_before',self.producer,self.sha)
  self.assertEqual(x['schema'],'kpf50.clock-sample.v1');self.assertEqual(x['phase'],'clock_before')
  self.assertEqual(len(json.loads((self.p/x['native_file']).read_text())['samples']),2)
  with self.assertRaises(FileExistsError):c.capture(self.p,'full-a','r1','clock_before',self.producer,self.sha)
 def test_bad_pin_never_runs(self):
  with self.assertRaises(ValueError):c.capture(self.p,'full-a','r1','clock_before',self.producer,'0'*64)
 def test_bad_native_rows_refused(self):
  x={'schema':'epyc.kpf50.hsa-clock.v1','pid':1,'frequency_hz':100,'samples':[{'host_before_ns':1,'hsa_ticks':4,'host_after_ns':2},{'host_before_ns':2,'hsa_ticks':3,'host_after_ns':3}]}
  with self.assertRaises(ValueError):c.validate(json.dumps(x),1,0,4)
  x['samples'][1]['hsa_ticks']=5
  with self.assertRaises(ValueError):c.validate(json.dumps(x),2,0,4)
  with self.assertRaises(ValueError):c.validate(json.dumps(x),1,2,4)
 def test_missing_and_failing_producer(self):
  self.producer.write_text('raise SystemExit(2)\n'); sha=c.digest(self.producer)
  with self.assertRaises((RuntimeError,ValueError)):c.capture(self.p,'full-a','r1','clock_after',self.producer,sha)
  self.assertFalse((self.p/'full-a.clock_after.json').exists())
if __name__=='__main__':unittest.main()
