# Fable 5 Architectural Review — entry handoff (a prompt, not a task list)

**Status**: READY (pending pre-run gitnexus refresh — see Run configuration).
**Created**: 2026-06-12.
**What this is**: the entry prompt for a one-shot strategic-architecture review by Claude
Fable 5. It is deliberately a *high-level brief*, not a step-by-step plan. Fable 5's job is to
give us architectural insight we cannot produce ourselves; the implementation is ours.

---

## Run configuration (for whoever launches the session)

- **Model**: `claude-fable-5`. Run as a Claude Code agent **in `/workspace`** with the
  `gitnexus-*` skills and the `gitnexus` CLI available.
- **Effort**: `xhigh` by default; use `max` for the self-optimizer-integrity and serving-topology
  facets, where depth matters most. (We only spend Fable 5 on reasoning we cannot reproduce — so
  do not dial effort down.)
- **Thinking**: omit the `thinking` parameter (always-on for this model); if you surface
  reasoning anywhere, use `display: "summarized"`. **Do not** ask the agent to echo, transcribe,
  or reproduce its internal reasoning as output text.
- **Data retention**: 30-day retention is required for this model and is satisfied here.
- **Parallelism**: the agent is authorized to spawn as many subagents as it needs (see
  §How to work).
- **Freshness gate, not repeated reindexing.** Indices were refreshed at authoring (2026-06-12):
  `epyc-orchestrator` and `epyc-inference-research` are current; an `epyc-llama` (llama.cpp fork)
  index is current too, queryable as `--repo llama.cpp`. At **session start**, run `gitnexus status` in `/workspace`,
  `/mnt/raid0/llm/epyc-orchestrator`, `/mnt/raid0/llm/epyc-inference-research`, and
  `/mnt/raid0/llm/llama.cpp`. Re-run `scripts/gitnexus-analyze.sh <repo-path>` **only** for repos
  reported stale, or if `git rev-parse HEAD` changes during the session. Do **not** re-analyze
  before every facet — this is analysis-only, and repeated indexing wastes the Fable 5 window and
  adds host load. If `llama.cpp` is not available as a queryable GitNexus repo label after this
  check, treat it as **raw-file-only evidence** and say so in your findings. Never run bare
  `gitnexus analyze` (always use the wrapper `scripts/gitnexus-analyze.sh`).

---

## 0. Framing & mandate

You are a principal systems / ML-infrastructure architect. We are giving you a one-shot consult.

This is **open-source performance and architecture work on commodity-CPU LLM inference** — model
serving, kernel and runtime performance, an autonomous optimization controller, and request
routing. It is engineering for throughput and quality. It is not security research, not
exploit/defense work, and not frontier-model training. Engage every topic on its technical
merits; if anything genuinely sits outside what you can work on, say so plainly and move on
rather than declining the whole engagement.

Your mandate is **review and architectural insight only**:
- **Do not implement anything.** No code, no patches.
- **Do not write step-by-step action plans we could write ourselves.** We can grind. What we
  cannot do is see the architecture from above. Spend your effort there.
- The four problems in §4 are **where we think the hard architecture is. They are starting
  points, not a fence.** We may have assumed blockers are immovable that you can see resolutions
  for; we may be conceptually stuck in ways we cannot perceive. **Naming what we are missing —
  including reframing the problem itself — is your single highest-value contribution.**

---

## 1. The North Star (read this first; everything else serves it)

> An orchestration infrastructure that is **agnostic to the specific models** deployed in its
> stack, can **cure itself organically**, and **optimally learns to use every tool available —
> implemented *and* backlogged — to maximize inference task quality AND speed.**

Unpack what each clause means here:

- **Model-agnostic**: the value is in the orchestration, not any one model. We are not afraid to
  deploy **many small specialized models** (heterogeneity is a feature). Models should be
  swappable; the system's intelligence is in how it routes, escalates, composes, and accelerates
  them — not in a single hero model.
- **Self-healing / cures itself organically**: the system should detect its own regressions and
  contamination and recover, without an operator hand-fixing each incident. Today recovery is
  manual and tactical.
- **Optimally learns to use every tool — including the backlog**: this is the subtle one. Our
  handoff indices (§3) are not just a TODO list; they are a **catalogue of capabilities the
  orchestration should learn to wield**. A capability sitting in the backlog that the system never
  learns to deploy is wasted leverage. Treat "the backlog is part of the toolbox" as a design
  premise worth examining.
- **Maximize quality AND speed**: both objectives, jointly, under a fixed hardware budget.

