import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from protocol_runner import run_sequence

class ProtocolTests(unittest.TestCase):
    def fixtures(self):
        warm=[{'text':'private-one'}, {'text':'private-two'}]
        data=[]
        for i in range(48):
            body={'n':i, 'speculative.n_max':0 if i%2 else 4}
            digest=hashlib.sha256(json.dumps(body).encode()).hexdigest()
            data.append((f't{i}',body,digest))
        return warm,[hashlib.sha256(json.dumps(x).encode()).hexdigest() for x in warm],data
    def test_order_events_no_private_bodies(self):
        warm,warm_expected,rows=self.fixtures()
        def fake(_port,tag,body,digest,*_):
            self.assertEqual(digest,hashlib.sha256(json.dumps(body).encode()).hexdigest())
            return {'tag':tag,'body_sha256':digest,'completed':True,'http_status':200,'prompt_n':130,'predicted_n':3}
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'events.jsonl'; out=run_sequence(1,warm,warm_expected,rows,fake,threading.Event(),threading.Event(),99999999999,p,lambda:None)
            events=[json.loads(s) for s in p.read_text().splitlines()]
            self.assertEqual(len(out['rows']),48)
            self.assertEqual([e['kind'] for e in events], ['warm_complete']*2+['t7a_started']+['t7a_request_complete']*48+['t7a_completed'])
            self.assertNotIn('private-',p.read_text())
    def test_incomplete_records_progress(self):
        warm,warm_expected,rows=self.fixtures();calls=[]
        def fake(_port,tag,body,digest,*_):
            calls.append(tag)
            if len(calls)==6: raise RuntimeError('test')
            return {'tag':tag,'body_sha256':digest,'completed':True,'http_status':200}
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'events.jsonl'
            with self.assertRaises(RuntimeError):run_sequence(1,warm,warm_expected,rows,fake,None,None,0,p,lambda:None)
            last=json.loads(p.read_text().splitlines()[-1]);self.assertEqual(last['kind'],'protocol_incomplete');self.assertEqual(last['completed_t7a_requests'],3)
    def test_refused_exposure_guard_never_sends_target(self):
        warm,warm_expected,rows=self.fixtures();calls=[]
        def fake(_port,tag,body,digest,*_):
            calls.append(tag);return {'tag':tag,'body_sha256':digest,'completed':True,'http_status':200}
        def guard():raise RuntimeError('prior exposure')
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(RuntimeError):
                run_sequence(1,warm,warm_expected,rows,fake,None,None,0,Path(td)/'e',guard)
        self.assertEqual(calls,['warm-0','warm-1'])
    def test_duplicate_predeclared_identity_refused_before_send(self):
        warm,warm_expected,rows=self.fixtures();rows[-1]=rows[0]
        with self.assertRaises(ValueError):run_sequence(1,warm,warm_expected,rows,None,None,None,0,'/no/such/path',lambda:None)

if __name__=='__main__':unittest.main()
