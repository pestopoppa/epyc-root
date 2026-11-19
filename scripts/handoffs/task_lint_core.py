#!/usr/bin/env python3
"""task_lint.py — score handoff checkbox tasks against the executability rubric (ws58, 2026-11-02).

Usage:
  task_lint.py FILE.md [...]            lint open tasks in working-tree handoff files (exit 1 if any FAIL)
  task_lint.py --audit MANIFEST.json    score every open task in the backlog-refactor manifest at its
                                        pinned sha; writes refinements JSON + stats JSON next to it
  --json                                machine-readable output for FILE mode

Rubric fields (see task-readiness-audit-20261102.md):
  a deliverable/done-criterion  b class inferable  c inference identity (model, quant/build, metric,
  rule, region, estimate, inputs)  d prereqs named as IDs  e size (one turn / one row)
  f no dangling refs  g owner handoff/track  h no hidden operator decision
"""
import json, os, re, subprocess, sys, collections

WS = '/workspace'
REPOS = {'': WS, 'repos/epyc-orchestrator/': WS + '/repos/epyc-orchestrator',
         'repos/epyc-inference-research/': WS + '/repos/epyc-inference-research'}
RETIRED = [r'data/stt-cs8-public-20261030', r'data/openmementos', r'backups/episodic-leak-20260917',
           r'Qwen2\.5-Coder-32B[-_A-Za-z0-9.]*Q4_K_M', r'/mnt/raid0/llm/tmp/(?:wt|worktree)[^\s`]*',
           r'\.claude/worktrees/[^\s`]+']

CHECKBOX = re.compile(r'^(\s*)[-*] \[( |x|X|~|>|!)\]\s?(.*)$')
TID = re.compile(r'\b(?:[A-Z][A-Z0-9]{1,8}-[A-Z]?\d{1,4}[a-z]?|[A-Z]{1,2}\d{1,3}[a-z]?)\b')
DONE = re.compile(r'done[- ]when|done:|DoD|deliverable|acceptance|accept(?:ed)? (?:if|when)|exit criteri|'
                  r'result_path|→\s*`|->\s*`|output:|produces?\b|writes?\b|commit(?:s|ted)?\b|land(?:s|ed)?\b|'
                  r'publish|record(?:s|ed)?\b|file[sd]?\b|tick when|closes? when|PASS|keep if|verdict|'
                  r'add(?:s)?\b|creat|implement|fix|wire|delete|remove|rename|move|update', re.I)
ASSESS_ONLY = re.compile(r'^\W*(?:\*\*[^*]+\*\*\W*)?(?:assess|evaluate|investigate|consider|explore|review|'
                         r'look into|think about|study|understand|scope|survey|decide whether)\b', re.I)
INFER = re.compile(r'llama-bench|\bbench(?:mark)?(?:ed|ing)?\b|\bA/B\b|\bsweep\b|\bppl\b|perplexit|'
                   r't/s\b|tok/s|tokens?/s|\bdecode (?:A/B|t/s|at depth)|rowflow|launcher|'
                   r'CPU[- ]quarter|whole[- ]host|on (?:the )?(?:GPU|MI210)|\bsmoke\b|\bn ?= ?\d{2,}|\bpass@|'
                   r'(?:scored|eval) run|\barms?\b.{0,40}\bvs\b|run .{0,30}(?:suite|harness)', re.I)
OPER = re.compile(r'operator (?:to |must |should |will )?(?:decid|approv|choos|ratif|sign|confirm|pick|select|rule)|'
                  r'ask (?:the )?operator|NEEDS-OPERATOR|operator(?:\'s)? (?:call|decision|ruling|sign-?off|approval)|'
                  r'awaiting operator|pending operator|operator-gated|needs operator|operator ratif|'
                  r'operator[- ]review|operator .{0,30}decision|decide whether|choose between|implement or procure|'
                  r'\bor\b .{0,40}\bwhichever the operator', re.I)
EXTERNAL = re.compile(r'upstream (?:merge|release|PR)|waiting (?:on|for) (?:upstream|vendor|release|the 2nd GPU|second GPU)|'
                      r'post-2nd-GPU|after .{0,30}(?:released|ships)|blocked-external|hardware arriv', re.I)
