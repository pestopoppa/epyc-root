import pathlib,tempfile,json,unittest
from postE17_histogram import project
def native(rows,era=None,timestamp=None):
 r={'eval_details':{'details':{},'question_results':rows}}
 if era is not None:r['eval_details']['details']['eval_quality_era']=era
 if timestamp is not None:r['timestamp']=timestamp
 return r
class NativeCohortControls(unittest.TestCase):
 def project(self,rows):
  with tempfile.TemporaryDirectory() as tmp:
   p=pathlib.Path(tmp)/'native.jsonl';p.write_text(''.join(json.dumps(r)+'\n' for r in rows));return project([p])
 def test_cutover(self):
  d=self.project([native([{'disposition':'task_failed','error':'e'}],timestamp=t) for t in ['2026-09-23T21:37:08Z','2026-09-23T21:37:09Z']]);self.assertEqual(d['residual_count'],1);self.assertEqual(d['refusals']['unbound_cohort'],1)
 def test_missing_timestamp(self):
  d=self.project([native([{'disposition':'task_failed','error':'e'}],era='E17'),native([{'disposition':'task_failed','error':'e'}])]);self.assertEqual(d['residual_count'],1);self.assertEqual(d['missingness']['timestamp_missing'],2);self.assertEqual(d['refusals']['unbound_cohort'],1)
 def test_unparseable_timestamp(self):
  d=self.project([native([{'disposition':'task_failed'}],timestamp=t) for t in ['broken','2026-09-24T00:00:00']]);self.assertEqual(d['residual_count'],0);self.assertEqual(d['missingness']['timestamp_unparseable'],2)
 def test_historical_mixed_era(self):
  d=self.project([native([{'disposition':'task_failed'}],era='E16',timestamp='2026-10-01T00:00:00Z'),native([{'disposition':'task_failed','error':'contradiction'}],era='E17',timestamp='2026-09-23T21:37:08Z'),native([{'disposition':'task_failed','timestamp':'2026-09-23T21:37:08Z'},{'disposition':'task_failed','eval_quality_era':'E16'},{'disposition':'task_failed','error':'e'}],era='E17')]);self.assertEqual(d['error_histogram'],{'e':1});self.assertEqual(d['refusals'],{'historical_or_unknown_era':1,'era_timestamp_conflict':1,'unsupported_child_cohort_fields':2})
 def test_class_counts(self):
  d=self.project([native([{'disposition':s,'error':'e'} for s in ['task_failed','task_failed','infra_failed','scoring_failed','scored']],era='E17'),{'row_type':'question_result','ended_at_s':1800000000,'result':{'disposition':'task_failed','error':'sidecar'}}]);self.assertEqual(d['class_counts'],{'task_failed':3,'infra_failed':1,'scoring_failed':1,'scored':1});self.assertEqual(d['error_histogram'],{'e':2,'sidecar':1})
 def test_missing_error_unknown_category(self):
  d=self.project([native([{'disposition':'task_failed'},{'disposition':'mystery'},{}],era='E17')]);self.assertEqual(d['error_histogram'],{'<missing native error>':1});self.assertEqual(d['missingness']['error_missing_or_nontext'],1);self.assertEqual(d['refusals']['unknown_or_missing_category'],2)
 def test_malformed_rows(self):
  d=self.project([[],native({},era='E17'),native([None],era='E17'),{'era':'E17','status':'task_failed','error_text':'invented'}]);self.assertEqual(d['refusals'],{'non_object_row':1,'malformed_question_rows':1,'malformed_question_row':1,'unsupported_native_shape':1})
  with tempfile.TemporaryDirectory() as tmp:
   p=pathlib.Path(tmp)/'bad.jsonl';p.write_text('{\n');self.assertEqual(project([p])['refusals'],{'malformed_json':1})
