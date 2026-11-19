#!/usr/bin/env python3
"""Owner-less filing pass (keeper-friction-review 2026-11-05, refinement 3). Run by filing_watch.sh each minute.

    python3 scripts/coordination/churn/auto_file.py [--flags DIR] [--dry-run] [--owner-age-s N] [--min-age-s N]

For every unfiled run in filing-due.jsonl (grants/<id>.ended|.complete, no filing-done/<id>.FILED):
  * decision_rule parses with file_result.py's own parser -> run file_result.py <id> (the ONLY sanctioned writer of
    FILED records); the result is logged and pushed to the owner's mailbox as a non-action notice.
  * prose rule, owner live (handoff-sessions.json status running with a live pid, a fresh bus heartbeat, or a fresh
    bus outbox write) -> nothing; the owner files it.
  * prose rule, owner not live, run ended >= --min-age-s ago -> one line in filing-owner-less.jsonl (the standing
    filer's queue: it files with `file_result.py <id> --verdict-json V`) and ONE alarm per newly queued batch.
Each run is attempted once (filing-autofile.state.json); never writes .FILED/.verdict.json itself; kills nothing.
"""
import argparse, datetime, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "rowflow"))
import file_result  # noqa: E402
import filing  # noqa: E402  (the end-record / manifest readers)

DEFAULT_FLAGS = os.environ.get("ROWFLOW_FLAGS", "/mnt/raid0/llm/tmp/compute-flags")
DEFAULT_BUS = os.environ.get("FILING_WATCH_BUS_ROOT", "/workspace/coordination/session-bus")


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(flags, msg):
    with open(os.path.join(flags, "filing-watch.log"), "a") as f:
        f.write(f"{now_iso()} auto-file {msg}\n")


def machine_checkable(rule):
    try:
        file_result.parse(str(rule or ""))
        return True
    except file_result.RuleError:
        return False


def _pid_alive(pid):
    try:
        r = subprocess.run(["ps", "-o", "stat=", "-p", str(int(pid))], capture_output=True, text=True, timeout=10)
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0 and bool(r.stdout.strip()) and not r.stdout.strip().startswith("Z")


def _ts(v):
    try:
        return datetime.datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def owner_live(owner, flags, bus_root, max_age_s, now=None):
    """-> (bool, why). Unknown/empty owner is never live."""
    now = now or time.time()
    if not owner or owner == "?":
        return False, "no owner"
    names = {owner}
    for pre in ("h-", "handoff-"):
        if owner.startswith(pre):
            names.add(owner[len(pre):])
    try:
        with open(os.path.join(flags, "handoff-sessions.json")) as f:
            sessions = (json.load(f) or {}).get("sessions") or {}
        for n in names:
            s = sessions.get(n)
            if isinstance(s, dict) and s.get("status") == "running" and s.get("pid") and _pid_alive(s["pid"]):
                return True, f"handoff-sessions {n} running pid {s['pid']}"
    except (OSError, ValueError, AttributeError):
        pass
    for n in names:
        try:
            with open(os.path.join(bus_root, "heartbeats", n + ".json")) as f:
                t = _ts(json.load(f).get("ts"))
            if t and now - t <= max_age_s:
                return True, f"heartbeat {n} fresh"
        except (OSError, ValueError, AttributeError):
            pass
        try:
            if now - os.path.getmtime(os.path.join(bus_root, "outbox", n + ".jsonl")) <= max_age_s:
                return True, f"bus outbox {n} fresh"
        except OSError:
            pass
    return False, "no running session, heartbeat or bus write"


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def due_rows(flags):
    seen = {}
    try:
        with open(os.path.join(flags, "filing-due.jsonl")) as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict) and isinstance(r.get("id"), str) and file_result.re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", r["id"]):
                    seen.setdefault(r["id"], r)
    except OSError:
        pass
    # filing_watch.sh only scans grants/; DEPRECATED fallback for an on-disk smoke-completed row with no grants/ copy
    for rid, ep in filing.smoke_complete_ids(flags):
        if rid not in seen and not os.path.exists(os.path.join(flags, "grants", rid + ".ended")):
            seen[rid] = {"id": rid, "ended_file": ep, "source": "smoke-complete"}
    return list(seen.values())


def notify(flags, kind, rid, disc, summary, owner, detail, action):
    try:
        import notify as nt  # rowflow/notify.py: idempotent, live-tree-gated bus + mailbox
        nt.emit(flags, kind, rid, disc, summary, "warning" if action else "info", owner=owner or "", detail=detail,
                action=action, meta={})
    except Exception as e:  # noqa: BLE001 - a notification failure never blocks filing
        log(flags, f"WARN notify {kind} {rid}: {type(e).__name__}: {e}")


