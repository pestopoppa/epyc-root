# Fable 5 findings 01c — Sequential verdict: worked e-process specification

**Date**: 2026-06-12. **Companion to**: `fable5-findings-01-impl-plan.md` Phase 1.4 (this doc IS that phase, fully specified). **Prereqs**: Phase 1.1–1.2 (per-question ledger), Phase 2.0 (instrument repair), Phase 2.1 (designed core) — the spec works on the accidental 43-set too, with lower power.

## 0. Why e-processes (and not SPRT or more MAD)

The decisive property: **anytime validity under optional stopping and optional continuation.** Your evaluator's customer is a *planner that decides when and whether to re-test based on the data so far* — exactly the behavior that invalidates fixed-n tests and classical SPRT-with-peeking. An e-process (a nonnegative supermartingale under H0 with E₀[E_t] ≤ 1) gives `P(∃t: E_t ≥ 1/α) ≤ α` (Ville). The planner can look every trial, stop, resume, or abandon — the error guarantee survives. Secondary benefits: e-values **compose across candidates** (e-BH gives FDR control over the whole archive later, if wanted) and **multiply across independent evidence batches** (T1 core evidence × promotion-eval evidence = one number).

It also dissolves the MAD filter's dilemma cleanly: MAD asks "is this single draw significant?" (answer at your resolution: almost never, except lucky 2-flip draws — hence both over-exclusion of real wins and the t775 ratchet). The e-process asks "has this *config* accumulated enough evidence?" — the question you actually mean. `mad_noise` and `reproduction_confirmed` collapse into one state: `accumulating`.

## 1. Objects and notation

