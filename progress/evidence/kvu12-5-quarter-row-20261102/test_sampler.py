import json,tempfile,unittest
from pathlib import Path
from sampler import Monitor
class SamplerTest(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name);p=self.root/'class/drm/card0/device';p.mkdir(parents=True);(p/'vendor').write_text('0x1002');(p/'device').write_text('0x740f');(p/'gpu_busy_percent').write_text('0');(self.root/'class/kfd/kfd/proc').mkdir(parents=True)
 def test_zero_vram_pid_invalid(self):
  m=Monitor(self.root/'samples',sysroot=self.root);m.sample();(self.root/'class/kfd/kfd/proc/123').mkdir();m.sample();self.assertFalse(m.quiet(m.samples[0]['ts_ns'],m.samples[-1]['ts_ns']))
 def test_nonzero_busy_invalid(self):
  m=Monitor(self.root/'samples',sysroot=self.root);m.sample();(self.root/'class/drm/card0/device/gpu_busy_percent').write_text('1');m.sample();self.assertFalse(m.quiet(m.samples[0]['ts_ns'],m.samples[-1]['ts_ns']))
 def test_large_sampling_gap_invalid(self):
  m=Monitor(self.root/'samples',sysroot=self.root);m.sample();m.sample();m.samples[1]['ts_ns']=m.samples[0]['ts_ns']+3_000_000_001;self.assertFalse(m.quiet(m.samples[0]['ts_ns'],m.samples[-1]['ts_ns']))
 def test_zero_observations_bracket(self):
  m=Monitor(self.root/'samples',sysroot=self.root);m.sample();m.sample();self.assertTrue(m.quiet(m.samples[0]['ts_ns'],m.samples[-1]['ts_ns']))
if __name__=='__main__':unittest.main()
