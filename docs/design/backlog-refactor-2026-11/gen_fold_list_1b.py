#!/usr/bin/env python3
"""BRF-T7-1: ordered route-1b fold list (route-1a end state -> 29 domain handoffs), neutral per TRACK.

    python3 gen_fold_list_1b.py <worktree at origin/main + BRF-T1-1/T7-1 tooling> <out.json>

Route 1a (fold-list-1a.json) merged only handoffs with the same readiness signature. Route 1b merges
handoffs whose readiness DIFFERS: every former handoff becomes a `## Track:` with its own
`<!-- gate: ... -->` marker (BRF-T2-1), so it keeps its readiness inside the merged file. This generator:

1. reads origin/main through the REAL index_state code (collect + build_graph + derive_readiness) and
   splits it into UNITS (a handoff, or one track of an already track-gated handoff);
2. applies all 26 route-1a folds VIRTUALLY, as the BRF-T1-1 fold script does them (source body -> one
   track gated by the source row's Deps mapped through .folded.json and the fold; anchor body untracked,
   inheriting the kept row's Deps; retired ids repointed in every Deps cell), checking 1a neutrality;
3. groups the route-1a end state (64 handoffs) by plan target (`backlog-refactor-plan` targets; the 3
   model-evaluation-queue files are one target: BRF-T7-MEQ) and folds each group: anchor and members alike
   put their body under `## Track: <file stem>` gated by their row's Deps; tracks they already had are
   LIFTED with their markers; a ref to a handoff of the same group becomes `<ROW>#<track>` refs (the row id
   would gate the merged file on its own boxes and never clear); a Deps cell (row ids only) that named a
   member names the kept row (coarser, never looser);
4. proves neutrality per fold, cumulatively: derive_readiness over the virtual graph (per-track gates,
   track refs, task states) must leave every unit with dispatchable work at the same readiness with the
   same blockers (ids mapped through the redirects).

Output style follows fold-list-1a.json. Read-only: nothing in the worktree is written.
"""
import collections, copy, glob, gzip, importlib.util, json, os, re, subprocess, sys
from pathlib import Path

WT = Path(sys.argv[1]).resolve(); OUT = Path(sys.argv[2])
sys.path.insert(0, str(WT / 'scripts/handoffs'))
spec = importlib.util.spec_from_file_location('ist', WT / 'scripts/handoffs/index_state.py')
ist = importlib.util.module_from_spec(spec); spec.loader.exec_module(ist)
brc = ist.brc
D = WT / 'docs/design/backlog-refactor-2026-11'
A = WT / 'handoffs/active'
plan = json.load(open(D / 'backlog-refactor-plan-20261102.json'))
FL = json.load(open(D / 'fold-list-1a.json'))
ref = json.load(gzip.open(D / 'task-readiness-refinements-20261102.json.gz'))
HEAD = subprocess.check_output(['git', '-C', str(WT), 'rev-parse', 'HEAD'], text=True).strip()
ORIGIN = subprocess.check_output(['git', '-C', str(WT), 'merge-base', 'HEAD', 'origin/main'], text=True).strip()
UNT = ist.UNTRACKED

# ---------------------------------------------------------------- 1. origin state, by UNIT
state = ist.collect(); g = ist.build_graph(state)
nodes0 = {n['id']: n for n in g['nodes']}
rows0 = state['rows']
h2n = {n['handoff']: n['id'] for n in g['nodes'] if n['handoff']}
folded0 = json.load(open(A / '.folded.json'))
tgt = lambda v: (v.get('target') if isinstance(v, dict) else v).rsplit('/', 1)[-1]  # noqa: E731


def unit_boxes(path, lo=0, hi=10 ** 9):
    """Dispatchable boxes (line, task id or None) of a file slice: the same classify() index_state uses."""
    out = []
    for ln, st, body, head in brc._boxes(path):
        if st == 'x' or not (lo < ln <= hi):
            continue
        code, _ = brc.classify(path, ln, st, body, head)
        if code == 0:
            m = ist._TASK_ID.match(body.strip())
            out.append((ln, m.group(1) if m else None, body.strip()[:90]))
    return out


