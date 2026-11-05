import json,sys
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text())
if r.get('status')!='PASS' or r.get('processes_spawned')!=0 or r.get('gpu_accessed') is not False: raise SystemExit(1)
n=4 if r.get('mode')=='SMOKE_ONLY' else 18 if r.get('mode')=='MODEL_FREE_QUALIFICATION' else -1
if len(r.get('controls',[]))!=n or not all(c.get('matched') is True for c in r['controls']): raise SystemExit(1)
