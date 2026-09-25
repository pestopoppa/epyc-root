# 2026-09-25 — main-ak-seat (overnight: DS41 run 9 → stop → ctx A/B → run 9b)

Overnight window 2026-09-24 20:15Z → 2026-09-25 04:05Z. The evening build and its learnings are in
`progress/2026-09/2026-09-24-main-ak-seat.md` (*Reduced-scope planner build*, root `a32ba396`/`dcadbe72`). This
entry starts where that file stops, at "run 9 LIVE". Owning handoffs:
- INF-77, `handoffs/active/deepseek-v41-flash-evaluation.md` (DS41 §C);
- INF-78, `handoffs/active/autokernel-orchestrator-actor-backend.md`.

Running plan: `/mnt/raid0/llm/tmp/stack-window-plan-20260924.md`.

## DS41 run 9: refused, fresh store, launched

- **First launch REFUSED at 20:14Z.** The store's champion of record was the old port anchor `ebb68dc55`, not the
  anchor `5a60152ae` (0 keeps, 1 experiment row). **The run-9 dry run (rc=0) never checks this.**
- **The operator approved the fresh-store route**, following the DS41-C13 precedent:
  - the store is archived as `store-run8-cor-ebb68dc55/` (`ARCHIVED.txt`; reversible);
  - a fresh `store/` carries over `inbox/`;
  - the refused state dir is kept as `state-run9-refused-cor/`.
- **Run 9 launched 20:14:55Z**: `serial_run` 2580766, `run.py` 2580771, `state-run9/`, research `6afc7eed`,
  target `ds41-5a60152ae-cpu-t48-dspark-b2`, :8083 on `-kvu` (196,608-token slot).

## Half-screen floor (00:25Z)

- Location: `store/runtime-source-floors/5b995a27…/3a0b8832…/serving-floor.ds41-5a60152ae-cpu-t48-dspark-b2.cpu-half-….json`.
- Setup: cores 0-47, `-t 48`, `matched_process_v2`, 48 launches, one every ~4.7 min.
- **Floor 5.789%** (interval 2.91-9.55%), between-launch SD 2.79%, MDE 3.0%. Run 7's floor on the old anchor was
  5.097%.

## Loop order learned (the pre-launch plan was wrong)

- **The real order:** half floor → batch 0's half-screen PROPOSAL and its measurement → batch 1's full-target
  calibration (~4 h, every CPU region lock).
- **The plan's assumption:** both floors back to back (~8.5 h). That was wrong.
- **Consequence:** an evening launch puts the full-target calibration into the next day.
- Recorded in DS41-C25 (run 9 / 9b block), DS41-C28, and `docs/guides/agent-workflows/agent-loop-design.md` →
  *Launching and stopping a DS41-style serial run*.

## Run 9 stopped at the boundary (01:30Z)

- **When:** at the half-floor → batch-0 boundary. The batch-0 planner had been live 61 min on the old inline
  code, and that call was discarded.
- **How:** TERM to `run.py` 2580771 and `serial_run` 2580766. Everything died, including opencode 3054534, with
  no KILL.
- **The DS41-C22 stop path works on a live actor call.** Its record is the first `actor-calls.jsonl` line, an
  `actor_call.v1` with rc −15 (this closes DS41-C24).
- The CPU locks were freed, and `state-run9/STOPPED.txt` was written.

## Research main and shared clone

- **Research main fast-forwarded** `170c763c` → `30631761` (`lane/ak-planner-integ-20260924`), pushed under the
  push lock.
- **Contents:** perf cache `f4a5d240`, ctx-variable `ce5800cb`, turn metrics `0bf2d7c2`, pre-existing test fixes
  `535391b6`, `node_profile` render in both modes `8a9d2a40` (DS41-C20e), metrics hardening `30631761`.
- **The shared clone was fast-forwarded after run 9 was dead.** Other sessions' dirty files were left untouched.

## INF-78 OAB-9: context-placement A/B — INLINE wins

**Setup.**
- Driver: `/mnt/raid0/llm/tmp/ak-ctx-ab/driver.py`, 2 ABAB pairs, 01:28Z → 04:03Z. Pair 3 needed 71 min and did
  not fit the 3.5 h budget.
- Seat and server: plain opencode seat; :8083 Qwen3.8-27B Q8_0, one server generation (pid 2009477, `-kvu`,
  `n_ctx_slot` 196,608).
