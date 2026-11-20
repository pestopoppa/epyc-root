"""Prepare sealed calibration requests without executing or reading model weights."""
import argparse
import copy
from pathlib import Path

from floor import _module, validate_requests


def prepare(plan_path, target_quant, prompt_id, seed, repetitions):
    capture = _module('capture')
    worker = _module('worker')
    plan, identity = capture._read(plan_path)
    capture._plan(plan)
    if plan['origin'] != 'native_claimed':
        raise ValueError('floor requires native_claimed plan')
    _module('admission').admit(plan, capture._read, require_floor=False)
    if type(repetitions) is not int or not 2 <= repetitions <= 100:
        raise ValueError('floor repetitions must be between 2 and 100')
    if type(seed) is not int or not 0 <= seed <= 4294967295:
        raise ValueError('invalid calibration seed')
    cases = [c for c in plan['cells'] if c['target_quant'] == target_quant]
    if not cases or len({c['target_sha256'] for c in cases}) != 1:
        raise ValueError('unknown or ambiguous target quant')
    prompts, prompt_identity = capture._read(plan['native_worker']['prompt_manifest'])
    if prompt_identity['sha256'] != plan['prompt_manifest_sha256']:
        raise ValueError('floor prompt manifest mismatch')
    prompt = prompts['prompts'].get(prompt_id)
    if not isinstance(prompt, str) or not prompt:
        raise ValueError('missing calibration prompt text')
    requests = []
    for repetition in range(repetitions):
        case = copy.deepcopy(cases[0])
        case.update(cell_id=f'floor-{target_quant}-{repetition}', prompt_id=prompt_id,
                    seed=seed, repetition=repetition)
        requests.append(dict(
            schema=worker.SCHEMA, run_id=plan['run_id'], plan_sha256=identity['sha256'],
            case=case, prompt=prompt,
            settings=copy.deepcopy({key: plan[key] for key in capture.SHARED}),
            runtime=copy.deepcopy(plan['native_worker']),
            trace_semantics='greedy_prefix_acceptance_and_same_prefix_verify_vs_serial_logits'))
    validate_requests(plan, requests, capture._read)
    return {'requests': requests}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--target-quant', required=True)
    parser.add_argument('--prompt-id', required=True)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--repetitions', type=int, required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    prepared = prepare(args.plan, args.target_quant, args.prompt_id, args.seed, args.repetitions)
    _module('capture')._exclusive(Path(args.output), prepared)
