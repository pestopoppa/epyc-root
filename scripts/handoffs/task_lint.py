#!/usr/bin/env python3
"""task_lint_v2 — three modes over handoff checkboxes. Regex classification is ADVISORY; an explicit [class] tag or an
execution-type validation against the deliverable wins.

  task_lint_v2.py report   FILE.md ...     every finding, exit 0 always (advisory)
  task_lint_v2.py migrate  FILE.md ...     per-fold gate: a failed a/d/f/h field is OK when the box carries NEEDS-OWNER /
                                           NEEDS-OPERATOR / NEEDS-DECOMPOSITION; NEEDS-OPERATOR is never itself a failure;
                                           an already-issued authorization is not an operator decision; exit 1 only on
                                           an UNTAGGED failure
  task_lint_v2.py publish  FILE.md:LINE    rowflow publish gate for ONE box: class must be inference (explicit or
                                           validated), identity complete (model, build, harness, metric+direction, rule,
                                           region, est), est may be `provisional` ONLY with a bounded pilot clause (a plain
                                           numeric est passes; no run citation is required);
                                           NEEDS-* present -> refuse; non-inference deliverable -> refuse. exit 1 on refuse
Changes vs task_lint.py (2026-11-02 second-pass review §1): (i) execution-type validator — the deliverable decides, not a
metric mention (scorer/build/wire/implement/audit/replay/read-only => non-inference even if 't/s' appears; measure/run/
compare/A/B/floor/calibrat/sweep on a model => inference); (ii) authorization classes — pending-choice vs historical-ruling
vs standing-constraint vs issued-authorization; only pending-choice is NEEDS-OPERATOR; (iii) estimate rule — a first
experiment passes with `est: provisional` + `pilot:` clause; (iv) field d reports the NAMED prerequisite text, never a
program gate; (v) numeric children are refused: a roll-up must be tagged `[roll-up]` and is non-dispatchable."""
import re, sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import task_lint_core as L1   # v1 regexes, path checks and block parser

TAGS = re.compile(r'NEEDS-(OWNER|OPERATOR|DECOMPOSITION)')
ROLLUP = re.compile(r'\[roll-up\]|\(roll-up', re.I)
NONINF_DELIV = re.compile(r'\b(scorer|grader|parser|adapter|writer|reader|hook|schema|fixture|unit test|test(?:s)? pass|wire|implement|refactor|'
                          r'port(?:ing)?\b(?!.{0,20}\b(?:bench|measure))|land|merge|commit|rename|delete|document|write-?up|read-?only|zero[- ]inference|'
                          r'no inference|offline|replay (?:of|over) (?:retained|banked|stored|saved)|re-?segment|re-?score|re-?judge|'
                          r'disagreement analysis|reconcil|audit\b|census|lint|register|ingest|emit .{0,30}rows)\b', re.I)
INF_DELIV = re.compile(r'\b(measure|re-?measure|calibrat|floor|sweep|A/B|A/A|ABA|bake-?off|compare .{0,40}\b(?:model|quant|arm|backend)|'
                       r'run (?:the |a |an )?(?:\w+ )?(?:suite|bench|eval|campaign|arm|cohort|screen|smoke|pilot|window|row)|'
                       r'llama-bench|decode .{0,20}t/s|tg128|pp512|generation comparison|recording run|collect .{0,30}(?:responses|transcripts|completions)|'
                       r'run \w[\w-]* against (?:our|the) (?:local )?(?:endpoint|server|model)|benchmark .{0,30}(?:endpoint|model))\b', re.I)
AUTH_ISSUED = re.compile(r'operator decision \d{4}-\d{2}-\d{2}|(operator|coordinator)[^.\n]{0,60}(authori[sz]ed|approved|ruled|ruling|decided|ratified|directive|go-ahead|granted)|'
                         r'(authori[sz]ed|approved|ratified|decided) (?:by the )?(operator|coordinator)|operator \d{4}-\d{2}-\d{2}:|\bruling Q\d\b|OP-[A-Z0-9-]+ (?:DECIDED|APPLIED)', re.I)
STANDING = re.compile(r'STANDING CONSTRAINT|standing (?:rule|constraint|hold)|DO NOT LAUNCH|hold \(operator|operator hold|human-amendment-only', re.I)
PENDING = re.compile(r'(operator|owner)[^.\n]{0,40}\b(to decide|must decide|decides?|decision (?:owed|pending|package)|choose|pick|select|sign(?:s|-off)?|ratif(?:y|ies))\b|'
                     r'awaiting operator|pending operator|needs operator|OPERATOR DECISION|decide whether|choose between|implement or procure', re.I)
