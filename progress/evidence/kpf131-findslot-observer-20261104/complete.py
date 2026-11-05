import json,sys
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/kvu/observer-findslot-v1')
try:
 r=json.loads((D/'out/RESULT.json').read_text()); a=json.loads((D/'out/attempt.json').read_text())
 assert r['schema']=='kpf131.findslot-observer.v1' and r['status']=='OBSERVER_FIXTURE_PASS' and r['smoke'] is False and r['case_count']==2
 assert r['row_id']==a['row_id']=='kvu-kpf131-findslot-observer-20261104' and len(a['nonce'])==48 and r['attempt_nonce']==a['nonce']
 assert [x['answer'] for x in r['records']]==['RESULT PASS 2 3','RESULT DETECTED 0 1']
 assert all(x['capture']['exit_code']==0 and len(x['capture']['events'])==2 and x['capture']['events'][0]['mapped']==x['capture']['events'][1]['mapped'] and len(x['capture']['events'][0]['mapped'])==5 for x in r['records'])
except Exception:sys.exit(1)
