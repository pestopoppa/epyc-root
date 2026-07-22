# SafetyGate / Promotion-Gate / RLVR-Export Provenance Audit — 2026-07-22

**Scope:** read-only walk of every numeric input reaching a gating verdict in
`/mnt/raid0/llm/epyc-orchestrator` (== `/workspace/repos/epyc-orchestrator`).
Commissioned by operator 2026-07-22. Read-only: no inference, no HTTP, no stack
commands, no source edits. Offline pure-code imports only. Files read at
committed HEAD where the trail crossed another agent's mid-edit set.

HEAD at audit: `22e32ec27e73` (branch `spec-dec-mtp-refresh-2026-06-22`).

Per-number method answers four questions: (1) physical producer chain
(file:line); (2) era-filtered? (E7-eval-instrument era live from
2026-07-21T10:30Z, scope `eval_quality`); (3) can an infra failure impersonate a
quality signal (REL-1: infra errors must become excluded error rows, never
scored-wrong); (4) is provenance carried to the verdict, or does the number
arrive naked?

**HARD BOUNDARY respected:** ESC-7 (whether *real* ECE re-enters gating) is an
open operator decision. This report maps mechanics and flags mechanical defects
(dropped provenance, missing era filter, possible infra impersonation). It does
**not** recommend flipping any operator-reserved default.

---

## Executive Summary

The **live per-trial SafetyGate quality path is not era-fenced for the E7
eval-instrument boundary** (F1, CRITICAL). Post-E7 results (79k-question /
41-suite pool + B7 scorer, live since 2026-07-21T10:30Z) are gated against
**pre-E7 baselines still resident in state** — `baselines_by_tier` T1=1.814 /
T2=1.524, pre-E7 per-suite baselines (the old 20-suite set), a pre-E7 MAD
history window, and a Pareto frontier whose exclusion epoch
(`pareto_exclude_before_ts` = 2026-07-20T13:30Z, the **v7-speed** cutover)
predates E7 by a day. `active_instrument_eras` tracks only `autopilot_speed` and
`cpu_bench` — there is **no `eval_quality` active-era key and no quality-epoch
advance**. The era registry itself says pre-boundary quality rows are "historical
priors ... not directly comparable" and that the scorer changed; the gate treats
them as directly comparable. Net effect: a scorer/pool change can be charged to
the model as a quality regression (spurious revert) or credited as an
improvement (spurious promotion). This is live (`trial_counter` = 1438,
`consecutive_failures` = 2 of 3).

The **RLVR export drops confidence provenance** (F2, HIGH):
`export_rlvr_environment._environment_row` builds a `SimpleNamespace` **without
`details`** (the sole carrier of `confidence_is_real`), and `_eval_record` never
extracts `confidence_is_real` either. Verified empirically: **every T1/T2
exported row fails `ready_for_training` with a `confidence_not_real` blocker and
zeroed calibration+discrimination components — even when `ece`/`auroc` are
present and finite.** This is fail-**closed** (under-credits; does not
impersonate quality), isolated to the export: the two in-loop callers
(`autopilot.py:8287`, `safety_gate.py:607`) pass the *real* `EvalResult` and are
correct.

**Confirmed sound (no defect):** SafetyGate promotion verdicts do **not** consume
`ece`/`auroc`/`calibration_violations` (verified across `check()` 1211–1601).
REL-1 is upheld on the primary producer paths — quality denominator excludes
error rows, reliability = non-error fraction, and the known infra-failure
patterns (circuit-open in-band text, forced-role fallback, orphan/abandoned
drain) are converted to **excluded error rows**, not scored-wrong. The
reliability floor 0.8 path correctly suppresses quality checks and signals RETRY
(does not advance the rollback counter). The RLVR `confidence_is_real` gate on
calibration/discrimination is null-safe fail-closed.

**Finding counts:** CRITICAL 1 · HIGH 1 · MEDIUM 3 · LOW 2.