def run_pass(flags, bus_root, dry_run=False, owner_age_s=1800, min_age_s=1200, now=None, alert_max_age_s=86400):
    now = now or time.time()
    state_path = os.path.join(flags, "filing-autofile.state.json")
    state = load_json(state_path, {})
    queue_path = os.path.join(flags, "filing-owner-less.jsonl")
    queued = {r.get("id") for r in (json.loads(l) for l in open(queue_path) if l.strip())} if os.path.exists(queue_path) else set()
    report = {"filed": [], "failed": [], "queued": [], "owner_live": [], "skipped": [], "alerted": []}
    for row in due_rows(flags):
        rid = row["id"]
        if os.path.exists(os.path.join(flags, "filing-done", rid + ".FILED")):
            continue
        if rid in state or rid in queued:
            # already attempted/queued: the owner still gets its single filing-due alert (dedup is notify.emit's marker)
            continue
        mp, m = filing.load_manifest(flags, rid)
        ep, _rc, _line = filing.load_end(flags, rid)
        if not m or not ep:
            report["skipped"].append(rid); continue  # file_result.py would refuse (exit 2); the alarm owns these
        rule, owner = m.get("decision_rule"), str(m.get("owner") or "")
        # filing-due: ONE alert per row to the owner's inbox/bus (notify.emit dedups on kind|row), only for runs that ended
        # recently enough to still matter and have sat unfiled >= min_age_s; older backlog goes through the janitor sweeps.
        try:
            age = now - os.path.getmtime(ep)
            if not dry_run and min_age_s <= age <= alert_max_age_s and not machine_checkable(rule):
                import notify as nt
                nt.filing_due(flags, rid, owner, _line)
                report["alerted"].append(rid)
        except Exception as e:  # noqa: BLE001 - never blocks filing
            log(flags, f"WARN filing-due {rid}: {type(e).__name__}: {e}")
        if machine_checkable(rule):
            if dry_run:
                report["filed"].append(rid); continue
            r = subprocess.run([sys.executable, os.path.join(HERE, "file_result.py"), rid, "--flags", flags],
                               capture_output=True, text=True, timeout=120)
            out = (r.stdout + r.stderr).strip().replace("\n", " | ")[:600]
            state[rid] = {"at": now_iso(), "rc": r.returncode, "out": out}
            log(flags, f"file_result {rid} rc={r.returncode}: {out}")
            if r.returncode == 0:
                report["filed"].append(rid)
                notify(flags, "auto-filed", rid, "v1", f"{rid} filed by auto_file.py (machine rule {rule!r}): "
                       f"{out[:200]}; review at your next boundary", owner, {"file_result": out}, False)
            else:
                report["failed"].append(rid)
            continue
        live, why = owner_live(owner, flags, bus_root, owner_age_s, now)
        if live:
            report["owner_live"].append(rid); continue
        if now - os.path.getmtime(ep) < min_age_s:
            continue
        rec = {"id": rid, "queued_at": now_iso(), "owner": owner or None, "owner_state": why, "decision_rule": rule,
               "result_path": m.get("result_path"), "end_file": ep, "manifest": mp, "handoff_task": m.get("handoff_task"),
               "file_with": f"python3 scripts/coordination/churn/file_result.py {rid} --verdict-json <verdict.json>"}
        report["queued"].append(rid)
        if not dry_run:
            with open(queue_path, "a") as f:
                f.write(json.dumps(rec, sort_keys=True) + "\n")
            queued.add(rid)
    if not dry_run:
        tmp = state_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(state, f, indent=1, sort_keys=True)
        os.replace(tmp, state_path)
        if report["queued"]:
            ids = sorted(report["queued"])
            log(flags, f"queued {len(ids)} owner-less prose-rule run(s) in {queue_path}: {' '.join(ids)}")
            notify(flags, "filing-owner-less", "", f"{ids[0]}+{len(ids)}",
                   f"{len(ids)} run(s) need an agent verdict and their owners are not live; standing filer: consume "
                   f"{queue_path} (file_result.py <id> --verdict-json V)", "", {"ids": ids}, True)
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--flags", default=DEFAULT_FLAGS)
    ap.add_argument("--bus-root", default=DEFAULT_BUS)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--owner-age-s", type=int, default=1800, help="heartbeat/outbox freshness that counts as a live owner")
    ap.add_argument("--min-age-s", type=int, default=1200, help="a prose-rule run is queued only this long after its end")
    a = ap.parse_args(argv)
    rep = run_pass(a.flags, a.bus_root, a.dry_run, a.owner_age_s, a.min_age_s)
    print(json.dumps({k: (v if a.dry_run else len(v)) for k, v in rep.items()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
