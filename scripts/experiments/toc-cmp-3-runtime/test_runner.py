"""Offline transport and candidate-custody checks; no inference."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

PRIOR = Path('/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp3-semantic/packet')
sys.path.insert(0, str(PRIOR))
spec = importlib.util.spec_from_file_location('runtime_runner', Path(__file__).with_name('runner.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_transport_extracts_raw_judgment():
    raw = json.dumps({'choices': [{'finish_reason': 'stop', 'message': {'content': '{"ok":true}'}}]}).encode()
    assert runner.response_bytes(raw) == b'{"ok":true}'


@pytest.mark.parametrize('payload', [
    {'choices': []},
    {'choices': [{'finish_reason': 'length', 'message': {'content': '{}'}}]},
    {'choices': [{'finish_reason': 'stop', 'message': {'content': None}}]},
])
def test_transport_rejects_incomplete_response(payload):
    with pytest.raises(ValueError):
        runner.response_bytes(json.dumps(payload).encode())


def test_candidate_custody_rejects_mutated_packet(tmp_path, monkeypatch):
    from semantic import canonical, digest
    (tmp_path / 'runner.py').write_bytes(b'changed')
    manifest = {'packet_sha256': {'runner.py': digest(b'original')}, 'build_sha256': {},
                'model': {'path': 'unused'}}
    (tmp_path / 'inputs.json').write_bytes(canonical({**manifest, 'sha256': digest(canonical(manifest))}))
    monkeypatch.setattr(runner, 'HERE', tmp_path)
    with pytest.raises(ValueError, match='custody mismatch'):
        runner.verify()


@pytest.mark.parametrize(('name', 'expected'), [
    ('ordinary-preserved', 'entailed'),
    ('folded-conflict', 'contradicted'),
    ('missing-external-evidence', 'unknown'),
])
def test_real_candidate_boundary_with_mock_evaluator(tmp_path, monkeypatch, name, expected):
    """Exercise the actual candidate boundary using a deterministic HTTP double."""
    if not (runner.CANDIDATE / 'src/graph/compaction_semantic.py').is_file():
        pytest.skip('prepared candidate not present')
    from semantic import canonical

    def http(_route, _timeout, body):
        case = json.loads(body['messages'][1]['content'])
        judgments = {}
        for field, value in case['reference'].items():
            verdict, message, quote = 'entailed', 0, value
            if name == 'folded-conflict' and field == 'pinned_governance':
                verdict, message, quote = 'contradicted', 1, 'Send the receipt to the external reviewer'
            elif name == 'missing-external-evidence' and field == 'artifacts':
                verdict = 'unknown'
            judgments[field] = {'verdict': verdict, 'rationale': 'Offline fixture judgment.',
                                'evidence': [] if verdict == 'unknown' else [{'message': message, 'quote': quote}]}
        content = canonical({'request_id': case['request_id'], 'judgments': judgments}).decode()
        return canonical({'choices': [{'finish_reason': 'stop', 'message': {'content': content}}]})

    monkeypatch.setattr(runner.base, 'http', http)
    monkeypatch.setattr(runner.base, 'remaining', lambda _: 100)
    outcome = runner.capture_boundary(name, tmp_path, 'offline-mock', 100)
    assert outcome['actual_verdict'] == expected
    assert outcome['blocked'] == (expected != 'entailed')
    captured = json.loads((tmp_path / name / 'case.json').read_bytes())
    assert ('independently verified by the bank' in captured['reference']['artifacts']) == (name == 'missing-external-evidence')
    assert 'Bank verification record' not in captured['observed_messages'][1]['content']
