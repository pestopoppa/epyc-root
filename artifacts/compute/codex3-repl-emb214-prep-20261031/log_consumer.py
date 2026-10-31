#!/usr/bin/env python3
import collections,json,pathlib,sys
d=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else pathlib.Path(__file__).resolve().parent/'run';c=collections.Counter()
for p in sorted(d.glob('*.pair.json')):
 try:c[json.loads(p.read_text()).get('status','unknown')]+=1
 except Exception:c['unreadable']+=1
print(json.dumps({'pairs':sum(c.values()),'statuses':dict(c)}))
for n in ('PARTIAL.json','TERMINAL.json'):
 p=d/n
 if p.exists():print(n,p.read_text().strip())
