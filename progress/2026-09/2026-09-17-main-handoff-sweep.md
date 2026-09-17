# 2026-09-16/17 — main session: handoff sweep (zero-inference fan-out + GPU queue)

This main thread ran the handoff sweep. It dispatched up to 10 subagents at a time on zero-inference and GPU
tasks, then reviewed and integrated their work. The main thread ran no inference itself; the MI210 queue
belonged to `sub-gpu-runner`, which was later collected by `sub-gpu-collect` / `sub-gpu-collect2`. Each lane's
detail is in its own shard, `progress/2026-09/2026-09-16-sub-*.md` and `2026-09-17-sub-*.md`. Pass 1 of
2026-09-16 is `2026-09-16.md`. This shard covers the rest of the sweep through the 2026-09-17 operator
`/wrap-up`.

## GPU outcomes

| Item | Result | Evidence |
|---|---|---|
| INF-62 SL-1 (`--spec-draft-n-max` × `p-min`) | **Keep n-max 8.** The DFlash2 block_size 8 clamps it to 7. p-min is ignored on the DFlash2 branch. | research `6b585b58` → main `8146880b` |
| INF-62 SL-5 (DF2-6 A/A) | **Deterministic.** 12/12 identical per arm across fresh processes, so run-to-run noise is zero at temp 0. | research `416cd853` |
| DF2-6 serial-exact confirmation | **Serial-exact passes 12/12** on both drafters. Non-parity is the 1-row vs multi-row numeric split, not a DFlash2 defect. | research `7a876f23` |
| CJ-1e GPQA-Diamond pair | **Unresolved.** 152 vs 158 of 198, sign test p = 0.405. The box stays with the owner; CJ-GATE decides adoption. | research `c72e5ad2` |
| fable5 §5 #1 MoE batched `-np` | **Q-A GO** (E = 1.021). **Q-B bounded null:** M2(32) = 0.619 / 0.655 after the pre-registered top-up. **CLOSED** as a bounded null on 09-17; operator: "no more levers". | research `6cbdd856`, `f5179054` |
| ERNIE MI210 ROCm | **Fix refuted.** All 4 precision variants (off, narrow f32, wide, outscale) leave ≥1024² blank. | research `cf05eefc`, `ca8c63d6` |
| EV-13b review-F1 | **Fails the EV-6 judge-swap gate:** 2.94pp vs the 2pp limit. Leg B was not run. The operator **PARKED** it on 09-17 (root `007e4092`); it resumes when HG-9 needs a judge-stable ranking. | research `aac025a4` |
| OCC-1 optical compression | **NEGATIVE, closed.** Every image arm's ΔF1 CI lies below −0.3. | research `84dc568d`; root `960a97c9` |
| INF-61 np×depth grid at n-max 8 | **Slower** than the withdrawn n-max 4 grid at np≥2 (cross-session). The A/B/A is approved but on GPU hold. | research `0a711890` |
| PRB-T4 TALE-EP | **Inconclusive** on 3 of 4 suites. Scorers fixed (orchestrator `f0015306`, research `52595b9b`); re-run filed (PRB-T4-RERUN). | research `b4d38ebc` |

## Infrastructure and governance outcomes

- **Hub:** `:8100` serves a read-only origin/main view (dashboard fix A, root `87152356`; orchestrator
  launch manifest `3e967e27`).
- **Hub manifest v12 change reverted:** orchestrator `e7bfc62b`, reverted in `0329ab10`. Its premise was
  wrong: v12 was stopped, and aku12a is the live store.
- **Push helper:** `sub-gpu-collect-push.sh` now fails loudly. It checks every step, exits 5 on a rebase
  conflict and exits 6 when there is nothing to push.
- **Supervision:** `fleet_watch` cron installed; hub supervisor relaunched from the canonical root.
- **AutoPilot safety and evidence** (in the merge train `sub/autopilot-train-20260916`, being merged and
  pushed now):
  - AP-54 eval fence: Landlock read, write and execute, plus the inherited-TMPDIR fix.
  - AP-55 promotion gate in shadow mode (operator mode A). AP-55-ARM is pre-approved after one shadow run.
  - Gate-frontier (c)+(b): clean trials become frontier representatives; an empty frontier needs ≥3
    comparable reproductions.
  - Mutation identity = the mutated-file sha (`f083a0cd`); mutation candidates are allowed in multitier
    (`c12f17f5`, review fixes `25c8e913`).
