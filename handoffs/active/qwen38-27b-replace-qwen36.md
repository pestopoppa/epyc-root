# Qwen3.8-27B — replace Qwen3.6-27B in production

**Status**: ACTIVE — weights downloading 2026-08-14 (release day); no quality/throughput gate has run.
**Created**: 2026-08-14
**Priority**: P2 (model refresh; no production pain forcing it, but a same-day release refresh is cheap to stage)
**Effort**: Medium — download + load-smoke + quality gate + throughput + registry swap

## Objective

Stage `Qwen3.8-27B` as the replacement for `Qwen3.6-27B-MTP-Q8_0`, which is the **primary model for
`architect_general` + `coder_escalation`** (both served from the :8083 MI210 process, ROCm0; the 122B
vacated to `architect_critic` 2026-07-31). Qwen3.8 was released 2026-08-14.

## What is known (verified against HF on release day)

- Upstream: `Qwen/Qwen3.8-27B` (public, not gated), plus `Qwen/Qwen3.8-2.4T-A95B` (the large sibling).
- **Qwen3.8-27B is MULTIMODAL** — a vision projector (`mmproj`) ships alongside it. This is a new
  capability vs the text/code-only Qwen3.6-27B; treat it as optional, not a migration requirement.
- **MTP is packaged SEPARATELY** for Qwen3.8 (unlike Qwen3.6-27B's embedded MTP head):
  `ggml-org/Qwen3.8-27B-GGUF/mtp-Qwen3.8-27B-Q8_0.gguf` (3.16 GB). The base `Qwen3.8-27B-Q8_0.gguf`
  (28.6 GB ggml-org / 29.05 GB unsloth) does **not** embed it. Wiring the draft therefore needs an
  explicit `-md`/`--model-draft` sidecar, not the same-file self-draft Qwen3.6 used.

## Artifacts

| Artifact | Source | Size | Status |
|---|---|---|---|
| `Qwen3.8-27B-Q8_0.gguf` | `unsloth/Qwen3.8-27B-GGUF` | 29.05 GB | downloading (2026-08-14) |
| `mtp-Qwen3.8-27B-Q8_0.gguf` | `ggml-org/Qwen3.8-27B-GGUF` | 3.16 GB | downloading (2026-08-14) |
| `mmproj-Qwen3.8-27B-Q8_0.gguf` (optional, vision) | `ggml-org/Qwen3.8-27B-GGUF` | 0.63 GB | not downloaded |

Destination: `/mnt/raid0/llm/models/`. Download log: `/tmp/opencode/dl_qwen38.outerr`.

## Steps

- [ ] **Verify the download** — byte counts + GGUF header (`llama-gguf r`): arch, `block_count`,
  `context_length`, and whether MTP tensors (`nextn`) are present in the base or only in the sidecar.
- [ ] **Load smoke** on the v9 HIP build (`-ngl 999 -c 4096`, 32-token generation) — no op fallback,
  coherent output. This is the qwen3moe/qwen35moe-family op-coverage check the 27B dense needs.
- [ ] **MTP wiring** — confirm `--spec-type draft-mtp` with the explicit `mtp-*.gguf` sidecar loads and
  drafts (vs Qwen3.6's embedded self-draft). Check whether `draft_model` in the registry must change from
  same-file to the sidecar path.
- [x] **Quality gate — DECLINED by operator (2026-08-14):** *"quality will improve certainly."* The
  Qwen3.8→Qwen3.6 quality uplift is taken as a given (same-day release refresh); no coder/architect
  quality comparison will be run. The load-smoke below is the only remaining correctness check, and it
  confirms the model loads + generates — a technical check, not a quality gate.
- [ ] **Throughput** — decode + prefill on the MI210 (plain and `draft-mtp`), vs the Qwen3.6-27B numbers
  (~99.8 t/s plain at `-c 512`; the coder_escalation serving baseline). MTP acceptance rate too. For the
  serving config, not a go/no-go gate.
- [ ] **Registry swap** — `architect_general` + `coder_escalation`: `model_path` →
  `Qwen3.8-27B-Q8_0.gguf`, `draft_model` → `mtp-Qwen3.8-27B-Q8_0.gguf` (if sidecar wiring confirmed),
  then `stack_change_pipeline.py` regenerate + the standard model-stack-change checklist.

## Key questions this handoff must answer

1. **MTP sidecar vs embedded**: does the base GGUF actually omit MTP tensors, and does the sidecar wire
   cleanly with `--spec-type draft-mtp`? (Qwen3.6 relied on embedded self-draft — a same-file assumption
   that may not transfer.)
2. **Multimodal**: is the vision projector a reason to *also* stage Qwen3.8 for `worker_vision`/
   `vision_escalation`, or strictly out of scope for this coder/architect swap?
3. ~~**Is this even worth it**~~ — RESOLVED by operator (2026-08-14): quality uplift is a given, so the
   swap is worth it on quality grounds alone. Throughput won't move materially (dense, BW-bound); the
   throughput step exists to record the serving baseline, not to gate the decision.
