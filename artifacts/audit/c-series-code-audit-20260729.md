# Adversarial code audit — session-bus C-series, 2026-07-29

**Scope**: every C-row landed on the delivery plane on 2026-07-29 (C24–C36 plus P1b), in
`scripts/coordination/tmux_adapter.py`, `session_bus.py`, `session_bus_coordinator.py` and their
suites. Read-only audit; no source edited, nothing committed, no checkbox flipped. The live `agent`
tmux session was never written to — no `send-keys`, no `attach`, no `new-window`. Two read-only
calls were made against it (`list-windows`, `display-message -p`), the same class the C35/C36
commits used for their own corroboration.

---

## Headline verdict

**The C-series is substantially sound, and better evidenced than most code of its kind.** 27 of the
30 fault-injections I planted were killed by the existing suites; the two load-bearing empirical
claims (C35's detached `window_activity` premise, C36's rollout-tail premise) both survive
independent re-measurement; and C36 demonstrably works against the live fleet.

It is **not** clean. I found one genuine fail-open that the module's own stated invariant forbids
(FO-1), one demonstrated false invariant with a fixture that hides it (FO-3), one crash path (WI-3),
and — most relevant to the brief — **three further instances of the exact "boundary test that never
hits the boundary" class the author caught once in their own work** (WT-1, WT-2, WT-3). All three
were found by mutation, not by reading; all three survive mutants that delete or weaken the guard
the test is named after.

Separately, and independent of correctness: **the suite is green only under an interpreter that has
`jsonschema`.** Under `/usr/bin/python3` — the interpreter `CLAUDE.md` and `BUS_PROTOCOL.md`
instruct every agent to use for `session_bus.py` — one test is red at HEAD, and the commit that
claims to have repaired that file states "16/16 green" without naming an interpreter (WT-6).

I could not convince myself C35 is safe for the three Claude mains in the general case (FO-2). I did
not prove it broken, and today's measurement says its premise holds; the residual is that nothing
automated will tell you when it stops holding.

### Test results I ran myself

Canonical root `/mnt/raid0/llm/epyc-root` (per `pytest.ini`).

| Interpreter | Suites | Result |
|---|---|---|
| `epyc-orchestrator/.venv` (jsonschema 4.26.0, pytest 9.0.3) | `tests/test_tmux_adapter.py` + `tests/test_session_bus.py` + `scripts/coordination/tests/` | **357 passed** (75 s) |
| same | `tests/test_tmux_adapter.py` + `scripts/coordination/tests/test_tmux_adapter_live.py` | **103 passed** — 101 unit + 2 live wrappers carrying **72/72** internal checks |
| no-jsonschema interpreter | `scripts/coordination/tests/test_routing_intent.py` | **1 failed, 15 passed** |
| no-jsonschema interpreter | `tests/test_tmux_adapter.py` + live | **103 passed** (adapter is interpreter-independent) |

The live suite created and killed its own `busadapter-test-<pid>` sessions only. My own
measurements used throwaway `auditc35-<pid>` / `auditcap-<pid>` / `auditlive-<pid>` sessions,
all killed.

---

## FAIL-OPEN RISKS

*(worst first; every item states the concrete state that triggers it)*

### FO-1 — C36 `runtime: idle` silently waives the "no heartbeat — fail closed" blocker

`scripts/coordination/tmux_adapter.py:1111-1121`

```python
if runtime_state == "active":
    blockers.append(...)
elif runtime_state == "idle":
    pass                      # heartbeat blockers below are skipped entirely
elif hb is None:
    blockers.append("no heartbeat — cannot tell if the agent is thinking; fail closed")
```

`elif` chaining means a runtime `idle` skips **the missing-heartbeat blocker as well**, not only
`working` and staleness. The commit body and the in-code comment both enumerate exactly two things
runtime-idle clears — "`the heartbeat's working AND its staleness`" — and neither mentions this
third. The permissive scope is wider than the documented change.

