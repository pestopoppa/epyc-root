> **SUPERSEDED AND NON-AUTHORITATIVE — 2026-07-30.**
>
> This file is a stale draft (last written 2026-07-29 16:39Z) that predates the W2
> group entirely. It was never the local authority. **Do not read it as the record.**
>
> Two separate reasons it is void:
> 1. **It is a partial snapshot.** The auditor flagged the divergence on 2026-07-29
>    (`msg-20260729T190401Z-129-auditor`): it is missing the headline, the Gemma
>    quality ledger and the whole W2 group.
> 2. **Its subject matter is retracted.** On 2026-07-30 the entire E5 Stage-B
>    throughput record was suspended — the placement shapes under test inherited a
>    NUMA wiring defect, so 27 of 31 cells are confounded. See
>    [`handoffs/active/numa-placement-defect-20260730.md`](../../handoffs/active/numa-placement-defect-20260730.md).
>
> **The authoritative record** is the sibling `e5_w0_preliminary_results.html` in this
> directory. A hosted presentation copy existed historically, but it is not a project source,
> locator, or update target. The local HTML was rewritten from scratch on 2026-07-30 as the NUMA
> decision package.
>
> Retained, not deleted, because historical records in this repo are append-only.

# E5 — NUMA × Batch Interaction Sweep: Results

*(File name deliberately unchanged from the W0 preliminary release. The sibling local HTML is the
E5 results artifact; this markdown file is retained only as a superseded historical draft.)*

---

> # ⛔ ⛔ DRAFT — NOT FOR PUBLICATION ⛔ ⛔
>
> **This revision is STAGED, not publishable.** The Stage-B campaign was still running when it was
> written, so every live figure below is a placeholder carrying the literal token `TODO-FILL`.
>
> **Historical local-update gate — all five had to be true before rendering a replacement:**
>
> 1. `grep -c TODO-FILL artifacts/operator/e5_w0_preliminary_results.md` returns **0**.
> 2. This whole `⛔ DRAFT` block is **deleted**.
> 3. Every Stage-B number quoted below has been read out of the final run dirs' `cells.jsonl` /
>    `summary.md` — **not** from a partial in-flight run, and **not** from the R2/R4 summarizer
>    peak (see §8.2 — that peak is invalid by construction).
> 4. The era-label question in §8.3 is resolved (the run manifests stamp a **stale** era).
> 5. Replace the authoritative local HTML in place and verify it from its local content hash.
>    Do not treat any hosted presentation copy as an input or update target.
>
> The `.html` render alongside this file is still the **old W0-only** version. It has not been
> touched. Regenerate it from this source at publication time.

---

> ## Grade banner — read this before quoting any number
>
> This artifact now carries **two grades side by side**, and they are not interchangeable:
>
> | Wave | Grade | Why |
> |---|---|---|
> | **W0 (scout)** | **OBSERVATION-GRADE — gates nothing** | Ran 2026-07-23 under `--allow-host-health-warning` at 20 days host uptime, on the **v7** kernel. Retained unedited, never overwritten. |
> | **Stage-B W1 / W4** | **DECISION-GRADE** for cells reporting `decision_grade=true` | Post-reboot, zero host-health warnings, full claim grammar per `MEASUREMENT.md`. |
> | **Stage-B W1 / W4, T=32 rungs** | **OBSERVATION-ONLY** | `empty_trimmed_window` instrument limitation — see §8.1. Recoverable offline; not lost. |
> | **Stage-B W2 (gemma4)** | **THROUGHPUT ONLY; QUALITY-INVALID** | The focused post-fix capture smoke has **not** passed. See §7. |
> | **W3 (dense control)** | **NOT RUN — dropped by operator scope decision** | Not a failure, not a loss. See §3. |
>
> Per `MEASUREMENT.md`, an observation-grade number may generate hypotheses but **must not gate
> keep / revert / deploy / promote / buy / close decisions**. A decision-grade number may — but
> only when quoted with its full claim grammar (§5) and only for cells that individually report
> `decision_grade=true`.

---

## 1. What E5 is

The NUMA × batch 2D interaction sweep — the never-before-measured cross between NUMA placement
(C1 whole-machine, C1b second-node, C2 half-machine pair, C3 quarters) and `-np` request batching.
Before E5, NUMA-split and `-np` had only ever been measured **separately**.

It answers one provisioning question directly: **does a single full-machine high-`-np` server beat
quarter-batched servers?** Two reads are pre-registered — iso-concurrency (hold total in-flight
T = N×K fixed, vary the split) and unconstrained peak-aggregate (N,K).

- **W0** is the scout wave over the grid (2026-07-23/24, v7 kernel, 20-day uptime).
- **Stage-B (W1/W2/W4)** is the decision-grade confirmation wave, post-reboot, on the v8 kernel,
  at the production 256-token budget.

---

## 2. Host state during Stage-B — quiesced, not production

**Stated explicitly so these numbers are not misread as production throughput.**

