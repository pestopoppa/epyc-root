#!/usr/bin/env python3
"""DF2-17 analysis: per-prompt tables under the predeclared rules (PREDECLARED.md). Never aggregates into a verdict per arm alone."""
import json, sys, collections
from pathlib import Path
ROOT = Path('/mnt/raid0/llm/tmp/gpu-queue-20261020/df2-17')
stage = sys.argv[1]
D = ROOT / stage
NEAR = 0.5

def load(label):
    p = D / label / 'records.jsonl'
    if not p.exists(): return None
    return {r['id']: r for r in map(json.loads, p.read_text().splitlines())}

def first_diff(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y: return i
    return None if len(a) == len(b) else min(len(a), len(b))

base = load('off_A')
marg = {m['id']: m for m in json.loads((D / 'off_A' / 'baseline_margins.json').read_text())}
arms = {}
for ap in sorted(D.glob('*/arm.json')):
    arms[ap.parent.name] = json.loads(ap.read_text())
out = {'stage': stage, 'baseline_density': {}, 'arms': {}, 'voids': []}
for pid, r in base.items():
    ps = [p for p in marg[pid]['positions'] if p['margin'] is not None]
    n = len(ps)
    out['baseline_density'][pid] = {'n_tokens': len(r['tokens']), 'stop': r['stop_type'], 'margin_identical_to_main': marg[pid]['tokens_identical_to_main_pass'],
        'near_tie_lt_0.5': sum(p['margin'] < NEAR for p in ps) / n if n else None, 'near_tie_lt_0.1': sum(p['margin'] < 0.1 for p in ps) / n if n else None,
        'cap_hit': len(r['tokens']) >= 1600}
for label, arm in arms.items():
    if label == 'off_A': continue
    recs = load(label)
    rows = []
    for pid, b in base.items():
        a = recs.get(pid) if recs else None
        if a is None: rows.append({'id': pid, 'verdict': 'MISSING'}); continue
        fd = first_diff(b['tokens'], a['tokens'])
        row = {'id': pid, 'suite': b.get('suite'), 'verdict': 'PASS' if fd is None else 'FAIL', 'first_diff': fd, 'len_base': len(b['tokens']), 'len_arm': len(a['tokens']),
               'stop_base': b['stop_type'], 'stop_arm': a['stop_type'], 'draft_n': a['draft_n'], 'draft_n_accepted': a['draft_n_accepted'], 'cap_hit_base': len(b['tokens']) >= 1600}
        if fd is not None:
            pos = marg[pid]['positions']
            m = pos[fd] if fd < len(pos) else None
            if m and m['margin'] is not None and fd < len(a['tokens']):
                arm_tok = a['tokens'][fd]
                row.update(base_margin=m['margin'], base_top1=m['top1'], base_top2=m['top2'], arm_token=arm_tok, arm_token_is_base_top2=(arm_tok == m['top2']),
                           class_=('near-tie' if (arm_tok == m['top2'] and m['margin'] < NEAR) else 'degenerative(non-near-tie)'),
                           margin_band=('<0.1' if m['margin'] < 0.1 else '<0.5' if m['margin'] < 0.5 else '>=0.5'))
            else:
                row.update(class_='unclassified(length-only divergence)' if fd >= min(len(a['tokens']), len(b['tokens'])) else 'unclassified')
        rows.append(row)
    out['arms'][label] = {'verify_width': arm['verify_width'], 'kind': arm['kind'], 'n_max': arm['n_max'], 'n_pass': sum(r['verdict'] == 'PASS' for r in rows),
                          'n_fail': sum(r['verdict'] == 'FAIL' for r in rows), 'drafted_all': all((r.get('draft_n') or 0) > 0 for r in rows if r['verdict'] != 'MISSING') if arm['kind'] != 'none' else None,
                          'per_prompt': rows}
for lab in ('off_B', 'serial_df7'):
    if lab in out['arms'] and out['arms'][lab]['n_fail'] > 0: out['voids'].append(f'{lab} not 100% identical to off_A -> stage VOID')
(D / 'df2_17_tables.json').write_text(json.dumps(out, indent=1))
# markdown
md = [f'# DF2-17 {stage}: per-prompt tables (baseline = off_A)\n']
for label, a in out['arms'].items():
    md.append(f'\n## {label} (kind {a["kind"]}, verify width {a["verify_width"]}): PASS {a["n_pass"]}/{a["n_pass"]+a["n_fail"]}, drafted-all={a["drafted_all"]}\n')
    md.append('| prompt | verdict | first diff | base margin | arm tok = base top2 | class | band | len base/arm | draft_n | cap hit |\n|---|---|---|---|---|---|---|---|---|---|')
    for r in a['per_prompt']:
        md.append(f'| {r["id"]} | {r["verdict"]} | {r.get("first_diff")} | {r.get("base_margin", "")} | {r.get("arm_token_is_base_top2", "")} | {r.get("class_", "")} | {r.get("margin_band", "")} | {r.get("len_base")}/{r.get("len_arm")} | {r.get("draft_n")} | {r.get("cap_hit_base")} |')
(D / 'df2_17_tables.md').write_text('\n'.join(md) + '\n')
print(json.dumps({k: (v['n_pass'], v['n_fail']) for k, v in out['arms'].items()}), out['voids'])
