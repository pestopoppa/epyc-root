#!/usr/bin/env python3
"""CAP-02 HIL deterministic scans over the stored flag-on recordings (BRF-T3-2, zero inference, read-only on the evidence).

STOP RULE (declared before any number was computed; docs/guides/agent-workflows/measurement-sufficiency.md):
  Question/decision: do the stored CAP-02 recordings (HIL-15b flag-on run, 80 runs; HIL-18a spectrum run, 120 replays), re-read with the
  CURRENT unchanged orchestrator code (95d663e5), reproduce the filed L2 scan, dependency-AUC, spectrum ranking and recording-verify results,
  and does the scan alone cover each consumer box's acceptance? | evidence already usable: yes, both runs are KEEP-listed on disk |
  units: every run/replay (census, no sampling), strata = task key | minimum coverage: all 80 + all 120 | looks: ONE pass per scan,
  no thresholds changed; bootstrap seeds as filed (l2_scan seed 0 / B 1000; hil15c/d floors unchanged, 2000 draws seed 0) |
  stop: when every scan has been compared leaf-for-leaf against its filed artefact (mismatches reported, never papered over) |
  inconclusive: a scan that cannot be reproduced, or a coverage shortfall against the box's own acceptance | cap: one process, 1 core |
  records: this JSON + RESULT lines on stdout | gate or diagnostic: diagnostic (operational reading), no gate verdict.

Inputs are copied to a scratch dir with sha256 before/after; originals are never opened for write.
Usage: cap02_rescan.py CODE_DIR SCRATCH_DIR OUT.json CODE_PRE13E_DIR   (CODE_PRE13E_DIR = git archive of 13e693a4^, the pre-fix scanner the filed spectrum report was built under; run with the orchestrator venv python; CODE_DIR = git-archive of orchestrator 95d663e5)
"""
import collections, glob, hashlib, json, os, random, re, shutil, subprocess, sys
CODE, SCR, OUT, CODE_OLD = sys.argv[1:5]
sys.path.insert(0, CODE)
os.chdir(CODE)
T = '/mnt/raid0/llm/tmp'
D15 = f'{T}/hil15b-flagon-out/run-20261023T220108Z/driver'
D18 = f'{T}/hil18a-spectrum-out/run/driver'
TASKS = f'{T}/fillers-3c4ca599/jobs/hil15b_tasks.json'
V16 = f'{T}/hil16a-verify-out/check-20261023T234638Z/result.json'
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
ins = {'hil15b_events.sqlite': f'{D15}/events.sqlite', 'hil15b_labels.json': f'{D15}/labels.json', 'hil15b_outcomes.jsonl': f'{D15}/progress/outcomes.jsonl',
       'hil15b_tasks.json': TASKS, 'hil18a_events.sqlite': f'{D18}/events.sqlite', 'hil18a_replays.jsonl': f'{D18}/replays.jsonl',
       'filed_l2_report_hil15c.json': f'{D15}/l2_report_hil15c.json', 'filed_l2_report.json': f'{D15}/l2_report.json', 'filed_auc_table.json': f'{D15}/auc_table.json',
       'filed_spectrum_report.json': f'{D18}/spectrum_report.json', 'filed_hil16a_verify.json': V16,
       'filed_hil15c_eval.json': f'{T}/hil15c-20261024/hil15c_eval.json', 'filed_hil15d_eval.json': f'{T}/hil15d-20261024/hil15d_eval.json'}
os.makedirs(f'{SCR}/in', exist_ok=True)
hashes = {}
for k, p in ins.items():
    hashes[k] = {'path': p, 'sha256': sha(p)}
    shutil.copy(p, f'{SCR}/in/{k}')
    assert sha(f'{SCR}/in/{k}') == hashes[k]['sha256']
os.makedirs(f'{SCR}/in/progress', exist_ok=True); shutil.copy(f'{SCR}/in/hil15b_outcomes.jsonl', f'{SCR}/in/progress/outcomes.jsonl')

