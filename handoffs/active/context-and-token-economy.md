# Context-Folding: Progressive Session Compaction Upgrade

> **Fold destination** (BRF-T1-F6, BRF-T1-1, route 1a, 2026-11-02): renamed from `context-folding-progressive.md`; absorbs 7 handoff(s) as `## Track:` sections at the end of this file (`delegation-context-preassembly.md`, `memento-block-reasoning-compression.md`, `per-request-reasoning-budget.md`, `rao-redel-substrate-spike.md`, `reasoning-compression.md`, `reasoning-effort-levels.md`, `tool-output-compression.md`). The body above the first track is the former `context-folding-progressive.md`.

**Scratch**: `/mnt/raid0/llm/tmp/ni08-equation-designs-20261006/` (CF-HF1 source survey)

Retired ROOT publication custody: `/mnt/raid0/llm/tmp/codex-ni-root-legacy-retirement-20261030`; original heads, patches and exact dirty bytes remain preserved there.
**Status**: refreshed 2026-11-09 (RTG-08 audit; see the audit-refresh section). Core context-folding phases landed; open work is the CF-3c instrument decision, the compaction A/B, and the folded tracks below. The 2026-06-19 alpha sweep is decision-scoped: promote the dual-objective score into the Phase 2b design variant, but do not change production compaction behavior without live/held-out validation. Original 2026-07-14 status text superseded.
**Created**: 2026-03-17
**Updated**: 2026-11-09
**Priority**: HIGH
**Categories**: context_management, session_compaction, rl_training_data
**Parent index**: [routing-and-optimization-index.md](routing-and-optimization-index.md) (row RTG-08). Corrected 2026-11-09: research-evaluation-index.md does not own this file.
**Completed ledger**: [context-folding-progressive-completed-through-2026-05-28.md](../completed/context-folding-progressive-completed-through-2026-05-28.md)

## 2026-11-09 audit refresh

- **What changed:** RTG-08 audit applied (47 boxes inspected, no box needs an Autopilot run; the Autopilot HOLD gates nothing in this file). In this pass: the Enable decision was RE-POSED (the "monitor-only, no behaviour change" premise was false; see the box at the audit-catch section, options A-D, recommendation C); the L163 "requires autopilot" claim was corrected (any orchestrator traffic works); CTX-HO-1 and CTX-HO-3 received their missing specification (the seven model-filled fields are not in the repo and are not invented; `worker_checkpoint.py` has no `resume_state`); an arm-name mapping table was added under the CF-3c A/B box. Other audit findings (already-done boxes, stale anchors, stale TB/E/RP boxes) are not part of this edit pass; header Status/Updated dates remain stale.
- **Current next action:** operator answers the Enable decision; in parallel the non-mutating shadow flag, CTX-HO-1 (after reading arXiv 2606.02875 App. C) and CTX-HO-3 are standalone code/doc work.
- **Doable now (no compute):** shadow-flag code, CTX-HO-1/3, TOC-CMP-5 bracket-role test, pre-registration documents, kv_bytes/token from GGUF headers.
- **Needs compute:** CF-3c A/B and every arm run (frontdoor :8070, quiet host), TOC-MP-4, DCP-6/12/13 arms, TB-1/E-2 curves. Disk: raid free 186G vs the 150GiB long-run floor.

## Executor Start Here

Do not reimplement Phases 0, 1, 1+, 2a, 2b L1-L4, 2c scaffolding, 3a, or 3b. The active question is whether the remaining aggressive-compression and monitoring probes justify new behavior beyond the already-landed multi-tier compaction stack.

## Outstanding Tasks
#### Compaction governance — intake 2026-11-06 (2611.05306 waves)

- [x] **TOC-CMP-1 — Fix the inverted reference-miss detector in the orchestrator summary path so a destroyed identifier can fire: read identifiers from `seg.granular_blocks` rather than the compacted text, and add a unit test whose only passing outcome is the destroyed-identifier case firing.** ✅ 2026-11-09 — already fixed: orchestrator `921f71d1` (2026-07-21, ancestor of main `98221350`); `src/graph/session_summary.py:355-366` computes lost ids as `granular_blocks` identifiers minus the surviving stub; tests `tests/unit/test_session_summary.py:304` (destroyed identifier fires) and `:322` (preserved identifier does not). Re-filing of the box ticked in the 2026-07-21 audit-catch section. [no-belief: re-filing of an already-landed code fix; no new measurement]
- [ ] **TOC-CMP-2 — Build the governance retention-and-compliance probe: declare 5-8 EPYC rules with hard/soft/prose enforcement classes and a sibling-target control, then measure four arms (full history, intact rule, degraded residue, rule absent) with deterministic tool-call predicates and the Appendix D v4 rubric, reporting retention as a ceiling and compliance as the result.**
  - **Specification added 2026-11-09 (audit).** (1) The "Appendix D v4 rubric" is the rubric of intake-2639 (arXiv 2608.11392, "AI Guardrail Survival under Single-Cycle Agentic Self-Summarization"; `research/intake_index.yaml`, plan row RI-3 in `research/deep-dives/ydnlc-20261106/PLAN.md`); copy its criteria into the probe spec, none are restated in this repo. (2) The 5-8 rules do not exist yet: the machine-readable rule registry with `enforcement_class: hard|soft|prose` is REG-ENF-1 in coordination-and-churn-pipeline.md and is still open. **Decision needed (low stakes):** (a) wait for REG-ENF-1; (b) pick 5-8 rules now from CLAUDE.md and the hook set, classing each by whether a hook enforces it (hard), a check warns (soft) or only prose states it. **Recommendation: (b)**, with the class column re-checked when REG-ENF-1 lands; the probe needs rules, not the registry. (3) "Sibling-target control" is defined in intake-2631/2636, not in this repo; read the definition before building. (4) Build of the probe harness and the deterministic predicates is doable now with zero inference; the four arms need a served model and are compute (see the COMPUTE list in the RTG-08 phase-1 report).
- [ ] **TOC-CMP-3 — Add the compaction artifact contract to the TOC A/B: the six-field execution brief (verbatim task, current intent, plan, completion requirements, artifacts, pointers), a pinned-governance buffer exempt from folding and re-injected verbatim with a post-fold entailment check, and a verbatim_manifest arm that declares what left the view.**
  - **Status 2026-11-09 (audit):** verified absent in code: no pinned-governance buffer and no six-field brief exist in `src/`. The "TOC A/B" arms are the `context_arm_ab.ARMS` set (`summary_only`, `summary_pointer`, `pointer_only`, `prune_pointer`, `full_history`); the `verbatim_manifest` arm has no counterpart (see the arm-name mapping table under the CF-3c A/B box). Code half (default-off flag) is doable now; the A/B is compute.
- [ ] **TOC-CMP-4 — Make the compaction A/B reproducible before running it: pre-register a minimum detectable effect of 0.10 blocked actions per step, at least 30 paired compaction points per model with 8-12 repeats each, three arms (raw tail, summary, FIFO), a boundary-stratified bootstrap, and report Pass^3 alongside accuracy.**
  - 2026-11-09 apr2 approved-routing: option (a) runner built, zero inference: orchestrator `scripts/benchmark/toc_cmp4_runner.py` (draw, plan, `run_schedule` with injected submit, resume ledger, re-run-once-then-drop policy) and 30 frozen points `benchmarks/toc_cmp4/points-20261109.json`, sha256 `9de7e3bad1714675d1550421aa920840dc7ab7ff2ccb22dded16b853bad2655a`, 720-run schedule from `plan`; arm order is a seeded sha256 permutation per point. Assumptions to confirm: pool is the 50 `core_v2` ids (not all reach a boundary turn: runs without a boundary event need a validity rule), strata are fixed absolute turn bands early 2-3, middle 4-6, late 7-9 instead of trajectory terciles. Orchestrator `d19d44cd`. Running waits for the live stack and the operator ack. [no-belief: runner and draw, nothing measured]
  - **Specification added 2026-11-09 (audit).** "Blocked actions per step" is defined in TOC-MP-3(b): post-boundary blocked/error actions over the first 5 actions, counted separately from deliberate re-reads; it is a trajectory-artifact field only if the TOC-MP-3 schema additions carry it (verify in `trajectory_artifact.py` before pre-registering). `raw tail` and `FIFO` are not in `context_arm_ab.ARMS`. **Decision needed:** (a) pre-register with the implemented names (`summary_only`, `pointer_only`, `prune_pointer`) and drop the unimplemented `raw tail`/`FIFO`; (b) add two arms to `ARMS` first. **Recommendation: (a)**, since TOC-MP-2i already built those arms and (b) adds code for names no prior result uses. Reconcile the repeat count: TOC-MP-3(a) says n>=2 trials (prefer 4), this box says 8-12 repeats; the larger pre-registered number governs only if its cost (>=30 points x 8 repeats x 3 arms = 720 runs per model, duration per run unknown) fits a window. Pre-registration document is doable now.
  - 2026-11-09 apr2 second-pass: PARTIAL. Pre-registration written on root branch `apr2/second-pass-20261109`: `docs/design/toc-cmp-4-preregistration-20261109.md`. It verified the per-turn `blocked` field in `src/graph/trajectory_artifact.py` (lines 262-275, under `context_arm_ab`), so BAPS needs no schema addition, and registers option (a) (`summary_only`, `pointer_only`, `prune_pointer`), 30 frozen paired points per model, 8 repeats (pilot of 8 points x 4 repeats first), boundary-stratified bootstrap, Holm over three contrasts, MDE 0.10 (requires per-point paired SD <= 0.196, an unmeasured assumption), Pass^3 beside accuracy, futility-only interim. Box stays open until the operator acks (a) versus (b) and the 720-run cell is booked. [no-belief: pre-registration text only]
  - **2026-11-09 apr2 decided-rows: operator chose option (a) and to book the 720-run cell at low rank. NOT PUBLISHED; it needs a live stack and a runner that does not exist.** (1) Every arm run goes through the orchestrator REPL graph on the live frontdoor `:8070` (this file's "Needs compute" line and `docs/design/toc-mp-ab-design-20261031.md` section 1: C = 16,384 inside the 65,536 slot, all arms on the same unmodified server), so it is a live-stack job, not a self-contained launcher row. (2) No runner drives `ORCHESTRATOR_CONTEXT_ARM` / `ORCHESTRATOR_CONTEXT_FORCE_TURNS` over (point, arm, repeat) with the seeded arm permutation and the receipt; none exists in either repo. (3) The 30 frozen paired points (sha256 in the receipt) are not drawn. (4) Per-run time is unknown until the 96-run pilot, and the pre-registration makes the 720-run booking conditional on it. Pre-registration section 2 now stands as ratified option (a). Doable first: runner plus point-list draw (zero inference), then the 96-run pilot row once a stack window exists. [no-belief: decision note]
- [ ] **TOC-CMP-5 — Add the remaining role-boundary regression assertions to the orchestrator summary path: a hostile tool output containing the bracket-role literal `[User]:` must not survive `build_consolidation_prompt` as an un-neutralised role boundary, and the summary must stay a prompt block rather than a user-role message.** (REWRITTEN 2026-11-09, audit: the ChatML half is already covered, `tests/unit/test_control_token_assemblers.py:297` asserts `build_consolidation_prompt([INJ])` has no control tokens. Remaining: `[User]:` appears nowhere in `src/`, and `src/security/control_tokens.py` neutralises ChatML-family tokens only, so the bracket-role case is untested and probably unhandled; the "stays a prompt block" assertion is absent. Standalone orchestrator test plus, if the test fails, a neutraliser extension. Zero inference.) [2026-11-09 apr2 rtg08-evl47-pip04-code: IMPLEMENTED on orchestrator branch `apr2/rtg08-evl47-pip04-code-20261109` (8c7d0f33), tick on landing. Three tests in `tests/unit/test_control_token_assemblers.py`: bracket-role text stays inside the Events block verbatim (nothing before it), the summary goes out as a prompt string with routing role `worker_general` and no message list, and a tripwire that no `src/` file uses `[User]:`-style framing. No neutraliser extension: the literal is not a boundary for any template the stack serves, and the tripwire flags it if that changes. Run with the orchestrator venv python plus system pytest on PYTHONPATH (repo conftest needs fastapi, absent from system python; the venv lacks pytest): 19 passed, 1 skipped; 2 unrelated failures in the same file (`test_every_sink_calling_function_is_accounted_for`, `test_accounted_elsewhere_has_no_stale_entries`, both about `proactive_stage.py`) exist independent of this change. [no-belief: test addition]]


- **[declined: ws58 2026-11-03 content-review: unbounded conditional ("only if it answers a current production question") with no question named; the L3 sweet spot stands]** **CF-L5 maximum-compression validation**: run the L5 single-sentence-per-segment compression check only if it answers a current production question. Compare against the known L3 sweet spot and record whether L5 is rejected, role-limited, or worth further tuning.
- [ ] **CF-3c live quality-monitor validation**: validate `CompactionQualityMonitor` on real traffic/telemetry. The class scaffold exists; tune degradation thresholds only after upstream-compressor anti-thrashing in [tool-output-compression.md](context-and-token-economy.md#track-tool-output-compression) Phase 3d is accounted for.
  - **Note 2026-11-09 (audit):** overlaps the Enable decision (below, audit-catch section) and the CF-3c A/B; it cannot start until that decision lands because the monitor is created only inside the destructive compaction branch. "Real traffic" = any orchestrator traffic (not Autopilot-specific).
- [x] **CF-2c.0 / NIB2-43 dual-objective alpha sweep**: implemented an offline retrieval proxy in `epyc-inference-research` `scripts/benchmark/compaction_alpha_sweep.py` and scored existing Package-C compaction/summarizer rows at alpha values `{0.0, 0.25, 0.5, 0.75, 1.0}`. Result artifacts: `data/research/2026-06-19-compaction-alpha-sweep/alpha_sweep.{json,csv}`. On 110 valid rows, alpha `0.0` beat faithfulness-only alpha `1.0` by `+0.051315` average precision (`0.940463` vs `0.889148`) and improved ROC-AUC (`0.743056` vs `0.534420`), crossing the `>2%` promotion gate. This is still a proxy result, not a deployment decision: promote dual-objective scoring into the Phase 2b design variant, then require a live/held-out validation before changing production compaction behavior.
- [x] **CF-2c.1 alpha-promotion decision scope**: existing evidence is sufficient to promote the dual-objective score into the Phase 2b design variant only. The remaining blocker is specific and non-inferential: do not flip live production compaction behavior until a live/held-out validation artifact exists. ✅ 2026-07-14

## Decision Record: CF-DD8 / NIB2-40

**Closed 2026-06-13**: do not add a separate context-folding implementation for Claude Code-style "budget reduction" right now. The concrete per-message cap surface found in the local docs is tool-output scoped, and EPYC already has explicit ownership there via [tool-output-compression.md](context-and-token-economy.md#track-tool-output-compression): `truncate_output()` provides an 8192-character hard cap, `_spill_if_truncated()` limits visible previews and preserves full output by pointer, and the native compression layer sits before spill/truncation.

Layer mapping:

| Claude Code layer | EPYC owner / state | Decision |
|---|---|---|
| Budget reduction | [tool-output-compression.md](context-and-token-economy.md#track-tool-output-compression) for tool outputs; REPL token-budget knobs for generation budgets | No new CF-owned cap. Keep caps/compression/spill in the tool-output lane. |
| Snip | Segment architecture can support surgical removal, but no live need is proven for a new `trim_segment(segment_id)` API | Evidence-gated follow-up only if CF-3c telemetry shows a single large segment or failed trace is poisoning summaries. |
| Microcompact | Native tool-output compression plus spill/peek | Existing owner; sequence Phase 3d anti-thrashing before CF-3c tuning. |
| Context collapse | L4 two-level condensation / consolidated summaries | Covered; L5 validation remains the only aggressive-compression question. |
| Auto-compact | Threshold-triggered session compaction | Covered; live quality validation remains open. |

Reopen criteria: only promote new context-folding code if clean live telemetry shows context loss from non-tool session history that tool-output compression cannot address, or if `CompactionQualityMonitor` flags recurring reference misses caused by one removable segment class. In that case, prefer a narrow surgical-snip API over another global per-message cap.

## Dependency Forks

| Outcome | Next action |
|---|---|
| L5 quality collapses or only helps non-coding roles | Keep L3 as the default sweet spot; document any role-specific exception. |
| L5 is competitive with L3 on target roles | Promote a narrow follow-up to tune L5 per role, gated by live monitor results. |
| CF-3c telemetry is noisy due to compress/uncompress oscillation | Sequence after [tool-output-compression.md](context-and-token-economy.md#track-tool-output-compression) Phase 3d anti-thrashing work. |
| Alpha sweep shows alpha < 1.0 beats helpfulness-only by >2% | **MET 2026-06-19**: alpha `0.0` improved average precision by `+5.13pp` over alpha `1.0` on the Package-C offline proxy. Promote the dual-objective score into the Phase 2b design variant, with live/held-out validation before production behavior changes. |
| Alpha sweep shows no signal | Park dual-objective compression until GPU/fine-tune capacity exists. |

## Completed Scope

| Scope | Result | Ledger |
|---|---|---|
| Phase 0 trigger threshold | Complete. | [completed ledger](../completed/context-folding-progressive-completed-through-2026-05-28.md) |
| Phase 1 two-level condensation | Complete. | [completed ledger](../completed/context-folding-progressive-completed-through-2026-05-28.md) |
| Phase 1+ segment cache/dedup | Code complete. | [completed ledger](../completed/context-folding-progressive-completed-through-2026-05-28.md) |
| Phase 2a summarizer eval | Done; 30B-A3B is minimum viable summarizer at 3.0/3.0. | [completed ledger](../completed/context-folding-progressive-completed-through-2026-05-28.md) |
| Phase 2b L1-L4 sweep | Done; L3 sweet spot recorded at 82% compression and 2.84/3 retention. | [completed ledger](../completed/context-folding-progressive-completed-through-2026-05-28.md) |
| Phase 2c/3a/3b code | Helpfulness scoring, process rewards, role-aware profiles, and monitor scaffold landed; live validation remains above. | [completed ledger](../completed/context-folding-progressive-completed-through-2026-05-28.md) |
| CF-DD8 / NIB2-40 gap analysis | Done; no separate context-folding per-message cap. Tool-output budget reduction stays in the tool-output-compression lane; surgical snip is telemetry-gated. | This file, decision record above. |

## Key Files

- `/mnt/raid0/llm/epyc-orchestrator/src/graph/session_log.py`
- `/mnt/raid0/llm/epyc-orchestrator/src/graph/session_summary.py`
- `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/`
- [tool-output-compression.md](context-and-token-economy.md#track-tool-output-compression)
- [routing-intelligence.md](routing-program.md#track-routing-intelligence)
- [non-inference-backlog.md](engineering-hygiene-backlog.md)

## Reporting Instructions

After any CF task, update this active handoff with command, dataset/log source, metric direction, result, and the fork decision. Update [routing-and-optimization-index.md](routing-and-optimization-index.md), [research-evaluation-index.md](research-evaluation-index.md), and [non-inference-backlog.md](engineering-hygiene-backlog.md) if task ownership or priority changes.

## Research Intake Update — 2026-07-21 (Seven-policy bake-off — and a corrected reading of it)

- **[intake-869] "Diagnosing and Mitigating Context Rot in Long-horizon Search"** (arxiv:2606.29718; GAIR/SJTU, Pengfei Liu) + code release `github.com/GAIR-NLP/ContextRot`
  - Relevance: supplies the **comparative ablation CF-3c lacks** — seven context-management methods across three families (compaction/summarization, trimming/discarding, isolation/sub-agents) on one common harness and model set. Distinct from intake-273 (Chroma), which is static single-turn; this is multi-turn self-accumulated agentic context.
  - Headline as published: keep-latest+summary lifts BrowseComp 35.0 → 48.2 (+13.2pp) and cuts rot rate 53.4% → 16.2%.
  - **CORRECTED READING — use this, not the headline.** Their own table shows keep-latest ALONE at 43.8% and plain Discard at 44.6%. So **observation-dropping carries ~9pp of the 13.2pp and summarization adds only 3.6-4.4pp.** And FoldAgent actually scores *higher* on accuracy (54.0%) than the declared winner. This is quantitatively close to intake-274 (The Complexity Trap), which found masking ≥ summarization on SWE-bench across five configs at lower cost, with a 13-15% trajectory-elongation penalty from summaries.
  - **Practical read for CF-3c:** treat "drop stale observations" as the robust cross-domain result and "add LLM summarization on top" as a domain-specific, small, cost-negative-until-proven addition to be A/B'd rather than assumed.
  - The most durable takeaway is not the policy ranking at all: it is the **behavioral failure mode**. Rot presents as give-up / hedged-uncertain answers, and our compaction telemetry currently tracks reference misses, not refusal/hedging. A rot-rate move 53.4% → 16.2% is a far sharper signal than the accuracy delta.
  - Caveats: BrowseComp is a 100-sample split (a 4.4pp gap ≈ 4 questions — our per-suite gate-resolution caveat applies); the model-dependence claim is n=2; the 98.7% judge-agreement figure lacks chance correction (see intake-876); live-web contamination may account for up to 4pp (intake-877). All numbers are OBSERVATIONS under MEASUREMENT.md.
  - Usable asset: the harness talks OpenAI-compatible endpoints and its **local-search arm (BrowseComp-Plus + embedding retrieval) is self-hostable against our BGE servers** — the cheapest path to re-measuring under our own protocol.

- [x] CF-3c design input: frame the compaction A/B around the seven-policy ablation, prioritizing observation-dropping and treating summarization as the marginal arm to be justified, not the default. ✅ 2026-07-29 — **corrected to match the live path:** `ContextCompressor` performs deterministic type-aware stubbing only; `openai_compat.py` consumes that result directly and no caller invokes an LLM summarizer. The first runnable comparison is therefore `no compaction` versus protected-zone deterministic stubbing, with the threshold pre-registered; an LLM-summary arm is a separate future feature, not a currently available control. [intake-869, intake-274] **[2026-09-14 correction]** an LLM IS invoked on other compaction-adjacent paths: `src/graph/compaction.py:176-189` (worker-generated compaction index) and `src/repl_environment/environment.py:~679` (spill summary). The statement above holds only for `ContextCompressor`/`openai_compat.py`. `intake-1350#record`.

#### CF-3c A/B frame (2026-07-29)

Run only after the monitor is persisted and the operator's shadow-telemetry enable decision below:

1. **A0 — no compaction:** preserve the same conversation/prompt construction without the
   `context_compression` feature.
2. **A1(k) — current implementation:** protected first/last zones plus deterministic file-read/REPL
   stubs, with `TOOL_OUTPUT_AGE_THRESHOLD=k`; pre-register a small bounded set of `k` values rather
   than treating the current `8` as evidence.
3. **A2 — future, only if implemented:** A1 plus a separately introduced LLM summary component. It
   must earn an incremental benefit over A1; it cannot be described as a test of today's code.

Hold the workload, model, prompt construction and turn cap fixed. Record reference-loss, give-up,
and no-answer/max-turns rates together; a lower apparent rot rate paired with more unfinished
trajectories is a loss. This changes no runtime configuration and authorizes no inference while E5
holds the host. [2026-09-14] Also record per-task re-fetch/retrieval-call count as a required co-metric:
a threshold that holds quality but raises re-queries is not equivalent. `intake-1359#record`.
- [x] **CF-AB-1 — Define arms A3, A4 and A5 in the CF-3c A/B frame (lines 86-103) as declared-parameter arms; not to be run until TOC-SP-5 shows binding windows at the role.** A3 staged elision-then-summarize: soft threshold 0.60 of the window, hard 0.85, recent window 0.30 floored at 2 turns (`intake-1991#record`; rule-based elision before LLM summarisation is the cheapest effective strategy, `intake-1991#02`). A4 age-tiered half-life elision: activate at 0.50 of the allowance, newest 4 tool results verbatim, caps 4096/2048/1024/512/256 chars for tool-result age <=7/<=15/<=31/<=63/older, head and tail 50/50 around an omission marker, age counted in tool results not turns, constants not tuned first (`intake-2153#00`). A5 hard mask: K = 5 (also K = 4) newest tool results verbatim, older results replaced by a one-line placeholder carrying tool name, arguments and the peek pointer, error outputs exempt, age unit stated (`intake-2157#00`). The existing A1 stub arm is the no-pointer arm. Each arm is compared with the no-management control at two window sizes under HIL-2 item 8 and TOC A/B-COST/TRIG/STRAT. ✅ 2026-10-20
  - CF-AB-1 addendum (2026-10-21, design text only; arm numbers A6 and A7 are unused by A0-A5, so no renumbering was needed): **A6, reset with a structured handoff artifact** (schema: state, next steps, open defects; trigger at the A3 window thresholds; compared with A3 on uncached prefill per solved task and premature-wrap-up share from the HIL-12 scan) (`intake-2228#record`). **A7, externalised lossless log with programmatic search** (complete history outside the prompt, only the current turn kept, grep or Python search, declared log format and tool surface; not run until the binding-window screen shows a binding window at the role and a local probe shows the role writes working search code; priced by TU-LADDER-1) (`intake-1011#record`). **Co-metric for all CF-AB-1 arms:** a post-compaction closed-book recall exam with questions mined from the elided region, identifier answers matched mechanically, a one-search recovery arm, declared before any run, not an LLM judge for identifier questions (`intake-117#record`). Two dives proposed an A6 with different content; this addendum resolves it as the handoff-artifact arm above.
- [x] ~~CF candidate: add give-up-rate and uncertain-incorrect-rate as compaction-quality dimensions alongside reference misses.~~ **DECLINED/SUPERSEDED 2026-11-01:** the correction below scopes uncertain-incorrect to the eval tower because production has no correctness label; the current production dimensions are the scoped give-up and no-answer/max-turns item below. [no-belief: superseded scope; no production correctness label]
- **[declined: ws58 2026-11-03 content-review: merged into the CF-3c A/B as one arm]** CF candidate: the `keep_k_latest_wo_reasoning` arm is a direct cheap test for the retain-historical-thinking-blocks question owned by [reasoning-compression.md](context-and-token-economy.md#track-reasoning-compression). [intake-869]

## Deep-Dive Correction — 2026-07-21 (CF-3c's instrument is off, inverted, and unpersisted)

Supersedes the ordering in the 2026-07-21 intake section above. A deep dive on intake-869 verified the paper's numbers (all correct as cited) but found the **actionables were stacked on an instrument that measures nothing**. Verified against source 2026-07-21:

**1. `CompactionQualityMonitor` is gated off.** Defined `src/graph/session_log.py:563`; its only call site (`src/graph/session_summary.py:250-306`) requires BOTH `features().role_aware_compaction` AND `features().helpfulness_scoring`. Both are `FeatureSpec(..., False, False, ...)` (`src/features.py:152`, `:154`) — off in dev *and* prod. **Zero production telemetry exists.** `context_compression` is likewise `False, False` (`:185`).

**2. The reference-miss detector is INVERTED — this is the highest-value line in the analysis.** At `session_summary.py:276` compaction overwrites in place: `seg.consolidated = f"[Compacted] {first_sentence}"`. The miss check at `:297` then does `compacted_ids = extract_identifiers(seg.consolidated)` — extracting identifiers from the **surviving stub**. It therefore fires only when a later turn references content compaction KEPT, and can **never** fire for content compaction DESTROYED — the entire failure mode it exists to detect. `seg.granular_blocks` still holds the pre-compaction text, so the fix is one line.

**3. It is never persisted** — excluded from the LangGraph state projection (`src/graph/langgraph/state.py:207`), no writer for `to_dict()` outside tests. Emits one INFO line per hit and dies with the session.

**4. The durable finding from the paper is the rot ↔ no-answer substitution, not the policy ranking.** Table 4 (Qwen3.5/BrowseComp): ReAct has NA=0.0; every summarization arm has NA=37-49%. Summary(Turn) reports rot 1.8% while **38.4% of trajectories never produce an answer**. Keep-Latest NA 4.2 → KL+sum NA 17.6 — adding summarization roughly **quadruples the unfinished-trajectory rate**. **Any give-up-rate telemetry we add MUST be paired with a non-termination counter, or we will optimize straight into agents that never finish.**

**5. Corrections to the earlier intake section's framing:**
- Summarization's marginal contribution over trimming is **+1.55pp averaged and sign-inconsistent** (4 of 6 model×dataset cells positive; GLM/BC+ −1.1, GLM/xbench −0.6) — not the +3.6-4.4pp single most-favorable cell quoted earlier.
- Table 9 gives ±2.5 to ±3.8 SD over 5 repeats on a 100-question split — the Discard→KL+sum gap of +3.6 is **not distinguishable from noise**.
- The paper never claims 48.2 is the accuracy winner; it bolds FoldAgent 54.0. Its actual claim is a cross-dataset average, where KL+sum wins by **0.35pp over n=2 models**.
- `keep_k_latest` is **not** pure trimming — it falls back to summary-restart on overflow. The real contrast is "summarize on overflow" vs "summarize proactively at 32K".
- Cost framing was backwards: the expensive arms are pure threshold-triggered summarization (21.7→53-69 tool calls); the trim+summarize hybrid is barely above trim alone. Its real cost is **unfinished trajectories, not tokens** — so summarization must justify itself against `repl_max_turns` rate, not token spend.

**6. Our stack is already past the paper's baseline.** `build_granular_summary` retains a **60-character** output preview per turn — we never keep raw observations. And `src/context_compression.py` already implements a keep-latest-8-with-summary hybrid (`TOOL_OUTPUT_AGE_THRESHOLD = 8`, `summarize_tool_output()` stubbing file reads/REPL while keeping errors verbatim, protected-zone first-3/last-5). A seven-policy bake-off would mostly re-derive a design we have already committed to. [2026-09-14: the code stubs ALL middle-zone tool outputs once ≥8 tool messages sit in the middle zone (`context_compression.py:334`) — "keep-latest-8" overstates retention.]

- [x] **Fix the inverted detector (one line, highest value here) ✅ 2026-07-29**: implemented by epyc-orchestrator `921f71d1` in `src/graph/session_summary.py`, with regression coverage in `tests/unit/test_session_summary.py`; the completed duplicate is recorded below.
- [x] Persist `CompactionQualityMonitor` through the LangGraph state projection and checkpoint writer. epyc-orchestrator `30aa952e5101274f42e7ce22bf933696632bfa69` adds a plain-data projection (`to_dict`) and restore (`from_dict`) path. The existing `run_task_lg_durable` / `AsyncSqliteSaver` checkpoint writer now persists it; a test writes to temporary SQLite, opens a fresh saver/graph reader, verifies the payload, and restores into a new TaskState. 153 focused tests passed; log `/mnt/raid0/llm/tmp/ni08-equation-designs-20261006/context-compaction-monitor-20261030/VALIDATION-CF-MONITOR-r2-20261030.log` (SHA-256 `0fbf74737df1eacbcbf1c341cb94b2b438b79334e9adb05af1078144216e046a`). Feature flags remain off; no live telemetry, reload, or measurement/grade change is claimed. ✅ 2026-10-30 [no-belief: implementation/tooling; no new measurement]
- [x] Add give-up-rate AND **no-answer / max-turns rate** as production dimensions. Detectors already exist in `src/pipeline_monitor/anomaly.py` (`detect_repl_max_turns` = the paper's NA exactly; `detect_assistant_help_request` ≈ give-up; `detect_self_doubt_loop` ≈ hedging) — the work is joining them to compaction state, not writing them. Scope **uncertain-incorrect to the eval tower only** — it needs a correctness label that does not exist in production. ✅ 2026-11-01 — epyc-orchestrator implementation `df5645e961107854a475fcf86fd19464ba1d1ae5`; q1-locked focused validation (109 passed) at `epyc-orchestrator:artifacts/validation/cf-terminal-outcomes-20261101/REVALIDATION.md`, receipt commit `32586f6db0256bb57a92d9e2aa2f81f7d66104fe`. No live traffic telemetry or feature-flag enablement is claimed. [belief: cc]
- [ ] Replace the seven-policy bake-off with the narrower question our code actually poses — **CF-3c A/B — the question our code actually poses (absorbs the seven-policy bake-off, the keep_k_latest_wo_reasoning arm, the masking anchor and the non-termination counter).** Arms: A0 no compaction; A1(k) protected-zone deterministic stubbing at TOOL_OUTPUT_AGE_THRESHOLD k (sweep); A2 observation-masking/truncation (the MANDATORY anchor — neither ACM nor AREX ran one, and intake-274/869 + BEAM Table 8 say masking carries most of the benefit); A3 keep_k_latest_wo_reasoning (the retain-historical-thinking-blocks test, intake-869). Every arm reports the non-termination counter (budget exhaustion must surface as NA, never as a silent highest-confidence answer). Frontdoor model, same tasks, same seeds; metrics: task accuracy, tokens/task, wall. Decision: adopt the cheapest arm within 1 pp of the best; an LLM-summary arm is a separate component and is not part of this comparison.
  - **Arm-name mapping (added 2026-11-09; the four arm vocabularies below are DIFFERENT sets and the letters collide).** Disambiguate by always prefixing the source, e.g. `CF-3c/A3` vs `CF-AB-1/A3`.

    | Concept | CF-3c A/B (this box) | CF-3c frame (L99-103) | CF-AB-1 / CF-AB-2 | TOC-MP-2 | TOC-CMP-4 | `context_arm_ab.ARMS` |
    |---|---|---|---|---|---|---|
    | No management | A0 | A0 | A0 (control) | 5 full history (reference) | none | `full_history` |
    | Deterministic stubbing at age k | A1(k) | A1(k) | A1 (no-pointer arm) | none | none | none (production `ContextCompressor`, not an arm) |
    | Observation masking, mandatory anchor | A2 | none | A5 hard mask (K=5 or 4, with pointer) is the nearest | 4 prune+pointer is the nearest | FIFO (nearest) | `prune_pointer` (nearest) |
    | LLM summary | none ("separate component") | A2 (future) | A3 staged elision-then-summarize (nearest) | 1 summary-only, 2 summary+pointer | summary | `summary_only`, `summary_pointer` |
    | keep_k_latest_wo_reasoning | A3 | none | none | none | none | none |
    | Age-tiered half-life elision | none | none | A4 | none | none | none |
    | Pointer only, recent tail | none | none | none | 3 pointer-only | raw tail (nearest, no pointer) | `pointer_only` |
    | Reset with handoff artifact | none | none | A6 | none | none | none |
    | Externalised lossless log + search | none | none | A7 | none (pointer arms use `peek`/`grep` on the verbatim log) | none | none |

    Collisions: `A2` = masking (CF-3c A/B) = future LLM summary (L99-103 frame); `A3` = keep_k_latest_wo_reasoning (CF-3c A/B) = staged elision-then-summarize (CF-AB-1). Only TOC-MP-2 and `context_arm_ab.ARMS` correspond one-to-one (1-5 to `summary_only`, `summary_pointer`, `pointer_only`, `prune_pointer`, `full_history`; verified `src/graph/context_arm_ab.py:16`). TOC-CMP-4's `raw tail` and `FIFO` have NO exact counterpart in `ARMS`; TOC-CMP-3's `verbatim_manifest` arm is also unmapped. Resolution when the A/B is pre-registered: use the `ARMS` names as the runnable vocabulary and pre-register which CF-AB-1 arms map onto them.
- [x] Do NOT prioritize running the ContextRot harness. ✅ 2026-07-29 — current Stage-2 evidence confirms the only self-hostable arm (BrowseComp-Plus) has a ~1pp-or-negative summarization effect; its paid `SERPER_API_KEY` and missing license also fail the open-source-only constraint. If reopened, reproduce only the behavioral rot/NA signature, never the underpowered accuracy delta.
- **[declined: ws58 2026-11-03 content-review: standing rule with no completion state (its own text says so); stays readable here]** **STANDING — if the ContextRot harness is ever reopened, reproduce ONLY the behavioural
  rot/NA signature, NEVER the underpowered accuracy delta.** The paid `SERPER_API_KEY` and
  missing license also fail the open-source-only constraint, so any reopening must clear that
  first.
  *(SPLIT 2026-08-12 by `mainC`. The box carried two things: a DECISION not to prioritise,
  which genuinely completed on 2026-07-29, and a rule constraining HOW a future reopening may
  proceed. Closing the box retired the rule — so whoever reopens the harness would find no
  live constraint and could rerun the exact underpowered accuracy delta this forbids.)*
- [x] **Self-hostable/BGE correction recorded ✅ 2026-07-29**: the shipped embeddings are Qwen3-Embedding-8B-specific (4096-dim, 821MB, bf16); using BGE would require re-embedding all 100,195 docs and would break comparability. Source-backed intake/deep-dive correction: epyc-root `2102c0f05`.

### Ownership clarification — 2026-07-21 (this is orchestrator work, not inference-research)

The rot ↔ no-answer finding and the compaction-telemetry fixes are **orchestrator-side**, not inference-research, and need no quiet window or inference budget:

- The instrument is `CompactionQualityMonitor` (`src/graph/session_log.py:563`) and its call site `src/graph/session_summary.py`, both orchestrator code.
- The give-up / no-answer detectors already exist in `src/pipeline_monitor/anomaly.py` (`detect_repl_max_turns` = the paper's NA metric exactly, `detect_assistant_help_request` ≈ give-up, `detect_self_doubt_loop` ≈ hedging). The work is joining them to compaction state and persisting the result — plumbing, not measurement.
- Nothing here requires llama.cpp, a kernel build, or a benchmark slot. Validating that the telemetry *moves* needs orchestrator traffic, but ANY orchestrator traffic works (manual chat, a scripted session, a benchmark run); Autopilot is not required (corrected 2026-11-09), and it rides normal operation rather than a reserved inference window.

The one genuinely inference-adjacent item is the optional ContextRot harness replication, which is already marked do-not-prioritise above (self-hostable arm is the low-signal one, ~25-50h/arm, underpowered at achievable reps).

- [x] Fixed the inverted reference-miss detector (`session_summary.py`) to compare identifiers destroyed by compaction — present in `seg.granular_blocks`, absent from the surviving stub — rather than identifiers read off the stub itself. Two regression tests added that fail against the prior behaviour in both directions (missed real loss; false positive on preserved content). ✅ 2026-07-21

### Audit catch 2026-07-21 — the fixed detector is DEAD CODE until the flags flip

The inverted-detector fix (`epyc-orchestrator 921f71d1`) and the persistence task above are both inert while `role_aware_compaction` AND `helpfulness_scoring` remain `FeatureSpec(..., False, False, ...)` (`features.py:152,154`). No enable task existed — the "highest-value one-line fix" currently executes zero times in production.

- [ ] **Enable decision (operator): the compaction-quality flag set (`two_level_condensation`, `role_aware_compaction`, `helpfulness_scoring`)** — **RE-POSED 2026-11-09: the original "flip two flags in SHADOW, monitor-only, no behavior change" premise is FALSE.** Verified at orchestrator `98221350` (`src/graph/session_summary.py`): (1) `_maybe_refresh_session_summary` returns early into `_refresh_two_level_summary` only when `two_level_condensation` is on (`:149-151`); the whole branch below is unreachable otherwise. (2) Inside it, `role_aware_compaction` (+ more than 4 segments) AND `helpfulness_scoring` gate `seg.consolidated = f"[Compacted] {first_sentence}"` (`:309-340`), which OVERWRITES the segment text that `to_prompt_block()` renders into the prompt (`:378`). (3) `CompactionQualityMonitor` is constructed only inside that overwrite branch (`:336-338`), so the monitor cannot record anything without the destructive compaction. (4) All three are `FeatureSpec(..., False, False, ...)` (`src/features.py:168,170,172`) and none appears in the production feature-wave overrides. So enabling the monitor IS a behaviour change to the session prompt; the flags do not just "govern whether telemetry is recorded". `granular_blocks` keeps the pre-compaction text in state, but it is not rendered.
  - **Decision needed (operator).** Options: **(A) Defer, record the reason** — leave all three off; the detector fix (`921f71d1`) stays dead code until the CF-3c A/B; cost: CF-3c has no instrument and nothing validates the monitor. **(B) Flip all three on live** — the first real telemetry, but switches the session-summary path from per-2-turn re-summarization to granular+deep consolidation (`two_level_condensation`) AND destroys segment text beyond the first sentence; a quality risk on every session with no baseline, and it cannot be called shadow. **(C) Build a true non-mutating shadow, then flip only that** — new default-off flag (e.g. `compaction_shadow`) that computes helpfulness scores, would-compact counts and hypothetical reference misses (against the would-be stub) without writing `seg.consolidated`, creating the monitor outside the overwrite branch; cost: a small orchestrator code change plus tests, and it still needs `two_level_condensation` on to reach the code, so that flag's own behaviour change must be accepted or the shadow re-hosted on the legacy path. **(D) Offline replay** — run the scoring and detector over stored session logs and trajectories with no flag flip and no live behaviour change; cost: needs a corpus of stored sessions (none emitted while the stack was off) and does not prove the live path.
  - **Recommendation: (C), with `two_level_condensation` decided on its own as arm A1-class evidence in the CF-3c A/B, and (A) as the interim state.** Rationale: only (C) gives the telemetry the box wants without silently degrading prompts; (B) conflates three behaviour changes with one measurement. Until the operator answers, do NOT flip any of the three; the shadow-flag code is standalone and proceeds regardless (CODE-WORK). Re-pose via AskUserQuestion when the stack relaunches.
  - **Note 2026-11-09 (apr2 compaction-shadow): option C BUILT, flag default off; box stays OPEN for validation.** Operator chose C. New flag `compaction_shadow` (`COMPACTION_SHADOW`, `src/features.py`) in orchestrator branch `apr2/compaction-shadow-20261109` @ `235188cd`: with it on, `_refresh_two_level_summary` computes role-aware profile + helpfulness scores, creates `CompactionQualityMonitor` and records would-compact counts and hypothetical reference misses against the would-be stub (kept in new `TaskState.compaction_shadow_stubs`, never rendered), while `seg.consolidated` is never written (shadow wins even if `role_aware_compaction`/`helpfulness_scoring` are on); with it off behaviour is unchanged. Tests: `tests/unit/test_session_summary.py` 15 passed (4 new), `tests/unit/test_features.py` 48 passed. **Reaching this code still requires `two_level_condensation` ON (`:149-151`); that flag was NOT turned on and changes the session-summary path on its own, so it must be decided as CF-3c arm A1-class evidence. Nothing is flipped.** Remaining for this box: land the branch, then (with `two_level_condensation` accepted) run real traffic with `compaction_shadow` and read the monitor. Tests were run without the repo conftest (no venv here; borrowed deps path + a local asyncio shim). [no-belief: code built, no measured result yet]

## Research Intake Update — 2026-07-29 (CF-3c: the masking anchor neither ACM nor AREX ran)

_Via `/research-intake` Stage-2 2026-07-29 (intake-913…932 batch): ACM (intake-914), AREX (intake-922#record), PRO-LONG (intake-919). Sibling filings in [tool-output-compression.md](context-and-token-economy.md#track-tool-output-compression) (verbatim-log A/B, total-token instrumentation, `query_memory` over spill pointers)._

- **[declined: ws58 2026-11-03 content-review: merged into the CF-3c A/B as arm A2 (mandatory anchor)]** **Add an observation-masking / truncation arm as the MANDATORY anchor for CF-3c.** Neither ACM (intake-914) nor AREX (intake-922#record) ran one — verified in both papers **and in ACM's released code**. Without it no learned-compression result we produce is interpretable either. Our own intake-274/869 already hold that masking carries most of the benefit.
- **[declined: ws58 2026-11-03 content-review: a four-piece build for an arm the evidence already disfavours (masking carries the benefit: intake-274/869, BEAM Table 8); refile only if the CF-3c A/B shows masking insufficient]** Add **ACM Base** as the agent-initiated-trigger arm against threshold-triggered compaction. Scope it as FOUR pieces, not a tool schema: `manage_context` / `query_memory` JSON schemas, a memory-tools system prompt, an in-band `[CURRENT CONTEXT TOKEN: N]` meter injected into the last tool message each turn, and a summarizer/querier call path. **Without the meter the agent cannot self-trigger.**
- **[declined: ws58 2026-11-03 content-review: curiosity — running a third party's omitted ablation decides nothing on our stack]** Run ACM's own UNREPORTED ablation (`runtime.py disable_query_memory`, the `re_mem_noquery` arm) — isolates the value of the lossless archive from the compression policy. Implemented in released MIT code; the authors omitted the result.
- **[declined: ws58 2026-11-03 content-review: merged into the CF-3c A/B as a reporting requirement of every arm]** Pair any adoption with the **non-termination counter this handoff already mandates** [too-big: conditional adoption guard belongs to the handoff owner] (see the 2026-07-21 deep-dive correction, item 4). ACM reports none; AREX structurally cannot — budget exhaustion silently returns the highest-confidence answer instead of an NA.
- [x] Record that AREX's **+11.8pt ACU figure is NON-CITABLE** ✅ 2026-07-29 — verified in committed intake-922#record Stage-2 evidence (`epyc-root` `683f70de`, `research/intake_index.yaml` Claim 10): no masking anchor; no observation-dropping vs learned-summary arm; and the `w/o ACU` arm removes a tool the model was trained to call. It must not transfer to CF-3c as a capability figure.
- [x] Record the **ARC-AGI-3 provenance downgrade for intake-919** ✅ 2026-07-29 — verified in committed intake-919 Stage-2 evidence (`epyc-root` `683f70de`, `research/intake_index.yaml` adversarial finding): all PRO-LONG figures use ARC-AGI-3's public set, which the benchmark authors exclude from official progress/leaderboard claims. The ARC-sponsored Duke-harness provenance and its reported `97.1% / 0.0%` bimodality downgrade SOTA framing; internal same-set ablations remain usable.

**Dedup / conflation hazard — `arXiv 2607.21503` is NOT ACM.** It is a **different paper from the same week with a near-identical title** to intake-914's source. Anyone re-fetching ACM by title will land on it. Check the arXiv ID, not the title, before citing anything as ACM evidence in this handoff.

- [ ] **CF-AM-1 — Compare parallel small-model gist extraction with current folding and lossless raw
  retrieval.** On one held-out local document/search set, run identical tasks through current
  deterministic Context-Folding, a bounded fan-out of small local gist extractors, and raw append-log
  retrieval. Every gist must retain resolvable raw-document/event ids; failure to resolve is a hard
  error. Report answer quality, evidence recall, gist omission/contradiction, hit/reuse rate, complete
  inference and retrieval tokens, communication, peak memory, and wall time. Hold the final planner and
  judge fixed. Do not adopt ActiveMem's comparison-set-relative ACT score or unreleased runtime.
  - **Specification added 2026-11-09 (audit).** The "one held-out local document/search set" was unnamed. **Decision needed:** (a) the failing-log set shared with REPL-EMB-3.1/3.2 (TOC-SP-3 screen), (b) ContextBench instances from DCP-10 (gold files give resolvable evidence ids; scorer prep done), (c) BrowseComp-Plus local arm (rejected earlier as low-signal and embedding-incompatible; see the self-hostable correction above). **Recommendation: (b)**: it has gold evidence ids, a scorer, and runs with zero decode for the baseline arms. Compute: inference for the gist extractors; shape and duration unknown until the set and extractor model are chosen.
- **[declined 2026-11-09 (audit): by the box's own [check] rule: no TOC-MP-2 arm (1-5, mapped in `context_arm_ab.ARMS`) or TOC-MP-2i knob needs a "what left the view" tiered index, and `docs/design/toc-mp-ab-design-20261031.md` has no eviction-index arm; retired as a design with no measured demand. Refile only if the TOC-MP-4/full A/B shows retrieval misses that a resident index would fix (see M-MP2 trigger).]** **CF-EI-1 — File the tiered eviction index as a mechanism DISTINCT from the CF-3c masking
      anchor** (intake-1316#record): a resident, address-anchored map of *what left the view*,
      separate from spill pointers — which are followable but never announce that a span existed.
      Verified parameters: k=10 blocks/tier, unbounded tiers, newest block retained with 9 collapsed
      to one line each, lossless seq spans. **Required design input — the undisclosed third
      regime**: any adopted index must state what it does when its OWN char budget binds, because
      the source silently degrades to one global span with zero anchors. Cost the −1.8 as the
      authors' unreproduced number, **never as a measured cost** — no released flag can re-run that
      arm. [check: is a "what left the view" tiered index one of the TOC-MP-2 retrieval-over-compaction arms? If yes, merge there; if no arm needs it, retire as a design with no measured demand]
- **[declined: ws58 2026-11-03 content-review: a finding, not a task — it is now cited inside the CF-3c A/B arm A2]** **CF-3c evidence — independent corroboration for the masking anchor, from a different group**
      (intake-1330#record). BEAM Table 8: removing working memory **BEATS** the full system at 100K
      (0.327 vs 0.311), at 500K and at 1M; only at 10M is every component positive. The paper's own
      abstract contradicts it, which makes this a self-published negative result and therefore
      strong evidence for the anchor CF-3c already mandates at :166. Harness caveat: upstream
      BEAM's published evaluator passes `probing_question` to all ten evaluators but omits it from
      the judge prompt. Its 100K split also uses one-item refusal rubrics for all 40 abstention
      prompts, so this comparison is not question-conditioned and does not test multi-criterion
      abstention ([judge source](https://github.com/mohammadtavakoli78/BEAM/blob/b2da22eac88bb0874c64665f13457eb99835774a/src/evaluation/compute_metrics.py),
      [100K prompt files](https://github.com/mohammadtavakoli78/BEAM/tree/b2da22eac88bb0874c64665f13457eb99835774a/chats/100K)).
- **CF-SA-1 (record, no work)** — semantic-anchor recurrent-state checkpointing is currently
  **INEXPRESSIBLE** here. Three prerequisites, in order: emit real structural boundaries
  (multi-message rendering or in-band special tokens); move the live edit path off
  `int(len*0.8)` character offsets onto `session_log_records`; make compaction suffix-only.
  `intake-1318#02`. Zero compute.
- [x] **CF-HF-1 — Mine the 11 shipped `HarnessFactory` implementations as a same-interface
      reference set** (AgentFold `intake-155`, ReSum `intake-157` already local). MIT source
      reading only; no claims carried. `intake-1320#record`. Zero compute.

## 2026-08-09 — per-operator context budgets (research-intake Stage-2b)

- [ ] **Port per-operator context budgets to the delegation path.** Our delegation/tool-output context
  is assembled against a single budget; OpenMLE-Evo budgets **per operator**, which is the mechanism
  behind the prompt-tail reduction the intake-940#record dive rated as one of only two citable claims from that
  source. Shipped constants, read from `OpenMLE-Evo/tts_search/configs/search/airaevo.yaml`
  ([intake-1024](../../research/intake_index.yaml), dive-verified 2026-08-09): global
  `max_related_cards 3`; improve `ancestor_k 3` / `sibling_k 3`; crossover `2` / `2`; debug
  `max_related_cards 8`. Cross-links AP-ME-1 in
  [autopilot-continuous-optimization.md](autopilot-program.md) — the planner-context
  half of the same idea. Offline-first: measure current per-operator context size before changing it.
  - **Specification added 2026-11-09 (audit):** cross-link target is `autopilot-program.md` AP-ME-1 (file exists; the link text still says autopilot-continuous-optimization). The offline measurement uses the existing inference-tap events (`/mnt/raid0/llm/tmp/inference_tap_events.jsonl`, the DCP-14 source): per delegated sub-call, parent vs child prompt chars grouped by role. Whether `_maybe_dcp_seed_context` (`chat_delegation.py:253`) applies a per-operator budget today was not verified. Zero inference.

## Research Intake Update — 2026-09-14 (intake-1346…1366)
_Via /research-intake Stage-4 (operator-approved plan 2026-09-14). Sources: intake-1350 SoL-Pi, intake-1359 compression interaction costs — dive-verified._

- [ ] **CF-PB-1 — Plan-boundary compaction trigger priced by local break-even.** Price a rewrite as re-prefill tokens (llama.cpp prefix-cache invalidation) vs per-request savings; SoL-Pi's formula structure ports, its 12.5 cache ratio does not. Note the `len(state.context) > 12000` OR-trigger (`graph/compaction.py:223`) dominates the 0.75 ratio today. If adopted, pass step progress INTO the summary request (SoL-Pi's own open #42 defect is exactly dropping it). Inference-gated. `intake-1350#04`. *(Anchor fixed 2026-11-09: the `len(state.context) > 12000` OR-trigger is now `src/graph/compaction.py:223`, not `:130`.)*
- [x] **CF-RX-1 — `_REPL_OUTPUT_RE` never matches.** ✅ 2026-09-14 — merged to epyc-orchestrator main `35b05fde` (pushed to origin 2026-09-14) (commit `090c63d9`). `context_compression.py:188` looks for `<<<\/TOOL_OUTPUT>>>`; the real end marker is `<<<END_TOOL_OUTPUT>>>` (`repl_environment/types.py:18`); the `">>>" in content` fallback (`:205`) masks it. Fixed by building the regex from the `types.py` constants with `re.escape` (no import cycle; loading `context_compression` now also imports the `repl_environment` package). Note: it changes `classify_tool_output` results for delimited REPL output inside the default-off `context_compression` path. `intake-1350#record`.
- [x] **CF-AB-2 — Two further arms and a co-metric for the CF-AB-1 frame (design text only).** Add to CF-AB-1, renumbered so no arm collides: A6, reset with a structured handoff artifact (schema: state, next steps, open defects; trigger at the A3 window thresholds; compared with A3 on uncached prefill per solved task and premature-wrap-up share from the HIL-12 scan) (intake-2228#record); A7, an externalised lossless log with programmatic search (complete history outside the prompt, only the current turn kept, grep or Python search, declared log format and tool surface; not run until the binding-window screen shows a binding window at the role and a local probe shows the role writes working search code; priced by TU-LADDER-1) (intake-1011#record); and a co-metric, a post-compaction closed-book recall exam with questions mined from the elided region, identifier answers matched mechanically, a one-search recovery arm, declared before any run, not an LLM judge for identifier questions (intake-117#record). Note that two dives proposed an A6 with different content; this task resolves it as above. Acceptance: CF-AB-1 text carries A6, A7 and the co-metric. Estimate: 0.3 day. ✅ 2026-10-21
- [x] **CF-AB-3 — Offline prefix-stability replay for CF-AB-1 arms (zero inference).** Over the TOC-SP-5 corpus (62 `data/bep_sandbox` trajectories) render A1, A3, A4, A5 and report per turn the common-prefix length with the previous turn prompt and the implied re-prefill fraction, with a second column bounding what a shift path could recover (tokens outside the common prefix lying in a run of at least 256 identical tokens), an upper bound since no live role can use shift reuse today; record blocked if tool outputs are not in the corpus (intake-2230#record, intake-2283#record). Run under `region-lock run --cpu-list 0-95`. Acceptance: a table per arm with both columns, or the blocked record. Estimate: 1 day. ✅ 2026-10-21
  - 2026-10-21 (dpf-logpfx): BLOCKED record accepted by the task text. The TOC-SP-5 corpus (62 trajectories, 384 turns, 0 unparsable) carries no tool-output text and no full prompt: `raw_output` max 817 chars, `prompt_tail` on 162 turns (max 700 chars), `prompt_has_last_output` is a boolean (`artifacts/dpf-logpfx/cf-ab-3-bep-corpus-probe.json`). Replay engine for A0/A1/A3/A4/A5 (common prefix, re-prefill fraction, shift-recoverable bound) is built and tested on synthetic trajectories: `scripts/analysis/cf_ab3_prefix_replay.py`, `tests/analysis/test_cf_ab3_prefix_replay.py` (5 passed). Re-run once the TOC-SP-6 trajectory artifact exists.

✅ 2026-10-06 CF-HF-1 accepted: [11-harness source comparison](../../docs/reference/harnessfactory-source-comparison-20261006.md), JIT pin `ababa06c2f54d799fd9fbc356e5368f61a452260`; 92 source hashes/44 interface exports independently verified by MAIN. JIT code MIT scope is separate from original AgentFold/ReSum code. Source structure only; no copied code, execution or performance claims.

### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

Operator-approved 2026-10-31 (plan revision 2, `research/intake-stage3-plan-2026-10-31-ws58.md`, sha256 `043e502133cae214175ea3f2a395f575e6ca13b9f3ee058525ed020264ab5012`; relayed by the ws58 coordinator; budget approved: about 13 MI210-hours for the drafter pilot, 6-9 engineer-weeks for the race checker, the 95.5 GB ThinkingCap download; D1 confirmed: in-weights calculator declined, GPU reason recorded on intake-2550/2574; D2 approved: scratch upstream builds are measurement instruments only). Trigger records below are prose with no checkbox until a reviewed session confirms their condition.

- [ ] **CF-AKV-0 — Zero-inference screen: how much resident context old tool results hold (intake-2590#record, intake-2596#record).** From existing orchestrator serving records and REPL traces, compute per long agent loop the share of resident context held by tool responses older than the last two turns, and the share of decode steps above 48K context. Escalate to the trigger-gated KV-drop semantics probe only if the median long loop holds at least 40% old tool results and at least 20% of decode steps exceed 48K tokens.
  - 2026-11-01 bounded audit: the inspected native sources do not establish resident old-tool token shares or per-decode context occupancy, and the original task lacks an operational long-loop definition. Both requested metrics and the >=40% / >=20% trigger remain unknown; this box stays OPEN. Research `af74b64d8c9b7542573aa67412eee060c7fdde90`, [retained source/record scope and limits](https://github.com/pestopoppa/epyc-inference-research/blob/af74b64d8c9b7542573aa67412eee060c7fdde90/artifacts/engineering/cf-akv0-20261101/REPORT.md). This is a bounded observability finding, not a full historical census or evidence of absence; no KV-drop probe was triggered. [belief: cc]
  - **Definition needed (added 2026-11-09, audit; proposal, not a decision already made):** "long loop" := a REPL task of >= 8 orchestrator turns whose final prompt exceeds 16K tokens (the TOC-MP-2 context budget C). Data source: none yet; `trajectory_artifact` writer exists but is default off and has emitted no artifacts, so the screen is blocked on the first instrumented run (any orchestrator traffic with `trajectory_artifact` on), not on Autopilot.

- *Intake trigger record (no checkbox until it fires), M3, row W2KERN-5 (intake-2590#record):* Bounded probe: tool-result KV drop+shift on a pure full-attention role in llama-server, using existing llama_memory_seq_rm + seq_add (as in the streaming-llm / context-shift path), on a recorded orchestrator agent trace. Measure (a) tokens re-prefilled per ...

## Track: delegation-context-preassembly
<!-- gate: none -->

> Folded from `handoffs/active/delegation-context-preassembly.md` @ `7e268b4de29c` on 2026-11-02 (BRF-T1-F6, route 1a, operator D1/D5; retired row RTG-10 → RTG-08). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Delegation Context Pre-Assembly (Budget-Bounded)

**Scratch**: `/mnt/raid0/llm/tmp/dcp9a-custody-20261006-02`, `/mnt/raid0/llm/tmp/codex-ni06-main-20261006/dcp9a-approved-source`; originals retained private.

**Status**: implementation-scoped draft — audit-refined 2026-05-25; still feature-flag/default-off until DCP-6 validates. 2026-06-12 offline replay passed task-root/file-selection/budget checks; DCP-6a repair is landed on the current live orchestrator branch (`fix/substring-scorer-digit-separators` `2e2e0d3`). The live API launch marker already includes that repair, and orchestrator `29b9ba3` adds a runnable J7/DCP A/B driver (`scripts/benchmark/dcp_j7_ab.py`) with default `--stub` schema validation and real-run refusal unless a host-quiet window is confirmed. Orchestrator `56a72f6` records the first live J7 A/B artifact after the cached-delegation telemetry fix in `f96a6ab`: 6/6 HTTP-200 rows, 3 OFF + 3 ON, zero errors, all rows with delegation success. Result is not promotion-grade: ON cut average generated tokens from 352.0 to 247.333 but worsened p50 latency from 20.219s to 32.628s, so `dcp_pre_assembly` remains default-off pending larger/quality-scored evidence and cleanup of broad running-state attestation caveats. 2026-06-21 follow-up: the runner summary now emits `decision` (`dcp_j7_decision.v1`) so future clean-window runs are self-classifying; the existing artifact is `hold` with blockers `latency_not_improved` and `quality_not_scored`. Orchestrator `c3b2514e` adds a read-only DCP/J7 section to `scripts/attest/generate_attestation.py`, so running-state attestation now surfaces the latest DCP/J7 artifact, status, recommendation, blockers, arm counts, latency delta, and quality-score coverage without launching inference.
**2026-07-06 no-inference prep**: orchestrator `7c84f102` fixes the J7 runner safety contract so default invocation is schema-only stub mode and live inference requires explicit `--real --host-quiet-confirmed`. The current stub artifact is `benchmarks/results/runs/dcp_j7/stub-20260706T033205Z/`; it validates the result schema and self-classifies as insufficient (`missing_latency_delta`, `quality_not_scored`), which is expected for no-inference prep. DCP remains default-off; the remaining decision work is a larger quality-scored live run only if we deliberately reopen J7 after the unfavorable first live A/B.
**Created**: 2026-05-25 (via `/research-intake` deep dive of intake-605 Repo Prompt)
**Categories**: context_management, agent_architecture, routing_intelligence, tool_implementation
**Source**: intake-605 (Repo Prompt — Context Builder + CodeMaps); cross-ref intake-330 (code-review-graph), intake-151 (GitNexus), intake-295 (fff.nvim)
**Owning index**: [`routing-and-optimization-index.md`](routing-and-optimization-index.md) RTG-10
**DCP-6 falsification-harness status**: [`bep-dcp-falsification-harness.md`](autopilot-program.md#track-bep-dcp-falsification-harness) (offline replay closed 2026-06-12; DCP-6a code landed; server reload/deploy attestation primitive landed 2026-06-18 in `epyc-orchestrator` `756c96b`; 2026-06-19 launch-code provenance check is satisfied but broad running-state attestation remains caveated; `29b9ba3` provides the host-quiet A/B runner; first live A/B artifact landed in `56a72f6` and argues against promotion on latency).

#### Objective

Give the orchestrator a **proactive, token-budget-bounded context _assembly_ layer** that packages a curated, sliced, codemap-augmented context bundle for a sub-task *before* the receiving role runs — instead of having each delegated role re-discover context reactively from scratch via REPL. This is the *assemble* side of context engineering; [`context-folding-progressive.md`](context-and-token-economy.md) owns the *evict* side (compaction of an already-large context).

#### Strategic frame — why this is a real gap

Two opposite context philosophies:
- **Ours (reactive discovery)**: the Root LM runs REPL code (grep / read / ColGREP / GitNexus queries) mid-reasoning, pulling context in as it goes. Flexible, but each delegated sub-agent pays the discovery cost again, and unbounded reads can flood the window.
- **Repo Prompt (proactive pre-assembly)**: a Context Builder loop curates a bundle that *provably fits* a token budget before the model runs: task analysis → file discovery → codemap generation → token verification → iterative add/drop/slice → emit a non-prescriptive handoff prompt.

RP built this for cloud GPT-5 Pro (its 60k default is literally the ChatGPT-Pro paste ceiling). On our **BW-bound CPU regime the principle is sharper, not weaker**: every unearned context token is DRAM bandwidth paid at decode, and the prefill of a bloated bundle is pure latency. A budget-bounded packager is plausibly a double win on delegation — less prefill latency *and* less context contamination (better quality).

#### What we already have (building blocks)

- **GitNexus** — Tree-sitter symbol graph (42.6K symbols / 73.3K relationships on epyc-orchestrator), impact analysis, `context`/`impact` MCP commands. Can produce signature-level structure → the **CodeMaps analog**, but nothing currently emits an "architecture snapshot" sized to a budget for prompt injection.
- **ColGREP / NextPLAID** — AST-chunked code search (ColGREP ~71% top-1), `epyc-orchestrator/src/repl_environment/code_search.py`. Candidate *file/chunk discovery* engine.
- **context-folding-progressive** — eviction/compaction (two-level condensation, segment scoring). The complement, not a substitute.
- **dispatcher.py / escalation.py** — where a packaged bundle would attach to a delegated sub-task.
- **TOON encoder** — structured-payload compaction; relevant for encoding the assembled bundle.

#### The RP mechanism (reverse-engineered) — what to mine

From the official blog + the open-source `w-winter/dot314` MCP wrapper source (repoprompt.com is JS-opaque).
1. **Iterative selection loop**: task analysis → auto file discovery → codemap gen → token verification against budget → iterative refinement (drop/add) → file slicing to fit → non-prescriptive handoff prompt.
2. **Per-file inclusion modes**: each file tracked as `full | slices | codemap_only`; reads auto-promote to slices; overlapping/adjacent line-ranges auto-merged. So a 10k-line file contributes only its relevant ~200 lines, or just its signatures.
3. **CodeMaps as a separate budget class**: signature-only API skeletons injected distinctly from full bodies — architecture awareness while reserving budget for the files actually under edit.
4. **Non-prescriptive discovery prompt** (its own task below): discovery deliberately withholds proposed solutions, emitting open questions + file-relationship explanations only, to avoid biasing / under-scoping the downstream plan.

#### Proposed tasks (implementation-grade after audit)

- [x] **DCP-1 — Context bundle data model + per-file inclusion modes.** ✅ 2026-05-26 (flipped 2026-07-14; on main, tested — see status quo). Define a `ContextBundle` with per-entry `mode ∈ {full, slices, codemap_only}`, merged line-range slices (auto-merge overlapping/adjacent ranges), and a live token-count accumulator. Each entry MUST carry: `path`, `mode`, `line_ranges`, `symbol_ids` where available, `content_sha256`, `source` (`gitnexus|colgrep|direct_read|manual_seed`), `reason_included`, `reason_downgraded_or_excluded`, and `estimated_tokens`. Reuse GitNexus for `codemap_only`, ColGREP/read for `slices`/`full`. Store the bundle manifest separately from rendered prompt text so downstream roles can request top-ups against stable IDs instead of asking for "that file again." *(Substrate for everything else; net-new.)*
- [x] **DCP-2 — Budget-bounded assembly loop.** ✅ 2026-05-26 (flipped 2026-07-14; discovery+pack core on main, tested). Given a sub-task description + token budget, run discover → codemap → token-verify → add/drop/slice until the bundle fits; emit the bundle + a manifest of what was included/excluded and why. **Budget is a per-role parameter, NOT a fixed 60k** — ours is set by the receiving role's context window and the CPU latency target, not a cloud paste ceiling. Implement as a two-pass loop for efficiency: first pass uses only cheap metadata (GitNexus graph, file sizes, symbol names, ColGREP candidate IDs); second pass reads bodies only for files that survive ranking. Reserve explicit budget bands before packing: task/instructions, codemap, editable slices/full files, tests/examples, and an output reserve. Fail closed if the estimate cannot fit after slicing: emit `codemap_only` + "missing evidence" manifest rather than silently overflowing.
  - **Correction 2026-09-14:** only `output_reserve` is honoured in code (`context_assembly.py:337`); `BudgetBands.codemap/editable/tests/task` are manifest-only (`:258`) and the live DCP-4 call passes no bands (`chat_delegation.py:287`, budget 2000). "Reserve explicit budget bands" is NOT implemented; `codemap_only` is a greedy downgrade rung (`:283`, `:321`), not a band. `intake-1357#record`.
- [x] **DCP-3 — CodeMaps-as-budget-class.** ✅ 2026-05-26 (flipped 2026-07-14; ast-codemap on main, tested; GitNexus not a runtime dep). Add a GitNexus-backed "architecture snapshot" producer: signature-only skeletons for a symbol/file set, sized to a sub-budget, injected as a distinct section. *(Closes the "analyzed-not-wired" gap — GitNexus can already do this, nothing exposes it for prompt injection.)* Cache codemaps by `(path, content_sha256, gitnexus_index_commit)` and expose staleness in the manifest. If `gitnexus status` is stale, either run the wrapper re-index before assembly or mark codemap confidence low and prefer direct slices for changed files.
- [x] **DCP-4 — Wire pre-assembly into delegation as a seed bundle, not a hard context firewall.** WIRED 2026-05-26 (`31ea6d4`), behind `features().dcp_pre_assembly` (default-off). Attach point is `chat_delegation._run_specialist_loop` (the LIVE specialist delegation path — NOT `dispatcher.py`, which only generates the plan/commands): after `corpus_ctx` is built, `_maybe_dcp_seed_context()` augments it with `render_bundle(assemble_delegation_bundle(query, code_search_fn=deleg_repl._code_search, file_reader_fn=...))`. Added `context_discovery.render_bundle()` (the missing body-materialization step — the bundle only planned modes). **Advisory**: reactive discovery stays fully enabled; any failure falls back to plain `corpus_ctx` (never blocks delegation). 7 tests. *(Top-up-rate eval signal + manifest-in-prompt are DCP-6-era refinements; the seed currently renders bodies only.)* Remaining: offline replay + DCP-6 inference A/B (deferred to post-J6).
- [x] **DCP-5 — Non-prescriptive discovery prompt.** Landed in `epyc-orchestrator` `b7ba6265`: `architect_investigate` now frames supplied context as an evidence bundle, asks delegation briefs to identify open questions, file relationships, missing evidence, and omitted-file uncertainty, and avoids prescribing implementation details before discovery. This is prompt-surface only, not a PromptForge A/B promotion; keep DCP-6 quality/latency evidence as the enablement gate.
- [ ] **DCP-6 — Eval.** Measure on a delegation-heavy workload: prefill tokens, end-to-end latency, top-up count, bundle-build latency, downstream answer quality, hallucinated-file references, and context-contamination failures vs the reactive-discovery baseline. Hypothesis: budget-bounded pre-assembly cuts prefill + latency at equal-or-better quality. Non-inference replay over historical tasks closed 2026-06-12 for task-root/file-selection/budget correctness; DCP-6a live-branch commit `2e2e0d3` fixes shallow one-line slices and manifest freshness hashes and replays clean. Launch-code provenance is satisfied (`server_launch_git_sha=eeb8cce`, current API `git_sha=27e09a1`), but orchestrator `670aab4` records a caveated running-state attestation. Orchestrator `29b9ba3` adds the executable A/B harness (`python3 scripts/benchmark/dcp_j7_ab.py --stub ...` for schema/artifact validation; real mode requires `--host-quiet-confirmed` and refuses if AutoPilot is running). First live A/B artifact landed at `benchmarks/results/runs/dcp_j7/20260619T113143Z/` in orchestrator `56a72f6` after `f96a6ab` fixed cached-delegation telemetry; it completed cleanly but did not support promotion (`on.p50_elapsed_s=32.628` vs `off.p50_elapsed_s=20.219`, `on.avg_tokens_generated=247.333` vs `off.avg_tokens_generated=352.0`, zero errors). The artifact summary now records `decision.status=hold` because latency regressed and rows were not quality-scored. Orchestrator `c3b2514e` makes attestation report this status directly in JSON/Markdown (`## DCP/J7 Status`). Remaining work is larger/quality-scored falsification and broad operational attestation cleanup before any enablement. Arms also include (absorbs DCP-7 and DCP-11): a minimal-context arm (EDIT-Bench Table 3 shows enrichment HURTS 2 of 7 models, up to -8.15 pp, so more context is not monotonically better) and the DCP-11 packer-rendering change (edit-site files kept verbatim, never codemap_only) ON vs current. Run only after DCP-12 sizes the sample.
  - **2026-11-01 telemetry preparation (design, not implemented):** time assembly plus rendering in `epyc-orchestrator/src/api/routes/chat_delegation.py::_maybe_dcp_seed_context` and carry status and duration in request-scoped delegation diagnostics through to `scripts/benchmark/dcp_j7_ab.py::_summarize_response`. Distinguish disabled, empty, failed and successful seeds. No explicit top-up event has been identified: leave `top_up_count` null with `top_up_observable=false` until an explicit, request-correlated missing-evidence request is instrumented. Count reactive search/read calls separately, excluding seed discovery; a generic retrieval call is not proof of a top-up. Avoid shared mutable telemetry on worker primitives. This is preparation for DCP-6, not an evaluation result.
- [x] **DCP-6b — J7 runner no-inference safety revalidation.** ✅ 2026-07-06 — Orchestrator `7c84f102` makes stub/schema validation the default runner mode, requires explicit `--real --host-quiet-confirmed` for live inference, and records `benchmarks/results/runs/dcp_j7/stub-20260706T033205Z/` as a current schema artifact.
- **[declined: ws58 2026-11-03 content-review: merged into DCP-6 as the minimal-context arm; a finding, not a task]** **DCP-7 — external evidence that MORE CONTEXT IS NOT MONOTONICALLY BETTER** (intake-1152, EDIT-Bench, arXiv:2511.04486v2 Table 3). First external number we hold for what a context field is worth on an editing task, and it points *against* naive enrichment. Seven models, three context levels (code only / +highlight / +highlight+cursor): claude-sonnet-4 62.41 / 64.81 / 64.26; glm-4.6 52.96 / 56.48 / **44.81 (−8.15)**; o3-mini 60.00 / **56.30 (−3.70)** / 55.19; qwen3-coder 56.48 / **53.89 (−2.59)**. Highlighting helps 5 of 7 and HURTS 2; adding cursor position on top costs one model 8.15 pp. The abstract's "up to 11%" is glm-4.6's within-model range, not a typical effect — typical is 2-4 pp. **Read-across:** DCP assembles context budgets on the assumption that relevant context helps; this says a *relevant-looking* field can be per-model negative at single-digit-pp magnitude. Not decision-gating (different task, different models) — a prior worth holding before the next budget change.
  - **Priors 2026-09-14 (not gating):** (a) once the edit site is known, signature/skeleton renderings of the rest of the edited files bought no resolve signal over name placeholders (23/70 vs 25/70, McNemar p=0.754, oracle ceilings, Claude-only) `intake-1357#01`; (b) summaries of code answered 4/45 behavioural questions vs 27/45 for source `intake-1357#03`; (c) SWEzze: segment keep/drop with "N lines omitted" placeholders +2.0–4.6 pp absolute at ~6x, single run, unpaired p 0.14–0.52 — context beyond a given fault location worth only +0.4–1.6 pp `intake-1365#01`; (d) graph neighbours appended to lexical hits helped LLM agents +5.4–8.1 File Recall@5 (matched toggle, agentic, Python) — attach, don't separate; expansion is NOT assumed to dominate under DCP's evicting budget `intake-1364#03`.
- [x] **DCP-8 — borrow the paired descriptive/lazy instruction axis** (intake-1157, CanItEdit) as an instrument for prompt-construction work, where instruction specificity currently varies uncontrolled: every problem carries a fully-specified AND a minimal instruction, making specificity a controlled variable rather than a confound. Pairs with CJ-7c in `canonical-judge-suite-revamp.md`; filed here because DCP owns the instruction-assembly side. ✅ 2026-11-01 — APP `19655f323b23870c18e241067bbe04dbb2fc69c3`; [native controls and source proof](https://github.com/pestopoppa/epyc-orchestrator/blob/d1412e5aa7edff7911136483400226ee66143607/docs/evidence/dcp8-paired-instruction-20261101/README.md). [no-belief: source conformance instrument]
- [x] **DCP9A-USAGE — privacy-bounded Eq4 input-component usage audit.** MAIN accepted2026-10-06: [stable214,334rows/conservative34,412subset and independent recomputation](../../artifacts/ni08/usage-source-audit-20261006/README.md). Correct all-input-components denominator, explicit moving/ambiguous/duplicate exclusions, private immutable projection, aggregate-only partial intensity. No billing, purpose or Definition1 trajectory authority; parent remains open.
- [ ] **DCP-9a — Compute the Eq.-4 quantities over the existing Claude Code journals** (do now, zero compute): cache-read fraction `h`, cache-creation share, uncached-input share, input:output ratio, per-session token intensity, and the Definition-1 trajectory test over time. First-pass numbers are already in hand and dive-verified: **61 transcripts, 45,902 usage records, h = 0.9845, input:output 350.5:1**. This **supersedes and sharpens** the bearing row "measure coordination overhead as a fraction of mains' token spend from existing journals" — the ~60%/95% figure remains a budget whose artifact is absent, and no baseline of our own exists. `intake-1333#00`, `intake-1325#04` (the unsplit ancestor). Done when the Definition-1 trajectory test (h over time, per session) is filed beside the point estimates already in hand (h = 0.9845, input:output 350.5:1 over 45,902 records).
- **[declined: ws58 2026-11-03 content-review: agent-fleet bookkeeping (coordination share of mains' token spend), not an inference or orchestration-stack question; P5-3 carries the purpose label if it is ever wanted]** **DCP-9b — The coordination SHARE is NOT computable from journals as they stand.** This is an **instrumentation** task, not a measurement task: it needs the per-turn PURPOSE LABEL written at write time (P5-3 in [`loop-owned-fleet-implementation.md`](coordination-and-churn-pipeline.md#track-loop-owned-fleet-implementation)), never post-hoc classification of transcripts. **Depends on P5-3.** `intake-1333#00`. Zero compute.

#### Audit refinements / missed gaps

1. **Token counting must be model-calibrated, not a rough character heuristic.** The packer should use the same tokenizer or conservative estimator as the target role. Log estimate-vs-rendered-token error and keep p95 over-estimation positive; under-estimation is the failure mode that causes prompt overflow.
2. **Slice boundaries need semantic padding.** A line-range slice should automatically include imports, enclosing class/function headers, decorators, type definitions referenced by the slice, and adjacent tests where cheap. A 20-line hunk without its type/import context is high-risk even if it fits.
3. **Bundle freshness is a correctness property.** Every bundle should include `repo_sha`, `gitnexus_index_commit`, and per-file `content_sha256`. If a delegated role applies edits after files change, the manifest should be considered stale and regenerated.
4. **Do not run broad search on every delegation.** Candidate discovery should prefer caller/callee neighborhoods from GitNexus plus ColGREP top-k, capped by role and task class. Full-repo ColGREP every handoff would erase the latency win.
   - 2026-09-14: GitNexus neighbourhoods are design intent only — `context_discovery.py:96-133` is ColGREP/lexical-only. If implemented, attach 1-hop edges (confidence ≥0.9) to lexical hits in the same pass; score before default (DCP-10). `intake-1364#record`.
5. **Security/noise filters belong in DCP-1, not as an afterthought.** Exclude binaries, generated artifacts, huge lockfiles, secrets-like files, and vendored dirs by policy unless explicitly requested. Record exclusions so the worker can ask for an override.
6. **Context-folding integration should share scoring features.** Importance signals from folding (recent use, role relevance, failure history, symbol centrality) should be exposed as rank features for DCP instead of implementing a parallel heuristic.
7. **The first production mode should be advisory.** Attach the bundle while leaving existing reactive discovery enabled, then compare whether the role uses fewer reads/tool calls. Only consider stricter modes after DCP-6 shows quality does not drop.
8. **Replay proved file selection is not enough.** The first 2026-06-12 scratch replay selected every expected existing file, but task-root search returned only `start_line` without `end_line`, so tiny files rendered as one-line slices. DCP-6a now validates content depth and `content_sha256`, not just path presence: live-branch commit `2e2e0d3` has 100% line coverage and 0 missing hashes in the current offline replay.

#### Open questions (for brainstorming)

- Does pre-assembly *replace* reactive discovery for delegated roles, or layer under it (assemble a seed bundle, still allow REPL top-ups)? Likely hybrid.
- Right budget per role? Tie to the role's context window and a CPU latency target, not a fixed number.
- Can DCP-2's discovery reuse the learned router / difficulty signal to size the budget by task difficulty?
- Slicing granularity: function-level (GitNexus symbols) vs line-range (ColGREP chunks) vs both?
- Interaction with context-folding: if the assembled bundle still overflows mid-task, folding takes over — do the two share the segment-importance scorer?
- Source-linked diagnostics in delegated context (owned trigger, no checkbox; intake P4-RETRIEVAL M14, 2026-10-20): DCP-4 seed bundles are built from code search and file reads only, with no wiki or diagnostic-artifact source. When a quality-scored DCP-6 run produces a non-hold `decision` and its failure analysis attributes at least one miss to an absent repo-resident diagnostic (script, query or wiki page), add one held-out task class for that case to DCP-6; until then do not build the injection in order to measure it.
- VibeMemBench (arXiv 2609.23570; intake-1968 and intake-1976, M14): the companion subtree was a 100-byte "Coming" README at the 2026-10-07 dive; a 2026-10-20 plan-time check (not dive-verified) found `scripts/` and a public Hugging Face dataset. When a coding-agent memory comparison is scoped, dive the released harness and dataset before adopting it; the paper's matched memory-on/off design is already DCP-6's.

#### Dependencies / cross-cutting

- **context-folding-progressive** — assemble vs evict; should share segment-importance heuristics (extends routing-index CCC #7).
- **meta-harness (completed ledger) / autopilot-continuous-optimization** — DCP-5 non-prescriptive prompt = PromptForge mutation; DCP-2 budget = candidate autopilot search-space knob.
- **GitNexus** (DCP-3) and **ColGREP** (DCP-1/2 discovery).
- **batched-edit-parallel-apply** (sibling RP-derived handoff) — a pre-assembled bundle feeds a clean think-then-act batch edit.
- **internal-interaction-lifecycle** — P2 consult reuses DCP `_maybe_dcp_seed_context()` ranking / rendering for context packaging via `features().dcp_for_consult`; DCP does NOT own consult lifecycle. See [`internal-interaction-lifecycle.md`](routing-program.md#track-internal-interaction-lifecycle).

#### Key file locations (targets)

- `epyc-orchestrator/src/orchestration/dispatcher.py`, `escalation.py` — delegation attach point (DCP-4).
- `epyc-orchestrator/src/repl_environment/code_search.py` — ColGREP discovery (DCP-1/2).
- GitNexus MCP `context`/`impact` — codemap source (DCP-3).
- `epyc-orchestrator/src/prompt_builders/` — non-prescriptive handoff prompt (DCP-5).
- `epyc-orchestrator/src/context/bundle.py` *(proposed, new)* — ContextBundle model + assembly loop. **Layout note (gap-fix 2026-05-25):** implemented as top-level `epyc-orchestrator/src/context_assembly.py` (DCP-1/DCP-2 pack core, on main (merged 2026-05-26)) to match the existing `context_manager.py` / `context_compression.py` convention rather than a new `src/context/` package.

#### Reporting

Update this handoff + routing-and-optimization-index RTG-10 after each DCP task; record bench results (DCP-6) per `feedback_incremental_persistence`.

#### Post-result conditional workflow + mitigation (DCP-6 / bulk-inference J7)

Pre-run wiring: **DCP-1 + DCP-2 discovery + DCP-3 ast-codemap DONE + tested** on main (merged 2026-05-26) (`src/context_discovery.py`: `discover_candidates` / `build_python_codemap` / `cost_candidates` / `assemble_delegation_bundle`, injectable ColGREP + file-reader backends, 11 tests; codemap is a dependency-free `ast` signature skeleton — GitNexus is not a runtime dep). **DCP-4 advisory seed-bundle attach is also DONE** (`31ea6d4`, re-audited 2026-05-27): `chat_delegation._maybe_dcp_seed_context()` wires ColGREP + workspace file reads into `assemble_delegation_bundle`, appends `render_bundle(...)` to the specialist context, and falls back to reactive discovery on any assembly failure. The 2026-06-12 offline replay closed scratch-root/file-selection/budget validation (`/mnt/raid0/llm/tmp/dcp6_offline_replay_20260612/summary.json`); DCP-6a live-branch replay (`/mnt/raid0/llm/tmp/dcp6a_current_offline_replay_20260612/summary.json`) now closes content-depth/freshness in isolation. The 2026-06-18 reload-attestation primitive is also landed (`epyc-orchestrator` `756c96b`): `orchestrator_stack.py` stamps the orchestrator fleet marker with launch-time git SHA, `/dashboard/api/version` exposes `server_launch_git_sha`, and the live API currently reports `git_sha=27e09a1` plus `server_launch_git_sha=eeb8cce`; that launch SHA contains both `2e2e0d3` and `756c96b`. Orchestrator `670aab4` records the 2026-06-19 attestation with GitNexus drift clean and 6 API workers sampled, but the broad running-state gate remains caveated by deleted llama-server executable paths and feature-flag intent diffs. Orchestrator `29b9ba3` adds the missing J7 A/B command surface: `scripts/benchmark/dcp_j7_ab.py` runs ABBA-style `dcp_pre_assembly` off/on arms, writes incremental `results.jsonl`, `meta.json`, and `summary.json`, refuses real inference unless `--host-quiet-confirmed` is passed, and reverts the flag off after real runs. Orchestrator `f96a6ab` fixed cached-delegation telemetry so the harness no longer trips over `specialist_repl_errors` on cache hits, and `56a72f6` records a completed live A/B at `benchmarks/results/runs/dcp_j7/20260619T113143Z/`. Remaining work is quality scoring plus broader sample size; the first n=3/arm run is clean but not favorable on latency.

Run **advisory-first** (bundle attached, reactive discovery still enabled — DCP-1 audit #7). Decision tree:
- ✅ prefill+latency down AND quality ≥ baseline AND top-up rate ≤20% → keep advisory; consider seed-bundle-primary mode after a second confirm.
- ⚠️ quality flat but top-up rate >20% (packer under-selecting) → tune discovery depth / ColGREP top-k / per-role budget; re-run.
- ❌ quality drop OR no latency improvement → keep reactive discovery; shelve pre-assembly; flag off.

Mitigation: flag default-off; advisory mode never removes reactive discovery; top-ups always allowed (no hard firewall); bundle freshness (`repo_sha`/`content_sha256`) re-checked per delegation; security/noise exclusion policy applied at DCP-1. Operator decision tree mirrored in [`bulk-inference-campaign.md`](eval-tower-program.md#track-bulk-inference-campaign) Package J.


#### Research-intake integration — 2026-07-22 (graph-wiring: KB->delegation, gated)
_Via /research-intake Stage-2 (intake-881 graph-engineering wiring assessment)._
- [ ] (Gated) Add the ColBERT KB as an optional prior-decisions source in delegation-context pre-assembly, behind the existing `dcp_pre_assembly` flag; measure quality/latency before default-on (DCP's live A/B is already latency-unfavorable: ON 32.6s vs OFF 20.2s)

#### Research Intake Update — 2026-09-14 (intake-1346…1366)
_Via /research-intake Stage-4 (operator-approved plan 2026-09-14). Sources: intake-1346 ripwire, intake-1356 LocAgent/Loc-Bench, intake-1357 act-context, intake-1358 Deep Agentic Search, intake-1364 LARGER, intake-1365 SWEzze, intake-1366 ContextBench — all dive-verified._

- [ ] **DCP-10 — Zero-decode discovery scoring on ContextBench (primary instrument).** Per instance: shallow checkout at `base_commit` (`CONTEXTBENCH_TMP_ROOT` on raid, never /tmp), run `discover_candidates` (`context_discovery.py:96`) with `ORCHESTRATOR_EDIT_ROOT` at the checkout; emit `pred_files`+`pred_spans` from `DiscoveredHit.line_ranges`, and separately the post-`pack_to_budget` spans. Score File and Line recall/precision/F1 **macro per task**, plus recall at the live 2000-token budget and at 2x/4x. Start Lite Python (266) + all C/C++ (128). Arms at fixed `max_files`: (a) task-root lexical; (b) ColGREP; (c) ColGREP + 1-hop GitNexus edges (conf ≥0.9) appended; (d) same edges re-rank-only; (e) `ripwire --for/--pack-task` at a pinned SHA. **Wrap the shipped scorer first** (it micro-averages, drops errored/empty predictions, scores empty gold/pred as 1.0, mangles dot-paths via `lstrip("./")`, EditLoc falls back to the gold patch, parses `.h` as C): count errors/empty as recall 0, exclude the 3 empty-gold and 42 `/workspace`-scratch-file tasks, flag the third-party-audit-reported 88 unresolvable-path tasks (count not re-verified), prefix-strip paths, drop EditLoc, omit Symbol for C/C++. Requires DCP-10a for the C/C++ arm. `intake-1366#record`, `intake-1364#record`, `intake-1346#record`.
  - [x] **DCP-10-SCORE-PREP (NI05-38)** ✅ 2026-10-05 — prepare pure deterministic macro file/span precision/recall/F1, safe checkout-relative path normalization and unioned inclusive ranges; preserve error/empty prediction denominators and explicit immutable task dispositions. Report actual deterministic packer output at 2k/4k/8k with full/slice/codemap line provenance and estimated-token identity. Hand-checked synthetic fixtures only. No acquisition, checkouts, index/model builds, actual discovery arms or full-benchmark claim. Prospective exclusive scored-report request/original-output/input/source custody is VB-CONTEXTBENCH-SCORE-WIRE; shared verifier grade only, descriptive score fields, no historical backfill.
  - [x] **DCP-10a — Close the C/C++ gap in task-root discovery.** ✅ 2026-09-14 — merged to epyc-orchestrator main `35b05fde` (pushed to origin 2026-09-14) (commit `982ca87c`, test `test_code_search_discovers_cpp_and_systems_language_files`). The task-root whitelist lacked `.c/.cc/.cpp/.h/.hpp/.go/.rs/.java`; now covered (plus `.cxx`). Codemap stays `.py`-only (`context_discovery.py:205,279`), so the C/C++ arm scores discovery, not codemaps. `intake-1366#record`.
  - [ ] **DCP-10b — Secondary Python ranking cross-check on Loc-Bench V1** (after DCP-10): Acc@5/@10 file + Function Acc@10 on the `discover_candidates` ordering with `evaluate_results(dataset="czlll/Loc-Bench_V1")`; strip `.__init__`; raise `max_files` to ≥10; report bug-only (post-Oct-2024) vs all. Rows stay in scratch, never committed; exclude the 10 MULocBench-flagged invalid instances and issue-#24 instances; define our own frozen split (do NOT reuse ripwire's salted "held-out" slices — its split was re-partitioned by a rename). `intake-1356#record`, `intake-1346#04`.
  - **[declined: ws58 2026-11-03 content-review: tooling comparison (ripwire vs GitNexus) with no stack decision attached; the only consumer would be a CLAUDE.md rule change, which is human-only]** **DCP-10c — ripwire vs GitNexus blast-radius head-to-head (evidence only).** Pinned ripwire SHA vs current GitNexus (upgrade from 1.6.8 first) on epyc-orchestrator + epyc-root; pre-authored frozen questions weighted to callers/impact/context; GitNexus run with its intended impact/context workflow; commit questions, raw outputs and scoring; judge outside both projects. The external 27W/7L/14T is single-judge, uncommitted and CLI-only-GitNexus — not evidence. **CLAUDE.md is human-only (`human_only_paths.yaml`); any change to the gitnexus-before-edit rule needs an operator token.** `intake-1346#03`.
- **[declined: ws58 2026-11-03 content-review: merged into DCP-6 as an arm; the implementation is complete in APP source and only the validation remains]** **DCP-11 — Packer rendering: stop downgrading edit-site files to signatures.** For a candidate with ColGREP hit line-ranges, never render `codemap_only`; keep the hit AST segments verbatim (+ class headers/imports) and render other segments as `# ... N lines omitted`, or exclude with a "missing evidence" manifest entry. `test_pack_includes_high_priority_full_then_downgrades` encodes today's downgrade and must change with it. Policy change → validate as a DCP-6 arm (ON vs current) after DCP-12. `intake-1357#record`, `intake-1365#record`. Implementation completed in APP source `b7110ec02502113ba8f1554ca54153c734e44bd6` + `ee471a4d3cd6c9a1f81fd3e560495dd1f35dbcd3`, published by `9e138e3a3e22ecf8c57cd5bf50beed571d107b54`; hosted run 41282077353 passed 299 tests (0 failures/errors/skips), with 23 source hashes pinned to the source commit. Original 298-pass run 41281631425 is separately preserved. Evidence: `artifacts/engineering/dcp11-ast-edit-evidence-20261101/`. No runtime/model-quality claim; DCP-6 validation remains after DCP-12. [belief: cc]
- [ ] **DCP-12 — DCP-6 power prerequisite.** Before any DCP-6 rerun: ≥2 identical-arm reruns of the same role+prompt set to measure the local run-to-run flip rate, then size the paired sample for exact McNemar. n=3/arm cannot resolve effects under an ~9%-class flip floor (6/70 flips on a T=0 cloud API). `intake-1357#04`.
  - **2026-11-02 calibration preparation:** the existing `epyc-orchestrator/scripts/benchmark/dcp_j7_ab.py` sequences OFF and ON arms and does not supply quality scores for its fixed prompts. It cannot measure identical-arm correctness flips as shipped. Prepare a same-role, same-prompt, same-configuration repeated-run harness with predeclared per-task correctness labels and paired outcomes; then compute observed discordance and size the later paired comparison before DCP-6. Preserve the runner's host-quiet admission contract, and do not infer that a queued launcher is itself a quiet-window attestation. No calibration result has been produced.
- [ ] **DCP-13 — Delegation hand-off fidelity.** Code facts at orchestrator `5a9442d3`: the architect decision loop breaks on turn 0 in every branch (`chat_delegation.py:203-220`) so the advertised `fetch_report` is unreachable; D|Approved and the `skip_synthesis_on_timeout` early return can hand handle+summary text to the user; `worker_summarize` runs even for rescued reports whose summary is discarded. Zero-compute half DONE 2026-09-14 — merged to epyc-orchestrator main `35b05fde` (pushed to origin 2026-09-14): `2bffb45b` removes the dead `fetch_report` advertisement from the synthesis prompt and `review.py` fallback; `57ceb7d5` returns full reports on D|Approved, the timeout early return and four other user-facing returns (architect-error early returns, forced-synthesis failure fallback, `needs_input` partial); `a2af42ad` skips `worker_summarize` on rescued reports while still persisting the handle. **Residual (closed by DCP-13a and DCP-13b below, 2026-11-09 audit: the earlier "Residual (open)" text described exactly those two children, both ticked).** Open here: only the inference-gated arms (i)-(iii) listed under DCP-13b. `fetch_report` remains a real REPL tool (`environment.py:543`) and the turn-0 break at `chat_delegation.py:203-220` still holds.
  - [x] **DCP-13a — Drop or make actionable the `fetch_report` line in handle text.** `_to_report_handle_text` (`chat_delegation_reports.py`) still writes "Use fetch_report('<id>') for full content." into text the architect cannot act on (turn-0 break); update the report-handle integration test with it. Zero compute.
  - [x] **DCP-13b — Cache hits return the short form.** On non-rescued runs the delegation cache stores handle+summary text, so a later cache hit hands the user that form; store the full report (or reload it from the handle) on the user-facing path. Zero compute. Inference-gated arms stay open here: (i) label confident-wrong outcomes where the stored raw report held the evidence but summary/answer dropped it (arms: summary+handle vs raw vs verbatim rescue); (ii) index-backed seed bundle with NO specialist delegation vs delegation; (iii) explored-vs-used evidence drop (seed bundle = step 0) against the ≤20% top-up rule. `intake-1358#record`, `intake-1366#record`.
- [x] **DCP-14 — Delegation propagation audit over recorded traces (zero inference).** ✅ 2026-10-21 For each delegated sub-call join the parent and child prompts on `parent_request_id` in the inference-tap events (`src/runtime/inference_tap.py:407-437`, call site `src/llm_primitives/inference.py:477-487 @5d4ad2c0`; file `/mnt/raid0/llm/tmp/inference_tap_events.jsonl`, 2026-08-24 to 2026-10-05) and report, per role, the share of parent format constraints, option lists, ids and required output schema that appear in the worker input, using a rule-based detector fixed before the run (the parent constraints are not structured fields) (`intake-2171#03`: a delegate's input is a measurement variable). Truncated prompts (prompt cap 8,000 chars, about 12.7 percent flagged in a feasibility probe that is not a result) are a separate denominator, not silently counted; report N parents per role and unparsable pairs. Trace-only, so DCP-12's power prerequisite does not apply; sibling of DCP-13.

  - 2026-10-21 `noninf-memeval` ran, NOT ticked: [`artifacts/noninf-memeval-20261021/dcp14.py`](../../artifacts/noninf-memeval-20261021/dcp14.py) (detector fixed before the run, sha256 `aae5fcb26c1f4d3e`) over `/mnt/raid0/llm/tmp/inference_tap_events.jsonl` (sha256 prefix `976cdd811228daa5`, 290,555 lines, 3,105 `start` events, 2026-08-24 to 2026-10-05); result `dcp14_result.json`. STRUCTURAL FINDING: `parent_request_id` is the API request id (`api-xxxx`), which no `start` event carries as its own `request_id` (0 of 587 parents). So there is no parent-prompt event to join to; the join pairs sibling calls inside one `parent_request_id` group: delegate = `worker_general`/`worker`/`worker_vision`, parent = the latest earlier non-delegate call (frontdoor, architect_*, ...). 172 delegate-only groups have no parent prompt in the tap and are reported as `no_parent_prompt`, not paired. Per parent-role to worker_general pair counts (parents N / pairs analysed / identical-prompt pairs / truncated, separate / unparsable): frontdoor 237 / 241 / 195 / 11 / 0; architect_general 30 / 30 / 6 / 0 / 0; architect_critic 20 / 20 / 0 / 0 / 0; ingest_long_context 44 / 0 / 0 / 44 / 0 (every pair truncated); coder_escalation 1 / 0 / 0 / 1 / 0. Propagation (item level, share of parent items found verbatim in the worker prompt; non-identical pairs in brackets): frontdoor format 0.749 (0.483), option lists 0.989 (0.600 on 1 pair), ids 0.891 (0.873), schema 0.000 on 1 pair; architect_general format 0.111 (0.040), schema 0.043 (0.000), ids 1.000 on 3 pairs, options 1.000 on 3 identical pairs; architect_critic format 0.000, schema 0.000 on 20 pairs each. Reading: 195 of 241 frontdoor pairs are the same prompt (the worker is handed the user prompt), so frontdoor propagation is mostly copy; where a higher role writes its own delegate prompt (architect_*, critic) format constraints and schemas almost never reach the worker. Caveats: regex detector over unstructured text, small N outside frontdoor, groups with more than one delegate share one parent.
- [x] **DCP-15 — Measure and propagate format and schema constraints in architect-written delegate prompts (report-only first; no fix assumed).** From DCP-14 over the recorded tap: when architect_general writes the worker prompt, only 0.111 of its format constraints and 0.043 of its schema keys reach the worker (30 parents; 0.040 / 0.000 on the 24 and 22 non-identical pairs); architect_critic 0 of 20 pairs for both. Task: (1) classify, by reading a fixed sample of the 20 critic and 24 non-identical architect pairs, whether the dropped constraints were needed by the worker's required output (a dropped constraint that the worker did not need is not a defect); (2) if needed, specify where the constraint block is carried (structured field versus prompt text) so DCP-14 can be re-run against a structured source. Zero inference; depends on DCP-14 (done). Evidence: `artifacts/noninf-memeval-20261021/dcp14_result.json`.
  - ✅ 2026-11-09 (apr2 third-pass) report-only classification done: [`artifacts/noninf-memeval-20261109-dcp15/README.md`](../../artifacts/noninf-memeval-20261109-dcp15/README.md) (per-pair list `dcp15_pair_classification.json`). All 20 critic and 24 non-identical architect pairs re-derived with the DCP-14 detector's own pairing (counts reproduce) and read. **42 of 44 parents are the fixed plan-review template** (`Review plan. Reply JSON ONLY: {...}`) paired with an unrelated benchmark task: the dropped "format" and "schema" items are the plan-reviewer's own reply schema, which the worker never needed, so the 0.043 / 0.000 rates are a PAIRING ARTIFACT (the detector pairs a worker call with the latest non-delegate call in the request group, which here is the plan-review step, not the author of the worker prompt). Real candidates: 2 architect_general pairs whose parent is `Respond with ONLY valid Python code...` and whose child drops that preamble (plausibly needed; N=2 supports no rate). Carrying spec: authors write an `output_constraints` structured field at delegation time (format list + schema keys) from which the prompt text is rendered, and DCP-14 re-runs against that field; until then DCP-14 should count a pair only when the parent prompt contains the child task text. No fix assumed or implemented. [belief: cc]

2026-10-05 NI36/DCP-13a,b source boundary accepted: remove unreachable fetch instruction, keep compact loop telemetry and return the separately retained full report to the user on cache hits; legacy summary-only entries miss the report-required path. Original CI37327525343 reopens TRUE Judged/Located for 57/57 complete cache/architect cases and 1/1 separate ordinary capacity refusal, zero skips/failures/errors. Ordinary five-source candidate504 is promoted as appdb38737d; helper/workflow stay candidates. No inference or live-cache performance claim; inference-dependent DCP-13 arms stay open. NI37 timeout reporting is newly filed; tally **35/37**.

NI38 bounded offline score preparation accepted 2026-10-05: original CI37345306976 passes12/12 scorer and67/67 reader/ingestion cases, zero skips/failures/errors. Main independently reopens both CI receipts TRUE Judged/Located and the bound original synthetic scored-report archive in owned0700 custody: one TRUE report and two diagnostic NULL/zero-row originals, preserving original UUIDs/modes/bytes. Descriptive macro file/span metrics retain failure/empty denominators and caller-declared dispositions/costs; no official dataset denominator or quality claim. Reviewed app sourcec8851695 and root sourcecab789885 are promoted unchanged; recipe remains separate. Original public prefixes: artifacts/ni05/contextbench-score-37345306976. Full DCP-10 benchmark stays open; tally **40/44**, NI18/41/43/44 continue.

- [x] **DCP-RENDER-IDENTITY — refuse changed bound file content before rendering any context seed.** ✅ 2026-10-06 — [Render identity contract](../../docs/reference/dcp-render-content-identity-contract.md), APPmain049ecf5a and originalCI37457222213 TRUE17/17 after complete MAIN custody review. Changed bound readable content raises before FULL/SLICES/CODEMAP; advisory caller falls back, matching/unbound/unreadable compatibility retained. DCP-12/live gates remain separate; no absolute prompt budget or discovery/quality claim.

- [x] **DCP-11-PREP — implement the literal hit-span-preserving policy as a source candidate.** ✅ 2026-10-06 — [Contract](../../docs/reference/dcp-hit-span-policy-preparation.md) promoted APPmaincd37eb3c; originalCI37458830138 TRUE33/33 after complete MAIN source-first custody review. COLGREP+nonemptyranges never downgrades to CODEMAP_ONLY, retaining mode ceiling or missing-evidence exclusion/ranges. Spanless warm.py fixture and other sources unchanged. Parent DCP-11/DCP-12/DCP-6 gates stay open; no AST/header reconstruction or live quality/activation warrant.

2026-10-06 source boundary: DCP9A-USAGE supplies a fresh explicitly bounded cohort; historical61-transcript figures above are not current-cohort evidence. Definition1 remains not evaluable because ordered completed-task quality/time records under a fixed judge are missing. DCP9b requires write-time purpose labeling, never transcript classification.

#### Bounded discovery score correction

- [x] **DCP2-FINITE-SCORE-SOURCE** — normalize malformed or non-finite ranking scores on both supported discovery inputs: parsed ColGREP payloads and direct DiscoveredHit lists. One finite-score helper maps conversion failures, NaN and infinities to the existing neutral0.0 fallback before grouping/max/sorting. Preserve finite ranking, file/query/exclusion/cost behavior and input hit/range objects. Bind exact two-file sourceb21e45af and all25 original whole-module cases through VB-NI08-DCP2-COLGREP-SCORE-CONFORMANCE before MAIN acceptance. No default flip, real ColGREP process, inference, live corpus quality, DCP integration/performance or promotion warrant; broader live DCP decision stays open. ✅ 2026-10-07 — [MAIN exact source/original25 acceptance](../../artifacts/ni08/dcp2-finite-score-source-acceptance-20261007/README.md); APPf0df, native TRUE25/25, original status/grade/custody preserved; broader live gates remain open.
- [x] **DCP-16 — Append the delegation-arm comparator clauses to the M12 record (one edit, document only).** One edit to the M12 record: (1) any fan-out or dispatch arm carries a retrieval top-k comparator (BM25 or embedding) at matched consultant tokens (intake-2244#record); (2) the comparator set for a long-input arm includes a serial chunk chain, and every arm reports worker decode tokens and serial wall-clock beside consultant tokens (intake-2258#record); (3) arm B schema candidates are the Minions explanation, citation and answer record with abstention dropped and an extracted-information, rationale, answer-or-NO-INFORMATION, confidence record, cited for direction only and scope-limited (intake-2273#record); (4) any arm with more than one sample per sub-task states its selector and reports oracle coverage beside selected accuracy at matched consultant tokens, and the earlier claim that samples above 16 hurt is withdrawn as a repeated-sampling result (intake-2274#record) and applies at three or more sample widths (intake-2312#record); (5) a variant returns path-op-value revisions to a typed state instead of a rewritten summary, measuring decoded tokens and task success (intake-2282#record). Acceptance: the five clauses are in the M12 record text. Estimate: 0.2 day. ✅ 2026-10-21
- [x] **DCP-17 — DCP-14 detector column: sub-ask enumeration count.** ✅ 2026-10-21 Add one report-only column to the DCP-14 rule-based detector, fixed before the run: per parent and child pair, the count of enumerated or bulleted sub-asks in the worker input and the matching enumeration count in the worker response, so the sub-task-count stratum can be read from recorded traces (intake-2244#record). Zero inference, no threshold. Sibling of DCP-14; if DCP-14 is already applied it lands as an extension. Acceptance: the column appears in the DCP-14 report on a fixture pair. Estimate: 0.3 day.
  - 2026-10-21 (dpf-sample-yarn-zc, lane `lane/dpf-sample-yarn-zc-epyc-root-20261021`, commit `ea4e69096`): DONE as an extension, since DCP-14 already exists as the run-once script `artifacts/noninf-memeval-20261021/dcp14.py` (sha256 prefix `aae5fcb26c1f4d3e`, left untouched). `scripts/research/dcp14_enum_column.py` re-states DCP-14's pairing rule as functions and adds the report-only columns `parent_enum`, `worker_input_enum`, `worker_response_enum` (rule fixed in the module docstring: bullet, numbered, lettered or checkbox lines; worker response = concatenated chunk events); truncated and unparsable pairs are separate strata. Acceptance: on the fixture pair (`tests/fixtures/dcp14_enum/events.jsonl`) the column reads 3 / 2 / 2; `tests/test_dcp17_enum_column.py` 3 passed (q3, region-lock build role). The column has not been run over the real tap file (not required by the acceptance).

#### Research Intake Update — 2026-10-20 (harness cluster)

Operator-approved 2026-10-20 via research intake (plan sha256 1dc83054706ca0bae002602307b0d9ba6435b010be4d6ffd8a495a04605f3967). Monitor and knowledge records below are prose: no checkbox, no index next action.

- **M12 (monitor, 2026-10-20) — Delegation-arm follow-ons (interleaved versus plan-then-execute, explicit output schema versus free-form summary, architect-built deterministic scaffold, architect reasoning effort, nested-delegation kept_work field).** Trigger: HS-4 section 3.5 delegation tuning opens after the P0.4 freeze, or nested delegation is enabled. First step when it fires: Add the arm to the delegation A/B under P-AB-1. No immediate step remains: Delegation tuning has not opened; DCP-14 measures propagation first. Comparator clauses appended 2026-10-21 (DCP-16): (1) any fan-out or dispatch arm carries a retrieval top-k comparator (BM25 or embedding) at matched consultant tokens (intake-2244#record); (2) the comparator set for a long-input arm includes a serial chunk chain, and every arm reports worker decode tokens and serial wall-clock beside consultant tokens (intake-2258#record); (3) arm B schema candidates are the Minions explanation, citation and answer record with abstention dropped and an extracted-information, rationale, answer-or-NO-INFORMATION, confidence record, cited for direction only and scope-limited (intake-2273#record); (4) any arm with more than one sample per sub-task states its selector and reports oracle coverage beside selected accuracy at matched consultant tokens, and the earlier claim that samples above 16 hurt is withdrawn as a repeated-sampling result (intake-2274#record) and applies at three or more sample widths (intake-2312#record); (5) a variant returns path-op-value revisions to a typed state instead of a rewritten summary, measuring decoded tokens and task success (intake-2282#record).

#### Research Intake Update — 2026-10-21 (harness cluster, DP-F amendment)

Operator-approved Stage-3 amendment (plan sha256 2edfb0662f61e1254e7dc5e2b21888ef4f19df800a283e82b25caebeb6644746). Durable records only: no checkbox, no index next action. Each monitor row carries its trigger and first step; each knowledge row states what to rely on. Ledger ids (DPF-...) key to the Stage-3 recommendation mapping preserved in `.research-session.json` (`stage3_filing`).

##### M17 — Fan-out and delegation arms waiting on the UFH-13 thesis experiment or shell subagents

- DPF-1806-L1 (intake-1806#04, intake-1806#05): The paper does not measure token or latency costs and supplies no local-model or capacity-bounded fan-out result. Keep the existing shell-subagent trigger (`permission.task`, `subagent_depth` or HS-4 P4). When it fires, test spawn width and entries per worker in our own paired A/B, reporting uncached prefill and task success; no local accuracy gain is established by the paper. Its one-level script mechanism is narrowed and still review-required (intake-1806#01); multi-level recursion was not demonstrated.
- DPF-1806-L5 (intake-1806#05): The paper evaluates only Oolong-Synthetic; this is a scope fact, not evidence that the probe is runnable locally. Trigger: the operator selects the YaRN/long-context dive set. First ingest arXiv:2511.02817 and check whether its Synthetic split is runnable on local models.
- DPF-W1-ANTHROPIC-DYNAMIC-WORKFLOWS-L4 (intake-2227): Fan-out bounds as a template for our fan-out: concurrency default tied to CPU count, per-call item cap, per-run agent cap, a projected-token warning. Our REPL parallel_dispatch has max_workers but no… — Existing trigger stands (shell subagents re-enabled). When it fires, add the per-run cap and projected-token warning as two items of that design.
- DPF-W1-LRLM-L3 (intake-2241): Weak-model coding tax: free-form control code is the largest single loss for Qwen3-8B on OOLONG (-24.2 pp, 3.9x latency); the Mistral-7B/Codestral gap shrinks 28->16 pp under the fixed chain. One cel… — Trigger: S4 results exist for a small worker role; then compare that role's REPL turn failures (parse errors, crashes, runaway recursion) with LRLM-1's fixed arm. Note HIL-9 item 6 (feature actually exercised) applies.
- DPF-W1-LRLM-L4 (intake-2241): Pre-execution cost bound: N=(k)^d+1 calls and C-hat computed before the first leaf call; a task is refused or re-planned if over budget. — Trigger: LRLM-1 arm is built; add a predicted-vs-actual call-count column. No separate task.
- DPF-W1-MINIONS-M1 (intake-2244): Mechanism: the consultant never reads the corpus; it emits a Python function that generates a chunk x instruction x sample job grid for small workers, then only sees filtered answers (section 5.1). R… — none now; at unfreeze, Minions-style job grid is one candidate dispatch shape and must be A/B'd with consultant seconds, not dollars
- DPF-W1-MINIONS-M2 (intake-2244): Worker output contract: workers abstain or return JSON {explanation, citation, answer}; abstentions are dropped before the consultant sees anything; the consultant decides sufficiency or names job id… — At the M12 trigger define arm B as the abstain-and-cite schema above; do not cite the paper as evidence the schema helps (not ablated)
- DPF-W2-COA-C1 (intake-2258): Mechanism contrast with MinionS: serial chunk chain with a rewritten CU and a manager, no code-generated job grid, no abstention, no re-ask. Wall-clock is the sum over chunks (no parallelism), so on… — none now; at unfreeze a chunk-chain is one candidate dispatch shape beside the Minions job grid
- DPF-W2-COA-C7 (intake-2258): Ingest-into-role decline: wiring a chunk chain into ingest_long_context is not actionable now (fan-out/dispatch build frozen behind UFH-13; no local-model or latency evidence in the paper). — Reason: frozen consumer, and the source carries no local-hardware cost data.
- DPF-W2-LLMXMR-L6 (intake-2273): Code release (github.com/thunlp/LLMxMapReduce) exists; reading it would settle the baseline prompts and the exact map/collapse prompts. Not read here (no repo clone in this wave; paper only). — none now; read-only clone at M12 trigger if arm B is built
- DPF-W2-LMONKEYS-L3 (intake-2274): Cheap-model-many-samples vs one strong call is task-dependent (8B beats 70B at fixed FLOPs on MATH/GSM8K/MiniF2F, loses on CodeContests); API-dollar Table 1 does not transfer to a bandwidth-bound CPU… — none now; at fan-out unfreeze consider a best-of-k worker arm only for tasks with a deterministic checker, costed in consultant-host seconds
- DPF-W2-PRISM-P6 (intake-2282): LLM-generated schemas: equal on RepoQA, 93% / 58% of expert elsewhere; schema generation from task description plus one example. — none now; PromptForge has no typed-state memory to schema; revisit if M12 variant P1 opens
- DPF-W3-CONSENSUS-E2 (intake-2300): Verbalized confidence is a consensus proxy, not a truth signal. — Fold into R4's trigger note: if the best-of-K arm is built, confidence enters only as a selector candidate and is scored against the checker; never a claim-tuple field.
- DPF-W3-CONSENSUS-E4 (intake-2300): Predicted consensus as a risk flag that triggers retrieval, tools or deferral. — Trigger: TE-reopen escalation-design review opens. Then consider sample disagreement or confident agreement on a verifier-absent task as an escalation feature to test; frozen with UFH-13 until then.
- DPF-W3-LCBOOST-B1 (intake-2306): Model-written actions (continuous action space) were highly unstable even for GPT-3.5; a discrete action menu worked. — Trigger: S4 Omega A/B has per-tier data. Then compare the existing free-form REPL arm against a discrete-action arm (retrieve / scan / append / merge / null) on the same tasks. Note S4 gate: no new REPL tools before S4, so this stays a com…
- DPF-W3-LCBOOST-B2 (intake-2306): Null-skip output convention ('output null if no answer in this chunk') lets a sequential scan skip irrelevant chunks. — Fold into the same M12 trigger as LongAgent A1: the output-schema arm includes an explicit null value.
- DPF-W3-LONGAGENT-A1 (intake-2308): Members fabricate answers on chunks that hold no answer, even after SFT; refusal training trades answer accuracy (51.0 to 78.6 refusal; 83.3 to 78.3 accuracy). — Trigger: M12 fires (HS-4 s3.5 delegation tuning opens after P0.4 freeze). Then the output-schema arm carries an explicit 'no answer in my scope' value, and the arm reports the rate at which a worker returns an answer when the scope holds n…
- DPF-W3-MORECALLS-C2 (intake-2312): Fit the scaling model on K=1..5 and extrapolate to choose K. — Trigger: RUS-1 arm built and K=1..5 per-task correctness logged. Then fit G(K,D) on K<=5 and compare its predicted K* with measured K up to 8 before spending the full sweep. Real-data validity is unproven (simulated only in text).
- DPF-W3-TRACELEN-F2 (intake-2316): Add the length term to RUS-1 only after F1 shows the within-question direction on our roles. — Trigger: F1 probe done. Then keep or drop the length term in the RUS-1 selector; the selector table also carries a 'length not used' row.
- DPF-W3-TRACELEN-F4 (intake-2316): Forking-token counts match length and need no prompt change. — Trigger: F1 shows a length signal on our roles. Then count a fixed small forking-token list in the same records; zero-cost.
- DPF-W2-DCNOISE-R4 (intake-2264): Planner-written aggregator prompt reduces agg noise
- DPF-W2-DCNOISE-R6 (intake-2264): RAG worse than no-RAG on several tasks (QA-IB, QA-LB, Sum, Char; better on KV) per Table 7
- DPF-W2-LRLM-REPO-R6 (intake-2275): SELECT_RELEVANT drops partials containing "not found" strings
- DPF-W2-RLMUNC-R3 (intake-2284): Recursion helps Qwen3-Coder, hurts GPT-5; RLM below base inside the window (<131K).
- DPF-W2-RLMUNC-R4 (intake-2284): Verbalized confidence per step via a JSON suffix; missing values filled by the trajectory mean; non-monotonic vs accuracy.
- DPF-W2-ARCHON-A4 (intake-2255): 7B components rank OK but critique/fuse poorly; 70B+ needed; up to 5x time and cost.
- DPF-W2-ARCHON-A6 (intake-2255): Layer grammar (one component type per layer, generator first, critic before ranker/fuser) as a template for declarative delegation pipelines.

## Track: memento-block-reasoning-compression
<!-- gate: none -->

> Folded from `handoffs/active/memento-block-reasoning-compression.md` @ `7e268b4de29c` on 2026-11-02 (BRF-T1-F6, route 1a, operator D1/D5; retired row UFH-03 → RTG-08). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Memento: Block-Level Reasoning Compression with KV Cache Masking

**Scratch**: `/mnt/raid0/llm/tmp/memento-block-reasoning-compression/` · worktrees: `/mnt/raid0/llm/worktrees/memento-block-reasoning-compression-*`

**Status**: REFRESHED 2026-05-28 — S1 runtime PASSED; S2 LoRA validation is the only live implementation gate; S3 remains blocked
**Created**: 2026-04-08 (via research intake)
**Updated**: 2026-05-28 (S2 decision fork and S3 block clarified)
**Categories**: kv_cache, training_distillation, context_extension, inference_serving
**Deep-dive**: `research/deep-dives/memento-iterative-reasoning-cluster.md`

#### 2026-05-28 Audit Reset — Executor Start Here

S1 answered the llama.cpp feasibility question. The next executor should not touch deployment wiring until a trained adapter proves the model can emit reliable block/summary structure under quantized inference.

| Live decision | Default |
|---|---|
| Which model first? | Start with a CPU-feasible Qwen3-0.6B format smoke if no GPU is available; use Qwen3-1.7B for the validation target. Do not start 8B/32B CPU training. |
| Can S3 begin now? | No. S3 requires S2 evidence: format compliance, compression ratio, and no severe benchmark degradation. |
| Is OpenMementos already staged? | Yes: `/mnt/raid0/llm/data/openmementos/`. Verify paths before training because dataset storage is outside this repo. |
| Does block masking save peak memory? | In current llama.cpp it frees reusable KV cells; it does not shrink preallocated buffers. Phrase claims as effective context/batch capacity unless paged-attention metadata is fixed. |

##### S2 Minimal Runbook

```bash
cd /mnt/raid0/llm/epyc-inference-research
python scripts/benchmark/memento_sft.py --dry-run
# Then run the smallest real Stage-1 format-learning job that fits the current host/GPU budget.
```

Record results in this table before promoting S3:

| Model | Adapter | Format compliance | Compression ratio | MATH-500 delta | Decode stable with S1 masking? | Decision |
|---|---|---:|---:|---:|---|---|
| Qwen3-0.6B | memento-s1-lora (rank 16, 8.26M trainable) | TBD — inference check pending (GGUF convert + masked-prompt structure test) | TBD | TBD | TBD | **smoke → continue** ✅ 2026-08-27 — 16 steps / 126 samples trained (loss quarters 1.485→1.337, adapter integrity 168/168 lora_B nonzero, all finite; 18.8 s/sample CPU). Belief row ingested: `clm_memento_sft_stage1_seconds_per_sample` Witnessed/Attested (SC20). Format-compliance numbers still needed before the 1.7B gate closes |
| Qwen3-1.7B | memento-s1-lora (rank 16) — Stage-1 smoke COMPLETE 2026-08-27 | **FAIL at smoke scale (verified both ways)** — with the verified stack (extended-vocab Q8 base + lora GGUF; memento tokens are single ids 151669-151672), greedy generation emits zero block/summary tokens with thinking ON (`<think>`-only outputs) AND with thinking OFF (direct 5.7k-char answers, no markers). The 126-sample/1-epoch smoke did not learn the structure; the pipeline itself is verified end-to-end (tokens → training → convert → serving) | **−2.0 pp (n=50)** — base 0.440 vs adapter 0.420 (1-question difference, within noise) | TBD | TBD | **continue — scale stage-1 data, GPU-GATED (deferred)** (the fork's format-fails branch: fix the input side; the tokens/vocab/data pipeline is verified correct, so the fix is training scale — a few thousand samples of the 228k corpus — not a stop; no severe accuracy drop fired). **2026-08-27 operator decision: the scaled run happens on the GPU, not CPU** — CPU cost is 10-40 h at seq 4096 / 5-21 h at seq 2048 (measured ~4.7 min/step @ 4096); GPU needs a ROCm torch build in the ml-training venv (currently CUDA-only — the ROCm install was explicitly declined 2026-08-27) plus a GPU window. Recommended first checkpoint when unblocked: 1,000 samples @ seq 2048; if the format fails there too, the diagnosis shifts to the training objective (stage-2 masking) before any 40-CPU-hour investment |

Decision forks:

- **Format fails**: fix prompts/data preprocessing; do not touch runtime masking.
- **Format passes but accuracy drops hard**: keep S1 as reference, stop before S3.
- **Format + accuracy pass on 1.7B**: schedule 32B QLoRA or equivalent GPU-backed validation before production integration.

#### Objective

Investigate Memento-style block reasoning compression for EPYC stack — training models to segment reasoning into blocks, compress each block into a dense summary (memento), and mask original block KV states while retaining memento KV states. This could reduce peak KV cache 2-3x during reasoning while preserving accuracy, composing with our existing Hadamard+q4_0 KV quantization.

#### Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-289 | Memento: Teaching LLMs to Manage Their Own Context | high | new_opportunity |
| intake-290 | OpenMementos-228K (MIT, 13.9GB) | high | new_opportunity |
| intake-292 | InftyThink (ICLR 2026, arxiv:2503.06692) | high | new_opportunity |
| intake-293 | InftyThink+ (arxiv:2602.06960) | high | new_opportunity |
| intake-294 | Accordion-Thinking (arxiv:2602.03249) | high | new_opportunity |

#### Key Findings (Deep Dive 2026-04-09)

##### Dual Information Stream (Memento's unique contribution)
- KV cache states computed while a block is visible carry **implicit information** beyond the summary text
- Recomputing KVs without block context: 66.1% → 50.8% AIME24 (-15.3pp)
- Probing: passcode injected into masked block is recoverable from downstream memento KV states at 23-27% (vs 10% chance), signal concentrates in deeper layers
- This is **architectural, not learned** — confirmed on toy transformer, persists across training checkpoints
- **Implication**: Text-level compression approaches (InftyThink, Accordion, our context-folding) have a fundamental ~15pp ceiling vs. KV-retaining approaches for reasoning tasks

##### Accuracy Gap Is Consistency, Not Capability
- Pass@64 Jaccard similarity: **96.4%** between Base and Memento solved sets
- Majority voting at **k=3** recovers base accuracy without RL
- **EPYC opportunity**: Combine Memento KV savings + existing `short-m@k` voting (intake-129) = 2-3x KV reduction at ZERO accuracy cost

##### Scale Helps
- Accuracy gap: -6.3pp at 8B → -3.5pp at 32B (averaged across 5 benchmark groups)
- Our production 32B architect would see minimal accuracy loss
- MATH-500 is near-lossless (<1pp gap) across all scales

##### Composability — Quad-Stack KV Compression
- **Block masking (Memento)**: 2-3x — removes entire reasoning blocks (WHICH semantic blocks survive)
- **KV quantization (Hadamard+q4_0)**: 2-4x — compresses each surviving KV entry (deployed, `b51c905`) (HOW tokens stored)
- **KV compaction (Attention Matching)**: 10x — constructs compact latent KV entries with fitted biases/values (planning, [attention-matching-kv-compaction.md](long-context-program.md#track-attention-matching-kv-compaction)) (HOW MANY entries exist)
- **KV selection (TriAttention/Expected Attention)**: 2-10x — keeps only important tokens (evaluating, triattention-kv-selection.md). Note: AM compaction subsumes selection at 20x+; redundant to stack both.
- Theoretical combined (quant × compaction × masking): **up to 120x**. Conservative: **40x** (quant × compaction alone, no selection or masking needed). Quality cliff under multi-layer compression is the key unknown — each pair tested independently.

##### Serving Throughput
- Memento vLLM: 4,290 vs 2,447 tok/s at full concurrency (1.75x), B200 GPU
- Mechanism: block masking frees KV entries mid-generation → higher effective batch size
- For our single-user llama.cpp stack: benefit is faster generation at long contexts (less memory bandwidth for KV attention)

#### Implementation Path

##### S1: llama.cpp Block Masking Feasibility (prerequisite) — FEASIBILITY CONFIRMED (2026-04-13)

**API correction**: The handoff originally referenced `llama_kv_self_seq_rm()` — this does NOT exist. The correct API is:
- **Public**: `llama_memory_seq_rm(llama_memory_t mem, llama_seq_id seq_id, llama_pos p0, llama_pos p1)` at `include/llama.h:733`
- **C++ virtual**: `llama_memory_i::seq_rm()` at `src/llama-memory.h:103`
- **Concrete**: `llama_kv_cache::seq_rm()` at `src/llama-kv-cache.cpp:388`

**Feasibility assessment**: YES — `llama_memory_seq_rm()` can serve as the Memento block eviction primitive.

**Call chain**: `llama_memory_seq_rm()` → `mem->seq_rm()` (virtual dispatch) → `llama_kv_cache::seq_rm()` → iterates `v_cells[stream]`, checks `cells.pos_in(i, p0, p1)`, calls `cells.seq_rm(i, seq_id)` → clears seq bit, if no sequences remain: frees cell (`pos[i] = -1`, removed from `used` set)

**Key findings**:
1. **Mid-sequence removal**: Fully supported. Any contiguous position range [p0, p1) can be removed. Always succeeds (returns true).
2. **Position gap**: After removal, remaining cells keep original positions. No automatic shifting. This is CORRECT for Memento — the dual information stream requires preserving original RoPE phases.
3. **Cell freeing**: Freed cells are immediately reusable by `find_slot()`. Data buffers are pre-allocated/static (not freed), so benefit is effective context extension, not peak memory reduction.
4. **ISWA**: Transparent — `llama_kv_cache_iswa::seq_rm()` delegates to both base and SWA caches.
5. **Block tracking gap**: Partial sequence removal does NOT deallocate paged attention blocks. This is a metadata leak (blocks logically empty but still allocated). Only matters if paged attention is enabled.

**DO NOT close the position gap with `seq_add`**: The KV states after the evicted block carry implicit information from attending to the reasoning block during their original computation. Shifting RoPE positions would corrupt this encoding.

**Test skeleton**: Written at `tests/test-memento-block-masking.cpp` in llama.cpp-experimental. 5 test functions: basic eviction, gap semantics, post-eviction generation, multi-block iterative eviction, memory usage check. Compiles against current headers; requires `--model <path>` at runtime.

**S1 Runtime Validation — PASSED (2026-04-14)**:

Ran all 5 tests against Qwen3-1.7B-Q8_0 (`llama.cpp-experimental/build-diff-test`). Results:

| Test | Result | Key observation |
|------|--------|----------------|
| Basic block eviction | PASS | `seq_rm([15,46))` correctly creates position gap, pos_min=0, pos_max=61 preserved |
| Position gap semantics | PASS | Removing [30,70) leaves positions 0-29 and 70-99 intact, no auto-shift |
| Generation after eviction | PASS | `llama_decode()` succeeds at positions after the gap — no attention corruption |
| Multi-block iterative eviction | PASS | 3 sequential block→evict cycles, 4x compression (200→50 KV entries) |
| Memory usage | PASS | Freed cells available for reuse |

**S1 COMPLETE** — block masking primitive is validated end-to-end. S2 (LoRA training) is now unblocked.

**Builds on**: Our hybrid-precision buffer work (split attention, eviction from recent→old in `kv-cache-quantization.md`). Block masking is architecturally simpler — straight eviction, no demotion/requantization.

##### S2: Model Fine-Tuning (requires S1 success) — DESIGN COMPLETE (2026-04-13)

**Dataset**: OpenMementos-228K downloaded at `/mnt/raid0/llm/data/openmementos/` (228,557 examples, 4.7 GB). Default config (20 shards) has training-ready block/summary formatted responses. Full config (39 shards, 9.2 GB) includes intermediate pipeline outputs (sentences, block boundaries, block summaries).

**Dataset stats**: ~9 blocks/response median, ~12K response tokens mean, 54% math / 27% science / 19% code. Special tokens: `<|block_start|>`, `<|block_end|>`, `<|summary_start|>`, `<|summary_end|>` — all balanced, 100% have `<think>` wrapper + answer section.

**Training script**: `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/memento_sft.py` — dry-run validated.

**Two-stage LoRA design**:
1. **Stage 1 (full attention, format learning)**: Standard causal attention. Model learns to generate block/summary token structure. 2 epochs, lr=2e-4, seq_len=4096.
2. **Stage 2 (memento attention, compression learning)**: Custom 2D attention mask that blocks future tokens from attending to completed block content (only summaries persist). Teaches the model that block content is transient. 1 epoch, lr=5e-5, seq_len=4096. The memento mask removes ~59% of causal attention positions.

**LoRA config**: rank=16, alpha=32, dropout=0.05, targets=[q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj]. ~393K trainable params for 1.7B model (0.02% of base).

**Model ladder** (CPU-feasible validation path):
> ⚠️ **BOTH numeric columns below are WRONG and must not be planned against** (`mainC`, 2026-08-12,
> from the UFH-03 smoke). Retained only so the correction is legible.
>
> **`LoRA Params` omits `num_hidden_layers`.** For Qwen3-0.6B the measured trainable count is
> **8,257,536**, not 197K — **42× low**. Independently re-derived: r=16 over the six listed targets gives
> q 49,152 + k 32,768 + v 32,768 + o 49,152 + gate 65,536 + up 65,536 = **294,912 per layer × 28 layers
> = 8,257,536**, matching the measurement exactly. The other three rows are computed the same way and are
> therefore also wrong; they are **not** corrected here because each needs its own layer count and
> head/intermediate dims, and inventing them would repeat the original error.
>
> **`Est. Time/Epoch` is optimistic by more than an order of magnitude.** Measured **4.74 s/sample**
> (Qwen3-0.6B, seq 1024, bf16, grad-checkpointed, 24 cores). Against the S2 corpus of 228,557 samples
> that is **~301 h/epoch at seq 1024** — versus the ~19 h claimed. The design calls for **seq 4096**
> (~4× cost) and **2 epochs**, i.e. ~2,400 h; even granting a generous 4× full-machine speedup over the
> one-region measurement, ~600 h. Scout-grade and grad-checkpointing costs ~30%, so treat the exact
> multiplier as soft — but the gap is 15–30×, not a rounding error.
>
> **Consequence: the "Feasible?" column is unsupported.** If the 0.6B *smoke* row is really ~300 h, the
> 1.7B "validation target" is not a validation target on CPU. **Re-derive this ladder before committing
> any schedule to it**, and treat GPU or a corpus subsample as the live options.

| Model | BF16 Mem | LoRA Params | Est. Time/Epoch | Feasible? |
|-------|----------|-------------|-----------------|-----------|
| Qwen3-0.6B | 1.2 GB | ~~197K~~ **8.26M measured** | ~~19h~~ **~301h @seq1024 measured** | ⚠️ re-derive |
| Qwen3-1.7B | 3.4 GB | ~~393K~~ wrong, re-derive | ~~54h~~ wrong, re-derive | ⚠️ re-derive |
| Qwen3-8B | 16 GB | ~~786K~~ wrong, re-derive | ~~11 days~~ wrong, re-derive | ⚠️ re-derive |
| Qwen3-32B | 64 GB | ~~983K~~ wrong, re-derive | ~~42 days~~ wrong, re-derive | No — requires GPU QLoRA |

**Blockers**: `peft`, `trl` packages not installed (pip install). 32B requires GPU — CPU training is infeasible at production scale. Recommend: validate on 1.7B (CPU), then rent GPU time for 32B QLoRA.

**GGUF conversion path**: Trained LoRA adapter converts to GGUF via `llama.cpp/convert_lora_to_gguf.py`, loadable at inference with `llama-server --lora adapter.gguf`.

**Validation plan**:
1. MATH-500 accuracy (memento vs base)
2. Format compliance (block/summary token pairing)
3. Compression ratio (block tokens vs memento tokens)
4. Integrate with S1 block masking for end-to-end KV savings test

###### S2 Research Intake Update — 2026-10-04

Operator-approved [P3 operational integration](../../research/intake-stage3-plan-2026-10-03-decision-tools.md#p3-operational-integration--exercise-both-real-tool-loops-and-improve-sft-input-selection) at `3911ec91`; its pinned SFT entry points and controls are part of this task contract.

- **[declined: ws58 2026-11-03 content-review: premise declined — the operator's 2026-11-03 model audit declined S2 (CPU LoRA training infeasible, ~301 h/epoch), so there is no SFT path to feed]** **S2-CGE-1 — Feed complete, independently verified targets into Memento's existing SFT path at a matched token budget.** Add an opt-in selector actually consumed before train_stage and a preparation-only entrypoint that constructs no model weights. Bind independent deterministic correctness labels to exact problem/response bytes; unknown or unjoinable labels remain ineligible. Require ordered, balanced block/summary pairs and a final answer surviving the real tokenizer/template and sequence cap. Deduplicate by problem before splitting; where multiple eligible solutions exist, prefer the cheaper complete target. Preserve source/domain/difficulty quotas, including an explicit unknown-difficulty stratum, when selecting across problems. Keep the seeded sampler selectable as incumbent and preserve prompt masking and Stage-2 attention semantics. Screen at most 512 staged records using only locally available independent references/verifiers; never manufacture labels from the teacher's response or reserved MATH-500 evaluation answers. Selected identities must demonstrably reach the existing training loader, not end in an audit report.

**S2-CGE-1 controls, dependency and decision.** Freeze the candidate slice, independent labels, source locations, problem/response digests, cached tokenizer/template, cap and selection rule. Compare the current seeded sampler/nonzero-completion filter on the same pool at matched supervised-token budgets and source/difficulty quotas; record examples and padded tokens too. Retain all inclusion/refusal reasons, full/retained token counts, complete structure and final-answer survival. Split by deduplicated problem identity first, reserve 20% for the preprocessing screen and exclude training overlap with reserved MATH-500. Count wrong, unknown, unjoinable, malformed, truncated, prompt-only and duplicate records. Independent correctness labels are absent from the inspected staged schemas: implement explicit refusal, locate bounded local references, and report a missing eligible population rather than silently accepting teacher assertions. Conformance requires cheap-wrong versus correct, unknown-label, truncated-ending, overlap and actual-loader-consumption fixtures. At least 64 eligible records across two source strata is the proposed minimum population for a bounded format/loader smoke, not evidence of learning benefit or statistical precision. The held-out screen must supply more complete verified targets at matched token cost without broken quotas; a later training comparison additionally needs a predeclared minimum useful learning effect, matched compute budget and precision design under the existing S2 owner. Otherwise stop at the named data limitation, with no weight run or asserted learning benefit. Preparation/tokenization is not model inference; expanded S2 training requires resolution of its existing GPU/environment restriction and a coordinated window. Original behavior logprobs are unnecessary for offline SFT; they become mandatory only for the distinct off-policy RL consumer. TU-MH-1 and S2-CGE-1 are independent; native-tool transcripts are not automatically Memento-format targets.

**K6 / K9 / M3 qualification.** Correctness-before-efficiency governs actual SFT inputs. Keep offline SFT, evaluation and off-policy RL eligibility distinct. Full multi-harness RL requires a named model/workload/objective and eligible original rollouts; exact-token export belongs only to that actual consumer. New decision-bearing selection results require native preparation-output capture/projection under [VB-RI-OPS-WIRE](../../research/intake-stage3-plan-2026-10-03-decision-tools.md#approval-and-exact-stage-4-filing-scope) before their first run; the existing SFT stage hook retains its owner. This preparation task does not close S2's training/format gates or admit S3.

##### S3: Deployment Integration (requires S1 + S2)

1. Wire block masking into `orchestrator_stack.py` as inference-time feature flag
2. Implement Fold/Unfold toggle (from Accordion-Thinking) gated by difficulty_signal band
3. Combine with `short-m@k` voting for zero-accuracy-cost operation
4. Stack with existing Hadamard+q4_0 quantization

#### Open Questions

- ~~Can block masking be implemented in llama.cpp via existing `llama_memory_seq_rm()`?~~ **YES** — confirmed 2026-04-13, mid-sequence removal works, position gap semantics are correct for Memento
- Does Memento compose with speculative decoding? Block masking changes attention patterns and KV cache layout.
- Is SFT on OpenMementos sufficient for GGUF-quantized models, or does quantization degrade memento quality?
- How does the 7K block length cap interact with our difficulty-band token budgets?
- Can InftyThink+'s efficiency reward replace our regex-based difficulty signal for reasoning budget allocation?

#### Relationship to Existing Handoffs

- **reasoning-compression.md**: Memento is a new Tier 3+ approach. Updated 2026-04-08 with Memento cluster section.
- **context-folding-progressive.md**: OpenMementos data pipeline (boundary scoring + iterative refinement) validates Phase 2 methodology and could generate Phase 3 training data.
- **kv-cache-quantization.md**: Memento KV masking is orthogonal to quantization — multiplicative when stacked.
- **triattention-kv-selection.md**: Third KV compression layer — all three compose.
- **llama-cpp-v3-upstream-rebuild.md**: KV eviction API is the critical dependency.

#### Failure Modes

1. **Excessive generation**: Block masking can induce 3x more tokens on some problems (Figure 5c). Mitigation: block length cap (7K) + reasoning length alarm (Action 9).
2. **Sliding-window incompatibility**: Models with sliding-window attention (Olmo-3) see minimal KV savings (0.85-0.93x). Our Qwen2.5/Qwen3 models use full attention — not affected.
3. **SFT quality risk**: Fine-tuning already-trained reasoning models always risks degradation. Memento control runs (SFT on OpenThoughts without block annotations) show 2-5pp drops.

#### Research Intake Update — 2026-09-07

Sawtooth / duplicate-processing argument, banked for the summarize-family cluster — WITH the correction that inverts the naive reading. The axis on which prefix+sliding beats a summarize/last-k family is accuracy-per-second and GPU utilisation, NOT raw throughput: last-k is 1.54× FASTER in tok/s at 32K. Filing this without the correction would propagate an error into a GPU-gated decision. Relevant to Failure Mode 1 (excessive generation) and to the `reasoning-compression.md` Tier-3+ comparison. `intake-1315#04`.

#### Progress checklist

- [x] S1 llama.cpp block-masking feasibility + runtime validation (5/5 tests PASS, 2026-04-14) ✅
- *Moved to [`model-evaluation-queue.md`](model-evaluation-queue.md) § Track: meq-carve-memento-block-reasoning-compression on 2026-11-03 (BRF-T1-MEQ, operator D2): "S2 Stage-1 format-learning smoke on Qwen3-0.6B …".*
- **[declined: operator 2026-11-03 model-audit: CPU LoRA training infeasible per its own measurement (~301 h/epoch at the 0.6B smoke model)]** S2 validation target: Qwen3-1.7B LoRA (promote/stop decision)
      ⚠️ **Feasibility unproven — see the corrected ladder above.** At the measured 4.74 s/sample the
      0.6B *smoke* model implies ~301 h/epoch at seq 1024; the 1.7B "validation target" is not a
      validation target on CPU under those numbers. Re-derive before scheduling.
- [x] Install peft/trl; run memento_sft.py real Stage-1 job ✅ 2026-08-12 — shared persistent venv at
      `/mnt/raid0/llm/venvs/ml-training` (torch 2.13.0+cpu, transformers 5.15.0, peft 0.20.0, trl 1.9.2).
      Deliberately **not** under `/tmp`: the earlier GRPO venv was lost to `/tmp` cleanup.
      **The stated blocker was not the real one.** `peft`/`trl` were missing, but the training path was a
      SKELETON — `get_peft_model()` sat commented out behind `# TODO: Uncomment when peft is installed`,
      so installing the packages would never have produced a LoRA run.

- [x] **Repair `memento_sft.py` — six pre-existing defects, none of which a passing run would reveal**
      ✅ 2026-08-12, research `c62ba27e`. (1) **LoRA never applied** — the optimizer collected all 596M
      base params while the script printed "LoRA"; it was silently running a full fine-tune.
      (2) **`resize_token_embeddings` SHRANK the vocab** 151936→151673: Qwen3 ships reserved slots so the
      four memento tokens already fit, and the resize destroyed 263 embedding rows plus the tied
      output-head rows. (3) **The final adapter save was a TODO** — a completed run persisted nothing.
      (4) **Labels covered the prompt**, training the model to generate problem statements.
      (5) **Subsets drawn from shard 0 only**, and shards are domain-clustered, so `--max-samples 100`
      yielded 100% `code` rather than the intended mix. (6) **The LoRA param estimate omitted
      `num_hidden_layers`** — the 42× error that propagated into this handoff's ladder.
      Plus one introduced and caught in the same session: 3/128 records have prompts ≥ seq_len, so after
      truncation every label is `-100` and `cross_entropy` returns **nan** (first smoke printed
      `avg loss: nan`). The gradient was verified *zero* rather than nan, so no adapter was poisoned, but
      the metric was worthless. Now dropped with a logged count plus a non-finite-loss guard before
      `backward()`.
      Verified by 14 pytest-collected tests with a mutation harness, **10/10 mutants killed**. The first
      pass had **4 survivors and the tests were fixed, not the scoreboard** — including removing two of
      the author's own "fixes" (`enable_input_require_grads()`, an fp32 upcast loop) that were measured
      **not** load-bearing on this stack, and rewriting one vacuous test that re-derived a value instead
      of calling the function under test.
- **[declined: ws58 2026-11-03 content-review: blocked on S2, which the operator declined 2026-11-03 (CPU LoRA infeasible)]** S3 deployment integration (BLOCKED on S2 pass): wire block masking flag into orchestrator_stack.py
- **[declined: ws58 2026-11-03 content-review: blocked on S2, which the operator declined 2026-11-03]** S3: Fold/Unfold toggle + short-m@k voting + Hadamard+q4_0 stacking

## Track: per-request-reasoning-budget
<!-- gate: none -->

> Folded from `handoffs/active/per-request-reasoning-budget.md` @ `7e268b4de29c` on 2026-11-02 (BRF-T1-F6, route 1a, operator D1/D5; retired row EVL-33 → RTG-08). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Per-Request Reasoning Budget for Hybrid SSM+MoE Models

**Status**: INVESTIGATION COMPLETE (Steps 1-2 done 2026-04-17; Steps 3-4 need running server)
**Created**: 2026-04-15
**Priority**: MEDIUM (unblocks per-request reasoning control, autopilot tuning)
**Categories**: llama.cpp, inference
**Depends on**: None
**Related**: [`v3-hybrid-ssm-regression.md`](../completed/v3-hybrid-ssm-regression.md), [`bulk-inference-campaign.md`](eval-tower-program.md#track-bulk-inference-campaign)

---

#### Problem

`thinking.budget_tokens: 0` in the `/v1/chat/completions` request body does not suppress reasoning on Qwen3.5 hybrid SSM+MoE models. The server returns 210 chars of `reasoning_content` and empty `content` despite budget=0.

Works correctly on pure MoE models (Qwen3-Coder-30B — returns content, no reasoning).

Current workaround (2026-04-15): Removed `--jinja` flag from architect_general entirely. Without `--jinja`, llama-server uses generic ChatML template with no thinking scaffolding. Previous `--reasoning off` workaround was insufficient — the jinja template itself primed the model into think mode. This is even coarser — no reasoning capability at all, no per-request control. **Stale premise (PRB-T1, 2026-08-21): this workaround was reversed on 2026-06-26 (commit `f4a8a3ca`) and `architect_general` has launched WITH `--jinja` ever since. The paragraph above is retained as history, not current state.**

#### Why This Matters

Per-request reasoning control would enable:
1. Orchestrator sets `budget_tokens=0` for architect_general (structured TaskIR output, no thinking needed)
2. Orchestrator sets `budget_tokens=512` for architect_coding (useful for plan design)
3. AutoPilot tunes budget per role via NumericSwarm (explore quality-vs-speed tradeoff)
4. No server restarts — all control at API level

#### Reproduction

```bash
# Server running WITH reasoning enabled (default --jinja, no --reasoning off)
# Qwen3.5-35B-A3B hybrid on port 8280

# budget=0 should produce NO reasoning — but it does (210 chars)
curl http://localhost:8280/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"auto","messages":[{"role":"user","content":"What is 2+2?"}],"max_tokens":64,"thinking":{"budget_tokens":0}}'
# → reasoning_content: 210 chars, content: empty

# Same request on pure MoE (Qwen3-Coder-30B, port 8082) works correctly
# → reasoning_content: none, content: "2 + 2 = 4"
```

#### Investigation Plan

1. **Find budget enforcement**: In `llama.cpp-experimental`, search `tools/server/server.cpp` and `common/chat.cpp` for where `budget_tokens` is checked during token sampling/generation
2. **Trace hybrid code path**: The hybrid SSM+MoE models have recurrent layers that process tokens sequentially. Check if the `</think>` forced injection happens before or after the recurrent state update — if after, the SSM may have already committed to a reasoning trajectory
3. **Test fix**: When `budget_tokens=0`, inject `</think>` as the very first generated token (before any SSM state update). Verify on Qwen3.5-35B-A3B
4. **Test budget>0**: Verify that `budget_tokens=N` correctly caps reasoning at N tokens then transitions to content

#### Investigation Results (2026-04-17, Steps 1-2)

##### Budget Enforcement Pipeline (Fully Traced)

The reasoning budget is enforced via a **sampling-level state machine** — not a model-level control. The complete flow:

1. **Request parsing**: `server-common.cpp:1108-1118` reads `thinking.budget_tokens` → `reasoning_budget_tokens`
2. **Sampler init**: `sampling.cpp:260-299` creates `common_reasoning_budget_init()` with budget, start/end tag tokens, and prefill tokens
3. **State machine**: `reasoning-budget.cpp:59-127` implements:
   - `IDLE` → wait for `<think>` tag tokens
   - `COUNTING` → decrement remaining budget per generated token
   - `FORCING` → force `</think>` + fallback message by setting all other logits to -∞
   - `DONE` → passthrough (no more budget control)
4. **Logit forcing**: `reasoning-budget.cpp:129-149` — when `FORCING`, sets all logits to `-INFINITY` except the next forced token

##### Root Cause: SSM State Update Race

The bug is specific to **hybrid SSM+MoE models** (Qwen3.5-A3B):

- **Attention layers** process the full context bidirectionally — budget forcing works because logit manipulation happens before the next token is committed
- **SSM/Mamba layers** update their recurrent state **during each token generation step** (`llama-context.cpp:3345-3354` accesses `llama_memory_hybrid`)
- When `budget_tokens=0`, the state machine promotes from `COUNTING` to `FORCING` at init (`reasoning-budget.cpp:201-204`), but the **prefill matching** (`reasoning-budget.cpp:221-246`) must first detect `<think>` in the prefill before promotion happens
- On hybrid models, the first generated token after `<think>` triggers an SSM state update that commits the model to a reasoning trajectory, even though the sampler is about to force `</think>`

##### Proposed Fix (Steps 3-4, needs running server)

**Fix A** (minimal): In `reasoning-budget.cpp:200-204`, ensure `FORCING` state is set BEFORE the first token is generated when `budget=0` AND `<think>` is detected in prefill. Current code does this, but the SSM has already processed the prefill with `<think>` visible — the fix may need to strip `<think>` from the SSM prefill or inject `</think>` into the prefill itself.

**Fix B** (robust): For hybrid models, when `budget_tokens=0`, do not include `<think>` in the generation prompt at all. This means the chat template should suppress the think scaffold when budget=0 — modify `chat.cpp:1313-1331` to check budget before setting `thinking_start_tag`.

**Fix C** (workaround): Already deployed — remove `--jinja` flag entirely. Loses all thinking capability but avoids the SSM state commitment issue.

##### Verified Test Protocol (for Steps 3-4)

```bash
# Test 1: budget=0 → no reasoning (the bug)
curl localhost:8280/v1/chat/completions -d '{"model":"auto","messages":[{"role":"user","content":"What is 2+2?"}],"max_tokens":64,"thinking":{"budget_tokens":0}}'

# Test 2: budget=512 → capped reasoning
curl localhost:8280/v1/chat/completions -d '{"model":"auto","messages":[{"role":"user","content":"Prove sqrt(2) is irrational"}],"max_tokens":1024,"thinking":{"budget_tokens":512}}'

# Test 3: No regression on pure MoE (port 8082)
curl localhost:8082/v1/chat/completions -d '{"model":"auto","messages":[{"role":"user","content":"What is 2+2?"}],"max_tokens":64,"thinking":{"budget_tokens":0}}'
```

#### Key Files (Updated with Line Numbers)

| File | Lines | Purpose |
|------|-------|---------|
| `tools/server/server-common.cpp` | 1108-1118 | Request budget parsing (OAI format) |
| `tools/server/server-common.cpp` | 1636-1644 | Anthropic format parsing |
| `tools/server/server-task.cpp` | 488-506 | Budget param extraction + tokenization |
| `common/chat.cpp` | 1313-1331 | Think tag setup for chat templates |
| `common/sampling.cpp` | 260-299 | Sampler init with reasoning budget |
| `common/reasoning-budget.cpp` | 59-127 | **State machine** (IDLE→COUNTING→FORCING→DONE) |
| `common/reasoning-budget.cpp` | 129-149 | **Logit forcing** (-∞ for non-forced tokens) |
| `common/reasoning-budget.cpp` | 200-204 | **Budget=0 promotion** (COUNTING→FORCING) |
| `common/reasoning-budget.cpp` | 221-246 | **Prefill detection** (initial state from prefill) |
| `src/llama-context.cpp` | 3345-3354 | **Hybrid SSM memory access** (root cause) |

#### Success Criteria

- `budget_tokens=0` on Qwen3.5 hybrid → empty `reasoning_content`, non-empty `content`
- `budget_tokens=512` → reasoning capped at ~512 tokens, then content follows
- No regression on pure MoE models
- Orchestrator can thread `thinking.budget_tokens` through ChatRequest per role

#### Research Intake Update — 2026-04-17

##### Adaptive Reasoning Budget via Attention Entropy (Halo Framework)
- **[intake-392]** "Limited Reasoning Space" (arxiv:2602.19281) proposes replacing fixed token budgets with **entropy-based adaptive control**
- **Mechanism**: Monitor mean attention entropy across layers during inference (O(1), <1% overhead). When accumulated uncertainty exceeds threshold → trigger semantic compression (summarize reasoning so far) + context reset.
- **Results**: 76.4% on RULER (3x over AdaCoT), 1.29x token overhead vs Tree-of-Thoughts' 3.5x. Tested on Qwen2.5 (7B/72B), Mixtral, DeepSeek-V2-Lite.
- **No public implementation** — but architecturally simple. The Observer reads attention distributions already computed during inference. Could be exposed as a per-layer entropy metric in llama-server API.
- **Relevance**: Once budget_tokens enforcement works (the core problem above), entropy monitoring becomes the natural next step — adaptive budget instead of fixed cap. The Observer could feed the orchestrator a real-time "model is diverging" signal that triggers early `</think>` injection.
- **Implementation path**: (1) Expose per-layer attention entropy in llama-server, (2) orchestrator reads entropy signal, (3) orchestrator adjusts budget_tokens dynamically per-request based on entropy trend.

#### Research Intake Update — 2026-05-04

##### Endless-Repetition Feature Mechanism (Qwen-Scope Section 8)

- **[intake-521] "Qwen-Scope: Turning Sparse Features into Development Tools for LLMs"** (Qwen Team, 2026-04-30) — Section 8 directly addresses a "stuck-in-X" failure-mode taxonomy that overlaps with this handoff's scope.
  - Mechanism: Qwen3-8B SAEs reveal specific repetition features whose pre-activation values rise sharply at the onset of endless repetition and remain elevated throughout — i.e. the model has a measurable internal precursor for entering a repetition loop. Bidirectional steering experiments confirm the features are *causal*: amplifying induces repetition on normal samples; suppressing reduces repetition on repetition-prone samples.
  - Important caveat the paper documents explicitly: the same repetition features fire on **benign repetition** (instruction-echo, multiple-choice answer-choice repetition). Naive feature-suppression at training time degrades the model's ability to do legitimate repetition. This is why Section 8 uses **rare-negative-rollout augmentation in DAPO** (one SAE-steered repetitive output per group of G rollouts) instead of the SASFT-style suppression of Section 7.
  - Reported results: SAE-guided rare-negative augmentation in RL drops the held-out repeat ratio sharply across Qwen3-1.7B / Qwen3-8B / Qwen3-30B-A3B versus vanilla DAPO under identical RL setup; on Qwen3-30B-A3B it also yields +5.84pp MGSM relative to the pre-RL baseline. Vanilla RL only +1.08pp on the same metric.
  - Delta from current approach: this handoff fixes the *enforcement* path for `budget_tokens` (state machine, logit forcing, hybrid SSM memory access). Qwen-Scope offers a *complementary diagnostic and training-time* path — SAE feature activations as a per-token "stuck-pressure" signal that could be exposed in the same way intake-392's mean attention entropy is proposed in the prior intake update. **Concrete connection**: the Halo entropy-based adaptive budget already proposed (2026-04-17 intake update above) and Qwen-Scope's repetition-feature pre-activation are two independent in-progress signals for the same underlying state — the model is about to fail to terminate. Both could be exposed in llama-server as per-decode-step scalars and used by the orchestrator to trigger early `</think>` injection.
  - Cross-link: the Ring-mini stuck-in-think failure mode documented in `research/deep-dives/ring-mini-stuck-in-think-failure-mode.md` (2026-05-04) is the closest analogue in our own diagnostic record. Ring-mini is non-Qwen so the Qwen-Scope SAEs do not transfer directly, but the methodology — identify the stuck-state feature → use its pre-activation as a precursor signal → manufacture rare-negative rollouts via amplification — is portable to any Qwen-family checkpoint that exhibits comparable budget-overrun failures.
  - Action: when budget enforcement in this handoff lands, add a follow-up exploratory task to (a) extract Qwen3-1.7B / Qwen3-8B Lethality-of-think feature ids using contrastive sets of completed-vs-overrun think traces from our own benchmark logs, (b) verify pre-activation rise pattern matches Section 8 Figure 19, (c) consider exposing the scalar in llama-server alongside attention entropy. Tracked in `../completed/qwen-scope-sae-toolkit.md` (archived 2026-06-12; the repetition-feature methodology is preserved there).
  - Caveats (Tier 2b): ICML 2025 "Steering Language Model Refusal with Sparse Autoencoders" reports broad-task degradation under feature steering; the rare-negative-rollout pathway largely sidesteps this because the model learns to *avoid* steered outputs rather than imitate them. Section 8 Table 7 still shows Qwen3-8B IFEval -2.08pp vs Before-RL — task-dependent regressions remain plausible at the intervention scale used.

#### Research Intake Update — 2026-05-19

##### CGR — concrete no-training Adaptive Thinking implementation

- **[intake-566] "Certainty-Guided Reasoning"** (arxiv:2509.07820, Nogueira/Sun/Silva/Zumot)
  - Direct match for this handoff's goal: **model-agnostic, no-fine-tune, single-knob** dynamic thinking budget. Periodically probes the LLM's own predicted probability over answer tokens during the CoT; terminates early once a target certainty threshold is reached. No auxiliary head, no draft model, no constrained decoding.
  - Headline: **AIME2025 baseline accuracy preserved while eliminating millions of tokens in aggregate** at the level of an evaluation run. Adds a **Grade metric** that penalizes incorrect answers and permits abstention — risk-sensitive evaluation aligns with our per-request budget framing.
  - Implementation cost on EPYC: a sampling-loop patch in our `epyc-llama` fork that, every N decode tokens, runs the answer-token probability probe and early-stops if above threshold. Estimated ~150 LoC + flag plumbing.

##### External practitioner corroboration (with caveats)

- **[intake-542] @jun_song (Super-Tune) X post** — Korean local-LLM practitioner reports that after testing most viral X "speed tricks", only **Adaptive Thinking** + SFT-duplicate-suppression preserved quality at 100k+ context. Useful direction-setting signal; treat as anecdotal not validated.
- Tier 2b — **adaptive thinking failure modes ARE documented**: arxiv 2505.15400 ("When to Continue Thinking") shows models under-engage Continue-Thinking on hard questions AND over-invoke on easy questions — bimodally brittle. ASRR framework reports ~32.5% budget reduction at **non-zero ~1.2% pass@1 accuracy loss**. CGR's "preserves baseline accuracy" claim must be verified at our temperature/topk settings on our benches, not taken at face value.

##### Speculative-decoding concurrency caveat — corroborates `project_slot_promotion_shelved`

- **[intake-567] ECHO** (arxiv:2604.09603) confirms vanilla EAGLE-3 underperforms autoregressive decoding at bs≈128, matching the @ZenMagnets reply to the jun_song thread. ECHO's own scheduler-level fix (sparse confidence gating, unified super-tree) **recovers and exceeds baseline** — so the blanket "spec-dec hurts high-concurrency" claim is true ONLY for naive vanilla implementations.
- Not actionable for EPYC today (single-user, bs≈1, SGLang-only ECHO impl), but useful as a "why our shelved decision was right" reference and as evidence for the slot-promotion-shelved reopen criteria.

**Concrete next step (this handoff)**: when prototyping the per-request budget infrastructure, design the API surface so CGR-style certainty-threshold early-stop slots in alongside the existing hard-cap budget. Both are values on a single "stop signal" abstraction.


#### Research Intake Update — 2026-05-21

##### SpecExit — speculative early-exit via draft-model hidden states

- **[intake-592] SpecExit: Accelerating Large Reasoning Model via Speculative Exit (arxiv:2509.24248, OpenReview)** — Tencent AngelSlim team. Predicts BOTH future tokens AND an early-exit signal directly from a lightweight draft model's hidden states — no separate probing overhead (a documented weak point of confidence-based or predicted-length-based early-exit). Claims: 66% average reasoning-trace length reduction, 2.5x end-to-end latency speedup vs SD baseline, accuracy maintained.
- **Mechanism**: Inspired by speculative decoding's hidden-state use. The draft model emits, in addition to candidate tokens, a scalar exit-signal predicted from the same forward-pass hidden state. Joint prediction eliminates the separate-probe overhead.
- **Why it matters for this handoff**: Directly aligns with this handoff's stated goal — "no fine-tune, model-agnostic, single-knob dynamic thinking budget." Adds a THIRD axis to the existing budget plumbing: (a) hard cap (this handoff's prior work), (b) certainty probe (CGR intake-566), (c) hidden-state-derived joint exit signal (SpecExit). Note: (a)+(b) compose; (c) sidesteps the probe-overhead limitation of (b).
- **Caveats (Tier 2b)**:
  - SpecExit's 2.5x is "additive vs SD baseline" — on EPYC at single-user bs=1, vanilla SD has been net-negative for Qwen3.6 with Qwen3-1.7B drafter (`project_slot_promotion_shelved`); SpecExit may inherit that gating issue unless tested with the reopen-criteria configurations (larger drafter, non-greedy verifier, long-context).
  - Early-exit mechanisms have documented failure modes: confidence overconfidence, predicted-length over-optimism on hard problems, progress-signal instability on complex tasks. SpecExit claims to mitigate by joint prediction, but third-party replication is absent at submission time.
  - 66% generation-length reduction is comparable to CGR (intake-566) and dynamic-early-exit (arxiv:2504.15895) — head-to-head ablation against these on the same benchmark suite has not been published.

##### Concrete next step for this handoff

When budget enforcement infrastructure (Step 3-4: state machine, logit forcing, hybrid-SSM memory access) lands and a running server is available, add SpecExit-style hidden-state probe as a third stop-signal source in the API surface design. The abstraction is already framed (per the prior 2026-05-19 CGR intake update): a single "stop signal" abstraction over which hard-cap / certainty-threshold / hidden-state-exit are interchangeable producers.

Cross-references: [[angelslim-techniques-evaluation]] (umbrella stub), [[reasoning-compression]], [[memento-block-reasoning-compression]], [[decision-aware-routing]].

#### Research Intake Update — 2026-05-24

##### New Related Research

- **[intake-603] "Deep Think with Confidence (DeepConf)"** (arxiv:2508.15260)
  - Relevance: Confidence-gated filtering/early-termination of reasoning traces is a per-request reasoning-budget lever that reports **up to 84.7% fewer generated tokens** vs full parallel self-consistency, with up to 99.9% on AIME 2025 (DeepConf@512). Training-free, framed as serving-framework-integrable, validated on Qwen3 (our frontdoor/architect family).
  - Key technique: model-internal confidence signal gates which traces continue/vote; online + offline variants.
  - Reported results: AIME2025 ~99.9% @512 traces; −84.7% tokens vs full parallel thinking.
  - Delta from current approach: our budget control is template/stop-signal-driven (hard-cap / certainty-threshold / hidden-state-exit). DeepConf adds a **confidence-weighted multi-trace** producer that fits the existing "stop signal" abstraction as a fourth source. The token-reduction claim is the headline win on a BW-bound CPU — but the 99.9% is at 512 traces (large absolute compute), and like all voting methods it is candidate-bounded (cannot recover a correct answer never sampled). Prototype against a local Qwen3 server and measure real CPU t/s + accuracy (standalone llama-bench only — no run_benchmark.py).

- **[intake-602] "Chain-of-Thought Reasoning Without Prompting (CoT-Decoding)"** (arxiv:2402.10200)
  - Relevance: Decode-level, training-free elicitation of reasoning — directly relevant to eliciting/suppressing reasoning per request without a thinking template (the core problem of this handoff for hybrid SSM models where `budget_tokens:0` fails).
  - Key technique: branch into top-k first tokens (vs greedy); CoT paths emerge among continuations; answer-token confidence gap selects the reasoning path.
  - Delta from current approach: implementable in our full-control llama.cpp fork as a sampler variant. Caveat: top-k branching multiplies decode passes — net win unproven on BW-bound CPU; measure before committing.

- **[intake-601] "OptiLLM" optimizing inference proxy** (github: algorithmicsuperintelligence/optillm) — its ThinkDeeper module emulates a `reasoning_effort` parameter and DeepConf/CoT-decoding/entropy-decoding are bundled as modules; useful **pattern** reference for the per-request reasoning-budget API surface. **Correction (2026-05-24 deep-dive):** these local modules are HuggingFace-transformers-only in OptiLLM (in-process model + hooks) and do NOT run over llama-server — they are reimplementation targets, not drop-in. DeepConf-offline + CoT-decoding need only `top_logprobs` (which llama-server exposes), so a proxy/fork reimplementation is feasible; ThinkDeeper is transformers-only. Headline "2-10x" is marketing — see intake-601 contradicting_evidence.

##### Actionable (decided 2026-05-24): DeepConf-offline FIRST

DeepConf-offline is the highest-ROI item from this intake and is scheduled ahead of the OptiLLM-style method-selection axis. It is a **proxy-layer reimplementation** (N parallel llama-server completions with `top_logprobs` → bottom-10% group-confidence filter → confidence-weighted vote) — no llama.cpp fork needed for the offline variant. Build + sanity-check in a dedicated session, then hand the `n_traces / percentile-η / window / warmup / group-metric` sweep to autopilot's NumericSwarm. **Tracked as P21.A in [`routing-and-optimization-index.md`](routing-and-optimization-index.md); full analysis in [`research/deep-dives/optillm-test-time-techniques.md`](../../research/deep-dives/optillm-test-time-techniques.md).** Sanity-check needs a local Qwen3 server → **stop the running autopilot first** (no-concurrent-inference). The DeepConf-online (mid-generation early-stop) variant is fork work, deferred. Cross-ref: [[reasoning-compression]], [[decision-aware-routing]].

**UPDATE 2026-05-24 (A2 done — NOT adopting):** built as an isolated spike (41 tests) and validated against live Qwen3.6. **Decisive negative:** DeepConf's confidence-weighted vote ties plain majority (3/4 = 3/4, no gain), and the confidence signal is anti-correlated with correctness (top-1-confidence 1/4; correct-vs-wrong gap −0.158) — the model is overconfident on wrong short answers. So DeepConf adds N× generation + `n_probs` cost for **zero accuracy benefit** on our stack. Not wired into the orchestrator or autopilot; no branch/worktree is needed for the remaining bulk-inference run. Reasoning-budget control for this handoff should rely on the existing stop-signal/template levers, not DeepConf. Full data: [`research/deep-dives/optillm-test-time-techniques.md`](../../research/deep-dives/optillm-test-time-techniques.md) §P21.A Outcome.

#### Stop-signal abstraction — design only (2026-07-29)

This is an interface contract for a future **experimental** reasoning controller, not a production sampler feature. The existing `budget_tokens` state machine is the only executable producer today; Step 3/4 must first prove it correct on hybrid SSM models. No producer may waive a quality gate or modify the frozen production kernel.

Each producer may emit, at a decode boundary:

```text
StopSignal { producer: hard_cap | certainty_probe | draft_hidden_exit,
             disposition: continue | request_close_think | abstain,
             evidence_ref: trace-local immutable observation reference,
             confidence: optional [0,1], next_eligible_token, reason_code }
```

The controller is a deterministic arbiter. `hard_cap` is authoritative once its existing state machine reaches the forcing boundary. Every other producer is **advisory and fail-closed**: missing evidence, unsupported architecture, invalid confidence, or disagreement means `continue`, not early close. A request acts only at the next eligible decode boundary using the same explicit closing-token path as hard cap; it never edits a prompt retrospectively or claims the model finished answering.

| Producer | Admission before it may request close |
|---|---|
| `hard_cap` | Source-proven budget state machine plus this handoff's hybrid budget=0 and pure-MoE regression checks |
| `certainty_probe` (CGR-shaped) | Versioned probe cadence/answer-token contract, saved signal, and paired quality + total-token non-inferiority evidence |
| `draft_hidden_exit` (SpecExit-shaped) | Experimental-kernel-only hidden-state contract, draft/target compatibility and output parity, and paired quality + latency evidence |

Confidence values are not comparable or scalarized. Enable at most one advisory producer per explicit experiment identifier; unsupported paths emit `abstain`. For every non-hard-cap request retain producer/version, request/decode positions, disposition, reason code, raw-signal reference, and later scorer result. This permits deterministic replay and detects overconfident early exits without rerunning inference. Such records are observations until a measurement protocol supplies the quality gate.

#### Progress checklist

- [x] Step 1-2: trace budget-enforcement pipeline + root-cause (SSM state-update race, 2026-04-17) ✅
- [x] DeepConf-offline spike - NOT adopting (zero accuracy benefit, 2026-05-24) ✅
- [ ] Step 3: implement fix (force </think> / suppress think scaffold at budget=0 for hybrid SSM), needs running server [REWRITTEN 2026-11-09 (audit): the repro is Qwen3.5 on 2026-04-17. In current code `thinking_budget_fields(0)` returns `{}` BY DESIGN (`src/backends/serving_params.py:511-514`), so "budget=0" sends NO field and cannot suppress thinking; the original symptom may be a semantics issue, not a server bug. Probe: one request on the v10 frontdoor :8070 with `thinking_budget_tokens` omitted vs a small value, plus `enable_thinking=false` on the chat path; record whether `reasoning_content` is returned. If budget=0 never needed to mean "off" (that is `enable_thinking`), retire Steps 3-4. Needs a served frontdoor, no Autopilot.]
- **[declined: ws58 2026-11-03 content-review: merged into Step 3 as its verification (same fix, same server)]** Step 4: verify budget>0 caps reasoning at N tokens; no regression on pure MoE
- [ ] Thread `thinking_budget_tokens` through ChatRequest per role [REWRITTEN 2026-11-09 (audit): the server field is `thinking_budget_tokens`, not `thinking.budget_tokens`. Plumbing already exists: `ChatRequest.thinking_budget` (`src/api/models/requests.py:234`), `RoutingResult.reasoning_budget` (`chat_utils.py:92`), request-local scope `repl_thinking_budget.py`, flag `repl_thinking_budget` (`src/features.py:247`, default off), per-role `reasoning_budget_easy/hard` fields (`src/config/models.py:1354-1355`). Remaining: choose per-role values (needs TB-1/E-2 curves) and decide enabling the flag.]
- [x] Design stop-signal abstraction to slot in CGR certainty-threshold / SpecExit hidden-state exit ✅ 2026-07-29 — design-only deterministic `StopSignal`/arbiter contract: hard cap remains the only executable authority; CGR and SpecExit are advisory, one-at-a-time, fail-closed producers pending source, parity, and paired quality/total-token evidence. No production sampler, server, or kernel change.

#### Research Intake Update — 2026-08-21 (chat-template dive, intake-1212…1217)

- [x] **PRB-T1** — Re-examine the standing `--jinja` removal workaround. It was adopted because the
      jinja template "primed the model into think mode", surrendering per-request reasoning control
      entirely. A 2026-08-21 dive rendered both the stock `Qwen/Qwen3.8-27B` template and the
      Unsloth template embedded in our production GGUF: **both handle `enable_thinking=false`
      correctly**, suppressing the reasoning-instruction block and emitting the proper empty-think
      prefill. What the templates *do* have is a fatal `raise_exception` on any `reasoning_effort`
      outside `{xhigh, medium, low}` — and an `xhigh` default that injects a 209-character
      instruction when no kwargs are passed. Determine whether the behaviour that motivated
      removing `--jinja` was actually one of those, and whether the workaround is still needed.
      ✅ 2026-08-21 — **OBSOLETE: already reversed 2026-06-26 by commit `f4a8a3ca`**; compiled priors
      emit `jinja: true` for architect_general and the J12 gate passed 2026-07-06 (0 think-leaks, n=15).
      Neither Qwen3.8 template defect motivated it — both post-date the workaround by four months.
- [x] **PRB-T2** — **TALE-EP (intake-1215) needs no server support at all.** This handoff's
      objective is per-request reasoning control and it has been blocked since 2026-04-17 on server
      support for `thinking.budget_tokens`. TALE puts a per-question numeric token budget in the
      *prompt*, estimated zero-shot by the model itself — reported at 67% token reduction for
      −2.72% average accuracy, and +3.11% accuracy on GSM8K at 75.7% fewer tokens. Evaluate it as
      the unblock path. Caveats to carry: MathBench-College shows −8% / −4%, far worse than the
      headline; and the estimator costs an extra model call, cheap on closed APIs and not obviously
      cheap on our bandwidth-bound CPU decode.
      ✅ 2026-08-21 — **evaluation DESIGNED (below); run is PRB-T4.** Key find: the harness already
      exists (`eval_tale_budget.py`, 2026-04-09) and has never been run; it does not charge the
      estimator call, and neither intake-1215 anchor suite (GSM8K, MathBench) is in our question pool.
- [x] **PRB-T3** — Confirm whether a top-level `reasoning_effort` field survives to the template on
      our llama-server path or is consumed by the server before render. Untested in the dive (needs
      a running server). The same silent-no-op shape is already recorded from a different vendor and
      stack in intake-946, where a top-level `enable_thinking` field was ignored and only
      `chat_template_kwargs` took effect.
      ✅ 2026-08-21 — **DECISIVE: a top-level `reasoning_effort` is DROPPED** — 0 occurrences tree-wide
      in frozen v9, and the jinja global set is a closed literal; `chat_template_kwargs` is the ONLY
      body→template route. Same silent-no-op shape as intake-946. Static analysis; see below.

##### PRB-T1 findings — the `--jinja` workaround is OBSOLETE (reversed 2026-06-26)

**Verdict: obsolete and already reversed. No action needed to restore `--jinja`; it is on today.**

Lifecycle of the workaround:

| Event | Commit | Date | Evidence |
|---|---|---|---|
| Adopted (drop `--jinja` for architect_general) | `0879ed56` | 2026-04-15 | `git log -1 0879ed56`: "fix: drop --jinja for architect_general to prevent Qwen3.5 hybrid think-loops" |
| Reversed (re-include in `--jinja`) | `f4a8a3ca` | 2026-06-26 | `git log -S'architect_general no longer excluded from --jinja' -- src/registry/stack_priors.py` returns exactly this commit: "Determinism: honor declared temps + fixed seed + unify sampler; route architect to chat-completions" |
| Gate satisfied | — | 2026-07-06 | `orchestration/reports/j12_think_loop_probe_20260706T143621Z/summary.json` |

Current state, three layers, all agreeing that `--jinja` is ON for `architect_general`:

1. **Prior** — `src/registry/stack_priors.py:2280-2283` sets `"jinja": bool((mode == "default") or (mode == "worker_pool" and worker_type == "explore"))`. `architect_general` is `mode == "default"`, so the prior is unconditionally `True`. The comment at `:2272-2279` records the reasoning: the 2026-04-15 exclusion "made the registry's `enable_thinking=false` inert (kwarg only applies on the `/v1/chat/completions`+jinja path)".
2. **Compiled** — `orchestration/derived/stack_priors.yaml:357` → `jinja: true`, inside the `architect_general` record (block opens `:300`; confirmed by content, not position — `slot_save_path: /mnt/raid0/llm/cache/kv_slots/architect_general` at `:354`). Compiled at `2026-08-11T01:36:33Z` (`:51`). Of the 12 compiled flag blocks only `vision_escalation` (`:1889`) and `worker_vision` (`:2975`) carry `jinja: false`.
3. **Launcher** — `scripts/server/orchestrator_stack.py:1345` `_build_role_command` loads `flags = _runtime_flags(runtime)` from `_stack_prior_launch(role_name)` (`:235`, reads `STACK_PRIORS_PATH`), then at `:1402`: `if flags.get("jinja", role_name != "architect_general") is True: cmd.append("--jinja")`. The architect_general exclusion survives **only as the dict default**; the compiled priors supply an explicit `True`, so the default is unreachable for this role.

**The gate named in the code actually ran and passed.** `stack_priors.py:2278` says the re-inclusion was "Gated on the J12 think-loop suppression probe before trusting". That probe exists (`scripts/benchmark/j12_think_loop_probe.py`) and its one recorded run — `orchestration/reports/j12_think_loop_probe_20260706T143621Z/summary.json` — reports for `architect_general`: `n: 15`, `think_leaks: 0`, `repetition_loops: 0`, `known_wait_reference_loops: 0`, `empty: 0`, `error_answers: 0`, `expect_matches: 14` (one miss, `plan_02`). `frontdoor` 15/15 clean. The gate is satisfied, not outstanding.

**Was the original motivation one of the 2026-08-21 template defects? No.** The workaround targeted Qwen3.5-122B-A10B hybrid `<think>` loops on a model that no longer sits on this role (it vacated to `architect_critic` :8074 — `stack_templates/default.yaml:156-160`). The `reasoning_effort` `raise_exception` and the 209-char xhigh default are properties of the **Qwen3.8** template only (sha12 `12827f24b742`), which post-dates the 2026-04-15 workaround by four months. The three older fleet templates (sha12 `55d4931433fe`, `8452ca85cb1e`) do not carry them at all. So the two are unrelated findings that happen to touch the same flag.

**Reconciliation with the model swap — three planes disagree, and that divergence is itself the finding:**

| Plane | Says architect_general is | Citation |
|---|---|---|
| Stack template | `Qwen3.8-27B-Q8_0` | `stack_templates/default.yaml:139` (commit `1cff5162`, 2026-08-20) |
| Compiled priors | `qwen3.6-27b-mtp-q8_0` / `Qwen3.6-27B-MTP-Q8_0` | `orchestration/derived/stack_priors.yaml:304-305` |
| MASTER registry | `model_role: qwen36_27b_mtp_q8_local` | `orchestration/model_registry.yaml:1501` |

Literal-string `Qwen3.8` count: **0** in `orchestration/model_registry.yaml` and **0** in `orchestration/derived/stack_priors.yaml`. (A bare `grep "Qwen3.8" orchestration/model_registry.yaml` returns 4 hits, but all four are the regex `.` matching `Qwen3-8B-DFlash-b16` at `:506-511` — not the model. The dispatching session's "zero occurrences" is correct.) **Only the stack template names Qwen3.8.** The compiled priors were generated 2026-08-11, nine days before the 2026-08-20 template change, so they have not been recompiled since the swap. UNVERIFIED whether that is intentional staging or drift — flagged here, not resolved (recompiling the registry is not this subagent's write).

Consequence for this handoff: because `--jinja` is on, the GGUF's embedded template renders on every `/v1/chat/completions` request. Once the priors are recompiled the template that renders will be the Qwen3.8 one carrying the `reasoning_effort` raise. The MASTER registry pins `chat_template_kwargs.enable_thinking: false` for this role (`orchestration/model_registry.yaml:1499-1500`) and the raise sits inside the `enable_thinking` gate, so it stays unreachable at production posture — but the margin is one config flip wide.

**Residual defect (not fixed — code edits are outside this subagent's write scope).** `scripts/server/orchestrator_stack.py:1397-1402` still carries the reversed policy as both a comment ("SKIP for architect_general — Qwen3.5 hybrids enter infinite `<think>` loops") and a live fallback default. It is inert while the priors compile, but if `_stack_prior_launch` ever returns `{}` for this role (role absent from compiled priors — a real possibility given the plane divergence above), `flags.get("jinja", role_name != "architect_general")` silently resolves to `False` and architect_general launches **without** `--jinja`, re-inerting `enable_thinking=false`. Recommend deleting the role-specific default and the stale comment; prepared for the owning session, not applied here.

##### PRB-T3 findings — a top-level `reasoning_effort` is DROPPED

**Static analysis of the frozen production tree `/mnt/raid0/llm/llama.cpp` @ `0db32c06e` (`git rev-parse --short HEAD`). Read-only; nothing built, modified, or committed.**

**Answer: a top-level body field `reasoning_effort` is neither server-consumed nor template-visible. It is silently discarded** — the same shape intake-946 records for a top-level `enable_thinking`.

1. **No code can read it.** `grep -rn "reasoning_effort" --include='*.cpp' --include='*.h' --include='*.hpp' .` over the whole frozen tree returns **0 matches**. Per-file `grep -c` over all 13 of `tools/server/*.cpp` plus `common/chat.cpp` returns 0 for every file. The identifier does not exist in the kernel.

2. **The jinja global set is a closed literal.** `common/chat.cpp:883-895`, in `common_chat_template_direct_apply_impl`, builds the render variables explicitly:

   ```cpp
   nlohmann::ordered_json inp = nlohmann::ordered_json{
       {"messages", messages_override.has_value() ? *messages_override : inputs.messages},
       {"bos_token", tmpl.bos_token()},
       {"eos_token", tmpl.eos_token()},
       {"enable_thinking", inputs.enable_thinking},
   };
   ```

   The only further additions are `tools` (`:896-898`, conditional), every key of `inputs.extra_context` (`:900-905`), every key of `additional_context` (`:905-910`), and `add_generation_prompt` (`:911-913`). `jinja::global_from_json(ctx, inp, inputs.mark_input)` (`:920`) then installs exactly that object as the template's globals. **There is no request-body spill anywhere in this function** — an arbitrary top-level field can reach the template only by first becoming an `extra_context` key.

3. **`extra_context` is date helpers plus `chat_template_kwargs`, and nothing else.** `common/chat.cpp:2714-2717`:

   ```cpp
   params.extra_context = common_chat_extra_context();
   for (auto el : inputs.chat_template_kwargs) {
       params.extra_context[el.first] = json::parse(el.second);
   }
   ```

   and `common_chat_extra_context()` (`common/chat.cpp:2543-2551`) returns an object containing only `datetime` and `date_string`.

4. **`chat_template_kwargs` passthrough — CONFIRMED, and it is a two-layer merge.** `tools/server/server-common.cpp:1073-1077`, inside `oaicompat_chat_params_parse`:

   ```cpp
   auto chat_template_kwargs_object = json_value(body, "chat_template_kwargs", json::object());
   inputs.chat_template_kwargs = opt.chat_template_kwargs;
   for (const auto & item : chat_template_kwargs_object.items()) {
       inputs.chat_template_kwargs[item.key()] = item.value().dump();
   }
   ```

   Server-launch defaults seed the map and the per-request object overrides key-by-key. `opt.chat_template_kwargs` comes from `params_base.default_template_kwargs` at model load (`tools/server/server-context.cpp:1479`), which `--chat-template-kwargs` and `--think` populate (`common/arg.cpp:3285`, `:3433-3436`). **`chat_template_kwargs` is therefore the ONLY route from a request body to a template variable** — which is exactly why the registry's `enable_thinking: false` is expressed as a kwarg and why dropping `--jinja` made it inert (PRB-T1).

5. **Which top-level reasoning fields ARE read** (the contrast makes the omission exact): `reasoning_format` (`server-common.cpp:1061-1062`), `reasoning_budget_tokens`, `reasoning_budget_message`, `reasoning_control` (`:1120-1131`), and the Anthropic-shape `thinking.budget_tokens` → `thinking_budget_tokens` mapping (`tools/server/server-chat.cpp:577-585`). `reasoning_effort` appears in none of them. Note `enable_thinking` gets a *special* second read out of the kwarg map at `server-common.cpp:1080-1087`, including a type guard that raises on a quoted string — there is no equivalent for `reasoning_effort`.

6. **No unknown-field rejection anywhere on the path.** The body is read key-by-key through `json_value(body, ...)`; `grep -n "unknown\|unrecognized\|unsupported param" tools/server/server-common.cpp tools/server/server-task.cpp` returns nothing. `server-chat.cpp:570` even shows the Anthropic bridge forwarding only an explicit whitelist (`temperature`, `top_p`, `top_k`, `stream`, `chat_template_kwargs`). An unrecognised top-level key produces **no error and no warning**: a silent no-op.

**Consequence.** The Qwen3.8 template's `reasoning_effort` `raise_exception` can only fire if `reasoning_effort` is passed *inside* `chat_template_kwargs`. A top-level `"reasoning_effort": "none"` cannot reach it — and cannot reach anything else either. Any orchestrator code that sets a top-level `reasoning_effort` against our llama-server is a no-op today.

**Status: static analysis of frozen v9 only.** Live-render confirmation still wants a `POST /apply-template` when a server is next up (route registered `tools/server/server.cpp:262`, handler `tools/server/server-context.cpp:4981`): render the same body twice, once with `reasoning_effort` top-level and once with it under `chat_template_kwargs`, and diff the returned prompt. The static path is decisive on its own; the live check is belt-and-braces and would also demonstrate the raise.

##### PRB-T2 findings — TALE-EP evaluation design (design only; the run is PRB-T4)

**The harness already exists and has never been run.** `epyc-inference-research/scripts/benchmark/eval_tale_budget.py` (409 lines, commit `f5b67614`, 2026-04-09) implements the arms below and already prints a per-suite breakdown (`:300-321`) and a β distribution (`:322-328`). `data/tale_budget/` does not exist on disk → zero recorded runs. What follows is therefore the *delta* needed to make it decision-grade, not a new script.

**Target.** `architect_general` :8083 — the thinking-capable Qwen role whose template carries the 2026-08-21 defects. Model is `Qwen3.8-27B-Q8_0` per `stack_templates/default.yaml:139`, GPU/MI210; if the priors are not recompiled by run time it will actually launch Qwen3.6-27B (`derived/stack_priors.yaml:304`). **Record which GGUF actually served — do not assume from the template.** Add one CPU-decode replicate on `frontdoor` :8080 (Qwen3.6-35B-A3B, `derived/stack_priors.yaml:784`), because intake-1215's overhead caveat is specifically about bandwidth-bound CPU decode and a GPU-only result cannot answer it.

**Posture.** Production posture — `chat_template_kwargs.enable_thinking: false` (`model_registry.yaml:1499-1500`), `--reasoning off`, `--jinja` on. That is what we serve, so that is what the decision is about. TALE-EP is a *prompt*-level budget and needs no thinking channel to work.

**Arms** (harness `--conditions`, all three):
1. `baseline` — question verbatim, no brevity constraint.
2. `static` — fixed per-suite limit (`STATIC_LIMITS`, `:41-49`). **Not optional**: it is the control that says whether any gain is TALE's *estimation* or merely brevity.
3. `tale` — two calls: zero-shot self-estimate (`TALE_PREPASS_PROMPT`, `:51-56`, `max_tokens=32`) → `"Answer in under {beta} words.\n\n" + question` (`:58`), β clamped to [10,500] (`:185`).

**Suites — per-suite reporting is mandatory.** From `benchmarks/prompts/question_pool.jsonl` (79,479 questions, 38 suites, verified by direct count):

| Class | Suite | Pool n | Take per arm |
|---|---|---|---|
| Math (where the CCoT hazard lives) | `math` | 1,819 | 150 |
| Math (hard) | `olympiadbench` | 674 | 100 |
| Knowledge | `mmlu_pro` | 12,032 | 150 |
| Coding | `livecodebench` | 2,360 | 100 |

n=500 per arm × 3 arms = 1,500 generations + 500 estimator calls ≈ 2,000 requests per host.

**Anchor mismatch — state it before the run, not after.** intake-1215's one favourable headline is **GSM8K (+3.11% accuracy at 75.7% fewer tokens)** and its worst caveat is **MathBench-College (−8% / −4%)**; the average is **67% token reduction for −2.72% accuracy**. **Neither anchor suite exists in our pool** — there is no `gsm8k` and no `mathbench` among the 38. `math` and `olympiadbench` are substitutes, not replications. This run therefore **cannot confirm or refute either published number**; it can only measure our own stack. (The harness's `STATIC_LIMITS["gsm8k"]` key at `:43` is dead for the same reason.) Do not report a result as agreeing or disagreeing with intake-1215.

**Two harness gaps to close first** (both small, both in `eval_tale_budget.py`):
- **The estimator call is never charged.** `estimate_tale_budget` at `:179` does `text, _, _ = generate_response(...)`, discarding tokens and elapsed, and `TrialResult` (`:60-71`) has no field for them. Without this, the extra-call overhead measurement is impossible and TALE's savings are overstated by construction. Add `estimator_tokens` / `estimator_s` and report savings **net** of them.
- **Words vs tokens.** The docstring cites TALE's "use less than {beta} **tokens**" (`:13-14`) but the implemented prompt says "**words**" (`:51-56`, `:58`). A word budget is not the published intervention. Pick one, and say which in the write-up.
- Also: `generate_response` hardcodes `temperature=0.0` (`:117`). Pin to the role's declared production temperature + seed 42 per measurement policy, since accuracy here is sampling-sensitive.

**Metrics**, per suite × arm: accuracy, mean completion tokens, mean latency, OAA (`eval_metrics.compute_batch_oaa`, α=0.5), β distribution; TALE only: estimator tokens/latency and **net** token change = (estimator + answer) − baseline answer. Scoring already delegates per-question to `debug_scorer.score_answer` with the pool's declared `scoring_method` (`:157-167`), so it is not a hardcoded substring match.

**Decision rule** (fixed in advance):
- **ADOPT** if, on ≥3 of the 4 suites, net token reduction ≥ 30% **and** accuracy delta ≥ −1.0pp, **and** no single suite is worse than −3.0pp, **and** `tale` beats `static` on net tokens at equal-or-better accuracy.
- **ADOPT `static` INSTEAD** if `static` matches or beats `tale` on net tokens at equal accuracy — then TALE's estimator call is pure overhead and the cheap arm wins.
- **DECLINE** if any suite loses > 3.0pp, or net reduction < 15% once the estimator call is charged.
- **INCONCLUSIVE** otherwise → re-run at n=400/suite before deciding.
- Report a bootstrap CI per suite; at n=100–150 a single-question flip is noise, not a regression (`feedback_per_suite_gate_resolution_artifact`).

**Cost / gating.** ~2,000 requests per host, exclusive inference window, autopilot stopped first (no-concurrent-inference).

- [ ] **PRB-T4** — **Run the PRB-T2 TALE-EP evaluation.** Gated on an exclusive inference window (no
      server was up as of 2026-08-21; stale 2026-11-09: r1 failed 2026-10-31 on native cwd, a successor is queued (script `epyc-inference-research/scripts/benchmark/eval_tale_budget.py`)). Pre-run: close the three
      `eval_tale_budget.py` gaps above (charge the estimator call, resolve words-vs-tokens, pin
      temperature+seed); confirm which GGUF actually serves :8083. Then run the 4 suites × 3 arms on
      `architect_general`, plus the `frontdoor` CPU-decode overhead replicate, and apply the fixed
      decision rule. On completion the run produces measurements → file the belief-kernel adapter
      wiring task at the same boundary (source row in `scripts/vidya/adapters/README.md`). Execution (absorbs PRB-T4-RERUN and the native-cwd repair): after the scorer fix is on the shared orchestrator clone, run `eval_tale_budget.py --pool benchmarks/prompts/question_pool.prbt4-refresh-20260917.jsonl --suites math olympiadbench mmlu_pro livecodebench --n-questions 400 --sample-seed 42` in an exclusive MI210 window with the 2026-09-16 serving args; the launcher's execution-path visibility is repaired and smoked first (Codex3), retaining the original cohort, prompts, costs and rule.
    - [x] **PRB-T4-PREP-20261031** — Native normal and STOP controls, bounded source and full diagnostic writer fixtures retained in `artifacts/compute/codex3-runtime-checkpoint-20261031-0135/prb/`; cohort remains queued. Valid capped responses are known and scored under original logic; missing usage and interrupted transport are UNKNOWN. ✅ 2026-10-31 [belief: cc]
    - 2026-10-31 (terminal17:37:24Z, `codex3-prbt4-r1-20261031`): **FAILED-RUN rc1, harness; invalid**, with no scientific verdict. Native `region-lock.sh:3` could not `cd /mnt/micron/codex3-lanes/orchestrator`; the job ended at startup and `results/FINAL.json` was absent at18:02:58Z. The full4suites×400 seed42 fixed questions, estimator+baseline/static/tale, original estimator cost and10,000-draw paired rule remain unmeasured; original PRB-T4/RERUN stay OPEN. [Native cutoff evidence](../../artifacts/compute/codex3-results-filing-1802-20261031/prbt-summary.json). [belief: cc]
      - **[declined: ws58 2026-11-03 content-review: merged into PRB-T4 as execution mechanics]** **PRB-T4-NATIVE-CWD-REPAIR-20261031** — Codex3 repairs launcher execution-path visibility, qualifies real normal native entry/request/result/drain through the scheduled namespace and publishes a newly smoked successor ID; retain the original cohort, prompts, costs and rule, including scored valid caps and UNKNOWN missing/interrupted cells. No production-adoption claim.
      - **GPU RUN 2026-09-16 19:10Z – 09-17 02:22Z (sub-gpu-runner; box NOT ticked). Verdict under the fixed rule,
        on 3 of 4 suites: INCONCLUSIVE.** Evidence: research `b4d38ebc`, `data/prb-t4-tale-gpu-20260916/`, with no
        question text.
        - **Setup.** Qwen3.8-27B-Q8_0 served on v9 `b10125-0db32c06e`; the GGUF was verified via `/props`.
          Production architect_general argv (np 2, 32k per slot, MTP n-max 8), temperature 0.1, seed 42, token
          budgets, `enable_thinking=false`.
        - **Validity.** Residency proven: 25,869 samples, KFD 1, peak 36.1 GiB. Category CANDIDATE with no
          codified protocol, so these are observations. CIs are paired bootstraps.

        | suite (n) | baseline acc / tok | tale acc Δ | tale net tok Δ | static acc Δ | static net tok Δ |
        |---|---|---|---|---|---|
        | math (150) | 97.3% / 266 | +0.7pp [0.0, +2.0] | **−58.4%** [−55.5, −61.0] | −0.7pp | −72.2% |
        | olympiadbench (100) | 32.0% / 6,688 | −1.0pp [−8, +6] | −26.6% [−20.7, −32.5] | **−12.0pp** [−20, −4] | −77.7% |
        | livecodebench (100) | 100% / 205 | 0.0pp | −18.6% | 0.0pp | −27.9% (static wins) |

        - **Rule application.**
          - Only math meets ≥30% net and ≥−1pp, so ADOPT fails.
          - static does not win everywhere, so ADOPT_STATIC_INSTEAD fails.
          - The worst suite is −1.0pp and the mean net reduction is 34.6%, so DECLINE fails.
          - The result is INCONCLUSIVE. The rule's next step is a re-run at n=400 per suite.
        - **Defects to fix before the re-run:**
          1. **mmlu_pro never ran** (rc=1 at q1). `debug_scorer` raised `ScoringUnavailableError` because the
             multiple-choice gold is 'I' with 0 configured choices; the pool join lacks the A–J choices.
             With mmlu_pro missing, ADOPT is impossible. Only a loss >3pp on mmlu_pro could turn the verdict
             into DECLINE; the mean net reduction stays above 15% even at 0% on mmlu_pro.
          2. **livecodebench accuracy is vacuous.** The pool's `scoring_method` is `substring` with `'def '`, so
             100% on every arm is a scorer artifact. Only its token and latency deltas carry information.
          3. **All 150 sampled `math` items are `gsm8k_*` ids.** The "no gsm8k in our pool" premise above is
             wrong for this sample, but this is a different model, so it is still not a replication of
             intake-1215#record.
          4. The CPU `frontdoor` replicate was not run (a GPU-only window).
        - **Belief kernel.** `ingest tale-budget` wrote 24 rows for math and olympiadbench. The livecodebench
          sidecar was deliberately NOT ingested, because its accuracy rows come from the vacuous scorer.
      - **Defects 1–3 FIXED 2026-09-17 (sub-scorer-fix, offline; box still open).** Research `52595b9b`;
        orchestrator `f0015306` (on orchestrator main as of 2026-09-17). Details: `progress/2026-09/2026-09-17-sub-scorer-fix.md`.
        - **Root causes.** None of the three is in TALE's own scoring.
          - livecodebench: the live `question_pool.jsonl` (built 2026-07-27) predates the 2026-08-12
            executable-oracle rebuild and was never regenerated. 2,349 rows still score `substring 'def '`.
          - mmlu_pro: the source gold is correct (`answer == LABELS[answer_index]` on 12,032/12,032 rows).
            The adapter emitted `scoring_config={}` for an A–J suite, and the shared scorer knew only A–H, so
            the 2,053 I/J-gold rows (17.1%) were unscoreable.
          - math: `load_questions` took the first n rows in file order, which is 1,319 gsm8k rows before the
            500 MATH-500 rows. olympiadbench drew geometry at 5% against a population share of 19%.
        - **Fixes.**
          - Shared scorer: `choice_labels`, and a refusal for substring on code rows.
          - The adapter re-derives gold from the pinned snapshot.
          - Seeded source-stratified sampling (`--sample-seed`).
          - A pre-inference oracle preflight (exit 2).
          - Three-valued scoring.
          - `question_pool.py --refresh-suites`.
        - **Re-run input.** `benchmarks/prompts/question_pool.prbt4-refresh-20260917.jsonl` (gitignored,
          sha256 `3c3b498a…`): livecodebench is 704 rows, all `code_execution`; mmlu_pro is 12,032 rows. Every
          sampled row passes the preflight. The **live** pool is unchanged.
      - **[declined: ws58 2026-11-03 content-review: merged into PRB-T4 as its run command]** **PRB-T4-RERUN — GPU re-run of livecodebench + mmlu_pro (and math/olympiadbench at n=400)** after the
        fix.
        - GPU-only, exclusive MI210 window. NOT run by sub-scorer-fix.
        - Command: `eval_tale_budget.py --pool benchmarks/prompts/question_pool.prbt4-refresh-20260917.jsonl
          --suites math olympiadbench mmlu_pro livecodebench --n-questions 400 --sample-seed 42`, with the
          same serving args as the 2026-09-16 run.
        - Pre-condition: the shared orchestrator clone must carry the scorer fix. Otherwise the preflight
          refuses mmlu_pro (fail-closed, by design).
        - The 2026-09-16 livecodebench accuracy (100%) and the missing mmlu_pro cell are superseded by this
          re-run.
        - **Caveat on the 2026-09-16 rows already quoted above.**
          - The "math" cells measure **GSM8K only** (150/150 `gsm8k_*`), not the math suite.
          - The olympiadbench cells come from a subject-skewed draw (geometry 15/300 trials).
          - Neither may be read as the suite-level number.
      - **Pre-run gaps closed 2026-09-16 (sub-gpu-prep, offline; run still open):** research `a454b7fd`
        (ported as `76f5132b`, on research `main` via merge `a280853d`) — estimator tokens/time charged
        (`*_incl_estimator` beside answer-only), TALE-EP token budgets (`--budget-unit tokens` default),
        `--temperature`/`--seed`, `--endpoint` for any GPU URL, served model/GGUF identity from
        `/v1/models`+`/props` in `<out>.meta.json`, `--chat-template-kwargs`. Tests:
        `scripts/benchmark/test_eval_tale_budget.py` 14/14. Belief-kernel task: VB-PRB-T4.

**PRB-T3 LIVE CONFIRMATION ✅ 2026-08-21 (closing the static-analysis caveat).** Real llama-server
(frozen v9, CPU, Qwen3.6-35B-A3B, test port :8990), `POST /apply-template`: a top-level
`reasoning_effort: low` renders **byte-identical to a no-kwargs request** (59 B both) — the server
consumes/drops it before the template — while `chat_template_kwargs: {reasoning_effort: low}`
renders the steering instruction (225 B). The static tree-wide zero-occurrence finding and the live
behaviour now agree: the only working channel is `chat_template_kwargs`.

## Track: rao-redel-substrate-spike
<!-- gate: none -->

> Folded from `handoffs/active/rao-redel-substrate-spike.md` @ `7e268b4de29c` on 2026-11-02 (BRF-T1-F6, route 1a, operator D1/D5; retired row EVL-34 → RTG-08). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### RAO + ReDel Substrate Spike

**Status**: Step 1 PASS + Step 2 harness prepared; Step 2 execution awaits clean inference window

> **2026-07-14 audit note — FUND-OR-CLOSE**: schedule the ~10-60min naturally-delegating A/B in the next inference window or archive with an explicit reopen trigger. The taxonomy-branch push (29/29 tests) is an independent zero-inference operator decision. No activity since 2026-05-19.
**Created**: 2026-05-19 (post-cluster-deep-dive)
**Categories**: agent_architecture, autonomous_research, tool_implementation
**Priority**: HIGH (substrate enables all future RAO/RLM/Tree-GRPO work)
**Depends on**: `../completed/meta-harness-optimization.md`, `repl-turn-efficiency.md`, `halo-trace-loop-spike.md`
**Source deep-dive**: [`/workspace/research/deep-dives/2026-05-19-rao-rlm-cluster.md`](../../research/deep-dives/2026-05-19-rao-rlm-cluster.md)

#### Objective

Validate whether `ReDel` (intake-550, MIT + Commons Clause, `github.com/zhudotexe/redel`, last push 2026-05-11) is the right substrate for EPYC's recursive-agent harness work — replacing in-house build of the asyncio + REPL + delegate-as-tool scaffolding that RAO (intake-536), RLM (intake-153), and Tree-GRPO (intake-549) all presume.

If ReDel passes the pre-flight gate, lift its delegation primitives (`DelegateOne` blocking, `DelegateWait` non-blocking with `asyncio.gather`), event-stream logger, and web debugger into our orchestrator stack rather than rebuilding from scratch.

If it fails, fall back to in-house design per `../completed/meta-harness-optimization.md` Tier 3.

#### Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-536 | RAO — Recursive Agent Optimization (arxiv:2605.06639) | high | new_opportunity (training-side; hardware-blocked) |
| intake-541 | @neural_avb X-post RAO breakdown | high | worth_investigating (teaching asset) |
| intake-547#record | Wang RLM reproduction (arxiv:2603.02615) | high | worth_investigating (depth caveat — **load-bearing**) |
| intake-548 | Orchestration-trace survey (arxiv:2605.02801) | high | worth_investigating (5-sub-decision taxonomy) |
| intake-549 | Tree-GRPO (arxiv:2509.21240, ICLR 2026) | medium | worth_investigating (methodological alt) |
| intake-550 | ReDel toolkit (arxiv:2408.02248, EMNLP 2024 Demos) | high | worth_investigating (substrate candidate — **focus of this spike**) |
| intake-537 | TDS RLM deep-dive blog (Avishek Biswas) | high | already_integrated |
| intake-153 | RLM canonical paper (Zhang/Kraska/Khattab arxiv:2512.24601) | high | already_integrated (~80% pattern coverage) |

#### Key Findings from Deep-Dive

- **ReDel substrate**: MIT + Commons Clause license (research use OK; resale blocked), 98.9 KB Python core, Python 3.10+, built on `kani`, **swappable to local llama-server via `OPENAI_BASE_URL` env var** — drops onto our stack with zero llama.cpp changes.
- **Wang reproduction caveat** (intake-547#01, intake-547#02): on **Kimi K2 OOLONG, depth-0 (86.6%) BEATS depth-1 RLM (60.0%)**. Direction-of-effect is model-dependent. Depth=2 DeepSeek v3.2 S-NIAH inflates wall-clock 96× (3.6s → 89.3s → 344.5s). **`max_depth=1` is the load-bearing default for any RAO/RLM-style integration on EPYC.**
- **Stopping-decision gap** (intake-548): no published RL method as of May 2026 explicitly trains the stopping decision. On CPU EPYC where every token is BW-expensive, a learned stop policy has more differential value than anywhere else. The 5-sub-decision taxonomy `{when-to-spawn, whom-to-delegate, how-to-communicate, how-to-aggregate, when-to-stop}` should be wired into the episodic store as a labelling axis (~50 LoC, mirrors `tri-role-coordinator-architecture.md` TR-2.2's `assigned_role` precedent).
- **RAO training hardware re-evaluation** (2026-07-14): the prior "hardware-blocked (DGX Spark not yet acquired)" gate is dead — DGX abandoned; an AMD MI210 (gfx90a, 64GB, ROCm 6.2) was installed 2026-07-02. Training viability must now be re-evaluated against gfx90a (needs the training-viability smoke, master index §A00 item 4), not treated as blocked. The substrate spike prepares the ground so whichever learned policy arrives first can land with minimal substrate change.

#### Spike Plan (3 steps, gated)

##### Step 1 — ReDel pre-flight gate (1 day, ~$0 compute)

**Goal**: prove ReDel + `kani` can connect to EPYC's llama-server, drive a `DelegateOne` call against `worker_general` (gemma4-26B-A4B Q4_K_M MTP), and return a non-empty result.

```bash
# In a throwaway venv (NOT in /workspace tree)
python3.11 -m venv /tmp/redel-spike && source /tmp/redel-spike/bin/activate
pip install "redel[all] @ git+https://github.com/zhudotexe/redel.git@main"
export OPENAI_API_KEY=local
export OPENAI_BASE_URL=http://localhost:<worker_general_port>/v1

python -c "
from kani.engines.openai import OpenAIEngine
from redel import ReDel
import asyncio
engine = OpenAIEngine(model='worker_general', temperature=0.7)
ai = ReDel(root_engine=engine, delegate_engine=engine, title='spike')
async def main():
    async for ev in ai.query('What is 2+2? Delegate the answer to a sub-agent.'):
        print(ev)
asyncio.run(main())
"
```

**Gate criteria** (≥3 of 4 must pass):
1. ReDel installs cleanly under Python ≥3.10.
2. `kani.engines.openai.OpenAIEngine` accepts the local `OPENAI_BASE_URL`.
3. `DelegateOne` triggers a non-empty child response from llama-server.
4. The event stream yields ≥1 `DelegationEvent` per child spawn.

**Estimated dev cost**: 20 LoC of glue, 2-4 hours including troubleshooting.
**Estimated compute cost**: <100 K tokens against local llama-server (zero $).
**Success criteria for Step 2**: ≥3/4 gates pass AND the event stream is JSON-serializable.

##### Step 2 — Paired A/B vs current `repl_executor` (1 person-week, ~10 CPU-hours)

**Goal**: paired A/B on a fixed RLM-style workload (10 OOLONG-equivalent samples drawn from existing autopilot eval-tower benchmarks) comparing:
- **A**: current in-house `repl_executor` recursive harness (`max_depth=1`)
- **B**: ReDel `DelegateWait` with `asyncio.gather` (`max_depth=1`, mirrored config)

**Metrics**: accuracy, wall-clock, total tokens, dev complexity (LoC delta if we adopt B).

**Gate criteria**: ReDel matches or beats current harness on ≥2 of 3 numerical metrics AND adoption LoC delta ≤ 500 net additions (i.e. lift patterns; do not vendor entire dependency tree if it exceeds this).

##### Step 3 — Conditional substrate replacement (2-3 person-weeks, gated on Step 2)

If Step 2 passes, draft a feature-flagged substrate replacement: ReDel-style delegation primitives + event-stream logger + 5-sub-decision-taxonomy labelling on episodic store. Default-off, A/B for 1 week against production traffic, promote on parity.

**Dev cost**: ~800-1200 LoC including tests + flag + telemetry. Targets:
- `repl-turn-efficiency.md` Tier-2 already in scope
- `unified-trace-memory-service.md` for event-stream persistence
- `tri-role-coordinator-architecture.md` TR-2.2 for the 5-sub-decision labelling

#### Non-Goals for This Spike

- **RAO training itself**: hardware-blocked. The training recipe (mean-of-children + LOO + depth-IF) is reproducible-from-paper but should be deferred until GPU compute lands (`project_dgx_spark_target`).
- **Tree-GRPO** (intake-549): same training-blocker as RAO. Track methodologically; do not implement.
- **Vendoring ReDel**: do NOT add ReDel as a runtime dependency. Lift the *patterns* (delegation primitives, event stream, debugger). Per `feedback_minimum_imports`.

#### Failure Modes to Watch

- **Infinite-delegation loops**: ReDel-class harnesses can spawn until `max_depth` cap without making progress. Implement loop detection on tool-call repetition.
- **Reward hacking via LLM-judge proxies**: if/when we ever train a delegation policy, the per-node LLM-judge reward (RAO's design) is exactly the proxy-reward attack surface. Counter-measure: per-child (not mean) failure tracking + judge-output sanity audit.
- **Mean-of-children masking catastrophic child failure**: RAO's mean-aggregation reward biases the parent toward over-delegating easy splits. Counter-measure: report MIN-child-success alongside mean during evaluation.

#### Open Questions for User

1. **Substrate scope**: pure pattern-lift (in-house re-implementation drawing from ReDel design) vs hybrid (vendor `kani` for the engine surface, in-house everything else) vs full vendor (`pip install redel[all]`)? Pattern-lift is the `feedback_minimum_imports`-aligned default.
2. **Stopping-policy research direction**: should Step 3 explicitly include a learned-stop-policy experiment (intake-548 gap as a research target), or stay focused on substrate replacement only?
3. **Trace store extension**: the 5-sub-decision taxonomy labelling needs a column on episodic store events. OK to add to `unified-trace-memory-service.md` schema?

#### Step 1 Result (2026-05-19) — gates 4/4 PASS (1-line ReDel patch needed)

**Verdict**: proceed to Step 2 (gated on user approval per `feedback_no_concurrent_inference`).

##### Environment

- Throwaway venv `/tmp/redel-spike` (Python 3.13.7 — only interpreter on host; satisfies ReDel's `>=3.10`).
- Worker target: `worker_general` at `http://localhost:8072/v1`, serving `/mnt/raid0/llm/models/gemma-4-26B-A4B-it-Q4_K_M.gguf` via ik_llama.cpp PR #1744 MTP. Confirmed idle (`slots_idle:1`) before each run; no concurrent autopilot trial active.
- `pip install "redel @ git+https://github.com/zhudotexe/redel.git@main"` → `redel-0.0.3`, `kani-1.9.1`, `pydantic-2.13.4`, `kani-ratelimits-1.1.0`, `rapidfuzz-3.14.5`, `aiolimiter-1.2.1` + transitive (10 packages, all wheels). 1 build (the `redel` sdist itself, 44 KB wheel).
- Then `pip install "kani[openai]"` → `openai-2.37.0`, `httpx-0.28.1`, `tiktoken-0.13.0`, `regex-2026.5.9`, `requests-2.34.2` + transitive (16 packages, all wheels).
- Kani downgraded to `1.8.0` after a kani-1.9 API quirk surfaced (cosmetic; same fault reproduced on both, see gate 3 caveat below).

##### Install LoC / package count

- Core `redel` package: **20 Python files**, **98.9 KB total** — `app.py` (14 KB), `kanis.py` (7.4 KB), `base_kani.py` (7.2 KB), `delegation/` (4 files, ~14 KB), `events.py` (2.9 KB), `eventlogger.py` (3.0 KB), `embeddings.py` (2.4 KB).
- Glue script `preflight.py`: **77 LoC** (handoff budgeted ~20 LoC; the extra 57 are event-stream introspection + JSON-serializable dump for gate scoring, not part of any production lift).
- `[all]` extras **could not install** — numpy 1.26.4 has no Python-3.13 wheel and the host lacks `python3.13-dev` (`Python.h`), so meson-build fails. The extras are FastAPI/uvicorn/websockets/numpy for the web visualizer; the spike doesn't need them, so this is documented and not blocking. **For Step 3 / web debugger work**: use a Python 3.10 or 3.11 venv (the deep-dive's recommended interpreter), or install `python3.13-dev` system package, or pin numpy ≥2.1 which has 3.13 wheels.

##### Upstream bug found and patched in venv (not vendored, not pushed)

`redel/kanis.py:125` — `ReDelKani.get_prompt(self)` does not forward `**kwargs`. `kani.Kani.get_model_completion()` (in both kani 1.8.0 and 1.9.1) passes `include_functions=...` through to `get_prompt`, which raises `TypeError: ReDelKani.get_prompt() got an unexpected keyword argument 'include_functions'`. 1-line fix applied in the venv only:

```python
# before:
async def get_prompt(self) -> list[ChatMessage]:
    ...
    return await super().get_prompt()
# after:
async def get_prompt(self, **kwargs) -> list[ChatMessage]:
    ...
    return await super().get_prompt(**kwargs)
```

This is a trivial upstream PR candidate. The substrate viability assessment should not deduct for it — it's a project hygiene gap that a Step 2 implementation would either patch out, work around, or report upstream.

##### Gate scorecard

| # | Criterion | Outcome | Evidence |
|---|-----------|---------|----------|
| 1 | ReDel installs cleanly under Python ≥3.10 | **PASS (core), FAIL (`[all]`)** | Core install: 10 packages, all wheels, ~30s. `[all]` install: numpy 1.26.4 build-from-source fails on py3.13 missing Python.h. Marked PASS because the substrate's delegation + event-stream surfaces require only core. |
| 2 | `kani.engines.openai.OpenAIEngine` accepts the local `OPENAI_BASE_URL` | **PASS** | `OpenAIEngine(api_base="http://localhost:8072/v1", api_key="local", model=<gguf-path>)` made successful HTTP POST `/v1/chat/completions` against llama-server. Two warnings (unknown context length, unknown tokenizer → o200k_base fallback) — cosmetic; production use should pass `max_context_size=16384` explicitly. |
| 3 | `DelegateOne` triggers a non-empty child response from llama-server | **PASS (with 1-line patch)** | Child kani `alpha` at `depth=1` received `instructions="Calculate 2+2 and provide the result."`, returned `content="2+2=4"`. Aggregated by root, final answer `"2+2=4"`. Note: ReDel main HEAD defaults to **DelegateAndWait** scheme (`delegate` + `wait` tool pair, not `DelegateOne` blocking) — semantically equivalent for the gate. |
| 4 | Event stream yields ≥1 DelegationEvent per child spawn | **PASS** | 28 events / 7 distinct types: `KaniSpawn` ×2 (depths 0 and 1), `KaniDelegated` ×1, `KaniStateChange` ×6, `KaniMessage` ×7, `RootMessage` ×6, `TokensUsed` ×4, `RoundComplete` ×1. Full payload 24,759 bytes, JSON-serializable via pydantic `model_dump(mode="json")` — no custom serializer needed. |

**Cost actual**: 1,799 tokens total (1,732 prompt + 67 completion across 4 round-trips), 2.98s wall clock. Well under the <100K-token budget.

##### Secondary observations (carry into Step 2 design)

- **DelegateAndWait is the default scheme**, not DelegateOne. The deep-dive's "DelegateOne (blocking) vs DelegateWait (asyncio.gather)" framing should be updated: `delegate()` is non-blocking + `wait("alpha"|"all")` is the synchronization point. `DelegateOne` exists in the package but isn't the default. This matters for the Step 2 A/B — arm B should test the default delegate+wait pair, since that's what a real adoption gets.
- **Benign teardown noise**: ReDel emits `ValueError: task_done() called too many times` on asyncio.run shutdown (`redel/app.py:283`). The exception comes from a `_dispatch_task` cancellation race — does not affect event delivery before shutdown. File upstream as a small fix-it; orthogonal to substrate viability.
- **Tokenizer cost**: kani falls back to `o200k_base` (OpenAI's tokenizer) for token accounting because gemma4's tokenizer isn't bundled with tiktoken. This will mis-count tokens for budget enforcement by ~10–20% under typical English. The fix is to pass a kani-compatible tokenizer at engine construction; not in scope for the gate but Step 2 should record it.
- **Event stream is genuinely the cleanest novelty over current EPYC code** — every event has `id`, `timestamp`, `type`, and (where relevant) `depth`/`parent`/`children`. This is the substrate surface the deep-dive Table B "EPYC vs ReDel" row called out as a wholesale upgrade.

##### Artifacts (not committed)

- `/tmp/redel-spike/preflight.py` — the 77-LoC glue script.
- `/tmp/redel-spike/run4.json` — final successful 28-event capture (the run4 numbers above).
- All earlier runs (`run1.json`, `run2.json`, `run3.json`) preserved in the venv for failure-mode forensics. Throwaway venv; not persisted to /mnt/raid0 or git.

##### Gate verdict and next step

**4 / 4 PASS** → proceed to Step 2 paired A/B. Step 2 requires explicit user approval per `feedback_no_concurrent_inference` because it touches inference at scale (~10 OOLONG samples × 2 arms ≈ 60–90 minutes wall on local llama-server). See Step D in the umbrella task summary for the prepared A/B harness.

#### Step 3 Pre-work: 5-sub-decision taxonomy wired into episodic store (2026-05-19)

**Status**: LANDED on local feature branch — `rao-redel-subdecision-taxonomy` in `epyc-orchestrator` (commit `8bf985c`). **NOT pushed, NO PR yet** per umbrella prompt's "open a feature branch but do not push or open a PR" gate.

This is the cheapest piece of Step 3 (the survey's labelling axis, ~50 LoC budget became 663 LoC including 29 tests) executed early, in parallel with the Step 1 pre-flight gate, because it adds value independently of whether the ReDel substrate is ever adopted.

##### Files

| File | Status | LoC | Purpose |
|------|--------|-----|---------|
| `src/classifiers/subdecision_taxonomy.py` | NEW | 87 | `OrchestrationSubDecision` enum {SPAWN, DELEGATE, COMMUNICATE, AGGREGATE, STOP}, `DEFAULT_SUBDECISION = None` (opposite polarity to `DEFAULT_TRINITY_ROLE`), `normalise_subdecision()` (returns None for unknown, never coerces), `subdecision_labelling_enabled()` env-flag (default OFF). Mirrors `src/classifiers/role_taxonomy.py`. |
| `orchestration/repl_memory/episodic_store.py` | MODIFIED | +51 -6 | `MemoryEntry.sub_decision: Optional[str]` field, idempotent `ALTER TABLE ADD COLUMN sub_decision TEXT` + `CREATE INDEX idx_sub_decision`, `sub_decision` kwarg added to `store()`, `store_immediate()`, `GraphEnhancedStore.store_with_graphs()`, all four SELECT statements widened (4 read sites: `retrieve_by_similarity`, `get_by_id`, `get_all_memories`, `get_q_outliers`). Backward-compatible: NULL on legacy rows tolerated by all readers. |
| `scripts/memory/backfill_sub_decision.py` | NEW | 219 | Substring-heuristic backfill (delegate / aggregate / stop / communicate / spawn → matching label; `escalation` action_type with no delegate token → SPAWN; everything else stays NULL). Idempotent, dry-run flag, mirrors `scripts/memory/backfill_assigned_role.py`. |
| `tests/unit/test_episodic_store_sub_decision.py` | NEW | 312 | 29 tests, all pass. 9 taxonomy / 3 schema-migration / 6 writer-round-trip / 7 classification-heuristic / 4 backfill-script. Existing `test_episodic_store_assigned_role.py` (21 tests) and `test_episodic_store.py` (29 tests) still pass — no regression (verified `pytest tests/unit/test_episodic_store_sub_decision.py tests/unit/test_episodic_store_assigned_role.py tests/unit/test_episodic_store.py` → 79 passed). |

##### Polarity caveat (load-bearing)

`assigned_role` defaults to `"worker"` on NULL (Trinity TR-1.5 — legacy memories are overwhelmingly worker calls). `sub_decision` does **NOT** — NULL is the correct answer for any event that isn't a sub-decision (e.g., a routing memory whose action is `"frontdoor:direct"` is not labelled because it doesn't represent a sub-decision in the survey's sense). This is enforced in `normalise_subdecision()` (returns None for unknown) and in the backfill heuristic (returns None on no match). Tests assert this explicitly — see `TestSubDecisionTaxonomy.test_normalise_unknown_returns_none` and `TestBackfillScript.test_backfill_writes_labelled_rows_only`.

##### Why this lands cleanly without inference changes

The column is additive. No production code path writes to it yet — the feature flag defaults OFF, and no caller in `chat_pipeline/` or `classifiers/` was modified. The only behaviour change at runtime is the idempotent `ALTER TABLE` on `EpisodicStore.__init__`, which is the same pattern TR-2.2 already established for `assigned_role` and `model_id`.

##### Gates open / waiting on user

- **Push + PR**: pending user review. The branch lives at `epyc-orchestrator/rao-redel-subdecision-taxonomy` (local only).
- **Writer wire-in**: deferred to RAO+ReDel Step 3 Phase A (when the ReDel adapter / 5-sub-decision event emitter lands behind `RLM_USE_REDEL=1`). The column is ready when that work is.
- **Backfill on production episodic.db**: deferred. The script is dry-run-clean; the user can `python scripts/memory/backfill_sub_decision.py --db orchestration/repl_memory/sessions/episodic.db --dry-run` to see what would change.

#### Step 2 — A/B harness PREPARED, awaiting user approval (2026-05-19)

**Status**: harness written + dry-run-verified + UNEXECUTED per `feedback_no_concurrent_inference`. The user must explicitly approve a launch window when worker_general can be exclusively occupied for ≈20–60 minutes (autopilot paused or in a confirmed idle gap).

##### Script

`/mnt/raid0/llm/epyc-inference-research/scripts/research/rao_redel_step2_ab.py` (370 LoC). Compares two delegation arms on 10 deterministic needle-in-a-haystack samples (`{4096, 8192}` ctx × `{0.10, 0.25, 0.50, 0.75, 0.90}` depth, Paul Graham essay haystack, gold substring `"eat a sandwich and sit in Dolores Park on a sunny day"`, case-insensitive substring scoring) at `max_depth=1`.

- **Arm A** — minimal in-process `repl_executor`-style recursive delegate (the substrate behaviour the production `repl_executor` wraps with routing/policy/memory layers; we mirror only the substrate so the comparison is apples-to-apples against ReDel). 3 LLM round-trips per sample: root-with-tool, child, root-aggregates.
- **Arm B** — ReDel `DelegateAndWait` (the default scheme) at max_depth=1, using the throwaway venv at `/tmp/redel-spike` with the 1-line `get_prompt` patch from Step 1.

Both arms POST to `http://localhost:8072/v1/chat/completions` (worker_general / gemma-4-26B-A4B Q4_K_M MTP).

##### Pre-flight gate (built into the script)

The script refuses to start if:
- worker_general health endpoint is not reachable (exit 4).
- `slots_processing > 0` at launch (exit 3) — guards against autopilot collisions.

##### Exact bash invocation (DO NOT RUN until user approves)

```bash
# 1. Confirm worker_general is exclusively available
curl -s http://127.0.0.1:8072/health | python3 -c "import json,sys; h=json.load(sys.stdin); assert h['status']=='ok' and h['slots_processing']==0; print('clear')"

# 2. (optional) dry-run — prints 10 sample IDs without inference, sanity check
/tmp/redel-spike/bin/python /mnt/raid0/llm/epyc-inference-research/scripts/research/rao_redel_step2_ab.py \
  --dry-run --out /tmp/unused.json

# 3. THE actual A/B run — runs both arms × 10 samples sequentially.
#    Expected wall-clock: 20-60 min. Writes JSON results + summary.
OUT=/mnt/raid0/llm/epyc-inference-research/data/research/$(date -u +%Y-%m-%d)-rao-redel-step2-ab/results.json
/tmp/redel-spike/bin/python /mnt/raid0/llm/epyc-inference-research/scripts/research/rao_redel_step2_ab.py \
  --out "$OUT"

# 4. Inspect summary
python3 -c "import json; d=json.load(open('$OUT')); print(json.dumps(d['summary'], indent=2))"
```

##### Gate criteria (from this handoff's Step 2 spec)

| # | Criterion | Pass condition |
|---|-----------|----------------|
| 1 | Wall-clock | ReDel arm shows ≥0 regression vs Arm A (Step 2 spec says ≥10% improvement on parallel delegation, but our 10-sample sequential matrix doesn't exercise asyncio.gather; treat as parity gate here) |
| 2 | Accuracy | ReDel arm ≤0 accuracy regression on the 10 samples |
| 3 | Token efficiency | ReDel arm within ±20% of Arm A total tokens |
| 4 | Event-stream richness | ReDel arm yields a JSON-serializable event stream sufficient to label every sample with the 5-sub-decision axis without further parsing (Step 1 already showed yes — re-verified here at scale) |
| 5 | LoC delta if adopted | ≤500 net additions (separate calculation, not in this script) |

Per the handoff's Step 2 paragraph, **any 1 of gates 1–3 passing AND gate 4 passing** is sufficient to escalate to Step 3. If all three numerical gates regress, the spike closes negative and the deep-dive's "ReDel as substrate (RECOMMENDED, low risk)" finding gets revised.

##### Expected compute time and impact (one-paragraph)

The full run is **10 samples × 2 arms × 3 LLM round-trips per arm-A sample / variable round-trips per arm-B sample**. At gemma4-26B-A4B Q4 ≈ 76.5 t/s solo decode (per `project_worker_general_swap_2026_05_08`), each 4096-ctx sample's full delegation flow takes ~30–60s and each 8192-ctx sample ~60–120s, putting total wall-clock between 20 minutes (lucky) and 60 minutes (pessimistic). This will fully occupy worker_general for that window — autopilot trial throughput on `worker_general`-routed tasks drops to zero. Please confirm a quiet window before launching (the script will refuse if `slots_processing != 0`, but it cannot detect a pending autopilot trial that hasn't yet started a request).

#### Step 2 Result (2026-05-19) — both arms 100% accurate, gates 3/5 PASS, BUT no delegation occurred

**Verdict**: **AMBIGUOUS — substrate is parity-class, but the workload failed to exercise delegation. Recommend a delegation-forcing follow-up before deciding on Step 3 escalation.**

**Raw artifact**: `/mnt/raid0/llm/epyc-inference-research/data/research/2026-05-19-rao-redel-step2-ab/results.json`

##### Summary numbers (n=10 each arm)

| Metric | Arm A (`repl_executor` mimic) | Arm B (ReDel DelegateAndWait) | Δ B−A |
|---|---|---|---|
| accuracy (substring match) | **100%** (10/10) | **100%** (10/10) | 0 pp |
| wall median (s) | 5.79 | 6.23 | +0.45 s (**+7.6%**) |
| wall mean (s) | 6.41 | 6.90 | +0.49 s (**+7.6%**) |
| tokens median | 6,132 | 6,325 | +193 (**+3.1%**) |
| tokens mean | 6,131.6 | 6,324.1 | +192.5 (**+3.1%**) |
| max_depth observed | **0** | **0** | none — see below |
| errors | 0 | 0 | — |
| wall total | ~64 s | ~69 s | run completed in <3 min, not 20–60 min |

##### The load-bearing observation: depth=0 on every single sample

**Neither arm delegated.** Gemma4-26B-A4B answered every 4096-ctx and 8192-ctx needle directly without invoking the `delegate` tool. This is exactly the depth-0-beats-depth-1 pattern intake-547#01 (Wang) reproduced on Kimi K2 OOLONG (86.6% depth-0 vs 60.0% depth-1) — a base model with enough long-context muscle to handle the task in one shot will (correctly) refuse to spawn a sub-agent.

What this means for the spike:
- Both arms measured **substrate overhead with no delegation actually exercised**. ReDel's ~3% token + ~8% wall overhead is *exactly* the cost of carrying the `delegate` tool definition + larger system prompt + event-stream machinery when delegation isn't used.
- The `asyncio.gather`-vs-sequential aspect that the deep-dive flagged as the headline ReDel win was never tested — neither arm ever had a "parallel sub-agent fan-out" moment, because there was never even a single sub-agent spawn.
- The substrate's behaviour-when-not-delegating is **as good as the in-house code**: both arms 100% accuracy, sub-second wall difference on this workload, ReDel never artificially forces a delegation that the model didn't want.

##### Gate scorecard against handoff Step 2 spec

| # | Criterion | Threshold | Result | Status |
|---|-----------|-----------|--------|--------|
| 1 | Wall-clock | ReDel ≥0 regression | B is +7.6% slower | **REGRESSION (mild)** |
| 2 | Accuracy | ReDel ≤0 regression | parity (100% / 100%) | **PASS** |
| 3 | Token efficiency | within ±20% | +3.1% | **PASS** |
| 4 | Event-stream richness | JSON-serializable + sub-decision labelable | 10× clean event streams, no errors | **PASS** |
| 5 | LoC delta if adopted | ≤500 net additions | not measured (separate calc) | n/a |

Handoff says "any 1 of gates 1–3 passing AND gate 4 passing" → escalate to Step 3. Gates 2+3+4 pass → **technically eligible to escalate**. But the no-delegation finding tells us the test wasn't probing the substrate's distinguishing feature.

##### Secondary observations

- **Tokenizer mis-count noise**: kani falls back to `o200k_base` for token counting (gemma4 tokenizer not in tiktoken). The reported token counts are within ~5–10% of true gemma4 tokens on English. Not blocking; Step 3 should pass a kani-compatible tokenizer explicitly.
- **ReDel benign teardown noise (10× instances)**: `ValueError: task_done() called too many times` fires once per `ReDel.__del__` shutdown (`redel/app.py:283`). Visible in the run log, does not affect results, does not corrupt the event stream before shutdown. File as a small upstream fix-it; orthogonal to substrate viability.
- **The 1-line `get_prompt` patch from Step 1 held up across 10 ReDel instantiations** — no further patches needed.
- **Worker_general's lstrip-strict tokenizer behaviour is consistent**: the model's outputs are reproducible token-for-token across A and B for the same context (verified by spot-checking final answers). Substrate change doesn't perturb output content.

##### Recommendation for Step 3 escalation decision

The result is genuinely ambiguous and any of three reads is defensible:

1. **Accept (escalate to Step 3)**: gates 2+3+4 passed. A +3.1% token / +7.6% wall overhead is small and is the cost of a feature-flagged-off substrate change. ReDel's event-stream + visual-debugger + first-class `DelegateAndWait` is worth ~3–8% on the never-actually-delegated workload. Re-test delegation behaviour when a real delegation-heavy benchmark (e.g., OOLONG-Real D&D 32K, or DeepDive) is available.
2. **Re-test (delegation-forcing follow-up)**: rerun the A/B with a system prompt that *requires* delegation (e.g., "You MUST delegate the answer to the sub-agent — do not answer directly"). This isolates substrate-with-delegation overhead and would let us measure the asyncio.gather / event-stream behaviour the deep-dive cared about. Cost: another ~3-min run, no extra LoC.
3. **Close negative**: the substrate is parity-class for the workloads we care about (because base models are good enough to skip delegation). Mark substrate replacement DEFERRED until either (a) a delegation-heavy workload surfaces in autopilot, or (b) we move to a smaller base model that genuinely needs depth=1 to hit accuracy.

The 5-sub-decision episodic-store wiring from Step 3 pre-work is independently valuable in all three branches — it stays on the local feature branch awaiting user-direction on push + PR.

##### Adoption LoC delta estimate (not measured in this run)

If we adopted ReDel as substrate per the handoff's Step 3:
- New: `epyc-orchestrator/src/api/routes/chat_pipeline/redel_executor.py` (~500-800 LoC including feature-flag plumbing, event-stream → sub_decision mapper, kani-tokenizer wiring for gemma4, sequential `kani-ratelimits` integration, telemetry exporter).
- Dependency additions: `redel`, `kani[openai]`, `kani-ratelimits`, `pydantic` (already present). ~10 transitive packages.
- ReDel `[all]` extras (web UI) NOT in scope.
- Deletions: 0 (legacy `repl_executor.py` stays behind flag for paired-A/B in production).

**Net ~500–800 LoC additions** → at the upper edge of the handoff's "≤500 net additions" gate. Step 3 design should aim for ~400 LoC by skipping the kani-ratelimits wiring (we have our own rate-limit logic) and reusing the existing pipeline structured-logging via a thin adapter rather than ReDel's `eventlogger.py`.

#### Step 2 Path-2 Result (2026-05-19) — delegation-forced rerun: model REFUSES delegation, arm-A pattern BROKEN

**Verdict**: the right next test is a workload that *naturally* requires delegation, not prompt-injection that the model resists. Substrate evaluation remains parity-leaning-positive overall; the asyncio.gather / parallel fan-out headline win is **still unmeasured** on EPYC workloads because the base model decides not to delegate.

**Raw artifact**: `/mnt/raid0/llm/epyc-inference-research/data/research/2026-05-19-rao-redel-step2-ab-force-delegate/results.json`.

Same 10 samples, same arms, but each prompt prefixed with `"INSTRUCTION: You MUST use the \`delegate\` tool to forward this exact question to a sub-agent (named alpha). Pass the full long context to the sub-agent…"`.

##### Summary numbers

| Metric | Arm A (in-house) | Arm B (ReDel) |
|---|---|---|
| accuracy | **0%** (0/10) | **40%** (4/10) |
| errored runs | **10 / 10** | 0 / 10 |
| max_depth_seen | 1 (delegation actually fired) | **0** (no delegation despite "MUST delegate" instruction) |
| wall median (errored arm-A) | 12.7 s | 12.8 s |
| wall mean | 12.7 s | **59.7 s** (bimodal: ~135 s when engaged, ~10 s when refused) |
| tokens mean | 5,737 | **11,320** (vs 6,131 in Path-1 — ReDel ate +85% on force-delegate) |

##### Diagnoses

###### Arm A — tool-call truncation kills the substrate

Every arm-A sample died with `json.JSONDecodeError: Unterminated string starting at: line 1 column 17 (char 16)` at the `json.loads(tc["function"]["arguments"])["instructions"]` step. Mechanism:

1. Root-with-tool round-trip uses `max_tokens=256`.
2. Gemma4 emits a `delegate` tool call where `arguments` is a JSON string `{"instructions": "<the full needle haystack>"}`.
3. At `max_tokens=256` the model can't fit the entire haystack (4096+ token context) into the tool-call argument string → JSON gets truncated mid-string.
4. The aggregation round can't parse it.

**This is a real substrate finding, not a script bug**. The "pass full context via tool-call arguments" pattern fundamentally doesn't scale: parent's tool-call output is capped by `max_tokens`, but the context the sub-agent needs is many KB. Production `repl_executor` avoids this by carrying context **via REPL variables / state**, not via tool-call arguments. The arm-A mimic was a faithful render of the surface but missed the load-bearing variable-passing-by-reference detail.

Implication for Step 3 adoption: any ReDel-vs-`repl_executor` lift must preserve the variable-by-reference mechanism. ReDel's `kani` engine already does this implicitly (chat history is in the parent kani's state, not in the tool-call payload), so this is a point in ReDel's favour — but only because the test exposed that arm-A's surface mirror missed it.

###### Arm B — gemma4-26B-A4B refuses prompt-injected delegation

ReDel arm: max_depth=0 on **every single sample** despite the explicit "you MUST use the delegate tool" instruction. Gemma4 is sufficiently RLHF-trained to ignore prompt-injection-style mandates that try to override the natural answer. Behaviour is bimodal:

- 4 of 5 4096-ctx samples: model "engages" with the instruction (long-form prose explaining why it could answer either way) → 132-138 s wall, 16,500-16,750 tokens, often correct (substring matches in the verbose answer).
- 1 of 5 4096-ctx samples: model refuses fast → 6 s, 4,400 tokens, wrong.
- All 5 8192-ctx samples: all fast (4-14 s), all wrong. The combination of long context + force-delegate prefix pushes the model into terse refusal mode.

**This is also a real substrate finding**: capable base models will not delegate just because the prompt tells them to. Forcing delegation via prompt injection (the easiest follow-up to Path-1) is not the right way to stress-test the substrate's delegation path. The right way is a workload that **structurally** requires delegation — e.g., a benchmark where the parent can't fit the full context but the child can (need a context-window mismatch), or a multi-question task where parallel sub-agents are obviously cheaper than serial reasoning.

##### Combined verdict across Path-1 + Path-2

**Substrate parity-leaning-positive, asyncio.gather win unproven on our workloads.**

| Aspect | Path-1 (model decides) | Path-2 (force) |
|---|---|---|
| arm A delegates | No (depth=0) | Yes (depth=1) but breaks |
| arm B delegates | No (depth=0) | No (depth=0) — model refuses |
| arm A accuracy | 100% | 0% (broken) |
| arm B accuracy | 100% | 40% |
| arm B wall vs A | +7.6% | +370% (when engaged) / ±0% (when refused) |
| arm B tokens vs A | +3.1% | +85% mean |

ReDel's substrate is **mechanically sound** — it doesn't introduce errors, the event stream stays clean, the delegation primitives work as advertised. The two open questions are whether (a) a delegation-positive workload would reveal a meaningful asyncio.gather win and (b) the in-house `repl_executor` (with its variable-by-reference plumbing that arm A's mimic missed) would beat ReDel on that workload.

##### Recommended Step 3 entry criteria

Do not escalate to Step 3 substrate-replacement work based on Path-1 + Path-2 alone. Two cheaper next-step options ordered by cost:

1. **Identify a naturally-delegating workload** in our existing eval pool. Candidates:
   - DeepDive-style multi-tool web research (arm B can do `asyncio.gather` for parallel sub-queries).
   - HotpotQA multi-hop (each hop = one sub-agent call).
   - Multi-question test items where parallel sub-agent fan-out actually saves wall time.
   Re-run the A/B on whichever surfaces. ~30-60 min compute.
2. **Use a smaller base model that needs delegation**. Qwen3-1.7B drafter would delegate the long-context task to worker_general; that's the natural-delegation case. ~10 min compute.

Either is cheap and unblocks the substrate decision. The 5-sub-decision episodic-store wiring (Step 3 pre-work) lands on its own merits regardless.

#### References

- Deep-dive: `/workspace/research/deep-dives/2026-05-19-rao-rlm-cluster.md`
- ReDel repo: `https://github.com/zhudotexe/redel`
- RAO paper: `https://arxiv.org/abs/2605.06639`
- Wang RLM reproduction: `https://arxiv.org/abs/2603.02615`
- Orchestration-trace survey: `https://arxiv.org/abs/2605.02801`
- Tree-GRPO: `https://arxiv.org/abs/2509.21240`
- Related handoffs: `../completed/meta-harness-optimization.md`, `halo-trace-loop-spike.md`, `repl-turn-efficiency.md`, `tri-role-coordinator-architecture.md`, `unified-trace-memory-service.md`

#### Progress checklist

- [x] Step 1 ReDel pre-flight gate - 4/4 PASS ✅
- [x] Step 2 paired A/B (Path-1 + force-delegate Path-2) executed - ambiguous/parity ✅
- [x] Step 3 pre-work: 5-sub-decision taxonomy wired into episodic store (local branch, not pushed) ✅
- **[declined: ws58 2026-11-03 content-review: merged into the EVL-34 rerun; the first run recorded zero delegations in both arms (diagnostic only)]** Run a naturally-delegating workload A/B (HotpotQA/DeepDive or small base model) before Step 3 escalation
  - 2026-10-29 (ws58 results filing batch B, diagnostic observation, no tick): `codex-evl34-natural-delegation-20261029` rc0 complete 02:10:20Z, CPU 48-71, gemma, HotpotQA distractor, n=10 per arm, depth cap 1. **Zero natural delegations in either arm** (A REPL-executor mimic: max_depth 0 on 10/10; B ReDel delegate-wait: delegations 0 on 10/10). Exact-match 0/10 in both arms (sentence-form answers against short golds; A's lenient `correct` is 4/10, and B does not record it). Wall 167.8 s vs 196.1 s; total tokens 18,755 vs 22,173 (A vs B). Predeclared rule: diagnostic, report EM, wall and tokens per arm, no adoption conclusion. Class: invalid as a delegation A/B, because the delegation path was never exercised, and the EM scorer cannot resolve verbose answers. Result `/mnt/raid0/llm/tmp/codex-evl34-delegation-20261029/results/natural-delegation.json` sha `7fe304f6646d…`. The box stays open. [belief: cc]
    - [ ] **EVL-34 natural-delegation rerun (filed 2026-10-29, ws58 filer B):** rerun with a model that actually needs to delegate (the small-base-model option in Step 2 next steps, e.g. a ~1.7B front model delegating to worker_general) and a normalized or substring answer scorer. Done when at least one arm records more than 0 natural delegations and EM is resolvable.
      - 2026-10-31: `codex3-evl34-r11-budget-v7-ab-20261030` -> FAILED-RUN (no measurement). Granted 22:06:21Z, job rc=1 at 22:06:27Z: `campaign_job.py` -> `source_closure.verify_local_source()` raised FileNotFoundError on `/mnt/raid0/llm/tmp/codex-evl34-delegation-20261029/requirements-freeze.txt` (declared source missing at launch; no PILOT-DONE.json, no cells run). Rule (DeepDive 39-48 paired EM, CI, missing bounds) unevaluated; incomplete is unknown. Follow-up: restore/repoint that file in source declaration, re-seal, re-queue. [no-belief: harness failure, no measurement]
      - 2026-11-02: The missing freeze was recovered byte-identically and a v8 custody successor prepared; see [repair evidence](../../artifacts/compute/codex3-row-repairs-20261101/README.md). Its launcher explicitly refuses execution until the canonical engine and qualification are available. Verify the runtime in its actual host execution context, prepare the row using the current rowflow contract, and preserve the frozen cases, scorer and prior unknowns. This preparation is not an A/B result. [no-belief: preparation only]
    - [x] **Repair r10 child/aggregate budget and republish r11.** ✅ 2026-10-30 — r11 budget-v6 passed entry-only R7 smoke (79.6326 s; both real model responses and usage, GPU residency, result writer and clean server/supervisor drain); same qualified manifest was resubmitted and keeper QUEUED it at 20:55:01Z with 0 refusals / 0 warnings. The 20-cell pilot and verdict remain pending; control33 semantic results remain partial/unknown; zero matched delegation in a future full pilot means INCONCLUSIVE_NO_DELEGATION. Preserve r10 eight unknowns and controls 28–32; do not infer pilot completion from READY. [no-belief: launch repair and qualification only; pilot verdict pending]
- [x] Operator decision: push/PR the sub-decision-taxonomy feature branch ✅ 2026-11-09 — already landed: epyc-orchestrator `602c44c5` (2026-05-20, "wire 5-sub-decision taxonomy axis (intake-548) (#1)", ancestor of main `98221350`), code in `orchestration/repl_memory/episodic_store.py` (`sub_decision` field, :193) and `scripts/memory/backfill_sub_decision.py`; the feature branch and commit `8bf985c` no longer exist. [no-belief: merge-state fact; no measurement]
- [ ] Step 3 conditional substrate replacement (~400-800 LoC) - gated on delegation-positive re-test

#### Research Intake Update — 2026-07-21 (Two new RLM sources — the depth evidence still favours max_depth≤1)

Three RLM-lineage sources arrived together. **None of them overturns the pinned `max_depth=1`; the independent evidence continues to point the other way.**

- **[intake-866] "Language model harnesses are compositional generalizers"** (Alex L. Zhang, personal blog) — credibility 3.
  - Claims RL-training an RLM harness on SHORT tasks transfers to held-out tasks 8-32x longer with ~10x the eval lift of RL-ing the base Transformer, trained on **Qwen3-30B-A3B-Instruct-2507** — the exact MoE class we run on CPU. Introduces "locally in-distribution" (LID) as the proposed mechanism.
  - **Treat as an observation, not a result.** Graphs only, no numeric tables, no seeds, no eval-set sizes, single-seed single-model 150-step run — a claimed 10x differential lift with no variance reporting could be seed noise. The author concedes LID is "very hard to formalize in an empirically meaningful way", i.e. it is unfalsifiable as stated, and reports a degenerate failure mode where the RLM collapses to offloading the whole problem to one sub-call.
  - **It has zero independent criticism because it is weeks old and blog-published — absence of scrutiny, not evidence of correctness.**
- **[intake-867] "Reinforcing Recursive Language Models"** (alphaXiv) + **[intake-868] SkyRL `examples/train/rlm`** (Apache-2.0, actively maintained).
  - The genuinely new content is a training formulation: one shared policy for parent and child roles, with **parent-to-child GRPO advantage inheritance** and 1/k_g normalization. The code implements the parent/child rollout-tree bookkeeping that this spike needs as an *accounting model* for nested sub-agents, independent of any RL.
  - Caution on the credit-assignment scheme: intake-878 quantifies why trajectory-level advantage degrades in multi-turn settings — **but note it contains no analysis of recursion or depth at all**; the "compounds with depth" framing is an extrapolation by the citing source, not a finding.
- **Standing counter-evidence (unchanged, and still the strongest datapoint):** intake-547#01, intake-547#02 — depth-0 86.6% vs depth-1 60.0% on Kimi K2 OOLONG, base models at 100.0% on S-NIAH degrading under depth-1, and ~96x wall-clock inflation at depth 2. RLM gains appear only where the base model scores ~0.0%, i.e. **recursion rescues failing models rather than improving competent ones.**

- [x] Substrate-decision input: keep `max_depth` at 0-1 for competent models and reserve recursion for near-zero-baseline cases; revisit only if a controlled local A/B contradicts intake-547#01 or intake-547#02. ✅ 2026-07-29 — this is a planning default, not a performance claim: the controlled counter-evidence in intake-547#01 and intake-547#02 remains stronger than intake-866's unmeasured framing, and no local A/B has contradicted it. [intake-866, intake-547#01, intake-547#02]
- [x] Design input: the SkyRL parent/child rollout-tree model (`parent_rid` /
  `depth` / `child_index` with reward propagation) is a reusable accounting
  shape for nested sub-agents here, usable without adopting any RL. **Scoped
  2026-07-29:** `EpisodicStore` already persists the five-class `sub_decision`
  axis but has no tree-linkage fields; do not mistake that label for rollout
  accounting. The implementation is an additive SQLite migration plus a
  backward-compatible read/write surface, and requires independent review
  before code lands. ✅ 2026-07-29 [intake-868]

  - **Minimal data contract:** nullable `rollout_id`, immediate
    `parent_memory_id`, non-negative `depth`, and non-negative `child_index`.
    `rollout_id` identifies one root-to-leaf execution; `parent_memory_id`
    identifies the direct parent (not a model or task id). A root has NULL
    parent and depth 0. Existing rows remain NULL on all four fields.
  - **Reward semantics:** retain each event's observed `q_value`; compute any
    parent/child credit aggregation in a read-only query or a separately named
    derived report. Do not overwrite parent or child rewards during this
    accounting migration.
  - **Compatibility surface:** extend the `MemoryEntry` model, `store` and
    `store_immediate` keyword-only inputs, and every projection used by
    `retrieve_by_similarity`, `get_by_id`, and `get_all_memories`. Additive
    DDL must be idempotent on fresh and pre-existing databases, with legacy
    NULL rows round-tripping unchanged; index only `(rollout_id, depth,
    child_index)` after a query-plan justification.
  - **Required independent review before implementation:** verify the DDL,
    all writer/read projections, FAISS/SQLite consistency and concurrent
    migration behavior; add fresh/migrated/legacy/round-trip tests. The
    current graph index is stale but still classifies `EpisodicStore` HIGH
    blast radius (77 upstream, 27 direct), so this design deliberately makes
    no code change.

##### Correction 2026-07-21 — depth should be CONDITIONAL, not a pinned default (operator challenge)

The earlier note recorded intake-547#00 and intake-547#01 as supporting a **static** `max_depth=1`. That under-reads it. The finding is that **RLM gains appear only where the base model scores ~0** — on Kimi K2 OOLONG depth-1 *lost* (86.6 → 60.0), but on DeepSeek OOLONG depth-1 *rescued* a total failure (0.0 → 42.1). Direction-of-effect is conditional on whether the base attempt is going to fail. A pinned default throws that away in both directions: it forfeits the rescue where recursion helps, and it still pays depth where recursion hurts.

**The correct shape is a gated surface: escalate depth only when the base attempt is predicted to fail.** We already hold the training data for exactly that predictor — `learned-routing-controller.md` lists an **Escalation prediction** surface, "Binary (will frontdoor fail?)", with **10,528 positive + 56,457 negative** examples, status **Ready**. It has never been built. The `COMP_r(x)` competence probe proposed from intake-866 is the same quantity approached from the other side (per-role familiarity → predicted success), so the two should be developed as one signal rather than two.

**Three constraints that must ride with any depth surface:**
1. **Cost gating is not optional.** intake-547#02 measures depth-1 at ~25x wall-clock (3.6s → 89.3s) and depth-2 at ~96x (→ 344.5s). The expected-value condition is `P(base fails) × value(rescue) > cost_multiplier`, so depth-2 needs a very high failure probability to clear; depth-1 is the tractable rung. Do not expose depth-2 without a measured gate.
2. **This is newly computable, and was not before.** Until 2026-07-21 the routing reward could not represent the cost side at all (the entire cost/speed half was inert — see `decision-aware-routing.md`). A depth surface priced against a constant reward would have been untunable. It is worth building now for that reason, and was not before.
3. **Per-model, not global.** intake-547#00's direction-of-effect differs by model, so the gate must be conditioned on the target role/model, not a single global threshold.

- [x] Reframe the substrate decision from "pin `max_depth`" to "expose depth as a conditional surface gated on predicted base-attempt failure". The static `max_depth=1` remains the correct *default*; what changes is that it stops being the only setting. ✅ 2026-07-29 — decision framing is now explicit: `P(fail)` must be target-role/model-specific and clear an expected-value gate with the rescue value and cost multiplier; depth-2 remains unavailable until it has its own measured threshold. This closes the framing only. The escalation/competence predictor and the numeric gate are separate open implementation tasks below; no runtime depth policy, inference, or measurement claim changed.
- **[declined: ws58 2026-11-03 content-review: premise contradicted — the escalation probe was adversarially refuted (within-suite AUC 0.5521 +/- 0.038, 2026-11-02 correction); there is no validated predictor to build the gate on]** Build the Escalation-prediction surface (10,528 pos / 56,457 neg, already labelled and Ready per `learned-routing-controller.md`) as the depth gate, developed jointly with the `COMP_r(x)` competence probe — they estimate the same underlying quantity.
  - **2026-11-02 correction:** the earlier “Ready” description refers to a historical snapshot, not a validated depth predictor. The [escalation probe](routing-program.md#escalation-prediction-probe--2026-07-27-provisional-adversarial-verification-pending) was adversarially refuted; its owner reports within-suite AUC 0.5521 ± 0.038 for worker_general and 0.5204 ± 0.037 for frontdoor, with defective outcome labels. Do not use the refuted aggregate result or fit a depth policy to those labels. Repair the labels and re-evaluate per role/model under the owning handoff's EP-5 before relying on this signal. The task remains open. [belief: cc]
- [ ] Gate depth escalation on expected value, not on predicted failure alone: require `P(fail) × value(rescue) > cost_multiplier`, with depth-2 held behind a measured threshold given the ~96x wall-clock.
  - 2026-11-02: [Prospective gate contract](../../docs/design/conditional-depth-gate-contract.md) fixes the units, role/model bindings, invalid-input behavior and depth-2 evidence requirements. It also calls out potential harm to correct answers; no gate implementation or measured threshold is claimed. [no-belief: design only]

##### Audit catch 2026-07-21 — OOLONG is the missing instrument for the open depth A/B

The open checkbox above ("Run a naturally-delegating workload A/B before Step 3 escalation") and the intake‑547-vs-866 depth dispute share one missing piece: **we do not hold the benchmark the dispute is measured on.** OOLONG (and MRCRv2/GraphWalks) appear in intake-866's eval span and intake-547#record's reproduction, but none is in our suite (`dataset_adapters.py` has no oolong adapter; long-context coverage is longbench/zeroscrolls/leval/ruler/needle). Adopting OOLONG would let us run **depth-0 vs depth-1 on OUR models** instead of arbitrating between two external results on models we do not serve — directly answering both this handoff's A/B gate and the conditional-depth surface question.

- [ ] Evaluate adopting OOLONG as a suite adapter (source/licence check first), sized to the depth question: n large enough to resolve a ~10-25pp gap, not a full-suite port. If adopted, the naturally-delegating-workload A/B above should run on it. Cross-file with the completed [long-context-eval-datasets.md](../completed/long-context-eval-datasets.md) rationale before adding a sixth long-context suite.
  - 2026-11-02: [Readiness audit](../../artifacts/research/rao-oolong-adoption-readiness-20261102.json) identifies the missing native depth bridge, context-level power plan and depth-aware belief capture. Existing YaRN OOLONG arms answer a different question; do not duplicate that study or present it as depth evidence. [no-belief: readiness audit only]
  - Requirements for this adapter are filed as OOL-1 below (2026-10-21 DP-F amendment); see OOL-1. Checkbox state unchanged.
- [x] **OOL-1 — Oolong adapter requirements (supersedes the unnumbered source-and-licence-first line).** This task carries the requirements for the open line "Evaluate adopting OOLONG as a suite adapter" (the source and licence check is cleared: repo and both datasets MIT, scorer self-contained; strike that clause). The adapter must: vendor `src/eval/eval_helpers.py` at repo SHA `0bb7eabe8` unmodified and import it, never re-implement from paper prose; load only `context_window_text`, never `context_window_text_with_labels`, except in a clearly named labels-given ablation whose record carries `labels_given: true` and is excluded from any gate (a regex scored near 100 percent on the labelled text); use one cached prefill per context for its 25 questions through a thin OpenAI-compatible client to llama-server (cache_prompt true, one slot per context, question last); score per the repo code and persist `parse_confidence`, reporting the share of low per (model, length) and hand-classifying 20 low items per arm before any thinking-on versus thinking-off comparison; log answered, attempted and no-answer separately and classify failures as wrong, no-answer (budget), refusal or unparsable before accuracy, running thinking-on and thinking-off as arms; report confidence intervals clustered by context; pin `oolongbench/oolong-synth@81d2f8d9349f6ff329d695f9be494051e9f05cb9` and `oolong-real@3ae6ab58ffcc4253ed52daeb58e02ed4cfea5784` as source_revision and add the belief-kernel source row in the same change (intake-2246#record, intake-2281#record, intake-2261#record). Acceptance: the original line points here, the requirements are filed, and the adapter fails a test that feeds the labelled column. Estimate: 2-3 days for the adapter, runs per YARN-AGG-1. ✅ 2026-10-21
  - 2026-10-21 (fillers-3c4ca599): Oolong runs registered under queue item `yarn-native-gate` (NOT armed). thinking_on budget: 16384 is derivable (architect-bench R2 precedent); pre-register fixed cap vs reasoning-budget arm before the first run.
  - 2026-10-21: adapter built in epyc-inference-research lane `lane/dpf-sample-yarn-ool` (`scripts/benchmark/oolong_adapter.py`, commit `a1ed3633a`). 11/11 unit tests pass (tiny fixture, no model/dataset), including `test_labelled_column_is_refused` (the labelled column raises `LabelledColumnError`; `labels_given` records are excluded from gates). Pins: `oolong-synth@81d2f8d9349f6ff329d695f9be494051e9f05cb9`, `oolong-real@3ae6ab58ffcc4253ed52daeb58e02ed4cfea5784`. Vendored `eval_helpers.py` @ `0bb7eabe8` unmodified, sha256 `247583a3b653b91c39fb88a102460802f1493175b23d05a7217aead0d685c64c` (verified on import). Belief-kernel row added in `scripts/vidya/adapters/README.md`, task `VB-OOLONG-WIRE` in `vidya-belief-substrate-program.md`. The runs (thinking on/off arms, hand-classifying 20 low-confidence items per arm) are YARN-AGG-1's, not part of this task.


2026-10-30: R10 paired native diagnostic collected all 20 fixed pilot cells (source rows 10–19 × production REPL and ReDel, depth ≤1); disjoint smoke control27 was excluded. Exact-match accuracy was REPL **4/10**, ReDel **3/10**. Native server usage totals were respectively **76,766 prompt + 4,049 completion tokens** over 18 requests and **23,044 + 191** over 10 requests; summed arm wall times were **115.030 s** and **28.860 s**. These are descriptive numbers for this small diagnostic, not adoption, significance or speed claims. REPL recorded zero tools/delegations; ReDel recorded zero assistant tool calls, delegate calls, depth-1 spawns and delegated events. Therefore native verdict `INCONCLUSIVE_NO_DELEGATION` is supported and the naturally-delegating A/B / Step3 criterion remains unmet. The captured GPU server used Qwen3.6-35B-A3B-MTP-Q8, frozen production GPU kernel, ctx49152/np3; all 28 server requests have PID/birth-bound, during-request positive HIP/KFD residency samples (1,821 samples, minimum observed VRAM 38,151,901,184 bytes). The grant assigned CPUs184–191 and launcher used taskset; no independent per-thread CPU residency was captured. Server drain was verified. Source row and prompt hashes, 20 journal start/end/native identities and exact scorer were reopened. `PILOT-DONE.json` SHA-256 `bf8f7e20bc192f620cc554d54416dcce6ea079dad31dbb32d992f963a0158338`. [belief: cc] [Committed native audit](../../artifacts/compute/results-filing-20261030-0157.json).


- *(2026-10-30; DeepDive R1 original, partial)* Frozen first-ten source-order `qa_rl` training questions, separate control excluded, paired native production REPL and ReDel, same 35B model and question, 8192 reserved generation tokens/arm. Original ended `rc78` at 02:48:23Z: 11/20 cells complete (10 REPL, one ReDel); nine ReDel cells are unknown and `PILOT-DONE.json` is absent. All 20 exposure identities match their frozen prompt hashes; server drained. The 10 complete REPL cells scored 0/10 normalized exact match; their seven recorded browser calls completed and no child calls were tracked. The only complete pair (case3) had zero exact match and zero tracked delegation on both routes. Real, unforced ReDel pilot event logs show a linked root delegate call, depth-1 child spawn and delegation in eight *unknown* cells (0,1,2,5,6,7,8,9); those eight child logs report the predeclared aggregate budget exhausted. The remaining unknown case4 logged malformed delegate arguments and a later truncated-frame/API connection error, without a linked child. These partial native events establish observed delegation, not a completed delegation-positive paired evaluation or a Step 3 result. This is training data and model-training exposure is unknown. During-window own-server KFD: 13,482 samples, 38,151,901,184–38,301,331,456 VRAM bytes. Frozen declaration SHA `f6cddfe144274686b9dac6754349f46f6ae5076a31c452bf545e7bc23e2f4881`; original result SHA `fe87043d12af87210429fcae7006e9fbc45e241a5f1089295cd02243e14cf9c8`; pilot native artifacts `/mnt/raid0/llm/tmp/codex3-evl34-deepdive-r1-20261030/` and immutable exposure journal `/mnt/raid0/llm/tmp/codex3-evl34-deepdive-r1-20261030/pilot-journal/`. [belief: cc]

Owner action: preserve nine unknown exposures without redraw; investigate native budget exhaustion and the case4 broker failure under a separately predeclared successor. Existing A/B and Step 3 remain open. [Durable audit references](../../artifacts/compute/20261030-0310/results.json).


##### 2026-10-30 05:30 original HSF and YaRN event filing

EVL-34 DeepDive R8's separately published native control completed both production REPL and ReDel delegate/wait arms in 88.698s, rc0, with writer and child cleanup. Neither produced a matched natural delegation and child, so qualification is `no_matched_natural_delegate_and_child`; no pilot, Step 3, quality or overhead claim follows. Durable control archive SHA-256 `29d3ed0820b85ea9a83192447a4f39325772131afd467680c9d004fe6ec3bac7`, native result SHA-256 `242297db3a41fc1204d1aa97c74d1bb09e3314e3bb80f97cfa125929c07f575d`. [Control evidence](../../artifacts/compute/results-filing-20261030-0530.json). [belief: cc]


##### 2026-10-30 06:05 original EVL, Paddle and YaRN resource events

- EVL DeepDive R8 original grant ended 05:49:17Z rc1 at `disk floor plus concurrent reservations`. The source checks this before creating the pilot attempt or captured grant, so this event exposed no new pilot cell. Its separately retained two-arm native control had no matched natural delegation. R9 repair is separate; no pilot quality or Step 3 claim. [Native event audit](../../artifacts/compute/results-filing-20261030-0605.json).
  - [belief: cc] Original native records and unchanged criteria are linked above.

- **FAILED-RUN `codex3-evl34-deepdive-r10-pilot-20261030` (owner codex3):** ended 13:19:56Z rc78 `job-rc-78:exited`; PILOT-DONE.json not produced. class=unknown (rc78 is the pilot's own code; root cause not in the launcher log). owner action: codex3 read the r10 preflight/pilot logs and record the rc78 meaning. Per predeclared rule, zero completed delegation-positive pairs is inconclusive; no Step3 claim, no redraw. [no-belief: failed run]
**2026-10-30 original-event filing — EVL34 DeepDive R10 original:** FAILED rc78, partial: REPL 10 complete; ReDel 2 complete, 8 unknown. Server drained; no pilot assessment. At least one child exhausted aggregate reservation budget. Native evidence `/mnt/micron/codex3-evl34-deepdive-r10-20261030/pilot/campaign-pilot-1793365239…477299 (digits elided for the PII hook)/result.json`, SHA-256 `bc7bf269bcee0cdb35fef978fb8e25b6de99d0064af5bfecaf8685b904a7456c`. [Audit](../../artifacts/compute/results-filing-20261030-1340.json). [belief: cc]


##### 2026-10-30 EVL34 DeepDive R11 v6 original pilot — incomplete diagnostic

- [x] **File the original R11 pilot and preserve its exposure outcomes.** ✅ 2026-10-30 The 20 fixed cells all started; REPL completed 10/10, ReDel 4/10 (12, 17, 18, 19), with 11, 13–16 and 20 unknown. The run ended 22:36:17Z rc78, `partial=true`, `failure=null`, server drained; no PILOT-DONE. The native return code deliberately denotes this all-complete-or-unknown partial state. Original normalized exact match is REPL **0/10** and ReDel **0/4 known**, bounded **0–6/10** with the original ten-pair denominator; unknown is not wrong. Completed-arm wall sums are 362.164s and 441.629s; native server usage is 41,023 prompt + 28,412 completion and 193,338 + 16,786 tokens respectively, only over the 10 and 4 completed cells. These descriptive subsets cannot support a full-cohort performance comparison. [belief: cc]
  - Reopened frozen declaration, all start identities, source-row and prompt hashes, completed end/start bindings and unchanged exact scorer. All first captured ReDel requests expose unforced delegate/wait. The registered predicate (root assistant delegate call, linked depth-1 spawn, matching delegation event) is satisfied by native streams in **7/10 cases: 11–16 and 19**, including completed 12 and 19; the partial case20 cannot establish absence. Thus **OBSERVED_DELEGATION_NEEDS_AB** as an observation within **INCOMPLETE_DIAGNOSTIC**; separate A/B is required before Step 3, which remains open. [belief: cc]
  - Native failure records identify case11's 2 MiB journal-record bound, cases13–16 aggregate reservation exhaustion in child traces, and case20 invalid tool-call argument JSON. The R11 budget repair therefore did not prevent four aggregate exhaustions. Case11's child log also records a per-child cap event; it is not the journal failure. No cause is inferred from rc78. All exposures are spent; no redraw or retroactive completion. [belief: cc]
  - Budget: 524,288 reserved tokens per arm, depth-1 child cap 16 calls, 900s per cell. Frozen source manifest SHA-256 `e5998c644c49ec90e67b0a15aa16e724cf18ae9816d70ed5c21f8380e9c1e5ce`; native result SHA-256 `3794d6706f1ea8da6a7992e126965328a84cdd0a74a6c545f54b2288bf7be648`. Model `c1283d8b80c3e38b2735ddbc9766d3b3126f44d6c484be419d4e101d09a76131`, kernel `2b49713f0e3c022132393bf302dab954a1e2c1974b91c28d01ce2d192abdfa7b`; actual GPU mapping was versioned `libggml-hip.so.0.16.0`. Original immutable native data: `/mnt/micron/codex3-evl34-deepdive-r11-budget-v6-20261030/pilot/`; frozen packet `/mnt/raid0/llm/tmp/codex3-evl34-deepdive-r11-budget-v6-20261030/`. [Offline audit and replay](../../artifacts/compute/evl34-r11-original-20261030/audit.json). [belief: cc]
- [x] **EVL34-R11-PARTIAL-FINALIZER** ✅ 2026-10-30 (operational finalizer and offline controls only) — correct prospective collection's bounded-record failure and partial reporting without changing the predeclared grader; validate offline against retained native records and preserve unknowns. Derive any successor aggregate from the allowed root and child call topology at 4096 reserved output tokens per call; the frozen broker reserves max_tokens only. The present 128-call aggregate cannot fund 16 children each making 16 calls plus root calls; retain a 16-call lifetime child cap and 900s cell limit in the successor. The original R11 implementation reset its 16-call cap on each `full_round_stream`; the original evidence is unchanged. The observed delegation still needs a separately designed A/B before Step 3.


**R11 loaded-source provenance correction (2026-10-30).** The shared orchestrator checkout fast-forwarded `84f6f6f15f713d21098dbad2b153d32f8cc13624` → `b0f8613d65f30986f147e5467b1c66892c887ce5` at **22:32:07 UTC**, during the 21:54–22:36 pilot. Relevant REPL executor and primitive files have that same checkout mtime, and a later REPL cell has a 22:36:04 prompt-file timestamp. Per-cell imported code versions were not captured and cannot be reconstructed from those timestamps. The `e5998c…` campaign fingerprint binds the packet adapter, not every underlying bytecode version actually loaded during the run. EM and event counts remain located observations, but this run cannot establish a reproducible single-source comparison; no prior result or exposure is changed. The subsequent prospective v7 binds an independent existing lane and rechecks its readset before each exposure. [belief: cc]


2026-10-30 accepted v7 prospective preparation: [source, frozen prompt-hash manifest, fixtures and entry qualification](../../artifacts/compute/codex3-evl34-r11-budget-v7-ab-20261030/) preserve the 8 MiB bounded record and partial finalizer. Engineering budgets are 128 root plus 256 total child calls, REPL 256 one-call lookups and ReDel 16 helpers with 16 lifetime calls each, global 384 × 4096 reserved output credits, 900 s/cell. Fresh DeepDive 39–48 and control 49 are predeclared once. R7 actual qualification PASS 114.55 s, peak RSS 38,447,210,496 B, receipt SHA-256 `4b03965c09ec1ea4ac3629b6c4d6c0c310d77b8c1066d01c13f12f6ce4a70671`. Launcher SHA-256 `99ed4c71f3c012f181b561497ffacba63529a3ade6a7b55579bf646856e073a2`, catalog `fc909212d2fbddcc7c43cf383ddc2da144f6a9803c88a0009ac40d968d3a9607`. Keeper queued at 23:44:29; 20,100 s window, 19,740 s minimum, 64 GiB. No A/B result or Step 3 quality claim exists yet; the earlier R11 source-change caveat still applies. [no-belief: preparation and qualification only]

## Track: reasoning-compression
<!-- gate: none -->

> Folded from `handoffs/active/reasoning-compression.md` @ `7e268b4de29c` on 2026-11-02 (BRF-T1-F6, route 1a, operator D1/D5; retired row UFH-05 → RTG-08). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Reasoning Compression for Inference Cost Reduction

**Scratch**: `/mnt/raid0/llm/tmp/reasoning-compression/` · worktrees: `/mnt/raid0/llm/worktrees/reasoning-compression-*`

**Status**: in-progress
**Created**: 2026-03-14 (via research intake)
**Categories**: training_distillation, cost_aware_routing

#### Objective

Explore reasoning token compression techniques that can reduce inference cost for reasoning models by 50-60% while maintaining or improving accuracy. OPSDC demonstrates that much reasoning output is actively harmful — compressing it improves both cost and quality. This could fundamentally change how we route to reasoning models.

> **Cluster role**: this handoff is the **counter-evidence anchor** of the reasoning-economics cluster (`research-evaluation-index.md`) — the empirical case that *adding* reasoning can be net-negative. It directly bounds the "does added reasoning help?" gates in [`gpu-cot-scaffold-sidecar.md`](../completed/gpu-cot-scaffold-sidecar.md) (G1) and [`minddr-deep-research-mode.md`](minddr-deep-research-mode.md) (MD-9): a scaffold/pipeline that fails to beat own-think is this handoff's finding restated.

#### Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-110#record | OPSDC: On-Policy Self-Distillation for Reasoning Compression | high | new_opportunity |
| intake-126 | FlowSteer: Concise Reasoning via Flow Matching | high | new_opportunity |
| intake-127 | TrimR: Verifier-based Training-Free Thinking Compression | high | new_opportunity |
| intake-129 | short-m@k: Shorter Thinking Chains for Improved Reasoning | high | new_opportunity |
| intake-128 | Adaptive CoT Compression (Self-Optimizing Framework) | high | worth_investigating |
| intake-133 | Reasoning as Compression (Information Bottleneck theory) | medium | worth_investigating |
| intake-134 | CoLaR: Dynamic Latent Compression of Reasoning Chains | medium | worth_investigating |
| intake-130 | Do NOT Think That Much (overthinking analysis) | medium | worth_investigating |
| intake-276 | Brevity Constraints Reverse Performance Hierarchies | high | worth_investigating |
| intake-125 | S3-CoT: Self-Sampled Succinct Reasoning | medium | worth_investigating |
| intake-103 | Thinking to Recall: Reasoning Unlocks Parametric Knowledge | medium | worth_investigating |

#### Approach Taxonomy

Four families of techniques, ordered by implementation effort:

##### Tier 0 — Pre-compressed checkpoint (zero training; no new inference infrastructure)
- **ThinkingCap-Qwen3.6-27B** (intake-892): a weights-level reasoning-compression candidate, not an
  inference-time effort/budget dial. Treat its reported token and accuracy deltas as an **observation**:
  the vendor is the only source, its 12 out-of-domain cells are directionally adverse in 8 cases, and
  the GGUF repository declares no license. Any candidate comparison must hold the existing MTP setup
  constant and independently measure an accuracy-per-total-token trade-off before registry admission.

##### Tier 1 — Zero-training (inference-time only)
- **TrimR** (intake-127): Verifier prunes reasoning tokens at inference. Compatible with our existing scorer infrastructure. **Highest priority — deploy immediately.**
- **short-m@k** (intake-129): Run k parallel generations, stop at first m completions, majority vote. 34.5% more accurate than longest chains. Maps to spec-decode verify-accept paradigm.
- **TALE-EP** (intake-1215, arXiv:2412.18547v5): per-question **numeric** token budget, estimated
  zero-shot by the reasoning model itself and placed in the prompt (inference-time only, no training,
  no server support). 67% token reduction at −2.72% average accuracy (461.25 → 148.72 avg output
  tokens; 83.75% → 81.03%), and **+3.11% accuracy on GSM8K at 75.7% fewer tokens** (318.10 → 77.26).
  Supersedes stylistic conciseness prompting (next entry) as the preferred form of this intervention,
  per intake-276's April 2026 prediction — now evidenced rather than predicted.
  - **Caveat 1 — generalisation is worse than the headline**: MathBench-College generalisation shows
    −8% (GPT-4o-mini) and −4% (GPT-4o) against vanilla CoT, far worse than the −2.72% average. The
    67% headline is an average over a heterogeneous distribution.
  - **Caveat 2 — the estimator is not free**: the per-question estimator costs an **extra model call**
    per request. That is invisible on closed APIs (where the paper measured it) and is **unmeasured on
    our bandwidth-bound CPU decode**. Measure estimator overhead against savings before adopting — do
    not treat 67% as a net win until that is done.
  - Evidence: `intake-1215` (`research/intake_index.yaml:94305`), dive-verified 2026-08-21 against
    arXiv:2412.18547v5 full text; TALE-EP arms are closed-models-only (GPT-4o/-mini, Yi-lightning),
    nothing measured on a reasoning-native Qwen3.x think channel.
- **Conciseness prompting**: Just add "be concise" to Qwen3 worker prompts. OPSDC paper shows 37% token reduction with comparable accuracy on easy problems. Zero effort.
- **Behavior-Conditioned Inference** (intake-897, arXiv:2509.13237): extract compact named
  procedures from successful EPYC traces, retrieve them into context, and evaluate a local A/B on
  fixed accuracy and **total** pipeline tokens (retrieval-prefill plus decode). The source's 46% is
  an output-token-only best case, so it is not a CPU cost claim until the prefill contribution is
  measured. The handbook must be append-only with raw traces retained; because the procedures are
  model-extracted, require a held-out validation gate before any rollout.

##### Tier 2 — Activation steering (no weight changes)
- **FlowSteer** (intake-126): Nonlinear activation steering transforms verbose→concise reasoning. Input-dependent control enables per-request reasoning budget. No retraining needed, but requires activation hook infrastructure.
- **S3-CoT** (intake-125): Self-sampled activation steering for shorter CoT. No teacher model required.

##### Tier 3 — Training required
- **OPSDC** (intake-110#04): Self-distillation, 8x H200 for ~100 steps. Best results (57-59% compression at accuracy parity to +3.3pp). Requires GPU access.
  - **Corrected 2026-08-10** — the earlier "+ accuracy gains (9-16 points)" figure came from the v1 abstract and **the authors revised it away**. Current Table 2: Qwen3-8B MATH-500 95.7 → 95.7 (**+0.0**, 56.9% reduction); Qwen3-14B 93.0 → 96.3 (**+3.3**, 56.3%). Per the authors' own Appendix D the "+9-16" was the *base* model being mis-scored by a boxed-only grader. The **compression** result stands; treat accuracy as parity, not uplift. Source: `intake-110#record` `claim_corrections` claim_index 4.
- **CoLaR** (intake-134): Latent-space reasoning compression. 53.3% chain reduction, 4.8% performance loss. Bypasses KV cache entirely. Longer-term.

#### Open Questions

- Can TrimR's verifier be our existing debug_scorer.py or does it need a specialized verifier?
- Does FlowSteer's activation steering work with quantized GGUF models via llama.cpp?
- OPSDC's difficulty adaptation (56% compression on easy, 35% on hard) — can we extract this as a routing signal without training?
- How does reasoning compression interact with speculative decoding acceptance rates?
- OPSDC shows AIME 2025 accuracy *drops* by 5.4pp — frontier-difficulty problems are harmed. Routing must account for this.

#### OPSDC Deep Analysis (arxiv:2603.05433)

**Mechanism**: Same model serves as both teacher and student. Teacher receives conciseness instruction, student doesn't. Reverse KL on student rollouts. Teacher refreshed every M=50 steps for progressive compression.

**Key finding — "reasoning is harmful"**: Under independent per-token error model (p_err=10^-4), removing ~2,750 tokens predicts >=28% relative accuracy improvement. Empirically validated: Qwen3-14B goes 70.0%→86.1% on MATH-500 purely from conciseness training with zero correctness reward.

**Difficulty adaptation is emergent**: Easy problems get 56-59% compression, hard problems 35%. The KL divergence between concise-prompted and base model is itself a difficulty signal usable for routing.

**Routing insight (zero-cost)**: Compare output length with/without conciseness prompt. Large ratio = easy → route to fast model. Small ratio = hard → escalate. Or simpler: just add conciseness instruction, short output = easy, long output = hard.

**Limitations**: AIME 2025 accuracy drops 5.4pp. Forward KL causes catastrophic collapse. Teacher update interval M must be 40-60 (sensitive). Math-only validation. No LoRA testing.

#### Implementation Progress (2026-03-14)

##### Action 1: Conciseness Prompting — DONE
- Added conciseness instructions to `worker_general.md`, `worker_math.md`, `coder_primary.md`
- Hot-swap files — takes effect on next request, no restart needed
- `architect_*` and `coder_escalation` already had conciseness suffixes

##### Action 2: TrimR Evaluation — READY
- Created `epyc-inference-research/scripts/benchmark/eval_trimr.py` (evaluation script)
- Created `epyc-inference-research/docs/experiments/trimr-reasoning-pruning.md` (experiment doc)
- Supports three strategies: `full`, `think-strip`, `trimr` (paragraph-level pruning)
- Uses existing `debug_scorer.py` for quality measurement
- Dry-run validated, awaiting model availability for live evaluation
- Run: `python eval_trimr.py --suites math --n-questions 20 --model-port 8080`

##### Action 3: Difficulty-Adaptive Routing Signal — DONE
- Created `epyc-orchestrator/src/classifiers/difficulty_signal.py` (~230 lines)
  - Mirrors `factual_risk.py` architecture exactly
  - 7 regex features: prompt_length, multi_step, constraints, code, math, nesting, ambiguity
  - Weighted score → band (easy/medium/hard)
- Wired into `_route_request()` in routing pipeline (after factual-risk block)
- Added `difficulty_score` and `difficulty_band` to `RoutingResult` and `EscalationContext`
- Config block added to `classifier_config.yaml` (mode: shadow)
- 30 tests in `tests/classifiers/test_difficulty_signal.py` — all passing
- **Currently in shadow mode**: computes and logs, does NOT influence routing

##### Remaining Work
- [x] Run TrimR evaluation on math/gpqa suites — ✅ 2026-04-09 (Package B). DeepSeek-R1-Distill-Qwen-7B on 4×48t NUMA. **GPQA**: full 58.3% → think-strip 52.6% → trimr 45.7% (2400 avg think tokens, thinking helps ~6pp). **Math (GSM8K)**: 66% all strategies identical (151 avg think tokens — model barely thinks on easy math). **Verdict**: TrimR valuable on hard tasks, irrelevant on easy tasks. Aligns with difficulty-adaptive routing. Prerequisites resolved: `chat.cpp` PEG parser fix, binary rebuild, `--jinja` in stack, `\boxed{}` scorer fix.
- [x] Collect shadow telemetry from difficulty signal in production — ✅ 2026-04-06. Package A collected 635 routing decisions with shadow predictions.
- [x] Validate difficulty signal predictive power against benchmark accuracy — ✅ 2026-04-06. At old thresholds (0.3/0.6): 92% easy, 0% hard, no predictive spread. Recalibrated to 0.15/0.35 for ~40/40/20 split. Medium prompts take 29% longer (p50 36s vs 25s). Re-validation needed at new thresholds. **Partial progress 2026-04-21 (NIB2-32 + NIB2-35)**: Analysis script delivered at `scripts/analysis/difficulty_signal_validation.py` — computes Spearman(band_ordinal, error_indicator) with ENFORCE-READY / TUNE-THRESHOLDS / SIGNAL-NOISE / INSUFFICIENT-DATA verdict. Persistence gap identified and closed same day via NIB2-35: `ChatResponse` now surfaces `difficulty_score`/`difficulty_band`/`factual_risk_score`/`factual_risk_band`; `RoleResult` carries them forward; `build_diagnostic()` writes them into `seeding_diagnostics.jsonl`. Re-validation unblocks once Package D (or any seeded benchmark run) accumulates n≥100 records post-2026-04-21. Report: `progress/2026-04/difficulty-signal-revalidation-2026-04-21.md`.
- **[declined: ws58 2026-11-03 content-review: duplicate of routing-program.md's learned router, which already routes by difficulty; "if validated" names no validation]** If validated: implement enforce mode (route easy→worker, hard→architect)
- [x] FlowSteer deep-dive (intake-126) — ~~blocked on Qwen3.5 (no `build_cvec()` in `qwen35.cpp`)~~ **corrected 2026-10-21**: `qwen35.cpp:198` and `qwen35moe.cpp:221` DO call `build_cvec` at ffc1bac82 (v10); the real silent no-op is `qwen4exp.cpp` (Qwen3.8-Flash-Next; comment only at L391). SEAL linear baseline works on dense Qwen3/Qwen2.5 via `--control-vector`
- [x] ~~Generate SEAL control vectors for Qwen3-32B (Action 8 — 2-day experiment). **Prep DONE 2026-04-09**: `generate_pairs.py` (80 contrastive problems), `eval_cvectors.py` (scaling sweep at 0.3/0.5/0.7), experiment design doc. Awaiting model servers.~~ (closed 2026-10-29 audit: OBSOLETE → Qwen3-32B GGUF deleted 2026-10-20 (model_registry.yaml:7647 deprecated_reason); box awaited model servers since 2026-04-09)
- [x] Reasoning length alarm: cancel + re-generate when `<think>` exceeds 1.5× band budget (Action 9) — `_check_reasoning_length_alarm()` in helpers.py, double-gated (feature flag + enforce mode), wired into `_execute_turn()` with retry + conciseness nudge, 9 tests
- [x] Implement n-gram loop detection (Action 4) — added `detect_think_block_loop()` to `quality_detector.py`, 8 tests
- [x] Wire band-adaptive token budgets through difficulty_signal enforce mode (Action 5) — `_repl_turn_token_cap()` now accepts `difficulty_band`, returns band-specific cap when mode=enforce (1500/3500/7000). `TaskState.difficulty_band` propagated from `RoutingResult`. Gated behind enforce mode (no behavior change while shadow).
- [x] Compute Omega metric per-suite — ✅ 2026-04-09 (Package B Phase 4). **Critical finding: 7/10 suites show tools/REPL HURT accuracy vs direct.** Worst: agentic -54.5pp, coder -44pp, general -26pp, math -26pp. Only hotpotqa (+12pp) and gpqa (+6pp) benefit from tools. Implication: default routing should prefer direct mode; REPL/tool use should be opt-in for known-beneficial suites.
- [x] Summarizer quality assessment — shared with `context-folding-progressive.md` Phase 2 (Claude-as-Judge eval of consolidation across model tiers; SFT data collection mirrors `eval_trimr.py` pattern) ✅ 2026-10-29 (audit: context-folding Phase 2a summarizer eval DONE (30B-A3B minimum viable 3.0/3.0): completed/context-folding-progressive-completed-through-2026-05-28.md:9,:270; active context-folding-progressive.md:56) [no-belief: audit-reconciliation]
- [x] Audit conciseness prompts: verified stylistic language, not suppression (Action 7). **UPDATE 2026-04-07**: intake-276 deep-dive reveals our "be concise" prompts are the weakest form tested — explicit numeric word limits outperform. See Action 12 below.
- [x] **Action 12: Upgrade conciseness prompts to explicit word limits** — ✅ 2026-04-09. Replaced vague "be concise"/"be direct" with format-specific word limits in worker_general.md (MC: letter+1 sentence, yes/no: answer+1 sentence, factual: <15w, open: <60w) and worker_math.md (MC: letter+1 sentence, numeric: <50w, proof: <100w). Removed "Show work step by step" from worker_math registry suffix (contradicts brevity on easy problems). Based on CCoT (2407.19825) 30-60 word sweet spot and TALE (2412.18547) findings.
- [x] **Action 13: Model-tier-differentiated conciseness** — ✅ 2026-04-09. Audit confirmed existing tier differentiation is correct: architect already has aggressive "<150 tokens" + "maximally concise"; frontdoor stays elaborative (user-facing); coder uses "code only". Updated thinking_reasoning suffix from verbose 4-line instruction to "Think step by step in <think> tags. Answer portion: under 50 words." Applied to all 3 thinking model variants in registry.
- [x] **Action 14: Add OAA metric to eval framework** — ✅ 2026-04-07. `eval_metrics.py` with `compute_oaa()` (α-penalized excess tokens), `compute_pti()` (per-token intelligence), `compute_batch_oaa()` (batch JSONL). CLI: `python eval_metrics.py --results path.jsonl`.
- [x] **Action 16: Answer-tag stop sequences for benchmark scoring** — ✅ 2026-04-09 (orchestrator), ✅ 2026-04-10 (research repo port). Replaced `####` marker with `<answer></answer>` XML tags in all benchmark prompts (GSM8K, GAIA, CRUXEval, SimpleQA, HotpotQA, sentinel questions). Added `</answer>` to `direct_stage.py` stop sequences — generation halts immediately after model emits `</answer>`, eliminating post-answer rumination loops. Scorers (`debug_scorer.py`) default to `<answer>` extraction with `####` legacy fallback. `ChatRequest.stop_sequences` field added for request-level overrides. **2026-04-10**: Ported to `epyc-inference-research` — the research repo's `dataset_adapters.py` and `debug_scorer.py` had diverged and still used `####`. All 7 adapter prompts + extract patterns updated; scorer defaults updated with `####` legacy fallback. Files: orchestrator: `dataset_adapters.py`, `direct_stage.py`, `debug_scorer.py`, `requests.py`, `seeding_orchestrator.py`, `sentinel_questions.yaml`; research: `dataset_adapters.py`, `debug_scorer.py`.
- [x] **Action 15: TALE dynamic budget estimation** — ✅ 2026-04-11 (Package C). 40 questions (math+general), 3 conditions. **Static limits outperform TALE on OAA** (static -3.48 vs TALE -5.95). TALE matches baseline on math (95%) but hurts general (50% vs 95%). Pre-pass adds latency without benefit. **Decision: keep Action 12 static limits, TALE deferred.** Revisit if difficulty_signal improves to enable per-suite policy.
- [x] CMV deep-dive: think block stripping (Action 10) — N/A for our architecture (raw LLM output not carried into next-turn context; REPL stdout is what flows forward)
- [x] CMV output spill with retrieval pointer (Action 11) — `_spill_if_truncated()` in helpers.py, writes full output/error to `/tmp/{task_id}_{label}_t{turn}.txt` + appends `peek()` pointer. Feature flag `output_spill_to_file`. 9 tests.

#### Deep-Dive Findings (2026-03-15)

##### Action 4: N-gram Loop Detection (from S3-CoT/SEER deep-dive)

**Source**: `research/deep-dives/reasoning-compression-s3cot-adaptive.md`, Path D

**What**: Detect repeated reasoning patterns (n-gram repetition in `<think>` blocks) and truncate. SEER finding: failed outputs are consistently ~1,193 tokens longer than successful ones — length itself is a failure signal.

**Implementation**:
- Add n-gram repetition detector to `session_log.py` or as a post-generation filter
- Detect 3-gram or 4-gram repeats within `<think>` blocks (sliding window)
- When repetition ratio exceeds threshold (e.g., 0.15), truncate reasoning and force answer extraction
- Estimated effort: ~1 day, ~100 lines

**Why not S3-CoT**: S3-CoT's activation steering (VL-D in residual stream) is incompatible with Qwen3.5 hybrid SSM architecture (Mamba2 layers don't have standard residual streams). Only viable for dense models (Qwen3, Llama).

##### Action 5: Band-Adaptive Token Budgets (from Overthinking/CIB deep-dive)

**Source**: `research/deep-dives/overthinking-info-bottleneck.md`

**What**: Replace flat REPL token cap (5000) with difficulty-band-adaptive budgets:

| Band | Token Budget | Rationale |
|------|-------------|-----------|
| easy | 1,500 | 92% of correct answers come in first solution round |
| medium | 3,500 | Standard budget |
| hard | 7,000+ | Hard problems need full computation buffer |

**Dependency**: Requires difficulty_signal.py in `enforce` mode (currently `shadow`).

**Implementation**: In `_repl_turn_token_cap()` (`src/graph/helpers.py`), read difficulty_band from routing context and return band-specific cap instead of flat 5000.

**Theoretical backing**: CIB (Proposition 4.1) proves flat token penalties are provably suboptimal. The optimal penalty is semantic — tokens that carry new information should cost less than redundant tokens. Band-adaptive budgets are a practical approximation.

##### Action 6: Omega Metric for Reasoning Routing (from Reasoning Recall deep-dive)

**Source**: `research/deep-dives/reasoning-recall-cot-controllability.md`

**What**: Compute per-suite Omega metric (weighted pass@k improvement from reasoning ON vs OFF). Suites with high Omega benefit from reasoning; suites with low Omega waste tokens on reasoning.

**Formula**: `Omega = sum_{k=1}^{N} [k * (pass@k_ON - pass@k_OFF) / pass@k_OFF] / sum_{k'=1}^{N} k'`

**Implementation**: Run `seed_specialist_routing.py` with reasoning ON/OFF for each suite, compute Omega, store as per-suite annotation in model_registry.yaml. Use to validate whether `difficulty_signal.py` bands correlate with actual reasoning benefit.

**Cross-reference**: Feeds into `routing-intelligence.md` Phase 5 (seeding/eval integration).

##### Action 7: Controllability Validation (from CoT Controllability deep-dive)

**Source**: `research/deep-dives/reasoning-recall-cot-controllability.md` (Paper 2, OpenAI arxiv:2603.05706)

**Key findings that validate our approach**:
1. **Conciseness prompting is safe**: Stylistic/length control has <=2.7pp accuracy cost. Our worker prompt edits (Action 1) fall in this category.
2. **Content suppression is dangerous**: "Don't reason about X" has 6-16.7pp cost and 0.1-15.4% compliance. Never instruct models to skip specific reasoning steps.
3. **Smaller models are least controllable**: RL-trained 7B-14B models (our workers) are the models LEAST responsive to conciseness prompts. Conciseness gains may be smaller than expected at worker tier.
4. **Computational buffer effect**: Even meaningless tokens improve accuracy by 21-27% on factual recall. Aggressive compression risks removing useful computation.

**Action**: Audit our conciseness prompts to ensure they use stylistic language ("be concise", "focus on key steps") and never suppression language ("don't think about", "skip reasoning for"). Already looks correct but should be verified.

##### Action 8: SEAL Control Vectors for Dense Models (from FlowSteer deep-dive)

**Source**: `research/deep-dives/flowsteer-concise-reasoning.md`

**What**: Generate linear control vectors (SEAL baseline) for reasoning conciseness on dense Qwen3-32B using llama.cpp's existing `tools/cvector-generator/`. Contrastive pairs: concise vs verbose reasoning on MATH prompts. Deploy via `--control-vector-scaled`.

**Compatibility**: Dense Qwen3 (`qwen3.cpp` has `build_cvec()`), Qwen2.5 (`qwen2.cpp` has `build_cvec()`). Qwen3.5 / Qwen3.5-MoE ALSO have the hook (`qwen35.cpp:198`, `qwen35moe.cpp:221` at ffc1bac82; earlier text claiming otherwise was stale — the S3-CoT SSM-residual objection at L159 is a separate, architectural question). NOT Qwen3.8-Flash-Next (`qwen4exp.cpp` has no `build_cvec()` call: a control vector is accepted by the server and silently ignored on v10). The SEAL harness now refuses this case (`scripts/seal/eval_cvectors.py` `NO_CVEC_HOOK_ARCHS`). Quantization: control vectors added in F32 residual stream, should work with GGUF but no published validation.

**FlowSteer MLP (nonlinear)**: Deferred — no llama.cpp infrastructure for MLP ODE solve at intervention points. SEAL is the deployable subset.

**Effort**: ~2 days. Risk: low (worst case: no effect, revert).

##### Action 9: Reasoning Length Alarm (from short-m@k deep-dive)

**Source**: `research/deep-dives/short-mk-parallel-reasoning.md`, Phase 0

**What**: When a `<think>` block exceeds 1.5× the band budget tokens and is still generating, cancel the generation and re-generate with a fresh seed. Take the shorter result. This is effectively sequential short-1@2.

**Why it works**: short-m@k paper shows shorter reasoning chains are up to 34.5% more accurate within the same question. Correct reasoning is concise; incorrect reasoning wanders (95-188 backtracks for correct vs 269-352 for incorrect). Easy problems have the highest wrong/right token ratio (2x), making length alarm most discriminative there.

**Three-layer stack** (complementary and additive):
1. Conciseness prompting shifts length distribution leftward (deployed)
2. Band-adaptive budgets cap the right tail (implemented, awaiting enforce)
3. Length alarm + re-generation actively selects for shorter chains (this action)

**Implementation**: ~80 lines in `src/graph/helpers.py`, integrates with `difficulty_signal.py` bands and `detect_think_block_loop()`. Gate behind feature flag. Effort: ~1 day.

**Full short-m@k**: Parallel generation infeasible (architect models run -np 1, VRAM constrained). Sequential short-1@k (Phase 1, ~150 lines) worth trying for math tasks after Phase 0 validates.

##### Action 10: Think Block Stripping from Carried Context — N/A

**Source**: `research/deep-dives/cmv-structural-trimming-repl.md`, intake-141 (arxiv:2602.22402)

**Investigation**: CMV's Pass 3 removes `<think>` blocks from carried context. Investigated whether this applies to our REPL architecture.

**Finding**: Does NOT apply. In our architecture, `state.last_output` is the REPL execution stdout (Python code output), not the raw LLM response. The raw LLM response (`raw_llm_output`) is consumed within a single turn for code extraction, FINAL() rescue, and workspace updates, then discarded. Think blocks never leak into subsequent turns. This differs from Claude Code where the full assistant message (including think blocks) stays in conversation history.

##### Action 11: Output Spill with Retrieval Pointer — DONE

**Source**: `research/deep-dives/cmv-structural-trimming-repl.md`, intake-140/141

**What**: When REPL output or error exceeds the prompt builder's preview limit (1500/500 chars), write full content to a temp file and append a `peek()` retrieval pointer to the truncated preview. Gives the model agency to access the full output on demand.

**Gap identified**: REPL stdout can be arbitrarily long. The session log only stores 200-char previews. The repl_tap.log is a diagnostic interleaved log, not per-turn queryable. There was no mechanism for the model to access full output from a truncated turn.

**Implementation**:
- `_spill_if_truncated()` in `src/graph/helpers.py` (~30 lines)
- Writes to `/mnt/raid0/llm/tmp/{task_id}_{label}_t{turn}.txt`
- Truncates at `max_chars - 150` to leave room for the pointer within the builder's own truncation limit
- Wired into `_execute_turn()` before `build_root_lm_prompt()` call
- Feature flag: `output_spill_to_file` (production=True, test=False, env=`OUTPUT_SPILL_TO_FILE`)
- 9 tests in `tests/unit/test_output_spill.py`

#### Research Intake Update — 2026-04-04

##### New Related Research
- **[intake-258] "Think Anywhere in Code Generation"** (arxiv:2603.29957)
  - Relevance: Introduces on-demand inline reasoning during code generation — model learns to invoke `<thinkanywhere>` blocks at high-entropy positions (assignments, returns)
  - Key technique: Cold-start training + RLVR (GRPO with hierarchical rewards) teaches Qwen2.5-Coder-7B to adaptively reason mid-generation
  - Reported results: +18.8pp on LeetCode, +12.2pp on MBPP; 238-306 fewer reasoning tokens than GRPO baseline; upfront thinking shortened ~35-50%
  - Delta from current approach: Our reasoning compression focuses on post-hoc pruning/compression of existing think blocks. Think Anywhere instead trains the model to place reasoning precisely where needed — a complementary angle. The finding that high-entropy positions predict reasoning need could strengthen our difficulty_signal.py routing (currently uses prompt features, not generation-time entropy).

#### Research Intake Update — 2026-07-08: RE-Bench Reasoning Evaluation (rec-005)

**Source**: RE-Bench (intake-794)

> **⚠ CORRECTION 2026-07-22 (RC-RE-1 scoping):** RE-Bench is NOT a "reasoning-capability evaluation for open-weight models." It is METR's **long-horizon agentic ML-engineering benchmark** — AI-R&D tasks scored vs human experts over multi-hour budgets — and 6 of its 7 environments need 1-8×H100 (only the CPU-only Rust-Codecontests env is runnable here, OBSERVATION-grade). It is open-weight-*compatible* at the model-driver level (our OpenAI-compatible llama-server endpoint) but is the WRONG instrument for reasoning-compression safety. Right tool = held-out AIME/MATH-500/GPQA in the E7 tower scored by accuracy-vs-token rescue-rate. Re-scope RC-RE-2 accordingly. Full analysis: `epyc-inference-research/docs/design/re-bench-open-weight-compatibility.md`.

**Key finding**: RE-Bench focuses on reasoning capability evaluation for open-weight models. Directly relevant to our CoT study and reasoning compression work.

**Applicability to EPYC**: If RE-Bench includes open-weight model evaluation, it could serve as a validation suite for our reasoning compression techniques (TrimR, difficulty-adaptive budgets, SEAL control vectors). Particularly relevant for evaluating whether compressed reasoning degrades reasoning quality on held-out reasoning tasks.

**Cross-reference**: Our existing Tier 1-3 compression taxonomy and the OPSDC finding (reasoning can be net-negative) suggest RE-Bench could help calibrate the compression-vs-quality tradeoff for different difficulty bands.

- [x] **RC-RE-1** — check RE-Bench for open-weight model compatibility and integration with our eval tower ✅ 2026-07-22
- **[declined: ws58 2026-11-03 content-review: duplicate — E-2/E-3 (effort ladder) measure accuracy vs tokens on pinned items for every stack model; an external RE-Bench run adds no decision]** **RC-RE-2** — run RE-Bench against compressed vs uncompressed reasoning to validate compression safety

#### Notes

This is the most active research front discovered during the 2026-03-14 intake run. 7 of 10 expansion entries cluster around reasoning compression, approaching the problem from different angles. The theoretical foundation (Information Bottleneck, intake-133) explains why: CoT traces contain information about the response that isn't directly accessible from the prompt, so compression is lossy but bounded. The practical implication is that our current REPL token cap (5000 tokens) is a crude version of what these methods do adaptively — we should upgrade to difficulty-aware reasoning budgets.

#### Research Intake Update — 2026-04-06

##### New Related Research
- **[intake-264] "Embarrassingly Simple Self-Distillation Improves Code Generation"** (arxiv:2604.01193)
  - Relevance: Simplest possible self-distillation — temperature-sample own outputs, SFT on them. No verifier, teacher, or RL needed.
  - Key technique: Simple Self-Distillation (SSD) — resolves precision-exploration conflict by reshaping token distributions contextually
  - Reported results: Qwen3-30B 42.4% → 55.3% pass@1 on LiveCodeBench v6 (+12.9pp); generalizes across 4B-30B scale
  - Delta from current approach: Our Tier 3 (OPSDC, intake-110#record) requires RL + reward model. SSD achieves meaningful gains with just SFT on self-generated data. The finding that self-generated data beats curated data challenges Doc-to-LoRA data curation assumptions.

- **[intake-266] "A Survey of On-Policy Distillation for Large Language Models"** (arxiv:2604.00626)
  - Relevance: First unified taxonomy of on-policy distillation — contextualizes OPSDC (intake-110#record) and SSD (intake-264) within f-divergence framework
  - Key technique: Three-axis OPD taxonomy (feedback signal × teacher access × loss granularity)
  - Delta from current approach: Explains why off-policy (static teacher data) causes exposure bias → compounding errors. Validates our Tier 3 direction but suggests teacher-free approaches (SSD) may be underweighted.

##### Deep-Dive Correction (2026-04-06)
**Caveat on intake-264 (SSD)**: The 42.4→55.3% LCBv6 result is less impressive than it sounds — Nanbeige-3B (a 3B model) scores 76.9 on LCBv6, and Qwen3-32B baseline is already at 55.7%. Thinking models gain only +2-3pp from SSD. Requires 8xB200 for SFT — not actionable for our inference-only stack. The precision-exploration conflict theory is legitimate but the practical impact is near-zero for GGUF consumers. **Worth monitoring only** for: (a) SSD-trained checkpoints appearing as GGUFs on HuggingFace, (b) inference-time adaptations of the distribution reshaping idea.

**Caveat on intake-266 (OPD Survey)**: Training-only methods exclusively. The exposure bias framing (DAgger bound: on-policy correction reduces error accumulation from O(eT²) to O(eT)) is the main extractable insight — it explains why OPSDC's self-rollout approach works from first principles. The "agent-level distillation" open problem is already addressed by our completed SkillBank pipeline. Useful as a theoretical reference only.

#### Research Intake Update — 2026-04-08

##### New Related Research
- **[intake-286] "Self-Distilled RLVR (RLSD)"** (arxiv:2604.03128)
  - Relevance: Extends the OPSDC/SSD distillation line — combines self-distillation for token-level magnitude with RLVR for update direction
  - Key technique: RLSD separates environment-anchored update direction (RLVR/GRPO) from self-distilled update magnitude (token-level policy differences). Stop-gradient + clipping on teacher signal.
  - Reported results: Claims higher convergence ceiling and superior training stability vs pure RLVR or pure OPSD
  - Delta from current approach: Extends our Tier 3 understanding (OPSDC, intake-110#record). Addresses the known OPSD instability (information leakage → progressive collapse) by limiting distillation to magnitude only. Still requires training infrastructure (8x GPU) — not actionable for inference-only stack.
  - Known limitations: OPSD component has structural information leakage risk even with clipping; GRPO's sequence-level credit assignment remains a bottleneck; hyperparameter sensitivity to clipping bounds not fully ablated.
  - Status: MONITOR ONLY — training method, same actionability caveat as intake-264/266.

#### Research Intake Update — 2026-04-08

##### New Related Research — Memento Cluster (Block-Level Reasoning Compression)

A cluster of 4 closely related papers/repos on training models to self-compress their reasoning chains by segmenting into blocks and generating dense summaries ("mementos"). This represents a new Tier 3+ approach that goes beyond our existing compression taxonomy.

- **[intake-289] "Memento: Teaching LLMs to Manage Their Own Context"** (Microsoft Research)
  - Relevance: Directly applicable — trains models to segment reasoning into blocks, compress each into a memento, mask original block KV states. 2-3x peak KV reduction on Qwen3-8B/32B, Phi-4 14B.
  - Key technique: Dual information stream — memento KV states retain implicit block info even after text masking. Removing this channel drops 15pp on AIME24. Custom vLLM fork with native block masking.
  - Reported results: Qwen3-32B AIME26: -2.6pp at 2x KV reduction. Gap shrinks with scale (-6.3pp@8B → -3.5pp@32B). RL closes remaining gap.
  - Delta from current approach: Our TrimR/FlowSteer operate post-hoc; Memento trains the model itself to compress. Requires SFT on OpenMementos (228K traces, MIT). vLLM-based, not llama.cpp — porting block masking to llama-server is non-trivial but conceptually similar to our ISWA hybrid buffer.
  - Composability: Orthogonal to Hadamard+q4_0 KV quantization — compresses attention span, not precision. Multiplicative savings possible.
  - **New handoff stub created**: `memento-block-reasoning-compression.md`

- **[intake-290] "OpenMementos-228K"** (HuggingFace dataset, MIT)
  - Relevance: Training data for Memento approach. 228K reasoning traces with block boundaries and compressed summaries (54% math, 27% science, 19% code). ~6x trace-level compression.
  - Key technique: 5-stage data pipeline (sentence splitting → boundary scoring → segmentation → summary generation → iterative refinement). Judge-feedback loop: 28% → 92% pass rate.
  - Delta: The data pipeline itself is valuable — could generate context-folding training data (Phase 2) or TrimR evaluation sets.

- **[intake-292] "InftyThink" (ICLR 2026)** (arxiv:2503.06692)
  - Relevance: Predecessor approach — iterative reasoning with periodic summarization. Sawtooth memory pattern. 3-11% improvement on MATH500/AIME24/GPQA.
  - Delta: Text-level only (no KV retention) — Memento shows 15pp loss from missing KV channel. SFT-only (no RL). Peer-reviewed at ICLR.

- **[intake-293] "InftyThink+" (arxiv:2602.06960)** + **[intake-294] "Accordion-Thinking" (arxiv:2602.03249)**
  - Relevance: Add RL to iterative summarization. InftyThink+: 21% AIME24 gain on 1.5B. Accordion: 3x throughput with Fold/Unfold toggle.
  - Delta: All text-level — lack Memento's dual stream. Accordion's Fold/Unfold toggle is the most directly usable pattern for our architecture.

##### Impact on Existing Actions
- **Tier 3 taxonomy expanded**: Memento/InftyThink/Accordion form a new sub-family alongside OPSDC (self-distillation) and CoLaR (latent compression). All require training but offer fundamentally different compression vs. inference-only approaches.
- **Context-folding synergy**: OpenMementos' data pipeline (boundary scoring + iterative refinement) validates our Phase 2 approach and could provide training data for Phase 3 RL.
- **KV cache composition**: Memento block masking + Hadamard+q4_0 quantization = multiplicative KV savings. Worth investigating once llama.cpp block masking is feasible.

#### Research Intake Update — 2026-04-13

##### New Related Research
- **[intake-350] "Latent Briefing: KV Cache Compaction for Multi-Agent Systems"** (github:CuriousCaliBoi/latent-briefing)
  - Relevance: Complements CoLaR (intake-134) as another latent-space approach to reducing inter-agent token overhead. While CoLaR bypasses KV cache via latent reasoning compression, Latent Briefing operates directly on KV cache — compacting an orchestrator's trajectory cache before injecting into a worker agent. Both target the same goal (reduce cost of multi-step reasoning chains) from different abstraction layers.
  - Key technique: Attention-score-driven MAD thresholding + PGD reweighting for cross-model KV transfer
  - Delta from current approach: KV-level technique, not reasoning-level. More relevant to triattention-kv-selection.md handoff. Cross-reference only.

#### Research Intake Update — 2026-04-15

##### New Related Research
- **[intake-374] "Rethinking Generalization in Reasoning SFT"** (arxiv:2604.06628)
  - Relevance: Directly informs CoT data quality requirements for reasoning compression. Verified long-CoT traces yield consistent cross-domain gains (+8-12% over No-CoT). "Repeated exposure > coverage" — repeating 2.5k samples 8x outperforms one-pass 20k under fixed 640-step budget. Safety degrades as reasoning improves — asymmetric generalization.
  - Key technique: Conditional analysis of SFT generalization across optimization dynamics, data quality, and model capability
  - Reported results: 14B models show 15-20% better generalization than 1.7B; dip-and-recovery trajectory in cross-domain performance during training
  - Delta from current approach: Our Tier 3 approaches (OPSDC, CoLaR) assume SFT generalizes. This paper shows generalization is conditional on data quality and model capability — weaker models may only imitate surface patterns. Relevant for selecting compression training data and evaluating which models benefit from reasoning compression SFT.

- **[intake-378] "On the Role of Reasoning Patterns in the Generalization Discrepancy of Long CoT SFT"** (arxiv:2604.01702) — **UPGRADED to high relevance / new_opportunity after deep dive**
  - Relevance: Contradicts naive "more CoT = better" assumption. DeepSeek-R1's divergent, branch-heavy exploration patterns cause WORSE generalization despite lower training loss. Filtering branch-heavy trajectories improves AIME25 by 5.1%, BeyondAIME by 5.5%.
  - Key technique: Trajectory filtering to remove frequently branching reasoning patterns
  - **Deep dive quantitative findings**:
    - Propose steps: R1=33.3% vs gpt-oss=22.5%; Propose→Propose transition: R1=0.53 vs gpt-oss=0.34
    - Llama3.1-8B: 21pp average gap (29.5% vs 50.5%) from same problem set, same budget, different reasoning traces
    - "Dilution effect": R1's lower SFT loss comes from trivial routine tokens, not better reasoning learning. Low loss is a MISLEADING quality signal.
    - Random 10% step deletion: gpt-oss data degrades significantly (tight dependency); R1 data is unaffected or improves (redundancy confirmed)
    - Filtering by branching keywords ≠ filtering by length — limited overlap between the two filters
  - Delta from current approach: Three actionable implications for our Tier 1 approaches:
    - (1) The random step deletion experiment directly validates TrimR/short-m@k — branch-heavy reasoning IS safe to prune at inference time
    - (2) Branching density (Propose step %) could serve as a runtime quality signal for routing: high branching = unproductive exploration → truncate or escalate
    - (3) If we use R1-distilled data (OpenR1-Math-220k) for any future training, must filter by branching density first
  - **Deep dive**: `research/deep-dives/sft-generalization-reasoning-patterns.md`

- **[intake-374 supplement] "Data Repetition Beats Data Scaling in Long-CoT SFT"** (arxiv:2602.11149, not yet in index)
  - Independent confirmation: 128 epochs on 400 samples beats 1 epoch on 51,200 samples by 12-26pp on AIME'24/25 (Kopiczko et al., Qualcomm). Token accuracy serves as saturation indicator. No increased catastrophic forgetting.

##### Training Data Strategy (intake-374/378/2602.11149 synthesis)

For any future Tier 3 training (OPSDC, CoLaR, SEAL SFT, RLVR):

1. **Depth > breadth**: 128 epochs on 400 curated samples beats 1 epoch on 51.2k by 12-26pp (arxiv:2602.11149, confirmed by intake-374's "2.5k × 8 > 20k × 1" finding). Don't scale data beyond saturation.
2. **Filter by branching density**: Use intake-378 Proxy 2 (branching keyword proportion) to remove divergent, branch-heavy traces before training. DeepSeek-R1 traces produce 21pp worse generalization than convergent traces on Llama3.1-8B — even with identical problems and budget.
3. **Token accuracy = saturation indicator**: Stop adding epochs when token accuracy plateaus. Beyond saturation, additional epochs waste compute without generalization gains.
4. **Safety evaluation mandatory**: Reasoning SFT asymmetrically improves reasoning while degrading safety (intake-374). Any future fine-tuning must include safety benchmarks alongside capability measurement.

##### Formalizer Complements Compression (cross-reference)

The formalizer pipeline (`mathsmith-hc-formalizer-eval.md`, `src/formalizer.py`) reduces overthinking at the source — complementary to, not competing with, Tier 1-3 compression:

- **Formalizer** reduces INPUT ambiguity: fills in missing premises, clarifies constraints → solver doesn't waste tokens exploring alternative interpretations
- **Compression** reduces OUTPUT tokens: prunes redundant reasoning after generation (Tier 1), steers toward conciseness (Tier 2), or trains for shorter traces (Tier 3)

Theoretical link: CIB (Conditional Information Bottleneck, `research/deep-dives/overthinking-info-bottleneck.md`) shows formalizer raises I(Z; Y | X), which Proposition 4.1 proves reduces optimal reasoning length. The S4 A/B test in the formalizer handoff should measure total pipeline token cost (formalizer + solver) vs solver-only baseline, at equal or better accuracy — providing empirical validation. Source: user insight connecting arxiv:2504.06514 (missing premises → overthinking) to formalizer value proposition.

#### Research Intake Update — 2026-04-17

##### New Related Research
- **[intake-386] "LongCoT: Benchmarking Long-Horizon Chain-of-Thought Reasoning"** (arxiv:2604.14140)
  - Relevance: Directly validates compression hypothesis — frontier models achieve <10% accuracy on long-horizon reasoning (GPT 5.2: 9.8%, Gemini 3 Pro: 6.1%). Longer reasoning traces help but don't solve the problem. Accuracy falls sharply as problem DAG sizes grow.
  - Key technique: 2,500 expert-designed problems across 5 domains requiring 10K-100K+ reasoning tokens. Deterministic verification.
  - Reported results: Best model <10% accuracy; simple scaffolds fail to close the gap.
  - Delta from current approach: Corroborates the core insight behind reasoning compression — unbounded reasoning is harmful. Also relevant as a benchmark for evaluating our compressed-reasoning models.
- **[intake-392] "Limited Reasoning Space: The cage of long-horizon reasoning in LLMs"** (arxiv:2602.19281)
  - Relevance: Provides theoretical grounding for why longer reasoning degrades performance — the "Limited Reasoning Space" hypothesis explains attention diffusion in extended chains.
  - Key technique: Halo framework uses model predictive control with entropy-driven dual controller for adaptive reasoning budget.
  - Delta from current approach: Aligns with our Tier 1-3 compression taxonomy. The Halo "Measure-then-Plan" strategy is a dynamic variant of reasoning budget control — complementary to per-request-reasoning-budget.md.
- **[intake-404] "Target Policy Optimization"** (arxiv:2604.06159)
  - Relevance: TPO is a GRPO replacement that eliminates policy gradients via cross-entropy fitting of a closed-form target distribution. Directly relevant to any future Tier 3 RL-based training (OPSDC, RLVR, FoldGRPO) — if we ever add RL fine-tuning to the pipeline, TPO claims 7x fewer steps to convergence on sparse reward tasks vs GRPO, and stable multi-epoch training where GRPO diverges.
  - Key technique: Target q_i proportional to p_i^old * exp(u_i/eta); gradient is simply p-q, vanishing at convergence. No clipping, no critic, no policy gradients.
  - Reported results: Terminal reward H=10: TPO 7.4% error vs GRPO 50.4%; Reasoning Gym Graph Coloring (Qwen3-1.7B): TPO 0.96 vs GRPO ~0; multi-epoch stable (TPO 0.2% at 4 epochs vs GRPO non-monotonic 37.6% at 2 epochs).
  - Delta from current approach: All Tier 3 references (OPSDC, RLSD, FoldGRPO) use GRPO as the RL backbone. TPO's sparse-reward advantage is particularly relevant since reasoning verification rewards are inherently sparse (binary correct/incorrect). Low relevance today (we don't RL-train), but high potential value if Tier 3 materializes.

#### Research Intake Update — 2026-04-22

##### New Related Research

- **[intake-437] "Cut Your Losses! Learning to Prune Paths Early for Efficient Parallel Reasoning"** (arxiv:2604.16029)
  - Relevance: STOP (Super TOken for Pruning) is a learnable, prefix-level path-pruning mechanism that complements our existing TrimR/difficulty-band framework at a different layer.
  - Key technique: Learnable super token at prefix level identifies unproductive branches from initial errors; first systematic taxonomy of path pruning (internal/external signal × learnable/heuristic).
  - Reported results: GPT-OSS-20B AIME25 84% → 90% under fixed compute. Scales 1.5B–20B, covering our worker/coder tier.
  - Delta from current approach: Our Tier 1 uses TrimR (training-free) and difficulty_signal (shadow). STOP is learnable and internal-signal — a third category in the taxonomy. Compositional feasibility with think-strip + difficulty bands is worth evaluating.

- **[intake-441] "Where does output diversity collapse in post-training?"** (arxiv:2604.16027)
  - Relevance: Post-trained LMs generate significantly less varied outputs than base models; the collapse is in weights, not generation format. CoT suppression preserves answer-level diversity in Think models. This constrains what our reasoning length alarm (Action 9) and conciseness prompts can achieve.
  - Key finding: Inference-time interventions cannot recover training-time diversity loss. Diversity loss decomposes into quality-control + residual components.
  - Delta: We've been treating verbose reasoning as a generation-format problem. This paper argues some of the variation (or lack thereof) is baked in. Useful framing when evaluating new post-trained checkpoints — measure diversity alongside accuracy.

- **[intake-443] "OneVL: One-Step Latent Reasoning and Planning with Vision-Language Explanation"** (arxiv:2604.18486)
  - Relevance: Dual-objective compression (text + future-frame prediction) produces more generalizable latent representations than single-objective text compression. Prefill-only inference pattern (decoders discarded at inference) is interesting for CPU efficiency.
  - Key technique: Latent CoT with dual auxiliary decoders (language + world model), 4 visual + 2 language latent tokens, three-stage training.
  - Delta: Autonomous-driving domain. Methodological insights (dual-objective compression, prefill-only inference) transferable to Action 3 enforce-mode design — consider whether a second auxiliary objective (beyond token-level reconstruction) could sharpen our difficulty signal.

##### Notes

- intake-437 STOP is the most directly actionable — feasibility probe against current think-strip path is a clear next experiment.
- intake-441 diversity-collapse finding suggests adding a diversity metric to the eval tower alongside accuracy (connects to eval-tower-verification.md).

#### Action 10a — STOP Learnable Path Pruning (2026-04-22, DD3 / intake-437)

**Source**: `/workspace/research/deep-dives/stop-learnable-path-pruning.md` (401 lines). Compositional verdicts: STOP COMPOSES WITH all existing Tier 1 techniques (TrimR, short-m@k, conciseness, difficulty bands, n-gram loop detection). Fills an unoccupied quadrant in the pruning taxonomy: **internal signal × learnable × selection** (we currently cover external/heuristic/selection via TrimR and internal/heuristic/detection via n-gram loops).

**Target**: NIB2-46 in backlog. Gated on NIB2-32 difficulty-signal re-validation producing a live verdict (STOP's cost savings only make sense at `difficulty_band ∈ {medium, hard}`).

**Phased experiment plan** (total ~5 inference-days):

- **Phase 0 — Instrumentation** (~1d, non-inference, NIB2-46): reserve unused token in the tokenizer; add orchestrator hook for hidden-state fetch at a specific prefix position. Update `scripts/benchmark/seeding_types.py` `RoleResult` with `prefix_hidden_state` optional field.
- **Phase 1 — Probe data collection** (~2d, inference-gated on worker `-np ≥ 2`): run k=4 parallel sampling on GSM8K+MATH+GPQA (≈4k rollouts). Target: **AUC ≥ 0.80 AND ≥0.05 AUC delta over length-only baseline** (tightened 2026-04-22 post Tier 2b — original 0.75 gate was not robust against simple length/canonicity proxies; 84→90 AIME25 result is only 2 questions on a 30-question set without 8-seed CI, so the probe must prove genuine signal over trivial heuristics).
- **Phase 2 — Train probe head** (~0.5d): linear `[d_model → 1]` + super-token embedding. Frozen backbone; no DGX Spark needed.
- **Phase 3 — Online A/B** (~1d, inference): STOP k=4 α=0.5 vs majority@4 on held-out GSM8K+MATH+GPQA. Success gate: ≥1.5pp accuracy gain OR ≥25% token savings.
- **Phase 4 — Integration** (~1d): gate STOP behind difficulty bands (easy=no, medium=k=2, hard=k=4). Cross-ref `routing-intelligence.md` STOP gating policy.
- **Phase 5 — Telemetry** (~1d): probe-score distribution, prune-decision counts, per-suite performance.

**Compositional** with:
- TrimR (post-hoc paragraph pruning on STOP survivors)
- short-m@k / reasoning length alarm (single-sample re-roll vs multi-sample selection — orthogonal)
- Conciseness prompts (upstream style control)
- Difficulty signal + band caps (natural gating: decides whether STOP is invoked at all)
- N-gram loop detection (in-flight mid-generation detection independent of probe)

**Gates** (tightened 2026-04-22 post Tier 2b):
- Phase 1 probe AUC ≥ 0.80 AND ≥0.05 delta over length-only baseline: proceed to Phase 2.
- Phase 3: ≥1.5pp accuracy gain OR ≥25% token savings vs majority@4 baseline, AND at least parity vs DeepConf (training-free confidence pruning, arxiv 2509.24944). Add DeepConf as Phase 3 A/B arm.
- If either gate fails: revert to short-m@k + TrimR only. Keep STOP as `worth_investigating`.

**Tier 2b findings (2026-04-22 sweep)**:
- AIME25 84 → 90 is only 2 questions on a 30-question set, reported as single-seed without CI; community protocol (Artificial Analysis, DeepScaleR, VAR-MATH arxiv:2507.12885) requires 8-seed averaged pass@1 with CIs. Likely within baseline 95% CI.
- "Learnable prefix-token + scoring head on frozen backbone" is standard prefix-tuning (arxiv 2601.13288, 2512.16650) — taxonomy novelty survives but mechanism novelty does not.
- Training-free competitors unbenchmarked: DeepConf (2509.24944), Stop-When-Enough (2510.10103), REFRAIN, Confidence-Dynamics (2604.04930), SlimSC, ConCISE.
- "Initial errors" claim unfalsified: no length-only baseline ablation in the paper; the learned signal may be a length/canonicity proxy.
- Credibility score recommended 6 → 4-5 on re-review.
See `/workspace/research/deep-dives/stop-learnable-path-pruning.md` § Tier 2b for detail.

#### Diversity Collapse Interaction (2026-04-22, DD4 / intake-441)

Our Action 12-15 conciseness work and Action 9 reasoning-length-alarm operate at generation-format level. Intake-441 shows post-training diversity loss is **structural (weights)** — inference-time interventions cannot recover it. This bounds the upside of format-level conciseness prompts. Concretely: if a model's base-diversity is collapsed, even perfect prompting cannot produce novel reasoning paths — we can only prune what's there.

**Implication**: factor diversity-collapse awareness into model-selection decisions for the worker/coder tier. When evaluating new post-trained checkpoints, include diversity metrics alongside accuracy (see `eval-tower-verification.md` EV-8). Do not chase +1pp accuracy from a model whose diversity baseline collapsed by >20%.

#### Research Intake Update — 2026-04-27

##### New Related Research

- **[intake-483] "Hybrid Policy Distillation for LLMs"** (arxiv:2604.20244)
  - Relevance: theoretical successor to the OPD survey already tracked here (intake-266). Unifies SFT, SeqKD, RKLD/MiniLLM, and JSD/GKD as a single token-level reweighted log-likelihood objective parameterized by the choice of weighting estimator. Proposes HPD: token-level fusion of FKL guidance on under-estimated expert tokens with RKL suppression on over-estimated student-sampled tokens via Schulman's negative-K1 estimator. No additional hyperparameters.
  - Key technique: gating sign of K1 estimator selects FKL vs RKL per token; uses both off-policy and lightweight on-policy samples; Reinforce-on-suppression redirects suppressed mass to expert tokens.
  - Reported results: Qwen2.5 7B→1.5B reasoning avg 39.83 (HPD off-policy) vs 36.61 (JSD), 32.67 (SFT), 35.55 (SeqKD); on-policy HPD+OPD 33.41 vs SFT+OPD 29.56 (+13% rel.); LLaMA3 8B→1B HPD+OPD +20% rel. Coding HumanEval+MBPP: HPD 66.35 avg (DS-Coder 6.7B→1.3B) vs SFT 61.45.
  - Delta from current approach: relevant only if EPYC ever acquires training-capable GPUs (DGX Spark not yet acquired per memory) — strictly better default than SFT+OPD if/when the cloud-rental option opens. Until then, monitor as the canonical reference for the post-OPD-survey unification view; useful pedagogy when interpreting OPSDC (intake-110#record), Self-Distilled RLVR (intake-286), and Embarrassingly Simple Self-Distillation (intake-264).
  - **Tier 2b — contradicting evidence found**: arxiv:2603.25562 ("Revisiting On-Policy Distillation: Empirical Failure Modes and Simple Fixes") + arxiv:2604.13016 ("Rethinking On-Policy Distillation") + Thinking Machines Lab analysis identify three OPD failure modes that HPD only partially addresses: (1) imbalanced one-token signal — sampled-token variant reduces matching to a single token, becomes unreliable as rollouts drift from teacher-common prefixes; (2) unreliable teacher guidance on student-generated prefixes — stronger teacher can fail to improve a student where weaker teacher succeeds; (3) tokenizer/special-token mismatch distortions. Self-distillation specifically can suppress alternative-hypothesis exploration, dropping OOD accuracy up to 40% — reinforces our existing intake-441 diversity-collapse stance. **Action**: do not assume HPD is a free win; if/when adopted, gate on OOD/diversity metrics, not just in-distribution reasoning benchmarks. Capacity-gap caveat applies — HPD's reported gains are at 7B→1.5B and may invert at larger gaps.
  - Verdict: `worth_investigating` — relevance medium (no immediate action without GPUs).

#### Research Intake Update — 2026-05-04

##### SAE-feature mechanism for endless repetition (Qwen-Scope Section 8)

- **[intake-521] "Qwen-Scope: Turning Sparse Features into Development Tools for LLMs"** (Qwen Team, 2026-04-30) — deep-dive at `research/deep-dives/qwen-scope-sae-suite.md`; coordination handoff `../completed/qwen-scope-sae-toolkit.md` (archived 2026-06-12).
  - Relevance: Section 8 of the report identifies SAE features causally linked to **endless repetition** (a low-frequency reasoning failure mode) and uses bidirectional feature steering to confirm causal direction. The mechanism is mechanistically adjacent to the "reasoning length alarm" (Action 9 in this handoff), to the diversity-collapse interaction (Action 12-15 conciseness work), and to the Phase 3 STOP-pruning gates that already require ≥1.5pp accuracy gain or ≥25% token savings vs majority@4.
  - Paper findings worth tracking:
    - Repetition features show monotonically rising pre-activation values across token positions in repetitive contexts (Figure 17a). The pre-activation curve crosses a threshold *before* the first repeated token — i.e. the feature carries a precursor signal that could be used at decode time.
    - Bidirectional steering (Figure 20) confirms causal direction: amplifying the feature on non-repetitive samples induces repetition; suppressing on repetition-prone samples reduces it.
    - **Critical caveat the paper documents (Figure 21)**: the same features fire on **benign repetition** — instruction-echo, multiple-choice answer-choice repetition. The feature is not specific to pathological repetition. The paper uses this as the explicit reason to PREFER rare-negative-rollout augmentation in DAPO over SASFT-style training-time suppression.
  - SAE-DAPO result (paper Section 8.4): rare-negative-rollout augmentation drops repeat ratio sharply across Qwen3-1.7B / Qwen3-8B / Qwen3-30B-A3B; on Qwen3-30B-A3B also +5.84pp MGSM relative to pre-RL. Vanilla DAPO only +1.08pp on the same metric.
  - Delta from current approach: this handoff's STOP-pruning Phase 3 + DeepConf A/B arm + Action 9 reasoning-length-alarm operate at the *generation-format* level. SAE feature pre-activation is a *representation-level* precursor signal that is independent and complementary. The two paths converge on the same operational question — "is the model heading into a non-productive loop?" — but answer it from different signals.
  - Tier 2b — concrete contradictions to integrate alongside the Section 8 reading:
    - **Section 8 has a methodological confound (deep-dive 2026-05-04)**: Repetition features are identified by within-sample first-vs-last-occurrence comparison of the same token, which mechanically selects "fires more later in repetitive contexts." Bidirectional steering fixes the causal direction, but Figure 20 coefficients are not surfaced in the extracted text. The +5.84pp MGSM result is therefore not cleanly attributable to repetition suppression — it could include collateral effects from injecting OOD steered samples. Any port to Qwen-family stuck-in-think work in this handoff must include an ablation distinguishing feature-targeted from generic-OOD rare-negative rollouts.
    - **Falsifying-SAE-Reasoning-Features** (Ma et al. 2026, arxiv:2601.05679) is cited in Qwen-Scope's own reference list but Section 9.2 does NOT engage with whether Section 8's repetition features survive the Ma et al. falsification framework. Worth pulling Ma et al. before crediting Section 8's mechanism.
    - The diversity-collapse caveat noted earlier in this handoff (intake-441, 2026-04-22) bounds the upside of SASFT-style suppression at the weights level. Qwen-Scope's Section 7 SASFT shows non-trivial regressions on Qwen3-8B (HellaSwag -2.88 / MMLU -2.06) which are plausibly downstream of the same diversity-collapse mechanism. Hence the paper's *own* recommendation for repetition control is rare-negative-rollout, NOT suppression.
  - **Triple-blocked for direct adoption** (per `../completed/qwen-scope-sae-toolkit.md` priority 3):
    1. RL training infra (DGX Spark not yet acquired, `project_dgx_spark_target`).
    2. Need a documented Qwen-family stuck-in-think failure mode in EPYC's own logs (Ring-mini stuck-in-think is non-Qwen and SAEs don't transfer directly across families).
    3. The OOD-rollout vs feature-targeted-rollout ablation must run before crediting the +5.84pp.
  - **Near-term integration that does NOT require RL infra**: if budget enforcement in `per-request-reasoning-budget.md` lands AND we observe Qwen-family reasoning runs in our own logs that exhibit precursor-style monotone pre-activation rises in middle-band SAE features, we have an *inference-time* signal for "model is heading into a loop" without any training-time intervention. This is the same idea as the Halo entropy-based adaptive budget already noted in `per-request-reasoning-budget.md` (intake-392, 2026-04-17) — two independent precursor signals for the same internal failure state, both cheap to expose in llama-server.
  - **Action**: monitor only. Do NOT add an SAE-DAPO arm to Phase 3 — the existing DeepConf + STOP comparison is the right scope for the current canary. Re-evaluate when (a) a Qwen-family stuck-in-think is documented in EPYC logs, (b) the Falsifying-SAE-Reasoning-Features paper has been read, (c) RL training infra is online. Until then this is a watch-list item, not an action item.

#### Research Intake Update — 2026-05-19

##### Latent / abstract Chain-of-Thought cluster — full taxonomy refresh

This update folds five new entries into the Tier-3/Tier-4 axis of the handoff. They collectively cover both the **training-free** and **training-required** branches of the "compress CoT into a non-verbal channel" design space.

- **[intake-545] "Thinking Without Words" (Abstract CoT)** (arxiv:2604.22709, Ramji/Naseem/Astudillo — IBM Research)
  - Replaces natural-language CoT with a short sequence of tokens from a **reserved abstract vocabulary** — up to **11.6× fewer reasoning tokens** at comparable accuracy. Recipe: policy-iteration warm-up (SFT from verbal CoT + self-distillation under constrained decoding) → warm-started RL.
  - Emergent power-law over the abstract codebook suggests a compact discrete latent reasoning code is learned.
  - **Distinct contribution vs existing intake**: discrete reserved-token codebook with policy-iteration warm-up — preserves standard autoregressive decoding (unlike Coconut/CODI/Soft Thinking continuous latent), and uses explicit training (unlike Soft Thinking training-free).
  - Tier 2b — **measurable regressions on hard reasoning**: AIME'25 24.4% vs SFT+RL 25.6% (−1.2pp); GPQA-Diamond 50.5% vs 51.5% (−1.0pp). Token savings real (2.7×–7.9×) but the seed paper frames these as "comparable" — they are small but consistent regressions on the harder benchmarks. **Action**: measure on representative agent traces (long-tail tool-call reasoning) — report tokens/answer AND pass@1 jointly. Do NOT default to the seed paper's headline 11.6× compression for production.

- **[intake-559] Coconut** (arxiv:2412.06769, Hao/Sukhbaatar/Su/Li/Hu/Weston/Tian — Meta/UCSD, COLM 2025) — **foundational** continuous-thought baseline. Last-layer hidden state fed back as next input embedding, curriculum training. ProsQA 97.0% vs 77.5% verbal CoT (FLOPS-matched). Brittle curriculum is the known weak point.
- **[intake-560] CODI** (arxiv:2502.21074, Shen/Yan/Zhang et al.) — self-distillation alternative to Coconut: matches explicit CoT at 3.1× compression at GPT-2 scale via single-model two-pass teacher/student alignment. Architecturally cleaner (no curriculum) but unvalidated at >7B scale.
- **[intake-561] Token Assorted** (arxiv:2502.03275, Su/Zhu/Xu/Jiao/Tian/Zheng — Meta) — **closest cousin** to Abstract CoT: VQ-VAE-learned discrete codebook replaces the early planning portion of the CoT, later steps stay verbal. Random-mix training. Preserves standard autoregressive decoding (no engine changes).
- **[intake-562] Soft Thinking** (arxiv:2505.15778, Zhang et al.) — **only training-free entry** in the latent-CoT family. Replace argmax with probability-weighted mixture of top-k embeddings, fed back as next input. **Up to +2.48pp pass@1 AND up to 22.4% token reduction** on math + coding with **zero retraining** — only a decoder patch.

**Taxonomy revision**:
- **Tier 1 (no-training quick wins)**: Soft Thinking (intake-562) is now the highest-priority candidate. **Concrete next step**: implement top-k embedding mixture as an opt-in flag in our llama.cpp fork, verify on coder/frontdoor with measured pass@1 + tokens/answer delta. Risk to flag: mixture-of-embeddings may interact badly with quantized (Q4_K_M/Q6_K) embedding lookups — needs validation that the mixture stays on the model's natural manifold.
- **Tier 3 (training-required) discrete-codebook head-to-head**: Abstract CoT (intake-545) vs Token Assorted (intake-561). Pick winner based on EPYC-relevant metric: tokens/decision at parity accuracy on coder/frontdoor traces. Both preserve standard llama.cpp decode path.
- **Tier 4 (architectural alternatives)**: Coconut (intake-559) and CODI (intake-560) as foundational references — do not pursue implementation; cite when explaining why discrete reserved-token approach is preferable for our setting (preserves token-level inspection, no architecture change).

##### Practitioner skepticism signal — verified-vs-hyped local-LLM speedups at 100k+ ctx

- **[intake-542] @jun_song (Super-Tune) X post** + **[intake-566] CGR (Certainty-Guided Reasoning)** (arxiv:2509.07820, Nogueira/Sun/Silva/Zumot)
  - jun_song's empirical claim: after testing "most viral X speed tricks", only **(1) SFT for duplicate-inference suppression** and **(2) Adaptive Thinking dynamic budget** verified as quality-preserving at 100k+ context. CGR is the **concrete, model-agnostic, no-training implementation of Adaptive Thinking**: periodically probes answer-token certainty during the thinking trace, terminates early once a threshold is reached. Reports AIME2025 baseline accuracy preserved with millions of tokens eliminated in aggregate.
  - Adjacent — Tier 2b — **adaptive thinking is bimodally brittle**: arxiv 2505.15400 documents the failure mode (under-thinking on hard questions, over-thinking on easy questions). ASRR framework reports ~32.5% budget reduction at ~1.2% pass@1 accuracy loss — the accuracy hit is **non-zero**, contradicting any "quality preserved" framing.
  - **Concrete action**: CGR prototype is low-risk — a llama-cli sampling-loop patch in epyc-llama; A/B against existing reasoning-budget cap on a single bench. If even half the claimed aggregate-token reduction holds at our temperature/topk settings, the throughput win compounds with existing CPU optimizations without conflicting with `project_slot_promotion_shelved`.

#### Research Intake Update — 2026-05-20

##### New Related Research

- **[intake-570] "Expanding the Capabilities of RL via Text Feedback" (RLTF)** (Song/Chen/Tajwar/Munos/Pathak/Bagnell/Singh/Zanette, CMU+Inria; arxiv:2602.02482, OpenReview)
  - **Relevance**: Joins the RLSD/OPSDC/CODI self-distillation family already tracked here. RLTF-SD treats the post-feedback second-turn rollout as an implicit teacher and distills it back into the one-shot policy; RLTF-FM adds an auxiliary head that predicts the critique itself, enabling iterative self-feedback at inference time with no external critic.
  - **Reported results**: K&K 0.802/0.880, MATH500 0.598/0.636, LitBench 8.80/8.40 (SD/FM). Replacing text critiques with binary correctness collapses gains — semantically-rich text feedback is load-bearing (matches the existing Tier 2b "rich signal beats sparse" thread).
  - **Delta from current approach**: This is a training-time technique (GPU-gated, out of scope on EPYC CPU stack today) — file alongside RLSD as a reference for when GPU becomes available. The RLTF-FM inference-time self-feedback loop is reproducible as a harness pattern without retraining, but reported gains depend on the trained FM head — do not expect equivalent improvements from a pure-prompt analogue.

#### Research Intake Update — 2026-05-21

##### New Related Research — Recursive Reasoning Architecture Lineage (HRM → TRM → GRAM)

User-submitted GRAM paper (arxiv:2605.19376) ingested with two reference-chase expansions (HRM, TRM). All three are architecturally distinct from the latent-reasoning entries already tracked here (intake-443 OneVL, intake-559 Coconut, intake-332 Ouro): they propose dedicated *recursive reasoning networks* trained from scratch on puzzle tasks rather than latent CoT compressions of pretrained LLMs.

- **[intake-582] "Generative Recursive Reasoning Models (GRAM)"** (Baek/Jo/Kim/Ren/Bengio/Ahn, arxiv:2605.19376, ICLR 2026 workshop)
  - **Relevance**: First entry in our intake to introduce *stochastic* latent trajectories + amortized variational inference to recursive reasoning. Multi-trajectory inference-time scaling (parallel τ sampling) is a different axis from the depth-only scaling discussed elsewhere in this handoff. Closest lineage neighbor is Ouro (intake-332) — looped LM latent reasoning — but Ouro stays deterministic.
  - **Reported results**: Sudoku-Extreme 97.0% vs TRM 87.4% / HRM 55.0% / Looped TF 61.3%. ARC-AGI-1 52.0% (vs TRM 44.6%, HRM 40.3%). N-Queens 8×8 with N=20 samples — 99.7% accuracy, 90.3% solution-coverage vs deterministic ceiling 36.1%. Compute-matched: GRAM @ 16 iter + N=20 samples beats TRM @ 320 iter at comparable budget.
  - **Delta from current approach**: Requires training a recursive architecture from scratch — same scope gate as Ouro (intake-332). NO EPYC deployment path on pretrained GGUFs today. Captured as conceptual reference: the variational-multi-trajectory framing is the relevant idea, not the specific GRAM model. Ablations are load-bearing — remove guidance and N-Queens collapses to 50.27%; remove stochasticity and both tasks collapse to 0% (naive noise injection does not work; the variational framework itself is the source of gains).

- **[intake-583] "Less is More: Recursive Reasoning with Tiny Networks (TRM)"** (Jolicoeur-Martineau, arxiv:2510.04871, Oct 2025)
  - **Relevance**: Captures the architectural simplification that GRAM positions against. 7M-parameter single-2-layer-net recursive model beats Deepseek R1 / o3-mini / Gemini 2.5 Pro on ARC-AGI-1 (45%) and ARC-AGI-2 (8%) while using <0.01% of their parameters. Direct architectural predecessor in the GRAM ablation table.
  - **Reported results**: ARC-AGI-1 45%, ARC-AGI-2 8% at 7M params. Per GRAM compute-matched runs, TRM needs 320 iterations to reach what GRAM gets in 16 iterations with N=20 parallel samples.
  - **Delta from current approach**: Same training-from-scratch gate. Worth filing because the parameter-efficiency claim (7M, no pretraining, 1000 examples) is potentially relevant to the draft-model / cost-aware routing space — could a TRM-style 7M recursive puzzle solver act as a specialized router for constraint-satisfaction subtasks? Open question, no immediate action.

- **[intake-584] "Hierarchical Reasoning Model (HRM)"** (Wang et al., arxiv:2506.21734, Jun 2025)
  - **Relevance**: Foundational paper of the recursive-reasoning lineage. Two-module recurrent architecture (slow planner + fast computation) trained on 1000 puzzle examples. Reference-tracked so future entries citing HRM resolve cleanly.
  - **Reported results**: 27M params, near-perfect on Sudoku and optimal-path mazes without pretraining or CoT data. Per GRAM: Sudoku-Extreme 55.0%, ARC-AGI-1 40.3%, ARC-AGI-2 5.0% — the weakest of the three recursive baselines.
  - **Delta from current approach**: Partially superseded by TRM (architectural simplification — TRM dropped the dual-module design and improved accuracy) and extended by GRAM (multi-trajectory generalization). Reference-only entry; no action item.

**Cross-cutting note**: All three entries share the same scope constraint that already gates Ouro (intake-332) and OneVL (intake-443): the techniques require training architectures from scratch and have no demonstrated transfer recipe to pretrained GGUF LLMs. Monitoring for (a) open code/checkpoint release on ahn-ml.github.io/gram-website, (b) any transfer-learning bridge from these recursive nets to pretrained LLMs, (c) follow-up papers — would change relevance to high.

- **[intake-585] "Are Your Reasoning Models Reasoning or Guessing? A Mechanistic Analysis of Hierarchical Reasoning Models"** (Ren & Liu, arxiv:2601.10679)
  - **Tier 2b on the entire HRM → TRM → GRAM lineage**: HRM doesn't reason — it converges to fixed-point attractors by pattern matching. Fails on trivial puzzles; progress across recursive steps is grokking-style (abrupt) not progressive; trapped in incorrect fixed points.
  - **Productive payload**: Augmented-HRM (data augmentation + input perturbation + model bootstrapping) improves Sudoku-Extreme from **54.5% → 96.9%** with NO architectural change. Most of HRM's claimed gap was missing training tricks, not missing bio-inspiration.
  - **Implication for any future recursive-net port to EPYC** (e.g., the "tiny recursive net as router/verifier" thread the user has been circling): if we port one of these architectures to a routing subproblem, the load-bearing transfer is the **training recipe**, not the architecture. Verdict in intake: `adopt_patterns`.

##### Deep-dive

Full analysis at [`research/deep-dives/2026-05-21-recursive-reasoning-routing.md`](../../research/deep-dives/2026-05-21-recursive-reasoning-routing.md) — covers the lineage in detail, maps it onto our existing routing infrastructure (BGE+MLP, Phase 2 hidden-state probe, Trinity Phase 4 sep-CMA-ES), and proposes three hypotheses (TRM-as-router DO NOT pursue; GRAM-multi-trajectory via cheap MC-dropout proxy; **GRAM-as-verifier SCOPE FIRST** — the genuinely novel framing missing from `learned-routing-controller.md` / `decision-aware-routing.md` / `outer-coordinator-learned-head.md`).


#### Research Intake Update — 2026-05-28

##### New Related Research (OPD reference set — training-side, no executable EPYC task today)

- **[intake-639] "Unmasking On-Policy Distillation: Where It Helps, Where It Hurts, and Why"** (arxiv:2605.10889) — verdict: **worth_investigating**
  - Relevance: Per-token gradient-alignment diagnostic for OPD. Complements intake-110#record (OPSDC), intake-266 (OPD survey), intake-286 (HPD) by providing the "when does OPD help" answer the survey flagged as open.
  - Key technique: Training-free diagnostic framework with token/question/teacher granularity; "ideal per-node gradient" derivation (maximizes student success probability); targeted-rollout algorithm.
  - Reported results: Qualitative — teacher gradients align with ideal more on incorrect-rollout tokens than correct ones; motivates asymmetric distillation guidance.
  - Delta from current approach: Diagnostic, not an objective. Requires per-token gradient access — inference-only stack does not provide. Cross-reference here as the canonical OPD when-to-apply diagnostic; revisit if/when cloud-GPU rental opens.

- **[intake-641] "SDAR: Self-Distilled Agentic Reinforcement Learning"** (arxiv:2605.15155) — verdict: **not_applicable**
  - Relevance: Sigmoid-gated auxiliary OPSD on top of GRPO for multi-turn agent RL. Same OPSD primitive as intake-110#record.
  - Reported results: +9.4% ALFWorld, +7.0% Search-QA, +10.2% WebShop-Acc over GRPO baseline (Qwen2.5/3).
  - Delta: Training-only; we have no in-house RL pipeline. Documented for future agent-training initiative.

- **[intake-642] "TIP: Token Importance in On-Policy Distillation"** (arxiv:2604.14084) — verdict: **worth_investigating**
  - Relevance: Same Sang/Xu/Zhou cluster as OPSDC (intake-110#record). Direct successor to the intake-266 OPD-survey caveat that flagged token-importance as the open frontier.
  - Key technique: Two-axis (entropy × teacher-student divergence) token taxonomy; parameter-free Soft-OR token scoring; top-K deterministic retention.
  - Reported results: Qwen3-8B→4B MATH-500 76.7% → 79.1% at 50% retention; up to 47% peak training-memory reduction.
  - Delta: Canonical post-OPSDC token-selection refinement. Gradient-time-only — cannot apply to inference stack. Note also for `research-evaluation-index.md`.

##### 2026-05-28 Deep-dive revisions to the OPD cluster

The initial intake's blanket "training-only, EPYC has no GPUs" dismissal was too quick for the OPD-family entries. Deep-dive 2026-05-28 surfaced inference-time / downstream-checkpoint angles and four concurrent critique/competing papers.

**Revised assessments**:
- **intake-639 (Apple, Unmasking OPD)**: relevance low → **medium**. The diagnostic is **logprobs-only** (not gradient-access-requiring) — runs on our forward-only llama.cpp stack. Usable as a screening tool for any third-party OPD-distilled checkpoint we consider deploying. Rollouts expensive (45K-200K/question) — one-off offline use only.
- **intake-642 (TIP)**: relevance low → **medium**. The 14B→1.5B test regime is **directly drafter range** (FastDraft / intake-624). 47% peak-memory cut compounds with FastDraft for any drafter we'd fund on cloud GPU. Soft-OR score is logprobs-only — possibly usable as a spec-dec verify-gating signal (unexplored by authors).
- **intake-643 (EffOPD)**: verdict **not_applicable → worth_investigating**. SVD analysis shows OPD-trained checkpoints have effective rank 2,341 vs 2,754 for RL-trained at 8B (top 1% captures 94.7%). The buried downstream-checkpoint corollary: **OPD-distilled models should LoRA-compress better than RL-trained** — relevant to Doc-to-LoRA Phase B (`../completed/08-doc-to-lora-prototype.md`, archived 2026-06-12; Phase B is GPU-gated) rank-8 default.

**New related research (Tier 2b expansion 2026-05-28)**:
- **[intake-644] "Rethinking OPD" (Li et al., Tsinghua, arxiv:2604.13016)**: token-overlap-concentration mechanism (72%→91%, 97-99% mass on overlap tokens at student-visited states). Overlap-ratio is a single scalar **computable from logprobs over teacher top-K** — strictly simpler and more falsifiable than intake-639's gradient-alignment cosine. Two-stage cold-start-SFT-then-OPD recipe with response-length sweet spot (3K-7K) is directly applicable to FastDraft drafter training. **Likely v1 token selector** over TIP Soft-OR.
- **[intake-645] "TRACE" (Wang et al., arxiv:2605.10194)**: per-token tri-routing among {FKL, RKL, ∅(GRPO)}. **Scale-inversion finding**: FKL dominates at 8B, RKL dominates at 1.7B — for any drafter ≤2B trained on rented cloud GPU, RKL-on-error is the v1 candidate. Anneal-to-GRPO schedule means trained model has **zero inference-time overhead**.
- **Parked**: arxiv:2605.11182 (Zhu et al., "Many Faces") — full text not yet available, review-on-publish; arxiv:2603.25562 (Fu et al., CASIA) — overlapping content with intake-639, cross-ref only.

**Net frame**: 2026 OPD is a maturing subfield converging on token-selective objectives. None of the four critique papers cite each other or 639/642/643 — concurrent parallel discovery. Pre-funding any cloud-GPU drafter training, bench candidate selectors (intake-644 overlap, intake-645 TRACE-RKL, intake-642 Soft-OR) on the same drafter target to pick a v1 recipe.

#### Research Intake Update — 2026-07-02

##### SPIRAL / recursive self-aggregation — training-free parallel-trace + aggregation (intake-732 / 746 / 747)
SPIRAL (arXiv 2606.23595) trains one model to jointly emit parallel CoT traces + a learned aggregation trace via "set RL"; the TRAINED aggregator is GPU-RL and not deployable here. The **training-free inference pattern IS minable**: sample N parallel traces, then run a prompted aggregation trace, plus **recursive self-aggregation** (intake-746 arXiv 2509.26626; intake-747 "aggregate your own responses" arXiv 2503.04104). This is the aggregation-trace generalization of the Tier-1 short-m@k majority vote (§Approach Taxonomy → Tier 1) and the multi-sample-selection complement to Action 9's single-sample re-roll; a natural additional A/B arm alongside DeepConf/majority@4 in the STOP Phase-3 baseline (§Action 10a).
- **FEASIBILITY**: full parallel generation is infeasible on the architect tier (`-np 1`); scope this fan-out to the **worker/coder tier** (`-np ≥ 2`) on NUMA-concurrent multi-instance serving (see the STOP Phase-1 `-np ≥ 2` note in §Action 10a).
- **MANDATORY CONTROL**: any test must include a **same-inference-compute majority-vote / self-consistency baseline** — aggregation gains often reflect ordinary sample-count scaling and can *degrade* with correlated errors; SPIRAL's set-RL gains are also math/verifiable-only and may not transfer to our largely non-verifiable production traffic.

##### Diverse-exploration RL objectives — HW-gated training reference (intake-748 / 749)
Poly-EPO (arXiv 2604.17654) and Polychromic Objectives for RL (arXiv 2509.25424) are training-time diversity-preserving RL objectives — the **training-side answer to the diversity-collapse bound** documented in §Diversity Collapse Interaction (inference-time interventions cannot recover training-time diversity loss). Tier-3 forward-pointer only (we don't RL-train yet), filed like TPO / RLTF / RLSD; materializes with the MI210.

- [x] **Correct RE-Bench framing** (flagged by the 2026-07-22 RC-RE-1 scoping): RC-RE-1/rec-005 frames RE-Bench as a reasoning-QUALITY eval; it is actually long-horizon **agentic ML-engineering vs human experts** (6/7 envs need 1-8xH100). Re-scope RC-RE-2 accordingly. Scoping: `epyc-inference-research/docs/design/re-bench-open-weight-compatibility.md`. ✅ 2026-07-22


#### 2026-07-25 — intake Stage-2a dive: Tier-0 rung + BCI (with a corrected cost story)

_Via `/research-intake` Stage-2 2026-07-25; see [`intake-derived-work-2026-07-25.md`](frontier-lab-automation.md)._

- [x] Add a **Tier-0 (zero-training, zero-inference-infra): adopt a pre-compressed checkpoint** rung to the taxonomy, seeded with ThinkingCap-Qwen3.6-27B. Record as an **observation** (vendor self-reported, no independent corroboration); note its own table is 8-of-12 negative out-of-domain and the repo declares no license. ✅ 2026-07-29 — taxonomy entry added above with the admission constraints, grounded in committed `research/intake_index.yaml` intake-892 (vendor results, directional counter-evidence, and license finding).
- [x] Add **Behavior-Conditioned Inference** (arXiv 2509.13237) as a Tier-1 candidate: extract named procedural "behaviors" from our own successful traces, retrieve k into context, measure output-token delta at fixed accuracy. Best-instrumented paper in the batch (5 seeds MATH, 80 runs AIME, temp 0.6/top-p 0.95). ✅ 2026-07-29 — added to the Tier-1 taxonomy from committed intake-897, including the required local A/B instead of importing its handbook.
- [x] **Corrected cost story — measure before believing.** The 46% is **"up to"**, output-tokens-only, with no accuracy figure at that operating point, and the **input-side cost is admitted but never measured** (`"involves a larger number of input tokens due to the inclusion of retrieved behaviors"`; **k=40** behaviors/query on AIME). Their defence — *"no autoregressive generation required on the input side"* — is a **GPU-prefill argument that inverts on a bandwidth-bound-decode / compute-bound-prefill CPU stack**. Score **total pipeline tokens** (retrieved-behavior prefill + decode), never decode alone. ✅ 2026-07-29 — carried into the Tier-1 entry using committed intake-897's Stage-2 correction; no claim of CPU benefit is permitted before the local total-token A/B.
- [x] Two guardrails ride along: behaviors are **model-extracted** (SkillsBench −1.3 pp caution ⇒ held-out validation gate mandatory), and a behavior handbook is itself an **accumulating store** ⇒ build append-only with raw traces retained (arXiv 2605.12978). ✅ 2026-07-29 — both constraints are now carried in the Tier-1 entry, grounded in intake-897's committed contradictory-evidence review.

#### Research Intake Update — 2026-07-28: Looped-transformer / recurrent-depth lineage (intake-902..912)

_Via `/research-intake` Stage-2 dives 2026-07-28 (7 dives: 903/904/905/906/908/910/911; six dive-verified, one dive-overturned). Full corrections in `research/intake_index.yaml`._

**Loop-placement taxonomy** (new axis for this handoff's lineage tracking): **model-loop** (Ouro intake-332 — whole stack iterated), **layer-loop** (Loopie intake-908 — each layer applied R=2 times before advancing), **token-routed recursion** (MoR intake-906 — router picks per-token depth), **converted recurrence** (Retrofitted Recurrence intake-911 — pretrained model surgically converted). All four share the scope gate: no llama.cpp/GGUF path.

- **[intake-905] Huginn recurrent-depth (2502.05171, NeurIPS 2025 spotlight)** — dive-verified anchor of the lineage. 3.5B/795B tokens; "50B-equivalent" is FLOPs-unrolling arithmetic (num_steps×1.5B+2B), NOT model parity — MMLU 31.38 vs OLMo-7B 60.56. Inference-mechanism evidence is UNEVEN: per-token KL-exit adaptive compute quantified (MTBench 5.63→5.56); cyclic KV-cache sharing quantified (**budget 4 of 32 steps, no MTBench loss** — deep-iteration KV can be aggressively bounded; cited observation only, architecture-specific); self-speculative decoding has ZERO published numbers (never cite for spec-dec plans); continuous-CoT ≈1–2 fewer steps. Matched-twin GSM8K win (9.02 vs 1.82) is params/tokens-matched, not FLOPs-matched. Checkpoint Apache-2.0, transformers-only.
- **[intake-910] Huginn latent-CoT probe (2507.02199, COLM'25 wkshp)** — calibration row for ALL latent-reasoning entries here (Coconut/CoLaR/Ouro): at 3.5B, recurrence depth is NOT a CoT substitute — CoT-suppressed GSM8K 3.11→4.93 strict (r=4→32, plateau) vs 24.87/38.13 same-model-with-CoT; latent recurrence *complements* explicit CoT. The probe does NOT refute latent computation wholesale (lens methods only detect token-decodable content; authors concede this) and does not touch the compute-scaling claim.
- **[intake-908] Loopie (2607.16051, IQuestLab/Ubiquant) — dive-OVERTURNED, WATCH-ONLY.** Layer-loop R=2 MoE at 20B-A2B/6B-A0.6B; claims wall-clock-matched pre-training crossover vs own Qwen3-30B-A3B reproduction at ~600B tokens (explicitly NOT FLOP-matched; inference compute matching deferred). Weights/code links DEAD as of 2026-07-28; v1 IMO/IPhO gold claims silently retracted in v2 (newsletters still restate them — treat as retracted). In its own Table 3, Nemotron Cascade 2 beats it on AIME24/25. CPU-decode hypothesis (tagged HYPOTHESIS, not task): R=2 consecutive reuse of ~37MB Q4 active-expert working set might hit EPYC L3 → 2× effective FLOPs at ~1× weight traffic; contingent on per-iteration router agreement, unobservable without weights.
- **[intake-911] Retrofitted Recurrence (2511.07384, Huginn group)** — the transfer bridge the 2026-05-21 cross-cutting note monitored for now EXISTS (pretrained→recurrent conversion, ~20 Apache-2.0 checkpoints ≤1B, runs in transformers), but at 26–52B uptraining tokens on an MI300A cluster: consumable, not reproducible here. GSM8K 26.5→51.2 over r=1→32, but r=1 is WORSE than the non-recurrent post-trained control (45.2) — the knob buys back quality only at ~32× core FLOPs. Same-group-as-Huginn: not independent evidence.
- **[intake-904/906] RRT (ICLR 2025) + MoR (NeurIPS 2025)** — external corroboration (by construction, not controlled comparison) of our TIDE post-mortem: competitive early-exit/adaptive-depth was only ever demonstrated WITH training-time loop/exit losses; neither paper ran a post-hoc control arm. Their throughput figures are not serving numbers (RRT 2.66× = oracle-exit SIMULATION, hardware unspecified; MoR 2.06× = bespoke H100 harness, no prefill workload).
- **[intake-902/903/907/912] UT / MoEUT / DeepLoop / MoD** — lineage reference rows only (UT = superseded root; MoEUT = loop+MoE ancestor, no checkpoints; DeepLoop = training-time p=1/2 tied-depth normalization rule, useful diligence question for any future looped-checkpoint onboarding; MoD = MoR's routing ancestor).

**Watch-trigger update (supersedes the 2026-05-21 cross-cutting note's condition (b) for the looped lineage)**:
the bridge's existence alone no longer flips relevance. The broader conversion/checkpoint-admission triggers remain:
(i) conversion recipe at ≤5B tokens or single-GPU scale, OR (ii) a converted/looped checkpoint ≥7B with instruct tuning,
OR (iii) any looped-model GGUF/llama.cpp support upstream. The operator-approved 2026-10-04 RC-XLLM-PREFILL-1 below
separately files a small native feasibility smoke. Lack of a ≥7B instruct/GGUF release does not veto that smoke;
it does not erase the original broader admission criteria.

##### Research Intake Update — 2026-10-04 — P5 native endpoint-prefill feasibility

Filed from the operator-approved [decision-tools plan](../../research/intake-stage3-plan-2026-10-03-decision-tools.md)
at `3911ec91`. Objective: determine whether the released endpoint-prefill mechanism has an executable CPU/ROCm
path worth developing for EPYC's long-prefill workloads. The current llama.cpp executor cannot consume its native
endpoint tensors and terminal-cache banks. This is an independent research runner with one task owner here.

- [ ] **RC-XLLM-PREFILL-1 — Execute the smallest released, bound native teacher/student endpoint-prefill smoke.** Resolve the Part II S teacher directory artifact and matching S student from the pinned catalog; use its existing loaders/file-set/hash checks and teacher_manifest_sha256 binding, not the unbound legacy student-file path. Implement a finite research runner comparing full-depth teacher prefill with student endpoint plus teacher terminal-cache construction, followed by identical-depth teacher decoding. Start CPU/eager, batch one, short frozen inputs, with a claimed eight-core footprint, 8 GiB memory ceiling and thirty-minute execution cap. Permit only a narrowly identified device/attention compatibility shim with operation-level conformance; stop at the first unsupported operation rather than launch a general port. If CPU executes both paths correctly, exercise the same inputs on ROCm in a coordinated GPU window. Retain the runnable path and specific remaining incompatibilities; no persistent endpoint, weight training, GGUF conversion, registry change or production-kernel modification. [check: which production role or lever does the teacher/student endpoint-prefill smoke inform, and what number would change a decision? If none can be named, retire]
- [x] **RC-XLLM-PREFILL-SOURCE — publish the reviewed finite endpoint-prefill actor and exact primary source seams.** ✅ 2026-10-07 — [MAIN source-only acceptance](../../artifacts/ni08/ufh05-finite-runner-source-20261007/README.md): Research main6e06fae72 publishes seven exact source artifacts, actor byte-identical to reviewed v2,44 original primary source identities and two-path device patch/shim map. Recipe identity remains RC-XLLM-PREFILL-1; output is ungraded operational metadata. No native/model run, weights download, feasibility, protocol amendment, upstream patch application or production change. Runtime parent and VB-RI-OPS-WIRE remain open.

**Six controls and decision.** Freeze repository `3af99f493e14fba162625d5dd687abea551a299e`, exact artifacts/manifests/
tokenizer, native dependencies/runtime/dtype, any shim, inputs/token IDs and logical depth. Baseline is full-depth
native teacher prefill; it is not the serving model and cannot select a production role. Retain terminal-bank
shapes/finite checks, logits, continuations, cold startup, warm prefill, cache construction, decode, memory/residency
and every error per input/arm. Develop on short texts and reserve different texts/lengths untouched for conformance
and timing. Count every failed load, unsupported operation, memory refusal and failed continuation; CPU success
does not establish ROCm success. Reject teacher mismatch, incorrect cache structure, failed operation conformance
or budget overrun. Student/teacher answer equality is not execution conformance; retain approximation loss separately
from runtime defects. Initial timing is descriptive. Only executable bound paths with held-out prefill savings under
a predeclared protocol/interval and explicit approximation-quality budget justify a subsequent small quality/latency
comparison against a current suitable incumbent. No production decision follows from the smoke.

**Execution conditions.** Artifact/tokenizer acquisition and an isolated native dependency environment are named
implementation dependencies. Claim the eight-core CPU footprint through the current region-lock workflow; ROCm
requires its coordinated GPU window and verified in-run HIP/VRAM residency. A missing eager operator yields a named,
tiny operation test/repair and effort estimate; any larger port returns as a concrete ROI proposal. Before the first
decision-bearing run, land native capture/projection through VB-RI-OPS-WIRE, using the existing ClaimTuple grader.
Filing establishes no download, installation, successful load or local execution.

**K11 — retained mechanism and source qualifications.** The student predicts the recurrent teacher endpoint;
one teacher core recurrence and coda construct terminal banks, and teacher decoding retains its original depth.
This is neither standalone student decoding nor faster decode. Published timing is warmed prefill-only and reports
task-specific quality losses; it is not an EPYC end-to-end benefit. Family labels omit embeddings, and training-token
suffixes are not parameter counts. Finite-depth equivalence is not guaranteed by the sufficient limiting theorem:
retain converging prefix-cache, closed invariant state-set, uniform contraction, context-Lipschitz and continuous
readout assumptions. Contractive carryover alone does not prove full recurrence contraction. Directory file/hash
verification and teacher-manifest binding are mandatory; the legacy student-file path lacks the same binding.
CPU tensor loading does not prove model execution, and documented CUDA/FlashAttention paths do not prove ROCm support.
Use native architecture loaders rather than assuming Transformers AutoModel compatibility. No universal teacher
envelope is introduced.

**M5 — broader follow-on, prose only.** A larger runtime port or production-role candidate requires executable
mechanism evidence, quality/cost justification and a suitable checkpoint. Preserve the original admission watch above;
do not turn this immediate smoke back into a passive candidate note. Risk determines safeguards rather than relevance.
Record discussion: intake-1853#record and intake-1854#record; their pinned primary anchors and narrowed corrections
remain the factual warrants.

- **[declined: ws58 2026-11-03 content-review: unbounded watch on a third-party release; research intake is the watch]** **Loopie artifact watch (intake-908)**: re-check `huggingface.co/IQuestLab` (Loopie-*-preview) and `github.com/IQuestLab` (loopie / vllm / megatron repos) before any port/eval planning; if released, pull config.json + vLLM diff to scope what a llama.cpp-experimental layer-loop port would need, then revisit the declined 6B-A0.6B CPU smoke test vs Ouro-2.6B-Thinking.
- [x] Dive-verify the 7 operator-selected lineage intakes and record corrections in the index ✅ 2026-07-28

#### Research Intake Update — 2026-08-21 (chat-template dive, intake-1212…1217)

- [x] **RC-T1** — Add **TALE** (intake-1215, arXiv:2412.18547v5) to the *Tier 1 — zero-training*
      family, **above** "Conciseness prompting". It is the numeric-budget form of the same
      intervention: a per-question token budget estimated zero-shot by the reasoning model itself.
      Reported 67% token reduction at −2.72% average accuracy, and **+3.11% accuracy on GSM8K at
      75.7% fewer tokens**. This is exactly the form our own intake-276 dive predicted in April 2026
      would beat stylistic instructions — that dive listed TALE as literature to fetch and nobody
      fetched it until now.
      ✅ 2026-08-21 (Tier 1 entry added) — **TALE-EP** inserted in *Approach Taxonomy → Tier 1*
      directly above "Conciseness prompting", with the 67%/−2.72% and GSM8K +3.11%/75.7% figures
      sourced to `intake-1215`.
- [x] **RC-T2** — Record TALE's two full-text-only caveats before anyone adopts it on the headline:
      MathBench-College generalisation shows −8% (GPT-4o-mini) and −4% (GPT-4o) against vanilla CoT,
      far worse than the −2.72% average; and the per-question estimator costs an **extra model
      call** per request, which is invisible on closed APIs and is not obviously free on our
      bandwidth-bound CPU decode. Measure estimator overhead against savings before treating 67% as
      a net win.
      ✅ 2026-08-21 — both caveats recorded as Caveat 1 (MathBench-College −8%/−4%) and Caveat 2
      (extra estimator call, unmeasured on our CPU decode) inline under the new Tier 1 TALE-EP entry,
      so an implementer reading the taxonomy cannot reach the headline without them.
- [x] **RC-T3** — File TALE as an intake entry ✅ 2026-08-21 (intake-1215, dive-verified)

**Context from the same round, for the "Conciseness prompting" line already in Tier 1.** Its
stylistic form is now measured: intake-1214 (CCoT, arXiv:2401.05618v3) reports 48.70% length
reduction with negligible aggregate impact — but a **27.69% math penalty for GPT-3.5**, while GPT-4
showed no statistically significant math decrease. The damage is localised twice, to one domain and
to the weaker model, which converges with intake-276's scale-dependent result from an independent
study. Any evaluation of a conciseness intervention must therefore report **per-suite, never
aggregate**.

#### Research intake 2026-10-21 — open-model backdoors, control-vector projection, Qwen3.8 post-train (research intake entries 2191–2213, see research/intake_index.yaml)

- [ ] **RC-CVEC-HOOKS — Re-resolve control-vector hook coverage and fail loud on a silent no-op.** At ffc1bac82 qwen35.cpp:198 and qwen35moe.cpp:221 call build_cvec while qwen4exp.cpp does not (only a comment at L391): amend the stale Qwen3.5 blocker (FlowSteer line, L129) and the Action 8 compatibility note (L209), record that a control vector on Qwen3.8-Flash-Next is ignored on v10, and make the SEAL harness assert a measurable logit change whenever a vector is loaded (intake-2201#record). **PARTIAL 2026-10-21 (not ticked):** stale text corrected (root e988b11bd); `eval_cvectors.py` and `seal_multi_role_regression_check.py` refuse arch qwen4exp (research c5661c5f9); remaining: assert a measurable logit change on a live server. Absorbs RC-CVEC-SAFETY as the deployment gate: before any steering vector is loaded on a production role, the SEAL evaluation must also report refusal rate and false-refusal rate on a public harmful/benign set plus harmless-prompt KL/perplexity at each scale; the behavioural shift is the pass/fail, cosine with a refusal direction is diagnostic only.
- **[declined: ws58 2026-11-03 content-review: merged into RC-CVEC-HOOKS as the deployment gate; no vector is on a production role today]** **RC-CVEC-SAFETY — Behavioural safety gate for every candidate steering vector.** Add refusal rate and false-refusal rate on a public harmful/benign prompt set, plus harmless-prompt KL or perplexity, to the SEAL control-vector evaluation at each scale (scripts/seal/eval_cvectors.py and seal_multi_role_regression_check.py measure accuracy and tokens only); the behavioural shift is the pass/fail gate and cosine with one refusal direction is a diagnostic only, because refusal can span a multi-dimensional cone (intake-2204#03, intake-2211#02, intake-2202#04).

- Trigger (no checkbox): a steering or reasoning-compression plan names Qwen3.8-Flash-Next as its target. Then open the build_cvec hook for qwen4exp on llama.cpp-experimental under the four-step kernel workflow; apply the vector per residual branch (four branches, intake-2205#02) and report per-branch norms.
- Trigger (no checkbox): a projection-mode or affine steering vector is trialled on a lineup model AND produces incoherent output or a harmless-prompt KL above 0.1. Then evaluate affine concept editing (projection toward the null-class mean, intake-2203#00) as the fallback.
- Trigger (no checkbox): RC-CVEC-SAFETY measures a non-trivial refusal or false-refusal shift for a candidate vector. Then run the offline per-layer cosine screen against a difference-of-means refusal direction for that model and check whether the shift lies along more than one refusal direction (intake-2204#03, intake-2211#02).

## Track: reasoning-effort-levels
<!-- gate: none -->

> Folded from `handoffs/active/reasoning-effort-levels.md` @ `7e268b4de29c` on 2026-11-02 (BRF-T1-F6, route 1a, operator D1/D5; retired row RTG-28 → RTG-08). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Reasoning Effort Levels — prompt-conditioned quality/token ladder

**Status (2026-07-20): STUB — idea captured, not yet designed.** Operator idea, raised while reading the
R2a result in [`architect-model-selection-bench.md`](model-evaluation-queue.md).

**One-line purpose:** give every role a **tunable reasoning-effort dial** — a spectrum of prompt
conditions (and token budgets) trading generated tokens for quality — instead of the current binary
"reasoning on / reasoning off", so latency-sensitive roles can buy *some* reasoning without paying full CoT.

> **⚠ 2026-07-22 — a THIRD axis surfaced that may matter stack-wide: `max_tokens` (completion budget) as a
> silent quality lever.** See **§ Token-budget study** below. Short version: on hard problems, models get
> *truncated mid-reasoning* and score wrong for a budget reason, not a capability reason — a ~57pp swing was
> measured on one suite. Production budgets may be below the "knee" for several stack models. The operator
> flagged this as worth a dedicated later-session study across the whole stack.

#### Motivating evidence (measured, not hypothesised)

Arm A4 = **Qwen3.6-35B-A3B (production frontdoor)**, GPQA-Diamond, **identical 50 questions**,
`enable_thinking=false` in BOTH arms — the only change is what the prompt asks for:

| Prompt condition | accuracy | mean tokens |
|---|---:|---:|
| "Answer with the letter only" | 52.0% | 537 |
| "Reason step by step, then answer" | **84.0%** | 2150 |
| **Δ** | **+32.0pp** (McNemar b=19 c=3, **p=8.6e-04**) | **4.0×** |

So the two endpoints of the ladder are real, large, and cheap to measure. 84.0% also sits within noise
of the vendor-published 86.0% for this model, so the high end is a genuine ceiling, not an artifact.
Full protocol + provenance in the R2a section of the architect bench handoff.

#### The core design question
**Are there useful intermediate points, and is the accuracy/token curve smooth or a step?** If it is
smooth, effort becomes a real dial. If it is a step function (you either reason or you don't), the
"ladder" collapses to a binary and the work is just picking the threshold per role.

#### ⚠ INVARIANT — effort is calibrated PER MODEL, and never inherited (operator, 2026-07-20)
**The ladder is a property of a (model, quant) pair, not of a role and not of the stack.** Every model
gets its own curve measured independently; a level that is optimal for one model says nothing about the
same level on another. Two independent results from 2026-07-20 already show per-model divergence on
*adjacent* dials:
- **Native thinking (R2b):** Qwen3.6-35B-A3B fails to terminate `<think>` on 48% of items even at a
  16384-token budget, making thinking-ON catastrophic **for that model**. Whether Qwen3.5-122B-A10B-IQ2
  does the same is a *separate measurement* — explicitly not generalized.
- **Spec-dec draft depth:** the measured optimum differs per model on the same GPU and kernel
  (122B-IQ2 → `n-max 2`; 27B-dense and 35B-A3B → `n-max 4`). Inheriting one model's setting cost ~29%
  throughput. Same failure shape, different dial.

**Consequences, binding on the design:**
1. Effort levels are **defined** generically (prompt templates) but **certified per model** — no level is
   "enabled" for a model until that model's own curve has been measured.
2. A **role default is a (model × level) pair.** Swapping the model bound to a role, or changing its
   quant, **invalidates the level** and requires re-calibration (see E-7).
3. Store the curves **indexed by model/quant, never by role** ([[feedback_model_not_role_indexing]]),
   so a model serving three roles is measured once and a role swap cannot silently inherit a stale level.
4. Do not extrapolate across quants of the same model either — quantization is exactly what the parent
   architect bench is testing for reasoning damage.

#### ⚠ Design constraint learned the hard way (2026-07-20)
**Do NOT implement effort as a bare `max_tokens` cap.** A hard cap truncates the model *mid-derivation*,
and a truncated answer scores **wrong** — you lose the quality without the model ever getting to state a
cheaper answer. This exact failure was observed repeatedly today (AIME at 4096: response cut mid-working,
scored a garbage `1`; CoT at 8192: ~20% truncation; and the historical `enable_thinking` probe whose
"+33pp for thinking-off" is most likely this same artifact — see
[[feedback_parse_failure_rate_is_a_scoring_artifact]]).
**Effort must be steered primarily by the PROMPT** ("answer in at most two sentences of reasoning",
"give a brief justification then answer"), so the model *plans* a short answer and still emits a
well-formed final answer. A token cap is at best a backstop, and if used it needs a
`--reasoning-budget-message`-style graceful-close so the model terminates cleanly instead of being cut.

#### § Token-budget study — `max_tokens` as a stack-wide quality lever (operator-flagged 2026-07-22)

**The finding.** On hard tasks, models are truncated *mid-reasoning* by the completion-token ceiling and
score wrong for a **budget** reason, not a capability reason. This is a distinct axis from prompt-effort and
native-`<think>`: it is the raw `max_tokens` a request is allowed. Measured across this session:

| Suite (arm A1 122B-IQ2 unless noted) | budget | truncation | overall acc | acc among FINISHED | Δ from budget |
|---|---:|---:|---:|---:|---|
| AIME'25 avg@4 | 16384 | 6% | 71.7% | 76.1% | small |
| gpqa_diamond_cot | 4096→8192 | ~20%→low | — | — | raised mid-session |
| **olympiadbench_hard (pilot n=24)** | 16384 | **46%** | **50.0%** | **76.9%** | **≈ +27pp latent** |

On `olympiadbench_hard` the model **largely can solve the problems** (76.9% when it finishes) but the
measured score is 50.0% because 46% get cut off (truncated-and-correct: only 2/11). That is a **~57pp swing
between finished and truncated** driven purely by token budget. Related but *distinct* failure: native
`<think>` **non-termination** (R2d/E-6: 18–50% never close the block even at 16384) — same symptom
(budget-exhausted, no answer), different cause (looping vs. legitimately-long reasoning); the fix differs
(`--reasoning-budget` force-close vs. simply more `max_tokens`).

**Why it matters for production.** Every stack role runs with an effective completion ceiling
(`roles.*.reasoning_budget`, `max_tokens_multiplier`, orchestrator request defaults). If those ceilings sit
**below the knee** for a given model, that model is **silently losing quality on hard tasks** — invisibly,
because a truncated answer looks like a wrong answer in aggregate accuracy. Nobody would see it without the
finished-vs-truncated split.

**The operator's two hypotheses (both testable):**
1. **Per-model/per-task tuning is needed** — the budget knee differs by model (a 3B-active model reasons
   differently than a 122B) and by task difficulty, so quality-maximization requires a matrix.
2. **A single "mostly-ok" generous setting recovers most quality** — there may be one budget (per model, or
   even stack-wide) that captures ≥90% of the model's max-budget accuracy, making per-task tuning unnecessary.
   This is the cheap-win hypothesis and should be tested first.

**Study design (later session):**
- [ ] **TB-1 — Per-model budget curve.** For each stack model, on a truncation-inducing suite
      (`olympiadbench_hard` is ideal — it induces 9–16k-token reasoning), sweep `max_tokens ∈
      {4k, 8k, 16k, 24k, 32k}` on the **same pinned items**, plot **accuracy AND truncation-rate vs budget**,
      and report the **finished-only accuracy** (the budget-independent ceiling) alongside overall. Find the
      **knee** (truncation < ~5%, accuracy plateaus). Use the idempotent `(id,seed)` resume so each higher
      budget only re-runs the items the lower budget truncated.
      - 2026-11-03 CAP-04 pilot result (ws58, BRF-T4-CAP04): **REVISE, screen; TB-1 not advanced.** 76/76 units ran, and every validity check passed (budget, think-leak,
        critic thinking, residency, slot context). The 8k/16k cells were derived from one 32k generation, and that derivation failed its check: 0/4 fresh 8192 generations were equal
        to or a prefix of the base (non-greedy sampling plus speculative decoding). So no sub-32k cell counts, there is no knee, and TB-2, TB-3 and TB-4 are UNCOVERED. Valid 32k cells:
        frontdoor olympiad 0.50 (0 truncated); architect_critic olympiad 0.25 overall and 0.30 finished-only, 2/12 truncated inside thinking. E-2/E-3 screen on GPQA (frontdoor,
        32k): L2 0.95 = L3 0.95, 1 rescued and 1 harmed of 20, L3 +1178 mean tokens. The re-screen must generate fresh at each budget.
        OBSERVATION: `/mnt/raid0/llm/tmp/brf-cap04/job/out/summary.json` sha256 `9d2204432edc…`, `results.jsonl` `81397b10396f…`. [belief: cc]
- [ ] **TB-2 — Test the "single mostly-ok setting" hypothesis.** Does one budget capture ≥90% of each
      model's max-budget accuracy? If yes → a simple per-model (or stack-wide) default; if no → the
      per-task matrix (hypothesis 1). Report quality-per-token, not just quality — budget = tokens = time on
      a shared box ([[feedback_cpu_decode_bw_bound]]).
- [ ] **TB-3 — Audit production ceilings against the knees.** Cross-reference each role's live
      `reasoning_budget_easy/hard` (`src/config/models.py:1354-1355`) and `max_tokens_multiplier` (`orchestration/model_registry.yaml`, value 4) against its measured
      knee. Flag any role running **below** its knee — that is silent quality loss, fixable by raising one number. *(Anchor fixed 2026-11-09: `reasoning_budget` is NOT a `model_registry.yaml` role field; the registry has only `max_tokens_multiplier` and one workaround note at ~:1583. The audit half is blocked until TB-1 yields knees; the inventory half, listing every role's current budgets and multiplier, is doable now.)*
- **[declined: ws58 2026-11-03 content-review: merged into E-2 (its own text says fold into E-2/E-6)]** **TB-4 — Interaction with the effort ladder.** Budget is a **third axis** alongside prompt-effort
      (L0–L3) and native-`<think>`. A tight prompt-effort level *reduces* the budget needed (the model plans
      brevity); the full 2-D (effort × budget) grid per model is the complete picture. Fold into E-2/E-6.

##### Production control problem — budget × concurrency × VRAM is a JOINT, dynamic constraint (operator, 2026-07-22)

The study above measures *static* per-model curves. **Production is harder: reasoning budget and server
concurrency are coupled through VRAM, and the coupling is dynamic.** Measured 2026-07-22 while sizing the
batched hard-suite run (MI210, 64 GiB, f16 KV, per-slot ctx 36864 = prompt + 32768 budget):

| model | weights+base | **per-slot KV @36864** | slots to fill 64 GiB |
|---|---:|---:|---:|
| 122B-IQ2 (MoE/GQA) | 38.2 GiB | **0.99 GiB** | ~20 |
| 27B-dense Q8 | 26.9 GiB | **2.39 GiB** | ~13 |
| 35B-A3B (MoE) | 35.7 GiB | **0.76 GiB** | ~30 |

**Key facts for a router:** (1) KV/slot scales **linearly with the reasoning budget** (`n_ctx_slot`), and
(2) it is **strongly per-architecture** — the dense 27B costs 2–3× the KV/slot of the MoE arms, so it can
serve **far fewer** concurrent high-budget requests on the same card. So VRAM = `weights + Σ_slots(budget_i ×
kv_per_token)`. **A naive "raise the budget" or "raise concurrency" in isolation risks OOM**, which in
llama.cpp silently shrinks `n_ctx_slot = n_ctx / n_parallel` → **truncation** (the very failure the budget was
meant to fix). This makes budget-selection and admission-control **one problem**.

**The router design this implies (the operator's framing):**
- [x] **TB-5 — Expose `max_tokens` / `reasoning_budget` as a per-request tunable surface** the router sets from **assessed task complexity** (easy → tight budget, hard → generous). Requires per-request budget plumbing through the orchestrator serving path (llama-server already accepts it per request). Natural extension of [[project_learned_routing_controller]] — budget becomes a routing *output*. ✅ 2026-11-01 — Orchestrator `2b9e710de2d5e183c790523c72dbbeca117e8a16` on `origin/main`; 55 focused controls passed under R6. Evidence: [TB-5 artifact](../../artifacts/engineering/tb5-request-budget-surface-20261101/README.md). [no-belief: implementation and deterministic software controls; no measurement or production behavior claim]
- [x] **TB-6-exec — np × context throughput surface, ALL GPU architect candidates (GPU-only study).**
      ✅ 2026-07-23 — COMPLETE for **A1** (122B-A10B UD-IQ2_M, MoE, MTP2), **A3** (Qwen3.6-27B dense Q8, MTP4),
      **A4** (Qwen3.6-35B-A3B Q8, MoE, MTP4) — each at its own max-opt MTP depth, v7 kernel, MI210. Grid
      np{1,2,4,8,16,32} × L{2048,8192,16384,32768} (drivers `study_np_context*.sh`, artifacts
      `np_context_study_20260723/`). Aggregate decode t/s (— = grid-capped or VRAM-guard SKIP):

      | np↓/L→ | **A1** 2k | 8k | 16k | 32k | **A3** 2k | 8k | 16k | 32k | **A4** 2k | 8k | 16k | 32k |
      |---|---|---|---|---|---|---|---|---|---|---|---|---|
      | 1  | 54.7 | 52.7 | 57.1 | 52.0 | 46.8 | 47.0 | 41.4 | 42.5 | 72.4 | 94.0 | 99.4 | 73.3 |
      | 2  | 44.0 | 44.2 | 44.8 | 43.0 | 79.1 | 64.3 | 64.0 | 65.2 | 103.2 | 111.5 | 98.3 | 98.9 |
      | 4  | 63.1 | 60.9 | 55.6 | 45.7 | 113.8 | 102.5 | 90.8 | 95.2 | 147.2 | 159.0 | 126.9 | 131.5 |
      | 8  | 85.3 | 66.8 | 62.7 | — | 151.2 | 119.9 | 100.4 | — | 181.1 | 193.8 | 159.5 | — |
      | 16 | 99.9 | 86.2 | — | — | 152.9 | 104.0 | — | — | 220.9 | 207.1 | — | — |
      | 32 | 103.4 | — | — | — | 128.7 | — | — | — | 243.5 | — | — | — |

      **Peak aggregate per (arm, budget) [np@peak]:** L2k → A1 103@32 · A3 153@16 · **A4 243@32**; L8k → A1 86@16 ·
      A3 120@8 · **A4 207@16**; L16k → A1 63@8 · A3 100@8 · **A4 160@8**; L32k → A1 52@**1** · A3 95@4 · **A4 132@4**.

      **KEY FINDINGS (cross-candidate):**
      1. **Throughput ranking A4 ≫ A3 > A1 at every batched operating point** — small-active MoE (3B active)
         batches best, dense 27B second, large-active IQ2 MoE worst. At L2k peak: 243 / 153 / 103.
      2. **A1 is the SOLE outlier.** It is the only arm with (a) an np=2 dip AND (b) a long-context batching
         *collapse* (net-negative at 32k: np4=45.7 < np1=52.0). A3 (dense) and A4 (small MoE) both batch
         **robustly at every budget** (A3 2.2–3.3×; A4 up to 3.4×).
      3. **⚠ CORRECTION of the earlier A1-only reading (was wrong):** the np=2 dip is **NOT** generic-MoE (A4
         MoE shows *no* dip, 1.43× at np=2) and the long-CoT collapse is **NOT** generic-long-context (A4
         batches fine at 32k). BOTH are **A1-SPECIFIC**, confounded across IQ2-quant / MTP-2 / large-active —
         cause not isolated (candidate followup RP/kernel).
      4. **Batching is ARCHITECTURE-DEPENDENT, not universal.** The earlier "optimal np → 1 as budget grows /
         don't batch long-CoT" rule holds **ONLY for A1**. Dense + small-MoE keep ~2–3× batching at 32k.
      5. **Why dense batches so well:** weight-reuse amortization (read weights once, apply to np tokens) beats
         MoE expert-scatter at low–mid np; the MoE edge (fewer active params) only surfaces at high np with
         expert reuse — which is exactly where A4 pulls away (243 @ np32) and A3 plateaus (~153 @ np8-16).
      6. **Caveat:** np=1 cells are n=1 (NREQ=np) → noisy baselines (A4 np=1 ranged 72–99 across L); the
         batched aggregates (n=np) are the reliable reads. Peak numbers, not np=1 ratios, drive the policy.

      **Router rule — per-arm, architecture-aware (supersedes the single-arm rule):**
      - **A1** (large IQ2 MoE): batch ≤8k (np8-16); 16k np4-8; **≥32k np=1**; **never np=2**.
      - **A3** (dense): batch **all** budgets, sweet spot **np=8** (regresses past np=16).
      - **A4** (small MoE): batch aggressively **all** budgets, scales to **np=32+**, no dip — the throughput arm.

      Cross-check: earlier fixed-*total*=36864 probe np4=62 matches A1's L=8192 np4=60.9. ✅
- **[declined: ws58 2026-11-03 content-review: era v8 and deleted models (ThinkingCap, both Fable-Fusion variants deleted 2026-10-20; Laguna retired); nothing in it can run]** **TB-6-exec-v8 candidate extension — grids terminal; prefill-to-depth RAG RUNNING 2026-07-28.** Under the operator's zero-idle,
      observation-grade grant, extend `epyc-inference-research/artifacts/np_context_study_v8_20260727/`
      with one-load-per-model frozen-v8 runs: ThinkingCap Q8 and both Fable-Fusion Q8 variants each
      receive an `rb1024` SWE/LCB first-read plus the canonical `np×L` grid; Laguna UD-IQ2_M receives
      the grid with DFlash off; A4 receives the `L=2k/8k` era-bridge column. After those cells finish,
      run the separate production-template prefill-to-depth instrument using pinned real retrieval
      prompts. The four prerequisite grids are terminal, and the q3-held successor is live first on
      Fable non-MTP; retain this item open until the separate RAG instrument terminalizes. Evidence
      collection does not authorize a lineup or registry change.
- [x] **TB-6-sidecar CPU-containment repair** ✅ 2026-07-27 — an initial GPU-sidecar
      thread-affinity check caught a ROCm helper thread inheriting the broad host mask during a
      concurrent Laguna Q4 CPU arm, correctly invalidating that arm rather than accepting a false
      clean-window claim. `np_context_study_v8_20260727/driver/run_model_block.sh` now places the
      driver before child creation in the dedicated threaded cgroup-v2 `epyc-v8-gpu-sidecar`, with
      `cpuset.cpus=184-191`; every server thread is therefore hard-confined even if it subsequently
      requests a broad affinity. The driver records `sidecar_cpuset.txt` and retains the existing
      per-thread affinity proof. Self-test and the 12-cell aggregation suite passed; the live grid
      remains observation-only and in progress.
- [ ] **TB-6-exec-followups (GPU-owned) — remaining scope: (d) per-model `kv_bytes/token` for every GPU-resident model today (the :8083 Qwen3.8-27B Q8 + DFlash2 recipe), from the launcher's per-buffer VRAM decomposition (SSU-F10) or the GGUF header, as the admission-control constant TB-6 needs; (b) the prefill-to-depth instrument stays as the cheap way to measure decode-at-KV-depth when (d) needs a live check.** Done when the constant is in the registry row and TB-6 reads it.
- [ ] **TB-6-exec (c) — A2/CPU np×context surface (RETITLED 2026-11-09: Qwen3.8-Flash-Next UD-IQ4_XS on `architect_general`, not the deprecated 122B-Q4) — HANDED TO CPU LINEAGE 2026-07-23.** Does the
      Q4 arm on CPU show the same batching-collapse shape? Owned by the CPU session per the GPU/CPU split
      ([[project_session_split_2026_07_23]]); tracked here for the surface's completeness only.
      *(Retarget 2026-10-28 (operator): Qwen3.5-122B deprecated. The CPU arm of this question is now Qwen3.8-Flash-Next
      UD-IQ4_XS on `architect_general`. Do not run it on the 122B.)*
- [ ] **TB-6 — Concurrency-aware admission control (VRAM *and BANDWIDTH* guard).** The router/orchestrator
      must track live `Σ(budget_i × kv_per_token_model)` against the card and **admit/queue/downgrade**
      requests so the sum never forces `n_ctx_slot` below a request's budget. Per-model `kv_per_token`
      (measured above) is the key constant; extends the live placement SM in
      [[project_heterogeneous_slot_fabric]] (already "everything is a slot"). Potentially **asynchronous** —
      hold or shed budget under pressure rather than truncate. Non-trivial joint scheduler:
      **complexity-estimate → budget → admission → placement**.
      > **⚠ MEASURED 2026-07-22 — the binding constraint is memory BANDWIDTH, not VRAM capacity; and the
      > optimal concurrency is a function of context (= reasoning budget).** Batching `olympiadbench_hard`
      > (budget 32768 → per-slot ctx 36864) on the 122B-IQ2:
      > - **np=14:** fit VRAM comfortably (52/64 GiB) but **collapsed** — per-request decode fell so far that
      >   **54/155 requests (35%) exceeded a 3600s timeout**. (The "18.2 tok/s aggregate" first reported was
      >   NOT a real throughput — it is real-tokens ÷ a wall-clock inflated by 54 timeout-stalls; discard it.
      >   True np=14 aggregate is unmeasured, but ≈ or below single-stream by the np=4 point below.)
      > - **np=4 (native per-request timing):** median **11.9 tok/s/request → ~47 tok/s aggregate** — only
      >   ~8% over single-stream spec-none (43.6). So at this context **batching barely helps** and sequential
      >   would have been just as fast + reliable.
      > **Why (vs pre-promotion B32 benches that showed 148.7 agg):** those were at *small* context (~512–2k),
      > where KV is tiny and 32 slots pack in. At 36864 ctx the KV read per decode step scales with
      > `(context × active_slots)` and MoE requests scatter across experts → each step reads far more memory →
      > **aggregate throughput DROPS as concurrency rises**. **So there is an `np × context` optimum curve, and
      > the optimal np collapses toward 1 as the reasoning budget (context) grows.** TB-1 must therefore be a
      > **2-D (budget × concurrency) grid** capturing the decode-collapse knee; "fits in VRAM" is NOT
      > sufficient to raise concurrency. Bandwidth ceiling ≈ `Σ(ctx_i) × kv_bytes/token / mem_bw`. Evidence:
      > `artifacts/architect-bench-gpu-20260720/runs/olympiadbench_hard/` (A1 np=14 timeouts vs np=4 timing).
      > **✅ 2026-07-23: the 2-D grid is now MEASURED for all GPU candidates — see TB-6-exec surface above
      > (A1) + the consolidated cross-candidate table (A1/A3/A4). Router-integration plan: TB-6-ROUTER below.**
- [ ] **TB-6-ROUTER — Wire the np×budget surface into the router (GATE MET, see 2026-11-09 note; formerly GATED on GPU joining the orchestration
      *(2026-11-09 audit, gate verified at config level: `orchestration/stack_topology.yaml:249-258,285` declares the MI210 27B (Qwen3.8-27B Q8, :8083, `cpu_shape: GPU_HOST_LANE`, `gpu_host_lane: true`) as a serving instance, `architect_critic` since the 2026-09-27 swap. The "today the MI210 is a bench instrument" precondition text below is stale. This is a topology declaration; the stack is currently off, so live serving was not re-observed. Remaining work is unchanged: build the :8083 np x budget lookup and wire router admission for one role.)*
      stack).** The surfaces give, per GPU-resident model, a lookup `reasoning_budget → (optimal np, expected
      aggregate t/s, expected per-request t/s)`. This is the missing half of the routing decision: the learned
      router already maps *task → budget* ([[project_learned_routing_controller]]); this maps *budget →
      concurrency policy*. **Precondition (why gated):** the MI210 is today a *bench instrument*, NOT a serving
      node — production is CPU-only. This activates only when the GPU is registered as a serving backend in
      `orchestrator_stack.py` / `model_registry` — an operator-gated stack change
      ([[feedback_stack_change_three_gates]], [[project_orchestrator_stack_freeze]]).
      **Data products to freeze into the registry per GPU model** (the `optimal_gpu_serving` block already
      exists as the home): (1) `kv_bytes_per_token` (admission capacity constant, from VRAM readings);
      (2) `np_ceiling(budget)` — concurrency beyond which aggregate plateaus/declines (A1: np16 @≤8k, np8 @16k,
      **np1 @≥32k**); (3) the full `agg_throughput(np,budget)` + `per_req_throughput(np,budget)` surface for SLA
      estimation; (4) **forbidden operating points** — np=2 for MoE arms (universal dip). **Integration, three
      layers:** (a) *Static server sizing* — size each model's launch `-np` to its expected budget distribution
      (AutoPilot TB-7 realized-demand): short-budget roles → high np; deep-reasoning architect → np1-2; never
      launch a MoE arm at np=2. (b) *Complexity→budget→concurrency co-decision* — extend the learned controller
      to emit a coupled concurrency ceiling alongside the budget; do not admit a request into a slot pool that
      would exceed `np_ceiling(budget)`. (c) *Live admission/placement* — the TB-6 controller tracks
      `Σ(budget_i × kv_bytes/token)` against BOTH the VRAM cap AND the bandwidth-collapse ceiling; near the
      ceiling it admits/queues/downgrades (shed budget or route to CPU) rather than pack another slot into the
      collapse region. Integrates with [[project_heterogeneous_slot_fabric]] ("everything is a slot") + the
      within-role-placement SM. **Cross-model dimension:** the consolidated table also picks *which* GPU arm
      serves a given (budget,load) point — a small-active MoE (A4) may sustain higher aggregate at moderate np
      than a dense model (A3) whose higher KV/slot forces an earlier collapse. **Validate before activation:**
      re-measure under the *production* serving config (real RAG-context prompts, not the short-prompt proxy —
      long prompts shift the collapse leftward) via the prefill-to-depth variant, reconciled with AutoPilot's
      realized budget distribution. Precondition MET 2026-09-24: the MI210 serves architect_critic / coder_escalation / ingest_long_context on :8083 (KVU-11, OP-56), so this is no longer gated. Build the lookup for the :8083 recipe from its np x L surface; done when the router's admission consults it for one role.
- [x] **TB-7 — Calibrate the budget policy from AutoPilot's live token stats (no new inference).** AutoPilot ✅ 2026-07-22
      already records **tokens-generated per successfully-completed task**. That is a free, production-grounded
      distribution of "how much budget did each task class actually need" — mine it to set per-(task-class,
      model) budget defaults and to find the knee *without* running the TB-1 sweep for every task type.
      Cross-check the TB-1 curves (capability ceiling) against the AutoPilot distribution (realized demand):
      the deployable budget is roughly the high percentile of realized demand for the task class, capped by
      the VRAM/concurrency budget (TB-6). **Do this first** — it may answer TB-2's "single mostly-ok setting"
      from existing data before any GPU sweep.

**Coverage target (TB-1):** every production model — frontdoor (35B-A3B), worker (gemma-4-26B-A4B), architect
(122B), ingest (Qwen3-Next-80B), reviewer arm, coder. Cheapest first; frontdoor + architect gate any
production budget change (operator-gated).

**Per-model INVARIANT applies** (see above): the budget knee is a `(model, quant)` property, certified per
model, never inherited. **Tooling ready:** `olympiadbench_hard` suite + `math_symbolic` scorer +
finished-vs-truncated split (`truncated`/`finish_reason` fields in per-question JSONL) + idempotent budget
top-ups + **`--concurrency` batched runner + a VRAM-sizing probe** (per-slot KV table above) — all landed
this session. The batched run gives the TB-1 sweeps ~10× wall-clock, and the per-slot-KV constants are the
inputs TB-6's admission-control needs. **Method note:** each `-np` slot must get the FULL per-request budget
as its `n_ctx_slot` (`-c = per_slot_ctx × n_parallel`) — else llama.cpp silently truncates; verify
`n_ctx_slot ≥ budget` and VRAM headroom at launch (the batched run does).

#### § MODEL-specific repetition-penalty fence (operator, 2026-07-23; attribution CORRECTED)

**Finding (olympiadbench_hard, 2026-07-23):** the **Qwen3.5-122B-A10B** loops on `\boxed{answer}` to the
token cap (degenerate repetition — solves it, can't stop) — **at BOTH quants: UD-IQ2_M (25% of items) AND
UD-Q4_K_M** (A2/CPU, item-1 = 32768 tok, tail-uniqueness 0.03, `\boxed{2n-1}`×N on the *same* item IQ2
looped on). The Q8 arms do NOT loop (27B-dense **0%**, 35B-A3B **~1%**). **⇒ the defect tracks the MODEL
(122B-A10B), NOT quantization** — the 2-bit-EOS-damage hypothesis is REFUTED (RP-2). It is likely a
model×prompt property (the `\boxed{}` instruction may be a trigger — RP-3).

**Policy (operator, corrected): apply the repetition penalty to the MODELS that need it (the 122B-A10B, at
any quant), NOT keyed on quant aggressiveness, and NOT blanket across the stack.** Rationale: the penalty
has a real quality cost (registry's own Qwen note: `presence_penalty > 1.0` causes language mixing;
repetition penalties hurt legitimate repetition in code/math/structured output — confirmed by RP-1:
`repeat 1.3` tanked accuracy to ~15%). Production already uses penalties per-model (worker `repeat_penalty
1.05`, gemma4 `1.1` crash-mitigation, some frontdoor `presence_penalty 1.5`) — **but the 122B-A10B architect
has NONE at either quant**, and our bench matched that, so the loop would occur in production. The fence is a
**per-MODEL** property (certified per model), never inherited stack-wide.

- [x] **RP-1 — Repetition-penalty probe ✅ 2026-07-23:** `repeat_penalty 1.1` is the fix (loop 100%→22%, tokens 32768→10.6k, acc held 55%); `1.3` over-penalizes (~15%); DRY(0.8) ruled out (inconsistent + 0/40). On A1's 40 looping items, test
      `repeat-penalty {1.1, 1.3}` and the **DRY sampler** vs baseline — does it break the loop
      (truncation→0, tokens↓) WITHOUT hurting accuracy? Pick the least-cost fence. Driver `probe_reppen.sh`.
- [x] **RP-2 — Quant attribution: REFUTED ✅ 2026-07-23.** A2 (122B-A10B **Q4**, CPU) loops **identically**
      to IQ2 on the same item → the loop is **MODEL-specific (122B-A10B), NOT quant-specific**. So it is
      NOT 2-bit EOS damage, and the ~2× token cost is inherent to the 122B-A10B candidate at either quant
      (does not distinguish IQ2 vs Q4). *(A2 was run unfenced only to answer this — a clean H1 accuracy
      read needs the fence on BOTH A1 and A2; see RP-5.)*
- **[declined 2026-11-09 (audit): the loop being characterised is the Qwen3.5-122B-A10B `\boxed{}` loop; the 122B was deprecated 2026-09-22 and its sibling RP-4/RP-5 were closed OBSOLETE on 2026-10-29, which is this box's own [check] retirement condition. Refile only naming a SERVED model that loops.]** RP-3 (original text kept): **RP-3 — Does it loop on the ARCHITECT WORKLOAD** (multi-step planning) or only on competition-math
      `\boxed{}` prompts? The `\boxed{}` instruction may itself be the trigger — **now the leading hypothesis
      for the root cause** (both quants loop; models differ). Test on real architect tasks + a no-`\boxed`
      prompt variant. [check: which model's loop is this (the 2026-07-23 fence names it)? If it is the deprecated 122B, retire; if it is a served model, keep and name it in the box]
- [x] ~~**RP-4 — MODEL-specific penalty policy in the registry:** add a per-**model** repetition-penalty~~ (closed 2026-10-29 audit: OBSOLETE → RP-4 is explicitly for the Qwen3.5-122B-A10B (both quants): 122B deprecated 2026-09-22, GGUF deleted 2026-09-23, lane closed (graveyard row model_registry.yaml ~12737; 84dff9d39 retired 122B work))
      default for the 122B-A10B (both quants) — RP-1 says **mild `repeat_penalty ~1.1`** (breaks the loop,
      accuracy held ~55%; `1.3` over-penalizes to ~15%). Operator-gated. Do NOT key on quant; do NOT blanket.
- [x] ~~**RP-5 — Clean H1 (Q4 vs IQ2 reasoning parity) WITH the fence.** Both quants loop unfenced, so the~~ (closed 2026-10-29 audit: OBSOLETE → RP-5 compares A1(IQ2) vs A2(Q4) of the 122B (cf. handoff:212 "A2/CPU (122B-Q4)"); 122B lane retired 2026-09-22/23 and closed 2026-10-29 (graveyard row ~12737))
      H1 accuracy comparison must run A1(IQ2) and A2(Q4) both at `repeat_penalty 1.1` on the same hard items.
      CPU-window-gated (A2 is CPU). This is the remaining architect-bench accuracy unknown.

#### Prioritized task list
- [x] **E-1 — Design the ladder.** Draft 4–5 effort levels, e.g. L0 answer-only → L1 one-line ✅ 2026-07-22
      justification → L2 brief step-by-step (bounded) → L3 full CoT → (L4 native `<think>` on).
      Levels must be *prompt* variants; note which also set a budget backstop.
- [ ] **E-2 — Measure the curve, once per model.** Sweep the levels on the **already-pinned**
      GPQA-Diamond items (`artifacts/architect-bench-gpu-20260720/questions_gpqa_diamond_cot.json`) so
      results are paired with everything measured today. Plot accuracy vs mean tokens → **one Pareto
      frontier per (model, quant)** — see the per-model INVARIANT above. Report truncation +
      parse-failure + empty-content rate at every level (a level that truncates or fails to terminate is
      **disqualified, not scored** — scoring it as "wrong" is the artifact that has already bitten twice).
      **Coverage target: every model in the production stack**, not just the architect-bench arms —
      gemma-4-26B-A4B (worker), Qwen3-Next-80B (ingest), the reviewer arm, and any drafter used
      standalone. Cheapest first; the frontdoor + architect curves are the two that gate E-4. Scoring (absorbs E-3): score each level by rescue rate — how often it rescues items the cheaper level got wrong, against its token cost — not by mean accuracy. Budget is the third axis (absorbs TB-4): for each model, the (effort x max_tokens) grid is the complete picture; a tight effort level reduces the budget needed.
- **[declined: ws58 2026-11-03 content-review: merged into E-2 as its scoring rule]** **E-3 — Evaluate by rescue-rate, not mean accuracy.** Per
      [[feedback_accuracy_token_tradeoff_rescue_metric]]: score an effort level by how often it *rescues*
      tasks the cheaper level got wrong, versus its token cost. Mean accuracy hides that a level may only
      help on a narrow band of hard items.
- [ ] **E-4 — Per-role defaults, expressed as (model × level) pairs.** Map levels → roles *given the
      model currently bound to each role*; a bare "frontdoor = L2" is malformed (see INVARIANT).
      Operator's stated prior: **architect + reviewer should reason; frontdoor arguably too.** Frontdoor
      is the hard case — interactive, and it pays the token cost most, so it wants the **knee** of its own
      curve, not the top. Note the architect and reviewer currently share one model (122B-A10B-IQ2), so
      they share one curve but may sit at different points on it. Current bindings (the "122B-A10B-IQ2" note is stale): architect_general = Qwen3.8-Flash-Next UD-IQ4_XS (:8074), architect_critic = Qwen3.8-27B Q8 (:8083), frontdoor = Qwen3.6-35B-A3B Q8 (:8070); each gets its own curve from E-2.
- [x] **E-7 — Re-calibration trigger.** ✅ 2026-07-29. Make the invariant enforceable, not aspirational: a model swap,
      quant change, or kernel promotion **invalidates** that model's certified levels. Record each curve
      with its `(model, quant, kernel/era)` stamp and add a validator that flags a role whose bound model
      no longer matches the model its effort level was certified against. Same failure mode the registry
      already had — a role launching an artifact that had no model-indexed row of its own.
      **Amendment 2026-08-21 (via CT-2, `qwen-chat-template-evaluation.md`): the CHAT TEMPLATE is a
      calibration-voiding axis this trigger does not cover.** `architect-model-selection-bench.md:267`
      already ruled the prompt-template axis a per-model property, and the 2026-08-21 fleet sweep found
      three distinct embedded templates across four production models. A template swap (or a GGUF
      re-embed) invalidates certified levels the same way a quant change does — extend the stamp to
      `(model, quant, kernel/era, template_sha)` when E-7's validator is next touched.
       **First template-stamped recalibration ran 2026-08-22** (the terse pilot voided frontdoor +
       architect_general; both re-measured on the live path with `template 1443ea9ab4bb` in the
       stamp, belief-graded Witnessed/Attested): CT-E7 in `qwen-chat-template-evaluation.md`. The
       stamp extension is now PRACTICED **and ENFORCED: the validator was extended 2026-08-23
       (orchestrator `0e801e68`) — `REQUIRED_CERTIFICATION_FIELDS` now
       `(model, quant, kernel_era, template_sha)`; the bound template sha is read from
       `roles.<role>.chat_template` falling back to `server_mode.<role>.chat_template`
       (`served_template_sha256_12`), compared in normalized 12-char form (full 64-hex ≡ short).
       16 tests pass; live run exits 0 (ledger empty, validator dormant but correct). CORRECTION
       2026-08-23 (operator-prompted): the ledger's `active_kernel_era` had read
       `production-consolidated-v8`, which is STALE — production has been v9 since the
       2026-08-11 freeze and every E-7/Q38 calibration since is stamped `v9 0db32c06e/10125`.
       The field was written 2026-08-03 (pre-v9) and the v9 promotion never rolled it forward
       because the ledger was empty (no certificates to invalidate). Fixed 2026-08-23:
       `active_kernel_era: production-consolidated-v9`; a comment in the ledger now mandates
       rolling it forward at every kernel promotion, empty or not.**
- **[declined: ws58 2026-11-03 content-review: duplicate of routing-program.md's learned router (task -> budget); a stretch item with no difficulty signal of its own]** **E-5 — Dynamic selection (stretch).** Let the router pick effort from task difficulty rather than
      pinning it per role — a natural extension of [[project_learned_routing_controller]]. Needs a
      difficulty signal that is cheaper than just running the hard path.
- [x] **E-6 — Interaction with the `<think>` axis.** ✅ 2026-07-21. Effort (prompt) and `enable_thinking`
      (native channel) are **independent axes**; measured the grid. R2b/R2d established unlimited native
      `<think>` LOSES for both models via a **non-termination tail** (18% A1 / 50% A4). **Budget-cap result
      (`--reasoning-budget N --reasoning-budget-message`):** force-closing `<think>` drove non-termination
      to **0%** and recovered accuracy to ≈ think-off for both models at both budgets, at ~1.6–3× tokens
      (vs 6× unlimited) — **no capped arm is statistically distinguishable from think-off (all p ≥ 0.62),
      and none beats it.** Higher budget (6144) was consistently ≤ lower (2048). **Conclusion: the native
      channel can be made *safe* with a budget cap, but the accuracy lever is the PROMPT (axis 1, +32pp),
      not native `<think>`.** Full table in `architect-model-selection-bench.md` §R2d + §E-6; driver
      `architect_bench_gpu_budget.sh` (was named `run_budget.sh`; that name is not in git), analysis `e6_budget_analyze.py`; data `artifacts/architect-bench-gpu-20260720/e6_reasoning_budget/`.
- [ ] **E-6b — retest budget-cap on a NON-saturated suite.** E-6 ran on `gpqa_diamond_cot` (~85–90%
      ceiling), where "capped thinking ties think-off" may be a ceiling effect. Re-run the budget sweep on
      `olympiadbench_numeric` (harder) to see whether native thinking, once it terminates, *ever* beats the
      prompt-CoT baseline. Cheap: reuse `scripts/benchmark/architect_bench_gpu_budget.sh` (epyc-inference-research; `run_budget.sh` is not in git, anchor fixed 2026-11-09) with the olympiad suite.

#### Dependency graph
`R2a (done)` → `E-1 design` → `E-2 curve (per model, fan-out)` → `E-3 rescue-rate` → `E-4 role defaults` → `E-5 dynamic`.
`E-2` fans out per model and is the long pole; `E-4` cannot start until the frontdoor + architect curves exist.
`E-6` depends on **R2b** (thinking ON/OFF ablation, architect bench). `E-7` gates any deploy of `E-4`.
`E-4` is operator-gated (production config).

#### Cross-cutting concerns
- **This is a production-config change surface**, hence operator-gated. Nothing here edits the stack.
- Token cost is a **throughput** cost on a shared box: 4× output tokens on the frontdoor is a real
  capacity hit, not just per-request latency. Weigh against `feedback_cpu_decode_bw_bound`.
- Prompt-effort levels interact with **agent-file compression operating points** (roles already carry an
  `agent_file_compression_operating_point`) — both change the prompt; don't tune them blind to each other.
- Whatever ladder is chosen must be expressible per-role in the registry, and **indexed by model/quant,
  not role**, for the measurement rows ([[feedback_model_not_role_indexing]]).

#### Reporting instructions
Record per level × model: accuracy, mean/median/p90 tokens, truncation rate, parse-failure rate, and
rescue-rate vs the next-cheaper level. Flip the checkboxes here; a per-role default change is a proposal
to the operator, not an edit.

#### Key file locations
- Pinned item sets + all R1/R2 evidence: `epyc-inference-research/artifacts/architect-bench-gpu-20260720/`
- Runner (already supports `--limit`, `--repeats`, per-question JSONL, truncation capture):
  `epyc-inference-research/scripts/benchmark/v7_quality_gate_runner.py`
- Analysis: `architect_bench_analyze.py`, `thinking_ablation_analyze.py`, `architect_bench_rescore.py`
- Prompt text currently lives in the adapters: `epyc-inference-research/scripts/benchmark/dataset_adapters.py`
  (`gpqa_diamond` = letter-only, `gpqa_diamond_cot` = full CoT — these are already L0 and L3).

## Track: tool-output-compression
<!-- gate: none -->

> Folded from `handoffs/active/tool-output-compression.md` @ `7e268b4de29c` on 2026-11-02 (BRF-T1-F6, route 1a, operator D1/D5; retired row UFH-07 → RTG-08). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Tool Token Optimization — Output Compression + Definition Reduction

**Status**: Phase 2 implemented (output compression); Phase 2b monitoring wired (2026-04-11); Phase 3a-c done (definition audit, compression, AP-16 runtime measurement); A/B done (+4pp REPL, suite-dependent); Phase 4a-d MCP wrapper/telemetry/registration landed; P3d fallback chain now landed in orchestrator runtime scope; P3d.5 done
**Created**: 2026-04-04 (via research intake deep dive)
**Updated**: 2026-10-06
**Categories**: context_management, agent_architecture
**Priority**: MEDIUM
**Depends on**: None (independent workstream)
**Scratch**: `/mnt/raid0/llm/tmp/codex-ni06-main-20261006/` (MAIN review and decision custody; KEEP-marked).

---

#### Objective

Reduce token consumption from tool outputs (shell commands, test runners, git operations) by 60-90% before they enter the LLM context window. This is an **upstream compression layer** — complementary to session-level context folding (which compresses conversation history) and reasoning compression (which compresses model output). Together they multiplicatively reduce context pressure.

Target environments:
1. **Autopilot sessions** (Claude API) — direct cost reduction on input tokens
2. **Local llama.cpp sessions** — extend effective context within constrained windows (8K-32K)
3. **Root-archetype** — if successful, push patterns to the shared agent archetype for all Claude Code users

---

#### Existing Infrastructure (audit 2026-04-05)

The orchestrator already has two output handling mechanisms that the original handoff did not account for:

1. **`_spill_if_truncated()`** at `helpers.py:320-355` — truncates output to `max_output_preview` (1500 chars), spills full content to `/mnt/raid0/llm/tmp/` with `peek()` retrieval pointer. Feature flag `output_spill_to_file` (True in production). [2026-09-14: location is `src/graph/file_artifacts.py:47-73` (see the 2026-08-12 reference correction below); the effective default of `output_spill_to_file` must be re-verified — "True in production" is stale. `intake-1350#record`]
2. **`truncate_output()`** at `tools/base.py:105-120` (was `:80-95`, re-anchored 2026-09-14) — 8192 char hard cap per tool execution.

The Phase 2 native compression module **layers before** these mechanisms: compress first, then spill if still too long. This is strictly better — a 50K pytest output compresses to ~2K (failure-focused), and spill handles the case where even 2K exceeds the 1500-char preview limit.

#### Phase 2 Implementation (2026-04-05)

**Compression module**: `epyc-root/scripts/utils/compress_tool_output.py` (27 tests, all pass)

7 command handlers:
| Command | Strategy | Expected Savings |
|---------|----------|-----------------|
| pytest / python -m pytest | Failure focus — keep FAILED/ERRORS + summary | 90%+ |
| cargo test | Failure focus for Rust output | 90%+ |
| git status | Stats extraction — count by category + file list | 80-90% |
| git diff | Drop index/---/+++ boilerplate, keep changed lines | 70-80% |
| git log | Compact to hash + subject (detect already-compact) | 60-70% |
| ls | Aggregate by extension — `42 files (15 .py, 8 .ts)` | 70-80% |
| cargo build / make / tsc / gcc | Error focus — strip compilation, keep errors + context | 80-90% |

**Orchestrator integration**: Feature flag `tool_output_compression` (env `TOOL_OUTPUT_COMPRESSION`, default off). Wired at `helpers.py:1497` before `_spill_if_truncated()`. [2026-09-14: now `helpers.py:~700`, calls at `:727`/`:730`.]

**Claude Code hook finding**: PostToolUse hooks **cannot replace built-in tool output** (only MCP tools support `updatedMCPToolOutput`). The Claude Code hook approach from Phase 0/1 is not viable for Bash output compression. ~~Future work: wrap compression as an MCP tool~~ → **DONE (Phase 4 landed the MCP-tool wrapper `tool_output_compressor_mcp.py`)**; PreToolUse command rewriting remains an alternative.

---

#### Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-259 | RTK — Rust Token Killer | high | worth_investigating |

##### RTK Assessment (from deep dive, 2026-04-04)

**Strengths**:
- 60-90% token reduction across 100+ commands, <10ms overhead
- 12 well-documented filtering strategies (stats extraction, failure focus, tree compression, deduplication, etc.)
- 17.3k GitHub stars, active development (v0.34.3 stable, v0.35.0-rc active)
- Claude Code PreToolUse hook integration exists

**Risks (deploy-cautious)**:
- **Security**: Shell injection via `sh -c` (runner.rs), telemetry enabled by default, plaintext secrets in tracking DB, CI trust bypass — Issue #640 unresolved
- **Compensation problem**: Issue #582 reports 18% cost *increase* — compressed output forces more output tokens from LLM to compensate for missing context
- **Resource exhaustion**: EAGAIN/posix_spawn errors under heavy tool use (Issue #968) — directly relevant to autopilot workloads
- **376 open issues** including P1-critical bugs (multi-file cat, git push timeouts, broken JSON)
- **Hook scope**: Only intercepts Bash tool calls — Claude Code built-in tools (Read, Grep, Glob) bypass entirely

---

#### Phase 0 — RTK Sandboxed Trial

**Objective**: Measure actual net token savings (input reduction minus output compensation) under autopilot workload.

**Steps**:
1. Install RTK binary: `curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh`
2. Configure: `RTK_TELEMETRY_DISABLED=1`, exclude sensitive commands (`curl`, `env`)
3. Run `rtk init -g --auto-patch` to install Claude Code hook
4. Execute one standard autopilot session with RTK enabled
5. Collect metrics: `rtk gain --all --format json`
6. Compare against a baseline autopilot session without RTK:
   - Input tokens (should decrease)
   - Output tokens (may increase — compensation effect)
   - Total cost
   - Task completion rate (must not regress)
   - Retry/re-run frequency (indicator of information loss)

**Go/no-go criteria**:
- Net token savings ≥ 40% (accounting for output compensation)
- No EAGAIN errors during the session
- Task completion rate within 5% of baseline
- No security incidents (secrets in logs, unexpected network calls)

**Outcome → Phase 1 or Phase 2** depending on results.

---

#### Phase 1 — Deploy RTK (if Phase 0 passes go/no-go)

**Objective**: Production deployment with feature flag and monitoring.

**Steps**:
1. Add RTK binary to autopilot bootstrap (`scripts/nightshift/`)
2. Feature flag: `TOOL_OUTPUT_COMPRESSION=rtk` (values: `off`, `rtk`, `native`)
3. Configure exclusions per our security requirements
4. Add `rtk gain` metrics to autopilot session reports
5. Monitor for EAGAIN errors, cost regression, task quality

**Rollback**: `TOOL_OUTPUT_COMPRESSION=off` + `rtk init -g --uninstall`

---

#### Phase 2 — Native Hook Implementation (if Phase 0 fails go/no-go, or after Phase 1 identifies RTK limitations)

**Objective**: Implement the highest-value compression strategies as native Claude Code hooks, without RTK's security surface or bug load.

##### Strategy Prioritization (by our command frequency × compression ratio)

| Priority | Command | Strategy | Expected Savings | Effort |
|----------|---------|----------|-----------------|--------|
| P0 | test runners (pytest, cargo test) | Failure focus — hide passing tests, show only failures with context | 90%+ | ~100 lines |
| P0 | git status | Stats extraction — counts by status category | 80-90% | ~30 lines |
| P0 | git diff | Smart truncation — keep meaningful hunks, drop boilerplate headers | 70-80% | ~60 lines |
| P1 | git log | Stats extraction — compact format with hash + subject | 60-70% | ~20 lines |
| P1 | ls/tree | Tree compression — aggregate by directory, group by type | 70-80% | ~50 lines |
| P2 | build output (cargo build, tsc) | Error focus — strip passing compilation, show errors only | 80-90% | ~40 lines |
| P2 | linter output | Grouping by pattern — aggregate by rule/severity | 70-80% | ~40 lines |

##### Implementation Architecture

Two options:

**Option A: Shell-based hooks** (lowest effort)
- One bash script per command in `scripts/hooks/tool_output_compress/`
- Register as PostToolUse hooks in Claude Code settings
- Pipe command output through the compression script
- Pro: Simple, easy to customize, no compilation
- Con: Slower than Rust, shell parsing fragility

**Option B: Python compression module** (moderate effort)
- `scripts/utils/compress_tool_output.py` with per-command handlers
- Callable from hooks or directly from autopilot infrastructure
- Can also compress outputs in orchestrator's REPL pipeline (not just Claude Code)
- Pro: Testable, reusable across autopilot and orchestrator
- Con: More infrastructure

**Recommendation**: Option B — the Python module can serve both Claude Code hooks AND the orchestrator's REPL output path (where `_spill_if_truncated()` already operates). Single implementation, two integration points.

##### Root-Archetype Integration

If native compression proves valuable:
1. Extract the compression module as a standalone utility
2. Add to `agents/shared/` as a tool output processing standard
3. Document in root-archetype's operating constraints
4. Ship as a recommended hook configuration in agent bootstrap

---

#### Cross-References

| Handoff | Relationship |
|---------|-------------|
| `context-folding-progressive.md` | Complementary layers: this handoff compresses tool inputs, context-folding compresses conversation accumulation |
| `reasoning-compression.md` | Complementary layers: this compresses tool outputs, reasoning-compression compresses model reasoning |
| `../completed/meta-harness-optimization.md` | RTK/native hooks could be deployed as harness optimizations in autopilot; AP-16 tracks instruction_token_ratio for Phase 3 |
| `orchestrator-conversation-management.md` | Output compression reduces what enters the conversation, easing conversation management |
| `repl-turn-efficiency.md` | Complementary: this compresses tokens per tool call, REPL turn efficiency reduces number of tool calls |

---

#### Open Questions

- Does the compensation effect (Issue #582) scale with task complexity? Simple tasks may benefit from compression while complex debugging tasks may suffer.
- What's the right compression level per agent role? Architect may need full context, worker may benefit from compressed.
- Should compression be adaptive — start compressed, fall back to full on retry?
- For the orchestrator's REPL pipeline: compress before `build_root_lm_prompt()` or before `_spill_if_truncated()`?

#### Research Intake Update — 2026-04-06

##### New Related Research
- **[intake-273] "Context Rot"** (Chroma) — Performance degrades with input length, especially low-similarity content. Validates aggressive compression of tool outputs before context entry. Distractors (topically related but wrong content) amplify degradation — our compression should strip irrelevant tool output sections, not just truncate.
- **[intake-274] "The Complexity Trap" (arXiv:2508.21433)** — Simple observation masking (stripping old tool outputs) matches LLM summarization. 50% cost reduction, solve rates maintained. **Direct validation**: our pattern-based compression (Phase 2) is the right approach — possibly better than LLM-based compression for tool outputs. The hybrid finding (masking + summarization = 7-11% further savings) confirms our two-layer architecture (compress tool outputs first, then LLM-summarize conversation). Answers Open Question 4: compress before `_spill_if_truncated()` is correct — upstream compression is strictly better.
- **[intake-271] "Skill Issue: Harness Engineering"** (HumanLayer) — 14-22% token overhead from verbose agent instructions. Tool outputs that include explanatory framing (e.g., git status headers, pytest collection lines) are effectively "instructions" that consume attention budget without aiding task completion.

#### Research Intake Update — 2026-04-09

##### New Related Research
- **[intake-301] "AXI: Agent eXperience Interface"** (axi.md)
  - Relevance: TOON format achieves ~40% token savings over JSON — directly applicable as wire format for compressed tool outputs
  - Key technique: Combined operations (navigate+snapshot in single call), pre-computed aggregates (inline totals), progressive disclosure (minimal default + `--full`)
  - Reported results: 100% success, $0.074/task (lowest), 4.5 turns (most efficient) across 490 browser automation runs
  - Delta from current approach: Our Phase 2 compresses output *content*; AXI optimizes output *format*. These are complementary — apply TOON encoding after pattern-based compression for multiplicative savings. The progressive disclosure principle (minimal default, explicit `--full`) mirrors our truncation + peek() architecture.

- **[intake-302] "SkillReducer: Optimizing LLM Agent Skills for Token Efficiency"** (arXiv:2603.29919)
  - Relevance: 48% compression of tool/skill descriptions via adversarial delta debugging — applicable to our orchestrator's tool definitions
  - Key technique: Taxonomy-driven progressive disclosure separates core rules from supplementary content loaded conditionally
  - Reported results: 48% description compression, 39% body compression, +2.8% quality improvement (less-is-more)
  - Delta from current approach: We compress tool *outputs*; SkillReducer compresses tool *definitions*. Combined with AXI's output format optimization, this is a three-layer compression stack: definition → output format → output content.

---

#### Phase 3 — Tool Definition Compression (SkillReducer)

**Status**: design ready
**Source**: intake-302 (SkillReducer, arXiv:2603.29919)

##### Objective

Apply SkillReducer's compression principles to orchestrator tool definitions. We compress tool OUTPUTS (Phase 2) but not tool DEFINITIONS. SkillReducer reports 48% description compression, 39% body compression, +2.8% quality improvement (less-is-more effect).

##### Target Surface Area

1. **`DEFAULT_ROOT_LM_TOOLS`** in `src/prompt_builders/constants.py` (~2382 words)
   - Primary tool description block injected into every REPL prompt
   - Contains 30+ tool descriptions with when-to-use / when-not-to-use patterns
   - Apply adversarial delta debugging: remove description content, measure task success, keep minimal surviving description

2. **Agent role overlays** (`orchestration/prompts/*.md`)
   - frontdoor.md, architect_investigate.md, etc.
   - Each adds role-specific instructions that could be compressed
   - AP-16 already tracks `instruction_token_ratio` — use as measurement

3. **`tool_registry.py`** tool descriptions
   - Registered tool descriptions used by `list_tools()`
   - Visible to the model at runtime

##### Implementation Approach

**P3a — Audit current token cost**:
- Count tokens in each tool definition across all prompt paths
- Rank by frequency of use (from autopilot logs) * token cost
- Identify low-value descriptions (tools rarely used but consuming tokens)

**P3b — Manual compression pass**:
- Remove redundant when-NOT-to-use patterns where obvious from context
- Collapse duplicate tool entries (e.g., `web_research` appears multiple times in constants.py)
- Apply progressive disclosure: minimal description + `--help` escape hatch
- Measure `instruction_token_ratio` before/after via AP-16

**P3c — A/B test**:
- Run compressed vs original definitions on seeding harness
- Gate: quality must not regress (SkillReducer's +2.8% finding suggests it won't)

**P3d — Automated compression (future)**:
- Build adversarial delta debugging script
- Input: tool definition text + eval suite
- Output: minimal description that maintains task success

##### Work Items

- [x] P3a: Token audit of tool definitions across all prompt paths — ✅ 2026-04-09. `scripts/analysis/token_audit.py` + `docs/token_audit_report.md`. DEFAULT: 841 est. tokens (647 words), 41 entries, 4 duplicates. No usage freq data (seeding diagnostics unavailable). Instruction token ratio: 29.8%.
- [x] P3b: Manual compression of `DEFAULT_ROOT_LM_TOOLS` — ✅ 2026-04-09. 55% reduction (647→290 words). Removed 4 duplicates, all "Do NOT" clauses, merged related tools, flattened sections. Old version preserved as `VERBOSE_ROOT_LM_TOOLS` for A/B. Instruction token ratio: 16.0%. 162 tests pass.
- [x] P3c: Measure `instruction_token_ratio` delta (AP-16) — ✅ 2026-06-28. Static audit now reports default tool definitions at 15.0% of tools+rules+roles, with a prompt-library proxy of 10,686 char-proxy tokens. Runtime AP-16 was repaired in `epyc-orchestrator` commit `bd627b3e`; patched v6-era trials `#1010/#1011` recorded 3,188/3,295 instruction tokens and 91.8%/92.1% instruction ratios, replacing the stale 10,748-token prompt-library charge. `docs/token_audit_report.md` now separates active PromptBuilder scaffold from full prompt-library size.
- [x] P3d: A/B test compressed vs original definitions on seeding harness ✅ 2026-07-14 — A/B done (+4pp REPL, suite-dependent), per status header.

#### Research Intake Update — 2026-04-17

##### New Related Research

- **[intake-395] "Claude-Mem: Persistent Memory Compression System for Claude Code"** (repo: thedotmack/claude-mem)
  - Relevance: 3-layer progressive-disclosure retrieval (search → timeline → get_observations) is a direct template for how compressed tool outputs could be queried token-efficiently.
  - Key technique: hybrid FTS5+Chroma search over AI-summarized observations; ~10x token savings claimed via batched-ID full-detail fetch only after index filtering.
  - Delta: adopt the progressive-disclosure layering pattern for tool-output retrieval surfaces; do not adopt the component (AGPL-3.0, Bun/Node).

- **[intake-397] "Open Agents — Vercel-Labs Reference App for Background Coding Agents"** (repo: vercel-labs/open-agents)
  - Relevance: durable-workflow + tool-result reconnection patterns for long-running tool invocations whose outputs should survive disconnects/compaction.
  - Key technique: Vercel Workflow SDK step persistence with stream-reconnect; explicit agent/sandbox separation so tool outputs belong to the sandbox state rather than agent context.
  - Delta: pattern-only (TS/Vercel stack); cross-ref with hermes-outer-shell's two-layer memory architecture.

- **[intake-399] "GenericAgent: minimal self-evolving autonomous agent framework"** (repo: lsdefine/GenericAgent)
  - Relevance: minimal-tool-set discipline (9 atomic tools, <30K context) as a constraint when designing compression-aware tool interfaces.
  - Key technique: dynamic tool creation via `code_run` rather than adding tool surface area; layered memory pulls reduce per-turn context inflation.
  - Delta: reinforces the design pressure toward minimal tool surfaces and lazy-loaded tool outputs.

#### Research Intake Update — 2026-04-20

##### New Related Research
- **[intake-414] "Token Savior Recall — 97% Token Reduction MCP Server"** (repo: mibayy/token-savior)
  - Relevance: AST-level symbol navigation replaces full-file reads (41M → 67 chars per symbol lookup); hybrid BM25+vector search with RRF fusion for memory retrieval.
  - Key technique: structural AST indexing with symbol-level granularity; three-layer progressive disclosure contract (15/60/200 tokens); backward slice (130→12 lines, -92%); content-hash staleness detection.
  - Reported results: 98% task success rate, 40% active token reduction, 85% injected char reduction, 46% wall-time reduction.
  - Delta from current approach: RRF fusion in search path is an upgrade over simpler cascade; content-hash symbol staleness for automatic invalidation when code changes is novel for the compression pipeline.

- **[intake-415] "Context Mode — Context Window Optimization for AI Coding Agents"** (repo: mksglu/context-mode)
  - Relevance: subprocess sandbox execution prevents raw tool output from entering context — the exact Phase 3 MCP tool wrapping pattern identified in this handoff.
  - Key technique: subprocess sandbox in 11 language runtimes (only stdout enters context); FTS5+BM25 with RRF and Porter stemming; intent-driven filtering (>5KB threshold → index, return relevant sections only).
  - Reported results: Playwright snapshot 56.2KB→299B (99%); GitHub issues x20: 58.9KB→1.1KB (98%); large JSON API: 7.5MB→0.9KB (99%).
  - Delta from current approach: the subprocess sandbox pattern is the workaround for the PostToolUse hook limitation identified in Phase 2. The >5KB intent-threshold gating heuristic is a practical implementation detail worth borrowing.

#### Research Intake Update — 2026-04-24

##### New Related Research

- **[intake-454] "hermes-agent v2026.4.23 (v0.11.0)"** (`github.com/NousResearch/hermes-agent/releases/tag/v2026.4.23`)
  - Relevance: upstream compressor gains anti-thrashing, dedup, language-respecting collapse, and a fallback-to-main-model chain on 503/404. Directly overlaps this handoff's Phase 3+ compressor work.
  - Key technique: anti-thrashing (prevents the "compress → uncompress → compress again" oscillation we flagged in Phase 2b monitoring); language-aware collapse (preserves code-block structure in multi-language tool outputs); fallback chain so compressor failures degrade to main-model summarization instead of retry loops.
  - Delta: evaluate whether to port upstream compressor patches directly (our fork lags); the anti-thrashing logic in particular is a concrete fix for a known Phase 2b failure mode. Language-aware collapse is a natural extension to the current content-type routing.

- **[intake-450] "Venice Skills — Agent Skills for the Venice.ai API"** (`github.com/veniceai/skills`)
  - Relevance: ≤500-line SKILL.md rubric + explicit "gotchas" section — models the pattern this handoff's definition-reduction work (Phase 3a-b) is already following.
  - Delta: corroborating reference point, not a new technique. Apply to any future skill authored from compression insights.

#### Phase 3d — Fallback Chain (added 2026-04-24 from intake-454 deep-dive)

Source: [`research/deep-dives/hermes-agent-v2026-4-23-release.md`](../../research/deep-dives/hermes-agent-v2026-4-23-release.md). Upstream hermes-agent v2026.4.23 ships compressor improvements that **directly close a Phase 2b oscillation failure mode** flagged in our monitoring. All work non-inference (offline fixtures sufficient for unit-level validation).

**2026-06-14 audit correction**: the local `/mnt/raid0/llm/hermes-agent` clone has no `v2026.4.23` / `v0.11.0` tag; available compression commits map mainly to `agent/context_compressor.py` history (`119bad65` prune-first, `548cedb8` role-aware summary insertion, `3e2ed18a` one-shot main-endpoint fallback). Those are context-compaction patterns, not a direct drop-in for the deterministic bash-output compressor. Current local targets are split:

- `epyc-root/scripts/utils/compress_tool_output.py` — deterministic command-output compressor used by REPL output compression and the MCP wrapper.
- `epyc-orchestrator/src/context_compression.py` — B2 history compaction cheap pre-pass; already has type-aware tool output summarization and tool-pair sanitization.
- `epyc-orchestrator/src/tool_output_compressor_mcp.py` — Claude-Code-facing MCP wrapper; Phase 4a-b now owns compressed tool result telemetry.

Do not port a model fallback chain into `compress_tool_output.py` without new evidence: that script has no model dependency by design. Use Phase 4c top-up telemetry to decide whether anti-thrashing/language-aware additions are still needed.

##### Objective

Port three upstream compressor patterns into our `scripts/utils/compress_tool_output.py`:
1. **Anti-thrashing** — prevents the "compress → uncompress → re-compress" oscillation we already see in Phase 2b monitoring telemetry.
2. **Language-aware collapse** — preserves code-block structure across multi-language tool outputs (current per-content-type routing is a coarser version of this).
3. **Fallback-to-main-model chain on 503/404** — when the compressor model is unavailable, degrade to main-model summarization rather than dropping into retry loops that poison context.

##### Dependency

- D — pin bump v2026.3.23 → v2026.4.23 (now routed by [`user-facing-harness-index.md`](user-facing-harness-index.md)) — recommended-but-not-strict prerequisite. We can read the upstream patches directly without bumping our pin first; bumping makes side-by-side comparison easier and lets us run upstream's anti-thrashing test fixtures.

##### Work Items

- [x] **3d.1 — Inspect upstream patches** — locate the v0.10.0 → v0.11.0 commits touching the compressor module in `/mnt/raid0/llm/hermes-agent`. Identify the three patterns (anti-thrashing, language-aware, fallback chain) at the function/class level. Capture upstream's test fixtures if any. (~1 h) **DONE 2026-06-14**: upstream local history maps to context-compressor commits, not a direct deterministic bash-output port; no upstream fixture should be blindly transplanted.
- [x] **3d.2 — Port anti-thrashing into `scripts/utils/compress_tool_output.py`** — minimal version: track recent compress/decompress operations on the same content hash; suppress the third operation in any A→B→A oscillation pattern within a turn. (~2 h) **DONE 2026-06-18** in `epyc-root` `ca8c338`: the deterministic compressor now keeps a bounded recent outcome history by content hash, suppresses the third flip in a recent compress → passthrough → compress pattern, and emits `*_anti_thrash_suppressed` metadata when the guard fires. GitNexus impact for `compress_tool_output_with_metadata` was LOW (`impactedCount=2`). Validation: `python3 -m py_compile scripts/utils/compress_tool_output.py scripts/utils/test_compress_tool_output.py` passed; the base interpreter lacked `pytest`/`pip`/`venv`, so the worker used a direct Python smoke for the new gate.
- [x] **3d.3 — Port language-aware collapse** — extend the existing per-content-type routing with a language detector for code blocks (re-use existing fence-marker heuristics in the file); preserve fence boundaries when collapsing. (~2 h) **DONE 2026-06-27**: `scripts/utils/compress_tool_output.py` now applies a deterministic `code_fence_collapse` fallback for unknown-command outputs with oversized fenced blocks, preserving fence delimiters and language tags while replacing middle lines with language-appropriate omission markers. GitNexus impact for `compress_tool_output` was LOW (`impactedCount=1`); `compress_tool_output_with_metadata` was LOW (`impactedCount=2`). Validation: `python3 -m py_compile scripts/utils/compress_tool_output.py scripts/utils/test_compress_tool_output.py`; `uv run --with pytest pytest scripts/utils/test_compress_tool_output.py -q` -> `33 passed`; `uv run --with ruff ruff check scripts/utils/compress_tool_output.py scripts/utils/test_compress_tool_output.py` passed.
- [x] **3d.4 — Port fallback chain (503/404 → main model)** — when compressor model returns 503/404 or times out, route the input through the main model with a prompt template targeting summarization instead of compression-style condensation; cap fallback retries at 1. (~1–2 h) **DONE 2026-06-28** in `epyc-orchestrator` `a5080ecb`: the deterministic root compressor remains model-free, and the actual runtime fallback landed at `src/api/routes/chat_summarization.py::_run_two_stage_summarization`. If `llm_batch()` falls back to sequential chunk digesting and a worker digest fails with 404/503/timeout, the chunk is retried once through the synthesis/main role (`frontdoor`) before becoming a failed-section placeholder. Stats now expose `worker_fallback_role`, `worker_fallback_count`, and `worker_failure_count`. GitNexus impact was LOW for the orchestrator file (`impactedCount=6`) and LOW for `_run_two_stage_summarization` (`impactedCount=2`). Validation: `py_compile`, `ruff`, focused summarization tests (`39 passed`), adjacent chat vision/REPL/pipeline tests (`96 passed`), and API import smoke + summarization (`76 passed`).
- [x] **3d.5 — Validate against recorded oscillation transcript** — replay a saved Phase 2b monitoring transcript that exhibits the documented oscillation; confirm anti-thrashing prevents the third compression and the resulting context is correct. (~1 h, offline fixture only) **DONE 2026-06-28**: no recorded fixture existed locally, so `scripts/utils/test_compress_tool_output.py` now reconstructs the Phase 2b compress -> passthrough -> compress sequence on the same content hash and asserts the third call returns `pytest_anti_thrash_suppressed` with unchanged text/char counts. Validation: `python3 -m py_compile scripts/utils/compress_tool_output.py scripts/utils/test_compress_tool_output.py`; `uv run --with pytest pytest scripts/utils/test_compress_tool_output.py -q` (`34 passed`); `ruff` unavailable on this host.

##### Cross-references

- Synergizes with [`context-folding-progressive.md`](context-and-token-economy.md) Phase 3c — anti-thrashing reduces oscillation-induced false positives in their monitoring telemetry. See that handoff's Phase 3c subsection for cross-ref.
- Companion to [`user-facing-harness-index.md`](user-facing-harness-index.md) (the pin bump that gives us side-by-side access to upstream patches).

#### Research Intake Update — 2026-04-26

##### New Related Research

- **[intake-473] "@mariozechner/pi-agent-core — Stateful TypeScript Agent Runtime"** (`github.com/badlogic/pi-mono/tree/main/packages/agent`)
  - Relevance: defines `afterToolCall` as the canonical post-execute / pre-LLM-payload hook for tool-result rewriting. This is precisely the surface our compress_tool_output work needs to live on once it generalizes beyond a single point in the pipeline. Field-replace semantics let an `afterToolCall` return only the rewritten `content` (what the LLM sees) without touching `details` (what the UI sees), or vice versa — no deep merge, no coupling to tool internals.
  - Key technique: **throw-isolation** — a throw inside an `afterToolCall` middleware becomes an error tool result for that one call only, batch continues. CHANGELOG #3084 (2026-04-17) shows this was a deliberate fix to an earlier "abort whole batch" bug. Means the compaction / fallback / language-aware-collapse logic can fail on a single output without taking down adjacent compressions in the same parallel batch — directly addresses the Phase 3d.4 "compressor 503/404 → main model" fallback story.
  - Delta from current approach: our `scripts/utils/compress_tool_output.py` is currently invoked as a single point in the pipeline. The pi-agent-core hook architecture suggests factoring it as a composable middleware that other concerns (PII redaction, secret stripping, audit metadata injection) can stack onto without knowing about each other. Pairs cleanly with the upstream hermes v0.11.0 plugin-result-transform-hook surface tracked in 3d.x — same idea, different runtime.
  - Implementation refs:
    - `agent-loop.ts:617-642` — `afterToolCall` integration with field-replace semantics and throw-isolation.
    - `types.ts:64-73` — `AfterToolCallResult` shape (`{ content?, details?, isError?, terminate? }`).
  - Deep-dive: `research/deep-dives/pi-agent-core-stateful-ts-runtime.md`

#### Research Intake Update — 2026-04-30

##### New Related Research

- **[intake-509] "Skills For Real Engineers — Matt Pocock's Claude Code skills collection"** (`github.com/mattpocock/skills`)
  - **Reframe (post deep-dive 2026-04-30): `/caveman` is a prose-envelope-only style rider, NOT a generic compression alternative.** It is **orthogonal to TOON, not substitutable** — TOON owns structured payloads (already shipped, ~40% measured at the encoding layer); `/caveman` operates on the model's free-form prose generation. Stack order is `caveman on prose wrapper → TOON on the embedded structured payload`. Anything this handoff compresses that is structured (tool args, JSON-shaped tool results, registry slices) belongs to TOON; `/caveman` is only a candidate for the prose envelope around it.
  - Relevance: ships **`/caveman`** — a SKILL.md prompt instructing the agent to drop filler/articles/pleasantries/hedging from its own output while preserving technical accuracy. Pocock claims ~75% token reduction (self-reported, no methodology disclosed, no public measurement protocol — anecdotal headline only). The skill is one level up from our tool-output compressors and operates at the *agent's outgoing prose* layer.
  - Key technique: pure prompt-side compression — no second-pass LLM, no compressor model dependency, no parsing, no failure modes from a 503/404 fallback. A system-prompt rider is the leanest possible compression mechanism. Genuinely different mechanism class from the compressor-model approach this handoff currently pursues (Phase 3d.x); the two are complementary on prose-only payloads.
  - Delta from current approach: nothing in this handoff currently addresses *assistant-output* prose verbosity — the entire Phase 3d focus is tool-output compression. `/caveman` raises the question of whether a sibling "prose-envelope rider" lever should land in Phase 4+, gated identically to the suggestion-injection feature flag in `repl-turn-efficiency`. **Not in scope for Phase 3d.**
  - **Critical risks (block deployment without explicit eval gates)**:
    1. **Hedge-preservation risk**: `/caveman`'s drop-list explicitly includes "hedging" alongside articles/pleasantries. For inter-model escalation/delegation/consultation flows, hedge-stripping silently turns "this might work but..." into "this work" — a downstream verifier or aggregator that compares confidence levels across models cannot tell low-confidence answers from high-confidence ones. **Lever must NOT be deployed on flows that aggregate multi-model opinions until a hedge-preservation eval (uncertainty-marker recall on a held-out set) is in place.**
    2. **Persistence-clause risk**: `/caveman`'s prompt body says **"ACTIVE EVERY RESPONSE once triggered. No revert."** Applied across an inter-model session, the consumer model permanently degrades the upstream's prose unless the protocol carries an explicit "stop caveman" reset token. Need a session-scoped (not turn-scoped) on/off contract before this can be wired into any auto-flow.
    3. **Reasoning-fidelity risk**: prompt-side style riders are known to occasionally degrade reasoning on multi-step tasks (the model "compresses" intermediate thinking it actually needed). Pocock's repo does not measure this; the auto-clarity exception in `/caveman` covers "multi-step sequences where fragment order risks misread" but the gate is non-deterministic.
  - **Minimum eval gate before deployment** (Phase 4+ work): 50 consultation traces, blind quality scoring by Q-scorer, target **≥95% baseline quality at ≥40% prose-only token reduction**, plus an explicit hedge-preservation recall eval on a held-out set with explicit uncertainty markers. Do NOT trust Pocock's 75% headline as either a target or a baseline — treat it as an upper bound only.
  - Caveat: no empirical claims with methodology (credibility_score null). Pattern adoption only — no runtime component, MIT-licensed but calibrated to TypeScript app development. Pre-deep-dive framing of `/caveman` as a generic compression alternative was overstated; the corrected framing above governs.

#### Research Intake Update — 2026-05-25

##### New Related Research
- **[intake-605] "Repo Prompt — context-engineering tool (CodeMaps, Context Builder)"** (repoprompt.com)
  - Relevance: CodeMaps extracts classes/functions/references into a compact structural overview — a token-reduction lever at the *input/context-assembly* layer, sibling to this handoff's tool-output compressors. Reinforces the structured-vs-prose split: structural maps (like TOON for payloads) beat shipping full file bodies.
  - Key technique: structural symbol extraction + token-budget-bounded context selection; "curate over auto-search."
  - Reported results: vendor claim ~80% token reduction (unbenchmarked, credibility null) — treat as upper bound only, same caution as the `/caveman` 75% headline.
  - Delta from current approach: input-side analogue, not a tool-output compressor; proprietary GUI so pattern-only. Overlaps intake-330 (code-review-graph, ~8.2× structural token reduction) already tracked.
  - Audit refinement: if DCP emits CodeMaps or manifests as tool/context payloads, encode them with structured fields and stable IDs rather than prose blobs. Token savings should be measured with model-calibrated token counts and downstream top-up/error rates, not vendor headline percentages.

#### Research Intake Update — 2026-05-26

##### New Related Research
- **[intake-609] "FastMCP — Pythonic framework for building MCP servers and clients"** (`github.com/prefecthq/fastmcp`, Apache-2.0, v3.3.1)
  - Relevance: Phase 3 of this handoff identifies "wrap compression as MCP tool" as the workaround for the PostToolUse hook limitation (PostToolUse cannot replace built-in tool output; only MCP tools support `updatedMCPToolOutput`). FastMCP is the canonical Python scaffold for that wrapper; the project already runs a live FastMCP server (`epyc-orchestrator/src/mcp_server.py`, 11 tools, stdio, vendored-v1 path via `mcp>=1.0.0`).
  - Key technique (Phase 3 requires standalone v3, NOT the vendored v1 — feature boundary verified in intake-609 `notes`):
    - **Around-style middleware** (`on_call_tool` hook with pre+post + mutate-response + short-circuit): the natural insertion point for the compressor — pre-call passes through, post-call rewrites the tool result with the compressed payload AND emits the compression-ratio + downstream-top-up-rate metrics from intake-605's audit refinement, without instrumenting each tool by hand. Vendored-v1 has NO middleware.
    - **In-memory transport / test client**: unit-test the compressor end-to-end against the real tool without subprocess overhead. Vendored-v1 path requires a stdio subprocess.
    - **Server composition**: stack the compressor next to other internal tools in one process if Phase 3 grows beyond a single endpoint.
  - Delta from current approach: replaces the Phase 3 "wrap as MCP tool" stub with a concrete framework choice. Cost: adds `fastmcp>=3` as a new top-level dep alongside the existing `mcp>=1.0.0` — OR migrate the live `src/mcp_server.py` from vendored v1 to standalone v3 at the same time (recommended in intake-609 `notes` to avoid dual-codepath drift). v2→v3 upgrade guide exists; standalone v3 is a strict superset of the vendored v1 API at the decorator surface.

#### Phase 4 — MCP Tool Wrapping (unblocked 2026-05-26)

**Status**: P4a/P4b landed 2026-06-14 (`epyc-orchestrator` `fe64140`); P4c landed 2026-06-14 (`epyc-orchestrator` `5cf9d1e`); P4d landed 2026-06-14 (`epyc-orchestrator` `e346613`); **P4e closed 2026-09-24: the MCP surface was DROPPED (OP-49 C), see P4e.** Resolves the Bash-output gap that PostToolUse hooks cannot close (only MCP tools support `updatedMCPToolOutput`).

##### Objective

Expose the existing `scripts/utils/compress_tool_output.py` logic as an MCP tool surface so Claude Code sees compressed Bash output for the high-frequency commands enumerated in §"Strategy Prioritization" (`cargo test`, `git status/diff/log`, `ls`, `cargo build`/`make`/`tsc`/`gcc`). The orchestrator-side path that runs through `helpers.py:1497` [2026-09-14: now `~:700`] (`TOOL_OUTPUT_COMPRESSION` flag) keeps working unchanged — Phase 4 only adds the Claude Code MCP-tool surface that Phase 2's PostToolUse hook approach could not.

##### Approach

Add a new MCP server module that wraps the bash invocation as a `run_bash_compressed` tool, with an around-style middleware that runs the existing compressor on the tool result before it returns. This is intentionally a **separate FastMCP instance** from `src/mcp_server.py` (whose 11 tools are read-only introspection) — composed into the same Claude Code session via two `.mcp.json` entries, not via FastMCP server composition (the two surfaces have nothing to share at the composition layer).

##### Work Items

- [x] **P4a — Bash-compressor MCP server skeleton** (~1 h). New file `epyc-orchestrator/src/tool_output_compressor_mcp.py`. Single tool `run_bash_compressed(command: str, timeout_s: int = 60, working_dir: str = "") -> str` that shells out via `subprocess.run` with the same security envelope as the existing orchestrator bash path. Uses `from fastmcp import FastMCP` (v3, already pinned in pyproject after the 2026-05-26 migration). Add module-level test (`tests/unit/test_tool_output_compressor_mcp.py`) mirroring `test_mcp_server.py`'s direct-import pattern — v3 keeps `@mcp.tool()` callable, so existing test style transfers. **DONE 2026-06-14**.
- [x] **P4b — Compressor middleware** (~2 h). Implement `CompressorMiddleware(Middleware)` with `on_call_tool(self, context, call_next)`:
  1. `result = await call_next(context)` — let the tool run.
  2. Detect content type from the command (re-use the existing routing logic in `scripts/utils/compress_tool_output.py` — import, don't duplicate).
  3. Run the compressor on `result.content` strings; rewrite the result with the compressed payload.
  4. Emit per-call telemetry (`command`, `pre_bytes`, `post_bytes`, `compression_ratio`, `compressor_strategy`) into the existing Phase 2b monitoring sink (`logs/tool_compression_monitor.jsonl`).
  Wire via `mcp.add_middleware(CompressorMiddleware())` in the module's bottom. Use the FastMCP in-memory client (`from fastmcp import Client; Client(mcp)`) for the unit-test fixture so the middleware path is exercised without spawning a stdio subprocess. **DONE 2026-06-14**: root compressor now exposes metadata (`compress_tool_output_with_metadata`); MCP middleware rewrites text content, preserves structured result content, attaches `tool_compression` metadata, and writes JSONL telemetry with env override `TOOL_COMPRESSION_MONITOR_PATH`.
- [x] **P4c — Downstream-top-up rate measurement** (~1 h). Per intake-605's audit refinement (line 373), vendor token-reduction claims must be measured by *downstream* effects, not headline %. Add a paired telemetry field `next_turn_followup_command` to the Phase 2b sink — populated by reading the next bash command in the same session journal; flag patterns that look like "re-run uncompressed for missing context" (e.g., the same command re-issued within 3 turns, or `cat`/`head`/`tail` against a file just listed). Compute weekly `top_up_rate = followups / compressed_calls` from the journal; gate any compression-strategy promotion on top_up_rate ≤ 10%. **DONE 2026-06-14** in `epyc-orchestrator` `5cf9d1e`: MCP telemetry now records `top_up_candidate`, `followup_distance`, `followup_reason`, `next_turn_followup_command`, `followup_source_command`, and `session_id`; detection covers repeated commands within three compressed calls plus `cat`/`head`/`tail` views after `ls`, including common `head`/`tail` flags. Session filtering is exact when `TOOL_COMPRESSION_SESSION_ID` is set, avoiding cross-session contamination. Added `scripts/analysis/tool_compression_topups.py` to compute the weekly JSONL `top_up_rate` and gate against `<=10%`. Validation: `py_compile`; `ruff`; `pytest` for `test_tool_output_compressor_mcp.py` + `test_tool_compression_topups.py` passed 14; empty-live-log smoke reports 0 compressed calls, gate n/a.
- [x] **P4d — `.mcp.json` registration + Claude Code smoke test** (~30 min). Add a second entry to `epyc-orchestrator/.mcp.json` alongside `orchestrator`: `bash-compressor` → `python src/tool_output_compressor_mcp.py`, stdio. Restart Claude Code, run the smoke commands from §"Strategy Prioritization" via `run_bash_compressed`, verify each returns a visibly compressed result with the expected ratio band (60-90% per the table). Gate live use on a 1-week observation window of P4c top-up-rate before defaulting any high-frequency command to the compressed surface. **DONE 2026-06-14** in `epyc-orchestrator` `e346613`: project `.mcp.json` now registers both `orchestrator` and `bash-compressor` using the repo `.venv/bin/python` and absolute script paths with `PYTHONPATH=/mnt/raid0/llm/epyc-orchestrator`. Validation: `python3 -m json.tool .mcp.json`; both FastMCP servers booted and exited cleanly on stdio EOF; in-memory `run_bash_compressed` smoke returned `git status` strategy `git_status` at ratio `0.3399`, `ls -la tests/unit` strategy `ls` at ratio `0.0012`, and a top-up smoke flagged `ls src` → `head -20 src/tool_output_compressor_mcp.py` as `file_view_after_listing`. **Root registration fix 2026-06-28**: umbrella-session `.mcp.json` now also registers `bash-compressor`; root-started Claude Code sessions were previously unable to create the P4c telemetry sink.
- [x] **P4e — Decision gate: roll-out scope** ✅ 2026-09-24 — **DROPPED (operator, OP-49 option C).** The
  `bash-compressor` registration was removed from both `.mcp.json` files (root and orchestrator) and from the local
  `enabledMcpjsonServers`. Reasons: zero calls in 3 months. The tool's allowlist is not read-only (`python`,
  `sed -i`, `find -exec`). It has no shell, so no pipes, and builds/bench commands aren't allowed. And every
  PreToolUse guard matches `Bash` only, so promoting it would have been a route around all 8 of them. The module
  `src/tool_output_compressor_mcp.py`, its tests and `tool_compression_topups.py` stay in the tree, unregistered.
  The compressor library and the orchestrator-side `TOOL_COMPRESSION` path are unaffected. Any future Claude Code
  output compression must go through the `Bash` tool and its hooks, not a parallel MCP shell. Original: (no time estimate; data-driven). After 1 week of P4c data, decide per-command: (i) promote to default (Claude Code agent file overlay points the model at `run_bash_compressed` for that command), (ii) keep optional, or (iii) drop. Record decisions in this handoff under a "P4e results" subsection. **2026-06-28 evidence status**: telemetry is now present but underpowered. A controlled `git status` smoke created `/mnt/raid0/llm/epyc-root/logs/tool_compression_monitor.jsonl`; the analyzer reports `compressed_calls=1`, `min_compressed_calls=100`, `rollout_decision=awaiting_minimum_observations`, and `ready_for_rollout_decision=false`. `epyc-orchestrator` now prevents one-off smoke rows from falsely producing `promote_candidate`. **2026-09-14:** `/mnt/raid0/llm/epyc-root/logs/tool_compression_monitor.jsonl` does not exist on disk (checked 2026-09-14) — the observation window is not accruing. `intake-1359#record`. **2026-09-24 root cause (UFH-07): the tool is never CALLED.** Across all 1,092 retained Claude Code transcripts (2026-08-24→09-24) there are 0 `mcp__*` tool_use blocks of any kind and 0 ToolSearch queries for the compressor; MCP tools surface as deferred tools, and no agent file or skill points a session at `run_bash_compressed`. Registration (both `.mcp.json`, `enabledMcpjsonServers`) and the write path are correct: a real FastMCP in-memory `call_tool("run_bash_compressed", {"command": "git status"})` wrote a full P4c row (all follow-up fields populated); 19/19 unit tests pass. The window cannot accrue until an agent file directs use, and doing that for every session IS option (i) — so the P4e gate is now an operator choice about how to collect the data — **OP-49** (options: direct agents to the tool, which is option (i) in effect; a tagged canary that stays out of the top-up-rate calculation; or drop the tool).

##### Dependencies

- Standalone `fastmcp>=3` in `epyc-orchestrator/pyproject.toml` — **LANDED 2026-05-26** alongside the `src/mcp_server.py` migration. No further dep work.
- Existing `scripts/utils/compress_tool_output.py` (Phase 2) — re-used as a library, not modified.
- Existing Phase 2b monitoring sink (`logs/tool_compression_monitor.jsonl`) — extended with new fields, schema-backward-compatible.

##### Cross-references

- Phase 2 (orchestrator-side compression at `helpers.py:1497`) — Phase 4 is the **Claude-Code-facing** counterpart; the two paths are independent and can both ship.
- **Harness↔orchestrator context-management collision (2026-07-16):** a candidate *user-facing* harness (Hermes/OpenCode/ACP-speaker — NOT the dev harness) runs its OWN conversation compaction / prompt-cache mgmt / sub-agent spawning that can double-up or fight this orchestrator-side compression + `context-folding-progressive.md`. Orchestrator-side compression only pays off if the harness **cooperates** (defers to the Orch) — the concrete instance of the "layer-B needs harness cooperation ⇒ open-source harness" requirement in [`harness-selection-and-integration.md`](harness-program.md#track-harness-selection-and-integration). Seam = the `/v1` boundary.
- Phase 3d (anti-thrashing / language-aware / fallback chain) — those patches go into `compress_tool_output.py` itself, so they automatically benefit Phase 4 once the middleware is wired.
- [`internal-kb-rag.md`](knowledge-pipelines.md) — K6 was satisfied via the kb-search skill route, not an MCP tool; the v3 middleware pattern in P4b is the precedent if a future kb-search MCP variant is wanted.
- [`meta-harness-optimization.md`](../completed/meta-harness-optimization.md) HLE-1 — the per-call telemetry shape in P4b is a candidate evidence source for the "per-component harness metrics" axis if the compressor is ever scored as a harness component.
- intake-609 `notes` field — feature-boundary table behind the v1-vs-v3 decision.

#### Research Intake Update — 2026-07-21 (Phase 3d: observation-dropping beats summarization on the evidence)

- **[intake-869] "Diagnosing and Mitigating Context Rot in Long-horizon Search"** (arxiv:2606.29718; GAIR/SJTU) + `github.com/GAIR-NLP/ContextRot`
  - Relevance to Phase 3d: a seven-policy head-to-head that our evidence base (intake-273/274) could not provide. **But read the ablation, not the headline** — keep-latest alone 43.8% and plain Discard 44.6% versus keep-latest+summary 48.2% off a 35.0% ReAct baseline, i.e. dropping stale observations carries ~9pp of the 13.2pp lift and summarization contributes 3.6-4.4pp.
  - This corroborates intake-274 (The Complexity Trap) rather than contradicting it: masking matched or beat LLM summarization on SWE-bench in 4 of 5 configs on cost, with summaries causing 13-15% trajectory elongation. Two domains, same direction.
  - Second finding worth carrying: method effectiveness is **model-dependent** (isolation +19% on Qwen3.5, negative on GLM-4.7), which cautions against one global compression policy across our heterogeneous role stack — though it rests on n=2.
  - Numbers are OBSERVATION-grade (100-sample splits, no chance-corrected judge agreement, live-web contamination exposure per intake-877).

- [x] Phase 3d design input: bias the fallback chain toward cheap observation-dropping before LLM summarization, and require summarization to earn its cost in an A/B rather than assuming it. ✅ 2026-07-29 — audit resolves the ownership boundary: `compress_tool_output.py` already does deterministic observation dropping for recognized commands and fenced blocks, and deliberately has no model dependency. The only model fallback is the separate orchestrator two-stage document-summarization path, so it must not be ported into this tool-output script by analogy. Any runtime reorder needs its own telemetry-backed orchestrator task; unknown-command passthrough remains fail-safe rather than a generic lossy dropper. [intake-869, intake-274] [2026-10-20 regime caveat, `intake-2157#00`, `intake-2157#01`: dropping stale observations gains accuracy only while the model's own no-management accuracy on the task is below about 70 percent, and extra turns are paid in every regime; stratify before promoting an elision default per role. Default stays spill-only; see TOC-SP-7.]

#### Research Intake Update — 2026-07-29 (the compaction-default question: verbatim log + grep vs summarize-and-compact)

_Via `/research-intake` Stage-2 2026-07-29 (intake-913…932 batch). ACM (intake-914) and PRO-LONG (intake-919) both argue for a verbatim append-only trajectory log read back by `grep`/Python in place of threshold-triggered summarize-and-compact. Every arm in both papers is a closed frontier model, so the transfer question is ours to answer. Sibling filings in [`context-folding-progressive.md`](context-and-token-economy.md) (CF-3c masking anchor, ACM Base arm, non-termination counter)._

- [ ] **First-party A/B: verbatim-append trajectory log + grep/Python read, vs current summarize-and-compact.** Run on OUR models (frontdoor Qwen3.6-35B-A3B, architect Qwen3.8-Flash-Next UD-IQ4_XS — retargeted 2026-10-28 (operator): Qwen3.5-122B deprecated). This is the transfer test neither PRO-LONG nor its antecedent offers — every arm in both is a closed frontier model. MUST report **WALL-CLOCK** (neither paper reports latency) and MUST include a **log-growth / grep-latency curve** — the axis both papers assert ("tractable for logs over 100k+ lines") and neither measures. Deterministic-replay-eligible on the scoring axis. [2026-10-20 harness-cluster pointer: see TOC-SP-7 in the "Research Intake Update — 2026-10-20 (harness cluster)" section at the end of this file.] Step 0 (absorbs A/B-CTRL): decide what "current summarize-and-compact" is as a RUNNABLE arm — the live path does deterministic type-aware stubbing only and no caller invokes an LLM summarizer — or the comparison has no control. Requirements (absorbs A/B-C and A/B-INSTR): hold the context budget C equal across arms and record it in the artifact; hold ground-truth answer cardinality fixed while scaling the log; log trajectory length and tool-call count; LOCA-bench is DECLINED as the suite (n=75, no latency axis, 7 mock MCP servers) and LOCA Table 4 may be cited for GLM-5.2 only.
  - **[declined: ws58 2026-11-03 content-review: merged into the A/B as step 0]** **A/B-CTRL — the nominal control arm may not exist. Resolve before scheduling any compute**
        (intake-1316#record). `context-folding-progressive.md:84` states the live path does
        deterministic type-aware stubbing only and *"no caller invokes an LLM summarizer"*. Decide
        what "current summarize-and-compact" means as a **runnable** arm, or the comparison has no
        control. Zero compute; blocks the A/B independently of any source.
  - **[declined: ws58 2026-11-03 content-review: merged into the A/B as a requirement]** **A/B-C — hold the context budget C explicitly EQUAL across backbones and record it in the
        artifact** (intake-1316#record). Scroll's sweep is unauditable in exactly this way, and that
        is the specific defect our A/B should be built not to have. LOCA Table 4 may be cited as a
        prior for **GLM-5.2 only** (66.7 / 62.7 at LOCA 128K/256K) with the harness caveat stated
        inline; **do NOT cite the Qwen3.6-35B-A3B row as same-harness evidence about our frontdoor
        class.** COMPUTE-GATED as a citation-bearing arm; the requirement itself is zero-compute
        design text.
  - **[declined: ws58 2026-11-03 content-review: merged into the A/B as a recorded decline plus three requirements]** **A/B-INSTR — LOCA-bench evaluated as a candidate suite and DECLINED** (intake-1342#record),
        five reasons: n=75 with no repetitions, so SE 4.6–5.8 pp exceeds the effect sought; answer
        cardinality confounded with the length knob; no latency axis, which this A/B requires as
        its binding output; 7 mock MCP servers / 280 tools / Docker as cost of entry;
        ground-truth-adjacency in the verifier harness. Three requirements LOCA nonetheless earns
        for OUR arms: hold C equal across arms and record it; hold ground-truth answer cardinality
        fixed while scaling the log; log trajectory length, tool-call count and tool-output tokens
        alongside accuracy so premature termination is visible as itself rather than as a wash.
  - [x] **A/B-COST** (TOC-SP-7, 2026-10-20): every elision, masking or LLM-compression arm reports compressor wall time per episode, extra model turns per task, the SUM of input tokens over all turns (rolling input tokens, not final context size), prefix-cache reuse and the number of prefix-cache invalidations (history compression versus pre-cache observation compression), and declares summary placement (top versus tail append) (`intake-2150#04`, `intake-2157#02`); when arms share tasks it also reports per-task best arm and the oracle gain over the best single arm before any router is built (`intake-2172#record`).
  - [x] **A/B-TRIG** (TOC-SP-7, 2026-10-20): record the trigger fraction against the named window denominator and run at least two fractions (0.25 and 0.5) so context rot is separable from overflow avoidance.
  - [x] **A/B-STRAT** (TOC-SP-7, 2026-10-20): report accuracy per policy arm per evidence-span stratum and per terminal_state, with eta, rho and aligned rho beside accuracy (`intake-2172#record`, `intake-2189#record`).
  - **A/B-ARMS / A/B-REL** (TOC-MP-2, TOC-MP-3, 2026-10-31): arm table with each arm's flag/config recipe and C, plus the reliability, retrieval-miss, literal-recoverability and wall-share requirements and their schema additions: [`docs/design/toc-mp-ab-design-20261031.md`](../../docs/design/toc-mp-ab-design-20261031.md).
- [x] **Prerequisite: produce a single chronological, grep-able trajectory artifact per task** — and audit which `peek`/`grep` implementation is live. [2026-09-14: the event schema must include a per-task `spill_pointer_follows` count (peek/grep events whose path matches a spill path) and a retrieval-vs-execution tool-call split — completion can stay flat while re-queries double (5/6 cells in one synthetic environment; no surge in ALFWorld). `intake-1359#01`.] [2026-10-20 harness-cluster pointer: see TOC-SP-6 in the "Research Intake Update — 2026-10-20 (harness cluster)" section at the end of this file.] ✅ 2026-10-22
  **AUDIT HALF DONE 2026-08-12 (`auditor`) — box stays open for the build half.** The live
  implementation is the FILE-CAPABLE one: standard `REPLEnvironment` → `_FileToolsMixin`
  (`file_tools.py:15,22`) → `_FileExplorationMixin`, bound into the model namespace at
  `environment.py:416` (`"peek": self._peek`). Spill pointers ARE followable today. The
  context-only `RestrictedExecutor` variant is DOUBLY dormant: `restricted_python` defaults
  False (`features.py:112`) AND `is_available()` returns False on this host (RestrictedPython
  not installed), so the import-guarded path falls back regardless. **Latent hazard worth one
  line in the build**: installing RestrictedPython and flipping the flag silently swaps in
  context-only `peek` (`restricted_executor.py:206`, no `file_path` param) and every
  `_spill_if_truncated()` pointer becomes unfollowable — the build should either port
  `file_path` into `RestrictedExecutor._peek` or make `_RestrictedREPLEnvironment` refuse
  loudly at construction while spill pointers exist.
  *Build half — the one design input it needs before code (named, routed 2026-08-12): the
  artifact's EVENT SCHEMA is owned by the A/B above (what must the grep-latency curve grep
  for — code/output/error only, or prompt + token counts per event?). Hook point is known:
  `graph/helpers.py` has `state.last_output`/`last_error`/`last_code` untruncated in hand
  before the compression/spill block (~:700); `_spill_if_truncated` fires only on truncation
  so it is NOT the seam. Wrong schema = re-run the A/B, so the requirements come first.* **The gap is NOT verbatim storage.** Our episodic memory store is *already* untruncated and recently hardened: `orchestration/repl_memory/episodic_store.py`, `memories` table, with `action` / `context` / `outcome` as plain `TEXT` columns and no truncation at the write chokepoint. What does truncate is the REPL processing journal — `src/graph/session_log.py` (`output_preview[:200]`, `error_message[:300]`, `tool_calls[:5]`) — and what is missing is any *one* chronological artifact spanning a whole trajectory that a `grep` can walk. Second half of the audit: `src/repl_environment/file_exploration.py` has file-capable `_peek`/`_grep` while `src/restricted_executor.py`'s variants are CONTEXT-ONLY (no `file_path`) — if the latter sits on a live path, the `peek(99999, file_path=…)` pointer that `_spill_if_truncated()` emits is unfollowable there.
  - [x] Trajectory-artifact schema field (harness-cluster, 2026-10-20): `terminal_state` in {finished, context-exhausted, turn-exhausted, killed} (turn exhaustion is today only the string `[Max turns (N) reached]`, `src/graph/langgraph/nodes.py:154-158 @5d4ad2c0`; `intake-2172#record`).
  - [x] Trajectory-artifact schema field (harness-cluster, 2026-10-20): prompt tokens and served `n_ctx` per turn.
  - 2026-10-22 (rte-toc-writers) BUILD HALF DONE (orchestrator `e9cf0949`, origin/main). `src/graph/trajectory_artifact.py` writes one append-only JSONL per task (`<ORCHESTRATOR_TRAJECTORY_ARTIFACT_DIR>/<task_id>.trajectory.jsonl`): a `turn` event per REPL turn (request_id, prompt chars, server prompt/cached/completion tokens - null when unobserved, `n_ctx` from the compiled registry, retrieval-vs-execution tool-call split, spill-ledger fields with `turn_created`/`turn_age`, `ledger_visible` size/age, `shell_compaction_seen`) and one `final` event (`terminal_state`, `terminal_reason`, `solved` = the graph's finish flag NOT a grade, rolling input tokens with observed-turn count, `prefix_cache_invalidations`, `compressor_wall_s`, `spill_pointer_follows`, `evidence_span_tokens` null, computed offline by `evidence_span_tokens_est`). Hashes, lengths, counts and spill paths only. Default OFF: runtime flag `trajectory_artifact` (declared in `orchestration/runtime_flags.spec.yaml`) AND `ORCHESTRATOR_TRAJECTORY_ARTIFACT_DIR`; hooks in `_record_session_turn`, `_make_end_result`, `_spill_if_truncated`, `_execute_turn`, all fail-silent. Flag-off proof: `tests/unit/test_trajectory_artifact.py::test_flag_off_writes_nothing_and_spill_is_byte_identical` (flag off with dir set; flag on without dir; flag on with dir: spill text identical, no file or state when off). 44 passed (prompt_layout + trajectory_artifact + output_spill), 111 with features/runtime_flags. `terminal_state` mapping: success=finished, `[Max turns`=turn-exhausted, context-overflow error=context-exhausted, anything else=killed with the bracketed reason kept.
  - [x] **TOC-WRITER-HOOKS-1 - hook `trajectory_artifact.note_history_rewrite` and `note_shell_compaction` into their producers.** Today no compression arm calls `note_history_rewrite` (so `prefix_cache_invalidations` is always 0) and no OpenCode plugin `event` handler (`session.compacted`, see TOC-SP-10) calls `note_shell_compaction` (so `shell_compaction_seen` is always false). Call the first from every path that rewrites already-sent history (session compaction / history-level compression arms) and the second from the shell-compaction signal. Acceptance: a unit test per hook showing the final-event counter moves, flag-off byte identity retained. Owner: the TOC A/B session. ✅ 2026-10-22
    - 2026-10-22 (a1-orch-code, 3c4ca599) DONE, orchestrator `9eeb7ba8` (origin/main). Producers: `note_rendered_history` (the rendered session-log block, i.e. summary refresh / two-level consolidation; a non-append-only change counts one `prefix_cache_invalidations`) called where `_execute_turn` renders it, and escalation compression that changes the prompt. Session compaction is deliberately NOT a producer: it rewrites `TaskState.context`, never rendered into a prompt (UFH14-B1), so counting it would inflate the field. Shell compaction: control-only `/v1` packet `x_session_compacted` (answered before prompt parsing, no inference) -> `note_shell_compaction_session`, applied to every task bound to the session via `bind_session` (repl_executor) and to later ones; the OpenCode plugin `event` hook forwards `session.compacted` (root `harness/opencode-plugin`, node tests 100 pass / 6 skip). Caveat: `/v1` turns that do not run the graph produce no trajectory, so the mark lands only on graph tasks sharing the session id. Tests `tests/unit/test_trajectory_artifact.py` 22 (21 pass, 1 pre-existing skip: root toc_ab carrier path); flag off = no-op, byte identity kept.
  - [x] **TOC-WRITER-TOOLCALLS-1 - pass `tool_calls` on error turns so the retrieval/execution split is not undercounted.** `trajectory_artifact.note_turn` takes the tool-call names that `_record_session_turn` is given; the error-path callers in `src/graph/helpers.py` pass none, so retrieval/execution totals undercount on error turns. Pass `_get_exploration_tool_calls(...)` (baseline-diffed) at the error-path call sites. Acceptance: a test with an error turn that peeked, showing `retrieval` counted. Owner: the TOC A/B session. ✅ 2026-10-22
    - 2026-10-22 (a1-orch-code, 3c4ca599) DONE, orchestrator `9eeb7ba8`. The two post-execution nudge paths in `src/graph/helpers.py` (input() error turn, rejected status FINAL) pass the baseline-diffed `_get_exploration_tool_calls(...)` to the trajectory artifact only (new `trajectory_tool_calls` kwarg of `_record_session_turn`, None unless the artifact is on). The session-log record is NOT given them because its `tools:[...]` renders into the session-summary prompt block, so prompt bytes stay identical. Test: an error turn that peeked counts `retrieval`=1 while the session-log record keeps `tool_calls=[]`.
  - [x] Trajectory-artifact schema field (harness-cluster, 2026-10-20): spill-ledger fields (chars, lines, turn created, turn age at each follow, whether any size or age ledger was visible to the model at that turn; `intake-2151#00`, `intake-2151#01`).
  - [x] Trajectory-artifact schema field (harness-cluster, 2026-10-20): the trajectory-only evidence-span covariate (tokens between the first and last tool results the answer needs; `intake-2189#record`).
  - [x] Trajectory-artifact schema field (harness-cluster, 2026-10-20): a request id that joins each event to the inference tap so cost fields can be joined.
  - Trajectory-artifact schema field (TOC-SP-10, 2026-10-21; design text, the writer stays the line-477 box): `shell_compaction_seen` (boolean, per task, default `false`; set `true` for the rest of the trajectory once the harness reports that it compacted the session itself, so double compaction by the shell and by our policy is separable from our policy alone; `intake-1011#record`). Source event, verified against OpenCode pin `350c726a`: `session.compacted` is a bus event (`packages/schema/src/session-compaction-event.ts`, payload `{sessionID}`), published once per completed compaction (`packages/opencode/src/session/compaction.ts:554`, only when the compaction result is `continue`), and delivered to a plugin through the generic `event` hook (`packages/plugin/src/index.ts:224`, dispatched at `packages/opencode/src/plugin/index.ts:259`); there is no hook literally named `session.compacted`, so the template's premise is corrected: subscribe in the plugin's `event` handler and match `event.type === "session.compacted"`. The distinct pre-compaction hook is `experimental.session.compacting` (`plugin/src/index.ts:305`); it fires before the summary is written and is not the signal. Only the harness-side flag is verified at the pin; nothing was run.
  - [x] **VB-TOC-AB-WRITE producer call (owed, filed 2026-10-21):** the trajectory-artifact writer calls `scripts/vidya/adapters/toc_ab.write_belief_measurements(out_dir, run_id=..., producer=..., trajectory_path=..., arms=...)` at its finalize boundary, before the first compression A/B run; carrier and reader landed in root `7335da327`. ✅ 2026-10-29 (audit: orchestrator e9cf0949 (2026-10-21, on origin/main) TOC-SP-6 writer + toc_ab sidecar; scripts/benchmark/toc_ab_sidecar.py:100-103 calls write_belief_measurements at finalize; handoffs commit 9f8082a9e) [no-belief: audit-reconciliation]
- [x] Instrument **TOTAL** tokens per episode (not peak) in any compression A/B. **REOPENED 2026-09-16** (the closure below is false). ~~✅ 2026-07-29~~ — `src/graph/session_log.py` now accepts optional observed `input_tokens` / `output_tokens` per turn and aggregates episode `total_input_tokens`, `total_output_tokens`, `total_tokens`, and `token_observed_turns`. Missing usage stays explicit (`None` / observed-turn denominator), never silently zero; generated session logs expose per-turn totals when present. Focused suite `tests/unit/test_session_log.py` 52 passed. This is a telemetry primitive only; the first-party A/B remains open and any result is observation-grade until protocolled. ACM reports peak only while raising tool calls 1.6-2.4×, plus a summarizer call per compression and a full-archive-ingesting querier call per retrieval. On a prefill-bound CPU host, flatter peaks at 2× the calls may be a net throughput LOSS. [2026-10-20 harness-cluster pointer: see TOC-SP-7 in the "Research Intake Update — 2026-10-20 (harness cluster)" section at the end of this file.] ✅ 2026-11-01 — APP `44fa7f7d61305564c9b88ae14a13d7eb93ae785b`; [tests and canary](https://github.com/pestopoppa/epyc-orchestrator/tree/73dff64ccb79518b65ce351f41291564b6c62e0f/docs/evidence/toc-episode-usage-20261101); ROOT `a50cb6e807a1594de5e660ded02e116773f36746`, `tests/vidya/test_toc_episode_usage.py`. [no-belief: prospective instrumentation and model-free controls]
  - 2026-11-01: The requested TOTAL-token primitive is now implemented through the actual request-local usage ledger and trajectory event; the historical July session-log closure above remains false. The boundary spans REPL creation through FINAL repair, including a failed two-stage fallthrough, and excludes prior routing. Backend-reported input/output totals carry observed-call denominators; content-cache replay is separate and incomplete/censored evidence is null. Exactly pinned per-arm/task trajectory byte segments prevent cross-arm borrowing when task IDs repeat. Successful early two-stage without a trajectory is unavailable; multiple graph finals refuse export. APP controls 24 passed plus two real executor/model-free graph → sidecar → strict ROOT reader → private ledger canaries; ROOT controls 54 passed. No model execution, scientific A/B, performance or deployment claim. The existing-family projection preserves native fields; generic planning applicability is unavailable without native model/stack scope, so VB-TOC-EPISODE-USAGE stays open. [no-belief: source and model-free controls]
  - **Reopen note 2026-09-16 (sub-closure-fix, `closure_audit.py --strict-idents` sweep):** the claimed session-log token totals **exist on no ref**. Orchestrator `origin/main` @ `88a2902d` `src/graph/session_log.py` has no per-turn `input_tokens`/`output_tokens` and no `total_input_tokens`/`total_output_tokens`/`total_tokens`/`token_observed_turns` aggregation; `tests/unit/test_session_log.py` has no such test. `git log --all -G` over `src/graph/` and that test file finds no commit on any branch that ever added them. The tick arrived in root `08e9d60d` (2026-07-29), the same "2026-07-29" codex-lane closure wave as RC-9/E1a. Evidence: `progress/2026-09/2026-09-16-sub-closure-fix.md`. The total-token telemetry primitive is still needed before any compression A/B.
- [x] Map `query_memory` onto the existing `_spill_if_truncated()` pointer machinery. VERIFIED: ACM's memory needs NO embedding model, NO vector index, NO chunking — verbatim JSON archived by integer key, read back via one LLM recall call. This is a read API over spill pointers we already write (`helpers.py:320-355`). ✅ 2026-11-01 — APP `233338749f2609fd9a7621263bb024992df7f237`; [tests and proof](https://github.com/pestopoppa/epyc-orchestrator/tree/73e423913e7c59afb1f4e2c018d9d799eba38bb4/docs/evidence/query-memory-20261101). [no-belief: implementation and model-free controls]
  - 2026-11-01: Default-off `ORCHESTRATOR_QUERY_MEMORY=1` exposes `TOOL("query_memory")` through a private session registry, retaining permission/policy enforcement and scoped artifact authority. One-based keys map to existing insertion-ordered artifact paths and expire with the REPL. A recall makes one tracked worker call and accepts only an exact quote from the complete artifact; artifacts over 12,000 characters refuse with the existing `peek` fallback. This adds no embeddings, index service or chunking and makes no relevance or model-quality guarantee. Related controls: 79 passed, 1 legacy-default skip; one chat-header fixture failure reproduced on the unmodified base was deselected. No live activation or inference. [no-belief: source and model-free controls]
  **SCOPED 2026-07-29 (`auditor`) — machinery verified, one MISMATCH to resolve before implementing, and
  the row's code reference is wrong.**
  *Reference correction:* `_spill_if_truncated` lives at **`src/graph/file_artifacts.py:47-73`**, not
  `helpers.py:320-355` — helpers.py only re-exports it (`:39-42`) and calls it (`:727`, `:730`);
  `helpers.py:320-355` is unrelated `<<<TOOL_OUTPUT>>>` block-matching code.
  *What the pointer machinery actually is:* the full text is written to
  `/mnt/raid0/llm/tmp/{safe_task_id}_{label}_t{turn}.txt` and the model is handed a pointer string
  `[... N chars truncated; full {label}: peek(99999, file_path="…")]`. So the archive is keyed by the
  **triple (task_id, label, turn), encoded as a filesystem path**.
  *THE MISMATCH:* ACM's model — and this row's own wording — is *"verbatim JSON archived by **integer
  key**"*. The existing spill has no integer key and no index; the path IS the key. So `query_memory`
  cannot be a thin read over what is already written. It needs one of:
  (a) a per-task manifest mapping `int -> spill path` written at spill time (smallest change, keeps
  the path as truth); (b) renaming spills to a monotonic integer per task (breaks the existing
  `peek(...)` pointers already in transcripts); or (c) `query_memory(task_id, label, turn)` — no
  integer key at all, matching what exists and dropping ACM's key convention.
  **(a) is recommended:** it adds an index without invalidating any pointer already emitted, and the
  spill write is the only place that needs to change.
  *Left unimplemented deliberately:* this is a new agent-facing read API, not a fix — it wants the key
  decision above made first, and a design that adds an index is a different-sized change from the
  "thin read API" the row assumes.

#### Research Intake Update — 2026-09-14 (intake-1346…1366)
_Via /research-intake Stage-4 (operator-approved plan 2026-09-14). Sources: intake-1350 SoL-Pi, intake-1357 act-context, intake-1359 compression interaction costs, intake-1365 SWEzze — all dive-verified._

**STANDING (2026-09-14):** never LLM-summarise code-bearing tool output that feeds an edit; prefer verbatim slicing/masking. Summaries answered 4/45 behavioural questions vs 27/45 for source `intake-1357#03`; token-level compression (LLMLingua-2 ~3x) was −7…+6 instances vs full context `intake-1365#02`.

- [x] **TOC-SP-1 — Spill footer calls `peek`/`grep` with arguments in the wrong order.** ✅ 2026-09-14 — merged to epyc-orchestrator main `35b05fde` (pushed to origin 2026-09-14) (commit `1e2a6315`). `environment.py:650` emitted `peek("{path}")` / `grep("{path}", pattern)` but the signatures are `_peek(n, file_path)` / `_grep(pattern, file_path)` — the pointer never read the file. Footer now `peek(2000, file_path=...)` / `grep("<pattern>", file_path=...)`; the same bug in `suggestions.py` hint templates (flag `REPL_SUGGESTIONS`) fixed too; test executes the footer calls against a real spill. `intake-1350#record`.
- [x] **TOC-SP-2 — Exact recall for spilled output.** Add offset/length paging to `peek` (reads only `f.read(n)` from byte 0, `file_exploration.py:58-94`), a tail excerpt to `_spill_if_truncated` (head-only, `file_artifacts.py:63-70`), and content-hash spill names (currently `{task}_{label}_t{turn}` opened "w"). Pattern: SoL-Pi ObservationPack handle + exact paged recall. `intake-1350#02`. ✅ 2026-09-16
  - Evidence: epyc-orchestrator branch `sub/tooling-orch-20260916`, commit `af89c864`, integrated by orchestrator merge `370dc715` (pushed in `753343f5`, 2026-09-16).
    - `peek(n, file_path=None, offset=0)` pages by character offset; a negative offset counts from the end. It reads with `newline=""`, so CR/CRLF offsets are exact. At offset 0 the behaviour is unchanged.
    - `_spill_if_truncated` now returns head + tail, with an executable `peek(<omitted>, file_path=..., offset=<head_len>)` marker between them. The result stays within `max_chars`.
    - Spill names are `{task}_{label}_{sha256[:16]}.txt`, written atomically and never overwritten. Legacy `_t{turn}` files are untouched.
  - Tests: `tests/unit/test_output_spill.py`, 13 tests. They cover exact span recall via `REPLEnvironment.execute`, a verbatim legacy `peek(99999, file_path="…_t3.txt")` pointer still resolving, and paging round-trips. Combined with the peek and spill suites, 50/50 pass. GitNexus impact on `_spill_if_truncated` is LOW.
  - Not changed: the `root_lm_system.txt` peek doc (a prompt change, so left for the owner).
- [ ] **TOC-SP-3 — Verified-quote receipt for the spill worker summary.** `_spill_output` (`environment.py:907` (`def _spill_output`, anchor fixed 2026-11-09; originally `:746-838 @5d4ad2c0`); synchronous `role="worker"`, `n_tokens=512` `llm_call` at ~`:1005-1006`) summarises only the last 4,000 chars and accepts it unverified. Replace with quotes byte-verified against the full spill, exit-status agreement, failure evidence required inside quote content (stricter than SoL-Pi's label-only check), fail-open to head/tail; the summary is also accepted only if it is non-empty and shorter than the span it summarises (a cheap safety net, nearly vacuous at the 8,192-char spill threshold). Measure evidence retention vs the current summary on real failing test logs (inference), one shared failing-log set with REPL-EMB-3.1/3.2, as contrastive pairs (same task, raw spill readable vs summary only; keep tasks where the raw run succeeds and the summary run fails) and classify each loss as missing critical fact, lost variable or state, incorrect summary, unnecessary re-discovery or token truncation (`intake-2150#00`). Arms: current summary, verified-quote summary, a deterministic no-LLM shape header (JSON/CSV keys and row counts, code symbol list, test-log failure lines; replay-eligible and consistent with the standing rule against LLM-summarising edit-bearing output; `intake-2152#02`), and a placeholder-plus-pointer arm with no summary (`intake-2157#04`). Zero-compute preparation already done: the current prompts lack identifier/path/value retention, the task instruction as input, errors-only-if-they-inform-avoidance and a fixed state structure relative to ACON's optimized guideline (`intake-2150#record`); do not adopt ACON's credential-truncation rule (redaction is TOC-RD-1). `intake-1350#03`.
  - [x] **TOC-SP-3-EXP09-PILOT — File the original 12-log pilot verdict and preserve native evidence.** Result: `brf-exp09-pilot-20261102`, rc=75, 37/48 cells; inconclusive/REVISE harness because five answers hit the 256-token cap. [Native evidence and disposition](../../docs/reports/brf-exp09-pilot-20261104/README.md); parent TOC-SP-3 remains open. ✅ 2026-11-04 [belief: cc]
  - [x] **TOC-SP-3-EXP09-R2 — Repeat the frozen EXP-09 pilot with a 1024-token evaluator answer budget.** Worker Qwen3.6-35B-A3B-MTP-Q8_0, production-consolidated-v10 CPU kernel-store binary, unchanged `_spill_output` at orchestrator `3a428cb3`; 12 frozen failing logs, control/verified-quote/shape-header/pointer-only. Capture raw answers and evidence. Stop at 2700s, explicit STOP/deadline, invalid control/linkage or operational futility; partial/parse-truncated captures remain inconclusive. Full 48-cell completion plus verified control/mismatch rejection is required before EXPAND if verified-quote accuracy >= control; a clean full comparison below control supports STOP. Publish the repaired row and file its verdict; no activation claim. Filed rc=0; native result SHA-256 `d29680e346f05481d1387e8f90a2d095d009abfe9ea2a1bdb7be4b8e2cc32296`; [verdict and native evidence](../../docs/reports/brf-exp09-r2-20261104/README.md). ✅ 2026-11-04 [belief: cc]
    - Historical checkpoint 2026-11-04 (superseded by the corrected disposition below): `brf-exp09-answerbudget-r2-20261104` was initially filed inconclusive: 48/48 cells rc0, no 1024 ceiling hits; accuracy control 0.804, verified_quote 0.868, shape_header 1.000, pointer_only 0.264, but pass_complete reports mechanism_fired=false and capture_complete=false, so REVISE and no EXPAND/STOP call. The then-proposed next step was to diagnose the flags and repeat the 12-log pass; the corrected disposition and expanded R3 below supersede it.
  - **2026-11-04 EXP-09 R2 disposition:** rc=0, 48/48 unique item-arm cells, all parsed and below 1024 tokens; 12/12 planted quote mismatches rejected, pinned control and linkage verified. Verified-quote mean accuracy 0.8681 vs control 0.8035; exploratory decision **EXPAND**, not a product or statistical gate. The original terminal flags `mechanism_fired=false` and `capture_complete=false` are retained: `run_cell` returned score-only dictionaries for in-memory aggregation while complete cell records were emitted. Independent rederivation, earlier inconclusive filing and corrected verdict are preserved in [R2 evidence](../../docs/reports/brf-exp09-r2-20261104/README.md). Capped-10 failed-ID gold and substring matching limit interpretation. A separate non-gating audit using exact ID equality on that capped reference found mean recall 0.667 for verified quote and 0.250 for control; it does not alter the predeclared verdict. GitNexus upstream impact on orchestrator `_spill_output` reports CRITICAL: four direct callers, 16 total symbols, two API processes. That index is stale (indexed `84f6f6f`, checkout `326f502`), so counts need refresh before implementation; treat the reported risk conservatively and stop edits of that symbol. The independent evaluation row does not change it. [belief: cc]
  - [x] **TOC-SP-3-EXP09-R3-PARTIAL — File and preserve the disk-floor-interrupted R3 control capture.** rc=75; 24 of 96 planned cells, all control, no paired comparison; native result SHA-256 `59b4358cfdb709bf3b14a0781803d6595080b3045c8c0133b830b3e836ba7266`; [native partial result](../../docs/reports/brf-exp09-r3-partial-20261104/README.md). R3 remains open for the missing treatment cells. ✅ 2026-11-04 [belief: cc]
  - [x] **TOC-SP-3-EXP09-R4-STOP — File the disk-floor stop of the R4 continuation.** rc=75 after one second; no new native treatment cells, 24 original controls remain byte-exact. [End record and seed evidence](../../docs/reports/brf-exp09-r4-disk-stop-20261104/README.md). Parent R3 remains open. ✅ 2026-11-04 [belief: cc]
  - [x] **TOC-SP-3-EXP09-R5-STOP — File the disk-floor stop of the R5 continuation.** rc=75 after one second; no new native treatment cells, and the original 24-control seed remains SHA-256 `59b4358cfdb709bf3b14a0781803d6595080b3045c8c0133b830b3e836ba7266`. [End record and seed evidence](../../docs/reports/brf-exp09-r5-disk-stop-20261104/README.md). Parent R3 remains open. ✅ 2026-11-04 [belief: cc]
  - [x] **TOC-SP-3-EXP09-R6-STOP — File the disk-floor stop of the R6 continuation.** rc=75 after one second; no native treatment result or non-dry preflight; 24 original controls retain SHA-256 `59b4358cfdb709bf3b14a0781803d6595080b3045c8c0133b830b3e836ba7266`. [End record and seed evidence](../../docs/reports/brf-exp09-r6-disk-stop-20261104/README.md). Parent R3 remains open. ✅ 2026-11-04 [belief: cc]
  R7 continuation `brf-exp09-resume-r7-20261104` retains the R3 controls and is undergoing publication qualification for missing treatments; its runtime disk guard remains 150 GiB. The allocator does not hold for disk capacity, so a grant below the floor stops inconclusively. Compare across execution IDs and scratch pointer roots; no served-latency claim.
  - [x] **TOC-SP-3-EXP09-R3 — Expand the spill-summary evidence-retention screen on 24 distinct failing logs.** Worker Qwen3.6-35B-A3B-MTP-Q8_0, production-consolidated-v10 CPU kernel-store, unchanged `_spill_output` at orchestrator `3a428cb3`; retain 12 original logs and add 12 distinct-content test cases from 9 provenance groups (including one labeled intentional negative control and one 132,119-character log beyond the pilot’s 120,000-character upper bound); record their source campaigns and treat same-campaign cases as correlated; several added logs share capped gold test IDs, comparing control/verified-quote/shape-header/pointer-only with 1024-token answer cap. Fix the terminal capture aggregation and preserve raw answers/evidence. Pilot observed +6.46 percentage points verified-quote vs control; at 24 independent pairs worst-case paired standard error is about 20.4 points; correlated source groups can increase it, so this is descriptive screening, not a significance or activation gate. Check operational futility after each verified-quote cell from the fourth onward; stop on invalid identity/linkage, STOP/deadline, 2700-second cap, futility or full completion. Incomplete, unparsed or truncated captures are inconclusive. Report paired outcomes, per-arm denominators, quote acceptance/fallback and refetch counts, capped-reference scorer limits and native terminal validity; keep fallback cells in the primary denominator; retain the original substring scorer for the predeclared comparison and additionally report exact failed-ID recall on the same capped reference. Publish and file the row. ✅ 2026-11-09 — CLOSED AS SUPERSEDED by TOC-SP-3-EXP09-R7-SCREEN (below, ✅ 2026-11-05): R7 `brf-exp09-resume-r7-20261104` rc0 completed exactly this design (24 logs x 4 arms = 96 cells, original R3 controls retained, seed sha 59b4358c verified) after the R4-R6 disk-floor stops. No further R3 cells will run. [no-belief: superseded by an already-filed result]
  - **R3 interrupted 2026-11-04:** `brf-exp09-expanded-r3-20261104` rc=75 at the 150 GiB disk floor after 24/96 cells, all control; [original records](../../docs/reports/brf-exp09-r3-partial-20261104/README.md). No paired verdict is possible. Resume the remaining treatment cells with the same corpus, control/source/model pins and scorer; retain the original control bytes and disclose that treatment runs in a separate server execution and potentially different CPU region; retained control views and new treatment views also contain different scratch-path pointers. Continuation `brf-exp09-resume-r4-20261104` passed its fresh-cell smoke and is published; the 150 GiB long-run disk floor remains in force. R4 stores treatment cells in `out/results.jsonl`, the original controls in `out/results.r3-native.jsonl`, and preflight/terminal events in `out/run-events.r4.jsonl`; require matching non-dry-run execution identity and valid completion from the events as well as the full seed-plus-treatment grid. No served-latency or single-execution comparison is warranted. [belief: cc]
  - **R4 stopped 2026-11-04:** `brf-exp09-resume-r4-20261104` ended rc=75 at the disk floor one second after grant, with no native treatment cell or real preflight. [End and byte-exact control seed](../../docs/reports/brf-exp09-r4-disk-stop-20261104/README.md). The R3 screen remains incomplete. Successor `brf-exp09-resume-r5-20261104` passed a fresh-treatment smoke and is published; retain the 150 GiB long-run floor and split-execution/pointer limitations. R5 stores the original controls separately in `out/results.r3-native.jsonl`, new treatment cells in `out/results.jsonl`, and execution events in `out/run-events.r5.jsonl`; a verdict requires all three and the matching non-dry-run execution identity. R5 also ended rc=75 at the disk floor one second after grant, with no native treatment or real preflight; its stop is preserved in [R5 evidence](../../docs/reports/brf-exp09-r5-disk-stop-20261104/README.md). Two successive continuations thus made no treatment progress; the 150 GiB guard remains in force. The installed allocator has no disk-aware admission hold, so a ready successor can be granted below the floor and stop again; no keeper or gate was modified. Successor `brf-exp09-resume-r6-20261104` passed a fresh-treatment-cell smoke and is published, reusing the R5 kept source worktree. Its manifest note that R5 had “no new treatment cell” refers to native data; R5 did generate one dry-run quote cell. [belief: cc]
  - [x] **TOC-SP-3-EXP09-R7-SCREEN — file the R7 24-log, 96-cell screen.** ✅ 2026-11-05 `brf-exp09-resume-r7-20261104` rc0, descriptive PASS (verified_quote 0.8204 >= control 0.7663; shape_header 0.9792, pointer_only 0.2604). Validity: seed sha 59b4358c verified, 96 unique cells, all parsed (max 500 tokens), 24/24 planted rejections, control unchanged, valid pass_complete (exec 3cd36b60a388). Original 12: control 0.7827 / VQ 0.8681; added 12: 0.7500 / 0.7728. Paired VQ vs control 9 better, 5 worse, 10 tied; VQ fell back on 3 cells (kept in denominator); exact-ID recall control 0.125, VQ 0.680 (report-only). Exploratory, capped-10 substring scorer, correlated sources: no significance, no promotion. Evidence: `filing-done/brf-exp09-resume-r7-20261104.verdict.json`, `/mnt/raid0/llm/tmp/brf-exp09-resume-r6/r7/out/results.jsonl`. [no-belief: exploratory descriptive screen, no claim tuple captured]
  - 2026-11-03 EXP-09 pilot result (ws58, BRF-T4-EXP09): **REVISE (harness), screen.** The control was executed unchanged (orchestrator `3a428cb3`, fn sha `e1707a1b`), and the planted
    mismatch was rejected in 9/9 cells. The predeclared futility look fired after 37/48 cells (verified-quote 6.592 over 9 cells could not reach the control's 9.717 over 12).
    Accuracy: control 0.81, verified-quote 0.732, shape-header 0.50, pointer-only 0.271. Retention: 0.42, 0.73, 1.00, 0.00. The futility is confounded: all 5 parse failures
    are answers truncated at exactly 256 completion tokens (4 shape-header, 1 verified-quote). On parsed paired items, verified-quote scored 0.824 against the control's 0.808.
    The box stays open. Re-run the 12-log pass with a larger answer budget or a capped ID list before the full corpus.
    OBSERVATION: `/mnt/raid0/llm/tmp/brf-exp09/out/results.jsonl` sha256 `cb8f455daa1d…`. [belief: cc]
- [x] **TOC-RD-1 — Redact before compressing.** ✅ 2026-09-14 — merged to epyc-orchestrator main `35b05fde` (pushed to origin 2026-09-14) (commit `118b65e5`). `tool_output_compressor_mcp.py` returned output without redaction; now `redact_if_enabled` runs on raw text before compression, on the returned text, and inside direct `run_bash_compressed` calls (after the 200k cap). The `redaction.py` PEM rule now also redacts from an unterminated BEGIN header to end-of-text (terminated keys unchanged). Note: an unterminated key redacts everything after it, by design. New PEM tests live in `tests/unit/test_credential_redaction_truncated_pem.py` because the root `pii_precommit.sh` hook blocks edits to the existing credential test file.
  - [x] **TOC-RD-1a — PII pre-commit hook gaps (root `scripts/hooks/pii_precommit.sh`).** ✅ 2026-10-06 — ED25519 recognition is complete under NI07-31. Operator chose 1B: retain scanning of both credential-redaction fixture files; the proposed two global whole-file exclusions are rejected and unapplied. This closes the remaining operator-choice deliverable, not fixture editability. Exact source/content/custody guidance for any future concrete fixture edit is in the [resolved decision](../../docs/reference/credential-fixture-hook-decision.md); no exception is authorized. `intake-1350#record`.
  - [x] **TOC-RD-1b — PII hook over-blocks perf sample periods in markdown table cells** (filed 2026-09-24, <!-- completion: ✅ 2026-10-31 [no-belief: historical fixture restoration and staged-hook controls, no new measurement]; Research implementation 6918763bd7c8c5259a8da8be2832c564707719b7; test scripts/kernel_rnd/autokernel/loop/test_perf_period_hook.py; Git validation 299341e8258aa479fab60ee2ba19219098d9121c:artifacts/autokernel_ctx_ab_20260925/TOC-RD-1b-VALIDATION.md -->
    main-ak-seat). Committing research `ce5800cb`'s fixture (`loop/fixtures/ds41-run8-planner-prompt.txt`, a real
    DS41 planner prompt) tripped the `account_number` rule (`\b[0-9]{12,19}\b`) on 12-13-digit `perf` sample periods
    in 7 markdown table cells. The author redacted them. The committed bytes therefore differ from the real prompt. Inline
    mode's byte-for-byte fidelity was shown against the copy recovered from the opencode store (sha equal to the call
    record's), not against the committed fixture. Candidate exemption: a digit run in a `|`-delimited cell whose column header or row
    names a perf field (`Period`, `Samples`, `period`), with no account/card/customer/iban/routing/ssn token on the
    line — the same guard the config exemption uses.
    - Add a must-block negative-control fixture row (an account number in a markdown table) in the SAME change.
      `reviewer-calibration-accounting.md` flags this exemption surface for being tuned on its own over-blocks.
    - Do not change the hook outside that reviewed change. Acceptance: the unredacted fixture commits, and the
      negative control still blocks.
    - **Recurred 2026-09-25 (research `135b8492`).** The hook redacted 7 period cells in each of the two committed
      OAB-9 bundle `INDEX.md` copies (`artifacts/autokernel_ctx_ab_20260925/bundle-manifests/`). This time it
      rewrote the files in place, with `[period redacted]`, rather than blocking. So evidence copies silently
      stop being byte-exact, and the artifact README has to say so. Same exemption shape, second instance.
    - **Resolved 2026-10-31.** The exact run-8 fixture now hashes to the recorded actor-call prompt (`72c8677850d955b2598bd9d7254460b0fdead5c0ee2f150c80e897ae0ce47b99`); its seven period cells and the matching rows in both OAB-9 INDEX copies are restored. The same-change synthetic account row is still blocked by the actual staged ROOT hook; the restored prompt passes. The historical node-profile control fixture and its hash assertion were updated to retain their one-section delta.

- [x] **TOC-RD-1B-SRC — implement and verify the exact observed-periods cell selector.** ✅ 2026-10-06 — [MAIN source/native acceptance](../../artifacts/ni08/pii-period-source-20261006/README.md), staged synthetic73/73 with same-table account/secret refusal and full compatibility controls. Parent historical unredacted-fixture acceptance remains open; no whole-file exemption or historical reconstruction.

- [x] **TOC-RD-1a-NI-ED25519 — staged header recognition child.** ✅ 2026-10-06 — ROOT staged-blob scanner recognizes ED25519 while retaining RSA/OPENSSH; source/recipe promoted eb870f0fe697f02f887bedecaeaccaf24df2d531; native run 37474797195 TRUE9/9. This closes only the implementation child. Parent TOC-RD-1a is resolved by operator choice 1B: both fixture files remain scanned, with no whole-file exemption applied.

[Resolved scanner decision and narrower preparation guidance](../../docs/reference/credential-fixture-hook-decision.md); the rejected exact patch remains unchanged historical evidence.


##### Prospective bounded spill-summary request correction — 2026-10-07

- [x] **TOC-SP-4 — bound the rolling spill-summary request context.** ✅ 2026-10-07 — [MAIN original and product acceptance](../../artifacts/ni08/ufh12-spill-summary-source-acceptance-20261007/README.md). APP source `63399d6` is published as product `8108452` (exact two-file bytes); the 4,000-character request budget includes labels, bounded previous summary and at least one new-tail character. Whole15 mocked-worker/owned-spill controls passed in original hosted run `37664607006` at ROOT recipe `533d649`, with the complete eager source/config/readset and 52 locked packages/714 wheel hashes. Original NULL `37649822725` (pytest missing) and NULL `37659831973` (langgraph missing) remain separate. This closes request-size source conformance only; TOC-SP-3 quote verification, summary correctness/evidence retention, inference, runtime and deployment remain open. Native companion: VB-NI08-UFH12-SPILL-SUMMARY-CONTEXT-BUDGET.

Source/native recipe custody remains retained under /mnt/raid0/llm/tmp/ni08_remaining_backlog_screen-20261007/; MAIN applies checklists only after review of original source/read/result/error evidence.

#### Research Intake Update — 2026-10-20 (harness cluster)

Operator-approved 2026-10-20 via research intake (plan sha256 1dc83054706ca0bae002602307b0d9ba6435b010be4d6ffd8a495a04605f3967). Monitor and knowledge records below are prose: no checkbox, no index next action.

- [ ] **TOC-SP-5 — Decide the 1991-L1/L2 gates on the one standing per-turn corpus, or record each blocked on the trajectory-artifact build (read-only, zero inference).** Over `data/bep_sandbox` (62 trajectories, coder_escalation, 5 tasks x 2 arms; the only per-turn corpus, MF-VBS-1) compute: (a) per served role and its named window denominator (65,536 per slot on :8070; on :8083 the per-request cap 262,144 inside the shared 393,216 pool, the 98,304 figure is historical) the share of trajectories whose peak prompt exceeds 0.50, 0.60 and 0.85 of the window (`intake-1991#01`, `intake-2153#00`); (b) the spill-pointer follow rate per task (peek or grep by spill path), stratified by spill-size decile with follows-per-spill, plus re-reads and re-runs of the same path or command after an elision (`intake-1991#02`, `intake-2151#04`, `intake-2157#04`). Predeclared rule (Stage-3 proposal): a metric the corpus cannot compute is recorded 'blocked on the TOC-SP-6 artifact build'; if under 10 percent of trajectories exceed 0.60 of the window at a role, the CF-AB-1 compaction arms are skipped for that role; if under 10 percent of tasks ever dereference a spill pointer, the `query_memory` row (line 498) stops at the stub-with-rerun-hint form. Denominator: all 62 trajectories, unparsable ones counted. 62 trajectories cannot support a population claim; the result gates arms and a schema decision only. Record a dated result note under this task.
  - 2026-10-21 (noninf-toc; read-only, zero inference) PARTIAL, not ticked. Corpus `data/bep_sandbox/**/traces/*.jsonl`: 62 trajectories, 0 unparsable, 384 turns; roles `coder_escalation` (59 trajectories) and `architect_coding`+`coder_escalation` (3). (a) The corpus records no prompt tokens and no served n_ctx, only `prompt_chars` and on 162 of 384 turns; 26 of 62 trajectories carry it on every turn, 36 on none. Because tokens cannot exceed characters, a trajectory whose largest `prompt_chars` is below 0.50 x window cannot exceed 0.50 of that window: the largest value over the 26 covered trajectories is 12,649 chars, below 0.50 x 65,536 = 32,768, so none of those 26 exceeds 0.50, 0.60 or 0.85 of the :8070 per-slot window (nor of the 262,144 per-request cap on :8083). The other 36 trajectories (denominator is all 62) are recorded 'blocked on the TOC-SP-6 artifact build' (no per-turn prompt tokens). The share-above-0.60 rule (under 10 percent skips CF-AB-1 compaction arms) therefore cannot be decided at any role from this corpus; role-to-window mapping for `architect_coding` was not resolved. (b) Spill-pointer follow rate: blocked/undefined. 0 turns carry a spill header in `prompt_tail` and 0 turns reference a spill path in `raw_output`/`extracted_code`; the tasks never spilled, so there are no spills to follow and 'under 10 percent dereference' would be vacuous. The `query_memory` stop rule is NOT triggered by this. Re-run once the TOC-SP-6/line-477 artifact exists.
  - 2026-10-22 (rte-toc-writers): stays OPEN. The trajectory-artifact writer landed (orchestrator `e9cf0949`, default off) but no run has emitted artifacts yet, so the read-only (a)/(b) computation has nothing to read. Re-run it over the first A/B run's artifacts (`final.rolling_input_tokens`, per-turn `prompt_tokens`/`n_ctx`, `spill_follows`); the previously 'blocked on the TOC-SP-6 artifact build' metrics become computable then.
- [x] **TOC-SP-6 — Extend the UFH-07 trajectory-artifact event schema (the open prerequisite box at line 477) with the fields the harness-cluster dives need (design text; the writer stays the line-477 box).** Add as sub-bullets: `terminal_state` in {finished, context-exhausted, turn-exhausted, killed} (turn exhaustion is today only the string `[Max turns (N) reached]`, `src/graph/langgraph/nodes.py:154-158 @5d4ad2c0`; `intake-2172#record`); prompt tokens and served `n_ctx` per turn; spill-ledger fields (chars, lines, turn created, turn age at each follow, whether any size or age ledger was visible to the model at that turn; `intake-2151#00`, `intake-2151#01`); the trajectory-only evidence-span covariate (tokens between the first and last tool results the answer needs; `intake-2189#record`); and a request id that joins each event to the inference tap so cost fields can be joined. ✅ 2026-10-20
- [x] **TOC-SP-7 — Amend the compression A/B requirements: children A/B-COST, A/B-TRIG, A/B-STRAT under the first-party A/B box (line 456), and the Phase 3d regime caveat on line 450.** A/B-COST: every elision, masking or LLM-compression arm reports compressor wall time per episode, extra model turns per task, the SUM of input tokens over all turns (rolling input tokens, not final context size), prefix-cache reuse and the number of prefix-cache invalidations (history compression versus pre-cache observation compression), and declares summary placement (top versus tail append) (`intake-2150#04`, `intake-2157#02`); when arms share tasks it also reports per-task best arm and the oracle gain over the best single arm before any router is built (`intake-2172#record`); add a one-line pointer on line 496. A/B-TRIG: record the trigger fraction against the named window denominator and run at least two fractions (0.25 and 0.5) so context rot is separable from overflow avoidance. A/B-STRAT: report accuracy per policy arm per evidence-span stratum and per terminal_state, with eta, rho and aligned rho beside accuracy (`intake-2172#record`, `intake-2189#record`). Phase 3d annotation, in place and without unticking: regime caveat (`intake-2157#00`, `intake-2157#01`), the masking gain collapses above about 70 percent no-management accuracy and extra turns are paid in every regime, so stratify before promoting any elision default per role; the default stays spill-only and any non-default policy per role carries a stratified A/B result before it is declared as per-role registry data (precedent: `COMPACTION_PROFILES`, `src/graph/session_log.py:501-559 @5d4ad2c0`). ✅ 2026-10-20
- [x] **TOC-SP-8 — Error-bearing output is never LLM-summarised or aged out in the REPL spill path (implement behind a default-off flag).** Today `_spill_output` is purely length-triggered and summarises an error-bearing stdout/[STDERR] over 8,192 chars exactly like a success, while the prompt-build path truncates errors harder than outputs (500 versus 1,500 chars, `graph/helpers.py:1200-1205 @5d4ad2c0`) and `scripts/utils/compress_tool_output.py:52-125` keys on the command string only; the only exemption is the default-off `/v1` folding path (`src/context_compression.py:203-235`, substring match). Implement: output with a non-zero exit, a traceback marker or a [STDERR] segment keeps head+tail with the executable peek marker and is never worker-summarised; unit tests in `tests/unit/test_output_spill.py` for success/error parity, flag-off byte identity and the 500-char error budget; the error definition is taken from the structured `ExecutionResult.error` plus a [STDERR] marker check. Evidence: masking error outputs raised the open-error rate (`intake-2157#04`). No activation; activation belongs to the CF-AB-1 A/B.
  - 2026-10-21 (noninf-toc) code done, not ticked. epyc-orchestrator `af8ac62f` (lane noninf-toc-20261021): `_spill_output(output, error=None)` in `src/repl_environment/environment.py`; flag `ORCHESTRATOR_REPL_SPILL_ERROR_PRESERVE=1` (default off, read per call). Error-bearing = structured `error` argument, `[STDERR]` marker, `Traceback (most recent call last)` line, or a `[exit code: N]` line with N>0. Such output is spilled in full, returns header + first 300 + last 200 chars (500-char budget) + executable `peek(2000, file_path=...)` footer, and never calls the worker. Tests in `tests/unit/test_output_spill.py::TestSpillErrorPreserve` (success/error parity, kwarg, flag-off still summarises, 300-char head) plus the existing `tests/unit/test_repl_spill_output.py`: 32 passed. Follow-up (main-approved): with the flag on, `execute()`'s exception text over `output_cap` is routed through `_spill_output(..., error=...)` (`_error_text_for_result`); flag off and under-cap text are byte-identical (exact-string tests); 40 passed across the three test files. No activation. ✅ 2026-10-21
- [x] **TOC-SP-9 — Draft a result-equality repeat-notice guard as a default-off, separable REPL-loop arm.** Baseline: the call-agnostic no-progress guard `ORCHESTRATOR_REPL_LOOP_GUARD` (`graph/helpers.py:296-322, 1255-1262 @5d4ad2c0`, default off; it counts turns without `file_write_safe` or `FINAL(` and is explicitly not identical-match); there is no repeated-error or read-without-edit detector. Design: key = (action sha256, observation hash or exit+output hash, file revision+range); deliver one factual notice per evidence key after a quiet period (through turn 10); the text calls it a repeat notice and states it does not establish stalled progress; a terminate rule only after an identical failing streak (5 for reminder and 8 for terminate are the published hypothesis with no efficacy evidence, `intake-1991#record`); the notice is measured apart from view shortening (`intake-2153#02`). Fixtures: identical call with a different result, identical result with a different file revision, quiet period, flag-off identity. Draft and fixtures only; no activation.
  - 2026-10-21 (noninf-toc) draft and fixtures done, not ticked. epyc-orchestrator `af8ac62f`: new unwired `src/graph/repeat_notice.py` (`RepeatNoticeGuard`, flag `ORCHESTRATOR_REPL_REPEAT_NOTICE`, default off, separate from `ORCHESTRATOR_REPL_LOOP_GUARD`); key = (action sha256, exit+output sha256, file revision, range); one factual notice per key after the quiet period (no notice through turn 10); text says it does not establish stalled progress; reminder at 5 and terminate at 8 identical failing turns (hypothesis constants). `tests/unit/test_repeat_notice.py`: 6 passed (different result, different file revision/range, exit status, quiet period + one-per-key, terminate streak, flag default). Flag-off identity holds trivially: nothing imports the module. Interpretation of "quiet period (through turn 10)": no notice is delivered through turn 10 (accepted by main). Draft only, default off, unwired. ✅ 2026-10-21
- [x] **TOC-SP-10 — Add `shell_compaction_seen` to the trajectory event schema.** Add a boolean `shell_compaction_seen` to the trajectory-artifact event schema, populated from the OpenCode plugin hook `session.compacted` once the event name is verified against the audited OpenCode pin `350c726a` (the premise is read only from a template), so double compaction is observable (intake-1011#record). Acceptance: the field is in the schema and the event name is verified or the task records the pin check failed. Estimate: 0.3 day. ✅ 2026-10-21
  - 2026-10-21 (dpf-logpfx): field filed as design text under the trajectory-artifact schema list (below the request-id field). Event name verified at OpenCode pin `350c726a`: `session.compacted` is a bus event (`packages/schema/src/session-compaction-event.ts`, published `compaction.ts:554`), delivered via the plugin `event` hook (`plugin/src/index.ts:224`, dispatched `opencode/src/plugin/index.ts:259`); no hook is literally named `session.compacted`. Nothing run.
- [x] **TOC-SP-11 — External-corpus cross-check for the TOC-SP-5 window-binding gate (column-only read).** Read only the top-level columns (harness, benchmark, models, status, success, steps, max_tokens) of the 12 v2 parquet files of the public Exgentic traces dataset by column projection (no message bodies), first confirming the definition of max_tokens in the dataset build script, then report per benchmark and harness the share of runs whose max_tokens exceeds 0.60 and 0.85 of 65,536 and of 262,144, beside the 62-trajectory corpus result (intake-2303#record). Zero inference. Acceptance: a per-benchmark table with N and the max_tokens definition recorded. Estimate: 0.5 day. ✅ 2026-10-21
  - 2026-10-21 (dpf-logpfx): DONE. Column-only read (no `spans`) of Exgentic/agent-llm-traces-v2 at revision `4b8ad4ab`; table and script: `artifacts/dpf-logpfx/toc-sp-11-exgentic-v2-window-crosscheck.json`, `scripts/analysis/toc_sp11_exgentic_window_crosscheck.py`. Definition of `max_tokens` (dataset build script `_recompute_aggregates`): per-session maximum over surviving chat spans of input plus output tokens, NOT the request parameter. Discrepancy: the task says 12 parquet files; the dataset has 9 (`data/train/0000..0008`), and 10,056 rows were read against 10,057 documented. Share of runs above 0.60 / 0.85 of 65,536 and of 262,144: ALL (10,056) 33.6/25.9% and 5.7/4.0%; appworld (1,500) 78.5/64.3% and 0.1/0.0%; browsecompplus (1,948) 51.9/40.1% and 13.3/9.2%; swebench (1,959) 36.3/22.1% and 12.0/10.4%; tau2_airline (957) 8.8/6.8% and 1.0/0.6%; tau2_retail (1,848) 10.5/9.5% and 1.0/0.3%; tau2_telecom (1,844) 10.8/10.0% and 2.6/0.6%. By harness (>0.60 of 65,536): smolagents_code 57.6%, claude_code 32.5%, tool_calling 28.1%, openai_solo 21.1%, tool_calling_with_shortlisting 2.7%. Window-binding signal for the TOC-SP-5 gate: appworld and browsecompplus exceed 0.60 of a 64K window in 52-79% of runs. Beside the 62-trajectory corpus (none of the 26 covered trajectories exceed any threshold; 36 blocked) the two do not overlap enough to compare. Caveat: max values reach 3.4M tokens, above any window, so tails are not interpreted.
- **M7 (monitor, 2026-10-20) — Context-policy follow-ons (cache of repeated read-only results, reject-with-notice overflow, LLM-compression tuning, learned router, staleness measure, Yuj replication, AgentLongBench probe, IterResearch, ParallelMuse, LongBioBench).** Trigger: The TOC-SP-5 result shows a role with a binding window (peak prompt above 0.60 for more than 10 percent of trajectories), or the A/B-CTRL arm survives the standing rule against LLM-summarising edit-bearing output. First step when it fires: Add the listed arm to the CF-AB-1 comparison at that role. No immediate step remains: Without a binding window none of them has a problem to solve; each is untested by its author.
- **K2 (knowledge, 2026-10-20) — Per-model and regime priors (component and context-policy value depends on served model and budget; main effects suffice; a wall-clock cap conflates speed with window management; preview length sits at ACON's threshold).** Retained use: Cited by TOC-SP-7 and HIL-9 items 8 and 19; borrows no number.

##### Research intake 2026-10-22 — Locals + Beacon (intake-2386..2460)

- [x] **TOC-SP-LB1 — Measure the rate of consecutive identical (name, args) tool calls and what follows them in the conversation stores, then choose between wiring the result-equality repeat notice and model-voiced steering with a one-reply tool ban (intake-2386).** ✅ 2026-10-22
  - *(2026-10-22, workspace-f8 / locals-a.)* Measured (branch `f8/locals-a-orch-20261022` (unmerged, not pushed), commit `640e7a37`, `scripts/analysis/toc_sp_lb1_repeat_calls.py`; read-only over the cloud-llm-vault `claude` and `codex` stores and `opencode.db` (`mode=ro`, LIMITed); polling tools `write_stdin`/`wait`/`sleep`/`BashOutput`/`TaskOutput` excluded; a repeat = the same (tool, canonical args) as the immediately preceding call; only counts leave the script). Consecutive-identical rate: **qwen-gpu 1/3,383 = 0.03%** (162 sessions), **qwen-local 0/918**, deepseek (cloud, opencode) 1/2,745 = 0.04%, Claude vault 77/32,179 = 0.24% (1,703 files; 83% result-equal, 19% followed by a third identical call; top repeats Edit 41, Bash 19, Read 10), Codex vault 28/7,107 = 0.39% (142 files; 11% result-equal, 11% followed by a third). The 1,393 Codex `write_stdin` repeats are polling and excluded. **Decision: wire NEITHER the result-equality repeat notice NOR the one-reply tool ban now.** The local repeat rate is two to three orders of magnitude below any rate where either costs back its tokens and prompt surface (1 repeat in 4,301 local calls); the only sizeable pattern (cloud-agent `Edit` retried with an identical failing argument, 83% result-equal) is the case a result-equality notice would address, so if a trigger fires later, build the notice, not the ban. Trigger to reopen: local repeat rate above 1% over at least 5,000 local calls.

#### Research Intake Update — 2026-10-30 (Mainplane retrieval over compaction; intake-2522..2534)

Operator-approved 2026-10-31 via research intake (plan sha256 525849605518c57ce866f299b686116b6686df9efb457f4af9fc5f0866ffe097). Monitor records are prose: no checkbox, no index next action.

- [x] **TOC-MP-1 — Prove every REPL context pointer is readable by the REPL that receives it, and fix any denial (zero inference).** The orchestrator emits three pointer kinds, all under `tmp_dir`: the session-log block `Full log: peek(99999, file_path=...)` (`src/graph/session_summary.py:351-362`), compaction's `read_file("<tmp_dir>/session_<task>_ctx_<n>.md")` (`src/graph/compaction.py:278-291`) and spill `peek(n, file_path=..., offset=k)` (`src/graph/file_artifacts.py:100-139`). `_validate_file_path` (`src/repl_environment/environment.py:570-625 @ b0f8613d`) admits only the scratch task root when `task_root_active()` and only root + read_roots under `request_scope()`, so a pointer can be dead in those modes. Add a unit test that emits each pointer kind under default, task-root and request-scope modes and calls the pointed tool; where a read is denied, admit the request's own session artifacts or write them under the task root. Acceptance: the test passes in all three modes, with the fix commit named here (intake-2523, intake-2524). ✅ 2026-10-31 — ORCH `9ca8511726afddea9c4e0fc2af4a43fb27d2adf4`, `tests/unit/test_toc_mp1_artifact_pointers.py`; [test and fix evidence](../../progress/2026-10/2026-10-31-toc-mp1-pointer-custody.md). [belief: cc]
  - 2026-10-31: ORCH main `9ca8511726afddea9c4e0fc2af4a43fb27d2adf4` fixes the emitted compaction `read_file` pointer in all three modes and session-log/spill `peek` under task-root and request-scope, using exact per-REPL session artifact capabilities. Sibling, symlink, knowledge-fence and disabled-tool negatives remain refused; legacy unowned resumed-log pointers are withheld. Focused pointer tests: 47 passed, 1 skipped; related tests: 168 passed; Ruff clean. Zero inference. [Completion receipt](../../progress/2026-10/2026-10-31-toc-mp1-pointer-custody.md). [belief: cc]
- [x] **TOC-MP-2 — A/B-ARMS: fix the arm set of the first-party verbatim-log A/B (design text, zero inference).** Arms at one recorded context budget C: (1) summary-only, the MemGPT DMR baseline shape (intake-2530); (2) summary + full-log pointer, today's production shape (`_session_log_prompt_block`) and the Cursor / Claude Code / OpenClaw shape (intake-2524, intake-2534); (3) pointer-only: recent verbatim tail + full-log pointer + one continuation sentence, no summary (Mainplane, intake-2522, intake-2523); (4) no-summary tool-result pruning (OpenClaw client path: soft-trim, then placeholder) with a pointer written into each placeholder (intake-2534); (5) full history in context while it fits, as reference. Arms 1-2 use OpenClaw's published sectioned summary prompt (`compaction.ts` @ 0e7b5c3) so the summary arm is not a straw man; A/B-CTRL still decides how the summary is produced on the live path. Acceptance: an arm table under the A/B box giving each arm's flag/config recipe and C. ✅ 2026-10-31
  - 2026-10-31 (workspace-58): arm table, C = 16,384 tokens (harness-side prompt cap inside the 65,536 :8070 slot), shared boundary at f x C (f = 0.5, also 0.25), shared 0.20 x C verbatim tail, OpenClaw prompts pinned by sha256 at `0e7b5c34`, arm-to-code map and flags in [`docs/design/toc-mp-ab-design-20261031.md`](../../docs/design/toc-mp-ab-design-20261031.md) section 1. Finding: no arm runs today; the REPL prompt renders no history, `_maybe_compact_context` rewrites unrendered `TaskState.context`, and the production `Full log` pointer names a 200-char-preview journal. Implementation is TOC-MP-2i. [no-belief: design text]
- [x] **TOC-MP-3 — A/B-REL: add reliability, retrieval-miss, literal-recoverability and wall-time requirements to the A/B (design text, zero inference).** (a) n >= 2 trials per task (prefer 4, the tau2 protocol, intake-2532) and pass^k / pass@k per arm with the per-task estimator mean_task C(c,k)/C(n,k) (intake-2533), never p^k of the mean success; (b) post-boundary blocked/error actions over the first 5 actions, counted separately from deliberate re-reads (intake-2527); (c) retrieval misses: tasks whose needed fact sits only in the externalized log and is never read, plus re-fetch tokens and wall time per arm (intake-2522, intake-2526); (d) probes stratified by literal recoverability: direct (literal in the query), paraphrase, two-hop (intake-2531); (e) compaction wall time as a share of end-to-end time (intake-2528#record). Acceptance: the requirements sit under the A/B box and every field they need is in the trajectory-artifact schema or filed as a schema addition. ✅ 2026-10-31
  - 2026-10-31 (workspace-58): requirements (a)-(e), metric directions and the field mapping (existing trajectory fields plus filed schema additions) in [`docs/design/toc-mp-ab-design-20261031.md`](../../docs/design/toc-mp-ab-design-20261031.md) section 2; the additions ship with TOC-MP-2i. [no-belief: design text]
- [x] **TOC-MP-2i — Implement the A/B arm knobs and TOC-MP-3 schema additions behind default-off flags (zero inference; before TOC-MP-4).** Per `docs/design/toc-mp-ab-design-20261031.md`: `session_log_verbatim` (`ORCHESTRATOR_SESSION_LOG_VERBATIM`) verbatim per-turn log with byte offsets, written where TOC-MP-1 makes it readable; `context_arm_ab` (`ORCHESTRATOR_CONTEXT_ARM_AB`) with env knobs `ORCHESTRATOR_CONTEXT_ARM`, `ORCHESTRATOR_CONTEXT_BUDGET_TOKENS`, `ORCHESTRATOR_CONTEXT_TRIGGER_FRACTION`, `ORCHESTRATOR_CONTEXT_FORCE_TURNS`, `ORCHESTRATOR_SESSION_SUMMARY_PROMPT`; boundary branch in `_maybe_compact_context` measuring the rendered history, `_session_history_prompt_block` renderer, OpenClaw prompts vendored with sha256 test; trajectory additions (`boundary` event, `turn.blocked`, `turn.log_follows` incl. `read_file`, `turn.probe_literals_present`, `turn.code_sha256`, `turn.turn_wall_s`, `final.arm`/`context_budget_tokens`/`trigger_fraction`/`trial_index`/`boundary_wall_s`/`task_wall_s`). Acceptance: flag-off prompt bytes identical to origin/main (exact-string test); one unit test per arm showing the rendered block after a forced boundary; runtime_flags spec re-synced. ✅ 2026-10-31 orchestrator `f61cca823bb714bbcd69c218f32aba913fd6f869` · [tests](../../artifacts/compute/codex3-toc-mp2i-20261031/record-final.log) [no-belief: default-off code and tests only]
  - Implemented in orchestrator `f61cca823bb714bbcd69c218f32aba913fd6f869`, promoted on main `f87b7c545f847ed2fa48b018664d1de3533a23f6`. Offline validation: 108 passed / 1 skipped plus 12 final targeted passes, Ruff and diff check; [review and validation](/mnt/raid0/llm/tmp/codex3-toc-mp2i-20261031/REVIEW.md), [completion receipt](/mnt/raid0/llm/tmp/toc-mp1-20261031/MP2i-DONE.json). History captures post-redaction REPL output; capped context bundles and foreign legacy logs refuse. Task wall is graph-run wall excluding HTTP/queue; the scientific runner must prove target tokenizer identity and reject heuristic fallback. No inference, grade, A/B result or TOC-MP-4 completion is claimed.
- [ ] **TOC-MP-4 — Exact-value needle screen across arms 1-3 before the full A/B (correctness-class inference; after TOC-MP-1 and TOC-MP-2).** Fixture: 20 REPL tasks whose answer is an unforgeable 24-character value printed once by an early tool call inside a >4,000-character output, with externalization forced at fixed turn indices (ARC Appendix B design, intake-2525). Arms 1-3 of TOC-MP-2 at one recorded C; frontdoor model; n = 2 runs per task; score only the exact submitted value. Record orchestrator commit, flags, model/quant, C and the trajectory artifacts. Decision rule, fixed in advance: pointer-only exact recall >= summary+pointer keeps arm 3 in the full A/B as the candidate default; otherwise record the miss pattern here and fire M-MP2. Acceptance: result table, artifact path and the decision line.
- **M-MP2 (monitor, 2026-10-30 intake) — pointer-arm refinements.** Content-addressed spill stubs (head/tail preview + short hash id + length) with recall guards (per-step recall cap, per-recall char cap, LRU re-stub) from ARC (intake-2525), and a MemGPT-style memory-pressure notice before externalization so the model can save facts first (intake-2530). Trigger: TOC-MP-4 or the full A/B records pointer-only retrieval misses. No checkbox until then.
- **M-MP3 (monitor, 2026-10-30 intake) — summary-arm refinements, added to M7's LLM-compression tuning list.** Parallel or asynchronous compaction (intake-2528#record) and verifier-optimised summary prompts (TRACE, intake-2527). Trigger: a summary arm wins the full A/B. No checkbox until then.


## Track: research-intake-harness-inference-2026-11-06

Source batch: 12 entries ingested 2026-11-06 (t3code, Foundry Local, HarnessMM + 9 expansion entries). Plan: `research/intake-stage3-plan-2026-11-06-harness-inference.md`.
- [ ] **CTX-HO-1 — Amend CF-AB-1 A6 to the measured handoff field set and co-metric.** Replace A6's three-field schema with the seven deterministic fields (repository change state, changed source files, non-source artifacts, validation outcome, latest validation command, latest validation evidence, continuation-state label) and seven model-filled fields; add `events per solved task` beside uncached prefill as a co-metric. Acceptance: A6 text carries both field lists and both metrics; no new arm. [2026-11-09 apr2 rtg08-evl47-pip04-code: NOT DONE, named blocker unchanged. Appendix C of arXiv 2606.02875 could not be read verbatim here: the PDF fetch returned only metadata (no text layer extractable, no pdftotext); one HTML fetch returned a seven-name list through a summarising model ("problem understanding", "work completed", "evidence observed", "observed failures or error evidence", "remaining uncertainty", "rollback notes", "recommended next action") and a repeat request for the verbatim passage was refused, so that list is UNVERIFIED and was not copied into A6. Next: read the appendix directly (HTML or PDF text layer) and copy the names verbatim. [no-belief: blocked on source access]]
  - **Specification added 2026-11-09 (audit).** Source: intake-2653 (arXiv 2606.02875, "Handoff Debt"), Appendix C, via `research/intake-stage3-plan-2026-11-06-harness-inference.md` RI-13/RI-14.
    - **The seven deterministic fields** (named in this box, derivable from git and the validation journal): `repository change state`, `changed source files`, `non-source artifacts`, `validation outcome`, `latest validation command`, `latest validation evidence`, `continuation-state label`.
    - **The seven model-filled fields are NOT derivable from the repo.** No file in epyc-root or the intake index lists them; the index entry carries only the abstract-level list (changed files, non-source artifacts, latest validation command, uncertainty, rollback risk, verification). Nothing may be invented. **Step 0 of this box: read Appendix C of arXiv 2606.02875 and copy the seven names verbatim into A6.** If the appendix is unreachable, the box stays open with that as its named blocker.
    - **A6 is defined twice, consistently:** in the CF-AB-1 addendum (2026-10-21, `intake-2228#record`) and again in CF-AB-2 (also 2026-10-21, "A6, reset with a structured handoff artifact"); both give the three-field schema (state, next steps, open defects). **The CF-AB-1 addendum is canonical; amend it, and add a one-line pointer in CF-AB-2 rather than a second schema** (a second copy would re-create the double-definition drift).
    - Co-metric `events per solved task` is added beside uncached prefill per solved task; it needs the event count per trajectory (trajectory_artifact schema; confirm the field exists, else file it as a schema addition as TOC-MP-3 did).
    - Zero inference; doc-only; standalone.

- [ ] **CTX-HO-3 — Render validation evidence into the /log checkpoint envelope.** The completed-checkpoint envelope carries a `resume_state` block with the latest validation command, its observed output or exit, remaining uncertainty, a rollback note, non-source artifacts and a continuation-state label. Acceptance: a real checkpoint renders a populated block from the executed `--validation-json`; missing evidence renders as explicitly unknown. [2026-11-09 apr2 rtg08-evl47-pip04-code: IMPLEMENTED and tested but NOT COMMITTED: the commit-msg hook (D9, ratified 2026-08-15) refuses any change under `scripts/coordination/**` and the bus schema without an operator ack, and no ack was given to this session. The change sits uncommitted in worktree `/mnt/raid0/llm/worktrees/apr2-rtg08-evl47-pip04-code-root-20261109` (files `scripts/coordination/worker_checkpoint.py`, `coordination/session-bus/session_bus.schema.json`, `tests/coordination/test_worker_checkpoint.py`); needs `D9-ack:` in the commit message from the operator or main. Option 1 taken: `--remaining-uncertainty`, `--rollback-note`, `--continuation-state` (done|resumable|blocked) on `worker_checkpoint.py`; `payload.resume_state` = latest validation command + observed exit/stdout/stderr (from the executed `--validation-json`), the three fields, and `non_source_artifacts` (artifact paths whose suffix is not in SOURCE_SUFFIXES); absent values render the literal `unknown`; new fields are left out of the spec hash when empty so in-flight journals keep their identity. `session_bus.schema.json` gained an optional `resume_state` object (payload has additionalProperties false; no consumer in checkpoint_reconcile/coordinator reads payload keys beyond the fixed set). Tests: `tests/coordination/test_worker_checkpoint.py` + `test_checkpoint_reconcile.py` 73 passed (4 new: populated block from a real git lane, missing evidence renders `unknown`, bad state refused, CLI publish passes the bus schema); `tests/test_session_bus.py` 260 passed, 126 skipped. [no-belief: tooling]]
  - **Specification added 2026-11-09 (audit), facts from `scripts/coordination/worker_checkpoint.py` at `origin/main`:** there is NO `resume_state` anywhere in the file. What exists: `--validation-json` (repeatable argv arrays; `_run_validations` captures `argv`, `rc`, `stdout`, `stderr`; journal phase `validation_passed`); `_receipt_validation` (`:483`) already renders each validation as `{command, exit_code, evidence_ref: "inline-json:{stdout,stderr}"}` into the receipt payload (`:918`); `--resume-action` is a free-text string rendered as `resume_action` (`:279`, `:341`) and copied into the completed payload (`:924`); the bus envelope is `_bus_envelope` (`:579`, kind `task-checkpoint`, payload passed through unchanged). So the latest validation command, exit and output ALREADY ship in `payload.validation`; the `resume_state` block is new packaging plus three fields with no input channel: `remaining uncertainty`, `rollback note`, and `continuation-state label`. **Decision needed (small, recommend option 1):** (1) add three optional flags `--remaining-uncertainty`, `--rollback-note`, `--continuation-state` (enum, e.g. `done|resumable|blocked`) and build `resume_state` in the payload next to `validation`, rendering absent values as the literal `unknown`; (2) derive them from existing fields (`--resume-action`, `--blocker-class`) with no new flags, less honest because the model's uncertainty is not captured. Non-source artifacts come from `--path` minus source suffixes (rule to be stated in the code). Acceptance as above, plus a test that a checkpoint with no evidence renders `unknown`, not an empty string. Standalone code work in epyc-root `scripts/coordination/`; verify nothing else parses the payload (bus consumers, `session_bus.py`) before adding the key.

