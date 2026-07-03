# Progress — 2026-07-02 — Research Intake (intake-751..772)

## Session

Processed a 15-URL research-intake batch (operator-provided) + an 8-entry approved literature expansion. All via parallel per-URL sub-agents (Phase 1+2); main agent did all writes (Phase 3–5) per governance.

- **Index:** `research/intake_index.yaml` grew 747 → **772 entries** (intake-751..772). `validate_intake.py` exit 0.
- **Within-batch dedup:** URLs #4 (blog) + #5 (arXiv 2605.03413) = same paper → merged into **intake-754**. URLs #1 (arXiv 2606.26493) + #2 (HF model) = paper + its weights → kept as **intake-751** (paper) + **intake-752** (model, `arxiv_id: null` to avoid a primary-key collision).

## 14 provided sources (intake-751..764)

| ID | Source | Verdict | Rel |
|----|--------|---------|-----|
| 751/752 | Nemotron-Labs-TwoTower (diffusion LM, frozen-AR + trained-denoiser two-tower; 2.42× @ 98.7%) | worth_investigating | med |
| 753 | "Don't Train the Model, Evolve the Harness" (Meta-Harness on frozen open model, 0→80.1%) | adopt_patterns | **high** |
| 754 | Learning to Theorize the World (NEO program-induction + MDL) | worth_investigating | med |
| 755 | AdaJEPA (online test-time JEPA world-model adaptation) | not_applicable* | low |
| 756 | Qwen3.6-27B-NVFP4 (GPU-native FP4, FP8-parity) | not_applicable* | med |
| 757 | Dockerless (execution-free SWE patch verifier) | worth_investigating | med |
| 758 | Scaling Embeddings > Scaling Experts (LongCat-Flash-Lite scaling laws) | adopt_patterns | med |
| 759 | ROCm/aiter (AMD kernel lib — **gfx90a NOT supported**) | adopt_patterns | med |
| 760 | ROCm/triton (**gfx90a first-class**) | adopt_component | **high** |
| 761 | ROCm/flash-attention (**gfx90a via CK+Triton**) | adopt_component | **high** |
| 762 | vLLM Dockerfile.rocm (gfx90a in PYTORCH_ROCM_ARCH; AITER excludes it; ROCm 7.2.3 base) | adopt_patterns | **high** |
| 763 | vLLM v0.6.5 ROCm docs (**default ROCm 6.2 = our bind-mount**; MI210 listed) | worth_investigating | **high** |
| 764 | PorTAL (base-agnostic adapter + per-base converter refit) | worth_investigating | med |

\* not_applicable flagged for operator confirmation (creative-use notes preserved).

## 8 approved expansion entries (intake-765..772)

Cross-model-LoRA / hypernetwork cluster (chased from PorTAL): **765** Cross-LoRA (only training-free/CPU-plausible member), **766** LoRA-X (ICLR'25, same-family-only), **767** CAST (activation-space, evidence-weak), **768** SHINE, **769** Profile-to-PEFT, **770** Platonic Representation Hypothesis (theoretical basis; warns alignment weakest in our small-drafter regime), **771** Text-to-LoRA (Sakana, **open code+weights** — the actionable entry). Autopilot cluster (chased from harness-opt): **772** Darwin Gödel Machine (adopt_patterns, **high** — canonical reference for our autopilot loop).

## Key decision-grade finding — MI210 gfx90a support matrix

gfx90a IS supported by ROCm/triton, ROCm/flash-attention, and vLLM core (`PYTORCH_ROCM_ARCH`); **AITER/MORI/DeepEP are gfx942/gfx950-only**. vLLM v0.6.5 docs default to ROCm 6.2 (our bind-mount) and list MI210 → the viable path for the open "vLLM MI210 number" item (`2026-07-02-mi210.md`) is a **from-source current-vLLM build for gfx90a**, expecting no AITER acceleration.

## Handoffs updated (Phase 4a)

`gpu-acceleration-path.md` (ROCm cluster + support matrix), `meta-harness-optimization.md` (753), `engram-conditional-memory.md` (758 + MATH500 contradiction), `tq3-quantization-evaluation.md` (756 NVFP4 bar), `speculative-decoding-mtp-refresh.md` (751/752 two-tower contrast).

## Follow-on (in progress this session)

Operator requested a review/audit + deep-dive distillation into handoffs. Targets: ROCm/MI210 build-path deep-dive + mi210 progress-log resolution; Darwin Gödel → autopilot implementable patterns; cross-model-LoRA cluster decision-matrix deep-dive.

## Phase 2 (same session) — Deep-dive distillation + autopilot implementation

Operator asked to review/audit the intake insights, deep-dive the valuable ones, and distill into handoffs, then implement the 3 "do-this-first" autopilot patterns.

### Deep-dive docs written (`research/deep-dives/`)
- `2026-07-02-rocm-mi210-vllm-gfx90a.md` — gfx90a support matrix + from-source vLLM build path. Resolves the mi210 progress-log "vLLM MI210 number" open item to a build-and-measure task (prebuilt `rocm6.4.1` image = fast route; from-source current-vLLM @ ROCm 6.2 = fallback; **AITER/MORI/DeepEP exclude gfx90a** → reference-kernel vLLM).
- `2026-07-02-cross-model-lora-transfer-cluster.md` — 8-entry decision matrix. All GPU-training-gated **except Cross-LoRA** (CPU SVD, low fidelity); **Text-to-LoRA** (open weights) = the one CPU-runnable validation.

### Handoffs updated
gpu-acceleration-path, meta-harness-optimization, engram-conditional-memory, tq3-quantization-evaluation, speculative-decoding-mtp-refresh, autopilot-continuous-optimization (+ the `2026-07-02-mi210.md` progress-log append).

### Autopilot patterns implemented — branch `dgm-harness-patterns-2026-07-02`, commit `d820e94f` (epyc-orchestrator)
3 observe-only "do-this-first" patterns from intake-772 (DGM) + intake-753 (harness-evolution):
- **P1** stepping-stone lane — `ParetoArchive.stepping_stones{,_text}` → planner prompt, `AUTOPILOT_STEPPING_STONES`-gated (default on).
- **P4** mechanism-class effectiveness split — `digest.py`, observe-only code>prompt frontier-rate.
- **P3** `STEPPING_STONE_ABLATION_PROTOCOL.md` — segment-level A/B gate for promotion to authoritative.

Isolated in a git worktree; the **live autopilot (PID 517077, main tree) is unaffected** until an operator merge while idle. Verified: py_compile, functional smoke, `test_pareto_archive_tiers.py` 6/6, GitNexus impact LOW on both modified symbols, 3-lens adversarial review (0 blocker/major, 2 minor fixes applied).

### Operator decisions recorded
- `not_applicable` verdicts **CONFIRMED** for intake-755 (AdaJEPA) + intake-756 (NVFP4-Qwen); creative-use notes retained.

### Deferred (next session)
- Autopilot **Pattern 2** (fecundity parent sampling) + **Pattern 5** (token cost axis — MEASUREMENT trust boundary, operator-only); both gated on P1 landing + the P3 ablation.
- **MI210 vLLM head-to-head** (Qwen3-8B, fp16, vLLM-gfx90a vs llama.cpp-HIP) — build-and-measure, operator-scheduled.
- **Text-to-LoRA CPU validation** — gated on orchestrator `--lora` wiring (doc-to-lora Finding 7).
- Merge branch `dgm-harness-patterns-2026-07-02` into the active branch when autopilot is idle.
