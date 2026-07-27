# RLM Contested Claims — Self-Evaluation

**Status**: stub
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
- [repl-session-memory-maturity.md](repl-session-memory-maturity.md) — E2 is the acceptance test for
  its D-c.

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
- fast-rlm's own harness has **no baseline arm**: `benchmarks/_harness.py:4` states verbatim
  *"No budget sweeps, no non-RLM baseline yet"*. Neither it nor intake-547 answers "versus just
  sending the context". E3 exists because of this.

## Tasks

- [ ] E0 — Read the two primaries directly (arXiv:2603.02615 § depth results, arXiv:2512.24601 §
      depth default). Record whether the wall-clock ladder (3.6s → 89.3s → 344.5s) and the Kimi-K2
      OOLONG reversal (depth-0 86.6% vs depth-1 60.0%) are stated as measured or inferred, and on
      what n. Zero inference. **Do this before any run** — it may change what E1 needs to measure.
- [ ] E1 — Depth-1 vs depth-2 sweep on **our** stack. Start with synthetic NIAH
      (fast-rlm `benchmarks/niah_benchmark.py` is fully self-contained — no dataset download, runs
      against local models). Record accuracy and wall-clock per arm. **Pre-declare the kill criterion
      before running.**
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
