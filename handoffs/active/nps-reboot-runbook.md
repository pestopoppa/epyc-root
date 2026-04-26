# NPS BIOS Reboot Runbook — CPU1 Unlock Gate

**Status**: scheduled (pending user-initiated reboot window)
**Priority**: HIGH — gates CPU1 TP-sharding real-world viability
**Created**: 2026-04-24
**Owner**: CPU-optimization workstream (see [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md))
**Scope**: change NPS mode from NPS2 → NPS4; conditionally to L3-as-NUMA

## Why this reboot

Measured 2026-04-24 that under **NPS2**, CPU1 TP-sharding cannot deliver its 2-5× single-instance projection. The combined ceiling of barrier-redesign + CCD-pinning + NUMA-local-mbind is ~2-5% (see `research/deep-dives/cpu-tp-phase1a-ccd-barrier-2026-04-24.md` and memory `project_cpu1_nps2_ceiling.md`). Cause: node distance ratio is only 10/12 (20% cross-node penalty) — too uniform for NUMA TP to matter.

**NPS4** = 4 NUMA nodes × 3 CCDs each; **L3-as-NUMA** = 12 NUMA nodes × 1 CCD each. Either unlocks meaningful NUMA granularity. NPS4 is the prudent first step (preserves 4×48t deployment, AMD-recommended, lower risk). L3aaN is a second step IF NPS4 proves the concept.

## Pre-reboot state (FREEZE before BIOS change)

Capture these numbers so post-reboot regressions are detectable.

### Production registry baselines

| Role | Model | NUMA Config | Per-inst t/s | Agg t/s | Source |
|---|---|---|---|---|---|
| frontdoor | Qwen3.5-35B-A3B Q4KM | 4×48t | 12.7 | ~50.8 | model_registry.yaml |
| coder_escalation | Qwen2.5-Coder-32B Q4KM | 4×48t | 10.8 | ~43.3 | model_registry.yaml |
| worker_explore | Qwen3-Coder-30B-A3B Q4KM | 1×24t | 39.1 | — | model_registry.yaml |
| architect_general | Qwen3.5-122B-A10B Q4KM | 2×96t | 4.3 | ~8.3 | model_registry.yaml |
| architect_coding | REAP-246B Q4KM | 2×96t | 8.0 | 16.5 | model_registry.yaml |

### 2026-04-24 direct measurements (freeze)

#### Single-instance thread sweep (Qwen3-Coder-30B-A3B Q4, -p 0 -n 64 -r 3, quiet host, OMP build)

| Config | t/s |
|---|---|
| taskset 0-23, -t 24 | 44.32 |
| taskset 0-47, -t 48 | 45.80 |
| taskset 0-95, -t 96 (all 96 phys, no SMT) | **49.34** (peak) |
| taskset 0-47,96-143, -t 96 (node 0 phys+HT) | 44.63 |
| taskset 0-143, -t 144 (crosses NUMA) | 25.74 bimodal |
| --numa distribute --mlock, -t 192 | 18.69 bimodal |

#### Concurrent-split sweep, OMP build, SMT-paired cpusets

| Model | 4×48t | 8×24t | 16×12t | 32×6t | 48×4t | Peak |
|---|---|---|---|---|---|---|
| Qwen3.6-27B Q8 | 6.62 | 7.91 | 8.55 | 10.47 | **15.39** | 48×4t |
| Qwen3.6-35B-A3B Q8 | 64.26 | 76.35 | 85.89 | 92.75 | **135.08** | 48×4t |
| Qwen2.5-Coder-32B Q4 | 13.64 | 15.08 | 16.01 | **20.03** | 17.34 ↓ | 32×6t |

35B-A3B Q8 at 48×4t = 135 t/s ≈ 100% of 460 GB/s BW roofline.

#### CPU1 Phase 1.0+1.1 noOMP measurements (Qwen3-Coder-30B-A3B Q4, 96t, n=64 r=3)

| Build/Config | t/s |
|---|---|
| OMP flat (production) | 45.92 |
| noOMP flat (ggml default) | 38.90 |
| noOMP + Phase 1.0 only (CCD barrier) | 38.22 |
| noOMP + Phase 1.0 + 1.1 (CCD barrier + pinning) | 39.07 |

#### 2-way NUMA microbench (`tp_gemv_numa_bench`, 7.6 GB GEMV)

