# 2026-08-13 — coordinator-agent pickup + fleet re-instantiation (session 2)

## Session purpose

Prior coordinator session (opencode pid 1598123, run `2e77f75d`) stopped mid-day. Operator
instructed: pick up where it left off, re-instantiate mainA/B/C/D on **hosted DeepSeek V4 Flash**
(API key, not the free tier), and have the auditor audit all completed work and deliver updates to
relevant handoffs so the dispatch loop returns the auditor's drafted tasks to mains.

## Crash investigation (F-43, filed in coordinator-role-failure-modes-and-refactor.md)

**The prior coordinator was NOT crashed — it was SIGSTOPped.** Evidence:

- Process state `T` (stopped), all 121 threads stopped, wchan `do_signal_stop`. Parent `fish`
  (14147). Fresh opencode launched in the same window at 13:05:51 (this session).
- Trigger: 12:57:58 → 13:00:00Z, `AI_APICallError: Rate limit exceeded` on
  `opencode/deepseek-v4-flash-free` ×4+ (mainA, mainB, the coordinator's own stream at 12:58:05,
  mainC). The free tier could not sustain 5 concurrent mains + coordinator.
- Secondary wedge: opencode composer mis-detection. Short nudges to mainD repeatedly failed the
  adapter's pre-Enter verification; the doorbell text was left unsubmitted (operator had to press
  Enter manually for the auditor message).
- Fix: **switched mains to hosted `deepseek/deepseek-v4-flash`** via `main-max.md` agent file.

## What I did (this session, 13:06–13:30Z)

1. Cold-start reconstruction (Phases 0–2): daemon HEALTHY (epoch 68, pid 1486558, supervised),
   supervisor alive (pid 1483558), fleet_watch running (pid 760637). tmux session `agent` had
   windows htop/btop/coordinator/inference/auditor — mainA–D windows gone. verify_llama_cpp
   context from prior session: PASS.
2. Crash investigation (above) — filed as **F-43**.
3. **Re-instantiated mainA/B/C/D** on hosted DeepSeek V4 Flash:
   - `main-max.md`: `model: opencode/deepseek-v4-flash-free` → `model: deepseek/deepseek-v4-flash`
     (variant high, temperature 0). Verified the hosted provider works (this session's own log:
     `providerID=deepseek modelID=deepseek-v4-flash`).
   - Spawned all 4 via `tmux_adapter.py spawn --agent <id> --command 'cd <worktree> &&
     /home/node/.opencode/bin/opencode --agent main-max'`. 7/7 mains live.
   - Probes resolve all 4 (endpoint `agent:<id>` verified, pane_dead False).
4. **Dispatched mains** to their assigned rows with briefs in `coordination/session-bus/tasks/`:
   - mainA → `opendataloader-pipeline-integration--011-L512` (brief `mainA-resume-011-20260813.md`)
   - mainB → `opendataloader-pipeline-integration--013-L534` (`mainB-resume-013-20260813.md`)
   - mainC → `repl-turn-efficiency--Prefix-L107` (`mainC-resume-prefix-20260813.md`)
   - mainD → `opendataloader-pipeline-integration--P2-L615` (`mainD-resume-p2-20260813.md`)
   - All 4 nudged (short messages — long ones fail the opencode composer gate, F-41). All 4
     confirmed working (mainA wiring intrinsic metrics into `comparison.py METRIC_ORDER`; mainB
     exploring ODL-013; mainC preparing RTE-Prefix live A/B + compute-request; mainD on ODL-P2).
5. **Dispatched auditor** to audit mainA–D completed work and update handoffs:
   - Brief `auditor-audit-mainAD-20260813.md` — emphasizes the loop: auditor persists to handoffs
     (checkbox flips + newly drafted `- [ ]` rows); dispatch machinery re-scans handoffs
     (`backlog_queue_gen.py --generate` + intake) and routes drafted rows to idle mains. Auditor
     NEVER messages mains directly (cleared contexts).
   - Doorbell rung (payload nudge refused by a runtime false-positive: codex rollout tail stuck at
     `thread_settings_applied`). Auditor confirmed working (re-running odl_bench tests, 26 passed).

## Coordination finding routed (mainC, 13:19Z)

**Inference (compute grant authority, rule 11) is unreachable on the bus**: heartbeat 14h+ stale,
codex session never drains. 8 unread messages in `inbox/inference.jsonl` including 6+ compute
requests (mainA A7 + contention rebench, mainB ODL-013, mainC RTE-Prefix ×2, mainD ODL-P2). All 4
CPU regions are now FREE (autokernel released ~13:17Z) yet no grant can be issued. mainC correctly
prepared compute-independent work (analysis template + decision criteria) while waiting. Routed to
operator in this session's report.

## Pending / next actions

