"""Only an independently enrolled diagnostic plan can bind diagnostic cells."""
import hashlib,json,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/vidya'))
from adapters import m4_cpu_speed as reader
from claim_tuple import ProjectionError

def fixture(tmp_path):
    root=tmp_path.resolve(); scenario={'name':'q38fn_canonical_t48','threads':48}
    recipe={'scenario':scenario['name'],'scenario_config':scenario}
    plan={'schema':'epyc.m4.q38.recipe-comparison.v1','status':'REVIEWED_DIAGNOSTIC',
          'decision_authority':'descriptive_only','model':{'path':'/model','sha256':'a'*64},
          'recipes':{'canonical_t48':scenario,'configured_t96':{'name':'configured','threads':96}},
          'cells':[{'rep':i,'arm':a,'recipe':r} for i in range(3) for a in ('baseline','candidate') for r in ('canonical_t48','configured_t96')]}
    sha=lambda b:hashlib.sha256(b).hexdigest()
    server=root/'img/bin/llama-server';server.parent.mkdir(parents=True);server.write_bytes(b'server')
    plan['champion']='c'*40;plan['candidate']='d'*40;plan['images']={}
    for arm,commit in (('baseline','c'*40),('candidate','d'*40)):
        m=root/f'{arm}-manifest.json'
        m.write_bytes(json.dumps({'source_commit':commit,'root':str(root/'img'),'files':{'bin/llama-server':sha(b'server')}}).encode())
        plan['images'][arm]={'path':str(m),'sha256':sha(m.read_bytes())}
    raw=json.dumps(plan).encode();(root/'comparison-plan.json').write_bytes(raw)
    cfg=reader.SourceConfig(root,root,hashlib.sha256(raw).hexdigest())
    native={'receipt':str(root/'00-baseline-canonical_t48/process-captures/baseline-pair-00.json'),
            'role':'architect_general','model':'/model','recipe':recipe,
            'row':{'category':'BASELINE','extra':{'pair':0,'model_sha256':'a'*64,'context':8192,'binary':str(server)}}}
    return cfg,native,plan

def test_diagnostic_plan_cell_bound(tmp_path):
    cfg,native,_=fixture(tmp_path);reader._verify_diagnostic(native,cfg)

@pytest.mark.parametrize('mutation',[
 lambda n:n.update(role='worker'),
 lambda n:n.update(receipt=n['receipt'].replace('baseline-pair-00','baseline-pair-01')),
 lambda n:n['recipe']['scenario_config'].update(threads=96),
 lambda n:n['row']['extra'].update(model_sha256='b'*64),
 lambda n:n['row']['extra'].update(pair=1),
])
def test_diagnostic_mismatches_refused(tmp_path,mutation):
    cfg,native,_=fixture(tmp_path);mutation(native)
    with pytest.raises(ProjectionError):reader._verify_diagnostic(native,cfg)

def test_diagnostic_plan_tampering_refused(tmp_path):
    cfg,native,plan=fixture(tmp_path);plan['status']='DRAFT_NOT_FOR_EXECUTION'
    (tmp_path/'comparison-plan.json').write_text(json.dumps(plan))
    with pytest.raises(ProjectionError):reader._verify_diagnostic(native,cfg)

def test_image_manifest_tampering_refused(tmp_path):
    cfg,native,plan=fixture(tmp_path);(tmp_path/'baseline-manifest.json').write_text('{}')
    with pytest.raises(ProjectionError,match='manifest changed'):reader._verify_diagnostic(native,cfg)

def test_image_server_modified_refused(tmp_path):
    cfg,native,_=fixture(tmp_path);(tmp_path/'img/bin/llama-server').write_bytes(b'other')
    with pytest.raises(ProjectionError,match='modified after capture'):reader._verify_diagnostic(native,cfg)

def test_captured_binary_must_be_image_server(tmp_path):
    cfg,native,_=fixture(tmp_path);other=tmp_path/'other';other.write_bytes(b'server')
    native['row']['extra']['binary']=str(other)
    with pytest.raises(ProjectionError,match='not the manifest image server'):reader._verify_diagnostic(native,cfg)

def test_compare_harness_hash_not_required(tmp_path):
    cfg,_,_=fixture(tmp_path)
    assert not hasattr(reader,'DIAGNOSTIC_COMPARE_SHA256')

@pytest.mark.parametrize('token',['GGML_UNBOUND=1','LLAMA_ARG_CTX_SIZE=42','LD_PRELOAD=/tmp/x'])
def test_unbound_environment_refused(token):
    argv=['env','GGML_IQK=1','GGML_FA_SPLIT_KV=0',token,'llama-server']
    with pytest.raises(ProjectionError,match='unbound native environment'):
        reader._verify_recipe_env(argv,{'GGML_FA_SPLIT_KV':'0'})
