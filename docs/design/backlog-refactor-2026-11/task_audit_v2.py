#!/usr/bin/env python3
"""task_audit_v2 — regenerate refinements + stats from the manifest at ONE pinned sha with the second-pass rules:
 - a derived field must come from the task's OWN block (same box + continuation lines); a neighbouring line proves
   location, not applicability -> NEEDS-OWNER instead;
 - class = task_lint_v2.exec_type (explicit tag > deliverable validation > advisory regex);
 - field d: resolve the prerequisite the task NAMES (a task id inside the named phrase, or a box in the same handoff whose
   title shares >=2 significant words with the phrase); program relationships are recorded separately as program_gate
   and NEVER substituted;
 - field h: pending-choice -> NEEDS-OPERATOR; issued-authorization / historical-ruling / standing-constraint are recorded,
   not re-queued;
 - field e: NEEDS-DECOMPOSITION with the box's existing named children listed; no numeric split;
 - estimate: a first experiment may carry `est: provisional` with a bounded pilot clause."""
import json, re, os, sys, collections, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import task_lint as L1, task_lint_v2 as L2
OUT = os.path.dirname(os.path.abspath(__file__)) + '/'
W = '/mnt/raid0/llm/worktrees/ws58-fable-audit'
STOP = set('the a an of on in to for and or with from by at is are be as this that its it before after once only if then any all'.split())
def words(s): return {w for w in re.findall(r'[a-z0-9][a-z0-9_.-]{2,}', s.lower()) if w not in STOP}

def main(manifest):
    m = json.load(open(manifest)); sha = m['pinned_sha']; s12 = sha[:12]
    files = {}
    def lines_of(path):
        if path not in files: files[path] = open(W + '/' + path, errors='replace').read().split('\n')
        return files[path]
    tasks = [t for t in m['tasks'] if t['class'] == 'dispatchable']
    recs, stats, by_dom, kinds = [], collections.Counter(), collections.defaultdict(collections.Counter), collections.Counter()
    boxes_by_file = collections.defaultdict(list)
    for t in m['tasks']:
        p, ln = t['src'].split('@')[0].rsplit(':', 1); boxes_by_file[p].append((int(ln), t['task_id'], t['text']))
    for t in tasks:
        path, ln = t['src'].split('@')[0].rsplit(':', 1); ln = int(ln); lines = lines_of(path)
        txt, ch = L1.block(lines, ln - 1)
        r = L2.score2(txt, ch); cls = r['class']; fails = r['fails']
        dom = (t.get('dest_file') or 'unrouted').replace('.md', '')
        stats['open'] += 1; stats['class:' + cls] += 1; by_dom[dom]['open'] += 1
        if r['decision_kind']: kinds[r['decision_kind']] += 1
        for k in fails: stats['fail:' + k] += 1; by_dom[dom]['fail:' + k] += 1
        if not fails: stats['executable'] += 1; by_dom[dom]['executable'] += 1; continue
        prop, flags = {}, set(); own = txt   # OWN block only
        if 'a' in fails:
            k = re.search(r'(done when|→|->|result_path|verdict|PASS|keep if|deliverable)', own, re.I)
            prop['a'] = ('derive from own block: ' + own[max(0, k.start() - 40):k.end() + 100].strip()) if k else 'NEEDS-OWNER: state the artifact/commit/verdict that ticks this box'
            if not k: flags.add('NEEDS-OWNER')
        if 'b' in fails: prop['b'] = f'execution type conflicts ({r["class_basis"]}); owner tags [{cls}] or corrects'; flags.add('NEEDS-OWNER')
        if 'c' in fails:
            sub = {}
            for s in r['missing_c']:
                k = L1.SUB[s].search(own)
                sub[s] = ('derive from own block: ' + own[max(0, k.start() - 30):k.end() + 60].strip()) if k else ('provisional allowed with a bounded pilot clause' if s == 'estimate' else 'NEEDS-OWNER')
                if not k: flags.add('NEEDS-OWNER')
            prop['c'] = sub
        if 'd' in fails:
            pre = r['named_prereq'] or ''
            tid = L1.TID.search(pre); hit = None
            if tid: hit = tid.group(0)
            else:
                pw = words(pre)
                for bl, bid, btxt in boxes_by_file[path]:
                    if bl != ln and bid and len(pw & words(btxt)) >= 2: hit = f'{bid} ({path}:{bl})'; break
            prop['d'] = (f'gate: {hit} (resolved from the NAMED prerequisite "{pre[:80]}")' if hit else f'NEEDS-OWNER: name the task ID behind "{pre[:80]}"')
            if not hit: flags.add('NEEDS-OWNER')
            prop['program_gate'] = t.get('track_gate') or []   # recorded separately, never substituted
        if 'e' in fails:
            kids = [bid for bl, bid, _ in boxes_by_file[path] if bid and bl > ln and bl <= ln + 40 and lines[bl - 1].startswith(' ')]
            prop['e'] = f'NEEDS-DECOMPOSITION: define child outputs + acceptance first; existing named children: {kids[:8]}; roll-up stays non-dispatchable; never split numerically'
            flags.add('NEEDS-DECOMPOSITION')
        if 'f' in fails: prop['f'] = f'verify then resolve or flag MISSING: {r["dangling"]}'; flags.add('NEEDS-OWNER')
        if 'h' in fails:
            prop['h'] = 'pending operator choice -> operator queue entry; worker box gated on it'; flags.add('NEEDS-OPERATOR')
        if r['decision_kind'] and r['decision_kind'] != 'pending-choice': prop['decision_kind'] = r['decision_kind'] + ' (recorded, not re-queued)'
        recs.append({'id': t['id'], 'task_id': t['task_id'], 'src': t['src'], 'class': cls, 'class_basis': r['class_basis'], 'failed': fails,
                     'decision_kind': r['decision_kind'], 'proposed': prop, 'flags': sorted(flags),
                     'destination': {'file': t.get('dest_file'), 'section': t.get('dest_section'), 'new_row': t.get('new_row'), 'route': 'apply during atomic fold commit'}})
    json.dump({'pinned_sha': sha, 'generated': '2026-11-02', 'rubric': 'task-readiness-audit-20261102.md + second-pass rules (v2)', 'n_open': stats['open'],
               'n_deficient': len(recs), 'decision_kinds': kinds, 'tasks': recs}, open(OUT + 'task-readiness-refinements-20261102.json', 'w'), indent=1)
    json.dump({'stats': stats, 'decision_kinds': kinds, 'by_domain': by_dom}, open(OUT + 'task-readiness-stats-20261102.json', 'w'), indent=1)
    print(json.dumps(stats, indent=0)); print('decision kinds', dict(kinds))

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else OUT + 'backlog-refactor-manifest-20261102.json')
