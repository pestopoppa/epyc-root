# Resolution ledger — 2026-08-12

**Built 08:30Z from artifacts, not from anyone's memory.** Every row carries a commit, a receipt path,
a file:line, or the literal token `NO ARTIFACT`. An item is CLOSED only with a hash or a receipt.
Standing operator instruction this replaces: *"I want all progress logged as it proceeds. No blind spots."*

Verification basis: `git log` across `/workspace` (= `/mnt/raid0/llm/epyc-root`, same inode 96604698),
`/mnt/raid0/llm/epyc-orchestrator`, `/mnt/raid0/llm/epyc-inference-research`, since 2026-08-11T23:00Z;
the live session bus; `artifacts/operator/receipts/`; `token-queue.md`; the five lane handovers in
`docs/reviews/`; `progress/2026-08/2026-08-12.md`; `artifacts/operator/MORNING-PACKAGE-20260812.md`.
Handovers and reviews are **analyses, not proof of resolution** — nothing enters §4 on their word alone.

---

## 1. UNOWNED — the blind spots

**This section is not empty.** Ten items. None has a named owner. Rows U-1 to U-3 are one failure with
three faces and are the reason the rest of this file could not be reconstructed from the bus alone.

| # | Item | Evidence (measured 08:26–08:31Z) | What "done" looks like |
|---|---|---|---|
| U-1 | **The bus cannot see 7 of its 8 agents.** `stuck_state.json` reads `"unreadable:FileNotFoundError"` for auditor, codex-bus-tests, inference, mainA, mainB, mainC, mainD — only `coordinator-agent` is readable. `boundary_state.json` reads `None\|None` for mainA/mainC/mainD/auditor/codex-bus-tests. On disk: `heartbeats/` has 4 files (of 8), `cursors/` has 1 (of 8), `outbox/` has 3 (of 8). | `coordination/session-bus/stuck_state.json`, `boundary_state.json`; `ls` of the three dirs; 8 `stuck-state-unreadable` + 11 `operator-backlog-unreadable` records in `advisory.jsonl` | Cursor + heartbeat file restored for each roster id; `stuck_state.json` shows zero `unreadable` |
| U-2 | **The loss is invisible to `git status`.** `a70dbe1a` untracked the 33 live bus files (correctly, via `git rm --cached`) and gitignored the paths (`.gitignore:90-97`). The on-disk files are now gone anyway, and because they are ignored, nothing will ever report it. | `git ls-tree a70dbe1a^` lists all 24 cursor/heartbeat/outbox files; `.gitignore:93-96` | Either restore from `a70dbe1a^` or record deliberately that the reset was intended |
| U-3 | **mainC's and mainD's overnight outboxes are unrecoverable.** Recoverable at `a70dbe1a^`: auditor 137 lines, inference 85, mainB 56, coordinator-agent 46, mainA 35. **mainC and mainD committed blobs were already 0 lines** — their live content was never committed and is now off disk. | `git show a70dbe1a^:coordination/session-bus/outbox/<id>.jsonl \| wc -l` | mainC/mainD re-state their overnight reports, or it is written off explicitly |
| U-4 | **Root repo has diverged and the gap is growing.** `/workspace` main: **315 ahead / 140 behind** `origin/main`, merge-base `3dd1ec1b` (2026-08-11T02:48:35Z). `MORNING-PACKAGE-20260812.md` recorded **285/106** at 05:3xZ — it grew by 30/34 with nobody executing the runbook. Research repo: **11 ahead / 182 behind**. Orchestrator: 2 ahead / 0 behind. | `git rev-list --left-right --count HEAD...origin/main` in each repo | Runbook `artifacts/operator/quiesce-merge-push-reboot-20260812.md` (`9c8fd6fe`) run end to end |
| U-5 | **The merge blocker is cleared and nobody acted on it.** mainA's `??`-status `agents/shared/HARNESS_RUN_POLICY.md` is absent from disk; backup at `/mnt/raid0/llm/tmp/era-repair/HARNESS_RUN_POLICY.stray-backup.md`. The only stated obstacle to U-4 is gone. | `ls agents/shared/HARNESS_RUN_POLICY.md` → no such file | Same as U-4 |
| U-6 | **The hardware-idle backfill runner is not running.** `5af987ef` shipped it to close a measured 3h47m idle gap. No process exists; `coordination/backfill/` contains only `README.md` — no queue. `backfill_supervisor.sh` was deliberately not started by that commit. | `ps` shows no backfill process; `ls coordination/backfill/` | Supervisor started, queue non-empty, one bus finding emitted |
| U-7 | **DebugBench oracle rebuild has no owner.** auditor handover, verbatim: *"mainC opened the remediation row; needs an eval-pipeline owner."* The oracle is vacuous (`e6e3644a`): 3,233 of 4,250 rows (76.1%) pass by echoing the buggy code. Every score under this config is uninterpretable. | `e6e3644a`; `docs/reviews/auditor-morning-handover-20260812.md` | An owner named, or the suite marked unusable in the registry |
| U-8 | **Four orphaned validators.** `scripts/validate/check_ratification_receipts.py` — zero references since it landed 08-02. `index_state.py --check` — bound by CLAUDE.md, no mechanism runs it. `verify_llama_cpp.sh` failure is **warn-and-continue** inside `session_init.sh`. Bench adapter's `datasets`/`pyarrow` live only in system python3, so a venv-invoked bench takes the adapter's fail-open `except`: one stdout line, 0 items, no abort | `progress/2026-08/2026-08-12.md:1630-1634, 1653-1661` (auditor: *"wiring deliberately NOT landed unilaterally — options packaged to coordinator"*) | Each either wired to a caller or deleted |
| U-9 | **AM Track-2, claimed-deployed but DROPPED — re-port decision unowned.** auditor's own word is `unowned`; it was routed and nobody took it. Same entry records SC12's write-side window **missed at the v9 freeze**, and DAR L489 now blocking 7 further rows | `progress/2026-08/2026-08-12.md:271-273` | An owner named, or the re-port explicitly declined |
| U-10 | **The daemon wedged again after its own fix.** `f5f8ad97` closed the bootstrap chain at 00:45:19Z (`advisory.jsonl` 1,044 MiB → 0, daemon CPU 29.5% → 1.8%). At **08:20:27Z** `bus_supervisor` found it unhealthy again — *"heartbeat age 999999s"* — killed pid 2759575 and relaunched. That restart is what reset the bus state in U-1 and destroyed the advisory history in COR-6. Nobody owns the recurrence | `logs/bus_supervisor.log`; `advisory.jsonl` earliest record 08:20:31Z | Root cause of the 999999s heartbeat found, or a standing detector for it |

