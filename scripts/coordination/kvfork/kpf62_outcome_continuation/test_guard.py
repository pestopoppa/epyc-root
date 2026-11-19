import copy
import unittest
from guard import validate

class Tests(unittest.TestCase):
    def setUp(self):
        self.o=[{'id':'q','arm':a,'complete':True,'finish_reason':'eog','output_tokens':[1,2,3]} for a in ('full','reuse')]
        self.s=[{'id':'q','arm':a,'segment':i,'start':start,'tokens':tokens,'finish_reason':reason} for a in ('full','reuse') for i,start,tokens,reason in [(0,0,[1,2],'continue'),(1,2,[3],'eog')]]
    def test_valid_pair(self):
        self.assertEqual(validate(['q'],self.o,self.s),{'pairs':1,'outcomes':2,'segments':4})
    def test_exhaustion_refused(self):
        self.o[1].update(complete=False,finish_reason='length')
        with self.assertRaises(ValueError): validate(['q'],self.o,self.s)
    def test_interruption_and_missing_pair_refused(self):
        with self.assertRaises(ValueError): validate(['q'],self.o[:1],self.s)
        with self.assertRaises(ValueError): validate(['q'],self.o,self.s[:-1])
    def test_duplicate_cross_arm_and_token_mismatch_refused(self):
        with self.assertRaises(ValueError): validate(['q'],self.o+[self.o[0]],self.s)
        bad=copy.deepcopy(self.s);bad[-1]['arm']='full'
        with self.assertRaises(ValueError): validate(['q'],self.o,bad)
        bad=copy.deepcopy(self.s);bad[-1]['tokens']=[9]
        with self.assertRaises(ValueError): validate(['q'],self.o,bad)
    def test_single_segment(self):
        single=[{'id':'q','arm':a,'segment':0,'start':0,'tokens':[1,2,3],'finish_reason':'eog'} for a in ('full','reuse')]
        self.assertEqual(validate(['q'],self.o,single)['segments'],2)
if __name__=='__main__': unittest.main()
