# Context-Folding: Progressive Session Compaction Upgrade

**Status**: refreshed 2026-07-14 - core context-folding phases landed; active only for L5/Phase 3c validation and design probes. The 2026-06-19 alpha sweep is now decision-scoped: promote the dual-objective score into the Phase 2b design variant, but do not change production compaction behavior without live/held-out validation.
**Created**: 2026-03-17
**Updated**: 2026-06-13
**Priority**: HIGH
**Categories**: context_management, session_compaction, rl_training_data
**Parent index**: [routing-and-optimization-index.md](routing-and-optimization-index.md), [research-evaluation-index.md](research-evaluation-index.md)
**Completed ledger**: [context-folding-progressive-completed-through-2026-05-28.md](../completed/context-folding-progressive-completed-through-2026-05-28.md)

## Executor Start Here

Do not reimplement Phases 0, 1, 1+, 2a, 2b L1-L4, 2c scaffolding, 3a, or 3b. The active question is whether the remaining aggressive-compression and monitoring probes justify new behavior beyond the already-landed multi-tier compaction stack.

## Outstanding Tasks

- [ ] **CF-L5 maximum-compression validation**: run the L5 single-sentence-per-segment compression check only if it answers a current production question. Compare against the known L3 sweet spot and record whether L5 is rejected, role-limited, or worth further tuning.
- [ ] **CF-3c live quality-monitor validation**: validate `CompactionQualityMonitor` on real traffic/telemetry. The class scaffold exists; tune degradation thresholds only after upstream-compressor anti-thrashing in [tool-output-compression.md](tool-output-compression.md) Phase 3d is accounted for.
- [x] **CF-2c.0 / NIB2-43 dual-objective alpha sweep**: implemented an offline retrieval proxy in `epyc-inference-research` `scripts/benchmark/compaction_alpha_sweep.py` and scored existing Package-C compaction/summarizer rows at alpha values `{0.0, 0.25, 0.5, 0.75, 1.0}`. Result artifacts: `data/research/2026-06-19-compaction-alpha-sweep/alpha_sweep.{json,csv}`. On 110 valid rows, alpha `0.0` beat faithfulness-only alpha `1.0` by `+0.051315` average precision (`0.940463` vs `0.889148`) and improved ROC-AUC (`0.743056` vs `0.534420`), crossing the `>2%` promotion gate. This is still a proxy result, not a deployment decision: promote dual-objective scoring into the Phase 2b design variant, then require a live/held-out validation before changing production compaction behavior.
- [x] **CF-2c.1 alpha-promotion decision scope**: existing evidence is sufficient to promote the dual-objective score into the Phase 2b design variant only. The remaining blocker is specific and non-inferential: do not flip live production compaction behavior until a live/held-out validation artifact exists. ✅ 2026-07-14

## Decision Record: CF-DD8 / NIB2-40

**Closed 2026-06-13**: do not add a separate context-folding implementation for Claude Code-style "budget reduction" right now. The concrete per-message cap surface found in the local docs is tool-output scoped, and EPYC already has explicit ownership there via [tool-output-compression.md](tool-output-compression.md): `truncate_output()` provides an 8192-character hard cap, `_spill_if_truncated()` limits visible previews and preserves full output by pointer, and the native compression layer sits before spill/truncation.

Layer mapping:

| Claude Code layer | EPYC owner / state | Decision |
|---|---|---|
| Budget reduction | [tool-output-compression.md](tool-output-compression.md) for tool outputs; REPL token-budget knobs for generation budgets | No new CF-owned cap. Keep caps/compression/spill in the tool-output lane. |
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
| CF-3c telemetry is noisy due to compress/uncompress oscillation | Sequence after [tool-output-compression.md](tool-output-compression.md) Phase 3d anti-thrashing work. |
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
- [tool-output-compression.md](tool-output-compression.md)
- [routing-intelligence.md](routing-intelligence.md)
- [non-inference-backlog.md](non-inference-backlog.md)

## Reporting Instructions

After any CF task, update this active handoff with command, dataset/log source, metric direction, result, and the fork decision. Update [routing-and-optimization-index.md](routing-and-optimization-index.md), [research-evaluation-index.md](research-evaluation-index.md), and [non-inference-backlog.md](non-inference-backlog.md) if task ownership or priority changes.

## Research Intake Update — 2026-07-21 (Seven-policy bake-off — and a corrected reading of it)

