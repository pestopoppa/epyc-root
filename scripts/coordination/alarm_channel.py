#!/usr/bin/env python3
"""alarm_channel.py — THE operator-reachable alarm channel (P0-1).

Owning handoff: handoffs/active/loop-owned-fleet-implementation.md § Phase 0 / P0-1
Conventions:    coordination/session-bus/BUS_PROTOCOL.md (advisory / last-hop escalation)

--------------------------------------------------------------------------
WHY THIS EXISTS
--------------------------------------------------------------------------
Every alarm this fleet has ever raised went to `coordination/session-bus/advisory.jsonl`,
which is delivered to NO ONE. On 2026-08-14 the whole fleet was dead for ELEVEN HOURS
while every internal signal fired correctly and no human ever learned of it. A signal
that terminates inside the machine is not a signal; it is a log line.

This module is the last hop: machine -> a channel a human actually reads. It is
deliberately small, stdlib-only, and has exactly one job.

--------------------------------------------------------------------------
THE FOUR PROPERTIES THAT MAKE IT USABLE
--------------------------------------------------------------------------
1. EMIT ONCE ON STATE CHANGE, NEVER PER TICK. An alarm has an identity (its `key`)
   and a lifecycle: inactive -> active (notify) -> ... -> inactive (notify the
   resolution). Re-raising an already-active key updates its evidence and its
   occurrence count and notifies NOBODY. The gate metric is "zero alarms on a
   well-run night" — a channel that pages every 60s trains the operator to mute it,
   which is exactly how you get an 11-hour outage with all lights blinking.

2. THE LOCAL FILE IS ALWAYS WRITTEN. The push backend is best-effort; the local
   JSONL record is the durable one. Ordering is deliberate: file FIRST, push
   second, so a crash mid-push still leaves the forensic record. That ordering
   means the first record can only honestly say `delivery: pending`, so the
   OUTCOME is a second record — `delivery-result` (ok / skipped_not_live /
   skipped_disabled) or the loud `delivery-failed`. "Was a human actually
   paged?" is therefore answered by a record being PRESENT, never by inferring
   it from the absence of one. Per notification the log holds:
       {"event":"raised"|"cleared", "delivery":"pending"}   <- it happened
       {"event":"delivery-result"|"delivery-failed", ...}   <- what came of it

3. A FAILED DELIVERY IS ITSELF AN EVENT, NEVER A SILENT SWALLOW. If the push
   backend is unreachable the alarm still lands locally AND a `delivery-failed`
   record is appended AND a loud line goes to stderr AND the process exits
   non-zero. (Origin class: `feedback_fail_open_defaults_conceal_their_own_corruption`
   — a fail-open notifier is worse than no notifier, because it manufactures the
   belief that someone was told.)

4. IT SHIPS DISABLED-BUT-CONFIGURED. The default config carries a PLACEHOLDER
   endpoint containing the sentinel `REPLACE-ME`. While the sentinel is present the
   module never touches the network; it records `skipped_not_live` loudly. Nothing
   in this repo tries to reach an endpoint the operator did not choose.

--------------------------------------------------------------------------
GOING LIVE — THE EXACT ONE-LINE CHANGE
--------------------------------------------------------------------------
In `coordination/session-bus/alarm_config.yaml`, replace the single `url:` line
under `ntfy:` with your real topic, e.g.

      url: https://ntfy.sh/epyc-fleet-a7f3c1-alarms      # <- the only edit needed

Then `scripts/coordination/alarm_channel.py test` must print DELIVERED and the
phone must buzz. No other key needs touching: `enabled: true` and `backend: ntfy`
are already the shipped defaults, and the placeholder sentinel is what holds the
channel back. (`enabled: false` remains available as an explicit kill switch.)

Pick a topic name with ~10 random characters: an ntfy topic IS its password.

--------------------------------------------------------------------------
CONFIG PARSING
--------------------------------------------------------------------------
`pyyaml` IS importable in both the system python3 and
`/mnt/raid0/llm/epyc-orchestrator/.venv` (checked 2026-08-16, 6.0.3), and
`session_bus.py` uses it. This module still prefers a ~60-line hand-rolled
parser for the tiny nested-scalar subset the config uses, so that the ALARM path
— the one thing that must work when everything else is broken — has zero import
surface beyond the stdlib. A config file whose first non-comment character is `{`
is parsed as JSON instead.

--------------------------------------------------------------------------
EXIT CODES
--------------------------------------------------------------------------
    0   ok — notified, suppressed as duplicate, or nothing to do
    3   the alarm was RECORDED LOCALLY but PUSH DELIVERY FAILED
    4   the alarm could not even be recorded locally (channel is broken)
    64  usage error

Usage:
    alarm_channel.py raise --severity critical --key fleet-absent \
        --message "0 live roster mains; assignment halted" \
        [--evidence '{"live_mains":0,"checked":"tmux+heartbeat"}'] [--dry-run]
    alarm_channel.py clear --key fleet-absent [--message "3 mains back up"]
    alarm_channel.py status [--json]
    alarm_channel.py test [--dry-run]

Environment overrides (used by the drill; production reads the config file):
    ALARM_STATE_PATH    dedupe state json      (default coordination/session-bus/alarm_state.json)
    ALARM_CONFIG_PATH   config file            (default coordination/session-bus/alarm_config.yaml)
    ALARM_FILE_PATH     durable local record   (default from config `file.path`)
    ALARM_BACKEND       force backend          (ntfy|email|file)
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:  # POSIX only; the module degrades to "no cross-process lock" without it
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX
    fcntl = None  # type: ignore[assignment]

# ── constants ──────────────────────────────────────────────────────────────
SCHEMA_STATE = "alarm_channel.state.v1"
SCHEMA_ALARM = "alarm_channel.alarm.v1"
SCHEMA_ADVISORY = "session_bus.advisory.v1"   # BUS_PROTOCOL advisory row shape
SCHEMA_CONFIG = "alarm_channel.config.v1"

PLACEHOLDER_SENTINEL = "REPLACE-ME"

SEVERITIES = ("critical", "warning")

EXIT_OK = 0
EXIT_DELIVERY_FAILED = 3
EXIT_UNRECORDABLE = 4
EXIT_USAGE = 64

REPO_ROOT = Path(__file__).resolve().parents[2]
BUS_ROOT = REPO_ROOT / "coordination" / "session-bus"

DEFAULT_CONFIG_PATH = BUS_ROOT / "alarm_config.yaml"
DEFAULT_STATE_PATH = BUS_ROOT / "alarm_state.json"
DEFAULT_ALARM_FILE = BUS_ROOT / "alarms.jsonl"

# What the module falls back to when the config file is missing entirely. It is
# the shipped default, verbatim — a missing config must not mean "no alarms", it
# must mean "alarms still land in the local file".
BUILTIN_CONFIG: dict[str, Any] = {
    "schema_version": SCHEMA_CONFIG,
    "enabled": True,
    "backend": "ntfy",
    "advisory_mirror": False,
    "ntfy": {
        "url": f"https://ntfy.sh/{PLACEHOLDER_SENTINEL}-epyc-fleet-alarms",
        "timeout_s": 10,
        "priority_critical": "urgent",
        "priority_warning": "default",
    },
    "email": {
        "to": f"{PLACEHOLDER_SENTINEL}@example.invalid",
        "from": "epyc-fleet@localhost",
        "smtp_host": "localhost",
        "smtp_port": 25,
        "timeout_s": 20,
    },
    "file": {"path": str(DEFAULT_ALARM_FILE)},
}


class AlarmError(RuntimeError):
    """The channel itself is broken (unwritable state / record file)."""


# ── time ───────────────────────────────────────────────────────────────────
def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ── minimal YAML subset parser ─────────────────────────────────────────────
def _scalar(raw: str) -> Any:
    """Coerce a YAML scalar. Quoted -> string verbatim; else typed."""
    s = raw.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    low = s.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    if low in ("null", "~", ""):
        return None
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the nested-scalar-mapping subset this config uses.

    Supports: `# comments`, blank lines, `key: value`, and nesting by indent
    (any consistent width). Sequences are NOT supported and raise loudly rather
    than being silently dropped — a config key that vanishes quietly is how a
    notifier ends up pointed at nothing.
    """
    stripped = text.lstrip()
    if stripped.startswith("{"):
        return json.loads(text)

    root: dict[str, Any] = {}
    # stack of (indent, mapping); the mapping at the top owns the current level
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        body = line.strip()
        if body.startswith("- "):
            raise ValueError(
                f"alarm config line {lineno}: sequences are not supported by the "
                f"built-in parser ({body!r}); keep the config to nested key: value"
            )
        # strip trailing comment when it is not inside quotes
        if "#" in body:
            quote = None
            for i, ch in enumerate(body):
                if ch in ("'", '"'):
                    quote = None if quote == ch else (quote or ch)
                elif ch == "#" and quote is None and (i == 0 or body[i - 1] == " "):
                    body = body[:i].rstrip()
                    break
        if ":" not in body:
            raise ValueError(f"alarm config line {lineno}: expected 'key: value', got {body!r}")

        key, _, value = body.partition(":")
        key = key.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise ValueError(f"alarm config line {lineno}: indentation underflow")
        parent = stack[-1][1]
        if value.strip() == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _scalar(value)
    return root


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Read the config, overlaying it on BUILTIN_CONFIG (missing keys keep defaults)."""
    cfg_path = path or Path(os.environ.get("ALARM_CONFIG_PATH", str(DEFAULT_CONFIG_PATH)))
    merged: dict[str, Any] = json.loads(json.dumps(BUILTIN_CONFIG))  # deep copy
    if cfg_path.exists():
        try:
            parsed = parse_simple_yaml(cfg_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:  # loud, never silent — a broken config is an alarm-class defect
            print(f"alarm_channel: WARNING unreadable config {cfg_path}: {exc}; using built-in defaults",
                  file=sys.stderr)
            parsed = {}
        for k, v in parsed.items():
            if isinstance(v, dict) and isinstance(merged.get(k), dict):
                merged[k].update(v)
            else:
                merged[k] = v
    merged["_config_path"] = str(cfg_path)

    backend_env = os.environ.get("ALARM_BACKEND")
    if backend_env:
        merged["backend"] = backend_env
    file_env = os.environ.get("ALARM_FILE_PATH")
    if file_env:
        merged.setdefault("file", {})["path"] = file_env
    return merged


# ── state (dedupe) ─────────────────────────────────────────────────────────
def state_path_from_env(explicit: Path | None = None) -> Path:
    if explicit:
        return explicit
    return Path(os.environ.get("ALARM_STATE_PATH", str(DEFAULT_STATE_PATH)))


def _read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": SCHEMA_STATE, "active": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8") or "{}")
    except Exception as exc:
        # A corrupt state file must NOT silently reset to "nothing is active" —
        # that would re-notify everything. It is quarantined and reported loudly.
        quarantine = path.with_suffix(path.suffix + f".corrupt-{int(time.time())}")
        try:
            path.replace(quarantine)
        except OSError:
            pass
        print(f"alarm_channel: WARNING alarm state {path} was corrupt ({exc}); "
              f"quarantined at {quarantine}. Active alarms may re-notify once.", file=sys.stderr)
        return {"schema_version": SCHEMA_STATE, "active": {}}
    if not isinstance(data, dict):
        return {"schema_version": SCHEMA_STATE, "active": {}}
    data.setdefault("schema_version", SCHEMA_STATE)
    if not isinstance(data.get("active"), dict):
        data["active"] = {}
    return data


def _write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".alarm_state.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class _StateLock:
    """Cross-process exclusion so two tickers cannot both decide 'it is new'."""

    def __init__(self, path: Path):
        self.lock_path = path.with_suffix(path.suffix + ".lock")
        self._fh = None

    def __enter__(self):
        if fcntl is None:
            return self
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.lock_path, "a+")
        fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        if self._fh is not None:
            try:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            finally:
                self._fh.close()
                self._fh = None
        return False


# ── delivery backends ──────────────────────────────────────────────────────
def _is_placeholder(value: Any) -> bool:
    return isinstance(value, str) and PLACEHOLDER_SENTINEL in value


def _render(event: dict[str, Any]) -> tuple[str, str]:
    """(title, body) for a push backend."""
    sev = event["severity"].upper()
    verb = "RESOLVED" if event["event"] == "cleared" else sev
    title = f"[EPYC {verb}] {event['key']}"
    lines = [event["message"], "", f"key:      {event['key']}",
             f"severity: {event['severity']}", f"event:    {event['event']}",
             f"host:     {event['host']}", f"time:     {event['ts']}"]
    ev = event.get("evidence") or {}
    if ev:
        lines.append("")
        lines.append("evidence:")
        for k in sorted(ev):
            lines.append(f"  {k}: {ev[k]}")
    return title, "\n".join(lines)


def _deliver_ntfy(cfg: dict[str, Any], event: dict[str, Any]) -> None:
    ntfy = cfg.get("ntfy") or {}
    url = ntfy.get("url")
    if not url:
        raise AlarmError("ntfy backend selected but ntfy.url is unset")
    title, body = _render(event)
    prio = ntfy.get("priority_critical" if event["severity"] == "critical" else "priority_warning", "default")
    if event["event"] == "cleared":
        prio = "default"
    tag = {"critical": "rotating_light", "warning": "warning"}.get(event["severity"], "bell")
    if event["event"] == "cleared":
        tag = "white_check_mark"
    req = urllib.request.Request(
        url,
        data=body.encode("utf-8"),
        method="POST",
        headers={"Title": title, "Priority": str(prio), "Tags": tag,
                 "Content-Type": "text/plain; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=float(ntfy.get("timeout_s", 10))) as resp:
        # NB: `getattr(resp, "status", resp.getcode())` would be wrong — Python
        # evaluates the default eagerly, so it calls getcode() even when
        # `.status` exists, and explodes on any response object lacking it.
        code = getattr(resp, "status", None)
        if code is None:
            code = resp.getcode()
        if not (200 <= int(code) < 300):
            raise AlarmError(f"ntfy returned HTTP {code}")


def _deliver_email(cfg: dict[str, Any], event: dict[str, Any]) -> None:
    import smtplib
    from email.message import EmailMessage

    em = cfg.get("email") or {}
    to = em.get("to")
    if not to:
        raise AlarmError("email backend selected but email.to is unset")
    title, body = _render(event)
    msg = EmailMessage()
    msg["Subject"] = title
    msg["From"] = em.get("from", "epyc-fleet@localhost")
    msg["To"] = to
    msg.set_content(body)
    with smtplib.SMTP(em.get("smtp_host", "localhost"), int(em.get("smtp_port", 25)),
                      timeout=float(em.get("timeout_s", 20))) as smtp:
        smtp.send_message(msg)


PUSH_BACKENDS = {"ntfy": _deliver_ntfy, "email": _deliver_email}


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, sort_keys=True) + "\n"
    with open(path, "a", encoding="utf-8") as fh:
        if fcntl is not None:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        fh.write(line)
        fh.flush()
        os.fsync(fh.fileno())


def _alarm_file(cfg: dict[str, Any]) -> Path:
    return Path((cfg.get("file") or {}).get("path") or DEFAULT_ALARM_FILE)


def _mirror_advisory(cfg: dict[str, Any], event: dict[str, Any]) -> None:
    """Optional BUS_PROTOCOL advisory row. OFF by default.

    advisory.jsonl is read by no human — that is the whole reason this module
    exists — so mirroring is opt-in and purely for the machine-side record.
    """
    if not cfg.get("advisory_mirror"):
        return
    kind = {"raised": "alarm-raised", "cleared": "alarm-cleared",
            "delivery-failed": "alarm-delivery-failed"}.get(event["event"], "alarm")
    row = {
        "schema_version": SCHEMA_ADVISORY,
        "ts": event["ts"],
        "kind": kind,
        "alarm_key": event["key"],
        "severity": event["severity"],
        "reason": event["message"],
    }
    try:
        _append_jsonl(BUS_ROOT / "advisory.jsonl", row)
    except OSError as exc:
        print(f"alarm_channel: WARNING advisory mirror failed: {exc}", file=sys.stderr)


# ── the core: notify exactly once, record always ───────────────────────────
def _notify(cfg: dict[str, Any], event: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    """Record locally (always) then push (best effort, loudly on failure).

    Returns the event, annotated with `delivery` and `backend`.
    """
    backend = str(cfg.get("backend", "file")).strip().lower()
    event["backend"] = backend
    path = _alarm_file(cfg)

    if dry_run:
        event["delivery"] = "dry-run"
        title, body = _render(event)
        print("--- DRY RUN: would append to", path, "---")
        print(json.dumps(event, indent=2, sort_keys=True))
        if backend in PUSH_BACKENDS:
            target = (cfg.get(backend) or {}).get("url") or (cfg.get(backend) or {}).get("to")
            live = "NOT LIVE (placeholder)" if _is_placeholder(target) else "live"
            print(f"--- DRY RUN: would push via {backend} -> {target} [{live}] ---")
            print(f"Title: {title}")
            print(body)
        return event

    # 1. durable local record FIRST — a crash mid-push still leaves forensics.
    #    It is written as `delivery: pending` because at this instant that is the
    #    truth. The outcome is a SECOND record (`delivery-result`, or the loud
    #    `delivery-failed`), so the log never claims an outcome it did not observe
    #    and "was a human actually paged?" is answered by a record's presence
    #    rather than by inferring from the absence of one.
    event["delivery"] = "pending"
    try:
        _append_jsonl(path, event)
    except OSError as exc:
        raise AlarmError(f"could not write the durable alarm record {path}: {exc}") from exc

    # 2. push, best effort
    if not cfg.get("enabled", True):
        event["delivery"] = "skipped_disabled"
        print(f"alarm_channel: NOTICE channel disabled in config ({cfg.get('_config_path')}); "
              f"alarm recorded locally only -> {path}", file=sys.stderr)
    elif backend == "file":
        event["delivery"] = "ok"
    elif backend not in PUSH_BACKENDS:
        event["delivery"] = "failed"
        event["delivery_error"] = f"unknown backend {backend!r}"
        _record_failure(cfg, event, path)
    else:
        target = (cfg.get(backend) or {}).get("url") or (cfg.get(backend) or {}).get("to")
        if _is_placeholder(target):
            event["delivery"] = "skipped_not_live"
            print(f"alarm_channel: NOTICE {backend} endpoint is still the PLACEHOLDER "
                  f"({target}); nothing was pushed. Alarm recorded at {path}. "
                  f"Edit the one `url:` line in {cfg.get('_config_path')} to go live.",
                  file=sys.stderr)
        else:
            try:
                PUSH_BACKENDS[backend](cfg, event)
                event["delivery"] = "ok"
            except Exception as exc:  # noqa: BLE001 — a notifier may never raise past here

                event["delivery"] = "failed"
                event["delivery_error"] = f"{type(exc).__name__}: {exc}"
                _record_failure(cfg, event, path)

    # 3. the outcome is its own record. `delivery-failed` (loud, written by
    #    _record_failure) already covers the failure case; everything else gets a
    #    `delivery-result` line so the durable log states, positively, what
    #    happened to this notification.
    if event["delivery"] != "failed":
        try:
            _append_jsonl(path, {
                "schema_version": SCHEMA_ALARM,
                "ts": _now(),
                "event": "delivery-result",
                "severity": event["severity"],
                "key": event["key"],
                "message": f"{event['event']} {event['key']!r}: delivery={event['delivery']}",
                "evidence": {"original_event": event["event"], "original_ts": event["ts"]},
                "backend": backend,
                "delivery": event["delivery"],
                "host": event.get("host"),
                "pid": os.getpid(),
            })
        except OSError as exc:
            print(f"alarm_channel: WARNING could not record the delivery result: {exc}",
                  file=sys.stderr)

    _mirror_advisory(cfg, event)
    return event


def _record_failure(cfg: dict[str, Any], event: dict[str, Any], path: Path) -> None:
    """A failed delivery is itself an event. Loud on stderr, durable on disk."""
    failure = {
        "schema_version": SCHEMA_ALARM,
        "ts": _now(),
        "event": "delivery-failed",
        "severity": "critical",
        "key": event["key"],
        "message": (f"ALARM DELIVERY FAILED via {event.get('backend')}: "
                    f"{event.get('delivery_error')} — the alarm {event['key']!r} was recorded "
                    f"locally but NO HUMAN WAS PAGED."),
        "evidence": {"original_event": event["event"],
                     "backend": event.get("backend"),
                     "error": event.get("delivery_error"),
                     "record": str(path)},
        "host": event.get("host"),
        "pid": os.getpid(),
        "delivery": "n/a",
    }
    try:
        _append_jsonl(path, failure)
    except OSError as exc:
        print(f"alarm_channel: CRITICAL could not even record the delivery failure: {exc}",
              file=sys.stderr)
    print(f"alarm_channel: DELIVERY FAILED [{event.get('backend')}] key={event['key']}: "
          f"{event.get('delivery_error')} — alarm recorded at {path}, NOBODY WAS PAGED.",
          file=sys.stderr)
    _mirror_advisory(cfg, failure)


def raise_alarm(key: str, severity: str, message: str, evidence: dict[str, Any] | None = None,
                *, cfg: dict[str, Any] | None = None, state_file: Path | None = None,
                dry_run: bool = False) -> dict[str, Any]:
    """Raise `key`. Notifies ONLY on the inactive -> active transition.

    Returns {"action": "notified"|"suppressed", "event": {...}|None, "active": {...}}.
    """
    if severity not in SEVERITIES:
        raise ValueError(f"severity must be one of {SEVERITIES}, got {severity!r}")
    if not key or any(c.isspace() for c in key):
        raise ValueError(f"alarm key must be a short whitespace-free identity, got {key!r}")
    cfg = cfg or load_config()
    sp = state_path_from_env(state_file)

    with _StateLock(sp):
        state = _read_state(sp)
        now = _now()
        active = state["active"]
        existing = active.get(key)

        if existing:
            # STATE UNCHANGED -> no notification. This is the whole point.
            existing["count"] = int(existing.get("count", 1)) + 1
            existing["last_seen"] = now
            existing["message"] = message
            if evidence:
                existing["evidence"] = evidence
            if not dry_run:
                _write_state(sp, state)
            return {"action": "suppressed", "event": None, "active": existing}

        event = {
            "schema_version": SCHEMA_ALARM,
            "ts": now,
            "event": "raised",
            "severity": severity,
            "key": key,
            "message": message,
            "evidence": evidence or {},
            "host": socket.gethostname(),
            "pid": os.getpid(),
        }
        event = _notify(cfg, event, dry_run)
        if not dry_run:
            active[key] = {
                "severity": severity,
                "message": message,
                "evidence": evidence or {},
                "raised_at": now,
                "last_seen": now,
                "notified_at": now,
                "count": 1,
                "delivery": event.get("delivery"),
            }
            _write_state(sp, state)
        return {"action": "notified", "event": event, "active": active.get(key)}


def clear_alarm(key: str, message: str | None = None, *, cfg: dict[str, Any] | None = None,
                state_file: Path | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Resolve `key`. Notifies ONCE if it was active; a no-op otherwise."""
    cfg = cfg or load_config()
    sp = state_path_from_env(state_file)

    with _StateLock(sp):
        state = _read_state(sp)
        entry = state["active"].get(key)
        if entry is None:
            return {"action": "not-active", "event": None}
        now = _now()
        event = {
            "schema_version": SCHEMA_ALARM,
            "ts": now,
            "event": "cleared",
            "severity": entry.get("severity", "warning"),
            "key": key,
            "message": message or f"RESOLVED: {entry.get('message', key)}",
            "evidence": {"raised_at": entry.get("raised_at"),
                         "occurrences_while_active": entry.get("count", 1)},
            "host": socket.gethostname(),
            "pid": os.getpid(),
        }
        event = _notify(cfg, event, dry_run)
        if not dry_run:
            del state["active"][key]
            history = state.setdefault("recent_resolved", [])
            history.append({"key": key, "raised_at": entry.get("raised_at"),
                            "cleared_at": now, "count": entry.get("count", 1)})
            del history[:-50]
            _write_state(sp, state)
        return {"action": "notified", "event": event}


