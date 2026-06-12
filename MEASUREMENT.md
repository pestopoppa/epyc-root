<!-- Adopted 2026-06-12 from the Fable 5 architecture review (handoffs/active/fable5-proposed-MEASUREMENT.md).
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
- Published constants per core version: quantum (3/n), single-trial MDE (2 flips), per-suite resolution (3/n_suite), known-dead items (must be zero after Phase 2.0 repair).
- Decision rule: sequential e-process per `fable5-findings-01c` (`policy_version` cited in every verdict). Single-trial deltas below MDE are *never* decisions.
- **Anti-gaming**: question selection, seeds, and n are evaluator-side constants; rotating audit block correlation is published with the verdict.

### P-QUAL-PROMO — Promotion / generalization quality
Fresh stratified draw, **n ≥ 200**, qids unseen within 60 days, broken-suite items excluded by the suite-health table, runs only on `confirmed` candidates; its e-value multiplies the candidate's running E (combined threshold E ≥ 100 for baseline changes).

### P-AB-1 — Orchestrator A/B (routing, prompts, features)
Paired where possible (same questions both arms); **N ≥ 100/arm for production-role decisions** (the X-MAS lesson: a 20pp effect at N=25 collapsed to 4pp at N=100); every failure classified by reason (backend outage / timeout / empty / genuine — `feedback_classify_eval_failures_by_reason`) with infra-failure rate reported next to the effect; flag-state attestation across all workers recorded in the run header (the 1-of-6 worker lesson).

### P-SPEED-OBJ — The throughput objective (autopilot Pareto axis)
Axis = **task_rate** (questions / eval-wall-hour) per findings-05; t/s retained as host-health telemetry only; `speed_metric_mode`/`protocol_id` journaled; noise reference CV ≈ 9% → all rate claims via the non-inferiority/improvement e-process, never single-trial.

### P-GPU-1 — GPU canonical (PLACEHOLDER — **must be ratified before first MI210 number**; hardware not acquired, all GPU work HW-GATED)
Required fields when written: device state capture (rocm-smi clocks/power/temp before+after), warm-up policy, per-GCD memory residency check, host-side interference policy (CPU stack quiesced or declared), reps as P-BENCH-1, and a vendor-number rule: *no vendor-reported figure may appear in a decision row — local reproduction only* (`agentic-rocm-kernel-authoring.md` already flags gfx90a compile≠perf).

## 2. Claim grammar & examples
- ✅ `frontdoor decode 27.06 t/s [P-BENCH-2, n=5, 2026-04-26, attest a3f2]`
- ✅ `config 9bd1 confirmed +2q on core_v2 [P-QUAL-T1/seq-v1, E=24.3, k=5, 2026-06-20]`
- ❌ `+17% with EP flags` (no protocol, no reps — this exact claim later collapsed to +1.6% under P-BENCH-1)
- Metric direction MUST be stated where ambiguous (`higher-better`/`lower-better`) — confirmed-direction errors have burned debugging time before (CLAUDE.md §Debugging).
- Comparisons only within a protocol + instrument version. Cross-protocol comparisons are analysis, labeled as such.

## 3. Standing noise & resolution table (update on instrument change)
| Quantity | Value | Source |
|---|---|---|
| T1 quality quantum / MDE | 0.0698 / 2 flips (≈4.7pp) | findings-01 §1 |
| Per-suite quantum @2q | 1.5 (50pp) | eval_tower per_suite_counts |
| Speed/rate noise | CV ≈ 9.1%, outliers to −27% under host drift | journal 714–776 |
| Host-throttle signature | multi-day uptime −60%+; drop_caches+rewarm restores | `feedback_host_throttle_check` |
| Practical BW anchor | 460 GB/s aggregate; 4.79 GB/s/thread | roofline findings.md |

## 4. Governance
- Changes to this file: PR-reviewed amendment with a one-line CHANGELOG; protocols are append-or-version, never silently edited.
- Validators: `check_claims_grammar.sh` (warn-mode month 1) over new handoff/index diffs; journal rows carry `protocol_id`; ATTESTATION artifact (findings-04 §B) is the `attest <id>` referent.
- The eval trust boundary (program.md) extends to this file: the autopilot may **read** it, never edit it.

