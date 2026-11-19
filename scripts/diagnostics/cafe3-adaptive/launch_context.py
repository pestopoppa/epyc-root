#!/usr/bin/env python3
"""Validate a retained CAFE3 context before native capture (never starts compute)."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import time


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def hex_digest(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value), 'invalid SHA256')
    return value


def canonical(value):
    path = Path(value)
    require(path.is_absolute() and str(path.resolve(strict=True)) == value, 'noncanonical path')
    require(path.is_file(), 'not a regular file')
    return path


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def load(path):
    return parse_json(Path(path).read_bytes())


def parse_json(data):
    return json.loads(data, object_pairs_hook=unique_object,
                      parse_constant=lambda value: require(False, 'nonfinite JSON: ' + value))


def bound_file(reference):
    path = canonical(reference['path'])
    require(sha256(path) == hex_digest(reference['sha256']), 'file digest mismatch: ' + str(path))
    return path


def bound_json(reference):
    # Parse exactly the bytes whose digest was checked, not a second path read.
    path = canonical(reference['path'])
    data = path.read_bytes()
    require(hashlib.sha256(data).hexdigest() == hex_digest(reference['sha256']), 'file digest mismatch: ' + str(path))
    return parse_json(data)


def file_identity(path):
    """Compare prehashed inputs without rereading model weights inside a grant."""
    info = canonical(path).stat()
    require(stat.S_ISREG(info.st_mode), 'input is not regular')
    return dict(device=info.st_dev, inode=info.st_ino, size=info.st_size,
                mtime_ns=info.st_mtime_ns, ctime_ns=info.st_ctime_ns)


def cpu_set(value):
    require(isinstance(value, str) and re.fullmatch(r'\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*', value), 'invalid CPU list')
    cpus = set()
    for part in value.split(','):
        ends = [int(x) for x in part.split('-')]
        lo, hi = ends[0], ends[-1]
        require(0 <= lo <= hi < 4096, 'invalid CPU range')
        region = set(range(lo, hi + 1))
        require(not region & cpus, 'duplicate CPU')
        cpus |= region
    return cpus


def build_receipt(reference, backend):
    receipt = bound_json(reference)
    schemas = {'cpu': 'epyc.cafe3.build.v1', 'hip': 'epyc.cafe3.hip-build.v1'}
    require(backend in schemas and receipt['schema'] == schemas[backend]
            and receipt['mode'] == 'build', 'full matching backend build required')
    # Reuse the producer's source/marker/linkage/export validator. Never accept a
    # caller-supplied validator or execute code from the receipt's scratch tree.
    directory = 'cafe3-build' if backend == 'cpu' else 'cafe3-hip-build'
    source = Path(__file__).resolve().parent.parent / directory / 'driver.py'
    spec = importlib.util.spec_from_file_location('cafe3_launch_build', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Replacement packets have their own retained input inventory and runs.
    # Always execute the trusted repository validator, bound to this packet.
    module.D = canonical(reference['path']).parent
    module.validate(receipt)
    run = Path(receipt['run']).resolve(strict=True)
    executable = canonical(str(run / 'build/bin/llama-server'))
    for artifact in (executable, run / 'build/CMakeCache.txt', run / 'linkage.log'):
        name = str(artifact.resolve(strict=True))
        require(name in receipt['files'] and sha256(name) == receipt['files'][name], 'unbound build artifact')
    return receipt, executable


def validate_launch_context(manifest_path, expected_sha256, argv, *, environ=None, now=None, affinity=None):
    """Return exact argv and isolated child env; caller must use both unchanged.

    This is a launch precondition, not evidence of actual mappings, HIP residency,
    executed protocol, correctness or performance. Input preparation is separate.
    """
    env = os.environ if environ is None else environ
    now = time.time() if now is None else now
    affinity = set(os.sched_getaffinity(0)) if affinity is None else set(affinity)
    manifest = bound_json(dict(path=str(manifest_path), sha256=expected_sha256))
    require(manifest['schema'] == 'epyc.cafe3.launch-context.v1', 'wrong context schema')
    require(isinstance(manifest['run'], str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,160}', manifest['run']), 'invalid run')
    require(argv == manifest['argv'] and isinstance(argv, list)
            and all(isinstance(arg, str) and arg and '\0' not in arg for arg in argv), 'argv mismatch')
    receipt, executable = build_receipt(manifest['build'], manifest['backend'])
    require(argv[0] == str(executable), 'executable mismatch')

    # Prepared outside the grant. Its SHA is retained in the predeclared manifest;
    # inode/size/mtime/ctime detect replacement and ordinary in-place mutation.
    prepared = bound_json(manifest['prepared'])
    require(prepared['schema'] == 'epyc.cafe3.prepared.v1', 'wrong prepared schema')
    require(set(prepared['models']) == {'target', 'draft'}, 'target/draft identities required')
    for item in [*prepared['models'].values(), prepared['corpus']]:
        hex_digest(item['sha256'])
        require(item['identity'] == file_identity(item['path']), 'prepared input changed')
    require(prepared['corpus'] == manifest['corpus'], 'corpus identity mismatch')
    # Deliberately narrow canonical CLI. Reject aliases, equals forms, remote
    # loaders and duplicate options rather than guess which option wins.
    for arg in argv[1:]:
        if arg.startswith('-'):
            require('=' not in arg, 'equals-form options forbidden')
            require(not (arg.startswith(('--model', '-m')) and arg not in ('-m', '--model-draft')) and
                    not arg.startswith(('--hf', '-hf', '-mu', '--lora', '--mmproj')),
                    'model override forbidden')
    for role, flag in (('target', '-m'), ('draft', '--model-draft')):
        require(argv.count(flag) == 1, 'one canonical model option required')
        index = argv.index(flag)
        require(index + 1 < len(argv) and argv[index + 1] == prepared['models'][role]['path'], 'model argv mismatch')

    protocol = bound_json(manifest['protocol'])
    require(protocol['schema'] == 'epyc.cafe3.protocol.v1' and protocol['corpus'] == manifest['corpus'], 'protocol/corpus mismatch')
    for key in ('question', 'decision_rule', 'checkpoints', 'stop_on_answer', 'stop_on_futility'):
        require(isinstance(protocol[key], str) and protocol[key].strip(), 'missing protocol ' + key)
    require(type(protocol['repetitions']) is int and protocol['repetitions'] > 0, 'invalid repetitions')
    require(isinstance(protocol['arms'], list) and protocol['arms'] and
            all(isinstance(arm, str) and arm for arm in protocol['arms']) and
            len(set(protocol['arms'])) == len(protocol['arms']), 'invalid protocol arms')
    arm = manifest['arm']
    require(isinstance(arm, str) and (arm == 'adaptive' or re.fullmatch(r'static-\d+', arm))
            and arm in protocol['arms'], 'undeclared protocol arm')

    row = manifest['row']
    require(isinstance(row, str) and re.fullmatch(r'[A-Za-z0-9_.-]+', row) and env.get('FILLER_ID') == row, 'row mismatch')
    require(env.get('FILLER_DRYRUN', '0') == '0', 'native context refuses dryrun')
    # Only the official grant directory is accepted, never an arbitrary JSON or
    # copied grant. Region labels, GPU token and CPU expansion are all bound.
    grant = bound_file(manifest['grant'])
    require(str(grant) == '/mnt/raid0/llm/tmp/compute-flags/grants/' + row + '.grant', 'nonofficial grant path')
    require(not grant.with_suffix('.ended').exists() and not grant.with_suffix('.complete').exists(), 'grant already ended')
    fields = {}
    for token in grant.read_text().split():
        key, value = token.split('=', 1)
        require(key not in fields, 'duplicate grant field')
        fields[key] = value
    epoch = lambda value: datetime.strptime(value, '%Y-%m-%dT%H:%MZ').replace(tzinfo=timezone.utc).timestamp()
    start, end = epoch(fields['start']), epoch(fields['end'])
    require(start <= now < end and now < int(env['FILLER_DEADLINE']) <= end, 'expired/future grant or invalid deadline')
    require(not Path(env['FILLER_STOPFILE']).exists(), 'STOP present')
    placement = manifest['placement']
    require(placement['regions'] == fields['regions'] and placement['holds'] == fields['holds'], 'grant placement mismatch')
    require(type(placement['threads']) is int and placement['threads'] > 0 and
            str(placement['threads']) == env['FILLER_THREADS'], 'thread placement mismatch')
    cpus = cpu_set(placement['cpus'])
    require(cpus == cpu_set(env['FILLER_CPUS']) == affinity, 'affinity mismatch')
    if 'cpus' in fields:
        require(cpus == cpu_set(fields['cpus']), 'grant CPU mismatch')
    else:
        # write_grant omits cpus= when regions already spell the CPU list.
        explicit = [part for part in fields['regions'].split(',') if part != 'mi210_0']
        require(explicit and cpus == cpu_set(','.join(explicit)), 'explicit grant CPUs required')
    gpu = 'gpu-quiet' in fields['holds'].split(',')
    require(gpu == (manifest['backend'] == 'hip') and env['FILLER_NEEDGPU'] == ('1' if gpu else '0'), 'GPU grant mismatch')
    device_env = manifest['device_env']
    require(set(device_env) == ({'HIP_VISIBLE_DEVICES', 'ROCR_VISIBLE_DEVICES'} if gpu else set()), 'device bindings required')
    require(all(value == '0' and env.get(key) == value for key, value in device_env.items()), 'device placement mismatch')
    for flag, aliases in (('-t', ('--threads',)), ('-tb', ('--threads-batch',))):
        require(not any(alias in argv for alias in aliases) and argv.count(flag) == 1 and
                argv[argv.index(flag) + 1] == str(placement['threads']), 'argv thread mismatch')
    require(not any((arg.startswith(('--gpu-layers', '--n-gpu-layers')) and arg != '--gpu-layers-draft')
                    or (arg.startswith('-ngl') and arg != '-ngl')
                    for arg in argv), 'noncanonical GPU layers')
    for flag in ('-ngl', '--gpu-layers-draft'):
        require(argv.count(flag) == 1, 'canonical GPU layer flags required')
        layers = int(argv[argv.index(flag) + 1])
        require(layers > 0 if gpu else layers == 0, 'GPU layer placement mismatch')

    journal = Path(manifest['journal'])
    require(journal.is_absolute() and journal.parent.resolve(strict=True) == journal.parent and
            not journal.exists() and not journal.is_symlink(), 'journal must be a new canonical path')
    child = dict(LD_LIBRARY_PATH=str(executable.parent), OMP_NUM_THREADS=str(placement['threads']), GGML_IQK='1',
                 LLAMA_CAFE3_ADAPTIVE='1' if arm == 'adaptive' else '0', LLAMA_CAFE3_RUN=manifest['run'],
                 LLAMA_CAFE3_CONTEXT_SHA256=expected_sha256, LLAMA_CAFE3_JOURNAL=str(journal), **device_env)
    if not gpu:
        child.update(HIP_VISIBLE_DEVICES='-1', ROCR_VISIBLE_DEVICES='-1', CUDA_VISIBLE_DEVICES='-1')
    # No inherited LD_PRELOAD, model env, loader path or extra adaptive settings.
    return dict(argv=argv, env=child, context_sha256=expected_sha256,
                build_base=receipt['base'], models=prepared['models'], protocol=manifest['protocol'],
                arm=arm, corpus=prepared['corpus'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest')
    parser.add_argument('sha256')
    parser.add_argument('argv_json', help='JSON array of the actual intended server command')
    args = parser.parse_args()
    try:
        plan = validate_launch_context(args.manifest, args.sha256, load(args.argv_json))
    except (OSError, ValueError, KeyError, TypeError, IndexError, subprocess.CalledProcessError) as error:
        parser.exit(1, 'CAFE3 CONTEXT REFUSED: ' + str(error) + '\n')
    print(json.dumps(plan, indent=2))


if __name__ == '__main__':
    main()
