# Loop-belief redesign for the Vidya belief kernel — design and build plan

Author: design subagent (read-only), 2026-10-21. Status: PROPOSED. Main reviews, then dispatches.
Nothing here was implemented, pushed, or written to the canonical ledger. Scratch outputs live in
this directory (`serving_sources_summary.json`, `ledger_examples.json`).

Code citations use the ROOT hub view `/mnt/raid0/llm/views/epyc-root-main` @ `e2e71aa4f` (tracks
origin/main and contains VB-LOOP-SCOPE `0ed65d1c5`). `/workspace` main is 513 commits behind and
lacks `loop_beliefs.py`. Research citations (`L/` = `scripts/kernel_rnd/autokernel/loop/`) use the
worktree `/mnt/raid0/llm/worktrees/corpus-flagoff-research-20261021` (branch contains
`b7b23fe1c`; the research main checkout at `e0f5a101a` does not). Orchestrator citations use
`/mnt/raid0/llm/epyc-orchestrator` main @ `9aa15a65` (contains `955b6f28`).

**Dates (updated by main thread 2026-10-21):** trial evaluation moved to **2026-11-30**; both loops
live by **~2026-11-23**. A consumer's window starts at its first live receipt, so Phase 1 is still
scheduled early (build by 10-28, verified by 10-30): every week earlier is a week more of window.

---

## 0. Verdict in one paragraph

The loops already produce the beliefs they need. AutoKernel `experiments.db` holds 395 substantive
attempts across the DS41, Q38FN and 27B stores, each with a mechanism id, a target symbol, a
falsifier, a status and (when timed) an effect against a stated noise floor. The 125 serving A/B
sources hold paired medians, effects, floors and a decisive flag. Three defects keep this out of
the planner prompt:

1. **The frame path drops every value.** `to_frames` writes no `value`, `unit`, effect or
   mechanism (`scripts/vidya/claim_tuple.py:668-719`). The serving adapter says so itself:
   "ClaimTuple frames intentionally do not carry those fields"
   (`adapters/autokernel_legacy_serving.py:281`).
2. **Only one record kind is projected.** Refusals, nulls, regressions and serving floors never
   reach the ledger, so negative results do not exist there.
3. **Scope matching is flat.** A claim scoped only to `device` matches every target on that device
   (`loop_beliefs.py:343-363`). That is why five CPU models all get the same 12 INF-70 and serving
   claims, and why a model with no claims of its own looks as if it has some.

The fix:

- Extend the carrier with an inert, value-bearing `observation` block plus a few more scope keys.
- Project the loops' own records (serving A/B v2, experiments, serving floors) with the same
  ladder, keeping negatives as first-class claims.
- Make the reader tier its matches (target / sibling weights / host) and render the numbers.

`claim_tuple.grade()` stays the only grader. No ladder is added, and no grade moves.

---

## 1. Diagnosis (verified 2026-10-21)

| # | Finding | Evidence |
|---|---|---|
| D1 | Frames carry no measured values. `ClaimTuple.value` and `unit` exist (`claim_tuple.py:127,137`), but `to_frames` emits only `display_text`, `grade`, `protocol_id`, `reps`, `category`, `metric_direction` (`:686-718`). The 230 backfilled serving claims all have the same text: "<arm> observed median aggregate serving rate; protocol and scientific witnesses unqualified" (`legacy_serving.py:189`). | ledger sample, `ledger_examples.json` |
| D2 | Device-only scope matches every model. `applicability_matches` accepts a claim that declares `device` alone (`loop_beliefs.py:346`). The INF-70 read-bandwidth claims carry `{backend, device}` only. The render then round-robins kinds into a 12-claim cap (`:723-742`) and keeps only the newest run per source kind (`:576-590`), which gives 6 INF-70 lines plus 6 serving lines. | `/mnt/raid0/llm/tmp/belief-loop-consumers-20261021/final-proof/ds41-section.txt` |
| D3 | The live targets have no target-scoped claims. DS41-1017 (`DeepSeek-V4.1-Flash-1017-MXFP4-experts-00001-of-00009.gguf`) has never run (campaign README). Qwen3.6-35B-A3B-MTP-Q8_0 and Qwen3-VL-30B have no AutoKernel or bench records. 27B GPU has 13 experiment rows, all refusals, and those are not projected. | §3 |
| D4 | Identity is per arm, not per experiment. Anchor and candidate are separate claims with identical text (`legacy_serving.py:185-200`). The effect, floor, decisive flag and `mechanism_id` are in the native source but in no frame. | source sample §3.2 |
| D5 | Negative results are absent. `gate_refused`, `measured_null`, `regression`, `patch_rejected` and `measured_divergence` rows (DS41 store: 21/21/8/30/1) have no projection. 10 serving receipts are refused outright ("unsupported authority", `/mnt/raid0/llm/tmp/belief-loop-consumers-20261021/vb-loop-scope/backfill-*.json`). | §3.1 |
| D6 | Adapters exist for exactly the Phase-1 targets but have no input: `kv_quant_27b_v10` (0 sidecars), `ds41_1017_validation`, `dflash2_experimental_runtime` (DF2-4 is pre-hook), and `autopilot_journal` (paused since 2026-08-11). The ledger has 0 frames from any of them. | sub-report C; `grep -c kv-quant-27b ledger.jsonl` = 0 |
| D7 | AutoPilot trials are not model-scoped at all. Journal rows carry no role, model, quant or device (0 `.gguf` hits in 1,372 trials). Every trial is an end-to-end eval over the mixed lineup. The AP-55 `infra_fingerprint` field is written by code (`autopilot.py:11375`) but by no on-disk row. | sub-report B |

| D8 | No AutoKernel planner turn has ever seen a belief section. 933 v1 belief receipts (2026-09-25 → 10-11) all have `section_bytes: 0`: 930 `inapplicable_target`, 3 (27B) `ledger_missing`. The reply schema's `relies_on_claims` (`L/actors.py:1575`) is never mentioned in the `_HYPOTHESIS_TASK` JSON template (`:3130-3153`), only in the belief section's tail, so even a non-empty section would rarely draw a declared reliance, which VB-LOOP-TEST (b) requires. | sub-report A §1-2 |

The ledger (30,813 frames) is 89% research intake. The 1,580 unscoped measurement frames are
aux/governed receipts, embedder placement, CI and similar. None of them answers a loop question,
and they stay as they are (§7).

---

## 2. The questions, from demand

Each question is grounded in a code path the planner or critic already runs, or in a stored turn.

**What the AutoKernel planner already has.** `AgentPlanner.propose` (`L/actors.py:3648`) builds
the prompt from `render_context` (`:2503`), in this order:

1. selected target
2. standing constraints (program.md "Settled")
3. `ALREADY IMPLEMENTED AT HEAD` (`:2541`)
4. pending hypotheses
5. formed-never-measured
6. profile
7. diminishing-returns escape (`:2703`)
8. family-level escape (`:2769`)
9. `Characterised — do NOT re-measure` (`:2819`, same-epoch only)
10. runtime treatments already measured (`:2840`)
11. `## Already tried` (`:2854`). This is the **12 newest rows**, plus every current-epoch keep and one row per abstained family, capped at 40.
12. shared historical mechanisms (`:2939`)
13. serving observations (`:2949`)
14. rejection feedback (`:2958`)
15. inbox

The belief section is appended **last** (`:3679-3680`). `prior_experiments` come from the store's
own `ExperimentStore.recall` (`L/run.py:1780`).

The substrate therefore must not duplicate this in-store memory. It must supply four things the
store cannot:

- memory **across stores and campaigns**: the fresh DS41-1017 store, and the parallel `store` and
  `store-b0ba1d427` lanes;
- **durable per-mechanism records** that do not age out of the 12-row window;
- **measured** floors and anchors;
- **cross-loop** facts (INF-70, kv-quant, AutoPilot).

The three stored turns below show each gap.

- **Turn B** (DS41 store, `akm-ds41-dense-q8-seed-prepass-*`). A `measured_null` of −0.564% on
  09-30 aged out of `## Already tried` and was excluded from `Characterised` as cross-epoch. The
  10-01 prompt (`state-run10i/…/20261001T154722-codex-…stderr` l.1186-1210) did not show it. The
  next variant hit the same `gate_refused` mnpack error, then a **decisive regression of −3.41%**.
