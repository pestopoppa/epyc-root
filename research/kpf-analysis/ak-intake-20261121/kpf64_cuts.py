#!/usr/bin/env python3 -I
"""KPF-64-CUTS: count checkpoint-induced prefill cuts per request from a llama-server verbose log.

Usage: kpf64_cuts.py LOG [LOG...]   (zero-inference; reads logs only)

Per request (slot id + task) the log gives:
  "new prompt ... task.n_tokens = N"
  "cached n_tokens = K, memory_seq_rm [K, end)"   logged when a batch starting at K is assembled
  "created context checkpoint ... n_tokens = K"   created BEFORE the batch starting at K is decoded
  "init sampler ... text = N"                      prompt finished assembling (last batch queued)
so batch i spans [K_i, K_{i+1}) and its wall time is ts(K_{i+1}) - ts(K_i) (includes checkpoint creation).
"""
import re, sys, json, math, collections

TS = r'(\d+)\.(\d\d)\.(\d\d\d)\.(\d\d\d)'
def ts(m):  # mm.ss.ms.us
    return int(m[0]) * 60 + int(m[1]) + int(m[2]) / 1e3 + int(m[3]) / 1e6

R_NEW = re.compile(r'^' + TS + r' I slot\s+operator\(\): id\s+(\d+) \| task (-?\d+) \| new prompt, n_ctx_slot = \d+, n_keep = \d+, task.n_tokens = (\d+)')
R_CACHED = re.compile(r'^' + TS + r' I slot\s+operator\(\): id\s+(\d+) \| task (-?\d+) \| cached n_tokens = (\d+), memory_seq_rm')
R_CKPT = re.compile(r'^' + TS + r' I slot create_check: id\s+(\d+) \| task (-?\d+) \| created context checkpoint \d+ of \d+ \(pos_min = \d+, pos_max = \d+, n_tokens = (\d+)')
R_INIT = re.compile(r'^' + TS + r' I slot init_sampler: id\s+(\d+) \| task (-?\d+) \| init sampler, took [\d.]+ ms, tokens: text = (\d+)')
R_REL = re.compile(r'^' + TS + r' I slot\s+release: id\s+(\d+) \| task (-?\d+) \|')

def parse(path):
    open_req = {}   # slot id -> dict
    done = []
    with open(path, errors='replace') as f:
        for line in f:
            m = R_NEW.match(line)
            if m:
                t = ts(m.groups()[:4]); sid = int(m.group(5)); N = int(m.group(7))
                open_req[sid] = dict(slot=sid, task=int(m.group(6)), N=N, t0=t, bounds=[], ckpt={}, t_init=None)
                continue
            m = R_CACHED.match(line)
            if m:
                sid = int(m.group(5)); r = open_req.get(sid)
                if r and r['t_init'] is None:
                    r['bounds'].append((int(m.group(7)), ts(m.groups()[:4])))
                continue
            m = R_CKPT.match(line)
            if m:
                sid = int(m.group(5)); r = open_req.get(sid)
                if r and r['t_init'] is None:
                    r['ckpt'][int(m.group(7))] = ts(m.groups()[:4])
                continue
            m = R_INIT.match(line)
            if m:
                sid = int(m.group(5)); r = open_req.get(sid)
                if r and r['t_init'] is None:
                    r['t_init'] = ts(m.groups()[:4])
                    done.append(open_req.pop(sid))
                continue
    return done

def analyse(reqs, n_ubatch=2048):
    rows = []
    for r in reqs:
        b = r['bounds']
        if not b or r['t_init'] is None:
            continue
        K = [x[0] for x in b]; T = [x[1] for x in b] + [r['t_init']]
        if any(T[i+1] < T[i] for i in range(len(T)-1)):
            continue  # clock reset across a server restart
        N = r['N']; K0 = K[0]; n_proc = N - K0
        if n_proc <= 0:
            continue
        ends = K[1:] + [N]
        batches = []
        for i in range(len(K)):
            L = ends[i] - K[i]
            if L <= 0:
                continue
            batches.append(dict(start=K[i], L=L, wall=T[i+1] - T[i], end=ends[i]))
        # kind of the boundary that ENDS each batch (i.e. the cut position)
        for bt in batches:
            e = bt['end']
            if e == N:
                bt['kind'] = 'final'
            else:
                off = N - e
                has_ck = e in r['ckpt']
                if off == 4:
                    bt['kind'] = 'n-4'
                elif off == min(n_ubatch, 4 + n_ubatch) or off == 4 + n_ubatch:
                    bt['kind'] = 'n-(4+n_ubatch)'
                elif has_ck and off < n_ubatch:
                    bt['kind'] = 'near-end-other'
                elif has_ck:
                    bt['kind'] = 'user-start/junction'
                elif bt['L'] < n_ubatch:
                    bt['kind'] = 'partial-no-ckpt'   # batch-budget share / non-checkpoint break
                else:
                    bt['kind'] = 'full'
        n_b = len(batches)
        n_min = math.ceil(n_proc / n_ubatch)
        ub = sum(math.ceil(b_['L'] / n_ubatch) for b_ in batches)
        ck_wall = [r['ckpt'][k] - T[i] for i, k in enumerate(K) if k in r['ckpt'] and k != N]
        rows.append(dict(task=r['task'], N=N, n_proc=n_proc, batches=batches, n_iter=n_b,
                         extra_iter=n_b - n_min, ubatches=ub, extra_ub=ub - n_min,
                         wall=T[-1] - T[0], ck_n=len(ck_wall), ck_wall=sum(ck_wall)))
    return rows

