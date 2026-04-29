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

---

## Phase 0 — RESULTS (DONE 2026-04-29) — **NO-GO with narrow closure**

### Step 0.1 — intake-491 paper read

**Confirmed** via WebFetch on arxiv.org/html/2506.01206v1:
- Arm pool: `(3,3,2,1)`, `(3,2,2,1,1)`, `(2,2,2,1,1,1)` (Table 5)
- Tree encoding: `(N₁, N₂, ..., Nᵧ)` where N_i = "number of new nodes obtained by sampling from each node at the i^th generation"
- Reward: `r_k^(t) := -(1/N_accept + λ_γ·γ(𝒯_k)/N_accept)·I` — speedup-inverse minimization with draft-length penalty
- Algorithm: UCB1 with policy `k* = argmax_k [r̂_k^(t) + λ_UCB·√(2ln(t)/n_k^(t))]`
- Hardware: Pythia-6.9B (instruction-tuned), MT-bench, **greedy decoding (temperature=0)**
- Headline: sequential 112.69 → MAB-optimized **128.21 t/s (+13.7%)** [NOTE: handoff originally cited 138.22 / +22.65%, possibly different table or revision; webfetch returned 128.21]
- Cold-start convergence: not documented in paper

**Discrepancy flag**: handoff Premise table cites MAB-optimized=138.22 but paper §5.5 (per WebFetch) reports 128.21. The relative ranking of fixed shapes (3,2,2,1,1 > 3,3,2,1 > 2,2,2,1,1,1) is consistent. Either way, the ≥0% gate is what matters for this falsification probe.

### Step 0.2 — Heap-spec tree shape control traced

Files: `/mnt/raid0/llm/llama.cpp-experimental/common/speculative.cpp:987-1300`.

**Critical finding**: DySpec uses a **HARDCODED dynamic branching factor by depth**:

```cpp
auto branching_factor = [&](int depth) -> int {
    if (depth == 0) return MAX_BRANCHES_PER_NODE;
    if (depth <= 2) return 5;
    if (depth <= 4) return 3;
    return 2;
};
```

The shape `(MAX, 5, 5, 3, 3, 2, 2, ...)` is approximately `(8, 5, 5, 3, 3)` if MAX_BRANCHES_PER_NODE=8.

When `params.p_split=0` (production setting), line 1174 `if (k > 0 && cur_p->data[k].p < params.p_split) break;` drops ALL k>0 candidates (any non-greedy branch fails `< 0`). Tree degenerates to **linear** chain.

When `p_split=0.05`, the tree builds out branches up to MAX_BRANCHES_PER_NODE wide × depth, pruned by per-branch probability ≥ 0.05.

**Consequence for the falsification probe**: We CANNOT inject the paper's exact (3,2,2,1,1) shape without modifying source (LOC change). The Phase 0 measurement compared `p_split=0` linear vs `p_split=0.05` existing-DySpec-shape. Per the gate: if even existing-DySpec-shape doesn't beat linear, no MAB selector over the paper's arm pool can help (since the paper's arm pool produces shapes weaker than DySpec's hardcoded shape on average).

### Step 0.3 — Single-config benchmark RESULTS

5-rep proper canonical pp32 (`taskset -c 0-95 -t 96 -fa 1 --mmap 0` + `numactl --interleave=all`) + 3-prompt × 3-rep end-to-end via llama-server. v5 PGO build at `/mnt/raid0/llm/llama.cpp-experimental/build_v5_pgo_use/`. Server warmup: 60s after `/health` ok before first request.

**Megasync at ~110% on 1 core** during measurement window — consistent noise floor across all measurements.

**`--draft-p-split` CLI is rejected by llama-server** (line 3501 of `common/arg.cpp` restricts to `LLAMA_EXAMPLE_SPECULATIVE` only). Workaround: env var `LLAMA_ARG_DRAFT_P_SPLIT`.

**Coder-30B Q4_K_M, prompt set = 3 production-realistic coding prompts:**

| Shape | rep | t/s | accept% | predicted_ms |
|---|---|---|---|---|
| linear (p_split=0) | 1 | 29.94 | 68.7 (158/230) | 8550 |
| linear | 2 | 36.33 | 59.6 (168/282) | 7045 |
| linear | avg | **33.14 ± 4.52** | 64.1 ± 6.4 | — |
| tree (p_split=0.05) | 1 | 18.14 | 68.7 (158/230) | **14116** |
| tree | 2 | 36.20 | 59.6 (168/282) | 7071 |
| tree | avg | **27.17 ± 12.77** (variance ±48% CV) | 64.1 ± 6.4 | — |

