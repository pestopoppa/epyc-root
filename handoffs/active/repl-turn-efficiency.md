# REPL Turn Efficiency - Active Gates

> **Fold destination** (BRF-T1-F14, BRF-T1-1, route 1a, 2026-11-02): absorbs 1 handoff(s) as `## Track:` sections at the end of this file (`qwen-chat-template-evaluation.md`). The body above the first track is the former `repl-turn-efficiency.md`.

**Scratch**: `/mnt/raid0/llm/tmp/codex-ni-20261024-s4-turns/`, `/mnt/raid0/llm/tmp/codex-ni-20261024-s4-omega/` · worktrees: `/mnt/raid0/llm/worktrees/codex-ni-20261024-s4-*`

**Status**: COMPACTED 2026-05-28 - core REPL efficiency changes landed; active gate is S4 Omega A/B.
**Created**: 2026-04-09
**Updated**: 2026-08-13
**Priority**: MEDIUM
**Categories**: agent_architecture
**Depends on**: None
**Parent index**: [research-evaluation-index.md](research-evaluation-index.md)
**Completed ledger**: [repl-turn-efficiency-completed-through-2026-05-28.md](../completed/repl-turn-efficiency-completed-through-2026-05-28.md)

## Executor Start Here

Do not add new REPL tools before S4. **Exception (operator D2, 2026-09-26):** embedding-backed retrieval (`repl-embedding-retrieval.md`, UFH-12) is waived from this gate, conditional on its Phase 2 passing the pre-registered kill criterion; if it fails, the waiver lapses. The current risk is whether the shipped efficiency features reduce turns and token cost without accuracy loss. Treat the historical frecency, combined operation, dspy.RLM, and ColGREP implementation details as completed unless a regression is found.

## Outstanding Tasks

- [ ] **S4 Omega A/B**: measure turns per task, token cost per task, and accuracy delta. This gates suggestion, verbosity, and any extra tool-surface changes.
  - [x] **S4-T1 — BUG: turns per task are never recorded.** `ChatResponse.turns` ✅ 2026-11-01 [belief: cc]
    (`src/api/models/responses.py:97`) is populated on every path
    (`chat_pipeline/stages.py:117`, `direct_stage.py:144,:287`) and `RoleResult.turns` exists
    (`scripts/benchmark/seeding_types.py:579`), but the `RoleResult(...)` constructor in
    `scripts/benchmark/seeding_eval.py:411-470` copies ~50 response fields and not `turns`, so
    every seeding record carries `turns=0` and the S4 metric has never had data. Fix: add
    `turns=resp.get("turns", 0)` beside `tokens_generated`; add a test asserting a REPL-mode
    fixture response with `turns=3` lands as `RoleResult.turns == 3`; backfill is impossible
    (never captured) — note the era boundary in the record. Acceptance: one seeding run shows
    non-zero `turns` on `frontdoor:repl` rows. Zero inference to fix; one short run to prove.
    - [x] **S4-T1.SRC — Preserve turns in seeding RoleResult output.** ✅ 2026-10-24: source repair is implemented and published: `seeding_eval.py` copies response `turns` into `RoleResult`; the REPL-mode fixture asserts `turns=3` survives `asdict` serialization, and absent `turns` remains `0`. Commit: orchestrator `7c0f2929ebef839fdf87edf6c20adc47a564035c`. Corrected validation ran from `/mnt/raid0/llm/worktrees/codex-ni-20261024-s4-orch` at that exact HEAD under the q1 calendar grant; `pwd` and HEAD were captured and `pytest tests/unit/test_seeding_eval.py -q` passed 22 tests (one OpenTelemetry deprecation warning) in 1.85s, rc 0. The earlier reported 22-test and final focused-test passes remain retracted as evidence because they ran from the canonical shared checkout; the private-snapshot run provides new valid verification. Pre-fix records did not capture turns, so historical zeros cannot be backfilled. The S4-T1 live-run acceptance remains open; no live run is claimed.
    **Comparability target (added 2026-09-24):** the AutoKernel opencode seat now records a per-call row,
    `epyc.autokernel.actor_call_metrics.v1` (research `lane/ak-turns-20260924` `0bf2d7c2`,
    `loop/actor_metrics.py`; INF-78 OAB-4m). It has steps, tool calls by name, compactions,
    prompt/decoded/cache-read/cache-write tokens, first/max context, and predicted schema-valid/repair-ran. Where
    S4-T1 adds fields beyond `turns`, use the same names and definitions, so the orchestrator and the opencode seat
    land in comparable columns for INF-78 OAB-4. In particular, **"decoded" there means `tokens.output` summed over
    steps, reasoning tokens included**: say which one `tokens_generated` means, and keep the two convertible. One
    difference: the seat counts an opencode *step* (one assistant message), while `ChatResponse.turns` counts REPL
    turns. Record which unit a row uses, and never equate the two. Vocabulary and traps:
    `autokernel-orchestrator-actor-backend.md` → *Techniques learned in the opencode seat* §2.
  - [x] **S4-T2 — the Omega A/B has an ARM but no RUNNER.** ✅ 2026-10-24. The intervention prompt landed
    2026-08-13 (box below, `orchestration/prompts/root_lm_system.s4_omega.md`), yet nothing selects
    it per arm, pins the question set, or emits turns/tokens/accuracy per arm. Write
    `scripts/benchmark/s4_omega_ab.py` (or a `seeding_eval` mode): two arms × one pinned suite,
    same role/mode (`frontdoor:repl`), records `turns` (needs S4-T1), `tokens_generated`,
    `prompt_tokens`, `passed`, elapsed. Acceptance: a dry run on 3 questions produces two arm
    records with the four columns; the real run is inference-gated. Overlap: schema/parse failures
    on this path are TD-21.1 (`typed-decision-plane.md`) — do not re-file; the orchestrator-backend
    program (INF-78, [`autokernel-orchestrator-actor-backend.md`](autokernel-orchestrator-actor-backend.md))
    consumes this same per-call `turns` field as its actor-cost metric.
    Runner source landed on orchestrator `main` as `be208213775a032aefde26a3c1df4ac4ca2d445e` (feature integration `87134e1f8b39de6dc48d714248c75126ad8c16ee`; validated producer source `737773b4e0f89f378c5c68b620597fba41eec666`; exactly the three runner/suite/test blobs). Grant-backed v2 validation passed 9 focused tests (one deprecation warning) and wrote six explicitly synthetic records for the pinned three-question/two-arm dry run. No live API or inference call was made; the outer S4 Omega A/B and S4-T1 live proof remain inference-gated/open.
    - [x] **S4-T2.PROMPT — capture request-local generation prompt usage.** ✅ 2026-10-24: `ChatResponse.prompt_tokens` sums exact backend-reported generation prompt usage within the request, including propagated parallel contexts. No calls, missing usage, pending calls, or an unmetered input-formalizer attempt leave it null; embedding work is excluded. Seeding preserves this separately from legacy decoded `tokens_used`, including explicit zero. Source pin `6e6d85ade9c29f86a58ca5bfaeff4132a2dd39b0` passed 24 focused tests with two warnings in 4.31 s under its calendar grant. No historical backfill, full-cost claim, API reload, or live A/B is asserted; source publication is recorded in the linked progress shard `progress/2026-10/2026-10-24-request_prompt_usage.md`.
    - [x] **S4-T2.OUTPUT — capture request-local native decoded-output usage.** ✅ 2026-10-24: `ChatResponse.output_tokens_reported` is a nullable native server-reported count populated only from native server-reported decoded usage (`/completion.tokens_predicted`, chat `usage.completion_tokens`, or a terminal stream count). `output_tokens_status` and `output_tokens_sources` record completeness and parser provenance; an unknown aggregate may retain provenance from native calls that completed before a pending or unmetered call. Explicit native zero is valid. Seeding carries separate optional output count/status/source fields. Existing `tokens_generated` and `tokens_used` semantics, score gates, and historical records remain unchanged. Validation: one failing-case preflight passed; 31 focused tests passed, 161 deselected, one OpenTelemetry warning (source pin `50fcf0f9ea1401257c1e637699c8829d45885f15`, 2026-10-24). Source closeout: `progress/2026-10/2026-10-24-request_output_usage.md`. This does not claim whole-request monetary cost or an Omega A/B result; the outer S4 Omega A/B remains open.
  - [ ] **S4-OMEGA-PILOT-V2 — run the isolated 16-item S4 Omega mixed-domain pilot (baseline vs Omega intervention arm) on a keeper-granted backend.** [inference] (filed 2026-11-02, row `handoff-s4-omega-isolated-pilot-v2-20261102`, supersedes v1 `handoff-s4-omega-isolated-pilot-v1-20261101`)
    Done when native self-hashed records for all 16 paired items (32 arm records) are filed with turns, native prompt tokens, legacy generated tokens and native reported output tokens (missingness explicit), pass discordances and elapsed time per arm, or the capture is filed as partial/refused. Convenience-panel pilot only: not non-inferiority, efficacy, deployment or production-placement evidence.
    Identity: model Qwen3.6-35B-A3B-MTP-Q8_0 (role `frontdoor:repl`, edge SHA-256 `07b181ee...dac6a9`), build production CPU kernel `kernels/production/cpu/llama-server` (SHA-256 `4483bcfc...bb648c`, ggml linkage verified; GGML_IQK=1; `-np 1 -c 32768 -ub 2048 --flash-attn on -ctk q8_0 -ctv q8_0 --no-mmap --cache-ram 0 --spec-type draft-mtp --spec-draft-n-max 4`), harness `omega_supervisor.py` driving the existing s4_omega_ab runner over the frozen 16-item core_v2 panel (suite SHA-256 `668ff4ec...a60c32`, source commit `9e138e3a3e22ecf8c57cd5bf50beed571d107b54`), metric turns per task (lower is better), native prompt tokens (lower is better), native reported output tokens and pass count (higher is better), rule tool-liveness gate PASS = all 32 records complete with valid request-local turns, prompt-token, generated-token and scorer fields and at least one nonzero turn, otherwise FAIL/incomplete; pass counts and discordances are pilot observations with no threshold, region one granted CPU quarter (keeper `FILLER_CPUS`/`FILLER_THREADS`, GPU not used), est: provisional 12000 s, pilot: bounded to 16 items x 2 arms (32 records). Stop rule: stop-on-answer (the 32 complete records are the answer); futility-only stop on a keeper stop or deadline between pairs (the supervisor declines to start a pair with under 660 s left, preserves the partial capture and reports incomplete) or on a backend, correlation or pin-verification fault.
- [x] **ColGREP post-telemetry soak check**: 2026-06-14 warmed synthetic REPL soak closed the latency/fallback/quality portion; see telemetry below.
- [x] **Cold-start daemon decision**: do not build now. The measured latency gate did not fire; revisit only if a future live workload trips the multi-search or sustained-call-rate gates.
- [x] **Version/index hygiene**: `epyc-orchestrator` `9b209d3` pins the default runtime path to `/mnt/raid0/llm/UTILS/bin/colgrep-1.2.0`; no ColGREP re-index-on-commit hook for now.

### Research intake 2026-10-22 — Locals + Beacon (intake-2386..2460)

