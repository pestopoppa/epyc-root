#!/usr/bin/env python3
"""Smoke gate for the DS41-1017 target-only baseline: each of the two builds is launched ONCE with the exact recipe argv/env/port,
the frozen request is sent twice (determinism), the output is detokenized for a coherence read, the server is stopped and its PID verified dead.
Correctness work (needs no quiet host) but it loads 502 GB --no-mmap per build: run under
  region-lock run --cpu-list 0-95 --role build --tag ds41-1017-smoke -- python3 -I smoke_1017.py --deadline ISO --execute
Writes SMOKE_OK (only if both builds loaded, answered, were deterministic across the two requests, produced 256 tokens, and the PID is dead) and
SMOKE_RESULT.json. Own PIDs only. The argv/env are copied from `dryrun.out` of the approved gate_1017.py (execution digests c70c8066.../4a175f16...).
"""
import argparse, datetime, json, os, signal, subprocess, sys, time, urllib.request
D = '/mnt/raid0/llm/tmp/ds41-1017-baseline-20261021'
GB = '/mnt/raid0/llm/kernels/builds'
MODEL = '/mnt/raid0/llm/models/antirez/deepseek-v4.1-flash-gguf/DeepSeek-V4.1-Flash-1017-MXFP4-experts-00001-of-00009.gguf'
PORT = 18741
BUILDS = [('champion_dd3d9721c', f'{GB}/cpu-20261020-dd3d9721c'), ('candidate_f0c96dc1f', f'{GB}/cpu-20261020-f0c96dc1f')]

def argv(build):
    return ['taskset', '-c', '0-95', 'numactl', '--interleave=all', f'{build}/bin/llama-server', '-m', MODEL, '-np', '1', '-c', '8192', '-t', '48', '-tb', '48',
            '-b', '2048', '-ub', '512', '-ctk', 'f16', '-ctv', 'f16', '--device', 'none', '-ngl', '0', '-fa', 'on', '--host', '127.0.0.1', '--port', str(PORT),
            '--metrics', '--slots', '--no-kv-unified', '--no-mmap', '--no-webui', '--load-threads', '48']

def env(build):
    return {'GGML_IQK': '1', 'LD_LIBRARY_PATH': f'{build}/bin', 'OMP_DYNAMIC': 'false', 'OMP_PLACES': 'cores', 'OMP_PROC_BIND': 'spread', 'OMP_WAIT_POLICY': 'active'}

def http(path, body=None, timeout=600):
    req = urllib.request.Request(f'http://127.0.0.1:{PORT}{path}', data=None if body is None else json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())

def alive(pid):
    try: os.kill(pid, 0); return True
    except ProcessLookupError: return False

def port_busy():
    import socket
    s = socket.socket(); s.settimeout(1)
    try: s.connect(('127.0.0.1', PORT)); return True
    except OSError: return False
    finally: s.close()

def mem_avail_gib():
    return int([l for l in open('/proc/meminfo') if l.startswith('MemAvailable')][0].split()[1]) / 1048576

def run_one(label, build, req, stop):
    rec = {'label': label, 'build': build, 'argv': argv(build)}
    rec['mem_available_gib_before_load'] = round(mem_avail_gib(), 1)
    if mem_avail_gib() < 800:   # main 2026-10-21: DS41 resident ~739 GiB measured; abort cleanly under ~800 GiB available
        rec['ok'] = False; rec['pid_dead'] = True; rec['error'] = f'MemAvailable {mem_avail_gib():.0f} GiB < 800 GiB: not loaded'
        return rec
    logp = f'{D}/smoke-{label}.server.log'
    t0 = time.time(); p = None
    try:
        p = subprocess.Popen(argv(build), env=env(build), stdout=open(logp, 'wb'), stderr=subprocess.STDOUT, start_new_session=True)
        rec['pid'] = p.pid
        while True:
            if time.time() > stop: raise TimeoutError('deadline during load')
            if p.poll() is not None: raise RuntimeError(f'server exited rc={p.returncode} during load')
            try:
                if http('/health', timeout=5).get('status') == 'ok': break
            except Exception: pass
            time.sleep(5)
        rec['load_s'] = round(time.time() - t0, 1)
        outs = []
        for i in range(2):
            t1 = time.time(); r = http('/completion', req); dt = time.time() - t1
            toks = r.get('tokens') or []
            outs.append({'n_tokens': len(toks), 'tokens': toks, 'wall_s': round(dt, 2), 'predicted_per_second': (r.get('timings') or {}).get('predicted_per_second'),
                         'stop_type': r.get('stop_type'), 'content': r.get('content')})
        rec['requests'] = outs
        rec['deterministic'] = outs[0]['tokens'] == outs[1]['tokens']
        rec['n256'] = all(o['n_tokens'] == 256 for o in outs)
        try: rec['detok_first_64'] = http('/detokenize', {'tokens': outs[0]['tokens'][:64]}).get('content')
        except Exception as e: rec['detok_err'] = repr(e)
        rec['ok'] = bool(rec['deterministic'] and rec['n256'])
    except Exception as e:
        rec['ok'] = False; rec['error'] = repr(e)
    finally:
        if p is not None and p.poll() is None:
            p.send_signal(signal.SIGTERM)
            try: p.wait(240)
            except subprocess.TimeoutExpired:
                p.kill(); p.wait(60)
        rec['pid_dead'] = (p is None) or (not alive(p.pid))
        rec['teardown_s'] = round(time.time() - t0, 1)
    for o in rec.get('requests', []): o['content'] = (o['content'] or '')[:400]
    return rec

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--deadline', required=True); ap.add_argument('--execute', action='store_true')
    ap.add_argument('--concurrent-gpu-note', default='none declared'); a = ap.parse_args()
    stop = datetime.datetime.strptime(a.deadline, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc).timestamp()
    m = json.load(open(f'{D}/prompt-manifest.ds41-decode.json')); req = m['prompts'][0]['request']
    print('plan:', [(l, ' '.join(argv(b))[:140]) for l, b in BUILDS], 'port', PORT, 'free', not port_busy())
    if not a.execute: print('dry: nothing launched'); return 0
    if port_busy(): sys.exit(f'port {PORT} busy')
    res = {'started_utc': datetime.datetime.now(datetime.timezone.utc).strftime('%FT%TZ'), 'concurrent_gpu_job': a.concurrent_gpu_note, 'runs': []}
    for label, b in BUILDS:
        res['runs'].append(run_one(label, b, req, stop))
        json.dump(res, open(f'{D}/SMOKE_RESULT.json', 'w'), indent=1)
        if not res['runs'][-1]['ok'] or not res['runs'][-1]['pid_dead']: break
    res['all_ok'] = len(res['runs']) == 2 and all(r['ok'] and r['pid_dead'] for r in res['runs'])
    # the two builds must also agree token-for-token (greedy, same model): informational, a mismatch is recorded not gated
    if len(res['runs']) == 2 and res['all_ok']:
        res['champion_vs_candidate_token_identical'] = res['runs'][0]['requests'][0]['tokens'] == res['runs'][1]['requests'][0]['tokens']
    res['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).strftime('%FT%TZ')
    json.dump(res, open(f'{D}/SMOKE_RESULT.json', 'w'), indent=1)
    if res['all_ok']: open(f'{D}/SMOKE_OK', 'w').write(res['finished_utc'] + '\n')
    print(json.dumps({k: v for k, v in res.items() if k != 'runs'}, indent=1)); return 0 if res['all_ok'] else 1

if __name__ == '__main__': sys.exit(main())