EST = re.compile(r'\best(?:imate)?[:\s]\s*(provisional|~?\d+)', re.I)
SUFF = re.compile(r'\bstop(?:[- ]rule|[- ]on[- ]answer|[- ]on[- ]futility|/continue)\b|\bsufficiency\b|\bfutility\b|\bstop contract\b', re.I)
PILOT = re.compile(r'\bpilot\b.{0,80}\b(bounded|n\s?=\s?\d+|\d+\s?(?:items|rows|prompts|min|h)\b)', re.I)

def own_block(text):
    """The box's OWN text: its first line plus continuation lines, EXCLUDING nested checkbox descendants and their
    continuations (a child's requirements or authorizations must not classify the parent)."""
    out, skip_indent = [], None
    for i, l in enumerate(text.split('\n')):
        if i == 0: out.append(l); continue
        m = L1.CHECKBOX.match(l)
        if m: skip_indent = len(m.group(1)); continue
        if skip_indent is not None and (len(l) - len(l.lstrip()) > skip_indent or not l.strip()): continue
        skip_indent = None; out.append(l)
    return '\n'.join(out)

def exec_type(text):
    """(class, basis). Explicit tag > deliverable validation > v1 regex (advisory)."""
    m = re.search(r'\[(non-inference|inference|operator-decision|blocked-external)\]', text)
    if m: return m.group(1), 'explicit'
    head = text.split('\n')[0]
    ni, inf = bool(NONINF_DELIV.search(head)), bool(INF_DELIV.search(head))
    if ni and not inf: return 'non-inference', 'deliverable'
    if inf and not ni: return 'inference', 'deliverable'
    cls, *_ = L1.score(text)
    return cls, 'advisory-regex' + ('-conflict' if ni and inf else '')

UNRESOLVED = re.compile(r'(operator|owner)[^.\n]{0,40}\b(to decide|must decide|must choose|to choose|should choose|choose between|decides? whether|picks?|selects?)\b|'
                        r'awaiting operator|pending operator|needs operator|NEEDS-OPERATOR|decision (?:owed|pending|package)|OPERATOR DECISION(?!\s+\d{4}-\d{2}-\d{2})|implement or procure|'
                        r'\bor\b .{0,40}\bwhichever the operator', re.I)

def decision_kind(text):
    # An UNRESOLVED choice is detected independently of any approval: an earlier authorization never suppresses it.
    if UNRESOLVED.search(text): return 'pending-choice'
    if STANDING.search(text): return 'standing-constraint'
    if AUTH_ISSUED.search(text): return 'issued-authorization'
    if PENDING.search(text): return 'pending-choice'
    if L1.OPER.search(text): return 'historical-ruling' if re.search(r'\d{4}-\d{2}-\d{2}', text) else 'pending-choice'
    return None

def score2(text, children=0):
    text = own_block(text)
    cls, basis = exec_type(text)
    _, f, dang, miss, pre = L1.score(text, children)
    dk = decision_kind(text)
    f['h'] = dk == 'pending-choice'
    if cls == 'operator-decision' and dk != 'pending-choice':   # an issued ruling is not a decision box: classify by the work it names
        head = text.split('\n')[0]
        cls, basis = ('inference', 'deliverable-after-authorization') if INF_DELIV.search(head) or L1.INFER.search(text) else ('non-inference', 'deliverable-after-authorization')
    f['c'] = bool(miss) if cls == 'inference' else False
    if cls == 'inference' and 'estimate' in miss:
        e = EST.search(text)
        if e and (e.group(1).isdigit() or (e.group(1).lower() == 'provisional' and PILOT.search(text))): miss = [x for x in miss if x != 'estimate']; f['c'] = bool(miss)
    if cls == 'inference' and re.search(r'\best(?:imate)?[:\s]\s*provisional', text, re.I) and not PILOT.search(text):
        if 'estimate' not in miss: miss = miss + ['estimate']; f['c'] = True
    f['b'] = basis.endswith('conflict')
    f['s'] = cls == 'inference' and not SUFF.search(text)   # sufficiency: an inference task states its stop rule
    tags = sorted(set(TAGS.findall(text)))
    roll = bool(ROLLUP.search(text))
    numeric_child = bool(re.match(r'^\s*[-*] \[ \]\s*\*\*[A-Z][A-Z0-9-]*-[A-Z0-9.]*\d\.\d+\*\*', text.split('\n')[0]))
    return {'class': cls, 'class_basis': basis, 'fails': [k for k, v in f.items() if v], 'missing_c': miss, 'dangling': dang,
            'named_prereq': pre, 'decision_kind': dk, 'tags': tags, 'rollup': roll, 'numeric_child': numeric_child}

