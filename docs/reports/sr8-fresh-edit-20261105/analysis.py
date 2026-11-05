#!/usr/bin/env python3
"""Fail-closed analysis for the SR-8 prepared paired edit comparison.

Not an inference worker. Input records must be authenticated by the native
capture system; this arithmetic cannot prove the process or GPU residency.
"""
import math

ARMS = ('plain', 'current_dflash2', 'prompt_lookup')


def analyze_sr8(rows, schedule):
    if len(schedule) != 5 or len({x['task'] for x in schedule}) != 5 or {x['rep'] for x in schedule} != set(range(1, 6)):
        raise ValueError('invalid predeclared schedule')
    tasks={x['rep']: x['task'] for x in schedule}
    expected={(rep,tasks[rep],arm) for rep in range(1,6) for arm in ARMS}
    indexed={}
    for row in rows:
        key=(row.get('rep'),row.get('task'),row.get('arm'))
        if key not in expected or key in indexed or row.get('status')!='ok':
            raise ValueError('missing, duplicate or invalid observation')
        if row.get('temperature') != 0 or row.get('fresh_server') is not True or row.get('gpu_residency') is not True:
            raise ValueError('sampling, fresh server or residency unproven')
        if row.get('edit_validity') != 'PASS':
            raise ValueError('synthetic edit validity missing or failed')
        t=row.get('decode_tps')
        if type(t) not in (float,int) or not math.isfinite(t) or t <= 0:
            raise ValueError('invalid decode speed')
        if key[2]!='plain':
            rounds, accepted, drafted = row.get('draft_rounds'), row.get('accepted'), row.get('drafted')
            if (type(rounds)!=int or rounds<0 or type(accepted)!=int or accepted<0 or
                    type(drafted)!=int or drafted<accepted or drafted<rounds or (rounds == 0 and (drafted != 0 or accepted != 0)) or (rounds > 0 and drafted == 0)):
                raise ValueError('missing acceptance count')
        indexed[key]=row
    if set(indexed)!=expected:
        raise ValueError('incomplete paired cohort')
    comparisons=[]
    for rep in range(1,6):
        task=tasks[rep]
        base=indexed[rep,task,'current_dflash2']; lookup=indexed[rep,task,'prompt_lookup']
        comparisons.append({'rep':rep,'task':task,'ratio':lookup['decode_tps']/base['decode_tps']})
    # Equal-weight log ratio makes each matched task-repetition one unit.
    ratio=math.exp(sum(math.log(x['ratio']) for x in comparisons)/len(comparisons))
    summary = {}
    for arm in ARMS:
        observations = [r for k,r in indexed.items() if k[2] == arm]
        entry = {'mean_decode_tps':sum(r['decode_tps'] for r in observations)/len(observations)}
        if arm != 'plain':
            rounds=sum(r['draft_rounds'] for r in observations)
            entry['zero_proposal_requests'] = sum(r['drafted'] == 0 for r in observations)
            entry['mean_accepted_draft_tokens'] = sum(r['accepted'] for r in observations)/rounds if rounds else None
            entry['mean_emitted_per_verified_round'] = 1.0 + entry['mean_accepted_draft_tokens'] if rounds else None
        summary[arm] = entry
    return {'arms':summary,'n_pairs':len(comparisons),'paired_geometric_mean_ratio':ratio,'candidate_threshold_met':ratio>=1.5,
            'comparisons':comparisons,'scope':'arithmetic only; requires verified runtime, corpus and correctness before any routing decision'}
