#!/usr/bin/env python3
import json,pathlib
D=pathlib.Path(__file__).resolve().parent
for p in sorted(D.glob('results/**/job-result*.json')):
 x=json.loads(p.read_text());print(json.dumps({'path':str(p),'status':x.get('status'),'partial':x.get('partial'),'reason':x.get('reason'),'run':x.get('run')},sort_keys=True))
p=D/'ws58-launcher.out'
if p.exists():print(json.dumps({'path':str(p),'bytes':p.stat().st_size}))