def boxes(path):
    lines = open(path, encoding='utf-8', errors='replace').read().split('\n')
    for i, l in enumerate(lines):
        m = L1.CHECKBOX.match(l)
        if m and m.group(2) == ' ':
            txt, ch = L1.block(lines, i); yield i + 1, txt, ch

def run_report(paths):
    for p in paths:
        for ln, txt, ch in boxes(p):
            r = score2(txt, ch); print(f"{p}:{ln}: {'OK' if not r['fails'] else 'FAIL ' + ','.join(r['fails'])} [{r['class']}/{r['class_basis']}]"
                                       + (f" decision={r['decision_kind']}" if r['decision_kind'] else '') + (f" tags={r['tags']}" if r['tags'] else ''))
    return 0

def run_migrate(paths):
    bad = 0
    for p in paths:
        for ln, txt, ch in boxes(p):
            r = score2(txt, ch)
            hard = [k for k in r['fails'] if k in ('a', 'd', 'f', 'h', 's')]
            if r['numeric_child']: print(f"{p}:{ln}: REFUSE numeric child id (split must name a disjoint deliverable)"); bad += 1; continue
            if r['rollup'] and not re.search(r'non-dispatchable|do not dispatch', txt, re.I): print(f"{p}:{ln}: REFUSE roll-up without non-dispatchable marker"); bad += 1; continue
            if hard and not r['tags']: print(f"{p}:{ln}: UNTAGGED FAIL {','.join(hard)} [{r['class']}]"); bad += 1
            elif hard: print(f"{p}:{ln}: tagged {r['tags']} fails={hard} (allowed)")
    return 1 if bad else 0

# What each identity field needs, so a refusal names the exact edit (ws58 2026-11-02).
FIELD_HINT = {
    'model': 'model: name it (e.g. Qwen3.8-27B, Q38FN, DS41, gemma)',
    'quant_build': 'quant_build: the quant or build (e.g. Q8_0, IQ4_XS, v10 production, champion, experimental build)',
    'metric': 'metric: what is measured, with direction (e.g. decode t/s, higher is better)',
    'rule': 'rule: the decision rule (keep if / threshold / floor / descriptive, no verdict)',
    'region': 'region: where it runs (CPU quarter Q0-Q3, whole-host, GPU/MI210)',
    'estimate': 'estimate: `est <N> s`, or `est: provisional` plus a bounded `pilot:` (n=<k>, <k> prompts, <k> min)',
}


def missing_fields_text(miss):
    return '; '.join(FIELD_HINT.get(m, m) for m in miss)


def publish_text(txt, ch=0):
    r = score2(txt, ch); why = []
    if r['tags']: why.append(f"NEEDS tags present {r['tags']}")
    if r['class'] != 'inference': why.append(f"class {r['class']} ({r['class_basis']}) — non-inference payload refused "
                                             "(state the run/measurement the row performs, or tag the box [inference])")
    if r['missing_c']: why.append(f"identity incomplete: {r['missing_c']} — add {missing_fields_text(r['missing_c'])}")
    if 's' in r['fails']: why.append('no sufficiency/stop rule stated — add `stop-on-answer when <condition>; stop-on-futility on <condition>; '
                                     'gate-class = futility-only` (inference task must say stop-on-answer / stop-on-futility)')
    if r['rollup']: why.append('roll-up is non-dispatchable')
    if 'h' in r['fails'] or r['decision_kind'] == 'pending-choice': why.append('pending operator choice (field h) — route to the operator queue first')
    if 'd' in r['fails']: why.append(f"untestable prose prerequisite: {r['named_prereq']!r}")
    if r['decision_kind'] == 'standing-constraint': why.append('standing constraint / operator hold named in the box')
    return why

def run_publish(spec):
    p, ln = spec.rsplit(':', 1); ln = int(ln)
    lines = open(p, encoding='utf-8', errors='replace').read().split('\n'); txt, ch = L1.block(lines, ln - 1)
    why = publish_text(txt, ch)
    print(f"{spec}: {'PUBLISHABLE' if not why else 'REFUSE — ' + '; '.join(why)}")
    return 1 if why else 0

if __name__ == '__main__':
    a = sys.argv[1:]
    if not a or a[0] not in ('report', 'migrate', 'publish'): print(__doc__); sys.exit(2)
    sys.exit({'report': lambda: run_report(a[1:]), 'migrate': lambda: run_migrate(a[1:]), 'publish': lambda: run_publish(a[1])}[a[0]]())
