# Benchmark Methodology

**Category**: `benchmark_methodology`
**Confidence**: inferred
**Last compiled**: 2026-07-31 (adds three methodology results from the vision-role evaluation: a saturated suite can order arms WRONGLY not just fail to separate them; an output-length cap silently penalises reasoning models; a model with no draft path running unaccelerated is at its OPTIMUM, never a BASELINE — the concrete case the OPTIMUM/BASELINE/CANDIDATE grammar was ratified to prevent; earlier 2026-07-30 note: MEASUREMENT v2 ratified: core + annex constitution, explicit metric scoping, P-BENCH-PLACEMENT-1 registered, P-BENCH-3 conformed, retracted April exemplar replaced; prior E8/E5 status update retained)
**Sources**: 100+ documents

## Compiled Update — 2026-07-31: a saturated suite can rank arms wrongly, an output cap can silently fail reasoning models, and "no draft path" is an OPTIMUM not a BASELINE

**Confidence: verified** — the vision-suite comparison and the truncation counts are direct
measurements with persisted artifacts; the OPTIMUM/BASELINE/CANDIDATE grammar is an operator-ratified
constitutional amendment.

### A saturated benchmark can order arms WRONGLY, not merely fail to separate them

The earlier 42-question OCRBench+ChartQA vision suite (used through 2026-07-30 to evaluate
`vision_escalation` candidates — see [Multimodal](multimodal.md)) placed the incumbent Qwen2.5-VL-7B
**2nd**; the same-day 250-question MMMU val run placed it **last**. Qwen3-VL-8B **inverted** between
the two suites as well. This is a stronger claim than the standing "saturated benchmarks fail to
separate arms" caution: **a saturated suite can order arms in the wrong direction**, so a decision
taken on it is not merely under-powered — it can be actively backwards. The 42-question suite is
retired for ranking purposes; MMMU val (250 stratified questions, identical rows per arm) is the
instrument now used for this role. [Multimodal](multimodal.md) carries the full vision-role decision
this methodology finding gates.

### An output-length cap silently penalises reasoning models

The same vision evaluation ran a production `max_tokens=128` cap that produced **3** parse failures
for the incumbent versus **41** and **50** for the two Qwen3-VL candidate arms — the reasoning models
were being truncated mid-reasoning and scored as wrong, not as genuinely incorrect. Raising the cap
to `max_tokens=2048` still leaves those models emitting no letter on **~9%** of hard questions. The
generalizable rule: an output-length cap tuned for a non-reasoning incumbent is not a neutral
harness parameter when a reasoning-capable candidate is added to the same suite — it becomes a
hidden thumb on the scale that specifically penalises the newer arm. The vision role's production
config now requires `max_tokens ≥ 1024`.

### A model with no draft path running without speculation is at its OPTIMUM, not a BASELINE

Separately, a spec-decoding headline table wrongly excluded Qwen3-Next-80B on the reasoning that it
was "unaccelerated," i.e. treated its `--spec-type none` run as a non-production baseline rather than
what it actually is: the best configuration available for a model that has no draft path at all.
This is the concrete case that motivated an operator-ratified amendment to `MEASUREMENT.md` (`epyc-root`
`0b92049e`, 2026-07-31): the §3 claim grammar now requires every reported measurement to declare
`category=OPTIMUM | BASELINE | CANDIDATE`, with an explicit rule that **if no draft path exists, the
unaccelerated run IS the OPTIMUM** and belongs in the headline table, never in a baseline addendum.
§5 was amended in parallel: **promotion is decided on the production-optimal configuration alone**,
a `BASELINE`-category regression is not a promotion blocker and must not be cited as one, and a gate
that blocks on a non-production arm is defective and must be repaired, not waived. This directly
narrowed `bench-cpu.md`: its 28 `llama-bench` prefill cells could previously veto a kernel whose
*production* throughput had improved, even though `llama-bench` cannot exercise speculative decoding
at all and so never measured the production recipe in the first place — those cells now record and
report but do not block. The agent digest (`agents/shared/MEASUREMENT_POLICY.md`) gained the
category rule it had entirely lacked before this amendment.

**Open governance question, unresolved as of this compile**: `MEASUREMENT_POLICY.md:79` states
amendments are human-PR-reviewed, while `MEASUREMENT.md`'s trust-boundary membership (§5, "read-only
for autonomous optimization processes") does not name the digest itself. As written, it is not
determinable whether an agent may edit the digest. Needs an operator ruling.

### Source References

- [`progress/2026-07/2026-07-31.md`](../progress/2026-07/2026-07-31.md) — §15a (the 42q-vs-MMMU ranking inversion and the `max_tokens` truncation counts), §18 (the MEASUREMENT.md ratification summary), §20 (the "OPTIMUM not BASELINE" process lesson naming Qwen3-Next-80B)
- [`MEASUREMENT.md`](../MEASUREMENT.md) — §3 the OPTIMUM/BASELINE/CANDIDATE claim grammar (with the Qwen3-Next-80B `--spec-type none` exemplar), §5 the production-optimal-alone promotion rule and the `bench-cpu.md` narrowing, CHANGELOG entry dated 2026-07-31
- [`multimodal-pipeline.md`](../handoffs/active/multimodal-pipeline.md) — task V-1 (the suite mis-ranking) and S-15 (the `max_tokens ≥ 1024` production-config task)
- [Multimodal](multimodal.md) — the full MMMU vision-role decision this section's methodology findings gate

## Compiled Update — 2026-07-30 the constitution restructured, and a placement protocol born from a defect

MEASUREMENT.md v2 was operator-ratified (apply 20260730T103218Z): a lean core
constitution plus three protocol-family annexes under `measurement/protocols/`,
all inside the same human-only trust boundary (`human_only_paths.yaml` extended
and re-pinned). Confidence: `verified` — the ratification receipts, the delta
ledger, and the same-day conformance amendment are all in-repo.

### Key Findings (2026-07-30)

- **Metric scoping is now explicit (§1)**: `task_rate` is the autopilot-objective
  axis and the only speed metric where tokens aren't commensurable across arms;
  tokens/s is the instrument-level, fully decision-grade metric for model/kernel
  benches. v1's "t/s is telemetry only" was always scoped to the autopilot
  objective — v2 says so. Same-day lesson: a new scoping section over legacy
  protocol cards needs a reconciliation pass — P-BENCH-3's carried-over tasks/h
  mandate contradicted §1 until a conformance amendment (found by a parallel
  session, verified, ratified) made tok/s primary with tasks/h as a secondary
  orchestration readout, never the ranking key.
  [MEASUREMENT.md](../MEASUREMENT.md)
- **v2 fixed a governance inversion**: two operator-ratified 2026-07-27 policies
  (deterministic replay before regeneration; consolidated apply-time
  ratification) lived only in the agent digest while the constitution — whose
  own rule is "the constitution wins" — never absorbed them. The stale era-table
  copy (missing E4-qcore/E6/E7/E8) was replaced by a pointer to the append-only
  registry, and the phantom claims-grammar validator was built for real
  (warn-mode, diff-scoped).
  [RATIFICATION_LEDGER](../artifacts/operator/measurement-v2-draft/RATIFICATION_LEDGER.md)
- **P-BENCH-PLACEMENT-1 exists because every other protocol was satisfied while
  production served at a fraction of canonical speed** (the 2026-07-30 NUMA
  placement defect): placement — CPU affinity, NUMA memory policy, mmap mode,
  instance count, slot concurrency — was an axis P-BENCH-1/2/3 simply did not
  constrain. Its gates encode the day's hard lessons: first-touch-only
  interleave makes warm re-tests silently re-measure the previous arm's
  placement; shared mmap places pages once for the whole fleet (start-order
  dependence); a wall-clock rate is never a decode rate; every arm runs the
  production acceleration recipe.
  [bench-cpu annex](../measurement/protocols/bench-cpu.md)
- **Exemplars are claims too.** The §3 grammar exemplar (`27.06 t/s`, April) was
  retracted on evidence — it predated the NPS4 reboot and its source CSV was a
  spec-off baseline posing as a production figure — and replaced by a
  production-recipe P-BENCH-PLACEMENT-1 figure with the retraction preserved
  inline as an append-style comment.
  [ratify_p_bench_placement_1_v2.sh](../artifacts/operator/ratify_p_bench_placement_1_v2.sh)

## Compiled Update — 2026-07-29 two campaigns that have produced instruments, not results

Two of the project's largest open campaigns reached a state that is easy to
misread, so this entry states it first and plainly.

**E8 has no baseline signature.** No E8 quality baseline has been collected in
full, applied, or published. Everything landed between 2026-07-27 and 2026-07-29
is instrument repair, provenance plumbing, and publication hardening — every
entry says so in its own words ("evidence checkpoint only", "instrument repair
only", "instrument/integration checkpoint only", "publication-path hardening
only"). **E5 has no decision-grade cell.** Its Stage-B waves W1-W4 are blocked on
an operator-scheduled reboot, so the W0 scout numbers remain the only E5 data and
remain observation-grade.

Confidence: `verified` for the campaign *status* facts, the landed instrument
work and its test counts, and the methodological rules below — all read directly
from the owning handoffs. No performance or quality conclusion is promoted here,
because neither campaign has produced one.

### Key Findings (2026-07-29)

- **The E8 numeric half is complete; the quality half is not, and the two are
  routinely conflated.** Numeric frontier accumulation reached its exact-stop
  boundary `16/16/0` at trial `1458` on 2026-07-27 (trial `1459` never dispatched;
  trial `1457` was terminated pre-admission when an external GitNexus process
  overlapped its eval and is recorded as `autopilot_killed_mid_trial`); the
  authoritative journal fold has 16 eligible entries and reconstructs a three-point
  frontier. On the quality side only the **T1 tier** is terminal — v5 T1/r1, r2 and
  r3 each `50/50` with 25 correct and zero final errors, recorded as E8/`core_v2`
  `e8_quality_full_pool_tier_baseline.v4`, `n=50`, `q=1.5`. That is an evidence
  checkpoint; it neither applies nor publishes a baseline. T2 collection has not
  completed. [autopilot-decision-plane-audit](../handoffs/active/autopilot-decision-plane-audit-2026-07-22.md)

- **Deterministic replay before regeneration was applied under pressure and held.**
  T1/r3 ordinal 32 hit a scorer-side `ReadTimeout`; the protocol repaired it with
  exactly one deterministic scorer-tail replay, **without regenerating inference**,
  and the terminal row carries `error: null`. The same rule governs the open work:
  "do not run new generation before deterministic replay of saved outputs is
  exhausted." [autopilot-decision-plane-audit](../handoffs/active/autopilot-decision-plane-audit-2026-07-22.md)

- **A scorer that shares mutable execution state across invocations produces
  divergences that look like model behaviour.** An E8 completion attempt correctly
  *refused admission* because ordinal `418` / `bcb_BigCodeBench/190` had a stored
  verdict of `false` while deterministic re-scoring returned `true`. Root cause:
  BigCodeBench code execution shared `/mnt/raid0/llm/tmp`, so concurrent
  invocations collided on the same `test.db` — meaning **the stored `false` has no
  execution witness at all**. The remedy is ordered, not parallel: integrate scorer
  isolation (private per-invocation workspaces) *first*, then the replay successor,
  and only then run a bounded retry. Any correction ledger must bind source bytes,
  scorer source hashes, per-row before/after verdicts, and corrected sidecars.
  [autopilot-decision-plane-audit](../handoffs/active/autopilot-decision-plane-audit-2026-07-22.md),
  [progress 2026-07-29](../progress/2026-07/2026-07-29.md)

- **Failed evidence is preserved immutably and classified as ineligible, not
  deleted or quietly retried.** Two E8 successor namespaces are kept on disk as
  failures — one a wrong-request attempt with no valid collection, one where all six
  c1 requests completed but the run correctly failed closed at `RACE.build_plan`
  because its predecessor journal response differed from the sealed EvalTower
  sidecar. Abort paths terminalize as *ineligible audit evidence*. The earlier v4
  collection is likewise labelled historical, non-decision evidence after the
  fixed-vector context defect.
  [autopilot-decision-plane-audit](../handoffs/active/autopilot-decision-plane-audit-2026-07-22.md)

- **An instrument can be extensively hardened and still not be signable.** The E8
  chain accumulated large validated test counts across the window (322 tests on the
  integrated remediation checkpoint, 325 on the race-retry publication hardening, 202
  on the independent Tier-A re-audit that verified all six original fail-open findings
  closed), yet the consolidated ratification wrapper carries an explicit
  **FIX-FIRST — do not sign as pushed** verdict for mechanical reasons: a branch tip
  that is not self-consistent with its own checkout, an add/add-conflicting divergence
  from main, and a validator that cannot validate the segmented resume provenance the
  live collection actually produces. Test count is not signability.
  [autopilot-decision-plane-audit](../handoffs/active/autopilot-decision-plane-audit-2026-07-22.md),
  [gpu-serving-tie-in-program](../handoffs/active/gpu-serving-tie-in-program.md)

- **E5's grading discipline survived the pause, including the parts that are
  inconvenient.** W0 ran under `--allow-host-health-warning` at 20-day uptime and is
  scout/non-decision **by design**; the operator-facing results artifact leads with an
  observation-grade banner and the handoff instructs that when decision-grade results
  land the banner must be *rewritten* (not just the numbers), that the W0 figures must
  be **retained alongside** rather than edited to agree, and that the artifact must be
  republished to the same URL. W0's Gemma group is separately unusable for quality —
  430/430 parse failures with no raw SSE ledger, unrecoverable — and a focused post-fix
  capture smoke must pass before any decision-grade W2 run. The cause was
  **re-attributed 2026-07-29** (research `5d6a17f2`): the capture parser bug was real
  and is fixed, but what consumed the budget is that the harness emitted no
  `--reasoning` flag, so gemma4 ran at llama-server's `auto` default (ON for
  `arch=gemma4`) while both model registries record `reasoning: 'off'` — W0/W2 were not
  running the production recipe they exist to mirror. A re-run smoke reproduced it:
  41/43 `response_capture_missing_answer_text`, every one HTTP 200 with `predicted_n`
  exactly 256, empty `response_text` and 599–1174 chars of `reasoning_text` ending
  mid-sentence, against a clean llama-server log. The capture fail-close **detects**,
  it does not **prevent**; without `--reasoning off` a W2 run fails closed again at
  ~41/43.
  [batched-decode-measurement](../handoffs/active/batched-decode-measurement.md)

- **Decision-grade and deployable are different states, and the record now says which
  it means.** The FG-4b A4 CPU re-anchor is `decision_grade=true` *and*
  `proposal_only=true`: 13.1599 tok/s median over five exact 512-token server decodes
  with a ratified affinity receipt, and a generated registry patch that was
  deliberately **not applied**. Similarly, the G3 saved-output replay closed with zero
  mismatches across five 48-item arms but is recorded as observation-only with a
  32,768-vs-16,384 context confound and no deployment, lineup, registry or role
  decision attached. [progress 2026-07-29](../progress/2026-07/2026-07-29.md)

- **A pass/fail tally is only comparable when the invocation path is quoted with it.**
  The same tree at the same commit under the same interpreter reported 2 failed / 616
  passed from the canonical root and 5 failed / 610 passed from `/workspace` — one tree,
  two names, because E8 ratifier scripts compare the invocation path to the literal
  canonical root as a trust-boundary guard. Path dependence also changed *which* tests
  ran (615 vs 618). The guard was not relaxed: making a test pass by weakening a
  trust-boundary check would be a trust-boundary change.
  [progress 2026-07-29](../progress/2026-07/2026-07-29.md)

### Open Questions (2026-07-29)

- Structured timeout provenance remains an instrument-correctness blocker before fresh
  final-C1/finalizer evidence, the consolidated human receipt, or any baseline apply —
  and the c1 retry timeout is a governed 300-second-budget decision that must not be
  silently raised.
- Producer-pin recurrence is open: older producer namespaces can still be selected
  without a runtime seal, and the ratified receipt binds the original producer helper
  while the live audit requires the current helper hash. The recorded remedy is to
  preserve the historical pin and bind the runtime helper *separately* — never to
  weaken the original provenance check.
- E5's R1-R4 questions have no answers and will not until Stage-B runs post-reboot.
- A `salient-token confidence` line of work is blocked outright: per-token logprobs are
  not persisted, so offline re-scoring of the relevant era is impossible.

### Source References (2026-07-29)

- [autopilot-decision-plane-audit-2026-07-22.md](../handoffs/active/autopilot-decision-plane-audit-2026-07-22.md)
  — E8 status of record (numeric 16/16/0 complete; quality T1-only; nothing applied or
  published), the instrument-repair chain, the ineligible-evidence discipline, the
  BigCodeBench execution-collision finding, and the open sub-gates.
- [batched-decode-measurement.md](../handoffs/active/batched-decode-measurement.md) — E5
  scout-vs-Stage-B grading, the artifact-republication rules for a grade change, and the
  Gemma capture invalidity.
- [gpu-serving-tie-in-program.md](../handoffs/active/gpu-serving-tie-in-program.md) — the
  FIX-FIRST ratification-wrapper verdict and the program-wide rule that bench observations
  inform design but never gate promotion alone.
- [progress 2026-07-29](../progress/2026-07/2026-07-29.md) — FG-4b decision-grade/
  proposal-only terminal, the G3 observation-only closeout, and the invocation-path tally
  divergence.

## Compiled Update — 2026-07-28 bounded recovery and targeted validation

The post-v8 campaign closed three related evidence practices. First, a scorer
or converter defect is repaired by deterministic replay of saved outputs; new
generation is reserved for a generation-path defect. That rule allowed the
ThinkingCap no-think row and the G3 receiver continuation to retain their
sealed inference evidence while correcting the downstream path. Second,
targeted remedial inference must test the hypothesized failure mechanism, not
quietly become a full-suite rerun: Laguna's eight preclassified LCB cases
recovered only one new solve despite fixing several termination modes. Third,
the E8 quality-baseline recovery binds reconstruction to the sealed T1 core
before any output write and keeps collection distinct from the later
human-only baseline application.

### Key Findings (2026-07-28)

- **Do deterministic tail replay before regeneration.** The corrected
  ThinkingCap no-think SWE/LCB row is comparable because the capture was
  re-scored from sealed outputs with the frozen v4 converter; the old
  thinking-enabled row stays diagnostic rather than being blended into the
  comparison. G3 likewise completed its receiver-only continuation from the
  sealed generator ledger, but its missing matched controls and stop-reason
  metadata defect remain explicit open work.
- **A termination repair is not a quality repair.** Laguna FG-2V changed one
  literal loop to a normal stop and improved several format stops, yet its
  focused eight-row screen gained only one new LCB solve. The evidence rules
  out inferring coding-role suitability from a cleaner finish reason alone.
- **Recovery instruments must validate source identity before side effects.**
  E8 partial-r2 schema v2 reconstructs from the sealed T1 `core_v2` and
  rejects legacy or mismatched intermediates before creating collection
  output. The active collection remains observation/evidence work; no quality
  baseline has been applied or published.

### Open Questions (2026-07-28)

- G3 needs matched receiver-nothink and Qwable-prefix controls, plus faithful
  llama-server stop-reason classification, before any generator selection.
- E8 still requires complete fresh recovery evidence and the separate
  consolidated human trust-boundary action before its quality baseline can be
  applied.

### Source References (2026-07-28 bounded recovery and targeted validation)

- [Architect model comparison handoff](../handoffs/active/architect-model-selection-bench.md) — sealed no-think ThinkingCap authority and the bounded Laguna FG-2V result.
- [GPU CoT scaffold sidecar](../handoffs/active/gpu-cot-scaffold-sidecar.md) — deterministic receiver-only G3 continuation, results, and unidentifiable-control caveat.
- [Autopilot decision-plane audit](../handoffs/active/autopilot-decision-plane-audit-2026-07-22.md) — sealed-core E8 recovery contract and unapplied baseline state.

## Compiled Update — 2026-07-26 capture-integrity boundary

The Laguna architect comparison exposed an evidence defect rather than a model
verdict: the original runner retained only the final 4,000 response characters.
That makes the initial `18/40` SWE read and selective replacement draws
diagnostic only. Schema v4 now retains and fingerprints complete prompt,
response, and reasoning material, fails incomplete rows and stale resume data
closed, and makes the converter and judge require the reviewed producer and
pinned prompts. A lossless agentic-SWE trajectory contract applies the same
principle to every assistant reply and pre-truncation tool observation. The
separate Laguna prompt-contract-fix full-40 and official Docker scores remain
open; no coding-specialist decision follows from this update.

### Key Findings (2026-07-26)

- **A score cannot be decision-grade when the scored response was tail-sliced.**
  Full-response retention and row-level identities are now a prerequisite for
  conversion, scoring, or safe resume; token caps remain visible model outcomes
  rather than being repaired into partial patches.
- **The capture gate generalizes beyond one-shot SWE.** Agentic trajectories
  now preserve full turn evidence and publish a run-level eligibility manifest,
  so incomplete, legacy, over-budget, or source-mismatched evidence is not
  silently accepted by a later scorer.

### Source References (2026-07-26 capture-integrity boundary)

- [Architect model comparison handoff](../handoffs/active/architect-model-selection-bench.md) — Laguna result supersession, v4 gate, and remaining full-40/Docker work.
- [Scoring infrastructure handoff](../handoffs/active/scoring-infra-standardization.md) — completed lossless agentic trajectory capture contract.
- [Progress 2026-07-26](../progress/2026-07/2026-07-26.md) — capture failure modes, validation evidence, and explicit non-decision posture.

## Compiled Update — 2026-07-24

Two converging threads landed this cycle: the architect-candidate benchmark reached a **well-powered, scorer-corrected NULL** across all six/seven reasoning-QA measurements (no accuracy basis for an architect model choice), and a near-miss on that same verdict — a stale answer-extractor that manufactured a false-significant result — triggered a stack-wide audit that found **~10+ independent, duplicated answer-scoring implementations**, one of which sits on the autopilot RL reward path. Confidence: `verified` for the landed scorer-standardization code (regression-tested) and the measured McNemar results; `observation` for the CPU A2/RP-5 arm (still GPU-session-coexistent, pre-final-analysis at compile time).

### Key Findings (2026-07-24)

- **Architect model-selection bench: seven independent paired measurements are now null, and the CPU quant-comparison arm (A2) tracks at-or-above the GPU IQ2 arm.** Following R6 (`olympiadbench_hard`, the first non-saturated suite, n=155: A1 68.4% / A3 69.0% / A4 64.5%, all pairwise p≥0.19), the CPU session ran **A2 (122B-A10B UD-Q4_K_M, fenced with `repeat_penalty 1.1`)** overnight on the pinned item sets: `aime25` complete 23/30 (76.7%); `olympiadbench_hard` ~72% on the answered subset (the remainder filtered to only the 17 items A1-IQ2 got wrong, per an operator ROI call — the untested-item conservative assumption can only *overstate* the IQ2 penalty, giving a one-sided H1 bound); `gpqa_diamond_cot` skipped on a power-math argument (185 paired items give MDE ~6–7pp, insufficient to resolve a subtle 1–2pp degradation, and the knowledge axis is already certified by AXA-1's Δ0.0pp n=212 parity). Live read: **A2-Q4 tracks at-or-above the A1-IQ2 band** — no gross Q4-vs-IQ2 reasoning degradation is materializing (see [Quantization](quantization.md) for the full termination-defect refutation this arm also settled). [architect-model-selection-bench](../handoffs/active/architect-model-selection-bench.md), [progress 2026-07-24](../progress/2026-07/2026-07-24.md)

- **R7: a stale answer-extractor nearly manufactured a false "keep the big models" verdict — corrected to a clean quality-tied NULL.** Pooling banked per-question data (n=533) to answer "should A1(122B)/A3(27B-dense) be dropped vs A4(35B-A3B)?" first showed A1/A3 *significantly* beating A4 (p=0.005/0.043). Root cause: `gpqa_diamond` was scored with a stale `extract_letter_answer` that dropped bare-letter final-line answers, and verbose A4 leaked **15% of items to false parse-failures vs A1's 0%** — a scoring bug that systematically penalizes models that show their work, exactly the bias class this bench had already fixed once (R1, 2026-07-20). Re-scored with the canonical extractor (A4 gpqa 43.4%→53.0%), the pooled read flips to **A1 69.8 / A3 69.6 / A4 67.4 — every pairwise p ≥ 0.23 (NULL)**. Verdict: on measured quality A1/A3 do **not** outcompete A4; combined with A4 also being throughput-best on GPU (see [Hardware Optimization](hardware-optimization.md)), the keep/drop lean is **quality-tied → A4 suffices, A1/A3 not justified on quality grounds** — pending the still-unbuilt Phase-2 tool-use/coding gate, which the runbook now makes a **hard, required** precondition for any architect keep/drop verdict (reasoning-QA alone cannot decide it, since the architect's real job is planning/tool-use, not math QA). [architect-model-selection-bench](../handoffs/active/architect-model-selection-bench.md) §R7, [architect-bench-runbook](../docs/reference/architect-bench-runbook.md) §7/§9

- **Scorer fragmentation audit: ~10+ independent answer-scoring implementations exist across the stack, one on the production RL reward path.** Triggered directly by the R7 near-miss, an audit found duplicated extraction/scoring logic in the research repo (`v7_quality_gate_runner` — now canonical, `lib/scorer`, `score_benchmarks`, `score_aa_omniscience_run`, `xmas_function_axis_sweep`, `xmas_cheap_kill`, `score_with_claude`, `short_mk_voting`, plus per-adapter local extractors) and the orchestrator (`pipeline_monitor/model_grader.grade_answer`, and — flagged **HIGH RISK** — `api/services/memrl.score_completed_task`, the autopilot RL reward path; if it shares the verbose-penalty bug it has been biasing production routing reward against models that show their reasoning). Phase 1a landed same-day: the 15 validated extraction primitives were promoted verbatim into a single canonical `answer_scoring.py` library (module dependency = `re` only, sympy/Fraction lazy), with `v7_quality_gate_runner` now importing/re-exporting from it (−331 lines of duplication, external API unchanged) and a regression test locking the bare-letter and truncated-boxed cases. Migration of the other ~10 research consumers (1b) and the orchestrator audit/fix of `memrl`/`model_grader`/`rubric_review` (1c, production-touching, operator-gated) remain open. [scoring-infra-standardization](../handoffs/active/scoring-infra-standardization.md)

