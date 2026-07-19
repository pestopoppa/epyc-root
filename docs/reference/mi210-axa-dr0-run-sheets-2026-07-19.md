# MI210 AXA-2 / DR-0 Run Sheets - 2026-07-19

Purpose: turn the current residency and drafter-control notes into executable run sheets so the
next quiet window spends time measuring, not re-designing. These sheets do not ratify `P-GPU-1`
and do not touch production v6.

## Preconditions Shared By Both Gates

- Production v6 stays frozen; candidate execution uses `/mnt/raid0/llm/llama.cpp-experimental`
  at the current v7 promotion branch unless a newer checked tip is recorded.
- MI210 is single-owner for each run. Do not overlap with other GPU jobs.
- Record pre/post `pgrep -af 'llama-bench|llama-server|llama-cli|llama-mtmd-cli'` and
  `rocm-smi --showpids`.
- Pin `LD_LIBRARY_PATH=/mnt/raid0/llm/llama.cpp-experimental/build-hip/bin`.
- Treat results as observation-grade unless `P-GPU-1` is ratified or retro-certifies the exact
  protocol/artifact.

## AXA-2 Teleport V1 Validation

Scope: default-off re-prefill cutover only. The CPU stream begins normally; policy snapshots
`prompt + generated_so_far`, acquires a MI210 lease, sends the full prefix to a GPU lane as a
fresh request, then returns `cpu_prefix + gpu_suffix`. Do not implement spec-dec catch-up in v1.

Implementation seam:

- CPU call path: `epyc-orchestrator/src/llm_primitives/inference.py::_call_caching_backend`
- Backend stream wrapper: `epyc-orchestrator/src/backends/llama_server.py`
- Policy surface: default-off lease helper plus telemetry, not kernel work

Required telemetry:

- `teleport_candidate`
- `gpu_lease_acquired`
- `gpu_prefill_start`
- `gpu_prefill_end`
- `cutover`
- `fallback`
- `lease_released`

Validation experiments:

1. GPU prefill sizing at prefix lengths matching expected cutover prefixes: 2K, 8K, 16K, and 32K
   tokens where the model supports it.
   - 2026-07-19 observation-grade partial: 122B UD-IQ2_M on MI210 completed `pp2048 342.06 t/s`,
     `pp8192 135.56 t/s`, and `pp16384 76.52 t/s` with q4_0/f16 KV on the current HIP build. The
     current build's mixed-KV `pp32768` q4_0/f16 path held VRAM but fell into a no-row / 0% GPU
     CPU-bound fallback, while homogeneous 32K KV controls at the same prefix, b1024/ub256, and t32
     completed cleanly: f16/f16 `489.31 t/s`, q4_0/q4_0 `487.87 t/s`. A read-only code audit found
     `GGML_CUDA_FA_ALL_QUANTS=OFF`, which rejects mixed K/V flash-attn pairs and explains the
     unsupported long-prefix mixed path. An isolated experimental HIP build with
     `GGML_CUDA_FA_ALL_QUANTS=ON` then completed q4_0/f16 `pp32768` at `415.31 t/s` with real MI210
     activity and clean KFD cleanup. Same-window homogeneous controls keep the build choice scoped:
     current default no-warmup f16/f16 and q4_0/q4_0 rows stayed at `489.82`/`489.07 t/s`, while
     the all-quants build measured `416.55`/`414.60 t/s` on those same homogeneous 32K shapes.
     This closes the root-cause question for AXA-2.3: mixed-KV 32K is usable only with the
     all-quants flash-attn build, not the current default HIP build, and `FA_ALL_QUANTS` is a
     mixed-KV lane option rather than a blanket default. Artifacts:
     `data/gpu-mi210/axa2-qwen35-122b-iq2m-prefill-sizing-20260719T060039Z/summary.json` and
     `data/gpu-mi210/axa2-qwen35-122b-iq2m-prefill32k-t32-20260719T062410Z/summary.json` and
     `data/gpu-mi210/axa2_32k_prefill_qwen35_122b_v1_q4k_f16v_b1024_ub256_20260719T064333Z/summary.json` and
     `data/gpu-mi210/axa2_32k_prefill_qwen35_122b_v1_f16kv_b1024_ub256_20260719T065143Z/summary.json` and
     `data/gpu-mi210/axa2_32k_prefill_qwen35_122b_v1_f16k_q4v_b1024_ub256_rerun_20260719T070336Z/summary.json` and
     `data/gpu-mi210/axa2_32k_prefill_qwen35_122b_v1_q4kv_b1024_ub256_20260719T071051Z/summary.json` and
     `data/gpu-mi210/axa2_24k_prefill_qwen35_122b_v1_q4k_f16v_b1024_ub256_20260719T072203Z/summary.json` and
     `data/gpu-mi210/axa2_32k_prefill_qwen35_122b_v1_q4k_f16v_no_warmup_b1024_ub256_20260719T072934Z/summary.json` and
     `data/gpu-mi210/axa2_mixed_kv_fa_matrix_current_build_20260719T073441Z/summary.json` and
     `data/gpu-mi210/axa2_fa_all_quants_mixed_kv_validation_20260719T073906Z/summary.json` and
     `data/gpu-mi210/axa2_fa_all_quants_regression_controls_20260719T074221Z/summary.json` and
     `data/gpu-mi210/axa2_current_build_no_warmup_homogeneous_controls_20260719T074757Z/summary.json`.
     Use `415.31 t/s` as an observation-grade all-quants-build mixed-KV 32K cost only; keep the
     current default HIP build's mixed-KV 32K cost rejected.
