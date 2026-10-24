# 2026-10-24 — workspace-f8

## Night 2026-10-23 → morning 2026-10-24 (per-task /wrap-up, subagent, branch `f8/wrapup-20261024-morning`)

Not operator-invoked: Step 3 pruning and the Step 5 wiki sweep did not run. Scope is the f8 root commits on origin/main
after the evening wrap-up (`4e9d96ecd`), one research commit, and the overnight GPU/CPU jobs reported by the calendar owner
(workspace-58). Results were read from each launcher's `launch.log` RESULT line and its verdict files.

### Root commits

| SHA | What |
|---|---|
| `4b9aaa337` | Applied the evening's prepared rows: the OP-83 row no longer names the private pilot path, and INF-22's next action moves from M4.1 to M4.2. |
| `f12ddb9aa` | **KPF-17.4b ticked** (c1_locus `target_restore_defect`). KPF-17.4c filed. KPF-13.1b spec-off half noted as NOT decision-grade. KPF-GL2 live proof recorded. |
| `28c039dd7` | vidya: kpf174b rules-v2 conformance arms (`kpf174b_c1_spec_off`, `kpf174b_junction_sweep`). They project the pass fraction through the existing conformance path; `claim_tuple.grade()` decides, no new rule. 41 tests. Dry-run of the jsonl sidecars: 1/1 projected per sidecar, 0 refused. The pretty-printed `records/*.json` are declined by design (they duplicate the jsonl). |
| `5cf67c1c0` | RTG-58 next action after the KPF-17.4b read-out (13.1b resume, 17.4c filed). |

### Research commit

| SHA | Branch | What |
|---|---|---|
| `332cf2648` | `f8/kpf-gpu-followups-fix-20261023` | kpf13 `Server.start` (GPU) waits up to 120 s (2 s poll) for its own teardown's VRAM to drain before the empty-card check, and logs the wait. kpf174's silent 90 s wait is replaced by that shared logged wait. `analyze_v4` sets `decision_grade` only when BOTH launches have judged controls, as the predeclaration says. Rules shas unchanged (v4 `cbd24433…`, kpf174 v2 `2be6f9b0…`). 119 passed. |

An amendment written after the run records both fixes. It changes no rule, and the original verdict file is kept as
written.

### KPF GPU follow-up results (job `kpf-gpu-followups`, 18:18-18:35Z)

- **KPF-17.4b:** c1_locus = `target_restore_defect`. With speculation off, g2 at c = 2148 diverges at token 56 with gap
  0.094 (not near-tie). g1 passes. In the junction sweep, the first failing junction is 2148 (pattern `other`, with an
  acceptance drop). Child: KPF-17.4c.
- **KPF-13.1b: NOT_DECISION_GRADE.** The spec-off launch ran all 6 cells (A 5/6, B 2/6). It gives a provisional
  target-side locus (`target_restore_defect`). The drafter-on launch aborted 1 s after the driver stopped its own spec-off
  server: the card still showed 38.34 GiB used, because of the VRAM release lag. Re-analysis with the fixed analyzer: all
  three decision fields read `NOT_DECISION_GRADE`, with provisional values kept separately. The original
  `decision_grade = true` verdict must not be cited.

### Infra lesson: KFD returns a dead server's VRAM late

After you kill your own GPU server, KFD takes more than 1 s to return its VRAM. A driver that runs launches back to back
must poll for the drain before its empty-card check. Two jobs hit this:

- `kpf-gpu-followups` (kpf13 drafter-on launch, 18:27:58Z), fixed in `332cf2648`.
- `ufh14-lb7-1-probes` (step s2-OFF refused at 20:25Z with 38 GiB free < 50 GiB, and no foreign KFD process). Its fix
  is in progress.

The lesson is now one dated row in the inference-backlog-scheduling skill's incident ledger
(`.claude/skills/inference-backlog-scheduling/references/incident-ledger.md`), in this commit.

### Operator

