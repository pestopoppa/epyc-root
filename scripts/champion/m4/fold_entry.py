#!/usr/bin/env python3
"""INF-22 M4 fold cell entry: `fold_entry.py PLAN CELL OUT` (the argv fold_gate.run formats).

One invocation = one cell = ONE fresh llama-server on the cell's sealed image:

  outer  load + verify() the sealed fold plan (seal, status BOUND, cell present), derive
         the cell (role, arm, backend, image, server_args, env, placement, model shas),
         take grant/STOP/HOLD/deadline from rowflow's FILLER_* env (refuse when missing),
         write OUT/cell-plan.json (the native per-cell plan), then run the inner phase
         under the M4 watcher (scripts/benchmark/m4_cpu_ownership/watch.run: STOP / HOLD /
         grant-change / deadline polling, cgroup.kill or session drain).
  inner  start the server through owned.spawn (pid + birth in the watcher's registry),
         prove placement/residency, run the sealed prompt pool through the P-BENCH-3
         measurement of server_np_sweep (run_prompt_batch + summarize_cell: aggregate
         decode tok/s from llama.cpp's own timings) plus a per-cell completeness
         record (requested vs produced, errors, truncations), stop the server and write OUT/cell-result.json.

Why not the backends' own entries: m4_cpu_recipe_entry/m4_cpu_recipe_compare verify a
12-cell, architect_general-only Q38 recipe plan against a hardcoded champion ref, and
m4_gpu_speed/launcher.py runs only a code-owned enrolled V2 plan whose enrollment must
never be populated from a row. Neither consumes a fold plan, so this entry reuses their
measurement and containment modules (watch, owned, entry._grant, server_np_sweep) and
binds them to the sealed fold plan instead. The GPU frame (prompt pool, 8 prompts,
seed 42, tier 1, n_predict 256, no warmup, np from the recipe, numactl/taskset prefix,
LD_LIBRARY_PATH) is the M4-GPU-AA-NOISE frame the 0.950 floor was calibrated on.

Exit 0 only when OUT/cell-result.json holds a valid measurement. 2 = refused before
launch, 1 = measurement failed or invalid, 124 = STOP/HOLD/grant/deadline interrupt.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OWNERSHIP = ROOT / 'scripts/benchmark/m4_cpu_ownership'
GPU_SPEED = ROOT / 'scripts/benchmark/m4_gpu_speed'

RESULT_SCHEMA = 'epyc.m4.fold_cell_result.v1'
CELL_PLAN_SCHEMA = 'epyc.m4.fold_cell_plan.v1'
SMOKE_SCHEMA = 'epyc.m4.fold_cell_smoke.v1'
# Reference frame: M4-GPU-AA-NOISE real-aa-plan.json sweep (the 0.950 floor's frame).
FRAME = {'prompt_limit': 8, 'prompt_seed': 42, 'tier': 1, 'n_predict': 256, 'warmup_prompts': 0,
         'startup_timeout_s': 900, 'request_timeout_s': 900}
DEFAULT_FLAGS = '/mnt/raid0/llm/tmp/compute-flags'
# Device facts from the reference native plan (m4-gpu-aa-noise run/real-native-plan.json).
DEVICES = {'mi210_0': {'kfd_vram_file': 'vram_57300',
                       'device_vram_path': '/sys/class/drm/card2/device/mem_info_vram_used',
                       'vram_limit_bytes': 64424509440}}
KFD_ROOT = Path('/sys/class/kfd/kfd/proc')
SENSITIVE = ('LD_', 'GGML_', 'LLAMA_', 'HSA_', 'HIP_', 'ROCR_', 'OMP_', 'KMP_')
GPU_LIBPATH = ('/opt/rocm/lib', '/usr/lib/llvm-20/lib')
MODEL_FLAGS = ('-m', '--model', '-md', '--model-draft', '--mmproj', '--chat-template-file')
FORBIDDEN_ARGS = ('--host', '--port', '--slot-save-path')
RAM_RESERVE = 64 * 1024**3
SAMPLE_S = 0.1


class Refused(Exception):
    pass


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def fold_gate():
    return sys.modules.get('fold_gate') or _load('fold_gate', HERE / 'fold_gate.py')


def ownership():
    if str(OWNERSHIP) not in sys.path:
        sys.path.insert(0, str(OWNERSHIP))
    import entry, owned, watch  # noqa: E401
    return entry, owned, watch


def sweep():
    if str(OWNERSHIP) not in sys.path:
        sys.path.insert(0, str(OWNERSHIP))
    return sys.modules.get('server_np_sweep') or _load('server_np_sweep', GPU_SPEED / 'server_np_sweep.py')


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def cpu_set(spec: str) -> set[int]:
    out = set()
    for part in str(spec).split(','):
        part = part.strip()
        if not part:
            continue
        a, _, b = part.partition('-')
        lo, hi = int(a), int(b or a)
        if hi < lo:
            raise Refused(f'bad cpu range {part}')
        out.update(range(lo, hi + 1))
    if not out:
        raise Refused('empty cpu list')
    return out


def arg_value(argv: list[str], *flags: str) -> str | None:
    for i, a in enumerate(argv):
        if a in flags:
            return argv[i + 1] if i + 1 < len(argv) else None
        for f in flags:
            if a.startswith(f + '='):
                return a.split('=', 1)[1]
    return None


# ---------------------------------------------------------------- plan + cell derivation
def load_plan(plan_path: Path, *, verify_live=True, env=None) -> dict:
    fg = fold_gate()
    try:
        plan = json.loads(Path(plan_path).read_text())
    except (OSError, ValueError) as exc:
        raise Refused(f'plan unreadable: {exc}')
    if plan.get('schema') != fg.PLAN_SCHEMA:
        raise Refused('plan: wrong schema')
    if plan.get('plan_sha256') != fg.plan_digest(plan):
        raise Refused('plan: seal broken (edited after bind)')
    if plan.get('status') != 'BOUND':
        raise Refused(f'plan: status {plan.get("status")} is not BOUND')
    if verify_live:
        errs = fg.verify(plan, env={} if env is None else env)
        if errs:
            raise Refused('plan verify: ' + '; '.join(errs))
    return plan


def derive_cell(plan: dict, cell_id: str) -> dict:
    """Everything the cell needs, derived only from the sealed plan."""
    fg = fold_gate()
    cells = [c for c in plan['cells'] if c.get('id') == cell_id]
    if len(cells) != 1:
        raise Refused(f'cell {cell_id!r} not in plan')
    c = cells[0]
    backend, arm = c['backend'], c['arm']
    if backend not in ('cpu', 'gpu') or arm not in ('baseline', 'candidate'):
        raise Refused('cell backend/arm invalid')
    img = plan['images'].get(c['image'])
    if not img or c['image'] != f'{backend}.{arm}':
        raise Refused(f'cell image {c["image"]} not sealed in plan')
    want_src = plan['champion'] if arm == 'baseline' else plan['candidate']
    if img.get('source') != want_src:
        raise Refused('cell image source differs from its arm commit')
    argv = list(c['server_args'])
    on = fg.M4_ON
    has_on = any(argv[i:i + len(on)] == on for i in range(len(argv)))
    if (arm == 'candidate') != has_on or (arm == 'baseline' and fg.M4_FLAG in argv):
        raise Refused('arm treatment differs from M4 on/off')
    for f in FORBIDDEN_ARGS:
        if arg_value(argv, f) is not None or f in argv:
            raise Refused(f'server_args may not set {f} (entry owns it)')
    sealed = plan['models']
    models = {}
    for i, a in enumerate(argv):
        if a in MODEL_FLAGS:
            p = str(Path(argv[i + 1]).resolve())
            if p not in sealed:
                raise Refused(f'{a} {argv[i + 1]} not sealed in plan models')
            models[p] = sealed[p]
            m = re.search(r'-(\d{5})-of-(\d{5})\.gguf$', p)
            if m:  # split GGUF: llama.cpp loads the sibling shards implicitly; each must be sealed
                for k in range(1, int(m.group(2)) + 1):
                    shard = p[:m.start()] + f'-{k:05d}-of-{m.group(2)}.gguf'
                    if shard not in sealed:
                        raise Refused(f'split shard {shard} not sealed in plan models')
                    models[shard] = sealed[shard]
    if arg_value(argv, '-m', '--model') is None:
        raise Refused('server_args lack -m')
    np_ = int(arg_value(argv, '-np', '--parallel') or 1)
    pl = c.get('placement') or {}
    if not pl.get('cpus') or not pl.get('numactl') or 'device' not in pl:
        raise Refused('placement incomplete (cpus, numactl, device)')
    cpu_set(pl['cpus'])
    device = pl['device']
    if backend == 'gpu' and device not in DEVICES:
        raise Refused(f'gpu cell device {device!r} unknown')
    if backend == 'cpu' and device != 'none':
        raise Refused('cpu cell must have device none')
    env = dict(c.get('env') or {})
    if any(not isinstance(k, str) or not isinstance(v, str) for k, v in env.items()):
        raise Refused('cell env must be str->str')
    if any(k.startswith(fg.HIDDEN_ENV_PREFIXES) for k in env):
        raise Refused('cell env carries a hidden M4 override')
    root = Path(img['root'])
    libpath = ':'.join([str(root / 'bin'), *(GPU_LIBPATH if backend == 'gpu' else ())])
    if 'LD_LIBRARY_PATH' in env and env['LD_LIBRARY_PATH'] != libpath:
        raise Refused('cell env LD_LIBRARY_PATH points away from its image')
    return {'schema': CELL_PLAN_SCHEMA, 'plan_sha256': plan['plan_sha256'], 'cell': c['id'],
            'role': c['role'], 'backend': backend, 'arm': arm, 'pair': c['pair'], 'position': c['position'],
            'source_commit': want_src, 'image': c['image'], 'image_root': str(root),
            'image_files': img['files'], 'binary': str(root / 'bin/llama-server'),
            'server_args': argv, 'np': np_, 'env': env, 'ld_library_path': libpath,
            'placement': pl, 'device': DEVICES.get(device), 'models': models,
            'prompt_pool': plan['prompt_pool'], 'frame': dict(FRAME)}


def server_command(cp: dict, port: int) -> list[str]:
    pl = cp['placement']
    return ['numactl', *pl['numactl'].split(), '--', 'taskset', '-c', pl['cpus'], cp['binary'],
            *cp['server_args'], '--host', '127.0.0.1', '--port', str(port), '--log-colors', 'off']


def server_env(cp: dict, base: dict) -> dict:
    env = {k: v for k, v in base.items() if not k.startswith(SENSITIVE)}
    env.update(cp['env'])
    env['LD_LIBRARY_PATH'] = cp['ld_library_path']
    return env


# ---------------------------------------------------------------- run-time authority
def runtime(env: dict, cp: dict) -> dict:
    """Grant/STOP/HOLD/deadline from rowflow's filler_run15.sh job contract."""
    need = ['FILLER_ID', 'FILLER_DEADLINE', 'FILLER_END', 'FILLER_STOPFILE', 'FILLER_CPUS', 'FILLER_PORTS']
    missing = [k for k in need if not env.get(k)]
    if missing:
        raise Refused('rowflow job contract missing: ' + ','.join(missing)
                      + ' (run under scripts/coordination/rowflow/filler_run15.sh; one keeper row for the fold)')
    smoke = env.get('FILLER_DRYRUN') == '1'
    if smoke and not env.get('FILLER_DRYRUN_DIR'):
        raise Refused('FILLER_DRYRUN=1 without FILLER_DRYRUN_DIR')
    flags = Path(env.get('FILLER_FLAGS_DIR') or DEFAULT_FLAGS)
    grants = Path(env.get('FILLER_GRANTS_DIR') or flags / 'grants')
    grant = grants / (env['FILLER_ID'] + '.grant')
    stop = Path(env['FILLER_STOPFILE'])
    try:
        deadline = int(env['FILLER_DEADLINE'])
        end = int(env['FILLER_END'])
    except ValueError:
        raise Refused('FILLER_DEADLINE/FILLER_END not epoch integers')
    if not stop.is_absolute():
        raise Refused('FILLER_STOPFILE not absolute')
    if stop.exists():
        raise Refused(f'STOP present: {stop}')
    if not flags.is_dir() or any(flags.glob('HOLD_*')):
        raise Refused(f'HOLD present or hold dir missing: {flags}')
    if not grant.is_file():
        raise Refused(f'grant missing: {grant}')
    if not time.time() < deadline < end:
        raise Refused('outside grant window or deadline passed')
    fields = dict(f.split('=', 1) for f in grant.read_text().split() if '=' in f)
    entry, _, _ = ownership()
    try:
        if smoke:  # keeper smoke: synthetic rowflow dry-run grant bound to this row id
            entry._grant(grant, fields.get('regions', ''), deadline, allow_dryrun=True, expected_row_id=env['FILLER_ID'])
        else:
            entry._grant(grant, fields.get('regions', ''), deadline, require_host_holds=cp['backend'] == 'cpu')
    except (OSError, ValueError, KeyError) as exc:
        raise Refused(f'grant refused: {exc}')
    if cp['backend'] == 'gpu' and env.get('FILLER_NEEDGPU') != '1':
        raise Refused('gpu cell without FILLER_NEEDGPU=1 (grant does not name mi210_0)')
    have = cpu_set(env['FILLER_CPUS'])
    if smoke:  # the smoke holds only its own few cpus: pin the health probe there, never the planned placement
        cp['placement'] = dict(cp['placement'], planned_cpus=cp['placement']['cpus'], cpus=env['FILLER_CPUS'])
    want = cpu_set(cp['placement']['cpus'])
    if not want <= have:
        raise Refused(f'placement cpus {cp["placement"]["cpus"]} outside granted FILLER_CPUS {env["FILLER_CPUS"]}')
    if not want <= os.sched_getaffinity(0):
        raise Refused('placement cpus outside this process affinity')
    port = int(env['FILLER_PORTS'].replace(',', ' ').split()[0])
    return {'grant': str(grant), 'stop': str(stop), 'hold': str(flags), 'deadline': deadline,
            'end': end, 'port': port, 'row_id': env['FILLER_ID'], 'grant_sha256': sha_bytes(grant.read_bytes()),
            'smoke': smoke}


