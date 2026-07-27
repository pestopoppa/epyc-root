# RLM Contested Claims — Self-Evaluation

**Status**: active — E0 landed 2026-07-27 and **materially changed what E1 should measure**
(see *E0 results*). E1/E3 remain inference-gated; E2 rescoped to `repl-session-memory-maturity.md`
D-c1 on real traffic.
**Created**: 2026-07-27 (via research intake, operator-approved 2026-07-27)
**Priority**: MEDIUM
**Categories**: agent_architecture, context_management, benchmark_methodology
**Parent index**: [research-evaluation-index.md](research-evaluation-index.md)
**Related**:
- [rao-redel-substrate-spike.md](rao-redel-substrate-spike.md) — holds the depth caveat as a
  load-bearing constraint (§ "Wang reproduction caveat"). **Cross-reference only** — that handoff is
  under a 2026-07-14 FUND-OR-CLOSE audit note; do not append tasks to it. E4 writes to it only once
  first-party evidence exists.
- [master-handoff-index.md](master-handoff-index.md) § N17 — the conditional-depth surface this
  handoff supplies evidence for.
- [repl-turn-efficiency.md](repl-turn-efficiency.md)
- [repl-session-memory-maturity.md](repl-session-memory-maturity.md) — E2 rescoped there as D-c1
  (real-traffic measurement, not a synthetic arm here).

## Objective

Replace received evidence with first-party measurement on three RLM claims that keep resurfacing in
this repo, and settle two that nobody owns at all.

> Every EPYC record of the RLM depth caveat traces to one external reproduction (intake-547,
> arXiv:2603.02615) that we have never run. `max_depth=1` is already our load-bearing default and N17
> already frames the likely resolution — depth rescues failing attempts and hurts competent ones. This
> handoff exists to replace received evidence with our own, and to settle two claims nobody owns at
> all: whether carrying prior REPL code into a resumed prompt is cheaper, and what an RLM actually
> buys over just sending the long context.

## Research Context

| Intake ID | Title | Relevance | Verdict | Verification |
|-----------|-------|-----------|---------|--------------|
| intake-547 | Think, But Don't Overthink: Reproducing Recursive Language Models (arXiv:2603.02615) | high | worth_investigating | (pre-lifecycle entry — no `verification` field; treat its numbers as unverified) |
| intake-901 | fast-rlm REPL memory / resumable sessions (re-review 2026-07-27) | high | adopt_patterns | dive-verified |
| intake-153 | Recursive Language Models (arXiv:2512.24601) | high | already_integrated | (pre-lifecycle entry) |

## What is already settled — do not re-derive

- `max_depth=1` is **already** the load-bearing default for any RAO/RLM-style integration on EPYC.
  This handoff does not propose changing it; it measures whether the reason we hold it is true here.
- The likely resolution is **already framed** in master-index N17: depth rescues *failing* attempts
  and hurts *competent* ones, so depth should be gated on predicted failure rather than pinned. This
  handoff supplies the evidence that surface needs; it does not re-invent the framing.
  **⚠ Qualified by E0**: N17's "rescues failing attempts" premise rests on the `0.0 → 42.1` figure,
  which E0 found to be substantially a **format-compliance artifact** (the base model solved the task
  but failed a strict-format scorer, and no rescoring was done). The idea stands; its headline
  evidence does not.
- fast-rlm's own harness has **no baseline arm**: `benchmarks/_harness.py:4` states verbatim
  *"No budget sweeps, no non-RLM baseline yet"*. Neither it nor intake-547 answers "versus just
  sending the context". E3 exists because of this.

## Tasks

- [x] E0 — Primaries read directly, with an independent adversarial re-read of every verdict ✅
      2026-07-27. **Result: this changes what E1 should measure.** Findings in *E0 results* below.
- [ ] E1 — **RESCOPED BY E0**: measure **Base vs Depth-1 first**, not depth-1 vs depth-2. E0 showed
      the cost is a *step function at the Base→RLM boundary* (24.8× then 3.86× for DeepSeek S-NIAH),
      so the large, decision-relevant effect is the first step — and it is the comparison neither
      source reads cleanly. Start with synthetic NIAH (fast-rlm `benchmarks/niah_benchmark.py` is
      self-contained, no dataset download). **Record latency and tokens SEPARATELY** — E0 showed they
      move in opposite directions with depth, so a combined cost metric would hide the finding.
      Pre-declare n, reps and the kill criterion before running; n=20 single-run cannot resolve these
      effect sizes.
  - [ ] E1a — Use a **format-robust scorer**, or score twice (strict + lenient) and report both. The
        single most-cited number in this literature is a formatting artifact; do not reproduce that
        mistake.