**Owner-adjacent but still unowned:** C39 e8-v4 keyed-receipt patch. mainD's handover says *"Not closed,
and it is yours"* and names nobody. Patch `artifacts/operator/e8v4_keyed_receipt_20260812.patch` (`51738208`),
**unapplied**, two known defects — mainD's own instruction is *"Do not sign it as it stands."* See §3.

---

## 2. OPEN, WITH OWNER

| Item | Owner | Done = | Open since | Artifact |
|---|---|---|---|---|
| MMLU-Pro A3 control: two parameter rulings (SPEC flag string; kernel label v7-vs-v9) | coordinator-agent + inference | Both rulings issued, then the ~15 min run fired with explicit `max_hold_s` | 08:20:46Z | `outbox/mainB.jsonl` msg-20260812T082046Z-1-mainB; manifest research `4dbc9840` |
| A4 E8 frozen-kernel worktree — one command a sandbox classifier refuses to mainB | mainB + operator | `/mnt/raid0/llm/llama.cpp-v8-e8` exists (detached @ `67a433bf`) | overnight | `docs/reviews/mainB-overnight-handover-20260812.md` L120-127 |
| A14 GateDecision echo — parked branch `a14-gatedecision-echo` @ `a7d7bdb6`, 6 files +299/-0, 9 tests | coordinator + inference | Cherry-picked (NOT `--ff-only`) onto main | overnight | branch `a7d7bdb6` |
| P0-0 — 7 red tests, standing prediction all go green with zero test edits | inference | Tests run post-reboot | overnight, compute-gated | `3c7edafc` |
| T8 — 7 unqualified `ingest_long_context` tok/s quotes across 5 owners' handoffs | coordinator | All 7 qualified or removed | overnight; gated on merge landing | `7dddce0f` (research) |
| W4 `migration_status` | coordinator | — | overnight | **NO ARTIFACT** — named only in mainB's handover |
| toc L449 build half — needs the A/B owner's artifact **event schema** | auditor | Schema supplied, half certified | overnight | `40aa9d38`, `723a3539` |
| HS-OD-1 activation (refuse unhonoured OpenAI body fields) | inference | Activated at inference's own boundary | 02:16Z | orch `cbe551e8` (pushed) + 30 tests |
| E5 re-measurement (gemma non-MTP arm) | mainA | **CLOSED** — 18/18 cells, error_rate 0.0, 43/43 req/cell, observation-grade (13d18h uptime voids decision-grade). Remaining E5 rows T3/T10/T12/`stack_numa` still compute-gated. | research `703a80a2` + `4cca1bd7`, orchestrator `efbbbbe9`, root `23a323a0` |
| **8 stale claims older than 300 h**, all from the 2026-07-29 fleet death — `inference` **5**, `auditor` 1, `mainB` 1, `mainD` 1. An agent can only release its own | each holder | All 8 released | since 2026-07-29 (**~13 days**) | `progress/2026-08/2026-08-12.md:1256-1259` |
| ↳ **`inference`'s dead claim has been sitting on `mainC`'s assigned work (A10) all night** — *"1b. Migrate research consumers … delete each duplicate extractor"* | inference | Claim released, A10 unblocked | ~13 days | `progress/2026-08/2026-08-12.md:1263-1265` |
| `autopilot-decision-plane-audit:307` — producing an "after" runs BigCodeBench test code | inference (compute) | Re-run under deterministic code scoring | overnight | `progress/2026-08/2026-08-12.md:1858-1863` |

