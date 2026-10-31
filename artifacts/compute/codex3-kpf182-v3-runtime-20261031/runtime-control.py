#!/usr/bin/env python3
import hashlib,json,os,signal,socket,subprocess,threading,time,urllib.request
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/codex3-kpf182-component-proof-20261031'); B=D/'build-cpu/bin'; M='/mnt/raid0/llm/models/unsloth/Qwen3.5-0.8B-GGUF/Qwen3.5-0.8B-Q8_0.gguf'; port=19767
out=D/'runtime-control'; out.mkdir(exist_ok=False)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(M)=='0ad885ffd4bb022fc4f0d33a3308fa108ef8613159d3b3a67e23abca056b7a6c'
for name in ['llama-server','libllama-server-impl.so','libllama.so']:
 assert (B/name).exists()
identity={n:sha(B/n) for n in ['llama-server','libllama-server-impl.so','libllama.so']}; identity['model_sha256']=sha(M)
(out/'IDENTITY.json').write_text(json.dumps(identity,indent=2)+'\n')
with socket.socket() as sock: sock.bind(('127.0.0.1',port))
def req(path,payload=None):
 b=None if payload is None else json.dumps(payload).encode(); request=urllib.request.Request(f'http://127.0.0.1:{port}'+path,data=b,headers={'Content-Type':'application/json'}); return json.loads(urllib.request.urlopen(request,timeout=70).read())
def run(label,trace):
 rd=out/label; rd.mkdir(); log=(rd/'server.log').open('wb'); env={**os.environ,'LD_LIBRARY_PATH':str(B),'KPF182_NATIVE_TRACE':str(trace),'OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'1'}
 argv=[str(B/'llama-server'),'-m',M,'--host','127.0.0.1','--port',str(port),'-ngl','0','-t','2','-tb','2','-c','4096','-np','3','-b','128','-ub','128','--kv-unified','--slot-fork-min-tokens','16','--ctx-checkpoints','8','--cache-ram','0','--no-mmap','--metrics']
 (rd/'argv.json').write_text(json.dumps(argv,indent=2)+'\n'); p=subprocess.Popen(argv,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True); (rd/'pid.json').write_text(json.dumps({'pid':p.pid,'birth':Path(f'/proc/{p.pid}/stat').read_text().split(') ')[1].split()[19]})+'\n')
 peak=[0]; stop=threading.Event()
 def sample():
  while not stop.wait(.1):
   try:
    for ln in Path(f'/proc/{p.pid}/status').read_text().splitlines():
     if ln.startswith('VmRSS:'):
      own_rss=0
      for own in Path("/proc/self/status").read_text().splitlines():
       if own.startswith("VmRSS:"): own_rss=int(own.split()[1])*1024
      peak[0]=max(peak[0],int(ln.split()[1])*1024+own_rss)
      if peak[0]>7*1024**3: os.kill(p.pid,signal.SIGTERM)
    children=Path(f"/proc/{p.pid}/task/{p.pid}/children").read_text().strip()
    if children: os.kill(p.pid,signal.SIGTERM); break
   except (OSError,ProcessLookupError): break
 th=threading.Thread(target=sample,daemon=True); th.start()
 try:
  deadline=time.monotonic()+100
  while time.monotonic()<deadline:
   if p.poll() is not None: raise RuntimeError('server exited before ready')
   try:
    if req('/health').get('status')=='ok': break
   except Exception: time.sleep(.3)
  else: raise RuntimeError('health timeout')
  maps=Path(f'/proc/{p.pid}/maps').read_text(); (rd/'maps.txt').write_text(maps)
  for lib in ['libllama-server-impl.so','libllama.so']:
   assert any(str(B) in line and lib in line for line in maps.splitlines()),f'missing own mapping {lib}'
  tokens=req('/tokenize',{'content':('Amber willow river lantern. '*50),'add_special':False})['tokens']; assert 64<len(tokens)<1800
  source=tokens+tokens[:12]; child=tokens+tokens[12:24]; print(label,'prefix_length',len(tokens),flush=True)
  inputs=[('source',0,source,[len(tokens)],0),('child1',1,child,None,8),('child2',2,child,None,8)]
  for name,slot,prompt,ckpt,n in inputs:
   body={'prompt':prompt,'id_slot':slot,'cache_prompt':True,'n_predict':n,'temperature':0,'seed':42,'return_tokens':True}
   if ckpt is not None: body['checkpoint_at']=ckpt
   (rd/(name+'.started')).write_text(json.dumps({'slot':slot,'prompt_sha256':hashlib.sha256(json.dumps(prompt).encode()).hexdigest(),'n_tokens':len(prompt)})+'\n')
   result=req('/completion',body); (rd/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n')
   if result.get('id_slot')!=slot: raise RuntimeError(f'{name}: wrong slot')
  (rd/'COMPLETE').write_text('all three HTTP responses saved\n')
 finally:
  if p.poll() is None: p.send_signal(signal.SIGTERM)
  try: rc=p.wait(timeout=20)
  except subprocess.TimeoutExpired: p.kill(); rc=p.wait(timeout=10)
  stop.set(); th.join(timeout=2);log.close();(rd/'cleanup.json').write_text(json.dumps({'pid':p.pid,'returncode':rc,'verified_dead':p.poll() is not None,'sampled_peak_server_plus_supervisor_rss_bytes':peak[0]},indent=2)+'\n')
run('trace-off',0);run('trace-on',1)
for name in ['source','child1','child2']:
 a=json.loads((out/'trace-off'/f'{name}.json').read_text());b=json.loads((out/'trace-on'/f'{name}.json').read_text());
 (out/(name+'-comparison.json')).write_text(json.dumps({'off_content':a.get('content'),'on_content':b.get('content'),'off_tokens':a.get('tokens'),'on_tokens':b.get('tokens'),'content_equal':a.get('content')==b.get('content'),'tokens_present':isinstance(a.get('tokens'),list) and isinstance(b.get('tokens'),list),'tokens_equal':a.get('tokens')==b.get('tokens')},indent=2)+'\n')
print('comparison complete',flush=True)
