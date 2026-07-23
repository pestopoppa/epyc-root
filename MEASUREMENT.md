<!-- Adopted 2026-06-12 from the Fable 5 architecture review (handoffs/completed/fable5-proposed-MEASUREMENT.md).
     Amendments: PR-reviewed, append-or-version. The autopilot may READ this file, never edit it. -->

# MEASUREMENT.md — How numbers become claims in this project

**Purpose.** Every optimization decision here rests on a measurement. This file defines the *only* sanctioned ways to produce a performance or quality number, and the grammar for citing one. If a number in a handoff, index, journal, or planner prompt does not cite a protocol from this file, it is an observation, not a claim, and MUST NOT gate a decision.

**The one rule:** *A claim = (metric, protocol-id, n/reps, date, host-attestation ref).* Everything else in this file exists to make that rule cheap to follow.

## 1. Protocol registry

### P-BENCH-1 — Canonical single-instance decode (llama-bench)
- **Entry point**: `bench_canonical.sh` / `canonical_recipe.py` (epyc-inference-research) — **never hand-typed commands** (`feedback_use_codified_recipes_not_memory`; the 2026-05-28 session lost a day to recipe drift + a RUNPATH binary mismatch).
- Core recipe: `taskset -c 0-95 -t 96 -fa 1`, no `--numa distribute`, no GGML_* env unless the variant-under-test IS an env flag (then: one flag per arm). The recipe module enforces `OMP_DYNAMIC=false` + clang-20 libomp `LD_LIBRARY_PATH` and runs `assert_binary_resolves_correctly()` (readelf/ldd — the libllama RUNPATH guard).
- **Preconditions (all enforced or attested)**: no concurrent inference (`pgrep llama` zombie check; per `feedback_no_concurrent_inference` benches require an explicit operator window); host-health tier — uptime ≤1wk → `drop_caches` + **NUMA-interleave re-warm** (never bare re-read; `feedback_drop_caches_numa_eviction`), ≥1wk → reboot required (`feedback_host_throttle_check`); governor + `kernel.numa_balancing` checked per session (it self-resets); THP pool noted (production `--no-mmap --mlock` depletes it).
- **Reps**: ≥5 for claims of ≥5% effects; **≥10 for ≤2% effects**; report median + MAD. Cold-vs-warm declared. `-fa 1` always explicit (8–10% swing; llama-bench defaults 0).
- **Reference anchors**: 460 GB/s practical aggregate BW; per-thread share ≈ 4.79 GB/s × 96 (structural — not recoverable by code); NUMA law: ≤65GB models → 4×48t quarters 6–7× aggregate; 130–250GB → 1×96t; 192t anti-optimal.

### P-BENCH-2 — Canonical multi-instance / aggregate (production-shaped)
For quarter-split or concurrent-instance claims: launch via `orchestrator_stack.py` (never ad-hoc), canonical OMP env stack (PROC_BIND=spread, PLACES=cores, WAIT_POLICY=active, KMP_BLOCKTIME=10), mlock + sequential loading, **live-affinity verification** (`affinity_preflight.py` — topology_hash certifies intent, not reality), contention matrix certified fresh. Aggregate metric = sum of per-instance decode over identical prompt sets, same wall window.

### P-BENCH-3 — Batched/slot decode (NEW; the CPU14/E1/E2 regime)
Single instance, `-np N` sweep {1,2,4,8,16}, fixed question batch; metrics = aggregate tasks/hour AND per-stream p50/p95 latency; report per-N. Required before any batched-serving or batched-kernel claim. (No protocol existed for this regime — that absence is why it stayed an evidence vacuum.)

