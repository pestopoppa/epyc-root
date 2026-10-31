#!/usr/bin/env python3
"""Prospective 200-item v9/v10 native embedding comparison; preserve all attempts."""
import hashlib,json,math,os,pathlib,signal,subprocess,sys,tempfile,threading,time
D=pathlib.Path(__file__).resolve().parent;MODEL='/mnt/raid0/llm/models/bge-large-en-v1.5-f16.gguf';BIN={'v9':'/mnt/raid0/llm/llama.cpp/build/bin/llama-embedding','v10':'/mnt/raid0/llm/kernels/production/cpu/llama-embedding'}
def sha(b):return hashlib.sha256(b).hexdigest()
def atom(p,x):
 fd,n=tempfile.mkstemp(dir=p.parent,prefix='.tmp-')
 try:
  with os.fdopen(fd,'w') as f:json.dump(x,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
  os.link(n,p)
 finally:os.unlink(n)
def main():
 mode=os.environ['EMB214_MODE'];assert mode in ('smoke','full');out=D/os.getenv('EMB214_OUT','run');out.mkdir(exist_ok=True);fid=os.getenv('FILLER_ID');gp=pathlib.Path('/mnt/raid0/llm/tmp/compute-flags/grants')/(fid+'.grant') if fid else None;grant=gp.read_bytes() if gp and gp.is_file() else None
 if mode=='full' and not grant:raise RuntimeError('grant missing')
 deadline=int(os.environ['FILLER_DEADLINE'])-20;stopped=False
 def handler(*_):
  nonlocal stopped;stopped=True
 signal.signal(signal.SIGTERM,handler);signal.signal(signal.SIGINT,handler)
 def stop():return stopped or (D/'STOP').exists() or time.time()>=deadline or (mode=='full' and (not gp.is_file() or gp.read_bytes()!=grant))
 def partial(reason):
  tmp=out/'.partial.tmp';tmp.write_text(json.dumps({'partial':True,'reason':reason})+'\n');os.replace(tmp,out/'PARTIAL.json')
 plan=sha((D/'PLAN.json').read_bytes());source=sha((D/'SOURCE-SHA256SUMS').read_bytes());sample=sha((D/'SAMPLE.json').read_bytes());items=json.loads((D/'SAMPLE.json').read_text()) if mode=='full' else [{'ordinal':0,'id':'engineering-1','text':'A short sentence about safe retries.'},{'ordinal':1,'id':'engineering-2','text':'A second different engineering control.'}];assert len(items)==(200 if mode=='full' else 2);counts={'pass':0,'fail':0,'unknown':0}
 for item in items:
  idx=item['ordinal'];itemhash=sha(item['text'].encode());vectors={}
  for arm in ('v9','v10'):
   name=f'{idx:03d}-{arm}';ep=out/(name+'.exposure.json');rp=out/(name+'.result.json');vp=out/(name+'.vector.json')
   if rp.exists():
    x=json.loads(rp.read_text());e=json.loads(ep.read_text());assert e['plan_sha256']==plan and e['source_sha256']==source and e['sample_sha256']==sample and e['text_sha256']==itemhash and e['arm']==arm
    if x.get('status')=='ok':assert vp.is_file() and sha(vp.read_bytes())==x['vector_file_sha256'];vectors[arm]=json.loads(vp.read_text())
    continue
   if ep.exists():atom(rp,{'status':'UNKNOWN','reason':'prior exposed incomplete; no redraw','exposure_sha256':sha(ep.read_bytes())});continue
   if stop() or (mode=='full' and time.time()+120>=deadline):partial('before next native request or insufficient cleanup reserve');return 75
   binary=pathlib.Path(BIN[arm]);cmd=[str(binary),'-m',MODEL,'-p',item['text'],'-t','2' if mode=='smoke' else '8','--embd-output-format','json'];env={'PATH':'/usr/bin:/bin','LD_LIBRARY_PATH':str(binary.parent)+':'+str(D/'runtime-libs'),'OMP_NUM_THREADS':'1','HIP_VISIBLE_DEVICES':'-1','ROCR_VISIBLE_DEVICES':'-1'}
   atom(ep,{'id':item['id'],'ordinal':idx,'arm':arm,'text_sha256':itemhash,'plan_sha256':plan,'source_sha256':source,'sample_sha256':sample,'binary_sha256':sha(binary.read_bytes()),'grant_sha256':sha(grant) if grant else None,'grant':grant.decode() if grant else None,'argv_redacted':[str(binary),'-m',MODEL,'-p','<text-sha256:'+itemhash+'>','-t',cmd[-3],'--embd-output-format','json'],'cpu_affinity':sorted(os.sched_getaffinity(0)),'started_epoch':time.time()})
   p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,start_new_session=True);birth=pathlib.Path('/proc',str(p.pid),'stat').read_text().rsplit(') ',1)[1].split()[19];atom(out/(name+'.active.json'),{'pid':p.pid,'birth':birth,'started_epoch':time.time()});state={}
   def collect():
    try:state['out'],state['err']=p.communicate(timeout=90)
    except Exception as e:state['error']=repr(e)
   t=threading.Thread(target=collect,daemon=True);t.start()
   while t.is_alive() and not stop():t.join(.05)
   if stop():
    if p.poll() is None:os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(10)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
    t.join(2);partial('interrupted exposed embedding request');return 75
   t.join(1)
   if t.is_alive() or p.poll() is None:
    if p.poll() is None:os.killpg(p.pid,signal.SIGTERM);p.wait()
    atom(rp,{'status':'UNKNOWN','reason':'native timeout','exposure_sha256':sha(ep.read_bytes())});continue
   try:
    if p.returncode!=0:raise RuntimeError('native rc '+str(p.returncode)+' stderr '+state.get('err',b'')[-2000:].decode(errors='replace'))
    data=json.loads(state['out']);vec=data['data'][0]['embedding'] if isinstance(data,dict) else data[0]['embedding']
    if not isinstance(vec,list) or not vec or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in vec):raise ValueError('missing or nonfinite vector')
    atom(vp,vec);atom(rp,{'status':'ok','vector_file_sha256':sha(vp.read_bytes()),'stdout_sha256':sha(state['out']),'stderr_sha256':sha(state['err']),'dimension':len(vec),'rc':p.returncode,'finished_epoch':time.time(),'exposure_sha256':sha(ep.read_bytes())});vectors[arm]=vec
   except Exception as e:atom(rp,{'status':'UNKNOWN','reason':repr(e),'rc':p.returncode,'exposure_sha256':sha(ep.read_bytes())})
  pair=out/(f'{idx:03d}.pair.json')
  if pair.exists():x=json.loads(pair.read_text());assert x['sample_sha256']==sample and x['text_sha256']==itemhash;counts[x['status']]+=1;continue
  a=vectors.get('v9');b=vectors.get('v10');cos=None
  if a is not None and b is not None and len(a)==len(b):
   aa=math.fsum(v*v for v in a);bb=math.fsum(v*v for v in b)
   if aa>0 and bb>0:cos=math.fsum(x*y for x,y in zip(a,b))/math.sqrt(aa*bb)
  status='unknown' if cos is None or not math.isfinite(cos) else 'pass' if cos>=0.9999 else 'fail';atom(pair,{'id':item['id'],'ordinal':idx,'text_sha256':itemhash,'sample_sha256':sample,'cosine':cos,'threshold':0.9999,'status':status,'v9_result_sha256':sha((out/(f'{idx:03d}-v9.result.json')).read_bytes()),'v10_result_sha256':sha((out/(f'{idx:03d}-v10.result.json')).read_bytes())});counts[status]+=1
 atom(out/'TERMINAL.json',{'state':'complete' if sum(counts.values())==len(items) else 'incomplete','counts':counts,'expected':len(items),'all_pass':counts['pass']==len(items),'partial':False,'sample_sha256':sample,'control':mode=='smoke','default_flip_performed':False});return 0
if __name__=='__main__':sys.exit(main())