**Flagged — open >2h with no landing artifact:** W4 (`migration_status`) and T8 both sit with
`coordinator` and neither has moved since the overnight handovers. Both predate the 05:3xZ morning
package and appear unchanged in it. Per the recurrence check, these were never blocked.

---

## 3. AWAITING THE OPERATOR

| # | Decision | Verified at | Note |
|---|---|---|---|
| O-1 | **`coordinator_daemon.authority: manual` → `assign`** | `coordination/session-bus/config.yaml:83` | While manual, the daemon logged **114 `would-assign`** and **20 `would-idle`** records in a 7-minute window (20 per agent × 6 agents) that it could not act on. `advisory.jsonl` |
| O-2 | **Widen roster `lanes`** | `config.yaml` roster: mainB `[gpu,none]`, mainC `[none]`, mainD `[none]`, auditor `[none]` | **7 `lane cpu not in <id> roster lanes` rejections each** for exactly those four, in the current shard. The often-quoted **5,292** figure is **not reproducible** — see COR-6. Rejection site: `scripts/coordination/session_bus_coordinator.py:503` |
| O-3 | **A `hardware-backfill` roster row** | `scripts/coordination/hardware_backfill.py:120` sets `AGENT_ID = "hardware-backfill"`; roster ids are `auditor, codex-bus-tests, coordinator-agent, inference, mainA, mainB, mainC, mainD` | `_require_roster_id` refuses the append, so the new runner's findings **cannot reach the bus**. The script's own docstring says so at :81-82 |
| O-4 | **OP-16 host reboot** — *the operator has stated the reboot happens only after this cleanup is resolved, not before* | uptime **13 d 18:44** at 08:25Z (was 13 d 15:49 in the morning package) | The mechanical refusal is **`freq_under_load`**, not the uptime gate: `preflight_canonical.py:395-421` FAILs when boosting cores < `FREQ_BOOST_MIN_CORES`, with the literal fix *"REBOOT the host"*. `gate_uptime` only WARNs past 2 d (:75-99). `inference` correctly refused to patch around it |
| O-5 | **Six ratified gates still showing `[ ]`** | `token-queue.md` :134, :144, :292, :302, :312, :322 | All six receipts read `status: ratified` — verified by reading each JSON. Receipts are authoritative; the daemon never ticks a box |
| O-6 | **Two gates that must NOT be signed** | `token-queue.md` :351 and :154 | `APPLY-C39-KEYED-RECEIPT-E8V4-20260812` — **withdrawn by its own author**; the daemon's own notice records mainD filing it 01:21:10Z and reporting the same task complete 01:41:39Z (`msg-20260812T014139Z-235-mainD`); two known defects. `RATIFY-E9-ROUTING-REWARD-ERA-20260729` — **superseded, and now mechanically un-runnable**: its command asserts `sha256 == 6aedacad…`, the live file is `b1afb679…`, and it asserts `'id: E9-routing-reward' not in t` while the file already contains it. Signing it produces an `AssertionError`, not a change |
| O-7 | Two capability gates blocking the daemon | `token-queue.md:36`, `:38` | `triage: NOT IMPLEMENTED, gate triage not granted, triage_calls_per_day=0`; `headless_workers: NOT IMPLEMENTED, gate headless-worker not granted, max_headless_workers=0`. Reported as `capability_blockers` in every saturation record |

