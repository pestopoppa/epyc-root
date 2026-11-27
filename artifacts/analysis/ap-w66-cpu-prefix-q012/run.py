import os,json,subprocess,time,pathlib,urllib.request,socket,hashlib,signal,threading
D=pathlib.Path(__file__).parent
os.sched_setaffinity(0,set(range(72)))
B=pathlib.Path('/mnt/raid0/llm/kernels/builds/cpu-20261126-ce6fcbbde-c22-composite')
M='/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(B/'bin/libggml-cpu.so')=='7cafa501d43a31f318cf29e51d34549cbd1d002d15f8f705e0a25543cd5d9822'
for line in (B/'SHA256SUMS').read_text().splitlines():
 h,n=line.split(None,1)
 if n in ['bin/llama-server','bin/libllama.so','bin/libggml-base.so','bin/libllama-common.so']:assert sha(B/n)==h
s=socket.socket();s.bind(('127.0.0.1',0));port=s.getsockname()[1];s.close()
env=dict(os.environ,LD_LIBRARY_PATH='/usr/lib/llvm-20/lib:'+str(B/'bin'),OMP_NUM_THREADS='72',OMP_PROC_BIND='true',OMP_PLACES=','.join('{'+str(i)+'}' for i in range(72)),GGML_IQK='1',ROCR_VISIBLE_DEVICES='',HIP_VISIBLE_DEVICES='')
argv=['numactl','--physcpubind=0-71','--interleave=0,1,2','--',str(B/'bin/llama-server'),'-m',M,'--host','127.0.0.1','--port',str(port),'--metrics','--slots','--jinja','-ngl','0','-fa','on','-np','1','-c','16384','-t','72','-tb','72','-b','2048','-ub','2048','-ctk','f16','-ctv','f16','--reasoning','off','--spec-type','draft-mtp','--spec-draft-n-max','2','--no-kv-unified','--cache-ram','0','--no-mmap','--slot-save-path',str(D/'slots')]
log=(D/'server.log').open('w');p=subprocess.Popen(argv,env=env,stdout=log,stderr=subprocess.STDOUT)
(D/'launch.json').write_text(json.dumps({'pid':p.pid,'argv':argv,'environment':{k:env[k]for k in ['LD_LIBRARY_PATH','OMP_NUM_THREADS','OMP_PROC_BIND','OMP_PLACES','GGML_IQK','ROCR_VISIBLE_DEVICES','HIP_VISIBLE_DEVICES']},'source':json.loads((B/'BUILD-OK.json').read_text()),'started':time.time()},indent=2))
base=f'http://127.0.0.1:{port}'
def call(path,obj=None):
 req=urllib.request.Request(base+path,data=json.dumps(obj).encode() if obj is not None else None,headers={'Content-Type':'application/json'})
 return json.load(urllib.request.urlopen(req,timeout=600))
stop=threading.Event()
def monitor():
 with (D/'resources.jsonl').open('w')as f:
  while not stop.wait(2):
   if p.poll() is not None:return
   statuses=[]
   for t in pathlib.Path(f'/proc/{p.pid}/task').glob('*/status'):
    try:
     vals={k:v.strip() for k,v in [x.split(':',1)for x in t.read_text().splitlines()if ':' in x]}
     statuses.append(vals['Cpus_allowed_list'])
    except FileNotFoundError:pass
   numa={}
   try:
    for line in pathlib.Path(f'/proc/{p.pid}/numa_maps').read_text().splitlines():
     for tok in line.split():
      if len(tok)>2 and tok[0]=='N' and tok[1].isdigit() and '='in tok:
       k,v=tok.split('=');numa[k]=numa.get(k,0)+int(v)
   except FileNotFoundError:pass
   rec={'time':time.time(),'affinities':sorted(set(statuses)),'threads':len(statuses),'numa_pages':numa,'kfd_present':pathlib.Path(f'/sys/class/kfd/kfd/proc/{p.pid}').exists()}
   f.write(json.dumps(rec)+'\n');f.flush()
   for a in statuses:
    for r in a.split(','):
     x=r.split('-');assert 0<=int(x[0])<=int(x[-1])<=71,a
   assert not rec['kfd_present']
threading.Thread(target=monitor,daemon=True).start()
try:
 for i in range(300):
  if p.poll()is not None:raise RuntimeError('server died')
  try:
   call('/health');break
  except Exception:time.sleep(1)
 else:raise RuntimeError('health timeout')
 # Inert tool history deliberately contains reasoning fields whose template treatment
 # changes on appending a user turn. Every response is graded against the same literal.
 tools=[{'type':'function','function':{'name':'lookup','description':'Read a table row','parameters':{'type':'object','properties':{'key':{'type':'string'}},'required':['key']}}}]
 messages=[{'role':'system','content':'You are testing a table reader. Respond to every new user request with exactly READY and no other text. Do not call tools.'},{'role':'user','content':'Inspect the historical table.'}]
 for i in range(8):
  messages.extend([{'role':'assistant','reasoning_content':('Check the recorded row carefully and preserve its identity. '*70),'content':'','tool_calls':[{'id':f'c{i}','type':'function','function':{'name':'lookup','arguments':json.dumps({'key':str(i)})}}]},{'role':'tool','tool_call_id':f'c{i}','content':('row '+str(i)+' value 42 checked. ')*50}])
 results=[]
 for ordinal,preserve in enumerate([False,True,True,False]):
  call('/slots/0?action=erase',{})
  payload={'messages':messages,'tools':tools,'tool_choice':'none','stream':True,'temperature':0,'seed':1234,'max_tokens':32,'id_slot':0,'cache_prompt':True,'chat_template_kwargs':{'enable_thinking':False,'preserve_thinking':preserve}}
  for phase in ['warm','target']:
   body=dict(payload)
   if phase=='target':body['messages']=messages+[{'role':'assistant','content':'READY'},{'role':'user','content':'Confirm the completed table inspection. Return exactly READY.'}]
   (D/f'{ordinal}-{phase}-request.json').write_text(json.dumps(body))
   req=urllib.request.Request(base+'/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
   t0=time.monotonic();first=None;parts=[];events=[]
   with urllib.request.urlopen(req,timeout=600)as r:
    for raw in r:
     if not raw.startswith(b'data:'):continue
     data=raw[5:].strip()
     if data==b'[DONE]':break
     e=json.loads(data);events.append(e)
     for c in e.get('choices',[]):
      delta=c.get('delta',{});text=delta.get('content','')
      if text:
       if first is None:first=time.monotonic()-t0
       parts.append(text)
   wall=time.monotonic()-t0
   counters=next((e['timings']for e in reversed(events)if 'timings'in e),None)
   output=''.join(parts)
   row={'ordinal':ordinal,'preserve_thinking':preserve,'phase':phase,'wall_s':wall,'delivered_ttft_s':first,'output':output,'accepted':output.strip()=='READY','timings':counters,'events':events}
   results.append(row);(D/'results.json').write_text(json.dumps(results,indent=2))
   print(json.dumps({k:v for k,v in row.items()if k!='events'}),flush=True)
finally:
 stop.set()
 if p.poll()is None:
  p.terminate()
  try:p.wait(timeout=20)
  except subprocess.TimeoutExpired:p.kill();p.wait()
 (D/'cleanup.json').write_text(json.dumps({'pid':p.pid,'returncode':p.returncode,'exists':pathlib.Path(f'/proc/{p.pid}').exists(),'ended':time.time()}))
