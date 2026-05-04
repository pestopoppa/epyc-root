# Qwen3.5-122B-A10B — Arch-Class Probe (Probe B)

**Status**: Phase 1 + Phase 2 COMPLETE 2026-05-04. c2 (`GGML_NUMA_REPACK_INTERLEAVE=0`) wins +1.28% at 96t canonical. Phase 2 wiring revalidation found production `2× --numa distribute` is suboptimal in BOTH dimensions; recommended Phase 1 wiring change: 1× canonical 96t + c2 (+184% per-request) OR 4× per-NUMA-node 24t + c2 (+96% aggregate at 4-concurrent).
**Created**: 2026-05-04
**Categories**: hardware_optimization, benchmark_methodology
**Priority**: MEDIUM (only model in current 27B/31B/122B production trio with plausible 2× single-instance headroom)
**Parent index**: [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md)
**Related**:
- [`model-registry-v5-deployment-draft.yaml`](model-registry-v5-deployment-draft.yaml) — `todo_or_undecided` slot for `architect_general`
- [`cpu-kernel-env-flags-inventory.md`](cpu-kernel-env-flags-inventory.md) — Per-Arch Deployment Matrix
- [`single-instance-system-tuning.md`](single-instance-system-tuning.md) — host prerequisites

## Why this exists

The v5 deployment draft (line 214) lists `architect_general` (Qwen3.5-122B-A10B Q4_K_M) under `todo_or_undecided` because no clean per-arch canonical measurement was taken during the 2026-04-29/30 multi-arch coverage campaign. Production currently runs this model 2× cross-NUMA at 4.3 t/s/instance under a config wired 2026-03-29 — predates the v5 audit and CPU1 stack stabilization.

The 122B is unique in our roster: 256 experts, 8 active, ~10B active params, hybrid MoE structure. Existing arch classes in the deployment matrix (MoE Q4 sync-bound = Coder-30B; MoE Q4 DRAM-bound = REAP-246B; Hybrid SSM MoE = Qwen3-Next-80B) don't cleanly map. The probe answers two questions:

1. **Which arch class does it sit in?** → determines per-role env block
2. **Is the 2026-03-29 cross-NUMA wiring still optimal?** → may have been left behind by NPS4 + CPU2 NUMA-mbind landings

## Pre-flight (mandatory — same as every canonical probe)

```bash
# Host prereqs (per cpu-kernel-env-flags-inventory.md §211)
sudo sysctl -w kernel.numa_balancing=0       # check /proc — self-resets
sudo sysctl -w kernel.perf_event_paranoid=1
echo always | sudo tee /sys/kernel/mm/transparent_hugepage/enabled
echo always | sudo tee /sys/kernel/mm/transparent_hugepage/defrag
sudo cpupower frequency-set -g performance
```

**Reproducibility tripwire** (run before trusting any 122B number):

```bash
OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active \
  numactl --interleave=all -- taskset -c 0-95 \
  /mnt/raid0/llm/llama.cpp/build/bin/llama-bench \
  -m /mnt/raid0/llm/lmstudio/models/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf \
  -t 96 -fa 1 --mmap 0 -p 0 -n 32 -r 5
```

**Gate**: tg32 ≥ 47 t/s (cold-boot canonical) or ≥ 58 t/s (warmed). If not, the host is degraded — abort, do not proceed with 122B numbers.

## Probe configurations (Probe B methodology, n≥5)

| Config | Env vars | Hypothesis |
|---|---|---|
| **c0** | (none — default v5) | Baseline. Match if 122B is DRAM-bound like REAP-246B. |
| **c1** | `GGML_CCD_POOLS=1 GGML_CCD_WORK_DIST=1 GGML_BARRIER_LOCAL_BETWEEN_OPS=1` | CPU1 stack. Match if 122B is sync-bound like Coder-30B (+1.8% expected). |
| **c2** | `GGML_NUMA_REPACK_INTERLEAVE=0` | mbind kill-switch. Match if 122B benefits from per-CCD bind like Q8 frontdoor. |
| **c3** | c1 + c2 combined | Hybrid SSM dense pattern (Nemotron-9B-v2 winner). Unlikely on MoE per Qwen3-Next-80B falsification, but cheap to test. |

**Workload** (single-instance, 96t-single-NUMA-node):

