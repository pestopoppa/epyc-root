import importlib.util, json, os, hashlib
from pathlib import Path
R=Path(__file__).resolve().parent
def module(name):
 s=importlib.util.spec_from_file_location(name,R/(name+".py")); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
a=module("native_task_log_original"); b=module("native_task_log_corrected")
L="slot launch_slot_: id 1 | task 9 | processing task, is_child = 0"
C="cancel task, id_task = 9"
X="slot release: id 1 | task 9 | stop processing: n_tokens = 32000, truncated = 0"
F="cancel task, id_task = 10"
cases={"ordered":([L,C,X],True,True),"release_before_cancel":([L,X,C],True,False),"cancel_before_launch":([C,L,X],True,False),"foreign_cancel":([L,F,X],False,False),"missing_release":([L,C],False,False),"duplicate_release":([L,C,X,X],False,False),"late_second_cancel":([L,C,X,C],True,False)}
results=[]
for name,(lines,old,new) in cases.items():
 observed=[]
 for m in (a,b):
  try:m.canceled_task(lines,task_id=9); observed.append(True)
  except Exception as e:
   if type(e).__name__!="TraceError":raise
   observed.append(False)
 if observed!=[old,new]:raise AssertionError((name,observed,old,new))
 results.append({"case":name,"original":observed[0],"corrected":observed[1]})
stop=os.environ.get("FILLER_STOPFILE"); end=os.environ.get("FILLER_END")
import time
if stop and Path(stop).exists():raise RuntimeError("STOP")
if end and time.time()>=float(end):raise RuntimeError("deadline")
out=Path(os.environ["CANCEL_RESULT"]); out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps({"schema":"kpf18.cancel-order.v1","status":"PASS","controls":results,"affinity":sorted(os.sched_getaffinity(0)),"sources":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in R.glob("*.py")}},indent=2)+"\n")
