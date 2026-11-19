# FM-2 Stage 1 row spec (NOT published; no queue/FILLERS/ready write was made)

Format: `epyc.row.v3` spec for `scripts/coordination/rowflow/publish_row.py` (SPEC_KEYS), modelled on
`/mnt/raid0/llm/tmp/inf86-reprefill-rate-20261110/spec.json`; contract per `docs/guides/agent-workflows/compute-fillers.md`.
Publish steps the owner must do (not done here): copy `scripts/benchmark/fm2_adamast_{launch,job}.sh`,
`fm2_adamast_check_complete.py` -> `/mnt/raid0/llm/tmp/fm2-adamast-20261110/{launch.sh,job.sh,check_complete.py}`, copy
`scripts/coordination/{adamast_normalize,delegation_accounting}.py` beside them, write `SOURCE.sha256`, clone upstream at
`3c83d81c85937f5e8911fd96daa2ca38c1ad2585` + `git apply providers_base_url.patch`, fill the three `<...>` values, then
`publish_row.py spec.json`, check `ls ready/<id>.json`, arm the inference-mailbox watcher.

```json
{
 "id": "fm2-adamast-20261110",
 "owner": "<owning session, RTG-34 coordinator-role-failure-modes track>",
 "handoff_task": "coordination-and-churn-pipeline.md:FM-2 — AdaMAST fixed-catalog grading pilot",
 "launcher": "/mnt/raid0/llm/tmp/fm2-adamast-20261110/launch.sh",
 "lane": "cpu",
 "shape": "quarter",
 "regions": "any-cpu-quarter",
 "declared_threads": 24,
 "threads_evidence": ["job passes -t $FILLER_THREADS and taskset -c $FILLER_CPUS to its private llama-server; the python/adamast client is idle while the server computes"],
 "ram_gib": "<judge GGUF size + ~8 GiB; model undetermined>",
 "ports": [18711],
 "min_window_s": 3600,
 "estimate_s": 10800,
 "first_progress_s": 900,
 "result_path": "/mnt/raid0/llm/tmp/fm2-adamast-20261110/out/results.jsonl",
 "result_format": "jsonl",
 "unit_key": "unit_id",
 "resumable": true,
 "verdict_by": "agent",
 "smoke_predicate": "/usr/bin/python3 -I /mnt/raid0/llm/tmp/fm2-adamast-20261110/smoke_predicate.py",
 "keep": ["out/manifest.json", "out/index.jsonl", "out/results.jsonl", "out/judged/*.json", "out/traces/*.jsonl", "out/server.log", "job.sh", "launch.sh", "adamast_normalize.py", "SOURCE.sha256"],
 "width_justification": "one private llama-server, strictly sequential one-call-per-trace judging; a quarter's cores are all it can use.",
 "decision_rule": "QUESTION: on a stratified, outcome-blind sample of our own Claude Code and Codex transcripts, what is the prevalence of each of the 14 fixed MAST codes (adamast/core/mast.json, AdaMAST 3c83d81c8) as assigned by one local judge model, one call per trace, and which F-series ledger families (mast_fseries_crosswalk.json) do the fired codes support? SAMPLE (predeclared, frozen in out/manifest.json, seed fm2-adamast-20261110): 3 traces per stratum of (harness: claude|codex) x (month of first record) x (main|subagent); the 2026-11-10 smoke saw 6 non-empty claude strata, codex strata appear only if ~/.codex/sessions holds rollouts, so expect about 18-40 traces. EXPECTED EFFECT / SIZE: descriptive only. With n=3 per stratum a stratum-level rate is unresolvable (0/3 has a Wilson 95% upper bound ~56%); only pooled per-code prevalence over ~20-40 traces and gross harness/kind contrasts (>~30 pp) can be read, with Wilson intervals; anything finer is reported as not resolved. NOT a faithfulness measure: no human gold, no oracle, one judge model; the repo's agreement gate is not used or trusted. VERDICTS (agent files from out/judged/*.json): COMPLETE (all traces judged; report per-code counts with Wilson 95% CIs, per-stratum table, parse-failure rate), PARSE_FAIL_HIGH (>25% of judge calls returned unparseable/empty output: the judge model or response_format=json is not usable, fix before any prevalence is quoted), INCOMPLETE. STOP-ON-ANSWER: every trace has judged/<id>.json -> summarize, write grants/<id>.complete via --complete-cmd. STOP-ON-FUTILITY: precondition fail (patch absent from providers.py, binary/linkage/model missing), server not ready in 1800 s or port listener not our PID, >25% judge-call failures after the first 8 calls, STOP file, FILLER_END -> no verdict (resumable). Stage 2 (adamast generate, induced taxonomy) is a separate row after FM-4/oracle work.",
 "notes": "OUTCOME-BLIND: adamast_normalize.py strips outcome/final_gate_status recursively and emits no outcome field. Model-execution row: needs a grant, never run_direct. Interpreter: /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python (openai 2.31.0 present; remaining adamast deps unproven until the smoke)."
}
```

## Launcher env pins (resolved at publish time, not guessed)

| name | value | status |
|---|---|---|
| `FM2_ADAMAST_SRC` | checkout of `github.com/multi-agent-systems-failure-taxonomy/AdaMAST` @ `3c83d81c85937f5e8911fd96daa2ca38c1ad2585` (Apache-2.0, 2026-08-26) + `providers_base_url.patch` | clone exists in `/mnt/raid0/llm/worktrees/rtg34-fm-20261110-scratch/adamast-upstream` (unpatched) |
| `FM2_SERVER_BIN` | a `kernels/production/cpu` llama-server | undetermined: path plus a sha256/version/ggml-linkage precond like inf86's `precond.sh` still to be written |
| `FM2_MODEL_GGUF` | judge model | UNDETERMINED (see below) |

## Undetermined

- **Judge model.** Registry/operator choice; a JSON-capable instruct model with thinking off (Qwen3.x needs
  `qwen_thinking_lib.sh` handling per compute-fillers.md; `--reasoning off` is in the job but not proven for the chosen model).
  `max-trace-chars` 24000 (about 6-8k tokens) with `-c 16384`; adamast default is 6000.
- **Does the patch matter?** The `openai` SDK already reads `OPENAI_BASE_URL` natively and the intake dive says AdaMAST honours
  it; the patch (`ADAMAST_BASE_URL`) is explicit and harmless but a smoke should first try `OPENAI_BASE_URL` alone.
- **`smoke_predicate.py`, `precond.sh`, `SOURCE.sha256`**: not written (need the final model/binary); publish_row refuses
  a smoke_predicate that already exits 0, so write it against a real smoke output (compute-fillers.md, Publishing discipline).
- **adamast install deps** other than `openai` and whether `python -m adamast` imports cleanly in that venv.
- The `adamast judge` output schema was read from source only (`diagnoses[]`); never run.
