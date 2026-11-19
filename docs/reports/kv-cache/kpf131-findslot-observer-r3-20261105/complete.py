import json,os,sys
from pathlib import Path
D=Path(__file__).resolve().parent
try:
 smoke=os.getenv("FILLER_SMOKE")=="1" or os.getenv("FILLER_DRYRUN")=="1"
 result=Path(os.environ["FILLER_DRYRUN_RESULT_PATH"]) if smoke else D/"out/RESULT.json"
 r=json.loads(result.read_text())
 assert r["status"]=="PASS" and r["smoke"] is smoke and r["case_count"]==2 and len(r["records"])==2
 for x in r["records"]: assert x["native"]["hits"]==2 and x["native"]["exit_code"]==0 and x["native"]["before"]==x["native"]["after"] and x["cleanup_confirmed"] and x["gdb_rc"]==0
except Exception as e:
 print(e,file=sys.stderr);sys.exit(1)
