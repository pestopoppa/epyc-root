import json
from pathlib import Path
b=Path(__file__).resolve().parent
try:
 r=json.loads((b/'out/RESULT.json').read_text());e=json.loads((Path(r['run_dir'])/'END.json').read_text())
 assert r['status']=='PASS' and r['classification']=='MODEL_FREE_QUALIFICATION' and r['rc']==0 and r['own_pid_dead']
 assert [c['case'] for c in r['cases']]==['positive','duplicate','multi_layout','foreign_task','foreign_slot','truncated']
 assert not r['cases'][0]['refused'] and r['cases'][0]['entries']==['compare'] and r['cases'][0]['boundary']==[1,10]
 assert all(c['refused'] and c['judge_entries']==[] for c in r['cases'][1:])
 assert e['rc']==0 and e['own_pid_dead'] and r['pre_seal']==r['post_seal'] and r['pre_seal']
except Exception: raise SystemExit(1)
