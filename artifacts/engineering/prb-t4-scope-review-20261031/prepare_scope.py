"""Private review payload only: emits JSON stdout; never appends or reviews frames."""
import hashlib
import itertools
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path('/mnt/raid0/llm/worktrees/mains/codex-refactor-01a16fc3')
sys.path.insert(0, str(ROOT / 'scripts/vidya'))
from frames import make_frame
from fold import fold

STAMP = '2026-10-31T19:30:00Z'
METRICS = {'tale_suite_accuracy', 'tale_mean_answer_tokens', 'tale_mean_tokens_incl_estimator', 'tale_mean_latency_s_incl_estimator'}
CONDITIONS = {'baseline', 'static', 'tale'}


def prepare(capture):
    records = capture['records']
    frames = [r['frame'] for r in records]
    sources = [f for f in frames if f['frame_type'].endswith('/source_observed/v1')]
    claims = [f for f in frames if f['frame_type'].endswith('/claim_proposed/v1')]
    evidence = [f for f in frames if f['frame_type'].endswith('/evidence_supports_claim/v1')]
    assert len(frames) == 72 and len(sources) == len(claims) == len(evidence) == 24, 'unexpected target history'
    by_source = {f['assertion']['source_id']: f for f in claims}
    assert len(by_source) == 24
    groups = {'math': [], 'olympiadbench': []}
    grid = set()
    for source in sources:
        a = source['assertion']
        prefix, run, suite, condition, metric, locator = a['locator'].split(':', 5)
        assert prefix == 'tale-budget' and run == 'prb_t4_gpu_20260916_191049_' + suite
        assert suite in groups and condition in CONDITIONS and metric in METRICS
        key = (suite, condition, metric)
        assert key not in grid, 'duplicate suite/condition/metric'
        grid.add(key)
        claim = by_source[a['source_id']]
        assert claim['pubinfo']['actor'] == source['pubinfo']['actor'] == 'vidya.adapters.tale_budget/v1'
        support = [f for f in evidence if f['assertion']['claim_id'] == claim['assertion']['claim_id']]
        assert len(support) == 1 and support[0]['assertion']['source_id'] == a['source_id']
        groups[suite].append({'claim_id': claim['assertion']['claim_id'], 'source_frame_id': source['frame_id'], 'claim_frame_id': claim['frame_id'], 'support_frame_id': support[0]['frame_id'], 'original_display_text': claim['assertion']['display_text'], 'original_support_assertion': support[0]['assertion'], 'raw_result_present': Path(locator).exists()})
    assert grid == set(itertools.product(groups, CONDITIONS, METRICS)), 'incomplete target grid'
    texts = {
        'math': 'Scope correction: these historical math-labelled observations describe the GSM8K-only sampled subset, not the full mixed math suite. The committed handoff reports 150/150 gsm8k_* questions and excludes the suite\'s 500 MATH-500 rows. Historical result locators are currently unavailable; these counts are attributed to that handoff, not remeasured here.',
        'olympiadbench': 'Scope correction: these historical olympiadbench observations describe the subject-skewed sampled subset, not representative suite performance. The committed handoff reports geometry 15/300 trials against a 19% population share. Historical result locators are currently unavailable; these counts are attributed to that handoff, not remeasured here.'}
    payloads = []
    for suite, rows in groups.items():
        payloads.append(make_frame(frame_type='epyc.vidya/frame/correction_recorded/v1', assertion={'entry_id': 'prb-t4-sample-scope-' + suite, 'claim_ids': sorted(r['claim_id'] for r in rows), 'correction_text': texts[suite], 'classification': None}, provenance={'method': 'private-review/prb-t4-scope-correction/v1', 'about': 'VB-PRB-T4-CAVEAT', 'source_handoff': 'handoffs/active/vidya-belief-substrate-program.md', 'historical_raw_unavailable': True}, actor='codex-refactor-01a16fc3', authority_scope='research-verification', created_at=STAMP))
    before = fold(frames, as_of=STAMP)
    after = fold(frames + payloads, as_of=STAMP)
    assert set(before.beliefs) == set(after.beliefs)
    for cid, old in before.beliefs.items():
        new = after.beliefs[cid]
        assert old.pro == new.pro and old.con == new.con
        left, right = asdict(old), asdict(new)
        left.pop('corrections'); right.pop('corrections')
        assert left == right and new.review_required and len(new.corrections) == 1
    return {'status': 'PRIVATE_REVIEW_ONLY_NOT_APPENDED', 'canonical_frontier': capture['frontier'], 'canonical_sha256': capture['ledger_sha256'], 'canonical_record_count': capture['record_count'], 'scope_identity': groups, 'proposed_frames': payloads, 'native_fold_target_controls': '24 targets: original grades and all other state unchanged; correction review required', 'limitation': 'Target-only fold; full-ledger dependency effects require separate review. No correction_reviewed frames or canonical writes.'}


if __name__ == '__main__':
    capture = json.loads(Path(sys.argv[1]).read_text())
    plan = prepare(capture)
    import copy
    for mutation in ['missing', 'duplicate']:
        bad = copy.deepcopy(capture)
        if mutation == 'missing':
            bad['records'].pop()
        else:
            bad['records'].append(bad['records'][0])
        try:
            prepare(bad)
        except AssertionError:
            pass
        else:
            raise AssertionError('negative control accepted: ' + mutation)
    plan['negative_controls'] = ['missing target refused', 'duplicate target refused']
    plan['implementation_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    print(json.dumps(plan, indent=2))