---

## Per-Number Provenance Table

Numbers that reach a gating verdict (SafetyGate `check()` / `update_baseline()`),
plus the RLVR reward numbers (observe-only but they carry a `ready_for_training`
determination that gates training-data admission).

| # | Number | Producer chain (file:line) | Era-filtered? | Infra-impersonation possible? | Provenance carried to verdict? |
|---|--------|----------------------------|---------------|-------------------------------|--------------------------------|
| 1 | `result.quality` (0-3, per tier) | `eval_tower._aggregate` 2998-2999 (`correct/n_scored*3`) → `EvalResult.quality` → `safety_gate.check` quality-floor 1328-1333, regression 1341-1355, monotonic `update_baseline` 1836, archive-max 1846 | **NO** — compared vs pre-E7 tier baseline; gate never reads `details.core_id`/era (F1) | Partly — errors excluded (good); NaN → `quality_not_finite` fail 1304-1306; partial(read-timeout,error=None) scored (F5) | **Naked** — arrives as bare float; `details.core_id`/`dataset_sha`/`confidence_is_real` not threaded into verdict |
| 2 | `result.reliability` (0-1) | `_aggregate` 3039-3040 (`n_scored/total_count`) → `check` reliability-floor 1318-1324 (floor 0.8, `RELIABILITY_FLOOR` 123) | N/A (fraction, era-neutral) | Bounded — REL-1 error rows lower it correctly; NaN bypasses floor (F6, not reachable from producer) | Verdict exposes `reliability_blocked` flag (good); floor value not stamped |
| 3 | `per_suite_quality[suite]` | `_aggregate` 3049 → `check` per-suite gate 1434-1480 | **NO** — pre-E7 per-suite baselines; new E7 suites (mmlu_pro, gpqa_diamond…) have no baseline → gate skips; shared suites compared cross-scorer (F1) | Same as #1 (per suite) | Naked; threshold resolution uses `per_suite_counts` (#4) |
| 4 | `per_suite_counts[suite]` | `_aggregate` 3057 → `per_suite_regression_threshold` 229-241 | N/A | N/A (sets 3/n resolution, not a gate itself) | Carried as `n_result`/`n_baseline` in violation string |
| 5 | `result.speed` / `baseline.frontdoor_speed` | `_aggregate` 3032 → `check` throughput floor 1492 (×0.8) | Speed IS fenced — `pareto_epoch_ts`/`frontier_rerun_required` (E6-speed) | Host-throttle detection demotes to warning 1503-1543 (read-only) | Warning carries throttle triggers |
| 6 | `routing_distribution["architect"]` | `_aggregate` 3082-3094 → `check` routing cap 1483-1489 (`ARCHITECT_ROUTING_CAP` 0.80) | N/A | Low | Naked fraction |
| 7 | `baseline.quality_for_tier(tier, strict)` | YAML `autopilot_baseline.yaml` (seed, `captured_at 2026-04-04`) + `autopilot_state.json:baseline_state.baselines_by_tier` → `Baseline.load`/`apply_state` 693-921 | **NO era stamp** on baseline; dup-state vs ledger (F4) | Loader guards scale/archive-max/corrupt (good, 715-836) | Baseline has no `core_id`/era field |
| 8 | Pareto frontier max quality | `_pareto_archive_for_safety_guard` 275-296 (journal-authoritative) → archive-max guard 726-741, 1846-1875 | **NO** — `pareto_exclude_before_ts` = v7-speed epoch (2026-07-20), NOT E7 (2026-07-21); pre/post-E7 quality entries coexist (F1) | Reproduction-count + on-frontier guards (good) | Frontier entries keyed by trial_id/tier, no era |
| 9 | MAD `quality_history_by_tier` | `check` 1597 appends passed quality → `_mad_significance` 1072-1092 | **NO** — window mixes pre/post-E7 samples (F1); live window is pre-E7 | Failed/NaN trials excluded from window (good, 1591-1598) | `mad_noise`/`mad_zero_window` categories carried |
| 10 | `ece` / `auroc` | `_aggregate` 3103-3126 (from non-error confidences) → **NOT read by SafetyGate**; read by `rlvr_reward_from_result` 111-112 | eval-era stamped in `details.ece_instrument_era` (ev11b) but not gate-consumed | Default **0.0 not NaN** → absence reads as perfect calibration / degenerate AUROC (F3) | In `details` only; flat METRIC line emits `0.0000` for absent (F3) |
| 11 | `confidence_is_real` | `_aggregate` 3280-3281 (`sources ⊆ {completion_probabilities_geomean}`) → `details` → `rlvr_tiers._confidence_is_real` 259-271 gate 164-170 | Provenance flag, era-neutral | Gate zeroes calib/disc + `confidence_not_real` blocker (good, fail-closed) | **Dropped by RLVR export SimpleNamespace** (F2) |
| 12 | Seq `E_quality` / `E_rate_noninf` | `_sequential_verdict` 1094-1209 (default-off `AUTOPILOT_SEQ_VERDICT`) → `update_baseline` 1797-1819 | Partial — `core_id`-paired + `seq_stale_reference`; default-off | Fail-closed on unavailable inputs (good) | `seq` block on verdict (rich provenance) |