### P-QUAL-T1 — Autopilot trial-gate quality (the production instrument card)
- Instrument: **core_id** (versioned question set; currently the seed-42 accidental set — to be replaced per findings-01-impl Phase 2), n, per-question ledger ON, eval concurrency **fixed at 3** (part of the instrument — changing it is a new core version), scoring = deterministic methods only, `<think>` stripped.
- Published constants per core version: quantum (3/n), single-trial MDE (2 flips), per-suite resolution, known-dead items (must be zero after Phase 2.0 repair).
- Per-suite resolution = `1 / n_suite`. Example: tool_use has n=5 → resolution 0.2; coder has n=50 → resolution 0.02. A single-question flip on tool_use is -0.2 (one-fifth of the scale); on coder it is -0.02. **Do not treat all suites as having uniform resolution.**
- Decision rule: sequential e-process per `fable5-findings-01c` (`policy_version` cited in every verdict). Single-trial deltas below MDE are *never* decisions.
- **Anti-gaming**: question selection, seeds, and n are evaluator-side constants; rotating audit block correlation is published with the verdict.
- **Sentinel suites with non-standard execution**: tool_use runs `force_mode: "repl"` with substring scoring on tool-output. Moderate regressions (-0.2 to -2.9 on the 0-3 scale, i.e. 1–4 questions missed of 5) are **advisory only** (see `TOOL_USE_CATASTROPHIC_REGRESSION` in `safety_gate.py`); only catastrophic drops (≤ -3.0, ≥3 of 5 questions failed) are hard violations. This threshold is part of the instrument — changing it is a new core version.

### P-QUAL-PROMO — Promotion / generalization quality
Fresh stratified draw, **n ≥ 200**, qids unseen within 60 days, broken-suite items excluded by the suite-health table, runs only on `confirmed` candidates; its e-value multiplies the candidate's running E (combined threshold E ≥ 100 for baseline changes).

### P-AB-1 — Orchestrator A/B (routing, prompts, features)
Paired where possible (same questions both arms); **N ≥ 100/arm for production-role decisions** (the X-MAS lesson: a 20pp effect at N=25 collapsed to 4pp at N=100); every failure classified by reason (backend outage / timeout / empty / genuine — `feedback_classify_eval_failures_by_reason`) with infra-failure rate reported next to the effect; flag-state attestation across all workers recorded in the run header (the 1-of-6 worker lesson).

### P-SPEED-OBJ — The throughput objective (autopilot Pareto axis)
Axis = **task_rate** (questions / eval-wall-hour) per findings-05; t/s retained as host-health telemetry only; `speed_metric_mode`/`protocol_id` journaled; noise reference CV ≈ 9% → all rate claims via the non-inferiority/improvement e-process, never single-trial.

### P-SMOKE-1 — Sanity check (non-decision-gating)
A lightweight pass/fail sufficient to **unblock work** but **insufficient to gate any decision**. Examples: REPL sentinel 4/5 pass after infra fix; single-question smoke test before benchmark; one-shot model output extraction check. Citation format: `4/5 toolrunner sentinel pass [P-SMOKE-1, 2026-07-11]`. A smoke check that fails → investigate. A smoke check that passes → proceed, but still require a protocol-level claim before any keep/revert/deploy/promote decision.

### P-GPU-1 — GPU canonical (RATIFIED 2026-07-19; amendment appended at end of file)
Required fields when ratified: device state capture (rocm-smi clocks/power/temp before+after), warm-up policy, per-GCD memory residency check, host-side interference policy (CPU stack quiesced or declared), reps as P-BENCH-1, and a vendor-number rule: *no vendor-reported figure may appear in a decision row — local reproduction only* (`agentic-rocm-kernel-authoring.md` already flags gfx90a compile≠perf). **Close this placeholder when MI210 hardware is acquired or permanently deferred.**

## 2. Claim grammar & examples

- ✅ `frontdoor decode 27.06 t/s [P-BENCH-2, n=5, 2026-04-26, attest a3f2]`
- ✅ `config 9bd1 confirmed +2q on core_v2 [P-QUAL-T1/seq-v1, E=24.3, k=5, 2026-06-20]`
- ✅ `4/5 toolrunner sentinel pass [P-SMOKE-1, 2026-07-11]`
- ❌ `+17% with EP flags` (no protocol, no reps — this exact claim later collapsed to +1.6% under P-BENCH-1)
- Metric direction MUST be stated where ambiguous (`higher-better`/`lower-better`) — confirmed-direction errors have burned debugging time before (CLAUDE.md §Debugging).
- Comparisons only within a protocol + instrument version. Cross-protocol comparisons are analysis, labeled as such.