- Prompts: the inline control is run 8's prompt plus `node_profile` (79,890 chars, sha `a265a03a`); the variable
  arm's prompt is the index only (18,055 chars).

| | inline p1 | inline p2 | variable p1 | variable p2 |
|---|---|---|---|---|
| wall (min) | 37.6 | 28.7 | 54.4 | 33.6 |
| steps | 23 | 24 | 49 | 29 |
| tool calls | 25 (bash 22, read 3) | 26 (bash 21, grep 1, read 4) | 54 (bash 35, read 19) | 35 (bash 26, grep 1, read 8) |
| decoded | 52.9k | 43.8k | 68.9k | 47.7k |
| first / peak context | 40.6k / 104k | 40.6k / 92k | 19.1k / 163k | 19.1k / 118k |
| compactions | 0 | 0 | 0 | 0 |
| reply (all schema-valid) | abstain | hypothesis `akm-q4k-x4-avx512` | abstain | abstain |

**Bundle use and contention.**
- The variable arm used the bundle as designed: 6-7 bundle calls, all 3 required files read, 0 `INDEX.md`
  re-reads.
- It also read **all six file-only sections**, then explored lane source more (3-4x inline's tool output).
- Contention was negligible: 6 of 132 (inline) and 2 of 172 (variable) `/slots` samples had another slot busy.

**Predictions checked:**
- first-step context halves: **confirmed**;
- peak falls: **refuted**;
- 0 compactions instead of 1: **moot**, because inline no longer compacts on the 196k slot;
- wall gain: **refuted**.

**Learnings** (written into INF-78 §Techniques learned → 4 and the agent-loop guide):
- a thin prompt made the 27B explore MORE, so context placement alone does not reduce work;
- the RLM-style benefit presupposes a model or scaffold that pulls precisely;
- with 196k slots, compaction is no longer the binding cost;
- the next levers are the fixed overhead (OAB-10), lane reads and never building (OAB-11), and
  orchestration-side scouts (OAB-8), not hiding context.

**Limits.** n=2, and inline always ran first. A 3rd pair, a different model, a small slot, or pull caps could each
change the verdict (OAB-9b).

**Evidence:** research `605e8301` + `135b8492` + `0ac0b0c0`, `artifacts/autokernel_ctx_ab_20260925/`:
- README with the table, verdict and caveats;
- `driver.py`, the log, `results.jsonl`, the per-call results and `actor-calls.jsonl`;
- the two variable-arm bundle manifests and indexes.

The exports and bundle sections stay under `/mnt/raid0/llm/tmp/ak-ctx-ab/`.

## Run 9b launched (04:04Z)

- **Processes:** `serial_run` 3279632, `run.py` 3279639, `state-run9b/`, same store, research `30631761`.
- **Mode:** default **inline** (the winner), now with `node_profile` and per-call metrics.
- **`EPYC_ROOT_REPO`** = `/mnt/raid0/llm/worktrees/root-main-epyc-root-repo`, a detached root `origin/main`
  checkout, not a lane.
- **The half floor was reused.** The run went straight to the planner call (opencode 3284175, 04:09Z) with no
  re-calibration.
- **Known daytime impact.** Batch 1's full-target calibration (~4 h, every CPU region lock, blocks :8070 and the
  CPU speech cores) follows batch 0's proposal and measurement, so it will likely run mid-day on 2026-09-25
  (DS41-C28).

## Root documentation (this wrap-up)

| File | Change |
|---|---|
| `handoffs/active/autokernel-orchestrator-actor-backend.md` (INF-78) | `[x]` OAB-9. New §Techniques learned → 4 (A/B table, predictions checked, learnings, what could change the verdict). OAB-7 status: built, A/B'd, loses on the 27B plain seat. OAB-7s/4m/R4c merge status. OAB-12 progress. New `[ ]` OAB-9b |
| `handoffs/active/deepseek-v41-flash-evaluation.md` (INF-77) | `[x]` C20e, C20h, C24. Run 9 / 9b block under C25 (refusal, fresh store, half floor, loop order, stop, relaunch). C10a and C25 launch-line halves recorded; both stay open on run 9b's first planner reply. C11 re-check. New `[ ]` C27 (dry-run COR check) and C28 (batch-1 calibration off-hours) |
| `docs/guides/agent-workflows/agent-loop-design.md` | Run-9 launch lessons (loop order, COR refusal, `EPYC_ROOT_REPO`, stop path). A/B result and learnings in *Context as files*. Two unresolvable backtick references fixed so the reference guard passes |
| `scripts/vidya/adapters/README.md` + `handoffs/active/vidya-belief-substrate-program.md` | The metrics and bundle producers are now merged. VB-AK-METRICS-1 and VB-AK-CTX-1 updates point at the first post-hook rows and manifests |
| `handoffs/active/tool-output-compression.md` | TOC-RD-1b recurrence: the PII hook rewrote 14 perf-period cells in `135b8492` |
| `progress/2026-09/2026-09-25-main-ak-seat.md` | this file |

