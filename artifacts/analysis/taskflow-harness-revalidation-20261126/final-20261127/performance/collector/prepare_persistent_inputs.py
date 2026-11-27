"""Prepare current persistent-phase descriptors; no collector/model calls or polling."""
from pathlib import Path
import argparse,hashlib,json
HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
COV=BASE/'coverage'
SERVING=COV/'persistent-serving/runs/final-01'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def write(p,d):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(d,indent=2)+'\n')
def bind(p,kind,expected=None):return {'kind':kind,'path':str(p),'sha256':expected or sha(p)}
p=argparse.ArgumentParser();p.add_argument('--require-terminal',action='store_true');a=p.parse_args()
config=load(HERE/'INPUTS-FINAL-WORKING.json');pending=[];raw_callbacks=[];new_specs=[]
roots=[]
for family in ['persistent-callback','persistent-callback-admission-v2','persistent-w66-light-12','persistent-mm-mechanical','persistent-tu-off-auto-ci','persistent-w66-light-identity']:
    roots += [(family,root,root/'PLAN.json') for root in sorted((COV/family/'runs').glob('*')) if root.is_dir() and (root/'PLAN.json').is_file()]
future=COV/'persistent-callback-admission-v2/runs/paw-clean-paid-01'
if not any(root==future for _,root,_ in roots):roots.append(('persistent-callback-admission-v2',future,COV/'persistent-callback-admission-v2/PAW-PLAN.json'))
for family,root,plan_path in roots:
    plan=load(plan_path);units=root/'units'
    if 'jobs' in plan:rows=[dict(job['row'],id=job['id']) for job in plan['jobs']]
    elif 'row' in plan:
        # AutoCI is incremental; only realized exact unit IDs have request evidence.
        rows=[dict(plan['row'],id=unit.name) for unit in sorted(units.glob('*')) if unit.is_dir()]
    else:raise ValueError('unrecognized actual persistent plan: '+str(plan_path))
    projection=HERE/'persistent-plan-projections'/(family+'-'+root.name+'.json');write(projection,rows)
    bindings=[bind(plan_path,'actual_persistent_plan'),bind(projection,'exact_job_id_and_row_projection')]
    for name in ['APPROVAL.json','RESULTS.json','READY.json']:
        path=root/name
        if path.exists():bindings.append(bind(path,'raw_callback_owner_receipt'))
    for name in ['callback.py','RUNNER-SEAL.json','control.py']:
        path=COV/family/name
        if path.exists():bindings.append(bind(path,'persistent_callback_source_or_seal'))
    for name in ['READY.json','GRANT.json','SERVING.json','CONFIG-gpu.json','CONFIG-cpu.json','PRE-CLOSE.json','CLEANUP.json']:
        path=SERVING/name
        if path.exists():bindings.append(bind(path,'actual_final01_serving_identity'))
    summary_path=root/'RESULTS.json';summary=load(summary_path) if summary_path.exists() else None
    raw_callbacks.append({'root':str(root),'actual_root_exists':root.is_dir(),'plan_path':str(plan_path),'raw_results_summary':summary,'source_sha256':sha(summary_path) if summary_path.exists() else None})
    for row in rows:
        unit=units/row['id'];owner=unit/'RESULT.json';worker=unit/'worker/receipt.json';record=load(owner) if owner.exists() else {};receipt=load(worker) if worker.exists() else {}
        # Raw callback launch errors with no native unit are not model failures.
        launch_failed=bool(summary and not unit.exists() and any(r.get('status')=='callback_error' and r.get('backend')==row.get('backend') and r.get('slot')==row.get('slot') for r in summary.get('terminal',[])))
        terminal=record.get('terminal_at') or record.get('ended_at') or receipt.get('ended_at')
        if not terminal and not launch_failed:pending.append({'unit':str(unit),'state':'no terminal native receipt yet'})
        for pattern in ['*RECEIPT*.json','*ASSESSMENT*.json','*GRADE*.json']:
            for path in sorted(unit.glob(pattern)):bindings.append(bind(path,'qualified_check_or_source_record_not_auto_acceptance'))
        path=unit/'independent/oracle-result.json'
        if path.exists():bindings.append(bind(path,'qualified_structural_grade_not_auto_acceptance'))
    backends=sorted({row['backend'] for row in rows}) or ['gpu']
    spec={'id':family+'/'+root.name,'layout':'quality','serving_root':str(SERVING),'units_root':str(units),'plan':str(projection),'backends':backends,'bindings':bindings,'profile_tags':['persistent_final01_server','own_unit_root_shared_serving_and_resources','raw_score_separate_qualified_grade','no_device_benchmark']}
    if family=='persistent-callback-admission-v2':spec['profile_tags'].append('repaired_admission_v2_original_plan_preserved')
    if family=='persistent-w66-light-12':spec['profile_tags'].append('accurate_light_v2_zero_prior_help')
    if family=='persistent-mm-mechanical':spec['profile_tags'].append('supplemental_mechanical_feedback_original_cap2_preserved')
    if family=='persistent-tu-off-auto-ci':spec['profile_tags'].append('supplemental_deterministic_autoci_not_extra_paid_semantic_guidance')
    new_specs.append(spec)
