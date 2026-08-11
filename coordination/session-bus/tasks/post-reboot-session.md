# COORDINATOR HANDOVER BRIEF — written 2026-08-11 ~22:30Z

**If you are the incoming coordinator, read this before you run anything.** It is a pointer
document, not a restatement of the handoffs it cites — go read those when a section says to.

**If you are the OUTGOING coordinator, rewriting this file at wrap-up is your JOB, not a
courtesy.** Your successor trusts it absolutely and will start from whatever premise it states.
The previous version of this file was dated 2026-07-29, described a post-reboot cold start that
never happened, and named v8 as production. On the morning of 2026-08-11 a fresh coordinator read
it and started from a false premise; recovering cost most of the morning. **A brief describing the
fleet two sessions ago is worse than no brief, because it is believed.** Date-stamp it, state what
you verified and what you did not, and delete anything you cannot re-verify.

**The file name is historical.** This is not a post-reboot document. It is *the* coordinator
handover.

---

## 0. Check the clock before you believe anything below

```
uptime                      # 2026-08-11 22:30Z reads: up 13 days, 8:48 — NO reboot has occurred
date -u
```

Ground truth as verified at 22:30Z 2026-08-11:

| Fact | Value | How verified |
|---|---|---|
| Host uptime | 13 days, 8:48 — **no reboot** | `uptime` |
| Production kernel | `production-consolidated-v9` @ `0db32c06e3e550065b78311a6031ef3dd2c4f27c`, `llama-server` version **10125** | `scripts/session/verify_llama_cpp.sh` exit 0 |
| Rollback anchor | v8 `67a433bf45a8a091d83b4ea0b32ff0735fd51800`, binary 10107 | `CLAUDE.md` |
| epyc-root main tip | `d7a17f03`, **68 commits unpushed**, 266 dirty porcelain entries | `git log @{u}..`, `git status --porcelain` |
| epyc-orchestrator tip | `f8eb36f7`, **8 unpushed**, 5 dirty | same, in `/mnt/raid0/llm/epyc-orchestrator` |
| epyc-inference-research tip | `87c4b9c4`, **4 unpushed**, 1169 porcelain entries (largely untracked results — **never `git add` this tree wholesale**) | same |
| Commits landed today | **75** in epyc-root, **11** in epyc-orchestrator | `git log --since='2026-08-11 00:00'` |
| coordinator-daemon | pid **942753**, started 22:25:54 | `ps -eo pid,lstart,args` |
| bus supervisor | pid **489217**, started 08:48:00 | same |
| GPU (MI210) | 0% use, 0% VRAM allocated | `rocm-smi --showuse --showmemuse` |
| Serving stack | **fully DOWN** — every component `unavailable` / `state-missing` | `orchestrator_stack.py status` |
| AutoPilot | DOWN since 2026-07-27 | last journal activity; stack status |

Today's richest source, and the one to read next, is
[`progress/2026-08/2026-08-11.md`](../../../progress/2026-08/2026-08-11.md) — 851 lines, one
section per main, each written by that main for its own lane.

---

## 1. Bringup

1. **`uptime` first.** If it reads days, nothing below about "restart everything" applies to tmux
   or the stack — only to the daemon, which dies on its own schedule.
2. **`tmux new-session -d -s agent`** — only if the session is genuinely absent. `cmd_spawn` in
   `tmux_adapter.py` fails closed without it (defect **C20**,
   `handoffs/active/session-bus-thin-dispatcher.md`). That refusal is correct behavior, not a bug,
   and it is **not optional**: nothing spawns until the session exists.
   `tmux.allow_session_creation: false` means the adapter will never create it for you. Every main
   is a *window* in this one session — a standing operator requirement (2026-07-27).
   At 22:30Z the session holds windows: `coordinator`, `htop`, `btop-`, `inference`, `auditor`,
   `mainA`, `mainB`, `mainC`, `mainD`, `fish`.
3. **The coordinator-daemon does not survive, does not announce its own death, and `status` will
   lie to you about it.** On 2026-08-01T05:42:54Z it died and stayed dead until 2026-08-11T08:48Z —
   **243.1 hours**, measured as the single >1h gap in `advisory.jsonl`. Throughout, `status`
   reported `state=working epoch=13 pid=52352`: **the state file outlives the process that wrote
   it.** The supervisor was dead too — nothing watched the watcher.
   - Start the **SUPERVISOR**, never the daemon by hand:
     `nohup /mnt/raid0/llm/epyc-root/scripts/coordination/bus_supervisor.sh >/dev/null 2>&1 &`
   - Confirm with **`ps -p <pid>`**, not with `status`.
   - C35 (landed today, `45471692`) makes `status` fold liveness + identity + freshness into a
     leading verdict — it now prints `pid 942753 is alive and is the coordinator-daemon`. Trust
     that line only when you have confirmed the daemon is running the *current* source (see §3).
