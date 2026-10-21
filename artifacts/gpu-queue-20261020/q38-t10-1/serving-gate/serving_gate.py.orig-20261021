#!/usr/bin/env python3
"""Q38-T10.1 serving gate: paired spec-on vs spec-off on graded short-answer prompts (>= 59 clean), per-prompt PASS/FAIL,
regressions and gains counted separately with Clopper-Pearson bounds, plus a token-parity record, for the two serving roles:
  GPU  architect_critic  Qwen3.8-27B Q8 : spec off (A/A) vs DFlash2 n-max 7   (production :8083 argv, own port)
  CPU  frontdoor         Qwen3.6-35B-A3B-MTP Q8 : spec off (A/A) vs draft-mtp n-max 4 (registry frontdoor shape, own port)
Extends the staged control driver q38t101_control.py (same server lifecycle, sampling, PID discipline, residency proof).

Own servers only, on non-production ports (>= 18000). The production stack is DOWN and this never starts it.
The outer process takes the claims itself (gpu-quiet exclusive + device flock for the GPU phase; gpu-quiet shared + a bench-role
CPU-region claim for the CPU phase) via region-lock, and runs each phase as a child under that claim.

usage:
  serving_gate.py --deadline 2026-10-21T06:25:00Z            # full run (both phases), claims taken here
  serving_gate.py --dry-run [--deadline ...]                 # validate paths/argv/corpus/ports, start NOTHING
  serving_gate.py --judge-only RUN_DIR                       # re-grade existing records (no servers, no claims)
  serving_gate.py --selfcheck                                # pure-python grader / Clopper-Pearson check, no processes
Stops 5 min before --deadline; a phase is skipped (SKIPPED_DEADLINE) if less than its minimum span remains.
"""
import argparse, ast, datetime, fcntl, hashlib, json, math, os, re, shlex, signal, subprocess, sys, threading, time, urllib.request
from pathlib import Path

STAGE = Path('/mnt/raid0/llm/tmp/q38t101-serving-gate')
CORPUS = STAGE / 'corpus.jsonl'
CORPUS_SHA = STAGE / 'corpus.sha256'
RESULT = STAGE / 'RESULT.serving_gate.json'
RL = Path('/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock')
DEVICE_LOCK = Path('/mnt/raid0/llm/tmp/gpu_device.mi210_0.lock')
GPU_BIN_DIR = Path('/mnt/raid0/llm/kernels/builds/gpu-20261006-4348de400/bin')      # champion HIP build used by the control arm (4348de400)
CPU_BIN_DIR = Path('/mnt/raid0/llm/kernels/production/cpu')                         # production v10 CPU kernel store (read-only use)
LAUNCH_JSON = Path('/mnt/raid0/llm/epyc-orchestrator/logs/server_launches/8083.json')  # production architect_critic argv (read-only)
ARGV_TXT = Path('/mnt/raid0/llm/tmp/overnight-20261020/argv.8083-gate.txt')            # fallback / cross-check (read-only)
GPU_MODEL = Path('/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf')
GPU_DRAFT = Path('/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf')
CPU_MODEL = Path('/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf')
TEMPLATE = Path('/mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja')
CPU_LIST = '0-47,96-143'          # NUMA_HALF_A, frontdoor :8080 shape (stack_topology.yaml)
CPU_NUMA = '--interleave=0,1'
CPU_THREADS = '48'
MTP_N_MAX = '4'                   # registry frontdoor acceleration.draft_max
PRODUCTION_PORTS = {8000, 8070, 8071, 8072, 8073, 8074, 8080, 8081, 8082, 8083, 8084, 8085, 8086, 8087, 8088, 8089, 8090, 8091, 8092, 8093, 8094, 8095, 8180, 9000, 9002}
HOST = '127.0.0.1'
N_PREDICT = 512
MIN_N = 59
THRESHOLD = 0.05
STOP_MARGIN_S = 300
MIN_SPAN = {'gpu': 1800, 'cpu': 3600}      # seconds that must remain before the stop time to start a phase
EST_MIN = {'gpu': 20, 'cpu': 45}           # estimate, minutes (see handoff note)
VRAM_FLOOR = 20 * 1024**3
DROP_PAIRS = ('--port', '--slot-save-path', '--cache-ram')
DRAFT_FLAGS_WITH_VAL = ('-md', '-ngld', '--spec-type', '--spec-draft-n-max', '--device-draft')
VRAM_PATH = '/sys/class/drm/card2/device/mem_info_vram_used'
BUSY_PATH = '/sys/class/drm/card2/device/gpu_busy_percent'

# ------------------------------------------------------------------ graders (frozen with the corpus; deterministic, gold is local)
def tag_answer(text):
    m = re.findall(r'<answer>(.*?)</answer>', text or '', re.S | re.I)
    return m[-1].strip() if m else None

