"""Write native custody for the bounded EXP01 input rebuild and its dry-run plan."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

P = Path(__file__).resolve().parent
IK = Path('/mnt/raid0/llm/ik_llama.cpp')
ROW = 'vidya-exp01-proxy-input-recovery-20261118'
HEAD = 'c04881fc0f31dae5f8ec59c1d683889f0c9dfa11'
SRC = P / 'inputs/Qwen_Qwen3.6-35B-A3B-Q8_0.gguf'
SMOKE_SRC = Path('/mnt/raid0/llm/models/Qwen_Qwen3-0.6B-Q8_0.gguf')
CORPUS = P / 'calib/wiki.test.raw'
ITEMS = P / 'items/exp01-items-24.jsonl'
Q8_SHA = 'afddb074d3ce9ec8a3f64bfe7288a6c33f0d3a629be3caf4b5de1386a582dbd5'
CALIB_SHA = 'bfe9eb16ab9987fb88bde4ea9a30a00f2a45db01dfc14bad78d05325789c4f12'
ITEMS_SHA = '96dc98cf6b2cfdd65897f1deaf2b6f8481225d013851262cf08d6171f150fdbc'
ARMS = dict(Q4KM='Q4_K_M', IQ2XXS='IQ2_XXS', IQ4KT='IQ4_KT', IQ2KT='IQ2_KT')
LIBS = (IK / 'build/ggml/src/libggml.so', IK / 'build/src/libllama.so')
BINARIES = {name: IK / 'build/bin' / name for name in ('llama-imatrix', 'llama-quantize')}
SMOKE_TENSOR = 'blk.0.ffn_up.weight'
STAT = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')


def artifact(path: Path, *, hash_bytes: bool = True) -> dict:
    path = path.resolve(strict=True)
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        result = {'path': str(path), **{key: getattr(before, key) for key in STAT}}
        if hash_bytes:
            result['sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
        after = path.stat()
        if any(getattr(before, key) != getattr(after, key) for key in STAT):
            raise ValueError(f'artifact changed during observation: {path}')
    return result


def load(path: Path) -> dict:
    return json.loads(path.read_bytes())


def write(path: Path, data: dict) -> None:
    # Link the complete file into its final name without replacing existing custody.
    temp = path.parent / f'.{path.name}.{uuid.uuid4().hex}.tmp'
    try:
        with temp.open('x') as stream:
            json.dump(data, stream, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def tooling() -> dict:
    paths = dict(CORPUS=CORPUS, ITEMS=ITEMS, launcher=P / 'launch.sh',
                 recovery=P / 'recover_q8.sh', build=P / 'build_job.sh', capture=Path(__file__),
                 spec=P / 'spec.json', transfer=P / 'fetch_ranges.py',
                 smoke_source_receipt=P / 'inputs/SMOKE-INPUT-PIN.json', **BINARIES)
    paths.update({p.name: p for p in LIBS})
    pins = {name: artifact(path) for name, path in paths.items()}
    if (pins['CORPUS']['sha256'], pins['ITEMS']['sha256']) != (CALIB_SHA, ITEMS_SHA):
        raise ValueError('archived corpus or item set changed')
    actual = subprocess.check_output(['git', '-C', IK, 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', IK, 'status', '--porcelain', '--untracked-files=no'])
    if actual != HEAD or dirty:
        raise ValueError('reference source identity changed')
    for name, path in BINARIES.items():
        if HEAD[:9].encode() not in subprocess.check_output(['strings', path]).splitlines():
            raise ValueError(f'binary lacks pinned embedded build commit: {name}')
        env = {**os.environ, 'LD_LIBRARY_PATH': ':'.join(str(lib.parent) for lib in LIBS)}
        linkage = subprocess.check_output(['ldd', path], env=env, text=True)
        for library in LIBS:
            matches = [line.split()[2] for line in linkage.splitlines()
                       if line.split()[:2] == [library.name, '=>']]
            if len(matches) != 1 or Path(matches[0]).resolve() != library.resolve():
                raise ValueError(f'unexpected build linkage: {name} {library.name}')
    return pins


def check() -> dict:
    receipt_path = P / 'inputs/Q8-VERIFIED.json'
    receipt = load(receipt_path)
    metadata = artifact(SRC, hash_bytes=False)
    if (any(receipt[key] != value for key, value in metadata.items())
            or receipt['sha256'] != Q8_SHA or metadata['st_size'] != 36914690368):
        raise ValueError('pre-grant model verification differs from current source identity')
    expected_tooling = load(P / 'TOOLING-PINS.json')
    if tooling() != expected_tooling:
        raise ValueError('tooling source pins changed')
    smoke_receipt = load(P / 'inputs/SMOKE-INPUT-PIN.json')
    smoke_source = artifact(SMOKE_SRC, hash_bytes=False)
    if (smoke_source != {key: value for key, value in smoke_receipt.items() if key != 'sha256'}
            or smoke_source['st_size'] != 804753824):
        raise ValueError('pinned smoke input identity changed')
    return dict(source=receipt, source_receipt=artifact(receipt_path), smoke_source=smoke_receipt,
                tooling=expected_tooling, tooling_receipt=artifact(P / 'TOOLING-PINS.json'), ik_commit=HEAD)


def allocation(smoke: bool) -> dict:
    values = {key: os.environ[key] for key in ('FILLER_ID', 'FILLER_CPUS', 'FILLER_THREADS',
                                               'FILLER_DEADLINE', 'FILLER_STOPFILE')}
    cpus = set()
    for span in values['FILLER_CPUS'].split(','):
        lo, _, hi = span.partition('-')
        cpus.update(range(int(lo), int(hi or lo) + 1))
    if (values['FILLER_ID'] != ROW or cpus != os.sched_getaffinity(0)
            or len(cpus) != int(values['FILLER_THREADS']) or len(cpus) != (4 if smoke else 24)
            or int(values['FILLER_DEADLINE']) <= time.time()):
        raise ValueError('native affinity, threads, deadline or row differ from allocation')
    grants = Path(os.environ.get('FILLER_GRANTS_DIR', '/mnt/raid0/llm/tmp/compute-flags/grants'))
    if os.environ.get('FILLER_DRYRUN') == '1':
        grants = Path(os.environ['FILLER_DRYRUN_DIR']) / 'grants'
    grant = grants / f'{ROW}.grant'
    identity = artifact(grant)
    raw = grant.read_text()
    fields = dict(field.split('=', 1) for field in raw.split())
    start, end = (datetime.strptime(fields[key], '%Y-%m-%dT%H:%MZ').replace(tzinfo=timezone.utc).timestamp()
                  for key in ('start', 'end'))
    deadline = int(values['FILLER_DEADLINE'])
    if (hashlib.sha256(raw.encode()).hexdigest() != identity['sha256']
            or fields.get('id', ROW) != ROW or fields['regions'] != values['FILLER_CPUS']
            or not start <= time.time() < deadline <= end):
        raise ValueError('allocator grant bytes differ from invocation')
    return dict(values=values, grant=identity, grant_raw=raw, grant_start=start, grant_end=end)


def complete() -> bool:
    result_path = P / 'official/RESULT.json'
    if not result_path.is_file():
        return False
    result = load(result_path)
    if (result['state'] != 'complete-unsealed' or result['mode'] != 'official' or result['row_id'] != ROW
            or not (set(ARMS) | {'imatrix.dat', 'RUN.json', 'results.jsonl', 'BUILD-DONE.json'}) <= result['outputs'].keys()
            or load(P / 'official' / result['run_id'] / 'TERMINAL.json') != result):
        return False
    for recorded in result['outputs'].values():
        if artifact(Path(recorded['path']), hash_bytes='sha256' in recorded) != recorded:
            return False
    return True


def owned_members(pgid: int) -> set[int]:
    rows = subprocess.check_output(['ps', '-eo', 'pid=,pgid=,stat='], text=True)
    return {int(pid) for pid, group, state in (line.split() for line in rows.splitlines())
            if int(group) == pgid and not state.startswith('Z')}


def cleanup(proc: subprocess.Popen) -> None:
    for signum, grace in ((signal.SIGTERM, 5), (signal.SIGKILL, 2)):
        if not owned_members(proc.pid):
            break
        try:
            os.killpg(proc.pid, signum)
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + grace
        while owned_members(proc.pid) and time.monotonic() < deadline:
            time.sleep(0.1)
    proc.wait(timeout=2)
    if owned_members(proc.pid):
        raise ValueError('owned native process group survived TERM/KILL')


def run_native(env: dict, native_log) -> int:
    # Keep the process in the allocator's session, with a dedicated group we can reap.
    proc = subprocess.Popen(['/bin/bash', P / 'build_job.sh'], env=env, stdout=native_log,
                            stderr=subprocess.STDOUT, process_group=0)
    try:
        return proc.wait()
    finally:
        old_int = signal.signal(signal.SIGINT, signal.SIG_IGN)
        old_term = signal.signal(signal.SIGTERM, signal.SIG_IGN)
        try:
            cleanup(proc)
        finally:
            signal.signal(signal.SIGINT, old_int)
            signal.signal(signal.SIGTERM, old_term)


def run() -> int:
    smoke = os.environ.get('FILLER_DRYRUN') == '1'
    if smoke != (os.environ.get('FILLER_SMOKE') == '1'):
        raise ValueError('a dry-run must be a bounded smoke, and an official grant cannot smoke')
    mode = 'smoke-native' if smoke else 'official'
    root = P / ('smoke' if smoke else 'official')
    attempt = root / uuid.uuid4().hex
    attempt.mkdir(parents=True)
    rc = 4
    failure = None
    outputs = {}
    try:
        pins = check()
        grant = allocation(smoke)
        source = pins['smoke_source'] if smoke else pins['source']
        arms = {'IQ4KT': ARMS['IQ4KT']} if smoke else ARMS
        chunks = 1 if smoke else 560
        control = dict(schema='epyc.exp01.input_recovery.v1', row_id=ROW, run_id=attempt.name,
                       mode=mode, started_at=time.time(), inputs=pins, active_source=source, allocation=grant,
                       recipe=dict(imatrix_chunks=chunks, imatrix_context=512,
                                   flags=['--no-ppl', '-no-fug', '-no-fmoe'], arms=arms))
        if smoke:
            control['recipe']['smoke_quant_tensor'] = SMOKE_TENSOR
            control['recipe']['other_quantized_weights'] = 'Q8_0 passthrough'
        write(attempt / 'RUN.json', control)
        env = dict(os.environ, EXP01_RECOVERY_OUT=str(attempt), EXP01_RECOVERY_SRC=source['path'],
                   EXP01_RECOVERY_SRC_SIZE=str(source['st_size']), EXP01_RECOVERY_SRC_SHA=source['sha256'],
                   EXP01_RECOVERY_CHUNKS=str(chunks), EXP01_RECOVERY_MODE='smoke' if smoke else 'official')
        with (attempt / 'BUILD.log').open('xb') as native_log:
            rc = run_native(env, native_log)
        paths = [path for path in attempt.iterdir() if path.is_file()]
        outputs = {path.name: artifact(path) for path in sorted(paths)}
        stream = [json.loads(line) for line in (attempt / 'results.jsonl').read_bytes().splitlines()]
        units = ['preflight', 'imatrix', 'plan-IQ4KT-im', 'quant-IQ4KT'] if smoke else [
            'preflight', 'imatrix', 'plan-IQ4KT-im', 'plan-IQ2KT-im',
            *(f'quant-{arm}' for arm in ARMS), 'build-done']
        values = grant['values']
        if (rc != 0 or [entry['unit'] for entry in stream] != units or stream[0].get('ok') is not True
                or any(entry.get('rc', 0) != 0 for entry in stream)
                or Path(values['FILLER_STOPFILE']).exists()
                or time.time() >= int(values['FILLER_DEADLINE'])):
            raise ValueError('native failure, incomplete ordered units, STOP or allocator deadline')
        matrix = outputs['imatrix.dat']
        if (matrix['st_size'] <= 0 or matrix['path'] != stream[1]['out']
                or matrix['st_size'] != stream[1]['size'] or matrix['sha256'] != stream[1]['sha256']
                or stream[1]['chunks'] != chunks or stream[1]['ctx'] != 512):
            raise ValueError('native matrix differs from its manifest')
        if smoke:
            model = attempt / 'models/Qwen3-0.6B-IQ4_KT.gguf'
            meta = artifact(model, hash_bytes=False)
            if meta['st_size'] != stream[-1]['size'] or meta['path'] != stream[-1]['out']:
                raise ValueError('native smoke GGUF differs from its manifest')
            with model.open('rb') as weights:
                if weights.read(4) != b'GGUF':
                    raise ValueError('native smoke GGUF header missing')
            native_log = (attempt / 'quant-IQ4KT.log').read_text()
            tensors = re.split(r'(?m)(?=^\[\s*\d+/\s*\d+\]\s+)', native_log)
            conversions = [entry for entry in tensors if 'converting to ' in entry]
            if (len(conversions) != 1 or native_log.count('converting to ') != 1
                    or re.match(r'\[\s*\d+/\s*\d+\]\s+' + re.escape(SMOKE_TENSOR)
                                + r' - .*type =\s*q8_0,', conversions[0]) is None
                    or 'converting to iq4_kt .. ' not in conversions[0]
                    or re.search(r'size =\s+[\d.]+ MiB ->\s+[\d.]+ MiB', conversions[0]) is None):
                raise ValueError('native smoke must rederive exactly one Q8_0 to IQ4_KT tensor')
            outputs['IQ4KT'] = meta
        else:
            manifest = load(attempt / 'BUILD-DONE.json')
            if (manifest['row'] != ROW or set(manifest['arms']) != set(ARMS)
                    or manifest['imatrix'] != matrix['path']):
                raise ValueError('native build manifest differs')
            for arm, row in manifest['arms'].items():
                path = attempt / 'models' / f'Qwen3.6-35B-A3B-{ARMS[arm]}.gguf'
                meta = artifact(path, hash_bytes=False)
                if (row['path'] != meta['path'] or row['size'] != meta['st_size'] or row['size'] < 1
                        or row['mtime'] != meta['st_mtime_ns'] // 1_000_000_000):
                    raise ValueError(f'native arm {arm} differs from its manifest')
                with path.open('rb') as weights:
                    if weights.read(4) != b'GGUF':
                        raise ValueError(f'native arm {arm} lacks a GGUF header')
                outputs[arm] = meta
    except (OSError, ValueError, KeyError, subprocess.SubprocessError, KeyboardInterrupt) as exc:
        failure = f'{type(exc).__name__}: {exc}'
        rc = 4
    result = dict(schema='epyc.exp01.input_recovery_receipt.v1', mode=mode, row_id=ROW,
                  run_id=attempt.name, ended_at=time.time(), rc=rc, outputs=outputs,
                  state='partial-or-failed' if rc else ('smoke-native-complete' if smoke else 'complete-unsealed'))
    if smoke and rc == 0:
        result['verified_iq4kt_tensors'] = len(conversions)
    if failure:
        result['failure'] = failure
        print(failure, file=sys.stderr)
    write(attempt / 'TERMINAL.json', result)
    if not smoke:
        write(root / 'RESULT.json', result)
    elif rc == 0:
        write(Path(os.environ['FILLER_DRYRUN_RESULT_PATH']), result)
    return rc


def interrupt(_signum, _frame):
    raise KeyboardInterrupt('row process interrupted')


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, interrupt)
    if sys.argv[1:] == ['check']:
        check()
    elif sys.argv[1:] == ['pin-smoke-input']:
        write(P / 'inputs/SMOKE-INPUT-PIN.json', artifact(SMOKE_SRC))
    elif sys.argv[1:] == ['pin-tooling']:
        write(P / 'TOOLING-PINS.json', tooling())
    elif sys.argv[1:] == ['run']:
        raise SystemExit(run())
    elif sys.argv[1:] == ['complete']:
        raise SystemExit(0 if complete() else 1)
    else:
        raise SystemExit('expected check, pin-tooling, run, or complete')
