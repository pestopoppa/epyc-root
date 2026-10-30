import glob,json,os
from native_projection import project_redel
paths=glob.glob('/mnt/raid0/llm/tmp/codex3-evl34-production-20261029/full-redel-synthetic-*/events.json');events=json.load(open(max(paths,key=os.path.getmtime)))
r=project_redel(events,{'prompt_tokens':50,'completion_tokens':10},True)
assert r['answer']=='fixture final' and r['delegations']==2 and r['max_depth']==1 and r['server_usage']['completion_tokens']==10
broken=[x for x in events if x['type']!='round_complete']
try:project_redel(broken,None,True)
except ValueError:pass
else:raise AssertionError('missing round accepted')
assert project_redel(events,None,True)['server_usage'] is None
print('actual synthetic native ReDel events projected; captured server usage retained, missing round refused')
