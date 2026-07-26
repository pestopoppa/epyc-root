# E8 Quality Baseline Reseed

Default: after the E8 numeric rerun reaches 16 completed trials, run dedicated E8 full-pool tier
quality baselines matching E7, create a source-hashed evidence manifest, and use a separate
human-only atomic apply transaction. The quality hold stays open until that receipt is applied.

Alternatives considered:
- Derive values from the numeric rerun: rejected because numeric action sampling is not the E7
  full-pool quality instrument.
- Leave the hold open indefinitely: fail-closed fallback if the dedicated evidence cannot be
  produced.
