#!/usr/bin/env python3
"""BRF-T1-0: apply-time reconciliation + ordered route-1a fold list (readiness-neutral by real derive_readiness)."""
import json, gzip, re, os, sys, hashlib, collections, subprocess, glob, copy, importlib.util
from pathlib import Path
WT = Path(sys.argv[1]); OUT = Path(sys.argv[2])
sys.path.insert(0, str(WT / 'scripts/handoffs'))
spec = importlib.util.spec_from_file_location('ist', WT / 'scripts/handoffs/index_state.py'); ist = importlib.util.module_from_spec(spec); spec.loader.exec_module(ist)
brc = ist.brc
D = WT / 'docs/design/backlog-refactor-2026-11'
plan = json.load(open(D / 'backlog-refactor-plan-20261102.json'))
man = json.load(gzip.open(D / 'backlog-refactor-manifest-20261102.json.gz'))
ref = json.load(gzip.open(D / 'task-readiness-refinements-20261102.json.gz'))
expm = json.load(open(D / 'backlog-experiment-manifest-20261102.json'))
PIN = man['pinned_sha']
HEAD = subprocess.check_output(['git', '-C', str(WT), 'rev-parse', 'HEAD'], text=True).strip()
def ident(body):
    t = re.sub(r"\s+", " ", re.sub(r"[`*_]", "", body)).strip()[:110].lower()
    return hashlib.sha1(t.encode()).hexdigest()[:12]
A = WT / 'handoffs/active'
# ---------- 1. reconciliation: current boxes vs manifest ----------
cur = collections.defaultdict(dict)   # fn -> id -> (state, line, task_id, cls)
for p in sorted(A.glob('*.md')):
    fn = p.name
    if fn.endswith('-index.md') or fn == 'CURRENT-CAMPAIGN.md': continue
    for lineno, st, body, head in brc._boxes(p):
        code, reasons = brc.classify(p, lineno, st, body, head) if st == ' ' else (0, [])
        cls = 'closed' if st == 'x' else ('dispatchable' if code == 0 else ('guarded' if any('DO-NOT-DISPATCH' in r or 'reusable checklist' in r for r in reasons) else 'refused'))
        m = re.match(r"\**\s*`?([A-Z][A-Z0-9]{1,7}(?:-[A-Z0-9.]+)+[a-z]?)`?", body)
        cur[fn].setdefault(ident(body), ('x' if st == 'x' else ' ', lineno, m.group(1) if m else None, cls, body[:110]))
pin = collections.defaultdict(dict)
for t in man['tasks']:
    fn = t['src'].split(':')[0].split('/')[-1]; pin[fn].setdefault(t['id'], t)
recon = {'pinned_sha': PIN, 'manifest_apply_time_sha': man['apply_time_reconciliation']['current_sha'], 'current_sha': HEAD,
         'commits_since_pin': subprocess.check_output(['git', '-C', str(WT), 'log', '--format=%h %s', f'{PIN}..HEAD'], text=True).splitlines(),
         'handoff_files_changed_since_pin': subprocess.check_output(['git', '-C', str(WT), 'diff', '--name-status', PIN, 'HEAD', '--', 'handoffs/'], text=True).splitlines(),
         'files': {}}
