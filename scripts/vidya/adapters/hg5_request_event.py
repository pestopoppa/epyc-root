"""Strict HG5 completed-post-answer event facts; existing measurement ladder only.

A seal is byte integrity, never evidence of loaded runtime identity or correctness.
Nullable native counters decline that metric; legacy receipts are never backfilled.
No protocol/direction/category label is invented as a recorded producer fact.
"""
from __future__ import annotations
import hashlib,json,math,os,re,stat
from datetime import datetime,timezone
from pathlib import Path
from claim_tuple import ClaimTuple,ProjectionError,register
SCHEMA_SHA256="d1a0b46d1df1e7de6a0af43a3c328b7ca635e6422fce0bbfda679544c3115868"
PRODUCER_SHA256="994d581338b080bf28e9f587164f397720bd51f9befdfe3bdba6759164a409df"
PRODUCER_V2_SHA256="a69a6c3cc0386582a98a97918dea77d8a4640e857098e42c69bba3d1455ec489"
SCHEMA_V2_SHA256="4e00cc2565cf50bf187f50714c8bd4281abfaaf56b63f23bce9cf7f4ddded600"
PROJECTION_NAME="hg5-request-event"
ADAPTER_ID="vidya.adapters.hg5_request_event/v1"
AUTHORITY="measurement"
METRICS={"calls":"calls","prompt_tokens":"tokens","completion_tokens":"tokens","prompt_ms":"ms","generation_ms":"ms"}
def canonical(value):
 return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def reject(message):raise ProjectionError("HG5 request event: "+message)
def pairs(items):
 out={}
 for k,v in items:
  if k in out:reject("duplicate JSON key "+k)
  out[k]=v
 return out
def read_file(path,*,native=False):
 path=Path(path);directory_fd=None
 if native:
  directory_fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
  directory=os.fstat(directory_fd);named=os.lstat(path.parent)
  if (directory.st_dev,directory.st_ino)!=(named.st_dev,named.st_ino) or directory.st_uid!=os.geteuid() or stat.S_IMODE(directory.st_mode)!=0o700:
   os.close(directory_fd);reject("native parent must be owned stable mode0700")
 try:fd=os.open(path.name if native else path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK,dir_fd=directory_fd)
 except BaseException:
  if directory_fd is not None:os.close(directory_fd)
  raise
 try:
  first=os.fstat(fd);link=os.lstat(path)
  if not stat.S_ISREG(first.st_mode) or (first.st_dev,first.st_ino)!=(link.st_dev,link.st_ino) or first.st_nlink!=1:reject("unstable/nonregular/multiply-linked file")
  if native and (first.st_uid!=os.geteuid() or stat.S_IMODE(first.st_mode)!=0o600):reject("native file must be owned mode0600")
  if first.st_size>1048576:reject("native size exceeds bounded envelope")
  raw=b""
  while len(raw)<=1048576:
   chunk=os.read(fd,65536)
   if not chunk:break
   raw+=chunk
  last=os.fstat(fd);link_after=os.lstat(path)
  if len(raw)>1048576 or (first.st_dev,first.st_ino,first.st_size,first.st_mtime_ns,first.st_ctime_ns,first.st_mode,first.st_uid,first.st_nlink)!=(last.st_dev,last.st_ino,last.st_size,last.st_mtime_ns,last.st_ctime_ns,last.st_mode,last.st_uid,last.st_nlink) or (first.st_dev,first.st_ino)!=(link_after.st_dev,link_after.st_ino):reject("file changed during capture")
  if native:
   final_directory=os.fstat(directory_fd);final_named=os.lstat(path.parent)
   if (directory.st_dev,directory.st_ino)!=(final_directory.st_dev,final_directory.st_ino) or (directory.st_dev,directory.st_ino)!=(final_named.st_dev,final_named.st_ino) or (directory.st_mode,directory.st_uid,directory.st_ctime_ns)!=(final_directory.st_mode,final_directory.st_uid,final_directory.st_ctime_ns) or (directory.st_mode,directory.st_uid,directory.st_ctime_ns)!=(final_named.st_mode,final_named.st_uid,final_named.st_ctime_ns):reject("native parent changed during read")
  return raw
 finally:
  os.close(fd)
  if directory_fd is not None:os.close(directory_fd)