## 3. Standing noise & resolution table (update on instrument change)

| Quantity | Value | Source |
|---|---|---|
| T1 quality quantum / MDE | 0.0698 / 2 flips (≈4.7pp) | findings-01 §1 |
| Per-suite quantum | `1 / n_suite` (formula) | eval_tower per_suite_counts |
| Speed/rate noise | CV ≈ 9.1%, outliers to −27% under host drift | journal 714–776 |
| Host-throttle signature | multi-day uptime −60%+; drop_caches+rewarm restores | `feedback_host_throttle_check` |
| Practical BW anchor | 460 GB/s aggregate; 4.79 GB/s/thread | roofline findings.md |
| Tool-use sentinel resolution | 0.2 (n=5); advisory threshold -0.6 (1 miss of 5) | safety_gate.py TOOL_USE_CATASTROPHIC_REGRESSION |

## 4. Governance

- Changes to this file: PR-reviewed amendment with a one-line CHANGELOG; protocols are append-or-version, never silently edited.
- Validators: `check_claims_grammar.sh` (warn-mode month 1) over new handoff/index diffs; journal rows carry `protocol_id`; ATTESTATION artifact (findings-04 §B) is the `attest <id>` referent.
- The eval trust boundary (program.md) extends to this file: the autopilot may **read** it, never edit it.
- **Measurement-debt queue**: when a number is demoted-to-prior, a re-measure ticket is auto-created at `handoffs/active/measurement-debt/` keyed by corpus type. The master handoff index surfaces outstanding re-measure items. Closing a debt item requires the new measurement to cite the current protocol.

## 5. Retroactivity & reconciliation

**Scope first**: the claim grammar governs **decision-gating claims** — numbers that justify keep/revert, deploy, promote, buy, or close decisions. It does NOT govern training data (episodic memories, item-difficulty priors) or narrative history (progress logs, archived handoffs). Mislabeling those as "claims to be purged" would be the same category error this project keeps paying for in the other direction.

**The prime directive**: *never destroy primary records; demote, label, or re-derive interpretations.* Three verbs, applied per corpus:
- **retro-certify** — the number was provably produced by a now-named protocol (command/env/reps recorded). It gets `protocol_id: <P> (retro)` and full claim status. No re-measurement.
- **demote-to-prior** — real data from an unknown or known-flawed instrument. Keeps its place as evidence for *hypothesis formation* and item-difficulty priors; **cannot gate a decision**; a decision that today rests only on demoted numbers gets a re-measure ticket (priority = consumer impact).
- **retire-view** — derived artifacts (frontiers, baselines, dashboards) are rebuilt under the current policy/era; the old view is archived read-only, never edited in place.

Anything known-contaminated keeps its supersession tag (the existing `bug_corrupted_by` machinery) — tagged history, not deletion.

### 5a. Instrument-era table (load-bearing artifact)

Consumed by every replay/dashboard/verdict tool: `orchestration/instrument_eras.yaml`, append-only.