## Checklist sync / derived actionables

- **Flips: 4** (INF-78 OAB-9; DS41-C20e, C20h, C24).
- **Kept open on purpose:**
  - C10a and C25: their launch-line halves are satisfied, and their remaining clause is run 9b's first planner
    reply, in flight at wrap-up;
  - C11: `test_serial_roster` still fails 3 tests on `605e8301`, while `test_existing_cpu_run` now passes.
- **Filed: 3 new tasks** — DS41-C27, DS41-C28 and INF-78 OAB-9b.
- **Extended: 5** — OAB-7, OAB-12, VB-AK-METRICS-1, VB-AK-CTX-1 and TOC-RD-1b.
- **Declined: 3.**
  - A 3rd A/B pair on the unchanged setup: 2/2 on every cost metric, so it folds into OAB-9b's trigger.
  - A separate belief-kernel source for the A/B driver's `results.jsonl`: its columns are the
    `actor_call_metrics.v1` rows (VB-AK-METRICS-1) plus bundle reads (VB-AK-CTX-1).
  - Re-running the bounded arm now: that is DS41-C20d2, already filed. The A/B tested placement, not the seat.

---

# 2026-09-25 daytime — main-ak-seat (04:30Z → ~15:55Z: runs 9b-10, INF-78 build-out, fast loader, Vidya reader)

Running plan: `/mnt/raid0/llm/tmp/stack-window-plan-20260924.md`, entries from "04:26Z WRAP-UP DONE" on. Owning
handoffs: INF-77 (DS41 §C), INF-78, INF-65 (V6R-4), and the Vidya program (VB-AK-BELIEF).

## DS41: run 9b killed by STOP, idle CPU, runs 9c and 9d, re-anchor, run 10

- **04:26Z run 9b killed by a misused `STOP`.** `serial_run` forwards SIGTERM to `run.py` as soon as it sees
  `STOP`; the batch-0 planner call died at ~18 min (`stopped_mid_formation`). Recorded in DS41-C28 (root
  `8eb57a2c`).
- **The CPU then sat idle 04:26Z → 07:15Z,** held for an "off-hours" relaunch. The operator's correction: nothing
  else uses compute besides AutoKernel, so there is no off-hours constraint. DS41-C28 is closed as moot on that
  ruling.
- **Run 9c (07:15:54Z).** Its first planner reply (08:05Z: 36.8 min, 29 steps, 47.3k decoded, peak context 111,116,
  schema-valid, rc 0) closes DS41-C10a and DS41-C25. The proposal, the Q4_K/Q5_K activation-scale hoist out of
  `mul_mat_qX_K_q8_2_X4_T`, was accepted twice by the Codex critic and then silently dropped by `gates.op_scope`.
  Run 9c was stopped ~08:56Z on the operator's order, for the OAB-10/11 A/B.
- **Why the proposal was dropped (DS41-C29, research `c7215eb5`).** The gate required `unpack_q4_scales*` markers
  that exist only in the keeps-v10 tree, so the ~30%-of-cycles kernel was unreachable on the DS41 anchor: 0 of ~15
  attempts across runs 3-9c ever built. The fix admits both layouts and records every abandoned candidate with its
  retained patch.
- **Resume (DS41-C30, research `1ef55655`)** plus backfill row `eab36f3e`. Run 9d (~10:53Z, research `300951de`,
  control listener `:8471`) resumed the hoist at build and failed on `RatchetRefused`, which consumed the claim.
  Fixed by DS41-C31 (research `71c46655`): reuse the retained patch, an infrastructure `lane_error` releases the
  claim, and a `resume reopen` CLI.
- **Run 9d killed ~14:40Z on the operator's order** (TERM drained; KILL cleared `serial_run` 348518 and `run.py`
  417443). A control-API pause requested at 12:27Z never landed, because the calibration batch was still running.