- **Turn C** (27B, `…/actor-replies/20261004T175213…`). The planner estimated that about 60% of the
  fixup "must disappear to plausibly clear the approximately 2.7% serving floor". The **measured**
  floor was 0.807% (store `serving-floor.q27b-…json`). Two lanes proposed the same mechanism 6 s
  apart, and `## Already tried` read "(nothing yet)" even though a critic rejection was already
  recorded.
- **Turn A** (Q38FN b0ba). `akm-cpu-mmid-rows-multitoken-reuse` was abstained 12 times with the same
  re-derived "already implemented" text. That text also wrote off IQ3_S grid-gather, which was later
  **kept at +0.593%**.

| Q | Question at planning time | Grounding |
|---|---|---|
| Q1 | **Was this mechanism already tried on this target, and what happened?** (outcome, effect, floor, build/epoch) | Turns A and B. The AutoKernel critic already answers this from the store's own `experiments.db`: `hypothesis_rejected` reason "This mechanism has already been measured under the selected conditions. On 2026-10-04 … akm-ds41-mmid-verify-block-qact was measured null at -0.721% against the 3.412% floor … epoch c42cd5615dfb" (ak-ds41 store, attempt `ca9e28d9…`). `experiments.md` is generated "so every attempt this loop has made" is visible (27B store header). **That memory is per store.** The fresh DS41-1017 store has none, so the substrate's job is to carry it across stores, campaigns and loops. AutoPilot equivalent: the AP-53 fold "Previously Rejected Configs" (`rejected_mutation_ledger.py:337-346`) and the 276 critic issues of the "repeat / already" type (sub-report B §2). |
| Q2 | **Which variants are dead ends here, and why?** (correctness refusal, decisive regression, null within floor, scope refusal) | 27B store: 5 × `gate_refused` "MUL_MAT failed on ROCm0" on 2 mechanisms (`experiments.md`). The planner re-proposed `akm-q8-j16-single-tile-streamk-five-cta` and got "byte-identical to the patch the correctness gate has already refused twice". DS41: `regression` "DECISIVE REGRESSION — effect -8.215% exceeded the 3.412% noise floor". |
| Q3 | **What is the measured serving rate and noise floor for this model/quant/device/recipe?** | Turn C guessed a 2.7% floor; the measured floor was 0.807%. `serving-floor.q27b-9a3f1392a-gpu-dflash2-np1….json`: median 81.12 t/s, floor 0.807%, n=10, GPU residency proven. AutoPilot example A (planner_archive 2026-08-09T14:25): "every trial from #1480–#1503 fails … Throughput floor: ~9–16 t/s < 36.6 t/s (80% of baseline 45.8)… not caused by the mutated variable". The planner had no per-model rate record to localise the collapse. |
| Q4 | **What worked, by how much, and does it still stand on the current build?** (keeps with effect, build sha / epoch, contested or withdrawn status) | `kept` rows carry `effect_fraction` plus `claims.effect.status: verified` (payload). The do-not-repeat channel and the VB-LOOP-TEST criterion (b) "verified result reused" need the number and the epoch. |
| Q5 | **What transfers from a sibling target?** (same architecture, other weights/recipe) | DS41-1017 starts empty, but DS41-Q4 has 69 mechanisms tried, with 9 decisive positive and 9 decisive negative results. The 1017 README pins the champion `dd3d9721c` and the old prompt token list. Rows that are not quant-specific (rmsnorm, OMP placement, metadata reuse) are candidates for transfer. |
| Q6 | **What do we know about this op/symbol/shape?** (prior effects on `ggml_iqk_try_mul_mat_id`, `tinyBLAS_Q0_AVX::gemm4xN`, `launch_mul_mat_q`) | Experiment rows carry `target_surface` and `target_symbol` (DS41: 27 symbols, Q38FN: 18, 27B: 1). Gate details carry `test-backend-ops` op/shape lines (payload `gates[].detail`). |
| Q7 | **What hardware ceiling applies?** (host read bandwidth, roofline) | INF-70 claims (already value-bearing in text). Useful as background, but **not** evidence about a model. This is the D2 failure. |
| Q8 (AutoPilot) | **Has this config knob been tried in this stack regime, with what q/s outcome?** | The journal `config_diff` and `keep_revert_decision` exist. There is no regime scope until AP-55 `infra_fingerprint` rows exist. This is prospective only (§5.3). |

Status semantics the planner needs on every answer: verified, refuted, contested, withdrawn (§4.3).

---

## 3. Sources (where the answers live today)

### 3.1 AutoKernel `experiments.db` (per store, SQLite, read-only)

Schema: `attempt_id, recorded_at, campaign_id, epoch_sha256, mechanism_id, target_surface,
target_symbol, statement, falsifier, status, effect_fraction, exact_effect, target_effect,
refusal_reason, result_sha256, spawn_parent, branch_id, width, depth, payload(JSON)`.

The payload keys include `research_scope` (backend, measurement_surface, **model {path, sha256}**,
quant, recipe), `comparison` (the full A/B with residency), `gates` (compile/correctness with
`test-backend-ops` detail), `claims.effect.status`, `champion_head`, `belief_receipt_id` and
`candidate_diff_sha256`.

| Store | rows | substantive* | distinct mechs | with effect | symbols | epochs | rows with `research_scope`+`comparison` |
|---|---|---|---|---|---|---|---|
| ak-ds41-cpu-decode-20260923/store | 385 | 218 | 99 | 79 | 27 | 21 | 59 |
| …/store-b0ba1d427 | 444 | 48 | 33 | 23 | 10 | 6 | 20 |
| …/store-run9d-cor-5a60152ae | 5 | 1 (gate_refused) | — | 0 | — | — | 0 |
| ak-q38fn-cpu-decode-20261003/store-b0ba1d427 | 331 | 114 | 59 | 50 | 18 | 9 | 42 |
| ak-27b-gpu-verify-20261004/store | 13 | 13 | 2 | 0 | 1 | 1 | 0 (5 rows have `gates`) |
| ak-ds41-1017-cpu-decode-20261021/store | none (never launched) | — | — | — | — | — | — |

\*Excludes `planner_transient`, `abstained`, `stopped_mid_formation`, `lane_error`, `resume_rejected`, `superseded`.

Status vocabulary in the DS41 store: kept 22, keep_candidate 5, measured_null 21, regression 8,
gate_refused 21, patch_rejected 30, integrity_refused 1, measured_divergence 1, hypothesis_rejected
38, refused_duplicate 1, anchor_verified 18, runtime_observed 3, measurement_invalid 2,
anchor_guard_excursion 3, …

**Scope caveat.** Refusal rows carry no `research_scope`. Their scope is the store's, pinned by the
campaign manifest (`inputs*/campaign-manifest.json`, `targets*/`). This is the same "producer
contract pins the whole scope" basis the reader already accepts for `SOURCE_SCOPES`
(`loop_beliefs.py:366-420`).

### 3.2 AutoKernel serving A/B sources (`<store>/serving-beliefs/sources/<capture>.json`)

There are 125 sources: DS41-Q4 82 (`store`, `store-b0ba1d427`, run8/run9d) and Q38FN 43. Each is
5.6–47 MB because it carries residency samples. Schemas: `serving_ab.v1/v2` and
`serving_runtime_ab.v1`.

Fields: `mechanism_id`, `recorded_at`, `epoch`, `comparison.{metric=aggregate_tok_s,
anchor_tok_s, candidate_tok_s, anchor/candidate_samples[n], effect, effect_pct, noise_floor_pct,
decisive, pairs, np, recipe, recipe_env, recipe_hash, measurement_plan, residency.backend,
belief_capture.inputs.{recipe.model, build_paths, resolved_arms.execution_digest}}`.

Outcomes by model:

| Model | captures | mechanisms | decisive + | decisive − | date range |
|---|---|---|---|---|---|
| DS41-Q4 | 82 | 69 | 9 | 9 | 2026-09-26 → 10-08 |
| Q38FN | 43 | 40 | 3 | 1 | 2026-10-05 → 10-08 |

Summary: `serving_sources_summary.json`. The canonical ledger already holds 230 v1 arm claims
from these sources (152 DS41, 78 Q38FN), identity-only per D1/D4. 10 receipts are refused
(`protocol_id != ""` / attestation recorded → "unsupported authority",
`legacy_serving.py:93-96`).

`paired_loadgen` `serving_ab.v1` records carry no `belief_capture` and are skipped by export.
That gap is already filed as VB-AK-PAIRED-LOADGEN-WRITE.

