#!/usr/bin/env python3
"""EXP-06 / PIP02-PHASEC-CUSTODY: page-eligibility re-read of the filed v8 exposure snapshot (zero inference, read-only).
Stop rule (before computing): re-derive the 690 / 65 split and the per-shard structure from the stored v8 snapshot (plan SHA bound), then test
whether a FRESH inventory can be regenerated in this namespace by checking every root/capture the snapshot read still exists. Stop at that
determination; no inventory is rewritten, no lock created, no start inferred from absence.
Usage: exp06_custody_reread.py OUT.json"""
import collections, hashlib, json, os, sys
V8 = '/mnt/raid0/llm/tmp/codex3-pip-exposure-recheck-20261101/all-shards-inventory-v8.json'
PLAN = '/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/english755-fresh-plan.json'
PHASEC = '/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/campaigns-fresh'
raw = open(V8, 'rb').read(); d = json.loads(raw); pg = d['pages']
cand = [x for x in pg if x['disposition'] == 'CANDIDATE_NO_OBSERVED_START']
plan_ok = hashlib.sha256(open(PLAN, 'rb').read()).hexdigest() == d['plan_sha256'] == '63028e74950ba7250f33cbce13f4f0bdd165bba2a075242db4475c26f645ed68'
shards_c = sorted({x['shard'] for x in cand})
res = {'schema': 'brf-t3/exp06-custody-reread/1', 'snapshot': V8, 'snapshot_sha256': hashlib.sha256(raw).hexdigest(), 'plan_sha256_matches_declared': plan_ok,
       'pages': len(pg), 'unique_page_indices': len({x['page']['index'] for x in pg}), 'dispositions': dict(collections.Counter(x['disposition'] for x in pg)),
       'candidate_no_observed_start': {'n': len(cand), 'shards': shards_c, 'n_shards': len(shards_c), 'every_candidate_shard_has_5_pages': all(sum(1 for c in cand if c['shard'] == s) == 5 for s in shards_c),
          'any_in_scope_unknown_shard': any(str(x['shard']) in d['scope_unknown_by_shard'] for x in cand),
          'any_has_start_region_or_finish_record': any(x['page_starts'] or x['regions'] or x['finish_records'] for x in cand),
          'shard_dirs_absent_in_surviving_phasec_root': {str(s): not os.path.exists(f'{PHASEC}/shard-{s:02d}') and not os.path.exists(f'{PHASEC}/shard-{s}') for s in shards_c}},
       'scope_unknown_shards': len(d['scope_unknown_by_shard']), 'captures_total': len(d['captures']), 'captures_without_verified_complete_result': len(d['captures_without_verified_complete_result']),
       'terminal_reasons': dict(collections.Counter(d['captures'][k]['terminal_reason'] for k in d['captures_without_verified_complete_result'])),
       'no_evidence_pages_total': sum(1 for x in pg if not (x['page_starts'] or x['regions'] or x['finish_records'])),
       'snapshot_warning': d['warning']}
roots = {r: os.path.isdir(r) for r in d['roots']}
caps_exist = collections.Counter(os.path.exists(v['path']) for v in d['captures'].values())
res['fresh_inventory_feasible_here'] = {'campaign_roots_total': len(roots), 'campaign_roots_present_now': sum(roots.values()), 'roots': roots,
    'capture_files_total': len(d['captures']), 'capture_files_present_now': caps_exist[True], 'capture_files_absent_now': caps_exist[False],
    'attempt_roots_present_now': dict(collections.Counter(os.path.isdir(r) for r in d['attempt_roots'])),
    'verdict': 'NOT REPRODUCIBLE in this namespace: inventory_all.py refuses when any declared campaign root is inaccessible (6 of 7 roots, under /mnt/micron, are absent) — the snapshot is therefore the last readable record, and the box clause "refresh the inventory" cannot be met by replay (absence may be a mount/namespace difference, not asserted to be deletion)'}
json.dump(res, open(sys.argv[1], 'w'), indent=1, sort_keys=True)
print(json.dumps({k: res[k] for k in ('pages', 'dispositions', 'plan_sha256_matches_declared', 'captures_without_verified_complete_result', 'terminal_reasons', 'no_evidence_pages_total')}))
print(json.dumps(res['candidate_no_observed_start'])); print(json.dumps({k: v for k, v in res['fresh_inventory_feasible_here'].items() if k != 'roots'}))
