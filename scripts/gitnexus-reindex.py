#!/usr/bin/python3
"""GitNexus re-index as a queued rowflow row, plus the staleness trigger.

Operator 2026-11-20: re-indexing is a structured trade-off queued like any keeper task, not a launcher that grabs
regions itself. `trigger`/`publish` PUBLISH (scripts/coordination/rowflow/publish_row.py) two sibling rows for one
commit and let the keeper's packer choose by what is free:
  host  regions 0-95 (whole host; the keeper never grants it beside a live GPU grant), full workers, short estimate
  q3    regions 72-87 pocket (claim 72-75, `--workers 1`), longer estimate; 88-95/184-191 are MI210 host threads
Both carry `--complete-cmd` "index is fresh", so whichever runs first turns its sibling into a no-op; the analyze
writer lock (rc 75) also forbids two at once. Never preempts or waits on running rows; the claim is the engine's.
Estimates = median measured wall of that option * 1.25 (history.jsonl), seeded from proxies (epyc-root whole-host
96 s; llama.cpp 1-worker ~35 min vs ~29 min whole host) and floored at rowflow's 300 s MIN_ESTIMATE_S.
Every run (`exec`, run inside the grant) appends wall time, workers, threads, region, node count to
state.json (`last_run`) and history.jsonl, so 1-worker vs whole-host can be measured.

Subcommands
  check                              print the trigger decision, change nothing
  trigger  [--batch-id ID] [--min-interval-h N] [--handoff-task F:TASK] [--rank R] [--dry-run]
                                     if stale, nothing outstanding, batch not yet requested and last request older
                                     than N hours: publish the two rows
  publish                            same, but skip the staleness/interval/batch gates (operator-forced)
  exec     --option host|q3 ...      the row's job body (inside a grant)
  fresh                              exit 0 when the index is up-to-date (the rows' --complete-cmd)
  estimates                          print the current per-option estimates
Exit: trigger/check 0 always except usage (64).
"""
import argparse
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).absolute().parent
REPO_ROOT = Path(os.environ.get("GITNEXUS_REINDEX_REPO", "/workspace"))
STATE_DIR = Path(os.environ.get("GITNEXUS_REINDEX_STATE_DIR", "/mnt/raid0/llm/tmp/gitnexus-reindex"))
POCKET_CORES = range(72, 88)          # q3 cores that do not own the MI210 (siblings +96)
DEFAULT_CPUS = "72-75"                # 4 cores; `--workers 1` needs two threads
ENGINE = os.environ.get("GITNEXUS_ROWFLOW_ENGINE", "/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh")
PUBLISH_ROW = os.environ.get("GITNEXUS_PUBLISH_ROW", str(HERE / "coordination" / "rowflow" / "publish_row.py"))
DEFAULT_HANDOFF_TASK = os.environ.get("GITNEXUS_HANDOFF_TASK", "engineering-hygiene-backlog.md:GNX-REINDEX")
DEFAULT_RANK = 900                    # housekeeping: low rank
MARGIN = 1.25
MIN_ESTIMATE_S = 300                  # rowflow publish floor
SEED_WALL_S = {"host": 96.0, "q3": round(96.0 * 35 / 29)}   # proxies: epyc-root whole host; 1-worker/whole-host = 35/29
HISTORY_KEEP = 5
DEFAULT_INTERVAL_H = 6.0
REFUSAL_RETRY_S = 900                 # an admission refusal (64/75) does not burn the full interval
REFUSED_RC = {64, 75}


class Usage(Exception):
    pass


def parse_cpus(text):
    cpus = set()
    for tok in text.split(","):
        a, sep, b = tok.strip().partition("-")
        if not a.isdigit() or (sep and not b.isdigit()):
            raise Usage(f"malformed cpu list {text!r}")
        lo, hi = int(a), int(b) if sep else int(a)
        if hi < lo:
            raise Usage(f"malformed cpu list {text!r}")
        cpus.update(range(lo, hi + 1))
    return cpus


def validate_pocket(text):
    """Every cpu must be a q3 non-GPU core (72-87) or its SMT sibling (168-183)."""
    cpus = parse_cpus(text)
    allowed = set(POCKET_CORES) | {c + 96 for c in POCKET_CORES}
    bad = sorted(cpus - allowed)
    if bad or not cpus:
        raise Usage(f"cpus {bad or text} outside the q3 non-GPU pocket 72-87/168-183 "
                    "(88-95/184-191 are MI210 host threads)")
    return text


OPTIONS = ("host", "q3")


def option_region(option, cpus=DEFAULT_CPUS):
    """(declared regions, engine --claim-cpus) of one option."""
    if option == "host":
        return "0-95", "0-95"
    validate_pocket(cpus)
    return "72-87", cpus


