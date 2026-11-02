import hashlib
import importlib.util
from pathlib import Path

MODULE = Path(__file__).parents[2] / 'scripts/champion/m4/resolve_scope.py'
spec = importlib.util.spec_from_file_location('m4_scope_binding', MODULE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture(tmp_path):
    (tmp_path / 'source').write_text('source')
    pin = hashlib.sha256(b'source').hexdigest()
    runtime = {'binary_family': 'llama.cpp', 'flags': {'spec': {'enabled': True}}}
    primary = {'launch': {'primary_roles': ['main'], 'requirements': {'model_path': '/models/m'}, 'runtime': runtime}}
    alias = {'launch': {'primary_roles': ['main'], 'requirements': {'model_path': '/models/m'},
                        'runtime': {'binary_family': 'llama.cpp', 'flags': {'spec': {'enabled': False}}}}}
    prior = {'source_artifacts': {'registry': {'path': 'source', 'sha256': pin}},
             'roles': {'main': {'serving': primary}, 'alias': {'serving': alias}}}
    registry = {'server_mode': {'main': {'model': '/models/m', 'shared_with': ['alias']}}}
    scope = {'gpu': [{'role': 'main', 'model_path': '/models/m'},
                     {'role': 'alias', 'model_path': '/models/m'}]}
    return scope, prior, registry


def test_alias_uses_physical_runtime(tmp_path):
    scope, prior, registry = fixture(tmp_path)
    got = module.resolve(tmp_path, scope, prior, registry)
    assert got['status'] == 'SOURCE_BOUND_ONLY'
    assert got['roles'][1]['primary'] == 'main'
    assert got['roles'][1]['primary_runtime']['flags']['spec']['enabled'] is True


def test_stale_source_and_scope_mismatch_refused(tmp_path):
    scope, prior, registry = fixture(tmp_path)
    (tmp_path / 'source').write_text('changed')
    scope['gpu'][1]['model_path'] = '/models/other'
    got = module.resolve(tmp_path, scope, prior, registry)
    assert got['status'] == 'REFUSED'
    assert any('source pin mismatch' in e for e in got['errors'])
    assert any('model conflicts' in e for e in got['errors'])


def test_alias_conflict_refused(tmp_path):
    scope, prior, registry = fixture(tmp_path)
    registry['server_mode']['main']['shared_with'] = []
    assert module.resolve(tmp_path, scope, prior, registry)['status'] == 'REFUSED'


def test_escaping_source_and_duplicate_refused(tmp_path):
    scope, prior, registry = fixture(tmp_path)
    prior['source_artifacts']['registry']['path'] = '../outside'
    scope['gpu'].append(scope['gpu'][0])
    got = module.resolve(tmp_path, scope, prior, registry)
    assert got['status'] == 'REFUSED'
    assert any('duplicate' in e for e in got['errors'])


def test_structured_model_path(tmp_path):
    scope, prior, registry = fixture(tmp_path)
    registry['server_mode']['main']['model'] = {'path': '/models/m', 'mmproj_path': '/models/projector'}
    got = module.resolve(tmp_path, scope, prior, registry)
    assert got['status'] == 'SOURCE_BOUND_ONLY'
    assert got['roles'][0]['primary_registry']['model']['mmproj_path'] == '/models/projector'