- **Candidate** C: a config-fingerprint (`action_identity.config_fingerprint`, already canonical).
- **Reference** B: the baseline config's *per-question profile* on the current core: `p̂_B(q)` = mean correctness of question q over B's last `W=10` non-excluded trials (per-question ledger). Refreshed continuously as baseline trials occur; frozen-snapshot per candidate at candidate creation (`ref_snapshot_ts`) and refreshed only at candidate state transitions (prevents moving-target pathologies).
- **Trial observation** for C at trial t: the per-question outcome vector on the core, `x_t(q) ∈ {0,1}`.
- **Paired trial statistic**: restrict to the *discordant-capable* set `D = {q : 0 < p̂_B(q) < 1 or x_t(q) ≠ round(p̂_B(q))}`; define the centered per-trial delta
  `S_t = Σ_{q∈core} (x_t(q) − p̂_B(q))`, with range bound `R = |core|` but practically `R_eff = |D|` (typically ~10–14 on today's set; ~25–35 on a designed core).
  Using the centered sum against the *profile* (not a single B trial) is what makes one C-trial informative even when B isn't re-run alongside it; B's own sampling error is second-order because W=10 trials back the profile (and the periodic baseline re-runs keep it fresh — see §5 cadence).
- Within-trial question outcomes are dependent (same generation context, host state); **the unit of e-update is therefore the trial**, never the question. Across trials of C, S_t are independent given the config (independent generations, independent host noise) — the assumption the design needs, and the same one every current gate already makes.

## 2. The e-process (quality axis)

Per candidate C, maintain wealth `E_C` (init 1.0). H0: "C is not better than B," formalized as `E[S_t] ≤ 0`.

**Update rule — capped-bet test supermartingale (aGRAPA-style):**
```
z_t   = S_t / R_eff_t                      # bounded in [-1, 1]
λ_t   = clip( μ̂_{t-1} / (σ̂²_{t-1} + μ̂²_{t-1}), 0, 0.5 )   # bet from PAST data only (predictable)
E_C  *= (1 + λ_t · z_t)
```
where `μ̂, σ̂²` are running mean/variance of past `z` for this candidate (Kelly-style bet, shrunk; the 0.5 cap bounds per-trial wealth loss at 50%). λ_t depending only on strictly prior data keeps the supermartingale property; with `E[z_t] ≤ 0` under H0, `E[1 + λ z] ≤ 1`. First trial bets a prior λ₁ = 0.1.

**Thresholds** (defaults; all in `policy_version: seq-v1`):
- `confirmed` : E_C ≥ 1/α with **α = 0.05 → E ≥ 20**.
- `refuted`   : E_C ≤ 0.05 (wealth ~gone; not a formal type-II bound — e-processes don't give one — but a practical futility floor) **or** k ≥ budget with E_C < 2.
- `accumulating` otherwise. **Budget**: k_max = 8 trials per candidate (≈ 1.8h of T1 wall; planner-visible).

**Power sanity check** (so expectations are calibrated): a true +2-question improvement on a core with R_eff ≈ 12 gives E[z] ≈ 0.17; with the Kelly bet settling near λ ≈ 0.3–0.5, expected log-wealth growth ≈ 0.025–0.05/trial → E ≥ 20 typically inside 4–7 trials *if reproducible*; a +1-question effect confirms in roughly 8–15 (often hitting budget → correctly judged "not worth more evidence at this effect size"). A noise config random-walks and dies at the futility floor. These match the intuition you want: 1-flip "wins" stop being decisions, 2-flip real wins confirm within a planner-session, and nothing confirms off a single lucky draw — the t775 ratchet becomes impossible.

## 3. The non-inferiority e-process (task-rate axis) and the joint verdict

Same machinery on the findings-05 objective: `y_t = (task_rate_t − task_rate_B) / task_rate_B`, winsorized to [−0.5, 0.5], tested against H0: `E[y_t] ≤ −m` with margin **m = 0.05** (one noise-quantum of the rate axis; CV≈9%). Bet update identical, on `(y_t + m)/0.5`.

**Joint verdict** (replaces keep/revert + MAD on the improvement branch):
- `confirmed_improvement` := E_quality ≥ 20 **and** E_rate_noninf ≥ 20 → eligible for baseline promotion + plain archive admission + strategy/AP-22 learning.
- A *rate*-improvement candidate (speed-seeking config) swaps the roles: E_rate ≥ 20 and E_quality_noninf ≥ 20 (margin = 1 core quantum). The planner declares the claimed axis in the action (`expected_axis`), so the right pair of processes is primary; both pairs are always computed.
- Regression protection is **unchanged and immediate**: the hard floors and the −5% gate (made resolution-aware) still revert a clearly-bad trial on the spot — sequential machinery is for *crediting improvements*, never for delaying damage control.

## 4. State schema (lives in the ledger; views rebuilt per findings-01 Phase 3)

```jsonc
// journal row addition per evaluated trial:
"seq": { "candidate": "<fingerprint>", "core_id": "core_v2", "k": 4,
         "z": 0.083, "lambda": 0.31, "E_quality": 6.4, "E_rate_noninf": 11.2,
         "state": "accumulating", "policy_version": "seq-v1" }

// derived per-candidate view (in-memory; rebuildable by folding journal):
{ "fingerprint": "...", "core_id": "core_v2", "created_trial": 781,
  "ref_snapshot": {"fingerprint_B": "...", "ts": ..., "profile_hash": "..."},
  "trials": [781, 784, 790, 791], "E_quality": 6.4, "E_rate_noninf": 11.2,
  "wealth_history": [[781,1.1],[784,2.0],[790,4.1],[791,6.4]],
  "state": "accumulating", "budget": 8, "expected_axis": "quality" }
```
Excluded trials (`exogenous_*`, corrupted) update **nothing** (same gate as today). Core-version or policy-version change ⇒ all `accumulating` candidates reset (wealth → 1, k → 0) under the new id; `confirmed` verdicts keep their (core_id, policy) provenance.

## 5. Integration points (exact)

1. `safety_gate.check` improvement branch (`safety_gate.py:638-689`): replace `_mad_significance` with `sequential_verdict.update(candidate, question_results, task_rate)`; verdict categories map `accumulating→benign-no-learning`, `confirmed→clean-pass`, `refuted→failed-experiment` in `learning_exclusions.py`.
2. `update_baseline`: callable **only** with a `confirmed_improvement` verdict (kills the ratchet by construction); promotion also triggers the findings-01 Phase 2.4 large fresh eval, whose result *multiplies into the same E* (independent batch ⇒ product is still an e-value) — promotion finalizes at the combined E ≥ 100 (α=0.01 for baseline changes).
3. Planner prompt (per-candidate block, generated): `candidate <fp8>: k=4/8, E_q=6.4 (needs 20), E_rate=11.2 — one more reproduction worth ≈×1.5 if real. Recommended: reproduce | abandon.` This converts "should I re-test?" from vibes into expected-wealth arithmetic the critic can audit.
4. **Baseline freshness cadence**: schedule 1 baseline-config trial per ~10 trials (the seed_batch the planner already over-produces, now given a job) so `p̂_B` and the rate reference track host drift; profile staleness > 48h flags the candidate's verdicts `stale-reference`.
5. Shadow rollout: 2 weeks dual-logging (`seq` block alongside MAD verdicts), then the findings-01 §4 flip-rate report decides cutover; `AUTOPILOT_LEGACY_MAD=1` keeps the old path for one release.

## 6. Failure modes considered (and answers)

- **Reference drift / regime change** (reboot, model swap): attestation boundary events (findings-04 §B) reset reference snapshots; candidates spanning a boundary mark trials excluded — same as today's exogenous machinery.
- **Planner farming many candidates** (multiplicity): each candidate's α is marginal; if candidate volume grows, apply e-BH across `confirmed` candidates monthly for FDR — composable by design, defer until it matters.
- **Within-trial dependence**: handled by trial-level updates (§1); never update per-question.
- **Adversarial overfitting to the core**: out of scope for this spec — that's the audit block's job (findings-01 Phase 2.2); a confirmed-on-core candidate with a failing audit correlation gets `confirmed-core-only`, not promoted.
- **Effect heterogeneity across suites**: z is core-global; per-suite wealth (same rule, suite-restricted R_eff) is computed as *telemetry only* — do not gate on it (n too small), do surface it to the planner.

**Effort**: ~2–3 days for `src/autopilot_core/sequential_verdict.py` (+~150 LoC, pure, unit-testable with simulated Bernoulli streams: verify Ville bound empirically at α=0.05 over 10⁵ null runs), plus the two wiring points and the prompt block.
