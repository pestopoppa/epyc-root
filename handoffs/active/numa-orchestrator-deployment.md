# Handoff: NUMA-Aware Orchestrator Deployment

**Status**: DEPLOYED (2026-03-19). NUMA-pinned launching live in orchestrator_stack.py. Model swaps executed.
**Created**: 2026-03-18
**Priority**: CRITICAL — 6.7x throughput on frontdoor model with zero code changes
**Blocks**: None
**Blocked by**: None
**Related**: [`inference-acceleration-index.md`](inference-acceleration-index.md), [`ssm-hybrid-acceleration.md`](ssm-hybrid-acceleration.md), [`tree-speculation-numa-drafting.md`](tree-speculation-numa-drafting.md)

## Summary

Session 2026-03-18d discovered that NUMA-aware CPU pinning gives **6-7x aggregate throughput** on models ≤65GB by running 4 independent instances on NUMA quarters. This is a config-only change — the existing production binary (`production-consolidated-v2`, build 8214) already has all necessary features.

## What To Deploy

### Production Binary

**No new build required.** Use the existing binary:
```
/mnt/raid0/llm/llama.cpp/build/bin/llama-server
Version: 8214 (7acee0d64) on branch production-consolidated-v2
Features: tree speculation, freeze-recurrent, HSD, DySpec
```

### NUMA Topology (EPYC 9655)

```
Node 0: cores 0-47, HT 96-143   (~566 GB RAM)
Node 1: cores 48-95, HT 144-191 (~566 GB RAM)

Quarter splits:
  Q0A: cores 0-23, HT 96-119
  Q0B: cores 24-47, HT 120-143
  Q1A: cores 48-71, HT 144-167
  Q1B: cores 72-95, HT 168-191
```

**Container limitation**: `numactl --membind` is blocked. Use `taskset -c` for CPU pinning. Memory follows first-touch policy (model weights allocated on the NUMA node of the loading threads).

### Per-Model Launch Configuration

#### Frontdoor: Qwen3.5-35B-A3B Q4_K_M (20 GB) — **4 instances, NUMA quarters, moe6+lookup**

```bash
# Instance 1 (NUMA quarter 0A)
taskset -c 0-23,96-119 /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/unsloth/Qwen3.5-35B-A3B-GGUF/Qwen3.5-35B-A3B-Q4_K_M.gguf \
  --override-kv qwen3moe.expert_used_count=int:6 --lookup \
  -t 48 -np 1 --port 8080 -ngl 0 --mlock

# Instance 2 (NUMA quarter 0B)
taskset -c 24-47,120-143 /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/unsloth/Qwen3.5-35B-A3B-GGUF/Qwen3.5-35B-A3B-Q4_K_M.gguf \
  --override-kv qwen3moe.expert_used_count=int:6 --lookup \
  -t 48 -np 1 --port 8081 -ngl 0 --mlock

# Instance 3 (NUMA quarter 1A)
taskset -c 48-71,144-167 /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/unsloth/Qwen3.5-35B-A3B-GGUF/Qwen3.5-35B-A3B-Q4_K_M.gguf \
  --override-kv qwen3moe.expert_used_count=int:6 --lookup \
  -t 48 -np 1 --port 8082 -ngl 0 --mlock

# Instance 4 (NUMA quarter 1B)
taskset -c 72-95,168-191 /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/unsloth/Qwen3.5-35B-A3B-GGUF/Qwen3.5-35B-A3B-Q4_K_M.gguf \
  --override-kv qwen3moe.expert_used_count=int:6 --lookup \
  -t 48 -np 1 --port 8083 -ngl 0 --mlock
```

**Benchmark**: ~19.6 t/s per instance with moe6+lookup, ~78 t/s aggregate (4 instances)
**Routing**: Round-robin across ports 8080-8083 (NOT YET IMPLEMENTED — needs src/ changes)
**Note**: Swapped from Qwen3-Coder-30B-A3B (2026-03-19). No AR drafter — speculation is net-negative on Qwen3.5 hybrids (S3 result). mlock enabled for stable latency.

#### Coder Escalation: Qwen2.5-Coder-32B Q4_K_M (18.5 GB) — **4 instances, spec+tree+lookup**

