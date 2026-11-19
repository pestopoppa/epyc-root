#!/usr/bin/env python3
import hashlib,json,os,signal,shutil,subprocess,sys,tempfile,time
from pathlib import Path
D=Path(__file__).resolve().parent;B=D.parent;R=B/'repro';pkg=Path('/usr/local/share/npm-global/lib/node_modules/gitnexus');inp=Path('/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/llama-native-c5/ggml/src/ggml-cpu/ops.cpp');digest=hashlib.sha256(inp.read_bytes()).hexdigest();assert digest=='f0d83af52edf9d41bd76a95dd9c07d7769c8f00369c4b09474f67f2114752e3d'
if os.environ.get('FILLER_DRYRUN')=='1':
 with tempfile.TemporaryDirectory(prefix='fixtures-',dir=D) as t:
  tmp=Path(t)
  for name in ['source-fix','candidate','enum-candidate']:
   source=B/name;dest=tmp/name;dest.mkdir();shutil.copy2(source/'package.json',dest/'package.json');shutil.copytree(source/'dist',dest/'dist');(dest/'node_modules').symlink_to(pkg/'node_modules',target_is_directory=True)
  cases=[('enum',R/'enum-regression.mjs',tmp/'candidate',tmp/'enum-candidate'),('graph',R/'progress-regression.mjs',tmp/'source-fix',tmp/'enum-candidate')]
  for label,script,a,b in cases:
   p=subprocess.run(['node',str(script),str(a),str(b)],capture_output=True,text=True,timeout=30);(D/f'{label}.stdout').write_text(p.stdout);(D/f'{label}.stderr').write_text(p.stderr)
   if p.returncode:sys.exit(p.returncode)
   with (D/'results.jsonl').open('a') as f:f.write(json.dumps({'unit':label,'status':'passed','output':p.stdout.strip()})+'\n')
  for _ in range(10):
   if Path(os.environ['FILLER_STOPFILE']).exists():break
   time.sleep(1)
 sys.exit(0)
start=time.monotonic()
with (D/'ops.out').open('w') as out,(D/'ops.err').open('w') as err,(D/'ops.samples').open('w') as samples:
 p=subprocess.Popen(['node','--max-old-space-size=2048',str(R/'enum-worker-canary.mjs'),str(inp)],stdout=out,stderr=err,start_new_session=True)
 while p.poll() is None and time.monotonic()-start<60 and not Path(os.environ['FILLER_STOPFILE']).exists():
  q=subprocess.run(['ps','-L','-p',str(p.pid),'-o','pid,tid,psr,stat,pcpu,rss,time,wchan:24'],capture_output=True,text=True);samples.write(f'elapsed={time.monotonic()-start:.3f}\n{q.stdout}');samples.flush();time.sleep(1)
 if p.poll() is None:
  os.killpg(p.pid,signal.SIGTERM)
  try:p.wait(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
  outcome='timeout' if not Path(os.environ['FILLER_STOPFILE']).exists() else 'stopped'
 else:outcome='completed' if p.returncode==0 and '"type":"result"' in (D/'ops.out').read_text() else 'failed'
record={'unit':'ops-fixed-worker','status':outcome,'seconds':round(time.monotonic()-start,3),'input_sha256':digest,'returncode':p.returncode}
with (D/'results.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
(D/'complete').write_text(outcome+'\n')
if outcome=='failed':sys.exit(1)