---

## 4. CLOSED — with the commit that proves it

All 11 hashes below were re-resolved against `git log` at 08:24Z. **All 11 are correct as given.**

| Item | Commit | Landed | Verification beyond the hash |
|---|---|---|---|
| Hook-2 revert (destructive-revert guard, fired twice in one night) | `3d8800e6` | 07:38Z | Reverts `03e17111` |
| Pattern-kill hook narrowed to pkill-only | `e08fe836` | 07:42Z | **Executed at the hook:** `pgrep -f llama-server` → exit **0** (allowed); `pkill -f llama-server` → exit **2** (blocked) |
| Doorbell — payload to the bus, panes only rung | `777f826e` | 07:53Z | — |
| Hardware-idle backfill runner + detector | `5af987ef` | 07:50Z | Code landed; **not running** — see U-6 |
| Bus-root canonicalisation, one strategy | `8b308468` | 07:59Z | `session_bus.py:48` `get_bus_root()`; `merge_gate.py` imports it |
| Worktree machinery + migration doc | `724b5f85` | 08:18Z | — |
| Worktree-correct pre-commit wrapper + SHARED_REPOS | `dc5317d7` | 08:10Z | — |
| FETCH_HEAD resolution fix for worktrees | `8de1f2c7` | 08:15Z | — |
| `worktrees/` gitignore | `5df3c9eb` | 08:20Z | Commit states plainly it does **not** close the hazard — see COR-4 |
| `start_orchestrator_test.sh`: stop resolving by name pattern | `81412a6e` | 06:27Z | Orphaned fix, twice destroyed, landed on the third attempt |
| `start_orchestrator_test.sh`: stop ADVICE taught the removed stop CODE | `c46caf24` | 06:37Z | Follow-up to `81412a6e` |

**Four ratifications signed by the operator, each with a receipt read on disk:**

| Gate | Receipt index | Vehicle |
|---|---|---|
| `RATIFY-ANNEXG-V9-CURRENCY-20260811` | `artifacts/operator/receipts/RATIFY-ANNEXG-V9-CURRENCY-20260811.json` | `artifacts/operator/ratify_annexg_v9_currency_20260811.json` |
| `RATIFY-CONSOLIDATED-ERA-ROWS-20260811` | `…/RATIFY-CONSOLIDATED-ERA-ROWS-20260811.json` | `…/ratify_consolidated_era_rows_20260811.json` |
| `RATIFY-V9-CPU-BENCH-ERA-ADVANCE-20260811` | `…/RATIFY-V9-CPU-BENCH-ERA-ADVANCE-20260811.json` | `…/ratify_v9_cpu_bench_era_advance_20260811.json` |
| `RATIFY-CPU-BENCH-BINARY-VERSION-20260811` | `…/RATIFY-CPU-BENCH-BINARY-VERSION-20260811.json` | `…/ratify_cpu_bench_binary_version_20260811.json` (applied as `49873fdc`) |

