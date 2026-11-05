#!/usr/bin/env python3
"""Q38P-3a spec-off paired ROCm serving comparison with in-decode GPU residency."""
import hashlib, json, os, signal, socket, statistics, subprocess, sys, time, urllib.request
D = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, D)
import gpuproof as gp

OUT = os.path.join(D, 'smoke-out' if os.environ.get('FILLER_SMOKE') == '1' else 'out'); RES = os.path.join(OUT, 'results.jsonl'); SUM = os.path.join(OUT, 'summary.json')
DONE = os.path.join(OUT, 'STAGE1-COMPLETE.json')
IDENT = json.load(open(os.path.join(D, 'IDENTITY.json'))); ARMS = IDENT['arms']; G = IDENT['gate']
STOPF = os.environ.get('FILLER_STOPFILE', os.path.join(D, 'STOP'))
DEADLINE = int(os.environ.get('FILLER_DEADLINE', str(int(time.time()) + 5400)))
PLUMB = os.environ.get('FILLER_DRYRUN') == '1' or os.environ.get('FILLER_SMOKE') == '1'
PORT = 18935; HOST = '127.0.0.1'; CPUS = os.environ.get('FILLER_CPUS', '184-191')
LAUNCH_NEED_S = 420; OWN_VRAM_MIN = 20 * 1024**3
DROP = ('HIP_VISIBLE_DEVICES', 'ROCR_VISIBLE_DEVICES', 'CUDA_VISIBLE_DEVICES', 'HSA_NO_SCRATCH_RECLAIM')
PARITY = ["Explain in two sentences what a hash table is.", "Write a Python function that reverses a linked list.",
          "List three causes of the French Revolution."]
DECODE = ["Write a detailed explanation of how TCP congestion control works, covering slow start and congestion avoidance.",
          "Implement a thread-safe LRU cache in C++ with get and put methods, and explain the design.",
          "Summarize the main ideas of the theory of evolution by natural selection for a high-school student.",
          "Write a bash script that finds the ten largest files under a directory and prints their sizes.",
          "Describe the differences between supervised, unsupervised and reinforcement learning with examples."]
BENCH = [('pp512', 512, 0), ('pp2048', 2048, 0), ('pp512@d16384', 512, 16384)]


def now(): return time.strftime('%FT%TZ', time.gmtime())
def append(u):
    with open(RES, 'a') as f: f.write(json.dumps(u) + '\n'); f.flush(); os.fsync(f.fileno())
def atomic(p, o):
    t = p + '.tmp'; json.dump(o, open(t, 'w'), indent=1); os.replace(t, p)
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''): h.update(b)
    return h.hexdigest()
def med(x): return statistics.median(x) if x else None


def gate_dependency():
    p = IDENT['depends_on']['result']
    try: v = json.load(open(p)).get('verdict')
    except (OSError, ValueError): v = None
    return v == 'PASS', v


def arm_env(arm):
    a = ARMS[arm]; e = {k: v for k, v in os.environ.items() if k not in DROP}
    e['LD_LIBRARY_PATH'] = a['ld']; e['HSA_OVERRIDE_CPU_AFFINITY_DEBUG'] = '0'; e.update(a['env']); return e


def server_argv(arm):
    a = ARMS[arm]
    return ['taskset', '-c', CPUS, a['bin'] + '/llama-server', '-m', IDENT['model'], '--host', HOST, '--port', str(PORT),
            '-np', '1', '-c', '65536', '-t', '8', '--load-threads', '8', '-b', '512', '-ub', '512', '--flash-attn', 'on', '--jinja',
            '-ctk', 'q8_0', '-ctv', 'q8_0', '--kv-unified', '--no-mmap', '-ngl', 'all', '--ctx-checkpoints', '32',
            '--chat-template-file', IDENT['chat_template'], '--no-cache-idle-slots', '--device', 'ROCm0']


def bench_argv(arm):
    a = ARMS[arm]
    return ['taskset', '-c', CPUS, a['bin'] + '/llama-bench', '-m', IDENT['model'], '-ngl', '99', '-fa', '1', '-ctk', 'q8_0',
            '-ctv', 'q8_0', '-b', '512', '-ub', '512', '-t', '8', '-mmp', '0', '-p', '512,2048', '-n', '0', '-d', '0,16384',
            '-r', '3', '-o', 'json']


def http(path, body=None, timeout=600):
    req = urllib.request.Request(f'http://{HOST}:{PORT}{path}', data=json.dumps(body).encode() if body else None,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read())


def stream_decode(prompt):
    body = {'prompt':prompt, 'n_predict':(64 if PLUMB else 256), 'temperature':0, 'top_k':1, 'seed':0, 'cache_prompt':False, 'stream':True}
    req = urllib.request.Request(f'http://{HOST}:{PORT}/completion', data=json.dumps(body).encode(), headers={'Content-Type':'application/json'})
    stamps=[]; timing={}
    with urllib.request.urlopen(req, timeout=600) as response:
        for line in response:
            if not line.startswith(b'data: '): continue
            value=json.loads(line[6:])
            if value.get('content'): stamps.append(time.time())
            if value.get('timings'): timing=value['timings']
    if len(stamps)<2 or not timing: raise RuntimeError('missing streamed decode interval or timing')
    return stamps[0],stamps[-1],timing

