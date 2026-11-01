"""Offline controls for terminal negative outcomes and attempt/source binding."""
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from completion_check import complete_verdict
from verdict_inputs import VERDICT_INPUTS

FIXTURE = ROOT / 'tests' / 'fixtures' / 'full-fail-mape'

def actual_pair():
    return (json.loads((FIXTURE / 'VERDICT.json').read_text()),
            json.loads((FIXTURE / 'RESULT.json').read_text()))

def protocol_source_hashes():
    manifest = json.loads((ROOT / 'CANDIDATE-MANIFEST.json').read_text())
    return manifest['protocol_hashes']

def bound_pair(v=None, run=None):
    actual_v, actual_run = actual_pair()
    v = copy.deepcopy(actual_v if v is None else v)
    run = copy.deepcopy(actual_run if run is None else run)
    manifest = json.loads((ROOT / 'CANDIDATE-MANIFEST.json').read_text())
    row_id = manifest['id']
    run_id = row_id + '-offline-attempt-0001'
    source_sha = manifest['source_code_manifest_sha256']
    candidate_sha = hashlib.sha256((ROOT / 'CANDIDATE-MANIFEST.json').read_bytes()).hexdigest()
    fixture_dir = ROOT / 'tests' / 'fixtures' / 'native-capture'
    input_hashes = {}
    for rel in VERDICT_INPUTS:
        source = fixture_dir / (('out/' + rel) if rel.startswith('sibling_') else rel)
        input_hashes[rel] = hashlib.sha256(source.read_bytes()).hexdigest()
    input_sha = input_hashes['run/pb_qcost_1.jsonl']
    input_path = str(ROOT / 'out' / 'attempts' / row_id / 'run' / 'pb_qcost_1.jsonl')
    verdict_path = str(ROOT / 'out' / 'attempts' / row_id / 'VERDICT.json')
    manifest['result_path'] = verdict_path
    protocols = protocol_source_hashes()
    metadata = {'row_id':row_id, 'run_id':run_id, 'attempt_id':run_id,
        'source_code_manifest_sha256':source_sha, 'candidate_manifest_sha256':candidate_sha,
        'input_sha256':input_sha, 'verdict_inputs_sha256':input_hashes, 'predeclaration_sha256':protocols['predeclaration_sha256'],
        'amendment_sha256':protocols['amendment_sha256'],
        'input_path':input_path,'verdict_path':verdict_path,'state':'COMPLETE'}
    v.update(metadata)
    v['input_path'] = input_path
    v_bytes = (json.dumps(v, indent=1, default=str) + '\n').encode()
    verdict_sha = hashlib.sha256(v_bytes).hexdigest()
    run.update({'status':'COMPLETE','partial':False,'exit_code':0,'cleanup_verified':True,
        'smoke':False,'protocol_requests':66,'coefficient_grade':'mechanical VERDICT.json',
        **metadata,'input_path':input_path,'verdict_path':verdict_path,
        'verdict_sha256':verdict_sha})
    result_sha = hashlib.sha256((json.dumps(run, indent=1, default=str) + '\n').encode()).hexdigest()
    attempt = {'row_id':row_id,'run_id':run_id,'attempt_id':run_id,
        'source_code_manifest_sha256':source_sha,'candidate_manifest_sha256':candidate_sha,
        'predeclaration_sha256':protocols['predeclaration_sha256'],
        'amendment_sha256':protocols['amendment_sha256'],
        'input_path':input_path,'verdict_path':verdict_path,'state':'COMPLETE',
        'input_sha256':input_sha,'verdict_sha256':verdict_sha,'result_sha256':result_sha,
        'finalization':{'input_sha256':input_sha,'verdict_inputs_sha256':input_hashes}}
    args = {'verdict_sha256':verdict_sha,'result_sha256':result_sha,'input_sha256':input_sha,
        'source_code_manifest_sha256':source_sha,'candidate_manifest_sha256':candidate_sha,
        'predeclaration_sha256':protocols['predeclaration_sha256'],
        'amendment_sha256':protocols['amendment_sha256'],
        'expected_input_path':input_path,'expected_verdict_path':verdict_path,
        'verdict_inputs_sha256':input_hashes}
    return v,run,attempt,manifest,args