### 3.3 AutoKernel serving floors (`<store>/serving-floor.<recipe>.requests-<digest>.json`)

Schema `epyc.autokernel.serving_floor.v1`: `median_tok_s, floor_pct, floor_ci, n, cv_pct,
spread, metric, unit, recipe, recipe_hash, request_digest, residency{backend, gpu_residency,
proven}, headline_admissibility{mde_pct, power, n_per_arm}`.

Found: 27B GPU `q27b-9a3f1392a-gpu-dflash2-np1`, with median 81.12 t/s, floor 0.807% and n=10.
Phase 1 lists the DS41/Q38FN floors by glob.

**No adapter.** This is the direct answer to Q3.

### 3.4 Other measured records for the Phase-1 targets (sub-report C)

- **27B KV-quant sweep v10**: `epyc-inference-research/data/gpu-mi210/kv-quant-27b-v10-sweep/run-20260922T135201Z/runs/<cell>/result.json`.
  - 5 `ok` cells (f16 d2k, q8_0 d2k/d32k, q4_0 d2k/d32k; f16 d32k missing). N=1.
  - Binary sha is in `identities.json`.
  - No `belief_measurements.jsonl`, so the existing adapter projects 0.
- **27B gate bundle**: `/mnt/raid0/llm/autokernel/surface/operator_gate_bundle.json`, sha-sealed. Champion `14ba0262` vs anchor: pp512 836.02/836.09, tg128 30.41/30.67.
- **27B DF25 concurrency grid**: `/mnt/raid0/llm/artifacts-df25/…/g2_rows.jsonl` (192+96 rows). **No model or build in the row**, so it stays unscoped.
- **AutoKernel served-shape calibrations** (`<store>/served_shape/*.json`, `epyc.autokernel.served_shape_calibration.v2`): per-shape correctness NMSE, e.g. `ds41_expert_down` IQ2_S. DS41-1017 has 2 files × 368 measurements. These are the only op/tensor-shape records, and they hold correctness, not timing. They are a **Phase-2** source for Q6, and the first DS41-1017 target-tier content that exists before its floor.
- **INF-61 np×depth grid**: `data/inf61-q38-np-depth-mtp8-20260916/` (36 ok cells), argv only. Phase 2.
- **DS41-1017 baseline**: `/mnt/raid0/llm/tmp/ds41-1017-baseline-20261021/`. The floor has not run (slot 2026-10-22T06:30Z). The smoke run is n=2 with the GPU not quiet, so do not project it. The floor result will be the first DS41-1017 target-tier belief; wire it through `ds41_1017_validation` (D6).
- **INF-70 roofline**: already in the ledger with numbers in the text. It is host-scoped (`device` only), and some runs carry `model_file: Qwen3.8-Flash-Next-IQ4_XS-uniform.gguf`, which is not the served UD quant.
- **Registry throughputs and recipe-module constants** (`model_registry.yaml`, `scripts/lib/*_recipe.py`): these are not records. They have no N and no locator per number. Do not ingest them.

### 3.5 AutoPilot (sub-report B)

| Source | Path | Content |
|---|---|---|
| Journal | `orchestration/autopilot_journal.jsonl` + `_1.jsonl` | 1,372 trials (0–1505). Fields: q/s/c/r, `config_diff`, `keep_revert_decision`, `failure_analysis`, `eval_details.seq_paired_baseline` in 225 of 362 eval rows. **No model, role or device.** |
| Planner archive | `logs/planner_archive.jsonl` | 4,595 rows. Stores prompt hash and a 500-char preview only. |
| StrategyStore | `strategies.db` | 1,428 rows, no scope. `strategy_conventions` is empty. |

The ledger has no AutoPilot source kind, and the `autopilot_journal` adapter has 0 post-hook rows.

AutoPilot plans over 4 merged targets derived from `stack_priors.yaml`
(`loop_beliefs_bridge.py:148-230`):

| Model | Quant | Backend |
|---|---|---|
| Qwen3.8-27B-Q8_0 | Q8_0 | gpu |
| Qwen3.6-35B-A3B-MTP-Q8_0 | Q8_0 | cpu |
| Q38FN | UD-IQ4_XS | cpu |
| Qwen3-VL-30B-A3B | Q4_K_M | cpu |

DS41 is not live there.

---

## 4. The record

### 4.1 Shape (one loop belief = one ClaimTuple, projected and graded as today)

```jsonc
{
  // identity (unchanged rule: claim_id = clm_<measurement_id>, derived once in to_frames)
  "measurement_id": "ak-exp:v1:<store-digest16>:<attempt_id>",
  "source_class": "measurement",            // "verifier" for gate refusals (4.4)
  "source_kind": "autokernel-experiment",
  "metric": "aggregate_tok_s", "metric_direction": "higher_better", "category": "CANDIDATE",
  "value": 22.31, "unit": "t/s", "reps": 5, "reps_basis": "scored:matched process pairs",
  "date": "2026-10-04T04:37:38Z", "protocol_id": "",          // absent -> Judged (an observation)
  "attestation_locator": "autokernel-experiments:<store>/experiments.db#attempt=<id>",
  "attestation_sha256": "<sha256 of the row's canonical bytes>", "attestation_present": true,
  "claim": "DS41-Q4 cpu [ds41-00d118d44-cpu-t48-dspark-b2]: akm-ds41-mmid-qact-block-partition on ggml_iqk_try_mul_mat_id: +2.05% vs anchor (floor 3.41%, 5 pairs) — producer verdict KEPT",

  // WHERE it holds (extends VB-APPLICABILITY; still inert to grading)
  "applicability": {
    "model_file": "/mnt/.../DeepSeek-V4.1-Flash-Q4.gguf",   // existing
    "model_sha256": "a5e2e2c3…",                             // NEW, only when recorded
    "quant": "Q8_0", "backend": "cpu", "device": "epyc-9655", // existing; quant AS RECORDED
    "kernel": {"build_path": "…", "execution_digest": "…"},   // existing
    "build_sha": "7ef803926107…",                             // NEW: spawn_parent / champion_head
    "epoch": "c42cd5615dfb…",                                 // NEW: anchor/recipe/host epoch
    "recipe": "ds41-00d118d44-cpu-t48-dspark-b2",             // NEW: launch recipe id
    "np": 1,                                                  // NEW
    "surface": "ggml/src/ggml-cpu/iqk/iqk_dispatch.cpp",      // NEW
    "symbol": "ggml_iqk_try_mul_mat_id",                      // NEW
    "op": "MUL_MAT_ID", "shape": "…",                         // NEW, only from gate/op records
    "scope_basis": "native"                                   // NEW: native | store_manifest
  },

  // WHAT was measured (NEW, inert to grading, emitted by to_frames only when present)
  "observation": {
    "anchor_value": 21.90, "effect_rel": 0.0205, "noise_floor_rel": 0.03412,
    "decisive": false, "n_pairs": 5,
    "outcome": "improved|null|regressed|refused_correctness|refused_scope|divergence|anchor|floor",
    "outcome_native": "kept",                                 // producer status, verbatim
    "outcome_reason": "<refusal_reason / failure text, ≤300 chars, verbatim>",
    "mechanism": {"id": "akm-…", "statement": "<≤240 chars>", "falsifier": "<≤240 chars>"},
    "retrofit": true                                          // projected from a pre-hook record
  }
}
```

### 4.2 How this fits ClaimTuple and the ladder

| Change | Where | Grading effect |
|---|---|---|
| `observation: dict` field, validated (allowed keys above, canonical JSON, numbers finite) | `claim_tuple.py` after `applicability` (`:180`); validation beside `:183-212` | **None.** `grade()` never reads it. A test asserts that for every tuple, grade(t) == grade(replace(t, observation={})). |
| New applicability keys `model_sha256, build_sha, epoch, recipe, np, surface, symbol, op, shape, scope_basis, role, stack_regime, config_key` | allowed set `claim_tuple.py:185-186` | None. The set is already declared inert. |
| `to_frames` emits `observation` (plus `metric`, `value`, `unit`) inside the **evidence** assertion, conditionally | `claim_tuple.py:711-715` | None. `fold` reads `claim_id`, `grade`, `evidence_id`, `source_id` from evidence frames and ignores other keys (`fold.py:560-586`). Conditional keys keep byte-identical frames, and so identical `frame_id`s, for every existing tuple. This is the SC57 precedent (`:681-692`). |
| Optional `stance: "supports"\|"opposes"` (default supports) emitting `evidence_opposes_claim` | `to_frames` | None on the ladder. **Phase 3 only** (DP-2). `research_intake` already emits opposes frames (`adapters/research_intake.py:348`). |