- **A parallel Track 2 built the first runnable tool-use/coding eval scaffold**, closing part of the gap the runbook's new hard gate (§9) requires before any architect verdict: the `datasets` extra was installed (LiveCodeBench loads 2360 items), and a sandboxed `code_exec_scorer.py` (isolated subprocess, fresh temp cwd, RLIMIT_CPU/AS/CORE/NPROC, wall timeout, minimal env) replaces the placeholder `substring "def "` check, smoke-tested on correct/wrong/runaway/functional cases. Wiring it to the suites and hardening isolation (unshare/nsjail/container — the current scaffold is trusted-code only) remain open before any at-scale run, as does the actual A1/A3/A4 coding-harness run and the larger agentic SWE-bench/tau-bench multi-turn tool-loop harness. [scoring-infra-standardization](../handoffs/active/scoring-infra-standardization.md)

- **The architect-bench SOP (runbook) crystallized a hard pre-verdict scoring gate from the R7 incident.** Because a scorer fix in code does not retroactively propagate to already-stored `per_question.jsonl`/`*.rescored.jsonl` results (they are point-in-time), the runbook now requires, before any pooled read or keep/drop verdict: (1) regenerate every arm's rescored file with the *current* extractor, and (2) print per-arm `noparse` counts per suite and stop if the gap is asymmetric across arms. This mechanizes the project's standing rule ([[feedback_parse_failure_rate_is_a_scoring_artifact]]) into a gate rather than a reviewer habit. [architect-bench-runbook](../docs/reference/architect-bench-runbook.md) §7

### Delta — audit closure + coding ladder stood up (compiled 2026-07-24 later)

- **The memrl question CLOSED: NOT affected.** The read-only orchestrator audit (59 file:line citations)
  found the live TD reward does **zero regex answer-extraction** — success is a structural flag, cost terms
  are telemetry/priors, latency is length-normalized — so autopilot reward carries no verbose penalty. The
  judge-parse bug class exists but every affected path is dormant or reward-decoupled; two latent 1c-fix items
  scoped (a 500-char candidate truncation in `review_service.review()` re-enterable via `allow_delegation=True`,
  and a false-*positive* last-letter fallback in `debug_scorer`). Bonus finding: **tool use is production-live**
  via the bespoke REPL protocol (`TOOL()/CALL()/FINAL()`), so an architect tool-use eval can run through the
  orchestrator today (`force_role="architect_general", force_mode="repl"`); `ChatRequest.tools` is
  accepted-but-never-consumed. [audit](../research/deep-dives/2026-07-24-autopilot-scoring-tooluse-audit.md)
- **The Phase-2 coding ladder went from "no harness" to running in one session**, every rung
  validated-on-canonical before model tokens: HumanEval (164/164 canonicals; arms tied+saturated —
  A4 95.7 / A1 95.1 / A3 92.1, IQ2 costs nothing on executable code); **real LiveCodeBench-hard** (53 contest
  problems w/ hidden stdin/stdout tests; **discriminative** — A4 54.7%); **BigCodeBench-hard** (90/148
  canonical-verified; two harness bugs — venv-symlink `resolve()` and OpenBLAS-vs-RLIMIT_AS — caught by the
  canonical gate); **SWE-bench Verified official docker harness** with a **gold-calibration filter** (instance
  in slice iff its gold patch resolves here): 40/40 resolved on the calibrated slice; oracle patch-gen rung
  (SEARCH/REPLACE protocol → offline diff conversion → FAIL_TO_PASS) chained behind the GPU runs.
  [scoring-infra-standardization](../handoffs/active/scoring-infra-standardization.md)

### Final ladder results (compiled 2026-07-24 EOD)

The coding ladder completed: pooled 4-rung n=347 **dead-tied** (A4 64.8 / A3 64.6 / A1 63.4, all p≥0.53) —
a real null on discriminative suites — but **SWE-oracle (n=40, gold-calibrated) produced the campaign's first
significant separation: A3 52.5% vs A4 35.0% (+17.5pp, McNemar p=0.039 uncorrected, discordants 8/1)**, with
A3 also directionally ahead on BCB-hard: the dense model leads the *realistic* tiers while the small-active
MoE leads contest algorithmics. Patch-protocol discipline scaled with size (A1 34 > A3 32 > A4 27 non-empty).
Method note for SWE paired stats: the harness report omits empty-patch instances from resolved/unresolved —
pair over the FULL slice or n silently shrinks. Next: Laguna-S-2.1 IQ2 candidate fold-in (config → SWE →
LCB), then the A3-vs-A4 SWE confirmation expansion (p=0.039 is 1-of-~12 comparisons and needs it).

### Open Questions (2026-07-24)

- The A2/RP-5 CPU Q4 arm's paired McNemar analysis (canonical rescore) against A1-IQ2 was still pending at compile time — will H1 (does IQ2 preserve the 122B's reasoning relative to Q4?) close as parity, given the live at-or-above read?
- Do the hard coding tiers (LCB-hard / BCB-hard / SWE-oracle) separate the three arms where reasoning-QA could not — and do the discriminative survivors get registered into the eval-tower pool (era-sensitive, operator decision package pending results)?
- The agentic multi-turn harness (SWE-bench agentic / tau-bench) remains unbuilt; the audit's orchestrator-REPL path is the cheap first rung.

### Source References (2026-07-24)

- [architect-model-selection-bench.md](../handoffs/active/architect-model-selection-bench.md) — R6/R7 results, the scorer-artifact correction, the CPU A2/RP-5 overnight arm, the six/seven-way NULL verdict.
- [architect-bench-runbook.md](../docs/reference/architect-bench-runbook.md) — the codified SOP (golden rules, suite ladder, scoring discipline, the new §7 hard pre-verdict gate and §9 required Phase-2 gate).
- [scoring-infra-standardization.md](../handoffs/active/scoring-infra-standardization.md) — the ~10+-implementation fragmentation audit, Phase 1a canonical library, Phase 2a code-execution scaffold.
- [progress 2026-07-23](../progress/2026-07/2026-07-23.md), [progress 2026-07-24](../progress/2026-07/2026-07-24.md) — R7 discovery narrative, A2/RP-5 overnight execution.

## Compiled Update — 2026-07-21

The 2026-07-20/21 eval-tower audit cycle produced the deepest instrument review to date and, in the same window, executed the largest instrument change. Two read-only audits (tower internals + the loop around the tower) surfaced **3 CRITICAL / 16 HIGH / ~55 MED-LOW** defects — most fixed the same day with tests; the question pool was **rebuilt and era-labeled E7**; the **EV-11 confidence stub was proven a phantom and neutralized**; and a 12-URL research intake added a **judge-validity cluster** (intake-874/875/876) that names a failure mode our judge-scored numbers currently cannot detect. Confidence: `verified` for the landed mechanical fixes (each with tests) and the executed E7 rebuild; `external`/`observation` for the judge-validity papers, all of which are operator-review candidates under the human-amendment-only measurement trust boundary (scoring semantics, thresholds, era handling are never agent-amended).

### Key Findings (2026-07-21)

- **The eval tower's recurring bugs trace to seven architectural weaknesses, not bad luck.** The tower-internal audit named them: (1) scorer/module identity is nondeterministic — same-named modules (`debug_scorer.py`, `dataset_adapters.py`, `question_pool.py`) exist in two repos and `sys.path` is mutated at import + lazily at runtime, so *which code scores your eval depends on which eval ran first in the process*; (2) silent-fallback is the default error philosophy (scorer→scorer with no provenance, failure caches, empty suites → legitimate-looking zero-quality); (3) identity/provenance is not machine-checked (disjoint qid namespaces, no dataset-content hash on tier draws); (4) evidence is single-copy and fragile; (5) the gate is asymmetric (quality guarded, reliability not gated at all, NaN passes every check); (6) dead code + 55-field explosion mask policy gaps; (7) tests mock at the wrong boundary and some enshrine bugs. Two findings were double-discovered by independent subagents (QID-1, REL-1) → high confidence. ([eval-tower-architecture-audit-2026-07-20](../handoffs/active/eval-tower-architecture-audit-2026-07-20.md))

- **Confirmed-in-production, not hypothetical.** The live 53,231-question pool was built by the STALE orchestrator adapter registry — **15 of 33 adapter suites present**; `scoring_verifiers` (EV-3) and `omniscience` were marked "integrated" in the verification handoff but **never actually sampled**, and `gaia` shipped **0 rows**. `math_verify` silently degraded to `exact_match` on every *threaded* eval (math-verify's `signal.alarm` raises off-main-thread → bare-except fallback), resurrecting the EV-11 0/1,819 no-op invisibly and concurrency-dependently. Promotion "fresh-draw" recency exclusion was a qid-namespace no-op (sha1-hash qids ∩ raw pool-id set = ∅). ECE was exactly 0.0 for 1182/1182 journaled rows; 634 bare `NaN` tokens made the journal non-strict JSON; a per-suite `3.0/n` float boundary fired a hard violation on a single-question flip in 186 (n,k) combos. ([eval-tower-architecture-audit-2026-07-20](../handoffs/active/eval-tower-architecture-audit-2026-07-20.md), [eval-tower-verification](../handoffs/active/eval-tower-verification.md))

- **Most of the phased A-E fix plan landed the same day, with tests.** A1 killed silent scorer→scorer fallbacks (unreachable-judge / typo'd-verifier / thread-degrade all score-as-ERROR); A4 unified qid namespaces; A5/A6 made the journal + baseline durable (atomic tmp+replace, flock, torn-tail quarantine, `schema_version`); B1 added a reliability floor + excluded errored rows from the quality denominator (an infra 5xx wave no longer reads as a quality regression); B2 restored quantum-inclusive per-suite thresholds (a single-question flip is at-resolution noise per MEASUREMENT's MDE, not a hard violation); B6 renamed the dead EV-8 diversity gate (`src/safety_gate.py`→`diversity_gate.py`) to kill the module-identity collision; C1-C8 stamped instrument identity on every result, made loaders fail-closed + retryable, enforced strict split discipline, and added serial-path stall protection + orphan drain; D1-D6 added incremental per-question persistence (the `feedback_incremental_persistence` requirement the tower itself had violated), strict JSON (`allow_nan=False`), and one canonical shard iterator; E2/E3 added the missing fake-transport error-path suite + an ECE pin test. Scoring-semantics legs still take a one-line operator sign-off (EV-CONF precedent). ([eval-tower-architecture-audit-2026-07-20](../handoffs/active/eval-tower-architecture-audit-2026-07-20.md), [eval-tower-loop-robustness-audit-2026-07-20](../handoffs/active/eval-tower-loop-robustness-audit-2026-07-20.md))

- **E7-eval-instrument: the question pool was rebuilt against the full research registry and era-labeled.** 53,231 rows / 21 suites → **79,479 rows / 41 suites (38 nonzero)**; shared suites byte-identical (zero row loss, verified via module `__file__`); `mmlu_pro` (12,032), `scoring_verifiers` (6,701), `omniscience` (600) + 15 more suites now sampled by T1/T2/T3 for the first time; `gaia`/`aa_lcr`/`document_extraction` = 0 with loud `source_absent` accounting (operator downloads pending). Because this is an instrument change, an era row **E7-eval-instrument** was appended to `instrument_eras.yaml` under the operator's pre-authorization — never edited in place; pre-boundary quality rows become historical priors. The **B7 scorer-semantics package** (final-region extraction, boundary-anchored substring, multiple-choice end+length ranking, boxed/multiset/textual-MC) was ratified (op-bundle ESC-6 option B) with a **146-row golden-delta doc: 50 outcomes changed, all finding-traced**, 21/39 live sentinels package-sensitive. The E7 boundary bundles pool + scorer so a single instrument shift captures both. ([eval-tower-architecture-audit-2026-07-20](../handoffs/active/eval-tower-architecture-audit-2026-07-20.md), [progress 2026-07-21](../progress/2026-07/2026-07-21.md))

- **EV-11 confidence was a phantom worth 10-15% of every RLVR tier score; now neutralized, with real logprob plumbing landed.** `confidence = float(correct)` is tautological → ECE is a constant 0.0 → `rlvr_tiers._calibration_component = 1 − ece` is pinned to a phantom 1.0 that silently gated autopilot promotion (`required_metric` for tiers 2-3). Interim fix (pre-approved, low-risk-first): `rlvr_reward_from_result` zeroes BOTH calibration and discrimination and appends a `confidence_not_real` blocker unless `details['confidence_is_real']` is True (stub/mixed/legacy rows fail closed). Plumbing landed: opt-in `n_probs` threads llama.cpp `completion_probabilities` end-to-end → `confidence_source=completion_probabilities_geomean`. EV-11b's closed-top-bin ECE (`stat_tests.expected_calibration_error`) is implemented + era-labeled but **moot until confidence is real**; the final real-ECE re-entry to gating is operator-gated (ESC-7, decide with EV-4's calibration data). ([eval-tower-loop-robustness-audit-2026-07-20](../handoffs/active/eval-tower-loop-robustness-audit-2026-07-20.md), [eval-tower-verification](../handoffs/active/eval-tower-verification.md))

- **Judge-validity intake: our judge-scored numbers have no validity check for the dominant failure mode.** Three convergent 2026-07-21 entries, all operator-review candidates (human-amendment-only):
  - **[intake-875]** *Self-Play Reward Hacking of Reference-Free LLM Judges* (arxiv:2607.05904, cred 2): a judge shown a candidate without ground truth scores plausibility, not correctness. Judge pass-rate rises 0.716→0.938 under self-play while hidden-anchor accuracy stays flat 0.209→0.202; best-of-N judge-selected gap widens 0.20@k=1 → **0.588@k=16** while true unit-test pass moves only 0.27→0.29. Hacked errors transfer across judge families and a three-family min-vote ensemble still accepts **~55%** of hacked wrong answers — directly undercutting the "cross-family verification is the strongest defense" rule this project already codified. The measured fix is **de-anchoring** (commit-first / blind-solve → FPR 0.906→0.012); a plain "verify/recompute" instruction is worthless (FPR 0.719).
  - **[intake-874]** *Reward Hacking in Rubric-Based RL* (arxiv:2606.04923, Tsinghua KEG, cred 4): rubric judges are demonstrably, reproducibly hackable via *semantic* exploits (not rule-breaking). Exploitability is capped by whether the author can cheaply emit the pattern (format bias ~66% elicitation vs 95-100% for lexical/tone/self-praise); in-domain capability drops while aggregate general benchmarks stay flat → **an aggregate suite is an unreliable reward-hacking tripwire**. Honest scope: it kills "rubric judges are robust to hacking" but does NOT rank rubric-vs-verifiable (our own intake-660/664 show programmatic verifiers gamed 32.8% of the time — neither class is a safe default).
  - **[intake-876]** *Agreement Metrics for LLM-as-Judge* (arxiv:2606.00093, Rao & Callison-Burch, cred 3): on non-degenerate binary judge-vs-human data Pearson/Spearman/Kendall/phi/MCC collapse to the *same number* — reporting several side-by-side manufactures false corroboration. **Cohen's kappa** is the only common coefficient adding information (it exposes judge positive-rate drift). A full-text search of the 865-entry intake index returned **zero** prior hits for kappa/Krippendorff/inter-rater, and neither MEASUREMENT.md nor MEASUREMENT_POLICY.md mentions agreement statistics.
  Proposed operator rules: an **anchor rule** (any judge-scored gating metric paired with a judge-independent verifier + the gap reported; widening-with-N is the hacking signature), a **de-anchoring rule** for selection judges, a **dual-judge offline audit** (clean vs bias-augmented rubric, runnable today), a **CHERRL bias taxonomy + exploitability axis** for RM-5, and a **chance-corrected agreement statistic** folded into P-REV-1 before it ratifies. ([eval-tower-verification](../handoffs/active/eval-tower-verification.md), [progress 2026-07-21](../progress/2026-07/2026-07-21.md))

- **EV-4 calibration baseline is RUNNING on the E7 instrument** — the first decision-grade-capable calibration baseline (rebuilt pool where `scoring_verifiers` is actually sampled, ratified B7 scorer, real logprob confidence). Its first execute was honestly refused by the B2/B5 concurrency guard (worker_general topology cap = 1, J5-measured min_ratio 1.005; the old `--min-eval-concurrency 3` predated the truthful ladder), then rewritten as two sequential per-role phases: frontdoor@3 → worker_general `--allow-serial` (intentional, recorded). ~820 HE-R+ candidate items/role; ECE/AUC/Top-1/Bottom-1/Spearman baseline to be recorded on completion. ([inference-batch-loop](../handoffs/active/inference-batch-loop.md), [progress 2026-07-21](../progress/2026-07/2026-07-21.md))

- **Cost-reduction filter scope confirmed + paired-significance is the codified successor to the 3/n gate.** The mid-range difficulty filter (30-70% historical pass rate, Spearman ρ ≥ 0.87, 44-70% task reduction) applies to **external fixed-task evals** (Terminal-Bench Core, 89 tasks) and NOT to autopilot's rotating regression pool — the objectives are opposite (cross-agent rank ordering vs within-system regression detection; ceiling/floor questions are the regression/breakthrough signals, and only 3 of the 50-qid stable core are mid-range). Separately, exact-McNemar + Wilson CIs mined from intake-802 (`llm-inference-bench`, credibility bumped 2→3 after source verification) landed as stdlib-only `stat_tests` primitives and are documented in chapter 06 as the formal successor to the 3/n resolution gate; `eval_tower.screen_paired_arms` emits them gated on `dataset_sha256`+`test_profile` match, but stays observation-grade until the EV-11 math re-baseline reaches a codified recipe. ([eval-benchmark-cost-reduction](../handoffs/active/eval-benchmark-cost-reduction.md))

### Open Questions (2026-07-21)

- Will the operator adopt the anchor + de-anchoring judge rules and a chance-corrected agreement statistic into MEASUREMENT.md? All are human-amendment-only trust-boundary edits. [intake-875/876]
- EV-4's E7 baseline is the first data able to inform the ESC-7 real-ECE-to-gating decision — pending its terminal ECE/AUC/Top-1/Spearman row.
- `gaia`/`aa_lcr`/`document_extraction` sample at 0 rows until operator downloads land; until then the E7 pool's coverage of long-context + agentic suites is nominal-but-empty.
- Is there a discriminative frontier/harder eval tier to replace the saturated (90-94%) production review suites, now that E7 adds `mmlu_pro`/`gpqa`-class suites to the draw?
- Should any past autopilot best-of-N / candidate-selection gain be retrospectively re-checked for reliance on judge-measured scores with no independent anchor? [intake-875]

### Source References (2026-07-21)

- [eval-tower-architecture-audit-2026-07-20.md](../handoffs/active/eval-tower-architecture-audit-2026-07-20.md) — tower-internal teardown (3 CRITICAL/16 HIGH/~55 MED-LOW), the seven architectural weaknesses, confirmed-in-production evidence (15/33 suites, threaded math_verify degrade, qid no-op), and the phased owner-tagged A-E fix plan + E7 A3 pool rebuild.
- [eval-tower-loop-robustness-audit-2026-07-20.md](../handoffs/active/eval-tower-loop-robustness-audit-2026-07-20.md) — the loop around the tower; EV-11 confidence-phantom (10-15% of RLVR score), EV-CONF sequencing, and the runner/preflight/ledger robustness fixes.
- [eval-tower-verification.md](../handoffs/active/eval-tower-verification.md) — EV-1..EV-13 program, EV-CONF real-confidence plumbing, and the 2026-07-21 judge-validity intake block (intake-874/875/876 operator-review candidates).
- [eval-benchmark-cost-reduction.md](../handoffs/active/eval-benchmark-cost-reduction.md) — mid-range difficulty filter (external-fixed-task-only) + intake-802 McNemar/Wilson paired-significance as the 3/n-gate successor.
- [inference-batch-loop.md](../handoffs/active/inference-batch-loop.md) — the single-writer `/loop` that carries EV-4 to a decision-grade run.
- [progress 2026-07-21](../progress/2026-07/2026-07-21.md) — E7 A3 execution log, B7 golden-delta, EV-CONF plumbing, the 12-URL intake summary, and the EV-4 two-phase launch.
- intake-874 `2606.04923` (cred 4) · intake-875 `2607.05904` (cred 2) · intake-876 `2606.00093` (cred 3) — judge-validity cluster; all observation-tier, operator-review candidates.

## Compiled Update — 2026-07-20

Two model-role selection benches (architect and reviewer) and the eval-tower calibration work converge on one methodological rule: **objective oracles, not model-as-judge** — the reviewer work measured model-as-judge patch-review as near-random on hard negatives, so both role-selection benches are objective-scored only. Confidence: `verified`/decision-grade for accuracy verdicts scored by objective oracles; `observation` for every throughput row (pre-`P-GPU-1`).

### Key Findings (2026-07-20)

- **Architect model-selection is a specced, GATED, objective-scored bench** (not yet run). Phase 1 = AIME'25 (new adapter) + GPQA-Diamond + MMLU-Pro *control*, paired + seed-pinned + production sampling; the quality verdict is device-independent decision-grade, throughput stays observation-grade until `P-GPU-1`. It exists because the only local quality signal — the AXA-1 Δ0.0pp IQ2≈Q4 parity — is statistically powerless on reasoning (n≈4/hard-suite), and every published benchmark of the exact Qwen3.5/3.6 models is THIN (27B GPQA reported as both 73.4 and 87.8; a deployment-eval preprint scored Qwen3-30B-A3B dead-last 0.226, a harness/prompt artifact contradicting its own ~80% AIME — intake-862 `2604.07035`, cred 2). The architect choice remains **UNDECIDED**. ([architect-model-selection-bench](../handoffs/active/architect-model-selection-bench.md), [architect-model-selection-2026-07-20](../docs/reference/architect-model-selection-2026-07-20.md))
- **Reviewer model-role ablation (H5) on the decision-grade C-CRAB P-REV-1 corpus: model-as-judge patch-review is near-random, and no arm cleanly wins.** GLM-5.2-IQ2 FAILS admission (FA 41.7%, FR 25.0%, **AUC 0.509 ≈ random**); the A0 objective-verifier floor is perfect by construction (FA/FR 0.0%). A3 122B-IQ2 lowers false-accepts (FA 12.5%) but over-rejects (FR 58.3%); A1 122B-Q4 self-review fails both sides (FA 45.8/FR 41.7); fast small arms are no better (Qwen3.6-27B AUC 0.503, Qwable IQ4 AUC 0.438; a Qwen+Qwable scaffold is best-shaped at AUC 0.659 but FR still too high). Family-preference is a *weak* measured covariate (−0.9..+3.5pp). ([reviewer-model-ablations](../handoffs/active/reviewer-model-ablations.md))
- **Eval-tower must track ECE + AUC, not just accuracy** (SWE-RM: two verifiers with identical accuracy produced opposite RL outcomes). EV-11 `math_verify` scorer flip landed and EV-11a fixed nested-boxed-LaTeX truncation. EV-11b surfaced a real binning divergence: the inline `_aggregate` ECE (top bin half-open, drops `confidence==1.0` failures) vs the canonical `stat_tests.expected_calibration_error` (top bin closed) differ 0.15–0.40 on binary-confidence math suites — recommendation is to adopt the canonical definition, era-label the metric shift, and bundle it with a fresh operator-gated re-baseline (EV-11c). ([eval-tower-verification](../handoffs/active/eval-tower-verification.md))
- **Instrument saturation is a standing, dated hazard.** Production review suites sit in the 90–94% band and cannot resolve the top-2 stack models (a small MoE appears tied with a much larger dense model of the same family) — the exact failure the DRACO ">90% → reject / non-discriminative" rule guards against, observed on a *deploy-gating* comparison, motivating a harder frontier eval tier. ([eval-tower-verification](../handoffs/active/eval-tower-verification.md))
- **The model-probe scoreboard codifies observation-grade discipline:** one glance-able row per model/quant (pp/tg/quality/role-ready/artifact), all single-config small-n = OBSERVATION per MEASUREMENT.md, append-a-row rule, and blocked candidates are not speed-reran without a named quality/loader/protocol fix. P-BENCH-3 batched-decode runs fail-closed (`decision_grade=false`) on host-health warnings and index by model+quant, never by role. ([model-probe-scoreboard](../docs/reference/model-probe-scoreboard.md), [batched-decode-measurement](../handoffs/active/batched-decode-measurement.md))

### Open Questions (2026-07-20)

- Phase-2 architect planning-task design (SWE-bench-Verified FAIL_TO_PASS oracle vs bespoke mined-log tasks) — must have an objective oracle or be dropped, since model-judge scoring is near-random.
- The EV-11b ECE-binning definition is operator-gated (CRITICAL SafetyGate/journal/RLVR path) and awaits the bundled math re-baseline.
- Is there a discriminative frontier/harder eval tier to replace the saturated production review suites?

### Source References (2026-07-20)

- [architect-model-selection-bench.md](../handoffs/active/architect-model-selection-bench.md) + [architect-model-selection-2026-07-20.md](../docs/reference/architect-model-selection-2026-07-20.md) — objective-scored, gated architect bench + THIN published-benchmark caveats.
- [reviewer-model-ablations.md](../handoffs/active/reviewer-model-ablations.md) — registry-driven reviewer tournament; model-as-judge near-random on hard negatives.
- [eval-tower-verification.md](../handoffs/active/eval-tower-verification.md) — ECE/AUC calibration, math_verify, saturation hazard.
- [model-probe-scoreboard.md](../docs/reference/model-probe-scoreboard.md) — living observation-grade scoreboard + stop-list.
- [batched-decode-measurement.md](../handoffs/active/batched-decode-measurement.md) — P-BENCH-3 fail-closed host-health discipline.
- intake-862 `2604.07035` — deployment-aware multi-objective evaluation + the Qwen3-30B-A3B=0.226 harness-artifact caution.

## Summary

The project uses a purpose-built 8-suite (expanded to 23-suite) benchmarking framework to evaluate models for specific roles in the multi-model orchestrator. Unlike generic leaderboard benchmarks (MMLU, HumanEval), each suite tests a capability that maps directly to an agent role: can a model follow precise formatting (instruction_precision), chain multi-step reasoning (thinking), generate working code (coder), or produce valid tool calls (agentic). 61 baseline models have been evaluated across 381 total configurations.

The framework operates on two parallel scoring tracks. The `v1/` track uses Claude-as-Judge with a 0-3 rubric for open-ended quality assessment, chosen after experiments showed algorithmic scoring severely underscored models (38% vs 89% for the same output). The `debug/` track uses deterministic machine verifiers (multiple_choice, exact_match, code_execution, substring, programmatic, f1, llm_judge) for automated regression testing and MemRL reward injection without API costs. The deterministic pool now contains 56,448 questions across 23 suites, with 577 curated YAML questions and 55,871 drawn from HuggingFace datasets via runtime adapters.

