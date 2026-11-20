"""Dedicated rowflow CPU capture. Offline-prepared weights; no retries or redraws."""
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time
from urllib.request import build_opener, ProxyHandler

from bfcl_capture_run import Journal, capture_case
from bfcl_native import CATEGORIES, OfficialV3
from bfcl_residency import LocalNativeTransport, fingerprint


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def select_rows(manifest, cohort='multi-turn'):
    if cohort == 'single-turn':
        rows, count = manifest['cases'][:14], 14
        allowed = CATEGORIES
    elif cohort == 'multi-turn':
        rows, count = manifest['cases'][16:], 10
        allowed = {'multi_turn_base', 'multi_turn_composite', 'multi_turn_long_context',
                   'multi_turn_miss_func', 'multi_turn_miss_param'}
    else:
        raise ValueError('unknown coverage cohort')
    if len(rows) != count or len({r['case']['id'] for r in rows}) != count:
        raise ValueError('wrong selected coverage count or duplicate ID')
    if any(r['category'] not in allowed for r in rows):
        raise ValueError('unexpected selected category')
    return rows


def summarize(verdicts, total):
    known = sum(v.get('valid') is True or v.get('valid') is False for v in verdicts)
    return {'completed': len(verdicts), 'total': total, 'known': known,
            'unknown': len(verdicts) - known,
            'passed': sum(v.get('valid') is True for v in verdicts),
            'coverage_complete': len(verdicts) == total,
            'score': None, 'scope': 'selected coverage diagnostic; no representative score'}


def stop_server(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=15)
    if process.poll() is None:
        raise RuntimeError('owned server survived shutdown')


