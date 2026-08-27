# Lightning Attention Port to llama.cpp

**Status**: COMPACTED 2026-05-28 - v1 Ring-mini port complete; active only for production-suitability decisions.
**Created**: 2026-04-29
**Updated**: 2026-07-26
**Priority**: MEDIUM
**Categories**: ssm_hybrid, context_extension, kv_cache, training_distillation, inference_serving
**Workstream**: Inference Acceleration + CPU Engineering
**Parent index**: [inference-research-index.md](inference-research-index.md)
**Completed ledger**: [lightning-attention-port-v1-completed-through-2026-05-28.md](../completed/lightning-attention-port-v1-completed-through-2026-05-28.md)

## 2026-07-26 Staleness Review

The [design-backlog triage](design-backlog-triage-2026-07-23.md) preserves the
dedicated-op path as profile-gated and leaves the production-role decision
open. No new role or profile evidence was produced by this review, so LQ-1
through LQ-4 remain correctly gated.

## Executor Start Here

Do not restart the Lightning Attention port. The historical ledger preserves the full implementation, benchmark, and quality notes. Current work is to decide whether Ring-mini-linear-2.0 has a live production role and to run only the validation slice needed for that decision.

| Current question | Executor rule |
|---|---|
| Is L1-L4 still open? | No. Treat the v1 llama.cpp port as complete unless the branch no longer builds or the model no longer loads. |
| Should L5 get implemented? | No by default. Dedicated `GGML_OP_LIGHTNING_ATTN` work is profile-gated and only justified if traces show constant-`g` materialization or head-thread underutilization as a material bottleneck. |
| Can Ring-mini draft Qwen3-Coder? | No. The F1 drafter check found tokenizer mismatch and impossible throughput math for that target. |
| What is the likely useful role? | Q-scorer/routing classifier, AIME-style direct-answer math specialist, same-family Ring-flash drafter if Ring-flash appears, or parked architecture reference. |

## Outstanding Tasks

- [x] **LQ-1 role decision**: **parked architecture reference** (owner: Inference
  Acceleration / this handoff) ✅ 2026-07-29. This is a production-role decision,
  not a claim that the port or model is broken. The Q4 artifact remains on disk and
  current v8 production/experimental sources retain the `bailingmoe` architecture,
  but it is Tier C, cold, and unpinned; no active stack configuration selects it.
  The last complete quality review is historical (2026-05-04) and scored 59/90
  (65.6%), with 7 empty responses and a regression when the output budget was
  enlarged. The Qwen drafter route is already a hard no-go (different tokenizer
  and impossible acceptance/throughput math); neither a current q-scorer/routing
  comparison nor a compatible Ring-flash target exists. Do not assign it a live
  role from the AIME spot check or old review alone. Reopen only with (a) a
  specified same-tokenizer Ring-flash candidate, or (b) an owned, current-era
  q-scorer/routing A/B against the incumbent; either condition then starts LQ-2
  or LQ-3 respectively.
- [ ] **LQ-2 broader quality eval**: if keeping a math/reasoning role, run a focused AIME/MATH/GPQA-style bundle with `reasoning_budget=0`, exact prompt templates, and explicit safety exclusions.
- [ ] **LQ-3 Ring-flash drafter check**: only if a compatible Ring-flash target is available. Measure acceptance-adjusted throughput; raw Ring-mini t/s is not enough.
- [ ] **LQ-4 profile-gated L5 decision**: only profile after LQ-1/2/3 gives a reason to keep the model. Promote a dedicated op only when the profile proves a material bottleneck.

## Dependency Forks

| Outcome | Next action |
|---|---|
| Quality pass + useful live role | Keep active, schedule the narrow follow-up validation for that role, and update the relevant domain index. |
| Quality pass but no production role | Park as architecture reference; keep the completed ledger as the durable implementation record. |
| Quality fail or safety/agentic regression remains material | Close as negative/limited-use after preserving the result; do not spend L5 effort. |
| Branch or model load regresses | Reopen only the minimum build/load fix, then rerun the smallest sanity benchmark before any quality claim. |

## Completed Scope

