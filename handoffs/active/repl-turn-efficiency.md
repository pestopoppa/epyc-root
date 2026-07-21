# REPL Turn Efficiency - Active Gates

**Status**: COMPACTED 2026-05-28 - core REPL efficiency changes landed; active gate is S4 Omega A/B.
**Created**: 2026-04-09
**Updated**: 2026-06-14
**Priority**: MEDIUM
**Categories**: agent_architecture
**Depends on**: None
**Parent index**: [research-evaluation-index.md](research-evaluation-index.md)
**Completed ledger**: [repl-turn-efficiency-completed-through-2026-05-28.md](../completed/repl-turn-efficiency-completed-through-2026-05-28.md)

## Executor Start Here

Do not add new REPL tools before S4. The current risk is whether the shipped efficiency features reduce turns and token cost without accuracy loss. Treat the historical frecency, combined operation, dspy.RLM, and ColGREP implementation details as completed unless a regression is found.

## Outstanding Tasks

- [ ] **S4 Omega A/B**: measure turns per task, token cost per task, and accuracy delta. This gates suggestion, verbosity, and any extra tool-surface changes.
- [x] **ColGREP post-telemetry soak check**: 2026-06-14 warmed synthetic REPL soak closed the latency/fallback/quality portion; see telemetry below.
- [x] **Cold-start daemon decision**: do not build now. The measured latency gate did not fire; revisit only if a future live workload trips the multi-search or sustained-call-rate gates.
- [x] **Version/index hygiene**: `epyc-orchestrator` `9b209d3` pins the default runtime path to `/mnt/raid0/llm/UTILS/bin/colgrep-1.2.0`; no ColGREP re-index-on-commit hook for now.

## Cold-Start Daemon Gate

Do not implement a daemon unless at least one of these conditions is met during a representative seeding or REPL run:

- p50 `code_search()` latency is at least 600 ms across a full run.
- At least 20% of REPL turns issue two or more `code_search()` calls.
- One role issues at least one `code_search()` call per second for at least 30 seconds.

## Current Telemetry State

2026-06-13 audit: historical logs were not sufficient to answer the daemon gate. `/mnt/raid0/llm/tmp/repl_tap.log` had no durable `code_search()` latency/fallback records, and the existing ColGREP path only wrote successful calls to the in-memory exploration log without latency. The code path is now instrumented in `epyc-orchestrator`: each ColGREP call appends `artifacts["_code_search_telemetry"]`, success responses include `latency_ms`, success exploration-log args include `engine=colgrep`, `latency_ms`, and `fallback=false`, and fallback paths log `fallback_reason` (`missing_binary`, `timeout`, `oserror`, `nonzero_exit`, `bad_json`) plus elapsed time. Do not make daemon decisions from pre-2026-06-13 data.

2026-06-14 warmed synthetic soak: initialized the ColGREP index for `/mnt/raid0/llm/epyc-orchestrator/src` in 52s (`382` source units), then ran 32 `REPLEnvironment._code_search()` calls through the production wrapper with `REPL_COLGREP=1`, `REPL_COLGREP_BIN=/mnt/raid0/llm/UTILS/bin/colgrep`, and `REPL_COLGREP_PATH=/mnt/raid0/llm/epyc-orchestrator/src`. Results: `32/32` telemetry events, `0` wrapper fallbacks, p50 `208.5ms`, p90 `212ms`, p95 `213ms`, max `224ms`, every successful call returned 5 results, effective sequential throughput `2.44 calls/s`. A six-query quality smoke (`FinalSignal`, `ASTSecurityVisitor`, `create_repl_environment`, `_record_colgrep_telemetry`, `OpenAIChatRequest x_disable_repl`, and `execute_parallel_calls`) found the expected source file in top-5 for `6/6` queries. This closes the daemon latency gate for now: subprocess-per-query remains the default. Because this was a synthetic code-search soak, it does not prove future live turn-frequency behavior; revisit only if live `_exploration_log` data shows at least 20% of REPL turns issuing 2+ searches or a role sustaining at least 1 `code_search()`/s for 30s.

