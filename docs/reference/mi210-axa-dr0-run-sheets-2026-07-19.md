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
2. Cold-load vs page-cache-hot load wall-clock for the intended resident targets.
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