- **v7 runner pins resealed:** research `6d010a92` (RATIFIED).
- **P-CAL ratified:** root `86f290d0`, option (a).
- **HS-4 decided:** thin shell (OpenCode), with the Hermes features built in the orchestrator (root
  `903ec585`, merged in `cbe105fe`).
  - P0.1/P0.2 landed on orchestrator main (`ed554da2`, `b44ab3a8`).
  - P0.3 and P0.3b landed on root (`4c1d1f3e`, `71569c2c`).
  - SC86 write hook landed (`934317b2`).
- **Harness improvement loop:** stub filed (UFH-08, root `f19f7ab3`).
- **UFH-02 closed:** `hermes-outer-shell.md` moved to completed (`c63947f5`, `9b5090be`).
- **Rewind leak, option A:**
  - The live prompt leak is fixed (orchestrator `09bdb998`).
  - The checkpoint re-pin ratify script is on root (`0e2bbc33`) and **awaits the operator's RATIFY**
    (MHS-3b).
- **Closure-inflation audit:** about 5 of 3,359 ticked boxes asserted code that never existed, all from
  one commit (`4762625d`). RC-9 and E1a were reopened. RC-9 has since been re-implemented (orchestrator
  `ebfb1cb5`).
- **Other landed work:**
  - Red tests fixed across all three repos (root `6df6d793`, orchestrator `3a7e8081`, research `8eca61d5`).
  - The dead `/v1` `recall()` fixed (orchestrator `83c7ed2f`).
  - The inert `mempalace:` block commented out (root `91d56181`).

## Holds and in-flight work at wrap-up time

- **GPU hold:** the operator asked for **no GPU work until they signal** (AutoKernel quiet window). Every
  GPU follow-up filed in this sweep waits on that signal: INF-61-ABA, DF2-8a, ERNIE-ROCM-NEXT and PRB-T4-RERUN.
- **AutoPilot merge train:** `sub/autopilot-train-20260916` is being merged and pushed now. After it lands:
  - flip MHS-3;
  - AutoPilot restart and API reload (the AP-54 fence goes live);
  - AP-55-ARM after one shadow run;
  - VB-MHS-OPS-HOOK and VB-AP-PROMO-RULE.
- **Episodic-memory leak cleanup:** prep is in progress (MHS-3c).
- **Operator steps outstanding:** MHS-3b (checkpoint re-pin RATIFY).

## Why the backlog grew

The open-box count rose during this sweep, and that is expected. Many new boxes were filed:
- HS-4 P0–P5;
- HIL-1..5;
- VB/SC write-side tasks;
- the reopened phantom closures RC-9 and E1a;
- PRB-T4-RERUN;
- the follow-ups filed by this wrap-up.

Meanwhile, index pruning and the wiki compilation sweep run only in an operator-invoked `/wrap-up`, and
none had run until this one. Filing is continuous and pruning is batched, so the count rises between
wrap-ups.

## This wrap-up (progress + checkbox sync pass, `sub-wrapup-port`)

- Ported 20 subagent shards from the shared clone:
  - 15 were missing on origin/main;
  - 4 appended to their origin/main copies (ap54-fence, gate-frontier, hs4-p03, vb-writers);
  - ap55bc was taken from the shared clone because it records the review fixes (`0e6e2288`).
- Skipped `2026-09-14-research-intake.md` and `2026-09-15-opencode.md`: origin/main already has the newer,
  post-wrap-up copies.
- Checkbox flips:
  - fable5 §5 #1 (bounded null);
  - SC85 (root `1d5f5314`, research `2f053f61`/`e2c48c13`);
  - v7 re-seal, recorded as `[x]`;
  - MHS-3a;
  - HS-4 P0-pre ×2 (recall fix, mempalace block).
- New tasks: AP-55-ARM, VB-AP-PROMO-RULE, VB-RUNNER-PATHS, MHS-3b, MHS-3c, HS-4 P0-MCP-a/b, INF-61-ABA, DF2-8a, ERNIE-ROCM-NEXT, Z12-COMMIT, K28.5a-COMMIT, AKU-RED-LOOP.
- The EV-13b-GATE and EV-13b-LEGB drafts were dropped at rebase: the operator had already parked EV-13b
  (root `007e4092`), which settles both.
- Agent logging was not active for this session.
