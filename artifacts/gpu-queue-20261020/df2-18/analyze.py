#!/usr/bin/env python3
"""Parse rowexact_margin logs -> per-row JSONL + per-width table + A/A verdicts."""
import json, re, sys, collections
from pathlib import Path
ROOT = Path('/mnt/raid0/llm/tmp/gpu-queue-20261020/df2-18')
sub = sys.argv[1] if len(sys.argv) > 1 else 'runs'
D = ROOT / sub
NODE = re.compile(r'^    #(\d+)\s+(\S+)\s+(\S+)\s+(\[[^\]]*\])\s+(\S+)\s+diff (\d+)/(\d+) max\|d\|=(\S+) first@(-?\d+)')
LAY = re.compile(r'-(\d+)$')

def parse(path):
    rows, cur, out = [], None, {'rows': [], 'digest': {}}
    for line in path.read_text(errors='replace').splitlines():
        m = re.match(r'^-- token row (\d+) \(pos (\d+)\)', line)
        if m:
            cur = {'row': int(m.group(1)), 'pos': int(m.group(2)), 'diff_nodes': []}; out['rows'].append(cur); continue
        if cur is None: continue
        m = NODE.match(line)
        if m:
            cur['diff_nodes'].append({'idx': int(m.group(1)), 'name': m.group(2), 'op': m.group(3), 'ne': m.group(4), 'type': m.group(5),
                                      'n_diff': int(m.group(6)), 'n_elem': int(m.group(7)), 'max_abs': float(m.group(8))}); continue
        m = re.match(r'^  nodes .*: compared (\d+), DIFFER (\d+), first=(\S+), shape-skip (\d+), unmatched-name (\d+) \(batch (\d+) nodes, ref (\d+) nodes\)', line)
        if m:
            cur.update(compared=int(m.group(1)), differ=int(m.group(2)), first_name=m.group(3), shape_skip=int(m.group(4)), unmatched=int(m.group(5))); continue
        m = re.match(r'^  logits .*: (IDENTICAL|DIFFER) n_diff=(\d+)/(\d+) max\|d\|=(\S+) argmax (\d+)(==|!=)(\d+)', line)
        if m:
            cur.update(logits_identical=m.group(1) == 'IDENTICAL', logit_n_diff=int(m.group(2)), logit_max_abs=float(m.group(4)), argmax_same=m.group(6) == '=='); continue
        m = re.match(r'^  MARGIN row=(\d+) ref_top1=(\d+) ref_top2=(\d+) ref_margin=(\S+) bat_top1=(\d+) bat_top2=(\d+) bat_margin=(\S+)', line)
        if m:
            cur.update(ref_top1=int(m.group(2)), ref_top2=int(m.group(3)), ref_margin=float(m.group(4)), bat_top1=int(m.group(5)), bat_top2=int(m.group(6)), bat_margin=float(m.group(7))); continue
        m = re.match(r'^  DIGEST row=(\d+) ref_nodes=(\w+)', line)
        if m: cur['ref_nodes_digest'] = m.group(2); continue
        m = re.match(r'^DIGEST batch_nodes=(\w+) n_batch_nodes=(\d+)', line)
        if m: out['digest']['batch_nodes'] = m.group(1); out['digest']['n_batch_nodes'] = int(m.group(2)); continue
        m = re.match(r'^DIGEST logits_batch=(\w+) logits_ref=(\w+)', line)
        if m: out['digest']['logits_batch'] = m.group(1); out['digest']['logits_ref'] = m.group(2); continue
        m = re.match(r'^  state .*: (IDENTICAL|DIFFER)', line)
        if m: out['state_identical'] = m.group(1) == 'IDENTICAL'
    return out

def layer_of(nodes, i):
    n = nodes[i]
    m = LAY.search(n['name'])
    if m: return int(m.group(1)), False
    for j in range(i + 1, min(i + 6, len(nodes))):
        m = LAY.search(nodes[j]['name'])
        if m: return int(m.group(1)), True
    return None, True

res = []
metas = {p.stem.replace('.meta', ''): json.loads(p.read_text()) for p in D.glob('*.meta.json')}
parsed = {}
for lab, meta in sorted(metas.items()):
    p = D / f'{lab}.log'
    parsed[lab] = parse(p)
    for r in parsed[lab]['rows']:
        nodes = r['diff_nodes']
        first = None
        if nodes:
            lay, inferred = layer_of(nodes, 0)
            first = {'idx': nodes[0]['idx'], 'name': nodes[0]['name'], 'op': nodes[0]['op'], 'type': nodes[0]['type'], 'layer': lay, 'layer_inferred': inferred}
        by_op = collections.Counter(n['op'] for n in nodes)
        by_op_type = collections.Counter(f"{n['op']}:{n['type']}" for n in nodes)
        res.append({'label': lab, 'width': meta['width'], 'prefix': meta['prefix'], 'nocap': meta['nocap'], 'env': meta['extra_env'], 'row': r['row'],
                    'first_differing_node': first, 'n_compared': r.get('compared'), 'n_differ': r.get('differ'), 'shape_skip': r.get('shape_skip'),
                    'differ_by_op': dict(by_op), 'differ_by_op_type': dict(by_op_type),
                    'logit_max_abs': r.get('logit_max_abs'), 'logits_identical': r.get('logits_identical'), 'argmax_same': r.get('argmax_same'),
                    'ref_margin': r.get('ref_margin'), 'bat_margin': r.get('bat_margin'), 'ref_top1': r.get('ref_top1'), 'ref_top2': r.get('ref_top2'),
                    'bat_top1': r.get('bat_top1'), 'bat_top2': r.get('bat_top2'),
                    'ref_nodes_digest': r.get('ref_nodes_digest'), 'batch_digest': parsed[lab]['digest'].get('batch_nodes'),
                    'residency': meta['residency'], 'rc': meta['rc']})
(D / 'rows.jsonl').write_text(''.join(json.dumps(x) + '\n' for x in res))

# A/A: label pairs *_a / *_b
aa = []
for lab in sorted(parsed):
    if lab.endswith('_a') and lab[:-1] + 'b' in parsed:
        a, b = parsed[lab], parsed[lab[:-1] + 'b']
        same = (a['digest'] == b['digest'] and len(a['rows']) == len(b['rows']) and
                all(x.get('ref_nodes_digest') == y.get('ref_nodes_digest') and x.get('logit_max_abs') == y.get('logit_max_abs')
                    and x.get('differ') == y.get('differ') and x.get('first_name') == y.get('first_name') for x, y in zip(a['rows'], b['rows'])))
        aa.append({'pair': lab[:-2], 'bitwise_identical': same, 'digest_a': a['digest'], 'digest_b': b['digest']})
(D / 'aa.json').write_text(json.dumps(aa, indent=1))
print('runs', len(metas), 'rows', len(res), 'A/A pairs', len(aa), 'A/A identical', sum(x['bitwise_identical'] for x in aa))
for x in aa:
    if not x['bitwise_identical']: print('A/A NOT IDENTICAL:', x['pair'])
