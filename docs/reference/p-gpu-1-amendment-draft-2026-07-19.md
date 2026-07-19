
## P-GPU-1 — MI210 GPU Canonical Throughput Amendment Draft (2026-07-19)

**Status: proposed amendment text only.** This file is not the measurement
constitution and does not ratify `P-GPU-1`. Until `/workspace/MEASUREMENT.md`
is amended by the operator/human review path, `P-GPU-1` remains deferred there
and every MI210 / HIP / GPU throughput number remains observation-grade.

If ratified, the amendment should replace the current deferred `P-GPU-1`
placeholder with the text below.

**Supersedes** the prior "`P-GPU-1` deferred" status. Applies to all decision-gating GPU
(MI210 / gfx90a / HIP) throughput, spec-dec, and residency numbers. Metric direction:
higher-better (t/s) unless a lower-better metric is explicitly stated.

**Kernel-provenance rule (production-named kernels ONLY).** A `P-GPU-1` decision-grade claim
MAY ONLY be produced on a **production-named kernel** (`production-consolidated-vN`).
Measurements on any experimental / candidate / fork kernel (`llama.cpp-experimental`,
`experimental-v7-*`, branch builds) are **OBSERVATIONS ONLY**: they MUST NOT gate any
keep / revert / deploy / promote / buy / close decision, and MUST NOT be consumed by
AutoPilot or any automated optimizer.

**Required evidence fields — ALL mandatory. A claim missing ANY field is an observation.**
1. **Hardware state** — GPU model, gfx target, ROCm runtime + driver, visible device id,
   `llama-server --version`; llama.cpp commit + clean/dirty; `rocm-smi` clocks, power,
   temperature, utilization, VRAM, and PID mapping recorded **before AND after** each
   run/window; VRAM used before / during / after request / after cleanup.
2. **Host interference** — explicit CPU-stack state (quiesced, or declared non-quiesced with
   reason); `llama-server` / AutoPilot / KFD PID checks before and after; whether the CPU
   production stack is stopped, hidden from ROCm, or intentionally co-resident.
3. **Binary/model identity** — exact worktree, branch, commit, binary path, `LD_LIBRARY_PATH`,
   backend list; exact model path, mmproj (if used), quant, context, KV quant,
   reasoning/sampling flags, spec-dec mode.
4. **Run recipe** — warm-up policy; **fresh server per rep** unless resident-server mode is
   explicitly declared; discard rules for warm-up reps and shape-change graph recapture;
   **reps per the `P-BENCH-1` rule (n≥5 for ≥5% claims, n≥10 for ≤2% claims)**; fixed
   prompt/task set, prompt-token count, generated-token floor, seed + sampling policy.
5. **Result grammar** — report **median and MAD** for throughput plus prompt/decode split
   where available; for spec-dec, report draft generated/accepted counters and acceptance
   rate; for service/residency claims, report active-overlap tax and cleanup proof;
   vendor/web numbers may appear ONLY as background narrative, never in a decision row.
6. **Attestation** — a `P-GPU-1` decision row uses the standard grammar
   `metric [P-GPU-1, n/reps, YYYY-MM-DD, attest <ref>]`.

**Retro-certification (allowed, strict).** An existing GPU artifact MAY be upgraded from
observation to a `P-GPU-1` claim ONLY IF (a) it was produced on a **production-named kernel**
per the provenance rule above, AND (b) a field-by-field audit confirms **every** mandatory
field is present in the artifact. If any mandatory field is absent — including the
clocks/power/temperature before-and-after record — the artifact **remains observation-grade
and MUST be re-run** under this protocol. No partial upgrades.

**Consequence for the current v7 candidate.** The Gate-R residency number and the banked GPU
wins were measured on the *experimental* kernel, so they remain observations until re-run on
`production-consolidated-v7` after promotion. `P-GPU-1` ratification enables that
post-promotion certification; it does not upgrade pre-promotion experimental numbers.
