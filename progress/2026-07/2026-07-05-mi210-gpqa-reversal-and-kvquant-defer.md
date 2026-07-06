# 2026-07-05 — MI210 campaign: GPQA REVERSAL (scaffold WORKS on reasoning tasks, +12) + KV-quant SCOPED→DEFER

Self-contained wrap-up for the MI210 "reasoning-economics" slice that landed since the previous wrap-up (`67e14670`, 2026-07-05 — the CoT verifier/selector-pivot continuation of `2026-07-05-cot-falsification-and-mtp.md`). That entry left **two open threads**: (1) the **GPQA reasoning-diagnostic IN FLIGHT** (nothink vs ownthink vs scaffold-Qwable, to decide whether the earlier scaffold falsification was **distribution-specific**, not fundamental), and (2) the **KV-quant lever** at findings-05c **L14** still `[U]`/source-hypothesized-alive in a narrow single-stream-long-ctx regime. This session **resolved both** — and the GPQA result is a **REVERSAL**, the headline of the whole CoT arc. All work was committed inline to the owning handoffs; this is the narrative + evidence index. **Every GPU number here is an OBSERVATION** (single MI210, serial, contended host, single-sample seed=42, deterministic MC scoring, no `P-GPU-1` protocol per MEASUREMENT.md) — usable for direction, never decision-gating. All items experimental-HOLD; operator-only authorizes any production push, CPU-correctness-gated first.

## The arc, corrected

This session's CoT arc, end to end: single-shot scaffold **FALSIFIED on code** (both strength regimes) → self-debug/recursive **loop weak on code** (4% rescue, RL-ceiling) → **literature says scaffold-injection is a published dead-end** (amplifier-not-substitute) → **BUT the GPQA re-test on the RIGHT distribution REVERSED it: the scaffold WORKS on reasoning-bottlenecked tasks (+12 vs nothink).** The corrected conclusion is **distribution-conditional, not "dead."** Two operator methodology catches were decisive: **(1)** we had tested the **wrong distribution** — bigcodebench is library-API knowledge, not reasoning; **(2)** the **caps were too tight** — an 8192 cap truncated ownthink and understated it. Both catches, together, flipped the verdict.

## What landed this session

### 1. GPQA REASONING DIAGNOSTIC — a REVERSAL (commit `a3670e9f`) — THE headline result
GPQA grad-science, **N=48**, 35B-A3B-Q8 beneficiary (GPU), ownthink cap 16384 / scaffold-gen cap 8192, deterministic MC scoring, seed 42. OBSERVATION-grade.

| arm | pass | vs nothink | note |
|---|---|---|---|
| nothink | 23/48 (48%) | — | |
| ownthink | 32/48 (67%) | +9 | **20/48 STILL truncated @16384 → LOWER BOUND** (the 35B OVER-thinks, does not converge) |
| **scaffold-Qwable** | **35/48 (73%)** | **+12 (+25%)** | **0 truncated; 15 of 25 nothink-failures RESCUED / 3 regressions** |