The value goes on the **evidence** frame because it is a property of the measurement. The claim
frame's `display_text` also states the number, so text-only readers see it.

### 4.3 Status (read side, from fold and gate only; no new rule)

| Status | Fold/gate condition | Planner meaning |
|---|---|---|
| verified | gate ALLOW at floor `Judged/Located`, verdict Supported | the observation stands (it may be a negative result) |
| refuted | verdict Opposed (`fold.Belief.verdict`, spec §7.1) | do not rely on it |
| contested | verdict Conflicted, unadjudicated correction, or dependency alert (`_bucket`, `loop_beliefs.py:437-449`) | contradiction; needs new evidence |
| withdrawn | retracted support and no live support (`:439-441`) | no longer stands |
| weak | below the floor | counted, not shown |

`_bucket` gains `refuted`, read from `belief.verdict(floor)`. Everything else exists today.

**Negative results are first-class.** A null, a regression or a correctness refusal is a
*verified* claim whose `observation.outcome` is negative. It is a dead end the planner can trust.
It is never encoded as a refuted claim; "refuted" is reserved for evidence that contradicts the
observation itself.

### 4.4 Refusals before timing (correctness/scope gates)

These are checks, not measurements, so they project as **verifier class**:

- `decided_proposition` = the gate's native output line, e.g. "MUL_MAT failed on ROCm0", or the
  failing `test-backend-ops` line from `gates[].detail`.
- `binding_kind` stays `""`.
- The SC56 cap therefore gives `Judged` (`claim_tuple.py:375-391`). That is honest, because the
  check decided the gate proposition and not the claim text.
- `metric` is the gate id (`correctness:MUL_MAT`), `value` is 0, `category` CANDIDATE,
  `metric_direction` higher_better.

There is no new class and no new ladder. Scope gates (`patch_rejected`, `refused_at_formation`)
are **not** projected. They describe the author's diff, not the target. Critic rejections and
authoring failures are not projected either. They are LLM judgments with no check behind them, and
the critic's "already measured" text points at a row that is projected anyway.

---

## 5. Write side

### 5.1 Projections (ROOT adapters; `claim_tuple.grade()` grades all of them)

| Adapter (new/changed) | Native input | Producer hook (prospective) | Projects |
|---|---|---|---|
| `autokernel_legacy_serving` **v2 projection** (`legacy-serving-v2:<capture>`) | `serving-beliefs/sources/<id>.json` (unchanged strict reader `_source`/`_rows`, `legacy_serving.py:34-208`) | none needed; existing `serving_beliefs` export | ONE claim per capture: value = candidate median, anchor, effect, floor, decisive, `mechanism_id`, recipe, np, epoch, `build_paths` |
| `autokernel_experiments` **new** | `<store>/experiments.db` rows (read-only SQLite, `mode=ro`) | research loop's experiment-row writer (the function that inserts into `experiments`; see §5.2). Add a self-hashed `belief_capture` to the payload so new rows are not retrofit. | kept/keep_candidate/measured_null/regression/measured_serving_gate (measurement); gate_refused/integrity_refused/measured_divergence (verifier); anchor_verified/runtime_observed (BASELINE). Rows that have a serving capture are de-duplicated against the v2 serving claim by `belief_receipt_id`/capture join, and the experiment claim keeps statement and falsifier. |
| `autokernel_serving_floor` **new** | `<store>/serving-floor.*.json` | the AutoKernel floor writer | BASELINE: median t/s, floor %, n, CI, residency proven/unproven |
| `kv_quant_27b_v10` **retrofit reader** | `run-*/runs/<cell>/result.json` + `identities.json` | already wired prospectively | per cell: decode/prompt t/s, KV type, depth, n=1. **Phase 2.** |
| `autopilot_journal` (existing SC6) **+ applicability** | journal rows with `infra_fingerprint`, `config_diff` | `autopilot.py:11390` `journal.record` (the post-trial block at `:11391-11408` is the hook) | scope `{stack_regime: infra_fingerprint digest, role→model_file, config_key}`. **Prospective only; Phase 2.** |

Adapter-table rows to add to `scripts/vidya/adapters/README.md` (in the same commits):

- `autokernel-experiment`: measurement + verifier; Live (retrofit + prospective).
- `autokernel-serving-floor`: measurement; Live.
- `autokernel-legacy-serving` v2: amend the existing row.
- Also amend the `kv-quant-27b`, `autopilot-journal` and `ds41-1017-validation` rows.

### 5.2 Hook points in the loops

- **AutoKernel.** Each producer and its hook:

  | Record | Producer | Phase-1 handling | Phase-2 change |
  |---|---|---|---|
  | Experiments row | `controller/experiments.py:438 ExperimentStore.record` (INSERT at `:470`), called from `L/archive.py:476 record` (call sites `L/run.py:4876, 4889, 5250, 5853, 5920, 5949, 7474`). Row body: `L/loop.py:617 Outcome.to_attempt`. Scope: `L/archive.py:634 original_research_scope`. | Ingested at planning time (see below) | Add a self-hashed `belief_capture` at `archive.record`, so new rows are prospective, not retrofit |
  | Serving A/B | `L/serving.py:1487 compare` → `serving_beliefs.prepare` (`:1588`) / `finish` (`:1720`); export `L/serving_beliefs.py:121`, called by `L/archive.py:507` | Unchanged. The v2 projection reads the same source bytes. | — |
  | Floor | `L/serving.py:2168 write_floor` (schema at `:1996`) | Ingested by glob | Write a sidecar digest |
  | `paired_loadgen` | `paired_loadgen.py:92` | — | No caller and 0 records. VB-AK-PAIRED-LOADGEN-WRITE stays as filed. |

  The ingest step is `scoped_ingest.ingest_scoped_store` (`scoped_ingest.py:240`). It already runs
  inside `prepare` for the loop's own `--source-root` (`loop_beliefs.py:178-210`, passed by
  `L/run.py:653-659`). Phase 1 extends it to:

  - read `experiments.db` incrementally: rows with `recorded_at` above the memo high-water mark,
    selecting `payload` only for those rows. **The DS41 `experiments.db` is 4.3 GB, with payloads up
    to about 6 MB each**, so a full scan is a backfill-only operation, never a planning-step one;
  - glob `serving-floor.*.json`.

  **Phase 1 needs no research change to the producers.** The one research change in Phase 1 is in
  the prompt contract (P1-G below).
- **AutoPilot.** Phase 1 writes nothing. AutoPilot benefits from AutoKernel and floor beliefs for
  its model targets (Q3, Q7). Its own trials become beliefs only once AP-55 `infra_fingerprint`
  rows exist (first post-restart trial).

### 5.3 Why AutoPilot trials are not backfilled

A journal row names no model. The lineup changed after August (worker swap, v10 freeze), and
attributing a trial to a model or a regime by date would invent a scope the run never captured.
AutoPilot already sees its own history through the journal, Pareto and AP-53 blocks. **Decided:
prospective only.**

---

## 6. Backfill (from existing campaign history)

| Store / source | Recoverable honestly | Must stay unscoped / not projected |
|---|---|---|
| 125 serving A/B sources | All admissible ones (115) → v2 claims with value, effect, floor, decisive, mechanism, recipe, np, epoch, build path, model path. `model_sha256` comes from the matching experiment row's `research_scope.model.sha256` when the capture joins, and is otherwise absent. | the 10 "unsupported authority" receipts stay refused (strict adapter unchanged) |
| experiments.db (DS41 ×3, Q38FN, 27B) | ≈ 394 substantive rows; after removing critic/authoring/scope-gate rows ≈ 230 claims. Measured rows use the native `research_scope`. Refusal rows use the store-manifest scope (`scope_basis: store_manifest`). | `planner_transient`/`abstained`/`lane_error` etc. (noise); critic and authoring rows |
| serving floors | every `serving-floor.*.json` | — |
| INF-70 | unchanged (already in the ledger, host tier) | model-file-tagged INF-70 runs on `IQ4_XS-uniform` stay matched to that file only, not to UD |
| kv-quant run-c (Phase 2) | 5 ok cells, N=1 | runs a/b (`status: error`) |
| DF25 rows, registry rates, recipe constants, AutoPilot trials | — | no native scope or no record (§3.4, §5.3) |