```bash
# Same pattern as frontdoor, 4 instances on quarters
# Each instance: 48 threads, ports 8084-8087
taskset -c 0-23,96-119 /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/bartowski/Qwen2.5-Coder-32B-Instruct-GGUF/Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf \
  -md /mnt/raid0/llm/models/Qwen2.5-0.5B-Instruct-f16.gguf \
  --draft-max 32 --draft-p-split 0.05 --kv-unified --lookup \
  -t 48 -np 1 --port 8084 -ngl 0 --mlock
# ... repeat for ports 8085-8087 on other quarters
```

**Benchmark**: ~43.3 t/s aggregate (10.8 t/s × 4 instances)
**Note**: Q4_K_M confirmed optimal (2026-03-24) — f16 offers zero quality gain at 41% speed loss and 3.5x RAM. 4 copies = 74 GB total (was 260 GB with f16).

#### Architect General: Qwen3.5-122B-A10B Q4_K_M (69 GB) — **1 instance, node 0, moe8+spec+lookup**

```bash
taskset -c 0-47,96-143 /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/unsloth/Qwen3.5-122B-A10B-GGUF/Q4_K_M/Qwen3.5-122B-A10B-Q4_K_M-00001-of-00003.gguf \
  -md /mnt/raid0/llm/lmstudio/models/unsloth/Qwen3.5-0.8B-GGUF/Qwen3.5-0.8B-Q8_0.gguf \
  --draft-max 8 --kv-unified --lookup \
  --override-kv qwen3moe.expert_used_count=int:8 \
  -t 96 -np 1 --port 8088 -ngl 0
```

**Benchmark**: 12.6 t/s with moe8+spec_q8_k8+lookup (best accel config from sweep)
**Note**: Swapped from Qwen3-235B-A22B (2026-03-19). Saves **64 GB RAM** (69 GB vs 133 GB). Quality +0.75 (2.57 vs 1.82), speed -1.1 t/s vs old best accel. Strong agent/tool-use improvement (TAU2 +21pp).

#### Architect Coding: Qwen3-Coder-480B-A35B Q4_K_M (250 GB) — **1 instance, node 0, tree, 1.41x**

```bash
taskset -c 0-47,96-143 /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/lmstudio-community/Qwen3-Coder-480B-A35B-Instruct-GGUF/Qwen3-Coder-480B-A35B-Instruct-Q4_K_M-00001-of-00008.gguf \
  -md /mnt/raid0/llm/models/Qwen3-Coder-Instruct-DRAFT-0.75B-32k-Q4_0.gguf \
  --draft-max 48 --draft-p-split 0.05 --kv-unified \
  -t 96 -np 1 --port 8089 -ngl 0
```

**Benchmark**: 3.82 t/s vs 2.71 t/s at 192t (1.41x). Tree speculation adds +9% on top of NUMA pinning.
**Note**: Single instance only (250 GB spans both NUMA nodes). `--draft-p-split 0.05` enables tree speculation.

#### Ingest Long Context: Qwen3-Next-80B-A3B Q4_K_M (46 GB) — **2 instances, ~2x aggregate**

```bash
# Instance 1 (node 0)
taskset -c 0-47,96-143 /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/lmstudio-community/Qwen3-Next-80B-A3B-Instruct-GGUF/Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf \
  -t 96 -np 1 --port 8090 -ngl 0

# Instance 2 (node 1)
taskset -c 48-95,144-191 /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/lmstudio-community/Qwen3-Next-80B-A3B-Instruct-GGUF/Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf \
  -t 96 -np 1 --port 8091 -ngl 0
```

**Benchmark**: ~12 t/s per instance, ~24 t/s aggregate
**Note**: No drafter — speculation is net-negative on hybrid models. 46 GB fits on one node.

## What Was Actually Deployed (2026-03-19)

### Model Swaps Executed

| Role | Previous Model | New Model | Rationale |
|------|---------------|-----------|-----------|
| frontdoor | Qwen3-Coder-30B-A3B Q4_K_M (16 GB) | **Qwen3.5-35B-A3B Q4_K_M** (20 GB) | +19pp quality (2.48 vs 1.90), moe6+lookup gives ~19.6 t/s per instance |
| architect_general | Qwen3-235B-A22B Q4_K_M (133 GB) | **Qwen3.5-122B-A10B Q4_K_M** (69 GB) | +25pp quality (2.57 vs 1.82), saves 64 GB RAM, 12.6 t/s with moe8+spec+lookup |

