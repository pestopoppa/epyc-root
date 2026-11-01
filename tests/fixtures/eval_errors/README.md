# EvalTower source-bound fixture

`source_batch.jsonl` is a privacy-minimized projection of the producer-written
batch `evaltower-T1-1793396458477-ee7e0158-3q`. It retains only fields used by
the dashboard reader and omits answers, prompts, host covariates, and error
details.

- Producer source: `epyc-orchestrator` `origin/main` at
  `29fdfc5a7cc229f1dcafee327f193b1623de0d32`
- Producer path: `/mnt/raid0/llm/tmp/eval_tower_trials/trial_unknown/question_results.jsonl`
- Original JSONL SHA-256: `fb0118b58a29cb6635d28044e0b9be771f0ed62a48b9c56e6851b2854867d728`
- Selected batch: three completed results, one non-error scored-correct row and
  two `infra_failed` error rows, followed by the producer's `batch_complete`
  marker. This is a reader contract fixture, not a live or scientific result.
