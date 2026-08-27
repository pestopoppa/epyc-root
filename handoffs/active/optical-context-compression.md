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
| intake-1148#record | oh-my-pi (omp) — the parent harness | high | adopt_patterns | dive-verified |

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
- [x] **OCC-2 — record the provider image-billing asymmetry** as a cost-aware-routing input,
  independent of OCC-1's outcome, with the staleness caveat attached. ✅ 2026-08-25 — see the
  OCC-2 Record section below (all cells re-verified against provider docs; Anthropic drift
  demonstrates the staleness caveat).
- [ ] **OCC-3 — (only if OCC-1 is positive) re-derive the frame-shape table for our own readers.**
  The published shapes do not transfer.

## OCC-2 Record — Provider Image-Billing Asymmetry (2026-08-25)

Recorded independent of OCC-1's outcome: the asymmetry is a cost-aware-routing input in its own
right. All cells re-verified against primary provider docs on 2026-08-25; sources inline.

### Billing shape by provider

| Provider | Billing shape | Implication for frame-size optimization | As-of | Verification |
|----------|---------------|------------------------------------------|-------|--------------|
| **Google Gemini 3.x** | Fixed per-image budget at any pixel size, keyed only by `media_resolution`: LOW 280 / MEDIUM 560 / HIGH 1120 / ULTRA_HIGH 2240 tokens per image (default = HIGH, 1120). Pre-Gemini-3: 258 tokens/image Pan-and-Scan. | The one flat-rate reader: **larger frames are free characters** — pack more text per frame up to the model's pixel/request limits. | 2026-08-25 | VERIFIED — Google Cloud Gemini Enterprise Agent Platform docs, "Image tokenization" (page last updated 2026-08-24; marked Preview/Pre-GA). ai.google.dev unreachable from this host; verified via the Google Cloud mirror. |
| **OpenAI (gpt-4.1 / gpt-5.x vision)** | Area-proportional: image = 32×32 px patches; billed tokens = patch count × model multiplier (1.2×–2.46× by model). Per-model patch budgets (1,536 high / 2,500 / 10,000) cap cost by downscaling; gpt-5.6 `original`/default bills raw patch count with **no** cap. | Larger frames never help: cost scales with area; beyond the budget the image is downscaled (no fidelity gain), and on gpt-5.6 default detail larger frames are strictly more expensive. | 2026-08-25 | VERIFIED — platform.openai.com/docs/guides/vision, "Calculating costs". |
| **Anthropic (Claude 4.7+, high-res tier)** | Patch-based visual tokens: ⌈w/28⌉×⌈h/28⌉ per image, area-proportional under a hard per-image cap. High-res tier: max long edge 2576 px / **4784 visual tokens**; standard tier: 1568 px / 1568 tokens. | Larger frames allowed only within the tier cap and billed per pixel inside it — bigger frame = more tokens, never free. | 2026-08-25 | VERIFIED — docs.anthropic.com/en/docs/build-with-claude/vision, "Resolution and token cost". NOTE: the tile model the upstream note was built on (768 px tiles @ 1600 tokens, 100-tile cap) is gone from current docs — the staleness caveat is demonstrated, not hypothetical. |
| **Kimi (kimi-k2.6 / kimi-k3 vision)** | Dynamic, resolution-proportional token billing (higher resolution → more tokens; use the token-estimation API to predict). Docs recommend ≤4K (4096×2160); higher resolutions "will only cost more time processing the input without improving model understanding performance" (server-side cap implied). | Larger frames cost more tokens and gain nothing past ~4K. The specific 1792 px downscale figure from the upstream note is NOT in current Kimi API docs — treat as unverified; likely inherited from the open-source Kimi-VL model card. | 2026-08-25 | PARTIAL — billing shape VERIFIED (platform.kimi.ai/docs/guide/use-kimi-vision-model, "Estimate token usage and costs"; kimi-k2-6-quickstart, "Recommended Resolution"); the 1792 px numeric claim is unverified-as-of-2026-08-25. |

### Staleness caveat (load-bearing)

This table is pinned to provider pricing and **can silently go stale — and already has**: the
Anthropic cell's tile formulation in the upstream note does not match current docs. Provider
pricing pages change without notice. Every cell carries its as-of date and source; **re-verify
against the cited source before any decision consumes these numbers**. This table is a
time-pinned external reference, not a measurement claim under MEASUREMENT.md.

### Cost-aware-routing consumer

One-line pointer (nothing consumes this today): treat this table as a per-provider cost-shape
prior for the live cost-aware-routing surface in [`decision-aware-routing.md`](decision-aware-routing.md)
§DAR-4b — the inference-time preference vector `ω_cost` and cost-scaling `τ` at the retriever
selection score (`epyc-orchestrator/orchestration/repl_memory/retriever.py`,
`_scalarized_selection_score` :46, `_retrieve` :225-368) — **if and only if** a hosted vision
reader (Gemini/OpenAI/Anthropic/Kimi) ever enters the routing pool. For local readers (OCC-1's
actual subject) image billing is irrelevant: their cost is tokens-decoded, not billed input.

## Reporting Instructions

Report OCC-1 as a measurement under [`MEASUREMENT.md`](../../MEASUREMENT.md) claim grammar: name the
reader, the history fixture, the billed-token accounting method, and the recall metric. A cost claim
without the reader named is not a claim.
