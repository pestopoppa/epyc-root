import ast
import hashlib
import json
import os
from pathlib import Path
import socket
import threading
import time
from types import SimpleNamespace as NS
import unittest
import cancel_seed_transport as transport
from slots_transport import bounded_slots

RESULTS=[]
class Abort(RuntimeError):pass
class Stop(RuntimeError):pass
class Peer:
    def __init__(self,mode,payload=b'[{"id":1,"is_processing":true}]'):
        self.mode,self.payload=mode,payload
        self.socket=socket.socket();self.socket.bind(('127.0.0.1',0));self.socket.listen(1);self.socket.settimeout(1)
        self.port=self.socket.getsockname()[1];self.done=threading.Event();self.request=None
        self.thread=threading.Thread(target=self.serve);self.thread.start()
    def serve(self):
        try:
            conn,_=self.socket.accept()
            with conn:
                conn.settimeout(1);self.request=conn.recv(4096)
                if self.mode=='headers':self.done.wait(.8);return
                conn.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: '+str(len(self.payload)).encode()+b'\r\nConnection: close\r\n\r\n')
                if self.mode=='body':self.done.wait(.8);return
                if self.mode=='trickle':
                    for byte in self.payload:
                        if self.done.wait(.025):break
                        conn.sendall(bytes([byte]))
                else:conn.sendall(self.payload)
        except (OSError,TimeoutError):pass
    def close(self):
        self.done.set();self.thread.join(2);self.socket.close()
        if self.thread.is_alive():raise RuntimeError('peer not joined')

def context(peer,budget=.15,stop_after=None):
    started=time.monotonic()
    def boundary():
        if stop_after is not None and time.monotonic()-started>=stop_after:raise Stop('fixture STOP')
    def forbidden():raise AssertionError('unbounded client.slots used')
    return NS(check_boundary=boundary,client=NS(base=f'http://127.0.0.1:{peer.port}',slots=forbidden),args=NS(port=peer.port),deadline=NS(remaining=lambda:budget))

class Slots(unittest.TestCase):
    def actual(self,mode,exception,budget=.15,stop_after=None):
        peer=Peer(mode);ctx=context(peer,budget,stop_after);before=time.monotonic()
        try:
            with self.assertRaises(exception) as caught:
                transport.SeedControl()(gate=NS(Abort=Abort),ctx=ctx,R=None,srv=NS(proc=NS(pid=os.getpid(),poll=lambda:None)),slot=1,source_ids=[0]*32512,checkpoint=32000,n_predict=256,control=1,attempt=1)
            elapsed=time.monotonic()-before
            self.assertLess(elapsed,.7)
            self.assertTrue(peer.request.startswith(b'GET /slots HTTP/1.1\r\n'))
            if mode=='success':self.assertIn('not independently empty',str(caught.exception))
            RESULTS.append({'entry':'SeedControl.__call__','case':mode+('-STOP' if stop_after else ''),'exception':type(caught.exception).__name__,'elapsed_s':elapsed,'request_sha256':hashlib.sha256(peer.request).hexdigest()})
        finally:peer.close()
    def test_actual_success(self):self.actual('success',Abort)
    def test_actual_stalled_headers(self):self.actual('headers',TimeoutError)
    def test_actual_stalled_body(self):self.actual('body',TimeoutError)
    def test_actual_continuous_trickle(self):self.actual('trickle',TimeoutError)
    def test_actual_stop_during_headers(self):self.actual('headers',Stop,budget=.6,stop_after=.05)
    def test_actual_stop_during_body(self):self.actual('body',Stop,budget=.6,stop_after=.05)
    def test_local_deadline(self):
        peer=Peer('headers')
        try:
            with self.assertRaises(TimeoutError):bounded_slots(context(peer,budget=.6),deadline=time.monotonic()+.1)
        finally:peer.close()
    def test_exhausted_deadline_no_request(self):
        peer=Peer('success')
        try:
            with self.assertRaises(TimeoutError):bounded_slots(context(peer,budget=0))
            self.assertIsNone(peer.request)
        finally:peer.close()
    def test_payload_refusals_and_preservation(self):
        for payload in (b'{}',b'[{"id":1},{"id":1}]',b'[{"id":true}]',b'bad',b'x'*1048577):
            peer=Peer('success',payload)
            try:
                with self.assertRaises(ValueError):bounded_slots(context(peer,budget=.6))
            finally:peer.close()
        expected=[{'id':1,'id_task':9,'is_processing':False,'kv_cells':{'private':12},'extra':'unchanged'}]
        peer=Peer('success',json.dumps(expected).encode())
        try:self.assertEqual(bounded_slots(context(peer,budget=.6)),expected)
        finally:peer.close()
    def test_all_three_actual_calls_bound(self):
        tree=ast.parse(Path(transport.__file__).read_text())
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='bounded_slots']
        self.assertEqual(len(calls),3)
        self.assertEqual(sum(any(k.arg=='deadline' and isinstance(k.value,ast.Name) and k.value.id=='until' for k in n.keywords) for n in calls),1)
        self.assertNotIn('ctx.client.slots()',Path(transport.__file__).read_text())
    def test_watchdog_threads_joined(self):
        self.assertFalse(any(t.name.endswith('(watch)') for t in threading.enumerate()))

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Slots)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    out=Path(os.environ.get('SLOTS_RESULT','RESULT.json'))
    out.parent.mkdir(parents=True,exist_ok=True)
    data={'schema':'kpf18.slots-transport-qualification.v1','status':'PASS' if result.wasSuccessful() else 'FAIL','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'observations':RESULTS,'scope':'three isolated SeedControl slots calls only; model-free; no native cancellation or full-candidate claim','inputs':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}}
    temp=out.with_suffix('.tmp');temp.write_text(json.dumps(data,indent=2)+'\n');temp.replace(out)
    raise SystemExit(0 if result.wasSuccessful() else 1)
