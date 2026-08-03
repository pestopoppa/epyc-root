# Canonical Judge Suite Revamp — Replace a Saturated Instrument with Execution-Verified Ones

**Status**: stub — investigation scoped, nothing acquired, nothing run. Operator-authorised 2026-08-02.
**Created**: 2026-08-03
**Categories**: benchmark_methodology, evaluation, routing
**Related (owns adjacent work — do NOT duplicate)**: [`scoring-infra-standardization.md`](scoring-infra-standardization.md) (Track 2 owns the exec-scorer + coding ladder + LCB contamination refresh), [`architect-model-selection-bench.md`](architect-model-selection-bench.md) (owns the architect keep/drop verdict and its SWE/LCB arms), [`eval-tower-verification.md`](eval-tower-verification.md) (owns E-era eval-pool registration)
**Tracked in**: [`research-evaluation-index.md`](research-evaluation-index.md) — index row added 2026-08-03 (operator-approved).

## Problem

The canonical 79-question judge suite **cannot rank the current fleet**. Measured 2026-08-02:
a paired head-to-head of `architect_general` (Qwen3.6-27B Q8_0) vs `frontdoor` (Qwen3.6-35B-A3B Q8_0),
one judge (Qwen3.5-122B, neither arm), identical 70 questions, matched 8192-token per-slot budget:

| | architect_general (27B) | frontdoor (35B-A3B) |
|---|---|---|
| paired total (0–3 rubric) | **180 / 204 (88.2%)** | **179 / 204 (87.7%)** |
| per-question wins | 9 | 4 |
| ties | \multicolumn{2}{c}{55} |

Exact sign test on the 13 discordant pairs: **p = 0.267**. Not significant.

**The cause is ceiling saturation, not model equivalence.** 50 of 68 scored questions (**74%**) got a
perfect 3 from BOTH arms and carry zero discriminating information:

| suite | both-perfect | usable signal |
|---|---|---|
| general | 10/10 (100%) | none |
| thinking | 9/10 (90%) | almost none |
| math | 8/9 (89%) | almost none |
| coder | 7/9 (78%) | little |
| instruction_precision | 7/11 (64%) | some |
| agentic | 6/10 (60%) | some |
| tool_compliance | 3/9 (33%) | **the only informative suite** |

Evidence: `epyc-inference-research/data/judge_suite_headtohead_20260802/` (README + SHA256SUMS +
harness). Note the path uses **underscores**; the comment block in `public_benchmarks.yaml` writes it
with hyphens — one of them should be corrected when someone touches that file.

**What does discriminate.** Published benchmarks separate the same pair on **8 of 8** axes:
MMLU-Pro 86.2 / 85.2 · GPQA-D 87.8 / 86.0 · AIME26 94.1 / 92.7 · LiveCodeBench-v6 83.9 / 80.4 ·
SWE-bench-V 77.2 / 73.4 · Terminal-Bench-2 59.3 / 51.5. Locally, SWE-bench-oracle-40 separates
(27B 21/40 vs frontdoor 14/40 on a superseded run; the ratified comparable authority is **23/40**).
The operator notes olympiad-math also discriminates somewhat. Our own new `tool_compliance_local`
fleet run spreads **70.4–85.2% (14.8pp)** — and it is the one suite in the table above that was not
at ceiling.

**The unifying property of everything that works is that it is EXECUTION-VERIFIED or
PROGRAMMATICALLY CHECKABLE, not LLM-judged.** That is precisely the axis on which our suite failed.

## Scope — what this handoff owns, and what it must NOT re-do

This handoff owns **instrument selection for cross-model ranking**: acquiring candidate corpora,
sizing them, determining their execution requirements, and proving each one discriminates across
≥2 fleet models so `public_benchmarks.yaml` can be fed with locally-measured, rankable keys.

It does **not** own, and must reuse rather than rebuild:

- **`scoring-infra-standardization.md` Track 2** already built the execution substrate:
  `scripts/benchmark/code_exec_scorer.py` (subprocess isolation, RLIMIT_CPU/AS/CORE, process-group
  kill), `code_execution` dispatch inside the canonical `score_response`, `agentic_swe_harness.py`
  (multi-turn bash/edit loop, `/testbed` reset, lossless trajectory capture), and the canonical
  `answer_scoring.py` extractors. Its open items **2a-iii-followon** (cgroup `pids.max`) and
  **2a-iv** (bubblewrap isolation) are the hardening gate for any at-scale execution run — this
  handoff inherits that gate, it does not re-open it. Its **2d** already owns "pull a newer
  LiveCodeBench release (v5/v6 date-window)"; the LCB task below is scoped as *sizing + fleet-wide
  discrimination*, and the acquisition step should be executed once, jointly with 2d.