Cost-aware reward design is layered on top of benchmark results for the MemRL routing system. The reward formula `quality_base - lambda * max(0, cost_ratio - 1.0)` gates cost penalties behind correctness, following the industry consensus established by xRouter (Salesforce), RouteLLM (LMSYS/ICLR 2025), and FrugalGPT (Stanford). Lambda=0.15 creates meaningful cost differentiation across the 13.4x speed range of the model pool (frontdoor at 18.3 t/s vs architect at 6.75 t/s) without overwhelming quality signal. Extended reward dimensions cover quality-gap penalty (over-qualified model selection), memory-tier penalty (WARM when HOT suffices), and web research effectiveness (source diversity, completeness, query strategy).

### Checkpoint update (2026-07-19)

The model-probe scoreboard is now the required companion for future model and
quant rows. Stop-listed candidates are not speed-rerun unless the proposed run
names a concrete quality, loader, protocol, parser, artifact, or compatibility
fix and an explicit reopen hypothesis. This keeps speed observations from
silently becoming admission evidence and redirects scarce windows to the
operator-gated promotion and GLM accept-control work. [Model probe scoreboard](../docs/reference/model-probe-scoreboard.md)

The GLM reviewer path also separates observation from decision-grade evidence:
P-REV-1 execution requires explicit protocol attestation and a decision-grade
accept-control signoff report, while missing notes, synthesized timestamps, or
incomplete row coverage fail closed. [GLM capability gates](../handoffs/active/glm52-reviewer-capability-gates.md)

Benchmark hardening in December 2025 addressed ceiling effects where top models scored 89-93%. Every tier was bumped up one difficulty level with post-doctoral T3 questions added, spreading the score distribution meaningfully across model classes. A mode-advantage suite (90 questions) was specifically designed to produce strong routing signal for MemRL by including tasks that structurally require specific execution modes (react, REPL, delegation, specialist escalation).

## 2026-07-19 Update — claim-grade measurement and reviewer evaluation

- A decision-gating number must carry metric direction, protocol id, repetitions, date, and attestation. P-GPU-1 additionally requires production-named kernel provenance and complete hardware/host/binary/model/cleanup fields; candidate-kernel rows are observations regardless of how plausible the value looks. Sources: [P-GPU-1 ratification package](../docs/reference/p-gpu-1-ratification-package-2026-07-18.md), [P-GPU-1 amendment draft](../docs/reference/p-gpu-1-amendment-draft-2026-07-19.md), [OP-2 canonical bench package](../docs/reference/op-2-canonical-bench-window-package-2026-07-18.md).
- Reviewer evaluation exposed a separate methodology constraint: balanced samples must not mix exact-answer, substring/code-prefix, and patch-review representations under one scorer. The current path is homogeneous source suites with deterministic ground truth, explicit false-accept/false-reject accounting, and a cheap screen before any P-REV-1 confirmation. Sources: [GLM reviewer capability gates](../handoffs/active/glm52-reviewer-capability-gates.md), [reviewer model ablations](../handoffs/active/reviewer-model-ablations.md), [model-probe scoreboard](../docs/reference/model-probe-scoreboard.md).
- Positive accept-control or judge-preference results do not substitute for hard-negative patch-review evidence. GLM's external JudgeBench/SWE results were positive, but C-CRAB P-REV-1 failed admission; the reviewer route therefore remains open research rather than a production-quality conclusion. Sources: [GLM reviewer capability gates](../handoffs/active/glm52-reviewer-capability-gates.md), [GLM accept-control signoff packet](../docs/reference/glm52-accept-control-signoff-packet-2026-07-18.md), [model-probe scoreboard](../docs/reference/model-probe-scoreboard.md).

## Key Findings

### New (2026-07-18, GLM reviewer-corpus representation guard)

- **Reviewer FA/FR tables are invalid when the selected rows mix incompatible candidate representations.** The GLM near-miss checkpoint found that a nominally balanced code slice combined exact-answer controls, substring/code-prefix controls, Python patch diffs, and C-CRAB patch reviews, so false-reject and false-accept rates were measuring corpus heterogeneity as much as reviewer quality. The durable rule is to stratify by source benchmark, source suite, and provenance scoring method before interpreting reviewer calibration. Sources: [glm52-reviewer-capability-gates.md](../handoffs/active/glm52-reviewer-capability-gates.md), [inference-acceleration-index.md](../handoffs/active/inference-acceleration-index.md), [progress 2026-07-18](../progress/2026-07/2026-07-18.md).
- **Harnesses should refuse mixed reviewer representations by default and require an explicit override for diagnostic mixtures.** The GLM direct corpus runner now records available/selected representation summaries, exposes `--source-suite`, `--source-benchmark`, and `--provenance-scoring-method` filters, and blocks execution when selected rows span multiple representation buckets unless `--allow-mixed-representation` is set. That turns a post-hoc interpretation failure into a pre-execution method gate. Sources: [model admission doc](../repos/epyc-inference-research/docs/reference/models/model-admission-2026-07-16.md), [model smoke queue](../repos/epyc-inference-research/docs/reference/models/model-smoke-queue-2026-07-16.md), [progress 2026-07-18](../progress/2026-07/2026-07-18.md).
- **A recovered narrow result does not close a broader reviewer role.** Homogeneous `seeded-mutation/cruxeval/exact_match` n=24 improved to FA `0.0%`, FR `16.7%`, parse `0.0%`, but it is exact-answer review evidence only; patch-review admission still needs a matched patch-diff corpus and the P-REV-1 measurement amendment before any role claim. Sources: [glm52-reviewer-capability-gates.md](../handoffs/active/glm52-reviewer-capability-gates.md), [model admission doc](../repos/epyc-inference-research/docs/reference/models/model-admission-2026-07-16.md), [model smoke queue](../repos/epyc-inference-research/docs/reference/models/model-smoke-queue-2026-07-16.md).

### New (2026-07-16, v7 K5 quality gate + readiness checks)

- **Endpoint contract is part of benchmark validity: the raw `/v1/completions` K5 attempt is non-evidence, and the corrected chat-endpoint harness is the gate record.** The old `/mnt/raid0/llm/tmp/v7-quality-20260716/` run failed the model/template contract with a Content-only protocol error. The fixed `v7_quality_gate_runner.py` uses `/v1/chat/completions` by default, records endpoint metadata, and keeps `/v1/completions` only as an explicit compatibility mode. Sources: [gemma-challenge-kernel-techniques-v7.md](../handoffs/active/gemma-challenge-kernel-techniques-v7.md), [progress 2026-07-16.md](../progress/2026-07/2026-07-16.md).
- **K5's promotion-quality comparison passed with matched suite scores, not inferred speed proxies.** Production v6 and refreshed v7 candidate `8e5c555ab` both scored MMLU-Pro `73/200=36.5%` and GPQA `50/195=25.6%`, with `0` errors and comparator `PASS` against the `-5pp` per-suite threshold. The result says "no observed K5 quality regression at this sample size"; it does not by itself promote the kernel or replace the operator promotion decision. Sources: [gemma-challenge-kernel-techniques-v7.md](../handoffs/active/gemma-challenge-kernel-techniques-v7.md), [progress 2026-07-16.md](../progress/2026-07/2026-07-16.md), `/mnt/raid0/llm/tmp/v7-quality-20260716-chat/v7_quality_gate_report.md`.
- **Readiness evidence is layered: code correctness, generated-stack consistency, and promotion-gate no-inference checks are separate gates.** The launcher/device guard passed focused unit tests, generated stack artifacts were refreshed by `stack_change_pipeline.py update`, and `stack_change_pipeline.py check --run-promotion-gate` passed with `summary: ok`, `acceptance: no-inference checks passed`, and `181` promotion-gate tests. This is the correct closure shape for a stack-change checkpoint: inference evidence and no-inference readiness are recorded separately. Sources: [gemma-challenge-kernel-techniques-v7.md](../handoffs/active/gemma-challenge-kernel-techniques-v7.md), [progress 2026-07-16.md](../progress/2026-07/2026-07-16.md).

### New (2026-07-17, CPU host drift and clean-run preflight)

- **CPU guard-cell drift can be host/runtime state rather than source regression, so future CPU A/Bs need an explicit clean-run preflight before anyone blames the kernel.** The K34 paired rerun showed current production recovered far above the earlier 07-16 guard cells while v7 stayed near parity on the same host, which makes the old slow numbers a repeatability artifact rather than a source-level verdict. The preflight to record before expensive CPU guard cells is: no AutoPilot/llama-server/bench/profiler, `numactl --hardware`, `free -h`, governor/EPP/boost/THP/NUMA-balancing, pinned `LD_LIBRARY_PATH`, build commit, and a cheap frontdoor sentinel. Sources: [gemma-challenge-kernel-techniques-v7.md](../handoffs/active/gemma-challenge-kernel-techniques-v7.md), [progress 2026-07-17](../progress/2026-07/2026-07-17.md).
- **v7 finalization now carries an explicit throughput-vs-context artifact requirement, so operator-facing matrices must use the fastest validated serving config rather than raw baseline runs.** K35 records exact model path/SHAs, v7 build commit, MTP/NEXTN and `ngram-mod,draft-mtp` flags, reasoning-off lanes, KV dtype/quant choices, GPU/CPU/hybrid offload mode, role overrides, context depths, acceptance side data, pinned `LD_LIBRARY_PATH`, the clean-host preflight, and cleanup proof. Sources: [gemma-challenge-kernel-techniques-v7.md](../handoffs/active/gemma-challenge-kernel-techniques-v7.md), [progress 2026-07-17](../progress/2026-07/2026-07-17.md).
- **Authored execution recipes are not benchmark evidence until the real binary accepts the flags and the command runs.** The July inference-batch audit found dozens of schema-valid command strings that referenced nonexistent runners or unsupported flags; only a command-surface audit against actual `--help` output and executable paths exposed the fabrication. Treat manifest generation and lint as shape checks only. Runnable benchmark recipes need real CLI grounding before they count as methodology. Sources: [inference-batch-loop.md](../handoffs/active/inference-batch-loop.md), [progress 2026-07-17](../progress/2026-07/2026-07-17.md), [k35-optimized-stack-throughput-context-report-2026-07-17.md](../research/deep-dives/k35-optimized-stack-throughput-context-report-2026-07-17.md).

### New (2026-07-07, real-suite v1 clean-window ledger scored 70% accuracy; E1 dense-control sweep completed as useful-but-not-pristine)

> **Review flag (project-wiki writer-evidence policy):** model-compiled, not adopted until human or measured review. Numbers below are observations without decision-gating protocol citations.

- **The real-suite v1 clean-window n=50 run now has usable results — superseding the 2026-07-06 hard negative.** The 2026-07-07 run of `run_real_suite_v1_evaltower_window.py --apply --confirm-clean-window --n 50` completed at `orchestration/reports/real_suite_v1_eval_20260707T013009Z/` with `35/50` correct (`quality_0_3=2.10`, reliability `0.94`), median request speed `32.606 t/s`, aggregate `29.462 t/s`, wall `1178.696s`, and `3` request errors (`1` no-such-group, `2` timed out). This supersedes the 2026-07-06 `0/50` hard negative (which failed on backend-unavailable). The artifact is a usable real-suite ledger for method triage and baseline comparison, but W3 acceptance remains open pending follow-up on AP-16 instruction-token bloat (`93.0%` instruction-token ratio) and how this ledger feeds promotion/regret views. Sources: [frontier-f1-real-task-corpus.md](../handoffs/active/frontier-f1-real-task-corpus.md), [progress 2026-07-07](../progress/2026-07/2026-07-07.md).

- **E1 dense-control P-BENCH-3 sweep completed as useful-but-not-pristine evidence.** The `qwen36_27b_q8` sweep at `-np 1,2,4,8,16` with `GGML_IQK=1` completed `43/43` cells with `0` errors. Tasks/hour scaled `20.11 → 124.62`, aggregate predicted t/s `1.07 → 6.81`, and p95 latency rose `240.9s → 674.0s`. The MI210 server remained live, so the run used `--skip-clean-check --allow-host-health-warning` and is classified as **useful dense-control evidence, not pristine host-exclusive decision evidence**. The corrected run (with `GGML_IQK=1`) replaced an aborted attempt that missed the IQK env. Sources: [batched-decode-measurement.md](../handoffs/active/batched-decode-measurement.md), [progress 2026-07-07](../progress/2026-07/2026-07-07.md).

- **The method discipline used for harness mutations is now explicit in the checkpoint record.** MH-9's bounded `new_file` support was accepted only after narrow Ruff and pytest verification on the touched files, and the live preflight still remained a separate P1.5 gate that exited `wait_for_boundary` rather than being conflated with code correctness. That is a useful distinction for benchmark methodology: a green code mutation does not imply runtime readiness, and the test bundle should say exactly which layer it proves. Sources: [meta-harness-optimization.md](../handoffs/active/meta-harness-optimization.md), [orchestration-robustness-audit-2026-07-11.md](../handoffs/active/orchestration-robustness-audit-2026-07-11.md), [progress 2026-07-11.md](../progress/2026-07/2026-07-11.md).

### New (2026-07-05, tool-use lane live under Gate-3 discipline + tier-segregated coverage instrument + real-suite clean-window runner + W8 sparse-baseline repair + RI-10 scored-canary protocol)

> **Review flag (project-wiki writer-evidence policy):** model-compiled, not adopted until human or measured review. Coverage percentages, canary proxies, and per-trial numbers below are observations unless a protocol id is cited.

- **The tool-use sentinel lane went from "built but inert" to live-activated — and every restart now passes through the Gate-3 telemetry contract.** Activation was executed 2026-07-04 at a clean trial boundary: orchestrator reloaded with `AUTOPILOT_TOOL_SENTINELS=1`, Gate-3 hard telemetry passed (`get_eval_secret=7-8` counted calls, all timing rows successful, no-tool isolation clean), and AutoPilot restarted with the flag verified in `/proc`. Two methodology refinements followed. First, a **recent-window telemetry gate**: `fable5_gate_report.py` no longer reopens `tool_use_activation` on a single latest zero-call eval — it summarizes the last 10 tool-metric rows and only flags when that window has no nonzero rows (the live window showed 4 nonzero rows / 26 calls, proving activation while individual evals still vary). Second, a **prompt-shape contract fix** (orchestrator `8be68732`): the forced-REPL sentinels had pinned `force_mode: repl` while asking for plain text/no code — a self-contradictory eval prompt; the repaired contract requires executable Python with `TOOL("get_eval_secret", ...)` followed by `FINAL(secret)`. The 2026-07-05 maintenance restart repeated the full sequence (trial-1151 stale daemon SIGKILL-verified, API reload under `gate3-tool-telemetry` profile, Gate-3 hard pass, fresh daemon with sentinel env attested). Remaining work is behavioral evidence (journaled nonzero `total_tool_calls` under the repaired contract) and usefulness scoring — not activation. Sources: [tool-use-eval-contract.md](../handoffs/active/tool-use-eval-contract.md), [progress 2026-07-04](../progress/2026-07/2026-07-04.md), [progress 2026-07-05](../progress/2026-07/2026-07-05.md).
- **Zero-tool-call evals are a latency/behavior question, not a code-mutation target — and parallel tool batching is a measure-first follow-up.** The live planner's first wrong move after activation was drafting a `src/tool_policy.py` code mutation to "fix" a zero-tool eval; an operator guardrail StrategyStore row (`opseed-green-tool-use-no-tool-policy-code-mutation-20260704`) now steers the planner away from that lever, and a broader boundary commit (`19f276df`) makes the planner process read-only (`Read`/`Grep`/`Glob` only; any mutation must be returned as an AutoPilot action). A read-only sidecar also established that independent read-only structured REPL calls are *already* executed in parallel (`REPLEnvironment._execute_structured()` → `execute_parallel_calls()`), so "batch independent tool calls" is not a missing executor: since live windows still show near-zero `total_tool_calls`, the mandated next step is to measure `len(tools_called) >= 2` frequency, read-only eligibility, and `parallel_tools_used` before touching HIGH/CRITICAL executor paths. Sources: [tool-use-eval-contract.md](../handoffs/active/tool-use-eval-contract.md), [progress 2026-07-04](../progress/2026-07/2026-07-04.md), [progress 2026-07-05](../progress/2026-07/2026-07-05.md).
- **Real-suite v1 acceptance is now mechanized as a guarded, plan-only-by-default clean-window runner — the decision-grade run itself is still outstanding.** After the first packaging attempt failed on a contested window (11/50 correct, 34/50 connection errors — already compiled above as a diagnostics-not-evidence lesson), orchestrator `a825a069` added `run_real_suite_v1_evaltower_window.py`: plan-only by default, live evaluation requires `--apply --confirm-clean-window`, and active AutoPilot blocks the run unless `--allow-autopilot-active` explicitly marks it **non-decision-grade**. Supporting repairs closed the remaining suite gaps: the materializer now accepts `code_execution` rows with `test_code` as scoreable without expected text, restoring exact class balance (`8/7x6`, `debug_root_cause=7/7`); packaged runs emit prompt-free `question_ledger.jsonl` rows; and W4 reporting is closed (`fbfde20b`: `by_task_class` accuracy/reliability/error summaries plus DAR-1 per-class regret). The W2b demand-side corpus also refreshed green on 2026-07-03: 229/229 live token-payload coverage, 1,475 mixed prompt-free rows, weighted live/historical shares 0.534/0.466 with the dominance gate passing. A plan-only smoke confirmed 50 questions / correct class and tier counts; F1's remaining acceptance is exactly one artifact — a clean-window full EvalTower per-question ledger run per P-QUAL-PROMO. Sources: [frontier-f1-real-task-corpus.md](../handoffs/active/frontier-f1-real-task-corpus.md), [progress 2026-07-05](../progress/2026-07/2026-07-05.md).
- **The clean-window real-suite run now exists as decision-grade packaging, but its result is a hard negative rather than acceptance evidence.** The 2026-07-06 stopped-window run of `run_real_suite_v1_evaltower_window.py --apply --confirm-clean-window --n 50` completed and packaged `question_ledger.jsonl` / `summary.json` under `real_suite_v1_eval_20260706T192007Z`, but scored `0/50` with `0.0` quality and `0.0` reliability. The failure mix is dominated by backend-unavailable circuit-open responses on `8070` plus repeated no-progress nudge failures on `coder_escalation` and `frontdoor`, which makes the artifact useful for method triage but still leaves W3 open. Sources: [frontier-f1-real-task-corpus.md](../handoffs/active/frontier-f1-real-task-corpus.md), [bulk-inference-campaign.md](../handoffs/active/bulk-inference-campaign.md), [progress 2026-07-06](../progress/2026-07/2026-07-06.md).
- **Eval coverage now has a tier-segregated instrument, and T3 was semantically recut as the expert/hard workflow lane.** The all-shard coverage report exposes per-tier numerators *and* cached pool denominators: at the 2026-07-05 fold, 2,457-2,488 distinct qids over ~24-25K scored rows against a 52,210-row stable pool (~4.7% upper-bound coverage, repeat factor ~9.9-10.1x), split T1 `1771-1805/21133` (~8.4%, 255 eval-bearing trials), T2 `843/26667` (~3.2%, 18 trials), T3 `160/5431` (~2.9%, 1 trial). This is deliberately **planner pressure, not policy**: the controller prompt now names thin higher-tier lanes and least-covered non-sentinel suites (`tool_use`, `agentic`, `skill_transfer`, `long_context`, `real_suite_v1`, `mode_advantage_hard`, ...), prefers tier-3 deep evals when T3 evidence is thin, and treats T1-only gains under T1/T2 hypervolume plateau as overfit risk — while `DEFAULT_FRONTIER_TIER`, EvalTower sampling, SafetyGate, and authority gates are unchanged. A companion repair keeps validation lanes schedulable: observational `deep_eval` blacklist patterns are filtered on load and refused on append, so a low-quality eval can no longer self-lock the T1/T2/T3 validation lanes. The strict Fable report carries the coverage section as advisory `attention`, never as an authority blocker. Sources: [evidence-plane-instrument-repair.md](../handoffs/active/evidence-plane-instrument-repair.md), [progress 2026-07-05](../progress/2026-07/2026-07-05.md).
- **W8's dominant terminal blocker turned out to be a sparse-baseline gate artifact — repaired as advisory-below-n=5, and replay semantics were made explicit.** A read-only trajectory diagnostic showed 27 of 43 reverted candidates all died on the same per-suite verdict: `general` regression -1.800 against a **two-question** baseline. `SafetyGate.check()` now treats a threshold-crossing per-suite regression as advisory when either side has fewer than 5 questions, unless the drop is catastrophic (>2.5 on the 0-3 scale) — full collapses stay terminal, two-question baselines stop rejecting moderate candidates. Complementary evidence-plane fixes: benign AP-24 `excluded` accumulating candidates are replay-eligible again; planner evidence now states that W8 confirmation needs replayable `numeric_trial`/`structural_experiment` candidates (`seed_batch` is observational and can never satisfy replay) and renders concrete blockers such as `unreplayable_action=seed_batch`; and a planner priority-pressure warning fires when zero replayable accumulating candidates exist. W8 remains genuinely evidence-bound after all report-plane audits (two independent sidecar audits found no report-only bug): the open tail is a recent replayable candidate plus fresh promotion eval plus sequential confirmation. Sources: [evidence-plane-instrument-repair.md](../handoffs/active/evidence-plane-instrument-repair.md), [progress 2026-07-04](../progress/2026-07/2026-07-04.md), [progress 2026-07-05](../progress/2026-07/2026-07-05.md).
- **The sequential-verdict machinery gained a multiple-testing (alpha-wealth) guard — and the exposure was real, not theoretical.** The readiness report now exposes global candidate-fingerprint multiplicity (`fingerprints_tested`, `alpha_spent`, `expected_false_confirms`, budget exhaustion), and a live guard blocks first-time candidate fresh-eval confirmation when the shared alpha budget is exhausted. Journal replay quantified the problem: 52 candidate fingerprints at `alpha=0.05` means `alpha_spent=2.6` against a default budget of 1.0 — new fingerprint confirmations are correctly disallowed until the budget policy is revisited. In the same hardening pass, the W6 audit report added a separate **core-inflation warning** (monotone core-up/audit-flat, distinct from the beyond-resolution gaming alarm) and **fence governance**: era-fenced gaming events are preserved and each must carry an `adjudicated`/`demoted`/`superseded` disposition before W6 cutover can be ready — an era fence may contextualize alarms but must not silently hide them. An observation-only paired-baseline diagnostic (`eval_details.seq_paired_baseline`, exact McNemar/sign-test vs the latest trusted same-tier reference draw, `used_for_gating=false`, computed after all gate decisions) now builds the evidence surface for a future signed amendment on paired candidate-vs-baseline screening. Sources: [progress 2026-07-04](../progress/2026-07/2026-07-04.md), [progress 2026-07-05](../progress/2026-07/2026-07-05.md), [evidence-plane-instrument-repair.md](../handoffs/active/evidence-plane-instrument-repair.md).
- **RI-10 canary methodology: operational proxies are explicitly not quality evidence, and the A/B arms got deterministic assignment plus a leak-audited scored protocol.** Three durable rules emerged. (1) *Deterministic arm assignment*: canary enforce/shadow selection moved from process RNG to a stable task-id sample key (`blake2s(canary_salt, role, task_id)`) after the evidence window came up lopsided (1 enforce / 19 shadow) — chance has no place in arm attribution. (2) *Fail-closed decision packets*: the RI-10 decision report returned `status=hold_quality_unscored` even though sample depth was ready (31 enforce / 50 shadow) and every operational proxy favored enforce (31/31 success, p95 2.58s vs 32.26s, ~2.6x lower mean cost, no escalation inflation) — success/latency/cost do not substitute for factuality scoring, so the gate holds. (3) *Scored request packets keep answer keys out of payloads*: the scored-canary plan renders payload JSONL and answer-key JSONL separately, filters rows whose expected answer is visible in the prompt (audit: 0 leaks over 60 requests, 30/30 arms, 20 per role), and a deterministic token-F1 scorer summarizes accuracy by role and arm — turning the remaining RI-10 quality gap into a prepared quiet-window dispatch rather than a missing harness. Sources: [progress 2026-07-05](../progress/2026-07/2026-07-05.md), [progress 2026-07-04](../progress/2026-07/2026-07-04.md).
- **Scorers must fail closed, and the phase-health "current-code" guard now watches the whole scorer/prompt chain.** A trial traceback exposed that `debug_scorer._word_count_by_relation()` raised on `count: null` items — an exception the seeding runner swallowed per-question, silently damaging seed batches. The repair coerces numeric counts and returns `False` (fail-closed) on missing/non-numeric thresholds. The generalizable half: `AUTOPILOT_RUNTIME_SOURCE_PATHS` was expanded so strict phase health reports the live daemon `code_stale` when the seeding/eval scorer chain (`debug_scorer.py`, `seeding_eval.py`, `seeding_scoring.py`, `seeder.py`), planner-evidence prompts, state-store policy, or `experiment_journal.py` change under it — measurement code drift now trips fail-closed health checks instead of surfacing as a later scoring surprise. A related `--require-outcome-progress` strict mode turns journal-derived outcome progress (frontier-admission staleness, keepable/wasted-eval rates) into an optional blocker; its first live smoke correctly reported `outcome_stalled` at 172 trials since last frontier admission. Sources: [progress 2026-07-04](../progress/2026-07/2026-07-04.md), [progress 2026-07-05](../progress/2026-07/2026-07-05.md).

### New (2026-07-04, ledger-derived core_v2 candidate and W8 checkpoint)

- **`core_v2` replacement is now ledger-derived rather than same-seed-repeat-derived, and activation is era-guarded.** The 2026-06-15 same-seed repeat no-go remains a stale-era diagnostic: it could not assemble 40 medium-difficulty items and was contaminated by pre-determinism infrastructure errors. The current selector instead reads folded rollover journals, applies the live `pareto_exclude_before_ts` era fence, filters corrupted/skipped/invalid/no-vector rows, and produced a review artifact with `selected=40`, `eligible=79`, `observed=923`, `source_rows=77`, `untrusted_rows=25`, and `era_excluded_rows=849`. The activation path now fails closed: a configured `AUTOPILOT_T1_CORE_ID` is refused unless `instrument_eras.yaml` has an active `autopilot_quality` row with the matching `core_id`; the generated readiness report shows the artifact/evidence pass and `missing_core_era` as the only blocker. This repairs the instrument-building path without changing live AutoPilot defaults or crossing the human-owned era boundary. Sources: [evidence-plane instrument repair](../handoffs/active/evidence-plane-instrument-repair.md), [fable5 optimizer integrity findings](../handoffs/active/fable5-window2-findings-01-optimizer-integrity.md), [progress 2026-07-03](../progress/2026-07/2026-07-03.md).
- **W8 remains the open promotion-eval tail even though W4/W6 restart/cutover state is green.** The latest checkpoint reports `161` snapshots and `43` candidate snapshots through latest trial `1107`; the candidate still has `combined_E=0.953774` versus required `100.0`, no fresh promotion eval, and no sequential confirmation. Current blockers are `combined_E_below_required`, `fresh_promotion_eval_required`, `no_recent_multi_observation_accumulating_candidate`, and `seq_confirmation_required`; status counts remain dominated by excluded/reverted/refuted evidence (`34` reverted, `6` excluded, `3` refuted). Benchmark authority claims therefore still cite W8 as data-bound rather than code-blocked. Sources: [evidence-plane ledger handoff](../handoffs/active/evidence-plane-ledger-and-sequential-verdicts.md), [evidence-plane instrument repair](../handoffs/active/evidence-plane-instrument-repair.md), [progress 2026-07-04](../progress/2026-07/2026-07-04.md).

