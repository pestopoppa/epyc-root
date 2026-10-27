#!/usr/bin/env python3
"""Private experimental prepare/replay; never point at a shared source tree."""
import hashlib, json, os, pathlib, signal, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parent
TOOL = ROOT / 'tool'
NODE = pathlib.Path('/usr/local/bin/node').resolve()
BUDGET = '16777216'

def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()

def tree(path, exclude=()):
    result = {}
    for base, dirs, files in os.walk(path, followlinks=True):
        dirs[:] = sorted(d for d in dirs if d not in exclude)
        for name in sorted(files):
            p = pathlib.Path(base) / name
            if p.is_file(): result[str(p.relative_to(path))] = digest(p)
    return result

def identity(source):
    return {'source': tree(source, {'.git', '.gitnexus'}),
            'tool': tree(TOOL), 'node': digest(NODE), 'wrapper': digest(pathlib.Path(__file__)), 'chunkBudget': BUDGET}

def atomic(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, sort_keys=True))
    os.replace(temp, path)

def run_bounded(command, env, stage, state):
    cpus = os.sched_getaffinity(0)
    max_threads = 24 if stage == 'prepare19' else 12
    def interrupted(sig, frame):
        raise RuntimeError(f'interrupted by signal {sig}')
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, interrupted)
    supervised = os.environ.get('GNX_OUTER_SUPERVISOR') == '1'
    child = subprocess.Popen(command, env=env, start_new_session=not supervised)
    peak = 0
    try:
        while child.poll() is None:
            try: tids = list(pathlib.Path(f'/proc/{child.pid}/task').iterdir())
            except FileNotFoundError:
                if child.poll() is not None: break
                raise
            peak = max(peak, len(tids))
            if len(tids) > max_threads: raise RuntimeError('node thread bound exceeded')
            for tid in tids:
                try:
                    if os.sched_getaffinity(int(tid.name)) != cpus:
                        raise RuntimeError('node thread affinity drift')
                except ProcessLookupError: pass
            if pathlib.Path(ROOT / 'STOP').exists() or pathlib.Path('/mnt/raid0/llm/tmp/HOLD_GPU_FOR_QUIET_20261024').exists() or list(pathlib.Path('/mnt/raid0/llm/tmp/compute-flags').glob('HOLD_*')):
                raise RuntimeError('STOP or HOLD')
            deadline = os.environ.get('FILLER_DEADLINE')
            if deadline and time.time() >= int(deadline): raise RuntimeError('deadline')
            time.sleep(.2)
        return child.returncode
    finally:
        if child.poll() is None:
            if supervised: child.terminate()
            else: os.killpg(child.pid, signal.SIGTERM)
            try: child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if supervised: child.kill()
                else: os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        atomic(state / f'{stage}-threads.json', {'peak_node_tids':peak, 'limit':max_threads, 'affinity':sorted(cpus)})

def main():
    stage, src, state = sys.argv[1:]
    src, state = pathlib.Path(src).resolve(), pathlib.Path(state).resolve()
    if not src.is_relative_to(ROOT) or not state.is_relative_to(ROOT):
        raise SystemExit('source and state must be private scratch descendants')
    state.mkdir(parents=True, exist_ok=True)
    manifest = state / 'identity.json'
    receipt = state / 'prepared.json'
    env = {k: os.environ[k] for k in ('HOME', 'PATH', 'TMPDIR', 'XDG_CACHE_HOME', 'LANG', 'LC_ALL') if k in os.environ}
    env.update(GITNEXUS_HOME=str(state / 'registry'), GITNEXUS_CHUNK_BYTE_BUDGET=BUDGET,
               GNX_SPLIT_REPORT_CACHE='1', UV_THREADPOOL_SIZE='1',
               GITNEXUS_PARSE_CHUNK_CONCURRENCY='1', GITNEXUS_EMBEDDING_THREADS='1',
               GITNEXUS_LBUG_EXTENSION_INSTALL='never', GITNEXUS_LBUG_BUFFER_BYTES='536870912',
               GITNEXUS_LBUG_MAX_DB_SIZE='8589934592', LD_PRELOAD=str(TOOL / 'gitnexus-lbug-cap.so'),
               OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               NODE_OPTIONS='--max-old-space-size=8192')
    if stage in ('prepare', 'prepare19'):
        if receipt.exists() or manifest.exists(): raise SystemExit('state already used')
        if (src / '.gitnexus').exists(): raise SystemExit('prepare requires fresh private storage')
        before = identity(src)
        if stage == 'prepare19':
            seal = ROOT / 'preseal.json'
            if not seal.is_file() or json.loads(seal.read_text()) != before:
                raise SystemExit('source or runtime differs from reviewed preseal')
        env['GNX_SPLIT_PREPARE_RECEIPT'] = str(receipt)
        workers = '19' if stage == 'prepare19' else '2'
    elif stage == 'resolve':
        if not receipt.is_file() or not manifest.is_file(): raise SystemExit('missing preparation receipt')
        before = json.loads(manifest.read_text())
        cache = before.pop('cache')
        if identity(src) != before or tree(src / '.gitnexus') != cache:
            raise SystemExit('source, runtime or cache identity drift')
        workers = '1'
    else: raise SystemExit('expected prepare or resolve')
    rc = run_bounded([str(NODE), '--v8-pool-size=1', str(TOOL / 'bootstrap.cjs'), 'analyze', str(src),
                      '--force', '--index-only', '--skip-git', '--workers', workers], env, stage, state)
    if identity(src) != before: raise SystemExit('source or runtime identity drift during analysis')
    if stage in ('prepare', 'prepare19'):
        if rc == 0 or not receipt.is_file(): raise SystemExit('prepare did not reach boundary')
        if any((src / '.gitnexus' / p).exists() for p in ('lbug', 'meta.json')):
            raise SystemExit('unexpected prepare index publication')
        before['cache'] = tree(src / '.gitnexus')
        atomic(manifest, before)
        print('PREPARED: no complete index published')
    elif rc:
        raise SystemExit(rc)
    else:
        print('RESOLVED: verify graph sentinels before publication')

if __name__ == '__main__': main()