def ram_check(cp: dict, meminfo: Path = Path('/proc/meminfo')) -> dict:
    need = sum(Path(p).stat().st_size for p in cp['models']) if cp['backend'] == 'cpu' else 0
    mem = dict(line.split(':', 1) for line in meminfo.read_text().splitlines() if ':' in line)
    avail = int(mem['MemAvailable'].split()[0]) * 1024
    if avail < need + RAM_RESERVE:
        raise Refused(f'insufficient RAM: available {avail} < models {need} + reserve {RAM_RESERVE}')
    return {'mem_available_bytes': avail, 'model_bytes': need, 'reserve_bytes': RAM_RESERVE}


def outer(plan_path: Path, cell_id: str, out: Path, env=None) -> int:
    env = dict(os.environ if env is None else env)
    fg = fold_gate()
    hidden = [k for k in env if k.startswith(fg.HIDDEN_ENV_PREFIXES)]
    if hidden:
        raise Refused('hidden M4 override in environment: ' + ','.join(hidden))
    plan = load_plan(plan_path)
    cp = derive_cell(plan, cell_id)
    if not out.is_dir() or any(p.name != 'entry.log' for p in out.iterdir()):
        raise Refused('OUT must be the fresh cell directory fold_gate created')
    rt = runtime(env, cp)
    cp['runtime'] = rt
    cp['ram'] = ram_check(cp)
    cp['server_argv'] = server_command(cp, rt['port'])
    raw = json.dumps(cp, indent=2, sort_keys=True).encode()
    (out / 'cell-plan.json').write_bytes(raw)
    _, _, watch = ownership()
    child = dict(env, M4_DELEGATED_CGROUP_PARENT=env.get('M4_DELEGATED_CGROUP_PARENT', '/sys/fs/cgroup'),
                 FOLD_CELL_PLAN_SHA256=sha_bytes(raw))
    cmd = [sys.executable, '-B', str(Path(__file__).resolve()), '--inner', str(plan_path), cell_id, str(out)]
    rc = watch.run(cmd, rt['grant'], rt['stop'], rt['hold'], rt['deadline'], out, env=child)
    wr = json.loads((out / 'watch-result.json').read_text())
    if wr.get('status') != 'closed' or wr.get('containment_empty') is not True:
        print(f'FOLD-ENTRY cell={cell_id} INVALID containment not proven empty', flush=True)
        return 1
    if rt['smoke']:
        ok = (out / 'smoke-health.json').is_file()
        print(f'FOLD-ENTRY cell={cell_id} SMOKE {"PASS" if ok else "FAIL"} rc={rc}', flush=True)
        return 75 if ok else 1
    if rc != 0:
        print(f'FOLD-ENTRY cell={cell_id} FAILED rc={rc} reason={wr.get("reason")}', flush=True)
        return 124 if rc == 124 else 1
    errs = validate_result(out / 'cell-result.json', cp)
    if errs:
        print(f'FOLD-ENTRY cell={cell_id} INVALID ' + '; '.join(errs), flush=True)
        return 1
    res = json.loads((out / 'cell-result.json').read_text())
    print(f'FOLD-ENTRY cell={cell_id} OK aggregate_decode_tps={res["aggregate_decode_tps"]:.3f}', flush=True)
    return 0


