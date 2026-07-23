# Designed T1 eval core — `core_v2` — design note & operator promotion checklist

**Date**: 2026-07-23 · **Status**: BUILT, validated, **NOT promoted** (operator gate is intact — see checklist).
**Artifact**: `epyc-orchestrator/benchmarks/prompts/core_v2.jsonl` (1 metadata row + 50 question rows).
**Builds on**: `handoffs/completed/fable5-findings-01-impl-plan.md` §2.0–2.1 (instrument repair: excise dead
items, replace the accidental `legacy_pool_seed_42_n50` sample with a *designed* paired core);
`handoffs/active/autopilot-decision-plane-audit-2026-07-22.md` (E4 quality-era / `core_id` provenance);
the 2026-07-20 operator **difficulty-descending** doctrine (`architect-model-selection-bench.md` §"Difficulty-descending
sequential evaluation").

This designed core replaces the ad-hoc seed=42 draw with a fixed, versioned, decision-value-stratified
50-question T1 instrument built entirely from **a-priori** keys (no inference was run — no model solve-rates
were used to select items, which would be circular). It is inert until the operator authorizes it (below).

---

## 1. What was built

- **File format**: JSONL. Row 1 is the `{"__core_metadata__": true, "core_id": "core_v2", ...}` metadata row;
  rows 2–51 are **full verbatim question rows** copied from the E7 pool, each annotated with a `core_selection`
  block (`tier`, `stable_qid`, `suite_slot_k`, `slot_kind`, `selection_reason`).
- **Why full rows, not id-only references** (the loader `_load_designed_core` supports both): (a) the E7 pool
  has **1,016 duplicate global `id` values**, so bare-id references are ambiguous; (b) full rows make the core
  load **without** the 1.35 GB pool (fast, self-contained, pool-independent at eval time); (c) it matches the
  existing `core_v2_select.py` writer + the on-disk `core_v2_ledger_20260703_min5.jsonl` convention; (d) the
  core is a **frozen instrument** — embedding rows freezes content, and the metadata `built_from.pool_sha256`
  pins the pool build it was cut from for drift detection.
- **Provenance stamped in metadata**: `core_id=core_v2`, `policy_version=core_v2_designed_e7_v1`,
  `dataset_content_sha256` (eval-tower reproducibility stamp, verified to match the load-time recompute),
  `built_from`= `{pool_path, pool_sha256=9b433fa7…, pool_generated_at=2026-07-21T08:45:59Z, pool_total_questions=79479,
  eval_quality_era=E7-eval-instrument}`, full `exclusions` block with rationale, and an embedded
  `selection_report` compatible with `core_v2_promotion_report.py`.

## 2. Selection rules (a-priori, deterministic, seed-free)

The pool was streamed once and filtered with **eval_tower's exact scoreability gates** (`_is_scoreable_question`
+ the row-validation gate: non-empty prompt, `expected` present & non-null, non-empty suite). Only rows that
pass — i.e. rows the eval tower would actually score — are eligible.

1. **Stratify by decision-value, NOT pool size.** Every scoreable **text** suite is represented (≥1 item);
   dominant suites are **capped at ≤2** regardless of row count (`general` 14,042 rows and `coder` 664 rows both
   get 2; `thinking` 11,214 rows and `scoring_verifiers` 6,701 rows get 1). 14 "decision-value" suites — the
   capabilities the swarm actually optimizes the production stack for (coding, math, science/knowledge, factual,
   agentic/routing) — get **2 items** (a per-suite paired unit, per fable5 "per-suite quantum = 2 q/suite"); the
   remaining 22 scoreable text suites get **1 item** each. 14×2 + 22×1 = **50**.
