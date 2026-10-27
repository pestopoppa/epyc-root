#!/usr/bin/env python3
import hashlib, json, os, signal, subprocess, sys, time, urllib.request
from pathlib import Path
import collect
B=collect.BASE
BIN=Path('/mnt/raid0/llm/tmp/repl-emb-211-20261024/llama-src/build-cpu/bin')
MODEL=Path('/mnt/raid0/llm/tmp/repl-emb-211-20261024/gguf/embeddinggemma-2-BF16.gguf')
LINK='/workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh'
PORT='18993'
REFCMD=Path('/mnt/raid0/llm/tmp/repl-emb-25-26-20261020/q/cmd-07-stgate-probe45.sh.done')
def owns_port(pid, port):
 inodes=set()
 for row in Path('/proc/net/tcp').read_text().splitlines()[1:]:
  fields=row.split()
  if fields[1]==f'0100007F:{int(port):04X}' and fields[3]=='0A': inodes.add(fields[9])
 for fd in Path(f'/proc/{pid}/fd').iterdir():
  try: target=os.readlink(fd)
  except FileNotFoundError: continue
  if target.startswith('socket:[') and target[8:-1] in inodes: return True
 return False

def main():
 out=B/'out'
 if out.exists() or (B/'COMPLETE.json').exists(): raise RuntimeError('stale output')
 if collect.digest(BIN/'llama-server')!='a2e62037e37ff0391017bd68fec421f271f94c2dfb1df3e767ff45abeeb4c01b' or collect.digest(MODEL)!='68bae29d62fb8c7d23e98d21fd4662753ddd636e6b62b8a70dfe059a9844f216': raise RuntimeError('binary or model digest mismatch')
 work=B/'run'; work.mkdir(exist_ok=False)
 env=os.environ.copy(); env['LD_LIBRARY_PATH']=str(BIN)
 with (work/'linkage.txt').open('w') as f: subprocess.run(['bash',LINK,str(BIN/'llama-server'),str(BIN)],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 argv=[str(BIN/'llama-server'),'-m',str(MODEL),'--host','127.0.0.1','--port',PORT,'-np','4','-c','8192','-t','4','--embeddings','--pooling','mean','-b','2048','-ub','2048','--embd-normalize','2','--no-mmap','-lv','3']
 proc=None; failure=None
 try:
  with (work/'server.log').open('w') as log:
   proc=subprocess.Popen(argv,env=env,stdout=log,stderr=subprocess.STDOUT)
   for _ in range(180):
    if proc.poll() is not None: raise RuntimeError('server exited')
    try:
     with urllib.request.urlopen('http://127.0.0.1:'+PORT+'/health',timeout=1) as r:
      if r.status==200: break
    except OSError: time.sleep(1)
   else: raise RuntimeError('server health timeout')
   if not owns_port(proc.pid,PORT): raise RuntimeError('server does not own health port')
   affinity=sorted(os.sched_getaffinity(proc.pid))
   if affinity != list(range(72,96)): raise RuntimeError('server CPU affinity differs from q3 claim')
   (work/'server-affinity.json').write_text(json.dumps(affinity))
   maps=Path(f'/proc/{proc.pid}/maps').read_text(); (work/'server-maps.txt').write_text(maps)
   libs={line.split()[-1] for line in maps.splitlines() if '/libggml' in line and '/' in line.split()[-1]}
   if not libs or any(not str(Path(x).resolve()).startswith(str(BIN.resolve())+'/') for x in libs): raise RuntimeError('foreign or absent ggml mappings')
   (work/'mapped-library-digests.json').write_text(json.dumps({x:collect.digest(Path(x)) for x in sorted(libs)},indent=2))
   text=(work/'server.log').read_text()
   on='Flash Attention enabled' in text; off='Flash Attention not supported, set to disabled' in text
   if on==off: raise RuntimeError('flash attention resolution absent or ambiguous')
   meta={'st-fp32-full':{'runtime':'sentence-transformers/transformers/torch-cpu','argv':['bash',str(REFCMD)],'versions':{'torch':'2.14.1+cpu','transformers':'5.20.1','sentence_transformers':'6.1.0'},'flash_attn_requested':'n/a','flash_attn_resolved':'n/a'},'gguf-bf16':{'runtime':'llama-server CPU','argv':argv,'binary_sha256':collect.digest(BIN/'llama-server'),'flash_attn_requested':'auto','flash_attn_resolved':'on' if on else 'off'}}
   (work/'runtime-meta.json').write_text(json.dumps(meta,indent=2))
   collect.run('http://127.0.0.1:'+PORT,out,meta)
 except BaseException as exc: failure=exc
 finally:
  if proc is not None:
   if proc.poll() is None: proc.terminate()
   try: proc.wait(timeout=10)
   except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=10)
   if proc.poll() is None: raise RuntimeError('server cleanup failed')
 if failure: raise failure
 (B/'COMPLETE.json').write_text(json.dumps({'result':str(out/'RESULT.json'),'server_reaped':True},indent=2))
def interrupted(signum, frame): raise RuntimeError(f'interrupted by signal {signum}')
if __name__=='__main__':
 for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP): signal.signal(sig,interrupted)
 main()
