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


def matrix(cfg=None):
    cases = [(context, mode) for context in PRESETS for mode in ('auto', 'forced')]
    if cfg is None or 'cases' not in cfg:
        return cases
    selected = [tuple(case) for case in cfg['cases']]
    if not selected or len(set(selected)) != len(selected) or any(case not in cases for case in selected):
        raise ValueError('cases must be a nonempty unique subset of the native matrix')
    return selected


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
    if cfg.get('runner_kind') == 'transcribe':
        argv = [cfg['runner'], '--backend', 'cpu', '--threads', '3',
                '--timestamps', 'token', '--raw-tokens', '--stream-chunk-ms', '80',
                '--stream-att-right', context[1:], '-m', cfg['model'],
                '-o', str(transcript)]
        if mode == 'forced':
            argv += ['--language', 'en-US']
        return argv + [cfg['audio']]
    return [cfg['runner'], cfg['model'], cfg['audio'], str(PRESETS[context]),
            'auto' if mode == 'auto' else 'en-US', '3', str(transcript)]


def parse_native(parser, stdout, transcript, kind):
    if kind == 'transcribe':
        # Native CLI interleaves timing rows. Preserve all witness lines so
        # the shared strict parser still rejects duplicates, gaps and bad counts.
        stdout = '\n'.join(line.replace('CS8_NEMO_', 'CS8_MATCHED_NEMO_', 1)
                           for line in stdout.splitlines() if line.startswith('CS8_NEMO_'))
    return parser.parse(stdout, transcript)


def reference_agrees(value, reference):
    return (reference.get('status') == 'PASS' and reference.get('rc') == 0
            and reference.get('reaped') is True and value.get('status') == 'PASS'
            and value['model_sha256'] == reference['model_sha256']
            and value['audio_sha256'] == reference['audio_sha256']
            and value['case'] == reference['case']
            and value['tokens']['unk_count'] == reference['tokens']['unk_count'] == 0
            and bool(value['tokens']['token_ids'])
            and value['tokens']['token_ids'] == reference['tokens']['token_ids']
            and value['tokens']['hypothesis_with_unk'] == reference['tokens']['hypothesis_with_unk'])


def worker_groups(cpus, physical=False):
    if physical:
        unique = {}
        for cpu in sorted(cpus):
            topology = Path(f'/sys/devices/system/cpu/cpu{cpu}/topology')
            key = tuple((topology / field).read_text().strip()
                        for field in ('physical_package_id', 'core_id'))
            unique.setdefault(key, cpu)
        cpus = list(unique.values())
    return [cpus[i:i + 3] for i in range(0, len(cpus) - 2, 3)][:8]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('config', type=Path)
    args = ap.parse_args()
    cfg = json.loads(args.config.read_text())
    config_sha = sha(args.config)
    cases = matrix(cfg)
    if cfg.get('references') and (cfg.get('runner_kind') != 'transcribe'
            or set(cfg['references']) != {c + '-' + m for c, m in cases}
            or any(path not in cfg['pins'] for path in cfg['references'].values())):
        raise ValueError('parity requires complete pinned independent-runner references')
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
    output = Path(cfg['smoke_output'] if os.environ.get('FILLER_SMOKE') == '1'
                  and 'smoke_output' in cfg else cfg['output'])
    output.mkdir(exist_ok=True)
    cpus = sorted(os.sched_getaffinity(0))
    groups = worker_groups(cpus, cfg.get('distinct_physical_cores', False))
    cap = cfg.get('max_workers', 8)
    if not isinstance(cap, int) or not 1 <= cap <= 8:
        raise ValueError('max_workers must be between one and eight')
    groups = groups[:cap]
    if not groups:
        raise ValueError('requires three assigned CPUs')
    if os.environ.get('FILLER_SMOKE') != '1' and len(groups) != cfg.get('required_workers', len(groups)):
        raise ValueError('grant does not provide required physical worker topology')
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
                     started_epoch=time.time(), loaded_paths=[], native_sha256={}, peak_sampled_rss_kib=0)
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
                        for line in Path(f'/proc/{child.pid}/status').read_text().splitlines():
                            if line.startswith('VmRSS:'):
                                value['peak_sampled_rss_kib'] = max(value['peak_sampled_rss_kib'], int(line.split()[1]))
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
                    tokens = parse_native(parser, (output / (key + '.stdout')).read_text(),
                                          transcript.read_text(), cfg.get('runner_kind'))
                    value['tokens'] = tokens
                    missing = sorted(expected_maps - loaded)
                    foreign = sorted(p for p in loaded if 'libggml' in Path(p).name and p not in expected_maps)
                    value.update(missing_residency=missing, foreign_ggml=foreign)
                    value['status'] = 'PASS' if not missing and not foreign and tokens['hypothesis_with_unk'].strip() else 'FAIL'
                except (ValueError, OSError, UnicodeError) as exc:
                    value.update(status='FAIL', reason='native witness invalid: ' + str(exc))
            if cfg.get('references'):
                reference_path = cfg['references'][key]
                reference = json.loads(Path(reference_path).read_text())
                value.update(reference_path=reference_path,
                             reference_sha256=cfg['pins'][reference_path],
                             reference_agreement=reference_agrees(value, reference))
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
        results = list(pool.map(run, cases))
    terminal = [r for r in results if r is not None]
    if len(terminal) != len(cases):
        return 75
    summary = dict(schema='stt5-crisp-public-runtime/v1', config_sha256=config_sha,
                   cases=terminal, complete=True, workers=len(groups),
                   verdict='PASS' if all(r['status'] == 'PASS' for r in terminal) else 'INCONCLUSIVE',
                   validation_exposed=False, rate_calibrated=False, parity_established=False)
    if cfg.get('references'):
        parity = all(r.get('reference_agreement') is True for r in terminal)
        summary.update(verdict='PASS' if parity else 'INCONCLUSIVE',
                       parity_established=parity and os.environ.get('FILLER_SMOKE') != '1',
                       parity_scope='public JFK only; exact native IDs and transcript',
                       smoke=os.environ.get('FILLER_SMOKE') == '1')
    write_new(output / 'summary.json', summary)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