units = {}            # uid -> dict(node, name, disp, open, gates, file, boxes)
for nid, n in nodes0.items():
    p = ist.handoff_paths().get(n['handoff'])
    if n.get('tracks'):
        secs = {s['name']: s for s in ist.scan_tracks(p)}
        for t in n['tracks']:
            s = secs.get(t['name'])
            if s:
                bx = unit_boxes(p, s['line'], s['end'])
            else:   # (untracked): boxes outside every section
                inside = [(s_['line'], s_['end']) for s_ in secs.values()]
                bx = [b for b in unit_boxes(p) if not any(lo < b[0] <= hi for lo, hi in inside)]
            units[f'{nid}::{t["name"]}'] = dict(node=nid, name=t['name'], disp=t['dispatchable'], open=t['open'],
                                                gates=t['gates'], file=n['handoff'], boxes=bx,
                                                r0=t['readiness'], b0=t['blocked_by'])
    else:
        units[f'{nid}::{UNT}'] = dict(node=nid, name=UNT, disp=n['dispatchable'], open=n['open'], gates=None,
                                      file=n['handoff'], boxes=unit_boxes(p) if p else [],
                                      r0=n['readiness'], b0=n['blocked_by'])
for u in units.values():
    assert len(u['boxes']) == u['disp'], (u['file'], u['name'], len(u['boxes']), u['disp'])
task_refs_all = {g_ for u in units.values() for g_ in (u['gates'] or ()) if g_ not in rows0}
TASKS0 = ist.task_box_states(task_refs_all) if task_refs_all else {}


# ---------------------------------------------------------------- 2. the virtual graph
class V:
    """Virtual backlog: rows (Deps cells), unit hosting, unit gate markers, redirects."""

    def __init__(self):
        self.host = {uid: u['node'] for uid, u in units.items()}
        self.gates = {uid: (list(u['gates']) if u['gates'] is not None else None) for uid, u in units.items()}
        self.tname = {uid: u['name'] for uid, u in units.items()}           # track name in the host file
        self.deps = {rid: list(r['deps']) for rid, r in rows0.items()}
        self.file = {rid: r['handoff'] for rid, r in rows0.items()}
        self.index = {rid: r['index'] for rid, r in rows0.items()}
        self.R = {}                                                          # retired row -> kept row
        self.tasks = dict(TASKS0)                                            # task id -> {open,...}
        self.task_from = {}                                                  # translated task ref -> row it stood for
        for k, v in folded0['ids'].items():
            if not (isinstance(v, dict) and v.get('retired')):
                self.R[k] = tgt(v)

    def res(self, r):
        seen = set()
        while r in self.R and r not in seen:
            seen.add(r); r = self.R[r]
        return r

    def alive(self):
        return sorted(self.deps)

    def disp(self, rid):
        return sum(units[u]['disp'] for u, h in self.host.items() if h == rid)

    def graph(self):
        ns, es = [], []
        for rid in self.alive():
            us = sorted(u for u, h in self.host.items() if h == rid)
            n = {'id': rid, 'dispatchable': sum(units[u]['disp'] for u in us), 'open': sum(units[u]['open'] for u in us)}
            if any(self.gates[u] is not None for u in us):
                # one track per unit (a unit is a former handoff or a track it already had); several units
                # with gates None (untracked) behave as one: same inherited Deps
                n['tracks'] = [{'name': self.tname[u], 'uid': u, 'gates': self.gates[u], 'dispatchable': units[u]['disp'],
                                'open': units[u]['open']} for u in us]
                assert len({t_['name'] for t_ in n['tracks']}) == len(us), ('duplicate track names', rid)
            ns.append(n)
            for d in self.deps[rid]:
                es.append({'kind': 'dep', 'from': rid, 'to': d})
        counts = ist.derive_readiness(ns, es, self.tasks)
        per = {}
        for n in ns:
            if n.get('tracks'):
                for t in n['tracks']:
                    per[t['uid']] = (t['readiness'], t['blocked_by'])
            else:
                for u, h in self.host.items():
                    if h == n['id']:
                        per[u] = (n['readiness'], n['blocked_by'])
        return per, counts, {n['id']: n['readiness'] for n in ns}

    def norm_blockers(self, b):
        return sorted({self.res(self.task_from.get(x, x)) for x in b})