2. **Difficulty spread from the a-priori pool `tier`** (1 easy … 3 hard; model-independent — the only difficulty
   key the pool carries, exactly the "rank by an a-priori, model-independent difficulty key ONLY" rule):
   - Per suite, dedupe candidates by `stable_qid` and sort **(tier asc, stable_qid asc)**.
   - `k=1` → the suite's **median-difficulty** item (closest a-priori proxy to the p∈[0.2,0.8] max-information band).
   - `k=2` → the **hardest** + the **median** (spread with a hard-lean).
   - Within-tier tie-break: `stable_qid = sha1(suite\x00prompt)[:16]` ascending — fully deterministic, seed-free.
   - The file is ordered **hardest→easiest** to match the 2026-07-20 difficulty-descending evaluation doctrine
     (so a saturation-stop early-exit at eval time drops the least-informative items last).
   - **Resulting tier histogram: tier 3 = 21, tier 2 = 17, tier 1 = 12** — a genuine spread with the intended
     hard-lean (the legacy accidental core was the opposite failure: ~16/43 saturated always-correct items).

No random seed is used anywhere; re-running the builder on the same `pool_sha256` reproduces the identical 50 ids.

## 3. Per-suite composition (50 items / 36 suites)

| cluster | suite | slots | tiers | selected ids |
|---|---|---|---|---|
| agentic/routing | agentic | 2 | [3, 2] | bfcl_030, bfcl_007 |
| agentic/routing | mode_advantage | 2 | [3, 2] | ma_multi_006, ma_iter_013 |
| agentic/routing | mode_advantage_hard | 1 | [3] | ma_hard_code_011 |
| agentic/routing | real_suite_v1 | 1 | [2] | real_suite_v1_0026 |
| agentic/routing | skill_transfer | 1 | [1] | st_plan_math_003 |
| code | bigcodebench | 2 | [1, 1] | bcb_BigCodeBench/1028, bcb_BigCodeBench/0 |
| code | coder | 2 | [2, 1] | humaneval_HumanEval_52, mbpp_0106 |
| code | cruxeval | 2 | [2, 1] | cruxeval_input_0156, cruxeval_output_0590 |
| code | debugbench | 2 | [3, 2] | debugbench_number-of-atoms_java, debugbench_queries-on-number-of-points-inside-a-circle_cpp |
| code | livecodebench | 2 | [3, 2] | leetcode_dungeon-game, leetcode_flip-equivalent-binary-trees |
| code | scoring_verifiers | 1 | [2] | sv_MBPP-R+_Mbpp/425::sol4 |
| code | usaco | 1 | [2] | usaco_silver_836_silver_multiplayer_moo |
| factual/retrieval | hotpotqa | 2 | [3, 2] | hotpot_comparison_5a87868c5542996e4f308828, hotpot_bridge_5a75e06155429976ec32bc60 |
| factual/retrieval | simpleqa | 2 | [3, 1] | simpleqa_general_02965, simpleqa_general_03966 |
| factual/retrieval | web_research | 1 | [1] | wr_multi_006 |
| instruction | instruction_precision | 1 | [1] | ifeval_2801 |
| long-context | leval | 1 | [3] | leval_legal_contract_qa_439 |
| long-context | long_context | 1 | [2] | needle_023 |
| long-context | longbench | 1 | [3] | longbench_671b3fa1bb02136c067d5353 |
| long-context | needle_parameterized | 1 | [2] | needle_16384_0.50 |
| long-context | ruler | 1 | [1] | ruler_niah_4096_25 |
| long-context | zeroscrolls | 1 | [2] | zeroscrolls_space_digest_460 |
| math/quant | aime | 2 | [3, 3] | aime_2024-II-15, aime_2024-II-1 |
| math/quant | math | 2 | [3, 1] | math500_Precalculus_00068, gsm8k_01110 |
| math/quant | aime25 | 1 | [3] | aime25_2025-II-12 |
| math/quant | olympiadbench | 1 | [3] | olympiadbench_combinatorics_2431 |
| science/knowledge | general | 2 | [3, 2] | mmlu_abstract_algebra_00028, mmlu_professional_accounting_10382 |
| science/knowledge | gpqa | 2 | [3, 3] | gpqa_Chemistry (general)_0329, gpqa_Organic Chemistry_0308 |
| science/knowledge | mmlu_pro | 2 | [3, 3] | mmlu_pro_health_06250, mmlu_pro_chemistry_04051 |
| science/knowledge | gpqa_diamond | 1 | [3] | gpqa_diamond_2305aa77f736 |
| science/knowledge | gpqa_diamond_cot | 1 | [3] | gpqa_diamond_cot_64d1b920ee51 |
| science/knowledge | longcot_mini | 1 | [1] | longcot_mini_18 |
| science/knowledge | omniscience | 1 | [2] | omniscience_Economics_0066 |
| science/knowledge | physics | 1 | [2] | phybench_electricity_55 |
| science/knowledge | physreason | 1 | [2] | physreason_cal_problem_00292_sq1 |
| science/knowledge | thinking | 1 | [1] | hellaswag_38608 |

