# Fable 5 Architectural Review — window 2 (a prompt, not a task list)

**Status**: READY (pending preflight — see Run configuration).
**What this is**: the entry prompt for a one-shot strategic-architecture review by Claude Fable 5.
A high-level brief, not a step-by-step plan. Your job is architectural insight we cannot produce
ourselves; the implementation is ours.

## Run configuration
- **Vehicle** [OPERATOR: default = full agent]: run as a Claude Code agent in `/workspace` with the
  `gitnexus-*` skills + `gitnexus` CLI, and authority to spawn as many parallel subagents as you
  need. **This brief targets the full-agent path** — it *links* context rather than inlining it, so it
  is not self-contained. A chat-only run is a **degraded** fallback: without repo access you cannot do
  the portfolio audit (§8.4), the resurrection sweep (§3), or read the MI210 hybrid draft, so the
  operator must paste those in; say plainly in your output if you are working chat-only.
- **Model** `claude-fable-5`. **Effort** `xhigh` default; `max` for the focus facet(s) in §4.
- **Thinking** omitted (always-on); if surfaced, `display:"summarized"`. **Never** echo, transcribe,
  or reproduce your internal reasoning as output text.
- **Data retention** 30-day (required, satisfied). Prompt-cache this static entry packet.
- **Freshness gate, not repeated reindexing.** At session start run `gitnexus status` in `/workspace`,
  `/mnt/raid0/llm/epyc-orchestrator`, `/mnt/raid0/llm/epyc-inference-research`, `/mnt/raid0/llm/llama.cpp`.
  Reindex any stale/errored repo with an **explicit absolute path** — e.g.
  `scripts/gitnexus-analyze.sh /mnt/raid0/llm/epyc-orchestrator` — never bare `gitnexus analyze`; a
  heavy reindex should be run with the autopilot paused. **State is volatile (verified 2026-07-02):**
  epyc-root and epyc-inference-research are current; **epyc-orchestrator is stale and a query on it may
  hit a KuzuDB replay error until reindexed**; **`llama.cpp` is not a known repo label** (unregistered;
  on-disk index stale from 2026-06-19, pre-v6/pre-MI210). **If a `gitnexus query` errors, or a repo
  (esp. `--repo llama.cpp`) is not a known label, fall back to raw file reads under the absolute repo
  path** — `/mnt/raid0/llm/llama.cpp` for the fork. Do not block the review on a perfect index.

## 0. Framing & mandate
You are a principal systems / ML-infrastructure architect; we are giving you a one-shot consult.
This is **open-source performance and architecture work on commodity-CPU LLM inference** — model
serving, kernels/runtime, an autonomous optimization controller, request routing. It is engineering
for throughput and quality; not security work, not frontier-model training. Engage every topic on
its merits; if something is genuinely outside what you can work on, say so and move on.
Your mandate is **review and architectural insight only**: do not implement; do not write
step-by-step plans we could write ourselves. **Naming what we are missing — including reframing the
problem itself — is your single highest-value contribution.** Two outputs are **standing deliverables you
produce unprompted, every time**: a full audit and reprioritization of our entire handoff portfolio
against the current system state, and a closing self-critique of your own plan (both detailed in §8).

## 1. The North Star (read first)
> An orchestration infrastructure **agnostic to the specific models** deployed, that **cures itself
> organically**, and **optimally learns to use every tool available — implemented and backlogged —
> to maximize inference task quality AND speed** under a fixed hardware budget.
(This was your own restatement last window. Re-critique it if it is still wrong.)

## 1.5. What changed since our last consult (2026-06-12) — do not re-solve these
- v6+iqk kernel cutover COMPLETE (one kernel; ik_llama deprecated). Determinism work deployed.
- **The MI210 GPU landed (2026-07-02)** — gfx90a in the devcontainer via ROCm 6.2. Vulkan is
  impossible on gfx90a; HIP needs an fp8 guard fix for ROCm<6.3; gemma4-31B+MTP has full HIP op
  coverage but MTP only via llama-server (CLI unwired); GPU-only. The heterogeneous CPU+GPU future
  is now the present.
- **We built your #1 thesis.** The evidence plane (event-sourced per-question ledger + sequential
  e-process verdicts) went **live-authority 2026-07-02** (`AUTOPILOT_SEQ_VERDICT=1`, W6 audit clear,
  `decision_grade_possible=true`). `MEASUREMENT.md` is our instrument constitution; `instrument_eras.yaml`
  exists. Routing-truth W1–W8, running-state attestation, F5, F7 are complete.
