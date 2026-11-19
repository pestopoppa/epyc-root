import json,sys,pathlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from decode import decode
cases=json.loads(pathlib.Path(__file__).with_name('inputs.json').read_text())
print('READY',flush=True)
if sys.stdin.readline().strip()!='GO':sys.exit(64)
records=[]
for c in cases:
 r=decode(c['input'])
 ok=r.get('status')==c['expected_status'] and r.get('native_binding')=='UNKNOWN' and r.get('historical_control')=='UNKNOWN'
 if c['expected_structural'] is not None:ok=ok and r.get('structural_status')==c['expected_structural']
 if 'expected_reason' in c:ok=ok and r.get('reason')==c['expected_reason']
 records.append(dict(case=c['case'],passed=ok,result=r))
print(json.dumps(records),flush=True)
if sys.stdin.readline().strip()!='ACK':sys.exit(64)
sys.exit(0 if all(r['passed'] for r in records) else 1)
