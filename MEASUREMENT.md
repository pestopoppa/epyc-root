<!-- RATIFIED by operator 20260730T103218Z — see RATIFICATION_LEDGER in the apply bundle.
     Applied via apply_v2.sh --apply; delta record: artifacts/operator/measurement-v2-draft/RATIFICATION_LEDGER.md.
     Every semantic difference vs v1 is enumerated in RATIFICATION_LEDGER.md in this directory.
     Amendments: human-only, PR-reviewed, append-or-version. The autopilot may READ, never edit. -->

# MEASUREMENT.md — How numbers become claims in this project

**Purpose.** Every optimization decision rests on a measurement. This file defines the *only*
sanctioned ways to produce a performance or quality number and the grammar for citing one. A
number that does not cite a protocol from the registry below is an **observation**, not a claim,
and MUST NOT gate a keep / revert / deploy / promote / buy / close decision.

**The one rule:** *A claim = (metric, protocol-id, n/reps, date, host-attestation ref).*
Everything else exists to make that rule cheap to follow.

**Document layout (v2).** This core file holds the constitution: claim grammar, metric scoping,
protocol index, noise table, governance, and retroactivity. Full normative protocol text lives in
four annexes in `measurement/protocols/`, which carry the SAME trust boundary and amendment rules as this
file — they are the constitution, filed by family or instrument class, not commentary on it. Daily-use guidance for
sessions is the digest at `agents/shared/MEASUREMENT_POLICY.md`; when in doubt, this file and its
annexes win.

## 1. Metric scoping — task_rate vs tokens/s

Two speed metrics coexist; each is authoritative in its own scope and MUST NOT be substituted
for the other:

- **`task_rate` (tasks / eval-wall-hour, higher-better)** is the **autopilot objective axis**
  (`P-SPEED-OBJ`, per findings-05) and the only speed metric for whole-system / cross-device
  decisions where tokens are not commensurable across arms (different models, tokenizers, or
  devices — e.g. `P-SHED-1`). Noise reference CV ≈ 9.1%: all rate claims go through the
  non-inferiority / improvement e-process, never a single trial. `speed_metric_mode` /
  `protocol_id` journaled.
- **tokens/s (prefill or decode, higher-better)** is the **instrument-level metric** for
  individual model / kernel / configuration benchmarks (`P-BENCH-*`, `P-GPU-1`). Within those
  protocols t/s is fully decision-grade. The v1 phrase "t/s retained as host-health telemetry
  only" applies ONLY inside the autopilot objective scope — it does not demote t/s claims
  produced under a bench protocol.

Metric direction MUST be stated wherever ambiguous (`higher-better` / `lower-better`) —
confirmed-direction errors have burned debugging time before (CLAUDE.md §Debugging).

## 2. Protocol registry (index)

Full normative text: **B** = `measurement/protocols/bench-cpu.md`, **Q** =
`measurement/protocols/quality-eval.md`, **G** = `measurement/protocols/gpu-cross-device.md`,
**K** = `measurement/protocols/kernel-research.md`.
Status: ✅ ratified, 📋 staged (operator-apply).