### New (2026-07-02, sequential-verdict authority cutover + evolve-the-harness + eval-parity + GPU roofline discipline)

- **Sequential-verdict authority went live on 2026-07-02 — the keystone evidence gate flipped from "volume-blocked" to "enabled" only after both history axes cleared and a deliberate restart boundary was used.** For months the anytime-valid e-process (`AUTOPILOT_SEQ_VERDICT`) was code-complete but withheld because trusted per-question vectors and sequential shadow rows had not accrued (mid-June: `68/120` and `16/30`). By the post-reboot restart it read `trusted_vectors=193/120` and `seq_shadow_rows=116/30`, W6 audit was clear (`40/30`, `gaming_alarm=false`), and strict phase-health was current-code clean, so baseline authority (consent+state) and sequential authority were both switched on under `--max-trials 2000`. The durable rule: a benchmark-authority claim cites a passing strict readiness report plus a deliberate cutover, never the mere presence of a default-off flag; authority is disabled again on any era reset or strict-readiness regression. Sources: [evidence-plane-ledger-and-sequential-verdicts.md](../handoffs/active/evidence-plane-ledger-and-sequential-verdicts.md).
- **Promotion evals now carry a fail-closed replay + confidence-interval contract (W8), so a candidate cannot be promoted on stale or unreplayable evidence.** Forced fresh-promotion deep evals replay the pending candidate's exact numeric params or structural flags and fail closed if the candidate is unreplayable (`33c16b47`); a Phase-2.4 CI non-regression guard requires effective paired-question evidence (`r_eff`) and a one-sided delta lower bound that excludes regression before finalization, recording the CI object into promotion state (`b62bc205`); and the P-QUAL-PROMO draw contract uses trial-seeded fresh T2 draws, `n` bounded to 200–500, excludes qids seen in the last 60 days, excludes broken/artifact suites via the item-analytics suite-health table, and fails closed below 200 fresh healthy scoreable questions (`2aa3b40c`). Current reports still show `combined_E_below_required`, `fresh_promotion_eval_required`, and `seq_confirmation_required` — so W8 live promotion-eval evidence remains the last open gate. Sources: [evidence-plane-ledger-and-sequential-verdicts.md](../handoffs/active/evidence-plane-ledger-and-sequential-verdicts.md).
- **"Evolve the harness, don't train the model" is an external empirical validation of the fixed-model meta-harness loop — with a code-over-prompt mechanism preference and a per-model transfer caveat.** intake-753 (Joel Niklaus, HF Space) lifted a frozen DeepSeek-V4-Pro from 0% all-pass / 63.4 pooled to 80.1 held-out pooled on Harvey's Legal Agent Benchmark with zero weight changes, purely by evolving prompts/tools/validators. Five of the top six accepted harnesses were deterministic **code** mechanisms, not prompt edits (validating our Tier-2 code-mutation search over pure PromptForge prompt-editing); promotion used a 3-trial noise-margin rule (≥1 point clears the incumbent, mirroring our resolution-aware/`mad_noise` gate); and code fixes transferred across model families (V4-Flash +14.4 pts) while prompt playbooks did NOT (Nemotron-3 Ultra +0.4 pts), so a harness must be tuned per served model. Per MEASUREMENT.md these are single-benchmark, LLM-judge, non-peer-reviewed observations that shape the proposer contract — never gate promote/revert without local re-measurement. Sources: [meta-harness-optimization.md](../handoffs/active/meta-harness-optimization.md), [intake-753](../research/intake_index.yaml).
- **J9/HLE observe-only meta-metric validation stays a recorded negative result under the new authority regime.** Over 580 metric-bearing trials, `execution_fidelity` and `planning_stability` separate keep/revert but only mirror existing task-quality/safety signals; `feedback_interpretation`, `memory_coherence`, and `recovery_rate` remain dashboard-only. No HLE metric is Pareto-promotion-eligible before the N2 ledger/sequential-verdict redesign — the methodology rule that a new harness metric must separate accepted-vs-rejected, predict future regressions, and stay under the missingness cap before becoming an objective. Sources: [meta-harness-optimization.md](../handoffs/active/meta-harness-optimization.md).
- **The v6+iqk kernel promotion cleared its eval-parity gate with matched-question paired evidence, not aggregate throughput.** P-QUAL-PROMO required N≥200 matched full-port rows: IQK-on vs IQK-off on `worker_general` (port 8072), AA-Omniscience deterministic F1, `206` common questions, accuracy unchanged (`0.111650` == `0.111650`), avg F1 `+0.008365`, hallucination rate `-0.010929`, Omniscience Index `+0.005464`, and throughput `38.46` vs `27.78` t/s (`1.385×`). The discipline: a speed win is only creditable when the same questions are scored on both arms, the paired accuracy delta excludes regression, and both arms carry runtime attestations (IQK-off/on attest JSONs). A clean post-reboot bench and any operator production-policy decision remain separate formal gates outside the autonomous bar. Sources: [v6-iqk-promotion.md](../handoffs/active/v6-iqk-promotion.md).
- **GPU first-touch benchmarks are explicitly framed as contended-host observations, and roofline % is the primary lens.** The 2026-07-02 MI210 (gfx90a, CDNA2, 64 GB HBM2e) bring-up ran against a live 28-process CPU stack at ~106 load; every number is a first-pass OBSERVATION, not a canonical decision-gating figure. GPU-resident decode was insulated from the CPU contention (decode variance ±0.01 t/s), which narrows the `feedback_no_concurrent_inference` rule to CPU-DRAM contention rather than all co-located inference — while model-load and prefill still touched the contended host and carry noise. Effective bandwidth as a fraction of the ~1.64 TB/s roofline (32–47%) was the headline metric, and gemma4-31B + NEXTN MTP gave 1.44× decode (30.01→43.25 t/s) at 59.7% draft acceptance. Sources: [progress 2026-07-02 MI210](../progress/2026-07/2026-07-02-mi210.md).
- **Matched-precision head-to-head isolates a quantized-dequant artifact from general kernel immaturity — the durable cross-engine benchmarking method.** llama.cpp-HIP hit only 33% (Q4_K) and 47% (Q8_0) of the MI210 roofline, which looked like CDNA2 kernel immaturity until a byte-identical-weights fp16 comparison (Goedel-Qwen3-8B converted to f16 GGUF for llama.cpp, same HF weights loaded by vLLM) reached 62% roofline — proving the gap is specifically the quantized MMQ-dequant path, not general kernel maturity. The comparison was deliberately matched-precision (fp16 both sides) and matched-model, with vLLM ~11% faster per-stream (69 vs 62 t/s) and decisively ahead only on batched serving (1129 vs 909 tok/s, and llama.cpp was not tested batched, so that row is not like-for-like). Method lessons: convert to identical weights before comparing engines, hold precision constant, and label non-like-for-like rows. Sources: [progress 2026-07-02 MI210](../progress/2026-07/2026-07-02-mi210.md), [intake-759](../research/intake_index.yaml).

### New (2026-07-17 — PPL-only gates are gameable, optimized-stack matrices must not mix baselines, and authored commands need execution-grounding)

- **A PPL-only quality gate is gameable and must be replaced by multi-suite downstream evals for any kernel/drafter/quant candidate.** The Gemma Challenge's own lesson: the top *lossy* submission held perplexity (PPL ≤ 2.42) while losing **15 GPQA-Diamond / 40 MMLU-Pro points** — PPL preserved, capability destroyed. The v7 gate encodes the fix: `v7_quality_gate_runner.py` scores MMLU-Pro (TIGER-Lab, 10-choice A-J) + GPQA-Diamond at production sampling (seed 42) via the **chat** endpoint, with a per-suite `-5pp` regression threshold and both-suites-must-pass; the K5 run measured v6 and v7 candidate identically (MMLU-Pro `36.5%`, GPQA `25.6%`, 0 errors, comparator PASS). Methodology corollary surfaced the same session: an early raw `/v1/completions` attempt was discarded as a **protocol error** (Content-only, no chat template) — a quality gate that skips the production chat path is not evidence. Sources: [gemma-challenge-kernel-techniques-v7.md](../handoffs/active/gemma-challenge-kernel-techniques-v7.md), [speculative-decoding-mtp-refresh.md](../handoffs/active/speculative-decoding-mtp-refresh.md).
- **An operator-facing "optimized stack" throughput matrix must use each role's fastest VALIDATED serving config and never silently mix optimized and baseline (or stale-override) numbers.** The K35 release report tabulates every production role across context depths using its real fast path — MI210-resident no-spec (frontdoor `99→78 t/s` at 2K→32K), Gemma4 CPU composed `ngram-mod,draft-mtp` (worker `126→83 t/s` with `492/666` accepted), architect native NEXTN, Qwen3-Next default-experts — each row carrying exact command lines, model SHA/size, v7 commit/`LD_LIBRARY_PATH`, a no-contention preflight, and cleanup proof. The discipline is enforced by *invalidation*: three ingest rows that had used a stale `qwen3next.expert_used_count=int:4` MoE-expert-count override were explicitly marked "do not use," and a harness `-np>1` context-accounting bug was caught (an architect 8K attempt correctly failed, then passed after the fix). The report also states its own gaps (true `vision_escalation` lane has a measured quality defect; concurrency rows optional) rather than laundering them into a clean-looking table. Sources: [k35-optimized-stack-throughput-context-report-2026-07-17.md](../research/deep-dives/k35-optimized-stack-throughput-context-report-2026-07-17.md), [gemma-challenge-kernel-techniques-v7.md](../handoffs/active/gemma-challenge-kernel-techniques-v7.md).
- **Authored benchmark/execution commands are hypotheses until a real binary accepts their flags — ground every one against `--help`/execution, not schema+lint.** Sub-agents that wrote a 52-entry execution manifest from semantic intent produced ~30 `execution.command` strings citing runners/flags/recipes that exist nowhere on disk (no `eval_tower.py replay` CLI, no `bench_canonical.sh --recipe` flag); the well-formed YAML passed schema and lint, and only an adversarial command-audit caught it. For benchmarking specifically, this is the same failure class as the older bench-harness fixes (a speed test routed through a nonexistent subprocess): a command that has never been executed or `--help`-checked is not a runnable recipe. See [Agent Architecture](agent-architecture.md) for the full command-fabrication + 5-pass re-audit method. Sources: [inference-batch-loop.md](../handoffs/active/inference-batch-loop.md), [progress 2026-07-17](../progress/2026-07/2026-07-17.md).

### New (2026-06-25, Terminal-Bench adopt_component + mid-range filter domain constraints)

- **Terminal-Bench Core v0.1.1 (Harbor Framework) is `adopt_component` for external terminal-agent evaluation.** The Harbor repo (`github.com/harbor-framework/terminal-bench`) is the runnable harness — Docker-sandboxed, pip-installable, 89 hand-crafted tasks (SWE, ML, security, sysadmin, data science), each with an English instruction + automated test script + reference solution. Registry-versioned (19 dataset versions). Top scores: Codex CLI + GPT-5.2 at 63%, Terminus 2 + Claude Opus 4.5 at 58%. Prerequisite for local use: build a Terminus-compatible Harbor adapter over our `/v1/chat/completions` endpoint (~1 day). The dataset is hosted separately at `github.com/laude-institute/terminal-bench`. Sources: [intake-726](../research/intake_index.yaml), [eval-benchmark-cost-reduction.md](../handoffs/active/eval-benchmark-cost-reduction.md).

- **Mid-range difficulty filter (MR) is valid for cross-agent ranking on fixed task banks, but NOT for within-system regression detection.** arxiv:2603.23749 (Ndzomga, March 2026) shows that selecting tasks with 30–70% historical pass rate reduces evaluation tasks by 44–70% while maintaining rank order (Spearman ρ ≥ 0.87) across 101 agents on TB Core (23 scaffolds). The guarantee is rank preservation, not regression sensitivity. **For autopilot: the objectives are incompatible.** Ceiling questions (>70% pass rate) are strong regression signals when they fail; floor questions (<30%) signal breakthroughs. The MR filter discards both classes — the wrong trade-off for mutation-acceptance gates. **Correct autopilot application**: use per-qid pass-rate history to curate and rotate question pool slots (replace permanently saturated/floor stable-core qids), not to shrink the evaluated set. **Correct external application**: after running our stack against all 89 TB Core tasks, the MR subset (~37–50 tasks) can replace the full 89-task run for routine re-evaluations. Sources: [intake-727](../research/intake_index.yaml), [eval-benchmark-cost-reduction.md](../handoffs/active/eval-benchmark-cost-reduction.md).

- **Autopilot's 50-qid stable core is highly polarized: 3/50 mid-range, 15/50 floor, 32/50 ceiling (measured 2026-06-25).** Analysis of 141 journal trials with question_results (trials 789–969) across 1382 unique qids: only 50 qids appear in ≥50 trials (stable core). Suite breakdown: `simpleqa` (4 qids, all floor <30%), `mode_advantage_hard` (2 qids, all floor), `hotpotqa` (6 qids, 3 floor / 3 ceiling), `general` (7 qids, 1 floor / 6 ceiling), `coder`/`debugbench`/`livecodebench`/`math`/`thinking` (15 qids, all ceiling >70%), `cruxeval`/`instruction_precision`/`vl` (3 qids, the only mid-range entries). This polarization means the stable core has low differential signal between config mutations — the question pool needs curation, not subsetting. Sources: [autopilot journal analysis](../progress/2026-06/2026-06-25.md).

### New (2026-06-22, real-task-corpus eval suite + publication protocol-backfill gate)

- **A production-query eval suite is being built as a substitute for synthetic benchmarks, but its first packaging attempt failed on a contaminated window — not adopted yet.** F1 captures real session tasks (`task_record.v1` embedded in progress events; W1 taxonomy of 7 measured workload classes landed; 372 training-eligible records by 2026-06-20, weighted-dominance gate `true` at 0.585). W3 curated a 50-row YAML real-suite across 7 classes (46/50 prompts recovered, 39/50 expected-backed), but the first standalone EvalTower packaging run was during a concurrent/contested window and scored 11/50 correct with 34/50 errors (connection-refused dominated, ~0.66 quality on 0-3). A clean-window rerun is still required before any decision use; W4 (wire into decisions) is blocked on it. This reinforces the standing rule that contested-window runs are diagnostics, not evidence. Sources: [frontier-f1-real-task-corpus.md](../handoffs/active/frontier-f1-real-task-corpus.md), [progress 2026-06-21](../progress/2026-06/2026-06-21.md).
- **Public benchmark publication is gated on protocol/attestation backfill, with unverified historical rows now retired from public claims.** The public-results generator, protocol-backfill parser, public-scrub gate, internal-alias scrub, generated review queue, and review-decision overlay now classify all 374 generated rows as public-safe while routing 325 unverified historical rows to `retired_from_public_claims`. The remaining active publication blockers are 31 pre-attestation historical rows that need a real historical attestation artifact, current rerun, or retirement, plus 18 evidence-linked rows that need protocol tags. The methodology-post draft documents the April-26 canonical collapse (`+17%` -> `+1.6%`) as the main exact-number candidate, but the April 24 Q8 microkernel exact rows are paraphrase-only unless raw repack logs are found or remeasured. Sources: [frontier-f6-upstream-publication.md](../handoffs/active/frontier-f6-upstream-publication.md), [docs/publication/public-results-draft.md](../docs/publication/public-results-draft.md), [canonical-cpu-benchmarking-methodology-draft.md](../docs/publication/canonical-cpu-benchmarking-methodology-draft.md).
- **Clean-window evidence discipline held across two more A/B-style decisions, both of which recorded `hold`.** DCP-6's first live A/B (n=3/arm) cut tokens but regressed p50 latency (20.2s→32.6s) with quality unscored → `decision.status=hold`. X-MAS's constrained-policy quiet-window A/B (100 rows) improved latency (ratio 0.714) but regressed score (-0.250 vs required +0.050) → still blocked. Bulk-inference J7/DCP-6 offline replay likewise recorded `decision=hold` (latency 32.6s vs 20.2s, zero quality scoring). The pattern: a single-axis win (tokens or latency) is not a pass when the gate requires a quality-scored, regression-excluding verdict. Sources: [bulk-inference-campaign.md](../handoffs/active/bulk-inference-campaign.md), [delegation-context-preassembly.md](../handoffs/active/delegation-context-preassembly.md), [x-mas-text-routing.md](../handoffs/active/x-mas-text-routing.md).
- **J9 HLE observe-only meta-metrics did not earn Pareto promotion.** Over 580 metric-bearing trials, `execution_fidelity` and `planning_stability` separate keep/revert but only mirror existing quality/safety signals; `feedback_interpretation`, `memory_coherence`, and `recovery_rate` stay dashboard-only. No promotion eligibility until the N2 ledger/sequential-verdict redesign — a negative meta-optimization result recorded as such. Source: [meta-harness-optimization.md](../handoffs/active/meta-harness-optimization.md).