- [ ] E2 — **RESCOPED 2026-07-27 (operator): do not replicate this synthetically.** The original plan
      was a ≥3-rep ON/OFF arm against the source's n=1 table. The source's own caveat — the code dump
      stays cheap only when follow-ups add a line or two, and *"a session where every query does heavy
      multi-step work is the case to watch"* — says the synthetic regime is not ours, so replicating
      it would answer a question we do not have. Measurement moved to
      `repl-session-memory-maturity.md` **D-c1**, riding real T3 hard-workflow/tool-use/REPL traffic
      at zero added inference. Keep this line only as the pointer; **no arm runs here.**
- [ ] E3 — Add the **non-RLM long-context baseline arm** that neither source has. Without it, no
      depth number can say whether recursion beats simply sending the context.
- [ ] E4 — Write the resolution into `rao-redel-substrate-spike.md` § caveat and master-index N17 as
      first-party evidence — or explicitly record that ours agrees with the external reproduction.

## E0 results (2026-07-27) — primaries read, verdicts adversarially re-verified

Both papers were read directly (arXiv:2603.02615 via PDF + figure-image extraction, since the
numeric results live in figures, not text tables) and every verdict was independently re-checked by
a second reader instructed to refute. Where the two disagreed, the disagreement is recorded.

### The repo's own record of arXiv:2603.02615 is wrong in two places

| Our record | Primary source | Verdict |
|---|---|---|
| "3.6s @ **depth-1** → 344.5s @ depth-2 (~96×)" | §4.3: *"DeepSeek v3.2 solves the base S-NIAH task in just 3.6 seconds. Activating RLM (Depth=1) inflates this to 89.3 seconds, and pushing to Depth=2 skyrockets … to an impractical 344.5 seconds."* Figure 2 bar is labelled **"Base LLM"**. | **OVERTURNED (arm mislabel).** 3.6s is the BASE arm. 96× spans Base→D2. The true **D1→D2 factor is 3.86×** — our two-point record overstates the depth-2 *marginal* cost by ~25×. |
| "Token-cost inflation is **exponential** in depth" | §4.3: *"while the execution time strictly increases with depth, the token usage sometimes stabilizes or even slightly drops from Depth=1 to Depth=2."* Tokens **fall** D1→D2 in 3 of 4 cells. | **OVERTURNED.** Depth-2 is a **latency** pathology (runs crash on format collapse or stall in serial sub-call loops, burning wall-clock without tokens), not a token-cost one. |

**The structural finding we had missed: cost is a step function at the Base→RLM boundary, not a
function of depth.** Latency multipliers Base→D1 then D1→D2: DeepSeek S-NIAH 24.8× then 3.86×; Kimi
S-NIAH 10.3× then 1.54×; DeepSeek OOLONG 5.4× then 1.90×; Kimi OOLONG 2.69× then 1.33×. In all four
cells the first step dominates and the multiplier **decelerates** — the opposite of exponential.

### The rescue number that N17 leans on is substantially a scorer artifact

`0.0 → 42.1` (DeepSeek OOLONG) is real and correctly recorded — but Appendix A.3 states the base
model *"had successfully found the answers but produced long narrative explanations instead of the
expected strict formats"*, and confirms **no rescoring was done**. The base model could do the task;
it failed the format check. This is our own `feedback_parse_failure_rate_is_a_scoring_artifact.md`
pattern. The caveat appears nowhere in the abstract or in §4.2 where the result is presented.
A.3 is also internally incoherent — it attributes the 0% to *"formatting failures under recursive
abstraction"* when the run in question is the **Base LLM** arm, which involves no recursion.

**Consequence for master-index N17:** the conditional-depth surface is partly premised on
"recursion rescues failing attempts". That premise now rests on a format-compliance artifact, not a
demonstrated reasoning gain. It does not falsify the conditional-depth idea, but it removes its
headline evidence — worth knowing before funding the experiment.

### The paper overclaims against its own figure