### NUMA Configuration Deployed

- **orchestrator_stack.py** updated to use `taskset -c` CPU pinning (not numactl)
- **frontdoor**: 4x48t NUMA quarters (ports 8080-8083), moe6+lookup, mlock enabled, ~19.6 t/s/instance
- **coder_escalation**: 4x48t NUMA quarters (ports 8084-8087), **Qwen2.5-Coder-32B Q4_K_M** (was f16, changed 2026-03-24 — same quality, 1.7x faster, 3.5x less RAM)
- **architect_general**: 1x96t node0 (port 8088), Qwen3.5-122B-A10B, moe8+spec_q8_k8+lookup, 12.6 t/s
- **architect_coding**: 1x96t node0 (port 8089), unchanged model (480B), tree speculation dm=48
- **ingest**: 1x96t node0 (port 8090), unchanged model (80B SSM), mlock enabled

### Total Model Footprint

~515 GB with multi-instance copies (4×20 GB frontdoor + 4×18.5 GB coder + 69 GB architect + 250 GB coding + 46 GB ingest + misc). Reduced from ~701 GB after coder quant decision (f16→Q4KM saves 186 GB).

### Remaining Work Items (deployment record — see also updated list below)

1. **Round-robin routing** — multi-instance models need round-robin request distribution. Requires `src/` changes. Currently only first instance receives traffic.
2. **Benchmark validation of 35B on NUMA 4-way** — verify moe6+lookup under NUMA 4-way.
3. ~~**Worker NUMA configs**~~ — DONE (2026-03-21): worker_explore pinned to Q0A with spec_overrides.
4. ~~**model_registry.yaml NUMA fields**~~ — Superseded: spec_overrides in orchestrator_stack.py handles NUMA-specific params.

## Orchestrator Changes Required

### 1. `orchestrator_stack.py` — NUMA-Aware Launch

Modify the server launch logic in `epyc-orchestrator/scripts/server/orchestrator_stack.py` to:

1. **Read NUMA config from model registry** — new field `numa_config` per model
2. **Launch with `taskset`** — prepend `taskset -c <cpu_list>` to the server command
3. **Launch multiple instances** for models with `numa_instances > 1`
4. **Assign ports sequentially** — each instance gets a unique port

### 2. `model_registry.yaml` — Add NUMA Fields

Add to each model's config in `epyc-orchestrator/orchestration/model_registry.yaml`:

```yaml
frontdoor:
  model: Qwen3.5-35B-A3B-Q4_K_M
  acceleration: moe6+lookup
  mlock: true
  # NUMA fields:
  numa_instances: 4
  numa_threads_per_instance: 48
  numa_cpu_lists:
    - "0-23,96-119"
    - "24-47,120-143"
    - "48-71,144-167"
    - "72-95,168-191"

architect_general:
  model: Qwen3.5-122B-A10B-Q4_K_M
  acceleration: moe8+spec_q8_k8+lookup
  draft_max: 8
  numa_instances: 1
  numa_threads_per_instance: 96
  numa_cpu_lists:
    - "0-47,96-143"

architect_coding:
  model: Qwen3-Coder-480B-A35B-Instruct-Q4_K_M
  draft_max: 48
  draft_p_split: 0.05  # tree speculation
  numa_instances: 1
  numa_threads_per_instance: 96
  numa_cpu_lists:
    - "0-47,96-143"
```

### 3. Request Routing — Round-Robin for Multi-Instance Models

For models with `numa_instances > 1`, the orchestrator must:
1. Track which ports belong to each model role
2. Route incoming requests round-robin across ports
3. Optionally: route to the instance with the shortest queue (least-loaded)

Simple implementation: maintain a per-role atomic counter, `port = ports[counter++ % n_instances]`.

## Host Setup: memlock for --mlock

The devcontainer has `--ulimit memlock=-1:-1` (unlimited), but the **host** defaults to 64 KB. If launching orchestrator_stack.py from the host, `--mlock` will fail silently.

**Fix (one-time, requires re-login):**
```bash
echo "daniele - memlock unlimited" | sudo tee -a /etc/security/limits.conf
# Then log out and back in, or: sudo su - daniele
```

