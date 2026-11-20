"""Per-cell DFlash native-trace worker. Execute only in an admitted row.

The trace-enabled executable takes --request JSON --output JSON. Stock server
summary counters cannot supply this protocol and must never be substituted.
"""
from __future__ import annotations

import argparse
import importlib.util
import math
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

spec = importlib.util.spec_from_file_location('precision_worker_capture', Path(__file__).with_name('capture.py'))
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)
SCHEMA = 'epyc.target-precision.native-trace.v1'


def request_for(plan_path, cell_id):
    plan, identity = capture._read(plan_path)
    capture._plan(plan)
    cases = [c for c in plan['cells'] if c['cell_id'] == cell_id]
    if len(cases) != 1:
        raise ValueError('unknown cell')
    case = cases[0]
    # Hash only the small prompt manifest, never model weights in the grant.
    prompts, receipt = capture._read(plan['native_worker']['prompt_manifest'])
    if receipt['sha256'] != plan['prompt_manifest_sha256']:
        raise ValueError('prompt manifest digest mismatch')
    prompt = prompts['prompts'][case['prompt_id']]
    if not isinstance(prompt, str) or not prompt:
        raise ValueError('missing prompt text')
    config = plan['native_worker']
    if set(config) != {'executable', 'env', 'prompt_manifest', 'targets', 'drafter', 'timeout_s'}:
        raise ValueError('unknown or missing native worker setting')
    for value in [config['executable'], config['drafter'], config['targets'][case['target_quant']]]:
        if not isinstance(value, str) or not Path(value).is_absolute():
            raise ValueError('native paths must be absolute')
    env = config['env']
    if (not isinstance(env, dict) or not env.get('LD_LIBRARY_PATH')
            or any(not isinstance(k, str) or not isinstance(v, str) for k, v in env.items())):
        raise ValueError('explicit native environment and library path required')
    timeout = config['timeout_s']
    if type(timeout) not in (float, int) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('invalid native timeout')
    return plan, {
        'schema': SCHEMA, 'run_id': plan['run_id'], 'plan_sha256': identity['sha256'],
        'case': case, 'prompt': prompt,
        'settings': {key: plan[key] for key in capture.SHARED},
        'runtime': config,
        'trace_semantics': 'greedy_prefix_acceptance_and_same_prefix_verify_vs_serial_logits',
    }