- **kpf131b-specon start.** The auto-mode classifier denied the start. The operator then approved it via the decision
  tool at about 07:49Z on 10-24, after the queue's 21:30Z guard had passed. Launcher up at 07:49Z (pid 2788428), ARMED
  flag touched at 07:50Z. It resumes only the 12 pending drafter-on cells of KPF-13.1b. **Armed, no result**; it is
  waiting for a grant.
- **KPF-18-S1.7g note (side agent, relayed by the operator).** The graphs-ON re-measure changes three variables at once:
  HIP graphs, a fresh load instead of a ~20-min step history, and stricter pinning. Its predeclaration already attributes
  any difference to all three jointly. So a "graphs-sensitive" label means HSF-4/5 must quote the graphs-ON numbers. It
  never means "graphs cause it".

### Overnight jobs that ended (reported by workspace-58)

Other agents are preparing the read-outs. Nothing here is a verdict beyond the RESULT line.

| Row | Ended | State |
|---|---|---|
| `kpf18-s1-step7-graphs-on` | 18:49Z | complete; read-out in progress |
| `kpf18-item3-v2-sameshape` | 19:03Z | RESULT `FORK_EFFECT`, 3/3 valid loads; read-out in progress |
| `gpu-zos-1a` | 19:11Z | complete; read-out in progress |
| `pb-qcost-1-confirm` | 20:17Z | complete; read-out in progress. Another session disturbed the SMT siblings 92-95 at about 19:30-20:00Z, which the read-out must account for. |
| `ufh14-lb7-1-probes` | 20:25Z | rc 1 on the VRAM drain race. s1-ON passed and is kept. Fix in progress; re-queued behind a FIXED flag. |
| `m4-srpf-pbhol` | 21:17Z | complete; read-out in progress |
| `spec-rng-1-2-gpu-run` | 22:21Z | complete; read-out in progress |
| `nib2-gnx1-reindex` | 01:09Z | complete; read-out in progress |

### Open items

- `kpf131b-specon` is waiting for its grant.
- ufh14-lb7-1: land the drain fix, then touch the FIXED flag.
- Seven read-outs are landing (every ended row above except ufh14).
- **Operator:** run the SEC-ART-POST-b ratify command, and label the DHM-4 pilot (OP-83). Both are still pending.
- `filler_run2.sh` has 2 lint hits.
- KPF-18-S1.R3 still needs a launcher. Item-3 v2 does not supersede it:
  - Item-3 v2 measures fork vs nofork against an A/A floor (`nofork` vs `nofork_repeat`, 3 fresh loads).
  - R3 needs two extra cold arms (coldC, coldD) for a 6-pair cold floor, a prompt-cache-hit arm on another slot, and an
    item-2 g3 re-run with at least 3 Q repeats. Item-3 v2 runs none of these.
  - R3's own text says item-3 v2 "stays its own row".
- CH-27 is waiting on workspace-7b's registry-plan paths.

### Checklist sync (handoffs not edited: three agents are landing read-outs there)

| Item | State | Note |
|---|---|---|
| KPF-17.4b | `[x]` (`f12ddb9aa`) | none |
| KPF-17.4c | `[ ]`, filed | none |
| KPF-13.1b | `[ ]` | correct: NOT_DECISION_GRADE until kpf131b-specon runs |
| KPF-18-S1.R3 | `[ ]` | its text still says item-3 v2 had "0/3 valid loads". It now has 3/3 (`FORK_EFFECT`). The read-out owner should refresh that clause. |

### Wrap-up gates

| Gate | Result |
|---|---|
| `index_state.py --check` | rc 0 on the first run; scratch warning unchanged (139) |
| Agent log | skipped: `agent_log.sh` writes into the shared clone's `logs/` (gitignored), not the worktree |
| Wiki / pruning | not run (per-task wrap-up) |

## Morning 2026-10-24: overnight read-outs (per-task /wrap-up, subagent)

### Root commits

