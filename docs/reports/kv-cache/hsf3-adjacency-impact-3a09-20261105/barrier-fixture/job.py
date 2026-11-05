#!/usr/bin/env python3
import importlib.util,json,os,tempfile,signal,time,uuid
from datetime import datetime,timezone
from pathlib import Path
D=Path(__file__).resolve().parent
ROW_ID="hsf3-native-barrier-qualification-20261105"
started=time.time()
def deadline_epoch(value):
 try: return float(value)
 except ValueError: return datetime.fromisoformat(value.replace("Z","+00:00")).timestamp()
deadlines=[started+120]
for key in ("FILLER_DEADLINE","FILLER_END"):
 if os.environ.get(key): deadlines.append(deadline_epoch(os.environ[key]))
end=min(deadlines)
def check():
 stop=Path(os.environ.get("FILLER_STOPFILE",str(D/"STOP")))
 if stop.exists() or (D/"STOP").exists(): raise RuntimeError("STOP requested")
 if time.time()>=end: raise RuntimeError("deadline reached")
def alarm(signum,frame): raise RuntimeError("bounded qualification deadline")
signal.signal(signal.SIGALRM,alarm)
signal.setitimer(signal.ITIMER_REAL,max(0.001,end-time.time()))
check()
invocation=os.environ["HSF3_INVOCATION_ID"]
spec=importlib.util.spec_from_file_location("sealed_gap_producer",D/"producer.py"); p=importlib.util.module_from_spec(spec); spec.loader.exec_module(p)
W=[{"id":"A","start":"2026-10-03T00:00:00Z","end":"2026-10-04T00:00:00Z"},{"id":"B","start":"2026-10-04T00:00:00Z","end":"2026-10-05T00:00:00Z"}]
def call(i):
 t=f"2026-10-03T01:00:{i*5:02d}Z"
 return {"schema":p.METHOD["serving_call_schema"],"record_id":str(i),"ts_start":t,"ts_end":f"2026-10-03T01:00:{i*5+1:02d}Z","outcome":"ok","dispatched":True,"role":"frontdoor","caller":{"session_id":"synthetic-session","client_class":"chat_repl"},"queue":{"enqueue_ts_epoch":str(p.epoch(t))}}
cases=[]
for name in ["ordered_control","shuffled_control","missing_middle_completion","invalid_middle_completion"]:
 check()
 rows=[call(i) for i in range(3)]
 if name=="shuffled_control": rows=[rows[2],rows[0],rows[1]]
 if name=="missing_middle_completion": rows[1].pop("ts_end")
 if name=="invalid_middle_completion": rows[1]["ts_end"]="invalid"
 with tempfile.TemporaryDirectory(dir=D) as tmp:
  tmp=Path(tmp); source=tmp/"synthetic.jsonl"; source.write_text("".join(json.dumps(r)+"\n" for r in rows))
  try:
   check()
   report=p.extract([source],W,tmp/"capture")
   check()
   pairs=[json.loads(x) for x in (tmp/"capture/session-gap-pairs.jsonl").read_text().splitlines()]
   bridges=sum(x["first_record"]=="0" and x["next_record"]=="2" for x in pairs)
   passed=(len(pairs)==2 and bridges==0) if name.endswith("control") else bridges==0
   cases.append({"case":name,"passed":passed,"n_pairs":len(pairs),"forbidden_bridges":bridges,"malformed_records":report["counts"].get("malformed_records",0)})
  except (ValueError,KeyError,TypeError,ArithmeticError):
   cases.append({"case":name,"passed":not name.endswith("control"),"refused":True})
check()
result={"row_id":ROW_ID,"invocation_id":invocation,"started_epoch":started,"completed_epoch":time.time(),"synthetic_only":True,"schema":"hsf3_native_barrier_qualification.v1","scope":"Synthetic parser qualification only; no live sources, gap evidence, class coverage, ClaimTuple or HSF-3 closure.","cases":cases,"status":"PASS" if all(c["passed"] for c in cases) else "UNSAFE"}
out=Path(os.environ["FILLER_DRYRUN_RESULT_PATH"]) if os.environ.get("FILLER_SMOKE")=="1" else D/"out/RESULT.json"
if os.environ.get("FILLER_SMOKE")=="1" and (D/"out").resolve() in out.resolve().parents: raise ValueError("separate smoke path required")
out.parent.mkdir(parents=True,exist_ok=True)
check()
with out.open("x") as f: json.dump(result,f,indent=2); f.write("\n")