- **[intake-869] "Diagnosing and Mitigating Context Rot in Long-horizon Search"** (arxiv:2606.29718; GAIR/SJTU, Pengfei Liu) + code release `github.com/GAIR-NLP/ContextRot`
  - Relevance: supplies the **comparative ablation CF-3c lacks** — seven context-management methods across three families (compaction/summarization, trimming/discarding, isolation/sub-agents) on one common harness and model set. Distinct from intake-273 (Chroma), which is static single-turn; this is multi-turn self-accumulated agentic context.
  - Headline as published: keep-latest+summary lifts BrowseComp 35.0 → 48.2 (+13.2pp) and cuts rot rate 53.4% → 16.2%.
  - **CORRECTED READING — use this, not the headline.** Their own table shows keep-latest ALONE at 43.8% and plain Discard at 44.6%. So **observation-dropping carries ~9pp of the 13.2pp and summarization adds only 3.6-4.4pp.** And FoldAgent actually scores *higher* on accuracy (54.0%) than the declared winner. This is quantitatively close to intake-274 (The Complexity Trap), which found masking ≥ summarization on SWE-bench across five configs at lower cost, with a 13-15% trajectory-elongation penalty from summaries.
  - **Practical read for CF-3c:** treat "drop stale observations" as the robust cross-domain result and "add LLM summarization on top" as a domain-specific, small, cost-negative-until-proven addition to be A/B'd rather than assumed.
  - The most durable takeaway is not the policy ranking at all: it is the **behavioral failure mode**. Rot presents as give-up / hedged-uncertain answers, and our compaction telemetry currently tracks reference misses, not refusal/hedging. A rot-rate move 53.4% → 16.2% is a far sharper signal than the accuracy delta.
  - Caveats: BrowseComp is a 100-sample split (a 4.4pp gap ≈ 4 questions — our per-suite gate-resolution caveat applies); the model-dependence claim is n=2; the 98.7% judge-agreement figure lacks chance correction (see intake-876); live-web contamination may account for up to 4pp (intake-877). All numbers are OBSERVATIONS under MEASUREMENT.md.
  - Usable asset: the harness talks OpenAI-compatible endpoints and its **local-search arm (BrowseComp-Plus + embedding retrieval) is self-hostable against our BGE servers** — the cheapest path to re-measuring under our own protocol.

- [x] CF-3c design input: frame the compaction A/B around the seven-policy ablation, prioritizing observation-dropping and treating summarization as the marginal arm to be justified, not the default. ✅ 2026-07-29 — **corrected to match the live path:** `ContextCompressor` performs deterministic type-aware stubbing only; `openai_compat.py` consumes that result directly and no caller invokes an LLM summarizer. The first runnable comparison is therefore `no compaction` versus protected-zone deterministic stubbing, with the threshold pre-registered; an LLM-summary arm is a separate future feature, not a currently available control. [intake-869, intake-274]

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
holds the host.
- [ ] CF candidate: add give-up-rate and uncertain-incorrect-rate as compaction-quality dimensions alongside reference misses. [intake-869]
- [ ] CF candidate: the `keep_k_latest_wo_reasoning` arm is a direct cheap test for the retain-historical-thinking-blocks question owned by [reasoning-compression.md](reasoning-compression.md). [intake-869]

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

**6. Our stack is already past the paper's baseline.** `build_granular_summary` retains a **60-character** output preview per turn — we never keep raw observations. And `src/context_compression.py` already implements a keep-latest-8-with-summary hybrid (`TOOL_OUTPUT_AGE_THRESHOLD = 8`, `summarize_tool_output()` stubbing file reads/REPL while keeping errors verbatim, protected-zone first-3/last-5). A seven-policy bake-off would mostly re-derive a design we have already committed to.