def neutral(v):
    """Every unit with open (dispatchable) work keeps readiness and its blockers (mapped)."""
    per, counts, nr = v.graph()
    bad = []
    for uid, u in units.items():
        if u['disp'] == 0:
            continue
        r1, b1 = per[uid]
        if (u['r0'], v.norm_blockers(u['b0'])) != (r1, v.norm_blockers(b1)):
            bad.append({'unit': uid, 'before': [u['r0'], u['b0']], 'after': [r1, b1]})
    return bad, counts, nr


V0 = V()
per0, counts0, _ = V0.graph()
assert not neutral(V0)[0], 'virtual model does not reproduce origin readiness'

# ---------------------------------------------------------------- 3. route 1a, virtually (fold.py semantics)
APPLIED_1A = []


def apply_1a(v, e):
    keep = e['anchor_row_kept']
    srcs = [s.split('/')[-1] for s in e['sources']]
    live = [s for s in srcs if s in h2n]
    if not live and all(s in folded0['files'] for s in srcs):
        APPLIED_1A.append(e['order'])          # this fold already landed on origin_main: its tracks are real
        return
    assert len(live) == len(srcs), f"fold {e['order']} half-applied on origin_main: {sorted(set(srcs) - set(live))}"
    srows = [h2n[s] for s in srcs]
    idmap = dict(e['redirects']['rows'])
    members = set(srows) | {keep}
    for s, rid in zip(srcs, srows):
        ds = []
        for d in v.deps[rid]:
            d = idmap.get(v.res(d), v.res(d))
            if d not in members and d not in ds:
                ds.append(d)
        for u, h in list(v.host.items()):
            if h == rid:
                assert v.gates[u] is None, f'1a source {s} already has tracks; fold.py would flatten them'
                v.host[u] = keep; v.gates[u] = ds; v.tname[u] = s[:-3]
    for rid in srows:
        del v.deps[rid]; v.R[rid] = keep
    dest = e['destination'].split('/')[-1]
    v.file[keep] = dest
    for rid in v.alive():
        nd = []
        for d in v.deps[rid]:
            d = v.res(d)
            if d != rid and d not in nd:
                nd.append(d)
        v.deps[rid] = nd


V1 = copy.deepcopy(V0)
for e in FL['folds']:
    apply_1a(V1, e)
    bad, c1a, _ = neutral(V1)
    assert not bad, (e['order'], bad[:3])
end1a = V1.alive()
_, _, per0_1a = V1.graph()
print('route-1a end state:', len(end1a), 'handoffs', c1a, file=sys.stderr)

# ---------------------------------------------------------------- 4. route-1b groups: one per plan target
pl = {h['handoff']: h for h in plan['handoffs']}
tmeta = {t['target']: t for t in plan['targets']}
meq = plan['model_evaluation_queue']
tmeta.setdefault(meq['target'], {'target': meq['target'], 'owner_index': meq['owner_index'],
                                 'priority_rank_after': meq['priority_rank_after']})
fold_of = {}   # file at origin -> 1a fold entry it belongs to (anchor or source)
for e in FL['folds']:
    for f in [e['anchor']] + e['sources']:
        fold_of[f.split('/')[-1]] = e
meq_files = set(meq['whole_handoffs']) | {meq['target']}


