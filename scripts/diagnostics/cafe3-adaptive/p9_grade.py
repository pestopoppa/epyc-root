#!/usr/bin/env python3
"""Offline, fail-closed CAFE3 P9 assessment over sealed whole-arm captures.

No live grant check, model execution, model hashing, or new belief-grade ladder.
Malformed/missing evidence refuses assessment; valid negative outcomes fail.
"""
import argparse
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

import launch_context as context
import protocol_requests

POLICY = dict(schema='epyc.cafe3.p9-policy.v1', metric='aggregate-request-wall-tokens-per-second',
              minimum_gain_percent=1, identity='all-tokens-vs-static-0',
              recovery='post-exploration-zero-to-positive-probe', recovery_max_rounds=128)


def need(value, message):
    context.require(value, message)


def integer(value, low=0):
    return type(value) is int and value >= low


def number(value, low=0):
    return type(value) in (int, float) and math.isfinite(value) and value > low


def jsonl(reference):
    path = context.canonical(reference['path'])
    data = path.read_bytes()
    need(hashlib.sha256(data).hexdigest() == context.hex_digest(reference['sha256']), 'capture digest mismatch')
    need(data.endswith(b'\n'), 'partial journal tail')
    lines = data.splitlines()
    need(lines and all(line.strip() for line in lines), 'empty journal record')
    return [context.parse_json(line) for line in lines]


def rounds(rows, manifest, digest, requests, cap):
    """Partition synchronous native writes into disjoint sequential HTTP windows."""
    groups = [[] for _ in requests]
    previous_time = 0
    for ordinal, row in enumerate(rows, 1):
        need(row['schema'] == 'epyc.cafe3.round.v1' and row['run'] == manifest['run'] and
             row['context_sha256'] == digest, 'round custody mismatch')
        need(type(row['ordinal']) is int and row['ordinal'] == ordinal, 'journal ordinal gap')
        need(integer(row['unix_ns'], 1) and row['unix_ns'] >= previous_time, 'round clock regression')
        previous_time = row['unix_ns']
        for key in ('request', 'request_epoch', 'sequence', 'round', 'ticket', 'selected_width', 'actual_width', 'accepted'):
            need(integer(row[key], 1 if key in ('request_epoch', 'round', 'ticket') else 0), 'invalid round ' + key)
        need(row['implementation'] in ('mtp', 'dflash', 'dflash2') and
             row['selected_width'] == row['actual_width'] <= cap and
             row['accepted'] <= row['actual_width'] and type(row['probe']) is bool and
             number(row['elapsed_us']) and type(row['position_zero_probability']) in (int, float) and
             math.isfinite(row['position_zero_probability']) and 0 <= row['position_zero_probability'] <= 1,
             'invalid round measurement')
        matches = [i for i, request in enumerate(requests)
                   if request['unix_started_ns'] <= row['unix_ns'] <= request['unix_ended_ns']]
        need(len(matches) == 1, 'round outside unique request window')
        groups[matches[0]].append(row)
    identities, recoveries, violations = set(), 0, 0
    for group in groups:
        need(group, 'request lacks round evidence')
        key = tuple(group[0][k] for k in ('request', 'request_epoch', 'sequence'))
        need(key not in identities, 'reused native request identity')
        identities.add(key)
        seen, zero_round, last_ticket = set(), None, 0
        recovered, overdue = False, False
        for index, row in enumerate(group, 1):
            need(tuple(row[k] for k in ('request', 'request_epoch', 'sequence')) == key and
                 row['round'] == index and row['ticket'] > last_ticket and
                 row['implementation'] == group[0]['implementation'], 'request round discontinuity')
            last_ticket = row['ticket']
            # Initial mandatory width 0 -> 1 exploration is not recovery.
            if row['selected_width'] == 0 and not row['probe'] and len(seen) == cap + 1 and zero_round is None:
                zero_round = index
            if zero_round is not None and index - zero_round > POLICY['recovery_max_rounds']:
                overdue = True
            if zero_round is not None and row['selected_width'] > 0 and row['probe']:
                if index - zero_round <= POLICY['recovery_max_rounds']:
                    recovered = True
                zero_round = None
            seen.add(row['selected_width'])
        recoveries += recovered
        violations += overdue
    return recoveries, violations