Every retrofit frame carries `provenance.retrofit: true` (the envelope already supports this; the
intake adapter sets it). It also carries `observation.retrofit: true`, so the render can label it.

`protocol_id` is never filled, so every retrofit claim grades `Judged/Located` by the existing
ladder. That is exactly what it is: an observation.

Backfill runs against a **copy** of the canonical ledger first (diff and fold counts reviewed),
then once against the canonical ledger under its flock, by the owning session.

---

## 7. Read side (`scripts/vidya/loop_beliefs.py`)

### 7.1 Matching — three tiers, never mixed

Matches go into three tiers, which are kept separate:

1. **target**: `model_file` basename (or `model_sha256`) **and** backend equal to the target's.
   The existing `applicability_matches` rule applies, with one change: it now **requires
   `model_file` or `model_sha256`**. A device-only scope no longer matches here.
2. **sibling**: same `MODEL_LINEAGE` family and same backend, different weights or recipe.
   - `MODEL_LINEAGE` is a declared table in the reader, like `SOURCE_SCOPES` (`:366-420`), and
     each row has a `basis` sentence.
   - Seed rows: DS41 = {`DeepSeek-V4.1-Flash-Q4.gguf`,
     `DeepSeek-V4.1-Flash-1017-MXFP4-experts-00001-of-00009.gguf`}; Q38FN = {UD-IQ4_XS, IQ4_XS-uniform}.
   - Rendered as "measured on <sibling file>, recipe <r>; transfer unproven".
   - Never counted as target evidence.
3. **host**: device/backend-only scopes (INF-70). Capped at 3 lines and labelled "host ceiling,
   not about this model".

### 7.2 Ranking inside the target tier

The tier is sorted in this order:

1. Flagged first: contested, withdrawn, refuted. This is the existing order, plus refuted.
2. Current-epoch decisive outcomes (improved, regressed), newest first.
3. Correctness refusals and divergences.
4. Nulls.
5. Anchor/floor records. The newest floor per recipe is always shown.
6. Older epochs, labelled: "stale epoch — the number is not comparable; the fact that the
   mechanism was tried still stands". This wording mirrors `experiments.md`.

Within each group: grade, then recency. At most one detailed line per (mechanism, recipe), with
"(+k earlier captures: …)".

### 7.3 Render (value-bearing)

One line per claim:

```
- clm_… [Judged/Located · verified · retrofit] DS41-Q4/cpu ds41-00d118d44-cpu-t48-dspark-b2 build 7ef80392 epoch c42cd561
  akm-ds41-q4q5-two-row-activation-reuse @ mul_mat_qX_K_q8_2_X4_T: REGRESSED −8.22% (floor 3.41%, 5 pairs; anchor 21.9 t/s)
```

After the detailed lines comes a compact **tried-mechanisms index** for the target and sibling
tiers, e.g.:

```
Tried on DS41-Q4: akm-…-prefetch null(−0.7%) · akm-…-unroll kept(+3.1%) · akm-…-streamk refused(MUL_MAT ROCm0) …
```

The index holds up to 80 ids in about 3 KB. It answers Q1 cheaply even when the detailed lines
are capped.

Caps:

| Part | Limit |
|---|---|
| target detailed | 16 |
| sibling detailed | 8 |
| host | 3 |
| index | 80 ids |
| section | 14 KB |

New defaults: `DEFAULT_MAX_CLAIMS` 12 → 27, `DEFAULT_MAX_BYTES` 10,000 → 14,000 (`:89-90`).

When the target tier is empty, the section says so first: "No beliefs are scoped to <target>. The
lines below are sibling/host context only." This also fixes the "same 12 claims" illusion.

### 7.4 Answer JSON additions

| Key | Content |
|---|---|
| `evidence.tiers` | `{target: n, sibling: n, host: n}` |
| `evidence.claims[]` | gains `tier`, `status`, `outcome`, `mechanism_id`, `value`, `unit`, `effect_rel` |
| `evidence.tried_index` | the tried-mechanisms index |
| `evidence.nonempty_target` | bool; feeds VB-REFOCUS-READ-COUNTER |

Reliance (`relies_on_claims` / `vidya_claim_ids`) accepts target- and sibling-tier ids. Host-tier
ids are refused as reliance by the consumer's existing premise check: a "not evidence" flag in the
answer, which the AutoPilot `_vidya_premise_skip` path and the AutoKernel seed check already honour
for contested and withdrawn.

v1/v2 deduplication: when a v1 arm claim and a v2 capture claim share a receipt locator, only v2 is
shown. The ledger keeps both (§8).

### 7.5 Target additions (both consumers)

`Target` gains optional `model_sha256` and `focus_symbols` (a ranking boost only, never a filter).
`from_mapping` accepts them. Consumers that do not pass them behave as today.

**AutoKernel.** What `belief_context` sends today:

- the campaign target `{model_path, quant (census dominant quant, e.g. "Q8_0" for
  DS41-Q4), backend, device, surface}` (`L/belief_context.py:146-156`, from `L/run.py:3591-3595`);
- `surface` = `serving:<recipe>`, which the ROOT `Target.from_mapping` drops today.

Phase 1 keeps `surface` as `recipe` (strip the `serving:` prefix) and uses it to rank
same-recipe claims first. In Phase 2 it also passes the target surfaces from `owned-targets.json` as
`focus_symbols`.

Phase 1 also needs one research prompt change (P1-G):

1. Add `relies_on_claims` to the `_HYPOTHESIS_TASK` JSON template (`L/actors.py:3130-3153`), with
   one line saying "list the belief-section claim ids your mechanism depends on; [] if none". Without
   it, criterion (b) of the test is unlikely to fire (D8).
2. Move the belief section from the prompt tail (`:3679`) to right after `## Already tried`
   (`:2854`), so it sits next to the in-store memory it extends.

**AutoPilot.** No change in Phase 1.

### 7.6 Cost

`prepare` already folds the whole ledger (cold 20–25 s, warm about 1.6 s, sub-report B). The new
tiers and ranking are linear in matched claims, which is fewer than 1,000. The incremental
experiments read is bounded: one SQLite query per store with a high-water mark.

---

## 8. Migration of today's claims

| Claims | Action |
|---|---|
| 329 INF-70 (device-only or IQ4_XS-uniform) | **Keep, re-tier.** Device-only claims become host tier (≤3 lines, never target evidence). File-tagged claims match their own file only. No ledger write. |
| 230 legacy-serving v1 arm claims | **Keep, hide behind v2.** No retraction: a retraction would render them as "withdrawn, result no longer stands", which is false. The reader dedupes by receipt locator. |
| Intake (89%) and other unscoped measurement frames | Untouched, and never matched to loop targets (no applicability). |

---

## 9. Phasing and estimate

Deadlines (updated 2026-10-21):

- Evaluation **2026-11-30**.
- Both loops live by **~2026-11-23**. The 7-day minimum window counts from the first live receipt.
- Phase 1 is still targeted at **build 10-28, verified 10-30**, so loops can start in early November
  with roughly 4 weeks of window instead of 1.

Effort assumes agent-days with file-scoped tests. All CPU work runs under `region-lock run
--cpu-list 0-95`.

### Phase 1 — value-bearing, target-specific beliefs for DS41, Q38FN and 27B. Build by 10-27, verify by 10-28.

