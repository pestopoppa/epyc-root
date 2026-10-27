import hashlib,json,sys,tempfile
from pathlib import Path
from datetime import datetime,timezone
D=Path(__file__).resolve().parent;sys.path.insert(0,str(D/'private/vidya'))
from adapters import chat_template_ab_capture as cap
from ledger import Ledger
import ingest_sources,loop_beliefs
class Fresh:
 def status(self,ledger,index): return {'fresh':True,'lag_entries':0}
with tempfile.TemporaryDirectory(dir=D/'tmp') as temp:
 p=Path(temp);run=p/'run';run.mkdir()
 for arm in (0,1):(run/f'results_arm{arm}.jsonl').write_text('{"id":"synthetic"}\n')
 marker={'profile':'ct21-direct-exploratory-v1','profile_path':str(D/'DIAGNOSTIC-PROFILE.md'),'source_path':str(D/'direct_diagnostic.py'),'profile_sha256':hashlib.sha256((D/'DIAGNOSTIC-PROFILE.md').read_bytes()).hexdigest(),'source_sha256':hashlib.sha256((D/'direct_diagnostic.py').read_bytes()).hexdigest()}
 cap.write_belief_measurements(run,run_id='synthetic-direct-canary',producer='synthetic',model_path='/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf',model_name='Qwen3.8-27B',quant='Q8_0',kernel={'source_commit':'a'*40,'binary_version':'1'},serving={'mode':'test_port'},sampling={'temperature':0,'seed':7},arms={0:{'label':'OFF','template_sha256':'b'*64},1:{'label':'ON','template_sha256':'b'*64}},summary={'arithmetic':{'arm0':{'n':1,'correct':1,'truncated':0,'errors':0},'arm1':{'n':1,'correct':1,'truncated':0,'errors':0}}},exploratory=marker)
 now=datetime.now(timezone.utc).isoformat();ledger=Ledger(p/'ledger.jsonl');report=ingest_sources.ingest(ledger,'chat-template-ab',[run],as_of=now)
 assert report['rows_projected']==2 and report['frames_emitted']>0
 now=datetime.now(timezone.utc).isoformat();ans=loop_beliefs.prepare('ct21.synthetic.canary',{'model_file':'Qwen3.8-27B-Q8_0.gguf','quant':'Q8_0','backend':'gpu','device':'gfx90a'},ledger=p/'ledger.jsonl',index_path=p/'index',as_of=now,sync_module=Fresh(),known_good=p/'known_good.json',alarm_state=p/'alarms.json',alarm_config=p/'alarm.yaml',read_log=p/'reads.jsonl')
 print(json.dumps({'synthetic_only':True,'ingest':report,'prepare_status':ans['status'],'evidence':ans.get('evidence')},default=str))
 assert ans['status']=='ready'
 assert len(ans['evidence']['claim_ids'])==2 and 'synthetic-direct-canary' in ans['evidence']['section']
 assert ans['evidence']['tried_index_count']==0  # no invented do-not-repeat history
