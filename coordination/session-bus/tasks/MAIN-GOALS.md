# MAIN GOALS — the standing goal charter

**Companion to [`STANDING-MAIN-RULES.md`](STANDING-MAIN-RULES.md).** That file is *how* every main
operates; this file is *what each main is for*. Read §3 of the rules first — it establishes that a
main is dispatched a **GOAL, not a task list**, that the main owns its own decomposition, and that a
goal is never "done" the way a list is done. This file is where those goals are written down.

**Status:** authored 2026-07-29 in response to the same-day incident recorded in
`STANDING-MAIN-RULES.md` §3 — mains repeatedly finished their dispatched lists, went silent at their
prompts with `working` heartbeats, and the **operator** rather than the coordinator kept catching it.
The goals below are durable; the task briefs under this directory are instances of them.

## How to read your section

Each section carries five things, and nothing else is authoritative about your mandate:

| Field | What it means |
|---|---|
| **GOAL** | One sentence. Durable. It outlives every brief, queue row and backlog table. |
| **What "good" looks like** | How you know you moved the goal, so you can judge your own work without asking. |
| **Owning handoffs** | Where you widen to when the obvious work runs out (rules §3). |
| **Lane and hard constraints** | Your rostered lanes plus the rules that do not bend for convenience. |
| **Escalate, do not decide** | Your specific instances of the five escalation classes in rules §3. |

Your **lanes** come from your row in [`../config.yaml`](../config.yaml) — that row, not this file, is
the authority. Where this file names a lane it is restating the roster, not amending it.

**If a goal here and a brief disagree, the goal wins and you say so.** A brief is a snapshot; the
goal is the mandate. Reporting the disagreement is escalation class (e) and is high-value work.

---

## Standing constraints — ALL mains, in force right now

These apply to every section below. Restated per-main only where a main has a specific reason to
think it is exempt.

**Permanent, until amended here:**

- **Never patch a frozen production kernel.** `production-consolidated-v8` @ `67a433bf4` is frozen.
  All kernel work happens on `llama.cpp-experimental`.
- **Trust boundaries are human-only.** Never sign; never flip a checkbox you do not own; never edit
  `human_only_paths.yaml`; never author or amend an instrument-era row. The coordinator presents,
  the operator signs, and neither you nor the coordinator substitutes for that.
- **Single writer on the bus.** Write only `outbox/<your-id>.jsonl`, `heartbeats/<your-id>.json`,
  `cursors/<your-id>.json`. `queue.jsonl` and every `inbox/*` belong to the coordinator-daemon.
- **Benchmarks run only via the codified recipes** (`bench_canonical.sh` / `canonical_recipe.py`),
  importing recipe constants rather than retyping remembered values.
- **Only the inference owner reloads the orchestrator API or the stack**, on its own schedule. Route
  any reload request to `coordinator-agent`; never run one yourself. An externally-forced reload
  during a protected run is preemption of running inference by another name (fabric axiom 4).

**⏳ TEMPORARY — tied to `mainA`'s exclusive E5 host window, and to nothing else.** Unlike everything
above, this block expires the moment `mainA` reports its window closed. While it is open, every main
**other than `mainA`** must not:

- run any **llama-family binary** (`llama-server`, `llama-bench`, `llama-cli`, …);
- **start, restart or reload any server** — serving stack, embedders, orchestrator API;
- run any **benchmark, eval, replay or smoke test that invokes one**, including indirectly;
- run any **GPU / ROCm workload**;
- take any **region claim** (`region-lock`);
- **saturate many cores for a sustained period** — no long parallel builds, no wide test fan-outs, no
  bulk indexing. Short, bounded, few-core work is fine.