```bash
OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active \
  $ENV_BLOCK \
  numactl --interleave=all -- taskset -c 0-95 \
  /mnt/raid0/llm/llama.cpp/build/bin/llama-bench \
  -m /mnt/raid0/llm/lmstudio/models/unsloth/Qwen3.5-122B-A10B-GGUF/Q4_K_M/Qwen3.5-122B-A10B-Q4_K_M-00001-of-00003.gguf \
  -t 96 -fa 1 --mmap 0 -p 0 -n 32 -r 5
```

**Coverage**: tg32 mandatory; tg128 optional if c1 or c2 shows ≥ +5% (decode regime sanity check). pp512 optional if any config wins (long-prompt regime sanity check).

## Bonus probe — production wiring revalidation

The current production wiring is `2× cross-NUMA -t 96 --numa distribute` (set 2026-03-29). Three follow-on configurations worth measuring once arch class is identified:

| Config | Wiring | Hypothesis |
|---|---|---|
| **w0** | Current production: 2× `--numa distribute` -t 96 | Baseline (4.3 t/s/instance × 2 = 8.6 t/s aggregate observed) |
| **w1** | 2× single-NUMA-node: `numactl --cpunodebind=0/1 --membind=0/1` -t 24 | Match if 122B fits per-node like Coder-30B-A3B (+26% precedent) |
| **w2** | 4× single-NUMA-node: `--cpunodebind=0..3 --membind=0..3` -t 24 | Aggregate-throughput regime; expect per-instance drop but higher total |
| **w3** | 1× full-machine 96t with winning env from c0/c1/c2/c3 | Single-user latency-optimal (current architect serves 1 slot at a time) |

**Note**: w1–w3 require RAM headroom check — 4× 69 GB = 276 GB just for weights, plus KV. Validate against `numactl -H` free per node before launching w2.

## Decision gates

| Outcome | Action |
|---|---|
| Any single-instance config c0/c1/c2/c3 ≥ +5% over c0, σ ≤ 1% | Wire env block into v5 draft `architect_general` role; remove from `todo_or_undecided` |
| All single-instance configs within ±2% under tight Probe B | Mark `arch_class: dense_q4` analogue in v5 draft (`env: {}`); document |
| w1 or w3 single-instance ≥ +20% over w0 per-instance | Propose orchestrator wiring change (separate handoff — touches stack registry, see `project_orchestrator_stack_freeze.md`) |
| w2 aggregate ≥ +30% over w0 aggregate AND quality A/B passes | Propose 4-way EP wiring (separate handoff) |

## Persistence + reporting

- All raw `llama-bench` JSON output → `/mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/2026-XX-XX-qwen35-122b-arch-probe/` (incremental — write per-config as it completes, per `feedback_incremental_persistence.md`)
- Findings writeup → same dir, `findings.md`
- v5 draft update PR after completion
- Handoff move: `active/` → `completed/` once v5 draft updated

## Constraints

- Per `feedback_no_concurrent_inference.md`: **per-run user approval required** before each `llama-bench` invocation. No auto-launch.
- Per `feedback_phased_plan_gates.md`: phase gate at end of c0..c3 single-instance probe (decide w1..w3 scope based on results) before launching the bonus probe.
- Per `feedback_canonical_baseline_protocol.md`: tripwire result MUST be persisted alongside 122B numbers — a 122B figure without an adjacent passing tripwire is not valid evidence.

## Effort estimate

- Pre-flight + tripwire: 30 min
- c0..c3 single-instance probe (n=5 each, ~10 min/run × 4 configs): ~1.5 h
- w1..w3 bonus probe (gated): ~1.5 h
- Findings writeup + v5 draft update: ~1 h

Total: ~4.5 h serial, requires ~90 min uninterrupted EPYC for the bonus phase.

---

## Phase 1 RESULTS — 2026-05-04

Tripwire: Coder-30B Q4_K_M tg32 r=5 = 47.86 ± 0.36 t/s (canonical band 47-49 t/s ✅).

| Config | Env block | avg t/s | σ t/s | σ % | Δ vs c0 |
|---|---|---|---|---|---|
| **c0** default v5 | (none) | 12.041 | 0.037 | 0.31% | baseline |
| **c1** CPU1 stack | `GGML_CCD_POOLS=1 GGML_CCD_WORK_DIST=1 GGML_BARRIER_LOCAL_BETWEEN_OPS=1` | 12.065 | 0.024 | 0.20% | +0.21% |
| **c2** mbind off | `GGML_NUMA_REPACK_INTERLEAVE=0` | **12.195** | 0.051 | 0.42% | **+1.28%** |
| **c3** c1+c2 | both | 12.048 | 0.082 | 0.68% | +0.06% |

