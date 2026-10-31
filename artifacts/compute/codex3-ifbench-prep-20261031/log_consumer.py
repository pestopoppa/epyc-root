#!/usr/bin/env python3
import collections,json,pathlib,sys
d=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else pathlib.Path(__file__).resolve().parent/'run';c=collections.Counter()
for p in sorted(d.glob('*.result.json')):
 try:c[json.loads(p.read_text()).get('status','UNKNOWN')]+=1
 except Exception:c['unreadable']+=1
print(json.dumps({'attempts':sum(c.values()),'statuses':dict(c),'correctness':'UNRUN','timing':'UNRUN'}))
for n in ('PARTIAL.json','TERMINAL.json','FAILURE.json'):
 p=d/n
 if p.exists():print(n,p.read_text().strip())
