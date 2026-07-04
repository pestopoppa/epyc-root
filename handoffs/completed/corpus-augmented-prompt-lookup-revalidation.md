# Corpus-Augmented Prompt Lookup Revalidation

**Status**: COMPLETED 2026-07-04; prompt-injection ROI was not proven, the operator approved reclaiming the artifact, and `/mnt/raid0/llm/cache/corpus` was deleted to recover about `651G`
**Parent index**: [inference-acceleration-index.md](../active/inference-acceleration-index.md)
**Priority at closure**: high option value because the corpus occupied about `651G`; closed after the clean-window A/B failed to prove benefit and the operator chose reclamation
**Related**: [speculative-decoding-mtp-refresh.md](../active/speculative-decoding-mtp-refresh.md), [model-stack-single-source-update-pipeline.md](../active/model-stack-single-source-update-pipeline.md), archived [hybrid-lookup-spec-decode.md](../archived/hybrid-lookup-spec-decode.md), archived [llama-server-prompt-lookup.md](../archived/llama-server-prompt-lookup.md)

## Objective

Decide whether the local code corpus at `/mnt/raid0/llm/cache/corpus` is a live
performance feature or reclaimable dead weight. Outcome: the prompt-injection
path did not provide measured coding-task acceleration, and the operator chose
reclamation rather than a final static n-gram experiment.

## Final Findings

- Live `llama-server` commands do not pass native n-gram/prompt-lookup corpus
  flags; active servers use draft-MTP where supported.
- Prompt-stuffing corpus retrieval is distinct from native llama prompt lookup:
  the former injects `## Reference Code` / `<reference_code>` snippets into the
  prompt, while the latter would pass lookup/static-cache flags to
  `llama-server` and draft tokens without prompt content.
- Recent inference tap logs are not the strongest corpus proof. The current
  proof is the corpus health/preflight artifacts plus live `RegistryLoader`
  role parsing.
- Production code still has corpus-injection call sites:
  `src/prompt_builders/builder.py:build_corpus_context()`,
  `src/api/routes/chat.py`, `src/api/routes/chat_pipeline/stream_adapter.py`,
  `src/graph/helpers.py`, and `src/api/routes/chat_delegation.py`.
- Direct `build_corpus_context()` testing returned an empty string before the
  2026-07-03 repair.
- 2026-07-03 repair: `build_corpus_context()` now resolves
  `RegistryLoader(validate_paths=False)`, gates on the parsed per-role
  `acceleration.corpus_retrieval` flag, emits structured log metadata for
  disabled/injected/slow/error outcomes, and suppresses retrievals above the
  configured slow-query threshold.
- At test time, live role parsing intentionally enabled prompt-stuffing only for the
  frontdoor/coder lane: `frontdoor=True`, `coder_escalation=True`, and
  `worker_general=False`, `architect_general=False`, `ingest_long_context=False`
  for `acceleration.corpus_retrieval`. All five keep native `lookup=false`.
- Forced retrieval against `/mnt/raid0/llm/cache/corpus/v3_sharded` can return
  snippets, but one realistic query took about `29s` for 3 snippets; short
  low-overlap queries returned no snippets in about `0.36s`.
- 2026-07-03 no-inference health probe artifact:
  `/mnt/raid0/llm/epyc-orchestrator/orchestration/reports/corpus_health_probe_20260703T112521Z.json`.
  Warm-cache observation over 6 representative coding queries: `6/6` returned
  snippets, `17` snippets total, `p50=0.331ms`, `p95=298.016ms`,
  `candidate_count_total=27`, `failure_count=0`, and
  `usable_for_online_prompt_injection=true` under a `5000ms` p95 threshold.
  This is health evidence only; it does not prove quality or end-to-end speed.
- 2026-07-03 A/B harness repair: `scripts/benchmark/corpus_quality_gate.py`
  now records per-prompt retrieval diagnostics in the corpus arm, reuses the
  corpus singleton across prompt pairs, supports no-inference `--preflight-only`,
  supports generation-only `--skip-judge`, and exposes `--min-score` /
  `--rag-min-score` so threshold candidates are explicit.