# ---------------------------------------------------------------- inner (under watch.run)
def output_record(r) -> dict:
    resp = r.response if isinstance(r.response, dict) else {}
    return {'qid': r.qid, 'success': bool(r.success), 'predicted_tokens': r.predicted_tokens,
            'stop_type': resp.get('stop_type'), 'truncated': bool(resp.get('truncated')),
            'request_sha256': r.request_sha256}


def completeness(outputs: list[dict], n_requested: int) -> dict:
    """Completeness of the measured batch: every request answered with tokens, no error, no truncation."""
    return {'n_requested': n_requested,
            'n_produced': sum(1 for o in outputs if o['success'] and (o['predicted_tokens'] or 0) > 0),
            'errors': sum(1 for o in outputs if not o['success']),
            'truncations': sum(1 for o in outputs if o['success'] and o['truncated'])}


def mapped_libs(pid: int, maps: Path | None = None) -> dict:
    lines = (maps or Path(f'/proc/{pid}/maps')).read_text().splitlines()
    libs = {}
    for line in lines:
        part = line.split()
        if len(part) >= 6 and ('libggml' in part[-1] or 'libllama' in part[-1] or 'libmtmd' in part[-1]):
            libs[str(Path(part[-1]).resolve())] = None
    return libs


def prove_image(cp: dict, pid: int) -> dict:
    root = Path(cp['image_root']).resolve()
    libs = mapped_libs(pid)
    if not any('libggml' in p for p in libs):
        raise RuntimeError('no libggml mapped by the server')
    sealed = {str((root / rel).resolve()): d for rel, d in cp['image_files'].items()}
    for p in libs:
        if not p.startswith(str(root) + '/'):
            raise RuntimeError(f'server mapped a library outside its image: {p}')
        if p not in sealed:
            raise RuntimeError(f'mapped library not sealed in plan: {p}')
        with open(p, 'rb') as fh:
            libs[p] = hashlib.file_digest(fh, 'sha256').hexdigest()
        if libs[p] != sealed[p]:
            raise RuntimeError(f'mapped library differs from seal: {p}')
    exe = Path(f'/proc/{pid}/exe').resolve()
    with open(exe, 'rb') as fh:
        exe_sha = hashlib.file_digest(fh, 'sha256').hexdigest()
    if str(exe) != str(Path(cp['binary']).resolve()) or exe_sha != cp['image_files']['bin/llama-server']:
        raise RuntimeError('running executable is not the sealed image binary')
    return {'exe': str(exe), 'exe_sha256': exe_sha, 'mapped': libs}


