<!-- RATIFIED 20260730T103218Z. Annex G of MEASUREMENT.md (same trust boundary, same
     amendment rules). GPU and cross-device protocol family. -->

# Annex G — GPU & cross-device protocols

## P-GPU-1 — MI210 GPU canonical throughput (RATIFIED 2026-07-19)

*(v2 merges the v1 §1 placeholder and the v1 tail ratified block — one protocol, one location.
The placeholder's "close when MI210 hardware is acquired or permanently deferred" clause is
resolved: the MI210 is installed and serving.)*

Applies to all decision-gating GPU (MI210 / gfx90a / HIP) throughput, spec-dec, and residency
numbers. Metric direction: higher-better (t/s) unless a lower-better metric is explicitly
stated.

**Kernel-provenance rule (production-named kernels ONLY).** A P-GPU-1 decision-grade claim MAY
ONLY be produced on a **production-named kernel** (`production-consolidated-vN`; currently v9
`0db32c06e`). Measurements on any experimental / candidate / fork kernel
(`llama.cpp-experimental`, `experimental-v7-*`, branch builds) are **OBSERVATIONS ONLY**: they
MUST NOT gate any keep / revert / deploy / promote / buy / close decision and MUST NOT be
consumed by AutoPilot or any automated optimizer.

*Narrowed for in-worktree candidate search only by `P-AK-SEARCH-1` (Annex K, ratified 2026-08-03).
The decision-grade clause above is unchanged, and the consumption clause continues to bind every
consumer other than the AutoKernel controller that produced the record, within the campaign that
produced it.*

**Required evidence fields — ALL mandatory; a claim missing ANY field is an observation.**
1. **Hardware state** — GPU model, gfx target, ROCm runtime + driver, visible device id,
   `llama-server --version`, llama.cpp commit + clean/dirty; `rocm-smi` clocks, power,
   temperature, utilization, VRAM, PID mapping recorded **before AND after** each run/window;
   VRAM before / during / after request / after cleanup.
2. **Host interference** — explicit CPU-stack state (quiesced, or declared non-quiesced with
   reason); `llama-server` / AutoPilot / KFD PID checks before and after; whether the CPU
   production stack is stopped, hidden from ROCm, or intentionally co-resident.
3. **Binary/model identity** — exact worktree, branch, commit, binary path, `LD_LIBRARY_PATH`,
   backend list; exact model path, mmproj (if used), quant, context, KV quant,
   reasoning/sampling flags, spec-dec mode.
   **The `LD_LIBRARY_PATH`/backend evidence is satisfied ONLY by a verifier-produced
   linkage receipt captured against the running binary — verifier id and version, the
   inspected library set with per-library resolved path and sha256, and the verdict —
   never by a recorded environment string alone. A receipt that inspected no libraries
   is vacuous and does not satisfy this field.** (Amended 2026-08-12: llama.cpp dlopens
   `libggml-hip.so`, so a HIP-invoked run can execute wholly on CPU while `ldd` shows
   nothing — INC-20260731, reproduced twice on 2026-08-12. Governs claims made after
   this date; artifacts already dispositioned are not re-graded.)
4. **Run recipe** — warm-up policy; **fresh server per rep** unless resident-server mode
   explicitly declared; discard rules for warm-up reps and shape-change graph recapture; reps
   per the P-BENCH-1 rule (n≥5 for ≥5% claims, n≥10 for ≤2%); fixed prompt/task set,
   prompt-token count, generated-token floor, seed + sampling policy.
5. **Result grammar** — median + MAD, prompt/decode split where available; spec-dec: draft
   generated/accepted counters + acceptance rate; service/residency: active-overlap tax +
   cleanup proof; **vendor/web numbers only as background narrative, never in a decision row**
   (gfx90a compile≠perf per `agentic-rocm-kernel-authoring.md`).
6. **Attestation** — `metric [P-GPU-1, n/reps, YYYY-MM-DD, attest <ref>]`.

**Retro-certification (allowed, strict).** An existing GPU artifact upgrades to a P-GPU-1 claim
ONLY IF (a) produced on a production-named kernel AND (b) a field-by-field audit confirms
**every** mandatory field present (including the before-and-after clocks/power/temperature
record). Any absent field → the artifact remains observation-grade and MUST be re-run. No
partial upgrades.

**Standing consequence for experimental-era numbers.** Numbers measured on experimental kernels
before a promotion (e.g. the v7-candidate Gate-R residency number and banked GPU wins) remain
observations until re-run on the promoted production kernel. Ratification of this protocol
enables that post-promotion certification; it never upgrades pre-promotion experimental numbers.

