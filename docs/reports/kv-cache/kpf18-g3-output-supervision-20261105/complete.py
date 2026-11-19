import json,os,time
from pathlib import Path
p=Path(os.environ['QUAL_RESULT']);r=json.loads(p.read_text())
assert r['schema']=='kpf18.g3.isolated-output-supervision.v1' and r['status']=='PASS' and r['tests']==6
assert [c['case'] for c in r['controls']]==['normal','growth','stop','deadline','failure','detached']
assert all(c['receipt']['pid_absent'] and c['receipt']['children_after']==[] for c in r['controls'])

g=r['grant_boundary']
assert isinstance(g,dict) and g['stop_absent'] is True
assert type(g['end']) is int and type(g['checked_at']) in (int,float)
assert g['checked_at']<g['end']
stop=Path(g['stopfile'])
assert stop.is_absolute() and stop.name=='STOP'
# Recheck the child-recorded boundary without relying on inner-only environment.
assert not stop.exists() and not stop.is_symlink()
assert time.time()<g['end']
