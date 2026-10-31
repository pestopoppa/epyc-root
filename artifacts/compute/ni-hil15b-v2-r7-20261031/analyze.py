#!/usr/bin/env python3
"""Aggregate exact frozen HIL15b-v2 slots; no quality verdict on partial data."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

SOURCE = Path('/mnt/raid0/llm/worktrees/mains/codex-ni-orchestrator')
EPYC_ROOT = Path('/mnt/raid0/llm/tmp/codex-ni-ap-legacy-status-wrap-20261030')
sys.path.insert(0, str(SOURCE))
from src.trace.dependency_features import auc_table, load_runs

D = Path(__file__).resolve().parent
subprocess.run(['/usr/bin/python3', str(D/'verify_source.py')], check=True)
tasks = json.loads((D / 'hil15b_v2_tasks.json').read_text())
assert hashlib.sha256((D / 'hil15b_v2_tasks.json').read_bytes()).hexdigest() == '0089c2a840bc40367433de754424b17ad9a5edca954b312513e6ecaa0abd4312'
cal = {t['task_key'] for t in json.loads((D / 'calibration_tasks.json').read_text())}
held = {t['task_key'] for t in json.loads((D / 'heldout_tasks.json').read_text())}
assert len(tasks) == 20 and len(cal) == 16 and len(held) == 4 and cal.isdisjoint(held)
out = D / 'out'
labels = {}
runs = {}
per = {}
unknown = []
for rep in range(3):
    for t in tasks:
        key = t['task_key']; rid = f'{key}-r{rep}'
        slot = out / 'slots' / rid
        complete = slot / 'COMPLETE.json'
        if not complete.exists():
            unknown.append(rid)
            continue
        m = json.loads((slot / 'native' / 'manifest.json').read_text())
        assert m['verdict'] == 'OK' and len(m['runs']) == 1 and m['runs'][0]['run_id'] == rid
        assert m['join']['joined_outcome'] == m['join']['task_runs'] == 1
        assert m['replay_verify'][rid]['rc'] == 0
        passed = bool(m['runs'][0]['pass'])
        labels[rid] = (key, passed)
        per.setdefault(key, []).append(passed)
        loaded = load_runs(slot / 'native' / 'events.sqlite')
        assert set(loaded).issubset({rid})
        runs.update(loaded)

def section(keys):
    rows = [v for k in keys for v in per.get(k, [])]
    return {'tasks': len(keys), 'complete_attempts': len(rows), 'passes': sum(rows),
            'failed': len(rows)-sum(rows), 'unknown_attempts':sum(3-len(per.get(k,[])) for k in keys)}

full = not unknown
assessment = {'schema':'hil15b_v2_frozen60_assessment/v1', 'frozen_taskset_sha256':'0089c2a840bc40367433de754424b17ad9a5edca954b312513e6ecaa0abd4312',
              'calibration':section(cal),'heldout':section(held),'total':section(cal|held),
              'unknown_slot_ids':unknown,'per_task':{k:{'completed':len(per.get(k,[])),
                        'passes':sum(per.get(k,[])),'rate_3':(sum(per[k])/3 if len(per.get(k,[]))==3 else None)}
                        for k in [t['task_key'] for t in tasks]},
              'full_original_denominator':full,'partial':not full,
              'answer_metric_direction':'higher_better',
              'tool_conformance':'separate from exact-final answer grade'}
if full:
    band = sum(1 for v in per.values() if sum(v) in (1,2))
    assessment['variance_tasks'] = band
    assessment['band_16_to_20'] = band >= 16
    assessment['spectrum_target_about_10'] = band >= 10
    assessment['failed_recording_count'] = assessment['total']['failed']
    assessment['hil16a_three_failed_recordings'] = assessment['total']['failed'] >= 3
    assessment['global_auc_table'] = auc_table(runs, labels)
    auc_path = out / 'auc_table.json'
    auc_path.write_text(json.dumps(assessment['global_auc_table'], indent=2)+'\n')
    if assessment['global_auc_table'].get('status') != 'insufficient':
        sys.path.insert(0, str(EPYC_ROOT/'scripts'/'vidya'))
        from adapters.hil15a_auc import write_belief_measurements
        first = json.loads((out/'slots'/f"{tasks[0]['task_key']}-r0"/'native'/'manifest.json').read_text())
        carrier = {'schema':'hil15b_v2_aggregate/v1','mock':False,
                   'hashseed':first['hashseed'],'flags':first['flags'],
                   'label_classes':['False','True'],'served_model':first['served_model']}
        sidecar = write_belief_measurements(out, run_id='hil15b-v2-frozen60-r1',
                    producer='hil15b_v2_frozen60/analyze.py', auc_table_path=auc_path,
                    manifest=carrier)
        assessment['auc_belief_sidecar'] = str(sidecar)
    else:
        assessment['auc_belief_sidecar'] = None
        assessment['auc_belief_refusal'] = 'native combined AUC insufficient; no measurement tuple emitted'
    assessment['verdict'] = 'full measured cohort; band pass' if band >= 16 else 'full measured cohort; band miss'
else:
    assessment['verdict'] = 'INCONCLUSIVE: original-denominator slots incomplete; unknowns are not failures or successes'
(out / 'ASSESSMENT.json').write_text(json.dumps(assessment, indent=2)+'\n')
print(json.dumps({'verdict':assessment['verdict'],'total':assessment['total']},indent=2))
