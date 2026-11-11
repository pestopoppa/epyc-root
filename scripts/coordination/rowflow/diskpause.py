#!/usr/bin/env python3
"""diskpause - the host disk floor as PAUSE WITH HYSTERESIS, not a kill (operator 2026-11-07, "Pause with hysteresis").

Before: any launcher whose free-disk read fell under 150 GiB killed its row (4 INF-22 rows, 12:17Z: ids burned, terminal).
Now (this module + filler_run15.sh + rowflow.allocate):

  free <  FLOOR (150)      stop admitting (no new grant, no new smoke, a granted-but-unstarted row waits) and SIGSTOP the
                           largest-writing running rows, attributed by scratch_root growth (du between two samples) until
                           they account for >= COVER (0.9) of the observed growth. A stopped row keeps its grant and its id
                           (non-terminal): nothing to republish.
  free >= RESUME (180)     SIGCONT every row this module stopped; admissions resume.
  FLOOR <= free < RESUME   hysteresis: the state does not change (paused stays paused; running stays running).
  free <  EMERGENCY (50)   the only hard kill; done by the launcher (filler_run15.sh), never by this module.

Signals go ONLY to a row's captured group: <state>/<id>.inner.pgid ("pgid birth", written by the launcher's inner engine) and
only while the leader's start time still equals the captured birth (a reused pid is never signalled); descendants that
left the group via setsid are reached through the SAME captured id (session id == pgid). Never a name match.
Log lines on STATE TRANSITIONS only (pause, each row stopped, resume, no-attributable-writer once); a steady state is silent.

Configuration (env; defaults in parentheses): FILLER_DISK_FLOOR_GIB (150), FILLER_DISK_RESUME_GIB (max(180, floor+30)),
FILLER_DISK_EMERGENCY_GIB (50, never above the floor), FILLER_DISK_PAUSE_COVER (0.9), FILLER_DISK_PAUSE_SAMPLE_S (5),
FILLER_DISK_PAUSE_MIN_S (10: minimum seconds between evaluations), FILLER_DISK_PATH (/mnt/raid0).
State: <flags>/disk-pause/{state.json,events.log,PAUSED (marker while paused),lock}.

HOLD-ADMISSIONS (operator 2026-11-07): a file <flags>/HOLD-ADMISSIONS ("owner=..", "reason=.." lines) stops NEW grants and
admissions; running rows continue. admission_gate() folds it with the disk pause into one reason string.

CLI:  diskpause.py tick [--flags DIR]  |  status [--flags DIR]
"""
import copy
import fcntl
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
FLAGS = os.environ.get("ROWFLOW_FLAGS", "/mnt/raid0/llm/" + "tmp/compute-flags")
HOLD_FILE = "HOLD-ADMISSIONS"
GIB = 1 << 30


# ------------------------------------------------------------------ configuration
def config(env=None):
    e = os.environ if env is None else env
    floor = float(e.get("FILLER_DISK_FLOOR_GIB", 150))
    return {
        "floor": floor,
        "resume": float(e.get("FILLER_DISK_RESUME_GIB", max(180.0, floor + 30.0))),
        "emergency": min(float(e.get("FILLER_DISK_EMERGENCY_GIB", 50)), floor),
        "cover": float(e.get("FILLER_DISK_PAUSE_COVER", 0.9)),
        "min_growth": float(e.get("FILLER_DISK_PAUSE_MIN_GROWTH_MIB", 1.0)) * (1 << 20),   # bytes/s; below this stopping frees nothing
        "sample_s": float(e.get("FILLER_DISK_PAUSE_SAMPLE_S", 5)),
        "min_s": float(e.get("FILLER_DISK_PAUSE_MIN_S", 10)),
        "path": e.get("FILLER_DISK_PATH", "/mnt/raid0"),
    }


def next_paused(paused, free, floor, resume):
    """The hysteresis: below the floor -> paused; at/above resume -> running; in between -> unchanged."""
    if free < floor:
        return True
    if free >= resume:
        return False
    return paused


# ------------------------------------------------------------------ pure decision
def new_state():
    return {"paused": False, "since": None, "paused_ids": {}, "samples": {}, "last_eval": 0.0, "noattr": False}