- **Run 10 (15:26Z, DS41-C32).**
  - Anchor `00d118d44` = the DS41 port + champion `90c12df42` (fast loader).
  - Fresh store; the old one is archived as `store-run9d-cor-5a60152ae/`. The inbox carries both retained hoist
    patches.
  - Inputs r5; code root is the dedicated research worktree `/mnt/raid0/llm/worktrees/research-ds41-run10` @
    `67cac838`; control listener `127.0.0.1:8471`; `serial_run` 2762645.
  - **Calibration launches took 163 / 170 / 167 s, against ~282 s before.** Next: DS41-C33.

## Fast loader: a lost feature re-ported, and the champion advanced

- **We built parallel repack in December 2025** (`52ddd3200`; upstream PR #18239 closed unmerged). It was lost when
  v6 Stage 1a `814e81782` was reverted as a whole. Incident: INC-20260925 in
  `docs/reference/agent-config/INCIDENT_LOG.md` (root `fe63adbb`, verified on origin/main).
- **Re-ported onto the champion.** `25132e042` is the repack re-port (test restored, 150/150 bit-exact). `90c12df42`
  adds a parallel pread reader as an OpenMP team (`--load-threads`); the old loader thread had been pinned to CPU 0.
  Both are bit-exact; the 27B loads 3.2x faster warm and 2.1x cold.
- **Champion advanced** `ak/champion/llama-cpp-ffc1bac82eec` `2b57340bf` → `90c12df42`, pushed to the fork;
  workspace-8d was notified.
- **Gates:**
  - DS41 load: 254 / 278 s → 98.2 s, with a 263 s single-thread control on the same binary.
  - Decode A/B cut by the operator after one pair (0.99, identical output).
  - Builds: `kernels/builds/cpu-20260925-{90c12df42,2b57340bf}`.
- **Evidence committed in this wrap-up:** research `a5906f24` (`data/champion-advance-fastload-20260925/`). It was
  untracked in the shared clone; those copies were moved aside, checksum-identical, to
  `/mnt/raid0/llm/tmp/research-untracked-backup-20260925/` so they cannot block the clone's next fast-forward.
- Filed: INF-65 V6R-4 `[x]`, V6R-4a (carry into v11), and V6R-4b (operator ratification of the one-feature-per-commit
  rule, proposed OP-58).

## INF-78: the orchestrator backend, built and deployed

- **OAB-1 + OAB-3:** orchestrator `9124c7f1`, plus Fable review fixes `7f5d6870`. **OAB-2:** research `751ec730`
  and CLI `e33eb1d3`. Orchestrator main `994529fd`; API reloaded 08:28:41Z; smoke PASS ×3; witness quiet.
- **OAB-10/11** (research `bdd0a951`): fixed overhead 12,912 → 4,950 tokens per call. The trimmed call took 6
  steps and 10 tools, with ctx_first 32.7k. The baseline arm was aborted at 54+ min (censored), and the A/B stopped
  after one trimmed call.
- **OAB-7 (context bundle as a REPL variable):** turn-1 root prompt −74%. **OAB-8:** scouts. Integration went
  through a second Fable review (F1-F7 and F12-F14 fixed). The operator's scoped architect-REPL exception is
  `7d0ce447`. Orchestrator main `b9e004e3`.
- **API reloaded 14:40:38Z** (pid 2517073) after run 9d was killed; OAB-2 smoke PASS; witness quiet.
- **Production-visible with that reload:**
  - the `auto_wrap_final` one-line-print fix;
  - the schema preamble reaching the model (with `final_schema_validation` on);
  - the proactive stage no longer answering scoped or bundle requests before the REPL;
  - REPL sandbox refusals of frame attributes, `attrgetter`/`methodcaller` and dunder-reaching `format`.
- **The opencode store fault** that failed an author call was root-caused to the reaper's no-op VACUUM. Fixed in
  root `9177edaa` and research `e57e93ea` (`snapshot: false`, `OpencodeStoreError`).
- **Planner timeline audit:**
  - decode is 87% of wall; one 30k-token reasoning turn was 68% of a call;
  - `--variant high` is inert;
  - thinking IS on through the template, and `tokens.reasoning = 0` is an accounting artifact;
  - operator: reasoning stays on, no thinking A/B.

  The giant final turns re-derive the Q4_K bit-unpack formulas. Recommended and filed: a concision rule plus an 8k
  per-turn cap (OAB-22), and a separate per-call budget (OAB-23).
- The live OAB-4 A/B is next.

## Vidya: a generic belief-kernel reader

- **The operator directed a generic reader, not a hypothesis seed,** and moved the KV-quant planner wiring to
  main-ak-seat (workspace-8d agreed). Codex owns AutoPilot and asked us to own the AutoKernel side.
- **Research `lane/belief-reader-20260925` @ `56cb9493`, unmerged:** the generic reader, receipts and reliance.
  It also retires the KV-quant-specific block that reached research main via `0555cd2b`.
- **The receipt proposal** (`/mnt/raid0/llm/tmp/vidya-planner-receipt-proposal-20260925.md`) awaits Codex
  sign-off.
- **Blocking defect:** the producer writes `summarize_cell` stats dicts where the root adapter requires scalars.
- Root `fa8d0fa1`: VB-AK-SEAT accepts the orchestrator kind; research `67cac838` updated the fixture.
- Filed in the Vidya program as VB-AK-BELIEF-1, VB-KVQ-V10-DICT, VB-APPLICABILITY, VB-INGEST-IDEMPOTENT and
  VB-AK-RELIANCE-REVIEW. Every one that touches root `scripts/vidya/` is marked as needing Codex coordination.

## Root documentation (this wrap-up)

| File | Change |
|---|---|
| `handoffs/active/deepseek-v41-flash-evaluation.md` (INF-77) | `[x]` C10a, C25 (run 9c's reply), C28 (moot by operator ruling), C29-C32. Runs 9c/9d/10 block. C27 re-noted. New `[ ]` C33 (run 10 first results), C34 (delete the partial build dir once the operator confirms). Stale status line refreshed |
| `handoffs/active/autokernel-orchestrator-actor-backend.md` (INF-78) | `[x]` OAB-1, 2, 3, 10, 11, 13, 14, 20. 2026-09-25 operator rulings section. OAB-4/7/8/9b/12 status. New `[ ]` OAB-15 (store decisions, proposed OP-59), 16 (scout tap record), 17 (review remainder), 18 (`PREFIX_STABLE_ORDER`), 19 (compaction target), 21 (reasoning accounting), 22 (concision + 8k cap), 23 (per-call budget) |
| `handoffs/active/autokernel-champion-aggregate.md` (INF-65) | `[x]` V6R-4 (fast loader + champion advance). New `[ ]` V6R-4a (carry into v11), V6R-4b (rule ratification) |
| `handoffs/active/vidya-belief-substrate-program.md` | VB-AK-SEAT-b1x research side done. New VB-AK-BELIEF section: 5 `[ ]` tasks, with Codex coordination marked |
| `docs/guides/agent-workflows/agent-loop-design.md` | *Operating lessons from runs 9c-10*: never idle compute, pause through the control listener, dedicated research worktree, resume, disposition log, load cost, reasoning accounting |
| `progress/2026-09/2026-09-25-main-ak-seat.md` | this section |

Research, this wrap-up: `a5906f24` (the fast-loader gate evidence).

## Checklist sync / derived actionables

- **Flips: 16** (the gate's grep count). DS41: C10a, C25, C28, C29, C30, C31, C32 (7). INF-78: OAB-1, 2, 3, 10,
  11, 13, 14, 20 (8). INF-65: V6R-4 (1). C29-C32, OAB-13, OAB-14, OAB-20 and V6R-4 are new `[x]` lines for work
  finished this session.
- **Filed open:** DS41-C33, C34; OAB-15, 16, 17, 18, 19, 21, 22, 23; V6R-4a, V6R-4b; VB-AK-BELIEF-1,
  VB-KVQ-V10-DICT, VB-APPLICABILITY, VB-INGEST-IDEMPOTENT, VB-AK-RELIANCE-REVIEW (17).
- **Kept open on purpose:**
  - OAB-4/7/8: built, but their acceptance is the live OAB-4 A/B;
  - OAB-12: the seat-side per-section bytes;
  - VB-AK-SEAT-b1x: needs a real `orch:` campaign call;
  - DS41-C27: the dry run still skips COR, and run 10 needed the manual route again.
- **Declined: 4.**
  - A task to make `--planner-effort` meaningful: the effort knob cannot bound reasoning on this server, and
    OAB-22's rule plus cap is the lever. Folded there.
  - A thinking on/off A/B: the operator ruled reasoning stays on.
  - Finishing the cut decode A/B now: the operator cut it; the full pair count moves to the v11 promotion gate
    (V6R-4a).
  - A belief-kernel source for the fast-loader gate files: a one-off promotion-gate record, not a recurring
    producer. Per-launch load time already lands in the loop's own calibration records.
