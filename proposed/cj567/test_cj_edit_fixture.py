"""Offhost-only fixture conformance; no models or external source execution."""
import ast
import difflib
import hashlib
import pytest
from cj_edit_fixture import fixture, exact_formatted_match, SOURCE_FUNCTION, MUTATIONS, HIDDEN_TEST


def test_known_inverse_and_mutated_sources_are_distinct():
    doc=fixture()
    assert len(doc['inverse_mutation'])==4
    for row in doc['inverse_mutation']:
        assert row['original_sha256']==hashlib.sha256(row['expected'].encode()).hexdigest()
        assert row['original_sha256']!=row['mutated_sha256']
        assert exact_formatted_match(row['expected'],SOURCE_FUNCTION)


def test_anti_apply_records_diff_old_to_mutated_new():
    for row,mutation in zip(fixture()['anti_apply'],MUTATIONS):
        before=SOURCE_FUNCTION.replace('sum(values) / len(values)',mutation[1])
        expected=''.join(difflib.unified_diff(SOURCE_FUNCTION.splitlines(True),before.splitlines(True),fromfile='old.py',tofile='new.py'))
        assert row['diff']==expected
        assert row['mutated_sha256']==hashlib.sha256(before.encode()).hexdigest()


def test_paired_instructions_share_oracle_and_hide_assertions():
    rows=fixture()['suites']['cj7_descriptive_lazy_candidate']
    assert len(rows)==8
    for i in range(0,8,2):
        a,b=rows[i:i+2]
        assert a['pair_id']==b['pair_id']
        assert {a['instruction_kind'],b['instruction_kind']}=={'descriptive','lazy'}
        assert a['scoring_config']==b['scoring_config']
        assert a['scoring_method']=='code_execution'
        assert 'def check' not in a['prompt'] and 'assert candidate' not in b['prompt']
        assert a['expected']==b['expected']==SOURCE_FUNCTION


def test_formatter_accepts_layout_and_refuses_wrong_or_invalid_code():
    assert exact_formatted_match('def _mean(values:list[float])->float:\n return sum(values)/len(values)',SOURCE_FUNCTION)
    for _,expr,_,_ in MUTATIONS:
        assert not exact_formatted_match(SOURCE_FUNCTION.replace('sum(values) / len(values)',expr),SOURCE_FUNCTION)
    assert not exact_formatted_match('def ???',SOURCE_FUNCTION)


def test_hidden_execution_uses_existing_functional_oracle():
    # Existing canonical scorer is deliberately reused rather than rebuilding isolation.
    from code_exec_scorer import score_functional
    assert score_functional(SOURCE_FUNCTION,HIDDEN_TEST,'_mean',timeout=2)
    for _,expr,_,_ in MUTATIONS:
        assert not score_functional(SOURCE_FUNCTION.replace('sum(values) / len(values)',expr),HIDDEN_TEST,'_mean',timeout=2)