def run(directory):
    directory = Path(directory)
    config = json.loads((directory / 'CONFIG.json').read_text())
    smoke = os.environ.get('FILLER_SMOKE') == '1'
    out = (Path(os.environ['FILLER_DRYRUN_RESULT_PATH']).parent / 'bfcl-native'
           if smoke else directory / 'run')
    out.mkdir(parents=True, exist_ok=False)  # no retry, continuation or redraw
    prepared = json.loads((directory / 'MODEL.json').read_text())
    if fingerprint(Path(prepared['path']).stat()) != prepared['stat']:
        raise ValueError('model changed since offline verification')
    flags = Path(os.environ.get('FILLER_FLAGS_DIR', '/mnt/raid0/llm/tmp/compute-flags'))
    grants = Path(os.environ.get('FILLER_GRANTS_DIR', str(flags / 'grants')))
    grant_path = grants / (os.environ['FILLER_ID'] + '.grant')
    grant = grant_path.read_bytes() if grant_path.exists() else None
    if not smoke and not grant:
        raise ValueError('full capture requires grant')
    ending = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: ending.set())
    deadline = float(os.environ['FILLER_DEADLINE']) - 20
    stopfile = Path(os.environ.get('FILLER_STOPFILE', str(directory / 'STOP')))

    def stop():
        return (ending.is_set() or stopfile.exists() or time.time() >= deadline or
                (not smoke and (not grant_path.exists() or grant_path.read_bytes() != grant)))

    # Bind failure/race refuses capture; no endpoint reuse or request retry.
    with socket.socket() as candidate:
        candidate.bind(('127.0.0.1', 0))
        port = candidate.getsockname()[1]
    argv = [config['server'], '--model', prepared['path'], '--alias', config['model'],
            '--host', '127.0.0.1', '--port', str(port), '--n-gpu-layers', '0',
            '--threads', str(min(8, len(os.sched_getaffinity(0)))), '--threads-batch',
            str(min(8, len(os.sched_getaffinity(0)))), '--ctx-size', '32768',
            '--parallel', '1', '--jinja', '--no-warmup']
    runtime = {'model': config['model'], 'model_file': prepared, 'argv': argv}
    write_new(out / 'runtime.json', runtime)
    identity = {'model': config['model'], 'model_sha256': prepared['sha256'],
                'server_binary_sha256': config['server_binary_sha256'],
                'build_manifest_sha256': sha(directory / 'BUILD.json'),
                'runtime_manifest_sha256': sha(out / 'runtime.json')}
    write_new(out / 'attempt.json', {'identity': identity, 'smoke': smoke,
        'grant_sha256': hashlib.sha256(grant).hexdigest() if grant else None,
        'row': os.environ['FILLER_ID'], 'affinity': sorted(os.sched_getaffinity(0)),
        'config_sha256': sha(directory / 'CONFIG.json'), 'selection_sha256': sha(directory / 'SELECTION.json')})
    env = {**os.environ, 'LD_LIBRARY_PATH': config['library_path'],
           'HIP_VISIBLE_DEVICES': '-1', 'ROCR_VISIBLE_DEVICES': '-1', 'OMP_NUM_THREADS': '1'}
    verdicts = []
    with (out / 'server.log').open('xb') as log:
        process = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, env=env)
        write_new(out / 'server.json', {'pid': process.pid, 'argv': argv})
        try:
            opener = build_opener(ProxyHandler({}))
            ready = False
            while not stop() and process.poll() is None:
                try:
                    with opener.open(f'http://127.0.0.1:{port}/health', timeout=1) as response:
                        ready = response.status == 200
                except OSError:
                    pass
                if ready:
                    break
                ending.wait(.25)
            if not ready:
                raise RuntimeError('owned server not ready within grant')
            transport = LocalNativeTransport(process.pid, port, identity,
                directory / 'BUILD.json', out / 'runtime.json', timeout=300)
            if smoke:
                # Synthetic engineering input, no corpus/gold/checker exposure.
                journal = Journal(out / 'smoke.jsonl')
                try:
                    payload = {'model': config['model'], 'messages': [{'role': 'user',
                        'content': 'Use add to add 2 and 3.'}], 'tools': [{'type': 'function',
                        'function': {'name': 'add', 'description': 'Add two integers',
                        'parameters': {'type': 'object', 'properties': {'a': {'type': 'integer'},
                        'b': {'type': 'integer'}}, 'required': ['a', 'b']}}}],
                        'tool_choice': 'auto', 'max_tokens': 24, 'temperature': 0,
                        'seed': 20261031, 'stream': False}
                    journal.append({'kind': 'identity', 'identity': identity, 'software_control': False})
                    journal.append({'kind': 'residency', 'phase': 'before', 'proof': transport.probe()})
                    journal.append({'kind': 'exposure', 'request': payload})
                    response = transport(payload)
                    journal.append({'kind': 'response', 'response': response})
                    journal.append({'kind': 'residency', 'phase': 'after', 'proof': transport.probe()})
                    if not response.get('choices'):
                        raise ValueError('smoke native response has no choices')
                finally:
                    journal.close()
                summary = {'status': 'smoke_pass', 'benchmark': 'bfcl_v3',
                           'synthetic_noncohort': True, 'completed': 1, 'score': None, 'identity': identity}
            else:
                bridge = OfficialV3(config['checker'])
                rows = select_rows(json.loads((directory / 'SELECTION.json').read_text()),
                                   config.get('cohort', 'multi-turn'))
                for row in rows:
                    if stop() or time.time() + 330 >= deadline:
                        break
                    verdict = capture_case(bridge, row, config['model'], identity,
                        config['catalog'], out / (row['case']['id'] + '.jsonl'), transport,
                        lambda: stop() or time.time() + 330 >= deadline)
                    verdicts.append(verdict)
                    write_new(out / (row['case']['id'] + '.result.json'), verdict)
                    if verdict.get('valid') is None:
                        break
                summary = {'status': 'complete' if len(verdicts) == len(rows) else 'partial',
                           'benchmark': 'bfcl_v3', 'cohort': config.get('cohort', 'multi-turn'),
                           **summarize(verdicts, len(rows))}
            write_new(out / 'RESULT.json', summary)
            if smoke:
                write_new(Path(os.environ['FILLER_DRYRUN_RESULT_PATH']), summary)
            write_new(out / 'TERMINAL.json', summary)
        except BaseException as error:
            write_new(out / 'ABORTED.json', {'status': 'aborted', 'score': None,
                'error': str(error), 'error_type': type(error).__name__,
                'completed': len(verdicts)})
            raise
        finally:
            stop_server(process)
            write_new(out / 'shutdown.json', {'pid': process.pid, 'returncode': process.returncode})


if __name__ == '__main__':
    run(sys.argv[1])
