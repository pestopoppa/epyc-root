"""Model-free exercise of the actual disabled candidate cancellation entry."""
import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import TestCase, main
from unittest.mock import patch

BASE = Path('/mnt/raid0/llm/tmp/kvu/kpf18-integrated-successor-20261104/candidate')
MODULE = BASE/'vendor/cancel_seed_transport.py'
PIN = '95ea82faece95847abceb3eab1c36b52bcd244faa4db5477ec6983f0bf4f513f'
sys.path[:0] = [str(BASE/'vendor'), str(BASE), str(BASE/'research/scripts/benchmark/kpf18')]
if hashlib.sha256(MODULE.read_bytes()).hexdigest() != PIN:
    raise RuntimeError('candidate transport changed')
spec = importlib.util.spec_from_file_location('actual_seed_transport', MODULE)
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)

class Abort(Exception):
    pass

class Deadline:
    def remaining(self): return 10

class Ledger:
    def __init__(self): self.entries=[]
    def add(self, entry): self.entries.append(entry)

class Response:
    status = 200
    def __init__(self):
        event={'id_slot':-1,'prompt_progress':{'total':32512,'processed':31744}}
        self.lines=[b'data: '+json.dumps(event).encode()+b'\n', b'']
    def readline(self): return self.lines.pop(0)
    def close(self): pass

class Sock:
    def setsockopt(self,*args): pass
    def shutdown(self,*args): pass

class Connection:
    def __init__(self, logs): self.sock=Sock();self.logs=logs
    def request(self,*args,**kwargs): pass
    def getresponse(self): return Response()
    def close(self): self.logs.write_text(self.logs_text)
    logs_text=''

class NativeCancel(TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.log=self.root/'server.log';self.log.write_text('')
        self.ledger=Ledger()
        self.proc=NS(pid=42,poll=lambda:None)
        self.server=NS(proc=self.proc,log=self.log)
        self.empty={'id':1,'is_processing':False,'n_prompt_tokens':0,'kv_cells':{'private':0}}
        self.running={'id':1,'is_processing':True,'id_task':42}
        self.after={'id':1,'is_processing':False,'id_task':42,'n_prompt_tokens':32000}
        self.slots=[self.empty,self.running,self.after]
        def get_slots(): return [self.slots.pop(0) if len(self.slots)>1 else self.slots[0]]
        self.ctx=NS(check_boundary=lambda:None,client=NS(base='http://127.0.0.1:1234',slots=get_slots),
                    args=NS(port=1234),out=self.root,deadline=Deadline())
        self.gate=NS(Abort=Abort,body_for=lambda *a,**k:{},
                     sha256_file=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest(),
                     write_json=lambda p,v:Path(p).write_text(json.dumps(v)))

    def invoke(self, logs, clock):
        connection=Connection(self.log);connection.logs_text=logs
        real_capture=transport.capture
        def capture(**kwargs): return real_capture(**kwargs,sleep=lambda _:None,clock=lambda:0)
        with patch.object(transport,'pid_owns_port',return_value=True), \
             patch.object(transport.http.client,'HTTPConnection',return_value=connection), \
             patch.object(transport,'capture',side_effect=capture), \
             patch.object(transport.time,'monotonic',side_effect=clock), \
             patch.object(transport.time,'sleep',return_value=None):
            return transport.SeedControl()(gate=self.gate,ctx=self.ctx,R=NS(rows=self.ledger),
                  srv=self.server,slot=1,source_ids=[0]*32512,checkpoint=32000,
                  n_predict=256,control=1,attempt=1)

    def test_close_plus_matching_native_release_yields_scoped_witness(self):
        logs=('slot launch_slot_: id 1 | task 42 | processing task, is_child = 0\n'
              'cancel task, id_task = 42\n'
              'slot release: id 1 | task 42 | stop processing: n_tokens = 32000, truncated = 0\n')
        result=self.invoke(logs,[0,1,2])
        self.assertTrue(result['observed_cancel_task'])
        self.assertEqual(result['seed_task_id'],42)
        self.assertEqual(len(self.ledger.entries),1)
        record=json.loads(Path(result['raw_record_path']).read_text())
        self.assertFalse(record['native_geometry_admitted'])
        self.assertTrue(record['native_task_witness']['native_release_observed'])

    def test_idle_without_native_release_is_not_cancel_witness(self):
        result=self.invoke('',[0,1,2,5])
        self.assertFalse(result['observed_cancel_task'])
        record=json.loads(Path(result['raw_record_path']).read_text())
        self.assertIsNone(record['native_task_witness'])
        self.assertIn('absent/ambiguous',record['native_refusal'])

    def test_foreign_idle_task_is_never_release_ack(self):
        self.after['id_task']=43
        with self.assertRaisesRegex(Abort,'did not become idle'):
            self.invoke('',[0,1,12])
        self.assertEqual(self.ledger.entries,[])
        record=json.loads((self.root/'construction/Cmask1-attempt1/seed.json').read_text())
        self.assertEqual(record['refusal'],'native cancellation not acknowledged')

if __name__ == '__main__': main()
