#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/autokernel-all-devices-all-dimensions/hip-build-prereq-repair-20261104')
p=D/'attempt-1/RESULT.json'
if not p.is_file(): raise SystemExit('full HIP build result missing')
r=json.loads(p.read_text())
if r.get('schema')!='akx-all-31-gdn.hip-build-result.v1' or r.get('status')!='built': raise SystemExit('wrong prerequisite result identity')
m=Path(r['manifest_path'])
if hashlib.sha256(m.read_bytes()).hexdigest()!=r.get('manifest_sha256'): raise SystemExit('HIP build manifest digest changed')
obj=json.loads(m.read_text())
if obj.get('schema')!='akx-all-31-gdn.hip-build-manifest.v1' or obj.get('native_op_executed') or obj.get('auto_kernel_runtime_invoked'): raise SystemExit('invalid build-only manifest')

for artifact in [obj['binary'],obj['hip_object']]:
 path=Path(artifact['path'])
 if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=artifact['sha256']: raise SystemExit(f'build artifact changed: {path}')
for name,digest in obj['libraries'].items():
 if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=digest: raise SystemExit(f'library changed: {name}')
print('HIP_BUILD_PREREQUISITE_COMPLETE')
