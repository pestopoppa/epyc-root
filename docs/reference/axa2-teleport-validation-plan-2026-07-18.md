# AXA-2 Teleport Validation Plan - 2026-07-18

**Status**: no-inference design + validation plan. This document records the
decision surface only; it does not execute commands, touch production v6, or make
new measurement claims.

## Thesis

AXA-2 should make long CPU turns movable to the MI210 without KV/state migration.
The v1 mechanism is **re-prefill teleport**: take the original prompt plus
generated-so-far, run one GPU prefill, then continue decode on the GPU. Optional
catch-up keeps the CPU decoding while the GPU prefills, then replays
tokens-since-snapshot as same-model draft tokens for one batched verify step.

This intentionally sidesteps composed-spec state save/restore
(`common/speculative.cpp:3063`) and any cross-build KV format coupling. It does
not sidestep quality: Q4-CPU to IQ2-GPU is a mid-stream model/quant change, even
though re-prefill launders state format.

The current prep seam is the orchestrator policy path
`src/llm_primitives/primitives.py::evaluate_teleport_decision`, with
`src/llm_primitives/teleport.py` carrying the decision rules,
`src/gpu_lease.py` carrying single-owner cutover state, and
`src/backends/llama_server.py` carrying the transport/backend wrapper.

## What AXA-2 Must Prove

1. **Economic win**: migration saves wall-clock time for long-running turns after
   load, re-prefill, catch-up, scheduler, and admission overhead.
2. **Continuity bound**: same seed and production sampling do not diverge earlier
   than an operator-acceptable threshold, or the policy restricts teleport to
   roles where divergence is acceptable.
3. **Quality policy**: mid-stream quant changes are either explicitly allowed for
   selected tails/roles, or teleport is same-quant-only.
4. **Single-card safety**: teleport admission respects the MI210 single-owner
   lane and never evicts higher-priority residency/reviewer work without policy.
5. **Artifact completeness**: every decision row carries enough protocol data to
   become decision-grade if `P-GPU-1` is ratified or rerun under it.

## Validation Matrix

| Gate | Question | Method | Required artifact fields | Pass rule |
|---|---|---|---|---|
| V0 design smoke | Can teleport be modeled without KV migration? | Dry-run orchestration trace only | role, prompt tokens, generated tokens, CPU t/s, candidate GPU target, policy decision | Produces deterministic `stay`/`teleport` decision with no server action. |
| V1 prefill cost | What is `reprefill(P+N)` on MI210? | Placeholder GPU prefill sweep at representative `P+N` sizes | model, quant, context, prompt tokens, prefill t/s, wall-clock, commit, ROCm state | Median cost supports break-even below. |
| V2 load cost | What are cold and page-cache-hot load costs? | Placeholder load timing with no decode | model path, file size, cold/hot label, wall-clock, page-cache state, VRAM before/after | Resident and cold-load policies have separate thresholds. |
| V3 catch-up | Does CPU catch-up replay verify cheaply? | Placeholder same-model draft replay test | snapshot token, catch-up token count, accepted/verified counts, stall time | Same-model replay acceptance approximately 1.0 and stall less than no-catch-up pause. |
| V4 continuity | How soon do CPU and HIP streams diverge? | Placeholder seeded CPU-vs-GPU sampling comparison | prompt hash, seed, sampler params, model/quant pair, divergence token, output hashes | Divergence is within declared policy, or teleport restricted. |
| V5 end-to-end | Does policy win on real long turns? | Placeholder replay harness on captured non-sensitive traces | trace id, predicted remaining tokens, actual remaining tokens, baseline wall, teleported wall, cleanup proof | Positive median wall-clock delta with no cleanup leak. |

## Break-Even Assumptions

Decision inequality:

```text
expected_remaining_tokens * (1 / cpu_tps - 1 / gpu_tps)
  > load_cost + reprefill_cost(P + generated_so_far) + catchup_cost + scheduler_overhead
```

Initial planning thresholds from the MI210 roadmap remain hypotheses until
validated:

- **Resident GPU target**: likely break-even around `150-250` remaining tokens.
- **Cold load from RAID0**: likely break-even around `350-500` remaining tokens
  if load is `5-9s`.
- **No teleport** when GPU is occupied by a higher-priority lease, the target is
  not resident and expected tail is short, or quant policy disallows the swap.
- **Same-model catch-up** may reduce visible stall but must still be charged in
  the inequality.

## Risk List

- **Quant discontinuity**: Q4 CPU to IQ2 GPU may alter continuation quality.
- **Sampling divergence**: CPU and HIP sampling may diverge even with the same
  prompt, seed, and sampler settings.
- **Tail prediction error**: the turn may end before migration amortizes.
- **GPU contention**: teleport can steal the single MI210 from AXA-1 residency,
  reviewer experiments, or admission-smoke lanes.
- **Load-state ambiguity**: page-cache-hot and cold-load timings imply different
  policy thresholds.
- **Artifact under-specification**: pre-`P-GPU-1` rows may lack clocks, power,
  temp, or cleanup fields needed for decision-grade claims.
- **Implementation temptation**: slot-state teleport and composed-spec
  save/restore are larger mechanisms and should not be bundled into v1.

