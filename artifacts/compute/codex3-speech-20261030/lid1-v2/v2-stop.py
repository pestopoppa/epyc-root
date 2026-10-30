import json,os,signal,subprocess,sys,time
from pathlib import Path
base=Path('/mnt/raid0/llm/tmp/codex3-cs26-lid1-20261030')
for kind,model,lib in (('whisper','large-v3-turbo','/mnt/raid0/llm/whisper.cpp/build/bin'),('crisp','firered','/mnt/micron/codex3-cs8-stt2-crisp-20261030/install/lib')):
 d=base/f'v2-smoke-stop-{kind}';env=os.environ.copy();env.update(CS26_SMOKE='1',FILLER_END=str(time.time()+240),FILLER_STOPFILE=str(d/'STOP'),LD_LIBRARY_PATH=lib,HIP_VISIBLE_DEVICES='-1',ROCR_VISIBLE_DEVICES='-1');cmd=[sys.executable,str(d/'job.py'),model];p=subprocess.Popen(cmd,env=env);started=time.monotonic()
 while time.monotonic()-started<90:
  paths=list((d/'results'/model).glob('worker-*.jsonl.active'))
  if len(paths)==2:break
  if p.poll() is not None:raise RuntimeError('early exit')
  time.sleep(.01)
 else:raise RuntimeError('timeout before active')
 p.send_signal(signal.SIGTERM);rc=p.wait(timeout=20);s=json.loads((d/'results'/model/'status.json').read_text());assert rc==75 and s['started']==2 and s['unknown']==2 and s['outcomes']==0,s
 p=subprocess.run(cmd,env=env,timeout=90);s=json.loads((d/'results'/model/'status.json').read_text());assert p.returncode==75 and s['unknown']==2 and s['outcomes']==0,s
 print('stop-drain-resume-ok',model,json.dumps(s),flush=True)
