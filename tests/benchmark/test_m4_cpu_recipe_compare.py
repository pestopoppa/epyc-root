"""Model-free pre-run tests for the M4 Q38FN diagnostic frame."""
import hashlib, importlib.util, json, sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('m4_cpu_compare_test',ROOT/'scripts/benchmark/m4_cpu_recipe_compare.py')
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def packet(tmp, monkeypatch):
    monkeypatch.setenv('FILLER_ID','inf22-q38-test')
    monkeypatch.setattr(mod.subprocess,'check_output',lambda *a,**k:'c72ec82f5417bb2937310326120f149b665e8400\n')
    images={}
    for arm,commit in [('baseline','c72ec82f5417bb2937310326120f149b665e8400'),('candidate','bc441f1a261766d11bfeff21668a1031c4dbf8cd')]:
        root=tmp/arm;(root/'bin').mkdir(parents=True);bin=root/'bin/llama-server';lib=root/'bin/libggml.so';bin.write_bytes(b'bin');lib.write_bytes(b'lib')
        manifest=tmp/(arm+'.json');manifest.write_text(json.dumps({'source_commit':commit,'root':str(root),'files':{'bin/llama-server':sha(bin),'bin/libggml.so':sha(lib)}}))
        images[arm]={'path':str(manifest),'sha256':sha(manifest)}
    model=tmp/'model';model.write_bytes(b'model');draft=tmp/'draft';draft.write_bytes(b'draft')
    inputs=[]
    for source in (model,draft):
        receipt=tmp/(source.name+'-custody.json');receipt.write_text(json.dumps({'schema':'epyc.m4.file-custody.v1','path':str(source),'sha256':sha(source),'identity':mod._identity(source.stat())}))
        inputs.append({'path':str(source),'sha256':sha(source),'custody_path':str(receipt),'custody_sha256':sha(receipt)})
    configs={}
    for name,threads,env in [('canonical_t48',48,{'GGML_FA_SPLIT_KV':'0','GGML_NOHUGEPAGE_PROCESS':'1','GGML_FUSED_DECODE_OFF':'1'}),('configured_t96',96,{'GGML_FA_SPLIT_KV':'0','GGML_NOHUGEPAGE_PROCESS':None,'GGML_FUSED_DECODE_OFF':None})]:
        configs[name]={'name':name,'role':'architect_general','threads':threads,'server_context_size':262144,'recipe_env':env,'model':str(model),'draft_model':str(draft),'image_path':None}
    src={'compare':'scripts/benchmark/m4_cpu_recipe_compare.py','runner':'scripts/benchmark/m4_cpu_producer/native/k35_stack_context_matrix_runner.py',
         'writer':'scripts/benchmark/m4_cpu_producer/capture.py','comparator':'scripts/benchmark/m4_cpu_producer/native/compare_v9_promotion_arms.py','ownership':'scripts/benchmark/m4_cpu_ownership/owned.py'}
    plan={'schema':'epyc.m4.q38.recipe-comparison.v1','status':'REVIEWED_DIAGNOSTIC','decision_authority':'descriptive_only','row_id':'inf22-q38-test',
          'champion':'c72ec82f5417bb2937310326120f149b665e8400','candidate':'bc441f1a261766d11bfeff21668a1031c4dbf8cd',
          'sources':{k:sha(ROOT/v) for k,v in src.items()},'images':images,'model':{'path':str(model),'sha256':sha(model)},
          'inputs':inputs,
          'recipes':configs,'cells':[{'rep':r,'arm':a,'recipe':n} for r in range(3) for a in ('baseline','candidate') for n in configs]}
    path=tmp/'plan.json';path.write_text(json.dumps(plan));return path,plan


def test_frame_binds_complete_inputs_and_images(tmp_path, monkeypatch):
    path,plan=packet(tmp_path,monkeypatch)
    assert mod.verify(path,sha(path))['plan']['decision_authority']=='descriptive_only'
    Path(plan['inputs'][0]['path']).write_bytes(b'changed')
    with pytest.raises(ValueError,match='identity changed'): mod.verify(path,sha(path))


@pytest.mark.parametrize('defect',['unreviewed','extra_recipe_axis','missing_cell','wrong_row','wrong_env'])
def test_frame_refuses_unbound_or_changed_plan(tmp_path,monkeypatch,defect):
    path,plan=packet(tmp_path,monkeypatch)
    if defect=='unreviewed':plan['status']='UNARMED_REVIEW_REQUIRED'
    if defect=='extra_recipe_axis':plan['recipes']['canonical_t48']['parallel']=2
    if defect=='missing_cell':plan['cells'].pop()
    if defect=='wrong_row':plan['row_id']='other'
    if defect=='wrong_env':plan['recipes']['canonical_t48']['recipe_env']['GGML_NOHUGEPAGE_PROCESS']=None
    path.write_text(json.dumps(plan))
    with pytest.raises(ValueError):mod.verify(path,sha(path))