| Step | Files | Tests | Est. |
|---|---|---|---|
| P1-A carrier | ROOT `scripts/vidya/claim_tuple.py` (observation field, applicability keys, conditional emission in `to_frames`) | `tests/vidya/test_claim_tuple.py`: (a) every registered projection's fixture frames are byte-identical before and after; (b) grade invariance under observation; (c) observation validation refusals | 0.5 d |
| P1-B serving v2 | ROOT `adapters/autokernel_legacy_serving.py` (`project_v2`, `native_rows_v2`); `scoped_ingest.py` emits v2 beside v1 | `tests/vidya/test_autokernel_legacy_serving.py` + v2 fixtures; replay of 3 real sources (DS41, Q38FN, runtime_ab) | 0.5 d |
| P1-C experiments adapter | ROOT `adapters/autokernel_experiments.py` (new; status→outcome table, verifier projection for gates, store-manifest scope, dedup join); `scoped_ingest.py` incremental SQLite read; `cli.py ingest autokernel-experiments` | new `tests/vidya/test_autokernel_experiments.py`: fixture DB with one row per status; scope_basis; no row without `attempt_id`; refusal → Judged verifier; byte-stable ids | 1.0 d |
| P1-D floor adapter | ROOT `adapters/autokernel_serving_floor.py`; scoped_ingest glob | fixture from the 27B floor file | 0.25 d |
| P1-E reader | ROOT `scripts/vidya/loop_beliefs.py` (tiers, `MODEL_LINEAGE`, ranking, value render, tried index, refuted bucket, v1/v2 dedup, Target extras, answer keys) | `tests/vidya/test_loop_beliefs.py`: device-only claims never reach the target tier; sibling labelling; caps; empty-target banner; refuted bucket; determinism (same ledger → same section bytes) | 1.0 d |
| P1-F backfill | run on a ledger copy in `/mnt/raid0/llm/tmp/…`, review, then canonical (owning session) | fold totals unchanged for pre-existing claims; chain verifies | 0.25 d |
| P1-G consumers | **research** `L/actors.py`: `relies_on_claims` in the `_HYPOTHESIS_TASK` template, and the belief section placed after `## Already tried`. **orchestrator** `loop_beliefs_bridge.py`: confirm the new answer keys pass `_check_answer` (`:266-281`) and that host-tier ids are refused as premises. Update fixtures. Merge the research change only between campaign runs. | `test_belief_context.py`, `test_actors.py`, `test_autopilot_loop_beliefs.py` | 0.75 d |
| P1-H README rows, progress, handoff text | ROOT README source table; program handoff (main applies) | `index_state.py --check` | 0.25 d |

Total: about **4.5 agent-days**. It splits into three parallel lanes:

- A + B + D: carrier and small adapters.
- C: experiments.
- E: reader, against fixture frames, until A lands.

That gives about 2 calendar days.

**Phase-1 acceptance checks.** Run them on a canonical-ledger copy plus a dry-run planner prompt.

| # | Check |
|---|---|
| AC1 | `prepare` DS41-Q4 cpu: ≥20 target-tier claims with value+unit+n; ≥5 negative outcomes (regressed/null/refused) with mechanism ids; tried index ≥60 mechanisms. |
| AC2 | `prepare` DS41-1017 cpu: target tier 0 with the empty-target banner; ≥8 sibling-tier DS41-Q4 lines labelled "transfer unproven"; ≤3 host lines. |
| AC3 | `prepare` Q38FN UD-IQ4_XS cpu: ≥15 target-tier value-bearing claims; tried index ≥35 mechanisms. |
| AC4 | `prepare` Qwen3.8-27B-Q8_0 gpu: ≥3 target-tier claims: the serving floor (81.1 t/s, floor 0.81%, n=10) and 2 mechanisms refused by the correctness gate ("MUL_MAT failed on ROCm0"). |
| AC5 | `prepare` Qwen3.6-35B-A3B and Qwen3-VL-30B: target tier 0 with the banner, so the five CPU models no longer get identical usable sets. |
| AC6 | An AutoKernel planner prompt built through `belief_context` and an AutoPilot `CONTROLLER_PROMPT_TEMPLATE` render (fixture turn) both contain the AC1/AC4 lines. Section ≤14 KB. Warm `prepare` p95 ≤10 s. |
| AC7 | Every pre-existing claim's grade, verdict and gate outcome is identical before and after the backfill (fold diff on the copy). Every existing adapter fixture's frame ids are unchanged. |
| AC8 | "Was it tried" probe: 10 random `mechanism_id`s from the DS41 and Q38FN stores each appear in the answer (detailed line or index) with their outcome. |

### Phase 2 — by 2026-11-13, leaving 10 days of buffer before 11-23 (rest of the live targets, prospective writers)

| Item | Owner | Est. |
|---|---|---|
| research experiment-row writer emits `belief_capture` (new rows not retrofit) | AutoKernel owner | 0.5 d |
| VB-AK-PAIRED-LOADGEN-WRITE | AutoKernel owner | 0.5 d |
| `kv_quant_27b_v10` retrofit reader for run-c | — | 0.5 d |
| DS41-1017 floor through `ds41_1017_validation` once the 10-22 floor exists | — | 0.25 d |
| `autopilot_journal` applicability (`stack_regime`, `config_key`) from AP-55 `infra_fingerprint` | — | 0.75 d |
| AutoKernel passes `focus_symbols` | — | 0.25 d |
| VB-REFOCUS-READ-COUNTER from `evidence.nonempty_target` | — | 0.25 d |
| `autokernel_served_shape` adapter (verifier/measurement NMSE per shape; gives DS41-1017 op-level target-tier content before its floor) | — | 0.5 d |

Total about 3.5 days.

### Phase 3 — after the 11-30 evaluation, only if PASS

- Finding-level claims (DP-2), INF-61 grid, gate bundle, gfx90a op-level records.
- A protocol annex for matched-process serving A/B (DP-3).

---

## 10. Decision points (operator)

**DP-1 — Retrofit historical loop records as observations.** This bends the program's stance,
not the ladder. §4.7 says "a row that predates a producer's provenance hook is skipped rather than
back-filled", and the AutoKernel adapters apply this as "zero tuples without a producer capture"
(`autokernel_evaluation_event.py:6-9`, `ak_history.py:12-13`). Phase 1 depends on reading
`experiments.db` rows and serving floors that have no `belief_capture`.

| Option | What it means | Tradeoff |
|---|---|---|
| (a) **Allow retrofit projections** | Fields present in the record only; `protocol_id` never filled, so the ladder caps them at Judged; `provenance.retrofit=true`; rendered as "retrofit". | Every DS41/Q38FN dead end and the whole 27B content exist **before** the trial. Risk: a planner over-weights a pre-hook number. Mitigated by the Judged grade and the label. |
| (b) Prospective only | — | 27B GPU and DS41-1017 have ~0 target beliefs until new runs. Q1/Q2 answers wait weeks. Every cross-store memory the turns in §2 lacked stays absent. Criterion (b) can only fire on results produced inside the trial window itself. |
| (c) Hash-attested native artifacts only | Serving sources and floors; not `experiments.db` | Keeps strictness. Loses every refusal/null/regression row, including all of 27B's AutoKernel content. |

**Recommendation: (a).** The rule's purpose is "a tuple invented on read claims warrant the
original run never captured". Option (a) invents nothing and claims no warrant (Judged is the
"observation" rung). Phase 1 as planned assumes (a). Under (c), drop P1-C's refusal statuses and
AC4's refusal lines.

**DP-2 — Claim identity at finding level (Phase 3, not blocking).** Today identity is derived once
from `measurement_id` (§4.7), so each capture is its own claim. Replications of the same mechanism
on the same target are grouped only for display, and fold-computed "contested/refuted across
replications" does not exist.

| Option | What it means | Tradeoff |
|---|---|---|
| (a) Keep per-observation claims | Reader groups by (target, recipe, mechanism) | No doctrine change. |
| (b) Finding claims | `claim_id` derived centrally in `claim_tuple` from (scope core, mechanism, metric). Each capture is evidence. Stance comes from the native decisive verdict (supports/opposes). The fold yields Conflicted when replications disagree. | Bends §4.7 "identity derived once from measurement_id". That is the rule that stopped three A/B arms from merging into one belief. |

**Recommendation: (a) through 11-30; revisit with the trial data.**

**DP-3 — Protocol annex for AutoKernel matched-process serving A/B (human-only trust boundary).**
Without one, every loop belief stays `Judged` (an observation). The strict adapter refuses receipts
that cite a protocol (`legacy_serving.py:93-96`).

| Option | Tradeoff |
|---|---|
| (a) Ratify `measurement/protocols/` annex for `matched_process_v2` | Lets new captures reach Verified/Witnessed. |
| (b) Not now | — |

**Recommendation: (b).** The trial tests whether beliefs change decisions, and observations
suffice for that.

**DP-4 — AutoPilot PASS rule and the AP3 role-restart gate during the trial.** See §12.6. The
options are (A) counterfactual-confirmed reliance, (B) declared reliance plus a reviewer, and (C)
AutoKernel carries the trial while AutoPilot is held to no-harm only. **Recommendation:** (A) with
the gate on for `spec_draft`/`kv_profile`; otherwise (C).

Everything else in this plan is decided here: tiers, sibling table, value-on-evidence-frame,
verifier projection of gate refusals, no AutoPilot backfill, and no v1 retraction.

---

## 11. Risks

