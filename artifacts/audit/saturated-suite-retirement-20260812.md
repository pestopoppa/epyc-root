# Saturated judge-suite retirement — evidence report (2026-08-12)

**Task** (handoffs/active/architect-model-selection-bench.md:173): retire — not harden — the
judge suites `general` (10/10 both-perfect), `thinking` (9/10), `math` (8/9), which carry no
discriminating information at the ≥27B tier (2026-08-02 head-to-head,
research `data/judge_suite_headtohead_20260802/README.md`, research commit `7d7bc8d3`).
Delivered as working-tree edits on research `main` + this report; nothing committed.

## What changed (research repo, `/mnt/raid0/llm/epyc-inference-research`)

| File | Change |
|---|---|
| `benchmarks/prompts/v1/suite_retirements.json` (NEW) | Machine-readable retirement sidecar, schema `suite_retirement.v1`. Entries for `general`/`thinking`/`math`: `tier: 27B+`, `min_params_b: 27`, measured both-perfect (`10/10`, `9/10`, `8/9`) and rates (1.0/0.9/0.89), `measured: 2026-08-02`, evidence pointers (head-to-head README, commit `7d7bc8d3`, epyc-root handoff), reason text. |
| `scripts/benchmark/score_with_claude.py` | `:77-105` `RETIREMENT_SCHEMA`/`SUITE_RETIREMENTS_PATH`/`SuiteRetirementError` + fail-closed `load_suite_retirements()` (missing/unparseable/wrong-schema/malformed-entry all raise); `:141-148` `parse_model_params_b()` (largest bare `<num>B` token, `-A10B` active-expert suffixes excluded); `:151-172` `retirement_stamp()` (tier-scoped; unresolvable size = at-tier, fail-closed); `:339-345` main() refuses via `parser.error` (exit 2) before opening any input when the sidecar is bad; `:369-376` model tier from `model_path` → role → config; `:403` per-row stamp; new CSV column `suite_retirement` (after `score_eligibility`, both eligible and ineligible branches); `:490-540` summary: comparative Total/Passed computed over non-retired rows only (labelled "(discriminating suites only)" when mixed), per-suite lines bannered `*** NON-DISCRIMINATING: … ***`, `*** SUITE RETIREMENT ***` block, and **exit 3** with a `NO DISCRIMINATING SUITES IN THIS RUN` wall when every scored suite is retired. Scores are still recorded — retirement blocks the comparative read, not the data. |
| `scripts/benchmark/rebuild_summary.py` | `:20-31` imports the loader from `score_with_claude`; `:60` `RETIRED_CELL_STAMP = "!RETIRED-NONDISCRIMINATING"`; `:63-77` `retired_suite_stamp()` (same tier fail-closed rule, from model name); `:80-90` `aggregate_totals()` — cross-suite `total`/`pct` in `summary.csv` now exclude stamped suites; `:305-328` cells for retired-at-tier suites render `c/t !RETIRED-NONDISCRIMINATING@27B+`; `:479-495` main() loads the sidecar first and `SystemExit`s (non-zero) without writing `summary.csv` if it is missing/invalid. |
| `benchmarks/prompts/v1/{general,thinking,math}.yaml` | 6-line comment header (comment only — parsed content verified unchanged, 10 prompts each) pointing at the sidecar and the consumers. |
| `scripts/benchmark/test_score_with_claude.py` | +9 tests (see below), +`pytest` import, 3 local helpers. |
| `scripts/benchmark/test_rebuild_summary.py` (NEW) | 3 tests for the rebuild path. |

Root repo: `docs/reference/architect-bench-runbook.md` §8 — dated "Retired judge suites
(2026-08-12)" bullet; `handoffs/active/architect-model-selection-bench.md:173` checkbox flipped.

**Not touched**: historical result artifacts (`benchmarks/results/**`, `data/judge_suite_headtohead_20260802/**`),
suite question content, `benchmarks/results/reviews/summary.csv` (not regenerated — next rebuild picks up the stamps).

## Property each test pins

