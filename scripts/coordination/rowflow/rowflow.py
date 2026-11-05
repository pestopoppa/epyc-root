#!/usr/bin/env python3
"""rowflow.py - the simplified inference-row pipeline (ws58, operator ruling 2026-11-01: remove every gate that is
not indispensable).

OWNER CONTRACT (two things): the launcher script and a small spec. `publish_row.py <spec.json>` derives the rest.

    spec (JSON)      required: id, owner, launcher (abs path, runs filler_run15.sh), lane (cpu|gpu),
                               result_path (what the filer reads), decision_rule, estimate_s, handoff_task
                     optional: result_format (jsonl|json|csv|tsv|text-lines|markdown-table|custom:<cmd>; default by
                               extension), regions (default gpu -> mi210_0,184-191; cpu -> any-cpu-quarter),
                               busy_fraction (0..1: share of its claimed cpus the job keeps busy; unset = 1.0; below
                               0.5 the row is never promoted to a host/quiet-host drain, only placed on free regions),
                               ram_gib (48), priority_rank (100), scratch_root (launcher's job dir), keep (globs that
                               ADD reaper protection; empty = inputs (older than the first job start) + result_path),
                               first_progress_s (300; aliases smoke_timeout_s, dryrun_timeout_s), smoke_predicate (shell; exit 0 =
                               the job's first real progress), unit_key (the field a real record must carry), dryrun_native_result
                               (count a unique per-attempt native JSON unit without touching result_path), lineage, lineage_reset,
                               supersedes, snapshot (true forces the snapshot below),
                               coexist_quiet_host ("gitnexus-q3" only: a single-worker gitnexus row on q3 cpus that
                               exclude the MI210 host threads, busy_fraction <= 0.1; see COEXIST below)

    COEXIST (operator 2026-11-05: "this way if GPU is running a timing run, we can still use spare threads on it to run
                    gitnexus as needed without impacting independent CPU runs on q0,q1, and q2"): a row marked
                    coexist_quiet_host=gitnexus-q3 and a quiet-host row neither prevent nor are prevented by each other
                    on q3: the quiet-host row treats q3 as free when its only holders are coexist rows, and a coexist row
                    may take COEXIST_Q3 cores while a quiet-host grant holds q3 (never 184-191, never another coexist
                    row's cores); drains and rank holds of a quiet-host row never hold a coexist row back.

    SNAPSHOT RULE   OPT-IN (operator 2026-11-03): only with `"snapshot": true` is the launcher's directory, and every
                    engine/job file under worktrees/ or /workspace (or a /workspace/repos/<x> target), copied at publish
                    time into <scratch_root>/snapshot/ (git archive HEAD of its directory when the worktree is clean, else
                    a working-tree copy with dirty=true), paths rewritten, files chmod a-w; the row's launcher/engine/
                    result paths point INTO the snapshot. Row field `snapshot` records it. Default: nothing is copied; a
                    launcher outside the job-dir root is refused in one line naming both fixes.

    published row    compute-flags/ready/<id>.json  schema epyc.row.v3 (derived: engine, min_window_s, window_s,
                     ports, gib, launcher sha256, scratch_root/keep for the reaper)

KEEPER SIDE (deterministic, no LLM): the keeper is the qualifier.
    allocate                  THE allocator (2026-11-01, operator "compute keeps idling because of scheduling races"): ONE
                              snapshot per tick (region-lock, open grants' holds=, live dry runs); dry runs and grants are
                              assigned together from it (an operator rank < URGENT_RANK first, by rank; then starved
                              lane, then priority_rank, a grantable row before a dry run; a region is never handed twice; any-cpu-quarter is resolved only here); it arms the
                              poller, admits through grant_ok_launcher (the one parser), WRITES the grant. Self-healing every tick: HEAL stale-grant / HEAL conflict (re-assigned) / CONFLICT,
                              IDLE-WHY <region>: <reason>, UNDERUSED (<5 % of a held quarter for 10 min -> owner fix task,
                              never killed), ALERT on the 3rd repeat (ws58-keeper-alerts.jsonl).
    gpu-batch                 run the queued GPU smokes (publish_row's GPU-busy queue) NOW if the GPU is free; any session
                              may call it, and allocate does the same on every GPU-free tick
    smokes (operator 2026-11-05)  publish_row QUEUES a CPU row's smoke (dryrun/<id>/SMOKE-QUEUED.json); allocate places
                              queued smokes FIRST, each on 4 genuinely free cores of one quarter (never 184-191, never
                              a quiet-host/gpu-q3 grant's cores), and runs it detached via publish_row --run-smoke. No
                              free cores = SMOKE-WAIT, never FAIL. The first-progress timer starts at engine START.
    (the dry run is publish_row.py's smoke: rowflow.dryrun_run, keeper-placed or --smoke-now; no grant. PASS = the job's
     FIRST REAL PROGRESS within first_progress_s - see FirstProgress; "a JSON appeared" is not progress)
    status <id>               needs-dryrun | dryrun-running | failed | parked | stale | stopped | grantable | armed | running | done
                              (stopped: the launcher's --stop file exists - never granted, never a drain candidate;
                               reason = the path; deleting it returns the row to grantable)
                              (parked: MAX_FAILS failed dry runs in the lineage, OR MAX_FAILS consecutive arming/launch
                              failures since the row's PASS - a PASS alone no longer keeps an unarmable row grantable)

Nothing here writes FILLERS.md, nonces, receipts or breakers. Removed with this flow: epyc.ready.v2 manifests,
ready/<id>.row.md, the 18-cell FILLERS.md row, keeper_qual_gate/qualify_launcher (nonce, receipt, fixture, cutoff proof),
the owner-wide worker breaker, the registry-row check, ws58_arm-v2.py.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:   # the keeper runs `python3 -I`: isolated mode does not put the script's directory on sys.path
    sys.path.insert(0, _HERE)
import hostutil  # noqa: E402  - measured CPU%/GPU% for every status surface (2026-11-03 session review item 2)
import notify  # noqa: E402  - push every terminal event / smoke FAIL / disk-floor crossing (incident 2026-11-04)

SCHEMA = "epyc.row.v3"
ADMISSION_CLASSES = {"correctness", "diagnostic", "block-correctness",
                     "block-timing-pairable", "block-timing-quiet", "filler"}
_LLM = "/mnt/raid0/llm/"  # the scratch root is spelled in two pieces: the repo hook refuses any script that names it next to a delete
FLAGS = os.environ.get("ROWFLOW_FLAGS", _LLM + "tmp/compute-flags")
RL = os.environ.get("ROWFLOW_RL", "/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock")
ROCM_SMI = "/opt/rocm/bin/rocm-smi"
TMP = os.environ.get("ROWFLOW_TMP", _LLM + "tmp/")  # tests override
ENGINE_RE = re.compile(r"filler_run(\d+)\.sh$")
CANONICAL_ENGINE = "filler_run15.sh"
MAX_FAILS = 3
DISK_FLOOR_GIB = 150.0       # == filler_run15.sh FILLER_DISK_FLOOR_GIB default and scratch_release.DISK_FLOOR_GIB
DEFAULT_BUDGET_GIB = 1.0     # a row's declared scratch growth when the spec names none (budget_gib)
STOP_GRACE_S = 600  # a job may finish its current item before honouring the stop file
_STEM_SUFFIX = re.compile(r"(?:[-_](?:\d{8}(?:T\d{4,6}Z?)?|v\d+|r\d+|rearm|retry\d*|try\d+))+$", re.I)
SNAPSHOT_MAX_BYTES = 256 << 20  # a snapshot copies a directory; a launcher that lives next to models is a spec defect


def _default_snapshot_roots():
    """Directories whose contents change under the keeper's feet: lane worktrees (merged/removed per session) and the
    /workspace clone plus every repo its repos/ symlinks resolve to. A launcher, job or engine under one of them is
    SNAPSHOTTED into the row's scratch_root at publish time (tests override the list)."""
    roots = [_LLM + "worktrees/", "/workspace/"]
    for p in ["/workspace", _LLM + "epyc-root"] + sorted(glob.glob("/workspace/repos/*")):
        if not os.path.isdir(p):
            continue
        try:
            rp = os.path.realpath(p)
        except OSError:
            continue
        if os.path.basename(rp).startswith("llama.cpp"):
            continue  # the production kernel tree is FROZEN: a binary under it is not volatile
        if rp and rp != "/" and rp.rstrip("/") + "/" not in roots:
            roots.append(rp.rstrip("/") + "/")
    return roots


SNAPSHOT_ROOTS = _default_snapshot_roots()


class Refused(Exception):
    pass


def need(ok, why):
    if not ok:
        raise Refused(why)


def now_iso():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def atomic_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(value, f, indent=1, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def load_json(path):
    try:
        with open(path) as f:
            v = json.load(f)
        return v if isinstance(v, dict) else None
    except (OSError, ValueError):
        return None


def alive(pid):
    try:
        return bool(pid) and subprocess.run(["ps", "-o", "pid=", "-p", str(int(pid))], capture_output=True).returncode == 0
    except (ValueError, TypeError):
        return False


def id_stem(rid):
    return _STEM_SUFFIX.sub("", rid or "") or rid


# ---------------------------------------------------------------- paths
def ready_path(flags, rid): return os.path.join(flags, "ready", rid + ".json")
def dry_dir(flags, rid): return os.path.join(flags, "dryrun", rid)
def pass_path(flags, rid): return os.path.join(dry_dir(flags, rid), "PASS.json")
def armed_path(flags, rid): return os.path.join(dry_dir(flags, rid), "ARMED.json")
def running_path(flags, rid): return os.path.join(dry_dir(flags, rid), "RUNNING.json")
def fail_paths(flags, rid): return sorted(glob.glob(os.path.join(dry_dir(flags, rid), "FAIL-*.json")))
def granted_path(flags, rid): return os.path.join(dry_dir(flags, rid), "GRANTED.json")


ARM_FAIL_KINDS = ("arm", "launch")
_LEGACY_ARM_FAIL = "poller did not log 'launcher up pid='"


def is_arm_fail(f):
    """A FAIL record written by the allocator (arming: no 'launcher up pid=' in 30 s; launch: admission refused the
    armed poller), not by a dry run. Records before 2026-11-03 carry no kind: matched by the arm_one reason."""
    return (f or {}).get("kind") in ARM_FAIL_KINDS or str((f or {}).get("reason", "")).startswith(_LEGACY_ARM_FAIL)


def arm_fails_since_pass(flags, rid, p=None):
    """[FAIL records] of the consecutive arming/launch failures since the row's PASS and its last successful grant
    (ws58 2026-11-03: yarn-e1-a2-gpu failed to arm 172 times after its PASS and stayed grantable all night)."""
    p = load_json(pass_path(flags, rid)) if p is None else p
    t0 = max(iso_epoch((p or {}).get("passed_at")) or 0.0, iso_epoch((load_json(granted_path(flags, rid)) or {}).get("at")) or 0.0)
    out = []
    for fp in fail_paths(flags, rid):
        f = load_json(fp) or {}
        if is_arm_fail(f) and (iso_epoch(f.get("at")) or 0.0) >= t0:
            out.append(dict(f, fail_file=fp))
    return sorted(out, key=lambda f: iso_epoch(f.get("at")) or 0.0)


def row_sha(flags, rid):
    p = ready_path(flags, rid)
    return sha256(p) if os.path.isfile(p) else None


def rows(flags):
    out = {}
    for p in sorted(glob.glob(os.path.join(flags, "ready", "*.json"))):
        d = load_json(p)
        if d and d.get("schema") == SCHEMA and d.get("id"):
            out[d["id"]] = d
    return out


# ---------------------------------------------------------------- launcher parsing (static, no exec)
def parse_launcher(path):
    """Tokens of the engine invocation inside the launcher: engine path + its options. Resolves $D/$HERE-style
    variables assigned at the top of the script; anything else stays literal."""
    text = open(path, errors="replace").read()
    need(text.startswith("#!"), "launcher has no shebang")
    assigns = {}
    for m in re.finditer(r'^(?:export\s+)?([A-Za-z_][A-Za-z_0-9]*)=("?)([^\n"]*)\2\s*$', text, re.M):
        assigns[m.group(1)] = m.group(3)
    assigns.setdefault("HERE", os.path.dirname(path))

    def expand(s):
        for _ in range(3):
            s = re.sub(r"\$\{([A-Za-z_][A-Za-z_0-9]*)(?::[-?][^}]*)?\}|\$([A-Za-z_][A-Za-z_0-9]*)",
                       lambda m: assigns.get(m.group(1) or m.group(2), m.group(0)), s)
            s = s.replace('$(dirname "$0")', os.path.dirname(path)).replace("$(dirname $0)", os.path.dirname(path))
        return s
    # the engine line may be continued with backslashes
    joined = re.sub(r"\\\n", " ", text)
    line = next((el for el in (expand(l) for l in joined.splitlines()) if re.search(r"filler_run\d+\.sh", el) and "--id" in el), None)
    need(line, "launcher does not invoke a filler_run*.sh engine with --id")
    toks = shlex.split(line, comments=True)
    i = next(i for i, t in enumerate(toks) if ENGINE_RE.search(t))
    o = {"engine": toks[i], "class": "", "min_window": 0, "ports": [], "stop": "", "workdir": "/workspace",
         "complete_cmd": "", "cmd": "", "gpu_quiet": "", "claim_cpus": "", "nofold": False, "id": ""}
    j = i + 1
    one = {"--id": "id", "--class": "class", "--stop": "stop", "--workdir": "workdir", "--complete-cmd": "complete_cmd",
           "--cmd": "cmd", "--gpu-quiet": "gpu_quiet", "--claim-cpus": "claim_cpus"}
    while j < len(toks):
        t = toks[j]
        if t == "--min-window":
            o["min_window"] = int(toks[j + 1]); j += 2
        elif t == "--port":
            o["ports"] = [int(x) for x in toks[j + 1].split(",") if x]; j += 2
        elif t in one:
            o[one[t]] = toks[j + 1]; j += 2
        elif t in ("--sched-port", "--excl-lock", "--gpu-threads", "--role", "--precond-cmd", "--requires-tool", "--qual-interpreter"):
            j += 2
        elif t == "--no-fold-siblings":
            o["nofold"] = True; j += 1
        elif t in ("--self-claim", "--repeat"):
            j += 1
        else:
            j += 1
    need(o["id"], "engine line has no --id")
    need(o["class"] in ("cpu", "gpu", "cpu+gpu"), "engine --class missing")
    need(o["min_window"] > 0, "engine --min-window missing")
    need(o["complete_cmd"], "engine --complete-cmd missing (the engine refuses without it)")
    need(o["stop"], "engine --stop missing")
    o["threads"], o["threads_evidence"] = launcher_threads(text, assigns, o)
    return o


_THREAD_PATS = (
    ("-t", re.compile(r"(?<![\w-])-t\s+['\"]?(\d+)\b")),
    ("--threads", re.compile(r"--threads[ =]+['\"]?(\d+)\b")),
    ("--workers", re.compile(r"--workers[ =]+['\"]?(\d+)\b")),
    ("OMP_NUM_THREADS", re.compile(r"\bOMP_NUM_THREADS=['\"]?(\d+)\b")),
)
_TASKSET = re.compile(r"\btaskset\s+(?:-a\s+)?(?:-c|--cpu-list)\s+['\"]?([\d,-]+)")


def count_cpus(cpus):
    n = set()
    for tok in str(cpus or "").split(","):
        tok = tok.strip()
        if re.fullmatch(r"\d+(-\d+)?", tok):
            a, b = (tok.split("-") + [tok])[:2]
            n |= set(range(int(a), int(b) + 1))
    return len(n)


def launcher_threads(text, assigns, o):
    """Refinement 1 (keeper-friction review 2026-11-05): the threads the job declares in its argv - -t/--threads N,
    --workers N, OMP_NUM_THREADS=N, taskset -c LIST - in the launcher and in the job file its --cmd names (.sh/.py).
    Variables assigned in the launcher (and ${X:-N} defaults) are expanded. Returns (max threads or None, [evidence])."""
    texts = [text]
    for m in re.finditer(r"(/[^\s'\"`;|&()<>]+\.(?:sh|py))", o.get("cmd") or ""):
        try:
            texts.append(open(m.group(1), errors="replace").read()[:1 << 20])
        except OSError:
            pass

    def ex(t):
        for _ in range(3):
            t = re.sub(r"\$\{([A-Za-z_]\w*):-([^}]*)\}", lambda m: assigns.get(m.group(1), m.group(2)), t)
            t = re.sub(r"\$\{([A-Za-z_]\w*)\}|\$([A-Za-z_]\w*)", lambda m: assigns.get(m.group(1) or m.group(2), m.group(0)), t)
        return t
    best, tsk, ev = None, None, []
    for t in texts:
        # python argv lists (["-t", THREADS] / ["taskset", "-c", CPUS]): the first literal a NAME = "..." assignment
        # gives (the production value; a conditional's smoke branch comes after `if`) becomes a plain argv token
        pyv = {}
        for m in re.finditer(r"^[ \t]*([A-Za-z_]\w*)\s*=\s*(?:\(.*?or\s*)?[\"']([\d][\d,-]*)[\"']", t, re.M):
            pyv.setdefault(m.group(1), m.group(2))
        for m in re.finditer(r"^[ \t]*([A-Za-z_]\w*)\s*=\s*(\d+)\s*(?:#.*)?$", t, re.M):
            pyv.setdefault(m.group(1), m.group(2))
        t = re.sub(r"""[\"'](-t|--threads|--workers|-c|--cpu-list|taskset)[\"']\s*,\s*(?:[\"']([\w,-]+)[\"']|([A-Za-z_]\w*))""",
                   lambda m: f" {m.group(1)} {m.group(2) or pyv.get(m.group(3), m.group(3))}", t)
        t = re.sub(r"""[\"']taskset[\"']\s*,""", " taskset ", t)
        t = ex(re.sub(r"\\\n", " ", t))
        for line in t.splitlines():
            if line.lstrip().startswith("#"):
                continue
            for name, rx in _THREAD_PATS:
                for m in rx.finditer(line):
                    n = int(m.group(1))
                    if 0 < n <= 192:
                        ev.append(f"{name} {n}"); best = max(best or 0, n)
            for m in _TASKSET.finditer(line):
                n = count_cpus(m.group(1))
                if n:
                    ev.append(f"taskset {m.group(1)}"); tsk = max(tsk or 0, n)
    # an explicit thread knob wins over a taskset list (taskset 0-95 + -t 48 uses 48 threads); taskset alone bounds it
    return (best if best is not None else tsk), sorted(set(ev))


# the launcher's own `D=` idioms that name its directory (ws58 2026-11-05: 18 rows carried an unexpanded `$D/...STOP`)
_D_SELF_DIR = re.compile(r"""^\$\((?:cd\s+(?:--\s+)?"\$\(dirname\s+(?:--\s+)?"(?:\$0|\$\{BASH_SOURCE\[0\]\})"\)"\s*&&\s*pwd|dirname\s+(?:--\s+)?"(?:\$0|\$\{BASH_SOURCE\[0\]\})")\)$""")
_D_SELF_REAL = re.compile(r"""^\$\(dirname\s+(?:--\s+)?"\$\(readlink\s+-f\s+(?:--\s+)?"(?:\$0|\$\{BASH_SOURCE\[0\]\})"\)"\)$""")


def resolve_stop_path(d):
    """The row's STOP file as an absolute path, or None (unknown). Manifest `stop_file` when it is a literal absolute
    path; else the launcher's `--stop` with ITS OWN single `D=` assignment substituted (a literal absolute path or the
    launcher-directory idiom). Only literal paths and `$D/...` count; anything else is unknown (= no STOP evidence)."""
    sf = str((d or {}).get("stop_file") or "")
    if sf.startswith("/") and "$" not in sf and "`" not in sf:
        return os.path.normpath(sf)
    lp = str(((d or {}).get("launcher") or {}).get("path") or "")
    try:
        text = open(lp, errors="replace").read()
    except OSError:
        return None
    if not sf:
        m = re.search(r"""--stop[ =]+("[^"]*"|'[^']*'|\S+)""", re.sub(r"\\\n", " ", text))
        sf = m.group(1).strip("\"'") if m else ""
    m = re.match(r"^\$(?:D|\{D\})(/.*)$", sf)
    if not m:
        return None
    defs = {v.strip() for v in re.findall(r"^[ \t]*(?:export\s+)?D=(.*?)\s*(?:#.*)?$", text, re.M)}
    if len(defs) != 1:
        return None
    v = defs.pop()
    if len(v) > 1 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1]
    if v.startswith("/") and not re.search(r"[$`*?]", v):
        base = v
    elif _D_SELF_REAL.match(v):
        base = os.path.dirname(os.path.realpath(lp))
    elif _D_SELF_DIR.match(v):
        base = os.path.dirname(os.path.abspath(lp))
    else:
        return None
    rest = m.group(1)
    if re.search(r"[$`*?]", rest):
        return None
    return os.path.normpath(base + rest)


# ---------------------------------------------------------------- snapshot (rows are independent of lanes)
def volatile_root(path):
    """The SNAPSHOT_ROOTS entry a path falls under, spelled or resolved (/workspace/repos/<x> symlinks count), else None."""
    if not isinstance(path, str) or not os.path.isabs(path):
        return None
    for p in (path, os.path.realpath(path)):
        for r in SNAPSHOT_ROOTS:
            if p == r.rstrip("/") or p.startswith(r):
                return r
    return None


_ABS_TOKEN = re.compile(r"(?<![\w.])(/[^\s'\"`;|&()<>]+)")


def referenced_paths(o):
    """Absolute, existing paths the engine line executes or uses: the engine, --cmd/--complete-cmd tokens, --workdir."""
    out = []
    for s in (o.get("engine", ""), o.get("cmd", ""), o.get("complete_cmd", ""), o.get("workdir", "")):
        for t in _ABS_TOKEN.findall(" " + str(s)):
            t = t.rstrip("/.,:") or t
            if os.path.exists(t) and t not in out:
                out.append(t)
    return out


def _git(wt, *args):
    r = subprocess.run(["git", "-C", wt] + list(args), capture_output=True, text=True, timeout=120)
    return r.returncode, r.stdout


def _dir_bytes(d):
    n = 0
    for root, dirs, files in os.walk(d):
        dirs[:] = [x for x in dirs if x not in (".git", "__pycache__")]
        for f in files:
            try:
                n += os.lstat(os.path.join(root, f)).st_size
            except OSError:
                pass
    return n


def _rmtree_ro(d):
    """rmtree of a tree whose files are read-only (the previous snapshot of this row)."""
    for root, dirs, files in os.walk(d):
        for x in dirs:
            try:
                os.chmod(os.path.join(root, x), 0o755)
            except OSError:
                pass
    shutil.rmtree(d, ignore_errors=True)


