"""Synthetic contract checks for prospective M4 process capture; no model or ledger writes."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/vidya'))
from adapters import m4_cpu_speed as reader
from claim_tuple import ProjectionError
import cli
import ingest_sources

PRODUCER_FIXTURE = ROOT/'tests/vidya/fixtures/m4_cpu_producer'
PRIVATE_PREFIX = '/mnt/raid0/llm/tmp/refactor-01a16fc3/m4-full-gate-next-source/cpu-packet'

@pytest.fixture(autouse=True)
def no_private_producer(monkeypatch):
    import builtins
    original_open = builtins.open
    original_io_open = __import__('io').open
    def checked_open(file, *args, **kwargs):
        if isinstance(file, (str, Path)) and str(file).startswith(PRIVATE_PREFIX):
            raise PermissionError('private host producer forbidden in tests')
        return original_open(file, *args, **kwargs)
    def checked_io_open(file, *args, **kwargs):
        if isinstance(file, (str, Path)) and str(file).startswith(PRIVATE_PREFIX):
            raise PermissionError('private host producer forbidden in tests')
        return original_io_open(file, *args, **kwargs)
    monkeypatch.setattr(builtins, 'open', checked_open)
    monkeypatch.setattr(__import__('io'), 'open', checked_io_open)
    with pytest.raises(PermissionError):
        Path(PRIVATE_PREFIX, 'capture.py').read_bytes()
    monkeypatch.setattr(reader, 'PRODUCER_ROOT', PRODUCER_FIXTURE.resolve())
    for name, expected in reader.SOURCE_SEALS.items():
        assert hashlib.sha256((PRODUCER_FIXTURE/name).read_bytes()).hexdigest()==expected

@pytest.fixture
def record(tmp_path, monkeypatch):
    producer=reader.PRODUCER_ROOT
    spec=importlib.util.spec_from_file_location('m4_test_capture',producer/'capture.py')
    capture=importlib.util.module_from_spec(spec); spec.loader.exec_module(capture)
    monkeypatch.setattr(reader,'CAPTURE_ROOT',tmp_path.resolve())
    run=tmp_path/'model-000/pair-00/baseline'; run.mkdir(parents=True)
    prompt=run/'prompt.txt'; prompt.write_text('synthetic fixture')
    prompt_hash=run/'prompt.sha256'; prompt_hash.write_text(hashlib.sha256(prompt.read_bytes()).hexdigest())
    model=tmp_path/'fixture'; binary=tmp_path/'image/bin/llama-server'
    (run/'plan.json').write_text(json.dumps({'binary':str(binary),'cells':[{'server_argv':[str(binary),'-m',str(model)]}]}))
    summary={'status':'ok','results':[{'status':'ok','passed_min_completion':True,'scenario':'fixture','decode_tps':1.0,'nominal_context':2048,'cleanup':{'completed':True,'dead':True},'prompt_path':str(prompt),'prompt_sha256_path':str(prompt_hash)}]}
    sp=run/'summary.json'; sp.write_text(json.dumps(summary))
    row={'decode_tps':1.0,'summary_path':str(sp),'summary_sha256':hashlib.sha256(sp.read_bytes()).hexdigest(),'scenario':'fixture','prompt_sha256':prompt_hash.read_text()}
    kwargs=dict(directory=tmp_path/'model-000/process-captures',row=row,arm='baseline',pair=0,role='fixture',model=str(model),model_sha='a'*64,recipe={'scenario':'fixture'},context=2048,binary=binary,commit='c72ec82f5417bb2937310326120f149b665e8400',producer=producer/'dispatch.py',runner=producer/'native/k35_stack_context_matrix_runner.py',comparator=producer/'native/compare_v9_promotion_arms.py')
    capture.capture(**kwargs)
    return kwargs['directory']/'baseline-pair-00.json',sp,kwargs,capture

def test_write_once_partial_and_tamper(record):
    path,summary,kwargs,capture=record
    native=reader.native_rows(path)[0]
    assert reader.project(native).value == 1.0
    assert not (path.parent.parent/'throughput.json').exists()
    with pytest.raises(FileExistsError): capture.capture(**kwargs)
    plan=summary.with_name('plan.json'); plan.write_text(plan.read_text()+' ')
    with pytest.raises(ProjectionError): reader.project(native)

def test_generic_cli_dry_run_and_foreign_source(record,tmp_path,capsys):
    path,_,_,_=record; ledger=tmp_path/'private-ledger.jsonl'
    assert set(cli._FILE_SOURCES)==set(ingest_sources.SOURCES)
    def run(source):
        assert cli.main(['--json','--ledger',str(ledger),'ingest',source,'--path',str(path),'--as-of','2026-10-27T15:00:00Z','--dry-run'])==0
        return json.loads(capsys.readouterr().out)
    own=run('m4-cpu-recipe-speed'); assert (own['rows_projected'],own['frames_emitted'])==(1,3)
    other=run('champion-fold-gate'); assert other['rows_projected']==0 and len(other['declined'])==1
    assert not ledger.exists()

def test_dispatcher_saves_first_process_before_next_failure(tmp_path, monkeypatch):
    """Only synthetic input bytes and in-process substitutes; no server or model access."""
    import os, time
    from types import SimpleNamespace
    producer=reader.PRODUCER_ROOT
    monkeypatch.syspath_prepend(str(producer))
    spec=importlib.util.spec_from_file_location('m4_dispatch_test',producer/'dispatch.py')
    dispatch=importlib.util.module_from_spec(spec); sys.modules[spec.name]=dispatch; spec.loader.exec_module(dispatch)
    model=tmp_path/'synthetic-input'; model.write_text('synthetic')
    digest=hashlib.sha256(model.read_bytes()).hexdigest()
    scope=tmp_path/'scope.json'; scope.write_text('{}'); plan=tmp_path/'plan.json'; plan.write_text('{}')
    entry={'model_sha256':digest,'additional_model_inputs':[], 'context':2048,
           'baseline':{'scenario':'fixture','treatment':'default-off'}, 'candidate':{'scenario':'fixture','treatment':'srpf-cap512'}}
    monkeypatch.setattr(dispatch,'scenarios_for_plan',lambda native,plan:{'fixture':SimpleNamespace(draft_model=None)})
    monkeypatch.setattr(dispatch,'validate',lambda scope,plan,scenarios:{('fixture',str(model)):entry,('another_role',str(tmp_path/'unused')):entry})
    class Comparator:
        PASS_RATIO=.98; FAIL_RATIO=.95
        def load_arm(self,paths,binary,arm):
            p=paths[0]
            return [{'decode_tps':1.0,'summary_path':str(p),'summary_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'scenario':'fixture','prompt_sha256':'a'*64}]
    cmp=Comparator()
    monkeypatch.setattr(dispatch,'module',lambda name,path:cmp if name=='m4_k35_compare_native' else object())
    real_is_file=Path.is_file
    def is_file(self):
        if str(self)=='/mnt/raid0/llm/tmp/compute-flags/grants/refactor-01a16fc3-m4-cpu-speed-all-20261027.grant': return True
        return real_is_file(self)
    monkeypatch.setattr(Path,'is_file',is_file)
    class FakeChild:
        count=0
        def __init__(self,command,env):
            FakeChild.count+=1; self.pid=999999999; self.returncode=0 if self.count==1 else 1
            path=Path(command[command.index('--output-dir')+1]); path.mkdir(parents=True)
            if self.returncode==0:
                (path/'summary.json').write_text('{"fixture":true}')
                (path/'plan.json').write_text('{"fixture":true}')
        def poll(self): return self.returncode
    monkeypatch.setattr(dispatch.subprocess,'Popen',FakeChild)
    for k,v in {'FILLER_ID':'refactor-01a16fc3-m4-cpu-speed-all-20261027','M4_SPEED_WRITER_WIRED':'1','FILLER_STOPFILE':str(tmp_path/'STOP'),'FILLER_DEADLINE':str(int(time.time())+60)}.items(): monkeypatch.setenv(k,v)
    out=tmp_path/'out'
    argv=['dispatch.py','--scope',str(scope),'--plan',str(plan),'--baseline-image',str(tmp_path/'base'),'--candidate-image',str(tmp_path/'cand'),'--out',str(out),'--role','fixture','--execute']
    monkeypatch.setattr(sys,'argv',argv)
    with pytest.raises(RuntimeError,match='native arm returned 1'): dispatch.main()
    assert FakeChild.count==2 and len(list(out.glob('model-000/process-captures/*.json')))==1
    assert not (out/'model-000/throughput.json').exists()
