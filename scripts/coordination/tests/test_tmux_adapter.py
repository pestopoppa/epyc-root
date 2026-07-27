#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""Tests for scripts/coordination/tmux_adapter.py (M5).

SAFETY: never touches the live `agent` session. Every tmux case runs in a
throwaway session named `busadapter-test-<pid>`, killed on exit even on failure,
and BUS_ROOT is redirected to a temp tree so the real config, heartbeats and
ledger are untouched. The live-tmux group skips cleanly if no tmux is reachable.

Two groups:
  unit  — resolve_target/probe against synthetic configs; no tmux at all
  live  — nudge, rate limit, busy-window refusal, dead pane, spawn, spawn cap

Usage: scripts/coordination/tests/test_tmux_adapter.py [--unit-only]
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
    cfg = {"roster": roster, "flags": {"codex_sendkeys": sendkeys},
           "caps": {"max_spawns_per_day": spawn_cap},
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

        cfg = write_config(bus, [{"id": "a", "endpoint": "tmux:sess:7"}])
        t, why = m.resolve_target(cfg, "a")
        check(t == "sess:7", f"explicit window in endpoint resolves ({t})")

        # blocker composition — target resolves, so only the state guards can fire
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


# ------------------------------------------------------------------ live group


def test_live() -> None:
    rc, _ = tmux("-V")
    if rc != 0:
        print("== live: SKIPPED (no tmux reachable) ==")
        return
    print(f"== live: real tmux in throwaway session {SESSION} ==")
    with tempfile.TemporaryDirectory() as d:
        bus = Path(d)
        m = load(bus)
        try:
            tmux("new-session", "-d", "-s", SESSION, "-n", "quiet", "sleep 300")
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
            write_config(bus, [{"id": "quiet", "endpoint": f"tmux:{SESSION}"}], spawn_cap=1)

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
            rc = m.cmd_spawn(S())
            created = [f for f in ("inbox/spawned.jsonl", "outbox/spawned.jsonl",
                                   "heartbeats/spawned.json", "cursors/spawned.json")
                       if (bus / f).exists()]
            check(rc == 0, f"real spawn returns 0 (rc={rc})")
            check(len(created) == 4, f"all four bus files exist after spawn ({len(created)}/4)")
            rc2, out = tmux("list-windows", "-t", SESSION, "-F", "#{window_name}")
            check("spawned" in out.split(), "the pane exists after its files (order matters)")

            rc = m.cmd_spawn(S())
            check(rc == 2, "spawn refuses once the daily cap is reached")

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
                           "creating one")

            write_config(bus, [{"id": "win-ok", "endpoint": f"tmux:{SESSION}"}],
                         spawn_cap=3, live_session=SESSION)
            class S5:
                agent = "win-ok"; command = "true"; dry_run = True
            rc = m.cmd_spawn(S5())
            check(rc == 0, "spawn accepts the declared live session")
        finally:
            tmux("kill-session", "-t", SESSION)
            print(f"  (throwaway session {SESSION} killed)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit-only", action="store_true")
    args = ap.parse_args()
    test_unit()
    if not args.unit_only:
        test_live()
    failed = [w for ok, w in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    for w in failed:
        print(f"  FAILED: {w}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
