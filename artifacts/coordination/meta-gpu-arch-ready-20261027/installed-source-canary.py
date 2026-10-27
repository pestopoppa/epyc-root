#!/usr/bin/env python3
import hashlib,importlib.util,json,sys
from pathlib import Path
from datetime import datetime,timezone,timedelta
D=Path('/mnt/raid0/llm/tmp/codex-ni-20261027-meta-gpu-arch-ready/packet'); O=D.parent/'installed-source-canary'; O.mkdir(exist_ok=False)
root=Path('/mnt/raid0/llm/views/epyc-root-main');sys.path.insert(0,str(root/'scripts/vidya'))
from adapters import speech_ggml_optest as a
from ledger import Ledger
import ingest_sources,loop_beliefs
spec=importlib.util.spec_from_file_location('meta_writer',D/'monitor.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
for name in ('stdout','stderr','linkage.log'): (O/name).write_text('synthetic control only')
(O/'residency.jsonl').write_text(''.join(json.dumps({'pid':1,'start_ticks':'42','time_ns':2,'kfd_gpu_id':2,'pid_in_kfd':True,'vram_bytes':5})+'\n' for _ in range(2)))
raw={name:hashlib.sha256((O/name).read_bytes()).hexdigest() for name in ('stdout','stderr','linkage.log','residency.jsonl')}
(O/'results.json').write_text(json.dumps({'schema':'epyc.model_free_backend_correctness.v1','source_commit':'520ad4f55d805a544862be88d652ec68fcd194ab','source_seal_sha256':'b'*64,'binding_sha256':'c'*64,'pid':1,'start_ticks':'42','start_ns':1,'end_ns':3,'kfd_gpu_id':2,'reaped':True,'gates':{'fixture_process_rc':0,'meta_moe_nmse':'OK','positive_device_samples':2},'raw_sha256':raw})+'\n')
f={'backend':'ROCm0','device_arch':'gfx90a','op':'qwen4exp-meta-moe-nmse','binary_sha256':'a'*64,'source_seal_sha256':'b'*64,'binding_sha256':'c'*64,'residency_proof':'synthetic-only','positive_device_samples':2,'suite_case_count':1,'n_failed':0,'tree':{'commit':'520ad4f55d805a544862be88d652ec68fcd194ab'}}
sidecar=m.emit_native(a,O,f); ledger=Ledger(O/'ledger.jsonl'); asof=(datetime.now(timezone.utc)+timedelta(seconds=10)).isoformat()
report=ingest_sources.ingest(ledger,'speech-ggml-optest',[sidecar],as_of=asof); (O/'ingest.json').write_text(json.dumps(report,indent=2)+'\n'); assert report['rows_projected']==1 and report['frames_emitted']>0
# The independent history below is explicitly synthetic and never leaves this scratch ledger.
testspec=importlib.util.spec_from_file_location('fixture_history',root/'tests/vidya/test_loop_beliefs.py'); fixture=importlib.util.module_from_spec(testspec); testspec.loader.exec_module(fixture)
for frame in fixture._loop('synthetic-history',model='synthetic-qwen4exp',quant='',backend='gpu',device='gfx90a',mech='synthetic-do-not-repeat',outcome='null'): ledger.append(frame)
class Sync:
 @staticmethod
 def status(*args,**kwargs): return {'fresh':True,'index':'synthetic-only','index_sha256':'d'*64}
class Alarm:
 def clear(self,*args,**kwargs): return None
answer=loop_beliefs.prepare('autokernel',{'model_file':'synthetic-qwen4exp','backend':'gpu','device':'gfx90a'},ledger=O/'ledger.jsonl',as_of=asof,sync_module=Sync(),known_good=O/'known-good.json',read_log=O/'read.jsonl',alarm_state=O/'alarm.json',alarm_api=Alarm())
(O/'prepare.json').write_text(json.dumps(answer,indent=2,default=str)+'\n'); print(json.dumps({'ingest':report,'prepare_status':answer['status'],'evidence':answer.get('evidence')},default=str)); assert answer['status']=='ready' and 'synthetic-do-not-repeat' in answer['evidence']['section'] and answer['evidence']['tried_index_count'] > 0 and len(answer['evidence']['host_claim_ids']) == 1