- **`architect-model-selection-bench.md`** owns the architect keep/drop verdict and its SWE/LCB
  arms. Ranking numbers produced here are inputs to that decision, never a re-litigation of it.
- **`eval-tower-verification.md`** / `scoring-infra-standardization.md` **2c** own registering any
  new suite into the **E-era eval pool**. Adopting a benchmark as a *ranking prior* is NOT the same
  act as registering it as an eval-tower row, and this handoff must not do the latter.
- **`eval-benchmark-cost-reduction.md`** owns the mid-range difficulty filter for fixed external
  evals. Once a candidate here is calibrated, that filter is how its per-run cost comes down —
  do not invent a second subsetting scheme.
- **`harness-selection-and-integration.md`** HS-10 already defines the evaluation-side harness
  randomization pattern and its negative precedent. Any multi-turn agentic candidate (tau-bench)
  inherits that pattern.

## Success criteria — what "this suite can rank our fleet" means operationally

A candidate is **adoptable** only if all four hold. These are the acceptance tests, not aspirations.

1. **Non-saturation.** < 25% of items scored perfect by both arms of the sharpest available pair
   (27B vs 35B-A3B). The current suite is at 74%; `tool_compliance` at 33% is the empirical proof
   that a suite below the line still ranks.
2. **Spread.** Fleet-wide score range ≥ ~10pp across the six text models, comparable to
   `tool_compliance_local`'s measured 14.8pp. A tighter spread is not automatically fatal, but it
   must be reported with a paired significance test, not a bare delta.
3. **Cross-model coverage of the SAME benchmark key.** ≥ 2 fleet models measured on one identical
   key, same slice, same scaffold. This is the criterion the published `bfcl_v3` / `bfcl_v4` split
   fails: two models, two keys, zero rankability.
4. **Objective oracle.** Pass/fail comes from execution or a deterministic checker. No LLM judge in
   the scoring path — that is the failure mode being replaced, and per MEASUREMENT.md scoring is a
   human-amendment-only trust boundary.

## Constraint — comparability is by BENCHMARK KEY, never by axis name

Two values are comparable **iff they share a benchmark key**. `aime26` ≠ `aime25`;
`ruler_1m` ≠ `longbench_v2` ≠ `mrcr_v2_128k`; `bfcl_v3` ≠ `bfcl_v4`. The `axes:` mapping in
`epyc-orchestrator/orchestration/public_benchmarks.yaml` is a **view for role relevance and must
never be used as a comparison unit** — collapsing keys under an axis name is exactly the mixed-scale
defect that put a 27-question long-context score into `quality_overall`. Every artifact this handoff
produces must be emitted under an explicit key that slots into that schema (`schema_version: 1`,
`benchmarks:` for vendor claims, `local_benchmarks:` for our own runs, `absent_from_card:` for
"not reported" — which is a required disclosure, never permission to infer a favourable value).

Precedent to follow: `tool_compliance_local`, added 2026-08-02 as a `local_benchmarks` key measured
across all six models under one judge and one budget. That is the shape of a good output here —
except the replacements should be execution-verified rather than judged.

## Scope limit — COLD-START VALUE ONLY

This is a **prior for routing before there is routed traffic**. Autopilot's measured rewards outrank
any static prior the moment real traffic exists, so the target is **"good enough to seed", not
exhaustive**. Concretely: prefer the smallest slice that satisfies the four success criteria; do not
build toward full-benchmark parity with vendor leaderboards; stop as soon as a candidate ranks.
Budget discipline matters more than completeness — the consumer is
`orchestration/repl_memory/q_scorer.py`'s degraded-path fallback and the compiled
`priors.quality_overall` mean over `universal_keys` (`mmlu_pro`, `gpqa_diamond`, `livecodebench_v6`),
both of which are overridden by measured rewards later.

## Disk — measured, and what is unknown

`/mnt/raid0` (overlay): **3.7T total, 3.4T used, 158G available, 96% full.** HF hub cache total: **42G**.
**Size corpus and execution substrate separately — they are not the same cost.**