def grade_gsm(text, gold):
    a = tag_answer(text)
    if a is None: return False, 'no_answer_tag'
    a = re.sub(r'[\s$,%]', '', a).rstrip('.')
    try: return abs(float(a) - float(gold)) < 1e-6, 'ok'
    except ValueError: return False, 'unparsable_number'

def mc_letter(text):
    t = (text or '').strip()
    m = re.fullmatch(r'\(?\**([A-J])\**\)?[.):]?', t)
    if m: return m.group(1)
    m = re.findall(r'answer\s*(?:is|:)?\s*\**\(?([A-J])\b', t, re.I)
    if m: return m[-1].upper()
    m = re.match(r'\s*\**\(?([A-J])[.):]\s', t)
    return m.group(1) if m else None

def grade_mc(text, gold):
    l = mc_letter(text)
    return (l == gold.strip().upper()), ('ok' if l else 'no_letter')

def _canon(s):
    s = s.strip()
    try: return repr(ast.literal_eval(s))
    except Exception: return s

def grade_crux(text, gold):
    a = tag_answer(text)
    if a is None: return False, 'no_answer_tag'
    if _canon(a) == _canon(gold): return True, 'ok'
    try:
        g = ast.literal_eval(gold.strip())
        if isinstance(g, str) and a.strip().strip('\'"') == g: return True, 'ok'
    except Exception: pass
    return False, 'ok'

def _norm_qa(s):
    s = re.sub(r'[^\w\s]', ' ', (s or '').lower()); s = re.sub(r'\b(a|an|the)\b', ' ', s)
    return s.split()

def grade_f1(text, gold, thr):
    a = tag_answer(text)
    if a is None: return False, 'no_answer_tag'
    p, g = _norm_qa(a), _norm_qa(gold)
    if not p or not g: return False, 'empty'
    common = 0; gl = list(g)
    for w in p:
        if w in gl: gl.remove(w); common += 1
    if common == 0: return False, 'ok'
    pr, rc = common / len(p), common / len(g)
    return (2 * pr * rc / (pr + rc)) >= thr, 'ok'

def grade_ifeval(text, g):
    t = text or ''; ins = g['instruction']; kw = g.get('kwargs', {})
    if not t.strip(): return False, 'empty'
    if ins == 'change_case:english_lowercase': return t == t.lower(), 'ok'
    if ins == 'change_case:english_capital': return t == t.upper(), 'ok'
    if ins == 'punctuation:no_comma': return ',' not in t, 'ok'
    if ins == 'startend:quotation': s = t.strip(); return len(s) > 1 and s[0] == '"' and s[-1] == '"', 'ok'
    if ins == 'startend:end_checker': return t.strip().strip('"').strip().lower().endswith(kw['end_phrase'].strip().lower()), 'ok'
    if ins == 'keywords:forbidden_words': return not any(re.search(r'\b' + re.escape(w) + r'\b', t, re.I) for w in kw['forbidden_words']), 'ok'
    if ins == 'detectable_format:json_format':
        s = t.strip().removeprefix('```json').removeprefix('```JSON').removeprefix('```').removesuffix('```').strip()
        try: json.loads(s); return True, 'ok'
        except Exception: return False, 'invalid_json'
    return False, 'unsupported_instruction'

def grade(item, text):
    g = item['grader']; ty = g['type']
    if ty == 'numeric_answer_tag': return grade_gsm(text, item['gold'])
    if ty == 'mc_letter': return grade_mc(text, item['gold'])
    if ty == 'crux_answer_tag': return grade_crux(text, item['gold'])
    if ty == 'f1_answer_tag': return grade_f1(text, item['gold'], g['threshold'])
    if ty == 'ifeval': return grade_ifeval(text, g)
    return False, 'unknown_grader'

# ------------------------------------------------------------------ Clopper-Pearson
def _cdf(k, n, p):      # P(X <= k), X ~ Bin(n, p)
    return sum(math.comb(n, i) * p**i * (1 - p)**(n - i) for i in range(0, k + 1))

def _bisect(pred_true_below):
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if pred_true_below(mid): lo = mid
        else: hi = mid
    return (lo + hi) / 2

def cp_upper(k, n, alpha):
    """Exact upper limit: largest p with P(X<=k | p) >= alpha (alpha=0.05 one-sided 95%; 0.025 per side for the two-sided 95% interval)."""
    if n == 0 or k >= n: return 1.0
    return _bisect(lambda p: _cdf(k, n, p) > alpha)

def cp_lower(k, n, alpha):
    if n == 0 or k <= 0: return 0.0
    return _bisect(lambda p: (1 - _cdf(k - 1, n, p)) < alpha)

