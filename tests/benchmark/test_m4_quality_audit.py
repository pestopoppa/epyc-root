import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[2] / 'scripts/benchmark/m4_quality_audit.py'
spec = importlib.util.spec_from_file_location('m4_quality_audit', MODULE)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def make_run(tmp_path):
    prompts = {'q1': 'first', 'q2': 'second'}
    plan = {'schema': 'epyc.m4.quality_audit_plan.v1', 'seed': 42, 'max_tokens': 64, 'runner_sha256': 'a'*64,
            'roles': {'worker_general': {'model_path': '/models/worker.gguf', 'suites': {
                'mmlu_pro': [{'id': q, 'prompt_sha256': hashlib.sha256(p.encode()).hexdigest(), 'expected': 'A'} for q, p in prompts.items()]}}}}
    plan_path = tmp_path / 'plan.json'
    plan_path.write_text(json.dumps(plan))
    runs = tmp_path / 'runs'
    for arm in ('baseline', 'candidate'):
        directory = runs / 'worker_general' / arm / 'mmlu_pro'
        directory.mkdir(parents=True)
        rows = [{'id': q, 'suite': 'mmlu_pro', 'arm': f'worker_general-{arm}', 'runner_source_sha256': 'a'*64, 'seed': 42, 'correct': True, 'truncated': False,
                 'effective_request': {'endpoint': 'chat', 'temperature': 0.0}, 'finish_reason': 'stop', 'expected': 'A',
                 'prompt': p, 'prompt_fingerprint': {'sha256': hashlib.sha256(p.encode()).hexdigest()}}
                for q, p in prompts.items()]
        (directory / 'per_question.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
        summary = {'meta': {'models': '/models/worker.gguf', 'seed': 42, 'temperature': 0.0, 'max_tokens': 64},
                   'suites': [{'suite': 'mmlu_pro', 'n': 2, 'errors': 0, 'truncated': 0, 'correct': 2}]}
        (directory / 'result.json').write_text(json.dumps(summary))
    return plan_path, hashlib.sha256(plan_path.read_bytes()).hexdigest(), runs


def rewrite(path, modify):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    modify(rows)
    path.write_text(''.join(json.dumps(row)+'\n' for row in rows))


def test_clean_native_pair(tmp_path):
    plan, sha, root = make_run(tmp_path)
    result = audit.audit(plan, sha, root)
    assert result['complete'] and len(result['rows']) == 2
    assert all(row['n'] == 2 and row['correct'] == 2 for row in result['rows'])


@pytest.mark.parametrize('mutation', ['wrong_plan', 'changed_prompt', 'duplicate', 'wrong_seed', 'missing_finish', 'summary_mismatch', 'missing_arm', 'wrong_arm', 'wrong_runner', 'wrong_answer'])
def test_refuses_unbound_or_inconsistent_capture(tmp_path, mutation):
    plan, sha, root = make_run(tmp_path)
    directory = root / 'worker_general' / 'candidate' / 'mmlu_pro'
    path = directory / 'per_question.jsonl'
    if mutation == 'wrong_plan': sha = '0'*64
    elif mutation == 'changed_prompt': rewrite(path, lambda rows: rows[0].update(prompt='different'))
    elif mutation == 'duplicate': rewrite(path, lambda rows: rows[1].update(id='q1'))
    elif mutation == 'wrong_answer': rewrite(path, lambda rows: rows[0].update(expected='B'))
    elif mutation == 'wrong_arm': rewrite(path, lambda rows: rows[0].update(arm='worker_general-baseline'))
    elif mutation == 'wrong_runner': rewrite(path, lambda rows: rows[0].update(runner_source_sha256='b'*64))
    elif mutation == 'wrong_seed': rewrite(path, lambda rows: rows[0].update(seed=7))
    elif mutation == 'missing_finish': rewrite(path, lambda rows: rows[0].update(finish_reason=''))
    elif mutation == 'summary_mismatch':
        document = json.loads((directory / 'result.json').read_text()); document['suites'][0]['correct'] = 1
        (directory / 'result.json').write_text(json.dumps(document))
    elif mutation == 'missing_arm': path.unlink()
    with pytest.raises((ValueError, OSError)):
        audit.audit(plan, sha, root)


def test_truncated_captures_remain_incomplete(tmp_path):
    plan, sha, root = make_run(tmp_path)
    directory = root / 'worker_general' / 'candidate' / 'mmlu_pro'
    rewrite(directory / 'per_question.jsonl', lambda rows: rows[0].update(truncated=True, finish_reason='length', correct=False))
    path = directory / 'result.json'
    document = json.loads(path.read_text()); document['suites'][0].update(truncated=1, correct=1)
    path.write_text(json.dumps(document))
    result = audit.audit(plan, sha, root)
    assert not result['complete']
    assert result['rows'][1]['truncated'] == 1