ticked = set()
for fn in sorted(set(cur) | set(pin)):
    c, pn = cur.get(fn, {}), pin.get(fn, {})
    r = {'ticked_since_pin': [k for k in pn if pn[k]['state'] == ' ' and k in c and c[k][0] == 'x'],
         'reopened_since_pin': [k for k in pn if pn[k]['state'] == 'x' and k in c and c[k][0] == ' '],
         'new_open': [{'id': k, 'line': c[k][1], 'task_id': c[k][2], 'class': c[k][3], 'text': c[k][4]} for k in c if k not in pn and c[k][0] == ' '],
         'new_closed': [k for k in c if k not in pn and c[k][0] == 'x'],
         'missing_in_current': [k for k in pn if k not in c]}
    nt = lambda x: re.sub(r"[`*_\s]", "", x)[:60].lower()
    newtxt = {nt(c[k][4]): k for k in c if k not in pn}
    r['reidentified_same_text'] = [{'pinned_id': k, 'current_id': newtxt[nt(pn[k]['text'])], 'state_pinned': pn[k]['state'], 'state_now': c[newtxt[nt(pn[k]['text'])]][0]}
                                   for k in r['missing_in_current'] if nt(pn[k]['text']) in newtxt]
    gone = {x['pinned_id'] for x in r['reidentified_same_text']}; came = {x['current_id'] for x in r['reidentified_same_text']}
    r['missing_in_current'] = [k for k in r['missing_in_current'] if k not in gone]
    r['new_open'] = [x for x in r['new_open'] if x['id'] not in came]; r['new_closed'] = [k for k in r['new_closed'] if k not in came]
    if fn not in pin: r['new_file'] = True
    if fn not in cur: r['file_gone_from_active'] = True
    ticked |= {(fn, k) for k in r['ticked_since_pin']}
    if any(v for v in r.values()): recon['files'][fn] = r
recon['totals'] = {'manifest_tasks': len(man['tasks']), 'current_tasks': sum(len(v) for v in cur.values()),
                   **{k: sum(len(v.get(k, [])) for v in recon['files'].values()) for k in ['ticked_since_pin', 'reopened_since_pin', 'new_open', 'new_closed', 'missing_in_current', 'reidentified_same_text']}}
# ---------- 2. graph from the real index_state logic ----------
state = ist.collect(); g = ist.build_graph(state)
nodes = {n['id']: n for n in g['nodes']}
dep = [(e['from'], e['to']) for e in g['edges'] if e.get('kind') == 'dep']
h2n = {n['handoff'].split('/')[-1]: n['id'] for n in g['nodes']}
def disp(n): return n.get('dispatchable', n.get('open', 0))
def readiness(groupmap):
    """groupmap: node id -> group id. Real derive_readiness on the merged graph; returns per-ORIGINAL-node readiness."""
    agg = {}
    for nid, n in nodes.items():
        gid = groupmap.get(nid, nid); a = agg.setdefault(gid, {'id': gid, 'dispatchable': 0}); a['dispatchable'] += disp(n)
    edges = [{'kind': 'dep', 'from': groupmap.get(f, f), 'to': groupmap.get(t, t)} for f, t in dep]
    edges = [e for e in edges if e['from'] != e['to']]
    ml = list(agg.values()); counts = ist.derive_readiness(ml, edges); byg = {m['id']: m for m in ml}
    return {nid: byg[groupmap.get(nid, nid)]['readiness'] for nid in nodes}, counts
base, base_counts = readiness({})
def flips(groupmap):
    after, counts = readiness(groupmap)
    return [nid for nid in nodes if disp(nodes[nid]) > 0 and after[nid] != base[nid]], counts
# ---------- 3. candidate groups per plan target ----------
meq = set(plan['model_evaluation_queue']['whole_handoffs'])
retire = {h['handoff'] for h in plan['handoffs'] if h['action'] == 'retire'}
pl = {h['handoff']: h for h in plan['handoffs']}
tgt_meta = {t['target']: t for t in plan['targets']}
h2t = {}
for h in plan['handoffs']:
    fn = h['handoff']
    if fn in retire or fn in meq or fn not in h2n: continue
    h2t[fn] = h['target'] or fn
bytgt = collections.defaultdict(list)
for fn, t in h2t.items(): bytgt[t].append(fn)
groups = []   # list of lists of fn
for t, mem in bytgt.items():
    part = collections.defaultdict(list)
    for fn in mem:
        n = nodes[h2n[fn]]; part[(n['readiness'], tuple(sorted(n.get('blocked_by', []))))].append(fn)
    groups += [(t, sorted(v)) for v in part.values()]
def gmap(gs):
    m = {}
    for t, mem in gs:
        anc = anchor(mem)
        for fn in mem: m[h2n[fn]] = h2n[anc]
    return m
def anchor(mem):
    return max(mem, key=lambda fn: (disp(nodes[h2n[fn]]), pl[fn]['action'] in ('rename-to-target', 'rename-to-target+split', 'keep-as-target', 'keep'), fn))
