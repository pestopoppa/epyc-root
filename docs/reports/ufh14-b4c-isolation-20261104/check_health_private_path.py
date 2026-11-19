#!/usr/bin/env python3
"""Exercise AST-extracted native health resolution with fake records/probes only."""
import ast
import asyncio
import builtins
import difflib
import hashlib
import json
import logging
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

BASE = Path('/mnt/raid0/llm/tmp/agentic-serving-harness-fixes')
PACKET = BASE / 'prefix-cpu-packet-20261104'
SOURCE = BASE / 'gs-app-impact-source'
FILE = SOURCE / 'src/api/routes/health.py'
OLD = FILE.read_text()
needle = '    Path(__file__).resolve().parents[3] / "orchestration" / "derived" / "stack_priors.yaml"'
replacement = '''    Path(
        os.environ.get("ORCHESTRATOR_PATHS_STACK_PRIORS_PATH")
        or str(Path(__file__).resolve().parents[3] / "orchestration" / "derived" / "stack_priors.yaml")
    )'''
assert OLD.count(needle) == 1
NEW = OLD.replace('import logging\n', 'import logging\nimport os\n').replace(needle, replacement)
PATCH = PACKET / 'health-private-path.proposed.patch'
PATCH.write_text(''.join(difflib.unified_diff(OLD.splitlines(True), NEW.splitlines(True), fromfile='a/src/api/routes/health.py', tofile='b/src/api/routes/health.py')))
NAMES = {'_DEFAULT_STACK_PRIORS_PATH', '_RUNTIME_SELECTED_ROLE_ALIASES', '_first_backend_url', '_stack_prior_backend_urls', '_runtime_selected_backend_urls', '_probe_core_backends'}
selected = []
for node in ast.parse(NEW).body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in NAMES:
        selected.append(node)
    elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in NAMES for t in node.targets):
        selected.append(node)
assert len(selected) == len(NAMES)
CODE = compile(ast.Module(body=selected, type_ignores=[]), '<AST-native-health-proposed>', 'exec')
DEFAULT = SOURCE / 'orchestration/derived/stack_priors.yaml'
results = []


def exercise(name, env, expected, *, explicit=None, runtime=False):
    calls = []
    probes = []
    selected_servers = [{'port': 19642, 'roles': ['frontdoor']}] if runtime else []
    fake_module = SimpleNamespace(read_runtime_stack_selected_servers=lambda: selected_servers)
    def safe_import(module, *args, **kwargs):
        assert module == 'scripts.server.runtime_facts_manifest', module
        return fake_module
    def records(path):
        assert isinstance(path, Path), type(path)
        calls.append(str(path))
        return {'frontdoor': {'serving': {'endpoint': 'http://owned-fixture.invalid:19642', 'ports': [19642]}}}
    async def fake_probe(url):
        probes.append(url)
        return {'ok': True, 'url': url, 'fixture': True}
    scope = {
        '__file__': str(FILE), '__builtins__': dict(vars(builtins), __import__=safe_import),
        'os': SimpleNamespace(environ=env), 'Path': Path, 'Any': Any, 'asyncio': asyncio,
        'logger': logging.getLogger('health-path-test'), 'live_stack_role_records': records,
        'stack_prior_serving': lambda record: record['serving'],
        'stack_prior_serving_ports': lambda serving: serving['ports'],
        '_probe_backend': fake_probe, '_fallback_backend_urls': lambda: {},
        'classify_exception': lambda exc: ('unexpected', str(exc)),
    }
    exec(CODE, scope)
    kwargs = {} if explicit is None else {'stack_priors_path': explicit}
    answer = asyncio.run(scope['_probe_core_backends'](**kwargs))
    assert calls == [str(expected)], (name, calls, expected)
    assert len(probes) == 1 and answer['frontdoor']['ok']
    assert scope['_stack_prior_backend_urls'].__defaults__ == (scope['_DEFAULT_STACK_PRIORS_PATH'],)
    assert scope['_runtime_selected_backend_urls'].__defaults__ == (scope['_DEFAULT_STACK_PRIORS_PATH'],)
    results.append({'name': name, 'passed': True, 'resolved_path': calls[0], 'route': 'runtime_selected' if runtime else 'stack_prior', 'fake_probe_calls': len(probes)})


exercise('unset_preserves_checkout_default', {}, DEFAULT)
exercise('empty_preserves_checkout_default', {'ORCHESTRATOR_PATHS_STACK_PRIORS_PATH': ''}, DEFAULT)
private = PACKET / 'private/stack_priors.yaml'
exercise('absolute_private_override', {'ORCHESTRATOR_PATHS_STACK_PRIORS_PATH': str(private)}, private)
exercise('private_override_runtime_selected_branch', {'ORCHESTRATOR_PATHS_STACK_PRIORS_PATH': str(private)}, private, runtime=True)
exercise('unset_runtime_selected_preserves_default', {}, DEFAULT, runtime=True)
exercise('spaces_unicode_path_parsed', {'ORCHESTRATOR_PATHS_STACK_PRIORS_PATH': '/private path/δοκιμή.yaml'}, Path('/private path/δοκιμή.yaml'))
exercise('relative_path_semantics_preserved', {'ORCHESTRATOR_PATHS_STACK_PRIORS_PATH': 'private/stack_priors.yaml'}, Path('private/stack_priors.yaml'))
exercise('explicit_parameter_overrides_environment', {'ORCHESTRATOR_PATHS_STACK_PRIORS_PATH': str(private)}, Path('/explicit/priors.yaml'), explicit=Path('/explicit/priors.yaml'))
assert FILE.read_text() == OLD
clean = not subprocess.check_output(['git', '-C', str(SOURCE), 'status', '--porcelain'], text=True).strip()
assert clean
report = {
    'schema': 'epyc.health-private-path-tests.v1', 'passed': True, 'tests': results,
    'source_commit': subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip(),
    'source_clean': clean, 'maintained_source_edits': False, 'application_imports': False,
    'network_calls': 0, 'inference': False, 'patch': str(PATCH),
    'patch_sha256': hashlib.sha256(PATCH.read_bytes()).hexdigest(),
    'test_script': str(Path(__file__).resolve()),
    'scope': 'Exact AST-extracted native _probe_core_backends and both native URL resolvers compiled from proposed source; fake native records, runtime manifest reader and backend probes. No copied checkout or application imports.',
    'limits': ['Tests isolate path resolution; no live HTTP, model server or full API integration.', 'Override is captured at module import, matching existing default-argument behavior.', 'Relative overrides retain pathlib semantics; set an absolute private path before application import.'],
    'change': 'Existing environment override becomes effective for health defaults; unset and empty retain original checkout default.',
}
output = BASE / 'health-patch-tests-20261104.json'
output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'artifact': str(output), 'passed': len(results), 'source_clean': clean}))