CUT_KINDS = ('user-start/junction', 'near-end-other', 'n-(4+n_ubatch)', 'n-4')

def report(rows, n_ubatch=2048, rho_fallback=None):
    """Per-kind table. Extra wall of a cut = the fixed part of the partial batch it ends,
    max(0, T_i - rho*L_i), rho = the request's own full-ubatch s/token (global median if it has none);
    plus the checkpoint-creation wall at that boundary. Upper-ish: the interval also holds other slots' work."""
    import statistics as S
    full = [b['wall'] / b['L'] for r in rows for b in r['batches'] if b['kind'] == 'full' and b['L'] == n_ubatch]
    rho_g = S.median(full) if full else rho_fallback
    out = {k: dict(cuts=0, extra_wall=0.0, ckpt_wall=0.0, reqs=set()) for k in CUT_KINDS}
    tot_wall = sum(r['wall'] for r in rows)
    ex_ub = sum(r['extra_ub'] for r in rows); ex_it = sum(r['extra_iter'] for r in rows)
    for ri, r in enumerate(rows):
        fl = [b['wall'] / b['L'] for b in r['batches'] if b['kind'] == 'full' and b['L'] == n_ubatch]
        rho = S.median(fl) if fl else rho_g
        for b in r['batches']:
            k = b['kind']
            if k in out:
                o = out[k]; o['cuts'] += 1; o['reqs'].add(ri)
                o['extra_wall'] += max(0.0, b['wall'] - rho * b['L'])
    n = len(rows)
    res = dict(requests=n, prefill_wall_s=round(tot_wall, 1), extra_ubatches_per_req=round(ex_ub / n, 3),
               extra_iterations_per_req=round(ex_it / n, 3), rho_global_ms_per_tok=round(rho_g * 1e3, 3))
    tab = {}
    for k, o in out.items():
        tab[k] = dict(cuts_per_req=round(o['cuts'] / n, 3), frac_reqs=round(len(o['reqs']) / n, 3),
                      extra_wall_s=round(o['extra_wall'], 1), share_pct=round(100 * o['extra_wall'] / tot_wall, 2))
    res['by_kind'] = tab
    res['sum_share_pct'] = round(sum(t['share_pct'] for t in tab.values()), 2)
    ck = sum(r['ck_wall'] for r in rows)
    res['ckpt_create_wall_s'] = round(ck, 1); res['ckpt_create_share_pct'] = round(100 * ck / tot_wall, 2)
    res['ckpts_per_req'] = round(sum(r['ck_n'] for r in rows) / n, 3)
    return res

def main():
    reqs = []
    for p in sys.argv[1:]:
        reqs += parse(p)
    rows = analyse(reqs)
    res = report(rows)
    rho0 = res['rho_global_ms_per_tok'] / 1e3
    # split by prompt size: short (<=200 processed tokens) vs rest
    res['short_req_le200_pct'] = round(100 * sum(1 for r in rows if r['n_proc'] <= 200) / len(rows), 1)
    for name, sel in (('n_proc<=200', lambda r: r['n_proc'] <= 200), ('200<n_proc<=2048', lambda r: 200 < r['n_proc'] <= 2048), ('n_proc>2048', lambda r: r['n_proc'] > 2048)):
        sub = [r for r in rows if sel(r)]
        if sub:
            q = report(sub, rho_fallback=rho0); res.setdefault('by_size', {})[name] = dict(
                requests=q['requests'], prefill_wall_s=q['prefill_wall_s'], sum_share_pct=q['sum_share_pct'],
                extra_ub_per_req=q['extra_ubatches_per_req'], ckpt_share_pct=q['ckpt_create_share_pct'])
    print(json.dumps(res, indent=1))

if __name__ == '__main__':
    main()
