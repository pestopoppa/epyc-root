import threading
import types
import unittest
import item4_control as d

class Client:
    def __init__(self):
        self.release=threading.Event(); self.lock=threading.Lock(); self.active={}; self.bad=False
    def complete(self, body, timeout=None):
        slot=body['id_slot']; n=body['n_predict']; task=100+slot
        if slot==3 and n==0:
            return {'http':200,'timings':{'id_slot':3,'id_task':99}}
        if slot!=3:
            with self.lock: self.active[slot]=True
            if not self.release.wait(2): raise RuntimeError('fake timeout')
        else:
            self.release.set()
        t={'id_slot':slot,'id_task':task}
        if slot==3:
            if body['slot_fork'] is False: t['cache_n']=3
            else: t.update(fork_src_kind='checkpoint',n_fork_tokens=3,fork_src_slot=0)
        if self.bad and slot==1: t.pop('id_task')
        return {'http':200,'timings':t,'tokens':[1]}
    def slots(self):
        with self.lock: active=dict(self.active)
        a=[]
        for s in range(4):
            a.append({'is_processing':bool(active.get(s)),'id_task':100+s,
                      'next_token':{'n_decoded':9},'n_prompt_tokens':3,
                      'checkpoints':[{'n_tokens':3,'pinned':True}]})
        return a

def body(ids,n,slot,**kwargs):
    return {'prompt':ids,'n_predict':n,'id_slot':slot,'slot_fork':kwargs.get('fork')}
class FakeGate:
    @staticmethod
    def G(ctx,group): return {'trunk':[1,2,3], 'src_tail_long':[4,5,6], 'suffixes':[[7,8]]}
    @staticmethod
    def cat(x,y): return x+y
    @staticmethod
    def erase_all(ctx): pass
    body_for=staticmethod(body)
class FakeCtx:
    def __init__(self):
        self.client=Client();self.args=types.SimpleNamespace(item4_suffix=0,n_probs=20)
        self.ps=types.SimpleNamespace(decoders=[[10],[11]])
    def check_boundary(self):pass
class Tests(unittest.TestCase):
    def test_both_arms(self):
        for fork in (True,False):
            result=d.run_arm(FakeGate,FakeCtx(),0,3,fork=fork,timeout_s=1)
            self.assertEqual(result['target']['task'],103)
            self.assertEqual([b['task'] for b in result['decoders']],[101,102])
    def test_missing_binding_refused(self):
        ctx=FakeCtx();ctx.client.bad=True
        with self.assertRaises(d.Refusal): d.run_arm(FakeGate,ctx,0,3,fork=True,timeout_s=1)
    def test_bad_geometry_refused(self):
        with self.assertRaises(d.Refusal): d.run_arm(FakeGate,FakeCtx(),0,4,fork=True,timeout_s=1)
    def test_arms_force_speculation_off(self):
        original=FakeCtx().client
        calls=[]; old=Client.complete
        def capture(self, request, timeout=None):
            calls.append(request.copy());return old(self,request,timeout)
        Client.complete=capture
        try:d.run_arm(FakeGate,FakeCtx(),0,3,fork=False,timeout_s=1)
        finally:Client.complete=old
        self.assertTrue(all(x['speculative.n_max']==0 for x in calls))
if __name__=='__main__':unittest.main()

class RawTests(unittest.TestCase):
    def test_first_logit_capture(self):
        import json
        b={'slot':3,'task':9,'response':{'tokens':[1]}}
        row={'schema':'kpf.first_logits.v1','scope':'first_token_speculation_disabled','slot':3,'task':9,
             'position':7,'input_token':4,'selected_token':1,'n_vocab':2,'float32_bits_u32':[0,1065353216]}
        raw=(json.dumps(row)+'\n').encode()
        self.assertEqual(d.first_logits(raw,b,7,4)['bits'],[0,1065353216])
        for bad in (b'',raw+raw,raw.replace(b'1065353216',b'2139095040')):
            with self.assertRaises(d.Refusal):d.first_logits(bad,b,7,4)

class PairTests(unittest.TestCase):
    def test_layout_refusal_is_unknown(self):
        class FakeGuard:
            @staticmethod
            def guard(raw,**kw): return {'ok':True}
            @staticmethod
            def compare(a,b): raise ValueError('layout mismatch')
        arm={'src':{},'target':{},'decoders':[{},{}],'prefix':3}
        result=d.pair_observation(FakeGuard,b'trace',b'',arm,arm,(3,1),(3,1))
        self.assertEqual(result['status'],'UNKNOWN')
        self.assertIsNone(result['gate_verdict'])
