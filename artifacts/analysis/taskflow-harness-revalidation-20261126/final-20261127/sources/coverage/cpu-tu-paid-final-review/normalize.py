"""Explicit read-only projection of legacy owner/JOB/worker evidence; no models."""
from pathlib import Path
import argparse,hashlib,json,re,shutil
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def write(p,d):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(d,indent=2)+'\n')
def normalize(owner_path,grade=None):
    owner_path=owner_path.resolve();unit=owner_path.parent
    assert owner_path.name=='RESULT.json'
    owner=load(owner_path);job_path=unit/'JOB.json';worker_path=unit/'worker/receipt.json';job=load(job_path);worker=load(worker_path)
    assert owner.get('terminal_at') and worker.get('ended_at') and worker.get('session')
    assert worker.get('status') in ['review','succeeded','completed'],worker.get('status')
    cid=owner['case'];assert cid in ['TU-GR-1','MM-5'] and worker['case']==cid
    session_profile=worker['session_profile'];assert owner['backend']==job['backend']==session_profile['backend']
    assert owner['slot']==job['slot']==session_profile['slot']
    assert job['thinking'] is session_profile['thinking'] and job['sampling']==session_profile['sampling']
    assert owner.get('worker_receipt_sha256')==sha(worker_path)
    assert worker['job_sha256']==sha(job_path)
    assert not worker.get('outside_scope') and not worker.get('unsafe_paths')
    plan_path=unit.parent.parent/'PLAN.json';plan=load(plan_path)
    match=re.search(r'-(?:objective|guidance|paid)-([12])$',unit.name);ordinal=int(match[1]) if match else 0
    row=owner
    paid_plan = None
    if 'jobs' in plan:
        matching = [item for item in plan['jobs'] if item['id'] == unit.name]
        if len(matching) != 1 or ordinal != 2:
            raise ValueError('expected the unique authorized native paid2 row')
        paid_plan = matching[0]
        row = paid_plan['row']
        for name, expected in paid_plan['sha256'].items():
            if sha(name) != expected:
                raise ValueError('authorized paid guidance input changed: ' + name)
    elif 'cohort' in plan:
        candidates=[item['row'] for item in plan['cohort'] if any(item['id']+suffix==unit.name for suffix in ['',f'-objective-{ordinal}',f'-guidance-{ordinal}'])]
        assert len(candidates)==1;row=candidates[0]
    profile=row.get('profile');assert profile in ['on-coding','off-common-on-sampling','off-recommended']
    patch=unit/'worker/candidate/candidate.patch';assert sha(patch)==worker['patch_sha256']
    base=HERE/'projections'/unit.name
    assert not base.exists(),'never overwrite a prior evidence projection'
    (base/'independent').mkdir(parents=True);shutil.copy2(patch,base/'independent/candidate.patch')
    sources={str(p):sha(p) for p in [owner_path,job_path,worker_path,plan_path,patch]}
    if paid_plan:
        sources.update(paid_plan['sha256'])
        paid = paid_plan['source_guidance']
        if owner['source_guidance'] != paid or paid['paid_model_calls'] != 1:
            raise ValueError('actual terminal guidance accounting disagrees with plan')
        guidance = Path(job['prompt'])
        measure = load(guidance.parent/'measurement.json')
        turns = [json.loads(line) for line in (guidance.parent/'events.jsonl').read_text().splitlines()]
        complete = [turn['usage'] for turn in turns if turn.get('type') == 'turn.completed']
        if (measure['execution']['wall_s'] != paid['measured_wall_s']
                or len(complete) != 1
                or any(complete[0].get(key) != paid['usage'][key] for key in
                       ('input_tokens','cached_input_tokens','output_tokens','reasoning_output_tokens'))):
            raise ValueError('measured actual guidance usage disagrees with plan')
    session=unit/'worker/session.json'
    if session.exists():sources[str(session)]=sha(session)
    feedback=[]
    if ordinal:
        prompt=unit/'VERIFIER-FEEDBACK.md' if ordinal==1 else Path(job['prompt'])
        assert prompt.is_file() and sha(prompt)==job['prompt_sha256']==worker['prompt_sha256']
        if ordinal==2:
            prior_worker=Path(worker['resume']['prior_run']).resolve()
            assert prior_worker.name=='worker'
            prior_unit=prior_worker.parent
            assert re.search(r'-(?:objective|guidance)-1$',prior_unit.name)
            prior_receipt=prior_worker/'receipt.json';prior_job=prior_unit/'JOB.json';first_prompt=prior_unit/'VERIFIER-FEEDBACK.md'
            assert sha(prior_receipt)==worker['resume']['receipt_sha256']
            prior=load(prior_receipt);old_job=load(prior_job)
            assert prior['session']==worker['session'] and sha(prior_job)==prior['job_sha256']
            assert sha(first_prompt)==prior['prompt_sha256']==old_job['prompt_sha256']
            assert old_job['backend']==job['backend'] and old_job['thinking'] is job['thinking'] and old_job['sampling']==job['sampling']
            for path in [prior_receipt,prior_job,first_prompt]:sources[str(path)]=sha(path)
            feedback.append({'path':str(first_prompt),'sha256':sha(first_prompt),'native_ordinal':1,'help_kind':'deterministic-objective-verifier; zero paid semantic guidance'})
        sources[str(prompt)]=sha(prompt)
        feedback.append({'path':str(prompt),'sha256':sha(prompt),'native_ordinal':ordinal,'help_kind':'deterministic-objective-verifier; zero paid semantic guidance' if ordinal==1 else 'paid-main-source-guidance; one semantic round'})
    result={'id':unit.name,'case':cid,'backend':job['backend'],'slot':job['slot'],'thinking':job['thinking'],'profile':profile,'sampling':job['sampling'],'status':owner['status'],'worker_status':worker['status'],'terminal_at':owner['terminal_at'],'started_at':worker['started_at'],'session':worker['session'],'changed_files':worker['changed_files'],'patch_sha256':worker['patch_sha256'],'outside_scope':worker.get('outside_scope',[]),'unsafe_paths':worker.get('unsafe_paths',[]),'generation_observed':worker.get('generated_observed'),'model_wall_s':worker['ended_at']-worker['started_at'],'request_cap':job['request_cap'],'generated_ceiling':job['generated_ceiling'],'wall_s':job['wall_s'],'native_ordinal':ordinal,'owner_raw_id':owner['id'],'projection_sources':sources,'actual_prior_feedback':feedback,'projection_schema':'legacy.owner-job-worker.review.v1','projection_semantics':'explicit schema adaptation only; original raw statuses/ids preserved and no source judgment fabricated'}
    if paid_plan:
        result['prior_measured_paid_guidance'] = paid
    if grade:
        grade=grade.resolve();g=load(grade);assert g['candidate_patch_sha256']==worker['patch_sha256']
        if g['rc'] != 0 or g['oracle_manifest_sha256'] != 'f0f7978b540f0f83d5c5fef3e4f8e45badb11475d4c4d35cae74ea8584816c4b':
            raise ValueError('expected actual pinned TU V3 pass for this exact paid2 candidate')
        for stream in ('stdout','stderr'):
            path = grade.parent / (stream + '.log')
            if sha(path) != g[stream + '_sha256']:
                raise ValueError('actual grade streams changed')
            sources[str(path)] = sha(path)
        sources[str(grade)]=sha(grade)
        # Do not send prior source-expert recommendations, answers or oracle code.
        clean={key:g[key] for key in ['rc','oracle_sha256','acceptance_version','candidate_patch_sha256'] if key in g}
        clean['acceptance_version'] = 'TU V3'
        clean['oracle_manifest_sha256'] = g['oracle_manifest_sha256']
        clean['scope']='deterministic checker receipt only; no semantic acceptance inferred'
        write(base/'STRUCTURAL-RECEIPT.json',clean)
        result['oracle']={key:clean[key] for key in ['rc','oracle_sha256','acceptance_version'] if key in clean}
    write(base/'RESULT.json',result)
    write(base/'PROJECTION.json',{'source_owner_result':str(owner_path),'source_hashes':sources,'projected_result_sha256':sha(base/'RESULT.json'),'projected_patch_sha256':sha(base/'independent/candidate.patch'),'objective_ordinal':ordinal,'owner_raw_id_preserved':owner['id'],'review_input_id':unit.name,'original_verifier_feedback_preserved_verbatim':True,'source_recommendation_or_direct_answer_exposed':False,'model_calls':0})
    return {'result':str(base/'RESULT.json'),'structural_receipt':str(base/'STRUCTURAL-RECEIPT.json') if grade else None,'native_ordinal':ordinal}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--owner-result',type=Path,required=True);p.add_argument('--deterministic-grade',type=Path);a=p.parse_args();print(json.dumps(normalize(a.owner_result,a.deterministic_grade),indent=2))
