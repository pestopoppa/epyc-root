# E5 W0 — NUMA x Batch Interaction Sweep: Preliminary (Scout) Results

> ## ⚠️ OBSERVATION-GRADE ONLY — DOES NOT GATE ANY DECISION
>
> W0 ran with `--allow-host-health-warning` because host uptime was **20 days** at run time
> (2026-07-23), and the harness refuses **decision-grade** P-BENCH-3 runs past one week of
> uptime. W0 is therefore **scout-by-design**, not decision-grade. Per `MEASUREMENT.md`, these
> numbers may generate hypotheses but **must not gate keep / revert / deploy / promote / buy /
> close decisions**. Decision-grade confirmation is W1-W4, currently blocked on a host reboot.

---

## 1. What E5 W0 is

The NUMA x batch 2D interaction sweep — the never-before-measured cross between NUMA
placement (C1 whole-machine, C1b second-node, C2, C3 quarters) and `-np` request batching.
Previously, NUMA-split and `-np` had only ever been measured **separately**. W0 is the scout
wave over this 2D grid; W1-W4 are the pending decision-grade confirmation waves, one per model
group.

69/69 cells ran clean across 4 model groups (2,967 saved offline-scored responses total).

---

## 2. Results grids (aggregate throughput, tasks/h, raw offline_scores)

Bold = aggregate-optimal cell for that model group. All numbers below were cross-checked
against the actual run-dir `summary.md` files, not just the handoff — no discrepancies found.

### qwen36_q8_0 (MoE-35B) — `e5-w0-qwen36-nothink-20260723T194901Z`

| Placement | np1 | np2 | np4 | np8 | np16 | np32 |
|---|---|---|---|---|---|---|
| C1 (whole-machine) | 1359 | 1505 | 1549 | 1610 | 1734 (kvu) | 1528 |
| C1b (second-node)  | 988  | 1120 | 1109 | 1198 | 1154 | — |
| C2 | 1540 | 1729 | 1826 | 1718 | 1707 | — |
| C3 (quarters) | 1682 | 1909 | **2028 (optimal)** | 1774 | — | — |

### gemma4_26b_a4b_q4km_mtp — `e5-w0-gemma-20260723T203422Z`

| Placement | np1 | np2 | np4 | np8 |
|---|---|---|---|---|
| C1 (whole-machine) | 1515 | 2018 | 2127 | 2475 (np16: 2854, np32: 2879) |
| C3 (quarters) | 3246 | 4129 | 4448 | **5076 (optimal)** |

C3-np8 vs C1-np32 iso-T=32: 5076.47 / 2854.45 = **1.78x**. **All 10 cells are quality-invalid
— see §4, W2.** Speed numbers above are retained only as scout throughput signal.

### qwen36_27b_q8 (dense) — `e5-w0-dense-20260723T204720Z`

| Placement | np1 | np2 | np4 | np8 | np16 | np32 |
|---|---|---|---|---|---|---|
| C1 full-machine | 574 | 808 | 849 | 611 | 781 | 810 |
| C1 half0 | 751 | — | — | 814 | — | — |
| C1b (second-node) | 836 | 939 | 965 | 1009 | 984 | — |
| C2 | 819 | 1009 | 1085 | 1027 | 926 | — |
| C3 (quarters) | 1225 | **1415 (optimal)** | 1407 | 1334 | — | — |

Paired probes: half0 beats full-machine at both K=1 (751 vs 574) and K=8 (814 vs 611) — the
dense C1 shape question is **RESOLVED**.

### qwen3_next_80b — `e5-w0-80b-20260723T221055Z`

| Placement | np1 | np2 | np4 | np8 | np16 | np32 |
|---|---|---|---|---|---|---|
| C1 (whole-machine) | 1162 | 1434 | 1550 | 1669 | 1700 | 1556 |
| C1b (second-node)  | 1377 | 1659 | 1886 | 2013 | 1905 | — |
| C3 (quarters) | 1897 | 2275 | **2520 (optimal)** | 2386 | — | — |

---

## 3. Cross-model pattern

- **Held for every model**: C3 (quarters) is aggregate-throughput-optimal for all four groups
  (qwen36 MoE-35B, gemma, dense, 80B) — the quarter-split beats whole-machine and second-node
  placements everywhere tested.
- **Model-dependent**: C1b (second-node) vs C1 (single-node whole-machine) flips by
  architecture. It **loses** for the MoE-35B (qwen36: np4 1109 vs 1549) but **wins** for dense
  (np4: 965 vs 849) and 80B (np4: 1886 vs 1550).

---

## 4. Per-wave prune status (W1-W4), from `stage_b_prune_plan.json`

