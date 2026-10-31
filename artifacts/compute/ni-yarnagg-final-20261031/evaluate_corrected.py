#!/usr/bin/env python3
"""Read-only native integrity audit and repair analysis for the predeclared YARN-AGG run."""
import hashlib, importlib.util, json, shutil, sys, tempfile
from pathlib import Path

PACKET=Path(__file__).resolve().parent
SRC=Path('/mnt/raid0/llm/tmp/codex-ni-yarn-agg1g-prep-20261031')
RUN=SRC/'run'
sys.path.insert(0,str(PACKET/'archive'))
from scripts.benchmark.yarn_gate import agg_scoring

spec=importlib.util.spec_from_file_location('corrected_subset_extract',PACKET/'subset_extract.py')
subset_mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(subset_mod)

def read_jsonl(p): return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def score(rows): return {r['item_id']:r['score'] for r in rows}
def summarize(a0,a1): return agg_scoring.net_paired_mcnemar(a0,a1,alpha=0.05,right_at=1.0)
def fail(msg): raise AssertionError(msg)

def validate_full():
    plan=json.loads((RUN/'plan/plan.json').read_text())
    decision=json.loads((RUN/'decision.json').read_text())
    if plan['n_items'] != 141 or decision['status'] != 'FINAL': fail('full plan/decision incomplete')
    if plan['plan_sha256'] != decision['plan_sha256'] or plan['plan_sha256'] != 'dc8fa414b5e50328d294fe6d4b9a32fe5bea97b98a727808c37ceb5c4f4ade68': fail('plan identity mismatch')
    complete=(RUN/'COMPLETE').read_text()
    if sha(RUN/'decision.json') not in complete: fail('COMPLETE does not bind decision hash')
    items=read_jsonl(RUN/'plan/items.jsonl')
    if len(items)!=141 or len({r['item_id'] for r in items})!=141: fail('plan item count/uniqueness')
    expected={r['item_id']:r for r in items}
    arms={}
    for arm in ('A0','A1'):
        path=RUN/'results'/f'{arm}.jsonl'; rows=read_jsonl(path)
        if sha(path)!=decision['results_sha256'][arm]: fail(f'{arm} result digest mismatch')
        if len(rows)!=141 or len({r['item_id'] for r in rows})!=141: fail(f'{arm} results partial/duplicate')
        by={}
        for r in rows:
            i=r['item_id']; planned=expected.get(i)
            if planned is None: fail(f'unplanned {arm} item {i}')
            if r['arm']!=arm or r['status']!='ok' or r['plan_sha256']!=plan['plan_sha256']: fail(f'non-final {arm} item {i}')
            for key in ('prompt_sha256','cell','segment','gate'):
                if r.get(key)!=planned.get(key): fail(f'{arm} plan/result {key} mismatch for {i}')
            if r.get('zone')!='native' or r.get('n_source')!='server_timings': fail(f'{arm} non-native/unmeasured item {i}')
            tm=r.get('timings') or {}; pn=tm.get('prompt_n'); cn=tm.get('cache_n') or 0
            if not isinstance(pn,int) or not isinstance(cn,int) or r.get('real_n')!=pn+cn: fail(f'{arm} served prompt_n/cache_n mismatch for {i}')
            if r.get('usage',{}).get('prompt_tokens') != r['real_n']: fail(f'{arm} usage/real_n mismatch for {i}')
            if not isinstance(r['score'],(int,float)) or isinstance(r['score'],bool): fail(f'{arm} nonnumeric score for {i}')
            by[i]=r
        if set(by)!=set(expected): fail(f'{arm} exact planned set incomplete')
        arms[arm]=by
    full=summarize(score(list(arms['A0'].values())),score(list(arms['A1'].values())))
    if full != decision['pooled_native']: fail('recomputed full paired result differs from native decision')
    return plan,decision,arms,full

