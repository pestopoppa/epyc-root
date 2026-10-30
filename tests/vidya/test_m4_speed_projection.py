"""M4 speed readers: synthetic native receipts, no model or GPU."""
from __future__ import annotations
import dataclasses
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

VIDYA = Path(__file__).resolve().parents[2] / 'scripts' / 'vidya'
if str(VIDYA) not in sys.path:
    sys.path.insert(0, str(VIDYA))
from claim_tuple import ProjectionError  # noqa: E402
from adapters import m4_cpu_speed as cpu, m4_gpu_speed as gpu  # noqa: E402


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + '\n')


def cpu_receipt(tmp_path, monkeypatch):
    monkeypatch.setattr(cpu, 'ROOT', tmp_path.resolve())
    (tmp_path/'native').mkdir()
    for name in ('dispatch.py','native/k35_stack_context_matrix_runner.py','native/compare_v9_promotion_arms.py'):
        (tmp_path/name).write_text('fixture source')
    source_hashes={'producer_sha256':hashlib.sha256((tmp_path/'dispatch.py').read_bytes()).hexdigest(),'native_runner_sha256':hashlib.sha256((tmp_path/'native/k35_stack_context_matrix_runner.py').read_bytes()).hexdigest(),'native_comparator_sha256':hashlib.sha256((tmp_path/'native/compare_v9_promotion_arms.py').read_bytes()).hexdigest()}
    rows=[]
    recipe={'scenario':'fake','treatment':'fixture'}
    for arm in ('BASELINE','CANDIDATE'):
        for i in range(5):
            d=tmp_path/arm/str(i); d.mkdir(parents=True)
            prompt=d/'prompt.txt'; prompt.write_text('fixture prompt')
            ph=d/'prompt.sha256'; ph.write_text(hashlib.sha256(prompt.read_bytes()).hexdigest()+'\n')
            binary=str(d/'llama-server'); argv=['-m','/fixture/model.gguf']
            if arm=='CANDIDATE': argv += ['--prefill-order','srpf','--prefill-contend-cap','512']
            _write(d/'plan.json',{'binary':binary,'cells':[{'server_argv':argv}]})
            summary=d/'summary.json'
            _write(summary,{'status':'ok','results':[{'status':'ok','passed_min_completion':True,'scenario':'fake','nominal_context':2048,'decode_tps':100.0,'prompt_path':str(prompt),'prompt_sha256_path':str(ph),'cleanup':{'completed':True,'dead':True}}]})
            commit='c72ec82f5417bb2937310326120f149b665e8400' if arm=='BASELINE' else 'bc441f1a261766d11bfeff21668a1031c4dbf8cd'
            row={'measurement_id':f'{arm}-{i}','metric':'decode_tokens_per_s','value':100.0,'unit':'tokens_per_second','category':arm,'metric_direction':'higher_better','protocol_id':'','reps':1,'reps_basis':'one fresh-server scored process','role':'worker','model_path':'/fixture/model.gguf','recipe':recipe,'attestation_locator':str(summary),'attestation_sha256':hashlib.sha256(summary.read_bytes()).hexdigest(),'date':'2026-10-27','claim':'fixture','extra':{'binary':binary,'native_scenario':'fake','context':2048,'source_commit':commit,**source_hashes}}
            row['measurement_sha256']=cpu._sha(cpu._canonical(row)); rows.append(row)
    receipt=tmp_path/'throughput.json'
    _write(receipt,{'schema':cpu.SCHEMA,'quality_gate':'separate','role':'worker','model_path':'/fixture/model.gguf','baseline_recipe':recipe,'candidate_recipe':recipe,'belief_measurements':rows})
    return receipt


def test_cpu_projection_rechecks_native_source_and_refuses_tampering(tmp_path,monkeypatch):
    receipt=cpu_receipt(tmp_path,monkeypatch); rows=cpu.native_rows(receipt)
    assert len(rows)==10 and cpu.project(rows[0]).value==100.0
    Path(rows[0]['row']['attestation_locator']).write_text('{}')
    with pytest.raises(ProjectionError): cpu.project(rows[0])


def test_cpu_prompt_proof_refuses_changed_prompt(tmp_path,monkeypatch):
    receipt=cpu_receipt(tmp_path,monkeypatch); row=cpu.native_rows(receipt)[0]
    summary=json.loads(Path(row['row']['attestation_locator']).read_text())
    Path(summary['results'][0]['prompt_path']).write_text('changed')
    with pytest.raises(ProjectionError): cpu.project(row)


def test_gpu_projection_replays_native_metric_and_requires_cleanup(tmp_path,monkeypatch):
    native_path=Path('/mnt/raid0/llm/tmp/refactor-01a16fc3/m4-fold-gates/speed-gpu/native/server_np_sweep.py')
    spec=importlib.util.spec_from_file_location('m4_gpu_native_test',native_path)
    m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m)
    monkeypatch.setattr(gpu,'ROOT',tmp_path.resolve()); monkeypatch.setattr(gpu,'module',lambda:m)
    (tmp_path/'native').mkdir(); producer=tmp_path/'native/server_np_sweep.py'; producer.write_text('fixture source')
    req=tmp_path/'requests.jsonl'; maps=tmp_path/'maps.txt'; binary=tmp_path/'bin/llama-server'
    item=m.RequestResult(model='fixture',np_level=1,request_index=0,qid='q',suite='s',success=True,latency_ms=10,predicted_tokens=10,prompt_tokens=5,predicted_tps=10,predicted_ms=1000,stream_id=0)
    req.write_text(json.dumps(dataclasses.asdict(item))+'\n'); maps.write_text(f'0 0 0 0 0 {binary.parent}/libggml-cpu.so\n')
    (tmp_path/'events.jsonl').write_text(json.dumps({'event':'server_stopped','result':{'ps_verified_dead':True}})+'\n')
    command=[str(binary),'-m','/fixture','-c','65536','-np','1','--prefill-order','srpf','--prefill-contend-cap','512']
    cell=m.summarize_cell(model=m.ModelSpec(label='fixture',path=Path('/fixture')),np_level=1,results=[item],wall_s=1.0,ttft_ms=1.0,server_pid=123,server_command=command)
    extra={'context_size':65536,'np':1,'gpu_residency_during':[{'pid':123,'own_vram_bytes':1,'device_vram_bytes':2,'kfd_process_count':1}],'ggml_maps':str(maps),'binary':str(binary),'role':'fixture','source_commit':'bc441f1a261766d11bfeff21668a1031c4dbf8cd','producer_sha256':hashlib.sha256(producer.read_bytes()).hexdigest()}
    row={'measurement_id':'fixture','metric':'aggregate_decode_tokens_per_s','value':cell['aggregate_decode_tps'],'unit':'tokens_per_second','date':'2026-10-27','category':'CANDIDATE','claim':'fixture','metric_direction':'higher_better','protocol_id':'','reps':1,'reps_basis':'one fresh-server process','attestation_locator':str(req),'attestation_sha256':hashlib.sha256(req.read_bytes()).hexdigest(),'extra':extra}
    row['measurement_sha256']=gpu.sha(gpu.canonical(row)); cell['belief_measurements']=[row]
    cells=tmp_path/'cells.jsonl'; cells.write_text(json.dumps(cell)+'\n')
    assert gpu.project(gpu.native_rows(cells)[0]).value==10.0
    (tmp_path/'events.jsonl').write_text('{}\n')
    with pytest.raises(ProjectionError): gpu.project(gpu.native_rows(cells)[0])
