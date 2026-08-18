# 2026-08-18 — research-intake — oh-my-pi / omp cohort (stages 1–4)

**Session**: operator-invoked `/research-intake https://github.com/can1357/oh-my-pi https://omp.sh/`
**Outcome**: 13 entries `intake-1148..1160`, all `dive-verified`; 7 handoffs amended, 1 stub created,
1 index row added. Started 2026-08-16, completed 2026-08-18.

## Problem

Two operator-submitted sources on the **oh-my-pi (omp)** coding agent, whose headline claim is that
changing only the *edit tool* — holding model and prompt fixed — lifts coding pass rate by more than
most model upgrades, at zero training compute. The question for us: is that real, and does it bear on
the open HS-4 harness-selection gate or on our own edit/eval paths.

## What the dives found (root cause of the entry-level corrections)

| Finding | Status |
|---|---|
| Grok Code Fast 1 `6.7% → 68.3%` | **CONFIRMED exactly** — 4/60 → 41/60 in the published run reports |
| "+15 pts avg over patch" | **CONFIRMED** — independently recomputed as **+15.61** |
| "3 runs per task, 180 tasks per run" | **OVERTURNED** — all 134 reports are n=**60**; headline cells are single-shot (`Runs per task = 1`) |
| Effect vs `str_replace` (the realistic baseline) | **NARROWED to +2.97 pp** (14/19, sign p=0.064) vs +19.4 pp against `patch` |
| Noise floor | **MEASURED from the author's own 22 repeated configs**: median test-retest spread 3.75 pp, max 17.8 pp; binomial 95% CI at n=60 is ±15.5 pp unpaired |
| Per-line content hashes (the novel mechanism) | **ABANDONED BY ITS AUTHOR** in `30793c165`/`7c6457652` (May 2026) for a file-level 4-hex tag + **plain line numbers** |
| "hashline is line-granularity vs our file-granularity `current_shas`" | **OVERTURNED** — shipped hashline is file-granularity, the same property we already have |
| Diff-XYZ "contradiction" with the harness claim | **DISSOLVED** — the paper disclaims production prediction and is non-reasoning/greedy/single-pass; its "smaller open models" means sub-7B Qwen2.5-Coder (a floor effect) |
| omp HS-4 cooperation surface | **CONFIRMED SUFFICIENT, config-only, no fork** — `compat.extraBody` → `Object.assign(params, extraBody)` |

**Consequence for us**: the effect that survives is "replacing a diff-blob format with a line-anchored
one is worth a lot *for models not tuned to that blob format*". Against `str_replace` it is inside the
benchmark's own noise. Neither this cohort nor Diff-XYZ measures the band of open-weight models we
actually serve — that is unmeasured, not settled.

## Corrections pushed back onto the entries that carry them

Checking the citations deferred at Stage 1 found intake-1150's **prior-art paragraph** wrong in three
places, while its own measurements (already verified) stand untouched:

- `26% → 59%` attributed to GPT-4 Turbo; the aider primary source says that is **June GPT-4**
  (Turbo went 20 → 61), and drops aider's disclosed **72% ceiling** (28% of tasks don't fit 8k).
- A sentence attributed to Cursor's blog ("full rewrite beats aider-like diffs under 400 lines")
  **is not in it** — Cursor says its *eval set* was built from ~450 files under 400 lines. The
  sentence matches the title of aider GitHub issue #625.
- "GPT-3.5 scored 19%" **not located** on either aider page searched — recorded as unlocated,
  explicitly **not** as fabricated.

Also cross-linked onto intake-1148: Cursor **and** aider independently name line-number emission as
the failure mode to avoid, and both predate hashline — whose shipped format moved toward it.

## Changes

| Repo | File | Change |
|---|---|---|
| epyc-root | `research/intake_index.yaml` | +1,834 lines, pure append + in-place dive fields; 13 new entries, all `dive-verified` with `claim_anchors`, `claim_corrections`, `depends_on`, `dive_corrections` |
| epyc-root | `handoffs/active/harness-selection-and-integration.md` | omp candidate row; **HS-1d** `[x]`, **HS-5** `[ ]` |
| epyc-root | `handoffs/active/batched-edit-parallel-apply.md` | **BEP-6** `[x]`, **BEP-7** `[ ]` |
| epyc-root | `handoffs/active/canonical-judge-suite-revamp.md` | **CJ-7a–d** `[ ]` (judge-free suite designs) |
| epyc-root | `handoffs/active/delegation-context-preassembly.md` | **DCP-7**, **DCP-8** `[ ]` |
| epyc-root | `handoffs/active/speculative-decoding-mtp-refresh.md` | **SR-8** `[ ]` |
| epyc-root | `handoffs/active/architect-model-selection-bench.md` | **CAL-1** `[ ]` |
| epyc-root | `handoffs/active/scoring-infra-standardization.md` | **Phase 3 · 3a, 3b** `[ ]` |
| epyc-root | `handoffs/active/optical-context-compression.md` | **NEW STUB** — OCC-1/2/3 |
| epyc-root | `handoffs/active/routing-and-optimization-index.md` | **RTG-53** row (deps `UFH-07, INF-41`) |
| epyc-root | `handoffs/active/master-handoff-index.md` | regenerated rollup counts only |

## Results

- `validate_intake.sh` **exit 0** (1,156 entries, 0 duplicate ids, 0 duplicate arxiv_ids)
- `index_state.py --check` **exit 0, 0 problems** — new stub owned by exactly one row, no orphans
- **Zero deletions** in `handoffs/` apart from the 4 regenerated rollup rows; rollup arithmetic
  reconciles exactly against what was added (+1 / +7 / +6 / +1 across the four domains)
- Checkboxes: **15 new `- [ ]`**, **2 new `- [x] … ✅ 2026-08-18`** (HS-1d, BEP-6 — both settled by dives)

## Two things worth remembering beyond this cohort

1. **`snapcompact` (intake-1159) — optical context compression.** History rendered to pixel-font PNG
   frames read back by a vision model: local, deterministic, **no LLM call**. A zero-inference
   alternative to what `tool-output-compression.md` and `context-folding-progressive.md` do with a
   model call. It ships **without its evidence** — ~70 experiment scripts, zero committed results —
   which is why it is `worth_investigating`, not `adopt`. Now owned by the new stub (OCC-1).
2. **Copilot Arena (intake-1156).** Static code benchmarks rank-correlate with real in-the-wild
   developer preference at **r_s ≤ 0.1** (vs 0.62 for Chatbot Arena coding), over 4.5M suggestions and
   11,604 votes. An external caution on static-suite model ranking — filed as CAL-1 with its
   counter-reading attached (preference may track latency/verbosity, and it measures neither
   correctness nor throughput).

## Two operator declines that were wrong, recorded because the reasoning should be visible

I recommended declining Copilot Arena ("no read-across") and Qwen2.5-Coder ("low relevance"). The
operator overrode both. Copilot Arena turned out to carry the most useful external number of the
session; Qwen2.5-Coder is what makes the intake-1151 correction *checkable* rather than assertable.

## Deferred

**OCC-1 is the only open measurement**: billed-token cost and QA recall for bitmap frames vs raw
text, on a reader we serve. Blocker is a named external prerequisite — a vision-capable local reader
on the live vision path (`multimodal-pipeline.md`, INF-41) — not a decision. Filed as OCC-1/2/3 with
an index row, not left in prose.
