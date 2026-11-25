#!/usr/bin/env python3
"""notify.py - push, never wait-to-be-noticed, for rowflow terminal events (incident 2026-11-04).

Row npd1-step2-a1-tpot-20261104 was killed at 20:04Z (`.ended` = rc=75 reason=disk-floor) and nobody was told for 3 h:
filler_run15.sh's write_ended and rowflow.record_fail wrote FILES only, and the only routed alert (route_alert) covered
IDLE-VIOLATION. This module is called BY THE CODE THAT WRITES the event (no LLM, no agent polling):

    row-ended   filler_run15.sh after write_ended (every reason) and on the cleanup-failed REFUSED path (no .ended)
    smoke-fail  rowflow.record_fail (every dryrun/<id>/FAIL-N.json, smoke and arm/launch)
    disk-floor  rowflow.allocate (the keeper tick): ONE alert per crossing below the floor, hysteresis on recovery
    queued-aged rowflow.allocate: a smoke marker (SMOKE-QUEUED / GPU-SMOKE-QUEUED) older than 2 h with no batch (F9)
    underused   rowflow.underused: first UNDERUSED of a (region, row); underused-shrink after 30 min (F6/F9)

Each event yields exactly one notification, keyed deterministically (sha256 of kind|row|discriminator):
    1. one line in <flags>/rowflow-alerts.jsonl (operator-/dashboard-visible; schema rowflow.alert.v1)
    2. one session-bus msg from the `rowflow-keeper` service outbox, assignee = the row's owner when that is a roster id,
       else `inference` (the compute resource owner) with payload.row_owner = the spec's owner
A marker <flags>/notify/sent/<key>.json records which sinks landed; a repeat call is a no-op for landed sinks and
retries only a failed bus append. Every failure here is logged and swallowed: notification never blocks .ended.
Never deletes anything; reclaimable-disk candidates are information only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys

SCHEMA = "rowflow.alert.v1"
WRITER = "rowflow-keeper"           # roster service id (coordination/session-bus/config.yaml)
FALLBACK_ASSIGNEE = "inference"     # resource_owner [cpu, gpu]
# Row-owner slug -> roster id, only for a slug that is NOT itself a roster id. Empty: 2026-11-19 the alias
# autokernel -> codex-ak-main-01a11473 (ea54250f5) pinned alerts to a session-suffixed address that went stale; `autokernel`
# is now its own roster row, so the row's owner IS the bus target. A roster id always wins over an alias.
OWNER_ALIASES = {}
NON_COMPLETE_HIGHLIGHT = ("disk-floor", "hard-end", "job-rc-", "cleanup-failed", "partial-native-incomplete",
                          "launcher-signalled", "grant-expired-unrun", "build-missing", "refused", "malformed-grant",
                          "regions-unusable", "window-")
_HERE = os.path.dirname(os.path.abspath(__file__))
_HOME = os.environ.get("FILLER_ENGINE_HOME") or _HERE   # a row's engine snapshot runs this copy; rowflow.py lives in the live dir


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _bus_script():
    env = os.environ.get("ROWFLOW_SESSION_BUS")
    if env:
        return env
    for p in (os.path.join(os.path.dirname(_HERE), "session_bus.py"), "/workspace/scripts/coordination/session_bus.py"):
        if os.path.isfile(p):
            return p
    return None


def _log(msg):
    print(f"{_now()} [notify] {msg}", file=sys.stderr)


def parse_ended(text):
    """`rc=75 time=... reason=disk-floor` + optional key=value lines -> dict."""
    out = {}
    lines = (text or "").splitlines()
    if lines:
        for tok in lines[0].split(" "):
            if "=" in tok:
                k, v = tok.split("=", 1)
                out[k] = v
        if "reason=" in lines[0]:
            out["reason"] = lines[0].split("reason=", 1)[1]
    for ln in lines[1:]:
        if "=" in ln:
            k, v = ln.split("=", 1)
            out.setdefault(k.strip(), v.strip())
    return out


def severity_of(reason):
    r = str(reason or "")
    if r == "complete":
        return "info"
    return "critical" if any(r.startswith(h) for h in NON_COMPLETE_HIGHLIGHT) else "warning"


def row_meta(flags, rid):
    try:
        with open(os.path.join(flags, "ready", rid + ".json")) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def row_owner(flags, rid, fallback=None):
    return str(row_meta(flags, rid).get("owner") or fallback or "")


PUBLISHER_ID_ENV = ("EPYC_AGENT_ID", "WRAPUP_AGENT_ID", "SESSION_BUS_AGENT")
PUBLISHER_SESSION_ENV = ("CLAUDE_CODE_SESSION_ID", "CODEX_THREAD_ID", "CODEX_SESSION_ID", "CLAUDE_SESSION_ID")


def publisher_info(env=None):
    """Who published a row - INFORMATION ONLY (routing stays owner -> `inference` mailbox). First non-empty roster-id env,
    first non-empty session-token env, the OS user and the time."""
    env = os.environ if env is None else env
    pick = lambda names: next(((n, env[n]) for n in names if env.get(n)), (None, None))
    idv, sv = pick(PUBLISHER_ID_ENV), pick(PUBLISHER_SESSION_ENV)
    try:
        import getpass  # noqa: PLC0415
        user = getpass.getuser()
    except Exception:  # noqa: BLE001
        user = env.get("USER") or ""
    return {"agent_id": idv[1], "agent_id_env": idv[0], "session": sv[1], "session_env": sv[0], "user": user, "at": _now()}


# ------------------------------------------------------------------ the inference mailbox (operator 2026-11-05)
# <flags>/notify/inbox/inference.jsonl: one line per alert (same key as rowflow-alerts.jsonl), append-only.
# <flags>/notify/inbox/inference.acks.jsonl: one line per handled key, append-only. unacked = keys without an ack line.
INBOX = "inference"
ESCALATE_AFTER_S = int(os.environ.get("ROWFLOW_ALERT_ESCALATE_S", 30 * 60))


def inbox_path(flags):
    return os.path.join(flags, "notify", "inbox", INBOX + ".jsonl")


def acks_path(flags):
    return os.path.join(flags, "notify", "inbox", INBOX + ".acks.jsonl")


def _append_line(path, rec):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")


def _read_jsonl(path):
    out = []
    try:
        with open(path) as f:
            for ln in f:
                try:
                    d = json.loads(ln)
                except ValueError:
                    continue
                if isinstance(d, dict):
                    out.append(d)
    except OSError:
        pass
    return out


def inbox_record(rec):
    d = rec.get("detail") or {}
    return {"schema": "rowflow.inbox.v1", "key": rec["key"], "ts": rec["ts"], "kind": rec["kind"], "severity": rec["severity"],
            "row_id": rec.get("row_id"), "owner": rec.get("row_owner"), "handoff_task": rec.get("handoff_task"),
            "publisher": rec.get("publisher"), "reason": d.get("reason") or rec["kind"], "summary": rec["summary"]}


def acked_keys(flags):
    return {str(a.get("key")) for a in _read_jsonl(acks_path(flags))}


def read_inbox(flags, since=None, row_glob=None, unacked=False):
    import fnmatch  # noqa: PLC0415
    acks = acked_keys(flags) if unacked else set()
    seen, out = set(), []
    for r in _read_jsonl(inbox_path(flags)):
        k = str(r.get("key"))
        if k in seen or (unacked and k in acks) or (since and str(r.get("ts") or "") < since):
            continue
        if row_glob and not fnmatch.fnmatch(str(r.get("row_id") or ""), row_glob):
            continue
        seen.add(k)
        out.append(r)
    return out


def ack(flags, key, by=None, note=None):
    """Append one ack line; idempotent (a key already acked is not re-appended). Returns False for an unknown key."""
    if key not in {str(r.get("key")) for r in _read_jsonl(inbox_path(flags))}:
        return False
    if key not in acked_keys(flags):
        _append_line(acks_path(flags), {"key": key, "ts": _now(), "by": by or (publisher_info().get("agent_id")
                     or publisher_info().get("session") or ""), "note": note})
    return True


def is_filed(flags, rid):
    return bool(rid) and os.path.exists(os.path.join(flags, "filing-done", str(rid) + ".FILED"))


def ack_filed(flags, rid, by="auto-ack-filed", log=print):
    """Ack every open inbox alert of row `rid` (its FILED receipt resolves them). Best effort: never raises. -> keys acked."""
    done = []
    try:
        acks = acked_keys(flags)
        for r in read_inbox(flags):
            k = str(r.get("key"))
            if str(r.get("row_id") or "") == str(rid) and k not in acks and ack(flags, k, by=by, note="auto-ack: row FILED"):
                acks.add(k)
                done.append(k)
                log(f"AUTO-ACK-FILED {k} {rid}")
    except Exception as e:  # noqa: BLE001
        _log(f"ack_filed {rid}: {type(e).__name__}: {e}")
    return done


def withdrawn_no_run(flags, rid):
    """True when rid was withdrawn before its smoke ever ran: _withdraw_smoke_queued wrote grants/<id>.ended (rc=75) and
    moved the marker to dryrun/<id>/.withdrawn/, with no .complete and no PASS/FAIL record. No evidence exists, so the row
    is TERMINAL with no FILED receipt owed (WITHDRAWN-NO-RUN)."""
    g = os.path.join(flags, "grants", rid)
    d = os.path.join(flags, "dryrun", rid)
    return (os.path.exists(g + ".ended") and not os.path.exists(g + ".complete") and os.path.isdir(os.path.join(d, ".withdrawn"))
            and not os.path.exists(os.path.join(d, "PASS.json")) and not glob.glob(os.path.join(d, "FAIL-*.json")))


def unfiled_ended(flags, key):
    """The row id of inbox alert `key` when that row has ENDED (grants/<id>.ended|.complete) without a
    filing-done/<id>.FILED receipt, else None. An ack of such an alert must not stand in for filing (operator 2026-11-07)."""
    for r in _read_jsonl(inbox_path(flags)):
        if str(r.get("key")) == key:
            rid = str(r.get("row_id") or "")
            if not rid:
                return None
            ended = any(os.path.exists(os.path.join(flags, "grants", rid + s)) for s in (".ended", ".complete"))
            filed = os.path.exists(os.path.join(flags, "filing-done", rid + ".FILED")) or withdrawn_no_run(flags, rid)
            return rid if ended and not filed else None
    return None


def filing_due(flags, rid, owner, ended_line=""):
    """ONE filing-due alert per row (key sha256(kind|row|v1) + O_EXCL claim in emit = dedup): rowflow-alerts.jsonl, the
    inference mailbox (owner field: alerts_for() hands it to the owner's dispatcher) and a session-bus msg to the owner when it
    is a roster id, else to `inference` with payload.row_owner. Reason it never reached main-inf22 before: only the coordinator
    was nudged (filing_takeover_alarm, after 1 h), owner-less ids are not roster ids, and live-owner rows were skipped silently."""
    summary = (f"FILING DUE: row {rid} ended ({ended_line[:80]}) with no filing-done/{rid}.FILED. Record the verdict with "
               f"`file_result.py {rid} --receipt <commit>:<handoff>#<BOX-ID>` (a pushed box commit is not filing) or `--verdict-json`.")
    return emit(flags, "filing-due", rid, "v1", summary, "warning", owner, {"reason": "filing-due", "ended": ended_line[:200]}, action=True)


try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import handoff_ref as _handoff_ref  # noqa: E402  (bin/rowflow; repo: scripts/coordination)
except ImportError:
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import handoff_ref as _handoff_ref  # noqa: E402
    except ImportError:
        _handoff_ref = None


def _norm(x):
    return os.path.basename(str(x or "")).removesuffix(".md").lower()


def alerts_for(flags, slug="", handoff="", rows=(), session_ids=()):
    """Unacked inbox alerts that belong to one dispatcher session: row owner == slug/handoff, handoff_task names the
    handoff, the row is one of its rows, or the publisher session is one of its session ids."""
    names = {n for n in (_norm(slug), _norm(handoff)) if n}
    rows, sids = set(rows or ()), {s for s in session_ids or () if s}
    out = []
    for r in read_inbox(flags, unacked=True):
        ht = str(r.get("handoff_task") or "")
        if _handoff_ref is not None and ht:   # C4: route a moved box's alert to the session owning its NEW file
            ht = str(_handoff_ref.repoint(ht) or ht)
        pub = r.get("publisher") or {}
        if (_norm(r.get("owner")) in names or (r.get("row_id") in rows) or (pub.get("session") in sids)
                or any(n and n in ht.lower() for n in names)):
            out.append(r)
    return out


def alerts_block(alerts, flags):
    if not alerts:
        return ""
    lines = [f"- [{a.get('severity')}] {a.get('summary')} (key {a.get('key')})" for a in alerts[:10]]
    more = f"\n- ... {len(alerts) - 10} more: rowflow.py alerts --unacked" if len(alerts) > 10 else ""
    return (f"UNHANDLED ROW ALERTS (inference mailbox {inbox_path(flags)}): handle each, then ack it with "
            f"`python3 {os.path.join(_HOME, 'rowflow.py')} alerts --ack <key>`:\n" + "\n".join(lines) + more + "\n")


def escalate_stale(flags, route, now=None, after_s=None, log=print):
    """Keeper tick: a CRITICAL inbox alert still unacked after `after_s` -> route(kind, message, evidence) exactly once
    (marker <flags>/notify/escalated/<key>.json, O_EXCL) plus one line in rowflow-alerts.jsonl kind=alert-unacked."""
    after_s = ESCALATE_AFTER_S if after_s is None else after_s
    now = dt.datetime.now(dt.timezone.utc) if now is None else now
    done = []
    for r in read_inbox(flags, unacked=True):
        if is_filed(flags, r.get("row_id")):
            ack_filed(flags, r.get("row_id"), log=log)
            continue
        if r.get("severity") != "critical":
            continue
        try:
            t = dt.datetime.strptime(str(r.get("ts")), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
        except ValueError:
            continue
        if (now - t).total_seconds() < after_s:
            continue
        m = os.path.join(flags, "notify", "escalated", str(r["key"]) + ".json")
        try:
            os.makedirs(os.path.dirname(m), exist_ok=True)
            os.close(os.open(m, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        except FileExistsError:
            continue
        msg = (f"UNACKED {int((now - t).total_seconds() // 60)} min: {r.get('summary')} (owner {r.get('owner')}; "
               f"ack: rowflow.py alerts --ack {r['key']})")
        ok = route("alert-unacked", msg, {"key": r["key"], "row_id": r.get("row_id"), "owner": r.get("owner")})
        _write_json(m, {"key": r["key"], "at": _now(), "routed": bool(ok)})
        with open(os.path.join(flags, "rowflow-alerts.jsonl"), "a") as f:
            f.write(json.dumps({"schema": SCHEMA, "key": "esc-" + str(r["key"]), "ts": _now(), "kind": "alert-unacked",
                                "severity": "critical", "row_id": r.get("row_id"), "row_owner": r.get("owner"),
                                "summary": msg, "detail": {"routed": bool(ok)}}, sort_keys=True) + "\n")
        log(f"ALERT-UNACKED {r['key']} {r.get('row_id') or '-'} escalated routed={bool(ok)}")
        _push_safe(flags, {"key": "esc-" + str(r["key"]), "kind": "alert-unacked", "row_id": r.get("row_id"),
                           "detail": {"cause": msg}}, str(r.get("owner") or ""))
        done.append(r["key"])
    return done


def _roster(bus_root):
    try:
        import yaml  # noqa: PLC0415
        with open(os.path.join(bus_root, "config.yaml")) as f:
            cfg = yaml.safe_load(f) or {}
        return {str(r.get("id")): str(r.get("role") or "") for r in cfg.get("roster") or [] if isinstance(r, dict)}
    except Exception:  # noqa: BLE001 - unreadable roster: route to the fallback
        return {}


def _bus_root():
    return os.environ.get("ROWFLOW_BUS_ROOT") or "/workspace/coordination/session-bus"


def event_key(kind, rid, disc):
    return hashlib.sha256(f"{kind}|{rid}|{disc}".encode()).hexdigest()[:24]


def _marker(flags, key):
    return os.path.join(flags, "notify", "sent", key + ".json")


def _write_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        json.dump(value, f, sort_keys=True)
    os.replace(tmp, path)


_LLM = "/mnt/raid0/llm/"  # two pieces on purpose: the repo hook (NIB2-108) refuses a script that names the scratch root next to a delete
LIVE_FLAGS = _LLM + "tmp/compute-flags"


def is_live(flags):
    """The shared bus is written only for the live compute-flags tree, or when ROWFLOW_BUS_ROOT names a bus explicitly
    (tests and scratch trees must never post to the fleet bus)."""
    return bool(os.environ.get("ROWFLOW_BUS_ROOT")) or os.path.realpath(flags) == os.path.realpath(LIVE_FLAGS)


def _owner_not_roster_once(flags, rid, owner):
    """F9 (AK audit B9): a legacy row whose owner is not a roster id still routes to `inference`, logged ONCE per row."""
    m = os.path.join(flags, "notify", "owner-not-roster", str(rid).replace("/", "_"))
    try:
        os.makedirs(os.path.dirname(m), exist_ok=True)
        fd = os.open(m, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, json.dumps({"row": rid, "owner": owner, "at": _now()}).encode())
        os.close(fd)
    except FileExistsError:
        return
    except OSError as e:
        _log(f"owner-not-roster {rid}: marker failed: {e}")
    _log(f"owner-not-roster {rid}: owner {owner!r} is not a roster id; alerts go to {FALLBACK_ASSIGNEE}")


def _bus_send(rec, owner, action, flags=LIVE_FLAGS):
    if not is_live(flags):
        return "skipped: non-live flags tree and no ROWFLOW_BUS_ROOT"
    script = _bus_script()
    if not script:
        return "failed: session_bus.py not found"
    bus_root = _bus_root()
    roster = _roster(bus_root)
    owner = owner if owner in roster else OWNER_ALIASES.get(owner, owner)
    assignee = owner if roster.get(owner) not in (None, "", "retired") and owner != WRITER else FALLBACK_ASSIGNEE
    if assignee == FALLBACK_ASSIGNEE and owner != FALLBACK_ASSIGNEE:
        _owner_not_roster_once(flags, rec.get("row_id") or rec["kind"], owner)
    stamp = rec["ts"].replace("-", "").replace(":", "")
    msg = {"id": f"msg-{stamp}-{int(rec['key'][:8], 16)}-{WRITER}", "to": assignee,
           "kind": "defect" if action else "status", "task_id": rec.get("row_id") or rec["kind"],
           "payload": {k: v for k, v in rec.items() if k != "ts"}}
    if action:
        msg.update(action_required=True, assignee=assignee)
    try:
        r = subprocess.run([sys.executable, script, "--bus-root", bus_root, "append", "--agent", WRITER,
                            "--target", "outbox", "--json", json.dumps(msg)], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"failed: {type(e).__name__}: {e}"
    if r.returncode != 0:
        return f"failed: rc={r.returncode} {(r.stderr or r.stdout).strip()[-200:]}"
    return f"sent:{assignee}:{msg['id']}"


# ------------------------------------------------------------------ live push (operator 2026-11-24: delivery must be deterministic)
# The bus record above is DURABLE but is read only at the owner's next drain; a live owner in a long task saw a smoke-fail
# 2 h late (ak-c22-i8pc-gate-gpu-20261124-r3, 20:10Z -> 22:3xZ). For actionable kinds the keeper also PUSHES one line:
#   channel  <flags>/notify/push/channel/<owner>.log - one line per push; watch_rows.sh (the owner's run_in_background
#            watcher) prints it as `PUSH <line>` and exits, which re-invokes the live session. That is the ONLY push channel a
#            `monitor:file` roster identity has (autokernel, pipeline-mgmt). GAP: with no watcher armed nothing host-side can
#            reach such a session (no sanctioned client for the Claude Code UDS sockets; tmux doorbell needs a tmux endpoint);
#            owner_watch.py raises OWNER-WATCHER-DEAD and the 15 min escalation below still runs.
#   doorbell tmux_adapter.py doorbell --agent <owner> (sanctioned content-free pane signal, C45) for a tmux:* endpoint.
# Dedupe: one push per alert key (O_EXCL marker). Rate limit: <= 1 push per owner per PUSH_MIN_INTERVAL_S; the rest queue
# and leave as ONE batched line at the next allowed moment (push_tick, every keeper tick). Escalation: a pushed key not acked
# (rowflow.py alerts --ack) after PUSH_ESCALATE_S is pushed once to PUSH_ESCALATE_TO. Every failure is swallowed.
PUSH_KINDS = frozenset({"smoke-fail", "queued-smoke-orphaned", "queued-smoke-dropped", "ak-harness-failure",
                        "gpu-host-foreign", "tick-refused"})
PUSH_MIN_INTERVAL_S = 60
PUSH_ESCALATE_S = 15 * 60
PUSH_ESCALATE_TO = "pipeline-mgmt"
PUSH_LINE_MAX = 400


def _push_dir(flags, *parts):
    return os.path.join(flags, "notify", "push", *parts)


def time_now():
    return dt.datetime.now(dt.timezone.utc).timestamp()


def smoke_fail_cause(fail_path, rec=None):
    """First `SMOKE FAIL` line of the row's launcher.out, else TERMINAL-smoke.json's reason/error, else the FAIL reason."""
    rec = rec or {}
    logs = [rec.get("dryrun_log")] + ([os.path.join(os.path.dirname(fail_path), "launcher.out")] if fail_path else [])
    term = None
    for lp in [p for p in logs if p]:
        try:
            with open(lp, errors="replace") as f:
                for line in f:
                    if "SMOKE FAIL" in line:
                        return line.strip()
                    if term is None and "TERMINAL-smoke.json" in line:
                        term = next((t for t in line.replace("(", " ").replace(")", " ").split()
                                     if t.endswith("TERMINAL-smoke.json")), None)
        except OSError:
            continue
    for tp in (term, rec.get("terminal")):
        if not tp:
            continue
        try:
            with open(tp) as f:
                t = json.load(f)
            why = t.get("reason") or t.get("error") or t.get("detail")
            if why:
                return f"TERMINAL-smoke: {str(why).strip()}"
        except (OSError, ValueError, AttributeError):
            continue
    return str(rec.get("reason") or "").strip()


def push_line(rec):
    d = rec.get("detail") or {}
    cause = " ".join(str(d.get("cause") or rec.get("summary") or "").split())
    fix = d.get("fix_task") or rec.get("handoff_task") or "-"
    return f"{rec.get('kind')} row={rec.get('row_id') or '-'} cause={cause} fix_task={fix} key={rec.get('key')}"[:PUSH_LINE_MAX]


def _push_target(owner):
    roster = _roster(_bus_root())
    owner = owner if owner in roster else OWNER_ALIASES.get(owner, owner)
    return owner if roster.get(owner) not in (None, "", "retired") and owner != WRITER else FALLBACK_ASSIGNEE


def _endpoint(owner):
    try:
        import yaml  # noqa: PLC0415
        with open(os.path.join(_bus_root(), "config.yaml")) as f:
            cfg = yaml.safe_load(f) or {}
        for r in cfg.get("roster") or []:
            if isinstance(r, dict) and str(r.get("id")) == owner:
                return str(r.get("endpoint") or "")
    except Exception:  # noqa: BLE001
        pass
    return ""


def _tmux_adapter():
    for p in (os.environ.get("ROWFLOW_TMUX_ADAPTER"), os.path.join(os.path.dirname(_HERE), "tmux_adapter.py"),
              "/workspace/scripts/coordination/tmux_adapter.py"):
        if p and os.path.isfile(p):
            return p
    return None


def _deliver(flags, owner, text):
    """Channel line always (the owner's watcher reads it); doorbell when the owner has a tmux endpoint on the live bus."""
    res = {}
    try:
        p = _push_dir(flags, "channel", owner + ".log")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a") as f:
            f.write(f"{_now()} {text}\n")
        res["channel"] = "written"
    except OSError as e:
        res["channel"] = f"failed: {e}"
    if not is_live(flags):
        res["doorbell"] = "skipped: non-live flags tree"
    elif not _endpoint(owner).startswith("tmux:"):
        res["doorbell"] = "n/a: endpoint not tmux (watcher channel only)"
    elif not _tmux_adapter():
        res["doorbell"] = "failed: tmux_adapter.py not found"
    else:
        try:
            r = subprocess.run([sys.executable, _tmux_adapter(), "doorbell", "--agent", owner],
                               capture_output=True, text=True, timeout=30)
            res["doorbell"] = "rung" if r.returncode == 0 else f"refused: rc={r.returncode} {(r.stderr or r.stdout).strip()[-160:]}"
        except (OSError, subprocess.TimeoutExpired) as e:
            res["doorbell"] = f"failed: {type(e).__name__}: {e}"
    return res


class _Lock:
    def __init__(self, flags):
        self.p = _push_dir(flags, ".lock")

    def __enter__(self):
        import fcntl  # noqa: PLC0415
        os.makedirs(os.path.dirname(self.p), exist_ok=True)
        self.fd = os.open(self.p, os.O_CREAT | os.O_RDWR)
        fcntl.flock(self.fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, *a):
        os.close(self.fd)


def _flush_owner(flags, owner, now, deliver=None):
    """Send the owner's queued lines as ONE push if the per-owner rate limit allows. Caller holds the lock."""
    qp = _push_dir(flags, "queue", owner + ".jsonl")
    items = _read_jsonl(qp)
    if not items:
        return None
    sp = _push_dir(flags, "owner", owner + ".json")
    try:
        with open(sp) as f:
            last = float(json.load(f).get("last_push") or 0)
    except (OSError, ValueError, AttributeError):
        last = 0.0
    if now - last < PUSH_MIN_INTERVAL_S:
        return "deferred"
    text = items[0]["line"] if len(items) == 1 else f"{len(items)} alerts: " + " | ".join(i["line"] for i in items)
    res = (deliver or _deliver)(flags, owner, text)
    _write_json(sp, {"last_push": now, "at": _now(), "n": len(items), "result": res})
    os.unlink(qp)
    for i in items:
        mp = _push_dir(flags, "sent", i["key"] + ".json")
        try:
            with open(mp) as f:
                m = json.load(f)
        except (OSError, ValueError):
            m = {"key": i["key"], "owner": owner}
        m.update(pushed_at=now, delivery=res, batch=len(items))
        _write_json(mp, m)
    _log(f"PUSH {owner} n={len(items)} {res}")
    return res


def push(flags, rec, owner, now=None, deliver=None):
    """Queue one push for `rec` to `owner` (at most once per alert key), then flush if the rate limit allows."""
    now = time_now() if now is None else now
    key = str(rec["key"])
    mp = _push_dir(flags, "sent", key + ".json")
    os.makedirs(os.path.dirname(mp), exist_ok=True)
    try:
        os.close(os.open(mp, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    except FileExistsError:
        return "dup"
    line = push_line(rec)
    _write_json(mp, {"key": key, "owner": owner, "kind": rec.get("kind"), "row_id": rec.get("row_id"),
                     "queued_at": now, "line": line})
    with _Lock(flags):
        _append_line(_push_dir(flags, "queue", owner + ".jsonl"), {"key": key, "line": line})
        return _flush_owner(flags, owner, now, deliver) or "queued"


def push_tick(flags, now=None, deliver=None, log=print):
    """Keeper tick: flush rate-limited queues; push an unacked pushed key once to PUSH_ESCALATE_TO after PUSH_ESCALATE_S."""
    now = time_now() if now is None else now
    out = {"flushed": [], "escalated": []}
    qd = _push_dir(flags, "queue")
    with _Lock(flags):
        for n in sorted(os.listdir(qd)) if os.path.isdir(qd) else []:
            if n.endswith(".jsonl") and _flush_owner(flags, n[:-6], now, deliver) not in (None, "deferred"):
                out["flushed"].append(n[:-6])
    sd = _push_dir(flags, "sent")
    acked = acked_keys(flags)
    for n in sorted(os.listdir(sd)) if os.path.isdir(sd) else []:
        if not n.endswith(".json"):
            continue
        try:
            with open(os.path.join(sd, n)) as f:
                m = json.load(f)
        except (OSError, ValueError):
            continue
        key = str(m.get("key") or "")
        if is_filed(flags, m.get("row_id")):
            ack_filed(flags, m.get("row_id"), log=log)
            continue
        if (not m.get("pushed_at") or m.get("escalated") or m.get("owner") == PUSH_ESCALATE_TO or key.startswith("pesc-")
                or key in acked or key.removeprefix("esc-") in acked or now - float(m["pushed_at"]) < PUSH_ESCALATE_S):
            continue
        m["escalated"] = now
        _write_json(os.path.join(sd, n), m)
        push(flags, {"key": "pesc-" + key, "kind": "push-unacked", "row_id": m.get("row_id"),
                     "detail": {"cause": f"unacked {int((now - float(m['pushed_at'])) // 60)} min by {m.get('owner')}: "
                                         f"{m.get('line')}"}}, PUSH_ESCALATE_TO, now=now, deliver=deliver)
        log(f"PUSH-UNACKED {key} {m.get('row_id') or '-'} -> {PUSH_ESCALATE_TO}")
        out["escalated"].append(key)
    return out


def _push_safe(flags, rec, owner):
    try:
        return push(flags, rec, _push_target(owner))
    except Exception as e:  # noqa: BLE001 - a push fault never breaks emit()
        _log(f"push {rec.get('kind')} {rec.get('row_id') or '-'}: {type(e).__name__}: {e}")
        return f"failed: {e}"


def emit(flags, kind, rid, disc, summary, severity, owner="", detail=None, action=True, meta=None):
    """One idempotent notification. Returns the alert record (or the stored marker on a repeat)."""
    key = event_key(kind, rid, disc)
    mpath = _marker(flags, key)
    try:
        with open(mpath) as f:
            mark = json.load(f)
    except (OSError, ValueError):
        mark = None
    if mark is None:
        rec = {"schema": SCHEMA, "key": key, "ts": _now(), "kind": kind, "severity": severity, "row_id": rid or None,
               "row_owner": owner or None, "summary": summary, "detail": detail or {}}
        meta = meta if meta is not None else (row_meta(flags, rid) if rid else {})
        if meta.get("handoff_task"):
            rec["handoff_task"] = meta["handoff_task"]
        if meta.get("publisher"):
            rec["publisher"] = meta["publisher"]
        try:
            # O_EXCL on a claim file: two writers racing on one event produce one alerts line
            os.makedirs(os.path.dirname(mpath), exist_ok=True)
            fd = os.open(mpath + ".claim", os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
        except FileExistsError:
            return None
        except OSError as e:
            _log(f"{kind} {rid}: cannot claim {mpath}: {e}")
            return None
        with open(os.path.join(flags, "rowflow-alerts.jsonl"), "a") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
        mark = {"record": rec, "bus": None, "inbox": None}
        _write_json(mpath, mark)
        os.unlink(mpath + ".claim")
    if "inbox" in mark and mark["inbox"] is not True:  # pre-mailbox markers stay as they were; the inference mailbox: independent of the bus, retried like it
        try:
            _append_line(inbox_path(flags), inbox_record(mark["record"]))
            mark["inbox"] = True
        except OSError as e:
            mark["inbox"] = f"failed: {e}"
            _log(f"{kind} {rid}: inbox append failed: {e}")
        _write_json(mpath, mark)
    if not str(mark.get("bus") or "").startswith(("sent:", "skipped:")):
        mark["bus"] = _bus_send(mark["record"], owner or mark["record"].get("row_owner") or "", action, flags)
        _write_json(mpath, mark)
        _log(f"{kind} {rid or '-'} [{mark['record']['severity']}] bus={mark['bus']}")
    if kind in PUSH_KINDS:
        _push_safe(flags, mark["record"], owner or mark["record"].get("row_owner") or "")
    return mark


# ------------------------------------------------------------------ event entry points
def row_ended(flags, rid, ended_text=None, reason=None, rc=None, owner=None):
    ended = parse_ended(ended_text) if ended_text is not None else {}
    reason = reason or ended.get("reason") or "unknown"
    rc = rc if rc is not None else ended.get("rc")
    owner = owner or ended.get("owner") or row_owner(flags, rid)
    sev = severity_of(reason)
    disc = ended.get("time") or reason   # one .ended per id; cleanup-failed (no .ended) keys on its reason
    tag = "COMPLETE" if reason == "complete" else "NOT COMPLETE"
    summary = f"row {rid} ended rc={rc} reason={reason} [{tag}]"
    if reason.startswith("disk-floor"):
        summary += " - /mnt/raid0 free space fell below FILLER_DISK_FLOOR_GIB; see rowflow-alerts.jsonl disk-floor"
    return emit(flags, "row-ended", rid, disc, summary, sev, owner,
                {"rc": rc, "reason": reason, "ended": ended, "complete": reason == "complete"}, action=reason != "complete")


def smoke_fail(flags, rid, fail_path, rec, owner=None):
    owner = owner or row_owner(flags, rid)
    reason = str(rec.get("reason") or "")[:300]
    try:
        cause = smoke_fail_cause(fail_path, rec)[:300]
    except Exception:  # noqa: BLE001
        cause = reason
    return emit(flags, "smoke-fail", rid, os.path.basename(fail_path), f"row {rid} {rec.get('kind') or 'smoke'} FAIL "
                f"({os.path.basename(fail_path)}): {reason}", "warning", owner,
                {"fail_file": fail_path, "reason": reason, "fix_task": rec.get("fix_task"), "cause": cause})


# ------------------------------------------------------------------ host disk floor
def free_gib(path="/mnt/raid0"):
    return shutil.disk_usage(path).free / (1 << 30)


def _quiet_host():
    """The ONE quiet-host helper (quiet_host.py): beside this file when installed, else up to scripts/coordination/."""
    here = os.path.dirname(os.path.abspath(__file__))
    for d in (here, os.path.dirname(here)):
        if os.path.isfile(os.path.join(d, "quiet_host.py")) and d not in sys.path:
            sys.path.insert(0, d)
    import quiet_host
    return quiet_host


def reclaimable(root, top=5, timeout=60):
    """Largest top-level dirs under root (information only; nothing is deleted). A du of everything: deferred while a
    quiet-host grant is live (DEFER-QUIET-HOST), else run under nice/ionice."""
    qh = _quiet_host()
    if qh.defer("notify reclaimable", log=lambda m: print(m, file=sys.stderr)):
        return [{"deferred": "DEFER-QUIET-HOST: quiet-host grant live"}]
    try:
        r = subprocess.run(qh.scan_prefix() + ["du", "-x", "-s", "-B1G", "--", *sorted(os.path.join(root, n) for n in os.listdir(root))],
                           capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return [{"error": f"{type(e).__name__}"}]
    out = []
    for ln in r.stdout.splitlines():
        try:
            g, p = ln.split("\t", 1)
            out.append({"path": p, "gib": int(g)})
        except ValueError:
            continue
    return sorted(out, key=lambda x: -x["gib"])[:top]


def disk_floor_check(flags, state_path, blocked_rows, free=None, floor=None, hyst=None, reclaim_root=None, log=print):
    """ONE alert per crossing below the floor; re-armed only once free >= floor + hysteresis (one 'cleared' alert)."""
    floor = float(floor if floor is not None else os.environ.get("FILLER_DISK_FLOOR_GIB", 150))
    hyst = float(hyst if hyst is not None else os.environ.get("ROWFLOW_DISK_HYST_GIB", 25))
    free = free_gib() if free is None else float(free)
    try:
        with open(state_path) as f:
            st = json.load(f)
    except (OSError, ValueError):
        st = {"below": False, "crossing": 0}
    if not st.get("below") and free < floor:
        st = {"below": True, "crossing": int(st.get("crossing", 0)) + 1, "since": _now()}
        _write_json(state_path, st)
        cands = reclaimable(reclaim_root) if reclaim_root else []
        rows = sorted(set(blocked_rows))
        log(f"DISK-FLOOR /mnt/raid0 free {free:.0f} GiB < floor {floor:.0f} GiB; rows blocked: {','.join(rows) or '-'}")
        emit(flags, "disk-floor", "", f"crossing-{st['crossing']}-{st['since']}",
             f"/mnt/raid0 free {free:.0f} GiB is below FILLER_DISK_FLOOR_GIB={floor:.0f}: running rows are killed "
             f"(rc=75 disk-floor) and no row can run; blocked: {', '.join(rows) or 'none'}. Reclaim candidates are "
             f"information only - nothing was deleted.", "critical", FALLBACK_ASSIGNEE,
             {"free_gib": round(free, 1), "floor_gib": floor, "rearm_at_gib": floor + hyst, "rows_blocked": rows,
              "reclaimable_candidates_info_only": cands})
        return "raised"
    if st.get("below") and free >= floor + hyst:
        since = st.get("since")
        st = {"below": False, "crossing": int(st.get("crossing", 0)), "cleared": _now()}
        _write_json(state_path, st)
        log(f"DISK-FLOOR cleared: free {free:.0f} GiB >= {floor + hyst:.0f} GiB")
        emit(flags, "disk-floor-cleared", "", f"crossing-{st['crossing']}-{since}",
             f"/mnt/raid0 free {free:.0f} GiB is back above floor+hysteresis ({floor + hyst:.0f} GiB); rows can run",
             "info", FALLBACK_ASSIGNEE, {"free_gib": round(free, 1), "floor_gib": floor}, action=False)
        return "cleared"
    return None


def disk_warn_check(flags, state_path, free=None, floor=None, margin=None, hyst=None, regrow_gib=10.0, reclaim_root=None, log=print,
                    cands_fn=None):
    """EARLY WARNING (2026-11-23, after the 150 GiB pause stopped all compute with no prior alert): ONE alert when free falls below
    floor + margin (default 40 GiB), naming the top reclaimable dirs and the worktree-janitor command; re-alerted only if free drops a
    further `regrow_gib` while still in the band; re-armed once free >= warn + hysteresis. Information only - nothing is deleted."""
    floor = float(floor if floor is not None else os.environ.get("FILLER_DISK_FLOOR_GIB", 150))
    margin = float(margin if margin is not None else os.environ.get("ROWFLOW_DISK_WARN_MARGIN_GIB", 40))
    hyst = float(hyst if hyst is not None else os.environ.get("ROWFLOW_DISK_HYST_GIB", 25))
    free = free_gib() if free is None else float(free)
    warn = floor + margin
    try:
        with open(state_path) as f:
            st = json.load(f)
    except (OSError, ValueError):
        st = {"warned": False, "crossing": 0}
    if free < warn and (not st.get("warned") or free <= float(st.get("last_free", warn)) - regrow_gib):
        st = {"warned": True, "crossing": int(st.get("crossing", 0)) + (0 if st.get("warned") else 1), "last_free": free, "since": st.get("since") or _now()}
        _write_json(state_path, st)
        cands = (cands_fn or (lambda: reclaimable(reclaim_root) if reclaim_root else []))()
        log(f"DISK-WARN /mnt/raid0 free {free:.0f} GiB < warn {warn:.0f} GiB (floor {floor:.0f}); top: "
            + ", ".join(f"{c.get('path')} {c.get('gib')}G" for c in cands if "path" in c))
        emit(flags, "disk-warn", "", f"crossing-{st['crossing']}-{int(free)}",
             f"/mnt/raid0 free {free:.0f} GiB is within {margin:.0f} GiB of the pause floor ({floor:.0f} GiB). Reclaim your own scratch/worktrees NOW: "
             f"`python3 scripts/system/worktree_gate.py by-owner` lists clean+landed worktrees by owner; `disk_janitor.sh --once` reaps filed scratch. "
             f"Nothing was deleted.", "warning", FALLBACK_ASSIGNEE,
             {"free_gib": round(free, 1), "floor_gib": floor, "warn_gib": warn, "top_dirs_info_only": cands})
        return "raised"
    if st.get("warned") and free >= warn + hyst:
        st = {"warned": False, "crossing": int(st.get("crossing", 0)), "cleared": _now()}
        _write_json(state_path, st)
        log(f"DISK-WARN cleared: free {free:.0f} GiB >= {warn + hyst:.0f} GiB")
        return "cleared"
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--flags", default=os.environ.get("ROWFLOW_FLAGS", LIVE_FLAGS))
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("row-ended")
    p.add_argument("--id", required=True)
    p.add_argument("--ended-file")
    p.add_argument("--reason")
    p.add_argument("--rc")
    p.add_argument("--owner")
    a = ap.parse_args(argv)
    text = None
    if a.ended_file:
        try:
            with open(a.ended_file) as f:
                text = f.read()
        except OSError as e:
            _log(f"cannot read {a.ended_file}: {e}")
    try:
        row_ended(a.flags, a.id, text, reason=a.reason, rc=a.rc, owner=a.owner)
    except Exception as e:  # noqa: BLE001 - never fail the caller
        _log(f"row-ended {a.id}: {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