4. **Do not read an unreadable tmux window as "no main there."** That is the **C14 polarity
   error**: a roster row whose window cannot be matched must NOT be counted dead — doing so hands
   out occupied slots. Derive liveness from what is observable; never assume absence from a field
   nobody maintains.

---

## 2. C34 — the interpreter split. Read this before your first bus write.

`/usr/bin/python3` has **no `jsonschema`**; `/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python`
has 4.26.0. Under the bare interpreter `session_bus.py validate` reports the bus schema-clean while
the venv interpreter surfaces the real failures — that split silently refused **368 of 1137 outbox
rows (32%)** at relay: authored, never sent, nobody told.

> **Use `/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python` for every bus WRITE and every
> `validate`.**

The 2026-08-11 coordinator lost a `task-assign` to exactly this within twenty minutes of taking the
role — it lacked `payload.lane`, `lease_expires_ts` and `epoch`, and was silently unrelayable.
`mainD` closed the structural half today (`035dfecf`, `cc67a493`): `_validator` falls back to a
vendored dependency-free draft-7 subset over the same schema file and *refuses to construct* on a
keyword it does not implement. Refusals fell **368 → 151 (32% → 13%)**. The 151 residual rows still
need a disposition — coordinator's call.

---

## 3. Every C-series fix is inert until the daemon is restarted

This bit the fleet **five times in one evening** — C39, C28, C38's tick path, R1 and R2 were all
committed, boxed, and not running. A closed box carrying real measurements is more misleading than
an open one: the numbers are true and the state they imply is not.

Restarts today, each by killing the pid *you captured yourself*, verifying death with `ps -p`, and
letting the supervisor relaunch:

| From | To | At | Made live |
|---|---|---|---|
| 496387 | **921178** | 22:18:12 | R1, C39, C28, C38 tick path |
| 921178 | **942753** | 22:25:54 | R2 |

Verified live *by consumers*, not by inspection: C39 fired five `token-gate-looks-spent` notices two
seconds after start; `relay_state.json` (110 KB) now exists on disk, which is the proof C28/C38 are
executing.

**`mainD` has proposed** — not yet filed as a numbered C-item — a supervisor-side check so a running
daemon that predates its own source is detected instead of remembered, plus a cron watcher for the
supervisor itself (`hub_supervisor.sh` was found dead 08-10, same class). It is a host-level change,
so it is an operator ask. Route it.

---

## 4. R1 — the fleet had no working autonomous wake path until today

Until `b1222b6e` (mainD, today) there was **no path by which a stalled main could be woken**. The
daemon calls a heartbeat older than 3600s STUCK and nudges; `tmux_adapter.py` refused every nudge
past 900s. Between the thresholds nobody has decided you are stuck; past 3600s somebody has and can
no longer reach you — **the guard hardened exactly as the condition worsened.** Every main crossed
900s at ~10:14–10:22Z and the whole fleet, coordinator included, went unreachable for ~10 hours.
1,903 `stuck-nudge-refused` rows; recovered only by a human passing `--heartbeat-max-age 86400`.

Both documented escape hatches were unavailable: C35 lifts the `working` blocker and never
staleness; C36 is codex-rollout-only, i.e. 0% of an all-Claude fleet.

**The fix.** `hb_stale_override_ok` decides on *pane evidence* — `pane_dead` false plus quiescence
past the spinner interval, the same evidence C35 already trusts — instead of a timer. A timer cannot
distinguish wedged from quietly waiting; the pane can. Fails closed on every unknown.

**The fail-open that hid it.** `last_nudge_ts` / `last_nudge_sig` were written only on `rc == 0`
while escalation was gated on `last_nudge_sig`, so an always-refused nudge could never escalate —
1,903 refusals into `advisory.jsonl`, **a file with no reader**. Refusal now carries its own clock
and escalation lands in the **coordinator's inbox**.

> `--heartbeat-max-age 86400` was the manual workaround and should no longer be needed.
> **If you find yourself reaching for it, R1 has regressed.** Say so; do not re-apply it silently.

A test was asserting the bug (`test_c35_the_override_touches_only_the_working_blocker`, justifying
the refusal because staleness "is already tunable with `--heartbeat-max-age`" — the very knob a
human had to set to 86400 to rescue the fleet). Rewritten, intent preserved.