def cp_block(k, n):
    return {'k': k, 'n': n, 'rate': (k / n if n else None), 'two_sided_95': [cp_lower(k, n, 0.025), cp_upper(k, n, 0.025)],
            'one_sided_95_upper': cp_upper(k, n, 0.05)}

# ------------------------------------------------------------------ argv
def strip_pairs(toks, names):
    out, i = [], 0
    while i < len(toks):
        if toks[i] in names: i += 2; continue
        out.append(toks[i]); i += 1
    return out

def load_gpu_prod_args():
    notes, toks, src = [], None, None
    try:
        a = json.loads(LAUNCH_JSON.read_text())['argv']
        i = a.index(next(x for x in a if x.endswith('/llama-server')))
        toks, src = a[i + 1:], str(LAUNCH_JSON)
    except Exception as e:
        notes.append(f'launch json unusable: {e!r}')
    txt = []
    for line in ARGV_TXT.read_text().splitlines():
        if line.startswith('#') or not line.strip(): continue
        txt += shlex.split(line)
    if toks is None: toks, src = txt, str(ARGV_TXT)
    else:
        sa, sb = set(toks) - {'8083'}, set(txt)
        notes.append('tokens only in launch json: %s ; only in gate txt: %s' % (sorted(sa - sb), sorted(sb - sa)))
    return toks, src, notes

def gpu_argvs(port):
    toks, src, notes = load_gpu_prod_args()
    base = strip_pairs(toks, DROP_PAIRS)
    spec = base + ['--port', str(port), '--metrics', '--slots']
    off = strip_pairs(base, DRAFT_FLAGS_WITH_VAL) + ['--spec-type', 'none', '--port', str(port), '--metrics', '--slots']
    prefix = ['numactl', '--membind=3', '--', 'taskset', '-c', '184-191']      # same host placement as production :8083
    b = str(GPU_BIN_DIR / 'llama-server')
    return prefix + [b] + spec, prefix + [b] + off, src, notes

def cpu_argvs(port):
    """Frontdoor shape per registry server_mode.frontdoor + stack_topology NUMA_HALF_A: Qwen3.6-35B-A3B-MTP Q8 self-draft draft-mtp n-max 4,
    one slot, q8_0 KV, no-mmap, terse chat template, half-node placement. No launch record exists for the CPU frontdoor (production is DOWN),
    so this is reconstructed from the registry; context is trimmed (numerics are independent of -c)."""
    common = ['-m', str(CPU_MODEL), '--host', HOST, '--port', str(port), '-np', '1', '-c', '32768', '-t', CPU_THREADS, '--flash-attn', 'on', '--jinja',
              '-ctk', 'q8_0', '-ctv', 'q8_0', '--no-mmap', '--chat-template-file', str(TEMPLATE), '--metrics', '--slots']
    prefix = ['numactl', CPU_NUMA, '--', 'taskset', '-c', CPU_LIST]
    b = str(CPU_BIN_DIR / 'llama-server')
    return (prefix + [b] + common + ['--spec-type', 'draft-mtp', '--spec-draft-n-max', MTP_N_MAX],
            prefix + [b] + common + ['--spec-type', 'none'])

# ------------------------------------------------------------------ server lifecycle (from q38t101_control.py)
def rd(p):
    try: return int(Path(p).read_text().strip())
    except Exception: return -1

def http(port, path, body=None, timeout=900):
    req = urllib.request.Request(f'http://{HOST}:{port}{path}', data=None if body is None else json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read())

def port_in_use(port):
    import socket
    s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try: s.bind((HOST, port)); return False
    except OSError: return True
    finally: s.close()

class Abort(Exception): pass

