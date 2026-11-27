"""Deterministic paid execution/native-phase ledger. Read-only; no models or polling."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,re,sys,math
HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
COV=BASE/'coverage'
KEYS=['input_tokens','cached_input_tokens','uncached_input_tokens','output_tokens','reasoning_output_tokens']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def stable_sum(values):
    values=list(values);known=[x for x in values if isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and x>=0]
    return {'known_sum':sum(known) if known else None,'known_count':len(known),'unknown_count':len(values)-len(known)}
def vector(rows):
    rows=list(rows)
    return {'observed_execution_count':len(rows),'usage':{k:stable_sum(r['usage'].get(k) for r in rows) for k in KEYS},'sum_cli_execution_walls_s':stable_sum(r['execution'].get('wall_s') for r in rows),'scope':'observed executions only; unknown is never zero; summed CLI walls are not parallel elapsed or isolated model compute'}
def framework():
    lock=load(HERE/'SOURCE-LOCK.json')
    for p,digest in lock.items():assert sha(p)==digest,('metric/import source changed',p)
    original=BASE/'main-comparison'
    spec=importlib.util.spec_from_file_location('prepare',original/'prepare.py');prepare=importlib.util.module_from_spec(spec);sys.modules['prepare']=prepare;exec(compile((original/'prepare.py').read_bytes(),str(original/'prepare.py'),'exec'),prepare.__dict__)
    spec=importlib.util.spec_from_file_location('paid_measure',original/'measure.py');measure=importlib.util.module_from_spec(spec);exec(compile((original/'measure.py').read_bytes(),str(original/'measure.py'),'exec'),measure.__dict__)
    return measure

def discover():
    roots=[BASE/'main-comparison',COV/'legacy-comparison',COV/'legacy-direct-repair']+[p for p in COV.iterdir() if p.is_dir()]
    paths=set()
    for root in roots:
        for pattern in ['runs/*/*/plan.json','reviews/*/*/*/runs/*/*/plan.json','main-comparison/runs/*/*/plan.json']:
            paths.update(root.glob(pattern))
    return sorted(paths)

def condition(path,case):
    if case=='DS41-W-66' and '/w66-light-brief/' in str(path):return 'withdrawn-light-v1-stale-cause'
    return 'accurate-light-v2' if case=='DS41-W-66' and ('w66-light-' in str(path) or 'common-light' in str(path)) else 'detailed'

def native_records(config):
    records={}
    for epoch in config['epochs']:
        units=Path(epoch['units_root']);plan=load(epoch['plan']);rows=plan if isinstance(plan,list) else []
        planned={r['id']:r for r in rows};actual={p.name for p in units.glob('*') if p.is_dir()}
        for name in sorted(actual|set(planned)):
            unit=units/name;raw_path=unit/'RESULT.json';worker_path=unit/'worker/receipt.json';raw=load(raw_path) if raw_path.exists() else {};worker=load(worker_path) if worker_path.exists() else {};job=load(unit/'JOB.json') if (unit/'JOB.json').exists() else {};row=planned.get(name,{})
            if not raw and not worker and not job:continue
            profile=raw.get('profile') or row.get('profile');sp=worker.get('session_profile') or {}
            backend=raw.get('backend') or job.get('backend') or row.get('backend') or sp.get('backend');thinking=raw.get('thinking',job.get('thinking',row.get('thinking',sp.get('thinking'))));case=raw.get('case') or worker.get('case') or row.get('case')
            if profile is None:
                # No guessing thinking from IDs; retain an unknown profile explicitly.
                profile='profile-not-recorded'
            mode=(backend or 'unknown')+'-'+('ON' if thinking is True else 'OFF' if thinking is False else 'UNKNOWN')+'-'+profile
            resume=raw.get('resume') or worker.get('resume') or job.get('resume') or row.get('resume') or {};prior=resume.get('prior') or resume.get('prior_run') or resume.get('prior_attempt');prior=Path(prior) if isinstance(prior,str) and prior.startswith('/') else None
            if prior and prior.name=='worker':prior=prior.parent
            wires=[];known=0;unknown=0;seen=set();sources={};pending_archives=[]
            for path in [unit/'wire/requests.jsonl',unit/'worker/wire/requests.jsonl']:
                if not path.exists():continue
                sources[str(path)]=sha(path);known_archives=set()
                for line in path.read_text().splitlines():
                    try:r=json.loads(line)
                    except json.JSONDecodeError:unknown+=1;continue
                    known_archives.add(r.get('body_ref'))
                    fingerprint=hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':')).encode()).hexdigest()
                    if fingerprint in seen:continue
                    seen.add(fingerprint)
                    if r.get('upstream_attempted') is False:continue
                    amount=r.get('predicted_n');known+=amount if isinstance(amount,(int,float)) and not isinstance(amount,bool) else 0;unknown+=not isinstance(amount,(int,float)) or isinstance(amount,bool)
                    wires.append({'receipt_sha256':fingerprint,'t0':r.get('t0'),'wall_s':r.get('wall_s'),'predicted_n':amount})
                for archive in sorted(path.parent.glob('*.json.gz')):
                    if archive.name not in known_archives:pending_archives.append({'path':str(archive),'sha256':sha(archive),'generated_tokens':None})
            for path in [raw_path,worker_path,unit/'JOB.json']:
                if path.exists():sources[str(path)]=sha(path)
            records[str(unit)]={'source_unit':str(unit),'id':name,'case':case,'condition':condition(unit,case),'mode':mode,'raw_status':raw.get('status'),'worker_status':worker.get('status'),'patch_sha256':raw.get('patch_sha256') or raw.get('candidate_patch_sha256') or worker.get('patch_sha256'),'started_at':raw.get('started_at') or worker.get('started_at'),'terminal_at':raw.get('terminal_at') or worker.get('ended_at'),'raw_oracle':raw.get('oracle'),'generation_known_from_wire':known if wires else None,'generation_unknown_receipts':unknown,'wire_receipts':wires,'unreceipted_archives':pending_archives,'raw_generation_counters':{k:raw[k] for k in ['generation_observed','generation_charged','generation_unknown_requests','reserved_at_terminal'] if k in raw},'worker_generation_counters':{k:worker[k] for k in ['generated_observed','charged_toward_ceiling','generation_unknown','reserved_at_terminal'] if k in worker},'source_hashes':sources,'session_hashes':{str(path):sha(path) for path in [unit/'OPEN-CODE-SESSION.json',unit/'worker/session.json'] if path.exists()},'prior_session_sha256':resume.get('prior_session_sha256') or resume.get('session_sha256'),'prior_unit':str(prior) if prior else None,'prior_result_sha256':resume.get('prior_result_sha256'),'prior_worker_sha256':resume.get('receipt_sha256') or resume.get('prior_receipt_sha256'),'guidance_path':resume.get('feedback') or job.get('prompt'),'scope':'raw statuses/oracles and all known wire costs retained; no semantic verdict inferred'}
    return records

def main():
    p=argparse.ArgumentParser();p.add_argument('--native-input',type=Path,default=BASE/'performance/multi-epoch-v3/INPUTS-PERSISTENT-WORKING.json');p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert a.out.is_relative_to(HERE) and not a.out.exists();measure=framework();config=load(a.native_input);native=native_records(config);calls={};planned=[]
    feedback_files={sha(path):path for path in (BASE/'main-comparison/feedback').glob('*.json')}
    for path in discover():
        run=path.parent;plan=load(path);events=run/'events.jsonl';execution=run/'execution.json';case=plan.get('case');cond=condition(run,case)
        if not events.exists() and not execution.exists():planned.append({'plan':str(path),'case':case,'condition':cond,'state':'unlaunched; not counted as paid cost'});continue
        info=measure.read_events(events) if events.exists() else {'fresh_thread_count':0,'completed_turn_count':0,'thread_id':None,'usage':measure.normalized_usage(None),'errors':0,'malformed_records':0}
        identity='thread:'+info['thread_id'] if info.get('thread_id') else 'unidentified-execution:'+str(run)
        record={'call_id':identity,'occurrences':[str(run)],'case':case,'condition':cond,'arm':plan.get('arm'),'role':plan.get('review_kind') or plan.get('arm'),'mode':plan.get('mode'),'model':plan.get('model'),'effort':plan.get('reasoning_effort'),'execution':load(execution) if execution.exists() else {'rc':None,'wall_s':None},'usage':info['usage'],'state':'terminal execution observed' if execution.exists() else 'active or partial execution','fresh_thread_count':info.get('fresh_thread_count'),'completed_turn_count':info.get('completed_turn_count'),'errors':info.get('errors'),'malformed_records':info.get('malformed_records'),'source_hashes':{str(f):sha(f) for f in [path,events,execution,run/'measurement.json',run/'assistance-accounting.json',run/'launch-start.json'] if f.exists()},'reviewed_native_units':[],'qualification':'retained unconditional observed cost; no quality outcome inferred'}
        if record['arm'] in ['direct','direct-repair']:record['role']='main-only-implementation'
        if 'w66-light-acceptance-v2/' in str(run):record['qualification']='owner-designated qualified fresh rerun; historical first-review costs retained separately'
        elif 'w66-light-acceptance/' in str(run):record['qualification']='historical first light review; owner-designated failed review qualification; unconditional cost retained'
        root=path.parents[3];seal_path=root/'SEAL.json';seal=load(seal_path) if seal_path.exists() else {}
        for source,digest in seal.get('source_native_files',{}).items():
            if source.endswith('/RESULT.json') and str(Path(source).parent) in native and native[str(Path(source).parent)]['source_hashes'].get(source)==digest and native[str(Path(source).parent)]['patch_sha256']==plan.get('candidate_input_patch_sha256'):record['reviewed_native_units'].append(str(Path(source).parent))
        if not record['reviewed_native_units']:
            for source,digest in seal.get('source_native_files',{}).items():
                for key,n in native.items():
                    if source==str(Path(key)/'worker/receipt.json') and n['source_hashes'].get(source)==digest and n['patch_sha256']==plan.get('candidate_input_patch_sha256'):record['reviewed_native_units'].append(key)
        if not record['reviewed_native_units'] and plan.get('source_native_result_sha256'):
            for key,n in native.items():
                if n['source_hashes'].get(str(Path(key)/'RESULT.json'))==plan['source_native_result_sha256'] and n['patch_sha256']==plan.get('candidate_input_patch_sha256'):
                    record['reviewed_native_units'].append(key)
                    record['native_binding_method']='exact plan-bound RESULT and candidate patch hashes; qualified wrapper layout'
        if not record['reviewed_native_units']:
            for source,digest in seal.get('original_inputs',{}).items():
                if Path(source).name=='candidate.patch' and Path(source).is_file() and sha(Path(source))==digest:
                    for key,n in native.items():
                        if Path(source).is_relative_to(Path(key)) and n['patch_sha256']==digest:record['reviewed_native_units'].append(key)
        if record['mode'] is None and plan.get('feedback_sha256') in feedback_files:
            feedback=load(feedback_files[plan['feedback_sha256']]);wanted=feedback.get('local_attempt') or feedback.get('initial_row');patch=feedback.get('candidate_patch_sha256')
            record['reviewed_native_units']=[key for key,n in native.items() if n['id']==wanted and (not patch or n['patch_sha256']==patch)]
            record['source_hashes'][str(feedback_files[plan['feedback_sha256']])]=plan['feedback_sha256']
        if not record['mode'] and record['reviewed_native_units']:record['mode']=native[record['reviewed_native_units'][0]]['mode']
        if (run/'measurement.json').exists():
            recorded=load(run/'measurement.json').get('jsonl',{}).get('usage',{})
            record['measurement_usage_matches_raw_events']=all(recorded.get(k)==record['usage'].get(k) for k in KEYS)
            record['measurement_usage_as_recorded']=recorded
        record['model_profile_source']='requested plan profile; no independently invented provider revision'
        accounting=run/'assistance-accounting.json'
        if accounting.exists():
            cost=load(accounting);record['raw_semantic_review_advisory']=cost.get('semantic_review_advisory');record['candidate_unmodified']=cost.get('candidate_unmodified_by_review')
        if (run/'launch-start.json').exists():record['started_at']=load(run/'launch-start.json').get('started_unix')
        if identity in calls:
            old=calls[identity];assert old['usage']==record['usage'],('same call conflicting usage',identity);old['occurrences'].append(str(run));old['source_hashes'].update(record['source_hashes']);continue
        calls[identity]=record
    def branch_for(case,mode,paths):
        joined=' '.join(paths)
        if 'persistent-tu-off-auto-ci/' in joined:return 'supplemental-autoci'
        if 'mechanical' in joined:return 'supplemental-mechanical'
        if 'persistent-w66-light-identity/' in joined:return 'supplemental-identity'
        if case=='PAW-5' and ('/paw-clean' in joined or '-clean-' in joined):return 'clean-replay'
        if case=='PAW-5' and mode=='gpu-OFF-off-recommended':return 'historical-false-pin'
        return 'protocol-arm'
    calls=list(calls.values());baselines={};arms={}
    for call in calls:
        if call['role']=='main-only-implementation':baselines.setdefault((call['case'],call['condition']),[]).append(call);continue
        if call.get('mode') is None:continue
        branch=branch_for(call['case'],call['mode'],call['occurrences']+call['reviewed_native_units'])
        key=(call['case'],call['condition'],call['mode'],branch);arms.setdefault(key,{'calls':[],'native_units':set()})['calls'].append(call)
        arms[key]['native_units'].update(call['reviewed_native_units'])
    for key,n in native.items():
        if not n['patch_sha256'] or not n['case'] or 'profile-not-recorded' in n['mode'] or 'UNKNOWN' in n['mode']:continue
        arm_key=(n['case'],n['condition'],n['mode'],branch_for(n['case'],n['mode'],[key]))
        arms.setdefault(arm_key,{'calls':[],'native_units':set()})['native_units'].add(key)
    for arm in arms.values():
        todo=list(arm['native_units'])
        while todo:
            key=todo.pop();prior=native.get(key,{}).get('prior_unit')
            if prior and prior in native and prior not in arm['native_units']:
                row=native[key];parent=native[prior]
                expected=row.get('prior_result_sha256');actual=parent['source_hashes'].get(str(Path(prior)/'RESULT.json'))
                worker_expected=row.get('prior_worker_sha256');worker_actual=parent['source_hashes'].get(str(Path(prior)/'worker/receipt.json'))
                if ((expected and expected==actual) or (worker_expected and worker_expected==worker_actual)) and (not row.get('prior_session_sha256') or row['prior_session_sha256'] in parent['session_hashes'].values()):arm['native_units'].add(prior);todo.append(prior)
    for key,arm in arms.items():
        case,cond,mode,_=key
        present={r['call_id'] for r in arm['calls']}
        for call in calls:
            if call['role']=='main-only-implementation' or (call['case'],call['condition'],call.get('mode'))!=(case,cond,mode):continue
            if call['call_id'] not in present and any(unit in arm['native_units'] for unit in call['reviewed_native_units']):
                arm['calls'].append(call);present.add(call['call_id'])
    comparisons=[]
    for key,arm in sorted(arms.items()):
        case,cond,mode,branch=key;base=baselines.get((case,cond),[]);timeline=[{'kind':'paid-main-execution','call_id':r['call_id'],'role':r['role'],'started_at':r.get('started_at'),'wall_s':r['execution'].get('wall_s'),'qualification':r['qualification']} for r in arm['calls']]+[{'kind':'native-phase','source_unit':n,'started_at':native[n]['started_at'],'terminal_at':native[n]['terminal_at'],'raw_status':native[n]['raw_status']} for n in sorted(arm['native_units'])]
        captured=[r for n in arm['native_units'] for r in native[n]['wire_receipts']]
        unique={r['receipt_sha256']:r for r in captured}
        categories={}
        for call in arm['calls']:
            label='historical_first_light_review' if call['qualification'].startswith('historical first light') else 'qualified_fresh_light_rerun' if call['qualification'].startswith('owner-designated qualified') else 'paid_semantic_guidance' if call['role'] in ['guidance','initial-diagnosis'] else 'other_final_acceptance_or_takeover'
            categories.setdefault(label,[]).append(call)
        paid_vector=vector(arm['calls']);baseline_vector=vector(base)
        ratios={}
        for field in KEYS:
            numerator=paid_vector['usage'][field];denominator=baseline_vector['usage'][field]
            ratios[field]=numerator['known_sum']/denominator['known_sum'] if numerator['known_sum'] is not None and numerator['unknown_count']==denominator['unknown_count']==0 and denominator['known_sum'] else None
        ratios['sum_cli_execution_walls_s']=paid_vector['sum_cli_execution_walls_s']['known_sum']/baseline_vector['sum_cli_execution_walls_s']['known_sum'] if paid_vector['sum_cli_execution_walls_s']['known_sum'] is not None and paid_vector['sum_cli_execution_walls_s']['unknown_count']==baseline_vector['sum_cli_execution_walls_s']['unknown_count']==0 and baseline_vector['sum_cli_execution_walls_s']['known_sum'] else None
        comparisons.append({'case':case,'condition':cond,'mode':mode,'branch':branch,'paid_call_ids':sorted({r['call_id'] for r in arm['calls']}),'paid_execution_vectors':paid_vector,'separate_paid_cost_categories':{name:vector(rows) for name,rows in sorted(categories.items())},'unconditional_paid_to_same_condition_main_ratios':ratios,'native_phase_units':sorted(arm['native_units']),'native_wire_generation_known':stable_sum(r['predicted_n'] for r in unique.values()),'native_unknown_receipts':sum(r['predicted_n'] is None for r in unique.values()),'native_duplicate_receipt_references_excluded':len(captured)-len(unique),'native_unreceipted_archives':sum(len(native[n]['unreceipted_archives']) for n in arm['native_units']),'native_token_monetary_assumption':'zero local token charge by experiment convention; compute/time is separate','timeline':sorted(timeline,key=lambda r:r.get('started_at') or 0),'same_condition_main_only_call_ids':[r['call_id'] for r in base],'same_condition_main_only_execution_vectors':vector(base),'comparison_policy':'this alternative arm only; never compare a cross-arm sum against one baseline; shared parent phases may be referenced once in each alternative, never summed across alternatives'})
    output={'schema':'a3b.paid-call-accounting.v1','calls':sorted(calls,key=lambda r:(r['case'] or '',r['condition'],r['occurrences'][0])),'unlaunched_plans':planned,'native_phases':list(native.values()),'alternative_arm_comparisons':comparisons,'main_only_groups':[{'case':case,'condition':cond,'calls':[r['call_id'] for r in rows],'vectors':vector(rows)} for (case,cond),rows in sorted(baselines.items())],'global_unique_observed_execution_vectors':vector(calls),'global_total_scope':'inventory only, not an alternative-arm effectiveness comparison','source_native_input':{'path':str(a.native_input),'sha256':sha(a.native_input)},'limits':['All historical failed-review and later qualified-review execution costs remain separate and unconditional.','Cached and uncached input are distinct; reasoning tokens are a subset of output, never added again.','CLI execution walls include local tools; sums are not parallel batch elapsed or isolated model compute.','Manager/setup/coordination/source-audit costs are unisolated, neither zero nor included.','No semantic final verdict is invented from model advisories or structural rc; incomplete usage remains unknown.','Unlaunched future reviews are not charged zero as though complete.','Main-only light W66 is an eighth implementation execution condition, not a seventh unique task.'],'owner_quality_records':[{'path':str(path),'sha256':sha(path),'record':load(path),'scope':'owner source/qualified-grade judgment, separate from raw model advisory and raw oracle'} for path in sorted((BASE/'quality-assessments/registry').glob('*.json'))],'collector_source_sha256':sha(Path(__file__)),'model_calls':0}
    a.out.mkdir(parents=True);(a.out/'ACCOUNTING.json').write_text(json.dumps(output,indent=2)+'\n');print(json.dumps({'output':str(a.out),'unique_observed_paid_executions':len(calls),'alternative_arm_comparisons':len(comparisons),'unlaunched_plans':len(planned),'model_calls':0}))
if __name__=='__main__':main()
