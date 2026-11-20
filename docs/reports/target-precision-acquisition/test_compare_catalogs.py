import pytest
from compare_catalogs import compare, merge_shards


def test_split_and_unsplit_catalogs_match_without_claiming_causal_identity():
    result = compare({'bf16': [{'embed': [128, 256]}, {'head': [128, 256]}],
                      'q4': [{'head': [128, 256], 'embed': [128, 256]}]})
    assert result['structural_correspondence'] is True
    assert result['tensor_counts'] == {'bf16': 2, 'q4': 2}
    assert result['causal_precision_gate'] == 'UNRESOLVED'


def test_extra_mtp_head_and_changed_shape_are_retained():
    result = compare({'bf16': [{'embed': [128, 256], 'norm': [256]}],
                      'q4': [{'embed': [128, 512], 'mtp': [256]}]})
    assert result['structural_correspondence'] is False
    assert result['differences']['q4'] == {
        'missing': ['norm'], 'extra': ['mtp'],
        'shape_mismatch': {'embed': {'reference': [128, 256], 'candidate': [128, 512]}}}


def test_duplicate_tensor_across_shards_is_refused_even_when_shapes_match():
    with pytest.raises(ValueError, match='duplicate tensor'):
        merge_shards([{'embed': [128, 256]}, {'embed': [128, 256]}])


@pytest.mark.parametrize('shards', [[], [{}], [{'x': []}], [{'x': [0]}], [{'x': [True]}], [{'': [1]}]])
def test_incomplete_or_invalid_catalog_cannot_pass(shards):
    with pytest.raises(ValueError):
        merge_shards(shards)


def test_single_arm_cannot_claim_correspondence():
    with pytest.raises(ValueError):
        compare({'bf16': [{'x': [1]}]})


from compare_catalogs import validate_split_set


def test_missing_split_and_repeated_split_refused():
    a = {'split_count': 2, 'split_no': 0, 'split_tensors': 3, 'catalog_tensor_count': 2}
    b = dict(a, split_no=1, catalog_tensor_count=1)
    validate_split_set([a, b])
    for records in ([a], [a, a], [a, dict(b, split_tensors=4)], [a, dict(b, catalog_tensor_count=2)]):
        with pytest.raises(ValueError):
            validate_split_set(records)


def test_multiple_unsplit_files_refused():
    a = {'split_count': None}
    validate_split_set([a])
    with pytest.raises(ValueError):
        validate_split_set([a, a])
