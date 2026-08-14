# Qwen3.8-27B — replace Qwen3.6-27B in production

**Status**: ACTIVE — weights downloaded + header-verified 2026-08-14 (release day); load-smoke + throughput pending; quality gate declined.
**Created**: 2026-08-14
**Priority**: P2 (model refresh; no production pain forcing it, but a same-day release refresh is cheap to stage)
**Effort**: Low-Medium — download (done) + load-smoke + throughput + registry swap (quality gate declined)

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
- [ ] **Load smoke** on the v9 HIP build (`-ngl 999 -c 4096`, 32-token generation) — no op fallback,
  coherent output. This is the qwen35moe/qwen35-family op-coverage check the 27B dense needs.
- [x] **MTP wiring** ✅ 2026-08-14 — RESOLVED: the unsloth base embeds the nextn/MTP head, so
  `--spec-type draft-mtp` self-draft is same-file, exactly like Qwen3.6-27B-MTP. `draft_model` in the
  registry stays the same file. The separate `mtp-*.gguf` sidecar is NOT needed.
- [x] **Quality gate — DECLINED by operator (2026-08-14):** *"quality will improve certainly."* The
  Qwen3.8→Qwen3.6 quality uplift is taken as a given (same-day release refresh); no coder/architect
  quality comparison will be run. The load-smoke below is the only remaining correctness check, and it
  confirms the model loads + generates — a technical check, not a quality gate.
- [ ] **Throughput** — decode + prefill on the MI210 (plain and `draft-mtp`), vs the Qwen3.6-27B numbers
  (~99.8 t/s plain at `-c 512`; the coder_escalation serving baseline). MTP acceptance rate too. For the
  serving config, not a go/no-go gate.
- [ ] **Registry swap** — `architect_general` + `coder_escalation`: `model_path` →
  `Qwen3.8-27B-Q8_0.gguf` (and `draft_model` stays the same file), then `stack_change_pipeline.py`
  regenerate + the standard model-stack-change checklist.

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