## Artifact Schema

Each validation run should emit one directory with:

```text
summary.json
commands.placeholder.sh
policy_decision.json
environment.json
cleanup.txt
```

Minimum `summary.json` fields:

```json
{
  "protocol_id": "P-GPU-1-or-observation",
  "date": "YYYY-MM-DD",
  "artifact_kind": "axa2_teleport_validation",
  "llama_cpp_tree": "experimental-v7 path/commit, never production-v6",
  "model_cpu": {"path": "", "quant": "", "context": 0},
  "model_gpu": {"path": "", "quant": "", "context": 0},
  "sampling": {"seed": 42, "params": {}},
  "teleport_policy": {
    "role": "",
    "prompt_tokens": 0,
    "generated_so_far": 0,
    "expected_remaining_tokens": 0,
    "gpu_resident": false,
    "decision": "stay|teleport|blocked"
  },
  "costs": {
    "cpu_tps": null,
    "gpu_tps": null,
    "load_seconds": null,
    "reprefill_seconds": null,
    "catchup_seconds": null,
    "scheduler_overhead_seconds": null
  },
  "continuity": {
    "divergence_token": null,
    "cpu_output_hash": "",
    "gpu_output_hash": ""
  },
  "spec_catchup": {
    "draft_tokens": null,
    "accepted_tokens": null,
    "acceptance_rate": null
  },
  "cleanup": {
    "kfd_pids_after": [],
    "vram_used_after_mb": null
  },
  "verdict": "pass|fail|inconclusive"
}
```

## Placeholder Commands

Do not execute from this plan. Replace paths, ports, commits, and protocol flags
only inside an operator-approved validation window.

```bash
# Dry policy trace, no server action. This helper lives in epyc-orchestrator
# and evaluates the real TeleportPolicy code path without acquiring a lease.
cd /mnt/raid0/llm/epyc-orchestrator
python3 scripts/benchmark/axa2_teleport_policy_trace.py \
  --trace <captured-trace.jsonl> \
  --cpu-tps <cpu_tps> \
  --gpu-tps <gpu_tps> \
  --load-seconds <load_seconds> \
  --output <artifact-dir>

# Dry live-cutover bundle, no server action. This writes the operator command
# and required artifact checklist for a same-quant resident cutover smoke.
python3 scripts/benchmark/axa2_live_cutover_bundle.py \
  --output orchestration/reports/axa2_live_cutover_bundle_<date> \
  --policy-enabled \
  --role-allowlist architect_general \
  --cpu-quant q4_k_m \
  --gpu-quant q4_k_m \
  --generated-tokens 200 \
  --estimated-remaining-tokens 500 \
  --cpu-tps 20 \
  --gpu-tps 44

# Operator-window only: execute the prepared live-cutover bundle against
# already-running CPU/GPU llama-server endpoints. This still does not start
# servers, build kernels, restart AutoPilot, or touch production v6.
CPU_URL=http://127.0.0.1:<cpu-port> \
GPU_URL=http://127.0.0.1:<gpu-port> \
  orchestration/reports/axa2_live_cutover_bundle_<date>/operator_run.sh

# Placeholder only: GPU prefill sweep under experimental v7, never production v6.
python scripts/benchmark/axa2_prefill_sweep.py \
  --llama-bin /mnt/raid0/llm/llama.cpp-experimental/build/bin/llama-bench \
  --model <gpu-model.gguf> \
  --prompt-sizes 2048,8192,16384,32768 \
  --output <artifact-dir>

# Placeholder only: CPU-vs-HIP seeded sampling continuity.
python scripts/benchmark/axa2_sampling_continuity.py \
  --cpu-server <cpu-server-url> \
  --gpu-server <gpu-server-url> \
  --seed 42 \
  --sampler-profile production \
  --output <artifact-dir>
```

2026-07-19 sample dry trace artifact:
`/mnt/raid0/llm/epyc-orchestrator/orchestration/reports/axa2_policy_trace_20260719/`.
It contains two no-inference policy rows: a same-quant resident-tail cutover
candidate and a default cross-quant rejection (`quant_change_not_allowed`).

2026-07-19 sample live-cutover dry bundle:
`/mnt/raid0/llm/epyc-orchestrator/orchestration/reports/axa2_live_cutover_bundle_20260719/`.
It contains the no-inference operator command plus the artifact checklist for
cutover, lease-release, and seeded CPU-vs-GPU continuity evidence.

## Gate Dependencies

- `P-GPU-1` ratified, or rows stay observation-grade.
- v7 promotion readiness remains operator-gated; production v6 is frozen and must
  not be modified, built, or used as the teleport implementation target.
- AXA-1 residency quality is the prerequisite confidence signal for IQ2 tails,
  but not a blanket approval for mid-stream quant swaps.
- Operator decision required: Q4-CPU to IQ2-GPU teleport allowed for selected
  roles/tails, or same-quant-only.
- Orchestrator policy hooks required before serving work: long-running signal,
  expected-tail estimator, GPU lease/admission check, and break-even threshold.
- AXA-3/AP-2 should only register runtime knobs after AXA-2 validation lands.
