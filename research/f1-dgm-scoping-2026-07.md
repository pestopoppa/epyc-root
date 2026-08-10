# F1-DGM Scoping — DGM Synthetic Task-Generation for W4+ Corpus Expansion

**Type**: Design / scoping document (zero-cost design input — NO inference, NO code, NO commits in this pass)
**Owner handoff**: [`handoffs/active/frontier-f1-real-task-corpus.md`](../handoffs/active/frontier-f1-real-task-corpus.md) (F1-DGM-1/2/3)
**Plan**: Wave-2 B5 (`mnt-raid0-llm-epyc-root-tmp-deep-resear-cuddly-leaf.md`)
**Sources read**: DGM/Hyperagents/ADAS intake (rec-002, intake-786/787/791), SkillsBench v3 (intake-096), Simula deep-dive (`research/deep-dives/simula-synthetic-data-generation.md`, esp. §2, §3, §8.1–8.5, L340–416), both `debug_scorer.py` copies (orchestrator + research), `scripts/autopilot/eval_tower.py`, `scripts/benchmark/seeding_scoring.py`, `scripts/autopilot/rubric_scoring.py`, the curated W3 ledger `benchmarks/prompts/debug/real_suite_v1.yaml`, `dataset_adapter_modules/registry.py`.
**Date**: 2026-07-17

---

## 0. THE MANDATORY GUARD (read first)

> **Self-generated tasks MUST NOT enter the autopilot gate without human-curate confirmation.**
>
> DGM-generated tasks are, until a human curates them, **audit/promotion material only** — exactly the same power-discipline posture the F1 handoff already imposes on `llm_judge`/rubric items and on the real suite before *n* is large enough. This is not advisory: SkillsBench v3 (intake-096) is a direct empirical warning that self-generated content is **net-negative (−1.3pp avg) without validation gates against a curated baseline**. The curated W3 ledger (`real_suite_v1`, 50 rows, all deterministically scoreable) is that baseline.

The gate boundary in one line:

```
DGM generate → schema/scoreability/parity gates → double-critic QC → HUMAN CURATE (hard gate)
    → audit/promotion slice → [only after curation + n-discipline] → autopilot eval-tower gate
```

No automated path skips the human-curate node. The eval-tower `SafetyGate` remains the autopilot-admission authority; DGM output reaches it only as already-curated suite rows.

---

## 1. F1-DGM-1 — DGM task-generation methodology for W4+ corpus expansion

### 1.1 What DGM contributes, and what we deliberately drop

