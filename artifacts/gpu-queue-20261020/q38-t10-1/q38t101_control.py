#!/usr/bin/env python3
"""Q38-T10.1 control arm: is a per-request `speculative.n_max: 0` on a DFlash2 spec server token-identical to a spec-off server,
alone (i) and while a second slot speculates (iii)?  Run ONLY under gpu-quiet exclusive (run_q38t101_control.sh does that).
Own server instances only, non-production port, every PID captured, killed and verified dead.
usage: q38t101_control.py --out DIR --stop-epoch N [--port 18890] [--dry-run]"""
import argparse, glob, hashlib, json, os, re, shlex, signal, subprocess, sys, threading, time, urllib.request
from pathlib import Path

D = Path('/mnt/raid0/llm/tmp/gpu-staged-20261020')
BIN_DIR = Path('/mnt/raid0/llm/kernels/builds/gpu-20261006-4348de400/bin')
BIN = BIN_DIR / 'llama-server'
STUB = os.environ.get('Q38_STUB_BIN')          # CPU dry-run only: a python stub server stands in for llama-server
if STUB: BIN = Path(STUB)
LAUNCH_JSON = Path('/mnt/raid0/llm/epyc-orchestrator/logs/server_launches/8083.json')   # production architect_critic argv (read-only)
ARGV_TXT = Path('/mnt/raid0/llm/tmp/overnight-20261020/argv.8083-gate.txt')            # fallback / cross-check (read-only)
PROMPTS = D / 'q38t101_prompts.json'
PRODUCTION_PORTS = {8000, 8070, 8071, 8072, 8073, 8074, 8080, 8081, 8082, 8083, 8084, 8085, 8086, 8087, 8088, 8089, 8090, 8091, 8092, 8093, 8094, 8095, 9000, 9002}
HOST = '127.0.0.1'
N_PREDICT = 160
VRAM_TOTAL_GIB = 64.0
VRAM_FLOOR = 0 if os.environ.get('Q38_STUB_BIN') else 20 * 1024**3          # model must be resident: a CPU-fallback server would sit far below this
DROP_PAIRS = ('--port', '--slot-save-path', '--cache-ram')   # port is ours; the other two touch production state / host RAM, not numerics
DRAFT_FLAGS_WITH_VAL = ('-md', '-ngld', '--spec-type', '--spec-draft-n-max', '--device-draft')
VRAM_PATH = '/sys/class/drm/card2/device/mem_info_vram_used'
BUSY_PATH = '/sys/class/drm/card2/device/gpu_busy_percent'

def rd(p):
    try: return int(Path(p).read_text().strip())
    except Exception: return -1

def load_prod_args():
    """Production architect_critic argv without launcher prefix / binary / port. Returns (tokens, source, cross_check)."""
    notes = []
    toks = None
    try:
        a = json.loads(LAUNCH_JSON.read_text())['argv']
        i = a.index(next(x for x in a if x.endswith('/llama-server')))
        toks = a[i + 1:]
        src = str(LAUNCH_JSON)
    except Exception as e:
        notes.append(f'launch json unusable: {e!r}')
    txt = []
    for line in ARGV_TXT.read_text().splitlines():
        if line.startswith('#') or not line.strip(): continue
        txt += shlex.split(line)
    if toks is None:
        toks, src = txt, str(ARGV_TXT)
    else:
        sa, sb = set(toks) - {'8083'}, set(txt)
        notes.append('tokens only in launch json: %s ; only in gate txt: %s (expected: none beyond ordering; gate txt has no --port)' % (sorted(sa - sb), sorted(sb - sa)))
    return toks, src, notes

def strip_pairs(toks, names):
    out, i = [], 0
    while i < len(toks):
        if toks[i] in names: i += 2; continue
        out.append(toks[i]); i += 1
    return out

def build_argvs(port):
    toks, src, notes = load_prod_args()
    base = strip_pairs(toks, DROP_PAIRS)
    spec = base + ['--port', str(port), '--metrics', '--slots']
    off = strip_pairs(base, DRAFT_FLAGS_WITH_VAL) + ['--spec-type', 'none', '--port', str(port), '--metrics', '--slots']
    prefix = [] if STUB else ['numactl', '--membind=3', '--', 'taskset', '-c', '184-191']          # same host placement as production :8083
    return prefix + [str(BIN)] + spec, prefix + [str(BIN)] + off, src, notes

