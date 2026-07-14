# Window-2 findings 04 — Negative-space audit + self-critique (§8.5–8.6)

> **Archived 2026-07-14** (backlog ROI audit, [backlog-roi-audit-2026-07-14.md](../active/backlog-roi-audit-2026-07-14.md)): self-critique deliverable complete; actionable items live in other handoffs.

## 1. Delete / merge / freeze / stop-optimizing

- **Delete from active surfaces** (kill rows, findings-03): P0-restart row, LRC P4.5/4.6 (null), K-MEM completed rows, NUMA-private-weights (CLOSED NEGATIVE, measured), G11/G10 scored rows; the ~170 lines of A9 chronology (to progress logs); campaign Queue 1 (100% closed).
- **Merge**: RO-17/RO-18 audit rows into the stack-governance row; duplicate Queue/Package rows (K-MEM, K-ROPE, EV-4/H5); campaign Q3 keystone copy into the owning evidence-plane handoff.
- **Freeze harder** (adverse evidence, not missing instrumentation): DCP pre-assembly; dispatcher-v1-as-is; TQ3_1S merge prohibition stands.
- **Stop optimizing**: CPU micro-kernels for roles that may migrate (E3 8×8 SIMD, MoE-Spec CPU) until Gate R lands — a week of waiting beats a month of stranded SIMD; the MI210 handoff's simulator suite (cache policies, route tracing, H2D matrices) — build none of it unless M2 fails in a surprising way; the absolute-MLP/calibrator family in A9 (the index itself says stop; honor it).
- **Stop re-litigating once measured**: if M4 shows verify cost ≈ K×, write the family-C obituary for CPU targets into the acceleration index and point future spec-dec intake at GPU-pair configurations only.

## 2. Most dangerous silent assumptions (ranked)

1. **"W6 clear = gaming solved."** It means *no divergence within the fenced era's audit design*, under a one-sided trigger, after an unadjudicated re-base. Treating it as a solved-bit will bite at the next era fence. (findings-01 §4)
2. **"Authority live = instrument adequate."** Authority runs on the legacy seed-42 core with effective discriminating n≈10–14. The plane is honest about *noise*; it cannot manufacture *resolution*. Every day before I2 lands, confirmations are ~4.7pp-MDE decisions.
3. **"Same-seed repeatability measures difficulty."** Post-determinism it measures concurrency artifacts and infra flakiness only. Any future calibration batch built on repeat-flips will no-go forever — by construction.
4. **"Registry throughput numbers can rank placement."** They are observations (2026-03..05, no protocols, three model swaps ago). Gate R must re-anchor the CPU baseline in-window; do not let 24.3-vs-X carry a migration on its own.
5. **"The GPU is additive capacity."** Concurrency memory says otherwise on CPU (dual-half negative); the GPU analogue is PCIe/host-thread interference between the GPU server's host threads and the CPU fleet — measure the *combined* substrate (one CPU canonical rep during a GPU bench) before declaring the lanes independent.
6. **"α transfers across quant/sampling/traffic."** It is a model-pair property *at matched quant, temperature, and prompt mix*; the production temps are now 0.1–0.3 (N14), not the harness's temp-0.
7. **"The strategy store only contains what the pipeline wrote."** Direct SQLite writes are sanctioned practice; until R6, the store's provenance is a convention, not a property.

## 3. Invariant interfaces the North Star requires (hold these stable)

1. **Journal event schema + exclusion-policy enum** — now including `seq_refuted` (R1). The enum IS the guarantee; version it.
2. **MEASUREMENT.md protocol registry** — P-GPU-1 joins P-BENCH-1/2/3; placement decisions cite protocols or wait.
3. **Registry acceleration block extended with `device/ngl/binary_dir/env`** — placement as data; the compile→attest chain is the only path a placement change may take.
4. **The consent/authority file pattern** (operator-owned, fail-closed, read-only to the optimizer) — reuse it verbatim for any future restart-class lever (CAP-REG W4).
5. **Era registry append-only with disposition rule** (R5) — fence moves are era transitions, not knob turns.
6. **The claim grammar** — unchanged; it did its job this window (every GPU number above is labeled observation).

## 4. Smallest observations that would distinguish this architecture from alternatives

- One `grep` of production logs (M0) distinguishes "GPU drafter worth pursuing" from "self-MTP already saturates."
- One ledger-derived core_v2 item-set comparison (I2, zero inference) distinguishes "repeat-flip protocol measured difficulty" from "it measured flakiness" (<50% overlap = the latter).
- One frontdoor-on-MI210 bench (G3) distinguishes fleet-placement-first from kernel-work-first roadmaps.
- One journal replay counting fingerprints-vs-confirms distinguishes "multiplicity is theoretical" from "it is live" (confirms ≈ 0.05×fingerprints = live).
- One combined-substrate rep (CPU canonical during GPU load) distinguishes "two lanes" from "one contended host."