# validate each group alone and jointly; split offenders to singletons
changed = True
while changed:
    changed = False
    bad, _ = flips(gmap(groups))
    if bad:
        badfn = {fn for fn, nid in h2n.items() if nid in bad}
        new = []
        for t, mem in groups:
            if len(mem) > 1 and badfn & set(mem):
                new += [(t, [fn]) for fn in mem]; changed = True
            else: new.append((t, mem))
        groups = new
# greedy coalesce within a target where the real readiness stays identical
merged = True
while merged:
    merged = False
    for t in list(bytgt):
        gs = [g_ for g_ in groups if g_[0] == t]
        for i in range(len(gs)):
            for j in range(i + 1, len(gs)):
                gm = gmap(groups)
                sig = lambda fn: (nodes[h2n[fn]]['readiness'], frozenset(gm.get(b, b) for b in nodes[h2n[fn]].get('blocked_by', [])))
                if len({sig(fn) for fn in gs[i][1] + gs[j][1]}) != 1: continue   # same dep targets with open work (route-1a rule), not just same readiness today
                trial = [g_ for g_ in groups if g_ is not gs[i] and g_ is not gs[j]] + [(t, sorted(gs[i][1] + gs[j][1]))]
                if not flips(gmap(trial))[0]:
                    groups = trial; merged = True; break
            if merged: break
        if merged: break
final_bad, final_counts = flips(gmap(groups))
assert not final_bad, final_bad
# ---------- 4. registries ----------
CF = Path('/mnt/raid0/llm/tmp/compute-flags')
hs = json.load(open(CF / 'handoff-sessions.json')).get('sessions', {})
ready = []
for f in glob.glob(str(CF / 'ready/*.json')):
    try: d = json.load(open(f))
    except Exception: continue
    if isinstance(d, dict) and isinstance(d.get('handoff_task'), str): ready.append((os.path.basename(f), d['handoff_task']))
curated = (WT / 'scripts/handoffs/backlog_priority_curated.json').read_text()
master = (A / 'master-handoff-index.md').read_text()
idx_rows = state['rows']
refs_by_file = collections.defaultdict(list)
for r in ref['tasks']: refs_by_file[r['src'].split(':')[0].split('/')[-1]].append(r)
pending_total = 0
def linking(fn):
    out = subprocess.run(['git', '-C', str(WT), 'grep', '-l', '-F', f'handoffs/active/{fn}', '--', 'handoffs', 'docs', 'wiki', 'progress', 'scripts', 'agents', '.claude'], capture_output=True, text=True).stdout.split()
    out2 = subprocess.run(['git', '-C', str(WT), 'grep', '-l', '-F', f']({fn})', '--', 'handoffs/active'], capture_output=True, text=True).stdout.split()
    return sorted(set(out) | set(out2))
# ---------- 5. order + entries ----------
neutral_targets = {t for t in bytgt if len([g_ for g_ in groups if g_[0] == t]) == 1}
folds = [g_ for g_ in groups if len(g_[1]) > 1]
def rank(g_):
    t = g_[0]; return (0 if t in neutral_targets else 1, tgt_meta.get(t, {}).get('priority_rank_after', 99), t, -len(g_[1]))
folds.sort(key=rank)
# primary group of each target = the one that takes the plan target name
primary = {}
for t, mem in groups:
    sc = (any(pl[f]['action'] in ('rename-to-target', 'rename-to-target+split', 'keep-as-target', 'keep') or f == t for f in mem), sum(disp(nodes[h2n[f]]) for f in mem))
    if t not in primary or sc > primary[t][0]: primary[t] = (sc, mem)