class Server:
    def __init__(self, label, argv, port, out, stop_epoch, bin_dir, expect_gpu):
        self.label, self.argv, self.port, self.out, self.stop, self.bin_dir, self.expect_gpu = label, argv, port, out, stop_epoch, bin_dir, expect_gpu
        self.proc = None; self.samples = []; self._ev = threading.Event(); self._t = None; self.maps = []
    def _sample(self):
        while not self._ev.is_set():
            try: kf = sorted(int(x) for x in os.listdir('/sys/class/kfd/kfd/proc') if x.isdigit())
            except Exception: kf = []
            self.samples.append({'t': time.time(), 'vram': rd(VRAM_PATH), 'busy': rd(BUSY_PATH), 'child_in_kfd': (self.proc.pid in kf) if self.proc else None})
            self._ev.wait(1.0)
    def start(self):
        env = dict(os.environ)
        env['LD_LIBRARY_PATH'] = f'{self.bin_dir}:/opt/rocm/lib' if self.expect_gpu else str(self.bin_dir)      # this tree's own ggml, never the global path
        for k in ('HSA_OVERRIDE_GFX_VERSION', 'GGML_NOHUGEPAGE_PROCESS', 'LLAMA_SPEC_EXACT', 'LLAMA_SPEC_DIAG_ACCEPT', 'GGML_CUDA_LOG_MMVQ_ROUTE'): env.pop(k, None)
        if not self.expect_gpu: env['HIP_VISIBLE_DEVICES'] = '-1'; env['ROCR_VISIBLE_DEVICES'] = ''     # CPU role must never touch the MI210
        (self.out / f'{self.label}.server_command.txt').write_text(' '.join(shlex.quote(a) for a in self.argv) + '\n')
        self.log = (self.out / f'{self.label}.server.log').open('wb')
        self.proc = subprocess.Popen(self.argv, stdout=self.log, stderr=subprocess.STDOUT, env=env)
        self.pid = self.proc.pid
        with (self.out / 'pids.txt').open('a') as f: f.write(f'{self.label} {self.pid}\n')
        self._t = threading.Thread(target=self._sample, daemon=True); self._t.start()
        t0 = time.time()
        while True:
            if time.time() > self.stop: raise Abort('deadline during server load')
            if self.proc.poll() is not None: raise RuntimeError(f'{self.label} server exited rc={self.proc.returncode}')
            if time.time() - t0 > 1200: raise RuntimeError(f'{self.label} not ready in 1200 s')
            try:
                if http(self.port, '/health', timeout=5).get('status') == 'ok': break
            except Exception: time.sleep(3)
        self.vram_ready = rd(VRAM_PATH)
        try: self.maps = sorted({l.split()[-1] for l in Path(f'/proc/{self.pid}/maps').read_text().splitlines() if 'libggml' in l or 'libllama' in l})
        except Exception as e: self.maps = [f'maps unreadable: {e!r}']
        bad = [m for m in self.maps if m.startswith('/') and not os.path.realpath(m).startswith(os.path.realpath(str(self.bin_dir)))]
        if bad: raise RuntimeError(f'{self.label}: ggml/llama libs from outside {self.bin_dir}: {bad}')
        if self.expect_gpu:
            if self.vram_ready < VRAM_FLOOR: raise RuntimeError(f'{self.label}: VRAM {self.vram_ready} below residency floor {VRAM_FLOOR}')
            if not any('libggml-hip' in m for m in self.maps): raise RuntimeError(f'{self.label}: libggml-hip not mapped; not a HIP run: {self.maps}')
    def stop_and_verify(self):
        dead = True
        if self.proc is not None:
            if self.proc.poll() is None:
                self.proc.send_signal(signal.SIGTERM)
                try: self.proc.wait(timeout=90)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    try: self.proc.wait(timeout=60)
                    except subprocess.TimeoutExpired: pass
            try: os.kill(self.pid, 0); dead = False
            except ProcessLookupError: pass
            except Exception: dead = False
            if dead and self.proc.poll() is None: dead = False
        self._ev.set()
        if self._t: self._t.join(timeout=5)
        try: self.log.close()
        except Exception: pass
        s = self.samples
        return {'label': self.label, 'pid': getattr(self, 'pid', None), 'dead_after': dead, 'expect_gpu': self.expect_gpu, 'samples': len(s), 'libs': self.maps,
                'vram_ready_gib': round(getattr(self, 'vram_ready', -1) / 2**30, 2), 'vram_peak_gib': round(max([x['vram'] for x in s] or [0]) / 2**30, 2),
                'busy_max': max([x['busy'] for x in s] or [0]), 'busy_nonzero_samples': sum(1 for x in s if x['busy'] > 0),
                'child_in_kfd_samples': sum(1 for x in s if x['child_in_kfd'])}

def gen_body(prompt, n=N_PREDICT):
    return {'prompt': prompt, 'n_predict': n, 'temperature': 0.0, 'top_k': 1, 'top_p': 1.0, 'min_p': 0.0, 'typical_p': 1.0, 'repeat_penalty': 1.0, 'seed': 42,
            'stream': False, 'cache_prompt': False, 'return_tokens': True, 'samplers': ['top_k', 'temperature']}

def render(port, items):
    return [http(port, '/apply-template', {'messages': [{'role': 'user', 'content': p['prompt']}], 'chat_template_kwargs': {'enable_thinking': False}})['prompt'] for p in items]

