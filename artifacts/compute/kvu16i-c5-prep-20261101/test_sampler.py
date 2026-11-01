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
    def test_startup_zero_then_residency_then_kfd_loss_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            calls=[]
            def fake(pid,birth,hip,allow_uninitialized=False):
                calls.append(allow_uninitialized)
                if len(calls)==1:
                    return {'t':1,'own_vram_b':0,'card_used_b':0,'hip_resident':False}
                if len(calls)==2:
                    return {'t':2,'own_vram_b':1,'card_used_b':1,'hip_resident':True}
                raise OSError('KFD disappeared')
            out=Path(d)/'s';s=sampler.Sampler(2,3,'/x',out,.001,fake,startup=True,phase=lambda:'load').start()
            self.assertTrue(s.abort.wait(1));self.assertTrue(s.stop())
            self.assertEqual(calls,[True,True,False]);self.assertTrue(s.residency_seen)
            records=[json.loads(line) for line in out.read_text().splitlines()]
            self.assertEqual([x['phase'] for x in records],['load','load'])
            self.assertEqual(records[0]['own_vram_b'],0)
    def test_pid_reuse_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); proc=root/'proc/42'; proc.mkdir(parents=True)
            (proc/'stat').write_text('42 (test proc) S ' + ' '.join(['0']*18 + ['123'] + ['0']*5))
            with self.assertRaisesRegex(RuntimeError,'identity changed'):
                sampler.read_sample(42,124,'/hip',root/'proc',root/'kfd',root/'card')

if __name__=='__main__':unittest.main()