applied = []; entries = []
n_active = len([p for p in A.glob('*.md')]); n_completed = len(list((WT / 'handoffs/completed').glob('*.md')))
n_nodes = len(nodes); n_handoffs_tracked = len(state['handoffs'])
for k, (t, mem) in enumerate(folds, 1):
    anc = anchor(mem); srcs = [f for f in mem if f != anc]
    dest = t if primary[t][1] == mem else anc
    rows = {f: h2n[f] for f in mem}; keep_row = h2n[anc]; retired = [h2n[f] for f in srcs]
    applied.append((t, mem)); fl, counts = flips(gmap(applied)); assert not fl
    n_nodes -= len(srcs); n_active -= len(srcs); n_completed += len(srcs)
    dests = {f: dest for f in mem}
    sess = [{'slug': s, 'handoff_from': v.get('handoff'), 'handoff_to': f'handoffs/active/{dest}', 'handoff_rows_to': [keep_row]}
            for s, v in sorted(hs.items()) if isinstance(v, dict) and (v.get('handoff') or '').split('/')[-1] in mem and (v.get('handoff') or '').split('/')[-1] != dest]
    rowf = []
    for name, ht in sorted(ready):
        mm = re.match(r'^(handoffs/active/)?([A-Za-z0-9._-]+\.md)(.*)$', ht.strip())
        if mm and mm.group(2) in mem and mm.group(2) != dest:
            rowf.append({'spec': name, 'from': ht, 'to': f'handoffs/active/{dest}{mm.group(3)}'})
    tasks_cnt = sum(len(cur[f]) for f in mem); open_cnt = sum(1 for f in mem for v in cur[f].values() if v[0] == ' ')
    rec = {f: recon['files'][f] for f in mem if f in recon['files']}
    refs = [{'id': r['id'], 'task_id': r['task_id'], 'src': r['src'], 'class': r['class'], 'failed': r['failed'], 'decision_kind': r['decision_kind'], 'proposed': r['proposed']}
            for f in mem for r in refs_by_file[f] if (f, r['id']) not in ticked and r['id'] in cur[f] and cur[f][r['id']][0] == ' ']
    pend = [r for r in refs if r['decision_kind'] == 'pending-choice']; pending_total += len(pend)
    deps_union = sorted({d for f in mem for d in idx_rows[h2n[f]].get('deps', []) if d not in rows.values()})
    repoint = sorted({rid for rid, r in idx_rows.items() if rid not in rows.values() and set(r.get('deps', [])) & set(retired)})
    entries.append({
        'order': k, 'plan_target': t, 'destination': f'handoffs/active/{dest}',
        'destination_is_rename': dest != anc, 'anchor': f'handoffs/active/{anc}', 'anchor_row_kept': keep_row,
        'sources': [f'handoffs/active/{f}' for f in srcs],
        'moves': [f'git mv handoffs/active/{f} handoffs/completed/{f}' for f in srcs] + ([f'git mv handoffs/active/{anc} handoffs/active/{dest}'] if dest != anc else []),
        'sections': [{'source': f, 'section': f'## Track: {f[:-3]}', 'provenance': f'Folded from handoffs/active/{f} @ <sha12 at fold>', 'open_boxes_moved': sum(1 for v in cur[f].values() if v[0] == " ")} for f in srcs],
        'gate_signature': {'readiness': nodes[keep_row]['readiness'], 'blocked_by': nodes[keep_row].get('blocked_by', [])},
        'index_row_changes': {'delete_rows': [{'row': h2n[f], 'index': idx_rows[h2n[f]]['index']} for f in srcs],
                              'keep_row': {'row': keep_row, 'index': idx_rows[keep_row]['index'], 'plan_owner_index': tgt_meta.get(t, {}).get('owner_index'),
                                           'handoff_cell': dest, 'deps_union': deps_union},
                              'repoint_deps_in_rows': repoint,
                              'operator_queue_owner_cells': [r for r in retired if re.search(rf'\b{r}\b', master)],
                              'curated_priority_rekey_candidates': [r for r in retired if f'"{r}' in curated],
                              'repoint_reason_trailers': [f'Repoint-Reason: {r}: folded into {keep_row} ({dest}) — route 1a, D5' for r in retired]},
        'redirects': {'rows': {r: keep_row for r in retired}, 'files': {f: f'{dest}#track:{f[:-3]}' for f in srcs} | ({anc: dest} if dest != anc else {})},
        'link_repoint_files': {f: linking(f) for f in srcs + ([anc] if dest != anc else [])},
        'session_slug_rewrites': sess, 'rowflow_handoff_task_rewrites': rowf,
        'reconciliation': rec,
        'readiness_refinements': refs,
        'decision_package_D7': {'pending_choices': len(pend), 'tasks': [{'id': r['id'], 'task_id': r['task_id'], 'src': r['src']} for r in pend],
                                'delivery': 'AskUserQuestion at this fold; options+tradeoffs+recommendation from proposed; a dismissed question pauses only its own item'},
        'expected_gate': {'tasks_open_plus_closed_before': tasks_cnt, 'tasks_open_plus_closed_after': tasks_cnt, 'open_before': open_cnt, 'open_after': open_cnt,
                          'readiness_diff': {'changed': [], 'removed_nodes': retired, 'added_nodes': []},
                          'graph_after': {'nodes': n_nodes, 'readiness_counts': counts},
                          'board_files_after': {'active_md': n_active, 'completed_md': n_completed},
                          'queue_rows_delta': 0, 'orphaned_handoff_task_after': 0, 'orphaned_session_slugs_after': 0,
                          'commands': ['python3 scripts/handoffs/index_state.py', 'python3 scripts/handoffs/index_state.py --check',
                                       'python3 scripts/handoffs/task_lint.py migrate <touched>', 'dashboard tests: 132 pass, 4 known test_dashboard_nav /amd-ai-lab failures']}})
