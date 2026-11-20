#!/usr/bin/env python3
"""Validate completed native receipts before invoking the unchanged M-12c checklist.

Offline, outside compute grants. Integrity is consistency, not authentication or
proof of model identity; this does not attest a score's judgment provenance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

CHECKER_OBJECT = 'c9aac169b:scripts/benchmark/beam_prerun_checklist.py'
RESEARCH = '/mnt/raid0/llm/epyc-inference-research'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_arm(directory, arm):
    """Refuse incomplete receipts and inconsistent native question/answer bindings."""
    directory = Path(directory)
    receipt = json.loads((directory / 'beam_run_receipt.json').read_text())
    require(receipt.get('schema') == 'epyc.beam_run_receipt.v1', 'receipt schema')
    require(receipt.get('arm') == arm, 'arm identity')
    require(receipt.get('status') == 'complete' and receipt.get('completed_at'), 'incomplete run')
    count = receipt.get('questions_expected')
    require(type(count) is int and count > 0, 'invalid expected count')
    require(type(receipt.get('questions_completed')) is int
            and receipt['questions_completed'] == count, 'incomplete question count')
    require(receipt.get('dataset', {}).get('verified_before_inference') is True,
            'no contemporaneous dataset verification')
    sources = receipt.get('sources', {})
    require(set(sources) == {'launcher', 'adapter', 'retrievers'}, 'missing source bindings')
    for name, source in sources.items():
        require(digest(source['path']) == source['sha256'], f'source changed: {name}')
    require(digest(directory / 'prepared-questions.json') == receipt.get('prepared_questions_sha256'),
            'prepared questions digest')
    rows = json.loads((directory / 'prepared-questions.json').read_text())
    require(isinstance(rows, list) and len(rows) == count, 'prepared question count')
    ids = [row['id'] for row in rows]
    require(len(set(ids)) == count, 'duplicate question ids')
    prompts = {row['id']: hashlib.sha256(row['prompt'].encode()).hexdigest() for row in rows}
    require(prompts == receipt.get('prompt_sha256_by_question'), 'per-question prompt binding')
    reader = receipt['reader']
    require(hashlib.sha256(reader['prompt_template'].encode()).hexdigest()
            == reader.get('prompt_sha256'), 'shared template binding')
    require(digest(directory / 'reader.json') == receipt.get('reader_sha256'), 'reader digest')
    payload = json.loads((directory / 'reader.json').read_text())
    require(payload.get('model_role') == reader['model'], 'reader identity')
    answers = payload['results']['beam']
    require(set(answers) == set(ids), 'answer question set')
    truncated = 0
    for row in rows:
        answer = answers[row['id']]
        # Bind every prepared field, including scoring config, ability and prompt.
        require(all(answer.get(k) == v for k, v in row.items()), 'answer/prepared mismatch')
        require(isinstance(answer.get('response'), str), 'missing response')
        require(answer.get('finish_reason') in {'stop', 'length'}, 'missing finish reason')
        truncated += answer['finish_reason'] == 'length'
        params = answer.get('inference_params', {})
        require(bool(params) and all(reader.get(k) == v for k, v in params.items()),
                'generation parameters differ')
        require({'max_tokens', 'temperature', 'enable_thinking', 'cache_prompt', 'timeout'} <= set(params),
                'missing generation parameters')
    scored = list(directory.glob('scored-beam-*.json'))
    require(len(scored) == 1, 'need exactly one scored summary')
    summary = json.loads(scored[0].read_text())['summary']
    require(summary.get('truncated_rows') == truncated, 'summary truncation count differs')
    return {'arm': arm, 'receipt': receipt, 'summary': summary}


def admit_runs(specs, *, check_arms, min_max_tokens, expected_dataset_sha):
    """Require all three arms and valid bindings before the eight-item checker."""
    try:
        require(len(specs) == 3 and {arm for arm, _ in specs} == {'full', 'rag', 'trace'},
                'need exactly one full, rag and trace arm')
        arms = [validate_arm(path, arm) for arm, path in specs]
        receipts = [a['receipt'] for a in arms]
        require(all(set(r['prompt_sha256_by_question']) == set(receipts[0]['prompt_sha256_by_question'])
                    for r in receipts), 'question sets differ across arms')
        for key in ('model', 'max_tokens', 'temperature', 'enable_thinking', 'cache_prompt', 'timeout'):
            require(all(r['reader'][key] == receipts[0]['reader'][key] for r in receipts),
                    f'reader settings differ across arms: {key}')
    except (ValueError, KeyError, TypeError, OSError) as exc:
        return {'schema': 'epyc.beam_admission.v1', 'cleared': False,
                'integrity': 'FAIL', 'error': str(exc)}
    checklist = check_arms(arms, min_max_tokens=min_max_tokens,
                           expected_dataset_sha=expected_dataset_sha)
    return {'schema': 'epyc.beam_admission.v1', 'cleared': checklist['cleared'],
            'integrity': 'PASS', 'checklist': checklist,
            'checker_git_object': CHECKER_OBJECT}


def load_checker():
    source = subprocess.check_output(['git', '-C', RESEARCH, 'show', CHECKER_OBJECT], text=True)
    namespace = {'__name__': 'pinned_beam_checklist'}
    exec(compile(source, CHECKER_OBJECT, 'exec'), namespace)
    return namespace['check_arms']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm', action='append', required=True, metavar='NAME=RUN_DIR')
    parser.add_argument('--min-max-tokens', type=int, required=True)
    parser.add_argument('--expected-dataset-sha', required=True)
    args = parser.parse_args()
    specs = [item.split('=', 1) for item in args.arm]
    report = admit_runs(specs, check_arms=load_checker(), min_max_tokens=args.min_max_tokens,
                        expected_dataset_sha=args.expected_dataset_sha)
    print(json.dumps(report, indent=2))
    return 0 if report['cleared'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