PROSE_PREREQ = re.compile(r'\b(?:if validated|only if|until then|deferred|parked|after|once|requires?|depends? on|blocked (?:on|by)|prereq\w*|gated? (?:on|by)|'
                          r'needs? .{0,20}first|when .{0,40} (?:lands|is done|completes))\b', re.I)
SUB = {
    'model': re.compile(r'Qwen|gemma|DS41|Q38FN|GLM|Llama|MiniMax|Mistral|DeepSeek|Phi|\b\d{1,3}(?:\.\d)?B\b|'
                        r'architect|worker|coder|frontdoor|drafter|whisper|qwentts|\bmodel\b', re.I),
    'quant_build': re.compile(r'\bI?Q\d_\w+|IQ\d|bf16|\bf16|Q8_0|MXFP4|v10|v11|champion|production|experimental|'
                              r'\b[0-9a-f]{9,40}\b|build|kernel', re.I),
    'metric': re.compile(r't/s|tok/s|tokens?/s|accuracy|ppl|perplex|pass@|latency|alpha|acceptance rate|'
                         r'TTFT|WER|score|throughput|speedup|%|\bms\b|RSS|VRAM', re.I),
    'rule': re.compile(r'decision[_ ]rule|keep if|reject if|≥|>=|<=|≤|threshold|floor|gate|PASS|FAIL|'
                       r'win if|beats?|no regression|within \d|CI\b|significan', re.I),
    'region': re.compile(r'quarter|whole[- ]host|GPU|MI210|NUMA|node ?\d|cpu_shape|\bQ[0-3]\b|96 threads|CPU-only', re.I),
    'estimate': re.compile(r'estimate_s|\best\b|~?\d+(?:\.\d+)?\s?(?:min|minutes|h|hours|hrs|s|sec)\b|ETA', re.I),
}
PATHRE = re.compile(r'`([^`\s]+)`')
PATH_OK = re.compile(r'^(?:/|\.{0,2}/?[\w.-]+/)[\w./@+-]*[\w/]$')


def git_tree(root, ref='origin/main'):
    try:
        out = subprocess.run(['git', '-C', root, 'ls-tree', '-r', '--name-only', '-t', ref],
                             capture_output=True, text=True, timeout=120).stdout
        return set(out.split('\n'))
    except Exception:
        return set()


_TREES = None


def trees():
    global _TREES
    if _TREES is None:
        _TREES = {k: git_tree(v) for k, v in REPOS.items()}
    return _TREES


def path_exists(p):
    if any(c in p for c in '<>*{}$|') or '...' in p or p.startswith('http'):
        return None  # placeholder / pattern -> not checkable
    p = p.split(':')[0].split('#')[0].rstrip('/')
    if not p or '/' not in p:
        return None
    if p.startswith('/'):
        if os.path.exists(p):
            return True
        if p.startswith('/workspace/'):
            rel = p[len('/workspace/'):]
        elif p.startswith('/mnt/raid0/llm/'):
            rel = None
        else:
            return None if not p.startswith('/mnt') else False
        if rel is None:
            return False
        p = rel
    for pre, base in REPOS.items():
        cand = p[len(pre):] if pre and p.startswith(pre) else p
        if cand in trees()[pre] or os.path.exists(os.path.join(base, cand)):
            return True
    for base in (WS + '/repos/epyc-orchestrator', WS + '/repos/epyc-inference-research', '/mnt/raid0/llm',
                 '/mnt/raid0/llm/llama.cpp', '/mnt/raid0/llm/llama.cpp-experimental', '/mnt/raid0/llm/whisper.cpp',
                 '/mnt/raid0/llm/qwentts.cpp'):
        if os.path.exists(os.path.join(base, p)):
            return True
    # bare filenames with a dir that is clearly not a repo path (e.g. module.attr) -> uncheckable
    if not re.search(r'\.(md|py|sh|json|jsonl|yaml|yml|toml|txt|tsv|csv|gguf|log|html|cpp|c|h|cu|hip)$|/$', p) \
            and not p.split('/')[0] in ('data', 'scripts', 'docs', 'handoffs', 'artifacts', 'benchmarks',
                                         'wiki', 'agents', 'src', 'measurement', 'research', 'models', 'backups'):
        return None
    return False