def cmp(a, b, path='', st=None, tol=1e-12):
    """leaf-for-leaf comparison; returns dict(n, mismatches[list of first 20 paths], max_abs_float_diff)"""
    st = st or {'n': 0, 'bad': [], 'max': 0.0}
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b: st['bad'].append(f'{path}/{k}: key only in ' + ('recomputed' if k in a else 'filed'))
            else: cmp(a[k], b[k], f'{path}/{k}', st)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b): st['bad'].append(f'{path}: len {len(a)} vs {len(b)}')
        for i, (x, y) in enumerate(zip(a, b)): cmp(x, y, f'{path}[{i}]', st)
    else:
        st['n'] += 1
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
            st['max'] = max(st['max'], abs(a - b))
            if abs(a - b) > tol: st['bad'].append(f'{path}: {a} vs {b}')
        elif a != b: st['bad'].append(f'{path}: {a!r} vs {b!r}')
    return st
def summ(st): return {'leaves_compared': st['n'], 'mismatches': len(st['bad']), 'first_mismatches': st['bad'][:12], 'max_abs_float_diff': st['max']}

res = {'schema': 'brf-t3/cap02-rescan/1', 'orchestrator_code': '95d663e50e35b2636c7a945ec1dc05df50a1a846 (git archive src+scripts+config; filed L2 scan used 13e693a4, an ancestor)', 'inputs': hashes}
PY = sys.executable
# ---- S1: HIL-13 / HIL-15c: L2 scan CLI over the HIL-15b flag-on run (exact filed command shape)
out1 = f'{SCR}/l2_report_rescan.json'
r = subprocess.run([PY, 'scripts/trace/l2_scan.py', '--step-db', f'{SCR}/in/hil15b_events.sqlite', '--progress-logs', f'{SCR}/in/progress/*.jsonl',
                    '--tasks', f'{SCR}/in/hil15b_tasks.json', '--out', out1], capture_output=True, text=True)
res['S1_l2_scan_hil15b'] = {'rc': r.returncode, 'stderr': r.stderr.strip().splitlines()[-3:]}
rep = json.load(open(out1)); filed = json.load(open(f'{SCR}/in/filed_l2_report_hil15c.json')); filed0 = json.load(open(f'{SCR}/in/filed_l2_report.json'))
res['S1_l2_scan_hil15b']['vs_filed_hil15c_report'] = summ(cmp(rep, filed))
res['S1_l2_scan_hil15b']['vs_filed_original_l2_report_pre13e693a4'] = summ(cmp(rep, filed0))
res['S1_l2_scan_hil15b']['report_top_keys'] = sorted(rep)
res['S1_l2_scan_hil15b']['report_excerpt'] = {k: rep[k] for k in rep if k in ('n_traces', 'n_step_bearing', 'denominators', 'counts', 'category_counts', 'category_precision_vs_outcome', 'categories')}

# ---- S1b: same scan on the HIL-18a replays (outcomes from replays.jsonl, as hil15d did), in-process
from src.trace.l2.detectors import DetectorConfig, detect
from src.trace.l2.loaders import apply_tool_required, load_step_events, tool_required_map
from src.trace.l2.model import L2Trace
from src.trace.l2.report import dumps, scan
from src.trace.l2.schemas import export_tool_schemas
ents = [json.loads(l) for l in open(f'{SCR}/in/hil18a_replays.jsonl')]
base = {e['run_id']: L2Trace(trace_id=e['run_id'], task_key=e['task_key'], outcome=e['outcome']) for e in ents}
tr18 = [t for t in load_step_events(f'{SCR}/in/hil18a_events.sqlite', base) if t.trace_id in base]
apply_tool_required(tr18, tool_required_map(json.load(open(f'{SCR}/in/hil15b_tasks.json'))))
rep18 = json.loads(dumps(scan(tr18, DetectorConfig(schemas=export_tool_schemas()), seed=0, B=1000)))
json.dump(rep18, open(f'{SCR}/l2_report_hil18a_rescan.json', 'w'), indent=1, sort_keys=True)
res['S1b_l2_scan_hil18a'] = {'replays_in_manifest': len(ents), 'step_bearing': len(tr18), 'outcomes': dict(collections.Counter(t.outcome for t in tr18)), 'report': rep18}