| Mode | GB/s |
|---|---|
| Flat 96t | 246.3 |
| 2×48t NUMA-local (mbind + first-touch) | 250.0 (+1.5%) |

Full raw data in `/mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/2026-04-24/`.

### System state pre-reboot

| Knob | Current value |
|---|---|
| NPS mode | **NPS2** (2 nodes × 6 channels each; node distance 10/12) |
| THP | `always` (user set 2026-04-23 via sudo sysctl; non-persistent across reboot) |
| THP defrag | `always` (user set 2026-04-23; non-persistent) |
| NUMA balancing | **0** (off; user set 2026-04-23 via `sysctl kernel.numa_balancing=0`; non-persistent) |
| `perf_event_paranoid` | **1** (user set 2026-04-23; non-persistent) |
| 1 GB hugepages on node 1 | 1 allocated via `/sys/devices/system/node/node1/hugepages/...` (non-persistent) |
| Governor | `performance` (persistent in BIOS/OS) |
| SMT | enabled (192 logical from 96 cores) |

**IMPORTANT**: the `/proc/sys` and `/sys/kernel/mm` settings from 2026-04-23 are RUNTIME only; they reset on reboot. Need to re-apply after reboot.

## Reboot procedure

### Step 1 — Stop running workloads

```bash
# Stop any running llama-server instances (production orchestrator)
# User: verify no critical jobs in-flight before proceeding

# Check what's running
pgrep -af "llama-server|llama-bench|orchestrator_stack" | head -10

# Save any in-flight benchmark outputs (optional):
ls -la /mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/2026-04-24/
```

### Step 2 — BIOS change

Enter BIOS setup at boot (typically F2 or Del — depends on chassis). Navigate to:
- Advanced → AMD CBS → DF Common Options → Memory Addressing → **NUMA Nodes Per Socket**
  - Current: NPS2
  - Change to: **NPS4**
- Save + exit. System reboots.