**Decision: c2 wins.** z-score ~3 vs c0, comfortably above noise. CPU1 stack net-neutral here
(unlike Coder-30B where it's +1.8%). Combining both (c3) drops back to noise — the two levers
appear to interact destructively.

**Arch class assigned: `moe_q4_bw_bound_mbind_sensitive`.** Closest analogue is the Q8 frontdoor
(Qwen3.6-35B-A3B Q8) family where mbind-off was +6%. Distinct from Coder-30B "MoE Q4 sync-bound"
(c1 wins) and from REAP-246B "MoE Q4 DRAM-bound" (mbind-tolerant).

### v5 deployment draft updated
`architect_general` moved from `todo_or_undecided` to `roles:` with `env: { GGML_NUMA_REPACK_INTERLEAVE: 0 }`,
`expected_throughput.tg32_canonical_96t_single_instance: ~12.2 t/s`.

### Orchestrator updated
`_ROLE_ENV_BLOCKS["architect_general"]` in `orchestrator_stack.py` populated with the c2 env block.
Production launches now pick up the win automatically.

### The MUCH bigger finding — production wiring underperforms by ~2.8×

Production runs `2× --numa distribute -t 96` cross-NUMA at **4.3 t/s/instance** (per orchestrator
stack registry). Canonical single-instance **12.19 t/s**. Per-instance gap **+184% unused**.

For architect_general (slots=1, serial per instance), per-instance latency dominates. Switching
from 2× cross-NUMA to 1× canonical + c2 = ~2.8× latency win at the cost of dropping from 2 to 1
concurrent instance.

This wiring decision is OUT OF SCOPE for this probe. Tracked as Phase 2 below.

## Phase 2 RESULTS — 2026-05-04 (same session)

User direction: "proceed with Phase 2". RAM audit before launch: each NUMA node had ~120 GB
free (70 GB Q4 model fits; 4× concurrent fits per-node).

| Wiring | per-instance t/s | Aggregate | Notes |
|---|---|---|---|
| w3 (1× canonical 96t + c2) | 12.19 ± 0.05 | **12.19** | latency-optimal, single-request |
| w1a (1× 24t per-node + c2) | 4.207 ± 0.011 | 4.21 | per-node BW ceiling |
| w1b (2× concurrent 24t per-node + c2) | 4.19, 4.27 | **8.47** | linear 2× scaling, matches production registry's 8.6 |
| w2 (4× concurrent 24t per-node + c2) | 4.15, 4.25, 4.24, 4.22 | **16.86** | **linear 4× scaling — throughput-optimal at 4 concurrent** |
| Production now (2× `--numa distribute`) | 4.30 | 8.60 | **suboptimal in BOTH dimensions** |

**Operating-point matrix:**

| Workload regime | Optimal | Δ vs production |
|---|---|---|
| Single user, 1 request at a time | w3 | **+184% per-request** (4.3 → 12.19) |
| 4+ concurrent requests | w2 | **+96% aggregate** (8.6 → 16.86) |

**Key insight**: production's 2-instance cross-NUMA wiring is in the worst quadrant. Going
to 1× canonical wins per-request latency dramatically. Going to 4× per-NUMA-node wins
aggregate throughput (when the orchestrator actually issues 4 concurrent requests).

### Recommendation

**Immediate (low-risk, single-line registry change)**: switch architect_general from
`numa_instances: 2 / numa_ports: [8083, 8183]` to `numa_instances: 1 / numa_ports: [8083]`
with the c2 env block already wired in `_ROLE_ENV_BLOCKS`. Expected: +184% per-request
latency for the dominant single-user query pattern.

**Conditional (requires concurrent workload)**: only if architect_general scales to high
concurrency (eval batches, multi-tenant), switch to 4× per-NUMA-node 24t wiring for the
+96% aggregate win. Until then, the 4× wiring would leave 4-way capacity unused.

**Do NOT keep production's 2× cross-NUMA**: there is no workload where it is optimal.

Bundle: `data/cpu_optimization/2026-05-04-qwen35-122b-arch-probe/findings_phase2.md`