| Protocol | Scope | Metric (direction) | Status | Annex |
|---|---|---|---|---|
| P-BENCH-1 | Canonical single-instance CPU decode (llama-bench) | decode t/s (↑) | ✅ | B |
| P-BENCH-PREFILL-1 | Canonical single-instance CPU prefill | prefill t/s (↑) | ✅ 2026-07-24 (+07-25 amend) | B |
| P-BENCH-2 | Multi-instance / aggregate, production-shaped | aggregate decode t/s (↑) | ✅ | B |
| P-BENCH-3 | Batched/slot decode (`-np N` sweep) | aggregate + per-stream decode tok/s (↑) primary, per §1; p50/p95 latency (↓); tasks/h retained secondary | ✅ | B |
| P-BENCH-4 | Single-instance server-native spec-dec (FG-4b) | decode t/s (↑) | ✅ (+affinity superseding amend) | B |
| P-BENCH-PLACEMENT-1 | CPU affinity / NUMA memory policy / mmap mode / instance count / slot concurrency | aggregate + per-stream decode tok/s (↑) | ✅ 2026-07-30 | B |
| P-QUAL-T1 | Autopilot trial-gate quality (production instrument card) | suite score | ✅ | Q |
| P-QUAL-PROMO | Promotion / generalization quality | e-value | ✅ | Q |
| P-AB-1 | Orchestrator A/B (routing, prompts, features) | paired effect | ✅ | Q |
| P-CAL | Verifier/answer calibration | ECE (↓) / AUROC (↑) | ✅ 2026-07-23 | Q |
| P-PAIRED | Paired A/B significance verdict (McNemar) | verdict (not delta) | 📋 staged 2026-07-23 | Q |
| P-SMOKE-1 | Sanity check — unblocks work, gates nothing | pass/fail | ✅ | Q |
| P-SPEED-OBJ | Autopilot throughput objective | task_rate (↑) | ✅ | §1 above |
| P-GPU-1 | MI210 GPU canonical throughput | t/s (↑) | ✅ 2026-07-19 | G |
| P-SHED-1 | Cross-device shed trade (CPU→GPU displacement) | net task_rate (↑) | ✅ | G |
| P-DFLASH-LINEUP-1 | DFlash lineup enablement (per-lane) | acceptance + t/s ratio (↑) | ✅ 2026-07-25 | G |
| P-AK-SEARCH-1 | Kernel-candidate search inside experimental worktrees, per-backend | search verdict — **not a claim**; direction carried per record | ✅ 2026-08-03 | K |

## 3. Claim grammar & examples

- ✅ `frontdoor decode 40.22 tok/s per-stream, spec-dec on (draft-mtp n_max 4), arm A2 [P-BENCH-PLACEMENT-1, n=3, 2026-07-30, attest epyc-inference-research/data/numa_placement/20260730-P-BENCH-PLACEMENT-1/prodopt_results.txt]`
  <!-- Replaced 2026-07-30. The prior exemplar, `frontdoor decode 27.06 t/s
  [P-BENCH-2, n=5, 2026-04-26, attest a3f2]`, was the NUMA_NODE0-arm figure from the
  2026-04-17 head-to-head, invalid twice over: it predates the 2026-04-24 NPS4 reboot
  (when `0-47,96-143` genuinely was one NUMA node) and its source CSV records
  `spec == "baseline"`. The replacement is deliberately a PRODUCTION-RECIPE figure
  (spec-dec on), not a baseline. Grammar note: ✅ marks the FIELDS as complete; rep
  adequacy for a decision is still judged by the owning protocol's reps rule — this
  n=3 figure is an anchor; effect claims against it need reps per P-BENCH-1. -->
- ✅ `config 9bd1 confirmed +2q on core_v2 [P-QUAL-T1/seq-v1, E=24.3, k=5, 2026-06-20]`
- ✅ `4/5 toolrunner sentinel pass [P-SMOKE-1, 2026-07-11]`
- ❌ `+17% with EP flags` (no protocol, no reps — this exact claim later collapsed to +1.6%
  under P-BENCH-1)
- Comparisons only within a protocol + instrument version. Cross-protocol comparisons are
  analysis, labeled as such.
- **Category (required)**: every reported measurement declares exactly one of
  `category=OPTIMUM` · `category=BASELINE` · `category=CANDIDATE`.
  - `OPTIMUM` — the best configuration AVAILABLE for that model/role. If no
    speculative draft path exists for the model, the unaccelerated run IS its
    OPTIMUM (e.g. Qwen3-Next-80B-A3B `--spec-type none`); such a row is a headline
    row, NOT a baseline.
  - `BASELINE` — an optimization the model HAS, deliberately switched off.
    Diagnostic only. Appears only under *Addendum — baselines*. Never a headline.
  - `CANDIDATE` — measured, not adopted. Must be labelled so it is never mistaken
    for what production runs.
  An unlabelled measurement is not decision-grade.
  ✅ `ingest_long_context decode 10.12 tok/s, category=OPTIMUM (no draft path exists;
  spec none is optimal) [P-BENCH-1, n=5, 2026-07-31, attest …]`
  ❌ `frontdoor decode 24.92 tok/s, spec-dec off` (no category; reads as a headline,
  is a BASELINE)
