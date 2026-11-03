#!/usr/bin/env python3
"""run_direct - ONE command to run a published row on the hardware NOW (2026-11-03 session review item 1).

    run_direct.sh <ready.json | row-id> [--regions R] [--gpu-quiet none|shared|exclusive] [--timeout-s 600]
                                        [--window-s N] [--no-wait] [--wait-s 30]
    run_direct.sh stop   <row-id>     # touch the row's STOP file: the job stops between items (never a signal)
    run_direct.sh status <row-id>     # = rowflow.py status <row-id> (fixed short form, measured util)

What it does, deterministically and idempotently:
  1. resolves the row (ready/<id>.json, schema epyc.row.v3) and refuses with ONE line "REFUSED: <cause>; fix: <command>"
     when the id is terminal, STOP is present, the keeper already granted it, or it is already running directly;
  2. claims EXACTLY the cpus the row's regions name (`region-lock run --cpu-list ... --tag filler-<id>`), with a finite
     lock timeout; gpu-quiet is opt-in: none for cpu rows, shared for gpu/cpu+gpu rows unless --gpu-quiet says otherwise;
  3. runs the row's job command (the engine's --cmd) in its workdir with the engine's FILLER_* contract (FILLER_ID,
     FILLER_STOPFILE, FILLER_DEADLINE, FILLER_END, FILLER_END_ISO, FILLER_CPUS, FILLER_THREADS, FILLER_NEEDGPU, ...), detached,
     output to dryrun/<id>/direct.out, and writes grants/<id>.ended (rc=N reason=direct-run) when it exits;
  4. holds the row from the keeper: dryrun/<id>/DIRECT.json (live supervisor pid) makes rowflow status() report `running`,
     so the allocator never grants it while the direct run lives, and region-lock's filler-<id> tag attributes the busy
     regions to the row; the record carries CLAUDE_SESSION_ID when set, so the question-discipline hook knows which
     session owns a live launch;
  5. waits for the lock + 30 s, then prints the MEASURED utilisation of the claimed cpus and the GPU in a fixed 6-line
     summary (a claim below hostutil.IDLE_PCT is flagged). Long output stays on disk behind the printed logs path.

Nothing here is a judgment call: the regions come from the row, the gpu-quiet mode from the class, the successor id
from the suffix rule, the stop from the STOP file. Exit codes: 0 started (or already running), 2 refused, 75 the lane
did not free within --timeout-s.
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import hostutil  # noqa: E402
import rowflow as rf  # noqa: E402

GPU_HOST_THREADS = "184-191"
DEFAULT_TIMEOUT_S = 600
DEFAULT_WAIT_S = 30


def direct_path(flags, rid):
    return os.path.join(rf.dry_dir(flags, rid), "DIRECT.json")


def successor_id(rid):
    """DETERMINISTIC next id: '...-r3' -> '...-r4'; anything else -> '<id>-r2'."""
    stem, sep, tail = rid.rpartition("-r")
    if sep and tail.isdigit():
        return f"{stem}-r{int(tail) + 1}"
    return rid + "-r2"


def parse_regions(regions, cls):
    """(cpus, threads, needgpu) exactly as filler_run15.sh parse_regions derives them, or None when unusable."""
    qs, lst, gpu = [], [], False
    for tok in str(regions).replace(";", ",").split(","):
        tok = tok.strip()
        if tok == "mi210_0":
            gpu = True
        elif len(tok) == 2 and tok[0] == "q" and tok[1] in "0123":
            qs.append(int(tok[1]))
        elif tok and tok[0].isdigit():
            lst.append(tok)
    if cls == "cpu" and gpu or cls in ("gpu", "cpu+gpu") and not gpu:
        return None
    if cls == "gpu":
        cpus = ",".join(lst) if lst else GPU_HOST_THREADS
    elif lst:
        cpus = ",".join(lst)
    elif qs:
        cpus = ",".join(f"{n * 24}-{n * 24 + 23},{n * 24 + 96}-{n * 24 + 111}" for n in qs)
    else:
        return None
    ids = hostutil.parse_cpus(cpus)
    if not ids or any(c < 0 or c > 191 for c in ids):
        return None
    threads = len(set(ids)) if cls == "gpu" else len({c for c in ids if c < 96})
    return cpus, threads, gpu


def refuse(cause, fix):
    print(f"REFUSED: {cause}; fix: {fix}")
    return 2


def resolve(flags, arg):
    """ready/<id>.json path or row id -> (rid, row dict) or (rid, None)."""
    rid = os.path.basename(arg)[:-5] if arg.endswith(".json") else arg
    d = rf.load_json(rf.ready_path(flags, rid))
    return rid, (d if d and d.get("schema") == rf.SCHEMA else None)


def live_direct(flags, rid):
    """The DIRECT.json record when its supervisor is alive and the id is not terminal, else None."""
    rec = rf.load_json(direct_path(flags, rid))
    if not rec or not rf.alive(rec.get("pid")):
        return None
    if os.path.exists(os.path.join(flags, "grants", rid + ".ended")):
        return None
    return rec


def build(flags, rid, d, regions, gpu_quiet, window_s, timeout_s, rl=None):
    """PURE given the row: the region-lock argv, the job env and the paths. Refuses via ValueError(cause, fix)."""
    o = rf.parse_launcher(d["launcher"]["path"])
    cls = o["class"]
    pr = parse_regions(regions, cls)
    if pr is None:
        raise ValueError(f"regions {regions!r} unusable for class {cls}", f"run_direct.sh {rid} --regions <q0..q3 | 0-95 | mi210_0,88-91>")
    cpus, threads, needgpu = pr
    mode = gpu_quiet or ("none" if cls == "cpu" else "shared")
    if mode not in ("none", "shared", "exclusive"):
        raise ValueError(f"--gpu-quiet {mode!r} unknown", "use none, shared or exclusive")
    dd = rf.dry_dir(flags, rid)
    state = os.path.join(dd, "state")
    end = int(time.time()) + int(window_s)
    env = {"FILLER_ID": rid, "FILLER_STOPFILE": o["stop"], "FILLER_END": str(end), "FILLER_DEADLINE": str(end - 90),
           "FILLER_END_ISO": dt.datetime.fromtimestamp(end, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "FILLER_CPUS": cpus, "FILLER_THREADS": str(threads), "FILLER_NEEDGPU": "1" if needgpu else "0",
           "FILLER_PORTS": ",".join(str(p) for p in (d.get("ports") or [])), "FILLER_PIDFILE": os.path.join(state, rid + ".pids"),
           "FILLER_LIB": os.path.join(_HERE, "filler_lib.sh"),
           "FILLER_FLAGS_DIR": flags, "FILLER_GRANTS_DIR": os.path.join(flags, "grants"), "FILLER_OWNER": str(d.get("owner", "")),
           "FILLER_EST_WALL_S": str(d.get("estimate_s", "")), "FILLER_DIRECT": "1", "WS58_REGIONS": cpus}
    argv = [rl or rf.RL, "run", "--cpu-list", cpus, "--role", "bench", "--timeout-s", str(int(timeout_s)), "--tag", f"filler-{rid}"]
    if mode != "none":
        argv += ["--gpu-quiet", mode]
    started = os.path.join(dd, "direct.started")
    # the marker proves the LOCK was acquired and the job began; everything after `exec` is the row's own command
    argv += ["--", "bash", "-c", f"date -u +%FT%TZ > {json.dumps(started)}; exec bash -c {json.dumps(o['cmd'])}"]
    return {"id": rid, "argv": argv, "env": env, "cwd": o["workdir"] or "/workspace", "regions": regions, "cpus": cpus,
            "gpu_quiet": mode, "class": cls, "window_s": int(window_s), "end": end, "out": os.path.join(dd, "direct.out"),
            "started_marker": started, "state": state, "stop_file": o["stop"], "timeout_s": int(timeout_s)}


def supervise(spec_path):
    """Detached: run the lock+job, then write grants/<id>.ended (rc=N reason=direct-run). Lock timeout (75) writes no
    terminal record (the row stays grantable) and is recorded in DIRECT.json as result=lock-timeout."""
    spec = rf.load_json(spec_path)
    flags, rid = spec["flags"], spec["id"]
    os.makedirs(spec["state"], exist_ok=True)
    env = dict(os.environ, **spec["env"])
    with open(spec["out"], "a") as out:
        out.write(f"==== direct run {rf.now_iso()} regions={spec['regions']} cpus={spec['cpus']} gpu-quiet={spec['gpu_quiet']}\n")
        out.flush()
        p = subprocess.Popen(spec["argv"], cwd=spec["cwd"], env=env, stdout=out, stderr=subprocess.STDOUT)
        rec = dict(spec, pid=os.getpid(), child_pid=p.pid, child_birth=(rf._proc_stat(p.pid) or (0, 0, ""))[2])
        rf.atomic_json(spec_path, rec)
        rc = p.wait()
        out.write(f"==== direct run exit rc={rc} {rf.now_iso()}\n")
    if rc == 75 and not os.path.exists(spec["started_marker"]):
        rf.atomic_json(spec_path, dict(rec, result="lock-timeout", ended=rf.now_iso()))
        return 75
    ended = os.path.join(flags, "grants", rid + ".ended")
    if not os.path.exists(ended):
        with open(ended + ".tmp", "w") as f:
            f.write(f"rc={rc} time={rf.now_iso()} reason=direct-run\njob_id={rid}\nowner={spec['env'].get('FILLER_OWNER', '')}\n"
                    f"step=job-run\nestimated_wall_s={spec['env'].get('FILLER_EST_WALL_S', '')}\nstarted={spec.get('started_at', '')}\nregions={spec['regions']}\n")
        os.replace(ended + ".tmp", ended)
    rf.atomic_json(spec_path, dict(rec, result=f"rc={rc}", ended=rf.now_iso()))
    return rc


def summary(rid, rec, util, waited_s, started_at):
    cl = (util or {}).get("claim")
    L = [f"id:      {rid}",
         f"started: {started_at or 'not yet (waiting for the lock)'} pid={rec.get('pid')} regions={rec['regions']} cpus={rec['cpus']} "
         f"gpu-quiet={rec['gpu_quiet']} end={rec['env']['FILLER_END_ISO']}",
         ("util:    " + hostutil.line(util, prefix="").strip() + f"  (measured {waited_s} s after start)") if util else "util:    not measured (job not started yet)",
         f"logs:    {rec['out']}",
         f"status:  python3 {os.path.join(_HERE, 'rowflow.py')} status {rid}",
         f"stop:    {os.path.join(_HERE, 'run_direct.sh')} stop {rid}"]
    if util and cl is not None and cl < hostutil.IDLE_PCT:
        L.insert(3, f"WARNING: claimed cpus measure {cl:.0f}% busy {waited_s} s after start (loading, or the job is not on its claim); check logs")
    return "\n".join(L)


def launch(flags, rid, d, a, sleep=time.sleep, measure=None, spawn=None):
    """Refusals first (one line each), then spawn the supervisor, hold the row, wait for the lock + wait_s, measure, print."""
    G = os.path.join(flags, "grants")
    if os.path.exists(os.path.join(G, rid + ".ended")) or os.path.exists(os.path.join(G, rid + ".complete")):
        return refuse(f"{rid} is terminal (grants/{rid}.ended|.complete)", f"publish it under the successor id {successor_id(rid)}")
    live = live_direct(flags, rid)
    if live:
        print(f"ALREADY RUNNING: {rid} direct run pid={live['pid']} since {live.get('started_at')}; logs {live['out']}")
        return 0
    if os.path.exists(os.path.join(G, rid + ".grant")):
        return refuse(f"the keeper already granted {rid} (grants/{rid}.grant)", f"python3 {os.path.join(_HERE, 'rowflow.py')} status {rid}")
    try:
        rec = build(flags, rid, d, a.regions or d["regions"], a.gpu_quiet, a.window_s or d["window_s"], a.timeout_s)
    except rf.Refused as e:
        return refuse(f"launcher unusable: {e}", f"fix {d['launcher']['path']} then republish: python3 {os.path.join(_HERE, 'publish_row.py')} <spec.json>")
    except ValueError as e:
        return refuse(*e.args)
    if os.path.exists(rec["stop_file"]):
        return refuse(f"STOP file present ({rec['stop_file']})", f"rm {rec['stop_file']}")
    os.makedirs(rec["state"], exist_ok=True)
    for stale in (rec["started_marker"],):
        try:
            os.remove(stale)
        except OSError:
            pass
    rec.update(flags=flags, started_at=rf.now_iso(), pid=None, session_id=os.environ.get("CLAUDE_SESSION_ID") or None)
    rf.atomic_json(direct_path(flags, rid), rec)
    spawn = spawn or (lambda spec: subprocess.Popen([sys.executable, "-I", os.path.abspath(__file__), "_supervise", spec],
                                                    start_new_session=True, stdin=subprocess.DEVNULL,
                                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).pid)
    sup = spawn(direct_path(flags, rid))
    rec["pid"] = sup
    rf.atomic_json(direct_path(flags, rid), rec)   # the supervisor overwrites it with its own pid once it has forked the lock
    if a.no_wait:
        print(summary(rid, rec, None, 0, None))
        return 0
    deadline = time.time() + rec["timeout_s"] + 5
    started = None
    while time.time() < deadline:
        if os.path.exists(rec["started_marker"]):
            started = rf.head1(rec["started_marker"]) or rf.now_iso()
            break
        cur = rf.load_json(direct_path(flags, rid)) or {}
        if cur.get("result") == "lock-timeout":
            print(f"REFUSED: lane busy: the lock did not free within {rec['timeout_s']} s (holder lines in {rec['out']}); "
                  f"fix: run_direct.sh {rid} --regions <free regions> or wait and re-run")
            return 75
        if cur.get("ended"):
            print(f"ENDED before start: {cur.get('result')}; logs {rec['out']}")
            return 2
        sleep(1)
    if not started:
        print(f"REFUSED: lane busy: no start within {rec['timeout_s']} s; fix: run_direct.sh {rid} --regions <free regions> or wait and re-run")
        return 75
    sleep(a.wait_s)
    util = (measure or hostutil.measure)(1.0, {"claim": hostutil.parse_cpus(rec["cpus"])})
    print(summary(rid, rf.load_json(direct_path(flags, rid)) or rec, util, a.wait_s, started))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="run a published row on the hardware now (one command; see module doc)")
    ap.add_argument("target", help="ready/<id>.json or the row id; or the word stop / status followed by the id")
    ap.add_argument("rid", nargs="?", help="row id for stop/status")
    ap.add_argument("--flags", default=rf.FLAGS)
    ap.add_argument("--regions", help="override the row's regions (q0..q3 | 0-95 | mi210_0,88-91)")
    ap.add_argument("--gpu-quiet", choices=["none", "shared", "exclusive"], help="opt-in; default none (cpu) / shared (gpu rows)")
    ap.add_argument("--timeout-s", type=int, default=DEFAULT_TIMEOUT_S, help="lock wait budget (default 600; never forever)")
    ap.add_argument("--window-s", type=int, help="override the row's window_s (FILLER_DEADLINE)")
    ap.add_argument("--wait-s", type=int, default=DEFAULT_WAIT_S, help="seconds after start before the utilisation proof")
    ap.add_argument("--no-wait", action="store_true", help="return right after spawning (no utilisation proof)")
    a = ap.parse_args(argv)
    if a.target == "_supervise":
        return supervise(a.rid)
    if a.target in ("stop", "status"):
        if not a.rid:
            return refuse(f"{a.target} needs a row id", f"run_direct.sh {a.target} <row-id>")
        rid, d = resolve(a.flags, a.rid)
        if not d:
            return refuse(f"{rid} is not a published row", f"python3 {os.path.join(_HERE, 'publish_row.py')} <spec.json>")
        if a.target == "status":
            print(rf.status_text(rf.status(a.flags, rid, util=rf.measure_util())))
            return 0
        sf = str(d.get("stop_file") or "")
        if not sf:
            return refuse(f"{rid} declares no stop_file", "republish the row with an engine --stop path")
        os.makedirs(os.path.dirname(sf), exist_ok=True)
        open(sf, "a").close()
        live = live_direct(a.flags, rid)
        print(f"STOP written: {sf}; the job stops between items" + (f" (direct run pid={live['pid']}, logs {live['out']})" if live else "")
              + f"; it stays held until: rm {sf}")
        return 0
    rid, d = resolve(a.flags, a.target)
    if not d:
        return refuse(f"{rid} is not a published row (no ready/{rid}.json)", f"python3 {os.path.join(_HERE, 'publish_row.py')} <spec.json>")
    return launch(a.flags, rid, d, a)


if __name__ == "__main__":
    sys.exit(main())