## 5. Retroactivity & reconciliation (what happens to every number collected before this file existed)

**Scope first**: the claim grammar governs **decision-gating claims** — numbers that justify keep/revert, deploy, promote, buy, or close decisions. It does NOT govern training data (episodic memories, item-difficulty priors) or narrative history (progress logs, archived handoffs). Mislabeling those as "claims to be purged" would be the same category error this project keeps paying for in the other direction.

**The prime directive**: *never destroy primary records; demote, label, or re-derive interpretations.* Three verbs, applied per corpus:
- **retro-certify** — the number was provably produced by a now-named protocol (command/env/reps recorded). It gets `protocol_id: <P> (retro)` and full claim status. No re-measurement.
- **demote-to-prior** — real data from an unknown or known-flawed instrument. Keeps its place as evidence for *hypothesis formation* and item-difficulty priors; **cannot gate a decision**; a decision that today rests only on demoted numbers gets a re-measure ticket (priority = consumer impact).
- **retire-view** — derived artifacts (frontiers, baselines, dashboards) are rebuilt under the current policy/era; the old view is archived read-only, never edited in place.
Anything known-contaminated keeps its supersession tag (the existing `bug_corrupted_by` machinery) — tagged history, not deletion.

**The instrument-era table is the load-bearing artifact** — `orchestration/instrument_eras.yaml`, append-only, consumed by every replay/dashboard/verdict tool:
| era id | boundary | what changed | reconciliation |
|---|---|---|---|
| E0 → E1 | 2026-04-26 | canonical bench protocol established (CPU20) | pre-canonical CPU bench claims **demoted-to-prior** (precedent: EP +17%→+1.6% on re-measurement — the demotion is empirically justified, not bureaucratic) |
| E1 → E2 | 2026-06-02 | speed objective de-double-counted | pre-E2 speed **rescaled at read time** (×0.5 deinflate + `pareto_epoch_ts` — ALREADY IMPLEMENTED; this file just names it) |
| E2 → E3 | 2026-06-04 | tool sentinels live; T1 n 38→43 | cross-n frontier entries split per era; comparisons within-era only |
| E3 → E4 | (instrument repair lands) | dead items fixed/excised; core_v2; task_rate axis; sequential verdicts | **retire-view**: T1 frontier/baselines restart fresh (empty-frontier bootstrap exists); E≤3 frontier archived as historical view; quality numbers NOT rescaled across E3→E4 (different ceiling, different items — rescaling would fabricate precision) |
| (any) | episodic reset 2026-05-25 | routing memory wiped | pre-reset learned-routing claims demoted; post-reset memories are training data, out of claim scope |

