#!/usr/bin/env python3
"""Static half of the OBSERVATION CONTRACT — the part cheap enough to run on every commit.

ONE implementation, TWO consumers, so they cannot drift:

  * ``tests/test_observer_contract.py`` imports these checks (each as its own named,
    collected test) and adds the runtime battery on top.
  * ``scripts/hooks/observer_census_precommit.sh`` runs ``main()`` on every commit.

Deliberately dependency-free — stdlib and ``git`` only. A gate that needs pytest, jq
or a particular venv acquires a third state of its own ("the checker could not run"),
and a checker for *this* defect class arriving with *this* defect class would be a
poor joke. The one external call is ``git ls-files``, and its failure is raised, not
swallowed.

WHAT IT ENFORCES
----------------
  1. The registry is well formed; no duplicate rows.
  2. No row points at a file that no longer exists.
  3. RULE A — any file under the discovery roots that identifies a process by
     name/argv is registered (as adopted, deferred, or explicitly exempt-with-reason).
  4. RULE B — any file that sources ``observer_guard.sh`` is registered as adopted,
     so it cannot quietly drop out of the runtime battery.
  5. Every deferred row is bound to a REAL, currently-UNCHECKED ``- [ ]`` task in a
     real handoff. Deferring is fine. Deferring silently is what cost the hours.

Rules 3 and 4 are what make this survive its author: the subjects are discovered from
the tree, not listed by hand, so a new watchdog enrolls itself.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO / "scripts" / "coordination" / "observer_registry.json"

VALID_CONTRACTS = ("v1", "unadopted", "exempt")


def load_registry(path: Path | None = None) -> dict:
    return json.loads((path or REGISTRY_PATH).read_text())


# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #

def _git(*args: str) -> list[str]:
    return subprocess.run(
        ["git", "-C", str(REPO), *args],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()


def source_files(reg: dict) -> list[str]:
    """Candidate files: tracked AND untracked-but-not-ignored.

    Untracked files are included on purpose. ``git ls-files`` alone lists only the
    index, so a brand-new watchdog sitting in the working tree would be invisible —
    and "invisible until somebody remembers to ``git add``" is the exact shape of
    gap this whole contract exists to close.
    """
    disc = reg["discovery"]
    listed = _git("ls-files", *disc["roots"])
    untracked = _git("ls-files", "--others", "--exclude-standard", *disc["roots"])
    out = []
    for rel in [*listed, *untracked]:
        if not any(rel.endswith(e) for e in disc["extensions"]):
            continue
        if any(s in "/" + rel for s in disc["skip_path_substrings"]):
            continue
        out.append(rel)
    return out


def matching(reg: dict, pattern: str) -> set[str]:
    rx = re.compile(pattern)
    hits = set()
    for rel in source_files(reg):
        try:
            text = (REPO / rel).read_text(errors="replace")
        except OSError:
            continue
        if rx.search(text):
            hits.add(rel)
    return hits


# --------------------------------------------------------------------------- #
# The checks. Each returns a list of human-readable violations.
# --------------------------------------------------------------------------- #

def check_registry_well_formed(reg: dict) -> list[str]:
    bad, seen = [], set()
    for row in reg["observers"]:
        rid = row.get("id", "<no id>")
        if row.get("contract") not in VALID_CONTRACTS:
            bad.append(f"{rid}: contract must be one of {VALID_CONTRACTS}, got {row.get('contract')!r}")
        if row.get("script") in seen:
            bad.append(f"{rid}: duplicate row for {row.get('script')}")
        seen.add(row.get("script"))
        if row.get("contract") == "unadopted":
            if not row.get("owning_handoff"):
                bad.append(f"{rid}: deferred without an owning handoff")
            if not row.get("task_marker"):
                bad.append(f"{rid}: deferred without a task marker")
        if row.get("contract") == "exempt" and not row.get("reason"):
            bad.append(f"{rid}: exempt without a recorded reason")
    return bad


def check_no_stale_rows(reg: dict) -> list[str]:
    return [
        f"{r['id']}: registry row points at {r['script']}, which does not exist"
        for r in reg["observers"] if not (REPO / r["script"]).exists()
    ]


def check_rule_a(reg: dict) -> list[str]:
    found = matching(reg, reg["discovery"]["identity_probe_pattern"])
    found -= set(reg["discovery"].get("self_exclude", []))
    registered = {r["script"] for r in reg["observers"]}
    missing = sorted(found - registered)
    if not missing:
        return []
    return [
        "These files identify a process by name/argv but are absent from "
        f"{REGISTRY_PATH.relative_to(REPO)}:\n    " + "\n    ".join(missing) +
        "\n  Add a row: contract 'v1' if it adopts observer_guard.sh, 'unadopted' with "
        "an owning handoff + task marker if it is a known gap, 'exempt' with a reason "
        "if it is genuinely out of scope. Silence is the one option removed."
    ]


def check_rule_b(reg: dict) -> list[str]:
    found = matching(reg, reg["discovery"]["adoption_pattern"])
    found -= set(reg["discovery"].get("self_exclude", []))
    found = {f for f in found if not f.endswith("observer_guard.sh")}
    by_script = {r["script"]: r for r in reg["observers"]}
    out = []
    for rel in sorted(found):
        row = by_script.get(rel)
        if row is None:
            out.append(f"{rel}: sources observer_guard.sh but has no registry row")
        elif row["contract"] != "v1":
            out.append(f"{rel}: sources observer_guard.sh but is registered '{row['contract']}' "
                       "(adoption means contract 'v1', which is what enrols it in the battery)")
    return out


def check_runtime_well_formed(reg: dict) -> list[str]:
    """NIB2-81 remedy (b): validate the optional `runtime` object on a row.

    Shape only — the SEMANTICS (is the live daemon actually current) are what
    ``live_check_row``/``--live`` answers at runtime; this is the same static,
    every-commit guarantee the rest of the file gives the contract fields.
    """
    bad = []
    for row in reg["observers"]:
        rt = row.get("runtime")
        if rt is None:
            continue
        rid = row.get("id", "<no id>")
        if not isinstance(rt, dict):
            bad.append(f"{rid}: 'runtime' must be an object, got {type(rt).__name__}")
            continue
        for key in ("pidfile", "expected_path", "provenance"):
            v = rt.get(key)
            if not isinstance(v, str) or not v.strip():
                bad.append(f"{rid}: runtime.{key} must be a non-empty string")
        pidfile = rt.get("pidfile")
        if isinstance(pidfile, str) and not pidfile.startswith("/"):
            bad.append(f"{rid}: runtime.pidfile must be an absolute path, got {pidfile!r}")
        provenance = rt.get("provenance")
        if isinstance(provenance, str) and not provenance.startswith("/"):
            bad.append(f"{rid}: runtime.provenance must be an absolute path, got {provenance!r}")
        expected = rt.get("expected_path")
        if isinstance(expected, str) and expected != row.get("script"):
            bad.append(
                f"{rid}: runtime.expected_path ({expected!r}) must match the row's own "
                f"'script' ({row.get('script')!r}) — two names for one daemon is how they drift"
            )
        restart = rt.get("restart_on_stale")
        if restart is not None and not isinstance(restart, bool):
            bad.append(f"{rid}: runtime.restart_on_stale must be a bool if present")
        if restart:
            argv = rt.get("start_argv")
            if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
                bad.append(
                    f"{rid}: runtime.restart_on_stale=true requires a non-empty "
                    "runtime.start_argv list of strings"
                )
    return bad


def check_deferrals_are_live(reg: dict) -> list[str]:
    out = []
    for row in reg["observers"]:
        if row.get("contract") != "unadopted":
            continue
        handoff = REPO / row["owning_handoff"]
        if not handoff.exists():
            out.append(f"{row['id']}: owning handoff {row['owning_handoff']} does not exist")
            continue
        marker = row["task_marker"]
        open_lines = [
            ln for ln in handoff.read_text(errors="replace").splitlines()
            if marker in ln and re.search(r"-\s*\[\s\]", ln)
        ]
        if not open_lines:
            out.append(
                f"{row['id']}: no OPEN '- [ ]' task carrying marker '{marker}' in "
                f"{row['owning_handoff']}. Either the migration landed (flip the registry "
                "row to contract 'v1') or the deferral was silently lost."
            )
    return out


CHECKS = {
    "registry-well-formed": check_registry_well_formed,
    "no-stale-rows": check_no_stale_rows,
    "rule-a-process-pattern-observers-registered": check_rule_a,
    "rule-b-guard-adopters-registered": check_rule_b,
    "deferrals-bound-to-open-tasks": check_deferrals_are_live,
    "runtime-well-formed": check_runtime_well_formed,
}


def run_all(reg: dict | None = None) -> dict[str, list[str]]:
    reg = reg if reg is not None else load_registry()
    return {name: fn(reg) for name, fn in CHECKS.items()}


def _static_main() -> int:
    """UNCHANGED from before NIB2-81 remedy (b) — the ``--live`` addition below is
    purely additive and this path never runs when ``--live`` is absent."""
    results = run_all()
    failed = {k: v for k, v in results.items() if v}
    if not failed:
        print(f"observer census: OK ({len(load_registry()['observers'])} observers registered)")
        return 0
    print("\nOBSERVER CONTRACT VIOLATION\n", file=sys.stderr)
    for name, problems in failed.items():
        print(f"  [{name}]", file=sys.stderr)
        for p in problems:
            print(f"    - {p}", file=sys.stderr)
    print(
        "\n  Context: a watchdog that cannot observe its target must say so. On 2026-08-12 one\n"
        "  identified a healthy daemon by an argv pattern that had drifted, called it dead\n"
        "  forever, and relaunch-looped for hours in silence. Registry:\n"
        f"  {REGISTRY_PATH.relative_to(REPO)}   Contract: scripts/coordination/observer_guard.sh\n",
        file=sys.stderr,
    )
    return 1


# =============================================================================
# --live: the read-only /proc walk (NIB2-81 remedy (b))
# =============================================================================
#
# WHY THIS IS A SEPARATE MODE FROM THE STATIC CHECKS ABOVE. Those certify the
# FILE — the registry is well-formed, every risky pattern is enrolled. This
# certifies an INSTANCE — the process actually running at a registered
# ``runtime.pidfile`` right now. The static census stayed green throughout the
# 2026-09-17 incident ("census OK (17 observers)") while the live reaper
# executed a copy of its script that predated the fix by nine days — a
# structural gap between "the file is honest" and "the process obeying it is
# honest", and this closes the second half.
#
# THE MECHANISM (tmp/daemon-staleness-20260917/report.md §2b): bash opens a
# script's inode ONCE at launch and reads it incrementally for the process's
# whole life; git never writes a tracked file in place (checkout/reset/merge
# unlink-and-recreate it). So "is this daemon current" reduces to a single
# comparison: does the inode the process still has OPEN (visible live via
# ``/proc/<pid>/fd/<n>``, the bash script-fd convention observed at fd 255 on
# every live daemon censused that night) match the inode NOW on disk at the
# daemon's own ``expected_path``. Not a snapshot recorded at that daemon's own
# start (that is ``daemon_provenance.sh``'s ``dp_stale_since_start``, remedy
# (a), one layer cheaper and daemon-side) — this reads the process's actual
# open descriptor, so it also works for a daemon never wired to remedy (a) and
# it cannot be fooled by an inode number being reused between the two reads.
#
# EVERY BRANCH FAILS CLOSED. A permission error, an unreadable /proc entry, an
# ambiguous fd — none of those become "current". They become ``cannot_tell``,
# which is graded exactly as badly as a proven problem (CLAUDE.md Debugging:
# "a measurement whose window does not overlap the phenomenon is not evidence
# of its absence"; the same principle that makes ``unobservable`` in
# observer_guard.sh above suppress action rather than default to "fine").

LIVE_STATES = ("running_current", "running_stale", "running_off_canon",
               "not_running", "cannot_tell")

# One convention with daemon_provenance.sh's dp_canonical_root_a/b + dp_view_root
# ON PURPOSE — two independent implementations of "what counts as canon" is how
# a canon list drifts. DP_CANONICAL_ROOT / DP_VIEW_ROOT are TEST-ONLY overrides
# (mirrors EPYC_BUS_ROOT in bus_supervisor.sh); production code never sets them.
_DEFAULT_CANONICAL_ROOT = "/workspace"
_DEFAULT_VIEW_ROOT = "/mnt/raid0/llm/views/epyc-root-main"


def _canonical_roots() -> list[str]:
    root_a = os.environ.get("DP_CANONICAL_ROOT", _DEFAULT_CANONICAL_ROOT)
    try:
        root_b = os.path.realpath(root_a) if root_a else ""
    except OSError:
        root_b = ""
    view = os.environ.get("DP_VIEW_ROOT", _DEFAULT_VIEW_ROOT)
    roots: list[str] = []
    for r in (root_a, root_b, view):
        if r and r not in roots:
            roots.append(r)
    return roots


def _under_any_root(path: str, roots: list[str]) -> bool:
    for r in roots:
        rr = r.rstrip("/")
        if path == rr or path.startswith(rr + "/"):
            return True
    return False


def _read_pid(pidfile: Path) -> int | None:
    try:
        txt = pidfile.read_text().strip()
    except OSError:
        return None
    try:
        return int(txt)
    except ValueError:
        return None


def _read_cmdline(pid: int) -> str | None:
    """None => could not read at all (permission or the pid vanished mid-read).

    ``/proc/<pid>/cmdline`` is world-readable on Linux even across uids
    (bus_supervisor.sh's own ``resolve_daemon`` makes the same point) — an
    OSError here is almost always "the pid is gone", handled by the caller's
    prior ``/proc/<pid>`` existence check, but is still folded to ``None``
    (cannot_tell) rather than assumed-gone, because the two checks are not
    atomic and a race is not evidence.
    """
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return None
    return raw.replace(b"\0", b" ").decode("utf-8", "replace")


def _resolve_open_script_fd(pid: int, basename: str) -> tuple[str | None, str | None]:
    """Find the fd number holding the daemon's own script open.

    Returns (fd_number, error). error == "permission" means /proc/<pid>/fd could
    not even be listed/read — the caller must report cannot_tell, never a
    verdict about code identity from a directory it never saw. Prefers fd 255
    (the bash convention observed on every live daemon censused 2026-09-17: pid
    2873259, 639194, 4137635 all held their own script open there) and falls
    back to a full fd scan for a non-bash launcher or an unusual fd layout.
    """
    try:
        link = os.readlink(f"/proc/{pid}/fd/255")
    except PermissionError:
        return None, "permission"
    except OSError:
        link = None
    if link is not None:
        bare = link[: -len(" (deleted)")] if link.endswith(" (deleted)") else link
        if os.path.basename(bare) == basename:
            return "255", None

    try:
        entries = os.listdir(f"/proc/{pid}/fd")
    except PermissionError:
        return None, "permission"
    except OSError:
        return None, None

    for fd in entries:
        if fd == "255":
            continue
        try:
            link = os.readlink(f"/proc/{pid}/fd/{fd}")
        except PermissionError:
            return None, "permission"
        except OSError:
            continue
        bare = link[: -len(" (deleted)")] if link.endswith(" (deleted)") else link
        if os.path.basename(bare) == basename:
            return fd, None
    return None, None


def live_check_row(row: dict, canonical_root: str | None = None) -> dict:
    """Read-only /proc verdict for one registry row's ``runtime`` daemon.

    Returns ``{"id", "state", "detail", "pid"}``; ``state`` is one of
    ``LIVE_STATES``. Pure and side-effect-free — no alarm, no kill, no launch —
    so it is exactly as safe to call from a test as from the CLI, and
    ``bus_supervisor.sh``'s registry-restart tick reimplements the same
    inode-comparison idea in bash rather than shelling out to this, for the
    same reason ``daemon_provenance.sh`` is bash: a restart path with a Python
    dependency in the middle is one more way to fail closed into "did nothing".
    """
    rid = row.get("id", "<no id>")
    rt = row.get("runtime") or {}
    pidfile = rt.get("pidfile")
    expected_path = rt.get("expected_path") or row.get("script")

    def result(state: str, detail: str, pid: int | None = None) -> dict:
        return {"id": rid, "state": state, "detail": detail, "pid": pid}

    if not pidfile or not expected_path:
        return result("cannot_tell", "runtime row is missing pidfile/expected_path")

    pid = _read_pid(Path(pidfile))
    if pid is None:
        if not Path(pidfile).exists():
            return result("not_running", f"pidfile {pidfile} does not exist")
        return result("cannot_tell", f"pidfile {pidfile} exists but is unreadable or non-numeric")

    if not Path(f"/proc/{pid}").exists():
        return result("not_running", f"pidfile {pidfile} names pid {pid}, which is not alive")

    cmdline = _read_cmdline(pid)
    if cmdline is None:
        return result("cannot_tell", f"pid {pid}: /proc/{pid}/cmdline unreadable", pid)
    if not cmdline.strip():
        return result("not_running", f"pid {pid} has empty argv (zombie, or vanished mid-read)")

    basename = os.path.basename(expected_path)
    if basename not in cmdline:
        return result(
            "not_running",
            f"pid {pid} is alive but its argv ({cmdline[:80]!r}) does not name {basename!r} — "
            "the pid was RECYCLED to a different process, not our daemon",
        )

    fd, err = _resolve_open_script_fd(pid, basename)
    if err == "permission":
        return result("cannot_tell", f"pid {pid}: /proc/{pid}/fd unreadable (permission)", pid)
    if fd is None:
        return result(
            "cannot_tell",
            f"pid {pid}: could not resolve an open fd for {basename!r} (no fd 255 match, "
            "no other fd matches either)",
            pid,
        )

    try:
        link = os.readlink(f"/proc/{pid}/fd/{fd}")
        fd_st = os.stat(f"/proc/{pid}/fd/{fd}")
    except OSError:
        return result("cannot_tell", f"pid {pid}: fd {fd} vanished mid-read", pid)

    deleted = link.endswith(" (deleted)")
    bare = link[: -len(" (deleted)")] if deleted else link

    roots = [canonical_root] if canonical_root else _canonical_roots()
    if not _under_any_root(bare, roots):
        return result(
            "running_off_canon",
            f"pid {pid} executes {bare!r}, outside canon/view ({', '.join(roots)}) — a lane",
            pid,
        )

    root_for_expected = roots[0]
    current_path = Path(root_for_expected) / expected_path
    try:
        cur_st = current_path.stat()
    except OSError:
        return result(
            "running_stale",
            f"pid {pid} holds inode {fd_st.st_ino} open at {bare!r}, but {current_path} no "
            "longer exists on disk",
            pid,
        )

    if (fd_st.st_dev, fd_st.st_ino) != (cur_st.st_dev, cur_st.st_ino):
        why = "its open fd is on an UNLINKED (deleted) inode" if deleted else (
            "the on-disk inode at its own path has changed since it started"
        )
        return result(
            "running_stale",
            f"pid {pid} holds inode {fd_st.st_ino} open at {bare!r}; {current_path} is now "
            f"inode {cur_st.st_ino} — {why}",
            pid,
        )

    return result(
        "running_current",
        f"pid {pid} executes the current committed {expected_path} (inode {cur_st.st_ino})",
        pid,
    )


def run_live_census(reg: dict | None = None, canonical_root: str | None = None) -> list[dict]:
    reg = reg if reg is not None else load_registry()
    return [
        live_check_row(row, canonical_root)
        for row in reg["observers"]
        if row.get("runtime")
    ]


LIVE_SEVERITY = {
    "running_stale": "critical",
    "not_running": "critical",
    "running_off_canon": "critical",
    "cannot_tell": "warning",
}


def raise_live_alarms(
    results: list[dict],
    *,
    no_alarm: bool,
    alarm_state: Path | None = None,
    dry_run: bool = False,
) -> None:
    """Feed the SAME fleet alarm channel fleet_watch.sh already raises through
    (``alarm_channel.py`` — see its ``raise_alarm``/``clear_alarm``, and
    ``fleet_watch.sh``'s ``fw_alarm_raise``/``fw_alarm_clear`` which call the
    same functions over the CLI). No new sink. ``--no-alarm`` skips this
    entirely (a true dry run); ``alarm_state``/``dry_run`` exist so tests never
    touch the real dedupe state file — mirrors ``ALARM_STATE_PATH`` above.
    """
    if no_alarm:
        return
    coord_dir = str(Path(__file__).resolve().parent)
    if coord_dir not in sys.path:
        sys.path.insert(0, coord_dir)
    import alarm_channel  # local import: only touched when an alarm may actually fire

    for r in results:
        key = f"daemon-live:{r['id']}"
        if r["state"] == "running_current":
            alarm_channel.clear_alarm(
                key, message=f"{r['id']}: {r['detail']}", state_file=alarm_state, dry_run=dry_run
            )
            continue
        severity = LIVE_SEVERITY.get(r["state"], "warning")
        alarm_channel.raise_alarm(
            key,
            severity,
            f"{r['id']}: {r['state']} — {r['detail']}",
            {"id": r["id"], "state": r["state"], "pid": r.get("pid"), "detail": r["detail"]},
            state_file=alarm_state,
            dry_run=dry_run,
        )


def _print_live_report(results: list[dict]) -> int:
    print("\nLIVE CENSUS — /proc walk over registry rows carrying a 'runtime' field\n")
    if not results:
        print("  (no registry row carries a 'runtime' field — nothing to walk)")
        return 0
    bad = 0
    for r in sorted(results, key=lambda x: x["id"]):
        ok = r["state"] == "running_current"
        bad += 0 if ok else 1
        marker = "OK " if ok else "!! "
        pid_s = f"pid={r['pid']}" if r.get("pid") is not None else "pid=-"
        print(f"  [{marker}] {r['id']:<28} {r['state']:<18} {pid_s:<12} {r['detail']}")
    print(f"\n{len(results) - bad}/{len(results)} running current code.")
    if bad:
        print(
            "  Non-'running_current' verdicts are graded as problems (fail closed — "
            "tmp/daemon-staleness-20260917/report.md).",
        )
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        prog="observer_census.py",
        description="Static registry census, plus (--live) a read-only /proc walk "
                     "over registered daemon instances (NIB2-81 remedy (b)).",
    )
    ap.add_argument(
        "--live", action="store_true",
        help="walk /proc for every registry row with a 'runtime' field instead of "
             "running the static checks",
    )
    ap.add_argument(
        "--no-alarm", action="store_true",
        help="(--live only) compute verdicts and print the report, but never call "
             "alarm_channel — a true dry run",
    )
    ap.add_argument(
        "--alarm-state", type=Path, default=None,
        help="(--live only, tests) override alarm_channel's dedupe state path",
    )
    ap.add_argument(
        "--alarm-dry-run", action="store_true",
        help="(--live only, tests) pass dry_run=True through to alarm_channel so no "
             "state is persisted",
    )
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)

    if not args.live:
        return _static_main()

    live_results = run_live_census()
    rc = _print_live_report(live_results)
    raise_live_alarms(
        live_results,
        no_alarm=args.no_alarm,
        alarm_state=args.alarm_state,
        dry_run=args.alarm_dry_run,
    )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
