import unittest
from preflight_evaluate import evaluate
class Check(unittest.TestCase):
    def test_correct(self):
        r={'timings':{'prompt_n':2048,'cache_n':0},'tokens_evaluated':2048,'truncated':False}
        self.assertEqual(evaluate(r,2048)['verdict'],'PASS')
        for path,val in [('prompt_n',2047),('cache_n',1)]:
            bad={**r,'timings':{**r['timings'],path:val}}
            self.assertEqual(evaluate(bad,2048)['verdict'],'FAIL')
        self.assertEqual(evaluate({**r,'truncated':True},2048)['verdict'],'FAIL')
        self.assertEqual(evaluate({**r,'tokens_evaluated':True},2048)['verdict'],'INVALID')
    def test_missing(self):
        self.assertEqual(evaluate({},2048)['verdict'],'INVALID')