def test_guarded_entry_refuses_empty_or_changed_enrollment(tmp_path,monkeypatch):
    spec=importlib.util.spec_from_file_location('m4_recipe_entry_test',ROOT/'scripts/benchmark/m4_cpu_recipe_entry.py')
    entry_mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=entry_mod;spec.loader.exec_module(entry_mod)
    root=tmp_path/'capture';root.mkdir();out=root/'attempt';out.mkdir();path=tmp_path/'plan';path.write_text('{}')
    with pytest.raises(ValueError,match='enrollment absent'):
        entry_mod.check_enrollment(path,sha(path),'row',out)
    names=[ROOT/'scripts/benchmark/m4_cpu_recipe_entry.py',ROOT/'scripts/benchmark/m4_cpu_recipe_compare.py',
           *[ROOT/'scripts/benchmark/m4_cpu_ownership'/n for n in ('entry.py','watch.py','lease_owner.py','m4_cgroup_guard.py','owned.py')],
           *[ROOT/'scripts/benchmark/m4_cpu_producer'/n for n in ('capture.py','native/k35_stack_context_matrix_runner.py','native/compare_v9_promotion_arms.py')]]
    monkeypatch.setattr(entry_mod.enrollment,'ENABLED',True);monkeypatch.setattr(entry_mod.enrollment,'ROW_ID','row')
    monkeypatch.setattr(entry_mod.enrollment,'PLAN_PATH',str(path));monkeypatch.setattr(entry_mod.enrollment,'PLAN_SHA256',sha(path))
    monkeypatch.setattr(entry_mod.enrollment,'OUTPUT_ROOT',str(root));monkeypatch.setattr(entry_mod.enrollment,'SOURCE_SEALS',{str(p):sha(p) for p in names})
    entry_mod.check_enrollment(path,sha(path),'row',out)
    path.write_text('{"changed":true}')
    with pytest.raises(ValueError,match='plan or row enrollment mismatch'):
        entry_mod.check_enrollment(path,sha(path),'row',out)

def test_qualification_runs_owned_fixture_and_stops_cleanly(tmp_path,monkeypatch):
    import argparse,os,threading,time
    from datetime import datetime,timedelta,timezone
    spec=importlib.util.spec_from_file_location('m4_recipe_qual_test',ROOT/'scripts/benchmark/m4_cpu_recipe_entry.py')
    q=importlib.util.module_from_spec(spec);sys.modules[spec.name]=q;spec.loader.exec_module(q)
    dd=tmp_path/'dryrun';(dd/'grants').mkdir(parents=True);attempt=dd/'native-attempts'/'attempt-test';attempt.mkdir(parents=True)
    flags=tmp_path/'flags';flags.mkdir();result=attempt/'native-result.json';stop=dd/'stop';row='inf22-q38-test'
    now=datetime.now(timezone.utc);grant=dd/'grants'/f'{row}.grant'
    grant.write_text('regions=0-3 start='+ (now-timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%MZ') +' end='+ (now+timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%MZ')+f' holds=q0 schema=epyc.rowflow.dryrun-grant.v1 id={row} kind=rowflow-dryrun admission_class=block-timing-quiet')
    deadline=int(time.time()+90)
    for k,v in {'FILLER_DRYRUN':'1','FILLER_SMOKE':'1','FILLER_DRYRUN_DIR':str(dd),
                'FILLER_DRYRUN_RESULT_PATH':str(result),'FILLER_FLAGS_DIR':str(flags),
                'FILLER_STOPFILE':str(stop),'FILLER_CPUS':'0-3','FILLER_DEADLINE':str(deadline)}.items():monkeypatch.setenv(k,v)
    monkeypatch.setattr(q,'check_enrollment',lambda *args:None)
    a=argparse.Namespace(plan=tmp_path/'plan',plan_sha256='ignored',grant=grant,stop=stop,hold=flags,
        deadline=deadline,owner_pid=os.getppid(),owner_birth=q.watch.m4_cgroup_guard.birth(os.getppid()))
    def stop_after_unit():
        end=time.monotonic()+10
        while not result.exists() and time.monotonic()<end:time.sleep(.02)
        if result.exists():stop.touch()
    worker=threading.Thread(target=stop_after_unit);worker.start()
    try: assert q.qualification(a,row)==75
    finally:worker.join(timeout=12)
    assert json.loads(result.read_text())['measurement'] is False
    assert json.loads((attempt/'watch/watch-result.json').read_text())['containment_empty'] is True

def test_qualification_worker_refuses_real_environment(monkeypatch):
    spec=importlib.util.spec_from_file_location('m4_recipe_qual_reject',ROOT/'scripts/benchmark/m4_cpu_recipe_entry.py')
    q=importlib.util.module_from_spec(spec);sys.modules[spec.name]=q;spec.loader.exec_module(q)
    monkeypatch.delenv('FILLER_DRYRUN',raising=False)
    with pytest.raises(ValueError,match='guarded smoke'):q.qualification_worker()


def test_frame_ignores_loader_threads_but_not_real_recipe_differences(tmp_path, monkeypatch):
    path,plan=packet(tmp_path,monkeypatch)
    plan['recipes']['canonical_t48']['extra_args']=['-b','512','--load-threads','48']
    plan['recipes']['configured_t96']['extra_args']=['-b','512','--load-threads=96']
    path.write_text(json.dumps(plan))
    mod.verify(path,sha(path))
    plan['recipes']['configured_t96']['extra_args']=['-b','1024','--load-threads','96']
    path.write_text(json.dumps(plan))
    with pytest.raises(ValueError,match='unintended recipe differences'):mod.verify(path,sha(path))