---

## 5. Roster and ownership

From `coordination/session-bus/config.yaml` plus today's assignments. Briefs live in
`coordination/session-bus/tasks/`.

| Roster id | Model / effort | Lanes | Owns |
|---|---|---|---|
| `inference` | codex, gpt-5.6-sol high | `cpu, gpu, none` | **ALL compute and all reload rights.** Long-horizon AutoKernel goal. Never contend for the host without going through it. |
| `auditor` | Fable 5 xhigh | `none` | Governance + audit only; dispatches its own subagents. Audits other mains' completed work. |
| `mainA` | Opus high | `cpu, none` | E5 offline salvage + kernel-era integrity (A5/A6/A7, Token 2) |
| `mainB` | Opus high | `gpu, none` | Orchestrator correctness, sequential lane |
| `mainC` | Opus high | `none` | Governance / backlog / **owns the queue generator** |
| `mainD` | Opus high | `none` | **C-OWN** — the session-bus delivery plane, `tmux_adapter.py`, the whole C-series |
| `coordinator-agent` | — | `none` | You |
| `codex-bus-tests` | — | — | **retired**; row kept so its history stays attached |

**All non-inference lanes are `none`: no inference, no region claims, no process management.**
`caps.max_concurrent_mains: 7`. When re-spawning, always reuse the **existing roster ids** — a fresh
alias orphans that identity's cursor, outbox and triage `corr_id`s.

---

## 6. Operator decisions made 2026-08-11 — do not re-open these

- **C-OWN goes to a dedicated main (`mainD`)**, not the auditor. Handoff row updated at
  `handoffs/active/session-bus-thin-dispatcher.md:699`; brief
  `coordination/session-bus/tasks/mainD-c-own-delivery-plane.md`.
- **SEQ-A1 resolved as Horn A** — recompute per trial, readmitting 3 candidates (E = 11.55 / 8.70 /
  2.74) whose evidence was being discarded. The persistence/consumer half is explicitly in `mainB`'s
  lane. `sticky_refuted` was built neutral (defaults `False`, `43108014`) precisely so this could be
  settled from data.
- **The do-not-flip sweep extends to `handoffs/completed/` and `archived/` but REPORTS rather than
  restores there.** Both trees swept and clean; nothing needed restoring.
- **Stack / AutoPilot restore routes to `inference`, at its own boundary, after AutoKernel.** Not
  yours to execute — reload ownership follows the inference holder.
- **Each main writes its OWN wrap-up, per task, and the coordinator VERIFIES rather than
  substitutes.** A coordinator reconstructing a main's day from commit messages produces a plausible
  and wrong log. Nudge the main; never write for it.

---

## 7. Four ratifications signed today — and six stale checkboxes

Receipts in `artifacts/operator/receipts/`, all `status: ratified`:

| Gate | Effect |
|---|---|
| `RATIFY-ANNEXG-V9-CURRENCY-20260811` | Annex G P-GPU-1 pin v8 → v9; **zero** `currently-v8` clauses survive |
| `RATIFY-CONSOLIDATED-ERA-ROWS-20260811` | 4 era rows: `E9-cpu-kernel`, `E9-routing-reward`, `E8-cpu-bench-throttle-scope`, `E8-seeding-reward-b7-guard`; none struck |
| `RATIFY-V9-CPU-BENCH-ERA-ADVANCE-20260811` | Advanced the *state consumer*; verified live — `orchestration/autopilot_state.json` `cpu_bench` = `E9-cpu-kernel`. Exists only because the auditor caught a committed-not-live gap in the token signed 90 minutes earlier |
| `RATIFY-CPU-BENCH-BINARY-VERSION-20260811` | Additive `binary_version` + `kernel_commit` on the three cpu_bench kernel-cutover rows (10098 / 10107 / 10125); resolves the `cpu_bench` scope collision. No measured value changes |

> **Six gates carry a ratified receipt and still show `[ ]`** in `tokens/token-queue.md` — lines
> **134, 144, 292, 302, 312, 322**. The receipts are authoritative; **the boxes are stale**. C39
> annotates them (it fires `token-gate-looks-spent` rather than suppressing them) and that is
> correct. **ONLY the operator may tick a checkbox in that file.** Surface all six; touch none.

---

## 8. Genuinely open, with owners

- **The E8 cross-era decision package** — **UNOWNED** since `inference` handed off. Needs a
  coordinator assignment. (`artifacts/audit/completion-flurry-wiring-audit-20260811.md`, §D.)