| SHA | Content |
|---|---|
| `3837a842c` | M4.2 (INCOMPLETE, C2 NOT_MEASURED) and SPEC-RNG.1.2 (DO-NOT-CARRY, ticked) read-outs; VB-M4-PBHOL-WIRE and VB-SPEC-RNG-1-2-WIRE filed |
| `788f2a641` | master index rollup regenerated after the rebase (land.sh) |
| `5d674dd53` | GPU read-outs: KPF-18-S1.7g graphs-sensitive, item-3 v2 FORK_EFFECT, GPU-ZOS-1a OPEN; HSF-4.G, GPU-ZOS-2 and VB-KVU-PF.6 filed |
| `7d76d190e` | PB-QCOST-1 confirm (CONFIRMED, q axis PASS, INDICATIVE; confirm-R filed) and nib2-gnx1-reindex (PASSED at `fd1a894`, not ticked) read-outs |
| `f14fc6274` | INF-22 next action (M4.2 INCOMPLETE -> M4.2a); INF-50 drops SPEC-RNG.1.2 |
| `56cc57bdd` | next actions for INF-22, INF-23, RTG-58 and RTG-22; GPU-ZOS-1a residency-check amendment note |

### Read-outs (every verdict is by its predeclared rule)

- **KPF-18-S1.7g, step 7 with graphs ON:** graphs-sensitive in 4 of 21 cells (rule `79350337f034…`). HSF-4/5 must quote the graphs-ON numbers. The difference is attributed jointly to graphs ON, the HSA knob and the fresh-load / step-7-only history, NOT to graphs alone. HSF-4.G filed. Box ticked.
- **kpf18 item-3 v2:** FORK_EFFECT, 3/3 valid loads (rule `417310869f16…`). The child is a fork-effect candidate at token 1. Item 3 and R3 stay open.
- **GPU-ZOS-1a:** OPEN (rule `d38ce7dd9149…`). Spec-on share 4.15%, spec-off 1.48%; grade INDICATIVE. GPU-ZOS-2 (the one-step-lag design) filed.
  - Validity check 2 was swapped in job.sh for own-pid KFD residency at 10-23 16:16Z, before the 19:03Z grant. The amendment was only written on 10-24 (`AMENDMENT-residency-check.md`). Verdict and grade stand.
- **M4.2 m4-srpf-pbhol:** INCOMPLETE (rule `c97394d2…`); not ticked.
  - C1 512/2048 PASS (B/A 0.997 / 0.994); C3 PASS.
  - C2 NOT_MEASURED: all 3 off512 B reps are invalid because the long finished before the short was answered. M4.2a is being prepared.
- **SPEC-RNG.1.2:** DO-NOT-CARRY (rule `0af228a0…`), ticked. The distribution is invariant and there is no reproducibility gain (probe net_gain 0/48). The drive was cut at the window deadline at N = 300 per cell, the V1 floor.
- **PB-QCOST-1 confirm:** CONFIRMED, q axis PASS, grade INDICATIVE (rule `f45aef1a…`).
  - Cause of the grade: a sibling-summary path bug (verdict_q reads `out/run/sibling_summary.json`, the sampler writes `out/sibling_summary.json`).
  - Also a real disturbance on SMT siblings 92-95 from another session at about 19:30-20:00Z. It overlapped ub512 and ub256; ub1024 was clean.
  - The run-level contention bar hid it. confirm-R filed with a per-phase grade; being prepared.
- **nib2-gnx1-reindex:** PASSED at `fd1a894`, but origin/main was 2 commits ahead, so not ticked. A re-run launcher is being prepared.
- **Belief kernel:** VB-KVU-PF.6, VB-M4-PBHOL-WIRE, VB-SPEC-RNG-1-2-WIRE and VB-GNX-REINDEX-1 filed; VB-PBQ-1 widened to the confirm run. A wiring agent is running.

### GPU ops

- `ufh14-lb7-1-probes` job.sh gained a bounded VRAM-drain wait (120 s, 2 s poll) before EVERY session launch. Reason: the calendar grants it right after kpf131b-specon, and on resume the own-server guard would not fire (s1-ON is skipped, so no own pid is recorded). Gates, thresholds and the refusal are unchanged. FIXED flag touched at 07:55Z; `AMENDMENT-vram-drain.md` plus its 08:05Z addendum.
- `kpf131b-specon` armed at 07:49Z; booked after inf42-g1-gpu (grant ends by 08:28Z).

