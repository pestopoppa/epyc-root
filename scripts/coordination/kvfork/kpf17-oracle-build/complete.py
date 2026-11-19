#!/usr/bin/env python3
import hashlib,json,pathlib,subprocess,sys
D=pathlib.Path('/mnt/raid0/llm/tmp/kvfork/kpf17-oracle-build-20261104')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
try:
 r=json.loads((D/'out/RESULT.json').read_text());assert r['schema']=='kpf17.oracle-build.v1' and r['status']=='BUILT'
 assert r['source_commit']=='8952a0f693fb923918157eb25117641b74766230'
 assert r['patched_test_sha256']=='b2f7085c3b772b58d6e9eb5ec33f217f22e9e1987bb8f51f040094eb586ef2ab'
 assert r['oracle_header_sha256']=='90787c4a526d2dedd3d3d11bf944ea81eeb1c2efd77e5e6862e8e69a57b26249'
 subprocess.run(['python3',str(D/'check.py')],check=True,stdout=subprocess.DEVNULL)
 assert all(sha(pathlib.Path(p))==h for p,h in r['files'].items())
 assert all(sha(pathlib.Path(p))==h for p,h in r['compiler_sha256'].items())
except (OSError,KeyError,ValueError,AssertionError,subprocess.CalledProcessError):sys.exit(1)
