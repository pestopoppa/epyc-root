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
