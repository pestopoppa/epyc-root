"""Offhost report-contract tests; synthetic oracle vectors are not observations."""
import copy
import pytest
from cj_candidate_report import build_report


def document():
    return {'benchmark_key':'candidate_binary','declared_fleet':['a','b','missing'],
            'sharpest_pair':['a','b'],'oracle_identity':{'name':'synthetic fixture'},
            'source_run_identity':{'kind':'authored fixture'},
            'arms':{'a':[{'question_id':'1','benchmark_key':'candidate_binary','correct':True,'perfect':True,'score':1},
                         {'question_id':'2','benchmark_key':'candidate_binary','correct':False,'perfect':False,'score':0}],
                    'b':[{'question_id':'1','benchmark_key':'candidate_binary','correct':True,'perfect':True,'score':1},
                         {'question_id':'2','benchmark_key':'candidate_binary','correct':True,'perfect':True,'score':1}]}}


def compare(a,b,la,lb,key):
    assert la=='a' and lb=='b' and key=='candidate_binary'
    return {'shared_qids':len(a),'p_value_two_sided':1.0,'same_correct':1,'same_wrong':0,
            'a_correct_b_wrong':0,'a_wrong_b_correct':1}


def test_saturation_pair_range_and_missing_fleet_disclosure():
    r=build_report(document(),compare)
    assert r['both_perfect_fraction']==0.5 and r['available_arm_range_pp']==50
    assert r['fleet_range_pp'] is None and r['missing_fleet_arms']==['missing']
    assert not r['routing_prior_or_adoption'] and r['benchmark_key']=='candidate_binary'


@pytest.mark.parametrize('defect',['key','duplicate','missing','score','perfect','bool'])
def test_refuses_incomparable_oracle_vectors(defect):
    d=document();row=d['arms']['a'][0]
    if defect=='key':row['benchmark_key']='other'
    elif defect=='duplicate':d['arms']['a'][1]['question_id']='1'
    elif defect=='missing':d['arms']['b'].pop()
    elif defect=='score':row['score']=float('nan')
    elif defect=='perfect':row['score']=0.9
    else:row['correct']=1
    with pytest.raises(ValueError):build_report(d,compare)


def test_reuses_canonical_paired_statistics_offhost():
    # The native recipe supplies the existing pinned orchestrator tree.
    from scripts.autopilot.paired_stats import QuestionOutcome,mcnemar_from_vectors
    from dataclasses import asdict
    def real(a,b,la,lb,key):
        vectors=lambda rows:{qid:QuestionOutcome(qid,key,r['correct'],0) for qid,r in rows.items()}
        return asdict(mcnemar_from_vectors(vectors(a),vectors(b),la,lb))
    r=build_report(document(),real)
    assert r['paired_statistics']['shared_qids']==2
    assert r['paired_statistics']['a_wrong_b_correct']==1
    assert r['paired_statistics']['p_value_two_sided']==1.0
