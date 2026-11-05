import json,os,signal,sys,time
from pathlib import Path
from validate import D,validate,check
STOPPED=False
def stopped(signum,frame):
 global STOPPED
 STOPPED=True
for s in (signal.SIGTERM,signal.SIGINT): signal.signal(s,stopped)
def guard():
 check(not STOPPED and not (D/'STOP').exists() and not Path(os.getenv('FILLER_STOPFILE',str(D/'STOP'))).exists(),'STOP')
 if os.getenv('FILLER_DEADLINE'): check(time.time()<float(os.environ['FILLER_DEADLINE']),'grant deadline')
try:
 guard()
 r=json.loads((D/'out/full/RESULT.json').read_text())
 a=json.loads((D/'out/full/attempt.json').read_text())
 check(a['result_path']==str(D/'out/full/RESULT.json'),'result path mismatch')
 guard()
 validate(r,a,False)
 guard()
except Exception:
 sys.exit(1)
