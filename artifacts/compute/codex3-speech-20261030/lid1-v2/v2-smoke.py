import json,os,subprocess,sys,time
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/codex3-cs26-lid1-20261030/v2-smoke-normal');env=os.environ.copy();env.update(CS26_SMOKE='1',FILLER_END=str(time.time()+255),FILLER_STOPFILE=str(D/'STOP'),HIP_VISIBLE_DEVICES='-1',ROCR_VISIBLE_DEVICES='-1')
for model in ('tiny','base','large-v3-turbo','silero','firered'):
 env['LD_LIBRARY_PATH']='/mnt/micron/codex3-cs8-stt2-crisp-20261030/install/lib' if model in ('silero','firered') else '/mnt/raid0/llm/whisper.cpp/build/bin'
 p=subprocess.run([sys.executable,str(D/'job.py'),model],env=env,timeout=200);s=json.loads((D/'results'/model/'status.json').read_text());assert p.returncode==0 and s['started']==2 and s['outcomes']==2 and s['unknown']==0 and s['worker_returncodes']==[0,0],s
 for path in (D/'results'/model).glob('worker-*.jsonl'):
  x=[json.loads(l) for l in path.read_text().splitlines()];assert x[-1]['status']=='ok',x[-1]
 print('writer-drain-ok',model,flush=True)
