#!/usr/bin/env python3
"""Public-audio Crisp runtime matrix; never exposes the validation cohort.

Inputs are prepared and weight-hashed before publication. Native token/text
consistency and sampled library residency are engineering checks, not WER,
runner parity, rate calibration, or a replacement decision.
"""
import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import threading
import time

PRESETS = {'r0': 1, 'r3': 0, 'r6': 2, 'r13': 3}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value):
    with path.open('x') as out:
        json.dump(value, out, sort_keys=True)
        out.write('\n')
        out.flush()
        os.fsync(out.fileno())


def matrix():
    return [(context, mode) for context in PRESETS for mode in ('auto', 'forced')]


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


def command(cfg, context, mode, transcript):
    return [cfg['runner'], cfg['model'], cfg['audio'], str(PRESETS[context]),
            'auto' if mode == 'auto' else 'en-US', '3', str(transcript)]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('config', type=Path)
    args = ap.parse_args()
    cfg = json.loads(args.config.read_text())
    config_sha = sha(args.config)
    # Only small source/library/public-audio pins: model bytes were checked once
    # by the owner. Retain the prepared model stat identity, not a grant-time hash.
    for path, digest in cfg['pins'].items():
        if sha(path) != digest:
            raise ValueError('input/runtime drift: ' + path)
    stat = Path(cfg['model']).stat()
    if [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns] != cfg['model_stat']:
        raise ValueError('prepared model identity drift')
    spec = importlib.util.spec_from_file_location('matched_tokens', cfg['parser'])
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)
    output = Path(cfg['output'])
    output.mkdir(exist_ok=True)
    cpus = sorted(os.sched_getaffinity(0))
    groups = [cpus[i:i + 3] for i in range(0, len(cpus) - 2, 3)][:8]
    if not groups:
        raise ValueError('requires three assigned CPUs')
    available = list(groups)
    lock = threading.Lock()
    stopping = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stopping.set())
    signal.signal(signal.SIGINT, lambda *_: stopping.set())
    stopfile = Path(os.environ.get('FILLER_STOPFILE', str(output.parent / 'STOP')))
    deadline = min(time.time() + 1800, float(os.environ.get('FILLER_DEADLINE', time.time() + 1830)) - 30)
    expected_maps = set(cfg['expected_maps'])

    def run(case):
        context, mode = case
        key = context + '-' + mode
        exposure = output / (key + '.exposure.json')
        result = output / (key + '.result.json')
        if result.exists():
            prior = json.loads(result.read_text())
            if prior['config_sha256'] != config_sha:
                raise ValueError('result binding drift')
            for name, digest in prior.get('native_sha256', {}).items():
                if sha(output / name) != digest:
                    raise ValueError('native output drift')
            return prior
        if exposure.exists():
            prior = json.loads(exposure.read_text())
            if prior['config_sha256'] != config_sha:
                raise ValueError('exposure binding drift')
            value = dict(case=key, config_sha256=config_sha, status='UNKNOWN',
                         reason='exposed without terminal result; no redraw')
            write_new(result, value)
            return value
        if stopping.is_set() or stopfile.exists() or time.time() >= deadline:
            return None
        with lock:
            group = available.pop()
        transcript = output / (key + '.txt')
        argv = command(cfg, context, mode, transcript)
        value = dict(case=key, config_sha256=config_sha, command=argv,
                     cpus=group, workers=len(groups), threads=3,
                     row_id=os.environ.get('FILLER_ID'), admitted_cpus=cpus,
                     model_sha256=cfg['model_sha256'], audio_sha256=cfg['pins'][cfg['audio']],
                     started_epoch=time.time(), loaded_paths=[], native_sha256={})
        write_new(exposure, value)
        child = None
        started = time.monotonic()
        try:
            with (output / (key + '.stdout')).open('xb') as so, (output / (key + '.stderr')).open('xb') as se:
                env = {**os.environ, 'LD_LIBRARY_PATH': cfg['library_path'],
                       'OMP_NUM_THREADS': '3', 'OPENBLAS_NUM_THREADS': '1',
                       'HIP_VISIBLE_DEVICES': '-1', 'ROCR_VISIBLE_DEVICES': '-1',
                       'CRISPASR_NEMOTRON_STREAMING': '1', 'CRISPASR_FC_PW_Q8': '0'}
                env.pop('CS8_QUAL_HOLD', None)
                # taskset establishes affinity before loading the runner; no
                # Python preexec_fn in a threaded parent.
                child = subprocess.Popen(['taskset', '-c', ','.join(map(str, group)), *argv],
                                         stdout=so, stderr=se, env=env)
                loaded = set()
                while child.poll() is None:
                    try:
                        for line in Path(f'/proc/{child.pid}/maps').read_text().splitlines():
                            fields = line.split(None, 5)
                            if len(fields) == 6 and fields[5].startswith('/'):
                                loaded.add(fields[5])
                    except FileNotFoundError:
                        pass
                    if stopping.is_set() or stopfile.exists() or time.time() >= deadline or time.monotonic() - started > 300:
                        drain(child)
                        value['interrupted'] = True
                        break
                    stopping.wait(.05)
                child.wait()
                value.update(rc=child.returncode, reaped=True, wall_s=time.monotonic() - started,
                             loaded_paths=sorted(loaded))
            for suffix in ('stdout', 'stderr', 'txt'):
                path = output / (key + '.' + suffix)
                if path.exists():
                    value['native_sha256'][path.name] = sha(path)
            if value.get('interrupted'):
                value.update(status='UNKNOWN', reason='owned child drained at stop/deadline/timeout')
            elif child.returncode != 0:
                value.update(status='FAIL', reason='native runner error')
            else:
                try:
                    tokens = parser.parse((output / (key + '.stdout')).read_text(), transcript.read_text())
                    value['tokens'] = tokens
                    missing = sorted(expected_maps - loaded)
                    foreign = sorted(p for p in loaded if 'libggml' in Path(p).name and p not in expected_maps)
                    value.update(missing_residency=missing, foreign_ggml=foreign)
                    value['status'] = 'PASS' if not missing and not foreign and tokens['hypothesis_with_unk'].strip() else 'FAIL'
                except (ValueError, OSError, UnicodeError) as exc:
                    value.update(status='FAIL', reason='native witness invalid: ' + str(exc))
            write_new(result, value)
            with lock:
                with (output / 'results.jsonl').open('a') as out:
                    out.write(json.dumps(value, sort_keys=True) + '\n')
            return value
        finally:
            if child is not None:
                drain(child)
            with lock:
                available.append(group)

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(groups)) as pool:
        results = list(pool.map(run, matrix()))
    terminal = [r for r in results if r is not None]
    if len(terminal) != 8:
        return 75
    summary = dict(schema='stt5-crisp-public-runtime/v1', config_sha256=config_sha,
                   cases=terminal, complete=True, workers=len(groups),
                   verdict='PASS' if all(r['status'] == 'PASS' for r in terminal) else 'INCONCLUSIVE',
                   validation_exposed=False, rate_calibrated=False, parity_established=False)
    write_new(output / 'summary.json', summary)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