- **Supervisor staleness + supervisor-of-supervisor cron** — `mainD` proposed, operator/host-level
  ask, not yet filed as a C-item (§3).
- **`advisory.jsonl` rotation** — 1,091,556,378 bytes / **3,003,186 rows** and growing. C38 removed
  the per-tick full re-parse (measured ~8.9 s and ~6.6 GiB of transient dicts against a 45 s tick;
  now `relay_state.json`, 110 KB, 0 ms, one 0.54 s bootstrap). **Rotating the ledger already on disk
  is still unowned.** `handoffs/active/session-bus-thin-dispatcher.md:1858`.
- **Idle compute** — GPU 0% / 0% VRAM, all regions free, serving stack fully DOWN, AutoPilot down
  since 2026-07-27. Options were put to `inference`, which owns compute and all reload rights;
  awaiting its boundary. Not blocking anything.
- **C34's 151 residual refused rows** — disposition recommendation is with the coordinator.
- **C12 / C13** landed today (`d7a17f03`) after sitting filed-not-fixed since 07-29.
- **Counter reconciliation.** `python3 scripts/handoffs/index_state.py` reports **open 1203 /
  closed 2301** (blocked 5, guarded 66, total 3575 across 174 handoffs) while a raw checkbox grep
  over `handoffs/active/*.md` gives **1275 / 2297**. The gap is real and mechanical: `index_state`
  classifies *guarded* and *blocked* boxes into their own buckets. Reconcile it, or the dashboard
  and the coordinator's churn line will contradict each other in front of the operator.
  `--check` currently exits 0 with 0 problems.
- **`mainB` A4's seven failures** — need `inference` to relaunch `--numa-mode both` and recompile
  priors. `test_specific_role_urls` **stays red and must not be closed by relaxing it.**
- **`mainB` A14** — GateDecision echo, done and merge-ready, parked on branch
  `a14-gatedecision-echo` @ `a7d7bdb6` pending a merge window cleared with `inference`.
- **`mainA` A6 operator token** (decouple `decision_grade` from the secondary trimmed window,
  promotes 5 cells) — operator; nothing further owed by that lane until signed.
- **E8 frozen-kernel pin** — operator. Today's v9 freeze moved the tree the E8 protocol pins. The
  guard is working correctly; re-pinning it would re-base a measurement era.

---

## 9. Standing warnings

- **AutoPilot is DOWN and the serving stack is fully down.** Any bench number taken now is against a
  quiesced host, not a representative one. Sampling duty cycle here returns a near-zero value and
  would close a decision on a measurement artifact.
- **The P-BENCH decision-grade uptime window (≤ 1 week) has LAPSED** — 13 days and counting. It
  gates nothing until an operator call, but do not mint a decision-grade claim against it.
- **The backlog dispatch queue was superseded today.** `tasks/BACKLOG-DISPATCH-QUEUE.md` carries a
  do-not-dispatch banner and is retained as evidence, not deleted — dispatch from `mainC`'s
  generator (`scripts/coordination/backlog_queue_gen.py`, root `83eb7b94`). Re-derivation found
  whole-queue anchor rot at **34.5%** (up from 27% on 07-29) and true dispatchable at **≤ 71 of the
  220 rows the file advertised**.
- **Never `git add` wholesale in a shared clone**, and never `git commit --amend` — a 4-file amend
  swept 33 other sessions' staged files today. Recovery is `reset --soft` + pathspec re-commit.
  Commit with `-- <paths>`.
- **A dirty shared clone has no single author.** Attribute per hunk; an untracked working-tree edit
  looks identical to a committed one until someone else checks the repo out.
- **Kill only PIDs you captured yourself.** Never `pkill`/`pgrep` by name pattern on this host.
  After killing, verify with `ps -p <pid>` before reporting success.

---

## 10. Bus drain

At your first task boundary, and every boundary after:

```
/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python scripts/coordination/session_bus.py \
    drain --agent coordinator-agent --triage
/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python scripts/coordination/session_bus.py \
    append --agent coordinator-agent --target heartbeat \
    --json '{"state":"working","task_id":"<id>"}'
```

A heartbeat written once is a birth certificate, not a liveness signal. Refresh it at every
boundary — post-R1 it is also how the daemon decides whether it needs to come find you.

Contract: [`coordination/session-bus/BUS_PROTOCOL.md`](../BUS_PROTOCOL.md).
Role file: [`agents/coordinator-agent.md`](../../../agents/coordinator-agent.md).
