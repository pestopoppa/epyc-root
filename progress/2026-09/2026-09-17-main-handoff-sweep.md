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
| INF-62 SL-5 (DF2-6 A/A) | **Deterministic.** 12/12 identical per arm across fresh processes, so run-to-run noise is zero at temp 0. | research `416cd853` (on main as `8146880b`) |
| DF2-6 serial-exact confirmation | **Serial-exact passes 12/12** on both drafters. Non-parity is the 1-row vs multi-row numeric split, not a DFlash2 defect. | research `7a876f23` (on main as `8146880b`) |
| CJ-1e GPQA-Diamond pair | **Unresolved.** 152 vs 158 of 198, sign test p = 0.405. The box stays with the owner; CJ-GATE decides adoption. | research `c72e5ad2` (on main as `8146880b`) |
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

## Afternoon (after wrap-up pass 1; recorded by wrap-up pass 2, `sub-wrapup-pass2`)

Pass 1 pushed the progress port (`23bc0777`), checkbox sync (`357e3d7b`), this shard (`78a63fe7`), the
wiki sweep (`f6a55b2b`), index pruning (`030d3c5f`) and archival (`1a70988e`). The events below came after it.

### What happened

1. **The AutoPilot merge train landed.** The operator pushed it, and orchestrator main is now `a1a0251a`. It
   carries:
   - MHS-3 (`6df6f0d8`);
   - AP-54 (the eval knowledge fence: `a8bdb15f`, `80fa99aa`, `0d3b6e26`);
   - AP-55 (a)–(d) in shadow mode (`203cb6e2`, `f057f1fb`, `e3e67696`, `f76e65cd`);
   - gate-frontier (c)+(b);
   - MHS-4/MHS-5 (`8219d8e8`, `4f28e6c3`) and the W3e axis-name reads (`635a3467`).
2. **Checkpoint prompt-leak RATIFY (MHS-3b).** The operator ran it. Pushed as root `b8379d42`: all 10
   checkpoint prompt copies were re-pinned to `18f8ea01`.
3. **API reload, then stop.** The main session:
   - stopped the old API (up since 09-15);
   - purged the live episodic store while the API was down;
   - started the new API with `orchestrator_stack.py reload orchestrator`, with no models loaded.

   Checks on the new API:
   - `/health` returns `degraded` with 0 models, as expected.
   - A bad `x_tool_mode` returns 422 and names `repl` or `client`.
   - `chat.py` imports `knowledge_fence`, so the AP-54 fence runs on every eval request.
   - Memory reports 64,204 entries (was 64,208).
   - The startup warnings are pre-existing: `kuzu` is missing, and 4 `archive_*` tool handlers do not resolve.
     Both are now filed (NIB2-78/79).

   The API was then stopped at the operator's request. **The API is DOWN.**
4. **Episodic eval-leak purge (MHS-3c).** The purge used orchestrator tool `41baad2b`; detail is in
   `2026-09-17-sub-episodic-leak.md`. Scope:
   - offline stores and state backups: 11 `episodic.db` copies and 15 state backups;
   - the live store;
   - the pinned `multitier_v10` store, with operator approval.

   `--verify` passes on all of them. Backups, run logs, the receipt and `pinned_repin_proposal.json` are in
   `/mnt/raid0/llm/backups/episodic-leak-20260917/`. A caller timeout cut the first offline run off at item 19
   with no damage (the original was intact); the re-run finished it. v10's `checkpoint_meta.json` still pins
   the pre-purge digests. The ratify script for that re-pin is ready (root `b4744e00`, MHS-3d,
   `scripts/operator/run_v10_episodic_repin_ratify_20260917.sh`) and **awaits the operator's RATIFY**.
5. **Operator rulings.**
   - **OP-INF40: A.**
     - The ruling queued the confirm after the AutoKernel window (`d3449013`, row `75d5e2a7`).
     - It was then retargeted to qwen4exp on champion `ef81196d5` (`6f346ea3`). This follows the operator's
       *plan* to promote the champion to production and qwen4exp to `architect_critic`; nothing has been done
       on that plan yet.
     - The main session corrected two wrong first-draft reasons about qwen4exp before recording.
   - **Security-review CI gate: dropped.** The handoff was moved to completed (`9804fec9`).
   - **OP-9: B, a pinned supervisor cron** (`cadf0cb5`). The operator installed it. It is verified
     idempotent: the cron log shows "another supervisor already holds" while daemon pid 639194 is alive.
   - The rulings were applied in `4d0c5d55` and `6f346ea3`; EV-13b was parked in `007e4092`.
6. **Five zero-inference subagents were in flight at this wrap-up**, each writing its own shard and box
   flips: HS-4 MCP fixes, AP-57/AP-63(a), VB wiring, D-f session lease + ETR-4, and UTM-P1 + EPD-3.

### Pass-2 wrap-up actions

- Ported `2026-09-17-sub-episodic-leak.md`, which was missing on origin/main. No other 09-17 shard differed.
- Checkbox flips (each verified against orchestrator `origin/main` ancestry or the purge receipt):
  - MHS-3c (the parent and the pinned-v10 sub-box);
  - MHS-4 and MHS-5;
  - AP-54 and AP-55 (AP-55-ARM and AP-54b stay open);
  - the RTG-47 "rationalize supervision with OP-9's resolution" task, done in this pass as a
    *Lifecycle and supervision* section in `dashboard/README.md`.
- New tasks (MHS-3d was drafted here too, but `b4744e00` filed it first, so this pass kept that version):
  - NIB2-78 (`kuzu` missing, so GraphEnhancedRetriever never runs);
  - NIB2-79 (dead `archive_*` registry handlers).
