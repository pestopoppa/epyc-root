#!/usr/bin/env python3
"""Reject partial, skipped, or changed diagnostic artifacts; this is not a defect gate."""
import hashlib,json,pathlib,sys
D=pathlib.Path('/mnt/raid0/llm/tmp/kvfork/kpf17-partial-row-v2')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
try:
 r=json.loads((D/'out/RESULT.json').read_text()); assert r['schema']=='kpf17.partial.busy-source.diagnostic.v1'
 assert r['status']=='OBSERVED_PASS' and r['rc']==0 and r['marker'] is True and r['skip'] is False
 assert r['source_commit']=='a1f0c8cf9bd7102415a72577474f307b8ba94db9' and r['patched_test_sha256']=='33c2e9e54376515febeae3531ef4f5fa7038033bf7589516fda5a732428d0d5f'
 assert r['model']==json.loads((D/'model.json').read_text())
 assert sha(D/'build/bin/test-save-load-state')==r['binary_sha256']
 assert sha(D/'out/test.log')==r['test_log_sha256'] and sha(D/'out/linkage.log')==r['linkage_log_sha256']
 libs=r['linked_libraries']; assert any(k.startswith('libggml') for k in libs) and any(k.startswith('libllama') for k in libs)
 for v in libs.values():
  p=pathlib.Path(v['path']).resolve(strict=True); assert p.parent==(D/'build/bin').resolve() and sha(p)==v['sha256']
except (OSError,ValueError,KeyError,TypeError,AssertionError):sys.exit(1)
