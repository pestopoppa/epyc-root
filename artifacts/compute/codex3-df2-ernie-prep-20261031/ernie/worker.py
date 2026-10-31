#!/usr/bin/env python3
"""ERNIE native GPU requests; preserve every exposure and unaltered PNG."""
import base64,hashlib,io,json,os,pathlib,signal,socket,subprocess,sys,tempfile,threading,time,urllib.request
from PIL import Image,ImageStat
D=pathlib.Path(__file__).resolve().parent;BIN=pathlib.Path('/mnt/raid0/llm/worktrees/sub-gpu-prep-stable-diffusion.cpp/build-rocm-gpuprep-20260916/bin');M=pathlib.Path('/mnt/raid0/llm/models/diffusion')
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def atom(p,x):
 fd,n=tempfile.mkstemp(dir=p.parent,prefix='.tmp-')
 try:
  with os.fdopen(fd,'w') as f:json.dump(x,f,ensure_ascii=False,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
  os.link(n,p)
 finally:os.unlink(n)
def main():
 mode=os.environ['ERNIE_MODE'];assert mode in ('smoke','full');out=D/os.getenv('ERNIE_OUT','run');out.mkdir(exist_ok=True);plan=json.loads((D/'PLAN.json').read_text());fid=os.getenv('FILLER_ID');gp=pathlib.Path('/mnt/raid0/llm/tmp/compute-flags/grants')/(fid+'.grant') if fid else None;grant=gp.read_bytes() if gp and gp.is_file() else None
 if mode=='full' and (not grant or os.getenv('FILLER_NEEDGPU')!='1'):raise RuntimeError('genuine GPU grant missing')
 deadline=int(os.environ['FILLER_DEADLINE'])-20;flag=False
 def handler(*_):
  nonlocal flag;flag=True
 signal.signal(signal.SIGTERM,handler);signal.signal(signal.SIGINT,handler)
 def stop():return flag or (D/'STOP').exists() or time.time()>=deadline or (mode=='full' and (not gp.is_file() or gp.read_bytes()!=grant))
 def partial(reason):
  p=out/'.partial.tmp';p.write_text(json.dumps({'partial':True,'reason':reason})+'\n');os.replace(p,out/'PARTIAL.json')
 with socket.socket() as z:z.bind(('127.0.0.1',0));port=z.getsockname()[1]
 cmd=[str(BIN/'sd-server'),'--diffusion-model',str(M/'ernie-image-turbo-gguf/ernie-image-turbo-Q8_0.gguf'),'--vae',str(M/'ernie-image-turbo-comfy/vae/flux2-vae.safetensors'),'--llm',str(M/'ernie-image-turbo-comfy/text_encoders/ministral-3-3b.safetensors'),'-t','2' if mode=='smoke' else '8','--diffusion-fa','--diffusion-conv-direct','--vae-conv-direct','--listen-ip','127.0.0.1','--listen-port',str(port)]
 env={'PATH':'/usr/bin:/bin','LD_LIBRARY_PATH':str(BIN)+':/opt/rocm/lib','HIP_PATH':'/opt/rocm','ROCM_PATH':'/opt/rocm','HIP_VISIBLE_DEVICES':'0','OMP_NUM_THREADS':'1'};log=(out/('server-'+str(time.time_ns())+'.log')).open('xb');p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True);birth=pathlib.Path('/proc',str(p.pid),'stat').read_text().rsplit(') ',1)[1].split()[19];atom(out/('server-'+str(p.pid)+'.json'),{'pid':p.pid,'birth':birth,'argv':cmd,'mode':mode,'gpu_grant':grant.decode() if grant else None,'grant_sha256':hashlib.sha256(grant).hexdigest() if grant else None,'source_sha256':sha(D/'SOURCE-SHA256SUMS'),'plan_sha256':sha(D/'PLAN.json'),'model_catalog_sha256':sha(D/'MODELS.sha256'),'binary_sha256':sha(BIN/'sd-server'),'started_epoch':time.time()})
 try:
  url=f'http://127.0.0.1:{port}';ready=False;end=time.monotonic()+180
  while time.monotonic()<end and p.poll() is None and not stop():
   try:
    with urllib.request.urlopen(url+'/sdapi/v1/samplers',timeout=2) as r:ready=r.status==200
   except Exception:pass
   if ready:break
   time.sleep(.2)
  if stop():partial('startup interrupted');return 75
  if not ready:atom(out/'TERMINAL.json',{'partial':False,'state':'server_not_ready','remaining':'UNKNOWN','rc':p.poll()});return 0
  cases=[{'id':'engineering-control','prompt':'A simple red circle on a white background','language':'none'}] if mode=='smoke' else plan['cases'];shapes=[[512,512]] if mode=='smoke' else plan['shapes'];done=unknown=0
  for case in cases:
   for w,h in shapes:
    key=case['id']+f'-{w}x{h}';exp=out/(key+'.exposure.json');res=out/(key+'.result.json');png=out/(key+'.png')
    if res.exists():
     x=json.loads(res.read_text());old=json.loads(exp.read_text())
     if old['plan_sha256']!=sha(D/'PLAN.json') or old['source_sha256']!=sha(D/'SOURCE-SHA256SUMS') or (x.get('status')=='ok' and (not png.is_file() or x.get('png_sha256')!=sha(png))):raise RuntimeError('cached receipt or immutable study envelope drift')
     done+=x.get('status')=='ok';unknown+=x.get('status')!='ok';continue
    if exp.exists():
     atom(res,{'id':key,'status':'UNKNOWN','reason':'previous exposure without result; never redraw','exposure_sha256':sha(exp)});unknown+=1;continue
    if stop() or (mode=='full' and time.time()+180>=deadline):partial('before next case or insufficient request/cleanup reserve');return 75
    payload={'prompt':case['prompt'],'negative_prompt':'blurry, low quality, blank white image','width':w,'height':h,'steps':8,'cfg_scale':1.0,'seed':2026072732,'batch_size':1};atom(exp,{'id':key,'case_id':case['id'],'language':case['language'],'prompt_sha256':hashlib.sha256(case['prompt'].encode()).hexdigest(),'settings':{k:v for k,v in payload.items() if k!='prompt'},'source_sha256':sha(D/'SOURCE-SHA256SUMS'),'plan_sha256':sha(D/'PLAN.json'),'model_catalog_sha256':sha(D/'MODELS.sha256'),'gpu_grant':grant.decode() if grant else None,'grant_sha256':hashlib.sha256(grant).hexdigest() if grant else None,'started_epoch':time.time()});state={};samples=[]
    def request():
     try:
      req=urllib.request.Request(url+'/sdapi/v1/txt2img',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
      with urllib.request.urlopen(req,timeout=160) as r:state['http_status']=r.status;state['raw']=r.read()
     except Exception as e:state['error']=repr(e)
    t=threading.Thread(target=request,daemon=True);t.start()
    while t.is_alive() and p.poll() is None and not stop():
     sm={'epoch':time.time(),'server_alive':p.poll() is None,'kfd_pid_present':pathlib.Path('/sys/class/kfd/kfd/proc',str(p.pid)).exists()}
     try:
      z=subprocess.run(['/opt/rocm/bin/rocm-smi','--showmeminfo','vram','--showuse','--json'],capture_output=True,text=True,timeout=3);sm.update(rocm_smi_rc=z.returncode,rocm_smi=z.stdout[:10000]); parsed=json.loads(z.stdout) if z.returncode==0 else {}; used=[int(v.get('VRAM Total Used Memory (B)',0)) for v in parsed.values() if isinstance(v,dict)];sm['vram_used_bytes']=max(used,default=None)
     except Exception as e:sm['rocm_smi_error']=repr(e)
     samples.append(sm);t.join(.5)
    if stop():partial('interrupted exposed GPU request');return 75
    t.join(1)
    if t.is_alive() or 'error' in state:atom(res,{'id':key,'status':'UNKNOWN','reason':'request failure','error':state.get('error'),'samples':samples,'exposure_sha256':sha(exp)});unknown+=1;continue
    try:
     body=json.loads(state['raw']);raw=base64.b64decode(body['images'][0].split(',')[-1],validate=True);fd=os.open(png,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
     with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
     im=Image.open(io.BytesIO(raw));im.load();st=ImageStat.Stat(im.convert('RGB'));valid=im.format=='PNG' and im.size==(w,h);gpu_seen=any(s['kfd_pid_present'] and isinstance(s.get('vram_used_bytes'),int) and s['vram_used_bytes']>0 and (mode!='smoke' or s['vram_used_bytes']<=48*1024**3) for s in samples);status='ok' if valid and gpu_seen else 'UNKNOWN';atom(res,{'id':key,'status':status,'png_sha256':sha(png),'format':im.format,'size':im.size,'pixel_mean':st.mean,'pixel_stddev':st.stddev,'qualitative_review':'UNKNOWN','gpu_residency_and_vram_seen_during_request':gpu_seen,'samples':samples,'http_status':state['http_status'],'exposure_sha256':sha(exp),'completed_epoch':time.time()});done+=status=='ok';unknown+=status!='ok'
    except Exception as e:atom(res,{'id':key,'status':'UNKNOWN','reason':'invalid native image','error':repr(e),'samples':samples,'exposure_sha256':sha(exp)});unknown+=1
  atom(out/'TERMINAL.json',{'partial':False,'state':'complete_capture' if unknown==0 else 'incomplete_capture','captured':done,'unknown':unknown,'expected':len(cases)*len(shapes),'human_review':'UNKNOWN','official_longtextbench_score':'UNKNOWN','enhancer_on':'UNKNOWN','product_filter':'UNKNOWN','control':mode=='smoke'});return 0
 finally:
  if p.poll() is None:
   os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(10)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
  log.close();atom(out/('server-'+str(p.pid)+'.drain.json'),{'pid':p.pid,'birth':birth,'rc':p.returncode,'drained':p.poll() is not None,'server_log_sha256':sha(log.name)})
if __name__=='__main__':sys.exit(main())
