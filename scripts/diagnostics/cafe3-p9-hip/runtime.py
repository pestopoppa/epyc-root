#!/usr/bin/env python3
"""HIP P9 row boundary: presealed inputs, assigned-grant binding, native capture."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'cafe3-adaptive'))
import launch_context as context
import multi_arm
import p9_grade
import protocol_requests
import native_smoke


def reference(path):
    return dict(path=str(Path(path).resolve(strict=True)), sha256=context.sha256(path))


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    return reference(path)


def inputs(digest):
    inventory = context.bound_json(dict(path=str(ROOT / 'inputs.json'), sha256=digest))
    context.require(inventory['schema'] == 'epyc.cafe3.p9-inputs.v1', 'input schema')
    for path, expected in inventory['runtime'].items():
        context.bound_file(dict(path=path, sha256=expected))
    prepared = context.bound_json(inventory['prepared'])
    context.require(prepared['schema'] == 'epyc.cafe3.prepared.v1' and
                    set(prepared['models']) == {'target', 'draft'}, 'prepared model set')
    for item in [*prepared['models'].values(), prepared['corpus']]:
        context.hex_digest(item['sha256'])
        context.require(item['identity'] == context.file_identity(item['path']), 'prepared input drift')
    protocol = context.bound_json(inventory['protocol'])
    context.require(protocol['corpus'] == prepared['corpus'] and protocol['p9_policy'] == p9_grade.POLICY,
                    'protocol binding')
    widths = protocol['request_settings']['arm_widths']
    cap = widths['adaptive']
    context.require(type(cap) is int and 1 <= cap <= 7 and len(protocol['arms']) == cap + 2 and
                    set(protocol['arms']) == {'adaptive'} | {'static-' + str(w) for w in range(cap + 1)},
                    'complete bounded DFlash2 width schedule required')
    _, executable = context.build_receipt(inventory['build'], 'hip')
    # Exercise actual corpus/settings parser without models or grant fabrication.
    for arm in protocol['arms']:
        protocol_requests.prepare(dict(protocol=inventory['protocol'], corpus=prepared['corpus'],
                                       arm=arm, argv=['--host', '127.0.0.1', '--port', str(inventory['port'])]))
    return inventory, prepared, protocol, executable


def seal_schedule(inventory, prepared, protocol, executable, run):
    row = inventory['row']
    context.require(os.environ['FILLER_ID'] == row and os.environ.get('FILLER_DRYRUN', '0') == '0',
                    'native execution requires matching scheduled row')
    grant_path = Path('/mnt/raid0/llm/tmp/compute-flags/grants') / (row + '.grant')
    grant = reference(grant_path)
    fields = {}
    for token in grant_path.read_text().split():
        key, value = token.split('=', 1)
        context.require(key not in fields, 'duplicate grant field')
        fields[key] = value
    placement = dict(cpus=os.environ['FILLER_CPUS'], threads=int(os.environ['FILLER_THREADS']),
                     regions=fields['regions'], holds=fields['holds'])
    # All arms share the exact command. Only request widths/opt-in vary.
    argv = [str(executable), '-m', prepared['models']['target']['path'],
            '--model-draft', prepared['models']['draft']['path'],
            '-t', str(placement['threads']), '-tb', str(placement['threads']),
            '-ngl', '999', '--gpu-layers-draft', '999', '--host', '127.0.0.1',
            '--port', str(inventory['port']), '-c', '4096', '-np', '1',
            '--spec-type', 'draft-dflash', '--spec-draft-n-max', str(protocol['request_settings']['arm_widths']['adaptive']),
            '--spec-draft-n-min', '0', '--spec-draft-p-min', '0', '-fa', 'off']
    launches = []
    for arm in protocol['arms']:
        manifest = dict(schema='epyc.cafe3.launch-context.v1', run=run.name + '-' + arm,
                        row=row, backend='hip', arm=arm, argv=argv, build=inventory['build'],
                        prepared=inventory['prepared'], corpus=prepared['corpus'], protocol=inventory['protocol'],
                        grant=grant, placement=placement, device_env={'HIP_VISIBLE_DEVICES':'0', 'ROCR_VISIBLE_DEVICES':'0'}, journal=str(run / (arm + '-rounds.jsonl')))
        ref = write(run / (arm + '-context.json'), manifest)
        launches.append(dict(context=ref, log=str(run / (arm + '.log')),
                             process=str(run / (arm + '-process.json')), requests=str(run / (arm + '-requests.jsonl'))))
    return write(run / 'schedule.json', dict(schema='epyc.cafe3.schedule.v1',
                                            protocol=inventory['protocol'], launches=launches))


def run(digest):
    inventory, prepared, protocol, executable = inputs(digest)
    if os.environ.get('FILLER_DRYRUN') == '1':
        record = native_smoke.run(inventory, prepared, executable)
        write(os.environ['FILLER_DRYRUN_RESULT_PATH'], dict(
            schema='epyc.cafe3.p9-smoke.v2', inventory_sha256=digest,
            build=inventory['build'], executable=reference(executable), **record))
        return
    (ROOT / 'runs').mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='native-', dir=ROOT / 'runs'))
    schedule = seal_schedule(inventory, prepared, protocol, executable, work)
    capture_path = work / 'schedule-capture.jsonl'
    multi_arm.execute(schedule['path'], schedule['sha256'], capture_path)
    capture = reference(capture_path)
    assessment = p9_grade.assess(schedule, capture)
    assessment_ref = write(work / 'assessment.json', assessment)
    # Valid negative/inconclusive P9 is a completed experiment, not qualification failure.
    write(ROOT / 'RESULT.json', dict(schema='epyc.cafe3.p9-result.v1', inventory_sha256=digest,
          schedule=schedule, capture=capture, assessment=assessment_ref, verdict=assessment['verdict']))


def check(digest, smoke=False):
    path = Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else ROOT / 'RESULT.json'
    result = context.load(path)
    context.require(result['inventory_sha256'] == digest, 'result input binding')
    if smoke:
        inventory = context.bound_json(dict(path=str(ROOT / 'inputs.json'), sha256=digest))
        context.require(result['schema'] == 'epyc.cafe3.p9-smoke.v2' and
                        result['build'] == inventory['build'], 'smoke qualification')
        native_smoke.validate(result)
        context.bound_file(result['executable'])
    else:
        context.require(result['schema'] == 'epyc.cafe3.p9-result.v1', 'result schema')
        assessment = context.bound_json(result['assessment'])
        context.require(assessment['schema'] == 'epyc.cafe3.p9-assessment.v1' and
                        assessment['verdict'] in ('pass', 'fail', 'inconclusive') and
                        assessment['verdict'] == result['verdict'] and
                        assessment['schedule'] == result['schedule'] and assessment['capture'] == result['capture'],
                        'assessment binding')
        context.bound_file(result['schedule'])
        context.bound_file(result['capture'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('inputs', 'run', 'check', 'predicate'))
    parser.add_argument('inventory_sha256')
    args = parser.parse_args()
    if args.action == 'inputs':
        inputs(args.inventory_sha256)
    elif args.action == 'run':
        run(args.inventory_sha256)
    else:
        check(args.inventory_sha256, args.action == 'predicate' or os.environ.get('FILLER_DRYRUN') == '1')


if __name__ == '__main__':
    main()