- No-inference quality-gate preflights show why the threshold must be explicit:
  `corpus_quality_preflight_20260703T124703Z.json` reproduced the old
  `min_score=0.5` behavior with `0/6` injected prompts and `ready_for_ab=false`;
  `corpus_quality_preflight_20260703T124756Z.json` used candidate
  `min_score=0.0` and returned `6/6` injected prompts, `3` snippets per prompt,
  `failure_count=0`, `p50=1.206ms`, and `ready_for_ab=true`. This only clears
  the lookup/injection preflight, not the live quality/speed A/B.
- 2026-07-03 live shakedown safety finding: a direct production-port
  `corpus_quality_gate.py` run while AutoPilot was active was aborted after one
  prompt pair and the partial artifact was deleted. The single contaminated row
  (`coder_escalation` async-retry, corpus 3 snippets, `471.5ms` lookup,
  baseline `12.7` t/s vs corpus `8.7` t/s) is not evidence because AutoPilot was
  concurrently using the same production fleet. Orchestrator now requires
  `--confirm-clean-window` for live generation and exits `75` when AutoPilot is
  active unless `--allow-active-autopilot` is passed for explicitly
  non-claim-grade live-load telemetry.
- 2026-07-04 read-only audit: `/mnt/raid0/llm/cache/corpus/v3_sharded` was the
  live default corpus path, with `/mnt/raid0/llm/cache/corpus/mvp_index` still
  supported as a fallback; the full corpus tree was about `651G`. The loader is
  `CorpusRetriever`, `build_corpus_context()` is called by live chat,
  stream-adapter, delegation, and graph-helper paths on turn 0, and
  `corpus_quality_preflight_20260704T164539Z.json` shows `injected_count=6`,
  `6/6` injected prompts, `3` snippets per prompt, and no failures.
- These findings prove wiring/searchability only. They do **not** prove that
  corpus assistance improves code-writing quality or end-to-end latency.
- What remains disabled/unproven: native llama prompt lookup (`--lookup-*`,
  `--lookup-cache-static`) is not active for current frontdoor/coder roles; the
  old disabled `worker_pool.prompt_lookup` path is not used by the API;
  delegated specialist corpus context is default-off; and the quality-RAG branch
  is disabled unless `rag_enabled` is configured.
- 2026-07-04 no-inference scaffold: `scripts/corpus/build_static_ngram_cache.py`
  can export bounded text chunks from the v3 `snippets.db`, invoke
  `llama-lookup-create -m <model> -f <chunk> -lcs <part>`, and merge parts with
  `llama-lookup-merge`. Focused tests cover chunking, command construction,
  snippets filtering, dry-run behavior, and the large-scan guard. A tiny dry-run
  against the live corpus selected 3 Python snippets and wrote
  `/mnt/raid0/llm/tmp/corpus_static_ngram_dryrun_manifest.json` without loading
  a model or executing llama tools. This only makes the static-cache experiment
  ready; it does not justify a full corpus cache build.
- 2026-07-04 A/B harness alignment: `corpus_quality_gate.py` now defaults to
  the actual CPL-4 role pair, `coder_escalation` + `worker_general`, rather
  than `frontdoor` + `worker_general` + `architect_general`. The benchmark
  artifact records production role corpus flags separately from the benchmark's
  forced corpus arm, so `worker_general` can be tested without flipping live
  production config. Current no-inference preflight artifact:
  `orchestration/reports/corpus_quality_preflight_20260704T203100Z.json`
  (`6/6` prompts injected, `failure_count=0`, `ready_for_ab=true`,
  `coder_escalation.production_role_enabled=true`,
  `worker_general.production_role_enabled=false`,
  `benchmark_forces_prompt_injection=true`). This clears A/B setup only; no live
  generation or quality verdict has run.
