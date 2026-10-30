"""Cross-repository prospective PIP-02 capture and projection conformance."""
import importlib.util,json,os,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/vidya'))
from adapters import pip02_teds as adapter
from claim_tuple import ProjectionError,grade,to_frames
RESEARCH=Path(os.environ.get('PIP02_RESEARCH_ROOT','/workspace/repos/epyc-inference-research'))
WRITER=RESEARCH/'scripts/benchmark/odl_bench/pip02_score_capture.py'

@unittest.skipUnless(WRITER.is_file(),'prospective Research writer unavailable')
class CaptureTest(unittest.TestCase):
 def setUp(self):
  spec=importlib.util.spec_from_file_location('pip02_capture',WRITER);self.w=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.w)
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);p=Path(self.temp.name);self.p=p
  for name,content in [('source','source'),('capture','capture'),('registry','registry'),('gt','gt')]: (p/name).write_text(content)
  (p/'config').write_text(json.dumps({'server':{'model':'/test/model.gguf','pins':{'model':'a'*64}}}))
  (p/'plan').write_text(json.dumps({'pages':[{'image':str(i),'index':i,'table_count':1,'sha256':self.w.digest(p/'source')} for i in range(5)]}))
  h=self.w.digest;self.w.begin(p/'start','paddle',0,[p/'source',p/'gt',p/'config',p/'plan'],['scorer','0'])
  lin={'verified':True,'origin_capture_sha256':[h(p/'capture')],'finish_capture_sha256':h(p/'capture'),'selected_registries':{str(p/'registry'):h(p/'registry')},'selected_captures':{str(p/'capture'):h(p/'capture')},'registered_source_pins':{h(p/'capture'):{str(p/'source'):h(p/'source')}}}
  pages=[{'position':i,'image':str(i),'gt_index':i,'gt_tables':1,'status':'unknown','tables':None,'reason':'missing'} for i in range(5)]
  pages[0].update(status='complete',reason='complete',tables=[{'gt_idx':[0],'pred_idx':[0],'teds':.6,'teds_structure_only':.7}],input_sha256={str(p/'source'):h(p/'source')},source_lineage=lin)
  self.body={'arm':'paddle','cohort':'test','shard':0,'plan_sha256':h(p/'plan'),'gt_sha256':h(p/'gt'),'config_sha256':h(p/'config'),'scoring_sources_sha256':{'scorer':h(p/'source')},'pages':pages,'coverage':{'pages_complete':1,'pages_total':5,'gt_tables_scored':1,'gt_tables_total':5},'means':{'teds':.6,'teds_structure_only':.7}}
 def seal(self):
  p=self.p;(p/'result').write_text(json.dumps(self.body));self.w.finish(p/'start',p/'result',p/'x.score-receipt.json');return p/'x.score-receipt.json'
 def test_partial_numeric_observation(self):
  path=self.seal();rows=adapter.native_rows(path);self.assertEqual(len(rows),2);t=adapter.project(rows[0]);self.assertEqual(grade(t)[:2],('Judged','Located'));self.assertEqual(t.reps,1)
  evidence=to_frames(t,as_of=self.w.now(),adapter_id=adapter.ADAPTER_ID)[2]['assertion'];self.assertEqual(evidence['value'],'0.6');self.assertEqual(evidence['unit'],'score');self.assertIn('pip02-score:paddle:test:shard-0:sha256-',evidence['observation']['mechanism']['id']);self.assertIn('test paddle shard 0 (5-page shard convention)',t.claim);self.assertEqual(evidence['observation']['outcome_native'],'partial shard coverage')
 def test_changed_selected_capture_refused(self):
  path=self.seal();(self.p/'capture').write_text('changed')
  with self.assertRaises(ProjectionError):adapter.native_rows(path)
 def test_wrong_denominator_refused(self):
  self.body['coverage']['gt_tables_total']=4;path=self.seal()
  with self.assertRaises(ProjectionError):adapter.native_rows(path)
 def test_unknown_with_score_refused(self):
  self.body['pages'][1]['tables']=[];path=self.seal()
  with self.assertRaises(ProjectionError):adapter.native_rows(path)
 def test_missing_selected_capture_refused_at_finish(self):
  (self.p/'result').write_text(json.dumps(self.body));(self.p/'capture').unlink()
  with self.assertRaises(OSError):self.w.finish(self.p/'start',self.p/'result',self.p/'receipt')
 def test_prediction_index_contract(self):
  for invalid in ([],[-1],[True],[0,1],['0'],[None]):
   with self.subTest(pred=invalid):
    self.body['pages'][0]['tables'][0]['pred_idx']=invalid
    path=self.p/'bad-result';path.write_text(json.dumps(self.body));r=self.p/'bad-receipt'
    if r.exists(): r.unlink()
    self.w.finish(self.p/'start',path,r)
    with self.assertRaises(ProjectionError):adapter.native_rows(r)
 def test_unmatched_sentinel_accepted(self):
  self.body['pages'][0]['tables'][0]['pred_idx']=[''];path=self.seal();self.assertEqual(len(adapter.native_rows(path)),2)
 def test_odl_receipt_retained_but_unscoped_projection_declines(self):
  p=self.p;h=self.w.digest
  self.w.begin(p/'odl-start','odl',0,[p/'source',p/'gt',p/'plan'],['odl-scorer','0'])
  body=dict(self.body,arm='odl',scorer_sha256=h(p/'source'),pins_sha256=h(p/'source'),source_lineage={'0':{'verified':True}})
  (p/'odl-result').write_text(json.dumps(body));self.w.finish(p/'odl-start',p/'odl-result',p/'odl-receipt')
  self.assertEqual(adapter.native_rows(p/'odl-receipt'),())
  self.assertTrue((p/'odl-receipt').is_file())
 def test_invalid_match_refused(self):
  self.body['pages'][0]['tables'][0]['gt_idx']=[1];path=self.seal()
  with self.assertRaises(ProjectionError):adapter.native_rows(path)
 def test_score_out_of_bounds_refused(self):
  self.body['pages'][0]['tables'][0]['teds']=1.1;path=self.seal()
  with self.assertRaises(ProjectionError):adapter.native_rows(path)
 def test_result_tamper_refused(self):
  path=self.seal();(self.p/'result').write_text('{}')
  with self.assertRaises(ProjectionError):adapter.native_rows(path)
 def test_start_cannot_overwrite(self):
  with self.assertRaises(FileExistsError):self.w.begin(self.p/'start','paddle',0,[self.p/'gt'],['x'])
if __name__=='__main__':unittest.main()
