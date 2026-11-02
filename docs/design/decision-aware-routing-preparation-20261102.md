# Decision-aware routing preparation — 2026-11-02

This is implementation preparation, not a measurement result or authorization to change a routing default. The active handoff remains `handoffs/active/decision-aware-routing.md`.

## DAR-5 identity vectors

An offline single-step prototype maps reward from [-1, 1] to [0, 1] and computes the bilinear-weight and identity gradients from the same pre-update state. Its focused tests include a finite-difference joint-gradient check, invalid inputs, non-mutation and overflow; four tests passed. The prototype is scratch at `/mnt/raid0/llm/tmp/decision-aware-routing/dar5-preparation-20261102/`, not integrated source or a durable training artifact. It does not complete DAR-5.2: per-role identity state, initialization from known descriptors, persistence, training integration and a held-out comparison remain. The specified DAR-5.4 comparison also needs the fixed-reward DAR-4 baseline and IRT prompt features. Do not infer an improvement or enable a default from the prototype.

## Cache affinity

The prefix index provides per-physical-server predictions; a fresh, reconciled idle-slot match is stronger than a served-only ordering hint, but neither guarantees actual reuse. Actual server-reported cached-token counts arrive after dispatch, for the selected server. Missing, stale, disabled, unmatched, or unverified evidence must remain unknown rather than becoming a cold miss. Several roles may share one physical server. The task-completion reward path does not currently establish an attribution join to the serving ledger.

A reward change alone cannot compare current candidate caches. A potential default-zero selection term needs candidate-to-server mapping, the final rendered prompt, fresh verified residency evidence, and a calibrated cost scale; if those inputs are unavailable it should contribute no preference and record why. Trace post-selection overrides before choosing an integration point. The duration reward already includes actual prefill time, so an additional reward or penalty needs an explicit marginal objective to avoid double-counting. A nonzero reward-distribution change also requires the applicable operator-ratified instrument-era boundary. Preserve quality gates and the wall-clock speed axis.

Tests for a future implementation should cover zero-weight parity, shared-server roles, fresh versus stale or unverified predictions, unknown cache reports, rendered-prompt mismatch, post-selection overrides, and replay attribution. These are design constraints, not evidence of runtime savings or policy benefit.