- **It largely works** — the acute contamination symptoms you diagnosed are quiet. The open question is
  now narrower and deeper (the *guarantee*, and one calibration that won't certify) — see §2.

## 2. Where we're stuck NOW (our read — refute it)
We implemented the measurement/policy/narrative separation you designed, and much of it is now **built
and live-authority** (2026-07-02): the per-question ledger + sequential e-process verdicts run under
`AUTOPILOT_SEQ_VERDICT=1`, the W6 current-era audit is **clear** (`gaming_alarm=false`), the W7
game-layer hardening shipped, and the dashboard reports `decision_grade_possible=true`. So the acute
symptoms you diagnosed are, for now, quiet. What is **not** settled is the deeper guarantee:
- **W5 `core_v2` calibration is a repeated no-go** (33/40; "do not promote" since 2026-06-15, held —
  no smaller fallback `core_id`, no extra repeat planned). The instrument we built to *be* the product
  will not certify. Is that the instrument correctly rejecting a **mis-specified objective**, or a
  mis-built instrument?
- We built the **mechanism** (a ledger, a verdict rule, a W7 game layer) but we cannot show it delivers
  the **guarantee** — that refuted narratives cannot re-inject and that the optimizer cannot game the
  evidence base *by construction* rather than by after-the-fact alarm. W6 being "clear" today may mean
  *solved* or merely *re-based*.

Note this subsystem is **under active development right now** (autopilot live; W5–W8 being hardened by
us and a parallel agent), so treat 4A as *review the architecture we just built + the one held-open
question* — not debugging. **If you judge it largely solved, say so and reallocate your depth to 4B.**

**Second live frontier — the MI210 just landed (2026-07-02).** We now have a CPU (1.1 TB,
bandwidth-rich) plus one MI210 (gfx90a, ROCm 6.2). Last window this facet got the least depth and you
reversed our hypothesis — "frontdoor residency is the headline; GPU-drafting CPU targets is the
weakest leg." The α(drafter→target) measurement that forks the whole GPU program is **still
unmeasured** — the tokenizer blocker is now understood (aligned drafter = Qwen3.5-0.8B Q8/Q4; a retest
harness `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/n5_frontdoor_drafter_retest.sh` is staged behind a clean-window gate), but
no valid acceptance-rate data exists yet. With the hardware now present, architectural guidance is most
valuable *before* we pour concrete into the GPU path — so this is an active co-lead (§4B), not a
someday item. [OPERATOR: to run a single-facet deep-dive instead, drop §4B; to pivot the window
entirely, replace §2/§4 with 'Self-running lab (F2)' or a fresh full re-map.]

## 3. The toolbox (yours to critique)
Start at `handoffs/active/master-handoff-index.md` (now dispatch-only) → its domain indices. Use
gitnexus first (architecture/deps/flows at ~20–30% the token cost of raw reads); read raw files for
algorithm internals, prompt/template text, and config values. The indices are yours to **critique and
propose a restructure for** (delivered as a findings artifact, not an in-place edit) if they are
mis-framed for the North Star.

**Resurrection sweep (targeted — it cuts across both facets).** Much of our backlog was shelved,
blocked, or deprioritized under the *CPU-only, bandwidth-wall* regime that no longer holds. **Work
index-driven** — the master + domain indices already summarize all outstanding work; do **not** read
the full corpus (~349 handoff files / ~106k lines). Then run a **targeted** sweep of items whose
*reopen criteria* the new state plausibly now meets — the **MI210 (GPU)** and the **live evidence
plane** are the two triggers — pulling from `handoffs/blocked/`, the parked/"shelved" items in
`handoffs/completed/`, and abandoned `epyc-inference-research` tracks only where a criterion matches.
Archetype: Qwen3.5-27B hybrid-SSM spec-dec was **dead on CPU but viable on GPU (Dflash)** — surface
every track like it. Tell us which abandoned items the new hardware/state revives, which stay dead,
and why; a best-effort appendix can list the rest.

## 4. The focus problems (two co-leads)
**4A · Self-optimizer integrity — the guarantee, not the mechanism (largely built; review it).**
The evidence plane is built and live; W6 is clear and the W7 game layer shipped. So this is a *review
of what we built* plus the one open question — not a rescue. Entry points: `gitnexus query --repo
epyc-orchestrator "autopilot sequential verdict ledger pareto strategy memory"`; then
`src/autopilot_core/` (`sequential_verdict.py`, `learning_exclusions`, `pareto_math`),
`scripts/autopilot/` (`safety_gate.py`, `paired_stats.py`), the W5/W6/W7 calibration + audit +
game-layer paths, the strategy/episodic memory stores. Give us: (i) whether the shipped architecture
actually delivers the **provable** guarantee — refuted narratives cannot re-inject, and gaming is
impossible *by construction* rather than alarm-detected (is W7 the right design, or a patch to
re-derive?); and (ii) whether `core_v2`'s W5 no-go is the instrument correctly rejecting a
**mis-specified objective** vs. a mis-built instrument. **If you conclude it is largely solved, say so
plainly and spend the saved depth on 4B.**

**4B · Post-bandwidth-wall heterogeneous CPU+GPU serving (MI210 now present).**
*Our current thinking is already drafted.* Read `/mnt/raid0/llm/epyc-root/tmp/epyc_mi210_hybrid_inference_handoff.md` — a detailed,
measure-first research handoff that frames the MI210's role as three competing architecture families:
**(A)** dense RAM+GPU hybrid (static layer split / GPU-resident islands / grouped streaming / dense-block
streaming); **(B)** sparse MoE expert residency + streaming (hot-expert HBM cache; cold-miss GPU_LOAD vs.
CPU_EXPERT, à la Fiddler / HybriMoE); **(C)** CPU-primary target + MI210 speculative sidecar (small draft
model / EAGLE-3 head / native MTP). **Treat it as a hypothesis to criticize and improve, not a spec to
bless — do not be bound by it.**
Deliver, at the altitude we cannot reach ourselves: **(1) a critique of the framing** — is A/B/C the right
decomposition, or is the discriminating axis something else (prefill/decode disaggregation; KV-offload-
primary when the KV cache, not weights, is the memory pressure; batch-regime; a fourth family you'd add)?
Is "measure-first-then-integrate" the right staging? **(2) an EV-ranked comparison** of the options as
first-class alternatives for *our specific* substrate (EPYC 9655, 1.1 TB, one MI210 gfx90a,
single-user-latency-first, a heterogeneous small-specialist stack) and workloads — **plus your own
proposed architecture(s)** if you see something better than A/B/C. **(3) The reframing** of your
last-window reversal now the hardware is real (dense frontdoor residency vs. GPU-hosted draft/MTP heads
accelerating CPU targets — which, and why). **(4) [hard requirement] the smallest set of decisive
measurements** that discriminate between the families *before* we build any of them — start from
**α(drafter→target)** (still unmeasured; the tokenizer blocker is now understood and a retest harness
`/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/n5_frontdoor_drafter_retest.sh` is staged behind a clean-window gate — say whether
running it as-is is the right decisive experiment, and specify it so it cannot be silently blocked again).
Your output re-prioritizes that handoff down to the few measurements + prototypes actually worth running;
we (or Codex) then execute the measure-first plan.
Grounding entry points: `gitnexus query --repo epyc-inference-research "speculative draft target alpha
acceptance"` (indexed); **read the `llama.cpp` fork raw** for ROCm/HIP/kernel internals — it is not
gitnexus-indexed right now (see Run config); then `src/backends/`, `orchestrator_stack.py`, the
ROCm/HIP build path, and the `gpu-drafter-mi200-investigation.md` / `gpu-acceleration-path.md` handoffs.

## 5. Hardware substrate (confirm live at preflight)
EPYC 9655, 1.1 TB RAM, bandwidth-rich — plus, as of 2026-07-02, a single **AMD Instinct MI210
(gfx90a)** in the devcontainer via ROCm 6.2 bind-mount. Confirmed constraints: Vulkan impossible on
gfx90a (no ICD); HIP build needs an fp8 guard fix for ROCm<6.3; gemma4-31B+MTP has full HIP op
coverage but MTP only via llama-server (CLI unwired); GPU-only. We hold full `llama.cpp` fork control
and plan custom ROCm/HIP kernels to close the ROCm↔CUDA gap. This substrate is what makes §4B live.

## 6. Hypotheses to confirm/refute (with evidence)
1. "We built and shipped your evidence plane (ledger + sequential verdicts live, W6 clear, W7 game
   layer done), so integrity is now largely solved — only W5 `core_v2` certification remains, and that
   is an objective-specification question, not an architecture gap." 2. "The shipped W7 game layer gives
   the guarantee by construction (refuted narratives can't re-inject; gaming is structurally impossible),
   not just by after-the-fact alarm." 3. "`core_v2`'s no-go is the instrument correctly rejecting a
   mis-specified objective, not a failed calibration." 4. "We keep optimizing within framings we haven't
   questioned — which do we drop first?" 5. "Your own reversal still holds now the MI210 is real —
   frontdoor residency is the headline, GPU-drafting CPU targets the weakest leg — and α(drafter→target)
   gates the whole GPU-draft leg and must be measured before any GPU-draft investment."

## 7. How to work
- **Ground every claim** in a gitnexus result or a file you read, and cite it; if unverified, say so.
- **Guardrail (learned from last window): every falsifiable claim or proposed gate must ship with the
  single cheapest decisive experiment that would validate it before we commit — and you must flag
  which of your recommendations rest on an unverified "cheap" assumption.** (Last window an "one flag
  + one log read" step was silently blocked by a tokenizer incompatibility and is still unmeasured.)
- **Measurement discipline** (`MEASUREMENT.md`): treat any number you produce as a hypothesis unless
  you can cite it; where a decision needs a number we don't have, say "measurement required" and name
  the protocol. Do not invent decision-gating numbers.
- Ample context — do not wrap up early. **Parallelize aggressively** with subagents, but speed must
  never cost quality: every subagent finding is evidence-grounded and independently verified, and you
  adversarially synthesize, never concatenate. Proceed autonomously on reversible analysis.
- **Write authority (strict): subagents are read-only.** Only you (the lead) write, and only
  `handoffs/active/fable5-window2-findings-*` files plus one progress note under `progress/2026-07/`.
  Do **not** edit live indices or other handoffs — the index restructure (§8.4) is a *proposed* rewrite
  you deliver as a findings artifact, not an in-place edit. CLAUDE.md forbids index modifications
  without explicit operator approval.

## 8. Output contract (what to leave us)
1. **A scannable index first** — one line per recommendation (title · category · priority · the one
   fact that justifies it). Skimmable; save the density for the sections below.
2. **The architecture, per problem** — the unifying model (its "name and theorem"), the failure modes
   it resolves, the recommended design, explicit adopt-vs-hold decision gates, and the reframings
   where our problem statement was wrong.
3. **Build seeds for the 2–3 items we will build ourselves** (not full build plans): acceptance
   criteria + the single cheapest decisive experiment that proves the direction before we invest.
4. **[Standing deliverable — produce this unprompted, but index-driven] A portfolio audit + a
   reprioritized outstanding-work queue.** Work from the master + domain indices (they already summarize
   all outstanding work) — **do not read all ~349 handoff files / ~106k lines**; sample a file only to
   confirm a line. Deliver: **(i)** a triage of the indexed items — keep / revive / reorder / merge /
   kill, each with the one fact that decides it (folding in the §3 targeted resurrection sweep: which
   shelved/blocked/abandoned tracks the new state REVIVES, which the recommended architectures make
   load-bearing or obsolete); and **(ii)** a single **reprioritized master queue** rebuilt to our index
   standard — prioritized checkboxed list, dependency graph, cross-cutting concerns, key file locations,
   delete-on-complete (see CLAUDE.md's handoff-index requirements) — with each index's strategic purpose
   re-articulated, delivered as a *proposed* rewrite artifact (not an in-place edit). A best-effort
   appendix may flag anything outside the indices worth a look. *Last window this reprioritization only
   happened because the operator asked mid-session; this window it is non-skippable — but index-driven,
   not a 349-file read.*
5. **Negative-space audit**: what to delete/merge/freeze/stop-optimizing; the most dangerous silent
   assumptions; the invariant interfaces/contracts the North Star requires; the smallest decisive
   observations that would distinguish your architecture from alternatives; which bets compound
   (make now) vs. remain optional (reversible).
6. **Self-critique pass (close with this)**: what in this plan is weakest / most likely wrong / rests
   on the thinnest evidence; what would most change your recommendation; what you could not verify in
   this window.
And throughout: **if the most valuable thing you can say is that the North Star or our §2 framing is
wrong — say that first.**