def target_of(rid):
    """Plan target of a route-1a end node: the 1a fold's plan target, else the plan row of its own file."""
    f0 = rows0[rid]['handoff']
    if f0 in fold_of:
        return fold_of[f0]['plan_target'], 'fold-list-1a plan_target'
    if f0 in meq_files:
        return meq['target'], 'model_evaluation_queue (D2, BRF-T7-MEQ)'
    if f0 in pl:
        return (pl[f0]['target'] or f0), f"plan action {pl[f0]['action']}"
    return None, 'not in the plan (new since the pin): stays a singleton'


grp = collections.defaultdict(list); why = {}
for rid in end1a:
    t, w = target_of(rid)
    why[rid] = w
    grp[t or V1.file[rid]].append(rid)


def pref(t):
    """Anchor preference inside a group: the file already named as the target, the plan's rename/keep member,
    then the most dispatchable work."""
    def key(rid):
        f, f0 = V1.file[rid], rows0[rid]['handoff']
        act = (pl.get(f0) or {}).get('action', '')
        return (f == t, f0 == t, act in ('rename-to-target', 'rename-to-target+split', 'keep-as-target', 'keep'),
                V1.disp(rid), rid)
    return key


rank = lambda t: (tmeta.get(t, {}).get('priority_rank_after', 99), t)  # noqa: E731
folds = [(t, max(mem, key=pref(t)), sorted(mem)) for t, mem in sorted(grp.items(), key=lambda x: rank(x[0])) if len(mem) > 1]
singles = sorted(t for t, mem in grp.items() if len(mem) == 1)

# ---------------------------------------------------------------- 5. apply 1b folds cumulatively, proving neutrality
CF = Path('/mnt/raid0/llm/tmp/compute-flags')
try:
    hs = json.load(open(CF / 'handoff-sessions.json')).get('sessions', {})
except (OSError, ValueError):
    hs = {}
ready = []
for f in glob.glob(str(CF / 'ready/*.json')):
    try:
        d = json.load(open(f))
    except (OSError, ValueError):
        continue
    if isinstance(d, dict) and isinstance(d.get('handoff_task'), str):
        ready.append((os.path.basename(f), d['handoff_task']))
curated = (WT / 'scripts/handoffs/backlog_priority_curated.json').read_text()
refs_by_file = collections.defaultdict(list)
for r in ref['tasks']:
    refs_by_file[r['src'].split(':')[0].split('/')[-1]].append(r)


def linking(fn):
    out = subprocess.run(['git', '-C', str(WT), 'grep', '-l', '-F', f'handoffs/active/{fn}', '--', 'handoffs', 'docs', 'wiki',
                          'scripts', 'agents', '.claude', 'dashboard'], capture_output=True, text=True).stdout.split()
    out2 = subprocess.run(['git', '-C', str(WT), 'grep', '-l', '-F', f']({fn}', '--', 'handoffs/active'],
                          capture_output=True, text=True).stdout.split()
    return len(set(out) | set(out2))


def is_row_ref(v, x):
    return x in v.deps or x in v.R