def negative_controls():
    outcomes={}
    for name,kind in [('missing_pair','missing'),('prompt_hash_mismatch','prompt'),('served_count_mismatch','count')]:
        with tempfile.TemporaryDirectory(prefix='yarn-native-negative-',dir=PACKET) as td:
            out=Path(td)/'run';(out/'plan').mkdir(parents=True);(out/'results').mkdir()
            for rel in ('plan/plan.json','plan/items.jsonl','decision.json'):
                shutil.copy2(RUN/rel,out/rel)
            for arm in ('A0','A1'): shutil.copy2(RUN/'results'/f'{arm}.jsonl',out/'results'/f'{arm}.jsonl')
            d=json.loads((out/'decision.json').read_text())
            target='A0'; rows=read_jsonl(out/'results'/f'{target}.jsonl')
            idx=next(i for i,r in enumerate(rows) if r['segment']=='new_oolong')
            if kind=='missing': rows.pop(idx)
            elif kind=='prompt': rows[idx]['prompt_sha256']='0'*64
            else: rows[idx]['real_n']+=1
            rp=out/'results'/f'{target}.jsonl';rp.write_text(''.join(json.dumps(r,separators=(',',':'))+'\n' for r in rows))
            d['results_sha256'][target]=sha(rp);(out/'decision.json').write_text(json.dumps(d))
            try: subset_mod.extract(out)
            except (AssertionError,KeyError,ValueError) as exc:
                outcomes[name]={'rejected':True,'reason':f'{type(exc).__name__}: {exc}'}
            else: fail(f'negative control {name} was accepted')
    return outcomes

plan,decision,arms,full=validate_full()
subset=subset_mod.extract(RUN)
if subset['status']!='FINAL': fail('original 120 source subset not final')
if subset['result'] != decision['per_cell_native']['oolong_synth@131072']: fail('original 120 does not match native per-cell result')
controls=negative_controls()

pre=json.loads((PACKET/'JOINT-PREDECLARATION.json').read_text())
if pre['whole_plan_sha256']!=plan['plan_sha256'] or pre['whole_plan_n_items']!=141: fail('joint predeclaration mismatch')
if pre['original_120_n_items']!=120 or pre['subset_rule'] != 'same existing agg_scoring.net_paired_mcnemar helper, alpha 0.05, RIGHT iff score>=1.0, all exact 120 unique IDs paired and native from server_timings; no missing/error pair admitted; report b,c,mean difference,p,n_discordant,attempted counts and power note; no equivalence claim': fail('original subset contract mismatch')

result={
 'schema':'epyc.yarn_agg_1g.power_result.v1',
 'status':'FINAL',
 'plan_sha256':plan['plan_sha256'],
 'rule':{'method':'native paired one-sided exact McNemar','alpha':0.05,'right_if':'score >= 1.0','fail_if':'p_one_sided <= 0.05','power_target':'at least 10 new discordant pairs','equivalence_claim':False},
 'fresh_full_141':{**full,'power_target_reached':full['n_discordant']>=10,'interpretation':'harm detection only; NOT-FAIL is not equivalence or safety'},
 'original_registered_120':{**subset['result'],'power_target_reached':subset['result']['n_discordant']>=10,'attempted_a0':subset['attempted_a0'],'attempted_a1':subset['attempted_a1'],'attempted_both':subset['attempted_both'],'scope':'exact prospectively declared source-120 subset; prior scores not pooled'},
 'historical_extension':{'b':2,'c':1,'n_discordant':3,'status':'separate historical observation; excluded from both fresh decisions'},
 'integrity':{'full_pairs_per_arm':141,'original_120_pairs_per_arm':120,'result_hashes_match_native_decision':True,'recomputed_full_equals_native_decision':True,'recomputed_subset_equals_native_per_cell':True,'negative_controls':controls},
 'analysis_failure_repaired':{'original_status':'INCOMPLETE; original analyzer exit 2','cause':'subset extractor incorrectly asserted real_n == timings.prompt_n; native real_n is prompt_n + cache_n (cached-prefix tokens are part of served context)','repair':'enforce exact native equation real_n == timings.prompt_n + timings.cache_n, then retain all existing plan/pin/hash/pairing/zone/status checks'},
 'source_artifact_manifest':'SOURCE-ARTIFACTS.sha256.json',
 'original_failure_copy':'ORIGINAL-SUBSET-120-FAILURE.json'
}
(PACKET/'SUBSET-120-RESULT.json').write_text(json.dumps(subset,indent=2)+'\n')
(PACKET/'POWER-RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
(PACKET/'NEGATIVE-CONTROLS.json').write_text(json.dumps(controls,indent=2)+'\n')
print(json.dumps(result,indent=2))