## 5. Bets that compound vs. stay optional

**Compound (make now)**: R1 refutation closure (every future narrative inherits it) · P-GPU-1 + Gate R (every later GPU decision cites it) · ledger-derived difficulty (the instrument improves itself from its own exhaust — this is the F2 self-running-lab pattern applied to the instrument) · orchestrator placement-as-data plumbing (pays for every future card/model) · HIP kernel competence (fork control on the only viable GPU substrate for your archs).
**Optional/reversible (fine to defer)**: architect expert-split · embedder/vision hosting · TTS/image GPU rebench · drafter-farm anything · CPT scoping.

## 6. Self-critique (§8.6)

**Weakest links, in order:**
1. **The Gate-R throughput extrapolation.** 47%-roofline Q8 evidence comes from a *dense-ish 27B* (Qwen3.6-27B) and gemma4-31B; the frontdoor is a *sparse MoE + GDN hybrid* whose small per-expert GEMMs and router overhead on gfx90a are unmeasured, and whose HIP op coverage is asserted for the 27B GDN path but **not yet loaded as `qwen35moe`**. G2's op-coverage smoke is deliberately sequenced before G3 for this reason; if experts fall back to CPU ops, my #1 recommendation's numbers are void (the *framing* — fleet placement — survives).
2. **The W5 "post-fix deterministic" inference.** f4a8a3ca fixed seeds/temps, but server-side batching under `-np`/concurrency can still produce nondeterminism; I designed I4 (conc-1 vs conc-3) to *test* this rather than assume it, but my §3 narrative leans on determinism more confidently than the evidence strictly allows. Also the adversarial pass corrected one detail: pre-fix payloads *did* send temperature — accidental greedy 0.0 — so the pre-fix flips are sampling-regime artifacts of a different flavor than "unseeded sampling."
3. **The multiplicity channel (R4) is arithmetically argued, not empirically demonstrated.** I did not run the fingerprints-vs-confirms replay; it is listed as the decisive observation instead. If actual fingerprint minting is low (planner proposes few novel configs), R4 drops to P2 hygiene.
4. **Portfolio triage is index-grounded, not handoff-grounded.** Per the brief I sampled ~20 of 349 files; a deciding fact wrong *in an index* propagates into my triage. The three fired-gate findings were verified against owning handoffs; most keep verdicts were not.
5. **Traffic-shape claims are inferred.** "Frontdoor burns the most wall-clock" rests on eval-bottleneck defaults, escalation-chain structure, and role aliasing — no request-count telemetry was read. If real traffic is worker-dominated, residency EV shifts toward the worker (which would *strengthen* the GPU case — one 25 GB copy replaces 86 GB of no-mmap replicas — but change the model choice).
6. **What I could not verify this window**: live process env for the orchestrator API (read-only session; config-level verification only) · flash-attn/torch training viability on gfx90a for the F3/delta-mem revivals ([unverified], flagged in their rows) · the exact mechanism that zeroed W6's in-era cumulative count on 2026-06-28 (named as an auditability gap, itself worth one forensic hour) · whether `GGML_OP_OFFLOAD_MIN_BATCH` op-offload works with the *HIP* backend on this fork at useful prefill sizes (M3 tests it; I verified the code path exists, not its performance).

**What would most change my recommendations**: G3 landing <1.3× (residency demotes; HIP-kernel authoring becomes the critical path and the window-1 ordering partially inverts toward "eval-only hosting + kernels") · M0 showing α_MTP ≥ ~0.75 per role (drafter leg permanently closed; spec-dec attention moves entirely to GPU-pair configs) · I4 showing genuine error-free flips at conc=1 (the instrument has a deeper nondeterminism source than concurrency; W5 becomes a serving-stack investigation, not a protocol redefinition).

**Standing bias to audit in my output**: both windows, I have recommended *more measurement before building* — consistent with your MEASUREMENT.md culture, but a reviewer with a stronger build bias would note that R12's plumbing is cheap enough to build speculatively in parallel with G3 rather than behind it; if the bench passes, that ordering saves a week. I kept it gated because a failed Gate R would leave GPU plumbing as dead code in the launch path — your call to invert.

## Progress checklist

- [x] Negative-space + self-critique deliverable produced ✅