def snapshot_dir(src, dst):
    """Snapshot directory `src` (resolved) into `dst`. Inside a git worktree with a clean, tracked `src`: `git archive
    HEAD:<rel>` and the commit is recorded; otherwise (untracked or dirty) the working-tree files are copied and
    source_commit is null with dirty=true. Returns the unit record (without shas; those are taken after rewriting)."""
    need(os.path.isdir(src), f"snapshot source {src} is not a directory")
    size = _dir_bytes(src)
    need(size <= SNAPSHOT_MAX_BYTES, f"snapshot source {src} is {size >> 20} MiB (> {SNAPSHOT_MAX_BYTES >> 20} MiB); "
         "put the launcher and its job files in a small directory of their own")
    rc, top = _git(src, "rev-parse", "--show-toplevel")
    rec = {"source_path": src, "snapshot_dir": dst, "source_commit": None, "dirty": False, "method": "copy", "git_toplevel": None}
    if rc == 0 and top.strip():
        top = os.path.realpath(top.strip())
        rel = os.path.relpath(src, top)
        need(rel != ".", f"{src} is a repository top level; a launcher is snapshotted by directory, so it needs a subdirectory of its own")
        rec["git_toplevel"] = top
        _, head = _git(top, "rev-parse", "HEAD")
        _, tracked = _git(top, "ls-files", "--", rel)
        _, dirty = _git(top, "status", "--porcelain", "--untracked-files=all", "--", rel)
        if head.strip() and tracked.strip() and not dirty.strip():
            os.makedirs(dst)
            r = subprocess.run(["git", "-C", top, "archive", "--format=tar", f"HEAD:{rel}"], capture_output=True, timeout=300)
            need(r.returncode == 0, f"git archive HEAD:{rel} failed in {top}: {r.stderr.decode(errors='replace')[:200]}")
            x = subprocess.run(["tar", "-x", "-C", dst], input=r.stdout, capture_output=True, timeout=300)
            need(x.returncode == 0, f"extracting the archive of {rel} failed: {x.stderr.decode(errors='replace')[:200]}")
            rec.update(source_commit=head.strip(), method="git-archive")
            return rec
        rec.update(dirty=True, dirty_head=head.strip() or None,
                   dirty_reason="untracked" if not tracked.strip() else "uncommitted changes under " + rel)
    shutil.copytree(src, dst, symlinks=True, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    return rec


def snapshot_launcher(launcher, o, scratch):
    """Snapshot the launcher's directory, the engine's directory and every other referenced path's directory that lives
    under a SNAPSHOT_ROOT into <scratch>/snapshot/, rewrite every spelled/resolved source directory to its snapshot
    directory inside the snapshot's text files, make the files read-only and return (manifest, mapping)."""
    snap = os.path.join(scratch, "snapshot")
    if os.path.lexists(snap):
        _rmtree_ro(snap)
    src_dir = os.path.dirname(os.path.realpath(launcher))
    need(not (scratch + "/").startswith(src_dir + "/") and not src_dir.startswith(scratch + "/"),
         f"launcher dir {src_dir} and scratch_root {scratch} nest; a snapshotted launcher needs a scratch_root of its own (default {TMP}<id>)")
    units = [(src_dir, os.path.join(snap, "launcher"), {launcher})]
    for p in referenced_paths(o):
        if not volatile_root(p):
            continue
        rp = os.path.realpath(p)
        d = rp if os.path.isdir(rp) else os.path.dirname(rp)
        if any(d == u[0] or d.startswith(u[0] + "/") for u in units):
            units_match = next(u for u in units if d == u[0] or d.startswith(u[0] + "/"))
            units_match[2].add(p)
            continue
        units.append((d, os.path.join(snap, "ext", d.lstrip("/")), {p}))
    os.makedirs(snap, exist_ok=True)
    mapping = {}
    recs = []
    for d, dst, spelled_paths in units:
        rec = snapshot_dir(d, dst)
        mapping[d] = dst
        for sp in spelled_paths:  # the spelled form of each reference (e.g. /workspace/repos/<x>/...) maps too
            sd = sp if os.path.isdir(sp) else os.path.dirname(sp)
            sreal = os.path.realpath(sd)
            if sreal == d:
                mapping[sd.rstrip("/")] = dst
            elif sreal.startswith(d + "/"):
                mapping[sd.rstrip("/")] = os.path.join(dst, os.path.relpath(sreal, d))
        recs.append(rec)
    # longest source first so a nested spelling never gets a partial rewrite
    rewrites = sorted(mapping.items(), key=lambda kv: -len(kv[0]))
    files = {}
    for root, dirs, fns in os.walk(snap):
        for fn in fns:
            fp = os.path.join(root, fn)
            if os.path.islink(fp):
                continue
            with open(fp, "rb") as f:
                data = f.read()
            if b"\0" not in data:
                new = data
                for s, t in rewrites:
                    new = new.replace(s.encode(), t.encode())
                if new != data:
                    with open(fp, "wb") as f:
                        f.write(new)
            os.chmod(fp, os.stat(fp).st_mode & ~0o222)
            files[os.path.relpath(fp, snap)] = sha256(fp)

    def remap(p):
        for s, t in rewrites:
            if p == s or p.startswith(s + "/"):
                return t + p[len(s):]
        return p
    new_launcher = remap(os.path.realpath(launcher))
    need(os.path.isfile(new_launcher), f"snapshot has no launcher at {new_launcher}")
    manifest = {"source_path": launcher, "source_commit": recs[0]["source_commit"], "dirty": recs[0]["dirty"], "snapshot_dir": snap,
                "launcher": new_launcher, "method": recs[0]["method"], "git_toplevel": recs[0]["git_toplevel"],
                "rewrites": dict(rewrites), "units": recs, "sha256": files, "taken_at": now_iso()}
    for k in ("dirty_head", "dirty_reason"):
        if recs[0].get(k):
            manifest[k] = recs[0][k]
    return manifest, remap


# ---------------------------------------------------------------- publish
def guess_format(result_path):
    ext = os.path.splitext(result_path.split("*")[0].rstrip("/"))[1].lower()
    return {".jsonl": "jsonl", ".json": "json", ".csv": "csv", ".tsv": "tsv", ".md": "markdown-table"}.get(ext, "text-lines")


FETCH_KINDS = ("fetch", "prepare", "inputs", "download", "copy")


_VER = re.compile(r"^(.+?)-([vr])(\d+)((?:[-_]\d{8}(?:T\d{4,6}Z?)?)?)$", re.I)


def disk_floor_predecessor(flags, rid):
    """(id, scratch_root) of the newest lower version of rid's family (<base>-vN / -rN) when its grants/<id>.ended says
    reason=disk-floor; else None."""
    m = _VER.match(rid)
    if not m:
        return None
    base, kind, n = m.group(1), m.group(2).lower(), int(m.group(3))
    best = None
    for e in glob.glob(os.path.join(flags, "grants", "*.ended")):
        oid = os.path.basename(e)[:-6]
        w = _VER.match(oid)
        if w and w.group(1) == base and w.group(2).lower() == kind and int(w.group(3)) < n and (best is None or int(w.group(3)) > best[0]):
            best = (int(w.group(3)), oid, e)
    if not best or "reason=disk-floor" not in (head1(best[2]) or ""):
        return None
    return best[1], (load_json(ready_path(flags, best[1])) or {}).get("scratch_root")


def publish(spec, flags=FLAGS, source=None, allow_legacy_engine=False):
    for k in ("id", "owner", "launcher", "lane", "result_path", "decision_rule", "estimate_s", "handoff_task"):
        need(k in spec and spec[k] not in (None, ""), f"spec.{k} missing")
    rid = str(spec["id"])
    need(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]+", rid), "bad id")
    # operator 2026-11-01: fetch-only rows (download/copy inputs, e.g. acquire.py at 3% of a core holding a quarter) are
    # session preparation, not compute. The spec says what kind of row it is; fetch/prepare kinds are refused.
    need(str(spec.get("kind", "compute")).lower() not in FETCH_KINDS,
         "prepare inputs before publishing: fetching/copying data is session preparation, not a compute row")
    need(spec["lane"] in ("cpu", "gpu"), "lane must be cpu or gpu")
    if spec.get("admission_class") is not None:
        need(isinstance(spec["admission_class"], str) and spec["admission_class"] in ADMISSION_CLASSES,
             "admission_class must be one of " + ", ".join(sorted(ADMISSION_CLASSES)))
    if spec.get("dryrun_native_result") is not None:
        need(isinstance(spec["dryrun_native_result"], bool), "dryrun_native_result must be boolean")
    check_busy_fraction(spec)
    launcher = os.path.abspath(str(spec["launcher"]))
    need(os.path.isfile(launcher), f"launcher {launcher} missing")
    for term in (".ended", ".complete"):
        need(not os.path.exists(os.path.join(flags, "grants", rid + term)), f"id {rid} already has grants/{rid}{term}; a terminal id is never reused")
    o = parse_launcher(launcher)
    need(o["id"] == rid, f"launcher --id {o['id']} != spec id {rid}")
    eng = o["engine"]
    need(allow_legacy_engine or os.path.basename(eng) == CANONICAL_ENGINE, f"engine must be {CANONICAL_ENGINE} (found {os.path.basename(eng)}; "
         "older engines require the retired manifest/FILLERS stack and refuse without it)")
    need(os.path.isfile(eng), f"engine {eng} missing")
    lane = spec["lane"]
    need((lane == "gpu") == (o["class"] in ("gpu", "cpu+gpu")), f"lane {lane} disagrees with engine --class {o['class']}")
    est = int(spec["estimate_s"])
    need(est > 0, "estimate_s must be positive seconds")
    result_path = str(spec["result_path"])
    need(os.path.isabs(result_path), "result_path must be absolute")
    # rows are independent of lanes: a launcher / engine / job file under a worktree or /workspace changes under the keeper's
    # feet (lane merges before every resume, removal at session end). Operator 2026-11-03 (session review §5 item 8): the
    # snapshot into the row's own scratch_root is OPT-IN (`"snapshot": true`); by default nothing is copied.
    snap = None
    vr = volatile_root(launcher)
    if spec.get("snapshot") is not True and (vr or not launcher.startswith(TMP)):
        where = f"under the lane/worktree path {vr}" if vr else f"outside the job-dir root {TMP}"
        raise Refused(f"launcher {launcher} is {where}: copy its job dir to {TMP}{rid}/ and publish that launcher, or set "
                      f"\"snapshot\": true in the spec")
    if spec.get("snapshot") is True:
        volatile = [p for p in [launcher] + referenced_paths(o) if volatile_root(p)]
        scratch = os.path.normpath(spec.get("scratch_root") or TMP + rid)
        need(scratch.startswith(TMP) and scratch[len(TMP):].split("/")[0] not in ("", "compute-flags", "disk-audit-20261028"),
             f"scratch_root {scratch} must be a job dir under {TMP} (not compute-flags)")
        os.makedirs(scratch, exist_ok=True)
        try:
            snap, remap = snapshot_launcher(launcher, o, scratch)
        except Refused as e:
            raise Refused(f"launcher {launcher} lives under a lane/worktree path ({', '.join(volatile) or 'snapshot: true'}) and could not be snapshotted: {e}")
        launcher = snap["launcher"]
        o = parse_launcher(launcher)
        eng = o["engine"]
        need(os.path.isfile(eng), f"engine {eng} missing from the snapshot")
        result_path = remap(result_path)
        if result_path.startswith(snap["snapshot_dir"] + "/"):
            os.makedirs(os.path.dirname(result_path.split("*")[0]) or "/", exist_ok=True)
    else:
        scratch = os.path.normpath(spec.get("scratch_root") or (TMP + launcher[len(TMP):].split("/")[0] if launcher.startswith(TMP) else os.path.dirname(launcher)))
    need(scratch.startswith(TMP) and scratch[len(TMP):].split("/")[0] not in ("", "compute-flags", "disk-audit-20261028"),
         f"scratch_root {scratch} must be a job dir under {TMP} (not compute-flags)")
    need(launcher.startswith(scratch + "/"), f"launcher {launcher} is not inside scratch_root {scratch}")
    # coordinator 2026-11-04 (akxall8 v9..v37): a job stopped by the disk floor is a HOST condition, not an attempt. A new
    # version of a row family whose newest ended predecessor stopped reason=disk-floor must reuse that predecessor's
    # scratch_root (no fresh snapshot); otherwise wait for space. Each fresh 2 GB snapshot pushed the disk lower.
    pred = disk_floor_predecessor(flags, rid)
    if pred:
        need(os.path.normpath(pred[1] or "") == scratch,
             f"predecessor {pred[0]} stopped reason=disk-floor (host condition, not an attempt): reuse its scratch_root "
             f"{pred[1]} (no fresh snapshot) or wait for disk space")
    keep = list(spec.get("keep") or [])   # operator 2026-11-03: empty = inputs + result (the reaper protects every input)
    if result_path.startswith(scratch + "/"):
        rel = os.path.relpath(result_path, scratch)
        if rel not in keep:
            keep.append(rel)
    fmt = str(spec.get("result_format") or guess_format(result_path))
    need(fmt in ("jsonl", "json", "csv", "tsv", "text-lines", "markdown-table") or fmt.startswith("custom:"), f"unknown result_format {fmt}")
    # operator 2026-11-03: the smoke's PASS is the job's FIRST REAL PROGRESS within first_progress_s (FirstProgress)
    try:
        fps = int(spec.get("first_progress_s") or spec.get("smoke_timeout_s") or spec.get("dryrun_timeout_s") or FIRST_PROGRESS_S)
    except (TypeError, ValueError):
        raise Refused("first_progress_s must be whole seconds (e.g. \"first_progress_s\": 900)")
    need(fps > 0, "first_progress_s must be positive seconds")
    for k in ("smoke_predicate", "unit_key"):
        need(spec.get(k) is None or (isinstance(spec[k], str) and spec[k].strip()), f"{k} must be a non-empty string")
    if spec.get("unit_key") and fmt == "text-lines":
        try:
            re.compile(spec["unit_key"])
        except re.error as e:
            raise Refused(f"unit_key is a regex for text-lines results and does not compile: {e}")
    # scratch budget (operator 2026-11-04, lease Phase 3 minimal): the GiB this row may still write into scratch; the
    # allocator refuses its grant when free disk minus every live grant's budget would breach DISK_FLOOR_GIB.
    try:
        budget = float(spec.get("budget_gib") if spec.get("budget_gib") is not None else DEFAULT_BUDGET_GIB)
    except (TypeError, ValueError):
        raise Refused("budget_gib must be a number of GiB")
    need(budget >= 0, "budget_gib must be >= 0")
    # scratch_inputs (operator 2026-11-04): re-derivable inputs under scratch_root, released promptly once the row ends.
    sins = spec.get("scratch_inputs")
    if sins is not None:
        need(isinstance(sins, list) and all(isinstance(x, dict) and isinstance(x.get("path"), str) and x["path"]
                                            and not os.path.isabs(x["path"]) and ".." not in x["path"].split("/")
                                            and x.get("kind") in ("git-worktree", "sha-manifest") for x in sins),
             "scratch_inputs must be [{path (relative to scratch_root), kind: git-worktree|sha-manifest, manifest?, source?}]")
    regions = str(spec.get("regions") or ("mi210_0,184-191" if lane == "gpu" else ("0-95" if o["claim_cpus"] == "0-95" else "any-cpu-quarter")))
    if lane == "gpu":
        need("mi210_0" in regions, "gpu regions must name mi210_0")
    minwin = int(spec.get("min_window_s") or o["min_window"])
    need(minwin == o["min_window"], f"spec min_window_s {minwin} != launcher --min-window {o['min_window']}")
    window = max(minwin + 300, int(est * 1.2) + 300)
    window = -(-window // 60) * 60
    try:
        rank = float(spec.get("priority_rank", 100))
    except (TypeError, ValueError):
        raise Refused("priority_rank must be a number")
    row = {
        "schema": SCHEMA, "id": rid, "owner": str(spec["owner"]), "lane": lane, "regions": regions,
        "launcher": {"path": launcher, "sha256": sha256(launcher)}, "engine": {"path": eng, "sha256": sha256(eng)},
        "result_path": result_path, "result_format": fmt, "decision_rule": spec["decision_rule"],
        "handoff_task": spec["handoff_task"], "estimate_s": est, "min_window_s": minwin, "window_s": window,
        "gib": int(spec.get("ram_gib") or 48), "ports": sorted(set(o["ports"]) | {int(x) for x in (spec.get("ports") or [])}),
        "priority_rank": rank,
        "scratch_root": scratch, "keep": keep, "stop_file": o["stop"], "workdir": o["workdir"],
        "first_progress_s": fps, "budget_gib": budget,
        "published_at": now_iso(), "published_from": source or "spec",
    }
    if spec.get("total_units") is not None:
        row["total_units"] = int(spec["total_units"])
    if spec.get("admission_class") is not None:
        row["admission_class"] = spec["admission_class"]
    if spec.get("busy_fraction") is not None:
        row["busy_fraction"] = float(spec["busy_fraction"])
    if spec.get("coexist_quiet_host") is not None:
        check_coexist(spec, o, regions)
        row["coexist_quiet_host"] = COEXIST_TAG
    if snap:
        row["snapshot"] = snap
    elif isinstance(spec.get("snapshot"), dict):  # a republish from ready/<id>.json (publish_row.py --repair) keeps its snapshot record
        row["snapshot"] = spec["snapshot"]
    # who published it: INFORMATION ONLY (alerts route to the `inference` mailbox); a republish keeps the original
    row["publisher"] = spec["publisher"] if isinstance(spec.get("publisher"), dict) else notify.publisher_info()
    for k in ("lineage", "lineage_reset", "supersedes", "notes", "row", "dryrun_native_result", "publish_warnings",
              "smoke_predicate", "unit_key", "scratch_inputs", "fix_ref", "baseline_ref", "shape_override"):
        if spec.get(k) is not None:
            row[k] = spec[k]
    # refinement 4/5 root cause (2026-11-05 `$D` bug): the STOP file must resolve to an absolute path at publish
    sfp = resolve_stop_path({"stop_file": o["stop"], "launcher": {"path": launcher}})
    need(sfp, f"stop_file {o['stop']!r} is not absolute and does not resolve from the launcher's own D= assignment; "
              "use a literal absolute --stop path (or D=\"$(cd \"$(dirname \"$0\")\" && pwd)\" with --stop \"$D/<id>.STOP\")")
    row["stop_file"] = sfp
    sup = spec.get("supersedes")
    if sup is not None:
        need(isinstance(sup, str) and sup or isinstance(sup, list) and all(isinstance(x, str) and x for x in sup),
             "supersedes must be a row id or a list of row ids")
        need(rid not in ([sup] if isinstance(sup, str) else sup), "a row cannot supersede itself")
    if spec.get("fix_ref") is not None:
        need(isinstance(spec["fix_ref"], str) and spec["fix_ref"].strip(), "fix_ref must name the fix (commit or path)")
    check_engine_not_sealed(launcher, eng)
    # refinement 1: shape from evidence
    check_shape_evidence(spec, o)
    if o.get("threads"):
        row["declared_threads"] = int(o["threads"])
        row["threads_evidence"] = o.get("threads_evidence") or []
    if spec.get("shape") is not None:
        need(str(spec["shape"]) in SHAPES or re.fullmatch(r"multi-quarter\([2-3]\)", str(spec["shape"])), f"shape must be one of {SHAPES} or multi-quarter(n)")
        row["shape"] = str(spec["shape"])
    row["shape"] = shape_of(row, o)   # recorded: quarter | multi-quarter(n) | host | quiet-host | gpu | gpu-q3
    if row["shape"] in ("host", "quiet-host") and not whole_host_evidence(row):
        ram_host = int(row.get("gib") or 0) > 3 * QUARTER_RAM_GIB and row["shape"] == "host" and spec.get("shape") is None
        need(ram_host, f"shape {row['shape']} needs whole-host evidence: >= {WHOLE_HOST_THREADS} declared threads (found "
                       f"{row.get('declared_threads') or 'none'}{': ' + ', '.join(row.get('threads_evidence') or []) if row.get('threads_evidence') else ''}), "
                       f"a baseline_ref naming the decision-grade baseline / production-serving measurement, or "
                       f"shape_override \"operator: <who> <date>: <why>\"; right-sized: {right_size(row.get('declared_threads'), lane, o.get('gpu_quiet', ''))}")
    if row.get("busy_fraction") is None and row.get("declared_threads"):
        row["busy_fraction"] = round(min(1.0, row["declared_threads"] / claimed_cpus(regions, o.get("claim_cpus"), row["shape"])), 3)
        row["busy_fraction_source"] = "declared_threads"
    atomic_json(ready_path(flags, rid), row)
    return row


def withdrawn_dir(flags): return os.path.join(flags, "ready", ".withdrawn")


def withdraw(flags, rid, reason, log=print):
    """Refinement 5: end a row that will never run. Not running: ready/<id>.json -> ready/.withdrawn/<id>.json, a
    terminal grants/<id>.ended `rc=75 reason=<reason>` (status/queue_status/backlog_gen/dashboard read it as closed),
    and its STOP file touched (an armed poller never starts). Running (open grant): STOP touched, a pending record
    written; the keeper finishes the withdrawal once the grant ends. Nothing is killed or deleted.
    Returns WITHDRAWN | PENDING | ABSENT | TERMINAL."""
    reason = re.sub(r"\s+", "_", str(reason).strip()) or "withdrawn"
    G = os.path.join(flags, "grants")
    if any(os.path.exists(os.path.join(G, rid + t)) for t in (".ended", ".complete")):
        _move_withdrawn(flags, rid)
        return "TERMINAL"
    rp = ready_path(flags, rid)
    d = load_json(rp)
    if not d:
        return "ABSENT"
    sf = resolve_stop_path(d)
    if sf:
        try:
            os.makedirs(os.path.dirname(sf), exist_ok=True)
            open(sf, "a").close()
        except OSError as e:
            log(f"WITHDRAW {rid}: could not touch STOP {sf}: {e}")
    os.makedirs(withdrawn_dir(flags), exist_ok=True)
    if os.path.exists(os.path.join(G, rid + ".grant")):
        atomic_json(os.path.join(withdrawn_dir(flags), rid + ".pending.json"), {"id": rid, "reason": reason, "at": now_iso()})
        log(f"SUPERSEDE-PENDING {rid}: running; STOP touched, withdrawn when its grant ends (reason={reason})")
        return "PENDING"
    os.makedirs(G, exist_ok=True)
    with open(os.path.join(G, rid + ".ended"), "w") as f:
        f.write(f"rc=75 reason={reason} at={now_iso()}\n")
    _move_withdrawn(flags, rid)
    log(f"WITHDRAWN {rid} reason={reason}")
    return "WITHDRAWN"


def _move_withdrawn(flags, rid):
    rp = ready_path(flags, rid)
    if os.path.exists(rp):
        os.makedirs(withdrawn_dir(flags), exist_ok=True)
        os.replace(rp, os.path.join(withdrawn_dir(flags), rid + ".json"))


def finish_withdrawals(flags, log=print):
    """Keeper tick: a pending withdrawal whose grant has ended is completed (manifest moved; the run's own .ended stays)."""
    for pp in glob.glob(os.path.join(withdrawn_dir(flags), "*.pending.json")):
        rec = load_json(pp) or {}
        rid = rec.get("id") or os.path.basename(pp)[:-len(".pending.json")]
        if os.path.exists(os.path.join(flags, "grants", rid + ".grant")):
            continue
        r = withdraw(flags, rid, rec.get("reason") or "withdrawn", log)
        if r != "PENDING":
            os.replace(pp, pp[:-len(".pending.json")] + ".done.json")


def supersede(flags, row, log=print):
    """Refinement 5: publishing a row with `supersedes` withdraws each predecessor (reason=superseded-by:<id>)."""
    sup = row.get("supersedes")
    out = {}
    for pred in ([sup] if isinstance(sup, str) else list(sup or [])):
        if pred and pred != row["id"]:
            out[pred] = withdraw(flags, pred, f"superseded-by:{row['id']}", log)
    return out


def published_line(row, flags):
    return (f"PUBLISHED {row['id']} lane={row['lane']} regions={row['regions']} window_s={row['window_s']} min_window_s={row['min_window_s']} "
            f"gib={row['gib']} ports={row['ports']} result={row['result_path']} ({row['result_format']}) -> {ready_path(flags, row['id'])}")


def legacy_handoff_task(m):
    """The manifest's own handoff_task wins; a bare `<file>.md[:ID]` is normalised to `handoffs/active/<file>.md[:ID]`
    (the publish lint's form). Only a manifest with no task at all falls back to the legacy FILLERS:<id> marker."""
    ht = next((str(m[k]).strip() for k in ("handoff_task", "row", "handoff") if isinstance(m.get(k), str) and m[k].strip()), "")
    if not ht:
        return "FILLERS:" + str(m.get("id"))
    head, sep, tail = ht.partition(":")
    if head.endswith(".md") and "/" not in head:
        return "handoffs/active/" + head + sep + tail
    return ht


def spec_from_legacy(manifest, flags=FLAGS, rewrite_engine=True):
    """Mechanical migration of an epyc.ready.v2 / schema-less manifest to a v3 spec. If the launcher pins an older
    engine, a sibling `<name>.v15.sh` with the engine path replaced is written (new file; the original is untouched)."""
    m = manifest
    L = m.get("launcher")
    lp = L.get("path") if isinstance(L, dict) else L
    need(isinstance(lp, str) and os.path.isfile(lp), "legacy manifest has no readable launcher path")
    o = parse_launcher(lp)
    eng = o["engine"]
    if os.path.basename(eng) != CANONICAL_ENGINE and rewrite_engine:
        new_engine = os.path.join(flags, "bin", "rowflow", CANONICAL_ENGINE)
        text = open(lp, errors="replace").read()
        # every path-ish token ending in filler_runN.sh (literal, $D/engine/..., ${HERE}/...) -> the canonical engine;
        # private engine copies are exactly what the retired manifest stack bound, so they are not carried over
        new_text = re.sub(r"[A-Za-z0-9_$./{}:-]*filler_run\d+\.sh", new_engine, text)
        stem, ext = os.path.splitext(lp)
        np_ = stem + ".v15" + ext
        with open(np_, "w") as f:
            f.write(new_text)
        os.chmod(np_, 0o755)
        lp = np_
    regs = str(m.get("regions") or "")
    lane = "gpu" if "mi210" in regs else "cpu"
    rp = m.get("result_path")
    if not isinstance(rp, str) or not rp:
        rp = os.path.join(str(m.get("scratch_root") or os.path.dirname(lp)), "RESULT-NEEDS-SPEC.jsonl")
    spec = {"id": m.get("id"), "owner": m.get("owner"), "launcher": lp, "lane": lane, "regions": regs or None,
            "result_path": rp, "decision_rule": m.get("decision_rule") or "MIGRATED: decision_rule missing in legacy manifest; owner to fill",
            "estimate_s": int(m.get("estimate_s") or m.get("window_s") or 3600), "handoff_task": legacy_handoff_task(m),
            "priority_rank": m.get("priority_rank", 100), "ram_gib": m.get("ram_gib") or m.get("gib"), "scratch_root": m.get("scratch_root"),
            "min_window_s": o["min_window"]}
    # a ready/<id>.json written by publish() already carries the spec fields a republish needs: keep them
    # (derived/bookkeeping fields - window_s, published_*, publisher, engine, stop_file, workdir, schema, ... - are dropped)
    for k in ("shape", "first_progress_s", "smoke_predicate", "unit_key", "dryrun_native_result", "result_format",
              "ports", "busy_fraction", "budget_gib", "total_units", "scratch_inputs", "notes", "coexist_quiet_host",
              "fix_ref", "baseline_ref", "shape_override"):
        if m.get(k) is not None:
            spec[k] = m[k]
    legacy_class = m.get("admission_class") or m.get("class")
    if legacy_class is not None:
        spec["admission_class"] = legacy_class
    kp = m.get("keep")
    if isinstance(kp, str):
        kp = [x.strip() for x in kp.split(",") if x.strip()]
    if isinstance(kp, list) and kp:
        spec["keep"] = kp
    for k in ("lineage", "lineage_reset", "supersedes"):
        if m.get(k) is not None:
            spec[k] = m[k]
    return {k: v for k, v in spec.items() if v is not None}


# ---------------------------------------------------------------- result units (the filer's format)
def count_units(result_path, fmt, workdir=None):
    paths = glob.glob(result_path) if any(c in result_path for c in "*?[") else ([result_path] if os.path.exists(result_path) else [])
    if fmt.startswith("custom:"):
        r = subprocess.run(["bash", "-c", fmt[len("custom:"):]], cwd=workdir if workdir and os.path.isdir(workdir) else None,
                           capture_output=True, text=True, timeout=60)
        return 1 if r.returncode == 0 else 0
    n = 0
    for p in paths:
        if os.path.isdir(p):  # a directory result: every regular file written under it is one unit
            n += sum(len(fn) for _, _, fn in os.walk(p))
            continue
        try:
            text = open(p, errors="replace").read()
        except OSError:
            continue
        if fmt == "jsonl":
            for l in text.splitlines():
                l = l.strip()
                if l.startswith("{"):
                    try:
                        json.loads(l); n += 1
                    except ValueError:
                        pass
        elif fmt == "json":
            try:
                v = json.loads(text)
            except ValueError:
                continue
            if isinstance(v, list):
                n += len(v)
            elif isinstance(v, dict):
                lst = next((v[k] for k in ("results", "items", "records", "rows", "samples") if isinstance(v.get(k), list)), None)
                n += len(lst) if lst is not None else 1
        elif fmt in ("csv", "tsv"):
            n += max(0, len([l for l in text.splitlines() if l.strip()]) - 1)
        elif fmt == "markdown-table":
            n += len([l for l in text.splitlines() if l.startswith("|") and not re.match(r"^\|[\s:|-]+\|$", l)]) - 1 if "|" in text else 0
            n = max(n, 0)
        else:
            n += len([l for l in text.splitlines() if l.strip()])
    return n


# ---------------------------------------------------------------- first real progress (operator 2026-11-03, session review §3.1)
# A smoke PASSes only when the ACTUAL job makes its first REAL step within first_progress_s (default 300; spec may set it).
# "A JSON appeared" is not progress: 2026-11-03 three rows passed on qualification-only records and their real runs died
# in 9 s, 12 s and 3 s. The contract, in order (no judgment left to the reader):
#   1. spec.smoke_predicate (shell, run in --workdir with the smoke's FILLER_* env + FILLER_SMOKE_T0=<epoch at launch>):
#      exit 0 = progress. It must exit non-0 BEFORE the launch (else it cannot see this run) -> FAIL at once.
#   2. result_format custom:<cmd>: the same rule with <cmd> as the predicate.
#   3. otherwise a NEW real record in result_path (one not present, byte-identical, before the launch) that parses under
#      result_format and is not a placeholder:
#        - a PLACEHOLDER_MARKERS key/value (qualification_only:true, measurement:false, placeholder:true, smoke_only:true)
#          makes a record a placeholder, always;
#        - spec.unit_key given: the record has a non-null, non-empty value at that dotted key (csv/tsv/markdown: that
#          column; text-lines: the line matches unit_key as a regex);
#        - else json/jsonl: a finite number (not a bool) at depth <= 2 under a key outside BOOKKEEPING_KEYS;
#          csv/tsv/markdown-table: a numeric cell in a column outside BOOKKEEPING_KEYS; text-lines: any non-empty line;
#          a result directory: each new file, parsed by its extension (other files: non-empty = real).
FIRST_PROGRESS_S = 300
PLACEHOLDER_MARKERS = (("qualification_only", True), ("measurement", False), ("placeholder", True), ("smoke_only", True))
BOOKKEEPING_KEYS = re.compile(r"(?i)^(?:id|\w*_id|uuid|schema\w*|version|ts|t0?|time|timestamp|epoch|at|\w+_at|started\w*|ended\w*|"
                              r"pid|pgid|ppid|rc|exit\w*|returncode|seq|idx|index|attempt\w*|mtime|size|bytes|port|status|state|phase|"
                              r"ok|\w+_ok|elapsed\w*|wall\w*|duration\w*)$")


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and v not in (float("inf"), float("-inf"))


def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _has_measurement(v, depth=0):
    if _is_num(v):
        return True
    if isinstance(v, dict) and depth < 2:
        return any(_has_measurement(x, depth + 1) for k, x in v.items() if not BOOKKEEPING_KEYS.match(str(k)))
    if isinstance(v, list) and depth < 2:
        return any(_has_measurement(x, depth + 1) for x in v[:1000])
    return False


def _dotted(rec, key):
    for part in str(key).split("."):
        if not isinstance(rec, dict) or part not in rec:
            return None
        rec = rec[part]
    return rec


def record_verdict(rec, unit_key=None):
    """(real, why) for one parsed json/jsonl record (contract above)."""
    if isinstance(rec, dict):
        for k, v in PLACEHOLDER_MARKERS:
            if k in rec and rec[k] is v:
                return False, f"placeholder ({k}: {json.dumps(v)})"
        if unit_key:
            ok = _dotted(rec, unit_key) not in (None, "", [], {})
            return ok, f"unit_key {unit_key} " + ("set" if ok else "missing/empty")
        ok = _has_measurement(rec)
        return ok, "measurement field" if ok else "no numeric field outside the bookkeeping keys"
    if unit_key:
        return False, f"not an object, so no unit_key {unit_key}"
    ok = _is_num(rec) or (isinstance(rec, list) and _has_measurement(rec))
    return ok, "bare number" if ok else "bare non-numeric value"


def _table_records(lines, sep, unit_key):
    """[(text, real, why)] per data row of a csv/tsv/markdown table (first row = header)."""
    if not lines:
        return []
    hdr = [h.strip() for h in lines[0].split(sep)]
    out = []
    for l in lines[1:]:
        row = dict(zip(hdr, [c.strip() for c in l.split(sep)]))
        if unit_key:
            real = bool(row.get(unit_key))
            why = f"column {unit_key} " + ("set" if real else "missing/empty")
        else:
            real = any(not BOOKKEEPING_KEYS.match(h) and _is_num(_num(c)) for h, c in row.items())
            why = "numeric cell" if real else "no numeric cell outside the bookkeeping columns"
        out.append((l, real, why))
    return out


def _file_records(p, fmt, unit_key):
    try:
        text = open(p, errors="replace").read()
    except OSError:
        return []
    recs = []
    if fmt in ("jsonl", "json"):
        vals = []
        if fmt == "jsonl":
            for l in text.splitlines():
                if l.strip():
                    try:
                        vals.append(json.loads(l))
                    except ValueError:
                        pass
        else:
            try:
                v = json.loads(text)
            except ValueError:
                return []
            lst = v if isinstance(v, list) else None
            if isinstance(v, dict):
                lst = next((v[k] for k in ("results", "items", "records", "rows", "samples") if isinstance(v.get(k), list)), None)
            vals = lst if lst is not None else [v]
        for v in vals:
            real, why = record_verdict(v, unit_key)
            recs.append((json.dumps(v, sort_keys=True), real, why))
    elif fmt in ("csv", "tsv"):
        recs = _table_records([l for l in text.splitlines() if l.strip()], "," if fmt == "csv" else "\t", unit_key)
    elif fmt == "markdown-table":
        rows_ = [l.strip().strip("|") for l in text.splitlines() if l.startswith("|") and not re.match(r"^\|[\s:|-]+\|$", l)]
        recs = _table_records(rows_, "|", unit_key)
    else:
        rx = re.compile(unit_key) if unit_key else None
        for l in text.splitlines():
            if l.strip():
                hit = bool(rx.search(l)) if rx else True
                recs.append((l, hit, "non-empty line" if not rx else f"{'matches' if hit else 'does not match'} unit_key /{unit_key}/"))
    return [(p + "\0" + fp, real, why) for fp, real, why in recs]


def result_records(result_path, fmt, unit_key=None):
    """Every record now in result_path: [(fingerprint, real, why)]. A directory result: each regular file under it is
    parsed by its extension (guess_format); any other file is one record, real when non-empty."""
    paths = glob.glob(result_path) if any(c in result_path for c in "*?[") else ([result_path] if os.path.exists(result_path) else [])
    out = []
    for p in paths:
        if not os.path.isdir(p):
            out += _file_records(p, fmt, unit_key)
            continue
        for root, _, fns in os.walk(p):
            for fn in sorted(fns):
                fp = os.path.join(root, fn)
                f2 = guess_format(fp)
                if f2 in ("json", "jsonl", "csv", "tsv", "markdown-table"):
                    out += _file_records(fp, f2, unit_key)
                    continue
                try:
                    sz = os.path.getsize(fp)
                    out.append((fp + "\0" + sha256(fp), sz > 0, "non-empty file" if sz else "empty file"))
                except OSError:
                    continue
    return out


class FirstProgress:
    """The smoke's progress probe. Construct it BEFORE the launch (baseline), then .check() -> (progress, detail)."""

    def __init__(self, d, result_path, fmt, env, workdir=None):
        self.result_path, self.fmt, self.env = result_path, fmt, env
        self.workdir = workdir if workdir and os.path.isdir(workdir) else None
        self.unit_key = d.get("unit_key")
        self.pred = d.get("smoke_predicate") or (fmt[len("custom:"):] if fmt.startswith("custom:") else None)
        self.kind = "smoke_predicate" if d.get("smoke_predicate") else ("result_format custom:" if self.pred else "record")
        self.base, self.placeholders, self.stale = {}, [], False
        if self.pred:
            self.stale = self._pred()
        else:
            for fp, _, _ in result_records(result_path, fmt, self.unit_key):
                self.base[fp] = self.base.get(fp, 0) + 1

    def _pred(self):
        try:
            return subprocess.run(["bash", "-c", self.pred], cwd=self.workdir, env=self.env, stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, timeout=60).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    def check(self):
        if self.pred:
            return (True, f"{self.kind} exited 0") if self._pred() else (False, f"{self.kind} still exits non-0")
        seen = dict(self.base)
        self.placeholders = []
        for fp, real, why in result_records(self.result_path, self.fmt, self.unit_key):
            if seen.get(fp, 0) > 0:
                seen[fp] -= 1
            elif real:
                return True, f"new record in {self.result_path} ({why})"
            else:
                self.placeholders.append(why)
        return False, "no new real record"

    def what(self):
        """What never happened, for the one-line FAIL."""
        if self.pred:
            return f"{self.kind} `{self.pred[:80]}` never exited 0"
        ph = f"; {len(self.placeholders)} new record(s) ignored: {self.placeholders[0]}" if self.placeholders else ""
        return f"no unit in {self.result_path} ({self.fmt}): no new real record{ph}"

    def fix(self, n):
        if self.pred:
            return (f"fix: make the job reach the step {self.kind} tests within first_progress_s={n} (or raise first_progress_s "
                    "in the spec), then re-run publish_row.py <spec.json>")
        return (f"fix: make the job write its first measured record to {self.result_path} within first_progress_s={n} (a numeric "
                "field outside the bookkeeping keys, no qualification_only/measurement:false), or declare smoke_predicate or "
                "unit_key in the spec, then re-run publish_row.py <spec.json>")


# ---------------------------------------------------------------- lane state (one snapshot per tick)
QUARTERS = ("q0", "q1", "q2", "q3")
GPU = "gpu-quiet"
REGIONS = QUARTERS + (GPU,)
RAM_MARGIN_GIB = 64          # earlyoom fires at 40 GiB available
UNDERUSED_PCT = 5.0
UNDERUSED_S = 600
ALERT_REPEATS = 3


def rl_status():
    """region -> (state, holder-tag) for q0..q3 and gpu-quiet; state 'free' or the lock state (HELD/EXCL/SHRD)."""
    try:
        st = subprocess.run([RL, "status"], capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.TimeoutExpired):
        return {}
    out = {}
    for l in st.splitlines():
        b = l.split()
        if len(b) > 1 and b[0] in REGIONS and b[0] not in out:
            out[b[0]] = (b[1], b[-1] if len(b) > 2 else "")
    return out


def quarters_of(regions, fold=False):
    """qN names touched by a region string. fold=True maps SMT siblings (96-191) onto their quarter (region-lock folds)."""
    qs = set()
    for tok in str(regions).split(","):
        tok = tok.strip()
        if re.fullmatch(r"q[0-3]", tok):
            qs.add(tok)
        elif re.fullmatch(r"\d+(-\d+)?", tok):
            a, b = (tok.split("-") + [tok])[:2]
            for c in range(int(a), min(int(b), 191) + 1):
                if c < 96 or fold:
                    qs.add(f"q{(c % 96) // 24}")
    return qs
def ws58_cpus(regions):
    """The cpu part of a regions string ('mi210_0,184-191' -> '184-191'), exported as WS58_REGIONS."""
    return ",".join(t for t in str(regions or "").split(",") if re.fullmatch(r"\d+(-\d+)?", t.strip()))




CORES = tuple(f"c{n}" for n in range(96))   # ws58 2026-11-02 sub-quarter packing: one token per physical core


THREADS = tuple(f"t{n}" for n in range(96, 192))   # ws58 2026-11-02 18:30Z: one token per SMT-sibling thread
GRANT_CPUS_MARKER = "GRANT_CPUS"   # an engine containing it locks a GPU grant's own cpus (not --claim-cpus): see engine_grant_cpus


def qcores(q):
    lo = int(q[1]) * 24
    return {f"c{n}" for n in range(lo, lo + 24)}


def qthreads(q, n=16):
    """The SMT siblings a whole-quarter grant runs on: the engine's quarter list is a-b,s-(s+15), so the last 8 siblings
    of a quarter (q3: 184-191, the MI210 host threads) stay outside it. n=24: every sibling (a foreign region-lock hold)."""
    lo = 96 + int(q[1]) * 24
    return {f"t{k}" for k in range(lo, lo + n)}


def expand(tokens):
    """A whole quarter also holds its 24 core tokens and the 16 sibling threads it runs on, so it is free only when no
    sub-quarter row holds any of them. Idempotent."""
    out = set(tokens)
    for t in tokens:
        if t in QUARTERS:
            out |= qcores(t) | qthreads(t)
    return out


def compress(tokens):
    """Grant/log form: core/thread tokens of a whole quarter folded away; partial cores/threads kept (c48,t144,...)."""
    qs = {t for t in tokens if t in QUARTERS}
    cov = set().union(*[qcores(q) | qthreads(q) for q in qs]) if qs else set()
    return sorted(t for t in tokens if t not in cov)


def cpu_tokens(cpus, gpu_threads=False):
    """Tokens of a cpu list: a quarter covered fully -> qN, partly -> its core tokens plus the sibling threads a
    sub-quarter grant pins (cN + t(N+96)). gpu_threads=True (a GPU row's explicit host threads): siblings are thread
    tokens of their own (184-191 -> t184..t191), never folded onto their core / quarter."""
    cores, sibs = set(), set()
    for tok in str(cpus or "").split(","):
        tok = tok.strip()
        if re.fullmatch(r"\d+(-\d+)?", tok):
            a, b = (tok.split("-") + [tok])[:2]
            for c in range(int(a), min(int(b), 191) + 1):
                if c >= 96 and gpu_threads:
                    sibs.add(c)
                else:
                    cores.add(c % 96)
    out = {f"t{c}" for c in sibs}
    for q in QUARTERS:
        cs = {c for c in cores if f"q{c // 24}" == q}
        if len(cs) >= 24:
            out.add(q)
        else:
            out |= {f"c{c}" for c in cs} | {f"t{c + 96}" for c in cs}
    return out


def engine_grant_cpus(o):
    """True when the row's engine snapshot locks a GPU grant's own cpus (content check, never a path/version guess)."""
    try:
        with open(o.get("engine") or "", errors="replace") as f:
            return GRANT_CPUS_MARKER in f.read()
    except OSError:
        return False


def grant_cpus(regions):
    """The exact cpu list a grant's regions pin (cpus= field): explicit cpus as given, qN as the engine's a-b,s-(s+15)."""
    out = []
    for t in str(regions or "").split(","):
        t = t.strip()
        if re.fullmatch(r"\d+(-\d+)?", t):
            out.append(t)
        elif re.fullmatch(r"q[0-3]", t):
            a = int(t[1]) * 24
            out.append(f"{a}-{a + 23},{a + 96}-{a + 111}")
    return ",".join(out)


def tokens_cpus(tokens):
    """The exact cpu list (cores + their SMT siblings) of a sub-quarter option."""
    cs = sorted(int(t[1:]) for t in tokens if re.fullmatch(r"c\d+", t))
    return ",".join(str(c) for c in cs + [c + 96 for c in cs])


def cpu_list(q):
    lo = int(q[1]) * 24
    return f"{lo}-{lo + 23}"


def open_grants(flags):
    """Every grants/<id>.grant: {id, regions, holds, start, end, pid, dryrun, started}. holds = the regions the grant
    books (written by the allocator as holds=...; older grants: derived from regions)."""
    out = []
    for g in glob.glob(os.path.join(flags, "grants", "*.grant")):
        rid = os.path.basename(g)[:-6]
        first = head1(g)
        kv = dict(re.findall(r"(\w+)=(\S+)", first))
        regions = kv.get("regions", "")
        holds = set(kv["holds"].split(",")) if kv.get("holds") else quarters_of(regions) | ({GPU} if "mi210" in regions else set())
        holds = expand(holds)
        run = load_json(running_path(flags, rid))
        arm = load_json(armed_path(flags, rid))
        dry = bool(run)
        pid = (run or arm or {}).get("pid")
        started = False
        try:
            mt = os.path.getmtime(g)
            logp = os.path.join(dry_dir(flags, rid), "launcher.out" if dry else "poller.out")
            if os.path.getmtime(logp) >= mt - 1:
                started = any("START regions=" in l for l in tail(logp, 400))
        except OSError:
            pass
        out.append({"id": rid, "regions": regions, "holds": holds, "start": kv.get("start"), "end": kv.get("end"), "pid": pid,
                    "dryrun": dry, "started": started, "path": g})
    return out


SHAPES = ("quarter", "multi-quarter", "host", "quiet-host", "gpu", "gpu-q3")
WHOLE_HOST_THREADS = 48   # operator 2026-11-05: production CPU serving across all NUMA nodes (npd1-step5: -t 48 over 0-95)
GPU_Q3_TOKENS = frozenset({GPU, "q3"} | {f"t{k}" for k in range(184, 192)})   # gpu-quiet + q3 cores + 184-191
QUARTER_RAM_GIB = 256   # a quarter's share of the bookable RAM (1069 GiB / 4, rounded): a bigger model is multi-quarter


def shape_of(d, o=None):
    """quarter | multi-quarter(n) | host | quiet-host | gpu - the spec's `shape` wins; else derived from the launcher's
    claim (claim_cpus), ram_gib, gpu_quiet and role/class (operator 2026-11-01: heavy rows and timing baselines that
    need every quarter plus the GPU idle must be scheduled explicitly, never squeezed onto a quarter)."""
    sp = str(d.get("shape") or "").strip()
    if sp:
        return sp
    regs = str(d.get("regions") or "")
    if o is None:
        try:
            o = parse_launcher(d["launcher"]["path"])
        except (Refused, OSError, StopIteration, ValueError, KeyError):
            o = {}
    cls = o.get("class", "gpu" if "mi210" in regs else "cpu")
    if "mi210" in regs or cls in ("gpu", "cpu+gpu"):
        # refinement 2 (operator 2026-11-05: "a GPU timing run doesn't need a quiet host ... It just needs a quiet q3"):
        # a gpu-quiet exclusive row whose claim books >= 2 quarters is gpu-q3 unless it carries whole-host evidence
        cc = o.get("claim_cpus") or ""
        books_claim = not (cls == "gpu" and "mi210" in regs and (o.get("nofold") or engine_grant_cpus(o)))
        if o.get("gpu_quiet") == "exclusive" and books_claim and len(quarters_of(cc, fold=True)) >= 2:
            return "quiet-host" if whole_host_evidence(d) else "gpu-q3"
        return "gpu"
    if o.get("gpu_quiet") == "exclusive" and len(quarters_of(o.get("claim_cpus") or "0-95", fold=True)) >= 4:
        return "quiet-host"   # ws58 2026-11-01: gpu-quiet on a quarter claim = that quarter + GPU idle, not the whole host
    nq = len(quarters_of(o.get("claim_cpus") or regs, fold=True)) if regs not in ("any-cpu-quarter",) and not regs.startswith("any-of") else 1
    nq = max(nq, -(-int(d.get("gib") or 0) // QUARTER_RAM_GIB) if int(d.get("gib") or 0) > QUARTER_RAM_GIB else 1)
    if nq >= 4:
        return "host"
    return f"multi-quarter({nq})" if nq >= 2 else "quarter"


def row_shape(d):
    """(options, bench): the alternative region sets (frozensets over q0..q3/gpu-quiet) a row must hold at once, derived
    from the row's regions AND its launcher's region-lock claim (static parse; the engine's own defaults). bench = a
    timing row (keeps off q3 while a GPU grant is open). A `host` / `quiet-host` shape books every quarter (+ GPU)."""
    regs = str(d.get("regions") or "")
    try:
        o = parse_launcher(d["launcher"]["path"])
    except (Refused, OSError, StopIteration, ValueError, KeyError):
        o = {}
    if shape_of(d, o) == "gpu-q3":   # refinement 2: gpu-quiet + q3 + 184-191; q0-q2 stay free
        return [frozenset(compress(expand(set(GPU_Q3_TOKENS))))], True
    extra = set()
    cls = o.get("class", "gpu" if "mi210" in regs else "cpu")
    if "mi210" in regs or cls in ("gpu", "cpu+gpu"):
        extra.add(GPU)
    gq, cc, nofold = o.get("gpu_quiet", ""), o.get("claim_cpus", ""), o.get("nofold", False)
    if gq == "exclusive":
        extra.add(GPU)
        if not cc and cls == "gpu":
            cc = "0-95"
    gpu_row = cls == "gpu" and "mi210" in regs
    # ws58 2026-11-02 18:30Z: a GPU row holds gpu-quiet + ONLY the cpus its regions name (184-191 -> threads t184..t191,
    # free beside a whole-q3 / host row; 0-23 -> q0). Its launcher's --claim-cpus books cpus only while the engine
    # snapshot still locks that claim (pre-GRANT_CPUS engines; a --no-fold-siblings / claim-less one locks no cpu).
    legacy_claim = gpu_row and cc and not nofold and not engine_grant_cpus(o)
    if gpu_row and not legacy_claim:
        extra |= cpu_tokens(ws58_cpus(regs) or "184-191", gpu_threads=True)
        cc = ""
    elif cc and not (nofold and cls == "gpu"):
        extra |= cpu_tokens(cc)   # ws58 sub-quarter: a claim covering < 24 cores of a quarter holds only those cores
    if not cc and cls == "cpu" and ws58_cpus(regs) and "mi210" not in regs:
        rt = cpu_tokens(ws58_cpus(regs))
        if not (rt & set(QUARTERS)):
            extra |= rt; cc = ws58_cpus(regs)   # concrete sub-quarter regions (e.g. 0-3): only those cores
    sub = cc and not (extra & set(QUARTERS)) and any(t in CORES for t in extra)
    if sub or (cls == "gpu" and "mi210" in regs):
        bases = [set()]   # the claim pins the cpus: no extra quarter (whole-quarter/host shapes still add theirs below)
    elif regs == "any-cpu-quarter":
        bases = [{q} for q in QUARTERS]
    elif regs.startswith("any-of"):
        bases = [{x.strip()} for x in regs[len("any-of"):].split(",") if re.fullmatch(r"q[0-3]", x.strip())]
    else:
        bases = [quarters_of(regs)]
    shape = shape_of(d, o)
    if shape == "quiet-host":
        extra |= set(REGIONS)
    elif shape == "host":
        extra |= set(QUARTERS)
    elif shape.startswith("multi-quarter("):
        n = int(shape[len("multi-quarter("):-1] or 2)
        base_q = set().union(*[b for b in bases]) | {q for q in extra if q in QUARTERS}
        if len(base_q) < n:   # RAM-derived width: any n quarters, as alternatives
            bases = [set(c) for c in __import__("itertools").combinations(QUARTERS, n)]
    opts = []
    for b in bases:
        fs = frozenset(compress(expand(b | extra)))
        if fs and fs not in opts:
            opts.append(fs)
    return opts, (gq == "exclusive" or o.get("role") == "bench")


def grant_regions(d, option):
    """The regions= string of a grant for `option`: the row's own regions when concrete, else the chosen quarter."""
    regs = str(d.get("regions") or "")
    if "mi210" in regs:
        return regs
    qs = sorted(q for q in option if q in QUARTERS)
    if not qs and any(t in CORES for t in option):
        return tokens_cpus(option)   # sub-quarter grant: the exact cpu list
    if regs == "any-cpu-quarter" or regs.startswith("any-of"):
        return cpu_list(qs[0]) if qs else regs
    return regs


DRAIN_AFTER_S = 3600      # a host / multi-quarter row that waited this long drains the host (age boost; never preempts)
DRAIN_MAX_WAIT_S = 3600  # ws58 hotfix: drain only when the host frees within 1 h
DRAIN_UNKNOWN_S = 1800    # drain target when the busy regions carry no grant end (foreign hold): backfill <= 30 min
URGENT_RANK = 10          # ws58 2026-11-02: an explicit operator priority_rank below this beats lane starvation (21:25Z
                          # four rank-1 pilots lost the host to a rank-30 whole-host row that was promoted as a drain)


DRAIN_MIN_BUSY = 0.5      # operator 2026-11-03 (session review 3.1): a row whose spec says it keeps < half its claim busy
                          # (a ~4%-busy row) is never promoted to a host/quiet-host drain; it still takes free regions


COEXIST_TAG = "gitnexus-q3"
QUIET_SHAPES = ("quiet-host", "gpu-q3")   # shapes whose q3 hold leaves q3 cores 72-87 to coexist rows
COEXIST_MAX_BUSY = 0.1
GPU_HOST_THREADS = frozenset(range(184, 192))   # filler_run15 GPUTHR default / gpu-quiet reserved MI210 host threads
# q3 cores whose SMT siblings are NOT the MI210 host threads (72-87 -> siblings 168-183): a sub-quarter grant pins both
COEXIST_Q3 = frozenset({f"c{n}" for n in range(72, 88)} | {f"t{n}" for n in range(168, 184)})


def is_coexist(d):
    """Marked (coexist_quiet_host) OR by evidence (operator 2026-11-05: "as long as gitnexus doesn't touch the GPU's mgmt
    threads on q3 it can still run on q3 without impacting a timing run on the GPU"): a cpu row whose concrete regions
    are q3 cores 72-87 only (siblings 168-183, never 184-191) and whose declared busy_fraction <= COEXIST_MAX_BUSY.
    11:00Z: nine such -sq3 rows published before the marker existed sat grantable beside npd1-step5's quiet-host hold."""
    d = d or {}
    if d.get("coexist_quiet_host") == COEXIST_TAG:
        return True
    if d.get("lane") != "cpu" or "mi210" in str(d.get("regions") or ""):
        return False
    cpus = ws58_cpus(d.get("regions"))
    if not cpus or cpus != str(d.get("regions") or "").strip():
        return False
    bf = d.get("busy_fraction")
    if not isinstance(bf, (int, float)) or isinstance(bf, bool) or not 0 <= bf <= COEXIST_MAX_BUSY:
        return False
    toks = cpu_tokens(cpus)
    return bool(toks) and toks <= COEXIST_Q3


def check_coexist(spec, o, regions):
    """Publish gate for coexist_quiet_host (operator 2026-11-05): gitnexus single-worker q3 rows only."""
    need(spec.get("coexist_quiet_host") == COEXIST_TAG, f"coexist_quiet_host must be {COEXIST_TAG!r}")
    need(spec["lane"] == "cpu" and o["class"] == "cpu", "coexist_quiet_host needs lane cpu / engine --class cpu")
    bf = spec.get("busy_fraction")
    need(isinstance(bf, (int, float)) and not isinstance(bf, bool) and 0 <= bf <= COEXIST_MAX_BUSY,
         f"coexist_quiet_host needs busy_fraction <= {COEXIST_MAX_BUSY}")
    need(o.get("gpu_quiet") in ("", "none") and not o.get("claim_cpus") and not o.get("nofold"),
         "coexist_quiet_host launcher must claim exactly its granted cpus (no --claim-cpus/--gpu-quiet/--no-fold-siblings)")
    cpus = ws58_cpus(regions)
    need(cpus and cpus == str(regions).strip(), "coexist_quiet_host regions must be a concrete cpu list (e.g. 72-73)")
    raw = set()
    for t in cpus.split(","):
        a, b = (t.split("-") + [t])[:2]
        raw |= set(range(int(a), int(b) + 1))
    need(not (raw & GPU_HOST_THREADS), "coexist_quiet_host cpus touch the MI210 host threads 184-191")
    toks = cpu_tokens(cpus)
    need(toks and toks <= COEXIST_Q3, "coexist_quiet_host cpus must be q3 cores 72-87 (siblings 168-183) only; "
         "cores 88-95 pin the MI210 host threads 184-191")
    guard = os.path.join(o.get("workdir") or "", "gitnexus-guard.py")
    try:
        gtext = open(guard, errors="replace").read()
    except OSError:
        gtext = ""
    need("admit_subquarter_q3" in gtext and "--workers" in (o.get("cmd") or "") + open(spec["launcher"]).read() + _job_text(o),
         f"coexist_quiet_host is for single-worker gitnexus rows: {guard} must carry the q3 sub-quarter route and the job --workers 1")


def _job_text(o):
    m = re.search(r"(/\S+\.py)", o.get("cmd") or "")
    try:
        return open(m.group(1).strip("'\""), errors="replace").read() if m else ""
    except OSError:
        return ""


def check_busy_fraction(spec):
    """Publish gate (operator 2026-11-03): optional spec busy_fraction must be a number in 0..1."""
    bf = spec.get("busy_fraction")
    need(bf is None or (isinstance(bf, (int, float)) and not isinstance(bf, bool) and 0 <= bf <= 1),
         f"busy_fraction {bf!r} must be a number 0..1 (the share of its claimed cpus the job keeps busy, e.g. 0.9); "
         f"omit it when unknown (= 1.0)")


def whole_host_evidence(d):
    """Refinement 1: what earns a host / quiet-host shape - >= WHOLE_HOST_THREADS declared threads, a baseline_ref naming
    the decision-grade baseline / production-serving measurement it reproduces, or an operator shape_override."""
    d = d or {}
    try:
        if int(d.get("declared_threads") or 0) >= WHOLE_HOST_THREADS:
            return True
    except (TypeError, ValueError):
        pass
    return bool(str(d.get("baseline_ref") or "").strip()) or bool(str(d.get("shape_override") or "").strip())


def check_engine_not_sealed(launcher, eng):
    """sq3fix 2026-11-05: a job packet must not pin the live rowflow engine's digest. kpf17/kpf41 -sq3 sealed
    filler_run15.sh's sha256 at build time; the engine was redeployed (2134ef303) while their COEXIST grants waited on
    GLOBAL.q3, and both jobs asserted on the new digest at start (rc=1, empty out/). The engine is loop-plane code that is
    redeployed under running rows by design; the dry run already records engine_sha256 in PASS.json. Refuse a packet
    file in the launcher's directory that names the engine digest."""
    try:
        with open(eng, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return
    d = os.path.dirname(launcher)
    for root, dirs, files in os.walk(d):
        dirs[:] = [x for x in dirs if x not in ("__pycache__", ".git", "out", "source")]
        for fn in files:
            p = os.path.join(root, fn)
            try:
                if os.path.getsize(p) > (4 << 20):
                    continue
                with open(p, "rb") as f:
                    data = f.read()
            except OSError:
                continue
            need(digest.encode() not in data,
                 f"{p} pins the rowflow engine digest ({os.path.basename(eng)} sha256 {digest[:12]}...): the engine is "
                 "redeployed under queued rows, so a sealed engine digest fails the job at start; drop the engine from "
                 "the packet's seals (PASS.json records engine_sha256)")


def check_shape_evidence(spec, o):
    """Publish gate for the whole-host evidence fields themselves."""
    br = spec.get("baseline_ref")
    if br is not None:
        need(isinstance(br, str) and br.strip(), "baseline_ref must name the decision-grade baseline / production-serving measurement")
        if br.startswith("/"):
            need(os.path.exists(br), f"baseline_ref {br} does not exist")
    so = spec.get("shape_override")
    if so is not None:
        need(isinstance(so, str) and re.match(r"^operator:\s*\S+.*\d{4}-\d{2}-\d{2}.*:\s*\S", so),
             "shape_override must read \"operator: <who> <YYYY-MM-DD>: <why>\"")


def right_size(threads, lane, gpu_quiet=""):
    if lane == "gpu" or gpu_quiet == "exclusive":
        return "gpu-q3"
    if not threads:
        return "quarter (declare the job's threads: -t/--threads/--workers/OMP_NUM_THREADS/taskset)"
    n = -(-int(threads) // 24)
    return "quarter" if n <= 1 else f"multi-quarter({min(n, 3)})"


def claimed_cpus(regions, claim, shape):
    if shape in ("host", "quiet-host"):
        return 96
    n = count_cpus(claim) or (0 if "mi210" in str(regions) else count_cpus(ws58_cpus(regions)))
    if n:
        return n
    if shape.startswith("multi-quarter("):
        return 24 * int(shape[len("multi-quarter("):-1] or 2)
    return 24


def row_busy(d):
    """A row's / candidate's busy_fraction as a float in 0..1; absent or invalid = unknown = 1.0 (never demoted)."""
    b = (d or {}).get("busy_fraction")
    try:
        b = float(b)
    except (TypeError, ValueError):
        return 1.0
    return b if 0.0 <= b <= 1.0 and not isinstance((d or {}).get("busy_fraction"), bool) else 1.0


def row_rank(d):
    """A row's priority_rank as a float; absent/blank -> 100. (`or 100` turned an explicit rank 0 into 100.)"""
    r = (d or {}).get("priority_rank")
    try:
        return 100.0 if r is None or r == "" else float(r)
    except (TypeError, ValueError):
        return 100.0


def plan_order(c):
    """Candidate order. Rows that failed to arm/launch since their PASS (arm_fails > 0) go LAST, behind every healthy
    row, so they can never idle a region another row could take (2026-11-03 session review item 7: a rank-7 row that
    could not arm was planned first every tick and nothing else was placed); they are still retried when nothing
    healthy fits, so they reach MAX_FAILS and park instead of lingering forever. Then urgent rows (rank < URGENT_RANK)
    by rank; within a rank, and for every other row, the starved lane (fewest live rows) goes first, then rank, then a
    grantable row before a dry run."""
    r = float(c["rank"])
    return (1 if int(c.get("arm_fails") or 0) > 0 else 0, min(r, URGENT_RANK), c["lane_count"], r, 0 if c["kind"] == "grant" else 1, c["id"])


def placeable(x, free, ram, gpu_grant_open=False, held_ports=()):
    """x could be placed on this snapshot: an option fits the free regions and RAM, its ports are not held, and it is
    not failing to arm (cand["arm_fails"] > 0: its last arming/launch attempts since the PASS failed)."""
    if int(x.get("arm_fails") or 0) > 0:
        return False
    if {int(p) for p in held_ports} & {int(p) for p in (x.get("ports") or [])}:
        return False
    return bool(_fits(x, free, ram, gpu_grant_open))


def drain_blocker(c, pending, free=None, ram=None, gpu_grant_open=False, held_ports=()):
    """The best-ranked pending row (strictly better rank than c) that wants any region c's drain would hold, or None.
    A drain is never set for c while such a row is runnable: rank decides who gets the regions when they free.
    ws58 2026-11-03: with a snapshot (free, ram) only a blocker that is placeable THIS tick and not failing to arm
    holds c (yarn-e1-a2-gpu, rank 7, failed to arm 172 times and held every quiet-host row for 7 h on an idle host)."""
    need = set().union(*c["options"]) if c["options"] else set()
    better = [x for x in pending if x is not c and float(x["rank"]) < float(c["rank"]) and any(o & need for o in x["options"])]
    if c.get("shape") in QUIET_SHAPES:   # COEXIST: a coexist row never holds a quiet-host drain back
        better = [x for x in better if not x.get("coexist")]
    if free is not None:
        better = [x for x in better if placeable(x, free, ram, gpu_grant_open, held_ports)]
    return min(better, key=plan_order) if better else None


def _avail(c, free, cx=frozenset(), qh=frozenset()):
    """COEXIST (operator 2026-11-05): the tokens c may take. cx = tokens held by coexist rows, qh = tokens held by
    quiet-host rows. A coexist row also takes COEXIST_Q3 cores a quiet-host row holds (never another coexist row's); a
    quiet-host row treats coexist-held cores as free, and q3 as free when its only other holders are coexist rows."""
    if c.get("coexist"):
        return set(free) | ((set(qh) & COEXIST_Q3) - set(cx))
    if c.get("shape") in QUIET_SHAPES and cx:
        f2 = set(free) | (set(cx) & COEXIST_Q3)
        if expand({"q3"}) - {"q3"} <= f2:
            f2.add("q3")
        return f2
    return set(free)


def _fits(c, free, ram, gpu_grant_open):
    opts = [o for o in c["options"] if o and o <= free]
    if c.get("bench") and gpu_grant_open:
        opts = [o for o in opts if not (o & expand({"q3"}))]
    if ram - float(c.get("gib") or 0) < RAM_MARGIN_GIB:
        return []
    return opts


def own_block(h, free, ram, gpu_grant_open, ports):
    """Why better-ranked row h cannot be placed this tick when the cause is its OWN constraint (arming failures, a held
    port, RAM, the timing-row q3 rule), or None when it is blocked only because some of its regions are busy."""
    if int(h.get("arm_fails") or 0) > 0:
        return f"failing to arm (arm_fails={int(h.get('arm_fails') or 0)})"
    clash = ports & {int(x) for x in (h.get("ports") or [])}
    if clash:
        return f"port {','.join(map(str, sorted(clash)))} held"
    if ram - float(h.get("gib") or 0) < RAM_MARGIN_GIB:
        return f"RAM: {h.get('gib')} GiB would leave {ram - float(h.get('gib') or 0):.0f} GiB < {RAM_MARGIN_GIB} margin"
    if any(o and o <= free for o in h["options"]):
        return "timing row keeps off q3 while a GPU grant is open"   # fits on regions, filtered only by the bench rule
    if row_busy(h) < DRAIN_MIN_BUSY:   # operator 2026-11-03: a mostly idle row takes only regions that are free anyway
        return f"busy_fraction {row_busy(h):g} < {DRAIN_MIN_BUSY:g}: runs only when its regions are free"
    return None


def rank_reservation(c, pending, free, ram, gpu_grant_open, ports, now, grant_ends, drain):
    """ws58 2026-11-04 (rank inversion): the regions c may NOT take because a strictly better-ranked pending row that
    cannot be placed yet needs them and is blocked only by busy regions that free within DRAIN_MAX_WAIT_S (T = latest
    running-grant end); c may still take them when it ends by T. Returns (reserved regions, [(h, T)], [(h, reason)]) -
    the holds that bind c, and the better rows that bind nothing because they are blocked by their own constraint."""
    reserved, holds, skips = set(), [], []
    later = [float(e) for e in grant_ends if float(e) > now]
    dur = float(c.get("estimate_s") or c.get("window_s") or 0)
    for h in pending:
        if h is c or h is drain or float(h["rank"]) >= float(c["rank"]) or _fits(h, free, ram, gpu_grant_open):
            continue
        if c.get("coexist") and h.get("shape") in QUIET_SHAPES:
            continue   # COEXIST: a waiting quiet-host row never reserves q3 against a coexist row
        need = set().union(*h["options"]) if h["options"] else set()
        if not any(o & need for o in c["options"]):
            continue
        why = own_block(h, free, ram, gpu_grant_open, ports)
        if why is None:
            if not later:
                why = "needs busy regions with no grant end (foreign hold)"
            elif max(later) - now > DRAIN_MAX_WAIT_S:
                why = f"needs busy regions until {dt.datetime.fromtimestamp(max(later), dt.timezone.utc):%H:%MZ} (> {DRAIN_MAX_WAIT_S}s)"
        if why is not None:
            skips.append((h, why))
            continue
        T = max(later)
        if now + dur > T:
            reserved |= need
            holds.append((h, T))
    return reserved, holds, skips


def plan(free, cands, ram_gib, gpu_grant_open=False, now=None, grant_ends=(), quiet_ok=True, held_ports=(), drain_prev=None,
         coexist_held=(), quiet_held=()):
    """PURE. One snapshot -> assignments. free: free regions; cands: [{id, kind: grant|dryrun, lane, rank, lane_count, gib,
    bench, options: [frozenset], shape?, since? (epoch the row became runnable), window_s? (how long it would hold)}];
    ram_gib: MemAvailable now; grant_ends: end epochs of the running grants; quiet_ok: quiet-host rows allowed now (window knob).
    Order: plan_order (rank < URGENT_RANK first by rank, then starved lane, then rank, then a grantable row before a dry
    run). Fixpoint: as long as
    any pending candidate fits the remaining free regions and RAM it is placed, so no region stays idle while a fitting
    row waits. Never hands a region twice.
    DRAIN (never preempt): the top quiet-host row, or the top multi-quarter/host row that has waited DRAIN_AFTER_S, that
    cannot be placed now sets T = the latest end among the running grants; only rows that END before T are backfilled, so
    nothing idles while the host drains and nothing delays T; at T its whole shape is free and it is placed first.
    A row is neither promoted nor drained for while a better-ranked pending row that is placeable this tick and not
    failing to arm wants any of its regions (drain_blocker); plan.drain_held = [(row, blocker)] names those rows for the log.
    BUSY (operator 2026-11-03): a row with busy_fraction < DRAIN_MIN_BUSY (unset = 1.0) is never promoted or drained
    for; it is placed only when its regions are free anyway. plan.drain_lowbusy names those rows for the log.
    PORTS (ws58 2026-11-02): a candidate whose cand["ports"] meet held_ports (running grants) or a port placed this tick
    waits; two rows declaring the same port are never co-scheduled.
    COEXIST (operator 2026-11-05): coexist_held / quiet_held = tokens held by running coexist (cand["coexist"]) /
    quiet-host grants; see _avail.
    Returns (assigned [(cand, option)], idle {region: reason}, pending); plan.last_drain = (cand, T) or None."""
    now = time.time() if now is None else now
    cx, qh = set(coexist_held), set(quiet_held)
    free = set(free)
    if not any(t in CORES or t in THREADS for t in free):
        # abstract caller (regions only): a free quarter's cores/threads are free, and so are the MI210's host threads
        free = expand(free) | ({f"t{k}" for k in range(184, 192)} if GPU in free else set())
    else:   # token-level caller: a quarter is free for a whole-quarter row only when every core/thread it runs on is
        free = {t for t in free if t not in QUARTERS or expand({t}) <= free}
    # ws58 sub-quarter: a whole quarter also holds its core tokens. PURE: expand into shallow copies, never the
    # caller's dicts (e40203894 rewrote c["options"] in place; the returned assigned/pending carry the copies).
    cands = [dict(c, options=[frozenset(expand(o)) for o in c["options"]]) for c in cands]
    pending = sorted(cands, key=plan_order)
    if not quiet_ok:
        pending = [c for c in pending if c.get("shape") != "quiet-host"]
    free, ram, out = set(free), float(ram_gib), []
    ports = {int(x) for x in held_ports}
    drain, T = None, None
    plan.drain_held = []
    plan.drain_lowbusy = []
    plan.rank_holds = []   # [(lower row, better row, T)]: the lower row was kept off the better row's regions
    plan.rank_skips = []   # [(lower row, better row, reason)]: a lower row took regions a better row wants (own block)
    for c in pending:
        big = any(len([r for r in o if r in QUARTERS]) >= 2 for o in c["options"])
        if big and (c.get("shape") == "quiet-host" or now - float(c.get("since") or now) >= DRAIN_AFTER_S):
            if row_busy(c) < DRAIN_MIN_BUSY:   # operator 2026-11-03: a mostly idle row never books a quiet/whole host
                plan.drain_lowbusy.append(c)
                continue
            blocker = drain_blocker(c, pending, free, ram, gpu_grant_open, ports)
            if blocker is not None:   # ws58 2026-11-02: a better-ranked row wants these regions; no promotion, no drain
                plan.drain_held.append((c, blocker))
                continue
            pending.remove(c); pending.insert(0, c)   # the drain row goes FIRST: at T it takes the host before any quarter row
            if not _fits(c, _avail(c, free, cx, qh), ram, gpu_grant_open):
                later = [float(e) for e in grant_ends if float(e) > now]
                drain, T = c, (max(later) if later else now + DRAIN_UNKNOWN_S)
                prev = (drain_prev or {}).get(c["id"])
                if prev:   # ws58 2026-11-02: a drain's T never moves later (11:28Z akx-auto10 slid 11:53 -> 12:00)
                    T = min(T, float(prev))
                # ws58 2026-11-02: a far T no longer drops the drain (that left the "needs all regions, some busy" hold
                # with no T and nothing backfilled); free regions are backfilled by any row that ends by T, so the
                # host is never held empty, and T is persisted so it never slides later.
            break
    plan.last_drain = (drain, T) if drain else None
    need_r = set().union(*drain["options"]) if drain is not None else set()
    if drain is not None:  # best fit: the longest backfill that still ends by T goes first, so the gap is packed
        dur = lambda c: float(c.get("estimate_s") or c.get("window_s") or 0)  # noqa: E731
        pending = [drain] + sorted([c for c in pending if c is not drain], key=lambda c: (now + dur(c) > T, -dur(c)))
    while pending:
        placed = None
        for c in pending:
            late = drain is not None and c is not drain and now + float(c.get("estimate_s") or c.get("window_s") or 0) > T
            opts = _fits(c, _avail(c, free, cx, qh), ram, gpu_grant_open)
            if late and c.get("coexist") and drain.get("shape") in QUIET_SHAPES:
                late = False   # COEXIST: a quiet-host drain never holds a coexist row back
            if late:   # a row ending after T may only take regions the drain row does not need (T bounds backfill, never kills)
                opts = [o for o in opts if not (o & need_r)]
            if ports & {int(x) for x in (c.get("ports") or [])}:
                continue  # its port is held by a running grant: it waits
            if opts:   # ws58 2026-11-04: never hand a lower-ranked row regions a better-ranked row is waiting for
                reserved, holds, skips = rank_reservation(c, pending, free, ram, gpu_grant_open, ports, now, grant_ends, drain)
                kept = [o for o in opts if not (o & reserved)]
                if len(kept) < len(opts):
                    plan.rank_holds += [(c, h, T) for h, T in holds if (c, h, T) not in plan.rank_holds]
                opts = kept
                if opts:
                    plan.rank_skips += [(c, h, why) for h, why in skips]
            if not opts:
                continue
            # prefer the smallest option, then the one other pending rows want least (keeps their alternatives open)
            demand = {r: sum(1 for x in pending if x is not c for o2 in x["options"] if r in o2) for r in free}
            o = min(opts, key=lambda o: (len(o), sum(demand.get(r, 0) for r in o), sorted(o)))
            placed = (c, o)
            break
        if not placed:
            break
        c, o = placed
        out.append((c, frozenset(compress(o)))); free -= o; ram -= float(c.get("gib") or 0); pending.remove(c)
        if c.get("coexist"):
            cx |= o
        elif c.get("shape") in QUIET_SHAPES:
            qh |= o
        ports |= {int(x) for x in (c.get("ports") or [])}
    idle = {}
    for r in sorted(x for x in free if x in REGIONS):
        want = [c for c in pending if any(r in o for o in c["options"])]
        if not want:
            idle[r] = "no runnable row needs it (every grantable/dry-runnable row is placed, running, failed or parked)"
            continue
        c = want[0]; why = []
        if drain is not None:
            why.append(f"draining for {drain.get('shape', 'host')} {drain['id']} until {dt.datetime.fromtimestamp(T, dt.timezone.utc):%H:%MZ}")
        clash = ports & {int(x) for x in (c.get("ports") or [])}
        if clash:
            why.append(f"port {','.join(map(str, sorted(clash)))} held by a running grant; waits")
        for o in c["options"]:
            if r in o and not clash:
                miss = o - free
                if miss:
                    why.append(f"needs {','.join(compress(o))}: {','.join(compress(miss))} busy")
                elif c.get("bench") and gpu_grant_open and "q3" in o:
                    why.append("timing row keeps off q3 while a GPU grant is open")
                elif ram - float(c.get("gib") or 0) < RAM_MARGIN_GIB:
                    why.append(f"RAM: {c.get('gib')} GiB would leave {ram - float(c.get('gib') or 0):.0f} GiB < {RAM_MARGIN_GIB} margin")
        idle[r] = f"{c['kind']} {c['id']} " + ("; ".join(why) or "blocked")
    return out, idle, pending


plan.last_drain = None
plan.drain_held = []
plan.drain_lowbusy = []


def quiet_ok_now(flags, now=None):
    """Knob, OFF by default: <flags>/allocator.json {"quiet_windows": ["22:00-06:00", ...]} (UTC) limits quiet-host grants
    to those windows; absent or empty = any time."""
    cfg = load_json(os.path.join(flags, "allocator.json")) or {}
    wins = cfg.get("quiet_windows") or []
    if not wins:
        return True
    t = dt.datetime.fromtimestamp(now or time.time(), dt.timezone.utc)
    cur = t.hour * 60 + t.minute
    for w in wins:
        try:
            a, b = w.split("-"); a = int(a[:2]) * 60 + int(a[3:5]); b = int(b[:2]) * 60 + int(b[3:5])
        except (ValueError, IndexError):
            continue
        if (a <= cur < b) if a <= b else (cur >= a or cur < b):
            return True
    return False


# ---------------------------------------------------------------- status
def lineage_of(rid, allrows):
    d = allrows.get(rid) or {}
    seen = set()
    root = rid  # the id whose stem names the lineage: follows supersedes hops
    while True:
        if d.get("lineage"):
            return str(d["lineage"])
        sup = d.get("supersedes")
        sup = sup[0] if isinstance(sup, list) and sup else sup
        if isinstance(sup, str) and sup and sup not in seen:
            seen.add(sup); root = sup; d = allrows.get(sup) or {}
            if not d:
                return id_stem(sup)
            continue
        return id_stem(root)


def lineage_fails(flags, rid, allrows):
    # refinement 5: a successor that names its fix (fix_ref) does not inherit its predecessors' failures - count only
    # the chain from rid back to (and including) the nearest row declaring fix_ref
    chain, cur, seen = [], rid, set()
    while cur and cur not in seen:
        seen.add(cur); chain.append(cur)
        d = allrows.get(cur) or {}
        if d.get("fix_ref"):
            return lineage_of(rid, allrows), sum(len(fail_paths(flags, x)) for x in chain)
        sup = d.get("supersedes")
        cur = sup[0] if isinstance(sup, list) and sup else sup if isinstance(sup, str) else None
    lin = lineage_of(rid, allrows)
    reset = 0
    n = 0
    for other, d in allrows.items():
        if lineage_of(other, allrows) != lin:
            continue
        reset = max(reset, int(d.get("lineage_reset") or 0))
        n += len(fail_paths(flags, other))
    # ids whose manifest is gone but whose dryrun dir remains still count
    for dd in glob.glob(os.path.join(flags, "dryrun", "*")):
        oid = os.path.basename(dd)
        if oid not in allrows and id_stem(oid) == lin:
            n += len(fail_paths(flags, oid))
    return lin, max(0, n - reset)


RUN_DIRECT = os.path.join(_HERE, "run_direct.sh")


def next_action(st, flags, rid):
    """DETERMINISTIC one-line next action per state (2026-11-03: an agent reads it, never infers it)."""
    rp = ready_path(flags, rid)
    s = st["state"]
    if s in ("done", "running", "dryrun-running"):
        return "-"
    if s in ("held", "stopped"):
        return st.get("fix") or "-"
    if s in ("failed", "parked"):
        return (st.get("fix_task") or "fix the launcher") + f"; then republish: python3 {os.path.join(_HERE, 'publish_row.py')} <spec.json>"
    if s in ("grantable", "armed"):
        return f"wait for a keeper tick, or run it now on a free lane: {RUN_DIRECT} {rp}"
    if s in ("stale", "needs-dryrun"):
        return f"re-run the smoke: python3 {os.path.join(_HERE, 'publish_row.py')} <spec.json>"
    return f"publish the row: python3 {os.path.join(_HERE, 'publish_row.py')} <spec.json>"


def direct_path(flags, rid):
    return os.path.join(dry_dir(flags, rid), "DIRECT.json")


def direct_run(flags, rid):
    """The run_direct.sh record while its supervisor is alive and the id is not terminal, else None."""
    rec = load_json(direct_path(flags, rid))
    if rec and alive(rec.get("pid")) and not rec.get("ended"):
        return rec
    return None


def regions_held(regions):
    """Region tokens a regions string books: quarters it covers (whole) plus gpu-quiet for mi210 rows."""
    return sorted(quarters_of(regions) | ({GPU} if "mi210" in str(regions) else set()))


def status(flags, rid, allrows=None, util=None):
    """Row state + the fixed companions every surface prints: `next` (one deterministic action), `logs` (the row's
    dry-run dir: poller.out / launcher.out), `held` (regions its open grant books) and, when the caller passes a
    hostutil measurement, `util` (measured % of those regions). A grant is never reported as work: only `util` is."""
    st = _status_raw(flags, rid, allrows)
    st["next"] = next_action(st, flags, rid)
    st["logs"] = dry_dir(flags, rid)
    if st["state"] == "running":
        held, g = None, None
        if st.get("direct"):
            rec = direct_run(flags, rid) or {}
            held = regions_held(rec.get("regions", ""))
            st["held"] = held
            st["logs"] = rec.get("out") or st["logs"]
            st["grant_age_s"] = int(time.time() - (iso_epoch(rec.get("started_at")) or time.time()))
        else:
            g = next((g for g in open_grants(flags) if g["id"] == rid), None)
        if g:
            held = sorted(r for r in compress(g["holds"]) if r in REGIONS)
            st["held"] = held
            try:
                st["grant_age_s"] = int(time.time() - os.path.getmtime(g["path"]))
            except OSError:
                pass
        if held is not None:
            if util is not None:
                st["util"] = hostutil.regions_pct(util, held)
                idle = hostutil.idle_regions(util, held)
                if idle and st.get("grant_age_s", 0) > IDLE_HELD_AFTER_S:
                    st["blocker"] = f"IDLE-HELD {','.join(idle)}: measured <{hostutil.IDLE_PCT:g}% busy {st['grant_age_s']}s into the grant"
    return st


def _status_raw(flags, rid, allrows=None):
    allrows = rows(flags) if allrows is None else allrows
    d = allrows.get(rid)
    if not d:
        return {"id": rid, "state": "unknown", "reason": "no epyc.row.v3 row in ready/"}
    G = os.path.join(flags, "grants")
    lp = d["launcher"]["path"]
    cur = sha256(lp) if os.path.isfile(lp) else None
    out = {"id": rid, "lane": d["lane"], "owner": d["owner"], "launcher_sha256": cur, "priority_rank": d.get("priority_rank")}
    lin, nf = lineage_fails(flags, rid, allrows)
    out.update(lineage=lin, lineage_fails=nf)
    if os.path.exists(os.path.join(G, rid + ".complete")) or os.path.exists(os.path.join(G, rid + ".ended")) \
            or os.path.exists(os.path.join(flags, "filing-done", rid + ".FILED")):
        out.update(state="done", reason="grants/<id>.ended|.complete present"); return out
    if cur is None:
        out.update(state="failed", reason=f"launcher {lp} missing"); return out
    if str(d.get("result_path", "")).endswith("RESULT-NEEDS-SPEC.jsonl"):
        out.update(state="failed", reason="spec incomplete: the legacy manifest had no result_path; publish a spec with result_path (+ result_format, decision_rule)",
                   fix_task=f"publish a complete spec for {rid}: result_path/result_format/decision_rule were missing in the migrated manifest "
                            f"(python3 scripts/coordination/rowflow/publish_row.py <spec.json>)"); return out
    drec = direct_run(flags, rid)
    if drec:   # 2026-11-03 item 1: a live run_direct.sh supervisor holds the row (never granted while it lives)
        out.update(state="running", reason=f"direct run pid {drec.get('pid')} since {drec.get('started_at')}", direct=True); return out
    if os.path.exists(os.path.join(G, rid + ".grant")) and not os.path.exists(running_path(flags, rid)):
        out.update(state="running", reason="grants/<id>.grant open"); return out
    run = load_json(running_path(flags, rid))
    if run and alive(run.get("pid")):
        out.update(state="dryrun-running", reason=f"dry run pid {run.get('pid')} since {run.get('started')}"); return out
    p = load_json(pass_path(flags, rid))
    fails = [load_json(x) or {} for x in fail_paths(flags, rid)]
    last_fail = fails[-1] if fails else None
    if p and p.get("launcher_sha256") == cur:
        sf = resolve_stop_path(d)   # 2026-11-05: `$D/...` resolved; unknown (None) keeps the row grantable
        if sf and os.path.exists(sf):   # a STOP file stops the row: never granted, never a drain candidate, never burns the id
            out.update(state="stopped", reason=sf, stop_file=sf, fix=f"rm {sf}"); return out
        a = load_json(armed_path(flags, rid))
        if a and alive(a.get("pid")):
            if armed_engine_ok(a.get("pid"), rid):
                out.update(state="armed", reason=f"poller pid {a['pid']} on {a.get('queue')} regions={a.get('regions')}", regions=a.get("regions")); return out
            out["rearm"] = f"ARMED pid {a['pid']} runs no filler_run*.sh engine for this row; re-armed on the next tick"
        af = arm_fails_since_pass(flags, rid, p)
        out["arm_fails"] = len(af)
        if len(af) >= MAX_FAILS:   # ws58 2026-11-03: a PASS no longer keeps a row that cannot be armed grantable
            out.update(state="parked", reason=f"{len(af)} consecutive arming/launch failures since the PASS of {p.get('passed_at')} "
                                              f"(last: {str(af[-1].get('reason'))[:160]}); operator-escalations/{rid}.arming.md",
                       fail_file=af[-1]["fail_file"], fix_task=af[-1].get("fix_task")); return out
        out.update(state="grantable", reason=f"dry run passed {p.get('passed_at')} ({p.get('units')} unit(s) in {p.get('result_path')})"); return out
    if nf >= MAX_FAILS:
        out.update(state="parked", reason=f"{nf} failed dry runs in lineage {lin}; operator-escalations/{lin}.md"); return out
    if last_fail and last_fail.get("launcher_sha256") == cur and last_fail.get("row_sha256", row_sha(flags, rid)) == row_sha(flags, rid):
        # sha-keyed FAIL memo: only a launcher or spec edit retries the row, never a rowflow change (22:25Z 2026-11-01:
        # an unchanged single-threaded launcher was re-dry-run after the allocator landed)
        out.update(state="failed", reason=str(last_fail.get("reason"))[:300], fail_file=fail_paths(flags, rid)[-1],
                   fix_task=last_fail.get("fix_task")); return out
    if p:
        out.update(state="stale", reason="launcher changed since the passing dry run; a new dry run is needed"); return out
    out.update(state="needs-dryrun", reason="no dry run for the current launcher"); return out


# ---------------------------------------------------------------- dry run
def head1(path):
    try:
        return open(path, errors="replace").readline().strip()
    except OSError:
        return ""


def tail(path, n=30):
    try:
        return open(path, errors="replace").read().splitlines()[-n:]
    except OSError:
        return []


def vram_used_bytes():
    try:
        j = json.loads(subprocess.run([ROCM_SMI, "--showmeminfo", "vram", "--json"], capture_output=True, text=True, timeout=10).stdout)
        return max(int(v.get("VRAM Total Used Memory (B)", 0)) for v in j.values() if isinstance(v, dict))
    except Exception:
        return None


def kill_group(pid, grace=20):
    try:
        os.killpg(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        return
    for _ in range(grace):
        if not alive(pid):
            return
        time.sleep(1)
    try:
        os.killpg(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


# region-lock's real stderr lines (epyc-orchestrator src/runtime/region_lock_cli.py):
#   [region-lock] acquiring regions ['q1'] as role='build' (timeout_s=10.0) …
#   [region-lock] acquiring gpu-quiet exclusive + regions ['q0'] as role='bench' (timeout_s=600.0) …
#   [region-lock] waiting 15.0s for q0 (q0.lock) as role='bench' tag='t': held by pid N role=... tag=... age=...
#   [region-lock] held ['q1'] after 0.0s wait; running: ...      /  held gpu-quiet exclusive + regions ['q0'] after ...
#   [region-lock] TIMEOUT acquiring regions ['q1']: ...
_RL_ACQ = re.compile(r"\[region-lock\] acquiring (.+?) as role=")
_RL_WAIT = re.compile(r"\[region-lock\] waiting [\d.]+s for (\S+) \(")
_RL_HELD = re.compile(r"\[region-lock\] held (.+?) after [\d.]+s wait")
_RL_TIMEOUT = re.compile(r"\[region-lock\] TIMEOUT acquiring (.+?):")


def _rl_regions(what):
    """{regions} named by an acquire/held phrase: `regions ['q0', 'q1']`, `['q1']`, `gpu-quiet <mode> [+ regions [...]]`."""
    what = what.strip()
    m = re.search(r"regions \[([^\]]*)\]", what) or re.fullmatch(r"\[([^\]]*)\]", what)
    got = {x.strip().strip("'\"") for x in m.group(1).split(",") if x.strip()} if m else set()
    if what.startswith("gpu-quiet"):
        got.add(GPU)
    return got


def lock_waits(lines, holds):
    """Region sets the job asked region-lock for and has NOT been granted: an `acquiring` line with no later `held` (or
    TIMEOUT) line covering it, or a `waiting Ns for <region>` line outside every open acquire. `holds` is unused here;
    the caller compares."""
    pending = []
    for l in lines:
        m = _RL_ACQ.search(l)
        if m:
            got = _rl_regions(m.group(1))
            if got:
                pending.append(got)
            continue
        m = _RL_WAIT.search(l)
        if m:
            if not any(m.group(1) in a for a in pending):
                pending.append({m.group(1)})
            continue
        m = _RL_HELD.search(l) or _RL_TIMEOUT.search(l)
        if m:
            got = _rl_regions(m.group(1))
            pending = [a for a in pending if not a <= got]
    return pending


def busy_pct(s0, s1, cpus):
    b = sum(s1.get(c, (0, 0))[0] - s0.get(c, (0, 0))[0] for c in cpus)
    t = sum(s1.get(c, (0, 0))[1] - s0.get(c, (0, 0))[1] for c in cpus)
    return 100.0 * b / t if t > 0 else 100.0


def row_orphans(rid):
    """READ-ONLY: pids (other than ours) whose argv names this exact row id. Reported in the dry-run record; never killed."""
    out = []
    for q in os.listdir("/proc"):
        if not q.isdigit() or int(q) == os.getpid():
            continue
        try:
            if rid in open(f"/proc/{q}/cmdline", "rb").read().decode("utf8", "replace"):
                out.append(int(q))
        except OSError:
            continue
    return out


def _proc_stat(pid):
    """(ppid, pgid, starttime) from /proc/<pid>/stat, or None when gone/zombie."""
    try:
        f = open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()
    except (OSError, IndexError):
        return None
    if f[0] == "Z":
        return None
    return int(f[1]), int(f[2]), f[19]


def harness_tree(root, tracked):
    """ws58 2026-11-02: accumulate {pid: starttime} of root and every live descendant (setsid'd ones included: a new session
    keeps its ppid until the parent dies, so sampling during the run captures them before they are reparented)."""
    kids = {}
    for q in os.listdir("/proc"):
        if q.isdigit():
            st = _proc_stat(int(q))
            if st:
                kids.setdefault(st[0], []).append((int(q), st[2]))
    st = _proc_stat(root)
    todo = [root]
    if st:
        tracked.setdefault(root, st[2])
    while todo:
        for c, birth in kids.get(todo.pop(), []):
            if c not in tracked:
                tracked[c] = birth
                todo.append(c)
    return tracked


def tree_cpu_s(tracked, acc):
    """Cumulative cpu seconds (utime+stime) of every tracked process, monotone: an exited pid keeps its last value."""
    hz = os.sysconf("SC_CLK_TCK")
    for pid, birth in list(tracked.items()):
        try:
            f = open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()
        except (OSError, IndexError):
            continue
        if f[19] == birth:
            acc[pid] = (int(f[11]) + int(f[12])) / hz
    return sum(acc.values())


MEASURE_WINDOW_S = 60
OVERDECLARED_RATIO = 4.0   # declared busy >= 4x measured (and declared >= 0.5): flagged in PASS.json + launcher.out


def measured_busy(samples, claimed, until=None):
    """(measured_threads, measured_busy_fraction) over the last MEASURE_WINDOW_S of [(t, cpu_s)] up to `until`."""
    pts = [x for x in samples if until is None or x[0] <= until + 5]
    if len(pts) < 2:
        return None, None
    t1, c1 = pts[-1]
    t0, c0 = next((x for x in pts if x[0] >= t1 - MEASURE_WINDOW_S), pts[0])
    if t1 - t0 < 4:
        t0, c0 = pts[0]
    if t1 <= t0:
        return None, None
    th = max(0.0, (c1 - c0) / (t1 - t0))
    return round(th, 3), round(min(1.0, th / max(1, claimed)), 3)


def busy_flag(declared, measured):
    if measured is None or declared < 0.5 or declared < OVERDECLARED_RATIO * max(measured, 1e-3):
        return None
    return f"OVER-DECLARED busy_fraction: declared {declared:g}, measured {measured:g}; right-size the shape/claim"


def _same(pid, birth):
    st = _proc_stat(pid)
    return st is not None and st[2] == birth


def reap_pids(tracked, grace=20):
    """TERM every still-same process (and every process group one of them leads), wait up to grace s, KILL, verify via
    /proc. Only pids this harness started (tracked by harness_tree: pid + start time) are signalled; nothing is ever
    selected by name, argv or cwd (2026-11-03 session review). Returns (reaped, survivors)."""
    live = {p: b for p, b in tracked.items() if _same(p, b) and p != os.getpid()}
    if not live:
        return [], []
    for sig in (signal.SIGTERM, signal.SIGKILL):
        for p, b in live.items():
            st = _proc_stat(p)
            if st and st[2] == b:
                if st[1] == p:
                    try:
                        os.killpg(p, sig)
                    except (ProcessLookupError, PermissionError):
                        pass
                try:
                    os.kill(p, sig)
                except (ProcessLookupError, PermissionError):
                    pass
        for _ in range(grace * 4 if sig == signal.SIGTERM else 20):
            if not any(_same(p, b) for p, b in live.items()):
                break
            time.sleep(0.25)
        if not any(_same(p, b) for p, b in live.items()):
            break
    return sorted(live), sorted(p for p, b in live.items() if _same(p, b))


def record_fail(flags, rid, d, reason, extra):
    n = len(fail_paths(flags, rid)) + 1
    rec = {"id": rid, "at": now_iso(), "launcher_sha256": sha256(d["launcher"]["path"]) if os.path.isfile(d["launcher"]["path"]) else None,
           "row_sha256": row_sha(flags, rid), "rowflow_sha256": sha256(__file__), "reason": reason, "launcher_out_tail": tail(os.path.join(dry_dir(flags, rid), "launcher.out")),
           "fix_task": f"fix dry-run failure of {rid}: {reason} (see compute-flags/dryrun/{rid}/launcher.out; the keeper retries as soon as the launcher file changes)",
           **extra}
    fp = os.path.join(dry_dir(flags, rid), f"FAIL-{n}.json")
    atomic_json(fp, rec)
    try:  # push, not wait-to-be-noticed (2026-11-04); never blocks the FAIL record
        notify.smoke_fail(flags, rid, fp, rec, owner=str(d.get("owner") or ""))
    except Exception as e:  # noqa: BLE001
        print(f"notify smoke-fail {rid}: {type(e).__name__}: {e}", file=sys.stderr)
    return rec


def record_arm_fail(flags, rid, d, kind, reason, log=print):
    """An arming (kind=arm) or launch (kind=launch: admission refused the armed poller) failure of a PASSed row. The
    MAX_FAILS-th consecutive one since the PASS parks the row (status) and writes operator-escalations/<id>.arming.md."""
    pol = os.path.join(dry_dir(flags, rid), "poller.out")
    record_fail(flags, rid, d, reason, {"kind": kind, "launcher_out_tail": tail(pol), "tail_of": pol,
                                        "fix_task": f"fix the {kind} failure of {rid}: {reason} (see compute-flags/dryrun/{rid}/poller.out); "
                                                    f"after {MAX_FAILS} in a row the row is parked until it is republished"})
    af = arm_fails_since_pass(flags, rid)
    if len(af) < MAX_FAILS:
        return len(af)
    out = os.path.join(flags, "operator-escalations", rid + ".arming.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    L = [f"# PARKED NEEDS-OPERATOR - row `{rid}` ({len(af)} consecutive arming/launch failures since its PASS; written {now_iso()} by rowflow)", "",
         "The row passed its dry run but its poller cannot be armed or launched, so the allocator no longer grants it "
         "(a PASS alone used to keep it grantable forever). Last failures:", ""]
    L += [f"- {f.get('at')} [{f.get('kind') or 'arm'}] {str(f.get('reason'))[:300]}" for f in af[-5:]]
    L += ["", "Poller output tail:", "", "```"] + [str(x) for x in (af[-1].get("launcher_out_tail") or [])[-15:]] + ["```", "",
          "Options: 1. fix the launcher and republish (a new PASS clears the count); 2. drop (remove ready/<id>.json).", ""]
    with open(out, "w") as f:
        f.write("\n".join(L))
    if len(af) == MAX_FAILS:
        log(f"PARK {rid}: {len(af)} consecutive {kind} failures since its PASS; operator-escalations/{rid}.arming.md")
    return len(af)


def write_escalation(flags, rid, allrows):
    lin, nf = lineage_fails(flags, rid, allrows)
    if nf < MAX_FAILS:
        return
    out = os.path.join(flags, "operator-escalations", lin + ".md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    L = [f"# PARKED NEEDS-OPERATOR - lineage `{lin}` ({nf} failed dry runs; written {now_iso()} by rowflow)", "",
         "Nobody retries this lineage. Each failure below is the owner's recorded fix task.", ""]
    for other, d in sorted(allrows.items()):
        if lineage_of(other, allrows) != lin:
            continue
        for fp in fail_paths(flags, other):
            f = load_json(fp) or {}
            L.append(f"- {f.get('at')} **{other}**: {str(f.get('reason'))[:300]}")
    L += ["", "Options: 1. fix and re-admit under a new id with `lineage_reset: %d` in the spec; 2. re-scope under a new `lineage`; "
          "3. drop (remove ready/<id>.json)." % nf, ""]
    with open(out, "w") as f:
        f.write("\n".join(L))


def dryrun_grant_text(rid, admission_class, regions, holds, start, end):
    """Serialize the allocator's synthetic grant with backward-compatible fields plus rowflow identity/class."""
    if admission_class is not None:
        need(isinstance(admission_class, str) and admission_class in ADMISSION_CLASSES,
             f"invalid admission_class {admission_class!r}")
    fields = [f"regions={regions}", f"start={start:%Y-%m-%dT%H:%MZ}", f"end={end:%Y-%m-%dT%H:%MZ}",
              f"holds={','.join(sorted(holds))}", "schema=epyc.rowflow.dryrun-grant.v1", f"id={rid}", "kind=rowflow-dryrun"]
    if admission_class is not None:
        fields.append(f"admission_class={admission_class}")
    return " ".join(fields) + "\n"


def new_dryrun_native_result_path(dd):
    """Create a fresh result path for this exact qualification attempt."""
    import tempfile
    dry_dir = os.path.abspath(dd)
    if os.path.islink(dry_dir):
        raise Refused("dry-run output root may not be a symlink")
    root = os.path.join(dry_dir, "native-attempts")
    if os.path.islink(root):
        raise Refused("dry-run native-attempts directory may not be a symlink")
    os.makedirs(root, mode=0o700, exist_ok=True)
    if os.path.realpath(root) != os.path.join(os.path.realpath(dry_dir), "native-attempts"):
        raise Refused("dry-run native-attempts directory escaped its row")
    os.chmod(root, 0o700)
    attempt = tempfile.mkdtemp(prefix="attempt-", dir=root)
    os.chmod(attempt, 0o700)
    return os.path.join(attempt, "native-result.json")


SMOKE_BRANCH_RE = re.compile(r"\bFILLER_(?:SMOKE|DRYRUN)\w*")
SMOKE_SCAN_MAX_BYTES = 2 << 20


def smoke_branch_files(d):
    """The row's own launcher and every regular file its engine line runs (--cmd / --complete-cmd tokens) that names
    FILLER_SMOKE* or FILLER_DRYRUN*: a job that branches on them does something else under a smoke than in its grant.
    The engine itself (which honours them by design) is not scanned. An unreadable launcher counts as branching."""
    lp = d["launcher"]["path"]
    try:
        o = parse_launcher(lp)
    except (Refused, OSError, StopIteration, ValueError) as e:
        return [f"{lp} (unparsable: {e})"]
    eng = os.path.realpath(o["engine"])
    hits, seen = [], set()
    for f in [lp] + [x for x in referenced_paths({"cmd": o["cmd"], "complete_cmd": o["complete_cmd"]}) if os.path.isfile(x)]:
        rp = os.path.realpath(f)
        if rp in seen or rp == eng:
            continue
        seen.add(rp)
        try:
            if os.path.getsize(rp) > SMOKE_SCAN_MAX_BYTES:
                hits.append(f"{f} (too large to scan)")
                continue
            txt = open(rp, errors="replace").read()
        except OSError as e:
            hits.append(f"{f} (unreadable: {e})")
            continue
        if SMOKE_BRANCH_RE.search(txt):
            hits.append(f)
    return hits


def smoke_completion_check(d):
    """Operator 2026-11-02 (ws58): a smoke/dry-run PASS may file a row COMPLETE only when (1) the launcher has no smoke
    branch (no FILLER_SMOKE*/FILLER_DRYRUN* in it or in the files its --cmd/--complete-cmd run), (2) the result is not a
    dry-run-native isolated result, and (3) the engine's --complete-cmd, re-run in --workdir with every FILLER_SMOKE*/
    FILLER_DRYRUN* variable removed, passes on the artifacts the full job writes. Returns (ok, reason)."""
    if d.get("dryrun_native_result"):
        return False, "dryrun_native_result: the smoke wrote an isolated per-attempt result, not the full job's artifacts"
    hits = smoke_branch_files(d)
    if hits:
        return False, "launcher branches on FILLER_SMOKE/FILLER_DRYRUN (" + ", ".join(hits[:4]) + "): a smoke is not the job"
    o = parse_launcher(d["launcher"]["path"])
    env = {k: v for k, v in os.environ.items() if not SMOKE_BRANCH_RE.fullmatch(k)}
    wd = o.get("workdir") or d.get("workdir") or "/"
    try:
        r = subprocess.run(["bash", "-c", o["complete_cmd"]], cwd=wd, env=env, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"full-job --complete-cmd could not run outside the smoke: {e}"
    if r.returncode != 0:
        return False, f"full-job --complete-cmd rc={r.returncode} outside the smoke: the full job's artifacts do not satisfy it"
    return True, "no smoke branch; full-job --complete-cmd passes on the job's own artifacts"


def dryrun_run(flags, rid, regions, one_quarter=False, smoke_s=None):
    """The dry run on the regions the allocator assigned. Returns (verdict, message). verdict in PASS | FAIL | WAIT.
    Operator 2026-11-05: the smoke is a KEEPER-SCHEDULED filler - publish_row queues it, the allocator places it first on
    4 genuinely free cores and runs it here (publish_row --smoke-now runs it at once on the keeper's free snapshot);
    FILLER_SMOKE=1 / FILLER_SMOKE_UNITS=1 for launchers that can shrink their unit count. Its admission token lives in
    the row's private dryrun dir, never in grants/; its cpus are visible to the allocator through RUNNING.json.
    The first-progress timer starts only at engine START (the lock is held); a smoke still waiting for its lock after
    first_progress_s, or waiting on region-lock contention, ends WAIT (requeued), never FAIL.
    Operator 2026-11-03 (session review §3.1): PASS = FIRST REAL PROGRESS of the job (FirstProgress: smoke_predicate, or
    a new non-placeholder record) within first_progress_s (smoke_s, else the row's first_progress_s, else 300 s), then a
    clean stop (rc 0/75). rc 0/75 with no progress is a FAIL."""
    allrows = rows(flags)
    d = allrows.get(rid)
    need(d, "no v3 row")
    st = status(flags, rid, allrows)["state"]
    if st not in ("needs-dryrun", "stale"):
        return "WAIT", f"state {st}; nothing to do"
    dd = dry_dir(flags, rid)
    os.makedirs(os.path.join(dd, "state"), exist_ok=True)
    G = os.path.join(dd, "grants")
    os.makedirs(G, exist_ok=True)
    grant = os.path.join(G, rid + ".grant")
    holds = quarters_of(regions) | ({GPU} if "mi210" in regions else set())
    lp = d["launcher"]["path"]
    lsha = sha256(lp)
    timeout = int(smoke_s or d.get("first_progress_s") or d.get("dryrun_timeout_s") or FIRST_PROGRESS_S)
    window = max(int(d["min_window_s"]) + 300, timeout + STOP_GRACE_S + 300)
    start = dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0) - dt.timedelta(minutes=1)
    end = start + dt.timedelta(seconds=window)
    for stale in ("stop", "ended", "complete"):
        try:
            os.remove(os.path.join(dd, stale))
        except OSError:
            pass
    result_path = new_dryrun_native_result_path(dd) if d.get("dryrun_native_result") else d["result_path"]
    result_format = "json" if d.get("dryrun_native_result") else d["result_format"]
    units0 = count_units(result_path, result_format, d.get("workdir"))
    env = dict(os.environ, FILLER_DRYRUN="1", FILLER_DRYRUN_DIR=dd, FILLER_STATE_DIR=os.path.join(dd, "state"),
               FILLER_FLAGS_DIR=flags, FILLER_GRANTS_DIR=G,
               FILLER_POLL="5", FILLER_OWNER=str(d["owner"]), FILLER_EST_WALL_S=str(d["estimate_s"]),
               FILLER_DRYRUN_ONE_QUARTER="1" if one_quarter else "0",
               WS58_REGIONS=ws58_cpus(regions), **({"FILLER_SMOKE": "1", "FILLER_SMOKE_UNITS": "1", "FILLER_DISK_FLOOR_GIB": "20"} if smoke_s else {}))  # a smoke writes little: only a near-full disk stops it  # ws58 2026-11-01: launchers written for the v8 keeper read it
    if d.get("dryrun_native_result"):
        env["FILLER_DRYRUN_RESULT_PATH"] = result_path
    env["FILLER_SMOKE_T0"] = str(int(time.time()))
    probe = FirstProgress(d, result_path, result_format, env, d.get("workdir"))
    if probe.stale:
        reason = (f"no first progress possible: {probe.kind} `{probe.pred[:80]}` already exits 0 BEFORE the launch, so it cannot "
                  "see this run; fix: make it test this run's own output (e.g. a record newer than $FILLER_SMOKE_T0), then re-run "
                  "publish_row.py <spec.json>")
        record_fail(flags, rid, d, reason, {"regions": regions, "result_path": result_path, "result_format": result_format,
                                            "first_unit_at": None, "elapsed_s": 0})
        write_escalation(flags, rid, allrows)
        return "FAIL", reason
    with open(grant, "w") as f:
        f.write(dryrun_grant_text(rid, d.get("admission_class"), regions, holds, start, end))
    out = open(os.path.join(dd, "launcher.out"), "a")
    out.write(f"\n==== dry run {now_iso()} regions={regions} launcher_sha={lsha} units_before={units0}\n"); out.flush()
    lout = os.path.join(dd, "launcher.out")
    out_lines0 = len(tail(lout, 10**6))  # counted BEFORE the launch: a region-lock line the job prints at once is this run's
    p = subprocess.Popen(["bash", lp], cwd=flags, env=env, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
    tracked = harness_tree(p.pid, {p.pid: (_proc_stat(p.pid) or (0, 0, None))[2]})  # setsid'd group: pgid == p.pid
    atomic_json(running_path(flags, rid), {"pid": p.pid, "pgid": p.pid, "started": now_iso(), "regions": regions, "launcher_sha256": lsha, "grant": grant})
    t0 = time.time()
    t_lock = None
    cpu_acc, cpu_samples = {}, []
    vram_max = None
    gpu = "mi210_0" in regions
    first_unit_at = None
    progress = None
    stop_requested = None
    warning = None
    ended = os.path.join(dd, "ended")
    verdict, reason = None, None
    try:
        while True:
            for _ in range(5):
                time.sleep(1)
                harness_tree(p.pid, tracked)
            cpu_samples.append((time.time(), tree_cpu_s(tracked, cpu_acc)))
            if gpu:
                v = vram_used_bytes()
                if v is not None:
                    vram_max = max(vram_max or 0, v)
            # a dry run must never wait on a lock: a region-lock acquire for regions outside what this dry run holds, or one
            # not satisfied within 60 s, is the row's defect (the job's own claim ignores WS58_REGIONS)
            new_lines = tail(lout, 10**6)[out_lines0:]
            waits = lock_waits(new_lines, holds)
            if waits and (waits[0] - holds or time.time() - t0 > 60):
                # operator 2026-11-05: waiting for a slot is never a failure - lock contention is WAIT, the keeper requeues
                verdict, reason = "WAIT", (f"job waits on region-lock for {','.join(sorted(waits[0]))} while the smoke holds "
                                           f"{','.join(sorted(holds)) or '-'}; requeued, no FAIL recorded (if this repeats, make "
                                           "the job's own region-lock claim use $WS58_REGIONS under FILLER_SMOKE)")
                break
            if t_lock is None and any("START regions=" in l for l in new_lines):
                t_lock = time.time()   # the first-progress timer starts only once the engine holds its lock (START)
                out.write(f"==== engine START at +{int(t_lock - t0)}s; first-progress timer ({timeout} s) starts now\n"); out.flush()
            if first_unit_at is None:
                hit, why = probe.check()
                if hit:
                    first_unit_at, progress = now_iso(), why
                    out.write(f"==== first progress at {first_unit_at} (+{int(time.time() - t0)}s): {why}\n"); out.flush()
                    if not os.path.exists(ended):
                        open(os.path.join(dd, "stop"), "w").close()
                        stop_requested = time.time()
            if os.path.exists(ended) or p.poll() is not None:
                rc_line = (head1(ended) or "rc=? (no ended record)")
                m = re.match(r"rc=(\d+)", rc_line)
                rc = int(m.group(1)) if m else -1
                if first_unit_at is None:
                    hit, why = probe.check()
                    if hit:
                        first_unit_at, progress = now_iso(), why
                if "reason=disk-floor" in rc_line or "reason=hard-end" in rc_line and not first_unit_at and time.time() - t0 < 60:
                    verdict, reason = "WAIT", f"host condition, not the row: {rc_line[:100]} (free disk under the 150 GiB floor); retried later, no FAIL recorded"
                    break
                if not first_unit_at and rc not in (0, 75):
                    verdict, reason = "FAIL", (f"job ended {rc_line[:80]} after {int(time.time() - t0)}s, before its first "
                                               f"progress ({probe.what()}); fix: the job's own error is in {lout}; fix it, "
                                               "then re-run publish_row.py <spec.json>")
                elif not first_unit_at:
                    verdict, reason = "FAIL", (f"no first progress within {timeout} s: job ended {rc_line[:80]} after "
                                               f"{int(time.time() - t0)}s; {probe.what()}; {probe.fix(timeout)}")
                elif rc not in (0, 75):
                    verdict, reason = "FAIL", f"first unit written but the job ended {rc_line[:120]}"
                elif gpu and (vram_max is None or vram_max < 64 << 20):
                    verdict, reason = "FAIL", f"GPU row produced a unit but VRAM never showed residency (max {vram_max} B sampled during the run)"
                else:
                    verdict, reason = "PASS", f"first progress: {progress}; {rc_line[:80]}"
                break
            if stop_requested and time.time() - stop_requested > STOP_GRACE_S:
                # the engine's hard-end kill is production's truncation path too: PASS with a warning, then stop the group
                warning = f"job did not stop within {STOP_GRACE_S}s of the stop file (FILLER_STOPFILE not honoured between items); truncated by signal"
                if gpu and (vram_max is None or vram_max < 64 << 20):
                    verdict, reason = "FAIL", f"GPU row produced a unit but VRAM never showed residency (max {vram_max} B sampled during the run)"
                else:
                    verdict, reason = "PASS", f"first progress: {progress}; {warning}"
                break
            if first_unit_at is None and t_lock is not None and time.time() - t_lock > timeout:
                verdict, reason = "FAIL", f"no first progress within {timeout} s of engine START; {probe.what()}; {probe.fix(timeout)}"
                break
            if t_lock is None and time.time() - t0 > timeout:
                # still waiting for its lock / a held whole host: not the row's defect (codex3-pareval120 r2, 2026-11-05)
                verdict, reason = ("WAIT", f"the engine did not reach START within {timeout} s (waiting on its region lock, a "
                                           f"held host or admission; see {lout}); requeued, no FAIL recorded")
                break
    finally:
        if p.poll() is None:  # poll(), not ps: an exited-but-unreaped launcher is a zombie that ps still lists
            if not os.path.exists(os.path.join(dd, "stop")):
                open(os.path.join(dd, "stop"), "w").close()
            for _ in range(STOP_GRACE_S // 5 if verdict == "PASS" else 6):
                if p.poll() is not None:
                    break
                time.sleep(5)
            if p.poll() is None:
                kill_group(p.pid)
                try:
                    p.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    pass
        # ws58 2026-11-02: the harness owns every process it started, PASS, FAIL or timeout alike (a private engine copy
        # included): TERM the group + tracked descendants, 20 s, KILL, verify. ONLY tracked descendants (pid + start
        # time captured while the run was live) are ever signalled. 2026-11-03 (session review, DELETE verdict): the
        # argv/cwd "still naming the row" sweep is gone - on a shared host a row id in another process's command line
        # is not ownership (it killed the publisher's own tool shells 3x, exit 144, and an armed sibling launcher,
        # rc=143). Anything it would have found is reported read-only by row_orphans() in the record, never killed.
        harness_tree(p.pid, tracked)
        reaped, surv = reap_pids(tracked)
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        if reaped:
            out.write(f"==== REAPED {reaped}\n")
        leftover = sorted(set(row_orphans(rid)) - set(tracked))
        if leftover:
            out.write(f"==== NOTE {leftover} name this row but were not started by this dry run; left alone (never kill by name)\n")
        if surv:
            warning = (warning + "; " if warning else "") + f"UNREAPED {sorted(set(surv))}: survived TERM+KILL"
            out.write(f"==== {warning}\n")
        try:
            os.remove(grant)
        except OSError:
            pass
        try:
            os.remove(running_path(flags, rid))
        except OSError:
            pass
        if verdict == "FAIL" and one_quarter and (not reason.startswith("no first progress") or "never reached START" in reason):
            reason += (f" [dry run held ONE quarter, WS58_REGIONS={ws58_cpus(regions)}; a launcher whose own taskset/claim "
                       "hard-codes a wider cpu list must honour WS58_REGIONS under FILLER_DRYRUN]")
        out.write(f"==== dry run {verdict}: {reason} ({now_iso()})\n"); out.close()
    cur_sha = sha256(lp) if os.path.isfile(lp) else None
    if verdict == "PASS" and cur_sha != lsha:
        verdict, reason = "FAIL", "launcher changed while the dry run was running"
    rec = {"regions": regions, "units": count_units(result_path, result_format, d.get("workdir")) - units0, "result_path": result_path,
           "result_format": result_format, "first_unit_at": first_unit_at, "first_progress": progress,
           "first_progress_s": timeout, "progress_rule": probe.kind, "vram_used_max_bytes": vram_max,
           "engine_sha256": sha256(d["engine"]["path"]) if os.path.isfile(d["engine"]["path"]) else None,
           "ended": head1(ended) or None, "warning": warning, "dryrun_log": os.path.join(dd, "launcher.out"), "elapsed_s": int(time.time() - t0)}
    # refinement 1: what the job actually used (before the harness's stop), against the row's declared claim
    claimed = claimed_cpus(d.get("regions"), (parse_launcher(lp) if os.path.isfile(lp) else {}).get("claim_cpus"), str(d.get("shape") or "quarter"))
    mt, mb = measured_busy(cpu_samples, claimed, until=stop_requested)
    rec.update(measured_threads=mt, measured_busy_fraction=mb, measured_claimed_cpus=claimed)
    flag = busy_flag(row_busy(d), mb)
    if flag:
        rec["busy_flag"] = flag
        with open(os.path.join(dd, "launcher.out"), "a") as lo:
            lo.write(f"==== {flag}\n")
    if verdict == "WAIT":
        return verdict, reason
    # ws58 2026-11-02: a smoke that finished the WHOLE job (complete marker, or units reached the declared total) is done,
    # but only when the smoke WAS the job: no smoke branch, and the full-job completion predicate holds (smoke_completion_check)
    if verdict == "PASS" and (os.path.exists(os.path.join(dd, "complete"))
                              or (d.get("total_units") and rec["units"] >= int(d["total_units"]))):
        ok, why = smoke_completion_check(d)
        rec["job_complete"] = ok
        rec["job_complete_reason"] = why
        if not ok:
            with open(os.path.join(dd, "launcher.out"), "a") as lo:
                lo.write(f"==== smoke completion NOT filed: {why}\n")
    if verdict == "PASS":
        atomic_json(pass_path(flags, rid), {"id": rid, "passed_at": now_iso(), "launcher_sha256": lsha, **rec})
        for fp in fail_paths(flags, rid):
            pass  # history stays; status() prefers a current PASS
    else:
        record_fail(flags, rid, d, reason, rec)
        write_escalation(flags, rid, allrows)
    return verdict, reason


def lane_counts(flags, allrows):
    c = {"cpu": 0, "gpu": 0}
    for rid, d in allrows.items():
        if status(flags, rid, allrows)["state"] in ("grantable", "armed", "running"):
            c[d["lane"]] += 1
    return c


# ---------------------------------------------------------------- arm + grant (the allocator writes grants itself)
def arm_one(flags, rid, d, regions=None, log=print):
    """Start the row's poller (the exact launcher through its engine, polling grants/<id>.grant). Regions are NOT
    resolved here: the grant the allocator writes later carries them."""
    dd = dry_dir(flags, rid)
    os.makedirs(os.path.join(dd, "state"), exist_ok=True)
    log = os.path.join(dd, "poller.out")
    before = sum(1 for l in tail(log, 100000) if "launcher up pid=" in l)
    env = dict(os.environ, FILLER_POLL="5", FILLER_OWNER=str(d["owner"]), FILLER_EST_WALL_S=str(d["estimate_s"]),
               FILLER_STATE_DIR=os.path.join(dd, "state"), FILLER_FLAGS_DIR=flags, FILLER_GRANTS_DIR=os.path.join(flags, "grants"))
    if regions and ws58_cpus(regions):
        env["WS58_REGIONS"] = ws58_cpus(regions)
    for k in ("FILLER_DRYRUN", "FILLER_DRYRUN_DIR", "FILLER_DRYRUN_ONE_QUARTER"):
        env.pop(k, None)
    with open(log, "a") as out:
        out.write(f"\n==== arm {now_iso()}\n")
        subprocess.Popen(["bash", d["launcher"]["path"]], cwd=flags, env=env, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
    pid = None
    for _ in range(30):
        time.sleep(1)
        pids = [int(m.group(1)) for l in tail(log, 100000) for m in [re.search(r"launcher up pid=(\d+)", l)] if m]
        if len(pids) > before:
            pid = pids[-1]; break
    if not pid:
        n = record_arm_fail(flags, rid, d, "arm", "poller did not log 'launcher up pid=' within 30 s of arming", log)
        return None, f"fail: no launcher pid within 30 s ({n} consecutive since the PASS; parked at {MAX_FAILS})"
    with open(os.path.join(flags, "ws58-armed.queue"), "a") as f:   # id|pid|window_s|gib|regions: backlog_gen's pid lookup
        f.write(f"{rid}|{pid}|{d['window_s']}|{d['gib']}|{d['regions']}\n")
    atomic_json(armed_path(flags, rid), {"id": rid, "pid": pid, "regions": d["regions"], "at": now_iso(), "launcher_sha256": sha256(d["launcher"]["path"])})
    return pid, f"ARMED {rid} pid={pid}"


def iso_epoch(s):
    """epoch of an ISO-ish UTC stamp (…T%H:%MZ or …T%H:%M:%SZ); None when unparsable."""
    for f in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%MZ"):
        try:
            return dt.datetime.strptime(str(s), f).replace(tzinfo=dt.timezone.utc).timestamp()
        except (ValueError, TypeError):
            pass
    return None


def mem_available_gib():
    try:
        for l in open("/proc/meminfo"):
            if l.startswith("MemAvailable:"):
                return int(l.split()[1]) / 1048576
    except OSError:
        pass
    return 0.0


def _gate():
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:  # the keeper runs `python3 -I`: isolated mode does not put the script's directory on sys.path
        sys.path.insert(0, here)
    import grant_ok_launcher as gate
    return gate


def armed_engine_ok(pid, rid, proc="/proc"):
    """True when the ARMED pid is alive AND it (or a descendant, depth <= 6) runs a filler_run*.sh engine with --id rid.
    2026-11-03 session review item 7: an ARMED.json whose pid was a grant_supervisor.py (no engine under it) was planned
    first every tick, refused by admission (rc=15) and never re-armed; a pid that is not an engine is not armed."""
    try:
        if not alive(pid):
            return False
        o, _epid, _own = _gate().find_launcher(proc, int(pid), rid)
    except Exception:  # noqa: BLE001 - Refuse (another row's engine), OSError, UnicodeDecodeError: not this row's engine
        return False
    return bool(o)


def admit(flags, rid, d, pid, regions, window_s):
    """The ONE launcher-side admission (grant_ok_launcher.check: the parser of the live poller's argv, window >= min+300,
    regions survive its parse and cover its claim, --precond-cmd). Returns (ok, line)."""
    import argparse as _ap
    gate = _gate()
    cls = "gpu" if "mi210" in regions else ("whole-host" if regions == "0-95" else "block-correctness")
    # ws58 23:56Z: a cpu job with --gpu-quiet holds the GPU through the allocator's holds=, not a mi210 token in regions=
    a = _ap.Namespace(row=rid, pid=int(pid), window_s=int(window_s), regions=regions,
                      reserve=("gpu-quiet" if "mi210" not in regions else None), derived_class=cls, fillers="/dev/null", proc="/proc")
    try:
        return True, gate.check(a)
    except gate.Refuse as r:
        return False, f"refuse rc={r.code}: {r}"
    except (OSError, UnicodeDecodeError) as e:
        return False, f"refuse: launcher check could not read its inputs: {e}"


def disk_free_gib(path=None):
    try:
        return shutil.disk_usage(path or TMP).free / 2**30
    except OSError:
        return None


def disk_budget_refusal(flags, rid, allrows, free_gib=None):
    """None when granting `rid` keeps free disk minus every live grant's budget_gib (and its own) at or above
    DISK_FLOOR_GIB; else the refusal line. Live = grants/<id>.grant without .ended. Unknown free disk => no refusal
    (the filler's own floor still applies)."""
    free_gib = disk_free_gib() if free_gib is None else free_gib
    if free_gib is None:
        return None
    live = 0.0
    for g in open_grants(flags):
        if g["id"] == rid or os.path.exists(os.path.join(flags, "grants", g["id"] + ".ended")):
            continue
        live += float((allrows.get(g["id"]) or {}).get("budget_gib") or 0)
    own = float((allrows.get(rid) or {}).get("budget_gib") or 0)
    head = free_gib - live - own
    if head < DISK_FLOOR_GIB:
        return (f"disk budget: free {free_gib:.0f} GiB - live budgets {live:.0f} GiB - this row {own:.0f} GiB = "
                f"{head:.0f} GiB < {DISK_FLOOR_GIB:.0f} GiB floor")
    return None


def write_grant(flags, rid, regions, holds, window_s):
    start = dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0) - dt.timedelta(minutes=1)
    end = start + dt.timedelta(seconds=int(window_s))
    cpus = grant_cpus(regions)   # ws58 2026-11-02: the exact cpu list (a GRANT_CPUS engine locks + pins a GPU grant to it)
    # Written only when it adds something: for regions that already spell explicit cpus (mi210_0,184-191) the engine's
    # fallback (cpus= else regions) gives the same list, and sealed jobs that parse their grant strictly (inf22 M4:
    # exactly regions/start/end/holds) keep working.
    if cpus == ws58_cpus(regions):
        cpus = ""
    line = (f"regions={regions} start={start:%Y-%m-%dT%H:%MZ} end={end:%Y-%m-%dT%H:%MZ} holds={','.join(compress(holds))}"
            + (f" cpus={cpus}" if cpus else "") + "\n")
    p = os.path.join(flags, "grants", rid + ".grant")
    with open(p + ".tmp", "w") as f:
        f.write(line)
    os.replace(p + ".tmp", p)
    return line.strip()


# ---------------------------------------------------------------- invariants (self-healing, every tick)
def state_dir(flags):
    p = os.path.join(flags, "ws58-keeper-state", "allocator")
    os.makedirs(p, exist_ok=True)
    return p


def repeat_alert(flags, seen, log):
    """Count consecutive ticks a HEAL/UNDERUSED/CONFLICT condition is seen; the 3rd repeat raises an alert (ws58-keeper-alerts.jsonl)."""
    p = os.path.join(state_dir(flags), "repeats.json")
    old = load_json(p) or {}
    new = {}
    for k in seen:
        new[k] = int(old.get(k, 0)) + 1
        if new[k] == ALERT_REPEATS:
            log(f"ALERT {k} repeated {ALERT_REPEATS} ticks")
            with open(os.path.join(flags, "ws58-keeper-alerts.jsonl"), "a") as f:
                f.write(json.dumps({"ts": now_iso(), "from": "rowflow-allocator", "kind": "repeat", "condition": k, "repeats": ALERT_REPEATS}) + "\n")
    atomic_json(p, new)


def heal_grants(flags, grants, rl, log, seen, allrows=None):
    """(c) a grant whose region another job holds is re-assigned (grant removed before the poller started; the row is
    grantable again next tick); a grant whose poller/dry-run pid is dead with no end record is stale (moved aside)."""
    keep = []
    stale_dir = os.path.join(flags, "grants", "stale-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    for g in grants:
        rid = g["id"]
        ended = os.path.exists(os.path.join(flags, "grants", rid + ".ended")) or os.path.exists(os.path.join(flags, "grants", rid + ".complete"))
        if g["pid"] and not alive(g["pid"]) and not ended and not g["dryrun"]:
            os.makedirs(stale_dir, exist_ok=True)
            shutil.move(g["path"], os.path.join(stale_dir, os.path.basename(g["path"])))
            log(f"HEAL stale-grant {rid}: poller pid {g['pid']} dead, no .ended; grant moved to {os.path.basename(stale_dir)}/ (row re-granted when free)")
            seen.add(f"stale-grant:{id_stem(rid)}")
            continue
        foreign = [r for r in g["holds"] if r in REGIONS and r in rl and rl[r][0] != "free" and rl[r][1] not in ("", f"filler-{rid}")]
        if allrows and shape_of(allrows.get(rid) or {}) == "quiet-host":   # COEXIST: a coexist row on q3 is no conflict
            foreign = [r for r in foreign if not (r == "q3" and is_coexist(allrows.get(rl[r][1][len("filler-"):])))]
        if foreign:
            holder = ",".join(f"{r}={rl[r][1]}" for r in foreign)
            if not g["started"] and not g["dryrun"]:
                os.remove(g["path"])
                log(f"HEAL conflict {rid}: granted onto {holder} held by another job before START; grant withdrawn, re-assigned next tick")
                seen.add(f"conflict:{rid}")
                continue
            log(f"CONFLICT {rid}: running on {holder} held by another job (engine queued in region-lock); not killed")
            seen.add(f"conflict:{rid}")
        keep.append(g)
    return keep


def cpu_sample():
    """per-cpu (busy, total) jiffies from /proc/stat."""
    out = {}
    try:
        for l in open("/proc/stat"):
            if l.startswith("cpu") and l[3].isdigit():
                f = l.split(); v = [int(x) for x in f[1:9]]
                out[int(f[0][3:])] = (sum(v) - v[3] - v[4], sum(v))
    except (OSError, ValueError, IndexError):
        pass
    return out


def underused(flags, holders, log, seen, sample=None, now=None, vram=None):
    """(b) a held quarter whose CPUs are < 5 % busy for 10 minutes under the same holder is UNDERUSED (logged + an owner fix
    task dryrun/<id>/UNDERUSED.json); never killed. holders: region -> row id. Pure given sample/now/vram (tests)."""
    now = now or time.time()
    sample = cpu_sample() if sample is None else sample
    p = os.path.join(state_dir(flags), "usage.json")
    hist = load_json(p) or {"samples": []}
    hist["samples"] = [s for s in hist["samples"] if now - s["ts"] <= UNDERUSED_S * 2][-12:] + \
        [{"ts": now, "cpu": {str(k): v for k, v in sample.items()}, "holders": holders, "vram": vram}]
    atomic_json(p, hist)
    out = []
    for r, rid in holders.items():
        span = [s for s in hist["samples"] if s.get("holders", {}).get(r) == rid]
        if not span or now - span[0]["ts"] < UNDERUSED_S:
            continue
        s0 = span[0]
        if r == GPU and list(holders.values()).count(rid) > 1:
            continue  # quiet-host/host-sized row: gpu-quiet is held for silence, its quarters carry the usage check
        if r == GPU:
            vals = [s.get("vram") for s in span if s.get("vram") is not None]
            pct = 100.0 if not vals else (100.0 if max(vals) >= 64 << 20 else 0.0)
        else:
            lo = int(r[1]) * 24; cpus = list(range(lo, lo + 24)) + list(range(lo + 96, lo + 120))
            b0 = sum(s0["cpu"].get(str(c), (0, 0))[0] for c in cpus); t0 = sum(s0["cpu"].get(str(c), (0, 0))[1] for c in cpus)
            b1 = sum(sample.get(c, (0, 0))[0] for c in cpus); t1 = sum(sample.get(c, (0, 0))[1] for c in cpus)
            pct = 100.0 * (b1 - b0) / (t1 - t0) if t1 > t0 else 100.0
        if pct < UNDERUSED_PCT:
            out.append((r, rid, pct))
            seen.add(f"underused:{r}:{rid}")
            log(f"UNDERUSED {r} {rid}: {pct:.1f}% of its CPUs busy over {int(now - s0['ts'])}s (<{UNDERUSED_PCT:g}%); not killed; owner fix task dryrun/{rid}/UNDERUSED.json")
            fp = os.path.join(dry_dir(flags, rid), "UNDERUSED.json")
            if not os.path.exists(fp):
                os.makedirs(dry_dir(flags, rid), exist_ok=True)
                atomic_json(fp, {"id": rid, "at": now_iso(), "region": r, "busy_pct": round(pct, 1), "window_s": int(now - s0["ts"]),
                                 "fix_task": f"{rid} holds {r} but uses {pct:.1f}% of it: shrink its regions/claim (a fetch or single-core job is not a quarter row), or split the row"})
    return out


IDLE_HELD_AFTER_S = 60   # a grant older than this whose regions measure < hostutil.IDLE_PCT busy is IDLE-HELD


def measure_util(sample_s=hostutil.SAMPLE_S):
    """One measured utilisation reading per tick (patched in tests)."""
    return hostutil.measure(sample_s)


def idle_held(flags, grants, holders, util, log, seen, now=None):
    """2026-11-03 session review item 2: every held region is judged by MEASUREMENT, not by its grant file - a grant
    older than IDLE_HELD_AFTER_S whose region reads < IDLE_PCT busy logs IDLE-HELD (one line: region, row, %, age,
    where the logs are). Never kills, never de-grants; the 3rd consecutive tick raises the repeat ALERT. Returns the
    [(region, rid, pct)] list."""
    now = time.time() if now is None else now
    age = {}
    for g in grants:
        try:
            age[g["id"]] = int(now - os.path.getmtime(g["path"]))
        except OSError:
            continue
    out = []
    for r, rid in sorted(holders.items()):
        if rid not in age or age[rid] <= IDLE_HELD_AFTER_S:
            continue
        v = hostutil.regions_pct(util, [r]).get(r)
        if v is not None and v < hostutil.IDLE_PCT:
            out.append((r, rid, v))
            seen.add(f"idle-held:{r}:{rid}")
            log(f"IDLE-HELD {r} {rid}: measured {v:.0f}% busy, grant {age[rid]}s old; logs {dry_dir(flags, rid)}")
    return out


# ---------------------------------------------------------------- allocate: ONE snapshot, dry runs + grants together
def host_snapshot(flags, grants=None, rl=None):
    """(busy, free, holders) token sets of ONE snapshot: region-lock holds, open grants' holds and live smokes (a smoke
    holds its cpus by taskset, not region-lock, so only its RUNNING/SMOKE-PLACED record makes it visible)."""
    grants = open_grants(flags) if grants is None else grants
    rl = rl_status() if rl is None else rl
    # a quarter held in region-lock by sub-quarter grants (LOCK_SH + per-core locks) is busy only on those cores
    subq = {q for g in grants for q in QUARTERS if q not in g["holds"] and g["holds"] & qcores(q)}
    busy = expand({r for r, (s, _) in rl.items() if s != "free" and r not in subq})
    gids = {g["id"] for g in grants}
    for r, (s, t) in rl.items():   # a foreign (non-grant) region-lock hold folds SMT siblings: all 24 of its threads
        if s != "free" and r in QUARTERS and r not in subq and t[len("filler-"):] not in gids:
            busy |= qthreads(r, 24)
    holders = {r: t[len("filler-"):] for r, (s, t) in rl.items() if s != "free" and t.startswith("filler-") and r not in subq}
    for g in grants:
        busy |= g["holds"]
        for r in g["holds"]:
            if r in REGIONS:
                holders.setdefault(r, g["id"])
    busy |= live_smoke_tokens(flags)
    busy |= {q for q in QUARTERS if expand({q}) & busy}   # a quarter with any held core/thread is not whole-free
    free = (set(REGIONS) | set(CORES) | set(THREADS)) - busy
    return busy, free, holders


# ---------------------------------------------------------------- keeper-scheduled smokes (operator 2026-11-05)
SMOKE_CPUS = 4
def smoke_queued_path(flags, rid): return os.path.join(dry_dir(flags, rid), "SMOKE-QUEUED.json")
def smoke_placed_path(flags, rid): return os.path.join(dry_dir(flags, rid), "SMOKE-PLACED.json")


def live_smoke_tokens(flags):
    """cpu tokens of every live CPU smoke (RUNNING.json from dryrun_run, SMOKE-PLACED.json from the keeper)."""
    out = set()
    for pat in ("RUNNING.json", "SMOKE-PLACED.json"):
        for p in glob.glob(os.path.join(flags, "dryrun", "*", pat)):
            r = load_json(p) or {}
            if r.get("pid") and alive(r["pid"]):
                out |= cpu_tokens(ws58_cpus(r.get("regions")))
    return out


def cpu_ranges(cs):
    cs, out = sorted(cs), []
    for c in cs:
        if out and c == out[-1][1] + 1:
            out[-1][1] = c
        else:
            out.append([c, c])
    return ",".join(f"{a}-{b}" if b > a else str(a) for a, b in out)


def pick_smoke_cpus(free, n=SMOKE_CPUS):
    """n physical cores (with their SMT siblings) of ONE quarter, all genuinely free; a partly used quarter first so a
    whole free quarter stays whole for a row; never the MI210 host threads. None when nothing fits."""
    best = None
    for q in QUARTERS:
        cs = [int(c[1:]) for c in sorted(qcores(q), key=lambda t: int(t[1:]))
              if c in free and f"t{int(c[1:]) + 96}" in free and int(c[1:]) + 96 not in GPU_HOST_THREADS]
        if len(cs) < n:
            continue
        key = (q in free, q)   # a partly used quarter (q not whole-free) sorts first
        if best is None or key < best[0]:
            best = (key, cs[:n])
    return cpu_ranges(best[1]) if best else None


def place_smokes(flags, free, log=print, dry=False, n=SMOKE_CPUS, reserved=frozenset()):
    """Every queued CPU smoke (dryrun/<id>/SMOKE-QUEUED.json, oldest first) gets n free cores, and its smoke starts
    detached through publish_row.py --run-smoke (the same dryrun_run path). `free` is updated in place. No free cores is
    WAIT (logged), never a failure. Returns the placed (rid, cpus)."""
    placed = []
    qs = sorted(glob.glob(os.path.join(flags, "dryrun", "*", "SMOKE-QUEUED.json")),
                key=lambda p: ((load_json(p) or {}).get("queued_at") or "", p))
    for q in qs:
        rid = os.path.basename(os.path.dirname(q))
        pl = load_json(smoke_placed_path(flags, rid)) or {}
        if pl.get("pid") and alive(pl["pid"]):
            continue   # running; its cpus are already in busy
        want = int((load_json(q) or {}).get("cpus") or n)
        cpus = pick_smoke_cpus(free - reserved, want)
        if not cpus:
            log(f"SMOKE-WAIT {rid}: no {want} free cores this tick; stays queued (not a failure)")
            continue
        toks = cpu_tokens(cpus)
        free -= toks
        free -= {qq for qq in QUARTERS if expand({qq}) & toks}
        if dry:
            log(f"PLAN smoke {rid} cpus={cpus}"); placed.append((rid, cpus)); continue
        try:
            out = open(os.path.join(dry_dir(flags, rid), "smoke-runner.out"), "a")
            p = subprocess.Popen([sys.executable, os.path.join(_HERE, "publish_row.py"), "--run-smoke", rid,
                                  "--regions", cpus, "--flags", flags], stdout=out, stderr=subprocess.STDOUT,
                                 stdin=subprocess.DEVNULL, start_new_session=True)
            atomic_json(smoke_placed_path(flags, rid), {"id": rid, "pid": p.pid, "regions": cpus, "at": now_iso()})
            log(f"SMOKE-PLACE {rid} cpus={cpus} pid={p.pid} (log {os.path.join(dry_dir(flags, rid), 'launcher.out')})")
            placed.append((rid, cpus))
        except Exception as e:  # noqa: BLE001 - one smoke never stops the tick
            log(f"ERROR smoke {rid}: {type(e).__name__}: {e}")
    return placed


def allocate(flags, keeper_log=None, log=print, dry=False):
    """dry=True: snapshot + plan only (PLAN lines); nothing healed, armed, granted or started."""
    keeper_log = keeper_log or os.path.join(flags, "ws58-calendar-keeper.log")
    if glob.glob(os.path.join(flags, "HOLD_*")):
        log("HOLD present; nothing allocated"); return []
    seen = set()
    if not dry:
        try:
            finish_withdrawals(flags, log)
        except Exception as e:  # noqa: BLE001 - never stops allocation
            log(f"WITHDRAW-FINISH failed: {type(e).__name__}: {e}")
    allrows = rows(flags)
    rl = rl_status()
    grants = open_grants(flags) if dry else heal_grants(flags, open_grants(flags), rl, log, seen, allrows)
    gids = {g["id"] for g in grants}
    busy, free, holders = host_snapshot(flags, grants, rl)
    # keeper-scheduled smokes (operator 2026-11-05 "that's the keeper's ENTIRE point"): placed FIRST, ahead of every row,
    # the cores they take leave `free` before the plan below sees it
    # on genuinely free cores only; while a quiet-host / gpu-q3 grant runs, the q3 COEXIST cores stay the coexist rows'
    quiet_open = any(g["id"] in allrows and shape_of(allrows[g["id"]]) in QUIET_SHAPES for g in grants)
    place_smokes(flags, free, log, dry=dry, reserved=COEXIST_Q3 if quiet_open else frozenset())
    gpu_open = any(GPU in g["holds"] for g in grants)
    # COEXIST (operator 2026-11-05): tokens held by running coexist / quiet-host grants
    coexist_held = set().union(*[g["holds"] for g in grants if is_coexist(allrows.get(g["id"]))])
    quiet_held = set().union(*[g["holds"] for g in grants if g["id"] in allrows and shape_of(allrows[g["id"]]) in QUIET_SHAPES])
    if GPU in free and not dry and start_gpu_batch(flags, log):
        free.discard(GPU)  # queued GPU smokes run in the gap before the next GPU grant
    counts = lane_counts(flags, allrows)
    cands = []
    for rid, d in allrows.items():
        sd = status(flags, rid, allrows)
        st = sd["state"]
        if st not in ("grantable", "armed"):
            continue  # operator 2026-11-02: the dry run is publish_row's smoke; only PASSed rows are granted
        kind = "grant"
        # 2026-11-03 session review item 2: UNDERUSED alerts, never blocks (it de-granted r3 for its engine's spin).
        opts, bench = row_shape(d)
        since = (load_json(pass_path(flags, rid)) or {}).get("passed_at")
        window = int(d["window_s"])
        cands.append({"id": rid, "kind": kind, "lane": d["lane"], "rank": row_rank(d), "lane_count": counts[d["lane"]],
                      "gib": int(d.get("gib") or 0), "bench": bench, "options": opts, "shape": shape_of(d), "window_s": window,
                      "since": iso_epoch(since), "ports": list(d.get("ports") or []), "arm_fails": int(sd.get("arm_fails") or 0),
                      "busy_fraction": d.get("busy_fraction"), "coexist": is_coexist(d)})
    dfile = os.path.join(flags, "drain_state.json")
    drain_prev = {k: v for k, v in (load_json(dfile) or {}).items() if k in allrows}
    held_ports = {int(p) for g in grants for p in ((allrows.get(g["id"]) or {}).get("ports") or [])}
    ends = [iso_epoch(g["end"]) for g in grants if g.get("end")]
    out, excluded, plan_free, ram = [], set(), set(free), mem_available_gib()
    util = measure_util()
    idle_held(flags, grants, holders, util, log, seen)
    # 2026-11-03 session review item 7: a row that fails to arm or is refused at admission no longer idles the regions
    # planned for it until the next tick - the tick re-plans the still-free regions without it (bounded by the number
    # of candidates); plan_order already puts arm-failed rows last so a healthy row is never behind one.
    for _pass in range(len(cands) + 1):
        assigned, idle, pending = plan(plan_free, [c for c in cands if c["id"] not in excluded], ram, gpu_open,
                                        grant_ends=[e for e in ends if e], quiet_ok=quiet_ok_now(flags), held_ports=held_ports,
                                        drain_prev=drain_prev, coexist_held=coexist_held, quiet_held=quiet_held)
        if not dry:
            atomic_json(dfile, {plan.last_drain[0]["id"]: plan.last_drain[1]} if plan.last_drain else {})
        for hc, bc in plan.drain_held:
            log(f"DRAIN-HELD {hc['id']} (rank {hc['rank']:g}, {hc.get('shape')}): better-ranked {bc['id']} (rank {bc['rank']:g}) wants its regions; no drain")
        for lc in plan.drain_lowbusy:
            log(f"NO-DRAIN {lc['id']} ({lc.get('shape')}): busy_fraction {row_busy(lc):g} < {DRAIN_MIN_BUSY:g}, so it never books a "
                f"quiet/whole host and runs only when its regions are free; fix (if it really keeps its claim busy): set "
                f"busy_fraction >= {DRAIN_MIN_BUSY:g} in its spec and republish with publish_row.py")
        for lc, hc, T in plan.rank_holds:
            log(f"RANK-HOLD {lc['id']} (rank {lc['rank']:g}): better-ranked {hc['id']} (rank {hc['rank']:g}) waits for its "
                f"regions until {dt.datetime.fromtimestamp(T, dt.timezone.utc):%H:%MZ}; only rows ending by then may take them")
        for lc, hc, why in plan.rank_skips:
            log(f"RANK-SKIP {hc['id']} (rank {hc['rank']:g}) blocked by its own constraint: {why}; lower-ranked {lc['id']} "
                f"(rank {lc['rank']:g}) may take its regions")
        if plan.last_drain:
            dc, T = plan.last_drain
            log(f"DRAIN {dc['id']} ({dc.get('shape')}) until {dt.datetime.fromtimestamp(T, dt.timezone.utc):%Y-%m-%dT%H:%MZ}: new rows only if they end before then")
        if _pass == 0:
            log(f"SNAPSHOT free={','.join(compress(free)) or '-'} busy={','.join(f'{r}:{holders.get(r, '?')}' for r in compress(busy)) or '-'} "
                f"cands={len(cands)} assigned={len(assigned)} lanes cpu={counts['cpu']} gpu={counts['gpu']} {hostutil.line(util)}")
        failed = []
        for c, opt in assigned:
            rid, d = c["id"], allrows[c["id"]]
            regions = grant_regions(d, opt)
            if dry:
                log(f"PLAN {c['kind']} {rid} regions={regions} holds={','.join(compress(opt))} lane={c['lane']} rank={c['rank']:g}"); continue
            try:  # one row's failure never aborts the tick (22:33Z: an import error after ROW-ARM left q0 ungranted for 3 ticks)
                why = disk_budget_refusal(flags, rid, allrows)
                if why:   # host condition, not the row: no FAIL recorded, retried next tick
                    log(f"WAIT {rid}: {why}")
                    failed.append(rid); continue
                a = load_json(armed_path(flags, rid))
                if a and alive(a.get("pid")) and not armed_engine_ok(a.get("pid"), rid):
                    log(f"RE-ARM {rid}: ARMED pid {a.get('pid')} runs no filler_run*.sh engine for this row (not killed; re-armed)")
                    a = None
                if not (a and alive(a.get("pid"))):
                    pid, msg = arm_one(flags, rid, d, regions, log=log)
                    log(f"ROW-ARM {msg}")
                    if not pid:
                        failed.append(rid); continue
                else:
                    pid = a["pid"]
                ok, line = admit(flags, rid, d, pid, regions, d["window_s"])
                if not ok:
                    n = record_arm_fail(flags, rid, d, "launch", f"admission refused the armed poller: {line[:300]}", log)
                    log(f"SKIP {rid}: {line[:200]} ({n} consecutive arming/launch failures since the PASS; parked at {MAX_FAILS})")
                    failed.append(rid); continue
                gl = write_grant(flags, rid, regions, opt, d["window_s"])
                atomic_json(granted_path(flags, rid), {"id": rid, "at": now_iso(), "regions": regions, "pid": pid})  # resets the arm-fail count
                log(f"GRANT {rid} {gl} ({line[:160]})")
                out.append(("grant", rid, regions))
                plan_free -= expand(set(opt)); ram -= float(c.get("gib") or 0)
            except Exception as e:  # noqa: BLE001 - logged, counted, alerted on repeat
                log(f"ERROR {rid}: {type(e).__name__}: {e}")
                seen.add(f"error:{rid}"); failed.append(rid)
        if dry or not failed:
            break
        excluded |= set(failed)
        plan_free = {t for t in plan_free if t not in QUARTERS or expand({t}) <= plan_free}
        if not any(c["id"] not in excluded for c in pending):
            break
        log(f"RE-PLAN same tick: {','.join(sorted(failed))} failed to arm/launch; free={','.join(compress(plan_free)) or '-'}")
    for r, why in idle.items():
        log(f"IDLE-WHY {r}: {why}")
    left = plan_free - expand(set().union(*[o for _, o in assigned])) if assigned else plan_free
    for c in pending:
        if c["kind"] == "grant" and any(o <= left for o in c["options"]) and not (c.get("bench") and gpu_open):
            seen.add(f"idle-violation:{c['id']}"); log(f"IDLE-VIOLATION {c['id']} fits {','.join(compress(free))} but was not placed")
    if not dry:
        try:  # host disk floor: ONE alert per crossing (hysteresis), naming the rows it blocks; never deletes
            blocked = sorted(gids | {c["id"] for c in cands})
            if notify.disk_floor_check(flags, os.path.join(state_dir(flags), "disk_floor.json"), blocked,
                                       reclaim_root=TMP, log=log) == "raised" and notify.is_live(flags):
                route_alert("disk-floor", f"/mnt/raid0 below FILLER_DISK_FLOOR_GIB; {len(blocked)} rows blocked; see rowflow-alerts.jsonl",
                            {"rows_blocked": blocked[:50]}, log)
        except Exception as e:  # noqa: BLE001 - an alerting fault must not stop allocation
            log(f"DISK-FLOOR check failed: {type(e).__name__}: {e}")
        try:  # inference mailbox: a CRITICAL alert unacked for ROWFLOW_ALERT_ESCALATE_S -> operator alarm, exactly once
            if notify.is_live(flags):
                notify.escalate_stale(flags, lambda k, m, ev: route_alert(f"{k}-{ev['key']}", m, ev, log), log=log)
        except Exception as e:  # noqa: BLE001
            log(f"ALERT-UNACKED check failed: {type(e).__name__}: {e}")
        idle_violation(flags, free, cands, out, mem_available_gib(), gpu_open, held_ports, log, util=util)
        underused(flags, holders, log, seen, vram=vram_used_bytes() if GPU in holders else None)
        repeat_alert(flags, seen, log)
    return out


IDLE_VIOLATION_TICKS = 2


ALARM_CHANNEL = os.environ.get("ROWFLOW_ALARM_CHANNEL", os.path.join(os.path.dirname(os.path.dirname(_HERE)), "coordination", "alarm_channel.py"))


def route_alert(kind, message, evidence, log=print):
    """Push an allocator alert to the operator-reachable alarm channel (alarm_channel.py raise: emits once per state
    change). 2026-11-03 item 2: the IDLE-VIOLATION alert was the one signal that was right all afternoon, and it went
    to a log nobody reads. Best effort: a missing channel is logged, never fatal."""
    if not os.path.isfile(ALARM_CHANNEL):
        log(f"ALERT-ROUTE {kind}: alarm channel {ALARM_CHANNEL} missing; alert only in ws58-keeper-alerts.jsonl")
        return False
    try:
        r = subprocess.run([sys.executable, ALARM_CHANNEL, "raise", "--severity", "warning", "--key", f"rowflow-{kind}",
                            "--message", message, "--evidence", json.dumps(evidence)], capture_output=True, text=True, timeout=30)
        log(f"ALERT-ROUTE {kind}: rc={r.returncode} {(r.stdout or r.stderr).strip()[:160]}")
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired) as e:
        log(f"ALERT-ROUTE {kind}: {type(e).__name__}: {e}")
        return False


def idle_violation(flags, free, cands, granted, ram_gib, gpu_open=False, held_ports=(), log=print, util=None):
    """ws58 2026-11-03 (the yarn-e1-a2 deadlock: 7 h with every region free and nothing granted). Free regions + a
    grantable row that fits them + no grant written this tick, IDLE_VIOLATION_TICKS ticks in a row -> IDLE-VIOLATION
    alert (log every such tick, one ws58-keeper-alerts.jsonl record per episode). Returns the consecutive tick count."""
    p = os.path.join(state_dir(flags), "idle_violation.json")
    old = load_json(p) or {}
    fr = {r for r in free if r in REGIONS}
    if fr and not granted:
        tok = set(free) if any(t in CORES or t in THREADS for t in free) else \
            expand(fr) | ({f"t{k}" for k in range(184, 192)} if GPU in fr else set())
        fit = [c for c in cands if _fits(dict(c, options=[frozenset(expand(o)) for o in c["options"]]), tok, float(ram_gib), gpu_open)
               and not ({int(x) for x in held_ports} & {int(x) for x in (c.get("ports") or [])})]
    else:
        fit = []
    if not fit:
        if old:
            atomic_json(p, {})
        return 0
    n = int(old.get("ticks") or 0) + 1
    since = old.get("since") or now_iso()
    atomic_json(p, {"ticks": n, "since": since, "alerted": bool(old.get("alerted")) or n >= IDLE_VIOLATION_TICKS})
    if n >= IDLE_VIOLATION_TICKS:
        ids = ",".join(c["id"] for c in fit[:6]) + (f",+{len(fit) - 6}" if len(fit) > 6 else "")
        msg = (f"IDLE-VIOLATION ALERT {n} ticks since {since}: free {','.join(compress(fr))}, {len(fit)} grantable row(s) fit "
               f"({ids}), nothing granted" + (f"; {hostutil.line(util)}" if util else ""))
        log(msg)
        if not old.get("alerted"):
            rec = {"ts": now_iso(), "from": "rowflow-allocator", "kind": "idle-violation", "ticks": n, "since": since,
                   "free": sorted(fr), "grantable_fit": [c["id"] for c in fit], "util": util}
            with open(os.path.join(flags, "ws58-keeper-alerts.jsonl"), "a") as f:
                f.write(json.dumps(rec) + "\n")
            route_alert("idle-violation", msg, rec, log)
    return n


# ---------------------------------------------------------------- queued GPU smokes (operator 2026-11-02)
def gpu_batch_lock(flags): return os.path.join(flags, "dryrun", "GPU-SMOKE-BATCH.lock")


def gpu_batch_running(flags):
    """A detached queued-GPU-smoke batch is alive (its lock names a live pid); a dead lock is removed."""
    lk = gpu_batch_lock(flags)
    pid = (load_json(lk) or {}).get("pid")
    if pid and alive(pid):
        return True
    if os.path.exists(lk):
        try:
            os.remove(lk)
        except OSError:
            pass
    return False


def release_gpu_batch(flags):
    try:
        os.remove(gpu_batch_lock(flags))
    except OSError:
        pass


def start_gpu_batch(flags, log):
    """GPU free + queued smokes: start ONE detached batch (publish_row.py --run-gpu-queue) under a lock. True = the
    batch owns the GPU this tick (running or just started), so no GPU grant is assigned."""
    if gpu_batch_running(flags):
        return True
    if not glob.glob(os.path.join(flags, "dryrun", "*", "GPU-SMOKE-QUEUED.json")):
        return False
    os.makedirs(os.path.join(flags, "dryrun"), exist_ok=True)
    out = open(os.path.join(flags, "dryrun", "GPU-SMOKE-BATCH.out"), "a")
    p = subprocess.Popen([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "publish_row.py"),
                          "--run-gpu-queue", "--flags", flags], stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                         start_new_session=True)
    atomic_json(gpu_batch_lock(flags), {"pid": p.pid, "started": now_iso()})
    log(f"GPU-SMOKE-BATCH started pid={p.pid}")
    return True


def gpu_batch(flags, log=print):
    """`rowflow.py gpu-batch` (session review 2026-11-03 §5 item 8): ANY session runs the queued GPU smokes on a GPU-free
    tick - the same start_gpu_batch the allocator calls on every allocate tick (that path is unchanged). One line out.
    Returns 0 (started / already running / nothing queued) or 3 (HOLD present or GPU busy: re-run later)."""
    me = f"python3 {os.path.abspath(__file__)} gpu-batch"
    queued = glob.glob(os.path.join(flags, "dryrun", "*", "GPU-SMOKE-QUEUED.json"))
    holds = glob.glob(os.path.join(flags, "HOLD_*"))
    if holds:
        log(f"HOLD present ({os.path.basename(holds[0])}): {len(queued)} queued GPU smoke(s) not started; re-run `{me}` after the HOLD is removed")
        return 3
    if gpu_batch_running(flags):
        log(f"GPU-SMOKE-BATCH already running pid={(load_json(gpu_batch_lock(flags)) or {}).get('pid')}; "
            f"log {os.path.join(flags, 'dryrun', 'GPU-SMOKE-BATCH.out')}")
        return 0
    if not queued:
        log("no queued GPU smokes; nothing to do")
        return 0
    rl = rl_status().get(GPU, ("free", ""))
    holder = f"region-lock {GPU} {rl[0]} {rl[1]}".strip() if rl[0] != "free" else \
        next((f"grant {g['id']}" for g in open_grants(flags) if GPU in g["holds"]), None)
    if holder:
        log(f"GPU busy ({holder}): {len(queued)} queued GPU smoke(s) wait for the next GPU gap; re-run `{me}` then "
            "(the allocator also runs them on its next GPU-free tick)")
        return 3
    start_gpu_batch(flags, lambda m: log(f"{m}; log {os.path.join(flags, 'dryrun', 'GPU-SMOKE-BATCH.out')}"))
    return 0


# ---------------------------------------------------------------- cli
def status_text(st):
    """The fixed <= 8-line form (2026-11-03 operator design goal): state, measured util, blocker, next, logs."""
    L = [f"id:      {st['id']}", f"state:   {st['state']} - {str(st.get('reason', ''))[:160]}"]
    if st.get("held") is not None:
        u = st.get("util") or {}
        L.append("util:    " + (" ".join(f"{r}={hostutil.pct(u.get(r))}" for r in st["held"]) or "-") + f"  (held {','.join(st['held']) or '-'}, grant {st.get('grant_age_s', '?')}s old, measured now)")
    L.append(f"blocker: {st.get('blocker') or '-'}")
    L.append(f"next:    {st.get('next', '-')}")
    L.append(f"logs:    {st.get('logs', '-')}")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--flags", default=FLAGS)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("publish"); s.add_argument("spec"); s.add_argument("--migrate", action="store_true", help="spec is a legacy ready/<id>.json manifest")
    s = sub.add_parser("status"); s.add_argument("id"); s.add_argument("--json", action="store_true")
    sub.add_parser("list")
    s = sub.add_parser("withdraw", help="end a row that will never run: manifest -> ready/.withdrawn/, grants/<id>.ended rc=75, STOP touched")
    s.add_argument("id"); s.add_argument("--reason", required=True)
    s = sub.add_parser("allocate", help="ONE snapshot per tick: heal, assign dry runs + grants together, write grants, log IDLE-WHY/UNDERUSED")
    s.add_argument("--log", help="keeper log the detached dry runs append DRYRUN-RESULT to (default <flags>/ws58-calendar-keeper.log)")
    s.add_argument("--plan", action="store_true", help="snapshot + plan only; change nothing")
    sub.add_parser("gpu-batch", help="run the queued GPU smokes now if the GPU is free (any session; the allocator does the same every tick)")
    s = sub.add_parser("alerts", help="read the inference mailbox (<flags>/notify/inbox/inference.jsonl); --ack <key> marks one handled")
    s.add_argument("--since", help="ISO time, e.g. 2026-11-05T07:00:00Z"); s.add_argument("--row", help="row-id glob")
    s.add_argument("--unacked", action="store_true"); s.add_argument("--json", action="store_true")
    s.add_argument("--ack", metavar="KEY"); s.add_argument("--by"); s.add_argument("--note")
    a = ap.parse_args(argv)
    if a.cmd == "alerts":
        if a.ack:
            if not notify.ack(a.flags, a.ack, a.by, a.note):
                print(f"REFUSED: no alert with key {a.ack} in {notify.inbox_path(a.flags)}")
                return 2
            print(f"ACKED {a.ack}")
            return 0
        acks = notify.acked_keys(a.flags)
        for r in notify.read_inbox(a.flags, a.since, a.row, a.unacked):
            if a.json:
                print(json.dumps(dict(r, acked=r.get("key") in acks), sort_keys=True))
            else:
                print(f"{r.get('ts')} {'ACKED ' if r.get('key') in acks else 'OPEN  '}{str(r.get('severity')):8} {r.get('key')} "
                      f"{r.get('row_id') or '-'} owner={r.get('owner') or '-'} {r.get('summary')}")
        return 0
    try:
        if a.cmd == "publish":
            spec = load_json(a.spec)
            need(spec, f"{a.spec} is not a JSON object")
            if a.migrate:
                spec = spec_from_legacy(spec, a.flags)
            row = publish(spec, a.flags, source=os.path.abspath(a.spec))
            print(published_line(row, a.flags))
            supersede(a.flags, row)
            return 0
        if a.cmd == "withdraw":
            r = withdraw(a.flags, a.id, a.reason)
            print(f"{r} {a.id}")
            return 0 if r in ("WITHDRAWN", "PENDING", "TERMINAL") else 2
        if a.cmd == "status":
            st = status(a.flags, a.id, util=measure_util())
            print(json.dumps(st, indent=1) if a.json else status_text(st))
            return 0 if st["state"] != "unknown" else 2
        if a.cmd == "list":
            allrows = rows(a.flags)
            util = measure_util()
            print(hostutil.line(util))
            for rid in sorted(allrows, key=lambda r: row_rank(allrows[r])):
                st = status(a.flags, rid, allrows, util=util)
                u = " ".join(f"{r}={hostutil.pct(v)}" for r, v in (st.get("util") or {}).items())
                print(f"{st['state']:15} {allrows[rid]['lane']:3} rank={allrows[rid].get('priority_rank')} {rid}  "
                      f"{(u + '  ') if u else ''}{st.get('blocker') or st.get('reason', '')[:100]}")
            return 0
        if a.cmd == "allocate":
            allocate(a.flags, a.log, dry=a.plan)
            return 0
        if a.cmd == "gpu-batch":
            return gpu_batch(a.flags)
    except Refused as e:
        print(f"REFUSED: {e}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
