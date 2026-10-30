#!/usr/bin/env python3
"""Strict prospective projection of journal action count, not a terse-share verdict."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple,ProjectionError,grade,to_frames,register
ADAPTER_ID='vidya.adapters.kpf261_plan_steps/v1'
AUTHORITY='measurement'

def validate_plan_binding(task, row, initial, build_prompt):
 objective=row['original_action'];context=json.dumps({'objective':row['objective'],'prior_context':row['context']},ensure_ascii=False,sort_keys=True)
 if task['objective']!=objective or task['context']!=context:raise ProjectionError('task differs from fixed corpus')
 if initial['prompt']!=build_prompt(objective,context):raise ProjectionError('initial prompt differs from pinned corpus prompt')

SOURCE_VERSIONS = {
 'kpf261.real-planner.protocol.v1': ('f510391798f853bd7910a12909a0f0d02149b913', 'ffd9f3981b2a92e1c7d605eae884b9febd643ae78ebcdd93da89a13f5f224c60'),
 'kpf261.real-planner.protocol.v2': ('5778d55d01eac742566cd45277d148b3a681c4bf', 'd89ff592c2f484e659031b938d2e282fbaa88e41bda6d4d5d00aafa77a4f1ce4'),
}
PRIOR_SHA='a6bd53ec537f91aaf57d13f18784740a2564b3fc8539d84a76f75b84e5060922'

def validate_prior(root, protocol, corpus):
 raw=(root.parent/'prior-attempt.json').read_bytes()
 if hashlib.sha256(raw).hexdigest()!=PRIOR_SHA or protocol['prior_attempt_sha256']!=PRIOR_SHA:raise ProjectionError('prior attempt reference mismatch')
 ref=json.loads(raw);prior=Path(ref['capture_root'])
 if ref['schema']!='kpf261.prior-attempt-reference.v1' or ref['source_commit']!=SOURCE_VERSIONS['kpf261.real-planner.protocol.v1'][0] or ref['corpus_position']!=0:raise ProjectionError('prior identity mismatch')
 if {str(f.relative_to(prior)) for f in prior.rglob('*') if f.is_file()}!=set(ref['files']):raise ProjectionError('prior file set mismatch')
 for name,digest in ref['files'].items():
  path=(prior/name).resolve()
  if not path.is_relative_to(prior.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ProjectionError('prior file mismatch')
 old=json.loads((prior/'protocol.json').read_text());cp=json.loads((prior/'smoke-checkpoint.json').read_text());parsed=json.loads((prior/'plan-000/parsed.json').read_text());task=json.loads((prior/'plan-000/task.json').read_text());row=corpus[0]
 if old['schema']!='kpf261.real-planner.protocol.v1' or old['source_commit']!=SOURCE_VERSIONS[old['schema']][0] or old['source_manifest_sha256']!=SOURCE_VERSIONS[old['schema']][1] or old['synthetic'] is not False:raise ProjectionError('prior source identity mismatch')
 if cp['plans_attempted']!=1 or cp['journal_actions']!=0 or cp['journal_sha256']!=hashlib.sha256(b'').hexdigest() or (prior/'journal'/'plan_steps_parsed.jsonl').exists():raise ProjectionError('prior attempt is not zero-action')
 if parsed['steps']!=[] or parsed['journal_eligible'] is not False or json.loads((prior/'plan-000/call-000-response.json').read_text())['result']!='':raise ProjectionError('prior output is not empty')
 ident=f"win{row['source_window']}-{row['step']}"
 if parsed['task_id']!=ident or task['task_id']!=ident or task['corpus_position']!=0 or task['corpus_row_sha256']!=hashlib.sha256(json.dumps(row,sort_keys=True,ensure_ascii=False).encode()).hexdigest():raise ProjectionError('prior corpus position mismatch')

def replay_native_plan(root, manifest, primary, calls):
 """Replay the pinned native parser/repair with recorded responses, never inference."""
 import os,subprocess
 # Loading the native parser is safe only after checking its entire source closure.
 paths={str(f.relative_to(root)) for d in ('src','orchestration','scripts') for f in (root/d).rglob('*') if f.is_file() and '__pycache__' not in f.parts and f.suffix!='.pyc'}
 pins={entry['path']:entry['sha256'] for entry in manifest['files']}
 if paths!=set(pins):raise ProjectionError('native replay source file set mismatch')
 for name,digest in pins.items():
  path=root/name
  if (path.suffix=='.py' and not path.resolve().is_relative_to(root.resolve())) or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ProjectionError('native replay source mismatch')
 script="""import asyncio,json,sys