def analyze_argv(option):
    base = ["/bin/bash", str(HERE / "gitnexus-analyze.sh")]
    return base + (["--workers", "1"] if option == "q3" else [])


def run_env(option, base=None):
    env = dict(base if base is not None else os.environ)
    env["ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT"] = "1"
    if option == "q3":
        env["GITNEXUS_WORKER_POOL_SIZE"] = "1"
    else:
        env.pop("GITNEXUS_WORKER_POOL_SIZE", None)
    return env


# ---------------------------------------------------------------- history / estimates
def _history_path():
    return STATE_DIR / "history.jsonl"


def load_history():
    out = []
    try:
        for line in _history_path().read_text().splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    except OSError:
        pass
    return out


def append_history(rec):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(_history_path(), "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(rec, sort_keys=True) + "\n")


def estimate_s(option, history=None):
    """Median wall of the last HISTORY_KEEP successful runs of `option` (seed when none) * MARGIN, >= MIN_ESTIMATE_S."""
    walls = [float(h["wall_s"]) for h in (load_history() if history is None else history)
             if h.get("option") == option and h.get("rc") == 0 and isinstance(h.get("wall_s"), (int, float))]
    walls = sorted(walls[-HISTORY_KEEP:])
    wall = (walls[len(walls) // 2] if len(walls) % 2 else sum(walls[len(walls) // 2 - 1:len(walls) // 2 + 1]) / 2) \
        if walls else SEED_WALL_S[option]
    return max(MIN_ESTIMATE_S, int(-(-wall * MARGIN // 1)))


# ---------------------------------------------------------------- state
def _state_path():
    return STATE_DIR / "state.json"


def load_state():
    try:
        return json.loads(_state_path().read_text())
    except (OSError, ValueError):
        return {}


def update_state(**kw):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_DIR / "state.lock", "a+") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        st = load_state()
        st.update(kw)
        tmp = _state_path().with_suffix(".tmp")
        tmp.write_text(json.dumps(st, sort_keys=True))
        os.replace(tmp, _state_path())
        return st


def pid_alive(pid, start=None):
    """Liveness by /proc (kill -0 is blind to reuse): pid exists, not a zombie, same start time."""
    try:
        raw = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return False
    fields = raw[raw.rfind(")") + 2:].split()
    if fields[0] == "Z":
        return False
    return start is None or int(fields[19]) == start


def proc_start(pid):
    raw = Path(f"/proc/{pid}/stat").read_text()
    return int(raw[raw.rfind(")") + 2:].split()[19])


# ---------------------------------------------------------------- decision
def status_text():
    p = subprocess.run(["gitnexus", "status"], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=120)
    return p.stdout


def is_stale(text):
    """True stale, False up-to-date, None unreadable (never trigger on an unreadable status)."""
    m = re.search(r"^Status:\s*(.*)$", text, re.M)
    if not m:
        return None
    line = m.group(1).lower()
    if "stale" in line:
        return True
    if "up-to-date" in line:
        return False
    return None


def current_commit(text):
    m = re.search(r"^Current commit:\s*([0-9a-f]{7,40})", text, re.M)
    return m.group(1) if m else None


def decide(text, state, now, batch_id=None, min_interval_h=DEFAULT_INTERVAL_H):
    """Return (action, reason); action is 'run' or 'skip'."""
    stale = is_stale(text)
    if stale is None:
        return "skip", "status unreadable"
    if not stale:
        return "skip", "fresh"
    pid = state.get("pid")
    if pid and pid_alive(pid, state.get("pid_start")) and not state.get("finished_at"):
        return "skip", f"running pid {pid}"
    if batch_id and state.get("last_batch") == batch_id:
        return "skip", f"already requested for batch {batch_id}"
    started = state.get("started_at")
    if started:
        wait = REFUSAL_RETRY_S if state.get("rc") in REFUSED_RC else min_interval_h * 3600
        if now - started < wait:
            return "skip", f"last attempt {int(now - started)}s ago, min {int(wait)}s"
    return "run", "stale"


# ---------------------------------------------------------------- rows
def row_id(option, commit, batch_id=None):
    tag = re.sub(r"[^A-Za-z0-9]+", "-", batch_id)[:24] if batch_id else time.strftime("%Y%m%d", time.gmtime())
    return f"gnx-reindex-{option}-{(commit or 'unknown')[:7]}-{tag}".strip("-")


def plan_rows(commit, history=None, batch_id=None, cpus=DEFAULT_CPUS, handoff_task=DEFAULT_HANDOFF_TASK,
              rank=DEFAULT_RANK, rows_root=None):
    """The two sibling rowflow specs (host, q3) for one commit; pure, writes nothing."""
    root = Path(rows_root or STATE_DIR / "rows")
    specs = []
    for option in OPTIONS:
        regions, claim = option_region(option, cpus)
        rid = row_id(option, commit, batch_id)
        d = root / rid
        est = estimate_s(option, history)
        specs.append({
            "id": rid, "owner": "pipeline-mgmt", "schema": "epyc.row.v3", "kind": "compute", "lane": "cpu",
            "regions": regions, "claim_cpus": claim, "gnx_option": option,
            "launcher": str(d / "launch.sh"), "workdir": str(d), "scratch_root": str(d),
            "stop_file": str(d / "STOP"),
            "result_path": str(d / "out" / "results.jsonl"), "result_format": "jsonl", "unit_key": "unit_id",
            "decision_rule": ("QUESTION  Is the root GitNexus index fresh at the requested commit?\n"
                              "RULE      PASS iff the analyze run exits 0 and `gitnexus status` reports up-to-date.\n"
                              "STOP      one run; a sibling option that already refreshed the index makes this row a no-op."),
            "verdict_by": "agent", "estimate_s": est, "min_window_s": est, "priority_rank": rank,
            "handoff_task": handoff_task, "resumable": True, "ram_gib": 16,
            "busy_fraction": 1.0 if option == "host" else 0.5,
            "width_justification": ("whole-host re-index: the same analyze under a four-quarter claim, short estimate"
                                    if option == "host" else
                                    "q3 non-GPU pocket 72-87 single-worker re-index; leaves q0-q2 and the MI210 host threads free"),
            "estimate_justification": (f"median measured wall of the last {HISTORY_KEEP} {option} runs (history.jsonl; seed "
                                       f"{SEED_WALL_S[option]} s from proxies) x {MARGIN} margin, floor {MIN_ESTIMATE_S} s"),
            "first_progress_s": 120,
            "smoke_predicate": ("/usr/bin/python3 -I -c 'import json,os,sys; p=\"%s\"; t=int(os.environ[\"FILLER_SMOKE_T0\"]); "
                                "sys.exit(0 if os.path.getmtime(p)>t and json.load(open(p)).get(\"verdict\")==\"SMOKE_OK\" else 1)'"
                                % (d / "out-smoke" / "RESULT.json")),
            "notes": f"GitNexus re-index of {commit or 'HEAD'} ({option}); housekeeping, resumable, low rank.",
        })
    return specs


def write_row_files(spec):
    """Materialise launch.sh / job.sh / reindex.py / spec.json in the row's job dir."""
    d = Path(spec["workdir"])
    (d / "out").mkdir(parents=True, exist_ok=True)
    shutil.copy2(HERE / "gitnexus-reindex.py", d / "reindex.py")
    opt, rid = spec["gnx_option"], spec["id"]
    py = "/usr/bin/python3 -I"
    (d / "job.sh").write_text(
        "#!/bin/bash\nset -uo pipefail\n"
        f"D={d}\ncd {REPO_ROOT}\n"
        f"export GITNEXUS_REINDEX_STATE_DIR={STATE_DIR} GITNEXUS_REINDEX_REPO={REPO_ROOT}\n"
        'if [ -n "${FILLER_SMOKE:-}" ]; then\n'
        f"  exec {py} $D/reindex.py smoke --out $D/out-smoke/RESULT.json\nfi\n"
        f"exec {py} $D/reindex.py exec --option {opt} --row-id {rid} --out $D/out/results.jsonl\n")
    (d / "launch.sh").write_text(
        "#!/bin/bash\nset -euo pipefail\n"
        f"D={d}\ncd \"$D\"\nulimit -c 0\n"
        f"exec /bin/bash {ENGINE} --id {rid} \\\n"
        f"  --class cpu --claim-cpus {spec['claim_cpus']} --role build --min-window {spec['min_window_s']} \\\n"
        f"  --cmd \"/bin/bash $D/job.sh\" \\\n"
        f"  --complete-cmd \"GITNEXUS_REINDEX_REPO={REPO_ROOT} {py} $D/reindex.py fresh\" \\\n"
        "  --stop \"$D/STOP\" --workdir \"$D\"\n")
    for f in ("job.sh", "launch.sh"):
        os.chmod(d / f, 0o755)
    (d / "spec.json").write_text(json.dumps(spec, indent=1, sort_keys=True))
    return d / "spec.json"


def publish_spec(spec):
    path = write_row_files(spec)
    p = subprocess.run([sys.executable, PUBLISH_ROW, str(path)], text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=600)
    return p.returncode, p.stdout[-600:]


# ---------------------------------------------------------------- commands
def publish_rows(args, text, publisher=None):
    commit = current_commit(text)
    specs = plan_rows(commit, batch_id=args.batch_id, cpus=args.cpus, handoff_task=args.handoff_task, rank=args.rank)
    if getattr(args, "dry_run", False):
        return [{"id": sp["id"], "regions": sp["regions"], "estimate_s": sp["estimate_s"]} for sp in specs]
    out = []
    for sp in specs:
        rc, msg = (publisher or publish_spec)(sp)
        out.append({"id": sp["id"], "regions": sp["regions"], "estimate_s": sp["estimate_s"], "rc": rc, "msg": msg})
    update_state(published=[o["id"] for o in out if o["rc"] == 0])
    return out


def cmd_exec(args):
    """The row's job body: analyze under the option's workers, then record wall/workers/region/nodes."""
    opt = args.option
    regions, _ = option_region(opt, args.cpus)
    update_state(pid=os.getpid(), pid_start=proc_start(os.getpid()), finished_at=None)
    t0, started = time.monotonic(), time.time()
    p = subprocess.run(analyze_argv(opt), cwd=REPO_ROOT, env=run_env(opt), text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT)
    wall = time.monotonic() - t0
    sys.stdout.write(p.stdout)
    rec = run_record(opt, regions, p.returncode, wall, started, p.stdout, args.row_id)
    record_run(rec, args.out)
    return p.returncode


def run_record(option, regions, rc, wall_s, started, output, row_id=None, env=None):
    env = os.environ if env is None else env
    m = re.findall(r"([\d,]+)\s+nodes", output or "")
    return {"ts": started, "row_id": row_id, "option": option, "region": regions, "rc": rc,
            "wall_s": round(wall_s, 1), "workers": 1 if option == "q3" else None,
            "threads": int(env["FILLER_THREADS"]) if str(env.get("FILLER_THREADS", "")).isdigit() else None,
            "nodes": int(m[-1].replace(",", "")) if m else None, "commit": current_commit(output or "")}


def record_run(rec, out=None):
    append_history(rec)
    update_state(rc=rec["rc"], finished_at=time.time(), last_run=rec)
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        with open(out, "a") as f:
            f.write(json.dumps(dict(rec, unit_id=rec.get("row_id") or str(rec["ts"])), sort_keys=True) + "\n")


def cmd_smoke(args):
    text = status_text()
    ok = is_stale(text) is not None
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"verdict": "SMOKE_OK" if ok else "SMOKE_FAIL"}))
    return 0 if ok else 1


def cmd_fresh(args):
    return 0 if is_stale(status_text()) is False else 1


def cmd_check(args, text=None):
    text = status_text() if text is None else text
    action, reason = decide(text, load_state(), time.time(), args.batch_id, args.min_interval_h)
    print(json.dumps({"action": action, "reason": reason, "commit": current_commit(text)}))
    return action, reason


def cmd_trigger(args, text=None, publisher=None, force=False):
    text = status_text() if text is None else text
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_DIR / "trigger.lock", "a+") as lk:   # serialize triggers: one decision at a time
        fcntl.flock(lk, fcntl.LOCK_EX)
        action, reason = decide(text, load_state(), time.time(), args.batch_id, args.min_interval_h)
        if force and is_stale(text) is not None:
            action, reason = "run", "forced"
        res = []
        if action == "run":
            validate_pocket(args.cpus)
            if not args.dry_run:
                update_state(started_at=time.time(), last_batch=args.batch_id, rc=None, finished_at=None,
                             pid=None, requested_commit=current_commit(text))
            res = publish_rows(args, text, publisher)
        print(json.dumps({"action": "publish" if action == "run" else "skip", "reason": reason, "rows": res}))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("check", "trigger", "publish", "exec", "fresh", "smoke", "estimates"))
    ap.add_argument("--cpus", default=DEFAULT_CPUS)
    ap.add_argument("--batch-id")
    ap.add_argument("--min-interval-h", type=float, default=DEFAULT_INTERVAL_H)
    ap.add_argument("--handoff-task", default=DEFAULT_HANDOFF_TASK)
    ap.add_argument("--rank", type=float, default=DEFAULT_RANK)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--option", choices=OPTIONS)
    ap.add_argument("--row-id")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    try:
        validate_pocket(args.cpus)
        if args.cmd == "exec":
            if not args.option:
                raise Usage("exec needs --option")
            return cmd_exec(args)
        if args.cmd == "fresh":
            return cmd_fresh(args)
        if args.cmd == "smoke":
            return cmd_smoke(args)
        if args.cmd == "estimates":
            print(json.dumps({o: estimate_s(o) for o in OPTIONS}))
            return 0
        if args.cmd == "check":
            cmd_check(args)
            return 0
        return cmd_trigger(args, force=args.cmd == "publish")
    except Usage as exc:
        print(f"gitnexus-reindex: {exc}", file=sys.stderr)
        return 64


if __name__ == "__main__":
    raise SystemExit(main())
