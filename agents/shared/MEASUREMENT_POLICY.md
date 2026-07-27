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

## Deterministic replay before regeneration (operator-ratified 2026-07-27)

**If a result can be obtained without running inference — by deterministically rescoring or
transforming previously saved inference outputs — ALWAYS do that instead of regenerating.**
Origin: the architect-bench rescoring spiral (each scorer fix was triggering full same-era
reruns of every arm, blocking real work).

- **Scorer/converter/extractor defect** → the default remedy is a tail replay: re-run the
  fixed deterministic stage over BANKED model outputs (seconds, no inference). Regenerate
  only when the GENERATION path itself was defective.
- **Quality scores transfer across kernel eras once parity is proven** (e.g. v7→v8 paired
  Δ0.0pp exact ties). Kernel era-fencing exists for the speed axis; quality re-fencing is
  triggered only by instrument (scorer/pool) changes — and those get tail-replay too.
  Rebaseline only the axis that changed — never everything.
- **Before any full-suite rerun**, prefer focused runs on the discriminating/discordant
  items (the McNemar-discordant set carries the signal).
- **Pre-commit a stopping rule** before any bench campaign: name the table that is FINAL
  and the decision each outcome triggers; "confirmation" runs are shelved unless their
  result would change a deployment decision.

## Consolidated apply-time ratification (operator-ratified 2026-07-27)

**Evidence collection and validation NEVER wait on a human signature.** Protocol
pre-ratification is abolished as a default. The ceremony is inverted: agents run
collection/validation/repair autonomously and fail-closed with sealed provenance, and the
human signs ONCE, at apply time, over a consolidated evidence bundle (protocol + evidence
hashes + validation results + the exact state diff to be applied).

- **One token per trust boundary, not per artifact.** Human-only writes remain exactly: era
  registry rows, `MEASUREMENT.md`, AutoPilot baseline-state applies, production
  freezes/cutovers, host reboots. Everything upstream is autonomous.
- **A failed validation does NOT restart a ratification chain.** Fix, revalidate
  autonomously, re-present the SAME consolidated apply token with updated evidence hashes.
  Never serialize a repair loop through the operator.
- **Batch queued boundary items** into one attestation listing each item (the operator may
  strike lines) — the op-bundle grant pattern extended to state applies.
- **Never gate unrelated work on a boundary token.** Benches, replays, and evidence
  gathering on other instruments proceed regardless of any pending apply
  (origin incident: Laguna-Q4 wrongly chained behind an AutoPilot baseline apply).

- **Operator-presented commands must be pre-validated end-to-end by the agent** (dry-run
  the full validation path before handing over the token command). A command that fails in
  the operator's hands is an AGENT defect: fix, revalidate, re-present — never iterate
  draft→fail→redraft through the operator.

Rationale: the trust boundary exists so agents cannot self-certify the instruments that
judge them — it was never meant to meter the *pace* of evidence work. This converts
operator interactions from O(defects) to O(boundaries).

## Trust boundary

`MEASUREMENT.md`, the eval tower, scoring contracts, and this file are read-only for autonomous optimization processes. Changes are human, PR-reviewed amendments.