## P-DFLASH-LINEUP-1 — DFlash lineup enablement (RATIFIED 2026-07-25)

**Scope.** Gates a production lineup change enabling `--spec-type draft-dflash`; does NOT gate
whether DFlash capability may exist in a versioned kernel and is not a kernel-promotion
requirement. Evaluate every `(target model, target quant, device class, draft model)` lane
independently — never pool acceptance or speed across lanes. Acceptance and decode t/s
higher-better.

**Instrument & provenance.** The owning checked-in DFlash runner with its fixed prompt pack,
semantic validators, warmup, counterbalanced base/DFlash schedule, and replicate count. Artifact
records: runner commit; target + draft model paths/sizes/SHA256s; binary + shared-library
paths/SHA256s; complete argv/env; lane identity; raw per-replicate prompt rows; draft counters;
host preflight; process witnesses; cleanup. Every prompt response must pass its semantic
validator. Missing, malformed, non-finite, mixed-lane, contaminated, or incomplete evidence is a
failure.

**Metrics.** Per lane: pooled per-token acceptance = `sum(draft_n_accepted) / sum(draft_n)`
over all DFlash prompts and replicates. Per prompt class: base and DFlash decode throughput =
`sum(completion_tokens) / sum(decode_seconds)` over that prompt's replicates, then
`DFlash / base`. Persist all numerators and denominators; an aggregate or median-of-medians
speedup cannot substitute for per-prompt ratios.

**Lineup decision rule.** A lane is eligible only when ALL hold:
- pooled per-token acceptance ≥ 0.60;
- every prompt-class DFlash/base decode ratio ≥ 1.00;
- all identity, semantic, numerical, host, completeness, and cleanup checks pass.

Failure blocks DFlash for that lane only — not other lanes, non-DFlash serving, or promotion of
the underlying kernel capability. Passing does not itself edit a production lineup; the operator
must separately authorize the reversible deployment change.

**Prospective.** Applies only to runs started after the 2026-07-25 amendment; the 2026-07-24
Laguna IQ2/Q4/Q8 artifacts remain observations and MUST NOT be retro-certified. Grammar:
`DFlash lineup <lane> eligible|ineligible [P-DFLASH-LINEUP-1, acceptance=<value>, per-prompt
ratios=<values>, n=<reps>, YYYY-MM-DD, attest <ref>]`.

## P-SHED-1 — Cross-device shed trade (CPU→GPU work displacement)

**Scope.** Decision-gating claims about moving batched `worker_general`-class work off the CPU
fleet onto the MI210 shadow lane while the CPU is under stress — the regime where the mover
consumes the resource it relieves (the lane's 8 host threads occupy SMT siblings 184-191, whose
physical cores 88-95 are atomic region `q3`). Composite protocol: P-BENCH-2 governs the CPU
half, P-GPU-1 the GPU half, and the paired whole-system design below the net. Design source:
epyc-inference-research `docs/design/p2-5a-shed-trade-measurement-spec.md` (commit `d5f5942f`).

**Metric — `task_rate`, never tokens/s.** Primary quantity = task_rate summed across BOTH
devices on one frozen corpus, higher-better. Tokens/s is not commensurable across the sides
(CPU: gemma4-26B-A4B MoE; GPU lane: 27B dense — different tokenizers, different work/token). A
t/s difference across the two sides MUST NOT appear in a decision row under this protocol.
(Within-device t/s under P-BENCH-*/P-GPU-1 is unaffected — see core §1 metric scoping.)

**The net is measured directly, never reconstructed.** The decision quantity is a PAIRED
whole-system comparison of two configurations on the identical frozen corpus in the same wall
window. Measuring GPU gain and CPU loss separately and subtracting is FORBIDDEN: it compounds
both halves' noise (rate CV ≈ 9.1% each) and measures the halves under conditions that do not
co-occur — which is the phenomenon under study. Separate halves are retained as diagnostics
explaining the sign, never as inputs the answer is computed from.

**Arms (same frozen corpus; A0/A2 answer, A1/A3 explain).**
- **A0 — CPU-only under stress**: full stress load, all tasks CPU, lane NOT launched (`q3`
  free). Baseline total task_rate.
- **A1 — lane resident, idle**: full stress load, all tasks CPU, lane serving nothing. Isolates
  the **residency tax** of holding 8 host threads on `q3`. MANDATORY — without it a negative
  net cannot be attributed.
- **A2 — shed active**: stress minus shed fraction *f* on CPU; lane serves *f*.
- **A3 — GPU reference**: lane serves *f* against a declared-quiesced CPU (un-contended GPU
  ceiling).

