"""Evidence binding rejects configured-only or altered M4 role recipes."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
PRODUCER = ROOT/'scripts/benchmark/m4_cpu_producer'
sys.path.insert(0, str(PRODUCER))
spec = importlib.util.spec_from_file_location('m4_best_evidence_dispatch', PRODUCER/'dispatch.py')
dispatch = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = dispatch
spec.loader.exec_module(dispatch)


def test_draft_refuses_before_examining_models():
    with pytest.raises(ValueError, match='draft or unreviewed'):
        dispatch.validate_execution_evidence({'status':'DRAFT_NOT_FOR_EXECUTION','models':[]})


def test_reviewed_attestation_requires_exact_arm_and_unchanged_basis(tmp_path):
    source = tmp_path/'capture.json'; source.write_bytes(b'original evidence')
    entry = {'role':'architect_general', 'model_path':'/m/model.gguf'}
    recipe_sha = 'a'*64
    for arm, source_commit in [('baseline','c72ec82f5417bb2937310326120f149b665e8400'),('candidate','bc441f1a261766d11bfeff21668a1031c4dbf8cd')]:
        attestation = tmp_path/(arm+'.json')
        data={'schema':'epyc.m4.cpu.best_recipe_evidence.v1','status':'REVIEWED_BEST', 'role':entry['role'], 'arm':arm,
              'model_path':entry['model_path'], 'source_commit':source_commit, 'recipe_sha256':recipe_sha,
              'reviewer':'test','rationale':'fixture only','basis':[{'path':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}]}
        attestation.write_text(json.dumps(data)); entry[arm]={'best_evidence':str(attestation),'recipe_sha256':recipe_sha}
    plan={'status':'REVIEWED_READY','models':[entry]}
    dispatch.validate_execution_evidence(plan)
    source.write_bytes(b'changed')
    with pytest.raises(ValueError, match='basis changed'):
        dispatch.validate_execution_evidence(plan)
    source.write_bytes(b'original evidence')
    p=Path(entry['candidate']['best_evidence']); bad=json.loads(p.read_text());bad['status']='CONFIGURED_ONLY';p.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match='not the reviewed best'):
        dispatch.validate_execution_evidence(plan)


def test_full_cpu_topology_accepts_bound_48_thread_recipe(tmp_path):
    import dataclasses
    native = dispatch.module('m4_best_evidence_native', dispatch.RUNNER)
    model = tmp_path/'model.gguf'
    evidence = tmp_path/'evidence.json'; evidence.write_text('{}')
    scenario = dataclasses.replace(native.SCENARIOS[0], name='fixture48', role='architect_general', model=model,
                                   device='none', n_gpu_layers=0, numa_nodes='all', cpu_affinity='0-95',
                                   threads=48, draft_model=None, request_endpoint='chat')
    recipe={'scenario':scenario.name,'recipe_sha256':dispatch.recipe_digest(scenario),
            'best_evidence':str(evidence),'best_evidence_sha256':hashlib.sha256(evidence.read_bytes()).hexdigest(),
            'draft_model_sha256':''}
    entry={'role':'architect_general','model_path':str(model),'context':8192,'additional_model_inputs':[],
           'baseline':{**recipe,'treatment':'default-off'},'candidate':{**recipe,'treatment':'srpf-cap512'}}
    assert len(dispatch.validate({'cpu':[{'role':'architect_general','model_path':str(model)}]},
                                 {'models':[entry]}, {scenario.name:scenario})) == 1
    bad=dataclasses.replace(scenario, threads=97)
    with pytest.raises(ValueError, match='invalid CPU recipe dimensions'):
        dispatch.validate({'cpu':[{'role':'architect_general','model_path':str(model)}]}, {'models':[entry]}, {bad.name:bad})
