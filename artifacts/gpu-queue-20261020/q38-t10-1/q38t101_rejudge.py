#!/usr/bin/env python3
"""CPU-only re-judge of a q38t101 run dir with the patched draft_n guard (missing draft_n == 0 drafts).
usage: q38t101_rejudge.py <rundir>  -> writes <rundir>/judge_line.rejudged.json; original judge_line.json/summary.json untouched."""
import importlib.util, json, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('q38c', '/mnt/raid0/llm/tmp/gpu-staged-20261020/q38t101_control.py')
m = importlib.util.module_from_spec(spec); sys.dont_write_bytecode = True; spec.loader.exec_module(m)
d = Path(sys.argv[1]); old = json.loads((d / 'summary.json').read_text())
arms = {k: [json.loads(l) for l in (d / f'{k}.records.jsonl').read_text().splitlines() if l.strip()]
        for k in ('off_A', 'off_B', 'iv_spec_default', 'i_nmax0', 'iii_nmax0_concurrent')}
n = len(arms['off_A']); assert all(len(v) == n for v in arms.values())
aa = m.compare(arms['off_A'], arms['off_B'])
cmp = {k: m.compare(arms['off_A'], arms[k]) for k in ('i_nmax0', 'iii_nmax0_concurrent', 'iv_spec_default')}
g = {'guard_i_all_draft_n_zero': all((r['draft_n'] or 0) == 0 for r in arms['i_nmax0']),
     'guard_iii_fg_draft_n_zero': all((r['draft_n'] or 0) == 0 for r in arms['iii_nmax0_concurrent']),
     'guard_spec_live_default_draft_n_total': sum((r['draft_n'] or 0) for r in arms['iv_spec_default']),
     'guard_iii_prompts_with_overlapping_speculating_bg': sum(1 for r in arms['iii_nmax0_concurrent'] if r.get('bg_overlapping_with_drafts', 0) > 0),
     'guard_iii_bg_errors': [r['id'] for r in arms['iii_nmax0_concurrent'] if r.get('bg_error')]}
g_ok = (g['guard_i_all_draft_n_zero'] and g['guard_iii_fg_draft_n_zero'] and g['guard_spec_live_default_draft_n_total'] > 0
        and g['guard_iii_prompts_with_overlapping_speculating_bg'] == n and not g['guard_iii_bg_errors'])
ident = cmp['i_nmax0']['identical_count'] == n and cmp['iii_nmax0_concurrent']['identical_count'] == n
verdict = 'VOID_AA' if aa['identical_count'] != n else ('VOID_GUARDS' if not g_ok else ('PASS' if ident else 'FAIL'))
if not old.get('all_server_pids_dead'): verdict = 'ERROR_PIDS_NOT_DEAD' if verdict in ('PASS', 'FAIL') else verdict
out = {'verdict': verdict, 'rejudged_from': str(d), 'original_verdict': old.get('verdict'), 'n': n,
       'aa': {k: aa[k] for k in ('identical_count', 'n')}, **{f'{k}_vs_off': {kk: v[kk] for kk in ('identical_count', 'n')} for k, v in cmp.items()},
       'guards_ok': g_ok, **g, 'pids_dead': old.get('all_server_pids_dead')}
(d / 'judge_line.rejudged.json').write_text(json.dumps(out, indent=1)); print(json.dumps(out))