def is_complete(v,run,attempt,manifest,args):
    return complete_verdict(v,run,attempt,manifest,**args)

def test_actual_fail_mape_fixture_is_complete_but_scientifically_negative_when_bound():
    actual_v, _ = actual_pair()
    assert actual_v['confirm_overall'] == 'FAIL_MAPE'
    assert actual_v['confirm']['4']['refit_request_heldout_mape_pct'] == 11.56
    assert actual_v['q_overall'] == 'PASS'
    v,run,attempt,manifest,args = bound_pair()
    assert is_complete(v,run,attempt,manifest,args)
    # Completion means the 66-request study terminated validly; the outcome remains a FAIL_MAPE.
    assert v['confirm_overall'] == 'FAIL_MAPE'

def test_unbound_retained_r2_fixture_cannot_complete_r3():
    v,run = actual_pair()
    _,_,attempt,manifest,args = bound_pair()
    assert manifest['id'] == 'codex-ni-pbqcost-confirm-q-r3-20261101'
    attempt['row_id'] = 'codex-ni-pbqcost-confirm-q-r2-20261030'
    assert not is_complete(v,run,attempt,manifest,args)

def test_cross_attempt_run_or_verdict_pairing_is_refused():
    v,run,attempt,manifest,args = bound_pair()
    assert is_complete(v,run,attempt,manifest,args)
    assert not is_complete(v,run,{**attempt,'state':'ACTIVE'},manifest,args)
    assert not is_complete(v,{**run,'run_id':run['run_id']+'-other'},attempt,manifest,args)
    assert not is_complete(v,{**run,'verdict_sha256':'0'*64},attempt,manifest,args)
    assert not is_complete(v,{**run,'input_sha256':'0'*64},attempt,manifest,args)
    assert not is_complete(v,run,{**attempt,'input_path':'/unrelated/input.jsonl'},manifest,args)
    assert not is_complete(v,run,attempt,{**manifest,'result_path':'/unrelated/VERDICT.json'},args)

def test_attempt_source_or_protocol_drift_is_refused():
    v,run,attempt,manifest,args = bound_pair()
    assert is_complete(v,run,attempt,manifest,args)
    assert not is_complete(v,run,{**attempt,'source_code_manifest_sha256':'0'*64},manifest,args)
    assert not is_complete(v,run,attempt,manifest,{**args,'predeclaration_sha256':'0'*64})
    assert not is_complete(v,run,attempt,manifest,{**args,'amendment_sha256':'0'*64})

def test_nested_producer_label_disagreement_is_refused():
    v,run,attempt,manifest,args = bound_pair()
    bad=copy.deepcopy(v);bad['confirm']['overall']='INCOMPLETE'
    assert not is_complete(bad,run,attempt,manifest,args)
    bad=copy.deepcopy(v);bad['q_axis']['overall']='FAIL'
    assert not is_complete(bad,run,attempt,manifest,args)
    bad=copy.deepcopy(v);bad['label']='PB-QCOST-1 confirm CONFIRMED; q axis PASS; grade UNCONTENDED'
    assert not is_complete(bad,run,attempt,manifest,args)
    bad=copy.deepcopy(v);bad['proof']['all_ok']=False
    assert not is_complete(bad,run,attempt,manifest,args)

def test_incomplete_and_invalid_producer_labels_fail_closed():
    v,run,attempt,manifest,args = bound_pair()
    for bad in ('INCOMPLETE','INVALID_PROOF','FAIL'):
        changed=copy.deepcopy(v);changed['confirm_overall']=bad
        assert not is_complete(changed,run,attempt,manifest,args)
    changed=copy.deepcopy(v);changed['phases_done']=[256,512]
    assert not is_complete(changed,run,attempt,manifest,args)
    for key,bad in (('partial',True),('exit_code',75),('cleanup_verified',False),
                    ('smoke',True),('protocol_requests',65),('coefficient_grade',None)):
        assert not is_complete(v,{**run,key:bad},attempt,manifest,args)
