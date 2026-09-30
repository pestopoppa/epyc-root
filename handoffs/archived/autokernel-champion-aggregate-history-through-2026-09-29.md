# AutoKernel champion aggregate — superseded champion-state history through 2026-09-29

> **Historical ledger only; current work lives in [`../active/autokernel-champion-aggregate.md`](../active/autokernel-champion-aggregate.md).**
> Superseded champion-state narration (the `a2728701` / `732389d6` / `ef81196d5` eras); the champion is now
> `90c12df42` on `ak/champion/llama-cpp-ffc1bac82eec`.

## Start here — open work (everything else on this page is closed evidence)

| task | what to do |
|---|---|
| **CH-14** | Write the manual-research loop runbook — START FROM `scripts/benchmark/serving_evidence_refresh_runbook.md` (research repo, 2026-08-31): the serving-side procedure is now fully documented+scripted there (emitter chain, ceiling derivation, claim/residency gates); CH-14's remaining scope is the authority-boundary statement in docs/guides/ wrapping it.  (admit → gate → attest) in `docs/guides/`, stating the authority boundary explicitly. |
| **CH-16** | Correct the loop champion's inflated per-commit claims at the branch tip and in `program.md` — UNBLOCKED 2026-08-31 (branch merged + tagged); coordinate with INF-66 R21-3 (if the branch is retired, the note lands at tag `ak/pre-reconcile-loop-20260831`). |
| **CH-4 / CH-6 follow-ons** | See their entries; both are settled to a conclusion, follow-ons only. |
| **not on this page** | `AK-INST-3` (prove a campaign reaches `sci >= 1`), `AK-INST-2`, `AK-DEPLOY-2` live in [`autokernel-restart-and-strip.md`](../active/autokernel-restart-and-strip.md). |

**CONSOLIDATION COMPLETE 2026-09-08 — the champion is `ef81196d5`** (GPU tip `bff30cebe` + CPU
champion3 `9c4f73e29`, FOLD-2 G1-G5 PASS). INF-70 has **no CPU keeps to fold**; the operator's
*no-kernel-research-until-a-fully-consolidated-champion* condition is satisfied. Loop relaunch is a
**separate operator go**. Before any sweep picks up "an unfolded CPU branch", read the **DO-NOT-FOLD
ledger** at the bottom of this page (`inf70/sync17-fix2 @ 2516c9807` is a measured **regression**).

**RECONCILED 2026-08-31 — there is ONE champion now, by ratified invariant.** The two lineages
this page used to distinguish were the incident (INC-20260831-champion-lineage-fork: the rebuilt
loop was seeded 2026-08-30 from bare v9 as a NEW sibling branch while THE champion sat one branch
over; runs 18–20 optimised the wrong base; surfaced when the operator asked why DFlash2 was absent
from the dashboard capability list). Operator ruling, ratified into
`agents/shared/OPERATING_CONSTRAINTS.md` (root `35c1a6d1`): **one single champion per production
kernel tree**, aggregating ALL improvement work (manual + AutoKernel) between promotions;
seed-from-production is legal only immediately after a promotion; a second lineage for the same
tree is a defect the moment it exists; standing is resolved against the CURRENT frozen production,
live, never a pinned sha; the champion exists so promotion = take the one precompiled branch.

**The current champion: `a2728701` on `ak/champion/llama-cpp-0db32c06e3e5`** — merge of the
manual-admission side (`270b48ed`, MoE-Spec + DFlash2, tag `ak/pre-reconcile-manual-20260831`)
and the loop side (`4925b208`, tag `ak/pre-reconcile-loop-20260831`); zero conflicts, disjoint
file sets. **Measured 2026-08-31: +12.618% tg128 vs production resolved live** (264.53→297.91
tok/s, 20 pairs, 10.6× the calibrated 1.188% floor; pp512 +0.078% = NO CHANGE, floor
uncalibrated), oracle 3/3, inside the pre-committed chain-estimate band [11.2–15.3] → the
lineages are **additive, no interaction**. `270b48ed` is an *ancestor* — its work is IN the
current champion. The +28–48% Qwen3.8-27B serving-path evidence remains operator-gated (CH-13)
with no promotion authority. The loop-side per-commit history remains inflated — read **CH-16**
before quoting anything from the old branch's commit messages. Enforcement: single-champion
startup refusal (research `470378a9`) — the loop refuses to start off the canonical branch; run
21 runs attached to it at `a2728701`.

**STANDING UPDATED 2026-09-03 — the champion has advanced to `732389d6`, and its standing is
THREE measured workloads, not one number.** The paragraph above records `a2728701`; run 23 then
added three keeps (`7d2ea88b` MMVQ crossover, `db18f393` fattn eight-wave VKQ, `732389d6` Q4_K
weight-block hoist), all ancestors of the current tip. Measured against frozen production-v9,
resolved live:

| workload | surface | result | evidence |
|---|---|---|---|
| `gemma-4-26B-A4B-it-Q4_K_M` (**in-fleet worker**) | dec-b4 | **+7.206% DECISIVE** (174.26→186.76 t/s, 20 pairs, floor 0.456% — 15.8× it) | `champion-vs-production.732389d6d9d0.gemma-4-26B-A4B-it-Q4_K_M.json` |
| `Qwen3.8-27B-Q8_0` (production) | dec-b4 (prefill) | **−1.414% DECISIVE** (66.09→65.00 t/s, 20 pairs, floor 0.949%) | `champion-vs-production.732389d6d9d0.json` |
| `Qwen3.8-27B-Q8_0` | speculative decode | **2.38× with DFlash2** (acceptance 0.6501) | `boundary-20260901/dflash2-smoke/verdict.json` |

**Reading it.** The two decisive numbers point OPPOSITE directions and both are correct: the Q4_K
keeps are hard-gated on `GGML_TYPE_Q4_K` and therefore fire on the worker and are inert on the
Q8_0 production model, where the residual −1.4% is the aggregate's DFlash2/feature machinery
measured on a prefill-only surface that cannot observe DFlash2's own 2.38× decode win. A single
champion-vs-production headline cannot express this (INF-66 R23-26); quoting one without naming
its workload is the defect that made the +27.363% screen-rung number misleading (R23-19).

**Not superseded, still true:** the +12.618% tg128 standing above was measured on `a2728701` and
has NOT been re-measured on the current tip — treat it as the last known value for that surface,
not as the current champion's tg128 standing.
