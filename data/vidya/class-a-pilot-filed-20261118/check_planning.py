from pathlib import Path
import hashlib
import json
import subprocess
import sys

from check import BASE, ROOT, CANONICAL, BATCH, NOW, cli, dump, run
from adapters import committed_conclusion as ccm
from ledger import Ledger
from prepare import REF, GEMMA
import loop_beliefs as lb

def answer(name):
    o = json.loads((BASE/f'plan-{name}.json').read_text())
    assert o['status']=='ready' and o['reader_checkout_check'] and o['ledger_state']['fresh'], name
    return o

def checks():
    before = answer('before-q27-gpu')
    expected = ['gemma-cpu','q27-gpu','q38-cpu','q35-gpu']
    answers = dict((target, answer(f'after-{target}')) for target in expected)
    conf = {r['cc_id']:r['gold_index'] for r in json.loads((BASE/'confirmation.json').read_text()) if 'cc_id' in r}

    def gold_index(cid):
        return conf.get(cid.removeprefix('clm_').split(':r')[0])

    def selected(report, i, tier):
        return [r for r in report['evidence']['claims'] if r['tier']==tier and gold_index(r['claim_id'])==i]

    seen = {
        'CPU target gold 110': selected(answers['gemma-cpu'], 110, 'target'),
        'GPU target gold 74': selected(answers['q35-gpu'], 74, 'target'),
        'CPU sibling gold 5': selected(answers['q38-cpu'], 5, 'sibling'),
        'GPU host gold 34': selected(answers['q27-gpu'], 34, 'host'),
    }
    assert all(seen.values())
    for rows in seen.values():
        assert all((r['grade'],r['status'],r['retrofit'],r['run'])==
                   ('Judged/Located','verified',True,None) for r in rows), rows
    for key in expected:
        assert 'Judged/Located · verified · retrofit' in answers[key]['evidence']['section']

    records = ccm.read_register(BATCH)
    unscoped = {r['cc_id'] for r in records if not r['scope'] and r['kind']=='result'}
    state = BASE/'planning'
    ledger = state/'ledger.jsonl'
    frames = [x.frame for x in Ledger(ledger).read_all()]
    for x in answers.values():
        targets = [lb.Target.from_mapping(t) for t in x['targets']]
        collected = lb.collect(frames, targets, as_of=x['as_of'], consumer='cc-pilot')
        for r in collected['omitted']:
            assert (r.get('reason') != 'superseded_run' or
                    gold_index(r.get('claim_id') or '') is None and
                    r.get('source_kind') != 'committed-conclusion'), r
        visible = x['evidence']['claims'] + sum(x['evidence']['flagged'].values(), [])
        assert unscoped.isdisjoint(r['claim_id'].removeprefix('clm_').split(':r')[0] for r in visible)

    floor = 'clm_ak-floor:v1:q27b-9a3f1392a-gpu-dflash2-np1:8ccff75f84e0b4af'
    for report in (before, answers['q27-gpu']):
        assert any(r['claim_id']==floor and r['outcome']=='floor' and r['tier']=='target'
                   for r in report['evidence']['claims'])
    live = lambda o: {r['claim_id'] for r in o['evidence']['claims']
                      if r['source_kind']=='autokernel-r234-native-sweep' and not r['stale_epoch']
                      and not r['retrofit'] and r['tier']=='target'}
    assert live(before) == live(answers['q27-gpu']) and live(before)

    # Scratch control for the real dated epoch fence. The gold set has no second dated
    # epoch for the same exact model/source/recipe, so add one separately anchored comparator.
    comparator_file = BASE/'ac8-epoch-control.jsonl'
    comparator_file.unlink(missing_ok=True)
    cli('ac8-control-build','conclusion','add',
        '--path','handoffs/active/numa-placement-defect-20260730.md','--line','1023',
        '--ref',REF,'--stated-json',json.dumps({'date':'2026-07-30',
                    'metrics':[{'metric':'ctxalloc_resident_memory_increase','value':6,'unit':'GB'}]}),
        '--scope-json',json.dumps({'model_file':GEMMA,'backend':'cpu','device':'epyc-9655',
                                  'quant':'Q4_K_M','epoch':'E8-cpu-kernel'}),
        '--scope-evidence','handoff-header','--direction','lower_better','--retrofit',
        '--actor','h-vidya-belief-substrate/class_a_fill','--task-id','T12','--at',answers['gemma-cpu']['as_of'],
        '--register',str(comparator_file))
    rep = cli('ac8-control-ingest','--ledger',str(ledger),'ingest','committed-conclusion',
              '--path',str(comparator_file),'--only-new','--as-of',answers['gemma-cpu']['as_of'])
    assert not rep['refused'] and rep['frames_emitted']==3
    args = [sys.executable,str(ROOT/'scripts/vidya/loop_beliefs.py'),'prepare',
            '--consumer','cc-pilot','--target-json',json.dumps({'model_file':GEMMA,'backend':'cpu',
                                                                'quant':'Q4_K_M','context_tokens':8192}),
            '--as-of',answers['gemma-cpu']['as_of'],'--ledger',str(ledger),'--index',str(state/'index.yaml'),
            '--read-log',str(state/'reads.jsonl'),'--known-good',str(state/'known-good.json'),
            '--alarm-config',str(state/'alarm.yaml'),'--alarm-state',str(state/'alarm-state.json')]
    rc, result=run('plan-ac8-gemma-cpu',*args)
    assert rc==0 and result['status']=='ready' and result['reader_checkout_check']
    old = selected(result,110,'target')
    section=result['evidence']['section']
    control_id = 'clm_'+ccm.read_register(comparator_file)[0]['cc_id']+':r1#m0'
    current = [r for r in result['evidence']['claims'] if r['claim_id']==control_id]
    assert len(current) == 1 and not current[0]['stale_epoch'], current
    assert len(old)==6 and all(r['stale_epoch'] for r in old)
    assert section.index(control_id) < section.index('Older epochs') < section.index(old[0]['claim_id'])
    summary = json.loads((BASE/'ac1-ac5.json').read_text())
    after_sha = hashlib.sha256(CANONICAL.read_bytes()).hexdigest()
    assert after_sha == summary['before_sha']
    dump('ac6-ac9.json',dict(
        target_examples={k:[r['claim_id'] for r in rows] for k,rows in seen.items()},
        all_reader_checkout_checks=True, unscoped_projected_rows=len(unscoped),
        superseded_pilot_runs=0,
        epoch={'prior_gold':110,'older_epoch':'E5-cpu-kernel','older_claim_ids':[r['claim_id'] for r in old],
               'current_epoch':'E8-cpu-kernel','comparator':control_id,'comparator_is_scratch_only':True},
        budget={'stock_max_claims':lb.DEFAULT_MAX_CLAIMS,'stock_max_bytes':lb.DEFAULT_MAX_BYTES,
                'floor_retained':floor,'live_ak_target_claim_ids_retained':sorted(live(before)),
                'target_tier_before': before['evidence']['tiers_shown']['target'],
                'target_tier_after':answers['q27-gpu']['evidence']['tiers_shown']['target']},
        canonical_ledger_sha256_before=summary['before_sha'],canonical_ledger_sha256_after=after_sha))
    print('AC6-AC9 PASS')

if __name__=='__main__':
    checks()
