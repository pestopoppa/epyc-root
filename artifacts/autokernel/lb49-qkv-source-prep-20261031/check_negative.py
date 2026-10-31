"""Strict input custody controls; model-free generated tensors are not DS41 evidence."""
import json,pathlib,subprocess,struct
D=pathlib.Path(__file__).resolve().parent
paths=list(D.glob('fixture.src*'))+[D/'fixture.out',D/'fixture.meta']
original={p:p.read_bytes() for p in paths}
records=[]
def check(name,changes):
 try:
  for p,data in changes.items():p.write_bytes(data)
  r=subprocess.run([str(D/'replay_qkv'),str(D/'fixture'),'1'],capture_output=True,text=True)
  if r.returncode!=2 or 'REFUSED' not in r.stderr:raise RuntimeError(name+' accepted corrupt input')
  records.append({'name':name,'exit':r.returncode,'diagnostic':r.stderr.strip()})
 finally:
  for p,data in original.items():p.write_bytes(data)
p=D/'fixture.src0'
check('truncated-buffer',{p:original[p][:-1]})
check('changed-Q-after-capture',{p:original[p][:-8]+b'\0\0\0\0'+original[p][-4:]})
p=D/'fixture.src2'
check('broken-KV-alias',{p:original[p][:-4]+b'\0\0\0\0'})
p=D/'fixture.meta'
check('missing-input-presence',{p:original[p].replace(b'present3=1\n',b'')})
p=D/'fixture.out'
check('short-magic',{p:b'EPY'})
p=D/'fixture.src0'
data=bytearray(original[p]);struct.pack_into('<Q',data,52,2**64-1)
check('oversized-stride',{p:bytes(data)})
data=bytearray(original[p]);struct.pack_into('<q',data,20,2**31-1)
check('oversized-contiguous-shape',{p:bytes(data)})
p=D/'fixture.meta'
for name,old,new in [
 ('missing-phase',b'phase=after_backend_synchronize\n',b''),
 ('ask-time-phase',b'phase=after_backend_synchronize',b'phase=ask'),
 ('missing-schema',b'schema=1\n',b''),
 ('unknown-schema',b'schema=1',b'schema=2'),
 ('nonbinary-present',b'present3=1',b'present3=2'),
 ('nonbinary-iqk',b'iqk_on=0',b'iqk_on=2'),
 ('zero-source-threads',b'threads=1',b'threads=0'),
 ('oversized-source-threads',b'threads=1',b'threads=97'),
 ('negative-alias',b'alias2=1',b'alias2=-2'),
 ('self-alias',b'alias2=1',b'alias2=2'),
]: check(name,{p:original[p].replace(old,new)})
check('alias-to-absent-input',{p:original[p].replace(b'present3=1',b'present3=0').replace(b'alias4=-1',b'alias4=3')})
(D/'NEGATIVE.json').write_text(json.dumps(records,indent=2)+'\n')
print('PASS',len(records),'strict negative controls')
