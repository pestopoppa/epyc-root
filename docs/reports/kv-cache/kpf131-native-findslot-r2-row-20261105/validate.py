import hashlib,json,os
from pathlib import Path
D=Path(__file__).resolve().parent
ROW='kvu-kpf131-old-native-findslot-r2-20261104'
BIN='078cafd6e72d274f40d82c50012b0170f80d2f0d8e72f5574cca6f88e7de7d7d'
def check(value,message):
 if not value: raise ValueError(message)
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  while b:=f.read(1048576): h.update(b)
 return h.hexdigest()
def seal():
 pins=json.loads((D/'seal.json').read_text())
 for path,digest in pins.items(): check(sha(path)==digest,'seal mismatch: '+path)
 return sha(D/'seal.json')
def validate(r,a,smoke):
 check(r['schema']=='kpf131.native-findslot.v2' and r['status']=='FIXTURE_PASS','invalid result')
 check(r['row_id']==a['row_id']==ROW and r['smoke'] is smoke and a['smoke'] is smoke,'attempt mode mismatch')
 check(r['attempt_nonce']==a['nonce'] and len(a['nonce'])==48,'nonce mismatch')
 check(r['seal_sha256']==a['seal_sha256']==seal(),'seal changed')
 check(len(r['records'])==2 and r['case_count']==2,'case count')
 check(r['fixture_binary_sha256']==BIN and r['fixture_source_sha256']==sha(D/'fixture.cpp') and r['build_manifest_sha256']==sha(D/'build-manifest.json'),'fixture evidence binding')
 pins=json.loads((D/'pins.json').read_text())
 for rec,arm,ans in zip(r['records'],['honest','skip_apply'],['RESULT PASS 2 3','RESULT DETECTED 0 1']):
  check(rec['arm']==arm and rec['answer']==ans and type(rec['returncode']) is int and rec['returncode']==0,'answer or exact child rc')
  check(rec['pidfd_captured'] is True,'missing own-child pidfd receipt')
  check(rec['before']==rec['after'],'snapshot mismatch')
  s=rec['before']; check(s['pid']==rec['pid'] and s['birth_ticks']==rec['birth_ticks'] and s['birth_ticks']>0,'birth mismatch')
  check(s['boot_id']==rec['boot_id'] and bool(s['boot_id']),'boot identity')
  ex=s['executable']; check(ex['sha256']==BIN and ex['device']>=0 and ex['inode']>0,'executable snapshot')
  check(set(s['maps'])==set(pins) and len(pins)==5,'five DSO set')
  for p,h in pins.items():
   v=s['maps'][p]; check(v['sha256']==h and len(v['device_inode'])==3 and v['device_inode'][2]>0,'DSO snapshot')
  check(rec['extra_stdout']=='' and rec['cleanup_confirmed'] is True,'exit receipt')
