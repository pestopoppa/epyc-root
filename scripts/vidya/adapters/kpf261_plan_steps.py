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

def validate_native(out, protocol, complete, records):
 import re,runpy,base64,ast
 corpus_bytes=(out/'corpus.jsonl').read_bytes()
 if protocol['corpus_sha256']!='acd3089c3fb559a94bcd1c18b29dadd89e23afbe16cf5c48c9edaf1bf113fbf0':raise ProjectionError('unrecognized locked corpus')
 if hashlib.sha256(corpus_bytes).hexdigest()!=protocol['corpus_sha256']:raise ProjectionError('corpus hash mismatch')
 corpus=[json.loads(line) for line in corpus_bytes.splitlines()]
 plans=sorted(out.glob('plan-*'))
 if len(plans)!=complete['plans_attempted'] or [p.name for p in plans]!=[f'plan-{i:03d}' for i in range(len(plans))]:raise ProjectionError('plan sequence mismatch')
 root=Path(protocol['source_snapshot']);manifest=json.loads((root.parent/'source-manifest.json').read_text())
 manifest_raw=(root.parent/'source-manifest.json').read_bytes()
 if protocol['source_manifest_sha256']!='ffd9f3981b2a92e1c7d605eae884b9febd643ae78ebcdd93da89a13f5f224c60':raise ProjectionError('unrecognized source manifest')
 if hashlib.sha256(manifest_raw).hexdigest()!=protocol['source_manifest_sha256']:raise ProjectionError('source manifest mismatch')
 rel='src/repl_environment/redaction.py'; pin=next(x['sha256'] for x in manifest['files'] if x['path']==rel)
 if hashlib.sha256((root/rel).read_bytes()).hexdigest()!=pin:raise ProjectionError('redactor source mismatch')
 redact=runpy.run_path(str(root/rel))['redact_credentials']
 parser_rel='src/api/routes/chat_pipeline/proactive_stage.py'; parser_path=root/parser_rel
 parser_pin=next(x['sha256'] for x in manifest['files'] if x['path']==parser_rel)
 if hashlib.sha256(parser_path.read_bytes()).hexdigest()!=parser_pin:raise ProjectionError('parser source mismatch')
 tree=ast.parse(parser_path.read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_parse_plan_steps')
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
 for i,plan in enumerate(plans):
  task=json.loads((plan/'task.json').read_text());row=corpus[i];ident=f"win{row['source_window']}-{row['step']}"
  if task['task_id']!=ident or task['corpus_position']!=i or task['corpus_row_sha256']!=hashlib.sha256(json.dumps(row,sort_keys=True,ensure_ascii=False).encode()).hexdigest():raise ProjectionError('fixed corpus order mismatch')
  initial=json.loads((plan/'call-000-request.json').read_text())
  validate_plan_binding(task,row,initial,build_prompt)
  parsed=json.loads((plan/'parsed.json').read_text());steps=parsed['steps'];journal=byid.get(ident)
  if parsed['task_id']!=ident:raise ProjectionError('parsed identity mismatch')
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
 if protocol['schema']!='kpf261.real-planner.protocol.v1' or type(protocol['synthetic']) is not bool or type(complete['synthetic']) is not bool or protocol['synthetic']!=complete['synthetic']: raise ProjectionError('invalid producer protocol')
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