### In preparation (not run)

- M4.2a
- PB-QCOST-1 confirm-R
- NIB2-GNX-1 re-run
- KPF-18-S1.R3 predeclaration and launcher

### Read-outs: KPF-18.0b CPU re-runs and DHM-7.2a (zero compute, predeclared rules)

- **KPF-18.0b, CPU re-run of items 1, 2 and 5** (fixed runner `d4633648…`, 2026-10-20 22:07–23:39Z).
  - Item 1, read as counts: on the four control metrics, top-1, max-abs and greedy prefix match the control. KLD is 0.1045 vs 0.0840. That is the reverse-direction KL of the control's own pair: the fork is bit-identical to fresh-B in 8 of 8. Ticked.
  - Item 5 holds, 14/14 and 22/22 for both cache-idle settings. Ticked.
  - Item 2 is bit-identical in 11 of 12 pairs, tokens 12 of 12, and the record is partial at 12 of 16. Not ticked; "item 2, rest" is filed (inference, one CPU quarter).
  - KPF-18.0b.2 is answered NO from the 10-21 item-7 polls (0 of 73 fork_off polls carry `kv_cells_*`). The fork gates the gauges on fork-enabled. Ticked.
  - Belief dry run: 5 rows, 15 frames, 0 refused.
- **DHM-7.2a** (job `dhm72a-granite`, rc 0 at 10-23 15:57Z).
  - The granite 97m embedder recovers 3/5 planted classes, the same count as TF-IDF but a different set, and reports 78 of 80 clusters against 80 of 80. A tie goes to TF-IDF. This agrees with the 10-24 sweep, which had already ticked DHM-7.2 and DHM-7.
  - Counts-only aggregate committed.
  - Fixed a `mine_m2.py` notes string that always claimed TF-IDF; a test is added.
  - No adapter for `dev-harness-aggregate.v1` yet (VB-LB1.1 is open, and its source row exists).
## Midday 2026-10-24: approvals, batch E, belief wiring, sweep dispatch (operator-invoked /wrap-up, subagent, branch `f8/wrapup-20261024-midday`)

### Root commits since `2b6921ec8`

| SHA | Content |
|---|---|
| `1efcf20c9` | SPEC-RNG.1.2 note: the N=300 cut bounds only the primary invariance test; DO-NOT-CARRY rests on the N-independent probe (0/48) |
| `c01b33527` | belief wiring: VB-KVU-PF.6 and VB-M4-PBHOL-WIRE ticked; new adapters `spec_rng_1_2` and `pb_qcost`; `scripts/gitnexus-index-receipt.py`; 2794 tests pass |
| `3418c3adc` | batch E notes: KPF-19.1a CPU leg and HYBRID-PREFIX-REUSE (b) 64k holdout launchers prepared; KPF-18.0b re-runs and the DHM-7.2a run already exist, read-outs remain |
| `ef7902e2c` | DHM-5.1 always-on prefix from turn-1 usage fields (`mine_dhm51.py`, aggregate, results section) |
| `c56dae201` | read-outs: KPF-18.0b CPU re-runs and DHM-7.2a (section above) |
| `294ac50ac` | master index block regenerated |
| `2f573e0f0`, `823368fa8`, `3aaf313cb`, `4590b344f`, `044d17d84` | first commits from the running sweep agents (lint cleanup, DHM-7/7.2/7.2a and RT-2.1 ticks, KVU-12.3a, DHM-5.1 tick with DHM-5.2 filed, SEC-ART-1.1). The sweeps are still running, so their results are not summarised here. |
| this wrap-up | progress, checklist sync (M4.2a and AKX-ALL-LB3.2a filed; arming notes), wiki compile, manifest |

### Operator approvals (decision tool)