def port_free():
    """Free = nothing listening (connect refused) AND bindable with SO_REUSEADDR (TIME_WAIT from our own closed requests
    does not count as busy; llama-server binds with SO_REUSEADDR too)."""
    c = socket.socket(); c.settimeout(1)
    try:
        c.connect((HOST, PORT)); return False          # something is listening
    except OSError: pass
    finally: c.close()
    s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try: s.bind((HOST, PORT)); return True
    except OSError: return False
    finally: s.close()


def pid_alive(pid):
    # ps -p, never kill -0 (kill -0 is blind on this host)
    st = subprocess.run(['ps', '-p', str(pid), '-o', 'stat='], capture_output=True, text=True).stdout.strip()
    return st != '' and not st.startswith('Z')   # a zombie holds no GPU or port


def release(pid, timeout=60):
    """After a phase: wait for OUR captured pid to exit (TERM then KILL on that pid only), for its KFD entry to vanish and
    for the port to be free. Returns a dict of what was observed; 'ok' False means the GPU/port was not released."""
    t0 = time.time(); esc = []
    if pid:
        for sig, grace in ((None, 20), (signal.SIGTERM, 20), (signal.SIGKILL, 20)):
            if sig is not None and pid_alive(pid):
                try: os.kill(pid, sig); esc.append(int(sig))
                except ProcessLookupError: pass
            end = time.time() + grace
            while pid_alive(pid) and time.time() < end: time.sleep(0.5)
            if not pid_alive(pid): break
    end = t0 + timeout + 60
    while pid and os.path.exists(os.path.join(gp.KFD, str(pid))) and time.time() < end: time.sleep(0.5)
    end = time.time() + timeout
    while not port_free() and time.time() < end: time.sleep(1)
    r = {'pid': pid, 'alive': bool(pid) and pid_alive(pid), 'kfd_entry': bool(pid) and os.path.exists(os.path.join(gp.KFD, str(pid))),
         'port_free': port_free(), 'signals': esc, 'wait_s': round(time.time() - t0, 1)}
    r['ok'] = not r['alive'] and not r['kfd_entry'] and r['port_free']
    return r


def linkage(proof, arm):
    a = ARMS[arm]; ok = False; seen = []
    for m in proof['maps'].values():
        hip = [l for l in m['libs'] if 'libggml-hip' in l]; rt = [l for l in m['libs'] if 'libamdhip64' in l]
        seen.append({'hip': hip, 'amdhip': rt})
        if hip and all(sha(h) == a['libggml_hip_sha256'] for h in hip) and rt and all(r.startswith(os.path.realpath(a['hip_prefix'])) for r in rt):
            ok = True
    return ok, seen


def serve_phase(arm, cdir, timeout_at):
    """llama-server launch; a client thread issues the requests while gp.run_sampled samples the server; the server is stopped (own session) when the client is done or STOP appears."""
    import threading
    results = {'parity': [], 'decode': [], 'errors': [], 'affinity': []}
    pid_box = []
    allowed = set(os.sched_getaffinity(0))
    def spawned(pid):
        pid_box.append(pid)
        if os.environ.get('FILLER_PIDFILE'):
            with open(os.environ['FILLER_PIDFILE'], 'a') as f: f.write(str(pid)+'\n')
    def owns_listener():
        if not pid_box: return False
        inode_set = set()
        for fn in ('/proc/net/tcp','/proc/net/tcp6'):
            with open(fn) as f:
                for line in list(f)[1:]:
                    fields = line.split()
                    if int(fields[1].split(':')[1],16) == PORT and fields[3] == '0A': inode_set.add(fields[9])
        fds = '/proc/%d/fd' % pid_box[0]
        for fd in os.listdir(fds):
            try:
                target = os.readlink(fds+'/'+fd)
                if target.startswith('socket:[') and target[8:-1] in inode_set: return True
            except FileNotFoundError: pass
        return False
    def check_affinity():
        if not pid_box: raise RuntimeError('no captured server pid')
        taskdir = '/proc/%d/task' % pid_box[0]
        for tid in os.listdir(taskdir):
            try:
                if not os.sched_getaffinity(int(tid)) <= allowed: os.sched_setaffinity(int(tid), allowed)
            except ProcessLookupError: pass
        escapes = []
        for tid in os.listdir(taskdir):
            try:
                if not os.sched_getaffinity(int(tid)) <= allowed: escapes.append(tid)
            except ProcessLookupError: pass
        results['affinity'].append({'time':time.time(), 'allowed':sorted(allowed), 'escapes':escapes})
        if escapes: raise RuntimeError('server thread affinity escaped: '+repr(escapes))
    def client():
        t_end = timeout_at
        while time.time() < t_end:
            try:
                if http('/health', timeout=5).get('status') == 'ok' and owns_listener(): break
            except Exception: pass
            time.sleep(2)
        else:
            results['errors'].append('health timeout'); return
        try:
            check_affinity()
            for p in ([] if PLUMB else PARITY):
                r = http('/completion', {'prompt': p, 'n_predict': 64, 'temperature': 0, 'top_k': 1, 'seed': 0, 'cache_prompt': False})
                results['parity'].append(r.get('content', ''))
            for p in (DECODE[:1] if PLUMB else DECODE):
                check_affinity()
                t_start, t_end, t = stream_decode(p)
                check_affinity()
                results['decode'].append({'start':t_start, 'end':t_end, 'predicted_per_second': t.get('predicted_per_second'), 'prompt_per_second': t.get('prompt_per_second'),
                                          'predicted_n': t.get('predicted_n'), 'draft_n': t.get('draft_n'), 'draft_n_accepted': t.get('draft_n_accepted')})
        except Exception as e:
            results['errors'].append(repr(e))
        finally:
            open(os.path.join(cdir, 'client.done'), 'w').write(now())
    end = time.time() + 60
    while not port_free() and time.time() < end: time.sleep(1)
    if not port_free(): return {'error': f'port {PORT} busy after 60 s'}
    th = threading.Thread(target=client, daemon=True); th.start()
    # watchdog: the server never exits by itself; stop it (own session only) when the client is done
    done = os.path.join(cdir, 'client.done')
    stop_cond = os.path.join(cdir, 'STOP-SERVER')
    def watcher():
        while not os.path.exists(done) and not os.path.exists(STOPF) and time.time() < timeout_at: time.sleep(1)
        open(stop_cond, 'w').write('client done or STOP')
    threading.Thread(target=watcher, daemon=True).start()
    rc, err, proof = gp.run_sampled(server_argv(arm), os.path.join(cdir, 'server.log'), env=arm_env(arm), timeout_at=timeout_at,
                                    stopfile=stop_cond, on_spawn=spawned)
    if os.path.exists(STOPF): err = 'stop'
    elif err == 'stop': err = None   # our own client-done stop is the normal end of a server launch
    th.join(10)
    return {'rc': rc, 'error': err, 'proof': proof, **results}