def decide(state, free, rows, cfg, now):
    """PURE. rows: [{id, pgid, birth, alive, size}] (size = scratch_root bytes or None). Returns (state, actions, events);
    actions = [("stop"|"cont", row)], events = transition lines. No I/O, no clock."""
    st = copy.deepcopy(state)
    actions, events = [], []
    was = bool(st["paused"])
    paused = next_paused(was, free, cfg["floor"], cfg["resume"])
    growth = {}
    for r in rows:
        prev = st["samples"].get(r["id"])
        if prev and r.get("size") is not None and now > prev["t"]:
            growth[r["id"]] = (r["size"] - prev["size"]) / (now - prev["t"])
    st["samples"] = {r["id"]: {"t": now, "size": r["size"]} for r in rows if r.get("size") is not None}
    live = {r["id"] for r in rows if r.get("alive")}
    st["paused_ids"] = {i: v for i, v in st["paused_ids"].items() if i in live}   # a row that ended is no longer ours
    if paused and not was:
        st["since"] = now
        events.append(f"DISK-PAUSE free={free:.0f}GiB < floor {cfg['floor']:.0f}GiB: admissions stopped; stopping the largest writers "
                      f"(resume at {cfg['resume']:.0f}GiB, kill only below {cfg['emergency']:.0f}GiB)")
    if paused and free < cfg["floor"]:
        cand = [r for r in rows if r.get("alive") and r.get("pgid") and r["id"] not in st["paused_ids"]]
        ranked = sorted(((growth.get(r["id"], 0.0), r) for r in cand), key=lambda x: -x[0])
        mg = max(cfg.get("min_growth", 1 << 20), 1e-9)
        ranked = [(g, r) for g, r in ranked if g >= mg]   # a ~0-growth row is never stopped: it frees nothing
        total = sum(g for g, _ in ranked)
        acc = 0.0
        for g, r in ranked:
            actions.append(("stop", r))
            st["paused_ids"][r["id"]] = {"pgid": r["pgid"], "birth": r["birth"], "growth_bps": g, "at": now}
            events.append(f"DISK-PAUSE-STOP {r['id']} (scratch growth {g / (1 << 20):.1f} MiB/s): SIGSTOP group {r['pgid']}; id stays non-terminal")
            acc += g
            if acc >= cfg["cover"] * total:
                break
        if cand and not ranked and not st["noattr"]:
            events.append("DISK-PAUSE-NO-WRITER no running row's scratch_root is growing (sampled); admissions stay stopped, nothing stopped")
        st["noattr"] = bool(cand) and not ranked
        # release rows that are not (or no longer proven to be) the writer: recorded growth under the threshold (nothing
        # to free), or NO-WRITER concluded (no running row is growing) -> SIGCONT, never leave them frozen
        mg = max(cfg.get("min_growth", 1 << 20), 1e-9)
        rel = [i for i, v in st["paused_ids"].items() if float(v.get("growth_bps") or 0) < mg or st["noattr"]]
        for i in sorted(rel):
            v = st["paused_ids"].pop(i)
            actions.append(("cont", {"id": i, "pgid": v["pgid"], "birth": v["birth"]}))
            events.append(f"DISK-PAUSE-RELEASE {i}: SIGCONT group {v['pgid']} (" +
                          ("no writer attributable" if st["noattr"] else "not the writer: recorded growth under threshold") + ")")
    if not paused and (was or st["paused_ids"]):   # pause cleared (this tick, or earlier with rows still recorded): resume every stopped group
        for i, v in sorted(st["paused_ids"].items()):
            actions.append(("cont", {"id": i, "pgid": v["pgid"], "birth": v["birth"]}))
        events.append(f"DISK-RESUME free={free:.0f}GiB >= {cfg['resume']:.0f}GiB: SIGCONT {len(st['paused_ids'])} row(s) "
                      f"({','.join(sorted(st['paused_ids'])) or '-'}); admissions resumed")
        st["paused_ids"], st["since"], st["noattr"] = {}, None, False
    st["paused"] = paused
    return st, actions, events


# ------------------------------------------------------------------ process identity (never a name match)
def proc_birth(pid):
    try:
        with open(f"/proc/{int(pid)}/stat") as f:
            return f.read().rsplit(") ", 1)[1].split()[19]
    except (OSError, IndexError, ValueError):
        return None


def group_alive(pgid, birth):
    return bool(birth) and proc_birth(pgid) == str(birth)