- Per-protocol grammar extensions (e.g. `P-PAIRED` verdict rows, `P-SHED-1` f/stress fields)
  are defined in each protocol's annex entry.

## 4. Standing noise & resolution table (update on instrument change)

| Quantity | Value | Source |
|---|---|---|
| T1 quality quantum / MDE | 0.0698 / 2 flips (≈4.7pp) | findings-01 §1 |
| Per-suite quantum | `1 / n_suite` (formula) | eval_tower per_suite_counts |
| Speed/rate noise | CV ≈ 9.1%, outliers to −27% under host drift | journal 714–776 |
| Host-throttle signature | multi-day uptime −60%+; drop_caches+rewarm restores | `feedback_host_throttle_check` |
| Practical BW anchor | 460 GB/s aggregate; 4.79 GB/s/thread | roofline findings.md |
| Tool-use sentinel resolution | 0.2 (n=5); advisory band −0.2..−2.9; hard-fail ≤ −3.0 | safety_gate.py `TOOL_USE_CATASTROPHIC_REGRESSION` |

## 5. Governance

- **Amendments**: human-only, PR-reviewed, append-or-version — protocols are never silently
  edited. An amendment appends to the owning annex file and adds a one-line entry to the
  CHANGELOG block at the end of this core file. Superseding amendments name what they supersede.
- **Trust boundary**: this file, its `protocols/` annexes, the era registry, the eval tower, and
  scoring contracts are read-only for autonomous optimization processes (program.md).
- **Promotion is decided on the production-optimal configuration alone.** A regression in a
  `BASELINE`-category measurement is NOT a promotion blocker and MUST NOT be cited as one;
  a `BASELINE` improvement is NOT a promotion argument. Baselines are recorded to quantify
  what an already-adopted optimization buys, and appear only in an addendum. A gate that
  blocks on a non-production arm is defective and is repaired, not waived. Where an
  instrument cannot exercise the role's registered production recipe (e.g. `llama-bench`
  cannot drive speculative decoding), its cells are RECORDED and reported alongside and
  MUST NOT by themselves block promotion. Supersedes the protocol-scoped statement at
  `measurement/protocols/bench-cpu.md:216-220`, which is generalised by this clause.
- **Deterministic replay before regeneration** *(operator-ratified 2026-07-27; absorbed into the
  constitution by this v2 — previously lived only in the digest)*: if a result can be obtained
  without inference — by deterministically rescoring or transforming previously saved outputs —
  ALWAYS do that instead of regenerating. Scorer/converter/extractor defects get a tail replay
  over banked outputs; regenerate only when the generation path itself was defective. Quality
  scores transfer across kernel eras once parity is proven; rebaseline only the axis that
  changed. Before any full-suite rerun, prefer focused runs on the discordant items. Pre-commit
  a stopping rule before any bench campaign.
- **Consolidated apply-time ratification** *(operator-ratified 2026-07-27; absorbed likewise)*:
  evidence collection and validation never wait on a human signature. The human signs ONCE, at
  apply time, over a consolidated bundle (protocol + evidence hashes + validation results +
  exact state diff). Human-only writes remain exactly: era-registry rows, this constitution and
  its annexes, AutoPilot baseline-state applies, production freezes/cutovers, host reboots. A
  failed validation re-presents the SAME apply token with updated hashes — never a restarted
  chain. Boundary tokens are presented only while compute is saturated; unrelated work never
  gates on a pending token. Operator-presented commands must be pre-validated end-to-end.