V2 = copy.deepcopy(V1)
V2.track_from = {}            # `<ROW>#<track>` ref -> the route-1a row whose unit it names (for the blocker check)
_norm = V2.norm_blockers
entries, unproven = [], []
n_nodes = len(V2.alive())
for k, (t, anc, mem) in enumerate(folds, 1):
    others = [r for r in mem if r != anc]
    pre_disp = {r: V2.disp(r) for r in V2.alive()}
    pre_units = {r: sorted(u for u, h in V2.host.items() if h == r) for r in mem}
    files_before = {r: V2.file[r] for r in mem}
    member_set = set(mem)
    # every unit of the group becomes a marked track: a member's (and the anchor's) untracked body takes
    # `## Track: <its file stem>`; a track it already had keeps its name
    newname = {u: (files_before[r][:-3] if V2.gates[u] is None else V2.tname[u]) for r in mem for u in pre_units[r]}
    assert len(set(newname.values())) == len(newname), ('track name clash', t)
    drops, coarsened, rewritten = [], [], []

    def track_refs(S):
        return [f'{anc}#{newname[u]}' for u in pre_units[S] if units[u]['open'] > 0]

    def map_ref(ref_, where):
        """A gate-marker ref after this fold (markers accept row ids, `<ROW>#<track>` and task ids)."""
        if '#' in ref_:
            rid, _, nm = ref_.partition('#')
            return [f'{anc}#{nm}'] if rid in member_set else [ref_]
        if not is_row_ref(V2, ref_):
            return [ref_]                                                    # a task id
        r0_ = V2.res(ref_)
        if r0_ not in member_set:
            return [r0_]
        tr = track_refs(r0_)
        for x in tr:
            V2.track_from[x] = r0_
        if not tr:
            drops.append({'where': where, 'ref': ref_, 'reason': f'{r0_} has no open box (inert)'})
        rewritten.append({'where': where, 'ref': ref_, 'to': tr})
        return tr

    def remap(refs, where):
        out_ = []
        for d in refs:
            for x in map_ref(d, where):
                if x not in out_:
                    out_.append(x)
        return out_

    # (a) the group's units: bodies get the member row's Deps as their marker; lifted tracks keep theirs, mapped
    for r in mem:
        for u in pre_units[r]:
            where = f'{t}#{newname[u]}'
            V2.gates[u] = remap(V2.deps[r] if V2.gates[u] is None else V2.gates[u], where)
            V2.tname[u] = newname[u]; V2.host[u] = anc
    # (b) gate markers elsewhere that name a member (by row or by track)
    for u, h in V2.host.items():
        if h == anc or V2.gates[u] is None:
            continue
        if any((x.partition('#')[0] if '#' in x else (V2.res(x) if is_row_ref(V2, x) else None)) in member_set for x in V2.gates[u]):
            V2.gates[u] = remap(V2.gates[u], f'{V2.file[h]}#{V2.tname[u]}')
    # (c) Deps cells: a row id only, so a ref to a member becomes the kept row (coarser, never looser);
    # refused when the member had no dispatchable work but the merged row has (that would flip)
    for rid in V2.alive():
        if rid in member_set:
            continue
        nd = []
        for d in V2.deps[rid]:
            r0_ = V2.res(d)
            if r0_ in member_set:
                if pre_disp[r0_] == 0 and sum(pre_disp[x] for x in mem) > 0:
                    drops.append({'where': f'row {rid} Deps', 'ref': d, 'reason': f'{r0_} had no dispatchable work (would flip)'}); continue
                if r0_ != anc or d != anc:
                    coarsened.append({'row': rid, 'ref': d, 'to': anc})
                r0_ = anc
            if r0_ != rid and r0_ not in nd:
                nd.append(r0_)
        V2.deps[rid] = nd
    keep_deps = []
    for d in V2.deps[anc]:
        r0_ = V2.res(d)
        if r0_ not in member_set and r0_ not in keep_deps:
            keep_deps.append(r0_)
    V2.deps[anc] = keep_deps
    for r in others:
        del V2.deps[r]; V2.R[r] = anc
    V2.file[anc] = t
    V2.norm_blockers = lambda b, _v=V2: sorted({_v.res(_v.track_from.get(x, x.partition('#')[0] if '#' in x else x)) for x in b})
    bad, counts, nr = neutral(V2)
    if bad:
        unproven.append({'fold': k, 'target': t, 'flips': bad})
    n_nodes -= len(others)
    # ---- entry
    per, _, _ = V2.graph()
    tracks = []
    for r in [anc] + others:
        for u in pre_units[r]:
            tracks.append({'track': newname[u], 'from_file': files_before[r], 'from_row': r,
                           'kind': ('anchor body -> track' if u.endswith('::' + UNT) and r == anc and units[u]['node'] == r
                                    else 'member body -> track' if V1.gates[u] is None
                                    else 'lifted track (marker kept, refs mapped)'),
                           'origin_file': units[u]['file'],
                           'gate_marker': f"<!-- gate: {', '.join(V2.gates[u]) if V2.gates[u] else 'none'} -->",
                           'dispatchable': units[u]['disp'], 'open': units[u]['open'],
                           'readiness_before': units[u]['r0'], 'readiness_after': per[u][0]})
    anchor_file = files_before[anc]
    redirects_files = {files_before[r]: f'{t}#track:{files_before[r][:-3]}' for r in mem if files_before[r] != t}
    for r in mem:
        for u in pre_units[r]:
            if V1.gates[u] is not None and units[u]['file'] != files_before[r]:
                redirects_files.setdefault(units[u]['file'], f'{t}#track:{newname[u]}')
    dfiles = set(files_before.values())
    sess = [{'slug': s, 'handoff_from': v.get('handoff'), 'handoff_to': f'handoffs/active/{t}'}
            for s, v in sorted(hs.items()) if isinstance(v, dict)
            and (v.get('handoff') or '').split('/')[-1] in dfiles and (v.get('handoff') or '').split('/')[-1] != t]
    rowf = []
    for name, ht in sorted(ready):
        mm = re.match(r'^(handoffs/active/)?([A-Za-z0-9._-]+\.md)(.*)$', ht.strip())
        if mm and mm.group(2) in dfiles and mm.group(2) != t:
            rowf.append({'spec': name, 'from': ht, 'to': f'handoffs/active/{t}{mm.group(3)}'})
    ofiles = sorted({units[u]['file'] for r in mem for u in pre_units[r]})
    pend = sum(1 for f0 in ofiles for r_ in refs_by_file[f0] if r_['decision_kind'] == 'pending-choice')
    owner = tmeta.get(t, {}).get('owner_index')
    entries.append({
        'order': k, 'box': f'BRF-T7-F{k}' + (' (BRF-T7-MEQ)' if t == meq['target'] else ''),
        'plan_target': t, 'destination': f'handoffs/active/{t}', 'destination_is_rename': anchor_file != t,
        'anchor': f'handoffs/active/{anchor_file}', 'anchor_row_kept': anc,
        'members': [{'row': r, 'file_after_1a': files_before[r], 'readiness_after_1a': per0_1a[r],
                     'dispatchable': pre_disp[r], 'grouped_by': why[r]} for r in [anc] + others],
        'sources': [f'handoffs/active/{files_before[r]}' for r in others],
        'moves': [f'git mv handoffs/active/{files_before[r]} handoffs/completed/{files_before[r]}' for r in others]
                 + ([f'git mv handoffs/active/{anchor_file} handoffs/active/{t}'] if anchor_file != t else []),
        'procedure': ('anchor: keep its preamble (H1 and header lines up to the first `##` heading) untracked; from that '
                      'heading to its first existing `## Track:` goes under `## Track: <anchor stem>` (headings demoted two '
                      'levels outside fences). Each other member: the same for its whole body before its first `## Track:`, '
                      'appended as `## Track: <member stem>`. Every `## Track:` a member or the anchor already carries is '
                      'LIFTED verbatim (never demoted) after its owner, with the marker below. Stubs go to completed/ as in route 1a.'),
        'tracks': tracks,
        'gate_ref_rewrites': {'track_refs': rewritten, 'inert_refs_dropped': drops, 'deps_cells_coarsened_to_kept_row': coarsened},
        'index_row_changes': {'delete_rows': [{'row': r, 'index': V2.index[r]} for r in others],
                              'keep_row': {'row': anc, 'index': V2.index[anc], 'plan_owner_index': owner,
                                           'move_to_owner_index': bool(owner and owner != V2.index[anc]),
                                           'handoff_cell': t, 'deps_after': keep_deps},
                              'repoint_deps_in_rows': sorted({c['row'] for c in coarsened}),
                              'curated_priority_rekey_candidates': [r for r in others if f'"{r}' in curated],
                              'repoint_reason_trailers': [f'Repoint-Reason: {r}: folded into {anc} ({t}) — route 1b, D1/D5' for r in others]},
        'redirects': {'rows': {r: anc for r in others}, 'files': redirects_files},
        'link_repoint_files': {f: linking(f) for f in [files_before[r] for r in others] + ([anchor_file] if anchor_file != t else [])},
        'session_slug_rewrites': sess, 'rowflow_handoff_task_rewrites': rowf,
        'decision_package_D7': {'pending_choices_in_manifest': pend},
        'expected_gate': {
            'per_track_readiness_diff': bad, 'neutral': not bad,
            'readiness_of_node_after': nr[anc],
            'graph_after': {'nodes': n_nodes, 'readiness_counts': counts},
            'dispatchable': V2.disp(anc),
            'commands': ['python3 scripts/handoffs/index_state.py', 'python3 scripts/handoffs/index_state.py --check',
                         'per-track readiness equality: each track == its former handoff (blockers mapped through .folded.json)',
                         'python3 scripts/handoffs/task_lint.py migrate <touched>', 'python3 scripts/handoffs/belief_capture_check.py']}})

