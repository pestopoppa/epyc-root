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

### P-GPU-1 — GPU canonical (DEFERRED — hardware not acquired, all GPU work HW-GATED)
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
