"""Parser checks use synthetic data and do not demonstrate planner wiring."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/benchmark/m4_cpu_ownership'))
import planning_canary as canary


def native_fixture():
    result={'loop':'A','status':'PASS','known_line':True,'guard_refusal':True,
            'canonical_ledger_unchanged':True,'telemetry_unchanged':True}
    summary={'belief_status':'ready','section_bytes':200,'prior_rows':1,'tried_index_count':1,
             'known_hits':{canary.KNOWN:{'in_belief_section':True,'in_already_tried_window':True}}}
    belief=f'{canary.KNOWN} measured_null -1.10%'
    prompt=f'## Already tried\n{canary.KNOWN}'
    return result,summary,belief,prompt


def test_native_output_shape_control_only():
    canary.verify_native_result(*native_fixture())


def test_native_guard_failure_does_not_become_a_guard_pass():
    result,summary,belief,prompt=native_fixture()
    result.update(status='FAIL',guard_refusal=False)
    canary.verify_native_result(result,summary,belief,prompt)
    assert result['status']=='FAIL' and not result['guard_refusal']


@pytest.mark.parametrize('defect',['unknown','no_guard','no_history','invented_marker','forged_hit'])
def test_rejects_invalid_native_output(defect):
    result,summary,belief,prompt=native_fixture()
    if defect=='unknown': result['status']='UNKNOWN'
    if defect=='no_guard': result['guard_refusal']=False
    if defect=='no_history': prompt='## Other\n'+canary.KNOWN
    if defect=='invented_marker': belief='plan says pass'
    if defect=='forged_hit': summary['known_hits'][canary.KNOWN]['in_already_tried_window']=False
    with pytest.raises(ValueError): canary.verify_native_result(result,summary,belief,prompt)
