# MEASUREMENT v2 — Ratification ledger (2026-07-30)

> **APPLIED**: operator ran `apply_v2.sh --apply` at 20260730T103218Z. v1 backup:
> `artifacts/operator/measurement-v1-backup-20260730T103218Z/`. Residual draft markers in the
> live core cleaned by operator-authorized follow-up the same day. This ledger is now the
> historical delta record for the v1→v2 amendment.

Every semantic difference between the live `/workspace/MEASUREMENT.md` (617 lines, v1) and this
draft bundle. Items marked **[decision]** need an operator call; the rest are proposed as-is.
Nothing in this bundle is authoritative until ratified.

## Structural

- **L1 — Core + annex split.** v1 was a single append-grown file. v2 = core constitution
  (~200 lines: rule, grammar, metric scoping, protocol index, noise table, governance,
  retroactivity) + three annexes (`protocols/bench-cpu.md`, `quality-eval.md`,
  `gpu-cross-device.md`) carrying the full normative protocol text under the SAME trust
  boundary. Amendment rule updated: append to the owning annex + one CHANGELOG line in core.
  **[decided 2026-07-30: core + annexes]** — annexes install at `measurement/protocols/`; the
  apply script extends `human_only_paths.yaml` (+ sha256 re-pin) so the trust-boundary hook
  covers them.
- **L2 — Metric-scoping section added (§1).** Operator directive 2026-07-30: task_rate is the
  autopilot-objective metric; tok/s is the instrument-level metric for individual model/kernel
  benchmarks. v1's "t/s retained as host-health telemetry only" (P-SPEED-OBJ) is now explicitly
  scoped to the autopilot objective — it never demoted P-BENCH-*/P-GPU-1 t/s claims, but v1
  didn't say so.

## Staleness fixes

- **L3 — §5a era table replaced by a registry pointer.** The v1 copy was stale: it ends at
  E5-cpu-kernel/E3-routing while `instrument_eras.yaml` now carries E4-quality-core-v2,
  E5/E6/E8-autopilot-speed, E6/E8-cpu-kernel, E7-eval-instrument, E8. Constitutional content
  kept: the era-class rules (`scope: autopilot_tooling`, within-era comparison,
  `speed_metric_mode` false friend). The yaml (already human-append-only) becomes the single
  table of record.
- **L4 — P-GPU-1 merged and de-staled.** v1 had two P-GPU-1 blocks: the §1 placeholder ("close
  this placeholder when MI210 hardware is acquired or permanently deferred" — the MI210 has been
  installed and serving for months) and the ratified tail block. Merged into one entry in
  Annex G. The "consequence for the current v7 candidate" paragraph is rewritten as a standing
  rule about experimental-era numbers. **[resolved 2026-07-30]** — the banked GPU wins (Gate-R,
  K35 MTP rows, AXA-2, DR-3 K2) were NOT re-certified: the 2026-07-19 completeness audit
  (`pgpu1_artifact_completeness_audit.py`) found the primary Gate-R row missing mandatory
  fields, so P-GPU-1's no-partial-upgrades rule forbids retro-certification — rerun-only. The
  reruns are already tracked as open checkboxes (inference-acceleration-index DR-3e etc.,
  requiring `production-consolidated-v8`); no new measurement-debt tickets needed. One genuine
  v8 P-GPU-1 attestation exists (Laguna 122B IQ2,
  `handoffs/active/laguna-pgpu1-v8-promotion-attestation.json`). The v2 standing-rule wording
  stands.
- **L5 — Phantom validator.** v1 §4 cited `check_claims_grammar.sh` — the script did not exist.
  **[decided 2026-07-30: build]** — built at `scripts/validate/check_claims_grammar.sh`
  (warn-mode, diff/range/file modes, `--strict` opt-in); v2 §5 now cites the real script.
- **L6 — Digest-outruns-constitution fixed.** "Deterministic replay before regeneration" and
  "Consolidated apply-time ratification" (both operator-ratified 2026-07-27) existed ONLY in
  `agents/shared/MEASUREMENT_POLICY.md`; the constitution never absorbed them, violating its own
  "the constitution wins" rule. v2 core §5 absorbs both (condensed; the digest keeps the
  operational phrasing). Ratifying v2 retroactively regularizes the 07-27 grants.
- **L11 — P-QUAL-T1 instrument description was stale; fixed in v2.** v1 says "currently the
  seed-42 accidental set — to be replaced per findings-01-impl Phase 2". **[resolved
  2026-07-30]** — `core_v2` landed 2026-07-23 (era `E4-quality-core-v2`, core_id `core_v2`,
  50 items / 37 scoreable, `policy_version core_v2_designed_e7_v1`, replacing
  `legacy_pool_seed_42_n50`). The v2 card now states this; ratifying v2 certifies the updated
  wording.
- **L13 — P-BENCH-1 precondition language modernized.** v1 said benches "require an explicit
  operator window per `feedback_no_concurrent_inference`"; that memory was amended 2026-07-27
  (held region-lock claim, not per-run approval). v2 states the region-claim rule. Follow-up
  outside this bundle: `MEASUREMENT_POLICY.md` L20 and `agents/shared/WORKFLOWS.md` L32 still
  carry the abolished per-bench-approval language and contradict
  `OPERATING_CONSTRAINTS.md` — fix at the same time. **[update 2026-07-30]**: `WORKFLOWS.md`
  and `benchmark-analyst.md` fixed directly; `MEASUREMENT_POLICY.md` turned out to be
  hook-enforced human-only (`human_only_paths.yaml`), so its one-line fix rides this bundle's
  apply script (`apply_v2.sh` step 3) rather than an agent edit.

## Condensation (intended to be semantics-preserving)

- **L7 — P-BENCH-4 affinity amendment folded in.** The v1 tail amendment ("superseding
  amendment") is merged into the protocol's witness section; the supersession record (prior
  receipt path + SHA-256, "durable historical provenance only") is retained verbatim in
  substance.
- **L8 — P-PAIRED staged status preserved** unchanged (still operator-apply; the staged block is
  reproduced condensed in Annex Q with all thresholds, formulas, and provenance gates intact).
- **L9 — Prose compression throughout** (~617 → ~200 core + ~470 annex lines, but any single
  protocol lookup now costs one short file). Intended invariant: zero loss of directive polarity
  (every MUST/NEVER/ONLY survives) and zero loss of numeric thresholds. Recommended ratification
  check: `grep -ciE '\b(must|never|only|shall|forbidden)\b'` per protocol, v1 vs v2, plus a
  side-by-side read of the decision rules.
- **L10 — Dropped**: "warn-mode month 1" scheduling note (obsolete); duplicated
  claim-grammar examples inside protocol bodies where the core §3 grammar covers them.

## Not changed

- All decision rules, thresholds, rep counts, provenance gates, prospective/retro-certification
  clauses, dump list, per-corpus reconciliation rulings, and known-limits text carry over with
  original meaning.
- The trust boundary is untouched: human-only, PR-reviewed, append-or-version.