- **Tool-use experiments must prove the trial actually exercised tools before using the result as optimization signal (2026-06-05).** The active tool-use eval contract separates "model with tools available" from "model actually used the tool path." For AutoPilot/Pareto learning, the measurement contract needs per-trial evidence of tool invocation, helpfulness, and no-tool baseline comparison; otherwise a nominal tool-enabled trial can look like a tool result while measuring only ordinary text behavior. Sources: [tool-use-eval-contract.md](../handoffs/active/tool-use-eval-contract.md), [progress 2026-06-03](../progress/2026-06/2026-06-03.md), [progress 2026-06-04](../progress/2026-06/2026-06-04.md).
- **Model-card numbers are priors; local benchmark verdicts require the EPYC suite.** The Gemma 4 correction is a reusable benchmark rule: do not infer replacement viability from a newly released model card, and verify metric labels before comparing across modalities. The next action is a local suite run against the current frontdoor/vision baselines, not a prose verdict. Sources: [progress 2026-06-05](../progress/2026-06/2026-06-05.md), [multimodal-pipeline.md](../handoffs/active/multimodal-pipeline.md).
- **Benchmark default model order should follow the live stack manifest, not a frozen fallback tuple.** `scripts/benchmark/corpus_quality_gate.py` now derives its fallback model list from live `HOT_ROLES`/`PORT_MAP` membership at call time, so the quality-gate defaults stay aligned if a hot role is removed or reclassified. Sources: [progress 2026-06-15](../progress/2026-06/2026-06-15.md), [model-stack-single-source-update-pipeline.md](../handoffs/active/model-stack-single-source-update-pipeline.md).
- **Shared seeding default roles should prefer active discovery before any literal fallback list.** `scripts/benchmark/seeding_types.py` now asks `discover_active_roles()` for the fallback role order when stack priors are missing, and only uses the legacy tuple if discovery itself is empty. Sources: [progress 2026-06-15](../progress/2026-06/2026-06-15.md), [model-stack-single-source-update-pipeline.md](../handoffs/active/model-stack-single-source-update-pipeline.md).
- **Sequential verdicts remain an evidence gate until both history axes clear.** The e-process authority path is not blocked by code anymore; it is blocked by measurement volume. Readiness has accrued but is still volume-blocked (2026-06-20 live fold after trial 902: 68 trusted vectors out of 120 and 16 sequential shadow rows out of 30), so any benchmark claim that depends on sequential authority must cite a passing readiness report, not just the presence of the default-off flag. The W6 audit cutover (`--require-w6-audit`) is additionally blocked by an active trailing-30 gaming alarm even though audited rows now exceed the 30-row minimum. Sources: [evidence-plane-ledger-and-sequential-verdicts.md](../handoffs/active/evidence-plane-ledger-and-sequential-verdicts.md), [progress 2026-06-19](../progress/2026-06/2026-06-19.md).
- **Production-eval sampling knobs must be clamped server-side, not trusted from candidate configs.** The W7 eval clamp ensures production evaluation runs preserve controlled sampling and question selection, preventing a candidate from winning by mutating measurement conditions. This is benchmark-methodology state, not just AutoPilot implementation detail. Sources: [evidence-plane-ledger-and-sequential-verdicts.md](../handoffs/active/evidence-plane-ledger-and-sequential-verdicts.md), [progress 2026-06-19](../progress/2026-06/2026-06-19.md).
- **Audit streams need gaming alarms before promotion authority.** The W6 audit-block report now flags suspicious patterns where core metrics improve while audit effectiveness stays flat, making "measurement gaming" visible before a policy can ratchet. Treat audit-alarm state as part of acceptance evidence for future optimizer promotions. Sources: [evidence-plane-ledger-and-sequential-verdicts.md](../handoffs/active/evidence-plane-ledger-and-sequential-verdicts.md), [progress 2026-06-19](../progress/2026-06/2026-06-19.md).
- **In-progress clean-window runs are not evidence until the final aggregate validates.** The frontdoor G11 run `20260620_035613` first produced speed-only lookup artifacts and failed quality rows, then was resumed under the same run id with `--server-mode --skip-speed-tests --force --baseline-run 20260620_035613`. The corrected rerun is packaged in research `587c6cd`; deterministic-F1 AA labels are packaged in research `92a5602`. Frontdoor deterministic-F1 results are baseline OI `0.2753`, moe4 OI `0.2725`, and moe6 OI `0.2812`. Worker G11 run `20260620_062750` is packaged/scored in research `32f2c27` with baseline accuracy `0.1433`, hallucination rate `0.6829`, OI `0.2302`, and `52.63 t/s`. These are deterministic scorer evidence; an LLM-judge pass remains a separate decision before any tier-changing claim. Sources: [bulk-inference-campaign.md](../handoffs/active/bulk-inference-campaign.md), [research-evaluation-index.md](../handoffs/active/research-evaluation-index.md), [progress 2026-06-20](../progress/2026-06/2026-06-20.md).
- **Clean-window quality-suite commands should run through server mode and skip speed-only configs.** The failed frontdoor G11 run showed that production hosts can have a healthy server path while standalone `completion`/`lookup` subprocess binaries are absent. For AA-Omniscience and similar claim-grade quality runs, generated `run_benchmark.py` commands now include `--server-mode --skip-speed-tests`; speed sweeps are separate telemetry and should not be mixed into quality-evidence completion. Sources: [bulk-inference-campaign.md](../handoffs/active/bulk-inference-campaign.md), [research-evaluation-index.md](../handoffs/active/research-evaluation-index.md), [progress 2026-06-20](../progress/2026-06/2026-06-20.md).
- **DRACO contributes three CPU-portable LLM-as-judge construction methods, kept strictly as methodology (the numbers are closed-system observations).** From the DRACO deep-research benchmark (Perplexity AI, arXiv 2602.11685, external/preprint), three refinements are being folded into EV-9 without adopting any code or model: (1) **separate positive/negative rubric weighting** — score reward-bearing and penalty-bearing criteria independently rather than as one symmetric scalar; (2) **multi-judge ranking-stability across ≥2 local cross-family judges**, reusing the existing `src/bradley_terry.py` ranker rather than building a new one; (3) **saturation testing** — reject sentinel items that any candidate scores >90% on, because saturated items are non-discriminative. DRACO's four CONTENT axes (Factual Accuracy / Breadth-Depth / Presentation / Citation) are an ADDITION alongside EV-9's existing four MindDR-PROCESS dims, not a swap; the `deep_research_sentinel` suite already exists (MD-8 done). DRACO's leaderboard figures (e.g. orchestration beating bare base model, Perplexity DR 70.5% vs bare Opus 4.6 59.8%) are external observations on a closed Perplexity/frontier stack — not runnable here and never decision-gating for EPYC. Sources: [intake-713](../research/intake_index.yaml), [eval-tower-verification.md](../handoffs/active/eval-tower-verification.md) EV-9.
- **A calibrated benchmark core has a resolution floor: the designed `core_v2` instrument could not be assembled even from real calibration data (strict no-go).** The instrument-repair W5 effort tried to select ~40 medium-difficulty items (per-item p in [0.2,0.8]) from same-seed repeat calibration; outcomes were overwhelmingly bimodal (always-correct or always-wrong) rather than medium-band. A 3×300 batch yielded only 21 of 40 eligible items (shortfall 19); a two-repeat extension reached 33 of 40 (shortfall 7), still below target, so no `core_v2.jsonl` was promoted and the operational decision was to hold W5 open rather than lower the target or run more repeats in-window. The methodology lesson: an aggregate "n=43 T1 questions" overstates discriminating power when most items are saturated or pinned-zero; the effective discriminating set was nearer 10-14, and building a properly stratified replacement core is harder than expected. Sources: [evidence-plane-instrument-repair.md](../handoffs/active/evidence-plane-instrument-repair.md) W5, progress 2026-06-15.
- **Default eval fan-out must be capped by the reachable live fleet, not by static topology — full-only fleets get contaminated otherwise.** During the 2026-06-20 bounded accrual run, default eval concurrency trusted a static topology while the live fleet was full-only; trials 889/890 produced broad request errors and cross-slot crosstalk that look like model behavior but are infrastructure contention. Orchestrator `c13e5ae` now caps default eval concurrency by reachable live instances and records bounded `error_detail` in compact per-question rows so the failure reason is classifiable rather than scored as quality. A separate mid-`deep_eval` wedge (trial 894) was caught by a new `phase_health_report.py` stale-heartbeat detector and journaled as `autopilot_killed_mid_trial` (recovery evidence, not clean-readiness progress). Sources: [evidence-plane-ledger-and-sequential-verdicts.md](../handoffs/active/evidence-plane-ledger-and-sequential-verdicts.md), [evidence-plane-instrument-repair.md](../handoffs/active/evidence-plane-instrument-repair.md).
- **A real-task corpus is the open substitute for DRACO-style production-query sampling — gated on volume.** EPYC has no Perplexity-scale traffic, so the demand-side eval distribution is being built by passively harvesting actual operator/AutoPilot work into prompt-free, hash-ref-only `real_task_record.v1` rows. The compact training-eligible corpus now holds 372 records (>=100 class+outcome subgate met) plus 874 historical-conversation rows, but full W2 acceptance still needs a 2-week normal-use soak and non-zero token-payload coverage (currently 0/372 — the active AutoPilot process predates the token-telemetry fix, so it is stale for token capture and must not be interrupted solely for F1). Until the corpus matures, EV-9/`deep_research_sentinel` construction uses synthetic/curated queries; rubric (`llm_judge`) real-task items enter as audit/promotion material only, never as an autopilot optimization target, and per-class numbers are always reported un-pooled. Sources: [frontier-f1-real-task-corpus.md](../handoffs/active/frontier-f1-real-task-corpus.md), [eval-tower-verification.md](../handoffs/active/eval-tower-verification.md) EV-9.
- **External "#1 on benchmark X" vendor claims get a calibrated verification gate, not credit on the press release.** The Strand-Rust-Coder-14B verification handoff shows the discipline for a founder/marketing capability claim: locate the actual benchmark (RustEvo2, arXiv 2503.16922) and pin its harness to a commit SHA; confirm the model is NOT on the public leaderboard (it is not); calibrate a decision matrix against the real leaderboard distribution (a 14B fine-tune claiming #1 must beat its own 72B base-family sibling by +14.4pp — extraordinary); and require a data-contamination check (Strandset-Rust-v1 vs RustEvo2 eval tasks) plus sampling-protocol parity BEFORE a >=65% result is allowed to gate downstream investment. Always bench the un-fine-tuned base on the same harness to isolate the fine-tune delta from base-model capability. Sources: [strand-rust-coder-rustevo2-verification.md](../handoffs/active/strand-rust-coder-rustevo2-verification.md), intake-614/615/616.

- **Real-path canaries are mandatory for model-facing harnesses.** The BEP-2 falsification harness passed stub dry-runs while still failing the real `/chat` + REPL path in multiple ways: mock/real payload flags, REPL mode forcing, forbidden `open()` instructions, task-root isolation, and per-turn extraction behavior. The corrected methodology is: no-inference real-path canary with deterministic mocked LLM output, then one live single-task smoke, then full A/B. Stub validation alone only proves row/schema shape. [bep-dcp-falsification-harness.md](../handoffs/active/bep-dcp-falsification-harness.md), [progress 2026-05-27](../progress/2026-05/2026-05-27.md)
- **Root-cause claims require primitive evidence before narrative.** The BEP-2 retrospective logged several wrong but coherent diagnoses before per-turn trace evidence was inspected. The durable benchmark rule is to enumerate all observability artifacts first (`repl_tap`, structured tap, orchestrator log, scratch git diff, verifier output), cap blind fixes at one, and downgrade hypotheses to "suspected" until the primitive trace supports them. [progress 2026-05-27](../progress/2026-05/2026-05-27.md)
- **Seeding watchdogs now separate slow-model behavior from infrastructure stalls.** Slot polling labels no-token-progress hangs as `slot_stalled_no_progress`, idle-orphaned pending requests as `slot_idle_orphan`, and long empty llama outputs as `empty_generation`. This turns the previous "adaptive timeout vs genuine stall" ambiguity into explicit, env-tunable failure classes that should be treated as infrastructure evidence, not model quality signal. [progress 2026-05-27](../progress/2026-05/2026-05-27.md)
- **New harness metrics must prove signal before becoming objectives.** The HLE implementation intentionally writes execution-fidelity, feedback-interpretation, planning-stability, memory-coherence, recovery-rate, and oracle-adequacy fields in observe-only mode. The methodology rule is that no intermediate harness metric becomes a Pareto objective until it separates accepted-vs-rejected configs, predicts future regressions, and stays below the missingness cap. This prevents replacing one noisy final-task scalar with several unvalidated noisy intermediate scalars. [meta-harness-optimization.md](../handoffs/active/meta-harness-optimization.md), [autopilot-continuous-optimization.md](../handoffs/active/autopilot-continuous-optimization.md), [bulk-inference-campaign.md](../handoffs/active/bulk-inference-campaign.md)
- Claude-as-Judge scoring achieves semantic understanding of correct answers in unexpected formats, providing consistent 0-3 graded evaluation. Algorithmic pattern matching underscored by 51 percentage points on the same output in early experiments. [06-benchmarking-framework.md]
- Benchmark hardening eliminated the 89-93% ceiling effect. Expected post-hardening ranges: 30-50% for draft models (0.5-1.5B), 50-70% for general models (4-8B), 60-80% for specialized thinking models (8B+), 70-85% for large models (14B+). No model hits 90%+. [06-benchmarking-framework.md]
- Speculative decoding preserves quality (same model) while delivering 10x speed. MoE expert reduction trades quality for speed in a predictable curve: MoE4 at 85% quality/33.6 t/s, MoE3 at 78%/37.7 t/s vs baseline 89%/2.89 t/s. [06-benchmarking-framework.md]
- Instruction precision is the hardest gate for orchestration: models scoring below 70% are disqualified from frontdoor/dispatcher roles. All three coder quants (Q4KM, Q8, f16) hit an identical ceiling of 20/33 on instruction_precision -- this is a model-level weakness, not quantization-dependent. [07-benchmark-suite-construction.md, numa-orchestrator-deployment.md]
- Agent-generated benchmark questions had significant error rates: 2 answer errors in math and 17 answer errors across 76 mode-advantage tasks. All expected answers must be verified by computation, especially for modular arithmetic, financial calculations, and combinatorial counting. [07-benchmark-suite-construction.md]
- The 3-way seeding evaluation uses binary rewards (1.0/0.0) for Q-value updates to keep Q-values as faithful P(success) estimates, storing cost metrics separately in episodic memory. Cost is applied at routing time, not during learning, enabling later Optuna threshold tuning without retraining. [08-cost-aware-rewards.md]
- Nine suites now sample fresh questions from HuggingFace datasets on each run, totaling 35,560+ questions from MMLU (14K), ARC-Challenge+HellaSwag (11K), HotpotQA (7.4K), SimpleQA (4.3K), and others. Static YAML fallback for agentic, long_context, mode_advantage, web_research, and skill_transfer. [07-benchmark-suite-construction.md]
- Scoring propagation bug (fixed 2026-03-03): `question_pool.py` defaulted per-question scoring to `exact_match` ignoring YAML top-level defaults. This caused 50 web_research questions to be silently scored with exact_match instead of F1. [07-benchmark-suite-construction.md]
- SpecExec thesis partially refuted on EPYC 9655: verification cost scales 4-5x from N=1 to N=64 for Q4_K_M models. Only f16 models show near-flat behavior (1.69x at N=64). Dequantization compute overhead prevents the pure bandwidth-bound regime SpecExec assumes. [specexec-verification-profile.md]
- Optimal K for linear speculation is 16. Increasing draft-max from 16 to 256 provides zero throughput benefit because acceptance rate decay of linear sequences neutralizes verification cost savings. Tree speculation is the only path to more accepted tokens per round. [specexec-verification-profile.md]
- Self-speculation (layer skip) is not viable on either hybrid SSM or dense architectures without early-exit fine-tuning. Hybrid models suffer from SSM checkpoint/restore overhead (-44% to -52%). Dense models achieve near-zero acceptance rates (0.5-1.5%) because intermediate logits are untrained for next-token prediction. [self-speculation-benchmark.md]
- Draft model selection matters more than K: Qwen2.5-Coder-0.5B at 185 t/s with 91% acceptance dramatically outperforms Qwen3.5-0.8B at 44 t/s with 73% acceptance. The fastest drafter and best-matched target pair yield more gain than any tree or K optimization. [specexec-verification-profile.md]
- Comprehensive sweep (1,290 measurements) showed previously assumed optimal params were mostly wrong: coder tree helps contrary to prior assumption (ps=0.05 wins), 480B tree is harmful (-19%) contrary to prior assumption, and registry throughput values were inflated 2.3-3.6x from warm-cache single-prompt measurements. [progress/2026-03-21]
- The benchmark/seeding control-plane test infrastructure has achieved 100% coverage on all 10 seeding modules (`seeding_checkpoint`, `seeding_eval`, `seeding_infra`, `seeding_injection`, `seeding_legacy`, `seeding_orchestrator`, `seeding_rewards`, `seeding_scoring`, `seeding_tui`, `seeding_types`) plus `eval_log_format` via 167+ characterization tests (tranches A-I, 2026-04-14). All original 7 enforced orchestrator slice files also hold at 100%. Coverage was achieved test-only (no runtime behavior modifications) despite CRITICAL blast radius on key symbols like `_eval_single_config`, `evaluate_question_3way`, and `_precompute_embedding`. [integration-test-coverage.md, progress/2026-04-14 sessions 7-17]
- Specialist routing entrypoints (`seed_specialist_routing.py`, `seed_specialist_routing_v2.py`) advanced to 78%/76% coverage through tranches J-L, characterizing main() branches, debug-replay paths, evolve initialization failures, continuous-mode loops, preflight/resume handling, and v2 helper surfaces. Remaining gaps are concentrated in high-complexity replay/evolution hooks. [progress/2026-04-14 sessions 18-20]
- Integration test infrastructure (61 tests, 2026-04-13) uses a real `REPLEnvironment` with mock LLM primitives (`MockLLMPrimitives`), real in-memory `StubFailureGraph`/`StubHypothesisGraph` implementations (not MagicMock), and FastAPI `TestClient` with dependency overrides. This design principle -- "REPL is real, only LLM calls are mocked" -- allows testing the full graph execution loop while remaining independent of inference servers. [integration-test-coverage.md]
- Scoring Verifiers 4-metric protocol (Top-1, Bottom-1, Spearman rho, MAE) establishes that accuracy alone is insufficient for verifier evaluation: SWE-RM showed identical-accuracy verifiers producing opposite RL outcomes (AUC 0.805 smooth vs 0.710 collapse). Reasoning models dominate verification by 5-9pp. Self-evaluation bias degrades Top-1 by 10-15pp. [eval-tower-verification.md]
- Terminal-Bench 2.0 introduces outcome-driven verification (test final container state, not intermediate commands), container-per-test isolation, and three-property test design (specificity, solvability, integrity). The reward file mechanism (`reward.json` with graded metrics) is applicable to T1/T2 eval tiers needing partial credit. [integration-test-coverage.md]
- Math-Verify symbolic comparison fixes a 66% underestimation in math scoring: accuracy 0.1328 vs lm-eval-harness 0.0802 on MATH dataset. Three-step cascading comparison (string, numeric, symbolic) handles LaTeX, equivalent expressions, set notation, and percentages. Critical caveat: NOT thread-safe (`signal.alarm()`). [math-verify-integration-analysis.md]
- **DeepPlanning's rule-based deterministic scoring eliminates LLM-as-judge variance for constraint satisfaction tasks.** Every score is computed by programmatic Python rules that check constraints against the agent's output -- no inter-rater disagreement, no stochastic variance, O(1) compute per evaluation. The 8-dimension commonsense taxonomy (route consistency, sandbox compliance, itinerary structure, time feasibility, business hours, duration rationality, cost calculation, activity diversity) with 21 checkpoints provides a concrete template for building rule-based benchmark suites. All-or-nothing dimension scoring is harsh but realistic -- a plan with one temporal overlap is a broken plan. [deepplanning-agent-benchmark.md](../research/deep-dives/deepplanning-agent-benchmark.md)
- **Case accuracy vs composite reveals a critical evaluation gap.** DeepPlanning's 26-model leaderboard shows models scoring 60-80 composite (average constraint satisfaction) with near-zero case accuracy (all constraints satisfied simultaneously). The pattern holds across model families: Gemini-3-Pro-Preview achieves 41.8 composite but 0.7% travel case accuracy. This directly motivates adding case-level "all-pass" binary metrics alongside averaged quality scores in the eval tower. A growing composite-vs-case gap indicates fragility inappropriate for deployment. [deepplanning-agent-benchmark.md](../research/deep-dives/deepplanning-agent-benchmark.md)
- **Simula's double-critic rejection sampling addresses sycophancy bias in LLM-as-judge scoring.** Instead of a single "Is this correct?" assessment, two independent queries are made: "Is this CORRECT?" and "Is this INCORRECT?". Accept only when critics agree (Critic 1 YES, Critic 2 NO). A sycophantic model saying "yes" to both triggers rejection. Empirical validation on MATH: positive lift exists whenever `p(accept|correct) > p(accept|incorrect)`. LEXam shows correct failure mode: 61% rejection rate when teacher accuracy is only 57%. Cost is 2x judge inference per scored item. Applicable to Q-Scorer quality verification with prompt-only changes. [simula-synthetic-data-generation.md](../research/deep-dives/simula-synthetic-data-generation.md)
- **Simula's calibrated Elo complexity scoring enables principled difficulty stratification.** Batch-wise pairwise scoring aggregated into per-sample Elo ratings provides calibrated, cross-dataset complexity comparisons. Validation: model-assigned Elo aligns with human-annotated complexity labels on MATH (5-level) and Global MMLU (education levels). Rejected samples have systematically higher Elo scores than accepted ones. For EPYC: a `complexity_scorer.py` utility could stratify any benchmark suite by difficulty band, enabling adaptive testing that starts at medium difficulty and escalates/de-escalates based on model performance. [simula-synthetic-data-generation.md](../research/deep-dives/simula-synthetic-data-generation.md)
- **New model quality benchmarks reveal critical serving infrastructure gaps (2026-04-19).** Five models (M2.7, Qwen3.6, SG4-31b, SG4-26b-MM, SG4-26b-Q4KM) required iterative debugging: Gemma4 needed `use_chat_api + repeat_penalty 1.05 + reasoning off + KV q8_0`; Qwen3.6 entered `<think>` loops until `use_chat_api + reasoning off`; M2.7 needed `--jinja` for correct template (37% training data leakage without it). SG4-26b Q4KM proved irrecoverable (16.2%) and was deprecated. The benchmark infrastructure gained `--all-suites`, `--spec-type` passthrough, binary peak search for lookup_ngram sweeps, and per-model `disable_thinking`/`repeat_penalty` support. [progress/2026-04-19](../progress/2026-04/2026-04-19.md)
- **Context-regime coverage is now mandatory before any class-level CPU optimization conclusion (CPU23 protocol)**. A track may not claim closure or class-wide deployment guidance unless 2K/8K/32K + long-prompt-mid-stream interference were all measured AND the conclusion direction is stable across regimes (or explicitly split by regime). Prevents decode-only overgeneralization. **The CPU23 closure scope is the 3-proxy minimum-gate** (sync-bound MoE Coder-30B Q4_K_M + BW-bound MoE Qwen3.6-35B Q8_0 + dense/hybrid Qwen3.6-27B Q8) measured on 4 metrics × 3 regimes (Phase 2.2, 2026-04-28). **Explicitly NOT a class-wide closure**: Next-80B Q4_K_M, REAP-246B Q4_K_M, gemma-26B Q4_K_M, dense 32K throughput, and multi-concurrent-decode interference are deferred. The earlier 2026-04-27 partial probe on `-pg pp,tg` mode (combined prefill + 32-token decode) tested only 3 regimes × 1 metric × 2 model proxies and was DOWNGRADED on peer review (closure inflation). [cpu-context-regime-coverage.md]
- **Apples-to-apples build flags are required for any bit-exactness validation**. A 0.116-PPL chunk-1 discrepancy that initially looked like a NUMA_MIRROR Phase 1a regression was traced to pure `-march=znver5` codegen drift in fp ops vs an unflagged `-O3` build. Building a third `build_znver5/` baseline (znver5 only, no MIRROR) restored bit-exactness. The lesson: any baseline comparison for a feature flag MUST hold all OTHER compile flags constant. PPL determinism is real (re-running the same build twice produces byte-identical output), so any non-zero delta between two builds points to a real code/codegen difference, but that difference may not be the feature you intended to test. [progress/2026-04-27]
- **Closure language must enumerate which gates were met, not extrapolate**. Peer review on 2026-04-27 identified 10 closure-inflation events across CPU21/22/23/24/25 where one falsified hypothesis was generalized to a broader exhaustion conclusion: CPU22 closed by inference (15% sync ceiling) without running its own gate (≥10% on 2 sync-bound models, no crash, PPL bit-exact); CPU23 marked complete after 3 of 4 regimes × 1 of 4 metrics × 2 of 5 models; CPU24 attribution incomplete on MiniMax + 2-rep stability; CPU21 narrowed scope from libgomp+libomp matrix to libgomp only without acknowledging the gap. Remediation policy: any closure claim must explicitly enumerate which gates were met AND which were not, OR be explicitly downgraded from "closed" to "partial" or "needs revalidation". CPU20 protocol updated with retroactive artifact-bundle backfill rule. [cpu-benchmark-rigor-and-revalidation.md, progress/2026-04-27]
- **Retroactive artifact-bundle backfill is acceptable; papering over is not**. CPU20 mandates seven required artifact files per closure (README.md, system-state.txt, process-pre.txt, process-post.txt, ld_debug.log, results.csv, decision.md). When a track is already declared closed before the protocol was enforced, the backfill rule is: either reconstruct each file from existing logs + a fresh system-state snapshot + a re-run smoke command for `ld_debug.log`, OR explicitly downgrade from "closed" to "needs revalidation" with a `decision.md` stating "retroactive backfill incomplete; track downgraded". Creating empty placeholder files or fabricating decision.md without supporting artifacts is NOT acceptable. CPU21/23/24/25 are tracked for backfill in remediation Phase 2.5. [cpu-benchmark-rigor-and-revalidation.md]
- **≥5 reps required for sub-5% throughput deltas on this hardware**. Discovered via CPU22 Phase 3: an initial 3-rep Next-80B Q4_K_M measurement showed env=1 = 22.65 t/s vs env=0 = 21.31 t/s (+6.3%, would have been a positive signal for the work-stealing prototype). Re-running both at 5 reps converged to ~23.3 t/s (Δ -0.3%, neutral). The 3-rep result was a measurement artifact from cache-warmup state divergence between consecutive runs. **Rule**: 3 reps is fine for ≥10% deltas; for sub-5% deltas use ≥5 reps; for ≤2% claims consider ≥10 reps. Always report std alongside mean. [data/cpu_optimization/2026-04-28-cpu22-work-stealing/]
- **First-decode TTFT amplification under concurrent prefill is class-dependent**. CPU23 Phase 2.2 measured the long-prompt-mid-stream interference scenario via `llama-server --parallel 2`: rep-1 decode under concurrent 30K-token prefill showed 9.6× TTFT amplification on sync-bound MoE Coder-30B (4.77 t/s vs baseline 47.99), 1.15× on BW-bound MoE Q8 frontdoor, 1.08× on dense/hybrid. Steady-state continuous batching is essentially baseline (±2%) on all 3 classes — rep-2-onward decodes interleave efficiently with ongoing prefill. Per-iter latency variance in single-user mode (no interference) is uniformly low (CV 0.24-0.57%), so variance alone is NOT a stall signal absent active interference — the rep-1 stall is specifically a continuous-batching scheduler-wait artifact. [cpu-context-regime-coverage.md, data/cpu_optimization/2026-04-28-cpu23-interference-metrics/]
- **Sibling-directory `.md` references inside artifact-bundle READMEs need the agents_reference_guard hook to resolve relative-to-file-dir, not just relative-to-PROJECT_DIR**. Discovered when CPU21 Phase 2.1 README's reference to `decision.md` (sibling file in same dir) was rejected by the hook because it resolved to `$PROJECT_DIR/decision.md` (doesn't exist) instead of `$DIR/decision.md` (exists). Hook fix landed in commit `12b1e27`: try the file's own directory first, then fall back to `$PROJECT_DIR`. Strictly additive — anything that resolved before still resolves. [scripts/hooks/agents_reference_guard.sh]

## 2026-06-15 Update — Measurement Contract Tightening

- **Tool-use trials must prove they actually exercised tools before the result becomes optimization signal.** The live contract now separates "model had tools available" from "model actually used the tool path" and requires per-trial invocation evidence plus a no-tool baseline comparison. Sources: [tool-use-eval-contract.md](../handoffs/active/tool-use-eval-contract.md), [progress/2026-06/2026-06-03.md](../progress/2026-06/2026-06-03.md), [progress/2026-06/2026-06-04.md](../progress/2026-06/2026-06-04.md).
- **Real-path canaries are mandatory.** BEP-2 showed that stub validation can pass while the real `/chat` + REPL path still fails, so the durable method is no-inference canary, one live smoke, then the broader A/B. Source: [bep-dcp-falsification-harness.md](../handoffs/active/bep-dcp-falsification-harness.md).
- **Publication-grade claims now require protocol, reps, date, and attestation.** The canonical CPU methodology draft treats historical numbers without a protocol citation as observations, not decision gates, and the public-results draft keeps the same line between attested and historical rows. Sources: [canonical-cpu-benchmarking-methodology-draft.md](../docs/publication/canonical-cpu-benchmarking-methodology-draft.md), [public-results-draft.md](../docs/publication/public-results-draft.md).

## Actionable for EPYC

- The deterministic debug suite (577 curated + 55,871 HF-backed questions) enables fully automated regression testing and MemRL reward injection without Claude API costs. Any new model entering the stack can be benchmarked end-to-end with `run_overnight_benchmark_suite.sh`.
- Stratified tier sampling (`--stratify-tiers`) should be used for suites with real tier metadata (MMLU, Math, IFEval) to ensure balanced difficulty representation. Other suites fall through to uniform random.
- The mode-advantage suite provides strong MemRL routing signal by shifting the reward distribution from ~5% specialist-wins to ~25-35%, enabling the router to learn when to route rather than just that routing has a cost.
- All benchmark throughput values MUST be verified by sweep at deployment thread counts, not extrapolated from different configurations. The 2026-03-21 sweep corrected 3.6x inflated coder throughput that was biasing Q-scorer routing decisions.
- The test coverage strategy for benchmark control-plane code uses risk-weighted classification: must-test branches (recovery paths, failure control-plane, parsing fallbacks) are prioritized over acceptable-gap branches (import fallbacks, portability paths, environment-specific branches). Gate floors are raised incrementally only after corresponding test tranches land, not by forcing brittle branch-chasing. At least one dead code path was identified and fixed through this process (`output_parser.py` `common_perf_print` break shadowed by earlier skip pattern).
- Math-Verify integration (Apache-2.0, pip install + ~10-line change) should replace binary exact-match in `score_answer_deterministic()` for math suites. The 66% underestimation directly affects routing decisions. Thread safety workaround required if `_eval_question()` uses threading.
- The Scoring Verifiers 4-metric protocol (Top-1, Bottom-1, Spearman rho, MAE) should be adopted as the standard for evaluating any new verifier before it enters the RLVR pipeline. ECE and AUC tracking (EV-2, implemented) provide the calibration infrastructure.
- Terminal-Bench's outcome-driven verification pattern should be adopted for new llama-server integration tests. Container-per-test infrastructure deferred until measured need. The task.yaml metadata pattern is worth adopting for test classification across the integration test suite.
- Future work: dynamic lambda by task priority (interactive=higher lambda, batch=lower), multi-objective Pareto frontier maintenance, token-level cost accounting (prompt vs completion), and cache-aware cost reduction with RadixAttention.

## Scoring Verifiers Evaluation Protocol

The Scoring Verifiers framework (COLM 2025, NVIDIA Research) establishes a 4-metric evaluation standard for verifier quality that goes beyond simple accuracy. Accuracy alone is insufficient: SWE-RM demonstrated empirically that two verifiers with identical accuracy can produce completely different RL training outcomes (AUC 0.805 smooth training vs AUC 0.710 training collapse).

The four metrics are: **Top-1 Accuracy** (can the verifier identify the best solution), **Bottom-1 Accuracy** (can it identify the worst solution), **Spearman rho** (rank correlation between predicted and ground truth ordering), and **MAE** (score accuracy vs actual pass rate). Together these capture selection quality, rejection quality, full ordering quality, and calibration accuracy.

Key results: reasoning models dominate verification by 5-9 percentage points (o3-mini 88.2% Top-1 vs Qwen2.5-Coder-32B 79.1%). Distilled reasoning provides almost no benefit (78.2%) -- full reasoning is required. Test case scaling curves show standard models plateau at 15-20 test cases while reasoning models keep improving past 25; the sweet spot is 15 tests with a reasoning verifier. A critical methodological finding: never show the candidate solution to the test generator, as this causes 10-15pp Top-1 degradation from self-evaluation bias. Quantile selection (5 quality-stratified solutions per problem at 0%, 25%, 50%, 75%, 100% pass rates) is the recommended evaluation methodology.

Benchmark datasets are available at HuggingFace `nvidia/Scoring-Verifiers`: HE-R (164 problems, ~9.6 tests/problem), HE-R+ (164, ~764 tests/problem), MBPP-R (978, ~3.0 tests/problem), and MBPP-R+ (378, ~108.5 tests/problem).

> Source: [Eval Tower Verification](/workspace/handoffs/active/eval-tower-verification.md) -- intake-367/368, 4-metric protocol, reasoning model dominance, SWE-RM calibration gap

## Terminal-Bench Test Methodology Patterns

Terminal-Bench 2.0 (arxiv:2601.11868) provides five patterns directly applicable to the eval and integration test infrastructure:

1. **Outcome-driven verification** -- tests verify the FINAL STATE of a container, not intermediate commands. This contrasts with the current integration test approach (mock LLM calls, check return values) and recommends adding tests that start real servers, run operations, and verify end state.
2. **Container-per-test isolation** -- Docker per task with pinned dependencies and no shared state between tests. This is the biggest infrastructure gap relative to the current mock-based test suite.
3. **Three-property test design** -- Specificity (accept ALL correct end states), Solvability (oracle solution exists), Integrity (cannot cheat by shortcuts). These properties should be formalized for T0/T1/T2 eval tiers.
4. **Reward file mechanism** -- `reward.json` with graded metrics instead of binary pass/fail. Applicable to T1/T2 eval tiers that need partial credit scoring.
5. **Structured task.yaml metadata** -- difficulty, timeout budget, category tags, expected duration. Could inform a test registry for the integration test suite.

Terminal-Bench also defines an 8-category failure taxonomy (Disobey Task Specification, Step Repetition, Context Loss, Premature Termination, and 4 others) that maps to orchestrator failure modes. The recommendation is to adopt outcome-driven verification for new llama-server integration tests, defer container-per-test infrastructure until measured need (current mock-based tests provide fast CI), and adopt task.yaml metadata for test classification.

## Tulving Episodic Memory Benchmark

