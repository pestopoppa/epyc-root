import json,os
from pathlib import Path
D=Path(__file__).resolve().parent
p=Path(os.environ.get('RAM_RESULT',str(D/'out/full-attempt/RESULT.json')))
r=json.loads(p.read_text())
expected='SMOKE_ONLY' if os.environ.get('FILLER_SMOKE')=='1' or os.environ.get('FILLER_DRYRUN')=='1' else 'MODEL_FREE_QUALIFICATION'
assert r['status']=='PASS' and r['mode']==expected and r['cleanup_verified'] is True
assert len(r['controls'])==(4 if expected=='SMOKE_ONLY' else 28)
assert all(c['matched'] is True for c in r['controls'])