- [x] **Fix the inverted detector (one line, highest value here) ✅ 2026-07-29**: implemented by epyc-orchestrator `921f71d1` in `src/graph/session_summary.py`, with regression coverage in `tests/unit/test_session_summary.py`; the completed duplicate is recorded below.
- [ ] Persist `CompactionQualityMonitor` (add to the state projection at `graph/langgraph/state.py:207` + a writer) — currently dies with the session.
- [ ] Add give-up-rate AND **no-answer / max-turns rate** as production dimensions. Detectors already exist in `src/pipeline_monitor/anomaly.py` (`detect_repl_max_turns` = the paper's NA exactly; `detect_assistant_help_request` ≈ give-up; `detect_self_doubt_loop` ≈ hedging) — the work is joining them to compaction state, not writing them. Scope **uncertain-incorrect to the eval tower only** — it needs a correctness label that does not exist in production.
- [ ] Replace the seven-policy bake-off with the narrower question our code actually poses: does
  protected-zone deterministic stubbing beat no compaction, and what is the right
  `TOOL_OUTPUT_AGE_THRESHOLD`? That is the A0/A1(k) sweep above. An LLM-summary arm requires a
  separately implemented component and is not an existing-code comparison.
- [x] Do NOT prioritize running the ContextRot harness. ✅ 2026-07-29 — current Stage-2 evidence confirms the only self-hostable arm (BrowseComp-Plus) has a ~1pp-or-negative summarization effect; its paid `SERPER_API_KEY` and missing license also fail the open-source-only constraint. If reopened, reproduce only the behavioral rot/NA signature, never the underpowered accuracy delta.
- [x] **Self-hostable/BGE correction recorded ✅ 2026-07-29**: the shipped embeddings are Qwen3-Embedding-8B-specific (4096-dim, 821MB, bf16); using BGE would require re-embedding all 100,195 docs and would break comparability. Source-backed intake/deep-dive correction: epyc-root `2102c0f05`.

### Ownership clarification — 2026-07-21 (this is orchestrator work, not inference-research)

The rot ↔ no-answer finding and the compaction-telemetry fixes are **orchestrator-side**, not inference-research, and need no quiet window or inference budget:

- The instrument is `CompactionQualityMonitor` (`src/graph/session_log.py:563`) and its call site `src/graph/session_summary.py`, both orchestrator code.
- The give-up / no-answer detectors already exist in `src/pipeline_monitor/anomaly.py` (`detect_repl_max_turns` = the paper's NA metric exactly, `detect_assistant_help_request` ≈ give-up, `detect_self_doubt_loop` ≈ hedging). The work is joining them to compaction state and persisting the result — plumbing, not measurement.
- Nothing here requires llama.cpp, a kernel build, or a benchmark slot. Validating that the telemetry *moves* would require agent traffic (autopilot), but that is orchestrator-level and can ride normal operation rather than a reserved inference window.

The one genuinely inference-adjacent item is the optional ContextRot harness replication, which is already marked do-not-prioritise above (self-hostable arm is the low-signal one, ~25-50h/arm, underpowered at achievable reps).

- [x] Fixed the inverted reference-miss detector (`session_summary.py`) to compare identifiers destroyed by compaction — present in `seg.granular_blocks`, absent from the surviving stub — rather than identifiers read off the stub itself. Two regression tests added that fail against the prior behaviour in both directions (missed real loss; false positive on preserved content). ✅ 2026-07-21

### Audit catch 2026-07-21 — the fixed detector is DEAD CODE until the flags flip

The inverted-detector fix (`epyc-orchestrator 921f71d1`) and the persistence task above are both inert while `role_aware_compaction` AND `helpfulness_scoring` remain `FeatureSpec(..., False, False, ...)` (`features.py:152,154`). No enable task existed — the "highest-value one-line fix" currently executes zero times in production.

- [ ] **Enable decision (operator): flip `role_aware_compaction` + `helpfulness_scoring` on in SHADOW** — monitor-only, no behavior change: the compaction path they gate already runs; the flags only govern whether quality telemetry is recorded. Without this, CF-3c has no instrument and the detector fix cannot be validated against real traffic. If deliberately deferred, record why here so the dead-code state is a decision rather than an accident.

## Research Intake Update — 2026-07-29 (CF-3c: the masking anchor neither ACM nor AREX ran)

_Via `/research-intake` Stage-2 2026-07-29 (intake-913…932 batch): ACM (intake-914), AREX (intake-922), PRO-LONG (intake-919). Sibling filings in [tool-output-compression.md](tool-output-compression.md) (verbatim-log A/B, total-token instrumentation, `query_memory` over spill pointers)._

- [ ] **Add an observation-masking / truncation arm as the MANDATORY anchor for CF-3c.** Neither ACM (intake-914) nor AREX (intake-922) ran one — verified in both papers **and in ACM's released code**. Without it no learned-compression result we produce is interpretable either. Our own intake-274/869 already hold that masking carries most of the benefit.
- [ ] Add **ACM Base** as the agent-initiated-trigger arm against threshold-triggered compaction. Scope it as FOUR pieces, not a tool schema: `manage_context` / `query_memory` JSON schemas, a memory-tools system prompt, an in-band `[CURRENT CONTEXT TOKEN: N]` meter injected into the last tool message each turn, and a summarizer/querier call path. **Without the meter the agent cannot self-trigger.**
- [ ] Run ACM's own UNREPORTED ablation (`runtime.py disable_query_memory`, the `re_mem_noquery` arm) — isolates the value of the lossless archive from the compression policy. Implemented in released MIT code; the authors omitted the result.
- [ ] Pair any adoption with the **non-termination counter this handoff already mandates** (see the 2026-07-21 deep-dive correction, item 4). ACM reports none; AREX structurally cannot — budget exhaustion silently returns the highest-confidence answer instead of an NA.
- [x] Record that AREX's **+11.8pt ACU figure is NON-CITABLE** ✅ 2026-07-29 — verified in committed intake-922 Stage-2 evidence (`epyc-root` `683f70de`, `research/intake_index.yaml` Claim 10): no masking anchor; no observation-dropping vs learned-summary arm; and the `w/o ACU` arm removes a tool the model was trained to call. It must not transfer to CF-3c as a capability figure.
- [ ] Record the **ARC-AGI-3 provenance downgrade for intake-919**: all PRO-LONG numbers are on the **public set**, which the benchmark authors state is "emphatically not a valid measure of progress" and will "never" appear on their leaderboard; PRO-LONG is to high confidence the ARC-sponsored Duke harness, which those authors measured showing extreme bimodality (97.1% / 0.0%). Keep the internal ablations; discount the SOTA framing.

**Dedup / conflation hazard — `arXiv 2607.21503` is NOT ACM.** It is a **different paper from the same week with a near-identical title** to intake-914's source. Anyone re-fetching ACM by title will land on it. Check the arXiv ID, not the title, before citing anything as ACM evidence in this handoff.
