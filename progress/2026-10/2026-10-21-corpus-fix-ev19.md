# 2026-10-21 corpus-fix-ev19 (EV-19.1/.2/.3)

- mmlu_pro: live pool had `scoring_config={}` on all 12,032 rows (2,053 I/J gold). Fixed at source by PRB-T4 adapter; refreshed pool carries choices + A-J labels.
- tulving_episodic: not a corpus defect; self-check scored the literal `[]`. Self-check now renders empty-list gold as `None`.
- livecodebench 2,360 -> 704 executable-oracle rows (1,656 excluded, `no_validated_oracle`); real_suite_v1 YAML 1.1.
- Self-check, full pool: 0 wrong on all four suites. Residual elsewhere: `thinking` 22/11,214 numeric gold without choices (scorer-excluded).
- Commits: orchestrator `c153f975`, research `795cf9626`. Fixed pool NOT swapped live: `/mnt/raid0/llm/tmp/corpus-fix-ev19/question_pool.corpus-ev19-20261021.jsonl` sha256 `f8b536632b0d95feee339333f46247125def384b6d36d65b39711155825d7f0a` (operator era decision pending).
- History impact: `epyc-orchestrator/data/autopilot/corpus_fix_ev19_history_impact.md`.