`test_score_with_claude.py`:
1. `test_repo_retirement_sidecar_binds_the_three_saturated_suites` — the *shipped* sidecar names all three suites with the measured rates, `min_params_b=27`, `measured=2026-08-02`, and a `judge_suite_headtohead_20260802` evidence pointer. Deleting/gutting an entry fails here, visibly and counted.
2. `test_missing_retirement_sidecar_refuses_loudly_before_scoring` — sidecar absent ⇒ SystemExit(2), "FAIL-CLOSED" on stderr, judge never called, **no CSV written**. Absence of the guard's data is an error, never an implicit "nothing retired".
3. `test_invalid_retirement_sidecar_refuses_loudly` — wrong schema ⇒ same refusal (tamper ≡ missing).
4. `test_retired_suite_is_recorded_but_supports_no_comparative_read` — all-retired run: score still recorded (3), row stamped with the 2026-08-02 evidence, banner + "NO DISCRIMINATING SUITES" printed, **no `Total:` line**, exit 3.
5. `test_mixed_run_total_covers_only_discriminating_suites` — retired+live run: headline is `Total (discriminating suites only)` over the live rows only; retired row stamped, live row not.
6. `test_non_retired_suite_is_unaffected_at_tier` — COMPLIANT PATH: `coder` at 27B scores exactly as before (plain `Total:`, no banner, empty stamp, exit 0).
7. `test_sub_tier_model_is_not_stamped` — COMPLIANT PATH: retirement is tier-scoped; a 7B run of `general` is untouched.
8. `test_unresolved_model_tier_fails_closed_to_stamped` — unparseable model size cannot certify sub-tier ⇒ stamped, with `model-tier-unresolved` in the stamp.
9. `test_parse_model_params_b_naming_conventions` — `122B-A10B`→122, `26B-A4B`→26, `30b-a3b`→30, no-size→None.

`test_rebuild_summary.py`:
10. `test_retired_cell_stamp_applies_at_tier_only` — stamp at 27B and on unresolved size; clean at 7B and for live suites.
11. `test_aggregate_totals_exclude_stamped_suites` — stamped suites never feed the cross-suite total.
12. `test_rebuild_refuses_without_retirement_sidecar` — missing sidecar aborts the rebuild (non-zero SystemExit carrying "FAIL-CLOSED"); no `summary.csv` written.

## Test counts

Runner: pytest 9.1.1 (scratchpad venv; repo ships no pytest — same version as the stale
`__pycache__` pyc). Scope: the three test files covering touched modules
(`test_score_with_claude.py`, `test_rebuild_summary.py`, `test_capture_contract_guard.py` —
the last is the pre-existing static contract guard over `score_with_claude.py`, unmodified).

- **Before**: `--collect-only` 12 tests (6 + 0 + 6); run: 12 passed.
- **After**: `--collect-only` 24 tests (15 + 3 + 6); run: **24 passed**.

Mutation checks (each mutation applied, tests run, then reverted; final tree verified
mutation-free and 24/24 green):

| Mutation | Result |
|---|---|
| A: sidecar file deleted | **11 failed** — including 3 *pre-existing* main() tests, proving the runtime gate refuses to score at all |
| B: `general` entry deleted from sidecar | **5 failed** (sidecar-binding test + all general-path behavior tests, both consumers) |
| C: `retirement_stamp` in scorer neutered (`entry = None`) | **3 failed** (scorer behavior tests) |
| D: `retired_suite_stamp` in rebuild neutered | **1 failed** (rebuild stamp test) |

All failures are ordinary counted pytest failures — nothing asserts in a `main()` and nothing
launders to a plausible zero. YAML integrity re-verified after the comment headers: all three
suites parse to the identical 10-prompt structure. The static capture-contract guard still
passes (no prompt/response slices introduced; all required fragments intact).

## Boundary honestly stated

The stamp travels in the review CSV (`suite_retirement` column) and both in-repo consumers
enforce it, but a hypothetical out-of-repo consumer reading `claude_score` raw and ignoring
every other column can still average retired rows — preventing that would require poisoning
recorded scores, which the task forbids (retirement is forward-looking, not data destruction).

## Hardened-v3 design sketch (for the bench owner to take or decline — no content authored)

1. Ceiling target: ≤20% both-perfect at the 27B/35B pair, measured on a pilot before full runs (runbook §4 pilot rule).
2. Sourcing: draw from the already-validated non-saturated instruments rather than authoring from scratch — `olympiadbench_hard`-style Expression/Tuple items for math, LiveCodeBench-hard/SWE-adjacent slices for coder-adjacent reasoning, GPQA-diamond-CoT misses for thinking.
3. Per-item difficulty key must be a-priori and model-independent (runbook §8), so difficulty-descending early stopping stays valid.
4. Every candidate item needs a verified answer key (the two v1 defects shipped with their own keys documenting the defect — add a key-self-consistency check to intake).
5. Judge: current stripped generic-anchor rubric; absolute levels start a fresh era at the v3 boundary (eval-instrument era row).
6. Validation: paired pilot (n≈20/suite) on the 27B-vs-frontdoor pair; require ≥30% discordant-or-imperfect items before ratifying; wire results into the belief kernel at creation (write-side hook).
7. Un-retirement path: a v3 suite re-enters by amending `suite_retirements.json` (governance edit, evidence cited) — the guard needs no code change.