2026-06-14 version/index hygiene: installed a local versioned binary copy at `/mnt/raid0/llm/UTILS/bin/colgrep-1.2.0` and pinned `COLGREP_BIN` to that path in `epyc-orchestrator` `9b209d3`; `REPL_COLGREP_BIN` remains the override/rollback escape hatch. Runtime metadata records `COLGREP_VERSION=1.2.0` and expected SHA-256 `833e52aa6c40d090142fa132e3c75d3e792a4707474682a2496e3471f646f956`. Decision: do not add a commit hook or PostToolUse hook for ColGREP indexing yet. The measured full `src/` init cost was 52s, warmed search is fast, ColGREP auto-updates on search, and there is no evidence that a hook's CPU contention would buy enough freshness over manual `colgrep init /mnt/raid0/llm/epyc-orchestrator/src` after large source reshapes.

## Dependency Forks

| Outcome | Next action |
|---|---|
| Omega shows fewer turns and neutral/better accuracy | Keep the feature path and consider the next narrow suggestion/verbosity change. |
| Omega shows token savings but accuracy loss | Revert or gate the risky surface; keep only independently useful telemetry. |
| ColGREP soak is clean and latency acceptable | Leave subprocess-per-query in place; version pinning is complete. |
| ColGREP latency or call frequency trips daemon gate | Design the smallest daemon interface and add rollback controls before implementation. |

## Completed Scope

| Scope | Result | Ledger |
|---|---|---|
| S1 frecency | Landed. | [completed ledger](../completed/repl-turn-efficiency-completed-through-2026-05-28.md) |
| S2 combined operations | Landed. | [completed ledger](../completed/repl-turn-efficiency-completed-through-2026-05-28.md) |
| S3 contextual suggestions | Prototype landed, default-off, still Omega-gated. | [completed ledger](../completed/repl-turn-efficiency-completed-through-2026-05-28.md) |
| S5 dspy.RLM gaps | `_batch_llm_query()`, `workspace_scan()` frecency fallback, and `STUCK("reason")` landed through NIB2 tasks on 2026-04-17. | [completed ledger](../completed/repl-turn-efficiency-completed-through-2026-05-28.md) |
| S6 specialist bug fixes | Landed. | [completed ledger](../completed/repl-turn-efficiency-completed-through-2026-05-28.md) |
| S7 ColGREP default-on | Landed with rollback via `REPL_COLGREP=0`. | [completed ledger](../completed/repl-turn-efficiency-completed-through-2026-05-28.md) |

## Key Files

- `/mnt/raid0/llm/epyc-orchestrator/src/repl_environment/`
- `/mnt/raid0/llm/epyc-orchestrator/src/repl_environment/file_exploration.py`
- `/mnt/raid0/llm/epyc-orchestrator/src/repl_environment/code_search.py`
- `/mnt/raid0/llm/epyc-orchestrator/src/repl_environment/combined_ops.py`
- `/mnt/raid0/llm/epyc-orchestrator/src/repl_environment/context.py`
- [tool-output-compression.md](tool-output-compression.md)
- [meta-harness-optimization.md](meta-harness-optimization.md)
- [routing-and-optimization-index.md](routing-and-optimization-index.md)
- [research-evaluation-index.md](research-evaluation-index.md)
- [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md)

## Reporting Instructions

After S4 or soak work, update this handoff with the exact run, sample size, turns/task, token cost/task, accuracy delta, latency percentiles, and rollback decision. Update [research-evaluation-index.md](research-evaluation-index.md) and [master-handoff-index.md](master-handoff-index.md) if priority or scope changes.

## Research Intake Update — 2026-07-21 (RLM sub-call budget contracts + a verifiable span scorer)

- **[intake-868] SkyRL `examples/train/rlm`** (Apache-2.0, NovaSky-AI/Berkeley Sky Computing Lab) and **[intake-867]** its companion write-up.
  - Relevance: the training loop does not transfer (Ray + FSDP2 + vLLM engines, 4 GPUs), but the **REPL budget contracts are empirically-tuned and directly comparable to ours**: `rlm_query_batched` caps at **4 children per call**, a hard limit of **10 REPL rounds**, exactly **one repl block per response** (extras silently dropped), and a frozen-vs-policy switch for in-REPL sub-calls.
  - Highest-value portable artifact: `compute_metrics_multipaper` — a **character-interval precision/recall/F1** reward over verbatim extracted spans (merge/intersect interval arithmetic), ~60 lines, dependency-free, Apache-2.0. It scores character intervals rather than string equality, which **structurally sidesteps the comma-brittle substring-scorer bug class that has bitten us**. It is also a *verifiable* scorer, which intake-874/875 argue we should prefer over rubric judges wherever an objective anchor exists.
  - Context lives in a persistent Python REPL as a variable, never in the prompt — the same offloading model as our path.
  - **Prefix-cache warning worth noting:** the RLM scaffold re-appends the user query at the end of every turn rather than accumulating it, so successive turns share **no prefix**. Every turn is a cache miss on the query suffix — a real cost on bandwidth-bound CPU decode, and an argument against copying that scaffold shape verbatim.