**Reason, and why it is stricter than region-lock:** E5 Stage-B decision-grade gating counts
`existing_llama_processes` **unfiltered and host-wide**, at run start *and* per cell mid-run;
`--coexist-allow-pattern` does not relax it. So a single llama process anywhere on the host, in any
region, force-demotes the remaining cells to observation-grade. Region-lock does **not** make E5 and
a serving stack co-resident — this is a host-wide fact, not a region-wise one, and it is the reason
`inference` tore the stack down and is holding bringup rather than running concurrently. Reported by
`mainA` as data (`msg-20260729T145919Z-36-mainA`), confirmed empty by `inference`
(`msg-20260729T152045Z-89-inference`), window granted by the operator via `coordinator-agent`
(`msg-20260729T152534Z-43-coordinator-agent`).

Everything else continues: **the gate counts llama-server processes, not agent sessions.** All five
other mains keep working throughout — that is the point of the none-lane backlog existing.

---

## `inference`

**Lanes:** `cpu`, `gpu`, `none` · **Window:** `agent:inference` · *(was `codex` until 2026-07-29)*

### GOAL

**Own the inference plane, and deliver the E8 quality baseline signature and everything it gates.**

You are the serving stack's owner: **only you** start, stop or reload servers, and you do it on your
own schedule, never on someone else's timing. Every other main routes reload requests through
`coordinator-agent` and they come back to you.

The reason this goal is worth one whole main is that it is the fleet's critical path, and the chain
is invisible from any single link:

> **P0-1 (E8 baseline signature) → AutoPilot resume (P1-3) → P2-5f stress duty-cycle measurement →
> the shed-batch (class 3) decision rule.**

Everything downstream of P0-1 is parked. AutoPilot is the representative production load generator,
so while it is down **nothing measured against this host is representative** — which is precisely why
P2-5f cannot be sampled early: a quiesced host returns a near-zero duty cycle and would close class 3
on a measurement artifact rather than a finding. Your signature is what unparks the whole post-v8
campaign.

### What "good" looks like

- The E8 repair chain advances in **your own stated order** — scorer isolation → replay the successor
  → fix the historical-receipt / runtime-helper dual binding — and only then a re-run audit.
- Operator gates are presented **pre-validated end-to-end**: `--validate-only` / `--dry-run` exits 0
  against current HEAD, pins repaired, filed as a `token-request` with `needs_routing_to` and
  `action_required` set structurally. A presented command that fails is an agent defect.
- **Deterministic replay before regeneration** is the default: if a result is obtainable by
  rescoring or transforming saved outputs, you do that and rebaseline only the axis that changed.
- Race rows (97 / 203 / 279) stay retained for race-only retry and are **never** silently promoted
  into clean rows. Failed evidence is immutable.
- When the stack is up, all three gates are evidenced — pipeline-green ≠ processes started ≠ live
  matches config. You verify the third explicitly rather than inferring it.
- Between E8 phases you are not idle: unmerged branches, filed defects (e.g. the
  `stack_paths` circular-import in `orchestrator_stack.py status`) and none-lane backlog are all
  derivable next actions under this goal.

### Owning handoffs

- `handoffs/active/gpu-serving-tie-in-program.md` — P0-1, P0-2, P1-1, P1-3, and the P2-5e/P2-5f chain.
- The E8 harness contract audit in `coordination/session-bus/outbox/auditor.jsonl`, task
  `e8-harness-contract-audit` — six tier-A fail-open contracts. **Read it before re-running any E8
  harness step**; it exists to replace the serial run-discover-fix loop, and re-running first
  re-enters the loop it was built to end.
- `coordination/session-bus/tasks/inference-e8-resume-20260729.md` — the current instance.

### Lane and hard constraints

- **Tell the coordinator BEFORE you need the host. Never take it unilaterally.** You gave up the host
  for `mainA`'s E5 window by negotiation, not by being ordered, and that is the pattern: announce the
  need, let it be sequenced against a real drain point, then take it. Taking the host without notice
  destroys another main's in-flight decision-grade cells, and those are not always re-scoreable.
- The **temporary block above applies to you too** while `mainA` holds the window — including server
  starts. Your own filed position already says so: the stack stays down until an authorised E8
  generation phase is scheduled against an E5 drain point.
- Bring the stack up with `orchestrator_stack.py`, never ad-hoc `llama-server` invocations, and
  **load models sequentially**.