1. **Biggest: AutoPilot may not be able to pass the 11-11 test whatever the store holds.** Its
   actions are orchestrator knobs (`memrl_retrieval.semantic_k`, chat thresholds) evaluated over
   the whole mixed lineup. Its targets are model files whose beliefs are AutoKernel kernel
   results and serving floors.
   - The only Phase-1 belief that bears on a typical AutoPilot decision is the per-model serving
     rate and floor (Q3, the 08-09 throughput-floor collapse).
   - AutoPilot's own trial beliefs need AP-55 regime scope, which exists only after the restart.
   - Expect AutoKernel to carry the PASS. Say so before the 11-23 start, not after.
2. **AutoKernel already has strong in-store memory** (§2), and the "instrument nothing new"
   reviewer check discounts any decision the store alone would have produced. The countable wins
   are therefore narrow:
   - cross-store transfer to DS41-1017;
   - aged-out nulls (Turn B);
   - measured floors (Turn C);
   - cross-lane duplicates.

   Without the P1-G prompt changes, the planner will rarely declare reliance even on those.
3. **Retrofit over-trust.** Old-epoch numbers shown next to current ones. Mitigation: epoch and
   build on every line, the stale-epoch label, and Judged grade printed.
4. **Sibling transfer misread.** The DS41-Q4 dspark-b2 recipe has a drafter, and DS41-1017 is
   nospec with MXFP4 experts. Mitigation: recipe on every line, "transfer unproven", and sibling
   ids never counted as target evidence in the receipt.
5. **Ledger write contention and store size.** The backfill (~350 claims ≈ 1,050 frames, plus v2 115 × 3) runs
   under the ledger flock while both loops call `prepare`. Run it in one owner session between
   loop runs, and on a copy first. The backfill reads the 4.3 GB DS41 `experiments.db` and the
   44–47 MB serving sources. Schedule it outside timing windows, under the build-role region lock.
6. **Prompt budget.** 14 KB is about 3.5k tokens. AutoPilot prompts are already 66–91k chars.
   Keep the caps, and measure planner-call wall time for the no-harm criterion 2.

---

## 12. AutoPilot belief grain (addendum, 2026-10-21 ~18:00Z)

This addendum was written at the operator's request to refine the AutoPilot integration (risk 1).
Orchestrator citations are `/mnt/raid0/llm/epyc-orchestrator` @ `9aa15a65`. Measurements came
from a short pinned script, with no ledger writes.

### 12.1 What AutoPilot actually decides

AutoPilot's action space has three parts:

- **NumericSwarm surfaces**: `scripts/autopilot/species/numeric_swarm.py:32-143` (`SURFACES`).
- **StructuralLab flag flips**: `config_applicator.py:52-65`, `HOT_SWAP_FEATURES`.
- **Env/role-restart params**, classified by `classify_params` (`config_applicator.py:1376-1409`).
  The role-restart groups are `ENV_PARAMS` (`:68-141`) and the AP3 role-restart specs
  (`:419-657`). Each AP3 spec carries `role=` and `registry_path=`.

| Knob family | Keys (examples) | Grain | Per-model beliefs bear? |
|---|---|---|---|
| `spec_draft` | `role_restart.{frontdoor,worker,architect}_{spec_type,draft_max,draft_min,draft_p_min,draft_p_split,ngram_mod_n_*}`, `worker_threads_draft` | **role → one model.** frontdoor and worker_general → Qwen3.6-35B-A3B-MTP-Q8_0 (cpu); architect_critic → Qwen3.8-27B-Q8_0 (gpu, shares its server with coder_escalation and ingest_long_context) | **YES** |
| `kv_profile` | `role_restart.*_kv_profile` (registry `server_mode.<role>.kv_quant`) | role → model | **YES** (KV-quant sweep, KVU-12) |
| `kv_compaction` | `kv.keep_ratio`, `kv.keep_first`, `kv.n_future` (applied per slot through `compress_slot`) | lineup-wide setting, model-sensitive effect | partly |
| `placement` | `placement_policy.*` (AXA-3 GPU teleport) | cpu-role ↔ 27B-gpu pair | partly (serving floors, teleport break-even) |
| `routing` | `chat.long_context_threshold_chars` (routes requests to ingest_long_context, i.e. the 27B GPU server) | lineup knob that **loads one model** | **YES, indirectly**: PB-HOL-1 head-of-line on that server |
| `orchestrator` | `memrl_retrieval.*`, `chat.*` thresholds, `think_harder.*`, `monitor.*`, `escalation.*`, `repl.*`, `delegation.*`, hot-swap flags | **lineup-wide** | no; only AutoPilot's own trials (prospective, `stack_regime`) |
| `slot_serving` | `np`, `-b/-ub`, prefill budget, prefix fork, `--kv-unified`, `--cache-ram` | **not in the action space.** These are stack topology, owned by `stack-change`. | context only (explains q/s outcomes; feeds operator hypotheses) |

Two facts limit what any belief can change during the trial.

- **No historical trial touched a role-scoped knob.** The 1,372 historical trials touched
  `memrl_retrieval` 293×, flags 168×, `repl` 42×, `chat` 31×, `think_harder` 24×,
  `placement_policy` 21×, `monitor` 20×, `escalation` 15×, `kv` 4×, and **`role_restart` 0×**.
- **The role-scoped knobs are off by default.** They apply only when
  `AUTOPILOT_AP3_ROLE_RESTART_ENABLE` is set (`config_applicator.py:1433-1440`).

Unless the operator enables that gate for the trial, the knobs that per-model beliefs bear on are
unreachable. See DP-4.

### 12.2 Cross-loop beliefs at knob grain: adapters

All of these use one ladder (`claim_tuple.grade()`) and project only. Scope comes from each
record's own argv: `model_file` from `-m`; device from `--device none`/`ROCm0`. The scope also
holds `knobs`, the flag set held fixed, and `varied`, the knob the record's arms change.

| Source | Native record (paths) | Adapter | Scope → grain | Phase |
|---|---|---|---|---|
| KPF-18 prefix fork | `epyc.kpf.run.v1`, each with a runner-authored `belief_measurements.jsonl`. **27B GPU item 7:** `/mnt/raid0/llm/tmp/overnight-20261020/kpf18-run-c/records/kpf18-20261021T14*.json` (A1/A2 fork_off, B1/B2 fork_on; 4 sidecar lines), summary `kpf18-run-c/item7_summary.json`. **35B CPU:** `/mnt/raid0/llm/tmp/kv-prefix-fork/p1r-20261020/kpf18cpu/{run-20261020T163128Z, rerun-20261021/item{1,2,5,7}}` (24 lines) | **existing** `adapters/kv_prefix_fork.py`. It is strict and prospective but sets no `applicability` and has 0 ledger frames. Add `_applicability(argv)` and an ingest name. | **27B item 7:** Qwen3.8-27B-Q8_0, gpu, fork build `gpu-20261020-a1f0c8cf9`, argv `argv.8083-gate.txt`, launch prefix `taskset -c 184-191`, np 4, `varied=[slot_fork]`. Prefill tokens 254,512 → 74,512 (`prompt_tokens_processed`; fan-out 194,512 → 14,512). Child TTFT about 144–460 s → 25–50 s, roughly 8.5×. This bears on `routing` and `slot_serving` for architect_critic. **35B item 7:** Qwen3.6-35B-A3B-MTP-Q8_0, cpu, np 4. Fan-out 51,712 → 2,560; TTFT about 360–510 s → 38–47 s. Context for frontdoor/worker. | **1** |
| PB-HOL-1 | `epyc.pbhol1.run.v1` `summary.json` + `pb_hol_1.jsonl` + `run_meta.json` (`/mnt/raid0/llm/tmp/pb-hol-1/runs/20261021T160010Z/`) | **new** `adapters/pb_hol.py`. Retrofit under DP-1. Add a prospective `belief_measurements.jsonl` emitted by `pb_hol_1.py` (the producer lives in `/mnt/raid0/llm/tmp`; move it into research or root before wiring). | **Qwen3.8-27B-Q8_0, gpu** (champion `dd3d9721c`), np 3, `-b/-ub 512`, `--kv-unified`, DFlash2 n-max 7, `varied=[short_slot_index_order]`. Short TTFT B/A = **22.05×** (70.9 s vs 3.2 s, solo 0.28 s, 3 reps). The budget-on arms are empty because of a since-fixed harness bug. They re-run 2026-10-22 ~05:50Z into `runs/on-20261022/`. Project the off arms now and the on arms when they land; each run is its own claim set. Bears on `routing` (long-context threshold onto the architect server) and `slot_serving`. | **1** |
| PB-QCOST-1 | `/mnt/raid0/llm/tmp/analytics-20261020/PB-QCOST-1/results.json` (fit t = 324 + 0.987q + 2.41e-5·q·c ms, held-out MAPE 4.0–7.8%) | **new** `adapters/prefill_cost_fit.py` | `results.json` names **no model, binary or device**. It is an offline fit of samples whose scope must come from the input samples, and the record does not hold that. Unscoped until the fit run writes its sample manifest (GGUF sha, argv). | 2 |
| KVU-12 np×ctx×KV | research `artifacts/np_context_kvu_cpu_study_20261020/` per-cell `summary.jsonl` (README row 268); the redo `/mnt/raid0/llm/tmp/kvu12-redo-20261021/out/` is empty | `np_ctx_kvu` (README-prospective) | model and KV mode from each cell's argv → `kv_profile` for cpu roles | 2 (after the redo lands) |
| Serving floors | §3.3 | `autokernel_serving_floor` (P1-D) | model + recipe (+ knobs from `recipe_describe`) | 1 (already) |

