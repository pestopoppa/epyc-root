#!/usr/bin/env python3
"""host_hygiene_tick.py — the periodic disk-hygiene tick that survives a reboot.

WHY. The 2026-10-03 disk audit (/mnt/raid0/llm/tmp/disk-audit-20261003/) found every leak class
was already KNOWN and none was WATCHED: worktrees nobody removed (233 GiB removable), stray
GGUFs and `.part`/`.incomplete` leftovers, `~/.codex` growth (NIB2-84), a claude-backups job that
silently did not run from 2026-08-03 to 2026-10-03, the opencode reaper dead since the 10-03
reboot because nothing relaunches it (NIB2-81: "Nothing relaunches it after a reboot"), and no
host-wide free-space alert at all. Each fix that depended on someone remembering had lapsed.

HOW IT SURVIVES A REBOOT. There is no cron or systemd inside the container. The one scheduler
that does survive is the HOST crontab that runs `hub_supervisor.sh once` every ~2 minutes; that
supervisor launches this tick (detached, nice 19, ionice idle, rate-limited to
HYGIENE_TICK_INTERVAL_S). So the tick, and everything it keeps alive, comes back with the host.
The CODE runs from the read-only hub view (origin/main, never a session's uncommitted edit) when
the view carries it; its HOME (state, logs, registry, alarm channel) is HYGIENE_ROOT = the
canonical root. NOTE: the host cron runs a PINNED copy of hub_supervisor.sh
(install_supervision_cron_20260916.sh, OP-9 option B), so the hook only goes live once the
operator re-runs that installer with `--all` to move the pin past the commit that adds it.

WHAT ONE TICK DOES.
  cheap, every tick:
    * disk-free  — free bytes on /mnt/raid0/llm. Alarm `host-disk-free-low` (warning <200 GB,
                   critical <100 GB), raised after 2 consecutive low samples and cleared after 2
                   samples above 110% of the threshold (two-sample rule, both directions). The
                   message names the top growers from the daily size history.
    * keeper     — every observer-registry row whose runtime carries `relaunch_if_down: true`
                   (today: opencode_event_reaper) is relaunched from its canonical start_argv when
                   the census verdict is `not_running` and no unregistered copy is running.
                   Rate-limited (one attempt / 30 min / daemon). It NEVER kills: a stale or
                   off-canon copy raises `daemon-stale-<id>` with the restart command instead.
    * backups    — claude-backups/LAST_STATUS older than 36 h or not OK -> `claude-backups-stale`.
    * heartbeat  — one log line and state.json `heartbeat_at` per tick (the observer-registry row
                   `host_hygiene_tick` is scheduled-mode on this log).
  heavy, once per HYGIENE_HEAVY_INTERVAL_S (24 h), ONLY while no CPU region is claimed:
    * growers    — du of the known grower paths -> size history (14 samples) -> growth ranking.
    (NO worktree or scratch sweep, by operator direction 2026-10-04: worktree/scratch cleanup is
     a step of the wrap-up and `/log` routines — scripts/system/scratch_cleanup.py over each
     handoff's declared **Scratch** roots — never a cron job. The grower list below still names
     the worktrees dir when free space runs low.)
    * partials   — `.part`/`.incomplete`/`.aria2`/`.crdownload` files older than 24 h and held open
                   by no process, plus stray >=2 GiB files in /tmp and llm/tmp older than 2 days
                   -> logs/hygiene/stray_files.json; alarm `stray-download-files` (report only).
    * codex      — scripts/system/codex_retention_reaper.py report --json, if present (NIB2-84);
                   report only, apply is operator-confirmed.
  The heavy gate is three-valued and fails closed: `region-lock status --json` unreadable or any
  region held, or the AutoKernel cpu-window saying the loop holds its claim or is closing, means
  DEFER. It is re-checked between heavy steps, so a window that opens mid-run stops the run.
  A heavy phase starved for 3 days raises `host-hygiene-heavy-starved`.

The default tick deletes nothing. Its side effects are files under logs/hygiene/,
alarm_channel.py calls, and relaunching an opted-in daemon that is down. A prospective
HYGIENE_OPENCODE_EVENTS=1 duty additionally requires an owner-reviewed scheduled registry
handover. It invokes the existing event-only reaper once every 1800 seconds, independently
of daily heavy work and behind the CPU-region gate. See opencode-event-duty-handover.md.

Usage:  host_hygiene_tick.py tick [--force-heavy] [--dry-run]   # --dry-run: print alarms, no relaunch
        host_hygiene_tick.py status                             # print state.json
Tests:  tests/test_host_hygiene_tick.py
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("HYGIENE_ROOT") or HERE.parent.parent)
STATE_DIR = Path(os.environ.get("HYGIENE_STATE_DIR") or ROOT / "logs" / "hygiene")
LLM = "/mnt/raid0/llm"


def _env_f(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


GB = 1e9
GiB = 2**30
DISK_PATH = os.environ.get("HYGIENE_DISK_PATH", LLM)
FREE_WARN = _env_f("HYGIENE_FREE_WARN_GB", 200) * GB
FREE_CRIT = _env_f("HYGIENE_FREE_CRIT_GB", 100) * GB
CLEAR_FACTOR = 1.10
PERSIST = 2
HEAVY_INTERVAL_S = _env_f("HYGIENE_HEAVY_INTERVAL_S", 86400)
HEAVY_STARVED_S = 3 * 86400
RELAUNCH_MIN_S = 1800
BACKUP_STATUS = Path(os.environ.get("HYGIENE_BACKUP_STATUS", f"{LLM}/claude-backups/LAST_STATUS"))
BACKUP_MAX_AGE_S = 36 * 3600
REGION_LOCK = os.environ.get("HYGIENE_REGION_LOCK", f"{LLM}/epyc-orchestrator/scripts/region-lock")
CPU_WINDOW = Path(os.environ.get("HYGIENE_CPU_WINDOW", f"{LLM}/autokernel/cpu-window.json"))
ALARM = ROOT / "scripts" / "coordination" / "alarm_channel.py"
REGISTRY = ROOT / "scripts" / "coordination" / "observer_registry.json"
LOG_MAX_BYTES = 5 * 2**20
HISTORY_KEEP = 14
# Cadence is the inherited 1800-second invariant; timeout is a subsystem tunable.
EVENT_INTERVAL_S = 1800
EVENT_TIMEOUT_S = 900
EVENT_ALARM = "opencode-event-duty"
EVENT_CAPABILITY = "LR8_ONCE_STATUS_V1"

GROWERS = [
    "/home/node/.codex",
    "/home/node/.local/share/opencode",
    "/tmp/claude-1000",
    "/tmp/epyc-eval-fence-1000",
    f"{LLM}/worktrees",
    f"{LLM}/tmp",
    f"{LLM}/autokernel/campaigns",
    f"{LLM}/epyc-orchestrator/orchestration/repl_memory/sessions",
    f"{LLM}/epyc-orchestrator/logs",
    f"{LLM}/kernels/builds",
    f"{LLM}/claude-backups",
    f"{LLM}/cloud-llm-vault",
    f"{LLM}/cache",
    f"{LLM}/models",
    f"{LLM}/bus-runtime",
    f"{LLM}/epyc-root/logs",
    f"{LLM}/.trash",
]
# (root, maxdepth) — depth-bounded so a tmp dir full of checkouts is not walked file by file.
PARTIAL_ROOTS = [
    (f"{LLM}/models", 8), (f"{LLM}/cache", 8), (f"{LLM}/hf", 6), (f"{LLM}/hf_models", 6),
    (f"{LLM}/hf-models", 6), (f"{LLM}/hf-home", 8), (f"{LLM}/hf-cache", 8), (f"{LLM}/tmp", 3),
    ("/tmp", 3),
]
PARTIAL_SUFFIXES = (".part", ".incomplete", ".aria2", ".crdownload")
PARTIAL_MIN_AGE_S = 24 * 3600
LARGE_ROOTS = [(f"{LLM}/tmp", 3), ("/tmp", 3)]
LARGE_MIN_BYTES = 2 * GiB
LARGE_MIN_AGE_S = 2 * 86400
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "CMakeFiles"}


# --------------------------------------------------------------------------- utilities
def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


class Tick:
    def __init__(self, dry_run: bool = False, state_dir: Path = STATE_DIR):
        self.dry_run = dry_run
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.state_dir / "state.json"
        self.log_path = self.state_dir / "host_hygiene.log"
        try:
            self.state = json.loads(self.state_path.read_text())
        except (OSError, ValueError):
            self.state = {}
        self.state.setdefault("active_alarms", [])
        self.lines: list[str] = []

    # -- io
    def log(self, msg: str) -> None:
        line = f"{now_iso()} [hygiene] {msg}"
        self.lines.append(line)
        print(line)

    def flush(self) -> None:
        try:
            if self.log_path.exists() and self.log_path.stat().st_size > LOG_MAX_BYTES:
                os.replace(self.log_path, self.log_path.with_suffix(".log.1"))
            with self.log_path.open("a") as fh:
                fh.write("\n".join(self.lines) + "\n")
        except OSError:
            pass
        self.state["heartbeat_at"] = now_iso()
        write_json(self.state_path, self.state)

    # -- alarms (emit-once lives in alarm_channel.py; we only track what WE raised)
    def raise_alarm(self, key: str, severity: str, message: str, evidence: dict | None = None) -> None:
        self.log(f"ALARM raise {key} [{severity}] {message}")
        if not self.dry_run:
            argv = [sys.executable, str(ALARM), "raise", "--severity", severity, "--key", key,
                    "--message", message]
            if evidence:
                argv += ["--evidence", json.dumps(evidence, default=str)[:4000]]
            run(argv, timeout=60)
        if key not in self.state["active_alarms"]:
            self.state["active_alarms"].append(key)

    def clear_alarm(self, key: str, message: str) -> None:
        if key not in self.state["active_alarms"]:
            return
        self.log(f"ALARM clear {key}: {message}")
        if not self.dry_run:
            run([sys.executable, str(ALARM), "clear", "--key", key, "--message", message], timeout=60)
        self.state["active_alarms"].remove(key)


def run(argv: list[str], timeout: int = 60, **kw) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, **kw)
    except (OSError, subprocess.TimeoutExpired):
        return None


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(obj, indent=2, default=str) + "\n")
    os.replace(tmp, path)


def fmt_gb(n: float | None) -> str:
    return "?" if n is None else f"{n / GB:.1f} GB"


def du_bytes(path: str, timeout: int = 1800) -> int | None:
    if not os.path.exists(path):
        return None
    cp = run(["du", "-sx", "--block-size=1", path], timeout=timeout)
    try:
        return int(cp.stdout.split()[0]) if cp and cp.stdout else None
    except (ValueError, IndexError):
        return None


def open_files(proc_root: str = "/proc") -> set[str]:
    """Paths any visible process holds open (read-only /proc walk)."""
    out: set[str] = set()
    try:
        pids = [p for p in os.listdir(proc_root) if p.isdigit()]
    except OSError:
        return out
    for pid in pids:
        fd_dir = f"{proc_root}/{pid}/fd"
        try:
            fds = os.listdir(fd_dir)
        except OSError:
            continue
        for fd in fds:
            try:
                out.add(os.readlink(f"{fd_dir}/{fd}"))
            except OSError:
                continue
    return out


# --------------------------------------------------------------------------- cheap phase
def disk_free(t: Tick, path: str = DISK_PATH) -> None:
    try:
        free = shutil.disk_usage(path).free
    except OSError as exc:
        t.log(f"disk-free: cannot stat {path}: {exc} (unknown — no raise, no clear)")
        return
    t.state["disk_free_bytes"] = free
    low = free < FREE_WARN
    high = free > FREE_WARN * CLEAR_FACTOR
    t.state["disk_low_streak"] = t.state.get("disk_low_streak", 0) + 1 if low else 0
    t.state["disk_ok_streak"] = t.state.get("disk_ok_streak", 0) + 1 if high else 0
    t.log(f"disk-free {path}: {fmt_gb(free)} (warn<{fmt_gb(FREE_WARN)}, crit<{fmt_gb(FREE_CRIT)})")
    if t.state["disk_low_streak"] >= PERSIST:
        sev = "critical" if free < FREE_CRIT else "warning"
        growers = top_growers(t.state.get("grower_history", []))
        desc = "; ".join(f"{g['path']} {fmt_gb(g['size'])} ({g['delta_label']})" for g in growers) \
            or "no size history yet — run `host_hygiene_tick.py tick --force-heavy`"
        t.raise_alarm(
            "host-disk-free-low", sev,
            f"{path} has {fmt_gb(free)} free (< {fmt_gb(FREE_WARN)}). Top growers: {desc}. "
            f"Worktrees: python3 scripts/system/worktree_gate.py report --sizes",
            {"free_bytes": free, "growers": growers})
        t.state["heavy_due_now"] = True   # refresh the grower ranking at the next open gate
    elif t.state["disk_ok_streak"] >= PERSIST:
        t.clear_alarm("host-disk-free-low", f"{path} back to {fmt_gb(free)} free")


def top_growers(history: list[dict], n: int = 5) -> list[dict]:
    """Rank by growth over ~7 d (else ~1 d, else size) using the daily size snapshots."""
    if not history:
        return []
    latest = history[-1]
    ref = None
    for want_days in (7, 1):
        for h in history[:-1]:
            if latest["at_epoch"] - h["at_epoch"] >= want_days * 86400 * 0.8:
                ref = h
        if ref:
            break
    rows = []
    for path, size in latest["sizes"].items():
        if size is None:
            continue
        if ref and ref["sizes"].get(path) is not None:
            delta = size - ref["sizes"][path]
            days = (latest["at_epoch"] - ref["at_epoch"]) / 86400
            rows.append({"path": path, "size": size, "delta": delta,
                         "delta_label": f"{delta / GB:+.1f} GB in {days:.1f} d"})
        else:
            rows.append({"path": path, "size": size, "delta": None, "delta_label": "no baseline"})
    rows.sort(key=lambda r: (r["delta"] is not None, r["delta"] or 0, r["size"]), reverse=True)
    return rows[:n]


def _load_census():
    sys.path.insert(0, str(ROOT / "scripts" / "coordination"))
    import observer_census  # noqa: E402
    return observer_census


def _running_copies(basename: str, proc_root: str = "/proc") -> list[int]:
    hits = []
    me = os.getpid()
    for p in os.listdir(proc_root):
        if not p.isdigit() or int(p) == me:
            continue
        try:
            argv = Path(f"{proc_root}/{p}/cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        # match the script as an argv element (interpreter + script), never a substring of a grep
        if any(a.decode(errors="replace").endswith("/" + basename) or
               a.decode(errors="replace") == basename for a in argv[:3]):
            hits.append(int(p))
    return hits


def keeper(t: Tick, registry_path: Path = REGISTRY, root: Path = ROOT) -> None:
    try:
        reg = json.loads(registry_path.read_text())
        census = _load_census()
    except Exception as exc:  # noqa: BLE001 — a keeper that cannot read its registry says so
        t.log(f"keeper: cannot load registry/census: {exc}")
        return
    for row in reg.get("observers", []):
        rt = row.get("runtime") or {}
        # Scheduled rows have no daemon to relaunch, including a malformed mixed handover.
        if rt.get("mode") == "scheduled":
            continue
        if not rt.get("relaunch_if_down"):
            continue
        rid = row["id"]
        # None: the census's own canon list (/workspace, its alias, the view) — one definition of
        # canon, shared with daemon_provenance.sh, so a copy we launch is never graded off-canon.
        verdict = census.live_check_row(row, None if root == ROOT else str(root))
        state = verdict["state"]
        t.log(f"keeper {rid}: {state} — {verdict['detail'][:160]}")
        stale_key = f"daemon-stale-{rid}"
        if state == "running_current":
            t.clear_alarm(stale_key, f"{rid} running current code")
            t.clear_alarm(f"daemon-down-{rid}", f"{rid} running")
            continue
        if state in ("running_stale", "running_off_canon"):
            t.raise_alarm(stale_key, "warning",
                          f"{rid} is {state}: {verdict['detail'][:200]}. Restart it (kill pid "
                          f"{verdict.get('pid')} you verified, then the keeper relaunches it).",
                          verdict)
            continue
        if state != "not_running":
            continue   # cannot_tell: fail closed, never launch a second copy on a guess
        basename = os.path.basename(rt.get("expected_path") or row.get("script", ""))
        copies = _running_copies(basename)
        if copies:
            t.log(f"keeper {rid}: pidfile says down but {basename} runs as pid(s) {copies} — not relaunching")
            continue
        last = t.state.setdefault("relaunch_at", {}).get(rid, 0)
        if time.time() - last < RELAUNCH_MIN_S:
            t.log(f"keeper {rid}: relaunch rate-limited (last {int(time.time() - last)} s ago)")
            continue
        canon = census._canonical_roots()[0] if root == ROOT else str(root)
        argv = [a.replace("{canonical_root}", canon) for a in rt.get("start_argv") or []]
        if not argv:
            t.log(f"keeper {rid}: no start_argv")
            continue
        t.state["relaunch_at"][rid] = time.time()
        if t.dry_run:
            t.log(f"keeper {rid}: DRY-RUN would launch {argv}")
            continue
        logp = rt.get("log") or os.devnull
        try:
            with open(logp, "a") as out:
                proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out,
                                        stderr=subprocess.STDOUT, start_new_session=True,
                                        close_fds=True, cwd=canon)
        except OSError as exc:
            t.raise_alarm(f"daemon-down-{rid}", "warning", f"{rid} relaunch failed: {exc}")
            continue
        time.sleep(3)
        if proc.poll() is None:
            t.log(f"keeper {rid}: relaunched pid {proc.pid} ({' '.join(argv)})")
            t.clear_alarm(f"daemon-down-{rid}", f"{rid} relaunched pid {proc.pid}")
        else:
            t.raise_alarm(f"daemon-down-{rid}", "warning",
                          f"{rid} relaunch exited rc={proc.returncode} within 3 s; see {logp}")


def backups(t: Tick, status: Path = BACKUP_STATUS) -> None:
    key = "claude-backups-stale"
    try:
        st = status.stat()
        text = status.read_text(errors="replace").strip()
    except OSError:
        if status.parent.exists():
            t.raise_alarm(key, "warning", f"{status} is missing — the nightly session backup has no status")
        return
    age = time.time() - st.st_mtime
    ok = "OK" in text.split()
    t.log(f"backups: {status} age {age / 3600:.1f} h, '{text[:60]}'")
    if age > BACKUP_MAX_AGE_S or not ok:
        t.raise_alarm(key, "warning",
                      f"claude-backups last status '{text[:80]}' is {age / 3600:.0f} h old "
                      f"(> {BACKUP_MAX_AGE_S // 3600} h or not OK). The host job "
                      "(backup-claude-sessions.sh, host crontab 04:00) did not run or failed. "
                      "(It silently skipped 2026-08-03..10-03.)")
    else:
        t.clear_alarm(key, "claude-backups fresh")


def _event_daemon_copies(proc_root: Path = Path("/proc")) -> list[int]:
    """Strict read-only identity scan. Unreadable live entries are uncertainty.

    This is a preflight, not an atomic exclusion of the unchanged daemon. The
    owning session must stop that daemon and verify its PID before handover.
    """
    hits = []
    inspected = 0
    for entry in proc_root.iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            argv = (entry / "cmdline").read_bytes().split(b"\0")
        except OSError:
            if entry.exists():
                raise
            continue  # exited during the read
        inspected += 1
        if any(Path(a.decode(errors="replace")).name == "opencode_event_reaper.sh"
               for a in argv[:3] if a):
            hits.append(int(entry.name))
    if not inspected:
        raise OSError("process scan inspected no other process")
    return hits


def event_duty(t: Tick, registry_path: Path = REGISTRY, root: Path = ROOT) -> None:
    """Inactive by default; the daily heavy phase never controls event cadence."""
    if os.environ.get("HYGIENE_OPENCODE_EVENTS") != "1":
        return
    def refuse(message: str) -> None:
        t.raise_alarm(EVENT_ALARM, "warning", message)

    try:
        reg = json.loads(registry_path.read_text())
        rows = [r for r in reg["observers"] if r.get("id") == "opencode_event_reaper"]
        if len(rows) != 1:
            raise ValueError("expected exactly one opencode reaper row")
        row = rows[0]
        rt = row["runtime"]
        census = _load_census()
        if census.check_runtime_well_formed({"observers": [row]}):
            raise ValueError("invalid scheduled runtime shape")
        expected_log = str(t.state_dir / "opencode_event_reaper.log")
        if (rt.get("mode") != "scheduled" or rt.get("scheduler") != "host_hygiene_tick"
                or rt.get("restart_on_stale") is not False
                or rt.get("relaunch_if_down") is not False
                or rt.get("log") != expected_log or rt.get("start_argv")
                or row.get("script") != "scripts/system/opencode_event_reaper.sh"):
            raise ValueError("scheduled owner handover is incomplete")
        if not math.isfinite(rt["max_age_s"]):
            raise ValueError("scheduled log freshness limit is not finite")
        script = root / row["script"]
        with script.open() as source:
            capability_source = source.read(262144)
        if EVENT_CAPABILITY not in capability_source:
            raise ValueError("deployed canonical reaper lacks once-status capability")
    except (OSError, ValueError, KeyError, TypeError, AttributeError, ImportError, OverflowError) as exc:
        refuse(f"event-duty handover refused: {exc}")
        return
    last = t.state.get("opencode_event_last_attempt_epoch")
    if last is not None:
        if (not isinstance(last, (int, float)) or isinstance(last, bool)
                or last < 0 or last > time.time() or not math.isfinite(last)):
            refuse("event-duty cadence state is invalid or in the future")
            return
        if time.time() - last < EVENT_INTERVAL_S:
            return
    try:
        copies = _event_daemon_copies()
    except OSError as exc:
        refuse(f"event-duty daemon observation is blind: {exc}")
        return
    if copies:
        refuse(f"event-duty daemon is still present: pids={copies}; owner handover required")
        return
    if t.dry_run:
        t.log("event-duty DRY-RUN would run once-status after the CPU gate")
        return
    # Immediately before execution; a closed gate neither consumes cadence nor clears alarms.
    opened, why = heavy_gate()
    if not opened:
        t.log(f"event-duty deferred: {why}")
        return
    t.state["opencode_event_last_attempt_epoch"] = time.time()
    env = dict(os.environ, EPYC_ROOT=str(root),
               REAPER_ONCE_LOCK=str(t.state_dir / ".opencode-event.lock"))
    cp = run(["/bin/bash", str(script), "once-status"], timeout=EVENT_TIMEOUT_S, env=env)
    result = {"at": now_iso(), "state": "failed", "returncode": None}
    if cp is not None:
        result["returncode"] = cp.returncode
        # Bounded, single terminal marker; reject missing, duplicate or contradictory output.
        output = cp.stdout[-8192:]
        matches = re.findall(r"^LR8_ONCE_STATUS_V1 state=(present|absent|unobservable) "
                             r"prune_rc=([0-9]{1,3})$", output, re.M)
        if (len(cp.stdout) <= 8192 and len(matches) == 1
                and output.rstrip().splitlines()[-1]
                == f"{EVENT_CAPABILITY} state={matches[0][0]} prune_rc={matches[0][1]}"):
            state, prune_rc = matches[0]
            if int(prune_rc) <= 255 and cp.returncode == int(prune_rc) == 0:
                result["state"] = state
        result["output_tail"] = output[-2000:]
    t.state["opencode_event_result"] = result
    result_path = t.state_dir / "opencode_event_result.json"
    try:
        write_json(result_path, result)
        # Atomic replacement: failed writes cannot freshen a partially written census log.
        if result["state"] != "failed":
            write_json(Path(expected_log), result)
    except OSError as exc:
        result["state"] = "failed"
        result["storage_error"] = str(exc)
        t.log(f"event-duty result/log write failed: {exc}")
        try:
            write_json(result_path, result)
        except OSError as record_exc:
            t.log(f"event-duty failure record write failed: {record_exc}")
    if result["state"] in ("failed", "unobservable"):
        refuse(f"event-duty {result['state']}: {result}")
    else:
        t.clear_alarm(EVENT_ALARM, f"event-duty confirmed {result['state']}")


# --------------------------------------------------------------------------- heavy gate
def heavy_gate() -> tuple[bool, str]:
    """(open?, why). Three-valued underneath: unreadable == closed."""
    try:
        cw = json.loads(CPU_WINDOW.read_text())
        exp = cw.get("expires_at")
        expired = False
        if exp:
            expired = dt.datetime.fromisoformat(exp.replace("Z", "+00:00")) < dt.datetime.now(dt.timezone.utc)
        if not expired and (cw.get("loop_holds_claim") or cw.get("state") == "closing"):
            return False, f"autokernel cpu-window: state={cw.get('state')} holds_claim={cw.get('loop_holds_claim')}"
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as exc:
        return False, f"cpu-window unreadable: {exc}"
    cp = run([REGION_LOCK, "status", "--json"], timeout=30)
    if cp is None or cp.returncode != 0:
        return False, "region-lock status unreadable"
    try:
        rows = json.loads(cp.stdout)
    except ValueError:
        return False, "region-lock status not JSON"
    held = [r.get("region") for r in rows if r.get("global_held")]
    if held:
        return False, f"CPU regions held: {held}"
    return True, "no CPU region claimed"


class GateClosed(Exception):
    pass


# --------------------------------------------------------------------------- heavy phase
def heavy(t: Tick, force: bool = False, gate=heavy_gate) -> None:
    last = t.state.get("heavy_last_ok_epoch", 0)
    due = force or t.state.get("heavy_due_now") or time.time() - last >= HEAVY_INTERVAL_S
    if not due:
        return
    ok, why = (True, "forced") if force else gate()
    if not ok:
        t.log(f"heavy: deferred — {why}")
        if last and time.time() - last > HEAVY_STARVED_S:
            t.raise_alarm("host-hygiene-heavy-starved", "warning",
                          f"daily disk-hygiene scan has not run for {(time.time() - last) / 86400:.1f} d "
                          f"(gate: {why}). Run host_hygiene_tick.py tick --force-heavy at a quiet moment.")
        return

    def check():
        if force:
            return
        ok2, why2 = gate()
        if not ok2:
            raise GateClosed(why2)

    try:
        os.nice(19)
    except OSError:
        pass
    started = time.time()
    try:
        grower_snapshot(t, check)
        check()
        stray_files(t)
        check()
        codex_report(t)
    except GateClosed as exc:
        t.log(f"heavy: stopped mid-run, gate closed — {exc}")
        return
    t.state["heavy_last_ok_epoch"] = time.time()
    t.state["heavy_due_now"] = False
    t.clear_alarm("host-hygiene-heavy-starved", "daily disk-hygiene scan ran")
    t.log(f"heavy: done in {time.time() - started:.0f} s")


def grower_snapshot(t: Tick, check) -> None:
    sizes = {}
    for p in GROWERS:
        check()
        sizes[p] = du_bytes(p)
    hist = t.state.setdefault("grower_history", [])
    hist.append({"at": now_iso(), "at_epoch": time.time(), "sizes": sizes})
    del hist[:-HISTORY_KEEP]
    t.log("growers: " + ", ".join(f"{g['path']} {fmt_gb(g['size'])} ({g['delta_label']})"
                                  for g in top_growers(hist)))


def _walk_bounded(root: str, maxdepth: int):
    base = root.rstrip("/").count("/")
    for dirpath, dirnames, filenames in os.walk(root):
        if dirpath.count("/") - base >= maxdepth:
            dirnames[:] = []
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        yield dirpath, filenames


def stray_files(t: Tick, partial_roots=PARTIAL_ROOTS, large_roots=LARGE_ROOTS) -> dict:
    now = time.time()
    held = open_files()
    partials, large = [], []
    for root, depth in partial_roots:
        if not os.path.isdir(root):
            continue
        for dirpath, files in _walk_bounded(root, depth):
            for fn in files:
                if not (fn.endswith(PARTIAL_SUFFIXES) or ".part" in fn.rsplit("/", 1)[-1][-8:]):
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    st = os.lstat(p)
                except OSError:
                    continue
                if now - st.st_mtime < PARTIAL_MIN_AGE_S or p in held:
                    continue
                partials.append({"path": p, "bytes": st.st_size,
                                 "age_days": round((now - st.st_mtime) / 86400, 1)})
    for root, depth in large_roots:
        if not os.path.isdir(root):
            continue
        for dirpath, files in _walk_bounded(root, depth):
            for fn in files:
                p = os.path.join(dirpath, fn)
                try:
                    st = os.lstat(p)
                except OSError:
                    continue
                if st.st_size < LARGE_MIN_BYTES or now - st.st_mtime < LARGE_MIN_AGE_S or p in held:
                    continue
                if any(x["path"] == p for x in partials):
                    continue
                large.append({"path": p, "bytes": st.st_size,
                              "age_days": round((now - st.st_mtime) / 86400, 1)})
    rep = {"schema": "epyc.host_hygiene.stray_files.v1", "generated_at": now_iso(),
           "partials": sorted(partials, key=lambda r: -r["bytes"]),
           "large_tmp_files": sorted(large, key=lambda r: -r["bytes"])}
    write_json(t.state_dir / "stray_files.json", rep)
    pb = sum(r["bytes"] for r in partials)
    lb = sum(r["bytes"] for r in large)
    t.log(f"stray: {len(partials)} partial download(s) {fmt_gb(pb)}, {len(large)} large tmp file(s) {fmt_gb(lb)}")
    if pb + lb > 10 * GB:
        top = (rep["partials"] + rep["large_tmp_files"])[:3]
        t.raise_alarm("stray-download-files", "warning",
                      f"{fmt_gb(pb)} in {len(partials)} abandoned partial downloads and {fmt_gb(lb)} in "
                      f"{len(large)} large tmp files (none held open): "
                      + "; ".join(f"{r['path']} {fmt_gb(r['bytes'])}" for r in top)
                      + f". Full list: {t.state_dir / 'stray_files.json'}",
                      {"partial_bytes": pb, "large_bytes": lb})
    elif pb + lb < 5 * GB:
        t.clear_alarm("stray-download-files", "stray files below 5 GB")
    return rep


def codex_report(t: Tick) -> None:
    script = HERE / "codex_retention_reaper.py"
    if not script.exists():
        return
    cp = run([sys.executable, str(script), "report", "--json"], timeout=1800)
    if cp is None or cp.returncode not in (0,):
        t.log(f"codex: report failed rc={getattr(cp, 'returncode', None)}")
        return
    try:
        rep = json.loads(cp.stdout)
    except ValueError:
        t.log("codex: report is not JSON")
        return
    write_json(t.state_dir / "codex_report.json", rep)
    t.log("codex: report written -> " + str(t.state_dir / "codex_report.json"))


# --------------------------------------------------------------------------- main
def tick(force_heavy: bool = False, dry_run: bool = False, state_dir: Path = STATE_DIR) -> int:
    state_dir.mkdir(parents=True, exist_ok=True)
    lock = open(state_dir / ".tick.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("another hygiene tick is running; exiting")
        return 0
    t = Tick(dry_run=dry_run, state_dir=state_dir)
    try:
        disk_free(t)
        keeper(t)
        backups(t)
        event_duty(t)
        heavy(t, force=force_heavy)
    finally:
        t.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="periodic disk-hygiene tick (see module docstring)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    tp = sub.add_parser("tick")
    tp.add_argument("--force-heavy", action="store_true", help="run the heavy phase now, ignoring the gate")
    tp.add_argument("--dry-run", action="store_true", help="print alarms; never relaunch")
    sub.add_parser("status")
    a = ap.parse_args(argv)
    if a.cmd == "status":
        try:
            print((STATE_DIR / "state.json").read_text())
        except OSError:
            print("{}")
        return 0
    return tick(force_heavy=a.force_heavy, dry_run=a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