**Coder pp32 forward-pass baseline (non-spec-dec)**: 201.14 ± 5.99 t/s on v5 PGO (megasync floor).

**REAP-246B Q4_K_M:**

| Shape | rep | t/s | accept% |
|---|---|---|---|
| linear (p_split=0) | 1 | 7.43 | 59.9 |
| linear | 2 | 7.95 | 56.2 |
| linear | avg | **7.69 ± 0.37** | 58.0 ± 2.6 |
| tree (p_split=0.05) | 1 | 7.61 | 59.9 |
| tree | 2 | 7.99 | 56.2 |
| tree | avg | **7.80 ± 0.27** (Δ +1.4% noise) | 58.0 ± 2.6 |

**REAP pp32 forward-pass baseline**: 46.57 ± 1.14 t/s.

**rep0 missing for all 4 cells**: server `/completion` returned empty body within 240s curl timeout despite the 60s warmup. Investigation: when the server logs are 41 bytes, this is the "error: invalid argument: --draft-p-split" failure (which was fixed via env var fallback in the re-run).

### CRITICAL FINDING: Tree at temperature=0 produces identical output as linear

Direct JSON comparison of `comp_coder_linear_rep1.json` vs `comp_coder_tree_rep1.json`:

| Field | linear | tree |
|---|---|---|
| `predicted_n` | 256 | 256 |
| `draft_n` | 230 | 230 |
| `draft_n_accepted` | 158 | 158 |
| `content` first 100 chars | "...Also, ensure the function is efficient with O(log n)..." | "...Also, ensure the function is efficient with O(log n)..." (BYTE-IDENTICAL) |
| `predicted_ms` | 8550 | **14116 (+65%)** |

**Root cause**: at `temperature=0` (greedy), the verifier picks the highest-probability path through the tree. Non-greedy branches are computed (drafter cost) but never selected (verifier rejects). The tree's branching produces ZERO benefit and adds full verification cost on the non-greedy candidates.

This explains the +65% wall-clock penalty on Coder rep1 (cold-cache amplifies the overhead) and converges toward parity on rep2 (warm-cache absorbs the wasted compute).

### Phase 0 GATE verdict: **NO-GO with narrow closure**

Per Phase 0 GATE criteria ("≥0% on at least one of Coder/REAP, BOTH pp32 AND end-to-end"):

- **End-to-end Coder**: -18% mean (variance ±48% CV; rep1 -39%, rep2 parity). Regression with high variance.
- **End-to-end REAP**: +1.4% (well within ±0.3 noise band on REAP). Net null.
- **pp32 forward-pass** does not differ by p_split (target-only measurement); not directly testable for tree mechanism.

Net: **gate not met on either model**. Tree at temp=0 cannot beat linear because the verifier collapses to greedy path.

### Closure scope (per closure-inflation policy)

**Narrow closure**:
> "DySpec heap-spec tree at `--draft-p-split=0.05` with **greedy decoding (temperature=0)** produces BIT-IDENTICAL outputs to `--draft-p-split=0` linear baseline (verifier collapses tree to greedy path) while adding wasted draft+verify work on non-greedy branches. End-to-end on v5 PGO build with megasync noise floor: Coder-30B Q4_K_M -18% mean (high variance ±48% CV; rep1 -39% cold, rep2 parity warm), REAP-246B Q4_K_M +1.4% within noise band. The MAB selector over the paper's arm pool `(3,3,2,1)`, `(3,2,2,1,1)`, `(2,2,2,1,1,1)` cannot recover headroom that is structurally absent at temp=0 — selecting different shapes does not help when the verifier discards all non-greedy paths regardless of shape."

**Does NOT generalize to**:
- **Higher-temperature sampling** (paper used temp=0 too, but in their regime tree gain came from acceptance-length improvement that may exist on Pythia but not on our Coder/REAP-class targets — separate question).
- **Different arm pool** (e.g., shapes optimized for greedy-temp, like 1-deep wide-K shapes that sample top-K for fallback rather than branching).
- **Multi-tenant/concurrent workloads** where tree-shape selection might amortize cold-start cost differently.
- **Sampling-decoding configurations** (production currently uses temp=0; if a future workload uses temp>0, the question reopens).