**Totals**: 50 items · 36 suites · 14 double-slot + 22 single-slot · tier histogram {1:12, 2:17, 3:21}.

## 4. Exclusions & rationale

| excluded | scope | rationale |
|---|---|---|
| `aa_lcr`, `document_extraction`, `gaia` | whole suite | 0 rows in the E7 pool (absent-source, loud) — nothing to select. |
| `tulving_episodic` | whole suite | Scorer `f1_list` unimplemented (**SCORE-25**); rows are structurally unscoreable/misscored — excluded per task directive. |
| **`vl`** | whole suite | **Design decision (flag for operator review).** Multimodal (chart images); the T1 core runs on the CPU **text** worker, which cannot read `image_path` → historically **0/376**, zero Fisher information. Dropped per fable5 §2.1 "drop always-0 items — zero Fisher information." Not in the task's explicit exclusion list, so calling it out: re-add once the vl eval path is fixed and shows nonzero discrimination. |
| 8 `known_dead_instrument_items` | item-level | From `instrument_eras.yaml`: `usaco/{usaco_silver_1326,usaco_silver_759}`, `instruction_precision/{ifeval_2292,ifeval_3691}`, `bigcodebench/{bcb_BigCodeBench/228,bcb_BigCodeBench/51}` (empty-`expected` never-scored / pandas absent from venv), `vl/{chart_test_0452,chart_test_1401}` (unresolved 0/376). |

The metadata row carries this exclusion block verbatim (with rationale) for auditability.

## 5. Validation performed (offline; no inference, no network, no process management)

- **Loader** (`EvalTower._load_designed_core("core_v2")`, real code, default path): loads 50 questions,
  metadata `core_id=core_v2`, `policy_version=core_v2_designed_e7_v1`, **all 50 scoreable**, 36 suites,
  recomputed `dataset_content_sha256` **matches** the stamped value (order-stable).
- **Activation guard** (`designed_core_activation_guard`, fail-closed): against the **live** registry →
  `ok=False, status=missing_core_era` (operator gate intact); against a temp registry carrying the E4/core
  row → `ok=True, status=authorized`.
- **Promotion report** (`core_v2_promotion_report.py --core-id core_v2`): the artifact passes **all** artifact +
  selection-evidence checks; the **only** reported blocker is `instrument era: no active autopilot_quality
  instrument-era row declares a core_id` — i.e. the operator step below.
- **pytest** (orchestrator `.venv`, targeted): **58 passed** —
  `tests/unit/test_core_v2_real_file.py` (7 new, loads the real committed file),
  `test_eval_tower_instrument_repair.py` (loader+guard, 29),
  `test_instrument_era_guard_eval_quality.py` (10), `test_core_v2_select.py` (6),
  `test_core_v2_promotion_report.py` (2), `test_core_v2_calibrate.py` (4).

---

## 6. OPERATOR CHECKLIST — promotion (human-owned; do NOT let an agent perform these)

The measurement trust boundary (instrument-era registry) is **human-amendment-only** (MEASUREMENT.md §5).
Activation is deliberately blocked until the operator appends the row below.