def session_pids(pgid):
    """Pids of the captured id's session whose own group differs (setsid grandchildren); ps columns only."""
    try:
        out = subprocess.run(["ps", "-eo", "pid=,pgid=,sid=,stat="], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    pids = []
    for ln in out.splitlines():
        p = ln.split()
        if len(p) == 4 and p[2] == str(pgid) and p[1] != str(pgid) and not p[3].startswith("Z"):
            pids.append(int(p[0]))
    return pids


def signal_row(row, sig):
    """Signal the captured group (+ its session members) only if the leader's birth still matches. True when signalled."""
    if not group_alive(row["pgid"], row["birth"]):
        return False
    try:
        for p in session_pids(row["pgid"]):
            try:
                os.kill(p, sig)
            except OSError:
                pass
        os.killpg(int(row["pgid"]), sig)
        return True
    except OSError:
        return False


# ------------------------------------------------------------------ I/O
def _read_json(p):
    try:
        with open(p) as f:
            v = json.load(f)
        return v if isinstance(v, dict) else None
    except (OSError, ValueError):
        return None


def _atomic_json(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".part", "w") as f:
        json.dump(obj, f, indent=1, sort_keys=True)
    os.replace(p + ".part", p)


def dp_dir(flags):
    return os.path.join(flags, "disk-pause")


def is_paused(flags):
    return os.path.exists(os.path.join(dp_dir(flags), "PAUSED"))


def stopped_ids(flags):
    """Row ids this guard itself has SIGSTOPped and not yet resumed (stopped.json); rowflow labels them DISK-PAUSED (self)."""
    return set(_read_json(os.path.join(dp_dir(flags), "stopped.json")) or {})


def state_dir_default():
    return os.environ.get("FILLER_STATE_DIR") or os.path.join(_HERE, "state")


def running_rows(flags, state_dir=None):
    """Open grants (grants/<id>.grant without .ended) with a captured group; size is filled by measure()."""
    state_dir = state_dir or state_dir_default()
    rows = []
    gdir = os.path.join(flags, "grants")
    try:
        names = sorted(os.listdir(gdir))
    except OSError:
        return rows
    for n in names:
        if not n.endswith(".grant"):
            continue
        rid = n[:-6]
        if os.path.exists(os.path.join(gdir, rid + ".ended")):
            continue
        pgid = birth = None
        try:
            with open(os.path.join(state_dir, rid + ".inner.pgid")) as f:
                parts = f.read().split()
            pgid, birth = parts[0], parts[1]
        except (OSError, IndexError):
            pass
        root = (_read_json(os.path.join(flags, "ready", rid + ".json")) or {}).get("scratch_root")
        rows.append({"id": rid, "pgid": pgid, "birth": birth, "alive": bool(pgid) and group_alive(pgid, birth), "root": root, "size": None})
    return rows


def du_bytes(path, timeout=40):
    try:
        out = subprocess.run(["du", "-sb", "--", path], capture_output=True, text=True, timeout=timeout).stdout
        return int(out.split()[0])
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return None


def measure(rows, timeout=40):
    """Fill row['size'] for every alive row with a scratch_root, in parallel (du of a large root is slow)."""
    def one(r):
        r["size"] = du_bytes(r["root"], timeout) if r.get("root") and os.path.isdir(r["root"]) else None
    ts = [threading.Thread(target=one, args=(r,)) for r in rows if r.get("alive")]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return rows


def _log_event(flags, line):
    os.makedirs(dp_dir(flags), exist_ok=True)
    with open(os.path.join(dp_dir(flags), "events.log"), "a") as f:
        f.write(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) + " " + line + "\n")


