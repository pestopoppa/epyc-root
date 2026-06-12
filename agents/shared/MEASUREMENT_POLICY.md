# Measurement Policy (agent digest)

Canonical authority: `/workspace/MEASUREMENT.md` (protocol registry, claim grammar, retroactivity policy).
Era registry: `epyc-orchestrator/orchestration/instrument_eras.yaml` (append-only).
This digest exists so a session can act correctly without reading the full constitution; when in doubt, the constitution wins.

## The claim rule

A decision-gating number = `(metric, protocol-id, n/reps, date, attestation ref)`. A number without a protocol citation is an **observation**: usable for hypotheses, never for keep/revert/deploy/promote/buy/close decisions.

## Historical numbers — era-label first, then apply the verb

1. Era-label it (`instrument_eras.yaml`): pre-canonical CPU bench (E0)? pre-speed-fix autopilot speed (E2, ×0.5 deinflate by `pareto_epoch_ts` timestamp — NEVER by `speed_metric_mode`, which is identical across the fix)? pre-tool-era quality (E3a)? which T1 n (E3b, by `details.total`)?
2. Apply its verb: **retro-certified** (recorded command/env conforming to a named protocol) → use; **demoted-to-prior** → hypothesis only, open a re-measure ticket if it must gate; **retired-view** (frontiers/HV/baselines across era boundaries) → consult the era-appropriate rebuilt view.
3. **Never edit historical records to "fix" them — append** (supersession events, era entries, comments).

## Producing new numbers

- **Throughput**: only via the codified recipes — `bench_canonical.sh` / `canonical_recipe.py` (epyc-inference-research). Never hand-typed bench commands. Reps: ≥5 for ≥5% claims, ≥10 for ≤2%. `-fa 1` explicit. Binary-resolution check is part of the recipe.
- **Before any bench**: explicit operator approval (another agent may be benchmarking; concurrent runs silently poison both); host-health preflight (uptime ≤1wk → drop_caches + NUMA-interleave rewarm; ≥1wk → reboot required); `pgrep` zombie check.
- **Quality**: the autopilot eval tower is a versioned instrument (core id, n, quantum, MDE) — single-trial deltas below 2 question-flips are never conclusions; see MEASUREMENT.md P-QUAL-*. Known-dead instrument items are listed in `instrument_eras.yaml`.
- **A/B**: N ≥ 100/arm for production-role decisions; classify every failure by reason (infra vs model) and report the infra rate next to the effect.
- **Registry writes**: throughput/quality fields carry structured `measured: {date, protocol}` provenance (free-text comments are the legacy witness — do not destroy them in reformats).

## Trust boundary

`MEASUREMENT.md`, the eval tower, scoring contracts, and this file are read-only for autonomous optimization processes. Changes are human, PR-reviewed amendments.