(If it's a Supermicro/ASRock/Gigabyte board the menu path may differ slightly — look for "NPS" or "NUMA nodes per socket" in the AMD CBS → DF section.)

### Step 3 — Post-reboot validation

```bash
# Verify new NUMA topology
numactl --hardware | head -12
# Expected: "available: 4 nodes (0-3)" with distances similar to 10/12/12/12 pattern

# Re-apply non-persistent sysctls (from 2026-04-23 work):
sudo sysctl kernel.perf_event_paranoid=1
sudo sysctl kernel.numa_balancing=0
echo always | sudo tee /sys/kernel/mm/transparent_hugepage/enabled
echo always | sudo tee /sys/kernel/mm/transparent_hugepage/defrag

# Verify
cat /sys/kernel/mm/transparent_hugepage/enabled
cat /proc/sys/kernel/numa_balancing
cat /proc/sys/kernel/perf_event_paranoid

# Verify page cache warm-up needed (models will be cold after reboot)
free -g | head -3
# Expect `buff/cache` to be small (~1 GB vs ~439 GB before reboot)
```

### Step 4 — Sanity benchmark (10 min)

Run the canonical baseline model in a known config to confirm nothing's fundamentally broken:

```bash
cd /mnt/raid0/llm/llama.cpp-experimental
MODEL=/mnt/raid0/llm/lmstudio/models/lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf
LD_LIBRARY_PATH=./build-llamafile-on/bin taskset -c 0-95 \
  ./build-llamafile-on/bin/llama-bench -m "$MODEL" -t 96 -p 0 -n 64 -r 3
```

**Expected**: similar to pre-reboot 45-49 t/s range. Major regressions (<30 t/s) would indicate something more fundamental broke.

### Step 5 — Full re-benchmark matrix

Re-run the same measurements we have pre-reboot baselines for. Tools:

```bash
# 1. Single-instance thread sweep (reuse yesterday's sweep script with appropriate cpusets)
#    Note: under NPS4, cpusets for 24t/48t pinning may map differently to nodes.
bash /mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/2026-04-23/thread-sweep.sh
#    → outputs to /mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/2026-04-23/thread-sweep/

# 2. Concurrent-split sweep (4×48t / 8×24t / 16×12t / 32×6t / 48×4t)
bash /mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/2026-04-24/concurrent-sweep-16x12.sh
bash /mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/2026-04-24/concurrent-sweep-32x6.sh
bash /mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/2026-04-24/concurrent-sweep-48x4.sh
#    → note: under NPS4, the "SMT-paired within node" cpuset assignments in these scripts should be re-checked
#      since the NUMA node boundaries have shifted

# 3. CPU1 Phase 1.0+1.1 re-measurement
cd /mnt/raid0/llm/llama.cpp-experimental
GGML_CCD_POOLS=1 LD_LIBRARY_PATH=./build-noomp/bin ./build-noomp/bin/llama-bench \
  -m "$MODEL" -t 96 -p 0 -n 64 -r 3

# 4. 2-way / 4-way NUMA microbench
cd /mnt/raid0/llm/cpu-tp-prototype
./tp_gemv_numa_bench 5120 400000 15
#    (will need an update to test 4-way under NPS4 — see "Future work" below)

# Save all outputs to /mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/2026-04-25/  (use current date)
```

### Step 6 — Decision

Compare post-reboot vs pre-reboot numbers. Key deltas to examine:

| Measurement | Δ vs NPS2 | Interpretation |
|---|---|---|
| Single-instance 96t | ~equal | Expected (compute-bound or L3-resident parts unchanged) |
| 4×48t concurrent aggregate | Could go up (if quarter maps to node) or down (if quarter straddles nodes) | Reconfigure cpusets if down |
| 48×4t concurrent | Depends on sub-CCD layout under NPS4 | May need new cpuset layout |
| Phase 1.0+1.1 CPU1 | **HOPE: meaningful (+10-25%)** | Triggers further Phase 1.2/1.3 work |
| NUMA microbench 4-way | Should be bigger delta than 2-way NPS2's +1.5% | Confirms NUMA-local helps |

**Decision points**:
- **If CPU1 Phase 1.0+1.1 delivers +10% or more under NPS4**: proceed to CPU1 Phase 1.2 (CCD-aware work distribution) and 1.3 (weight mbind at model load).
- **If CPU1 still ~neutral under NPS4**: consider L3-as-NUMA reboot (Phase 2). If L3aaN also neutral → CPU1 is not the right lever on this hardware; deprioritize in favor of CPU4 (sync primitive, independent of NUMA) or KV-side memory optimizations.
- **If multi-instance 4×48t regresses under NPS4**: may need to re-pin cpusets (4 quarters under NPS4 = 4 NUMA nodes — potentially better). If still regressed, rollback to NPS2.

### L3-as-NUMA (12-way) future reboot — memory budget for weight replication

If and when we reboot to L3-as-NUMA (12 NUMA nodes = 1 per CCD), weight replication under Lever A' would scale to **12 replicas**. Memory budget:

- 30B-A3B Q4_K_M (17 GB) × 12 = **204 GB**
- Qwen3.5-35B-A3B Q4_K_M (~20 GB) × 12 = **240 GB**
- REAP-246B Q4_K_M (~130 GB) × 12 = **1560 GB** → **does not fit** in 1.1 TB RAM

So for large models like REAP-246B with **full weight replication**, L3aaN is infeasible. NPS4 (4 replicas × 130 = 520 GB) works.

**Updated 2026-04-26**: under CPU15 Phase 3.2's **shard-based inter-process EP** (`large-moe-expert-parallelism.md`), each instance only holds 1/N of expert weights in a node-local anon buffer. For REAP-246B with N=12: 12 × 11.5 GB shard buffers + 138 GB shared GGUF mmap = 276 GB total — **fits comfortably in 1.1 TB RAM**. So L3aaN + EP-shard for REAP-246B IS memory-feasible; the constraint shifts from "RAM budget" to "bandwidth math". Whether it delivers throughput is an open question — see the L3aaN section in `large-moe-expert-parallelism.md` for the pre-reboot prediction (likely neutral-to-worse vs single-instance, with two narrow paths where it might win).

Decision deferred per user: "we can do [L3aaN] later after we've exhausted our NPS4 optimization tracks". Under current NPS4 the 4-replica ceiling is 4 × max_model_size ≤ 1.1 TB → max ~275 GB model. Under L3aaN + EP-shard, the per-instance memory ceiling is 1.1 TB / N + shared mmap, giving access to much larger models if the bandwidth math works.

### Rollback (if NPS4 breaks something critical)

Return to BIOS, set NPS mode back to NPS2. Reboot. Re-apply sysctls.

## Ongoing work items surviving the reboot

### Infrastructure that persists

- `llama.cpp-experimental` branch `cpu-optimization/backlog-2026-04-23` with CPU1 Phase 1.0+1.1 code (env-var `GGML_CCD_POOLS=1`, noOMP build in `build-noomp/`)
- `build-llamafile-on` (production OMP baseline), `build-llamafile-off` (tinyBLAS off test), `build-vnni-q8` (CPU2 falsified port, safe to delete)
- Microbenches in `/mnt/raid0/llm/cpu-tp-prototype/`: `tp_gemv_bench` (flat vs CCD TP) and `tp_gemv_numa_bench` (2-way NUMA)
- Archive branch `archive/test-qwen36-upstream-2026-04-23` preserves prior-session state

### Future Phase 1 work (post-NPS reboot, if NPS4/L3aaN unlocks gains)

**Phase 1.2 — CCD-aware work distribution in ggml**:
- In `ggml_compute_forward_mul_mat` and `..._mul_mat_id`, change `ith/nth` strided partitioning to CCD-block-contiguous: worker on CCD c handles rows `[c * N / ccd_count, (c+1) * N / ccd_count)` instead of strided by thread index.
- Helper infrastructure already in place: `ggml_compute_state.ccd_id` and `.ccd_local_id` are set when `GGML_CCD_POOLS=1`.
- Still env-var-gated; bit-exact vs existing work distribution is a hard gate.
- Estimated: 2-3 days.

**Phase 1.3 — NUMA-bound weight mmap at model load**:
- In llama.cpp's model loader (`llama.cpp/src/llama-model-loader.cpp` approximately), add an optional mbind pass on weight tensors after mmap.
- For each weight tensor, split by N (row-major) into NPS_count chunks; mbind each chunk to its respective NUMA node.
- Requires `libnuma-dev` for `mbind` + `numa_bitmask_*`; runtime (`libnuma1`) already installed but headers not. Install: `sudo apt-get install -y libnuma-dev`.
- Gated by env var `GGML_NUMA_WEIGHTS=1`. Default off.
- Interaction with `--mlock`: mlock forces pages resident but doesn't dictate which node; mbind does. Combine both.
- Estimated: 2-3 days.

**Phase 1.4 — column-sharded matmul with per-CCD reduce** (if 1.2 + 1.3 together aren't enough):
- True "each CCD owns a disjoint slice of output N, compute partial, reduce at end" pattern from the handoff §"Core Design".
- Shared-L3 reduction primitive (bounce 1 × N_out × 4 bytes through L3 per reduction = ~70 KB for typical ops).
- Comm-hiding: prefetch next layer's weight shard into L2 during reduction window.
- Estimated: 3-5 days.

### Adjacent work that's independent of NPS mode

- **CPU4 — per-CCD lock-free sync primitive** (task #11 HIGH): reimplements ggml_barrier using a wait-free primitive (e.g. tournament tree or AMD RDTSCP-based). Could benefit both NPS2 and NPS4 configs. Not dependent on the BIOS change. ~1 week.
- **CPU7 — explore further tinyBLAS / BLAS paths for prefill**: tinyBLAS/BLIS showed 0% gain on decode but prefill regime is different. Separate test.
- **Production 48×4t / 32×6t deployment** (task #10 follow-up): orchestrator config change to adopt the concurrent-split aggregate win; independent of NPS mode but may re-benchmark differently under NPS4.
- **CPU6 — ZenDNN eval** (task #9): still deferred indefinitely; weak prior after tinyBLAS 0%.

### Baseline measurements to capture RIGHT NOW (pre-reboot freeze)

See next section for the specific commands to run before rebooting.

## Pre-reboot final baseline capture

If baselines weren't already captured today, run this pre-reboot freeze script:

```bash
# One-shot pre-reboot freeze — save to /mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/pre-nps4-freeze/
mkdir -p /mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/pre-nps4-freeze
cd /mnt/raid0/llm/llama.cpp-experimental
export LD_LIBRARY_PATH=./build-llamafile-on/bin
OUT=/mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/pre-nps4-freeze

# Canonical thread sweep
MODEL=/mnt/raid0/llm/lmstudio/models/lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf
for tn_set in "24 0-23" "48 0-47" "96 0-95"; do
    set -- $tn_set; t=$1; cpus=$2
    taskset -c "$cpus" ./build-llamafile-on/bin/llama-bench -m "$MODEL" -t "$t" -p 0 -n 64 -r 3 -o json > "$OUT/thread-${t}t.json"
done
./build-llamafile-on/bin/llama-bench -m "$MODEL" -t 192 -p 0 -n 64 -r 3 --numa distribute -mmp 1 -o json > "$OUT/thread-192t-distribute.json"

# 4x48t concurrent (SMT-paired quarters) on current production models
# See concurrent-sweep-16x12.sh for the cpuset pattern.

# System state snapshot
{
    echo "=== $(date -Iseconds) ==="
    numactl --hardware
    echo "THP: $(cat /sys/kernel/mm/transparent_hugepage/enabled)"
    echo "numa_balancing: $(cat /proc/sys/kernel/numa_balancing)"
    echo "perf_event_paranoid: $(cat /proc/sys/kernel/perf_event_paranoid)"
    grep -iE "AnonHugePages|HugePages_Total|Hugepagesize|Hugetlb" /proc/meminfo
    lscpu | head -30
} > "$OUT/system-state.txt"
```

## Resume workflow after reboot — TL;DR

After NPS4 reboot:
1. Re-apply sysctls (THP, numa_balancing, perf_event_paranoid)
2. Run sanity benchmark — confirm no gross regression
3. Re-run thread sweep + concurrent-split sweep + CPU1 Phase 1.0+1.1 + 2-way→4-way NUMA microbench
4. Compare against pre-reboot freeze
5. Decision: proceed to Phase 1.2/1.3 (if CPU1 wins) OR try L3aaN (if NPS4 marginal) OR abandon CPU1 (if both neutral)

All artifacts in `/mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/`. All code on `cpu-optimization/backlog-2026-04-23` branch of `llama.cpp-experimental`. All memories in `.claude/memory/MEMORY.md`.

## References

- `research/deep-dives/cpu-optimization-phase0-baseline.md` — Phase 0 baseline
- `research/deep-dives/cpu-optimization-cheap-checks-2026-04.md` — tinyBLAS/BLIS/compiler flats
- `research/deep-dives/cpu-96t-production-sweep-2026-04-24.md` — 96t-single-node + concurrent-split sweep
- `research/deep-dives/cpu-tp-sharding-phase0-microbench-2026-04-24.md` — standalone TP microbench validation
- `research/deep-dives/cpu-tp-phase1a-ccd-barrier-2026-04-24.md` — Phase 1.0+1.1 ggml integration result + NPS2 ceiling analysis
- `progress/2026-04/2026-04-23-cpu-optimization-kickoff.md`
- `progress/2026-04/2026-04-24.md`
- `progress/2026-04/2026-04-26.md` — Phase A-G + P1-P4 (next session reference)
- Memory: `project_cpu1_nps2_ceiling.md`, `project_concurrent_split_throughput.md`, `feedback_cpu_decode_bw_bound.md`, `feedback_canonical_baseline_protocol.md`
- Handoffs: `cpu-inference-optimization-index.md`, `intra-process-tensor-parallel-decode.md`, `single-instance-system-tuning.md`, `cpu-shape-specialized-gemv-decode.md`, `cpu-kernel-env-flags-inventory.md`, `cpu-hierarchical-barrier.md`, `cpu-optimization-thesis-pause-2026-04-26.md`, `large-moe-expert-parallelism.md`

---

# L3aaN evaluation plan — 2026-04-26 update

**Status**: pre-reboot SNAPSHOT IN HAND, BIOS reboot pending user authorization. Post-reboot agent: read this section first.

## Context as of 2026-04-26

A full Phase A-G plan ran today: canonical baselines + regression bisect (no source regression — historical 49.34 was a transient) + REAP-246B perf profile + bottleneck classification across the 5 production models + CPU1 stack instability isolation + CPU2 mbind kill-switch + CPU4 hierarchical sync (NEGATIVE). All findings in `progress/2026-04/2026-04-26.md`. Strategic position: **EP +17% on Qwen3.6-35B Q8_0 frontdoor** is the only confirmed production gain from CPU1+CPU2+CPU15 work. The 4 Q4_K_M production models are sync-bound (structural MoE imbalance — no software lever). Q8_0 frontdoor is bandwidth-bound (the remaining lever after EP is **L3aaN** — finer NUMA granularity).

## Pre-reboot snapshot (canonical NPS4 baselines at HEAD `8cb04da9d`)

`taskset -c 0-95 -t 96 -fa 1`, `LD_LIBRARY_PATH=/mnt/raid0/llm/llama.cpp-experimental/build/bin:/opt/AMD/aocc-compiler-5.0.0/lib`, no env vars unless noted. `llama-bench -p 0 -n 32 -r 2/3` per row.

| Model | Quant | Path | t/s ± std | perf class |
|-------|-------|------|-----------|------------|
| Qwen3-Coder-30B-A3B | Q4_K_M | `/mnt/raid0/llm/lmstudio/models/lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf` | 43.57 ± 0.10 | sync-bound |
| Qwen3.6-35B-A3B | Q8_0 | `/mnt/raid0/llm/models/Qwen3.6-35B-A3B-Q8_0.gguf` | 14.63 ± 0.01 | **BW-bound** ← L3aaN target |
| Qwen3-Next-80B-A3B | Q4_K_M | `/mnt/raid0/llm/lmstudio/models/lmstudio-community/Qwen3-Next-80B-A3B-Instruct-GGUF/Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf` | 23.25 ± 0.08 | sync-bound |
| REAP-246B-A35B | Q4_K_M | `/mnt/raid0/llm/models/Qwen3-Coder-REAP-246B-A35B-Q4_K_M.gguf` | 6.85 ± 0.01 | sync-bound |
| gemma-4-26B-A4B-it | Q4_K_M | `/mnt/raid0/llm/models/gemma-4-26B-A4B-it-Q4_K_M.gguf` | 25.01 ± 0.08 | mixed |

**Plus EP on the BW-bound frontdoor:**

| Config | t/s ± std | vs canonical |
|--------|-----------|--------------|
| Qwen3.6-35B Q8_0 + `GGML_EP_N_INSTANCES=2 GGML_EP_NUMA_PIN=1 GGML_EP_MASTER_ALL_NODES=1 GGML_EP_WORKER_DRONE=1 GGML_EP_SHARD=1` | (+17% per prior session, 17.18 t/s) | reference for EP win |

**System state at snapshot time:**
- NPS4 (4 NUMA nodes, distance 10/12)
- THP=always, numa_balancing=0
- Governor=performance, base=1998 MHz, max=4510 MHz
- Up 2 days, load avg 0.71-4.0 (varies during benches)
- Free RAM: ~1100 GB

## L3aaN reboot procedure

Per AMD BIOS settings (varies by motherboard):
1. `Advanced → AMD CBS → DF Common Options → Memory Addressing → NUMA Nodes Per Socket` → set to **L3 cache as NUMA domain** (alternatively labelled `NPS4 with L3 split` or similar)
2. Save & exit, reboot
3. Verify post-boot: `numactl --hardware` shows **12 nodes** (was 4 nodes under NPS4)
4. Verify CCD layout intact: each node should have ~8 CPUs and ~96 GB
5. Re-apply sysctls (THP=always, numa_balancing=0, governor=performance) — usually persistent but verify

**Rollback**: same BIOS path, set back to `NPS4` (or whichever was prior). ~30 min downtime.

## Post-reboot evaluation plan

The post-reboot agent should run, IN ORDER:

### Step 1 — Sanity (~5 min)
- `numactl --hardware` → confirm 12 nodes
- `pgrep -af "llama" | grep -v "grep\|zsh\|docker"` → must be clean
- `ls /mnt/raid0/llm/llama.cpp-experimental/build/bin/llama-bench` → exists
- `cd /mnt/raid0/llm/llama.cpp-experimental && git rev-parse --short HEAD` → expect `8cb04da9d`

### Step 2 — Canonical baselines on all 5 production models (~30 min, sequential)

EXACTLY the protocol from the pre-reboot snapshot (above). Same `LD_LIBRARY_PATH` prepend. `taskset -c 0-95 -t 96 -fa 1`. `llama-bench -p 0 -n 32 -r 2`. Record t/s + std.

**Write results to**: `progress/2026-04/2026-04-NN-l3aan-evaluation.md` (NN = post-reboot date, e.g. `2026-04-27`).

**Compare row-by-row to the snapshot table above.**

### Step 3 — Regression detector

For each model:
- **Δ ≥ −2%** → no regression, continue
- **−5% ≥ Δ > −2%** → flag, investigate before continuing
- **Δ < −5%** → STOP. Likely L3aaN incompatible with this model class. Decision: revert.

### Step 4 — EP frontdoor evaluation (~30 min)

Qwen3.6-35B-A3B Q8_0 with full EP stack:
```
GGML_EP_N_INSTANCES=2 GGML_EP_NUMA_PIN=1 GGML_EP_MASTER_ALL_NODES=1 \
GGML_EP_WORKER_DRONE=1 GGML_EP_SHARD=1 \
LD_LIBRARY_PATH=... \
./build/bin/llama-bench -m /mnt/raid0/llm/models/Qwen3.6-35B-A3B-Q8_0.gguf \
  -t 96 -fa 1 -p 0 -n 32 -r 3
```

Expected: ≥17.18 t/s if L3aaN is neutral on EP. **>17.18 t/s = L3aaN wins; ship.** <17.18 t/s but no other regressions = L3aaN neutral, revert (cost > benefit).

### Step 5 — Optional: per-CCD weight pinning probe

L3aaN's UNIQUE value: 12 NUMA nodes = 1 CCD each. Could enable per-CCD weight pinning (`mbind` weights per-CCD-node + `GGML_CCD_WORK_DIST=1` for per-CCD work distribution → each CCD reads its own weights from local L3). This is the CPU1 Phase 1.3 "local" mode that wasn't fully implemented.

If steps 1-4 pass, opportunistically try: `GGML_CCD_POOLS=1 GGML_CCD_WORK_DIST=1 GGML_BARRIER_LOCAL_BETWEEN_OPS=1` (the safe 3-flag CPU1 stack from P3) under L3aaN. Could deliver more than the +1.8% it delivers under NPS4.

### Step 6 — Decision matrix

| Outcome | Action |
|---------|--------|
| All 5 canonical regression-free + EP frontdoor improves | **Keep L3aaN**; update `cpu-shape-specialized-gemv-decode.md`; proceed to Phase H |
| All canonical regression-free + EP neutral | **Revert L3aaN** (no benefit); proceed to Phase H on NPS4 |
| Any model regresses ≥5% | **Revert L3aaN immediately**; document which class was incompatible |
| EP frontdoor regresses | Surprising; investigate before reverting (could be a config issue) |

### Step 7 — Phase H (PPL gates, 6-12 hours wall-clock)

After step 6 decision is final, run PPL gates on the chosen topology to validate v5 candidate stack:
- Each production model × {canonical, kill-switch off, CPU1 3-flag opt-in (if shipping), EP-frontdoor (only Qwen3.6)}
- 32-chunk WikiText-2 PPL via `llama-perplexity`
- Bit-identical OR ≤1e-4 relative drift required for ship

After Phase H: Phase I (v5 cherry-pick) → J (v5 audit) → K (shadow) → L (orchestration wiring) → M (rollout).

## Branch state at wrap-up

- `llama.cpp-experimental:feature/cpu-ep-inter-process` HEAD `8cb04da9d` — includes CPU2 mbind kill-switch (`af2e45de4`) + CPU1 P1.3 per-region mbind fix (`8cb04da9d`)
- `epyc-root:main` HEAD `4a59ad5` — all P1-P4 progress + handoffs

## What this session is NOT doing

- NOT shipping v5 yet (user direction: exhaust ALL CPU optimization tracks first)
- NOT touching orchestrator (Phase L blocked behind everything else)
- NOT testing other quant types beyond what's already in production lineup

## Key memory references for post-reboot agent

- `feedback_canonical_baseline_protocol.md` — `taskset -c 0-95 -t 96 -fa 1` + zombie check + 460 GB/s aggregate BW reference
- `feedback_llama_bench_fa_default.md` — ALWAYS pass `-fa 1` explicitly (default is 0)
- `feedback_never_pipe_llama_output.md` — never pipe llama-cli output through grep/tail; use file redirection
- `project_cpu_optimization_priorities_2026_04.md` — strategic context

## Critical paths for post-reboot quick-start

```bash
# 1. Verify state
numactl --hardware | head
cd /mnt/raid0/llm/llama.cpp-experimental && git rev-parse --short HEAD  # expect 8cb04da9d
pgrep -af "llama" | grep -v "grep\|zsh\|docker"

# 2. Canonical baseline on Coder-30B (smoke test, ~1 min)
LD_LIBRARY_PATH=/mnt/raid0/llm/llama.cpp-experimental/build/bin:/opt/AMD/aocc-compiler-5.0.0/lib \
  taskset -c 0-95 ./build/bin/llama-bench \
  -m /mnt/raid0/llm/lmstudio/models/lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf \
  -t 96 -fa 1 -p 0 -n 32 -r 2

# 3. Compare to snapshot reference 43.57 ± 0.10 — if within ±2%, system OK
```