def residency_sample(cp: dict, pid: int) -> dict:
    s = {'timestamp_ns': time.time_ns(), 'pid': pid}
    st = Path(f'/proc/{pid}/status').read_text()
    for line in st.splitlines():
        if line.startswith(('VmRSS:', 'Cpus_allowed_list:', 'VmLck:')):
            k, v = line.split(':', 1)
            s[k] = v.strip()
    if cp['backend'] == 'gpu':
        dev = cp['device']
        s['own_vram_bytes'] = int((KFD_ROOT / str(pid) / dev['kfd_vram_file']).read_text())
        s['device_vram_bytes'] = int(Path(dev['device_vram_path']).read_text())
        s['kfd_process_count'] = len(list(KFD_ROOT.iterdir()))
    else:
        s['kfd_own_entry'] = (KFD_ROOT / str(pid)).exists() if KFD_ROOT.is_dir() else False
    return s


def sample_ok(cp: dict, s: dict) -> bool:
    if 'error' in s:
        return False
    if cp_set(s.get('Cpus_allowed_list', '')) - cpu_set(cp['placement']['cpus']):
        return False
    if cp['backend'] == 'gpu':
        return 0 < s['own_vram_bytes'] <= cp['device']['vram_limit_bytes'] and s['device_vram_bytes'] > 0
    return s.get('kfd_own_entry') is False


