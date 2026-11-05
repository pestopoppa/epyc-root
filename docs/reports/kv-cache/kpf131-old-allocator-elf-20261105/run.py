#!/usr/bin/env python3
import os,sys,json,hashlib,subprocess,signal,time,pathlib,uuid,resource
B=pathlib.Path(__file__).resolve().parent
mode='smoke' if os.environ.get('FILLER_SMOKE')=='1' else 'full'
if mode=='smoke' and not os.environ.get('FILLER_DRYRUN_RESULT_PATH'):raise SystemExit('isolated publisher smoke receipt required')
if mode not in ('smoke','full'): raise SystemExit(64)
cpus=os.sched_getaffinity(0)
if (mode=='smoke' and len(cpus)!=4) or (mode=='full' and len(cpus)!=24): raise SystemExit('require four smoke CPUs or 24 full CPUs')
P=json.loads((B/'inputs.json').read_text()); attempt=mode+'-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+uuid.uuid4().hex
O=B/'out'/mode/attempt;O.mkdir(parents=True,exist_ok=False)
child=None; end=time.monotonic()+300; records=[]
if os.environ.get('FILLER_DEADLINE'): end=min(end,time.monotonic()+float(os.environ['FILLER_DEADLINE'])-time.time())
receipt=pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if os.environ.get('FILLER_DRYRUN_RESULT_PATH') else B/'out'/'RESULT.json'
def alarm(*args): raise RuntimeError('deadline during IO')
signal.signal(signal.SIGALRM,alarm);signal.setitimer(signal.ITIMER_REAL,max(.001,end-time.monotonic()))
def digest(p):
 with open(p,'rb') as f:
  h=hashlib.sha256()
  while True:
   checkpoint(); chunk=f.read(1048576)
   if not chunk:break
   h.update(chunk)
  return h.hexdigest()
def stop(*args):
 global child
 if child is not None:
  if child.poll() is None:
   child.terminate()
   try:child.wait(timeout=3)
   except subprocess.TimeoutExpired:child.kill();child.wait(timeout=3)
  if pathlib.Path('/proc/'+str(child.pid)).exists():raise RuntimeError('owned PID survives cleanup')
  child=None
 if args:raise SystemExit(75)
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
def checkpoint():
 if (B/'STOP').exists() or (os.environ.get('FILLER_STOPFILE') and pathlib.Path(os.environ['FILLER_STOPFILE']).exists()) or time.monotonic()>end:raise RuntimeError('STOP or deadline')
def check(p,h):
 checkpoint()
 if digest(p)!=h:raise RuntimeError('input digest mismatch: '+p)
metadata={}
def write_receipt(result):
 receipt.parent.mkdir(parents=True,exist_ok=True)
 tmp=receipt.with_name(receipt.name+'.'+uuid.uuid4().hex+'.tmp')
 tmp.write_text(json.dumps(dict(result,attempt_dir=str(O)),indent=2)+'\n');os.replace(tmp,receipt)
