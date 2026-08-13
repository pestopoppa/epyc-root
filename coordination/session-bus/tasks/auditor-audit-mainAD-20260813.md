# auditor — audit mainA-D completed work and update relevant handoffs

## 1. Drain first

```
/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python scripts/coordination/session_bus.py drain --agent auditor
```

Act on MUST-ACT items. Refresh your heartbeat after draining.

## 2. Task

You are the reviewer. mainA–D have completed a first wave of work (this morning, 2026-08-13,
before a coordinator stop) and are being re-dispensed onto new/resumed rows. **Audit the completed
work and deliver updates to all relevant handoffs** so that when mains proceed onto new tasks they
will be dispatched the tasks you draft.

### Work completed to audit (from this morning's sessions)

| Main | Row | What it claims | Evidence |
|---|---|---|---|
| mainA | `opendataloader-pipeline-integration--011-L512` (`handoffs/active/opendataloader-pipeline-integration.md:540`) | Premise verified: `odl_bench/` lacks intrinsic/Ekimetrics/FMRE refs; scoping Ekimetrics MIT scaffold integration | mainA ack `msg-20260813T104609Z-58-coordinator-agent`; worktree `lane/mainA` |
| mainB | `opendataloader-pipeline-integration--013-L534` (`:562`) | LiteParse vs OpenDataLoader vs pdftotext bench — mid-bench | worktree `lane/mainB` |
| mainC | `repl-turn-efficiency--Prefix-L107` (`handoffs/active/repl-turn-efficiency.md:107`) | Static audit + 2 instrumentation fixes + flag-gated prefix-stable order landed (orchestrator `d977454e`, `2c4087b7`) — awaiting compute for live A/B | mainC progress `progress/2026-08/2026-08-13-mainC.md` |
| mainD | `opendataloader-pipeline-integration--P2-L615` (`:615`) | Unlimited-OCR single-pass arm built + registered in `odl_bench` (26/26 tests) — awaiting compute for demo run | mainD progress `progress/2026-08/2026-08-13-mainD.md`; finding `msg-20260813T112442Z-32-mainD` |

### Audit method — persistence IS the deliverable

**You do NOT message mains directly.** Mains keep working and `/clear` at unrelated task
boundaries, so a direct message lands in a cleared or stale context and cannot act on it. Your job
is to persist so the dispatching machinery loops back to the handoffs:

- For each claim: verify against the actual code/commits (worktrees under
  `/mnt/raid0/llm/worktrees/mains/<id>` and the orchestrator/research trees), then update the
  corresponding handoff rows: flip checkboxes with evidence (`- [x]` + `✅ YYYY-MM-DD`), or record
  a finding that the row remains open.
- **Draft new task rows** in the handoffs for anything that becomes next-required after the audit
  (follow-up measurement, follow-up bench, unresolved defect) as open `- [ ]` checkboxes with
  enough context to screen. These become dispatchable: the coordinator's machinery re-scans the
  handoffs (`backlog_queue_gen.py --generate`), intakes open boxes into the queue, and dispatches
  them to idle mains. **This is how your drafted tasks reach mainA–D on their next dispatch.**
- Your own progress file: `progress/2026-08/2026-08-13-auditor.md` (in `/workspace`, your worktree).
- Run your wrap-up skill at checkpoints. Promote lane/mainA..D to `main` at wrap-up so the
  coordinator's queue rebuild sees the flipped/added boxes at HEAD.

## 3. Scope limits

- You are the reviewer: audit + update handoffs + draft tasks. **Do NOT take fresh task work.**
- Compute is inference-owned (BUS_PROTOCOL rule 11) — no compute needed for auditing.
