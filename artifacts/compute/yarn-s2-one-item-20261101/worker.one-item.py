#!/usr/bin/env python3
"""Run one arm of one prospective shard using the existing scoring producer."""
import hashlib,json,os,sys,time,urllib.request
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/refactor-01a16fc3/heavy-yarn-quarter-ready/yarn-s0-r11-repair-20261028')
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(1,str(D))
import exposure,bounded_append
from one_item import OneItemBudget
item_budget=OneItemBudget()
selection_used=False
from resource_budget import ResourcePause
from cutoff_policy_s2 import verify_old, censored, record_cutoff
sys.path.insert(2,'/mnt/raid0/llm/worktrees/yarn-native-gate-runner-20261022')
import arm_runner_private as r
r.append_jsonl=bounded_append.append
if os.environ.get('WINDOW_CONFIRMED')!='1': raise RuntimeError('grant confirmation missing')
shard,arm,out,port,deadline,pid,argv_file=sys.argv[1:8]
mode=sys.argv[8] if len(sys.argv)>8 else 'cohort'
bounded_append.configure(Path(out)/'results')
if mode not in ('cohort','characterize','smoke'): raise RuntimeError('invalid worker mode')
p=json.loads((D.parent/'partition-proposal.json').read_text()); selected=set(p['shards'][int(shard)]['item_ids'])
old=r.Plan.__init__
def init(self,out):
 old(self,out); self.items=[i for i in self.items if i['item_id'] in selected]
 if len(self.items)!=30: raise ValueError('partition incomplete')
 if mode=='characterize': self.items=self.items[:1]
 if mode=='smoke': self.items=self.items[:1] if os.environ.get('YARN_SMOKE_CASE')=='normal' else self.items[:30]
 if mode=="smoke":
  for item in self.items:item["max_tokens"]=8
r.Plan.__init__=init
current_item={}
old_messages=r.Plan.messages
def messages(self,item):
 messages=old_messages(self,item)
 if mode=="smoke":
  messages=[dict(m,content=m["content"][:4000]) for m in messages]
  item["prompt_sha256"]=hashlib.sha256(json.dumps(messages,sort_keys=True,separators=(",",":")).encode()).hexdigest()
 current_item.clear();current_item.update(item)
 return messages
r.Plan.messages=messages
old_pending=r.pending_for_arm
def pending(plan,where,which):
 items=old_pending(plan,where,which)
 ledger=Path(out)/"exposures"
 prior=set()
 if mode!="smoke":
  scope=json.loads((Path(__file__).resolve().parent/("SCOPE-s%d-conservative.json"%int(shard))).read_bytes())
  prior={(x["arm"],x["item_id"]) for x in scope["predecessor_unknown"]}
 if mode!="smoke":
  import eligible_gate,cohort_status
  summary=cohort_status.read(Path(__file__).resolve().parent/"SCOPE-s2-conservative.json",Path(out)/"plan"/"items.jsonl",Path(out))
  allowed=eligible_gate.eligible(scope,summary,which)
  items=[i for i in items if i["item_id"] in allowed]
 eligible=[i for i in items if (which,i["item_id"]) not in prior and (not ledger.exists() or exposure.state(ledger,which,i["item_id"],i["prompt_sha256"])=="unexposed")]
 global selection_used
 if mode=="cohort" and not selection_used:
  selection_used=True
  return item_budget.first_pending(eligible)
 return eligible
r.pending_for_arm=pending
# GPU E1 rates cannot bound CPU. Allow a fresh prefill only with a conservative
# 20000 s provisional window, and kill/censor any in-flight item when grant ends.
old_est=r.Rates.estimate
def estimate(self,item,cached): return 1.0 if mode=="smoke" else max(40000.0,old_est(self,item,cached))
r.Rates.estimate=estimate
if mode=="smoke":r.SAFETY_S=0
if mode!="smoke":verify_old()
if mode=="smoke":
 import smoke_admission
 admission=smoke_admission.check(os.sched_getaffinity(0))
 grant_bytes=json.dumps(admission,sort_keys=True,separators=(",",":")).encode()
 grant=None
