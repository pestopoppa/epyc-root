"""Post-hoc diagnostic (not predeclared): rank of each spec arm's first-divergent token inside the baseline's top-8 at that position, for ALL stage-1 first divergences."""
import sys, json, os, subprocess, signal
sys.path.insert(0, '/mnt/raid0/llm/tmp/gpu-queue-20261020/df2-17'); sys.path.insert(0, '/mnt/raid0/llm/tmp/gpu-queue-20261020/lib')
import df2_17_runner as R
from pathlib import Path
D = R.ROOT / 'stage1'
def L(a): return {r['id']: r for r in map(json.loads, (D / a / 'records.jsonl').read_text().splitlines())}
base = L('off_A'); arms = [p.name for p in D.iterdir() if (p / 'arm.json').exists() and p.name not in ('off_A', 'off_B', 'serial_df7')]
cases = {}
for a in arms:
    A = L(a)
    for pid, b in base.items():
        fd = next((i for i, (x, y) in enumerate(zip(b['tokens'], A[pid]['tokens'])) if x != y), None)
        if fd is not None: cases.setdefault(pid, {})[a] = (fd, A[pid]['tokens'][fd])
env = dict(os.environ); env['LD_LIBRARY_PATH'] = f'{R.B}:/opt/rocm/lib'
for k in ('HSA_OVERRIDE_GFX_VERSION', 'LLAMA_SPEC_EXACT'): env.pop(k, None)
log = open(str(R.ROOT / 'diag_rank_server.log'), 'wb')
p = subprocess.Popen(R.argv_for('stage1', 'none', 0), stdout=log, stderr=subprocess.STDOUT, env=env)
out = []
try:
    R.wait_ready(p, log)
    prompts = {q['id']: q for q in R.load_prompts('stage1')}
    for pid, arms_fd in cases.items():
        n = max(fd for fd, _ in arms_fd.values()) + 1
        b = R.gen_body(prompts[pid]['prompt'], n, probs=True); b['n_probs'] = 8
        r = R.http('/completion', b)
        same = r['tokens'] == base[pid]['tokens'][:n]
        cp = r['completion_probabilities']
        for a, (fd, tok) in arms_fd.items():
            tl = cp[fd]['top_logprobs']
            ids = [t['id'] for t in tl]
            out.append({'id': pid, 'arm': a, 'first_diff': fd, 'baseline_tokens_reproduced': same, 'arm_token': tok, 'arm_token_rank_in_baseline_top8': (ids.index(tok) + 1) if tok in ids else None,
                        'baseline_top8': [(t['id'], t['token'], round(t['logprob'], 4)) for t in tl],
                        'arm_token_gap_to_top1': round(tl[0]['logprob'] - tl[ids.index(tok)]['logprob'], 4) if tok in ids else None})
finally:
    p.send_signal(signal.SIGTERM); p.wait(timeout=90)
(R.ROOT / 'stage1' / 'diag_rank.json').write_text(json.dumps(out, indent=1))
print('done', len(out), 'dead', p.poll() is not None)