> **⚠ PREMISE CORRECTION 2026-08-10 — read before using this section.** The sentence below says
> DGM is a loop in which "an agent generates tasks", and section 1.1 then takes "only the
> task-generation half". **DGM has no task-generation half.** It self-modifies its own code and is
> evaluated on given coding benchmarks; the same holds for ADAS (intake-1068) and Hyperagents
> (intake-1069), which lists "a fixed task and evaluation distribution" among its own limitations.
> Verified against primary source when those two papers were finally ingested (they had been cited
> here with other entries' ids attached). What the lineage actually contributes is metacognitive
> self-modification. Any F1 scoping that inherits task generation from DGM rests on a capability
> that is not in the paper.


DGM (Darwin-Gödel-Machine; Hu/Lu/Clune/Zhang lineage, ADAS → DGM → Hyperagents; handoff cites arxiv 2505.22954) is a **self-code-modification + empirical-validation loop**: an agent generates tasks, executes them, validates results, and iteratively improves both tasks and its own capability, using **archive-based evolution over a parallel exploration tree**.

For F1 we take **only the task-generation half** and drop self-modification:

| DGM element | F1 adoption |
|---|---|
| Archive-based evolution (keep a growing pool of validated tasks) | **Adopt** — the archive is the growing curated corpus; W3 `real_suite_v1` seeds it |
| Parallel exploration tree (branch task variants) | **Adopt (as generation strategy)** — branch candidate variants per workload class |
| Empirical validation loop (execute → validate → keep/reject) | **Adopt, but gated** — validation = deterministic verifier + Simula double-critic + **human curate**, never self-admit |
| Self-code-modification of the generating agent | **DROP** — EPYC does not self-modify production agents; production kernels/stack are frozen. Out of scope. |
| On-the-fly generation *during* the autopilot loop | **DROP for the gate path** — generation is offline/batch, curated before it can gate anything |

### 1.2 Generation pipeline (proposed, design-only)

Seed from what F1 already measured, not from public benchmarks:

1. **Seed set** = the curated W3 ledger (`real_suite_v1`, 50 rows) + the measured workload taxonomy (`orchestration/workload_model.yaml`, 7 task classes with 30-day volume shares).
2. **Per-class branching**: for each of the 7 observed classes — `benchmark_eval_measurement`, `code_implementation`, `debug_root_cause`, `governance_docs_handoff`, `ops_deploy_process`, `planning_architecture_review`, `research_intake_deep_dive` — branch candidate tasks that (a) match the class's observed prompt shape and (b) carry a **complete, W3-schema-identical row**.
3. **Row schema (must match `real_suite_v1` exactly)**: `{id, tier, prompt, expected, scoring_method, scoring_config, source_suite, source_question_id, real_task_class, real_task_outcome}` plus a new provenance stamp `dgm_provenance: {generator, seed_node, critic_verdict, elo_complexity, curated_by, curated_at}`. A DGM row without a determinate `(expected, scoring_method, scoring_config)` triple is **not a candidate** — it is a rubric/judge item and diverts to the audit-only lane.
4. **Coverage-gap targeting** (Simula §8.3): map existing curated rows to the 7 classes, generate preferentially for under-covered classes/tiers. The W3 ledger is already class-balanced (8/7/7/7/7/7/7); DGM expansion must **preserve per-class balance and report per-class, never pooled** (existing F1 gate rule).

### 1.3 W3 curated-baseline validation gates (MANDATORY — the whole point)

A generated task advances through a fixed gate stack; failing any gate diverts it to reject or to the audit-only lane. Ordered:

| # | Gate | Rule | Rationale |
|---|---|---|---|
| G1 | **Schema-parity** | Row parses under the `real_suite_v1` YAML schema; `scoring_method ∈ {exact_match, multiple_choice, code_execution, programmatic, substring, f1, math_verify}` for the gate path | The eval-tower loader (`YAML_ONLY_SUITES`) only ingests this shape |
| G2 | **Scoreability** | Passes `eval_tower._is_scoreable_question(q)` deterministically (see §2.3). `code_execution` needs a real oracle; `exact_match/multiple_choice/substring/f1/math_verify` need `expected`; `programmatic` is expected-free | A row that cannot be graded deterministically cannot gate |
| G3 | **Verifier-parity** | Same row scores **identically under both `debug_scorer.py` copies** (orchestrator + research) on a fixed answer fixture (see §2.4 divergence table) | Prevents a task that passes in one repo and fails in the other from entering the corpus |
| G4 | **Double-critic QC** | Simula double-critic accepts the `(prompt, expected)` pair (Critic-1 YES *and* Critic-2 NO); disagreement → reject/auto-repair (§3.1) | Catches teacher/generator error in the reference answer itself |
| G5 | **Baseline-anchoring** | Class-share and (optional) embedding-diversity deltas vs the W3 baseline stay within bound; Elo-complexity distribution not pushed above the class's measured competence band (§3.2, §3.3) | SkillsBench-v3 drift protection; Simula weak-teacher caution |
| G6 | **HUMAN-CURATE (hard gate)** | A human confirms the curated batch before any promotion/gate use. No automated override. | The mandatory guard (§0) |

Only rows that clear **G1–G6** become corpus rows eligible for the autopilot gate, and even then only under the existing n-discipline ("do NOT let autopilot optimize against the suite until n is large enough — audit/promotion first").

### 1.4 Staged corpus lifecycle

```
generated (dgm_provenance stamped)
  → G1–G5 automated gates  → [fail] reject / audit-only lane
  → G6 human curate         → [reject] discard or revise
  → curated corpus (audit/promotion material)
  → n-discipline soak       → autopilot eval-tower gate (deterministic rows only)
```

This mirrors the reviewer-plane `shadow → advisory → narrow-canary → selective-authority` ramp from the umbrella plan: DGM tasks start as diagnostic/audit signal and earn gate authority only after human confirmation + accumulation.

---

## 2. F1-DGM-2 — Verifier-compatibility matrix

### 2.1 The scoring dispatch chain (as built)

```
eval_tower.py (T0/T1/T2/T3 runner)
  ├─ deterministic path:  seeding_scoring.score_answer_deterministic(...)
  │                         └─ from debug_scorer import score_answer   # ORCHESTRATOR copy (has math_verify)
  └─ rubric/judge path:   rubric_scoring.{build_rubric_judge_prompt, aggregate_rubric_score,
                                          deterministic_rubric_fallback}  # cross-family judge roles
```

- `eval_tower._is_scoreable_question(q)` decides gate-admittability **before** any model runs.
- The deterministic path resolves `debug_scorer` from the **orchestrator** copy (`scripts/benchmark/debug_scorer.py`), which is the superset (includes `math_verify`, stricter `code_execution` oracle gating, digit-separator-tolerant `substring`, diacritic-folding `f1`).
- The **research** copy (`epyc-inference-research/scripts/benchmark/debug_scorer.py`) is what research-repo benchmark harnesses import. It is **not identical** — see §2.4.

### 2.2 Scoring-method compatibility matrix

Grade = how DGM output maps to each method. "Gate-admittable" = can enter the autopilot gate deterministically (no judge).

| scoring_method | Deterministic? | Gate-admittable | Needs oracle/config | DGM-generatable | Notes for DGM |
|---|---|---|---|---|---|
| `exact_match` | ✅ pure | ✅ | `expected`; optional `extract_pattern` | ✅ easy | Numeric + number-word normalization built in; generate a crisp `<answer>`-taggable target |
| `multiple_choice` | ✅ pure | ✅ | `expected` = letter A–H | ✅ easy | Generate stem + labeled choices + gold letter; last-match parsing is robust |
| `substring` | ✅ pure | ✅ | `expected` substring | ✅ easy | **Orchestrator strips digit-group separators; research does not** (parity risk, §2.4). Comma-brittleness is a known scorer hazard (memory: `substring_scorer_comma_brittle`) |
| `f1` | ✅ pure | ✅ | `expected`; `threshold` (def 0.5) | ✅ easy | Token-overlap; **orchestrator folds diacritics (NFKD), research does not** (parity risk) |
| `programmatic` | ✅ pure | ✅ (expected-free set) | `verifier` name (+ params) | ✅ moderate | IFEval-style format checks; DGM must emit a supported `verifier` id. `language` verifier always passes (no langdetect) |
| `code_execution` | ✅ (sandboxed) | ✅ **iff oracle present** | `test_code` (asserts/unittest/`TEST_CASES`) or `entry_point`+`expected` | ✅ moderate | **CRITICAL parity gap**: orchestrator rejects a row with `test_code` that lacks a real assertion/unittest oracle; research copy will `return result.returncode == 0` — a task with a syntactically valid function and no real test **passes vacuously**. DGM `code_execution` rows MUST carry a genuine executable oracle and MUST clear G3 |
| `math_verify` | ✅ (symbolic) | ✅ | `extraction_mode`; needs `math-verify` lib | ⚠️ orchestrator-only | **Not present in the research copy** — falls back to `exact_match` there. Any DGM math task using `math_verify` fails G3 unless the research copy gains parity, or the task is authored to also pass `exact_match` |
| `llm_judge` | ❌ judge-dependent | ❌ (audit/promotion only) | judge server (port 8082) | ⚠️ generatable, **not gate-eligible** | Has a substring fast-path + substring fallback when judge is down, but the accept decision is a model call. Per F1 gate rule, rubric/judge items stay OUT of the autopilot gate |
| `rubric` (eval_tower) | ❌ judge-dependent | ❌ (audit/promotion only) | cross-family judge roles + `deterministic_rubric_fallback` | ⚠️ audit lane | Rubric path in eval_tower uses judge roles with a deterministic fallback; still not gate-eligible. Route DGM open-ended tasks here as diagnostic signal |

**Bottom line for the gate path**: DGM should generate against the **six pure-deterministic methods** (`exact_match`, `multiple_choice`, `substring`, `f1`, `programmatic`, `code_execution`-with-oracle). `math_verify` is admissible only if verifier-parity (G3) is first restored across the two repos. `llm_judge`/`rubric` tasks are welcome but land in the **audit/promotion lane, never the gate** — consistent with the existing F1 discipline.

### 2.3 Gate-admittability rule (reproduced from `eval_tower._is_scoreable_question`)

```
scoreable(q):
  if rubric-scored (method == "rubric" OR deep_research suite w/ expected_contains list): True
  if method == "code_execution": require real oracle
        (test_code startswith TEST_CASES  OR  executable assert  OR  unittest.TestCase
         OR (entry_point AND expected))
  else: has_expected(expected != "")  OR  method in {"programmatic"}   # expected-free set
```

This is the exact predicate DGM rows must satisfy at G2. Note `rubric` returns scoreable=True here but is still excluded from the *autopilot gate* by F1 policy — G2 admits it to the eval tower's *scored* set, G6 + F1 power-discipline keep it audit-only.

### 2.4 Two-repo verifier-parity divergences (the G3 checklist)

The two `debug_scorer.py` copies have drifted. A DGM task can score differently across them; G3 exists to catch exactly this. Known divergences today:

| Behavior | Orchestrator copy | Research copy | DGM impact |
|---|---|---|---|
| `math_verify` scorer | present | **absent** (→ `exact_match` fallback via unknown-method? actually raises `ValueError`) | Method unusable in research repo; G3 fails |
| `code_execution` no-oracle | **rejects** (returns False) | **runs code, returns `returncode == 0`** (vacuous pass) | Silent false-positives in research repo; hard G3 fail — require genuine oracle |
| `substring` digit separators | strips `,`/`_`/space between digits | no stripping | Numeric-answer tasks can flip |
| `f1` diacritic folding | NFKD fold before compare | no fold | Accented-token tasks can flip |
| `exact_match` `\boxed{}` fallback | absent (boxed handled in `math_verify`) | **present** | Boxed-answer tasks can flip |

**Recommendation**: G3 canonicalizes on the orchestrator scorer (it is what the eval-tower gate actually calls) and **requires the research copy to agree** on the fixture, OR the DGM build first reconciles the two copies. This is a pre-existing tech-debt surface F1-DGM surfaces but does not itself fix (see EV-13 `review_f1` clean-room scorer work and the `iq2_parity_eval` pattern already in-tree for parity-harness precedent).

---

## 3. F1-DGM-3 — Simula QC fold

Simula (`simula-synthetic-data-generation.md`, intake-410) is the published QC layer for exactly this synthetic-eval-generation step. Three mechanisms fold in; all are **design inputs** here (inference deferred to the operator loop).

### 3.1 Double-critic rejection sampling → validates the DGM reference answer (Gate G4)

The failure mode DGM shares with all self-generation: the generator can produce a `(prompt, expected)` pair where **`expected` itself is wrong**. A single "is this correct?" critic is sycophantic. Simula's fix (deep-dive §2):

```
Critic-1: "Is this reference answer CORRECT for this task?"   → p(correct)
Critic-2: "Is this reference answer INCORRECT for this task?" → p(incorrect)
Accept iff  Critic-1 == YES  AND  Critic-2 == NO
Disagreement → reject or auto-repair + re-critique
```

- Lift condition: `p(y) > p(y_corrupt)` — the critic must accept correct answers more than corrupted ones. Holds only where the local judge is competent on the class.
- **EPYC reuse target**: the double-critic pattern is already scoped for `q_scorer.py` (deep-dive §8.1; `orchestration/repl_memory/q_scorer.py` exists, 51KB). F1-DGM's G4 can share that critic implementation rather than build a second — one double-critic module, two callers (Q-scoring + DGM answer validation).
- Cost: 2× judge inference per candidate; runs offline in the operator loop, off the gate critical path.

### 3.2 Calibrated Elo complexity scoring → tiering + difficulty stratification (feeds G5)

The W3 ledger already has a `tier` field (1/2/3). Today tiers are assigned by source-suite heuristic. Simula's batch-wise pairwise Elo (deep-dive §3, §8.2) replaces that with a calibrated, cross-class-comparable difficulty score:

```
1. sample batches, each candidate appears K times
2. M3 assigns within-batch pairwise complexity
3. aggregate pairwise outcomes → per-candidate Elo
4. stratify into tiers by Elo band; calibrated across the 7 classes
```

- **New build**: `complexity_scorer.py` does **not** exist yet (Simula §8.2 proposes it under `epyc-inference-research/scripts/benchmark/`). F1-DGM-3 scopes it; it is a Wave-later build, not part of this design pass.
- Use: assign `tier` + `dgm_provenance.elo_complexity` to each generated row; drive coverage-gap generation by tier band; feed adaptive evaluation (start medium, escalate/de-escalate) to cut eval tokens.
- Validation precedent: Simula reports model-Elo aligns with human difficulty labels on MATH/Global-MMLU, and rejected samples carry systematically higher Elo — i.e. the critic filters what the model finds hard.

### 3.3 Weak-teacher caution → the hard limit on complexity per class (enforced at G5)

Simula's most important negative result (deep-dive §2 LEXam, §4 Fig-7, §5): **complexity is not universally good.** Where the teacher/generator is weak on a domain (LEXam: 57% teacher → **61% double-critic rejection**, high-complexity data *hurts*), pushing complexity is counterproductive because the generator gets hard answers wrong and encodes bad references.

Applied to F1's 7 classes: our local models are strong on some classes (code, benchmark/math) and **weak on EPYC-idiosyncratic classes** (governance/handoff, ops/deploy, planning/architecture-review — niche, project-specific, little public signal). For weak classes:

- **Expect high double-critic rejection** — that is correct behavior (the critic catching generator error), not a bug.
- **Do NOT push Elo complexity** in weak classes; cap generation to low-complexity bands there.
- **These weak classes are precisely where human-curate (G6) is non-negotiable** — the automated critic cannot exceed the generator's knowledge ceiling, so a human is the only reliable oracle.

This is the mechanistic reason SkillsBench-v3's −1.3pp shows up and why G5 bounds the complexity distribution per class against the W3 baseline.

### 3.4 Taxonomy coverage + mechanism-design principle

- **Taxonomy coverage** (deep-dive §8.3): map curated rows to the 7 workload classes (and, later, sub-taxonomies within a class); generate for under-covered nodes. This is the coverage engine behind §1.2 step 4.
- **Mechanism design / "no silver bullet"** (deep-dive §7): control coverage, complexity, and quality as *separate* axes and report them separately — do not collapse to one aggregate. F1 already enforces the per-class (never pooled) reporting rule; Simula extends it to per-axis.
- **Cost reality** (deep-dive §5): full Simula ≈ 5× inference vs baseline. All of it is deferred to the operator's long-horizon loop; this doc commits zero inference. Target scale is F1's regime — **hundreds to low-thousands of curated eval rows**, not the 512K-scale bulk generation Simula was built for (explicitly out of scope per deep-dive §8 "What Is NOT Transferable").

---

## 4. Decided vs. needs-a-later-build

**Decided in this scoping pass (design):**
- The mandatory guard and the G1–G6 gate stack, with human-curate as a hard, non-overridable node.
- DGM adoption = task-generation + archive + empirical-validation loop; **self-modification dropped**.
- Gate path restricted to the six pure-deterministic scoring methods; `math_verify` conditional on parity; `llm_judge`/`rubric` → audit/promotion lane only.
- Seed from W3 `real_suite_v1` + `workload_model.yaml` (7 classes), preserve per-class balance, report per-class/per-axis.
- Simula fold: double-critic → G4 answer validation (share `q_scorer` critic); Elo complexity → tiering/stratification; weak-teacher caution → per-class complexity cap.
- Verifier-parity (G3) canonicalizes on the orchestrator scorer; the two-repo divergence table is the G3 checklist.

**Needs a later build (implementation session, inference/code):**
1. A DGM generator harness (offline/batch) emitting W3-schema rows with `dgm_provenance`. NEW code, not in this pass.
2. `complexity_scorer.py` (Simula §8.2) — does not exist; batch-wise pairwise Elo utility in `epyc-inference-research/scripts/benchmark/`.
3. A shared double-critic module (Simula §2 / §8.1) factored out of / into `q_scorer.py`, callable as G4.
4. Verifier-parity reconciliation between the two `debug_scorer.py` copies (or a single canonical scorer + thin shims) — closes G3 mechanically. Overlaps EV-13 `review_f1` clean-room scorer + `iq2_parity_eval` precedent.
5. The automated gate-runner wiring G1–G5 (schema/scoreability/parity/critic/anchoring) + a human-curate review surface for G6.
6. Class-share + embedding-diversity delta metrics for G5 baseline-anchoring.

All builds are inference-gated and route through the operator's long-horizon `/loop` (no nightshift, quiet-window rider) per the umbrella plan.

---

## 5. Open questions for the implementation session

1. **Intake-ID discrepancy**: the F1 handoff + `recommendations.md` cite DGM as `intake-786` / arxiv `2505.22954`, but `intake_index.yaml` row `intake-786` is **STOP** (arxiv `2310.02304`). Reconcile the canonical DGM intake ID before wiring provenance. (Does not block the methodology; the DGM description in the handoff stands.)
2. **G3 canonicalization**: reconcile the two `debug_scorer.py` copies now (single canonical scorer) or gate-time-assert parity per task? A single scorer is cleaner but touches two repos' import surfaces.
3. **Double-critic judge model**: which local role is competent enough per class to satisfy `p(y) > p(y_corrupt)`? Weak classes (governance/ops/planning) may have **no** viable local critic → those classes may be human-curate-only from generation, not just at G6.
4. **Elo batch budget**: K-appearances × batch size × pairwise calls is the dominant inference cost. What K/batch gives stable tiers at F1's few-hundred-row scale?
5. **Corpus-vs-suite boundary**: does DGM output extend `real_suite_v1` in place (versioned `real_suite_v2`) or land in a separate `dgm_suite_v1` that is unioned only after soak? A separate suite keeps the human-curated W3 baseline pristine as the anchoring reference — recommended.
6. **Anchoring thresholds**: numeric bounds for G5 class-share / diversity / complexity drift are unset — needs the baseline distribution measured first.
7. **Weak-class policy**: confirm with the operator whether idiosyncratic EPYC classes should be generated at all, or captured passively only (W2/W3 path) and left out of DGM expansion.