The four facets in §4 are projections of this intent: self-cure without self-contamination
(integrity + the optimizer↔evaluator game); model-agnostic optimal tool-use (the routing/serving
decision architecture); and the speed ceiling (post-bandwidth-wall serving).

---

## 2. How we approached it, and where we suspect we are stuck

This is our own high-level account. Treat it as a hypothesis about ourselves — **we are
explicitly inviting you to refute the framing.**

**The stack, in two tiers.**
- An **orchestrator** (`epyc-orchestrator`) fronts a heterogeneous set of CPU-hosted models via
  *software* routing: a frontdoor model, role-specialized models (coder, architect, worker,
  vision, long-context), escalation paths, and a learned routing controller. Models run as
  NUMA-pinned `llama.cpp` instances on a single-socket EPYC 9655 (NPS4; quarter-machine 4×48t
  splits are the throughput sweet spot); routing is a software role→port map.
- An **autopilot** (`scripts/autopilot/`, `src/autopilot_core/`) is a recursive self-optimizer: an
  LLM *planner* proposes experiments across "species" (seed batches, numeric sweeps, prompt
  mutations, structural-flag flips), runs them through a tiered eval tower (T0 quick / T1 medium /
  T2 deep), keeps or reverts, and distills a **strategy memory** it retrieves on future trials to
  condition the next proposal. It optimizes a multi-objective Pareto archive (quality × speed × …).

**What we have done toward the intent.**
- *Acceleration*: measured many CPU levers. The wins that survived rigorous re-measurement are
  **NUMA multi-instance (~6.7× aggregate)**, **`draft_max` tuning (+15–20%)**, and a **KV-compression
  stack** (quantization × compaction × selection × masking). Most speculative-decoding variants
  went net-negative on Q4_K_M. We concluded single-instance CPU decode is **memory-bandwidth-bound
  and largely exhausted** (IPC 0.17–0.28 universal; `compute_kernel_memory_stalled` across four
  architecture classes).
- *Routing*: evolved role-based selection → a learned controller (~92% val acc) → decision-aware
  routing → a tri-role "Trinity" coordinator → a within-role placement state machine → an outer
  coordinator. Several sub-controllers, each with a different optimization paradigm (Q-tables,
  bilinear scorer, CMA-ES).
- *Self-optimization*: the autopilot has run for hundreds of trials, maintaining a Pareto frontier.

**Where we suspect we are conceptually stuck (our suspicions — challenge them):**
1. The autopilot's recurring failure is **not** the halting bug we keep patching. It is that the
   optimizer learns from evidence *it itself generates*, and that evidence keeps getting
   contaminated — distilled "strategy" narratives re-inject after we scrub them; a noise-exclusion
   policy (MAD) over-excludes reproduced wins; a test fixture once gate-locked the production
   baseline; a tier-scale mismatch poisoned the journal. Every fix has been **tactical**. We
   suspect there is no principled architecture separating *measurement* (facts) from *policy*
   (decisions) from *narrative* (hypotheses), and that "add another guardrail" may be the wrong
   move entirely.
2. Routing has **accreted**. We suspect it has lost a unifying decision principle — but we cannot
   see the simpler design from inside it.
3. We have **assumed the CPU bandwidth wall is a hard ceiling** and optimized within a fixed
   serving architecture (single-user, decode-latency-first, single context per process). The
   incoming GPU (see §5) may make that assumption obsolete, and the assumption itself may be the
   trap.
4. We treat the backlog as a **feature queue** rather than a toolbox the orchestration should
   learn to deploy. That may be an architectural blind spot.

---

## 3. The toolbox (and your license to restructure it)

The full catalogue of implemented + backlogged capabilities lives in the handoff indices. Start
at `handoffs/active/master-handoff-index.md`, which dispatches to five domain indices:
`routing-and-optimization-index.md`, `inference-acceleration-index.md`,
`cpu-inference-optimization-index.md`, `research-evaluation-index.md`, `hermes-agent-index.md`.

**Use gitnexus first** to understand architecture, dependencies, and execution flows — it is far
cheaper than reading raw source and is freshly relevant:
- `gitnexus query --repo <epyc-orchestrator|epyc-inference-research> "<concept>"` → execution flows
  + definitions.
- `gitnexus context <symbol>` → callers/callees for a symbol.
- `gitnexus impact <symbol> --direction upstream` → blast radius (also a risk read).
- `gitnexus cypher "<query>"` → direct graph queries.
Read **raw files only** for what the graph cannot carry: algorithm internals inside a function,
prompt/template text, and config/hyperparameter values. (Reminder: confirm `epyc-llama`
queryability via the freshness gate in Run configuration; if it is not a queryable GitNexus repo
label, treat the `llama.cpp` fork as raw-file-only evidence and say so. As of authoring it IS indexed and queryable as `--repo llama.cpp`.)