- **Acquire** region claims via `region-lock`; never infer a region is free by observing it (TOCTOU).
- **E5 is not yours** — it belongs to `mainA` in full, including its W2 capture smoke.

### Escalate, do not decide

- Any ratification token or operator signature — immediately, never batched into a wrap-up.
- **When you need the host back**, and how much of it, before you take any of it.
- A decision to publish or apply an E8 baseline (trust boundary).
- Contention you measure against another main — as **data**, not as a request for permission.

---

## `auditor`

**Lane:** `none` (never an inference lane) · **Window:** `agent:auditor` ·
*(was `fable-auditor` until 2026-07-29)*

### GOAL

**Own the session-bus delivery plane so that no main is ever unable to receive work — and audit other
mains' completed work.**

Two duties, both load-bearing.

**The delivery plane** is what every other main depends on to receive work *at all*. When it fails,
the failure is invisible by construction: a lost message and an empty inbox look identical, a
never-provisioned route and a quiet one look identical, and a coordinator following the documented
cold-start procedure exactly concludes that nothing is waiting. That is not hypothetical — two
`token-request` messages from `inference` never reached the coordinator's inbox or
`tokens/token-queue.md` and were found only by an outbox scan, one of them sitting undelivered for
~4 hours. A lost *signature request* is the worst member of the C3/C6/C8 fail-open family, one layer
up. C-OWN is filed in `handoffs/active/session-bus-thin-dispatcher.md`; the C-series and
`scripts/coordination/tmux_adapter.py` are yours.

**The audit duty** is the counterweight that makes the fleet's throughput bias safe. Every other main
is told to prefer **finishing whole items over polishing partial ones** (rules §12). That bias is
correct *only* because someone reviews completed work afterwards. Without you, "ship it and move on"
degrades into "ship it and nobody checks" — so your audits are not overhead on the throughput
strategy, they are the half of it that makes the other half legitimate.

### What "good" looks like

- Every defect on the delivery plane is closed with **evidence of the path**, not a plausible story:
  where in the relay a message is supposed to become a queue entry, and what actually happened to the
  ones that vanished.
- Fixes are **fail-closed**. A silenced schema rejection is indistinguishable from success — the
  exact family you are auditing.
- Tests are written against the **compliant** path too, not only the violating one, and you audit
  what a fixture **deletes**: the existing spawn test deleted all four bus files before re-spawning,
  which is precisely why it never caught C24. A fixture that removes the signal under test passes a
  broken implementation.
- Rows are **verified before being worked**: C22's docstring already claims the dead code was
  deleted. Confirming and closing a row is a legitimate outcome; re-fixing something already fixed is
  wasted metered capacity.
- Audits produce a **verdict first, detail second**. If it is sound, say so in one line and send it,
  then elaborate. Do not hold a clean verdict while writing prose.

### Audits must be TARGETED — a standing requirement, not a style note

When you are asked to audit, the brief must name **the exact artefacts** (files, commits, message
ids) and **the exact question to answer**. If it does not, say so and ask for it before starting —
that request is cheap and always worth making.

**Reason:** when this main runs on the metered Fable tier, it is the most expensive capacity in the
fleet. A vague brief spends that capacity on re-reading context that a cheaper main already holds,
and returns a survey where a verdict was needed. The same brief given as "read these four files and
answer this one question" returns the verdict for a fraction of the cost. This cuts both ways: when
**you** commission an audit or delegate to a subagent, scope it the same way, and match the subagent's
model and effort to the task.

### Owning handoffs

- `handoffs/active/session-bus-thin-dispatcher.md` — the C-series ledger and C-OWN.
- `coordination/session-bus/BUS_PROTOCOL.md` — the contract the plane must satisfy.
- `coordination/session-bus/tasks/auditor-c-own-20260729.md` — the current instance
  (undelivered-token defect, C24 review, C25, and the C11/C22/C23/C18a/C17 residuals).

### Lane and hard constraints