Stage-B decision-grade measurement is mutually exclusive with any other llama-server on the host:
the harness's health gate counts existing llama processes **unfiltered**, at run start *and*
per-cell mid-run. So for the duration of the campaign the host was deliberately emptied:

- **AutoPilot: DOWN.** No trial traffic, no eval fan-out, no frontier work.
- **Serving stack: DOWN.** Zero llama-server processes outside the harness's own cells.
- Host rebooted 2026-07-29 ~13:42Z; uptime well inside the P-BENCH decision-grade freshness window.
- No `--allow-host-health-warning`, no `--skip-clean-check` (either would force
  `decision_grade=false` for the whole run).

**What this means for the reader:** every Stage-B figure is a **quiesced-host ceiling**. It is the
correct basis for comparing *placements against each other* — that comparison is what E5 exists to
make, and it is clean. It is **not** a forecast of what any of these shapes will deliver while the
production stack, AutoPilot, embedders and the GPU tenant share the machine. Cross-role contention
is placement-blind and is measured elsewhere; do not add these numbers to a production capacity
model without that adjustment.

---

## 3. Scope — the sweep covered THREE model groups; the fourth was dropped, not failed

Stage-B ran **31 of the 45 pruned cells, across three model groups**:

| Wave | Model group | Cells | Status |
|---|---|---|---|
| **W1** | `qwen36_q8_0` (frontdoor MoE-35B) | 11 | Ran — see §5 |
| **W2** | `gemma4_26b_a4b_q4km_mtp` (worker_general) | 8 | Ran — throughput only, quality-invalid (§7) |
| **W4** | `qwen3_next_80b` (ingest) | 12 | Ran — see §5 |
| **W3** | `qwen36_27b_q8` (dense control) | 14 | **NOT RUN — dropped by operator decision** |

### Why W3 was dropped

**Operator decision, 2026-07-29:** *"27b_q8 is scheduled to run residently on the GPU."*

`qwen36_27b_q8` is planned for promotion as a **GPU-resident tenant**. A CPU-side NUMA × batch
sweep of that model would therefore measure a configuration that **will never serve** — the CPU
dense-control arm is superseded for the CPU plane.

This is a **scope change, not a result change, and not a deferral**:

- W3 did **not** fail. No W3 cell errored, wedged, or was demoted.
- W3 was **not** lost. Its 14 pruned cells were simply never launched; the campaign driver was
  replaced mid-flight before it could auto-launch them.
- W3 is **not** blocked waiting on anything. There is nothing to unblock.
- The **W0 W3 scout data already recorded is retained unedited** below (§6), per the
  append-never-edit rule. The dense C1 shape question it resolved stays resolved.

Durable record: coordinator message `msg-20260729T155710Z-45`, operator-instructed in-pane;
handoff `handoffs/active/batched-decode-measurement.md`, E5 section, W3 entry dated 2026-07-29.

---

## 4. Headline read

> ‼ **TODO-FILL** ‼ — one paragraph, written only after the final run dirs are summarized.
> It must answer the pre-registered question in plain language: *for each of the three model
> groups, does one full-machine high-`-np` server beat quarter-batched servers, and where is the
> iso-T crossover K\*?*
>
> **Constraints on what may be written here:**
> - Quote **R1** (iso-T crossover) — R1 guards per-pair against basis mixing and reports a winner
>   only on a consistent basis. R1 is the sound rule.
> - Do **NOT** quote the R2 Pareto peak or the R4 `per_shape_np_optimum` as a headline. Both are
>   invalid by basis-mixing in the current summarizer (§8.2).
> - Do **NOT** build the headline on a T=32 rung (§8.1) — those cells are observation-only.
> - If the sound, decision-grade evidence does not reach the top rung of a pre-registered family,
>   **say so** rather than substituting an observation-grade cell.

---

## 5. Stage-B decision-grade results

**Basis rule for every table in this section:** aggregate throughput is reported on the **trimmed
steady-state basis** (`tasks_per_hour_trimmed`). Where a cell has no trimmed value, the table cell
reads `n/a (obs-only)` and a footnote gives the reason — it does **not** silently fall back to
`tasks_per_hour_raw`. Raw and trimmed are different instruments and are never mixed inside one
comparison (this is exactly the defect described in §8.2).

### 5.1 Claim grammar

Per `MEASUREMENT.md`: *a claim = (metric, protocol-id, n/reps, date, host-attestation ref).*

