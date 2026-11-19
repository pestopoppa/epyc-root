"""Build a prospective capture bundle for one arm; never fabricate missing records."""
import hashlib,json,os
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bundle(run_dir, dev_manifest, engine, scope, alpha, output):
 run_dir=Path(run_dir); manifest=Path(dev_manifest)
 terminal=run_dir/'TERMINAL.json'; end=json.loads(terminal.read_text())
 if end.get('state') not in ('complete_raw','incomplete_raw') or end.get('mode')!='full' or end.get('counts',{}).get('unknown')!=0:raise ValueError('terminal is incomplete or unknown')
 rows=json.loads(manifest.read_text())['records']; ids={r['file_id'] for r in rows}
 if len(rows)!=len(ids):raise ValueError('duplicate manifest clip')
 got={}
 for path in run_dir.glob('*.belief-attempt.json'):
  a=json.loads(path.read_text())
  if (a.get('engine'),a.get('scope'),a.get('configured_alpha'))!=(engine,scope,alpha):continue
  if a.get('split')!='dev' or a.get('dev_manifest_sha256')!=sha(manifest):raise ValueError('dataset/split mismatch')
  ident=a.get('clip_id'); disposition=path.with_name(path.name.replace('.belief-attempt.json','.belief-disposition.json'))
  if ident not in ids or ident in got or not disposition.is_file():raise ValueError('missing, duplicate, or extra attempt')
  got[ident]={'attempt_path':str(path),'attempt_sha256':sha(path),'disposition_path':str(disposition),'disposition_sha256':sha(disposition)}
 if set(got)!=ids:raise ValueError('missing expected attempts')
 result={'schema':'epyc.cs8.lex2.native_bundle.v1','terminal_path':str(terminal),'terminal_sha256':sha(terminal),'items':[got[i] for i in sorted(ids)]}
 raw=(json.dumps(result,sort_keys=True)+'\n').encode();fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
 with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 return sha(output)
