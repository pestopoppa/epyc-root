"""Synthetic schema controls; values here are not fleet measurements."""
import copy
import json

import pytest
import yaml

from public_benchmark_registration import (
    UniqueLoader, main, registration_fragment, validate_catalog,
)


def catalog():
    return {'schema_version': 1, 'axes': {'bfcl_v3': 'tool_use', 'bfcl_v4': 'tool_use'},
            'universal_keys': [], 'models': {'a': {'benchmarks': {'bfcl_v4': .8},
                                                 'absent_from_card': ['bfcl_v3']}}}


def result(key='bfcl_v3'):
    return {'model': 'a', 'benchmark_key': key, 'value': .5,
            'absent_from_card': key == 'bfcl_v3',
            'source': {'path': 'run/result.json', 'sha256': 'a' * 64}}


def test_separate_keys_preserve_vendor_score_and_input():
    c = catalog()
    before = copy.deepcopy(c)
    p = registration_fragment(c, [result(), result('bfcl_v4')])
    assert c == before
    assert p['public_benchmarks_fragment']['models']['a'] == {
        'local_benchmarks': {'bfcl_v3': .5, 'bfcl_v4': .5}, 'absent_from_card': ['bfcl_v3']}
    assert p['routing_prior_or_adoption'] is False


def test_absence_added_for_new_local_result():
    c = catalog()
    c['models']['a']['absent_from_card'] = []
    p = registration_fragment(c, [result()])
    assert p['public_benchmarks_fragment']['models']['a']['absent_from_card'] == ['bfcl_v3']


@pytest.mark.parametrize('change', [
    {'benchmark_key': 'tool_use'}, {'benchmark_key': 'bfcl'}, {'model': 'missing'},
    {'value': True}, {'value': float('nan')}, {'value': float('inf')},
    {'value': 1.1}, {'value': -.1}, {'source': {'path': 'unbound'}},
    {'absent_from_card': False}, {'absent_from_card': 1},
])
def test_rejects_invalid_or_ambiguous_registration(change):
    r = result()
    r.update(change)
    with pytest.raises(ValueError):
        registration_fragment(catalog(), [r])


def test_refuses_duplicates_and_overwrite():
    with pytest.raises(ValueError, match='duplicate'):
        registration_fragment(catalog(), [result(), result()])
    c = catalog()
    c['models']['a']['local_benchmarks'] = {'bfcl_v3': .7}
    with pytest.raises(ValueError, match='overwrite'):
        registration_fragment(c, [result()])


@pytest.mark.parametrize('defect', ['unknown', 'axis', 'contradiction', 'duplicate', 'bool', 'hidden_vendor'])
def test_catalog_controls(defect):
    c = catalog()
    r = c['models']['a']
    if defect == 'unknown':
        r['local_benchmarks'] = {'bfcl': .3}
    elif defect == 'axis':
        c['axes']['tool_use'] = 'tool_use'
    elif defect == 'contradiction':
        r['absent_from_card'].append('bfcl_v4')
    elif defect == 'duplicate':
        r['absent_from_card'] *= 2
    elif defect == 'hidden_vendor':
        r['benchmarks']['bfcl_v4'] = float('nan')
        r['local_benchmarks'] = {'bfcl_v4': .5}
    else:
        r['benchmarks']['bfcl_v4'] = True
    with pytest.raises(ValueError):
        validate_catalog(c)


def test_yaml_duplicate_keys_refused():
    with pytest.raises(ValueError, match='duplicate YAML key'):
        yaml.load('bfcl_v3: 0.4\nbfcl_v3: 0.8\n', Loader=UniqueLoader)


def test_cli_pins_inputs_and_protects_catalog(tmp_path, capsys):
    c, r, out = [tmp_path / name for name in ['catalog.yaml', 'results.json', 'out.json']]
    c.write_text(yaml.safe_dump(catalog()))
    r.write_text(json.dumps([result()]))
    original = c.read_bytes()
    assert main(['--catalog', str(c)]) == 0
    assert 'PASS' in capsys.readouterr().out
    assert main(['--catalog', str(c), '--results', str(r), '--out', str(out)]) == 0
    p = json.loads(out.read_text())
    assert len(p['catalog_sha256']) == len(p['results_sha256']) == 64
    assert c.read_bytes() == original
    with pytest.raises(SystemExit):
        main(['--catalog', str(c), '--results', str(r), '--out', str(c)])
