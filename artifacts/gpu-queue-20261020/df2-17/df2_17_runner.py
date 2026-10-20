#!/usr/bin/env python3
"""DF2-17 runner: horizon (1600) and width replay of the greedy-parity ruling on the champion HIP build.
Run ONLY inside gpu_hold.sh.   usage: df2_17_runner.py <stage1|stage2> [--only ARM ...]
Fresh server process per arm, own-PID control only, residency sampled DURING each arm."""
import argparse, hashlib, json, os, signal, subprocess, sys, time, urllib.request
from pathlib import Path
sys.path.insert(0, '/mnt/raid0/llm/tmp/gpu-queue-20261020/lib')
import gpuq

ROOT = Path('/mnt/raid0/llm/tmp/gpu-queue-20261020/df2-17')
B = Path('/mnt/raid0/llm/kernels/builds/gpu-20261006-4348de400/bin')
TARGET = '/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf'
DRAFT = '/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf'
DF28 = '/workspace/tmp/questions_mtp_ab.json'
MIX = '/mnt/raid0/llm/tmp/inf70/agents/e3-alpha/prompts.json'
PORT, HOST = 18097, '127.0.0.1'
CAP = 1600
VRAM_FLOOR = 8 * 1024**3

# (label, kind, n_max, env)
def arms_for(stage):
    base = [('off_A', 'none', 0, {}), ('off_B', 'none', 0, {}), ('serial_df7', 'dflash', 7, {'LLAMA_SPEC_EXACT': 'serial'})]
    if stage == 'stage1':
        return base + [('mtp_n1', 'mtp', 1, {}), ('mtp_n2', 'mtp', 2, {}), ('mtp_n3', 'mtp', 3, {}),
                       ('dflash_n4', 'dflash', 4, {}), ('mtp_n5', 'mtp', 5, {}), ('dflash_n7', 'dflash', 7, {})]
    return base + [('dflash_n7', 'dflash', 7, {})]

def argv_for(stage, kind, n_max):
    kv = 'f16' if stage == 'stage1' else 'q8_0'
    a = ['taskset', '-c', '184-191', str(B / 'llama-server'), '-m', TARGET, '-np', '1', '-c', '32768', '--no-kv-unified',
         '-t', '8', '-tb', '8', '-b', '2048', '-ub', '2048', '-ctk', kv, '-ctv', kv,
         '--device', 'ROCm0', '-ngl', '99', '-fa', 'on', '--host', HOST, '--port', str(PORT), '--metrics', '--slots']
    if kind == 'none': a += ['--spec-type', 'none']
    elif kind == 'mtp': a += ['--spec-type', 'draft-mtp', '--spec-draft-n-max', str(n_max)]
    elif kind == 'dflash': a += ['-md', DRAFT, '-ngld', '99', '--spec-type', 'draft-dflash', '--spec-draft-n-max', str(n_max)]
    return a