- 2026-07-04 production-path guardrail: `epyc-orchestrator` `c0d5ee58` adds an
  explicit code-task scoped corpus eligibility path for roles whose
  `acceleration.corpus_retrieval` remains false. Current production behavior is
  unchanged because no live registry entry sets `task_scoped_roles` /
  `code_task_roles`, but a clean-window A/B can now enable `worker_general`
  without globally injecting corpus snippets into generic worker traffic. Focused
  tests prove configured worker code prompts can inject snippets, while
  configured non-code worker prompts still skip with `task_scope_disabled`.
- 2026-07-04 clean-window prompt-injection A/B outcome: AutoPilot was paused and
  stopped, then `corpus_quality_gate.py` generated corpus-on/off rows for
  `coder_escalation` and `worker_general` with forced corpus injection,
  `--min-score 0.0`, and `--confirm-clean-window`. Generation artifact:
  `/mnt/raid0/llm/epyc-orchestrator/orchestration/reports/corpus_quality_gate_20260704T222948Z.json`;
  judge artifact:
  `/mnt/raid0/llm/epyc-orchestrator/orchestration/reports/corpus_quality_gate_judged_20260704T224401Z_judge.json`.
  Both roles injected `6/6` prompts with 3 snippets each. Throughput was not
  improved: `coder_escalation` averaged `28.11` baseline t/s vs `27.86` corpus
  t/s (`-0.25`), and `worker_general` averaged `37.16` baseline t/s vs `34.06`
  corpus t/s (`-3.10`). The judge parsed 5/6 prompts per model; parse warnings
  are a measurement caveat. `coder_escalation` scored neutral (`1.0` vs `1.0`)
  because speed-mode generation produced empty outputs, so this is not positive
  quality evidence. `worker_general` failed the gate (`5.85` baseline vs `5.30`
  corpus, delta `-0.55`, threshold `-0.5`). This rejects broad/worker
  prompt-injection promotion from current evidence.
- 2026-07-04 operator reclaim decision: after the failed A/B, the operator
  authorized disk reclamation. A `gpt-5.4-mini` worker verified the path was a
  real directory under `/mnt/raid0/llm/cache`, found no active users via a
  lightweight `/proc/*/fd` scan, and ran
  `rm -rf -- /mnt/raid0/llm/cache/corpus`. Local verification confirmed the
  path is gone and `df -h /mnt/raid0/llm` reports about `965G` free, up from
  the worker's recorded `315G` before deletion. Sibling cache directories were
  left untouched.

## Prioritized Task List

- [x] **CPL-1: Fix or explicitly retire the wiring path, no inference.**
  Repair `build_corpus_context()` registry loading, make per-role
  `corpus_retrieval` resolution explicit, and add fail-visible diagnostics when
  corpus retrieval is disabled by config, missing index, import failure, or slow
  query timeout. Done 2026-07-03; current disabled roles fail visible as
  `role_disabled` rather than hidden import failure, while the frontdoor/coder
  lane now injects snippets when the query passes retrieval thresholds.
- [x] **CPL-2: Add live observability.** Emit structured tap/log metadata when
  corpus snippets are injected: role, request/task id, index path, query n-grams,
  snippet count, context chars, retrieval latency, and timeout/failure reason.
  This must make "header only, no corpus" impossible to confuse with real use.
- [x] **CPL-3: Add a cheap offline health probe.** Provide a CLI probe over the
  v3 sharded corpus that runs representative coding queries and reports
  p50/p95 latency, snippets returned, candidate counts, and whether the current
  index is usable for online prompt injection. Done 2026-07-03 via
  `scripts/benchmark/corpus_health_probe.py` and focused tests; first report
  artifact is listed above.