| Asset | Corpus on disk | Execution requirement |
|---|---|---|
| GPQA-Diamond | **already cached, ~140K total**: `datasets--hendrydong--gpqa_diamond` 108K (198-row membership) + `datasets--ankner--gpqa` 2.0M (MC framing/distractors; `datasets--Idavidrein--gpqa` 28K, gated) | **none** — deterministic letter-match via canonical `extract_letter_answer` |
| LiveCodeBench (cached v1-era) | **8.8G measured** — `datasets--livecodebench--code_generation/snapshots/bb83f1c3.../test.jsonl` = 9,375,644,586 bytes, **400 rows**, contest window **2023-05-07 → 2024-03-02**. Size is dominated by inline private test cases, not problem text. Also `datasets--cassanof--livecodebench_lite_filtered` 364M, `datasets--minimario--livecodebench-execute` 324K | `datasets` **already installed (5.0.0)**, and the exec sandbox **already exists** (`code_exec_scorer.py`). The prior claim in `architect-model-selection-bench.md` that "LiveCodeBench needs `datasets`+exec-sandbox" was true when written (2026-07-24) and is now **satisfied** by `scoring-infra-standardization.md` 2a-i/2a-ii — only the 2a-iv isolation hardening remains before at-scale runs |
| LiveCodeBench v6 (date-windowed, post-cutoff) | **unknown — needs sizing.** The cached window predates these models' cutoffs and is contamination-suspect; a v5/v6 release is a separate download. Extrapolating from the cached release (~23MB/row) it could be multi-GB, but that is an estimate, not a measurement | same substrate as above |
| BFCL | **unknown — needs sizing. Nothing on disk** — no `bfcl` / `gorilla` path found anywhere under `/mnt/raid0/llm` or `/workspace/repos`. Corpus is JSON and expected to be small | **unknown — needs determination.** BFCL's executable categories require live/mocked API execution, which is a different substrate from `code_exec_scorer.py`'s stdin/stdout+assert model. AST-only categories may need no sandbox at all — size the two categories separately |
| tau-bench | **unknown — needs sizing. Nothing on disk** | **unknown — needs determination.** Multi-turn agentic with a simulated user; closest existing substrate is `agentic_swe_harness.py`, but the user-simulator is not built |
| SWE-bench (already paid for) | repo checkouts **1.3G measured** at `epyc-inference-research/artifacts/architect-code-eval-20260724/swebench_repos`; `swebench_verified.json` 7.8M; `questions_livecodebench_hard.json` 6.3M (materialised LCB-hard n=53); `.venv-swebench` 361M | official docker eval. **Not visible from this devcontainer's docker context** (19 images / 49.66G, none SWE) — the gold images live on the host daemon; confirm before assuming they are still cached |
| OlympiadBench | **736K measured** (`datasets--math-ai--olympiadbench`) | none — numeric/symbolic checker; `olympiadbench_numeric` / `olympiadbench_hard` adapters already registered |

Headroom read: GPQA-D and OlympiadBench are effectively free. LCB is the only candidate with a
material disk cost, and one release is already paid for. **BFCL and tau-bench corpus sizes are the
two genuinely unknown numbers and must be measured before any download is authorised** — 158G of
headroom at 96% full is not a lot of room for a surprise.

## Tasks

One block per candidate suite. Each block is the same five steps: **acquire corpus → size on disk →
determine execution requirement → wire a representative sample → verify it discriminates across ≥2
fleet models.** No inference runs without the standing region claim; no at-scale execution before
`scoring-infra-standardization.md` 2a-iv lands.

### CJ-1 — GPQA-Diamond (start here: unsaturated at this tier, zero acquisition cost)

- [ ] **CJ-1a. Acquire corpus** — already cached (`hendrydong/gpqa_diamond` 198 rows + `ankner/gpqa`
      framing). Confirm the 198/198 normalized-text match still holds; no download expected.
- [ ] **CJ-1b. Size on disk** — measured ~140K; confirm and record, no growth expected.
- [ ] **CJ-1c. Execution requirement** — expected **none**. Confirm scoring runs through canonical
      `answer_scoring.extract_letter_answer`, NOT a bespoke extractor (this is the exact suite that
      produced the 2026-07-24 verbose-penalty scorer artifact: A4 15% false parse-failures vs A1 0%,
      gpqa 43.4→53.0% on re-score). Use `gpqa_diamond_cot`, not the letter-only framing, unless the
      operator says otherwise — the letter-only prompt suppresses reasoning.