batches = [{'batch': i // 8 + 1, 'orders': [e['order'] for e in entries[i:i + 8]]} for i in range(0, len(entries), 8)]
handoffs_before = len(h2n); after_1a = handoffs_before - sum(len(e['sources']) for e in entries)
out = {'schema': 'brf-fold-list-1a.v1', 'generated': '2026-11-02', 'origin_main': HEAD, 'pinned_sha': PIN,
       'rule': 'route 1a (D1): members of one fold share the real derive_readiness signature (readiness, blocked_by) and the joint merged graph (self-deps dropped) flips no node with dispatchable>0; validated cumulatively in list order with scripts/handoffs/index_state.py derive_readiness at origin_main',
       'excluded': {'retire_BRF-T1-RET': sorted(retire), 'model_evaluation_queue_BRF-T1-MEQ': sorted(meq),
                    'not_in_plan_new_since_pin': sorted(set(h2n) - set(pl)),
                    'meq_carves_left_for_BRF-T1-MEQ': plan['model_evaluation_queue']['box_moves']},
       'counts': {'graph_nodes_before': len(nodes), 'readiness_before': base_counts, 'readiness_after_all_1a': final_counts,
                  'folds': len(entries), 'batches': len(batches), 'sources_folded': sum(len(e['sources']) for e in entries),
                  'handoffs_before': handoffs_before, 'handoffs_after_1a_folds': after_1a,
                  'handoffs_after_1a_with_RET': after_1a - len([f for f in retire if f in h2n]),
                  'groups_incl_singletons': len(groups), 'pending_choices_in_folds': pending_total,
                  'neutral_targets': sorted(neutral_targets)},
       'reconciliation': recon, 'batches': batches, 'folds': entries}
out['id_encoding'] = "task ids are the manifest's 12-hex sha1 identity prefixed 'h' (an all-digit id trips the PII digit-run pre-commit hook); strip the leading 'h' before matching the manifest"
HEX = re.compile(r'^[0-9a-f]{12}$')
def enc(o, k=None):
    if isinstance(o, dict): return {kk: enc(v, kk) for kk, v in o.items()}
    if isinstance(o, list): return [enc(v, k) for v in o]
    if isinstance(o, str) and HEX.match(o) and k in ('id', 'pinned_id', 'current_id', 'ticked_since_pin', 'reopened_since_pin', 'new_closed', 'missing_in_current'): return 'h' + o
    return o
out = enc(out)
json.dump(out, open(OUT, 'w'), indent=1, ensure_ascii=False)
print(json.dumps(out['counts'], indent=1)); print(json.dumps(recon['totals'])); print({k: {kk: (len(vv) if isinstance(vv, list) else vv) for kk, vv in v.items()} for k, v in recon['files'].items()})
print('size', os.path.getsize(OUT))
