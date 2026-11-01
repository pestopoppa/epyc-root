import json,tempfile,unittest
from pathlib import Path
from completion import complete
class CompletionTests(unittest.TestCase):
 def test_qualification_rejects_missing_or_invalid(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'r';self.assertFalse(complete('qualification',p));p.write_text('{')
   self.assertFalse(complete('qualification',p))
   good={'kind':'qualification_control','target_exposed':False,'http_status':200,'draft_n':4,'draft_n_accepted':2,'token_count':5,**{k:'a'*64 for k in ('plan_sha256','full_model_catalog_sha256','source_sha256','grant_sha256')}}
   p.write_text(json.dumps(good));self.assertTrue(complete('qualification',p))
   for key,value in [('draft_n',None),('draft_n',0),('draft_n',True),('draft_n_accepted',None),('draft_n_accepted',5),('draft_n_accepted',True),('token_count',0),('token_count',True),('source_sha256','not-a-hash'),('target_exposed',True)]:
    bad=dict(good);bad[key]=value;p.write_text(json.dumps(bad));self.assertFalse(complete('qualification',p))
 def test_full_requires_valid_paired_observation(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'r';x={'state':'incomplete_raw','partial':True,'divergence_known':False,'hybrid_acceptance':None,'legacy_acceptance':None};p.write_text(json.dumps(x));self.assertFalse(complete('full',p))
   x.update(state='complete_raw',partial=False,divergence_known=True,hybrid_acceptance=0.5,legacy_acceptance=0.4);p.write_text(json.dumps(x));self.assertTrue(complete('full',p))
   for key,value in [('partial',True),('divergence_known',False),('hybrid_acceptance',None),('legacy_acceptance',1.1)]:
    y=dict(x);y[key]=value;p.write_text(json.dumps(y));self.assertFalse(complete('full',p))
if __name__=='__main__':unittest.main()
