"""Regression tests for completed-run admission; all readers/transports are offline."""
import copy
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from test_run_beam_reader import dataset, run
import run_beam_reader as launcher
import long_context_adapters as adapters
import admit_beam_runs as admission


@pytest.fixture
def completed(dataset, tmp_path, monkeypatch):
    class TraceFixture:
        name = 'offline-trace-fixture'

        def __init__(self, chunks, **kwargs):
            self.chunks = chunks

        def __call__(self, question, *, conversation_id, top_k):
            return self.chunks[conversation_id][:top_k]

    monkeypatch.setattr(adapters, 'TracePairChunkRetriever', TraceFixture)
    specs = [(arm, tmp_path / arm) for arm in ('full', 'rag', 'trace')]
    for arm, path in specs:
        run(dataset, path, arm)
        launcher.write_json(path / 'scored-beam-fixture.json', {'summary': {
            'fold': 'beam_macro', 'headline': 0.6, 'judge_model': 'different-judge',
            'truncated_rows': 0}})
    return specs, launcher.digest(dataset)


def admit(completed, checker):
    specs, sha = completed
    return admission.admit_runs(specs, check_arms=checker, min_max_tokens=2048,
                                expected_dataset_sha=sha)


def test_complete_runs_clear_unchanged_checklist(completed):
    report = admit(completed, admission.load_checker())
    assert report['integrity'] == 'PASS'
    assert report['cleared'], report
    assert len(report['checklist']['items']) == 8


@pytest.mark.parametrize('defect', [
    'prepared', 'running', 'failed', 'count', 'zero_count', 'bool_count', 'wrong_arm',
    'no_completed_at', 'no_source', 'wrong_source_hash', 'dataset_not_verified',
    'prompt_hash', 'template_hash', 'reader_hash', 'prepared_hash', 'missing_answer',
    'answer_prompt', 'answer_params', 'no_response', 'finish_reason',
    'hidden_truncation', 'duplicate_summary', 'missing_summary', 'reader_identity',
    'across_arm_reader', 'duplicate_ids', 'extra_prompt_hash',
])
def test_bad_bindings_cannot_reach_checklist(completed, defect):
    specs, _ = completed
    path = specs[0][1]
    rp = path / 'beam_run_receipt.json'
    receipt = json.loads(rp.read_text())
    payload = json.loads((path / 'reader.json').read_text())
    prepared = json.loads((path / 'prepared-questions.json').read_text())
    first = next(iter(payload['results']['beam'].values()))
    if defect in ('prepared', 'running', 'failed'):
        receipt['status'] = defect
    elif defect == 'count':
        receipt['questions_completed'] -= 1
    elif defect == 'zero_count':
        receipt['questions_expected'] = receipt['questions_completed'] = 0
    elif defect == 'bool_count':
        receipt['questions_completed'] = True
    elif defect == 'wrong_arm':
        receipt['arm'] = 'trace'
    elif defect == 'no_completed_at':
        del receipt['completed_at']
    elif defect == 'no_source':
        del receipt['sources']['launcher']
    elif defect == 'wrong_source_hash':
        receipt['sources']['adapter']['sha256'] = '0' * 64
    elif defect == 'dataset_not_verified':
        receipt['dataset']['verified_before_inference'] = False
    elif defect == 'prompt_hash':
        receipt['prompt_sha256_by_question'][prepared[0]['id']] = '0' * 64
    elif defect == 'template_hash':
        receipt['reader']['prompt_template'] += 'changed instruction'
    elif defect == 'reader_hash':
        receipt['reader_sha256'] = '0' * 64
    elif defect == 'prepared_hash':
        receipt['prepared_questions_sha256'] = '0' * 64
    elif defect == 'missing_answer':
        payload['results']['beam'].pop(prepared[0]['id'])
    elif defect == 'answer_prompt':
        first['prompt'] += 'changed'
    elif defect == 'answer_params':
        first['inference_params']['max_tokens'] = 1
    elif defect == 'no_response':
        del first['response']
    elif defect == 'finish_reason':
        del first['finish_reason']
    elif defect == 'hidden_truncation':
        first['finish_reason'] = 'length'
    elif defect == 'duplicate_summary':
        (path / 'scored-beam-extra.json').write_text('{}')
    elif defect == 'missing_summary':
        (path / 'scored-beam-fixture.json').unlink()
    elif defect == 'reader_identity':
        payload['model_role'] = 'another reader'
    elif defect == 'across_arm_reader':
        receipt['reader']['model'] = payload['model_role'] = 'another reader'
    elif defect == 'duplicate_ids':
        prepared[-1] = copy.deepcopy(prepared[0])
        launcher.write_json(path / 'prepared-questions.json', prepared)
        receipt['prepared_questions_sha256'] = launcher.digest(path / 'prepared-questions.json')
    elif defect == 'extra_prompt_hash':
        receipt['prompt_sha256_by_question']['invented'] = '0' * 64
    # Rebind mutated answers so deeper consistency checks are exercised, not just SHA checks.
    if defect in {'missing_answer', 'answer_prompt', 'answer_params', 'no_response',
                  'finish_reason', 'hidden_truncation', 'reader_identity', 'across_arm_reader'}:
        launcher.write_json(path / 'reader.json', payload)
        receipt['reader_sha256'] = launcher.digest(path / 'reader.json')
    launcher.write_json(rp, receipt)
    checker = Mock(side_effect=AssertionError('invalid run reached checklist'))
    report = admit(completed, checker)
    assert not report['cleared'], report
    assert report['integrity'] == 'FAIL'
    checker.assert_not_called()


@pytest.mark.parametrize('defect', ['missing_arm', 'duplicate_arm'])
def test_arm_inventory_is_exact(completed, defect):
    specs, sha = completed
    specs = specs[:-1] if defect == 'missing_arm' else [specs[0], specs[0], specs[2]]
    checker = Mock()
    report = admission.admit_runs(specs, check_arms=checker, min_max_tokens=2048,
                                  expected_dataset_sha=sha)
    assert not report['cleared']
    checker.assert_not_called()


def test_integrity_pass_does_not_override_checklist_failure(completed):
    checker = Mock(return_value={'cleared': False, 'items': [{'item': 3, 'status': 'FAIL'}]})
    report = admit(completed, checker)
    assert report['integrity'] == 'PASS' and not report['cleared']
    checker.assert_called_once()
