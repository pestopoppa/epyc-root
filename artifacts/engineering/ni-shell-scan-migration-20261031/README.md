# Shell scanner migration packet

Source commit: `c5c87541f4b487ad4f44df89b3cf9549eee7fc02`.

- `IMPLEMENTATION-REPORT.md` summarizes the change, semantic parity and validation result.
- `lane-validation-receipt.json` records R6 lock, CPU affinity, PID birth, RSS samples, runtime, and process absence.
- `lane-validation.log` is the raw successful test output.
- `setup-refusal.md` preserves the initial missing-pytest environment refusal.
- `validate_lane.py` is the bounded R6 validation runner.
- `progress.md` records completion and current review status.

The before/after command corpus is tracked with source in `tests/hooks/fixtures/shell_scan_migration_baseline.json`.
