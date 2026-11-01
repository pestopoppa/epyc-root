#!/usr/bin/env python3
"""Verify a three-arm run's custody and schedule, without grading its outcome.

This checks that directory names and recorded arm identities match the plan and
that payload bytes match their recorded hashes. Directory order is a caller
assertion, not proof of execution order. It cannot establish that a response came
from a model, a score is correct, a reset occurred, or the source identities and
grant are genuine. A runner must prove those independently before interpretation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

ARMS = {'baseline', 'strategy_short', 'strategy_long'}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify(plan_path: Path, capture_dir: Path) -> dict:
    plan_raw = plan_path.read_bytes()
    plan = json.loads(plan_raw)
    if plan.get('schema') != 'epyc.strategy_prompt_ablation.plan.v1':
        raise ValueError('foreign plan')
    if plan.get('run_authority') is not False:
        raise ValueError('plan cannot confer run authority')
    prompts = plan.get('prompt_sha256')
    schedule = plan.get('schedule')
    if not isinstance(prompts, dict) or set(prompts) != ARMS or not isinstance(schedule, list) or not schedule:
        raise ValueError('invalid plan arms or schedule')
    if any(not isinstance(d, str) or len(d) != 64 or any(c not in '0123456789abcdef' for c in d)
           for d in prompts.values()) or len(set(prompts.values())) != 3:
        raise ValueError('plan requires distinct lowercase prompt SHA-256 digests')
    sequence = []
    seen = set()
    for row in schedule:
        if not isinstance(row, dict) or not isinstance(row.get('question_id'), str) or not row['question_id']:
            raise ValueError('invalid schedule question')
        qid, order = row['question_id'], row.get('order')
        if qid in seen or not isinstance(order, list) or len(order) != 3 or set(order) != ARMS:
            raise ValueError('duplicate question or invalid arm order')
        seen.add(qid)
        sequence.extend((qid, arm) for arm in order)
    expected = {f'{i:06d}' for i in range(len(sequence))}
    if not capture_dir.is_dir() or {p.name for p in capture_dir.iterdir()} != expected:
        raise ValueError('capture directories must exactly match complete schedule')
    for i, (qid, arm) in enumerate(sequence):
        entry = capture_dir / f'{i:06d}'
        if entry.is_symlink() or not entry.is_dir():
            raise ValueError(f'invalid capture directory {i}')
        recfile = entry / 'record.json'
        if recfile.is_symlink() or not recfile.is_file():
            raise ValueError(f'missing capture record at {i}')
        record = json.loads(recfile.read_bytes())
        record_fields = {'schema', 'plan_sha256', 'question_id', 'arm', 'prompt_sha256',
                         'source_identity', 'slot_reset_receipt', 'origin', 'status',
                         'correct', 'error', 'turns'}
        if not isinstance(record, dict) or set(record) != record_fields:
            raise ValueError(f'invalid record fields at {i}')
        if (record.get('schema') != 'epyc.strategy_prompt_ablation.capture.v2'
                or record.get('origin') != 'live_claimed' or record.get('status') != 'complete'
                or record.get('plan_sha256') != _sha(plan_raw)
                or record.get('question_id') != qid or record.get('arm') != arm
                or record.get('prompt_sha256') != prompts[arm]):
            raise ValueError(f'capture identity mismatch at {i}')
        for key in ('source_identity', 'slot_reset_receipt'):
            if not isinstance(record.get(key), str) or not record[key].strip():
                raise ValueError(f'missing {key} at {i}')
        if record.get('correct') is not None and type(record['correct']) is not bool:
            raise ValueError(f'invalid score at {i}')
        if record['error'] is not None:
            raise ValueError(f'complete capture has task error at {i}')
        turns = record.get('turns')
        if not isinstance(turns, list) or not turns:
            raise ValueError(f'missing turns at {i}')
        files = {'record.json'}
        for j, turn in enumerate(turns, 1):
            turn_fields = {'turn', 'request_file', 'request_sha256', 'response_file',
                           'response_sha256', 'prompt_tokens', 'output_tokens', 'elapsed_s', 'error'}
            if (not isinstance(turn, dict) or set(turn) != turn_fields
                    or type(turn['turn']) is not int or turn['turn'] != j):
                raise ValueError(f'invalid turn ordering at {i}')
            if turn['error'] is not None:
                raise ValueError(f'complete capture has turn error at {i}')
            for key in ('request', 'response'):
                filename = f'turn-{j:04d}-{key}.bin'
                path = entry / filename
                if turn.get(key + '_file') != filename or path.is_symlink() or not path.is_file():
                    raise ValueError(f'invalid payload path at {i}')
                data = path.read_bytes()
                if not data or turn.get(key + '_sha256') != _sha(data):
                    raise ValueError(f'payload custody mismatch at {i}')
                files.add(filename)
            for key in ('prompt_tokens', 'output_tokens'):
                if turn.get(key) is not None and (type(turn[key]) is not int or turn[key] < 0):
                    raise ValueError(f'invalid {key} at {i}')
            elapsed = turn.get('elapsed_s')
            if elapsed is not None and (type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0):
                raise ValueError(f'invalid elapsed time at {i}')
        if {p.name for p in entry.iterdir()} != files:
            raise ValueError(f'unexpected capture files at {i}')
    return {'status': 'custody_only', 'records': len(sequence), 'plan_sha256': _sha(plan_raw),
            'limitations': 'No actual execution order, grant, identity, reset, native measurement, scorer or outcome verified.'}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--capture-dir', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.plan, args.capture_dir), sort_keys=True))


if __name__ == '__main__':
    main()
