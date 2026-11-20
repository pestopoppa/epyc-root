#!/usr/bin/env python3
"""Grant-bound GPU modes diagnostic. No model-weight hashing or input preparation."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import subprocess
import sys
import time
import uuid

D = Path('/mnt/raid0/llm/tmp/df2/cafe4-modes-native-hip-r7-20261120')
MARKER = re.compile(r'^CAFE4_MTP_ROLLBACK width=(\d+) accepted=(\d+) selected=(\d+) faulted=(\d+) off_error=(\S+) observe_error=(\S+) fault_error=(\S+) off_observe=(\S+) fault_observe=(\S+) tolerance=(\S+)$', re.M)
PASS = 'RESULT PASS nonfault rollback agrees; target snapshot fault demonstrably diverges'
FAULT = 'RESULT FAIL injected-fault nonfault rollback agrees; target snapshot fault demonstrably diverges'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def atomic(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex)
    tmp.write_text(json.dumps(record, indent=2, allow_nan=False) + '\n')
    os.replace(tmp, path)


def controls(text, rc, width, fault):
    """Require native numeric controls and exact intended exit, never any rc1."""
    matches = MARKER.findall(text)
    if len(matches) != 1 or rc != int(fault):
        return None
    try:
        w, a, selected, faulted = map(int, matches[0][:4])
        e0, e1, ef, eo, delta, tol = map(float, matches[0][4:])
    except ValueError:
        return None
    if not all(math.isfinite(x) and x >= 0 for x in (e0, e1, ef, eo, delta, tol)):
        return None
    if not (2 <= w <= width and 0 < a < w and selected > 0 and faulted > 0 and tol > 0):
        return None
    if abs(tol - 0.743863867) > 1e-9 or max(e0, e1, eo) > tol or min(ef, delta) <= 10 * tol:
        return None
    result_lines = [line for line in text.splitlines() if line.startswith('RESULT ')]
    if result_lines != [FAULT if fault else PASS]:
        return None
    for mode in (1, 2):
        if not re.search(r'^CAFE4_TARGET_RS .* mode=' + str(mode) + r'$', text, re.M):
            return None
    if 'CAFE4_MTP_LOAD_ENABLED' not in text or 'CAFE4_DRAFT_REWIND_V4' not in text:
        return None
    return dict(actual_width=w, accepted=a, selected=selected, faulted=faulted,
                off_error=e0, observe_error=e1, fault_error=ef,
                off_observe=eo, fault_observe=delta, tolerance=tol)


def diagnostics(text, rc, width, fault):
    """Retain failed-run evidence separately from qualifying controls.

    This record never participates in PASS, fault qualification, or retries.
    Malformed/duplicate markers are retained as reasons, never selected by luck.
    """
    reasons = []
    if rc != int(fault):
        reasons.append('unexpected-exit')
    matches = MARKER.findall(text)
    measured = None
    if len(matches) != 1:
        reasons.append('rollback-marker-count')
    else:
        names = ('actual_width', 'accepted', 'selected', 'faulted', 'off_error',
                 'observe_error', 'fault_error', 'off_observe', 'fault_observe', 'tolerance')
        try:
            values = [int(x) for x in matches[0][:4]] + [float(x) for x in matches[0][4:]]
            if not all(math.isfinite(x) and x >= 0 for x in values):
                reasons.append('invalid-numeric-values')
            else:
                measured = dict(zip(names, values))
                w, a, selected, faulted, e0, e1, ef, eo, delta, tol = values
                if not (2 <= w <= width and 0 < a < w and selected > 0 and faulted > 0 and tol > 0):
                    reasons.append('acceptance-or-target-counts')
                if abs(tol - 0.743863867) > 1e-9:
                    reasons.append('fixed-tolerance-mismatch')
                if max(e0, e1, eo) > tol:
                    reasons.append('nonfault-numerical-control')
                if min(ef, delta) <= 10 * tol:
                    reasons.append('fault-sensitivity')
        except ValueError:
            reasons.append('invalid-numeric-values')
    result_lines = [line for line in text.splitlines() if line.startswith('RESULT ')]
    if result_lines != [FAULT if fault else PASS]:
        reasons.append('result-witness')
    for mode in (1, 2):
        if not re.search(r'^CAFE4_TARGET_RS .* mode=' + str(mode) + r'$', text, re.M):
            reasons.append('target-mode-' + str(mode))
    for marker in ('CAFE4_MTP_LOAD_ENABLED', 'CAFE4_DRAFT_REWIND_V4'):
        if marker not in text:
            reasons.append('missing-' + marker)
    return dict(measurements=measured, failed_predicates=reasons,
                native_messages=[line for line in text.splitlines()
                                 if line.startswith(('UNKNOWN ', 'CAFE4_TRIAL_FAILURE ',
                                                     'CAFE4_CONTROL_FAILURE ', 'CAFE4_REFERENCE ',
                                                     'CAFE4_BOUNDARY ', 'CAFE4_PROPOSAL ',
                                                     'CAFE4_VERIFY_TOKEN '))])


def inputs():
    record = json.loads((D / 'inputs.json').read_text())
    for path, expected in record['artifacts'].items():
        if digest(path) != expected:
            raise ValueError('artifact digest mismatch: ' + path)
    for path, expected in record['runtime'].items():
        if digest(path) != expected:
            raise ValueError('runtime digest mismatch: ' + path)
    model = record['model']
    stat = Path(model['path']).stat()
    if {key: getattr(stat, 'st_' + key) for key in model['stat']} != model['stat']:
        raise ValueError('model identity changed since content verification')
    return record


def output():
    return Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if os.environ.get('FILLER_DRYRUN') == '1' else D / 'RESULT.json'


def mappings(pid, record):
    lines = [line.split() for line in Path(f'/proc/{pid}/maps').read_text().splitlines()]
    libraries = {str(Path(line[-1]).resolve()) for line in lines if len(line) >= 6 and ('/libggml' in line[-1] or '/libllama' in line[-1])}
    expected = {path for path in record['artifacts'] if '/libggml' in path or '/libllama' in path}
    if not libraries <= expected:
        raise ValueError('foreign llama/ggml mapping')
    model = any(len(line) >= 6 and line[-1] == record['model']['path'] for line in lines)
    return model and libraries == expected, sorted(libraries)


def residency(pid, root=Path('/sys/class/kfd/kfd/proc')):
    """Read per-child KFD membership and VRAM while the child is alive."""
    client = root / str(pid)
    values = {p.name: int(p.read_text().strip()) for p in client.glob('vram_*')}
    return dict(pid=pid, kfd_registered=client.is_dir(), vram_bytes=sum(values.values()),
                devices=values, at=time.time())


def resident(sample):
    return sample['kfd_registered'] and sample['vram_bytes'] > 0


def run():
    record = inputs()
    smoke = os.environ.get('FILLER_DRYRUN') == '1'
    row = os.environ['FILLER_ID']
    if row != record['row']:
        raise ValueError('row identity mismatch')
    grant = Path('/mnt/raid0/llm/tmp/compute-flags/grants') / (row + '.grant')
    if not smoke and not grant.is_file():
        raise ValueError('scheduled execution requires official grant')
    grant_hash = digest(grant) if grant.is_file() else None
    stop = Path(os.environ['FILLER_STOPFILE'])
    deadline = int(os.environ['FILLER_DEADLINE'])
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    work = D / 'runs' / uuid.uuid4().hex
    work.mkdir(parents=True)
    cases = []
    for width, fault in ((2, False), (2, True), (3, False), (3, True)):
        if stop.exists() or time.time() >= deadline:
            return 75
        log = work / f'width-{width}-fault-{int(fault)}.log'
        command = [record['executable'], record['model']['path'], '-ngl', '99', '--verify-batch', str(width)]
        if fault:
            command.append('--fault-injection')
        env = dict(os.environ, LD_LIBRARY_PATH=str(Path(record['executable']).parent),
                   OMP_NUM_THREADS=os.environ['FILLER_THREADS'])
        samples = []
        mapped = False
        libraries = []
        cutoff = None
        with log.open('w') as stream:
            proc = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, env=env)
            try:
                while proc.poll() is None:
                    if not mapped:
                        try:
                            local_mapped, libraries = mappings(proc.pid, record)
                            sample = residency(proc.pid)
                            if local_mapped and resident(sample):
                                samples.append(sample)
                            mapped = len(samples) >= 2
                        except FileNotFoundError:
                            pass
                        if mapped:
                            atomic(work / f'mapped-{width}-{int(fault)}.json', dict(pid=proc.pid, libraries=libraries, residency=samples, at=time.time()))
                            if smoke:
                                atomic(output(), dict(schema='cafe4.modes.progress.v1', status='NATIVE_MODEL_MAPPED',
                                       smoke=True, row=row, at=time.time(), pid=proc.pid, model_mapped=True,
                                       mapped_libraries=libraries, residency=samples, log=str(log), input_sha256=digest(D / 'inputs.json')))
                    if stop.exists() or time.time() >= deadline:
                        cutoff = 'STOP' if stop.exists() else 'deadline'
                        proc.terminate()
                        break
                    time.sleep(.05)
                try:
                    rc = proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    rc = proc.wait(timeout=10)
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=10)
        text = log.read_text(errors='replace')
        verdict = controls(text, rc, width, fault) if mapped and cutoff is None else None
        case = dict(width=width, fault=fault, rc=rc, controls=verdict, diagnostics=diagnostics(text, rc, width, fault), mapped=mapped,
                    mapped_libraries=libraries, residency=samples, cutoff=cutoff, child_reaped=proc.poll() is not None,
                    log=str(log), log_sha256=digest(log))
        atomic(work / f'case-{width}-{int(fault)}.json', case)
        cases.append(case)
        if smoke and cutoff == 'STOP' and mapped:
            return 75
        if verdict is None:
            break  # stop on answer/futility; never retry failed numerical controls
    ok = len(cases) == 4 and all(case['controls'] is not None and case['child_reaped'] for case in cases)
    terminal = dict(schema='cafe4.modes.native.v1', status='PASS' if ok else 'UNKNOWN',
                    smoke=smoke, row=row, grant_sha256=grant_hash, input_sha256=digest(D / 'inputs.json'),
                    cases=cases, build_receipt=record['build_receipt'], model=record['model'],
                    scope='one fixed prompt; GPU widths 2 and 3; diagnostic acceptance cap; no performance verdict',
                    affinity=sorted(os.sched_getaffinity(0)), at=time.time())
    atomic(work / 'terminal.json', terminal)
    atomic(output(), terminal)
    return 0 if ok else 2


def main():
    action = sys.argv[1]
    if action == 'inputs':
        inputs()
        return 0
    if action == 'predicate':
        record = json.loads(output().read_text())
        native = inputs()
        expected = sorted(path for path in native['artifacts'] if '/libggml' in path or '/libllama' in path)
        return 0 if (record.get('status') == 'NATIVE_MODEL_MAPPED' and record.get('smoke') is True
                     and record['row'] == native['row'] and record['model_mapped'] is True
                     and record['mapped_libraries'] == expected
                     and len(record.get('residency', [])) >= 2
                     and all(resident(s) and s['pid'] == record['pid'] for s in record['residency'])
                     and record['input_sha256'] == digest(D / 'inputs.json')
                     and record['at'] >= int(os.environ['FILLER_SMOKE_T0'])) else 1
    if action == 'check':
        record = json.loads((D / 'RESULT.json').read_text())
        inputs()
        return 0 if record['status'] == 'PASS' and record['smoke'] is False and len(record['cases']) == 4 else 1
    if action == 'run':
        return run()
    return 64


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as error:
        print('CAFE4 NATIVE REFUSED:', error, file=sys.stderr)
        sys.exit(2)