else:
 grant=Path('/mnt/raid0/llm/tmp/compute-flags/grants')/(os.environ['FILLER_ID']+'.grant')
if grant is not None:grant_bytes=grant.read_bytes()
class InfrastructureCutoff(Exception): pass
class LimitedResponse:
 def __init__(self,response):self.response=response
 def __enter__(self):self.response.__enter__();return self
 def __exit__(self,*args):return self.response.__exit__(*args)
 def read(self,*args):
  if args:raise ValueError("unexpected partial read")
  data=self.response.read(1024*1024+1)
  if len(data)>1024*1024:raise InfrastructureCutoff("native HTTP response exceeds bound")
  return data
def limited_open(request,timeout):
 return LimitedResponse(urllib.request.urlopen(request,timeout=timeout))
class DeadlineClient(r.Client):
 def __init__(self,url):
  super().__init__(url,opener=limited_open)
 def chat(self, messages, *, max_tokens, thinking, timeout):
  item=current_item.get("item_id"); prompt=current_item.get("prompt_sha256")
  if not item or not prompt:raise RuntimeError("missing captured item identity")
  if mode=="smoke" and time.monotonic()>=float(os.environ["YARN_SMOKE_START_DEADLINE_MONOTONIC"]):raise InfrastructureCutoff("smoke start deadline; no new exposure")
  ledger=Path(out)/"exposures"
  if not ledger.is_dir() or ledger.is_symlink():raise RuntimeError("exposure directory unavailable")
  if exposure.state(ledger,arm,item,prompt)!="unexposed":raise InfrastructureCutoff("prior exposure requires reconciliation")
  if mode=="cohort": item_budget.claim(item)
  exposure.begin(ledger,arm,item,prompt,hashlib.sha256(grant_bytes).hexdigest(),kind="r11" if mode=="smoke" else "grant")
  try:
   result=super().chat(messages, max_tokens=max_tokens, thinking=thinking, timeout=max(1.0, float(deadline)-time.time()+(5.0 if mode=="smoke" else -5.0)))
   data=(json.dumps(result,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
   if len(data)>1024*1024:raise InfrastructureCutoff("response exceeds capture bound")
   path=ledger/(exposure.key(arm,item,prompt)+".native.json")
   exposure.put(path,result)
   if hashlib.sha256(path.read_bytes()).hexdigest()!=hashlib.sha256(data).hexdigest():raise RuntimeError("capture identity mismatch")
   exposure.response(ledger,arm,item,prompt,hashlib.sha256(data).hexdigest())
   return result
  except r.ServerError as exc:
   if mode=="smoke":raise InfrastructureCutoff("direct R11 native request interrupted") from exc
   try: changed=grant.read_bytes()!=grant_bytes
   except OSError: changed=True
   stopped=changed or Path(os.environ['FILLER_STOPFILE']).exists() or bool(list(Path('/mnt/raid0/llm/tmp/compute-flags').glob('HOLD_*')))
   if censored(str(exc),exc.status,time.time(),float(deadline),stopped):
    raise InfrastructureCutoff(str(exc)) from exc
   raise
try:
 run=r.run_arm(Path(out),arm,DeadlineClient('http://127.0.0.1:'+port),deadline=float(deadline),stopfile=os.environ.get('FILLER_STOPFILE'),server={'pid':int(pid),'build_dir':'/mnt/raid0/llm/kernels/production/cpu','argv':Path(argv_file).read_text()})
except (InfrastructureCutoff,ResourcePause) as exc:
 print("in-flight or prior exposure remains unknown: "+str(exc),flush=True)
 sys.exit(75)
if mode=="cohort" and run.get("remaining", 0)>0 and run.get("stop_reason")=="plan-exhausted":
 run["stop_reason"]="one-item-boundary"
if mode=='characterize' and run['n_ok'] != 1: raise RuntimeError('characterization did not complete one item; retain as censored or error')
print(json.dumps(run)); sys.exit(7 if run['stop_reason']=='server-unreachable' else 0)
