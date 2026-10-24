#!/usr/bin/env python3
"""backlog_priority.py - regenerate handoffs/active/backlog-priority.json (dispatch order, compute order, graph colours).

    python3 scripts/handoffs/backlog_priority.py                  # write handoffs/active/backlog-priority.json
    python3 scripts/handoffs/backlog_priority.py --check          # freshness / consistency; non-zero on failure, writes nothing
    python3 scripts/handoffs/backlog_priority.py --sample 20      # stratified validation sample -> review sheet (stdout or --sheet FILE)
    python3 scripts/handoffs/backlog_priority.py --md FILE        # also the readable tables (dispatch, compute lane, held, non-tasks)
    python3 scripts/handoffs/backlog_priority.py --emit-classifier-batch FILE   # uncached boxes for the (future) LLM classifier

v2 (2026-10-24, after the Fable audit of v1). Two published orders, because the operator's question has two halves:

* ``dispatch_now`` (<= 50): NON-inference boxes that are unblocked and can be handed to a subagent THIS turn, ranked
  by what they gate (a box that is the explicit precondition of a compute item is T1), then size, then age.
* ``compute_lane``: the inference-backlog-scheduling packing order per lane (gpu / whole-host / cpu): RUNNING, BOOKED,
  ARMED-UNBOOKED (placeable), STALE-ARMED, BACKLOG; inside each status quiet -> atomic long -> builds -> resumable
  fillers. Live state comes from ``queue_status.py --json`` + the FILLERS.md fields, never from a hand table.

Blockers come from EXPLICIT anchors only: a curated ``before=`` edge, an in-box "depends on / after / precond / blocked
by / if <ID> passes" phrase that names a box or row ID, and FILLERS precondition clauses that name a box. Row-level Deps
edges are NOT inherited into boxes (the Deps column stays row -> row). Holds are box-scoped by the hold's own pattern, each
with a lifting condition; only PARKED/FROZEN rows hold at row level. Parent boxes with open children are collapsed into
their children; NOT SHIPPED / open-question / standing-constraint boxes are excluded and listed as non-tasks.

Per-row fields in the file: ``dispatch_score``, ``compute_score`` (both 0..1), ``lane`` (dispatch | compute | held),
``priority`` = max(dispatch_score, compute_score) (what the graph colours; ``score`` is the same number, the field
index_state.derive_priority reads), ``tier`` (T1..T7 of the winning item), ``basis``.  Tiers: T1 non-inference unblocked and
gates compute; T2 non-inference unblocked, other; T3 non-inference blocked by an open box (follows it); T4 compute live
(RUNNING / BOOKED / ARMED / STALE-ARMED); T5 compute queued-but-blocked or decision-bearing unqueued inference; T6 other
unqueued inference; T7 held (operator / stack-down / parked / frozen / external) with its lifting condition.

KIND / BLOCKED classification is still keyword heuristics (VERB_I, INF_RX, ...) unless a classifier cache exists. The
HOOK for the LLM classifier is ``scripts/handoffs/backlog_classifier_cache.json`` (format: see CLASSIFIER_CACHE_FORMAT):
entries keyed by the text hash of a box override kind / is_task / blocked_by; ``--emit-classifier-batch`` lists the boxes
that still need a pass; the header ``validation.error_rate`` (a hand-scored 100-box sample) is copied into
``classifier_error_rate`` (null until the classifier exists). Curated ``kind`` still outranks the cache.

``--check`` exits 1 when: the file is missing / invalid JSON / lacks its header fields; it is older than the newest
handoffs/ commit by more than 24 h; more than 5 % of curated entries match no open box; or the tree is behind origin/main.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import hashlib
import importlib.util
import json
import random
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
OUT_DEFAULT = REPO_ROOT / "handoffs" / "active" / "backlog-priority.json"
CURATED_PATH = HERE / "backlog_priority_curated.json"
CLASSIFIER_CACHE = HERE / "backlog_classifier_cache.json"
QUEUE_STATUS_CANDIDATES = (REPO_ROOT / ".claude/skills/inference-backlog-scheduling/scripts/queue_status.py",
                           Path("/workspace/.claude/skills/inference-backlog-scheduling/scripts/queue_status.py"))
SCHEMA = "backlog_priority.v2"
STALE_HOURS = 24
UNMATCHED_LIMIT = 0.05
DISPATCH_CAP = 50
CLASSIFIER_CACHE_FORMAT = {
    "schema": "backlog_classifier_cache.v1", "model": "<model id>", "classified_at": "<UTC>",
    "validation": {"sample": 100, "error_rate": "<float: hand-scored share of wrong verdicts>", "scored_at": "<UTC>"},
    "entries": {"<text_hash(box)>": {"kind": "I|N|O", "is_task": True, "blocked_by": ["<box or row ID>"], "parent_of": ["<ID>"]}}}

TIER_SHORT = {"1": "T1 non-inference, unblocked, gates compute", "2": "T2 non-inference, unblocked, other",
              "3": "T3 non-inference, blocked by an open box (follows it)", "4": "T4 compute live (running / booked / armed)",
              "5": "T5 compute queued-but-blocked or decision-bearing unqueued", "6": "T6 unqueued inference, routine",
              "7": "T7 held (named blocker + lifting condition)"}
BRIEF_SUFFIX = ("Constraints: shared host - no process management (never kill by name pattern); work only in a fresh detached worktree "
                "off origin/main; commit locally with explicit pathspecs, do not push; do not tick checkboxes or edit index rows "
                "(the owning session applies); no inference unless a grant exists; the task TEXT is the identity, file:line is a hint.")
STATUS_RANK = {"RUNNING": 0, "BOOKED": 1, "ARMED-UNBOOKED": 2, "STALE-ARMED": 3, "BACKLOG": 4}
STATUS_SCORE = {"RUNNING": .95, "BOOKED": .92, "ARMED-UNBOOKED": .88, "STALE-ARMED": .72}
GROUP_RANK = {"quiet": 0, "atomic": 1, "build": 2, "resumable": 3}


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- kind heuristics (the classifier replaces these)
VERB_I = r'^(run|re-?run|measure|re-?measure|replay|sweep|confirm|profile|bench|a/b|collect|execute|load|compare|re-?baseline|validate on|test on|time|probe)\b'
VERB_N = r'^(write|draft|document|prepare|design|implement|wire|build|port|fix|update|create|extend|define|add|land|persist|enumerate|derive|emit|publish|merge|catalog|annotate)\b'
INF_RX = re.compile(r'llama-bench|\bABA\b|A/B|\bsweep\b|inference window|compute window|quiet (window|host)|GPU window|CPU window|on a quarter|whole[- ]host|replicat|soak|overnight|\bPPL\b|perplexity|tok/s|\bwindow\b.{0,40}(run|bench)|N=\d+|\bn=\d+|requests?\b.{0,30}(run|measure)', re.I)
NOINF_RX = re.compile(r'zero[- ]inference|no inference|model-free|\boffline\b|read-only|no GPU|desk check|docs?-only|documentation|no model', re.I)
INF2_RX = re.compile(r'clean window|exclusive claim|host-quiet|canonical bench|never run|not yet run|re-?run|inference window|needs? an? (inference|GPU|CPU|compute|quiet) (window|slot)|quiet window|GPU window|CPU window|on a quarter|measurement window|timing window', re.I)
# a check that rides on someone else's next run ("at each driver's next GPU run", "at the next GPU AK window") is compute, not code
PIGGY_RX = re.compile(r'\b(at|on|in|during)\b.{0,30}\bnext\b.{0,24}\b(GPU|CPU|AK|inference|bench\w*)\b.{0,12}\b(run|window|launch|session)|first-(GPU|CPU)-run|\bnext (GPU|CPU) (run|AK window)', re.I)
# the OPERATOR is the actor: "operator D2" (a decision label) and a bare "operator" no longer count (audit #9)
OP_RX = re.compile(r'\boperator (decision|action|sign(s|-off)?|ratif\w*|approv\w*|go\b|ack\w*|runs?\b|to (sign|run|approve|decide|ratify|choose|apply))|human sign-off|awaiting operator|PENDING OPERATOR|USER APPROVAL', re.I)
OP_EXCL = re.compile(r'\boperator[- ]?(approved|pre-approved|ruling|chose|directed|2026)', re.I)
BLK_RX = re.compile(r'(blocked (on|by)|\bBLOCKED\b|gated (on|by)|waiting (on|for))', re.I)
# explicit dependency phrases that name an ID (a box or a row); nothing else is an anchor
KW_RX = re.compile(r'(?:depends?\s+on|dependent\s+on|only\s+after|\bafter\b|precond(?:ition)?s?\b|pre-?requisites?\b|blocked\s+(?:on|by)|gated\s+(?:on|by)|waits?\s+(?:for|on)|waiting\s+(?:for|on)|\bunless\b|\buntil\b)', re.I)
IF_RX = re.compile(r'\bif\s+(?P<id>[A-Z][A-Za-z0-9]*(?:-[A-Za-z0-9.]+)+)\s+(?:passes|clears|lands|is done|completes|succeeds)', re.I)
ID_RX = re.compile(r'(?<![\w.])([A-Z][A-Za-z0-9]*(?:-[A-Za-z0-9.]+)+(?:\([a-z]\))?)')
NONTASK_RX = re.compile(r'^\W*(NOT SHIPPED|NOT ADOPTED|NOT DONE|REJECTED|DECLINED|WON.?T FIX|SUPERSEDED|Open questions?\b|Question\s*:|FYI\b|Note\s*:|Context\s*:|For the record|Decision record|Record\s*:)', re.I)
OWN = [(r'workspace-f8|\bf8\b', 'f8'), (r'3c4ca599', '3c4ca599'), (r'workspace-58|\bws58\b', 'workspace-58'),
       (r'workspace-7b|\b7b\b', 'workspace-7b'), (r'workspace-ec|\bec\b', 'workspace-ec'), (r'workspace-sec', 'workspace-sec')]
ROW_RX = re.compile(r'\b((?:INF|EVL|RTG|UFH|REV|PIP)-\d{2})\b')


def _clean(t: str) -> str:
    t = re.sub(r'[*`]', '', t)
    return re.sub(r'^\W+', '', t)


def _body(t: str) -> str:
    """The box text without its leading 'ID — ' / 'ID (x) — ' label, so the first real verb is what the kind heuristics see."""
    t = _clean(t)
    m = re.match(r'^[A-Za-z0-9_.\-+/() ,]{1,45}?\s+[—–]\s+', t) or re.match(r'^[A-Za-z0-9_.\-+/]{2,40}\s+-+\s+', t)
    return t[m.end():] if m else t


def box_token(text: str) -> str:
    """The leading ID of a box ('RI-11', 'VB-FOLDGATE-WRITE', 'KPF-17.4c') or ''. The task text is the identity; this is its handle."""
    t = _clean(text)
    m = ID_RX.match(t)
    if not m:
        return ''
    tok = m.group(1).rstrip('.')
    if not (re.search(r'\d', tok) or re.fullmatch(r'[A-Z]+(-[A-Z]+)+', tok)):
        return ''
    return tok if re.match(r'^(?:\s|$|[—–:,.;()\-])', t[m.end():]) else ''


def text_hash(full: str) -> str:
    return hashlib.sha1(' '.join(re.sub(r'[*`]', '', full).lower().split())[:1500].encode()).hexdigest()[:16]


def auto_kind(text: str) -> str:
    t = text.replace('**', '')
    body = _body(t).lower()
    head = t[:240]
    if OP_RX.search(head) and not OP_EXCL.search(head) and not re.match(r'^(prepare|draft|write|compose|assemble|package|build|add|implement)\b', body):
        return 'O'            # "prepare the package for operator ratification" is a subagent task; the operator only signs it
    if NOINF_RX.search(t[:400]):
        return 'N'
    if re.match(VERB_I, body):
        return 'I'
    if re.match(VERB_N, body):
        return 'N'            # an authoring / code verb leads: the window keywords below describe what the artefact is FOR (audit: CS-6 run plan)
    if PIGGY_RX.search(t[:420]) or INF_RX.search(t[:420]) or INF2_RX.search(t[:420]):
        return 'I'
    return 'N'


def size_class(s: str) -> str:
    s = (s or '').strip()
    if s.startswith('~'):
        m = re.match(r'~\s*(\d+(?:\.\d+)?)\s*(h|hr|hours|min|m|d)', s)
        if m:
            v = float(m.group(1)); u = m.group(2)
            hrs = v if u.startswith('h') else (v / 60 if u in ('min', 'm') else v * 24)
            return 'S' if hrs <= 1 else ('M' if hrs <= 4 else 'L')
    return s[:1] if s[:1] in ('S', 'M', 'L') else 'M'


def size_of(full: str) -> str:
    m = re.search(r'~\s*(\d+(?:\.\d+)?)\s*(h|hr|hours|min|m|d)\b', full[:900])
    if m:
        return f'~{m.group(1)} {m.group(2)}'
    n = len(full)
    return 'S' if n < 350 else ('M' if n < 1000 else 'L')


# ---------------------------------------------------------------- git helpers
def _git(*args: str, cwd: Path = REPO_ROOT, timeout: int = 60) -> str | None:
    try:
        r = subprocess.run(['git', '-C', str(cwd), *args], capture_output=True, text=True, errors='replace', timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def git_state() -> dict:
    """{head, origin_main, behind, newest_handoffs_commit (epoch)}; any member None when git cannot answer."""
    head = _git('rev-parse', 'HEAD')
    om = _git('rev-parse', '--verify', '-q', 'origin/main')
    behind = _git('rev-list', '--count', 'HEAD..origin/main') if om else None
    ct = _git('log', '-1', '--format=%ct', 'HEAD', '--', 'handoffs')
    return dict(head=head, origin_main=om, behind=int(behind) if behind and behind.isdigit() else None,
                newest_handoffs_commit=int(ct) if ct and ct.isdigit() else None)


def _blame_dates(path: Path) -> dict[int, str]:
    r = _git('blame', '--line-porcelain', 'HEAD', '--', str(path.relative_to(REPO_ROOT)), timeout=120)
    if not r:
        return {}
    times, ln = {}, 0
    for l in r.splitlines():
        m = re.match(r'^[0-9a-f]{40} \d+ (\d+)', l)
        if m: ln = int(m.group(1))
        elif l.startswith('author-time '):
            times[ln] = datetime.datetime.fromtimestamp(int(l.split()[1]), datetime.timezone.utc).strftime('%Y-%m-%d')
    return times


# ---------------------------------------------------------------- collection
def collect_boxes(index_state) -> tuple[dict, list[dict]]:
    """(state, boxes). EVERY box (open and closed) carries file/line/token/indent/parent so anchors can be resolved; only OPEN
    boxes are classified and blamed. ``children`` are indices of directly nested boxes."""
    brc = index_state.brc
    state = index_state.collect()
    paths = index_state.handoff_paths()
    h2r: dict = {}
    for rid, r in state['rows'].items():
        h2r.setdefault(r.get('handoff'), []).append(rid)
    boxes: list[dict] = []
    for h, p in paths.items():
        lines = p.read_text(encoding='utf-8', errors='replace').splitlines()
        rel = str(p.relative_to(REPO_ROOT))
        dates = None
        stack: list[tuple[int, int]] = []                       # (indent, box index)
        for ln, st, body, head in brc._boxes(p):
            indent = len(lines[ln - 1]) - len(lines[ln - 1].lstrip())
            while stack and stack[-1][0] >= indent:
                stack.pop()
            b = dict(handoff=h, file=rel, line=ln, text=body, head=head, rows=h2r.get(h, []), open=st not in ('x', 'X'),
                     indent=indent, parent=stack[-1][1] if stack else None, children=[], token=box_token(body), idx=len(boxes),
                     code=0, reasons=[], touched=None, full=body[:1500], sub='')
            if b['parent'] is not None:
                boxes[b['parent']]['children'].append(b['idx'])
            stack.append((indent, b['idx']))
            if b['open']:
                if dates is None:
                    dates = _blame_dates(p)
                b['code'], b['reasons'] = brc.classify(p, ln, st, body, head)
                full = [lines[ln - 1]]
                for l in lines[ln:ln + 30]:
                    if re.match(r'\s*[-*] \[[ xX]\]', l) or l.startswith('#'):
                        break
                    full.append(l)
                b['full'] = ' '.join(x.strip() for x in full)[:1500]
                b['sub'] = '\n'.join(x.rstrip() for x in full[1:7])
                b['touched'] = dates.get(ln)
            boxes.append(b)
    return state, boxes


def load_queue(path: Path | None = None, run: bool = True) -> dict | None:
    """queue_status.py --json (read-only), or a saved JSON. None when unavailable."""
    if path:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    if not run:
        return None
    script = next((c for c in QUEUE_STATUS_CANDIDATES if c.exists()), None)
    if script is None:
        return None
    try:
        r = subprocess.run([sys.executable, '-I', str(script), '--json'], capture_output=True, text=True, timeout=120)
        return json.loads(r.stdout) if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None


def load_cache(path: Path = CLASSIFIER_CACHE) -> dict:
    try:
        d = json.loads(path.read_text(encoding='utf-8'))
        return d if isinstance(d, dict) and isinstance(d.get('entries'), dict) else {}
    except (OSError, ValueError):
        return {}


# ---------------------------------------------------------------- compute lane
def _dur_min(s: str) -> float | None:
    s = s.replace('~', ' ').lower()
    m = re.search(r'(\d+)\s*h\s*(\d+)\s*m', s)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    m = re.search(r'(\d+(?:\.\d+)?)(?:\s*-\s*\d+(?:\.\d+)?)?\s*(h|hr|hrs|hours|gpu-h|min|m)\b', s)
    if not m:
        return None
    v = float(m.group(1))
    return v * 60 if m.group(2) in ('h', 'hr', 'hrs', 'hours', 'gpu-h') else v


def _lane_of(shape: str, substrate: str = '') -> str:
    s = shape.lower()
    if re.search(r'whole[- ]host|\b0-95\b|\bq0-q3\b', s):
        return 'whole-host'
    if 'mi210' in s[:80] or re.match(r'^\s*gpu', s) or (substrate == 'gpu' and not re.match(r'^\s*(one )?cpu', s)):
        return 'gpu'
    return 'cpu'


def build_fillers(queue: dict | None, box_tokens: set[str], rows: set[str]) -> list[dict]:
    """One record per non-terminal FILLERS row with lane / group / base score and its explicit box preconditions."""
    if not queue:
        return []
    recs = []
    for status, lst in queue.get('buckets', {}).items():
        if status == 'COMPLETE':
            continue
        for r in lst:
            recs.append(dict(r, status=status))
    ids = {r['id'] for r in recs}
    pre_of: dict[str, set[str]] = collections.defaultdict(set)           # filler -> boxes named as its precondition
    chain_of: dict[str, set[str]] = collections.defaultdict(set)         # filler -> fillers named as its precondition
    for r in recs:
        for m in re.finditer(r'(?:precond\w*|blocked (?:on|by)|until|waits? (?:for|on)|gated (?:on|by)|depends on|requires)\b[^.;|]{0,200}',
                             r.get('notes', ''), re.I):
            seg = m.group(0)
            for t in ID_RX.findall(seg):
                t = t.rstrip('.')
                if t in box_tokens:
                    pre_of[r['id']].add(t)
            for t in re.findall(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)+', seg):
                if t in ids and t != r['id']:
                    chain_of[r['id']].add(t)
    is_pre = {t for s in chain_of.values() for t in s}
    out = []
    for r in recs:
        dur = _dur_min(r.get('duration', ''))
        group = ('quiet' if r.get('class') == 'block-timing-quiet' else
                 'build' if re.search(r'build', r['id']) or r['id'] in is_pre else
                 'atomic' if (dur or 0) >= 240 or re.search(r'\batomic\b|fixed order', r.get('notes', ''), re.I) else 'resumable')
        blocker = (r.get('blocker') or '')
        base = STATUS_SCORE.get(r['status'])
        if base is None:
            base = .6 if re.search(r'launcher|harness|build|code|fix', blocker, re.I) else .45
        rws = sorted({m for m in ROW_RX.findall(r.get('decision', '')) if m in rows})[:3]
        out.append(dict(id=r['id'], status=r['status'], lane=_lane_of(r.get('shape') or r.get('resources', ''), r.get('substrate', '')), group=group,
                        shape=(r.get('shape') or r.get('resources', ''))[:160], min_window=r.get('min_window', ''), ram_gib=r.get('ram_gib', ''),
                        cls=r.get('class', ''), duration=r.get('duration', ''), duration_min=dur, owner=r.get('owner', ''),
                        decision=r.get('decision', ''), blocker=blocker or None, base_score=base, rows=rws,
                        ends_in_min=r.get('ends_in_min'), preconds=sorted(pre_of.get(r['id'], ())),
                        chain=sorted(chain_of.get(r['id'], ())), notes=r.get('notes', '')))
    return out


LANE_SLOTS = {'cpu': 4, 'gpu': 1, 'whole-host': 1}                    # four CPU quarters run in parallel; the GPU and the whole host are single bins


def order_lane(fillers: list[dict], now: datetime.datetime) -> dict:
    """Per-lane packing order with an ETA from greedy list scheduling over the lane's bins (cpu = 4 quarters). A LOWER BOUND: it
    uses declared durations, ignores window availability and does not model the cpu / whole-host conflict."""
    lanes: dict[str, list[dict]] = {}
    for f in fillers:
        lanes.setdefault(f['lane'], []).append(f)
    fmt = lambda d: d.strftime('%Y-%m-%dT%H:%MZ')
    out = {}
    for lane, items in sorted(lanes.items()):
        items.sort(key=lambda f: (STATUS_RANK[f['status']], GROUP_RANK[f['group']], -f['compute_score'], f['id']))
        free = [now] * LANE_SLOTS.get(lane, 1)
        for f in items:
            if f['status'] == 'RUNNING' and f.get('ends_in_min') is not None:
                end = now + datetime.timedelta(minutes=max(0, f['ends_in_min']))
                k = free.index(min(free)); free[k] = max(free[k], end)
                f['eta_end'], f['eta_basis'] = fmt(end), 'grant end'
            elif f['status'] in ('BOOKED', 'ARMED-UNBOOKED') and f['duration_min']:
                k = free.index(min(free)); free[k] = free[k] + datetime.timedelta(minutes=f['duration_min'])
                f['eta_end'] = fmt(free[k])
                f['eta_basis'] = f"declared duration packed on the earliest-free of {len(free)} bin(s) (lower bound; ignores window availability)"
            else:
                f['eta_end'], f['eta_basis'] = None, ('no declared duration' if f['status'] in ('RUNNING', 'BOOKED', 'ARMED-UNBOOKED')
                                                      else 'not placeable: ' + (f['blocker'] or f['status'].lower()))
        out[lane] = dict(eta_end=max((f['eta_end'] for f in items if f['eta_end']), default=None), items=items, bins=len(free))
    return out


# ---------------------------------------------------------------- the build
def build(curated: dict | None = None, index_state=None, state=None, boxes=None, queue='auto', cache=None,
          git=None, now=None) -> dict:
    curated = curated or json.loads(CURATED_PATH.read_text(encoding='utf-8'))
    index_state = index_state or _load('index_state', 'scripts/handoffs/index_state.py')
    if state is None or boxes is None:
        state, boxes = collect_boxes(index_state)
    queue = load_queue() if isinstance(queue, str) and queue == 'auto' else queue
    cache = load_cache() if cache is None else cache
    git = git if git is not None else git_state()
    now = now or datetime.datetime.now(datetime.timezone.utc)
    try:                                                    # ETAs are relative to the queue snapshot (ends_in_min was computed then)
        qnow = datetime.datetime.strptime(queue['as_of'], '%Y-%m-%dT%H:%MZ').replace(tzinfo=datetime.timezone.utc)
    except (TypeError, KeyError, ValueError):
        qnow = now
    graph = index_state.build_graph(state)
    NODES = {n['id']: n for n in graph['nodes']}
    DEP = [e for e in graph['edges'] if e['kind'] == 'dep']
    W = curated.get('row_weights', {})
    HOLDS = curated.get('holds', [])
    PARK = curated.get('park_rows', {})
    ROWS = set(state['rows'])
    cents = cache.get('entries', {})
    ts = lambda d: d.strftime('%Y-%m-%dT%H:%MZ')

    # ---- token index over ALL boxes (an anchor naming a ticked box is satisfied, not a blocker)
    tok_idx: dict[str, list[dict]] = collections.defaultdict(list)
    for b in boxes:
        if b['token']:
            tok_idx[b['token']].append(b)
    box_tokens = set(tok_idx)

    def resolve(tok: str, frm: dict):
        """('open'|'closed'|'row'|None, target). Same file wins; an ambiguous token is not an anchor."""
        cands = tok_idx.get(tok, [])
        pick = [c for c in cands if c['file'] == frm['file']] or cands
        if pick and len({c['file'] for c in pick}) == 1:
            op = [c for c in pick if c['open']]
            return ('open', op[0]) if op else ('closed', pick[0])
        if tok in ROWS and not cands:
            return 'row', tok
        return None, None

    opened = [b for b in boxes if b['open']]

    # ---- curated matching (identity = row + text token)
    def find_box(rowid, tok):
        for b in opened:
            if rowid in b['rows'] and tok in b['text'].replace('**', '').replace('`', '')[:110]:
                return b
        return None

    cur_by_idx: dict[int, dict] = {}
    cur_key: dict[str, int] = {}
    unmatched: list[str] = []
    for c in curated['entries']:
        b = find_box(c['row'], c['tok'])
        if b is None:
            unmatched.append(f"{c['row']}:{c['tok']}")
            continue
        cur_by_idx[b['idx']] = c
        cur_key[f"{c['row']}:{c['tok']}"] = b['idx']

    done_idx: dict[int, str] = {}                           # completion claims awaiting the owner's tick
    done_stale: list[str] = []
    for d_ in curated.get('done_pending_tick', []):
        b = find_box(d_['row'], d_['tok'])
        if b is None:
            done_stale.append(f"{d_['row']}:{d_['tok']}")
        else:
            done_idx[b['idx']] = d_['done']

    # ---- per-box analysis
    A: dict[int, dict] = {}
    for b in opened:
        rowid = b['rows'][0] if b['rows'] else b['handoff']
        c = cur_by_idx.get(b['idx'])
        h = text_hash(b['full'])
        ce = cents.get(h) or {}
        a = dict(b=b, row=rowid, cur=c, hash=h, kind=(c or {}).get('kind') or ce.get('kind') or auto_kind(b['text']), holds=[],
                 blocked_by=[], blocked_row=[], is_task=True, why_not='', cached=bool(ce), key=f"{rowid}:{b['token'] or h[:8]}")
        if b['idx'] in done_idx:
            a.update(is_task=False, why_not='done, tick pending: ' + done_idx[b['idx']][:80])
        elif ce.get('is_task') is False:
            a.update(is_task=False, why_not='classifier: not a task')
        elif NONTASK_RX.search(b['text']) and not c:
            a.update(is_task=False, why_not='record / open question, not a task')
        elif re.match(r'^[\s*`]*~~', b['text']) and not c:
            a.update(is_task=False, why_not='struck through / superseded')
        if b['code'] == 2:                                    # backlog_row_check screener verdicts
            rs = ' '.join(b['reasons'])
            if re.search(r'DO-NOT-DISPATCH|PROHIBITION|standing-constraint', rs, re.I) and not c:
                a.update(is_task=False, why_not='standing constraint / guard: ' + b['reasons'][0][:90])
            elif re.search(r'OWNER', rs) and re.search(r'not you', rs):
                a['kind'] = a['kind'] if c else 'O'
            elif re.search(r'DEPENDENCY GRAPH|CHILD BOX', rs):
                pass                                          # represented by anchors / parent collapse below
            else:
                a['holds'].append(dict(name='screener', lift='resolve the condition the screener names: ' + b['reasons'][0][:110]))
        A[b['idx']] = a

    seen_keys: set[str] = set()
    for a in A.values():                                      # keys are row:token (or row:text-hash); a repeat gets the line appended
        if a['key'] in seen_keys:
            a['key'] += f"@{a['b']['line']}"
        seen_keys.add(a['key'])

    # parents with open children are containers (collapsed into their children) unless a curator vouched for them
    collapsed = []
    for i, a in A.items():
        if a['is_task'] and any(boxes[ci]['open'] for ci in a['b']['children']) and i not in cur_by_idx:
            a.update(is_task=False, why_not='collapsed into its open children')
            collapsed.append(a)

    # ---- holds (box-scoped by the hold's own pattern, each with a lifting condition)
    for i, a in A.items():
        b = a['b']
        if not a['is_task'] and not a['why_not'].startswith('collapsed'):
            continue                                          # a collapsed parent still computes holds: its children inherit them
        t = _clean(b['text'])[:320]
        for rid in b['rows']:
            if rid in PARK:
                a['holds'].append(dict(name='parked-file', lift=PARK[rid], inherit=False)); break
        for h in HOLDS:
            if h.get('rows') and not set(h['rows']) & set(b['rows']):
                continue
            if h.get('kinds') and a['kind'] not in h['kinds']:
                continue
            if re.search(h['pattern'], t, 0 if h.get('case_sensitive') else re.I) and not (h.get('except') and re.search(h['except'], t, re.I)):
                a['holds'].append(dict(name=h['name'], lift=h['lift'], inherit=bool(h.get('inherit'))))
        if a['cur'] and a['cur'].get('hold'):
            a['holds'].append(dict(name='curated-hold', lift=a['cur']['hold'], inherit=False))
        if a['kind'] == 'O':
            a['holds'].append(dict(name='operator', lift='the operator acts (decision / signature / run): ' + t[:90], inherit=False))
    for i, a in A.items():                                    # freeze / park passes from the nearest open ancestor
        p = a['b']['parent']
        while p is not None and a['is_task']:
            pa = A.get(p)
            if pa is not None:
                inh = [h for h in pa['holds'] if h.get('inherit')]
                if inh and not any(h['name'] == inh[0]['name'] for h in a['holds']):
                    a['holds'].extend(dict(h, inherited=True) for h in inh)
                break
            p = boxes[p]['parent']

    # ---- explicit blockers: in-box phrases that name a box / row ID
    for i, a in A.items():
        b = a['b']
        if not a['is_task']:
            continue
        txt = re.sub(r'[*`]', '', b['full'])[:700]
        toks: list[str] = []
        for m in KW_RX.finditer(txt):
            seg = re.split(r'[.;]\s|\n', txt[m.end():m.end() + 100])[0]
            toks += ID_RX.findall(seg)[:3]
        toks += [m.group('id') for m in IF_RX.finditer(txt)]
        toks += list(cents.get(a['hash'], {}).get('blocked_by') or [])
        toks += re.findall(r'downstream of ([\w.\-]+)', ' '.join(b['reasons']))     # the screener's dependency-graph verdict
        seen = set()
        for t_ in toks:
            t_ = t_.rstrip('.,')
            if t_ in seen or t_ == b['token']:
                continue
            seen.add(t_)
            how, tgt = resolve(t_, b)
            if how == 'open' and tgt['idx'] != b['idx'] and tgt['idx'] not in b['children'] and tgt['idx'] != b['parent']:
                a['blocked_by'].append(tgt['idx'])
            elif how == 'row' and tgt not in b['rows'] and NODES.get(tgt, {}).get('open', 0) > 0:
                a['blocked_row'].append(tgt)
        if not a['blocked_by'] and not a['blocked_row'] and not a['holds'] and a['kind'] != 'O':
            m = BLK_RX.search(_clean(b['text'])[:240])
            if m and not any(resolve(x.rstrip('.'), b)[0] == 'closed' for x in ID_RX.findall(_clean(b['text'])[m.end():m.end() + 80])):
                a['holds'].append(dict(name='text-blocker', lift='the blocker the box names is resolved: ' + _clean(b['text'])[m.start():m.start() + 110], inherit=False))

    # ---- gate edges: curated before=, in-box anchors; (A gates B)
    gates: dict[int, set] = collections.defaultdict(set)             # box idx -> {('box', idx) | ('filler', id)}
    for i, a in A.items():
        c = a['cur']
        if c and c.get('before') and a['is_task']:
            ref = c['before']
            if ref.startswith('filler:'):
                for fid in ref[7:].split(','):
                    gates[i].add(('filler', fid.strip()))
            elif ref in cur_key:
                gates[i].add(('box', cur_key[ref]))
        for j in a['blocked_by']:
            gates[j].add(('box', i))
    # ---- compute side: FILLERS rows, box links, scores
    fillers = build_fillers(queue, box_tokens, ROWS)
    fby = {f['id']: f for f in fillers}
    for f in fillers:                                        # box preconditions named in FILLERS rows are real T1 edges
        for tk in f['preconds']:
            for bb in tok_idx.get(tk, []):
                if bb['open'] and bb['idx'] in A and A[bb['idx']]['is_task']:
                    gates[bb['idx']].add(('filler', f['id']))
    links: dict[int, list[str]] = {}
    fid_rx = (re.compile(r'(?<![\w-])(' + '|'.join(re.escape(x) for x in sorted(fby, key=len, reverse=True) if len(x) >= 6) + r')(?![\w-])')
              if any(len(x) >= 6 for x in fby) else None)
    by_decision: dict[int, list[str]] = collections.defaultdict(list)       # a FILLERS decision column that names a box ID links it
    for f in fillers:
        for tk in ID_RX.findall(f['decision']):
            for bb in tok_idx.get(tk.rstrip('.'), []):
                if bb['open']:
                    by_decision[bb['idx']].append(f['id'])
    for i, a in A.items():
        ids = list((a['cur'] or {}).get('fillers', []))
        if a['kind'] == 'I':
            ids += by_decision.get(i, [])
            if fid_rx:
                ids += fid_rx.findall(re.sub(r'[*`]', '', a['b']['full']))
        links[i] = [x for x in dict.fromkeys(ids) if x in fby]
        for fid in links[i]:
            fby[fid].setdefault('boxes', []).append(a['key'])
            if a['row'] not in fby[fid]['rows']:
                fby[fid]['rows'].append(a['row'])

    def s_of(a):
        b, c = a['b'], a['cur']
        if c:
            return float(c['s'])
        t = b['text']
        bonus = (.12 if b['touched'] and b['touched'] >= '2026-10-21' else (.04 if b['touched'] and b['touched'] >= '2026-09-24' else 0)) \
            + (.06 if re.search(r'PRIORITY|NEXT|READY|armed|ARMED', t[:200]) else 0)
        return round(min(.6, W.get(a['row'], .2) * .7 + bonus), 3)

    for i, a in A.items():
        a['s'] = s_of(a)
        a['size'] = (a['cur'] or {}).get('size') or size_of(a['b']['full'])
        a['owner'] = next((n_ for p_, n_ in OWN if re.search(p_, a['b']['full'][:900])), None)
        a['blocked'] = bool(a['blocked_by'] or a['blocked_row'])
        a.update(gates=[], gate_compute=0.0, dispatch_score=0.0, compute_score=0.0, lane='none', tier=None)
    for f in fillers:
        sj = max([A[i]['s'] for i in A if A[i]['cur'] and f['id'] in links.get(i, [])] or [0.0])
        f['compute_score'] = round(min(.99, f['base_score'] + .05 * sj), 4)
    lane_order = order_lane(fillers, qnow)

    def blocker_names(a):
        return ', '.join([(A[j]['b']['token'] or A[j]['key']) for j in a['blocked_by'][:3] if j in A] + a['blocked_row'][:3])

    for i, a in A.items():                                   # inference boxes: compute lane
        if not a['is_task'] or a['kind'] != 'I':
            continue
        queued = [fby[f] for f in links[i]]
        live = [f for f in queued if f['status'] in STATUS_SCORE]
        if a['holds']:
            a.update(lane='held', tier=7, compute_score=round(.05 + .05 * a['s'], 4))
        elif a['blocked']:
            a['holds'].append(dict(name='blocked-by-box', lift='its named precondition lands: ' + blocker_names(a)))
            a.update(lane='held', tier=7, compute_score=round(.08 + .1 * a['s'], 4))
        elif live:
            a.update(lane='compute', tier=4, compute_score=max(f['compute_score'] for f in live))
        elif queued:
            a.update(lane='compute', tier=5, compute_score=max(f['compute_score'] for f in queued))
        else:
            a.update(lane='compute', tier=5 if a['s'] >= .5 else 6, compute_score=round(.10 + .30 * a['s'], 4))

    def gate_compute(i, seen=()):
        """Best compute_score this box gates (directly or through a chain of non-inference boxes) and what it gates."""
        best, names = 0.0, []
        for kind_, j in sorted(gates.get(i, ()), key=str):
            if kind_ == 'filler' and j in fby:
                best = max(best, fby[j]['compute_score']); names.append(f"compute: {j} ({fby[j]['status']})")
            elif kind_ == 'box' and j in A and j not in seen and A[j]['is_task']:
                t = A[j]
                nm = t['b']['token'] or _clean(t['b']['text'])[:40]
                if t['kind'] == 'I':
                    if {h['name'] for h in t['holds']} <= {'blocked-by-box'}:      # held behind this very box still counts as gated compute
                        best = max(best, t['compute_score'] or .2); names.append(f"compute: {nm}")
                else:
                    sb, sn = gate_compute(j, seen + (i,))
                    if sb:
                        best = max(best, sb * .98); names.append(f"{nm} -> {sn[0]}")
                    else:
                        names.append(f"box: {nm}")
        return best, names

    age = lambda t: (now.date() - datetime.date.fromisoformat(t)).days if t else 999
    for i, a in A.items():                                   # non-inference boxes: dispatch lane
        if not a['is_task'] or a['kind'] == 'I':
            continue
        a['gate_compute'], a['gates'] = gate_compute(i)
        if a['holds']:
            a.update(lane='held', tier=7, dispatch_score=round(.02 + .05 * a['s'], 4))
        elif a['blocked']:
            a.update(lane='held', tier=3)
        else:
            sc = {'S': .10, 'M': .06, 'L': .02}[size_class(a['size'])]
            a['lane'] = 'dispatch'
            if a['gate_compute']:
                a['tier'] = 1
                a['dispatch_score'] = round(min(1.0, .70 + .30 * (.5 * a['gate_compute'] + .3 * a['s'] + .2 * (sc / .10))), 4)
            else:
                d = age(a['b']['touched'])
                a['tier'] = 2
                a['dispatch_score'] = round(min(.69, .20 + (.15 if a['gates'] else 0) + sc + (.10 if d <= 7 else .07 if d <= 30 else .03 if d <= 90 else 0)
                                                + (0 if re.search(r'intake', a['b']['head'], re.I) else .05)
                                                + .06 * W.get(a['row'], .2) + .10 * (a['cur']['s'] if a['cur'] else 0)), 4)
    for _ in range(3):                                       # blocked boxes follow their blocker (just below it)
        for i, a in A.items():
            if a['tier'] != 3:
                continue
            vals = [max(A[j]['dispatch_score'], A[j]['compute_score']) for j in a['blocked_by'] if j in A]
            vals += [max([x['dispatch_score'] for x in A.values() if rid in x['b']['rows'] and x['lane'] == 'dispatch'] or [0.0]) for rid in a['blocked_row']]
            a['dispatch_score'] = min(.69, round(max(.10, max(vals) * .9 - .001), 4)) if vals else .10

    unblock = [f for f in fillers if f['status'] == 'STALE-ARMED' or (f['status'] == 'BACKLOG' and re.search(r'launcher|harness|build|code|fix', f['blocker'] or '', re.I))]

    # ---- rows
    items = [a for a in A.values() if a['is_task']]
    rows = []
    for nid, n in NODES.items():
        its = [a for a in items if nid in a['b']['rows']]
        frs = [f for f in fillers if nid in f['rows']]
        if not its and not frs and not any(nid in a['b']['rows'] for a in A.values()):
            continue
        ds = max([a['dispatch_score'] for a in its if a['lane'] == 'dispatch'] or [0.0])
        cs = max([a['compute_score'] for a in its if a['lane'] == 'compute'] + [f['compute_score'] for f in frs] or [0.0])
        held_best = max([a['dispatch_score'] or a['compute_score'] for a in its if a['lane'] == 'held'] or [0.0])
        pr = max(ds, cs)
        lane = 'compute' if cs >= ds and cs > 0 else 'dispatch' if ds > 0 else 'held'
        if pr == 0:
            pr = min(.15, held_best) or 0.01
        tier = min(([a['tier'] for a in its if a['lane'] == lane] + ([4 if f['status'] in STATUS_SCORE else 5 for f in frs] if lane == 'compute' else [])) or [7])
        hb = None
        if lane == 'compute':
            fb = max(frs, key=lambda f: f['compute_score'], default=None)
            ib = max([a for a in its if a['lane'] == 'compute'], key=lambda a: a['compute_score'], default=None)
            basis = (f"compute: {fb['id']} {fb['status']} ({fb['lane']}, {fb['group']})" if fb and (not ib or fb['compute_score'] >= ib['compute_score'])
                     else f"compute: {_clean(ib['b']['text'])[:80]}")
        elif lane == 'dispatch':
            ib = max([a for a in its if a['lane'] == 'dispatch'], key=lambda a: a['dispatch_score'])
            basis = f"dispatch T{ib['tier']}: {_clean(ib['b']['text'])[:80]}" + (f" (gates {ib['gates'][0]})" if ib['gates'] else '')
        else:
            hb = next((a for a in its if a['lane'] == 'held' and a['holds']), None)
            basis = "held: " + (hb['holds'][0]['name'] + ' - ' + hb['holds'][0]['lift'][:80] if hb else 'only non-task / blocked boxes')
        rows.append(dict(id=nid, domain=n['domain'], handoff=n['handoff'], open=n['open'], readiness=n['readiness'], dispatch_score=round(ds, 4),
                         compute_score=round(cs, 4), lane=lane, priority=round(pr, 4), tier=tier, basis=basis[:200],
                         lift=(hb['holds'][0]['lift'] if hb else '')))
    rows.sort(key=lambda r: (-r['priority'], r['id']))
    dependents = collections.defaultdict(set)
    for e in DEP:
        dependents[e['to']].add(e['from'])
    for k, r in enumerate(rows, 1):
        r['rank'] = k
        seen, st = set(), list(dependents.get(r['id'], ()))
        while st:
            d = st.pop()
            if d in seen or d == r['id']:
                continue
            seen.add(d); st.extend(dependents.get(d, ()))
        r['unblocks_rows'] = sorted(d for d in seen if NODES.get(d, {}).get('open', 0) > 0)

    # ---- the published orders
    def brief_of(a):
        briefs = curated.get('briefs', {})
        b = briefs.get(a['b']['token']) if a['b']['token'] else None
        if not b:
            b = next((v for k, v in briefs.items() if k in a['b']['text'][:110]), None)
        return ((b or _body(a['b']['text'])[:260]) + ' ' + BRIEF_SUFFIX).strip()

    disp = sorted([a for a in items if a['lane'] == 'dispatch'], key=lambda a: (-a['dispatch_score'], -a['s'], a['key']))
    dispatch_now = []
    for a in disp[:DISPATCH_CAP]:
        p = boxes[a['b']['parent']] if a['b']['parent'] is not None else None
        dispatch_now.append(dict(rank=0, id=a['key'], row=a['row'], task=_clean(a['b']['text'])[:300], hint=f"{a['b']['file']}:{a['b']['line']}",
                                 size=size_class(a['size']), tier=a['tier'], dispatch_score=a['dispatch_score'], gates=a['gates'][:4], owner=a['owner'],
                                 parent=(_clean(p['text'])[:80] if p else None), touched=a['b']['touched'], brief=brief_of(a), source='box'))
    for f in unblock:                                        # a code-blocked / dead-launcher FILLERS row is a dispatch item (operator ruling 10-22)
        dispatch_now.append(dict(rank=0, id=f"filler:{f['id']}", row=(f['rows'] or [None])[0],
                                 task=f"unblock FILLERS row {f['id']}: " + (f['blocker'] or 'launcher pid dead - re-arm so the validator accepts it'),
                                 hint='/mnt/raid0/llm/tmp/compute-flags/FILLERS.md', size=None, tier=1,
                                 dispatch_score=round(.70 + .15 * f['compute_score'], 4), gates=[f"compute: {f['id']} ({f['status']})"],
                                 owner=f['owner'], parent=None, touched=None, brief=(f['decision'][:240] + ' ' + BRIEF_SUFFIX).strip(), source='fillers'))
    dispatch_now = sorted(dispatch_now, key=lambda d: -d['dispatch_score'])[:DISPATCH_CAP]
    for k, d in enumerate(dispatch_now, 1):
        d['rank'] = k

    unq = sorted([a for a in items if a['lane'] == 'compute' and not links.get(a['b']['idx'])], key=lambda a: (-a['compute_score'], a['key']))
    boxes_of_filler = collections.defaultdict(list)
    for a in items:
        for fid in links.get(a['b']['idx'], []):
            boxes_of_filler[fid].append(_clean(a['b']['text'])[:100])
    compute_lane = dict(
        order="RUNNING > BOOKED > ARMED-UNBOOKED > STALE-ARMED > BACKLOG; inside a status: quiet -> atomic long -> builds -> resumable fillers (inference-backlog-scheduling section 3)",
        eta_basis="per lane: greedy packing of declared durations after the running grants end (cpu = 4 quarters, gpu / whole-host = 1 bin); a lower bound that ignores window availability and the cpu / whole-host conflict",
        lanes={ln: dict(eta_end=v['eta_end'], bins=v['bins'], items=[dict(pos=k, id=f['id'], status=f['status'], group=f['group'], shape=f['shape'], min_window=f['min_window'],
                                                          ram_gib=f['ram_gib'], cls=f['cls'], duration=f['duration'][:80], eta_end=f['eta_end'], eta_basis=f['eta_basis'],
                                                          owner=f['owner'], rows=f['rows'], compute_score=f['compute_score'], blocker=f['blocker'],
                                                          gated_by=f['preconds'], decision=f['decision'][:160], boxes=boxes_of_filler.get(f['id'], [])[:3])
                                                     for k, f in enumerate(v['items'], 1)]) for ln, v in lane_order.items()},
        unqueued_inference=[dict(rank=k, id=a['key'], row=a['row'], task=_clean(a['b']['text'])[:200], hint=f"{a['b']['file']}:{a['b']['line']}",
                                 tier=a['tier'], compute_score=a['compute_score'], size=size_class(a['size']),
                                 note=((a['cur'] or {}).get('why') or '')[:200]) for k, a in enumerate(unq[:60], 1)],
        unqueued_total=len(unq))
    held = sorted([a for a in items if a['lane'] == 'held'], key=lambda a: (a['tier'], -(a['dispatch_score'] or a['compute_score']), a['key']))
    hname = lambda a: a['holds'][0]['name'] if a['holds'] else 'blocked-by-box'
    hlift = lambda a: a['holds'][0]['lift'] if a['holds'] else 'its blocker box is ticked: ' + blocker_names(a)
    tcount = collections.Counter(str(a['tier']) for a in items)
    nontask_list = [dict(row=a['row'], hint=f"{a['b']['file']}:{a['b']['line']}", text=_clean(a['b']['text'])[:110], why=a['why_not'][:100])
                    for a in sorted(A.values(), key=lambda a: (a['row'], a['b']['line'])) if not a['is_task'] and not a['why_not'].startswith(('collapsed', 'done, tick'))]
    done_list = [dict(row=A[i]['row'], hint=f"{A[i]['b']['file']}:{A[i]['b']['line']}", task=_clean(A[i]['b']['text'])[:90], done=d_) for i, d_ in done_idx.items()]
    cache_hdr = cache.get('validation') or {}
    doc = {
        "schema": SCHEMA,
        "generated_by": "scripts/handoffs/backlog_priority.py + scripts/handoffs/backlog_priority_curated.json",
        "generated_at": ts(now),
        "queue_snapshot_at": (queue or {}).get('as_of'),
        "source_sha": git.get('head'), "origin_main_sha": git.get('origin_main'), "behind_origin_main": git.get('behind'),
        "curated_entries": len(curated['entries']), "curated_unmatched": len(unmatched), "curated_unmatched_ids": unmatched,
        "classifier_error_rate": cache_hdr.get('error_rate'),
        "classifier": dict(cached_boxes=sum(1 for a in A.values() if a['cached']), open_boxes=len(A), model=cache.get('model')),
        "method": ("Operator method 2026-10-24, rebuilt after the Fable audit. dispatch_now = non-inference boxes that are unblocked, ranked by what they gate "
                   "(explicit anchors only: curated before=, in-box depends/after/precond/blocked-by phrases naming an ID, FILLERS precondition clauses), then size, age, "
                   "non-intake; compute_lane = the FILLERS queue (queue_status.py --json) in the inference-backlog-scheduling packing order per lane with ETA. Row priority "
                   "= max(dispatch_score, compute_score); score = priority; lane records which side won. Holds are box-scoped with lifting conditions; parents collapse into "
                   "children; non-tasks are listed, not ranked. Kind / blocked are keyword heuristics until the classifier cache exists (classifier_error_rate null). "
                   "Advisory ordering: re-read the task TEXT before acting."),
        "tiers": TIER_SHORT, "overrides_file": "handoffs/active/backlog-priority.override.json",
        "counts": dict(boxes_by_tier=dict(sorted(tcount.items())), open_boxes=len(A), tasks=len(items), collapsed_parents=len(collapsed), non_tasks=len(nontask_list),
                       held_by=dict(collections.Counter(hname(a) for a in held).most_common()),
                       fillers_by_status=dict(collections.Counter(f['status'] for f in fillers))),
        "done_pending_tick": done_list, "done_stale": done_stale,
        "dispatch_now": dispatch_now,
        "compute_lane": compute_lane,
        "held": [dict(id=a['key'], row=a['row'], hint=f"{a['b']['file']}:{a['b']['line']}", tier=a['tier'], text=_clean(a['b']['text'])[:100],
                      hold=hname(a), lift=hlift(a)[:140]) for a in held[:400]],
        "non_tasks": nontask_list,
        "rows": {r['id']: {"tier": r['tier'], "rank": r['rank'], "score": r['priority'], "priority": r['priority'], "dispatch_score": r['dispatch_score'],
                           "compute_score": r['compute_score'], "lane": r['lane'], "basis": r['basis'], "unblocks": r['unblocks_rows'][:12],
                           "blocker": (r['lift'] if r['lane'] == 'held' else '')[:120]} for r in rows},
    }
    return dict(doc=doc, items=A, itemlist=items, fillers=fillers, rows=rows, unmatched=unmatched, nontasks=nontask_list, collapsed=collapsed,
                curated=curated, now=now, queue=queue, git=git, boxes=boxes, links=links, state=state, hname=hname, hlift=hlift)


# ---------------------------------------------------------------- check
def check(res: dict | None, path: Path = OUT_DEFAULT, git: dict | None = None) -> tuple[list[str], list[str]]:
    """(problems, notes). Problems fail --check; ``res`` may be None (then only the file + git checks run)."""
    problems, notes = [], []
    git = git if git is not None else git_state()
    if not path.exists():
        return [f"{path.name} is missing: run backlog_priority.py"], notes
    try:
        cur = json.loads(path.read_text(encoding='utf-8'))
    except ValueError as exc:
        return [f"{path.name} is not valid JSON ({exc})"], notes
    if not isinstance(cur, dict) or not isinstance(cur.get('rows'), dict):
        return [f"{path.name} must be an object with a 'rows' object"], notes
    for k in ('generated_at', 'queue_snapshot_at', 'source_sha', 'curated_unmatched', 'classifier_error_rate', 'dispatch_now', 'compute_lane'):
        if k not in cur:
            problems.append(f"{path.name} lacks header field '{k}' (v2 schema): regenerate")
    try:
        gen = datetime.datetime.strptime(str(cur.get('generated_at', '')), '%Y-%m-%dT%H:%MZ').replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        problems.append(f"{path.name} has no parseable generated_at")
        gen = None
    newest = git.get('newest_handoffs_commit')
    if gen and newest:
        lag = (datetime.datetime.fromtimestamp(newest, datetime.timezone.utc) - gen).total_seconds() / 3600
        if lag > STALE_HOURS:
            problems.append(f"{path.name} is {lag:.1f} h older than the newest handoffs/ commit (limit {STALE_HOURS} h): regenerate")
        else:
            notes.append(f"file is {max(0.0, lag):.1f} h behind the newest handoffs/ commit")
    elif gen:
        notes.append("newest handoffs/ commit unknown (no git): staleness not checked")
    if git.get('behind'):
        problems.append(f"this tree is {git['behind']} commit(s) behind origin/main: fetch + rebase before generating or trusting the file")
    elif git.get('behind') is None:
        notes.append("origin/main unknown: behind-check skipped")
    if res is not None:
        n, m = len(res['unmatched']), max(1, len(res['curated']['entries']))
        if n / m > UNMATCHED_LIMIT:
            problems.append(f"{n}/{m} curated entries ({n / m:.0%}) match no open box (limit {UNMATCHED_LIMIT:.0%}): prune " + ', '.join(res['unmatched'][:6]))
        elif n:
            notes.append(f"{n}/{m} curated entries match no open box: " + ', '.join(res['unmatched'][:6]))
        fresh = res['doc']['rows']
        missing = sorted(set(fresh) - set(cur['rows']))
        if missing:
            notes.append(f"{len(missing)} open row(s) missing from the file: {', '.join(missing[:6])}")
        both = [r for r in fresh if r in cur['rows']]
        notes.append(f"tier drift on {sum(1 for r in both if cur['rows'][r].get('tier') != fresh[r]['tier'])}/{len(both)} rows")
    return problems, notes


# ---------------------------------------------------------------- validation sample
def draw_sample(res: dict, n: int, seed: int = 0) -> list[dict]:
    """Stratified sample for the mandatory validation read: T1, T2-top, compute lane, random (n/4 each, topped up at random)."""
    rnd = random.Random(seed)
    items = res['itemlist']
    q = max(1, n // 4)
    t1 = sorted([a for a in items if a['tier'] == 1], key=lambda a: -a['dispatch_score'])
    t2 = sorted([a for a in items if a['tier'] == 2], key=lambda a: -a['dispatch_score'])[:50]
    comp = [dict(filler=True, id=f['id'], row=(f['rows'] or [''])[0], text=f"{f['id']} {f['status']} {f['lane']}/{f['group']}: {f['decision'][:160]}",
                 tier=4 if f['status'] in STATUS_SCORE else 5, blocked=f['blocker'] or '') for f in res['fillers']]
    comp += [a for a in items if a['lane'] == 'compute' and not res['links'].get(a['b']['idx'])]
    out, seen = [], set()

    def add(strat, a):
        if a.get('filler'):
            key, rec = a['id'], dict(stratum=strat, id=a['id'], row=a['row'], text=a['text'], hint='FILLERS.md', tier=a['tier'], kind='I', lane='compute', blocked=a['blocked'])
        else:
            key = a['key']
            bl = '; '.join([f"{h['name']}: {h['lift'][:60]}" for h in a['holds']] + [f"by {A_tok(res, j)}" for j in a['blocked_by']] + [f"row {r}" for r in a['blocked_row']])
            rec = dict(stratum=strat, id=key, row=a['row'], text=_clean(a['b']['text'])[:300], hint=f"{a['b']['file']}:{a['b']['line']}",
                       tier=a['tier'], kind=a['kind'], lane=a['lane'], blocked=bl)
        if key not in seen:
            seen.add(key); out.append(rec)

    for strat, pool in (('T1', t1), ('T2-top', t2), ('compute', comp)):
        for a in rnd.sample(pool, min(q, len(pool))):
            add(strat, a)
    tries = 0
    while len(out) < n and items and tries < 50 * n:
        add('random', rnd.choice(items)); tries += 1
    return out


def A_tok(res, j):
    b = res['boxes'][j]
    return b['token'] or _clean(b['text'])[:30]


def render_sheet(sample: list[dict], res: dict) -> str:
    esc = lambda t: (t or '').replace('|', '/').replace('\n', ' ')
    d = res['doc']
    out = [f"# Backlog-priority validation sample ({len(sample)} boxes)\n",
           f"generated_at {d['generated_at']} | queue_snapshot_at {d['queue_snapshot_at']} | source {str(d['source_sha'])[:9]}\n",
           "Read each box AT ITS file:line (the task TEXT is the identity), then fill the verdict column: `ok` or `wrong: <kind|tier|blocked|hold|non-task|stale>`. "
           "Abort the publish if more than 20 % are wrong and say so; write the measured rate into the cache header `validation.error_rate`.\n",
           "| # | stratum | row | box (first 300 chars) | file:line | tier | kind | lane | blocked / held | verdict |", "|-|-|-|-|-|-|-|-|-|-|"]
    for k, s in enumerate(sample, 1):
        out.append(f"| {k} | {s['stratum']} | {s['row']} | {esc(s['text'])} | `{s['hint']}` | T{s['tier']} | {s['kind']} | {s['lane']} | {esc(s['blocked'])[:120]} |  |")
    return '\n'.join(out) + '\n'


def classifier_batch(res: dict, limit: int | None = None) -> list[dict]:
    out = [dict(hash=a['hash'], row=a['row'], hint=f"{a['b']['file']}:{a['b']['line']}", heading=a['b']['head'], text=a['b']['full'][:1500],
                sub=a['b']['sub'], want="{kind: I|N|O, is_task: bool, blocked_by: [IDs]|null, parent_of: [IDs]}")
           for a in res['items'].values() if not a['cached']]
    return out[:limit] if limit else out


# ---------------------------------------------------------------- rendering
def render_md(res: dict) -> str:
    d = res['doc']
    esc = lambda t: (str(t) if t is not None else '').replace('|', '/').replace('\n', ' ')
    out = [f"# Backlog priority (generated {d['generated_at']}, queue {d['queue_snapshot_at']}, source {str(d['source_sha'])[:9]})\n",
           f"counts: {json.dumps(d['counts'])}\n", "## Dispatch now\n",
           "| # | row | task | hint | size | tier | score | gates | owner |", "|-|-|-|-|-|-|-|-|-|"]
    for x in d['dispatch_now']:
        out.append(f"| {x['rank']} | {x['row']} | {esc(x['task'][:110])} | `{x['hint']}` | {x['size']} | T{x['tier']} | {x['dispatch_score']} | {esc('; '.join(x['gates'])[:80])} | {x['owner'] or ''} |")
    out.append("\n## Compute lane\n")
    for ln, v in d['compute_lane']['lanes'].items():
        out.append(f"### {ln} (ETA {v['eta_end']})\n\n| # | id | status | group | shape | min | RAM | class | ETA | blocker |\n|-|-|-|-|-|-|-|-|-|-|")
        for f in v['items']:
            out.append(f"| {f['pos']} | {f['id']} | {f['status']} | {f['group']} | {esc(f['shape'][:50])} | {f['min_window']} | {f['ram_gib']} | {f['cls']} | {f['eta_end'] or ''} | {esc(f['blocker'] or '')[:60]} |")
    out.append(f"\n### unqueued inference (top {len(d['compute_lane']['unqueued_inference'])} of {d['compute_lane']['unqueued_total']})\n")
    out += [f"- {u['rank']}. {u['row']} T{u['tier']} {esc(u['task'][:110])}" for u in d['compute_lane']['unqueued_inference']]
    out.append("\n## Held (first 400)\n\n| row | tier | hold | lifts when | text |\n|-|-|-|-|-|")
    out += [f"| {h['row']} | T{h['tier']} | {h['hold']} | {esc(h['lift'][:80])} | {esc(h['text'][:70])} |" for h in d['held']]
    out.append(f"\n## Non-tasks (excluded, {len(d['non_tasks'])})\n")
    out += [f"- {n['row']} `{n['hint']}` {esc(n['text'][:80])} - {esc(n['why'])}" for n in d['non_tasks']]
    return '\n'.join(out) + '\n'


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="freshness / consistency; writes nothing")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--md", type=Path, help="also write the readable tables as markdown")
    ap.add_argument("--sample", type=int, metavar="N", help="draw a stratified validation sample and write a review sheet; writes no priority file")
    ap.add_argument("--sheet", type=Path, help="with --sample: write the sheet here (default stdout)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--emit-classifier-batch", type=Path, metavar="FILE", help="write the boxes the classifier cache does not cover as JSONL")
    ap.add_argument("--queue-json", type=Path, help="use a saved queue_status.py --json instead of running it")
    ap.add_argument("--no-queue", action="store_true", help="do not read the host queue (compute lane empty; queue_snapshot_at null)")
    ap.add_argument("--allow-behind", action="store_true", help="generate even though HEAD is behind origin/main")
    ap.add_argument("--fetch", action="store_true", help="git fetch origin first (network)")
    args = ap.parse_args(argv)
    if args.fetch:
        _git('fetch', '-q', 'origin', timeout=120)
    git = git_state()
    queue = None if args.no_queue else (load_queue(args.queue_json) if args.queue_json else 'auto')
    if not args.check and not args.sample and not args.emit_classifier_batch and git.get('behind') and not args.allow_behind:
        print(f"REFUSED: HEAD is {git['behind']} commit(s) behind origin/main; fetch + rebase (or --allow-behind)", file=sys.stderr)
        return 2
    res = build(queue=queue, git=git)
    if args.check:
        problems, notes = check(res, args.out, git)
        for n in notes: print("note:", n)
        for p in problems: print("PROBLEM:", p)
        print(f"{len(problems)} problem(s)")
        return 1 if problems else 0
    if args.sample:
        sheet = render_sheet(draw_sample(res, args.sample, args.seed), res)
        if args.sheet:
            args.sheet.write_text(sheet, encoding='utf-8'); print(f"wrote {args.sheet}")
        else:
            print(sheet)
        return 0
    if args.emit_classifier_batch:
        rows = classifier_batch(res)
        args.emit_classifier_batch.write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n', encoding='utf-8')
        print(f"wrote {args.emit_classifier_batch} ({len(rows)} boxes without a cache entry)")
        return 0
    args.out.write_text(json.dumps(res['doc'], indent=1, ensure_ascii=False) + "\n", encoding='utf-8')
    c = res['doc']['counts']
    print(f"wrote {args.out} ({len(res['rows'])} rows; boxes by tier {c['boxes_by_tier']}; dispatch_now {len(res['doc']['dispatch_now'])}; "
          f"fillers {c['fillers_by_status']}; {len(res['unmatched'])}/{len(res['curated']['entries'])} curated unmatched; queue {res['doc']['queue_snapshot_at']})")
    if args.md:
        args.md.write_text(render_md(res), encoding='utf-8')
        print(f"wrote {args.md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
