#!/usr/bin/python3
"""Real PB-QCOST entry used by keeper normal/cutoff qualification only."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import sys
import time

D = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(D))
import pb_qcost_1_q as P
from model_identity import verify_model_identity


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def proc_birth(pid: int) -> int:
    return int(Path(f'/proc/{pid}/stat').read_text().rsplit(') ', 1)[1].split()[19])


def atomic_json(path: Path, obj: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(obj, sort_keys=True, separators=(',', ':')).encode() + b'\n'
    tmp = path.with_name(path.name + f'.{os.getpid()}.tmp')
    tmp.write_bytes(raw)
    os.replace(tmp, path)
    return hashlib.sha256(raw).hexdigest()


def proc_alive(pid: int, birth: int) -> bool:
    try:
        stat = Path(f'/proc/{pid}/stat').read_text().rsplit(') ', 1)[1].split()
        return int(stat[19]) == birth and stat[0] not in ('Z', 'X', 'x')
    except (OSError, ValueError, IndexError):
        return False


def qualified_first_request(probe, row: dict, manifest: dict) -> dict:
    argv = probe.srv.argv
    def option(flag: str) -> str:
        try: return argv[argv.index(flag) + 1]
        except (ValueError, IndexError): raise RuntimeError(f'live server argv lacks {flag}')
    recipe = Path(manifest['production_recipe']['path'])
    expected = json.loads(recipe.read_text())
    actual = {
        'model': option('-m'), 'parallel': int(option('-np')), 'ctx': int(option('-c')),
        'threads': int(option('-t')), 'unified': '--kv-unified' in argv,
        'port': int(option('--port')),
    }
    if any(actual[key] != value for key, value in expected['server'].items()):
        raise RuntimeError(f'actual server argv differs from normalized production recipe: {actual!r}')
    if actual['port'] not in manifest['ports']:
        raise RuntimeError(f'actual server port is not the predeclared unique qualification port: {actual["port"]}')
    rb = probe.srv.readback or {}
    slot_readback = rb.get('n_slots_n_ctx_slot')
    props_status, props = probe.client._req('GET', '/props', timeout=20)
    slot_props = probe.client.slots()
    props_ctx = (props.get('default_generation_settings') or {}).get('n_ctx') if isinstance(props, dict) else None
    props_slots = props.get('total_slots') if isinstance(props, dict) else None
    slot_contexts = [s.get('n_ctx') for s in slot_props] if isinstance(slot_props, list) else None
    if (props_status != 200 or props_slots != actual['parallel'] or props_ctx != manifest['per_slot_n_ctx_required'] or
            not isinstance(slot_contexts, list) or len(slot_contexts) != actual['parallel'] or
            any(value != manifest['per_slot_n_ctx_required'] for value in slot_contexts) or
            props.get('model_path') != expected['server']['model'] or
            slot_readback != [actual['parallel'], manifest['per_slot_n_ctx_required']] or
            rb.get('proc_cmdline_matches_argv') is not True or rb.get('exe_matches_binary') is not True or
            not rb.get('hip_mapped') or rb.get('ggml_all_from_bin_dir') is not True or
            'true' not in str(rb.get('kv_mode_from_launch_log', ''))):
        raise RuntimeError(f'native server readback does not prove pinned slots/context/KV/binary/linkage: {rb!r}')
    if os.getpgid(probe.srv.proc.pid) != os.getpgrp():
        raise RuntimeError('native server escaped captured launcher process group')
    if row.get('http') != 200 or not row.get('ttft_ms') or row.get('length') != manifest['prompt_tokens_required']:
        raise RuntimeError(f'actual PBQ first request did not meet pinned prompt contract: {row!r}')
    return {
        'ok': True, 'scope': 'TARGET_SCRATCH_SERVER',
        'manifest_sha256': manifest['request_manifest_sha256'],
        'production_recipe_sha256': manifest['production_recipe']['sha256'],
        'kv_cache_mode': 'unified', 'n_ctx_total': actual['ctx'],
        'n_ctx_per_slot': slot_readback[1], 'total_slots': slot_readback[0],
        'native_readback': {'n_slots_n_ctx_slot': slot_readback,
            'proc_cmdline_matches_argv': rb['proc_cmdline_matches_argv'],
            'exe_matches_binary': rb['exe_matches_binary'],
            'kv_mode_from_launch_log': rb['kv_mode_from_launch_log'],
            'hip_mapped': rb['hip_mapped'], 'ggml_all_from_bin_dir': rb['ggml_all_from_bin_dir']},
        'prompt_tokens': row['length'],
        'measured_tok_s': row['length'] / (row['ttft_ms'] / 1000.0),
        'request_http': row['http'], 'request_wall_s': row['ttft_ms'] / 1000.0,
        'server_pid': probe.srv.proc.pid, 'server_birth_ticks': proc_birth(probe.srv.proc.pid),
        'server_argv_sha256': hashlib.sha256('\0'.join(argv).encode()).hexdigest(),
        'threads': actual['threads'], 'model': actual['model'], 'port': actual['port'],
    }


def run() -> int:
    phase = os.environ.get('FILLER_QUAL_PHASE', '')
    if phase not in ('normal', 'cutoff'):
        raise RuntimeError(f'unsupported qualification phase {phase!r}')
    if Path(os.environ['FILLER_QUAL_FIXTURE']).resolve() != Path(__file__).resolve():
        raise RuntimeError('fixture path differs from keeper-bound file')
    manifest_path = Path(os.environ['WS58_MANIFEST_PATH'])
    manifest = json.loads(manifest_path.read_text())
    if manifest['production'] is not True or manifest['id'] != os.environ['FILLER_ID']:
        raise RuntimeError('manifest/production/row identity mismatch')
    if manifest['request_manifest_sha256'] != sha(Path(manifest['production_recipe']['path'])):
        raise RuntimeError('request manifest differs from recipe pin')
    proof_path = Path(os.environ['WS58_QUAL_PROOF'])
    results = Path(os.environ['FILLER_RESULTS_DIR'])
    out = results / 'run'
    args = P.argparse.Namespace(
        out=str(out), deadline_epoch=float(os.environ['FILLER_END']) - 60,
        prompt_set=str(D / 'prompt_set.jsonl'), argv_file=str(D / 'argv.txt'),
        launch_prefix='env HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0 numactl --membind=3 -- taskset -c ' + os.environ['FILLER_CPUS'],
        champion_bin='/mnt/raid0/llm/kernels/builds/gpu-20261020-dd3d9721c/bin/llama-server',
        port=manifest['ports'][0], card=str(P.K.DEFAULT_CARD), vram_ceiling_gib=60.,
        vram_free_max_gib=2., load_timeout_s=240, require_hsa_knob=True,
    )
    identity = verify_model_identity()
    probe = P.Probe(args)
    probe.phase_id = f'qual-{phase}-{os.environ["WS58_QUAL_NONCE"]}'
    stop, state = None, []
    try:
        probe.start_server(512)
        probe.erase_all()
        stop, state = probe.start_feeders(1)
        row = probe.run_prefill(1, 1, manifest['prompt_tokens_required'], state)
        first = qualified_first_request(probe, row, manifest)
        if phase == 'normal':
            probe.stop_feeders(stop, state)
            probe.stop_server()
            if proc_alive(first['server_pid'], first['server_birth_ticks']):
                raise RuntimeError('normal server PID did not drain')
            result = results / 'QUAL-RESULT.json'
            result_sha = atomic_json(result, {'phase': phase, 'id': manifest['id'],
                'first_request': first, 'native_row': row, 'model_identity': identity,
                'production_recipe_sha256': manifest['production_recipe']['sha256']})
            atomic_json(proof_path, {'id': manifest['id'], 'nonce': os.environ['WS58_QUAL_NONCE'],
                'phase': phase, 'observed_cpus': sorted(os.sched_getaffinity(0)),
                'first_request': first, 'model_identity': identity,
                'result_writer': {'ok': True, 'result_path': str(result), 'sha256': result_sha},
                'disk': {'job_floor_gib': manifest['job_floor_gib']},
                'children_drained': True})
            return 0
        event_path = Path(os.environ['WS58_QUAL_CUTOFF_EVENT'])
        event = {'id': manifest['id'], 'nonce': os.environ['WS58_QUAL_NONCE'], 'phase': 'cutoff',
            'native_first_event': True, 'native_pid': first['server_pid'],
            'native_birth_ticks': first['server_birth_ticks'], 'first_request': first}
        atomic_json(event_path, event)
        stopfile = Path(os.environ['FILLER_STOPFILE'])
        deadline = time.monotonic() + 230
        while not stopfile.exists() and time.monotonic() < deadline:
            if not proc_alive(first['server_pid'], first['server_birth_ticks']):
                raise RuntimeError('native server exited before active STOP')
            time.sleep(.05)
        stop_observed = stopfile.exists()
        if not stop_observed:
            raise RuntimeError('active STOP not observed before qualification timeout')
        probe.stop_feeders(stop, state)
        probe.stop_server()
        if proc_alive(first['server_pid'], first['server_birth_ticks']):
            raise RuntimeError('cutoff server PID did not drain')
        partial = results / 'PARTIAL.json'
        atomic_json(partial, {'partial': True, 'unknown_disposition': 'UNKNOWN',
            'stop_observed': True, 'first_request': first, 'model_identity': identity})
        atomic_json(proof_path, {'id': manifest['id'], 'nonce': os.environ['WS58_QUAL_NONCE'],
            'phase': phase, 'observed_cpus': sorted(os.sched_getaffinity(0)),
            'first_request': first, 'model_identity': identity, 'partial': True, 'stop_observed': True,
            'unknown_disposition': 'UNKNOWN', 'children_drained': True})
        return 75
    finally:
        probe.deadline_hit.set()
        if stop is not None:
            probe.stop_feeders(stop, state)
        probe.stop_server()
        for server in probe.servers:
            if server['srv'].proc and server['srv'].proc.poll() is None:
                raise RuntimeError('owned native server did not exit')


if __name__ == '__main__':
    try:
        raise SystemExit(run())
    except BaseException:
        raise