| Wave | Model | Prune decision | Reason |
|---|---|---|---|
| **W1** | qwen36_q8_0 (MoE-35B) | Prunes only `C1b-{np4,np8,np16}` (throughput-only) | W0 whole-machine C3 wins by 44.78% / 44.77% / 34.97% at T=8/16/32; C1b/C1 ratio is 0.598 at K=4 and 0.463 at K=8, reproducing the documented half-pair collapse. |
| **W2** | gemma4_26b_a4b | **Full grid retained** | Retain full-vs-quarter family for clean 256-token confirmation despite W0 C3 wins of 36.24%-43.77%. **QUALITY-INVALID for interpretation**: original capture stored reasoning text without an answer channel — all 430/430 offline_scores rows are unrecoverable parse failures, no raw SSE ledger survives. RE-ATTRIBUTED 2026-07-29 (research `5d6a17f2`): the actual budget sink was **reasoning mode ON** — the harness emitted no `--reasoning` flag, so gemma4 ran at llama-server's `auto` default while both registries record `reasoning: 'off'`. The fail-close capture gate (`efd0980c`) **detects** this, it does not **prevent** it; a focused post-fix capture smoke test is a precondition before any decision-grade W2 run. |
| **W3** | qwen36_27b_q8 (dense) | **Full grid retained** | Dense C1 shape is already resolved (half0). W0's C1b@16 vs C3@8 comparison used mixed metric bases, so no additional prune is sound (flagged `[MIXED METRIC BASIS — caveated]` in the run summary). |
| **W4** | qwen3_next_80b | **Full grid retained** | Keep the ingest whole-machine family: W0 favors C3 by 17.44%-26.39%, but the 256-token clean confirmation remains the operator-scheduled W4 purpose. High-K `raw_fallback` rows are demoted from decision-grade use (per the handoff's W0-summarizer entry; not separately itemized in the prune-plan JSON). |

---

## 5. What W0 cannot tell us

- **Correctness/quality at scale**: W0 used a 64-token scout cap and (for gemma) captured
  reasoning-only output with no answer channel — quality is either capped, invalid (gemma), or
  simply unconfirmed at the 256-token production length. W1-W4 exist to re-run at production
  token budgets with the fail-close capture gate in place.
- **Decision-grade throughput**: every number above was collected on a host at 20 days uptime
  under an explicit health-warning override. None of it can be used to actually deploy a
  placement/np change — W1-W4 (post-reboot, within the 1-week freshness window) is the
  confirmation gate.
- **Dense/80B mixed-metric-basis cells** (W3's C1b@16 vs C3@8): W0's own comparison there used
  inconsistent metric bases, so no conclusion is drawn from it; W3 must re-measure cleanly.
- **Gemma correctness signal, period**: W2 will be the first wave with any usable quality
  ledger for this model group at all.

---

## 6. Provenance

- **Handoff**: `handoffs/active/batched-decode-measurement.md` (E5 section, "E5 W0", "W0
  summarizer", "Stage-B prune" entries, dated 2026-07-28).
- **Run dirs** (`/mnt/raid0/llm/epyc-inference-research/data/batched_decode/`):
  - `e5-w0-qwen36-nothink-20260723T194901Z` (canonical qwen36 source; 903 offline_scores rows)
  - `e5-w0-gemma-20260723T203422Z` (430 rows, all parse-failed — see §4)
  - `e5-w0-dense-20260723T204720Z` (989 rows)
  - `e5-w0-80b-20260723T221055Z` (645 rows)
  - Sum = 2,967 rows, matching the handoff's total exactly.
  - Two additional qwen36 dirs exist on disk (`e5-w0-qwen36-20260723T190338Z`,
    `e5-w0-qwen36-rerun1-20260723T191759Z`) but are not the canonical `W0_qwen` source in the
    prune plan — the `-nothink` dir is.
- **Prune plan**: `data/batched_decode/e5_pre_reboot_20260728/stage_b_prune_plan.json` in the
  research repo. SHA-256 `cabd10bd0fe52ed04ca28e314ad0ab8d505de9e5db571115d16c48d0832daee8` —
  confirmed matching the handoff's pinned value.
  - Superseded predecessor hash recorded in-file:
    `06b0abb2ca7abaf004ce56658a8c3753ea719ebdc4f1b50bec65a015954d4f8b` (predecessor file does not
    survive on disk; not independently re-verifiable).
- **Commits** (research repo, `/mnt/raid0/llm/epyc-inference-research`):
  - `efd0980c` — checkpoint E5 W0 scoring: adds `offline_scores.jsonl` + `rules.json` +
    `summary.md` across all 4 run dirs, adds `scripts/benchmark/e5_w0_offline_score.py`, and
    the fail-close capture gate.
  - `d61e4e8c` — provenance-repair edit to `stage_b_prune_plan.json` (+2/-1 lines): corrects a
    stale limitation that had wrongly claimed the offline_scores producer was absent.
- **Raw data location**: per-cell request/response captures and `offline_scores.jsonl` live
  under each run dir above; `summary.md` in each run dir carries the throughput grid quoted in
  §2.
- **Discrepancies found between handoff and run-dir data**: none material — every headline
  number, the prune-plan SHA-256, and the cross-model pattern claims in the handoff were
  independently verified against the run-dir `summary.md`/`stage_b_prune_plan.json` files and
  matched exactly.
- **Handoff references not locatable on disk**: none — every run dir, file, and commit cited
  by the handoff was found and confirmed.