2. Cold-load vs page-cache-hot load wall-clock for the intended resident targets.
   - 2026-07-19 observation-grade hot page-cache smoke: 122B UD-IQ2_M MI210 server with
     f16/f16 KV, `c32768`, b1024/ub256, and reasoning disabled reached `/health` in `7052 ms`,
     returned exact `READY` in `315 ms`, and cleaned up with no matching AXA server process or KFD
     PID. Artifact:
     `data/gpu-mi210/axa2_qwen35_122b_hot_load_lease_smoke_20260719T065557Z/summary.json`.
     This is a resident-lane acquisition input, not a cold-load row; do not use it for the cold-load
     break-even branch.
3. One cutover smoke with explicit slot-release proof and no leaked GPU process.
4. Catch-up API probe documented as v1.1 only: current llama-server HTTP has no clean "verify
   these already-generated draft tokens then continue" API.
5. Sampling-continuity divergence test: same prompt, seed 42 production sampling, CPU vs HIP
   build, record first divergent token.

Pass criteria:

- Teleport policy declines when expected remaining-token savings do not beat migration cost.
- When it accepts, the output is structurally coherent and the CPU prefix is preserved exactly.
- GPU lease is released and post-run ROCm shows no KFD PIDs.
- The divergence test records the divergence point; it does not need byte-identical continuation
  unless the policy claims same-model/same-quant continuity.

Open operator decision:

- Mid-stream quant change. Q4 CPU to IQ2 GPU is a model swap even though re-prefill launders KV
  format. Either restrict teleport to IQ2-acceptable tails/roles or require same-quant targets.

### AXA-3 Draft Knobs, Not Active Defaults

These policy knobs are safe to draft but must remain default-off until AXA-2 cost inputs and
`P-GPU-1` status are settled:

```yaml
axa3_teleport_policy:
  enabled: false
  mode: "v1_reprefill_cutover_only"
  long_running_trigger:
    min_generated_tokens: null
    role_allowlist: []
    rate_window_tokens: null
  break_even:
    require_positive_savings: true
    resident_remaining_tokens_estimate: [150, 250]
    cold_load_remaining_tokens_estimate: [350, 500]
    decision_grade: false
  prefill_cost_model:
    model: "qwen35_122b_iq2m"
    kv: "q4_0/f16"
    pp2048_tps: 342.06
    pp8192_tps: 135.56
    pp16384_tps: 76.52
    pp32768_tps: 415.31
    pp32768_status: "mixed_kv_requires_FA_ALL_QUANTS_build"
    f16_f16_pp32768_tps_control: 489.31
    q4_0_q4_0_pp32768_tps_control: 487.87
    current_default_no_warmup_f16_f16_pp32768_tps_control: 489.82
    current_default_no_warmup_q4_0_q4_0_pp32768_tps_control: 489.07
    fa_all_quants_f16_f16_pp32768_tps_control: 416.55
    fa_all_quants_q4_0_q4_0_pp32768_tps_control: 414.60
    fa_all_quants_homogeneous_regression_observed: true
    current_default_build_mixed_kv_pp32768_status: "rejected_cpu_fallback_zero_gpu_no_stdout"
    max_costed_prefix_tokens: 32768
    reject_mixed_kv_32k_cutover_cost: false
    require_fa_all_quants_for_mixed_kv_32k: true
    do_not_enable_fa_all_quants_globally_from_axa2: true
  load_cost_model:
    hot_page_cache_ready_ms_control: 7052
    cold_load_ready_ms: null
    cold_load_status: "operator_protocol_required"
  gpu_lease:
    single_owner_required: true
    require_free_mi210: true
    release_proof_required: true
    workload_weights: null
  quant_policy:
    mid_stream_quant_change: "operator_decision_required"
```

## DR-0 Quant-Asymmetric Self-Spec Run Sheet

Question: can a GPU-resident aggressive same-family artifact act as a drafter for a high-quality
CPU verifier and beat its overhead? Use the DR-1 rule: `E(alpha,K) > F(K)+H(K)`.

Current candidate artifact:

- `/mnt/raid0/llm/models/Qwen3.5-122B-A10B-MTP-GGUF/UD-IQ2_M/Qwen3.5-122B-A10B-UD-IQ2_M.gguf`
- Registry row: `qwen35_122b_iq2m`
- Existing observations:
  - long repeated output: no-spec `37.87 t/s`, native MTP `60.65 t/s`, composed
    `ngram-mod,draft-mtp` `287.09 t/s`
  - mixed 3-prompt slice: no-spec `41.85 t/s`, composed `50.77 t/s`, `3/3` sanity pass
  - broad 8-prompt slice: composed mean `80.77 t/s`, `5/8` pass, not a blanket default

Run arms:

1. CPU high-quant verifier baseline for the selected target task class.
2. MI210 drafter alone, recording draft tokens, accepted draft tokens where available, prompt t/s,
   decode t/s, load wall-clock, and quality sanity.
3. Combined quant-asymmetric path only if the planner can record `F(K)` and `H(K)` separately
   from accepted-token benefit.

Minimum task classes:

- repetitive structured generation
- bounded architect/reviewer JSON decision
- short code-review/no-bug control
- exact-format strict instruction

Pass criteria:

- Quality sanity passes on every included row, not just the repetitive control.
- Acceptance/economics satisfy `E(alpha,K) > F(K)+H(K)` on the selected task class.
- The result is task-class-scoped. A broad default requires a broader pass set; the current
  `5/8` broad result is explicitly insufficient.

Observation vs decision-grade:

- Observation-grade now: repeat the existing task-class probes on the current v7 tip and produce
  a complete `F+H` accounting table.
- Decision-grade later: rerun under a ratified `P-GPU-1` protocol or explicit retro-certification.

## Reporting

Update:

- `handoffs/active/mi210-big-model-and-acceleration-roadmap.md`
- `handoffs/active/gpu-drafter-control-redesign.md`
- `handoffs/active/inference-acceleration-index.md`

Record artifact directories, source commit, model paths, exact commands, pre/post process state,
ROCm cleanup proof, and whether the claim is observation-grade or decision-grade.