| Field | Value |
|---|---|
| **Metric** | Aggregate throughput `tasks_per_hour_trimmed` (steady-state basis) **and** per-stream latency p50 / p95 ms — reported per (placement, `-np`) cell, as P-BENCH-3 requires. |
| **Protocol-id** | `P-BENCH-3` (batched/slot decode) |
| **n / reps** | 43 pinned prompts per cell (`prompt_batch.selection="pinned_qids"`, 4096-char fail-closed cap), closed-loop across N instances × K streams; **1 pass per cell**. Per-wave confirmation: ‼ **TODO-FILL** ‼ (read `success_count` / `total_count` out of each final `cells.jsonl`). |
| **Date** | ‼ **TODO-FILL** ‼ (per-wave run start/end, UTC) |
| **Host-attestation ref** | ‼ **TODO-FILL** ‼ — `<run-dir>/manifest.json → attestation`, SHA-256 ‼ **TODO-FILL** ‼ per run dir. Attestation records host `Beelzebub`, kernel `6.14.0-37-generic`, llama-server binary path + `binary_version`, `GGML_IQK`, `kv_unified` per cell, and `existing_llama_processes` (empty). |
| **Kernel / binary** | `production-consolidated-v8` @ `67a433bf45a8a091d83b4ea0b32ff0735fd51800`, `llama-server` version **10107 (67a433bf4)**. Confirm per run: ‼ **TODO-FILL** ‼ |
| **Instrument era** | ‼ **TODO-FILL** ‼ — **do not copy the era string out of the run manifest without reading §8.3 first; it is stale.** |
| **Sampling regime** | Production temp 0.3 / seed 42 on every decision cell (operator-decided 2026-07-23). Temp-0 exists only in the five `-e1parity` twin cells, which carry `decision_grade_intent=false` and are excluded from R1/R2/R4. |
| **Launch pins** | `--device none` / `--device-draft none` (the v8 binary is HIP-capable; without the pin a CPU cell could silently offload draft work to the MI210), `-c` = 2048×K floored at 8192, `n_predict` 256, production spec-dec. |

### 5.2 W1 — `qwen36_q8_0` (frontdoor MoE-35B), 11 cells

Aggregate tasks/hour, trimmed steady-state basis. Bold = decision-grade optimum.

| Placement | np1 | np2 | np4 | np8 | np16 | np32 |
|---|---|---|---|---|---|---|
| C1 (whole-machine) | TODO-FILL | TODO-FILL | TODO-FILL | TODO-FILL | TODO-FILL | TODO-FILL *(obs-only, §8.1)* |
| C2 (half-machine pair) | TODO-FILL | TODO-FILL | TODO-FILL | TODO-FILL | TODO-FILL *(obs-only, §8.1)* | — |
| C3 (quarters) | TODO-FILL | TODO-FILL | TODO-FILL | TODO-FILL *(obs-only, §8.1)* | — | — |
| C1b (second-node) | *pruned* | *pruned* | *pruned* | *pruned* | *pruned* | — |

*C1b `np4/np8/np16` were pruned pre-registration on W0 evidence (throughput-only prune; W0
whole-machine C3 won by 44.78% / 44.77% / 34.97% at T=8/16/32, and the C1b/C1 ratio was 0.598 at
K=4 / 0.463 at K=8, reproducing the documented half-pair collapse).*

**Per-stream latency (P-BENCH-3 requires this reported alongside throughput):**

| Cell | p50 ms | p95 ms | TTFT p50 ms | TTFT p95 ms |
|---|---|---|---|---|
| ‼ **TODO-FILL** ‼ — one row per decision-grade cell | | | | |

**Pre-registered decision families for W1:**

| Family | Rungs | Verdict |
|---|---|---|
| Half-machine mechanism `{C1@T vs C2@T/2}` | T = 2, 4, 8, 16, **32** | ‼ **TODO-FILL** ‼ — R1 per-pair, consistent basis only. The **T=32 rung is observation-only** (§8.1); state that explicitly rather than reporting the family as fully resolved. |
| Quarter family `{C1b@K vs C3@K/2}` | T = 2, 4, 8, **16** | ‼ **TODO-FILL** ‼ (C1b rungs partly pruned — say which rungs actually carry evidence) |

**Cells demoted from decision-grade, with reason:** ‼ **TODO-FILL** ‼ — enumerate every cell with
`decision_grade=false`, quoting its `decision_grade_blockers` verbatim. Do not omit them; a silently
missing cell reads as a cell that was never run.

### 5.3 W4 — `qwen3_next_80b` (ingest), 12 cells

| Placement | np1 | np2 | np4 | np8 | np16 | np32 |
|---|---|---|---|---|---|---|
| C1 (whole-machine) | TODO-FILL | TODO-FILL | TODO-FILL | TODO-FILL | TODO-FILL | TODO-FILL *(obs-only, §8.1)* |
| C1b (second-node) | TODO-FILL | TODO-FILL | TODO-FILL | TODO-FILL | TODO-FILL *(obs-only, §8.1)* | — |
| C3 (quarters) | TODO-FILL | TODO-FILL | TODO-FILL | TODO-FILL *(obs-only, §8.1)* | — | — |

**Per-stream latency:** ‼ **TODO-FILL** ‼ (same shape as §5.2)

**Verdict on the ingest whole-machine family:** ‼ **TODO-FILL** ‼

**Cells demoted from decision-grade, with reason:** ‼ **TODO-FILL** ‼

### 5.4 W2 — `gemma4_26b_a4b_q4km_mtp` (worker_general), 8 cells — THROUGHPUT ONLY