**These indices are also yours to critique and restructure.** If you find the *map* of the work is
mis-framed for the North Star — wrong groupings, stale strategic purpose, missing structure, work
that no longer earns its place — say so, and propose the better organization (see §8).

---

## 4. The four candidate 10x problems (starting points, not a boundary)

**1 — Self-optimizer integrity architecture.** The autopilot learns from evidence it generates,
and that evidence keeps contaminating its own decisions; our fixes are tactical. *What architecture
makes a recursive self-optimizer's evidence base provably uncontaminable* — provenance,
falsifiability, and a principled separation of measurement / policy / narrative, with memory
structured so refuted narratives cannot re-inject?
- Entry: `gitnexus query --repo epyc-orchestrator "autopilot planner pareto strategy memory"`
  (e.g. `proc_157_pareto`, `Plan_with_providers`); then `src/autopilot_core/` (`pareto_math`,
  `learning_exclusions`), `scripts/autopilot/`, the strategy/episodic memory stores.
- Docs: `autopilot-continuous-optimization.md`, `retrain-routing-models.md`.

**2 — The optimizer↔evaluator interaction as a game.** The planner repeatedly finds loopholes in
the eval tower (gaming the T0 fast-reject gate, reproducing within-noise points, binary
keep/revert, anchoring on stale memory). *Redesign the planner–evaluator interaction so that
maximizing the planner's payoffs provably converges on the true Pareto frontier* — exploration
bonuses, posterior uncertainty, regret bounds. (Tightly coupled to #1; may be one combined target.)
- Entry: `eval_tower`, `learning_exclusions`, the seeder species.
- Docs: `eval-tower-verification.md`, `meta-harness-optimization.md`, `autopilot-continuous-optimization.md`.

**3 — A unifying routing/serving decision architecture.** Routing has accreted into a multi-level
hierarchy (role → model → within-role placement → migration) mixing Q-tables, a bilinear scorer,
and CMA-ES, with opaque composition semantics. *Is there one decision-theoretic model
(hierarchical MDP? bounded-regret cascade? something else) that unifies it* — and would a frontier
architect see a fundamentally simpler design for a single-user, heterogeneous-model, CPU-bound,
self-optimizing serving system?
- Entry: `gitnexus query --repo epyc-orchestrator "routing role model placement decision"` (e.g.
  `Generate_stream → Hybrid_router_kwargs`); then `routing.py`, `retriever.py`,
  `src/scheduling/placement.py`, `src/classifiers/`.
- Docs: `routing-and-optimization-index.md`, `learned-routing-controller.md`,
  `decision-aware-routing.md`, `tri-role-coordinator-architecture.md`,
  `within-role-placement-state-machine.md`, `outer-coordinator-learned-head.md`,
  `dynamic-stack-concurrency.md`.

**4 — Post-bandwidth-wall serving architecture.** Single-instance CPU decode is measured-to-
exhaustion and bandwidth-bound; no kernel tweak yields another 2×. The next leap comes from
changing *what* we compute (serving topology, prefill/decode disaggregation, batching,
workload-matched serving, KV amortization) and from the **heterogeneous CPU+GPU** future (§5). *What
serving architecture unlocks the next 10× given EPYC / 1.1 TB RAM / CPU-now-plus-one-GPU-soon?*
- Entry: `epyc-inference-research` spec/draft flows (e.g. `_load_dflash_module`); then
  `src/backends/`, `orchestrator_stack.py`, and the now-indexed fork via
  `gitnexus query --repo llama.cpp "<concept>"` (58.7K symbols; raw reads only for kernel internals).
- Docs: `inference-acceleration-index.md`, `cpu-inference-optimization-index.md`,
  `numa-prefill-decode-disaggregation.md`, `moe-spec-cpu-spec-dec-integration.md`,
  `llama-cpp-dsa-contribution.md`, plus the GPU cluster in §5.

---

## 5. The hardware trajectory and the MI210 hypothesis (running, not settled)

Today the substrate is **CPU+RAM only** (EPYC 9655, 1.1 TB, bandwidth-rich). **Near-future we gain
a single AMD Instinct MI210 GPU**, free to use however is best — this turns facet #4 into a
*heterogeneous CPU+GPU* topology question, not a CPU-only one.

**Our current hypothesis (please critique it; it is not set in stone):** use the MI210 to host
(a) a **dense frontdoor model** that exploits the GPU's high memory bandwidth, and (b) **fast
speculative / MTP decoding heads** running at blazing speed on-GPU to accelerate the *CPU+RAM-hosted
target models'* throughput via speculative decoding. We want your read on whether this
CPU-target + GPU-draft/frontdoor split is the right architecture or a local optimum — and on the
larger CPU↔GPU work-partitioning question.

A practical constraint we own: we have **full control of the `llama.cpp` fork**, and we plan to
build **custom LLM-tuned ROCm kernels to overcome the ROCm↔CUDA capability gap** (much GPU-inference
tooling is CUDA-first). Relevant backlog:
- `gpu-acceleration-path.md` (GPU hybrid serving research; AMD path is the live one),
- `gpu-drafter-mi200-investigation.md` (GPU-hosted drafter — directly this hypothesis),
- `gemma4-mtp-drafter-evaluation.md` (MTP drafter evaluation),
- `agentic-rocm-kernel-authoring.md` + `rocm-verify-profile-backend.md` (the custom-ROCm-kernel /
  ROCm↔CUDA-gap program, MI210/gfx90a-targeted).

---

## 6. Running hypotheses & doubts (confirm or refute, with evidence)

For each, tell us whether you agree, and on what evidence (a gitnexus query result or a file you
read). Refutations are as valuable as confirmations.

1. "Single-instance CPU decode is bandwidth-bound and effectively exhausted; the next gains are
   architectural, not kernel-level."
2. "The autopilot's contamination is structural (an evidence-base/memory architecture problem),
   not a sequence of bugs."
3. "Routing has lost a unifying principle and would be simpler under one decision model."
4. "The MI210 should host a dense frontdoor + on-GPU draft/MTP heads accelerating CPU targets."
5. "The backlog should be modeled as a toolbox the orchestration learns to deploy, not a feature
   queue."
6. "We are stuck because we keep optimizing *within* framings we have not questioned." — if true,
   which framing should we drop first?

---

## 7. How to work

- **Ground every claim** in a gitnexus query result or a file you actually read, and cite it. If
  something is not yet verified, say so.
- You have **ample context** — do not wrap up early, summarize prematurely, or worry about a
  budget. Work the problem to depth.
- **Parallelize aggressively.** Spawn as many subagents as you need (e.g. one per facet, or per
  exploration thread) to finish fast; asynchronous delegation that keeps subagents reporting back
  is a strength here. **Hard constraint: speed must never cost quality** — every subagent finding
  must be evidence-grounded and independently verified, and you (the orchestrator) adversarially
  check and synthesize, never merely concatenate.
- Persist findings to `handoffs/active/` as you go (don't hold everything in one context), and
  feel free to leave a progress note under `progress/2026-06/`.
- Proceed autonomously on reversible analysis; do not pause to ask permission for reading,
  querying, or drafting findings.

---

## 8. Output contract (what to leave us)

Write your output to `handoffs/active/fable5-findings-*.md` (one file per facet, or a coherent
set). Everything here is **architectural insight we will multiply into implementation workflows —
not for you to execute.** Deliver:

1. **The architecture, per problem** — the unifying model (its "name and theorem"), the failure
   modes it resolves, the recommended design, and the explicit decision criteria/gates that tell
   us when to adopt vs. hold. Include the reframings where our problem statement was wrong.
2. **A backlog-relevance map** — for the existing index items, which the recommended architecture
   makes load-bearing, which it reorders, and which it makes obsolete.
3. **A handoff/index review & reorganization** — review our handoffs and handoff-indices directly
   and propose refinements: new deep-dive topics worth opening, re-prioritization, and a
   **re-articulation of each index's/handoff's strategic purpose** so the set serves the North
   Star. Express this as a concrete proposed index rewrite, not a detailed task list.

And, throughout: **tell us what we are missing.** If the most valuable thing you can say is that
the North Star itself, or one of our four framings, is wrong — say that first.

---

## 8.5 Negative-space audit

In addition to proposing architectures, explicitly tell us:
- What should we **delete, merge, freeze, or stop optimizing** — subsystems, handoffs, or
  assumptions that consume attention without moving the North Star?
- Which **assumptions are most dangerous** because they silently shape every downstream decision?
- What **invariant interfaces/contracts** must exist for the North Star to be real rather than
  aspirational (e.g. model-capability descriptors, routing-evidence schema, eval provenance, the
  experiment ledger, serving telemetry, a hardware-abstraction boundary — surface the ones that
  actually matter)?
- What are the **smallest decisive observations** that would distinguish your recommended
  architecture from plausible alternatives (so we can later convert insight into gates)?
- Which **bets compound** if made now, and which should remain **optional until stronger evidence**
  exists (irreversible vs. reversible)?
