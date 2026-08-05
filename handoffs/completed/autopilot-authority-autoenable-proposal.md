# Proposal — Auto-enable AutoPilot authority on strict-readiness-pass

**Status**: COMPLETED / SUPERSEDED — retired from the active queue 2026-08-05. The operator-ratified consolidated apply-time signature model supersedes auto-enable; authority consent remains explicit and human-owned.
**Created**: 2026-06-28
**Owning handoff**: [evidence-plane-ledger-and-sequential-verdicts.md](../active/evidence-plane-ledger-and-sequential-verdicts.md) (owns the authority cutover bundle) · related [autopilot-continuous-optimization.md](../active/autopilot-continuous-optimization.md)
**Author context**: requested after the W6 gaming alarm cleared (calibrated in orchestrator `d4eae8b9`) and strict readiness began passing (`restart_ready=True`, all cutover gates green, 2026-06-28).

---

## Problem / goal

Today, planner **authority** (the right to ratify a trial as the new production baseline / canonical verdict) is enabled by an operator manually setting `baseline_ledger_authority_enabled` + the sequential-authority flag in state, *after* `restart_readiness_report.py --strict --require-seq-cutover --require-w6-audit` passes. The gates encode "reasonable confidence" (≥120 trusted vectors, ≥30 seq-shadow rows, flip-rate band, W6 audit corroboration). But even when they pass, authority stays **default-off until a human flips it** — so a powerful feature sits idle whenever no operator is watching.

**Goal**: let authority become **automatic once the confidence gates clear**, while keeping the human in the loop at the *policy* level and preserving full reversibility and auditability. The operator consents **once** to the automation; the system then reconciles authority to readiness on its own.

## Non-negotiable design principles

1. **Policy-level opt-in, not instance-level.** Behavior is unchanged unless the operator sets a one-time consent flag. This keeps the trust boundary human-owned (you authorize the *rule*; the machine applies it).
2. **Authority tracks readiness — it does not latch.** If strict readiness later *fails* (new gaming alarm, era reset, vector loss), authority **auto-disables** symmetrically. Never "enable once, stay on through a regression."
3. **Hysteresis / dwell.** Require strict-pass to hold for **K consecutive readiness checks over ≥M trials** before enabling — never flip on a single sample (the gates are resolution-quantized; one-sample flips are how we got noise alarms in the first place).
4. **Era-aware.** Only act on current-era evidence (`pareto_exclude_before_ts`). A kernel/instrument era boundary forces re-accrual before re-enable — no cross-era authority.
5. **Auditable.** Every auto-enable/disable writes a journal event carrying the **readiness snapshot that justified it**, so any flip is reconstructable.
6. **Reversible + kill switch.** Operator can force-disable and clear the policy flag at any time; force-disable wins over auto-enable until cleared.
7. **Scope-limited.** Applies ONLY to `baseline_ledger` + `sequential_verdict` authority. **Out of scope and permanently human-only:** safety gates, the eval tower / scoring, era-registry rows, the objective vector. (`MEASUREMENT.md §trust boundary`.)

## Mechanism

A small **authority controller** reconciles state to the strict verdict, called once per loop iteration (or every N trials) in `scripts/autopilot/autopilot.py`, reusing `restart_readiness_report` as the single source of truth (no new gate logic).

```
authority_controller(state):
    policy = env AUTOPILOT_AUTHORITY_AUTOENABLE in {off, shadow, on}   # default off
    if policy == off or state.authority_force_disabled:
        return                                   # unchanged behavior

    rr = restart_readiness_report(strict=True, require_seq_cutover=True, require_w6_audit=True)
    pass_now = rr.restart_ready and not rr.blockers
                and rr.sequential_cutover.cutover_ready
                and rr.w6_audit_cutover.cutover_ready
                and rr.baseline_authority.cutover_ready
                and rr.era_exclude_before_ts == state.pareto_exclude_before_ts   # era-aware

    state.authority_pass_streak = (state.authority_pass_streak + 1) if pass_now else 0
    dwell_met = state.authority_pass_streak >= K_CHECKS and trials_since_streak_start >= M_TRIALS

    desired = pass_now and dwell_met
    current = state.baseline_ledger_authority_enabled and state.sequential_authority_enabled

    if desired and not current:
        if policy == shadow:
            journal("authority_autoenable_would_fire", evidence=rr)      # log only
        else:
            enable_authority(state); journal("authority_autoenabled", evidence=rr)
    elif current and not pass_now:                                       # symmetry: regression
        disable_authority(state); journal("authority_autodisabled", reason=rr.blockers, evidence=rr)
```