| Placement | np1 | np2 | np4 | np8 | np16 | np32 |
|---|---|---|---|---|---|---|
| C1 (whole-machine) | TODO-FILL | TODO-FILL | TODO-FILL | TODO-FILL | TODO-FILL | TODO-FILL *(obs-only, §8.1)* |
| C3 (quarters) | TODO-FILL | TODO-FILL | TODO-FILL | TODO-FILL *(obs-only, §8.1)* | — | — |

**⚠ These throughput figures may not be paired with any correctness claim.** See §7 — the W2
quality ledger is invalid and stays invalid until the focused post-fix capture smoke passes.
Speed without a paired correctness check is not a serving decision; per project policy, speed
numbers are only quotable next to a correctness/garbage check.

---

## 6. W0 scout figures — RETAINED, era-labelled, unedited

Per `MEASUREMENT.md`, historical numbers are **era-labelled and appended, never edited to "fix"
them**. Everything in this section is the original W0 release text, preserved so scout-vs-confirmed
drift stays visible.

**W0 era label — read before comparing to §5:**

| | W0 (scout) | Stage-B (§5) |
|---|---|---|
| Date | 2026-07-23/24 | 2026-07-29 |
| Kernel | `production-consolidated-v7` @ `6ad45fa3f`, binary **10098** | `production-consolidated-v8` @ `67a433bf4`, binary **10107** |
| Host uptime | 20 days (health-warning override) | post-reboot, inside freshness window |
| Token budget | 64-token scout cap | 256-token production budget |
| Grade | observation-grade | decision-grade (except as noted) |

**These are different eras on the CPU-kernel axis** (`E6-cpu-kernel` → `E8-cpu-kernel`; v8 cutover
2026-07-25T18:38:43Z). Per the era registry's reconciliation rule: **do not rescale across this
boundary.** W0 figures are historical priors for v8 decisions, direction-only. Any W0-vs-Stage-B
delta below is a *four-way* confound (kernel + uptime + token budget + grade) and cannot be
attributed to any single axis.

### 6.1 W0 grids (original text, aggregate throughput tasks/h, raw offline_scores)

Bold = aggregate-optimal cell for that model group. All numbers were cross-checked against the
actual run-dir `summary.md` files, not just the handoff — no discrepancies found.
69/69 cells ran clean across 4 model groups (2,967 saved offline-scored responses total).

#### qwen36_q8_0 (MoE-35B) — `e5-w0-qwen36-nothink-20260723T194901Z`

| Placement | np1 | np2 | np4 | np8 | np16 | np32 |
|---|---|---|---|---|---|---|
| C1 (whole-machine) | 1359 | 1505 | 1549 | 1610 | 1734 (kvu) | 1528 |
| C1b (second-node)  | 988  | 1120 | 1109 | 1198 | 1154 | — |
| C2 | 1540 | 1729 | 1826 | 1718 | 1707 | — |
| C3 (quarters) | 1682 | 1909 | **2028 (optimal)** | 1774 | — | — |

#### gemma4_26b_a4b_q4km_mtp — `e5-w0-gemma-20260723T203422Z`

| Placement | np1 | np2 | np4 | np8 |
|---|---|---|---|---|
| C1 (whole-machine) | 1515 | 2018 | 2127 | 2475 (np16: 2854, np32: 2879) |
| C3 (quarters) | 3246 | 4129 | 4448 | **5076 (optimal)** |

C3-np8 vs C1-np32 iso-T=32: 5076.47 / 2854.45 = **1.78x**. **All 10 cells are quality-invalid —
see §6.2 and §7.** Speed numbers above are retained only as scout throughput signal.

#### qwen36_27b_q8 (dense) — `e5-w0-dense-20260723T204720Z`

*Retained unedited. This model group's Stage-B wave (W3) was subsequently dropped by operator scope
decision — see §3. These scout rows are not superseded by anything and are not invalidated by the
drop; they are simply the last CPU-plane measurement this model will get.*

| Placement | np1 | np2 | np4 | np8 | np16 | np32 |
|---|---|---|---|---|---|---|
| C1 full-machine | 574 | 808 | 849 | 611 | 781 | 810 |
| C1 half0 | 751 | — | — | 814 | — | — |
| C1b (second-node) | 836 | 939 | 965 | 1009 | 984 | — |
| C2 | 819 | 1009 | 1085 | 1027 | 926 | — |
| C3 (quarters) | 1225 | **1415 (optimal)** | 1407 | 1334 | — | — |

Paired probes: half0 beats full-machine at both K=1 (751 vs 574) and K=8 (814 vs 611) — the dense
C1 shape question is **RESOLVED** (observation-grade, v7 era).

#### qwen3_next_80b — `e5-w0-80b-20260723T221055Z`

| Placement | np1 | np2 | np4 | np8 | np16 | np32 |
|---|---|---|---|---|---|---|
| C1 (whole-machine) | 1162 | 1434 | 1550 | 1669 | 1700 | 1556 |
| C1b (second-node)  | 1377 | 1659 | 1886 | 2013 | 1905 | — |
| C3 (quarters) | 1897 | 2275 | **2520 (optimal)** | 2386 | — | — |

#### W0 cross-model pattern (original text)

