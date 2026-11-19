import ast
import copy
import pathlib
import unittest

HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE.parent / 'kpf50-no-redraw-prep-20261104' / 'runner/kpf18_gate.py'

def extract():
    tree=ast.parse(BASE.read_text())
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='require_kpf50_forks')
    env={};exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(BASE),'exec'),env)
    return env['require_kpf50_forks']

class Guard(unittest.TestCase):
    def setUp(self):
        self.guard=extract()
        self.replies={i:{'http':200,'error':None,'timings':{'n_fork_tokens':60000+i}} for i in range(4)}
    def test_four_real_counts(self):
        self.assertEqual(self.guard(self.replies),[60000,60001,60002,60003])
    def test_missing_or_extra_child_refuses(self):
        for value in ({i:self.replies[i] for i in (0,1,2)}, {**self.replies,4:self.replies[0]}, {False:self.replies[0],True:self.replies[1],2:self.replies[2],3:self.replies[3]}):
            with self.subTest(value=value),self.assertRaises(ValueError):self.guard(value)
    def test_bad_fork_witness_refuses(self):
        for value in (None,0,59999,60000.0,True,'60000',[],{}):
            r=copy.deepcopy(self.replies);r[2]['timings']['n_fork_tokens']=value
            with self.subTest(value=value),self.assertRaises(ValueError):self.guard(r)
        for value in (None,{},'bad'):
            r=copy.deepcopy(self.replies);r[2]['timings']=value
            with self.subTest(timings=value),self.assertRaises(ValueError):self.guard(r)
    def test_failed_http_and_missing_response_refuse(self):
        for value in (None,{}, {'http':500,'timings':{'n_fork_tokens':60000}}, {'http':200,'error':'timeout','timings':{'n_fork_tokens':60000}}):
            r=copy.deepcopy(self.replies);r[3]=value
            with self.subTest(value=value),self.assertRaises(ValueError):self.guard(r)

if __name__=='__main__': unittest.main()
