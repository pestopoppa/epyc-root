#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""LIVE-PANE tests for scripts/coordination/tmux_adapter.py (M5).

Companion to `tests/test_tmux_adapter.py`, which covers the predicates against
stubbed panes. THIS file drives a real tmux pane end to end: send-keys into a
live composer, the rate limit, a busy window, a dead pane, spawn, and the spawn
cap. Neither suite subsumes the other — **run both when you touch the adapter.**

    python -m pytest tests/test_tmux_adapter.py \
                     scripts/coordination/tests/test_tmux_adapter_live.py

SAFETY: never touches the live `agent` session. Every tmux case runs in a
throwaway session named `busadapter-test-<pid>`, killed on exit even on failure,
and BUS_ROOT is redirected to a temp tree so the real config, heartbeats and
ledger are untouched. The live-tmux group skips cleanly if no tmux is reachable.

Two groups:
  unit  — resolve_target/probe against synthetic configs; no tmux at all
  live  — nudge, rate limit, busy-window refusal, dead pane, spawn, spawn cap

WHY THIS FILE WAS INVISIBLE, AND WHY IT IS NAMED `_live` (C10, 2026-07-28). It was
`scripts/coordination/tests/test_tmux_adapter.py` — the SAME basename as
`tests/test_tmux_adapter.py`. Neither directory is a package, so pytest derived the
module name `test_tmux_adapter` for both and aborted any run that reached both with
`import file mismatch` — a collection ERROR that interrupts the whole session, not a
skip. In practice nobody ran it, and it sat RED at HEAD for a day after the C6
change while every quoted "green" came from the pytest path alone. The unique
basename is the fix; do not rename it back.

AND THE CHECKS NOW ASSERT. `check()` only appended to a module-global list that
`main()` inspected, so under pytest `test_unit`/`test_live` returned None and
reported PASS **no matter how many checks failed** — collected-but-always-green,
which is worse than uncollected because it manufactures false evidence. Each entry
point now asserts over the checks IT recorded.

Usage: scripts/coordination/tests/test_tmux_adapter_live.py [--unit-only]
       (or via pytest, as above — both paths report the same failures)
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE = REPO_ROOT / "scripts" / "coordination" / "tmux_adapter.py"
SESSION = f"busadapter-test-{os.getpid()}"

RESULTS: list[tuple[bool, str]] = []


def check(ok: bool, why: str) -> None:
    RESULTS.append((bool(ok), why))
    print(f"  {'PASS' if ok else 'FAIL'}  {why}")


def _assert_checks(start: int, label: str) -> None:
    """Fail the calling test if any check IT recorded failed.

    Sliced from ``start`` rather than reading all of RESULTS: the list is a module
    global shared by both entry points, so without the slice `test_live` would
    inherit `test_unit`'s failures and one defect would be reported twice.

    Without this, pytest saw two functions that return None and always passed.
    """
    failed = [why for ok, why in RESULTS[start:] if not ok]
    assert not failed, (f"{len(failed)} of {len(RESULTS) - start} checks failed in {label}:"
                        + "".join(f"\n  - {why}" for why in failed))


def _skip(reason: str) -> None:
    """Skip under pytest; degrade to a printed note when run as a script."""
    try:
        import pytest
    except ImportError:
        print(f"== SKIPPED: {reason} ==")
        return
    pytest.skip(reason, allow_module_level=False)


def load(bus_root: Path):
    spec = importlib.util.spec_from_file_location(f"ta_{bus_root.name}", MODULE)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.BUS_ROOT = bus_root
    m.LEDGER = bus_root / "adapter-ledger.jsonl"
    for d in ("heartbeats", "cursors", "inbox", "outbox", "tokens"):
        (bus_root / d).mkdir(parents=True, exist_ok=True)
    return m