def block(lines, i):
    """checkbox line i plus its continuation (deeper-indented, non-checkbox) lines."""
    m = CHECKBOX.match(lines[i])
    ind = len(m.group(1)) if m else 0
    out, j, children = [lines[i]], i + 1, 0
    while j < len(lines):
        l = lines[j]
        if not l.strip():
            break
        cm = CHECKBOX.match(l)
        if l.lstrip().startswith('#') or (cm and len(cm.group(1)) <= ind):
            break
        if cm:
            children += 1
        elif len(l) - len(l.lstrip()) <= ind and not l.startswith(' '):
            break
        out.append(l)
        j += 1
    return '\n'.join(out), children


def section_context(lines, i, radius=60):
    lo = i
    while lo > 0 and not lines[lo].startswith('#'):
        lo -= 1
    hi = i + 1
    while hi < len(lines) and not lines[hi].startswith('#') and hi - i < radius:
        hi += 1
    return lo, hi


def score(text, children=0, owner=True, nested=False):
    t = text
    f = {}
    first = CHECKBOX.match(t.split('\n')[0])
    body = first.group(3) if first else t
    is_inf = bool(INFER.search(t))
    is_op = bool(OPER.search(t))
    is_ext = bool(EXTERNAL.search(t))
    explicit = re.search(r'\[(non-inference|inference|operator-decision|blocked-external)\]', t)
    cls = explicit.group(1) if explicit else ('operator-decision' if is_op and not is_inf else
                                             'blocked-external' if is_ext else
                                             'inference' if is_inf else 'non-inference')
    # a
    f['a'] = (len(body.strip(' *')) < 12 and not children) or not bool(DONE.search(t)) or (bool(ASSESS_ONLY.search(body)) and not re.search(
        r'done[- ]when|deliverable|acceptance|→|->|result_path|verdict', t, re.I))
    # b: class ambiguous (signals for >1 class, no explicit tag)
    f['b'] = (not explicit) and (is_inf + is_op + is_ext) >= 2
    # c
    miss = []
    if cls == 'inference':
        miss = [k for k, rx in SUB.items() if not rx.search(t)]
    f['c'] = bool(miss)
    # d
    pm = PROSE_PREREQ.search(t)
    f['d'] = bool(pm) and not TID.search(t[pm.start():pm.start() + 160])
    # e
    steps = len(re.findall(r'(?:^|\s)\(?(?:\d{1,2}|[a-h])[).]\s', t)) + len(re.findall(r'; then|, then', t))
    f['e'] = len(t) > 1500 or children > 6 or steps >= 6 or bool(re.search(r'\(ongoing\)|\[too-big|~?\d+ days|split across', t, re.I))
    # f
    dang = []
    for rx in RETIRED:
        for mm in re.finditer(rx, t):
            dang.append(mm.group(0))
    for p in PATHRE.findall(t):
        if PATH_OK.match(p) and path_exists(p) is False:
            dang.append(p)
    f['f'] = bool(dang)
    f['g'] = not owner
    f['h'] = is_op  # operator-decision class also routes to the operator queue, never to a worker
    return cls, f, sorted(set(dang)), miss, (t[pm.start():pm.start() + 120] if f['d'] else None)


def lint_file(path, as_json=False):
    lines = open(path, encoding='utf-8', errors='replace').read().split('\n')
    res = []
    for i, l in enumerate(lines):
        m = CHECKBOX.match(l)
        if not m or m.group(2) != ' ':
            continue
        txt, ch = block(lines, i)
        cls, f, dang, miss, pre = score(txt, ch)
        fails = [k for k, v in f.items() if v]
        res.append({'line': i + 1, 'class': cls, 'fails': fails, 'dangling': dang, 'missing_c': miss})
    if as_json:
        print(json.dumps({'file': path, 'tasks': res}, indent=1))
    else:
        for r in res:
            if r['fails']:
                print(f"{path}:{r['line']}: FAIL {','.join(r['fails'])} [{r['class']}]"
                      + (f" dangling={r['dangling']}" if r['dangling'] else '')
                      + (f" c-missing={r['missing_c']}" if r['missing_c'] else ''))
        n = len(res); ok = sum(1 for r in res if not r['fails'])
        print(f"{path}: {ok}/{n} open tasks executable as-is")
    return all(not r['fails'] for r in res)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == '--audit':
        import task_audit  # noqa: driver lives beside this file
        task_audit.main(a[1])
        sys.exit(0)
    js = '--json' in a
    ok = all([lint_file(p, js) for p in a if p != '--json'])
    sys.exit(0 if ok else 1)
