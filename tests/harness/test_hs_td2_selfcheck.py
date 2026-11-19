"""Native-capture consumer controls against the real HS-TD-4 implementation."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.harness.hs_td2_selfcheck import selfcheck


@pytest.fixture(scope='module')
def api():
    root = Path(os.environ.get('EPYC_ORCHESTRATOR_REPO', '/mnt/raid0/llm/epyc-orchestrator'))
    spec = importlib.util.spec_from_file_location('hs_td4_test_api', root / 'src/typed_decisions/prepared_action.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def capture():
    return {'schema_version': 'hs_td2.turn_capture.v1', 'status': 'captured',
            'session_id': 's', 'turn_id': 'a', 'parent_id': 'u', 'reference_satisfied': None,
            'messages': [
                {'info': {'id': 'u', 'sessionID': 's', 'role': 'user'}, 'parts': []},
                {'info': {'id': 'a', 'sessionID': 's', 'parentID': 'u', 'role': 'assistant',
                          'time': {'completed': 3}}, 'parts': [{'type': 'text', 'text': '42'}]}]}


def response(satisfied=True, confidence=.9):
    return {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(
        {'satisfied': satisfied, 'confidence': confidence, 'reason': 'observed'})}}]}


@pytest.mark.parametrize('satisfied', [True, False])
def test_native_receipt_and_confidence_without_execution(api, satisfied):
    row = capture()
    result = selfcheck(row, api=api, judge=lambda _: response(satisfied), model='worker')
    receipt = result['receipt']
    assert result['capture_sha256'] == api.fingerprint(row)
    assert result['judgment']['confidence'] == .9
    assert receipt['schema_version'] == 'decision_receipt.v1'
    assert receipt['selected_id'] == ('satisfied' if satisfied else 'unsatisfied')
    assert receipt['validation_result'] == 'accepted'
    assert receipt['resolved_model'] is None  # alias is not proof of serving identity
    assert receipt['executed_arguments'] is None
    assert receipt['observed_downstream_outcome']['task_correctness'] == 'unknown'
    assert result['gate'] is False and result['reference_satisfied'] is None


@pytest.mark.parametrize('status', ['missing_parent', 'turn_error', 'oversize'])
def test_incomplete_capture_does_not_call_model(api, status):
    row = capture()
    row['status'] = status
    def forbidden(_):
        pytest.fail('invalid capture entered inference')
    result = selfcheck(row, api=api, judge=forbidden, model='worker')
    assert result['status'] == 'unknown'
    assert result['receipt']['validation_result'] == 'abstained'


@pytest.mark.parametrize('raw', [{}, response(confidence=float('nan')),
                                {'choices': [{'finish_reason': 'length'}]}])
def test_bad_judgment_preserves_unknown_and_response(api, raw):
    result = selfcheck(capture(), api=api, judge=lambda _: raw, model='worker')
    assert result['status'] == 'unknown'
    assert result['judgment'] is None
    assert result['response'] == raw


def test_timeout_is_non_gating_unknown(api):
    def timeout(_):
        raise TimeoutError('worker deadline')
    result = selfcheck(capture(), api=api, judge=timeout, model='worker')
    assert result['status'] == 'unknown'
    assert result['error'] == 'worker deadline'
    assert result['receipt']['fallback'] == 'incumbent_fallback'


def test_input_change_invalidates_receipt(api):
    row = capture()
    def mutate(_):
        row['messages'][1]['parts'][0]['text'] = 'changed'
        return response()
    result = selfcheck(row, api=api, judge=mutate, model='worker')
    assert result['receipt']['validation_result'] == 'stale'
    assert result['judgment'] is None


def test_expired_receipt_is_not_a_judgment(api):
    result = selfcheck(capture(), api=api, judge=lambda _: response(), model='worker', ttl_s=-1)
    assert result['receipt']['validation_result'] == 'expired'
    assert result['status'] == 'unknown'


def test_foreign_parent_blocks_judge(api):
    row = capture()
    row['messages'][1]['info']['parentID'] = 'other'
    result = selfcheck(row, api=api, judge=lambda _: pytest.fail('must not call'), model='worker')
    assert result['status'] == 'unknown'


def test_cli_requires_keeper_before_import_or_network(tmp_path):
    env = dict(os.environ)
    env.pop('FILLER_ID', None)
    run = subprocess.run([sys.executable, 'scripts/harness/hs_td2_selfcheck.py',
                          '--orchestrator-repo', str(tmp_path), '--captures', '/missing',
                          '--output', str(tmp_path / 'out'), '--endpoint', 'http://invalid',
                          '--model', 'worker'], env=env, capture_output=True, text=True)
    assert run.returncode == 2
    assert 'keeper execution required' in run.stderr
    assert not (tmp_path / 'out').exists()


def test_wire_bytes_survive_parse_failure(api):
    raw = ' {"broken": true} \n'
    result = selfcheck(capture(), api=api, judge=lambda _: raw, model='worker')
    assert result['response'] == raw
    assert result['receipt']['selector_calls'][0]['response'] == raw
    assert result['status'] == 'unknown'


def test_cli_writes_private_native_receipt(api, tmp_path, monkeypatch):
    from scripts.harness import hs_td2_selfcheck as consumer
    from io import BytesIO
    source, output = tmp_path / 'captures', tmp_path / 'out'
    source.write_text(json.dumps(capture()) + '\n')
    monkeypatch.setenv('FILLER_ID', 'test-only')
    monkeypatch.delenv('FILLER_STOPFILE', raising=False)
    monkeypatch.delenv('FILLER_DEADLINE', raising=False)
    monkeypatch.setattr(consumer.importlib, 'import_module', lambda _: api)
    monkeypatch.setattr(consumer.urllib.request, 'urlopen',
                        lambda *a, **kw: BytesIO(json.dumps(response()).encode()))
    monkeypatch.setattr(sys, 'argv', ['consumer', '--orchestrator-repo', str(tmp_path),
        '--captures', str(source), '--output', str(output),
        '--endpoint', 'http://mock', '--model', 'worker'])
    assert consumer.main() == 0
    assert json.loads(output.read_text())['status'] == 'ok'
    assert output.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        consumer.main()