Verify: `ulimit -l` should show `unlimited`.

All HOT-tier models should use `--mlock` (total ~775 GB locked, 355 GB remaining for KV caches + OS). This prevents the 30x cold-start penalty measured in S2.

## What NOT To Do

1. **Don't use `numactl --membind`** — blocked in container. `taskset` + first-touch is sufficient.
2. **Don't add speculation to hybrid models** (Qwen3.5-*) — S3 proved all draft configs are net-negative on NUMA 4-way. The drafter competes for NUMA quarter bandwidth.
3. **Don't run 192 threads on any model** — always worse than NUMA-pinned configs.
4. **Don't pipeline prefill** (S5) — ceiling is ~8%, not worth the C++ complexity.
5. **Don't merge `feature/dflash-speculation`** — DFlash NOT viable on Q4_K_M (27% per-token, 1.4% block).
6. **Don't omit `--draft-p-split 0`** for linear speculation — production binary defaults `p_split=0.1` (tree ON). Silent tree activation causes `kv_unified=true`, `n_seq_max=9`, and draft truncation overhead.

## Verification Checklist

After deployment, verify each model:

```bash
# Health check all instances
for port in 8080 8081 8082 8083 8084 8085 8086 8087 8088 8089 8090 8091; do
  echo -n "Port $port: "
  curl -s http://localhost:$port/health | jq -r '.status'
done

# Quick throughput test (frontdoor, expect ~24 t/s per instance)
curl -s http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"test","messages":[{"role":"user","content":"Hello"}],"max_tokens":64,"temperature":0}' \
  | jq '.timings.predicted_per_second'
```

## Expected Production Throughput (Aggregate) — Sweep-Verified 2026-03-21

All spec decode params verified by comprehensive sweep (`bench_all_spec_sweeps.sh`, 1,290 measurements).

| Role | Model | NUMA Config | Accel | dm | ps | Per-Instance t/s | Aggregate t/s |
|------|-------|-------------|-------|----|----|-----------------|---------------|
| frontdoor | **Qwen3.5-35B-A3B** Q4KM (20 GB) | **4×48t** | moe6 (lookup needs corpus) | — | — | **12.7** | **~50.8 t/s** |
| coder_escalation | Qwen2.5-Coder-32B Q4KM (18.5 GB) | **4×48t** | spec+tree+lu | 32 | 0.05 | 10.8 | **~43.3 t/s** |
| architect_general | **Qwen3.5-122B-A10B** Q4KM (69 GB) | **1×96t node0** | moe8+spec+lu | 24 | 0 | 4.3 | **4.3 t/s** |
| architect_coding | Qwen3-Coder-480B-A35B Q4KM (250 GB) | **1×96t node0** | spec+lu (NO tree) | 24 | 0 | 7.0 | **7.0 t/s** |
| ingest | Qwen3-Next-80B-A3B Q4KM (46 GB) | **1×96t node0** | none (SSM) | — | — | ~12 | **~12 t/s** |

**Key corrections from sweep:**
- 480B: tree (ps=0.05) was HARMFUL (-19%). Corrected to linear only (ps=0). dm=24 beats dm=48.
- 122B: dm=24 optimal (was 8). Still linear only. Throughput 4.3 (was claimed 12.6 — old number was different model/config).
- Coder: Using Q4KM here (not f16). Tree beneficial on Q4KM (ps=0.05). 4×48t aggregate 43.3 t/s.

**Frontdoor correction (2026-03-24 benchmark):** 4×48t moe6 measured at 12.7 t/s/inst, ~50.8 t/s aggregate (was estimated 19.6/78). The 19.6 figure included lookup acceleration which requires a pre-built ngram corpus — without it, `--lookup` is a no-op. Actual gain is moe6-only.

**Total model footprint**: ~515 GB (with 4x frontdoor + 4x coder copies)

*Note: Single-instance models (architect, ingest) run on node0 only, freeing node1 cores for multi-instance models. The NUMA partitioning prevents cross-model memory interference.

## Benchmark Data

All benchmark data and scripts are in `epyc-inference-research/`:

