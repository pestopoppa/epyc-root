# GPU Candidates surface — add Qwen3.8-27B as the new stock-27B arm

**Status**: ACTIVE — scoping only; the artifact update is staged behind the Qwen3.8-27B rollout (INF-60).
**Created**: 2026-08-14
**Priority**: P2 (presentation surface; not evidence authority)
**Effort**: Low — re-populate one candidate row with already-partial Qwen3.8-27B data + fill the gaps

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
| Throughput — decode (optimized `draft-mtp`) | ✅ **47.57 t/s** (256 tok, draft_n 285/256 ≈ 90% accept) | measured 2026-08-14 on v9 `0db32c06e`/`10125` |
| Throughput — prefill pp512 | ⬜ pending | needs one `llama-bench -p 512` (or longer-prompt server call); the 13-token 70.95 t/s is not usable |
| Coding ladder (LCB/BCB/SWE) | ⛔ **operator-DECLINED** | "quality will improve certainly" (2026-08-14) — no coding comparison will be run for Qwen3.8. See open question below. |
| RAG-at-depth | ⬜ pending | no Qwen3.8 RAG measurement yet |
| MTP workload-gate (batched vs deep-RAG) | ⬜ partial | single-stream acceptance ~90% measured; the batched-vs-long-context gate the artifact documents for MTP is not measured for Qwen3.8 |

## Steps

- [ ] **Populate the throughput row** — add Qwen3.8-27B with the 47.57 t/s MTP decode (already measured)
  and the pending pp512 prefill, era-labeled v9 `0db32c06e`.
- [ ] **Prefill pp512** — one `llama-bench -m Qwen3.8-27B-Q8_0.gguf -ngl 999 -nkvo 1 -p 512 -n 128 -r 3`
  (or the KV-on-GPU server equivalent) to fill the prefill cell.
- [ ] **Decide the coding-ladder cell** — see the open question; do NOT silently re-run the coding bench
  the operator declined, and do NOT leave a blank cell that reads as "unmeasured" when it is
  "operator-declined".
- [ ] **RAG-at-depth + MTP workload-gate** — either run the equivalent RAG/deep-context probe (long-prompt
  single-stream vs batched, same recipe the artifact used) or explicitly mark the cells deferred.
- [ ] **Update the verdict prose** — the artifact's "Bottom line" ("nothing new displaces the lineup on
  merit") must be re-read once Qwen3.8-27B lands in the row: if Qwen3.8-27B becomes the new coding bar on
  quality grounds (operator's given), the "Stock 27B dense" verdict transfers to it.

## Open question (the one thing that needs a decision)

The artifact's *core* is the coding ladder (LCB/BCB/SWE), and the operator declined the Qwen3.8→Qwen3.6
quality comparison. So: does the Qwen3.8-27B row ship **throughput + RAG + MTP only, with the coding
ladder marked "operator-declined"**, or is the ladder populated anyway (re-running the coding bench,
which would contradict the operator's "don't verify" directive)? Recommend the former — honor the
decline, label the cell, and note that Qwen3.8-27B inherits the "coding bar" verdict on the operator's
quality-given basis, not on a fresh measurement.

## Deps

`INF-60` (qwen38-27b-replace-qwen36.md) — this artifact update is the *presentation* tail of that rollout.
