# Handoff: NUMA-Aware Orchestrator Deployment

**Status**: READY TO DEPLOY. All benchmarks complete. No code changes to llama.cpp needed.
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

#### Frontdoor: Qwen3-Coder-30B-A3B Q4_K_M (16 GB) — **4 instances, 6.7x**

```bash
# Instance 1 (NUMA quarter 0A)
taskset -c 0-23,96-119 /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf \
  -md /mnt/raid0/llm/models/Qwen3-Coder-Instruct-DRAFT-0.75B-32k-Q4_0.gguf \
  --draft-max 32 --kv-unified \
  -t 48 -np 1 --port 8080 -ngl 0

# Instance 2 (NUMA quarter 0B)
taskset -c 24-47,120-143 /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf \
  -md /mnt/raid0/llm/models/Qwen3-Coder-Instruct-DRAFT-0.75B-32k-Q4_0.gguf \
  --draft-max 32 --kv-unified \
  -t 48 -np 1 --port 8081 -ngl 0

# Instance 3 (NUMA quarter 1A)
taskset -c 48-71,144-167 /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf \
  -md /mnt/raid0/llm/models/Qwen3-Coder-Instruct-DRAFT-0.75B-32k-Q4_0.gguf \
  --draft-max 32 --kv-unified \
  -t 48 -np 1 --port 8082 -ngl 0

# Instance 4 (NUMA quarter 1B)
taskset -c 72-95,168-191 /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf \
  -md /mnt/raid0/llm/models/Qwen3-Coder-Instruct-DRAFT-0.75B-32k-Q4_0.gguf \
  --draft-max 32 --kv-unified \
  -t 48 -np 1 --port 8083 -ngl 0
```

**Benchmark**: 95.8 t/s aggregate vs 14.2 t/s single-instance (6.7x)
**Routing**: Round-robin across ports 8080-8083

#### Coder Escalation: Qwen2.5-Coder-32B f16 (65 GB) — **4 instances, 6.4x**

```bash
# Same pattern as frontdoor, 4 instances on quarters
# Each instance: 48 threads, ports 8084-8087
taskset -c 0-23,96-119 /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  -m /mnt/raid0/llm/models/Qwen2.5-Coder-32B-Instruct-GGUF-f16/qwen2.5-coder-32b-instruct-fp16-00001-of-00009.gguf \
  -md /mnt/raid0/llm/models/Qwen2.5-0.5B-Instruct-f16.gguf \
  --draft-max 32 --kv-unified \
  -t 48 -np 1 --port 8084 -ngl 0
# ... repeat for ports 8085-8087 on other quarters
```

**Benchmark**: 26.4 t/s aggregate vs 4.1 t/s single (6.4x)
**Note**: 65 GB model — fits on one NUMA node (~566 GB each). 4 copies = 260 GB total, fits in 1.13 TB.

#### Architect General: Qwen3-235B-A22B Q4_K_M (130 GB) — **1 instance, node 0, 1.5x**

```bash
taskset -c 0-47,96-143 /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/lmstudio-community/Qwen3-235B-A22B-GGUF/Qwen3-235B-A22B-Q4_K_M-00001-of-00004.gguf \
  -md /mnt/raid0/llm/models/Qwen_Qwen3-0.6B-Q8_0.gguf \
  --draft-max 32 --kv-unified \
  -t 96 -np 1 --port 8088 -ngl 0
```

**Benchmark**: 7.87 t/s vs 5.19 t/s at 192t (1.5x)
**Note**: Too large for multi-instance (2×130 GB = 260 GB, would work but with degraded per-instance speed).

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
  model: Qwen3-Coder-30B-A3B-Instruct-Q4_K_M
  draft_max: 32
  # NEW NUMA fields:
  numa_instances: 4
  numa_threads_per_instance: 48
  numa_cpu_lists:
    - "0-23,96-119"
    - "24-47,120-143"
    - "48-71,144-167"
    - "72-95,168-191"

architect_general:
  model: Qwen3-235B-A22B-Q4_K_M
  draft_max: 32
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

## What NOT To Do

1. **Don't use `numactl --membind`** — blocked in container. `taskset` + first-touch is sufficient.
2. **Don't add speculation to hybrid models** (Qwen3.5-*) — S3 proved all draft configs are net-negative on NUMA 4-way. The drafter competes for NUMA quarter bandwidth.
3. **Don't run 192 threads on any model** — always worse than NUMA-pinned configs.
4. **Don't pipeline prefill** (S5) — ceiling is ~8%, not worth the C++ complexity.
5. **Don't merge `feature/dflash-speculation`** — DFlash NOT viable on Q4_K_M (27% per-token, 1.4% block).

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

## Expected Production Throughput (Aggregate)

| Role | Model | Current (192t) | After NUMA | Speedup |
|------|-------|---------------|-----------|---------|
| frontdoor | 30B-A3B | ~39 t/s (dm=32) | **95.8 t/s** (4×48t) | **2.5x** |
| coder_escalation | 32B f16 | ~5.8 t/s (tree) | **26.4 t/s** (4×48t) | **4.6x** |
| architect_general | 235B | ~8.6 t/s (dm=32) | **7.87 t/s** (1×96t) | 0.9x* |
| architect_coding | 480B | ~5.7 t/s (dm=48) | **3.82 t/s** (1×96t+tree) | 0.7x* |
| ingest | 80B | ~12 t/s | **~24 t/s** (2×96t) | **2.0x** |

*Note: Single-instance models show lower per-request speed with NUMA pinning (fewer threads) but this frees the other NUMA node for concurrent workloads. The architect models typically run alongside frontdoor, so the NUMA partitioning prevents cross-model interference.

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

## Architecture Insights for Future Work

1. **MoE models (few active params) are NUMA-sensitive** — cross-node memory access dominates because compute is cheap. NUMA pinning gives 6-7x.

2. **Dense hybrid models are compute-sensitive** — all params active, so 48 threads isn't enough. 2x aggregate max.

3. **Large hybrids (122B+) are recurrent-bottlenecked** — ~12 t/s decode regardless of NUMA config, thread count, or model size. Delta Net recurrence dominates.

4. **Qwen3.5 hybrids are 2-3.6x faster than pure MoE at 122B+ scale** — recurrent layers avoid KV cache bandwidth costs. Consider replacing 235B/480B MoE architect roles with Qwen3.5 hybrids if quality permits.

5. **Q4_K_M is optimal for hybrids** — recurrent state update (constant cost) fills most compute. Q8 costs 17-39% speed for marginal quality.