def run_arm(port, label, items, rendered, stop, out):
    recs = []
    for i, p in enumerate(items):
        if time.time() > stop: raise Abort(f'deadline in arm {label} at prompt {i}')
        t0 = time.time(); r = http(port, '/completion', gen_body(rendered[i])); t1 = time.time()
        tm = r.get('timings') or {}
        toks = r.get('tokens') or []
        rec = {'id': p['id'], 'tokens': toks, 'content': r.get('content'), 'stop_type': r.get('stop_type'), 'truncated_flag': r.get('truncated'),
               'truncated': (r.get('stop_type') == 'limit') or len(toks) >= N_PREDICT, 'draft_n': tm.get('draft_n'), 'draft_n_accepted': tm.get('draft_n_accepted'),
               'wall_s': round(t1 - t0, 2), 'content_sha256': hashlib.sha256((r.get('content') or '').encode()).hexdigest()}
        recs.append(rec)
        with (out / f'{label}.records.jsonl').open('a') as f: f.write(json.dumps(rec) + '\n')
        print(f'  {label} {p["id"]} n={len(toks)} stop={rec["stop_type"]} draft_n={rec["draft_n"]} {rec["wall_s"]}s', flush=True)
    return recs

def load_corpus():
    data = CORPUS.read_bytes()
    want = CORPUS_SHA.read_text().split()[0]
    got = hashlib.sha256(data).hexdigest()
    if got != want: sys.exit(f'corpus hash mismatch: {got} != frozen {want}')
    return [json.loads(l) for l in data.decode().splitlines()], got

# ------------------------------------------------------------------ inner phase (runs under the claim)
def inner_phase(phase, out, stop, port):
    items, digest = load_corpus()
    out.mkdir(parents=True, exist_ok=True)
    if port in PRODUCTION_PORTS or port < 18000: sys.exit(f'refusing production/low port {port}')
    if port_in_use(port): sys.exit(f'port {port} already in use')
    if phase == 'gpu':
        spec_argv, off_argv, src, notes = gpu_argvs(port); bin_dir, gpu, tag = GPU_BIN_DIR, True, 'gpu'; spec_label = 'gpu_dflash2'
    else:
        spec_argv, off_argv = cpu_argvs(port); src, notes = 'registry server_mode.frontdoor', []; bin_dir, gpu, tag = CPU_BIN_DIR, False, 'cpu'; spec_label = 'cpu_mtp'
    (out / f'config_echo.{phase}.json').write_text(json.dumps({'corpus_sha256': digest, 'n_predict': N_PREDICT, 'spec_argv': spec_argv, 'off_argv': off_argv, 'argv_source': src,
                                                               'cross_check': notes, 'bin_dir': str(bin_dir), 'stop_epoch': stop}, indent=1))
    infos, state, status, err = [], {'srv': None}, 'COMPLETE', None
    def on_term(sig, frm): raise Abort(f'signal {sig}')
    signal.signal(signal.SIGTERM, on_term); signal.signal(signal.SIGINT, on_term)
    try:
        srv = Server(f'{tag}_off', off_argv, port, out, stop, bin_dir, gpu); state['srv'] = srv; srv.start()
        rend = render(port, items)
        run_arm(port, f'{tag}_off_A', items, rend, stop, out)
        run_arm(port, f'{tag}_off_B', items, rend, stop, out)
        infos.append(srv.stop_and_verify()); state['srv'] = None
        srv = Server(spec_label, spec_argv, port, out, stop, bin_dir, gpu); state['srv'] = srv; srv.start()
        rend = render(port, items)
        run_arm(port, spec_label, items, rend, stop, out)
        infos.append(srv.stop_and_verify()); state['srv'] = None
    except Abort as e: status, err = 'INCOMPLETE', str(e)
    except Exception as e: status, err = 'ERROR', repr(e)
    finally:
        if state['srv'] is not None:
            try: infos.append(state['srv'].stop_and_verify())
            except Exception as e: infos.append({'cleanup_error': repr(e)})
    (out / f'phase.{phase}.json').write_text(json.dumps({'phase': phase, 'status': status, 'error': err, 'servers': infos}, indent=1))
    print('PHASE', phase, status, err, flush=True)
    return 0 if status in ('COMPLETE', 'INCOMPLETE') else 1

# ------------------------------------------------------------------ judge
def read_recs(out, label):
    p = out / f'{label}.records.jsonl'
    return [json.loads(l) for l in p.open()] if p.exists() else []

