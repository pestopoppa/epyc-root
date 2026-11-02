#!/usr/bin/env python3
"""Exact hybrid/legacy CPU depth comparison; only run under filler_run15."""
import ctypes,hashlib,json,os,pathlib,signal,statistics,subprocess,time
D=pathlib.Path(__file__).resolve().parent
B=pathlib.Path('/mnt/raid0/llm/kernels/builds/cpu-20261024-c72ec82f5-c5/bin')
STOP=False
signal.signal(signal.SIGTERM,lambda *_:globals().__setitem__('STOP',True))
signal.signal(signal.SIGINT,lambda *_:globals().__setitem__('STOP',True))
def guarded():
 return STOP or pathlib.Path(os.environ['FILLER_STOPFILE']).exists() or time.time()+30>=float(os.environ['FILLER_DEADLINE'])
def stat_check(v):
 s=pathlib.Path(v['path']).stat()
 return (s.st_size,s.st_mtime_ns,s.st_dev,s.st_ino)==tuple(v[k] for k in ['size','mtime_ns','device','inode'])
def validate_rows(rows,depth,n):
 assert isinstance(rows,list) and len(rows)==1
 r=rows[0];assert r['autokernel_hardened'] is False
 assert r['n_depth']==depth and r['n_prompt']==0 and r['n_gen']==n
 assert r['avg_ts']>0
 return r['avg_ts']
def drain(p):
 if p.poll() is None:
  os.killpg(p.pid,signal.SIGTERM)
  try:p.wait(timeout=5)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=5)
 assert p.poll() is not None
 # Own process group only. Refuse successful completion if any child survived.
 try:os.killpg(p.pid,0)
 except ProcessLookupError:return
 raise RuntimeError('owned process group still exists')
def pdeath():
 ctypes.CDLL(None).prctl(1,signal.SIGKILL)
 if os.getppid()==1:os._exit(75)
def main():
 smoke=os.environ.get('FILLER_DRYRUN')=='1'
 receipt=json.loads((D/'prepared.json').read_text())
 assert all(stat_check(x) for x in receipt['models']+receipt['products']+[receipt['source_ops'],receipt['store_manifest']])
 for x in receipt['products']:
  assert hashlib.sha256(pathlib.Path(x['path']).read_bytes()).hexdigest()==x['sha256']
 assert not guarded()
 cpus=os.environ['FILLER_CPUS'];threads=4 if smoke else 48
 if not smoke:assert set(range(96))<=os.sched_getaffinity(0)
 output=pathlib.Path(os.environ['FILLER_DRYRUN_DIR'])/'native-cells' if smoke else D/'run'
 output.mkdir(parents=True,exist_ok=False)
 target=pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'RESULT.json'
 assert not target.exists()
 plan=[(0,0,'hybrid')] if smoke else [(depth,i,arm) for depth in [16384,65536] for i in range(5) for arm in (['hybrid','legacy'] if i%2==0 else ['legacy','hybrid'])]
 records=[]
 for depth,i,arm in plan:
  if guarded():raise RuntimeError('STOP/deadline before arm')
  n=1 if smoke else 32
  mem=dict(line.split(':',1) for line in pathlib.Path('/proc/meminfo').read_text().splitlines())
  assert int(mem['MemAvailable'].split()[0])*1024 >= 104*1024**3,'less than 104GiB MemAvailable'
  stem=output/f'd{depth}-r{i}-{arm}'
  env={k:v for k,v in os.environ.items() if not k.startswith(('GGML_','OMP_','GOMP_','KMP_','LLAMA_'))}
  env.update(LD_LIBRARY_PATH=str(B),GGML_IQK='1',GGML_FUSED_DECODE_OFF='1',GGML_FA_SPLIT_KV='0',GGML_NOHUGEPAGE_PROCESS='1',OMP_PROC_BIND='spread',OMP_PLACES='cores',OMP_WAIT_POLICY='active',OMP_DYNAMIC='false')
  if arm=='legacy':env['GGML_FA_VKQ_F16']='1'
  argv=['taskset','-c',cpus,'numactl','--interleave=all','--',str(B/'llama-bench'),'-m',receipt['models'][0]['path'],'-ngl','0','-t',str(threads),'-fa','1','-ctk','f16','-ctv','f16','-mmp','0','-p','0','-n',str(n),'-d',str(depth),'-r','1','-o','json']
  stem.with_suffix('.plan.json').write_text(json.dumps(dict(argv=argv,env={k:v for k,v in env.items() if k.startswith(('GGML_','OMP_','LD_'))},receipt_sha256=hashlib.sha256((D/'prepared.json').read_bytes()).hexdigest()),indent=2))
  witnesses=[];started=time.time()
  with stem.with_suffix('.json').open('x') as out,stem.with_suffix('.err').open('x') as err:
   p=subprocess.Popen(argv,env=env,stdout=out,stderr=err,start_new_session=True,preexec_fn=pdeath)
   try:
    if os.environ.get('FILLER_PIDFILE'):
     with open(os.environ['FILLER_PIDFILE'],'a') as f:f.write(str(p.pid)+'\n')
    while p.poll() is None:
     if guarded() or time.time()-started>1800:raise RuntimeError('STOP/deadline/cell timeout')
     try:
      paths=[line.split()[-1] for line in pathlib.Path(f'/proc/{p.pid}/maps').read_text().splitlines() if 'libggml' in line]
      if paths:
       assert all(pathlib.Path(x).resolve().parent==B for x in paths),paths
       witnesses.append(dict(at=time.time(),pid=p.pid,paths=sorted(set(paths))))
     except FileNotFoundError:pass
     time.sleep(.2)
    assert p.returncode==0,p.returncode
   finally:drain(p)
  stem.with_suffix('.witness.json').write_text(json.dumps(witnesses))
  assert len(witnesses)>=2,'no two during-run own-library witnesses'
  speed=validate_rows(json.loads(stem.with_suffix('.json').read_text()),depth,n)
  records.append(dict(depth=depth,rep=i,arm=arm,tok_s=speed,pid=p.pid,rc=p.returncode))
 cells={}
 if not smoke:
  for depth in [16384,65536]:
   vals={a:[r['tok_s'] for r in records if r['depth']==depth and r['arm']==a] for a in ['hybrid','legacy']}
   assert all(len(v)==5 for v in vals.values())
   med={a:statistics.median(v) for a,v in vals.items()}
   floor=max(2.,*(100*(max(vals[a])-min(vals[a]))/med[a] for a in vals))
   effect=100*(med['hybrid']/med['legacy']-1)
   cells[str(depth)]=dict(median_tok_s=med,effect_pct=effect,noise_floor_pct=floor,verdict='gain' if effect>floor else 'regression' if effect < -floor else 'within_floor')
 result=dict(schema='cpu-fa-vkq2.result.v1',mode='qualification' if smoke else 'full',complete=True,records=records,cells=cells,direction='higher tok/s better',scope='CPU decode only; no MTP acceptance, fold or deployment verdict')
 with target.open('x') as f:json.dump(result,f,indent=2)
if __name__=='__main__':main()
