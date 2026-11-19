import unittest
from dataclasses import replace
from calibration import Sample,Witness,validate

class Calibration(unittest.TestCase):
    def setUp(self):
        self.s=[Sample(x, x-100, x+2, 1_000_000_000//10) for x in []]
        # 100 MHz: tick*10 is HSA nanoseconds, and host-HSA offset = 100 ns.
        self.s=[Sample(x,x//10-10,x+1,100_000_000) for x in (1000,1100,5000,5100)]
        self.w=[Witness(n,t,t+100,t-90,t-20) for n,t in [('edge0',2000),('middle',3000),('edge1',4000)]]
        self.args=(self.s,self.w,['edge0','middle','edge1'],1000)
    def run_check(self,s=None,w=None,markers=None,gap=1000,source='predeclared experimental bound'):
        return validate(self.s if s is None else s,self.w if w is None else w,markers or self.args[2],gap,bound_source=source)
    def test_correct_arithmetic_is_diagnostic_only(self):
        r=self.run_check();self.assertEqual(r['observed_offset_ns'],[100,101]);self.assertIn('no identity',r['scope'])
    def test_missing_and_duplicate_witnesses_refused(self):
        for w in (self.w[:-1],self.w[:2]+[self.w[0]], [replace(self.w[0],marker='edge1'), self.w[1], replace(self.w[2],marker='edge0')]):
            with self.assertRaises(ValueError):self.run_check(w=w)
    def test_changed_frequency_reversed_time_and_conflict_refused(self):
        for s in (self.s[:1]+[replace(self.s[1],hz=99_000_000)]+self.s[2:],self.s[:1]+[replace(self.s[1],before_ns=900)]+self.s[2:],self.s[:1]+[replace(self.s[1],hsa_tick=0)]+self.s[2:]):
            with self.assertRaises(ValueError):self.run_check(s=s)
    def test_missing_provenance_gap_and_bracket_refused(self):
        with self.assertRaises(ValueError):self.run_check(source='')
        with self.assertRaises(ValueError):self.run_check(gap=5)
        with self.assertRaises(ValueError):self.run_check(w=[replace(self.w[0],profiler_begin_ns=0)]+self.w[1:])
    def test_boolean_and_negative_time_refused(self):
        for value in (True,-1):
            with self.assertRaises(ValueError):self.run_check(s=[replace(self.s[0],before_ns=value)]+self.s[1:])

if __name__=='__main__':unittest.main()