- [x] **CPL-4: Run a focused corpus-on/off A/B for coding tasks.** Compare
  corpus injection off vs on for `coder_escalation` and `worker_general` if that
  role still handles any coding/refactor workload. Use
  `scripts/benchmark/corpus_quality_gate.py --min-score 0.0`
  unless deliberately testing another threshold; the old `0.5` threshold
  preflights as a no-op. Capture retrieval latency, generated t/s, quality, and
  injected-snippet telemetry. Live generation must run in a clean/isolated window
  (`--confirm-clean-window`; no active AutoPilot unless deliberately collecting
  non-claim telemetry with `--allow-active-autopilot`). This A/B decides whether
  prompt-stuffing corpus retrieval is useful, not whether native n-gram lookup
  should be enabled. **Setup status 2026-07-04**: default model selection and
  preflight metadata now match this role pair; next command for a claim-grade
  generation pass is `uv run python scripts/benchmark/corpus_quality_gate.py
  --models coder_escalation worker_general --min-score 0.0
  --confirm-clean-window --skip-judge --output <artifact>`, followed by judge or
  scoring only after the clean-window generation rows exist. Done 2026-07-04 in
  a quiet window; result failed broad promotion. If revisiting live
  `worker_general` corpus injection despite this result, use the code-task
  scoped eligibility and rerun with a stronger prompt/quality protocol rather
  than a blanket `corpus_retrieval: true` flip.
- [x] **CPL-4b: Corpus as a static n-gram *speculation* source (distinct
  mechanism from prompt-injection).** Retired by operator decision after CPL-4
  failed: no large corpus-derived static-cache build was run, and the source
  corpus has been deleted. The scaffold remains as code history only; rebuilding
  would require recreating the corpus and rerunning a new measurement protocol.
- [x] **CPL-5: Decide keep/quarantine/delete.** Decision: delete/reclaim. Current
  prompt-injection A/B evidence did not justify keeping the `651G` corpus for
  online prompt stuffing, and the operator declined the optional static n-gram
  experiment before reclaiming disk.

## Dependency Graph

```mermaid
flowchart TD
    C1[CPL-1 wiring/config] --> C2[CPL-2 observability]
    C1 --> C3[CPL-3 offline probe]
    C2 --> C4[CPL-4 corpus-on/off A/B]
    C3 --> C4
    C4 --> C4B[CPL-4b bounded static-cache build/A-B if justified]
    C4B --> C5[CPL-5 keep/quarantine/delete decision]
    C4 --> C5
```

## Cross-Cutting Concerns

- This is not the same as native draft-MTP. MTP may stay enabled while corpus
  injection is off; corpus work must not disturb current v6 draft-MTP serving.
- If role-level corpus enablement becomes a stack fact, it belongs in the
  generated stack-prior/descriptor pipeline rather than a stale local constant.
- Do not enable corpus retrieval broadly for `worker_general` unless a separate
  mixed-workload A/B proves it does not regress non-code worker traffic; the
  current safe path is code-task scoped only.
- Retrieval latency is part of the metric. A 29s snippet lookup is a regression
  even if the generated answer improves.
- The `651G` corpus was deleted only after explicit operator approval and the
  CPL-4/CPL-5 evidence above.

## Key File Locations

- Deleted corpus artifact: `/mnt/raid0/llm/cache/corpus/v3_sharded`
- Static n-gram cache builder:
  `/mnt/raid0/llm/epyc-orchestrator/scripts/corpus/build_static_ngram_cache.py`
- Corpus service: `/mnt/raid0/llm/epyc-orchestrator/src/services/corpus_retrieval.py`
- Prompt wiring: `/mnt/raid0/llm/epyc-orchestrator/src/prompt_builders/builder.py`
- Chat call sites: `/mnt/raid0/llm/epyc-orchestrator/src/api/routes/chat.py`,
  `/mnt/raid0/llm/epyc-orchestrator/src/api/routes/chat_pipeline/stream_adapter.py`,
  `/mnt/raid0/llm/epyc-orchestrator/src/api/routes/chat_delegation.py`,
  `/mnt/raid0/llm/epyc-orchestrator/src/graph/helpers.py`
- Registry/config: `/mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml`,
  `/mnt/raid0/llm/epyc-orchestrator/src/registry/registry_loader.py`
- Existing benchmark scaffold:
  `/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/corpus_quality_gate.py`

## Reporting Instructions

Closure updated
[inference-acceleration-index.md](../active/inference-acceleration-index.md) and
[master-handoff-index.md](../active/master-handoff-index.md) to remove this from
the active queue. Record any future recreation as a new handoff with a fresh
protocol; do not treat archived V3 corpus measurements as current evidence.