All four read `"status": "ratified"`. Two older gates (`…FG4B-AFFINITY-20260729`, `…E8-FINAL-C1-RETRY-CAPACITYFIX-20260729`)
also hold ratified receipts and are part of the six unticked boxes in O-5.

---

## 5. IN FLIGHT

| Work | Owner | State at 08:31Z | Artifact |
|---|---|---|---|
| M1 + M4 daemon milestones, plus the `campaign.py:2344-2346` `max_hold_s` fix | subagent | Defect confirmed: `acquire_device_claim(device_id, purpose=…, campaign_id=…, journal=journal)` passes **no `max_hold_s`**, while `inference_lock.py:375` accepts it and `:444` falls back to `_max_lock_hold_s()`. An abandoned device claim does not self-release | `/mnt/raid0/llm/epyc-inference-research/scripts/kernel_rnd/autokernel/campaign.py:2344-2346` |
| `steer`, rescoped to `authority.cross_main` | auditor | `authority.cross_main: [operator, coordinator-agent]` exists at `config.yaml:73`; **no `steer` implementation found** anywhere in `scripts/coordination/` | **NO ARTIFACT** |
| Worktree cutover (P2 — P1 landed) | — | P1 machinery landed (`724b5f85`, `dc5317d7`, `8de1f2c7`, `8b308468`, `a70dbe1a`, `5df3c9eb`). Cutover itself not started; **no owner named** | see §4 |
| MMLU-Pro hardened control | mainB → handed over | mainB `idle`, out of context, package delivered, 2 rulings pending (§2). GPU verified free: `rocm-smi` GPU use **0%**, zero KFD PIDs | research `4dbc9840` |
| E5 gemma no-MTP, CPU lane | mainA | **TERMINAL, not running** — driver 2854220 exited; 18/18 cells banked, 0% error; no servers of mine remain, ports 19380-19383 clear. The `load 151.5 / 4 PIDs` reading was the run mid-flight and is now stale. | `703a80a2`, `4cca1bd7` |

---

## 6. CORRECTIONS TO THE RECORD

