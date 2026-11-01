import json,tempfile,unittest
from pathlib import Path
from completion import complete
class CompletionTests(unittest.TestCase):
 def test_qualification_rejects_missing_or_invalid(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'r';self.assertFalse(complete('qualification',p));p.write_text('{')
   self.assertFalse(complete('qualification',p))
   for n in (None,0,True):
    p.write_text(json.dumps({'kind':'qualification_control','target_exposed':False,'http_status':200,'draft_n':n}));self.assertFalse(complete('qualification',p))
   p.write_text(json.dumps({'kind':'qualification_control','target_exposed':False,'http_status':200,'draft_n':1}));self.assertTrue(complete('qualification',p))
 def test_full_requires_valid_paired_observation(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'r';x={'state':'incomplete_raw','partial':True,'divergence_known':False,'hybrid_acceptance':None,'legacy_acceptance':None};p.write_text(json.dumps(x));self.assertFalse(complete('full',p))
   x.update(state='complete_raw',partial=False,divergence_known=True,hybrid_acceptance=0.5,legacy_acceptance=0.4);p.write_text(json.dumps(x));self.assertTrue(complete('full',p))
   for key,value in [('partial',True),('divergence_known',False),('hybrid_acceptance',None),('legacy_acceptance',1.1)]:
    y=dict(x);y[key]=value;p.write_text(json.dumps(y));self.assertFalse(complete('full',p))
if __name__=='__main__':unittest.main()