| Scope | Result | Ledger |
|---|---|---|
| L1-L4 v1 llama.cpp port | Complete. Ring-mini Q4_K_M reached coherent decode at 40.68 t/s on commit `33b60b925`. | [completed ledger](../completed/lightning-attention-port-v1-completed-through-2026-05-28.md) |
| F1 drafter compatibility | NO-GO for Qwen3-Coder target due to tokenizer mismatch and throughput math. | [completed ledger](../completed/lightning-attention-port-v1-completed-through-2026-05-28.md) |
| F2 long-context smoke | PASS at 32K with stable prefill/decode; representative results include pp512 858.4, tg128 44.3, pp1024+tg128 283.6, pp8192+tg128 661.7, pp32768+tg128 560.2. | [completed ledger](../completed/lightning-attention-port-v1-completed-through-2026-05-28.md) |
| F3 AIME sentinel | AIME 2025 #1 returned correct answer `70`. | [completed ledger](../completed/lightning-attention-port-v1-completed-through-2026-05-28.md) |
| L4+ quality eval | `reasoning_budget=0` fix produced 67/90 total, 23/30 pass, 0 empties; agentic and safety regressions remain. | [completed ledger](../completed/lightning-attention-port-v1-completed-through-2026-05-28.md) |

## Key Files

- `/mnt/raid0/llm/llama.cpp` or the relevant experimental fork containing `LLM_ARCH_BAILINGMOE_LINEAR`
- `/mnt/raid0/llm/epyc-inference-research/` for model/eval artifacts
- [log-linear-gated-deltanet-readiness.md](log-linear-gated-deltanet-readiness.md)
- [multiscreen-attention-evaluation.md](multiscreen-attention-evaluation.md)
- [qwen36-27b-cpu-feasibility.md](qwen36-27b-cpu-feasibility.md)
- [llama-cpp-dsa-contribution.md](llama-cpp-dsa-contribution.md)
- `research/deep-dives/ling-linear-lightning-attention-hybrid.md`

## Reporting Instructions

After any LQ task, update this active handoff with the command, model artifact, exact prompt/eval set, result, and the role decision. If a task resolves the remaining production decision, update [inference-research-index.md](inference-research-index.md) and [master-handoff-index.md](master-handoff-index.md).

## Research Intake Update — 2026-08-22 (Stage-2b, intake-1287#record MiniCPM-SALA)

A second architecture now lands on this handoff's GLA path. **MiniCPM-SALA** is a 9B hybrid in which
25 % of layers (8 of 32, at indices 0, 9, 16, 17, 22, 29, 30, 31 — clustered, not strided) do
InfLLM-V2 block-sparse **exact** attention at 2 KV heads, and the other 24 are linear. Licence
Apache-2.0; released checkpoint, revision `9180fe1d`. Compute classes below: **Z** zero-compute,
**G** compute-gated, **B** blocked-on.

