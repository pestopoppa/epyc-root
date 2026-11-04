import json,tempfile,unittest
from pathlib import Path
from adapters import ufh12_gs_coverage as adapter
fc = adapter._frozen
gc = fc.v

class CaptureTest(unittest.TestCase):
 def test_partial_sealed_source_and_tamper(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);rows=[{'id':str(i),'text':'q'+str(i),'stratum':'fixture','answer_named_verbatim':False,'code_intent':False} for i in range(500)]
   cohort={'n':500,'rows':rows,'scope':'synthetic fixture'};(p/'cohort.json').write_text(json.dumps(cohort))
   context={'schema':'epyc.gs-frozen-query-native-context.v2','cohort_sha256':gc.digest((p/'cohort.json').read_bytes()),'phase':'run','scope':'synthetic fixture','filler_id':'fixture','synthetic':True}
   (p/'run-context.json').write_text(json.dumps(context));ctx=(p/'run-context.json').read_bytes()
   lane=[{'id':str(i),'cosine':1-i/100} for i in range(10)]
   r=gc.seal({'id':'0','query_sha256':gc.digest(b'q0'),'cohort_sha256':context['cohort_sha256'],'phase':'run','stratum':'fixture','answer_named_verbatim':False,'code_intent':False,'token_count_eg2':4,'context_sha256':gc.digest(ctx),'captured_at':'now','stores':{'episodic':{'bge':lane,'eg2':lane},'strategy':{'bge':lane,'eg2':lane}}})
   (p/'results.jsonl').write_text(json.dumps(r)+'\n');side=fc.emit(p);out=json.loads(side.read_text())
   self.assertEqual(out['value'],1);self.assertEqual(out['extra']['expected_count'],500);self.assertFalse(out['extra']['complete']);self.assertEqual(fc.validate(out),[])
   native=adapter.native_rows(side);self.assertEqual(len(native),1);claim=adapter.project(native[0]);self.assertEqual(claim.source_kind,'ufh12-gs-coverage');self.assertEqual(claim.value,1);from claim_tuple import grade;self.assertEqual(grade(claim)[:2], ('Judged', 'Located'));self.assertEqual(claim.applicability, {'backend':'cpu'})
   (p/'results.jsonl').write_text('{}\n');self.assertTrue(fc.validate(out))
