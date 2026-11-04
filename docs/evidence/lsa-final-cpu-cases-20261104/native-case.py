#!/usr/bin/env python3
import hashlib,json,os,pathlib,subprocess,sys,time
D=pathlib.Path(__file__).resolve().parent
name,binary,*args=sys.argv[1:]; out=D/name; out.mkdir(); ready=out/'ready'; release=out/'release'
a=json.loads((D/'approved-cpu.json').read_text()); pins={str(pathlib.Path(x['path']).resolve()):x['sha256'] for x in a['artifacts'] if x['role'] in ('ggml_dso','llama_dso')}
env=dict(os.environ,LSA_LOAD_READY=str(ready),LSA_LOAD_RELEASE=str(release),LD_PRELOAD=str(D/'load-witness.so')+':'+a['exec_guard'])
with (out/'unit.log').open('wb') as log:
 p=subprocess.Popen([binary,*args],env=env,stdout=log,stderr=subprocess.STDOUT)
 try:
  until=time.monotonic()+60
  while not ready.exists():
   if p.poll() is not None or time.monotonic()>until: raise RuntimeError('load witness absent')
   time.sleep(.01)
  assert ready.read_text().strip()==str(p.pid)
  maps=set()
  for line in pathlib.Path(f'/proc/{p.pid}/maps').read_text().splitlines():
   n=line.split()[-1]
   if n.startswith('/') and ('libggml' in n or 'libllama' in n): maps.add(str(pathlib.Path(n).resolve()))
  assert maps==set(pins),(maps,set(pins))
  actual={p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in maps}; assert actual==pins
  release.write_text('release\n'); rc=p.wait(timeout=240)
 finally:
  if p.poll() is None: p.terminate(); p.wait(timeout=5)
(out/'witness.json').write_text(json.dumps({'pid':p.pid,'rc':rc,'mapped_dsos_sha256':actual,'argv':[binary,*args]},indent=2)+'\n')
sys.exit(rc)
