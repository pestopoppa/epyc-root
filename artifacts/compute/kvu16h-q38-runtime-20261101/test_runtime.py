import unittest
from runtime import Runtime, RuntimeFailure, SpawnFailure

class Supervisor:
    def __init__(self): self.calls=[]; self.fail=None; self.ok=True
    def spawn(self,a,r):
        self.calls.append(('spawn',a))
        if self.fail: raise self.fail
        return object()
    def verify(self,h,a,r): self.calls.append(('verify',a)); return self.ok
    def stop_and_drain(self,h): self.calls.append(('drain',h)); return self.ok
class Transport:
    def __init__(self): self.sent=[]
    def send(self,h,b): self.sent.append((h,b)); return {'http_status':200}
class Journal:
    def __init__(self): self.allow=True; self.events=[]
    def before_request(self,a,k,d): self.events.append(('before',a,k,d)); return self.allow
    def after_response(self,a,k,r): self.events.append(('after',a,k)); return self.allow
class Tests(unittest.TestCase):
    def setUp(self):
        self.s=Supervisor(); self.t=Transport(); self.j=Journal(); self.r=Runtime(self.s,self.t,self.j,lambda:False)
    def test_verified_request_and_drain(self):
        h=self.r.start('nodraft',{}); self.r.verify(h,'nodraft',{}); self.r.request(h,{'prompt':'x'},'measure')
        self.assertEqual([x[0] for x in self.j.events],['before','after']); self.assertTrue(self.r.stop(h)); self.assertFalse(self.r.stop(h))
    def test_no_send_without_identity_or_receipt(self):
        h=self.r.start('drafted',{})
        with self.assertRaises(RuntimeFailure): self.r.request(h,{},'measure')
        self.r.verify(h,'drafted',{}); self.j.allow=False
        with self.assertRaises(RuntimeFailure): self.r.request(h,{},'measure')
        self.assertEqual(self.t.sent,[]); self.assertTrue(self.r.stop(h))
    def test_failed_spawn_never_claims_cleanup(self):
        self.s.fail=SpawnFailure('pidfd failed',False)
        with self.assertRaises(SpawnFailure): self.r.start('drafted',{})
        self.assertTrue(self.r.cleanup_unverified)
    def test_unknown_spawn_error_and_failed_drain(self):
        self.s.fail=OSError('unknown')
        with self.assertRaises(RuntimeFailure): self.r.start('drafted',{})
        self.assertTrue(self.r.cleanup_unverified)
        self.s.fail=None
        with self.assertRaises(RuntimeFailure): self.r.start('drafted',{})
        self.assertEqual(len([x for x in self.s.calls if x[0]=='spawn']),1)
    def test_failed_drain_preserves_handle_and_blocks_reentry(self):
        h=self.r.start('drafted',{}); self.r.verify(h,'drafted',{})
        self.s.ok=False
        self.assertFalse(self.r.stop(h)); self.assertIs(self.r.active,h)
        self.assertFalse(h.stopped); self.assertTrue(self.r.cleanup_unverified)
        with self.assertRaises(RuntimeFailure): self.r.start('nodraft',{})
        with self.assertRaises(RuntimeFailure): self.r.request(h,{},'measure')
        self.assertEqual(self.t.sent,[])
        self.s.ok=True
        self.assertTrue(self.r.stop(h)); self.assertIsNone(self.r.active)
        with self.assertRaises(RuntimeFailure): self.r.start('nodraft',{})
    def test_unverified_spawn_blocks_reentry(self):
        self.s.fail=SpawnFailure('identity unknown',False)
        with self.assertRaises(SpawnFailure): self.r.start('drafted',{})
        self.s.fail=None
        with self.assertRaises(RuntimeFailure): self.r.start('nodraft',{})
        self.assertEqual(len([x for x in self.s.calls if x[0]=='spawn']),1)
    def test_stop_blocks_spawn_and_request(self):
        self.r.stop_requested=lambda:True
        with self.assertRaises(RuntimeFailure): self.r.start('drafted',{})
        self.assertEqual(self.s.calls,[])
    def test_coordinator_uses_separate_verified_servers(self):
        import importlib.util
        from pathlib import Path
        import sys
        path=Path(__file__).resolve().parent.parent/'kvu16h-q38-lifecycle-impl-20261101'/'lifecycle.py'
        spec=importlib.util.spec_from_file_location('q38_lifecycle_test',path)
        module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module)
        base={'binary':'bound','model':'bound','shape':{'np':1}}
        recipes={'drafted':dict(base,draft_model='draft',draft_options={'type':'dflash'}),
                 'nodraft':dict(base,draft_model=None,draft_options={})}
        out=module.run_pairs(self.r,recipes,[module.Pair('a',{'prompt':'one'})])
        self.assertFalse(out['partial']); self.assertEqual(out['cleanup'],{'drafted':True,'nodraft':True})
        self.assertEqual([x[1] for x in self.s.calls if x[0]=='spawn'],['drafted','nodraft'])
        self.assertIsNot(self.t.sent[0][0],self.t.sent[1][0])

if __name__=='__main__': unittest.main()
