"""Continue the terminal EXP01 recovery by generating its missing IQ2_KT arm."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import recovery_capture as recovery

PARENT_ROW = recovery.ROW
ROW = PARENT_ROW + '-r2'
PARENT_RUN = 'fbd168aa3fbd440eb4424f9a36a30f66'
PREVIOUS = ROOT / 'official' / PARENT_RUN
PINS = HERE / 'REUSE-PINS.json'
RUNNER_PINS = HERE / 'RUNNER-PINS.json'
REUSED_ARMS = {arm: native_type for arm, native_type in recovery.ARMS.items() if arm != 'IQ2KT'}
MATRIX = 'imatrix.dat'
TENSOR = recovery.SMOKE_TENSOR
CONTEXT = 512
DEADLINE_RC = 124
STOP_RC = 130


def stat_matches(pin: dict) -> bool:
    current = recovery.artifact(Path(pin['path']), hash_bytes=False)
    return all(pin.get(key) == value for key, value in current.items())


def read_units(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_bytes().splitlines()]


def source_identity(pins: dict) -> dict:
    return {name: pins[name] for name in ('source', 'source_receipt', 'smoke_source', 'ik_commit')}


def runner_identity() -> dict:
    return {path.name: recovery.artifact(path)
            for path in (Path(__file__), HERE / 'launch.sh', HERE / 'spec.json')}


def has_gguf_header(path: Path) -> bool:
    with path.open('rb') as stream:
        return stream.read(4) == b'GGUF'


def pin() -> None:
    if PINS.exists():
        raise FileExistsError('reuse pins already exist')
    inputs = recovery.check()
    terminal_path = PREVIOUS / 'TERMINAL.json'
    result_path = PREVIOUS.parent / 'RESULT.json'
    terminal = recovery.load(terminal_path)
    original = recovery.load(PREVIOUS / 'RUN.json')
    if (terminal_path.read_bytes() != result_path.read_bytes()
            or terminal['row_id'] != PARENT_ROW or terminal['run_id'] != PARENT_RUN
            or terminal['mode'] != 'official' or terminal['state'] != 'partial-or-failed'
            or terminal['rc'] == 0 or original['row_id'] != PARENT_ROW
            or original['run_id'] != PARENT_RUN or original['inputs'] != inputs
            or original['active_source'] != inputs['source']
            or original['recipe'] != dict(imatrix_chunks=560, imatrix_context=CONTEXT,
                                          flags=['--no-ppl', '-no-fug', '-no-fmoe'],
                                          arms=recovery.ARMS)):
        raise ValueError('original EXP01 failure, source, tooling or recipe differs')
    allocation = original['allocation']
    if (hashlib.sha256(allocation['grant_raw'].encode()).hexdigest() != allocation['grant']['sha256']
            or allocation['values']['FILLER_THREADS'] != '24'
            or allocation['values']['FILLER_ID'] != PARENT_ROW
            or not allocation['grant_start'] <= original['started_at'] < allocation['grant_end']):
        raise ValueError('original allocator receipt differs')
    expected = {'BUILD.log', 'RUN.json', 'results.jsonl', 'imatrix.log', MATRIX,
                'plan-IQ4KT-im.log', 'plan-IQ2KT-im.log',
                *(f'quant-{arm}.log' for arm in recovery.ARMS)}
    if terminal['outputs'].keys() != expected:
        raise ValueError('original raw output set differs')
    captured = {}
    for name, recorded in terminal['outputs'].items():
        item = recovery.artifact(PREVIOUS / name)
        if item != recorded:
            raise ValueError(f'original receipt mismatch for {name}')
        captured[name] = item
    units = read_units(PREVIOUS / 'results.jsonl')
    expected_units = ['preflight', 'imatrix', 'plan-IQ4KT-im', 'plan-IQ2KT-im',
                      *(f'quant-{arm}' for arm in recovery.ARMS)]
    if ([unit['unit'] for unit in units] != expected_units or units[0]['ok'] is not True
            or any(unit['rc'] != 0 for unit in units[1:-1])
            or units[-1]['rc'] != DEADLINE_RC or units[-1]['size'] != 0
            or Path(units[-1]['out']).exists()
            or list((PREVIOUS / 'models').glob('.partial-*'))):
        raise ValueError('original ordered units differ from expected deadline interruption')
    matrix = captured.pop(MATRIX)
    matrix_unit = units[1]
    if (matrix_unit['chunks'] != 560 or matrix_unit['ctx'] != CONTEXT
            or matrix_unit['out'] != matrix['path'] or matrix_unit['sha256'] != matrix['sha256']
            or matrix_unit['calib_sha256'] != inputs['tooling']['CORPUS']['sha256']
            or matrix_unit['size'] != matrix['st_size'] or not matrix['st_size']):
        raise ValueError('original native matrix does not match its successful unit')
    reused = {MATRIX: matrix}
    for arm, native_type in REUSED_ARMS.items():
        unit = next(unit for unit in units if unit['unit'] == f'quant-{arm}')
        path = PREVIOUS / 'models' / f'Qwen3.6-35B-A3B-{native_type}.gguf'
        identity = recovery.artifact(path)
        if (unit['type'] != native_type or unit['arm'] != arm or unit['out'] != identity['path']
                or unit['size'] != identity['st_size'] or not identity['st_size']
                or unit['extra'] != f"--imatrix {matrix['path']}" or not has_gguf_header(path)
                or not stat_matches(identity)):
            raise ValueError(f'original {arm} arm does not match its successful unit')
        reused[arm] = identity
    captured.update({'TERMINAL.json': recovery.artifact(terminal_path),
                     'RESULT.json': recovery.artifact(result_path)})
    recovery.write(PINS, dict(schema='epyc.exp01.continuation_pins.v1', row_id=ROW,
                              predecessor=dict(row_id=PARENT_ROW, run_id=PARENT_RUN,
                                               terminal_rc=terminal['rc'],
                                               failed_unit=units[-1], receipts=captured),
                              verified_at=time.time(), source=source_identity(inputs),
                              reference=inputs['tooling'], runner=runner_identity(), reused=reused))


def pin_runner() -> None:
    recovery.write(RUNNER_PINS, dict(schema='epyc.exp01.continuation_runner_pins.v1',
                                     reuse_pins=recovery.artifact(PINS), runner=runner_identity()))


def check() -> tuple[dict, dict]:
    inputs = recovery.check()
    pinned = recovery.load(PINS)
    runner = recovery.load(RUNNER_PINS)
    if runner != dict(schema='epyc.exp01.continuation_runner_pins.v1',
                      reuse_pins=recovery.artifact(PINS), runner=runner_identity()):
        raise ValueError('continuation runner or pregrant receipt bytes changed')
    if (pinned['schema'] != 'epyc.exp01.continuation_pins.v1' or pinned['row_id'] != ROW
            or pinned['source'] != source_identity(inputs) or pinned['reference'] != inputs['tooling']
            or pinned['predecessor']['row_id'] != PARENT_ROW
            or pinned['predecessor']['run_id'] != PARENT_RUN
            or pinned['reused'].keys() != {MATRIX, *REUSED_ARMS}):
        raise ValueError('continuation source, recipe runner or predecessor pins differ')
    for label, item in (pinned['reused'] | pinned['predecessor']['receipts']).items():
        if not stat_matches(item):
            raise ValueError(f'previously verified input identity changed: {label}')
    return inputs, pinned


def record(attempt: Path, entry: dict) -> None:
    with (attempt / 'results.jsonl').open('a') as stream:
        stream.write(json.dumps(entry, sort_keys=True) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def interrupted(values: dict) -> int:
    if Path(values['FILLER_STOPFILE']).exists():
        return STOP_RC
    if time.time() >= int(values['FILLER_DEADLINE']):
        return DEADLINE_RC
    return 0


def native_unit(attempt: Path, unit: str, argv: list[str], values: dict) -> int:
    env = dict(os.environ, LD_LIBRARY_PATH=':'.join(str(lib.parent) for lib in recovery.LIBS))
    log = attempt / f'{unit}.log'
    started = time.monotonic()
    rc = interrupted(values)
    with log.open('xb') as stream:
        if rc == 0:
            proc = subprocess.Popen(argv, env=env, stdout=stream, stderr=subprocess.STDOUT,
                                    process_group=0)
            try:
                while rc == 0:
                    try:
                        rc = proc.wait(timeout=1)
                        rc = interrupted(values) or rc
                        break
                    except subprocess.TimeoutExpired:
                        rc = interrupted(values)
            except KeyboardInterrupt:
                rc = STOP_RC
                raise
            finally:
                recovery.cleanup(proc)
                record(attempt, dict(unit=unit, rc=rc, argv=argv, log=str(log),
                                     duration_s=round(time.monotonic() - started, 3),
                                     cpus=values['FILLER_CPUS'], threads=int(values['FILLER_THREADS'])))
            return rc
    record(attempt, dict(unit=unit, rc=rc, argv=argv, log=str(log), duration_s=0,
                         cpus=values['FILLER_CPUS'], threads=int(values['FILLER_THREADS'])))
    return rc


def verify_conversion(path: Path, smoke: bool) -> int:
    log = path.read_text()
    if not re.search(r'(?m)^llama_model_quantize_internal: quant size\s+=', log):
        raise ValueError('native quantizer omitted its completed size summary')
    records = re.split(r'(?m)(?=^\[\s*\d+/\s*\d+\]\s+)', log)
    converted = [entry for entry in records if 'converting to ' in entry]
    quantized = [entry for entry in converted
                 if 'converting to iq2_kt .. ' in entry
                 and re.search(r'size =\s+[\d.]+ MiB ->\s+[\d.]+ MiB', entry)]
    if not quantized:
        raise ValueError('native quantizer produced no completed IQ2_KT conversion')
    if smoke and (len(quantized) != 1 or len(converted) != 1 or log.count('converting to ') != 1
                  or not re.match(r'\[\s*\d+/\s*\d+\]\s+' + re.escape(TENSOR)
                                  + r' - .*type =\s*q8_0,', quantized[0])):
        raise ValueError('smoke did not derive exactly one selected Q8_0 to IQ2_KT tensor')
    return len(quantized)


def run() -> int:
    smoke = os.environ.get('FILLER_DRYRUN') == '1'
    if smoke != (os.environ.get('FILLER_SMOKE') == '1'):
        raise ValueError('unexpected smoke/allocation flags')
    mode = 'smoke-native' if smoke else 'official'
    root = HERE / ('smoke' if smoke else 'official')
    attempt = root / uuid.uuid4().hex
    attempt.mkdir(parents=True)
    partials = []
    rc = 4
    failure = None
    outputs = {}
    verified_tensors = 0
    try:
        inputs, pinned = check()
        recovery.ROW = ROW
        allocation = recovery.allocation(smoke)
        values = allocation['values']
        threads = values['FILLER_THREADS']
        source = inputs['smoke_source'] if smoke else inputs['source']
        matrix_path = attempt / MATRIX if smoke else Path(pinned['reused'][MATRIX]['path'])
        partial = attempt / '.partial-IQ2_KT.gguf'
        partials.append(partial)
        model = attempt / ('Qwen3-0.6B-IQ2_KT.gguf' if smoke else 'Qwen3.6-35B-A3B-IQ2_KT.gguf')
        args = [str(recovery.BINARIES['llama-quantize']), '--allow-requantize',
                '--imatrix', str(matrix_path)]
        if smoke:
            args += ['--custom-q', '^blk[.]0[.]ffn_up[.]weight$=iq2_kt,.*=q8_0']
        args += [source['path'], str(partial), 'IQ2_KT', threads]
        recovery.write(attempt / 'RUN.json', dict(schema='epyc.exp01.continuation_run.v1',
                       row_id=ROW, run_id=attempt.name, mode=mode, started_at=time.time(),
                       allocation=allocation, source=source, reuse_pins=recovery.artifact(PINS),
                       runner_pins=recovery.artifact(RUNNER_PINS),
                       predecessor=pinned['predecessor'], reused={} if smoke else pinned['reused'],
                       recipe=dict(imatrix_chunks=1 if smoke else 560, imatrix_context=CONTEXT,
                                   matrix=str(matrix_path), native_type='IQ2_KT', argv=args,
                                   smoke_selected_tensor=TENSOR if smoke else None)))
        if shutil.disk_usage(attempt).free < (2 if smoke else 16) * 2**30:
            raise ValueError('insufficient scratch space for IQ2_KT output')
        if smoke:
            matrix_partial = attempt / 'imatrix.partial'
            partials.append(matrix_partial)
            context = str(CONTEXT)
            matrix_args = [str(recovery.BINARIES['llama-imatrix']), '-m', source['path'],
                           '-f', str(recovery.CORPUS), '-o', str(matrix_partial),
                           '--chunks', '1', '-c', context, '-b', context, '-ub', context,
                           '-t', threads, '--no-ppl', '-no-fug', '-no-fmoe']
            unit_rc = native_unit(attempt, 'imatrix', matrix_args, values)
            if unit_rc or not matrix_partial.is_file() or matrix_partial.stat().st_size <= 0:
                raise ValueError(f'native smoke matrix incomplete rc={unit_rc}')
            matrix_partial.rename(matrix_path)
            outputs[MATRIX] = recovery.artifact(matrix_path)
        else:
            outputs.update(pinned['reused'])
        unit_rc = native_unit(attempt, 'quant-IQ2KT', args, values)
        if unit_rc:
            raise ValueError(f'native IQ2_KT unit incomplete rc={unit_rc}')
        verified_tensors = verify_conversion(attempt / 'quant-IQ2KT.log', smoke)
        if not has_gguf_header(partial):
            raise ValueError('native IQ2_KT output lacks GGUF magic')
        if interrupted(values):
            raise ValueError('STOP or deadline crossed before output acceptance')
        partial.rename(model)
        outputs['IQ2KT'] = recovery.artifact(model, hash_bytes=smoke)
        rc = 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError, KeyboardInterrupt) as exc:
        failure = f'{type(exc).__name__}: {exc}'
        print(failure, file=sys.stderr)
    dispositions = []
    for path in partials:
        if path.exists():
            identity = recovery.artifact(path, hash_bytes=False)
            path.unlink()
            dispositions.append(dict(artifact=identity, disposition='deleted_unfinished_successor_bytes'))
    for path in sorted(attempt.iterdir()):
        if path.is_file() and path.suffix != '.gguf' and path.name not in outputs:
            outputs[path.name] = recovery.artifact(path)
    result = dict(schema='epyc.exp01.input_recovery_receipt.v1', mode=mode, row_id=ROW,
                  run_id=attempt.name, ended_at=time.time(), rc=rc, outputs=outputs,
                  state='partial-or-failed' if rc else ('smoke-native-complete' if smoke else 'complete-unsealed'),
                  generated_arm='IQ2KT', predecessor_row=PARENT_ROW, predecessor_run=PARENT_RUN,
                  partial_dispositions=dispositions)
    if rc == 0:
        result['verified_iq2kt_tensors'] = verified_tensors
    if failure:
        result['failure'] = failure
    recovery.write(attempt / 'TERMINAL.json', result)
    if not smoke:
        recovery.write(root / 'RESULT.json', result)
    elif rc == 0:
        recovery.write(Path(os.environ['FILLER_DRYRUN_RESULT_PATH']), result)
    return rc


def complete() -> bool:
    path = HERE / 'official' / 'RESULT.json'
    if not path.is_file():
        return False
    result = recovery.load(path)
    return (result['row_id'] == ROW and result['mode'] == 'official' and result['rc'] == 0
            and result['state'] == 'complete-unsealed'
            and {MATRIX, *recovery.ARMS, 'RUN.json', 'results.jsonl', 'quant-IQ2KT.log'} <= result['outputs'].keys()
            and (path.parent / result['run_id'] / 'TERMINAL.json').read_bytes() == path.read_bytes()
            and all(stat_matches(item) for item in result['outputs'].values()))


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, recovery.interrupt)
    match sys.argv[1:]:
        case ['pin']:
            pin()
        case ['pin-runner']:
            pin_runner()
        case ['check']:
            check()
        case ['run']:
            raise SystemExit(run())
        case ['complete']:
            raise SystemExit(0 if complete() else 1)
        case _:
            raise SystemExit('expected pin, pin-runner, check, run, or complete')
