import json,sys
from pathlib import Path
D=Path(__file__).resolve().parent
try:
 r=json.loads((D/'out/RESULT.json').read_text())
 assert r['status']=='PASS' and not r['smoke'] and r['case_count']==2 and len(r['records'])==2
 for x in r['records']: assert x['native']['hits']==2 and x['native']['exit_code']==0 and x['native']['before']==x['native']['after'] and x['cleanup_confirmed'] and x['gdb_rc']==0
except Exception as e:
 print(e,file=sys.stderr);sys.exit(1)
