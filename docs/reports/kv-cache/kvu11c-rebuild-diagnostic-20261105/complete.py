#!/usr/bin/env python3
import hashlib,json,subprocess,sys,os
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/kvfork/kvu11c-rebuild-diagnostic-20261105')
try:
 subprocess.run([sys.executable,str(D/'check.py')],check=True,stdout=subprocess.DEVNULL)
 if os.environ.get('FILLER_SMOKE')=='1' or os.environ.get('FILLER_DRYRUN')=='1':
  r=json.loads(Path(os.environ['FILLER_DRYRUN_RESULT_PATH']).read_text())
  assert r['status']=='built-ggml-base-only' and r['bytes']>0 and len(r['sha256'])==64
  sys.exit(0)
 r=json.loads((D/'out/RESULT.json').read_text())
 assert r['schema']=='kvu11c.hip-build.v1' and r['status']=='BUILT' and r['qwentts_commit']=='aca703283192f892f1e85636fbc48832c4d5560a' and r['ggml_commit']=='b86f660238dcc1a83b7cbf5a72d355a965de9245' and len(r['files'])==5
 assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest for p,digest in r['files'].items())
except (OSError,ValueError,AssertionError,KeyError,subprocess.CalledProcessError): sys.exit(1)