The Tulving Episodic Memory Benchmark (arXiv 2501.13121, ICLR 2025) introduces a complementary evaluation paradigm to the existing RULER/NIAH/LongBench/ZeroSCROLLS suite. Where those benchmarks test retrieval ("find the needle"), Tulving tests episodic memory: can a model track entity states across 200 chapters and order events chronologically? The benchmark generates synthetic book-like narratives with controlled ground truth (dates, locations, entity names, event contents) using a skewed geometric distribution for entity frequency, enabling multi-occurrence tracking evaluation.

Two metrics: **Simple Recall Score** (F1 grouped by matching event count bins: 0/1/2/3-5/6+, averaged across bins) and **Chronological Awareness Score** (average of Latest State score and Kendall τ temporal ordering score). The chronological score is dramatically harder — even GPT-5 only achieves 0.804 vs 0.942 recall. 11 datasets span 10K-1M tokens across 4 narrative styles (default, world news, sci-fi, ordered).

Key findings for benchmark methodology:
- **95% deterministic scoring.** Ground truth items are specific tokens (dates, location names, entity names). Exact + normalized string matching covers ~95% of cases. The LLM-as-judge handles only ~5% partial matches (e.g., "Bethpage State Park" vs "Bethpage Black Course" = 0.5). This aligns with our ch07 deterministic scoring philosophy.
- **Sharp cliff between 10K and 100K tokens.** Single-event recall drops 15pp, multi-event recall drops 31-33pp from 10K→100K (GPT-4o). This is a cliff, not gradual degradation. Only Gemini-2.5 family survives with <2% recall loss.
- **Reasoning models catastrophically fail at long context.** DeepSeek-R1 drops from 0.988→0.572 recall (-42%) and 0.964→0.147 chronological (-85%) from 10K→100K. o1 drops -61%/-95%. o1-mini drops -64%/-96%. These models excel at short-context episodic tasks and collapse at 100K — their effective context utilization windows are much shorter than advertised context lengths.
- **RAG chunk granularity is critical.** Chapter-level RAG (event-boundary-aligned) matches in-context performance (0.82 vs 0.81 F1). Paragraph-level RAG degrades to 0.60 because event information distributes across paragraphs. Event-boundary-aligned chunking >> fixed-size chunking for episodic tasks.
- **Fine-tuning fails for episodic knowledge.** GPT-4o-mini fine-tuned on single-event QA achieves 0.83 F1 on single-event questions but 0.00 on hallucination avoidance (0-event questions) and 0.19-0.37 on multi-event. It memorizes single facts without temporal/relational understanding.

Pre-generated datasets are available on Figshare (MIT license). Integration into our harness requires: download 20ch dataset, llama-server adapter, deterministic F1 scorer, suite registration. The 200ch variant is proposed as a YaRN context extension quality gate (P3b in research-evaluation-index).

2026-06-20 EPYC baseline: `epyc-inference-research` run `20260619_141212` completed the documented 20ch/456-QA Tulving slice on `ingest_long_context` with production/default GGUF expert settings (`--skip-moe-reduction`). Raw artifacts were packaged in research commit `b6edc64`; research `9e63af0` fixed Tulving ground-truth parsing for NumPy-array/list-repr answers and regenerated the score artifacts plus `tulving_failure_modes.md`. The corrected deterministic scorer covered `456/456` questions with no missing ground truth, avg F1 `0.4309`, Simple Recall `0.5530`, Chronological Awareness `0.1593`, and avg decode `17.27 t/s`; the benchmark log ended `448 completed, 8 skipped, 0 errors` because the corrected resume reused the first 8 rows. This result is a mixed baseline: usable lexical entity/time/location recall, poor event-content/full-detail retrieval, weak chronology, and failed zero-answer hallucination checks. It should drive targeted follow-up model-batched comparisons, not routing/memory promotion.

> Source: [intake-408](/workspace/research/intake_index.yaml) -- arXiv 2501.13121, ICLR 2025; [decision-aware-routing.md](/workspace/handoffs/active/decision-aware-routing.md) -- routing intelligence data; [research-evaluation-index.md](/workspace/handoffs/active/research-evaluation-index.md) P3b -- integration plan

> Source: [Integration Test Coverage](/workspace/handoffs/active/integration-test-coverage.md) -- intake-369, Terminal-Bench 2.0 methodology patterns, outcome-driven verification, container-per-test, three-property test design

## Math-Verify Integration for Math Benchmarks

Math-Verify (HuggingFace, Apache-2.0) provides robust symbolic math comparison that addresses a critical scoring gap: current binary exact-match scoring underestimates model capability by approximately 66% on math questions (Math-Verify accuracy 0.1328 vs lm-eval-harness 0.0802 on MATH dataset). This underestimation affects routing decisions and model selection.

The library implements a three-step cascading comparison: string match, then numeric comparison, then symbolic simplification with specialized handlers for relations, sets/intervals, matrices, and symbols. It correctly handles LaTeX-formatted answers vs plain text, equivalent expressions ("2x+1" vs "1+2x"), numeric precision ("0.333" vs "1/3"), set notation ("{1,2,3}" vs "{3,2,1}"), and percentage equivalence ("9%" = "0.09" = "9/100").

Critical integration caveats: (1) `verify(gold, pred)` is NOT symmetric -- gold answer must always be the first argument, (2) NOT thread-safe due to `signal.alarm()` usage -- if `_eval_question()` uses `ThreadPoolExecutor`, must switch to multiprocessing or set `timeout_seconds=None` with external timeout, (3) open interval "(1,2)" converts to `Tuple(1,2)` which could false-positive for coordinate pairs, (4) dependency on ANTLR4 runtime. Integration is low effort (pip install + ~10-line change in `score_answer_deterministic()`) with a fallback to exact match if Math-Verify fails.

A complementary tool, MathQ-Verify (arxiv:2505.13903), verifies question quality rather than answer quality via a 5-stage pipeline. Ablation shows Stage 5 (completeness) actually hurts F1 by +0.57pp -- deploy stages 1-4 only. A referenced finding (arxiv:2504.06514) shows that questions with missing premises cause models to generate MORE reasoning tokens, meaning filtering flawed questions also reduces inference cost.

**NIB2-03 audit applied stages 1-3 to the EPYC question pool (2026-04-21)**: 5,670 math-suite questions (aime + math + olympiadbench + physreason) scanned via `scripts/benchmark/dataset_audit/mathq_verify_audit.py`; 251 flagged (4.43%). Stage 4 (symbolic consistency between atomic assumptions and conclusions) deferred because it requires LLM-based decomposition. Signal finding: GSM8K's use of `$` as a **currency** symbol (`$10`, `$68`) collides with LaTeX math delimiters — 244 flags on the `math` suite alone. The heuristic is correct but the prompts are legible; mitigation is to gate the unbalanced-`$` check on prompts that also contain LaTeX commands. Smaller false-positive signal on AIME's `\sqrt{N}` shapes (~10 flags) will be tightened in a v2 pass. Without a working `antlr4-python3-runtime`, sympy-level parse validation is skipped to avoid flooding false positives. [`progress/2026-04/mathq-verify-audit-2026-04-21.md`]

> Source: [Math-Verify Integration Analysis](/workspace/research/deep-dives/math-verify-integration-analysis.md) -- intake-377/379, symbolic comparison, 66% underestimation fix, thread safety caveats

### New Findings (2026-06-13 — Evidence Plane And Claim Discipline)

- **The current T1 instrument had lower effective power than its nominal 43 questions implied.** Fable 5's review found that about 8 fixed T1 items could never pass under the live scoring path, while another large block was saturated. The effective discriminating set was closer to 10-14 items, with a fixed-set quality ceiling near 2.44/3.0. The instrument-repair handoff has landed the first repair batch: expected-free scorers are handled explicitly, pandas-backed code items are no longer silently broken, VL/OCR routing was traced and repaired, T0 sentinel scores are namespaced, and item analytics now classify pinned-zero suites. Core v2 selection still needs the calibration batch. Sources: [Fable 5 executive summary](../handoffs/completed/fable5-findings-00-executive-summary.md), [evidence-plane-instrument-repair.md](../handoffs/active/evidence-plane-instrument-repair.md).
- **Per-question outcome vectors are the next benchmark primitive.** The ledger branch derives stable question IDs and journals compact per-question outcomes so replay can use paired tests instead of aggregate-only comparisons. The branch is restart-bundle-ready, but the live journal still has 0 vector-bearing trials, so sequential verdicts remain gated on collecting history rather than theory alone. Source: [evidence-plane-ledger-and-sequential-verdicts.md](../handoffs/active/evidence-plane-ledger-and-sequential-verdicts.md).
- **Goodput is a valid concern, but not yet a live objective.** The replayable `task_rate_qph`, `goodput_qph`, and `tokens_per_solved_task` fields landed as shadow telemetry. The live Pareto vector did not flip because the replay only dropped 1 of 5 legacy frontier points under the proposed policy and raw task-rate admitted a zero-quality high-rate frontier candidate. Source: [objective-task-rate-goodput.md](../handoffs/active/objective-task-rate-goodput.md).
- **Publication-grade benchmark claims now require protocol, reps, date, and attestation.** The public-methodology draft uses the CPU frontdoor example where an apparent +17% improvement collapses to +1.6% under canonical controls, with the exact April 26 rows tied to named log artifacts and the older April 24 Q8 microkernel rows held to paraphrase-only unless raw repack logs are found or remeasured. Treat historical numbers without protocol IDs as observations or priors, not decision gates. Source: [canonical CPU benchmarking draft](../docs/publication/canonical-cpu-benchmarking-methodology-draft.md).
- **Repo-readiness scoring is deterministic evidence, not a qualitative review.** The first v1 scorer run rates the portfolio as Documented (L2), with root at Optimized (L4) and the three child repos at Documented (L2). This is useful as a backlog generator because criteria pass only on concrete artifact checks, but it does not certify artifact quality. Source: [repo-readiness-scorer.md](../handoffs/active/repo-readiness-scorer.md).

## Open Questions

- Claude-as-Judge integration with graded quality scores (0-3) combined with cost penalty is implemented but disabled. Enabling it would provide richer signal than binary pass/fail + cost but adds API cost.
- The llm_judge scoring method (using local worker model for physics/math semantic equivalence) has unknown accuracy compared to Claude-as-Judge. Validation data needed.
- Seeding stall classes are now explicit, but the default thresholds (`SEEDING_SLOT_STALL_WATCHDOG_S`, `SEEDING_SLOT_IDLE_ORPHAN_WATCHDOG_S`, `LLAMA_EMPTY_GENERATION_FAILURE_AFTER_S`) still need empirical calibration against real slow-but-healthy generations.
- Optuna threshold optimization for separated Q-values and cost metrics is designed but not yet implemented.
- Remaining integration test gaps (real LLM output parsing, think-harder config with actual CoT injection, budget controls with realistic token counts, streaming chat) require a running inference stack. Should these be maintained as a separate `@pytest.mark.integration_live` tier?
- The post-AR-3 analysis index defines 7 phases with 11 go/no-go metrics. Can this checklist-driven analysis pattern be generalized to future multi-day inference campaigns?
- What is the actual impact of Math-Verify's 66% underestimation correction on routing decisions? Do models currently penalized on math suites recover meaningfully when scored with symbolic comparison?
- Should Terminal-Bench's container-per-test pattern be adopted for llama-server integration tests, or does the current mock-based approach provide sufficient coverage?
- Can Simula's double-critic pattern be applied to the Q-Scorer without architectural changes (prompt-only modification)? What is the agreement rate and how does disagreement frequency correlate with model reliability?
- Should case-level "all-pass" binary metrics be added to the eval tower alongside averaged quality scores? DeepPlanning shows composite-vs-case gap is a fragility indicator.
- What is the optimal batch size for Elo complexity scoring of benchmark questions? Simula uses K appearances across batches to reduce noise -- what K is practical for our local LLM throughput?
- Does DRACO's separate positive/negative rubric weighting measurably change EV-9 deep-research scores vs a symmetric scalar on our local judges, and do two cross-family local judges (via `bradley_terry.py`) actually agree on ranking under saturation-filtered sentinels?
- Should the ledger-derived `core_v2_ledger_20260703_min5` candidate be promoted by appending the human-owned E4/core `autopilot_quality` era row, or should it stay a review artifact pending an explicit comparison against the 2026-06-15 33-item flip set?
- With sequential-verdict authority now live, does the anytime-valid e-process actually change AutoPilot keep/revert outcomes versus the retired single-shot MAD path, and does the W8 promotion-eval confidence-interval guard block any candidate that the legacy path would have promoted?
- Does the intake-753 "code-over-prompt" finding hold on the EPYC stack — do deterministic-code Tier-2 mutations transfer across our served models (gemma/Qwen/architect) better than PromptForge prompt edits, and should promotion adopt the explicit 3-trial ≥1-point noise margin as a codified rule rather than an ad-hoc gate?
- On the MI210, is llama.cpp's ~47%-of-roofline quantized ceiling closable by tuning the gfx90a MMQ-dequant kernels, and how does a quantized-vs-quantized (vLLM AWQ/fp8 vs llama.cpp Q4/Q8) matched comparison land once vLLM quant weights are available? The fp16 comparison only isolated where the gap is, not whether it is fixable.
- Does the eval-parity protocol (matched-question paired deterministic-F1 across a runtime toggle like IQK-on/off) generalize as the standard gate for future kernel/topology promotions, or is per-role/per-suite paired evidence needed before a stack-wide throughput change is credited?
- Under the repaired forced-REPL sentinel contract, do live AutoPilot evals actually journal nonzero `total_tool_calls`, and does per-suite `tool_helpfulness` on `tool_use` become a usable planner prior — or does the model still route around counted tools?
- What is the right sequential alpha-wealth budget policy now that 52 fingerprints have spent 2.6x the default 1.0 budget — replenish wealth on confirmed discoveries (e-process style), fence by era, or hold new-fingerprint confirmations until W8 finalizes a candidate?
- Is the W8 sparse-baseline advisory rule (per-suite regression advisory when either arm n<5 unless drop >2.5) the right resolution-aware threshold, or should per-suite gates require a minimum baseline sample before they can be terminal at all?
- Does raising T3 coverage (currently ~2.9%, one eval-bearing trial) via planner pressure alone produce enough hard-workflow evidence to detect T1-overfit, or does the expert/hard lane need a scheduled quota like the W6 audit block?

## Related Categories

- [Hardware Optimization](hardware-optimization.md) -- benchmark results directly depend on NUMA configuration, thread counts, and memory topology
- [Speculative Decoding](speculative-decoding.md) -- acceleration methods benchmarked across all suites
- [Routing Intelligence](routing-intelligence.md) -- MemRL Q-values derived from benchmark reward signals
- [Cost-Aware Routing](cost-aware-routing.md) -- reward formula design and cost normalization
- [MoE Optimization](moe-optimization.md) -- expert reduction benchmarked for quality/speed trade-offs
- [Agent Architecture](agent-architecture.md) -- meta-harness outer loop, evolve-the-harness fixed-model optimization, HLE observe-only harness metrics
- [Autonomous Research](autonomous-research.md) -- AutoPilot sequential-verdict authority, promotion-eval gating, and the strategy-store optimization loop these benchmarks feed

## Source References

