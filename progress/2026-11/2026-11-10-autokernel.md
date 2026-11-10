# 2026-11-10 — autokernel

Filing session for finished AutoKernel rows and handoff proposals (worktree `ak/filing-20261110`).

## Results filed (C9 rows)

| Row | Box | Verdict |
|---|---|---|
| `inf75-w2-gpu-census-c9-20261109` | AKX-P0d-W2 (ticked) | OBSERVED prefill512 and decode1 on ROCm0 at C9; structural witness only |
| `ak-iq3s-prof-c9-20261109` | AK-SEED-IQ3S-PROFILE (ticked) | NO_MOVE; IQ3_S ratio median 0.944 vs control 0.939 |
| `ak-lb49-sinks-gate-c9-20261109-r3` | AKX-ALL-10.1 (open) | CONTROL_NOT_RED: candidate cases PASS (cross-nth max NMSE 1.96e-11) but the planted mutant stayed green, so the gate has no power; r2 failed on a mutant-copy bug (shutil ignored `build*`) and r3 superseded it; child box AKX-ALL-10.1-MUTANT-POWER filed |
| `ak-kernel-mmq-h3-c9-20261109` | AK-MMQ-H3 (open) | REJECT_CORRECTNESS: candidate 1038/1202 vs C9 1202/1202, NaN/inf at n=16; no timing; child box AK-MMQ-H3-NAN-DIAGNOSE |
| `ak-mmq-h10b-moe-determinism-c9-20261110` | AK-MMQ-H10b (open) | CONTROL_NONDETERMINISTIC: dense varies by seed but repeats at one seed match; MoE not run; child box AK-MMQ-H10b-R2; stale PARKED note removed |
| `ak-q38fn-relianceproof-c9-20261109-r4` | AK-PLANNER-RELIANCE-PROOF (open) | NOT PROVEN: receipts 0, one prevalidated runtime arm (-0.569%, not kept), two warnings; diagnosis and r5 prep in progress |

Any keep from these rows is recorded for the C11 fold, not C10; none was claimed.

## Code boxes (research repo, all merged)

AK-ADM-1 ticked (`2d60b6670`). AK-RSM-1 partial (`2962c4c6c`). AK-PM-17 partial (`dcf4fd313`). AK-PM-3 ticked (ledger row added). AK-PM-12 status note, open. AK-WM-3 and AK-lineage partial (`1d222ed1b`), both open. Vidya source rows and tasks VB-AK-WM3-REPLAY-WIRE and VB-AK-LINEAGE-TAXONOMY-WIRE added.

## Governance

Operator decision 2026-11-10 "AutoKernel takes all": CH-19, CH-32..CH-37, C8-1-H17 and DF2-BLOCK16 moved from main-inf22 (closed) to autokernel in `kernel-champion-and-promotion.md`. INF-06 Next-action cell refreshed.

## Floor r3 and the r5 chain (evening)

- Floor r3 is queued (rank 2, serving only). The predicted 19:07Z drain start slipped to about 18:35Z.
- Cause of the slip: from 15:05 to 16:40Z an escaped GPU child, probably from `c11-skinny-det-gpu-20261110-r2`'s hard-end (`skdetjob.py` killpg isolation), held 36.9 GiB, so the keeper dropped the floor's reservation. Fix: Pipeline deployed engine cgroup leaf reaping. Lesson recorded in `docs/guides/agent-workflows/compute-fillers.md` (harness units stay in the row's process group).
- My GPU rows (bracket, c4-7, race-eqv r5) are gpu-q3 timing rows, blocked because `afc-v3-mild` holds q3. Operator decision: CPU rows prefer q0-q2.

## skinny-det r2

Hard-ended in stage c. Stage a was clean: 0 new fails, 140/140 and 76/76 on both stores, 151 skinny routes each. Stage b never ran. The r3 republish is pending: `launch.sh` has the r2 id baked in and needs a reseal.

## INF-86 (hybrid-checkpoint-prompt-reuse.md)

Now owned by AutoKernel. Row `inf86-reprefill-rate-20261110` published 17:18Z: CPU quarter, 3x16K and 2x64K sessions of 8 turns, trimmed-reply divergence design, verdict_by agent. Lesson: verbatim reply replay never enters checkpoint search (v1 smoke had attempt_lines=0); recorded in `compute-fillers.md`. The (G) #25592 box Next action was updated; box not ticked.

## Ratify package answers (to Pipeline)

Drop the floor-accept C9 script (superseded by C10 floor r3). `ratify2` stays current; the operator dry-runs it first since item C may have drifted.

## Housekeeping

Pipeline removed the dirty worktree `ak-c10-refs2-20261110`; all contents were already on main. Earlier results were filed by a prior audit (`ea2a69982`, `5870a7962`) and are not refiled.
