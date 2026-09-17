# Optical (Bitmap-Frame) Context Compression

**Completion note (2026-09-17)**: moved to `handoffs/completed/`. **Decision (operator, 2026-09-17): close — OCC-1 came back NEGATIVE.** On the served Qwen3-VL-30B-A3B reader the text arm scored SQuAD F1 0.888, while the five bitmap-frame arms scored 0.36–0.54 at billed-token ratios 0.33–0.52. No arm was non-inferior, so OCC-3 was never triggered and is closed SUPERSEDED. Evidence: research `84dc568d` (`data/occ1-optical-compression-20260916/`) and root `844a0502`. The findings (result, harness and re-run recipe for a better vision reader, pre-registered rule, belief rows) are extracted to [`wiki/context-management.md`](../../wiki/context-management.md) → *Compiled Update — 2026-09-17*. The OCC-2 billing record below stays here as the time-pinned reference that `wiki/cost-aware-routing.md` cites. The one still-open follow-up, SC85b (codify an OCC protocol), already lives in [`vidya-belief-substrate-program.md`](../active/vidya-belief-substrate-program.md). Body text below is historical.

**Status**: completed 2026-09-17 (closed, NEGATIVE). Previously: stub
**Created**: 2026-08-18 (via research intake, operator-approved 2026-08-18)
**Categories**: context_management, multimodal, cost_aware_routing, tool_implementation

## Objective

Establish whether rendering discarded conversation history into pixel-font PNG frames that a
vision-capable model reads back directly is cheaper, at equal recall, than the LLM-summarization
compaction we run today — **on a reader we actually serve**.

## Why this is a distinct track

Our compaction ([`tool-output-compression.md`](../active/tool-output-compression.md),
[`context-folding-progressive.md`](../active/context-folding-progressive.md)) is LLM-mediated: it costs a model
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

- [x] **OCC-1 — the decisive measurement.** Fixed history, one reader we serve: billed-token cost and
  QA recall, bitmap frames vs raw text. Requires a vision-capable local reader (see
  [`multimodal-pipeline.md`](../active/multimodal-pipeline.md) for the live vision path). Gate everything else
  on this.
  - 2026-09-16 scoping (zero inference): **GPU-only is feasible.** Reader = the served
    Qwen3-VL-30B-A3B Q4_K_M + F16 `qwen3vl_merger` mmproj. The champion `ef81196d5` ships
    `tools/mtmd/models/qwen3vl.cpp` and `libmtmd`, and clip has no backend restriction. The model
    fits the MI210 in about 21 GB. Harness, launch script and recipe are in research `070db22a`→`e2c48c13`, which passed the Fable review fixes
    (branch `sub/occ1-20260916`, `scripts/benchmark/occ1/README.md`), merged to research `main` at
    `0d3ca467`; the SC85 belief writer merged with root `sub/occ1-root-20260916` (`1d5f5314`). The reader test
    port is 18431 (`launch_reader.sh --port N`). Arms: text plus
    5 frame arms, 1568-px-wide, resample-free. SQuAD dev: 39 chunks × 30 q = 1,165 paired
    questions per arm, 234 requests, about 1.5 h of MI210 time. The full plan is pre-rendered at
    `/mnt/raid0/llm/tmp/occ1-run-20260916` (suite `261d8ac1eaed`). Predicted image cost is 2,401
    tokens per 6x10 frame, against about 8.7k text tokens per chunk. Next: GPU runner executes the
    README recipe (pilot, then full).
    Status 2026-09-16 (wrap-up): queued as **item 10** on the GPU queue; not run.
  - ✅ **RESULT 2026-09-16 15:41–16:16Z (sub-gpu-runner): OCC-1 is NEGATIVE under the pre-registration.**
    Evidence: research `84dc568d`, `data/occ1-optical-compression-20260916/`, holding the summary, digests
    and residency record, with no SQuAD text.
    - **Instrument.** Reader Qwen3-VL-30B-A3B-Instruct Q4_K_M + F16 mmproj on the champion build
      `b10301-ef81196d5`, MI210, n_ctx 16384.
    - **Fixture and metrics.** History fixture: SQuAD dev suite `261d8ac1eaed`, 1165 paired questions per arm.
      Billed tokens = server `usage.prompt_tokens`. Recall = SQuAD F1, with CIs from a chunk-clustered
      bootstrap. No codified protocol exists, so these are observations capped at Judged/Located.
    - **Text arm (BASELINE).** F1 **0.888**, EM 0.786, 9,286 prompt tok/req.
    - **Image arms (CANDIDATE)**, as F1 / token ratio vs text / ΔF1 [95% CI]:
      - 6x10-bw: 0.455 / 0.326 / −0.433 [−0.460, −0.407]
      - 6x10-color: 0.456 / 0.326 / −0.432 [−0.462, −0.402]
      - 8x8u-bw: 0.364 / 0.437 / −0.524 [−0.556, −0.489]
      - 12x12u-bw: 0.363 / 0.437 / −0.525 [−0.556, −0.495]
      - 8x13-bw: 0.536 / **0.516** / −0.351 [−0.375, −0.327]
    - **Verdicts.** The first four arms are NOT_NONINFERIOR. 8x13-bw is NEGATIVE_COST, because its ratio is
      above 0.5. Every EM McNemar p is below 1e-100.
    - **Validity.** No VOID reason fired. Residency was proven: 1283/1283 in-flight samples high and in KFD,
      peak +20.5 GiB. There were 0 cache hits. The 3-chunk pilot was also NEGATIVE.
    - **Reading.** Frames save 48–67% of billed tokens but lose 35–53 F1 points on this reader. No arm seeds
      OCC-3.
    - **Belief kernel.** 22 rows ingested (`ingest occ1`).
- [x] **OCC-2 — record the provider image-billing asymmetry** as a cost-aware-routing input,
  independent of OCC-1's outcome, with the staleness caveat attached. ✅ 2026-08-25 — see the
  OCC-2 Record section below (all cells re-verified against provider docs; Anthropic drift
  demonstrates the staleness caveat).
- [x] **OCC-3 — (only if OCC-1 is positive) re-derive the frame-shape table for our own readers.** ✅ 2026-09-17 CLOSED SUPERSEDED (not completed) — its gate failed: OCC-1 was NEGATIVE (root `844a0502`), and the operator closed the handoff 2026-09-17.
  - 2026-09-16: **not triggered**, because OCC-1 was NEGATIVE (no arm was POSITIVE). The box stays open only as
    the gated option; close or retire it at the next index pruning.
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
prior for the live cost-aware-routing surface in [`decision-aware-routing.md`](../active/decision-aware-routing.md)
§DAR-4b — the inference-time preference vector `ω_cost` and cost-scaling `τ` at the retriever
selection score (`epyc-orchestrator/orchestration/repl_memory/retriever.py`,
`_scalarized_selection_score` :46, `_retrieve` :225-368) — **if and only if** a hosted vision
reader (Gemini/OpenAI/Anthropic/Kimi) ever enters the routing pool. For local readers (OCC-1's
actual subject) image billing is irrelevant: their cost is tokens-decoded, not billed input.

## Reporting Instructions

Report OCC-1 as a measurement under [`MEASUREMENT.md`](../../MEASUREMENT.md) claim grammar: name the
reader, the history fixture, the billed-token accounting method, and the recall metric. A cost claim
without the reader named is not a claim.