| # | Claim as stated | What is true | Corrected by / evidence |
|---|---|---|---|
| COR-1 | Compute duty cycle **~19–20%**, escalated 01:24:55Z as waste on a night the operator asked not to waste compute | **~8–9%** across 23:00Z–05:00Z — ~30–32 min of hardware-holding work in 360, reconstructed from device-claim receipts. The 19–20% figure is arithmetically correct but scoped only to 23:00–01:24Z | Coordinator **retracted it itself** at 02:05:25Z. Restated in `artifacts/operator/MORNING-PACKAGE-20260812.md` §3 because *"the retraction lives only on the bus — there is no coordinator handover in `docs/reviews/`"* |
| COR-2 | Checkbox delta **1283→1265 open, 2294→2385 done** | **1273 → 1242 open (−31), 2306 → 2368 done (+62)**, by `grep -c '^\s*- \[ \]'` over `git archive <ref> handoffs/active`. The circulating pair **does not reproduce at any commit tested** — the coordinator's tick counter used a different scope | `MORNING-PACKAGE-20260812.md:34-39`. Circulating pair declared **unsourced** |
| COR-3 | Compute "has two takers" | Only **messages had been sent**. Dispatch was reported as utilisation three times in an hour | Coordinator's own dispatch note, `outbox/coordinator-agent.jsonl` msg-20260812T082244Z-*; **no dispatch-as-utilisation artifact survives** the bus reset (U-3) |
| COR-4 | `worktrees/` is a live hazard: a `git clean` would delete 29 worktrees including inference's 15 live campaign trees, and the gitignore closes it | Both halves were wrong. `git clean -ndx` prints **"Would skip repository"** for all 29 — git skips nested repos, so **`-fdx` removes none**. Only **`-ffdx`** removes them, as a single entry. And the gitignore **does not fix it**: `-x` re-includes ignored paths and `-ff` defeats the nested-repo skip. It buys 29 untracked lines off `git status` out of 232 dirty entries | mainD measured rather than assumed; recorded in the commit message of `5df3c9eb`. **The count is 29, not 20** — no "20" appears anywhere in the record |
| COR-5 | A `llama-server` at 0.1 %CPU was reported as a running measurement | It was a **69-second config probe** | Caught in-conversation; **no surviving artifact** — the outbox that carried it is among the files lost at U-3. Recorded here so the correction is not lost with it |
| COR-6 | Four mains rejected `lane cpu not in roster lanes` **5,292 times each** | The **four agents are confirmed** — mainB, mainC, mainD, auditor, exactly, and exactly on `lane cpu`. The **count is not reproducible**: the current shard holds **7 each**. `advisory.jsonl` was never tracked in git, has one shard, no rotation archive, and its earliest record is **2026-08-12T08:20:31Z** — the daemon restart. All prior daemon evidence is gone | Re-measured from `advisory.jsonl`; rejection site `session_bus_coordinator.py:503` |
| COR-7 | (New, found while building this) The daemon also logs **57 `lane none not in codex-bus-tests roster lanes`** rejections in the same 7-minute window | `codex-bus-tests` is `role: retired, lanes: []`. The daemon repeatedly tries to assign to a retired agent, at 8× the rate of any live one | `config.yaml:35`; `advisory.jsonl` |
| COR-8 | (New) `co_residency` reports `live_roles: []`, `matrix_status: "stale"` | Four `llama-server` processes are live at 2762–3329 %CPU. The co-residency view is blind to the running fleet | `advisory.jsonl` saturation records vs live `ps` |
| COR-9 | **"Uncommitted work does not survive a reboot"** — broadcast fleet-wide, and it changed behaviour: it is the stated reason `mainC` committed another agent's work rather than leave it | **False.** `df --output=source,target` puts `/workspace`, the scratch dir and the agent-memory dir all on **`/dev/md127`** — one persistent RAID. A host reboot does not touch the working tree. 172 dirty paths outside the bus, net −3,197 lines, all predating the session | mainA proved it; **the coordinator retracted its own broadcast to the same five agents in the same channel**. `progress/2026-08/2026-08-12.md:2179-2187`, cf. `:1605-1606` for the decision it drove |
| COR-10 | Two counts still **unreconciled between lanes** — nobody has adjudicated them | Merge-branch changed paths: mainD derives **67**, mainA derives **72**, same merge-base `921113ed`. Worktrees off `/mnt/raid0/llm/llama.cpp`: mainB's handover says **9**, the morning package says **24** | `progress/2026-08/2026-08-12.md:879-882` vs `:2077-2093`; `docs/reviews/mainB-overnight-handover-20260812.md` L143 vs `MORNING-PACKAGE-20260812.md:16`. Both remain open discrepancies, not settled facts |

---

## 7. HOW THIS FILE STAYS TRUE

1. **Owner:** `coordinator-agent` owns the file. Every other agent owns its **own rows** and may correct
   them directly — the standing instruction broadcast at 08:22:44Z tells all five mains and the auditor
   to do exactly that, without waiting to be asked.
2. **When:** at every task boundary, and immediately when an item **lands**, **blocks**, or is discovered
   with **no owner**. Not at wrap-up. The artifact is the status.
3. **The CLOSED rule:** an item moves to §4 **only** with a commit hash or a receipt path, and the hash is
   re-resolved (`git log -1 <hash>`) at the time it is written. A claim without a hash stays in §2.
   A "done" that cannot be resolved is written as `CLAIMED-UNVERIFIED` with the missing evidence named.
4. **The UNOWNED rule:** §1 is first and is never omitted. If it is genuinely empty, it says so in words.
   An item whose owner is a paused, absent, or context-exhausted session belongs in §1, not §2.
5. **Corrections are rows, not edits.** A retraction is a claim and gets the same verify-by-artifact
   standard as the claim it withdraws. §6 grows; it is never pruned.
6. **Recurrence check:** any row appearing here twice running with an unchanged blocker is proof it was
   never blocked. Do it before writing anything else.