def main_specoff():
    os.makedirs(OUT, exist_ok=True)
    if not gate_dependency()[0]:
        print('REFUSED: ROCm window probe is not PASS', flush=True); return 2
    order = [('p1','C'),('p1','B'),('p2','B'),('p2','C')]
    for pair, arm in order:
        if os.path.exists(STOPF): return 75
        if time.time() + 240 >= DEADLINE: return 75
        cdir = os.path.join(OUT, 'cells', ('smoke-' if PLUMB else '') + pair + '-' + arm)
        os.makedirs(cdir, exist_ok=True)
        # Stale client-done and STOP-SERVER files must never terminate this launch.
        for name in ('client.done', 'STOP-SERVER'):
            try: os.unlink(os.path.join(cdir, name))
            except FileNotFoundError: pass
        x = serve_phase(arm, cdir, min(DEADLINE - 30, time.time() + 1200))
        proof = x.get('proof') or {}; own = max(proof.get('kfd_pids_ours', {}).values(), default=0)
        lk, seen = linkage(proof, arm) if proof else (False, [])
        rel = release(proof.get('pid'))
        ds = x.get('decode') or []; vals = [v.get('predicted_per_second') for v in ds]
        def overlap(v):
            for ob in proof.get('observations', []):
                libs = ob['libs']; hip = [f for f in libs if 'libggml-hip' in f]; rt = [f for f in libs if 'libamdhip64' in f]
                if v['start'] <= ob['time'] <= v['end'] and ob['vram'] >= OWN_VRAM_MIN and hip and rt and all(sha(f)==ARMS[arm]['libggml_hip_sha256'] for f in hip) and all(f.startswith(os.path.realpath(ARMS[arm]['hip_prefix'])) for f in rt): return True
            return False
        checks = {'in_request_own_residency_and_linkage': bool(ds) and all(overlap(v) for v in ds), 'requests': len(ds) == (1 if PLUMB else len(DECODE)) and all(isinstance(v,(int,float)) and v > 0 for v in vals),
                  'no_draft': all(not v.get('draft_n') for v in ds), 'no_error': not x.get('error') and not x.get('errors'),
                  'own_vram': own >= OWN_VRAM_MIN, 'no_foreign_kfd': not proof.get('kfd_foreign'),
                  'linkage': lk, 'released': rel['ok']}
        u = {'unit_id': pair+'-'+arm, 'mode': 'smoke' if PLUMB else 'measurement', 'pair': pair, 'arm':arm,
             'decode_tps_median': med(vals) if checks['requests'] else None, 'checks':checks, 'valid':all(checks.values()),
             'decode': ds, 'affinity':x.get('affinity'), 'parity_text': x.get('parity'), 'proof':proof, 'linkage_seen':seen, 'release':rel,
             'server_argv':server_argv(arm), 'ld':ARMS[arm]['ld']}
        if not u['valid']:
            print(json.dumps(u), flush=True); return 3
        append(u)
        if PLUMB: return 0
    atomic(os.path.join(OUT,'COMPLETE.json'), {'order':order,'complete':True})
    return 0

if __name__ == '__main__':
    sys.exit(main_specoff())