def reduce_trace(trace, request):
    if trace.get('request') != request:
        raise ValueError('native request/settings echo mismatch')
    status = trace.get('status')
    if status in ('failed', 'invalid', 'abstained'):
        if not isinstance(trace.get('error'), str) or not trace['error'].strip():
            raise ValueError('terminal native error missing')
        return {'status': status, 'error': trace['error']}
    if status != 'ok':
        raise ValueError('unknown native status')
    # This first worker deliberately supports only greedy acceptance. Stochastic
    # token equality is not the rejection-sampling acceptance event.
    sampling = request['settings']['sampling']
    if sampling.get('temperature') != 0 or sampling.get('top_k') != 1:
        raise ValueError('worker supports greedy temperature=0 top_k=1 only')
    if trace.get('spec_type') != 'draft-dflash':
        raise ValueError('native trace is not DFlash')
    blocks = trace.get('blocks')
    if not isinstance(blocks, list) or not blocks:
        raise ValueError('missing native verification blocks')
    positions = {}
    max_abs = 0.0
    squared = []
    seen = set()
    vocab = None
    next_prefix = None
    encoding = trace.get('numerical_encoding', 'full-logits-v1')
    if encoding not in ('full-logits-v1', 'full-vocabulary-moments-v1'):
        raise ValueError('unknown numerical encoding')
    counts = []
    for block in blocks:
        index = block['block']
        capture._count(index)
        if index in seen:
            raise ValueError('duplicate native block')
        seen.add(index)
        draft, accepted = block['draft_tokens'], block['accepted']
        if not isinstance(draft, list) or not draft:
            raise ValueError('empty draft block')
        for token in draft:
            capture._count(token)
        capture._count(accepted)
        if accepted > len(draft):
            raise ValueError('accepted exceeds native draft')
        for position in range(len(draft)):
            row = positions.setdefault(position, {'position': position, 'accepted': 0, 'drafted': 0})
            row['drafted'] += 1
            row['accepted'] += int(position < accepted)
        rows = block['logits']
        # Includes the bonus prediction; paired rows must refer to identical
        # explicit token prefixes. No comparison of independent continuations.
        if not isinstance(rows, list) or len(rows) != len(draft) + 1:
            raise ValueError('missing full verification logits')
        for position, row in enumerate(rows):
            prefix = row['verify_prefix']
            if (not isinstance(prefix, list) or not prefix or prefix != row['serial_prefix']
                    or any(type(t) is not int or t < 0 for t in prefix)):
                raise ValueError('numerical comparison prefix mismatch')
            if position and prefix != rows[position - 1]['verify_prefix'] + [draft[position - 1]]:
                raise ValueError('verification prefix is not draft continuation')
            if position == 0 and next_prefix is not None and prefix != next_prefix:
                raise ValueError('native blocks do not follow accepted continuation')
            if encoding == 'full-vocabulary-moments-v1':
                if 'verify' in row or 'serial' in row:
                    raise ValueError('mixed numerical encoding')
                witness = row['witness']
                if set(witness) != {'count', 'verify_argmax', 'max_abs', 'sum_squared'}:
                    raise ValueError('invalid numerical witness fields')
                count, argmax = witness['count'], witness['verify_argmax']
                capture._count(count)
                capture._count(argmax)
                if not 1 <= count <= 1_000_000 or argmax >= count:
                    raise ValueError('invalid witness vocabulary or argmax')
                peak, ss = witness['max_abs'], witness['sum_squared']
                if any(type(x) not in (int, float) or not math.isfinite(x) or x < 0 for x in (peak, ss)):
                    raise ValueError('invalid numerical moments')
                # Rounding tolerance scales with the reported moment, never a
                # fixed absolute allowance that could hide tiny divergences.
                if not math.isfinite(peak * peak) or not peak * peak <= ss * (1 + 1e-12):
                    raise ValueError('numerical moments contradict maximum')
                if ss > count * peak * peak * (1 + 1e-12):
                    raise ValueError('numerical moments exceed coordinate bound')
                max_abs = max(max_abs, peak)
                squared.append(ss)
                counts.append(count)
            else:
                if 'witness' in row:
                    raise ValueError('mixed numerical encoding')
                verify, serial = row['verify'], row['serial']
                if not isinstance(verify, list) or not verify or not isinstance(serial, list) or len(verify) != len(serial):
                    raise ValueError('logit vector shape mismatch')
                count = len(verify)
                for left, right in zip(verify, serial):
                    if any(type(v) not in (int, float) or not math.isfinite(v) for v in (left, right)):
                        raise ValueError('nonfinite native logit')
                    delta = abs(left - right)
                    if not math.isfinite(delta) or not math.isfinite(delta * delta):
                        raise ValueError('native logit difference overflow')
                    max_abs = max(max_abs, delta)
                    squared.append(delta * delta)
                counts.append(count)
                argmax = max(range(count), key=verify.__getitem__)
            row_argmax = argmax
            if vocab is None:
                vocab = count
            if count != vocab:
                raise ValueError('vocabulary shape drift')
            if any(token >= vocab for token in draft):
                raise ValueError('draft token outside vocabulary')
            # Validate the greedy prefix count against actual verify predictions.
            if position < len(draft):
                match = draft[position] == row_argmax
                if (position < accepted and not match) or (position == accepted and match):
                    raise ValueError('native accepted prefix contradicts verify logits')
        bonus_row = rows[accepted]
        bonus = (bonus_row['witness']['verify_argmax'] if encoding == 'full-vocabulary-moments-v1'
                 else max(range(vocab), key=bonus_row['verify'].__getitem__))
        next_prefix = rows[0]['verify_prefix'] + draft[:accepted] + [
            bonus]
    try:
        total_squared = math.fsum(squared)
    except OverflowError as exc:
        raise ValueError('native aggregate divergence overflow') from exc
    if not math.isfinite(total_squared):
        raise ValueError('native aggregate divergence overflow')
    return {'status': 'ok', 'positions': list(positions.values()),
            'accepted': sum(p['accepted'] for p in positions.values()),
            'drafted': sum(p['drafted'] for p in positions.values()),
            'numerical_divergence': {'max_abs': max_abs, 'rms': math.sqrt(total_squared / sum(counts))}}


def run_cell(plan_path, cell_id, output):
    output = Path(output).absolute()
    if output.exists():
        raise FileExistsError(output)
    artifacts = []
    value = {'status': 'invalid', 'error': 'native worker not executed'}
    try:
        plan, request = request_for(plan_path, cell_id)
        config = plan['native_worker']
        # Small executable identity check; source/library/model admission belongs
        # in preflight. Neither a path nor an echo proves native residency.
        from scripts.vidya.qwen4exp_quality_capture import stable_bytes_identity
        _, executable = stable_bytes_identity(Path(config['executable']))
        if executable['sha256'] != plan['binary_sha256']:
            raise ValueError('native executable digest mismatch')
        directory = output.with_suffix('.native')
        directory.mkdir(exist_ok=False)
        req, raw = directory / 'request.json', directory / 'trace.json'
        capture._exclusive(req, request)
        artifacts.append(req)
        command = [config['executable'], '--request', str(req), '--output', str(raw)]
        stdout, stderr = directory / 'stdout', directory / 'stderr'
        artifacts.extend((stdout, stderr))
        with stdout.open('xb') as out, stderr.open('xb') as err:
            try:
                result = subprocess.run(command, env=config['env'], stdout=out, stderr=err,
                                        timeout=config['timeout_s'], check=False)
                if result.returncode:
                    raise RuntimeError(f'native executable rc={result.returncode}')
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError('native executable timed out') from exc
        trace, _ = capture._read(raw)
        value = reduce_trace(trace, request)
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as exc:
        value = {'status': 'failed' if isinstance(exc, RuntimeError) else 'invalid', 'error': str(exc)}
    finally:
        if 'raw' in locals() and raw.exists():
            artifacts.append(raw)
    if 'request' in locals():
        value['request'] = request
    value['native_artifacts'] = [_identity(p) for p in artifacts]
    capture._exclusive(output, value)
    return value


def _identity(path):
    from scripts.vidya.qwen4exp_quality_capture import stable_bytes_identity
    return stable_bytes_identity(path)[1]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--cell-id', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    run_cell(args.plan, args.cell_id, args.output)
