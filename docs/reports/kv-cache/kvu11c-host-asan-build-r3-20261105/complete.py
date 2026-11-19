import hashlib,json,os,sys
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kvu11c-asan-build-20261105/packet-r3')
p=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if os.environ.get('FILLER_SMOKE')=='1' or os.environ.get('FILLER_DRYRUN')=='1' else D/'out/RESULT.json'
r=json.loads(p.read_text()); assert r['schema']=='kvu11c.host-asan-build.v1' and r['status'] in ('SMOKE','BUILT')
assert len(r['files'])==(1 if r['status']=='SMOKE' else 5)
assert all(hashlib.sha256(Path(n).read_bytes()).hexdigest()==d for n,d in r['files'].items())