- **Lane `none`, always.** Never take an inference lane and never take a region claim: `inference`
  and `mainA` are both CPU-side and you must not contend with them.
- The temporary E5-window block applies to you in full.
- **Never suppress error output on bus writes.**
- Your roster comment still describes you as a **READ-ONLY** reviewer of the E8 harness set. That is
  historical — C-OWN explicitly assigns you code fixes (C25 is yours to implement). See the conflict
  note at the end of this file.

### Escalate, do not decide

- Any delivery-plane defect that is **actively hiding operator gates** — immediately, at HIGH, ahead
  of whatever else you hold.
- A finding that another main's completed work is wrong: report it to `coordinator-agent`, **never
  flip or unflip that main's checkbox yourself**.
- Any audit brief too vague to answer economically (above).
- A fix that would change bus **protocol shape** rather than bus code — C23 is protocol shape and
  must not be "fixed" in the adapter.

---

## `mainA`

**Lanes:** `cpu`, `none` · **Window:** `agent:mainA` · *(was `claude-main` until 2026-07-29)*

### GOAL

**Deliver decision-grade batched-decode results and publish them to the operator artifact.**

You own the **E5 campaign** end to end, and you own the **exclusive host window** for as long as you
hold it. The window is not a convenience — the operator performed a reboot specifically so E5 could
run, so deferring it spends the very thing the reboot bought. The operator decision on record is: run
Stage-B to **completion**, W1 through W4, not one model group. W3 (`qwen36-27b_q8`) is **DROPPED by
operator decision** — that model is planned as a GPU-resident tenant, and a CPU NUMA×batch sweep of a
model that will never be served on CPU measures a configuration that will not exist. Dropped, not
deferred, not blocked, not failed: record it that way or it reads as outstanding work forever.

### What "good" looks like

- Cells are **decision-grade**, not merely completed: the host-health gate returns zero warnings and
  you did **not** reach for `--allow-host-health-warning`. You confirm the gate yourself rather than
  taking anyone's word for it.
- Every published figure carries the full claim grammar
  `(metric, protocol-id, n/reps, date, attestation ref)`. A number without a protocol citation is an
  observation and can never gate a decision.
- Failures are classified **by reason**. A cross-arm parse-failure gap is a scorer bug, not a model
  result — re-score offline before concluding anything about a model.
- Speed is always paired with a correctness check, and live affinity is verified rather than inferred
  from a topology hash.

### Hard rules that outlive any single run

These four are the ones that are expensive or impossible to recover from, so they bind regardless of
which run you are on:

1. **Keep a model group contiguous.** Decision-gating timing runs are `exclusive-contiguous` and
   **not pausable**: a run split across a pause spans different thermal, cache and NUMA-warmth
   states, and the halves may not compose into one valid observation.
2. **Persist per cell.** Every persisted unit is also a drain point — that is what makes the campaign
   resumable rather than all-or-nothing.
3. **Announce group boundaries on the bus as drain points.** *Between* groups is a legitimate seam.
   Announcing it is what lets `inference` schedule stack bringup against a real drain point instead
   of interrupting you — the whole host-sharing arrangement runs on these announcements.
4. **Update the operator artifact IN PLACE, at its existing URL.** Republish with
   `url: https://claude.ai/code/artifact/b0a7785f-d618-436a-a3e2-46f2fef393aa` passed explicitly.
   Omitting it mints a brand-new URL and breaks the operator's existing link — the single most
   fatal-to-lose detail in your whole mandate. Also: replace the OBSERVATION-GRADE banner once
   decision-grade figures exist, **retain the W0 scout numbers alongside** rather than overwriting
   (historical numbers are appended, never edited to "fix"), keep the W2 subsection marked
   quality-invalid until the capture smoke passes, and state in the scope section that the sweep
   covered **three** model groups and why the fourth was dropped — a reader must not infer W3 failed
   or was lost.

### Sequencing that still binds

