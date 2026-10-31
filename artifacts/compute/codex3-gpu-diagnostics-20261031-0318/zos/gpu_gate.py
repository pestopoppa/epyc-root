#!/usr/bin/env python3
"""GPU-ZOS-2.3 native server and request collector. Verdict: analyze_gate.py."""
import argparse,datetime,hashlib,json,os,pathlib,re,shutil,signal,socket,subprocess,sys,threading,time,urllib.request
D=pathlib.Path('/mnt/raid0/llm/tmp/codex-ni-gpu-zos-build-prep-20261031/successor'); G=D/'gpu'; OUT=G/'out'; OUT.mkdir(parents=True,exist_ok=True)
C5=pathlib.Path('/mnt/raid0/llm/kernels/builds/gpu-20261024-c72ec82f5-c5'); CAND=D/'out/release'; DEBUG=D/'out/debug'
REC=pathlib.Path('/mnt/raid0/llm/epyc-orchestrator/logs/server_launches/8083.json'); REC_SHA='612323d93632856a923b2d163b7486b9e48e87645f41b16e0602260667c33149'; PORT=18398
PROMPTS=json.loads((G/'prompts.json').read_text()); WARM_PROMPTS=[f'Write a short paragraph about GPU-ZOS warmup #{i}; this prompt is excluded. (warmup stream {i})' for i in range(4)]; PROMPT_SHA='5b2c9febc28cc0c6cb1ea7e998696f927449c687feeb44ed8b3f0c341e079bf6'
MODELS=[pathlib.Path('/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf'),pathlib.Path('/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf')]
stop=False; proc=None
class WindowEnd(Exception):pass

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(path,data):
 tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,indent=2)+'\n');os.replace(tmp,path)
def pin_model(p):
 n=p.stat().st_size;h=hashlib.sha256()
 with p.open('rb') as f:
  h.update(f.read(min(n,64*1024*1024)));f.seek(max(0,n-64*1024*1024));h.update(f.read())
 h.update(str(n).encode());return {'path':str(p),'size':n,'edge_sha256':h.hexdigest()}
def free_vram():
 c=pathlib.Path('/sys/class/drm/card2/device');return int((c/'mem_info_vram_total').read_text())-int((c/'mem_info_vram_used').read_text())
def own_vram(pid):
 p=pathlib.Path(f'/sys/class/kfd/kfd/proc/{pid}');v=0
 for f in p.glob('vram_*'):
  try:v+=int(f.read_text())
  except (OSError,ValueError):pass
 return v

def drain_prior():
 for _ in range(18):
  if free_vram()>=50*2**30:
   time.sleep(5)
   if free_vram()>=50*2**30:return
  time.sleep(5)
 raise RuntimeError('VRAM free <50GiB twice before launch')

def port_free():
 s=socket.socket();s.settimeout(.2)
 try:return s.connect_ex(('127.0.0.1',PORT))!=0
 finally:s.close()

