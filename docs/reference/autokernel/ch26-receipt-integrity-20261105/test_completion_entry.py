import json, pathlib, tempfile, unittest
from unittest.mock import patch
import complete
from census_receipt import write_receipt, read_event, create_intent
from floor_binding import bind_request_boundaries
from test_floor_binding import fixture, expected_request

class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=pathlib.Path(self.tmp.name)
 def make_fixture(self):
  row,events,prompts,prepared=fixture(self.root); native={}
  (self.root/'build-runtime-prepared.json').write_text(json.dumps(prepared))
  for e in events:
   target=e['target']; e['before']['monotonic_ns']=1;e['after']['monotonic_ns']=3
   task={'pid':target['pid'],'tid':target['pid'],'start_ticks':target['start_ticks'],'identity_stable':True,'cpu_ticks':0,'allowed_cpus':[0]}
   sample={'errors':[],'census_complete':True,'truncated':False,'boot_id':target['boot_id'],'target':dict(target,identity_stable=True),'scan_start':0.,'monotonic_s':0.,'scan_end':1e-9,'tasks':[task]}
   census={'schema':'akagg.cpu-observation-candidate.v1','collector_visibility':'unverified','request_start':0.,'request_end':1.0,'policy_observation':{'measurement_admission':'none'},'request_phase_collector':{'schema':'akagg.request-phase-collector.v1','status':'unproven','placement':'unproven','contention':'unproven','errors':[]},'samples':[sample]}
   context={k:e[k] for k in ('launch_ordinal','phase','slot_index','prompt_id','request_sha256')}
   receipt=self.root/f"census-{e['launch_ordinal']}-{e['phase']}"
   create_intent(str(receipt)+'.intent',receipt_path=receipt,target=target,placement_window_ns=e['placement_window_ns'],request_context=context)
   e['host_census']=write_receipt(receipt,row=census,target=target,placement_window_ns=e['placement_window_ns'],request_context=context)
   e['measurement_admission']='none'
   ob=e['native_observer'];native[ob['evidence_path']]={'measurement_admission':'none','errors':[],'markers':ob['markers'],'target_observations':ob['target_observations']}
  floor=bind_request_boundaries(row,events,prompts,runtime_prepared=prepared);(self.root/'floor.json').write_text(json.dumps(floor))
  out=self.root/'input/full';out.mkdir(parents=True)
  (self.root/'input/verification-pin.json').write_text(json.dumps({'request':expected_request(prompts,row),'calibration_plan':row['calibration_plan']}))
  (out/'request-boundaries.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
  summary={'schema':'epyc.ds41_1017.calibrate_summary.v1','aa_pairs':24,'cmp_pairs':5,'unit':'process','build':'/mnt/raid0/llm/kernels/builds/cpu-20261024-c72ec82f5-c5','floor_file':str(self.root/'floor.json'),'floor_content_sha256':floor['content_sha256']}
  (out/'calibrate-summary.json').write_text(json.dumps(summary))
  return events,native
 def test_main_reads_all_census_receipts_and_refuses_missing(self):
  events,native=self.make_fixture()
  def raw(path,digest): return json.dumps(native[path]).encode(),None
  with patch.object(complete,'D',self.root),patch.object(complete,'read_receipt',side_effect=raw),patch.object(complete,'validate_source_census'):
   self.assertTrue(complete.main())
   pathlib.Path(events[0]['host_census']['path']).unlink()
   with self.assertRaises(FileNotFoundError): complete.main()
 def test_main_refuses_missing_intent_and_duplicate_journal(self):
  events,native=self.make_fixture()
  def raw(path,digest): return json.dumps(native[path]).encode(),None
  with patch.object(complete,'D',self.root),patch.object(complete,'read_receipt',side_effect=raw),patch.object(complete,'validate_source_census'):
   intent=pathlib.Path(events[0]['host_census']['path']+'.intent'); saved=intent.read_bytes(); intent.unlink()
   with self.assertRaises(FileNotFoundError):complete.main()
   intent.write_bytes(saved)
   journal=self.root/'input/full/request-boundaries.jsonl'
   with journal.open('a') as f:f.write(json.dumps(events[0])+'\n')
   with self.assertRaisesRegex(ValueError,'ambiguous'):complete.main()
 def test_file_and_parent_symlink_refused(self):
  events,_=self.make_fixture();e=events[0];real=pathlib.Path(e['host_census']['path'])
  alias=self.root/'alias';alias.symlink_to(real)
  e['host_census']['path']=str(alias)
  with self.assertRaises(OSError):read_event(e)
  directory=self.root/'aliasdir';directory.symlink_to(self.root,target_is_directory=True)
  e['host_census']['path']=str(directory/real.name)
  with self.assertRaisesRegex(ValueError,'noncanonical'):read_event(e)
if __name__=='__main__':unittest.main()
