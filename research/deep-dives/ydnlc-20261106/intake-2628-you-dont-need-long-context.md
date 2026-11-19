# intake-2628 — You don't need long context (NVIDIA, arXiv 2611.05306v1)

**Dive date**: 2026-11-06 · **Read depth**: FULL (body + Appendices A–G) · **Source revision**: 2611.05306v1 (2026-11-03)
**Verdict**: dive-verified with two narrowed claims.

## What the paper actually shows

Three research questions, each answered affirmatively with frontier closed-weight models:

1. **Long-horizon tasks** — end-of-conversation compaction (EoCC) at budgets from 48K/36K down to 8K/6K keeps
   accuracy within −3.7 to +5.6 ppts (Opus 4.5) and −3.3 to +4.4 ppts (GPT 5.6 Sol) across six benchmarks; at
   most 5 of 22 configurations per model lose more than 2 ppts.
2. **Long-input tasks** — storing documents as files and reading them selectively (grep/sed/head, bounded
   `doc-read`) matches or beats full-input baselines on six of seven benchmarks, and is −0.4 ppts on the
   seventh (LongBench v2, Opus). NIAH reaches 100% for both models with zero compactions; RULER rises from
   62.5→95.7 (Opus) and 65.5→96.4 (GPT); BABILong +24.9/+23.3.
3. **Single-action compaction** (SAC) — one environment action per context with only a natural-language semantic
   state preserves SWE-bench Verified for Opus (70.0→70.2) and improves Terminal-Bench (47.2→51.8); GPT loses
   2.0/3.3 ppts. Median peak context 7–9K, max 15–37K.

The most transferable design finding is Appendix A: the best compactions are **not** narratives but briefs for
further execution — verbatim task copy + current occupation/intentions/next steps + artifacts/plan/completion
requirements/pointers. Appendix G operationalises it.

## What it does not show

- **SSSM is a proposal.** No checkpoint is trained or evaluated; the abstract says "we outline the concept".
  SAC's positive result uses off-the-shelf frontier models plus prompting.
- **Open-weight local models are the counter-result** (Appendix D): Qwen 3 Coder Next collapses 53.0→3.6 on
  SWE-bench Verified at 16K/12K; Gemma 4 31B 65.2→58.0; Step 3.7 Flash 70.0→56.6; Qwen 3.6 27B 68.6→65.0;
  MiniMax M2.7 72.6→67.8. Terminal-Bench degrades similarly.
- **The cost multiples are retail-API interpolation**, not self-hosted FLOPs. The measured 3.6×/5.6×/7× figures
  are H100 decode throughput at 256K vs 16K; the benchmark x-fold savings come from Appendix B's price model
  anchored at $25/$20 per million output tokens.
- **Constraints that exist only in the transcript are untested here.** Rule retention and post-compaction
  compliance are measured in intake-2630/2631, both of which show loss.

## Hardware lens (EPYC)

The local latency series is a DGX Spark, not the EPYC host or MI210. For our stack the mechanism still matters
but the multiplier is smaller: CPU decode is bandwidth-bound and already loses ~55% decode by 128k on EPYC, so
the local win from short context is real but far below 7×; on MI210 at batch 1 the gain is also KV-bandwidth
bound. The dominant MI210 effect is capacity — 64 GB HBM buys slots/concurrency, not a 7× per-token speedup.

## Actionables (ledger)

| Action | Owner | Disposition |
|---|---|---|
| Adopt the Appendix A six-field structure as the declared schema for the structured handoff artifact (A6) | context-and-token-economy.md (CF-AB-1) | immediate (design text) |
| Add a constraint-retention dimension beside the closed-book recall co-metric | context-and-token-economy.md (CF-3c) | immediate (design text) |
| Specify the lossless-log + bounded-read tool surface (A7) with the paper's read-only-what-you-need contract | context-and-token-economy.md (CF-AB-1 A7) | probe (gated on TOC-SP-5) |
| Record the local depth multiplier next to any adoption of the paper's 3.6–7× | cpu-decode-roofline-program.md | knowledge-only |
| Do not open an SSSM post-training workstream | model-architecture-readiness.md | decline (build) / knowledge-only |
| Treat this as one cited consideration in the YARN go/no-go, not a re-scope | long-context-program.md | trigger |

## Dive-surfaced sources

Already ingested in this run: 2610.31710 (Compact-Bench), 2610.31778 (Compaction-Friendly), 2611.03223 (ARCBench).

## Artifacts

Source HTML and text: `/mnt/raid0/llm/tmp/dive-2628/`.