- [ ] **CJ-1d. Wire a representative sample** — the adapters exist (`gpqa_diamond`,
      `gpqa_diamond_cot` in `scripts/benchmark/dataset_adapters.py`). Decide n (full 198 vs a seeded
      subset) against the cold-start budget rule above.
- [ ] **CJ-1e. Verify discrimination across ≥2 fleet models** — vendor keys already span the fleet
      (27B 0.878 / 35B-A3B 0.860 / 122B 0.866 / Next-80B 0.729 / gemma4 0.823), so the local run's
      job is to confirm the ORDERING survives our Q8_0 + `enable_thinking=false` serving posture.
      Emit as `local_benchmarks.gpqa_diamond` under the same key as the vendor column.

### CJ-2 — LiveCodeBench (contamination-resistant via date-windowing; all six models publish it)

- [ ] **CJ-2a. Acquire corpus** — a **post-cutoff v5/v6 date window**, not the cached 2023-05→2024-03
      release. **Execute jointly with `scoring-infra-standardization.md` 2d, which already owns this
      acquisition** — do not run two downloads (see [[feedback_no_concurrent_downloads_shared_host]]).
- [ ] **CJ-2b. Size on disk** — cached release measured at 8.8G / 400 rows; **v6 size unknown**.
      Measure BEFORE downloading if the API allows, and check it against 158G of headroom.
- [ ] **CJ-2c. Execution requirement** — substrate exists (`code_exec_scorer.py` + `code_execution`
      dispatch, `datasets` 5.0.0 installed). Record explicitly that the harness's *shipped* LCB
      adapter loads `greengerong/leetcode` (2,360 LeetCode problems) and its `code_execution` was a
      **stub with commented-out asserts** — the real stdin/stdout materialisation happened separately
      into `questions_livecodebench_hard.json`. Reuse that materialisation path; do not trust the
      adapter's default. Gate at-scale runs on 2a-iv isolation hardening.
- [ ] **CJ-2d. Wire a representative sample** — reuse the existing hard-slice construction (n=53
      precedent) rather than authoring a new sampler.
- [ ] **CJ-2e. Verify discrimination across ≥2 fleet models** — the strongest candidate for
      cross-model coverage: `livecodebench_v6` is one of the three `universal_keys` and **every** text
      model reports it (0.839 / 0.804 / 0.804 / 0.789 / 0.566 / 0.771). Emit under a key that names
      the window (`livecodebench_v6`, or a distinct key if the local window differs — a different
      window is a **different benchmark key**, per the comparability constraint above).

### CJ-3 — BFCL (execution-verified tool use; would replace the 9-question LLM-judged proxy)

- [ ] **CJ-3a. Acquire corpus** — nothing on disk today. Identify the release and license before
      downloading.
- [ ] **CJ-3b. Size on disk** — **unknown, needs sizing.** Expected small (JSON), but measure.
- [ ] **CJ-3c. Execution requirement** — **unknown, needs determination, and size it separately from
      the corpus.** Split the answer by category: AST/relevance categories are likely checker-only;
      executable categories need live or mocked API execution, which `code_exec_scorer.py` does NOT
      currently model. State which categories we can run and which we decline.
- [ ] **CJ-3d. Wire a representative sample** — note that the orchestrator's production tool path is
      the bespoke Python-REPL protocol (`TOOL()/CALL()/FINAL()`), **not** llama-server native
      function calling, and `ChatRequest.tools` is accepted-but-never-consumed. Decide deliberately
      whether the local BFCL run measures the production REPL path or the native-function-call path —
      they are different instruments and must not share a key. The tool-call parser is already pinned
      (`epyc-orchestrator` `22c476dd`; Qwen XML deliberately unparsed so a parse failure cannot
      masquerade as a quality gap).
- [ ] **CJ-3e. Verify discrimination across ≥2 fleet models** — this is the highest-value fix in the
      set: the published BFCL evidence is **unrankable today** (122B reports `bfcl_v4` 0.722,
      Next-80B reports `bfcl_v3` 0.703 — two keys, no comparison). A single local run under ONE key
      across ≥2 models resolves that. Baseline to beat: `tool_compliance_local`, 70.4–85.2%.

### CJ-4 — tau-bench (multi-step agentic)

- [ ] **CJ-4a. Acquire corpus** — nothing on disk. Lowest priority of the four; treat as a stretch
      candidate.
