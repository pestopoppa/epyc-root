import hashlib, importlib.util, json, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
sys.path[:0]=[str(ROOT/'scripts/vidya/producers/lex2'),str(ROOT/'scripts/vidya')]
import lex2_native_capture as cap
import emit_lex2_observations as bridge
import claim_tuple
import ingest_sources, loop_beliefs
from ledger import Ledger
from datetime import datetime, timezone
spec=importlib.util.spec_from_file_location('lex2_adapter_draft',ROOT/'scripts/vidya/adapters/conversation_stack_measurement.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
class T(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory(); d=Path(self.t.name); self.d=d; h='a'*64
  c={k:h for k in ('dev_manifest_sha256','test_manifest_sha256','overlap_exclusions_sha256','clip_sha256','context_sha256','tokenizer_sha256','model_sha256','source_sha256','binary_sha256','ggml_sha256','grant_sha256','request_sha256')}
  (d/'manifest').write_text(json.dumps({'records':[{'file_id':'c'}]}));c['dev_manifest_sha256']=sha(d/'manifest')
  c['ggml_path']=str(d/'libggml.so')
  c.update(dataset_revision='r',clip_id='c',context_id='x',ggml_version='g',grant_id='grant',split='dev',scope='local',engine='nemo',configured_alpha=1,context_count=1,cpus=[1,2]); a=cap.start_attempt(d/'item.belief-attempt.json',c)
  (d/'stderr').write_text('LEX2 external tokenizer vocabulary verified (128 pieces)\nRNNT word boosting active phrases=1 effective_alpha=1.000000\n');(d/'stdout').write_text('test');(d/'samples').write_text(json.dumps({'sampled_while_child_live':True,'grant_id':'grant','grant_sha256':h,'ggml_mapping_observed':True,'ggml_library_sha256':h,'ggml_library_path':str(d/'libggml.so')})+'\n')
  binding=dict(clip_id='c',wav_sha256=h,context_sha256=h,model_sha256=h,runtime_sha256=h,grant_id='grant',configured_alpha=1,engine='nemo',scope='local',spm_sha256=h);(d/'item.result.json').write_text(json.dumps(dict(status='ok',rc=0,reaped=True,binding=binding)))
  o=dict(status='ok',child_reaped=True,returncode=0)
  for k in ('result','stdout','stderr','samples'):
   path=d/('item.result.json' if k=='result' else k);o[k+'_sha256']=sha(path);o[k+'_path']=str(path)
  cap.finish_attempt(d/'item.belief-disposition.json',a,o)
  (d/'terminal').write_text(json.dumps({'state':'complete_raw','counts':{'unknown':0}}))
  (d/'bundle').write_text(json.dumps(dict(schema='epyc.cs8.lex2.native_bundle.v1',terminal_path=str(d/'terminal'),terminal_sha256=sha(d/'terminal'),items=[dict(attempt_path=str(d/'item.belief-attempt.json'),attempt_sha256=sha(d/'item.belief-attempt.json'),disposition_path=str(d/'item.belief-disposition.json'),disposition_sha256=sha(d/'item.belief-disposition.json'))])))
  self.f=dict(scorer_predeclared_sha256=h,lex2_native_schema='epyc.cs8.lex2.prospective.v1',model_file='synthetic-lex2-fixture.gguf',runner_id='nemo',runner_commit='b'*40,ggml_version='g',backend='cpu',device='cpu',stratum='dev',dataset_revision='r',list_scope='local',case_policy='casefold',weights_sha256=h,dev_manifest_sha256=sha(d/'manifest'),split_manifest_path=str(d/'manifest'),test_manifest_sha256=h,overlap_exclusions_sha256=h,native_capture_sha256=sha(d/'bundle'),scorer_sha256=h,n=1,attempted_n=1,unknown_n=0,raw_token_unk_count=None,whisper_parity_gate_ref='ref',native_capture_path=str(d/'bundle'),keyword_f=.5)
  self.f.update(quant='q8',residency_proof='synthetic',language='en',normaliser_id='lexical',reference_set_id='fixture',reference_set_track='dev',segmentation_mode='clip',corpus_id='fixture@aaaaaaaaaaaa',normaliser_sha256=h,manifest_sha256=h,decode_options={'fixture':True},language_mode='forced',unk_count=0,unk_ban=False,confirmation_reuse_n=0,column='lex1_lexical',candidate=False,streaming=False)
  self.row=dict(metric='lexicon_keyword_f',value=.5)
 def tearDown(self):self.t.cleanup()
 def test_valid(self):self.assertEqual(m._lex2_native_problems(self.row,self.f,{}),[])
 def test_producer_projection(self):
  score={'schema':'cs8.lex2.dev-selection.v1','test_opened':False,'dev_manifest_sha256':self.f['dev_manifest_sha256'],'raw_terminal_sha256':sha(self.d/'terminal'),'scorer_predeclared_sha256':'a'*64,'cells':{'nemo|local|1':{'n':1,'folded':{'counts':{'tp':1,'fp':1,'fn':1},'f':.5,'non_list_wer':.2},'sensitive':{'counts':{'tp':1,'fp':1,'fn':1},'f':.5}}}}
  p=self.d/'score';p.write_text(json.dumps(score))
  harness={'model':'fixture','quant':'q8','runtime':{'kind':'port','binary_sha256':'a'*64},'device':'cpu','host_lane':'fixture','co_tenant':{'present':False,'sampled_during_row':True},'llm_judged':False}
  scdir=self.d/'scorer-link';scdir.mkdir();(scdir/'run').symlink_to(self.d,target_is_directory=True)
  original_replay=bridge.verify_score_replay;bridge.verify_score_replay=lambda *args: None # separate replay fixture below
  self.addCleanup(setattr,bridge,'verify_score_replay',original_replay)
  side=bridge.emit(m,p,self.d,'fixture','fixture',{'nemo|local|1':self.f},harness,scorer_dir=scdir,emitted_at='2026-10-31T00:00:00Z')
  rows=m.native_rows(side);self.assertEqual(len(rows),7)
  for row in rows:
   claim=m.project(row);self.assertEqual(claim.protocol_id,'');self.assertEqual(claim_tuple.grade(claim)[:2],('Judged','Located'))
  sys.modules['adapters.conversation_stack_measurement']=m
  now=datetime.now(timezone.utc).isoformat(); ledger=self.d/'ledger.jsonl'
  report=ingest_sources.ingest(Ledger(ledger),'conversation-stack-measurement',[side],as_of=now)
  self.assertEqual(report['rows_projected'],7);self.assertFalse(report['refused'])
  class Sync:
   def status(self,*a,**kw):return {'fresh':True,'lag_entries':0,'index_max_id':1,'synced_max_id':1,'last_sync':now}
   def sync(self,*a,**kw):raise AssertionError('unexpected sync')
  cfg=self.d/'alarm.yaml';cfg.write_text('backend: file\nfile:\n  path: '+str(self.d/'alarm.jsonl')+'\n')
  answer=loop_beliefs.prepare('test.cs8.lex2',{'backend':'cpu','device':'cpu','model_sha256':'a'*64,'model_file':'synthetic-lex2-fixture.gguf'},ledger=ledger,index_path=self.d/'index.yaml',as_of=now,sync_module=Sync(),known_good=self.d/'known.json',alarm_state=self.d/'alarm-state.json',alarm_config=cfg,read_log=self.d/'reads.jsonl')
  visible=[x for x in answer.get('evidence',{}).get('claims',[]) if x.get('source_kind')=='conversation-stack-measurement']
  self.assertEqual(answer['status'],'ready');self.assertEqual(len(visible),7)
  other=loop_beliefs.prepare('test.cs8.lex2',{'backend':'cpu','device':'cpu','model_file':'unrelated-real-model.gguf'},ledger=ledger,index_path=self.d/'index.yaml',as_of=now,sync_module=Sync(),known_good=self.d/'known-other.json',alarm_state=self.d/'alarm-state-other.json',alarm_config=cfg,read_log=self.d/'reads-other.jsonl')
  self.assertFalse([x for x in other.get('evidence',{}).get('claims',[]) if x.get('source_kind')=='conversation-stack-measurement'])
 def test_score_replay(self):
  src=self.d/'scorer';src.mkdir()
  (src/'score_dev.py').write_text("from pathlib import Path\nPath(__file__).with_name('DEV-SELECTION.json').write_text('exact')\n")
  (src/'grid_job.py').write_text("N=None\n")
  for name in ('research-scorer-snapshot','run'):(src/name).mkdir()
  for name in ('SOURCE-SHA256SUMS','CONVERSATION-CONTEXTS.json','DOMAIN-LEXICON-PROPOSAL.json'):(src/name).write_text('fixture')
  (src/'SCORER-PREDECLARED.json').write_text(json.dumps({'source_sha256':{k:sha(src/k) for k in ('score_dev.py','grid_job.py')}}))
  expected=self.d/'expected';expected.write_text('exact')
  bridge.verify_score_replay(expected,src,self.d)
  expected.write_text('altered')
  with self.assertRaises(ValueError): bridge.verify_score_replay(expected,src,self.d)
 def test_tamper(self):
  (self.d/'stdout').write_text('changed');self.assertTrue(m._lex2_native_problems(self.row,self.f,{}))
 def test_unknown(self):
  self.f['unknown_n']=1;self.assertTrue(m._lex2_native_problems(self.row,self.f,{}))
 def test_parity(self):
  self.f['whisper_parity_gate_ref']='';self.assertTrue(m._lex2_native_problems(self.row,self.f,{}))
if __name__=='__main__':unittest.main()