---

## Findings by Severity

### F1 — CRITICAL: quality gating path is not era-fenced for E7 (numbers gate without era provenance)

**Claim.** The live per-trial SafetyGate quality checks (floor, regression,
per-suite, MAD, monotonic promotion, archive-max) compare a post-E7 result
against pre-E7 baselines/frontier/history with **no era filter**. Only the
*speed* dimension is era-fenced (via `pareto_epoch_ts` / `frontier_rerun_required`
for the v7 kernel). The E7 eval-instrument change (pool 21→41 suites + B7 scorer)
is invisible to the gate.

**Evidence.**
- Era registry `orchestration/instrument_eras.yaml` E7-eval-instrument row
  (scope `eval_quality`, from `2026-07-21T10:30:00Z`):
  "pre-boundary T1/T2/T3 quality rows are **historical priors** for
  cross-suite/aggregate comparisons ... per-suite comparisons on the
  byte-identical shared suites remain usable **WITHIN the same scorer semantics
  only**" — and the B7 scorer is live from this boundary (scorer changed).
- `orchestration/autopilot_state.json` (read live):
  - `active_instrument_eras = {"autopilot_speed":"E6-autopilot-speed",
    "cpu_bench":"E6-cpu-kernel"}` — **no `eval_quality` key**.
  - `baseline_state.baselines_by_tier = {"1": 1.8139…, "2": 1.5242…}` — the
    strict same-tier baselines the regression gate (safety_gate.py:1341) and
    monotonic gate (1836) read.
  - `baseline_state.per_suite_quality_by_tier["1"]` = the **pre-E7 20-suite set**
    (`agentic, bigcodebench, coder, cruxeval, debugbench, general, gpqa,
    hotpotqa, instruction_precision, livecodebench, long_context, math,
    mode_advantage, mode_advantage_hard, simpleqa, skill_transfer, thinking,
    tool_use, usaco, vl`) — none of the E7 additions (mmlu_pro, gpqa_diamond,
    physreason, olympiadbench, aime, …).
  - `quality_history_by_tier` (MAD windows) are pre-E7 samples.
  - `pareto_exclude_before_ts = 1784554213.0` = **2026-07-20T13:30:13Z**;
    `pareto_epoch_reason` names the **v7 kernel/speed** cutover, not E7. So the
    archive-max guard's frontier (safety_gate.py:726, 1846) includes pre-E7
    quality entries.
- `safety_gate.SafetyGate.check()` (1211-1601) and `update_baseline()`
  (1738-1949): neither reads `result.details.core_id`, `dataset_content_sha256`,
  `ece_instrument_era`, nor `instrument_eras.yaml`. The only "freshness" gate is
  `_baseline_eligible` (1639-1687), which checks the **contention matrix /
  topology** (speed instrument), not the eval instrument.
