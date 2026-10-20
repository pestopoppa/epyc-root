#!/usr/bin/env python3
"""analysis.py <outdir> : build the timing tables (speech ms/frame or whisper ms, speed-up vs prod, neighbour throughput)
from final/results_qts.jsonl, timing/results_qts.jsonl (prod heavy rows of the first claim) and timing/results_whisper.jsonl."""
import json, statistics as st, collections, sys, pathlib

T = pathlib.Path('/mnt/raid0/llm/tmp/qwentts_threadpool_20261020')
out = pathlib.Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
lines = []


def P(s=''):
    print(s)
    lines.append(s)


def load(p):
    return [json.loads(l) for l in open(p)] if pathlib.Path(p).exists() else []


def nb_window_tps(r):
    """neighbour tokens/s over the speech process window [t0,t1], interpolating the partial reps at the edges."""
    reps = r.get('nb_reps_abs') or []
    t0, t1 = r['t0'], r['t1']
    tok = 0.0
    for a, b, tps in reps:
        lo, hi = max(a, t0), min(b, t1)
        if hi > lo:
            tok += 32.0 * (hi - lo) / (b - a)
    return tok / (t1 - t0) if t1 > t0 else None


def table(rows, key, title, nb_alone=None):
    g = collections.OrderedDict()
    for r in rows:
        if 'leg' not in r or r.get('variant') == 'nb_alone':
            continue
        g.setdefault((r['leg'], r['variant'], r.get('block', 'main')), []).append(r)
    P(f'### {title}')
    P('| leg | variant | n | median | min-max | vs prod | neighbour tok/s in window (median) |')
    P('|---|---|---|---|---|---|---|')
    base = {}
    for (leg, var, blk), rs in g.items():
        v = [r[key] for r in rs if r.get(key) is not None and not r['timeout']]
        to = sum(1 for r in rs if r['timeout'])
        if not v:
            P(f'| {leg} | {var}{"/" + blk if blk != "main" else ""} | 0 (TO={to}) | | | | |')
            continue
        m = st.median(v)
        if var == 'prod' and blk == 'main':
            base[leg] = m
        sp = f'x{base[leg] / m:.2f}' if leg in base and var != 'prod' else ''
        nb = [nb_window_tps(r) for r in rs if r.get('nb_reps_abs')]
        nb = [x for x in nb if x is not None]
        nbs = f'{st.median(nb):.2f}' if nb else ''
        P(f'| {leg} | {var}{"/" + blk if blk != "main" else ""} | {len(v)}{f" (TO={to})" if to else ""} | {m:.1f} | {min(v):.1f}-{max(v):.1f} | {sp} | {nbs} |')
    for r in rows:
        if r.get('variant') == 'nb_alone' and r.get('stamp_tps'):
            P(f'neighbour alone {r["leg"]}: median {st.median(r["stamp_tps"]):.2f} tok/s over {len(r["stamp_tps"])} reps (llama-bench internal avg {r["avg_ts"]:.2f})')
    P()


import datetime as dt
def _ep(x): return dt.datetime.fromisoformat(x.replace('Z', '+00:00')).timestamp()
# coordinator contamination notice: another agent co-ran a 24-thread llama-server on q0 cpus 0-23 in these windows
Q0_WINDOWS = [(_ep('2026-10-20T21:08:36Z'), _ep('2026-10-20T21:15:00Z')), (_ep('2026-10-20T21:34:30Z'), _ep('2026-10-20T21:51:39Z')),
              (_ep('2026-10-20T22:09:39Z'), _ep('2026-10-20T22:31:00Z'))]
def clean(rows):
    ok = []
    dropped = 0
    for r in rows:
        if 't0' in r and r.get('region') == '0-23' and any(r['t0'] < b and r['t1'] > a for a, b in Q0_WINDOWS):
            dropped += 1
            continue
        ok.append(r)
    P(f'(q0 reps discarded for overlapping the contamination windows: {dropped})')
    return ok
qf = clean(load(T / 'final/results_qts.jsonl') + load(T / 'final2/results_qts.jsonl') + load(T / 'final3/results_qts.jsonl'))
table(qf, 'total_ms_frame', 'qwen-tts, final claim (candidate = build2, total ms/frame, lower is better)')
qm = [r for r in load(T / 'timing/results_qts.jsonl')]
table(qm, 'total_ms_frame', 'qwen-tts, first claim (older fixed-budget builds; fixed-spin futex/yield variants), total ms/frame')
wm = load(T / 'timing/results_whisper.jsonl')
table(wm, 'total_ms', 'whisper-cli large-v3-turbo, 13/30 s window, total ms (lower is better)')
table(wm, 'encode_ms', 'whisper-cli, encode ms')
table(wm, 'batchd_ms', 'whisper-cli, batched-decode ms (the barrier-heavy phase)')
(out / 'timing_summary.md').write_text('\n'.join(lines) + '\n')
