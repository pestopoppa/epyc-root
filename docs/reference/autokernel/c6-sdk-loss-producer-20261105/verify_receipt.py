"""Offline consistency only; no producer authentication or completeness claim."""
import hashlib,json,pathlib

def verify(root, expected_pid):
 p=pathlib.Path(root); r=json.loads((p/'receipt.json').read_text()); data=(p/'records.csv').read_bytes()
 if r.get('schema')!='c6.sdk-buffer-receipt.v1' or type(expected_pid) is not int or expected_pid<1 or r.get('pid')!=expected_pid:raise ValueError('identity')
 if hashlib.sha256(data).hexdigest()!=r.get('records_sha256'):raise ValueError('digest')
 for key in ('setup_status','start_status','stop_status','flush_status','bad_headers','nonzero_drop_callbacks','io_error'):
  if type(r.get(key)) is not int or r[key]!=0:raise ValueError(key)
 if not data.endswith(b'\n'):raise ValueError('truncated')
 callbacks=headers=records=0
 for line in data.decode('ascii').splitlines():
  f=line.split(',')
  if f[0]=='C':
   if len(f)!=4 or any(not x.isdigit() for x in f[1:]) or int(f[1])!=callbacks+1 or int(f[3])!=0:raise ValueError('callback')
   callbacks+=1;headers+=int(f[2])
  elif f[0] in ('A','K'):
   if len(f)!=(7 if f[0]=='A' else 14) or any(not x.isdigit() for x in f[1:]):raise ValueError('record')
   if f[0]=='A' and int(f[-1])!=expected_pid:raise ValueError('api pid')
   records+=1
  else:raise ValueError('type')
 if not callbacks or callbacks!=r.get('callbacks') or headers!=r.get('headers_seen') or headers!=records:raise ValueError('counts')
 return {'status':'CONSISTENT_UNAUTHENTICATED','callbacks':callbacks,'records':records,'scope':'self-reported SDK buffer only; no target-op boundary, trace authenticity or total completeness'}