# ---- S2: HIL-15c / HIL-15d evaluation scripts, filed code unchanged except path constants redirected to scratch
def run_eval(src, outname, tag):
    code = open(src).read()
    code = code.replace('ORCH = "/mnt/raid0/llm/epyc-orchestrator"', f'ORCH = "{CODE}"')
    code = code.replace('"/mnt/raid0/llm/tmp/hil15c-20261024/hil15c_eval.json"', f'"{SCR}/{outname}"').replace('OUT = "/mnt/raid0/llm/tmp/hil15d-20261024"', f'OUT = "{SCR}"')
    code = code.replace('"/hil15d_eval.json"', f'"/{outname}"')
    p = f'{SCR}/{tag}_patched.py'; open(p, 'w').write(code)
    rr = subprocess.run([PY, p], capture_output=True, text=True, cwd=SCR)
    return rr, json.load(open(f'{SCR}/{outname}'))
r15c, e15c = run_eval(f'{T}/hil15c-20261024/hil15c_eval.py', 'hil15c_eval_rescan.json', 'hil15c')
r15d, e15d = run_eval(f'{T}/hil15d-20261024/hil15d_eval.py', 'hil15d_eval_rescan.json', 'hil15d')
res['S2_hil15c_eval'] = {'rc': r15c.returncode, 'vs_filed': summ(cmp(e15c, json.load(open(f'{SCR}/in/filed_hil15c_eval.json'))))}
res['S2_hil15d_eval'] = {'rc': r15d.returncode, 'vs_filed': summ(cmp(e15d, json.load(open(f'{SCR}/in/filed_hil15d_eval.json'))))}
res['S2_hil15c_eval']['summary'] = {k: e15c[k] for k in e15c if k in ('premature_wrap_up', 'zero_step_violation', 'no_final_step', 'labels_total', 'labels_failed', 'runs_with_tool_dependency', 'failed_with_tool_dependency', 'step_bearing', 'no_tool_runs', 'no_tool_fail')}
res['S2_hil15d_eval']['summary'] = {k: v for k, v in e15d.items() if not isinstance(v, (list, dict)) or k in ('universe_A', 'universe_B', 'A', 'B', 'no_final_step', 'premature_wrap_up', 'zero_step_violation')}

# ---- S3: HIL-15 dependency AUC table (src.trace.dependency_features) re-derived
from src.trace.dependency_features import auc_table, load_runs
labels = json.load(open(f'{SCR}/in/hil15b_labels.json'))
auc = auc_table(load_runs(f'{SCR}/in/hil15b_events.sqlite'), {k: (v[0], bool(v[1])) for k, v in labels.items()})
auc = json.loads(json.dumps(auc))
res['S3_hil15_auc'] = {'vs_filed': summ(cmp(auc, json.load(open(f'{SCR}/in/filed_auc_table.json')))), 'table': auc,
                       'tasks_total_in_run': len({re.sub(r"-r\d+$", "", k) for k in labels}), 'runs_total': len(labels), 'failed_total': sum(1 for v in labels.values() if not v[1])}

# ---- S4: HIL-18a spectrum ranking report re-derived from replays.jsonl + events.sqlite
from src.trace.spectrum_replay import build_report as sp_build, dumps as sp_dumps, load_manifest, traces_for_manifest
man = [json.loads(l) for l in open(f'{SCR}/in/hil18a_replays.jsonl')]
per_task, acct = traces_for_manifest(f'{SCR}/in/hil18a_events.sqlite', man)
sp = json.loads(sp_dumps(sp_build(per_task, acct, n_tasks=10, min_replays=20, top_m=3, human=None)))
sp_filed = json.load(open(f'{SCR}/in/filed_spectrum_report.json'))
res['S4_hil18a_spectrum'] = {'vs_filed': summ(cmp(sp, sp_filed)), 'tasks_reported': sp['tasks_reported'], 'target_tasks': sp['target_tasks'], 'join': sp['join'],
                             'tasks_skipped': sp['tasks_skipped'], 'usable_tasks': [t['ranking']['task_key'] for t in sp['tasks'] if t['ranking'].get('usable')],
                             'per_task_pass_fail': {t['ranking']['task_key']: [t['ranking']['n_pass'], t['ranking']['n_fail']] for t in sp['tasks']},
                             'l2_agreement_pooled': sp['l2_agreement_pooled'], 'human_overlap_sample': 'not supplied (--human absent): HIL-12 item 6 sample is a labelled-set obligation, not stored evidence'}

