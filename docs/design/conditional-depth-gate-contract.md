# Conditional depth expected-value gate

Implementation contract for the open numeric-gate task in
[RAO + ReDel substrate spike](../../handoffs/active/context-and-token-economy.md#track-rao-redel-substrate-spike).
This document specifies a prospective, default-off orchestrator policy; it does
not enable a runtime policy or establish a measured threshold.

## Inputs and units

For each proposed transition from current depth `d` to `d + 1`, require:

| Input | Contract |
|---|---|
| `p_base_fail` | Finite probability in `[0, 1]`, conditioned on the current task, target role, model identity and current depth. |
| `rescue_value` | Finite nonnegative expected utility conditional on base failure, in units of the base-attempt cost. It must already include the conditional probability that this depth transition rescues the failure. |
| `cost_multiplier` | Finite nonnegative incremental cost of this transition, in the same units as `rescue_value`. |
| `policy_binding` | Target role, model content identity, current/target depth, predictor/calibration revision, valuation revision and cost-estimate revision. |
| `depth_evidence` | For target depth 2, a retained measured threshold and its evidence identity for this exact role/model/depth transition. A boolean named `measured` is insufficient. |

The handoff's `P(fail) * value(rescue) > cost_multiplier` is dimensionally
meaningful only after these units are fixed. For example, if successful rescue
has value 100 base-cost units and its conditional success probability is 0.4,
`rescue_value` is 40, not 100. The cost term must use the same utility conversion.
Do not substitute a probability bounded by one for rescue value while comparing
against a wall-time ratio greater than one.

A published total wall-time ratio is not automatically the incremental cost
after a completed base attempt. Bind the cost estimate to whether escalation
runs before or after that attempt and account for reuse and sunk cost. The
historical ratios discussed in the handoff are motivation, not local thresholds.
The inequality is a necessary screen, not a complete utility model: depth can
also damage an otherwise correct answer. Estimate and deduct that expected harm
and any other material transition cost in the same units before admitting a
policy; absent those estimates, this contract alone cannot establish positive
net value.

## Decision procedure

1. Leave the existing configured depth behavior in place unless the policy is
   explicitly enabled. Installing this gate must not itself change the default.
2. When enabled, reject malformed, missing, nonfinite or out-of-range inputs,
   unknown bindings and mismatches between request and policy bindings. Return
   a distinct unavailable/invalid reason; do not report these as a low predicted
   failure probability or synthesize a zero score.
3. Admit only a single next-depth transition. Keep target depth greater than 2
   unavailable. Keep depth 2 unavailable without its own bound measured threshold;
   a depth-1 policy or a high `p_base_fail` cannot unlock it.
4. Compute `expected_rescue = p_base_fail * rescue_value`; admit only when it is
   strictly greater than `cost_multiplier`. Equality denies escalation.
5. For depth 2, require both the expected-value comparison and the separately
   bound measured threshold. Record which condition denied the request.

`COMP_r(x)` estimates success; an explicitly calibrated success probability can
be converted with `p_base_fail = 1 - p_success`. A raw competence score, ranking,
classifier margin or AUC is not a calibrated probability.

The [escalation-prediction probe](../../handoffs/active/routing-program.md#escalation-prediction-probe--2026-07-27-provisional-adversarial-verification-pending)
records a refuted result and requires outcome-label repair before another probe.
Its historical "Ready" dataset designation does not satisfy this input contract.
Keep the gate unavailable for that predictor until replacement calibration and
label validation exist; this does not prevent implementing the pure decision
function and testing it with synthetic values.

## Offline acceptance cases

These are synthetic policy tests, not evidence of recursion quality or cost.

| Case | Expected result |
|---|---|
| `p=0.8`, rescue value `40`, cost `25`, matched depth-1 binding | Admit: `32 > 25`. |
| `p=0.625`, rescue value `40`, cost `25` | Deny equality. |
| `p=0`, rescue value `40`, cost `0` | Deny equality. |
| `p=1`, rescue value `40`, cost `41` | Deny even with certain base failure. |
| NaN, infinity, negative value/cost, probability outside `[0,1]`, boolean numeric input | Invalid input; no escalation. |
| Role, model, calibration revision or depth transition differs from policy | Binding mismatch; no escalation. |
| Depth-1 inputs pass, requested target is depth 2, no depth-2 evidence | Unavailable. |
| Depth-2 evidence present, expected-value condition fails | Deny. |
| Depth-2 expected-value condition passes, measured threshold fails | Deny. |
| Target depth 3 or a skipped depth | Unavailable. |
| Policy disabled | Preserve existing configured behavior. |

## Implementation boundary

Place the pure decision function and request-path integration in
`epyc-orchestrator`, with explicit denial reasons and tests for the table above.
Do not introduce application runtime code in the root governance repository.
Before integration, inspect the actual recursion call sites and run their
GitNexus impact checks; this document makes no assertion about caller coverage.
Capture decision inputs, binding identities, computed expected value and denial
reason in the existing trace surface. Any later process producing verified
calibration or depth-cost findings must register its write-side belief source
and planning-context canary under the existing source-class rules before using
those findings to authorize a depth transition.