def first_div(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y: return i
    return None if len(a) == len(b) else min(len(a), len(b))

def judge_role(out, items, role, tag, spec_label, phase_info):
    n = len(items); by = {it['id']: it for it in items}
    A, B, S = read_recs(out, f'{tag}_off_A'), read_recs(out, f'{tag}_off_B'), read_recs(out, spec_label)
    r = {'role': role, 'arms': {f'{tag}_off_A': len(A), f'{tag}_off_B': len(B), spec_label: len(S)}, 'n_corpus': n}
    if len(A) < n or len(B) < n or len(S) < n:
        r['verdict'] = 'INCOMPLETE'; return r
    aa_id = sum(1 for a, b in zip(A, B) if first_div(a['tokens'], b['tokens']) is None)
    r['aa_identical'] = f'{aa_id}/{n}'
    srv = {s.get('label'): s for s in phase_info.get('servers', [])}
    g = {'all_pids_dead': len(phase_info.get('servers', [])) == 2 and all(s.get('dead_after') for s in phase_info.get('servers', []))}
    if tag == 'gpu':
        g['hip_resident'] = all(s.get('child_in_kfd_samples', 0) > 0 and s.get('busy_nonzero_samples', 0) > 0 and s.get('vram_peak_gib', 0) >= 20 for s in srv.values())
    else:
        g['cpu_only'] = all(s.get('child_in_kfd_samples', 0) == 0 for s in srv.values())
    drafted = sum((x['draft_n'] or 0) for x in S)       # llama-server omits timings.draft_n when nothing was drafted: missing == 0
    off_drafted = sum((x['draft_n'] or 0) for x in A + B)
    g.update({'spec_arm_drafted_tokens': drafted, 'spec_arm_live': drafted > 0, 'off_arms_drafted_tokens': off_drafted, 'off_arms_drafted_zero': off_drafted == 0})
    r['guards'] = g
    guards_ok = g['all_pids_dead'] and g['spec_arm_live'] and g['off_arms_drafted_zero'] and g.get('hip_resident', True) and g.get('cpu_only', True)
    rows, reg, gain, excl = [], 0, 0, []
    bpass = clean = ident = 0
    for a, b, s in zip(A, B, S):
        it = by[a['id']]
        pa, ra = grade(it, a['content']); ps, rs = grade(it, s['content'])
        trunc = a['truncated'] or b['truncated'] or s['truncated']
        fd = first_div(a['tokens'], s['tokens'])
        row = {'id': a['id'], 'kind': it['kind'], 'gold': it['gold'][:60], 'base_pass': pa, 'base_reason': ra, 'spec_pass': ps, 'spec_reason': rs, 'truncated_any': trunc,
               'n_tok_base': len(a['tokens']), 'n_tok_spec': len(s['tokens']), 'first_divergence': fd, 'token_identical': fd is None}
        if trunc: excl.append(a['id']); row['outcome'] = 'EXCLUDED_TRUNCATED'
        else:
            clean += 1; ident += (fd is None); bpass += pa
            if pa and not ps: reg += 1; row['outcome'] = 'REGRESSION'
            elif ps and not pa: gain += 1; row['outcome'] = 'GAIN'
            else: row['outcome'] = 'SAME_PASS' if pa else 'SAME_FAIL'
        rows.append(row)
    r.update({'rows': rows, 'n_clean': clean, 'excluded_truncated': excl, 'baseline_pass': bpass, 'token_identical_clean': f'{ident}/{clean}',
              'regressions': cp_block(reg, clean), 'gains': cp_block(gain, clean - bpass),
              'regression_given_baseline_pass': cp_block(reg, bpass),
              'denominator_note': 'regression rate = k / n_clean (filed spec); gains rate = k / baseline-FAIL clean prompts; regression_given_baseline_pass is informational'})
    r['regression_upper_95_one_sided'] = r['regressions']['one_sided_95_upper']
    if aa_id != n: r['verdict'] = 'VOID_AA'
    elif not guards_ok: r['verdict'] = 'VOID_GUARDS'
    elif clean < MIN_N: r['verdict'] = 'INSUFFICIENT_N'
    else: r['verdict'] = 'PASS' if r['regression_upper_95_one_sided'] < THRESHOLD else 'FAIL'
    return r

def judge(out, status_by_phase):
    items, digest = load_corpus()
    res = {}
    for phase, role, spec_label in (('gpu', 'architect_critic (27B DFlash2 n-max 7)', 'gpu_dflash2'), ('cpu', 'frontdoor (35B-A3B MTP n-max %s)' % MTP_N_MAX, 'cpu_mtp')):
        pj = out / f'phase.{phase}.json'
        info = json.loads(pj.read_text()) if pj.exists() else {'servers': []}
        res[phase] = judge_role(out, items, role, phase, spec_label, info)
        res[phase]['phase_status'] = status_by_phase.get(phase, info.get('status'))
    vs = [res[p]['verdict'] for p in res]
    overall = 'PASS' if all(v == 'PASS' for v in vs) else ('FAIL' if 'FAIL' in vs else 'INCOMPLETE_OR_VOID')
    summary = {'corpus_sha256': digest, 'n_predict': N_PREDICT, 'threshold': THRESHOLD, 'min_n': MIN_N, 'roles': res, 'second_verdict_distributional_parity': overall}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1))
    tsv = ['phase\tid\tkind\tbase_pass\tspec_pass\toutcome\tfirst_divergence\tn_tok_base\tn_tok_spec']
    for ph, rr in res.items():
        for row in rr.get('rows', []):
            tsv.append('\t'.join(str(x) for x in (ph, row['id'], row['kind'], row['base_pass'], row['spec_pass'], row['outcome'], row['first_divergence'], row['n_tok_base'], row['n_tok_spec'])))
    (out / 'per_prompt.tsv').write_text('\n'.join(tsv) + '\n')
    line = {}
    for ph, rr in res.items():
        line[ph] = {k: rr.get(k) for k in ('verdict', 'aa_identical', 'n_clean', 'baseline_pass', 'token_identical_clean', 'regression_upper_95_one_sided')}
        line[ph].update({'regressions': (rr.get('regressions') or {}).get('k'), 'gains': (rr.get('gains') or {}).get('k'), 'excluded': len(rr.get('excluded_truncated', []))})
    line['parity'] = overall
    (out / 'judge_line.json').write_text(json.dumps(line))
    print('JUDGE', json.dumps(line), flush=True)
    return summary, line