def http(path, body=None, timeout=1800, method=None):
    req = urllib.request.Request(f'http://{HOST}:{PORT}{path}', data=None if body is None else json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'}, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def wait_ready(proc, log, timeout=900):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if proc.poll() is not None: raise RuntimeError(f'server exited rc={proc.returncode}; {log}')
        try:
            if http('/health', timeout=5).get('status') == 'ok': return
        except Exception: time.sleep(3)
    raise RuntimeError('server not ready')

def gen_body(prompt, n, probs=False):
    b = {'prompt': prompt, 'n_predict': n, 'temperature': 0.0, 'top_k': 1, 'top_p': 1.0, 'min_p': 0.0, 'typical_p': 1.0,
         'repeat_penalty': 1.0, 'seed': 42, 'stream': False, 'cache_prompt': False, 'return_tokens': True,
         'samplers': ['top_k', 'temperature']}
    if probs: b.update({'n_probs': 2, 'post_sampling_probs': False})
    return b

def load_prompts(stage, proc_ready_render=None):
    if stage == 'stage1':
        d = json.loads(Path(DF28).read_text())
        return [{'id': x['id'], 'prompt': x['prompt'], 'suite': x.get('suite', 'olympiadbench')} for x in d]
    frozen = ROOT / 'stage2_rendered_prompts.json'
    if frozen.exists(): return json.loads(frozen.read_text())
    raw = json.loads(Path(MIX).read_text())
    out = []
    for x in raw:
        r = http('/apply-template', {'messages': [{'role': 'user', 'content': x['prompt']}], 'chat_template_kwargs': {'enable_thinking': False}})
        out.append({'id': x['id'], 'suite': x['suite'], 'raw_prompt': x['prompt'], 'prompt': r['prompt']})
    frozen.write_text(json.dumps(out, indent=1))
    return out

def run_arm(stage, label, kind, n_max, env_extra, out: Path):
    d = out / label; d.mkdir(parents=True, exist_ok=True)
    done = d / 'arm.json'
    if done.exists(): print('skip (done)', label, flush=True); return json.loads(done.read_text())
    log = d / 'server.stderr'
    argv = argv_for(stage, kind, n_max)
    (d / 'server_command.txt').write_text(' '.join(argv) + '\n')
    env = dict(os.environ)
    env['LD_LIBRARY_PATH'] = f'{B}:/opt/rocm/lib'
    for k in ('HSA_OVERRIDE_GFX_VERSION', 'GGML_NOHUGEPAGE_PROCESS', 'LLAMA_SPEC_EXACT', 'LLAMA_SPEC_DIAG_ACCEPT', 'GGML_CUDA_LOG_MMVQ_ROUTE'):
        env.pop(k, None)
    env.update(env_extra)
    (d / 'env.json').write_text(json.dumps({'LD_LIBRARY_PATH': env['LD_LIBRARY_PATH'], **env_extra}, indent=1))
    holder = {}
    recs, margin_recs = [], []
    smp = gpuq.Sampler(0.5, lambda: holder.get('pid'))
    t_arm = time.time()
    with smp, log.open('wb') as errf:
        proc = subprocess.Popen(argv, stdout=errf, stderr=subprocess.STDOUT, env=env)
        holder['pid'] = proc.pid
        try:
            wait_ready(proc, log)
            vram = gpuq._rd(gpuq.VRAM)
            if vram < VRAM_FLOOR: raise RuntimeError(f'{label}: VRAM {vram} below residency floor')
            prompts = load_prompts(stage)
            for q in prompts:
                t = time.time()
                r = http('/completion', gen_body(q['prompt'], CAP))
                tm = r.get('timings') or {}
                rec = {'id': q['id'], 'suite': q.get('suite'), 'tokens': r.get('tokens') or [], 'stop_type': r.get('stop_type'),
                       'content_sha256': hashlib.sha256((r.get('content') or '').encode()).hexdigest(), 'content': r.get('content'),
                       'draft_n': tm.get('draft_n'), 'draft_n_accepted': tm.get('draft_n_accepted'), 'predicted_n': tm.get('predicted_n'),
                       'predicted_per_second': tm.get('predicted_per_second'), 'wall_s': round(time.time() - t, 1), 'truncated': r.get('truncated')}
                recs.append(rec)
                with (d / 'records.jsonl').open('a') as f: f.write(json.dumps(rec) + '\n')
                print(f'  {label} {q["id"]} n={len(rec["tokens"])} stop={rec["stop_type"]} draft_n={rec["draft_n"]} {rec["wall_s"]}s', flush=True)
            if label == 'off_A':          # baseline margin pass (spec off only): top1-top2 logprob gap at every generated position
                for rec in recs:
                    q = next(p for p in prompts if p['id'] == rec['id'])
                    r = http('/completion', gen_body(q['prompt'], len(rec['tokens']), probs=True))
                    same = r.get('tokens') == rec['tokens']
                    cp = r.get('completion_probabilities') or []
                    mrow = {'id': rec['id'], 'tokens_identical_to_main_pass': same, 'n': len(cp), 'positions': []}
                    for e in cp:
                        top = e.get('top_logprobs') or e.get('top_probs') or []
                        top = sorted(top, key=lambda z: -(z.get('logprob', z.get('prob', 0))))
                        if len(top) >= 2:
                            lp = lambda z: z.get('logprob', z.get('prob'))
                            mrow['positions'].append({'tok': e.get('id'), 'top1': top[0].get('id'), 'top2': top[1].get('id'), 'margin': lp(top[0]) - lp(top[1])})
                        else: mrow['positions'].append({'tok': e.get('id'), 'top1': None, 'top2': None, 'margin': None})
                    margin_recs.append(mrow)
                    print(f'  margin pass {rec["id"]} identical={same} n={len(cp)}', flush=True)
                (d / 'baseline_margins.json').write_text(json.dumps(margin_recs))
        finally:
            pid = proc.pid
            if proc.poll() is None:
                proc.send_signal(signal.SIGTERM)
                try: proc.wait(timeout=90)
                except subprocess.TimeoutExpired:
                    proc.kill(); proc.wait(timeout=60)
    dead = True
    try: os.kill(pid, 0); dead = False
    except ProcessLookupError: pass
    text = log.read_text(errors='replace')
    import re
    arm = {'label': label, 'kind': kind, 'n_max': n_max, 'verify_width': n_max + 1 if n_max else 1, 'env': env_extra, 'argv': argv,
           'server_pid': pid, 'server_dead_after': dead, 'wall_s': round(time.time() - t_arm, 1), 'vram_at_ready': vram,
           'residency': smp.proof, 'kv_unified_lines': re.findall(r'kv_unified\s*=\s*\S+', text)[:2],
           'spec_exact_mode_logged': re.findall(r'speculative exactness mode \(LLAMA_SPEC_EXACT\) = (\w+)', text),
           'n_records': len(recs), 'records_sha256': hashlib.sha256(json.dumps([[r['id'], r['tokens']] for r in recs]).encode()).hexdigest()}
    done.write_text(json.dumps(arm, indent=1))
    return arm

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('stage', choices=['stage1', 'stage2']); ap.add_argument('--only', nargs='*')
    a = ap.parse_args()
    out = ROOT / a.stage
    for label, kind, n, env in arms_for(a.stage):
        if a.only and label not in a.only: continue
        print(f'[{time.strftime("%H:%M:%S")}] arm {label}', flush=True)
        try: arm = run_arm(a.stage, label, kind, n, env, out)
        except Exception as e:
            print('  ARM FAILED', label, repr(e), flush=True)
            (out / label).mkdir(parents=True, exist_ok=True)
            (out / label / 'FAILED.txt').write_text(repr(e))
            if label in ('off_A',): sys.exit(3)