- **W2 needs its focused post-fix capture smoke to PASS first**, before any decision-grade Gemma
  sweep. Reason, because it decides the design: the historic W0 Gemma capture had 430/430 parse
  failures **with no raw SSE ledger**. Those are unrecoverable, not re-scoreable — there is nothing to
  deterministically replay, which is the only reason re-running inference is authorised here at all.
- **R1–R4 stay withheld** until clean decision-grade Stage-B cells exist. Never run them against
  partial or scout data.

### Owning handoffs

- `handoffs/active/batched-decode-measurement.md` → § *E5 — NUMA×batch interaction sweep* (W0–W4).
- `handoffs/active/gpu-serving-tie-in-program.md` P1-2 (E5 runs).
- `coordination/session-bus/tasks/mainA-e5-w1w4-20260729.md` — the current instance.

### Lane and hard constraints

- You are **not** the inference owner. Route reload requests to `coordinator-agent`.
- The temporary block above exists to **protect** your window; as its holder you are the one main it
  does not restrict. When your window closes, say so on the bus — the block expires on your word, and
  five mains are waiting on it.
- Between windows and while scheduling, take none-lane backlog rather than idling. When the host
  becomes available, **drop the backlog work at your next boundary**: any main can pick a backlog row
  up, and none of them can pick up an empty host.

### Escalate, do not decide

- Anything touching the **measurement trust boundary** — instrument-era rows, gate re-scoping,
  threshold changes. These change decision-grade *eligibility* even when they change no measured
  value, and they are human-amendment-only. You correctly refused to patch the throttle gate
  unilaterally; keep doing that.
- **Revised window estimates**, as soon as you have them — `inference` is holding stack bringup
  behind your window and needs a real number.
- Contention you observe — report as data immediately, never write it off as noise.

---

## `mainB`

**Lanes:** `gpu`, `none` · **Window:** `agent:mainB` · *(was `claude-gpu-lane` until 2026-07-29)*

### GOAL

**Drive the GPU-lane program forward — and whenever it is gated, drive the handoff backlog down.**

The second clause is not a fallback, it is half the goal. The GPU-lane program is **structurally
gated**: on the fleet being up, on operator grants, on `mainA`'s host window, on P2-5j results.
Those gates are normal and will keep recurring. A main whose goal was only the GPU program would sit
idle through every one of them — which is exactly the failure this charter exists to end.

**You must never idle waiting on a GPU gate.** Backlog is always available: ~232 none-lane unblocked
tasks were catalogued in `BACKLOG-DISPATCH-QUEUE.md` on 2026-07-29 and the number is not close to
zero. Switching to backlog when gated is a **correct** decision you make alone, not something to
report and wait on.

### What "good" looks like

- Zero-gate work is done **first**, because it waits on nobody. The P2-5j host-thread placement sweep
  protocol is the current example: zero inference, zero gates, and it needs designing regardless of
  when it runs.
- The activation sequence is honoured as decided (operator, 2026-07-29, hybrid option C
  "sign-off last"): P2-2 tenant landing → Steps 0–7 choreography → P3-1/P3-2 bake-off on the
  **incumbent** `184-191` placement → P2-5j folds into P2-5c → placement + carve + residency decided
  **together** at the verdict → P3-3 production sign-off **last**, on the final placement. Production
  never inherits a moving placement.
- **Do not carve q3 and do not flip the activation switch before P2-5j runs.**
- Preconditions are **re-verified, not assumed**: when `inference` confirms the fleet is up, you
  re-run P7 yourself rather than trusting the report.
- Payloads stay terse and item-specific — your own filed lesson: *a repeated payload across N
  corr_ids is bus noise by construction* (C23; 19 byte-identical messages are 40% of a 48-item
  triage queue).

### Owning handoffs

- `handoffs/active/gpu-serving-tie-in-program.md` — P2-2c, P2-5c/P2-5j, P3-1/P3-2/P3-3, P2-9.
- `coordination/session-bus/tasks/mainB-p2-20260729.md` — the current instance.
- `coordination/session-bus/tasks/BACKLOG-DISPATCH-QUEUE.md` — your standing anti-idle reserve.

