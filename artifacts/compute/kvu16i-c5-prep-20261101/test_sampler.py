import json
from pathlib import Path
import tempfile
import threading
import unittest
import sampler

class SamplerTests(unittest.TestCase):
    def test_ceilings(self):
        self.assertIsNone(sampler.ceiling({'own_vram_b':0,'card_used_b':0}))
        self.assertEqual('soft',sampler.ceiling({'own_vram_b':sampler.SOFT+1,'card_used_b':0}))
        self.assertEqual('hard',sampler.ceiling({'own_vram_b':0,'card_used_b':sampler.HARD+1}))
    def test_actual_sampling_and_sticky_abort(self):
        with tempfile.TemporaryDirectory() as d:
            calls=[]
            def fake(pid,birth,hip):
                calls.append(1)
                return {'t':len(calls),'own_vram_b':sampler.SOFT+1,'card_used_b':0}
            p=Path(d)/'samples.jsonl'; s=sampler.Sampler(2,3,'/x',p,.001,fake).start()
            self.assertTrue(s.abort.wait(1)); self.assertTrue(s.stop()); self.assertEqual(len(p.read_text().splitlines()),1)
            self.assertEqual(json.loads(p.read_text())['own_vram_b'],sampler.SOFT+1)
    def test_reader_failure_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            def fake(*a): raise OSError('unreadable KFD')
            s=sampler.Sampler(2,3,'/x',Path(d)/'s',.001,fake).start();self.assertTrue(s.abort.wait(1));self.assertTrue(s.stop())
            self.assertIn('sampler refusal',s.reason)
    def test_pid_reuse_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); proc=root/'proc/42'; proc.mkdir(parents=True)
            (proc/'stat').write_text('42 (test proc) S ' + ' '.join(['0']*18 + ['123'] + ['0']*5))
            with self.assertRaisesRegex(RuntimeError,'identity changed'):
                sampler.read_sample(42,124,'/hip',root/'proc',root/'kfd',root/'card')

if __name__=='__main__':unittest.main()