- [x] Re-instantiate mainA/B/C/D on hosted DeepSeek V4 Flash (approved, done 13:11Z).
- [x] Dispatch mains to rows + auditor to audit (done 13:13–13:20Z).
- [x] File F-43 (crash investigation) in coordinator-role-failure-modes-and-refactor.md.
- [ ] Present 10 pending operator tokens.
- [ ] Resolve 16 action_required items owed by me (inference decision-requests) — stale, need
      disposition.
- [ ] Run `backlog_queue_gen.py --generate` + `session_bus_coordinator.py intake` after auditor
      completes, to admit its drafted rows to the queue.
- [ ] Operator decision: inference's bus unreachability — nudge manually / accept compute parked
      until its campaign ends / relax rule 11.
- [ ] Update post-reboot-session.md handover brief at wrap-up.

---

## Session 3 wrap-up (17:30Z–22:30Z, same day)

### What I did

1. **Cold start** (17:30Z): daemon HEALTHY (epoch 71), mainA–D windows gone, inference + auditor
   live. Spawned mainA/B/C/D on hosted DeepSeek V4 Flash. 7/7 mains.
2. **Wave-1 dispatch**: mainD → compute-request schema kinds (landed `5aae0c35`); mainA →
   paddleocr default-binary + ODL-011; mainB → A14 merge (landed `c61b8184`) + ODL-013; mainC →
   regen-screen-queue (proposed 17 rows); auditor → gate-receipt audit.
3. **Fixed the auditor launch model typo**: `gpt-5.6-sol-high xhigh` → `gpt-5.6-sol high`, in 4
   places on `lane/auditor` (commit `f846f9b9`).
4. **Found + fixed two daemon bugs** (details in failure-modes handoff):
   - **Role-constraint mis-assignment** (`240251bf`): auto-assign handed backlog to the auditor
     (reviewer), hardware-backfill (service) and coordinator — only `role=main` is schedulable now.
   - **STALE_REQUEUED black hole** (`ced09eba`): `apply_assignment`'s write path accepted only
     `READY` while `_eligible` admitted `STALE_REQUEUED`, so lease-expired rows were picked every
     tick and never assigned (`scheduling-pick-undelivered`, 20+ ticks). Aligned with
     `ASSIGNABLE_STATUSES`. Daemon restarted to epoch 73.
5. **Ran intake**: 17 rows from mainC admitted (screened + occupancy auto-derived). Queue went from
   stuck to draining continuously.
6. **Compute-release coordination** (operator released all compute ~22:14Z): 4-way parallel
   dispatch on disjoint resources — mainD P2-L615 demo (GPU MI210), mainA A7 grid (q0+q1), mainB
   K-LCM-1 (q2), mainC DCP-6 (q3). Queued behind: CJ-1d/1e, Parser-quality, S4, R1a, ODL-011/013,
   mainA contention re-bench.
7. **Authored the wrap-up division-of-labor policy stub** (`wrap-up-division-of-labor-policy.md`,
   RTG-51) — log skill for worker mains, auditor full wrap-up (indices + wiki), coordinator
   self-wrap-up; graded compute-window consumption model.
8. **Filed F-33..F-36** in `coordinator-role-failure-modes-and-refactor.md` (lost track of mains;
   unrouted auditor audits; auditor doorbell failure; declined ghost-prompt finding).

### Operator decisions this session

- **Push policy**: docs/handoffs pushes LIFTED; kernel/orchestrator code still held.
- **A9 PyTorch-ROCm**: authorize install, owner = inference.
- **Compute window**: graded (small-model / load-then-keep-hot / full-idle), not binary.
- **Wrap-up standardization**: park for later (log-skill design agreed, not encoded).

### Fleet state at wrap-up

- Daemon epoch 73, auto-assign now delivering. Queue: 13 READY + 11 STALE_REQUEUED, draining
  continuously as regions clear.
- mainA RUNNING AK-RUN-2 → A7 (q0+q1); mainB AK-RUN-1 → K-LCM-1 (q2); mainC S-11 → DCP-6 (q3);
  mainD CJ-1c → P2-L615 demo (MI210). Auditor on audit-completed-wave1-2.
- inference: autokernel discovery-first controller (Terra rewriting, Sol reviewing); compute
  released by operator.

### Pending / next

- [ ] Watch the 4-way compute dispatch; re-dispatch queued rows (CJ-1d/1e, Parser-quality, S4, R1a,
      ODL-011/013, contention re-bench) as regions clear.
- [ ] Diagnose why the coordinator-agent itself shows `stuck-unreachable` (composer/opencode
      delivery) — same C51 family, fix uncommitted.
- [ ] Encode the wrap-up division of labor (log skill) when picked back up.
- [ ] Reconcile the stale "each main writes its own wrap-up" rule in the post-reboot brief.