**Read the artifact, not the prose — the paper is wrong about its own linear half.** It says
"Lightning Attention" throughout and cites Qin et al. 2024. The released code calls
`fla.ops.simple_gla` (`chunk_simple_gla` / `fused_recurrent_simple_gla`) with `g_gamma` from
`_build_slope_tensor()` (`modeling_minicpm_sala.py:2045-2066`) — the parameter-free ALiBi power-of-2
slope schedule, i.e. **constant-decay Simple GLA without the layer-scaled decay that distinguishes
MiniMax's Lightning Attention**. Three independent implementers read it the same way (vllm #44095,
vllm #48999, sglang #30360). Reattribute to Simple GLA when citing the *mechanism*; keep "Lightning
Attention" only when quoting the paper. **This helps us** — constant-decay GLA is exactly what
`GGML_OP_GATED_LINEAR_ATTN` already implements. The paper is also contradicted by its own checkpoint
on QK-Norm: §2.1 claims it on "all attention layers (both sparse and linear)", and the checkpoint has
q_norm/k_norm on the 24 linear layers only (intake-1287#record).

### A correctness-first port needs ZERO new ggml operators (Z — recorded)

The opposite of the LTE finding. Read read-only from the frozen tree at `0db32c06e3e5`, 2026-08-23:

| Primitive SALA needs | Where it already is |
|---|---|
| Constant-decay gated linear attention | `GGML_OP_GATED_LINEAR_ATTN` at `ggml/include/ggml.h:569`; API `ggml_gated_linear_attn()` at `:2532`; SIMD-vectorised CPU f32 forward `ggml_compute_forward_gla_f32` at `ggml/src/ggml-cpu/ops.cpp:10556`; CUDA kernel `ggml/src/ggml-cuda/gla.cu`, which hipifies for gfx90a via the `../ggml-cuda/*.cu` glob |
| Per-layer recurrent/attention hybrid memory | `src/llama-memory-hybrid.cpp`, `hparams.is_recr_impl` (`src/llama-hparams.h:153`); in-tree precedent `src/models/kimi-linear.cpp` and `src/models/qwen3next.cpp` |
| NoPE, QK-norm, attention output gates | All expressible today |
| InfLLM-V2 block-sparse top-k selection | **The only missing primitive — and the reference does not need it either.** `modeling_minicpm_sala.py:2447-2454` instantiates ordinary eager/sdpa **dense** attention for the sparse layers whenever `torch.cuda.is_available()` is False. A dense-fallback GGUF port is numerically correct and gives up only the sparse-prefill speedup, exactly as the vendor's own CPU path does |

**Closest existing template for the linear half: upstream llama.cpp PR #27018**
(`LLM_ARCH_MINIMAX_01`, lightning-attention decay slopes on hybrid recurrent memory), **merged
2026-08-14 — four days after our v9 freeze point `0db32c06e3e5` (committed 2026-08-10T21:54:03Z)**. It
is therefore post-v9 and absent from our tree, which carries `LLM_ARCH_MINIMAX_M2` but not `_01`. It
is now a row in the monitoring table in
[log-linear-gated-deltanet-readiness.md](log-linear-gated-deltanet-readiness.md); read it there before
writing any new arch handler.

### Tasks

- [ ] **Z9 (Z, prerequisite for G18) — write the ~30-line pure-PyTorch constant-decay simple-GLA
      recurrence** to stand in for the `fla` Triton call, **so that an HF CPU numerical oracle exists
      at all**. Today there is none: `fla.ops.simple_gla` is Triton, Triton needs a GPU stack this host
      does not have for gfx90a (see `G6` in
      [rocm-verify-profile-backend.md](rocm-verify-profile-backend.md)), and without an oracle G18 has
      nothing to compare a GGUF against. Constant decay makes this small — the decay is a
      parameter-free ALiBi slope from head count, not a learned tensor. **No inference, no GPU, no
      process management: this is code to write, and it is executable now.**
- [ ] **G18 (G, prerequisite `Z9`) — SALA correctness-first port + CPU parity smoke.** On
      `llama.cpp-experimental` branched from the current production tip (**never v9**). Greedy
      (`temp 0`, fixed seed), **3 prompts × 32 tokens, every prompt under `sparse_config.dense_len` =
      8192** so both sides run the sparse layers dense and the comparison is not confounded by the one
      primitive we do not have. GGUF output vs the `Z9` HF CPU oracle.
      **Gate:** **token-identical output on all 3 prompts.** Anything less is not a parity result and
      must not be reported as one.
      **Owner:** this handoff. Both compute planes were held by other sessions through this wave —
      **filed, not run.**
- [ ] **B8 (B, blocked on `G18`) — the three things that all presuppose numerical correctness.**
      None may start before G18 passes; each is listed with the handoff that would own it if it does.
      **(a) Throughput.** Decode and prefill t/s for SALA Q4_K_M on EPYC at 4K / 32K / 128K against the
      production frontdoor, and on MI210 HIP. Owner if opened:
      [multiscreen-attention-evaluation.md](multiscreen-attention-evaluation.md).
      **(b) NoLiMa adjudication.** The paper's Table 3 reports 128K = 23.86; an unmerged NoLiMa
      leaderboard PR submitted by an account whose handle matches a SALA co-author reports **40.9** for
      the same model on the same benchmark, and lists an *effective length of 4K* for a model marketed
      at 1M. Neither source ships raw files, so this is only resolvable by running it. Owner if opened:
      [eval-tower-verification.md](eval-tower-verification.md).
      **(c) An InfLLM-V2 block-sparse ggml op.** **Justified only if (a) shows the dense fallback makes
      prefill the binding constraint above ~32K.** Owner if opened: this handoff. Note the standing
      decline on porting `infllmv2_cuda_impl` to HIP — sm80 CUDA only, zero hip/rocm hits, and upstream
      llama.cpp closed the SALA support request `not_planned`; **re-surface only if SGLang PR #30360's
      AMD ROCm CI leg goes green**, which is the leading indicator for this hardware.
      Adopting SALA as a production model is a separate standing **decline**: 9B dense against our
      35B-A3B, no evidence it wins on any axis we serve, and no reproduced number from anyone in six
      months.