def cp_set(spec: str) -> set[int]:
    try:
        return cpu_set(spec)
    except (Refused, ValueError):
        return {-1}


def inner(plan_path: Path, cell_id: str, out: Path) -> int:
    raw = (out / 'cell-plan.json').read_bytes()
    if sha_bytes(raw) != os.environ.get('FOLD_CELL_PLAN_SHA256'):
        raise RuntimeError('cell-plan.json changed between outer and inner')
    cp = json.loads(raw)
    # Seal + status re-checked here; the full live re-hash (~100 s over ~200 GB of models) was done
    # by the outer phase seconds earlier, and by fold_gate.run just before that.
    plan = load_plan(plan_path, verify_live=False)
    if derive_cell(plan, cell_id)['server_args'] != cp['server_args']:
        raise RuntimeError('cell derivation changed')
    sw = sweep()
    _, owned, _ = ownership()
    rt = cp['runtime']
    pool = Path(cp['prompt_pool']['path'])
    if sha_bytes(pool.read_bytes()) != cp['prompt_pool']['sha256']:
        raise RuntimeError('prompt pool changed')
    fr = cp['frame']
    prompts = sw.load_prompt_batch(pool, limit=fr['prompt_limit'], seed=fr['prompt_seed'], tier=fr['tier'], suites=set())
    owner = subprocess.run(['ss', '-ltnH', f'sport = :{rt["port"]}'], capture_output=True, text=True)
    if owner.stdout.strip():
        raise RuntimeError(f'port {rt["port"]} already listening')
    env = server_env(cp, os.environ)
    cmd = cp['server_argv']
    model = sw.ModelSpec(label=cp['role'], path=Path(arg_value(cp['server_args'], '-m', '--model')))
    stop = Path(rt['stop'])
    proc = None
    t0 = time.time()
    samples: list[dict] = []
    result = None
    try:
        proc = sw.start_server(cmd, env, out / 'server.log')
        sw.wait_for_health(rt['port'], fr['startup_timeout_s'], proc)
        t_loaded = time.time()
        ss = subprocess.run(['ss', '-ltnp', f'sport = :{rt["port"]}'], capture_output=True, text=True, check=True)
        if f'pid={proc.pid},' not in ss.stdout:
            raise RuntimeError('health port is not owned by the captured server PID')
        image = prove_image(cp, proc.pid)
        if rt.get('smoke'):
            return smoke_hold(cp, out, proc, image, t_loaded - t0, stop, rt['deadline'])
        first = residency_sample(cp, proc.pid)
        if not sample_ok(cp, first):
            raise RuntimeError(f'placement/residency unproven before batch: {first}')
        halt = threading.Event()

        def sampler():
            while not halt.is_set():
                try:
                    samples.append(residency_sample(cp, proc.pid))
                except (OSError, ValueError) as exc:
                    samples.append({'timestamp_ns': time.time_ns(), 'error': repr(exc)})
                halt.wait(SAMPLE_S)
        th = threading.Thread(target=sampler, daemon=True)
        th.start()
        b0 = time.time_ns()
        try:
            results, wall_s = sw.run_prompt_batch(port=rt['port'], model=model, np_level=cp['np'], prompts=prompts,
                                                  n_predict=fr['n_predict'], request_timeout_s=fr['request_timeout_s'],
                                                  requests_path=out / 'requests.jsonl')
        finally:
            b1 = time.time_ns()
            halt.set()
            th.join(timeout=5)
        inside = [s for s in samples if b0 <= s.get('timestamp_ns', 0) <= b1]
        if not inside or not all(sample_ok(cp, s) for s in samples):
            raise RuntimeError('placement/residency unproven during the request batch')
        row = sw.summarize_cell(model=model, np_level=cp['np'], results=results, wall_s=wall_s, ttft_ms=0.0,
                                server_pid=proc.pid, server_command=cmd)
        batch_outputs = [output_record(r) for r in results]
        result = {'schema': RESULT_SCHEMA, 'plan_sha256': cp['plan_sha256'], 'cell': cp['cell'],
                  'role': cp['role'], 'backend': cp['backend'], 'arm': cp['arm'], 'pair': cp['pair'],
                  'position': cp['position'], 'source_commit': cp['source_commit'],
                  'aggregate_decode_tps': row['aggregate_decode_tps'], 'per_stream_decode_tps': row['per_stream_decode_tps'],
                  'success_count': row['success_count'], 'total_count': row['total_count'],
                  'decode_tokens_total': row['decode_tokens_total'], 'np': cp['np'],
                  'frame': fr, 'completeness': completeness(batch_outputs, len(prompts)),
                  'batch_outputs': batch_outputs,
                  'image': {'name': cp['image'], 'root': cp['image_root'], **image},
                  'models': cp['models'], 'server_argv': cmd,
                  'env': {k: v for k, v in env.items() if k.startswith(SENSITIVE)},
                  'placement': cp['placement'], 'residency': {'before': first, 'during': inside,
                                                              'samples': len(samples)},
                  'timing': {'start': t0, 'loaded': t_loaded, 'load_s': t_loaded - t0,
                             'batch_s': (b1 - b0) / 1e9, 'end': time.time()},
                  'row_id': rt['row_id'], 'grant_sha256': rt['grant_sha256'],
                  'prompt_pool_sha256': cp['prompt_pool']['sha256'],
                  'prompt_qids': [p.qid for p in prompts], 'summary': row}
    finally:
        if proc is not None:
            stopped = sw.stop_server(proc)
            if subprocess.run(['ps', '-p', str(proc.pid)], capture_output=True).returncode == 0:
                raise RuntimeError(f'server pid {proc.pid} still alive after stop')
            if result is not None:
                result['cleanup'] = stopped
    with (out / 'cell-result.json').open('x') as fh:
        json.dump(result, fh, indent=2, sort_keys=True, allow_nan=False)
        fh.flush()
        os.fsync(fh.fileno())
    return 0 if not validate_result(out / 'cell-result.json', cp) else 1


