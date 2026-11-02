# Decision-aware routing preparation — 2026-11-02

This is implementation preparation, not a measurement result or authorization to change a routing default. The active handoff remains `handoffs/active/decision-aware-routing.md`.

## DAR-5 identity vectors

An offline single-step prototype maps reward from [-1, 1] to [0, 1] and computes the bilinear-weight and identity gradients from the same pre-update state. Its focused tests include a finite-difference joint-gradient check, invalid inputs, non-mutation and overflow; four tests passed. The prototype is scratch at `/mnt/raid0/llm/tmp/decision-aware-routing/dar5-preparation-20261102/`, not integrated source or a durable training artifact. It does not complete DAR-5.2: per-role identity state, initialization from known descriptors, persistence, training integration and a held-out comparison remain. The specified DAR-5.4 comparison also needs the fixed-reward DAR-4 baseline and IRT prompt features. Do not infer an improvement or enable a default from the prototype.

## Cache affinity

The prefix index provides per-physical-server predictions; a fresh, reconciled idle-slot match is stronger than a served-only ordering hint, but neither guarantees actual reuse. Actual server-reported cached-token counts arrive after dispatch, for the selected server. Missing, stale, disabled, unmatched, or unverified evidence must remain unknown rather than becoming a cold miss. Several roles may share one physical server. The task-completion reward path does not currently establish an attribution join to the serving ledger.

A reward change alone cannot compare current candidate caches. A potential default-zero selection term needs candidate-to-server mapping, the final rendered prompt, fresh verified residency evidence, and a calibrated cost scale; if those inputs are unavailable it should contribute no preference and record why. Trace post-selection overrides before choosing an integration point. The duration reward already includes actual prefill time, so an additional reward or penalty needs an explicit marginal objective to avoid double-counting. A nonzero reward-distribution change also requires the applicable operator-ratified instrument-era boundary. Preserve quality gates and the wall-clock speed axis.

Tests for a future implementation should cover zero-weight parity, shared-server roles, fresh versus stale or unverified predictions, unknown cache reports, rendered-prompt mismatch, post-selection overrides, and replay attribution. These are design constraints, not evidence of runtime savings or policy benefit.

## Fixed-reward data preparation

The located July 2026 reward replay predates the E18 duration axis. The current replay script can apply the current reward to progress events, but its emitted records do not include prompt features. The episodic-memory schema has objective and role fields but no listed stable task ID; a row-level join to the replay has not been established. Historical objectives can be truncated, so objective or role alone is insufficient to prove identity. A July training archive is also not evidence of E18 labels.

Before training or booking the cold-start comparison, establish a provenance-preserving task join and measure its coverage, including valid duration and role baselines. Audit era and consolidation provenance and report excluded cases. Write-time reward recovery from `q_value` is only valid under its recorded update-count conditions; do not treat every Q-value as an observed reward. The wall-clock reward was ratified in E18; the remaining issue is obtaining suitable observed data and a fixed-reward trained comparison, not ratification of that axis.

The identity prototype does not replace the descriptor path in the scorer. Integration needs independent per-role state, simultaneous updates, versioned validated persistence, guarded handling of old checkpoints and new roles, and real-scorer and router-fallback tests before any experimental comparison.

### Prepared coverage audit and controlled sweep

A fixture-tested aggregate-only auditor is prepared under `/mnt/raid0/llm/tmp/decision-aware-routing/join-prep/`. Current progress start/completion and reward-replay formats support a candidate task-ID join; duplicate IDs, conflicts and missing or inconsistent inputs must be excluded. The auditor does not establish a join to episodic memories, non-truncated features, or E18 scorer/configuration provenance. A real audit needs immutable, documented source snapshots and a baseline-role list derived from the exact scorer configuration; its output would measure coverage, not validate a training set or demonstrate a routing improvement.

For DAR-4b, `real_suite_v1` and the existing EvalTower window runner are candidates for a paired controlled workload and quality grader. They are not yet a sweep launcher: the current EvalTower HTTP helper does not propagate `routing_preferences`, and executed-role/selector telemetry needs verification. Request-level ω arms can initially hold τ fixed at 1; a τ sweep requires separately isolated, verified process configurations. Freeze and hash the suite, exclude forced-role questions under a predeclared rule, record arm order, errors, elapsed time and quality, and capture the actual selection and execution path. Fifty questions do not establish representativeness or adequate power. Wire the measurement source at write time before collecting results.
