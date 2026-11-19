"""Explicit first progress: verify real native output, not measurement:false bookkeeping."""
import hashlib,json,os
from pathlib import Path
p=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']).resolve()
r=json.loads(p.read_text())
assert r['smoke'] is True and r['measurement'] is False
assert len(r['runs'])==1
x=r['runs'][0]
assert x['case']==80 and x['arm']=='base' and x['repeat']==1 and x['rc']==0
assert x['mapping'] and any(s['kfd'] and (s['vram_bytes'] or 0)>0 for s in x['samples'])
raw=p.parent/'kvu19a2-native-smoke'/'smoke-case80-base-r1'/'out_80.bin'
assert raw.is_file() and raw.stat().st_size>0
assert hashlib.sha256(raw.read_bytes()).hexdigest()==x['output_sha256']
assert p.stat().st_mtime>=float(os.environ['FILLER_SMOKE_T0'])

canonical=json.loads((Path(__file__).parent/'canonical-input-hashes.json').read_text())['cases']['80']
assert x['input_hashes']==canonical
