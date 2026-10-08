"""Prospective original off-host controls: actual accepted writer → strict reader.

No tests or APP imports are executed during private preparation.
"""
import hashlib,importlib.util,json,os,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts/vidya"))
from adapters import hg5_request_event as reader
from claim_tuple import ProjectionError

class ReaderControls(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.directory=Path(self.temp.name);self.directory.chmod(0o700)
  source=Path(os.environ['HG5_WRITER_SOURCE']);self.source=source;assert hashlib.sha256(source.read_bytes()).hexdigest()in (reader.PRODUCER_SHA256,reader.PRODUCER_V2_SHA256)
  spec=importlib.util.spec_from_file_location('native_hg5_writer',source);self.writer=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.writer)
 def event(self,*,calls=1,unknown=False,failed=False,source_context=False):
  owner=SimpleNamespace(total_calls=0,total_prompt_tokens_reported=0,total_tokens_generated=0,total_prompt_eval_ms=0,total_generation_ms=0)
  context=json.dumps({'commit':'974cb4017791a5d500269fd44f7d9903528e1d5d','tree':'809ec3aa77a12e577643664e0405e9529428c885','producer_sha256':hashlib.sha256(self.source.read_bytes()).hexdigest()}) if source_context else ''
  with patch.dict(os.environ,{'HG5_REQUEST_EVENT_DIRECTORY':str(self.directory),'HG5_REQUEST_EVENT_SOURCE_CONTEXT':context}):capture=self.writer.begin_capture()
  capture.update(feature_enabled=True,stage='direct',step_before=self.writer.snapshot(owner))
  owner.total_calls=calls;owner.total_prompt_tokens_reported=7;owner.total_tokens_generated=3;owner.total_prompt_eval_ms=1.5;owner.total_generation_ms=2.5
  if unknown:owner=None
  self.writer.record_step(capture,owner,trigger='caller_forced',initial_role='frontdoor',target_role='architect_general',outcome='failed' if failed else 'adopted')
  plan=SimpleNamespace(requested='force_architect_general',enabled=True,disabled_reason=None,from_role='frontdoor',final_answer_role='frontdoor' if failed else 'architect_general',target_role='architect_general',error='bounded' if failed else None)
  return self.writer.finish_capture(capture,request_id='synthetic-owned-request',plan=plan,counters=self.writer.snapshot(owner),failure_type='RuntimeError' if failed else None)
 def mutate(self,path,change,*,reseal=True):
  doc=json.loads(path.read_bytes());change(doc['body'])
  if reseal:doc['body_sha256']=hashlib.sha256(self.writer.canonical(doc['body'])).hexdigest()
  path.write_bytes(self.writer.canonical(doc)+b'\n');return path
 def refuses(self,path):
  with self.assertRaises(ProjectionError):reader.native_rows(path)
 def test_actual_writer_registered_source_preserves_ungraded_facts(self):
  from ingest_sources import SOURCES
  source=SOURCES['hg5-request-event'];path=self.event();self.assertEqual(source.units(self.directory),[path]);rows=source.load().native_rows(path);self.assertEqual(len(rows),5);self.assertEqual(source.load().AUTHORITY,'measurement')
  for row in rows:
   self.assertEqual(row['envelope']['body']['runtime_origin'],'unknown')
   with self.assertRaisesRegex(ProjectionError,'producer category, metric_direction and protocol_id declarations absent'):source.load().project(row)
 def test_unknown_native_counters_decline_without_legacy_zero(self):self.assertEqual(reader.native_rows(self.event(unknown=True)),())
 def test_observed_zero_call_count_is_not_adoption_outcome(self):
  row=reader.native_rows(self.event(calls=0))[0];self.assertEqual(row['envelope']['body']['steps'][0]['delta']['calls'],0);self.assertEqual(row['envelope']['body']['steps'][0]['outcome'],'adopted');self.assertEqual(row['envelope']['body']['steps'][0]['call_status'],'not_called')
 def test_force_failure_native_bounded_fallback_fact(self):
  body=reader.native_rows(self.event(failed=True))[0]['envelope']['body'];self.assertEqual(body['final_role'],'frontdoor');self.assertEqual(body['steps'][0]['outcome'],'failed');self.assertEqual(body['failure']['exception_type'],'RuntimeError')
 def test_partial_nullable_metric_declines_only_missing_metric(self):
  def change(b):
   b['steps'][0]['after']['prompt_ms']=None;b['steps'][0]['delta']['prompt_ms']=None
  rows=reader.native_rows(self.mutate(self.event(),change));self.assertEqual(len(rows),4);self.assertNotIn('prompt_ms',[r['metric_key'] for r in rows])
 def test_native_counter_reset_preserves_unknown(self):
  def change(b):
   s=b['steps'][0];s['before']['calls']=2;s['after']['calls']=1;s['delta']['calls']=None;s['call_status']='unknown'
  rows=reader.native_rows(self.mutate(self.event(),change));self.assertNotIn('calls',[r['metric_key'] for r in rows])
 def test_no_step_actual_writer_disabled_event_declines(self):
  with patch.dict(os.environ,{'HG5_REQUEST_EVENT_DIRECTORY':str(self.directory),'HG5_REQUEST_EVENT_SOURCE_CONTEXT':''}):c=self.writer.begin_capture()
  c['feature_enabled']=False;p=SimpleNamespace(requested='off',enabled=False,disabled_reason='explicit_off',from_role='frontdoor',final_answer_role=None,target_role=None,error=None)
  self.assertEqual(reader.native_rows(self.writer.finish_capture(c,request_id='disabled',plan=p,counters=self.writer.snapshot(None))),())
 def test_body_tampering_without_new_seal_refuses(self):self.refuses(self.mutate(self.event(),lambda b:b.update(final_role='other'),reseal=False))
 def test_resealed_semantic_inconsistency_refuses(self):
  changes=[lambda b:b['steps'][0]['delta'].update(calls=2),lambda b:b['steps'][0]['before'].update(calls=True),lambda b:b['request_counters_at_capture'].update(prompt_ms=-1),lambda b:b['steps'].append(dict(b['steps'][0])),lambda b:b['steps'][0].update(initial_role='other'),lambda b:b.update(final_role='frontdoor'),lambda b:b['steps'][0].update(call_status='not_called'),lambda b:b.update(requested_mode='auto'),lambda b:b.update(eligible=False),lambda b:b['failure'].update(message='raw diagnostic'),lambda b:b['source'].update(commit='a'*40),lambda b:b.update(runtime_origin='verified'),lambda b:b['window'].update(end_monotonic_ns=0)]
  # One whole test case, all named mutations asserted; no extra inferred case IDs.
  for n,change in enumerate(changes):
   with self.subTest(native_mutation=n):self.refuses(self.mutate(self.event(),change))
 def test_native_mode_and_hardlink_custody_refuses(self):
  path=self.event();path.chmod(0o644);self.refuses(path);path.chmod(0o600);os.link(path,self.directory/'second.json');self.refuses(path)
 def test_native_terminal_and_parent_symlink_refuses(self):
  path=self.event();alias=self.directory/'alias.json';alias.symlink_to(path);self.refuses(alias)
  with tempfile.TemporaryDirectory() as d:
   alias=Path(d)/'alias';alias.symlink_to(self.directory,target_is_directory=True);self.refuses(alias/path.name)
 def test_duplicate_json_key_refuses(self):
  path=self.event();raw=path.read_bytes();path.write_bytes(raw.replace(b'"body":{',b'"body":{},"body":{',1));self.refuses(path)
 def test_mapping_cannot_fabricate_attestation(self):
  row=reader.native_rows(self.event())[0];row['artifact_sha256']='0'*64
  with self.assertRaises(ProjectionError):reader.project(row)
 def test_actual_writer_source_context_never_proves_loaded_runtime(self):
  path=self.event(source_context=True);body=reader.native_rows(path)[0]['envelope']['body'];self.assertEqual(body['source']['origin'],'source_authored_run_context');self.assertEqual(body['runtime_origin'],'unknown')
  self.refuses(self.mutate(path,lambda b:b['source'].update(producer_sha256='a'*64)))
 def test_nonfinite_json_number_and_unknown_extra_key_refuse(self):
  path=self.event();path.write_bytes(path.read_bytes().replace(b'1.5',b'NaN'));self.refuses(path)
  self.refuses(self.mutate(self.event(),lambda b:b.update(extra='unexpected')))
 def test_actual_cli_refuses_unlabelled_native_cost_without_ledger_rows(self):
  import cli,contextlib,io
  from ledger import Ledger
  path=self.event();ledger=self.directory/'ledger.jsonl';capture=io.StringIO()
  with contextlib.redirect_stdout(capture):rc=cli.main(['--ledger',str(ledger),'--json','ingest','hg5-request-event','--path',str(path),'--as-of','2099-01-01T00:00:00Z'])
  self.assertEqual(rc,0);report=json.loads(capture.getvalue());self.assertEqual(report['rows_projected'],0);self.assertTrue(report['refused']);self.assertIn('producer category',report['refused'][0]['reason']);self.assertEqual(report['frames_emitted'],0);self.assertTrue(not ledger.exists() or not list(Ledger(ledger).read_all()))
 def test_adopted_step_cannot_carry_failure_status(self):
  self.refuses(self.mutate(self.event(),lambda b:b['failure'].update(status='request_failed',exception_type='RuntimeError')))
 def v2_event(self, *, protocol='', category='CANDIDATE'):
  context={'commit':'1'*40,'tree':'2'*40,'producer_sha256':hashlib.sha256(self.source.read_bytes()).hexdigest(),'projection':{'category':category,'metric_direction':{k:'lower_better' for k in self.writer.COUNTERS},'protocol_id':protocol}}
  with patch.dict(os.environ,{'HG5_REQUEST_EVENT_DIRECTORY':str(self.directory),'HG5_REQUEST_EVENT_SOURCE_CONTEXT':json.dumps(context)}):capture=self.writer.begin_capture()
  owner=SimpleNamespace(total_calls=0,total_prompt_tokens_reported=0,total_tokens_generated=0,total_prompt_eval_ms=0,total_generation_ms=0)
  capture.update(feature_enabled=True,stage='direct',step_before=self.writer.snapshot(owner));owner.total_calls=1;owner.total_prompt_tokens_reported=3;owner.total_tokens_generated=2;owner.total_prompt_eval_ms=1.0;owner.total_generation_ms=2.0
  self.writer.record_step(capture,owner,trigger='caller_forced',initial_role='frontdoor',target_role='architect_general',outcome='adopted')
  plan=SimpleNamespace(requested='force_architect_general',enabled=True,disabled_reason=None,from_role='frontdoor',final_answer_role='architect_general',target_role='architect_general',error=None)
  return self.writer.finish_capture(capture,request_id='synthetic-v2',plan=plan,counters=self.writer.snapshot(owner))
 def test_v2_actual_predeclared_empty_protocol_yields_shared_observation(self):
  from claim_tuple import grade
  rows=reader.native_rows(self.v2_event());self.assertEqual(len(rows),5)
  for row in rows:
   item=reader.project(row);self.assertEqual(item.category,'CANDIDATE');self.assertEqual(item.metric_direction,'lower_better');self.assertEqual(item.protocol_id,'');self.assertEqual(grade(item)[:2],('Judged','Located'));self.assertEqual(item.extra['protocol_human_ratification'],'not_asserted');self.assertEqual(item.extra['runtime_origin'],'unknown')
 def test_v2_native_citation_copied_without_ratification_claim(self):
  path=self.v2_event(protocol='synthetic:cost-fixture-v2');row=reader.native_rows(path)[0];item=reader.project(row);self.assertEqual(item.protocol_id,'synthetic:cost-fixture-v2');self.assertEqual(item.extra['protocol_human_ratification'],'not_asserted')
 def test_v2_unsealed_declaration_change_refuses(self):
  self.refuses(self.mutate(self.v2_event(),lambda b:b['projection']['declaration'].update(category='BASELINE')))
 def test_v2_missing_native_label_refuses(self):
  self.refuses(self.mutate(self.v2_event(),lambda b:b['projection']['declaration'].pop('protocol_id')))
 def test_v2_wrong_direction_refuses(self):
  self.refuses(self.mutate(self.v2_event(),lambda b:b['projection']['declaration']['metric_direction'].update(calls='unknown')))
 def test_v2_cannot_claim_human_ratification_or_runtime(self):
  self.refuses(self.mutate(self.v2_event(),lambda b:b['projection'].update(human_ratification='ratified')))
  self.refuses(self.mutate(self.v2_event(),lambda b:b.update(runtime_origin='verified')))
 def test_v2_actual_cli_records_native_labelled_counter_rows(self):
  import cli,contextlib,io
  from ledger import Ledger
  path=self.v2_event();ledger=self.directory/'v2-ledger.jsonl';capture=io.StringIO()
  with contextlib.redirect_stdout(capture):rc=cli.main(['--ledger',str(ledger),'--json','ingest','hg5-request-event','--path',str(path),'--as-of','2099-01-01T00:00:00Z'])
  self.assertEqual(rc,0);report=json.loads(capture.getvalue());self.assertEqual(report['refused'],[]);self.assertEqual(report['rows_projected'],5);self.assertEqual(report['frames_emitted'],15);self.assertEqual(len(list(Ledger(ledger).read_all())),15)
