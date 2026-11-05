#!/usr/bin/env python3
"""Generate sealed synthetic fixtures only. Does not execute the validator."""
import copy,hashlib,json
from pathlib import Path
R=Path(__file__).parent/'controls';R.mkdir(exist_ok=True)
def put(p,x):
    data=(json.dumps(x,sort_keys=True,indent=2)+'\n') if not isinstance(x,str) else x
    p.write_text(data);return hashlib.sha256(data.encode()).hexdigest()
p={'source_commit':'1e8a6d5da9836a27e8f1d2010a02e6cebd95abdc','drafter':'DFlash2','device':'SYNTHETIC-GPU','dso_sha256':{'libggml-hip.so':'1'*64},'dispatch_families':{'synthetic_attention':'attention'}}
for k in ('server_sha256','model_sha256','drafter_sha256','argv_sha256','prompt_sha256'):p[k]='2'*64
put(R/'expected.json',p)
m={'schema':'epyc.kpf50.native-window.v1','identity':p,'synthetic':True,'window_index':0,'mode':'full','complete':True,'partial':False,'fresh_model':True,'pid':123,'pid_birth':'SYNTHETIC-BIRTH','attempt_start_ns':1,'artifacts':{}}
def add(k,v):
    name=k+'.txt';h=put(R/name,v);m['artifacts'][k]={'path':name,'sha256':h}
log=['KPF50_ITER_BEGIN iter=1 host_ns=100 draft_context=1','KPF50_DRAFT_BEGIN host_ns=110 slots=4','KPF50_DRAFT_END host_ns=120 slots=4']
for i in range(4):log += [f'KPF30_PHASE call=1 index={i} seq={i} pos=79999 phase=decode',f'KPF50_INPUT call=1 index={i} token={i+1} pos=79999']
log+=['KPF50_STEP_BEGIN call=1 host_ns=200','KPF50_TRUNK_MASK verified=1 masked=0 rows=4 n_kv=80000 expected=60000 layout_fnv=abcdef','KPF50_STEP_END call=1 host_ns=400 rc=0','KPF50_ITER_END iter=1 host_ns=500']
add('server_log','\n'.join(log)+'\n')
children=[{'role':'child','http':200,'error':None,'suffix_index':i,'seq_id':i,'context_tokens':80000,'trunk_tokens':60000,'suffix_tokens':20000,'timings':{'n_fork_tokens':60000}} for i in range(4)]
add('children',children);add('shape',[{k:c[k] for k in ('seq_id','context_tokens','trunk_tokens','suffix_tokens')} for c in children])
add('process_maps',dict(pid=123,pid_birth='SYNTHETIC-BIRTH',host_ns=250,**{k:p[k] for k in ('server_sha256','model_sha256','drafter_sha256','dso_sha256')}))
add('residency',[{'pid':123,'pid_birth':'SYNTHETIC-BIRTH','host_ns':t,'kfd':True,'vram_bytes':1,'device':'SYNTHETIC-GPU'} for t in (250,300)])
def clock(t):return {'schema':'epyc.kpf50.hsa-clock.v1','frequency_hz':1000000000,'samples':[{'host_before_ns':t,'host_after_ns':t,'hsa_ticks':t}]}
for k,t in [('clock_before',90),('clock_after',510),('smoke_before',10),('smoke_after',80)]:add(k,clock(t))
add('smoke_log','KPF50_CLOCK_WITNESS begin_ns=20 end_ns=70\n');add('smoke_csv','KernelName,BeginNs,EndNs\nkpf50_clock_witness,30,60\n');add('dispatch_csv','KernelName,BeginNs,EndNs\nsynthetic_attention,220,380\n')
put(R/'window.json',m)
mutations=[('missing_clock',['artifacts','clock_before'],None),('mixed_phase',['artifacts','server_log'],None),('wrong_candidate',['identity','source_commit'],'bad'),('incomplete',['complete'],False),('wrong_order',['mode'],'mask'),('native_unproved',['synthetic'],False)]
# Patches describe isolated controls; all are sealed and intentionally not executed.
put(R/'mutations.json',[{'name':n,'path':path,'value':v,'expected':'UNKNOWN' if n=='native_unproved' else 'REFUSE','operation':'remove' if v is None else 'replace'} for n,path,v in mutations])
put(R/'seals.json',{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(R.iterdir()) if f.name!='seals.json'})
