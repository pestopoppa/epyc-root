import hashlib
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import producer

class Monitor:
    def __init__(self,_pid,_birth,_hip,path,**kw):
        self.path=Path(path);self.abort=threading.Event();self.reason=None
    def start(self):
        now=time.monotonic()
        self.path.write_text(''.join(json.dumps({'t':now+i*.01,'phase':'load','own_vram_b':100,'hip_resident':True,'gpu_id':1,'gpu_unique_id':2,'gpu_bdf':'fixture'})+'\n' for i in range(2)))
        return self
    def stop(self):return True

class FakeServer:
    def __init__(self,sink):self.sink=sink;self.closed=False
    def start(self):return 123,456
    def alive(self):return True
    def close(self):
        assert not self.sink.exists(), 'qualification unit published before process drain'
        self.closed=True;return {'captured':True,'verified_dead':True}

class ProducerTests(unittest.TestCase):
    def test_qualification_never_loads_target_and_emits_after_cleanup(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); (d/'PLAN.json').write_text('{}');(d/'SOURCE-SHA256SUMS').write_text('source');(d/'RUNTIME-INPUTS.sha256').write_text('runtime');proof=d/'proof';proof.write_text('proof');grant=d/'grant';grant.write_text('fixture')
            run=d/'run';run.mkdir(); sink=d/'events';server=FakeServer(sink)
            def transport(_port,tag,body,digest,*_):
                self.assertEqual(tag,'qualification-control')
                self.assertEqual(hashlib.sha256(json.dumps(body).encode()).hexdigest(),digest)
                return {'tag':tag,'body_sha256':digest,'completed':True,'http_status':200,
                        'predicted_n':32,'draft_n':8,'draft_n_accepted':4}
            with patch.dict(producer.os.environ,{'KVU16I_PIN_PROOF':str(proof)}), patch.object(producer,'D',d), patch.object(producer.t7a_protocol,'verified_t7a_bodies',side_effect=AssertionError('target read')), patch.object(producer.warmup_protocol,'bodies',side_effect=AssertionError('warmup read')):
                result=producer.run_session(raw_mode='1',stop=threading.Event(),deadline=time.monotonic()+30,
                    event_sink=sink,exposure=d/'exposed',grant_path=grant,run_dir=run,server=server,
                    sampler_factory=Monitor,transport=transport,device={'gpu_id':1,'unique_id':2,'bdf':'fixture'},wait_health=lambda _:True,nap=lambda _:None)
            self.assertTrue(server.closed);self.assertEqual(result['verdict'],'CONTROL_COMPLETE')
            self.assertEqual(json.loads(sink.read_text())['kind'],'qualification_complete')
            self.assertTrue((run/'native-receipt.json').exists());self.assertFalse((d/'exposed').exists())
    def test_qualification_failure_has_no_rowflow_unit(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);(d/'PLAN.json').write_text('{}');(d/'SOURCE-SHA256SUMS').write_text('source');(d/'RUNTIME-INPUTS.sha256').write_text('runtime');proof=d/'proof';proof.write_text('proof');grant=d/'grant';grant.write_text('fixture')
            run=d/'run';run.mkdir();sink=d/'events';server=FakeServer(sink)
            def bad(*_):raise RuntimeError('control failure')
            with patch.dict(producer.os.environ,{'KVU16I_PIN_PROOF':str(proof)}), patch.object(producer,'D',d):
                result=producer.run_session(raw_mode='1',stop=threading.Event(),deadline=time.monotonic()+30,
                    event_sink=sink,exposure=d/'exposed',grant_path=grant,run_dir=run,server=server,
                    sampler_factory=Monitor,transport=bad,device={'gpu_id':1,'unique_id':2,'bdf':'fixture'},wait_health=lambda _:True,nap=lambda _:None)
            self.assertEqual(result['verdict'],'UNKNOWN');self.assertTrue(server.closed);self.assertFalse(sink.exists())
            self.assertTrue(json.loads((run/'native-receipt.json').read_text())['partial'])
    def test_prior_exposure_refuses_before_server(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);exp=d/'exposed';exp.write_text('{}');server=FakeServer(d/'events')
            with self.assertRaisesRegex(RuntimeError,'no redraw'):
                producer.run_session(raw_mode='0',stop=threading.Event(),deadline=time.monotonic()+30,
                    event_sink=d/'events',exposure=exp,grant_path=d/'unused',run_dir=d,server=server,
                    sampler_factory=Monitor,transport=None,device={'gpu_id':1,'unique_id':2,'bdf':'fixture'},wait_health=lambda _:True)
            self.assertFalse(server.closed)
    def test_incomplete_last_sample_line_is_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'samples';p.write_bytes(b'{"t":1}\n{"t"')
            self.assertEqual(producer.sample_rows(p),[{'t':1}])
if __name__=='__main__':unittest.main()