**Demonstrated.** With no `heartbeats/m.json` on disk and the pane active *right now* (so C35 cannot
be the cause):

```
NO heartbeat file on disk: True
  runtime=idle  -> nudge_ok=True   blockers=[]
  runtime=None  -> nudge_ok=False  blockers=['no heartbeat — cannot tell if the agent is thinking; fail closed']
```

It is worse than "absent", because `heartbeat()` (`tmux_adapter.py:453-458`) catches
`OSError` *and* `json.JSONDecodeError` and returns `(None, None)` for both. A **corrupt or
truncated** heartbeat file is therefore indistinguishable from a missing one, and takes the same
permissive path. That is the module's own definition of a fail-open: an unevaluable signal producing
permission rather than refusal.

**Untested.** Mutant `M17` — `elif runtime_state == "idle" and hb is not None:`, i.e. restoring the
old refusal — leaves **all 101 adapter tests green**. Nothing pins this behaviour in either
direction.

Not currently exploited: all eight roster heartbeats exist and parse. Severity is "a guard whose
whole purpose is fail-closed was removed for the four Codex mains, undocumented and unpinned",
not "it is misfiring today".

**Repair options** (either is defensible; the point is that it should be a decision, not a
side effect of `elif`): restore `hb is None` as an unconditional blocker independent of the
runtime, or keep the waiver and say so explicitly in the comment + a test, and split
`heartbeat()`'s absent/corrupt cases so a corrupt file can never take the same path as a missing
one.

### FO-2 — the three Claude mains are governed *only* by C35's heuristic, and nothing guards its premise for a real Claude pane

`tmux_adapter.py:1058-1064` (detached skip), `:1122-1137` (the override), `runtime_liveness`
Claude branch `:912-915`.

Verified read-only against the live fleet at 19:30Z: `runtime_liveness` returns `None` for `mainA`,
`coordinator-agent` and `auditor` — correct and honest, but it means for half the roster the entire
C36 protection is absent and the decision falls to C35 alone.

For those mains the chain is: the normal `--quiet-s` check is **skipped entirely when the session is
detached** (`quiet_check = "skipped: session detached…"`, line 1064) — and detached is the normal
overnight state, which is exactly when this system is supposed to be doing its job. So the only
pane-derived guard left is C35's own `quiet_for >= 120`.

That rests on one empirical claim: a TUI that is generating redraws at least once every 120 s.
**I re-measured it independently** rather than trusting either the 2026-07-27 reading (which said
detached tracking does not work) or the 2026-07-29 re-measurement (which said it does). Throwaway
detached session, three windows, sampled every 15 s for 105 s:

```
t=105s attached=0
   busy     quiet_for=0s      (printf every 0.2s)
   altbusy  quiet_for=0s      (redraw inside the ALTERNATE screen, as a TUI does)
   idle     quiet_for=105s
```

**The 2026-07-29 re-measurement is correct and the 2026-07-27 one was wrong**, including for
alternate-screen redraw, which neither prior measurement covered. C35's premise holds today.

The residual is that nothing will tell you when it stops. The live premise check
(`test_tmux_adapter_live.py:305-317`) asserts it against a synthetic `printf` emitter, not against a
Claude Code pane. A Claude state that is genuinely static for >120 s while the heartbeat still says
`working` — a permission modal, an `AskUserQuestion`, a paused tool approval — would satisfy the
override.

**What stops this being a high-severity finding** is a guard that is easy to miss and is doing real
work: `cmd_nudge` refuses to press Enter unless the composer *ends with* the message
(`tmux_adapter.py:1285-1289`), and a full-screen modal makes that check fail —
`"the pane is not accepting typed input (a full-screen modal, e.g. Codex backtrack mode, does this)"`.
So the realistic worst case is a refused nudge with typed text left in a pane, not a corrupted
generation. That mitigation is not mentioned in the C35 rationale, and it should be, because it is
what carries the risk.

### FO-3 — the C24 containment invariant is FALSE for cross-session endpoints, and its test uses a fake that cannot show it

