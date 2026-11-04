#!/usr/bin/env python3
"""Grant-only 2.2 query transfer diagnostic against private BGE and EG2 stores."""
import datetime,json,hashlib,os,signal,socket,subprocess,sys,time,urllib.request
from pathlib import Path
import numpy as np
import faiss
from gs_contract import seal
import frozen_capture
P=Path(__file__).resolve().parent
SOURCE=Path('/mnt/raid0/llm/tmp/cal-1025/ufh12-reqb/copy')
BIN=Path('/mnt/raid0/llm/tmp/repl-emb-211-20261024/llama-src/build-cpu/bin/llama-server')
BG=Path('/mnt/raid0/llm/models/bge-large-en-v1.5-f16.gguf')
EG=Path('/mnt/raid0/llm/tmp/repl-emb-211-20261024/gguf/embeddinggemma-2-BF16.gguf')
OLD={'episodic':'sessions.pre-eg2-20261026T054229Z-3a990d','strategy':'strategies.pre-eg2-20261026T054229Z-3a990d'}
NEW={'episodic':'sessions','strategy':'strategies'}
FILES={'episodic':('embeddings.faiss','id_map.npy'),'strategy':('strategy_embeddings.faiss','strategy_id_map.npy')}
THRESH=[.1,.3,.4,.6,.7,.75,.85,.9]
STOP=False

def handler(*_):
 global STOP;STOP=True

def digest(b):return hashlib.sha256(b).hexdigest()
def post(port,path,payload):
 req=urllib.request.Request(f'http://127.0.0.1:{port}'+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=90) as f:return json.load(f)
def embed(port,text,dim,prefix):
 r=post(port,'/v1/embeddings',{'input':prefix+text});rows=r['data']
 if len(rows)!=1 or rows[0]['index']!=0:raise ValueError('invalid embedding row')
 a=np.asarray(rows[0]['embedding'],dtype=np.float32)
 if len(a)!=dim or not np.isfinite(a).all():raise ValueError('embedding shape/nonfinite')
 if dim==768:a=a[:256]
 norm=np.linalg.norm(a)
 if not norm:raise ValueError('zero embedding')
 return a/norm