def status(state_file: Path | None = None) -> dict[str, Any]:
    sp = state_path_from_env(state_file)
    state = _read_state(sp)
    return {"state_path": str(sp), "active": state.get("active", {}),
            "recent_resolved": state.get("recent_resolved", [])[-10:]}


# ── CLI ────────────────────────────────────────────────────────────────────
def _exit_for(event: dict[str, Any] | None) -> int:
    if event and event.get("delivery") == "failed":
        return EXIT_DELIVERY_FAILED
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="alarm_channel.py",
        description="The operator-reachable alarm channel: emit once on state change.",
    )
    ap.add_argument("--dry-run", action="store_true", help="print what would be delivered; deliver nothing")
    ap.add_argument("--state", type=Path, default=None, help="override the dedupe state file")
    ap.add_argument("--config", type=Path, default=None, help="override the config file")
    ap.add_argument("--json", action="store_true", help="machine-readable stdout")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_raise = sub.add_parser("raise", help="raise an alarm (notifies only on state change)")
    p_raise.add_argument("--severity", choices=SEVERITIES, required=True)
    p_raise.add_argument("--key", required=True, help="the alarm identity, e.g. fleet-absent")
    p_raise.add_argument("--message", required=True)
    p_raise.add_argument("--evidence", default=None, help="JSON object of supporting evidence")

    p_clear = sub.add_parser("clear", help="resolve an alarm (notifies the resolution once)")
    p_clear.add_argument("--key", required=True)
    p_clear.add_argument("--message", default=None)

    sub.add_parser("status", help="list active alarms")
    sub.add_parser("test", help="send a test alarm end-to-end")

    args = ap.parse_args(argv)
    cfg = load_config(args.config)

    try:
        if args.cmd == "raise":
            evidence = None
            if args.evidence:
                try:
                    evidence = json.loads(args.evidence)
                except json.JSONDecodeError as exc:
                    print(f"alarm_channel: --evidence must be a JSON object: {exc}", file=sys.stderr)
                    return EXIT_USAGE
                if not isinstance(evidence, dict):
                    print("alarm_channel: --evidence must be a JSON OBJECT", file=sys.stderr)
                    return EXIT_USAGE
            res = raise_alarm(args.key, args.severity, args.message, evidence,
                              cfg=cfg, state_file=args.state, dry_run=args.dry_run)
            if args.json:
                print(json.dumps(res, indent=2, sort_keys=True))
            elif res["action"] == "suppressed":
                a = res["active"]
                print(f"suppressed: {args.key!r} already active since {a['raised_at']} "
                      f"(occurrence #{a['count']}) — no re-notification by design")
            else:
                d = (res["event"] or {}).get("delivery")
                print(f"notified: {args.key!r} raised ({args.severity}) delivery={d}")
            return _exit_for(res.get("event"))

        if args.cmd == "clear":
            res = clear_alarm(args.key, args.message, cfg=cfg,
                              state_file=args.state, dry_run=args.dry_run)
            if args.json:
                print(json.dumps(res, indent=2, sort_keys=True))
            elif res["action"] == "not-active":
                print(f"not-active: {args.key!r} was not active; nothing cleared, nobody notified")
            else:
                print(f"notified: {args.key!r} RESOLVED delivery={(res['event'] or {}).get('delivery')}")
            return _exit_for(res.get("event"))

        if args.cmd == "status":
            st = status(args.state)
            if args.json:
                print(json.dumps(st, indent=2, sort_keys=True))
                return EXIT_OK
            backend = cfg.get("backend")
            target = (cfg.get(backend) or {}).get("url") or (cfg.get(backend) or {}).get("to") \
                if isinstance(cfg.get(backend), dict) else None
            live = "DISABLED (enabled: false)" if not cfg.get("enabled", True) else (
                "NOT LIVE — placeholder endpoint; edit the one `url:` line to go live"
                if _is_placeholder(target) else "LIVE")
            print(f"config:  {cfg.get('_config_path')}")
            print(f"backend: {backend} -> {target}  [{live}]")
            print(f"record:  {_alarm_file(cfg)}")
            print(f"state:   {st['state_path']}")
            if not st["active"]:
                print("active alarms: none  (this is the well-run-night state)")
            else:
                print(f"active alarms: {len(st['active'])}")
                for k, v in sorted(st["active"].items()):
                    print(f"  [{v['severity']:8s}] {k}  since {v['raised_at']}  "
                          f"x{v['count']}  — {v['message']}")
            return EXIT_OK

        if args.cmd == "test":
            key = "alarm-channel-selftest"
            # A test must always deliver, so it clears itself first.
            clear_alarm(key, "self-test reset", cfg=cfg, state_file=args.state, dry_run=args.dry_run)
            res = raise_alarm(key, "warning",
                              "Self-test from alarm_channel.py — if you are reading this on "
                              "your phone, the last hop works.",
                              {"invoked_by": os.environ.get("USER", "unknown"),
                               "host": socket.gethostname()},
                              cfg=cfg, state_file=args.state, dry_run=args.dry_run)
            delivery = (res["event"] or {}).get("delivery")
            if args.json:
                print(json.dumps(res, indent=2, sort_keys=True))
            else:
                print(f"test alarm delivery={delivery} (record: {_alarm_file(cfg)})")
                if delivery == "ok":
                    print("DELIVERED")
                elif delivery == "skipped_not_live":
                    print("NOT DELIVERED — endpoint is still the placeholder. "
                          "Edit the `url:` line in the config to go live.")
                elif delivery == "failed":
                    print("DELIVERY FAILED — see stderr above.")
            if not args.dry_run:
                clear_alarm(key, "self-test complete", cfg=cfg, state_file=args.state)
            return _exit_for(res.get("event"))

    except AlarmError as exc:
        print(f"alarm_channel: CHANNEL BROKEN: {exc}", file=sys.stderr)
        return EXIT_UNRECORDABLE
    except ValueError as exc:
        print(f"alarm_channel: {exc}", file=sys.stderr)
        return EXIT_USAGE

    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
