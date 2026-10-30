#!/usr/bin/env python3
import json,sys,sqlite3
from pathlib import Path
cmd,*a=sys.argv[1:]
if cmd=='prepare':
 src,n,i,dst,scratch=a; tasks=json.loads(Path(src).read_text()); key=f'filter-{n}'
 t=next(t for t in tasks if t['task_key']==key).copy(); t['task_key']=f'{key}-p{i}'
 old=f'/mnt/raid0/llm/tmp/refactor-01a16fc3/hil15b-four-family-api-v2/source-scratch/{key}.csv'
 new=str(Path(scratch)/f'{key}-p{i}.csv'); t['prompt']=t['prompt'].replace(old,new); assert old not in t['prompt'] and 'source-scratch/' not in t['prompt'] and new in t['prompt']; assert t['family'] != 'join' or new+'.b' in t['prompt']; Path(dst).write_text(json.dumps([t],indent=2)+'\n')
elif cmd=='validate':
 attempt,n=Path(a[0]),a[1]
 for i in range(3):
  d=attempt/f'driver-{i}'; m=json.loads((d/'manifest.json').read_text()); expected=f'filter-{n}-p{i}-r0'
  assert m['mock'] is False and m['verdict']=='OK' and len(m['runs'])==1 and m['runs'][0]['run_id']==expected
  flags={'ORCHESTRATOR_OBSERVED_DEPENDENCY_LOGGING','ORCHESTRATOR_STEP_EVENT_LOGGING','ORCHESTRATOR_REPLAY_RECORDING'}
  assert set(m['flags']) == flags
  conn=sqlite3.connect(f'file:{d / "events.sqlite"}?mode=ro',uri=True)
  row=conn.execute("select detail_json from event where category='model_turn' and session_id=? order by id limit 1",(expected,)).fetchone(); conn.close()
  assert row
  seed=json.loads(row[0])['seed']; assert all(seed['env'].get(f)=='1' for f in flags)
  assert all(seed['features'].get(f.lower().removeprefix('orchestrator_')) is True for f in flags)
  j=m['join']
  assert j['task_runs']==1
  if j['step_bearing_runs']==1: assert j['joined_outcome']==1 and (j.get('join_ok',True) is True)
  else: assert j['step_bearing_runs']==0 and j['joined_outcome']==0 and j.get('join_ok') is True and j.get('zero_step_recorded_failed')==[expected] and m['runs'][0]['pass'] is False
  assert set(m['replay_verify'])=={expected} and m['replay_verify'][expected]['rc']==0
  assert m['l2_scan']['rc']==0
  report=json.loads((d/'l2_report.json').read_text())
  counts=report['n']; passed=m['runs'][0]['pass']
  assert type(passed) is bool and counts['traces']==1 and counts['unknown_outcome']==0
  assert counts['passed']==int(passed) and counts['failed']==int(not passed)
  auc=json.loads((d/'auc_table.json').read_text())
  # Canonical dependency_features.load_runs counts tool_dependency runs,
  # not every task/model/tool_step run. A retained zero-dependency run is
  # a known answer outcome with an insufficient 0/0 AUC, never an AUC gain.
  labels=json.loads((d/'labels.json').read_text())
  assert labels=={expected:[m['runs'][0]['task_key'],passed]}
  with sqlite3.connect(f'file:{d / "events.sqlite"}?mode=ro',uri=True) as db:
   dep_ids={json.loads(row[0])['run_id'] for row in db.execute("select detail_json from event where category='tool_dependency' order by id")}
  assert dep_ids <= {expected}
  auc_ids=dep_ids & labels.keys()
  expected_auc={'status':'insufficient','n_runs':len(auc_ids),'n_tasks':len({labels[r][0] for r in auc_ids})}
  assert auc==m['auc_table']==expected_auc
 print('complete unit',n)
else: raise SystemExit('unknown command')
