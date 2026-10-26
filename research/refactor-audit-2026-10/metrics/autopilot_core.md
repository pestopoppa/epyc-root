# Metrics: autopilot_core (/workspace/repos/epyc-orchestrator/src/autopilot_core)

files=20 loc=7417 code=6039 funcs=255 broad_except=8 swallowed=1 prints=0 module_level_calls=0 global_stmts=1 hardcoded_/mnt/raid0=0 public_undoc_funcs=12 no_module_doc=0 sys.path_mutations=0 shell=True=0

## Largest files (loc)
- src/autopilot_core/journal_snapshot_replay.py: 1009 loc, 30 funcs, max_func=146, max_cc=30
- src/autopilot_core/tier_specs.py: 743 loc, 34 funcs, max_func=77, max_cc=31
- src/autopilot_core/sequential_verdict.py: 703 loc, 22 funcs, max_func=70, max_cc=10
- src/autopilot_core/infra_fingerprint.py: 607 loc, 27 funcs, max_func=65, max_cc=19
- src/autopilot_core/planner_evidence.py: 571 loc, 26 funcs, max_func=66, max_cc=20
- src/autopilot_core/ap55_promotion_gate.py: 496 loc, 20 funcs, max_func=88, max_cc=22
- src/autopilot_core/measurement_guards.py: 439 loc, 7 funcs, max_func=116, max_cc=33
- src/autopilot_core/journal_reconstruction.py: 384 loc, 10 funcs, max_func=200, max_cc=45
- src/autopilot_core/instrument_era_guard.py: 377 loc, 9 funcs, max_func=127, max_cc=29
- src/autopilot_core/multitier_decision.py: 328 loc, 11 funcs, max_func=147, max_cc=17
- src/autopilot_core/rlvr_tiers.py: 325 loc, 14 funcs, max_func=115, max_cc=12
- src/autopilot_core/baseline_ledger.py: 293 loc, 9 funcs, max_func=101, max_cc=17
- src/autopilot_core/attestation_trust.py: 171 loc, 7 funcs, max_func=90, max_cc=11
- src/autopilot_core/verification_families.py: 169 loc, 6 funcs, max_func=26, max_cc=7
- src/autopilot_core/action_identity.py: 165 loc, 9 funcs, max_func=22, max_cc=10
- src/autopilot_core/learning_exclusions.py: 157 loc, 2 funcs, max_func=108, max_cc=24
- src/autopilot_core/pareto_math.py: 145 loc, 4 funcs, max_func=53, max_cc=16
- src/autopilot_core/__init__.py: 141 loc, 0 funcs, max_func=0, max_cc=0
- src/autopilot_core/authority_consent.py: 107 loc, 6 funcs, max_func=23, max_cc=3
- src/autopilot_core/live_reproductions.py: 87 loc, 2 funcs, max_func=41, max_cc=15

## Longest functions
- src/autopilot_core/journal_reconstruction.py:185 reconstruct_archive_from_journal_rows len=200 cc=45 depth=3 nargs=8
- src/autopilot_core/multitier_decision.py:182 evaluate_tier_validation len=147 cc=17 depth=2 nargs=7
- src/autopilot_core/journal_snapshot_replay.py:829 build_snapshot_replay_diagnostic len=146 cc=30 depth=3 nargs=2
- src/autopilot_core/instrument_era_guard.py:150 designed_core_activation_guard len=127 cc=29 depth=3 nargs=3
- src/autopilot_core/measurement_guards.py:286 infra_failure_reason len=116 cc=33 depth=4 nargs=3
- src/autopilot_core/rlvr_tiers.py:104 rlvr_reward_from_result len=115 cc=8 depth=2 nargs=1
- src/autopilot_core/learning_exclusions.py:14 classify_learning_exclusion len=108 cc=24 depth=2 nargs=2
- src/autopilot_core/baseline_ledger.py:94 reconcile_baseline_ledger len=101 cc=17 depth=2 nargs=2
- src/autopilot_core/instrument_era_guard.py:279 active_eval_quality_era len=99 cc=17 depth=3 nargs=2
- src/autopilot_core/journal_snapshot_replay.py:203 archive_payload_from_verified_snapshot len=99 cc=26 depth=2 nargs=2
- src/autopilot_core/journal_snapshot_replay.py:378 _fold_representative_tail_into_snapshot len=93 cc=21 depth=3 nargs=5
- src/autopilot_core/attestation_trust.py:58 attestation_precondition len=90 cc=11 depth=1 nargs=3
- src/autopilot_core/ap55_promotion_gate.py:253 batch_homogeneity len=88 cc=22 depth=2 nargs=9
- src/autopilot_core/journal_snapshot_replay.py:642 _fold_tail_archive_into_snapshot len=82 cc=27 depth=2 nargs=2

## Highest cyclomatic complexity
- src/autopilot_core/journal_reconstruction.py:185 reconstruct_archive_from_journal_rows cc=45 len=200
- src/autopilot_core/measurement_guards.py:286 infra_failure_reason cc=33 len=116
- src/autopilot_core/tier_specs.py:225 task_rate_qph_from_row_if_available cc=31 len=77
- src/autopilot_core/journal_snapshot_replay.py:829 build_snapshot_replay_diagnostic cc=30 len=146
- src/autopilot_core/instrument_era_guard.py:150 designed_core_activation_guard cc=29 len=127
- src/autopilot_core/journal_snapshot_replay.py:642 _fold_tail_archive_into_snapshot cc=27 len=82
- src/autopilot_core/journal_snapshot_replay.py:203 archive_payload_from_verified_snapshot cc=26 len=99

## Big classes (>=400 lines)

## Most swallowed broad excepts (except Exception: pass/continue/return const)
- src/autopilot_core/journal_reconstruction.py: 1 swallowed / 1 broad; lines [117]

## Import-time module-level calls (potential side effects)

## sys.path mutations

## Private cross-module imports (from x import _y)

## Duplicate function bodies across files (top 60 by duplicated lines)
