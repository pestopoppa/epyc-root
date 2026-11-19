import os,json
from pathlib import Path
d=Path(__file__).resolve().parent
p=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if os.environ.get('FILLER_SMOKE')=='1' else d/'full-results/RESULT.json'
r=json.loads(p.read_text()); raise SystemExit(0 if r['status']=='PASS' and r['smoke']==(os.environ.get('FILLER_SMOKE')=='1') and r['row_id']=='kpf50-custody-qualification-20261105' else 1)