- The eval-instrument identity IS produced — `_stamp_eval_instrument`
  (eval_tower.py:1517-1553) writes `details.core_id` + `dataset_content_sha256`
  and warns on intra-process drift — but it is a **warning-only, in-memory**
  detector (`_DATASET_SHA_BY_CORE_ID`, not persisted across restarts) and is
  never consulted by the gate.

**Why it matters (decision-impact).** A scorer/pool change that lowers measured
quality on the same model looks identical to a model regression: the regression
gate (`REGRESSION_THRESHOLD -0.05`) can force a revert, or a laxer→stricter
transition on some suites can flip per-suite gates. Conversely a pool that adds
easier suites can lift aggregate quality and manufacture a spurious promotion.
The registry's own reconciliation verb for these rows is "historical prior — do
not compare directly," which the gate violates. Matches the defect signature
"numbers gating without provenance."

**Boundary note.** *Whether* to auto-fence in code vs. reseed baselines by
operator action is a policy choice (the registry says "E4 opens when the
instrument repair lands ... append it then with core_id, policy_version, and the
rule that E≤3 T1 frontiers/baselines are retired views"). I flag the mechanical
gap; the remediation owner is the operator. This is **not** the ESC-7
reserved boundary.

---

### F2 — HIGH: RLVR export SimpleNamespace drops `details` → all T1/T2 rows fail-closed on calibration (known-filed gap, fully mapped)

**Claim.** `export_rlvr_environment._environment_row` reconstructs an
`EvalResult`-like object as a `SimpleNamespace` that omits `details`, the sole
carrier of `confidence_is_real`. `rlvr_reward_from_result` therefore reads
`confidence_is_real = False` for **every** exported row, which zeroes the
calibration and discrimination reward components and appends a
`confidence_not_real` blocker → every T1/T2 row is `ready_for_training = False`,
**even when `ece`/`auroc` are present and finite in the source**.

**Evidence (file:line).**
- `scripts/autopilot/export_rlvr_environment.py:238-245` — the SimpleNamespace
  carries exactly `tier, quality, reliability, ece, auroc, question_results`.
  **No `details`.**
- `src/autopilot_core/rlvr_tiers.py:259-271` `_confidence_is_real` reads
  `getattr(result, "details", None)`; absent → returns `False`.
- `rlvr_tiers.py:164-170`: `if not confidence_is_real: calibration = 0.0;
  discrimination = 0.0; blockers.append("confidence_not_real")`.
- **Double drop:** even if `details` were passed, `_eval_record`
  (`export_rlvr_environment.py:218-227`) merges only
  `("ece","auroc","routing_distribution")` from `details` and `question_results`
  from nested details — it **never extracts `confidence_is_real`**. So the flag
  is lost at both the record-merge and the SimpleNamespace-construction steps.

**Empirical confirmation (offline pure import, no inference):**
```
EXPORT SimpleNamespace (T1, ece=0.05, auroc=0.82):
  reward=0.7100 ready=False blockers=('confidence_not_real',)
  components: accuracy=0.8 reliability=0.95 calibration=0.0 discrimination=0.0
REAL w/ details.confidence_is_real=True (same numbers):
  reward=0.8460 ready=True  blockers=()
  components: accuracy=0.8 reliability=0.95 calibration=0.95 discrimination=0.82
EXPORT T0 binary: reward=1.0 ready=True (binary branch returns before the gate — unaffected)
```

**What else the SimpleNamespace drops.** `rlvr_reward_from_result` reads only
`tier, quality, reliability, ece, auroc, question_results, details`. The
SimpleNamespace supplies all **except `details`**. Therefore `details` (→
`confidence_is_real`) is the **only** reward-affecting attribute dropped; nothing
else in the reward computation is lost. The summary's `ready_for_training` /
`blocked` / `blocker_counts` (export_rlvr_environment.py:318-336) are
consequently systematically wrong for all continuous tiers (every T1/T2 counted
as blocked with `confidence_not_real`).

**Severity rationale.** Fail-**closed**: it under-credits and cannot impersonate
a quality signal, so it is a utility/correctness defect of the training-data
export, not a safety-gate impersonation. HIGH because it makes the export's
central output field (`ready_for_training` for continuous tiers) uniformly
wrong, and the two production callers that DO feed gating/telemetry
(`autopilot.py:8287` observe-only journal, `safety_gate.py:607` grep-line) pass
the real `EvalResult` and are correct — so the bug is isolated but total within
the export.

---

### F3 — MEDIUM: `ece`/`auroc` default 0.0 (not NaN) → absence-vs-zero ambiguity; latent perfect-calibration impersonation

**Claim.** `EvalResult.ece` / `auroc` initialize to `0.0`
(`safety_gate.py:508-509`) and `_aggregate` sets them to `0.0` when there are no
confidences (`eval_tower.py:3103-3104`). The D4 null-sentinel contract
(`to_grep_lines`, `_fmt_metric` 378-395) only nulls **non-finite** values, so a
never-measured `ece` emits the literal `0.0000` (reads as *perfect* calibration)
and `auroc` emits `0.0000` (reads as degenerate/worst discrimination) —
indistinguishable in the flat METRIC line from a genuine measurement.

**Why it matters.** `_calibration_component(0.0)` = `clamp01(1.0 - 0.0)` = **1.0**
(`rlvr_tiers.py:274-275`): absence-as-zero would score as *perfect* calibration
credit. The **only** thing preventing that today is the `confidence_is_real` gate
(F2's gate, working as intended on the real-EvalResult paths). Disambiguation
exists **in `details`** (`confidence_source_counts` / `confidence_is_real`,
eval_tower.py:3279-3281) but is not carried in the flat METRIC line. SafetyGate
does not consume `ece`/`auroc`, so there is no live gate impact today.

**Boundary note.** This becomes load-bearing only if real ECE is ever admitted to
gating — that is the ESC-7 operator-reserved decision. Flagged mechanically; **no
recommendation to change the default** here. If ESC-7 ever flips, the absence
sentinel for `ece`/`auroc` must be fixed *first* (init to NaN) or the
`confidence_is_real` gate preserved, or absence will impersonate perfect
calibration.

---

### F4 — MEDIUM: duplicated baseline state (state cache vs append-only ledger); drift only warns

**Claim.** The production baseline lives in **two** places:
`autopilot_state.json:baseline_state` (cache) and the append-only
`baseline_promotion` event ledger. `reconcile_baseline_ledger`
(`src/autopilot_core/baseline_ledger.py:75-158`) detects `drift` / missing
snapshots / metric mismatch but only emits **warnings + cutover blockers** — it
never auto-corrects, and `_event_quality_warning` (54-72) merely warns when an
event's `new_quality` differs from the folded `baselines_by_tier`.

**Evidence.** `baseline_ledger_authority_enabled = True` in live state
(operator-authorized flip 2026-06-28 per `baseline_ledger_authority_enabled_note`),
but `baseline_ledger_authority_enabled()` (161-172) additionally requires
`authority_consent("baseline_ledger")` (operator-owned consent file) — so agents
running as the autopilot uid **cannot self-grant** cache removal (good,
fail-closed). Until the operator-gated cutover
(`apply_baseline_ledger_authority` 175-203) removes the cache, the two sources
can silently diverge; only reconciliation diagnostics surface it.

**Severity rationale.** Matches "duplicated state without a single source of
truth," but it is **known and actively reconciled toward** a single source (the
ledger), gated behind operator consent. MEDIUM (leaning LOW) — the reconciler
exists; the residual risk is that drift is warn-only, not enforced, so a
hand-edited state cache could gate promotions inconsistent with the ledger.

---

### F5 — MEDIUM: partial (read-timeout, `error=None`) responses are scored and counted reliable → truncation charges quality, not reliability

**Claim.** A `partial=True` inference result with `error=None`
(`resp.get("partial")`, eval_tower.py:2559) is **not** an error row, so it enters
`scored_results` (3-line quality denominator, 2991) and is scored for correctness
like a complete answer, and it counts as non-error in reliability
(`n_scored/total`, 3039-3040). `partial_count` / `degraded_count` are journaled
(3296-3297) but **do not gate**.

**Evidence / bound.** The orphan/abandoned watchdog path is REL-1-correct —
`mark_abandoned` (2688-2695) sets `error` (so those rows are excluded and counted
against reliability). The gap is narrower: a **read-timeout-partial that still
returned a truncated answer with `error=None`** is scored (typically wrong). A
wave of such truncations depresses quality (risking a spurious regression revert
under F1's cross-era comparison) **without** tripping the 0.8 reliability floor
that would otherwise convert it to a RETRY.

**Judgment call.** Whether a truncated answer should be scored-wrong ("didn't
finish = wrong") or excluded as infra-degraded (REL-1 doctrine) is a design
decision; flagged as a residual infra-impersonation surface, not a clear bug.

---

### F6 — LOW: `reliability = NaN` bypasses the reliability floor

`check()` gates the floor on `math.isfinite(result.reliability)`
(safety_gate.py:1318); a NaN reliability would skip the floor and run the quality
checks over possibly-untrustworthy data. **Not reachable from the producer** —
`_aggregate` always yields a finite fraction (`n_scored/total_count`, `total>0`
guarded at 2987-2988; all error/loader paths set `reliability=0`). Defensive /
public-API-only concern. (Note: the symmetric NaN *quality* case IS handled —
`quality_not_finite` fail-closed at 1304-1306.)

---

### F7 — LOW: `fable5_gate_report` is a phase-readiness aggregator, not a naked-number gate

`scripts/autopilot/fable5_gate_report.py` (docstring line 6: "thresholds owned by
the underlying gates") composes `ready` / `blockers` from sub-gate sections
(phase status, tool-use, restart, W6/W8, eval-coverage). It does **not**
independently re-derive quality/reliability thresholds, and it does not read raw
`ece`/`auroc`/quality to gate. Report shape (`orchestration/reports/
fable5_gate_report_*.json`): `{blockers, next_actions, ready, sections,
summary}`. No provenance defect here; included for completeness of surface #3.

---

## Confirmed-Sound (verified, no defect) — build on these

- **SafetyGate verdicts do not consume ECE/AUROC/calibration_violations.**
  Verified: `check()` (safety_gate.py:1211-1601) references none of them. Only
  `to_grep_lines` (607) computes an observe-only RLVR view on the real EvalResult.
- **REL-1 on producer paths:** quality excludes error rows
  (eval_tower.py:2991-2999); reliability = non-error fraction (3039-3040);
  in-band circuit-open text → error (2448-2464); forced-role fallback → error
  (2466-2490); orphan/abandoned drain → error (2688-2695). Infra errors become
  excluded error rows, not scored-wrong, on all known patterns.
- **Reliability-floor RETRY semantics:** below 0.8 → suppress quality/regression/
  per-suite legs, set `reliability_blocked`, and **do not advance**
  `consecutive_failures` (1308-1324, 1569-1579) — an infra-error trial cannot
  trip auto-rollback or be recorded as a regression.
- **RLVR calibration/discrimination gate:** null-safe fail-closed on
  `confidence_is_real` (rlvr_tiers.py:164-170, 259-271); legacy rows lacking the
  stamp are treated not-real. Required-metric blockers (quality/reliability/ece/
  auroc/question_results) enforced (215-238); sub-chance AUROC earns no credit
  (278-283).
- **Baseline loader hardening:** scale guard (`QUALITY_MAX` 3.0, 803-837),
  above-archive-max guard on load + state-apply (726-741, 906-921), corrupt
  positive-float guard (839-885), atomic write (61-74). Thorough.
- **`update_baseline` eligibility** hard-gated on contention-matrix freshness +
  archive-first ordering + reproduction count ≥ 3 (1639-1687, 1738-1949).
  (Fences the *speed/topology* instrument — not the eval instrument; see F1.)

---

## Prioritized Fix List (file:line targets)

1. **F1 (CRITICAL) — era-fence or reseed the quality baseline for E7.**
   Mechanical options (operator owns the choice):
   - Reseed `autopilot_state.json:baseline_state.{baselines_by_tier,
     per_suite_quality_by_tier, per_suite_counts_by_tier}` and the MAD
     `quality_history_by_tier` from a post-E7 eval before gating post-E7 results;
     and advance a quality-epoch exclusion for the archive-max frontier
     (analogue of `pareto_exclude_before_ts`, which is currently the v7-speed
     epoch 2026-07-20, not E7 2026-07-21).
   - Or stamp `core_id`/era on `baseline_state` and have `check()`
     (safety_gate.py:1341, 1434-1448) + `update_baseline()` (1765) **skip / refuse
     cross-era comparison** the way the strict-same-tier gate already skips a
     missing baseline (1342-1347). Add an `eval_quality` key to
     `active_instrument_eras`.
   - Targets: `safety_gate.py:1341,1434-1448,1765,726`;
     `orchestration/autopilot_state.json` (baseline_state, pareto_exclude_before_ts);
     `orchestration/instrument_eras.yaml` (E4/core row per the file's own TODO).

2. **F2 (HIGH) — thread `confidence_is_real` through the RLVR export.**
   - `export_rlvr_environment.py:218-227` (`_eval_record`): add
     `confidence_is_real` to the keys merged from `details` (and the nested
     `details.details`).
   - `export_rlvr_environment.py:238-245` (`_environment_row`): give the
     `SimpleNamespace` a `details={"confidence_is_real": …}` (or pass the flag
     directly) so `rlvr_tiers._confidence_is_real` can read it. Add a regression
     test asserting a T1 row with real completion-probability confidence exports
     `ready_for_training=True`.

3. **F5 (MEDIUM) — decide partial/degraded handling.** `eval_tower.py:2559` /
   `_aggregate` 3039: choose whether a `read_timeout_partial` (`error=None`)
   should be an excluded error row (REL-1) or remain scored; if the latter,
   document that truncation is deliberately charged to quality.

4. **F3 (MEDIUM, gated on ESC-7) — fix the ece/auroc absence sentinel** *only if*
   the operator decides real ECE re-enters gating: init `EvalResult.ece/auroc` to
   `math.nan` (safety_gate.py:508-509) and set them NaN-on-absence in `_aggregate`
   (eval_tower.py:3103-3104) so `_fmt_metric` emits `null`. Do **not** touch until
   ESC-7 is decided.

5. **F4 (MEDIUM/LOW) — complete or enforce the baseline-ledger cutover.** Drive
   `apply_baseline_ledger_authority` (baseline_ledger.py:175-203) to remove the
   `baseline_state` cache once reconciliation is clean, so the append-only ledger
   is the single source of truth; until then, treat `drift` as a hard blocker
   rather than a warning.

6. **F6 (LOW) — defensively fail-closed on NaN reliability** at
   safety_gate.py:1318 (treat non-finite reliability as below-floor / blocked),
   mirroring the NaN-quality guard at 1304-1306.

---

*Audit artifacts: offline import of `src.autopilot_core.rlvr_tiers` (pure);
read-only reads of `autopilot_state.json`, `autopilot_baseline.yaml`,
`instrument_eras.yaml`, gate report JSON, eval report summary. No inference, no
HTTP, no stack commands, no source edits.*