- **Evidence must be DURABLE, not merely hashed** *(operator-ratified 2026-08-02)*: a
  ratification bundle records evidence hashes, but a hash over an artifact that no longer
  exists proves nothing — there is nothing left to check it against. Evidence backing any
  ratified or production-affecting claim MUST therefore live inside a repository, under
  `epyc-inference-research/data/<campaign>/`, with a `SHA256SUMS` and a README stating what
  was measured, when, and which claim it backs. Scratch paths (`/mnt/raid0/llm/tmp/...`) are
  valid for work in progress and MUST NOT appear as the evidence citation of a ratified
  claim. Artifacts too large to carry (multi-GiB imatrix files, build trees) are recorded
  hash-and-provenance-only, and the citation says so explicitly rather than pointing at a
  blob that is not there. Enforced by `scripts/validate/check_evidence_durability.py`, which
  fails on any citation resolving outside the repository or to a missing path.
  *Origin: on 2026-08-02 the master registry was found citing 158 unique scratch paths,
  including the MMMU-250 result that gated a live vision model cutover. 152 still existed and
  4.0 MiB carried nearly all of them — full exposure, no loss yet. The gap was constitutional
  rather than clerical: §5 mandated the hash and was silent on where the artifact must live.*
- **Validators**: `scripts/validate/check_claims_grammar.sh` (warn-mode; scans new handoff/index
  diffs for uncited decision-flavored numbers — built 2026-07-30 per ledger L5); journal rows
  carry `protocol_id`; the ATTESTATION artifact (findings-04 §B) is the `attest <id>` referent.
- **Measurement-debt queue**: when a number is demoted-to-prior, a re-measure ticket is created
  at `handoffs/active/measurement-debt/` keyed by corpus type; the master handoff index surfaces
  outstanding items. Closing a debt item requires a new measurement citing the current protocol.

## 6. Retroactivity & reconciliation

**Scope first**: the claim grammar governs **decision-gating claims** only. It does NOT govern
training data (episodic memories, item-difficulty priors) or narrative history (progress logs,
archived handoffs). Mislabeling those as "claims to be purged" is the inverse category error.

**Prime directive**: *never destroy primary records; demote, label, or re-derive
interpretations.* Three verbs:

- **retro-certify** — provably produced by a now-named protocol (command/env/reps recorded) →
  `protocol_id: <P> (retro)`, full claim status, no re-measurement.
- **demote-to-prior** — real data from an unknown/flawed instrument → hypothesis formation and
  item-difficulty priors only; CANNOT gate; a decision resting only on demoted numbers gets a
  re-measure ticket (priority = consumer impact).
- **retire-view** — derived artifacts (frontiers, baselines, dashboards) rebuilt under current
  policy/era; the old view archived read-only, never edited in place.

Known-contaminated data keeps its supersession tag (`bug_corrupted_by`) — tagged history, not
deletion.

### 6a. Instrument-era registry

The authoritative era table is `epyc-orchestrator/orchestration/instrument_eras.yaml`
(append-only, human-written, consumed by every replay/dashboard/verdict tool). This file no
longer duplicates it — the v1 copy had silently gone stale (missing E6/E7/E8). Era-class rules
that ARE constitutional:

- Each era row names its boundary, scope, and reconciliation verb; within-era comparisons only.
- **`scope: autopilot_tooling`**: when an orchestrator code fix retroactively invalidates
  historical measurements for specific suites, append an era with this scope. Reconciliation =
  targeted re-measurement of affected suites only, never wholesale demotion: affected journal
  rows keep values but get `bug_corrupted_by`; the planner ignores them for those suites only.
  (Example: 2026-07-11 toolrunner backend fix → only `tool_use` scores on broken-backend trials
  invalidated, not full trial quality.)
- ⚠️ Era-keying false friend: `speed_metric_mode` is identical on both sides of the E2 speed fix
  — key on `pareto_epoch_ts`, never on it.

### 6b. Per-corpus reconciliation rulings (2026-06 reconciliation, still governing)