from src.api.routes.chat_pipeline import proactive_stage as stage
from src.structured_output import parse_events
raw,calls=json.load(sys.stdin)
stage.resolve_planner_role=lambda:'architect_critic'
stage._should_inline_plan_call_for_test=lambda _:True
parse_events.begin_parse=lambda:None
parse_events.record_parse_event=lambda *a,**k:None
parse_events.note_repair_turn_from_last_call=lambda **k:None
class Recorder:
 def __init__(self):self.at=0;self.mismatch=False
 def llm_call(self,prompt,*args,**kwargs):
  if self.at>=len(calls):self.mismatch=True;raise ValueError('unrecorded call')
  request,response=calls[self.at];self.at+=1
  if request!={'prompt':prompt,'args':list(args),'kwargs':kwargs}:self.mismatch=True;raise ValueError('native repair request mismatch')
  return response
p=Recorder();steps=asyncio.run(stage._decompose_plan_steps(raw,primitives=p,task_id='replay'))
if p.mismatch or p.at!=len(calls):raise SystemExit('repair call mismatch')
print(json.dumps(steps))
"""
 env={'PATH':'/usr/bin:/bin','PYTHONPATH':str(root)+':/mnt/raid0/llm/epyc-orchestrator/.venv/lib/python3.11/site-packages','PYTHONDONTWRITEBYTECODE':'1','ORCHESTRATOR_PARSE_EVENTS_LOG':'off','HOME':'/nonexistent','OMP_NUM_THREADS':'1'}
 command=['/home/daniele/.local/share/uv/python/cpython-3.11-linux-x86_64-gnu/bin/python3','-B','-c',script]
 try:run=subprocess.run(command,input=json.dumps([primary,calls]),text=True,capture_output=True,cwd=root,env=env,timeout=30)
 except (OSError,subprocess.TimeoutExpired) as exc:raise ProjectionError('native repair replay unavailable') from exc
 if run.returncode:raise ProjectionError('native repair replay refused: '+run.stderr[-300:])
 return json.loads(run.stdout)

def validate_v2_primary(plan, initial, steps, native_parse, schema, root=None, manifest=None):
 import base64,urllib.parse
 if initial['args']!=[] or initial['kwargs']!={'role':'architect_critic','n_tokens':256,'json_schema':schema,'skip_suffix':True}:raise ProjectionError('native primary request mismatch')
 requests=sorted(plan.glob('call-*-request.json'));responses=sorted(plan.glob('call-*-response.json'))
 if len(requests)!=len(responses) or [f.name for f in requests]!=[f'call-{i:03d}-request.json' for i in range(len(requests))] or [f.name for f in responses]!=[f'call-{i:03d}-response.json' for i in range(len(requests))] or len(requests)>2:raise ProjectionError('primitive call sequence mismatch')
 calls=[(json.loads(req.read_text()),json.loads(resp.read_text())['result']) for req,resp in zip(requests,responses)]
 if not calls or any(not isinstance(value,str) for _,value in calls):raise ProjectionError('invalid primitive result')
 primary=calls[0][1];parsed=native_parse(primary)
 # A directly parsed plan must conform to the primary grammar. A malformed
 # primary may legitimately go through the pinned native repair path.
 if parsed:
  value=json.loads(primary);props=schema['items']['properties']
  if not isinstance(value,list):raise ProjectionError('primary output schema mismatch')
  for step in value:
   if not isinstance(step,dict) or not {'id','action'}<=set(step) or not set(step)<=set(props):raise ProjectionError('primary output schema mismatch')
   for key,x in step.items():
    if key in ('id','action','actor','parallel_group','persona','persona_hint') and not isinstance(x,str):raise ProjectionError('primary output schema mismatch')
    if key in ('depends_on','outputs') and (not isinstance(x,list) or any(not isinstance(y,str) for y in x)):raise ProjectionError('primary output schema mismatch')
   if 'actor' in step and step['actor'] not in ('worker','coder','architect'):raise ProjectionError('primary output actor mismatch')
  if len(calls)!=1 or parsed!=steps:raise ProjectionError('primary parsed output mismatch')
 elif primary.strip() or len(calls)>1:
  if root is None or manifest is None:raise ProjectionError('native repair replay source missing')
  if replay_native_plan(root,manifest,primary,calls[1:])!=steps:raise ProjectionError('native repair result mismatch')
 elif steps or len(calls)!=1:raise ProjectionError('empty primary cannot produce steps')
 wire=[]
 for f in sorted(plan.glob('wire-*-request.json')):
  obj=json.loads(f.read_text());raw=base64.b64decode(obj['body_base64'],validate=True)
  if hashlib.sha256(raw).hexdigest()!=obj['body_sha256']:raise ProjectionError('wire request hash mismatch')
  endpoint=urllib.parse.urlparse(obj['url']).path
  if endpoint!='/completion':
   if endpoint not in ('/props','/slots') or obj.get('method')!='GET':raise ProjectionError('unmatched RPC')
   continue
  payload=json.loads(raw);response=json.loads(f.with_name(f.name.replace('-request.json','-response.json')).read_text());body=base64.b64decode(response['body_base64'],validate=True)
  if hashlib.sha256(body).hexdigest()!=response['body_sha256'] or response.get('status')!=200:raise ProjectionError('wire response mismatch')
  text=body.decode('utf-8');chunks=[]
  for line in text.splitlines():
   if line.startswith('data: '):
    try:chunks.append(json.loads(line[6:]).get('content') or '')
    except (ValueError,AttributeError):pass
  if not chunks:
   try:chunks=[json.loads(text).get('content') or '']
   except (ValueError,AttributeError):pass
  wire.append((payload,''.join(chunks)))
 if len(wire)!=len(calls):raise ProjectionError('unmatched completion RPC')
 for i,((request,value),(payload,wire_value)) in enumerate(zip(calls,wire)):
  kwargs=request['kwargs']
  if kwargs.get('skip_suffix') is not True or payload.get('prompt')!=request['prompt'] or payload.get('json_schema')!=kwargs.get('json_schema') or wire_value!=value:raise ProjectionError('wire primary request mismatch' if i==0 else 'wire repair request mismatch')
  if i==0 and payload.get('n_predict')!=256:raise ProjectionError('wire primary budget mismatch')

def validate_v2_checkpoints(out, complete, records, corpus, raw, synthetic):
 count=complete['plans_attempted'];end=complete['next_corpus_position']
 if type(complete['count_target_met']) is not bool or type(complete['corpus_exhausted']) is not bool:raise ProjectionError('invalid continuation completion flags')
 if type(count) is not int or type(end) is not int or count<1 or end!=count+1 or end>len(corpus) or complete['corpus_exhausted'] is not (end==len(corpus)):raise ProjectionError('continuation counter mismatch')
 entries=raw.splitlines(keepends=True);id_to_pos={f"win{row['source_window']}-{row['step']}":i for i,row in enumerate(corpus)}
 checkpoints=sorted(out.glob('partial-checkpoint-*.json'));smoke=out/'smoke-checkpoint.json'
 if smoke.exists():checkpoints.insert(0,smoke)
 elif not synthetic and count>1:raise ProjectionError('smoke checkpoint missing')
 positions=[]
 for cp in checkpoints:
  item=json.loads(cp.read_text());pos=item['next_corpus_position']
  if type(pos) is not int or pos<2 or pos>end or item['plans_attempted']!=pos-1:raise ProjectionError('checkpoint position mismatch')
  if cp!=smoke and cp.name!=f'partial-checkpoint-{pos:03d}.json':raise ProjectionError('checkpoint filename mismatch')
  prefix=b''.join(line for line,record in zip(entries,records) if id_to_pos[record['task_id']]<pos)
  actions=sum(len(r['data']['steps']) for r in records if id_to_pos[r['task_id']]<pos)
  if hashlib.sha256(prefix).hexdigest()!=item['journal_sha256'] or actions!=item['journal_actions']:raise ProjectionError('checkpoint journal mismatch')
  if not synthetic:
   server=json.loads((out/f'server-preflight.resume-{pos:03d}.json').read_text());argv=server['argv']
   if argv.count('-m')!=1 or argv[argv.index('-m')+1]!='/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf':raise ProjectionError('resume preflight model mismatch')
  positions.append(pos)
 if positions!=sorted(positions):raise ProjectionError('checkpoint ordering mismatch')

def validate_native(out, protocol, complete, records):
 import re,runpy,base64,ast
 corpus_bytes=(out/'corpus.jsonl').read_bytes()
 if protocol['corpus_sha256']!='acd3089c3fb559a94bcd1c18b29dadd89e23afbe16cf5c48c9edaf1bf113fbf0':raise ProjectionError('unrecognized locked corpus')
 if hashlib.sha256(corpus_bytes).hexdigest()!=protocol['corpus_sha256']:raise ProjectionError('corpus hash mismatch')
 corpus=[json.loads(line) for line in corpus_bytes.splitlines()]
 plans=sorted(out.glob('plan-*'));v2=protocol['schema']=='kpf261.real-planner.protocol.v2';start=1 if v2 else 0
 if len(plans)!=complete['plans_attempted'] or [p.name for p in plans]!=[f'plan-{i:03d}' for i in range(start,start+len(plans))]:raise ProjectionError('plan sequence mismatch')
 root=Path(protocol['source_snapshot']);manifest=json.loads((root.parent/'source-manifest.json').read_text())
 manifest_raw=(root.parent/'source-manifest.json').read_bytes()
 expected_commit,expected_manifest=SOURCE_VERSIONS[protocol['schema']]
 if protocol['source_manifest_sha256']!=expected_manifest or (v2 and (protocol['source_commit']!=expected_commit or manifest['commit']!=expected_commit)):raise ProjectionError('unrecognized source identity')
 if hashlib.sha256(manifest_raw).hexdigest()!=protocol['source_manifest_sha256']:raise ProjectionError('source manifest mismatch')
 rel='src/repl_environment/redaction.py'; pin=next(x['sha256'] for x in manifest['files'] if x['path']==rel)
 if hashlib.sha256((root/rel).read_bytes()).hexdigest()!=pin:raise ProjectionError('redactor source mismatch')
 redact=runpy.run_path(str(root/rel))['redact_credentials']
 parser_rel='src/api/routes/chat_pipeline/proactive_stage.py'; parser_path=root/parser_rel
 parser_pin=next(x['sha256'] for x in manifest['files'] if x['path']==parser_rel)
 if hashlib.sha256(parser_path.read_bytes()).hexdigest()!=parser_pin:raise ProjectionError('parser source mismatch')
 tree=ast.parse(parser_path.read_text());schema=None
 if v2:
  if protocol['corpus_start']!=1:raise ProjectionError('continuation offset mismatch')
  sampler_sha='2321f3f7b9bd488ad6f2bec750f9fe83cda026a0cd1a5c8274d88557a4f01db2'
  if protocol['sampler_sha256']!=sampler_sha or hashlib.sha256((root.parent/'sampler.py').read_bytes()).hexdigest()!=sampler_sha:raise ProjectionError('continuation sampler mismatch')
  validate_prior(root,protocol,corpus)
  selected=[n for n in tree.body if isinstance(n,(ast.Assign,ast.AnnAssign)) and any(isinstance(t,ast.Name) and t.id in {'_PLAN_STEP_ACTORS','_PLAN_STEPS_SCHEMA'} for t in (n.targets if isinstance(n,ast.Assign) else [n.target]))]
  schema_env={};exec(compile(ast.Module(body=selected,type_ignores=[]),'pinned-plan-schema','exec'),schema_env);schema=schema_env['_PLAN_STEPS_SCHEMA']
 fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_parse_plan_steps')
 env={'_re':re,'_json':json};exec(compile(ast.Module(body=[fn],type_ignores=[]),str(parser_path),'exec'),env);native_parse=env['_parse_plan_steps']
 # Execute only the pinned builder and control-token functions; resolve the pinned default
 # template explicitly, without importing a mutable source tree or inheriting prompt overrides.
 from types import SimpleNamespace
 def pinned(rel):
  path=root/rel
  pin=next(x['sha256'] for x in manifest['files'] if x['path']==rel)
  data=path.read_bytes()
  if hashlib.sha256(data).hexdigest()!=pin:raise ProjectionError('prompt source mismatch')
  return data.decode()
 control=ast.parse(pinned('src/security/control_tokens.py'))
 names={'ZWSP','DEFAULT_CONTROL_TOKEN_REGEX','_ENV','_ENV_OFF','_compiled'}
 selected=[node for node in control.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in node.targets) or isinstance(node,ast.AnnAssign) and isinstance(node.target,ast.Name) and node.target.id in names or isinstance(node,ast.FunctionDef) and node.name in {'_pattern','neutralise_control_tokens'}]
 env_control={'re':re,'os':SimpleNamespace(environ={})}
 exec(compile(ast.Module(body=selected,type_ignores=[]),'pinned-control','exec'),env_control)
 template=pinned('orchestration/prompts/task_decomposition.md')
 builder=ast.parse(pinned('src/prompt_builders/builder.py'))
 fn=next(node for node in builder.body if isinstance(node,ast.FunctionDef) and node.name=='build_task_decomposition_prompt')
 env_builder={'_ct_neutralise':env_control['neutralise_control_tokens'],'_TASK_DECOMPOSITION_FALLBACK':'','resolve_prompt':lambda name,fallback,**kwargs:template.format(**kwargs)}
 exec(compile(ast.Module(body=[fn],type_ignores=[]),'pinned-builder','exec'),env_builder)
 build_prompt=env_builder['build_task_decomposition_prompt']
 byid={r['task_id']:r for r in records};matched=[]
 for i,plan in enumerate(plans,start):
  task=json.loads((plan/'task.json').read_text());row=corpus[i];ident=f"win{row['source_window']}-{row['step']}"
  if task['task_id']!=ident or task['corpus_position']!=i or task['corpus_row_sha256']!=hashlib.sha256(json.dumps(row,sort_keys=True,ensure_ascii=False).encode()).hexdigest():raise ProjectionError('fixed corpus order mismatch')
  initial=json.loads((plan/'call-000-request.json').read_text())
  validate_plan_binding(task,row,initial,build_prompt)
  parsed=json.loads((plan/'parsed.json').read_text());steps=parsed['steps'];journal=byid.get(ident)
  if parsed['task_id']!=ident:raise ProjectionError('parsed identity mismatch')
  if v2:validate_v2_primary(plan,initial,steps,native_parse,schema,root,manifest)
  if not journal:
   if steps:raise ProjectionError('eligible plan missing journal')
   continue
  if not steps or len(steps)!=len(journal['data']['steps']):raise ProjectionError('parsed/journal count mismatch')
  results=[]; wire=[]
  for f in sorted(plan.glob('call-*-response.json')):
   value=json.loads(f.read_text()).get('result');request=f.with_name(f.name.replace('-response.json','-request.json'))
   if isinstance(value,str):
    if not request.is_file():raise ProjectionError('primitive request missing')
    results.append((json.loads(request.read_text())['prompt'],value))
  for f in sorted(plan.glob('wire-*-response.json')):
   obj=json.loads(f.read_text())
   if 'body_base64' not in obj:continue
   body=base64.b64decode(obj['body_base64'],validate=True)
   if hashlib.sha256(body).hexdigest()!=obj['body_sha256']:raise ProjectionError('wire response hash mismatch')
   text=body.decode('utf-8',errors='replace');parts=[]
   for line in text.splitlines():
    if line.startswith('data: '):
     try:
      chunk=json.loads(line[6:]);parts.append(chunk.get('content') or ((chunk.get('choices') or [{}])[0].get('delta') or {}).get('content') or '')
     except (ValueError,TypeError,IndexError):pass
   request=f.with_name(f.name.replace('-response.json','-request.json'))
   if not request.is_file():raise ProjectionError('wire request missing')
   request_body=json.loads(request.read_text()); req=base64.b64decode(request_body['body_base64'],validate=True)
   if hashlib.sha256(req).hexdigest()!=request_body['body_sha256']:raise ProjectionError('wire request hash mismatch')
   request_text=req.decode('utf-8',errors='replace')
   try: request_text=json.dumps(json.loads(request_text),ensure_ascii=False,indent=2)
   except ValueError:pass
   if parts:wire.append((request_text,''.join(parts)))
   else:
    try:
     chunk=json.loads(text);wire.append((request_text,chunk.get('content') or ((chunk.get('choices') or [{}])[0].get('message') or {}).get('content') or ''))
    except (ValueError,TypeError,IndexError,AttributeError):pass
  if not results or any(not any(json.dumps(prompt,ensure_ascii=False)[1:-1] in request and result in response for request,response in wire) for prompt,result in results):raise ProjectionError('primitive request/response lacks wire attestation')
  candidates=[native_parse(result) for _,result in results]
  if not any(c==steps for c in candidates):raise ProjectionError('parsed steps, actor or persona do not rederive from pinned parser')
  for step,j in zip(steps,journal['data']['steps']):
   action=step.get('action');text=action if isinstance(action,str) else str(action)
   possible={text,redact(text).text}
   if not any(j['action']==x[:2000] and j['action_len']==len(x) for x in possible):raise ProjectionError('journal action mismatch')
   if j['step_id']!=str(step['id']) or j['actor']!=step.get('actor') or j['persona']!=(step.get('persona') or step.get('persona_hint')):raise ProjectionError('journal step fields mismatch')
  matched.append(ident)
 if matched!=[r['task_id'] for r in records]:raise ProjectionError('journal order differs from plans')

def _project(out, allow_synthetic=False):
 out=Path(out).resolve(); protocol=json.loads((out/'protocol.json').read_text()); complete=json.loads((out/'capture-complete.json').read_text())
 if protocol['schema'] not in SOURCE_VERSIONS or type(protocol['synthetic']) is not bool or type(complete['synthetic']) is not bool or protocol['synthetic']!=complete['synthetic']: raise ProjectionError('invalid producer protocol')
 if protocol['synthetic'] and not allow_synthetic: raise ProjectionError('synthetic fixture is not real traffic')
 path=out/'journal'/'plan_steps_parsed.jsonl'; raw=path.read_bytes(); digest=hashlib.sha256(raw).hexdigest()
 if digest!=complete['journal_sha256']: raise ProjectionError('journal attestation mismatch')
 records=[json.loads(line) for line in raw.splitlines()];n=0
 if not records:raise ProjectionError('empty journal')
 for record in records:
  data=record['data']; steps=data['steps']
  if record['schema']!='epyc.plan_steps_parsed.v1' or data['plan_id']!=record['task_id'] or data['n_steps']!=len(steps) or data['step_ids']!=[s['step_id'] for s in steps]: raise ProjectionError('journal schema inconsistency')
  n+=len(steps)
 if len({r['task_id'] for r in records})!=len(records): raise ProjectionError('duplicate task identity')
 validate_native(out,protocol,complete,records)
 if protocol['schema']=='kpf261.real-planner.protocol.v2':
  corpus=[json.loads(line) for line in (out/'corpus.jsonl').read_bytes().splitlines()]
  validate_v2_checkpoints(out,complete,records,corpus,raw,protocol['synthetic'])
 if n!=complete['journal_actions'] or complete['count_target_met']!=(n>=50): raise ProjectionError('action count inconsistent')
 tag='synthetic fixture' if protocol['synthetic'] else 'prospective planner journal'
 scope={}
 if protocol['synthetic'] and allow_synthetic and protocol.get('fixture_model_file'):
  scope={'model_file':protocol['fixture_model_file']}
 if not protocol['synthetic']:
  server=json.loads((out/'server-preflight.json').read_text()); argv=server['argv']
  if argv.count('-m')!=1 or argv[argv.index('-m')+1]!='/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf':raise ProjectionError('native model scope missing')
  scope={'model_file':argv[argv.index('-m')+1]}
 t=ClaimTuple(measurement_id='kpf261-actions-'+digest[:24],metric='planner_actions_journalled',value=n,date=records[-1]['timestamp'],category='BASELINE',claim=f'{tag}: {n} parsed actions journalled; no terse-share classification',metric_direction='higher_better',protocol_id='',reps=n,reps_basis='scored actions',unit='actions',attestation_path=str(path),attestation_sha256=digest,attestation_locator='kpf261-planner:'+digest,attestation_present=True,attestation_verified=True,source_kind='kpf261-plan-steps',applicability=scope,extra={'synthetic':protocol['synthetic'],'corpus_sha256':protocol['corpus_sha256']})
 return t
@register('kpf261-plan-steps')
def project(out, allow_synthetic=False):
 try:
  return _project(out, allow_synthetic=allow_synthetic)
 except ProjectionError:
  raise
 except (OSError, ValueError, TypeError, KeyError, IndexError, StopIteration, AttributeError, SyntaxError) as exc:
  raise ProjectionError(f'invalid planner capture: {type(exc).__name__}: {exc}') from exc

def native_rows(path):
 project(path)  # Reject synthetic or invalid native records before dispatch.
 return (Path(path),)
