import copy, unittest
from analyzer import analyze
I={'pid':'123','birth':'456','device':'0000:43:00.0','queue':'0','profiler':'synthetic-profiler'}
def fixture():
 return {'identity':I,'offset_scope':'synthetic-assumption-only','offset_ns':[-2,2], 'host_window_ns':[1,1000], 'phases':[{'id':'step0','host_ns':[100,400]},{'id':'step1','host_ns':[400,800]}], 'witnesses':[{'name':n,'identity':I,'host_ns':h,'trace_ns':t} for n,h,t in [('edge_start',[10,50],[20,40]),('interior',[450,500],[460,490]),('edge_end',[850,900],[860,890])]], 'kernels':[{'id':'a','identity':I,'trace_ns':[120,150]},{'id':'b','identity':I,'trace_ns':[450,470]},{'id':'c','identity':I,'trace_ns':[398,402]}]}
class Controls(unittest.TestCase):
 def test_valid_and_ambiguous(self):
  r=analyze(fixture()); self.assertEqual(r['counts'],{'step0':1,'step1':1}); self.assertEqual(r['ambiguous'],1); self.assertEqual(r['status'],'SYNTHETIC_ONLY')
 def test_mutations(self):
  def cases():
   d=fixture(); d['witnesses'].pop(); yield d
   d=fixture(); d['witnesses'][1]=copy.deepcopy(d['witnesses'][0]); yield d
   d=fixture(); d['witnesses'][0]['identity']=dict(I,pid='999'); yield d
   d=fixture(); d['witnesses'][1]['trace_ns']=[1,2]; yield d
   d=fixture(); d['witnesses'][1]['name']='edge_end'; yield d
   d=fixture(); d['offset_ns']=[2,-2]; yield d
   d=fixture(); d['offset_scope']='native-qualified'; yield d
   d=fixture(); d['kernels'][0]['identity']=dict(I,birth='999'); yield d
   d=fixture(); d['kernels'][1]['id']='a'; yield d
   d=fixture(); d['kernels']=[d['kernels'][0]]; yield d
   d=fixture(); d['phases'][1]['host_ns']=[399,800]; yield d
   d=fixture(); d['kernels'][0]['trace_ns']=[150,120]; yield d
   d=fixture(); d['witnesses'][2]['host_ns']=[700,750]; yield d
   d=fixture(); d['kernels']=[]; yield d
  for n,d in enumerate(cases()):
   with self.subTest(mutation=n):
    with self.assertRaises((ValueError,KeyError,TypeError)): analyze(d)
if __name__=='__main__': unittest.main(verbosity=2)