- The API being DOWN and the AutoPilot restart are not filed as tasks:
  - the operator asked for the API to stay down;
  - the restart is already the precondition of AP-55-ARM and VB-MHS-OPS-HOOK.
- The champion and qwen4exp promotions are an operator plan, recorded in `moe-spec-cpu-spec-dec-integration.md`,
  and were not filed as tasks.

## Evening (after pass-2 wrap-up) — zero-inference batch, landing audit, operator rulings

### Zero-inference work landed

Every item below passed the new landing gate: `git cherry origin/main <branch>` is empty in each repo.

| Task | Result | Commits |
|---|---|---|
| HS-4 P0-MCP-b | all 11 MCP tools take `session_id`; the P0.4 acceptance runner is prepared but not run | orch `54b6439d`, root `76917360` |
| HS-4 P0-MCP-a | root `.mcp.json` now uses the orchestrator venv. The operator applied the edit; the venv interpreter exists only inside the container | root `ed1dfd57` |
| HS-4 P0.4 preflight | operator installed `opencode-ai@1.18.31`. The Dockerfile pin is filed as a follow-up | root `de71a69a` |
| AP-63(a) | journal rows carry `run_manifest` and an explicit `lineage` parent | orch `0286c170`, root `df295516` |
| AP-55-ARM prep | `would_hold_enforce`/`would_hold_strict` recorded in shadow mode; `ap55_shadow_review.py`; shadow pinned in AUTHORITY_ENV. Not flipped | orch `cd79b80e` |
| AP-57 B (operator ruled B) | `speed_axis_reseed` ledger event, once per trial, replayed by `reconcile_baseline_ledger`, loud on write failure; the belief kernel deliberately does not project it | orch `01906607`, root `1d5f8cba`/`2d8ff334` |
| VB-AP-PROMO-RULE, VB-RUNNER-PATHS | adapter carries promotion_rule/frontier_admission/promotion_committed; `belief_capture.py` refuses a missing EPYC_ROOT | root `f71277f7`, research `0b295a25` |
| VB-RUNNER-PATHS-2 | tulving/occ1/beam scorers refuse loudly | research `ae92ac5c` |
| D-f | cross-process SQLite session lease with fencing (6 procs × 8 RMW = 48/48; 8/48 without the lease) | orch `0d6d1dd2` |
| D-f3 | graph snapshots were silently lost (signature mismatch); they now have their own `graph_snapshots` table and fail with a warning | orch `f853764f` |
| ETR-4/5/6/7 | guard test, `quality_unmeasured`, mock `tokens_generated`, dead imports | orch `1097a392`, `0399c3fe` |
| UTM-P1 | trace schema v2 pairing keys (harness/seed/turn_ordinal/task_key) | orch `dd24ed10` |
| EPD-3-R5/R6/R8 | routing cleanups | orch `d3f6062c` |
| NIB2-79 | 4 dead `archive_*` registry entries removed; a resolve test added | orch `0c03e658` |
| NIB2-78 | one warning line instead of a traceback storm; graph `close()` lock-release fix; `graph` extra. Operator ruled **A: kuzu stays uninstalled** | orch `61793b38`, root `1d5f8cba` |
| OBS-12, KB-WM-3 | skill interpreter hardening; index-graph provenance; audit-log gitignore fix | root `afb9745c`, `4120af69` |
| VB-PRB-T4 | closed by the main session (capture ran; driver on research main) | root `5d7a81fd` |

### Landing audit: 09-16 work that never reached main

A worktree cleanup found committed 09-16 work that had been reported and ticked but never landed.
The per-task wrap-ups had not verified landing.

| What | Resolution |
|---|---|
| 3 root vidya adapter branches (AP-54 fence, AP-55 gate, VB-AP53-RATE + SC83; about 1.3k lines) | landed as root `52b12f09` (merges `7d1ed3a5`/`48dc08b3`/`3671df47` plus `9d3d4f82`); 1391 vidya tests pass. Early ticks were corrected: VB-AP53-RATE and SC83 re-dated, AP-54 and AP-55 given notes |
| Research GPU evidence (SL-1/SL-5/DF2-6/CJ-1e/§5 pre-reg) | already on main under the collector commits `8146880b`/`6cbdd856`; 43 citations annotated (root `85af3ae4`) |
| INF-61 fence fix | missing from main's driver port, so main could not reproduce its own evidence; ported as research `c6e63877` |
| INF-70 evidence docs | landed as research `56ef1404` |
| 7 one-off drivers, 2 raw completion files, SL-2 (autokernel-owned) | declined; backed up as `preserve/2026-09-17/gpu-runner-20260916` and `gpu-prep-20260916` on research origin |

About 54 merged worktrees were removed (root plus orchestrator). A new standing rule was saved to
memory (`feedback_wrapup_must_verify_branch_landed`): a task is done only when `git cherry` is empty.

### Operator actions and rulings

- The v10 episodic re-pin was RATIFIED (root `810a6a82`), closing MHS-3d. The eval-leak cleanup is
  therefore complete on every store: live, offline, and pinned production_best.
- OP-KUZU was ruled A and OP-AP57 ruled B; both rows were removed (root `bee2f36a`).
- OP-AP57 had been filed in root `52dfc3cc` after the ap57 agent found that "B" was only a recommendation.

### State at close

- The API is DOWN (operator request) and AutoPilot is stopped.
- No GPU work until the operator signals. Ready at that point: INF-61 A/B/A, the OP-INF40 confirm on
  qwen4exp with the champion, the HS-4 P0.4 live acceptance (API reload first), the PRB-T4 re-run, and
  the ERNIE next hypothesis.
- Branches deliberately still off main: research `sub/akfix-20260916` (held AutoKernel fix `38d82ebe`,
  owner decision), plus the preserved one-off drivers.
