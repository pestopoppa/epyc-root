"""One sampled model-free source check, for smoke only."""
import os,sys,time
from pathlib import Path
import campaign_supervisor as supervisor
D=Path(__file__).resolve().parent
out=D/('codex3-evl34-r11-v7-preflight-'+str(os.getpid())+'-'+str(time.time_ns())+'.log')
supervisor.FLOOR=0
result=supervisor.supervise(['/bin/bash','-c','sha256sum --quiet -c "$1/PACKET.sha256" && exec /mnt/micron/codex3-evl34-deepdive-r9-20261030/bin/python3.11 -B "$1/source_closure.py"','_',str(D)],str(out),seconds=120,disk_path='/mnt/micron/codex3-evl34-deepdive-r9-20261030')
if result['rc']!=0 or result['reason'] is not None or not result['drained']:raise RuntimeError('model-free preflight failed')
print(out)