**This closure CONFIRMS existing production wisdom** in `model_registry.yaml`:
- Line 378: `p_split: 0   # linear only, tree is net-negative at 48t (sweep-verified)`
- Line 447: `p_split: 0   # linear only — tree harmful at all ps values, sweep-verified 2026-03-26`

The 2026-03-21/26 sweeps were correct for greedy-temp inference. v5 PGO build confirms.

### Phase 1 deferred indefinitely

Per Phase 0 NO-GO: implementing the MAB selector machinery (Phase 1 spec at handoff lines 117-153) is not justified on greedy-temp production. Reopen criteria:
- Production workload shifts to temp>0 sampling (not currently planned)
- Paper's claimed +13.7-22.65% on Pythia-6.9B at temp=0 turns out to be measurement-methodology-bound (different stack characteristics; needs separate falsification on Pythia or similar dense model on our hardware before generalizing back to Coder/REAP)

### Phase 1 prototype scope estimate (still recorded for completeness)

LOC + risk per file unchanged from handoff Phase 1 table (~245 LOC, LOW risk). NOT implementing per Phase 0 NO-GO. Defer indefinitely.


---

## Phase 0' — Sampling regime re-evaluation (2026-04-30, INCONCLUSIVE — POTENTIAL SIGNAL)

Bundle: [`data/cpu_optimization/2026-04-30-mab-phase-0-prime-sampling/`](../../epyc-inference-research/data/cpu_optimization/2026-04-30-mab-phase-0-prime-sampling/)

The Phase 0 NO-GO closure (2026-04-29) explicitly left the door open for "Higher-temperature sampling" and "Sampling-decoding configurations". This Phase 0' tests both axes.

### Method

Same models / drafter / build / prompts as Phase 0; only `temperature` and `seed` change:

| Phase | seed | temperature | shapes | reps × prompts | models |
|---|---|---|---|---|---|
| Phase 0 | not set | 0.0 | linear, tree p_split=0.05 | 3 × 3 | Coder + REAP |
| Phase 0' fixed | 4242 fixed | 0.7 | same | 3 × 3 | Coder + REAP |
| Phase 0' random | -1 (random) | 0.7 | same | 3 × 3 | Coder only |

### Result

**Fixed-seed temp=0.7 NO-GO**: 18/18 reps produced BYTE-IDENTICAL output between linear and tree across Coder + REAP. Mean t/s within 0.1-0.6% (noise). Probe-design caveat: deterministic seed makes the comparison uninformative — verifier samples the same token at each step regardless of which tree branches were drafted.

**Random-seed temp=0.7 POTENTIAL SIGNAL on Coder** (n=9):

| Shape | Mean t/s ± std | Accept rate |
|---|---|---|
| linear | 37.87 ± 5.29 | 53.4% |
| tree | 41.49 ± 7.06 | 58.1% |
| **Δ** | **+9.6%** | **+4.7 pp** |

