# 2026-10-03 — workspace-ec (renamed from workspace-8d after the host reboot)

This session was workspace-8d until the host went down (~2026-10-01 20:57Z to ~10-03 03:20Z). Its 2026-10-01 work is in
`2026-10-01-workspace-8d.md`. This file starts with the 10-01 evening results that the outage kept out of a wrap-up.

## RI-18 review gate: scored, verdict DROP (complete, 2026-10-01 18:53Z)

- The pinned revise redo finished 90/90 in workspace-76's granted gap: orch `08edc054`, detached worktree
  `orch-ri18-pin-08edc054`, segment `revise-20261001T181047Z-1960bd`, end `exit 0`. `score` ran automatically.
- **Decision DROP, pre-registered clause 1.** π1 (review every eligible answer) has a net of **−38.3 per 100 items,
  95% CI [−42.7, −34.0]**: 12 fixed, 234 broken, accuracy 72.2% → 33.9%. Split B is [−44.8, −32.4].
- The production gate πQ(0.6) never fires: 0 eligible triggers, net 0 [0, 0], so it is untested under BOUNDED-NULL-1.
  t* = 0.30, a tie at net 0. AUROC of −avg_q is 0.558 [0.511, 0.607]. n_primary = 579 (608 items; 29 HTTP errors).
- Mechanism: the cap-300 reviewer flags most correct answers WRONG (specificity 0.21 / 0.25 on A / B), and
  `worker_general`'s rewrite breaks 70-75% of those.
- The secondary rule reads HOLD_CAP_300: `question_cap=1500` does not land.
- Evidence: `/mnt/raid0/llm/tmp/ri18/run-v1/score.json`, `/mnt/raid0/llm/tmp/ri18/score-final.log` and the 6-row
  `belief_measurements.jsonl` sidecar.
- Derived:
  - **RI-18c** applies the DROP: remove the gate, verdict and revision from the five call sites and
    `review_low_q_threshold`; C1-C3 go with it.
  - **VB-RI18a**: the sidecar lacks the orch commit and store sha its adapter contract requires, and the run lives in
    scratch.
  - Declined: RI-18a/b (the instrument is retired) and VB-REVIEW-GATE (its producer is being deleted).
  - The TE-reopen note: after RI-18c, A2 has no review-gate trigger.

## ARCHSWAP-4: `:8074` relaunched under its own label (complete, 2026-10-01)

- `orchestrator_stack.py reload architect_general` ran from 18:10:45Z to 18:12:51Z, in the same gap as the RI-18
  redo. It gave PID 292218, slot dir `/mnt/raid0/llm/cache/kv_slots/architect_general`, and /health ok.
- `status` afterwards showed every model server with attest `ok`, i.e. 0 drift. Only ARCHSWAP-3b (the A-3 frontdoor
  scout-stage claim sample) is left of the ARCHSWAP residue.

## Lost cross-session messages while idle (2026-10-01, note only)

- The session went idle awaiting an operator decision. workspace-76's bus messages queued at 19:10Z and 20:01Z were
  never processed before the host went down at ~20:57Z.
- An idle session does not drain its inbox. Nothing acted on those two messages before the outage. Re-read them from
  the bus rather than assuming they were handled.

## Post-reboot stack restart (2026-10-03 ~03:5xZ)

- The production stack is back up, with every model server attest `ok`.
- DS41 holds all CPU regions in closed windows, so the frontdoor `/chat` serving proof waits for a DS41 open window.

## `start --dry-run` launched the production stack (fixed, orch `99e3e5fe`)

- On the freshly rebooted host, `orchestrator_stack.py start --dry-run` without `--migrate-to` started the whole
  stack. Only the `--migrate-to` path reads `--dry-run`. It was benign because a start was intended next anyway.
- Fixed in orch `99e3e5fe`, which refuses the combination (exit 2) and adds tests that drive `main()` with
  `cmd_start` booby-trapped. This is the same class as the 2026-08-12 inert `--validate-only`.
- Incident: `INC-20261003-start-dry-run-launched-stack`. Filed SCG-INERT-FLAGS, a structural sweep for other
  parsed-but-unread flags.

## `repl_embedding_pool` came back ON after the reboot (reset)

- `POST /config` writes persist in `orchestration/runtime_flags.json` across API restarts and reboots. So the
  2026-10-01 runtime enable for `orsv` survived the outage, against the REPL-EMB-2.1 kill rule's OFF default. It was
  turned OFF this morning (record stamped 03:51:31Z).
- Incident: `INC-20261003-runtime-flag-survived-reboot`. Filed REPL-EMB-4.5: an experiment enable carries an expiry
  or an explicit restore step.

## DFlash2 stack change

- The DFlash2 stack change for the 27B is in packaging for the operator's signature (stack-change package; nothing
  applied).

| Repo | File | Change |
|---|---|---|
| epyc-root | `handoffs/active/routing-intelligence.md` | RI-18 ticked with the DROP verdict; RI-18c filed; RI-18a/b declined |
| epyc-root | `handoffs/active/thesis-experiment-orchestrator-vs-strongest-model.md` | ARCHSWAP-4 ticked; residue line; TE-reopen RI-18 note |
| epyc-root | `handoffs/active/vidya-belief-substrate-program.md` | VB-REVIEW-GATE declined; VB-RI18 status; VB-RI18a filed |
| epyc-root | `handoffs/active/repl-embedding-retrieval.md` | "runtime-only" corrected; REPL-EMB-4.5 filed |
| epyc-root | `handoffs/active/stack-change-governance-pipeline.md` | SCG-DRYRUN `[x]`; SCG-INERT-FLAGS filed |
| epyc-root | `docs/reference/agent-config/INCIDENT_LOG.md` | two INC-20261003 entries |
| epyc-root | `progress/2026-10/2026-10-03-workspace-ec.md` | this file |

Index-row and adapter-README edits are prepared, not applied:
`/mnt/raid0/llm/tmp/wrapup-ec-20261003/INDEX_ROWS.md`.