def tick(flags=None, log=print, state_dir=None, free_gib=None, cfg=None, now=None, sleep=time.sleep, measure_fn=None, rows_fn=None):
    """One evaluation, serialized by a non-blocking flock (a second caller returns []). Returns the transition lines.
    Fast path: not paused and free >= floor -> no du, no state write beyond last_eval (the poller calls this only when
    free < floor or PAUSED exists, the keeper every tick)."""
    flags = flags or FLAGS
    cfg = cfg or config()
    now = time.time() if now is None else now
    os.makedirs(dp_dir(flags), exist_ok=True)
    lk = open(os.path.join(dp_dir(flags), "lock"), "a")
    try:
        try:
            fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return []
        sp = os.path.join(dp_dir(flags), "state.json")
        st = _read_json(sp) or new_state()
        for k, v in new_state().items():
            st.setdefault(k, v)
        free = free_gib if free_gib is not None else shutil.disk_usage(cfg["path"]).free / GIB
        want_paused = next_paused(bool(st["paused"]), free, cfg["floor"], cfg["resume"])
        if not want_paused and not st["paused"] and not st["paused_ids"]:
            return []
        if now - float(st.get("last_eval") or 0) < cfg["min_s"] and want_paused == bool(st["paused"]):
            return []
        rows = (rows_fn or running_rows)(flags, state_dir)
        mf = measure_fn or measure
        sampling = want_paused and free < cfg["floor"]
        if sampling:
            mf(rows)
            hist = [st["samples"].get(r["id"]) for r in rows if r.get("alive") and r.get("size") is not None]
            if not hist or any(h is None or now - h["t"] < 2 for h in hist):
                # no history old enough (the keeper's every-tick samples make this rare): baseline now, re-measure sample_s later
                for r in rows:
                    r["size0"] = r.get("size")
                sleep(cfg["sample_s"])
                now = now + cfg["sample_s"]
                mf(rows)
        elif want_paused != bool(st["paused"]) or st["paused_ids"]:
            mf(rows)   # resume path: sizes only refresh the sample baseline
        st2, actions, events = decide_with_baseline(st, free, rows, cfg, now, sampling)
        for kind, r in actions:
            ok = signal_row(r, signal.SIGSTOP if kind == "stop" else signal.SIGCONT)
            if not ok:
                events.append(f"DISK-PAUSE-{kind.upper()}-SKIP {r['id']}: captured group {r['pgid']} gone or birth changed (not signalled)")
                if kind == "stop":
                    st2["paused_ids"].pop(r["id"], None)
        st2["last_eval"] = now
        _atomic_json(sp, st2)
        _atomic_json(os.path.join(dp_dir(flags), "stopped.json"), st2["paused_ids"])
        marker = os.path.join(dp_dir(flags), "PAUSED")
        if st2["paused"]:
            open(marker, "a").close()
        elif os.path.exists(marker):
            os.remove(marker)
        for ln in events:
            log(ln)
            _log_event(flags, ln)
        return events
    finally:
        lk.close()


def decide_with_baseline(st, free, rows, cfg, now, sampling):
    """decide(), except that when the stored samples are absent/stale the keeper-side double sample is used: tick() has
    already re-measured rows; seed the baseline from the pre-sleep measurement kept in row['size0'] when present."""
    for r in rows:
        if "size0" in r and r.get("size") is not None:
            st = copy.deepcopy(st)
            st["samples"][r["id"]] = {"t": now - cfg["sample_s"], "size": r["size0"]}
    return decide(st, free, rows, cfg, now)


def admission_gate(flags, log=print, persist=True, log_transition=None):
    """The ONE reason string for 'no new grants/admissions' (HOLD-ADMISSIONS file and/or disk pause), else None.
    Logs once per change of the reason set (never per tick). Running rows are never touched by this gate."""
    reasons = {}
    hp = os.path.join(flags, HOLD_FILE)
    if os.path.exists(hp):
        kv = {}
        try:
            for ln in open(hp).read().splitlines():
                if "=" in ln:
                    k, v = ln.split("=", 1)
                    kv[k.strip()] = v.strip()
        except OSError:
            pass
        reasons["hold"] = f"HOLD-ADMISSIONS owner={kv.get('owner', '?')} reason={kv.get('reason', '?')}: no new grants or admissions; running rows continue"
    if is_paused(flags):
        reasons["disk"] = "DISK-PAUSE: free disk under the floor; no new grants or admissions until it is back above the resume level"
    if log_transition:
        log_transition(flags, "admission-gate", {k: v for k, v in reasons.items()}, log, persist=persist)
    return "; ".join(reasons.values()) if reasons else None


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    flags = FLAGS
    if "--flags" in a:
        i = a.index("--flags")
        flags = a[i + 1]
        del a[i:i + 2]
    cmd = a[0] if a else "status"
    if cmd == "tick":
        tick(flags)
        return 0
    if cmd == "status":
        print(json.dumps({"paused": is_paused(flags), "state": _read_json(os.path.join(dp_dir(flags), "state.json")), "config": config()}, indent=1, sort_keys=True))
        return 0
    print(__doc__)
    return 64


if __name__ == "__main__":
    sys.exit(main())
