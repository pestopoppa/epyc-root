import json,sys
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/kvu/find-slot-native-v1')
try:
 r=json.loads((D/'out/RESULT.json').read_text()); a=json.loads((D/'out/attempt.json').read_text())
 assert r['schema']=='kpf131.native-findslot.v1' and r['status']=='FIXTURE_PASS' and r['smoke'] is False and r['case_count']==2
 assert a['row_id']==r['row_id']=='kvu-kpf131-old-native-findslot-20261104' and a['result_path']==str(D/'out/RESULT.json')
 assert len(a['nonce'])==48 and r['attempt_nonce']==a['nonce']
 assert [x['answer'] for x in r['records']]==['RESULT PASS 2 3','RESULT DETECTED 0 1']
 assert all(x['before']==x['after'] and len(x['before'])==5 for x in r['records'])
except Exception:sys.exit(1)