# ------------------------------------------------------------------ outer: claims + phases
def write_result(rc, verdict, note, run):
    tmp = str(RESULT) + '.tmp'
    Path(tmp).write_text(json.dumps({'job': 'q38t101_serving_gate', 'ts': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'rc': rc,
                                      'verdict': verdict, 'note': note, 'run_dir': str(run)}) + '\n')
    os.replace(tmp, RESULT)

def claim_cmd(phase, span, inner_args):
    me = [sys.executable, '-I', str(Path(__file__).resolve())] + inner_args
    if phase == 'gpu':
        rl = [str(RL), 'run', '--gpu-quiet', 'exclusive', '--role', 'bench', '--tag', 'q38t101-gate-gpu', '--timeout-s', '900', '--']
    else:
        rl = [str(RL), 'run', '--gpu-quiet', 'shared', '--cpu-list', CPU_LIST, '--role', 'bench', '--tag', 'q38t101-gate-cpu', '--timeout-s', '900', '--']
    return ['timeout', '--signal=TERM', '--kill-after=120', str(span)] + rl + me

def validate():
    return [f'missing {p}' for p in (GPU_BIN_DIR / 'llama-server', CPU_BIN_DIR / 'llama-server', GPU_MODEL, GPU_DRAFT, CPU_MODEL, TEMPLATE, RL, CORPUS, CORPUS_SHA, LAUNCH_JSON, ARGV_TXT)
            if not Path(p).exists()]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--deadline'); ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--judge-only'); ap.add_argument('--selfcheck', action='store_true')
    ap.add_argument('--phases', default='gpu,cpu'); ap.add_argument('--gpu-port', type=int, default=18891); ap.add_argument('--cpu-port', type=int, default=18892)
    ap.add_argument('--out'); ap.add_argument('--phase-inner'); ap.add_argument('--stop-epoch', type=int)
    a = ap.parse_args()
    if a.selfcheck: return selfcheck()
    if a.judge_only:
        judge(Path(a.judge_only), {}); return 0
    if a.phase_inner:
        return inner_phase(a.phase_inner, Path(a.out), a.stop_epoch, a.gpu_port if a.phase_inner == 'gpu' else a.cpu_port)
    phases = [p for p in a.phases.split(',') if p]
    for p, port in (('gpu', a.gpu_port), ('cpu', a.cpu_port)):
        if p in phases and (port in PRODUCTION_PORTS or port < 18000): sys.exit(f'refusing production/low port {port}')
    items, digest = load_corpus()
    probs = validate()
    now = int(time.time())
    if a.deadline:
        stop = int(datetime.datetime.strptime(a.deadline, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc).timestamp()) - STOP_MARGIN_S
    elif a.dry_run: stop = now + 6 * 3600
    else: sys.exit('--deadline required (UTC, e.g. 2026-10-21T06:25:00Z)')
    run = STAGE / 'runs' / ('sg-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()))
    gs, go, gsrc, gnotes = gpu_argvs(a.gpu_port); cs, co = cpu_argvs(a.cpu_port)
    inner = lambda ph: ['--phase-inner', ph, '--out', str(run), '--stop-epoch', str(stop), '--gpu-port', str(a.gpu_port), '--cpu-port', str(a.cpu_port)]
    if a.dry_run:
        print(json.dumps({'corpus_sha256': digest, 'n_prompts': len(items), 'kinds': {k: sum(1 for i in items if i['kind'] == k) for k in sorted({i['kind'] for i in items})},
                          'n_predict': N_PREDICT, 'stop_utc': time.strftime('%FT%TZ', time.gmtime(stop)), 'span_s': stop - now, 'problems': probs}, indent=1))
        for name, v in (('GPU spec', gs), ('GPU off', go), ('CPU spec', cs), ('CPU off', co)): print(f'{name}:', ' '.join(shlex.quote(x) for x in v))
        print('gpu argv source:', gsrc, '|', gnotes)
        print('ports free: gpu', not port_in_use(a.gpu_port), 'cpu', not port_in_use(a.cpu_port))
        for ph in ('gpu', 'cpu'): print(f'CLAIM {ph}:', ' '.join(shlex.quote(x) for x in claim_cmd(ph, max(stop - now, 0), inner(ph))))
        print('device flock (gpu phase):', DEVICE_LOCK, '| min span s:', MIN_SPAN, '| est min:', EST_MIN)
        print('graders cover every item:', all(i['grader']['type'] in ('numeric_answer_tag', 'mc_letter', 'crux_answer_tag', 'f1_answer_tag', 'ifeval') for i in items))
        return 1 if probs else 0
    if probs: sys.exit('; '.join(probs))
    run.mkdir(parents=True, exist_ok=True)
    status = {}
    for ph in phases:
        span = stop - int(time.time())
        if span < MIN_SPAN[ph]:
            status[ph] = 'SKIPPED_DEADLINE'; print(f'{ph}: only {span}s before stop, need {MIN_SPAN[ph]}s'); continue
        lockf = None
        if ph == 'gpu':
            lockf = DEVICE_LOCK.open('a'); t0 = time.time()
            while True:
                try: fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB); break
                except OSError:
                    if time.time() - t0 > 300: status[ph] = 'DEVICE_CLAIM_BUSY'; lockf.close(); lockf = None; break
                    time.sleep(5)
            if lockf is None: continue
        span = stop - int(time.time())
        cmd = claim_cmd(ph, span, inner(ph))
        (run / f'claim.{ph}.cmd.txt').write_text(' '.join(shlex.quote(x) for x in cmd) + '\n')
        with (run / f'driver.{ph}.log').open('wb') as lg:
            rc = subprocess.call(cmd, stdout=lg, stderr=subprocess.STDOUT)
        status[ph] = 'CLAIM_UNAVAILABLE' if rc == 75 else (f'RAN_rc{rc}' if (run / f'phase.{ph}.json').exists() else f'NO_PHASE_RESULT_rc{rc}')
        if lockf: fcntl.flock(lockf, fcntl.LOCK_UN); lockf.close()
    alive = []
    try:
        for l in (run / 'pids.txt').read_text().splitlines():
            pid = int(l.split()[1])
            try: os.kill(pid, 0); alive.append(pid)
            except ProcessLookupError: pass
    except FileNotFoundError: pass
    status['alive_pids'] = alive
    summary, line = judge(run, status)
    verdict = 'ERROR_PIDS_NOT_DEAD' if alive else summary['second_verdict_distributional_parity']
    write_result(0, verdict, json.dumps({'phases': status, **line}), run)
    return 0