def smoke_hold(cp, out, proc, image, load_s, stop, deadline) -> int:
    """Keeper smoke = first real progress: this cell's server on its sealed image reached /health and its
    executable + mapped libraries match the seal. No request is sent, nothing is measured. Then hold until the
    smoke's STOP (the watcher kills us) or the deadline; 75 = controlled qualification stop."""
    doc = {'schema': SMOKE_SCHEMA, 'smoke_only': True, 'measurement': False, 'cell': cp['cell'],
           'plan_sha256': cp['plan_sha256'], 'health_load_s': load_s, 'pid': proc.pid,
           'image': {'name': cp['image'], **image}, 'models': cp['models'], 'placement': cp['placement']}
    with (out / 'smoke-health.json').open('x') as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
        fh.flush()
        os.fsync(fh.fileno())
    print(f'FOLD-ENTRY cell={cp["cell"]} SMOKE health in {load_s:.1f}s', flush=True)
    while not stop.exists() and time.time() < deadline:
        time.sleep(1)
    return 75


def validate_result(path: Path, cp: dict) -> list[str]:
    try:
        r = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        return [f'cell-result unreadable: {exc}']
    errs = []
    if r.get('schema') != RESULT_SCHEMA:
        errs.append('schema')
    for k in ('cell', 'arm', 'pair', 'position', 'plan_sha256', 'role', 'backend'):
        if r.get(k) != cp.get(k):
            errs.append(f'{k} mismatch')
    tps = r.get('aggregate_decode_tps')
    if not isinstance(tps, (int, float)) or not tps > 0:
        errs.append('aggregate_decode_tps not positive')
    if r.get('success_count') != r.get('total_count') or not r.get('total_count'):
        errs.append('not every request succeeded')
    c = r.get('completeness') or {}
    if not all(isinstance(c.get(k), int) for k in ('n_requested', 'n_produced', 'errors', 'truncations')):
        errs.append('completeness missing')
    elif c['n_requested'] != (r.get('frame') or {}).get('prompt_limit') or c['n_produced'] != c['n_requested'] \
            or c['errors'] or c['truncations']:
        errs.append('output incomplete')
    if (r.get('image') or {}).get('exe_sha256') != cp['image_files'].get('bin/llama-server'):
        errs.append('image sha not proven')
    if r.get('models') != cp.get('models'):
        errs.append('model shas differ from plan')
    return errs


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    is_inner = argv[:1] == ['--inner']
    if is_inner:
        argv = argv[1:]
    if len(argv) != 3:
        print('usage: fold_entry.py PLAN CELL OUT', file=sys.stderr)
        return 2
    plan, cell, out = Path(argv[0]), argv[1], Path(argv[2])
    try:
        return inner(plan, cell, out) if is_inner else outer(plan, cell, out)
    except Refused as exc:
        print(f'FOLD-ENTRY cell={cell} REFUSED {exc}', flush=True)
        return 2
    except (OSError, RuntimeError, ValueError, KeyError, TimeoutError) as exc:
        print(f'FOLD-ENTRY cell={cell} FAILED {type(exc).__name__}: {exc}', flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
