#!/usr/bin/env python3
"""Execute a sealed sequential CAFE3 arm schedule inside one grant; no grading."""
import argparse
import json
import os
from pathlib import Path

import launch_context as context
import native_runner
import protocol_requests


def prepare(path, digest, result_path):
    # Row runtimes pass pathlib.Path; compare filesystem strings consistently
    # without resolving/normalizing away noncanonical spellings or symlinks.
    result_path = os.fspath(result_path)
    schedule = context.bound_json(dict(path=str(path), sha256=digest))
    context.require(set(schedule) == {'schema', 'protocol', 'launches'} and
                    schedule['schema'] == 'epyc.cafe3.schedule.v1', 'invalid schedule')
    protocol = context.bound_json(schedule['protocol'])
    arms = protocol['arms']
    widths = protocol['request_settings']['arm_widths']
    cap = widths['adaptive']
    context.require(type(cap) is int and 1 <= cap <= 64, 'positive adaptive cap required')
    expected = {'adaptive'} | {'static-' + str(w) for w in range(cap + 1)}
    context.require(isinstance(arms, list) and len(arms) == len(expected) and set(arms) == expected,
                    'all static widths zero through adaptive cap required')
    launches = schedule['launches']
    context.require(isinstance(launches, list) and len(launches) == len(arms), 'incomplete arm schedule')
    plans, outputs, inputs = [], [result_path], [str(path), schedule['protocol']['path']]
    baseline = None
    for arm, entry in zip(arms, launches):
        context.require(set(entry) == {'context', 'log', 'process', 'requests'}, 'invalid launch entry')
        reference = entry['context']
        manifest = context.bound_json(reference)
        context.require(manifest['arm'] == arm and manifest['protocol'] == schedule['protocol'],
                        'schedule arm/order/protocol mismatch')
        # Only per-process identity, arm and journal may vary. The same argv,
        # models, build, backend, placement and grant are mandatory for every arm.
        common = {k: v for k, v in manifest.items() if k not in ('arm', 'run', 'journal')}
        if baseline is None:
            baseline = common
        context.require(common == baseline, 'cross-arm launch context mismatch')
        context.require(all(p['manifest']['run'] != manifest['run'] for p in plans), 'duplicate run identity')
        plan = context.validate_launch_context(reference['path'], reference['sha256'], manifest['argv'])
        protocol_requests.prepare(plan)
        plans.append(dict(entry=entry, manifest=manifest))
        outputs.extend([entry['log'], entry['process'], entry['requests'], manifest['journal']])
        inputs.extend([reference['path'], manifest['prepared']['path'], manifest['build']['path'],
                       manifest['grant']['path'], manifest['corpus']['path'], manifest['argv'][0]])
        inputs.extend(item['path'] for item in plan['models'].values())
    context.require(len(outputs) == len(set(outputs)), 'colliding output paths')
    for value in outputs:
        output = Path(value)
        context.require(output.is_absolute() and str(output) == value and
                        output.parent.resolve(strict=True) == output.parent and
                        not output.exists() and not output.is_symlink() and value not in inputs,
                        'output must be new canonical path outside inputs')
    return schedule, plans


def execute(path, digest, result_path):
    # Preflight every arm before any model process starts. Each supervisor also
    # revalidates its context at the actual launch boundary (STOP/deadline etc.).
    schedule, plans = prepare(path, digest, result_path)
    with Path(result_path).open('x') as stream:
        def write(record):
            stream.write(json.dumps(record, allow_nan=False) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        write(dict(schema='epyc.cafe3.schedule-capture.v1', status='UNASSESSED',
                   event='start', schedule=dict(path=str(path), sha256=digest),
                   protocol=schedule['protocol'], arms=[p['manifest']['arm'] for p in plans],
                   ordering='sequential-whole-arm'))
        for plan in plans:
            entry, manifest = plan['entry'], plan['manifest']
            reference = entry['context']
            try:
                record = native_runner.run(reference['path'], reference['sha256'], manifest['argv'],
                                           entry['log'], entry['process'], entry['requests'])
                rc = native_runner.exit_code(record)
                # A normal server exit without completed requests is insufficient.
                context.require(rc == 0 and record['cutoff'] == 'protocol-complete' and
                                record['request_rc'] == 0 and record['child_reaped'] is True and
                                record['requester_reaped'] is True, 'arm protocol incomplete')
                captures = {key: dict(path=entry[key], sha256=context.sha256(entry[key]))
                            for key in ('log', 'process', 'requests')}
                # Static arms intentionally have no adaptive round journal.
                if manifest['arm'] == 'adaptive':
                    journal = context.canonical(manifest['journal'])
                    context.require(journal.stat().st_size > 0, 'missing adaptive rounds')
                    captures['journal'] = dict(path=str(journal), sha256=context.sha256(journal))
                write(dict(event='arm-complete', status='UNASSESSED', arm=manifest['arm'],
                           context=reference, captures=captures))
            except Exception as error:
                write(dict(event='failed', status='UNASSESSED', arm=manifest['arm'],
                           context=reference, error=type(error).__name__ + ': ' + str(error)))
                raise
        write(dict(event='complete', status='UNASSESSED', arms=len(plans)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('schedule')
    parser.add_argument('sha256')
    parser.add_argument('result', help='exclusive schedule-capture JSONL')
    args = parser.parse_args()
    execute(args.schedule, args.sha256, args.result)


if __name__ == '__main__':
    main()
