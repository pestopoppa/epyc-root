import hashlib
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('m4_auth',ROOT/'scripts/benchmark/m4_cpu_ownership/native_authorization.py')
auth=importlib.util.module_from_spec(spec);spec.loader.exec_module(auth)

def h(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def packet(tmp):
    model=tmp/'model';model.write_bytes(b'model');evidence=tmp/'evidence';evidence.write_text('reviewed recipe')
    context=tmp/'context';context.write_text('historical conclusion present')
    history=tmp/'history';history.write_text('do not repeat history')
    scope=tmp/'scope';scope.write_text(json.dumps({'cpu':[{'role':'worker_general','model_path':str(model)}]}))
    recipe={'best_evidence':str(evidence),'best_evidence_sha256':h(evidence),'scenario_config':{'draft_model':None},'draft_model_sha256':''}
    native=tmp/'native';native.write_text(json.dumps({'models':[{'role':'worker_general','model_path':str(model),'model_sha256':h(model),'additional_model_inputs':[],'baseline':recipe,'candidate':recipe}]}))
    binding=tmp/'binding';binding.write_text(json.dumps({'status':'SOURCE_BOUND_ONLY','errors':[],'roles':[{'backend':'cpu','role':'worker_general','model_path':str(model)}]}))
    images={}
    for arm in ('baseline','candidate'):
        root=tmp/arm;bin=root/'bin';bin.mkdir(parents=True)
        binary=bin/'llama-server';binary.write_bytes(b'binary');lib=bin/'libggml-cpu.so';lib.write_bytes(b'library')
        seals={'bin/llama-server':h(binary),'bin/libggml-cpu.so':h(lib)}
        manifest=tmp/(arm+'-manifest');manifest.write_text(json.dumps({'source_commit':auth.CHAMPION if arm=='baseline' else auth.CANDIDATE,'files':seals}))
        images[arm]={'root':str(root),'files':seals,'build_manifest':str(manifest),'build_manifest_sha256':h(manifest)}
    return {'baseline_commit':auth.CHAMPION,'candidate_commit':auth.CANDIDATE,'role':'worker_general',
            'scope':str(scope),'scope_sha256':h(scope),'native_plan':str(native),'native_plan_sha256':h(native),
            'binding':str(binding),'binding_sha256':h(binding),'images':images,
            'canary':{'context':str(context),'context_sha256':h(context),'context_witness':'historical conclusion',
                      'history':str(history),'history_sha256':h(history),'history_witness':'do not repeat'}}

def test_fully_bound_admission(tmp_path):
    plan=packet(tmp_path)
    result=auth.verify(plan,current_champion=auth.CHAMPION,enrolled=True)
    assert result['role']=='worker_general'

@pytest.mark.parametrize('defect',['unenrolled','champion','model','library','scope','canary'])
def test_unbound_or_drifted_inputs_refuse(tmp_path,defect):
    plan=packet(tmp_path)
    if defect=='model': Path(json.loads(Path(plan['native_plan']).read_bytes())['models'][0]['model_path']).write_bytes(b'changed')
    if defect=='library': (Path(plan['images']['candidate']['root'])/'bin/libggml-cpu.so').write_bytes(b'changed')
    if defect=='scope': Path(plan['scope']).write_text('{}')
    if defect=='canary': Path(plan['canary']['history']).write_text('changed')
    with pytest.raises(ValueError):
        auth.verify(plan,current_champion='bad' if defect=='champion' else auth.CHAMPION,enrolled=defect!='unenrolled')