- [ ] **Review** `benchmarks/prompts/core_v2.jsonl` (metadata + 50 items) and this note, incl. the **`vl` exclusion**
      decision (§4) — confirm keep-excluded, or ask for a vl-inclusive rebuild.
- [ ] **Append the quality/core era row** to `epyc-orchestrator/orchestration/instrument_eras.yaml` under `eras:`
      (this is the "E4 opens when the instrument repair lands…" row reserved at `instrument_eras.yaml:118-120`,
      adapted to the current E5/E6/E7 era world). **READY TO PASTE** (set `from` to the activation moment):

```yaml
  - id: E4-quality-core-v2
    from: "2026-07-23T00:00:00Z"        # operator: set to the activation instant (UTC)
    scope: autopilot_quality
    core_id: "core_v2"
    policy_version: "core_v2_designed_e7_v1"
    note: >
      Designed T1 eval-core era. Replaces the accidental legacy_pool_seed_42_n50 T1 draw
      with the fixed, versioned, decision-value-stratified core_v2 (50 items / 36 scoreable
      text suites; a-priori pool-tier difficulty spread {1:12,2:17,3:21}; dead items excised;
      vl + tulving_episodic excluded). Artifact:
      benchmarks/prompts/core_v2.jsonl, dataset_content_sha256=4c464977b01b94a6c50d13addcd0a660ff948554306254e00748eed9b759e99c,
      built_from pool_sha256=9b433fa7f9d067c076f41fff18637c0246bfeab331dfc7f7052244e6db3238af
      (question_pool.jsonl, E7-eval-instrument, 79,479 rows, 2026-07-21).
      RECONCILIATION: all E<=3 T1 quality frontiers/baselines and the legacy_pool_seed_* draws
      are RETIRED VIEWS under this era — no cross-era T1 dominance; re-measure within era.
      Pairs with the E7-eval-instrument (scope eval_quality) scorer/pool boundary.
```

- [ ] **Re-run the validator** after appending (must flip to promotion-ready):
      `uv run python scripts/autopilot/core_v2_promotion_report.py --core-id core_v2 --core-path benchmarks/prompts/core_v2.jsonl --eras-path orchestration/instrument_eras.yaml --json`
      → expect `promotion_ready: true`, empty `blockers`.
- [ ] **Launch autopilot with** `AUTOPILOT_T1_CORE_ID=core_v2` (the eval tower resolves the file at
      `benchmarks/prompts/core_v2.jsonl` automatically; `AUTOPILOT_T1_CORE_PATH` is only needed for a non-default
      location). Optional: enable the W6 rotating audit block (`AUTOPILOT_W6_AUDIT_BLOCK=1`) so fresh pool items
      accrue per-item difficulty stats toward a future empirical `core_v3` refresh.
- [ ] **Restart** so the running process picks up the env (a stale process keeps the legacy sampler).
- [ ] **Verify live**: first T1 trial's `eval_details` shows `core_id=core_v2`,
      `core_selection=designed_core`, `n_questions=50`.

**Refresh policy**: `core_v2` is frozen. Any item swap bumps to `core_v3` with a new era row (never edit this
one). Once the audit block has accrued per-item solve stats over this era, an empirical medium-difficulty
refresh (`core_v2_select.py --source ledger`) can supersede it — again operator-gated.

## Operator directive on vl (2026-07-23): FIX-NOW, NO DEFERRAL

The "promote without vl / core_v2.1 later" branch is DELETED by operator direction. Whatever the
0/376 diagnosis finds, the instrument is fixed FIRST and core_v2 includes vl from birth (composition
amended, sha recomputed, one era row). Escalation ladder by finding depth: code/payload/schema →
session fixes immediately; launch-config (mmproj flag) → stack-script fix on idle stack; artifact
(re-download mmproj/model) → session executes, hours-scale; MODEL-choice (VL model itself wrong) →
operator decision presented immediately with options, never parked. The reseed sequences after the
vl fix — instrument correctness precedes gate liveness, consistent with every choice this campaign.
