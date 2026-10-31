#!/usr/bin/env python3
"""Recognize only the full immutable A3/B3 capture, never qualification output."""
import hashlib,json,pathlib,sys
G=pathlib.Path(__file__).resolve().parent;O=G/'out'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def complete(root=O):
 r=json.loads((root/'RESULT.json').read_text())
 assert r['schema']=='ni.gpu_zos23_one_extra_capture.v1'
 assert r['capture_complete'] is True and r['qualification_only'] is False and r['partial'] is False
 assert r['verdict']=='ATOMIC_DIAGNOSTIC_EXTENSION_CAPTURED' and r['ship_authorized'] is False and r['original_parent_complete'] is False
 assert set(r['arms'])=={'A1','B1','A2','B2','A3','B3'}
 for arm in ('A3','B3'):
  path=root/arm/'waves.jsonl';seal=json.loads((root/arm/'COMPLETE.json').read_text())
  assert seal['arm']==arm and seal['waves']==6
  assert seal['files']['waves.jsonl']==sha(path)==r['arms'][arm]['sha256']
  assert pathlib.Path(r['arms'][arm]['waves_path']).resolve()==path.resolve()
  waves=[json.loads(x) for x in path.read_text().splitlines()]
  assert [w['wave'] for w in waves]==list(range(7))
  counted=waves[1:];assert all(w['max_tokens']==1024 and len(w['responses'])==4 for w in counted)
  rows=[x for w in counted for x in w['responses']];assert len(rows)==24 and rows==r['arms'][arm]['responses']
  assert all(len(x['tokens'])==1024 and x['tokens_predicted']==1024 and x['timings']['predicted_per_second']>0 for x in rows)
 return True
if __name__=='__main__':
 try:complete();print('FULL_CAPTURE_COMPLETE');sys.exit(0)
 except (OSError,ValueError,KeyError,AssertionError,TypeError):sys.exit(1)