def schema_validate(value,rule,defs,path="envelope"):
 if "$ref" in rule:return schema_validate(value,defs[rule["$ref"].split("/")[-1]],defs,path)
 types=rule.get("type");types=[types] if isinstance(types,str) else types
 if types:
  valid={"null":value is None,"boolean":type(value) is bool,"integer":type(value) is int,"number":(type(value) is int or type(value) is float and math.isfinite(value)),"string":type(value) is str,"object":type(value) is dict,"array":type(value) is list}
  if not any(valid[t] for t in types):reject(path+" type differs")
 if "const" in rule and value!=rule["const"]:reject(path+" constant differs")
 if "enum" in rule and not any(type(value) is type(x) and value==x for x in rule["enum"]):reject(path+" enum differs")
 if isinstance(value,dict):
  props=rule.get("properties",{})
  if not set(rule.get("required",()))<=set(value) or (rule.get("additionalProperties") is False and not set(value)<=set(props)):reject(path+" exact keys differ")
  for k,v in value.items():schema_validate(v,props[k],defs,path+"."+k)
 if isinstance(value,list):
  if len(value)>rule.get("maxItems",len(value)):reject(path+" cardinality differs")
  for i,v in enumerate(value):schema_validate(v,rule["items"],defs,path+"."+str(i))
 if isinstance(value,str):
  if len(value)<rule.get("minLength",0) or len(value)>rule.get("maxLength",len(value)):reject(path+" text length differs")
  if "pattern" in rule and re.fullmatch(rule["pattern"],value) is None:reject(path+" identity differs")
 if type(value) in (int,float) and value<rule.get("minimum",value):reject(path+" negative number")
def validate(doc):
 version=doc.get("body",{}).get("schema") if isinstance(doc,dict) and isinstance(doc.get("body"),dict) else None
 if version not in ("hg5.request_intervention.v1","hg5.request_intervention.v2"):reject("unsupported native version")
 filename="hg5-request-intervention-v2.json" if version.endswith("v2") else "hg5-request-intervention-v1.json"
 raw=read_file(Path(__file__).parent/"schemas"/filename)
 if hashlib.sha256(raw).hexdigest()!=(SCHEMA_V2_SHA256 if version.endswith("v2") else SCHEMA_SHA256):reject("pinned producer schema changed")
 schema=json.loads(raw);schema_validate(doc,schema,schema["$defs"])
 body=doc["body"]
 if hashlib.sha256(canonical(body)).hexdigest()!=doc["body_sha256"]:reject("native body seal differs")
 window=body["window"]
 for clock in ("utc","monotonic"):
  if window["end_"+clock+"_ns"]<window["start_"+clock+"_ns"]:reject("inverted contemporaneous window")
 source=body["source"];ids=[source[k] for k in ("commit","tree","producer_sha256")]
 if source["origin"]=="unknown" and any(v is not None for v in ids):reject("unknown source invented identity")
 if source["origin"]=="source_authored_run_context" and (any(v is None for v in ids) or source["producer_sha256"] not in ((PRODUCER_V2_SHA256,) if version.endswith("v2") else (PRODUCER_SHA256,PRODUCER_V2_SHA256))):reject("source context producer differs from accepted writer")
 if body["eligible"]!=(body["plan_enabled"] and body["stage"]=="direct"):reject("eligibility differs from producer expression")
 failure=body["failure"]
 if failure["message"] is not None:reject("writer retains no raw failure message")
 if failure["exception_type"] is not None and not failure["exception_type"].isidentifier():reject("failure class is not bounded identifier")
 if failure["status"]=="none" and failure["exception_type"] is not None:reject("absent failure has exception class")
 if body["steps"]:
  step=body["steps"][0]
  if not body["eligible"] or step["initial_role"]!=body["initial_role"] or step["target_role"]!=body["requested_target_role"]:reject("step request/role eligibility differs")
  if step["trigger"]=="caller_forced" and body["requested_mode"]!="force_architect_general":reject("forced trigger lacks native forced request")
  for key in METRICS:
   before,after,delta=step["before"][key],step["after"][key],step["delta"][key]
   wanted=after-before if before is not None and after is not None and after>=before else None
   if delta!=wanted or (delta is not None and type(delta) is not type(wanted)):reject("native delta/reset consistency differs: "+key)
  calls=step["delta"]["calls"];status="unknown" if calls is None else "not_called" if calls==0 else "called"
  if step["call_status"]!=status:reject("call status differs from actual nullable counter delta")
  expected_role=step["target_role"] if step["outcome"]=="adopted" else step["initial_role"]
  if body["final_role"]!=expected_role:reject("final role differs from observed adoption")
  if step["outcome"]=="failed" and failure["status"]=="none":reject("failed outcome lacks bounded failure status")
  if step["outcome"]=="adopted" and failure["status"]!="none":reject("adopted outcome carries failed status")
 elif body["final_role"]!=body["initial_role"]:reject("no-step record changed final role")
 if version.endswith("v2"):
  declaration=body["projection"]["declaration"]
  if source["origin"]!="source_authored_run_context":reject("v2 declaration lacks captured source context")
  if hashlib.sha256(canonical(declaration)).hexdigest()!=body["projection"]["declaration_sha256"]:reject("pre-capture declaration seal differs")
 return body