# Old retired epochs remain separate so all ancestry and known late wires survive.
ids={e['id'] for e in new_specs};config['epochs']=[e for e in config['epochs'] if e['id'] not in ids]+new_specs
all_units=[Path(e['units_root'])/row['id'] for e in config['epochs'] for row in (load(e['plan']) if e['layout']=='quality' else [])]
extra=[]
for path in sorted((BASE/'quality-assessments/registry').glob('*.json')):
    record=load(path);extra.append(bind(path,'current_owner_source_acceptance_registry'))
    source=Path(record['source_review']) if record.get('source_review') else None;source_hash=record.get('source_review_sha256')
    if source and source_hash:
        extra.append(bind(source,'source_acceptance_nested_provenance',source_hash))
        if not source.is_file() or sha(source)!=source_hash:continue
    for unit in all_units:
        if unit.name!=path.stem:continue
        raw=load(unit/'RESULT.json') if (unit/'RESULT.json').exists() else {};worker=load(unit/'worker/receipt.json') if (unit/'worker/receipt.json').exists() else {};patch=raw.get('patch_sha256') or raw.get('candidate_patch_sha256') or worker.get('patch_sha256')
        if patch and patch==record.get('candidate_patch_sha256'):config.setdefault('reviews',{})[str(unit)]={'path':str(path),'sha256':sha(path)}
for folder in sorted(BASE.glob('*-oracle-v*')):
    if not folder.is_dir():continue
    for name in ['acceptance-migration.json','CONTROL.json','SOURCE.json','REASSESSMENT.json']:
        path=folder/name
        if path.exists():extra.append(bind(path,'versioned_grading_context_not_semantic_acceptance'))
for folder in sorted(BASE.glob('source-review*')):
    for path in [folder/'REVIEW.json',*sorted(folder.glob('grades/*/RESULT.json'))]:
        if path.is_file():extra.append(bind(path,'existing_source_or_qualified_grade_receipt'))
light= COV/'w66-light-brief-v2/main-comparison/runs'
if str(light) not in config['main_roots']:config['main_roots'].append(str(light))
for path in [light/'DS41-W-66/direct-1/measurement.json',COV/'w66-light-acceptance/COST-COMPARISON.json']:
    if path.exists():extra.append(bind(path,'eighth_main_execution_light_condition_or_separate_review_cost'))
for tree in ['w66-light-acceptance','legacy-assisted-review','paw-clean-review','paw-clean-review-v3']:
    for path in sorted((COV/tree).glob('reviews/*/*/*/runs/*/guidance-1/assistance-accounting.json')):extra.append(bind(path,'incremental_paid_main_review_cost_separate'))
new_specs[-1]['bindings'].extend(extra)
config['main_execution_scope']={'original_unique_task_ids':6,'original_first_pass_calls':6,'prior_TU_repair_extra_call':1,'fresh_W66_light_implementation_extra_call':1,'main_implementation_execution_calls':8,'light_is_new_condition_not_seventh_unique_task':True,'paid_acceptance_reviews_are_separate_calls':True,'manager_setup_review_costs_not_zero_or_included':True}
config['persistent_metrics_contract']={'serving_root':str(SERVING),'request_metrics':['upstream/delivered/client streaming TTFT with nonstream unknown','request/queue/client wall distributions','prefill/decode native timings and observational envelopes','prompt/cache/generated counts with unknowns preserved','paired MTP accepted/proposed receipts','resource windows including post-terminal drains'],'aggregate':'same unchanged metric algebra over all known deduplicated wire receipts; per-attempt/per-request records retained','no_structural_auto_accept':True,'retired_and_repaired_admission_histories_separate':True,'snapshot_policy':'descriptor only; no recurring collector snapshots. Run final validation once all expected callbacks/AutoCI are terminal, then main applies final snapshot.'}
config['closed_serving_receipts']=[bind(SERVING/name,'owner_verified_native_serving_close') for name in ['PRE-CLOSE.json','CLEANUP.json'] if (SERVING/name).exists()]
config['pending_terminal_sources']=pending
config['prepared_source']={'builder_sha256':sha(Path(__file__)),'base_input_sha256':sha(HERE/'INPUTS-FINAL-WORKING.json'),'model_calls':0,'collector_invoked':False}
write(HERE/'RAW-PERSISTENT-CALLBACK-STATES.json',raw_callbacks)
write(HERE/'INPUTS-PERSISTENT-WORKING.json',config)
write(HERE/'PERSISTENT-DESCRIPTOR-STATE.json',{'epochs':len(config['epochs']),'new_persistent_epochs':len(new_specs),'pending_native_terminal_receipts':pending,'final_validation_performed':bool(a.require_terminal and not pending),'collector_snapshots_performed':0,'raw_callback_states_path':str(HERE/'RAW-PERSISTENT-CALLBACK-STATES.json')})
if a.require_terminal and pending:raise SystemExit('Final validation refused: actual terminal native receipts remain pending; no fabricated zeros/acceptances.')
print(json.dumps({'descriptor':str(HERE/'INPUTS-PERSISTENT-WORKING.json'),'new_persistent_epochs':len(new_specs),'pending_terminal_sources':len(pending),'final_validation':bool(a.require_terminal and not pending),'snapshots':0}))