- [ ] Candidate: port the interval-F1 span scorer as an eval-tower scorer for evidence-grounded retrieval (also relevant to [internal-kb-rag.md](internal-kb-rag.md)). [intake-868]

## Deep-Dive Correction — 2026-07-21 (The scorer port is WITHDRAWN; take the prompt instead)

Supersedes the actionable in the 2026-07-21 intake section above. A source-level read of the SkyRL repo (all 12 files fetched; note the directory has **no README** — the earlier framing could not have come from one) overturns the recommendation.

**WITHDRAWN — do not port `compute_metrics_multipaper`.** Three findings, each sufficient on its own:
1. **It is dead code upstream.** Zero call sites across the entire example directory (`evidence_rewards.py:57-73`). Its sibling `compute_child_rlm_metrics` is also never called.
2. **SkyRL's actual reward is a closed-model LLM judge** — `judge_reward` (`:239-365`), `JUDGE_MODEL = "gpt-5.4-mini-2026-03-17"` against `api.openai.com`, hard-failing without `OPENAI_API_KEY`. The authors had the interval metric available and chose a rubric judge. That is evidence **against** the metric's sufficiency, not for it — inverting the intake-874/875 "prefer verifiable anchors" argument that justified the port.
3. **It reproduces our brittleness scar with an added bug.** Offsets are `str.find`-recovered, not annotated. At `:176-180`, a predicted span that does not match exactly is **dropped from the precision denominator rather than penalized** — a model emitting 10 spans with 9 hallucinated and 1 exact scores **precision 1.0**. Symmetrically at `:167-169` unmatched GT spans drop from recall, and if none match the item scores 0.0, making infra failure indistinguishable from model failure. `find` also returns only the first occurrence, while the prompt explicitly demands extracting repeated facts separately.

Correction to the earlier note: the blocker is NOT missing character-offset annotations (those are derived). It is that only **2 of ~30 adapters populate `context`** (`dataset_adapters.py:1550`, `:2435`), no suite stores span-level GT, and it grades a verbatim-quote-list task we do not run. The 58-line interval arithmetic (`:16-73`, stdlib-only) is correct and elegant, but it was never the hard part.

**PROMOTED — `MULTIPAPER_CHILD_SYSTEM_PROMPT` (`evidence_rlm_env.py:120-224`) is the repo's real portable artifact.** It is a battle-tuned REPL-discipline prompt and it is exactly the S4 Omega A/B arm this handoff lacks: a turn **floor** as well as a ceiling ("HARD LIMIT of 10 rounds, aim for 5-7, do NOT return after only 2-3 rounds — that is too shallow", `:153-156`), a mandated 5-turn search→expand→extract→verify procedure (`:185-223`), and a same-block causality constraint (`:137-140` — cannot `extract_section()` on `search()` results in the same block; never `FINAL_VAR` in the same block as an extraction).

Also correcting two earlier claims: the 4-children / 10-round budgets are **prompt text only, NOT enforced in code** (no `[:4]`/`max_rounds`/`max_turns` in `rlm_generator.py`), and the OpenRouter frozen model is **opt-in, not the default** (`frozen_openrouter_model: Optional[str] = None`, `rlm_config.py:20`).

- [ ] S4 Omega A/B candidate: adopt the turn-floor + mandated-procedure shape from `MULTIPAPER_CHILD_SYSTEM_PROMPT` as the intervention arm — this handoff previously had none.
- [ ] Only if an evidence-retrieval suite is separately justified: plumb HotpotQA's already-loaded-but-DISCARDED `supporting_facts` (`dataset_adapters.py:1524`) into the emitted record to create our first span-level GT, and write the interval metric ourselves with a robust matcher that counts unmatched predictions as **false positives**. Do NOT adopt SkyRL's `find`-based recovery.
