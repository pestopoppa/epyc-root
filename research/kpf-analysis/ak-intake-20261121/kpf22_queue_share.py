#!/usr/bin/env python3 -I
"""KPF-22-QUEUE-SHARE: queued share of request latency from serving_calls.jsonl (zero-inference)."""
import json, sys, datetime, collections
def t(s): return datetime.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()
rows = []
for l in open(sys.argv[1]):
    try: d = json.loads(l)
    except Exception: continue
    rows.append(d)
for d in rows:
    d['_s'] = t(d['ts_start']); d['_e'] = d['_s'] + d['wall_ms'] / 1e3
def conc(d):  # other requests on the same server in flight at this one's start
    u = d.get('server', {}).get('base_url') or d.get('caller', {}).get('backend_url')
    return sum(1 for o in rows if o is not d and (o.get('server', {}).get('base_url') or o.get('caller', {}).get('backend_url')) == u and o['_s'] <= d['_s'] < o['_e'])
tab = collections.defaultdict(lambda: dict(n=0, wall=0.0, pre=0.0, kv=0.0, kv_n=0, kv_wall=0.0))
for d in rows:
    c = min(conc(d), 3); k = tab[c]
    k['n'] += 1; k['wall'] += d['wall_ms']; k['pre'] += d['queue'].get('pre_dispatch_wait_ms') or 0
    kv = d.get('kv_admission')
    if kv:
        k['kv_n'] += 1; k['kv'] += kv['queue_wait_ms']; k['kv_wall'] += d['wall_ms']
print('in-flight-at-start | n | pre_dispatch wait/wall % | kv-pool-admission n | kv queue/wall %')
for c in sorted(tab):
    k = tab[c]
    print(c if c < 3 else '3+', k['n'], round(100 * k['pre'] / k['wall'], 1), k['kv_n'], round(100 * k['kv'] / k['kv_wall'], 2) if k['kv_wall'] else 'n/a')
kvs = [d for d in rows if d.get('kv_admission')]
tot_q = sum(d['kv_admission']['queue_wait_ms'] for d in kvs)
big = [d for d in kvs if d['kv_admission']['queue_wait_ms'] > 1000]
print('kv records', len(kvs), 'total queue ms', round(tot_q, 1), 'records queued >1s', len(big),
      'their share of queue time %', round(100 * sum(d['kv_admission']['queue_wait_ms'] for d in big) / tot_q, 1),
      'long_prefill among them', sum(1 for d in big if d['kv_admission']['long_prefill']))