| Test | Script | Data Dir |
|------|--------|----------|
| S2: hybrid 4-way | `bench_numa_parallel_decode.sh`, `bench_numa_cd_only.sh` | `data/numa_parallel/` |
| T5: dense 4-way tree | `bench_numa_tree_spec.sh` | `data/numa_tree_spec/` |
| T6: 480B tree+NUMA | `bench_numa_t6_480b.sh` | `data/numa_t6_480b/` |
| Production sweep | `bench_numa_production_sweep.sh` | `data/numa_production/` |
| S3: hybrid+draft | `bench_numa_s3_hybrid_draft.sh` | `data/numa_s3_hybrid_draft/` |
| S5: prefill | `bench_numa_s5_prefill.sh` | `data/numa_s5_prefill/` |
| Qwen3.5 sweep | `bench_numa_qwen35_sweep.sh` | `data/numa_qwen35_sweep/` |
| Quant scaling | `bench_hybrid_quant_scaling.sh` | `data/hybrid_quant_scaling/` |
| **Comprehensive spec sweep** | `bench_all_spec_sweeps.sh` | `data/all_spec_sweep/` |

## Architecture Insights for Future Work

1. **MoE models (few active params) are NUMA-sensitive** — cross-node memory access dominates because compute is cheap. NUMA pinning gives 6-7x.

2. **Dense hybrid models are compute-sensitive** — all params active, so 48 threads isn't enough. 2x aggregate max.

3. **Large hybrids (122B+) are recurrent-bottlenecked** — ~12 t/s decode regardless of NUMA config, thread count, or model size. Delta Net recurrence dominates.

4. **Qwen3.5 hybrids are 2-3.6x faster than pure MoE at 122B+ scale** — recurrent layers avoid KV cache bandwidth costs. Consider replacing 235B/480B MoE architect roles with Qwen3.5 hybrids if quality permits.

5. **Q4_K_M is optimal for hybrids** — recurrent state update (constant cost) fills most compute. Q8 costs 17-39% speed for marginal quality.

## Deployment Record (2026-03-19)

### What Was Implemented

Changes to `epyc-orchestrator/scripts/server/orchestrator_stack.py`:

1. **taskset CPU pinning** — replaced `numactl --preferred/--interleave` with `taskset -c` per NUMA quarter/node
2. **NUMA 4-way multi-instance** — frontdoor and coder_escalation each launch 4 NUMA-pinned instances
3. **NUMA-aware thread counts** — 48 (quarter) or 96 (node) per role, not blanket 96
4. **mlock** — `--mlock` for frontdoor + ingest (latency-critical, S2: 30x improvement)
5. **Worker/vision NUMA pinning** — worker_explore (Q0A), worker_vision (Q0B), vision_escalation (node1)

Model swaps in `model_registry.yaml`:
- frontdoor: Qwen3-Coder-30B-A3B → **Qwen3.5-35B-A3B Q4_K_M** (moe6+lookup, quality +31%)
- architect_general: Qwen3-235B-A22B → **Qwen3.5-122B-A10B Q4_K_M** (moe8+spec+lu, quality +41%, -64GB RAM)

### Deployed Port Map

| Role | Ports | NUMA Config | Threads | mlock |
|------|-------|-------------|---------|-------|
| frontdoor | 8080, 8180, 8280, 8380 | 4× quarters | 48 each | Yes |
| coder_escalation | 8081, 8181, 8281, 8381 | 4× quarters | 48 each | No |
| worker_explore | 8082 | Q0A | 24 | No |
| architect_general | 8083 | Node 0 | 96 | No |
| architect_coding | 8084 | Node 0 | 96 | No |
| ingest | 8085 | Node 0 | 96 | Yes |
| worker_vision | 8086 | Q0B | 24 | No |
| vision_escalation | 8087 | Node 1 | 96 | No |

### Remaining Work

1. ~~**Round-robin routing**~~ — DONE (2026-03-24). `RoundRobinBackend` wraps multi-instance backends. Config uses comma-separated URLs. frontdoor (4 instances) and coder_escalation (4 instances) now distribute requests round-robin.
2. **Benchmark validation** — Qwen3.5-35B on NUMA 4×48t with moe6+lookup needs direct benchmarking. The ~78 t/s estimate extrapolates from single-instance × NUMA scaling factor.
3. ~~**Coder quant quality benchmark**~~ — DONE (2026-03-24). Q4KM (74%) ≈ f16 (74%) > Q8 (77%) but Q4KM is 1.3-1.7x faster and 1.8-3.5x less RAM. Q4_K_M confirmed as optimal.
4. **Architect 2-instance** — 122B at 69GB could run 2×96t for ~2x aggregate if architect throughput bottlenecks.

