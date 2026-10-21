"""Offhost-only conformance leaf; synthetic fixtures do not measure a model."""
import copy
import pytest
from ifbench_fixture import exact_response_join, export_runner_responses, manifest, validate_corpus, nltk_seed_manifest, NLTK_RESOURCES


def population():
    rows = [{'key': i, 'prompt': f'precise prompt {i}', 'instruction_id_list': [f'c{i % 58}'], 'kwargs': [{}]} for i in range(300)]
    for row in rows[:44]:
        row['instruction_id_list'].append('c0');row['kwargs'].append({})
    return rows


def test_full_population_and_preregistered_identity():
    rows = population();validate_corpus(rows);doc = manifest(rows)
    assert len(doc['suites']['ifbench_candidate']) == 300
    assert sum(doc['preregistered']['constraint_counts'].values()) == 344
    assert len(doc['preregistered']['constraint_counts']) == 58
    assert len(doc['preregistered']['prompt_sha256_by_key']) == 300
    assert doc['preregistered']['routing_or_adoption'] is False


def test_exact_join_preserves_order_and_empty_response():
    rows = population();responses = [{'prompt': r['prompt'], 'response': ''} for r in reversed(rows)]
    joined = exact_response_join(rows,responses)
    assert [r['prompt'] for r in joined] == [r['prompt'] for r in rows]
    assert joined[0]['response'] == ''


@pytest.mark.parametrize('defect',['missing','extra','duplicate','normalized','nonstr'])
def test_join_refuses_all_coverage_defects(defect):
    rows=population();responses=[{'prompt':r['prompt'],'response':'answer'} for r in rows]
    if defect=='missing':responses.pop()
    elif defect=='extra':responses.append({'prompt':'extra','response':'x'})
    elif defect=='duplicate':responses[-1]=responses[0]
    elif defect=='normalized':responses[0]['prompt']+=' '
    else:responses[0]['response']=None
    with pytest.raises(ValueError):exact_response_join(rows,responses)


def test_runner_export_requires_all_exact_ids():
    rows=population();results={str(r['key']):{'response':'x'} for r in rows}
    assert len(export_runner_responses(rows,results)) == 300
    results.pop('299')
    with pytest.raises(ValueError):export_runner_responses(rows,results)


def test_corpus_refuses_duplicate_keys_and_constraint_drift():
    rows=population();rows[0]['key']=rows[1]['key']
    with pytest.raises(ValueError):validate_corpus(rows)
    rows=population();rows[0]['kwargs']=[]
    with pytest.raises(ValueError):validate_corpus(rows)


def test_seed_requires_all_four_resources_and_refuses_symlinks(tmp_path):
    with pytest.raises(ValueError):nltk_seed_manifest(tmp_path)
    for r in NLTK_RESOURCES:(tmp_path/r).mkdir(parents=True)
    (tmp_path/'tokenizers/punkt/model').write_bytes(b'pinned')
    assert nltk_seed_manifest(tmp_path)['files']['tokenizers/punkt/model']['bytes']==6
    (tmp_path/'link').symlink_to(tmp_path/'tokenizers/punkt/model')
    with pytest.raises(ValueError):nltk_seed_manifest(tmp_path)
