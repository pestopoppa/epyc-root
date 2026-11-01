import hashlib
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from mode_controller import execute, mode

class ModeControllerTests(unittest.TestCase):
    def test_invalid_modes_refuse(self):
        for value in (None,'','yes','2'):
            with self.assertRaises(ValueError): mode(value)
    def test_qualification_never_runs_full(self):
        def fake(port,tag,body,digest,*_):
            self.assertEqual(hashlib.sha256(json.dumps(body).encode()).hexdigest(),digest)
            return {'tag':tag,'body_sha256':digest,'completed':True,'http_status':200,'predicted_n':32,'draft_n':8,'draft_n_accepted':4}
        def forbidden(): raise AssertionError('target work exposed in qualification')
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'events'; r=execute('1',123,threading.Event(),threading.Event(),time.monotonic()+10,out,transport=fake,run_full=forbidden)
            self.assertEqual(r['mode'],'qualification')
            self.assertFalse(out.exists())  # owner emits first unit after cleanup
    def test_missing_draft_counter_refuses_without_unit(self):
        def fake(port,tag,body,digest,*_):
            return {'tag':tag,'body_sha256':digest,'completed':True,'http_status':200,'predicted_n':32}
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'events'
            with self.assertRaises(RuntimeError):execute('1',1,threading.Event(),threading.Event(),time.monotonic()+10,out,transport=fake,run_full=lambda:None)
            self.assertFalse(out.exists())
    def test_missing_counter_refuses_without_unit(self):
        def fake(*_): return {'tag':'qualification-control','body_sha256':'bad','completed':True,'http_status':200}
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'events'
            with self.assertRaises(RuntimeError):execute('1',1,threading.Event(),threading.Event(),time.monotonic()+10,out,transport=fake,run_full=lambda:None)
            self.assertFalse(out.exists())
    def test_full_only_when_requested(self):
        self.assertEqual(execute('0',1,threading.Event(),threading.Event(),time.monotonic()+10,'/unused',transport=None,run_full=lambda:'full-called'),'full-called')
    def test_stop_prevents_both_paths(self):
        e=threading.Event();e.set()
        for v in ('0','1'):
            with self.assertRaises(RuntimeError):execute(v,1,e,threading.Event(),time.monotonic()+10,'/unused',transport=None,run_full=None)
if __name__=='__main__':unittest.main()