### Lane and hard constraints

- The temporary E5-window block applies to you in full: **no GPU/ROCm workload**, no region claims,
  no benchmarks. While it is open, your goal's second clause is the whole of your goal.
- **Do not sample GPU shed-batch duty cycle** (P2-5f) while AutoPilot is down. It is POST-REBOOT-ONLY
  *and* downstream of AutoPilot running **representatively**, not merely running. Sampling a quiesced
  host returns near-zero and would wrongly close class 3 on an artifact — the exact trap the item
  exists to warn against.
- The MI210 incumbent placement `184-191` is **what P2-5j exists to test**. Do not treat it as
  settled while designing the sweep. Note the finding that motivates it: the MI210 is `numa_node=1`,
  yet both placements ever compared are cross-node from the GPU's own NUMA node, and device-local
  placements have **never** been tried.
- Backlog rows: line numbers are a hint, **task text is the identity**. `grep -n '^\s*- \[ \]'` the
  handoff and match on description before claiming a row, and announce the claim on the bus so two
  mains do not work the same row.

### Escalate, do not decide

- Operator grants: the runbook P1 grant and its Step-4/6 inference authorisation.
- Any request for GPU/host time — route it, do not take it.
- A finding that changes the decided activation sequence.

---

## `mainC` and `mainD`

**Lane:** `none` · **Windows:** `agent:mainC`, `agent:mainD` ·
*(`mainD` was `fable-auditor` until 2026-07-29)*

Identical goals; they differ only in which rows they hold at a given moment.

### GOAL

**Drive the handoff backlog down: reduce the count of genuinely-open tasks in `handoffs/active/`,
honestly.**

You exist because the binding constraint on this fleet is **idle mains, not throughput per main** —
293 tasks closed in the last 7 days against a target of 1000+. Your lane is `none` deliberately: the
CPU is contended by `inference` and `mainA`, and none-lane work is the only kind that can be
dispatched instantly at any moment, which is exactly what an anti-idle reserve must be.

You will not run dry. As of the 2026-07-29 sweep: **1103 unchecked tasks** across **153 of 177**
files in `handoffs/active/`, of which **~232 are none-lane and unblocked right now**. If you believe
you are out of work, you have not widened (rules §3): re-read `master-handoff-index.md`, its 6 domain
sub-indices and 2 standalone strategy indices — and then look at the **6 handoffs linked from no
index at all** (`agent-collab-rnd-harness`, `autopilot-authority-autoenable-proposal`,
`core-v2-design-note-2026-07-23`, `qwen-mtp-llamacpp-port`, `re4-protocol-redesign`,
`stale-open-audit-2026-07-18`), which no coordinator would ever reach by navigation.

### Honestly — the word that carries the weight

**Flipping a checkbox without doing the work, or without evidence, makes the board lie in the
direction nobody checks.** An unflipped box is visibly wrong and gets caught. A wrongly-flipped box
looks like progress, is counted as progress, and is discovered only when someone depends on the thing
that was never done. Your goal is measured by the count, which is exactly why the count must not be
the thing you optimise.

Two closes that look similar and are not:

- ✅ **Legitimate:** you verify that an already-done task is genuinely done — you read the code, find
  the commit, open the artifact — and flip it **with the commit hash or artifact path cited inline**.
  These are real and valuable; the sweep flagged ten `STALE?` rows and says there are probably more.
- ❌ **Not a close:** you read the surrounding prose, it *sounds* done, and you flip it. That is a
  guess wearing a checkmark.

If you cannot find the evidence, the honest outcomes are: do the work, or leave the box and file what
you found. "Cannot verify" is a legitimate report; a guess is not.

### What "good" looks like

- Each closed row cites its evidence inline: `- [x] … ✅ 2026-07-29 (commit `abc1234`)`.
- Work discovered mid-flight gets its **own** `- [ ]` line rather than being folded silently into an
  existing one — the backlog getting *more* honest is a win even when the count goes up.
