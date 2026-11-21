# KPF-60-LPT-MODEL: model-free LPT cost model for segment-parallel cold prefill (MI210 + CPU quarters)

Box: KPF-60-LPT-MODEL (kv-cache-program.md). Zero inference; script `/mnt/raid0/llm/tmp/ak-kpf-out/kpf60_lpt_model.py` (stdlib, `python3 -I`). Premise: HyPIC segment-parallel cold prefill (intake-2774#record; code intake-2783#record): segments are prefilled independently on different workers, then composed `S = T_C*S_prev + S_C|0` per segment (T_C from a second identity-init GDN pass), followed by a seam-window recompute of the first w tokens of each non-first segment (HyPIC default w=8; in-house W=64) with the true composed state. Not a quality claim: the approximation is gated by KPF-62 G3 / the drift-curve gate.

## 0. Verdict

**Do NOT open an implementation box on current evidence.** The >= 20% rule cannot be met by data: the KPF-60 P0 harvested only ONE device rate for ONE role (Qwen3.8-27B Q8_0 on MI210: pp2048 839 / pp8192 788 tok/s at ub512; 919 / 867 at ub2048). The P0 `cpu_pp` stage (35B-A3B and Flash-Next on CPU) was never harvested and no CPU rate for the 27B nor GPU rate for the 35B/Flash-Next exists. With a single measured device per role there is nothing to schedule across: predicted cut = 0% (27B), k>1 on the one device is -0.2% to -3.2% from seam recompute plus compose. 35B-A3B and Flash-Next: **excluded, rates missing** (not invented).
What the model does establish (parametric requirement, section 3): a >= 20% cut needs the helper devices together to supply roughly 0.32 of the home device's prefill rate at L >= 8k with w=8 (0.31-0.33 for L 8k-32k, including overheads up to 10x), about 0.65 at w=64 and L=8k; it is overhead-insensitive at L >= 8k because seam recompute (k-1)*w tokens dominates, not transfer/compose (transfers are tens of ms against seconds of prefill). The decision therefore reduces to one measured number: the helper-to-home rate ratio rho.
Plausibility (no number invented, direction only): CPU prefill on these models is compute-bound and not near 1/3 of an MI210 on a 27B-class dense model (the DESIGN estimate for 35B CPU is ~5 ms/token, i.e. ~200 tok/s, vs 788-919 tok/s on MI210 for the 27B, but those are different models); and a 35B-A3B Q8 (about 36 GB) cannot be co-resident on the MI210 beside the resident 27B (29-31 GB VRAM peak). That makes the CPU-home / GPU-helper direction (frontdoor) structurally blocked while architect_critic is resident. Treat as a hypothesis for the missing rates to confirm or kill.

## 0.1 Missing rates and the P0 stage that supplies them (design only, nothing run)

| missing | supplying stage (existing P0 plan `p0_timing_plan.md` section 2, script `p0_timing.sh`) |
|---|---|
| 35B-A3B Q8_0 CPU pp512/2048/8192 (full host 0-95 and a 48-thread half) | `cpu_pp` (needs the quiet full-host slot; not yet harvested, kv-cache-program.md L1709) |
| Flash-Next UD-IQ4_XS CPU pp | `cpu_pp` |
| 27B Q8_0 CPU pp (needed as helper rate for the 27B role) | `cpu_pp` with `INCLUDE_27B_CPU=1` |
| 35B-A3B on MI210 pp (needed for a GPU helper of frontdoor) | `gpu_pp` with `INCLUDE_35B_GPU=1`; also needs a co-residency decision |
| half-host (2x48t) scaling vs full host | one extra `cpu_pp` row at `-t 48` (not in the current plan) |
| pp > 8192 rates (model uses the pp8192 rate for 32k, an extrapolation) | extend `cpu_pp`/`gpu_pp` with pp32768 |
| per-segment transfer and compose cost (model uses DESIGN.md 2.2 estimates) | P1 code (inject/compose latency cannot be timed before then) |
If the inference backlog supplies rho >= the section 3 value for a served role, then (and only then) open an implementation box.

## 1. Assumptions

- Roles/devices from `p0_timing_plan.md` section 2 and `stack_topology.yaml`: 27B on MI210 (:8083, architect_critic, aliases coder_escalation/ingest_long_context), 35B-A3B Q8 on CPU (frontdoor/worker_general, full 0-95 plus halves 2x48t), Flash-Next UD-IQ4_XS on CPU (architect_general :8074). GPU host threads 184-191 are not offered as CPU workers.
- Assembler (home) device = the role's served device (it will decode); non-home segments ship their attention KV (27B: 65,536 B/token f16, derived from pinned GGUF metadata) plus the dense (A,B) transition state (DESIGN.md 2.2 estimates: 27B ~100 MB, 35B ~38.5 MB, Flash-Next ~76 MB per segment) over PCIe at 28.9 GB/s (measured P0 H2D). Transfers are serialised after the makespan (conservative, no overlap).
- Compose cost per segment 1 ms (GPU) / 10 ms (CPU) (DESIGN.md 2.2 bounds). Seam recompute = (k-1)*w tokens at the home rate, on the critical path (HyPIC repairs seams with the true composed state).
- LPT on uniform machines (speeds = rates), equal segments, k in {2,3,4,8}; equal-segment granularity makes the break-even rho step-like at short L (e.g. 0.33 vs 0.65 at L=2048); finer or unequal splits would soften it.
- Helper capacity in the parametric table = 2 equal workers sharing a total rate rho*r_home (production halves); CPU workers contend for memory bandwidth, so rho is the TOTAL achievable under contention, which is the quantity to measure.
- Native-window/quality: this is a time model only. HyPIC composition is exact only at layer 0; drift at depth is the KPF-62 drift-curve gate (see DESIGN.amended.md). Approximate output needs G3; a cut that costs quality does not count.
- Rates beyond pp8192 are extrapolated (flagged `*`). Sensitivity: overhead multiplier m in {1,3,10}, seam w in {8,64,128}, ubatch 512 vs 2048 (+9.5% on the single measured device).

## 1. Rates actually available (KPF-60 P0) and what each served role gets

| role | home device | home rate (tok/s) | other-device rate | status |
|---|---|---|---|---|
| 27B  (architect_critic / coder_escalation / ingest; MI210 :8083) | mi210 | 839 (pp2048) / 788 (pp8192), ub512 | CPU **MISSING** | home-only: no second device with a rate, predicted cut = none |
| 35B-A3B  (frontdoor / worker_general; CPU 0-95 :8070 + halves) | cpu | **MISSING** | **MISSING** | EXCLUDED from the prediction table; break-even table only |
| Flash-Next UD-IQ4_XS  (architect_general; CPU 0-95 :8074) | cpu | **MISSING** | **MISSING** | EXCLUDED from the prediction table; break-even table only |

## 2. Predicted cold-TTFT change from the MEASURED rates only

A parallel schedule needs at least two devices with a measured rate for the same role. Per role:

| role | devices with measured rate | L | best k | T0 (s) | T_par (s) | predicted cut |
|---|---|---|---|---|---|---|
| 27B  (architect_critic / coder_escalation / ingest; MI210 :8083) | mi210 only | 2048 | 1 (no helper) | 2.44 | 2.44 | **0% (no second measured device; k>1 on one device is -3.2% at w=64)** |
| 27B  (architect_critic / coder_escalation / ingest; MI210 :8083) | mi210 only | 8192 | 1 (no helper) | 10.39 | 10.39 | **0% (no second measured device; k>1 on one device is -0.8% at w=64)** |
| 27B  (architect_critic / coder_escalation / ingest; MI210 :8083) | mi210 only | 32768* | 1 (no helper) | 41.58 | 41.58 | **0% (no second measured device; k>1 on one device is -0.2% at w=64)** |
| 35B-A3B  (frontdoor / worker_general; CPU 0-95 :8070 + halves) | none | 2048 | - | - | - | **excluded (home rate missing)** |
| 35B-A3B  (frontdoor / worker_general; CPU 0-95 :8070 + halves) | none | 8192 | - | - | - | **excluded (home rate missing)** |
| 35B-A3B  (frontdoor / worker_general; CPU 0-95 :8070 + halves) | none | 32768 | - | - | - | **excluded (home rate missing)** |
| Flash-Next UD-IQ4_XS  (architect_general; CPU 0-95 :8074) | none | 2048 | - | - | - | **excluded (home rate missing)** |
| Flash-Next UD-IQ4_XS  (architect_general; CPU 0-95 :8074) | none | 8192 | - | - | - | **excluded (home rate missing)** |
| Flash-Next UD-IQ4_XS  (architect_general; CPU 0-95 :8074) | none | 32768 | - | - | - | **excluded (home rate missing)** |

`*` pp>8192 reuses the pp8192 rate (extrapolation; true rate is lower, which only raises the baseline).

## 3. Requirement table (parametric, NOT a prediction): helper rate needed for a >= 20% cut

rho = total helper rate / home-device rate; helpers = 2 equal workers; best k in [2, 3, 4, 8]; 
overhead multiplier m scales transfer+compose. Cells: minimum rho ("-" = unreachable even at rho=64).

| home | L | w | m=1 | m=3 | m=10 |
|---|---|---|---|---|---|
| mi210 (xfer=27B) | 2048 | 8 | 0.327 | 0.645 | 0.691 |
| mi210 (xfer=27B) | 2048 | 64 | 0.715 | 0.728 | 0.779 |
| mi210 (xfer=27B) | 2048 | 128 | 0.825 | 0.843 | 0.913 |
| mi210 (xfer=27B) | 8192 | 8 | 0.316 | 0.318 | 0.325 |
| mi210 (xfer=27B) | 8192 | 64 | 0.645 | 0.648 | 0.656 |
| mi210 (xfer=27B) | 8192 | 128 | 0.665 | 0.670 | 0.686 |
| mi210 (xfer=27B) | 32768 | 8 | 0.314 | 0.314 | 0.317 |
| mi210 (xfer=27B) | 32768 | 64 | 0.318 | 0.319 | 0.322 |
| mi210 (xfer=27B) | 32768 | 128 | 0.324 | 0.325 | 0.328 |
| cpu (xfer=35B) | 2048 | 8 | 0.651 | 0.690 | 0.867 |
| cpu (xfer=35B) | 2048 | 64 | 0.730 | 0.778 | 1.163 |
| cpu (xfer=35B) | 2048 | 128 | 0.846 | 0.911 | 1.305 |
| cpu (xfer=35B) | 8192 | 8 | 0.319 | 0.328 | 0.674 |
| cpu (xfer=35B) | 8192 | 64 | 0.648 | 0.657 | 0.694 |
| cpu (xfer=35B) | 8192 | 128 | 0.669 | 0.679 | 0.717 |
| cpu (xfer=35B) | 32768 | 8 | 0.314 | 0.316 | 0.324 |
| cpu (xfer=35B) | 32768 | 64 | 0.319 | 0.321 | 0.329 |
| cpu (xfer=35B) | 32768 | 128 | 0.325 | 0.327 | 0.646 |

Reading: with ideal splitting and negligible overhead the cut is rho/(1+rho), so 20% needs rho >= 0.25 (helpers together at least 1/4 of the home device). 
Seam recompute (k-1)*w tokens at the home rate and compose/transfer overheads raise it; the table gives the figure per w and m.

## 4. Sensitivity of the measured 27B row to the seam/ubatch choice

Home-only baseline at ub2048 instead of ub512 changes T0 by about 9-10% (919 vs 839 tok/s at pp2048). Because no helper rate exists, the cut stays 0%.