# ---- S4b: attribute the S4 l2_agreement drift: rebuild the spectrum report under the PRE-13e693a4 scanner (child process, old code) and compare to filed
sub = f'''
import json, sys
sys.path.insert(0, {CODE_OLD!r})
from src.trace.spectrum_replay import build_report, dumps, traces_for_manifest
man = [json.loads(l) for l in open({SCR + '/in/hil18a_replays.jsonl'!r})]
pt, acct = traces_for_manifest({SCR + '/in/hil18a_events.sqlite'!r}, man)
print(dumps(build_report(pt, acct, n_tasks=10, min_replays=20, top_m=3, human=None)))
'''
ro = subprocess.run([PY, '-c', sub], capture_output=True, text=True, cwd=CODE_OLD)
sp_old = json.loads(ro.stdout)
res['S4_hil18a_spectrum']['pre13e693a4_scanner_vs_filed'] = summ(cmp(sp_old, sp_filed))
def strip(r): return {'tasks': [t['ranking'] for t in r['tasks']], 'join': r['join'], 'skipped': r['tasks_skipped'], 'n': r['tasks_reported']}
res['S4_hil18a_spectrum']['ranking_subtree_current_vs_filed'] = summ(cmp(strip(sp), strip(sp_filed)))

# ---- S5: HIL-16a offline recording verification re-run (CAS + hash chain; no model)
from src.trace.replay.cas import CAS
from src.trace.replay.model import load_run, verify_integrity
cas15 = CAS(f'{D15}/cas')
ids = sorted(labels)
unclean, nturns = {}, 0
for rid in ids:
    run = load_run(f'{SCR}/in/hil15b_events.sqlite', rid)
    nturns += len(run.turns)
    pr = verify_integrity(run, cas15)
    if pr: unclean[rid] = pr[:3]
filed16 = json.load(open(f'{SCR}/in/filed_hil16a_verify.json'))
res['S5_hil16a_verify'] = {'recordings': len(ids), 'turns': nturns, 'unclean': unclean, 'failed_task_recordings_clean': sum(1 for k in ids if not labels[k][1] and k not in unclean),
                           'filed_recordings': filed16['recordings'], 'filed_unclean': filed16['unclean'], 'filed_failed_clean': filed16['failed_task_recordings_clean'],
                           'agrees_with_filed': (len(ids) == filed16['recordings'] and not unclean and not filed16['unclean'])}
# inputs unchanged
res['inputs_unchanged_after'] = all(sha(h['path']) == h['sha256'] for h in hashes.values())
json.dump(res, open(OUT, 'w'), indent=1, sort_keys=True, default=str)
for k in ('S1_l2_scan_hil15b', 'S2_hil15c_eval', 'S2_hil15d_eval', 'S3_hil15_auc', 'S4_hil18a_spectrum'):
    print(k, 'rc', res[k].get('rc'), json.dumps(res[k]['vs_filed'] if 'vs_filed' in res[k] else res[k]['vs_filed_hil15c_report']))
print('S1 vs original pre-13e', json.dumps(res['S1_l2_scan_hil15b']['vs_filed_original_l2_report_pre13e693a4']))
print('S5', json.dumps({k: v for k, v in res['S5_hil16a_verify'].items()}))
print('inputs_unchanged_after', res['inputs_unchanged_after'])
