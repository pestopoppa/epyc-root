import datetime,importlib.util,json,pathlib,sys,tempfile,time
V=pathlib.Path(__file__).resolve().parents[2]/'scripts/vidya'; sys.path.insert(0,str(V))
import claim_tuple as ct, loop_beliefs as lb, ingest_sources
from ledger import Ledger
HERE=pathlib.Path(__file__).resolve().parent
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
p=load('producer',HERE/'df2_fixture_producer.py'); a=ingest_sources.SOURCES['df2-row-exact-akx'].load()
class Sync:
 def status(self,*args): return {'fresh':True,'lag_entries':0,'index_max_id':1,'synced_max_id':1,'last_sync':'2026-10-27T00:00:00Z'}
 def sync(self,*args): raise AssertionError('unexpected sync')
def test_producer_registry_planning_canary():
 with tempfile.TemporaryDirectory() as tmp:
  root=pathlib.Path(tmp); out=root/'out'; out.mkdir(); gpu={'pci':'0000:43:00.0','hip_ordinal_0_pci':'0000:43:00.0','kfd_gpu_id':57300}; (out/'gpu-identity.json').write_text(json.dumps(gpu))
  sentinel=root/'sentinel'; sentinel.write_text('fixture'); manifest=root/'seal'; manifest.write_text(p.sha(sentinel)+'  '+str(sentinel)+'\n'); meta=root/'meta'; meta.write_text('fixture')
  for cell in ('GPU-MM-Q8_0-D27','GPU-MM-Q4_K-D27'):
   for arm in ('off','on'):
    stem=cell+'-'+arm; raw=out/(stem+'.jsonl'); log=out/(stem+'.log'); sam=out/(stem+'.samples.jsonl')
    records=[{'record':'run','backend_bound':'ROCm0','kmax':8,'repeats':3,'seed':'674854'}]
    for sub,(k,n) in enumerate(((5120,17408),(6144,5120),(17408,5120))):
     label=f'D27:W[ne00={k},ne01={n}]'
     for width in range(1,9):
      differs=arm=='off' and width>=2
      records.append({'record':'k','id':cell,'sub':sub,'sub_label':label,'k':width,'status':'OK','digest_batched':['a'*64]*3,'digest_serial':['b'*64 if differs else 'a'*64]*3,'width_differs_by_repeat':[differs]*3,'width_differs':differs,'batched_repeat_stable':True,'serial_repeat_stable':True})
     records.append({'record':'cell','id':cell,'sub':sub,'sub_label':label,'status':'OK','kmax':8,'repeats':3,'unstable_ks':[],'unsupported_ks':[],'err_ks':[],'k1_identity_violation':[],'first_fail_k':2 if arm=='off' else None})
    records.append({'record':'row_done','id':cell}); raw.write_text(''.join(json.dumps(x)+'\n' for x in records))
    log.write_text('GGML_CUDA_DF2_ROW_EXACT active\n' if arm=='on' else 'ordinary route\n'); sam.write_text(''.join(json.dumps({'t_ns':n,'pid':123,'gpu_id':57300,'pid_in_kfd':True,'vram_bytes':1,'process_vram_bytes':1})+'\n' for n in (11,12)))
    rec={'pid':123,'start_ticks':'1','started_ns':10,'ended_ns':13,'reaped':True,'rc':0,'marker':arm=='on','flags':{'GGML_CUDA_DF2_ROW_EXACT':'1' if arm=='on' else None},'raw_sha256':p.sha(raw),'log_sha256':p.sha(log),'samples_sha256':p.sha(sam)}; (out/(stem+'.receipt.json')).write_text(json.dumps(rec))
  side=p.emit(out,'output',{c:'FIXED' for c in ('GPU-MM-Q8_0-D27','GPU-MM-Q4_K-D27')},manifest,manifest,meta,meta,meta,HERE/'df2_fixture_producer.py')
  rows=a.native_rows(side); assert len(rows)==2
  for n in rows: assert ct.grade(a.project(n))[:2]==('Judged','Located')
  as_of=datetime.datetime.now(datetime.timezone.utc).isoformat(); ledger=root/'ledger.jsonl'
  report=ingest_sources.ingest(Ledger(ledger),'df2-row-exact-akx',[side],as_of=as_of)
  assert report['rows_projected']==2 and not report['refused'],report
  config=root/'alarm.yaml'; config.write_text('backend: file\nfile:\n  path: '+str(root/'alarms.jsonl')+'\n')
  ans=lb.prepare('test.df2',{'backend':'gpu','device':'0000:43:00.0','model_file':'fixture.gguf','op':'MUL_MAT','shape':'GPU-MM-Q8_0-D27'},ledger=ledger,index_path=root/'index.yaml',as_of=as_of,sync_module=Sync(),known_good=root/'known.json',alarm_state=root/'alarm.json',alarm_config=config)
  assert ans['status']=='ready',ans
  text=json.dumps(ans['evidence']); assert 'DF2 native' in text,text
  victim=out/'GPU-MM-Q8_0-D27-off.jsonl'; victim.write_text(victim.read_text()+'tampered\n')
  try: a.native_rows(side)
  except ct.ProjectionError: pass
  else: raise AssertionError('raw drift accepted')
  print('PRODUCER_PROJECTOR_PLANNING_CANARY_PASS (synthetic)')
