import json,os
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/gpu-serving-tie-in/p5-gold-offline-r3')
x=json.loads((D/'RESULT.json').read_text())
assert x['schema']=='p5.gold-control.v1'
assert x['status']=='PASS' and set(x['arms'])=={'negative','gold'}

assert x.get('owned_containers_removed') is True
assert not x.get('error') and not x.get('cleanup_error')
for arm, native in x['arms'].items():
 assert native['FAIL_TO_PASS'] and native['PASS_TO_PASS']
 assert all(v == 'PASSED' for v in native['PASS_TO_PASS'].values())
 if arm == 'gold':
  assert native['resolved'] is True and all(v == 'PASSED' for v in native['FAIL_TO_PASS'].values())
 else:
  assert native['resolved'] is False and any(v == 'FAILED' for v in native['FAIL_TO_PASS'].values())

import hashlib
for name, key in [('SOURCE.sha256','producer_source_manifest_sha256'),('launch.sh','producer_launcher_sha256')]:
 assert x[key] == hashlib.sha256((D/name).read_bytes()).hexdigest()