Primary: `net_task_rate = task_rate_total(A2) − task_rate_total(A0)`, higher-better, counting
tasks completed on both devices in the same wall window. Diagnostics:
`residency_tax = A1 − A0` (≤0 expected); `gpu_contention_tax = gpu(A2) − gpu(A3)`;
`cpu_displacement = cpu(A2) − cpu(A0)` (<0 by construction).

**Shed fraction swept, never assumed**: *f* ∈ {0.25, 0.50, 1.00} minimum (*f*=0 is A0). The
optimum may be interior (residency tax paid once; displacement grows with *f*) — a single-*f*
result MUST NOT be generalized to "shedding does not work".

**Stress is an input, not an observation**: fixed concurrent-request depth against the CPU
fleet, chosen so `q3` saturates in A0, declared in the run header. ≥2 stress levels (saturating
and 0.5× saturating). A trade measured only at saturation MUST NOT be generalized downward.

**Controls.** Arms interleaved and order-randomized within each rep block — never blocked
A0×n → A2×n (thermal/page-cache drift aliases onto the arm effect). Live affinity of every
instance and of the lane's host threads via `affinity_preflight.py` (topology hash certifies
intent, not reality). Host-health tier per P-BENCH-1, with drop_caches + NUMA-interleave re-warm
and lane pre-warm completed BEFORE the window opens in every resident-lane arm. Lane host-thread
count FIXED at 8 (SMT contention is non-linear; the v8 np×context ceiling table rests on that
shape). `q3` + the GPU device claim ACQUIRED via `region-lock` for the whole run — observing the
lane "looks free" is TOCTOU, not exclusion. All traffic through the eval-path fan-out with
forced role targets, never live `/chat`.

**Reps, MDE, pre-registered null.** Reps per the P-BENCH-1 rule; given rate CV ≈ 9.1%, a
plausible single-digit-percent net requires **n ≥ 10 paired blocks**. MDE computed and published
WITH the result, not after seeing it. Rate claims via the improvement / non-inferiority
e-process per P-SPEED-OBJ — never single-trial. `|net| < MDE` → verdict **"no detectable
trade"**, which is a decision (do not build), not a failed experiment.

**Pre-registered decision rule.**
- net > 0, e-process confirms, gain exceeds the operator's complexity threshold → the shed
  admission class may be built; the measured (*f*, stress) region is its validated envelope;
  outside it the class refuses.
- net > 0 within MDE, or e-process inconclusive → do NOT build; re-measure only if a consumer
  decision depends on it.
- net ≤ 0 at every swept *f* → close the shed class permanently (measurement-closed).
- net ≤ 0 explained wholly by residency_tax → narrower finding: the lane MUST NOT be resident
  during CPU stress; class stays closed; lane residency policy gains a stress-aware rule.

**Decision-grade requires ALL of**: this ratified protocol; a production-named kernel (currently
v9 `0db32c06e`) per the P-GPU-1 provenance rule; every P-GPU-1 mandatory field for the GPU half
and every P-BENCH-2 requirement for the CPU half; live-affinity attestation; a contention matrix
certified fresh for the current topology hash; the CPU fleet in its terminal PRODUCTION lineup
(not a bench shape); a frozen corpus manifest with identical sha256 across every arm and rep;
n ≥ 10 paired blocks with published MDE; an e-process verdict; an attestation ref. Missing ANY →
observation-grade (informs design, gates nothing). P-GPU-1's no-partial-upgrades
retro-certification rule applies unchanged.

**Prospective.** Applies only to runs started after ratification; no pre-amendment shed or
lane-residency artifact may be retro-certified. Report median + MAD; state metric direction per
row; per-stream p50/p95 latency reported per side as P-BENCH-3 requires for any batched-slot
claim. Grammar: `shed net <value> tasks/eval-wall-h at f=<f>, stress=<level> [P-SHED-1,
n=<reps>, YYYY-MM-DD, attest <ref>]`.

<!-- AMENDED per RATIFY-ANNEXG-V9-CURRENCY-20260811: the two P-GPU-1
     kernel-currency parentheticals track the CURRENT production kernel and moved
     v8 (67a433bf4, binary 10107) -> v9 (0db32c06e, binary 10125) at the
     2026-08-10T23:59:00Z cutover (ratify_v9_final_freeze_20260811.json, ratified
     2026-08-11T01:16:00Z). Decision-grade claims produced on v8 while v8 was the
     production kernel remain decision-grade for their era; from the cutover, new
     P-GPU-1 decision-grade claims require production-consolidated-v9. No other
     clause of this annex is changed by this amendment. -->
