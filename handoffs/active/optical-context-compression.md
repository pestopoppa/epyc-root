# Optical (Bitmap-Frame) Context Compression

**Status**: stub
**Created**: 2026-08-18 (via research intake, operator-approved 2026-08-18)
**Categories**: context_management, multimodal, cost_aware_routing, tool_implementation

## Objective

Establish whether rendering discarded conversation history into pixel-font PNG frames that a
vision-capable model reads back directly is cheaper, at equal recall, than the LLM-summarization
compaction we run today — **on a reader we actually serve**.

## Why this is a distinct track

Our compaction ([`tool-output-compression.md`](tool-output-compression.md),
[`context-folding-progressive.md`](context-folding-progressive.md)) is LLM-mediated: it costs a model
call, adds latency, and is nondeterministic — the failure surface our prompt-determinism work exists
to contain. Optical compaction is **local, deterministic, and inference-free**: no model call, no API
key, no latency beyond rasterization. If the recall/cost tradeoff holds it is a strictly better
mechanism for the same job; if it does not, that is a cheap negative result.

## Research Context

| Intake ID | Title | Relevance | Verdict | Verification |
|-----------|-------|-----------|---------|--------------|
| intake-1159 | `@oh-my-pi/snapcompact` — bitmap-frame context compression | high | worth_investigating | dive-verified |
| intake-1148 | oh-my-pi (omp) — the parent harness | high | adopt_patterns | dive-verified |

## Open Questions

- **The decisive one, and it is cheap:** for a fixed history, what is billed-token cost and QA recall
  for bitmap frames versus raw text, on a model we serve? Nothing should be adopted before this.
- Does the technique survive transfer at all? Every published frame shape targets a hosted frontier
  vision reader (Claude/Gemini/GPT/Kimi lines). We serve local models; the shape table would have to
  be re-derived, and no evidence says the effect survives.
- What is the cost of losing exact addressability? Rasterized history cannot be grepped, diffed, or
  partially quoted, and OCR-through-the-model failure is silent and content-dependent, not loud.

## Notes

- **The upstream claim ships without its evidence.** `docs/compaction.md` at head `37eee719` states
  the shape table comes from 200k-token evals "where bitmap frames preserved QA recall at lower
  billed-token cost than raw text for vision-capable models". The package contains ~70 experiment
  scripts (SQuAD harness, `exp01`–`exp22`, logit-lens and occlusion probes) and **zero committed
  results**. Not checkable from the repository — which is why intake-1159 is `worth_investigating`,
  not `adopt`.
- **Provider image-billing asymmetry is true independently of adoption** and is worth recording for
  cost-aware routing on its own: Gemini 3.x bills a *fixed* per-image budget at any pixel size (so
  larger frames are free characters), OpenAI patch billing is area-proportional (so larger frames
  cannot help), Anthropic high-res lines get larger frames under a visual-token cap, and Kimi's
  processor downscales past 1792px. This table is pinned to provider pricing and can silently go
  stale.
- Implementation is MIT, ~2,040 lines of TypeScript plus native rasterization, published standalone
  on npm as `@oh-my-pi/snapcompact`.

## Progress Checklist

- [ ] **OCC-1 — the decisive measurement.** Fixed history, one reader we serve: billed-token cost and
  QA recall, bitmap frames vs raw text. Requires a vision-capable local reader (see
  [`multimodal-pipeline.md`](multimodal-pipeline.md) for the live vision path). Gate everything else
  on this.
- [ ] **OCC-2 — record the provider image-billing asymmetry** as a cost-aware-routing input,
  independent of OCC-1's outcome, with the staleness caveat attached.
- [ ] **OCC-3 — (only if OCC-1 is positive) re-derive the frame-shape table for our own readers.**
  The published shapes do not transfer.

## Reporting Instructions

Report OCC-1 as a measurement under [`MEASUREMENT.md`](../../MEASUREMENT.md) claim grammar: name the
reader, the history fixture, the billed-token accounting method, and the recall metric. A cost claim
without the reader named is not a claim.