- **Held for every model**: C3 (quarters) is aggregate-throughput-optimal for all four groups
  (qwen36 MoE-35B, gemma, dense, 80B) — the quarter-split beats whole-machine and second-node
  placements everywhere tested.
- **Model-dependent**: C1b (second-node) vs C1 (single-node whole-machine) flips by architecture.
  It **loses** for the MoE-35B (qwen36: np4 1109 vs 1549) but **wins** for dense (np4: 965 vs 849)
  and 80B (np4: 1886 vs 1550).

### 6.2 W0 per-wave prune status (original text, from `stage_b_prune_plan.json`)

| Wave | Model | Prune decision | Reason |
|---|---|---|---|
| **W1** | qwen36_q8_0 (MoE-35B) | Prunes only `C1b-{np4,np8,np16}` (throughput-only) | W0 whole-machine C3 wins by 44.78% / 44.77% / 34.97% at T=8/16/32; C1b/C1 ratio is 0.598 at K=4 and 0.463 at K=8, reproducing the documented half-pair collapse. |
| **W2** | gemma4_26b_a4b | **Full grid retained** | Retain full-vs-quarter family for clean 256-token confirmation despite W0 C3 wins of 36.24%-43.77%. **QUALITY-INVALID for interpretation**: original capture stored reasoning text without an answer channel — all 430/430 offline_scores rows are unrecoverable parse failures, no raw SSE ledger survives. RE-ATTRIBUTED 2026-07-29 (research `5d6a17f2`): the actual budget sink was **reasoning mode ON** — the harness emitted no `--reasoning` flag, so gemma4 ran at llama-server's `auto` default while both registries record `reasoning: 'off'`. The fail-close capture gate (`efd0980c`) **detects** this, it does not **prevent** it; a focused post-fix capture smoke test is a precondition before any decision-grade W2 run. |
| **W3** | qwen36_27b_q8 (dense) | **Full grid retained** | Dense C1 shape is already resolved (half0). W0's C1b@16 vs C3@8 comparison used mixed metric bases, so no additional prune is sound (flagged `[MIXED METRIC BASIS — caveated]` in the run summary). |
| **W4** | qwen3_next_80b | **Full grid retained** | Keep the ingest whole-machine family: W0 favors C3 by 17.44%-26.39%, but the 256-token clean confirmation remains the operator-scheduled W4 purpose. High-K `raw_fallback` rows are demoted from decision-grade use (per the handoff's W0-summarizer entry; not separately itemized in the prune-plan JSON). |

*Appended 2026-07-29 (the table above is the original text, unedited):* the **W3** row is
**superseded by the operator scope decision in §3** — W3 was not run at all, so its "full grid
retained" prune decision was never executed. The row is kept because the prune plan is a historical
record, and historical records are appended to, never rewritten.

### 6.3 Scout-vs-confirmed drift

‼ **TODO-FILL** ‼ — after Stage-B is summarized, add one table per model group comparing the W0
scout figure and the Stage-B figure for **cells that exist in both**, with the delta.

**Rules for filling this in:**
- Compare only like-for-like placements and `-np` values.
- Label the delta as **confounded** (kernel v7→v8, uptime, 64→256 token budget). Do **not** present
  it as a kernel effect, a batching effect, or a regression/improvement — it is none of those on
  this evidence.
- Where a Stage-B cell is observation-only (T=32) or missing, leave the row blank rather than
  reaching for the raw basis to fill it.
- If a W0 direction **reverses** under Stage-B, that is the single most decision-relevant line in
  this artifact — call it out in §4.

---

## 7. W2 (gemma4) quality status — **QUALITY-INVALID**

**Unchanged and binding: the gemma4 group has no usable quality ledger, and Stage-B does not
change that.**

- **W0 history:** all 430/430 W0 gemma responses were parse failures. Root cause was
  re-attributed on 2026-07-29 (research `5d6a17f2`) from a capture-parser bug to **reasoning mode
  ON**: the harness emitted no `--reasoning` flag at all, so gemma4 ran at llama-server's
  `--reasoning auto` default — which for `arch=gemma4` is ON — while both model registries record
  `reasoning: 'off'` for this GGUF. The entire generation budget was spent in the reasoning
  channel before the answer channel opened. The W0 responses have no raw SSE ledger and are
  **unrecoverable**.
- **The fix** emits `--reasoning` server-side (template-independent, unlike `enable_thinking`,
  which some templates ignore); 19 gemma4 manifests were amended with `reasoning:'off'` plus
  append-only provenance, restoring the pre-registered intent rather than changing it.
- **The precondition is a focused post-fix capture smoke**, with a pass/fail verdict tool
  (`scripts/benchmark/e5_w2_capture_smoke_check.py`) that checks three properties: `reasoning_text`
  persisted separately, nonempty answer-text deltas whenever tokens were generated, and the **real**
  offline scorer seeing scoreable answer text. A negative control against a *copy* of the historic
  W0 gemma run correctly fails all three and exits 1.
- **Status: the post-fix smoke has NOT passed.** ‼ **TODO-FILL** ‼ — record the smoke's run id,
  date, verdict, and per-property result here **only once it has actually run and passed**. Until
  that line reads PASS with a real run id, this section keeps saying quality-invalid.

**Consequence:** W2 §5.4 throughput may be used for placement/provisioning reasoning about the
gemma worker **only** in combination with a quality signal from elsewhere. It may not be used to
claim that any W2 placement serves *correctly*, because no W2 cell has ever produced a scoreable
answer.

**Scope of the exposure is bounded and verified:** qwen36 W1 carries `enable_thinking:false` and is
confirmed clean live (46/46 nonempty answers, 0 reasoning); W0 dense and 80B produced 989/989 and
645/645 nonempty answers. gemma4 is the sole exposure.

---

## 8. Instrument limitations that bind interpretation

These are **not** caveats to skim. Two of them determine which numbers in §5 may be quoted at all.

### 8.1 T=32 cells return an empty trimmed window → observation-only (recoverable)

**What happens.** The steady-state metric `tasks_per_hour_trimmed` is computed by
`trimmed_aggregate()`, which sets `ramp_end = min(end_s of successes)` and
`drain_start = max(start_s of successes)` and counts only successes lying fully inside that window.
When in-flight concurrency approaches the 43-prompt batch size, almost nothing both starts after
the first completion **and** ends before the last start. The window is empty,
`tasks_per_hour_trimmed = 0.0`, and the cell is force-demoted with the blocker
`empty_trimmed_window: raw ramp+drain fallback is observation-only`.

**Confirmed live** on `qwen36_q8_0-C1-np32` (32 in flight, single instance) and
`qwen36_q8_0-C2-np16` (2 instances × np16 = 32 in flight). It affects **every T=32 cell in the
campaign** — C1-np32, C1b-np16, C2-np16, C3-np8 and the W2/W4 equivalents.

**Why it matters.** T=32 is the **top rung of both pre-registered decision families** — iso-T
`{C1@32 vs C2@16}` and `{C1b@16 vs C3@8}`. So the highest-concurrency rung of E5's core
roofline-flip read is observation-only. This is not cosmetic. Low/mid-K rungs (np 1/4/8/16 solo)
are unaffected and returned `decision_grade=true`.

**It is deferred, not lost.** The full per-request start/end/latency/success ledger is persisted in
each run dir's `requests.jsonl`. A ratified alternative steady-state rule can therefore be applied
**offline to these exact runs** — deterministic replay before regeneration, **no re-run of any
inference required**, at zero inference cost.

**Why it was not fixed in-flight.** The trimmed-window definition is measurement-instrument
territory and therefore human-amendment-only; and changing it mid-campaign would have made the
cells already banked non-comparable to the ones still to run. Proposing an alternative rule for
operator ratification is the correct path, and it is open.

### 8.2 The summarizer's R2/R4 peak is INVALID by basis-mixing — do not quote it

**What happens.** Each cell reports throughput on one of two bases: **trimmed** (steady-state) or
**raw_fallback** (untrimmed, includes the ramp-up burst — and therefore systematically *higher*).
The offline summarizer's **R2** Pareto and **R4** `per_shape_np_optimum` **mix the two bases** and
do **not** exclude `decision_grade=false` cells. So a cell that has no steady-state value at all
can win a comparison against a cell that does, purely because it is being scored on the more
generous basis.

**Evidence** *(from a partial, in-flight W1 sample taken 2026-07-29 while the campaign was still
running — this is defect evidence, NOT a result; it is superseded by the final run and must not be
quoted as throughput; re-derive against the final run dir:* ‼ **TODO-FILL** ‼ *)*:

```
R2 peak_cell : qwen36_q8_0-C2-np16   578.6 tasks/hr   basis=raw_fallback   decision_grade=FALSE
   ranked above
               qwen36_q8_0-C2-np8    462.8 tasks/hr   basis=trimmed        decision_grade=TRUE

Like-for-like, the ranking REVERSES:
   raw basis    : C2-np8  669.2  >  C2-np16  578.6
   trimmed basis: C2-np16 has NO VALUE AT ALL (empty trimmed window, §8.1)
```

`C2-np16` therefore wins on **no consistent basis**. R4 picks the same cell on the same basis and
does flag `mixed_metric_basis: true` — but still picks it.

**Why it matters.** This is worse than the T=32 cells merely failing to contribute: they *actively
contaminate* the summarizer's headline. A reader taking R2/R4 at face value would conclude that
2×quarter @np16 is the peak provisioning shape. That conclusion is an artifact of the comparison,
not a property of the machine.

**R1 is clean and is the rule to quote.** R1 already guards per-pair with a `mixed_metric_basis`
check and reports `status: winner` only on a consistent basis (e.g. the clean half-machine T=16
pair, `mixed_metric_basis: false`).

**Fix and status.** The fix is to apply R1's existing guard to R2/R4 — exclude
`decision_grade=false` cells from aggregation, or refuse a peak whose basis differs from its
rivals. It was **not** changed in-flight: it is instrument code, the campaign was live on it, and
changing aggregation mid-run would make banked cells non-comparable. It is a **pure post-hoc read**,
so it is fixable and re-runnable **offline against the same run dirs at zero inference cost**.
Instrument/scoring changes are a human trust boundary — proposed and tested, never self-ratified.

> **Operator-facing consequence: no R2 or R4 output may be quoted as a headline in this artifact
> until the summarizer guard lands and is re-run offline.** §4 and §5 are built on R1 and on
> per-cell trimmed values only.

### 8.3 The Stage-B run manifests carry a STALE instrument-era stamp

The E5 cell manifests were frozen at pre-registration on 2026-07-23 with
`ERA_CPU_KERNEL = "E6-cpu-kernel"` hardcoded (the **v7** cutover boundary,
2026-07-20T13:30:13Z). The frozen manifests are the source of the `era` block copied into every run
manifest. But Stage-B actually executed on the **v8** kernel (binary 10107 / `67a433bf4`), which is
`E8-cpu-kernel`, from 2026-07-25T18:38:43Z.

So `manifest.json → era.cpu_kernel` reads `E6-cpu-kernel` on runs that are physically E8. The era
stamp was correct for W0 (which genuinely ran on v7 / binary 10098) and is stale for Stage-B.

**This changes no measured value** — throughput, latency and attestation are all recorded
correctly, and the binary version in the attestation is the authoritative record of which kernel
ran. It affects **labelling**, which is exactly what the era registry exists to get right.

‼ **TODO-FILL** ‼ — resolve before publishing: state the correct era (`E8-cpu-kernel`) in §5.1,
and note that the run manifests' own `era` field is superseded by this correction. Era registry
rows are human-amendment-only; the correction is recorded as an append, never as an edit to the
run artifacts.

### 8.4 Under-load throttle gate was cpuset-blind (FIXED + operator-ratified, 2026-07-29)

The under-load CPU-frequency gate counted boosting cores across all 96 physical cores and required
≥80. But C1 pins 48 physical cores (0-47) and C2 pins 48 (48-95); the idle remainder parks near base
clock — so the gate **could never pass for a partial-machine cell**. W0 evidence has zero
counterexamples: every 96-core cell passed, every 48-core cell failed.

Throttle warnings feed `gate_warnings → hard_gates_passed → decision_grade`, so **19 of 45 Stage-B
cells** would have been force-demoted to observation-grade — including **100% of the pre-registered
half-machine mechanism family `{C1@T vs C2@T/2}`**, which is E5's core roofline-flip read.

The fix scopes the gate to the cell's pinned physical cores at the **unchanged** 2.5 GHz threshold
and **unchanged** 80/96 ratio (a 96-core cell still needs exactly 80; C1/C2 need 40 of 48), and now
persists the full per-core frequency vector in `throttle_check`. Because a measurement safety gate
is human-amendment-only, this was **presented as a decision package and ratified by the operator
before any edit** — never patched unilaterally.

**Not repairable retroactively for W0:** the old sampler persisted only the aggregate count and
discarded the per-core vector, so deterministic replay did not apply. W0 records stay unedited.

**Open:** whether this warrants an instrument-era row is an operator decision, still pending. The
change alters no measured value — only decision-grade *eligibility*.

### 8.5 Affinity preflight is blind to non-llama GPU processes and to SMT siblings (open)

The cell-mode preflight discovers foreign overlap only via a llama process-name pattern, so a
Python ROCm/PyTorch/TRL trainer is uncounted. Its raw logical-CPU intersection is also SMT-blind:
GPU host threads `184-191` and an E5 `0-95` cell share physical cores `88-95` but have an empty
logical-id intersection.

**Containment in force for this campaign:** no MI210 training workload may start during E5; the
training-viability smoke is deferred until the host is released. ‼ **TODO-FILL** ‼ — confirm from
the run events that no such process was resident during Stage-B before treating §5 as clean on this
axis.

---

## 9. What E5 still cannot tell us

- **Production-contended throughput.** §2: the host was quiesced with AutoPilot down. These are
  ceilings for placement comparison, not production capacity numbers.
- **The top rung of both decision families, on a sound basis.** §8.1: every T=32 cell is
  observation-only pending an operator-ratified steady-state rule applied offline.
- **Any peak-aggregate (N,K) claim from the summarizer.** §8.2: R2/R4 are basis-mixed. Only R1
  (iso-T, per-pair, basis-guarded) is sound today.
- **Gemma correctness at any placement.** §7: no W2 cell has ever produced a scoreable answer.
- **The dense control on the CPU plane.** §3: W3 was dropped by operator scope decision because
  that model is going GPU-resident. The W0 dense scout rows (§6.1) are the last CPU-plane
  measurement this model will get, and they are observation-grade v7-era.
- **Anything about quant pairing.** E5 sweeps a single quant per model, so the (CPU-quant,
  GPU-quant) axis stays single-valued — out of scope by design.

---

## 10. Provenance

**Handoff of record:** `handoffs/active/batched-decode-measurement.md` — E5 section (waypoint,
"E5 W0", "W0 summarizer + Stage-B prune", "W3 dropped", "T=32 cells", "R2/R4 mix metric bases",
"W2 focused post-fix capture smoke", "E5 W1-W4 runs" entries).

**Protocol:** `P-BENCH-3` (`MEASUREMENT.md` §1). **Harness:**
`epyc-inference-research/scripts/benchmark/server_numa_np_sweep.py`. **Frozen pre-registered grid:**
`scripts/benchmark/e5_cell_manifests.py` (121 cells). **Runbook:**
`data/batched_decode/E5_STAGE_B_RUNBOOK.md`.

### 10.1 Stage-B run dirs (`epyc-inference-research/data/batched_decode/`)

| Wave | Run dir | Cells | manifest.json SHA-256 |
|---|---|---|---|
| W1 | ‼ **TODO-FILL** ‼ | ‼ TODO-FILL ‼ | ‼ TODO-FILL ‼ |
| W2 | ‼ **TODO-FILL** ‼ | ‼ TODO-FILL ‼ | ‼ TODO-FILL ‼ |
| W4 | ‼ **TODO-FILL** ‼ | ‼ TODO-FILL ‼ | ‼ TODO-FILL ‼ |
| W3 | — not run (§3) | 0 of 14 | — |

*Note when filling in: the campaign driver was killed and replaced mid-flight (before it could
auto-launch the dropped W3). Verify that the run dir cited for each wave is the **final** one and
not a superseded partial — check `cells.jsonl` line count against the pruned cell count and confirm
the run reached its last cell.*

Per-cell request/response ledgers (`requests.jsonl`, `responses.jsonl`), per-cell affinity artifacts
(`affinity/`), server logs (`logs/`) and `summary.csv` live under each run dir.

### 10.2 W0 run dirs (retained)

- `e5-w0-qwen36-nothink-20260723T194901Z` — canonical qwen36 source; 903 offline_scores rows
- `e5-w0-gemma-20260723T203422Z` — 430 rows, all parse-failed (§7)
- `e5-w0-dense-20260723T204720Z` — 989 rows
- `e5-w0-80b-20260723T221055Z` — 645 rows
- Sum = 2,967 rows, matching the handoff total exactly.
- Two additional qwen36 dirs exist on disk (`e5-w0-qwen36-20260723T190338Z`,
  `e5-w0-qwen36-rerun1-20260723T191759Z`) but are **not** the canonical `W0_qwen` source in the
  prune plan — the `-nothink` dir is.

### 10.3 Prune plan

`data/batched_decode/e5_pre_reboot_20260728/stage_b_prune_plan.json`, SHA-256
`cabd10bd0fe52ed04ca28e314ad0ab8d505de9e5db571115d16c48d0832daee8` — confirmed matching the
handoff's pinned value. Append-only supersession chain; superseded predecessor hashes recorded
in-file (`06b0abb2ca7abaf004ce56658a8c3753ea719ebdc4f1b50bec65a015954d4f8b` →
`9b4d4f034e3da01cbaaa652838aa9bb481855853180e8deb2dfafc27d69396b8` → current). The earliest
predecessor file does not survive on disk and is not independently re-verifiable.

### 10.4 Commits (research repo, `/mnt/raid0/llm/epyc-inference-research`)

| Commit | What |
|---|---|
| `b294daa0` | E5 harness implementation (+ orchestrator `6a55aeed`) |
| `6b9a90c7` | sampling regime decision — production temp + seed 42 on every cell |
| `efd0980c` | W0 offline scoring + fail-close capture gate |
| `d61e4e8c` | provenance-repair edit to `stage_b_prune_plan.json` |
| `98cfff44` | throttle gate re-scoped to the cell's pinned cores (§8.4, operator-ratified) |
| `5d6a17f2` | `--reasoning` emit + 19 gemma4 manifests amended to `reasoning:'off'` (§7) |
| `040a2ad7` | `httpx` declared as an `--execute`-path dependency |
| `4a5b6bc7` | llama-process discovery via `/proc/<pid>/exe` instead of `ps args` substring |
| `c48bcb60` | W2 capture-smoke verdict tool + smoke manifest (§7) |
| ‼ TODO-FILL ‼ | Stage-B result commits |

### 10.5 Document history

| Date | Change |
|---|---|
| 2026-07-28 | First publication — W0 preliminary (scout) results, OBSERVATION-GRADE banner. |
| 2026-07-29 | **This revision (STAGED, unpublished).** Grade banner rewritten from observation-only to the two-grade table; scope section added (three model groups + W3 drop rationale); quiesced-host statement added; Stage-B decision-grade sections added with full claim grammar; W0 figures retained verbatim and era-labelled; §8 instrument limitations added (T=32 empty trimmed window, R2/R4 basis mixing, stale era stamp, throttle-gate re-scoping, preflight blindness). W0 numbers unedited throughout. |

---

*Numbers in this artifact follow the `MEASUREMENT.md` claim grammar — (metric, protocol-id, n/reps,
date, host-attestation ref). A figure quoted without that grammar is an observation and gates
nothing. Historical figures are appended and era-labelled, never edited.*
