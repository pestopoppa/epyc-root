import json, os, sys
from pathlib import Path
D=Path(__file__).resolve().parent
p=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if os.environ.get('FILLER_DRYRUN')=='1' else D/'RESULT.json'
try:
 r=json.loads(p.read_text()); prep=json.loads((D/'PREPARED.json').read_text())
 assert r['id']=='cross-keep-c6-mmq-n5-20261104' and r['dryrun']==(os.environ.get('FILLER_DRYRUN')=='1')
 assert r['ordinal']==7047 and r['native_rc']==0 and r['input_bytes_equal'] is True and r['route']=='MMQ' and r['residual']<=r['tolerance']==float(prep['tolerance'])
 assert r['source_build_sha256']==prep['build_receipt_sha256'] and r['candidate_hip_sha256']==prep['hip_sha256'] and r['binary_sha256']==prep['binary_sha256'] and r['cleanup'] is True and r['full_gak_pass'] is None
except Exception as e:
 print('INCOMPLETE',e,file=sys.stderr);sys.exit(1)