def selfcheck():
    assert grade_gsm('Work... <answer>$1,250.00</answer>', '1250')[0] and not grade_gsm('no tag', '3')[0]
    assert grade_mc('B', 'B')[0] and grade_mc('The answer is (C).', 'C')[0] and not grade_mc('ramble', 'A')[0]
    assert grade_crux('<answer>[1, 2]</answer>', '[1, 2]')[0] and grade_crux("<answer>'abc'</answer>", "'abc'")[0] and grade_crux('<answer>abc</answer>', "'abc'")[0]
    assert grade_f1('<answer>Schaefer Award</answer>', 'Hugo H. Schaefer Award', 0.8)[0] is False and grade_f1('<answer>Hugo H. Schaefer Award</answer>', 'Hugo H. Schaefer Award', 0.8)[0]
    assert grade_ifeval('hello', {'instruction': 'change_case:english_lowercase'})[0] and not grade_ifeval('Hello', {'instruction': 'change_case:english_lowercase'})[0]
    assert grade_ifeval('```json\n{"a":1}\n```', {'instruction': 'detectable_format:json_format'})[0]
    u = cp_upper(0, 59, 0.05); assert abs(u - (1 - 0.05 ** (1 / 59))) < 1e-9 and u < 0.05, u      # filed spec: 0.95^59 < 0.05
    assert cp_upper(1, 59, 0.05) > 0.05 and cp_lower(0, 59, 0.025) == 0.0
    print('selfcheck ok; k=0,n=59 one-sided upper =', round(u, 5), '; k=1,n=59 =', round(cp_upper(1, 59, 0.05), 5), '; k=1,n=80 =', round(cp_upper(1, 80, 0.05), 5))
    return 0

if __name__ == '__main__':
    sys.exit(main())
