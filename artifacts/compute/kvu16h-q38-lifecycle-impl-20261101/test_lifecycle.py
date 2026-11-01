import unittest
from lifecycle import InvalidRun, Pair, run_pairs


class Fake:
    def __init__(self):
        self.calls = []
        self.cached = 32
        self.stop_result = True
        self.cancel = False
        self.fail_verify = False
    def start(self, arm, recipe):
        self.calls.append(('start', arm)); return arm
    def verify(self, server, arm, recipe):
        if self.fail_verify: raise InvalidRun('birth identity changed')
    def request(self, server, body, kind):
        self.calls.append((kind, server, body))
        return {'http_status': 200, 'timings': {'cache_n': self.cached}}
    def stop(self, server):
        self.calls.append(('stop', server)); return self.stop_result
    def stopping(self): return self.cancel


def recipes():
    base = {'binary': 'bound', 'model': 'bound', 'shape': {'np': 1}}
    return {'drafted': dict(base, draft_model='draft', draft_options={'type': 'dflash'}),
            'nodraft': dict(base, draft_model=None, draft_options={})}


class Tests(unittest.TestCase):
    def test_separate_servers_identical_body_and_warm_each(self):
        f=Fake(); result=run_pairs(f, recipes(), [Pair('x', {'prompt':'p'}, {'prompt':'p'}, 16)])
        self.assertFalse(result['partial'])
        self.assertEqual([x[:2] for x in f.calls], [('start','drafted'),('warm','drafted'),('measure','drafted'),('stop','drafted'),('start','nodraft'),('warm','nodraft'),('measure','nodraft'),('stop','nodraft')])
        self.assertEqual(result['records'][1]['body_sha256'],result['records'][3]['body_sha256'])
        self.assertEqual(result['cleanup'], {'drafted':True,'nodraft':True})

    def test_bad_recipes_or_overrides_refused_before_start(self):
        f=Fake(); r=recipes(); r['nodraft']['draft_options']={'n':0}
        with self.assertRaises(InvalidRun): run_pairs(f,r,[Pair('x',{})])
        with self.assertRaises(InvalidRun): run_pairs(f,recipes(),[Pair('x',{'nested':{'speculative.n_max':0}})])
        with self.assertRaises(InvalidRun): run_pairs(f,recipes(),[Pair('x',{'prompt':'other'}, {'prompt':'prefix'}, 1)])
        self.assertEqual(f.calls, [])

    def test_cache_witness_and_cleanup_fail_closed(self):
        for cache in (None, 0, True):
            f=Fake(); f.cached=cache
            out=run_pairs(f,recipes(),[Pair('x',{'prompt':'prefix task'}, {'prompt':'prefix'}, 1)])
            self.assertTrue(out['partial']); self.assertEqual(out['cleanup'],{'drafted':True})
            self.assertNotIn(('start','nodraft'),f.calls)
        f=Fake(); f.stop_result=False
        self.assertTrue(run_pairs(f,recipes(),[Pair('x',{})])['partial'])

    def test_identity_and_stop_do_not_start_second_arm(self):
        f=Fake(); f.fail_verify=True
        self.assertTrue(run_pairs(f,recipes(),[Pair('x',{})])['partial'])
        self.assertEqual(f.calls,[('start','drafted'),('stop','drafted')])
        f=Fake(); f.cancel=True
        self.assertTrue(run_pairs(f,recipes(),[Pair('x',{})])['partial'])
        self.assertEqual(f.calls,[])

if __name__ == '__main__': unittest.main()