### State / env additions
- env `AUTOPILOT_AUTHORITY_AUTOENABLE` = `off` (default) | `shadow` | `on`. **`shadow` is the rollout default** — it logs every flip it *would* make without touching authority, so the operator can watch it decide correctly for a few days before granting `on`.
- state: `authority_pass_streak`, `authority_streak_start_trial`, `authority_force_disabled` (operator kill switch), `authority_autoenable_last_event`.
- constants: `K_CHECKS` (e.g. 3) and `M_TRIALS` (e.g. 10) — the dwell window.

### Reused, not reinvented
- `scripts/autopilot/restart_readiness_report.py` — the verdict (already the canonical gate).
- `scripts/autopilot/audit_block_report.py` — the calibrated W6 alarm (`d4eae8b9`).
- existing state authority flags + the journal event-sourcing path.

## How this addresses the failure modes we hit this session
| Risk seen | Guard in this design |
|---|---|
| W6 alarm fired on quantization noise | depends on the **calibrated** alarm; dwell prevents acting on single-sample gate flips |
| Kernel cutover contaminated speed baseline | era-aware check: authority won't enable across an era boundary without current-era re-accrual |
| Restart churn reset accrual | dwell measures *current-era* streak; a restart that drops evidence simply restarts the streak (and auto-disables if it was on) |
| "Enable once, drift later" | symmetric auto-disable on any strict-fail |
| Silent over-reach | shadow mode + journaled evidence for every (would-)flip; force-disable kill switch |

## Rollout plan
1. **Implement** the controller + state/env (planner-orchestration code; outside the scoring/era trust boundary). Land default `off`.
2. **Shadow** (`AUTOPILOT_AUTHORITY_AUTOENABLE=shadow`) for a dwell-window-plus of trials. Review the `authority_autoenable_would_fire` events: did it propose enabling exactly when you'd have manually, and auto-disable on regressions?
3. **Operator grants `on`** once shadow behavior is trusted. Authority now tracks readiness automatically.
4. Keep the manual flip + force-disable as the override path.

## Verification / tests
- Unit: controller enables only after K/M dwell; auto-disables on injected strict-fail; never acts in `off`; respects `authority_force_disabled`; refuses across an era-boundary mismatch; shadow mode never mutates authority.
- Integration: replay a journal where gates pass→fail→pass and assert authority follows with correct journal events.
- No interaction with the W6 gaming-alarm accrual (same guard the cutover tests already assert).

## Operator decision points (please rule on these)
1. **Approve the concept?** (auto-enable via one-time policy opt-in)
2. **Dwell window** `K_CHECKS` / `M_TRIALS` — how much "holding steady" before it flips (proposed 3 checks / 10 trials).
3. **Symmetric auto-disable** on regression — confirm desired (recommended yes).
4. **Shadow-first** rollout — confirm (recommended yes).
5. Anything to add to scope, or keep strictly baseline+sequential only (recommended: keep limited).

> Implementation is **not** to begin until these are answered; this is the trust-boundary gate.

## Progress checklist

- [x] BLOCKED: operator approval of trust-boundary gate required before any implementation — superseded by the 2026-07-27 consolidated apply-time ratification policy; no `AUTOPILOT_AUTHORITY_AUTOENABLE` controller exists. ✅ 2026-07-29
- [x] **Archive disposition:** operator-approved staleness cleanup moved this superseded proposal to `handoffs/completed/`; preserve it as the rejected auto-enable design and retain the explicit-consent baseline (`baseline_ledger.py` / `authority_consent.py`, orchestrator `e03c9f41`). ✅ 2026-08-05
