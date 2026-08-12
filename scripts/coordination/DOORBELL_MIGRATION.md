# Doorbell migration — daemon call sites to switch

`scripts/coordination/tmux_adapter.py` now has a `doorbell` subcommand (C45):
a fixed, content-free, idempotent ring — `Bus: unread inbox for <agent> —
drain now.` — with no `--message` parameter, exactly two fail-closed guards
(pane alive, composer empty), and none of `nudge`'s payload-path guards
(quiet-for, rate limit, heartbeat-state refusal, the C35 override machinery
built to patch that state check). See the C45 comment block in
`tmux_adapter.py`, directly above `doorbell_text`, for the full design
rationale — bus carries payload, doorbell only says "go read it" — and the
33-minute-unreachable incident (2026-08-12) it fixes.

This note is a mechanical work order for `session_bus_coordinator.py`'s
owner, not a design document. It does not modify the daemon: the daemon is
running and mid-quiesce, and it is the coordinator's file, not this
subagent's to edit.

## The two real call sites (payload nudges → switch to doorbell)

Both go through one low-level wrapper, `_tmux_nudge()`, which is the thing
that actually shells out to `tmux_adapter.py nudge`:

### 1. `_tmux_nudge()` — `scripts/coordination/session_bus_coordinator.py:2088-2099`

```python
def _tmux_nudge(agent: str, message: str, min_interval_s: float) -> tuple[int, str]:
    """Shell out to the adapter. Isolated so tests can substitute it wholesale."""
    script = Path(__file__).resolve().parent / "tmux_adapter.py"
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "nudge", "--agent", agent,
             "--message", message, "--min-interval-s", str(min_interval_s)],
            capture_output=True, text=True, timeout=120,
        )
    except Exception as exc:  # noqa: BLE001 — an unrunnable adapter is a refusal
        return 3, f"adapter invocation failed: {exc}"
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or "")).strip()
```

**Action**: add a sibling `_tmux_doorbell(agent: str) -> tuple[int, str]` with
the same shape, calling `tmux_adapter.py doorbell --agent <agent>` — no
`--message`, no `--min-interval-s` (doorbell has no rate limit to pass
through). Keep `_tmux_nudge` itself untouched; both call sites below need to
switch which helper they call, not have this one rewritten out from under
them. Same `nudge_fn`-style seam (`doorbell_fn=None` defaulting to
`_tmux_doorbell`) keeps both functions testable the way `nudge_fn` already
does.

### 2. `resolve_stuck_agents()` — message built at `:2318`, sent at `:2319`

```python
message = _STUCK_NUDGE_MESSAGE.format(unread=unread, agent=aid)
rc, out = nudge(aid, message, _STUCK_MIN_NUDGE_INTERVAL_S)
```

where (`:2081-2085`):

```python
_STUCK_NUDGE_MESSAGE = (
    "Bus: you have {unread} unread inbox message(s) and are idle. Run "
    "scripts/coordination/session_bus.py drain --agent {agent} now, act on what it "
    "delivers, and refresh your heartbeat."
)
```

This is a pure drain-nudge — everything it says is either constant or
derivable from the bus (`{unread}`), never a brief. **Textbook doorbell.**
**Action**: replace the `nudge(...)` call with `doorbell(aid)` (via the new
`_tmux_doorbell`/`doorbell_fn` seam) and drop `_STUCK_NUDGE_MESSAGE` and the
`.format()` call — the fixed string already says "go drain," and the unread
count is exactly the kind of restate-what's-already-durable content C45's
header argues against threading through a nudge at all.

**Judgment call left to the daemon owner, not decided here**: the function's
own de-dup/escalation bookkeeping — `_STUCK_MIN_NUDGE_INTERVAL_S` at `:2308-2311`,
`last_nudge_sig`/`last_nudge_ts` at `:2294-2306, 2321-2325`, and the
`stuck-refusing-drain` escalation gated on them — is about *detecting* an
unresponsive agent, not about sendkeys safety, so it does not have to change
just because the sendkeys call underneath it does. But doorbell is
idempotent and un-rate-limited by design (`tmux_adapter.py`'s own guard set
has nothing here to remove), so whether this bookkeeping should now ring on
every tick instead of backing off is a real behavioural choice, not a
mechanical one — flagging it rather than making it.

### 3. `pending_operator_actions()` — `:2679-2682`

```python
rc, out = nudge(COORDINATOR_AGENT,
                f"Bus: {len(overdue)} operator-decision item(s) have been unread in "
                f"your inbox past the deadline. Drain and present them now.",
                _OPERATOR_NUDGE_RETRY_S)
```

Same shape as #2 — a count plus "go drain," no brief. **Action**: switch to
`doorbell(COORDINATOR_AGENT)`. Note (per the surrounding comment at `:2672-2675`)
this call site is inert today — `coordinator-agent`'s endpoint is
`monitor:file`, not `tmux:...`, so `resolve_target` refuses it regardless of
`nudge` vs `doorbell` — but the code should still say what it means, and it
matters the moment that endpoint becomes a tmux one.

## NOT in scope — do not "migrate" these

Three other functions (`auto_yield`, `process_revocations`/R4,
`stall_ladder`) each build a list called `nudges` and hand it to
`_append_inbox(bus_root, ..., epoch)`:

- `:1418` (`auto_yield`'s R5 path)
- `:1687` (`process_revocations`, R4)
- `:1798` (`stall_ladder`)
- consumed at `:3073-3074`, `:3081-3082`, `:3124-3125`

These write a **bus inbox row** whose `"kind"` field happens to be the
string `"nudge"` — durable, schema-validated, cursor-tracked payload, exactly
what C45 says the bus is for. They never call `tmux_adapter.py` and never
touch a pane. The name is a historical false cognate with the sendkeys
`nudge`/`doorbell` pair above; nothing here needs to change, and trying to
route them through `doorbell` would be backwards — that payload already
lives on the bus, which is the whole point.

## Verifying the switch, once made

`tmux_adapter.py doorbell --agent <id>` (no `--message`) is exactly what
either new call site should invoke. `scripts/coordination/tests/`
already has coverage for the adapter side
(`test_tmux_adapter_doorbell.py`, 28 tests, unit + live-tmux groups); the
daemon owner's tests should assert the two switched call sites invoke
`doorbell_fn`/`_tmux_doorbell` and no longer pass a `--message`, mirroring
how `test_c35_*`/`test_c36_*` in `tests/test_tmux_adapter.py` assert against
injected `nudge_fn` stand-ins today.
