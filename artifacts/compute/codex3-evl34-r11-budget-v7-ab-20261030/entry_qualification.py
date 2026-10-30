"""Entry-only proof; never grades the semantic control or pilot outcome."""
import hashlib,json
from pathlib import Path
ROOT=Path('/mnt/micron/codex3-evl34-r11-budget-v7-ab-20261030/control')
D=Path(__file__).resolve().parent
RECEIPT=D/'LAUNCH-QUALIFICATION.json'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_bytes())
def facts(root,attempt,decl,source):
 root=Path(root).resolve(strict=True);attempt=Path(attempt).resolve(strict=True)
 if attempt.parent!=root or not attempt.name.startswith('campaign-control-'):raise ValueError('invalid attempt location')
 result=read(attempt/'result.json');sup=read(root/'campaign-supervisor.json');capture=read(attempt/'capture.json')
 if sup.get('rc')!=0 or sup.get('reason') is not None or sup.get('drained') is not True or sup.get('elapsed',999)>300:raise ValueError('supervisor not clean')
 if result.get('source_sha256')!=source or capture.get('source_sha256')!=source or capture.get('declaration_sha256')!=decl or result.get('server_drained') is not True:raise ValueError('source or server mismatch')
 control_id=str(read(D/'PREDECLARATION-FROZEN.json')['independent_smoke_control']['id'])
 statuses=result.get('statuses') or {}
 if statuses.get(control_id+'/production_repl') not in ('complete','unknown') or statuses.get(control_id+'/redel_delegate_wait')!='unknown' or len(statuses)!=2 or result.get('partial') is not True or result.get('failure') is not None:raise ValueError('control state mismatch')
 if not (result.get('qualification') or {}).get('qualified'):raise ValueError('entry milestone absent')
 wire=result.get('wire_capture') or {}
 if wire.get('requests',0)<1 or wire.get('first_tools')!=['delegate','wait'] or wire.get('tool_choice') not in (None,'auto'):raise ValueError('wire qualification')
 first_request=attempt/'0-redel_delegate_wait/redel_delegate_wait/outbound-requests/0000.json'
 if sha(first_request)!=wire.get('first_wire_sha256'):raise ValueError('captured request mismatch')
 journal=root/'control-journal';natives=list(journal.glob('*.native'))
 repl=[p for p in natives if read(p).get('arm')=='production_repl']
 redel=[p for p in natives if read(p).get('arm')=='redel_delegate_wait']
 if len(repl)!=1 or len(redel)!=1:raise ValueError('journal evidence missing')
 rr=read(repl[0]);rn=read(redel[0]);native=rr.get('native') or {};partial=rn.get('native') or {}
 start=repl[0].with_suffix('.start');initial=read(start);identity=initial.get('identity') or {}
 if rr.get('campaign_sha256')!=decl or rr.get('id')!=control_id or identity.get('campaign_sha256')!=decl or identity.get('id')!=control_id or identity.get('arm')!='production_repl':raise ValueError('REPL journal mismatch')
 if statuses[control_id+'/production_repl']=='unknown':
  if native.get('status')!='partial_entry_repl' or repl[0].with_suffix('.end').exists():raise ValueError('REPL partial mismatch')
 else:
  end=read(repl[0].with_suffix('.end'))
  if end.get('identity')!=identity or end.get('start_sha256')!=sha(start) or end.get('status')!='complete':raise ValueError('REPL complete mismatch')
 if not native.get('request_evidence') or not (native.get('server_usage') or {}).get('completion_tokens',0)>0:raise ValueError('REPL usage absent')
 redel_start=redel[0].with_suffix('.start');redel_identity=read(redel_start).get('identity') or {}
 if rn.get('campaign_sha256')!=decl or rn.get('id')!=control_id or redel_identity.get('campaign_sha256')!=decl or redel_identity.get('id')!=control_id or redel_identity.get('arm')!='redel_delegate_wait' or redel[0].with_suffix('.end').exists() or partial.get('status')!='partial_entry_redel' or not partial.get('request_evidence') or not (partial.get('server_usage') or {}).get('completion_tokens',0)>0:raise ValueError('ReDel usage absent')
 quiesce=attempt/'0-redel_delegate_wait/redel_delegate_wait/entry-quiesce.json';q=read(quiesce)
 if q.get('schema')!='evl34-entry-quiescence/v1' or q.get('all_inflight_drained') is not True or q.get('acknowledged') is not True:raise ValueError('quiescence absent')
 witness=attempt/'gpu-witness.jsonl';server_path=attempt/'SERVER.json';server=read(server_path)
 if not any(x.get('hip_mapped') and x.get('pid')==server.get('pid') and x.get('birth')==server.get('birth_ticks') and any(y.get('pid')==server.get('pid') and y.get('start_ticks')==server.get('birth_ticks') for y in x.get('bound',[])) for x in (json.loads(line) for line in witness.read_text().splitlines())):raise ValueError('GPU residency absent')
 paths=[attempt/'result.json',attempt/'capture.json',server_path,root/'campaign-supervisor.json',first_request,repl[0],start,redel[0],redel_start,witness,quiesce]
 if statuses[control_id+'/production_repl']=='complete':paths.append(repl[0].with_suffix('.end'))
 return {str(p):sha(p) for p in paths}
def verify(decl,source):
 receipt=read(RECEIPT)
 if receipt.get('schema')!='evl34-entry-qualification/v1' or receipt.get('scope')!='entry-only' or receipt.get('declaration_sha256')!=decl or receipt.get('source_sha256')!=source:raise ValueError('receipt identity')
 files=facts(ROOT,receipt['attempt'],decl,source)
 if files!=receipt.get('files'):raise ValueError('receipt evidence changed')
 return receipt
def build(attempt,decl,source):
 return {'schema':'evl34-entry-qualification/v1','scope':'entry-only','declaration_sha256':decl,'source_sha256':source,'attempt':str(attempt),'files':facts(ROOT,attempt,decl,source)}
