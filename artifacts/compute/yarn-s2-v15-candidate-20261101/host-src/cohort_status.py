"""Read-only strict cohort fold; never treats unknown exposure as fresh."""
import hashlib,json
from pathlib import Path
import accounting,exposure
LIMIT=128*1024**2
def lines(path):
 if not path.exists():return []
 if path.is_symlink() or path.stat().st_size>LIMIT:raise ValueError("invalid result file")
 raw=path.read_bytes()
 if raw and not raw.endswith(b'\n'):raise ValueError("torn result tail")
 return [json.loads(x) for x in raw.splitlines()]
def read(scope_path,plan_path,out):
 scope=json.loads(Path(scope_path).read_bytes());plan=lines(Path(plan_path));out=Path(out)
 rows=[]
 for arm in ('A0','A1'):
  for r in lines(out/'results'/(arm+'.jsonl')):
   if r.get('arm')!=arm:raise ValueError("arm mismatch")
   if r.get('status')=='ok':
    item,prompt=r.get('item_id'),r.get('prompt_sha256')
    if exposure.state(out/'exposures',arm,item,prompt)!='responded':raise ValueError("result lacks native capture")
    k=exposure.key(arm,item,prompt)
    marker=json.loads((out/'exposures'/(k+'.response')).read_bytes())
    raw=(out/'exposures'/(k+'.native.json')).read_bytes()
    if len(raw)>1024*1024 or hashlib.sha256(raw).hexdigest()!=marker['response_sha256']:raise ValueError("native capture mismatch")
    native=json.loads(raw)
    if native.get('content')!=r.get('output') or native.get('finish_reason')!=r.get('finish_reason') or native.get('usage')!=r.get('usage') or native.get('timings')!=r.get('timings'):raise ValueError("result differs from captured native response")
   rows.append(r)
 return accounting.classify(scope,plan,rows,lambda arm,item,prompt:exposure.state(out/'exposures',arm,item,prompt))