| Era | Boundary | What changed | Reconciliation |
|---|---|---|---|
| E0 → E1 | 2026-04-26 | Canonical bench protocol established (CPU20) | Pre-canonical CPU bench claims **demoted-to-prior** (precedent: EP +17%→+1.6% on re-measurement) |
| E1 → E2 | 2026-06-01T19:20:16Z | Speed objective de-double-counted | Pre-E2 speed **rescaled at read time** (×0.5 deinflate + `pareto_epoch_ts`) — ALREADY IMPLEMENTED |
| E2 → E3a | 2026-06-04 | Tool sentinels live (T0 n=15) | Pre-boundary: `tool_use` key ABSENT = era marker |
| E3a → E3b | 2026-06-05T13:07 (trial 652) | T1 n 38→43 (tool sentinels joined journaled T1) | Cross-n frontier entries split per era; within-era comparisons only |
| E3 → E4 | (instrument repair lands) | Dead items fixed/excised; core_v2; task_rate axis; sequential verdicts | **Retire-view**: T1 frontier/baselines restart fresh; E≤3 frontier archived; quality numbers NOT rescaled (different ceiling, different items) |
| E5-cpu-kernel | 2026-06-26T22:07:11Z | v6+iqk production cutover | Pre-boundary CPU throughput/quality **demoted-to-prior** (non-bit-exact vs v6+iqk); re-measure within era under P-BENCH/P-QUAL protocols |
| E3-routing | 2026-05-25T15:35:00Z | Episodic memory reset | All 287K+ rows post-date reset; **demote-to-prior wholesale** (trained under flawed-instrument eras, no reward decomposition) |

**New era class: `scope: autopilot_tooling`**. When orchestrator code (config, routing, extraction, backend init) is fixed and the fix retroactively invalidates historical measurements for specific suites, append an era with `scope: autopilot_tooling`. Reconciliation rule: **targeted re-measurement of affected suites only, not wholesale demotion**. Affected journal rows keep their values but get `bug_corrupted_by` tag; the planner/optimizer ignores them for the affected suites. Example: toolrunner backend missing from `ServerURLsSettings` (2026-07-11 fix) → all `tool_use` scores from trials where the backend was broken are `bug_corrupted_by: toolrunner_backend_missing`; only the `tool_use` suite on those trials is invalidated, not the full trial quality.

### 5b. Per-corpus reconciliation rulings

| Corpus | Items | Verb | Notes |
|---|---|---|---|
| **Bench results** (`data/cpu_optimization/`) | 65 dated dirs | 48/56 post-04-26 retro-certify (embed command lines + env as protocol witness); 8 doc-less + all 9 pre-canonical + ~30 March-era trees → demote-to-prior | Pre-canonical protocol empirically collapsed on re-measurement |
| **Autopilot journal** (current + rotated segments) | ~1200 rows | Immutable facts; never trashed, never rescaled in place. Era keys: `timestamp` vs `pareto_epoch_ts` for speed fix; `tool_use` key presence for tool-era; `details.total` for n-boundary | ⚠️ `speed_metric_mode` is FALSE FRIEND — identical on both sides of E2 boundary; never key on it |
| **Pareto archive / baselines** | 250 entries + 148 HV points | Entries retro-certify with era stamps; `hv_history_by_tier` (148 points, NO timestamps, pre-epoch on inflated speed) → retire-view, recompute from era-labeled entries | Frontier/baselines restart fresh at E4 |
| **Episodic/routing memory** | 287,682 rows | Demote-to-prior wholesale; out of claim scope (training data) | All trained under flawed-instrument eras; selective correction impossible (no reward decomposition stored) |
| **Model registries** (lean: 12, research: ~37) | 49 entries | Canonical-era values retro-certify; sweep-era (2026-03-21) and 2026-01 → demote + re-measure queue ordered by consumer impact | ⚠️ Free-text date/protocol in YAML comments — convert to structured `measured:` fields; reformat destroys the only witness |
| **Handoff/index claims** | 732 numeric claims across 71 files | History stays as written; grammar validator applies to **new diffs only**; 5+ index files → retire-view (regenerated citing protocols) | Rows ported to new master index cite protocol or carry `claim:unverified` |
| **Per-question eval corpora** | 3187 seeding + 1818 3way rows | Both demote-to-prior as item-difficulty priors feeding core_v2 selection | 3way set has zero scoring_method fields — era-labeled externally by date |
| **Strategy store / STM / planner narrative** | 1424+ entries | Governed by findings-01 Phase 4 (provenance or regeneration) | Narrative citing a demoted number fails provenance check |
| **Agent memory** | 49 of 108 files carry numbers | Pointers, not claims; new sessions re-verify per existing memory-recall caveat | Several already self-supersede |