`tmux_adapter.py:1477-1500` states, as the invariant that makes the heartbeat reset safe:

> AN IDENTITY `live_mains` CANNOT SEE IS AN IDENTITY `resolve_target` CANNOT REACH.

**Demonstrated false against real tmux.** Two throwaway sessions; roster row
`{"id":"ghost","endpoint":"tmux:auditother-N:ghostwin"}`, `tmux.live_session = auditlive-N`:

```
live_mains ids = set()                          | 0 roster main(s) live in session 'auditlive-N'
resolve_target = auditother-N:ghostwin          | endpoint names window 'ghostwin' (verified)
CONTAINMENT BREACH
```

`live_mains` (`tmux_adapter.py:569, 587-594`) only ever lists windows of `tmux.live_session` and
matches the endpoint's *window component* against that list; `resolve_target` addresses the session
the endpoint actually names. Uncounted **and** resolvable.

The C24 test set deliberately excludes this shape, with the justification (`tests/test_tmux_adapter.py:843-846`)
that "live_mains applies the endpoint match even across sessions, deliberately — so that is the safe
direction". That is only true when a window of the same *name* also happens to exist in the live
session. When it exists only in the foreign session, it is the dangerous direction.

`test_c24_cross_session_endpoint_overcounts_and_still_refuses` (`tests/test_tmux_adapter.py:927`)
passes because `_tmux_semantics` returns `(0, "")` for any session other than its own
(`tests/test_tmux_adapter.py:827-828`) — real tmux behaviour for an **absent** session, not for a
foreign session that exists. This is a fixture-fidelity defect of precisely the class that fixture's
own docstring warns about ("a fake that simply fails on a miss would make the invariant below pass
vacuously").

**Why it is not live today**: `cmd_spawn` refuses `session != live` at `tmux_adapter.py:1400-1404`,
*before* the heartbeat reset at `:1526`. So the specific C24 hazard is contained — but by a
different guard than the one the comment names, which means the documented reasoning would not
survive someone relaxing that check. Two secondary consequences stand regardless:

* a cross-session roster row is **never counted** by `live_mains`, so it undercounts the concurrency
  cap — "invent capacity", the polarity `live_mains`' own docstring says it must never take;
* no roster row uses a foreign session today, so this is latent in the same way C32 was latent right
  up until it wasn't.

### FO-4 — the fleet's real nudge rate limit is 20 s, set in two untested shell wrappers

`scripts/coordination/nudge_retry.sh:16` and `scripts/coordination/idle_supervisor.sh:71` both pass
`--min-interval-s 20`, overriding the adapter's 600 s default. `idle_supervisor.sh` then retries
every 40 s indefinitely (`POLL=40`, `CONFIRM=2`, `MAX=86400`).

This does **not** bypass any probe guard — every blocker still applies, so it cannot type into a
mid-generation pane. But C31's entire design discussion reasons about a 600 s limit whose purpose is
"to avoid pestering a working session", and the deployed value is 20 s. Neither script has a test
(`scripts/coordination/tests/` has `test_bus_supervisor.py` but nothing for `nudge_retry.sh`,
`idle_watch.sh` or `idle_supervisor.sh`).

Two smaller notes on the same two files, both fail-closed and therefore low priority:

* both locate a main's pane as `"$SESSION:$w"` — **the roster id, not the endpoint's window** — which
  is C25 exactly, re-derived a third time in a third place. `coordinator-agent` (window
  `coordinator`) is not in either `MAINS` list, so no live mismatch; the failure mode if it were
  would be a silent permanent UNKNOWN, not a false idle. I verified that `tmux capture-pane -t
  sess:missing` returns **rc=1**, unlike `display-message`, so the fallback-to-current-window hazard
  does *not* apply here.
* `idle_supervisor.sh:39` hardcodes `MAINS="inference auditor mainA mainB mainC mainD"`, already
  drifted from the roster (`coordinator-agent` absent).

---

## WRONG-OR-INCOMPLETE FIX

### WI-1 — C35 does not remove the deadlock it names, in the case it names

C35's own framing: a main that finishes a unit "still says `working`, because the code that would
update the heartbeat is exactly the code that has stopped running". But the code that stopped
running also stops *refreshing* the heartbeat — so the same session acquires the **staleness**
blocker (`--heartbeat-max-age`, default 900 s) alongside the `working` one, and C35 deliberately
removes only the latter (`tmux_adapter.py:1140-1141`; commit: "Staleness stays a separate blocker on
purpose").

**Live evidence**, read-only probe of the whole roster at 19:30Z:

```
mainA              rt=None hb=working  age=2178s   BLOCKED heartbeat says working (task r1-caveat-replay)
                                                   BLOCKED heartbeat is 2178s stale (> 900s)
coordinator-agent  rt=None hb=working  age=18226s  BLOCKED heartbeat says working (task fleet-bringup-watch)
                                                   BLOCKED heartbeat is 18226s stale (> 900s)
```

These are the two Claude mains — no C36 coverage — and both carry *both* blockers. Even a fired C35
override leaves them un-nudgeable. C35 therefore helps only in the roughly 0–15 minute window after
a main stops; past that, the operator still hand-relays or raises `--heartbeat-max-age`. The
motivating incident the commit cites (mainA holding the whole machine for an exclusive E5 window,
four hand-relays in a day) is not obviously inside that window.

The trade-off is disclosed in the commit body. The *headline* — "let pane quiescence override a
stuck `working` heartbeat", "THE DEADLOCK THIS REMOVES" — is not accurate about the stopped-agent
case, and the C-row should say so.

### WI-2 — C36 discards C35's audit trail on what is now the primary path

`tmux_adapter.py:1328-1336`. `cmd_nudge` records `heartbeat_override` / `window_quiet_for_s` only
when `heartbeat_override_applied` is true. When the **runtime** clears a `working` heartbeat, that
flag stays `False` and `heartbeat_override_reason` stays `None` (the C35 branch is skipped entirely
at line 1113), and nothing records `runtime_state` or `runtime_reason`.

So a ledger row for a nudge that overrode a `working` heartbeat via C36 — now the path for four of
eight roster ids — is byte-identical to an ordinary nudge to a genuinely idle main. C35's stated
reason for those fields ("if the override ever does interrupt a real generation, this row is the
evidence") no longer holds for the dominant path. One-line fix: pass `runtime_state`/`runtime_reason`
into `record(...)`; `record` already drops `None` fields.

### WI-3 — uncaught `AttributeError` in the C36 rollout tail parser

`tmux_adapter.py:848`:

```python
payload = json.loads(last).get("payload") or {}
```

catches only `json.JSONDecodeError`. The *head* parser twelve lines above
(`tmux_adapter.py:830`) catches `(OSError, json.JSONDecodeError, AttributeError)` for exactly this
reason. Demonstrated with synthetic rollouts:

```
1. tail is valid JSON but NOT an object ("null")        -> UNCAUGHT AttributeError 'NoneType' object has no attribute 'get'
3. tail's "payload" is a LIST                           -> UNCAUGHT AttributeError 'list' object has no attribute 'get'
```

The exception propagates out of `codex_state_from_rollouts` → `runtime_liveness` → **`probe`**, so
`cmd_probe` and `cmd_nudge` die with a traceback. Direction is fail-*closed* (the coordinator invokes
the adapter as a subprocess at `session_bus_coordinator.py:1374-1381`, so a tick sees a failed nudge,
not a crashed daemon), which is why this is here and not in the fail-open section. But `probe`
becomes unusable for that agent and the operator gets a stack trace instead of a reason — in the one
module whose entire value proposition is legible refusals.

Everything else I probed in that parser is correct and fails closed:

```
2. payload with no "type"        -> ('active', "ends in None, not a turn-terminal record")   [blocks]
4. empty / whitespace-only file  -> _last_line None -> refuse
5. 300 KB last record            -> _last_line exact match, state 'idle'      [the seek-from-EOF loop is right]
6. single line, no trailing \n   -> exact match
7. thread_source present, null   -> refuse ("none declares a non-subagent thread_source")
8. first line not JSON at all    -> refuse
```

### WI-4 — C33's notice is silently skipped when `coordinator-agent` is off the roster

`session_bus_coordinator.py:723`: `if COORDINATOR_AGENT in ids:`. When false, the whole
"token-request-not-presented" notice loop is skipped with no advisory and no alternative sink —
the same silent-drop shape C33 exists to eliminate. Latent (the id is on the live roster).

### WI-5 — `heartbeat()` cannot distinguish absent from corrupt

`tmux_adapter.py:453-458` returns `(None, None)` for both. Harmless before C36; feeds FO-1 now.

---

## WEAK TESTS

Every item below is a mutant I ran. "SURVIVED" means the named guard was deleted or weakened and the
**whole suite stayed green**.

| # | Test | Mutant | Result |
|---|---|---|---|
| WT-1 | `tests/test_tmux_adapter.py:1412` `test_c35_an_unreadable_pane_fails_closed` | `elif dead is not False:` → `elif dead is True:` (`tmux_adapter.py:1122`) | **SURVIVED — 101 passed** |
| WT-2 | *(none exists)* — C36 runtime-idle vs. missing heartbeat | `elif runtime_state == "idle":` → `… and hb is not None:` (`:1113`) | **SURVIVED — 101 passed** |
| WT-3 | `tests/test_session_bus.py:1573` `test_c26_boot_check_is_unknowable_not_false_without_proc_uptime` | `heartbeat_predates_boot` returns `False` instead of `None` when boot time is unknowable (`session_bus_coordinator.py:2553-2558`) | **SURVIVED — 130 passed** |

**WT-1** is the headline. The test's own docstring says *"`dead is not False` is the deliberate
wording — `not dead` would treat None as alive"*, and then never exercises that wording: the fixture
drives `display_rc=1`, which makes **both** `dead` and `quiet_for` `None`, so the refusal is produced
by the *next* guard (`elif quiet_for is None`, line 1124). The test would pass with the guard it
names removed. This is the same shape as the 120.0-boundary mutant the author caught in their own
work — a test whose assertion is satisfied before control ever reaches the code under test.

Honest qualification: today this is an **equivalent mutant**, not a live bug. `dead` and `quiet_for`
are parsed from one `display-message` call (`tmux_adapter.py:961-971`) and `dead` is assigned a bool
whenever that parse succeeds, so `dead is None` ⟺ `quiet_for is None`. The guard is currently
unreachable as a distinguishing branch. That is precisely why it needs a test: a future refactor that
splits those reads can delete the fail-closed half and the suite will not notice. (Removing the guard
*entirely* **is** killed, by `test_c35_a_dead_pane_is_never_overridden_and_still_refuses` — so the
`dead is True` half is covered and only the unreadable half is not.)

**WT-3** is the same shape one file over: the test asserts `boot_time(<missing path>) is None` —
a different function — and never asserts either `heartbeat_predates_boot`'s documented tristate or
the behaviour its own docstring promises ("cmd_status then leaves the pid verdict alone"). Also an
equivalent mutant today, since `None` and `False` are both falsy at the single call site
(`session_bus_coordinator.py:2581`); the docstring's `bool | None` contract invites a future
`is False` caller who would then get the wrong answer.

Three further weaknesses, not mutation-survivals:

**WT-4** — `tests/test_tmux_adapter.py:927` `test_c24_cross_session_endpoint_overcounts_and_still_refuses`
passes only because its fake models a cross-session target as absent. Real tmux disagrees; see FO-3
for the demonstration.

**WT-5** — the C36 live premise check asserts `parsed > 0`, not `parsed == seen`
(`scripts/coordination/tests/test_tmux_adapter_live.py:579`). The commit's claim is "120/120 tails
parse"; the test would pass at 1/120. It read 120/120 and 119/120 terminal on this host, so the claim
is *true* — it is just not the thing being enforced.

**WT-6 — the suite is green only under an interpreter that has `jsonschema`.**
`scripts/coordination/tests/test_routing_intent.py:113`
`test_append_refuses_unknown_routing_target_and_empty_list` asserts that `append` with
`needs_routing_to: []` exits 1 (`# schema minItems 1`). At HEAD:

```
no jsonschema  : 1 failed, 15 passed   (assert 0 == 1  — the empty list is ACCEPTED)
orchestrator venv: 16 passed
```

`/usr/bin/python3` — the interpreter `CLAUDE.md` and `BUS_PROTOCOL.md` tell every agent to use for
`session_bus.py append` — has no `jsonschema` on this host. So this is not a test-environment quirk:
it is C34's fail-open, still open on the authoring path, surfacing as a red test. C34 mitigates it
with an unconditional stderr warning (correct, and well tested) but explicitly does not close it.
Two consequences worth acting on:

* commit `12c56607` claims "16/16 green. 311 passed" without naming an interpreter. That claim is
  interpreter-dependent and is false under the documented one.
* the test should follow C34's own positive control and `pytest.importorskip("jsonschema")`, or
  assert the *warning* under the partial validator. As written it makes the documented agent
  workflow look like a test failure.

---

## SOUND

Everything below I tried to break and could not. Mutation tally across the three files:
**30 fault-injections, 27 killed, 3 survived** (WT-1/2/3 above).

**C36 — the core signal is well built and works live.** Every failure path returns
`None` = UNAVAILABLE and falls back; I could not construct an input that manufactures an `idle`.
Killed mutants: dropping the `thread_source` subagent filter; treating absent `thread_source` as
user; inverting the terminal-record test; picking one of two user rollouts instead of refusing;
treating a torn tail as `idle`; resolving the pane pid by roster id instead of endpoint; ignoring
`runtime: active`; unwiring the whole block. `pid → rollout` mapping is robust *by construction* — it
reads `/proc/<pid>/fd`, i.e. the file the process actually has open, not a name-based guess — so
"belongs to a different session" cannot happen once the pid is right, and the pid comes through the
endpoint. Verified read-only against the live fleet:

```
inference   backend=codex  runtime=active  hb=working age=64s
mainB       backend=codex  runtime=idle    hb=working age=70s
mainC       backend=codex  runtime=active  hb=working age=42s
mainD       backend=codex  runtime=idle    hb=working age=32s   -> nudge_ok=True
mainA       backend=claude runtime=None    hb=working age=2134s  (honest UNAVAILABLE)
coordinator-agent backend=claude runtime=None                    (honest UNAVAILABLE)
auditor     backend=claude runtime=None
codex-bus-tests backend=None runtime=None   (no window — refused, not guessed)
```

`mainD` is the case that justifies C36 over C35: quiet for 30 s, so the C35 override could not have
fired, yet the runtime shows it settled and it is now reachable.

**C35 ⇄ C36 compose cleanly and cannot contradict.** The precedence is total, not additive: when
the runtime answers, control never enters the heartbeat branch that contains the C35 override
(`:1111-1113`). Runtime `active` adds a blocker no other guard could have added. Runtime `None`
leaves the pre-C36 chain byte-identical (pinned by
`test_c36_UNAVAILABLE_changes_nothing_the_pre_C36_chain_decides`, and I killed the mutant that turns
UNAVAILABLE into idle). The only composition defects are the audit-trail loss (WI-2) and the
undocumented `hb is None` waiver (FO-1) — neither is a contradiction between the two rules.

**C32** — index endpoints now verified against `#{window_index}` instead of exempted; unreadable
reply refuses rather than attests. Restoring the digit exemption fails two tests including the C24
containment parametrisation.

**C31** — rate limit re-keyed to the window instance via the spawn epoch in the existing ledger.
Reverting to whole-history is killed. Both fail-safe choices (no spawn row ⇒ keep the old limit;
unparseable ts ⇒ skip, never a permanent block) are stated and correct.

**C30b** — post-spawn survival re-check; the deliberate asymmetry (an *unreadable* window list does
not manufacture a failure) is right, because the window and all four bus files already exist by then.
Removing the check is killed. The commit also fixed the shared C9 fake, which previously never showed
a window it had just created — a genuine fixture defect that would have made every spawn test pass
for the wrong reason.

**C29** — `_require_roster_id` on `drain`/`triage`/`cursor`; refuse rather than warn is the right
call (a warning leaves the cursor advance in place, which consumes another agent's mail). All three
removals are killed independently, and the positive control (rostered ids unaffected) is present.

**C34** — both halves. The unconditional degradation warning is killed when removed, and the
positive control (`test_c34_full_validation_stays_silent`) prevents it becoming a warning nobody
reads. The `already_flagged` dedupe is keyed `(relayed_src, unreachable)` and the new rows carry both
fields, so it is durable across a daemon restart — I checked the load path at
`session_bus_coordinator.py:2125-2130`. The C34 commit also *corrects* an earlier C33 claim in the
under-stating direction, which is the right direction to be wrong in.

**C27a/b/c** — the `_RELAY_HANDLERS` derivation, the relayed-and-flagged fallback, and the outbox
last-hop net are each killed by their own mutant. The reasoning ("duplicating a message costs a read;
dropping one costs a gate") is the correct asymmetry.

**C33, C26, P1b, C25, C24** — all killed by their own mutants (`C33_no_notice_to_coordinator`,
`C26_no_boot_override`, `P1b_no_liveness_check`, `P1b_permissionerror_is_dead`, `M11_c32_index_exempt`
via the C24 parametrisation). P1b's tristate (`PermissionError` ⇒ alive, unusable pid ⇒ unknown) is
right. C26's boot-time override only moves the verdict toward "not running", i.e. fail-closed.

**Live suite quality.** `_assert_checks` (`test_tmux_adapter_live.py:66-76`) genuinely fails the
pytest function — the previously-noted "entry points never asserted" defect is fixed — and the
per-group slice prevents double-reporting. 72/72 internal checks executed here, matching the claimed
count, with the C36 corpus premise really running (120/120 parse, 119/120 terminal).

**Self-criticism in the commits is real, not decorative.** The C24 follow-up (`3d509613`) retracts
its own safety argument and replaces it with a weaker but true one; C34 corrects C33's stated cause;
C36 documents that it repeated C25 inside itself one hour after landing C25, and that a fixture fed
a pane "quiet since 1973". That kind of disclosure is what made this audit tractable, and three of
my findings are extensions of defect classes the author had already named.

---

## Appendix — reproduction

```bash
cd /mnt/raid0/llm/epyc-root
VENV=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python     # jsonschema 4.26.0 + pytest 9.0.3

# full surface
$VENV -m pytest tests/test_tmux_adapter.py tests/test_session_bus.py scripts/coordination/tests/ -q

# the interpreter split (WT-6)
PYTHONPATH=/home/node/.local/lib/python3.13/site-packages /tmp/llama-server-test-venv/bin/python \
  -m pytest scripts/coordination/tests/test_routing_intent.py -q      # 1 failed, 15 passed
$VENV -m pytest scripts/coordination/tests/test_routing_intent.py -q  # 16 passed

# live suite check tally
$VENV scripts/coordination/tests/test_tmux_adapter_live.py            # 72/72 passed
```

Mutation harnesses, edge-case probes and the two tmux measurements are in
`/tmp/claude-1000/-workspace/a06c777b-6cee-4cab-af68-5ef77105a6eb/scratchpad/`
(`mutate.py`, `mutate2.py`, `mutate3.py`, `edge.py`, `demo_hb.py`, `xsess.py`, `c35_measure.sh`)
and are self-contained: they copy or symlink-mirror the repo into a sandbox and never write to
`/mnt/raid0/llm/epyc-root`.