### Completed (2026-03-21)

5. ~~**Comprehensive spec param sweep**~~ — DONE. 14/14 sweeps, 1,290 measurements. All models verified at deployment threads. Data: `data/all_spec_sweep/all_spec_sweep_20260320_011544.csv`.
6. ~~**Worker role replacement**~~ — DONE. 7B f16 → 30B-A3B in registry, orchestrator_stack.py, q_scorer.py. Try-cheap-first model at 39.1 t/s (48t).
7. ~~**Registry/config updates**~~ — DONE. All dm/ps/throughput values updated in model_registry.yaml, orchestrator_stack.py spec_overrides, q_scorer.py baseline_tps.
8. **mlock enabled on ALL HOT tier** — orchestrator_stack.py updated. Total ~701 GB locked, 429 GB free for KV + OS.

### Coder Quant Decision Matrix (COMPLETE — scored 2026-03-24)

| Variant | Size | 4×RAM | dm | ps | Tree? | 192t t/s | 48t t/s | 4×48t agg | Quality (raw) | Quality (pass) | Decision |
|---------|------|-------|----|----|-------|----------|---------|-----------|---------------|----------------|----------|
| **Q4_K_M** | 18.5 GB | 74 GB | 32 | 0.05 | Yes (+2.7%) | 12.2 | 10.8 | **~43.3** | 72.7% (133/183) | **74% (45/61)** | **WINNER — deploy** |
| Q8_0 | 33 GB | 132 GB | 16 | 0 | No (tree -6%) | 10.1 | 8.2 | ~32.7 | 74.3% (136/183) | 77% (47/61) | +3pp quality, -24% speed, 1.8x RAM |
| f16 | 65 GB | 260 GB | 32 | 0.05 | Yes (+17%) | 7.6 | 6.4 | ~25.6 | 72.7% (133/183) | 74% (45/61) | Same quality, -41% speed, 3.5x RAM |

**Conclusion (2026-03-24):** Q4_K_M confirmed as optimal coder quant. f16 offers **zero quality improvement** despite halving speed and 3.5x RAM. Q8 gains only +2 questions (47 vs 45 pass) at 24% speed cost and 1.8x RAM. The quality ceiling is the model itself, not the quantization.

**Suite-by-suite quality (pass rate ≥2, scored by Claude-as-Judge):**

| Suite | Q4KM | Q8_0 | f16 | Notes |
|-------|------|------|-----|-------|
| agentic (10) | 27/30 | 26/30 | 24/30 | f16 had a timeout (t3_q1) |
| coder (10) | 20/30 | 24/30 | 24/30 | Q8/f16 better on horse proof, probability |
| general (10) | 20/30 | 23/30 | 21/30 | Q8 fixed schedule bug; f16 has repetition |
| instruction_precision (11) | 20/33 | 20/33 | 20/33 | All three identical — model limitation |
| math (10) | 21/30 | 26/30 | 24/30 | Q8 nailed horse proof + probability theory |
| thinking (10) | 19/30 | 17/30 | 20/30 | Q8 had timeout; f16 better on paradox |

**Key observations:**
- All three quants hit the same instruction_precision ceiling (20/33) — constraint adherence is a model-level weakness
- Q8 showed notable math improvements (+5 raw points) but lost on thinking (timeout + planning errors)
- f16 showed repetition/degeneration issues (prompt echo, repetition loops) that were **worse** than Q4KM
- Both Q8 and f16 echo the full prompt before responding — likely a chat template issue at lower TPS

**Verified rules (sweep 2026-03-21):**
- Q4KM: tree (ps=0.05) is BENEFICIAL — overturns prior assumption
- Q8: tree hurts at 48t deployment, helps at 192t — mode-dependent
- f16: tree helps +17% at 48t — confirmed
- Hybrids (Qwen3.5-*): NO speculation — confirmed (122B tree = -25% to -40%)
- 480B MoE: tree is HARMFUL (-19%) — was assumed beneficial, now corrected to linear only