def request(body,timeout=600):
 req=urllib.request.Request(f'http://127.0.0.1:{PORT}/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=timeout) as r:
  raw=r.read();return json.loads(raw),hashlib.sha256(raw).hexdigest(),r.status

def check_shape(argv,cpus):
 a=list(argv); srv=a[7:]
 assert a[:4]==['numactl','--membind=3','--','taskset'] and a[4]=='-c' and a[5]=='184-191'
 assert a[6].endswith('/bin/llama-server')
 def val(k):return srv[srv.index(k)+1]
 want={'-np':'4','-c':'393216','-t':'8','-b':'512','-ub':'512','--spec-type':'draft-dflash','--spec-draft-n-max':'7','-ctk':'q8_0','-ctv':'q8_0','--device':'ROCm0','--device-draft':'ROCm0','-m':str(MODELS[0]),'-md':str(MODELS[1])}
 for k,v in want.items():assert val(k)==v,(k,val(k),v)
 assert '--kv-unified' in a and '--no-mmap' in a
 a[5]=cpus
 return a

def make_body(prompt,n):
 return {'messages':[{'role':'user','content':prompt}],'max_tokens':n,'temperature':0.0,'seed':1234,'ignore_eos':True,'chat_template_kwargs':{'enable_thinking':False},'stream':False,'return_tokens':True,'verbose':True,'cache_prompt':False,'n_probs':0}

def launch(arm,image,knob,cpus):
 global proc
 drain_prior();assert port_free(),'port busy'
 env=os.environ.copy();env['LD_LIBRARY_PATH']=f'{image}/bin:/opt/rocm/lib';env['HSA_OVERRIDE_CPU_AFFINITY_DEBUG']='0'
 for k in ('GGML_CUDA_DISABLE_GRAPHS','LLAMA_SPEC_EXACT','LLAMA_ZOS2'):env.pop(k,None)
 if knob is not None:env['LLAMA_ZOS2']=knob
 a=check_shape(json.loads(REC.read_text())['argv'],cpus);a[6]=str(image/'bin/llama-server')
 i=a.index('--port',7);a[i+1]=str(PORT);i=a.index('--slot-save-path',7);slots=OUT/arm/'slots';slots.mkdir(parents=True,exist_ok=True);a[i+1]=str(slots)
 image_pins=json.loads((OUT/'IMAGE-PINS.json').read_text())
 key='c5' if image==C5 else ('debug' if image==DEBUG else 'release')
 assert sha(image/'bin/llama-server')==image_pins[key]['llama_server_sha256'],(arm,key,'binary changed')
 assert sha(image/'bin/libllama-server-impl.so')==image_pins[key]['server_impl_sha256'],(arm,key,'server impl changed')
 armout=OUT/arm;armout.mkdir(parents=True,exist_ok=True)
 log=(armout/'server.log').open('wb');proc=subprocess.Popen(a,stdout=log,stderr=subprocess.STDOUT,env=env)
 p=proc.pid;birth=int(pathlib.Path(f'/proc/{p}/stat').read_text().split()[21]);atomic(armout/'launch.json',{'arm':arm,'argv':a,'pid':p,'birth':birth,'image':str(image),'image_server_sha256':sha(image/'bin/llama-server'),'image_impl_sha256':sha(image/'bin/libllama-server-impl.so'),'launch_record_sha256':sha(REC),'environ':{k:env.get(k) for k in ('LD_LIBRARY_PATH','HSA_OVERRIDE_CPU_AFFINITY_DEBUG','GGML_CUDA_DISABLE_GRAPHS','LLAMA_SPEC_EXACT','LLAMA_ZOS2')},'at':now()})
 for _ in range(300):
  if proc.poll() is not None:raise RuntimeError(f'{arm} server exited {proc.returncode}')
  try:
   with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/health',timeout=2) as r:
    if r.status==200:break
  except Exception:pass
  time.sleep(1)
 else:raise RuntimeError(f'{arm} health timeout')
 text=(armout/'server.log').read_text(errors='replace')
 flags=re.findall(r'GPU-ZOS-2: LLAMA_ZOS2 lazy-save=(\d+) greedy-fast=(\d+) overlap-process=(\d+)',text)
 expected={'all':('1','1','1'),'lazy-save':('1','0','0'),'greedy-fast':('0','1','0'),'overlap-process':('0','0','1'),None:('0','0','0')}[knob]
 if image==C5:assert not flags,(arm,'C5 unexpectedly has ZOS startup')
 else:assert len(flags)==1 and tuple(flags[0])==expected,(arm,flags,expected)
 maps=pathlib.Path(f'/proc/{p}/maps').read_text();mapped={}
 for name,pin in (('libggml-hip.so.0.16.0','libggml_hip_sha256'),('libllama.so.0.0.10419','libllama_sha256'),('libllama-server-impl.so','server_impl_sha256')):
  paths={pathlib.Path(x) for x in re.findall(r'/[^\s]+/'+re.escape(name)+r'(?: \(deleted\))?',maps)}
  assert len(paths)==1,(arm,name,sorted(map(str,paths)))
  path=next(iter(paths));assert '(deleted)' not in str(path) and path.resolve().is_relative_to(image.resolve()),(arm,name,path)
  digest=sha(path);assert digest==image_pins[key][pin],(arm,name,digest,image_pins[key][pin])
  mapped[name]={'path':str(path),'sha256':digest}
 for raw in {line.split(maxsplit=5)[-1] for line in maps.splitlines() if '/bin/libggml' in line and '.so' in line}:
  path=pathlib.Path(raw);assert path.exists() and path.resolve().is_relative_to(image.resolve()),(arm,'foreign ggml mapping',raw)
  assert sha(path)==sha(image/'bin'/path.name),(arm,'ggml mapping bytes differ',raw)
  mapped[path.name]={'path':str(path),'sha256':sha(path)}
 atomic(armout/'loader-proof.json',{'arm':arm,'pid':p,'birth':birth,'startup_flags':flags,'mapped':mapped,'image_pins_sha256':sha(OUT/'IMAGE-PINS.json')})
 v=own_vram(p)
 for _ in range(30):
  v=own_vram(p)
  if v>=40*2**30:break
  time.sleep(1)
 if v<40*2**30:raise RuntimeError(f'{arm} own KFD VRAM {v}<40GiB')
 raw=pathlib.Path(f'/proc/{p}/environ').read_bytes()
 for k,v in ((b'HSA_OVERRIDE_CPU_AFFINITY_DEBUG',b'0'),):assert k+b'='+v+b'\0' in raw
 assert b'GGML_CUDA_DISABLE_GRAPHS=' not in raw and b'LLAMA_SPEC_EXACT=' not in raw
 if knob is None:assert b'LLAMA_ZOS2=' not in raw
 else:assert b'LLAMA_ZOS2='+knob.encode()+b'\0' in raw
 return proc

def close_server(arm):
 global proc
 if proc is None:return
 p=proc.pid
 if proc.poll() is None:
  proc.terminate()
  try:proc.wait(timeout=10)
  except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
 assert proc.poll() is not None
 for _ in range(10):
  if not pathlib.Path(f'/proc/{p}').exists() and not pathlib.Path(f'/sys/class/kfd/kfd/proc/{p}').exists():break
  time.sleep(1)
 else:raise RuntimeError(f'{arm} pid/KFD still alive after close: {p}')
 proc=None

def sampler(pid,path,done,trip):
 with path.open('a') as f:
  while not done.is_set():
   v=own_vram(pid);r={'t':time.time(),'monotonic':time.monotonic(),'pid':pid,'own_vram_bytes':v,'card_free_bytes':free_vram()};f.write(json.dumps(r)+'\n');f.flush()
   if v>61440*2**20:
    trip.set()
    if proc is not None and proc.pid==pid and proc.poll() is None:proc.terminate()
    break
   done.wait(1)

def wave(arm,idx,n,prompts):
 global proc
 armout=OUT/arm;done=threading.Event();trip=threading.Event();pid=proc.pid;t=threading.Thread(target=sampler,args=(pid,armout/'vram.jsonl',done,trip),daemon=True);t.start()
 logpath=armout/'server.log';log_start=logpath.stat().st_size
 bodies=[make_body(x,n) for x in prompts];res=[None]*len(bodies)
 def call(i):
  try:
   with (armout/'request-start.jsonl').open('a') as f:f.write(json.dumps({'wave':idx,'index':i,'at':time.time()})+'\n');f.flush();os.fsync(f.fileno())
   deadline=int(os.environ.get('FILLER_DEADLINE',str(int(time.time()+7000))))
   r,h,code=request(bodies[i],timeout=max(10,min(190,deadline-time.time()-20)));choice=r.get('choices',[{}])[0]
   native=r.get('__verbose')
   toks=native.get('tokens') if isinstance(native,dict) else None
   slot=native.get('id_slot') if isinstance(native,dict) else None
   res[i]={'ok':code==200,'code':code,'response_sha256':h,'tokens':toks,'tokens_predicted':native.get('tokens_predicted') if isinstance(native,dict) else None,'id_slot':slot,'content':choice.get('message',{}).get('content'),'timings':r.get('timings',{}),'usage':r.get('usage',{})}
  except Exception as e:res[i]={'ok':False,'error':repr(e)[:500]}
 started=time.time();th=[threading.Thread(target=call,args=(i,)) for i in range(len(bodies))]
 for x in th:x.start()
 for x in th:x.join()
 ended=time.time();done.set();t.join(timeout=3)
 samples=[json.loads(x) for x in (armout/'vram.jsonl').read_text().splitlines() if x.strip()];inside=[s for s in samples if started<=s['t']<=ended and s['pid']==pid and s['own_vram_bytes']>=20*2**30]
 record={'arm':arm,'wave':idx,'max_tokens':n,'started':started,'ended':ended,'prompt_sha256':PROMPT_SHA,'prompts':prompts,'responses':res,'vram_inside_count':len(inside),'vram_peak':max((s['own_vram_bytes'] for s in inside),default=0),'guard_tripped':trip.is_set(),'at':now()}
 with (armout/'waves.jsonl').open('a') as f:f.write(json.dumps(record)+'\n');f.flush();os.fsync(f.fileno())
 if trip.is_set():raise RuntimeError(f'{arm} own-pid 60GiB guard tripped')
 if len(inside)<2:raise RuntimeError(f'{arm} wave{idx} fewer than two in-window own-KFD >=20GiB samples')
 if not all(r and r.get('ok') and isinstance(r.get('tokens'),list) and len(r['tokens'])==n and all(type(t) is int and t>=0 for t in r['tokens']) and type(r.get('tokens_predicted')) is int and r['tokens_predicted']==n and type(r.get('usage',{}).get('completion_tokens')) is int and r['usage']['completion_tokens']==n and type(r.get('id_slot')) is int and 0<=r['id_slot']<4 and isinstance(r.get('content'),str) and r['content'] and type(r.get('timings',{}).get('draft_n')) is int and r['timings']['draft_n']>0 and type(r['timings'].get('draft_n_accepted')) is int and 0<=r['timings']['draft_n_accepted']<=r['timings']['draft_n'] for r in res):
  if stop or time.time()>=int(os.environ.get('FILLER_DEADLINE',str(int(time.time()+7000))))-30:raise WindowEnd(f'{arm} wave{idx} reached window end')
  raise RuntimeError(f'{arm} wave{idx} response/token/draft proof failed')
 logbytes=logpath.read_bytes()[log_start:];records=[]
 pattern=r'slot\s+\w+: id\s+(\d+) \| task (\d+) \|\s+graphs reused\s*=\s*(\d+)'
 for slot,task,graphs in re.findall(pattern,logbytes.decode(errors='replace')):records.append({'slot':int(slot),'task':int(task),'graphs_reused':int(graphs)})
 slots=[r['id_slot'] for r in res]
 if len(set(slots))!=len(slots):raise RuntimeError(f'{arm} wave{idx} ambiguous native slots')
 joined=[]
 for slot in slots:
  matches=[x for x in records if x['slot']==slot]
  if len(matches)!=1 or matches[0]['task']<0 or matches[0]['graphs_reused']<=0:raise RuntimeError(f'{arm} wave{idx} missing/ambiguous positive graph proof for slot {slot}: {matches}')
  joined.append(matches[0])
 if len({x['task'] for x in joined})!=len(joined):raise RuntimeError(f'{arm} wave{idx} duplicate timing task')
 record['graph_proofs']=joined;record['server_log_byte_range']=[log_start,log_start+len(logbytes)]
 with (armout/'waves.jsonl').open('rb+') as f:
  lines=f.readlines();assert json.loads(lines[-1])['wave']==idx;f.seek(sum(map(len,lines[:-1])));f.truncate();f.write((json.dumps(record)+'\n').encode());f.flush();os.fsync(f.fileno())
 return record

def sigterm(_s,_f):
 global stop
 stop=True
signal.signal(signal.SIGTERM,sigterm)
def arm_receipt(arm,count,intent_path):
 root=OUT/arm;launch_data=json.loads((root/'launch.json').read_text())
 return {'arm':arm,'waves':count,'run_intent_sha256':sha(intent_path),'source_pins_sha256':sha(D/'SOURCE-PINS.json'),'image_pins_sha256':sha(OUT/'IMAGE-PINS.json'),'model_pins_sha256':sha(OUT/'MODEL-PINS.json'),'prompt_sha256':PROMPT_SHA,'launch_record_sha256':REC_SHA,'argv':launch_data['argv'],'environ':launch_data['environ'],'files':{x:sha(root/x) for x in ('launch.json','loader-proof.json','server.log','waves.jsonl','vram.jsonl')}}
def verify_complete(arm,count,intent_path):
 path=OUT/arm/'COMPLETE.json';old=json.loads(path.read_text());expected=arm_receipt(arm,count,intent_path)
 assert {k:v for k,v in old.items() if k!='at'}==expected,(arm,'completed arm pins/outputs changed')
 waves=[json.loads(s) for s in (OUT/arm/'waves.jsonl').read_text().splitlines()]
 assert len(waves)==count+1 and [w['wave'] for w in waves]==list(range(count+1)),(arm,'wave count/order')
 expected_n=1 if arm.startswith('S') else 4
 assert all(len(w['responses'])==expected_n and len(w.get('graph_proofs',[]))==expected_n for w in waves),(arm,'request-level graph proof')

def main():
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['smoke','cutoff','full','serial']);a=ap.parse_args()
 assert sha(G/'prompts.json')==PROMPT_SHA and sha(REC)==REC_SHA
 current=subprocess.check_output(['git','-C','/mnt/raid0/llm/llama.cpp','rev-parse','ak/champion/llama-cpp-ffc1bac82eec'],text=True).strip()
 assert current=='c72ec82f5417bb2937310326120f149b665e8400','champion advanced; re-cut and re-predeclare comparator'
 c=json.loads((D/'out/BUILD-COMPLETE.json').read_text());assert c['status']=='COMPLETE'
 assert pathlib.Path(C5/'bin/llama-server').exists();assert sha(C5/'bin/libggml-hip.so.0.16.0')=='23d39c91a82fad0a83743829dd59a10df91bfe0c4a933f0cce693fc7a831beb4'
 pin=[pin_model(p) for p in MODELS]
 mp=OUT/'MODEL-PINS.json'
 if mp.exists():assert json.loads(mp.read_text())['models']==pin,'canonical model bytes/size changed'
 else:atomic(mp,{'models':pin,'at':now()})
 intent={'schema':'ni.gpu_zos2_run_intent.v1','source_pins_sha256':sha(D/'SOURCE-PINS.json'),'image_pins_sha256':sha(OUT/'IMAGE-PINS.json'),'model_pins_sha256':sha(mp),'predeclaration_sha256':sha(G/'GPU-GATE-PREDECLARATION.md'),'prompt_sha256':PROMPT_SHA,'launch_record_sha256':REC_SHA,'arm_order':['A1','B1','A2','B2','O','F1','F2','F3','D0','D1','D2','D3','Dall'],'metric':'predicted_per_second','metric_direction':'higher_is_better','metric_unit':'decode tokens_per_second','min_effect_rel':0.01,'noise_rule':'max absolute same-window A2/A1 and B2/B1 geometric-mean ratios; SHIP requires 2x NF','validity':'original GPU-ZOS-2.3 §9, including own-PID KFD, graphs, exact tokens and conditional serial/A3B3 tiers'}
 intent_mode='cutoff-full' if os.environ.get('GPU_GATE_CUTOFF')=='1' else a.mode
 intent['mode']=intent_mode;intent['host_cpus']=os.environ.get('FILLER_CPUS','184-185')
 if a.mode=='serial':intent['arm_order']=['SA1','SA2','SB','SO'];intent['serial_followup_sha256']=sha(G/'SERIAL-FOLLOWUP.json')
 ip=OUT/f'RUN-INTENT-{intent_mode}.json'
 if ip.exists():
  old=json.loads(ip.read_text()); old.pop('at',None);assert old==intent,'run intent changed across resume'
 else:atomic(ip,{**intent,'at':now()})
 cpus=os.environ.get('FILLER_CPUS','184-185');assert cpus in ('184-185','184-191')
 if a.mode in ('smoke','cutoff'):
  arms=[('B-smoke',CAND,'all',1)]
 elif a.mode=='serial':
  core=json.loads((OUT/'RESULT.json').read_text());assert core['verdict']=='INCONCLUSIVE_SERIAL_REQUIRED' and (G/'SERIAL-FOLLOWUP.json').exists()
  arms=[('SA1',C5,None,8),('SA2',C5,None,8),('SB',CAND,'all',8),('SO',CAND,None,8)]
 else:arms=[('A1',C5,None,6),('B1',CAND,'all',6),('A2',C5,None,6),('B2',CAND,'all',6),('O',CAND,None,6),('F1',CAND,'lazy-save',2),('F2',CAND,'greedy-fast',2),('F3',CAND,'overlap-process',2),('D0',DEBUG,None,2),('D1',DEBUG,'lazy-save',2),('D2',DEBUG,'greedy-fast',2),('D3',DEBUG,'overlap-process',2),('Dall',DEBUG,'all',2)]
 try:
  for arm,image,knob,count in arms:
   if a.mode in ('full','serial') and (OUT/arm/'COMPLETE.json').exists():
    verify_complete(arm,count,ip);continue
   old=OUT/arm
   if old.exists():
    archive=OUT/'attempts'/f'{arm}-{int(time.time())}'
    archive.parent.mkdir(parents=True,exist_ok=True);old.rename(archive)
   deadline=int(os.environ.get('FILLER_DEADLINE',str(int(time.time()+7000))))
   if time.time()+500>deadline or stop:
    atomic(OUT/'PARTIAL.json',{'partial':True,'before_arm':arm,'at':now()});return 75
   launch(arm,image,knob,cpus)
   try:
    warm=wave(arm,0,64,WARM_PROMPTS);
    for i in range(count):
     if time.time()+220>deadline or stop:
      atomic(OUT/'PARTIAL.json',{'partial':True,'arm':arm,'before_wave':i+1,'at':now()});return 75
     wave(arm,i+1,256 if a.mode=='serial' else 1024,[PROMPTS[i]] if a.mode=='serial' else PROMPTS[4*i:4*i+4])
   finally:close_server(arm)
   atomic(OUT/arm/'COMPLETE.json',{**arm_receipt(arm,count,ip),'at':now()})
  if a.mode=='cutoff':
   atomic(OUT/'PARTIAL.json',{'partial':True,'after':'first real request','at':now()});return 75
  if a.mode=='smoke':atomic(OUT/'SMOKE-RESULT.json',{'status':'PASS','first_real_request':True,'writer':True,'cleanup':True,'at':now()});return 0
  if a.mode=='serial':
   subprocess.run([sys.executable,'-I','-B',str(G/'analyze_serial.py')],check=True);return 0
  subprocess.run([sys.executable,'-I','-B',str(G/'analyze_gate.py')],check=True)
  subprocess.run([sys.executable,'-I','-B',str(G/'analyze_debug.py')],check=True)
  return 0
 except WindowEnd as e:
  atomic(OUT/'PARTIAL.json',{'partial':True,'reason':repr(e),'at':now()});return 75
 except Exception as e:
  atomic(OUT/'FAILED.json',{'error':repr(e),'at':now()});print(repr(e),file=sys.stderr);return 1
 finally:
  if proc is not None:close_server('finally')
if __name__=='__main__':sys.exit(main())