### 5c. Known limits (hardest cases, accepted)

(a) Historical journal rows lack per-question IDs, so dead-question effects on old quality numbers cannot be retro-decomposed — old T1 quality is era-comparable only within (n, era); the per-question ledger starts clean at E4.

(b) Episodic Q-values cannot be selectively corrected (no decomposition stored) — wholesale demotion is the only honest verb.

### 5d. Explicit dump list (the only true deletions)

Everything else — including all 9.9/2.9-era supersession-tagged rows and dated backups — is kept.

- `autopilot_journal.{jsonl,tsv}.run3-poisoned` (104 rows, already named poisoned) and `archived_backups/autopilot_journal.jsonl.broken-run-backup` (6 rows).
- The 2026-04-29 *morning* multi-arch "Probe A" first-pass results (the canonical re-run's own decision.md calls them "almost entirely contamination"); keep the re-run.
- The two corrupted `thinking_deepseek_*_baseline` runs already listed in `benchmarks/results/REBENCHMARK_NEEDED.md` (precedent: 439 ×28-inflated spec_draft files were deleted 2026-01-15).
- Disk-hygiene candidates (operator call, not contamination): ~1.2GB of superseded embedding blobs under `repl_memory/sessions/` (reembedded.npz 602MB, pre-repair embeddings 227MB, pre-reset db backups).

## 6. Quick-reference: what to do when you encounter a number

1. **Era-label it first** — consult `instrument_eras.yaml` (match timestamp, scope, boundary).
2. **Apply the verb**:
   - `retro-certified` → use as a claim
   - `demoted-to-prior` → hypothesis only, do not gate, open re-measure ticket if it must gate
   - `retired-view` → consult the era-appropriate rebuilt view
3. **Never edit historical records to "fix" them** — append.
4. **New measurements** — cite a protocol from §1. No protocol → observation, not claim.

## P-GPU-1 — MI210 GPU canonical throughput (RATIFIED 2026-07-19)

**Supersedes** the prior "`P-GPU-1` deferred" status. Applies to all decision-gating GPU
(MI210 / gfx90a / HIP) throughput, spec-dec, and residency numbers. Metric direction:
higher-better (t/s) unless a lower-better metric is explicitly stated.

**Kernel-provenance rule (production-named kernels ONLY).** A `P-GPU-1` decision-grade claim
MAY ONLY be produced on a **production-named kernel** (`production-consolidated-vN`).
Measurements on any experimental / candidate / fork kernel (`llama.cpp-experimental`,
`experimental-v7-*`, branch builds) are **OBSERVATIONS ONLY**: they MUST NOT gate any
keep / revert / deploy / promote / buy / close decision, and MUST NOT be consumed by
AutoPilot or any automated optimizer.

**Required evidence fields — ALL mandatory. A claim missing ANY field is an observation.**
1. **Hardware state** — GPU model, gfx target, ROCm runtime + driver, visible device id,
   `llama-server --version`; llama.cpp commit + clean/dirty; `rocm-smi` clocks, power,
   temperature, utilization, VRAM, and PID mapping recorded **before AND after** each
   run/window; VRAM used before / during / after request / after cleanup.
2. **Host interference** — explicit CPU-stack state (quiesced, or declared non-quiesced with
   reason); `llama-server` / AutoPilot / KFD PID checks before and after; whether the CPU
   production stack is stopped, hidden from ROCm, or intentionally co-resident.
3. **Binary/model identity** — exact worktree, branch, commit, binary path, `LD_LIBRARY_PATH`,
   backend list; exact model path, mmproj (if used), quant, context, KV quant,
   reasoning/sampling flags, spec-dec mode.
4. **Run recipe** — warm-up policy; **fresh server per rep** unless resident-server mode is
   explicitly declared; discard rules for warm-up reps and shape-change graph recapture;
   **reps per the `P-BENCH-1` rule (n≥5 for ≥5% claims, n≥10 for ≤2% claims)**; fixed
   prompt/task set, prompt-token count, generated-token floor, seed + sampling policy.
5. **Result grammar** — report **median and MAD** for throughput plus prompt/decode split
   where available; for spec-dec, report draft generated/accepted counters and acceptance
   rate; for service/residency claims, report active-overlap tax and cleanup proof;
   vendor/web numbers may appear ONLY as background narrative, never in a decision row.
6. **Attestation** — a `P-GPU-1` decision row uses the standard grammar
   `metric [P-GPU-1, n/reps, YYYY-MM-DD, attest <ref>]`.

**Retro-certification (allowed, strict).** An existing GPU artifact MAY be upgraded from
observation to a `P-GPU-1` claim ONLY IF (a) it was produced on a **production-named kernel**
per the provenance rule above, AND (b) a field-by-field audit confirms **every** mandatory
field is present in the artifact. If any mandatory field is absent — including the
clocks/power/temperature before-and-after record — the artifact **remains observation-grade
and MUST be re-run** under this protocol. No partial upgrades.

**Consequence for the current v7 candidate.** The Gate-R residency number and the banked GPU
wins were measured on the *experimental* kernel, so they remain observations until re-run on
`production-consolidated-v7` after promotion. `P-GPU-1` ratification enables that
post-promotion certification; it does not upgrade pre-promotion experimental numbers.

### P-CAL — Verifier/answer calibration (ECE / AUROC)                    [added 2026-07-23]
- Instruments: eval-tower.math-rebaseline (GSM8K+MATH-500, n=1,819/arm, math_verify, seed 42,
  production sampling; run E7c 2026-07-23) and eval-tower.calibration-baseline.v1 (Scoring
  Verifiers HE-R+, n=820/arm, code_execution labels, seed 42; run EV-4c 2026-07-22). Era:
  E7-eval-instrument and later ONLY — pre-E7 calibration rows are void (proxy confidence).
- ECE = closed-top-bin stat_tests definition (ece_instrument_era=ev11b_closed_bin_2026_07_20),
  10 bins. Confidence = completion-probability geomean; a row gates ONLY when its aggregate
  carries confidence_is_real=True — proxy or mixed-provenance ECE is an observation FOREVER.
- Decision-capable uses (ESC-7 Option A, granted 2026-07-23 — DOMAIN-SCOPED): (a) RLVR reward
  calibration/discrimination components enter at their existing weights (rlvr_tiers) for
  provenance-clean CODE (code_execution-scored) rows only; (b) verifier-model promotion
  (EV-5/EV-7) may gate on code-domain ECE/AUROC against the same-domain P-CAL baseline.
  MATH: ECE usable as a cross-arm stability check only; math AUROC is an OBSERVATION
  (anti-discriminative 0.401/0.411 — geomean length confounding) pending EV-CONF-2
  (salient-token/answer-span confidence source).
- Baselines (era anchors, this amendment): code ECE 0.2532/0.3216, AUROC 0.6337/0.5751
  (frontdoor/worker_general, EV-4c); math ECE 0.2114/0.2199, AUROC 0.4013/0.4114
  observation-only (worker_general/worker_math, E7c). Ledger rows: EV-4-calibration-baseline,
  EV-11-math-rebaseline (2026-07-23).
### P-PAIRED — Paired A/B significance verdict (McNemar)                  [staged 2026-07-23; operator-apply]

  STATUS: STAGED for human review. This block is written by the P-PAIRED implementation
  session but NOT applied — the measurement trust boundary (MEASUREMENT.md §4) is
  human-amendment-only. The operator pastes this at the tail of MEASUREMENT.md by hand
  after auditing the cited implementation.

- Instrument identity. The paired-significance verdict surface is
  epyc-orchestrator `scripts/autopilot/paired_stats.py::mcnemar_verdict` (+ the
  `verdict_from_result` convenience and `MCNEMAR_EXACT_MAX_DISCORDANT` constant),
  driven from `scripts/autopilot/eval_tower.py::screen_paired_arms` (each matched pair
  carries a `verdict` block) and threaded per-role by
  `eval_tower.py::attach_role_paired_verdicts`. The producing instrument is
  eval-tower.math-rebaseline (GSM8K+MATH-500, n=1,819/arm, math_verify, seed 42,
  production sampling; `result.paired_significance` in each
  `eval_tower_math_rebaseline_*/summary.json`). Era: E7-eval-instrument and later ONLY —
  pre-E7 paired rows are void (proxy-scored arms). Metric direction: a lower two-sided
  p_value is stronger evidence of a real difference; the VERDICT, not the raw delta, is
  the decision object.

- Verdict semantics. Inputs are the discordant (flip) counts from
  `mcnemar_from_vectors`: b = a_correct_b_wrong (arm A wins the flip), c =
  a_wrong_b_correct (arm B wins the flip). The verdict block is
  {verdict, method:"mcnemar", approximation, n_discordant, p_value, z, alpha,
  exact_max_discordant}. Method selection by discordant count n_discordant = b + c:
  n_discordant <= 25 -> EXACT two-sided binomial sign test (approximation
  "exact_binomial", z null); n_discordant > 25 -> continuity-corrected NORMAL
  approximation (approximation "normal_approx", signed z; Edwards correction
  (|b-c|-1), two-sided p = erfc(|z|/sqrt(2))). Threshold rationale: the normal
  approximation is trustworthy only once b+c >= 25 (standard McNemar guidance), and the
  exact path divides by 2**n which overflows float64 past ~1000 discordant pairs — so the
  switch is both statistical and numerical. Verdict rule at alpha=0.05:
  "indistinguishable" unless p_value < alpha AND b != c; then "b_better" when c > b else
  "a_better". Provenance gate: a pair is scored ONLY when both arms declare, and agree
  on, {dataset_sha256, test_profile} (`paired_stats.require_matched_comparison`);
  mismatched/one-sided/both-missing provenance is refused to `mismatched_pairs`, never
  silently verdicted.

- Decision-capable uses (paired A/B keep/prefer on same-dataset, same-seed arms).
  A P-PAIRED verdict MAY gate a keep/prefer decision between two arms ONLY when both arms
  were scored on the identical question set (matching dataset_sha256) under the identical
  test_profile (matching scoring method, seed, sampling policy) — i.e. the pair appears in
  `pairs`, not `mismatched_pairs`, of the `result.paired_significance` block. Under that
  provenance: (a) verdict "a_better"/"b_better" (p_value < alpha) is decision-grade
  evidence to PREFER the winning arm over the loser for that dataset+profile; (b) verdict
  "indistinguishable" is decision-grade evidence of NO measured preference — it does NOT
  license a swap and MUST NOT be read as "equivalent" beyond this dataset/profile (a null
  is not proof of equality; report n_discordant so an underpowered null is visible). A
  verdict never gates across mismatched provenance, never upgrades a single-arm accuracy
  delta, and never gates outside the E7-eval-instrument era. Attestation grammar:
  `verdict [P-PAIRED, n_discordant/method, YYYY-MM-DD, attest <summary.json ref>]`.

- Baseline (era anchor, this amendment): E7c math re-baseline
  (`orchestration/reports/eval_tower_math_rebaseline_E7c/summary.json`), arms
  worker_general vs worker_math, seed 42: b=61, c=58, n_discordant=119 -> normal_approx,
  p_value ~0.855 -> verdict "indistinguishable" (the two worker arms are statistically
  indistinguishable on the math re-baseline; the ~0.2pp accuracy delta is inside the
  noise band). Ledger row: EV-11-math-rebaseline (2026-07-23). Tests:
  `tests/unit/test_paired_stats.py` (verdict known-answer: small exact + large normal,
  threshold boundary, direction, alpha), `tests/unit/test_eval_tower_paired_significance.py`
  (screen verdict attachment + per-role threading).