| Corpus | Items | Verb | Notes |
|---|---|---|---|
| Bench results (`data/cpu_optimization/`) | 65 dated dirs | 48/56 post-04-26 retro-certify (command lines + env as witness); 8 doc-less + 9 pre-canonical + ~30 March-era → demote | Pre-canonical protocol empirically collapsed on re-measurement |
| Autopilot journal (current + rotated) | ~1200 rows | Immutable facts; never rescaled in place; era keys per 6a | |
| Pareto archive / baselines | 250 entries + 148 HV points | Entries retro-certify with era stamps; `hv_history_by_tier` (no timestamps, inflated speed) → retire-view | Frontier/baselines restart fresh at E4 |
| Episodic/routing memory | 287,682 rows | Demote wholesale; out of claim scope (training data) | No reward decomposition stored → selective correction impossible |
| Model registries (lean 12, research ~37) | 49 entries | Canonical-era retro-certify; sweep-era 2026-03-21 + 2026-01 → demote + re-measure queue | ⚠️ Free-text date/protocol YAML comments are the only witness — reformats must not destroy them |
| Handoff/index claims | 732 claims / 71 files | History stays as written; grammar rule applies to new diffs only; 5+ index files → retire-view | Ported rows cite protocol or carry `claim:unverified` |
| Per-question eval corpora | 3187 + 1818 rows | Both demote as item-difficulty priors feeding core_v2 | 3way set era-labeled externally by date (no scoring_method fields) |
| Strategy store / STM / planner narrative | 1424+ entries | Findings-01 Phase 4 (provenance or regeneration) | Narrative citing a demoted number fails provenance |
| Agent memory | 49/108 files carry numbers | Pointers, not claims; sessions re-verify per memory-recall caveat | |
| Kernel-research strategy store (`scripts/kernel_rnd/kernel_store.py` SQLite; rows written before 2026-08-03) | pre-ratification rows | demote-to-prior (:180-182) + quarantine | Narrows the `Strategy store / STM / planner narrative` ruling above for these rows only — their evaluator never gated on coherence, so correctness labels were emitted without an anchor comparison and are not verdicts. Quarantined from every correct-only frontier and readiness computation; a lineage decision resting only on them gets a re-measure ticket (:164-166). Rows of that corpus written by the routing planner or the STM are NOT affected. |

**Known limits (accepted)**: (a) historical journal rows lack per-question IDs — old T1 quality
is era-comparable only within (n, era); the per-question ledger starts clean at E4. (b) episodic
Q-values cannot be selectively corrected — wholesale demotion is the only honest verb.

