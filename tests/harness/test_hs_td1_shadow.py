"""Shadow classification against the existing native prepared-action API; no inference."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.harness.hs_td1_shadow import classify, summarize


@pytest.fixture(scope='module')
def api():
    root = Path(os.environ.get('EPYC_ORCHESTRATOR_REPO', '/mnt/raid0/llm/epyc-orchestrator'))
    spec = importlib.util.spec_from_file_location('td1_shadow_native_api', root / 'src/typed_decisions/prepared_action.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def observation():
    return {'schema_version': 'hs_td1.dispatch_observation.v1', 'phase': 'pre_dispatch',
            'session_id': 's', 'turn_id': 'u', 'request': 'Read README', 'context': 'Local repo',
            'captured_at': '2026-11-19T10:00:00Z',
            'harness_decision': {'kind': 'observed', 'decision': 'permissive',
                                 'session_id': 's', 'turn_id': 'u', 'native_event_id': 'event-1'}}


def response(risk='low', intent='read', confidence=.9):
    return {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(
        {'risk': risk, 'intent': intent, 'confidence': confidence})}}]}


@pytest.mark.parametrize('risk,intent,agreement', [('low', 'read', True),
                                                  ('high', 'read', False),
                                                  ('medium', 'external', False)])
def test_policy_join_native_receipt_and_blind_model_input(api, risk, intent, agreement):
    row = observation()
    def judge(request):
        assert json.loads(request['messages'][1]['content']) == {
            'request': row['request'], 'context': row['context']}
        return response(risk, intent)
    result = classify(row, api=api, judge=judge, model='worker')
    assert result['agreement'] is agreement
    assert result['judgment']['confidence'] == .9
    assert result['observation'] == row
    receipt = result['receipt']
    assert receipt['schema_version'] == 'decision_receipt.v1'
    assert receipt['selected_id'] == f'{risk}:{intent}'
    assert len(receipt['offered_choices']) == 12
    assert receipt['resolved_model'] is None
    assert receipt['executed_arguments'] is None
    assert result['gate'] is False


@pytest.mark.parametrize('change', [
    {'phase': 'post_dispatch'}, {'request': ''}, {'context': None},
    {'harness_decision': {'kind': 'authored'}},
    {'harness_decision': {**observation()['harness_decision'], 'turn_id': 'other'}},
    {'harness_decision': {**observation()['harness_decision'], 'decision': 'unknown'}},
    {'harness_decision': {**observation()['harness_decision'], 'native_event_id': ''}},
])
def test_invalid_observation_never_enters_inference(api, change):
    result = classify(observation() | change, api=api,
                      judge=lambda _: pytest.fail('invalid observation called model'), model='worker')
    assert result['status'] == 'unknown'
    assert result['agreement'] is None


@pytest.mark.parametrize('raw', [response(risk='critical'), response(confidence=True),
                                response(confidence=float('nan')), {},
                                '{"choices":[],"choices":[]}',
                                {'choices': [{'finish_reason': 'length'}]}])
def test_invalid_response_stays_unknown(api, raw):
    result = classify(observation(), api=api, judge=lambda _: raw, model='worker')
    assert result['status'] == 'unknown'
    assert result['response'] == raw
    assert result['judgment'] is None and result['agreement'] is None


def test_timeout_mutation_and_expiration(api):
    def timeout(_):
        raise TimeoutError('worker timeout')
    assert classify(observation(), api=api, judge=timeout, model='worker')['status'] == 'unknown'
    row = observation()
    def mutate(_):
        row['harness_decision']['decision'] = 'restrictive'
        return response()
    result = classify(row, api=api, judge=mutate, model='worker')
    assert result['receipt']['validation_result'] == 'stale'
    assert result['agreement'] is None
    result = classify(observation(), api=api, judge=lambda _: response(), model='worker', ttl_s=-1)
    assert result['receipt']['validation_result'] == 'expired'
    assert result['status'] == 'unknown'


def test_denominators_and_confidence_per_turn(api):
    first = classify(observation(), api=api, judge=lambda _: response('high'), model='worker')
    second = classify(observation() | {'turn_id': 'other'}, api=api,
                      judge=lambda _: pytest.fail('wrong policy join'), model='worker')
    summary = summarize([first, second], expected=3)
    assert (summary['valid'], summary['unknown'], summary['agreements']) == (1, 2, 0)
    assert summary['confidence_by_turn'][0]['agreement'] is False
    assert summary['mean_confidence_valid'] == .9
    assert summary['all_attempt_elapsed_ms'] == first['elapsed_ms'] + second['elapsed_ms']
    with pytest.raises(ValueError, match='duplicate'):
        summarize([first, first], 2)
    assert summarize([], 2)['mean_confidence_valid'] is None


def test_cli_requires_keeper_before_network(tmp_path):
    env = dict(os.environ)
    env.pop('FILLER_ID', None)
    result = subprocess.run([sys.executable, 'scripts/harness/hs_td1_shadow.py',
                             '--orchestrator-repo', str(tmp_path), '--observations', '/missing',
                             '--output', str(tmp_path / 'out'), '--endpoint', 'http://invalid',
                             '--model', 'worker'], env=env, capture_output=True, text=True)
    assert result.returncode == 2 and 'keeper execution required' in result.stderr
    assert not (tmp_path / 'out').exists()


def test_cli_flushes_private_partial_output_and_refuses_duplicate(api, tmp_path, monkeypatch):
    from scripts.harness import hs_td1_shadow as shadow
    from io import BytesIO
    source, output = tmp_path / 'inputs.jsonl', tmp_path / 'outputs.jsonl'
    source.write_text((json.dumps(observation()) + '\n') * 2)
    monkeypatch.setenv('FILLER_ID', 'test-only')
    monkeypatch.delenv('FILLER_STOPFILE', raising=False)
    monkeypatch.delenv('FILLER_DEADLINE', raising=False)
    monkeypatch.setattr(shadow.importlib, 'import_module', lambda _: api)
    calls = []
    def worker(request, timeout):
        calls.append(request)
        return BytesIO(json.dumps(response()).encode())
    monkeypatch.setattr(shadow.urllib.request, 'urlopen', worker)
    monkeypatch.setattr(sys, 'argv', ['shadow', '--orchestrator-repo', str(tmp_path),
        '--observations', str(source), '--output', str(output),
        '--endpoint', 'http://mock', '--model', 'worker'])
    with pytest.raises(ValueError, match='duplicate turn'):
        shadow.main()
    assert len(calls) == 1
    assert json.loads(output.read_text())['status'] == 'ok'
    assert output.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        shadow.main()
    assert len(calls) == 1
