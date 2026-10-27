#!/usr/bin/env python3
"""Private CPU reference canary/full runner. Requires reviewed launcher and pins."""
import hashlib,importlib.util,json,os,pathlib,signal,subprocess,sys,time
from proof import check
D=pathlib.Path(__file__).resolve().parent
OLD=pathlib.Path('/mnt/raid0/llm/tmp/refactor-01a16fc3/parakeet-reference-ready/reference.py')
spec=importlib.util.spec_from_file_location('original_reference',OLD);ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
def sample(pid,birth,pins):
 p=pathlib.Path('/proc')/str(pid)
 stat=(p/'stat').read_text(); actual=int(stat[stat.rfind(')')+2:].split()[19])
 if actual!=birth: raise ValueError('PID reused')
 affinity=next(x.split(':',1)[1].strip() for x in (p/'status').read_text().splitlines() if x.startswith('Cpus_allowed_list:'))
 paths={}
 for line in (p/'maps').read_text().splitlines():
  parts=line.split(maxsplit=5)
  if len(parts)<6 or not parts[5].startswith('/'): continue
  raw=parts[5]
  if raw.endswith(' (deleted)'): raise ValueError('deleted mapping')
  path=str(pathlib.Path(raw).resolve())
  if path not in pins: raise ValueError('unlisted mapped file '+path)
  st=os.stat(path)
  if int(parts[4])!=st.st_ino: raise ValueError('mapping inode changed')
  paths[path]=pins[path]
 k=pathlib.Path('/sys/class/kfd/kfd/proc')/str(pid); present=k.exists();vram={}
 if present:
  for f in k.glob('vram_*'): vram[f.name]=int(f.read_text().strip())
 return dict(time=time.time(),pid=pid,birth=actual,affinity=affinity,maps=paths,kfd_present=present,vram=vram)
def one(argv,env,dest,stop,deadline,pins,guard=ref.stopcheck):
 dest.mkdir(); ref.write_json(dest/'argv.json',dict(argv=argv,env=env)); samples=[]; child=None;begin=time.time()
 try:
  with (dest/'stdout.txt').open('wb') as out,(dest/'stderr.txt').open('wb') as err:
   child=subprocess.Popen(argv,env=env,stdout=out,stderr=err)
   p=pathlib.Path('/proc')/str(child.pid);st=(p/'stat').read_text();birth=int(st[st.rfind(')')+2:].split()[19])
   while child.poll() is None:
    guard(stop,deadline); samples.append(sample(child.pid,birth,pins));time.sleep(.2)
   rc=child.wait();end=time.time()
 finally:
  if child is not None and child.poll() is None:
   child.terminate()
   try:child.wait(timeout=5)
   except subprocess.TimeoutExpired:child.kill();child.wait()
  ref.write_json(dest/'samples.json',samples)
 raw=(dest/'stdout.txt').read_text(encoding='utf-8');err=(dest/'stderr.txt').read_text(errors='replace')
 if rc or 'error:' in err.lower() or 'Successfully loaded Parakeet model' not in err or 'Processing file:' not in err or not raw.strip() or not raw.endswith('\n'): raise ValueError('CLI failed')
 if 'CPU_OBSERVER graph pid=' not in err.split('Processing file:',1)[1]: raise ValueError('no graph in audio window')
 evaluation=check(err,samples,child.pid,birth,pins,begin,end)
 ref.write_json(dest/'cpu-proof.json',dict(pid=child.pid,birth=birth,start=begin,end=end,**evaluation))
 return dict(rc=rc,transcript=raw,pid=child.pid,started_epoch_s=begin,files={n:ref.sha(dest/n) for n in ('stdout.txt','stderr.txt','argv.json','samples.json','cpu-proof.json')})
def main():
 out=pathlib.Path(sys.argv[1]);mode=sys.argv[2]
 if mode not in ('canary','full'):raise ValueError('mode')
 stop=pathlib.Path(os.environ['FILLER_STOPFILE']);deadline=int(os.environ['FILLER_DEADLINE'])-30
 ref.stopcheck(stop,deadline);out.mkdir(parents=True,exist_ok=False)
 pins=json.loads((D/'library-pins.json').read_text())
 for path,h in pins.items():
  if ref.sha(pathlib.Path(path))!=h:raise ValueError('library changed '+path)
 (out/'library-pins.json').write_bytes((D/'library-pins.json').read_bytes())
 grant=pathlib.Path(os.environ["REFERENCE_GRANT"]); grant_content=grant.read_bytes()
 def guard(stop,deadline):
  ref.stopcheck(stop,deadline)
  if not grant.exists() or grant.read_bytes()!=grant_content: raise RuntimeError("grant revoked or changed")
  flags=pathlib.Path("/mnt/raid0/llm/tmp/compute-flags")
  if any(flags.glob("HOLD_*")):raise RuntimeError("HOLD")
 guard(stop,deadline)
 rows=ref.validate_corpus();declare=ref.predeclare(out,'cpu',rows)
 declare['env']['LD_PRELOAD']=str(D/'observer.so')
 declare.update(observer_sha256=ref.sha(D/'observer.so'),observer_source_sha256=ref.sha(D/'observer.c'),runner_sha256=ref.sha(D/'cpu_runner.py'),proof_sha256=ref.sha(D/'proof.py'),pins_sha256=ref.sha(out/'library-pins.json'),cpu_proof='CPU-only devices, schedulers, direct graphs and host weight buffers; per-PID no VRAM throughout child; KFD presence permitted',mode=mode)
 ref.write_json(out/'predeclare.json',ref.seal(declare));ref.precheck(out,stop,deadline,rows)
 results=[]
 for i,r in enumerate(rows[:1] if mode=='canary' else rows):
  res=one(declare['argv'][i],declare['env'],out/f'{i:02d}',stop,deadline,pins,guard)
  results.append(dict(clip_id=r['clip_id'],pcm_sha256=r['pcm_sha256'],wav_sha256=r['wav_sha256'],source_wav_sha256=r['source_wav_sha256'],**res));ref.write_json(out/'partial-results.json',results)
 for path,h in pins.items():
  if ref.sha(pathlib.Path(path))!=h:raise ValueError('library changed after run '+path)
 ref.write_json(out/'COMPLETE.json',ref.seal(dict(schema='epyc.parakeet-cpu-observed.v2',leg='cpu',mode=mode,evidence_root=str(out.resolve()),preload_sha256=ref.sha(out/'preload.json'),results=results)))
if __name__=='__main__':
 for sig in (signal.SIGINT,signal.SIGTERM): signal.signal(sig,ref.signal_error)
 main()