def assess(schedule_ref, capture_ref):
    schedule = context.bound_json(schedule_ref)
    need(schedule['schema'] == 'epyc.cafe3.schedule.v1', 'schedule schema')
    protocol = context.bound_json(schedule['protocol'])
    need(protocol.get('p9_policy') == POLICY, 'missing or changed predeclared P9 policy')
    settings, arms = protocol['request_settings'], protocol['arms']
    cap = settings['arm_widths']['adaptive']
    need(integer(cap, 1) and cap <= 64, 'adaptive cap')
    expected = {'adaptive'} | {'static-' + str(w) for w in range(cap + 1)}
    need(len(arms) == len(expected) and set(arms) == expected and
         len(schedule['launches']) == len(arms), 'incomplete static coverage')
    need(integer(protocol['repetitions'], 1), 'repetitions')
    capture = jsonl(capture_ref)
    need(len(capture) == len(arms) + 2 and capture[0] == dict(
        schema='epyc.cafe3.schedule-capture.v1', status='UNASSESSED', event='start',
        schedule=schedule_ref, protocol=schedule['protocol'], arms=arms, ordering='sequential-whole-arm') and
        capture[-1] == dict(event='complete', status='UNASSESSED', arms=len(arms)), 'partial schedule')
    common, all_requests, totals, run_ids, outputs = None, {}, {}, set(), set()
    previous_end = None
    recovery_count, recovery_violations, backend = 0, 0, None
    for arm, entry, record in zip(arms, schedule['launches'], capture[1:-1]):
        manifest = context.bound_json(entry['context'])
        need(manifest['schema'] == 'epyc.cafe3.launch-context.v1' and manifest['arm'] == arm and
             manifest['protocol'] == schedule['protocol'], 'context arm/protocol mismatch')
        baseline = {k: v for k, v in manifest.items() if k not in ('arm', 'run', 'journal')}
        if common is None:
            common = baseline
            build, executable = context.build_receipt(manifest['build'], manifest['backend'])
            need(build['base'] == 'ffc1bac82eeca6f9099e1ccd9ba49703c460a115', 'wrong production base')
            prepared = context.bound_json(manifest['prepared'])
            need(prepared['schema'] == 'epyc.cafe3.prepared.v1' and
                 set(prepared['models']) == {'target', 'draft'} and
                 prepared['corpus'] == manifest['corpus'], 'prepared input mismatch')
            for item in prepared['models'].values():
                context.hex_digest(item['sha256'])
                need(context.file_identity(item['path']) == item['identity'], 'model identity drift')
            grant = context.bound_file(manifest['grant'])
            need(str(grant) == '/mnt/raid0/llm/tmp/compute-flags/grants/' + manifest['row'] + '.grant',
                 'unofficial grant')
            fields = {}
            for token in grant.read_text().split():
                key, value = token.split('=', 1)
                need(key not in fields, 'duplicate grant field')
                fields[key] = value
            epoch = lambda v: datetime.strptime(v, '%Y-%m-%dT%H:%MZ').replace(tzinfo=timezone.utc).timestamp()
            grant_start, grant_end = epoch(fields['start']), epoch(fields['end'])
            need(all(manifest['placement'][k] == fields[k] for k in ('regions', 'holds')), 'grant placement')
        need(baseline == common, 'cross-arm context drift')
        backend = manifest['backend']
        argv, placement = manifest['argv'], manifest['placement']
        need(integer(placement['threads'], 1), 'invalid threads')
        cpus = context.cpu_set(placement['cpus'])
        grant_cpus = fields.get('cpus', ','.join(v for v in fields['regions'].split(',') if v != 'mi210_0'))
        need(cpus == context.cpu_set(grant_cpus), 'grant CPUs mismatch')
        for role, flag in (('target', '-m'), ('draft', '--model-draft')):
            need(argv.count(flag) == 1 and argv[argv.index(flag)+1] == prepared['models'][role]['path'],
                 'model argv mismatch')
        for flag in ('-t', '-tb'):
            need(argv.count(flag) == 1 and argv[argv.index(flag)+1] == str(placement['threads']), 'thread argv mismatch')
        for flag in ('-ngl', '--gpu-layers-draft'):
            need(argv.count(flag) == 1 and
                 (int(argv[argv.index(flag)+1]) > 0 if backend == 'hip' else argv[argv.index(flag)+1] == '0'),
                 'backend argv mismatch')
        need(manifest['run'] not in run_ids, 'duplicate run')
        run_ids.add(manifest['run'])
        need(record['event'] == 'arm-complete' and record['status'] == 'UNASSESSED' and
             record['arm'] == arm and record['context'] == entry['context'], 'arm capture mismatch')
        refs = record['captures']
        need(set(refs) == ({'log', 'process', 'requests', 'journal'} if arm == 'adaptive' else
                           {'log', 'process', 'requests'}), 'capture set')
        for key, ref in refs.items():
            need(ref['path'] == (manifest['journal'] if key == 'journal' else entry[key]) and
                 ref['path'] not in outputs, 'capture path collision/mismatch')
            outputs.add(ref['path'])
            context.bound_file(ref)
        process = context.bound_json(refs['process'])
        need(process['schema'] == 'epyc.cafe3.process-capture.v1' and process['status'] == 'UNASSESSED' and
             process['context_sha256'] == entry['context']['sha256'] and process['argv'] == manifest['argv'] and
             process['argv'][0] == str(executable) and process['cutoff'] == 'protocol-complete' and
             type(process['request_rc']) is int and process['request_rc'] == 0 and
             process['child_reaped'] is True and process['requester_reaped'] is True and
             process['log'] == entry['log'] and process['requests_path'] == entry['requests'], 'incomplete process')
        need(number(process['started']) and number(process['ended']) and
             grant_start <= process['started'] < process['ended'] <= grant_end and
             (previous_end is None or previous_end <= process['started']), 'process window/order')
        previous_end = process['ended']
        expected_env = dict(LD_LIBRARY_PATH=str(executable.parent), OMP_NUM_THREADS=str(placement['threads']),
                            GGML_IQK='1', LLAMA_CAFE3_ADAPTIVE='1' if arm == 'adaptive' else '0',
                            LLAMA_CAFE3_RUN=manifest['run'], LLAMA_CAFE3_CONTEXT_SHA256=entry['context']['sha256'],
                            LLAMA_CAFE3_JOURNAL=manifest['journal'], **manifest['device_env'])
        if backend == 'cpu':
            need(manifest['device_env'] == {} and 'gpu-quiet' not in fields['holds'].split(','), 'CPU device placement')
            expected_env.update(HIP_VISIBLE_DEVICES='-1', ROCR_VISIBLE_DEVICES='-1', CUDA_VISIBLE_DEVICES='-1')
        else:
            need(backend == 'hip' and manifest['device_env'] == dict(HIP_VISIBLE_DEVICES='0', ROCR_VISIBLE_DEVICES='0') and
                 'gpu-quiet' in fields['holds'].split(','), 'HIP device placement')
        need(process['env'] == expected_env, 'process environment mismatch')
        # Runtime mappings must overlap the process and use the bound build.
        needed = {p for p in build['files'] if Path(p).name.startswith(('libllama', 'libggml'))}
        need(needed and any(number(s['at']) and process['started'] <= s['at'] <= process['ended'] and
                           needed <= {line.split()[-1] for line in s['maps'].splitlines() if line.split()}
                           for s in process['mapping_samples']), 'missing runtime library mappings')
        plan = dict(argv=manifest['argv'], arm=arm, corpus=manifest['corpus'], protocol=manifest['protocol'])
        _, _, prompts, _ = protocol_requests.prepare(plan)
        requests = jsonl(refs['requests'])
        order = [(rep, prompt) for rep in range(protocol['repetitions']) for prompt in prompts]
        need(len(requests) == len(order), 'incomplete request coverage')
        last_ns, tokens, elapsed = 0, 0, 0
        for request, (rep, prompt) in zip(requests, order):
            need(request['schema'] == 'epyc.cafe3.request-capture.v1' and request['status'] == 'UNASSESSED' and
                 request['context_sha256'] == entry['context']['sha256'] and request['protocol'] == schedule['protocol'] and
                 request['arm'] == arm and type(request['repetition']) is int and
                 request['repetition'] == rep and request['prompt_id'] == prompt['id'], 'request custody/order')
            payload = dict(prompt=prompt['prompt'], n_predict=settings['n_predict'], seed=settings['seed'],
                           temperature=0, stream=False, return_tokens=True, cache_prompt=False,
                           **{'speculative.n_max': settings['arm_widths'][arm]})
            need(json.dumps(request['payload'], sort_keys=True, allow_nan=False) ==
                 json.dumps(payload, sort_keys=True, allow_nan=False), 'request payload mismatch')
            response = request['response']
            need(response['stop'] is True and response['truncated'] is False and
                 isinstance(response['tokens'], list) and 0 < len(response['tokens']) <= settings['n_predict'] and
                 all(integer(t) for t in response['tokens']) and isinstance(response['timings'], dict), 'invalid response')
            need(integer(request['elapsed_ns'], 1) and integer(request['unix_started_ns'], 1) and
                 integer(request['unix_ended_ns'], 1) and
                 last_ns < request['unix_started_ns'] < request['unix_ended_ns'] and
                 process['started'] <= request['unix_started_ns'] / 1e9 <
                 request['unix_ended_ns'] / 1e9 <= process['ended'], 'request time window')
            wall_ns = request['unix_ended_ns'] - request['unix_started_ns']
            need(abs(wall_ns - request['elapsed_ns']) <= max(1000000, request['elapsed_ns'] // 100),
                 'wall/monotonic clock disagreement')
            last_ns = request['unix_ended_ns']
            tokens += len(response['tokens'])
            elapsed += request['elapsed_ns']
        all_requests[arm], totals[arm] = requests, dict(tokens=tokens, elapsed_ns=elapsed)
        if arm == 'adaptive':
            recovery_count, recovery_violations = rounds(jsonl(refs['journal']), manifest, entry['context']['sha256'], requests, cap)
    reference = [r['response']['tokens'] for r in all_requests['static-0']]
    identical = all([r['response']['tokens'] for r in records] == reference for records in all_requests.values())
    # Token counts are identical on the pass path; compare exact integer ratios.
    static = max((a for a in arms if a != 'adaptive'),
                 key=lambda a: Fraction(totals[a]['tokens'], totals[a]['elapsed_ns']))
    gain_ratio = Fraction(totals['adaptive']['tokens'] * totals[static]['elapsed_ns'],
                          totals[static]['tokens'] * totals['adaptive']['elapsed_ns'])
    gain_pass = gain_ratio >= Fraction(101, 100)
    verdict = 'pass' if identical and gain_pass and recovery_count else 'fail'
    reason = 'P9 thresholds met' if verdict == 'pass' else 'identity or speed threshold failed'
    if identical and gain_pass and not recovery_count:
        verdict, reason = 'inconclusive', 'no post-exploration zero recovery observed'
    if recovery_violations:
        verdict, reason = 'fail', 'zero recovery exceeded predeclared round bound'
    if backend == 'hip' and verdict != 'fail':
        verdict, reason = 'inconclusive', 'HIP captures lack overlapping VRAM/KFD residency evidence'
    return dict(schema='epyc.cafe3.p9-assessment.v1', verdict=verdict, reason=reason,
                schedule=schedule_ref, capture=capture_ref, policy=POLICY, totals=totals,
                identity_percent=100 if identical else None, best_static=static,
                gain_percent=float(100 * (gain_ratio - 1)),
                grader_sha256=context.sha256(__file__),
                recovery_requests=recovery_count, recovery_violations=recovery_violations, timing='aggregate request wall; sequential whole arms; descriptive only')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('schedule')
    parser.add_argument('schedule_sha256')
    parser.add_argument('capture')
    parser.add_argument('capture_sha256')
    parser.add_argument('output')
    args = parser.parse_args()
    try:
        result = assess(dict(path=args.schedule, sha256=args.schedule_sha256),
                        dict(path=args.capture, sha256=args.capture_sha256))
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        parser.exit(1, 'CAFE3 P9 REFUSED: ' + str(error) + '\n')
    with Path(args.output).open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return 0 if result['verdict'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
