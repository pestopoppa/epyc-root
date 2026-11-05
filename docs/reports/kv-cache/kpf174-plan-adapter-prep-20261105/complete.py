import json
from pathlib import Path
b=Path(__file__).resolve().parent
try:
 r=json.loads((b/'out/RESULT.json').read_text()); e=json.loads((Path(r['run_dir'])/'END.json').read_text())
 assert r['status']=='PASS' and r['classification']=='MODEL_FREE_QUALIFICATION' and r['rc']==0 and r['own_pid_dead'] and len(r['cases'])==10
 assert e['rc']==0 and e['own_pid_dead'] and r['pre_seal']==r['post_seal'] and r['pre_seal']
except Exception: raise SystemExit(1)
