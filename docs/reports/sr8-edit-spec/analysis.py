#!/usr/bin/env python3
"""Fail-closed analysis for the SR-8 prepared paired edit comparison.

Not an inference worker. Input records must be authenticated by the native
capture system; this arithmetic cannot prove the process or GPU residency.
"""
import math

ARMS = ('plain', 'current_dflash2', 'prompt_lookup')
TASKS = ('t2_add_and_use','t3_method_and_caller','t4_rename_module','t5_bugfix')

def analyze_sr8(rows):
    expected={(rep,TASKS[(rep-1)%len(TASKS)],arm) for rep in range(1,6) for arm in ARMS}
    indexed={}
    for row in rows:
        key=(row.get('rep'),row.get('task'),row.get('arm'))
        if key not in expected or key in indexed or row.get('status')!='ok':
            raise ValueError('missing, duplicate or invalid observation')
        if row.get('temperature') != 0 or row.get('fresh_server') is not True or row.get('gpu_residency') is not True:
            raise ValueError('sampling, fresh server or residency unproven')
        if row.get('edit_validity') != 'PASS':
            raise ValueError('canonical edit validity missing or failed')
        t=row.get('decode_tps')
        if type(t) not in (float,int) or not math.isfinite(t) or t <= 0:
            raise ValueError('invalid decode speed')
        if key[2]!='plain':
            rounds, accepted, drafted = row.get('draft_rounds'), row.get('accepted'), row.get('drafted')
            if (type(rounds)!=int or rounds<=0 or type(accepted)!=int or accepted<0 or
                    type(drafted)!=int or drafted<accepted or drafted<rounds):
                raise ValueError('missing acceptance count')
        indexed[key]=row
    if set(indexed)!=expected:
        raise ValueError('incomplete paired cohort')
    comparisons=[]
    for rep in range(1,6):
        task=TASKS[(rep-1)%len(TASKS)]
        base=indexed[rep,task,'current_dflash2']; lookup=indexed[rep,task,'prompt_lookup']
        comparisons.append({'rep':rep,'task':task,'ratio':lookup['decode_tps']/base['decode_tps']})
    # Equal-weight log ratio makes each matched task-repetition one unit.
    ratio=math.exp(sum(math.log(x['ratio']) for x in comparisons)/len(comparisons))
    summary = {}
    for arm in ARMS:
        observations = [r for k,r in indexed.items() if k[2] == arm]
        entry = {'mean_decode_tps':sum(r['decode_tps'] for r in observations)/len(observations)}
        if arm != 'plain':
            entry['mean_accepted_draft_tokens'] = sum(r['accepted'] for r in observations)/sum(r['draft_rounds'] for r in observations)
            entry['mean_emitted_per_verified_round'] = 1.0 + entry['mean_accepted_draft_tokens']
        summary[arm] = entry
    return {'arms':summary,'n_pairs':len(comparisons),'paired_geometric_mean_ratio':ratio,'candidate_threshold_met':ratio>=1.5,
            'comparisons':comparisons,'scope':'arithmetic only; requires verified runtime, corpus and correctness before any routing decision'}
