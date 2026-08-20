# Qwen3.8-27B — replace Qwen3.6-27B in production

**Status**: ACTIVE — download/smoke/MTP/throughput/architect-bench done; **registry swap DONE 2026-08-20** (`b376dadd`, validator 0 problems). Only the `stack_change_pipeline.py` regenerate + stack-change checklist remain, and those need a stack start — nothing is serving today, so `live == config` is unverified.
**Created**: 2026-08-14
**Priority**: P2 (model refresh; no production pain forcing it, but a same-day release refresh is cheap to stage)
**Effort**: Low-Medium — download/smoke/MTP/throughput/architect-bench done; the registry swap is the last step (the 2026-08-14 quality-gate decline was later reversed and the coding ladder ran)

## Objective

Stage `Qwen3.8-27B` as the replacement for `Qwen3.6-27B-MTP-Q8_0`, which is the **primary model for
`architect_general` + `coder_escalation`** (both served from the :8083 MI210 process, ROCm0; the 122B
vacated to `architect_critic` 2026-07-31). Qwen3.8 was released 2026-08-14.

## What is known (verified against HF on release day)

- Upstream: `Qwen/Qwen3.8-27B` (public, not gated), plus `Qwen/Qwen3.8-2.4T-A95B` (the large sibling).
- **Qwen3.8-27B is MULTIMODAL** — a vision projector (`mmproj`) ships alongside it. This is a new
  capability vs the text/code-only Qwen3.6-27B; treat it as optional, not a migration requirement.
- **MTP/NextN head is EMBEDDED in the unsloth base — NOT a separate sidecar (CORRECTION).** GGUF-header
  verification (`llama-gguf r`) shows the unsloth `Qwen3.8-27B-Q8_0.gguf` carries `blk.64.nextn.*`
  tensors (`eh_proj`/`enorm`/`hnorm`/`shared_head_norm`) and `qwen35.nextn_predict_layers` metadata —
  the same embedded self-draft layout as `Qwen3.6-27B-MTP-Q8_0`. So the wiring is **same-file
  `--spec-type draft-mtp` self-draft, unchanged from Qwen3.6**. The ggml-org `mtp-*.gguf` (3.16 GB) is a
  *full layer-64* draft model (`attn` + `ffn` + `nextn`) for the ggml-org base (which strips MTP) — it is
  **redundant** for the unsloth base and was downloaded only as a fallback.

## Artifacts

| Artifact | Source | Size | Status |
|---|---|---|---|
| `Qwen3.8-27B-Q8_0.gguf` | `unsloth/Qwen3.8-27B-GGUF` | 29.05 GB | ✅ downloaded + header-verified (embeds nextn/MTP) |
| `mtp-Qwen3.8-27B-Q8_0.gguf` | `ggml-org/Qwen3.8-27B-GGUF` | 3.16 GB | ✅ downloaded (redundant fallback; unsloth base embeds MTP) |
| `mmproj-Qwen3.8-27B-Q8_0.gguf` (optional, vision) | `ggml-org/Qwen3.8-27B-GGUF` | 0.63 GB | not downloaded |

Destination: `/mnt/raid0/llm/models/`. Download log: `/tmp/opencode/dl_qwen38.outerr`.

## Steps

- [x] **Verify the download** ✅ 2026-08-14 — both files at full declared size (29,047,086,048 B /
  3,164,006,688 B); GGUF header shows arch `qwen35`, `block_count`, `context_length`, and the embedded
  `nextn`/MTP tensors in the base (see "What is known" — the MTP-sidecar assumption was wrong).
- [x] **Load smoke** ✅ 2026-08-14 — PASS on v9 HIP (`-ngl 999 -c 4096 --spec-type draft-mtp --spec-draft-n-max 4`): model loads (31.98 GB VRAM), generates coherently ("Quicksort is a highly efficient sorting algorithm…"), no op-fallback warnings.
- [x] **MTP wiring** ✅ 2026-08-14 — RESOLVED: the unsloth base embeds the nextn/MTP head, so
  `--spec-type draft-mtp` self-draft is same-file, exactly like Qwen3.6-27B-MTP. `draft_model` in the
  registry stays the same file. The separate `mtp-*.gguf` sidecar is NOT needed.
- [x] **Quality gate — DECLINED by operator (2026-08-14):** *"quality will improve certainly."* The
  Qwen3.8→Qwen3.6 quality uplift is taken as a given (same-day release refresh); no coder/architect
  quality comparison will be run. The load-smoke below is the only remaining correctness check, and it
  confirms the model loads + generates — a technical check, not a quality gate.
