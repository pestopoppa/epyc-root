"""Exact operational identities; matching is independent of verifier outcomes."""
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts' / 'vidya'))
import actor_wire_subject as subject
from adapters import autokernel_actor_wire as wire
from claim_tuple import ProjectionError
from test_autokernel_actor_wire_adapter import build, reseal_write


def matrix(path):
    return wire.native_rows(path)[0]


def reseal_subject(value):
    value['subject_sha256'] = wire.digest({k:v for k,v in value.items() if k != 'subject_sha256'})
    return value


def test_exact_identity_and_no_inference_applicability(tmp_path):
    path, record = build(tmp_path, verdicts=('PASS','PASS','PASS'))
    native = matrix(path); result = subject.subject_for_native(native)
    assert subject.matches_native(result, native)
    assert result['producer'] == record['producer'] and result['request'] == record['request']
    assert set(result) == {'schema','producer','request','seat_digest','subject_sha256'}
    # Consumer-scoped since VB-AK-WIRE-PLANNER-TIER (e9f943781): the tuple names its consumer,
    # but must still carry NO inference applicability (model/device/backend) -- same contract
    # as test_autokernel_actor_wire_adapter.
    applicability = wire.project(native).applicability
    assert applicability == {'consumer': wire.PLANNER_CONSUMER, 'scope_basis': 'native'}
    assert not {'model_file', 'model_sha256', 'device', 'backend'} & set(applicability)
    result['request']['suite']['new.py'] = 'f'*64
    assert record['request']['suite'] != result['request']['suite']  # no mutable alias


@pytest.mark.parametrize('field', ['repo','commit','module'])
def test_producer_change_is_miss(tmp_path,field):
    path, _ = build(tmp_path); native = matrix(path); target = subject.subject_for_native(native)
    target['producer'][field] += '-other';reseal_subject(target)
    assert not subject.matches_native(target,native)


def test_suite_change_is_miss(tmp_path):
    path,_ = build(tmp_path);native=matrix(path);target=subject.subject_for_native(native)
    target['request']['suite']['actors.py']='d'*64;reseal_subject(target)
    assert not subject.matches_native(target,native)


@pytest.mark.parametrize('field,value', [('timeout_s',30),('launch_config',{'x':2}),('client_sha256','e'*64),('backend',{'kind':'codex','model':'changed'})])
def test_seat_configuration_change_is_miss(tmp_path,field,value):
    path,_=build(tmp_path);native=matrix(path);target=subject.subject_for_native(native)
    seats=target['request']['seats'];seats[0][field]=value
    seats.sort(key=wire.digest);target['request']['actor_config_digest']=wire.digest(seats);reseal_subject(target)
    assert not subject.matches_native(target,native)


def test_matrix_seat_and_different_seats_do_not_match(tmp_path):
    path,_=build(tmp_path,verdicts=('PASS','PASS','PASS'));rows=wire.native_rows(path)
    a=next(r for r in rows if r.get('index')==0);b=next(r for r in rows if r.get('index')==1)
    target=subject.subject_for_native(a)
    assert subject.matches_native(target,a)
    assert not subject.matches_native(target,b)
    assert not subject.matches_native(target,rows[0])
    # Native vs mocked check has the same operational subject, remains separate evidence.
    same_seat=[r for r in rows if r.get('index')==0]
    assert subject.subject_for_native(same_seat[0])==subject.subject_for_native(same_seat[1])
    assert wire.project(same_seat[0]).measurement_id != wire.project(same_seat[1]).measurement_id


def test_identity_does_not_filter_failed_aborted_or_unvisited(tmp_path):
    path,record=build(tmp_path,verdicts=('PASS',),abort='stopped')
    native=matrix(path);target=subject.subject_for_native(native)
    assert wire.project(native).value==0 and record['unvisited']
    assert subject.matches_native(target,native)
    # Same captured request/producer can have a different run outcome.
    other=tmp_path/'other';other.mkdir();path2,_=build(other,verdicts=('PASS','PASS','PASS'))
    assert subject.matches_native(target,matrix(path2))


@pytest.mark.parametrize('mutation', ['scope','digest','config','seat','nonfinite'])
def test_malformed_subject_refused(tmp_path,mutation):
    path,_=build(tmp_path);target=subject.subject_for_native(matrix(path))
    if mutation=='scope': target['model_file']='invented.gguf'
    elif mutation=='digest': target['subject_sha256']='0'*64
    elif mutation=='config': target['request']['actor_config_digest']='0'*64;reseal_subject(target)
    elif mutation=='seat': target['seat_digest']='0'*64;reseal_subject(target)
    else: target['request']['seats'][0]['timeout_s']=float('nan')
    with pytest.raises(ProjectionError):subject.matches_native(target,matrix(path))


def test_mutated_native_or_changed_original_file_refused(tmp_path):
    path,record=build(tmp_path);native=matrix(path);target=subject.subject_for_native(native)
    forged=copy.deepcopy(native);forged['record']['producer']['repo']='forged'
    with pytest.raises(ProjectionError):subject.subject_for_native(forged)
    record['producer']['commit']='b'*40;reseal_write(path,record)
    with pytest.raises(ProjectionError):subject.matches_native(target,native)