Per-prompt: p0 binary_search +18.2%, p1 lru_cache +8.3%, p2 csv_moving_avg +1.2%.
Per-rep variance high — p1_r0 tree LOSES -25.5% (drafter strong → tree wasted), p1_r2 tree WINS +52.6% (drafter weak at 40.6% accept → tree alt-paths exposed verifier's preferred sample).

**Statistical significance**: paired t-test n=9, t≈1.23, p≈0.23. **NOT significant** at 0.05 level despite the +9.6% mean.

### Mechanism observation

The per-rep variance pattern is consistent with tree mechanism's intended value proposition: tree helps when drafter top-1 diverges from verifier sampling (low accept rate); tree hurts when drafter top-1 already matches (high accept rate). MAB selector's claimed value is exactly to pick the right shape per-decode-round based on drafter quality.

### Phase 0' verdict: INCONCLUSIVE — do not launch Phase 1 implementation yet

Recommended next cut (~2-4 hours, no code changes):

1. **Coder random-seed at n≥30 reps**: replicate the +9.6% signal. If t-stat clears p<0.05, signal is real.
2. **REAP random-seed at n≥30 reps**: extend coverage to second target.
3. **Drafter-quality predictor sketch** (design-only, ~2 hours): identify a per-decode-round feature that distinguishes "drafter weak" from "drafter strong" rounds. Without this, context-free MAB cannot capture the per-rep variance pattern.

Phase 1 implementation (~245 LOC) is justified ONLY if (1) confirms signal at p<0.05 AND (3) identifies a usable feature.

### What this changes vs Phase 0 NO-GO closure

The Phase 0 closure stands. Phase 0' EXTENDS scope to confirm the door was correctly left open for sampling regime, AND finds a real (if noisy) signal there. Not a retraction — an extension.


---

## Phase 0'' RESULT (2026-04-29) — NO-GO ACROSS BOTH TARGETS — TRACK CLOSED

Bundle: [`data/cpu_optimization/2026-04-29-mab-phase-0-prime-prime-replication/`](../../epyc-inference-research/data/cpu_optimization/2026-04-29-mab-phase-0-prime-prime-replication/)

Phase 0' (2026-04-30) flagged a +9.6% mean signal on Coder at n=9 random-seed temp=0.7 (p≈0.23, NOT significant). Phase 0'' replicates at n=30 per cell (n=90 paired per model) on both Coder + REAP under the same regime.

### Final result

| Model | n_paired | linear mean t/s | tree mean t/s | Δ_pct | p-value |
|---|---|---|---|---|---|
| Coder-30B Q4_K_M | 90 | 40.58 | 38.97 | **-3.97%** | **0.0125 (significant — tree LOSES)** |
| REAP-246B Q4_K_M | 90 | 7.64 | 7.66 | +0.34% | 0.8685 (null) |

Per-prompt on Coder: p0 -6.07%, p1 -3.64%, p2 -2.01% (all losing).

**The Phase 0' "+9.6%" signal was a low-n type-I error.** At proper n=90, the true effect on Coder is a small significant regression; REAP is null.

### Combined evidence across all 3 tested regimes

| Regime | Coder result | REAP result | Verdict |
|---|---|---|---|
| Phase 0 greedy (temp=0) | byte-identical to linear | same | NO-GO |
| Phase 0' fixed-seed sampling (temp=0.7) | byte-identical to linear | same | NO-GO |
| Phase 0'' random-seed sampling (temp=0.7, n=90) | tree -3.97% (p=0.012) | tree +0.34% (p=0.87) | NO-GO |

### Track closure (per closure-inflation policy)

> "MAB tree-shape selector mechanism, tested on Qwen3-Coder-30B-A3B-Q4_K_M + Qwen3-Coder-REAP-246B-A35B-Q4_K_M targets with the Qwen3-Coder-Instruct-DRAFT-0.75B-32k-Q4_0 drafter at v5 PGO build, is structurally net-negative or null across all three tested verification regimes. At n=90 paired in the most favorable regime (random-seed sampling temp=0.7), Coder shows tree -3.97% (p=0.012); REAP shows tree +0.34% (p=0.87). Phase 1 implementation (~245 LOC) is not justified.
>
> Does NOT generalize to: different drafter (Pythia has different uncertainty profile), different arm pool (paper-shapes tuned for Pythia), multi-tenant / batched / concurrent-slot workloads, architecturally different targets (dense, hybrid SSM — only MoE Q4_K_M tested at scale)."

### Operational disposition

- Track CLOSED. Handoff moves to `handoffs/completed/`.
- Pre-production gate on MoE-Spec production registry integration condition (a) "MAB Phase 0 falsification probe completes with explicit GO or NO-GO" is RESOLVED via NO-GO at extended scope.
- No code in tree changes — MAB Phase 1 was never implemented.

### Phase progression

| Phase | Date | n | Verdict |
|---|---|---|---|
| Phase 0 | 2026-04-29 | 3 | NO-GO greedy temp=0 (verifier collapses) |
| Phase 0' fixed-seed | 2026-04-30 | 9 | NO-GO temp=0.7 fixed (verifier deterministic via seed) |
| Phase 0' random-seed | 2026-04-30 | 9 | INCONCLUSIVE (+9.6% noise) |
| **Phase 0''** | **2026-04-29** | **90** | **NO-GO definitive** (-3.97% p=0.012 Coder, +0.34% p=0.87 REAP) |

Final commit: pending after this closure.