def write_config(bus_root: Path, roster: list[dict], *, sendkeys="on", spawn_cap=3,
                 live_session: str | None = None) -> dict:
    # C9 (2026-07-28): the cap is CONCURRENCY — live roster-member windows — not
    # spawn actions per day. `max_spawns_per_day` is refused, not reinterpreted.
    cfg = {"roster": roster, "flags": {"codex_sendkeys": sendkeys},
           "caps": {"max_concurrent_mains": spawn_cap},
           "tmux": {"live_session": live_session or SESSION,
                    "allow_session_creation": False}}
    import yaml
    (bus_root / "config.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return cfg


def set_heartbeat(m, agent: str, state: str, *, age_s: float = 0.0) -> None:
    p = m.BUS_ROOT / "heartbeats" / f"{agent}.json"
    p.write_text(json.dumps({"agent": agent, "state": state, "task_id": "t",
                             "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}))
    if age_s:
        old = time.time() - age_s
        os.utime(p, (old, old))


def ledger(m) -> list[dict]:
    """Ledger rows, tolerating absence — a refused nudge writes no file at all."""
    if not m.LEDGER.exists():
        return []
    return [json.loads(l) for l in m.LEDGER.read_text().splitlines() if l.strip()]


def tmux(*args: str) -> tuple[int, str]:
    try:
        r = subprocess.run(["tmux", *args], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, str(exc)
    return r.returncode, (r.stdout or r.stderr).strip()


# ------------------------------------------------------------------ unit group


def test_unit() -> None:
    start = len(RESULTS)
    print("== unit: target resolution and guard blockers (no tmux) ==")
    with tempfile.TemporaryDirectory() as d:
        bus = Path(d)
        m = load(bus)

        cfg = write_config(bus, [])
        t, why = m.resolve_target(cfg, "ghost")
        check(t is None and "no roster row" in why, "no roster row -> refuse, and says why")

        cfg = write_config(bus, [{"id": "a", "endpoint": "monitor:file"}])
        t, why = m.resolve_target(cfg, "a")
        check(t is None and "not a tmux endpoint" in why, "non-tmux endpoint -> refuse")

        cfg = write_config(bus, [{"id": "a", "endpoint": "tmux:no-such-session"}])
        t, why = m.resolve_target(cfg, "a")
        check(t is None, "unknown session -> refuse")
        # The "refusing to guess" wording belongs to the no-matching-WINDOW path,
        # which needs a session that exists; asserted in the live group instead.

        # C32 (2026-07-29): THIS CHECK USED TO ASSERT A FALSE ATTESTATION. It read
        # `check(t == "sess:7", ...)` — a POSITIVE resolution, reported by the module
        # as "(verified)", for a window index in a session that does not exist. That
        # is not a wrong expectation about an edge case; it is the fixture pinning the
        # bug. Measured cause: `display-message -p -t sess:7 '#{window_name}'` exits
        # **0 with empty output** when the session is absent, and the old
        # `and not want.isdigit()` clause waived the mismatch comparison for numeric
        # window components — so every index endpoint skipped verification entirely.
        # A refusal is recoverable by asking again; a false "verified" is not.
        cfg = write_config(bus, [{"id": "a", "endpoint": "tmux:sess:7"}])
        t, why = m.resolve_target(cfg, "a")
        check(t is None, f"index endpoint in an ABSENT session is refused, not 'verified' ({t}: {why})")

        # blocker composition. The target does NOT resolve here (no tmux), so `not
        # target` is a blocker too; these assert that each state guard ALSO fires,
        # which is what the composition is about.
        cfg = write_config(bus, [{"id": "a", "endpoint": "tmux:sess:7"}], sendkeys="off")
        set_heartbeat(m, "a", "idle")
        p = m.probe(cfg, "a", 20.0, 900.0)
        check(any("codex_sendkeys is off" in b for b in p["blockers"]), "flag off is a blocker")

        cfg = write_config(bus, [{"id": "a", "endpoint": "tmux:sess:7"}])
        (bus / "heartbeats" / "a.json").unlink()
        p = m.probe(cfg, "a", 20.0, 900.0)
        check(any("no heartbeat" in b for b in p["blockers"]),
              "missing heartbeat is a blocker (fail closed, not fail open)")

        set_heartbeat(m, "a", "working")
        p = m.probe(cfg, "a", 20.0, 900.0)
        check(any("says working" in b for b in p["blockers"]), "heartbeat working is a blocker")

        set_heartbeat(m, "a", "idle", age_s=3600)
        p = m.probe(cfg, "a", 20.0, 900.0)
        check(any("stale" in b for b in p["blockers"]), "stale heartbeat is a blocker")

        # every unit case must be nudge_ok False; a green path needs real tmux
        check(not p["nudge_ok"], "no unit configuration is ever nudge_ok")

    _assert_checks(start, "unit")


# ------------------------------------------------------------------ live group


def test_live() -> None:
    start = len(RESULTS)
    rc, _ = tmux("-V")
    if rc != 0:
        _skip("no tmux reachable")
        return
    print(f"== live: real tmux in throwaway session {SESSION} ==")
    with tempfile.TemporaryDirectory() as d:
        bus = Path(d)
        m = load(bus)
        try:
            # The echoed input line must SURVIVE submission: post-Enter verification
            # requires the transcript echo as positive evidence (C6, 2026-07-28), and
            # a fixture that clears the screen on submit deletes the very signal under
            # test — it would pass an adapter that cannot tell a submission from a
            # swallowed Enter. This fixture did exactly that until 2026-07-28.
            tmux("new-session", "-d", "-s", SESSION, "-n", "quiet",
                 "sh", "-c", "printf '\\033[999;1H'; IFS= read -r line; "
                 "printf 'SUBMITTED\\n'; sleep 300")
            # `sh -c` as SEPARATE args, not one string. The default shell here is
            # fish, which rejects bash loop syntax — passing the loop as a single
            # arg created the window and fish killed it instantly, so this case
            # silently tested nothing until 2026-07-27.
            tmux("new-window", "-d", "-t", SESSION, "-n", "busy",
                 "sh", "-c", "while :; do date; sleep 1; done")
            rc_w, wins = tmux("list-windows", "-t", SESSION, "-F", "#{window_name}")
            check("busy" in wins.split(), f"the busy fixture window actually exists ({wins.split()})")
            cfg = write_config(bus, [
                {"id": "quiet", "endpoint": f"tmux:{SESSION}"},
                {"id": "busy", "endpoint": f"tmux:{SESSION}"},
            ])

            t, why = m.resolve_target(cfg, "quiet")
            check(t is not None and "matched window" in why,
                  f"resolves by window NAME when the endpoint omits it ({t})")

            # in-memory only — writing these would clobber the roster on disk,
            # and cmd_nudge/cmd_spawn re-read config.yaml from there
            cfg_noname = {"roster": [{"id": "absent", "endpoint": f"tmux:{SESSION}"}]}
            t2, why2 = m.resolve_target(cfg_noname, "absent")
            check(t2 is None and "Refusing to guess" in why2,
                  "real session but no window of that name -> refuses to guess a pane")

            cfg_bad = {"roster": [{"id": "x", "endpoint": f"tmux:{SESSION}:nope"}]}
            t3, why3 = m.resolve_target(cfg_bad, "x")
            check(t3 is None, "explicit-but-nonexistent window is REFUSED, not silently "
                              "redirected to tmux's current window")

            # C32: index endpoints get the SAME verification as names, against
            # #{window_index}. C14 lists `tmux:agent:3` as a supported resolved form,
            # and nothing here exercised one — which is how the exemption survived.
            rc_i, idx_out = tmux("list-windows", "-t", SESSION,
                                 "-F", "#{window_index}\t#{window_name}")
            by_name = dict(reversed(line.split("\t", 1)) for line in idx_out.splitlines() if "\t" in line)
            quiet_idx = by_name.get("quiet")
            check(quiet_idx is not None, f"quiet window has a readable index ({idx_out!r})")
            if quiet_idx is not None:
                cfg_idx = {"roster": [{"id": "quiet", "endpoint": f"tmux:{SESSION}:{quiet_idx}"}]}
                t4, why4 = m.resolve_target(cfg_idx, "quiet")
                check(t4 == f"{SESSION}:{quiet_idx}" and "index" in why4 and "quiet" in why4,
                      f"a CORRECT index endpoint resolves and names the window it verified ({why4})")

            # The measured 2026-07-29 counterexample: tmux exits 0 for an out-of-range
            # index, falling back to the current window. Refusing is the only safe read.
            cfg_99 = {"roster": [{"id": "quiet", "endpoint": f"tmux:{SESSION}:99"}]}
            t5, why5 = m.resolve_target(cfg_99, "quiet")
            check(t5 is None and "INDEX" in why5,
                  f"out-of-range index endpoint is REFUSED, never attested as verified ({t5}: {why5})")

            # The quiet-check only works while a client is ATTACHED; a throwaway
            # test session is detached, so assert the honest behaviour in each case
            # rather than pretending the signal is available.
            set_heartbeat(m, "busy", "idle")
            p = m.probe(cfg, "busy", 20.0, 900.0)
            if p["session_attached"]:
                check(any("mid-generation" in b for b in p["blockers"]),
                      "attached: a printing window is refused by the quiet-check")
            else:
                check("skipped" in p["quiet_check"] and not any(
                          "mid-generation" in b for b in p["blockers"]),
                      "detached: quiet-check is reported as skipped and does NOT block")

            # wait out the quiet window, then the green path
            time.sleep(22)
            set_heartbeat(m, "quiet", "idle")
            p = m.probe(cfg, "quiet", 20.0, 900.0)
            check(p["nudge_ok"], f"quiet window + idle heartbeat -> nudge_ok (blockers={p['blockers']})")

            class A:
                agent = "quiet"; message = "bus drain: test"; min_interval_s = 600.0; dry_run = True
                quiet_s = 20.0; heartbeat_max_age = 900.0
            rc = m.cmd_nudge(A())
            check(rc == 0, "--dry-run nudge returns 0")
            check(not m.LEDGER.exists(), "--dry-run nudge writes NO ledger entry")

            A.dry_run = False
            rc = m.cmd_nudge(A())
            check(rc == 0, f"real nudge succeeds (rc={rc})")
            rows = ledger(m)
            check(len(rows) == 1 and rows and rows[0]["kind"] == "nudge",
                  f"ledger records the nudge ({len(rows)} row(s))")

            rc = m.cmd_nudge(A())
            check(rc == 2, f"second nudge inside min-interval is rate-limited (rc={rc})")
            check(len(ledger(m)) == 1, "a rate-limited nudge adds no ledger entry")

            # dead pane
            tmux("new-window", "-d", "-t", SESSION, "-n", "dead", "true")
            time.sleep(1)
            cfg = write_config(bus, [{"id": "quiet", "endpoint": f"tmux:{SESSION}"},
                                     {"id": "busy", "endpoint": f"tmux:{SESSION}"},
                                     {"id": "dead", "endpoint": f"tmux:{SESSION}:dead"}])
            set_heartbeat(m, "dead", "idle")
            p = m.probe(cfg, "dead", 0.0, 900.0)
            check(not p["nudge_ok"], "a dead or vanished pane is never nudge_ok")

            # ---- spawn ----
            # spawn_cap is headroom here so the refusal below is attributable to the
            # missing roster row and not to the C9 concurrency cap, which is checked
            # first: `quiet` is a live window, so cap=1 would have refused anyway and
            # the case would have passed for the wrong reason.
            write_config(bus, [{"id": "quiet", "endpoint": f"tmux:{SESSION}"}], spawn_cap=9)

            class S:
                agent = "nope"; command = "true"; dry_run = True
            rc = m.cmd_spawn(S())
            check(rc == 2, "spawn refuses an agent with no roster row")

            S.agent = "spawned"
            write_config(bus, [{"id": "spawned", "endpoint": f"tmux:{SESSION}"}], spawn_cap=1)
            rc = m.cmd_spawn(S())
            created = [f for f in ("inbox/spawned.jsonl", "outbox/spawned.jsonl",
                                  "heartbeats/spawned.json", "cursors/spawned.json")
                       if (bus / f).exists()]
            check(rc == 0, "spawn --dry-run returns 0")
            check(not created, f"--dry-run creates NO bus files (found {created})")

            S.dry_run = False
            # A LONG-LIVED command, deliberately. `true` exits at once and tmux
            # reaps the window within ~0.3s (measured 2026-07-28), so every check
            # below that needs the spawned main to BE LIVE was a race against the
            # reaper — the C9 duplicate-refusal check passed or failed depending on
            # scheduling, and the "37/37" first quoted for it was flaky-green. A
            # fixture that cannot hold the state it asserts is not a test.
            S.command = "sleep 300"
            rc = m.cmd_spawn(S())
            created = [f for f in ("inbox/spawned.jsonl", "outbox/spawned.jsonl",
                                   "heartbeats/spawned.json", "cursors/spawned.json")
                       if (bus / f).exists()]
            check(rc == 0, f"real spawn returns 0 (rc={rc})")
            check(len(created) == 4, f"all four bus files exist after spawn ({len(created)}/4)")
            rc2, out = tmux("list-windows", "-t", SESSION, "-F", "#{window_name}")
            check("spawned" in out.split(), "the pane exists after its files (order matters)")

            rc = m.cmd_spawn(S())
            check(rc == 2, "spawn refuses to duplicate a main that is already live (C9)")

            # C9: the cap counts LIVE mains, so closing one returns its slot at once.
            # Under the old daily-action cap this stayed refused for the rest of the day.
            tmux("kill-window", "-t", f"{SESSION}:spawned")
            time.sleep(0.5)
            for rel in ("inbox/spawned.jsonl", "outbox/spawned.jsonl",
                        "heartbeats/spawned.json", "cursors/spawned.json"):
                (bus / rel).unlink(missing_ok=True)
            rc = m.cmd_spawn(S())
            check(rc == 0, f"closing a main returns its slot immediately (rc={rc})")
            tmux("kill-window", "-t", f"{SESSION}:spawned")
            time.sleep(0.5)

            # C24: a RE-spawned id must not inherit its dead predecessor's heartbeat.
            # The bug this pins was invisible above because that block deletes all four
            # bus files first — which is exactly the case a reboot does NOT produce. The
            # real post-reboot shape is the files surviving with a `working` state on a
            # task whose session is gone, and cmd_nudge then refusing on state AND age,
            # with the fresh session unable to clear either.
            hb = bus / "heartbeats/spawned.json"
            hb.write_text(json.dumps({"agent": "spawned", "state": "working",
                                      "task_id": "task-from-a-dead-session",
                                      "ts": "2020-01-01T00:00:00+00:00"}) + "\n")
            cur = bus / "cursors/spawned.json"
            cur.write_text(json.dumps({"agent": "spawned", "offset": 4242,
                                       "ts": "2020-01-01T00:00:00+00:00"}) + "\n")
            rc = m.cmd_spawn(S())
            check(rc == 0, f"spawn over a stale heartbeat returns 0 (rc={rc})")
            after = json.loads(hb.read_text())
            check(after["state"] == "idle",
                  f"C24: spawn RESETS an inherited heartbeat to idle (got {after['state']!r})")
            check(after["task_id"] is None,
                  f"C24: the dead session's task_id is cleared (got {after['task_id']!r})")
            check(not after["ts"].startswith("2020"),
                  f"C24: the heartbeat ts is refreshed (got {after['ts']!r})")
            cfg_c24 = m.load_config()
            p_c24 = m.probe(cfg_c24, "spawned", 0.0, 900.0)
            check(not any("heartbeat" in r for r in p_c24["blockers"]),
                  f"C24: a freshly spawned main is not heartbeat-blocked ({p_c24['blockers']})")
            # The cursor is a read POSITION, not a liveness claim — it must SURVIVE, or
            # the respawned session re-reads everything its predecessor already drained.
            check(json.loads(cur.read_text())["offset"] == 4242,
                  "C24: spawn preserves the inherited cursor offset")
            tmux("kill-window", "-t", f"{SESSION}:spawned")

            # C25: the spawned window is named from the ENDPOINT, not the roster id.
            # `new-window -n args.agent` produced `agent:inference` while the endpoint
            # said `tmux:agent:codex-inference`, so resolve_target verified a window the
            # spawn had not created and every such main was undeliverable FROM BIRTH.
            # Fixed by hand at 14:18Z with `tmux rename-window` — a manual step whose
            # omission silently breaks delivery.
            #
            # The assertion that matters is the SECOND one. Checking only the window
            # name would pass an adapter that names it correctly and still cannot be
            # reached; deliverability is the property, the name is the mechanism.
            print("\n  -- C25 spawn/endpoint window-name agreement --")
            class S25:
                agent = "c25"; command = "sleep 300"; dry_run = False
            cfg25 = write_config(bus, [{"id": "c25", "endpoint": f"tmux:{SESSION}:c25-window"}],
                                 spawn_cap=9)
            rc = m.cmd_spawn(S25())
            check(rc == 0, f"spawn with a window-naming endpoint returns 0 (rc={rc})")
            _rc, wins25 = tmux("list-windows", "-t", SESSION, "-F", "#{window_name}")
            check("c25-window" in wins25.split(),
                  f"the window carries the ENDPOINT's name, not the roster id ({wins25.split()})")
            check("c25" not in wins25.split(),
                  "and NOT the roster id — that window is what made spawned mains unreachable")
            t25, why25 = m.resolve_target(m.load_config(), "c25")
            check(t25 is not None,
                  f"THE POINT: a freshly spawned main is deliverable immediately ({t25}: {why25})")
            tmux("kill-window", "-t", f"{SESSION}:c25-window")
            time.sleep(0.5)
            for rel in ("inbox/c25.jsonl", "outbox/c25.jsonl",
                        "heartbeats/c25.json", "cursors/c25.json"):
                (bus / rel).unlink(missing_ok=True)

            # An INDEX endpoint is refused: tmux assigns indexes, so a spawn cannot
            # promise the window lands on the one the endpoint names, and a mismatch is
            # exactly the undeliverable-from-birth state above. Refusing is recoverable.
            write_config(bus, [{"id": "c25", "endpoint": f"tmux:{SESSION}:4"}], spawn_cap=9)
            rc = m.cmd_spawn(S25())
            check(rc == 3, f"spawn REFUSES a window-index endpoint rather than guessing (rc={rc})")
            check(not (bus / "inbox/c25.jsonl").exists(),
                  "a refused spawn creates no bus files")

            # C9 fail-closed: an uncountable live set must refuse, never assume zero.
            write_config(bus, [{"id": "spawned", "endpoint": f"tmux:{SESSION}"}],
                         spawn_cap=9, live_session="definitely-not-a-live-session")
            rc = m.cmd_spawn(S())
            check(rc == 2, "an unreachable live session refuses rather than counting zero (C9)")

            # C9: the superseded daily key is refused, not silently reinterpreted.
            import yaml as _yaml
            legacy = {"roster": [{"id": "spawned", "endpoint": f"tmux:{SESSION}"}],
                      "flags": {"codex_sendkeys": "on"},
                      "caps": {"max_spawns_per_day": 6},
                      "tmux": {"live_session": SESSION, "allow_session_creation": False}}
            (bus / "config.yaml").write_text(_yaml.safe_dump(legacy), encoding="utf-8")
            rc = m.cmd_spawn(S())
            check(rc == 3, f"caps.max_spawns_per_day alone is a misconfiguration, not a cap "
                           f"(rc={rc})")

            # ---- operator requirement: one live session, windows only ----
            print("\n  -- live-session enforcement --")
            src = MODULE.read_text()
            check('_tmux("new-session' not in src,
                  "the adapter never invokes new-session anywhere in its source")

            write_config(bus, [{"id": "elsewhere", "endpoint": "tmux:some-other-session"}],
                         spawn_cap=3, live_session=SESSION)
            class S2:
                agent = "elsewhere"; command = "true"; dry_run = True
            rc = m.cmd_spawn(S2())
            check(rc == 2, "spawn refuses a session that is not tmux.live_session")

            write_config(bus, [{"id": "notmux", "endpoint": "monitor:file"}],
                         spawn_cap=3, live_session=SESSION)
            class S3:
                agent = "notmux"; command = "true"; dry_run = True
            rc = m.cmd_spawn(S3())
            check(rc == 2, "spawn refuses a non-tmux endpoint (no more session name 'file')")

            write_config(bus, [{"id": "ghostsess", "endpoint": "tmux:definitely-not-running"}],
                         spawn_cap=3, live_session="definitely-not-running")
            class S4:
                agent = "ghostsess"; command = "true"; dry_run = True
            rc = m.cmd_spawn(S4())
            check(rc == 2, "spawn refuses a live_session that does not exist rather than "
                           "creating one (now caught at the C9 live-count stage, fail-closed)")

            write_config(bus, [{"id": "win-ok", "endpoint": f"tmux:{SESSION}"}],
                         spawn_cap=3, live_session=SESSION)
            class S5:
                agent = "win-ok"; command = "true"; dry_run = True
            rc = m.cmd_spawn(S5())
            check(rc == 0, "spawn accepts the declared live session")
        finally:
            tmux("kill-session", "-t", SESSION)
            print(f"  (throwaway session {SESSION} killed)")

    _assert_checks(start, "live")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit-only", action="store_true")
    args = ap.parse_args()
    # The entry points now raise on failure (so pytest sees it). As a script we
    # want the FULL tally, not the first failing group, so both groups run and the
    # summary below is what decides the exit code.
    for group in (test_unit,) if args.unit_only else (test_unit, test_live):
        try:
            group()
        except AssertionError:
            pass
    failed = [w for ok, w in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    for w in failed:
        print(f"  FAILED: {w}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