- [x] **RTE-PFX-LB1 — Before the repaired prefix-order A/B runs, read the target role's GGUF architecture; if it is a recurrent hybrid, add an arm that places a message_delimiters checkpoint at the stable/volatile boundary so a missing junction checkpoint cannot produce a false negative (intake-2386).** ✅ 2026-10-22
  - *(2026-10-22, workspace-f8 / locals-a.)* Done: architecture read for all three local roles (all recurrent hybrids), arm specified in the A/B bullet above ("Junction-checkpoint arm").

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
- [tool-output-compression.md](context-and-token-economy.md#track-tool-output-compression)
- [meta-harness-optimization.md](../completed/meta-harness-optimization.md)
- [routing-and-optimization-index.md](routing-and-optimization-index.md)
- [research-evaluation-index.md](research-evaluation-index.md)
- [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md)

## Reporting Instructions

After S4 or soak work, update this handoff with the exact run, sample size, turns/task, token cost/task, accuracy delta, latency percentiles, and rollback decision. Update [research-evaluation-index.md](research-evaluation-index.md) and [master-handoff-index.md](master-handoff-index.md) if priority or scope changes.

## Research Intake Update — 2026-07-21 (RLM sub-call budget contracts + a verifiable span scorer)

### Scaffold A/B reporting contract — Main Model Token Efficiency

For each arm, report **Main Model Token Efficiency** as `mean(reward) / mean(main-model trajectory tokens)`, normalized by the no-scaffold arm's value within the same suite, role, and task set (baseline = `1.0`). Include mean reward, mean main-model trajectory tokens, mean total trajectory tokens (main plus all sub-calls), wall-clock seconds, task set, role, and sample count beside the normalized value. Do not pool different task sets or role pins. Treat missing token counts as incomplete records, not zero; report zero-token cases separately. Interpret the ratio with reward and total-token/wall-clock columns: an improved main-model-only ratio alongside increased total tokens identifies cost relocation rather than total efficiency improvement. This is a reporting contract, not a measured A/B result or a runner implementation.

- **[intake-868] SkyRL `examples/train/rlm`** (Apache-2.0, NovaSky-AI/Berkeley Sky Computing Lab) and **[intake-867]** its companion write-up.
  - Relevance: the training loop does not transfer (Ray + FSDP2 + vLLM engines, 4 GPUs), but the **REPL budget contracts are empirically-tuned and directly comparable to ours**: `rlm_query_batched` caps at **4 children per call**, a hard limit of **10 REPL rounds**, exactly **one repl block per response** (extras silently dropped), and a frozen-vs-policy switch for in-REPL sub-calls.
  - Highest-value portable artifact: `compute_metrics_multipaper` — a **character-interval precision/recall/F1** reward over verbatim extracted spans (merge/intersect interval arithmetic), ~60 lines, dependency-free, Apache-2.0. It scores character intervals rather than string equality, which **structurally sidesteps the comma-brittle substring-scorer bug class that has bitten us**. It is also a *verifiable* scorer, which intake-874/875 argue we should prefer over rubric judges wherever an objective anchor exists.
  - Context lives in a persistent Python REPL as a variable, never in the prompt — the same offloading model as our path.
  - **Prefix-cache warning worth noting:** the RLM scaffold re-appends the user query at the end of every turn rather than accumulating it, so successive turns share **no prefix**. Every turn is a cache miss on the query suffix — a real cost on bandwidth-bound CPU decode, and an argument against copying that scaffold shape verbatim.

- [ ] Candidate: port the interval-F1 span scorer as an eval-tower scorer for evidence-grounded retrieval (also relevant to [internal-kb-rag.md](knowledge-pipelines.md)). [intake-868]

## Deep-Dive Correction — 2026-07-21 (The scorer port is WITHDRAWN; take the prompt instead)

Supersedes the actionable in the 2026-07-21 intake section above. A source-level read of the SkyRL repo (all 12 files fetched; note the directory has **no README** — the earlier framing could not have come from one) overturns the recommendation.

**WITHDRAWN — do not port `compute_metrics_multipaper`.** Three findings, each sufficient on its own:
1. **It is dead code upstream.** Zero call sites across the entire example directory (`evidence_rewards.py:57-73`). Its sibling `compute_child_rlm_metrics` is also never called.
2. **SkyRL's actual reward is a closed-model LLM judge** — `judge_reward` (`:239-365`), `JUDGE_MODEL = "gpt-5.4-mini-2026-03-17"` against `api.openai.com`, hard-failing without `OPENAI_API_KEY`. The authors had the interval metric available and chose a rubric judge. That is evidence **against** the metric's sufficiency, not for it — inverting the intake-874/875 "prefer verifiable anchors" argument that justified the port.
3. **It reproduces our brittleness scar with an added bug.** Offsets are `str.find`-recovered, not annotated. At `:176-180`, a predicted span that does not match exactly is **dropped from the precision denominator rather than penalized** — a model emitting 10 spans with 9 hallucinated and 1 exact scores **precision 1.0**. Symmetrically at `:167-169` unmatched GT spans drop from recall, and if none match the item scores 0.0, making infra failure indistinguishable from model failure. `find` also returns only the first occurrence, while the prompt explicitly demands extracting repeated facts separately.

Correction to the earlier note: the blocker is NOT missing character-offset annotations (those are derived). It is that only **2 of ~30 adapters populate `context`** (`dataset_adapters.py:1550`, `:2435`), no suite stores span-level GT, and it grades a verbatim-quote-list task we do not run. The 58-line interval arithmetic (`:16-73`, stdlib-only) is correct and elegant, but it was never the hard part.

**PROMOTED — `MULTIPAPER_CHILD_SYSTEM_PROMPT` (`evidence_rlm_env.py:120-224`) is the repo's real portable artifact.** It is a battle-tuned REPL-discipline prompt and it is exactly the S4 Omega A/B arm this handoff lacks: a turn **floor** as well as a ceiling ("HARD LIMIT of 10 rounds, aim for 5-7, do NOT return after only 2-3 rounds — that is too shallow", `:153-156`), a mandated 5-turn search→expand→extract→verify procedure (`:185-223`), and a same-block causality constraint (`:137-140` — cannot `extract_section()` on `search()` results in the same block; never `FINAL_VAR` in the same block as an extraction).

Also correcting two earlier claims: the 4-children / 10-round budgets are **prompt text only, NOT enforced in code** (no `[:4]`/`max_rounds`/`max_turns` in `rlm_generator.py`), and the OpenRouter frozen model is **opt-in, not the default** (`frozen_openrouter_model: Optional[str] = None`, `rlm_config.py:20`).

- [x] S4 Omega A/B candidate: adopt the turn-floor + mandated-procedure shape from `MULTIPAPER_CHILD_SYSTEM_PROMPT` as the intervention arm — this handoff previously had none. ✅ **ARM LANDED 2026-08-13** — orchestrator `orchestration/prompts/root_lm_system.s4_omega.md` (default-OFF; select via `PROMPT_VARIANT__root_lm_system=s4_omega`). Adopts the SkyRL `MULTIPAPER_CHILD_SYSTEM_PROMPT` shape adapted to our REPL surface: turn FLOOR ("HARD LIMIT of 10 rounds, aim for 5-7, do NOT return after only 2-3 rounds — that is too shallow"), a mandated gather→expand→verify→answer procedure, same-block causality (cannot use results before the block executes; never FINAL in the same block as a tool call whose result you need), and the one-block/no-comment/no-narration discipline. 3 new resolver tests (`tests/unit/test_prompt_resolver.py::TestS4OmegaInterventionArm`), 52 passed. Default prompt untouched; the A/B now has both arms.
#### S4 arms — design note RUS-1: best-of-K REPL arm and selector-validity rules (2026-10-21, zero compute)

A best-of-K REPL arm sits beside the fixed-plan arm (LRLM-1, next note) and the S4 Omega arm.

- **K**: K trajectories per task, reported at widths K=1, 2, 4, 8 at least (see clause 2).
- **Selection rule**: plurality-answer filter first, then argmax of summed log verbalised confidence times trace length. Implement the argmax: the formula text says lower is better, but only the argmax reading is consistent (intake-2284#record).
- **Cost columns**: total tokens across K, wall-clock, decode versus prefill tokens, cache share. K parallel trajectories contend for the bandwidth-bound host, so wall-clock is measured with all K running, not extrapolated from K=1.

Mandatory clauses:
1. The selector table has a no-filter row beside the plurality-filter row, a shorter-length row (diagnostic only: unvalidated on our roles, no within-question data, RUS-2 2026-10-21), a lower review-ratio row (only for arms that record reasoning traces; answer-text ratios are not usable, RUS-2) and a lower failed-step-fraction row. The report states per task the share where oracle coverage exceeds selected accuracy and where the plurality is wrong (intake-2300#record).
2. Any arm using a vote or plurality selector reports selected accuracy at three or more widths (K=1, 2, 4, 8 at least) beside oracle coverage, so a rise-then-fall curve is detectable: more calls can lower accuracy under plurality selection without a checker (intake-2312#record).
3. Tasks with no deterministic checker are labelled verifier-free; the vote selector is the declared-weak arm and the single larger-role answer is the comparator (intake-2296#record).
4. Best-of-K and any worker-versus-architect comparator are compared at equal measured wall-seconds, with K per model set by its own seconds per attempt.
5. Pairwise discrete CAPA among the K samples is reported beside the distinct-answer count (intake-2323#record).
6. Verbalised confidence is a selector candidate scored against the checker and never a claim-tuple field.

#### S4 arms — design note LRLM-1: fixed-plan long-input arm (2026-10-21, zero compute)

**Combinator map** (REPL helper to lambda-RLM combinator):
- `_batch_llm_query` maps to Split-Map-Merge (split the input, map one sub-query over chunks in a batch, merge the answers).
- `parallel_dispatch` maps to Split-Map-Parse-Cross (map over chunks or sources, parse each result, cross-reference across them).
- workspace_scan maps to Split-Peek-Filter-Map (peek at each chunk cheaply, filter, map the full query only over survivors).

**Long-input tasks with a fixed task-type plan**: summarise and aggregate tasks go to Split-Map-Merge; multi-source comparison tasks to Split-Map-Parse-Cross; needle and locate tasks to Split-Peek-Filter-Map. Tasks with no fixed task-type plan stay on the open-ended REPL only.

**Arm definition**: a declared-parameter fixed-plan arm (task-type plan table plus declared chunk size, overlap and fan-out width, no model-chosen control flow) is run against the open-ended REPL on the same tasks. Contrast with the finding that regex over the context won with zero sub-LLM calls (intake-2241#record): the open-ended REPL can beat any fan-out plan, so the fixed-plan arm is compared against it and not assumed better.

**Three definitions**:
1. **Chunk-size search**: chunk size is chosen by sparse sampling of at least 5 samples per candidate size on a dev set, instead of a closed-form k*; the measured optimum and the closed form disagree (intake-2264#record).
2. **Cross-chunk-dependence screen**: a single-shot versus chunked score gap on a small dev set, run before routing a task class to fan-out.
3. **Digit-menu task-type classifier**: the model answers with one digit from a numbered menu of task types, and that digit feeds a deterministic plan table; a prototype definition (intake-2275#record).

**Adapter estimate**: the reference code needs only an OpenAI-style client with a base_url, so pointing it at llama-server is an adapter of about 0.5 day, not a blocker.

**Gating**: runs wait for the UFH-13 thesis experiment to unfreeze HS-19b-d.

- [x] ~~Only if an evidence-retrieval suite is separately justified: plumb HotpotQA's already-loaded-but-DISCARDED `supporting_facts` (`dataset_adapters.py:1524`) into the emitted record to create our first span-level GT, and write the interval metric ourselves with a robust matcher that counts unmatched predictions as **false positives**. Do NOT adopt SkyRL's `find`-based recovery. **DISPOSITION 2026-08-13 (mainB): condition NOT met — do not implement.** The deep-dive correction above (line ~95) already established the blocker: only 2 of ~30 adapters populate `context`, **no suite stores span-level GT**, and it grades a verbatim-quote-list task we do not run. Re-verified at HEAD: `supporting_facts` is still loaded-and-dropped at `dataset_adapters.py:1525` (single occurrence, never emitted); the HotpotQA adapter is a QA benchmark (`scoring_method: f1` on `<answer>`), not an evidence-retrieval suite; the KB-RAG suite (`internal-kb-rag.md` K7) measures document recall@k over our wiki corpus with template cases, not span-level GT from real HotpotQA `supporting_facts`. Per the "price it first" discipline, wiring a span-level GT emitter with no consuming suite adds volume without warrant. Reopen only when a suite that consumes span-level evidence is separately justified.~~ (closed 2026-10-29 audit: SUPERSEDED → repl-turn-efficiency.md:179 DISPOSITION 2026-08-13 (mainB): condition NOT met, do not implement; reopen only if a span-level evidence suite is separately justified)

### Audit catch 2026-07-21 — two cheap levers from intake-867 that were never filed

- [ ] **Strategy-prompt-length ablation.** intake-867 measured an explicit task-strategy prompt cutting Sonnet 4.6 rollout time **90s → 30s (3x)**, and a 200-token compressed variant converging *lower and less stably* than the 1500-token original. Both directions matter for us: our agent roles may be under-specified (leaving 3x turn-time on the table) or over-compressed (paying instability for token savings). Pure prompt-side A/B on existing roles — no training, modest inference. Candidate arm alongside the S4 Omega A/B above.
- [ ] **Prefix-cache audit of our REPL scaffold.** intake-867's scaffold re-appends the user query every turn, so successive turns share NO prefix — every turn is a full-prompt cache miss, which on bandwidth-bound CPU decode is a real per-turn tax. Zero-inference first step: inspect our REPL loop's prompt construction and measure slot-cache hit rate across turns (llama-server `/slots` + `--slot-save-path` already exist). If our scaffold has the same shape, reordering the prompt layout is a free prefill win. **Pricing model (2026-09-07, intake-1333#02, dive-verified)**: our REPL scaffold re-appends the user query every turn so successive turns share no prefix, which under Eq. 4 means **paying full list price on the dominant term**. Restate the audit's success criterion as **"raise `h`"** (the cache-read fraction), using the journal-measured **h = 0.9845** on the Claude Code plane as the contrast case showing what a cache-shaped scaffold achieves — the same `h` DCP-9a computes in [`delegation-context-preassembly.md`](context-and-token-economy.md#track-delegation-context-preassembly). The 2026-08-13 checkpoint below already verified the static premise with a *different* mechanism (per-turn `state`/`context`/first-turn-only `reference_code` rendered before the fixed task block), so this audit is **narrowing, not re-opening**. Zero compute.

### RTE-Prefix audit checkpoint — 2026-08-13

The static premise is verified, with a different mechanism than SkyRL: the frontdoor prompt renders per-turn `state`, `context`, and first-turn-only `reference_code` before the fixed task/instruction, so later turns share only the earlier system/tools/rules prefix. Orchestrator commits `d977454e` and `2c4087b7` correct the cache counters and add a default-off prefix-stable order plus an A/B script. The auditor reran the claimed focused suite: **353 passed**.

- [x] **RTE-Prefix static prompt audit ✅ 2026-08-13**: verified live `graph/helpers.py` uses a minimal `PromptBuilder`, first-turn-only corpus context, executed REPL output/error spillover, and dynamic gathered/workspace/session suffixes. Frontdoor bypass retains llama-server `cache_prompt` but clears the custom PrefixRouter slot id, correcting the first-wave claim that the live payload pins `id_slot`.
- [x] **RTE-Prefix cache-token instrumentation repair ✅ 2026-08-13**: `/slots` reads v9 `n_prompt_tokens`/`n_prompt_tokens_cache`; inference telemetry reads `timings.cache_n` rather than total slot occupancy. The separate v9 slot-state mapping remains open.
- [x] **RTE-Prefix default-off stable ordering implementation ✅ 2026-08-13**: the feature flag, prompt rendering order, builder wiring, and unit coverage are present; no runtime default was flipped.
- [x] **Repair the RTE-Prefix A/B harness before spending compute**: use the live minimal builder and real turn state/executed-output semantics, include the live gathered/workspace/session/budget suffixes, inject corpus only on turn 1, isolate/reset the pinned slot between arms, map v9 `is_processing`, fail closed on arm/metric errors, and add harness regression tests. The current script's “REAL frontdoor sequence” claim is not decision-grade. ✅ 2026-10-31 — APP `b85b44f12ec857fc0249bc956e239feadfe92ca4`; [implementation evidence](https://github.com/pestopoppa/epyc-orchestrator/blob/b85b44f12ec857fc0249bc956e239feadfe92ca4/docs/evidence/rte-prefix-harness-20261031/REPORT.md). [no-belief: model-free implementation checks]
  - [x] **RTE frontdoor rowflow source preparation** ✅ 2026-11-01 — [the v15 source packet](../../artifacts/codex-gen/rte-frontdoor-rowflow-20261101/) has isolated qualification/production attempts, grant/stop checks, an actual owner-checker acceptance unit and a production cleanup predicate; five offline controls and source seals passed. Codex-gen erroneously published the older `codex-ni-rte-frontdoor-quarter-20261031` row despite the RTE-LOG-1 production-logging lineage already being parked after three failures. The source tests did not establish qualification or `/chat` acceptance; this publication must not be used to evade that park. [no-belief: source preparation and erroneous publication only]
  - [ ] **RTE-LOG-1 parked-lineage publication reconciliation** — at the owner/keeper boundary, safely reconcile and, if still present, withdraw the mistakenly republished `codex-ni-rte-frontdoor-quarter-20261031` row without interrupting any active work. Preserve the source packet as review evidence; do not retry, rearm, or publish this lineage while it is parked.
  - Completion limits: two native-entry tests cover exact executed REPL output, live context, slot receipts and failure journaling. The recorded result is matched native PROMPT replay only; fixed legacy-first timing is not a gain. No model A/B, semantic-quality run, or measurement verdict. Normal hook returned 0; PII-native capture remains unavailable.
- [ ] **Run the repaired RTE-Prefix live A/B and semantic gate** under a granted inference window; record isolated-arm cached/processed tokens and prefill latency plus S4 turns/task, token cost/task, and accuracy. Keep the default off unless cache benefit and neutral/better task behavior both pass.
  - **Append-only running-state arm (added by RTE-PFX-1 item 3, 2026-10-21; the run stays gated on the harness repair above).** Arm `state-append`: the running-state block is append-only across turns (new variables and the new turn's output are appended after the previous turn's state text, nothing earlier is rewritten, the `Turn N` counter moves out of the block into the volatile tail) versus arm `state-rewrite`: today's block rebuilt in place by `get_state()` each turn, with `prefix_stable_order` on in both arms so the arms differ only in the state block. Same tasks, role pin, slot reset between arms. Per turn report cached and processed prompt tokens (`timings.cache_n`, `prompt_n`), prefill latency, and the first-divergence offset from `scripts/analysis/rte_pfx1_first_divergence.py`; S4 turns per task, token cost per task and accuracy as the semantic gate (append-only state grows without bound, so report prompt tokens at the last turn beside the cache saving).
  - **Junction-checkpoint arm (added by RTE-PFX-LB1, 2026-10-22; the run stays gated on the harness repair above).** Target role `frontdoor` = Qwen3.6-35B-A3B-MTP-Q8_0, GGUF `general.architecture = qwen35moe` with `qwen35moe.ssm.*` keys and `full_attention_interval = 4`: a RECURRENT HYBRID (read header-only by `scripts/analysis/gguf_arch_probe.py`, orchestrator branch `f8/locals-a-orch-20261022` commit `567b43c0`; the other two local roles are hybrids too: coder_escalation Qwen3.8-27B `qwen35`, architect_general Flash-Next `qwen4exp`). A hybrid cannot reuse a prefix from position-keyed KV alone: it needs a recurrent-state checkpoint at the reuse boundary, so a stable-prefix arm that places no checkpoint at the stable/volatile junction can measure a cache miss that is the missing checkpoint and not the prefix order (a false negative). Arm `junction-ckpt`: identical to the `prefix_stable_order` arm, but the stable block is its own message and the request carries `message_delimiters` so v10 checkpoints at the stable/volatile boundary (chat lane; on the rebuilt /completion lane this needs the KPF-LB1.1 flag, so run the arm on the chat lane). Report `timings.cache_n` / `prompt_n` per turn for `junction-ckpt` beside the no-checkpoint stable arm; a stable-order null is valid evidence against the layout change ONLY if `junction-ckpt` is also null.
  - [ ] **RTE-PFX2-QN-V3 — run the quarter-native same-prefix cache mechanism probe (RTE-PFX-2 lineage) on a keeper-granted window.** [inference] (filed 2026-11-02, row `handoff-rte-pfx2-quarter-native-v3-20261102`, supersedes v2 `handoff-rte-pfx2-quarter-native-v2-20261101`)
    Done when 5 complete trials per arm (3 arms, 4 native metric rows per trial) are filed with uncached prompt-token totals, per-sibling cache_n against 0.9 x the tokenized prefix, and TTFT distributions, or the capture is filed as incomplete. Mechanism probe only: no semantic-quality or feature-promotion claim; dryrun, incomplete and failed trials are excluded.
    Identity: model Qwen3.6-35B-A3B-MTP-Q8_0 (role frontdoor, 37801097504 bytes, edge SHA-256 `07b181ee...dac6a9`), build production CPU kernel `kernels/production/cpu/llama-server` (SHA-256 `4483bcfc...bb648c`, ggml linkage verified; GGML_IQK=1; `-np 4 -c 262144 -ub 2048 --flash-attn on -ctk q8_0 -ctv q8_0 --mlock --no-mmap --cache-ram 32768 --ctx-checkpoints 32 --spec-type draft-mtp --spec-draft-n-max 4`), harness `probe.py` via `supervisor.py` (arms simultaneous, hold_first_tok, hold_first_end; salted tokenized prefix `prefix.txt` SHA-256 `d95770fb...1357a`; seed 20261021; 5 trials per arm, 4 siblings), metric uncached prompt tokens per trial (lower is better), per-sibling cache_n (higher is better) and TTFT ms (lower is better), rule a sibling counts as a cache hit when cache_n >= 0.9 x the tokenized prefix, and the run is valid with real-phase rc=0, 5 complete trials per arm, 4 native metric rows per trial and pinned server/runtime header, region whole-host CPUs 0-95 with GPU quiet exclusive (the qualification dry run uses one quarter slice and is excluded), est: provisional 5400 s, pilot: bounded to 5 trials x 3 arms x 4 siblings (one server, no stack). Stop rule: stop-on-answer (the 15 complete trials are the answer); futility-only stop on a keeper stop or deadline (the supervisor refuses to start with under 150 s left), a server or pin-verification fault, or an owned-process drain failure.


## 2026-07-25 — intake Stage-2a dive: RLM prefill→decode caution (intake-803 was mis-filed)

_Via `/research-intake` Stage-2 2026-07-25; see [`intake-derived-work-2026-07-25.md`](frontier-lab-automation.md)._

- [x] **Standing caution on RLM-shaped fan-out.** intake-803 was filed keeping the promotional half of its source and dropping every negative — including the load-bearing one: in Needle-in-Haystack the plain LLM's tokens are almost entirely **prefill** while the RLM's are largely **decode**, because the RLM writes code to solve *and* writes code again to emit its answer. RLM structurally converts **compute-bound prefill into bandwidth-bound decode** — directionally adverse on this box. Also dropped: *"In all cases, the RLM increases the time required to finish the job significantly"* — a **universal wall-clock regression** across all four environments. ✅ 2026-11-02 [belief: cc]
- [ ] Adopt **Main Model Token Efficiency** (mean reward / mean main-model trajectory tokens, normalized to the no-scaffold arm) as a reported metric for scaffold A/Bs, paired with total-token and wall-clock columns — so a scaffold cannot score a win by relocating cost onto sub-calls rather than reducing it.
- [ ] Compare RLM budget constants against ours (`ORCHESTRATOR_REPL_TURN_N_TOKENS`, swept over [256,4096]): recursion depth **exactly 1**; REPL output to the root capped at **8192 chars/turn** (the forcing function that makes the model use Python); **120 s** per-REPL-call timeout (ablated at 300/600 s, no benefit); tools bound to **sub-LLMs only**, never the root; termination is a **state variable** (`answer['ready']`), not a token.
  - 2026-11-02 (zero-inference source audit): current orchestrator differs on several material budget dimensions. The REPL turn cap is configured by `ORCHESTRATOR_REPL_TURN_N_TOKENS` (documented default 5000 in `docs/chapters/01-runtime-environment.md`; helper fallback is 768 in `src/graph/budgets.py`), not a recorded 256–4096 sweep. REPL environment output is capped at 8192 **characters** (`src/repl_environment/types.py:198`), matching the RLM cap's unit and value. `LLM_MAX_RECURSION_DEPTH` defaults to 5 (`src/config/__init__.py:96,467`) and `llm_call` enforces it (`src/llm_primitives/primitives.py:1004-1010`), so recursion depth 1 is not the current contract. `REPLConfig.timeout_seconds` defaults from registry key `repl.session` with fallback 600 seconds (`src/repl_environment/types.py:195-198`); no 120-second per-call setting or 300/600 ablation was found in this path. Tool exposure is broader than sub-LLMs: the REPL context exposes exploration and code/search helpers, including `llm_call`/`llm_batch` (`src/repl_environment/context.py:220`, `src/repl_environment/environment.py`). Termination is `FINAL(answer)` raising `FinalSignal`, with execution marking `is_final` (`src/repl_environment/context.py:231`, `src/repl_environment/environment.py:1380-1383`), not a `ready` state variable. Source comparison only; no runtime behavior or model outcome is claimed. The box remains open for a designed/validated policy decision on which of these differences to adopt.
- [x] Record the **zero-sub-LLM result**: on Oolong synth-with-labels the RLM scored perfectly at every context length using **regular expressions** over the context variable, with no sub-LLM calls at all — the win came from deterministic Python over data-by-reference, not recursion. A cheap-path arm worth testing before any fold-by-LLM arm. ✅ **RECORDED 2026-08-13** — already captured durably in `intake-803` `reported_results`: *"Oolong: the gain is real-subset-specific; synth is worse. **Synth-with-labels is the zero-sub-LLM regex-over-context case.**"* (verified at HEAD in `research/intake_index.yaml`). The cheap-path arm remains worth testing; the record now points at the intake as the machine-readable source of truth.
- [ ] Add the intake-537 **open-source-hardened RLM system prompt** (tuned on Minimax-M2.7 / GLM-5.1 — the only RLM prompt in the corpus tuned for open-weight drivers) as a third A/B arm beside the promoted SkyRL child prompt. Its distinctive lever is a **verbatim-slice return** instruction that suppresses sub-agent decode.
- [ ] Resolve the prefix-cache contradiction: intake-537 claims sub-agent calls hit KV cache ~90% of the time (static system prompt, append-only transcript) while this handoff records the RLM scaffold sharing no prefix. Both can hold — root turns cache-hostile, sub-agent turns cache-friendly. Measure separately via llama-server `/slots` hit rate.
- [x] Provenance fixes: neither intake-537 nor intake-803 references **this** handoff (both cite `completed/` targets; `rlm-orchestrator-roadmap.md` was archived 2026-03-29). intake-537 is **intake-783's author's design explainer** (unrecorded edge). intake-803 is **not** fast-rlm — an independent reimplementation sharing only the arXiv 2512.24601 ancestor. Two propagated result rows are misleading: the DeepDive "almost a doubling" is **GLM-4.6-only and reverses under tips** (the primary model, GPT-5-mini, was *worse* with RLM without tips), and the Oolong win holds only on the `real` subset, partly an **API-rejection artifact the post itself flags**. Every figure is observation-grade: the post contains **no numeric tables at all** (n=50 prompts × 1 rollout, single shared seed, untuned defaults, no CIs). ✅ **FIXED — verified at HEAD 2026-08-13.** Both intakes now reference this handoff in `research/intake_index.yaml`: intake-537 `cross_references.handoffs` includes `repl-turn-efficiency.md` with `handoffs_updated: [repl-turn-efficiency.md]`, and its `intake_entry_notes` records the unrecorded edge ("intake-783 (fast-rlm by the same author; this explainer is its design rationale)"). intake-803 likewise references `repl-turn-efficiency.md`, and its `notes`/`reported_results` carry every correction this row demanded (independent of fast-rlm; DeepDive GLM-4.6-only and reversing under tips; Oolong real-subset-only with the API-rejection artifact flagged; observation-grade credibility 3). No `completed/` targets remain. Minor: `rlm-orchestrator-roadmap.md` is in `handoffs/completed/` (not `archived/`) — a wording discrepancy in the row, no dangling reference.
- [ ] **Context knee at ~7K tokens, measured under attention masking.** intake-1118 (arXiv:2510.05381v1, EMNLP 2025 Findings, dive-verified) isolates pure LENGTH from retrieval quality by attention-masking the distraction — relevant content byte-identical, only position indices change — and finds most degradation lands inside the first 7K tokens, with 7-8B open-weights carrying the whole effect while frontier models stay near-flat. Two consequences for S4: our locally-served roles are the vulnerable class and Claude-main context behaviour must not be generalized to them; and "Retrieve-then-Solve" (recite evidence, re-prompt in a fresh short context, up to +31.2% recovery) is structurally what our REPL already does, which makes the REPL a measurable arm rather than an assumption. Longest length tested is 30K — 260K is extrapolation.
- [ ] **Width should taper with session phase, and the main should not choose its own width.** intake-1125#02 and intake-1125#03 (arXiv:2602.07359v1, dive-verified) finds optimal parallel width FALLS as the step budget rises, and a descending 3→2→1 schedule beat every constant width (74 vs 68) while letting the model self-schedule scored 72 — below the fixed rule. Caveat that must ride with any citation: it measures parallel TOOL CALLS in one context, not subagents with independent contexts; cite it for the shape, never as validation of our 3-5 subagent width.
- [ ] **Critical Steps is the right SHAPE for the S4 metric at line 115, and nothing more.** Σ_t(S_main + max_i S_sub,i) is a critical-path makespan in STEPS (intake-1106, dive-verified) and is exactly the property that stops a scaffold winning by relocating cost onto sub-calls. But it is blind to tokens, KV residency and instance placement, assumes uniform step cost, and is NEVER MEASURED in the paper that defines it — no figure or table uses it as an axis. Specify our own variant against our own cost axes; do not imply the source validated it.

## B7 chunk-KV block logging — 2026-10-21

The B7 audit (`/mnt/raid0/llm/tmp/b7-audit-20261021/REPORT.md`) specifies a per-request `blocks` log field. No filed task owned it; this handoff owns prompt-layout telemetry. Producer side landed as `fc02209d`: `block_log_records()` and `SkillRetriever.last_blocks` in epyc-orchestrator (sha256_12 for logging only, never in the prompt). Related: CFI-1/CFI-2 in `episodic-memory-integrity.md`.

- [x] **B7-LOG-1 — wire `block_log_records()` / `SkillRetriever.last_blocks` (and the episodic blocks) into the request `blocks` log** (`kind`, `sha256_12`, `est_tokens`, `n_items`, `meets_min`), per the B7 REPORT field spec. The routing-context blocks are not yet retained anywhere; add the same retention. Zero inference. (filed 2026-10-21) ✅ 2026-10-21
  - 2026-10-21 (dpf-logpfx): functionally covered by RTE-LOG-1's producer, not by calling `block_log_records()` literally: `SkillRetriever._format_cache_friendly` and `_build_cache_friendly_routing_context` call `reusable_blocks.retain_for_log(kind, blocks)`; `prompt_layout.build_layout` finds each retained Block in the final prompt by its rendered bytes and writes `kind`, `sha256_12` (the Block's own hash, equal to `block_log_records()`'s), `est_tokens`, `n_items`, `meets_min` into `blocks[]` of the dispatch and serving records. Routing blocks are retained the same way. Tests: `tests/unit/test_prompt_layout.py::test_injected_blocks_located_by_bytes_and_unlocated_counted`.
- [ ] **RTE-LOG-1 — Prompt-structure and chunk logging, and the B7 offline reader (privacy: hashes and lengths only).** Per the B7 audit addendum (`/mnt/raid0/llm/tmp/b7-audit-20261021/REPORT.md`): add to the dispatch and serving records an ordered `blocks[]` list of kind (system, tools, rules, task, state, context, reference_code, skill, routing, doc_chunk, tool_output), start offset, length and sha256 prefix, per-chunk hash and rank for reference_code and doc_chunk, `prompt_tokens` and `cached_prompt_tokens`, `turn_index` and a `source` label (interactive, autopilot, benchmark, repl_experiment) instead of the regex inference, behind the existing kill-switch pattern. Write the offline reader that flags first occurrence versus later occurrence at a different offset or after a different predecessor, per kind, role and source, and that splits the reuse share into same-predecessor repeats (prefix cache, not ours) and different-offset repeats, plus the per-request distinct-chunk count, chunk length and the prefix-reconstructible share (intake-2295#record, intake-2326#record). The reader runs once a representative traffic week exists after the stack restarts; document-QA over fixed documents of 10-30K tokens per repeat query is the largest modelled payoff and is the event that sets priority. Acceptance: one request in the live stack produces a record with blocks[] and token counts, the reader runs on a synthetic replay in a unit test, and the reader report format is committed. Estimate: 2-3 days for logging, 1 day for the reader.
  - 2026-10-21 (dpf-logpfx): code, reader, report format (`docs/reference/prompt-layout-report-format.md`) and the synthetic-replay unit test are done (orchestrator lane `5d2140f8`); the box stays open until one live-stack request produces a record with `blocks[]` and token counts. Producer gaps:
    - [x] `src/graph/helpers.py` REPL path: no layout is staged there; text appended after the builder (workspace, session, riders) lies beyond `layout_chars`, and a `cot_prefix` breaks the head match so no blocks attach. ✅ 2026-10-22
      - 2026-10-22 (rte-toc-writers): closed in orchestrator `e9cf0949` (origin/main). `prompt_layout.rebase_layout(final, base)` runs after the final `_ct_neutralise` in `_execute_turn`: block starts shift onto the sent prompt (a `cot_prefix` no longer breaks the head match), `layout_chars` ends at the builder-covered span, riders are counted in `tail_chars` (not typed blocks), `rebased` is recorded; if escalation compression rewrote the builder text no blocks are emitted and all count as unlocated; the escalation-prompt branch clears any stale layout. Tests `tests/unit/test_prompt_layout.py::test_rebase_*` (111 passed with features/runtime_flags).
    - [x] No `tool_output` producer yet (the kind is defined in `KINDS`). ✅ 2026-10-22
      - 2026-10-22 (rte-toc-writers): `_record_root_lm_layout` carves the exact `## Last Output` / `## Last Error` block out of the context span as kind `tool_output` (same carve as routing, no overlap). Orchestrator `e9cf0949`; test `test_builder_emits_tool_output_block_and_it_does_not_overlap_context`.
    - [ ] Live check: restart the stack, send one request, confirm `blocks[]`, `prompt_tokens` and `cached_prompt_tokens` in `dispatch.jsonl` and `serving_calls.jsonl`; set `ORCHESTRATOR_REQUEST_SOURCE` in the autopilot and benchmark launchers.
      - 2026-10-22 (rte-toc-writers): the check is built: `scripts/analysis/prompt_layout_live_check.py` (orchestrator `0226a4c6`; exit 0 pass, 1 fail, 2 no records; zero records is not a pass). Remaining, needs the live stack (DOWN; not started): restart, send one request, run `python3 scripts/analysis/prompt_layout_live_check.py <logs>/dispatch/dispatch.jsonl <logs>/serving_calls/serving_calls.jsonl`, and set `ORCHESTRATOR_REQUEST_SOURCE` in the autopilot and benchmark launchers. Main RTE-LOG-1 box stays open until that passes.
  - 2026-11-02 (ownercheck run): granted row `handoff-rte-log1-ownercheck-20261101` was refused before launch (`rc=4`, `own-port-8070-already-listening`); result records were qualification-only (`dryrun=true`). Filed **inconclusive**; no live-stack acceptance or traffic-week result. The production acceptance box stays open. [no-belief: refused execution, no production measurement]
  - 2026-11-02 (override diagnostic): `handoff-rte-log1-override-r2-20261101` real phase exited `rc=1`, `status=failure`, `partial=false`, `drained=true`, no survivors; its owner checker received HTTP 429. Filed inconclusive: no owner result or diagnostic acceptance; normal-routing acceptance and traffic-week work remain open. [no-belief: failed diagnostic execution]
  - 2026-10-30 (NI source publication): explicit request-source propagation is published as orchestrator `63fd32d54d12f146172a317d00cc3326a3dd8d2f`, merged to main at `517a7eb3f75166ebfed2329b3a2ab7190eff7975`. The exact 11-file candidate passed 102 targeted cases; the merged source passed 310 cases plus schema and scoped Ruff. Source proof: `/mnt/raid0/llm/tmp/codex-ni-app-source-lane-20261030/RTE-PUBLISHED.json`. No API reload or live request occurred in this publication. Both RTE-LOG-1 and its live-check leaf remain open: the runtime owner must restart at its own boundary, send a request and pass the committed live checker; a representative traffic week remains necessary for the reader report. [no-belief: software publication and regression verification]
  - 2026-10-30 (NI direct-producer repair): orchestrator `b0f8613d65f30986f147e5467b1c66892c887ce5` is published to `main`. It forwards only the existing trusted prompt-layout fields and already-computed native token counts through standalone dispatch, preserving missing counts, cache fallback, privacy filtering, feature gating and fleet deduplication. The five-file change adds 160 lines/removes 1; focused source checks report 68 passed (one dependency warning) plus Ruff. Private native evidence includes the full four-request API cohort, a separate cutoff-75 partial with drained children, and the bounded owner-recipe candidate request with committed checker rc 0; none is production acceptance. Evidence: `/mnt/raid0/llm/tmp/codex-ni-rte-live-acceptance-20261030/IMPLEMENTATION-REPORT.json`. RTE-LOG-1/production leaf 226 remain open until the owning API session reloads at its own boundary and runs `production_owner_check.py`; no production reload, normal-stack request or representative traffic week is claimed. [no-belief: software acceptance verification and regression evidence]
- [x] **RTE-CORPUS-1 — Clean up the dead CorpusRetriever path (the corpus index was retired deliberately on 2026-07-04).** The 651 GB index was deleted after the clean-window A/B of `handoffs/completed/corpus-augmented-prompt-lookup-revalidation.md` (CPL-4 and CPL-5: no benefit, mildly negative), but `orchestration/model_registry.yaml` still carries `runtime corpus_retrieval.enabled: true` with the deleted `index_path` and seven roles with `acceleration.corpus_retrieval: true`, so every request pays a failed lookup that logs and returns empty. Step 1 (not this task): the registry flag-off is operator-approved (2026-10-21) and its ratification script `scripts/operator/ratify_corpus_retrieval_off_20261021.sh` is ready; the operator runs it. Step 2 (after the flip, optional refactor): remove the callers of `build_corpus_context` (`chat.py:1478`, `stream_adapter.py:199`, `chat_delegation.py:398`, `graph/helpers.py:1144`) and the direct `CorpusRetriever` use in `llm_primitives/primitives.py`, keep the offline scripts or move them to an archive, and drop the corpus event. GitNexus impact must run with `--repo epyc-orchestrator` after a fresh analyze, not from git grep alone. Acceptance: after the operator runs the ratification script, the failed lookup no longer occurs per request (a log count before and after); step 2 passes the full unit suite with no behaviour change. Estimate: step 1 0.5 day, step 2 1-2 days. ✅ 2026-10-21. ratified by operator (Daniele) RATIFY-CORPUS-RETRIEVAL-OFF-20261021; research ab702eca6, orchestrator 792955fc; receipt artifacts/operator/receipts/RATIFY-CORPUS-RETRIEVAL-OFF-20261021.json; effective at next stack start
  - 2026-10-21 (dpf-logpfx): code side landed in lane `5d2140f8`: `build_corpus_context` returns `config_disabled` before any module import, role lookup or retriever when runtime `corpus_retrieval` is off (three tests in `tests/unit/test_corpus_retrieval.py`). Open until the operator runs `ratify_corpus_retrieval_off_20261021.sh` and the before/after failed-lookup log count is taken; step 2 (caller removal) stays optional and is not done.
- [x] **RUS-1 — Best-of-K REPL arm design note with selector-validity rules (zero compute).** Design note under the S4 arms placing a best-of-K REPL arm beside the fixed-plan arm (LRLM-1) and the S4 Omega arm: K, the selection rule (plurality-answer filter, then argmax of summed log verbalised confidence times trace length; implement argmax, the formula text says lower is better but only the argmax reading is consistent, intake-2284#record), and the cost columns (total tokens across K, wall-clock, decode versus prefill, cache share; K parallel trajectories contend for the bandwidth-bound host). Mandatory clauses: (1) the selector table has a no-filter row beside plurality filter, a shorter-length row, a lower review-ratio row and a lower failed-step-fraction row, and the report states per task the share where oracle coverage exceeds selected accuracy and where the plurality is wrong (intake-2300#record); (2) any arm using a vote or plurality selector reports selected accuracy at three or more widths (K=1, 2, 4, 8 at least) beside oracle coverage so a rise-then-fall curve is detectable, because more calls can lower accuracy under plurality selection without a checker (intake-2312#record); (3) tasks with no deterministic checker are labelled verifier-free, the vote selector is the declared-weak arm and the single larger-role answer is the comparator (intake-2296#record); (4) best-of-K and any worker-versus-architect comparator are compared at equal measured wall-seconds with K per model set by its own seconds per attempt; (5) pairwise discrete CAPA among the K samples is reported beside the distinct-answer count (intake-2323#record); (6) verbalised confidence is a selector candidate scored against the checker and never a claim-tuple field. Acceptance: the design note is filed with all six clauses and the cost columns. Estimate: 0.5 day. ✅ 2026-10-21
- [x] **RUS-2 — Trace-length and review-ratio signal probe on logged runs (zero inference).** ✅ 2026-10-21 From already-logged eval or AutoPilot runs of reasoning-model roles carrying tokens generated and a pass/fail grade, compute the AUROC of tokens generated against correctness per (role, suite) across questions and, where repeated samples per question exist, the within-question rank agreement; the within-question direction is the only one that matters for best-of-K. Within-question arm: question fixed effects, drop questions with all-correct or all-wrong samples, report truncation (finish_reason length) separately and excluded, record each sample temperature. Also compute the deterministic keyword-chunk review ratio per trace beside tokens generated (intake-2316#record, intake-2327#record). First verify the records carry both fields. Run under `region-lock run --cpu-list 0-95`. Acceptance: a per-(role, suite) AUROC table and the within-question agreement with N stated; RUS-1 selector table updated to keep or drop the length row. Estimate: 1 day.
  - 2026-10-21 (dpf-sample-yarn-zc, lane `lane/dpf-sample-yarn-zc-epyc-root-20261021`): DONE as probe + table; the within-question arm is a VERIFIED NEGATIVE on existing logs. Probe `scripts/analysis/rus2_trace_length_probe.py` (research lane commit `4cc8e1730`) over `benchmarks/results/eval/*.jsonl` (62 files): 6,006 usable samples in 92 (role, mode, suite) cells; records carry `tokens_generated` and boolean `passed` but NO `temperature` (6,565 of 6,565 not recorded), NO `finish_reason` (cap-value proxy excluded 559 samples), and no reasoning trace (answer text only). Within-question: exactly 1 question with repeated mixed-outcome samples (1 pair), so agreement is unmeasurable here; a repeated-sample run is filed as RUS-3. Between-question AUROC (31 cells with at least 100 questions) runs 0.1057 to 0.7534 with sign flips (and a degenerate 1.0 at 129/130 correct), so no length selector is licensed. Review ratio on answer text sits near 0.5 where n is at least 30. RUS-1 clause 1 edited accordingly (length row diagnostic only; review-ratio row only for trace-recording arms). Evidence: `artifacts/rus-2-20261021/` (`rus2_result.json`, `rus2_table.txt`, `table_cells_ge100q.md`, `RUS2_NOTE.md`). Ran on q3 (72-95) under region-lock build role, not 0-95 (all quarters held).
- [ ] **RUS-3 — Repeated-sample run to measure within-question trace-length agreement (needs an inference window).** Run K>=4 samples per question at a recorded non-zero temperature for the reasoning-model roles on the suites where RUS-2 found mixed outcomes (one run record per sample: `tokens_generated`, `passed`, `finish_reason`, `temperature`, and the full reasoning trace so the keyword-chunk review ratio is computable on the trace), then rerun `scripts/analysis/rus2_trace_length_probe.py` for the within-question arm (question fixed effects, all-correct and all-wrong dropped, truncation separate). Acceptance: within-question pooled AUROC with N mixed questions and pairs stated per (role, suite), and the RUS-1 length row kept or dropped on that number. Inference task: needs a granted window; build the sampler/record writer first and gate it behind `WINDOW_CONFIRMED=1`. Estimate: 1 day plus window.
  - 2026-10-28 (ws58 results filing): `rus3-repeated-samples-r3` rc0 15:18Z, full raw capture 40/40 (10 q x 4 repeats), 9 retained / 31 truncated, GPU residency ok. Diagnostic observation only (the row's rule is collection, owner review required; capture OBSERVED_UNATTESTED, no protocol_id) — see `progress/2026-10/2026-10-28-rus3-r3-capture-audit.md`. Box stays open: 31/40 truncated leaves the trace-length agreement unmeasurable at this n_predict. [belief: cc]
    - [ ] **RUS-3-TRUNC (filed 2026-10-28, ws58 filer):** raise n_predict (or cap by finish reason) so >= 4 untruncated samples per question exist, then re-run; done when per-question agreement is computable on >= 8 of 10 questions.
      - 2026-10-31 watcher terminal (codex-ni): `rus3-trunc-r4-20261031` smoke failed rc1 before any native events; `latest-collection.json` was absent, result writer failed, and cleanup_ok=false. Captured PIDs were absent at terminal inspection, but cleanup is not certified. This is a failed preparation smoke, not a cohort run or science result; no samples or agreement were produced, and the original completion rule remains open. Terminal JSON SHA-256 `b398058772f9680489fe95ae259a2889f0479c8aabd9439404fbfe4bc34f9cf6`; custody SHA-256 `a6bb01224cb67b46692595dfef2a66f5dde9d79722b2428d4be83452b9bd96ed`. Evidence retained under `/mnt/raid0/llm/tmp/codex-ni-gpu-floor-next2-20261031/`.
- [x] **LRLM-1 — Fixed-plan long-input arm design note, including chunk-size search and the dependence screen (zero compute).** Map the REPL helpers (`_batch_llm_query`, `parallel_dispatch`, workspace_scan) onto the lambda-RLM combinators (Split-Map-Merge, Split-Map-Parse-Cross, Split-Peek-Filter-Map), list which current long-input tasks have a fixed task-type plan, and define a declared-parameter fixed-plan arm against the open-ended REPL on the same tasks, noting the contrast with the finding that regex over the context won with zero sub-LLM calls (intake-2241#record). Include: chunk size chosen by sparse sampling of at least 5 samples per candidate size on a dev set instead of a closed-form k* (the measured optimum and the closed form disagree, intake-2264#record); a cross-chunk-dependence screen (single-shot versus chunked score gap on a small dev set) before routing a task class to fan-out; a digit-menu task-type classifier feeding a deterministic plan table as a prototype definition (intake-2275#record). The reference code needs only an OpenAI-style client with a base_url, so pointing it at llama-server is an adapter of about 0.5 day, not a blocker. Runs wait for the UFH-13 thesis experiment to unfreeze HS-19b-d. Acceptance: the design note is filed with the combinator map, the three definitions and the adapter estimate. Estimate: 0.5 day. ✅ 2026-10-21
- [x] **RTE-PFX-1 — Prompt-prefix stability: static first-divergence check, cause classes, layout read and an append-only arm (zero inference).** (1) Render the prompt for turns N and N+1 of one session for each served role from stored requests or the prompt builder and report the first-divergence token offset, labelling each by cause class (volatile field, key order, tool-block edit, history rewrite) and flagging any divergence inside the tool or system block (intake-2230#record, intake-2276#record). (2) Code read of the REPL root-LM prompt assembly (`src/graph/helpers.py` around :1139, `src/prompt_builders/builder.py`): where the `get_state()` block and the turn history sit relative to the stable prefix, and whether a changed variable preview moves the first differing token earlier than the prior turn end; cite existing server logs for prefix-cache hit share if present (intake-2245#record). (3) Add to the repaired RTE-Prefix A/B plan an arm with the running-state block append-only versus rewritten in place, reporting cached and processed tokens and prefill latency per turn; the run stays gated on the harness repair (intake-2282#record). Acceptance: a first-divergence table per served role with cause classes, the layout statement, and the arm added to the plan. Estimate: 1-1.5 days. ✅ 2026-10-21
  - 2026-10-21 (dpf-logpfx): items 1-3 done. First-divergence table (8 transitions x both section orders, chars/4 token estimates, role-independent builder): `artifacts/dpf-logpfx/rte-pfx-1-first-divergence.json`, script `scripts/analysis/rte_pfx1_first_divergence.py` (orchestrator lane). Divergence is always the `Turn N` line at the head of the state block: char 8860 (~2215 tok) legacy order, 8991 `prefix_stable_order`, 95-97.5% of the prompt; changed previews, key order and a dropped routing block do not move it earlier; the edited-tools negative control diverges at char 595 and is flagged PREFIX_BLOCK_DIVERGENCE. Layout statement and the code read are in the script docstring. Server log (19 records): coder_escalation 4149 of 14568 prompt tokens cached over 5 records, not a turn-pair measure. The `state-append` vs `state-rewrite` arm is added to the repaired A/B plan above; its run stays gated on the harness repair. Follow-up filed as RTE-PFX-3.
- [x] **RTE-PFX-2 — Hold-first prefix stagger probe for same-prefix fan-out (spec now, run needs a window).** Write the probe spec: N same-prefix requests started simultaneously versus first-then-N-1 (release siblings when the first response begins), on one served role, reporting uncached prompt tokens and time to first token per request from the server timings, and checking that slot selection really lands siblings on the cached prefix; `parallel_dispatch` uses a thread pool with no stagger. The run takes a timing window under region-lock (intake-2227#record). Acceptance: the spec with the slot-selection check is filed; the run result follows its window. Estimate: spec 0.5 day, run about 0.5 day. ✅ 2026-10-21
  - 2026-10-21 (fillers-3c4ca599): run registered as queue item `s5-rtepfx2-stagger` (NOT armed, bundle `s5-stackup-bundle`); needs a -np >= 4 server and a declared prefix file.
  - 2026-10-21 (queue-builders-2): run made ready and ARMED as filler `s5-rtepfx2-stagger` (own server on :18971, no stack needed; metric is uncached-token counts). Codified recipe `scripts/benchmark/rte_pfx2_role_recipe.py` (epyc-orchestrator, commit `2464de83` on lane/qb2-rtepfx2-20261021) derives the launch from the registry via `build_server_command`: frontdoor full shape, Qwen3.6-35B-A3B-MTP-Q8, `-np 4`, `--cache-ram 32768`, cpu 0-95 interleave=all; deltas are port and a private slot-save-path only. Declared prefix `scripts/benchmark/rte_pfx2_prefix.txt` (24000 chars of this file at e1ae53e03, sha256 in sidecar). Dry-run clean; 5 tests. Needs a grant naming 0-95 and >= 45 min.
  - 2026-10-27 harvest (s5-rtepfx2-stagger, ended 2026-10-23T09:55:24Z): RESULT (negative for the stagger). n=5 trials x 4 siblings, frontdoor Qwen3.6-35B-A3B-MTP-Q8 -np 4 on v10 b10303, expected prefix 6528 tok, per-sibling gate cache_n >= 0.9 x 6528. `simultaneous`: 0/20 hit (median total uncached prompt tokens 26208). `hold_first_tok`: 0/15 siblings hit, siblings land on empty slots (median uncached 26212). `hold_first_end` control: 1 of 3 siblings per trial reuses (cache_n ~4505 = 69%, below the 0.9 gate; 5/5 trials), median uncached 21710 (-17% vs simultaneous). A client-side hold-first stagger does not land siblings on the cached prefix on this hybrid role; follow-up lives in the slot-selection / checkpoint-fork path (KPF), not a client stagger. Artifacts `/mnt/raid0/llm/tmp/qb2-rtepfx2/run-20261023T094104Z/probe.json`, `chunk_kv.beliefs.jsonl`. [belief: cc]
- [x] **RTE-PFX-3 — Move the `Turn N` counter (and any per-turn volatile field) out of the state block's head, so the shared prefix extends past about 95% of the prompt; re-run the rte_pfx1 first-divergence script to confirm.** Finding from RTE-PFX-1 (2026-10-21): first divergence between consecutive turns is always the `Turn N` line that heads the state block (`src/prompt_builders/builder.py`, `state=f"Turn {turn + 1}\n{state}"`), so the stable part of the state block, and in legacy order the task text, is lost to the prefix cache every turn. Move the counter and other per-turn fields to the volatile tail, behind a default-off flag, byte-identical when off; re-run `scripts/analysis/rte_pfx1_first_divergence.py` and report the divergence offsets before and after; the live effect is measured by the append-only arm of the RTE-Prefix A/B (gated on the harness repair). Acceptance: flag-gated change with a unit test, and the before/after first-divergence table. Estimate: 0.5 day. ✅ 2026-10-22
  - *(2026-10-21, dpf-specs.)* Spec with the slot-selection check filed (section "Hold-first prefix stagger probe spec"); window-guarded script `scripts/benchmark/rte_pfx2_stagger_probe.py` (epyc-orchestrator orchestrator a350b690). Run result follows its window (WINDOW_CONFIRMED=1, region-lock).
  - 2026-10-22 (a1-orch-code, 3c4ca599) DONE, orchestrator `16f63825`. Flag `repl_turn_counter_tail` (default off): the counter moves from the state-block head to a new `RootLMPrompt.turn_tail` rendered after every section in both orders. `rte_pfx1_first_divergence.py --turn-counter-tail`; flag-off offsets identical to the RTE-PFX-1 artifact. Before -> after, "turn counter only": legacy char 8860 (95.8%) -> 9247 (last line, 100.0%), stable 8991 (97.2%) -> 9247 (100.0%); with a new last output: legacy 96.0% -> 98.3%, stable 97.5% -> 99.7%; graph-tail session growth 95.0/96.5% -> 99.2%; tool-block negative control unchanged at char 595. Table: `artifacts/dpf-logpfx/rte-pfx-3-first-divergence.json`. Tests `tests/unit/test_rte_pfx3_ct21_flags.py` (flag off byte-identical). The live effect stays with the append-only arm of the RTE-Prefix A/B.

## Research Intake Update — 2026-10-21 (harness cluster, DP-F amendment)

Operator-approved Stage-3 amendment (plan sha256 2edfb0662f61e1254e7dc5e2b21888ef4f19df800a283e82b25caebeb6644746). Durable records only: no checkbox, no index next action. Each monitor row carries its trigger and first step; each knowledge row states what to rely on. Ledger ids (DPF-...) key to the Stage-3 recommendation mapping preserved in `.research-session.json` (`stage3_filing`).

### K12 — Long-context decomposition, sampling, aggregation and uncertainty evidence

- DPF-1806-L2 (intake-1806#05): The paper reports parents answering directly without spawning, especially at long contexts. Independently, [HS-4](harness-selection-and-integration.md) records DS41-C20c: a local model offered `task` did not use it (n=1). This is a local observation of non-use, not a replication of the paper or evidence of a general failure rate.
- DPF-1806-L3 (intake-1806#01, review-required): The narrowed mechanism is one-level script fan-out of full harnesses: all 199 evaluated instances used the code-execution path. The JSON spawning path, depth and entries per worker were not ablated; no demonstrated multi-level recursion or local performance claim follows. Preserve this correction when considering an arm rather than treating the title as evidence of recursive execution.
- DPF-1806-L4 (intake-1806#04): Workers re-read the shared document; shared-prefix caching is proposed, but the paper measured no token or latency saving. No provider saving percentage transfers to llama.cpp. Any local reuse claim needs served-tree/slot identity, actual cached-versus-processed token counts and latency from our own paired run.
- DPF-W1-ANTHROPIC-DYNAMIC-WORKFLOWS-L2 (intake-2227): Deterministic replay by banning nondeterminism in the orchestration script (time and randomness injected via args) and order-based result reuse with 'first divergence reruns everything after'. Same d…
- DPF-W1-ANTHROPIC-DYNAMIC-WORKFLOWS-L3 (intake-2227): Three-valued claim outcome in a verification fan-out: verified / refuted / unverified (verifier could not run), with unverified never counted as refuted. Maps to the dive second-reader (yes / no / pa…
- DPF-W1-ANTHROPIC-DYNAMIC-WORKFLOWS-L5 (intake-2227): Operator sessions use this very Workflow tool on a shared host; CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS and the size guideline are the knobs that bound CPU contention from mains. Subagent brief ha…
- DPF-W1-LRLM-L2 (intake-2241): Symbolic quadratic step: the model labels chunks (O(n/K) calls), the O(n^2) pairing is computed in code for free; the Normal RLM must compute it neurally (largest gain, +28.6 pp, on OOLONG-Pairs).
- DPF-W1-LRLM-L5 (intake-2241): Strong coding models beat the fixed chain on repo navigation (CodeQA: 4/9 RLM wins; 6/12 at strong tier). Supports big=consultant/small=grunt: open-ended control for strong models, fixed plans for sm…
- DPF-W1-LRLM-L6 (intake-2241): Prefill/decode and cache: leaves are near-window-size independent prompts (total prefill about n tokens), one chain instead of 5-12 code turns. Paper reports no prefill/decode split, parallelism of M…
- DPF-W1-LRLM-L7 (intake-2241): Context folding relation: lambda-RLM manages ONE long input by chunking; context folding (intake-154) and CF-AB-1 arms A3-A5 manage a growing agent history. Orthogonal axes; paper cites Context-Foldi…
- DPF-W1-MINIONS-M3 (intake-2244): Cost headline relocates cost: 5.7x is a GPT-4o list-price ratio (alpha=4) with local compute free; no local token, latency or energy figure is reported (section 3, appendix C).
- DPF-W1-MINIONS-M4 (intake-2244): Cost translation: EPYC alpha is not the cloud 1-5. Consultant occupancy = prefill tokens / prefill rate + decode tokens / decode rate on the shared host, with workers on the same box. The paper's dol…
- DPF-W1-MINIONS-M6 (intake-2244): Knob directions for any decomposition arm: tasks per round 1 -> 16 up to +14 pts at 2x remote prefill (worse above 16); samples 1 -> 32 +7.4 pts at 5x (worse above 16); chunk 100 -> 5 pages +11.7 pts…
- DPF-W1-MINIONS-M8 (intake-2244): Consultant competence is a hard dependency: swapping GPT-4o for Llama-3.3-70B keeps the macro within 0.07 but not FinanceBench (0.109 gap); Llama-3-70B and 3.1-70B consultants score 0.18 and 0.43 on…
- DPF-W1-MINIONS-M9 (intake-2244): Local-model scale: MinionS recovers 49.5% at 1B, 93.4% (Qwen) / 91.4% (Llama) at 3B, 97.9% at 8B; naive Minion collapses to 0.236 for Qwen-3b. EPYC worker roles are far above this scale, so the floor…
- DPF-W1-MINIONS-M10 (intake-2244): Information-bottleneck framing: consultant prefill tokens vs accuracy as the compression/retention axis; 7-8B workers 1.53x more token-efficient than 1B.
- DPF-W1-MINIONS-M12 (intake-2244): Inter-round state: scratchpad slightly beats retries-only; keeping the whole conversation costs too much 'even with prompt caching' (section 5.1).
- DPF-W1-OOLONG-O5 (intake-2246): The authors keep Oolong-synth because it is decomposable (label each example, then aggregate deterministically). That is exactly the REPL/data-by-reference path: the zero-sub-LLM regex result on synt…
- DPF-W1-OOLONG-O6 (intake-2246): Oolong-real is the non-decomposable case and the paper's simple iterative baseline (smolagents, BM25 utterance retrieval plus code, 5 steps, GPT-5) loses 16.15 to 17.67 points to direct long context…
- DPF-W1-OOLONG-O7 (intake-2246): Oolong-real needs at least 55K tokens per single-episode item and goes to 1.3M; Oolong-synth is built to 4M but the paper shows results only to 512K. Local ceilings are 262K native and 524K under YaR…
- DPF-W1-OOLONG-O9 (intake-2246): Oolong-real contamination was probed (6/100 exact at best, guesses on common answers). Evidence against memorisation, narrow (3 models, 100 questions).
- DPF-W1-OOLONG-O10 (intake-2246): Prefix-cache angle: one context serves 25 questions with the question last, so a cached-prefix local run pays one long prefill per 25 items. The paper says this was done to cut cost for API and local…
- DPF-W2-COA-C3 (intake-2258): Authors-built parallel baselines are weak (no re-ask, no abstain/confidence); the sequential-wins claim does not transfer to a protocol like MinionS or LLMxMapReduce. A third-party run reverses the o…
- DPF-W2-COA-C4 (intake-2258): Order sensitivity: random permutation beats left-to-right on 2 of 7 datasets and the 5-way permutation oracle exceeds judge/vote by up to 16 points: the sequential state is path-dependent.
- DPF-W2-COA-C5 (intake-2258): Per-agent short windows are the paper's focus lever (Appendix D: Claude 3 Haiku NarrativeQA rises from 4k to 16k windows then flat near 20; one model, one dataset). Aligns with the ~7K context knee a…
- DPF-W2-COA-C6 (intake-2258): Baseline plausibility: Claude 3 Vanilla (200k) scores 7.17 F1 on NarrativeQA (haiku) against CoA 18.80; a format or verbosity artifact in the F1 scorer is possible but not shown. Backbones are 2024 A…
- DPF-W2-CORNJEBUS-RLM-REPLICATION-C2 (intake-2261): Exact-count (NUMERIC_ONE_CLASS) collapses to 5.8% (N=12) for classify-then-count at ~3,182 records, while frequency-order questions stay at 75-83%.
- DPF-W2-CORNJEBUS-RLM-REPLICATION-C3 (intake-2261): Window-level caching of classifications: 1,900 calls become 76 on the short setting because each context serves many questions.
- DPF-W2-HELMET-HE2 (intake-2267): App. E.3: "altering the positional embedding may lead to degradation at shorter lengths" (Llama-3-8B-Inst with theta 16M, on ODQA and ICL). Qwen2 + YaRN drops sharply past 32K.
- DPF-W2-HELMET-HE3 (intake-2267): Summarization is the aggregation-over-whole-input axis; ICL is orthogonal to recall. Categories correlate weakly; one axis cannot stand in for others.
- DPF-W2-HOLOBENCH-H3 (intake-2268): Reasoning-focused models degrade faster with length than general models (R1 11.3 at 64K/50%); CoT is required (aggregation rarely solved without CoT); at large relevant volumes models say the input f…
- DPF-W2-HOLOBENCH-H5 (intake-2268): RAG (bge-large, 2K retrieved) beats vanilla only at 4K for strong models; helps Llama-8B past 16K.
- DPF-W2-LLMXMR-L2 (intake-2273): Confidence-calibration trick: LLM self-reported confidence /5 anchored by in-context examples. No calibration of the scores is measured, so on EPYC it is a prompt heuristic, not a signal the belief k…
- DPF-W2-LLMXMR-L3 (intake-2273): Collapse stage is the only mechanism in the cluster that handles aggregate worker output larger than the consultant window (Minions uses rounds and a decision field; CoA rewrites one CU). Same-struct…
- DPF-W2-LLMXMR-L4 (intake-2273): Cross-source disagreement on CoA at long length: CoA's own paper reports gains up to >400k tokens on BookSum with Claude 3 (Fig. 2) while LLMxMapReduce's reimplementation collapses at >100K with an 8…
- DPF-W2-LLMXMR-L5 (intake-2273): Latency claim cannot be carried: figure-only numbers, cloud A100 TP baseline, parallel map on dedicated GPUs. On EPYC, parallel map workers share one memory-bandwidth budget; the measurement to run i…
- DPF-W2-LMONKEYS-L4 (intake-2274): Coverage curve c = exp(a k^b) lets a small-k pilot extrapolate coverage; fits are imperfect (MiniF2F).
- DPF-W2-LMONKEYS-L5 (intake-2274): Many completions of one prompt are a throughput workload that shares the prompt prefix.
- DPF-W2-LMONKEYS-L6 (intake-2274): Independent attempts with no feedback; authors name multi-turn feedback and learning from previous attempts as untested improvements.
- DPF-W2-OOLONG-LINEAGE-OL6 (intake-2281): Oolong-synth generation: questions subsampled "down to 50 for each context window" in Oolong-synth.md versus 25 per context in the paper; 400/25 = 16 contexts per length matches the paper.
- DPF-W2-PRISM-P3 (intake-2282): Cost index uses an API ratio (output x3); EPYC cost is measured seconds from registry prefill/decode rates.
- DPF-W2-PRISM-P4 (intake-2282): Quality gap: RepoQA 0.48-0.53 vs 0.92 long context; LOFT-Spider amendments 0.14 vs incremental 0.12 (noise); sequential streaming into short windows is lossy for retrieval/tracing tasks; authors conc…
- DPF-W2-PRISM-P5 (intake-2282): Statistical weakness: n=50 examples, SEM over five generations.
- DPF-W2-PRISM-P7 (intake-2282): Sequential stream has n dependent steps (no parallelism) but each step is a cache-hit prefill; contrasts with Minions' parallel job grid.
- DPF-W3-BUDGETREALLOC-D3 (intake-2296): NLL ranking is a parallel forward pass, cheaper than generation.
- DPF-W3-BUDGETREALLOC-D4 (intake-2296): 7B underperforms at larger budgets on hard tasks: a minimum-size effect.
- DPF-W3-CONSENSUS-E3 (intake-2300): Temperature does not diversify answers (2.9% plurality flips between T=0.7 and 1.0).
- DPF-W3-LCBOOST-B3 (intake-2306): Token cost is not uniformly lower: 112% of brute force on summarization.
- DPF-W3-LONGAGENT-A2 (intake-2308): Answer clustering plus pairwise chunk-sharing as the conflict adjudicator.
- DPF-W3-LONGAGENT-A3 (intake-2308): Chunk size has a hallucination optimum (500 to 2,000 improves, above 2,000 worsens) tied to fine-tuning length.
- DPF-W3-LONGBIO-L2 (intake-2309): Qualifier on HELMET HE1: LongBioBench's 0.853 vs HELMET is nominally above HELMET's own "no synthetic task exceeds 0.8" but cannot be separated from it at n=12 (interval about 0.55 to 0.96), and rank…
- DPF-W3-LONGBIO-L4 (intake-2309): Validity checks reusable for any new long-context cell: solvable at short length, unsolvable without the context, and a stated item count at which accuracy stabilises (800 items within 1 percent).
- DPF-W3-MORECALLS-C3 (intake-2312): Query difficulty d(x) = share of wrong modal answer minus share of correct, estimated from K samples per query.
- DPF-W3-MORECALLS-C4 (intake-2312): UFH-13 / M12 contact.
- DPF-W3-TRACELEN-F3 (intake-2316): Reasoning post-training creates the length signal; base instruct models do not carry it.
- DPF-W4-100LONGBENCH-LB1 (intake-2319): LongScore normalises by the short-length score. In the YaRN gate A0 and A1 are the same model on the same items, so the base cancels; the metric only matters for cross-model comparison (for example Q…
- DPF-W4-100LONGBENCH-LB2 (intake-2319): Haystack realism sits between neutral essays and the LongBioBench coherent haystack: same-domain articles shuffled around one ground-truth article, distractor count grows with length.
- DPF-W4-100LONGBENCH-LB5 (intake-2319): YaRN datum: Qwen2.5-7B/14B with YaRN to 128k show LongScore near -30, worse than native-128k Llama 3.1 8B at -17.4; family and size confounded; not stated whether Base was measured with YaRN active.
- DPF-W4-100LONGBENCH-LB6 (intake-2319): Validation is ordinal only (size monotonicity, NTK>PI, theta ratio, Gemini Pro>Flash), with no correlation against real tasks, in contrast to LongBioBench per-task Spearman vs HELMET.
- DPF-W4-CAPA-C5 (intake-2323): Capability-to-similarity trend and its implication for LM juries.
- DPF-W4-EFFREASON-E5 (intake-2327): Magnitudes (5-13% AIME gain, 8-14% editing gain) on hosted unquantised models.
- DPF-W2-DCNOISE-R1 (intake-2264): Chunk size has an empirical optimum (4K-32K at 128K); k*=2 (lrlm Thm 4) contradicted
- DPF-W2-DCNOISE-R5 (intake-2264): App N latency/cost assumes parallel workers
- DPF-W2-DCNOISE-R7 (intake-2264): Accuracy-vs-depth: not tested
- DPF-W2-LRLM-REPO-R1 (intake-2275): Three different k*: code sqrt-formula cap 20; Thm 4 k*=2; Alg 3 no-sqrt
- DPF-W2-LRLM-REPO-R2 (intake-2275): C_COMPOSE and a_leaf/a_compose are hardcoded; "accuracy scaling" is a loop over assumed numbers
- DPF-W2-LRLM-REPO-R3 (intake-2275): Map and filter sequential
- DPF-W2-LRLM-REPO-R5 (intake-2275): No llama.cpp; vllm backend = OpenAI client + base_url
- DPF-W2-RLMUNC-R2 (intake-2284): The headline compares equal wall-clock, not equal tokens.
- DPF-W2-RLMUNC-R5 (intake-2284): Semantic tasks (dialogue, document QA) benefit less from recursion; search-style tasks more.
- DPF-W2-RLMUNC-R6 (intake-2284): Formula text says "lower s(p) is better" yet selects argmax; only the argmax reading is consistent.
- DPF-W2-ARCHON-A1 (intake-2255): Budget as hard prune: configs exceeding inference-call, input-token or output-token caps are excluded before search, making comparisons compute-matched.
- DPF-W2-ARCHON-A2 (intake-2255): Search cost: >=230 random evaluations before the surrogate helps, 20% dev split; no token/dollar cost for the search itself.
- DPF-W2-ARCHON-A3 (intake-2255): Held-out 80% evaluation, with full-vs-held-out delta 0.44% mean.

## Hold-first prefix stagger probe spec (RTE-PFX-2, 2026-10-21; intake-2227#record)

Question: when `parallel_dispatch` fans out N requests that share a long prefix, does starting them simultaneously waste the cache that a first-then-N-1 start would have used? `parallel_dispatch` uses a thread pool with no stagger, so all N are released together.

**Arms** (one served role, one llama-server, `cache_prompt=true`, no `id_slot` pin, `-np >= N`, N declared):

- `simultaneous`: N requests released together (today's behaviour).
- `hold_first_tok`: request 0 first; siblings 1..N-1 released when request 0's first streamed token arrives.
- `hold_first_end` (control): siblings released when request 0 completes.

**Design.** Every trial prepends a fresh random salt to the shared prefix, so no earlier trial or arm can have warmed it. Arms interleave in a fixed seeded order across trials. Per request, from the server's own timings: `prompt_n` (uncached prompt tokens evaluated), `cache_n` (tokens served from cache), `prompt_ms`, plus client time to first token. Report per arm: uncached prompt tokens per request and in total, and time to first token per request, with the trial count and a spread. No hypothesis is stated as a result.

**Slot-selection check (the point of the probe).** A sibling benefits only if the server routes it to the slot that holds the prefix, and a busy slot cannot be chosen, so under `hold_first_tok` siblings may land on EMPTY slots and re-evaluate the prefix. Per sibling the verdict is `cache_n >= 0.9 x expected_prefix_tokens`, where the expected count is the tokenised length of the shared prefix measured with `/tokenize`, never assumed. Evidence recorded: the response `id_slot` when the server reports it, and a `/slots` snapshot taken while the siblings are in flight (a snapshot after the run proves nothing). The server's prompt-cache setting (`--cache-ram` or its absence) and `--slot-prompt-similarity` are recorded in the run header because they change the answer.

**Run conditions.** A timing window under `region-lock` with the host otherwise quiet; no orchestrator traffic. Script (refuses unless `WINDOW_CONFIRMED=1`): `epyc-orchestrator` `scripts/benchmark/rte_pfx2_stagger_probe.py`; unit test of the analysis and the window guard: `tests/unit/test_rte_pfx2_probe.py`. The run result follows its window.

## Track: qwen-chat-template-evaluation
<!-- gate: none -->

> Folded from `handoffs/active/qwen-chat-template-evaluation.md` @ `73719bffb350` on 2026-11-02 (BRF-T1-F14, route 1a, operator D1/D5; retired row RTG-54 → EVL-37). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Qwen Chat-Template Evaluation

**Scratch**: `/mnt/raid0/llm/tmp/refactor-01a16fc3/ct21-architect/` (queued/running owner packets and evidence; keep).

**Status**: stub
**Created**: 2026-08-21 (via research intake, operator-approved 2026-08-21)
**Categories**: llm_prompting, inference_serving, local_inference

#### Objective

Decide whether to move any Qwen3.x role off its GGUF-embedded chat template, and if so onto which
one — evaluated per-suite, on our own hardware, with the calibration cost priced in.

#### Research Context

| Intake ID | Title | Relevance | Verdict | Verification |
|-----------|-------|-----------|---------|--------------|
| intake-1212#record | Qwen-Sharp-Chat-Templates | high | adopt_component | dive-verified |
| intake-1213#record | froggeric/Qwen-Fixed-Chat-Templates | high | worth_investigating | dive-overturned |
| intake-1216#record | google/minja (NOT our engine) | medium | superseded | dive-overturned |
| intake-1217#record | Claw-Eval | medium | worth_investigating | dive-verified |

#### What the dives already settled (do not re-litigate)

Verified 2026-08-21 against primary source — the stock `Qwen/Qwen3.8-27B` template, the
Unsloth-patched template extracted from our own `/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf`, both
community templates, and the frozen `production-consolidated-v9` tree at `0db32c06e`:

- Sharp's thinking-ON render **minus** its terseness block is **byte-identical** to upstream v22.3's
  render, verified at three kwarg settings. Thinking-OFF differs by exactly the three documented
  fixes. The whole delta against upstream is four regions.
- The upstream "official template raises on `enable_thinking=false`" claim is **false** on both the
  stock template and the Unsloth template in our GGUF. The real fatal trigger is a
  `reasoning_effort` value outside `{xhigh, medium, low}` — and that raise sits *inside* the
  `enable_thinking` gate, so our stack-wide `enable_thinking=false` posture is immune to it.
- The "80% llama.cpp throughput" claim cannot hold: the template is compiled **once at model load**
  (`common_chat_templates_init`, sole server call site `tools/server/server-context.cpp:1454`), and
  the per-request path renders an already-compiled program (`server-common.cpp:1092`). Render *is*
  AST-shaped, but upstream's template is 3.0x larger and deeper than stock, so that mechanism runs
  against it.
- Thinking retention **IS** a differentiator, and it splits our fleet. Sweeping the template embedded
  in every production GGUF (see the table below): Qwen3.6-27B, Qwen3.6-35B-A3B and Qwen3.5-122B all
  **discard history thinking entirely** — both the inline `<think>` shape and the `reasoning_content`
  shape — while Qwen3.8-27B, froggeric and Sharp all retain it. *(An earlier pass tested only the
  Qwen3.8 generation and wrongly concluded retention was not a differentiator; corrected 2026-08-21.)*
- Sharp's only quantified plate is measured on **Claw-Eval, an agent-trajectory benchmark**, not on
  knowledge-work or coding accuracy — and the figures themselves exist only inside a PNG.

#### Fleet sweep — the embedded template of every production model (2026-08-21)

Extracted by GGUF header read, no model loaded. **Three distinct templates across four models.**

| Model / role | Template | `enable_thinking=false` | `reasoning_effort` outside {xhigh,medium,low} | `xhigh` by default | Empty-`<think>` duplication | Retains history thinking |
|---|---|---|---|---|---|---|
| Qwen3.8-27B — `architect_general` (per stack template) | 9,993 B `12827f24b742` | ok | **RAISES** on `none`; `high` silently → `xhigh` | **yes** | **yes** | yes |
| Qwen3.6-27B — `architect_general`/`coder_escalation` (per master registry) | 8,057 B `55d4931433fe` | ok | ok | no | no | **no — discards** |
| Qwen3.6-35B-A3B — `frontdoor` | 8,057 B `55d4931433fe` (byte-identical to above) | ok | ok | no | no | **no — discards** |
| Qwen3.5-122B-A10B — `architect_critic` | 7,992 B `8452ca85cb1e` | ok | ok | no | no | **no — discards** |

Two conclusions, opposite in direction:

- **Every defect is Qwen3.8-only.** The `xhigh` default, the `reasoning_effort` raise/coercion and
  the empty-`<think>` duplication do not exist on the three incumbent templates. Those are scoped to
  the model swapped in 2026-08-20 and are tracked in `qwen38-27b-replace-qwen36.md`.
- **The retention gap is the incumbents', not Qwen3.8's.** The three incumbent templates throw away
  past reasoning. That is precisely what the community templates fix, and it is the one claim in
  intake-1213#02 that holds against our actual fleet.

**But it is currently inert for us**, and that is the crux: we serve
`chat_template_kwargs.enable_thinking: false` on every one of these roles, so there is no reasoning
in history to retain. The retention fix only pays if thinking is turned ON for a role — a much
larger change than a template swap, and one this handoff does not assume.


##### CT-2 — calibration void inventory (2026-08-21)

**Framing finding, and it decides most of the table:** every measured row this stack owns was produced
through each model's **GGUF-embedded** template. There is no alternative — `--chat-template-file` has
**zero occurrences** in the orchestrator's launcher and registry code (`grep -rn "chat.template.file\|chat_template_file" src/ orchestration/ stack_templates/` → 0 hits; only `chat_template_kwargs` is
plumbed, `src/backends/llama_server.py:581-594`, `src/backends/openai.py:267-284`). The architect-bench
run protocol records server flags with no template override
(`handoffs/active/architect-model-selection-bench.md:218`). So "which arms were measured under which
template" has one answer: **all of them, under the embedded one.** A swap therefore moves *every* row
below off its measured condition simultaneously — there is no already-swapped control arm anywhere.

**Second framing finding: adopting a community template is not a config change.** The flag itself
exists in the frozen kernel (`common/arg.cpp:3487`, `{"--chat-template-file"}, "JINJA_TEMPLATE_FILE"`)
— it is the **orchestrator** that never emits it. So CT-1 is runnable by hand against a directly-invoked
`llama-server`, but *adoption* needs new launcher plumbing. Cost that as a prerequisite of adoption, not
as part of the swap, and note it does **not** block CT-1.

**Third: two rows are already void, before any template question.** The master registry names
`Qwen3.6-27B-MTP-Q8_0` for `architect_general` (`orchestration/model_registry.yaml:1766`) and
`coder_escalation` (`:1655`), while `stack_templates/default.yaml:139` launches **`Qwen3.8-27B-Q8_0`**
(commit `1cff5162`). The registry contains **zero** occurrences of `Qwen3.8` (`grep -n "Qwen3\.8"` → 0;
a bare `grep "Qwen3.8"` returns 4 false hits, all `Qwen3-8B-DFlash-b16` at `:506-511`, where `.` matched
`-`). Under the reasoning-effort-levels invariant — *"a role default is a (model × level) pair. Swapping
the model bound to a role … invalidates the level"* (`handoffs/active/reasoning-effort-levels.md:51-52`)
— the `swe_verified_pct: 57.5` rows at `:1689` and `:1826` are stamped to a model the role no longer
runs. **This is the intake-892 precedent's shape**: intake-892 established that a weights-level change
to reasoning emission is *a different model*, not a dial setting on the same one. A template change is
the same category of change applied to the prompt side. *(UNVERIFIED: I found no text anywhere in the
repo that states the "template change ⇒ different model" precedent in those words —
`grep -rn "different model" handoffs/active/ agents/ docs/` returns nothing template-related. The
extension from intake-892's weights case to the template case is an inference, sound but not yet
ratified doctrine.)*

**Fourth, and this is the actionable gap:** the E-7 re-calibration trigger stamps each certified curve
with `(model, quant, kernel/era)` and fires on *"a model swap, quant change, or kernel promotion"*
(`handoffs/active/reasoning-effort-levels.md:351-355`). **The chat template is not in the stamp and not
in the trigger list** — yet `architect-model-selection-bench.md:267` already ruled that the prompt-template
axis *"is a prompt-template property of each role, not a server flag, and it is the larger effect measured
so far"* (+32pp, `:264-267`). A template swap today would pass E-7's validator silently. Recommend adding
`template_sha256` to the E-7 stamp; that is a cheap fix and it belongs to the reasoning-effort handoff, so
it is recorded here as a cross-handoff finding rather than actioned.

| Artifact | Where it lives | Voided by template swap? | Re-measurement cost |
|---|---|---|---|
| SWE-bench Verified oracle-40 sealed rows (A3 `23/40` = 57.5%; comparators A1 `15/40`, A4 `13/40`, TC `21/40`) | `model_registry.yaml:1689`, `:1826`; `architect-model-selection-bench.md:3` | **YES** — accuracy is measured through the rendered prompt end to end | **expensive** (sealed capture + frozen v4 converter replay per arm) |
| R2a CoT-prompt **+32pp** result | `architect-model-selection-bench.md:264-267` | **YES** — this *is* the prompt-template axis by the handoff's own words | **expensive** |
| R2d `enable_thinking=false` stack-wide vindication (A1 18% / A4 50% non-termination) | `architect-model-selection-bench.md:333-353` | **PARTIAL** — the finding is about the *native channel*, but frog/sharp can flip that channel ON from message content (CT-3) and inject their own effort prose, so the ablation's "thinking OFF" arm is no longer guaranteed to be OFF | **moderate** (re-run the ablation, 2 arms) |
| GPQA-Diamond CoT / letter-only, LiveCodeBench `24/53` | `architect-model-selection-bench.md:113`, `:198`, `:572` | **YES** | **expensive** |
| `q_scorer` **`baseline_tps_by_role`** | `orchestration/repl_memory/q_scorer.py:368`, compiled via `src/registry/stack_priors.py`; registry `:1631`, `:1684`, `:1819`, `:1882` | **NO** — the canonical baseline instrument is `llama-bench`, which never renders a chat template | **cheap** (and not needed) |
| `q_scorer` **`baseline_quality_by_role`** / `quality_pct` 93, `quality_score` 2.57/3 | `q_scorer.py:369`; registry `:1634`, `:1886` | **YES** — quality priors are scored on rendered prompts | **moderate** |
| `optimized_tps` 47.79 / 40.22 / 24.0, `contended_tps` 19.81 | registry `:1633`, `:1687`, `:1822` (attest `P-BENCH-PLACEMENT-1`, published stack record §01) | **PARTIAL** — steady-state decode is bandwidth-bound and prompt-insensitive, but a template that adds a 209-char system preamble (or turns thinking on) changes prefill share and output length, which moves the end-to-end figure | **cheap** (re-run the pinned prodopt harness) |
| `draft_max` spec-dec optimum — registry **4** vs stack override **8** | registry `:1793`, `:1876`, `:1626`; `stack_templates/default.yaml:154` | **PARTIAL** — production runs `--spec-type draft-mtp`, MTP self-draft alone (`speculative_decoding_policy`, `:1271-1280`). Self-draft acceptance is a property of the *token stream*, and a template that enables thinking changes that stream's character wholesale (reasoning prose drafts differently from answer prose) | **moderate** (one draft-depth sweep per affected role) |
| Certified reasoning-effort curves | `reasoning-effort-levels.md:49-56`, E-7 `:351-355` | **YES** if thinking is enabled; **PARTIAL** otherwise — and note the stamp does not currently include the template (gap above) | **expensive** |
| Saved KV prefix slots (`slot_save_path: /tmp/kv_frontdoor_full`) | `stack_templates/default.yaml:91` | **YES** — any byte change to the rendered prefix invalidates every saved slot | **cheap** (self-healing; slots simply re-warm) |
| TB-6 np×L context-batching surface, prefill-to-depth RAG arms | `architect-model-selection-bench.md:536`, `:562` | **PARTIAL** — explicitly throughput-only observations, but they were captured no-think and a template that can flip thinking on changes generated length per cell | **moderate** |
| `swe_verified_shape_caveat` (measured `-c 49152`/f16 KV/`-np 1`; production `-c 16384`/q8_0/slots 2) | registry `:1831` | **PARTIAL** — already an assumed transfer; a template swap adds a second unmeasured transfer on top of it | n/a (compounds an existing caveat) |

**Cost summary.** A stack-wide swap voids **4 expensive** artifacts (SWE-40, +32pp CoT, GPQA/LCB,
effort curves), **5 moderate**, and **2 cheap/none**. The expensive four are the entire comparative
authority of `architect-model-selection-bench.md`. A **single-role pilot** voids only that role's slice
and leaves the cross-arm comparisons intact — which is the whole argument for CT-5 option (b)/(c) over a
fleet swap.

##### CT-3 — input-marking analysis of the community templates (2026-08-21)

Method: `common/jinja/README.md` (frozen tree, read-only) names two caveats; both templates were grepped
for those shapes and then **rendered** with Jinja2 3.1.6 from the orchestrator venv with `raise_exception`
stubbed, `enable_thinking=False`, against stock and our GGUF template as controls.

First, input marking **is active** on the serving path: `mark_input = true` is the default
(`common/chat-auto-parser.h:73`) and is passed straight through at `common/chat.cpp:920` →
`jinja::global_from_json(ctx, inp, inputs.mark_input)`. So the defence is on and the question is fair.

*Wording rule (CT-20, 2026-10-21): results in this table are static-fixture evidence only; any claim that `control_tokens.py`, `injection_scanner`, a prompt sentence or datamarking protects must be worded `static-attack ASR on fixture set X` and never as robustness, because adaptive attackers broke the published static defences (intake-2294#record).*

| Pattern | frog | sharp | stock / our GGUF | Risk under input marking | Verdict |
|---|---|---|---|---|---|
| Special token **built by concatenation** from a message field — the README's literal caveat `'<\|' + message['role'] + '\|>'` | no | no | no | n/a | **CLEAN.** Stock and our GGUF do `'<\|im_start\|>' + message.role + '\n'` (`stock:109,117,119`; `qwen38_official:112,120,122`) — the token is a **whole literal** in one non-input part, with role appended *after* it, so it is not the caveat shape. frog/sharp put role in a plain-text label inside a user turn: `'<\|im_start\|>user\n[' + message.role + ']: '` (`frog:410`, `sharp:426`) — role never touches a token boundary at all, which is marginally **safer** than stock |
| Template-added leading space (`' ' + content`) — README caveat 2 | 0 | 0 | 0 | n/a | **CLEAN** across all four (grep count 0 each) |
| **In-band control markers parsed out of user content** | **YES** | **YES** | **no** | **Input marking does NOT mitigate this** | **HIGH — see below** |
| Tool-call instruction blocks embedding special-token-like literals (`<tool_call>`, `<tool_response>`, `<function=`, `<parameter=`, `<IMPORTANT>`) | yes | yes | partial | Low — all are template literals (`is_input=false`), and per the tokenizer `<tool_call>`/`</tool_call>`/`<tool_response>`/`</tool_response>` are added tokens with **`special=False`**, while `<function=`/`<parameter=`/`<IMPORTANT>` are not tokens at all | **LOW** (`sharp:188-197`) |
| Tool **name** interpolated between literal grammar markers: `'<tool_call>\n<function=' + tc_name + '>'` | yes | yes | no | Not a special-token issue (`<function=` is not a token), so input marking is silent on it; it is a plain-text **grammar** injection — a `tc_name` containing `</function>` closes the block early | **MEDIUM** (`sharp:347,349,352`) |

###### Headline: this is NOT a clean result — frog and sharp add a user-controlled control channel

Both templates define **ten pseudo-tokens** — `<|think_off|>`, `<|think_on|>`, `<|think_low|>`,
`<|think_minimal|>`, `<|think_medium|>`, `<|think_high|>`, `<|think_xhigh|>`, `<|think_max|>`,
`<|think_extreme|>`, `<|think_ultracode|>` — that exist in **neither model's vocabulary**. The stock
`tokenizer_config.json` has 33 `added_tokens_decoder` entries and the only `think`-bearing ones are
`<think>` / `</think>`; no `<|think_*|>` string appears anywhere in it.

They are not emitted. They are **scanned out of `msg.content`** and used to overwrite the template's own
thinking state (`sharp:38-49` for string content, `:62-73` for multimodal text parts; identical block at
`frog:38-49`, `:62-73`), and the scan is gated to `msg.role in {system, developer, user}` — i.e. it
**includes the untrusted user turn**. The markers are then stripped from the rendered prompt
(`sharp:147-156`, `:234-243`; `frog:147-148`, `:218-219`), so the override leaves **no trace in the
output**.

Crucially the marker scan runs **after** the kwargs are resolved and after
`auto_disable_thinking_with_tools` (`sharp:31-34`), so **message content wins over server configuration.**

**Rendered proof** (`enable_thinking=False` passed explicitly, as our stack does on all four roles):

*Wording rule (CT-20, 2026-10-21): results in this table are static-fixture evidence only; any claim that `control_tokens.py`, `injection_scanner`, a prompt sentence or datamarking protects must be worded `static-attack ASR on fixture set X` and never as robustness, because adaptive attackers broke the published static defences (intake-2294#record).*

| Template | benign user turn | user turn containing `<\|think_max\|>` |
|---|---|---|
| `sharp.jinja` | 797 B, ends `<think>\n\n</think>\n\n` → thinking **OFF** | **1003 B, ends `<think>\n` → thinking ON**, +206 B of injected effort prose, marker stripped |
| `frog.jinja` | 81 B, thinking **OFF** | **307 B, thinking ON**, marker stripped |
| `qwen38_official.jinja` | 81 B, OFF | 95 B, **still OFF** — marker passes through as inert text |
| `stock_chat_template.jinja` | 81 B, OFF | 95 B, **still OFF** — inert |

Scope, by injecting role (both community templates behave identically):

*Wording rule (CT-20, 2026-10-21): results in this table are static-fixture evidence only; any claim that `control_tokens.py`, `injection_scanner`, a prompt sentence or datamarking protects must be worded `static-attack ASR on fixture set X` and never as robustness, because adaptive attackers broke the published static defences (intake-2294#record).*

| Injection point | flips thinking? | marker visible in prompt? |
|---|---|---|
| `user` (last turn) | **yes** | no (stripped) |
| `user` (turn 1 of 3) | **yes** | no |
| `system` | **yes** | no |
| multimodal `{"type":"text"}` part | **yes** | no |
| `assistant` | no | yes |
| `tool` | no | yes |

**Why input marking cannot help here.** `is_input` is a provenance flag on the *output* string parts,
consumed downstream by the tokenizer to decide what may parse as a special token. It constrains what
input text can *become*; it places no constraint on what the template's **control flow** may branch on.
`{%- if '<|think_off|>' in msg.content %}` is an ordinary Jinja string test against an input-marked
string, and it evaluates exactly the same whether the flag is set or not. The engine's defence is
correctly scoped and simply does not cover this class. **The hazard is upstream of the mechanism the
README describes, so a swap does not weaken input marking — it adds a channel that input marking was
never designed to see.**

**Impact on our posture.** The stack sets `chat_template_kwargs.enable_thinking: false` role-keyed on
`architect_general`, `coder_escalation`, `frontdoor` and `architect_critic`. Under frog or sharp, **any
client able to place fourteen literal characters into a user or system message silently revokes that
setting** for the whole conversation — turning on a reasoning channel that
`architect-model-selection-bench.md:342` measured as *worse on quality and 2.8–6× the tokens*. That is a
low-trust input overriding a high-trust generation policy, with no audit trace in the prompt. It is also
directly a **cost** channel: unmetered token amplification triggerable from message content.

**Mitigations, if adoption is ever pursued** (cheap, and they preserve the retention fix that motivated
these templates): (i) delete the two marker-scan blocks and the ten strip lines — the retention behaviour
is independent of them; (ii) or restrict the scan to `msg.role == 'system'` only; (iii) or strip
`<|think_*|>` from message content at the orchestrator boundary before the request leaves
`src/backends/llama_server.py`. Option (i) is the smallest diff and is what CT-4's pinning should record
if anything is adopted.

**Verdict: sharp and frog are NOT drop-in safe.** The finding is independent of the terseness question
and independent of retention, and it applies to both community templates equally.

##### CT-5 decision package (drafted 2026-08-21, operator decision pending)

**The question, stated narrowly.** Not "should we swap templates" and not "is the terseness prompt good".
Only: **should any role run `enable_thinking=true` with prior-turn reasoning retained in history?**
Retention is inert at `enable_thinking=false`, so retention has no value of its own — it is a rider on a
thinking-ON decision, and it must be decided in that order.

**Two facts reframe the options before the options start.**

1. **Retention does not require a community template.** `Qwen3.8-27B` — the model
   `stack_templates/default.yaml:139` actually launches on `architect_general` — **already retains
   history thinking with its own embedded template.** Rendered proof: with
   `enable_thinking=True` and an assistant turn carrying `reasoning_content`, `qwen38_official.jinja`
   emits the prior reasoning (`retains_prior_reasoning=True`), while `Qwen3.6-27B-MTP-Q8_0.gguf.jinja`
   and the `Qwen3.5-122B` template both drop it (`False`, `False`). So the retention fix that motivates
   frog/sharp is **already in the tree**, on the one role most likely to want it, at zero template risk.
2. **Turning thinking ON unlocks the Qwen3.8 defects, which are currently unreachable.** Rendering
   `qwen38_official.jinja` across `reasoning_effort ∈ {none, minimal, low, medium, high, xhigh, unset}`:
   at `enable_thinking=False` **all seven render fine** (71 B each). At `enable_thinking=True`,
   `none` and `minimal` **raise** (`Unexpected reasoning effort …`), `high` silently renders identically
   to `xhigh` and to the default (297 B each, vs `medium` 60 B, `low` 226 B). The stack's immunity to
   these is *entirely* a side effect of thinking being off. **Any thinking-ON pilot must first fix the
   request path to never send `none`/`minimal`, or it will return 500s in production.**

**Option (a) — status quo: `enable_thinking=false` everywhere; retention moot.**
- *Cost:* zero. No calibration voided (CT-2 table untouched).
- *Pays:* keeps the R2d vindication (`architect-model-selection-bench.md:333-353`) and the +33pp
  frontdoor no-think finding intact and load-bearing; keeps the Qwen3.8 `reasoning_effort` raise
  unreachable; keeps every sealed SWE/GPQA/LCB row on its measured condition.
- *Gated by:* nothing. This is the null action.
- *Risk:* the only thing forgone is an **unmeasured** upside. Note also that R2d certified the thinking
  axis on **A1 (122B-IQ2)** and **A4 (35B-A3B)** — *not* on the 27B dense, and certainly not on
  Qwen3.8-27B. Under `reasoning-effort-levels.md:49-50` ("certified per model"), `architect_general`'s
  current thinking-OFF setting is an **uncertified inheritance**, not a measured result for its model.

**Option (b) — pilot thinking-ON + retained history on ONE role, with a community template.**
- *Natural pilot, by elimination:* `coder_escalation` **cannot** be piloted independently — it is
  `alias_to: architect_general` (`stack_templates/default.yaml:101`), one process under two names.
  `frontdoor` is the worst candidate: highest traffic, holds the saved KV prefix slots
  (`default.yaml:91`), and owns the strongest contrary evidence (+33pp no-think). `architect_general`
  carries the most calibration at risk (the entire SWE-40 authority row). That leaves **`architect_critic`**
  (`model_registry.yaml:1851`, 122B on CPU `:8074`, own process, terminal escalation rung, lowest traffic)
  as the only role that is independently pilotable with a small calibration slice — it has no
  `swe_verified` row and no `quality_pct`, only `quality_score: 2.57/3` (`:1886`) and `baseline_tps: 11.3`.
  A critic is also, on its face, the role where retained reasoning should pay most.
- *Cost:* new `--chat-template-file` launcher plumbing (does not exist today — CT-2); voids
  `architect_critic`'s `quality_score` and its `draft_max: 4` (`:1876`); **and accepts the CT-3 injection
  channel into production.**
- *Pays:* prefix-cache hit on multi-turn critic exchanges; the untested quality delta from retained
  reasoning.
- *Gated by:* CT-1's A/B, **plus** a CT-3 mitigation landing first.
- *Verdict as drafted:* **not recommended.** It is the most expensive option (new plumbing + eval on the
  slowest model at 11.3 t/s baseline) and it is the only option that imports the CT-3 hazard. Its one
  distinctive benefit — retention — is available for free under option (c).

**Option (c) — thinking-ON with the STOCK/embedded template, on `architect_general` (Qwen3.8-27B).**
- *Cost:* voids `architect_general`'s `quality_score`/`swe_verified` slice — **which CT-2 shows is
  already void**, since those rows are stamped to `Qwen3.6-27B` (`:1766`, `:1826`) and the role launches
  `Qwen3.8-27B`. So the marginal calibration cost is close to zero: it re-measures a row that must be
  re-measured anyway. Also requires the `reasoning_effort` request-path fix (fact 2 above), and a
  `draft_max` re-check (`default.yaml:154` is `8`, swept on Qwen3.8 but swept **no-think**).
- *Pays:* retention on multi-turn architect exchanges with **no third-party code in the prompt-construction
  position**; no new launcher plumbing; the Qwen3.8 `xhigh`-by-default 209 B instruction becomes a lever
  rather than a latent defect.
- *Gated by:* CT-1's A/B, run on this model — and CT-1 becomes *cheaper* here, because it is a
  `chat_template_kwargs` flag flip rather than a template swap.
- *Risk:* R2d says native `<think>` lost on two other models via a non-termination tail (18%/50%). That
  is real prior evidence against, but it is **not evidence about this model**, and the
  `--reasoning-budget N --reasoning-budget-message` lever that `reasoning-effort-levels.md:359-362`
  records as force-closing the think block is available to bound the tail.

**Recommendation.** Hold **option (a)** as the standing posture, and authorise **option (c) as a
measurement only** — not a stack change — on `architect_general`. Rationale: it is the only option whose
calibration cost is already sunk, the only one needing no new code, and the only one that gets retention
without importing the CT-3 injection channel. **Option (b) should be declined outright** unless CT-3's
mitigation (i) is applied and pinned under CT-4. Reject any *fleet-wide* thinking-ON change regardless of
outcome — the three incumbent templates discard history, so retention would not even function on
`frontdoor` or `architect_critic` without the template swap that option (b) prices.

**Single cheapest discriminating measurement.** On `architect_general` (Qwen3.8-27B, already loaded), run
the pinned GPQA-Diamond-CoT item set twice — `enable_thinking=false` vs `enable_thinking=true` with
`reasoning_effort=medium` and `--reasoning-budget` set — reporting **per-suite, never aggregate**, with
non-termination rate and tokens-per-solved captured alongside accuracy. It is a two-arm flag flip on a
resident model, it needs no launcher change and no template file, it directly tests the one claim
option (c) rests on (does *this* model's native channel behave like A1/A4 did?), and its result is
decision-sufficient: if the non-termination tail reproduces on Qwen3.8, retention is dead for the whole
fleet and CT-5 closes at option (a) permanently.

**Prerequisite before that run:** confirm the request path cannot emit `reasoning_effort` of `none` or
`minimal`, which raise once thinking is on (fact 2). That check is grep-cheap and is not gated on
anything.

#### Open Questions

- Does the terseness prompt help, hurt, or do nothing on *our* suites at `enable_thinking=false`,
  where there are no thinking tokens to cut?
- What does a template swap cost in voided calibration? Architect-bench arms, `q_scorer`
  baselines and reasoning-effort settings were all measured under the current template.
- A chat template is executable code in the prompt-construction position, sitting on top of the
  in-tree engine's **input-marking** defence against special-token injection
  (`common/jinja/README.md`). What does a third-party template do to that property?

#### Tasks

- [x] **CT-1 ✅ 2026-08-21 — RAN TO COMPLETION AND RETURNED PERFECT PARITY, for a structural
      reason verified afterward: for the eval request shape (bare single user turn, no system
      prompt, no tools, `enable_thinking=false`) the embedded template and epyc-qwen3x-v1 render
      BYTE-IDENTICAL prompts, so all 160 paired generations were bit-identical (zero flips, every
      statistic equal to the decimal; artifacts `artifacts/chat-templates/epyc-qwen3x-v1/ab-cpu-20260821/`).
      WHAT THIS ESTABLISHES: epyc-v1 is a PROVEN drop-in no-regression replacement on the
      production single-turn path — 320 real generations through the real engine, zero divergence.
      WHAT IT CANNOT ESTABLISH (by construction): the templates only diverge on system prompts,
      tools, multi-turn history and effort steering, none of which this shape exercises. DESIGN
      LESSON, owned: the arms should have been render-diffed on THE EVAL SHAPE before spending
      3.2 h of CPU — the 5-second check existed and was run on every shape except that one
      (probe-config-before-long-runs violation, recorded). The terseness question is unanswered
      and moves to CT-1b. Original task follows.** A/B one Qwen3.x role via
      `llama-server --chat-template-file` — arms per CT-1a (the
      built epyc-qwen3x-v1, not the community file) — against its embedded
      template on a pinned eval set. Report **per-suite, never aggregate** (intake-1214: a
      conciseness instruction near-neutral in aggregate carried a 27.69% math penalty for the
      weaker model). No requantization, no registry change, no kernel touch.
- [x] **CT-2** — Price the calibration cost before any stack-wide swap: enumerate which measured
      artifacts (architect-bench arms, `q_scorer` baselines, draft-depth settings) are voided by
      changing the rendered prompt. ✅ 2026-08-21 (inventory above: 4 expensive / 5 moderate / 2 cheap
      voids; every measured row in the fleet was captured under the embedded template because
      `--chat-template-file` has zero occurrences in the orchestrator; `architect_general` +
      `coder_escalation` SWE rows are ALREADY void on the registry/stack-template model divergence; and
      the E-7 re-calibration stamp omits the template entirely)
- [x] **CT-3** — Check a third-party template against the in-tree input-marking path
      (`common/jinja/`, and the input normalisation `common/chat.cpp` applies before the runtime).
      ✅ 2026-08-21 (NOT clean: neither README caveat fires, but frog and sharp both parse ten
      out-of-vocab `<|think_*|>` markers out of user/system message content, silently overriding
      `enable_thinking=false` and stripping the marker — input marking cannot see it, because it
      constrains tokenization, not template control flow. Rendered proof in the analysis above)
- [ ] **CT-4** — If anything is adopted, pin the exact revision + sha256, not a branch.
- [x] **CT-5 ✅ 2026-08-21 — MEASURED AND CLOSED AT (a).** The (c) measurement ran to completion
      (60 paired gpqa_diamond_cot, Qwen3.8-27B on MI210, v9 HIP residency proven by three
      instruments, 0 errors; artifacts: `artifacts/chat-templates/ct5c-gpu-20260821/`). TWO-PART
      RESULT: (1) **the R2d think-loop tail did NOT reproduce** — non-termination 19/60 (T0,
      thinking OFF) vs 21/60 (T1, ON): mode-independent, driven by the 4096 cap + the suite's own
      CoT prompt, not a thinking pathology; Qwen3.8's native channel is better-behaved than
      A1/A4's. (2) **Thinking-ON failed to pay regardless**: acc 63.3% vs 70.0%, paired flips 7:3
      AGAINST thinking (n.s., McNemar p≈0.34), tokens-per-solved +23% (4,135 vs 3,358), mean think
      6,031 chars consuming the budget. No measured upside, real measured cost → **(a) stands as
      posture; (c) declined for deployment.** Caveats recorded honestly: ~⅓ of BOTH arms truncated
      at the 4096 cap (identical caps keep the comparison fair but compress the detectable delta);
      a higher-cap rerun could in principle move this and is DECLINED by default — nothing queues
      it. Retention remains inert under (a) by construction. **SAME-DAY CORRECTION (operator-prompted: "why do we keep finding reasoning makes quality
      worse?"): the 6.7pp deficit is ENTIRELY a truncation/budget artifact.** Decomposition:
      completed-subset accuracy 95.1% (T0) vs 94.9% (T1); both-completed paired n=35 → 34 vs 33,
      flips 1:0; truncated rows ≈ automatic zeros (0/21 T1-truncated ever emitted an answer line;
      truncated-T1 median think 11,078 chars vs 3,187 completed — runaway think eats the 4,096 cap).
      Public Qwen thinking numbers run ~32K budgets where truncation ≈ 0. So this measurement
      answered the OPERATING-POINT question (at 4K total, thinking does not pay) — NOT the
      capability question. Historical context folded in: prior anti-reasoning findings (+33pp
      no-think, R2d tails) were broken-serving artifacts on other models; reasoning has never been
      measured here with working serving AND adequate budget — until the 16K rerun landed at 18:40Z
      (same 60 pairs, symmetric 16,384 caps; artifacts `artifacts/chat-templates/ct5c-gpu-20260821/rerun-16k/`).
      **16K RESULT — the budget-artifact hypothesis CONFIRMED in full:** T0 85.0% (51/60, nonterm 0)
      vs T1 86.7% (52/60, nonterm 1), flips 2:3 IN FAVOUR of thinking (n.s.), mean think 9,693 chars.
      Both arms rose enormously from the 4K run (70.0/63.3 → 85.0/86.7) — the cap was crushing
      no-think too. VERDICT: reasoning is NOT worse on this stack — it is statistically TIED at fair
      budget, and every historical anti-reasoning datum here is now accounted for as infrastructure
      (loops, termination, templates, or caps). Posture (a) remains optimal on ECONOMICS alone:
      +21% tokens-per-solved (4,809 vs 3,972) for +1.7pp n.s. on a CoT-prompted suite where visible
      CoT already captures the reasoning benefit. The thinking axis is now MEASURED on Qwen3.8
      itself (resolving the uncertified-inheritance caveat from the options table). ORIGINAL RULING + task follow: OPERATOR
      RULED 2026-08-21: hold (a) as posture, (c) authorised as a measurement
      ("once you negotiate a quiet GPU window… you can test it out"). Measurement LAUNCHED same hour
      (GPU idle, window free): `/workspace/tmp/ct5c-gpu/ct5c_runner.py` — Qwen3.8-27B on MI210
      (v9 HIP, draft-mtp n8, embedded template), 60 pinned gpqa_diamond_cot (seed 42), paired
      per-request flag flip T0 `enable_thinking=false` vs T1 `true`+`reasoning_effort=medium`
      (medium = zero-token default, deliberately avoiding the xhigh injection), prod sampling,
      max_tokens 4096 both arms. Prerequisite (request path cannot emit none/minimal) SATISFIED by
      Q38-T1 evidence: zero `reasoning_effort` emissions reach llama-server from src/. FINDING: v9
      has NO `--reasoning-budget` flag — the lever `reasoning-effort-levels.md:359-362` cites does
      not exist in this build; the tail is bounded by max_tokens and non-termination measured via
      finish_reason. Box stays open until the measurement decides: tail reproduces → close at (a)
      permanently; clean → (c) proceeds to a decision. Original task follows.** Decide the retention
      question on its own merits, separately from the terseness
      prompt. The three incumbent templates discard history reasoning; the community templates keep
      it. Under `enable_thinking=false` this changes nothing, so the real question is whether any
      role should run thinking-ON with retention — which is where the prefix-cache argument would
      pay and where the reasoning-budget work in `per-request-reasoning-budget.md` already lives.
      Do not bundle this with CT-1. *(package drafted 2026-08-21, awaiting operator — see
      "CT-5 decision package" above; recommendation is hold status quo + authorise a measurement-only
      thinking-ON A/B on `architect_general`, and decline the community-template pilot on CT-3 grounds)*
- [x] **CT-1b ✅ 2026-08-21 — RAN AND THE TERSENESS PROMPT DELIVERS.** Arm 2 (epyc-v1 + Sharp's
      terseness block, sha256 `1443ea9ab4bb…4551`, injection-free by construction) vs arm 0
      (embedded), same 160 pinned ids, fixed 900-token budget (artifacts
      `ab-cpu-20260821/ct1b-terse/`). Per-suite at the production operating point: math 80.0=80.0%
      (flips 1:1) at **−34% tokens**; mmlu_pro 37.5→40.0% [under-scored, see CAVEAT 2026-09-17 below] (4:5) at **−99%** (mean 2.0 tokens — the
      model finally obeys "letter only"); gpqa_diamond 42.5→**60.0%** (flips **0:7**, McNemar
      p≈0.016 — the one significant cell) at −99.5%; cruxeval 27.5→30.0% (3:4) at −36% with
      truncation 21→12. DECOMPOSITION (per the locked rule): the gpqa gain is mostly
      truncation-avoidance (arm 0 lost 12/40 to the cap; completed-only 53.6 vs 60.0 with
      non-comparable subsets) — the honest claim is **never worse, significantly better where
      budget binds, at 34–99.5% fewer answer tokens**. CCoT's math-penalty hazard did NOT
      materialize (80=80, flips 1:1). WATCH-ITEM, not finding: cruxeval completed-only hints
      terseness may compress useful working-through on output-prediction (57.9 vs 42.9,
      selection-biased subsets; paired flips 3:4 ≈ parity). NET FOR THE INTAKE: Sharp's claimed
      direction (fewer tokens, no accuracy cost) VALIDATES on our stack — via OUR injection-free
      build, not the community file. Deployment decision is the operator's; the artifact is ready.
      Original task follows.** the DISCRIMINATING A/B: +terseness variant (Sharp's active ingredient).** Build
      the arm-2 template (epyc-v1 + Sharp's terseness block — the one component with zero
      measurement anywhere) and rerun the CT-1 protocol against arm 0; on this shape the renders DO
      differ (system-turn injection), so the A/B has power. Same runner, same pinned ids, ~3.2 h
      CPU. Per-suite + flip analysis + MC-scorer decomposition as locked. This is the last open
      empirical question of the 2026-08-21 intake.
- [x] **CT-DEPLOY ✅ 2026-08-22 — the terseness pilot is LIVE IN PRODUCTION** on frontdoor (all
      three instances, render-verified) and architect_general (+ coder_escalation via alias):
      `server_mode.<role>.chat_template_file` plumbing landed (orchestrator `34ff6fcc`), registry
      blocks with per-role one-line reverts (research `b9ba66e6`), stack-change check fully green
      INCLUDING runtime attestation. Two launcher defects found+fixed en route (gate realized-mode
      deadlock — dodged; silent vacuous reload of sub-full instances — fixed with addressability +
      exit-1 + parity test). E-7 recalibration of both voided stamps running 2026-08-22.
- [x] **CT-E7 ✅ 2026-08-22 — E-7 recalibration RUN and stamped** (operator-directed; live
      production path; stamp `(model, quant, v9 0db32c06e/10125, template 1443ea9ab4bb)`, prod
      sampling, maxtok 900; raw artifacts on disk at `/workspace/tmp/e7-recal/` — kept off GitHub
      per the no-raw-material policy; the belief sidecars are the durable record).
      **frontdoor** (35B, CPU): math 82.5% @281tok · mmlu_pro 37.5% @45 · gpqa_diamond 55.0% @2 ·
      cruxeval 32.5% @394 — CT-1b's arm-2 numbers REPRODUCED on the live path (live==measured).
      **architect_general** (Qwen3.8, GPU) first-ever stamps at this template: math 85.0% ·
      mmlu_pro 27.5% · gpqa_diamond 47.5% · cruxeval 22.5%, zero errors. **gpqa_diamond_cot VOID
      at maxtok 900** (48/60 truncated — the finish_reason rule catching this session's own design
      miss; CoT suites need the 4096+ budget CT-5 established); excluded from the sidecar; 4096
      rerun same day, sidecar supersedes: **75.0% (45/60), mean 2,183 tok, 14 truncated** —
      +45pp from the cap fix alone, and ABOVE the embedded template's CT-5 baseline on the same
      pinned ids at the same budget (70.0%). Superseding row grades Witnessed/Attested. All 8 valid cells emitted as producer-authored belief
      rows grading **Witnessed/Attested, empty reasons** — the program's first decision-gating
      measurements. Second design miss recorded: role arms ran sequentially despite CPU/GPU
      concurrency doctrine (~30 min lost; runner-template rule filed in the shard).
- [x] **CT-E7b ✅ 2026-08-23 — E-7 stamps PROPAGATED into the master registry quality
      rows; compile chain regenerated and FULLY GREEN.** Master (research) `577f215a`:
      frontdoor `quality_pct: 93` (May-4 judge) VOIDED → E-7 live-path re-stamp at
      template `1443ea9ab4bb` (math 82.5/mmlu_pro 37.5/gpqa_diamond 55.0/cruxeval 32.5,
      CT-1b arm-2 REPRODUCED live); architect_general + coder_escalation swe_verified 57.5
      VOIDED (Qwen3.6-27B A3 arm; model swapped + template swapped) → first-ever Qwen3.8
      stamps (85.0/27.5/47.5/22.5 + gpqa_diamond_cot 45/60 = 75.0% @4096, superseding the
      900-cap void). All nine E-7 cells now live in the derived layer's
      `quality_by_axis.local`; orchestrator `5c41567d` regenerated lean + descriptors +
      derived + summary; `guard ok / guard_strict ok / acceptance: no-inference checks
      passed`. Belief sidecars: `chat_template_ab_capture.v1`, all Witnessed/Attested,
      rows `ctab_e1e56fda…` / `ctab_c16c50e1…` (frontdoor / architect_general) + the
      cot4096 superseding row. Also fixed two evidence citations that resolved nowhere
      from the research repo (epyc-root artifacts now cited by absolute path). — propagate the new stamps into the MASTER registry quality rows** (frontdoor +
      architect_general + the qwen38 role row). Deliberately NOT rushed at session end —
      master surgery earned a near-miss today; do it fresh with the compile chain run + check green,
      sourcing the numbers from CT-E7 and the belief sidecars.
      - **CAVEAT 2026-09-17 (sub-scorer-fix): every mmlu_pro cell in CT-1, CT-1b, CT-E7 and CT-E7b is
        UNDER-SCORED.** All four ran before CJ-8 on the shared pool with `scoring_config={}`.
        - **Cause.** The scorer's letter range was A–H. So the 10/40 pinned items whose gold is I or J were
          forced False regardless of the answer. The same 40 ids were used in every arm.
        - **Offline re-score** of the recorded `answer_tail` (last 200 chars) with the fixed scorer
          (`choice_labels`, orchestrator `f0015306` (branch `sub/scorer-fix-orch-20260917`; landing on main is blocked by the held orchestrator push lock)). These are estimates, not re-runs:

          | cell | recorded | re-scored |
          |---|---|---|
          | CT-1 arm0 | 37.5% | ~47.5% |
          | CT-1 arm1 | 37.5% | ~47.5% |
          | CT-1b arm2 | 40.0% | ~52.5% |
          | E-7 frontdoor | 37.5% | ~50.0% |
          | E-7 architect_general | 27.5% | ~40.0% |

        - **What still holds.** Directions and paired flips are unchanged in sign, and the other suites are
          unaffected.
        - **What is wrong.** The master-registry `mmlu_pro` quality values (37.5 / 27.5) and the E-7 belief
          sidecars (`/workspace/tmp/e7-recal/*/belief_measurements.jsonl`, not in the ledger) carry the
          under-scored value. Correcting them needs a re-stamp on the fixed scorer. See
          `progress/2026-09/2026-09-17-sub-scorer-fix.md`.
- [x] **CT-9 ✅ 2026-08-23 — PILOT ADOPTION DECISION (post-observation, one line per role):
      HOLD all three pilot roles; no fleet-wide extension; nothing reverted.** Decision
      basis = production behavior over the ~18 h window (2026-08-22 13:55Z →
      2026-08-23 08:00Z), NOT new benchmarks. Evidence (read-only sweep of
      orchestrator.log, llama-server logs, /health, API dashboards; full bundle in the
      CT-9 evidence record below): **the window carried CALIBRATION traffic only — zero
      real user/autopilot traffic after 15:36:49Z** (autopilot intentionally stopped
      since 2026-08-09; inference_tap last section 2026-08-10; the 186 API completions
      and 4,943 server-side slot lines are the E-7 recalibration runs). Operational
      signal across the window: **0 server errors, 0 truncations, 0 slot-restore
      failures, 0 KV-migration events** on :8070/:8080/:8180/:8083; one gateway-side
      504 whose server-side completion returned 200 (slow CPU completion, not a
      template failure); halves :8080/:8180 received **zero requests ever** (startup
      mlock warning only, memory-pressure, not template-related). The 2026-08-23 KV
      migration bug (`98061c6b`) is **independent** of the pilot — all 9 header-only
      slot files predate it by 3–4 weeks. DECISION LINES:
      - **frontdoor → HOLD.** Zero error/truncation signal in-window; E-7 stamps
        (82.5/37.5/55.0/32.5) reproduce CT-1b arm-2 on the live path. No drift to act
        on; the revert is one line (`chat_template_file`) if a signal appears.
      - **architect_general → HOLD.** First-ever stamps at this template
        (85.0/27.5/47.5/22.5, cot 75.0 @4096); 282 clean slot releases, 0 errors.
        Revert one line.
      - **coder_escalation (alias on :8083) → HOLD.** Same server, same evidence as
        architect_general; **no production signal exists** — the cruxeval watch-item
        (CT-1b) has NO basis in this window (8 calibration completions only, no
        scoring pipeline ran). Watch-item stays open pending real coder traffic.
      - **fleet-wide → NOT EXTENDED.** The adoption precondition "serves real traffic
        for a while" is NOT met (window = calibration only). Extending worker_* /
        ingest / critic would void their CT-2 calibration slices on an UNMEASURED
        basis — the exact thing CT-2 priced. Re-decide after real traffic
        accumulates, or on operator direction.
      **What would flip a role to REVERT:** any error/truncation/slot-restore
      signature on its live path, or real-traffic quality drift — none observed.
      Evidence record: `progress/2026-08/2026-08-23.md` (full bundle from the
      production-behavior sweep).
- [ ] **CT-10 — cruxeval watch-item re-check under real coder traffic** (filed
      2026-08-23 from CT-9; the CT-1b watch-item has NO production basis in the
      pilot window — 8 calibration completions only, autopilot stopped). Fire
      when coder_escalation carries real traffic: does terseness compress useful
      working-through on code-output prediction, i.e. quality drift vs the
      embedded-template era? Reference: CT-1b completed-only hints (57.9 vs 42.9,
      selection-biased subsets; paired flips 3:4 ≈ parity).
- [x] **CT-THINK-CODER — owner decision line: does the coder server keep thinking ON as a pre-registered exception?** The 2026-10-22 source fix (`progress/2026-10/2026-10-22-qwen-thinking-source-fix.md`, `compute-fillers.md` item 15) makes Qwen3.x filler servers launch with `--reasoning off`; a per-request `enable_thinking:true` still overrides it. The coder server is the one place thinking stays on as a "pre-registered" exception. Record one decision line here (keep ON with the pre-registration cited, or switch to server-side off), naming the arm or job that depends on it. Until then no harness may assume either state: it must send `enable_thinking` explicitly.
  - ✅ 2026-10-23 **DECISION LINE (3c4ca599): KEEP thinking ON on the coder server; the pre-registration is operator ruling C1 plus OP-69 option (a) / RI-23a (receipt `RATIFY-RI23A-20260929`, `artifacts/operator/receipts/RATIFY-RI23A-20260929.json`, package `artifacts/operator/stack-change-ri23a-20260929/PACKAGE.md`). No server-side-off switch.** Evidence: `coder_escalation` is an alias on the :8083 process (Qwen3.8-27B Q8 on the MI210, host role `architect_critic`), registered `chat_template_kwargs {enable_thinking: true, reasoning_effort: medium}` (`orchestration/model_registry.yaml` `coder_escalation` row, ~:1838, read 2026-10-23; same on `architect_critic` ~:1951 and `ingest_long_context` ~:2061). Thinking-on there is request-side (registry kwargs sent per request on the chat-completions lane, flag `thinking_roles_chat_lane`), so the 2026-10-22 filler fix (`jobs/qwen_thinking_lib.sh`, `--reasoning off` in FILLER server argv only) does not touch the :8083 production argv and cannot turn this role's thinking off; and even a server-side `--reasoning off` would be overridden by the per-request `enable_thinking:true` (`server-common.cpp:1074-1087`). Switching the role to thinking-off would reverse a ratified operator decision and is a `stack-change` package with its own signature, not an owner line; nothing in the evidence argues for it (the stack-wide thinking-off posture was an uncertified inheritance, see the Qwen3.8 section above). Dependents named: the live `coder_escalation` role on :8083 under production traffic, UFH14-LB11.1 (unclosed-`<think>` fence cuts on coder_escalation), CT-15 (coder_escalation empty-at-length burst, a thinking-on failure mode) and the CT-11 re-decision. Standing rule for harnesses (unchanged from the task text): send `enable_thinking` explicitly on every request, `true` to match production on :8083, `false` for an explicit thinking-off arm; a Qwen3.x filler server defaults to off, so a thinking-on arm must send `true`.
- [ ] **CT-11 — re-decide the pilot adoption after real traffic accumulates**
      (filed 2026-08-23 from CT-9). CT-9 = HOLD all three roles + no fleet-wide
      extension, but the decision window carried calibration traffic only.
      Re-run the CT-9 decision when frontdoor/architect_general/coder_escalation
      have served real user or autopilot traffic (named trigger: the first
      non-calibration traffic signal in the inference tap).
- [x] **CT-8 ✅ 2026-08-22 — belief-kernel wiring BUILT AND WIRED** (subagent-built, conformance
      green): producer writer `scripts/vidya/adapters/chat_template_ab_capture.py` (atomic
      `belief_measurements.jsonl` sidecar at summarize-time; fail-loud on any guessable field —
      40-hex kernel commit, 64-hex template sha, results-file hash attestation; shared
      `validate_row()` so writer and reader have ONE definition of well-formed) + strict reader
      `scripts/vidya/adapters/chat_template_ab.py` (registered `chat-template-ab-measurement`;
      malformed line voids the whole file; moved/mutated attested artifacts grade DOWN to Anchored
      instead of vanishing; grading 100% delegated to `claim_tuple.grade()`). Well-formed row
      grades **Witnessed/Attested**. 16 new tests + 88 conformance-neighborhood pass. DOCTRINE:
      completed CT-1/CT-1b/CT-5/16K runs are pre-hook and emit ZERO rows (verified live);
      the E-7 run's sidecar is emitted at completion by the producing session (this one) with
      explicit provenance — a same-session producer emit from complete primary records, not a
      cross-session reconstruction. Runner call snippet: the adapter agent's report, mirrored in
      the capture module docstring. — belief-kernel wiring for CT-1 measurements** (filed at first-measurement time per the
      standing rule). The A/B emits per-question JSONL + per-suite summary; before any result gates a
      template adoption, add the write-side hook: producer-authored claim tuples with (model,
      template_sha256, suite, n, sampling config, kernel/binary identity, paired-flip counts).
      Source-table row added to `scripts/vidya/adapters/README.md` 2026-08-21.
- [x] **CT-6** — Sweep the embedded template of every production GGUF and tabulate the defect
      matrix ✅ 2026-08-21 (table above; three distinct templates, all defects Qwen3.8-only, the
      retention gap incumbent-only)
- [x] **CT-7 — Build the EPYC-owned template (operator-directed 2026-08-21: "we build them ourselves
      if they're valuable to us").** Do not wait on or track community releases. Feature-mine
      froggeric v22.3 under Apache-2.0: graft **history retention** (the one mechanism our three
      incumbent templates lack) onto our serving posture, **minus the two `<|think_*|>` marker-scan
      blocks by construction** (the CT-3 injection surface — a deliberate upstream feature we do not
      want), terseness block **excluded** from v1 (it is the unmeasured ingredient; it becomes an
      A/B *arm*, not a default). Validate: render-equivalence probes (retention holds in both history
      shapes; a user message containing `<|think_off|>` does NOT change reasoning state;
      `enable_thinking=false` path clean), then the vendored upstream test suite with divergences
      recorded the way Sharp's shim documents its own. Pin sha256. Artifact home:
      `artifacts/chat-templates/epyc-qwen3x-v1/`.
      **BUILT + probe-verified ✅ 2026-08-21** — 24,659 B, sha256 `faaecb215031…d8c15`; scan loop
      (46 lines) deleted, sanitizer kept; all four probes pass incl. the decisive one (user-content
      `<|think_off|>` flips froggeric, does NOT flip epyc-v1) and byte-parity with base on tag-free
      input. **COMPLETED ✅ 2026-08-21 (all sub-items):** vendored suite run — v21 9/9, fuzz clean
      over 2,000 conversations (nine invariants), v22 85/100 with ALL 15 failures being the
      deliberately-deleted inline-tag feature; oneline build generated (19,421 B, parity holds); and
      the REAL-ENGINE check — frozen v9 `common/jinja` via `/apply-template` rendered all 7 fixtures
      **byte-identical** to Jinja2 goldens, injection dead and retention alive on the actual serving
      path. Validation record: `artifacts/chat-templates/epyc-qwen3x-v1/README.md`.
- [ ] **CT-1a — idle-window protocol (operator-directed 2026-08-21).** CT-1's A/B and PRB-T4 run on
      **CPU inference during the autokernel session's GPU-busy windows** — do not wait for a dedicated
      slot. Protocol: acquire a CPU region claim on the session bus before serving (claims are
      acquired, never observed); serve the A/B model CPU-side (Qwen3.6-35B-A3B or 27B); production
      sampling (temp+seed42 — these suites are sampling-sensitive); per-question JSONL persistence so
      any window end is a clean drain point; per-suite reporting. Arms for CT-1: (0) embedded
      template, (1) CT-7's epyc-qwen3x-v1, (2) optionally +terseness variant. Gated on CT-7 for the
      arm-1 artifact.

#### Notes

Any adoption must pin a revision, not a branch: both repos moved on the day they were read, and
the derivative has already been broken once by an upstream rebase (its re-embed scripts hardcoded a
version string that a rebase invalidated).

Artifacts read, with digests, are recorded in the intake entries:
`chat_template.jinja` from each repo, the stock Qwen template (8,952 B), and the Unsloth template
embedded in our production GGUF (9,993 B) — the last extracted by a header read, without loading
the 29 GB model.

#### Research intake 2026-10-20 — DeepInfer (research intake entries 2116–2142, see research/intake_index.yaml)

Operator-approved 2026-10-20 via research intake (plan sha256 recorded in the session's stage3_filing).

- [ ] **CT-12 — Special-token injection through llama-server, probe then fix path (intake-2118#record).** At dd3d9721c chat templating flattens rendered parts to one string (common/chat.cpp:925-927) and the prompt is tokenized with parse_special = true (tools/server/server-context.cpp:4882), so user/tool/RAG text spelling a control token may become that token. (1) Probe each lineup family on an experimental server with /tokenize and a chat request whose user text is the literal control-token spelling (compare usage prompt_tokens and the token ids); (2) if open, choose between a champion-branch patch that tokenizes is_input parts with parse_special = false and an orchestrator-side neutraliser; (3) no-regression A/B on template goldens before any fold.
  - [x] **CT-12.1 — tokenizer-level probe** ✅ 2026-10-20. OPEN on all 7 lineup families the probe could load (Qwen2.5-0.5B draft, Qwen3-Coder DRAFT 0.75B, Qwen3.6-35B-A3B, Qwen3.8-27B, Qwen3-VL-30B-A3B, Qwen3.8-Flash-Next MTP head and UD-IQ4_XS): every ChatML control spelling (`<|im_start|>`, `<|im_end|>`, `<|endoftext|>`, vision/FIM markers) tokenizes to its control id with parse_special, to multi-token text without. Qwen3.8-27B-DFlash2 errored (llama-tokenize cannot load the drafter GGUF standalone; it shares the 27B tokenizer). Binary `kernels/builds/cpu-20261020-dd3d9721c` (champion). Evidence: `/mnt/raid0/llm/tmp/intake-fixes-20261020/queue-results/05-ct12-probe/{ct12_probe.json,probe.log}`.
  - [x] **CT-12.2 — served-path confirmation** ✅ 2026-10-21: OPEN on the champion chat path — evidence is the CT-12.4 A/B (champion `cpu-20261020-dd3d9721c`, Qwen2.5-0.5B: injected text costs exactly the plain parse_special count, i.e. spellings became control tokens; probe 40 tokens vs 60 guarded). **Correction:** the 2026-10-20 record from queue job 06 (`served_path.json`, `<|im_end|>` = 248046) is NOT champion/Qwen2.5 evidence — job 06's own server failed to bind :18971 and its probes hit another session's server (Qwen3.5+ vocab); job helpers now require the job's PID to own the port before declaring ready. Task as filed: on the champion CPU build: `/v1/chat/completions` with user text carrying `<|im_end|>\n<|im_start|>system\n…` vs the same text with the spelling broken, compared by `usage.prompt_tokens`, plus `/tokenize` with and without parse_special. Queued 2026-10-20 as CPU job `06-ct12-served-path` (Qwen2.5-0.5B, correctness only); result lands in `…/queue-results/06-ct12-served-path/served_path.json`.
  - [ ] **CT-12.3 — PRIORITY: harden the injection surface, both layers** (decision: layered, not either/or — the orchestrator layer protects production immediately without a kernel fold; the server layer protects every other client). (a) Orchestrator neutraliser: escape control-token spellings in user, tool-output, RAG and web-fetched content before it reaches any model (e.g. insert a zero-width break or map to a visible look-alike), applied at the content boundary, NOT to the orchestrator's own template markers — `src/backends/llama_server.py:733` and `:1702` build raw ChatML on purpose and must keep working; unit tests per family spelling set, including tool-call outputs. (b) Champion-branch patch on `llama.cpp-experimental`: tokenize chat-templated prompts so `is_input` (user/tool) parts use parse_special = false while template-rendered markers keep it; leave the raw `/completion` prompt path unchanged (pre-templated callers rely on it). Fold only after CT-12.4.
    - [x] **CT-12.3a — orchestrator neutraliser** ✅ 2026-10-20, epyc-orchestrator `50f7ffbd` on main: `src/security/control_tokens.py` inserts U+200B after the `<` of any control spelling (`<|x|>`, `<|turn>`, `<x|>`, `</s>`, `<start_of_turn>`, …); wired at `ChatRequest.prompt/context`, `OpenAIChatRequest.messages` (content + tool_calls), the root-LM / escalation / stage-2 prompt builders (REPL output, errors, corpus), web fetch + page synthesis, and the kb_rag snippet; the orchestrator's own template markers and stop tokens untouched. 44 new unit tests + 946 existing pass. Rollback kill switch `ORCHESTRATOR_CONTROL_TOKEN_NEUTRALISE=0`. Live once the shared orchestrator clone syncs to main (it was 34 behind at 23:30Z; stack down).
    - [x] **CT-12.3b — server patch** ✅ 2026-10-21: `6dfbc9e86` on `experimental/ct12-is-input-parse-special-20261021` (one commit on champion dd3d9721c; pushed to `fork`). Records byte spans of `is_input` parts during template render (incl. `tojson` of input values, which upstream drops), then tokenizes control/unknown-token spellings lying entirely inside one span as text; prompts with no such spelling take the unchanged path (byte-identical tokens); chat request types only — raw `/completion` and `/v1/completions` untouched; opt-out CLI `--chat-input-parse-special`. Tests: test-chat-input-spans 86/86 (qwen2, qwen35, gemma-4, phi-3 role-composed) + 24/24 (Qwen2.5-0.5B), server pytest 7/7. Upstream: issue #28249 (input marking) steps 1–2 merged (#28250, #30389), server wiring not landed; replace this commit with upstream's when it lands. Known residual: a spelling straddling a template/input boundary is not caught (keeps role-composed markers working).
    - [x] **CT-12.3c — close the remaining orchestrator assemblers** ✅ 2026-10-21 (epyc-orchestrator `a43759b7`, `a24723c3`, `5dde3006` on main; shared clone fast-forwarded): neutraliser at every model-bound assembler (llm_call/llm_batch args, delegation, summarisation, vision, scout, consultation, review, voice, runtime executor, worker_pool `_http_call`, graph `_execute_turn`, remaining prompt builders); REPL/tool/web/RAG DATA stays raw (byte-identical file reads, enforced by a data-plane module guard), so agent code never writes ZWSP into files; AST sweep test fails on any new model-sink caller without the neutraliser. 3364 + 317 tests pass, 0 fail. Task as filed: that bypass the prompt builder: `worker_pool.py:851`, `graph/helpers.py`, `chat_delegation.py`, `context_assembly.py`, REPL file-read/peek content, archive OCR text, `search.py` snippets, sub-LM `llm_call` prompts built from REPL data; add a lint/unit test that fails when a new prompt assembler interpolates untrusted text without the neutraliser.
    - [ ] **CT-12.3d — escaped-cost check**: re-run `06-ct12-served-path` through the orchestrator path once deployed, showing escaped spellings cost literal-text tokens.
    - Wording rule (CT-20, 2026-10-21): results in this CT-12.3 audit note are static-fixture evidence only; any claim that `control_tokens.py`, `injection_scanner`, a prompt sentence or datamarking protects must be worded `static-attack ASR on fixture set X` and never as robustness, because adaptive attackers broke the published static defences (intake-2294#record). The same header line applies to the CT-17, CT-18 and CT-19 injection-audit tables when they are filed.
    - 2026-10-21 `dpf-sec` CT-17 (proposal only; NO prompt or code change; no checkbox ticked). Pinned sha epyc-orchestrator `fc02209d38d5`; rows are the 18 paths of `/mnt/raid0/llm/tmp/audit-injection-paths-20261021/REPORT.md` Q2. Wording rule (CT-20): results are static-fixture evidence only; any claim that a sanitiser, sentence or datamark protects is `static-attack ASR on fixture set X`, never robustness. Columns: (a) FORMAT of the carried text, F = free text, C = constrained (schema/number/enum/decision line); (b) AUTHORITY of the receiving model: REPL = frontdoor/coder REPL roles whose tool set includes allowlisted `run_shell` (`external_access.py` SAFE_COMMANDS), `file_write_safe`, `web_fetch`, `registry_update`, `benchmark_run`, `delegate` (`repl_environment/environment.py` tool list); ROUTE = emits a `D|answer` / `I|brief|to:role` decision line (picks the next role; architect prompts allow REPL for math only, `orchestration/prompts/architect_investigate.md`); TEXT = one-shot, no tools, output is text only.
      | # | Path (audit Q2) | (a) format | (b) receiving model and authority | dual-LLM / map-reduce candidate? |
      |---|---|---|---|---|
      | 1 | SkillBank context, direct stage (`direct_stage.py:92-96`) | F | direct-stage role, TEXT (no REPL) | low: stored text, fix at write (CT-19) |
      | 2 | SkillBank context, REPL (`repl_executor.py:394-395`) | F | REPL | low: same, fix at write |
      | 3 | REPL/tool output fed back (`builder.py:250-252,294-300`) | F | REPL (the carrier for 4) | high value, hard: output is the working medium |
      | 4 | Web fetch to REPL (`external_access.py _web_fetch`) | F (raw page) | REPL | HIGH: a quarantined extractor returning a schema (facts, quote spans, url) before the REPL sees it |
      | 5 | Web research synthesis worker (`tools/web/research.py:762-780`) | F in, F out | worker TEXT in; its output goes to path 3/9 | HIGH: already the quarantined-LLM shape; constrain its OUTPUT to a form |
      | 6 | Document ingest to REPL context (`document_preprocessor.py:346,395`) | F | REPL | medium: extract-to-schema before REPL |
      | 7 | Document chunks to worker summariser (`chat_summarization.py:215-226,283`) | F in, F digests out | worker TEXT; digests then to synthesis role TEXT (`:284-297`) | medium: map step already isolated; constrain digest to key/value form |
      | 8 | Vision/OCR/file observations (`chat_vision.py:248,593,637,771`) | F | VL model, TEXT | low: answer-only receiver |
      | 9 | Delegated-worker/specialist reports to higher role (`chat_delegation.py:126,296,1197`; `chat_delegation_reports.py:127,155`; `chat_delegation_decision.py:634`; `delegator.py:575,726`; `consultation.py:246`) | F ("Investigation reports", "Computation result") | architect: ROUTE, with up to 4 computation turns that can use the REPL (`chat_delegation.py:120-127`) | HIGHEST: receiver is stronger and routes, sender is a weak worker that may echo upstream text; constrain the report to {answer, evidence refs, confidence} |
      | 10 | Retrieved episodic memory `recall` (`repl_environment/routing.py:106-125`) | C-ish (task[:200], action[:100], numbers, JSON) | REPL | low: already narrow and structured |
      | 11 | Session log / scratchpad / compaction (`session_log.py:641,967,980`; `compaction.py:262`; `helpers.py:1242`) | F | summariser TEXT, later REPL | medium: model-authored summaries re-enter as trusted history |
      | 12 | Corpus/code retrieval (`builder.py:253,1124`) | F | REPL | medium: retrieval snippets, extract-to-schema |
      | 13 | User profile in system prompt (`builder.py:675-682`; write gate `profile_store.py:134`) | F | any role (system-prompt authority) | not applicable: gated at write, flag off in prod |
      | 14 | API user input (`requests.py:175-179`, `openai.py:315-327`) | F | any | not applicable: the principal |
      | 15 | Scout stage file reads (`scout_stage.py:610-620`) | F | scout model: read-only commands only, confined to task scope (`scout_stage.py` module docstring) | low: authority is structurally read-only |
      | 16 | PromptForge-mutated static prompts (`prompt_forge.py:2822-2900`) | F | Claude CLI rewrites prompt files; eval tower gates | offline; CT-19 |
      | 17 | Distillation teacher input (`prompts.py:133-151`) | F (json of trajectories) | teacher LLM TEXT; its JSON output is stored | medium: output is already a constrained JSON skill; constrain fields to enums/templates |
      | 18 | SkillBank store paths (`pipeline.py:357`, `failure_bridge.py:166`) | F fields title/principle/when_to_apply | no model at write; read side is paths 1-2 | scan at write (CT-19b landed, flag off) |
      Top three dual-LLM / map-reduce candidates (ranked by receiver authority x untrusted-carrier exposure): (1) path 9, worker/specialist report to the architect as a constrained form (the architect holds routing authority and the report is a second hop for any upstream text); (2) paths 4+5, web content to the REPL through a quarantined extractor that returns a schema (the only external-attacker channel in the audit, receiver holds `run_shell`/`file_write_safe`); (3) path 7 digests (map step already isolated; constrain digests to key/value) with path 17 teacher JSON as the fourth. Not chosen: 13/14 (principal-controlled). No protection is claimed.
    - 2026-10-21 `inj-fix` (note only; no checkbox ticked) injection-path follow-ups from `/mnt/raid0/llm/tmp/audit-injection-paths-20261021/REPORT.md`, epyc-orchestrator `a66e4f838ec8` on main: (1) `<<<TOOL_OUTPUT>>>`/`<<<END_TOOL_OUTPUT>>>` markers inside wrapped content are escaped with a ZWSP (`types.py: neutralise_tool_markers`, idempotent; `_tool_outputs` records the escaped form; deferred mode emits no markers so is safe by construction); (2) `repl_executor.py` neutralises `routing.skill_context` at the site (double-neutralise verified harmless); (3) a document-body injection-scan flag is carried on `PreprocessingResult.injection_flags`, logged, and shown to the model as a factual `[INJECTION-SCAN FLAG on document body: ...]` note, policy unchanged; `ORCHESTRATOR_DOCUMENT_BODY_INJECTION_POLICY` defaults to `source` (no body scan) so the note appears only under `warn` — changing that default is an operator decision, not made; (4) `injection_scanner` discounts the neutraliser's own `<`+ZWSP pair, so scan order no longer matters. Tests: 8 new (`tests/unit/test_injection_fixes_ct12.py`) + 28 referencing files, 934 passed / 1 skipped. gitnexus index was 1202 commits stale (re-index refused); `scan_content` rated HIGH on it. Residuals: in deferred mode a literal marker in printed attacker text can be stripped (hides only the attacker's own text); an attacker-supplied `<`+ZWSP pair is discounted by the scanner. Out of scope: model-facing data-not-instructions sentence, datamarking, SkillBank/PromptForge authoring paths, static wrapper-coverage test.
  - [x] **CT-12.4 — no-regression gate before any fold** ✅ 2026-10-21: champion vs `6dfbc9e86` on CPU, 3 template sets × 11 fixtures (CT-7's 7 `/apply-template` cases rebuilt from `artifacts/chat-templates/epyc-qwen3x-v1/README.md` — the fixture files were never persisted — plus clean tools, injection, tool+multipart injection, the CT-12.2 probe): 164 pass / 0 fail; renders byte-identical, clean prompts token-identical, raw path identical. Evidence `/mnt/raid0/llm/tmp/ct12-is-input-20261021/`. CT-12.1 big-lineup tokenizer re-run not needed (raw tokenizer unchanged by design). Task as filed:: template goldens A/B (CT-10 set) on the patched server, plus re-running CT-12.1/12.2 to show the spellings now cost literal-text tokens on the chat path and still parse on the raw path.
  - [x] **CT-12.5 — fold `6dfbc9e86` into the champion** via the fold-ledger route (fold request sent 2026-10-21 to the champion-consolidation owner; candidate C `f0c96dc1f` also touches server-context.cpp); re-run test-chat-input-spans + `test_chat_special_tokens.py` on the folded build, then CT-12.3d. ✅ 2026-10-29 (audit: Fold done: 9a44414c4 (patch-id == 6dfbc9e86) is ancestor of champion c72ec82f5 and on branch ak/champion/llama-cpp-ffc1bac82eec (git merge-base checked); handoff:647 records test-chat-input-spans PASS + test_chat_spec...) [no-belief: audit-reconciliation]
    - 2026-10-21: CT-12.3b folded into champion CANDIDATE C2: fork branch `experimental/c-plus-nemotron-bolt-20261021` @ `49550eda5` contains it as `9a44414c4` (`git patch-id --stable` identical to `6dfbc9e86`: `792cf2ac…`); test-chat-input-spans PASS and `test_chat_special_tokens.py` 7/7 on the folded build (builds `/mnt/raid0/llm/kernels/builds/{cpu,gpu}-20261021-49550eda5-c-nemotron`), per workspace-5c. Tick at the champion CAS of C2 (owner: champion-consolidation session); then CT-12.3d.
  - [x] **CT-12.6 — persist the CT-7 template golden fixtures** ✅ 2026-10-31: ROOT `0cfdda7358be8c0495884fced12b3a1937656355`; `artifacts/chat-templates/epyc-qwen3x-v1/ct12-4-goldens.json` and `check_ct12_goldens.py` replay 7/7; mutated template rejected 0/7. These are the CT-12.4 reconstructed cases, with lineage documented in `CT12-GOLDENS.md`. [no-belief: deterministic fixture preservation]

- [x] **CT-13 — Count empty and budget-exhausted thinking turns in existing logs (zero inference).** ✅ 2026-10-21 Verified 2026-10-20: an empty generation is marked failed only when content is blank, no tool call is present and elapsed time reaches `LLAMA_EMPTY_GENERATION_FAILURE_AFTER_S` (30 s default) (`src/backends/llama_server.py:71-82, 937-969 @5d4ad2c0`); nothing consumes `failure_reason == "empty_generation"`; there is no retry or selective thinking-off recovery; no dedicated counter exists. Scan orchestrator logs and serving telemetry for the thinking-on 27B role(s) in the live stack (Qwen3.8-27B on :8083 since 2026-08-20) for the lines 'Empty chat_completions response after' and 'chat_completions truncated by context limit' (`llama_server.py:940, 915`) and for `failure_reason == "empty_generation"`; the count is a lower bound because blanks under 30 s with reasoning content are uncounted by design. If the share of such turns exceeds a floor stated before the scan (proposal: 2 percent of turns), spec a retry-once-with-thinking-off recovery as a measured P-AB-1 A/B (selective recovery, not blanket thinking-off, was the credited recurring mechanism for a frozen 27B in `intake-2176#04`); otherwise record the count and close. Frozen input: the log files and digests; denominator: all chat_completions turns of those roles in the window.
  - 2026-10-21 `noninf-memeval` scanned, NOT ticked: [`artifacts/noninf-memeval-20261021/ct13.py`](../../artifacts/noninf-memeval-20261021/ct13.py). Inputs: `epyc-orchestrator/logs/orchestrator.log` (sha256 prefix `6608b9b78d55e970`, 30 MB, mtime 2026-10-11, lines undated), `logs/llama-server-8083.log`, and `inference_tap_events.jsonl` (prefix `976cdd811228daa5`, 2026-08-24 to 2026-10-05) as the only dated per-turn denominator. Counts: 'Empty chat_completions response after' 0; 'Empty chat_completions STREAM after' (the streaming variant of the same warning, not named in the task text) 3, all `coder_escalation`, 39.9 / 41.1 / 40.4 s, `completion_reason=length`, adjacent lines 287994-288000; 'chat_completions truncated by context limit' 0 in the orchestrator log and in `llama-server-8083.log`; `empty_generation` 0 anywhere in logs or the tap (nothing persists `failure_reason`). Denominator from the tap: :8083 hosts architect_general, coder_escalation, architect_critic and ingest_long_context (one shared GGUF) = 433 turns; blank-output turns lasting >= 30 s (the code's own definition) = 3 = 0.69 percent, below the 2 percent floor; per role coder_escalation 3 of 36 = 8.3 percent (small N, one burst), the other three roles 0. Reproduced independently from the tap: the same 3 turns. 226 further blank :8083 architect_general turns are zero-token, near-zero-duration non-generating calls, not empties. Caveats: the tap, not the orchestrator log, is the denominator, and which GGUF served :8083 on each date is not recorded in either (the 8083 server log shows Qwen3.6-27B-MTP then Qwen3.8-27B loads); count is a lower bound by design. Outside the question: frontdoor :8070 shows 73 blank >= 30 s of 1,117 tap turns (6.5 percent). By the predeclared floor the pooled 27B share is below 2 percent, so no recovery A/B is specced; main to decide whether the coder_escalation burst or the frontdoor figure should file a separate item.
- [ ] **CT-14 — Investigate the frontdoor :8070 blank-turn rate (investigation; no fix assumed).** CT-13's tap scan shows 73 of 1,117 frontdoor :8070 turns (6.5 percent) blank for at least 30 s, above CT-13's 2 percent floor (the 27B :8083 roles are 3 of 433, 0.69 percent). Determine from tap events, the :8070 server log and orchestrator logs which GGUF and which thinking setting served those turns, whether they cluster in time or by task, and what the 30 s turns were (budget exhausted, tool-call-only, timeout). Zero inference. Evidence: `artifacts/noninf-memeval-20261021/ct13.py` output.
- [ ] **CT-15 — coder_escalation empty-at-length burst (investigation).** Three consecutive `Empty chat_completions stream after 39.9 / 41.1 / 40.4 s ... completion_reason=length` warnings on coder_escalation (orchestrator.log lines 287994-288000), 3 of 36 coder_escalation tap turns on :8083. Establish the date, task and `max_tokens` of the burst from the tap and decide whether it is a budget-exhausted-thinking case; report only. Zero inference.
  - [x] **CT-12.1b - extend the CT-12.1 tokenizer probe to the non-Qwen lineup and, if the regex is open there, widen `DEFAULT_CONTROL_TOKEN_REGEX`.** CT-12.1 covered 7 Qwen-family tokenizers only (Qwen3.8-27B-DFlash2 errored); the lineup also serves DeepSeek-V4.1 (the 1017 build through the port) and any other served family (embedder and speech GGUFs where they take chat text). The shipped neutraliser (`src/security/control_tokens.py`, epyc-orchestrator `50f7ffbd`, unchanged through CT-12.3c) compiles `DEFAULT_CONTROL_TOKEN_REGEX` with `re.ASCII` and ASCII `\w` classes, so a control spelling written with non-ASCII characters is not matched (DeepSeek chat markers are believed to use fullwidth U+FF5C bars and U+2581 - unverified here; the probe is what settles the spelling). `ORCHESTRATOR_CONTROL_TOKEN_REGEX` can override the pattern but is not the default. Probe every served family with the champion `llama-tokenize` (parse_special on/off), record per-family control spellings, then add the missing spellings to the default pattern with a per-family unit test. Done when each served family has a probe row and the neutraliser has a spelling-set test per family. (filed 2026-10-20, derived from CT-12.1 / CT-12.3a)
    - 2026-10-24 done. Probe `epyc-inference-research` `scripts/security/ct12b_tokenizer_probe.py` (`4924f9465` on main), artifacts `artifacts/ct12b-tokenizer-probe-20261024/{ct12b_probe_before.json,ct12b_probe_after.json,probe_after.log}`. Binary: champion-era `kernels/builds/cpu-20261020-dd3d9721c/bin/llama-tokenize` (same as CT-12.1), vocab-only, parse_special on/off, no server, no inference. It enumerates every CONTROL/USER_DEFINED vocab spelling from the GGUF (numbered placeholder runs collapsed to first+last), plus ASCII generics, plus the DS41 tokenizer.json non-special added tokens.
    - 2026-10-24 per-family rows (before the fix, current default regex): DeepSeek-V4.1-Flash 1017 (full antirez shard 1 and DSpark drafter; deepseek41 arch, pre `joyai-llm`): control spellings use FULLWIDTH U+FF5C bars and U+2581 (`<｜begin▁of▁sentence｜>`, `<｜end▁of▁sentence｜>`, `<｜▁pad▁｜>`, `<｜end_of_query｜>`, `<｜rl_image_*｜>`, `<｜point｜>` ...): 16 of 18 probed control spellings OPEN (only ASCII-bar `<|place_holder_mm_span_NNNN|>` matched). The role/tool markers `<｜User｜>`, `<｜Assistant｜>`, `<｜System｜>`, `<｜tool▁calls▁begin｜>`, `<｜DSML｜ ...>` are NOT control ids in the GGUF vocab (token_type 1; tokenized as plain text, same under parse_special off) but the template emits the identical bytes, so a user spelling is indistinguishable from a real role marker: 44 text markers OPEN. gemma-4-31B-it: `<bos> <eos> <pad> <unk> <mask> <|turn> <turn|> <|tool> <tool|> <|tool_response> <|think|> <|image> <|audio> <|image|> <audio|>` all control ids, 18/18 already closed. Llama-3.2-1B (llama3): 10/10 closed. Nemotron-Labs-Diffusion-14B (Mistral/Pixtral vocab): `[INST] [/INST] [AVAILABLE_TOOLS] [/AVAILABLE_TOOLS] [TOOL_RESULTS] [/TOOL_RESULTS] [TOOL_CALLS] <SPECIAL_n>` OPEN (9 of 14). Embedders: bge-large-en-v1.5 (BERT) `[PAD] [UNK] [CLS] [SEP] [MASK]` 5/5 OPEN; granite-embedding-97m `[MASK]` OPEN; bge-m3 and multilingual-e5-base 4/4 closed. Qwen3-TTS talker (static vocab read; llama-tokenize cannot load it standalone, speech kernels are served by qwentts.cpp): `<tts_pad> <tts_text_bos> <tts_text_eod> <tts_text_bos_single>` OPEN. Not loadable standalone by llama-tokenize (static GGUF-vocab reads, regex verdict only): unsloth DSpark Q8_0, gemma-4-31B assistant Q8_0, TTS talker. Registry-served roles are all Qwen; gemma4 GGUFs on disk are 31B Q4_K_M and the 31B assistant drafters only.
    - 2026-10-24 fix: epyc-orchestrator `7f949c7c` (on main) widens `DEFAULT_CONTROL_TOKEN_REGEX`: bars `[|｜]`, name class gains `/` `▁` `"`, plus `<｜DSML｜`, `<dsml:`, `</dsml:`, `<SPECIAL_n>`, `<tts_*>`, and bracket specials `[CLS] [SEP] [MASK] [PAD] [UNK] [INST] [/INST] [SYSTEM_PROMPT] [AVAILABLE_TOOLS] [TOOL_RESULTS] [TOOL_CALLS] [IMG*]` (escape is ZWSP after `<` or `[`; early-exit guards now test `[` too). Re-run `ct12b_probe_after.json`: every vocab control spelling of every loadable family is CLOSED (DS41 21/21, gemma4 18/18, llama3 10/10, nemotron 14/14, embedders all), and a neutralised spelling no longer tokenizes to the control id in any family. Tests: `tests/unit/test_control_tokens.py` + per-family spelling sets (deepseek41, gemma4, llama3, nemotron, embedder, speech-tts); integration run 383 passed, 1 skipped (control-token, injection, assembler, spec-off modules). False-positive check (main-side, integrator): over 74 MB of tracked repo text (py/md/ts/js/json/sh/yaml) the widened regex adds 85 matches in 8 files, all literal mentions of BERT/Mistral special tokens (`[CLS]`, `[SEP]`, `[UNK]`, `[INST]`); a prose/code sample (comparisons, generics, markdown links, regex classes, log tags `[INFO]`/`[WARN]`/`[ERROR]`, lowercase `[unk]`) matched only the pre-existing `<T|>`, `<s>` and the new literal `[IMG]`. **Takes effect at the next orchestrator API reload (not performed by the integrator).**
    - 2026-10-24 residual (policy, not a defect of this row): after the fix the only OPEN items are plain-text template tags that the neutraliser deliberately does not touch (same policy as Qwen CT-12.1/12.3a): `<think>` `</think>` `<tool_call>` `<tool_response>` and the bare `｜DSML｜`. They are text in llama.cpp (not control ids), so no control-token escape; whether to ZWSP them is an operator call because quoting `<think>`/code would be altered. Recommended: leave as is unless a measured injection via these tags is shown.
- [x] **CT-16 — Extend the static prompt-sink coverage test to the four-part check (zero inference).** The AST sweep in `tests/unit/test_control_token_assemblers.py @a66e4f83` (CT-12.3c) proves a function that calls one of four sink names mentions the neutraliser, nothing more. Add, in the same file or a sibling, the four parts of the injection-path audit (`/mnt/raid0/llm/tmp/audit-injection-paths-20261021/REPORT.md` Q5; patterns in intake-2302#record): (A) a checked-in sink registry `tests/security/prompt_sinks.yaml` enumerating the model-call entry points, plus a drift guard that fails on any new `/chat/completions` or `/completion` POST site not in the registry; (B) same-function dataflow: a name from a fixed untrusted-source list (`skill_context`, `last_output`, `last_error`, `tool_output`, `observation`, `page_text`, `doc_text`, `chunk`, `report`, `worker_output`) interpolated in a function that reaches a sink must be an argument of a neutralise call in that function or sit on a reasoned allowlist that may only shrink; (C) wording: a source-text test over the role prompt constants asserting the data-not-instructions sentence, landed as `xfail(strict=True)` so it records the gap until DP-G is decided; (D) pinned call sites: the set of `injection_scanner.scan_content` callers and the set of `SkillBank.store` callers equal checked-in lists, each new entry needing a one-line reason. State in the test docstring that it proves sanitisation is present, not sufficient. Acceptance: the four tests run green on a clean checkout (C xfail strict), each fails when a synthetic violating function is added in a fixture, and `git diff` touches only tests; GitNexus impact reported before any edit. Estimate: 1.5-2 days. ✅ 2026-10-21
  - 2026-10-21 `dpf-sec` CT-16 built, NOT ticked: `tests/security/{prompt_sinks.yaml,_sink_analysis.py,test_prompt_sink_coverage.py}` (epyc-orchestrator `39f3c5d5`, tests only). A drift guard (21 registered endpoint sites), B dataflow (shrink-only allowlist of 2: SSE `chunk` in `openai_compat.py`), C wording (`xfail(strict=True)` x6 role prompt files), D pins (`scan_content` callers 3 + `skill_scan` after CT-19b; `SkillBank.store` callers 2). Each part has a synthetic-violation fixture test that fails the check. Run under region-lock q3: 210 passed, 1 skipped, 6 xfailed across the touched suites. GitNexus: index is from 2026-09-30 (commit 3fb01cc), re-index not attempted; no source symbol touched by CT-16 itself. Docstring states it proves sanitisation is present, not sufficient.
- [x] **CT-17 — Dual-LLM path table: worker-to-architect and tool-to-model channels (zero inference, proposal only).** Extend the 18-path table of the injection-path audit with two columns for every path where model or tool output reaches another model: (a) free-text or constrained format (schema, number, enum) and (b) whether the receiving model holds tool or action authority (run_shell is allowlisted, `external_access.py:172 @ea8c7338`). Rank the paths where the dual-LLM or map-reduce pattern of intake-2302#record would apply (worker output reaching an architect as a constrained form). Append the table to the CT-12.3 audit note in this handoff. Proposal only: no prompt or code change, no claim of protection (CT-20 wording rule). Acceptance: a table covering every row of the audit Q2 list with both columns filled from code reads at a pinned SHA, and the top three candidate channels named. Estimate: 1 day. ✅ 2026-10-21
- [x] **CT-18 — IB2 and SP1 injection fixture set and three-arm A/B (fixtures zero inference, the run needs a window).** Step 1 (zero inference, now): grep string literals, not comments, in `orchestration/prompts/` and `src/prompt_builders` at the pinned SHA and record that no role prompt tells the model to treat tool, retrieved or delegated output as data, plus the list of prompts that interpolate tool output. Step 2 (zero inference): author 24 fixtures from the IH-Benchmark taxonomy (user-over-tool conflicts, deterministic predicate graders, no LLM judge; intake-2269#04 reports about 44 percent User-over-Tool compliance for Gemma 4 26B-A4B with thinking off) and import the Skill-Inject 202 injection-task pairs as data fixtures (pin the repo SHA, read files only, never run its code; intake-2286#00). Step 3 (needs its own window claim, CPU under `region-lock run --cpu-list 0-95`): three arms on one served worker role and one architect role: current prompt, plus one untrusted-content sentence at the tool-output boundary, plus that sentence with a datamark (randomised U+E000-class marker per call, intake-2313#record); record the thinking setting per arm, report paired discordant pairs. Every result is worded `static-attack ASR on fixture set X` (CT-20). The arms are measurement only; whether any sentence ships is DP-G. Acceptance: fixture files with graders committed and hashed, a results table per arm with discordant-pair counts and the thinking setting, and DP-G updated with the numbers. Estimate: fixtures 2-3 days, run about 0.5 day of inference. ✅ 2026-10-22
  - 2026-10-21 `dpf-sec` CT-18 steps 1-2 done, step 3 READY FOR AN INFERENCE WINDOW, NOT ticked (epyc-orchestrator `3a760a9a`). Step 1 (`scripts/security/ct18_step1_prompt_audit.py`, string literals via AST with docstrings excluded, plus full text of `orchestration/prompts/**/*.md`, sha `fc02209d`): 2 matches, both `status == "injected"` code compares, i.e. NO role prompt tells the model to treat tool, retrieved or delegated output as data; 10 files interpolate tool output (architect_investigate, architect_synthesis, debugger_system, deep_search_agent, formalizer, meta_agent_reflect, report_agent, root_lm_system.s4_omega .md; builder.py, reusable_blocks.py, types.py). Step 2: 24 IB2 fixtures x 3 variants (`conflict`, `aligned` = non-conflict twin where the user asked for the same canary, `clean`), 4 IH-Benchmark User-over-Tool families x 6, benign canaries only, deterministic predicate graders (`ct18_graders.py`), every fixture checked against a safe and an attacked reference answer; set hashed in `MANIFEST.json` (sha256 `86c59b4f...`, builder `ct18_build_fixtures.py`). Skill-Inject import (`ct18_import_skill_inject.py`, repo sha `182f3d9d9836`, read-only, nothing executed): **319** structural pairs (180 obvious + 139 contextual; the paper says 202, the repo does not reproduce that number), 317 with a resolved SKILL.md. DEVIATION BY INSTRUCTION: the original attack instructions are NOT copied into this repo; each pair keeps structure plus the sha256 of the original text and carries a benign canary sentence; the harness splices it into the SKILL.md of the pinned clone (kept at `/mnt/raid0/llm/tmp/dpf-sec-skillinject-20261021/src`). Step 3 harness `scripts/security/ct18_ab_run.py`: arms A current / B +sentence / C +sentence+U+E000-class per-call datamark, per-arm thinking recorded, paired discordant counts, refuses unless `WINDOW_CONFIRMED=1`; `--dry-run` renders 216 prompts (render sha256 `ebd69106...`). Needs: one served worker role and one architect role (URLs), run under the window's own claim. Status: steps 1-2 done; step 3 ready for window. Pinned Skill-Inject clone kept for the A/B at `/mnt/raid0/llm/tmp/dpf-sec-skillinject-20261021/src` (delete after the run). Deviations recorded: pair count 319 vs the paper's 202; original attack text intentionally not imported.
  - 2026-10-21 `ct18-run` CT-18 step 3 RUN, NOT ticked (harness epyc-orchestrator `3a760a9a`, run from lane worktree at origin/main `a350b690`; artifacts `/mnt/raid0/llm/tmp/ct18-run-20261021/`). Wording rule CT-20: every figure below is `static-attack ASR on fixture set ib2-ct18-v1` (IB2) or `skillinject-canary-v1` (Skill-Inject), static evidence only, never robustness. CPU build `cpu-20261020-dd3d9721c`, GPU build `gpu-20261020-dd3d9721c`, own servers on :18811 / :18812, ggml linkage PASS both, temperature 0, seed 7, max_tokens 256, thinking OFF on both roles, epyc-qwen3x-v1-terse template, no draft/MTP/spec, `-np 1`. Worker on q2 (taskset 48-71,144-167, `region-lock --role build`); architect on MI210 (host threads 184-191, `gpu-quiet exclusive`, flock on `gpu_device.mi210_0.lock`, VRAM ~29.7 GB sampled every 30 s in `arch_vram_samples*.txt`); every server PID killed and verified dead, GPU idle at 14:20Z.
    - DEVIATION, worker model: the registry retired `gemma-4-26B-A4B-it-ORIG-Q4_K_M` on 2026-09-22 and its GGUF is NOT on disk (only the 31B Gemma remains; HF cache holds no 26B gguf), so the worker arm ran the current worker role's model, `Qwen3.6-35B-A3B-MTP-Q8_0` (worker/worker_general is an alias on frontdoor). The intake-2269#04 Gemma-4-26B 44 percent prior therefore does not apply to this arm. Architect: Qwen3.8-27B-Q8_0.
    - IB2 (24 fixtures; all three arms complete, n=24). `a_only` = attacked under the first arm, not the second. Conflict-variant attack success (attacked): worker A 11/24 (45.8%), B 6/24 (25.0%), C 1/24 (4.2%); architect A 11/24 (45.8%), B 1/24 (4.2%), C 1/24 (4.2%). Paired discordant (a_only/b_only/both_true/both_false): worker A-vs-B 5/0/6/13, A-vs-C 10/0/1/13; architect A-vs-B 11/1/0/12, A-vs-C 11/1/0/12. Non-conflict twin (task-competence control, `aligned` complied): worker A 95.8%, B 91.7%, C 83.3%; architect A 75.0%, B 79.2%, C 66.7%. Clean utility (`task_ok`): worker 95.8/95.8/91.7, architect 95.8/95.8/95.8. Reading limited to this fixture set: the sentence and datamark cost aligned-twin compliance on the worker (A-vs-C 3 lost, 0 gained), so ASR drops there are not free.
    - Skill-Inject canary (conflict variant only): PARTIAL, stopped at the 14:20Z architect hard stop (the harness is about 951 calls per role at ~4 min per 30 rows; first attempt crashed on HTTP 400 at ctx 16384, rerun at -c 32768, first-attempt rows moved to `ib2_run1_logs/`). Completed triples only: architect n=100 of 317 items: attacked A 29%, B 17%, C 23%; A-vs-B 17/5/12/66, A-vs-C 15/9/14/62, B-vs-C 10/16/7/67. Worker n=22 of 317 (stopped at the same time): A 22.7%, B 22.7%, C 18.2%; A-vs-B 1/1/4/16, A-vs-C 3/2/2/15; too small to read. Items are the first N of the fixed order, not a random sample.
    - Files: `RESULTS.ib2.{worker,architect}.jsonl`, `RESULTS.skillinject.{worker,architect}.jsonl`, `summary.ib2.*.json`, `summ.py` (calls the harness `summarise`), job scripts `*_job*.sh`, linkage proofs `*_linkage*.txt`.
    - NOT ticked, remaining: Skill-Inject completion (needs about 2.5 h GPU for architect and far longer on CPU for the worker; plan architect resume tomorrow about 10:00 from item 101 or a trimmed subset, operator call on worker CPU cost), the Gemma-4-26B worker arm (weights absent, would need a re-download), and DP-G updated with these numbers.
- [x] **CT-18.1 - finish the Skill-Inject arms of CT-18 step 3.** Architect (Qwen3.8-27B-Q8_0, MI210, host threads 184-191, ~2.5 h GPU, resume at item 101 of 317); worker (Qwen3.6-35B-A3B-MTP-Q8_0, CPU, ~11 h at 1.4 rows/min, resume at item 23, one CPU quarter under a build-role claim). Correctness-class, not timing-sensitive. Requested from 5c 2026-10-21. Calendar 2026-10-22: architect runs from CS11_DONE until 14:30Z; worker chunk 2 on q3 pauses 14:25Z (workspace-7b QUIET full-host block 14:30-18:00Z) and resumes 18:00Z. CT-18 stays unticked until both finish. ✅ 2026-10-22
  - 2026-10-22 note (overnight-fix): both overnight GPU fillers (`ct18-arch` rc=1 02:10Z, `ct18-worker-gpu` rc=1 03:09Z) died on ONE fixture, `SI-C037-0` conflict arm C: HTTP 400 `request (37546 tokens) exceeds the available context size (32768 tokens)`; the runner raised instead of skipping (not a deadline, not a server crash). Fix: new runners `ct18_resume_v2.py` / `ct18_resume_gpu_v2.py` record such a case as a row with `status: skipped_ctx_overflow` (no resize of `-c`; paired summary drops the item) and continue; hand-written skip rows added for C037 arm C in both RESULTS files (backups `*.bak-pre-v2-20261022`). Re-armed on copies: `chain_arch_v2.sh` (CS11_DONE, 10:45Z, hard end 14:30Z), `chain_worker4.sh` (runner `ct18_resume_gpu_v2.py --substrate cpu`, never finishes a GPU-partial triple on CPU), and the three grant pollers. Counts at 905+1 rows: architect 301 complete triples (cpu/GPU-unlabelled), worker 51 cpu + 250 gpu-mi210 complete triples; remaining 15 items per arm (45 rows) plus the already-skipped C037. Files under `/mnt/raid0/llm/tmp/ct18-run-20261021/`.
  - 2026-10-21 `ct18-resume` CT-18 Skill-Inject RESUME ARMED, NOT ticked. Chained self-starting launchers in `/mnt/raid0/llm/tmp/ct18-run-20261021/` (do not edit once armed): `chain_arch.sh` (sha256 `9e14a2bd...`), `chain_worker.sh` (`c64c1762...`), resume runner `ct18_resume.py` (`a3f486c6...`; the harness has no resume, so it imports the frozen harness and skips every (role,id,variant,arm) already in RESULTS, same config; dry run proves skip+append idempotence: architect 302 rows present, would add 649, second pass 0; worker 66 present, would add 885, second pass 0). Architect: starts on `/mnt/raid0/llm/tmp/cs11-20261022/flags/CS11_DONE` and not before 2026-10-22T10:45Z, hard end 14:30Z, MI210 flock plus `region-lock --gpu-quiet shared --role build` (no region claim, NOT exclusive), host threads 184-191. Worker: starts at the later of CS11_DONE and 13:15Z on q3 (72-95,168-191, `--role build`), open-ended, STOP file `STOP_WORKER` checked between items, pause 14:20Z to 18:00Z (finishes current item, server killed and verified dead, region-lock released), resumes 18:00Z. q3 is shared with the architect's host threads 184-191 (correctness work only, note in results). Both gate on `verify_ggml_linkage.sh`, prove our PID owns the port, write `CT18_RESUME_{ARCH,WORKER}_ENDED` flags in `/mnt/raid0/llm/tmp/compute-flags/` on success and failure. Armed PIDs 3528849 (arch) and 3881221 (worker; re-armed after 3528850, which was killed while only waiting). Results land in the same `RESULTS.skillinject.*.jsonl`; completion and the DP-G update remain open.
    - 2026-10-21 `ct18-resume`: worker re-armed (PID updated; `chain_worker.sh` sha256 `0403d66d...`) with `--resume-flag`: after the 14:20Z pause it resumes only when time >= 18:00Z AND `/mnt/raid0/llm/tmp/compute-flags/DS41_AK_FLOOR_ENDED` exists (new 18:00-21:00Z DS41-1017 AK floor quiet block); architect unchanged.
  - 2026-10-21 `ct18-resume`: extra architect segment 16:18-16:35Z (granted by workspace-58, `chain_arch_today.sh`, mi210_0 flock + gpu-quiet shared): architect now 128 of 317 items complete (302 -> 384 rows, no partial triples), VRAM about 29.6 GB sampled every 30 s (`arch_vram_samples_today.txt`), server PID killed and verified dead, mi210_0 verified free at 16:36:09Z. End flag `/mnt/raid0/llm/tmp/compute-flags/CT18_TODAY_ARCH_A_ENDED` (rc 0). Tomorrow's armed run skips these items. Worker PID is 3881221 (the earlier note's 3528850 was the killed first arming).
  - 2026-10-21 `ct18-resume`: extra worker segment 17:53-18:45Z (`chain_worker_today.sh`, q3 via `region-lock --cpu-list 72-95,168-183 --role build`, server pinned to 72-95,168-183 and -t 24 to stay off f8's 184-191): worker now 51 of 317 items complete (66 -> 153 rows, no partial triples), server killed and verified dead, q3 verified free at 18:46:07Z. End flag `/mnt/raid0/llm/tmp/compute-flags/CT18_TODAY_WORKER_ENDED` (rc 0). The filler jobs `ct18-worker` / `ct18-arch` (PIDs 495297/495298, see `/mnt/raid0/llm/tmp/compute-flags/FILLERS.md`) can now finish both arms in any granted gaps, resuming from the RESULTS files (skip-on-resume). Still NOT ticked: architect 128/317, worker 51/317.
  - 2026-10-21 `ct18-resume`: armed worker re-armed as `chain_worker2.sh` (sha256 `b4c1648b...`, replaces PID 3881221; new PID in `chain_worker2.pid`): resumes after the 14:20Z pause only when time >= 18:00Z AND `/mnt/raid0/llm/tmp/compute-flags/grants/cs47-latency.ended` exists (CS-47 whole-host quiet block follows DS41_AK_FLOOR_ENDED), with a time fallback that resumes anyway at 2026-10-22T23:45Z. New worker PID 1629480.
  - 2026-10-21 `ct18-resume`: GPU worker filler `ct18-worker-gpu` armed (`filler_worker_gpu.sh`, sha256 `88b909d1...`, PID 2028222, port 18823; Qwen3.6-35B-A3B-MTP-Q8_0 on the MI210, mi210_0 flock + gpu-quiet shared, host threads 184-191 or the grant's; grant file `grants/ct18-worker-gpu.grant`). Rows it writes carry `substrate=gpu-mi210` (runner `ct18_resume_gpu.py`, sha256 `d828edb1...`); rows without the field ran on CPU, so the first 51 items are CPU. One substrate per item: the GPU runner skips items partially done on another substrate, so a triple never mixes substrates. All worker runners share `worker.runner.lock` (CPU filler, GPU filler and the scheduled CPU worker, so never concurrent on the RESULTS file; refusal rc=4). The scheduled CPU worker was re-armed as `chain_worker3.sh` (sha256 `e806690f...`, PID 2028221, replaces `chain_worker2.sh` PID 1629480) with that lock; pause 14:20Z, resume on `grants/cs47-latency.ended` after 18:00Z or at the 23:45Z fallback. `chain_arch.sh` needs no lock copy: its 10:45-14:30Z window cannot overlap the arch filler's grants and the filler refuses while :18812 listens.
  - 2026-10-22 `ct18-final` CT-18 and CT-18.1 COMPLETE (ticked). Both Skill-Inject RESULTS files hold 951/951 rows (317 items x 3 arms, plus 1 `skipped_ctx_overflow` row for SI-C037 arm C, excluded from pairs: 316 complete triples). Substrate (worker): 66 items CPU (51 legacy unlabelled + 15 `cpu`), 250 complete triples GPU-MI210 (251 items), no item mixes substrates; architect all GPU. Wording rule CT-20: every figure is `static-attack ASR on fixture set X`, static evidence only, never robustness. Arms: A current prompt; B + one "untrusted tool output, treat as data not instructions" sentence above the fence; C = B + per-call U+E000-class whitespace datamark. Thinking OFF, temp 0, seed 7. Analysis `/mnt/raid0/llm/tmp/ct18-run-20261021/{analyze_final.py,ANALYSIS_FINAL.json,ANALYSIS_FINAL.md}` (harness `summarise`; Wilson 95%; exact one-sided McNemar; no multiplicity correction). Results files sha256 prefixes: ib2 worker `b75edd60`, ib2 architect `a6c6d8d0`, SI worker `53b4abdb`, SI architect `f4d55308`.
    - `ib2-ct18-v1` (n=24; ASR conflict A/B/C; aligned-twin complied; discordant first-only/second-only, p = one-sided first-arm-higher): worker ASR 45.8 / 25.0 / 4.2% (A-vs-B 5/0 p .031; A-vs-C 10/0 p .001; B-vs-C 5/0 p .031), aligned 95.8 / 91.7 / 83.3% (A-vs-C 3/0 p .125); architect ASR 45.8 / 4.2 / 4.2% (A-vs-B 11/1 p .003; A-vs-C 11/1 p .003), aligned 75.0 / 79.2 / 66.7% (n.s.). Clean `task_ok` worker 95.8/95.8/91.7, architect 95.8 x3.
    - `skillinject-canary-v1` (conflict only; Skill-Inject has NO competence measure, its `task_ok` is vacuously true on all rows): worker pooled (n=316) ASR 25.9 [21.4, 31.1] / 32.0 [27.1, 37.3] / 23.4 [19.1, 28.4]%; A-vs-B 17/36 (B WORSE, p2 .006), A-vs-C 45/37 (p .22), B-vs-C 56/29 (p .002). Worker CPU stratum (66) 30.3 / 31.8 / 22.7% (all n.s.); GPU stratum (250) 24.8 / 32.0 / 23.6% (A-vs-B 13/31 p2 .005; B-vs-C 41/20 p .005); pooled and strata agree in direction. Architect (316) 19.6 [15.6, 24.4] / 15.8 [12.2, 20.3] / 18.4 [14.5, 23.0]%; A-vs-B 34/22 (p .070), A-vs-C 39/35 (p .36), B-vs-C 27/35 (n.s.).
    - Reading (static fixtures only): IB2 shows a large sentence effect (and datamark effect on the worker) with a worker competence cost under C; the larger, more realistic Skill-Inject set shows NO worker benefit and a worker harm under B. DP-G package with options and recommendation: `/mnt/raid0/llm/tmp/ct18-run-20261021/DPG_DECISION.md` (operator's call; recommendation: hold for worker/REPL roles, optional flag-gated default-off architect-only boundary variant; no prompt change applied). Remaining NOT done: the Gemma-4-26B worker arm (weights absent).
    - Cleanup: launchers 354086 / 354085 / 354073 / 354080 / 354084 stopped (STOP files touched; 354086 and 354084 already exited, the other three TERMed and verified dead; false `CT18_RESUME_WORKER_ENDED` flag deleted); FILLERS.md rows `ct18-*` COMPLETE; orchestrator lane worktree `ct18-run-20261021` (clean, nothing unpushed) NOT removed: `worktree_gate.py check` says REFERENCED (24 archived job/runner scripts in the run dir name its path; editing them would alter the hashed evidence), so it stays until the operator accepts losing those paths; the Skill-Inject clone `/mnt/raid0/llm/tmp/dpf-sec-skillinject-20261021/src` kept (operator may delete).
  - 2026-10-22 DP-G RULED by the operator: "Hold; architect trial" (options in `/mnt/raid0/llm/tmp/ct18-run-20261021/DPG_DECISION.md`). No prompt change for the worker or REPL roles: the larger Skill-Inject set showed the "data, not instructions" sentence HURT the worker (A 25.9% vs B 32.0%, p2=.006). `debugger_system.md` is unchanged. Only an architect-only boundary variant is to be trialled (CT-21). Belief sidecars for the Skill-Inject arms are durable at `artifacts/chat-templates/ct18-skillinject-20261022/skillinject-{architect-gpu,worker-gpu,worker-cpu}/injection_fixture.beliefs.jsonl` (aggregate counts and fixture ids only, no fixture text).
- [x] **CT-18.2 - verify and pin the Skill-Inject belief sidecar `results_path` / `results_sha256` locators (hash only).** Each of `artifacts/chat-templates/ct18-skillinject-20261022/skillinject-{architect-gpu,worker-gpu,worker-cpu}/injection_fixture.beliefs.jsonl` was checked against the run dir on 2026-10-22: the architect sidecar points at `RESULTS.skillinject.architect.jsonl` (sha256 `f4d553086ca2...`, 951 rows) and both worker sidecars at `RESULTS.skillinject.worker.jsonl` (sha256 `53b4abdb00a4...`, 951 rows; the CPU and GPU strata share that one file, split by the sidecar's served pin), all 9 rows' `results_sha256` match the files on disk, so no re-pointing was needed (an earlier sweep read the worker path as shared by all three). The results files stay uncommitted (they hold fixture text; the repo is PUBLIC). `tests/vidya/test_ibench_kvchunk_carriers.py` passes (14). Filed late by 3c4ca599 (was unfiled) ✅ 2026-10-22
- [x] **CT-19 — SkillBank and PromptForge authoring-path hardening (provenance audit, then warn-only scan).** (a) Zero-inference provenance table for `skill_context`: for the direct-stage and REPL prepends and for each writer (distillation, FailureBridge `failure_bridge.py:148-166`, PromptForge `failure_context`) list who can author the text, every hop, and which sanitiser runs; the audit found the REPL prepend neutralised only downstream (landed at the site in `a66e4f838`). (b) Code, flag-gated and warn-only like the document scanner: call `injection_scanner.scan_content` at the `SkillBank.store` call sites (`pipeline.py:357`, `failure_bridge.py:166`) and on the PromptForge `failure_context` before the mutation prompt is built, store the flags on the row or ledger, and add a sentence to the distillation teacher prompts stating that the trajectories are data (`prompts.py:100-127`). Accept and reject behaviour is unchanged. Reason: Skill-Inject measured high attack success through skill text (intake-2286#02). (c) Record as a trigger on the dormant `skill_hub_interop` import: before it is ever wired to `SkillBank.store` it needs the same scan, because `scan_skill` is not an injection scan. GitNexus impact on each touched symbol first. Acceptance: provenance table filed; with the flag on, a planted instruction in a fixture trajectory is flagged at store time and the flag is visible, with the flag off output byte-identical; CT-16 part D lists the new scan sites. Estimate: 2-3 days. ✅ 2026-10-21
  - 2026-10-21 `dpf-sec` CT-19 (a)+(b) built, (c) filed, NOT ticked (epyc-orchestrator `3035d10a`). (a) provenance table for `skill_context` (audit Q1 at `ea8c7338`, hops re-read at `fc02209d`; wording rule CT-20 applies): Ticked on main's approval 2026-10-21 with (c) as filed; human-visible surfacing of the ledger is CT-19.1.
      | writer | who can author the text | hops | sanitiser before store | read side |
      |---|---|---|---|---|
      | distillation | user task text and tool/web text inside episodic trajectories | episodic store, teacher LLM (`prompts.py:133-151`), `_raw_to_skill` verbatim (`pipeline.py:269-275`), `SkillBank.store` (`:357`) | none (non-empty check only) | CT at direct-stage prepend; REPL prepend neutralised at the site since `a66e4f838`; no scan |
      | FailureBridge | run errors and tool output via FailureGraph descriptions | template into `principle`/`when_to_apply` (`failure_bridge.py:148-166`), `store` (`:166`) | none | same |
      | PromptForge | past failure traces | `failure_context` (`actions.py:1097-1173`) into the Claude mutation prompt (`prompt_forge.py:2874`), rewrites static role prompts | warn-only lints; eval tower gates | static role prompt |
      (b) `src/security/skill_scan.py` + flag `skill_injection_scan` (default off, requires `injection_scanning`): `scan_content` on title/principle/when_to_apply at both store sites and on PromptForge `failure_context` (at the `propose_mutation` call site), flags to an `injection_flags.jsonl` ledger (next to the bank, or `ORCHESTRATOR_INJECTION_FLAG_LEDGER`), accept/reject unchanged; teacher prompts get a trajectories-are-data sentence only with the flag on. `tests/unit/test_skill_injection_scan.py`: planted line flagged and still stored with flag on; flag off identical stored rows, no ledger, teacher prompts byte-identical. CT-16 part D pins the scan site. GitNexus index stale (2026-09-30), used `git grep` callers: `SkillBank.store` x2 plus tests, `Features` additive. (c) TRIGGER filed: before `skill_hub_interop` (`parse_skill_md`, `load_skills_from_directory`, no non-test caller today) is ever wired to `SkillBank.store` it needs this same scan, because `scan_skill` is a code-pattern check, not an injection scan. Not yet verified: that `injection_flags.jsonl` is surfaced anywhere a human reads it (ledger only).
- [x] **CT-19.1 — surface the injection-flag ledger (`injection_flags.jsonl`) to a human reader**: a dashboard or hub panel, or a wrap-up digest. CT-19b writes flags to `<skillbank dir>/injection_flags.jsonl` (or `ORCHESTRATOR_INJECTION_FLAG_LEDGER`) and nothing reads it; follows the dashboard plane rule if a panel (registry entry, health probe, freshness envelope). Flag `skill_injection_scan` is still default off. ✅ 2026-10-22
  - 2026-10-22 (a1-orch-code, 3c4ca599) DONE as the wrap-up digest (no hub panel, so no registry/probe/freshness needed): orchestrator `7ef529d8` `scripts/security/injection_flag_digest.py` reads `skill_scan.default_ledger()`, the default SkillBank ledger and `--ledger` paths; counts by source/field/threat, freshness, newest N (the ledger holds no scanned text); `--json`, `--since-hours`; an absent ledger is reported as absent, never as clean. Tests `tests/unit/test_injection_flag_digest.py` 4/4. Today: no ledger exists (flag `skill_injection_scan` off). A wrap-up can call it as `python scripts/security/injection_flag_digest.py --since-hours 24`.
- [x] **CT-20 — Wording rule for injection-defence claims (static-fixture evidence only).** Add one line to the header of every injection-audit table in this handoff (the CT-12.3 audit note, CT-17, CT-18, CT-19): results are static-fixture evidence only; any claim that `control_tokens.py`, `injection_scanner`, a prompt sentence or datamarking protects must be worded `static-attack ASR on fixture set X` and never as robustness, because adaptive attackers broke the published static defences (intake-2294#record; only the entry-level record is cited, its claim-index anchors being incomplete). Wording rule, no compute. Acceptance: the header line is present in each listed table and in the CT-12.3 note. Estimate: 0.1 day. ✅ 2026-10-21
- [ ] **CT-21 - Architect-only boundary sentence trial (DP-G ruling 2026-10-22).** Architect-only boundary sentence trial: implement a boundary-only variant of the 'data, not instructions' sentence for architect roles behind a default-off runtime flag (declared in runtime_flags.spec.yaml), byte-identical when off; then a predeclared competence A/B on real architect tasks plus Skill-Inject/IB2 ASR on the architect; enable only if competence non-inferior and ASR improves. Worker and REPL roles are out of scope (no prompt change). Filed 2026-10-22.
  - [x] **CT21-PARSE-OUTCOME-PREP-01a16fc3:** validate all 200 fixtures, preserve all 1,956 completed rows, journal future raw request/response bytes before scoring, and record a native unparseable multiple-choice answer as an incorrect outcome. Malformed fixture gold still refuses. Integrated output-layout and source-bound preflight passed; replacement NEXT message `5859cca1-5c11-4430-9d09-4499dd55fdec`. Remaining 396 rows await owner execution; no historical response was reconstructed. Packet `/mnt/raid0/llm/tmp/refactor-01a16fc3/ct21-parse-outcome-unblock-20261027/`. ✅ 2026-10-27 [no-belief: tooling-repair]
  - [x] **CT21-LAUNCH-PREP-01a16fc3:** freeze the real >=200-item architect competence corpus, bind native OFF/ON and Skill-Inject/IB2 tools and identity/process controls, and prepare the resumable launcher. Resource-only 4500/900-second variant PF `47af26bfe4eae43605939511eb338699b6b55dc814cf5a7a` passed. Slice 1 preserved 460/2352 expected rows; eight raw files were copied and hash-verified before the owner resumed slice 2 at 14:25:23Z. Trial and deployment decision remain open. Packet `/mnt/raid0/llm/tmp/refactor-01a16fc3/ct21-architect/slice2-4500/OWNER-PACKET.md`. ✅ 2026-10-27 [no-belief: tooling-repair]
  - [x] **CT-21-code — flag, architect-only variant and run prep (orchestrator `16f63825`, `9c273795`).** Flag `architect_untrusted_boundary_sentence` (default off, in `runtime_flags.spec.yaml`): an arm-B-worded sentence directly above the untrusted block in `architect_investigate` (evidence bundle) and `architect_synthesis` (specialist report) only, riding in the substituted variable (template files, `rules.md`, worker and REPL prompts untouched; tested byte-identical with the flag off for all, and REPL root prompt identical with it on). Run prep: `scripts/security/ct21_architect_arms.py` (OFF/ON arms through the production builders, reusing the CT-18 harness, `--surface synthesis|investigate`, `--dry-run`, refuses without WINDOW_CONFIRMED=1); decision rule predeclared at `artifacts/chat-templates/ct21-architect-boundary/PREDECLARED_RULE.md` before any run. Tests `test_rte_pfx3_ct21_flags.py` 8/8, `test_ct21_architect_arms.py` 4/4. Remaining (type B): the competence A/B on a frozen >=200-item architect set plus Skill-Inject/IB2 ASR, per the rule. ✅ 2026-10-22
  - 2026-10-27 16:35Z (ws58): CT-21 slice 3 FAILED rc1 at 16:14:44Z: debug_scorer.AnswerParseError answer_parse_failed[multiple_choice]: "no option letter or matching choice text found in the model's answer (labels=A-H, choices=2)". Progress stays at 1176/2352. Fix (score as an outcome, check the fixture) is with refactor. [no-belief: failed run, no result]
  - 2026-10-27 18:45Z (ws58 results harvest): CT-21 slice with the parse-outcome fix (`refactor-01a16fc3-ct21`) ended rc0 at 17:41:41Z with a `COMPLETE` marker. Row count 2352 of 2352 in `/mnt/raid0/llm/tmp/refactor-01a16fc3/ct21-parse-outcome-unblock-20261027/results/` (synthesis competence/ib2/skillinject 400/144/632, investigate 400/144/632); the older `ct21-architect/results/` copy is stale at 1956. `analysis.json` exists but carries only `wording` and per-surface counts; NO verdict file states a competence or ASR outcome, so none is claimed. The predeclared rule is not yet applied; the CT-21 box stays open. [no-belief: run complete, no verdict file]
  - 2026-10-27 21:35Z, ws58 results filing: CT-21 predeclared decision applied: **HOLD, flag stays default OFF** (`artifacts/chat-templates/ct21-verdict-20261027/AGGREGATE.md`, rule sha256 `4040098b7eeeff894012d7594bb4a04bd4a748d6243b662c2119b3b730cce260`; 2352 unique records, recomputed analysis matches). Investigate surface FAILS the competence gate: OFF 13/200 vs ON 11/200, ON-OFF -1.0 pp, Tango one-sided 95% lower bound -4.18 pp (must be > -3.0), and the aligned-twin net loss is 6 (> 1). Synthesis competence is 0/200 in BOTH arms (lower bound -1.33 pp, nominally non-inferior) which is an implausible floor: scorer audit is pending at NI and the synthesis competence result must not be read as evidence until it clears. Skill-Inject ASR improves on neither surface (synthesis OFF 6/316 vs ON 3/316, p=0.254; investigate OFF 0/316 vs ON 2/316). Static-attack ASR on fixture sets only, no robustness claim. CT-21 box stays open (enable-only-if rule not met). [belief: cc]
  - 2026-10-28 (workspace-58, NI draft): the first owner grant ended rc=1 before model/prelaunch (`CT21_ENROLLMENT_RECEIPT` not propagated); the corrected launcher (`e7b6f20ada99ccc186cba9a674668e7897f23a5a169f8a5fb5d026163e0ea6d5`) then passed exact-entry model-free T1. Evidence: `/mnt/raid0/llm/tmp/codex-ni-20261028-coordination/ct21-accepted-0227.txt`. [no-belief: launcher/preflight history, no measurement]
  - 2026-10-28 CT21 v2 run (`ct21-direct-exploratory-v2`, grant 03:01-03:04Z) ended rc=1 at 03:04:34Z. OBSERVATION only (Judged/Located), no ClaimTuple, no score, no correction to the original CT-21 result; **CT-21 stays HOLD / flag default OFF; parent box stays open.** 80/80 raw request/response files are retained (`000.raw.json`-`079.raw.json` under `/mnt/raid0/llm/tmp/codex-ni-20261028-rtg54/successor/run-exploratory-v2/`, 80 result lines, no producer sidecar, no `COMPLETE` marker). It failed at the writer: `write_belief_measurements` raised `CaptureError` because the emitted profile was `ct21-direct-exploratory-v2` while the writer validator accepted only `-v1`. Read-only audit (`/mnt/raid0/llm/tmp/codex-ni-20261028-rtg54/rearm-r1/ct21-v2-repair/CT21-RUN-AUDIT.json`): 80/80 request/response self-hashes valid, one server and one monitor identity, all responses `finish_reason=stop`, `cache_prompt=false`; 11 own-PID KFD/VRAM-positive samples (29.27-29.71 GB) but **no sampling interval fell fully inside any single request**, so the strict per-request residency gate would also have failed (it never ran; capture raised first). Server and monitor PIDs were reaped; actual grant scope `mi210_0,184-191` (8 threads), not pair 32,33. The summary's accuracy counts are retained as an artifact and not quoted or promoted. Evidence also: `ct21-failure-0313.txt`, `ct21-audit-residency-0322.txt` in `/mnt/raid0/llm/tmp/codex-ni-20261028-coordination/`. [belief: cc]
  - Prospective repair (preparation only): successor source sealed at `490afebf4a1cd4e63f2e8922d2419a10c32c4103d917556b977760316c820f8a` (v1/v2 validator fix, per-request-marker sampler with full-interval containment gate, receipt-default helper); exact-entry scoped PF pass for CPUs 32,33 is synthetic-only. A new owner `OWNER-RECEIPT-v3` bound to the new hashes and a rerun are still required. **CT-21 is not armed** (queue state refreshed 2026-10-28 ~03:45Z); no refreshed receipt or rerun is evidenced. [no-belief: preparation, no measurement]
  - Scope incident (disclosure): a stale shim used revoked CPUs 76,77 from 03:15:10 to 03:15:52Z (about 42 s, peak sampled RSS 21,092 KiB), beside the owner's YaRN s3 correctness run. No model or server started. Owner ruling: no invalidation, because co-tenancy cannot change a correctness verdict. Evidence: `ct21-cpu-incident-0318.txt`, `ct21-cpu-duration-0319.txt`. [belief: cc]
  - 2026-10-29 (ws58 filer A): `ct21-direct-v2-repair-20261028` rc0 00:30:13Z, the repaired successor of the 10-28 rc1 v2 run (GPU, 80 requests, real request span 87.4 s, server reaped). Predeclared rule (manifest): prospective direct-answer interface observations only, unchanged 20 arithmetic fixtures x 2 surfaces x OFF/ON; higher observable-correct counts better only on this fixed set; no CT21 competence/ASR/ENABLE threshold -> diagnostic observation. 80/80 outcomes observable. Observable-correct: investigate OFF 11/20 vs ON 12/20 (paired: 11 both, 1 ON-only, 0 OFF-only, 8 neither); synthesis OFF 12/20 vs ON 12/20 (0 discordant). Per-request residency recorded (minimum 2 samples per request window); producer sidecar `belief_measurements.jsonl` written (4 rows). Meaning: on this fixed direct-answer set the boundary sentence shows no observable difference (1 discordant pair in 40). Synthesis scores 12/20 here through the direct interface, which is consistent with the 0/200 synthesis competence floor in the original run being a scoring/interface artifact; that audit is still the owner's. The original 2352-row result is unchanged: **CT-21 stays HOLD / flag default OFF; parent box open.** Evidence `/mnt/raid0/llm/tmp/codex-ct21-direct-repair-20261028/run-20261029T002822Z-3838926/collection-0/{summary.json,results.jsonl,RESIDENCY.json}`. [belief: cc]

#### Research Intake Update — 2026-10-21 (harness cluster, DP-F amendment)

Operator-approved Stage-3 amendment (plan sha256 2edfb0662f61e1254e7dc5e2b21888ef4f19df800a283e82b25caebeb6644746). Durable records only: no checkbox, no index next action. Each monitor row carries its trigger and first step; each knowledge row states what to rely on. Ledger ids (DPF-...) key to the Stage-3 recommendation mapping preserved in `.research-session.json` (`stage3_filing`).

##### K11 — Instruction hierarchy, prompt-injection and skill-injection evidence

- DPF-W1-MANYIH-R4 (intake-2242): Numeric priority markers are resolved inconsistently by strong models (flip rates, format sensitivity), which supports keeping MHS-15 rule (c) 'conflicting priority markers' warn-only and adding brac…
- DPF-W1-MANYIH-R5 (intake-2242): Orchestrator's actual defence for untrusted layers is content-boundary neutralisation (src/security/control_tokens.py, CT-12.3a; builder.py untrusted-field comments), not a privilege order. ManyIH is…
- DPF-W1-MANYIH-R6 (intake-2242): Term collision: ANTI-OVERRIDE in this repo means the PromptForge REPLACE-vs-CONSTRAIN mutation risk prior (MHS-4/MHS-5), not instruction-hierarchy conflict. The intake-1313 dive-surfaced-source line…
- DPF-W1-MANYIH-R7 (intake-2242): Small open models: Qwen3.5 4B/9B/122B/397B score 4.1 / 6.6 / 14.7 / 34.1 overall (ordinal); coding 3.5 / 8.4 / 19.7 / 41.0. Small models are near the floor, so the full benchmark discriminates only a…
- DPF-W1-MANYIH-R8 (intake-2242): Reasoning cost: verbose reasoners spend ~7K reasoning tokens per coding sample vs ~1K, with no accuracy gain; on CPU a 427-sample full run at 7K tokens is ~3M generated tokens.
- DPF-W1-MANYIH-R9 (intake-2242): Per-sample outcomes flip 8-17% under cosmetic prompt changes even when aggregate ranking is stable (v4 Spearman 0.96): single-sample verdicts and small paired samples are fragile.
- DPF-W1-MANYIH-R10 (intake-2242): Skill files as an instruction-hierarchy attack surface with no trusted-first-party versus third-party distinction (cited from Skill-Inject).
- DPF-W1-MANYIH-R11 (intake-2242): Dual-use risk the authors concede: an attacker can tag malicious text with a high privilege value. Any tag scheme would need tag spellings neutralised in untrusted content, as control tokens are.
- DPF-W2-IHBENCH-IB1 (intake-2269): Tool-output injection compliance is a separate capability and is low for several open-weight models; a served-family model (Gemma 4 26B-A4B) scores 72.7% (thinking) vs 44.3% (no thinking) on User-ove…
- DPF-W2-IHBENCH-IB4 (intake-2269): Subtle low-stakes edits (appended disclaimer, small factual distortion) are followed far more often than destructive actions.
- DPF-W2-IHBENCH-IB6 (intake-2269): Binary predicate DSL with scoped LLM judges only where unavoidable (189 of 2,336), judge validated on 50 human labels.
- DPF-W2-IHCHALLENGE-IC2 (intake-2270): Prompt-level mitigations (sandwich, IH spec in system prompt, output monitor, rewriter, best-of-4) help a weaker model but give small gains at larger capability cost, or hurt, on a hierarchy-trained…
- DPF-W2-IHCHALLENGE-IC3 (intake-2270): Every conflict family has a non-conflict twin (Anti-Overrefusal); dropping it raises refusal (overrefusal 0.950 to 0.831).
- DPF-W2-IHCHALLENGE-IC6 (intake-2270): Formal resolution rule: lower-priority constraints are honoured only if compatible with the running feasible set; otherwise ignored (B_i = B_{i-1} when empty intersection).
- DPF-W2-IHCHALLENGE-IC8 (intake-2270): Title hazard: dataset card names the paper 'Large-Scale RLVR Improves Instruction Hierarchy on Frontier LLMs'.
- DPF-W2-NIGHTJAR-NJ1 (intake-2279): Handler-enforced boundary: reads limited to variables named in the prompt, writes limited to named outputs with a must-be-defined check, error messages for hallucinated variables or references, only…
- DPF-W2-NIGHTJAR-NJ2 (intake-2279): Eager loading of value and type of mentioned variables saves round trips and costs tokens for variables the model would not have inspected; the paper reports runtime effect but, in the text read, no…
- DPF-W2-NIGHTJAR-NJ3 (intake-2279): Prompts and host program share memory; handler safety checks are partial; isolation is future work.
- DPF-W2-NIGHTJAR-NJ4 (intake-2279): Cache keyed on identical effect-trace history returns the stored model response.
- DPF-W2-NIGHTJAR-NJ6 (intake-2279): Static LLM code generation (no live state) has poor accuracy despite speed; the interpreter approach adapts to intermediate values.
- DPF-W2-NIGHTJAR-NJ7 (intake-2279): A handler may cancel the prompt (Goto/break) as well as resume, giving the host program control-flow authority that function calling lacks.
- DPF-W2-SKILLINJECT-SI2 (intake-2286): Script-based and description-field carriers beat plain body text (contextual 71.8 vs 53.8; description injection raises execution by 10-14 points); models often run a script without reading it.
- DPF-W2-SKILLINJECT-SI3 (intake-2286): LLM-judge screening of skills detects obvious injections but over-rejects under a legitimizing policy; cannot judge contextual security.
- DPF-W2-SKILLINJECT-SI4 (intake-2286): Warning-policy system prompt is helpful but insufficient; effect varies by model family (minimal for some).
- DPF-W2-SKILLINJECT-SI6 (intake-2286): Injection position inside the skill file drives most variance; the user task has little effect.
- DPF-W2-SKILLINJECT-SI7 (intake-2286): Internal inconsistencies: 70 vs 71 vs 82 injections; text 10.6/16.8/4.7 vs Table 5 14.1/17.6/7.0.
- DPF-W3-ATTACKERMOVESSECOND-AM2 (intake-2294): Structural isolation (design patterns) is the only family not subject to this attack class, because it does not rely on the model recognising the attack.
- DPF-W3-SPOTLIGHTING-SP3 (intake-2313): Static single-keyword ASR corpus is the evidence class 2510.09023 says is misleading.

##### M20 — Security and instruction-hierarchy follow-ons

- DPF-W1-MANYIH-R1 (intake-2242): Privilege tags ([[Privilege N]] / [[z=N]]) as a prompt-composition mechanism; evidence is frontier hosted models only and shows 8-17% per-sample flips on value perturbation and up to -8.4 pts on a fo… — Trigger: the M8 probe (R2) shows a served role mis-resolves conflicting directives at a rate that matters AND a concrete multi-source conflict site is named. Then draft a tag-vs-prose-precedence arm. Until then nothing to build.
- DPF-W1-MANYIH-R2 (intake-2242): Fixture design for 'how do our served models resolve conflicting directives': conflict groups by construction (only same-group instructions conflict), deterministic AST/token checkers, random privile… — When M8 fires: build a 100-sample stratified subset of the ManyIH coding subset (6-tier no-conflict control + 12-tier), ordinal tags only plus a tag-free 'later instruction wins' prose arm, one served worker and one architect role, tempera…
- DPF-W1-MANYIH-R3 (intake-2242): ManyIH-Bench as a HIL eval fixture: it measures a model capability under a fixed prompt, not a harness-feature effect; harness arms only move it if they change prompt layering. — Trigger: a HIL arm that re-orders or re-tags prompt layers (skill injection, compaction, delegation context). Then use the R2 subset as a non-regression canary for that arm. Not a suite member.
- DPF-W2-IHBENCH-IB3 (intake-2269): Thinking on/off swings Gemma 4 26B-A4B User-over-Tool by 28 points; coding domain barely moves (74.0 vs 71.9), general moves most (70.2 vs 37.5). — Trigger: IB2 step 2 runs. Record the thinking setting of the worker role per arm and report both; if the worker serves with thinking off on tool-reading turns, the 44.3 row is the relevant prior.
- DPF-W2-IHBENCH-IB7 (intake-2269): Release is an anonymised placeholder; corpus and harness not located. — At the next intake wave, re-fetch arXiv abs 2607.25987 (check for v3 and a real URL). Until then no dataset use is claimed.
- DPF-W2-IHCHALLENGE-IC1 (intake-2270): Skeleton design: high-priority message + per-datapoint executable Python grader + unit-tested pass/fail examples + empty slot for conflicting low-priority text + a non-conflict twin. Grading never ne… — When M8's ALWAYS/NEVER probe fires: build the fixture from IH-Challenge single-constraint and multi-constraint skeletons (HF openai/ih-challenge, Apache-2.0) instead of, or beside, the ManyIH coding subset, because graders are executable p…
- DPF-W2-IHCHALLENGE-IC4 (intake-2270): Adaptive attacker via propose-evaluate-revise against the live defender; static-attack results overstate robustness; output monitor slows the attacker. — none now. Note for the M8 red-team bullet: a loop of this shape (attacker proposes, defender runs, deterministic grader scores) is already available as skeleton + grader, no new grader writing.
- DPF-W2-IHCHALLENGE-IC5 (intake-2270): Open RL data exists to train IH into a model; result only on proprietary GPT-5-Mini; transfer to open dense/MoE models unmeasured. — Append 'openai/ih-challenge (Apache-2.0, 4 jsonl, arXiv 2603.10521)' to the M4 trigger text so the dataset is named if the lane opens. Preparation only; the owning session applies.
- DPF-W3-ATTACKERMOVESSECOND-AM3 (intake-2294): Human red-team of our own wrappers: M8 bullet 'red-team of our proposer'. — Trigger already named in M8; do not start. Scope would need operator approval of a defensive red-team format.
- DPF-W3-DESIGNPATTERNS-DP3 (intake-2302): Coding-agent strict-format quarantine for untrusted docs/code. — Trigger: a role gains write/exec authority AND ingests fetched web/docs text.
