"""Freeze ten source-order A/B cases and one disjoint entry control; no inference."""
import hashlib,json,os
from pathlib import Path
import pyarrow.parquet as pq
from paired_journal import encoded
from prompt_projection import project
D=Path(__file__).resolve().parent; source=Path('/mnt/raid0/llm/tmp/codex3-evl34-deepdive-prep-20261030/qa_rl.parquet'); old=Path('/mnt/raid0/llm/tmp/codex3-evl34-deepdive-r11-budget-v6-20261030')
sha=lambda x:hashlib.sha256(x).hexdigest(); source_sha=sha(source.read_bytes()); assert source_sha=='cfde3734fb4367cc748fefb7ac6df034269a8f40f20bfa05c81e69eaea7eeadb'
t=pq.read_table(source,columns=['id','question','answer']); assert t.num_rows==2234
raw=t.slice(39,11).to_pylist();rows=[{'source_index':39+i,'id':str(r['id']),'question':r['question'],'answer':r['answer']} for i,r in enumerate(raw)]
assert len(rows)==11 and len({r['id'] for r in rows})==11
entries=[]
for r in rows:
 assert isinstance(r['question'],str) and r['question'] and isinstance(r['answer'],str) and r['answer']
 entries.append({'source_index':r['source_index'],'id':r['id'],'row_sha256':sha(encoded(r)),'question_sha256':sha(r['question'].encode())})
source_dec={'schema':'evl34-deepdive-source-freeze/v1','source_url':'https://huggingface.co/datasets/zai-org/DeepDive','source_revision':'36b28945eaf271e64003e7fcd4ddb81af0828eb5','source_sha256':source_sha,'source_split':'qa_rl training; diagnostic only; training exposure unknown','selection':'source order 39-48 paired A/B, 49 disjoint entry control; no substitutions, output-conditioned selection or replay','pilot':entries[:10],'control':entries[10]}
def output(name,obj,private=False):
 raw=json.dumps(obj,sort_keys=True,indent=None if private else 2,ensure_ascii=False).encode()+b'\n'; fd=os.open(D/name,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600 if private else 0o644)
 with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 return sha(raw)
source_dec_sha=output('SOURCE-DECLARATION.json',source_dec)
output('PILOT-PRIVATE.json',{'source_sha256':source_sha,'rows':rows[:10]},True);output('CONTROL-PRIVATE.json',rows[10],True)
dec=json.loads((old/'PREDECLARATION-FROZEN.json').read_bytes());dec['pilot']=entries[:10];dec['independent_smoke_control']=entries[10];dec['source_declaration_sha256']=source_dec_sha;dec['server_port']=19987
b=dec['budget'];b['per_case_arm_max_reserved_generated_tokens']=1572864;b['reservation']='128 root plus at most 256 child model calls, each reserves up to 4096; common aggregate 384*4096; 900 seconds may censor any case';b['root_model_requests_max']=128;b['child_model_requests_total_max']=256;b['redel_distinct_helpers_max']=16;b['per_child_model_requests_max']=16;b['child_limit_basis']='ReDel at most 16 persistent helpers, 16 lifetime model calls per helper across rounds; REPL at most 256 distinct one-call tracked lookups; common root, child call and aggregate limits, architecture differs.'
dec['calibration_exception']['scope']='DeepDive source index 49 only; exclusive GPU; no CPU region claim; affinity 184-185'
dec['control_storage']['ram_root']='/mnt/micron/codex3-evl34-r11-budget-v7-ab-20261030/control';dec['control_repair_note']='New disjoint control49; first-response entry qualification only, natural delegation not forced.'
dec['source_selection']='source-order 39-48 paired A/B, control49 disjoint';dec['selection']='source-order fixed before exposure; no substitutions or redraw';dec['exposure']='Prior declarations through 38 excluded; 39-49 no conflict in recorded exposure scan; model-training exposure unknown.'
dec['prior_exposure_caveat']='Original R11 cases 11-20 and controls 28-33 remain immutable. Dual-role reserved 29-38 excluded. No prior output reused.'
dec['prior_control_disposition']='New disjoint control49; prior control outputs never reused.';dec['status']='FROZEN BEFORE V7 EXPOSURE';dec['purpose']='Separate naturally-delegating 10-pair A/B diagnostic after R11 observed delegation.'
dec['pilot_interpretation']='Report normalized exact match, paired differences and uncertainty, missing-outcome bounds, native delegation, wall time and tokens. No Step 3 promotion threshold is invented. No delegation is inconclusive for substrate-mechanism comparison.'
dec['feasibility']='20 cells x 900 seconds plus fixed startup/teardown allowance; the limit does not promise 384 full-output requests fit in 900 seconds.'
dec['tool_policy']='Unforced ReDel root delegate/wait; max depth 1; 16 helper instances, 16 lifetime requests each; REPL up to 256 one-call child lookups; common 128 root requests and 384 total; empty wait fixed; capture native events and errors.'
dec['predecessor_predeclaration_sha256']=sha((old/'PREDECLARATION-FROZEN.json').read_bytes())
decl_sha=output('PREDECLARATION-FROZEN.json',dec)
man=[]
for r,e in zip(rows,entries):man.append({**e,'prompt_sha256':sha(project(r).encode()),'prompt_bytes':len(project(r).encode())})
manifest_sha=output('FROZEN-PROMPT-MANIFEST.json',{'declaration_sha256':decl_sha,'source_sha256':source_sha,'pilot':man[:10],'control':man[10]})
print(json.dumps({'source_sha256':source_sha,'source_declaration_sha256':source_dec_sha,'declaration_sha256':decl_sha,'manifest_sha256':manifest_sha,'pilot_indices':[39,48],'control_index':49,'row_count':len(rows)}))
