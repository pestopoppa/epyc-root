#!/usr/bin/env python3
"""Synthetic-only qualification. No external inputs, native CLI, or inference entry."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent

def custody():
    for line in (BASE/'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1)
        path = BASE/name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError('custody failure: '+name)

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class Refused(ValueError): pass

def guarded_analyze(payload, plan, native, guard):
    if payload.get('synthetic_only') is not True or plan.get('synthetic_only') is not True:
        raise Refused('synthetic provenance required')
    if json.dumps(payload.get('geo'), sort_keys=True) != json.dumps(plan['geo'], sort_keys=True):
        raise Refused('geometry differs from sealed plan')
    results = payload.get('results')
    if not isinstance(results, dict) or set(results) != set(plan['launches']):
        raise Refused('launch set differs from sealed plan')
    for launch, expected in plan['launches'].items():
        cells = results[launch]
        if not isinstance(cells, dict) or set(cells) != set(expected):
            raise Refused('cell set differs from sealed plan')
        for cid, geometry in expected.items():
            cell = cells[cid]
            if not isinstance(cell, dict): raise Refused('cell is not an object')
            for key, value in geometry.items():
                actual = cell.get(key)
                if type(actual) is not type(value) or actual != value:
                    raise Refused('cell identity/geometry differs from sealed plan')
        errors = guard.validate_launch(cells, list(expected), length=plan['geo']['L'],
                     swa_cells=plan['geo']['swa_cells'], mutant_partial=launch=='mut_partial_noop')
        if errors: raise Refused('; '.join(errors))
    # Nothing in the native judge, including pooled spread, runs until ALL launches pass.
    return native.analyze(results, payload['geo'], prior_191a=None, rules=plan['rules'])

def main():
    if len(sys.argv)!=3 or sys.argv[2] not in ('smoke','full'): raise SystemExit('exclusive smoke output directory required')
    mode=sys.argv[2]
    out = Path(sys.argv[1])
    if out.name != 'worker' or out.parent.parent != BASE/'out' or not out.parent.name.startswith(mode+'-'):
        raise SystemExit('exclusive qualification output boundary')
    out.mkdir(exist_ok=False)
    custody()
    plan = json.loads((BASE/'plan.json').read_text())
    raw = (BASE/'fixture.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != plan['fixture_sha256']: raise RuntimeError('fixture custody')
    payload = json.loads(raw)
    guard = load('preflight_bound',BASE/'preflight.py')
    native = load('kpf174_bound',BASE/'native/kpf174/kpf174_swa_drafter.py')
    calls=[]
    original_analyze=native.analyze
    original_spread=native.k13.acceptance_spread
    def entered(*a,**kw):
        calls.append('analyze')
        return original_analyze(*a,**kw)
    def spread(*a,**kw):
        calls.append('acceptance_spread')
        return original_spread(*a,**kw)
    native.analyze=entered
    native.k13.acceptance_spread=spread
    def boundary():
        if (BASE/'STOP').exists(): raise RuntimeError('STOP')
        custody()
    boundary()
    reference=original_analyze(payload['results'],payload['geo'],prior_191a=None,rules=plan['rules'])
    calls.clear()
    delegated=guarded_analyze(payload,plan,native,guard)
    if delegated!=reference or not calls or calls[0]!='analyze': raise RuntimeError('delegation equality/order')
    actual={k:v['verdict'] for k,v in delegated['launches'].items()}
    if actual!=plan['expected_launch_verdicts']: raise RuntimeError('synthetic native mutant sensitivity')
    cases=[]
    controls=plan['controls'] if mode=='full' else ['missing_launch']
    for case in controls:
        boundary(); mutated=copy.deepcopy(payload)
        launch=mutated['results']['mut_partial_noop']; cid=next(iter(launch)); cell=launch[cid]
        if case=='missing_launch': del mutated['results']['flag_on']
        elif case=='extra_launch': mutated['results']['unknown']={}
        elif case=='rename_id': launch['synthetic-renamed']=launch.pop(cid)
        elif case=='geometry_group': cell['group']=902
        elif case=='geometry_junction': cell['c']=18
        elif case=='geometry_suffix': cell['S']=4
        elif case=='incomplete_later_launch': cell['arms'].pop()
        elif case=='unknown_source': cell['arms'][1]['fork_src_slot']=None
        elif case=='wrong_pruning': cell['pruned']=False
        elif case=='missing_control': cell['controls'].pop()
        else: raise RuntimeError('undeclared mutation')
        calls.clear()
        try: guarded_analyze(mutated,plan,native,guard)
        except Refused as exc:
            if calls: raise RuntimeError('native entered before structural refusal')
            cases.append({'case':case,'refused':True,'native_entries':list(calls),'reason':str(exc)})
        else: raise RuntimeError('mutation escaped: '+case)
    boundary()
    result={'schema':'epyc.kpf174.integration-qualification.v1','classification':'SMOKE_ONLY' if mode=='smoke' else 'MODEL_FREE_QUALIFICATION',
            'synthetic_only':True,'historical_rejudgment':False,'native_equality':True,
            'launch_verdicts':actual,'cases':cases,'progress':len(cases)}
    (out/'QUALIFICATION.json').write_text(json.dumps(result,indent=2)+'\n')
    custody()

if __name__=='__main__': main()