def main():
 global STOP
 if os.environ.get('FILLER_ID')!='ufh12-gs-frozen-query-v2-20261104' or not os.environ.get('FILLER_CPUS'):raise RuntimeError('grant identity/CPU allocation required')
 signal.signal(signal.SIGTERM,handler);signal.signal(signal.SIGINT,handler)
 cohort_bytes=(P/'cohort.json').read_bytes()
 if digest(cohort_bytes)!='3638c148301bbd3290b038aa449774bf38a676dc1afc629ac92850eb59dc2206':raise ValueError('cohort changed')
 cohort=json.loads(cohort_bytes); dry=os.environ.get('FILLER_DRYRUN')=='1'; rows=cohort['rows'][:1] if dry else cohort['rows'];out=(Path(os.environ['FILLER_DRYRUN_RESULT_PATH']).parent/'dryrun-results.jsonl') if dry else P/'results.jsonl'
 if out.exists():raise ValueError('prior output exists: refuse overwrite')
 deadline=int(os.environ['FILLER_DEADLINE']);stop=Path(os.environ['FILLER_STOPFILE']);procs=[];logs=[];allrows=[];phase='dryrun' if dry else 'run'
 dirs={};env=os.environ.copy();env.update(LD_LIBRARY_PATH=str(BIN.parent),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
 try:
  link=subprocess.run(['/bin/bash','/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh',str(BIN),str(BIN.parent)],env=env,capture_output=True,text=True)
  (P/(phase+'-linkage.log')).write_text(link.stdout+link.stderr)
  if link.returncode:raise RuntimeError('ggml linkage mismatch')
  for port in (19111,19112):
   with socket.socket() as sock:
    sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);sock.bind(('127.0.0.1',port))
  server_args=[]
  for label,model,port,ctx,pool in [('eg2',EG,19111,2048,'mean'),('bge',BG,19112,512,'cls')]:
   f=(P/(phase+'-'+label+'.log')).open('wb');logs.append(f)
   args=[str(BIN),'-m',str(model),'--host','127.0.0.1','--port',str(port),'-np','1','-c',str(ctx),'-t','4','--embeddings','--pooling',pool,'--embd-normalize','2','--no-mmap']
   if label=='eg2':args+=['-b','2048','-ub','2048']
   proc=subprocess.Popen(args,stdout=f,stderr=subprocess.STDOUT,env=env,start_new_session=True);procs.append(proc);server_args.append(args)
   if os.environ.get('FILLER_PIDFILE'):
    with open(os.environ['FILLER_PIDFILE'],'a') as pf:pf.write(str(proc.pid)+'\n')
   for _ in range(180):
    if STOP or stop.exists() or time.time()>=deadline-90:raise InterruptedError('stop/deadline during startup')
    if proc.poll() is not None:raise RuntimeError(label+' exited early')
    try:
     with urllib.request.urlopen(f'http://127.0.0.1:{port}/health',timeout=1) as h:
      if h.status==200:
       witness=subprocess.run(['ss','-ltnp',f'sport = :{port}'],capture_output=True,text=True,check=True).stdout
       if f'pid={proc.pid},' not in witness:raise RuntimeError(label+' listener is not owned server')
       break
    except OSError:pass
    time.sleep(1)
   else:raise RuntimeError(label+' startup timeout')
  witnesses=[]
  for proc,port in zip(procs,(19111,19112)):
   procstat=Path(f'/proc/{proc.pid}/stat').read_text()
   witness=subprocess.run(['ss','-ltnp',f'sport = :{port}'],capture_output=True,text=True,check=True).stdout
   if f'pid={proc.pid},' not in witness:raise RuntimeError('server listener ownership lost')
   maps=Path(f'/proc/{proc.pid}/maps').read_text()
   allowed={row['path'] for row in json.loads((P/'input-pins.json').read_text())['files']}
   mapped=sorted({str(Path(x.split()[-1]).resolve()) for x in maps.splitlines() if x.split()[-1].startswith('/') and ('libggml' in x or 'libllama' in x or 'libmtmd' in x)})
   if not mapped or any(x not in allowed for x in mapped) or not any('libggml-cpu' in x for x in mapped):raise RuntimeError('unbound mapped inference library')
   witnesses.append({'pid':proc.pid,'port':port,'proc_stat_sha256':digest(procstat.encode()),'listener':witness,'mapped_libraries':mapped,'maps_sha256':digest(maps.encode())})
  grant_path=Path(os.environ.get('FILLER_GRANTS_DIR','/mnt/raid0/llm/tmp/compute-flags/grants'))/(os.environ['FILLER_ID']+'.grant')
  grant_bytes=grant_path.read_bytes()
  context={'schema':'epyc.gs-frozen-query-native-context.v1','capture_started':datetime.datetime.now(datetime.timezone.utc).isoformat(),'filler_id':os.environ['FILLER_ID'],'filler_cpus':os.environ['FILLER_CPUS'],'filler_end':os.environ.get('FILLER_END'),'filler_deadline':os.environ['FILLER_DEADLINE'],'phase':phase,'grant_path':str(grant_path),'grant_text':grant_bytes.decode('utf-8'),'grant_sha256':digest(grant_bytes),'actual_affinity':sorted(os.sched_getaffinity(0)),'cohort_sha256':digest(cohort_bytes),'source_sha256':digest((P/'source.sha256').read_bytes()),'input_pins_sha256':digest((P/'input-pins.json').read_bytes()),'input_pins':json.loads((P/'input-pins.json').read_text()),'linkage_sha256':digest((P/(phase+'-linkage.log')).read_bytes()),'owned_servers':witnesses,'server_argv':server_args,'scope':cohort['scope'],'notes':'Pins were content verified before publication and metadata checked before use. Listener process IDs are observed at run start. No protocol or quality warrant is asserted.'}
  context_path=(Path(os.environ['FILLER_DRYRUN_RESULT_PATH']).parent/'context.json') if dry else P/'run-context.json'
  with context_path.open('x') as cf:
   json.dump(context,cf,sort_keys=True);cf.write('\n');cf.flush();os.fsync(cf.fileno())
  context_digest=digest(context_path.read_bytes())
  for store in OLD:
   dirs[store]={}
   for lane,folder,dim in [('bge',OLD[store],1024),('eg2',NEW[store],256)]:
    idx=faiss.read_index(str(SOURCE/folder/FILES[store][0]));ids=np.load(SOURCE/folder/FILES[store][1],allow_pickle=True).tolist()
    if idx.d!=dim or idx.ntotal!=len(ids) or len(set(ids))!=len(ids):raise ValueError('index/id mismatch')
    dirs[store][lane]=(idx,ids)
   if set(dirs[store]['bge'][1])!=set(dirs[store]['eg2'][1]):raise ValueError('index identities differ')
  fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'w') as f:
   for q in rows:
    if STOP or stop.exists() or time.time()>=deadline-90:break
    started_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
     text=q['text']; vbg=embed(19112,text,1024,'');veg=embed(19111,text,768,'task: search result | query: ')
     toks=post(19111,'/tokenize',{'content':'task: search result | query: '+text,'add_special':True})['tokens']
     if not isinstance(toks,list) or not toks or any(type(x)!=int for x in toks):raise ValueError('invalid tokenization')
     item={'schema':'epyc.gs-frozen-query-result.v1','cohort_sha256':digest(cohort_bytes),'id':q['id'],'query_sha256':digest(text.encode()),'stratum':q['stratum'],'answer_named_verbatim':q.get('answer_named_verbatim'),'code_intent':q.get('code_intent'),'token_count_eg2':len(toks),'stores':{},'phase':phase,'scope':'frozen code/docs query convenience sample; no production representativeness'}
     for store in dirs:
      item['stores'][store]={}
      for lane,vec in [('bge',vbg),('eg2',veg)]:
       idx,ids=dirs[store][lane];dist,ind=idx.search(vec.reshape(1,-1),10)
       if any(i<0 for i in ind[0]) or not np.isfinite(dist).all():raise ValueError('bad top-k')
       item['stores'][store][lane]=[{'id':str(ids[i]),'cosine':float(v)} for i,v in zip(ind[0],dist[0])]
    except Exception as exc:
     item={'schema':'epyc.gs-frozen-query-result.v1','cohort_sha256':digest(cohort_bytes),'id':q['id'],'stratum':q['stratum'],'phase':phase,'error_type':type(exc).__name__,'status':'error'}
    item['started_at']=started_at
    item['context_sha256']=context_digest
    item['captured_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    item=seal(item)
    f.write(json.dumps(item,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno());allrows.append(item)
    if not dry:frozen_capture.emit(P)
    if dry and item.get('status') != 'error':
     native=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']);native.write_text(json.dumps(item,sort_keys=True)+'\n')
  if len(allrows)!=len(rows):return 75
  failures=[r for r in allrows if r.get('status')=='error']
  if failures:return 2
  summary={'schema':'epyc.gs-frozen-query-summary.v1','phase':phase,'n':len(allrows),'expected_n':len(rows),'context_sha256':context_digest,'scope':cohort['scope'],'thresholds':THRESH,'stores':{},'token_percentiles':{str(q):float(np.percentile([x['token_count_eg2'] for x in allrows],q,method='linear')) for q in [0,5,25,50,75,95,100]}}
  for store in dirs:
   summary['stores'][store]={}
   for k in [5,10]:
    lanes={lane:[e['cosine'] for row in allrows for e in row['stores'][store][lane][:k]] for lane in ['bge','eg2']}
    summary['stores'][store][str(k)]={lane:{'percentiles':{str(q):float(np.percentile(vals,q,method='linear')) for q in [0,5,25,50,75,95,100]},'threshold_counts':{str(t):sum(v>=t for v in vals) for t in THRESH}} for lane,vals in lanes.items()}
  (P/(phase+'-summary.json')).write_text(json.dumps(summary,sort_keys=True)+'\n')
  return 0
 finally:
  for p in procs:
   if p.poll() is None:p.terminate()
  for p in procs:
   try:p.wait(timeout=8)
   except subprocess.TimeoutExpired:p.kill();p.wait(timeout=8)
  for f in logs:f.close()
  if any(p.poll() is None for p in procs):raise RuntimeError('server survived cleanup')

if __name__=='__main__':
 rc=main()
 if rc == 0 and os.environ.get('FILLER_DRYRUN') != '1':
  (P/'DONE.json').write_text(json.dumps({'complete':True,'summary':'run-summary.json'})+'\n')
 sys.exit(rc)
