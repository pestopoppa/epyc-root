import pathlib, tempfile, unittest, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "native"))
from unittest.mock import patch
from types import SimpleNamespace
from ring_archive import RingArchive, verify

class CompactIntegration(unittest.TestCase):
    def test_exact_terminal_source_set_and_replay(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d)/'rings'; a=RingArchive(p,max_bytes=10000)
            a.append(1, bytes(64), head=0, tail=0)
            a.append(1, bytes(64), head=0, tail=0, terminal=True)
            a.append(2, bytes(64), head=0, tail=0, terminal=True)
            receipt=a.finish()
            prov={1:{'cpu':0,'tracepoint_id':1},2:{'cpu':1,'tracepoint_id':2}}
            self.assertEqual(verify(p,receipt,max_bytes=10000,expected_sources={1,2},source_provenance=prov,expected_terminals={1:(0,0),2:(0,0)}),receipt)
            with self.assertRaises(ValueError): verify(p,receipt,max_bytes=10000,expected_sources={1,2},expected_terminals={1:(1,0),2:(0,0)})
            with self.assertRaises(ValueError): verify(p,receipt,max_bytes=10000,expected_sources={1,2,3})
    def test_missing_or_duplicated_terminal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'rings';a=RingArchive(p,max_bytes=10000)
            a.append(1,bytes(64),head=0,tail=0)
            receipt=a.finish()
            with self.assertRaises(ValueError):verify(p,receipt,max_bytes=10000,expected_sources={1})
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'rings';a=RingArchive(p,max_bytes=10000)
            a.append(1,bytes(64),head=0,tail=0,terminal=True)
            a.append(1,bytes(64),head=0,tail=0,terminal=True)
            receipt=a.finish()
            with self.assertRaises(ValueError):verify(p,receipt,max_bytes=10000,expected_sources={1})
    def test_worker_failure_cleans_owned_archive(self):
        import capture_worker
        fake=SimpleNamespace(receiver=SimpleNamespace(nonce='n'),abort=lambda:None)
        closed=[]
        class Sock:
            def close(self): closed.append(True)
        with tempfile.TemporaryDirectory() as d:
            out=str(pathlib.Path(d)/'result')
            argv=['--control-fd','3','--marker-fd','4','--owner-pid','1','--owner-uid','1','--target-pid','1','--cpus','0','--output',out]
            with patch.object(capture_worker.socket,'socket',side_effect=lambda **kw:Sock()), patch.object(capture_worker,'build_capture',return_value=fake), patch.object(capture_worker,'_send'), patch.object(capture_worker,'serve',side_effect=RuntimeError('fault')):
                with self.assertRaises(RuntimeError): capture_worker.main(argv)
            self.assertFalse(pathlib.Path(out+'.rings').exists()); self.assertFalse(pathlib.Path(out).exists()); self.assertEqual(len(closed),2)
    def test_worker_failure_after_archive_finish_cleans_archive(self):
        import capture_worker
        class Sock:
            def close(self): pass
        class Fake:
            receiver=SimpleNamespace(nonce='n')
            def abort(self): raise RuntimeError('abort fault')
        def build(marker, **kw):
            kw['archive'].append(1,bytes(64),head=0,tail=0,terminal=True); kw['archive'].finish(); return Fake()
        with tempfile.TemporaryDirectory() as d:
            out=str(pathlib.Path(d)/'result'); argv=['--control-fd','3','--marker-fd','4','--owner-pid','1','--owner-uid','1','--target-pid','1','--cpus','0','--output',out]
            with patch.object(capture_worker.socket,'socket',side_effect=lambda **kw:Sock()), patch.object(capture_worker,'build_capture',side_effect=build), patch.object(capture_worker,'_send'), patch.object(capture_worker,'serve',side_effect=RuntimeError('fault')):
                with self.assertRaises(RuntimeError): capture_worker.main(argv)
            self.assertFalse(pathlib.Path(out+'.rings').exists())
    def test_archive_setup_failure_closes_both_sockets(self):
        import capture_worker
        closed=[]
        class Sock:
            def close(self): closed.append(True)
        with tempfile.TemporaryDirectory() as d:
            out=str(pathlib.Path(d)/'result'); argv=['--control-fd','3','--marker-fd','4','--owner-pid','1','--owner-uid','1','--target-pid','1','--cpus','0','--output',out]
            with patch.object(capture_worker.socket,'socket',side_effect=lambda **kw:Sock()), patch.object(capture_worker,'RingArchive',side_effect=OSError('refusal')):
                with self.assertRaises(OSError): capture_worker.main(argv)
            self.assertEqual(len(closed),2)
    def test_marker_setup_failure_closes_control_socket(self):
        import capture_worker
        closed=[]
        class Sock:
            def close(self): closed.append(True)
        with tempfile.TemporaryDirectory() as d:
            out=str(pathlib.Path(d)/'result'); argv=['--control-fd','3','--marker-fd','4','--owner-pid','1','--owner-uid','1','--target-pid','1','--cpus','0','--output',out]
            with patch.object(capture_worker.socket,'socket',side_effect=[Sock(),OSError('bad marker')]):
                with self.assertRaises(OSError): capture_worker.main(argv)
            self.assertEqual(len(closed),1)
    def test_import_worker_without_native_execution(self):
        import capture_worker, owner_hook, owned_capture
        self.assertTrue(callable(capture_worker.build_capture))
        self.assertTrue(callable(owner_hook.RequestCapture.end))
        self.assertTrue(callable(owned_capture.Capture.finish))
if __name__ == '__main__': unittest.main()