- [x] **Throughput (optimized mode, GPU `draft-mtp`)** ✅ 2026-08-14/15 — prefill pp512 **727.29 t/s**; single-stream decode **flat ~45 t/s across 2k–32k depth** on real olympiadbench prompts (peak aggregate **157 t/s @np8**). **CORRECTION:** an earlier synthetic random-word probe showed a spurious 37→13.6 t/s decline + "MTP reversal at depth" — that was a prompt artifact (random words kill MTP acceptance), NOT real behaviour. On real prompts decode is flat and MTP holds. (natural-prompt single-shot 47.57 t/s still stands as the interactive figure.)
- [x] **Registry swap** ✅ 2026-08-20 — master registry commit `b376dadd`. `architect_general` +
  `coder_escalation`: `model` / `model_path` / `draft_model` / descriptor `name`+`path` →
  `Qwen3.8-27B-Q8_0.gguf` (self-draft, same file). `epyc-orchestrator/stack_templates/default.yaml`
  also repointed, and its `spec_overrides.draft_max: 24` corrected — that override was **silently
  beating** the registry's measured value at stack-assembly time.
  - **`model_role` was the trap.** It is load-bearing, not documentation: `model_descriptors.py:1233-1244`
    substitutes the `model_role` role's config when an alias's model id differs from its `server_mode`
    entry (recording `ignored_model_id`). Swapping `model_path` alone would have **served Qwen3.6 while
    the registry read as swapped**. Both refs now point at a new `qwen38_27b_q8_local` role;
    `qwen36_27b_mtp_q8_local` is RETAINED unmodified as the rollback anchor.
  - **`draft_max` 4 → 8, re-measured not inherited.** 4 was the measured optimum for *Qwen3.6*; depth is
    per-model. Qwen3.8 sweep (np=1, 12 real olympiadbench prompts, v9 `0db32c06e`/10125): plain 27.78 /
    n2 39.77 / n3 46.61 / n4 51.03 / n6 55.22 / **n8 55.46** / n12 51.14 t/s; acceptance 0.842 → 0.482
    across depth 2→8. Curve turns over past 8. MTP is worth **2.00× over plain** at n-max 8.
  - Every figure in the new role is measured on THIS artifact: `baseline_tps 27.78`, `optimized_tps 55.46`,
    `vram_gib 37.22` (n_slots=4, n_ctx 262144, q8_0 KV, kv_unified=true, sampled DURING residency).
    `optimized_tps_long_context` and `contended_tps` are explicitly `null` — not measured, and copying
    Qwen3.6's across would be a false attestation.
  - Validator: **0 problems** (this required fixing a pre-existing duplicate-key defect that had been
    failing the validator closed for the whole file — commit `a94e0e01`).
- [ ] **Stack-change checklist / `stack_change_pipeline.py` regenerate** — NOT run. Nothing is serving
  (`:8083` unbound), so config and runtime agree only by both being absent. `live == config` is
  UNVERIFIED until someone actually starts the stack; that is a separate lifecycle action with its
  own gates and was deliberately not taken here.
- [x] **Architect bench (reasoning + coding ladders)** ✅ 2026-08-15 — L0–L4: mmlu_pro 56.7%, gpqa_diamond 42.4% (letter) / 81.3% (CoT), aime25 **76.7%**, olympiadbench_hard 47.1%; P2a–P2d: humaneval 96.3%, BCB-hard 31.1%, LCB-hard **52.8%** (tops stock 45.3%), SWE-oracle 39/40 single-shot (2 hard tool-using instances deferred to the agentic rung). Full tables in `gpu-candidates-surface-qwen38-update.md` + the artifact dir. The quality uplift the operator banked is now measured — it is real on LCB (52.8 vs 45.3) and aime25 (76.7), near-parity elsewhere, with SWE + agentic still landing.

## Key questions this handoff must answer

1. ~~**MTP sidecar vs embedded**~~ — ANSWERED 2026-08-14: the unsloth base EMBEDS the nextn/MTP head
   (`blk.64.nextn.*` present in the GGUF header), so it is a like-for-like replacement for
   `Qwen3.6-27B-MTP-Q8_0` with **same-file self-draft** — no wiring change. The ggml-org sidecar is a
   full layer-64 draft model for the ggml-org (MTP-stripped) base and is redundant here.
2. **Multimodal**: is the vision projector a reason to *also* stage Qwen3.8 for `worker_vision`/
   `vision_escalation`, or strictly out of scope for this coder/architect swap?
3. ~~**Is this even worth it**~~ — RESOLVED by operator (2026-08-14): quality uplift is a given, so the
   swap is worth it on quality grounds alone. Throughput won't move materially (dense, BW-bound); the
   throughput step exists to record the serving baseline, not to gate the decision.