batches = [{'batch': i // 8 + 1, 'orders': [e['order'] for e in entries[i:i + 8]]} for i in range(0, len(entries), 8)]
end1b = V2.alive()
_, c1b, _ = V2.graph()
TOOLING = subprocess.check_output(['git', '-C', str(WT), 'log', '--reverse', '--format=%s', f'{ORIGIN}..HEAD'], text=True).splitlines()
out = {'schema': 'brf-fold-list-1b.v1', 'generated': '2026-11-02', 'origin_main': ORIGIN,
       'tooling_on_top_of_origin_main': TOOLING,
       'base': 'route-1a END state: the 26 folds of fold-list-1a.json applied virtually on origin_main (BRF-T1-1 fold.py semantics)',
       'route_1a_folds_already_on_origin_main': APPLIED_1A,
       'rule': ('route 1b (D1): one group per plan target (backlog-refactor-plan targets; the 3 model-evaluation-queue files '
                'are one target, BRF-T7-MEQ). Readiness may differ inside a group because every former handoff becomes a '
                'marked track: its body takes the member row Deps as its gate marker and the tracks it already had keep '
                'theirs. A ref to a handoff of the same group becomes `<ROW>#<track>` refs (index_state BRF-T7-1 '
                'prerequisite); a Deps cell ref to a member becomes the kept row. Proof: the real index_state '
                'derive_readiness (per-track gates, track refs, task states) over the virtual graph, cumulatively in list '
                'order: every unit with dispatchable work (a former handoff, or a track it already had) keeps readiness and '
                'blockers (mapped through the redirects).'),
       'counts': {'origin_nodes': len(nodes0), 'origin_readiness': counts0,
                  'after_1a_nodes': len(end1a), 'after_1a_readiness': c1a,
                  'folds': len(entries), 'batches': len(batches), 'sources_folded': sum(len(e['sources']) for e in entries),
                  'after_1b_nodes': len(end1b), 'after_1b_readiness': c1b,
                  'after_1b_excluding_backlog_refactor': len([r for r in end1b if V2.file[r] != 'backlog-refactor-2026-11.md']),
                  'singleton_targets': singles, 'groups': len(grp),
                  'track_refs_written': sum(len(e['gate_ref_rewrites']['track_refs']) for e in entries),
                  'deps_cells_coarsened': sum(len(e['gate_ref_rewrites']['deps_cells_coarsened_to_kept_row']) for e in entries),
                  'inert_refs_dropped': sum(len(e['gate_ref_rewrites']['inert_refs_dropped']) for e in entries),
                  'unproven_folds': len(unproven)},
       'unproven': unproven,
       'after_1b_handoffs': {rid: V2.file[rid] for rid in end1b},
       'batches': batches, 'folds': entries}
json.dump(out, open(OUT, 'w'), indent=1, ensure_ascii=False)
print(json.dumps(out['counts'], indent=1))
print('size', os.path.getsize(OUT))
