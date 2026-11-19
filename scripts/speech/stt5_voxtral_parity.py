#!/usr/bin/env python3
"""Public-JFK Voxtral token parity; prepared inputs only, no validation replay.

Model bytes must be verified before publication. Grant-time checks use the
restoration receipt and its stat identity, never a weight hash. A started case
is never rerun, including after interruption or a missing terminal receipt.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

from stt5_voxtral_tokens import compare, parse_voxtral_tokens

MODEL_SHA = '0289e58b62c1da39e4f6d1ed962c6d1cab8d261ca193d25a528a71a9b1b36792'
MODEL_SIZE = 4733486848
REVISION = '1c61dc461970d53264d784363b31ca113c7e01fd'
JFK_SHA = '59dfb9a4acb36fe2a2affc14bacbee2920ff435cb13cc314a08c13f66ba7860e'
REFERENCES = {
    '480': '5a1e91db2a59df826ae56c8efd7cfefb1e2f59ed6c942d146cc5e8f2f0cef44e',
    '960': '90b944541763f10792d833fbc9513a40598890930612059b46b28c06d5c1aeb3',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value):
    with Path(path).open('x') as out:
        json.dump(value, out, sort_keys=True)
        out.write('\n')
        out.flush()
        os.fsync(out.fileno())


def verify(cfg):
    if set(cfg['variants']) != {'480', '960'}:
        raise ValueError('requires exactly both delay variants')
    model = Path(cfg['model']).resolve()
    required = {cfg['model_receipt'], cfg['build_summary'], cfg['audio']}
    for variant in cfg['variants'].values():
        required.update([variant['runner'], variant['reference'], *variant['expected_maps']])
        if not variant['expected_maps']:
            raise ValueError('empty library residency contract')
    if not required <= cfg['pins'].keys():
        raise ValueError('missing required input/runtime pin')
    if cfg['pins'][cfg['audio']] != JFK_SHA:
        raise ValueError('requires the original public JFK fixture')
    for delay, variant in cfg['variants'].items():
        if cfg['pins'][variant['reference']] != REFERENCES[delay]:
            raise ValueError('original delay-specific reference required')
    # Refuse any attempted model hashing, even via a symlink or another suffix.
    for name, digest in cfg['pins'].items():
        path = Path(name)
        if path.samefile(model) or path.suffix.lower() == '.gguf':
            raise ValueError('weight hashing belongs before publication')
        if sha(path) != digest:
            raise ValueError('input/runtime drift: ' + name)
    receipt = json.loads(Path(cfg['model_receipt']).read_text())
    stat = model.stat()
    identity = [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns]
    if (receipt.get('verdict') != 'PASS' or receipt.get('download_rc') != 0
            or receipt.get('sha256') != MODEL_SHA or receipt.get('size') != MODEL_SIZE
            or receipt.get('revision') != REVISION
            or Path(receipt['path']).resolve() != model
            or receipt.get('model_stat') != identity):
        raise ValueError('prepared model receipt/stat mismatch')
    build = json.loads(Path(cfg['build_summary']).read_text())
    if (build.get('verdict') != 'PASS' or build.get('smoke') is not False
            or build.get('source_commit') != '2aa8d7669fcaa18d98d61a4bc8a077464e6b9919'):
        raise ValueError('build gate not established')
    for delay, variant in cfg['variants'].items():
        for name in [variant['runner'], *variant['expected_maps']]:
            if build['artifacts'].get(name) != cfg['pins'][name]:
                raise ValueError('runtime not bound to final build')
        if f'/voxtral{delay}/' not in variant['runner']:
            raise ValueError('delay/runtime mismatch')
        parse_voxtral_tokens(Path(variant['reference']).read_text())


def command(cfg, delay):
    return [cfg['variants'][delay]['runner'], '--backend', 'cpu', '--no-gpu',
            '--threads', '1', '-m', cfg['model'], '-f', cfg['audio']]


def evaluate(stdout, stderr, reference, rc, interrupted, loaded, expected):
    if interrupted or rc != 0:
        return dict(verdict='INCONCLUSIVE', reason='interrupted or native runner error')
    try:
        result = compare(stdout + '\n' + stderr, reference)
    except ValueError as exc:
        return dict(verdict='INCONCLUSIVE', reason=str(exc))
    missing = sorted(set(expected) - set(loaded))
    foreign = sorted(p for p in loaded if ('libggml' in Path(p).name or
                     'libcrispasr' in Path(p).name) and p not in expected)
    result.update(missing_residency=missing, foreign_libraries=foreign)
    if missing or foreign:
        result.update(verdict='INCONCLUSIVE', reason='library residency contract failed')
    return result


def admit_case(output, delay):
    # Exclusive directory creation also fences concurrent invocation. No replay
    # of terminal results is required: a fresh row must choose a fresh output.
    case = output / delay
    try:
        case.mkdir()
    except FileExistsError:
        raise ValueError('case already exposed or reserved; no redraw') from None
    return case


def drain(child):
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
    child.wait()
    if child.poll() is None:
        raise RuntimeError('owned child not reaped')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('config', type=Path)
    args = ap.parse_args()
    cfg = json.loads(args.config.read_text())
    config_sha = sha(args.config)
    verify(cfg)
    smoke = os.environ.get('FILLER_SMOKE') == '1'
    output = Path(cfg['smoke_output'] if smoke else cfg['output'])
    output.mkdir(exist_ok=True)
    stopped = False
    def stop(*_):
        nonlocal stopped
        stopped = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    stopfile = Path(os.environ.get('FILLER_STOPFILE', str(output.parent / 'STOP')))
    deadline = min(time.time() + 1200, float(os.environ.get('FILLER_DEADLINE', time.time() + 1230)) - 30)
    results = []
    for delay in ('480', '960'):
        if stopped or stopfile.exists() or time.time() >= deadline:
            return 75
        case = admit_case(output, delay)
        variant = cfg['variants'][delay]
        argv = command(cfg, delay)
        write_new(case / 'exposure.json', dict(command=argv, delay_ms=int(delay),
                  config_sha256=config_sha, model_sha256=MODEL_SHA,
                  row_id=os.environ.get('FILLER_ID'), cpus=sorted(os.sched_getaffinity(0)),
                  library_path=variant['library_path'], smoke=smoke))
        child = None
        loaded = set()
        interrupted = False
        try:
            env = {**os.environ, 'LD_LIBRARY_PATH': variant['library_path'],
                   'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1',
                   'HIP_VISIBLE_DEVICES': '-1', 'ROCR_VISIBLE_DEVICES': '-1'}
            with (case / 'stdout').open('x') as stdout, (case / 'stderr').open('x') as stderr:
                child = subprocess.Popen(argv, stdout=stdout, stderr=stderr, env=env)
                while child.poll() is None:
                    try:
                        for line in Path(f'/proc/{child.pid}/maps').read_text().splitlines():
                            fields = line.split(None, 5)
                            if len(fields) == 6 and fields[5].startswith('/'):
                                loaded.add(fields[5])
                    except FileNotFoundError:
                        pass
                    if stopped or stopfile.exists() or time.time() >= deadline:
                        interrupted = True
                        drain(child)
                        break
                    time.sleep(.05)
                child.wait()
            result = evaluate((case / 'stdout').read_text(), (case / 'stderr').read_text(),
                              Path(variant['reference']).read_text(), child.returncode,
                              interrupted, loaded, variant['expected_maps'])
            result.update(delay_ms=int(delay), rc=child.returncode, reaped=True,
                          config_sha256=config_sha, loaded_paths=sorted(loaded),
                          native_sha256={name: sha(case / name) for name in ('stdout', 'stderr')})
            write_new(case / 'result.json', result)
            results.append(result)
        finally:
            if child is not None:
                drain(child)
        if interrupted:
            return 75
    # Detect source/reference/runtime/model-stat drift across model execution.
    verify(cfg)
    if sha(args.config) != config_sha:
        raise ValueError('configuration drift')
    verdict = ('INCONCLUSIVE' if any(r['verdict'] == 'INCONCLUSIVE' for r in results)
               else 'PASS' if all(r['verdict'] == 'PASS' for r in results) else 'FAIL')
    write_new(output / 'summary.json', dict(schema='stt5-voxtral-public-parity/v1',
              verdict=verdict, cases=results, config_sha256=config_sha, smoke=smoke,
              parity_established=verdict == 'PASS' and not smoke,
              parity_scope='public JFK complete native token IDs only', validation_exposed=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
