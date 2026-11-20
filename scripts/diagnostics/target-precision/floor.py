"""Repeated native fresh-block/serial controls. Execute only in admitted rows.

Uses the same native executable and runtime observer as matrix cells, without
requiring a floor receipt before the floor itself has been measured.
"""
import argparse
import importlib.util
import math
from pathlib import Path


def _module(name):
    spec = importlib.util.spec_from_file_location('precision_floor_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_requests(plan, requests, read):
    worker = _module('worker')
    if not isinstance(requests, list) or len(requests) < 2:
        raise ValueError('floor requires repeated requests')
    prompts, identity = read(plan['native_worker']['prompt_manifest'])
    if identity['sha256'] != plan['prompt_manifest_sha256']:
        raise ValueError('floor prompt manifest mismatch')
    ref = plan['admission']['holdout']
    holdout, identity = read(ref['path'])
    if identity['sha256'] != ref['sha256'] or identity['sha256'] != plan['holdout_sha256']:
        raise ValueError('floor holdout digest mismatch')
    seen, baseline = set(), None
    for request in requests:
        case = request['case']
        repetition = case['repetition']
        if type(repetition) is not int or repetition < 0 or repetition in seen:
            raise ValueError('floor duplicate/invalid repetition')
        seen.add(repetition)
        comparable = {k: v for k, v in case.items() if k not in ('repetition', 'cell_id')}
        if baseline is None:
            baseline = comparable
        if comparable != baseline:
            raise ValueError('floor repeated case/settings drift')
        if (request['schema'] != worker.SCHEMA
                or request['trace_semantics'] != 'greedy_prefix_acceptance_and_same_prefix_verify_vs_serial_logits'
                or request['runtime'] != plan['native_worker']
                or request['settings'] != {k: plan[k] for k in worker.capture.SHARED}
                or plan['verification'].get('replay') != 'fresh-block-serial-v1'):
            raise ValueError('floor native profile/settings mismatch')
        pair = [case['prompt_id'], case['seed']]
        if pair not in holdout['calibration'] or pair in holdout['evaluation']:
            raise ValueError('floor requires disjoint calibration case')
        if (not request['prompt'] or request['prompt'] != prompts['prompts'][case['prompt_id']]
                or not any(c['target_quant'] == case['target_quant'] and
                           c['target_sha256'] == case['target_sha256'] for c in plan['cells'])):
            raise ValueError('floor prompt/target binding mismatch')


def summarize(plan, references, read):
    """Recompute a control from original traces and runtime observations."""
    worker = _module('worker')
    if not isinstance(references, list) or len(references) < 2:
        raise ValueError('floor requires repeated originals')
    seen, settings, case, prompt = set(), None, None, None
    coordinates, squared, maximum = 0, [], 0.0
    requests = []
    for ref in references:
        if set(ref) != {'trace', 'runtime'}:
            raise ValueError('floor original references required')
        originals = []
        for key in ('trace', 'runtime'):
            value = ref[key]
            if set(value) != {'path', 'sha256'} or not Path(value['path']).is_absolute():
                raise ValueError('floor absolute original reference required')
            native, identity = read(value['path'])
            if identity['sha256'] != value['sha256']:
                raise ValueError('floor original digest mismatch')
            originals.append(native)
        trace, observed = originals
        request = trace['request']
        requests.append(request)
        current = request['case']
        repetition = current['repetition']
        if type(repetition) is not int or repetition < 0 or repetition in seen:
            raise ValueError('floor duplicate/invalid repetition')
        seen.add(repetition)
        comparable = {k: v for k, v in current.items() if k not in ('repetition', 'cell_id')}
        if case is None:
            case, settings, prompt = comparable, request['settings'], request['prompt']
        if comparable != case or request['settings'] != settings or request['prompt'] != prompt:
            raise ValueError('floor repeated case/settings drift')
        for key in worker.capture.SHARED:
            if settings[key] != plan[key]:
                raise ValueError('floor plan setting mismatch: ' + key)
        if (request['schema'] != worker.SCHEMA or request['runtime'] != plan['native_worker']
                or request['trace_semantics'] != 'greedy_prefix_acceptance_and_same_prefix_verify_vs_serial_logits'
                or settings['verification'].get('replay') != 'fresh-block-serial-v1'):
            raise ValueError('floor native profile mismatch')
        worker.runtime.validate(observed, plan, request)
        reduced = worker.reduce_trace(trace, request)
        if reduced['status'] != 'ok' or trace.get('numerical_encoding') != 'full-vocabulary-moments-v1':
            raise ValueError('floor requires successful full-vocabulary moments')
        if len(trace['blocks']) != plan['verification']['blocks']:
            raise ValueError('floor block coverage mismatch')
        for block in trace['blocks']:
            for row in block['logits']:
                witness = row['witness']
                coordinates += witness['count']
                squared.append(witness['sum_squared'])
                maximum = max(maximum, witness['max_abs'])
    validate_requests(plan, requests, read)
    total = math.fsum(squared)
    if not math.isfinite(total):
        raise ValueError('floor squared sum overflow')
    # Calibration identity comes from the original traces, never evaluation cells.
    holdout_ref = plan['admission']['holdout']
    holdout, identity = read(holdout_ref['path'])
    if identity['sha256'] != holdout_ref['sha256']:
        raise ValueError('floor holdout digest mismatch')
    pair = [case['prompt_id'], case['seed']]
    if pair not in holdout['calibration'] or pair in holdout['evaluation']:
        raise ValueError('floor requires disjoint calibration case')
    return dict(target_quant=case['target_quant'], target_sha256=case['target_sha256'],
                comparison='fresh-block-vs-serial-same-prefix', repetitions=len(seen),
                coordinates=coordinates, max_abs=maximum, rms=math.sqrt(total / coordinates),
                trace_outputs=references)


def produce(plan, requests, directory):
    """Run predeclared repeated requests, retaining failed runs without a receipt."""
    worker = _module('worker')
    capture = worker.capture
    capture._plan(plan)
    config = plan['native_worker']
    if (set(config) != {'executable', 'env', 'prompt_manifest', 'targets', 'drafter', 'timeout_s'}
            or not isinstance(config['executable'], str) or not Path(config['executable']).is_absolute()
            or type(config['timeout_s']) not in (int, float)
            or not math.isfinite(config['timeout_s']) or config['timeout_s'] <= 0
            or not isinstance(config['env'], dict)
            or any(not isinstance(k, str) or not isinstance(v, str) for k, v in config['env'].items())):
        raise ValueError('floor native configuration invalid')
    if plan['origin'] != 'native_claimed':
        raise ValueError('floor requires native_claimed plan')
    _module('admission').admit(plan, capture._read, require_floor=False)
    validate_requests(plan, requests, capture._read)
    # These small-byte checks never read model weights.
    if worker._identity(Path(plan['native_worker']['executable']))['sha256'] != plan['binary_sha256']:
        raise ValueError('floor executable digest mismatch')
    directory = Path(directory).absolute()
    directory.mkdir(exist_ok=False)
    refs = []
    for i, request in enumerate(requests):
        req, raw, proof = (directory / f'{i}-{name}.json' for name in ('request', 'trace', 'runtime'))
        capture._exclusive(req, request)
        config = plan['native_worker']
        with (directory / f'{i}.stdout').open('xb') as out, (directory / f'{i}.stderr').open('xb') as err:
            observed = worker.runtime.execute(
                [config['executable'], '--request', str(req), '--output', str(raw)],
                config['env'], out, err, config['timeout_s'], plan, request)
        capture._exclusive(proof, observed)
        worker.runtime.validate(observed, plan, request)
        refs.append({key: {k: worker._identity(path)[k] for k in ('path', 'sha256')}
                     for key, path in (('trace', raw), ('runtime', proof))})
    control = summarize(plan, refs, capture._read)
    output = directory / 'control.json'
    capture._exclusive(output, control)
    return {**control, 'native_output': {k: worker._identity(output)[k] for k in ('path', 'sha256')}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--requests', required=True, help='JSON object with requests array for one quant')
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    capture = _module('capture')
    plan, _ = capture._read(args.plan)
    requests, _ = capture._read(args.requests)
    control = produce(plan, requests['requests'], args.output_dir)
    capture._exclusive(Path(args.output_dir) / 'receipt-control.json', control)
