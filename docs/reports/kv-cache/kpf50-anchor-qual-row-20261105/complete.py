import json,os
from pathlib import Path
ROW='kpf50-anchor-qual-20261105'
D=Path(__file__).resolve().parent
smoke=os.environ.get('FILLER_DRYRUN')=='1' or os.environ.get('FILLER_SMOKE')=='1'
p=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'full-results/RESULT.json'
try:
    if smoke and (p.resolve()==D/'full-results/RESULT.json' or D/'full-results' in p.resolve().parents):raise ValueError('isolation')
    r=json.loads(p.read_text())
    names=['positive','changed-root'] if smoke else ['positive','changed-root','changed-dependency','symlink-alias','missing-file']
    ok=(r.get('row_id')==ROW and r.get('schema')=='kpf50.anchor-qualification.v1' and r.get('status')==('SMOKE_ONLY' if smoke else 'SYNTHETIC_ANCHOR_QUALIFIED') and r.get('smoke') is smoke and r.get('partial') is smoke and r.get('scan_complete') is (not smoke) and r.get('cleanup_confirmed') is True and r.get('target_enabled') is False and [c['case'] for c in r['cases']]==names and all(c.get('matched') is True and c.get('pidfd_dead_verified') is True and c['actual']==c['expected'] and c['rc']==c['expected_rc'] for c in r['cases']))
except Exception:ok=False
raise SystemExit(0 if ok else 1)