**Per-corpus ruling** (counts from the 2026-06-12 reconciliation inventory — full report in `fable5-findings-appendix-evidence-reports.md`):
1. **Bench results** (`data/cpu_optimization/`: 65 dated dirs, 9 pre-/56 post-canonical) — **48/56 post-04-26 dirs embed exact command lines + env → retro-certify** by citing the dir doc as protocol witness. The 8 doc-less post dirs (nps4-restore, cpu2-prefetch, cpu2-q6k, numa-mirror-phase0a, clean-host-verification, cpu4-phase0, moe-dynamic-expert, numa-parallel-ceiling) + all 9 pre-canonical dirs + the ~30 March-era trees (numa_sweeps, spec_param_sweep, …) → **demote-to-prior** (their provenance certifies to a superseded protocol that empirically collapsed on re-measurement).
2. **Autopilot journal** (current segment 656 rows; 613 era-labelable) — rows are immutable facts; never trashed, never rescaled in place. **Era keys, exactly**: `timestamp` vs `pareto_epoch_ts`=2026-06-01T19:20:16Z for the speed fix (261 rows before / 395 after — ⚠️ `speed_metric_mode` is a FALSE FRIEND: identical `aggregate_batch_tps` on both sides; never key on it); tool-era by *presence* of the `tool_use` key in `per_suite_quality` (absent in all 364 pre-cutover rows); instrument-n by `details.total` — and note the n=38→43 boundary is **2026-06-05T13:07 (trial 652)**, not the 06-04 cutover. Rotated/backup segments (pre-05-26, no era fields) → leave-as-history, timestamp-only.
3. **Pareto archive / baselines** — `all_entries` (250) and frontiers carry per-entry timestamps + tier + fingerprint → retro-certify with era stamps; **`hv_history_by_tier` (148 points) has NO timestamps and pre-epoch points were computed on inflated speed → retire-view, recompute from era-labeled all_entries**. Frontier/baselines restart fresh at E4.
4. **Episodic/routing memory (287,682 rows, ALL post-dating the 05-25 reset)** — **demote-to-prior wholesale; out of claim scope** (training data). Every row was trained under flawed-instrument eras (inflated speed until 06-01, no tool signal until 06-04) and stores only binary outcome + final Q with **no reward decomposition** — selective correction is impossible, replay infeasible; the 0.99/day decay + forward-corrected rewards are the remedy. ⚠️ Live anomaly flagged during inventory: `embeddings.faiss` observed **0 bytes** (mtime 2026-06-12 14:54, lock present) against 287K db rows — verify whether mid-rebuild or broken; KNN routing depends on it.
5. **Model registries** (lean: 12 decision-gating numerics; research: ~37) — all carry free-text date/protocol *comments* (the only witness — ⚠️ a YAML reformat would destroy them). Convert comments to structured `measured: {date, protocol, value}` fields via the descriptor compiler; canonical-era values (frontdoor 24.3 May-4, architect 12.19 Probe-B) retro-certify; sweep-era (2026-03-21: worker 39.1@48t, coder 10.8) and 2026-01 values demote + re-measure queue ordered by consumer impact (q_scorer cost model first).
6. **Handoff/index claims** — **732 numeric performance claims across 71 active files** (measured). History stays as written; the grammar validator applies to **new diffs only**; the 5+ index files are retire-view (regenerated citing protocols); rows ported into the new master index cite a protocol or carry `claim:unverified`.
7. **Per-question eval corpora** — `seeding_diagnostics.jsonl` (3,187 rows, 100% with scoring_method + config; 2026-02/03) is the strongest era-labeled difficulty-prior corpus; the 3way set (1,818 rows, rich per-role results, **zero scoring_method fields** — scorer-era labeled externally by date, all pre-comma-fix) → both demote-to-prior as item-difficulty priors feeding core_v2 selection.
8. **Strategy store / STM / planner narrative** — governed by findings-01 Phase 4 (provenance or regeneration), which subsumes reconciliation: a narrative citing a demoted number fails its provenance check and is regenerated.
9. **Agent memory** (49 of 108 memory files carry numbers) — pointers, not claims; several already self-supersede; new sessions re-verify per the existing memory-recall caveat.

**Known limits (hardest cases, accepted)**: (a) historical journal rows lack per-question IDs, so dead-question effects on old quality numbers cannot be retro-decomposed — old T1 quality is era-comparable only within (n, era); the per-question ledger starts clean at E4. (b) episodic Q-values cannot be selectively corrected (no decomposition stored) — wholesale demotion is the only honest verb.

**What future agent sessions do differently** (the one paragraph to lift into CLAUDE.md on adoption): *when you encounter a historical number, first era-label it (instrument_eras.yaml), then check its verb: retro-certified → use; demoted → treat as hypothesis, do not gate, open a re-measure ticket if it must gate; retired-view → consult the era-appropriate rebuilt view. Never edit historical records to "fix" them — append.*

**Explicit dump list** (the only true deletions — everything else is demote/label/archive):
- `autopilot_journal.{jsonl,tsv}.run3-poisoned` (104 rows, already named poisoned) and `archived_backups/autopilot_journal.jsonl.broken-run-backup` (6 rows).
- The 2026-04-29 *morning* multi-arch "Probe A" first-pass results (the canonical re-run's own decision.md calls them "almost entirely contamination"); keep the re-run.
- The two corrupted `thinking_deepseek_*_baseline` runs already listed in `benchmarks/results/REBENCHMARK_NEEDED.md` (precedent: 439 ×28-inflated spec_draft files were deleted 2026-01-15).
- Disk-hygiene candidates (operator call, not contamination): ~1.2GB of superseded embedding blobs under `repl_memory/sessions/` (reembedded.npz 602MB, pre-repair embeddings 227MB, pre-reset db backups).
Everything else — including all 9.9/2.9-era supersession-tagged rows and dated backups — is kept.
