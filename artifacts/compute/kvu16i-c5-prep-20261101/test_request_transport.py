import hashlib
import json
import threading
import time
import unittest
import request_transport as T

class Response:
    status=200
    def read(self):return b'fixture'
class Connection:
    def __init__(self,*a,**k):self.sock=None
    def request(self,*a,**k):pass
    def getresponse(self):return Response()
    def close(self):pass
class TestTransport(unittest.TestCase):
    def setUp(self):
        self.stop=threading.Event();self.abort=threading.Event();self.body={'prompt':'fixture'}
        self.hash=hashlib.sha256(json.dumps(self.body).encode()).hexdigest()
    def test_completed_request_does_not_invent_trigger(self):
        r=T.execute(100,'x',self.body,self.hash,self.stop,self.abort,time.monotonic()+10,connection_factory=Connection)
        self.assertEqual(r['http_status'],200);self.assertIsNone(r['trigger_observed'])
    def test_native_timing_counters_recorded_without_response_text(self):
        class JsonResponse:
            status=200
            def read(self):
                return b'{"timings":{"prompt_n":130,"predicted_n":3,"cache_n":0,"draft_n":7,"draft_n_accepted":2},"choices":[{"text":"private"}]}'
        class JsonConnection(Connection):
            def getresponse(self): return JsonResponse()
        r=T.execute(100,'x',self.body,self.hash,self.stop,self.abort,time.monotonic()+10,connection_factory=JsonConnection)
        self.assertEqual((r['prompt_n'],r['predicted_n'],r['cache_n'],r['draft_n']), (130,3,0,7))
        self.assertNotIn('private', str(r));self.assertIsNone(r['trigger_observed'])
    def test_invalid_native_counter_remains_unknown(self):
        class BadResponse:
            status=200
            def read(self): return b'{"timings":{"prompt_n":true,"predicted_n":-1}}'
        class BadConnection(Connection):
            def getresponse(self): return BadResponse()
        r=T.execute(100,'x',self.body,self.hash,self.stop,self.abort,time.monotonic()+10,connection_factory=BadConnection)
        self.assertIsNone(r['prompt_n']); self.assertIsNone(r['predicted_n'])
    def test_stopped_never_starts(self):
        self.stop.set()
        with self.assertRaises(T.RequestInterrupted):T.execute(100,'x',self.body,self.hash,self.stop,self.abort,time.monotonic()+10,connection_factory=Connection)
    def test_wrong_hash_never_starts(self):
        with self.assertRaises(ValueError):T.execute(100,'x',self.body,'wrong',self.stop,self.abort,time.monotonic()+10,connection_factory=Connection)
if __name__=='__main__':unittest.main()