§4.2 asserts depth-2 *"uniformly degraded performance across all conditions"*. Its own Figure 1 shows
**Kimi K2 on S-NIAH flat at 90.0 → 90.0** from depth-1 to depth-2. One of four model×benchmark cells
shows no depth-2 degradation at all.

### Evidence grade: single-run, n=20, no repeats

`n = 20` per condition, one run, zero repeats, no variance, no error bars, no significance testing
(§4.5, the paper's only limitations subsection). S-NIAH accuracy is therefore quantized in 5pp steps:
the headline DeepSeek "plummet" 85.0 → 70.0 is a **three-question flip**, and Kimi's 100 → 90 a
two-question flip. Binomial SE at n=20 is ~10pp. This is exactly
`feedback_per_suite_gate_resolution_artifact.md`.

**Four threats the paper does not state:** (1) OOLONG contexts were capped at 1,024–65,536 tokens, so
RLM is tested in a regime where it is not needed; (2) Kimi K2's RLM arms only produce scores because
the author hand-patched the harness — without a bespoke `strip_think_tags()` fix *"all RLM (depth 1
and 2) samples failed with parsing errors"*; (3) scoring is strict-format exact-match, so an unknown
share of "reasoning failures" are format failures; (4) latency was measured on a consumer macOS
laptop over blocking sequential third-party API calls, so wall-clock is dominated by network and
queueing.

### What this changes for E1

- Measure **Base vs D1** first. That is where the cost step actually is, and it is the comparison
  both this paper and fast-rlm's harness lack a clean read on. D1 vs D2 is the smaller effect.
- Record **latency and tokens separately** — they move in opposite directions with depth, and a
  combined "cost" metric would hide the real finding.
- Use a **format-robust scorer**, or score twice (strict + lenient) and report both. The single most
  cited number in this literature is a formatting artifact; we should not reproduce that mistake.
- Pre-declare n and reps. n=20 single-run cannot resolve the effect sizes being claimed.

### arXiv:2512.24601 (canonical RLM)

Verification of the depth-default claim and of the figures our index records under intake-153 is in
the workflow transcript; the operative point for this handoff is that the depth caveat originates
with the reproduction, not the canonical paper. Recorded so E1 does not re-derive it.

**Grade every number above as observation-only under MEASUREMENT.md** — single-run n=20, no protocol
id, no attestation. None of it is decision-gating.

## Gates

- **Inference-gated on a clean CPU window.** The CPU lane belongs to the AutoPilot E8 baseline
  reseed, which gates all model-stack changes. Per-run operator approval is required — no `llama-*`
  on EPYC otherwise.
- **E1/E2/E3 are decision-gating**, so they run under a codified recipe with a protocol-id
  (`bench_canonical.sh` / `canonical_recipe.py`), or their numbers are observations only and cannot
  gate anything.
- **Deterministic replay before regeneration** (CLAUDE.md, operator-ratified 2026-07-27) applies to
  E2 re-scores: rescore saved outputs rather than re-running inference; rebaseline only the axis that
  changed.
- **Do NOT adopt fast-rlm's optional LLM judge.** Scoring is a human-amendment-only trust boundary
  (MEASUREMENT.md). Its deterministic scorers — `exact_match`, `numeric_match`, SQuAD-style token-F1
  — do not cross that boundary and may be reused.
- **Escalation to LongBench/NarrativeQA and OOLONG-synth only if NIAH shows the effect is real.**

## Open Questions

- Is the depth effect direction-of-effect model-dependent on *our* model lineup, as intake-547
  reports across DeepSeek v3.2 vs Kimi K2?
- Does the code-log-in-prompt saving hold when the workload is not a synthetic corpus built by the
  same person measuring it?
- On CPU inference at ~10-40 t/s, does any depth-2 arm survive its own wall-clock cost regardless of
  accuracy?

## Notes

Provenance: 2026-07-27 research intake of intake-901 (fast-rlm), Stage-2 dives D1/D2/D3 against
primary source at pinned SHA `f25f310b`. Two Stage-1 conclusions were overturned by those dives and
must not be re-derived from the Stage-1 report — see intake-901 `dive_corrections`. In particular the
fast-rlm session-cost figure **does** carry a stated protocol and a full per-query token table
(`docs/guide/sessions.md:64-79`); its weakness is n=1 per arm, no variance, no seed, synthetic corpus,
maintainer-measured — not the absence of a protocol.