- **Four launchers started**, all ARMED at 08:29Z (pids from FILLERS.md):
  - `m4-srpf-pbhol-2a` (M4.2a, pid 3297256). M4.2's C2 validity predicate rejected the head-of-line blocking it measures, and it would have rejected the PB-HOL-1 reference too. The fix: a rep is valid if the long is still in flight when the short is sent. Thresholds are unchanged. The old rows re-scored under it give 22.13x, recorded as non-gating. The job ENDED at 08:53Z; read-out owed.
  - `kpf18-s1-r3` (KPF-18-S1.R3, pid 3297259). ENDED 09:15Z, rc 0; read-out owed.
  - `pb-qcost-1-confirm-r` (pid 3297261), all three phases. This was the operator's choice over a cheaper ub256-only option, which would have relied on a per-phase rule written after the disturbance was seen.
  - `nib2-gnx1-reindex-2` (pid 3297264): a safe ff-only update of the shared orchestrator clone, then the re-index.
- **Batch-E one-quarter CPU correctness launchers PRE-APPROVED.** Two were armed at 09:06Z: `kpf191a-cpu-27b-dflash2` (pid 373944) and `hpr-b-64k-holdout` (pid 373947).

### SPEC-RNG.1.2 query (side agent)

The question was whether a 600-sample re-run is owed. No. The N=300 cut bounds only the primary invariance test, which passed. DO-NOT-CARRY rests on the 48-seed probe (0/48), which does not depend on N, so a re-run cannot produce CARRY. Note landed in `1efcf20c9`.

### Operator directive (relayed by workspace-58): dispatch every filed non-inference task now, fill idle CPU

The operator called 34% CPU utilisation over 12 h unacceptable. f8 had 89 open boxes, 46 of them non-inference (triage: `/mnt/raid0/llm/tmp/ws58-followups-20261024/TRIAGE.md`, owner f8, NON-INFERENCE). Four sweep subagents are dispatched and **still running; no results are reported here**:

- A: serving harness and orchestrator
- B: kernel, KPF and GPU design, plus folds
- C: belief kernel
- D: security, lint and log analyses

### Batch E (one-quarter CPU correctness work)

- Fit: KPF-19.1a (CPU leg) and HYBRID-PREFIX-REUSE (b) (64k holdout). Both armed, see above. Root notes `3418c3adc`.
- KPF-18.0b and DHM-7.2a had already run. Their read-outs landed in `c56dae201` (section above).
- LBH-2.1 is timing work, so it waits for a window.
- AKX-ALL-LB3.2 needs the whole host, and its instrument is not written. This wrap-up files AKX-ALL-LB3.2a: write the instrument now (code only).
- DS41-T5.1.1 is held.

### Belief wiring (`c01b33527`)

VB-KVU-PF.6 and VB-M4-PBHOL-WIRE ticked. New adapters `scripts/vidya/adapters/spec_rng_1_2.py` and `scripts/vidya/adapters/pb_qcost.py` (read sides done; VB-SPEC-RNG-1-2-WIRE and VB-PBQ-1 stay open on their write sides). New write-side tool `scripts/gitnexus-index-receipt.py`. 2794 tests pass.

### GPU queue and .trash pre-check

- GPU order: kpf131b-specon, ufh14-lb7-1-probes, m4-srpf-pbhol-2a, kpf18-s1-r3, then pb-qcost-1-confirm-r after the C4 champion rows. The CPU jobs are queued on q1/q2 from about 10:10Z, capped at 16:30Z.
- Ahead of the 15:40Z .trash sweep: all 49 paths of f8's armed jobs exist, and none resolve into `.trash`.

### Lesson (already in the incident ledger)

KFD releases a dead server's VRAM late. A launcher must wait for the VRAM to drain before EVERY launch, not only the first one.

### Checklist sync in this wrap-up

- Filed: M4.2a (box under M4.2) and AKX-ALL-LB3.2a (write the instrument now).
- Notes: arming of confirm-R, KPF-18-S1.R3, KPF-19.1a CPU leg and HPR-B 64k holdout. KPF-19.1a: the job-28 `strings-*` false negatives are the pipefail plus `grep -q` class, already linted.
- DHM-5.1 was ticked by a sweep (`4590b344f`), which also filed DHM-5.2, the paired probe. This wrap-up's duplicate (DHM-5.1a) was dropped during the rebase.
- Not edited: every task line that sweeps A-D own.