- [ ] **CJ-4b. Size on disk** — **unknown, needs sizing.**
- [ ] **CJ-4c. Execution requirement** — **unknown, needs determination.** It needs a simulated-user
      loop, which we do not have; `agentic_swe_harness.py` is the nearest substrate but models a
      bash/edit loop, not a conversational counterparty. Cost this honestly before proposing a build —
      a user simulator that is itself an LLM reintroduces exactly the judged-scoring failure mode.
- [ ] **CJ-4d. Wire a representative sample** — only after CJ-4c says the oracle is objective.
- [ ] **CJ-4e. Verify discrimination across ≥2 fleet models** — note no fleet model publishes
      tau-bench, so there is no vendor column to corroborate against; a local run stands alone.
      `terminal_bench_2` (published by 4 of 6 models, spread 0.494–0.593) is the cheaper agentic
      ranking signal if this proves expensive.

### CJ-5 — Cross-cutting

- [ ] **CJ-5a. Record every result under an explicit benchmark key** in the
      `public_benchmarks.yaml` schema (`local_benchmarks:` for our runs, `absent_from_card:` where a
      model does not report it). Never merge two keys under one axis name.
- [ ] **CJ-5b. Report the saturation and spread statistics for every candidate**, not just the mean:
      both-perfect fraction, fleet range, and a paired significance test on the sharpest pair. A
      candidate that ranks by mean but is 70% saturated has not passed criterion 1.
- [ ] **CJ-5c. Decide the fate of the existing 79-question suite** — retire, retain as a regression
      tripwire, or re-tier with harder questions. It is still the instrument behind
      `benchmarks/prompts/v1/*.yaml` and the 2026-05-04 anchor; deleting it silently would break
      comparability with that anchor. Propose, do not execute.

## Decision gate (OPERATOR)

- [ ] **CJ-GATE. Which suites to adopt is an OPERATOR decision, not the executor's.** Once CJ-1…CJ-4
      report corpus size, execution requirement, and measured discrimination, present a decision
      package per the canonical contract (`agents/shared/OPERATING_CONSTRAINTS.md` →
      *Operator Decision Requests*): options + tradeoffs + a recommendation. Do **not** adopt a
      suite, retire the canonical suite, edit `public_benchmarks.yaml`'s `universal_keys`, or
      register anything into the E-era eval pool unilaterally. Adoption as a *ranking prior* and
      registration as an *eval-tower row* are two separate decisions and must be presented as such.

## Key files / surfaces

- `epyc-inference-research/data/judge_suite_headtohead_20260802/` — the saturation evidence
  (README, SHA256SUMS, `run_judge_suite.py` with its pre-registered reporting contract,
  `judge_local.py`).
- `epyc-inference-research/scripts/benchmark/dataset_adapters.py` — adapter registry; `gpqa_diamond`,
  `gpqa_diamond_cot`, `livecodebench`, `olympiadbench_numeric`, `olympiadbench_hard` already exist.
- `epyc-inference-research/scripts/benchmark/code_exec_scorer.py`, `answer_scoring.py`,
  `agentic_swe_harness.py`, `suites.py` — the reuse surface.
- `epyc-inference-research/benchmarks/prompts/v1/*.yaml` — the 79-question canonical suite itself.
- `epyc-orchestrator/orchestration/public_benchmarks.yaml` — the schema this must feed.
- `epyc-orchestrator/orchestration/repl_memory/q_scorer.py` (L109-125) and
  `src/registry/model_descriptors.py` — the only two consumers; `q_scorer`'s
  `BASELINE_QUALITY_BY_MODEL` **mirrors** the compiled priors and must be re-mirrored whenever
  `public_benchmarks.yaml` changes (it silently disagreed for two measurement cycles before
  2026-08-02).

## Reporting

Update this handoff after each candidate block; flip `- [ ]` → `- [x]` with `✅ YYYY-MM-DD` and the
evidence path. Per-block commits with `-- <paths>` (shared tree). Record disk measurements as
measurements — write `unknown — needs sizing` rather than an estimate, and never let an estimate
harden into a cited number. All external benchmark figures remain OBSERVATION-grade under
MEASUREMENT.md and may never be stated as measurements of this deployment; the six-point SWE-bench
disclosure standard in `scoring-infra-standardization.md` applies to any external coding figure
quoted here. See [[feedback_eval_saturation_masks_model_gap]],
[[feedback_parse_failure_rate_is_a_scoring_artifact]], [[feedback_model_not_role_indexing]].
