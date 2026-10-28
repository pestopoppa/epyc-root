#!/usr/bin/env python3
"""backlog_priority.py - regenerate handoffs/active/backlog-priority.json (the graph's priority data).

    python3 scripts/handoffs/backlog_priority.py            # write handoffs/active/backlog-priority.json
    python3 scripts/handoffs/backlog_priority.py --check    # drift / staleness; non-zero on failure, writes nothing
    python3 scripts/handoffs/backlog_priority.py --out X    # write elsewhere (also --md FILE for the full ranked list)

Bands first (LOOP-CONTRACT, operator-adopted 2026-10-28): every row carries `kind` = inference-prep |
inference-ready | non-inference and ranks in that order. inference-prep (T0) = the curated `inference_prep`
snapshot of FILLERS.md BACKLOG rows blocked on a harness fix or a missing launcher (`--seed-prep` refreshes it);
inference-ready = unheld inference items (T4-T6); everything else is non-inference.

Ordering method within the bands (operator, 2026-10-24), applied to every open `- [ ]` box under handoffs/active + blocked:

1. INFERENCE items are classed with the inference-backlog-scheduling model: live (running / booked /
   armed) > ready and decision-bearing > routine; ROI = decision value per compute-hour; operator holds
   (DS41-1017, HIL-6, parked / frozen, pending operator decisions, external blockers) push items to T7
   with the blocker named.
2. A NON-INFERENCE task that gates an inference task inherits its score and ranks just above it.
3. NON-INFERENCE tasks blocked by nothing are the top tier: T1 if they gate compute, T2 otherwise.
4. Everything else blocked follows its blockers (T3 inherits, T7 held / blocked).
Row priority = its best open item; score = rank percentile over rows with open work.

Inputs: the repo (boxes, index rows, Deps edges) plus `backlog_priority_curated.json` next to this file:
hand-scored entries (the decision-bearing and live-compute items), row weights, holds, subagent briefs and
`done` completions that main has not ticked yet. LIVE COMPUTE STATE (what is running / armed on the
calendar) is NOT read from the host: it is recorded in the curated table, so refresh `cls: live` entries
(and `done`) there when the calendar moves, then regenerate. Everything not curated is scored by keyword
heuristics (kind) and the row weight; those are guesses, which is why the file is advisory ordering only.

`--check` exits 1 when the file is missing / invalid JSON, older than STALE_DAYS, lacks an open row, or
when the regenerated tiers differ from the committed ones for more than DRIFT_FRACTION of rows.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
OUT_DEFAULT = REPO_ROOT / "handoffs" / "active" / "backlog-priority.json"
CURATED_PATH = HERE / "backlog_priority_curated.json"
STALE_DAYS = 14
DRIFT_FRACTION = 0.15

FILLERS_DEFAULT = Path("/mnt/raid0/llm/tmp/compute-flags/FILLERS.md")
GRANTS_DIR = Path("/mnt/raid0/llm/tmp/compute-flags/grants")
PREP_BLOCKER_RX = re.compile(r'(harness fix|missing launcher)', re.I)
# Row/item lane (LOOP-CONTRACT 2026-10-28): emitted as `kind` on every row; prep > ready > non-inference.
LANES = ("inference-prep", "inference-ready", "non-inference")

TIER_NAME = {0: "T0 inference-prep (claimable: repair harness / write launcher, smoke, READY manifest)",
             1: "T1 non-inference, unblocked, unblocks compute", 2: "T2 non-inference, unblocked, other",
             3: "T3 non-inference, blocked, inherits (just above what it gates)",
             4: "T4 inference LIVE (running / booked / armed)", 5: "T5 inference ready, decision-bearing",
             6: "T6 inference routine / re-measurement", 7: "T7 held or blocked (named blocker)"}
TIER_SHORT = {"0": "T0 inference-prep", "1": "T1 non-inference, unblocked, unblocks compute", "2": "T2 non-inference, unblocked",
              "3": "T3 non-inference, blocked (inherits)", "4": "T4 inference live", "5": "T5 inference ready",
              "6": "T6 inference routine", "7": "T7 held / blocked"}


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- kind heuristics
VERB_I = r'^(run|re-?run|measure|re-?measure|replay|sweep|confirm|profile|bench|a/b|collect|execute|load|compare|re-?baseline|validate on|test on|time|probe)\b'
VERB_N = r'^(add|wire|write|build|implement|fix|fold|land|port|extend|define|persist|record|document|update|decide|specify|prepare|create|make|draft|tick|remove|delete|clean|close|file|report|move|migrate|refactor|install|apply|ratify|sign|approve|design|enumerate|resolve|audit|screen|review|read|check|investigate|explain|derive|emit|publish|merge|re-?resolve|catalog|annotate|turn|teach|parameterize|specif)\b'
INF_RX = re.compile(r'llama-bench|\bABA\b|A/B|\bsweep\b|inference window|compute window|quiet (window|host)|GPU window|CPU window|on a quarter|whole[- ]host|replicat|soak|overnight|\bPPL\b|perplexity|tok/s|\bwindow\b.{0,40}(run|bench)|N=\d+|\bn=\d+|requests?\b.{0,30}(run|measure)', re.I)
NOINF_RX = re.compile(r'zero[- ]inference|no inference|model-free|\boffline\b|read-only|no GPU|desk check|docs?-only|documentation|no model', re.I)
INF2_RX = re.compile(r'clean window|exclusive claim|host-quiet|canonical bench|never run|not yet run|re-?run|inference window|needs? an? (inference|GPU|CPU|compute|quiet) (window|slot)|quiet window|GPU window|CPU window|on a quarter|measurement window|timing window', re.I)
OP_RX = re.compile(r'operator (decision|action|sign|ratif|approv|go|ack|run)|human sign-off|\bratify\b|OPERATOR|awaiting operator|PENDING OPERATOR|USER APPROVAL', re.I)
BLK_RX = re.compile(r'(blocked (on|by)|\bBLOCKED\b|awaiting|gated (on|by)|needs? (an? )?operator|until the operator|pending (operator|the operator))', re.I)
HOLD_RX = re.compile(r'DO-NOT-DISPATCH|❄ FROZEN|\bFROZEN\b|\bPARKED\b|HELD\b|DS41-1017.{0,80}(hold|held)|HIL-6 (pilot|deferred)', re.I)
DS41_RX = re.compile(r'DS41-?1017|DS41[- ]class|DeepSeek-V4\.1', re.I)
N1_RX = re.compile(r'run\b|gate|A/B|window|measure|timing|record|arm\b|trial|replay|sweep|attribution|floor|keep|decision|bundle|premeasure|stack-change|promotion|champion|candidate|fold', re.I)
OWN = [(r'workspace-f8|\bf8\b', 'f8'), (r'3c4ca599', '3c4ca599'), (r'workspace-58|\bws58\b', 'workspace-58'),
       (r'workspace-7b|\b7b\b', 'workspace-7b'), (r'workspace-ec|\bec\b', 'workspace-ec'), (r'workspace-sec', 'workspace-sec')]


def _clean(t: str) -> str:
    t = re.sub(r'^\W+', '', t)
    if re.match(r'^[A-Za-z0-9_.\-+/]{2,40}\s+[—–-]', t):
        t = re.sub(r'^[A-Za-z0-9_.\-+/() ,]{1,40}?\s+[—–-]+\s+', '', t, count=1)
    return t


def auto_kind(text: str) -> str:
    t = text.replace('**', '')
    body = _clean(t).lower()
    if OP_RX.search(t[:240]) and not re.search(r'\boperator[- ]?(approved|pre-approved|ruling|chose|directed)', t[:240], re.I):
        return 'O'
    if NOINF_RX.search(t[:400]):
        return 'N'
    if re.match(VERB_I, body):
        return 'I'
    if INF_RX.search(t[:420]) or INF2_RX.search(t[:420]):
        return 'I'
    return 'N'


def size_of(full: str) -> str:
    m = re.search(r'~\s*(\d+(?:\.\d+)?)\s*(h|hr|hours|min|m|d)\b', full[:900])
    if m:
        v = float(m.group(1)); u = m.group(2)
        hrs = v if u.startswith('h') else (v / 60 if u in ('min', 'm') else v * 24)
        return f'~{v:g} {u}' + (' (L)' if hrs > 4 else '')
    n = len(full)
    return 'S' if n < 350 else ('M' if n < 1000 else 'L')


def _blame_dates(path: Path) -> dict[int, str]:
    try:
        r = subprocess.run(['git', '-C', str(REPO_ROOT), 'blame', '--line-porcelain', 'HEAD', '--', str(path.relative_to(REPO_ROOT))],
                           capture_output=True, text=True, errors='replace', timeout=120).stdout
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return {}
    times, ln = {}, 0
    for l in r.splitlines():
        m = re.match(r'^[0-9a-f]{40} \d+ (\d+)', l)
        if m: ln = int(m.group(1))
        elif l.startswith('author-time '):
            times[ln] = datetime.datetime.fromtimestamp(int(l.split()[1]), datetime.timezone.utc).strftime('%Y-%m-%d')
    return times


def collect_boxes(index_state) -> tuple[dict, list[dict]]:
    """(state, boxes) for every open `- [ ]` box in handoffs/active + blocked."""
    brc = index_state.brc
    state = index_state.collect()
    paths = index_state.handoff_paths()
    h2r: dict = {}
    for rid, r in state['rows'].items():
        h2r.setdefault(r.get('handoff'), []).append(rid)
    boxes = []
    for h, p in paths.items():
        lines = p.read_text(encoding='utf-8', errors='replace').splitlines()
        dates = None
        for ln, st, body, head in brc._boxes(p):
            if st != 'x' and st != 'X':
                if dates is None:
                    dates = _blame_dates(p)
                code, reasons = brc.classify(p, ln, st, body, head)
                full = [lines[ln - 1]]
                for l in lines[ln:ln + 30]:
                    if re.match(r'\s*[-*] \[[ xX]\]', l) or l.startswith('#'):
                        break
                    full.append(l)
                boxes.append(dict(handoff=h, file=str(p.relative_to(REPO_ROOT)), line=ln, text=body, head=head, code=code,
                                  reasons=reasons, rows=h2r.get(h, []), touched=dates.get(ln),
                                  full=' '.join(x.strip() for x in full)[:1500]))
    return state, boxes


# ---------------------------------------------------------------- inference-prep seed
def seed_prep(fillers: Path, nodes: dict, grants: Path = GRANTS_DIR, aliases: dict | None = None) -> list[dict]:
    """inference-prep seeds from FILLERS.md: BACKLOG rows whose FIRST `blocker=` is a harness fix or a missing
    launcher, minus rows already `.complete` in grants/ or marked superseded. Each maps to the index row whose
    handoff file (or row id) the FILLERS row names; unmapped rows keep row=''. Host state, so it is snapshotted
    into the curated table (`--seed-prep`), never read at build time."""
    by_handoff: dict = {}
    for nid, n in nodes.items():
        by_handoff.setdefault(Path(n.get('handoff') or '').name, []).append(nid)
    id_rx = re.compile(r'\b(' + '|'.join(sorted(map(re.escape, nodes), key=len, reverse=True)) + r')\b') if nodes else None
    out = []
    for l in fillers.read_text(encoding='utf-8', errors='replace').splitlines():
        c = l.split('|')
        if len(c) <= 18 or not c[8].strip().startswith('BACKLOG'):
            continue
        fid = c[1].strip()
        b = re.findall(r'blocker=\s*([^;|]*)', c[18])
        if not fid or not b or not PREP_BLOCKER_RX.match(b[0].strip()):
            continue
        if (grants / f'{fid}.complete').exists() or re.search(r'superseded|RETIRED|duplicate', c[18], re.I):
            continue
        row, how = '', ''
        for h in re.findall(r'([A-Za-z0-9_.\-]+\.md)\b', l):
            if by_handoff.get(h):
                row, how = sorted(by_handoff[h])[0], f'handoff {h}'
                break
        if not row and id_rx is not None:
            m = id_rx.search(l)
            if m:
                row, how = m.group(1), f'row id {m.group(1)} named'
        if not row:
            for rx, rid in (aliases or {}).items():
                if not rx.startswith('_') and rid in nodes and re.search(rx, fid, re.I):
                    row, how = rid, f'filler-id alias /{rx}/'
                    break
        out.append(dict(filler=fid, row=row, map=how or 'unmapped', owner=c[2].strip()[:60],
                        blocker=b[0].strip()[:140], cls=c[9].strip()[:40], decision=c[15].strip()[:160]))
    return sorted(out, key=lambda e: e['filler'])


# ---------------------------------------------------------------- the build
def build(curated: dict | None = None, index_state=None, state=None, boxes=None) -> dict:
    curated = curated or json.loads(CURATED_PATH.read_text(encoding='utf-8'))
    index_state = index_state or _load('index_state', 'scripts/handoffs/index_state.py')
    if state is None or boxes is None:
        state, boxes = collect_boxes(index_state)
    graph = index_state.build_graph(state)
    NODES = {n['id']: n for n in graph['nodes']}
    EDGES = [e for e in graph['edges'] if e['kind'] == 'dep']
    W = curated.get('row_weights', {})
    HOLD = curated.get('holds', {})
    PARK = curated.get('park', {})
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')

    items: dict[str, dict] = {}
    byloc: dict = {}
    curkey: dict = {}
    unmatched, done_list = [], []

    def mk(b, **kw):
        rowid = b['rows'][0] if b['rows'] else b['handoff']
        key = f"{rowid}@{Path(b['file']).name}:{b['line'] or 'new'}"
        it = dict(key=key, row=rowid, rows=b['rows'], file=b['file'], line=b['line'], head=b['head'],
                  text=b['text'][:260].replace('**', ''), full=b['full'], touched=b['touched'], code=b['code'],
                  reasons=b['reasons'], source='auto', kind='N', cls='N', s=0.0, size=size_of(b['full']), unblocks='',
                  blocker='', why='', owner='', filler='', before='', synthetic=False, in_progress=False, done='')
        it.update(kw)
        return it

    def find_box(rowid, tok):
        rx = re.compile(re.escape(tok))
        for b in boxes:
            if rowid in b['rows'] and rx.search(b['text'].replace('**', '')[:110]):
                return b
        return None

    # curated entries
    for c in curated['entries']:
        ckey = f"{c['row']}:{c['tok']}"
        if c.get('new'):
            b = dict(rows=[c['row']], file='handoffs/active/' + c['file'], line=0, text=c['title'], full=c['title'] + ' ' + c.get('why', ''),
                     code=0, reasons=[], touched=None, head='', handoff=c['file'])
            syn = False
            it = mk(b)
            it['key'] += ':' + re.sub(r'\W+', '-', c['tok'])[:30]
            it['synthetic'] = True
        else:
            b = find_box(c['row'], c['tok'])
            if b is None:
                unmatched.append((c['row'], c['tok']))           # box ticked / moved: fine, reported only
                continue
            loc = (b['file'], b['line'])
            syn = loc in byloc
            it = mk(b)
            if syn:
                it['key'] += '~fix'; it['synthetic'] = True; it['text'] = '(derived task) ' + c.get('why', '')[:200]
        kind, cls = c['kind'], c['cls']
        it.update(source='curated', kind=kind, cls=cls, s=c['s'], size=c.get('size') or it['size'], unblocks=c.get('unblocks', ''),
                  blocker=c.get('blocker', ''), why=c.get('why', ''), owner=c.get('owner', ''), filler=c.get('filler', ''),
                  before=c.get('before', ''), in_progress=bool(c.get('in_progress')), done=c.get('done', ''))
        if it['done']:
            done_list.append(it)
            if not c.get('new') and not syn:
                byloc[(b['file'], b['line'])] = it['key']        # an auto item must not re-create it
            continue
        items[it['key']] = it
        if not c.get('new') and not syn:
            byloc[(b['file'], b['line'])] = it['key']
            curkey[ckey] = it['key']
        else:
            curkey.setdefault(ckey, it['key'])

    # auto items
    rec_cut = '2026-10-21'
    for b in boxes:
        if (b['file'], b['line']) in byloc:
            continue
        rowid = b['rows'][0] if b['rows'] else b['handoff']
        w = W.get(rowid, .2)
        rhold = HOLD.get(rowid)
        k = auto_kind(b['text'])
        t = b['text']
        recent = bool(b['touched'] and b['touched'] >= rec_cut)
        bonus = (.12 if recent else (.04 if b['touched'] and b['touched'] >= '2026-09-24' else 0)) + (.06 if re.search(r'PRIORITY|NEXT|READY|armed|ARMED', t[:200]) else 0)
        s = round(min(.6, w * .7 + bonus), 3)
        cls, blocker = 'N', ''
        if b['code'] == 2:
            cls = 'U'; blocker = (b['reasons'][0] if b['reasons'] else 'undispatchable')[:140]; s = round(w * .3, 3)
        elif rhold or (PARK.get(rowid) and re.search(PARK[rowid], t[:300])) or HOLD_RX.search(t[:300]) or \
                (DS41_RX.search(t[:300]) and not re.search(r'noise floor', t[:300], re.I) and k == 'I'):
            cls = 'H'; blocker = rhold or 'text names a hold / freeze / park'
        elif BLK_RX.search(t[:200]):
            cls = 'NB' if k != 'I' else 'H'; blocker = 'text names a blocker: ' + BLK_RX.search(t[:200]).group(0)
            if k == 'O': cls = 'N'
        if k == 'I' and cls == 'N':
            cls = 'ready' if (w >= .5 and recent) else 'routine'
        it = mk(b, kind=k, cls=cls, s=s, blocker=blocker)
        items[it['key']] = it
        byloc[(b['file'], b['line'])] = it['key']

    # inference-prep items (curated snapshot of FILLERS.md, see seed_prep): kind 'P', ranked above everything
    prep_list = []
    for e in curated.get('inference_prep', []):
        rowid = e.get('row') or ''
        h = NODES.get(rowid, {}).get('handoff', '') if rowid else ''
        b = dict(rows=[rowid] if rowid in NODES else [], handoff=f"FILLERS:{e['filler']}",
                 file=('handoffs/active/' + Path(h).name) if h else str(FILLERS_DEFAULT), line=0,
                 text=f"inference-prep {e['filler']}: {e['blocker']}", full=e.get('decision', ''), code=0, reasons=[],
                 touched=None, head='')
        w = W.get(rowid, .2)
        s = round(min(.99, .5 + .4 * w + (.05 if re.match(r'decision|block-timing', e.get('cls', '')) or e.get('decision') else 0)), 3)
        it = mk(b, kind='P', cls='prep', s=s, source='curated-prep', filler=e['filler'], owner=e.get('owner', ''),
                why=f"FILLERS BACKLOG blocker={e['blocker'][:80]}; mapped by {e.get('map', 'unmapped')}")
        it['key'] = f"{it['row']}@prep:{e['filler']}"
        it['synthetic'] = True
        items[it['key']] = it
        prep_list.append(it)

    # row-dep inheritance (coarse): one best-matching auto box per dependency row
    rowbest = collections.defaultdict(list)
    for it in items.values():
        rowbest[it['row']].append(it)
    dep_rows = collections.defaultdict(set)
    for e in EDGES:
        dep_rows[e['to']].add(e['from'])
    for D_, Rs in dep_rows.items():
        if D_ not in NODES or NODES[D_]['open'] == 0:
            continue
        best_inf = None
        for r_ in Rs:
            if HOLD.get(r_) or NODES.get(r_, {}).get('open', 0) == 0:
                continue
            for it in rowbest.get(r_, []):
                if it['kind'] == 'I' and it['cls'] in ('live', 'ready') and (best_inf is None or it['s'] > best_inf['s']):
                    best_inf = it
        if not best_inf:
            continue
        cands = [i for i in rowbest.get(D_, []) if i['kind'] == 'N' and i['cls'] == 'N' and not i['before']
                 and not i['synthetic'] and i['source'] == 'auto']
        if not cands:
            continue
        na = set(re.findall(r'[A-Za-z][A-Za-z0-9\-.]{3,}', NODES[D_].get('next_action', '').lower()))

        def ov(i):
            tw = set(re.findall(r'[A-Za-z][A-Za-z0-9\-.]{3,}', i['text'].lower()))
            return len(na & tw) + i['s']
        top = max(cands, key=ov)
        if ov(top) - top['s'] < 1.5:
            continue                                            # no box matches the row's own next step: do not guess
        top['before'] = '@' + best_inf['key']
        top['s'] = max(top['s'], round(best_inf['s'] * .6, 3))
        top['unblocks'] = f"row-dep (coarse Deps edge {', '.join(sorted(Rs))}) -> {best_inf['row']} {best_inf['text'][:50]}"

    def resolve(ref):
        if not ref:
            return None
        if ref.startswith('@'):
            return items.get(ref[1:])
        k = curkey.get(ref)
        return items.get(k) if k else None

    for it in items.values():
        it['inf_unblock'] = False
        if it['kind'] in ('N', 'O') and it['cls'] in ('N', 'NB'):
            tgt = resolve(it['before'])
            chain = 0
            while tgt is not None and tgt['kind'] in ('N', 'O') and chain < 6:
                nxt = resolve(tgt['before'])
                if nxt is None:
                    break
                tgt = nxt; chain += 1
            if tgt is not None and tgt['kind'] == 'I':
                it['inf_unblock'] = True
            elif it['source'] == 'curated' and it['unblocks'] and N1_RX.search(it['unblocks'] + ' ' + it['why']) and not it['before']:
                it['inf_unblock'] = True

    def lane_of(it):
        if it['kind'] == 'P':
            return 'inference-prep'
        if it['kind'] == 'I' and it['cls'] not in ('hold', 'H', 'U'):
            return 'inference-ready'
        return 'non-inference'

    # Bands (2026-10-28 loop redesign): inference-prep 5+s > inference-ready 4+s > non-inference (<= 3.x),
    # except that a non-inference blocker of an inference item still sits just above what it gates.
    def eff_of(it):
        if it['kind'] == 'P':
            return 5.0 + it['s']
        if it['kind'] == 'I':
            if it['cls'] in ('hold', 'H'):
                return 0.5 * it['s']
            if it['cls'] == 'U':
                return 0.3 * it['s']
            return 4.0 + it['s'] + (0.02 if it['cls'] == 'live' else 0)
        if it['cls'] == 'U':
            return 0.3 * it['s']
        if it['cls'] == 'H':
            return 0.5 * it['s']
        tgt = resolve(it['before'])
        if it['cls'] == 'NB':
            # inherits what it gates, capped below the inference bands (non-inference never outranks them)
            return min(eff_of(tgt) + 0.0005, 3.9 + 0.09 * it['s']) if tgt is not None else 0.55 + 0.3 * it['s']
        if it['inf_unblock']:
            return 3.0 + it['s'] * 0.5 + tgt['s'] * 0.5 + 0.001 if tgt is not None else 3.0 + it['s']
        return 2.0 + it['s']

    def tier_of(it):
        if it['kind'] == 'P':
            return 0
        if it['kind'] == 'I':
            if it['cls'] in ('hold', 'H', 'U'): return 7
            if it['cls'] == 'live': return 4
            return 5 if (it['cls'] == 'ready' and it['s'] >= .5) else 6
        if it['cls'] in ('U', 'H'): return 7
        if it['cls'] == 'NB':
            return 3 if resolve(it['before']) is not None else 7
        return 1 if it['inf_unblock'] else 2

    for it in items.values():
        it['eff'] = round(eff_of(it), 5)
        it['tier'] = tier_of(it)
        it['lane'] = lane_of(it)
        if not it['why']:
            w_ = W.get(it['row'], .2)
            it['why'] = f"auto: row weight {w_:g}" + (f", touched {it['touched']}" if it['touched'] else '') + (f"; {it['blocker']}" if it['blocker'] else '')
        if not it['owner']:
            f = it['full'][:900]
            it['owner'] = next((n_ for p_, n_ in OWN if re.search(p_, f)), 'unowned')
    ordered = sorted(items.values(), key=lambda i: (-i['eff'], -i['s'], i['key']))
    for r_, it in enumerate(ordered, 1):
        it['rank'] = r_

    rows = []
    for nid, n in NODES.items():
        its = [i for i in items.values() if nid in i['rows']]
        if not its:
            continue
        best = min(its, key=lambda i: i['rank'])
        rows.append(dict(id=nid, domain=n['domain'], handoff=n['handoff'], open=n['open'], readiness=n['readiness'],
                         best_key=best['key'], best_text=best['text'][:150], best_kind=best['kind'], kind=best['lane'], tier=best['tier'],
                         eff=best['eff'], hold=HOLD.get(nid, ''), blocker=best['blocker'] if best['tier'] == 7 else '',
                         next_action=n['next_action'], n_by_tier=dict(collections.Counter(str(i['tier']) for i in its))))
    rows.sort(key=lambda r: (-r['eff'], r['id']))
    N = len(rows)
    dependents = collections.defaultdict(set)
    for e in EDGES:
        dependents[e['to']].add(e['from'])
    for k, r in enumerate(rows, 1):
        r['rank'] = k
        r['score'] = round(1 - (k - 1) / max(1, N - 1), 4)
        seen, st = set(), list(dependents.get(r['id'], ()))
        while st:
            d = st.pop()
            if d in seen or d == r['id']:
                continue
            seen.add(d); st.extend(dependents.get(d, ()))
        r['unblocks_rows'] = sorted(d for d in seen if NODES.get(d, {}).get('open', 0) > 0)

    doc = {
        "schema": "backlog_priority.v1",
        "generated_by": "scripts/handoffs/backlog_priority.py + scripts/handoffs/backlog_priority_curated.json",
        "generated_at": now,
        "method": ("LOOP-CONTRACT 2026-10-28 (operator-adopted loop redesign): every row and prep item carries kind = inference-prep | "
                   "inference-ready | non-inference, and the bands rank inference-prep (T0: FILLERS BACKLOG rows blocked on a harness fix or a "
                   "missing launcher, seeded via --seed-prep) above inference-ready (T4-T6) above all non-inference (T1-T3, T7; held inference "
                   "counts as non-inference until its hold clears). Within the bands, operator method 2026-10-24: inference items ranked by the inference-backlog-scheduling model (live > ready decision-bearing > "
                   "routine; ROI = decision value per compute-hour; operator holds push down with the blocker named); non-inference tasks that gate "
                   "an inference task inherit and rank just above it; non-inference tasks blocked by nothing are the top tier (T1 gates compute, "
                   "T2 does not); everything else blocked follows its blockers. Row priority = its best open item. score = rank percentile among "
                   "rows with open work (1.0 = highest). Approximate: ~120 curated items, the rest keyword heuristics; row Deps edges are coarse. "
                   "Regenerate: python3 scripts/handoffs/backlog_priority.py (see dashboard/README.md)."),
        "tiers": TIER_SHORT,
        "overrides_file": "handoffs/active/backlog-priority.override.json",
        "done_pending_tick": [{"row": i['row'], "task": i['text'][:90], "done": i['done']} for i in done_list],
        "kinds": list(LANES),
        "inference_prep": [{"rank": i['rank'], "filler": i['filler'], "row": i['row'], "kind": "inference-prep", "s": i['s'],
                            "blocker": i['text'].split(': ', 1)[-1][:140], "owner": i['owner'][:60], "why": i['why'][:160]}
                           for i in sorted(prep_list, key=lambda x: x['rank'])],
        "rows": {r['id']: {"kind": r['kind'], "tier": r['tier'], "rank": r['rank'], "score": r['score'],
                           "basis": f"T{r['tier']} {r['kind']} best open item ({r['best_kind']}): {r['best_text'][:90]}",
                           "unblocks": r['unblocks_rows'][:12],
                           "blocker": (r['hold'] or r['blocker'] or '')[:120]} for r in rows},
    }
    return dict(doc=doc, items=items, ordered=ordered, rows=rows, done=done_list, unmatched=unmatched, curated=curated,
                weights=W, now=now, nodes=NODES)


# ---------------------------------------------------------------- check
def check(res: dict, path: Path = OUT_DEFAULT) -> tuple[list[str], list[str]]:
    """(problems, notes). Problems fail --check; notes are informational."""
    problems, notes = [], []
    if not path.exists():
        return [f"{path.name} is missing: run backlog_priority.py"], notes
    try:
        cur = json.loads(path.read_text(encoding='utf-8'))
    except ValueError as exc:
        return [f"{path.name} is not valid JSON ({exc})"], notes
    fresh = res['doc']
    try:
        age = (datetime.datetime.now(datetime.timezone.utc).date() - datetime.date.fromisoformat(str(cur.get('generated_at', ''))[:10])).days
        if age > STALE_DAYS:
            problems.append(f"{path.name} is {age} days old (limit {STALE_DAYS}): regenerate")
        else:
            notes.append(f"age {age} d")
    except ValueError:
        problems.append(f"{path.name} has no parseable generated_at")
    crow, frow = cur.get('rows', {}), fresh['rows']
    nokind = sorted(r for r, e in crow.items() if e.get('kind') not in LANES)
    if nokind:
        problems.append(f"{len(nokind)} row(s) without a valid kind ({'|'.join(LANES)}): {', '.join(nokind[:6])}")
    missing = sorted(set(frow) - set(crow))
    if missing:
        problems.append(f"{len(missing)} open row(s) missing from the file: {', '.join(missing[:6])}")
    gone = sorted(set(crow) - set(frow))
    if gone:
        notes.append(f"{len(gone)} file row(s) no longer have open work: {', '.join(gone[:6])}")
    both = [r for r in frow if r in crow]
    diff = [r for r in both if crow[r].get('tier') != frow[r]['tier']]
    notes.append(f"tier drift on {len(diff)}/{len(both)} rows")
    if both and len(diff) / len(both) > DRIFT_FRACTION:
        problems.append(f"tier drift on {len(diff)}/{len(both)} rows (> {DRIFT_FRACTION:.0%}): regenerate "
                        f"(e.g. {', '.join(sorted(diff)[:6])})")
    if res['unmatched']:
        notes.append(f"{len(res['unmatched'])} curated entries match no open box (ticked or moved): "
                     + ', '.join(f"{r}:{t}" for r, t in res['unmatched'][:6]))
    return problems, notes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="drift / staleness vs a fresh in-memory build; writes nothing")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--md", type=Path, help="also write the full ranked list as markdown")
    ap.add_argument("--seed-prep", nargs="?", const=FILLERS_DEFAULT, type=Path, metavar="FILLERS_MD",
                    help="refresh the curated `inference_prep` snapshot from FILLERS.md (BACKLOG rows whose blocker is a "
                         "harness fix or a missing launcher), then regenerate")
    args = ap.parse_args(argv)
    if args.seed_prep and not args.check:
        cur = json.loads(CURATED_PATH.read_text(encoding='utf-8'))
        ist = _load('index_state', 'scripts/handoffs/index_state.py')
        nodes = {n['id']: n for n in ist.build_graph(ist.collect())['nodes']}
        seeds = seed_prep(args.seed_prep, nodes, aliases=cur.get('prep_aliases', {}))
        cur['inference_prep'] = seeds
        cur['inference_prep_source'] = {"file": str(args.seed_prep), "seeded_at": datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'),
                                        "rule": "FILLERS BACKLOG, first blocker= is 'harness fix' or 'missing launcher', no grants/<id>.complete, not superseded"}
        CURATED_PATH.write_text(json.dumps(cur, indent=1, ensure_ascii=False) + "\n", encoding='utf-8')
        print(f"seeded {len(seeds)} inference-prep item(s) ({sum(1 for e in seeds if e['row'])} mapped to an index row) into {CURATED_PATH.name}")
    res = build()
    if args.check:
        problems, notes = check(res, args.out)
        for n in notes: print("note:", n)
        for p in problems: print("PROBLEM:", p)
        print(f"{len(problems)} problem(s)")
        return 1 if problems else 0
    args.out.write_text(json.dumps(res['doc'], indent=1, ensure_ascii=False) + "\n", encoding='utf-8')
    tc = collections.Counter(r['tier'] for r in res['rows'])
    print(f"wrote {args.out} ({len(res['rows'])} rows; tiers {dict(sorted(tc.items()))}; "
          f"{len(res['done'])} done-pending-tick; {len(res['unmatched'])} curated unmatched)")
    if args.md:
        args.md.write_text(render_md(res), encoding='utf-8')
        print(f"wrote {args.md}")
    return 0


def render_md(res: dict) -> str:
    """Compact ranked list (T1, compute lane, held summary, rows)."""
    items, ordered, rows = res['items'], res['ordered'], res['rows']
    esc = lambda t: (t or '').replace('|', '/').replace('\n', ' ')
    hdr = "| rank | row | task | handoff:line | kind/cls | owner | size | unblocks | blocker | why |\n|-|-|-|-|-|-|-|-|-|-|\n"
    ln = lambda i: (f"| {i['rank']} | {i['row']} | {esc(i['text'][:90])} | `{Path(i['file']).name}:{i['line']}` | {i['kind']}/{i['cls']} | "
                    f"{esc(i['owner'])} | {esc(i['size'])} | {esc(i['unblocks'][:80])} | {esc(i['blocker'][:60])} | {esc(i['why'][:120])} |")
    out = [f"# Backlog priority (generated {res['now']})\n"]
    for t in range(0, 8):
        sel = [i for i in ordered if i['tier'] == t][:60]
        out.append(f"## {TIER_NAME[t]} ({sum(1 for i in ordered if i['tier'] == t)} boxes)\n\n" + hdr + "\n".join(ln(i) for i in sel) + "\n")
    out.append("## Done, not yet ticked on main\n\n" + "\n".join(f"- {i['row']} {esc(i['text'][:80])}: {i['done']}" for i in res['done']) + "\n")
    out.append("## Rows\n\n| rank | row | tier | best open item |\n|-|-|-|-|\n" +
               "\n".join(f"| {r['rank']} | {r['id']} | T{r['tier']} | {esc(r['best_text'][:90])} |" for r in rows) + "\n")
    return "\n".join(out)


if __name__ == "__main__":
    sys.exit(main())
