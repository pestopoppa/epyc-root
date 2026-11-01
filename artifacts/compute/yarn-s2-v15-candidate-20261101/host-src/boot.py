#!/usr/bin/python3
"""Source-bound common smoke and task-specific scheduled entry."""
import hashlib,json,os,sys
from pathlib import Path
D=Path(__file__).resolve().parent
manifest=D/"SOURCE-MANIFEST-v15.json"
expected=os.environ.get("YARN_BUNDLE_SHA","")
try:
 raw=manifest.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError("anchor")
 data=json.loads(raw)
 for name in ("boot.py","pincheck.py"):
  if hashlib.sha256((D/name).read_bytes()).hexdigest()!=data["files"][name]:raise ValueError("verifier pin")
 sys.path.insert(0,str(D));import pincheck
 pincheck.verify(D,manifest,expected,lambda:True)
except Exception as exc:
 print("source verification refused:",type(exc).__name__,file=sys.stderr);raise SystemExit(78)
if len(sys.argv)==3 and sys.argv[1]=="--smoke" and sys.argv[2] in ("normal","cutoff"):
 import job_side
 raise SystemExit(job_side.smoke(sys.argv[2],expected))
if len(sys.argv)!=1:
 print("usage: launch.sh [--smoke normal|cutoff]",file=sys.stderr)
 raise SystemExit(64)
import job_side
from resource_budget import ResourcePause,check as budget_check
try:
 cohort=Path('/mnt/micron/refactor-yarn-s2-v32-20261031/cohort')
 if not cohort.is_dir() or cohort.is_symlink():raise ValueError('live cohort unavailable')
 budget_check(cohort)
 result=job_side.job_auto(19422,expected)
except ResourcePause as exc:
 result={'state':'partial','partial':True,'reason':str(exc),'new_exposures':0}
except Exception as exc:
 print("scheduled task refused:",type(exc).__name__+": "+str(exc),file=sys.stderr)
 raise SystemExit(78)
result["partial"] = result.get("state") == "partial"
raw=json.dumps(result,sort_keys=True,separators=(',',':'))
if len(raw.encode())>256*1024:
 result={'state':'partial','partial':True,'reason':'actual job stdout metadata bound; native records retained','result_path':str(D/'cohort/results')};raw=json.dumps(result)
print(raw)
state=result.get("state")
raise SystemExit(0 if state=="complete" else 75 if state=="partial" else 78)
