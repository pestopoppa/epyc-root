# GPU Candidates surface — add Qwen3.8-27B as the new stock-27B arm

**Status**: ACTIVE — SWE rung complete; best-configuration refreshes remain (2026-08-20). The devcontainer blocker cleared; both protocols are
now scored and in the artifact. **Agentic SWE-40 = 21/40 (52.5%)** — re-run after fixing the harness
tool-call parser (`3bf16c3f`), superseding the provisional 15/40. **Oracle SWE-40 = 20/40 (50.0%)** vs
stock 27B's 23/40 — a **non-resolving** difference (paired exact McNemar p = 0.375, 5 discordant), so
read it as a tie on SWE, not a regression. Remaining: re-collect the 24-cell grid at the measured
`n-max 8` optimum (the grid was captured at 4, ~8.7% below peak).
**Created**: 2026-08-14
**Priority**: P2 (presentation surface; not evidence authority)
**Effort**: Low — re-populate one candidate row with already-partial Qwen3.8-27B data + fill the gaps

## NEXT STEP — top of queue

Re-collect Qwen3.8's 24-cell np × depth grid at measured `n-max 8`, then depth-sweep the other arms
under their own best draft settings. The existing Qwen3.8 grid used `n-max 4`, about 8.7% below peak.
Do not rerun the closed SWE protocols or revive the cleared devcontainer/parser blocker.

## The artifact

`/mnt/raid0/llm/tmp/claude-artifacts/np_context_v8_decision.html` — *"GPU Candidates — Throughput &
Model-Selection Surface"* (SHA-256 `816ad5cdd532634edb48f608321fb6ffc3d5546c3ff74aa6c7b54cf0655e6e2b`).
It is the **presentation surface only**; evidence authority is the research bundles
`epyc-inference-research/artifacts/np_context_study_v8_20260727/` (+ `np_context_study_20260723/` for v7),
per `gpu-serving-tie-in-program.md:294`. It currently shows: architect trio (A4 35B-A3B, **Stock 27B dense**,
A1 122B-A10B IQ2) on v7, plus the 27B finetunes (Fable-Fusion, ThinkingCap) and Laguna-S-2.1 IQ2 on v8, each
with the coding ladder (LCB-hard n=53, BCB-hard n=90, SWE-40 n=40), RAG-at-depth, throughput, and MTP
workload-gate.

## Task

Add **Qwen3.8-27B** as the new "Stock 27B" arm — the direct successor of the `Stock 27B dense`
(= Qwen3.6-27B) row, which is the current coding bar ("Tops SWE + BCB"). The update is a *row*, not a
re-design: same axes, same era-labeling discipline (label the kernel era; never silently re-collect).

## Equivalent axes + status

| Axis | Qwen3.8-27B status | Note |
|---|---|---|
| Throughput — decode (optimized `draft-mtp`) | ✅ **flat ~45 t/s** single-stream (47.6 @2k → 45.0 @32k) | 24-cell np × depth sweep on **real olympiadbench prompts**, v9 `0db32c06e`/`10125` |
| Throughput — prefill pp512 | ✅ **727.29 ± 28.00 t/s** | `llama-bench -ngl 999 -nkvo 1 -p 512 -r 3` |
| Coding ladder (LCB/BCB/SWE) | ✅ **RAN** — see *Coding ladder — WAS RUN* below | Originally ⛔ operator-DECLINED ("quality will improve certainly", 2026-08-14); the operator later authorized the ladder anyway ("both rungs, proceed") and it landed. |
| RAG-at-depth | ✅ measured | decode vs context depth is **flat** across 2k–32k on real prompts — no KV-read-cost decay in this range |
| MTP workload-gate (batched vs deep-RAG) | ✅ measured | peak **aggregate 157.3 t/s @np8/2k**; no MTP reversal at depth on real prompts |

> **RETRACTED (2026-08-15/16) — do not cite**: an earlier synthetic sweep reported a decode-vs-depth
> decline (`37.15 @512 → 37.95 @2k → 22.22 @8k → 13.61 @32k`) and an "**MTP HURTS at depth**" workload
> gate (plain beating MTP at 8k/32k). Both were a **synthetic random-word-prompt artifact** — the low
> MTP acceptance came from the random-word prompt, not from context depth. The 24-cell np × depth sweep
> on real olympiadbench prompts supersedes them with the flat curve and 157.3 t/s @np8 peak in the table
> above; those corrected numbers are the ones the artifact ships.

## Coding ladder — WAS RUN (supersedes the earlier "deferred")

The operator declined the Qwen3.8→Qwen3.6 quality comparison on 2026-08-14, then later authorized the coding
ladder anyway ("both rungs, proceed"). Full architect bench (v9 `0db32c06e`, seeded temp 0.6, MTP, reasoning
off) landed:

| Rung | Score | |
|---|---|---|
| LCB-hard (n=53) | **52.8%** (28/53) | tops the 27B class |
| BCB-hard (n=90) | **31.1%** (28/90) | ties stock 27B |
| SWE-40 (n=40) | **15/40 = 37.5% (provisional)** | agentic, understated — 19/40 empty from format-mismatch, now fixed |
| humaneval | 96.3% (158/164) | |
| aime25 / gpqa (cot) / gpqa (letter) / mmlu_pro / olympiad_hard | 76.7% / 81.3% / 42.4% / 56.7% / 47.1% | |

It is the same LCB-hard n=53 / BCB-hard n=90 / SWE-40 n=40 recipe the artifact already uses, so the
results slot straight into this row.

## Steps

- [x] **Populate the throughput row** — Qwen3.8-27B flat ~45 t/s MTP decode, pp512 prefill 727 t/s, era v9 `0db32c06e`.
- [x] **Prefill pp512** — `727.29 ± 28.00 t/s` (`llama-bench -ngl 999 -nkvo 1 -p 512 -r 3`).
- [x] **Coding-ladder cell** — populated (LCB 52.8% / BCB 31.1% / agentic SWE 21/40 / oracle SWE 20/40). ✅ 2026-08-20
- [x] **RAG-at-depth + MTP workload-gate** — measured: single-stream decode FLAT ~45 t/s (47.6@2k → 45.0@32k);
  peak aggregate 157.3 t/s @np8/2k. (The earlier "37→13.6 decline / MTP reversal" was a synthetic
  random-word-prompt artifact — corrected; real prompts give a flat MTP curve.)
- [x] **Update the verdict prose** — bottom line + verdict card re-read with Qwen3.8-27B as the new 27B coding bar.
- [x] **SWE-40 finalised on BOTH protocols** ✅ 2026-08-20 — agentic **21/40 (52.5%)** (supersedes the
  provisional 15/40; harness tool-call parser fixed, `3bf16c3f`) and oracle **20/40 (50.0%)**, a
  non-resolving difference vs stock 27B's 23/40 (paired exact McNemar **p = 0.375**, 5 discordant).
- [x] **Artifact reworked to best-configuration results only** ✅ 2026-08-20 — per operator instruction the
  surface tracks the best measured config per arm. Removed: the spec-off baseline column and the
  "N× over plain" ratio, the `FF 27B (non-MTP)` grid, the MTP workload-gate card, and every
  non-best FF rate. Headline is now **70.0 t/s** (dFlash2 block-8, np=1) as best *measured* with the
  parity caveat, alongside **55.46 t/s** as best *selectable*.
- [ ] **Re-collect the 24-cell np×depth grid at `n-max 8`** — the published grid was captured at
  `n-max 4`, i.e. ~8.7% under the measured optimum, and its cells were WITHDRAWN from the artifact
  rather than shipped below peak. Needs GPU; blocked only on compute availability.
- [ ] **Depth-sweep the other arms (A4, A3, A1, FF, Laguna)** — none was ever draft-depth swept, so
  their published figures are best-KNOWN, not best-POSSIBLE. Qwen3.8 gained 8.7% from its sweep
  alone; the same headroom plausibly exists here and would change cross-arm ranking.
- [ ] **Restore the MTP workload-gate finding somewhere durable** — it was removed from the artifact
  because it only exists as a comparison against a non-best config (MTP is net-negative for FF on
  single-stream deep RAG). It survives in this handoff and the wiki, but has no home on any surface.

## Deps

`INF-60` (qwen38-27b-replace-qwen36.md) — this artifact update is the *presentation* tail of that rollout.

## Completed 2026-08-15

- **Artifact updated across ALL sections** — `/mnt/raid0/llm/tmp/claude-artifacts/np_context_v8_decision.html`:
  header, new-candidate verdict card, coding ladder (LCB 52.8% / BCB 31.1%), reasoning ladder (aime25 76.7%,
  gpqa 42.4/81.3%), RAG heatmap, full 24-cell GRID, router-integration plan, bottom line.
- **np × depth 24-cell sweep done** (real olympiadbench prompts): single-stream flat ~45 t/s, peak 157 t/s @np8.
  CORRECTED the earlier synthetic "37→13.6 decline / MTP reversal" — that was a random-word-prompt artifact.
- **SWE images built** (40) + **containers started** + **agentic harness (P2e) running** on the 40 instances.
- ~~The coding-ladder cell stays `operator-declined — deferred`~~ — **superseded 2026-08-16**: the operator
  authorized the ladder, it ran, and the cell is populated. See *Coding ladder — WAS RUN* above.

## Completed 2026-08-16

- Agentic run 1 landed → **21 patches / 19 empty** (format-mismatch, not model failure).
- Harness parser fixed (native tool-call translation, 20/20 unit tests pass) — staged, awaiting commit.
- **SWE-40 = 15/40 (provisional)** written to the artifact; the re-run is parked on the devcontainer restart.
