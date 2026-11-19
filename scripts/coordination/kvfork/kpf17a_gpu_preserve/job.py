#!/usr/bin/env python3
"""Paired original/extended GPU harness preservation, under keeper grant only."""
import hashlib, json, math, os, pathlib, re, signal, struct, subprocess, sys, time, uuid
D=pathlib.Path(__file__).resolve().parent
R=D/'out'
C=json.loads((D/'identity.json').read_text())
L=pathlib.Path(C['libdir'])
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def verify():
 for p,h in C['files'].items():
  if sha(p)!=h:raise RuntimeError('input changed: '+p)
 return sha(D/'identity.json')
def paused():return pathlib.Path(os.environ['FILLER_STOPFILE']).exists() or time.time()>=float(os.environ['FILLER_DEADLINE'])
def run(args,log,env=None,sample=False):
 if paused():raise SystemExit(75)
 samples=[]
 with open(log,'wb') as f:
  p=subprocess.Popen(args,stdout=f,stderr=subprocess.STDOUT,env=env,start_new_session=True)
  with open(os.environ['FILLER_PIDFILE'],'a') as ids:ids.write(str(p.pid)+'\n')
  try:
   while p.poll() is None:
    if paused():
     os.killpg(p.pid,signal.SIGTERM)
     try:p.wait(timeout=5)
     except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
     assert p.poll() is not None
     raise SystemExit(75)
    if sample:
     try:
      lines=pathlib.Path(f'/proc/{p.pid}/maps').read_text().splitlines()
      libs=sorted({x.split()[-1] for x in lines if '/libggml' in x})
      if any(not pathlib.Path(x).resolve().is_relative_to(L.resolve()) for x in libs):raise RuntimeError('foreign ggml mapping')
      kfd=pathlib.Path(f'/sys/class/kfd/kfd/proc/{p.pid}')
      vram=sum(int(q.read_text().strip()) for q in kfd.glob('vram_*'))
      samples.append({'time_ns':time.time_ns(),'pid':p.pid,'mapped_ggml':libs,'own_hip':any(pathlib.Path(x).name.startswith('libggml-hip') for x in libs),'kfd_present':kfd.is_dir(),'vram_bytes':vram})
     except (FileNotFoundError,ProcessLookupError):pass
    time.sleep(.002 if sample else .1)
   if p.returncode:raise RuntimeError(f'command rc={p.returncode}: {log}')
  finally:
   if p.poll() is None:
    os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
 if sample:
  pathlib.Path(str(log)+'.residency.json').write_text(json.dumps(samples)+'\n')
 return samples
def parse(log,dump,case,supported,extended):
 rows=[x for x in log.read_text().splitlines() if x.startswith('case ')]
 assert len(rows)==1 and int(rows[0].split()[1])==case
 row=rows[0]
 assert (' unsupported' in row)==(not supported)
 if not supported:return row,None
 if extended:
  assert re.search(r'\bshared=0\b',row)
  row=re.sub(r'\s+shared=0\b','',row)
 assert re.search(r'\bnan=0\b',row)
 data=(dump/f'out_{case:02d}.bin').read_bytes()
 assert data and len(data)%4==0 and all(math.isfinite(x[0]) for x in struct.iter_unpack('<f',data))
 h=0x14650fb0739d0383
 for b in data:h=((h^b)*0x100000001b3)&((1<<64)-1)
 assert int(re.search(r'\bhash=([0-9a-f]+)',row)[1],16)==h
 return row,data
binding=verify()
if '--check' in sys.argv:sys.exit(0)
assert os.environ.get('FILLER_CPUS') and os.environ.get('FILLER_THREADS')
R.mkdir(exist_ok=True)
if (R/'binding').exists():assert (R/'binding').read_text()==binding
else:(R/'binding').write_text(binding)
env=dict(os.environ,LD_LIBRARY_PATH=str(L),GGML_BACKEND_PATH=str(L),ROCR_VISIBLE_DEVICES='0',HIP_VISIBLE_DEVICES='0')
bins=[]
for name in ('original','extended'):
 b=R/('harness-'+name); r=R/('build-'+name+'.json')
 if not r.exists():
  run(['g++','-O2','-std=c++17',str(D/(name+'.cpp')),'-I'+C['include'],'-L'+str(L),'-lggml','-lggml-base','-lggml-cpu','-Wl,-rpath,'+str(L),'-o',str(b)],R/('compile-'+name+'.log'),env)
  r.write_text(json.dumps({'binding':binding,'binary_sha256':sha(b)})+'\n')
 assert json.loads(r.read_text())=={'binding':binding,'binary_sha256':sha(b)}
 run(['bash',C['linkage_helper'],str(b),str(L)],R/('linkage-'+name+'.txt'),env)
 bins.append(b)
expected=json.loads((D/'expected_rocm0.json').read_text()); supported=set(expected['expected_supported'])
for case in [83]+[i for i in range(86) if i!=83]:
 if paused():raise SystemExit(75)
 done=R/f'case-{case:03d}.json'
 if done.exists():
  old=json.loads(done.read_text()); assert old['binding']==binding and all(sha(p)==h for p,h in old['files'].items());continue
 a=R/f'case-{case:03d}-{uuid.uuid4().hex}';a.mkdir(); paired=[]
 for setting in (0,1):
  vals=[]
  for name,b in zip(('original','extended'),bins):
   dump=a/f'{name}-{setting}';dump.mkdir();log=a/f'{name}-{setting}.txt'
   e=dict(env,FA_CASE=str(case),FA_DUMP_DIR=str(dump),GGML_CUDA_FA_MASK_SKIP=str(setting))
   if case==83 and name=='extended':e['FA_RESIDENCY_OBSERVE']='1'
   samples=run([str(b),'ROCm0','exact',os.environ['FILLER_THREADS']],log,e,True)
   if case in supported:
    good=[x for x in samples if x['own_hip'] and x['kfd_present'] and x['vram_bytes']>0]
    assert len(good)>=2,f'insufficient residency samples case={case}, harness={name}, setting={setting}'
   vals.append(parse(log,dump,case,case in supported,name=='extended'))
  assert vals[0]==vals[1],f'original vs extended mismatch: case={case}, setting={setting}'
  paired.append({'skip':setting,'status':'bitwise-equal' if case in supported else 'declared-unsupported'})
 files={str(p):sha(p) for p in a.rglob('*') if p.is_file()}
 rec={'schema':'kpf17a.gpu.preservation-case.v1','case':case,'status':'PASS','binding':binding,'attempt':str(a),'supported':case in supported,'comparisons':paired,'files':files,'commit':C['commit'],'threads':os.environ['FILLER_THREADS'],'cpus':os.environ['FILLER_CPUS'],'binaries':{b.name:sha(b) for b in bins}}
 tmp=done.with_suffix('.tmp');tmp.write_text(json.dumps(rec)+'\n');tmp.replace(done)
 with (R/'results.jsonl').open('a') as out:out.write(json.dumps(rec)+'\n');out.flush();os.fsync(out.fileno())
assert verify()==binding
for case in range(86):
 rec=json.loads((R/f'case-{case:03d}.json').read_text());assert rec['binding']==binding and rec['status']=='PASS' and all(sha(p)==h for p,h in rec['files'].items())
(R/'verdict.json').write_text(json.dumps({'status':'PASS','binding':binding,'cases':86,'supported':sum(i in supported for i in range(86)),'unsupported':sum(i not in supported for i in range(86)),'criterion':'original versus extended bit-identical for both skip settings, same build and grant'})+'\n')
(R/'COMPLETE').write_text(binding+'\n')