- **The CoT-scaffold WORKS on reasoning-bottlenecked tasks** (+12, 15 rescues / 3 regressions, 0 truncation). This **REVERSES** the single-shot falsification (`mode_advantage_hard` code + Qwable→gemma), which was **DISTRIBUTION-SPECIFIC** — code / library-API / capability-limited tasks have **nothing to amplify**.
- **Reconciles with the literature "amplifier not substitute" (arXiv:2605.28913):** the **RECEIVER's latent capability is the gate.** GPQA (grad-science) → the 35B HAS it → the scaffold amplifies (+12); bigcodebench (library-API knowledge gaps) → nothing to amplify (self-debug loop 4%). The literature was never "scaffold is dead" — it was "scaffold amplifies a capable receiver." We had been testing on the one distribution where the receiver had nothing to amplify.
- **Scaffold ≈ ownthink on quality but FAR more token-efficient:** +3 over ownthink (≈parity given ownthink's 20/48 truncation under-count), with **0 truncation** because Qwable reasons concisely + completely in 8192 while the 35B OVERTHINKS (>16k, non-convergent). The GPU reasoner delivers the benefit at a fraction of the beneficiary token cost and dodges the overthinking-truncation trap — exactly the blended-wall-clock objective the lane was scoped around.
- **CAVEAT — needs a control:** on multiple-choice the +12 could be "35B latent capability elicited" OR "Qwable solves it + the 35B relays the choice." A **Qwable-standalone GPQA control** disambiguates (amplify vs Qwable-solves-and-35B-relays). **Deployment value holds either way** — the beneficiary server answers better — and both readings are literature-endorsed (amplify vs standalone-reasoner). Control PENDING.
- **Lane REOPENED + VALIDATED on reasoning-bottlenecked tasks.** Conditional deploy rule: reasoning-bound tasks where the beneficiary has latent capability (gate via `difficulty_band` + task-class). The **verifier/selector is now a COMPLEMENTARY mode, not a replacement** for the scaffold. The autopilot reasoning-effort lever now has a **validated positive instance**.

### 2. KV-quant SCOPED → DEFER (commit `d9e0898e`) — findings-05c L14
The findings-05c **L14** D-Q8 KV-quant lever was resolved from `[U]`/alive-in-narrow-regime to **DEFER (marginal, rider-only): NO dedicated GPU run.**
- Only the **qwen35 ~1/4 full-global attention layers @ single-stream 32–64k** are the alive regime. Across the resident model classes the payoff is ~0: **GDN keeps KV O(1)**, **gemma SWA bounds it**, and **aggregate is weight-dominated** (3 of 4 resident classes ~0 payoff).
- **CPU precedent shows the dequant cast COSTS throughput** (+9% wall / −30% gen on the CPU path). No deployed role needs it.
- **Decision:** run only as a cheap **~2–4h RIDER** on a future dense-full-global long-ctx role, to close the `[U]` with data. Recipe scoped. **Not a speed lever — a max-context / VRAM characterization.**

### 3. Verifier/selector harness BUILT (not yet launched)
The verifier/selector best-of-N experiment (GenRM-style, the "one working help-another-model mode" from the prior entry) now has a **built driver**: `/mnt/raid0/llm/tmp/cot-g1/driver_verifier.py` — GenRM best-of-N on cruxeval, ready to run. **Not yet launched.** With the GPQA reversal, verifier/selector is now **COMPLEMENTARY to the reopened scaffold lane**, not its replacement.

### 4. gemma-4-26B IQ4_XS verified (13.6 GB)
The mid-precision gemma-4-26B **IQ4_XS** arm (between the deployed Q4_K_M and the Q8 clean-quality arm) is **verified at 13.6 GB** — mid-precision probe queued.

## Commits (this session, epyc-root, branch spec-dec-mtp-refresh-2026-06-22)

| Commit | Summary |
|---|---|
| `d9e0898e` | findings-05c L14: **KV-quant SCOPED → DEFER** (marginal, rider-only, no dedicated GPU run) — GDN O(1) / gemma SWA / aggregate weight-dominated → 3/4 resident classes ~0 payoff; CPU dequant-cast costs throughput; only qwen35 ~1/4 full-global @ single-stream 32–64k alive |
| `a3670e9f` | **GPQA REVERSAL:** scaffold WORKS on reasoning-bottlenecked tasks (+12 vs nothink; nothink 48% / ownthink 67% lower-bound / scaffold-Qwable 73%, 15 rescues / 3 regr / 0 truncation). Reverses the code-distribution falsification; reconciles with amplifier-not-substitute (receiver latent capability is the gate). Lane REOPENED + validated; verifier/selector now COMPLEMENTARY; Qwable-standalone control pending |

Wrap-up doc commit (this progress entry + handoff Status-header + index/wiki reconciliation) added separately this session (hash in the wrap-up report).

## Deferred / open (next session picks up)
- **Qwable-standalone GPQA control** — disambiguates "35B latent capability elicited" vs "Qwable solves + 35B relays." Deployment value holds either way; the control is a science question, not a deploy blocker. (`gpu-cot-scaffold-sidecar.md`)
- **Verifier/selector best-of-N** — harness BUILT (`driver_verifier.py`, GenRM on cruxeval); ready to run, not launched. Now COMPLEMENTARY to the reopened scaffold lane, not a replacement.
- **gemma-4-26B IQ4_XS mid-precision probe** — verified at 13.6 GB, queued.
- **KV-quant rider** — DEFERRED to a future dense-full-global long-ctx role only (~2–4h characterization rider, not a speed lever).
- **Conditional-deploy gating** — register the scaffold as a `capability_registry` lever gated by `difficulty_band` + task-class (reasoning-bound + beneficiary-has-latent-capability); it joins the autopilot 4D-Pareto reasoning-effort family with a validated positive instance now.
- Scratch experiment drivers (`iq2_*`, `driver_verifier.py`, `cot-g1/*`) remain uncommitted transient artifacts under `/mnt/raid0/llm/tmp/` — not code artifacts.

## Wiki
This slice (**GPQA reversal + amplifier-not-substitute reconciliation + KV-quant DEFER**) was compiled into `wiki/hardware-optimization.md` as an extension of the existing review-flagged 2026-07-05 subsection. The source scanner reports **9 new sources** spanning parallel autopilot / evidence-plane / dashboard sessions; a full cross-session compile is out of scope for this focused wrap-up, so `.last_compile` was **NOT** touched (advancing it would hide the other sessions' un-compiled sources from the next incremental scan — same precedent as the prior two MI210 wrap-ups).

## Memory
No new memory file this session. The load-bearing lesson — **an accuracy-vs-token feature's verdict is distribution-conditional; test on the distribution where the receiver has latent capability to amplify before declaring a scaffold dead** — extends the existing `feedback_accuracy_token_tradeoff_rescue_metric` and `feedback_observe_before_diagnosing` / `feedback_verify_test_method_before_calling_it_a_bug` discipline. The operator's two methodology catches (wrong bench + tight caps) are the concrete instance.