def native_rows(receipt):
 """Read exact owned immutable writer bytes; one row per known step cost metric."""
 try:raw=read_file(receipt,native=True)
 except (OSError,ValueError) as exc:reject("native custody unreadable: "+type(exc).__name__)
 try:doc=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:reject("nonfinite JSON constant"))
 except (ValueError,UnicodeDecodeError) as exc:reject("malformed JSON: "+type(exc).__name__)
 body=validate(doc)
 if Path(receipt).name!=body["event_id"]+".json":reject("file identity differs from event")
 if raw!=canonical(doc)+b"\n":reject("writer canonical envelope bytes differ")
 if not body["steps"]:return ()
 return tuple({"envelope":doc,"metric_key":key,"artifact_path":str(receipt),"artifact_sha256":hashlib.sha256(raw).hexdigest()} for key in METRICS if body["steps"][0]["delta"][key] is not None)

@register(PROJECTION_NAME)
def project(native):
 """Refuse unlabelled974 facts: the carrier defaults cannot supply native warrant."""
 if type(native) is not dict or set(native)!={"envelope","metric_key","artifact_path","artifact_sha256"}:reject("native projection row keys differ")
 rows=native_rows(native["artifact_path"])
 if native not in rows:reject("projection input differs from exact original native row")
 body=native["envelope"]["body"]
 if body["schema"]=="hg5.request_intervention.v1":reject("ungraded native facts: producer category, metric_direction and protocol_id declarations absent; prospective write-side declaration required before projection")
 labels=body["projection"]["declaration"];key=native["metric_key"];step=body["steps"][0]
 try:date=datetime.fromtimestamp(body["window"]["end_utc_ns"]/1e9,tz=timezone.utc).date().isoformat()
 except (OverflowError,OSError,ValueError):reject("native UTC outside date range")
 return ClaimTuple(measurement_id="hg5-request-event:"+body["event_id"]+":"+key,metric="hg5_intervention_"+key,value=step["delta"][key],date=date,category=labels["category"],metric_direction=labels["metric_direction"][key],protocol_id=labels["protocol_id"],claim="Completed post-answer intervention recorded "+key+"="+str(step["delta"][key])+" "+METRICS[key]+". Category/direction/protocol copied from explicit pre-capture source declaration; protocol citation does not assert human ratification. Loaded runtime origin unknown; no correctness, efficacy or all-request denominator.",reps=1,reps_basis="one captured native intervention step, never all-request coverage",unit=METRICS[key],attestation_path="",attestation_locator="hg5-request-event:"+native["artifact_path"],attestation_sha256=native["artifact_sha256"],attestation_present=True,attestation_verified=True,source_kind="hg5-request-event",extra={"native_body":body,"declaration_sha256":body["projection"]["declaration_sha256"],"runtime_origin":"unknown","protocol_human_ratification":"not_asserted","category_direction_protocol_origin":"source_authored_pre_capture_context","nullable_metrics_declined":[k for k in METRICS if step["delta"][k] is None]})