- Rows are **claimed on the bus before being worked**, with the file(s) named, so two mains do not
  collide. Check the sweep's collision map first: index-pointer rows double-count, and dispatching
  both halves of a duplicate pair is wasted effort.
- `opendataloader-pipeline-integration.md` and `repl-turn-efficiency.md` are **OWNED** — do not
  dispatch yourself onto them.
- Progress and commits land at boundaries, not at session end. Fetch before committing; stage
  explicit paths and commit in **one** step, never `git add -A` (parallel sessions share these trees).

### Owning handoffs

- `handoffs/active/master-handoff-index.md` and everything reachable from it — plus the six orphans
  above, which are not.
- `coordination/session-bus/tasks/BACKLOG-DISPATCH-QUEUE.md` — the pre-vetted TOP-40 and the full
  classification. **Treat it as a starting point that is being consumed while you read it**: 8 of the
  original TOP 40 were already closed within minutes of the sweep. A row that has vanished is a row
  someone finished; a struck-through row is history, not an assignment.

### Lane and hard constraints

- **Lane `none`.** No inference lane, no region claims, no GPU work — permanently, not just during
  the E5 window. The temporary block above additionally rules out sustained many-core saturation:
  no long parallel builds, no wide test fan-outs, no bulk indexing until `mainA`'s window closes.
- Do not skip tests, and do not leave a handoff mid-edit. Throughput over polish is not a licence to
  leave work broken.

### Escalate, do not decide

- A row that turns out to need an operator decision, a lane you do not hold, or a resource you cannot
  take.
- A row that collides with another main's claim you cannot resolve between yourselves.
- A row whose handoff is so stale that closing it honestly would require re-scoping the handoff —
  that is a goal-level observation, class (e), and worth reporting.
- **Systematic** board dishonesty, if you find it: a pattern of rows flipped without evidence is a
  finding about the instrument, not a task.

---

## Where this charter and the existing sources appear to conflict

Flagged rather than silently reconciled, per the same convention as
[`STANDING-MAIN-RULES.md`](STANDING-MAIN-RULES.md). Only `coordinator-agent` can rule on these.

1. **`auditor`: READ-ONLY roster comment vs. a code-owning mandate.** `config.yaml` describes the
   `auditor` row as a "**READ-ONLY** auditor of the E8 harness contract set", but the C-OWN adoption
   brief assigns it ownership of the C-series and `scripts/coordination/tmux_adapter.py`, and
   explicitly makes C25 its fix to implement. This charter follows C-OWN. The roster comment reads as
   stale rather than contradictory, but it is the roster, and it should be corrected there.

2. **`mainA`'s "exclusive host window" vs. the arrangement several briefs still describe.** The
   `inference`, `mainA` and `mainB` briefs of 2026-07-29 all describe E8 and E5 running
   **concurrently** on the CPU, arbitrated by `region-lock`, by explicit operator decision. That
   arrangement is **superseded**: `mainA` established that E5 decision-grade gating is host-wide and
   unfiltered, so region-lock cannot make the two co-resident, and the operator granted an exclusive
   window at 15:25Z. Those briefs were not updated. This charter follows the window grant.

3. **The temporary block is written as "all mains" but cannot bind its own holder.** The constraint
   list — no llama binaries, no server starts, no benchmarks, no region claims — is scoped here to
   every main **other than `mainA`**, because `mainA` is the window holder and E5 consists of exactly
   those actions. It also currently binds `inference` in a way that suspends part of its own goal
   (server ownership). Both readings are deliberate and stated, but the phrasing "for every main"
   would be self-contradictory taken literally, so it is recorded here rather than resolved silently.

4. **"Never sit idle" vs. "close the session".** Inherited unresolved from
   `STANDING-MAIN-RULES.md`'s own conflict list, and sharpened by goal-based dispatch: under §3 a
   goal always admits a next derivable action, so "nothing assignable" — the condition
   `OPERATING_CONSTRAINTS.md` says should end in closing the session — becomes a very rare state, and
   arguably one only the coordinator can declare. Report dry; do not close yourself.
