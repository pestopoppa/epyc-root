import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock
import producer

class FakeServer:
    last=None
    def __init__(self,cmd,env,log,pidfile):
        self.cmd=cmd;self.closed=False;FakeServer.last=self
        Path(log).write_text('llama_kv_cache: size = 13056.00 MiB (393216 cells, 16 layers, 4/1 seqs), K (q8_0): 6528 MiB\n')
    def start(self):return 123,456
    def alive(self):return True
    def close(self):self.closed=True;return {'verified_dead':True}
class Flag:
    def is_set(self):return False
class FakeSampler:
    def __init__(self,*a,**kw):self.abort=Flag();self.i=0
    def start(self):return self
    @property
    def last(self):
        self.i+=1
        return {'t':time.monotonic()+self.i,'hip_resident':True,'own_vram_b':int(50*2**30)}
    def stop(self):return True
class Tests(unittest.TestCase):
    def test_native_smoke_result_after_residency_and_cleanup(self):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as td:
            root=Path(td);native=root/'native.json'
            (root/'model-receipt.json').write_text('{}');(root/'linkage-1.txt').write_text('PASS')
            env={'FILLER_NEEDGPU':'1','FILLER_DRYRUN':'1','FILLER_DRYRUN_RESULT_PATH':str(native),
                 'FILLER_PIDFILE':str(root/'pid'),'FILLER_STOPFILE':str(root/'stop'),
                 'FILLER_DEADLINE':str(int(time.time())+90)}
            with mock.patch.dict(os.environ,env,clear=True), mock.patch.object(producer,'D',root), \
                 mock.patch.object(producer.device_identity,'discover',return_value={}), \
                 mock.patch.object(producer.server_lifecycle,'Server',FakeServer), \
                 mock.patch.object(producer.sampler,'Sampler',FakeSampler), \
                 mock.patch.object(producer,'healthy',return_value=True), mock.patch.object(producer.time,'sleep'):
                self.assertEqual(producer.main(),0)
            r=json.loads(native.read_text())
            self.assertTrue(FakeServer.last.closed);self.assertEqual(r['healthy_sample_count'],2)
            self.assertEqual(r['mode'],'qualification');self.assertEqual(r['non_kv_gib'],37.25)
            self.assertEqual(r['argv'][r['argv'].index('-ub')+1],'512')
            self.assertFalse((root/'result.json').exists())
    def test_missing_or_wrong_kv_shape_refused(self):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as d:
            log=Path(d)/'log';log.write_text('llama_kv_cache: size = 1 MiB (10 cells)')
            with self.assertRaisesRegex(RuntimeError,'shape-matched'):producer.target_kv_gib(log)
    def test_missing_gpu_refuses_before_server(self):
        with mock.patch.dict(os.environ,{'FILLER_NEEDGPU':'0'},clear=True), \
             mock.patch.object(producer.server_lifecycle,'Server') as server:
            with self.assertRaisesRegex(RuntimeError,'GPU grant'):producer.main()
            server.assert_not_called()
if __name__=='__main__':unittest.main()
