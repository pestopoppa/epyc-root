import json,os,time
from pathlib import Path
r=json.loads(Path(os.environ['QUAL_RESULT']).read_text()); b=r['boundary']; stop=Path(b['stop'])
assert r['row_id']=='kpf18-g3-integrated-cell-qual-20261105' and r['schema']=='kpf18.g3.integrated-cell.v1' and r['status']=='PASS' and r['tests']==4
assert stop==Path(os.environ['QUAL_EXPECTED_STOP']) and not stop.exists() and not stop.is_symlink() and b['checked_at']<b['end'] and time.time()<b['end']
