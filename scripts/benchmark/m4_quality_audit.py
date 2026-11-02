#!/usr/bin/env python3
"""Audit M4 paired native quality captures against an independently pinned plan.

This is a capture consistency audit, not a quality/promotion gate and not a
source of measurement claims. The caller supplies the plan digest from a
pre-run trust boundary; never derive that digest from a native result row.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_json(path: Path) -> dict:
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError(f'{path}: expected object')
    return value


def audit(plan_path: Path, expected_sha256: str, run_root: Path) -> dict:
    raw = plan_path.read_bytes()
    if len(expected_sha256) != 64 or digest(raw) != expected_sha256:
        raise ValueError('independent plan digest mismatch')
    plan = json.loads(raw)
    if not isinstance(plan, dict) or plan.get('schema') != 'epyc.m4.quality_audit_plan.v1':
        raise ValueError('invalid plan schema')
    roles = plan.get('roles')
    if not isinstance(roles, dict) or not roles:
        raise ValueError('empty role scope')
    if not isinstance(plan.get('runner_sha256'), str) or len(plan['runner_sha256']) != 64:
        raise ValueError('runner source digest missing')
    if plan.get('seed') != 42 or type(plan.get('max_tokens')) is not int or plan['max_tokens'] <= 0:
        raise ValueError('invalid seed or token cap')
    root = run_root.resolve(strict=True)
    records = []
    complete = True
    for role, role_spec in sorted(roles.items()):
        if not isinstance(role, str) or not role or Path(role).name != role or role in ('.', '..'):
            raise ValueError('invalid role name')
        if not isinstance(role_spec, dict) or not isinstance(role_spec.get('model_path'), str) or not Path(role_spec['model_path']).is_absolute():
            raise ValueError('invalid role model')
        suites = role_spec.get('suites')
        if not isinstance(suites, dict) or not suites:
            raise ValueError('empty suite scope')
        for suite, expected in sorted(suites.items()):
            if not isinstance(suite, str) or not suite or Path(suite).name != suite or suite in ('.', '..'):
                raise ValueError('invalid suite name')
            if not isinstance(expected, list) or not expected:
                raise ValueError('empty question set')
            required = {}
            for item in expected:
                if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not item['id'] or not isinstance(item.get('prompt_sha256'), str) or len(item['prompt_sha256']) != 64:
                    raise ValueError('invalid expected question')
                if item['id'] in required:
                    raise ValueError('duplicate expected question')
                required[item['id']] = item['prompt_sha256']
            for arm in ('baseline', 'candidate'):
                directory = (root / role / arm / suite).resolve(strict=True)
                if root not in directory.parents:
                    raise ValueError('capture path outside run root')
                per_question = directory / 'per_question.jsonl'
                if root not in per_question.resolve(strict=True).parents:
                    raise ValueError('capture file escapes run root')
                result_path = directory / 'result.json'
                if root not in result_path.resolve(strict=True).parents:
                    raise ValueError('result file escapes run root')
                raw_rows = per_question.read_bytes()
                rows = [json.loads(line) for line in raw_rows.splitlines() if line.strip()]
                if len(rows) != len(required) or any(not isinstance(row, dict) for row in rows):
                    raise ValueError('question count mismatch')
                seen = {}
                errors = truncations = correct = 0
                for row in rows:
                    qid = row.get('id')
                    if not isinstance(qid, str) or qid in seen or qid not in required:
                        raise ValueError('missing, duplicate or unexpected question')
                    if row.get('arm') != f'{role}-{arm}' or row.get('runner_source_sha256') != plan['runner_sha256']:
                        raise ValueError('arm or runner source mismatch')
                    if row.get('suite') != suite or row.get('seed') != plan['seed']:
                        raise ValueError('suite or seed mismatch')
                    if type(row.get('correct')) is not bool or type(row.get('truncated')) is not bool:
                        raise ValueError('invalid outcome flags')
                    request = row.get('effective_request')
                    if not isinstance(request, dict) or request.get('endpoint') != 'chat' or request.get('temperature') != 0.0:
                        raise ValueError('effective request mismatch')
                    prompt = row.get('prompt')
                    fingerprint = row.get('prompt_fingerprint')
                    if not isinstance(prompt, str) or not isinstance(fingerprint, dict) or digest(prompt.encode()) != fingerprint.get('sha256') or fingerprint['sha256'] != required[qid]:
                        raise ValueError('question prompt differs from pinned plan')
                    finish = row.get('finish_reason')
                    if not isinstance(finish, str) or not finish or (finish == 'length') != row['truncated']:
                        raise ValueError('missing or inconsistent finish reason')
                    seen[qid] = fingerprint['sha256']
                    errors += bool(row.get('request_error')) or finish == 'request_error'
                    truncations += row['truncated']
                    correct += row['correct']
                document = _read_json(result_path)
                meta, summary = document.get('meta'), document.get('suites')
                if not isinstance(meta, dict) or not isinstance(summary, list) or len(summary) != 1 or not isinstance(summary[0], dict):
                    raise ValueError('invalid native result')
                if meta.get('models') != role_spec['model_path'] or meta.get('seed') != plan['seed'] or meta.get('temperature') != 0.0 or meta.get('max_tokens') != plan['max_tokens']:
                    raise ValueError('native metadata mismatch')
                expected_summary = {'suite': suite, 'n': len(required), 'errors': errors, 'truncated': truncations, 'correct': correct}
                if any(summary[0].get(key) != value for key, value in expected_summary.items()):
                    raise ValueError('native summary disagrees with questions')
                complete &= errors == 0 and truncations == 0
                records.append({'role': role, 'suite': suite, 'arm': arm, 'n': len(rows), 'correct': correct,
                                'errors': errors, 'truncated': truncations, 'capture_sha256': digest(raw_rows),
                                'result_sha256': digest(result_path.read_bytes())})
    return {'schema': 'epyc.m4.quality_capture_audit.v1', 'plan_sha256': expected_sha256,
            'complete': bool(complete), 'rows': records}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--runs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(args.plan, args.plan_sha256, args.runs)
        with args.output.open('x', encoding='utf-8') as output:
            json.dump(result, output, indent=2, sort_keys=True)
            output.write('\n')
        return 0 if result['complete'] else 2
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f'REFUSED: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