**Explicit dump list (the only true deletions)** — everything else, including supersession-tagged
rows and dated backups, is kept: `autopilot_journal.{jsonl,tsv}.run3-poisoned` (104 rows) +
`archived_backups/autopilot_journal.jsonl.broken-run-backup` (6 rows); the 2026-04-29 *morning*
multi-arch "Probe A" first pass (its own re-run's decision.md: "almost entirely contamination");
the two corrupted `thinking_deepseek_*_baseline` runs in `REBENCHMARK_NEEDED.md`. Disk-hygiene
candidates (~1.2GB superseded embedding blobs under `repl_memory/sessions/`) are an operator
call, not contamination. Autonomous-loop reclamation of the enumerated expirable
classes is governed by §5 *"Evidence retention and reclamation"*; this list is otherwise closed and
confers no authority beyond its own enumeration.

## 7. Quick-reference: what to do when you encounter a number

1. **Era-label it** — `instrument_eras.yaml` (timestamp, scope, boundary).
2. **Apply the verb** — retro-certified → use as claim; demoted-to-prior → hypothesis only, open
   a re-measure ticket if it must gate; retired-view → consult the rebuilt view.
3. **Never edit historical records to "fix" them** — append.
4. **New measurements** — cite a protocol from §2. No protocol → observation, not claim.

## CHANGELOG

- **2026-08-02 (v2.x)** — §5 gains **evidence durability**: evidence for a ratified claim must
  live in-repo under `epyc-inference-research/data/<campaign>/` with hashes and a README;
  scratch paths may not be the citation of record. Closes a gap where the constitution
  required evidence hashes but never required the evidence to survive. Enforced by
  `scripts/validate/check_evidence_durability.py`.


- 2026-07-30 — v2 restructure RATIFIED (operator apply 20260730T103218Z): core + `measurement/protocols/` annex split; metric-scoping section
  added; stale era-table copy replaced by registry pointer; P-GPU-1 placeholder/ratified blocks
  merged. Full delta: `artifacts/operator/measurement-v2-draft/RATIFICATION_LEDGER.md`.
- 2026-07-31 — AMENDMENT: measurement categories `OPTIMUM`/`BASELINE`/`CANDIDATE` added to §3
  claim grammar; promotion-on-production-optimal clause added to §5 Governance, superseding the
  protocol-scoped rule at `measurement/protocols/bench-cpu.md:216-220`; `bench-cpu.md:91-92`
  narrowed so non-production-recipe cells record but do not block. Origin: repeated wasted
  measurement runs from conflating a spec-off BASELINE with a no-draft-path OPTIMUM.

## MI210-SUBSTRATE-CONSTANTS-1 — measured substrate constants (RATIFIED 2026-08-03)

Every roofline denominator this project uses is measured, not assumed. Each traces to a
committed receipt under `epyc-inference-research/data/`.

| Constant | Measured `[M]` | Derived `[D]` | Receipt |
|---|---|---|---|
| Peak fp16/bf16 matrix | **172.2 TFLOPS** | 181.0 | `data/mi210-mfma-peak/20260803T143200Z/` |
| Achievable HBM bandwidth | **1433.3 GB/s** | 1638 (datasheet) | `data/mi210-achievable-bandwidth/20260803T124401Z/` |
| PCIe H2D / D2H | **28.89 / 28.20 GB/s** | 31.5 (Gen4 x16) | `data/mi210-h2d-d2h/20260803T131500Z/` |
| Ridge, measured basis | **120.1 FLOP/byte** | — | derived from the two above |
| Ridge, spec basis | — | 110.5 FLOP/byte | retained for cross-vendor comparison |

`B*` on the measured basis: Q4_K 34 · Q8_0 64 · bf16 120.

**Usage rule (binding).** Use the **measured** basis for headroom and campaign sizing; use the
**spec** basis for cross-vendor comparison; **never mix them, and always state which was used.**
A utilisation quoted without its denominator is not a number. Two failure modes this rule exists
to prevent, both observed in 2026-08: converting our own figures to a measured basis while a
competitor's remain on spec, which makes a gap look smaller without it being smaller; and
dividing a per-OAM FLOPS figure by a per-GCD bandwidth, which is how a vendor knowledge base
published a ridge point off by 2×.

**Grade.** These are substrate constants at OBSERVATION grade. They describe the machine, not a
candidate: they license no promotion, no era row, and no release claim.

## AGGREGATION-SPEEDUP-1 — speedup aggregation (RATIFIED 2026-08-03)

**Rule.** Aggregate per-item speedups as `harmonic_mean({s_i : i correct})`, reported **beside**
`correctness_rate`, never instead of it.

**Forbidden:** a harmonic mean over any set containing failure-clamped sentinel values. Failures are
counted in `correctness_rate`; they are never encoded as a speedup and folded into the aggregate. A
published headline in this literature moved **2.8× on byte-identical outcomes** purely from the choice
of clamp constant — a single number whose value is set by a convention rather than by the data.

**Why harmonic and not geometric.** Harmonic mean punishes slowdowns heavily and nearly ignores large
speedups, which is the asymmetry we want: large wins on minor items should not offset a regression.
Geometric mean is the documented attack surface — `[0.1, 1000]` across two items yields a geometric
mean of 10 while one item regresses, and agents have been shown to perform exactly that optimization.

**SCOPE — this governs speedup and ratio aggregation ONLY.** It does **not** reach the
completion-probability geometric mean used for confidence calibration in the autopilot RLVR path, which
is a different quantity with a different justification. An audit on 2026-08-03 found **zero** sites
applying a geometric mean to speedups, so this rule is **prospective**: it prevents a future choice
rather than correcting a present one. Do not let a future sweep "retire geomean" by grepping the token.


## PAIRED-CI-1 — paired confidence intervals (RATIFIED 2026-08-03)

**Rule.** Paired comparisons report a closed-form paired confidence interval, computed **with the
small-K correction**.

**The small-K correction is mandatory, not advisory.** Without it, relative error is roughly **70% even
at N=2000**, because a `1/(K−1)` per-question bias does not average away as N grows. At the K=3–5 reps
this project typically runs, omitting it makes the interval worthless — worse than reporting none,
because it looks like rigour.

**Do not add bootstrapping.** The empirical-variance z statistic, the bootstrap and the sign test are
proven equivalent for this estimator; resampling machinery would add cost and no information.

**What this closes.** Before this rule, paired comparisons reported point estimates with no interval.
`llm_primitives/stat_tests.py` provides `wilson_interval` (a binomial proportion CI) and **no paired
CI** — so this is a genuine gap, not a restatement.

**SCOPE LIMIT, binding.** The estimator models two noise sources: data and prediction. **This
project’s dominant hazard is a third — environment/machine drift — which pairing does NOT remove**
unless both arms are interleaved within one environment window. The affine drift correction that
handles that third source **is not implemented anywhere in this project as of 2026-08-03**. Therefore:
a paired CI computed under this rule is valid for arms interleaved in one window, and **may not be used
to rank close variants across windows** until the drift correction exists. Adopting this alone is half
the instrument, and the half that is missing is the one that bites hardest here.


## CENSORING-1 — right-censoring and robust aggregation of repeats (RATIFIED 2026-08-03)

**Rule 1 — right-censoring.** For any benchmark with a wall-clock cap, a run that reaches the cap
scores **0**. The censored magnitude is **never imputed, extrapolated, or replaced by the cap value**.
The principle generalises: *make the score’s dependence on the measurement vanish at exactly the point
the measurement stops being informative.*

**Rule 2 — robust aggregation of repeats.** Aggregate R repeated timings with the **Hodges–Lehmann**
estimator (median of pairwise means) rather than the arithmetic mean. Drop-in, no other implication.

**Explicitly NOT adopted: `eff@k` as a scoring function.** It saturates — a caveat derivable from its
own defining equation and not stated in its source: on the hardest level the ceiling is
`α/(α−1) = 2` at `α = 2`, so **a 2× and a 1000× score identically**. It is unusable wherever magnitude
matters, which for kernel and serving work it does.

**BLOCKING PRECONDITION on any harness adopted to implement Rule 1.** The reference implementation in
the literature executes untrusted generated code in bare subprocesses with a documented inability to
kill `try`/`except` infinite loops. On a host shared with live inference servers that is not runnable
as delivered. **Adopt the rule; run it under our own isolation.**


## CONFORMANCE-VECTORS-1 — cross-backend numerical conformance vectors (RATIFIED 2026-08-03)

**Decision.** Cross-backend numerical conformance vectors are adopted as a **first-class instrument**.
Instruments touch the measurement trust boundary, which is why this is a ratified decision rather than
a task.

**What the instrument is.** Committed, edge-weighted test vectors that pin a decoder **bit-exactly**
rather than to a tolerance: each case carries the decoded value **and** its exact bit pattern, weighted
to boundaries and to the step either side of them.

**Two design requirements, both load-bearing.**

1. **Dual contracts per format.** Where a spec behaviour and our implementation behaviour legitimately
   differ, they are recorded as **two separate contracts**, so a backend cannot satisfy one by breaking
   the other. This is what lets a compatibility path be recorded as *documented-divergent* rather than
   as a bug.
2. **VERIFIED vs ASSERTED, per row.** Every row names the test that consumes it, or is marked
   `not yet checked`. A backend is conformant only if a test actually consumes the vectors; anything
   else is an observation from reading source and is marked as such.

**What motivated it.** An audit on 2026-08-03 found **three different answers for the same
quantization edge case across seven backend sites** in our own tree — CPU finite, HIP/Metal/SYCL/Vulkan
/OpenCL +Inf, CUDA ≥12.8 NaN. Nothing had compared them **because nothing ran**.

**Known limitation, recorded at adoption.** Hand-written vectors drift — that is the same failure mode
they exist to document. The `VERIFIED`/`ASSERTED` column is what makes the drift visible rather than
silent.