- [GLM-5.2 reviewer capability gates](../handoffs/active/glm52-reviewer-capability-gates.md) -- GC-shadow-repair2 checklist closure, mixed-representation diagnosis, exact-answer observation, and the open matched patch-diff calibration task.
- [Inference acceleration index](../handoffs/active/inference-acceleration-index.md) -- GLM/DSA row updates that scope the near-miss repair to exact-answer evidence and keep patch-review admission open.
- [Progress 2026-07-18](../progress/2026-07/2026-07-18.md) -- Session evidence for the runner filters/refusal guard, dry-run plans, live n=24 exact-match observation, cleanup, and focused validation.
- [Model admission 2026-07-16](../repos/epyc-inference-research/docs/reference/models/model-admission-2026-07-16.md) -- Research-side durable model-admission interpretation and evidence paths for the GLM representation repair.
- [Model smoke queue 2026-07-16](../repos/epyc-inference-research/docs/reference/models/model-smoke-queue-2026-07-16.md) -- Research-side queue state showing GC item 25 closed and P-REV-1 moved behind matched reviewer-scope corpus selection.
- [Chapter 06: Benchmarking Framework](/mnt/raid0/llm/epyc-inference-research/docs/chapters/06-benchmarking-framework.md) -- Claude-as-Judge methodology, 8-suite framework, quality vs speed trade-offs, orchestrator benchmark pipeline
- [Chapter 07: Benchmark Suite Construction](/mnt/raid0/llm/epyc-inference-research/docs/chapters/07-benchmark-suite-construction.md) -- Deterministic scoring, 23-suite pool (56,448 questions), HuggingFace adapters, reconstruction instructions
- [Chapter 08: Cost-Aware Reward Design](/mnt/raid0/llm/epyc-inference-research/docs/chapters/08-cost-aware-rewards.md) -- Reward formula, cost normalization, industry consensus, extended reward dimensions
- [Self-Speculation Benchmark](/mnt/raid0/llm/epyc-inference-research/docs/experiments/self-speculation-benchmark.md) -- Layer-skip results on Qwen3.5 hybrid SSM (net negative)
- [HiSpec External Draft Benchmark](/mnt/raid0/llm/epyc-inference-research/docs/experiments/hispec-external-draft-benchmark.md) -- Checkpoint optimization validation, freeze-recurrent results
- [SpecExec Verification Profile](/mnt/raid0/llm/epyc-inference-research/docs/experiments/specexec-verification-profile.md) -- Batch verification latency curves, draft model cost profiling, large-K linear results
- [NUMA Orchestrator Deployment](/workspace/handoffs/completed/numa-orchestrator-deployment.md) -- Comprehensive spec sweep (1,290 measurements), coder quant decision matrix
- [Progress 2026-03-21](/workspace/progress/2026-03/2026-03-21.md) -- Sweep results correcting inflated registry values
- [Integration Test Coverage](/workspace/handoffs/active/integration-test-coverage.md) -- 61 integration tests (graph execution, node-level, observability, API endpoints), mock LLM + real REPL design pattern, `GraphRunContext` factory fixture
- [Progress 2026-04-14 Sessions 7-20](/workspace/progress/2026-04/2026-04-14.md) -- Coverage tranches A-L bringing all 10 seeding modules + eval_log_format to 100%, specialist routing to 78%/76%, enforced slice held at 100%
- [Bulk Inference Campaign](/workspace/handoffs/active/bulk-inference-campaign.md) -- Packages B-E results (RI-9, TrimR, difficulty, Omega, tool A/B, CF 2a-2c, TALE), post-AR-3 analysis framework
- [Eval Tower Verification](/workspace/handoffs/active/eval-tower-verification.md) -- Scoring Verifiers 4-metric protocol, reasoning model dominance, SWE-RM calibration gap, ThinkPRM process verification, cross-family verification constraint
- [Math-Verify Integration Analysis](/workspace/research/deep-dives/math-verify-integration-analysis.md) -- intake-377/379, symbolic math comparison, 66% underestimation fix, ANTLR4 parsing, thread safety caveats
- [DeepPlanning Agent Benchmark deep dive](/workspace/research/deep-dives/deepplanning-agent-benchmark.md) -- intake-412, rule-based deterministic scoring, 26-model leaderboard, multi-granularity scoring (dimension/composite/case), reasoning-mode gap data, error taxonomy, reverse-generation methodology
- [Simula Synthetic Data Generation deep dive](/workspace/research/deep-dives/simula-synthetic-data-generation.md) -- intake-410, double-critic rejection sampling (sycophancy-resistant verification), calibrated Elo complexity scoring (cross-dataset difficulty stratification), taxonomy-based coverage analysis
- [Progress 2026-04-19](/workspace/progress/2026-04/2026-04-19.md) -- Five-model quality benchmark campaign (M2.7, Qwen3.6, SG4-31b, SG4-26b-MM), serving infrastructure debugging, benchmark tooling upgrades
- [Intake entries: 15 papers](/workspace/.claude/skills/project-wiki/data/) -- ARC, MMLU, GSM8K, HumanEval, MBPP, IFEval, BFCL, SpecExec, PhysReason, and others (all verdict: already_integrated)
- [intake-713 DRACO](/workspace/research/intake_index.yaml) -- Perplexity AI deep-research benchmark (arXiv 2602.11685), verdict adopt_patterns; three CPU-portable LLM-as-judge construction methods folded into EV-9; leaderboard numbers are external/closed-system observations only
- [Frontier F1 Real-Task Corpus](/workspace/handoffs/active/frontier-f1-real-task-corpus.md) -- passive prompt-free real-task harvest as the open substitute for production-query sampling; 372 training-eligible records, W2 acceptance gated on 2-week soak + token-payload coverage
- [Evidence Plane — Instrument Repair](/workspace/handoffs/active/evidence-plane-instrument-repair.md) -- W5 ledger-derived core candidate and era activation guard, W6 rotating audit block, live-eval fan-out cap on full-only fleet
- [Strand-Rust-Coder RustEvo2 Verification](/workspace/handoffs/active/strand-rust-coder-rustevo2-verification.md) -- intake-614/615/616; external vendor-claim verification-gate methodology, RustEvo2 (arXiv 2503.16922) harness pinning, leaderboard-calibrated decision matrix, contamination/sampling-parity checks before crediting a #1 claim
- [Evidence Plane — Ledger + Sequential Verdicts](/workspace/handoffs/active/evidence-plane-ledger-and-sequential-verdicts.md) -- the 2026-07-02 sequential-verdict authority cutover (readiness-gated, deliberate restart boundary), W8 promotion-eval replay + confidence-interval + P-QUAL-PROMO draw contract, W6 audit gaming-alarm clearance semantics
- [Meta-Harness Optimization](/workspace/handoffs/active/meta-harness-optimization.md) -- J9/HLE observe-only meta-metric negative result (diagnostic-only, no Pareto promotion), the metric-must-prove-signal-before-becoming-an-objective rule, and the intake-753 evolve-the-harness research update
- [intake-753 Don't Train the Model, Evolve the Harness](/workspace/research/intake_index.yaml) -- Joel Niklaus HF Space; external empirical validation of the fixed-model meta-harness loop (frozen DeepSeek-V4-Pro 0%→80.1% held-out), code-over-prompt mechanism preference, 3-trial noise-margin promotion, per-model transfer caveat; observations only (single benchmark, LLM-judge, non-peer-reviewed)
- [v6+iqk Promotion Cutover](/workspace/handoffs/active/v6-iqk-promotion.md) -- P-QUAL-PROMO matched full-port IQK-on/off eval-parity package (N=206 common AA-Omniscience rows, deterministic F1, no paired accuracy regression, +38.5% t/s, dual runtime attestations); clean post-reboot bench held as a separate formal gate
- [Progress 2026-07-02 MI210](/workspace/progress/2026-07/2026-07-02-mi210.md) -- MI210/gfx90a GPU first-touch benchmarks framed as contended-host observations, HBM roofline-% as primary lens, matched-precision fp16 GGUF-vs-HF cross-engine method isolating the quantized MMQ-dequant artifact, GPU-resident decode insulated from CPU contention
- [intake-759 AITER](/workspace/research/intake_index.yaml) -- AMD ROCm kernel library as an honest vendor performance-ceiling reference; gfx90a/MI210 absent from its support matrix, no llama.cpp binding (part of the 2026-07-02 ROCm/MI210 intake cluster intake-759..763 grounding the GPU comparison scope)
- [Tool-Use Eval Contract](../handoffs/active/tool-use-eval-contract.md) -- REPL `CALL(...)` sentinel lane, in-memory eval secrets, Gate-3 telemetry deploy gate, 2026-07-04 activation, forced-REPL prompt-shape contract fix (`8be68732`), planner read-only boundary, parallel tool-call batching measure-first finding
- [Frontier F1 Real-Task Corpus (2026-07-05 state)](../handoffs/active/frontier-f1-real-task-corpus.md) -- guarded plan-only clean-window EvalTower runner (`a825a069`), debug-quota repair to exact class balance, prompt-free question-ledger packaging, W4 per-task-class reporting closed, 2026-07-03 token/mixed-corpus refresh
- [Evidence Plane — Instrument Repair (2026-07-05 addendum)](../handoffs/active/evidence-plane-instrument-repair.md) -- T3 expert/hard-lane semantics correction, tier-segregated eval-coverage report, W8 report-plane audits and stale_accumulating/unreplayable-seed_batch blocker taxonomy
- [Progress 2026-07-04](../progress/2026-07/2026-07-04.md) -- tool-sentinel activation + Gate-3 pass, recent-window tool telemetry gate, sequential alpha-wealth guard, W6 core-inflation warning + fence governance, W8 sparse per-suite gate repair, RI-10 deterministic canary sampler, seeding scorer fail-closed repair, DAR-4b offline preference sweep (knob-insensitive selector surface)
- [Progress 2026-07-05](../progress/2026-07/2026-07-05.md) -- maintenance restart under Gate-3 discipline, eval coverage/T3 planner pressure, deep-eval blacklist schedulability repair, W8 replay-eligibility + paired-baseline diagnostics, RI-10 hold_quality_unscored decision packet + leak-audited scored request/scoring protocol, phase-health runtime-source and outcome-progress guards
- [K35 Optimized Stack Throughput-vs-Context Report](../research/deep-dives/k35-optimized-stack-throughput-context-report-2026-07-17.md) -- operator-facing per-role optimized-config matrix (fastest validated serving path, exact commands/SHA/preflight/cleanup, memory backfill); invalidated stale-MoE4-override + harness-context-bug rows; explicit vision-escalation quality-defect gap rather than a laundered clean table
- [Gemma-Challenge Kernel Techniques → v7](../handoffs/active/gemma-challenge-kernel-techniques-v7.md) -- PPL-only gate gamed (top lossy submission held PPL but lost 15 GPQA-D / 40 MMLU-Pro) → K5 multi-suite MMLU-Pro+GPQA chat-endpoint gate at production sampling; raw `/v1/completions` attempt discarded as protocol error
- [Inference-Batch Loop](../handoffs/active/inference-batch-loop.md) -- command-fabrication audit: authored bench/execution commands ground-truthed via `--help`/execution (schema+lint blind); 5-pass on-disk re-audit localizes fabrication to leaf commands
- [Progress 2026-07-17](../progress/2026-07/2026-07-17.md) -- K5 chat-gate PASS + protocol-error discard, K35 matrix finalization, and the manifest command-fabrication audit + repair

## Per-model compression-tolerance curve as model-onboarding deployment gate (2026-04-30)

**TL;DR**: `agent-file-prose-compression.md` (NEW handoff, HIGH priority, per intake-509 follow-up) elevates per-model compression-tolerance from a one-off A/B into a **deployment gate baked into the `/new-model` onboarding pipeline**. A model that fails ≥95% baseline compliance at the candidate compression level is flagged before reaching production.

### Why this matters as a methodology pattern

Three structural advantages over runtime compression A/Bs:

1. **Static, build-time, human-reviewed.** Compression is run once per agent file, the diff is reviewed by a human, the result is committed. Non-determinism of the compressor is replaced by a human gate. No 5-minute prompt-cache pressure, no live failure modes — the eval is reproducible.
2. **Monolog target, not aggregation.** Agent reads agent file as instructions to itself. There is no downstream verifier comparing confidence markers across multiple authors, so the hedge-stripping failure mode that blocks runtime `/caveman` deployment does not apply here. The eval surface is therefore narrower and more tractable.
3. **Per-model differentiation IS the eval signal.** A 1.7B drafter has less capacity to fill in caveman-style blanks than a 30B verifier. The eval explicitly measures **the compression-tolerance curve per model**, not a single binary "does it work". This makes the eval a proper deployment-gate input, not a yes/no.

### Eval gate

Pilot: `agents/shared/ENGINEERING_STANDARDS.md`. Compress at ladder of levels (e.g. 20% / 30% / 40% / 50% reduction). For each level, run a per-model compliance suite measuring whether the agent respects RFC 2119 directive polarity (`must`/`must not`/`never`/`always`/`MAY`/`SHOULD`), procedural ordering, and bundled examples. **Gate**: ≥95% baseline compliance at ≥30% token reduction. Models that fail at any level are tagged with their max-tolerable-compression level in the registry; orchestrator routing respects the per-model max.

### Cross-model deployment-gate matrix

| Model class | Expected compression tolerance |
|-------------|-------------------------------|
| Opus-class verifier (high-capacity, instruction-following well-trained) | 40-50% likely OK |
| Sonnet-class worker | 30-40% likely OK |
| Haiku-class drafter | 20-30% likely OK |
| Local 30B-A3B coder | empirical, no priors |
| Local 1.7B drafter | likely degrades fast |

Per-model curve becomes part of the model registry and enters routing decisions: if a route requires compressed agent files but the candidate model fails the gate at the required compression level, the route is rejected at deployment time, not at runtime.

### Sources

- [intake-509](https://github.com/mattpocock/skills) Skills For Real Engineers — `/caveman` source
- intake-450 — veniceai/skills (sibling SKILL.md authoring rubric)
- intake-301 — AXI/TOON encoding (orthogonal layer)
- [`handoffs/active/agent-file-prose-compression.md`](../handoffs/active/agent-file-prose-compression.md) NEW — `/agent-file-compress` skill + per-model deployment gate

## 2026-05-04 Update — Probe B 4-config protocol formalized

The 4-config Probe B methodology used throughout 2026-04-29/30 multi-arch coverage was applied formally on 2026-05-04 to close two `todo_or_undecided` slots in the v5 deployment draft (Qwen3.5-122B-A10B and Qwen3-Coder-REAP-246B-A35B). The protocol details are now explicit in [`handoffs/completed/qwen35-122b-a10b-arch-class-probe.md`](../handoffs/completed/qwen35-122b-a10b-arch-class-probe.md) — referenced here as the canonical methodology for any new model arch-class assignment.

### Pre-flight: reproducibility tripwire

Run before trusting any new bench output:

```
OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active \
  numactl --interleave=all -- taskset -c 0-95 \
  llama-bench -m Coder-30B-A3B-Q4_K_M -t 96 -fa 1 --mmap 0 -p 0 -n 32 -r 5
```

Expected: 47-49 t/s cold-boot, ~58 t/s warmed. If outside this band, host is degraded — investigate before benchmarking anything else. 2026-05-04 baseline: 47.86 ± 0.36 t/s (cold-boot canonical).

### 4 envelope configs (single-instance 96t, n=5 reps)

| Config | Env block | Tests |
|---|---|---|
| **c0** default v5 | (none) | baseline |
| **c1** CPU1 stack | `GGML_CCD_POOLS=1 GGML_CCD_WORK_DIST=1 GGML_BARRIER_LOCAL_BETWEEN_OPS=1` | sync-bound MoE class |
| **c2** mbind off | `GGML_NUMA_REPACK_INTERLEAVE=0` | mbind-sensitive class |
| **c3** combined | c1 + c2 | hybrid SSM dense pattern (Nemotron-9B-v2) |

All configs use the canonical OMP env stack + `numactl --interleave=all -- taskset -c 0-95 -t 96 -fa 1 --mmap 0`. n=5 reps; σ should land ≤ 1% per config under tight conditions.

### Decision gates

| Outcome | Verdict |
|---|---|
| Any single config ≥ +5% with σ ≤ 1% | Wire env block into v5 deployment draft for the role |
| All within ±2% under tight Probe B | Mark `arch_class: ...` analogue with `env: {}` (default v5) |
| ≥ +1% with z ≥ 3 vs c0 (statistically significant under tight σ) | Pragmatic flip — wire the winning env block, document the marginal delta |

The "z ≥ 3" gate was applied 2026-05-04 to close 122B-A10B's c2 +1.28% (z=3.0, σ=0.42%). The flip was justified despite being below the strict +5% gate because the σ was unusually tight (0.42% per-run, n=5) and the signal cleanly separated from c0/c1/c3.

### PPL bit-exact gate ≠ perf gate

Q6_K AVX-512BW Phase A demonstrated: a kernel can be **bit-exact** (5/5 PPL identical to scalar generic across production lineup) yet still **fail the perf gate** (geomean -0.28%, REAP-246B -1.01%) because the multi-thread regime is BW-saturated — ALU width doesn't help when cycles are spent waiting on DRAM. This is consistent with `project_q8_8x8_avx512bw_outcome` "+1-3% at 12-96t (BW-saturated)" pattern.

**Methodology corollary**: PPL gate (correctness) and perf gate (deployment) are independent. A kernel passing PPL is necessary but not sufficient for default-on flip — perf gate at production-relevant thread counts must also pass.

### Failure mode: Phase A.2 strict gate failure → Phase B/C de-prioritization

When the Phase A perf gate fails (Q6_K, 2026-05-04), the compounding rationale for downstream work (Q5_K body, blanket Q{5,6,8}_K default-on flip) is **falsified**, not just delayed. The "expected aggregate +2-7% on Q4_K_M decode" projection was contingent on the kernel showing some BW-utilization improvement; with -0.28% geomean confirmed, the path is closed unless new evidence emerges (different binary, different model class, different thread regime).

### Sources (2026-05-04)

- [`progress/2026-05/2026-05-04.md`](../progress/2026-05/2026-05-04.md) — full session log with all 3 probes (Q6_K Phase A, 122B-A10B Probe B Phase 1+2, REAP-246B Probe B)
- [`handoffs/completed/qkernel-q5q6-default-on-flip.md`](../handoffs/completed/qkernel-q5q6-default-on-flip.md) — Q6_K Phase A failure documented
- [`data/cpu_optimization/2026-05-04-q6k-default-on-validation/findings.md`](../../epyc-inference-research/data/cpu_optimization/2026-05-04-q6k-default-on-validation/findings.md) — Phase A.1+A.2 bundle
- [`data/cpu_optimization/2026-05-04-qwen35-122b-arch-probe/findings.md`](../../epyc-inference-research/data/cpu_optimization/2026-05-04-qwen35-122b-arch-probe/findings.md) + [`findings_phase2.md`](../../epyc-inference-research/data/cpu_optimization/2026-05-04-qwen35-122b-arch-probe/findings_phase2.md) — 122B Probe B
- [`data/cpu_optimization/2026-05-04-reap246b-arch-probe/findings.md`](../../epyc-inference-research/data/cpu_optimization/2026-05-04-reap246b-arch-probe/findings.md) — REAP-246B Probe B

### Multi-day uptime → bimodal bench throughput (2026-05-04 evening)

After 6+ hours of full-suite benchmark activity (May-4 sweep: REAP-246B, MiniMax-M2.7, Qwen3-Next-80B, etc., ~500 GB cumulative model loads), the same canonical recipe + same binary that gave 48.71 t/s in the morning produced 28.96-29.98 t/s in the evening (5 consecutive runs). Freq sample healthy (4.3 GHz, 96/96 cores boosting), NUMA pages perfectly balanced, libomp + wrapping verified at process level, `thp_fault_fallback=0`. Drop-caches did NOT recover throughput.

Definitive A/B test ruled out launcher / subprocess.run wrapping bugs: standalone preflight + `python -c "subprocess.run([sys.executable, preflight])"` produced 29.89 / 29.98 — identical bench numbers from both invocation modes.

The phenomenon matches `feedback_host_throttle_check.md` reset behavior — reboot reliably restores canonical baseline — but the documented signature there (cores stuck at 1998 MHz) does NOT match the freq sample, indicating a DIFFERENT multi-day-uptime hysteresis (likely kernel scheduler / CCD prefetcher / NUMA balancer state below /proc visibility).

**Methodology corollary**: the canonical-recipe preflight gate (5 checks: uptime / libomp / wrapping / tripwire bench / freq under load) is necessary but NOT sufficient — multi-day uptime can produce a state where ALL gates pass except tripwire bench. **Tripwire is the only canary that actually catches this.** When tripwire fails despite freq healthy, **reboot** rather than digging for a code-side cause. Don't `--skip-preflight` to bypass — the bench results would be at 60% of canonical baseline and not comparable.

Open instrumentation idea: capture full bench process state (numa_maps, smaps, vmstat delta, perf-stat) on tripwire FAIL so we have evidence next time the state appears. Tracked as deferred work in [`progress/2026-05/2026-05-04.md`](../progress/2026-05/2026-05-04.md) § "Evening session".

Source: [progress/2026-05/2026-05-04.md](../progress/2026-05/2026-05-04.md) § Evening session, [handoffs/completed/qwen36-benchmark-fixes.md](../handoffs/completed/qwen36-benchmark-fixes.md) 2026-05-04 update.

### Stack consolidation methodology (2026-05-04)

May-4 Claude-as-Judge scoring under canonical recipe + the morning's 9-model sweep produced enough data to consolidate the production hot tier from 4 model classes (Qwen3.5-35B-A3B, Qwen2.5-Coder-32B, Llama-3-8B × 2 roles) to 2 (Qwen3.6-35B-A3B Q8 + Qwen3-Coder-30B-A3B Q4). The consolidation argument:

1. **Score before t/s, not the other way around.** Llama-3-8B at 38% on agentic and general suites was disqualifying regardless of its 13.8 t/s; Qwen3-Coder-30B-A3B at 84% overall (87% agentic, 77% coder, 90% math) wins on capability AND was already 3× faster post-canonical (43.4 t/s).
2. **Test the same model on the actual target workload's suite.** "Don't deploy Nemotron-Nano-9B for general/coder/agentic" was a defensible no-go when Nemotron's 99% was on a 3-suite subset (no coder, no math, no instruction_precision); per-suite where comparable, it beat Qwen3-Coder, but the missing suites are the ones that matter.
3. **Single-model consolidation across slots is cheap when the GGUF mmap is shared.** Qwen3-Coder-30B-A3B as coder_escalation + worker_general + toolrunner is a single 16-GB resident binding; net savings vs three separate hot-tier residents (8B + 8B + 32B ≈ 33 GB).
4. **Latency vs decode-rate as separate optimization axes.** Initial argument for keeping toolrunner on a smaller Qwen3-4B Q8 (low-latency tool emission) didn't survive the agentic-suite numbers — Qwen3-Coder won on agentic AND on decode rate. The remaining argument (TTFT on sub-100-token prompts) lacks a measurement; not enough to justify a separate slot.

This methodology generalizes: **rank candidates per-suite, weight by traffic share, prefer single-model resident bindings when capability passes the floor for ALL traffic on that slot.** A single 16-GB MoE that hits 84% on all relevant suites beats a fleet of specialists each tuned to one suite.

Source: [progress/2026-05/2026-05-04.md](../progress/2026-05/2026-05-04.md) § Evening session, [handoffs/completed/qwen36-production-upgrade.md](../handoffs/completed/qwen36-production-upgrade.md) 2026-05-04 update, `epyc-orchestrator` branch `feature/stack-swap-2026-05-04` commits fee69b8 + 587219c.

### Stack consolidation methodology — extended 2026-05-06 with role-elimination data

Two refinements landed after re-benching the architect candidates and cross-checking REAP-246B's master CSV row:

#### 1. Role elimination via cross-role comparison

`architect_coding` was supposed to be the "hardest coding escalation" target. Its model (Qwen3-Coder-REAP-246B-A35B Q4_K_M) had been deployed there since 2026-03-29 without ever being scored on the canonical 183-question battery. Master CSV cross-check (`benchmarks/results/reviews/summary.csv`) revealed:

- REAP-246B coder = **7/10 (70%)**
- Worker (Qwen3-Coder-30B-A3B Q4) coder = 23/30 (77%) — *cheaper, better*
- Frontdoor (Qwen3.6-35B-A3B Q8) coder = 29/30 (97%) — *27pp better, 3.8× faster*

The role's purpose is no longer met by its current model AND no other available model class would do better than the existing frontdoor. **Conclusion**: the role itself is redundant. Hard coding escalations route to coder_escalation (which now also runs the frontdoor model on a separate slot, shared GGUF mmap).

**Methodology rule**: when a role's stated purpose ("hardest X") is no longer served by the current model AND no alternative model in the eval pool can serve it better than an already-deployed sibling role, **eliminate the role** rather than swap. Saves a slot AND removes a routing decision the orchestrator no longer needs to make.

Result: 139 GB warm-tier RAM reclaimed; coder escalation chain shortened from 3 (frontdoor → coder_escalation → architect_coding) to 2 (frontdoor → coder_escalation).

#### 2. Architect re-bench: speed × long-context-capability tiebreaks quality-tied candidates

Re-bench of the 3 architect_general candidates (Qwen3.5-122B-A10B Q4, Qwen3.6-27B Q4, Qwen3.6-27B Q8) on the full 183-question battery:

| Candidate | Total | t/s | long_context | Verdict |
|---|---|---|---|---|
| Qwen3.5-122B-A10B Q4 | 196/210 (93%) | 12.34 | 24/27 (89%) | KEEP |
| Qwen3.6-27B Q4 | 173/183 (95%) | 6.53 | not tested | reject |
| Qwen3.6-27B Q8 | 166/183 (91%) | 4.42 | not tested | reject |

Quality essentially tied (93-95%) — but 122B-A10B is **2× faster** (MoE 10B-active beats dense 27B) AND the only candidate with proven long-context capability (89% on long_context suite). For architect/synthesis workloads, latency matters more than the 1-2pp quality ceiling, and long-context capability is hard to retrofit.

**Methodology rule**: when quality scores are tied within ~3pp, **don't swap** — speed and long-context are real differentiators. Re-bench the existing candidate properly before treating it as inferior to "newer" alternatives.

Source: [progress/2026-05/2026-05-06.md](../progress/2026-05/2026-05-06.md), [handoffs/completed/qwen36-production-upgrade.md](../handoffs/completed/qwen36-production-upgrade.md) 2026-05-06 update, `epyc-orchestrator` branch `feature/stack-swap-2026-05-04` commits `7491a12` + `dad42a0`, [`benchmarks/results/reviews/may5_architect_candidates/`](../../epyc-inference-research/benchmarks/results/reviews/may5_architect_candidates/) per-question CSVs.

### Multi-day uptime hysteresis recurs at <2d (2026-05-06)

After the 2026-05-04 evening reboot the system ran clean for ~24h, then preflight tripwire failed at **29.49 t/s @ 1.5d uptime** — earlier than the documented 2.0d warn threshold. Same pattern: freq healthy, libomp + wrapping correct, NUMA balanced, drop_caches no-op. Reboot recovered the bench to 45.55 t/s.

Pattern is now confirmed across **two independent occurrences** with different initial uptimes (2.3d on May 4, 1.5d on May 6) producing the same ~60% throughput collapse. **The 2.0d preflight uptime warn threshold is not conservative enough.** Either tighten to 1.0-1.5d, OR accept that the threshold is purely advisory and the tripwire bench is the only reliable canary (warn doesn't fail-fast; only tripwire fails preflight).

Open instrumentation: still no signal in `/proc` to distinguish fast vs slow state. Capturing numa_maps + smaps + vmstat delta + perf-stat sample on tripwire FAIL would help root-cause if the pattern persists.

Source: [progress/2026-05/2026-05-06.md](../progress/2026-05/2026-05-06.md), [`scripts/lib/canonical_recipe.py`](../../epyc-inference-research/scripts/lib/canonical_recipe.py) `UPTIME_WARN_DAYS = 2.0` constant.

### Stack consolidation arc closed 2026-05-06 — final outcome

The May 4-6 stack consolidation thread merged into epyc-orchestrator main on 2026-05-06 via merge commit `a268040` (9 commits). Final production stack quality + RAM accounting:

| Role | Pre-2026-05-04 | Post-merge | Quality Δ | RAM Δ |
|---|---|---|---|---|
| frontdoor | Qwen3.5-35B-A3B Q4 (82%) | Qwen3.6-35B-A3B Q8 (93%) | +11pp | +18 GB |
| coder_escalation | Qwen2.5-Coder-32B Q4 (77%) | Qwen3.6-35B-A3B Q8 (93%) shared GGUF mmap | +16pp | +0 (shared) |
| worker_general / toolrunner | Llama-3-8B Q4 (38%) | Qwen3-Coder-30B-A3B Q4 (84%) shared | +46pp | +11 GB shared |
| worker_summarize | Qwen2.5-Coder-32B Q4 (77%) | Qwen3.6-35B-A3B Q8 (93%) shared with frontdoor | +16pp | -18.5 GB |
| architect_general | Qwen3.5-122B-A10B Q4 (94%) | unchanged | 0 | 0 |
| ingest_long_context | Qwen3-Next-80B-A3B Q4 (warm) | promoted hot; Stage 1 of three_stage_summarization | 0 | 0 |
| ~~architect_coding~~ | REAP-246B Q4 (70% coder) | **REMOVED** (frontdoor 97% > REAP 70%) | — | **-139 GB** |
| ~~thinking_reasoning~~ | Qwen3-Next-80B-A3B-Thinking | **REMOVED** (GGUF deleted from disk) | — | 0 |
| ~~worker_pool~~ | 3-tier hot/warm pool | **DEPRECATED** (config-only; superseded by worker_general consolidation) | — | 0 |

**Net: ~157 GB warm-tier reclaimed** (139 + 18.5 - 0 frontdoor Q8 increment offset by GGUF mmap sharing).

### Long-context bench finding — frontdoor model wins

Frontdoor (Qwen3.6-35B-A3B Q8) scored **27/27 (100%)** on the canonical long_context suite — beating every other tested candidate:

| Candidate | long_context score |
|---|---|
| Qwen3.6-35B-A3B Q8 (frontdoor) | **27/27 (100%)** |
| Qwen3-Next-80B-A3B Q4 (ingest_long_context) | 25/27 (93%) |
| Qwen3.5-122B-A10B Q4 (architect_general) | 24/27 (89%) |
| Qwen3-Coder-30B-A3B Q4 (worker_general) | 16/27 (59%) — degenerate repetition |

This drove the **three_stage_summarization stage inversion**: previous design had frontdoor as Stage 1 (full context, fast draft) + ingest_long_context as Stage 2 (quality review on reduced context). Inverted: ingest_long_context for Stage 1 (SSM-hybrid linear attention scales O(n) per token at large contexts) + frontdoor for Stage 2 (highest long_context quality). Each model now matched to its stage's demand profile.

### Single-source-of-truth refactor

The May-4/6 audit caught that orchestrator_stack.py's HOT_SERVERS / WARM_SERVERS / HOT_ROLES / SERIAL_ROLES were hand-edited dict literals duplicating wiring data already in NUMA_CONFIG. Adding/removing roles required editing 5 places consistently. Architect_coding registry-removal had been propagated to NUMA_CONFIG but NOT to HOT_SERVERS — `start` would have crashed.

Refactor (commit `bd2455d`):
- New `ROLE_LAUNCH_META` dict: per-role tier + mode + aliases + mode-specific kwargs (15 lines)
- `_build_servers_from_classification()` computes HOT_SERVERS + WARM_SERVERS at module load from NUMA_CONFIG + ROLE_LAUNCH_META
- `_validate_role_classification()` runs at module load; rejects port collisions, NUMA_CONFIG/ROLE_LAUNCH_META mismatches, missing classifications
- `validate_against_registry()` runs at `start` command; warns on drift between launcher and registry's process_layout / server_mode

Result: adding a role is now 2 places (NUMA_CONFIG + ROLE_LAUNCH_META) with self-validation; removing/renaming catches dangling refs at module load instead of at launch.

Source: [progress/2026-05/2026-05-06.md](../progress/2026-05/2026-05-06.md), [`epyc-orchestrator` merge `a268040`](../../epyc-orchestrator/), [`handoffs/completed/qwen36-production-upgrade.md`](../handoffs/completed/qwen36-production-upgrade.md).

## 2026-05-08 — Five bench harness fixes surfaced during gemma4 evaluation

The 2026-05-08 worker_general swap (gemma4-26B-A4B MTP) ran the harness end-to-end across two suites under conditions that exposed five distinct latent bugs. All were silent or partial failures pre-fix; none would have flagged in routine sweeps because each only manifests under specific config combinations.

### 1. `--lookup` flag deprecated upstream — wasn't replaced in our path

`scripts/lib/executor.py:339` still appended a literal `--lookup` to llama-server cmds for any config requesting prompt lookup acceleration. Production llama-server rejected this with `error: invalid argument: --lookup` (the flag was renamed to `--spec-type ngram-simple --spec-ngram-size-n N` in upstream months ago). Every `*_lookup` and `*_lookup_n*` config had been failing exit-1 silently for an unknown duration. Fix: route through the upstream flag, plumb a new `spec_ngram_size_n` parameter through `ServerManager.start` and the harness `_start_server` wrapper.

### 2. Lookup ngram sweep wasn't actually varying ngram

`_sweep_lookup_ngram._test_ngram` issued an inference call to the running server for each candidate ngram value (n=2, 3, 5, 9, 17, 33, 65, 128), assuming the legacy `--lookup` flag's per-request override semantics. Upstream `--spec-type ngram-simple` is **server-startup-fixed**, so all 8 sweep steps were running the same fixed-ngram server and reporting duplicate tps. Fix: restart the server with `spec_ngram_size_n=n` per sweep step; `_ServerState` gained a `lookup_ngram` slot to track the current value.

### 3. Port-bind race after rapid restart cycles

The MoE expert sweep + speculative-decoding draft-model swaps in a single bench run cycle the server through 6+ restarts. Some of those restarts left port 8080 in TIME_WAIT or partially released; the next launch hit `couldn't bind to server socket: ... double free or corruption` and crashed before model load. Fix: new `ServerManager._is_port_free(port)` + `_reserve_port(preferred, timeout=30, hops=10)` static helpers polled-then-hopped to the next free port (cmd argv updated to match), with a 30s wait before fallback. All downstream URLs use `self.port` and follow the hop transparently.

### 4. Speed tests routed through subprocess that didn't exist

`_run_speed_test` (the standard speed-only config runner) called `executor.run_inference` (the **subprocess** path that spawns standalone `llama-completion` / `llama-speculative` / `llama-lookup` binaries), even when a server was running with the right state. The harness's own preflight log warned `Missing subprocess binaries (server-mode still works): completion, speculative, lookup` — those binaries aren't built on production hosts. Every `spec_*` and `*_lookup` speed test exited 1 with `binary not found`. Fix: `_run_speed_test(..., ss=None)` accepts the server state and prefers `ss.server.run_inference` when running, mirroring the `_sweep_lookup_ngram` pattern. Backwards-compatible default.

### 5. `--skip-moe-reduction` kept moe`<X>`_* configs when X equaled the production target

`registry.get_baseline_experts(role)` had a fallback chain `accel.baseline_experts → accel.experts → 8`. The middle term was wrong: `accel.experts` is the **production-target reduction count** (e.g. `experts: 4` for "we want to deploy with 4 experts active"), NOT the **GGUF default** (the model's native expert count, e.g. 8 for Qwen3-30B-A3B). The `--skip-moe-reduction` filter `c.moe_experts is None or c.moe_experts == baseline_experts` then kept `moe<production_target>_*` configs because they "matched the baseline". 19 of 22 MoE roles in the registry were vulnerable. Fix: removed the dangerous `accel.experts` fallback; added explicit `baseline_experts` to all 20 affected role blocks (8 for Qwen3 family, 10 for Qwen3-Next-80B-A3B verified via direct GGUF metadata read).

### Plus

- New `--skip-speed-tests` CLI flag filters all `cfg.speed_test_only` configs for quality-only runs (e.g. tool_compliance-focused evaluations).
- `tool_compliance.yaml` gained `inference_params.max_tokens: 2048` (was inheriting the global default of 512); pre-fix, gemma4 `t3_q2_llm_delegation` truncated at exactly 512 ctok mid-prompt and scored 0/3.
- Added `constraints.forbid: [prompt_lookup]` to gemma4_31b/26b registry blocks — MTP-only models can't coexist with ngram-simple lookup (both consume the spec-decode slot).

### Lessons that generalize

- **Silent-failure backstop**: a CI guardrail that asserts every `*_lookup` config produces `tps > 0` would have caught (1)–(4) months earlier. The harness currently has no such assertion — every speed test that fails exit-1 just gets logged and skipped.
- **Field-name semantics in registries**: when a YAML key has both a "production-target" and a "GGUF-baseline" interpretation, name them distinctly (`experts` vs `baseline_experts`) AND have the registry loader REQUIRE both for any MoE role (or default the missing one explicitly with a warning, not silently fall back to the wrong one).
- **Flag deprecation needs a sweep**: when an upstream flag is renamed, search for it across all callers. The `--lookup` rename existed in upstream's CHANGELOG but didn't propagate to our harness.

Source: [progress/2026-05/2026-05-08.md § session 2 § Bench harness bugs fixed](../progress/2026-05/2026-05-08.md), commits `f106b7a` (harness fixes) + `a295618` (bench data) on `epyc-inference-research:feature/preflight-canonical-gate`.

## Agents' Last Exam (ALE) — not_applicable holds (2026-06-12)

intake-690 (arxiv:2606.05405) is a 1,000+-task occupation-grounded (O*NET/SOC 2018, 13 clusters → 55 subfields) "living benchmark" for long-horizon professional agent workflows, co-developed with 250+ industry experts; frontier agents score only **2.6% full-pass at the hardest tier**. The deep-dive stress-tested the not_applicable verdict and **confirmed it** — but corrected the maturity framing: ALE *is* released and runnable (`ale_run` toolkit, 150 public tasks, deterministic leak-resistant executable graders), so it passes "released?" and "verifiable?". The blocker is the **execution substrate**: tasks require provisioned cloud **Windows/Linux VMs running real professional software, driven by CUA computer-use agents** (screenshot/click/type via an MCP GUI bridge) — categorically outside our CPU-served `llama.cpp` + REPL/`CALL(...)` text harness. The only transferable nugget is the **O*NET/SOC occupational-coverage frame** as an orthogonal Ch07 *authoring lens* (our suites index by capability/source benchmark, never by occupational coverage) — needs no ALE data or infra. The sub-1%/2.6% pass figure is **non-commensurable** with our per-suite closed-form quality scores and must not be imported as an autopilot difficulty target. Precedent: AppWorld (intake-516, a *simpler* multi-app agent benchmark) was already deferred 2026-04-30 for "feasible but no current eval gap" → ALE defers *a fortiori*.

**Methodology cross-ref (from OBLIQ-Bench, intake-689, see search-retrieval.md):** the `gap(t)=V_t−R_t` retrieval-verification gap metric and the oblique-query construction recipe are reusable benchmark-construction techniques for authoring a harder code/KB retrieval eval — distinct from reusing OBLIQ's out-of-domain dataset.

Sources: [`research/deep-dives/2026-06-12-agents-last-exam.md`](../research/deep-dives/2026-06-12-agents-last-exam.md), [`research/deep-dives/2026-06-12-obliq-bench-retrieval-eval.md`](../research/deep-dives/2026-06-12-obliq-bench-retrieval-eval.md), intake-690/689.

### New (2026-07-21, judge validity: anchoring, agreement metrics, and search-time contamination)

> **Review flag (project-wiki writer-evidence policy):** model-compiled, not adopted until human or measured review. The measurement trust boundary is human-amendment-only; every item here is an operator-review proposal, not an applied change.

- **Judge-selected best-of-N inflates judge-measured scores while true quality stays flat, and cross-family ensembling is only a partial defense.** arXiv:2607.05904 measures a judge-vs-truth gap widening from **0.20 at k=1 to 0.588 at k=16** on LiveCodeBench while the selected candidate's unit-test pass rate moves only 0.27 → 0.29. Hacked errors transfer across judge families (Qwen/Llama/Gemma) and a three-family minimum-vote ensemble still accepts ~55% of hacked wrong answers — which directly qualifies the cross-family verification rule recorded as our strongest defense. The effective mitigation is **de-anchoring**: requiring the judge to commit to its own answer before or without seeing the candidate drops false-positive rate from 0.906 to 0.012, whereas a plain "verify/recompute" instruction is measured to do nothing (FPR 0.719). Sources: [eval-tower-verification.md](../handoffs/active/eval-tower-verification.md), [reviewer-decision-plane.md](../handoffs/active/reviewer-decision-plane.md), [progress 2026-07-21](../progress/2026-07/2026-07-21.md).

- **Rubric-based LLM judges are reproducibly hackable — but verifiable rewards are not a safe harbor either.** arXiv:2606.04923 (Tsinghua KEG) builds a controlled environment injecting a known bias into an otherwise unbiased judge and shows policies discover and exploit it, with discovery latency governed by bias-task entanglement and exploitation capped by whether the model can cheaply emit the pattern (format bias ~66% elicitation vs 95-100% for lexical/tone/self-praise). It also finds **in-domain capability degrades while aggregate general benchmarks stay flat**, so an aggregate suite is an unreliable tripwire for scorer gaming. Honest scope: it does not run a head-to-head against verifiable rewards, and our own corpus records deterministic verifiers being gamed 32.8% of the time — so neither reward class is a default. Sources: [eval-tower-verification.md](../handoffs/active/eval-tower-verification.md), [reviewer-model-ablations.md](../handoffs/active/reviewer-model-ablations.md), [reviewer-calibration-accounting.md](../handoffs/active/reviewer-calibration-accounting.md).

- **Raw percent agreement is not an adequate validation statistic for a judge, and our constitution does not currently require a better one.** arXiv:2606.00093 (Rao & Callison-Burch) shows that on non-degenerate binary judge-vs-human data Pearson/Spearman/Kendall/phi/MCC all collapse to the same number, so reporting several manufactures an illusion of corroboration; Cohen's kappa is the one common coefficient adding information, because its marginal-sensitive normalization exposes judge-vs-human positive-rate drift. Abstention handling is a **choice of estimand, not preprocessing**. A full-text search of the 878-entry intake index returned zero prior hits for kappa/Krippendorff/inter-rater, and neither MEASUREMENT.md nor MEASUREMENT_POLICY.md mentions an agreement statistic — the draft P-REV-1 reviewer grammar reports raw FA/FR/yield/CR with no chance correction. Caveat to carry: the paper does not discuss Gwet's AC1, and the kappa paradox bites hardest on the deliberately skewed near-miss corpora we build. Sources: [reviewer-calibration-accounting.md](../handoffs/active/reviewer-calibration-accounting.md), [eval-tower-verification.md](../handoffs/active/eval-tower-verification.md), [reviewer-model-ablations.md](../handoffs/active/reviewer-model-ablations.md).

- **Live-web agentic benchmarks carry a validity defect that no field of our claim grammar captures.** arXiv:2606.05241 defines Search-Time Contamination — an agent retrieving the benchmark's own metadata, question text, or answer instead of reasoning — with a three-tier severity taxonomy and up-to-4pp measured inflation across six public benchmarks, and per-agent leakage rates spanning ~0-78% depending on the retrieval stack. Our own exposure was checked and is currently **zero**: the `gaia` suite contributes 0 questions to the live pool (dataset gated and never downloaded), no web-search tool exists in `scripts/benchmark/`, `web_access` defaults False with only `frontdoor` enabling it, and the eval tower hits llama-server ports directly with no tool registry. The forward guard is to re-check if the absent-source suites are ever populated. Sources: [minddr-deep-research-mode.md](../handoffs/active/minddr-deep-research-mode.md), [eval-tower-verification.md](../handoffs/active/eval-tower-verification.md), [progress 2026-07-21](../progress/2026-07/2026-07-21.md).


## Calibration instrumentation era (compiled 2026-07-22)

The eval tower crossed from accuracy-only to **decision-grade calibration** in one arc
(sources: `handoffs/active/eval-tower-architecture-audit-2026-07-20.md`, the four 2026-07-22
audits, `progress/2026-07/2026-07-22.md`):

- **Fake-zero elimination**: absent confidence had emitted ECE/AUROC `0.0` — placeholder values
  masquerading as perfect/degenerate measurements. All decision-facing aggregates now emit
  `None` + `confidence_is_real` provenance; `decision_grade` demotes on reliability<0.8 or fake
  calibration, with reasons[].
- **The chat-path n_probs gap** (`83f53382`): llama's OpenAI-compat endpoint ignores the native
  `n_probs` param; the chat backend never translated to `logprobs`/`top_logprobs` nor parsed
  them back — and every eval role is a chat-completions role. One gap = every calibration void.
  First decision-grade rows (EV-4c HE-R+): frontdoor ECE 0.253/AUROC 0.634, worker 0.322/0.575,
  coherent ordering, triple-reproduced accuracy base (0.7085).
- **Instrument-lies theme**: the run-progress display counted excluded error rows as wrong
  (53.8% panic that was really 76% + honest exclusions); the `/slots` busy-sampler undercounted
  (a "scoring-bound" theory died when sidecar timing showed gen 9.7s / scoring 23ms). Verify the
  instrument before the conclusion — both false alarms came from probes, not the system.
- **Arm operability**: per-question sidecar rows now persist full answers + wall-clock intervals
  (`ended/started/elapsed/scored_at_s`) → concurrency depth (proven MAX OVERLAP 4) and offline
  re-scoring from the artifact alone; `--retry-errors-from` (error rows) and
  `--resume-incomplete-from` (interrupted arms, dataset-sha-guarded) make long arms recoverable.
- **REL-1 held under fire**: a mid-eval API restart burned 532 questions into *excluded error
  rows* — never scored wrong; the paired accuracy stayed honest (0.764 vs 0.762).

## Campaign terminal + instrument completion (compiled 2026-07-23)

The 2026-07-22/23 measurement campaign closed with the quality gate LIVE: era-fenced reseed
(T1 1.600 on the designed core_v2, escalation-off declared and artifact-verified; T2 1.891),
operator-applied via the human-amendment boundary. Constitution gained three acts: P-CAL
(domain-scoped calibration — code decision-capable, math observational pending EV-CONF-2's
salient-token source), P-PAIRED (McNemar verdicts, exact≤25/normal-CC above), and the
E4-quality-core-v2 era row. Scorer coverage CLOSED wholesale: a full-pool audit found exactly
2 gaps in 79,480 rows (f1_list, structural_exact_match), implemented byte-identical to research
reference adapters with the B7 pin unchanged. The judge-scoring class was fixed at the INGRESS
(calls had auto-routed into the REPL loop via the OpenAI-compat endpoint). The vl suite —
"dead 0/376" for six weeks — was recovered by re-measurement (truth-slice 20/20): the standing
lesson is that dead-suite claims EXPIRE and the ~7-minute instrumented truth-slice is the cheap
re-validation. Baseline discipline extracted: six refused attempts = six real production defects,
zero garbage numbers banked (missing tool libs, migration NULL-crash, client-side budget
override + five read caps, dead judge port, pre-REL-1 zero-tolerance gate, schema ceiling).
Sources: progress/2026-07/2026-07-2{2,3}.md, core-v2-design-note, decision-plane audit records.

### Probing the episodic store: three leakage traps, measured (2026-07-27)

Any supervised probe over `sessions/episodic.db` + `embeddings.faiss` hits the same three traps.
Each was found by inverting a result mid-analysis, not predicted in advance, so they are recorded as
measured properties of *this* store rather than general advice.

**1. The unit of identity is the embedding, not the `context` string.** The `context` column carries
material beyond the text that was actually embedded, so hashing it splits identical vectors into
different groups. Measured on the live store: **26,995 `frontdoor` routing rows carry only 2,384
distinct vectors** (~11× reuse), and **497 vector-hashes span more than one context-derived group**.
Group by a hash of the float32 vector bytes. Note 2,384 is the same figure `comp_region_probe.py`
flags in its own docstring — the store's effective dimensionality is far lower than its row count
suggests, and every probe over it must be designed around that.

**2. `GroupKFold` is deterministic — it cannot produce a stability estimate.** A "multi-seed" check
wrapped around it varies only the estimator's `random_state`, which for `lbfgs` changes nothing. The
observed symptom is a reported seed spread of *exactly* `0.0000`, which reads as "extremely stable"
and actually means "the control never ran." Use `GroupShuffleSplit` (or shuffle group assignment)
when you want variance.

**3. Row-weighted pooling is carried by a handful of objectives.** Group sizes here are extremely
skewed: for `frontdoor`, the **top-10 groups hold 33% of all rows while the median group size is 1**.
A pooled row-weighted metric is therefore substantially a measurement of ~10 repeated boilerplate
prompts. Report **group-weighted** (one prediction per distinct objective) as the headline. The two
views can disagree sharply and in *either* direction — in the 2026-07-27 escalation probe, frontdoor
was 0.784 row-weighted vs 0.575 group-weighted, while `worker_general` moved the other way, 0.579 vs
0.726. Ranking roles by the wrong view inverts the conclusion about which surface has signal.

**Non-negotiable controls for this store**: a shuffled-label run (must land ~0.5, else the harness
leaks), an ungrouped run retained *only* as a leakage anchor, and a minimum-positives guard so a
degenerate class (`worker_vision`: 4 failures in 1,456 rows) is skipped rather than reported as a
number.

Sources: `scripts/analysis/escalation_prediction_probe.py`, `scripts/analysis/comp_region_probe.py`,
`handoffs/active/learned-routing-controller.md`, `progress/2026-07/2026-07-27.md`.

## Compiled Update — 2026-07-29: eval-instrument correctness, the (model, scaffold) unit of report, and external-figure provenance

**Confidence**: verified for the first-party code/host findings (each closed by
executing the failure, not by reading the code); **observation-grade** for every
external figure quoted below, per MEASUREMENT.md. Both handoff records were
written by the same session that produced the fixes, so the *narrative* is
single-source — what is independently corroborated is the execution evidence
(9/9 and 14/14 checks) and the host measurements the fixes rest on.

### Two live correctness defects in the scoring/agentic-SWE path — both were doc/impl divergences

The scoring stack asserted two guarantees it did not provide. Neither would have
been found by inspection of the documentation, because the documentation was the
thing that was wrong.

1. **`subprocess.run(timeout=…)` kills only the DIRECT child.** Descendants
   survive the timeout as orphans, so a scored snippet that forks keeps running
   on the box after its trial is recorded. Fix: `start_new_session=True` plus
   `os.killpg(os.getpgid(proc.pid), SIGKILL)` on the timeout path. Verified by
   execution (9/9 checks) including the real orphan case — a detached grandchild
   that previously outlived the timeout.
   [`scoring-infra-standardization.md`](../handoffs/active/scoring-infra-standardization.md) §2a-iii

2. **No `/testbed` state reset between agentic-SWE trials**, so a crashed or
   dirty trial silently contaminated its successor and the "clean at base"
   assumption written into the protocol had never been verified. Fix:
   `DockerEnv.reset_testbed(base_commit)` called **fail-closed at the top of
   `run_instance`** (on error: status `testbed_reset_failed`, zero turns, empty
   patch — a silently-failed reset is exactly the contamination being fixed).
   Verified by execution (14/14 checks).
   [`scoring-infra-standardization.md`](../handoffs/active/scoring-infra-standardization.md) §2b-agentic-0

### `RLIMIT_NPROC` is the wrong mechanism for bounding a scorer — not merely unimplemented

`RLIMIT_NPROC` is enforced **per real UID, not per process tree**. This host runs
**~9,534 threads under uid 1000** (5,688 of them llama-server), so any per-scorer
cap fails the child's *first* fork under normal fleet load — and fails
**nondeterministically** as load varies, turning the scorer into an instrument
whose results track how busy the box is. The correct mechanism is cgroup v2
**`pids.max`** on the scorer's own subtree (counts only its own descendants,
unaffected by co-tenants), paired with `cpuset.cpus`/`memory.max` pinned to the
eval quadrant (cpuset 112-119) so the whole bound is enforced at the cgroup
rather than per process. Verified available on this host: `pids` controller
present, child cgroup creatable, needs `+pids` in `cgroup.subtree_control`.
Generalization: **a per-process resource limit is not a per-subtree resource
limit**, and choosing the wrong one produces an instrument that is silently
load-dependent.

### `git clean -fdx` is wrong in a SWE-bench testbed

The reset uses `git reset --hard <base_commit> && git clean -fd` — the omission
of `-x` is deliberate. `-x` also deletes **ignored** files, which in a SWE-bench
testbed include the `.egg-info`/build artifacts left by `pip install -e .`;
deleting those breaks imports and **manufactures false failures**. `reset --hard`
rather than `checkout -- .` so that an agent *commit* is undone too. The
regression test asserts the ignored artifact survives and the agent commit is
rolled back.

### An agentic-coding score is a property of the (model, scaffold) pair

The strongest evidence in this batch for treating the harness as part of the
instrument: at **fixed model and fixed reasoning effort**, a harness *revision*
(v1.2→v1.5) moved the score **+7.23**, which is **larger than the entire
5.08-point architecture spread at that same setting**; a published table shows a
6.8-point spread across three scaffolds on one model and one benchmark, with the
ranking against a competitor **flipping** between scaffolds. The counterweight
must always travel with the other half (a one-step model swap buys ≈3.6× the
full harness ladder, a reasoning-budget bump ≈2.0×): quoting either alone misuses
the number in one direction or the other. Grade: n=1 per cell, closed frontier
models, public demonstration set → **OBSERVATION only**; it gates nothing.
[`harness-selection-and-integration.md`](../handoffs/active/harness-selection-and-integration.md) §HS-12

Consequence adopted as a disclosure standard (six points, all required before any
external SWE-bench figure is quoted in a decision context): harness identity +
version pinned; **the model-harness pair as the unit of report**; denominator +
split; dataset mutation disclosed; n/reps/seeds; contamination posture.
[`scoring-infra-standardization.md`](../handoffs/active/scoring-infra-standardization.md) §2b-swe-hygiene

Corollary on commensurability: a vendor-self-reported **67.0% SWE-bench Verified
(335/500, thinking-off, n=1)** is **not commensurable** with our sealed
SWE-oracle-40 row (`23/40`) — different instrument, different denominator,
different scaffold. It may not be set beside an authority row.
[`architect-model-selection-bench.md`](../handoffs/active/architect-model-selection-bench.md) §2026-07-29 intake dive

### Provenance downgrades that kill four external figures

- **A vendor uplift claim dies when the vendor's own baseline is reconstructed.**
  One fine-tune's reported +5.00/+6.00/+5.33 rests on a baseline running ~10pp
  *under* the base model's official published numbers — so the claimed uplift is
  **smaller than the vendor-vs-vendor gap on the identical base model**, and the
  headline 69.40 sits *below* the base model's published 73.4.
- **Public-set provenance.** All PRO-LONG numbers are on the ARC-AGI-3 **public**
  set, which the benchmark's own authors state is "emphatically not a valid
  measure of progress" and will "never" appear on their leaderboard; the harness
  is to high confidence one those authors measured showing extreme bimodality
  (97.1% / 0.0%). Keep the internal ablations; discount the SOTA framing.
- **A triple-confounded ablation is non-citable.** AREX's +11.8pt ACU figure has
  no masking arm, no arm separating observation-dropping from the learned
  summary, and its "w/o ACU" is an **OOD ablation of a model explicitly trained
  on that very capability**.
  [`context-folding-progressive.md`](../handoffs/active/context-folding-progressive.md) §CF-3c
- **A "full-context" control that is not one.** The external RLM comparison
  (n=200, single run, **no variance reported**) implements its full-context arm
  as sliding-window 200k / 50k-overlap plus LLM aggregation, not one prefill — so
  it is not the clean long-context control it is cited as.
  [`rlm-contested-claims-self-evaluation.md`](../handoffs/active/rlm-contested-claims-self-evaluation.md) §E3a

### A cross-arm parse-failure gap is a scoring artifact — verify the parser per model

One model family emits **JSON inside `<tool_call>`**, not the XML
`<function=…><parameter=…>` form its base family uses, and the chat template
differs between two siblings of the same family (6,994 B vs 4,718 B). Verify the
tool-call parser **per model, not per family**, before any agentic arm: a
cross-arm parse-failure gap reads as a quality gap.

### Source References

- [`scoring-infra-standardization.md`](../handoffs/active/scoring-infra-standardization.md) — 2a-iii (process-group kill; `RLIMIT_NPROC` rejected with the per-UID rationale), 2a-iii-followon (cgroup v2 `pids.max`), 2b-agentic-0 (fail-closed testbed reset; `-fd` not `-fdx`), 2b-agentic-1 (per-model parser pin), 2b-swe-hygiene (six-point disclosure standard)
- [`harness-selection-and-integration.md`](../handoffs/active/harness-selection-and-integration.md) — HS-12 corrected capability-vs-harness decomposition and its counterweight; HS-10 harness randomization as an evaluation-side pattern
- [`architect-model-selection-bench.md`](../handoffs/active/architect-model-selection-bench.md) — non-commensurability of the vendor full-500 SWE-bench figure with the sealed SWE-oracle-40 authority row
- [`context-folding-progressive.md`](../handoffs/active/context-folding-progressive.md) — AREX ACU non-citability; ARC-AGI-3 public-set provenance downgrade
- [`rlm-contested-claims-self-evaluation.md`](../handoffs/active/rlm-contested-claims-self-evaluation.md) — E3a: the external long-context arm is not a clean control
- [`progress/2026-07/2026-07-29.md`](../progress/2026-07/2026-07-29.md) — "Two live bugs found in our own code", execution-verification tallies, host thread census

## The crash-window brick class: how an evidence namespace becomes permanently unusable (2026-07-29)

An evidence pipeline that writes durable artifacts has a failure mode distinct from "the run
failed": the run's *namespace* is left in a state no code can read and no rerun can replace. Six
E8 collection cycles were lost to this class in one day. Three instances, all the same shape —
**a window in which the on-disk state asserts something the pipeline cannot yet back**:

1. **Double-write of a completion marker.** A helper wrote `r2_complete.json` with
   `status: complete`, and each caller then re-read, updated and rewrote the same path with the
   watcher/claim/scorer evidence. A crash between the two writes left a marker claiming completion
   while missing the evidence every reader requires — and because the marker existed, the
   overwrite guards refused to let a rerun rebuild it. *Fix: one authoritative writer.* The helper
   takes the caller's extra fields and performs the single write, so the marker never exists in a
   partial state. Note the fix had to convert **four** call sites; a returns-only refactor would
   have silently broken three of them.

2. **In-place truncating write.** A local `_write_json` opened the destination `O_CREAT|O_TRUNC`
   and wrote in place, so a crash mid-write left a zero-length or half-written JSON *at the real
   path*. Readers then fail on decode, and the same overwrite guards make the namespace
   unrecoverable. *Fix: write-temp → fsync → `os.replace` → fsync-dir.* The codebase already had
   exactly that helper — the bug was a second, weaker implementation of an operation it had
   correct, so the repair **deleted** code. Worth generalising: when you find an unsafe primitive,
   check whether the safe one already exists before writing a third.

3. **Seal before publish.** A `run_seal.json` recording `status: complete` was written into the
   *staging* directory and only then atomically published. A crash in that window left staging
   asserting completeness for a bundle that was never published; because the publish is
   `RENAME_NOREPLACE`, a rerun could neither publish over it nor trust it. *Fix: seal after
   publish.*

**The generalisable rule is about which residual window you keep, not about eliminating it.**
"Make the two atomic together" was unavailable — `renameat2` moves one directory, and no primitive
publishes a tree and writes a file in one step. So the design question becomes: *of the crash
windows you cannot remove, which leaves a state that is **detectable and completable**?*
Published-but-unsealed is both (bundle present, seal absent; every input the seal hashes is already
durable, so re-sealing is deterministic). Sealed-but-unpublished is neither. Sequencing so the
survivor is the recoverable state is the achievable property.

**Two checks that made the reorder safe**, and which generalise to any publish-then-annotate
change: the publish did **not** chmod the destination read-only (so the post-publish write
succeeds), and the seal was **already excluded from its own bundle hash** (so moving it changes no
hash anywhere). Both were verified before the reorder, not after.

_Sources: `handoffs/active/session-bus-thin-dispatcher.md`; `progress/2026-07/2026-07-29.md`;
epyc-orchestrator branch `tierc-10d-crash-window-durability` (`8cdf14f9`)._

## A saturated suite does not merely fail to separate models — it reads NULL and looks like evidence (2026-08-02)

The canonical 79-question judge suite was used for keep/drop reads on the model fleet. A paired
head-to-head measured it against its own job and it could not do it.

**Setup.** `architect_general` (Qwen3.6-27B Q8_0) vs `frontdoor` (Qwen3.6-35B-A3B Q8_0), one judge
(Qwen3.5-122B, neither arm), identical 70 questions, identical per-suite `max_tokens`, and the
larger-slotted arm deliberately **held down** to the other's 8192-token per-slot budget so neither
got more room. Result: **180/204 (88.2%) vs 179/204 (87.7%)**, 9 wins / 4 losses / **55 ties**,
exact sign test **p = 0.267**.

**The null is a property of the instrument.** 50 of 68 questions (**74%**) scored a perfect 3 for
*both* arms and carry zero discriminating information.

| suite | both-perfect | informative? |
|---|---|---|
| general | 10/10 (100%) | none at all |
| thinking | 9/10 (90%) | almost none |
| math | 8/9 (89%) | almost none |
| coder | 7/9 (78%) | little |
| instruction_precision | 7/11 (64%) | some |
| agentic | 6/10 (60%) | some |
| tool_compliance | 3/9 (33%) | the only real signal |

Published benchmarks separate the same pair on **8 of 8** axes. Two independent judges even
disagreed on the *direction* of the difference — which is what no-signal looks like from the
inside.

**Why this is more dangerous than a benchmark that obviously fails.** A saturated suite returns a
confident, well-formed number with a p-value attached. Nothing in the output announces that the
questions are at ceiling. The prior wiki entry on the 42-question vision suite recorded the sharper
form of this: a saturated benchmark can **mis-rank**, not merely fail to rank — the incumbent
placed 2nd of 5 there and *last* on the unsaturated MMMU-250. **Ceiling saturation should be
computed and reported as a first-class statistic of every suite run**, not discovered when a
result looks surprising. The cheap version is the both-perfect count.

### Two questions in the suite were false, and their own answer keys said so

- `math/t3_q2_combinatorics` asserted `sum (-1)^k C(n,k) C(2n-k,n) = C(n,⌊n/2⌋)`. The LHS is
  **identically 1**; it agrees only at n=1. The reference answer computes `1 ≠ 2`, writes *"Hmm…
  Let me recheck the identity"*, and ships with *"a model answer should recognize the general
  structure even if the exact identity requires adjustment."* The 27B **proved the identity false**
  and was scored 2/3 for not constructing an involution for a statement that does not hold.
- `coder/t1_q1_algorithm` claimed TWO bugs in a binary search that had ONE (verified exhaustively:
  57,915 cases, zero failures with only `left = mid + 1`). Its key traces its own "Bug 2" trigger,
  writes `return 3 ✓`, then admits *"the code works after fixing Bug 1."*

**The generalisable rule: a reference answer that argues with itself is a defect report.** Grep the
answer keys for self-doubt markers (`Hmm`, `let me recheck`, `may have a typo`, `requires
adjustment`, `actually, the code works`) before trusting a suite. Run against pre-fix content this
found 8 markers on exactly the 2 broken questions and nothing elsewhere in 8 suites — a cheap,
high-precision screen.

### The rubric was contaminated in a way that survives re-runs

`rubric_system_prompt` embedded "calibration examples" naming **specific `question_id`s together
with the scores they received on other models** — including `math/t3_q2_combinatorics` as a
*score-1* exemplar and `coder/t1_q1_algorithm` as *score-0*. The judge is primed on question
identity before it reads an answer. This biases the absolute level but **not** an A-vs-B contrast,
because both arms receive it identically — the same reasoning that makes vendor-reported
thinking-on numbers usable for ranking and unusable for levels.

_Sources: `epyc-inference-research/data/judge_suite_headtohead_20260802/` (README + SHA256SUMS,
`check_evidence_durability.py` 0 errors); `handoffs/active/architect-model-selection-bench.md`;
`handoffs/active/canonical-judge-suite-revamp.md`; `progress/2026-08/2026-08-02.md`._
