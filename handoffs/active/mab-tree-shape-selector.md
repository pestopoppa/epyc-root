# Handoff: MAB Tree-Shape Selector for Heap-Spec

**Status**: Phase 0 falsification scheduled. Source: intake-491 (Mamba Drafters, EMNLP'25 Findings, §3.2).
**Created**: 2026-04-28
**Sibling tracks (orthogonal layers, may compound)**:
- [`moe-spec-cpu-spec-dec-integration.md`](moe-spec-cpu-spec-dec-integration.md) — verification-batch expert budgeting (already deployable on REAP-246B B=40)
- [`moe-dynamic-expert-selection.md`](moe-dynamic-expert-selection.md) — per-token dynamic K (Phase 0 entropy probe queued in agent's Phase 3 queue)
- This handoff — tree-topology axis (NEW)

**Pre-production push gate**: Phase 0 GO/NO-GO verdict required before MoE-Spec Phase 3 follow-up "production registry integration with per-role binary_path + per-role moe_spec_budget" lands in `model_registry.yaml`. See [`moe-spec-cpu-spec-dec-integration.md`](moe-spec-cpu-spec-dec-integration.md) gate blockquote at top.

**Categories**: speculative_decoding, moe_optimization, inference_serving
**Workstream**: Inference Acceleration → Algorithmic Spec-Dec
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md) Reopened Tracks section

---

## Premise

Mamba Drafters (Choi et al., EMNLP'25 Findings) §3.2 reports a multi-armed-bandit tree-shape selector that picks adaptively from a fixed pool of tree shapes. Reported on Pythia-6.9B with sampling decoding:

| Shape | Throughput (t/s) |
|---|---|
| sequential (linear) | 112.69 |
| (3,2,2,1,1) | 127.37 |
| (3,3,2,1) | 124.99 |
| (2,2,2,1,1,1) | 124.37 |
| **MAB-optimized** | **138.22** |

MAB beats sequential by **+22.65%** and beats the best fixed tree by **+8.5%**. The MAB arms are the fixed shape candidates; the reward signal is acceptance-length-per-draft-cycle (or equivalent throughput proxy).

This is a draft-loop tree-control mechanism orthogonal to:
- **Expert budgeting** (MoE-Spec): chooses which experts to compute inside a verification batch.
- **Per-token dynamic K** (moe-dynamic-expert-selection): chooses how many experts to compute per individual token.
- **Tree topology** (this handoff): chooses the shape of the speculation tree itself.

All three could in principle compound; verification of compounding is in Phase 2.

## Why the Amdahl ceiling from MoE-Spec applies here too

The autonomous CPU-optimization agent's Phase 2 v5 PGO end-to-end measurement (2026-04-28 evening) found that MoE-Spec gain attenuates **significantly** end-to-end vs forward-pass:

| Model | pp32 forward-pass | end-to-end llama-server |
|---|---|---|
| REAP-246B B=40 | +13.5% | +3% |
| Coder-30B B=64 | parity / wildly variable | +9% |

Cause: spec-dec round = drafter forward + target verification + accept-evaluation. MoE-Spec only accelerates the target verification step. Drafter and accept-evaluation are unchanged.

**The MAB selector likewise only changes the target verification step** (the tree topology determines the shape of the verification batch). Therefore the MAB selector inherits the same Amdahl ceiling. **Phase 0 must measure end-to-end** (not just forward-pass) on at least one prompt mix to establish the real ceiling.

This is a NEW gate criterion. Past tree-spec evaluation in our stack measured forward-pass behavior (per `tree-speculation-numa-drafting.md` completed handoff) — Phase 0 here corrects that measurement methodology gap.

---

## Phase 0 — Falsification probe spec

### Step 0.1 — Read intake-491 §3.2 + §4 (~30 min)

- Extract MAB arm definitions: enumerate the candidate tree shapes the paper uses
- Extract reward signal: accept_len/draft_len? throughput proxy? cold-start protocol?
- Extract update rule: UCB1, ε-greedy, Thompson sampling?
- Capture cold-start cost: how many decode rounds before policy converges?

### Step 0.2 — Trace existing heap-spec tree shape control (~1 hour)

Files of interest in `/mnt/raid0/llm/llama.cpp-experimental/`:
- `common/speculative.cpp` — DySpec implementation (heap-spec) approximately lines 1137-1300; identify where tree shape is constructed
- `common/speculative.h` — `common_speculative_state_tree` struct (around line 988 per audit)
- `common/arg.cpp` — `--draft-max`, `--draft-p-min`, `--draft-p-split` flag parsing
- `tools/server/server-context.cpp` — verification loop callsite

Goal: list 3-5 concrete insertion points where a per-decode-round arm-pull could replace the current fixed-shape construction.

### Step 0.3 — Single-config dry run with one fixed paper tree shape (~3h benchmark)

Pick the simplest paper tree shape (e.g., `(3,2,2,1,1)`). Run on:
- **Coder-30B Q4_K_M** at `--p-split 0.05` with selected fixed shape vs current `p_split=0` baseline
- **REAP-246B Q4_K_M** at `--p-split 0.05` with selected fixed shape vs current `p_split=0` baseline

For each: 5-rep proper canonical (`taskset -c 0-95 -t 96 -fa 1 --mmap 0` + `numactl --interleave=all`), build = v5 PGO at `/mnt/raid0/llm/llama.cpp-experimental/build_v5_pgo_use/`.

Both **pp32 forward-pass** AND **end-to-end via llama-server** (3 prompts × 3 reps minimum). Use same prompt set as MoE-Spec Phase 2 measurement for direct comparability.

### Step 0.4 — Phase 1 prototype scope estimate (~30 min)

LOC estimate, wall-clock estimate, risk assessment for the implementation files listed in Phase 1 below.

---

## Phase 0 GATE

**PROCEED to Phase 1** iff: ≥0% on at least one of (Coder-30B, REAP-246B) at the chosen fixed paper-shape vs current `p_split=0` baseline, BOTH in pp32 forward-pass AND end-to-end llama-server.

**CLOSE via test** iff: <0% on both pp32 AND end-to-end on both Coder-30B AND REAP-246B. Closure is scoped to:
> "intake-491 paper tree shape `(3,2,2,1,1)` on heap-spec at `--p-split 0.05` regresses on Coder-30B Q4_K_M and REAP-246B Q4_K_M under v5 PGO build, both pp32 and end-to-end. The paper's tree mechanism is GPU-EAGLE-3-bound and does not translate to CPU heap-spec at our threading regime. MAB selector is unlikely to recover headroom not present in the best fixed paper-shape."

**Does NOT generalize to**: "all tree-shape selectors are dead on CPU". A different arm pool (e.g., shapes selected via offline EAGLE-3 distillation on our targets) could still be tested in a separate falsification probe. This closure is scoped to the intake-491 paper-shape pool.

CPU20 7-artifact bundle path: `data/cpu_optimization/2026-04-2X-mab-tree-selector-phase-0/` with README.md, system-state.txt, process-pre.txt, process-post.txt, ld_debug.txt, results.csv (5-rep × {linear, paper-shape} × {pp32, end-to-end} × {Coder, REAP}), decision.md.

---

## Phase 1 — Implementation sketch (deferred behind Phase 0 gate)

### Files (in `/mnt/raid0/llm/llama.cpp-experimental/`)

| File | LOC | Change |
|---|---|---|
| `common/speculative.h` | +15 | `common_speculative_mab_config` struct (arms[], reward_decay, ucb_c) |
| `common/speculative.cpp` | +180 | New `struct common_speculative_state_mab` mirroring existing `common_speculative_state_tree` (~line 988). UCB1 arm-pull replaces fixed `draft_max`/`p_split` for the tree state path. Reward = accept_len/draft_len per round. |
| `common/arg.cpp` | +25 | `--draft-mab` bool, `--draft-mab-arms` CSV "B:D" pairs, `--draft-mab-decay` float. Mirror env vars `LLAMA_ARG_DRAFT_MAB*`. |
| `common/common.{h,cpp}` | +15 | `common_params_speculative` plumbing |
| `tools/llama-bench/llama-bench.cpp` | +10 | Env-var fallback (mirrors MoE-Spec Phase 1 plumbing pattern) |
| **Total** | **~245 LOC** | matches MoE-Spec Phase 1 plumbing footprint (~38 plumbing + ~30 mechanism) |

### Implementation sketch

```cpp
// common/speculative.h
struct common_speculative_mab_arm {
    int draft_max;     // B
    int draft_depth;   // D
};
struct common_speculative_mab_config {
    std::vector<common_speculative_mab_arm> arms;
    float reward_decay;  // EMA decay for arm reward estimates
    float ucb_c;         // UCB1 exploration coefficient
};

// common/speculative.cpp
struct common_speculative_state_mab : public common_speculative_state {
    common_speculative_mab_config cfg;
    std::vector<float> arm_reward_ema;  // exponential moving avg of accept_len/draft_len per arm
    std::vector<int>   arm_pull_count;
    int round_count = 0;
    int last_arm = 0;
};

int common_speculative_mab_pull(common_speculative_state_mab & s) {
    // UCB1 arm pull
    int best = 0;
    float best_score = -INFINITY;
    for (size_t i = 0; i < s.cfg.arms.size(); i++) {
        if (s.arm_pull_count[i] == 0) return i;  // explore unpulled arms first
        float exploit = s.arm_reward_ema[i];
        float explore = s.cfg.ucb_c * std::sqrt(std::log(s.round_count) / s.arm_pull_count[i]);
        float score = exploit + explore;
        if (score > best_score) { best = i; best_score = score; }
    }
    return best;
}
```

---

## Phase 2 — Measurement matrix

5-rep proper canonical: `taskset -c 0-95 -t 96 -fa 1 --mmap 0` + `numactl --interleave=all`.
Build: v5 PGO (`/mnt/raid0/llm/llama.cpp-experimental/build_v5_pgo_use/`).
Shapes: `linear` (existing `p_split=0`) | `paper-fixed` (best from Phase 0) | `MAB` (this implementation).
MoE-Spec budget interaction: `--moe-spec-budget {0, 64 (Coder), 40 (REAP)}` per role.
Prompts: same set as MoE-Spec Phase 2 end-to-end.
Reps: 5 minimum, 10 if absolute deltas <2%.

---

## Phase 2 binding gates

1. **Throughput**: ≥3% over best-of {linear, paper-fixed} on at least one model **end-to-end** (not forward-pass-only — Amdahl ceiling enforced per the parallel agent's Phase 2 finding).
2. **Quality**: bit-exact (structural property of standard rejection-sampling spec-dec).
3. **Stability**: 5-min sustained run; arm-distribution entropy non-increasing in last 30s of run (policy converged).
4. **Compounding with MoE-Spec**: at production budgets (REAP=40 deployable, Coder=marginal/disabled per parallel agent's verdict), MAB selector adds ≥0% (no regression).

If gate (1) met but (4) not met: deploy MAB selector at `moe_spec_budget=0` only; document interaction asymmetry.

---

## Phase 3 — Production decision

Standard production registry integration:
- Add `--draft-mab` + `--draft-mab-arms` to per-role launch flags in `model_registry.yaml`
- Document in [`inference-acceleration-index.md`](inference-acceleration-index.md) Reopened Tracks
- Update production progress logs

---

## CPU20 artifact bundle spec

Per phase: `data/cpu_optimization/2026-04-2X-mab-tree-selector-phase-{0,1,2}/`:
- `README.md` — phase purpose, hypothesis, gate criteria
- `system-state.txt` — `numactl --hardware`, `nproc`, `head /proc/cpuinfo`, kernel cmdline
- `process-pre.txt` / `process-post.txt` — `ps -ef`, `numastat -p $(pidof llama-server)` if running
- `ld_debug.txt` — `LD_DEBUG=files` capture for libomp identity confirmation
- `results.csv` — 5-rep × shape × {pp32, end-to-end} × {Coder, REAP} × {budget=0, budget=production} structured table
- `decision.md` — gate met/unmet, GO/NO-GO with measured numbers and which gate dominated

Phase 0 bundle is mandatory.

---

## Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Paper's MAB arms are tuned for Pythia-6.9B + sampling; transfer to Coder/REAP with greedy/low-temp may be poor | MEDIUM | Phase 0 falsifies cheaply on a single fixed shape; if all paper-shapes regress, close via test scoped to paper-shape pool |
| Cold-start cost dominates on short generations (≤32 tokens) | MEDIUM | Phase 2 measures both pp32 and longer end-to-end; document cold-start asymmetry if material |
| Compounding with MoE-Spec: mask interaction unknown | LOW | Phase 2 explicitly tests `moe_spec_budget × MAB shape` 2D matrix at production budgets |
| llama-bench separate-arg-parser plumbing duplicates MoE-Spec Phase 1 footprint | LOW | Mirror existing `LLAMA_ARG_MOE_SPEC_BUDGET` pattern; ~10 LOC |
| End-to-end measurement noise (system load, megasync, etc.) — parallel agent's Phase 2 Coder result was ±wildly variable | HIGH | Run during quiet system; 10 reps minimum if Phase 2 absolute deltas <2%; CPU20 process-state capture before/after |

---

## Sources

- intake-491: Choi et al., "Mamba Drafters for Speculative Decoding", EMNLP 2025 Findings, [arxiv:2506.01206](https://arxiv.org/abs/2506.01206), §3.2 MAB tree-shape selector
- Sibling handoff: [`moe-spec-cpu-spec-dec-integration.md`](moe-spec-cpu-spec-dec-integration.md) (verification-budget axis, Phase 1+2 deployable on REAP)
- Sibling handoff: [`moe-dynamic-expert-selection.md`](moe-dynamic-expert-selection.md) (per-token dynamic K, Phase 0 entropy probe queued)
- Reference: [`research/intake_index.yaml`](../../research/intake_index.yaml) intake-491 entry with MAB results table
- Closure-inflation policy: `feedback_closure_inflation.md` (memory) — bind closures to scoped enumeration