### 12.3 Target derivation and matching

**`Target` (ROOT, `loop_beliefs.py:301-340`)** gains three optional fields:

- `role`;
- `knob_families` (list from the family table in 12.1);
- `stack_regime` (AP-55 `infra_fingerprint` digest).

**`derive_targets`** (`loop_beliefs_bridge.py:201-230`) stops merging roles into one target. It
emits:

- for each live role and model in `stack_targets` (`:148-175`), one target `{model_path, quant,
  backend, role, knob_families}`. The families are derived **from the action space**: an AP3 spec
  whose `role` equals the role gives `spec_draft` and `kv_profile`; `routing` is added for the role
  that `chat.long_context_threshold_chars` routes to (`ingest_long_context`); `placement` is added
  for gpu roles;
- one lineup target `{scope: "lineup", stack_regime, knob_families: [orchestrator, kv_compaction]}`.

Same-model roles still share one `prepare` call; it carries several targets.

**Applicability** gains `role`, `knob_family`, `knobs` (dict) and `varied` (list). These are
inert, like the rest.

**Matching** extends 7.1:

| Tier | Rule |
|---|---|
| **knob** (new, ranked above plain target) | model matches **and** the claim's `knob_family` ∈ target's `knob_families` |
| plain target | model match, no family overlap |
| lineup | `stack_regime` equal |

Unknown families never match a family-scoped target. The render prints `varied` and the fixed
`knobs`, so the planner sees which flag set held the number.

### 12.4 The AutoPilot journal: decided, prospective only

Historical rows **are not projected.** There are three reasons:

1. **The grain is wrong.** All 1,372 rows vary lineup-wide orchestrator knobs (12.1). None is
   role-scoped, so none can reach a model target.
2. **"Regime unrecorded" is not a scope.** Their outcomes are dominated by regime faults: 24
   consecutive trials (#1480–1503) failed on a throughput floor invariant to the knob, and 66 rows
   are `bug_corrupted_by: killed`. Projecting `config_key + outcome` with no regime would present
   infrastructure failures as knob findings.
3. **It would add nothing.** AutoPilot already reads these rows through the journal summary,
   Pareto, AP-53 rejected-config fold and blacklist. The trial's "instrument nothing new" check
   would discount any decision they drove.

**Going forward:** the existing `autopilot_journal` adapter (SC6) gains applicability
`{stack_regime: infra_fingerprint digest, role→model_file map, config_key, knob_family}`. The
hook is `journal.record` (`autopilot.py:11390`). The `infra_fingerprint` is already passed at
`:11375`. Moved to Phase 1.

### 12.5 Planner reply

AutoPilot already has a reply field equivalent to `relies_on_claims`:

| Piece | Location |
|---|---|
| Reply field | `vidya_claim_ids` in `autopilot_rationale_schema` (`controller_io.py:1032-1045`) |
| Extraction | `controller_io.py:1170-1172` |
| Prompt instruction | `autopilot.py:6084-6087` |
| Premise skip | `_vidya_premise_skip` (`autopilot.py:8300-8318`) |
| Receipt | `build_planner_receipt` (`loop_beliefs_bridge.py:597-630`) |

One change is needed. The receipt row (`planner_coordinator.py:1829-1880`) must record, per
declared id, the claim's `tier`/`knob_family`, plus the action's knob family from
`classify_params`, so that 12.6 can be checked from receipts alone.

The AutoKernel change P1-G (adding the field to its JSON template) is separate and still needed.

### 12.6 Proposed AutoPilot PASS rule (operator decides: **DP-4**)

Each option below must be checkable from planner-archive receipts and the journal.

| Option | Rule | Tradeoff |
|---|---|---|
| **(A) counterfactual-confirmed reliance** | PASS if **≥3 planner turns** where (i) the accepted `vidya_claim_ids` include a knob- or target-tier claim whose `knob_family` equals the chosen action's family, **and** (ii) a **shadow draft** of the same turn with the belief section replaced by the empty banner proposes a different action, or the same action with a different value on that knob. Any premise skip (`SkipOutcome` "vidya premise …") that blocked a dispatch also counts as 1. The shadow draft is never dispatched and is recorded as `counterfactual_action` in the receipt. | Causal and receipt-checkable. Costs one extra draft call per qualifying turn, about 1 d to build. Needs the AP3 role-restart gate ON, or the only qualifying families are `routing` and `placement`. |
| (B) declared reliance + reviewer | ≥3 turns with accepted cross-loop reliance, each confirmed in writing by a reviewer (the current VB-LOOP-TEST style) | Cheap. Judgment-based. Weak against "the journal would have done it anyway". |
| (C) AutoPilot on no-harm only | AutoKernel alone carries the substrate PASS. AutoPilot stays wired if no-harm holds. | Honest about 12.1. Means the substrate is never tested on a lineup-wide planner. |

**Recommendation:**

- (A) for AutoPilot, with the AP3 role-restart gate enabled for the trial window, limited to
  `spec_draft`/`kv_profile` on the 27B and Qwen3.6-35B roles under the existing critic and quality
  gates.
- AutoKernel alone **may** carry the substrate's PASS. This is the existing "Partial" branch, made
  explicit.
- If the operator keeps the AP3 gate off, use (C). AutoPilot then has almost nothing a model-scoped
  belief can change, and holding it to a success bar would test the action space, not the substrate.

### 12.7 Phase placement

Must land and be verified before about **2026-11-16**. These steps add to P1-A..H.

| Step | Files | Est. |
|---|---|---|
| P1-I applicability keys `role`, `knob_family`, `knobs`, `varied`, `stack_regime` (part of P1-A) + knob tier, ranking and render (part of P1-E) | ROOT `claim_tuple.py`, `loop_beliefs.py` | 0.5 d |
| P1-J per-role, per-family targets + lineup target | orchestrator `loop_beliefs_bridge.py:148-230`; tests in `test_autopilot_loop_beliefs.py` | 0.5 d |
| P1-K `kv_prefix_fork` applicability + ingest of the 24 existing sidecars | ROOT `adapters/kv_prefix_fork.py`, `cli.py`, scoped/sync ingest | 0.5 d |
| P1-L `pb_hol` adapter (retrofit, off arms) + producer sidecar | ROOT `adapters/pb_hol.py`; move `pb_hol_1.py` into a repo | 0.5 d |
| P1-M `autopilot_journal` prospective applicability (from Phase 2) | ROOT adapter + orchestrator hook check at `autopilot.py:11390` | 0.5 d |
| P1-N receipt fields + shadow-draft counterfactual (**only if DP-4 = A**) | orchestrator `planner_coordinator.py:314-336, 1829-1880` | 1.0 d |

Total: **2.5 d**, plus 1.0 d if DP-4 = A. KVU-12 and PB-QCOST-1 stay in Phase 2.

**Acceptance AC9:**

- `prepare` for role `architect_critic` (27B gpu, families `spec_draft`, `kv_profile`, `routing`)
  returns PB-HOL-1 (22.05×, off arms) and KPF-18 item 7 (27B fork on/off) in the knob tier.
- `prepare` for role `frontdoor` (Qwen3.6-35B cpu) returns the KPF-18 item 7 arms as context.
- The lineup target returns "no beliefs at this regime" until the first post-restart trial.
