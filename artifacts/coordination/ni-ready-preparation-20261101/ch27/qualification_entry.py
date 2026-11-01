#!/usr/bin/python3
"""Same-job-entry first-request and active-cutoff proof for the canonical v14 engine.

This is a qualification fixture only. It launches the real candidate llama-server
from the pinned C5 launch artifact, with the production 48-thread arguments intact,
then sends the pinned frozen request. The keeper's synthetic two-SMT affinity bounds
qualification placement; no rate is inferred from that fixture.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

D = Path('/mnt/raid0/llm/tmp/codex-ni-v2-ch27-20261101')
RECIPE = D / 'production-recipe.json'
LAUNCH = D / 'production-launch.json'
REQUEST = D / 'request-manifest.json'
FIXTURE = D / 'qual_fixture.json'
EXPECTED_RECIPE_SHA = 'a48dbd8445caaa51ac1ae9756aa1f69936110cd2e937b6fd9209e56bc01272c4'
EXPECTED_REQUEST_DIGEST = '57c9006dfde7443a1bf9b58c08f1ac6834dddcdf3cafcfb770717f141b1d8640'
EXPECTED_MAIN = 'aa2143357d5382934580bcab6744b87b5fd1a6d4'
PORT = 18651


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def file_identity(path: Path) -> dict:
    st = path.stat()
    return {'path': str(path.resolve()), 'sha256': sha(path), 'device': st.st_dev,
            'inode': st.st_ino, 'size': st.st_size, 'mtime_ns': st.st_mtime_ns}


def atomic_json(path: Path, value: dict) -> None:
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')
    os.replace(tmp, path)


def launch_digest(path: Path, key: str) -> str:
    return json.loads(path.read_text())[key]['sha256']


def request_record() -> tuple[str, bytes, dict, str]:
    recipe = json.loads(RECIPE.read_text())
    manifest = json.loads(REQUEST.read_text())
    if (recipe.get('threads') != 48 or recipe.get('np') != 1 or recipe.get('ctx') != 8192
            or recipe.get('n_predict') != 256 or recipe.get('kv_unified') is not False
            or recipe.get('metric') != 'aggregate_tok_s'):
        raise SystemExit('REFUSED: production recipe shape changed')
    if len(manifest.get('prompts', [])) != 1:
        raise SystemExit('REFUSED: request manifest must contain the single original frozen request')
    row = manifest['prompts'][0]
    prompt_id, body_doc = row['prompt_id'], row['request']
    body = json.dumps(body_doc, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    body_sha = hashlib.sha256(body).hexdigest()
    request_digest = hashlib.sha256(json.dumps(
        [[prompt_id, body_sha]], ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
    if request_digest != EXPECTED_REQUEST_DIGEST:
        raise SystemExit(f'REFUSED: request digest {request_digest} != pinned native digest')
    if body_doc.get('n_predict') != 256 or len(body_doc.get('prompt', [])) != 102:
        raise SystemExit('REFUSED: frozen request tokens/n_predict changed')
    return prompt_id, body, recipe, request_digest


def source_argv(recipe: dict, launch: dict, cpus: str) -> tuple[list[str], dict]:
    if sha(RECIPE) != EXPECTED_RECIPE_SHA:
        raise SystemExit('REFUSED: production recipe hash mismatch')
    argv = list(launch['argv'])
    if (launch.get('executable', {}).get('path') != '/mnt/raid0/llm/kernels/builds/cpu-20261024-c72ec82f5-c5/bin/llama-server'
            or launch.get('executable', {}).get('sha256') != 'bfab92dffa31ad24f65ca53ec082ef8f1751b54d56efdc0f106bef797a72ee2e'
            or launch.get('model', {}).get('path') != recipe['model']
            or launch.get('model', {}).get('sha256') != '5ce89370720f8bf90890f439361282104c1aa1482d4013bb9a50923e758e71a4'
            or launch.get('drafter', {}).get('path') != recipe['spec_decode']['drafter']
            or launch.get('drafter', {}).get('sha256') != '5ff54097406a905cf3a724c709124ceb0e3e10235ee862298969e91c96fa96e6'):
        raise SystemExit('REFUSED: model, drafter, or C5 native binary pin changed')
    if argv[:3] != ['taskset', '-c', '0-95']:
        raise SystemExit('REFUSED: canonical launch taskset prefix changed')
    # The taskset prefix and llama-server both use -c. Search flags only in
    # the actual server argv, after the pinned executable, never across argv.
    executable = str(Path(launch['executable']['path']).resolve())
    try:
        server_index = argv.index(executable)
    except ValueError as exc:
        raise SystemExit('REFUSED: pinned server executable absent from launch argv') from exc
    if server_index < 3:
        raise SystemExit('REFUSED: server executable precedes canonical taskset prefix')
    argv[2] = cpus
    server_argv = argv[server_index:]
    def server_value(flag: str) -> str:
        try:
            index = server_argv.index(flag)
            return server_argv[index + 1]
        except (ValueError, IndexError) as exc:
            raise SystemExit(f'REFUSED: pinned server argv missing value for {flag}') from exc
    if (server_value('-t') != '48' or server_value('-tb') != '48' or server_value('-np') != '1'
            or server_value('-c') != '8192' or server_value('-m') != recipe['model']
            or server_value('-md') != recipe['spec_decode']['drafter']
            or '--no-kv-unified' not in server_argv or '-ngl' not in server_argv or server_value('-ngl') != '0'):
        raise SystemExit('REFUSED: production server argv no longer matches recipe')
    if server_value('--port') != str(PORT):
        raise SystemExit('REFUSED: production server port differs from reserved port')
    env = dict(launch['launch_env'])
    if env.get('LD_LIBRARY_PATH') != str(Path(launch['executable']['path']).parent):
        raise SystemExit('REFUSED: candidate library path differs from launch artifact')
    return argv, env


def birth_ticks(pid: int) -> int:
    fields = Path(f'/proc/{pid}/stat').read_text().rsplit(') ', 1)[1].split()
    return int(fields[19])


def owns_port(pid: int) -> bool:
    p = subprocess.run(['/usr/bin/ss', '-ltnp', f'sport = :{PORT}'],
                       capture_output=True, text=True, check=False)
    return p.returncode == 0 and f'pid={pid},' in p.stdout


def proc_snapshot(pid: int, expected_birth: int, expected_argv: list[str], expected_exe: Path) -> dict:
    """Read the captured child identity from procfs; fail closed on PID reuse or drift."""
    proc = Path(f'/proc/{pid}')
    stat = (proc / 'stat').read_text().rsplit(') ', 1)[1].split()
    birth = int(stat[19])
    if birth != expected_birth or stat[0] in ('Z', 'X', 'x'):
        raise RuntimeError(f'captured server identity is no longer live: pid={pid} birth={birth}')
    exe_link = os.readlink(proc / 'exe')
    exe = Path(exe_link.removesuffix(' (deleted)')).resolve()
    argv = [x for x in (proc / 'cmdline').read_bytes().decode().split('\0') if x]
    if exe != expected_exe.resolve() or argv != expected_argv:
        raise RuntimeError(f'captured server identity drift: exe={exe}, argv={argv!r}')
    env = {}
    for item in (proc / 'environ').read_bytes().split(b'\0'):
        if b'=' in item:
            k, v = item.split(b'=', 1)
            env[k.decode(errors='replace')] = v.decode(errors='replace')
    maps = (proc / 'maps').read_text()
    affinity = sorted(os.sched_getaffinity(pid))
    mapped = {}
    for line in maps.splitlines():
        fields = line.split()
        if len(fields) >= 6 and fields[-1].startswith('/') and ('libggml' in fields[-1] or 'libllama' in fields[-1]):
            path = fields[-1].removesuffix(' (deleted)')
            mapped[str(Path(path).resolve())] = path
    return {'pid': pid, 'birth_ticks': birth, 'exe': str(exe), 'argv': argv,
            'environment': env, 'cpu_affinity': affinity,
            'mapped_native_libraries': sorted(mapped)}


def stop_server(proc: subprocess.Popen, log, birth: int, expected_argv: list[str], executable: Path) -> dict:
    signal_sent = None
    if proc.poll() is None:
        proc_snapshot(proc.pid, birth, expected_argv, executable)
        proc.send_signal(signal.SIGTERM)
        signal_sent = 'SIGTERM'
        try:
            proc.wait(timeout=120)
        except subprocess.TimeoutExpired:
            proc_snapshot(proc.pid, birth, expected_argv, executable)
            proc.send_signal(signal.SIGKILL)
            signal_sent = 'SIGKILL'
            proc.wait(timeout=10)
    rc = proc.wait(timeout=1)
    try:
        stat = Path(f'/proc/{proc.pid}/stat').read_text().rsplit(') ', 1)[1].split()
        still_same_live = int(stat[19]) == birth and stat[0] not in ('Z', 'X', 'x')
    except (OSError, ValueError, IndexError):
        still_same_live = False
    if proc.poll() is None or still_same_live:
        raise RuntimeError(f'captured native server {proc.pid} was not drained')
    log.flush()
    return {'pid': proc.pid, 'birth_ticks': birth, 'signal': signal_sent,
            'returncode': rc, 'captured_process_drained': True}


def startup_readback(log_path: Path) -> dict:
    text = log_path.read_text(errors='replace')
    kv = re.search(r"kv_unified\s*=\s*'?\s*(true|false)", text, re.IGNORECASE)
    slots = re.search(r'n_slots\s*=\s*(\d+)\s*,\s*n_ctx_slot\s*=\s*(\d+)', text)
    threads = re.search(r'n_threads\s*=\s*(\d+)(?:\s*\(n_threads_batch\s*=\s*(\d+)\))?', text)
    if not (kv and slots and threads):
        raise RuntimeError('startup log lacks actual KV, slot/context, or thread readback')
    return {'kv_unified': kv.group(1).lower() == 'true',
            'slots': int(slots.group(1)), 'ctx_per_slot': int(slots.group(2)),
            'threads': int(threads.group(1)), 'batch_threads': int(threads.group(2) or threads.group(1)),
            'matched_lines': {'kv': kv.group(0), 'slots_context': slots.group(0), 'threads': threads.group(0)}}


def native_readback_ok(record: dict, recipe: dict, launch: dict) -> bool:
    """Shared fail-closed contract for live readback and model-free fixture checks."""
    try:
        proc = record['proc']
        startup = record['startup_log']
        props = record['props']
        slots = record['slots']
        expected_libs = {}
        for item in launch['dsos']:
            p = str(Path(item['path']).resolve())
            if 'libggml' in Path(p).name or 'libllama' in Path(p).name:
                expected_libs[p] = item['sha256']
        valid = (proc['exe'] == str(Path(launch['executable']['path']).resolve())
                 and record['exe_sha256'] == launch['executable']['sha256']
                 and proc['argv'] == launch['command_argv']
                 and len(proc['cpu_affinity']) == 2
                 and all(proc['environment'].get(k) == v for k, v in launch['launch_env'].items())
                 and set(record['mapped_library_sha256']) == set(expected_libs)
                 and record['mapped_library_sha256'] == expected_libs
                 and startup['kv_unified'] is recipe['kv_unified']
                 and startup['slots'] == recipe['np']
                 and startup['ctx_per_slot'] == recipe['ctx']
                 and startup['threads'] == recipe['threads']
                 and startup['batch_threads'] == recipe['threads']
                 and props['default_generation_settings']['n_ctx'] == recipe['ctx']
                 and props['total_slots'] == recipe['np']
                 and props['model_path'] == launch['model']['path']
                 and isinstance(slots, list) and len(slots) == recipe['np']
                 and all(s['n_ctx'] == recipe['ctx'] for s in slots))
        return bool(valid)
    except (KeyError, TypeError, ValueError):
        return False


def live_server_readback(proc: subprocess.Popen, birth: int, recipe: dict, launch: dict,
                         log_path: Path) -> dict:
    cmd = list(launch['command_argv'])
    identity = proc_snapshot(proc.pid, birth, cmd, Path(launch['executable']['path']))
    if identity['environment'].get('LD_LIBRARY_PATH') != launch['launch_env'].get('LD_LIBRARY_PATH'):
        raise RuntimeError('live server LD_LIBRARY_PATH differs from pinned launch environment')
    for key, value in launch['launch_env'].items():
        if identity['environment'].get(key) != value:
            raise RuntimeError(f'live server environment mismatch for {key}')
    exe_sha = sha(Path(f'/proc/{proc.pid}/exe'))
    if exe_sha != launch['executable']['sha256']:
        raise RuntimeError('live /proc executable digest differs from pinned executable')
    expected_libs = {}
    for item in launch['dsos']:
        p = Path(item['path']).resolve()
        if 'libggml' in p.name or 'libllama' in p.name:
            expected_libs[str(p)] = item['sha256']
    actual_libs = identity['mapped_native_libraries']
    if not actual_libs or set(actual_libs) != set(expected_libs):
        raise RuntimeError(f'actual mapped llama/ggml libraries differ from launch pin: {actual_libs!r}')
    mapped_hashes = {p: sha(Path(p)) for p in actual_libs}
    if mapped_hashes != expected_libs:
        raise RuntimeError('one or more mapped native library hashes differ from launch artifact')
    startup = startup_readback(log_path)
    status, props = http_json('GET', '/props')
    slots_status, slots_body = http_json('GET', '/slots')
    props_ctx = (props.get('default_generation_settings') or {}).get('n_ctx') if isinstance(props, dict) else None
    props_total_slots = props.get('total_slots') if isinstance(props, dict) else None
    slot_ctx = [slot.get('n_ctx') for slot in slots_body] if isinstance(slots_body, list) else None
    if status != 200 or slots_status != 200:
        raise RuntimeError('live /props or /slots returned non-200')
    record = {'proc': identity, 'exe_sha256': exe_sha, 'mapped_library_sha256': mapped_hashes,
              'startup_log': startup, 'props': props, 'slots': slots_body}
    if not native_readback_ok(record, recipe, launch):
        raise RuntimeError(f'live proc/maps/log/props/slots readback differs from pinned production: {record!r}')
    return record


def http_json(method: str, path: str) -> tuple[int, object]:
    req = urllib.request.Request(f'http://127.0.0.1:{PORT}{path}', method=method)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.status, json.loads(resp.read())


def native_prompt_count_ok(timings: dict, submitted_ids: int) -> bool:
    prompt_n, cache_n = timings.get('prompt_n'), timings.get('cache_n', 0)
    return (type(prompt_n) is int and type(cache_n) is int
            and prompt_n + cache_n == submitted_ids)


def first_request(proc: subprocess.Popen, prompt_id: str, body: bytes,
                  birth: int, log_path: Path, request_digest: str, recipe: dict,
                  recipe_sha: str, launch: dict, model_identity: dict,
                  drafter_identity: dict) -> dict:
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f'candidate server exited before health: {proc.returncode}')
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/health', timeout=2) as resp:
                if resp.status == 200 and owns_port(proc.pid):
                    break
        except (OSError, urllib.error.URLError, urllib.error.HTTPError):
            time.sleep(1)
    else:
        raise RuntimeError('candidate server failed health/own-PID proof')
    readback = live_server_readback(proc, birth, recipe, launch, log_path)
    req = urllib.request.Request(f'http://127.0.0.1:{PORT}/completion', data=body,
                                 headers={'Content-Type': 'application/json', 'Connection': 'close'})
    with urllib.request.urlopen(req, timeout=240) as resp:
        status = resp.status
        raw = resp.read()
    response = json.loads(raw)
    timings = response.get('timings', {})
    predicted_n = timings.get('predicted_n')
    rate = timings.get('predicted_per_second')
    prompt_n, cache_n = timings.get('prompt_n'), timings.get('cache_n', 0)
    submitted_ids = len(json.loads(body)['prompt'])
    if (status != 200 or type(predicted_n) is not int or predicted_n != 256
            or type(rate) not in (int, float) or rate <= 0
            or not native_prompt_count_ok(timings, submitted_ids)):
        raise RuntimeError('pinned request did not return matching native evaluated-token timing')
    model_path, drafter_path = Path(launch['model']['path']), Path(launch['drafter']['path'])
    model_sha, drafter_sha = model_identity['sha256'], drafter_identity['sha256']
    for path, before, expected in ((model_path, model_identity, launch['model']['sha256']),
                                   (drafter_path, drafter_identity, launch['drafter']['sha256'])):
        after = path.stat()
        if (before['sha256'] != expected or before['device'] != after.st_dev
                or before['inode'] != after.st_ino or before['size'] != after.st_size
                or before['mtime_ns'] != after.st_mtime_ns):
            raise RuntimeError(f'model input changed or its bytes differ from pin: {path}')
    return {
        'ok': True,
        'scope': 'TARGET_SCRATCH_SERVER',
        'manifest_sha256': request_digest,
        'production_recipe_sha256': recipe_sha,
        'prompt_id': prompt_id,
        'request_body_sha256': hashlib.sha256(body).hexdigest(),
        'prompt_tokens': prompt_n,
        'request_token_id_count': submitted_ids,
        'request_cache_tokens': cache_n,
        'n_ctx_total': readback['props']['default_generation_settings']['n_ctx'],
        'n_ctx_per_slot': readback['startup_log']['ctx_per_slot'],
        'total_slots': readback['props']['total_slots'],
        'kv_cache_mode': 'unified' if readback['startup_log']['kv_unified'] else 'split',
        'production_threads': readback['startup_log']['threads'],
        'native_server_binary_sha256': readback['exe_sha256'],
        'native_build_source_commit': launch['provenance']['source:head'],
        'native_build_source_branch': launch['provenance']['source:branch'],
        'native_model_sha256': model_sha,
        'native_drafter_sha256': drafter_sha,
        'model_file_identity': model_identity,
        'drafter_file_identity': drafter_identity,
        'native_readback': readback,
        'measured_tok_s': float(rate),
        'response_predicted_n': predicted_n,
        'response_sha256': hashlib.sha256(raw).hexdigest(),
        'stop': response.get('stop') is True,
    }


def main(phase: str) -> int:
    if phase not in ('normal', 'cutoff'):
        return 64
    nonce = os.environ['WS58_QUAL_NONCE']
    row_id = 'codex-ni-ch27-c5-raw-recalibration-v2-20261101'
    results = Path(os.environ['FILLER_RESULTS_DIR'])
    fixture_path = Path(os.environ['FILLER_QUAL_FIXTURE'])
    proof_path = Path(os.environ['WS58_QUAL_PROOF'])
    recipe_sha = sha(RECIPE)
    prompt_id, body, recipe, req_digest = request_record()
    fixture = json.loads(fixture_path.read_text())
    if fixture.get('schema') != 'epyc.qual.fixture.v1' or fixture.get('items') != 2:
        raise SystemExit('REFUSED: qualification fixture must pin normal and cutoff items')
    item = next((x for x in fixture['workloads'] if x.get('phase') == phase), None)
    if not item or item.get('prompt_id') != prompt_id or item.get('request_manifest_sha256') != req_digest:
        raise SystemExit('REFUSED: phase fixture does not bind the original request')
    cpus = os.environ.get('FILLER_CPUS', '')
    if not cpus or len(os.sched_getaffinity(0)) != 2:
        raise SystemExit('REFUSED: keeper qualification must use its actual two-SMT CPU placement')
    argv, env = source_argv(recipe, json.loads(LAUNCH.read_text()), cpus)
    launch = json.loads(LAUNCH.read_text())
    model_identity = file_identity(Path(launch['model']['path']))
    drafter_identity = file_identity(Path(launch['drafter']['path']))
    if model_identity['sha256'] != launch['model']['sha256'] or drafter_identity['sha256'] != launch['drafter']['sha256']:
        raise SystemExit('REFUSED: actual model/drafter bytes differ from canonical launch artifact')
    results.mkdir(parents=True, exist_ok=True)
    result_path = results / f'{phase}.json'
    log_path = results / f'{phase}.server.log'
    proc = None
    with log_path.open('wb') as log:
        try:
            proc = subprocess.Popen(argv, cwd=str(D), env=env, stdout=log, stderr=subprocess.STDOUT)
            pid = proc.pid
            birth = birth_ticks(pid)
            if os.getpgid(pid) != os.getpgrp():
                raise RuntimeError('native server did not inherit the captured qualification process group')
            first = first_request(proc, prompt_id, body, birth, log_path, req_digest,
                                  recipe, recipe_sha, launch, model_identity, drafter_identity)
            observed_cpus = sorted(os.sched_getaffinity(0))
            result = {'id': row_id, 'phase': phase, 'started': True, 'partial': phase == 'cutoff',
                      'disposition': 'UNKNOWN' if phase == 'cutoff' else 'complete',
                      'native_first_request': first, 'observed_cpus': observed_cpus,
                      'candidate_server_pid': pid, 'candidate_server_birth_ticks': birth,
                      'production_recipe_sha256': recipe_sha, 'source_request_sha256': req_digest}
            if phase == 'normal':
                atomic_json(result_path, result)
                result_writer = {'ok': True, 'result_path': str(result_path), 'sha256': sha(result_path)}
                drain = stop_server(proc, log, birth, launch['command_argv'],
                                    Path(launch['executable']['path']))
                proof = {'id': row_id, 'nonce': nonce, 'phase': 'normal', 'partial': False,
                         'first_request': first, 'result_writer': result_writer,
                         'observed_cpus': observed_cpus, 'disk': {'job_floor_gib': 150},
                         'children_drained': True, 'server_drain': drain}
                atomic_json(proof_path, proof)
                return 0
            event_path = Path(os.environ['WS58_QUAL_CUTOFF_EVENT'])
            event = {'id': row_id, 'nonce': nonce, 'phase': 'cutoff', 'native_first_event': True,
                     'native_pid': pid, 'native_birth_ticks': birth, 'first_request': first}
            atomic_json(event_path, event)
            stopfile = Path(os.environ['FILLER_STOPFILE'])
            deadline = time.monotonic() + 240
            while time.monotonic() < deadline and not stopfile.exists():
                if proc.poll() is not None:
                    raise RuntimeError('native server ended before keeper-triggered active STOP')
                time.sleep(0.05)
            if not stopfile.exists():
                raise RuntimeError('keeper did not issue active STOP after native first event')
            result['stop_observed'] = True
            result['partial'] = True
            result['disposition'] = 'UNKNOWN'
            drain = stop_server(proc, log, birth, launch['command_argv'],
                                Path(launch['executable']['path']))
            atomic_json(result_path, result)
            proof = {'id': row_id, 'nonce': nonce, 'phase': 'cutoff', 'partial': True,
                     'stop_observed': True, 'unknown_disposition': 'UNKNOWN',
                     'first_request': first, 'observed_cpus': observed_cpus,
                     'children_drained': True, 'server_drain': drain}
            atomic_json(proof_path, proof)
            return 75
        finally:
            if proc is not None and proc.poll() is None:
                launch = json.loads(LAUNCH.read_text())
                stop_server(proc, log, birth, launch['command_argv'],
                            Path(launch['executable']['path']))


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1] if len(sys.argv) == 2 else ''))