try:
 for lineage_path,lineage_sha in json.loads((B/'lineage.json').read_text()).items():check(lineage_path,lineage_sha)
 metadata={str(B/'lineage.json'):digest(B/'lineage.json'),str(B/'historical-source-digests.json'):digest(B/'historical-source-digests.json'),str(B/'inputs.json'):digest(B/'inputs.json')}
 for n,t in P['tools'].items():check(t['path'],t['sha256'])
 images=P['images']
 smoke_image='/mnt/raid0/llm/kernels/builds/gpu-20261020-a1f0c8cf9/bin/libllama.so.0.0.10348'
 if not isinstance(images,dict) or len(images)!=16 or smoke_image not in images:raise RuntimeError('pinned 16-image inventory or explicit smoke ELF missing')
 selected=[smoke_image]
 expected_count=1
 if len(selected)!=expected_count or len(set(selected))!=expected_count:raise RuntimeError('empty or inexact selected inventory')
 for image in selected:
  if not pathlib.Path(image).is_file():raise RuntimeError('selected ELF missing: '+image)
  with open(image,'rb') as elf:
   if elf.read(4)!=b'\x7fELF':raise RuntimeError('selected file is not ELF: '+image)
 for index,p in enumerate(selected):
  check(p,images[p]); st=os.stat(p); fd=os.open(p,os.O_RDONLY); prefix=f'{index:02d}-'+pathlib.Path(p).name
  try:
   for label,tool,args in [('elf', 'readelf', ['-h', '-W', '-S', '-n']), ('symbols', 'nm', ['-a', '-C']), ('find-slot', 'objdump', ['-d', '--disassemble=_ZNK14llama_kv_cache9find_slotERK12llama_ubatchb']), ('apply-ubatch', 'objdump', ['-d', '--disassemble=_ZN14llama_kv_cache12apply_ubatchERKNS_9slot_infoERK12llama_ubatch']), ('apply-ubatch-part', 'objdump', ['-d', '--disassemble=_ZN14llama_kv_cache12apply_ubatchERKNS_9slot_infoERK12llama_ubatch.part.0'])]:
    checkpoint();check(P['tools'][tool]['path'],P['tools'][tool]['sha256'])
    target=O/(prefix+'.'+label+'.txt');err=O/(prefix+'.'+label+'.stderr')
    argv=[P['tools'][tool]['path'],*args,'/proc/self/fd/'+str(fd)]
    with target.open('xb') as stdout,err.open('xb') as stderr:
     child=subprocess.Popen(argv,stdout=stdout,stderr=stderr,pass_fds=(fd,),preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_FSIZE,(8*1024*1024,8*1024*1024)))
     pid=child.pid
     try:birth=pathlib.Path('/proc/'+str(pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
     except FileNotFoundError:birth=None
     while child.poll() is None:
      checkpoint()
      if time.monotonic()>end:raise RuntimeError('deadline')
      try:child.wait(timeout=.2)
      except subprocess.TimeoutExpired:pass
     rc=child.returncode;stop()
    records.append({'input':p,'tool':tool,'argv':argv,'pid':pid,'birth_start_ticks':birth,'rc':rc,'stdout':target.name,'stdout_sha256':digest(target),'stderr':err.name,'stderr_sha256':digest(err)})
    allocator_symbols={'find-slot':'_ZNK14llama_kv_cache9find_slotERK12llama_ubatchb','apply-ubatch':'_ZN14llama_kv_cache12apply_ubatchERKNS_9slot_infoERK12llama_ubatch','apply-ubatch-part':'_ZN14llama_kv_cache12apply_ubatchERKNS_9slot_infoERK12llama_ubatch.part.0'}
    if label in allocator_symbols:
     body=target.read_text(errors='replace'); symbol=allocator_symbols[label]
     if ('<'+symbol+'>:') not in body:raise RuntimeError('requested allocator symbol body absent')
     if not any(line.strip().split(':',1)[0] and ':' in line and line.lstrip()[0:1] in '0123456789abcdef' and '\t' in line for line in body.splitlines()):raise RuntimeError('allocator symbol has no instruction bytes')
    if rc or target.stat().st_size>=8*1024*1024 or err.stat().st_size>=8*1024*1024:raise RuntimeError('ELF tool failed or hard 8MiB output limit; preserve diagnostic and unknowns')
   check(p,images[p]); after=os.stat(p)
   if (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):raise RuntimeError('input identity changed')
  finally:os.close(fd)
 for n,t in P['tools'].items():check(t['path'],t['sha256'])
 for path,sha in metadata.items():check(path,sha)
 for lineage_path,lineage_sha in json.loads((B/'lineage.json').read_text()).items():check(lineage_path,lineage_sha)
 if len(records)!=expected_count*5 or {r['input'] for r in records}!=set(selected):raise RuntimeError('incomplete actual inventory')
 result={'row_id':'kpf131-old-allocator-elf-20261105','lineage':json.loads((B/'lineage.json').read_text()),'status':'ALLOCATOR_ELF_CAPTURED','mode':mode,'attempt':attempt,'source_commit':P['source_commit'],'input_pins':P,'records':records,'processed_files':len(selected),'unknowns':['targeted allocator disassembly captured; offsets and STL/object layouts require independent recovery and own-child validation','physical cache ABI offsets unvalidated','actual server task/request/slot/stream/batch binding absent','historical runtime mapped DSO digests unavailable','same-user transient input mutation not excluded','missing DWARF or symbol means unknown, never unsupported or impossible'],'scope':'read-only ELF inventory; images never executed; no model, GPU, native layout or task-binding qualification'}
except BaseException as e:
 signal.setitimer(signal.ITIMER_REAL,0);stop()
 # Failure custody: preserve and hash even the interrupted tool's files.
 failure_files={}; custody_error=None
 signal.setitimer(signal.ITIMER_REAL,30)
 try:
  for path in O.iterdir():
   if path.is_file():
    with path.open('rb') as stream:failure_files[path.name]=hashlib.file_digest(stream,'sha256').hexdigest()
 except BaseException as custody: custody_error=str(custody)
 finally:signal.setitimer(signal.ITIMER_REAL,0)
 result={'failure_digest_error':custody_error,'failure_output_sha256':failure_files,'status':'INVALID','mode':mode,'attempt':attempt,'records':records,'error':str(e),'processed_files':0}
 (O/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');write_receipt(result);raise
finally:signal.setitimer(signal.ITIMER_REAL,0);stop()
(O/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
write_receipt(result)
print(receipt)