def http(port, path, body=None, timeout=900):
    req = urllib.request.Request(f'http://{HOST}:{port}{path}', data=None if body is None else json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def port_in_use(port):
    import socket
    s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try: s.bind((HOST, port)); return False
    except OSError: return True
    finally: s.close()

class Abort(Exception): pass

class Server:
    def __init__(self, label, argv, port, out, stop_epoch):
        self.label, self.argv, self.port, self.out, self.stop = label, argv, port, out, stop_epoch
        self.proc = None; self.samples = []; self._ev = threading.Event(); self._t = None
    def _sample(self):
        while not self._ev.is_set():
            try: kf = sorted(int(x) for x in os.listdir('/sys/class/kfd/kfd/proc') if x.isdigit())
            except Exception: kf = []
            self.samples.append({'t': time.time(), 'vram': rd(VRAM_PATH), 'busy': rd(BUSY_PATH), 'child_in_kfd': (self.proc.pid in kf) if self.proc else None})
            self._ev.wait(1.0)
    def start(self):
        env = dict(os.environ)
        env['LD_LIBRARY_PATH'] = f'{BIN_DIR}:/opt/rocm/lib' if not STUB else env.get('LD_LIBRARY_PATH', '')                      # this tree's own ggml, never the global path
        for k in ('HSA_OVERRIDE_GFX_VERSION', 'GGML_NOHUGEPAGE_PROCESS', 'LLAMA_SPEC_EXACT', 'LLAMA_SPEC_DIAG_ACCEPT', 'GGML_CUDA_LOG_MMVQ_ROUTE'):
            env.pop(k, None)
        (self.out / f'{self.label}.server_command.txt').write_text(' '.join(shlex.quote(a) for a in self.argv) + '\n')
        self.log = (self.out / f'{self.label}.server.log').open('wb')
        self.proc = subprocess.Popen(self.argv, stdout=self.log, stderr=subprocess.STDOUT, env=env)
        self.pid = self.proc.pid
        (self.out / 'pids.txt').open('a').write(f'{self.label} {self.pid}\n')
        self._t = threading.Thread(target=self._sample, daemon=True); self._t.start()
        t0 = time.time()
        while True:
            if time.time() > self.stop: raise Abort('deadline during server load')
            if self.proc.poll() is not None: raise RuntimeError(f'{self.label} server exited rc={self.proc.returncode}')
            if time.time() - t0 > 900: raise RuntimeError(f'{self.label} not ready in 900 s')
            try:
                if http(self.port, '/health', timeout=5).get('status') == 'ok': break
            except Exception: time.sleep(3)
        self.vram_ready = rd(VRAM_PATH)
        if self.vram_ready < VRAM_FLOOR: raise RuntimeError(f'{self.label}: VRAM {self.vram_ready} below residency floor {VRAM_FLOOR}')
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
        return {'label': self.label, 'pid': getattr(self, 'pid', None), 'dead_after': dead, 'samples': len(s),
                'vram_ready_gib': round(getattr(self, 'vram_ready', -1) / 2**30, 2),
                'vram_peak_gib': round(max([x['vram'] for x in s] or [0]) / 2**30, 2),
                'busy_max': max([x['busy'] for x in s] or [0]), 'busy_nonzero_samples': sum(1 for x in s if x['busy'] > 0),
                'child_in_kfd_samples': sum(1 for x in s if x['child_in_kfd'])}

def gen_body(prompt, extra=None, n=N_PREDICT):
    b = {'prompt': prompt, 'n_predict': n, 'temperature': 0.0, 'top_k': 1, 'top_p': 1.0, 'min_p': 0.0, 'typical_p': 1.0,
         'repeat_penalty': 1.0, 'seed': 42, 'stream': False, 'cache_prompt': False, 'return_tokens': True,
         'samplers': ['top_k', 'temperature']}
    if extra: b.update(extra)
    return b

def render(port, prompts):
    out = []
    for p in prompts:
        r = http(port, '/apply-template', {'messages': [{'role': 'user', 'content': p['prompt']}], 'chat_template_kwargs': {'enable_thinking': False}})
        out.append(r['prompt'])
    return out

def one(port, rendered, extra=None, n=N_PREDICT):
    t0 = time.time()
    r = http(port, '/completion', gen_body(rendered, extra, n))
    t1 = time.time()
    tm = r.get('timings') or {}
    return {'tokens': r.get('tokens') or [], 'content': r.get('content'), 'stop_type': r.get('stop_type'), 'truncated': r.get('truncated'),
            'draft_n': tm.get('draft_n'), 'draft_n_accepted': tm.get('draft_n_accepted'), 't0': t0, 't1': t1}

def run_arm(port, label, prompts, rendered, extra, stop, out, concurrent_bg=None):
    """Sequential foreground requests. With concurrent_bg (list of rendered long prompts) a background thread keeps ONE speculating request alive."""
    recs = []
    for i, p in enumerate(prompts):
        if time.time() > stop: raise Abort(f'deadline in arm {label} at prompt {i}')
        bg = {'on': True, 'log': [], 'err': None}
        th = None
        if concurrent_bg:
            def loop(k=i):
                j = 0
                while bg['on']:
                    try:
                        r = one(port, concurrent_bg[(k + j) % len(concurrent_bg)], None, 400)   # default draft: speculates
                        bg['log'].append({'t0': r['t0'], 't1': r['t1'], 'draft_n': r['draft_n'], 'n': len(r['tokens'])})
                    except Exception as e:
                        bg['err'] = repr(e); return
                    j += 1
            th = threading.Thread(target=loop, daemon=True); th.start(); time.sleep(0.6)    # let the speculating slot get going
        try:
            r = one(port, rendered[i], extra)
        finally:
            bg['on'] = False
            if th: th.join(timeout=120)
        rec = {'id': p['id'], 'fmt': p.get('fmt'), **{k: r[k] for k in ('tokens', 'content', 'stop_type', 'truncated', 'draft_n', 'draft_n_accepted')}, 'wall_s': round(r['t1'] - r['t0'], 2),
               'content_sha256': hashlib.sha256((r['content'] or '').encode()).hexdigest()}
        if concurrent_bg:
            ov = [b for b in bg['log'] if b['t0'] < r['t1'] and b['t1'] > r['t0']]
            rec['bg_overlapping_requests'] = len(ov); rec['bg_overlapping_with_drafts'] = sum(1 for b in ov if (b['draft_n'] or 0) > 0)
            rec['bg_error'] = bg['err']
        recs.append(rec)
        with (out / f'{label}.records.jsonl').open('a') as f: f.write(json.dumps(rec) + '\n')
        print(f'  {label} {p["id"]} n={len(rec["tokens"])} stop={rec["stop_type"]} draft_n={rec["draft_n"]} {rec["wall_s"]}s', flush=True)
    return recs

def first_div(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y: return i
    return None if len(a) == len(b) else min(len(a), len(b))

def compare(ref, other):
    rows = []
    for r, o in zip(ref, other):
        d = first_div(r['tokens'], o['tokens'])
        rows.append({'id': r['id'], 'identical': d is None, 'first_divergence': d, 'n_ref': len(r['tokens']), 'n_other': len(o['tokens'])})
    return {'identical_count': sum(1 for x in rows if x['identical']), 'n': len(rows), 'rows': rows}

def parse_ok(fmt, text):
    t = (text or '').strip()
    try:
        if fmt == 'json': j = json.loads(t); return isinstance(j, dict) and all(k in j for k in ('name', 'year', 'tags'))
        if fmt == 'csv': rows = [l for l in t.splitlines() if l.strip()]; return rows[0].replace(' ', '') == 'planet,diameter_km' and len(rows) == 6 and all(l.count(',') == 1 for l in rows)
        if fmt == 'yaml': kv = dict(l.split(':', 1) for l in t.splitlines() if ':' in l); return all(k.strip() in kv for k in ('host', 'port', 'debug'))
        if fmt == 'answer': return re.fullmatch(r'ANSWER:\s*-?\d+', t) is not None
    except Exception: return False
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True); ap.add_argument('--stop-epoch', type=int, required=True)
    ap.add_argument('--port', type=int, default=18890); ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    if a.port in PRODUCTION_PORTS or a.port < 18000: sys.exit(f'refusing production/low port {a.port}')
    spec_argv, off_argv, src, notes = build_argvs(a.port)
    prompts = json.loads(PROMPTS.read_text())
    assert len(prompts) == 20 and sum(1 for p in prompts if p.get('fmt')) == 4
    digest = hashlib.sha256(PROMPTS.read_bytes()).hexdigest()
    cfg = {'argv_source': src, 'cross_check': notes, 'spec_argv': spec_argv, 'off_argv': off_argv, 'prompts_sha256': digest, 'n_predict': N_PREDICT,
           'binary': str(BIN), 'binary_mtime': time.strftime('%FT%TZ', time.gmtime(BIN.stat().st_mtime))}
    (out / 'config_echo.json').write_text(json.dumps(cfg, indent=1))
    print(json.dumps({k: cfg[k] for k in ('argv_source', 'prompts_sha256', 'binary')}), flush=True)
    for need in (BIN, Path('/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf'), Path('/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf'),
                 Path('/mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja')):
        assert need.exists(), f'missing {need}'
    if a.dry_run:
        print('SPEC ARGV:', ' '.join(shlex.quote(x) for x in spec_argv)); print('OFF  ARGV:', ' '.join(shlex.quote(x) for x in off_argv))
        print('cross-check:', notes); print('port free:', not port_in_use(a.port)); return 0
    if port_in_use(a.port): sys.exit(f'port {a.port} already in use')
    stop = a.stop_epoch
    servers, procs_info, arms, result = [], [], {}, {}
    state = {'srv': None}
    def on_term(sig, frm): raise Abort(f'signal {sig}')
    signal.signal(signal.SIGTERM, on_term); signal.signal(signal.SIGINT, on_term)
    status, err = 'COMPLETE', None
    try:
        # ---- server 1: spec OFF (reference) ----
        srv = Server('off', off_argv, a.port, out, stop); state['srv'] = srv; srv.start()
        rendered_off = render(a.port, prompts)
        long_bg = rendered_off[4:8]                                    # 4 plain prompts reused as the speculating neighbour's work
        arms['off_A'] = run_arm(a.port, 'off_A', prompts, rendered_off, None, stop, out)
        arms['off_B'] = run_arm(a.port, 'off_B', prompts, rendered_off, None, stop, out)
        procs_info.append(srv.stop_and_verify()); state['srv'] = None
        # ---- server 2: DFlash2 spec on ----
        srv = Server('spec', spec_argv, a.port, out, stop); state['srv'] = srv; srv.start()
        rendered_spec = render(a.port, prompts)
        arms['iv_spec_default'] = run_arm(a.port, 'iv_spec_default', prompts, rendered_spec, None, stop, out)                 # informative: speculation is live on this server
        arms['i_nmax0'] = run_arm(a.port, 'i_nmax0', prompts, rendered_spec, {'speculative.n_max': 0}, stop, out)
        arms['iii_nmax0_concurrent'] = run_arm(a.port, 'iii_nmax0_concurrent', prompts, rendered_spec, {'speculative.n_max': 0}, stop, out, concurrent_bg=render(a.port, [{'prompt': p['prompt']} for p in prompts[4:8]]))
        procs_info.append(srv.stop_and_verify()); state['srv'] = None
    except Abort as e: status, err = 'INCOMPLETE', str(e)
    except Exception as e: status, err = 'ERROR', repr(e)
    finally:
        if state['srv'] is not None:
            try: procs_info.append(state['srv'].stop_and_verify())
            except Exception as e: procs_info.append({'cleanup_error': repr(e)})
    # ---- judge ----
    s = {'status': status, 'error': err, 'prompts_sha256': digest, 'servers': procs_info, 'arms_done': {k: len(v) for k, v in arms.items()}}
    alive = [p for p in procs_info if p.get('dead_after') is False]
    s['all_server_pids_dead'] = not alive and all('cleanup_error' not in p for p in procs_info)
    full = lambda k: k in arms and len(arms[k]) == len(prompts)
    verdict = 'INCOMPLETE'
    if full('off_A') and full('off_B'):
        aa = compare(arms['off_A'], arms['off_B']); s['aa_off_vs_off'] = {k: aa[k] for k in ('identical_count', 'n')}
        s['aa_rows'] = aa['rows']
        base = arms['off_A']
        s['truncated_baseline_ids'] = [r['id'] for r in base if len(r['tokens']) >= N_PREDICT]
        if aa['identical_count'] != aa['n']: verdict = 'VOID_AA'
        else:
            checks = {}
            for k in ('i_nmax0', 'iii_nmax0_concurrent', 'iv_spec_default'):
                if full(k):
                    c = compare(base, arms[k]); checks[k] = c; s[f'{k}_vs_off'] = {kk: c[kk] for kk in ('identical_count', 'n')}; s[f'{k}_rows'] = c['rows']
            if full('i_nmax0'):
                # draft_n guard: llama-server OMITS timings.draft_n when nothing was drafted (tools/server/server-task.cpp:261 `if (draft_n > 0) { base["draft_n"] = ...}`;
                # upstream asserts it at tools/server/tests/unit/test_speculative.py:104 `"draft_n" not in res_disabled.body["timings"]`). So a missing draft_n means ZERO drafts.
                s['guard_i_all_draft_n_zero'] = all(((r['draft_n'] or 0) == 0) for r in arms['i_nmax0'])
            if full('iv_spec_default'):
                s['guard_spec_live_default_draft_n_total'] = sum((r['draft_n'] or 0) for r in arms['iv_spec_default'])
            if full('iii_nmax0_concurrent'):
                r3 = arms['iii_nmax0_concurrent']
                s['guard_iii_fg_draft_n_zero'] = all(((r['draft_n'] or 0) == 0) for r in r3)   # missing draft_n == 0 drafts (see comment above)
                s['guard_iii_prompts_with_overlapping_speculating_bg'] = sum(1 for r in r3 if r.get('bg_overlapping_with_drafts', 0) > 0)
                s['guard_iii_bg_errors'] = [r['id'] for r in r3 if r.get('bg_error')]
            if full('i_nmax0') and full('iii_nmax0_concurrent') and full('iv_spec_default'):
                g_ok = (s['guard_i_all_draft_n_zero'] and s['guard_iii_fg_draft_n_zero'] and s['guard_spec_live_default_draft_n_total'] > 0
                        and s['guard_iii_prompts_with_overlapping_speculating_bg'] == len(prompts) and not s['guard_iii_bg_errors'])
                ident = checks['i_nmax0']['identical_count'] == len(prompts) and checks['iii_nmax0_concurrent']['identical_count'] == len(prompts)
                verdict = ('VOID_GUARDS' if not g_ok else ('PASS' if ident else 'FAIL'))
                s['control_identity_i_and_iii'] = ident; s['guards_ok'] = g_ok
            fmt_tab = {}
            for k in ('off_A', 'iv_spec_default', 'i_nmax0', 'iii_nmax0_concurrent'):
                if full(k): fmt_tab[k] = {r['id']: parse_ok(r['fmt'], r['content']) for r in arms[k] if r.get('fmt')}
            s['machine_parse_ok'] = fmt_tab
    if not s['all_server_pids_dead']: verdict = 'ERROR_PIDS_NOT_DEAD' if verdict in ('PASS', 'FAIL') else verdict
    s['verdict'] = verdict
    peak = max([p.get('vram_peak_gib', 0) for p in procs_info] or [0])
    s['vram_peak_gib'] = peak; s['vram_total_gib'] = VRAM_TOTAL_GIB
    (out / 'summary.json').write_text(json.dumps(s, indent=1))
    line = {'verdict': verdict, 'status': status, 'aa': s.get('aa_off_vs_off'), 'i_vs_off': s.get('i_nmax0_vs_off'), 'iii_vs_off': s.get('iii_nmax0_concurrent_vs_off'),
            'iv_default_vs_off': s.get('iv_spec_default_vs_off'), 'guards_ok': s.get('guards_ok'), 'vram_peak_gib': peak, 'pids_dead': s['all_server_pids_dead'], 'error': err}
    print('JUDGE', json.dumps(line), flush=True)
    (out / 'judge_line.json').write_text(json.dumps(line))
    return 0 if status != 'ERROR' else 1

if __name__ == '__main__':
    sys.exit(main())
