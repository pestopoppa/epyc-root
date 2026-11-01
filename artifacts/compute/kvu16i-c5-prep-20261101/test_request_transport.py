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
    def test_stopped_never_starts(self):
        self.stop.set()
        with self.assertRaises(T.RequestInterrupted):T.execute(100,'x',self.body,self.hash,self.stop,self.abort,time.monotonic()+10,connection_factory=Connection)
    def test_wrong_hash_never_starts(self):
        with self.assertRaises(ValueError):T.execute(100,'x',self.body,'wrong',self.stop,self.abort,time.monotonic()+10,connection_factory=Connection)
if __name__=='__main__':unittest.main()
