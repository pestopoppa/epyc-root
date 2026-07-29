# Difficulty Signal Re-Validation — Data Gap Report (NIB2-32)

**Date**: 2026-04-21
**Script**: `/mnt/raid0/llm/epyc-orchestrator/scripts/analysis/difficulty_signal_validation.py`
**Handoff**: [`reasoning-compression.md`](../../handoffs/active/reasoning-compression.md) Action 3
**Status**: Script delivered; **execution blocked on shadow-telemetry persistence gap** (see below)

## What was planned

Per `reasoning-compression.md` L93: "At old thresholds (0.3/0.6): 92% easy, 0% hard, no predictive spread. Recalibrated to 0.15/0.35 for ~40/40/20 split. Medium prompts take 29% longer (p50 36s vs 25s). Re-validation needed at new thresholds."

NIB2-32 scope: re-bin the 635 Package A routing decisions at the new thresholds, cross-correlate with benchmark accuracy, emit a go/no-go on enforce mode.

## What was found (blocker)

The `difficulty_score` / `difficulty_band` shadow telemetry is **not persisted** to either of the two queryable data streams on disk:

| Data stream | Samples | Has `difficulty_*`? |
|---|---|---|
| `logs/seeding_diagnostics.jsonl` | 3,187 | No |
| `logs/progress/*.jsonl` (393,185 entries across all days) | 393,185 | No |

`routing_meta` is constructed with `difficulty_score` / `difficulty_band` at `src/api/routes/chat_pipeline/routing.py:220-221`, but that dict isn't routed to either persistence stream. The Package A analysis from 2026-04-06 that produced the "92.3% easy, 0% hard" finding was performed on in-session server logs (since rotated/gone); the raw 635 decisions were never written to a committed artifact.

Package A output directories under `data/package_a/<timestamp>/` contain only `env_flags.txt` — no routing decisions.

## Prerequisite fix needed before NIB2-32 can execute

A small persistence fix: route the `difficulty_score`, `difficulty_band`, `factual_risk_score`, `factual_risk_band` fields from the `routing_meta` dict (constructed in `routing.py:220-221`) into `seeding_diagnostics.jsonl` at record-write time. Implementation should be ~20 LoC in `scripts/benchmark/seeding_types.py` (RoleResult) and the seeding emit site.

This is itself a small non-inference task (~1h). It's **not in NIB2-32's scope** (plan specified offline analysis only, assuming data existed) but it's a prerequisite. Two paths forward:

1. **Add a new backlog entry (proposed NIB2-35)**: "Persist `routing_meta.difficulty_*` and `factual_risk_*` to `seeding_diagnostics.jsonl`". Then re-run NIB2-32 once data accumulates.
2. **Expand NIB2-32 scope** to include the persistence fix. But that conflicts with plan-defined scope.

Recommended: path 1 (add NIB2-35, keep NIB2-32 deliverable as the analysis script).

## Deliverable as it stands

`scripts/analysis/difficulty_signal_validation.py`:
- Loads diagnostics + progress logs, joins by `question_id`
- Accepts user-provided raw routing-decisions JSONL via `--raw-routing-decisions`
- Computes band distribution, per-band pass/fail rate, Spearman rank correlation (band ordinal vs error indicator)
- Emits verdict: ENFORCE-READY (|rho|≥0.30) / TUNE-THRESHOLDS (0.15≤|rho|<0.30) / SIGNAL-NOISE (|rho|<0.15) / INSUFFICIENT-DATA (n<100)
- Human + `--json` output

Current output on live data: `INSUFFICIENT-DATA (n=0)` — confirms the gap described above.

## Cross-reference

- `handoffs/active/reasoning-compression.md` Action 3
- `src/api/routes/chat_pipeline/routing.py:178-221` (where shadow telemetry is computed but not persisted)
- `scripts/benchmark/seeding_types.py` RoleResult dataclass (proposed persistence target)
