#!/usr/bin/env python3
"""rowflow.py - the simplified inference-row pipeline (ws58, operator ruling 2026-11-01: remove every gate that is
not indispensable).

OWNER CONTRACT (two things): the launcher script and a small spec. `publish_row.py <spec.json>` derives the rest.

    spec (JSON)      required: id, owner, launcher (abs path, runs filler_run15.sh), lane (cpu|gpu),
                               result_path (what the filer reads), decision_rule, estimate_s, handoff_task
                     optional: result_format (jsonl|json|csv|tsv|text-lines|markdown-table|custom:<cmd>; default by
                               extension), regions (default gpu -> mi210_0,184-191; cpu -> any-cpu-quarter),
                               quiet_guard_regions (list of booked quarters kept idle on purpose, e.g. ["q0","q2"]: the keeper's
                               UNDERUSED skips them, queue_status shows GUARD),
                               busy_fraction (0..1: share of its claimed cpus the job keeps busy; unset = 1.0; below
                               0.5 the row is never promoted to a host/quiet-host drain, only placed on free regions),
                               requires_quiet_host (bool: granted only onto quarters measuring < 15% foreign busy, never on
                               the NUMA side of a whole-host / bandwidth-heavy grant; see QUIET GATE), bandwidth_heavy (bool;
                               unset = heavy iff a declared busy_fraction >= 0.6),
                               ram_gib (48), priority_rank (100), scratch_root (launcher's job dir), keep (globs that
                               ADD reaper protection; empty = inputs (older than the first job start) + result_path),
                               first_progress_s (300; aliases smoke_timeout_s, dryrun_timeout_s), smoke_predicate (shell; exit 0 =
                               the job's first real progress), unit_key (the field a real record must carry), dryrun_native_result
                               (count a unique per-attempt native JSON unit without touching result_path), lineage, lineage_reset,
                               supersedes, snapshot (true forces the snapshot below),
                               coexist_quiet_host (accepted and ignored since the COEXIST path was deleted, Pass 5 2026-11-07)

    gpu-q3 NARROW (operator 2026-11-05 "Narrow + emergency deploy"): a GPU grant holds gpu-quiet + its host threads
                    t184-191; a GPU TIMING grant also holds their SMT-sibling cores 88-95 and NEVER the rest of q3 -
                    cores 72-87 (siblings 168-183) stay grantable to any CPU row beside a GPU timing run. Replaces the
                    rule that a GPU timing run holds all of q3 (q38p4b-int8 refused "q3 busy" by an 8-core build on
                    80-87). A quieter neighbourhood is declared explicitly (regions + shape_override).

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
    resume <id> --by <owner> --reason R   owner-only: a resumable row whose last end was rc=75 reason=stopped|released-early is
                              requeued under the SAME id (STOP + terminal end cleared, manifest back in ready/, PASS kept, out/ and the
                              resume ledger kept, ROW-RESUMED logged); status shows `next: resume (rowflow.py resume <id>)`
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
import itertools
import json
import math
import os
import re
import shlex
import shutil
import stat
import signal
import subprocess
import sys
import time
import fcntl

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:   # the keeper runs `python3 -I`: isolated mode does not put the script's directory on sys.path
    sys.path.insert(0, _HERE)
import hostutil  # noqa: E402  - measured CPU%/GPU% for every status surface (2026-11-03 session review item 2)
import diskpause  # noqa: E402  - disk floor = pause with hysteresis + HOLD-ADMISSIONS (operator 2026-11-07)
import notify  # noqa: E402  - push every terminal event / smoke FAIL / disk-floor crossing (incident 2026-11-04)
try:
    import handoff_ref  # noqa: E402  (installed beside this file in bin/rowflow)
except ImportError:  # repo checkout: scripts/coordination/handoff_ref.py
    sys.path.insert(0, os.path.dirname(_HERE))
    try:
        import handoff_ref  # noqa: E402
    except ImportError:  # a copied candidate dir (replay gate) has no sibling: repointing degrades to identity
        class handoff_ref:  # noqa: N801
            @staticmethod
            def repoint(ref, root=None, sha=None, moves=None):
                return ref

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
    """True for a live process. A ZOMBIE (exited, not yet reaped) is NOT alive: a smoke whose bash exited but sits <defunct>
    otherwise kept its RUNNING.json regions busy until the deadline (AK 2026-11-20: q3 + GPU idle, "held by ?")."""
    try:
        if not pid:
            return False
        r = subprocess.run(["ps", "-o", "stat=", "-p", str(int(pid))], capture_output=True, text=True)
        return r.returncode == 0 and not r.stdout.strip().startswith("Z")
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
    """[FAIL records] of the consecutive arming/launch failures since the row's PASS, its last successful grant and its
    last operator UNPARK (ws58 2026-11-03: yarn-e1-a2-gpu failed to arm 172 times after its PASS and stayed grantable
    all night)."""
    p = load_json(pass_path(flags, rid)) if p is None else p
    t0 = max(iso_epoch((p or {}).get("passed_at")) or 0.0, iso_epoch((load_json(granted_path(flags, rid)) or {}).get("at")) or 0.0)
    un = iso_epoch((load_json(unpark_path(flags, rid)) or {}).get("at")) or 0.0   # records up to AND IN the unpark second are forgiven
    out = []
    for fp in fail_paths(flags, rid):
        f = load_json(fp) or {}
        at = iso_epoch(f.get("at")) or 0.0
        if is_arm_fail(f) and at >= t0 and (not un or at > un):
            out.append(dict(f, fail_file=fp))
    return sorted(out, key=lambda f: iso_epoch(f.get("at")) or 0.0)


# ---------------------------------------------------------------- parking, fresh attempts, GPU idleness
# docs/reports/coordination/keeper-friction-review-20261105.md Pass 4 (P4.3 / P4.4). A rule still carrying a module flag
# (COMPLETE_BEFORE_RC14) keeps it for the replay gate's negative control; the always-on rules lost theirs 2026-11-10
# (pipeline audit #9; history in docs/reference/agent-config/INCIDENT_LOG.md, INC-20261110-rowflow-switches).
COMPLETE_BEFORE_RC14 = True   # a dead poller whose row has a terminal success receipt is COMPLETE, not rc=14 (11/11 false)
GPU_IDLE_SAMPLES = 2          # consecutive quiet device samples before a GPU grant reads IDLE-HELD
_PRECOND_REFUSED = "refuse rc=12: not ready: precond-cmd failed"


def unpark_path(flags, rid): return os.path.join(dry_dir(flags, rid), "UNPARK.json")


def is_precond_refusal(f):
    """A launch FAIL record whose admission refusal was the launcher's own --precond-cmd (grant_ok_launcher rc=12)."""
    return is_arm_fail(f) and _PRECOND_REFUSED in str((f or {}).get("reason", ""))


def precond_park(flags, rid, cur, p=None):
    """the FAIL record that parks `rid`, or None. A precond refusal is terminal for the row AS PUBLISHED: the newest
    launch refusal by --precond-cmd whose launcher_sha256 == the current launcher and row_sha256 == the current manifest,
    written after the PASS / last grant / last `rowflow.py unpark`. A launcher or spec edit (sha change) or an unpark
    retries it; nothing else does (kpf50 / kpf41: 171 refusals of one unchanged precond, one per tick, 171 alerts)."""
    rs = row_sha(flags, rid)
    for f in reversed(arm_fails_since_pass(flags, rid, p)):
        if is_precond_refusal(f) and f.get("launcher_sha256") == cur and f.get("row_sha256") == rs:
            return f
    return None


def job_sha(launcher_path):
    """sha256 over the launcher and every existing file it references (job.py, engine, ...): a changed JOB with an unchanged
    launcher text is a new attempt too (operator 2026-11-06). None when the launcher cannot be parsed."""
    try:
        files = sorted({os.path.realpath(x) for x in referenced_paths(parse_launcher(launcher_path)) if os.path.isfile(x)}
                       | {os.path.realpath(launcher_path)})
        return hashlib.sha256("\n".join(f"{f} {sha256(f)}" for f in files).encode()).hexdigest()
    except Exception:  # noqa: BLE001
        return None


def lineage_unpark_at(flags, lin, allrows):
    """Epoch of the newest UNPARK.json of the lineage id itself or of any row / dryrun id in the lineage (0 = never)."""
    t = 0.0
    for dd in glob.glob(os.path.join(flags, "dryrun", "*")):
        oid = os.path.basename(dd)
        if oid == lin or id_stem(oid) == lin or (oid in allrows and lineage_of(oid, allrows) == lin):
            t = max(t, iso_epoch((load_json(os.path.join(dd, "UNPARK.json")) or {}).get("at")) or 0.0)
    return t


def counted_fails(flags, oid, un):
    """FAIL files of `oid` that still count against its lineage: newer than the last unpark (records IN the unpark second
    are forgiven, as for arming fails)."""
    out = []
    for fp in fail_paths(flags, oid):
        at = iso_epoch((load_json(fp) or {}).get("at")) or 0.0
        if not un or at > un:
            out.append(fp)
    return out


def fresh_attempt(flags, rid, allrows, cur):
    """Operator 2026-11-06: a parked lineage gives a republish whose launcher or job sha is NEW to the lineage ONE fresh
    attempt without a new id + lineage_reset. Fresh iff no FAIL record in the lineage carries the current launcher sha with
    a matching (or unrecorded) job sha. The attempt's own FAIL then carries the current shas, so the lineage parks again."""
    if not cur:
        return False
    lin = lineage_of(rid, allrows)
    jcur = None
    for dd in glob.glob(os.path.join(flags, "dryrun", "*")):
        oid = os.path.basename(dd)
        if not (oid == rid or id_stem(oid) == lin or (oid in allrows and lineage_of(oid, allrows) == lin)):
            continue
        for fp in fail_paths(flags, oid):
            f = load_json(fp) or {}
            if f.get("launcher_sha256") != cur:
                continue
            if f.get("job_sha256") is None:
                return False
            jcur = jcur or job_sha(allrows[rid]["launcher"]["path"]) if rid in allrows else None
            if jcur is None or f.get("job_sha256") == jcur:
                return False
    return True


def unpark(flags, rid, by="", note=""):
    """Operator unpark: arming/launch FAIL records before this moment no longer count (precond park and the MAX_FAILS
    park alike); the row is grantable again on the next tick if its PASS still matches. Returns the record written."""
    rec = {"id": rid, "at": now_iso(), "by": by or os.environ.get("USER") or "", "note": note}
    os.makedirs(dry_dir(flags, rid), exist_ok=True)
    atomic_json(unpark_path(flags, rid), rec)
    return rec


def terminal_success(flags, rid):
    """the receipt that says `rid`'s job FINISHED - grants/<id>.complete, or grants/<id>.ended whose first line
    reads rc=0 ... reason=complete - else None. A poller that is dead after this receipt completed; it did not die."""
    G = os.path.join(flags, "grants")
    if os.path.exists(os.path.join(G, rid + ".complete")):
        return f"grants/{rid}.complete"
    h = head1(os.path.join(G, rid + ".ended"))
    if h and re.search(r"(^|\s)rc=0(\s|$)", h) and "reason=complete" in h:
        return f"grants/{rid}.ended ({h[:90]})"
    return None


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
           "--cmd": "cmd", "--gpu-quiet": "gpu_quiet", "--claim-cpus": "claim_cpus", "--precond-cmd": "precond_cmd"}
    while j < len(toks):
        t = toks[j]
        if t == "--min-window":
            o["min_window"] = int(toks[j + 1]); j += 2
        elif t == "--port":
            o["ports"] = [int(x) for x in toks[j + 1].split(",") if x]; j += 2
        elif t in one:
            o[one[t]] = toks[j + 1]; j += 2
        elif t in ("--sched-port", "--excl-lock", "--gpu-threads", "--role", "--requires-tool", "--qual-interpreter"):
            if t == "--role":
                o["launch_role"] = toks[j + 1]   # gpushape: read only by gpu_timing_row (row_shape's `role` stays unset)
            j += 2
        elif t == "--no-fold-siblings":
            o["nofold"] = True; j += 1
        elif t in ("--self-claim", "--repeat"):
            j += 1
        else:
            j += 1
    o["argv"] = toks[i:]   # the engine argv as the launcher will exec it (publish's claim check feeds grant_ok_launcher)
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
_OMP_SHELL = re.compile(r"(?:^|[\s;&|('\"])(?:export\s+)?OMP_NUM_THREADS=\d+(?:\s+[\w/.$]|\s*$)")   # the shell env of a command
_COMPUTE_BIN = re.compile(r"llama-(?:server|bench|cli|perplexity|batched-bench)|ik_llama|whisper-|qwentts|\bbench\b")
_TASKSET = re.compile(r"\btaskset\s+(?:-a\s+)?(?:-c|--cpu-list)\s+['\"]?([\d,-]+)")


def count_cpus(cpus):
    n = set()
    for tok in str(cpus or "").split(","):
        tok = tok.strip()
        if re.fullmatch(r"\d+(-\d+)?", tok):
            a, b = (tok.split("-") + [tok])[:2]
            n |= set(range(int(a), int(b) + 1))
    return len(n)


_PY_OMP = re.compile(r"""['"]OMP_NUM_THREADS['"]\s*[:,]\s*['"]?(\d+)\b""")   # {'OMP_NUM_THREADS': '24'} / env['..'] style
_FILLER_THREADS_REQ = re.compile(r"""FILLER_THREADS['"]?\s*\)?\s*(?:!=|==)\s*['"](\d+)['"]""")   # a job that requires its width
_PY_IMPORT = re.compile(r"^\s*(?:import\s+([\w, ]+)|from\s+(\w+)\s+import\b)", re.M)
_SCRIPT_REF = re.compile(r"(?:\$\{?D\}?/)?([A-Za-z0-9_./-]+\.(?:sh|py|bash))\b")


_INFRA_DIRS = ("/compute-flags/bin/", "/scripts/coordination/rowflow/")


def _is_rowflow_infra(f):
    """True for the rowflow engine / keeper sources themselves (deployed bin/ or repo scripts/coordination/rowflow). Their
    comments carry thread numbers (`-t 48`, `-t 10`); scanning them as a job's argv widened r5/r6 from 24 threads to
    48 -> multi-quarter(2) and granted a quarter the job never used (shapefix 2026-11-22)."""
    f = os.path.normpath(f)
    here = os.path.dirname(os.path.abspath(__file__)) + os.sep
    return f.startswith(here) or any(d in f for d in _INFRA_DIRS)


def _job_chain(cmd, max_files=32):
    """[(path, text)] of the job files --cmd runs and, transitively, the scripts they name (absolute, $D/-relative or
    relative to the file's dir / its own D=) and the sibling Python modules they import - where a job's compute process
    actually sets its threads (a wrapper's env is not its worker's)."""
    seen, out, todo = set(), [], []

    def add(f):
        f = os.path.normpath(f)
        if _is_rowflow_infra(f):   # shapefix 2026-11-22: a job that merely NAMES the engine must not make its source evidence
            return False
        if f in seen or len(seen) >= max_files or not os.path.isfile(f):
            return False
        seen.add(f)
        todo.append(f)
        return True
    for m in re.finditer(r"(/[^\s'\"`;|&()<>]+\.(?:sh|py))", cmd or ""):
        add(m.group(1))
    while todo:
        f = todo.pop(0)
        try:
            t = open(f, errors="replace").read()[:1 << 20]
        except OSError:
            continue
        out.append((f, t))
        bases = [os.path.dirname(f)] + [v.strip("\"'") for v in re.findall(r"^[ \t]*(?:export\s+)?D=(\S+)", t, re.M)
                                         if v.strip("\"'").startswith("/")]
        for m in _SCRIPT_REF.finditer(t):
            r = m.group(1)
            if r.startswith("/"):
                add(r)
            else:
                for b in bases:
                    if add(os.path.join(b, r)):
                        break
        if f.endswith(".py"):
            for m in _PY_IMPORT.finditer(t):
                for name in (m.group(1) or m.group(2) or "").split(","):
                    name = name.strip().split(" ")[0]
                    if re.fullmatch(r"\w+", name or ""):
                        add(os.path.join(os.path.dirname(f), name + ".py"))
    return out


def launcher_threads(text, assigns, o):
    """Refinement 1 (keeper-friction review 2026-11-05): the threads the job declares in its argv - -t/--threads N,
    --workers N, OMP_NUM_THREADS=N, taskset -c LIST - in the launcher and in the job file its --cmd names (.sh/.py).
    Variables assigned in the launcher (and ${X:-N} defaults) are expanded. Returns (max threads or None, [evidence])."""
    chain = _job_chain(o.get("cmd") or "")
    direct = re.findall(r"(/[^\s'\"`;|&()<>]+\.(?:sh|py))", o.get("cmd") or "")
    texts = [text] + [t for f, t in chain if f in {os.path.normpath(x) for x in direct}]
    deep = [t for f, t in chain if f not in {os.path.normpath(x) for x in direct}]

    def ex(t):
        for _ in range(3):
            t = re.sub(r"\$\{([A-Za-z_]\w*):-([^}]*)\}", lambda m: assigns.get(m.group(1), m.group(2)), t)
            t = re.sub(r"\$\{([A-Za-z_]\w*)\}|\$([A-Za-z_]\w*)", lambda m: assigns.get(m.group(1) or m.group(2), m.group(0)), t)
        return t
    v, ev = _scan_threads(texts, ex)
    if v is not None:
        # files the job reaches transitively (scripts it runs, modules it imports) and the Python-env / required-width
        # forms only ever RAISE a known width: smoke branches (taskset 124,125 / -t 2) and helper envs must not shrink
        # an unknown row (keeper classfix 2026-11-05)
        dv, dev = _scan_threads(texts + deep, ex, py=True)
        if dv is not None and dv > v:
            v, ev = dv, sorted(set(ev) | set(dev))
    return v, ev


def _scan_threads(texts, ex, py=False):
    best, tsk, omp, ev = None, None, None, []
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
                # OMP_NUM_THREADS counts only on a compute binary's own environment (same line), never a helper's
                # (inf75-c5-w3-halfb-census 2026-11-05: job.py's helper env OMP_NUM_THREADS='1' refused -t 48 serving)
                if name == "OMP_NUM_THREADS" and not (_COMPUTE_BIN.search(line) or _OMP_SHELL.search(line)):
                    continue
                for m in rx.finditer(line):
                    n = int(m.group(1))
                    if 0 < n <= 192:
                        ev.append(f"{name} {n}")
                        if name == "OMP_NUM_THREADS":
                            omp = max(omp or 0, n)
                        else:
                            best = max(best or 0, n)
            # the compute process's own env / required width in Python (keeper classfix 2026-11-05, yarn-oolong v38:
            # job_side.py ran llama-server with {'OMP_NUM_THREADS':'24'} and refused FILLER_THREADS != '24', while
            # launch.sh's blanket `export OMP_NUM_THREADS=1` was the only evidence read -> 4-core grant)
            for m in (_PY_OMP.finditer(line) if py else ()):
                n = int(m.group(1))
                if 0 < n <= 192:
                    ev.append(f"OMP_NUM_THREADS {n}"); omp = max(omp or 0, n)
            for m in (_FILLER_THREADS_REQ.finditer(line) if py else ()):
                n = int(m.group(1))
                if 0 < n <= 192:
                    ev.append(f"FILLER_THREADS {n}"); best = max(best or 0, n)
            for m in _TASKSET.finditer(line):
                n = count_cpus(m.group(1))
                if n:
                    ev.append(f"taskset {m.group(1)}"); tsk = max(tsk or 0, n)
    # an explicit thread knob wins over a taskset list (taskset 0-95 + -t 48 uses 48 threads); taskset alone bounds it
    return (best if best is not None else omp if omp is not None else tsk), sorted(set(ev))


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
    if spec.get("gpu_use") is not None:
        need(spec["gpu_use"] == "quiet-only", "gpu_use must be \"quiet-only\" when present")
        need(o["class"] == "cpu+gpu" and o.get("gpu_quiet") == "exclusive",
             "gpu_use quiet-only needs engine --class cpu+gpu --gpu-quiet exclusive (the row holds the MI210 idle, never executes on it)")
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
    # ONE BOOKING DURATION (pipeline audit 2026-11-10 #3): optional max_window_s bounds the grant (a row that must fit a
    # window shorter than its estimate); resumable says a window end is a normal end (filed "partial, resumes").
    arq = autorequeue_max_check(spec.get("autorequeue_max"))
    res = spec.get("resumable", False)
    need(isinstance(res, bool), f"resumable {res!r} must be true or false (true: the job checkpoints and a window end is "
                                "a normal end, filed as partial; false: the job must finish inside one window)")
    if spec.get("max_window_s") is not None:
        try:
            mx = int(spec["max_window_s"])
        except (TypeError, ValueError):
            raise Refused("max_window_s must be whole seconds")
        need(mx >= minwin + 300, f"max_window_s {mx} < min_window_s {minwin} + 300 (the launcher gate refuses a shorter grant)")
        window = min(window, mx)
    window = -(-window // 60) * 60
    need(res or est <= window,
         f"estimate_s {est} > window_s {window} on a row that is not resumable: it cannot finish inside one grant; "
         f"raise max_window_s, or declare \"resumable\": true if the job checkpoints and continues on its next grant")
    book = compute_book_s(est, minwin, window)
    try:
        rank = float(spec.get("priority_rank", 100))
    except (TypeError, ValueError):
        raise Refused("priority_rank must be a number")
    row = {
        "schema": SCHEMA, "id": rid, "owner": str(spec["owner"]), "lane": lane, "regions": regions,
        "launcher": {"path": launcher, "sha256": sha256(launcher)}, "engine": {"path": eng, "sha256": sha256(eng)},
        "result_path": result_path, "result_format": fmt, "decision_rule": spec["decision_rule"],
        "handoff_task": spec["handoff_task"], "estimate_s": est, "min_window_s": minwin, "window_s": window,
        "book_s": book, "resumable": res,
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
    if spec.get("reclaimable") is not None:   # raw/reclaimable declaration (2026-11-23): globs under scratch_root; LARGE-DERIVED flags the rest
        row["reclaimable"] = [str(x) for x in (spec["reclaimable"] if isinstance(spec["reclaimable"], (list, tuple)) else [spec["reclaimable"]])]
    if spec.get("scratch_gb") is not None:   # per-row scratch declaration (disk guards 2026-11-21); the keeper logs SCRATCH-OVER, never kills
        row["scratch_gb"] = float(spec["scratch_gb"])
    qg = check_quiet_guard(spec, regions)
    if qg:
        row["quiet_guard_regions"] = qg
    for k in ("requires_quiet_host", "bandwidth_heavy"):   # PM-KEEPER3 2026-11-23: quiet-host gate inputs (bool only)
        if spec.get(k) is not None:
            need(isinstance(spec[k], bool), f"{k} {spec[k]!r} must be true or false")
            row[k] = spec[k]
    if snap:
        row["snapshot"] = snap
    elif isinstance(spec.get("snapshot"), dict):  # a republish from ready/<id>.json (publish_row.py --repair) keeps its snapshot record
        row["snapshot"] = spec["snapshot"]
    # who published it: INFORMATION ONLY (alerts route to the `inference` mailbox); a republish keeps the original
    row["publisher"] = spec["publisher"] if isinstance(spec.get("publisher"), dict) else notify.publisher_info()
    for k in ("lineage", "lineage_reset", "supersedes", "notes", "row", "dryrun_native_result", "publish_warnings",
              "smoke_predicate", "unit_key", "scratch_inputs", "fix_ref", "baseline_ref", "shape_override", "width_justification", "whole_host_need", "gpu_fence_override", "timing", "gpu_use", "verdict_by", "shape_widen", "autorequeue_max"):
        if spec.get(k) is not None:
            row[k] = spec[k]
    # refinement 4/5 root cause (2026-11-05 `$D` bug): the STOP file must resolve to an absolute path at publish
    sfp = resolve_stop_path({"stop_file": o["stop"], "launcher": {"path": launcher}})
    need(sfp, f"stop_file {o['stop']!r} is not absolute and does not resolve from the launcher's own D= assignment; "
              "use a literal absolute --stop path (or D=\"$(cd \"$(dirname \"$0\")\" && pwd)\" with --stop \"$D/<id>.STOP\")")
    row["stop_file"] = sfp
    if spec.get("timing") is not None:
        need(str(spec["timing"]) in GPU_TIMING_KINDS, f"timing must be one of {GPU_TIMING_KINDS}")
    sup = spec.get("supersedes")
    if sup is not None:
        need(isinstance(sup, str) and sup or isinstance(sup, list) and all(isinstance(x, str) and x for x in sup),
             "supersedes must be a row id or a list of row ids")
        need(rid not in ([sup] if isinstance(sup, str) else sup), "a row cannot supersede itself")
    if spec.get("fix_ref") is not None:
        need(isinstance(spec["fix_ref"], str) and spec["fix_ref"].strip(), "fix_ref must name the fix (commit or path)")
    check_engine_not_sealed(launcher, eng)
    envp = check_env_passthrough(launcher)
    if envp:
        row["env_passthrough"] = envp
    check_gpu_declared(row, o)
    # refinement 1: shape from evidence
    check_shape_evidence(spec, o)
    if o.get("threads"):
        row["declared_threads"] = int(o["threads"])
        row["threads_evidence"] = o.get("threads_evidence") or []
    # shapefix 2026-11-22: the spec's own declared_threads is authoritative over the argv scan (r6 declared 24, the scan
    # read 48 out of the engine's comments and the row was granted q0+q2). A larger scan is logged, never silently used.
    sdt = spec.get("declared_threads")
    if isinstance(sdt, int) and not isinstance(sdt, bool) and sdt >= 1:
        scanned = int(o.get("threads") or 0)
        if scanned > sdt:
            w = f"THREADS-SCAN-OVERRIDDEN spec declared_threads {sdt} kept over argv scan {scanned} ({', '.join(o.get('threads_evidence') or [])})"
            print(f"{rid}: {w}")
            row["publish_warnings"] = list(row.get("publish_warnings") or []) + [w]
        row["declared_threads"] = sdt
        o["threads"] = sdt   # contract_of takes max(row, o["threads"]): the scan must not out-vote the declaration
    # keeper class fix 2026-11-05 (operator "fix it"): the contract is derived from evidence only; the spec's shape and
    # regions are advisory and a declaration that books >= SHAPE_TOLERANCE_CORES more than the contract needs is
    # refused unless the spec carries shape_override "operator: <who> <date>: <why>" (logged in the row)
    if str(spec.get("shape") or "").strip():
        row["declared_shape"] = str(spec["shape"]).strip()   # honoured as a width floor by contract_of
    if spec.get("device"):
        row["device"] = str(spec["device"])
    c = contract_of(row, o, flags)
    row["shape"] = c["shape"]
    decl = str(spec.get("shape") or "").strip()
    need(not decl or decl in SHAPES or re.fullmatch(r"multi-quarter\([2-3]\)", decl), f"shape must be one of {SHAPES} or multi-quarter(n)")
    m = re.fullmatch(r"multi-quarter\((\d)\)", decl)
    decl_cores = (24 * int(m.group(1)) if m else {"sub-quarter": SUB_CORES, "quarter": 24, "host": 96, "quiet-host": 96, "gpu": 0,
                  "gpu-q3": 8}[decl]) if decl else (24 if regions == "any-cpu-quarter" or regions.startswith("any-of")
                                                    else len({x % 96 for x in _cpu_set(ws58_cpus(regions)) if x < 96}))
    over = max(decl_cores - c["need"], c["held"] - c["need"])
    if not str(row.get("shape_override") or "").strip():
        need(c["shape"] not in ("host", "quiet-host") or c["evidence"] or int(row.get("gib") or 0) > 3 * QUARTER_RAM_GIB,
             f"shape {c['shape']} needs whole-host evidence: >= {WHOLE_HOST_THREADS} threads (found {c['threads'] or 'none'}), a "
             "baseline_ref naming the decision-grade baseline / production-serving measurement, or shape_override "
             f"\"operator: <who> <date>: <why>\"; right-sized from its threads: {'declare -t/--threads/--workers/OMP_NUM_THREADS' if c['threads'] is None else ('sub-quarter' if c['threads'] <= SUB_CORES else 'quarter' if c['threads'] <= 24 else 'multi-quarter(' + str(min(3, -(-c['threads'] // 24))) + ')')}")
        wj = width_justified(row, c)
        lit = literal_threads_sum(launcher, o)
        dmq = re.fullmatch(r"multi-quarter\(([23])\)", decl)
        if lit and dmq and not c["gpu_use"] and not c["timing"] and not row.get("timing"):
            fitq = -(-lit // 24)
            need(wj or int(dmq.group(1)) <= fitq,
                 f"declared {decl} but the launcher's literal thread knobs sum to {lit} threads ({fitq} quarter"
                 f"{'s' if fitq > 1 else ''}): the extra width idles. Republish as "
                 f"{'quarter' if fitq <= 1 else 'multi-quarter(' + str(fitq) + ')'}, or add width_justification "
                 "\"<why the extra width helps, >= 20 chars>\" (F6, AK audit B6)")
        if wj:
            print(f"WIDTH-JUSTIFIED {rid}: declared {decl or regions} over contract {c['shape']} by {over} cores: {wj}")
        need(wj or over < SHAPE_TOLERANCE_CORES, f"declared {decl or 'regions ' + regions} books {over} cores more than the evidence "
             f"contract needs ({c['shape']}: {c['need']} cores; threads {c['threads'] or 'unknown'}"
             f"{': ' + ', '.join(row.get('threads_evidence') or []) if row.get('threads_evidence') else ''}; engine lock "
             f"{'= grant' if c['lock'] else '= --claim-cpus ' + (o.get('claim_cpus') or '-')}); republish right-sized "
             f"(shape {c['shape']}, a claim no wider than it), add width_justification \"<why the extra width helps, >= 20 chars>\" "
             "(CPU rows only), or add shape_override \"operator: <who> <date>: <why>\"")
        wide = {int(t[1:]) for x in c["options"] for t in expand(x) if re.fullmatch(r"[ct]\d+", t)} - GPU_Q3_ALLOWED_CPUS
        if wj and c["gpu_use"]:   # justified whole q0-q2 quarters beside the GPU grant (operator 2026-11-06)
            wide -= {int(t[1:]) for q in ("q0", "q1", "q2") if any(q in x for x in c["options"]) for t in expand({q}) if re.fullmatch(r"[ct]\d+", t)}
        need(not (c["gpu_use"] and wide and not c["evidence"]), f"GPU-lane row locks cpus beyond q3 + 184-191 "
             f"({compress_cpus(wide)}); a GPU run needs gpu-quiet + q3's host threads (shape gpu-q3: regions "
             "mi210_0,88-95,184-191, --class gpu --no-fold-siblings) unless it carries whole-host evidence")
        q3 = {t for x in c["options"] for t in expand(x) if t in COEXIST_Q3 or t in qcores("q3")}
        need(not (c["gpu_use"] and not c["timing"] and q3 and not c["evidence"]), "non-timing GPU row books q3 cores: q3 CPU use runs in parallel "
             "with non-timing GPU work; use the plain gpu shape (regions mi210_0,184-191, --class gpu --no-fold-siblings). A "
             f"timing row declares it: --role bench, admission_class {'|'.join(GPU_TIMING_CLASSES)}, or timing: "
             f"{'|'.join(GPU_TIMING_KINDS)}; else shape_override")
        held_q3 = {t for x in c["options"] for t in expand(x)} & GPU_TIMING_NEVER_HELD
        need(c["shape"] != "gpu-q3" or not held_q3, "gpu-q3 regions must claim only gpu-quiet + 88-95 + 184-191 (operator "
             f"2026-11-05 NARROW: a GPU timing grant never holds q3 cores 72-87, found {','.join(compress(held_q3))}; they stay "
             "grantable to CPU rows beside a GPU timing run); a quieter neighbourhood needs explicit regions + shape_override")
    if c.get("widened"):
        wn = f"SHAPE-WIDENED {c['widened']} (opt out: shape_widen=false in the spec)"
        print(f"{rid}: {wn}")
        row["publish_warnings"] = list(row.get("publish_warnings") or []) + [wn]
    check_timing_shape(spec, o, c["shape"])
    cw = claim_wider_refusal(row, c, o)
    need(not cw, cw)
    lint = regions_wider_lint(regions, c, row)
    if lint:   # a lint, never a refusal (the contract already decides what is held)
        print(f"LINT {rid}: {lint}")
        row["publish_warnings"] = list(row.get("publish_warnings") or []) + [lint]
    if row.get("busy_fraction") is None and row.get("declared_threads"):
        row["busy_fraction"] = round(min(1.0, row["declared_threads"] / claimed_cpus(regions, o.get("claim_cpus"), row["shape"])), 3)
        row["busy_fraction_source"] = "declared_threads"
    atomic_json(ready_path(flags, rid), row)
    supersede_block(flags, row)   # PM-KEEPER3 #3: the predecessor stops being grantable NOW, not at the successor's PASS
    return row


def withdrawn_dir(flags): return os.path.join(flags, "ready", ".withdrawn")


def withdraw(flags, rid, reason, log=print):
    """Refinement 5: end a row that will never run. Not running: ready/<id>.json -> ready/.withdrawn/<id>.json, a
    terminal grants/<id>.ended `rc=75 reason=<reason>` (status/queue_status/backlog_gen/dashboard read it as closed),
    and its STOP file touched (an armed poller exits within one poll: filler_run15 honours STOP while waiting).
    Running (open grant): a RUNNING predecessor FINISHES - its STOP file is NOT touched (since 2134ef303 the engine polls
    STOP mid-run and would kill it); only a pending record is written and the keeper finishes the withdrawal once the
    grant ends. Nothing is killed or deleted.
    Returns WITHDRAWN | PENDING | ABSENT | TERMINAL."""
    reason = re.sub(r"\s+", "_", str(reason).strip()) or "withdrawn"
    G = os.path.join(flags, "grants")
    if any(os.path.exists(os.path.join(G, rid + t)) for t in (".ended", ".complete")):
        _move_withdrawn(flags, rid)
        return "TERMINAL"
    rp = ready_path(flags, rid)
    d = load_json(rp)
    if not d:
        return _withdraw_smoke_queued(flags, rid, reason, log)
    os.makedirs(withdrawn_dir(flags), exist_ok=True)
    if os.path.exists(os.path.join(G, rid + ".grant")):
        atomic_json(os.path.join(withdrawn_dir(flags), rid + ".pending.json"), {"id": rid, "reason": reason, "at": now_iso()})
        log(f"SUPERSEDE-PENDING {rid}: running; it finishes (STOP not touched), withdrawn when its grant ends (reason={reason})")
        return "PENDING"
    sf = resolve_stop_path(d)
    if sf:
        try:
            os.makedirs(os.path.dirname(sf), exist_ok=True)
            open(sf, "a").close()
        except OSError as e:
            log(f"WITHDRAW {rid}: could not touch STOP {sf}: {e}")
    os.makedirs(G, exist_ok=True)
    with open(os.path.join(G, rid + ".ended"), "w") as f:
        f.write(f"rc=75 reason={reason} at={now_iso()}\n")
    _move_withdrawn(flags, rid)
    log(f"WITHDRAWN {rid} reason={reason}")
    return "WITHDRAWN"


def withdraw_pending_path(flags, rid): return os.path.join(withdrawn_dir(flags), rid + ".pending.json")


def smoke_queued_running(flags, rid):
    """A queued GPU smoke of `rid` is (or may be about to be) running: its dryrun/<id>/RUNNING.json names a live pid, or
    the detached GPU-SMOKE-BATCH is alive (it snapshots the queue at start, so any queued row may be its next smoke)."""
    r = load_json(running_path(flags, rid)) or {}
    if r.get("pid") and proc_alive(r["pid"]):
        return True
    return gpu_batch_running(flags)


def _withdraw_smoke_queued(flags, rid, reason, log):
    """No ready manifest: a GPU row waiting for its smoke exists only as dryrun/<id>/GPU-SMOKE-QUEUED.json (+ unpublished
    .json). Also reached by the keeper for a pending withdrawal whose smoke ended without PASS (marker removed by the
    batch, manifest back in unpublished.json). Running -> PENDING record; not running -> terminal .ended rc=75, marker
    moved to dryrun/<id>/.withdrawn/ (never deleted). Neither marker nor pending -> ABSENT."""
    q = os.path.join(dry_dir(flags, rid), "GPU-SMOKE-QUEUED.json")
    pending = os.path.exists(withdraw_pending_path(flags, rid))
    if not os.path.exists(q) and not (pending and os.path.exists(os.path.join(dry_dir(flags, rid), "unpublished.json"))):
        return "ABSENT"
    os.makedirs(withdrawn_dir(flags), exist_ok=True)
    if smoke_queued_running(flags, rid):
        if not pending:
            atomic_json(withdraw_pending_path(flags, rid), {"id": rid, "reason": reason, "at": now_iso(), "smoke": True})
        log(f"SUPERSEDE-PENDING {rid}: queued GPU smoke running; withdrawn when the smoke ends (reason={reason})")
        return "PENDING"
    G = os.path.join(flags, "grants")
    os.makedirs(G, exist_ok=True)
    with open(os.path.join(G, rid + ".ended"), "w") as f:
        f.write(f"rc=75 reason={reason} at={now_iso()}\n")
    if os.path.exists(q):
        wd = os.path.join(dry_dir(flags, rid), ".withdrawn")
        os.makedirs(wd, exist_ok=True)
        os.replace(q, os.path.join(wd, "GPU-SMOKE-QUEUED.json"))
    log(f"WITHDRAWN-SMOKE-QUEUED {rid} reason={reason}")
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


# PM-KEEPER3 #3 (AK 2026-11-23, supersede race): ak-rsreplay-q4x-singleslot-repro r1 (resumable) was re-granted after its
# successor r2 PUBLISHED and the two collided on ports. supersede() only withdraws at the successor's PASS, and the guards
# that stop a requeue (capcut_closed / resume_row) only scanned ready/*.json - a successor still waiting for its smoke
# (dryrun/<id>/unpublished.json or a queued marker) was invisible, so auto-requeue / capcut requeue / resume made the
# predecessor grantable again. publish() now writes ready/.superseded/<pred>.json at once; superseded_by() reads it plus
# every manifest form, and every requeue path and the allocator's candidate list refuse a superseded id. A RUNNING
# predecessor keeps running (nothing is stopped or killed); it is simply never granted again.
def superseded_dir(flags): return os.path.join(flags, "ready", ".superseded")


def _supersedes_list(d):
    sup = (d or {}).get("supersedes")
    out = []
    for v in (sup if isinstance(sup, list) else [sup]):
        out += re.findall(r"[A-Za-z0-9_.-]+", str(v or ""))
    return out


def supersede_block(flags, row, log=print):
    """At publish: mark every `supersedes` predecessor not-grantable (ready/.superseded/<pred>.json {by, at}). Returns ids."""
    out = []
    for pred in _supersedes_list(row):
        if not pred or pred == row.get("id"):
            continue
        p = os.path.join(superseded_dir(flags), pred + ".json")
        cur = load_json(p) or {}
        if cur.get("by") != row.get("id"):
            os.makedirs(superseded_dir(flags), exist_ok=True)
            atomic_json(p, {"id": pred, "by": row.get("id"), "at": now_iso()})
            log(f"SUPERSEDED-BLOCK {pred} by {row.get('id')}: not grantable from now (requeue/resume/re-grant refused); "
                "a running grant finishes")
        out.append(pred)
    return out


def superseded_index(flags):
    """{predecessor id: successor id} from the block markers, ready/*.json, dryrun/*/unpublished.json and queued smoke
    markers' specs (one scan; allocate builds it once per tick)."""
    out = {}
    for mp in glob.glob(os.path.join(flags, "ready", "*.json")) + glob.glob(os.path.join(flags, "dryrun", "*", "unpublished.json")):
        oid = os.path.basename(os.path.dirname(mp)) if mp.endswith("unpublished.json") else os.path.basename(mp)[:-5]
        for pred in _supersedes_list(load_json(mp)):
            if pred != oid:
                out.setdefault(pred, oid)
    for q in glob.glob(os.path.join(flags, "dryrun", "*", "*SMOKE-QUEUED.json")):
        oid = os.path.basename(os.path.dirname(q))
        for pred in _supersedes_list((load_json(q) or {}).get("spec")):
            if pred != oid:
                out.setdefault(pred, oid)
    for mp in glob.glob(os.path.join(superseded_dir(flags), "*.json")):
        pred, b = os.path.basename(mp)[:-5], (load_json(mp) or {}).get("by")
        if b and b != pred:
            out[pred] = str(b)
    return out


def superseded_by(flags, rid, index=None):
    """The successor id that supersedes `rid`, else ''."""
    return (superseded_index(flags) if index is None else index).get(rid, "")


def published_line(row, flags):
    return (f"PUBLISHED {row['id']} lane={row['lane']} regions={row['regions']} window_s={row['window_s']} min_window_s={row['min_window_s']} "
            f"book_s={row.get('book_s')} resumable={str(bool(row.get('resumable'))).lower()} gib={row['gib']} ports={row['ports']} result={row['result_path']} ({row['result_format']}) -> {ready_path(flags, row['id'])}")


def legacy_handoff_task(m):
    """The manifest's own handoff_task wins; a bare `<file>.md[:ID]` is normalised to `handoffs/active/<file>.md[:ID]`
    (the publish lint's form). Only a manifest with no task at all falls back to the legacy FILLERS:<id> marker."""
    ht = next((str(m[k]).strip() for k in ("handoff_task", "row", "handoff") if isinstance(m.get(k), str) and m[k].strip()), "")
    if not ht:
        return "FILLERS:" + str(m.get("id"))
    head, sep, tail = ht.partition(":")
    if head.endswith(".md") and "/" not in head:
        ht = "handoffs/active/" + head + sep + tail
    return handoff_ref.repoint(ht, sha=m.get("handoff_task_sha"))   # C4: a moved box migrates to its new file


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
              "fix_ref", "baseline_ref", "shape_override", "width_justification", "gpu_fence_override", "timing", "gpu_use", "verdict_by",
              "resumable", "max_window_s", "whole_host_need", "quiet_guard_regions", "autorequeue_max",
              "requires_quiet_host", "bandwidth_heavy"):
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
RAM_MARGIN_GIB = 100         # PIPE-EVE-RAM-MARGIN 2026-11-10: the ratified job_fence margin (2026-10-21); earlyoom fires at 40 GiB


def ram_fence_env(d, env):
    """PIPE-EVE-RAM-MARGIN: inject the row's declared ram_gib into the job as job_fence's admission inputs, so the job's own
    pre-exec RAM check uses the same need and margin the allocator placed it with. A launcher's explicit value wins."""
    gib = int(d.get("gib") or 0)
    if gib > 0:
        env.setdefault("JOB_FENCE_NEED_RAM_GIB", str(gib))
        env.setdefault("JOB_FENCE_RAM_MARGIN_GIB", str(RAM_MARGIN_GIB))
    return env
UNDERUSED_PCT = 5.0
UNDERUSED_S = 600
UNDERUSED_SHRINK_S = 1800   # F6 (AK audit B6): continuously UNDERUSED this long -> a "shrink to <n> quarters" note to the owner
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


def gpu_q3_claim_cores(regions):
    """The physical cores (SMT siblings folded) a GPU grant's region-lock claim touches: filler_run15 GRANT_CPUS locks
    the grant cpus < 96 with --no-fold-siblings (sub-quarter: LOCK_SH GLOBAL.q3 + LOCK_EX per core); the >= 96 host
    threads are tasksetted, unlocked. A whole qN region would take GLOBAL.qN exclusive."""
    out = set()
    for t in (grant_cpus(regions) or str(regions or "")).split(","):
        a, _, b = t.partition("-")
        if a.isdigit():
            out |= {c % 96 for c in range(int(a), int(b or a) + 1)}
    return out


def tokens_cpus(tokens):
    """The exact cpu list (cores + their SMT siblings) of a sub-quarter option."""
    cs = sorted(int(t[1:]) for t in tokens if re.fullmatch(r"c\d+", t))
    # 2026-11-08 (inf75-c7r-w3-halfb): held t<N> SMT tokens belong to the list too; dropping them ran the job on 80 of 96 cpus
    ts = sorted({int(t[1:]) for t in tokens if re.fullmatch(r"t\d+", t)} - {c + 96 for c in cs})
    return ",".join(str(c) for c in cs + [c + 96 for c in cs] + ts)


def cpu_list(q):
    lo = int(q[1]) * 24
    return f"{lo}-{lo + 23}"


def open_grants(flags):
    """Every grants/<id>.grant: {id, regions, holds, start, end, pid, dryrun, started}. holds = the regions the grant
    books (written by the allocator as holds=...; older grants: derived from regions)."""
    out = []
    for g in glob.glob(os.path.join(flags, "grants", "*.grant")):
        rid = os.path.basename(g)[:-6]
        if os.path.exists(os.path.join(flags, "grants", rid + ".ended")):
            continue   # an ended grant holds nothing (a hand-release / engine end that left the .grant behind is no phantom hold)
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


SHAPES = ("sub-quarter", "quarter", "multi-quarter", "host", "quiet-host", "gpu", "gpu-q3")
WHOLE_HOST_THREADS = 48   # operator 2026-11-05: production CPU serving across all NUMA nodes (npd1-step5: -t 48 over 0-95)
# gpu-q3 NARROW (operator 2026-11-05 "Narrow + emergency deploy"; q38p4b-int8 refused "needs gpu-quiet,q3,t184..t191: q3
# busy" while an 8-core AITER build sat on 80-87/176-183): a GPU TIMING grant holds gpu-quiet + its host threads 184-191
# + their SMT-sibling physical cores 88-95 - NEVER the rest of q3. Cores 72-87 (siblings 168-183) stay grantable to CPU
# rows beside a GPU timing run. This REPLACES the rule that a GPU timing run holds all of q3; a timing row that really
# needs a quieter neighbourhood declares it (explicit regions, or shape_override).
GPU_Q3_TOKENS = frozenset({GPU} | {f"c{k}" for k in range(88, 96)} | {f"t{k}" for k in range(184, 192)})   # gpu-quiet + 88-95 + 184-191
GPU_TIMING_NEVER_HELD = frozenset({"q3"} | {f"c{n}" for n in range(72, 88)} | {f"t{n}" for n in range(168, 184)})   # q3 cores 72-87 + siblings
QUARTER_RAM_GIB = 256   # a quarter's share of the bookable RAM (1069 GiB / 4, rounded): a bigger model is multi-quarter
SUB_CORES = 4           # a <= SUB_CORES-thread job is a SUB_CORES-core row (any aligned block of one quarter)
CONTRACT_LOCK_MARKER = "CONTRACT_LOCK"   # an engine containing it locks the grant's lock= cpus instead of --claim-cpus
SHAPE_TOLERANCE_CORES = 24   # publish refuses a declaration that books >= a quarter more than the contract needs
GPU_Q3_ALLOWED_CPUS = frozenset(range(72, 96)) | frozenset(range(168, 192))   # q3 cores + their SMT siblings (incl. 184-191)
# q3 cores whose SMT siblings are NOT the MI210 host threads (72-87 -> siblings 168-183)
COEXIST_Q3 = frozenset({f"c{n}" for n in range(72, 88)} | {f"t{n}" for n in range(168, 184)})
GPU_BLOCKED = "gpu-quiet-not-quiet"   # planner-only token: a held-back EXCLUSIVE row's GPU (never free, unknown end)
GPU_HOST_THREADS = frozenset(range(184, 192))   # filler_run15 GPUTHR default / gpu-quiet reserved MI210 host threads
GPU_TIMING_KINDS = ("bench", "profile", "ak-keep-gate")
GPU_TIMING_CLASSES = ("block-timing-pairable", "block-timing-quiet")


def _engine_has(o, marker):
    try:
        with open((o or {}).get("engine") or "", errors="replace") as f:
            return marker in f.read()
    except OSError:
        return False


def engine_grant_cpus(o):
    """True when the row's engine snapshot locks a GPU grant's own cpus (content check, never a path/version guess)."""
    return _engine_has(o, GRANT_CPUS_MARKER)


def engine_contract_lock(d, o, flags=None):
    """The engine that will run this row locks the grant's lock= cpus: the engine file carries CONTRACT_LOCK and, when a
    poller is already armed, that poller was armed on this very engine (ARMED.json engine_sha256: a poller armed on an
    older engine keeps running the old code, whose lock is still --claim-cpus)."""
    if not _engine_has(o, CONTRACT_LOCK_MARKER):
        return False
    a = load_json(armed_path(flags or FLAGS, str(d["id"]))) if (d or {}).get("id") else None
    if a and alive(a.get("pid")) and a.get("engine_snapshot"):   # the poller runs its own snapshot: judge that copy
        return _engine_has({"engine": os.path.join(a["engine_snapshot"], os.path.basename(o.get("engine") or ""))}, CONTRACT_LOCK_MARKER)
    if a and alive(a.get("pid")):
        try:
            return a.get("engine_sha256") == sha256(o["engine"])
        except OSError:
            return False
    return True


def gpu_timing_row(row, o):
    """A GPU row that measures time on the GPU (holds 88-95 beside its host threads, never 72-87): launcher --role bench, a timing admission_class, or an
    explicit spec `timing` kind (bench | profile | ak-keep-gate)."""
    return ((o or {}).get("launch_role") == "bench" or (row or {}).get("admission_class") in GPU_TIMING_CLASSES
            or str((row or {}).get("timing") or "") in GPU_TIMING_KINDS)


def check_timing_shape(spec, o, contract_shape):
    """Publish gate (coordinator 2026-11-10, vidya-r234-native-sweep-20261104e/f): GPU timing (launcher --role bench, a
    timing admission_class, a timing kind) makes the contract gpu-q3 and silently overrides a declared shape - the spec
    said gpu + mi210_0,0-23,184-191 + width_justification, the grant clipped q0 and the job died. Refuse when the contract
    resolved to gpu-q3 but the declared shape is something else, and name the field to change. (The reverse - declared
    gpu-q3 without a timing signal - is refused by the "non-timing GPU row books q3" gate; whole-host evidence or a
    shape_override that resolves a timing row to (quiet-)host is not an override and passes.)"""
    decl = str(spec.get("shape") or "").strip()
    if not decl or decl == "gpu-q3" or contract_shape != "gpu-q3":
        return
    if not gpu_timing_row({"admission_class": spec.get("admission_class"), "timing": spec.get("timing")}, o):
        return
    why = ("launcher --role bench" if (o or {}).get("launch_role") == "bench" else
           f"admission_class {spec.get('admission_class')}" if spec.get("admission_class") in GPU_TIMING_CLASSES else
           f"spec timing {spec.get('timing')}")
    raise Refused(f"declared shape {decl!r} but {why} makes this a GPU-timing row, whose contract is gpu-q3 (gpu-quiet + "
                  f"q3 cores 88-95 + MI210 host threads 184-191; any other regions are clipped from the grant): set spec "
                  f"shape \"gpu-q3\" if it times the GPU, or remove {why} if it does not")


def row_threads(d, flags=None):
    """declared_threads (>= 1); None when unknown (unknown != 0). Smoke measured_threads is never width evidence."""
    vals = []
    for v in ((d or {}).get("declared_threads"),):
        try:
            if v is not None:
                vals.append(int(v))
        except (TypeError, ValueError):
            pass
    # keeper classfix 2026-11-05 (yarn-oolong v38, iqk-q8-prefill, STT5 r5): a smoke's footprint is NEVER evidence
    # for the row's width - the smoke runs on 4 cpus (often only a preflight), so its measured_threads (0.099, 1.9,
    # 2.2) shrank quarter rows to 4-core grants their jobs refused. PASS.json measured_threads stays a busy signal only.
    vals = [v for v in vals if v >= 1]   # < 1 thread is not a width (int(0.099) == 0 read as a 0-thread row)
    return max(vals) if vals else None


def gpu_quiet_only(row, o, flags=None):
    """the row holds the MI210 quiet but does not USE it - gpu_use "quiet-only", or
    --class cpu+gpu --gpu-quiet exclusive whose smoke measured < 1 GiB VRAM. Such a row is CPU work, not GPU lane."""
    if (row or {}).get("gpu_use") == "quiet-only":
        return True
    o = o or {}
    if o.get("gpu_quiet") == "exclusive" and o.get("class") == "cpu+gpu" and (row or {}).get("id"):
        v = (load_json(pass_path(flags or FLAGS, str(row["id"]))) or {}).get("vram_used_max_bytes")
        return isinstance(v, (int, float)) and v < (1 << 30)
    return False


def _opts(d):
    try:
        return parse_launcher(d["launcher"]["path"])
    except (Refused, OSError, StopIteration, ValueError, KeyError, TypeError):
        return {}


_KFD = re.compile(r"(?i)\bGGML_HIP\b|\bhipcc\b|build-hip|-DGGML_HIP|\bhip_?build\b|--device[ =]+['\"]?rocm|"
                  r"(?<![\w-])(?:-ngl|--n-gpu-layers|--gpu-layers)[ =]+['\"]?(?!0\b)\d+|\b(?:HIP|ROCR)_VISIBLE_DEVICES=")


# GPU-FENCE-VACUOUS (operator 2026-11-05): under the fence a GPU test finds no backend, skips and exits rc0, so GPU-only
# work must be DECLARED (token) at publish. Superset of _KFD: a backend-op test on ROCm, a HIP test binary, a gpu-class job.
_SEP = r"(?:[ =]+['\"]?|['\"]?\s*,\s*['\"])"   # shell argv (`-b ROCm0`) or a Python/JSON list (`"-b", "ROCm0"`)
_GPU_WORK = re.compile(r"(?i)--device" + _SEP + r"rocm|(?<![\w-])(?:-ngl|--n-gpu-layers|--gpu-layers)" + _SEP + r"(?!0\b)\d+|"
                       r"\b(?:HIP|ROCR)_VISIBLE_DEVICES=(?!-1\b)['\"]?\d|(?<![\w-])(?:-b|--backend)" + _SEP + r"rocm|"
                       r"\btest-backend-ops\b[^\n]*\brocm|build-hip[^\s'\"]*/bin/test-|\bROCm\d\b")
# build-only HIP evidence (GGML_HIP, hipcc, build-hip) still takes the token via _KFD but is never refused: compiling is not GPU work


def gpu_declared(d, o=None):
    """The row holds the GPU token by declaration: mi210 regions, a gpu/cpu+gpu launcher, lane gpu, or --gpu-quiet."""
    d, o = d or {}, (_opts(d or {}) if o is None else o)
    return ("mi210" in str(d.get("regions") or "") or o.get("class") in ("gpu", "cpu+gpu") or d.get("lane") == "gpu"
            or o.get("gpu_quiet") in ("shared", "exclusive"))


def job_texts(d, o=None):
    """{path: text} of the launcher, its --cmd, and every job file (.py/.sh) the launcher or cmd runs: absolute paths,
    $D/<f> references, and bare/relative names resolved against the launcher dir and the --workdir (one level deep)."""
    d, o = d or {}, (_opts(d or {}) if o is None else o)
    try:
        launcher = d["launcher"]["path"]
    except (KeyError, TypeError):
        launcher = (d.get("launcher") if isinstance(d.get("launcher"), str) else "") or ""
    out = {"<cmd>": o.get("cmd") or ""}
    bases = [b for b in (os.path.dirname(launcher) if launcher else "", o.get("workdir") or "") if b]

    def add(p):
        if p in out or len(out) > 40 or re.match(r"filler_(?:run\d+|lib)\.sh$", os.path.basename(p)):
            return   # the engine itself is not the job
        try:
            if os.path.isfile(p) and os.path.getsize(p) < 4 << 20:
                out[p] = open(p, errors="replace").read()[:1 << 20]
                return True
        except OSError:
            pass

    if launcher:
        add(launcher)
    rx = re.compile(r"(?:\$\{?D\}?/)?([A-Za-z0-9_./-]+\.(?:sh|py|bash))\b")
    for _ in range(2):
        for t in list(out.values()):
            for m in rx.finditer(t):
                f = m.group(1)
                if f.startswith("/"):
                    add(f)
                else:
                    for b in bases:
                        if add(os.path.normpath(os.path.join(b, f))):
                            break
    return out


def gpu_work_evidence(d, o=None):
    """[(file, line)] where the row's launcher/cmd/job files run GPU-only work (comment lines ignored)."""
    hits = []
    for f, t in job_texts(d, o).items():
        for ln in t.splitlines():
            s = ln.strip()
            if s.startswith("#") or s.startswith("//"):
                continue
            if _GPU_WORK.search(ln):
                hits.append((f, s[:160]))
                break
    return hits


def _kfd_capable(d, o=None):
    return any(_KFD.search(t) for t in job_texts(d, o).values())


def gpu_touch(d, o=None):
    """GPU EXCLUSIVITY (coordinator 2026-11-05, kvu16g2-ab: 41 GB foreign VRAM under a gpu-quiet EXCLUSIVE grant): the
    row's job can open /dev/kfd - a GPU-class launcher, mi210 regions, a HIP build, -ngl > 0, --device ROCm, -b ROCm0,
    HIP/ROCR_VISIBLE_DEVICES - so it, and its smoke, hold the gpu-quiet token for their whole duration."""
    d, o = d or {}, (_opts(d or {}) if o is None else o)
    if cpu_declared(d, o):
        return False
    return gpu_declared(d, o) or bool(gpu_work_evidence(d, o)) or _kfd_capable(d, o)


def cpu_declared(d, o):
    """keeper classfix 2026-11-05 (STT5 r5 held gpu-quiet idle on 4 cores, blocking 7 GPU rows): a row whose launcher
    says --class cpu with no --gpu-quiet, on a CPU lane / non-mi210 regions (or spec device: cpu), is CPU work. A HIP
    path in its job files is not GPU evidence - the GPU fence covers it - so it never holds the GPU token."""
    d, o = d or {}, o or {}
    if str(d.get("device") or "").lower() == "cpu" and o.get("class") != "gpu" and o.get("gpu_quiet", "") in ("", "none"):
        return True
    return (o.get("class") == "cpu" and o.get("gpu_quiet", "") in ("", "none") and d.get("lane") != "gpu"
            and "mi210" not in str(d.get("regions") or ""))


def check_gpu_declared(row, o):
    """Publish gate (GPU-FENCE-VACUOUS, operator 2026-11-05): GPU work without the GPU token runs fenced and passes vacuously."""
    if gpu_declared(row, o) or str(row.get("gpu_fence_override") or "").strip():
        return   # gpu_fence_override "operator|owner: <who> <date>: <why GPU-looking code never runs here>" (static
                 # evidence is conditional, e.g. a KIND=='gpu' branch); the engine's runtime GPU-FENCE-VACUOUS check still applies
    ev = gpu_work_evidence(row, o)
    need(not ev, "GPU-FENCE: this row runs GPU work without the GPU token - under the fence it sees no GPU, a GPU test skips "
         "and exits 0 (a vacuous PASS). Evidence: " + "; ".join(f"{os.path.basename(f)}: `{l}`" for f, l in ev[:3]) +
         ". Declare the token (lane gpu, regions mi210_0,..., --class gpu, or --gpu-quiet shared|exclusive), drop the GPU work, or, "
         "when that code never runs in this row, add gpu_fence_override \"<who> <date>: <why>\" (the runtime check still applies).")


def _sub_blocks(within=QUARTERS):
    """Every aligned SUB_CORES-core block (cores + SMT siblings) of the given quarters, never the MI210 host threads and
    never a block under a smoke pocket (SMOKE_POCKETS)."""
    out = []
    for q in within:
        lo = int(q[1]) * 24
        for a in range(lo, lo + 24, SUB_CORES):
            cs = range(a, a + SUB_CORES)
            if not any(c + 96 in GPU_HOST_THREADS or f"t{c + 96}" in POCKET_TOKENS for c in cs):
                out.append(frozenset({f"c{c}" for c in cs} | {f"t{c + 96}" for c in cs}))
    return out


def contract_of(d, o=None, flags=None):
    """THE resource contract of a row (keeper class fix 2026-11-05, operator "fix it"), derived from evidence only:
    launcher argv (--class, --claim-cpus, --gpu-quiet, --no-fold-siblings, --role), the job's threads (-t/--threads/
    --workers/OMP_NUM_THREADS/taskset; Python NAME = "N" resolved), PASS.json measured_threads / vram_used_max_bytes,
    gpu_use, RAM, and what the engine will actually lock. The spec's shape / regions are advisory (publish compares).
      shape    sub-quarter | quarter | multi-quarter(n) | host | quiet-host | gpu | gpu-q3 (logs, dashboard)
      options  alternative token sets to hold = the claim handed to the engine (grant holds= / lock=)
      lock     True: the engine locks exactly the granted cpus (CONTRACT_LOCK); False: it locks --claim-cpus, so the
               options cover the claim (an honest hold, never a fake co-run)
      need     cores the evidence needs; held = cores of the widest option (held - need >= tolerance: over-booked)
      (the coexist / lends keys are gone, Pass 5 2026-11-07: nothing has lent since gpu-q3 NARROW 2026-11-05)"""
    d = d or {}
    o = _opts(d) if o is None else o
    regs = str(d.get("regions") or "")
    cls = o.get("class") or ("gpu" if "mi210" in regs else "cpu")
    gq, cc, nofold = o.get("gpu_quiet", ""), o.get("claim_cpus", ""), bool(o.get("nofold"))
    honours = engine_contract_lock(d, o, flags)
    if not re.fullmatch(r"\d+(-\d+)?(,\d+(-\d+)?)*", cc or ""):   # an unresolved claim ($CPUS): a legacy engine may
        cc = "0-95" if cc and not honours and not re.search(r"WS58_REGIONS|FILLER_CPUS", cc) else ""   # lock anything
        # (read as the host) unless it names the grant's own cpus; a CONTRACT_LOCK engine's lock= replaces it anyway
    tv = [x for x in (row_threads(d, flags), o.get("threads")) if x]
    threads = max(tv) if tv else None
    if threads is None and (len(str(d.get("width_justification") or "").strip()) >= WIDTH_JUSTIFICATION_MIN
                            or bool(str(d.get("shape_override") or "").strip())):
        # a width-agnostic job (no thread knob) with a justified (width_justification) or operator-overridden
        # (shape_override) multi-quarter declaration books that width, never one quarter
        dw = re.fullmatch(r"multi-quarter\(([23])\)", str(d.get("declared_shape") or d.get("shape") or ""))
        if dw and not d.get("timing") and d.get("admission_class") not in GPU_TIMING_CLASSES:
            threads = 24 * int(dw.group(1))
    gpu_row = "mi210" in regs or cls in ("gpu", "cpu+gpu") or d.get("lane") == "gpu"
    gpu_use = gpu_row and not gpu_quiet_only(d, o, flags)
    timing = gpu_timing_row(d, o)
    evidence = ((threads or 0) >= WHOLE_HOST_THREADS or bool(str(d.get("baseline_ref") or "").strip())
                or bool(str(d.get("shape_override") or "").strip()))
    gib = int(d.get("gib") or 0)
    abstract = regs == "any-cpu-quarter" or regs.startswith("any-of")
    decl_cpus = "" if abstract else ws58_cpus(regs)
    if not abstract and not decl_cpus and re.fullmatch(r"q[0-3](,q[0-3])*", regs.replace(" ", "")):
        decl_cpus = ",".join(cpu_list(q) for q in regs.replace(" ", "").split(","))   # regions "q2": that quarter
    # rtg34-r1a 2026-11-11: an abstract-region row (any-cpu-quarter, e.g. --self-claim) with > 72 threads or a declared
    # host / quiet-host shape and whole-host evidence IS a host row; it fell to multi-quarter(3) and was granted q0-q2
    # while its own 0-95 claim then waited 600 s on q3. Three quarters cannot host more than 72 threads.
    dshape = str(d.get("declared_shape") or d.get("shape") or "").strip()
    whole = ((len(quarters_of(cc or decl_cpus, fold=True)) >= 4 or (threads or 0) > 72 or dshape in ("host", "quiet-host"))
             and (evidence or gib > 3 * QUARTER_RAM_GIB))
    gpu_tok = {GPU} if (gpu_row or gq == "exclusive" or gpu_touch(d, o)) and not cpu_declared(d, o) else set()
    lock_tokens, floored = set(), False
    if gpu_use and not whole:
        # GPU work: gpu-quiet + its host threads; a GPU-timing row also holds the host threads' SMT-sibling cores 88-95
        # (gpu-q3 NARROW, operator 2026-11-05: never the rest of q3 - 72-87 stay grantable); q0-q2 only with evidence
        grant_cpus_engine = cls == "gpu" and (nofold or engine_grant_cpus(o) or not cc)
        src = decl_cpus if grant_cpus_engine else cc
        lock_tokens = cpu_tokens(src, gpu_threads=True) if src else set()
        if (grant_cpus_engine or honours) and not (evidence or _cpu_set(src) <= GPU_Q3_ALLOWED_CPUS):
            lock_tokens = {f"t{k}" for k in GPU_HOST_THREADS}   # declared cpus beyond q3: the contract clips them
            # operator 2026-11-06 ("Allow, q0-q2 only"): a justified GPU row keeps the WHOLE quarters q0-q2 it declares beside
            # its GPU grant (its correctness reference runs on the ggml CPU backend); never q3 72-87, never the whole host
            if len(str(d.get("width_justification") or "").strip()) >= WIDTH_JUSTIFICATION_MIN:
                lock_tokens |= {q for q in cpu_tokens(src, gpu_threads=True) if q in ("q0", "q1", "q2")}
        if timing:
            shape, base = "gpu-q3", set(GPU_Q3_TOKENS)   # 72-87 are simply not held
        else:
            shape, base = "gpu", {GPU} | (lock_tokens or {f"t{k}" for k in GPU_HOST_THREADS})
        opts = [frozenset(base | lock_tokens)]
    elif whole:
        shape = "quiet-host" if (gq == "exclusive" or gpu_row) else "host"
        opts = [frozenset(set(QUARTERS) | gpu_tok)]
    else:
        pinned = bool(decl_cpus) and not (cpu_tokens(decl_cpus) & set(QUARTERS))   # concrete sub-quarter regions
        legacy = len(_cpu_set(cc) & set(range(96))) if (cc and not honours) else 0
        nq_ram = -(-gib // QUARTER_RAM_GIB) if gib > QUARTER_RAM_GIB else 1
        if d.get("shape_widen") is False:   # opt-out (shapefix 2026-11-22): never widen on RAM; the owner owns the fit
            nq_ram = 1
        if pinned:
            shape, opts = "sub-quarter", [frozenset(cpu_tokens(decl_cpus) | (cpu_tokens(cc) if legacy else set()))]
        elif threads is not None and legacy <= (SUB_CORES if threads <= SUB_CORES else 24 * -(-threads // 24)):
            n = max(-(-threads // 24), nq_ram)
            # a declared quarter / multi-quarter / timing shape is honoured, never shrunk below it (iqk-q8-prefill
            # 2026-11-05: declared quarter, granted 4 cores, job refused rc 8 "not a whole quarter")
            fl = re.fullmatch(r"multi-quarter\(([23])\)", str(d.get("declared_shape") or d.get("shape") or ""))
            floor = int(fl.group(1)) if fl else (1 if str(d.get("declared_shape") or d.get("shape") or "") == "quarter"
                                                 or d.get("timing") or d.get("admission_class") in GPU_TIMING_CLASSES else 0)
            floored = floor > max(-(-threads // 24), nq_ram) or (floor and threads <= SUB_CORES)
            n = max(n, floor)
            if threads <= SUB_CORES and nq_ram <= 1 and not floor:
                shape, opts = "sub-quarter", _sub_blocks()
            elif n <= 1:
                shape, opts = "quarter", [frozenset({q}) for q in QUARTERS]
            else:
                n = min(n, 3)
                shape, opts = f"multi-quarter({n})", [frozenset(c) for c in sorted(itertools.combinations(QUARTERS, n), key=lambda c: ("q3" in c, c))]   # q0-q2 combinations first
        else:   # threads unknown, or a legacy engine whose claim locks more: the claim is what gets locked
            qs = quarters_of(cc, fold=True) if cc else (set() if abstract else quarters_of(decl_cpus, fold=True))
            if cc and not (cpu_tokens(cc) & set(QUARTERS)):
                shape, opts = "sub-quarter", [frozenset(cpu_tokens(cc))]
            elif honours and len(qs) >= 2:   # unknown size, lock follows the grant: the declared width, never a whole host
                dm = re.fullmatch(r"multi-quarter\(([23])\)", str(d.get("shape") or ""))
                n = int(dm.group(1)) if dm else 1
                shape = f"multi-quarter({n})" if n > 1 else "quarter"
                opts = [frozenset(x) for x in itertools.combinations(QUARTERS, n)]
            elif len(qs) >= 4:   # legacy engine: its claim is what gets locked (publish refuses this without evidence)
                shape, opts = ("quiet-host" if gq == "exclusive" else "host"), [frozenset(QUARTERS)]
            elif len(qs) >= 2 or nq_ram >= 2:
                n = min(max(len(qs), nq_ram), 3)
                shape = f"multi-quarter({n})"
                opts = [frozenset(qs)] if len(qs) == n else [frozenset(c) for c in itertools.combinations(QUARTERS, n)]
            elif qs:
                shape, opts = "quarter", [frozenset(qs)]
            else:
                within = [x.strip() for x in regs[len("any-of"):].split(",")] if regs.startswith("any-of") else QUARTERS
                shape, opts = "quarter", [frozenset({q}) for q in within if q in QUARTERS]
        if shape.startswith("multi-quarter(") and not gpu_tok:
            # operator 2026-11-06 "Yes, both": a CPU row's multi-quarter booking is q0-q2 ONLY. q3's cores 88-95 are the
            # physical cores behind the MI210 host threads 184-191 (lsa-quality-32k-r5-pca got q1+q3; c7-q38-ppl-bisect-r5
            # then waited 600 s on the q3 lock, rc75, MI210 idle ~40 min). A multi-quarter row waits for q0-q2 instead.
            nmq = int(shape[len("multi-quarter("):-1])
            opts = [o for o in opts if "q3" not in o] or [frozenset(c) for c in itertools.combinations(QUARTERS[:3], nmq)]
        opts = [frozenset(x | gpu_tok) for x in opts]
    # keeper classfix 2026-11-05 (iqk-q8-prefill-ab-r3 regions q2 + shape_override -> granted 80-83 on q3;
    # inf75-c5-w3-halfb-census-c6-r2 mi210_0,48-95,144-191 + shape_override -> mi210_0,80-83): explicit concrete
    # regions are honoured VERBATIM - never shrunk or moved - for a CPU row, and for any row carrying shape_override
    explicit = (not whole and bool(decl_cpus) and (bool(str(d.get("shape_override") or "").strip())
                                                   or (not gpu_row and len(quarters_of(decl_cpus, fold=True)) <= 1)))
    if explicit:
        et = cpu_tokens(decl_cpus, gpu_threads=gpu_row)
        nq = len(et & set(QUARTERS))
        opts = [frozenset(et | gpu_tok)]
        cpu_extra = {t for t in et - set(QUARTERS) if t in CORES}
        shape = ("sub-quarter" if not nq else "quarter" if nq == 1 and not cpu_extra else
                 f"multi-quarter({min(nq, 3)})" if not cpu_extra else shape)
        floored = True
    if regs.startswith("any-of") and not whole and not explicit:
        # PM-ANYOF 2026-11-20 (lsa-cpu-sparse-e2e-bound-20261120-r1: "any-of q1,q2" granted q0): only the last
        # derivation branch read the any-of set; every threads-known branch emitted all QUARTERS. The declared set
        # is a hard allow-list for every option: quarter, core and sibling-thread tokens must all fall inside it.
        allowed = {x.strip() for x in regs[len("any-of"):].split(",") if x.strip() in QUARTERS}

        def _quarter_of(t):
            if t in QUARTERS:
                return t
            m = re.fullmatch(r"[ct](\d+)", t)
            if not m or (t[0] == "t" and int(m.group(1)) in GPU_HOST_THREADS):
                return None   # not a cpu token, or an MI210 host thread (the GPU token's own business)
            return f"q{(int(m.group(1)) % 96) // 24}"
        inside = [x for x in opts if {_quarter_of(t) for t in x} - {None} <= allowed]
        if allowed and not inside:   # declared width > set size: the whole set, never a quarter outside it
            inside = [frozenset(allowed | gpu_tok)]
        opts = inside or opts
    opts = [frozenset(compress(expand(x))) for x in opts if x] or [frozenset({q} | gpu_tok) for q in QUARTERS]
    held = max((len({t for t in expand(x) if t in CORES}) for x in opts), default=0)
    need_cores = held if (whole or gpu_use or threads is None or floored) else (SUB_CORES if threads <= SUB_CORES else 24 * -(-threads // 24))
    widened = ""
    if shape.startswith("multi-quarter(") and not whole and threads is not None and not explicit:
        nmq = int(shape[len("multi-quarter("):-1])
        if nmq > -(-threads // 24):
            widened = (f"{nmq} quarters for {threads} threads: " + ("declared shape floor" if floored else
                       f"RAM {gib} GiB > {QUARTER_RAM_GIB} GiB/quarter" if gib > QUARTER_RAM_GIB else "unknown"))
    return {"shape": shape, "options": opts, "bench": gq == "exclusive", "widened": widened, "threads": threads, "gpu_use": gpu_use,
            "timing": timing, "evidence": evidence, "lock": honours, "need": need_cores, "held": held,
            "claim": cc if cls != "gpu" else "", "explicit_cpus": decl_cpus if explicit else ""}


def shape_of(d, o=None):
    return contract_of(d, o)["shape"]


def row_shape(d):
    c = contract_of(d)
    return c["options"], c["bench"]


def whole_host_evidence(d):
    return contract_of(d)["evidence"]


def lock_cpus(option):
    """The cpu list a CONTRACT_LOCK engine locks for a grant option (whole quarters as the engine's own quarter lists)."""
    qs = ",".join(sorted(q for q in option if q in QUARTERS))
    return ",".join(x for x in (grant_cpus(qs), tokens_cpus(option)) if x)


def grant_regions(d, option):
    """The regions= string of a grant for `option`: exactly the cpus the contract holds (a GPU row keeps its regions
    unless the contract clipped them; a concrete CPU region that matches the option is kept verbatim)."""
    regs = str(d.get("regions") or "")
    if "mi210" in regs and str(d.get("shape_override") or "").strip():
        return regs   # keeper classfix 2026-11-05: explicit regions + shape_override are honoured verbatim
    if re.fullmatch(r"q[0-3](,q[0-3])*", regs.replace(" ", "")) and set(regs.replace(" ", "").split(",")) == {q for q in option if q in QUARTERS}:
        return ",".join(cpu_list(q) for q in regs.replace(" ", "").split(","))
    if "mi210" in regs:
        cpus = _cpu_set(ws58_cpus(regs))
        held = {int(t[1:]) for t in expand(option) if re.fullmatch(r"[ct]\d+", t)}
        if cpus <= held:
            return regs
        return "mi210_0," + compress_cpus((cpus & held) or (held & GPU_HOST_THREADS) or GPU_HOST_THREADS)
    qs = sorted(q for q in option if q in QUARTERS)
    if not qs and any(t in CORES for t in option):
        return tokens_cpus(option)   # sub-quarter grant: the exact cpu list
    if regs == "any-cpu-quarter" or regs.startswith("any-of") or quarters_of(ws58_cpus(regs)) != set(qs):
        return ",".join(cpu_list(q) for q in qs) if qs else regs
    return regs


# ---------------------------------------------------------------- BUILD-POCKET carve-out (pipeline-mgmt 2026-11-20)
# filler-ak-q38fn-draftfa-window-cpu-20261119 (multi-quarter(3), 28000 s) held q0-q2 for ~7.8 h; q3 is the MI210's host
# threads, so a short build region-lock claim waited >45 min with no pocket. Thresholds live in build_pocket_policy.json
# (override: <flags>/allocator.json {"build_pocket": {...}}). See the JSON's _doc for the rule.
BUILD_POCKET_POLICY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_pocket_policy.json")
BUILD_WAIT_DIR = "build-wait"   # <flags>/build-wait/<owner>-<ts>.json: a refused `claim --build` (it had no pocket)


def build_pocket_policy(flags=None):
    pol = {"stopping_horizon_s": 600, "long_hold_s": 7200, "max_hold_s": 7200, "waiter_ttl_s": 7200, "waiter_ttl_cap_s": 1800, "queue_dir": TMP.rstrip("/") + "/queue"}
    pol.update({k: v for k, v in (load_json(BUILD_POCKET_POLICY_FILE) or {}).items() if not k.startswith("_")})
    if flags:
        pol.update((load_json(os.path.join(flags, "allocator.json")) or {}).get("build_pocket") or {})
    return pol


def _pid_live(pid):
    try:
        return os.path.isdir(f"/proc/{int(pid)}")
    except (TypeError, ValueError):
        return False


def build_waiters(flags, now=None, rowids=(), log=None):
    """Build claims waiting for a q0-q2 pocket: a live FIFO lock ticket on q0-q2 (region-lock queue dir; the tag is not a
    row id) or an unexpired build-wait record whose pid is alive (a record with no pid, a dead pid or a zombie is ignored and logged
    BUILD-WAIT-STALE, never deleted; its TTL is min(waiter_ttl_s, waiter_ttl_cap_s) - a refused re-claim refreshes at_epoch). [{src, who, since}]."""
    now = time.time() if now is None else now
    pol = build_pocket_policy(flags)
    ttl = float(pol["waiter_ttl_s"])
    out = []
    for p in glob.glob(os.path.join(str(pol["queue_dir"]), "*.json")):
        t = load_json(p) or {}
        regs = {str(r) for r in (t.get("regions") or [])}
        if not (regs & {"q0", "q1", "q2"}) or not _pid_live(t.get("pid")) or str(t.get("tag") or "") in rowids:
            continue
        since = float(t.get("created_at") or now)
        if now - since <= ttl:
            out.append({"src": "ticket", "who": str(t.get("tag") or t.get("pid")), "since": since})
    for p in glob.glob(os.path.join(flags, BUILD_WAIT_DIR, "*.json")):
        t = load_json(p) or {}
        since = float(t.get("at_epoch") or 0)
        owner = str(t.get("owner") or os.path.basename(p)[:-5] or "?")
        if now - since > min(ttl, float(pol.get("waiter_ttl_cap_s", ttl))):
            continue
        if proc_alive(t.get("pid")):
            out.append({"src": "build-wait", "who": owner, "since": since})
        elif log:
            log(f"BUILD-WAIT-STALE {owner}: record pid {t.get('pid')!r} is absent/dead; ignored (record kept)")
    return out


def long_q012_cand(c, flags_pol):
    """A long, undeclared CPU row that books all of q0-q2 (the build-pocket rule applies to it)."""
    if c.get("whole_host_need") or c.get("lane") == "gpu" or c.get("shape") in ("host", "quiet-host"):
        return False
    return hold_s(c) > float(flags_pol["long_hold_s"]) and any(
        {"q0", "q1", "q2"} <= set(o) and GPU not in o for o in c["options"])


DRAIN_AFTER_S = 3600      # a host / multi-quarter row that waited this long drains the host (age boost; never preempts)
DRAIN_MAX_WAIT_S = 3600  # ws58 hotfix: drain only when the host frees within 1 h
# D9 2026-11-18 (KEEPER-DRAIN-HOLDS-GPU): a drain target whose earliest start lies beyond this horizon gets NO reservation
# (nothing is drained for it); the DRAIN_AFTER_S age boost still ranks it first when its regions free.
DRAIN_RESERVE_HORIZON_S = 7200   # D9 2026-11-18: a PARTIAL-host drain target starting beyond this gets no reservation
# (rule 3): only quarter / sub-quarter / multi-quarter(n) targets are deferred; host / quiet-host / gpu-exclusive whole
# targets ALWAYS keep their reservation (the unconditional 7200 s horizon starved whole-host rows in the replay gate).


def drain_horizon_applies(c):
    """True when the drain target's contract shape is a partial host (quarter, sub-quarter, multi-quarter(n))."""
    shape = str(c.get("shape") or "")
    return shape in ("quarter", "sub-quarter") or bool(re.fullmatch(r"multi-quarter\(\d\)", shape))
URGENT_RANK = 10          # ws58 2026-11-02: an explicit operator priority_rank below this beats lane starvation (21:25Z
                          # four rank-1 pilots lost the host to a rank-30 whole-host row that was promoted as a drain)


# BACKFILL-IF-FITS (operator 2026-11-07): a waiting wide row reserves its regions only until its EARLIEST FEASIBLE START S
# (the ends of the grants that hold the regions it needs; live smokes count SMOKE_HOLD_S). A lower row may take them iff
# now + its book_s <= S. S unknown (a needed region busy with no known end), not in the future (expired) or beyond the
# longest busy window -> NO reservation at all; a persisted drain T in the past never blocks.
SMOKE_HOLD_S = 1200       # a live smoke's cores free within this bound (the dry-run deadline order of magnitude)

# ONE BOOKING DURATION (pipeline audit 2026-11-10 #3, operator scope "Scheduling model"): every admission question -
# backfill ahead of a drain target T, a rank hold, the earliest-start reservation - asks `now + book_s <= T`, where
#     book_s = clamp(estimate_s * BOOK_K, min_window_s, window_s)
# is computed ONCE at publish and stored in the row (book_s()). window_s stays the grant length (the engine's hard end).
# SAFETY kept: a row admitted ahead of T whose window outlasts T gets a grant whose end= is capped at T (plan.hard_end), so
# the engine's hard-end kill frees the regions at T even when it overruns its booking; a cap that would leave less than
# min_window_s + the gate margin is never written (that row is not admitted ahead of T).
# BOOK_K from the data (grants/*.ended 2026-10-27..11-10, actual wall / estimated_wall_s): 381 rc=0 `complete` runs of
# >= 120 s plus 9 window-killed overruns (counted as uncovered) -> P90 = 0.74; k = 0.75 covers 90.2 % of them (all 753
# completes incl. sub-2-minute ones: P90 0.43). Owners' estimates are long: the median run uses 14 % of its estimate.
BOOK_K = 0.75
CAP_SLACK_S = 300 + 120   # grant_ok_launcher MARGIN_S + the grant's 1-2 min start back-dating / minute flooring


def hold_s(c):
    """How long a candidate's grant would hold its regions (the booked window; abstract callers: the estimate)."""
    return float(c.get("window_s") or c.get("estimate_s") or 0)


def compute_book_s(estimate_s, min_window_s, window_s):
    """book_s = clamp(estimate_s * BOOK_K, min_window_s, window_s), whole seconds."""
    est, lo, hi = float(estimate_s or 0), float(min_window_s or 0), float(window_s or 0)
    b = max(est * BOOK_K, lo)
    return int(min(b, hi) if hi else b)


def book_s(c):
    """The ONE admission duration of a row/candidate: its published book_s; a row published before 2026-11-10 (no
    book_s) gets the same formula from its estimate/min_window/window, so old and new rows are admitted alike."""
    if c.get("book_s"):
        return float(c["book_s"])
    if not c.get("estimate_s"):
        return float(c.get("window_s") or 0)   # abstract callers with only a window
    return float(compute_book_s(c.get("estimate_s"), c.get("min_window_s"), c.get("window_s")))


def cap_ok(c, now, T):
    """A grant capped to end at T still clears the launcher gate's window >= min_window + margin."""
    return T - now >= float(c.get("min_window_s") or 0) + CAP_SLACK_S


DRAIN_MIN_BUSY = 0.5      # operator 2026-11-03 (session review 3.1): a row whose spec says it keeps < half its claim busy
                          # (a ~4%-busy row) is never promoted to a host/quiet-host drain; it still takes free regions


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


def check_quiet_guard(spec, regions=None):
    """Publish gate: optional spec quiet_guard_regions = a list of quarters the row books ON PURPOSE and keeps idle (a
    pre-registered contention guard, e.g. a /proc/stat sampler that rejects any cell where they are busy). Must be a
    non-empty list of qN names, a subset of the quarters the row's regions book. Returns the sorted list ([] when unset)."""
    qg = spec.get("quiet_guard_regions")
    if qg is None:
        return []
    need(isinstance(qg, list) and qg and all(isinstance(x, str) and re.fullmatch(r"q[0-3]", x) for x in qg),
         f"quiet_guard_regions {qg!r} must be a non-empty list of quarters, e.g. [\"q0\", \"q2\"]")
    booked = quarters_of(regions if regions is not None else spec.get("regions") or "")
    extra = sorted(set(qg) - booked)
    need(not extra, f"quiet_guard_regions {sorted(set(qg))} must be a subset of the row's booked regions "
                    f"{sorted(booked) or '(none: declare concrete regions, e.g. q0,q1,q2)'}; not booked: {extra}")
    return sorted(set(qg))


def quiet_guard_of(flags, rid):
    """The guard quarters a published row declares ([] = none). Read-only."""
    q = (load_json(ready_path(flags, rid)) or {}).get("quiet_guard_regions")
    return [x for x in q if isinstance(x, str)] if isinstance(q, list) else []


# the dry-run env a launcher must carry across a privilege wrapper. The engine derives
# FILLER_GRANTS_DIR / FILLER_STATE_DIR from FILLER_DRYRUN_DIR, so these are the only names it cannot reconstruct.
DRYRUN_REQUIRED_ENV = ("FILLER_DRYRUN", "FILLER_DRYRUN_DIR", "FILLER_DRYRUN_ONE_QUARTER", "FILLER_SMOKE", "WS58_REGIONS")


def check_env_passthrough(launcher):
    """Refuse a `sudo ... --preserve-env=LIST` wrapper whose LIST omits a required dry-run name (the cj6a launch.sh:33
    line dropped FILLER_GRANTS_DIR and its dry run polled the MAIN grants dir for 20 h). Returns the env_passthrough list."""
    try:
        text = re.sub(r"\\\n", " ", open(launcher, errors="replace").read())
    except OSError:
        return None
    lists = []
    for line in text.splitlines():
        if line.lstrip().startswith("#") or not re.search(r"\bsudo\b", line):
            continue
        for m in re.finditer(r"--preserve-env=(\S+)", line):
            lists.append([x for x in m.group(1).strip("'\"").split(",") if x])
    for lst in lists:
        miss = [n for n in DRYRUN_REQUIRED_ENV if n not in lst]
        need(not miss, f"sudo --preserve-env list omits {','.join(miss)}: the dry run would lose its world across sudo; use "
                       f"--preserve-env={','.join(dict.fromkeys(lst + list(DRYRUN_REQUIRED_ENV)))}")
    return sorted(set().union(*map(set, lists))) if lists else None


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


def _cpu_set(text):
    out = set()
    for t in str(text or "").split(","):
        a, _, b = t.strip().partition("-")
        if a.isdigit() and (not b or b.isdigit()):
            out |= set(range(int(a), int(b or a) + 1))
        elif re.fullmatch(r"q[0-3]", t.strip()):
            q = int(t.strip()[1])
            out |= set(range(24 * q, 24 * q + 24)) | set(range(96 + 24 * q, 120 + 24 * q))
    return out


def compress_cpus(cpus):
    out, run = [], []
    for c in sorted(cpus):
        if run and c == run[-1] + 1:
            run.append(c)
            continue
        if run:
            out.append(f"{run[0]}-{run[-1]}" if len(run) > 1 else str(run[0]))
        run = [c]
    if run:
        out.append(f"{run[0]}-{run[-1]}" if len(run) > 1 else str(run[0]))
    return ",".join(out)


WIDTH_JUSTIFICATION_MIN = 20


_LIT_THREADS = re.compile(r"(?:(?<![\w-])(?:--threads|-t)[ =]+|\bOMP_NUM_THREADS=)(\d+)\b")


def literal_threads_sum(launcher, o=None):
    """F6 (AK audit B6): the sum of LITERAL thread knobs (--threads N, -t N, OMP_NUM_THREADS=N) in the launcher text and
    (which carries its --cmd), comments skipped. 0 = none written literally (variables are contract_of's job, never guessed here)."""
    try:   # the launcher text already carries --cmd; reading o["cmd"] too would count it twice
        texts = [open(launcher, errors="replace").read()]
    except (OSError, TypeError):
        texts = [str((o or {}).get("cmd") or "")]
    tot = 0
    for t in texts:
        for ln in t.splitlines():
            if not ln.lstrip().startswith("#"):
                tot += sum(int(x) for x in _LIT_THREADS.findall(ln))
    return tot


def width_justified(row, c):
    """The justification text when a CPU row's extra width is admitted by width_justification, else ''. Never for a GPU
    row, a timing row or a whole-host shape: the q3/gpu-quiet placement rules are separate gates and stay unchanged."""
    wj = row.get("width_justification")
    if not isinstance(wj, str) or len(wj.strip()) < WIDTH_JUSTIFICATION_MIN:
        return ""
    gpu = bool(c.get("gpu_use")) or str(row.get("lane")) == "gpu"
    if c["shape"] in ("host", "quiet-host") or (not gpu and (c.get("timing") or row.get("timing"))):
        return ""   # a GPU row's width is whole q0-q2 quarters only (contract_of clips the rest)
    return wj.strip()


def check_shape_evidence(spec, o):
    """Publish gate for the whole-host evidence fields themselves."""
    br = spec.get("baseline_ref")
    if br is not None:
        need(isinstance(br, str) and br.strip(), "baseline_ref must name the decision-grade baseline / production-serving measurement")
        if br.startswith("/"):
            need(os.path.exists(br), f"baseline_ref {br} does not exist")
    wj = spec.get("width_justification")
    if wj is not None:
        need(isinstance(wj, str) and len(wj.strip()) >= WIDTH_JUSTIFICATION_MIN,
             f"width_justification must be a string of >= {WIDTH_JUSTIFICATION_MIN} characters naming why the extra width helps")
    so = spec.get("shape_override")
    if so is not None:
        need(isinstance(so, str) and re.match(r"^operator:\s*\S+.*\d{4}-\d{2}-\d{2}.*:\s*\S", so),
             "shape_override must read \"operator: <who> <YYYY-MM-DD>: <why>\"")


def regions_wider_lint(regions, c, row=None):
    """a warning when the spec's concrete regions name more physical cores than the
    evidence contract's widest option holds (e.g. shape quarter with regions 48-95, or a gpu row with mi210_0,48-95,...).
    The grant follows the contract, so the extra regions only mislead readers / dashboards / hand-written launchers that
    read regions=. None when regions are abstract, within the contract, or carry an operator shape_override."""
    regs = str(regions or "")
    if regs == "any-cpu-quarter" or regs.startswith("any-of") or str((row or {}).get("shape_override") or "").strip():
        return None
    cpus = ws58_cpus(regs)
    if not cpus and re.fullmatch(r"q[0-3](,q[0-3])*", regs.replace(" ", "")):
        cpus = ",".join(cpu_list(q) for q in regs.replace(" ", "").split(","))
    cores = {x % 96 for x in _cpu_set(cpus) if x not in GPU_HOST_THREADS}   # MI210 host threads are not cores booked
    held = int(c.get("held") or 0)
    if len(cores) <= held:
        return None
    return (f"REGIONS-WIDER-THAN-SHAPE: regions {regs} name {len(cores)} cores but the contract ({c.get('shape')}) holds "
            f"{held}; the grant follows the contract - republish with regions matching the shape (or drop regions)")


def claim_wider_refusal(row, c, o):
    """Pipeline audit 2026-11-10 #2: the launcher's region-lock claim (--claim-cpus / --gpu-quiet, as grant_ok_launcher
    reads them) must be covered by EVERY grant the contract can produce. Otherwise the planner places the row, the
    admission gate refuses it rc=13 ("claims q0+q1+q2+q3+gpu-quiet, regions=0-23 ... missing q1+q2+q3") on every tick,
    and the row parks after a PASS (akx-lb3-2-cv6-pair-20261107-r2: 56 refusals). Mirrors admit() + gate.check exactly
    (same parse_regions / claim_of / cpu_regions / region_set, same reserve). Returns the refusal text, or None.
    A claim that is not a literal cpu list at publish ($WS58_REGIONS, $CPUS) and a --self-claim job are not judged."""
    argv = list((o or {}).get("argv") or [])
    if not argv:
        return None
    gate = _gate()
    go = gate.parse_engine(argv)
    if not go or go.get("self_claim"):
        return None
    if go.get("claim_cpus") and not re.fullmatch(r"\d+(-\d+)?(,\d+(-\d+)?)*", go["claim_cpus"]):
        return None
    misses = []
    for opt in c.get("options") or []:
        regions = grant_regions(row, opt)
        reserve = "gpu-quiet" if "mi210" not in regions else None   # as admit() passes it
        try:
            cpus = gate.parse_regions(regions, go["class"], go["gpu_threads"])
        except gate.Refuse:
            continue   # an unparsable grant is a different defect (the gate names it); not this check's
        cl, gm = gate.claim_of(go, cpus)
        fold = not (go["nofold"] and go["class"] != "gpu")
        want = gate.cpu_regions(cl, fold) if cl else set()
        if gm:
            want.add("gpu-quiet")
        have = gate.region_set(regions) | (gate.region_set(reserve) if reserve else set())
        miss = want - have
        if miss:
            misses.append((regions, gate.fmt(want), gate.fmt(miss)))
    if not misses:
        return None
    regions, want, miss = misses[0]
    flags_s = (f"--class {go['class']}" + (f" --claim-cpus {go['claim_cpus']}" if go.get("claim_cpus") else "")
               + (f" --gpu-quiet {go['gpu_quiet']}" if go.get("gpu_quiet") else ""))
    return (f"CLAIM-WIDER-THAN-CONTRACT: the launcher ({flags_s}) claims {want}, but the contract ({c.get('shape')}) grants "
            f"regions={regions} which miss {miss}; the admission gate would refuse every grant rc=13 and the row would park "
            f"after its PASS ({len(misses)} of {len(c.get('options') or [])} grant option(s) affected). FIX: narrow the "
            f"launcher's claim to the shape (e.g. --claim-cpus \"$WS58_REGIONS\", or drop --gpu-quiet exclusive for a CPU "
            f"row that does not need the MI210 idle), or declare the width the claim needs (shape/regions + "
            f"width_justification or baseline_ref), then re-run publish_row.py")


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


def drain_outranks(c, drain):
    """PM-INVERSION 2026-11-20: a drain reserved for row `drain` never binds a row with a STRICTLY better rank (lower
    number) - better-ranked rows always take precedence and the drain re-forms after them. Only rows of equal or worse
    rank are drain-late (the whole-host starvation protection the replay gate checks)."""
    # PM-DRAINFIX 2026-11-22: a STICKY drain (formed on an earlier tick, T still ahead) binds EVERY row, better-ranked
    # ones included: once formed, T is fixed and only moves earlier (inf45-e5v2-stageb-r7: a stream of rank-20 GPU rows
    # each re-formed the drain later, 00:01Z -> 05:14Z, and the rank-25 quiet-host row lost the whole night)
    return drain is not None and c is not drain and (bool(drain.get("drain_sticky")) or float(c["rank"]) >= float(drain["rank"]))


def drain_blocker(c, pending, free=None, ram=None, gpu_grant_open=False, held_ports=()):
    """The best-ranked pending row (strictly better rank than c) that wants any region c's drain would hold, or None.
    A drain is never set for c while such a row is runnable: rank decides who gets the regions when they free.
    ws58 2026-11-03: with a snapshot (free, ram) only a blocker that is placeable THIS tick and not failing to arm
    holds c (yarn-e1-a2-gpu, rank 7, failed to arm 172 times and held every quiet-host row for 7 h on an idle host)."""
    need = set().union(*c["options"]) if c["options"] else set()
    better = [x for x in pending if x is not c and float(x["rank"]) < float(c["rank"]) and any(o & need for o in x["options"])]
    if free is not None:
        better = [x for x in better if placeable(x, free, ram, gpu_grant_open, held_ports)]
    return min(better, key=plan_order) if better else None


def _placeable_now(x, free, ram, gpu_grant_open, drain, need_r, now, T):
    """x has a fitting option this tick that a drain does not refuse it (drain-late rows only take non-drain regions)."""
    opts = _fits(x, free, ram, gpu_grant_open)
    if drain_outranks(x, drain) and (now + book_s(x) > T or now + hold_s(x) > T) and not cap_ok(x, now, T):
        opts = [o for o in opts if not (o & need_r)]
    return bool(opts)


def rank_fragment_ok(c, o, contenders, free, ram, gpu_grant_open, held_ports=(), eff=None):
    """PM-INVERSION 2026-11-20 (22:54Z: rank-35 quarter row lsa took q0, rank-22 multi-quarter(3) c16-fold-cpu could no
    longer fit, q1+q2 idled): option o of c is refused when a STRICTLY better-ranked contender that fits the free set now
    would have no fitting option left once o is taken. contenders: pending rows plus build-pocket-held rows (held rows
    keep their regions for the build claim and their own rank, never for a worse row to fragment). Only MULTI-QUARTER
    contenders (an option spanning >= 2 quarters) count: same-width contention keeps the starved-lane order. eff(h, opts)
    drops options a drain / deferred horizon would refuse h anyway (a refused contender reserves nothing)."""
    for h in contenders:
        if h is c or float(h["rank"]) >= float(c["rank"]) or not placeable(h, free, ram, gpu_grant_open, held_ports):
            continue
        if not any(sum(1 for q in QUARTERS if q in x) >= 2 for x in h["options"]):
            continue
        opts = _fits(h, free, ram, gpu_grant_open)
        if eff is not None:
            opts = eff(h, opts)
        if opts and not any(not (x & o) for x in opts):
            return False
    return True


def stop_reserved(c, contenders, free, stopping, ram, gpu_grant_open, ports, horizon_s):
    """PM-STOPRES 2026-11-21 (c17-fold-cpu rank 22 needs q0-q2; its owner STOPped nta (q0) and idxk (q1+q2); q0 freed first
    and a rank-40 quarter row took it while idxk was still checkpointing). Regions held by a grant whose STOP file is set
    free imminently (stopping). A STRICTLY better-ranked multi-quarter contender h that does not fit now but would fit
    once the stopping regions end reserves the already-free quarters of that option. Returns [(h, regions)]; the caller
    refuses c any option touching them unless c's booking ends within horizon_s."""
    if not stopping:
        return []
    out = []
    for h in contenders:
        if h is c or float(h["rank"]) >= float(c["rank"]) or _fits(h, free, ram, gpu_grant_open):
            continue
        if own_block(h, free, ram, gpu_grant_open, ports) is not None:
            continue
        for x in sorted(h["options"], key=lambda o: sorted(o)):
            if sum(1 for q in QUARTERS if q in x) >= 2 and x & stopping and x <= (free | stopping):
                out.append((h, frozenset(x & free)))
                break
    return out


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
        busy = sorted(set().union(*[o - free for o in h["options"] if o])) if h.get("options") else []
        return (f"busy_fraction {row_busy(h):g} < {DRAIN_MIN_BUSY:g}: runs only when its regions are free"
                + (f" (its own regions {','.join(compress(set(busy)))} are busy; other free cores do not fit it)" if busy else ""))
    return None


def earliest_start(c, free, now, grant_ends=(), region_ends=None):
    """(S, why): the earliest feasible start of waiting row c - the time every region of its best option is free, from
    the ends of the grants (and live smokes) holding them (region_ends {token: end epoch | None}). A needed region with no
    known end (foreign hold) counts as freeing at S or later, S = the latest known end (else the latest running-grant
    end). S is None (no reservation) when nothing at all has a known end, when S is not in the future (an expired grant still
    held: it frees any moment) or when S lies beyond the longest busy window (the latest running-grant end). Abstract
    callers (region_ends None) fall back to the latest running-grant end."""
    later = [float(e) for e in grant_ends if e and float(e) > now]
    longest = max(later) if later else None
    if region_ends is None:
        best = longest
    else:
        best = None
        for o in c["options"]:
            ends = [region_ends.get(r) for r in (o - free)]
            known = [float(e) for e in ends if e is not None]
            if len(known) < len(ends):
                # coordinator 2026-11-10 (rank-2 floor slipped 19:07Z -> 21:11Z): a foreign / unknown-end hold on ONE
                # needed region never releases the reservation on the others. The unknown region "frees at T or
                # later": T = the latest KNOWN end among the needed regions; with none known, the latest running-grant
                # end; with neither, no reservation.
                if not known:
                    if longest is None:
                        continue
                    known = [longest]
            s = max(known or [now])
            best = s if best is None else min(best, s)
        if best is None:
            return None, "a needed busy region has no known end (foreign hold) and no running grant end is known"
    if best is None:
        return None, "no running grant end is known"
    if best <= now:
        return None, "its regions' grants are past their end (expired): they free any moment"
    if longest is None or best > longest:
        return None, f"start {dt.datetime.fromtimestamp(best, dt.timezone.utc):%Y-%m-%dT%H:%MZ} is beyond the longest busy window"
    return best, None


def rank_reservation(c, pending, free, ram, gpu_grant_open, ports, now, grant_ends, drain):
    """ws58 2026-11-04 (rank inversion): the regions c may NOT take because a strictly better-ranked pending row that
    cannot be placed yet needs them and is blocked only by busy regions that free within DRAIN_MAX_WAIT_S (T = latest
    running-grant end); c may still take them when it ends by T. Returns (reserved regions, [(h, T)], [(h, reason)]) -
    the holds that bind c, and the better rows that bind nothing because they are blocked by their own constraint."""
    reserved, holds, skips = set(), [], []
    later = [float(e) for e in grant_ends if float(e) > now]
    dur = book_s(c)
    for h in pending:
        if h is c or h is drain or float(h["rank"]) >= float(c["rank"]) or _fits(h, free, ram, gpu_grant_open):
            continue
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
        over = now + dur > T or now + hold_s(c) > T
        if over and not cap_ok(c, now, T):
            reserved |= need
            holds.append((h, T))
        elif over:   # D9 2026-11-11: overruns T but a T-capped grant clears its min window: its grant ends at T (hard-end cap)
            plan.caps.append((c["id"], need, T))
    return reserved, holds, skips


# D9 2026-11-18 GPU-Q3-GUARD (codemode-ab-v2-35b-cpu-20261118-r2 took all of q3 for 24 h at 20:30Z; the MI210 idled with
# 9 gpu-q3 rows queued): while any GPU-lane row is grantable or queued, a CPU row placed on q3 never takes q3's cores
# 88-95 (SMT 184-191, the MI210 host threads). For that grant q3 is "q3-narrow" = 72-87 (+168-183), offered only to a
# row whose declared threads fit 16 cores and only when no q0-q2 option fits; a row needing all 24 cores waits for
# q0-q2. Host / quiet-host / GPU rows and the no-GPU-queued case are unchanged.
Q3_NARROW = frozenset({f"c{k}" for k in range(72, 88)} | {f"t{k}" for k in range(168, 184)})
Q3_NARROW_CORES = 16
Q3_GUARD = frozenset({f"c{k}" for k in range(88, 96)} | {f"t{k}" for k in range(184, 192)})


def gpu_lane_cand(c):
    """A GPU-lane candidate: its lane is gpu, or (not a host / quiet-host row) an option holds gpu-quiet."""
    return c.get("lane") == "gpu" or (c.get("shape") not in ("host", "quiet-host")
                                      and any(GPU in o for o in c.get("options") or ()))


def gpu_q3_guard(c):
    """The options of CPU candidate c under GPU-Q3-GUARD (options already expanded): a q3 whole-quarter option becomes
    Q3_NARROW when c's threads fit Q3_NARROW_CORES, else it is dropped; any other option touching 88-95/184-191 is
    dropped. Host-wide options (all four quarters) and GPU-lane rows are returned unchanged."""
    if gpu_lane_cand(c) or c.get("shape") in ("host", "quiet-host") or c.get("explicit"):
        # explicit concrete regions stay honoured verbatim (operator 2026-11-18 scope add, rule 4: the declare-only
        # contract package handles pins)
        return list(c["options"])
    th = c.get("threads")
    fits = th is not None and int(th) <= Q3_NARROW_CORES
    out = []
    for o in c["options"]:
        if sum(1 for q in QUARTERS if q in o) >= 4:
            out.append(o)
        elif "q3" in o:
            if fits and not any(q in o for q in QUARTERS[:3]):
                out.append(frozenset((o - expand({"q3"})) | Q3_NARROW))
        elif o & Q3_GUARD:
            continue
        else:
            out.append(o)
    return out


def plan(free, cands, ram_gib, gpu_grant_open=False, now=None, grant_ends=(), quiet_ok=True, held_ports=(), drain_prev=None,
         region_ends=None, region_holders=None, gpu_queued=False, build_waiting=False, build_policy=None, stopping=()):
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
    BACKFILL-IF-FITS (operator 2026-11-07): T is the drain row's earliest feasible start (earliest_start:
    region_ends {token: end | None}); unknown, expired or beyond the longest busy window -> no reservation
    (plan.no_reserve = [(row, why)]); a persisted T is used only while it is still in the future.
    BUILD-POCKET (2026-11-20): a long (> long_hold_s) undeclared q0-q2 row is not placed while build_waiting (plan.build_held);
    a resumable one is placed with a hard end at max_hold_s (build_policy; plan.hard_end) so the pocket reopens at the cut.
    STOP-RESERVE (PM-STOPRES 2026-11-21): stopping = tokens held by grants whose STOP file is set (checkpointing, free within
    build_policy stopping_horizon_s); a better-ranked multi-quarter row that fits once they end reserves the already-free
    quarters (plan.stop_reserves = [(worse row, better row, regions)]); worse rows ending within the horizon may still take them.
    Returns (assigned [(cand, option)], idle {region: reason}, pending); plan.last_drain = (cand, T) or None."""
    now = time.time() if now is None else now
    free = set(free)
    if not any(t in CORES or t in THREADS for t in free):
        # abstract caller (regions only): a free quarter's cores/threads are free, and so are the MI210's host threads
        free = expand(free) | ({f"t{k}" for k in range(184, 192)} if GPU in free else set())
    else:   # token-level caller: a quarter is free for a whole-quarter row only when every core/thread it runs on is
        free = {t for t in free if t not in QUARTERS or expand({t}) <= free}
    # ws58 sub-quarter: a whole quarter also holds its core tokens. PURE: expand into shallow copies, never the
    # caller's dicts (e40203894 rewrote c["options"] in place; the returned assigned/pending carry the copies).
    cands = [dict(c, options=[frozenset(expand(o)) for o in c["options"]]) for c in cands]
    # D9 2026-11-18 GPU-Q3-GUARD: gpu_queued (a GPU-lane row queued but not a candidate) or a GPU-lane candidate
    plan.gpu_q3_guard = bool(gpu_queued) or any(gpu_lane_cand(c) for c in cands)
    if plan.gpu_q3_guard:
        cands = [dict(c, options=gpu_q3_guard(c)) for c in cands]
    bp = dict(build_policy or build_pocket_policy())
    plan.build_held = []
    held = []
    if build_waiting:   # BUILD-POCKET (a): a build claim is waiting - a long undeclared q0-q2 row is not booked over its pocket
        held = [c for c in cands if long_q012_cand(c, bp)]
        plan.build_held = [c["id"] for c in held]
        cands = [c for c in cands if c not in held]
    plan.build_held_rows = held
    stopping = expand(set(stopping or ()))
    stop_h = float(bp.get("stopping_horizon_s", 600))
    plan.stop_reserves = []   # [(worse row, better row, regions)]
    pending = sorted(cands, key=plan_order)
    if not quiet_ok:
        pending = [c for c in pending if c.get("shape") != "quiet-host"]
    free, ram, out = set(free), float(ram_gib), []
    ports = {int(x) for x in held_ports}
    drain, T = None, None
    plan.drain_held = []
    plan.drain_lowbusy = []
    plan.no_reserve = []
    plan.drain_deferred = []   # [(row, S)]: earliest start S beyond DRAIN_RESERVE_HORIZON_S -> no reservation
    dfr_r, dfr_T = set(), None   # D9 2026-11-18 "only admit rows that end within 2 h": a deferred target's regions take
    # only rows ending by now + DRAIN_RESERVE_HORIZON_S (capped there, or refused) - so its earliest start never moves later
    plan.rank_holds = []   # [(lower row, better row, T)]: the lower row was kept off the better row's regions
    plan.rank_skips = []   # [(lower row, better row, reason)]: a lower row took regions a better row wants (own block)
    plan.caps = []         # [(row id, regions, T)]: admitted by estimate ahead of T on these regions -> grant end capped at T
    plan.hard_end = {}     # {row id: T}: the placed row's grant must end by T (DRAIN-BY-ESTIMATE safety)
    def _prev_T(c):
        v = (drain_prev or {}).get(c["id"])
        try:
            return float(v) if v is not None and float(v) > now else None
        except (TypeError, ValueError):
            return None
    # PM-DRAINFIX 2026-11-22: a drain formed on an earlier tick (persisted T still ahead) is considered FIRST and is not
    # dropped for a better-ranked row (drain_blocker), so its T can never slide later
    for c in sorted(pending, key=lambda c: _prev_T(c) is None):
        big = any(len([r for r in o if r in QUARTERS]) >= 2 for o in c["options"])
        sticky_T = _prev_T(c)
        if big and (c.get("shape") == "quiet-host" or now - float(c.get("since") or now) >= DRAIN_AFTER_S):
            if row_busy(c) < DRAIN_MIN_BUSY:   # operator 2026-11-03: a mostly idle row never books a quiet/whole host
                plan.drain_lowbusy.append(c)
                continue
            # PM-INVERSION 2026-11-20: build-pocket-held rows still outrank a drain target - they are off the plan only
            # for the build claim, so the drain must not form for a worse row and lock them out once the claim clears
            # (22:50Z: rank-22/40 q0-q2 rows build-held, invisible here; the rank-110 host row drained q0-q2 for 2.75 h)
            blocker = None if sticky_T is not None else drain_blocker(c, pending + held, free, ram, gpu_grant_open, ports)
            if blocker is not None:   # ws58 2026-11-02: a better-ranked row wants these regions; no promotion, no drain
                plan.drain_held.append((c, blocker))
                continue
            pending.remove(c); pending.insert(0, c)   # the drain row goes FIRST: at T it takes the host before any quarter row
            if not _fits(c, free, ram, gpu_grant_open):
                S, why = earliest_start(c, free, now, grant_ends, region_ends)
                prev = (drain_prev or {}).get(c["id"])
                if S is not None and prev and now < float(prev) < S:   # T only moves earlier; an EXPIRED T never blocks
                    S = float(prev)
                if sticky_T is not None:   # PM-DRAINFIX: a sticky T never moves later and never lapses to "unknown"
                    S = sticky_T if S is None else min(S, sticky_T)
                    c["drain_sticky"] = True
                if S is not None and sticky_T is None and S - now > DRAIN_RESERVE_HORIZON_S and drain_horizon_applies(c):   # D9 2026-11-18: partial-host only
                    plan.drain_deferred.append((c, S))
                    # PM-CAP 2026-11-21: backfill onto a deferred target's regions is bounded by its REAL earliest start S
                    # (a row ending by S cannot delay it), not by the 2 h horizon (which cut a 3.8 h single-quarter row at 7260 s
                    # with S = 6.4 h away; ak-draft-head-svd-cpu-20261121-r2q0). The horizon only decides "no reservation".
                    dfr_r, dfr_T = set().union(*c["options"]), S
                    S, why = None, (f"earliest start {dt.datetime.fromtimestamp(S, dt.timezone.utc):%Y-%m-%dT%H:%MZ} "
                                    f"beyond reserve horizon {DRAIN_RESERVE_HORIZON_S}s")
                if S is None:
                    plan.no_reserve.append((c, why))
                else:
                    drain, T = c, S
            break
    plan.last_drain = (drain, T) if drain else None
    need_r = set().union(*drain["options"]) if drain is not None else set()
    if drain is not None:  # best fit: the longest backfill that still ends by T goes first, so the gap is packed
        dur = book_s
        pending = [drain] + sorted([c for c in pending if c is not drain], key=lambda c: (drain_outranks(c, drain), now + dur(c) > T, -dur(c)))
        # (PM-INVERSION: strictly better-ranked rows first - the drain never binds them)
    unfit = set()   # MIN-CAP: rows whose hard-end cap would leave less than min_window_s + 300 this tick
    plan.min_cap_skips = []
    while pending:
        placed = None
        for c in pending:
            if c["id"] in unfit:
                continue
            # D9 2026-11-11 (operator "Cap backfill at T"): a row whose booking or hold overruns T is admitted capped at T
            # when the cap clears its min window (cap_ok); only a row the cap would starve below min_window stays late
            over = drain_outranks(c, drain) and (now + book_s(c) > T or now + hold_s(c) > T)
            late = over and not cap_ok(c, now, T)
            capd = over and not late
            opts = _fits(c, free, ram, gpu_grant_open)
            if late:   # a row ending after T may only take regions the drain row does not need (T bounds backfill, never kills)
                opts = [o for o in opts if not (o & need_r)]
            if dfr_T is not None and (now + book_s(c) > dfr_T or now + hold_s(c) > dfr_T) and not cap_ok(c, now, dfr_T):
                opts = [o for o in opts if not (o & dfr_r)]   # would end beyond the horizon: off the deferred target's regions
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
            if opts:   # PM-INVERSION: a worse row never fragments the quarters a better-ranked fitting row needs
                def _eff(h, hopts):
                    if drain_outranks(h, drain) and (now + book_s(h) > T or now + hold_s(h) > T) and not cap_ok(h, now, T):
                        hopts = [x for x in hopts if not (x & need_r)]
                    if dfr_T is not None and (now + book_s(h) > dfr_T or now + hold_s(h) > dfr_T) and not cap_ok(h, now, dfr_T):
                        hopts = [x for x in hopts if not (x & dfr_r)]
                    return hopts
                opts = [o for o in opts if rank_fragment_ok(c, o, pending + held, free, ram, gpu_grant_open, ports, _eff)]
            if opts and stopping and now + book_s(c) > now + stop_h:   # PM-STOPRES: a better row is waiting on stopping grants
                for h, res in stop_reserved(c, pending + held, free, stopping, ram, gpu_grant_open, ports, stop_h):
                    hit = [o for o in opts if o & res]
                    if hit:
                        if (c["id"], h["id"], res) not in [(a["id"], b["id"], r) for a, b, r in plan.stop_reserves]:
                            plan.stop_reserves.append((c, h, res))
                        opts = [o for o in opts if not (o & res)]
            if opts and not any(t in QUARTERS for x in opts for t in x) and not (plan.gpu_q3_guard and Q3_NARROW in opts):
                # (GPU-Q3-GUARD: a quarter row's q3-narrow option is its whole-quarter grant, not sub-quarter packing)
                # PACKING (operator "fix it" 2026-11-05): a sub-quarter row goes onto a partly used quarter; it breaks a
                # whole free quarter only while more are free than the whole-quarter rows that fit now need
                # AK audit 2026-11-20 (PACKING-GPU-INVERSION, MI210 idle 11:50-12:11Z): a GPU option (gpu-quiet + q3's
                # host threads 88-95/184-191) never "breaks" q3 - under GPU-Q3-GUARD no CPU row may take those cores -
                # and wq counts only whole-quarter rows that can really be placed now (not drain-late on every fitting
                # option); drain-late rank-45/57 quarter rows held rank-30 gpu-q3 rows off an idle MI210.
                keep = [x for x in opts if GPU in x or not any(q in free and expand({q}) & x for q in QUARTERS)]
                wq = sum(1 for x in pending if x is not c and any(t in QUARTERS for o2 in x["options"] for t in o2)
                         and _placeable_now(x, free, ram, gpu_grant_open, drain, need_r, now, T))
                opts = keep or (opts if sum(1 for q in QUARTERS if q in free) > wq else [])
            if not opts:
                continue
            if plan.gpu_q3_guard and any(not (x & Q3_NARROW and not x & set(QUARTERS)) for x in opts):
                # GPU-Q3-GUARD: q3-narrow only when no q0-q2 option fits (it is smaller, so min() would pick it first)
                opts = [x for x in opts if not (x & Q3_NARROW and not x & set(QUARTERS))] or opts
            # prefer the smallest option, then the one other pending rows want least (keeps their alternatives open)
            demand = {r: sum(1 for x in pending if x is not c for o2 in x["options"] if r in o2) for r in free}
            # operator 2026-11-10 ("Prefer q0-q2 for CPU rows"): a whole-quarter option on q3 goes last - q3 holds the
            # MI210's host cores c88-c95, so a CPU quarter row takes q3 only when it is its only fitting quarter (an
            # explicit q3 row has no other option; order only, never a reservation)
            # GPU-Q3-GUARD ordering (operator 2026-11-18): a CPU option touching 88-95/184-191 goes after every other one
            o = min(opts, key=lambda o: (GPU not in o and bool(o & Q3_GUARD), len(o), not (o & qcores("q3")) and not (o & set(QUARTERS)),
                                         "q3" in o and GPU not in o, sum(demand.get(r, 0) for r in o), sorted(o)))
            placed = (c, o)
            break
        if not placed:
            break
        c, o = placed
        caps = [t for rid, need, t in plan.caps if rid == c["id"] and need & o]
        if drain_outranks(c, drain) and (now + hold_s(c) > T or now + book_s(c) > T) and o & need_r:
            caps.append(T)
        if dfr_T is not None and (now + hold_s(c) > dfr_T or now + book_s(c) > dfr_T) and o & dfr_r:
            caps.append(dfr_T)
        if c.get("resumable") and long_q012_cand(c, bp) and {"q0", "q1", "q2"} <= set(o) and GPU not in o:
            # BUILD-POCKET (b): a resumable long row yields its pocket at a checkpoint; anticipatory, so it never cuts
            # below the launcher's gate (min_window_s + MARGIN_S): max(max_hold_s, min_window_s + 300) (2026-11-21 MIN-CAP)
            caps.append(now + max(float(bp["max_hold_s"]), float(c.get("min_window_s") or 0) + 300))
        if caps and min(caps) - now < float(c.get("min_window_s") or 0) + 300:
            # MIN-CAP guard: never hand out a window the launcher refuses (rc=12); hard boundary -> not granted this tick
            plan.min_cap_skips.append((c["id"], min(caps) - now))
            unfit.add(c["id"])
            continue
        if caps:
            plan.hard_end[c["id"]] = min(caps)
        out.append((c, frozenset(compress(o)))); free -= o; ram -= float(c.get("gib") or 0); pending.remove(c)
        ports |= {int(x) for x in (c.get("ports") or [])}
    idle = {}
    plan.idle_entries = {}   # {region: (head, [other rows' reasons])}: the keeper appends WAIT-FOR-SMOKE rows
    for r in sorted(x for x in free if x in REGIONS):
        want = [c for c in pending if any(r in o for o in c["options"])]
        # PM-INVERSION: the REAL fit reason - build-pocket-held rows wanting r, and rows that do not fit the free shape
        hw = [f"{x.get('shape') or x['kind']} row {x['id']} (rank {float(x['rank']):g}) BUILD-POCKET-HELD: long q0-q2 "
              f"row not booked while a build claim waits" for x in sorted(held, key=lambda x: (float(x["rank"]), x["id"]))
              if any(r in o for o in x["options"])]
        if not want and hw:
            plan.idle_entries[r] = (hw[0], hw[1:])
            idle[r] = idle_why_line(hw[0], hw[1:])
            continue
        if not want:
            idle[r] = "no runnable row needs it (every grantable/dry-runnable row is placed, running, failed or parked)"
            continue
        c = want[0]; why = []
        if drain is not None and r in need_r:   # D9 2026-11-18: only a region the drain reserves is "draining"
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
        head = f"{c['kind']} {c['id']} " + ("; ".join(why) or "blocked")
        # pipeline-mgmt 2026-11-11: EVERY other ready row that could use r, each with its own blocker (the drain row plus
        # one other row hid busy q3 cores, port/RAM holds and drain-late rows). Diagnostics only: placement is above.
        rest = [_idle_row_why(x, r, free, ram, gpu_grant_open, ports, drain, T, now, region_ends, region_holders)
                for x in sorted(want, key=lambda x: (float(x["rank"]), x["id"])) if x is not c] + hw
        plan.idle_entries[r] = (head, rest)
        idle[r] = idle_why_line(head, rest)
    return out, idle, pending


IDLE_WHY_MAX_ROWS = 8   # rows named per region per IDLE-WHY line; the rest collapse to "+N more"


def idle_why_line(head, rest, cap=IDLE_WHY_MAX_ROWS):
    """ONE line per region: the head row's reason, then up to cap-1 more rows' own reasons, then '+N more'."""
    rest = list(rest)
    shown, more = rest[:max(cap - 1, 0)], len(rest) - max(cap - 1, 0)
    return head + "".join("; also " + e for e in shown) + (f"; +{more} more" if more > 0 else "")


def _idle_row_why(c, r, free, ram, gpu_grant_open, ports, drain, T, now, region_ends=None, region_holders=None):
    """Why ready row c is not on idle region r this tick, from c's OWN constraint: drain-late, arming, port, RAM, a busy
    region (holder + end), the timing-row q3 rule, or a rank reservation."""
    head = f"{c.get('shape') or c['kind']} row {c['id']} (rank {float(c['rank']):g})"
    if drain_outranks(c, drain) and now is not None and T is not None:
        need_r = set().union(*drain["options"]) if drain["options"] else set()
        over = now + book_s(c) > T or now + hold_s(c) > T
        if over and not cap_ok(c, now, T) and any(r in o and o & need_r for o in c["options"]):
            return f"{head} drain-late: would end after T {dt.datetime.fromtimestamp(T, dt.timezone.utc):%H:%MZ}"
    if int(c.get("arm_fails") or 0) > 0:
        return f"{head} failing to arm (arm_fails={int(c.get('arm_fails') or 0)})"
    clash = set(ports) & {int(x) for x in (c.get("ports") or [])}
    if clash:
        return f"{head} port {','.join(map(str, sorted(clash)))} held by a running grant"
    if ram - float(c.get("gib") or 0) < RAM_MARGIN_GIB:
        return f"{head} RAM: {c.get('gib')} GiB would leave {ram - float(c.get('gib') or 0):.0f} GiB < {RAM_MARGIN_GIB} margin"
    o = next((o for o in c["options"] if r in o), set())
    if set(o) - set(free):
        return _blocked_by(c, r, free, region_ends, region_holders)
    if c.get("bench") and gpu_grant_open and "q3" in o:
        return f"{head} timing row keeps off q3 while a GPU grant is open"
    return f"{head} fits but is held for a better-ranked row (rank reservation)"


def _blocked_by(c, r, free, region_ends=None, region_holders=None):
    """'<shape> row <id> needs <busy>: held by <holder> until <end>' for the first option of c covering region r."""
    o = next((o for o in c["options"] if r in o), set())
    miss = set(o) - set(free)
    head = f"{c.get('shape') or c['kind']} row {c['id']} (rank {float(c['rank']):g})"
    if not miss:
        return head + " fits its regions but is held by its own constraint"
    def owner(t):
        h = (region_holders or {}).get(t)
        if h is None:
            h = next(((region_holders or {}).get(q) for q in QUARTERS if t in expand({q}) and (region_holders or {}).get(q)), None)
        return h
    holders = sorted({str(owner(t)) for t in miss if owner(t)})
    ends = [float(e) for e in ((region_ends or {}).get(t) for t in miss) if e]
    msg = f"{head} needs {','.join(compress(miss))}"
    if holders:
        msg += f": held by {','.join(holders)}"
    if ends:
        msg += f" until {dt.datetime.fromtimestamp(max(ends), dt.timezone.utc):%H:%MZ}"
    return msg


plan.last_drain = None
plan.drain_held = []
plan.drain_lowbusy = []
plan.no_reserve = []
plan.drain_deferred = []
_DRAIN_DEFERRED_LOGGED = {}   # {row id: S} last logged DRAIN-DEFERRED state (keeper process lifetime)
plan.caps = []
plan.hard_end = {}
plan.build_held = []
plan.idle_entries = {}
plan.build_held_rows = []


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
            un0 = lineage_unpark_at(flags, lineage_of(rid, allrows), allrows)
            return lineage_of(rid, allrows), sum(len(counted_fails(flags, x, un0)) for x in chain)
        sup = d.get("supersedes")
        cur = sup[0] if isinstance(sup, list) and sup else sup if isinstance(sup, str) else None
    lin = lineage_of(rid, allrows)
    reset = 0
    n = 0
    un = lineage_unpark_at(flags, lin, allrows)
    for other, d in allrows.items():
        if lineage_of(other, allrows) != lin:
            continue
        reset = max(reset, int(d.get("lineage_reset") or 0))
        n += len(counted_fails(flags, other, un))
    # ids whose manifest is gone but whose dryrun dir remains still count
    for dd in glob.glob(os.path.join(flags, "dryrun", "*")):
        oid = os.path.basename(dd)
        if oid not in allrows and id_stem(oid) == lin:
            n += len(counted_fails(flags, oid, un))
    return lin, max(0, n - reset)


RUN_DIRECT = os.path.join(_HERE, "run_direct.sh")


RUNNABLE_STATES = ("grantable", "armed")
GPU_QUEUED_STATES = RUNNABLE_STATES + ("needs-dryrun", "dryrun-running")   # GPU-Q3-GUARD: a GPU row still to run


def runnable(st):
    """THE one candidate predicate (pipeline audit 2026-11-10 #2): may the planner place this row, and may a region it fits
    be reported as "fits but was not placed"? `st` is status()'s dict. Parked (precond refusal or MAX_FAILS arming/launch
    failures), failed, stopped, done, running and unpublished rows are never runnable. Every consumer (allocate's
    candidate list, the same-tick re-plan, the in-tick and the persisted IDLE-VIOLATION) asks this one predicate."""
    st = st or {}
    return (st.get("state") in RUNNABLE_STATES and not st.get("precond_parked")
            and int(st.get("arm_fails") or 0) < MAX_FAILS)


def next_action(st, flags, rid):
    """DETERMINISTIC one-line next action per state (2026-11-03: an agent reads it, never infers it)."""
    rp = ready_path(flags, rid)
    s = st["state"]
    if s == "done" and resumable_stopped(flags, rid)[1] is None:
        return f"resume (rowflow.py resume {rid})"
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
                if GPU in held:
                    # a GPU-token grant is judged by the device only - its CPU regions (MI210 host
                    # threads / q3 cores) read low by design; idle = the keeper's persisted GPU_IDLE_SAMPLES-sample verdict
                    n = int((load_json(gpu_idle_state_path(flags)) or {}).get(rid) or 0)
                    idle = [GPU] if n >= GPU_IDLE_SAMPLES else []
                else:
                    idle = hostutil.idle_regions(util, held)
                if idle and rid in diskpause.stopped_ids(flags):
                    st["blocker"] = f"DISK-PAUSED (self): {rid} SIGSTOPped by the disk-pause guard until free disk is back above the resume level"
                elif idle and st.get("grant_age_s", 0) > IDLE_HELD_AFTER_S:
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
        pk = precond_park(flags, rid, cur, p)   # BEFORE the armed branch - a live poller whose
        if pk:                                  # precond keeps refusing was re-admitted (and re-FAILed) every tick
            out.update(state="parked", precond_parked=True, arm_fails=len(arm_fails_since_pass(flags, rid, p)),
                       reason=f"precond-cmd refused at {pk.get('at')} ({str(pk.get('reason'))[:160]}); terminal for this "
                              f"launcher+spec: retried only after a launcher/spec edit or `rowflow.py unpark {rid}`",
                       fail_file=pk["fail_file"], fix_task=pk.get("fix_task")); return out
        # pipeline audit 2026-11-10 #2: the MAX_FAILS park is checked BEFORE the armed branch, like the precond park.
        # akx-lb3-2-cv6-pair-20261107-r2 kept a live poller after its 3rd rc=13 refusal, read "armed", and was re-planned
        # (RE-PLAN 37, IDLE-VIOLATION 36) for 3.5 h with its arm-fail count climbing past the park threshold.
        af = arm_fails_since_pass(flags, rid, p)
        out["arm_fails"] = len(af)
        if len(af) >= MAX_FAILS:   # ws58 2026-11-03: a PASS no longer keeps a row that cannot be armed grantable
            out.update(state="parked", reason=f"{len(af)} consecutive arming/launch failures since the PASS of {p.get('passed_at')} "
                                              f"(last: {str(af[-1].get('reason'))[:160]}); operator-escalations/{rid}.arming.md",
                       fail_file=af[-1]["fail_file"], fix_task=af[-1].get("fix_task")); return out
        a = load_json(armed_path(flags, rid))
        if a and alive(a.get("pid")):
            if armed_engine_ok(a.get("pid"), rid):
                out.update(state="armed", reason=f"poller pid {a['pid']} on {a.get('queue')} regions={a.get('regions')}", regions=a.get("regions")); return out
            out["rearm"] = f"ARMED pid {a['pid']} runs no filler_run*.sh engine for this row; re-armed on the next tick"
        out.update(state="grantable", reason=f"dry run passed {p.get('passed_at')} ({p.get('units')} unit(s) in {p.get('result_path')})"); return out
    if nf >= MAX_FAILS and not fresh_attempt(flags, rid, allrows, cur):
        out.update(state="parked", reason=f"{nf} failed dry runs in lineage {lin}; operator-escalations/{lin}.md "
                                          f"(owner: `rowflow.py unpark {lin}`, or republish with a changed launcher/job for one fresh attempt)"); return out
    if last_fail and last_fail.get("launcher_sha256") == cur and last_fail.get("row_sha256", row_sha(flags, rid)) == row_sha(flags, rid) \
            and (last_fail.get("job_sha256") is None or last_fail.get("job_sha256") == job_sha(lp)):
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


RESIDENCY_FLOOR_B = 64 << 20
SMOKE_RESIDENCY_FILE = "residency.json"   # no longer read (audit #1: cgroup attribution); publish_row preflight still exports it
GPU_SAMPLE_S = 0.15          # short GPU jobs (ATT ~0.5 s) fall between 1 s samples; ~10% of a core, harness only, smokes only


_CGROUP_CID = re.compile(r"(?:docker-|/docker/)([0-9a-f]{64})(?:\.scope)?\s*$", re.M)
DOCKER_ROW_LABEL = "epyc.filler.row"   # stamped by filler_run15's docker shim on every `docker run|create` of the row


def cgroup_container_id(text):
    m = _CGROUP_CID.search(text or "")
    return m.group(1) if m else None


def pid_container_id(pid):
    """Container id of a host pid from its cgroup (the harness shares the host pid namespace), or None."""
    try:
        with open(f"/proc/{int(pid)}/cgroup") as f:
            return cgroup_container_id(f.read())
    except (OSError, ValueError):
        return None


ROWFLOW_CGROUP = "/sys/fs/cgroup/rowflow"   # filler_run15 puts each job in its own leaf <id>@<launcher pid> (audit #1)


def cgroup_row(text):
    """The row id of a /proc/<pid>/cgroup text whose v2 path is /rowflow/<id>@<tag>[/...], else None."""
    for line in (text or "").splitlines():
        if line.startswith("0::/rowflow/"):
            leaf = line[12:].split("/", 1)[0]
            if "@" in leaf:
                return leaf.split("@", 1)[0]
    return None


def pid_cgroup_row(pid):
    try:
        with open(f"/proc/{int(pid)}/cgroup") as f:
            return cgroup_row(f.read())
    except (OSError, ValueError):
        return None


def row_leaf_pids(rid):
    """(has_leaf, pids): the pids in every populated cgroup leaf of row `rid`. has_leaf False = the row's job was started
    by an engine without cgroup placement (pre-deploy grant): callers fall back to the legacy tree attribution."""
    has, pids = False, set()
    for leaf in glob.glob(os.path.join(ROWFLOW_CGROUP, glob.escape(rid) + "@*")):
        try:
            if "populated 1" not in open(os.path.join(leaf, "cgroup.events")).read():
                continue
            has = True
            pids |= {int(x) for x in open(os.path.join(leaf, "cgroup.procs")).read().split()}
        except (OSError, ValueError):
            continue
    return has, pids


def pid_is_rows(pid, rid, legacy):
    """THE answer to "is this host pid row `rid`'s?". A pid in a rowflow leaf belongs to that leaf's row and nothing else:
    inherited by every child regardless of env cleaning, setsid, double fork or reparenting. MIGRATION: only while the row
    has no populated leaf (job started by a pre-cgroup engine), `legacy` = membership of its process tree or FILLER_ID on
    the pid or an ancestor. Delete the legacy branch once no grant predating the engine deploy is live."""
    owner = pid_cgroup_row(pid)
    if owner is not None:
        return owner == rid
    if rid and row_leaf_pids(rid)[0]:
        return False
    return pid in legacy or (bool(rid) and lineage_filler_id(pid) == rid)


_CONTAINER_ROW = {}   # container id -> its DOCKER_ROW_LABEL value ("" = unlabelled); only definite answers are cached


def container_row(cid):
    """The row label of container `cid` ("" when it has none), or None when docker could not answer (not cached)."""
    if cid not in _CONTAINER_ROW:
        lab = docker_row_label(cid)
        if lab is None:
            return None
        if len(_CONTAINER_ROW) > 512:
            _CONTAINER_ROW.clear()
        _CONTAINER_ROW[cid] = lab
    return _CONTAINER_ROW[cid]


def row_container_pids(rid, cand):
    """The pids of `cand` that run inside a container labelled DOCKER_ROW_LABEL=<rid>. A container's processes are children
    of containerd-shim, never of the job (vllm-aiter-gfx90a-gpu-20261111-r3: its own vLLM pid read FOREIGN and the row was
    marked CONTAMINATED). The label is stamped by filler_run15's docker shim; an unlabelled or other-row container stays foreign."""
    out = set()
    for q in cand or ():
        cid = pid_container_id(q)
        if cid and container_row(cid) == rid:
            out.add(q)
    return out


def own_pids(flags, g, cand=()):
    """Every pid of grant `g`'s row: its cgroup leaves; for a pre-cgroup grant, the grant's and ARMED pid's trees. Plus
    the pids of `cand` (pass the KFD clients) that sit in a container carrying this row's docker label."""
    has, pids = row_leaf_pids(g["id"])
    if not has:
        for x in (g.get("pid"), (load_json(armed_path(flags, g["id"])) or {}).get("pid")):
            if str(x or "").isdigit():
                pids |= tree_pids(int(x)) | {int(x)}
    rest = [q for q in (cand or ()) if q not in pids]
    return pids | row_container_pids(g["id"], rest) if rest else pids


def pid_filler_id(pid):   # legacy attribution only (pid_is_rows)
    try:
        with open(f"/proc/{int(pid)}/environ", "rb") as f:
            for item in f.read().split(b"\0"):
                if item.startswith(b"FILLER_ID="):
                    return item[10:].decode("utf-8", "replace")
    except (OSError, ValueError):
        pass
    return None


def lineage_filler_id(pid, depth=16):   # legacy attribution only (pid_is_rows)
    for _ in range(depth):
        fid = pid_filler_id(pid)
        if fid is not None:
            return fid
        st = _proc_stat(pid)
        if not st or st[0] <= 1:
            return None
        pid = st[0]
    return None


def docker_row_label(cid):
    """The row label of a container, or None when unreadable. Asked once per container while it still exists."""
    try:
        r = subprocess.run([os.environ.get("FILLER_DOCKER_BIN") or "docker", "inspect", "--format",
                            '{{index .Config.Labels "' + DOCKER_ROW_LABEL + '"}}', cid], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def sample_gpu_residency(root, tracked, own, rid=None, containers=None):
    """One sample: refresh the smoke's process tree, and keep the peak KFD VRAM of each client that is this row's
    (pid_is_rows), or a process in a container carrying this row's label (a docker client's job is not its descendant). Foreign
    clients and device-wide VRAM never count: the idle device reads about 13 MB and another row's model is not this row's proof."""
    harness_tree(root, tracked)
    for q, b in (gpu_occupancy().get("pids") or {}).items():
        mine = pid_is_rows(q, rid, tracked)
        if not mine and rid and containers is not None:   # a container's processes sit in docker's cgroup, not the row's leaf
            cid = pid_container_id(q)
            if cid:
                if cid not in containers:
                    containers[cid] = docker_row_label(cid) == rid
                mine = containers[cid]
        if mine:
            own[q] = max(own.get(q, 0), b)


def gpu_sample_window(root, tracked, own, n=6, interval=GPU_SAMPLE_S, rid=None, containers=None):
    """About one second of fast residency samples (replaces the harness loop's 1 s sleep on a GPU smoke)."""
    for _ in range(n):
        time.sleep(interval)
        sample_gpu_residency(root, tracked, own, rid, containers)


def own_vram_peak(own):
    return max(own.values(), default=0)


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
    seen = {root}   # keeper 2026-11-10: re-walk already-tracked pids too, so a child a tracked parent starts LATER (a GPU
    while todo:     # server two levels down) joins the tree; bounded by the one /proc scan above, `seen` stops pid cycles
        for c, birth in kids.get(todo.pop(), []):
            if c in seen:
                continue
            seen.add(c)
            if tracked.setdefault(c, birth) == birth:   # a reused pid (different starttime) is not walked through
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


def busy_flag(declared, measured, gpu=False):
    """OVER-DECLARED busy_fraction line, or None. Never for a row that holds the GPU token - its CPU share is LOW by
    design (the device does the work); the dry run judges such a row by VRAM residency / the rc78 vacuous-fence test."""
    if gpu:
        return None
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


AKLOOP_DIRS = (os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "akloop"),
               "/mnt/raid0/llm/views/epyc-root-main/scripts/coordination/akloop",
               "/workspace/scripts/coordination/akloop")


def is_ak_row(rid, d):
    """An AutoKernel row: an akloop chain row (akc-*) or any row the autokernel session owns."""
    return str(rid).startswith("akc-") or str((d or {}).get("owner") or "") == "autokernel" \
        or str((d or {}).get("family") or "").startswith("akchain-")


def _failclass_mod():
    for p in [os.environ.get("ROWFLOW_AKLOOP_DIR")] + list(AKLOOP_DIRS):
        if p and os.path.isfile(os.path.join(p, "failclass.py")):
            if p not in sys.path:
                sys.path.insert(0, p)
            import failclass  # noqa: PLC0415
            return failclass
    return None


def ak_failclass(flags, rid, d, rec):
    """AKPL-P3/P5: classify an AK row's FAIL record (AK-FAILRULE-1 rules, akloop/failclass.py) and route a harness
    failure to the pipeline inbox (notify, owner pipeline-mgmt), so it never costs the AK owner a turn. Returns the
    classification dict or None (not an AK row / classifier unavailable). Never raises."""
    if not is_ak_row(rid, d):
        return None
    try:
        fc = _failclass_mod()
        if fc is None:
            return None
        c = fc.classify_fail(dict(rec, id=rid), "\n".join(rec.get("launcher_out_tail") or []))
        out = c.to_dict()
        if c.side == "harness":
            out["routed"] = bool(fc.route(c, flags, notify_mod=notify, rid=rid))
        return out
    except Exception as e:  # noqa: BLE001 - classification never blocks the FAIL record
        return {"side": "unknown", "error": f"{type(e).__name__}: {e}"}


def record_fail(flags, rid, d, reason, extra):
    n = len(fail_paths(flags, rid)) + 1
    rec = {"id": rid, "at": now_iso(), "launcher_sha256": sha256(d["launcher"]["path"]) if os.path.isfile(d["launcher"]["path"]) else None,
           "job_sha256": job_sha(d["launcher"]["path"]) if os.path.isfile(d["launcher"]["path"]) else None,
           "row_sha256": row_sha(flags, rid), "rowflow_sha256": sha256(__file__), "reason": reason, "launcher_out_tail": tail(os.path.join(dry_dir(flags, rid), "launcher.out")),
           "fix_task": f"fix dry-run failure of {rid}: {reason} (see compute-flags/dryrun/{rid}/launcher.out; the keeper retries as soon as the launcher file changes)",
           **extra}
    fc = ak_failclass(flags, rid, d, rec)
    if fc is not None:
        rec["failclass"] = fc
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
    if _PRECOND_REFUSED in reason:   # terminal at the first refusal: one record, one alert
        park = (f"the row is PARKED now (precond refusal is terminal for this launcher+spec): fix the precondition, then "
                f"republish or `rowflow.py unpark {rid}`")
    else:
        park = f"after {MAX_FAILS} in a row the row is parked until it is republished"
    record_fail(flags, rid, d, reason, {"kind": kind, "launcher_out_tail": tail(pol), "tail_of": pol,
                                        "fix_task": f"fix the {kind} failure of {rid}: {reason} (see compute-flags/dryrun/{rid}/poller.out); {park}"})
    af = arm_fails_since_pass(flags, rid)
    if len(af) < MAX_FAILS:
        return len(af)
    out = os.path.join(flags, "operator-escalations", rid + ".arming.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    L = [f"# PARKED NEEDS-OWNER - row `{rid}` ({len(af)} consecutive arming/launch failures since its PASS; written {now_iso()} by rowflow)", "",
         "The row passed its dry run but its poller cannot be armed or launched, so the allocator no longer grants it "
         "(a PASS alone used to keep it grantable forever). Last failures:", ""]
    L += [f"- {f.get('at')} [{f.get('kind') or 'arm'}] {str(f.get('reason'))[:300]}" for f in af[-5:]]
    L += ["", "Poller output tail:", "", "```"] + [str(x) for x in (af[-1].get("launcher_out_tail") or [])[-15:]] + ["```", "",
          "Options (all owner-level): 1. fix the launcher and republish (a new PASS clears the count); "
          f"2. `rowflow.py unpark {rid}`; 3. drop (remove ready/<id>.json).", ""]
    with open(out, "w") as f:
        f.write("\n".join(L))
    if len(af) == MAX_FAILS:
        log(f"PARK {rid}: {len(af)} consecutive {kind} failures since its PASS; operator-escalations/{rid}.arming.md")
    return len(af)


def escalation_tag(options):
    """NEEDS-OWNER when every listed option is owner-level; NEEDS-OPERATOR only when an operator-only action is listed.
    options: [(text, operator_only)]."""
    return "NEEDS-OPERATOR" if any(op for _, op in options) else "NEEDS-OWNER"


def write_escalation(flags, rid, allrows):
    lin, nf = lineage_fails(flags, rid, allrows)
    if nf < MAX_FAILS:
        return
    out = os.path.join(flags, "operator-escalations", lin + ".md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    opts = [("fix and re-admit under a new id with `lineage_reset: %d` in the spec" % nf, False),
            ("`python3 rowflow.py unpark %s` (the owner may; earlier failed dry runs stop counting)" % lin, False),
            ("republish with a changed launcher or job: ONE fresh attempt, no new id needed", False),
            ("re-scope under a new `lineage`", False), ("drop (remove ready/<id>.json)", False)]
    L = [f"# PARKED {escalation_tag(opts)} - lineage `{lin}` ({nf} failed dry runs; written {now_iso()} by rowflow)", "",
         "Nobody retries this lineage. Each failure below is the owner's recorded fix task.", ""]
    for other, d in sorted(allrows.items()):
        if lineage_of(other, allrows) != lin:
            continue
        for fp in fail_paths(flags, other):
            f = load_json(fp) or {}
            L.append(f"- {f.get('at')} **{other}**: {str(f.get('reason'))[:300]}")
    L += ["", "Options: " + "; ".join(f"{i}. {t}" for i, (t, _) in enumerate(opts, 1)) + ".", ""]
    with open(out, "w") as f:
        f.write("\n".join(L))


def dryrun_window(d, timeout):
    """The smoke's own grant length: its first-progress deadline + the stop grace. This is the smoke's DEADLINE, not a
    booking (admission never reads it; a live smoke counts SMOKE_HOLD_S); it is floored at min_window_s + 300 only
    because grant_ok_launcher refuses any grant shorter than the launcher's --min-window + MARGIN_S."""
    return max(int(d.get("min_window_s") or 0) + 300, int(timeout) + STOP_GRACE_S + 300)


def dryrun_grant_holds(regions):
    """a dry-run grant books the EXACT core + SMT-sibling tokens of its regions; a whole
    quarter only when the regions name one (a 4-core smoke on 4-7 holds c4-c7,t100-t103, never q0)."""
    regs = str(regions or "")
    if "mi210" in regs:   # GPU dry runs keep their existing holds (out of this hotfix's scope)
        return quarters_of(regs) | {GPU}
    gpu = set()
    cpu = ",".join(t for t in regs.split(",") if t.strip() and not t.strip().startswith("mi210"))
    toks = expand(cpu_tokens(ws58_cpus(cpu), gpu_threads=True)) if cpu else set()   # a pocket smoke holds threads only
    whole = {q for q in QUARTERS if expand({q}) - {q} <= toks | {q}} if toks else set()
    return (toks - expand(whole)) | whole | gpu


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
# keeper-smoke-complete-fn 2026-11-10: a stock interpreter binary named on --cmd/--complete-cmd (`/usr/bin/python3 -B
# job.py`) is not the job's code: it is >2 MiB, so it read as "too large to scan" and every python-launched job scored
# job_complete=false (c6-native-residency-20261109-r3, c6-26-corpus-repin-20261109-r3). The SCRIPT it runs is still
# scanned (referenced_paths yields it). Exempt only a root-owned, non-group/other-writable regular file under a system
# bin dir whose basename is a known interpreter; any other oversized file (a custom binary) still counts as branching.
SMOKE_SYSTEM_BIN_DIRS = ("/usr/bin/", "/bin/", "/usr/local/bin/", "/usr/sbin/", "/sbin/")
SMOKE_INTERPRETER_RE = re.compile(r"(?:python[0-9.]*|bash|sh|dash|perl[0-9.]*|env|timeout|numactl|taskset|nice)")


def smoke_trusted_interpreter(path):
    """True iff `path` (followed through symlinks) is a stock system interpreter/wrapper binary, not row-owned code."""
    import stat as _stat
    rp = os.path.realpath(path)
    names = {os.path.basename(path), os.path.basename(rp)}
    if not any(SMOKE_INTERPRETER_RE.fullmatch(n) for n in names) or not rp.startswith(SMOKE_SYSTEM_BIN_DIRS):
        return False
    try:
        st = os.stat(rp)
    except OSError:
        return False
    return _stat.S_ISREG(st.st_mode) and st.st_uid == 0 and not st.st_mode & (_stat.S_IWGRP | _stat.S_IWOTH)


def smoke_scan_files(d):
    """The files smoke_branch_files scans: the row's launcher and every regular file its engine line runs (--cmd /
    --complete-cmd tokens), minus the engine and stock system interpreters. Raises when the launcher does not parse.
    publish_row's preflight scans the same set for environment cleaning (pipeline audit 2026-11-10 #4)."""
    lp = d["launcher"]["path"]
    o = parse_launcher(lp)
    eng = os.path.realpath(o["engine"])
    out, seen = [], set()
    for f in [lp] + [x for x in referenced_paths({"cmd": o["cmd"], "complete_cmd": o["complete_cmd"]}) if os.path.isfile(x)]:
        rp = os.path.realpath(f)
        if rp in seen or rp == eng or (f != lp and smoke_trusted_interpreter(f)):
            continue
        seen.add(rp)
        out.append(f)
    return out


def smoke_branch_files(d):
    """The row's own launcher and every regular file its engine line runs (--cmd / --complete-cmd tokens) that names
    FILLER_SMOKE* or FILLER_DRYRUN*: a job that branches on them does something else under a smoke than in its grant.
    The engine itself (which honours them by design) and stock system interpreters (smoke_trusted_interpreter) are not
    scanned; the scripts they run are. An unreadable or oversized file otherwise counts as branching."""
    lp = d["launcher"]["path"]
    try:
        files = smoke_scan_files(d)
    except (Refused, OSError, StopIteration, ValueError) as e:
        return [f"{lp} (unparsable: {e})"]
    hits = []
    for f in files:
        rp = os.path.realpath(f)
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


def smoke_units_capped(d, smoke_s):
    """True when the smoke ran with FILLER_SMOKE_UNITS=1 (dryrun_run sets it unless the row has a smoke_predicate): the
    job was shrunk, so whatever it wrote (e.g. the file a --complete-cmd tests) is the smoke's, not the full job's."""
    return bool(smoke_s) and not (d or {}).get("smoke_predicate")


def smoke_completion_check(d, units_capped=False, units=None):
    """Operator 2026-11-02 (ws58): a smoke/dry-run PASS may file a row COMPLETE only when (1) the launcher has no smoke
    branch (no FILLER_SMOKE*/FILLER_DRYRUN* in it or in the files its --cmd/--complete-cmd run), (2) the result is not a
    dry-run-native isolated result, and (3) the engine's --complete-cmd, re-run in --workdir with every FILLER_SMOKE*/
    FILLER_DRYRUN* variable removed, passes on the artifacts the full job writes. Returns (ok, reason)."""
    if d.get("dryrun_native_result"):
        return False, "dryrun_native_result: the smoke wrote an isolated per-attempt result, not the full job's artifacts"
    # ROWFLOW-SMOKE-COMPLETE-GENERAL: a unit-capped smoke writes the very artifact the --complete-cmd tests, so the
    # predicate passing proves nothing. Only a smoke that actually reached the declared total_units may be the job.
    if units_capped:
        tu = d.get("total_units")
        if not (tu and units is not None and int(units) >= int(tu)):
            return False, "smoke ran unit-capped (FILLER_SMOKE_UNITS=1) and did not reach total_units: a smoke is not the job"
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


def gpu_residency_required(d, regions):
    """A dry run must prove VRAM residency iff the row holds the MI210 AND executes on it. A row that declares
    gpu_use "quiet-only" (validated at publish: --class cpu+gpu --gpu-quiet exclusive) holds the GPU only to keep it
    idle; demanding residency from it failed every such CPU census (inf75-c5-w3-halfb-census-c6-20261105, 2026-11-05)."""
    return "mi210_0" in regions and (d or {}).get("gpu_use") != "quiet-only"


def smoke_measure_paths(d, dry_dir_path):
    return [os.path.join(dry_dir_path, "smoke_measure.json"),
            os.path.join(str(d.get("scratch_root") or ""), "out-smoke", "smoke_measure.json")]


def smoke_measure_stamp(path):
    try:
        st = os.stat(path)
        return (st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
    except OSError:
        return None


def fresh_smoke_measure(d, dry_dir_path, before):
    """Accept a valid measurement created or changed after the pre-launch snapshot."""
    for path in smoke_measure_paths(d, dry_dir_path):
        try:
            stamp = smoke_measure_stamp(path)
            if stamp is None or stamp == before.get(path):
                continue
            m = load_json(path)
            if not m:
                continue
            unit_s, loads_s = float(m["unit_s"]), float(m["loads_s"])
            if not math.isfinite(unit_s) or unit_s <= 0 or int(m["units_measured"]) < 1 or not math.isfinite(loads_s) or loads_s < 0:
                continue
            return path
        except (OSError, KeyError, TypeError, ValueError, OverflowError):
            continue
    return None


SMOKE_LOCK_NAME = "SMOKE.lock"   # F2 (AK audit B2, D9 2026-11-20): one smoke runner per row id


def smoke_lock_path(flags, rid): return os.path.join(dry_dir(flags, rid), SMOKE_LOCK_NAME)


def smoke_lock_holder(flags, rid):
    """'pid N (who) since T' from the pid sidecar the live holder writes into dryrun/<id>/SMOKE.lock, else None. Reads
    only (review S3: a probe never takes the flock, so it cannot make a real runner see a busy lock); the holder clears
    the sidecar before releasing, and a dead pid never counts."""
    d = load_json(smoke_lock_path(flags, rid)) or {}
    if d.get("pid") and proc_alive(d["pid"]):
        return f"pid {d['pid']} ({d.get('who', '?')}) since {d.get('at', '?')}"
    return None


def _verdict_since(flags, rid, t0):
    """(verdict, msg) recorded at or after epoch t0 (PASS.json, else the newest FAIL-*.json), else None."""
    pp = pass_path(flags, rid)
    cands = [(os.path.getmtime(pp), "PASS", pp)] if os.path.exists(pp) else []
    cands += [(os.path.getmtime(f), "FAIL", f) for f in fail_paths(flags, rid)]
    cands = [c for c in cands if c[0] >= t0 - 1]
    if not cands:
        return None
    _, v, path = max(cands)
    rec = load_json(path) or {}
    return v, f"recorded by the concurrent smoke: {rec.get('reason') or os.path.basename(path)}"


def dryrun_run(flags, rid, regions, one_quarter=False, smoke_s=None, wait_s=None, log=print):
    """F2: dryrun_run under a per-id flock on dryrun/<id>/SMOKE.lock (allocator batch, --smoke-now, gpu-batch, publish all
    reach here). A second caller blocks <= wait_s (default: the smoke's own timeout + grace), says who holds it, then returns
    the verdict that smoke recorded instead of running the smoke again; WAIT ("not run twice") when the holder outlives
    the wait - wait_s=0 (the publish path) refuses at once instead of blocking the owner's turn.
    Harmless duplicate: a caller that arrives AFTER the first smoke released the lock and whose state is still
    needs-dryrun (e.g. the first one WAITed) runs its own smoke; it is serialized, never concurrent."""
    dd = dry_dir(flags, rid)
    os.makedirs(dd, exist_ok=True)
    fd = os.open(smoke_lock_path(flags, rid), os.O_RDWR | os.O_CREAT, 0o664)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            who = smoke_lock_holder(flags, rid) or "another runner"
            log(f"smoke in progress by {who}, waiting ({rid})")
            t0 = time.time()
            limit = wait_s if wait_s is not None else int(smoke_s or FIRST_PROGRESS_S) + DRYRUN_DEADLINE_GRACE_S
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.time() - t0 >= limit:
                        return "WAIT", f"smoke of {rid} still in progress by {who} after {int(limit)}s; not run twice"
                    time.sleep(1)
            got = _verdict_since(flags, rid, t0)
            if got:
                return got
        os.ftruncate(fd, 0)
        os.pwrite(fd, json.dumps({"pid": os.getpid(), "who": " ".join(sys.argv[:3])[:120], "at": now_iso()}).encode(), 0)
        try:
            return _dryrun_run_locked(flags, rid, regions, one_quarter=one_quarter, smoke_s=smoke_s)
        finally:
            os.ftruncate(fd, 0)   # clear the pid sidecar before the flock goes
    finally:
        os.close(fd)   # closing releases the flock


def _dryrun_run_locked(flags, rid, regions, one_quarter=False, smoke_s=None):
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
    window = dryrun_window(d, timeout)
    start = dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0) - dt.timedelta(minutes=1)
    end = start + dt.timedelta(seconds=window)
    for stale in ("stop", "ended", "complete", "SMOKE-EXITED.json"):
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
               WS58_REGIONS=ws58_cpus(regions), **({"FILLER_SMOKE": "1", "FILLER_DISK_FLOOR_GIB": "20",
                                                                  **({} if d.get("smoke_predicate") else {"FILLER_SMOKE_UNITS": "1"})} if smoke_s else {}))  # a smoke writes little: only a near-full disk stops it  # ws58 2026-11-01: launchers written for the v8 keeper read it
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
        f.write(dryrun_grant_text(rid, d.get("admission_class"), regions, dryrun_grant_holds(regions), start, end))
    out = open(os.path.join(dd, "launcher.out"), "a")
    out.write(f"\n==== dry run {now_iso()} regions={regions} launcher_sha={lsha} units_before={units0}\n"); out.flush()
    lout = os.path.join(dd, "launcher.out")
    out_lines0 = len(tail(lout, 10**6))  # counted BEFORE the launch: a region-lock line the job prints at once is this run's
    measure_before = {p: smoke_measure_stamp(p) for p in smoke_measure_paths(d, dd)}
    p = subprocess.Popen(["bash", lp], cwd=flags, env=env, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
    tracked = harness_tree(p.pid, {p.pid: (_proc_stat(p.pid) or (0, 0, None))[2]})  # setsid'd group: pgid == p.pid
    # the dry-run grant's end= is a HARD deadline, carried in RUNNING.json so the keeper
    # (reconcile_dryruns) enforces it even when this harness is gone
    deadline = end.strftime("%Y-%m-%dT%H:%M:%SZ")
    atomic_json(running_path(flags, rid), {"pid": p.pid, "pgid": p.pid, "started": now_iso(), "regions": regions, "launcher_sha256": lsha,
                                           "grant": grant, "deadline": deadline, "harness_pid": os.getpid()})
    t0 = time.time()
    t_lock = None
    cpu_acc, cpu_samples = {}, []
    vram_max = None
    kfd_seen = {}
    gpu_containers = {}
    gpu = gpu_residency_required(d, regions) or d.get("lane") == "gpu"

    def residency_ok():
        nonlocal vram_max
        vram_max = own_vram_peak(kfd_seen) or vram_max
        return bool(kfd_seen)
    first_unit_at = None
    progress = None
    stop_requested = None
    warning = None
    ended = os.path.join(dd, "ended")
    verdict, reason = None, None
    try:
        while True:
            for _ in range(5):
                if gpu:   # sampled at GPU_SAMPLE_S (was 1 s: codex-att-r4d held 4.5 GB for ~2 s, unseen behind a slow rocm-smi call)
                    gpu_sample_window(p.pid, tracked, kfd_seen, rid=rid, containers=gpu_containers)
                else:
                    time.sleep(1)
                    harness_tree(p.pid, tracked)
            cpu_samples.append((time.time(), tree_cpu_s(tracked, cpu_acc)))
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
                elif gpu and not residency_ok():
                    verdict, reason = "FAIL", f"GPU row produced a unit but no owned KFD process or VRAM was observed during the run (max {vram_max} B)"
                else:
                    verdict, reason = "PASS", f"first progress: {progress}; {rc_line[:80]}"
                break
            if stop_requested and time.time() - stop_requested > STOP_GRACE_S:
                # the engine's hard-end kill is production's truncation path too: PASS with a warning, then stop the group
                warning = f"job did not stop within {STOP_GRACE_S}s of the stop file (FILLER_STOPFILE not honoured between items); truncated by signal"
                if gpu and not residency_ok():
                    verdict, reason = "FAIL", f"GPU row produced a unit but no owned KFD process or VRAM was observed during the run (max {vram_max} B)"
                else:
                    verdict, reason = "PASS", f"first progress: {progress}; {warning}"
                break
            if time.time() >= end.timestamp() and verdict is None:
                # the grant's end is a hard deadline; never-started = WAIT (bounded), started = FAIL
                verdict, reason = (("WAIT", f"deadline: the engine never reached START before the dry-run grant end {deadline}; "
                                            "requeued (bounded retry)") if t_lock is None else
                                   ("FAIL", f"deadline: dry-run grant end {deadline} passed after engine START without a clean stop"))
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
        record_smoke_exit(flags, rid, p.pid, tracked, surv)
        if verdict == "FAIL" and one_quarter and (not reason.startswith("no first progress") or "never reached START" in reason):
            reason += (f" [dry run held ONE quarter, WS58_REGIONS={ws58_cpus(regions)}; a launcher whose own taskset/claim "
                       "hard-codes a wider cpu list must honour WS58_REGIONS under FILLER_DRYRUN]")
        out.write(f"==== dry run {verdict}: {reason} ({now_iso()})\n"); out.close()
    measure = fresh_smoke_measure(d, dd, measure_before) if verdict == "PASS" and smoke_s else None
    if verdict == "PASS" and smoke_s and not measure:
        verdict, reason = "FAIL", "SMOKE-NO-MEASURE: no valid fresh smoke_measure.json from this smoke"
        with open(os.path.join(dd, "launcher.out"), "a") as log:
            log.write(f"==== dry run FAIL: {reason} ({now_iso()})\n")
    cur_sha = sha256(lp) if os.path.isfile(lp) else None
    if verdict == "PASS" and cur_sha != lsha:
        verdict, reason = "FAIL", "launcher changed while the dry run was running"
    rec = {"regions": regions, "units": count_units(result_path, result_format, d.get("workdir")) - units0, "result_path": result_path,
           "result_format": result_format, "first_unit_at": first_unit_at, "first_progress": progress,
           "first_progress_s": timeout, "progress_rule": probe.kind, "vram_used_max_bytes": vram_max,
           "residency_evidence": {"kfd_pids": sorted(kfd_seen)} if kfd_seen else None, "smoke_measure": measure,
           "engine_sha256": sha256(d["engine"]["path"]) if os.path.isfile(d["engine"]["path"]) else None,
           "ended": head1(ended) or None, "warning": warning, "dryrun_log": os.path.join(dd, "launcher.out"), "elapsed_s": int(time.time() - t0)}
    # refinement 1: what the job actually used (before the harness's stop), against the row's declared claim
    claimed = claimed_cpus(d.get("regions"), (parse_launcher(lp) if os.path.isfile(lp) else {}).get("claim_cpus"), str(d.get("shape") or "quarter"))
    mt, mb = measured_busy(cpu_samples, claimed, until=stop_requested)
    rec.update(measured_threads=mt, measured_busy_fraction=mb, measured_claimed_cpus=claimed)
    flag = busy_flag(row_busy(d), mb, gpu=GPU in holds or gpu_declared(d))   # GPU-token rows are never OVER-DECLARED by CPU %
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
        rec["smoke_units_capped"] = smoke_units_capped(d, smoke_s)
        ok, why = smoke_completion_check(d, rec["smoke_units_capped"], rec.get("units"))
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
def _engine_sha(d):
    try:
        return sha256(_opts(d).get("engine") or d["engine"]["path"])
    except (OSError, KeyError, TypeError):
        return None


# no-hold deploys (operator 2026-11-07): arm_one snapshots the engine set into the row's own dir and the poller runs only
# that copy, so deploy_rowflow refuses an engine swap only under LEGACY grants (grant_reads_live_engine).
ENGINE_SET = ("filler_lib.sh", "notify.py", "diskpause.py", "loop_metrics_hook.sh")   # re-read by a running poller/launcher
ENGINE_REREAD = ("filler_run15.sh",) + ENGINE_SET   # a deploy that changes one of these touches running legacy pollers


def engine_snapshot_dir(flags, rid):
    return os.path.join(dry_dir(flags, rid), "engine")


def snapshot_engine(flags, rid, engine):
    """Copy the row's engine and ENGINE_SET (from the engine's directory) into <flags>/dryrun/<id>/engine/ (read-only,
    sha256 recorded in ENGINE.json). Written to a temp dir and renamed, so a poller never sees a half-copied set; an
    earlier snapshot is replaced (a re-arm takes the engine that is live NOW). Returns (dir, ENGINE.json record)."""
    src = os.path.dirname(os.path.realpath(engine))
    dst = engine_snapshot_dir(flags, rid)
    tmp = f"{dst}.part-{os.getpid()}"
    if os.path.lexists(tmp):
        _rmtree_ro(tmp)
    os.makedirs(tmp)
    files = {}
    for name in (os.path.basename(engine),) + ENGINE_SET:
        sp = os.path.join(src, name)
        if not os.path.isfile(sp) and name != os.path.basename(engine):
            sp = os.path.join(_HERE, name)   # an engine published in a row snapshot dir: helpers come from the keeper's dir
        if not os.path.isfile(sp):
            continue
        dp = os.path.join(tmp, name)
        shutil.copyfile(sp, dp)
        os.chmod(dp, 0o555)
        files[name] = sha256(dp)
    rec = {"id": rid, "source_dir": src, "engine": os.path.basename(engine), "files": files, "taken_at": now_iso()}
    with open(os.path.join(tmp, "ENGINE.json"), "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    if os.path.lexists(dst):
        _rmtree_ro(dst)
    os.rename(tmp, dst)
    return dst, rec


def grant_reads_live_engine(flags, rid, proc="/proc"):
    """True when the open grant's poller may still re-read the LIVE engine set (a legacy row armed before engine snapshots,
    or one whose snapshot is gone): its ARMED.json names no engine_snapshot whose ENGINE.json exists, or the armed pid's
    argv runs an engine outside that snapshot."""
    a = load_json(armed_path(flags, rid)) or {}
    snap = a.get("engine_snapshot")
    if not snap or not os.path.isfile(os.path.join(snap, "ENGINE.json")):
        return True
    pid = a.get("pid")
    try:
        with open(os.path.join(proc, str(int(pid)), "cmdline"), "rb") as f:
            argv = [x.decode("utf8", "replace") for x in f.read().split(b"\0") if x]
    except (OSError, TypeError, ValueError):
        return False   # the poller is gone (nothing re-reads anything) or /proc is unreadable: the snapshot record decides
    eng = next((x for x in argv if ENGINE_RE.search(x)), None)
    return bool(eng) and not os.path.realpath(eng).startswith(os.path.realpath(snap) + "/")


def legacy_open_grants(flags, proc="/proc"):
    """Ids of open grants (grants/<id>.grant without .ended) whose poller still reads the live engine path."""
    out = []
    for g in sorted(glob.glob(os.path.join(flags, "grants", "*.grant"))):
        rid = os.path.basename(g)[:-6]
        if os.path.exists(os.path.join(flags, "grants", rid + ".ended")):
            continue
        if grant_reads_live_engine(flags, rid, proc):
            out.append(rid)
    return out


def deploy_guard(flags, changed, allow_open=False, proc="/proc"):
    """deploy_rowflow.sh step 3: (ok, line). A deploy that changes a file a running poller re-reads (ENGINE_REREAD) is
    refused only while LEGACY grants are open (pollers that still read the live path); snapshot-launched grants run
    their own copy and never block. --allow-open-grants overrides."""
    touched = sorted(set(changed) & set(ENGINE_REREAD))
    if not touched:
        return True, "no engine file changes"
    legacy = legacy_open_grants(flags, proc)
    if not legacy:
        return True, f"{','.join(touched)} change; no open grant reads the live engine (snapshot-launched rows run their own copy)"
    if allow_open:
        return True, f"--allow-open-grants: {len(legacy)} legacy grant(s) read the live engine: {','.join(legacy[:8])}"
    return False, (f"REFUSED: {','.join(touched)} change while {len(legacy)} LEGACY grant(s) still read the live engine path "
                   f"({','.join(legacy[:8])}); retry when they end or pass --allow-open-grants")


HOLD_NAME_RE = re.compile(r"^HOLD_[A-Za-z0-9_-]+$")


def operator_holds(flags):
    """The explicit operator emergency stop: <flags>/HOLD_<NAME> files with an EXACT name (no suffix, no dot) that resolve to
    an existing file. A renamed hold (HOLD_X.lifted-symlink, HOLD_X.disabled, ...) or a dangling link never matches -
    origin 2026-11-07: HOLD_ADMISSIONS.lifted-symlink still matched the HOLD_* glob and idled q2/q3/GPU for hours."""
    out = []
    for p in sorted(glob.glob(os.path.join(flags, "HOLD_*"))):
        n = os.path.basename(p)
        if ".lifted" in n or ".disabled" in n or not HOLD_NAME_RE.match(n) or not os.path.isfile(p):
            continue
        out.append(n)
    return out


def arm_one(flags, rid, d, regions=None, log=print):
    """Start the row's poller (the exact launcher through its engine, polling grants/<id>.grant). Regions are NOT
    resolved here: the grant the allocator writes later carries them."""
    dd = dry_dir(flags, rid)
    os.makedirs(os.path.join(dd, "state"), exist_ok=True)
    say = log if callable(log) else print
    log = os.path.join(dd, "poller.out")
    before = sum(1 for l in tail(log, 100000) if "launcher up pid=" in l)
    env = dict(os.environ, FILLER_POLL="5", FILLER_OWNER=str(d["owner"]), FILLER_EST_WALL_S=str(d["estimate_s"]),
               FILLER_STATE_DIR=os.path.join(dd, "state"), FILLER_FLAGS_DIR=flags, FILLER_GRANTS_DIR=os.path.join(flags, "grants"))
    if regions and ws58_cpus(regions):
        env["WS58_REGIONS"] = ws58_cpus(regions)
    ram_fence_env(d, env)
    for k in ("FILLER_DRYRUN", "FILLER_DRYRUN_DIR", "FILLER_DRYRUN_ONE_QUARTER", "FILLER_ENGINE_SNAPSHOT", "FILLER_ENGINE_HOME"):
        env.pop(k, None)
    snap = None
    try:   # the poller runs ONLY this copy (filler_run15 re-execs it): a later deploy never reaches a running row
        eng = _opts(d).get("engine") or d["engine"]["path"]
        snap, _rec = snapshot_engine(flags, rid, eng)
        env["FILLER_ENGINE_SNAPSHOT"] = snap
    except (OSError, KeyError, TypeError, Refused) as e:
        snap = None
        say(f"ENGINE-SNAPSHOT {rid} failed ({type(e).__name__}: {e}); armed on the live engine (legacy)")
    with open(log, "a") as out:
        out.write(f"\n==== arm {now_iso()}{' engine-snapshot ' + snap if snap else ''}\n")
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
    eng_sha = _engine_sha(d)
    if snap:
        try:
            eng_sha = sha256(os.path.join(snap, os.path.basename(_opts(d).get("engine") or d["engine"]["path"])))
        except (OSError, KeyError, TypeError, Refused):
            pass
    atomic_json(armed_path(flags, rid), {"id": rid, "pid": pid, "regions": d["regions"], "at": now_iso(), "launcher_sha256": sha256(d["launcher"]["path"]),
                                        "engine_sha256": eng_sha, "engine_snapshot": snap})   # the engine code this poller runs (contract lock)
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


def stop_group_bounded(pgid, term_s=1.5, kill_s=0.5):
    """TERM the group, settle, KILL whatever remains (even if the leader already left), settle. True when the tree is gone."""
    for sig, wait in ((signal.SIGTERM, term_s), (signal.SIGKILL, kill_s)):
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            pass
        except PermissionError:
            return False
        end = time.time() + wait
        while time.time() < end:
            if not tree_pids(pgid):
                return True
            time.sleep(0.1)
    return not tree_pids(pgid)


def stop_row_poller(flags, rid, d, pid, log=print, grace=1.5, proc="/proc"):
    """LOOP-11: stop THIS row's waiting poller; returns stopped | gone | not-ours | job | survived. Signals only when: no grant or dry
    run exists for the row (TERM then writes no .ended: the id stays usable), argv proves the pid is this row's engine or
    launcher (a recycled pid is not-ours), its group is the private setsid group arm_one created, and no member or
    descendant is an inner engine or left that session (a launched job always runs under setsid)."""
    if os.path.exists(os.path.join(flags, "grants", rid + ".grant")) or os.path.exists(running_path(flags, rid)):
        return "job"
    gate = _gate()
    try:
        pid = int(pid)
        argv = gate.read_cmdline(proc, pid) or []
        o = gate.parse_engine(argv)
        lp = (d.get("launcher") or {}).get("path")
        if not ((o and not o["inner"] and o["id"] == rid) or (not o and lp and lp in argv)):
            return "not-ours"
        f = open(f"{proc}/{pid}/stat").read().rsplit(")", 1)[1].split()
        pgid, sid = int(f[2]), int(f[3])
        if pgid != sid or pgid <= 1 or pgid == os.getpgid(0):
            return "not-ours"
        for q in tree_pids(pgid):
            try:
                g = open(f"{proc}/{q}/stat").read().rsplit(")", 1)[1].split()
            except (FileNotFoundError, ProcessLookupError):
                continue   # exited mid-scan: neither foreign nor a job
            except (OSError, IndexError):
                return "job"   # unreadable member: hold, never arm beside it
            io = gate.parse_engine(gate.read_cmdline(proc, q) or [])
            if int(g[3]) != sid or (io and io["inner"]):
                return "job"
    except (FileNotFoundError, ProcessLookupError):
        return "gone"
    except (OSError, ValueError, IndexError, TypeError, gate.Refuse):
        return "not-ours"
    if not stop_group_bounded(pgid, term_s=grace):
        log(f"ALERT POLLER-STOP {rid}: group {pgid} survived TERM+KILL")
        return "survived"
    log(f"POLLER-STOP {rid}: pid {pid} group {pgid} stopped")
    return "stopped"


def stop_poller_if_parked(flags, rid, d, pid, line, n, log=print):
    """A refusal that parks the row ends its poller; a transient refusal leaves it waiting. Returns the stop result or None."""
    if _PRECOND_REFUSED in line or n >= MAX_FAILS:
        return stop_row_poller(flags, rid, d, pid, log)
    return None


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


def grant_start(now=None):
    n = dt.datetime.now(dt.timezone.utc) if now is None else dt.datetime.fromtimestamp(now, dt.timezone.utc)
    return n.replace(second=0, microsecond=0) - dt.timedelta(minutes=1)


def capped_window(window_s, end_cap, now=None):
    """The grant window, shortened so a grant written now ends no later than end_cap (minute-floored); None = uncapped."""
    if not end_cap:
        return int(window_s)
    start = grant_start(now).timestamp()
    return max(0, min(int(window_s), int((int(end_cap) // 60) * 60 - start)))


def write_grant(flags, rid, regions, holds, window_s, lock="", end_cap=None):
    start = grant_start()
    end = start + dt.timedelta(seconds=int(window_s))
    if end_cap:   # DRAIN-BY-ESTIMATE: the engine's hard-end kill at end= frees the regions by the drain target
        end = min(end, dt.datetime.fromtimestamp((int(end_cap) // 60) * 60, dt.timezone.utc))
    cpus = grant_cpus(regions)   # ws58 2026-11-02: the exact cpu list (a GRANT_CPUS engine locks + pins a GPU grant to it)
    # Written only when it adds something: for regions that already spell explicit cpus (mi210_0,184-191) the engine's
    # fallback (cpus= else regions) gives the same list, and sealed jobs that parse their grant strictly (inf22 M4:
    # exactly regions/start/end/holds) keep working.
    if cpus == ws58_cpus(regions):
        cpus = ""
    line = (f"regions={regions} start={start:%Y-%m-%dT%H:%MZ} end={end:%Y-%m-%dT%H:%MZ} holds={','.join(compress(holds))}"
            + (f" cpus={cpus}" if cpus else "") + (f" lock={lock}" if lock else "") + "\n")
    p = os.path.join(flags, "grants", rid + ".grant")
    # D9 capcut: the cap stamp is a SIDECAR (grants/.capcut/stamps/<id>.cap), not a grant field - sealed jobs parse
    # their grant strictly. Written only when end_cap actually shortened end=; an uncapped grant clears a stale stamp.
    cap_floor = (int(end_cap) // 60) * 60 if end_cap else None
    if cap_floor is not None and int(end.timestamp()) == cap_floor:
        write_capstamp(flags, rid, cap_floor, f"{end:%Y-%m-%dT%H:%MZ}")
    else:
        clear_capstamp(flags, rid)
    with open(p + ".tmp", "w") as f:
        f.write(line)
    os.replace(p + ".tmp", p)
    return line.strip()


# ---------------------------------------------------------------- D9 capcut requeue (operator: "Requeue same id")
CAPCUT_MAX = 6            # requeues per row per CAPCUT_WINDOW_S; then the row ends normally
CAPCUT_WINDOW_S = 86400
CAPCUT_SLACK_S = 1800     # .ended time may trail the stamped cap by the engine's kill/poll latency (grant already deleted)


def capcut_dir(flags):
    return os.path.join(flags, "grants", ".capcut")


def capstamp_path(flags, rid):
    return os.path.join(capcut_dir(flags), "stamps", rid + ".cap")


def write_capstamp(flags, rid, cap, end_iso):
    p = capstamp_path(flags, rid)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".tmp", "w") as f:
        f.write(f"cap={int(cap)} end={end_iso}\n")
    os.replace(p + ".tmp", p)


def clear_capstamp(flags, rid, archive_as=None):
    p = capstamp_path(flags, rid)
    if os.path.exists(p):
        if archive_as:
            os.replace(p, archive_as)
        else:
            os.remove(p)


def capcut_pending(flags, rid):
    """Cut at our own drain cap AND not filed/superseded (capcut_closed)."""
    return capcut_cut(flags, rid) and not capcut_closed(flags, rid)


def capcut_closed(flags, rid):
    """Coordinator guard 2026-11-11: a capcut row is NOT requeued when it is already filed (filing-done/<id>.FILED) or
    SUPERSEDED (any ready/*.json names it in `supersedes`) - requeueing would duplicate work. Returns the reason or ""."""
    if os.path.exists(os.path.join(flags, "filing-done", rid + ".FILED")):
        return "already filed"
    by = superseded_by(flags, rid)   # PM-KEEPER3 #3: also an unsmoked successor and the publish-time block marker
    return f"superseded by {by}" if by else ""


def capcut_cut(flags, rid):
    """True when grants/<id>.ended is the engine's hard-end kill AT THE KEEPER'S OWN drain cap: rc=75 reason=hard-end,
    the grant is cap-stamped and its end= equals the stamped cap. The keeper requeues such a row under the same id;
    filing must not file it. (The same predicate lives in churn/filing.py:capcut_pending - keep them in step.)"""
    G = os.path.join(flags, "grants")
    if os.path.exists(os.path.join(G, rid + ".complete")):
        return False
    h = head1(os.path.join(G, rid + ".ended")) or ""
    if not (re.search(r"(^|\s)rc=75(\s|$)", h) and re.search(r"(^|\s)reason=hard-end(\s|$)", h)):
        return False
    st = head1(capstamp_path(flags, rid)) or ""
    return _capcut_matches(st, head1(os.path.join(G, rid + ".grant")) or "", h)


def _capcut_matches(st, gl, h):
    """2026-11-11 fix (afc-v3c-q38_flash-tools-mild-20261111): the launcher (filler_run15.sh end path) DELETES the
    .grant right after writing .ended, so at requeue time there is normally no grant end= to compare. Grant present:
    its end= must equal the stamped end (a re-grant without a cap cleared the stamp anyway). Grant gone: the .ended
    time must be at/after the stamped cap minute (the engine killed it AT the cap) and within CAPCUT_SLACK_S of it."""
    cm, se = re.search(r"\bcap=(\d+)", st), re.search(r"\bend=(\S+)", st)
    if not (cm and se):
        return False
    ge = re.search(r"\bend=(\S+)", gl)
    if ge:
        return se.group(1) == ge.group(1)
    tm = re.search(r"(?:^|\s)time=(\d{4}-\d\d-\d\dT\d\d:\d\d(?::\d\d)?Z)", h)
    if not tm:
        return False
    t = tm.group(1)
    fmt = "%Y-%m-%dT%H:%M:%SZ" if t.count(":") == 2 else "%Y-%m-%dT%H:%MZ"
    te = dt.datetime.strptime(t, fmt).replace(tzinfo=dt.timezone.utc).timestamp()
    cap = int(cm.group(1))
    return cap - 60 <= te <= cap + CAPCUT_SLACK_S


def capcut_requeue(flags, log=print, now=None):
    """Each tick, before filing/status: a row cut by our own drain cap is made grantable again under the SAME id -
    its .ended, .grant and cap stamp move to grants/.capcut/<id>.<ts>.*; the ready manifest is untouched. A row whose
    owner STOPped it, whose manifest is gone, or that hit CAPCUT_MAX requeues in 24 h ends as today (stamp archived,
    so filing proceeds). Returns the requeued ids."""
    now = time.time() if now is None else now
    G = os.path.join(flags, "grants")
    out = []
    for e in sorted(glob.glob(os.path.join(G, "*.ended"))):
        rid = os.path.basename(e)[:-6]
        if rid.startswith(".") or not capcut_cut(flags, rid):
            continue
        cd = capcut_dir(flags)
        os.makedirs(cd, exist_ok=True)
        ts = dt.datetime.fromtimestamp(now, dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        d = load_json(ready_path(flags, rid))
        sf = resolve_stop_path(d) if d else None
        hp = os.path.join(cd, rid + ".history.json")
        hist = [float(x) for x in ((load_json(hp) or {}).get("requeued_at") or []) if now - float(x) < CAPCUT_WINDOW_S]
        why = None
        closed = capcut_closed(flags, rid)
        if closed:
            clear_capstamp(flags, rid, archive_as=os.path.join(cd, f"{rid}.{ts}.cap-final"))
            log(f"CAPCUT-END {rid}: already filed/superseded ({closed}); ends normally")
            continue
        if not d:
            why = "no ready manifest (withdrawn/moved)"
        elif sf and os.path.exists(sf):
            why = f"STOP file {sf} present"
        elif len(hist) >= CAPCUT_MAX:
            why = f"requeue limit {CAPCUT_MAX}/24h reached"
        if why:
            clear_capstamp(flags, rid, archive_as=os.path.join(cd, f"{rid}.{ts}.cap-final"))
            log(f"CAPCUT-END {rid}: cut at the drain cap but {why}; ends normally")
            continue
        for suf in (".ended", ".grant"):
            src = os.path.join(G, rid + suf)
            if os.path.exists(src):
                shutil.move(src, os.path.join(cd, f"{rid}.{ts}{suf}"))
        clear_capstamp(flags, rid, archive_as=os.path.join(cd, f"{rid}.{ts}.cap"))
        hist.append(now)
        atomic_json(hp, {"id": rid, "requeued_at": hist})
        log(f"CAPCUT-REQUEUE {rid}: hard-end at the keeper's drain cap; .ended/.grant archived to .capcut/{rid}.{ts}.*, "
            f"same id grantable again ({len(hist)}/{CAPCUT_MAX} in 24h)")
        out.append(rid)
    return out


# ---------------------------------------------------------------- AUTO-REQUEUE (operator approved 2026-11-21)
# A RESUMABLE row whose window ended rc=75 reason=partial-* is made grantable again under the SAME id (the capcut
# mechanism: .ended/.grant archived, manifest and PASS untouched), at most AUTOREQUEUE_MAX times per row; then the row
# ends normally (filed) and its owner gets one alert. A PERSISTENT environmental refusal is never retried: the job
# declares it via FILLER_BLOCKED_FILE (filler_run15.sh -> reason=partial-blocked-*, blocked_on=/requeue=false lines in
# .ended) or a top-level "requeue": false / "blocked_on" in its RESULT json. (Mirrored in churn/filing.py.)
AUTOREQUEUE_MAX = 3
AUTOREQUEUE_CAP = 48   # ceiling for the per-row spec/manifest field `autorequeue_max` (time-sliced rows, operator 2026-11-21)


def autorequeue_max_check(v):
    """Validate the optional per-row `autorequeue_max` (int 0..AUTOREQUEUE_CAP, not bool); returns it or None. Raises Refused."""
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= AUTOREQUEUE_CAP:
        raise Refused(f"autorequeue_max {v!r} must be an integer 0..{AUTOREQUEUE_CAP} (global default {AUTOREQUEUE_MAX})")
    return v


def autorequeue_max_for(d):
    """Effective auto-requeue cap for a manifest: its valid autorequeue_max, else the global AUTOREQUEUE_MAX."""
    try:
        v = autorequeue_max_check((d or {}).get("autorequeue_max"))
    except Refused:
        v = None
    return AUTOREQUEUE_MAX if v is None else v


def autorequeue_dir(flags):
    return os.path.join(flags, "grants", ".autorequeue")


def _ended_text(flags, rid):
    try:
        with open(os.path.join(flags, "grants", rid + ".ended"), errors="replace") as fh:
            return fh.read(8192)
    except OSError:
        return ""


def _result_json(d):
    rp = str((d or {}).get("result_path") or "")
    if not rp:
        return {}
    if not os.path.isabs(rp):
        rp = os.path.join(str((d or {}).get("workdir") or ""), rp)
    if not rp.endswith(".json") or not os.path.isfile(rp):
        return {}
    try:
        with open(rp, errors="replace") as fh:
            r = json.load(fh)
    except (OSError, ValueError):
        return {}
    return r if isinstance(r, dict) else {}


def autorequeue_blocked(text, result=None):
    """The job's declared persistent blocker ("" = none): reason=partial-blocked-*, a blocked_on=/requeue=false line in
    .ended, or RESULT {"requeue": false} / {"blocked_on": ...}."""
    m = re.search(r"(?:^|\s)reason=(partial-blocked\S*)", text)
    b = re.search(r"(?m)^blocked_on=(.*)$", text)
    if b and b.group(1).strip():
        return b.group(1).strip()
    if m:
        return m.group(1)
    if re.search(r"(?m)^requeue=(false|0|no)\s*$", text):
        return "requeue=false"
    r = result or {}
    if r.get("blocked_on"):
        return str(r["blocked_on"])[:200]
    if r.get("requeue") is False:
        return "RESULT requeue=false"
    return ""


def autorequeue_history(flags, rid):
    return [float(x) for x in ((load_json(os.path.join(autorequeue_dir(flags), rid + ".history.json")) or {})
                               .get("requeued_at") or [])]


COMPLETE_SUSPECT_S = 60   # rc=0 reason=complete this soon after grant start, with no evidence of work, is not a completion


def _iso_epoch(s):
    try:
        return dt.datetime.strptime(s.strip(), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).timestamp()
    except (ValueError, AttributeError):
        return None


def complete_suspect(flags, rid, text=None):
    """Why an rc=0 reason=complete end is SUSPECT ("" = trustworthy). Suspect = ended within COMPLETE_SUSPECT_S of the grant
    start (.ended `started=`) AND (a) no result file was written after the start (the --complete-cmd passed on OUTPUT THAT
    PREDATES THE GRANT: c18-fold-cpu-20261122), or (b) the only evidence is a PASS with no first-progress marker (no other
    artifact under the workdir written since the start). A fresh RESULT with a FUTILITY*/FAIL* verdict is a legitimate fast
    end (c19-fold-cpu-20261123: proof-clause futility in seconds) and is never flagged."""
    text = _ended_text(flags, rid) if text is None else text
    head = text.splitlines()[0] if text else ""
    if not (re.search(r"(^|\s)rc=0(\s|$)", head) and "reason=complete" in head):
        return ""
    t_end = _iso_epoch((re.search(r"time=(\S+)", head) or [None, ""])[1])
    m = re.search(r"(?m)^started=(\S+)", text)
    t0 = _iso_epoch(m.group(1)) if m else None
    if t0 is None or t_end is None or not 0 <= t_end - t0 < COMPLETE_SUSPECT_S:
        return ""
    d = load_json(ready_path(flags, rid)) or {}
    wd = str(d.get("workdir") or "")
    rp = str(d.get("result_path") or "")
    if rp and not os.path.isabs(rp):
        rp = os.path.join(wd, rp)
    cands = [rp] if rp else []
    for base in (wd, os.path.join(wd, "out")) if wd else ():
        cands += glob.glob(os.path.join(base, "RESULT*.json"))
    fresh = [c for c in cands if os.path.isfile(c) and os.path.getmtime(c) >= t0 - 1]
    el = int(t_end - t0)
    if not fresh:
        return f"ended {el}s after grant start with no result file written since (complete-check passed on pre-existing output)"
    for c in fresh:
        try:
            v = str((json.load(open(c, errors="replace")) or {}).get("verdict") or "")
        except (OSError, ValueError, AttributeError):
            v = ""
        if v.startswith(("FUTILITY", "FAIL")):
            return ""   # the job itself wrote a terminal non-PASS verdict this run: legitimate fast end
    marker = False
    if wd and os.path.isdir(wd):
        skip = set(fresh)
        for root, dirs, files in os.walk(wd):
            dirs[:] = [x for x in dirs if x not in ("smoke", "__pycache__") and not x.startswith("out-smoke")]
            if root[len(wd):].count(os.sep) >= 3:
                dirs[:] = []
            for f in files:
                fp = os.path.join(root, f)
                if fp not in skip and not f.endswith(".pyc") and os.path.getmtime(fp) >= t0 - 1:
                    marker = True
                    break
            if marker:
                break
    if marker:
        return ""
    return f"ended {el}s after grant start with a PASS result but no first-progress marker (no artifact written by the run)"


def autorequeue_decision(flags, rid):
    """(kind, why): kind 'requeue' | 'blocked' | 'limit' | 'stop' | 'suspect' | 'suspect-requeue' | None (not an auto-requeue end at all)."""
    G = os.path.join(flags, "grants")
    text = _ended_text(flags, rid)
    if os.path.exists(os.path.join(flags, "filing-done", rid + ".FILED")):
        return None, ""
    sus = complete_suspect(flags, rid, text)
    if sus:
        d = load_json(ready_path(flags, rid))
        done = bool(((load_json(os.path.join(autorequeue_dir(flags), rid + ".history.json")) or {}).get("suspect_requeued")))
        stale = sus.startswith("ended") and "no result file" in sus
        if d and d.get("resumable") and stale and not done:
            return "suspect-requeue", sus
        return "suspect", sus
    if os.path.exists(os.path.join(G, rid + ".complete")):
        return None, ""
    first = text.splitlines()[0] if text else ""
    if not (re.search(r"(^|\s)rc=75(\s|$)", first) and re.search(r"(^|\s)reason=partial-\S+", first)):
        return None, ""
    d = load_json(ready_path(flags, rid))
    if not d or not d.get("resumable"):
        return None, ""
    if capcut_closed(flags, rid):
        return None, ""
    why = autorequeue_blocked(text, _result_json(d))
    if why:
        return "blocked", why
    sf = resolve_stop_path(d)
    if sf and os.path.exists(sf):
        return "stop", f"STOP file {sf} present"
    n = len(autorequeue_history(flags, rid))
    mx = autorequeue_max_for(d)
    if n >= mx:
        return "limit", f"auto-requeue limit {mx} reached"
    return "requeue", f"{n + 1}/{mx}"


def autorequeue_pending(flags, rid):
    """Filing must not file this end: the keeper requeues it under the same id."""
    return autorequeue_decision(flags, rid)[0] in ("requeue", "suspect-requeue", "suspect")   # suspect: held, not filed done


def autorequeue(flags, log=print, now=None, emit=None):
    """Each tick, next to capcut_requeue. Returns the requeued ids."""
    now = time.time() if now is None else now
    emit = emit or notify.emit
    G = os.path.join(flags, "grants")
    out = []
    for e in sorted(glob.glob(os.path.join(G, "*.ended"))):
        rid = os.path.basename(e)[:-6]
        if rid.startswith(".") or capcut_cut(flags, rid):
            continue
        kind, why = autorequeue_decision(flags, rid)
        if kind is None:
            continue
        ad = autorequeue_dir(flags)
        os.makedirs(ad, exist_ok=True)
        hp = os.path.join(ad, rid + ".history.json")
        hj = load_json(hp) or {}
        head = (_ended_text(flags, rid).splitlines() or [""])[0]
        if kind == "suspect":
            if hj.get("final_for") == head:
                continue
            owner = str((load_json(ready_path(flags, rid)) or {}).get("owner") or "")
            summary = (f"COMPLETE-SUSPECT {rid}: {why}; NOT filed as done - owner: verify the result is from this run "
                       f"(not auto-requeued: no stale output proven or already requeued once)")
            log(summary)
            try:
                emit(flags, "complete-suspect", rid, head[:80], summary, "warning", owner=owner)
            except Exception as ex:  # noqa: BLE001
                log(f"COMPLETE-SUSPECT alert failed: {type(ex).__name__}: {ex}")
            atomic_json(hp, dict(hj, id=rid, final_for=head, requeued_at=hj.get("requeued_at") or []))
            continue
        if kind != "requeue" and kind != "suspect-requeue":
            if hj.get("final_for") == head:
                continue   # decided once for this end; filing files it
            owner = str((load_json(ready_path(flags, rid)) or {}).get("owner") or "")
            sev = "warning"
            if kind == "limit":
                summary = (f"AUTOREQUEUE-LIMIT {rid}: ended {head!r} after {autorequeue_max_for(load_json(ready_path(flags, rid)))} auto-requeues; not requeued again, "
                           f"filed as partial - owner: fix the cause and republish")
            elif kind == "blocked":
                summary = (f"AUTOREQUEUE-BLOCKED {rid}: ended {head!r}, job declared a persistent blocker ({why}); "
                           f"not requeued - owner: clear the blocker and republish")
            else:
                summary, sev = f"AUTOREQUEUE-END {rid}: {why}; ends normally", "info"
            log(summary)
            if kind in ("limit", "blocked"):
                try:
                    emit(flags, f"autorequeue-{kind}", rid, head[:80], summary, sev, owner=owner)
                except Exception as ex:  # noqa: BLE001 - an alert failure never stops allocation
                    log(f"AUTOREQUEUE alert failed: {type(ex).__name__}: {ex}")
            atomic_json(hp, dict(hj, id=rid, final_for=head, requeued_at=hj.get("requeued_at") or []))
            continue
        ts = dt.datetime.fromtimestamp(now, dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        if kind == "suspect-requeue":
            owner = str((load_json(ready_path(flags, rid)) or {}).get("owner") or "")
            summary = (f"COMPLETE-SUSPECT {rid}: {why}; requeued once, reason=partial-blocked-stale-complete - owner: "
                       f"remove the stale output or the requeue ends complete again")
            try:
                emit(flags, "complete-suspect", rid, head[:80], summary, "warning", owner=owner)
            except Exception as ex:  # noqa: BLE001
                log(f"COMPLETE-SUSPECT alert failed: {type(ex).__name__}: {ex}")
        for suf in (".ended", ".grant", ".complete"):
            src = os.path.join(G, rid + suf)
            if os.path.exists(src):
                shutil.move(src, os.path.join(ad, f"{rid}.{ts}{suf}"))
        hist = autorequeue_history(flags, rid) + [now]
        atomic_json(hp, {"id": rid, "requeued_at": hist, **({"suspect_requeued": "partial-blocked-stale-complete"} if kind == "suspect-requeue" else {})})
        log(f"AUTO-REQUEUE {rid}: {head}; resumable partial end, .ended/.grant archived to .autorequeue/{rid}.{ts}.*, "
            f"same id grantable again ({len(hist)}/{autorequeue_max_for(load_json(ready_path(flags, rid)))})")
        out.append(rid)
    return out


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
    since = {k: v for k, v in (hist.get("underused_since") or {}).items()}
    out = []
    # a grant holding the GPU token is judged by KFD/VRAM (idle_held + gpu_grant_busy), never by CPU %
    gpu_rids = {rid for r, rid in holders.items() if r == GPU}
    guards, guard_lines = {}, {}
    for r, rid in holders.items():
        if r not in QUARTERS or rid in gpu_rids:
            continue
        if rid not in guards:
            guards[rid] = quiet_guard_of(flags, rid)
        if r in guards[rid]:
            guard_lines.setdefault(rid, []).append(r)
    log_transition(flags, "quiet-guard", {rid: f"QUIET-GUARD {rid} regions={','.join(sorted(rs))}" for rid, rs in guard_lines.items()}, log)
    for r, rid in holders.items():
        if rid in gpu_rids:
            continue
        if r in guards.get(rid, ()):
            continue   # a pre-registered quiet guard: idle on purpose, never UNDERUSED, never shrunk
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
            since.setdefault(f"{r}:{rid}", s0["ts"])
            out.append((r, rid, pct))
            seen.add(f"underused:{r}:{rid}")
            log(f"UNDERUSED {r} {rid}: {pct:.1f}% of its CPUs busy over {int(now - s0['ts'])}s (<{UNDERUSED_PCT:g}%); not killed; owner fix task dryrun/{rid}/UNDERUSED.json")
            fp = os.path.join(dry_dir(flags, rid), "UNDERUSED.json")
            try:   # F9: UNDERUSED reaches the owner (one alert per region+row: notify keys are idempotent)
                notify.emit(flags, "underused", rid, r, f"UNDERUSED {r} {rid}: {pct:.1f}% of its CPUs busy over "
                            f"{int(now - s0['ts'])}s; shrink its regions/claim or split the row", "warning",
                            str((load_json(ready_path(flags, rid)) or {}).get("owner") or ""),
                            {"region": r, "busy_pct": round(pct, 1)})
            except Exception as ex:  # noqa: BLE001
                log(f"UNDERUSED {rid}: notify failed: {type(ex).__name__}: {ex}")
            if not os.path.exists(fp):
                os.makedirs(dry_dir(flags, rid), exist_ok=True)
                atomic_json(fp, {"id": rid, "at": now_iso(), "region": r, "busy_pct": round(pct, 1), "window_s": int(now - s0["ts"]),
                                 "fix_task": f"{rid} holds {r} but uses {pct:.1f}% of it: shrink its regions/claim (a fetch or single-core job is not a quarter row), or split the row"})
    live = {f"{r}:{rid}" for r, rid, _ in out}
    hist["underused_since"] = {k: v for k, v in since.items() if k in live}
    atomic_json(p, hist)
    shrink_suggest(flags, holders, out, hist["underused_since"], now, log)
    return out


def _cpu_ids(spec):
    out = []
    for t in str(spec or "").split(","):
        a, _, b = t.strip().partition("-")
        if a.isdigit():
            out += list(range(int(a), int(b or a) + 1))
    return out


def build_idle_release(flags, holders, log, sample=None, now=None):
    """Auto-release of an IDLE BUILD claim (pipeline-mgmt 2026-11-21; D9 standing AK ack). A build-* grant whose own CPUs
    (build.json cpus) stay < idle_pct busy for idle_min minutes (policy build_pocket_policy.json: auto_release_idle) is ended
    through release_grant(by=its owner, ended_reason=auto-released-idle-build) and logged BUILD-AUTO-RELEASED <id> idle <N>min.
    Any busy tick resets the anchor. BUILD claims only: a measurement row is never touched. Never kills a process. Returns [ids]."""
    pol = (build_pocket_policy(flags).get("auto_release_idle") or {})
    if not pol.get("enabled"):
        return []
    now = now or time.time()
    sample = cpu_sample() if sample is None else sample
    thr, need_s = float(pol.get("idle_pct", 5.0)), float(pol.get("idle_min", 30)) * 60
    p = os.path.join(state_dir(flags), "build_idle.json")
    st = load_json(p) or {}
    live = {rid for rid in holders.values() if str(rid).startswith(BUILD_PREFIX)}
    new, out = {}, []
    for rid in sorted(live):
        bj = load_json(os.path.join(flags, "grants", rid + ".build.json")) or {}
        cpus = _cpu_ids(bj.get("cpus"))
        if not cpus:
            continue
        cur = {str(c): list(sample.get(c, (0, 0))) for c in cpus}
        a = st.get(rid)
        if not a:
            new[rid] = {"ts": now, "cpu": cur}
            continue
        b0 = sum(a["cpu"].get(str(c), (0, 0))[0] for c in cpus); t0 = sum(a["cpu"].get(str(c), (0, 0))[1] for c in cpus)
        b1 = sum(v[0] for v in cur.values()); t1 = sum(v[1] for v in cur.values())
        pct = 100.0 * (b1 - b0) / (t1 - t0) if t1 > t0 else 100.0
        if pct >= thr:
            new[rid] = {"ts": now, "cpu": cur}   # busy: restart the idle window
            continue
        new[rid] = a
        if now - a["ts"] >= need_s:
            try:
                if release_grant(flags, rid, str(bj.get("owner") or ""), "auto-released-idle-build", log=lambda m: None,
                                 ended_reason="auto-released-idle-build") == "RELEASED":
                    log(f"BUILD-AUTO-RELEASED {rid} idle {int((now - a['ts']) // 60)}min ({pct:.1f}% of its CPUs busy; no process killed)")
                    out.append(rid)
                    new.pop(rid, None)
            except Refused as e:
                log(f"BUILD-AUTO-RELEASE {rid}: refused: {e}")
    atomic_json(p, new)
    return out


def shrink_suggest(flags, holders, under, since, now, log, emit=None):
    """F6 (AK audit B6): a row UNDERUSED on some held quarters for UNDERUSED_SHRINK_S gets ONE owner note through
    notify.emit: "shrink to <n> quarters" (n = held CPU quarters minus the underused ones, at least 1). Never acts."""
    emit = emit or notify.emit
    by = {}
    for r, rid, pct in under:
        if now - float(since.get(f"{r}:{rid}") or now) >= UNDERUSED_SHRINK_S:
            by.setdefault(rid, []).append((r, pct))
    for rid, qs in by.items():
        held = sorted(r for r, x in holders.items() if x == rid and r in QUARTERS)
        n = max(1, len(held) - len(qs))
        owner = str((load_json(ready_path(flags, rid)) or {}).get("owner") or "")
        msg = (f"UNDERUSED {rid}: {','.join(r for r, _ in qs)} under {UNDERUSED_PCT:g}% busy for >= {UNDERUSED_SHRINK_S // 60} min "
               f"of the {len(held)} quarter(s) it holds; shrink to {n} quarter{'s' if n > 1 else ''} (shape "
               f"{'quarter' if n == 1 else f'multi-quarter({n})'}) on its next publish")
        try:
            if emit(flags, "underused-shrink", rid, ",".join(held), msg, "warning", owner,
                    {"held": held, "underused": [r for r, _ in qs], "suggest_quarters": n}):
                log(f"UNDERUSED-SHRINK {rid}: suggested {n} quarter(s) to owner={owner or FALLBACK_OWNER}")
        except Exception as ex:  # noqa: BLE001
            log(f"UNDERUSED-SHRINK {rid}: notify failed: {type(ex).__name__}: {ex}")


IDLE_HELD_AFTER_S = 60   # a grant older than this whose regions measure < hostutil.IDLE_PCT busy is IDLE-HELD


def measure_util(sample_s=hostutil.SAMPLE_S):
    """One measured utilisation reading per tick (patched in tests)."""
    return hostutil.measure(sample_s)


def gpu_idle_state_path(flags):
    return os.path.join(state_dir(flags), "gpu_idle.json")


def gpu_grant_busy(flags, g, util, occ):
    """(busy, why) of a GPU-token grant by GPU SIGNALS only - its own KFD clients (and their VRAM) and the device
    busy %. Busy when the grant's process tree holds any KFD client OR the device reads >= IDLE_PCT; quiet only when
    both are silent. CPU % is never consulted (ak-asm-t1-harness: a running GPU harness read IDLE-HELD by CPU %)."""
    own = own_pids(flags, g, (occ.get("pids") or {}))
    kfd = {p: v for p, v in (occ.get("pids") or {}).items() if p in own}
    busy_pct = (util.get("gpu") or {}).get("busy") if isinstance(util, dict) else None
    if kfd:
        return True, f"{len(kfd)} own KFD client(s) {','.join(map(str, sorted(kfd)[:4]))} hold {sum(kfd.values()) / (1 << 30):.1f} GiB"
    if busy_pct is not None and busy_pct >= hostutil.IDLE_PCT:
        return True, f"device {busy_pct:.0f}% busy"
    if busy_pct is None and not (occ.get("pids") or {}) and occ.get("vram_used") is None:
        return True, "device unreadable (never idle on no evidence)"
    return False, f"no own KFD client, device {busy_pct if busy_pct is not None else '?'}% busy"


def log_transition(flags, kind, current, log, persist=True):
    """Log current = {key: line} only for keys that were not present on the previous tick (state:
    ws58-keeper-state/allocator/logstate.json {kind: [keys]}); a key that disappears and returns logs again. Decisions
    never read this."""
    sp = os.path.join(state_dir(flags), "logstate.json")
    st = load_json(sp) or {}
    prev = set(st.get(kind) or [])
    for k, line in current.items():
        if k not in prev:
            log(line)
    if persist and set(current) != prev:
        st[kind] = sorted(current)
        try:
            atomic_json(sp, st)
        except OSError as ex:
            log(f"{kind} logstate write failed ({sp}): {ex}")


# ---------------------------------------------------------------- SCRATCH-OVER (operator 2026-11-21, disk guards; LOG ONLY, never a kill)
# A running row whose scratch_root grows past its declared `scratch_gb` (default SCRATCH_OVER_DEFAULT_GB = 40) logs
# `SCRATCH-OVER <row> <GB>`. A 29 GB smoke GGUF nobody declared is what this catches. du is throttled per row (SCRATCH_OVER_EVERY_S) and a
# row is re-logged only when its size grew >= SCRATCH_OVER_REGROW_GB since the last line (state in ws58-keeper-state/allocator/scratch_over.json).
SCRATCH_OVER_DEFAULT_GB = 40.0
SCRATCH_OVER_EVERY_S = 600
SCRATCH_OVER_REGROW_GB = 5.0


def _scratch_gb(path):
    try:
        r = subprocess.run(["du", "-sk", path], capture_output=True, text=True, timeout=300)
        return int(r.stdout.split()[0]) / 1048576.0
    except (OSError, subprocess.TimeoutExpired, ValueError, IndexError):
        return None


def scratch_over(flags, grants, log, now=None, du_gb=None, state_path=None):
    """Log SCRATCH-OVER for running grants over their declared scratch_gb (default 40). Returns [(rid, gb)] logged. Never raises, never kills."""
    now = time.time() if now is None else now
    du_gb = du_gb or _scratch_gb
    sp = state_path or os.path.join(flags, "ws58-keeper-state", "allocator", "scratch_over.json")
    st = load_json(sp) or {}
    out = []
    for g in grants:
        rid = g["id"]
        try:
            ent = st.get(rid) or {}
            if now - float(ent.get("checked", 0)) < SCRATCH_OVER_EVERY_S:
                continue
            m = load_json(ready_path(flags, rid)) or {}
            root = m.get("scratch_root")
            if not isinstance(root, str) or not os.path.isdir(root):
                continue
            cap = float(m.get("scratch_gb") or SCRATCH_OVER_DEFAULT_GB)
            gb = du_gb(root)
            ent["checked"] = now
            if gb is not None and gb > cap and gb >= float(ent.get("logged_gb", 0)) + SCRATCH_OVER_REGROW_GB:
                log(f"SCRATCH-OVER {rid} {gb:.1f}G (declared {cap:g}G{'' if m.get('scratch_gb') else ', default'}; root {root}; log-only)")
                ent["logged_gb"] = gb
                out.append((rid, round(gb, 1)))
            st[rid] = ent
        except Exception as ex:  # noqa: BLE001 - a log-only guard never stops allocation
            log(f"SCRATCH-OVER check failed for {rid}: {type(ex).__name__}: {ex}")
    try:
        os.makedirs(os.path.dirname(sp), exist_ok=True)
        with open(sp, "w") as fh:
            json.dump(st, fh)
    except OSError:
        pass
    return out


# ---------------------------------------------------------------- LARGE-DERIVED (operator 2026-11-23; LOG ONLY, never a kill)
# 18 GB of leftover GGUF/safetensors/bin sat in scratch because no row declared them. A running row whose scratch_root holds a regular
# file >= LARGE_DERIVED_MIN_BYTES (1 GiB) with a model suffix that the manifest's `reclaimable` globs (relative to scratch_root; "*" =
# everything is raw) do not name logs `LARGE-DERIVED <row> ...`. Symlinks are skipped (they own no bytes here). Declared files are freed at filing
# by the reaper, which deletes everything outside keep; the flag exists so a >1G file is a deliberate declaration, not an accident.
LARGE_DERIVED_MIN_BYTES = 1 << 30
LARGE_DERIVED_SUFFIXES = (".gguf", ".safetensors", ".bin")
LARGE_DERIVED_EVERY_S = 600


def large_derived(root, reclaimable=None, min_bytes=LARGE_DERIVED_MIN_BYTES):
    """[(path, bytes)] of undeclared regular files >= min_bytes with a model suffix under root, biggest first."""
    import fnmatch
    globs = [g.lstrip("./") for g in (reclaimable or [])]
    found = []
    for dp, _dn, fns in os.walk(root, followlinks=False):
        for fn in fns:
            if not fn.lower().endswith(LARGE_DERIVED_SUFFIXES):
                continue
            fp = os.path.join(dp, fn)
            try:
                st = os.lstat(fp)
            except OSError:
                continue
            if not stat.S_ISREG(st.st_mode) or st.st_size < min_bytes:
                continue
            rel = os.path.relpath(fp, root)
            if any(g == "*" or fnmatch.fnmatch(rel, g) or fnmatch.fnmatch(fn, g) for g in globs):
                continue
            found.append((fp, st.st_size))
    return sorted(found, key=lambda x: -x[1])


def large_derived_check(flags, grants, log, now=None, state_path=None, scan=None):
    """Log LARGE-DERIVED once per (row, file) for running grants. Returns [(rid, path, GB)] logged. Never raises, never kills."""
    now = time.time() if now is None else now
    scan = scan or large_derived
    sp = state_path or os.path.join(flags, "ws58-keeper-state", "allocator", "large_derived.json")
    st = load_json(sp) or {}
    out = []
    for g in grants:
        rid = g["id"]
        try:
            ent = st.get(rid) or {}
            if now - float(ent.get("checked", 0)) < LARGE_DERIVED_EVERY_S:
                continue
            m = load_json(ready_path(flags, rid)) or {}
            root = m.get("scratch_root")
            if not isinstance(root, str) or not os.path.isdir(root):
                continue
            ent["checked"] = now
            seen = set(ent.get("logged") or [])
            for fp, sz in scan(root, m.get("reclaimable")):
                if fp in seen:
                    continue
                log(f"LARGE-DERIVED {rid} {sz / 2**30:.1f}G {fp} (undeclared; add `reclaimable: [\"<glob under scratch_root>\"]` to the row spec "
                    "so filing frees it, or `keep` it deliberately; log-only)")
                seen.add(fp)
                out.append((rid, fp, round(sz / 2**30, 1)))
            ent["logged"] = sorted(seen)
            st[rid] = ent
        except Exception as ex:  # noqa: BLE001 - a log-only guard never stops allocation
            log(f"LARGE-DERIVED check failed for {rid}: {type(ex).__name__}: {ex}")
    try:
        os.makedirs(os.path.dirname(sp), exist_ok=True)
        with open(sp, "w") as fh:
            json.dump(st, fh)
    except OSError:
        pass
    return out


def idle_held(flags, grants, holders, util, log, seen, now=None, occ=None):
    """2026-11-03 session review item 2: every held region is judged by MEASUREMENT, not by its grant file - a grant
    older than IDLE_HELD_AFTER_S whose region reads < IDLE_PCT busy logs IDLE-HELD (one line: region, row, %, age,
    where the logs are). Never kills, never de-grants; the 3rd consecutive tick raises the repeat ALERT. Returns the
    [(region, rid, pct)] list.
    a grant holding the GPU token is judged by GPU signals ONLY (gpu_grant_busy: own KFD
    clients, device busy %), never by the CPU % of the regions it holds, and reads IDLE-HELD only after GPU_IDLE_SAMPLES
    consecutive quiet samples (state: ws58-keeper-state/allocator/gpu_idle.json {rid: quiet samples})."""
    now = time.time() if now is None else now
    age, by_id = {}, {}
    for g in grants:
        by_id[g["id"]] = g
        try:
            age[g["id"]] = int(now - os.path.getmtime(g["path"]))
        except OSError:
            continue
    gpu_ids = {g["id"] for g in grants if GPU in g["holds"]}
    out, lines = [], {}
    self_paused = diskpause.stopped_ids(flags)   # rows the disk-pause guard itself SIGSTOPped: idle by our own hand
    for r, rid in sorted(holders.items()):
        if rid not in age or age[rid] <= IDLE_HELD_AFTER_S:
            continue
        if rid in self_paused:
            lines[f"{r}:{rid}"] = f"DISK-PAUSED (self) {r} {rid}: SIGSTOPped by the disk-pause guard; not IDLE-HELD"
            continue
        if rid in gpu_ids:
            continue   # judged below, by the device
        if r in quiet_guard_of(flags, rid):
            continue   # declared quiet guard: idle on purpose (QUIET-GUARD is logged by underused); feeds IDLE-HELD-WARN too
        v = hostutil.regions_pct(util, [r]).get(r)
        if v is not None and v < hostutil.IDLE_PCT:
            out.append((r, rid, v))
            seen.add(f"idle-held:{r}:{rid}")
            lines[f"{r}:{rid}"] = f"IDLE-HELD {r} {rid}: measured {v:.0f}% busy, grant {age[rid]}s old; logs {dry_dir(flags, rid)}"
    sp = gpu_idle_state_path(flags)
    st = {k: int(v) for k, v in (load_json(sp) or {}).items() if k in gpu_ids}
    if gpu_ids:
        try:
            occ = gpu_occupancy() if occ is None else occ
        except OSError:
            occ = {"pids": {}, "vram_used": None}
    for rid in sorted(gpu_ids):
        if rid not in age or age[rid] <= IDLE_HELD_AFTER_S:
            st[rid] = 0
            continue
        if rid in self_paused:
            st[rid] = 0
            lines[f"{GPU}:{rid}"] = f"DISK-PAUSED (self) {GPU} {rid}: SIGSTOPped by the disk-pause guard; not IDLE-HELD"
            continue
        busy, why = gpu_grant_busy(flags, by_id[rid], util, occ)
        st[rid] = 0 if busy else int(st.get(rid) or 0) + 1
        if busy or st[rid] < GPU_IDLE_SAMPLES:
            continue
        v = float((util.get("gpu") or {}).get("busy") or 0.0) if isinstance(util, dict) else 0.0
        out.append((GPU, rid, v))
        seen.add(f"idle-held:{GPU}:{rid}")
        lines[f"{GPU}:{rid}"] = f"IDLE-HELD {GPU} {rid}: {why} for {st[rid]} samples, grant {age[rid]}s old; logs {dry_dir(flags, rid)}"
    try:
        atomic_json(sp, st)
    except OSError as ex:
        log(f"IDLE-HELD gpu state write failed ({sp}): {ex}")
    log_transition(flags, "idle-held", lines, log)
    return out


# ---------------------------------------------------------------- IDLE-HELD owner warning (operator 2026-11-05, notify-only)
# rock-aiter-tests-r3-20261105 hung on a stale lock and held gpu-quiet at 0% for ~20 min (21:20-21:41Z) while 7 GPU rows
# queued; the keeper logged IDLE-HELD every tick and told nobody (the earlier IDLE-HELD q3 under kvu16g3-retune-r3 was the
# same silent signal). A grant that has read IDLE-HELD continuously for IDLE_WARN_AFTER_S gets ONE [warning] to its owner
# through notify.emit (the smoke-fail path: rowflow-alerts.jsonl + inference inbox + session bus), then at most one repeat
# per IDLE_WARN_REPEAT_S. Covers gpu-quiet and CPU-quarter grants alike. NEVER kills, ends or changes a grant (the frozen
# keeper is notify-only; rowflow2 adds the rc=75 auto-end). Dedupe state: <flags>/ws58-keeper-state/allocator/idle_held_warn.json
# (first idle tick, last warning, warning count per grant); a tick that reads the grant busy again drops its entry.
IDLE_WARN_AFTER_S = 300    # continuous IDLE-HELD before the first warning
IDLE_WARN_REPEAT_S = 900   # at most one repeat warning per grant per this long
# IDLE-HELD should act: a grant IDLE-HELD continuously for IDLE_ESCALATE_AFTER_S raises
# ONE [critical] idle-held-escalate (notify.escalate_stale pages the operator if it stays unacked). RECLAIM is OPT-IN:
# only when <flags>/allocator.json {"idle_reclaim": true} or the row's spec {"idle_reclaim": true}, only after
# IDLE_RECLAIM_AFTER_S continuous idle, and only while a queued row wants a region the grant holds, the keeper touches the
# row's OWN stop file (resolve_stop_path) - the engine's STOP path: TERM the job group, KILL after its grace, .ended
# reason=stopped rc=75 (retryable). The row is then `stopped` (never re-granted) until its owner removes the stop file.
# The keeper never signals a process itself; a row whose stop file is unknown is escalated, never reclaimed.
IDLE_ESCALATE_AFTER_S = 1800
IDLE_RECLAIM_AFTER_S = 2700


def idle_reclaim_enabled(flags, row):
    cfg = load_json(os.path.join(flags, "allocator.json")) or {}
    return cfg.get("idle_reclaim") is True or (row or {}).get("idle_reclaim") is True


def _idle_act(flags, rid, e, regions, pct, idle_s, holds, owner, log, emit, wanted):
    """Escalate / opt-in reclaim for one continuously IDLE-HELD grant (state e is updated in place)."""
    if idle_s >= IDLE_ESCALATE_AFTER_S and not e.get("escalated_at"):
        summary = (f"IDLE-HELD {regions} {rid}: {pct:.0f}% busy for {idle_s}s after {int(e.get('warn_n') or 0)} warning(s); "
                   f"it holds {holds} while rows queue. Stop it (its stop file / rowflow.py withdraw) or ack this; "
                   f"logs {dry_dir(flags, rid)}")
        try:
            emit(flags, "idle-held-escalate", rid, regions, summary, "critical", owner,
                 {"regions": regions, "busy_pct": round(float(pct), 1), "idle_s": idle_s, "holds": holds,
                  "reclaim_after_s": IDLE_RECLAIM_AFTER_S, "logs": dry_dir(flags, rid)})
            e["escalated_at"] = time.time()
            log(f"IDLE-HELD-ESCALATE {regions} {rid}: {idle_s}s idle; [critical] sent to owner={owner or FALLBACK_OWNER}")
        except Exception as ex:  # noqa: BLE001
            log(f"IDLE-HELD-ESCALATE {regions} {rid}: notify failed: {type(ex).__name__}: {ex}")
    if idle_s < IDLE_RECLAIM_AFTER_S or e.get("reclaimed_at"):
        return
    row = load_json(ready_path(flags, rid)) or {}
    if not idle_reclaim_enabled(flags, row):
        return
    held = expand(set(r for r in regions.split(",") if r))
    if not any(expand(set(o)) & held for c in (wanted or ()) if c.get("id") != rid for o in c.get("options") or ()):
        return   # nobody queues for these regions: reclaiming frees nothing anyone wants
    sf = resolve_stop_path(row)
    if not sf:
        if not e.get("reclaim_refused"):
            e["reclaim_refused"] = True
            log(f"IDLE-RECLAIM-REFUSED {rid}: its stop file is unknown; escalated only")
        return
    try:
        os.makedirs(os.path.dirname(sf), exist_ok=True)
        with open(sf, "a") as f:
            f.write(json.dumps({"by": "rowflow idle-reclaim", "at": now_iso(), "regions": regions, "idle_s": idle_s,
                                "busy_pct": round(float(pct), 1)}) + "\n")
    except OSError as ex:
        log(f"IDLE-RECLAIM {rid}: stop file {sf} not written: {ex}")
        return
    e["reclaimed_at"] = time.time()
    log(f"IDLE-RECLAIM {regions} {rid}: {idle_s}s at {pct:.0f}% busy while queued rows want {holds}; touched its stop "
        f"file {sf} (engine stops it rc=75); remove the stop file to re-queue")
    try:
        emit(flags, "idle-held-reclaimed", rid, regions, f"IDLE-RECLAIM {rid}: stopped after {idle_s}s idle on {regions} "
             f"(opt-in idle_reclaim); remove {sf} to re-queue", "warning", owner, {"stop_file": sf, "idle_s": idle_s})
    except Exception as ex:  # noqa: BLE001
        log(f"IDLE-RECLAIM {rid}: notify failed: {type(ex).__name__}: {ex}")


IDLE_CRASH_CHILD_PCT = 5.0      # F6 (AK audit B6): a descendant above this CPU % is the job still working
IDLE_CRASH_REGION_PCT = 1.0     # "region busy 0 %" with measurement noise
IDLE_CRASH_SAMPLES = 2          # consecutive qualifying samples before the owner alert
IDLE_CRASH_ACT_S = 600          # review S2-1: act only after >= 10 min of continuous qualifying samples (audit bound)
IDLE_CRASH_MIN_GAP_S = 30       # samples closer than this are not "consecutive" (the keeper ticks ~60 s)


def idle_crash_state_path(flags):
    return os.path.join(state_dir(flags), "idle_after_crash.json")


def _tree_cpu(pid):
    """{pid: (starttime, cpu seconds)} of the launcher pid AND every live descendant (review S2-2: a launcher that execs
    into the job, or is the single worker, does its work in its own pid)."""
    hz = os.sysconf("SC_CLK_TCK")
    out = {}
    for c, birth in harness_tree(int(pid), {}).items():
        try:
            f = open(f"/proc/{c}/stat").read().rsplit(")", 1)[1].split()
        except (OSError, IndexError):
            continue
        if f[19] == birth:
            out[str(c)] = (birth, (int(f[11]) + int(f[12])) / hz)
    return out


def idle_crash_exempt(g, row):
    """Why idle_after_crash must not judge this grant (review S2-1), else None: a build lane, a quiet-host / gpu-q3 /
    timing row (its harness idles between arms by design), or a row with no first progress yet - its result file has
    not been written since the grant began (a 100+ GB mmap load or a quiet pre-run phase is not a crash). By design a
    row that writes its result only at the END (typical of a GPU row) stays exempt for its whole run: idle-after-crash
    never judges it, and its window end / the IDLE-HELD warnings are what bound a crashed one."""
    if g["id"].startswith(BUILD_PREFIX) or str(row.get("kind") or "") == "build":
        return "build"
    # publish_row normalizes shape gpu-q3 -> gpu and keeps the original in declared_shape (r14 false end)
    if (str(row.get("shape") or "") in ("quiet-host", "gpu-q3")
            or str(row.get("declared_shape") or "") in ("quiet-host", "gpu-q3") or row.get("timing")
            or row.get("admission_class") in GPU_TIMING_CLASSES):
        return "timing/quiet-host"
    rp = str(row.get("result_path") or "")
    try:
        t0 = os.path.getmtime(g["path"])
        hits = glob.glob(rp) if any(c in rp for c in "*?[") else [rp]
        if not any(os.path.exists(h) and os.path.getmtime(h) >= t0 for h in hits if h):
            return "no-first-progress"
    except (OSError, KeyError, TypeError):
        return "no-first-progress"
    return None


def idle_after_crash(flags, grants, util, log, now=None, emit=None, act=True, occ=None):
    """F6 (AK audit B6) idle-after-crash: a started (non-dry-run) grant whose launcher pid is alive while no descendant
    uses > IDLE_CRASH_CHILD_PCT CPU (the launcher's own pid included; for a GPU grant, the device reads idle for it) and
    every held region reads ~0 % busy, after its first progress (idle_crash_exempt). IDLE_CRASH_SAMPLES consecutive: a
    warning to the owner (alert before acting). >= IDLE_CRASH_ACT_S of continuous qualifying samples: the grant is ended the engine's own way - its STOP file is touched (filler_run15 stops, writes .ended rc=75) - and the
    owner is told reason=idle-after-crash. Never signals or kills a process. Returns [(rid, action)]."""
    now = time.time() if now is None else now
    emit = emit or notify.emit
    sp = idle_crash_state_path(flags)
    st = load_json(sp) or {}
    nst, out = {}, []
    for g in grants:
        rid, pid = g["id"], g.get("pid")
        if g.get("dryrun") or not g.get("started") or not pid or not proc_alive(pid):
            continue
        row = load_json(ready_path(flags, rid)) or {}
        skip = idle_crash_exempt(g, row)
        if skip:
            continue
        prev = st.get(rid) or {}
        e = {"t": now, "n": 0, "alerted": prev.get("alerted"), "ended": prev.get("ended"), "since": None}
        try:
            cpu = _tree_cpu(pid)
        except Exception:  # noqa: BLE001 - /proc races never end a grant
            continue
        e["cpu"] = {k: list(v) for k, v in cpu.items()}
        nst[rid] = e
        if e["ended"]:
            continue
        if not prev:
            continue   # the first sample is only a baseline for the CPU deltas
        dt_s = now - float(prev.get("t") or 0)
        if dt_s < IDLE_CRASH_MIN_GAP_S:
            nst[rid] = prev   # too close to the last sample to count: keep it as the baseline
            continue
        pcpu = prev.get("cpu") or {}
        busy_child = [k for k, (b, c) in cpu.items() if k in pcpu and pcpu[k][0] == b and 100.0 * (c - pcpu[k][1]) / dt_s > IDLE_CRASH_CHILD_PCT]
        busy_child += [k for k, (b, c) in cpu.items() if k not in pcpu and c / max(dt_s, 1.0) * 100.0 > IDLE_CRASH_CHILD_PCT]
        qs = [r for r in g["holds"] if r in QUARTERS]
        pct = hostutil.regions_pct(util or {}, qs)
        region_busy = any(v is None or v > IDLE_CRASH_REGION_PCT for v in pct.values())
        gpu_busy = False
        if GPU in g["holds"]:
            try:
                gpu_busy = gpu_grant_busy(flags, g, util or {}, occ if occ is not None else gpu_occupancy())[0]
            except Exception:  # noqa: BLE001 - unknown device state never ends a grant
                gpu_busy = True
        if busy_child or region_busy or gpu_busy or not (qs or GPU in g["holds"]):
            e["alerted"] = None   # working again: a later idle spell alerts afresh
            continue
        e["n"] = int(prev.get("n") or 0) + 1
        e["since"] = prev.get("since") or prev["t"]   # the quiet spell began at the baseline sample before this one
        owner = str(row.get("owner") or "")
        why = (f"launcher pid {pid} alive, {len(cpu)} descendant(s) none > {IDLE_CRASH_CHILD_PCT:g}% CPU, regions "
               f"{','.join(sorted(g['holds']))} ~0% busy")
        quiet_s = int(now - float(e["since"]))
        if e["n"] < IDLE_CRASH_SAMPLES or quiet_s < IDLE_CRASH_ACT_S:
            if e["n"] >= IDLE_CRASH_SAMPLES and not e["alerted"]:
                e["alerted"] = now
                log(f"IDLE-AFTER-CRASH-PENDING {rid}: {why} for {quiet_s}s; the grant ends after {IDLE_CRASH_ACT_S}s of this")
                try:
                    emit(flags, "idle-after-crash-pending", rid, g.get("start") or "", f"IDLE-AFTER-CRASH pending {rid}: {why}; "
                         f"the keeper ends the grant (STOP file, rc=75) if it stays so for {IDLE_CRASH_ACT_S // 60} min", "warning", owner,
                         {"pid": pid, "holds": sorted(g["holds"]), "logs": dry_dir(flags, rid)})
                except Exception as ex:  # noqa: BLE001
                    log(f"IDLE-AFTER-CRASH {rid}: notify failed: {type(ex).__name__}: {ex}")
            out.append((rid, "pending" if e["n"] >= IDLE_CRASH_SAMPLES else "quiet"))
            continue
        if not act:
            out.append((rid, "would-end"))
            continue
        sf = resolve_stop_path(row)
        if not sf:
            log(f"IDLE-AFTER-CRASH-REFUSED {rid}: {why}; its stop file is unknown - alerted only")
            out.append((rid, "no-stop-file"))
            continue
        try:
            os.makedirs(os.path.dirname(sf), exist_ok=True)
            with open(sf, "a") as f:
                f.write(json.dumps({"by": "rowflow idle-after-crash", "at": now_iso(), "reason": "idle-after-crash", "pid": pid}) + "\n")
        except OSError as ex:
            log(f"IDLE-AFTER-CRASH {rid}: stop file {sf} not written: {ex}")
            continue
        e["ended"] = now
        log(f"IDLE-AFTER-CRASH {rid}: {why} for {e['n']} samples; touched STOP {sf} (engine ends it rc=75 reason=idle-after-crash)")
        try:
            emit(flags, "idle-after-crash", rid, g.get("start") or "", f"IDLE-AFTER-CRASH {rid}: grant ended ({why}); the "
                 f"engine writes .ended rc=75; remove {sf} and republish to re-queue", "critical", owner,
                 {"pid": pid, "stop_file": sf, "reason": "idle-after-crash"})
        except Exception as ex:  # noqa: BLE001
            log(f"IDLE-AFTER-CRASH {rid}: notify failed: {type(ex).__name__}: {ex}")
        out.append((rid, "ended"))
    try:
        atomic_json(sp, nst)
    except OSError as ex:
        log(f"IDLE-AFTER-CRASH state write failed ({sp}): {ex}")
    return out


# ---------------------------------------------------------------- F7 (AK audit B7): builds are a lane; contamination names the offender
BUILD_PREFIX = "build-"
BUILD_MAX_MINUTES = 120
BUILD_MAX_CPUS = 24
CONTAM_PCT = 20.0          # a foreign process above this CPU % on a held quarter is contamination
CONTAM_SAMPLES = 2         # consecutive samples before CONTAMINATION.json + the owner alert


def _session_env(pid):
    """The CLAUDE/CODEX session hints in a pid's environment, when readable (same uid only)."""
    try:
        env = open(f"/proc/{int(pid)}/environ", "rb").read().split(b"\0")
    except (OSError, ValueError):
        return None
    keep = {}
    for kv in env:
        k, _, v = kv.decode(errors="replace").partition("=")
        if k in ("FILLER_ID", "CLAUDE_SESSION_ID", "CODEX_SESSION_ID", "EPYC_AGENT_ID", "EPYC_SESSION") and v:
            keep[k] = v[:80]
    return keep or None


def _cmdline(pid):
    try:
        return open(f"/proc/{int(pid)}/cmdline", "rb").read().replace(b"\0", b" ").decode(errors="replace").strip()
    except (OSError, ValueError):
        return ""


def record_build_wait(flags, owner, now=None, pid=None):
    """A refused `claim --build` leaves a build-wait record (TTL waiter_ttl_s, removed when the owner's next claim succeeds): the planner stops booking long
    undeclared q0-q2 rows over the pocket while it lives (BUILD-POCKET)."""
    now = time.time() if now is None else now
    # The claim CLI exits at once, so its own pid is dead before the planner reads the record: the claimant is the invoking
    # process (parent shell/agent) unless --wait-pid names one. pid was hardcoded None before (2026-11-20 stale autokernel-probe).
    pid = int(pid) if pid else os.getppid()
    d = os.path.join(flags, BUILD_WAIT_DIR); os.makedirs(d, exist_ok=True)
    atomic_json(os.path.join(d, f"{owner}.json"), {"owner": owner, "pid": pid, "at_epoch": now, "at": now_iso()})


def free_cores(q, free):
    """Physical-core tokens of quarter q that are free in this snapshot, ascending (a partly-held quarter: the unheld cores)."""
    return sorted((c for c in qcores(q) if c in free), key=lambda c: int(c[1:]))


def partial_tokens(cores, free):
    """Core tokens plus their SMT-sibling thread tokens that are also free (a sibling a smoke/other row holds is left out)."""
    return set(cores) | {f"t{int(c[1:]) + 96}" for c in cores if f"t{int(c[1:]) + 96}" in free}


# Q3-POCKET BUILD (AK 2026-11-21, D9 standing AK ack): build-autokernel-20261121T033012Z took all of q3 and held 88-95/184-191
# (the MI210 host threads), so queued GPU rows waited while q0-q2 sat behind long CPU timing rows. A build may instead take the
# q3 POCKET = cores 72-87 + SMT siblings 168-183 (exactly COEXIST_Q3, the cores gpu-q3 NARROW never gives a GPU grant): never
# 88-95 / 184-191, never gpu-quiet. Beside a GPU grant (holds gpu-quiet + 88-95 + 184-191) and beside a GPU TIMING grant alike -
# the same rule subquarter q3 rows already follow (NARROW: 72-87 stay grantable beside a GPU timing run).
BUILD_Q3_POCKET_CORES = 16
BUILD_GPU_HOST_CPUS = frozenset(range(88, 96)) | GPU_HOST_THREADS


def build_cpu_set(s):
    return {x for x in _cpu_set(s)}


def q3_pocket_claim(flags, free, n, want=None):
    """Tokens (cores + free SMT siblings) of a q3-pocket build, or None. n: first n free pocket cores; want: the explicit core
    tokens (all must be free). Never returns a token outside COEXIST_Q3."""
    pocket = sorted((c for c in COEXIST_Q3 if c.startswith("c") and c in free), key=lambda c: int(c[1:]))
    cores = sorted(want, key=lambda c: int(c[1:])) if want else pocket[:n]
    if not cores or (want and not set(want) <= set(pocket)) or (not want and len(cores) < n):
        return None
    toks = partial_tokens(cores, free) & COEXIST_Q3
    return toks if toks >= set(cores) else None


# LIGHT TEST CLAIM (AutoKernel approved 2026-11-23): `claim --build --light` - a tiny, short, single-process test lane on cores
# 84-87 that is NOT bandwidth-heavy, so it never blocks or delays a quiet row (quiet_gate skips it; the PM-KEEPER3 and QUIET-RESERVE
# build refusals do not apply to it). The advisory rules below are not enforced; they are the contract and are printed with the grant.
LIGHT_CORES = frozenset(range(84, 88))
LIGHT_MAX_CPUS = 4
LIGHT_MAX_MINUTES = 15
LIGHT_CONTENDED_WINDOW_S = 600
LIGHT_ADVISORY = ("prefix commands with `nice -n 19 taskset -c <granted cpus>`", "run single-process pytest",
                  "no model or GGUF loads", "no compiles, prebuilt only")


def is_light_build(flags, gid):
    """True when grants/<gid>.build.json records bandwidth_class: light (a LIGHT test claim)."""
    if not flags or not str(gid).startswith(BUILD_PREFIX):
        return False
    return (load_json(os.path.join(flags, "grants", gid + ".build.json")) or {}).get("bandwidth_class") == "light"


def _keeper_log_line(flags, line):
    try:
        with open(os.path.join(flags, "ws58-calendar-keeper.log"), "a") as f:
            f.write(f"{now_iso()} {line}\n")
    except OSError:
        pass


def contended_try_age(flags, rid, d, now):
    """Seconds since the newest contended-launch marker a RUNNING quiet row wrote (AutoKernel ak_row_harness.run_quiet appends
    a JSON line with `utc` to <out_dir>/contended.jsonl on every contended try), or None. Looked for beside the row's
    result_path, its launcher dir and their out/ subdirs."""
    dirs = []
    rp = str((d or {}).get("result_path") or "").split("*")[0]
    if rp:
        dirs.append(rp if rp.endswith("/") else os.path.dirname(rp))
    lp = str(((d or {}).get("launcher") or {}).get("path") or "")
    if lp:
        dirs.append(os.path.dirname(lp))
    newest = None
    seen = set()
    for base in dirs:
        for pat in ("contended.jsonl", "*/contended.jsonl", "out/*/contended.jsonl"):
            for f in glob.glob(os.path.join(base, pat)):
                if f in seen:
                    continue
                seen.add(f)
                ts = None
                try:
                    for line in reversed(tail(f, 20)):
                        try:
                            u = json.loads(line).get("utc")
                        except (ValueError, AttributeError):
                            continue
                        if u:
                            ts = iso_epoch(u)
                            break
                    if ts is None:
                        ts = os.path.getmtime(f)
                except (OSError, ValueError, TypeError):
                    continue
                newest = ts if newest is None else max(newest, ts)
    return None if newest is None else now - newest


def _claim_light_locked(flags, owner, cpus, minutes, log=print, now=None, grants=None, allrows=None, free=None):
    """LIGHT claim (see LIGHT TEST CLAIM). Refusals raise Refused('LIGHT-REFUSED <reason>') and are logged to the keeper log."""
    def refuse(why):
        msg = f"LIGHT-REFUSED {why}"
        _keeper_log_line(flags, msg)
        raise Refused(msg)
    need(owner and re.fullmatch(r"[\w.-]+", owner), "claim --build --light needs --owner <roster id>")
    if not isinstance(minutes, int) or not 1 <= minutes <= LIGHT_MAX_MINUTES:
        refuse(f"--minutes {minutes}: a light claim is 1..{LIGHT_MAX_MINUTES} minutes")
    s = str(cpus).strip()
    if not re.fullmatch(r"\d+(-\d+)?(,\d+(-\d+)?)*", s):
        refuse(f"--cpus {s!r}: a light claim names a cpu list within 84-87")
    cset = build_cpu_set(s)
    if not cset <= LIGHT_CORES:
        refuse(f"--cpus {s} names {compress_cpus(cset - LIGHT_CORES)} outside cores 84-87 (a light claim never leaves 84-87)")
    if len(cset) > LIGHT_MAX_CPUS:
        refuse(f"--cpus {s} is {len(cset)} cores; a light claim is at most {LIGHT_MAX_CPUS}")
    grants = open_grants(flags) if grants is None else grants
    allrows = rows(flags) if allrows is None else allrows
    t_now = time.time() if now is None else now
    held = [g["id"] for g in grants if is_light_build(flags, g["id"])]
    if held:
        refuse(f"another light claim is open ({held[0]}); one light claim at a time host-wide")
    for g in grants:   # AutoKernel run_quiet rejects contended launches and retries after 90 s: a marker < 10 min old = hands off
        if g["id"].startswith(BUILD_PREFIX):
            continue
        d = allrows.get(g["id"]) or load_json(ready_path(flags, g["id"])) or {}
        if not quiet_required(d) or set(QUARTERS) <= (g.get("holds") or set()) or str(d.get("shape") or "") in ("host", "quiet-host"):
            continue   # whole-host / quiet-host grants already refuse everything through the core-overlap check below
        age = contended_try_age(flags, g["id"], d, t_now)
        if age is not None and age < LIGHT_CONTENDED_WINDOW_S:
            refuse(f"running quiet row {g['id']} logged a contended launch attempt {age:.0f}s ago "
                   f"(< {LIGHT_CONTENDED_WINDOW_S // 60} min); its run_quiet is retrying - retry later")
    if free is None:
        _, free, _ = host_snapshot(flags, grants)
    wc = {f"c{x}" for x in cset}
    miss = sorted(wc - free)
    if miss:
        by = sorted({g["id"] for g in grants if g["holds"] & expand(set(miss))})
        refuse(f"cores {compress_cpus({int(c[1:]) for c in miss})} are held by {', '.join(by) or 'another job'}")
    part = partial_tokens(wc, free)
    want_tokens = expand(set(part))
    for g in open_grants(flags):   # on-disk truth under the claim lock
        both = want_tokens & expand(g["holds"])
        if both:
            refuse(f"{compress_cpus({int(x[1:]) % 96 for x in both if x[0] in 'ct'})} already held by {g['id']}")
    t = dt.datetime.now(dt.timezone.utc) if now is None else dt.datetime.fromtimestamp(now, dt.timezone.utc)
    gid = _new_build_id(flags, owner, t)
    cl = tokens_cpus(part)
    line = write_grant(flags, gid, cl, set(part), minutes * 60)
    rec = {"id": gid, "owner": owner, "kind": "build", "bandwidth_class": "light", "quarters": ["q3"], "cpus": cl,
           "minutes": minutes, "at": now_iso(), "partial": sorted(part), "pocket": "q3", "taskset_cpus": compress_cpus(cset)}
    atomic_json(os.path.join(flags, "grants", gid + ".build.json"), rec)
    quiet = sorted(g["id"] for g in grants if not g["id"].startswith(BUILD_PREFIX)
                   and quiet_required(allrows.get(g["id"]) or load_json(ready_path(flags, g["id"])) or {}))
    msg = f"LIGHT-CLAIM {gid} cpus={compress_cpus(cset)} beside quiet {','.join(quiet) or '-'}"
    _keeper_log_line(flags, msg)
    log(msg)
    log(f"LIGHT-GRANT {gid}: cores {compress_cpus(cset)} for {minutes} min (owner={owner}, bandwidth_class=light). Advisory, not enforced: "
        + "; ".join(a.replace("<granted cpus>", compress_cpus(cset)) for a in LIGHT_ADVISORY))
    return gid, line


def claim_build(flags, owner, cpus, minutes, log=print, now=None, grants=None, allrows=None, free=None, wait_pid=None, light=False):
    """CLAIM-ID 2026-11-21 (AK, D9 standing ack): two concurrent `claim --build --cpus 72-87` calls in the same UTC second both
    read the same free snapshot, both passed the checks, both minted build-<owner>-<second> and the second write_grant
    os.replace()d the first's grant: one id, two claimants, and the first release freed cores the second was still building on.
    Now the whole claim (snapshot -> overlap check -> grant write) runs under one flock (grants/.claim.lock), the id carries a
    random suffix and is created O_EXCL, and the tokens are re-checked against the on-disk grants so a stale injected snapshot
    cannot double-book. See _claim_build_locked for the claim itself."""
    G = os.path.join(flags, "grants")
    os.makedirs(G, exist_ok=True)
    fd = os.open(os.path.join(G, ".claim.lock"), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)   # blocking: claims are short; serialising them is the point
        if light:
            return _claim_light_locked(flags, owner, cpus, minutes, log, now, grants, allrows, free)
        try:
            r = _claim_build_locked(flags, owner, cpus, minutes, log, now, grants, allrows, free, wait_pid)
        except Refused:
            try:
                record_build_refusal(flags, owner, cpus, now)
            except Exception:  # noqa: BLE001 - bookkeeping never changes the refusal
                pass
            raise
        try:
            clear_build_refusal(flags, owner, cpus)
        except Exception:  # noqa: BLE001
            pass
        return r
    finally:
        os.close(fd)   # closing releases the flock


def _new_build_id(flags, owner, t):
    """build-<owner>-<UTC second>-<6 hex>, reserved by creating grants/<id>.build.json with O_EXCL (retry on a collision)."""
    for _ in range(50):
        gid = f"{BUILD_PREFIX}{owner}-{t:%Y%m%dT%H%M%SZ}-{os.urandom(3).hex()}"
        try:
            os.close(os.open(os.path.join(flags, "grants", gid + ".build.json"), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644))
        except FileExistsError:
            continue
        if os.path.exists(os.path.join(flags, "grants", gid + ".grant")):
            continue
        return gid
    raise Refused("BUILD-REFUSED: could not mint a unique build grant id")


def _claim_build_locked(flags, owner, cpus, minutes, log=print, now=None, grants=None, allrows=None, free=None, wait_pid=None):
    """`rowflow.py claim --build`: a short `build` grant (--cpus 72-87 or a count that finds no q0-q2 room = the q3 pocket, never
    88-95/184-191, never gpu-quiet; see Q3-POCKET BUILD) (grants/build-<owner>-<ts>.grant, holds one quarter) so a build
    is a lane the planner sees instead of contamination. cpus = a count (<= 24: the first whole-free quarter q0-q2)
    or a literal cpu list (its quarters). Refused - naming the grant - when it would overlap a timing grant's quarters,
    or any held quarter. Returns (grant id, line)."""
    need(owner and re.fullmatch(r"[\w.-]+", owner), "claim --build needs --owner <roster id>")
    need(isinstance(minutes, int) and 1 <= minutes <= BUILD_MAX_MINUTES, f"--minutes must be 1..{BUILD_MAX_MINUTES}")
    grants = open_grants(flags) if grants is None else grants
    allrows = rows(flags) if allrows is None else allrows
    if free is None:
        _, free, _ = host_snapshot(flags, grants)
    # PM-KEEPER3 (AK reverse case): a build claim is bandwidth-heavy and DRAM contention is host-wide, so no build claim
    # starts while a requires_quiet_host row runs anywhere (the same rule quiet_gate applies the other way)
    qrun = [g["id"] for g in grants if not g["id"].startswith(BUILD_PREFIX)
            and quiet_required(allrows.get(g["id"]) or load_json(ready_path(flags, g["id"])) or {})]
    need(not qrun, f"BUILD-REFUSED: quiet-host row {','.join(qrun)} is running (DRAM-wide quiet needed); a build claim is "
                   "bandwidth-heavy - retry when it ends")
    lane, _lk = build_lane_open(flags, now)
    qres_rows = [] if lane else quiet_reserve_blocks_build(flags)   # BUILD LANE: the reserve stops refusing builds
    if lane:
        _keeper_log_line(flags, f"BUILD-LANE open for {lane}: QUIET-RESERVE does not refuse build claim {owner} {cpus}")
    need(not qres_rows, f"BUILD-REFUSED: QUIET-RESERVE - quiet-host row(s) {','.join(qres_rows)} wait for a quiet host; a build claim is "
                        f"bandwidth-heavy - retry when they run (reserve self-releases after {quiet_reserve_max_s(flags) / 60:.0f} min)")
    tq = timing_quarters(flags, [g for g in grants if not g["id"].startswith(BUILD_PREFIX)], allrows)
    holder = {q: g["id"] for g in grants for q in QUARTERS if q in g["holds"] or g["holds"] & qcores(q)}
    s = str(cpus).strip()
    part = None   # PARTIAL-QUARTER: core (+free sibling) tokens a build holds inside a quarter other grants hold only in part
    if re.fullmatch(r"\d+", s):
        n = int(s)
        need(1 <= n <= BUILD_MAX_CPUS, f"--cpus {n}: a build lane is at most one quarter ({BUILD_MAX_CPUS} cores)")
        pick = [q for q in QUARTERS[:3] if q in free and q not in tq]
        if not pick:   # a quarter held only in part still has free cores: take n of them, never the whole quarter
            for q in QUARTERS[:3]:
                fc = free_cores(q, free)
                if q not in tq and len(fc) >= n:
                    part = partial_tokens(fc[:n], free); pick = [q]; break
        if not pick and n <= BUILD_Q3_POCKET_CORES:   # q0-q2 have no pocket: the q3 pocket 72-87 (never 88-95), beside GPU grants
            tg = timing_quarters(flags, [g for g in grants if not g["id"].startswith(BUILD_PREFIX) and g["holds"] & COEXIST_Q3], allrows)
            part = None if tg else q3_pocket_claim(flags, free, n)
            if part:
                pick = ["q3"]
        if not pick:   # BUILD-POCKET: remember the unmet claim so the planner leaves the next pocket for it
            record_build_wait(flags, owner, now, wait_pid)
        need(pick, f"no whole-free quarter q0-q2 and none with >= {n} free cores for a build now (" + ", ".join(
             f"{q}: {holder.get(q, 'busy')}" + (" [timing]" if q in tq else "") for q in QUARTERS[:3])
             + "); retry later, never run it unclaimed")
        qs = [pick[0]]
    else:
        need(re.fullmatch(r"\d+(-\d+)?(,\d+(-\d+)?)*", s), f"--cpus {s!r}: a count or a literal cpu list")
        bad = build_cpu_set(s) & BUILD_GPU_HOST_CPUS
        need(not bad, f"BUILD-REFUSED: --cpus {s} names {compress_cpus(bad)}, the MI210 host threads (cores 88-95 / 184-191); a build "
                      "never books them or gpu-quiet. Use the q3 pocket --cpus 72-87 (siblings 168-183 come with it)")
        qs = sorted(quarters_of(s, fold=True))
        need(len(qs) == 1, f"--cpus {s} spans {qs or 'no quarter'}; a build lane is one quarter")
        if qs == ["q3"]:
            # q3 is never booked whole by a build: only the pocket, whatever the list says (a pocket list is 72-87 / 168-183 cores)
            wc = {f"c{x % 96}" for x in _cpu_set(s)}
            need(wc <= COEXIST_Q3, f"BUILD-REFUSED: --cpus {s} is not inside the q3 pocket 72-87 (+168-183)")
            miss = sorted(wc - free)
            need(not miss, f"BUILD-REFUSED: q3 pocket cores {compress_cpus({int(c[1:]) for c in miss})} are held by "
                           f"{', '.join(sorted({g['id'] for g in grants if g['holds'] & set(miss)})) or 'another job'}")
            tg = timing_quarters(flags, [g for g in grants if not g["id"].startswith(BUILD_PREFIX) and g["holds"] & COEXIST_Q3], allrows)
            need(not tg, f"BUILD-REFUSED: a timing grant holds q3 pocket cores; a build there would perturb its measurement")
            part = q3_pocket_claim(flags, free, 0, want=wc)
            need(part, f"BUILD-REFUSED: q3 pocket {s} is not free")
        elif qs[0] not in free and qs[0] not in tq and free_cores(qs[0], free):   # held in part: the listed cores must be free
            want = {t for t in cpu_tokens(s) if t in CORES or t in THREADS}
            miss = sorted(want - free)
            if want and not miss:
                part = want
    pocket = bool(part) and qs == ["q3"]   # a q3-pocket build holds only 72-87/168-183: a GPU timing grant's 88-95 is not its quarter
    for q in qs:
        need(pocket or q not in tq, f"BUILD-REFUSED: {q} is held by timing grant {holder.get(q, '?')}; a build there would perturb "
                          "its measurement. Pick another quarter (or --cpus N to let the keeper pick)")
        need(part or q in free, f"BUILD-REFUSED: {q} is held by {holder.get(q, 'another job')}; pick a free quarter")
    t = dt.datetime.now(dt.timezone.utc) if now is None else dt.datetime.fromtimestamp(now, dt.timezone.utc)
    want_tokens = expand(set(part) if part else set(qs))
    for g in open_grants(flags):   # on-disk truth, under the claim lock: a held core is never booked twice
        both = want_tokens & expand(g["holds"])
        need(not both, f"BUILD-REFUSED: {compress_cpus({int(x[1:]) % 96 for x in both if x[0] in 'ct'}) or ','.join(sorted(both))} "
                       f"already held by {g['id']}; a second claim on the same cores is refused while it holds them")
    gid = _new_build_id(flags, owner, t)
    _rm(os.path.join(flags, BUILD_WAIT_DIR, f"{owner}.json"))
    if part:   # core-granular hold: explicit cpus + core/thread tokens, so the rest of the quarter stays claimable
        cl = tokens_cpus(part)
        line = write_grant(flags, gid, cl, set(part), minutes * 60)
        need(not pocket or set(part) <= COEXIST_Q3, "BUILD-REFUSED: internal: a q3-pocket build would hold tokens outside 72-87/168-183")
    else:
        cl = ",".join(cpu_list(q) for q in qs)
        line = write_grant(flags, gid, ",".join(qs), set(qs), minutes * 60)
    rec = {"id": gid, "owner": owner, "kind": "build", "quarters": qs, "cpus": cl,
           "minutes": minutes, "at": now_iso(), **({"partial": sorted(part)} if part else {}), **({"pocket": "q3"} if pocket else {})}
    atomic_json(os.path.join(flags, "grants", gid + ".build.json"), rec)
    log(f"BUILD-GRANT {gid}: {','.join(qs)} for {minutes} min (owner={owner}); run it pinned: taskset -c {rec['cpus']} ...")
    return gid, line


def reap_build_grants(flags, now=None, log=print):
    """Build grants past their end= are ended (grants/<id>.ended rc=0 reason=build-window) so their quarter frees.
    A build grant has no engine and no pid: nothing else would ever end it."""
    now = time.time() if now is None else now
    out = []
    for g in glob.glob(os.path.join(flags, "grants", BUILD_PREFIX + "*.grant")):
        gid = os.path.basename(g)[:-6]
        kv = dict(re.findall(r"(\w+)=(\S+)", head1(g) or ""))
        end = iso_epoch(kv.get("end")) if kv.get("end") else None
        if end is not None and now < end:
            continue
        with open(os.path.join(flags, "grants", gid + ".ended"), "w") as f:
            f.write(f"rc=0 time={now_iso()} reason=build-window\njob_id={gid}\n")
        _rm(g)
        log(f"BUILD-END {gid}: window over; quarter released")
        out.append(gid)
    return out


def release_grant(flags, rid, by, reason, regions=None, log=print, now=None, ended_reason="released-early"):
    """`rowflow.py release <id> --by <owner> --reason R [--regions q2,q1]`: the OWNER ends an idle/finished grant early (or
    shrinks it to the quarters it keeps) so the regions free on the keeper's next tick. Refused unless by == the row owner
    (ready manifest `owner`; a build grant: its build.json owner) and the job is NOT running: an engine/dry-run pid that is
    alive (a zombie is dead) refuses - a running job is never killed (preemption is by drain only). A grant whose job has not
    started may be released: the row's STOP file is touched so its armed poller exits. Whole release: grants/<id>.ended
    `rc=75 reason=released-early`, .grant renamed .grant.released-early, GRANT-RELEASED logged. Partial (`regions` = quarters
    the grant holds, not all): the .grant is rewritten to the remaining quarters (build.json follows).
    Returns RELEASED | SHRUNK. Raises Refused."""
    G = os.path.join(flags, "grants")
    gp = os.path.join(G, rid + ".grant")
    reason = re.sub(r"\s+", "_", str(reason or "").strip())
    by = str(by or "").strip()
    need(reason, "release: --reason is required")
    need(by, "release: --by <owner> is required (or EPYC_AGENT_ID in the environment)")
    need(not any(os.path.exists(os.path.join(G, rid + t)) for t in (".ended", ".complete")),
         f"release {rid}: already ended (grants/{rid}.ended|.complete); nothing to release")
    need(os.path.exists(gp), f"release {rid}: no open grant (grants/{rid}.grant)")
    bj = load_json(os.path.join(G, rid + ".build.json")) or {}
    is_build = rid.startswith(BUILD_PREFIX)
    owner = str(bj.get("owner") or "") if is_build else notify.row_owner(flags, rid)
    need(owner and owner == by, f"release {rid}: owner is {owner or '(unknown)'}, caller is {by or '(none)'}; only the row owner may release")
    g = next((x for x in open_grants(flags) if x["id"] == rid), None)
    need(g is not None, f"release {rid}: grant unreadable")
    pids = [g.get("pid")] + [(load_json(q) or {}).get("pid") for q in (running_path(flags, rid), armed_path(flags, rid))]
    live = [x for x in pids if x and proc_alive(x)]
    need(not ((g["dryrun"] or g["started"]) and live),
         f"release {rid}: job is running (pid {live[0] if live else '?'} alive); never killed - it finishes or drains")
    now_s = now_iso() if now is None else now
    if regions:
        want = {t.strip() for t in str(regions).split(",") if t.strip()}
        held = {q for q in g["holds"] if q in QUARTERS}
        need(want <= held, f"release {rid}: cannot release {','.join(sorted(want - held))}: not a quarter this grant holds "
                           f"({','.join(sorted(held)) or 'none'})")
        keep = sorted(held - want)
        if keep:
            kv = dict(re.findall(r"(\w+)=(\S+)", head1(gp)))
            cpus = ",".join(f"{int(q[1]) * 24}-{int(q[1]) * 24 + 23},{int(q[1]) * 24 + 96}-{int(q[1]) * 24 + 119}" for q in keep)
            kv.update(regions=",".join(keep), holds=",".join(keep), cpus=cpus)
            line = " ".join(f"{k}={kv[k]}" for k in ("regions", "start", "end", "holds", "cpus", "lock") if k in kv) + "\n"
            with open(gp + ".tmp", "w") as f:
                f.write(line)
            os.replace(gp + ".tmp", gp)
            if bj:
                bj.update(quarters=keep, cpus=cpus)
                atomic_json(os.path.join(G, rid + ".build.json"), bj)
            log(f"GRANT-RELEASED {rid}: shrunk to {','.join(keep)}; released {','.join(sorted(want))} by={by} reason={reason}")
            return "SHRUNK"
    if not is_build:
        sf = resolve_stop_path(load_json(ready_path(flags, rid)) or {})
        if sf:
            try:
                os.makedirs(os.path.dirname(sf), exist_ok=True)
                open(sf, "a").close()
            except OSError as e:
                log(f"GRANT-RELEASE {rid}: could not touch STOP {sf}: {e}")
    with open(os.path.join(G, rid + ".ended"), "w") as f:
        f.write(f"rc=75 time={now_s} reason={ended_reason} by={by} note={reason}\njob_id={rid}\n")
    os.replace(gp, gp + ".released-early")
    log(f"GRANT-RELEASED {rid}: ended by owner {by} reason={reason}; {','.join(sorted(g['holds'] & set(REGIONS))) or '-'} free next tick")
    return "RELEASED"


RESUME_REASONS = ("stopped", "released-early")


def resume_dir(flags):
    return os.path.join(flags, "grants", ".resume")


def _manifest_anywhere(flags, rid):
    """ready/<id>.json, else the same manifest parked under ready/.withdrawn/ or another ready/ subdir -> path or None."""
    for p in [ready_path(flags, rid), os.path.join(withdrawn_dir(flags), rid + ".json")] \
            + sorted(glob.glob(os.path.join(flags, "ready", "*", rid + ".json"))):
        if os.path.isfile(p):
            return p
    return None


def resumable_stopped(flags, rid):
    """(manifest_path, why_not): why_not is None when `rid` is a resumable row whose last end was rc=75 reason=stopped|
    released-early|partial-* (the owner's STOP, an owner release, or a job-declared resumable partial), so `rowflow.py resume` can requeue it in place."""
    G = os.path.join(flags, "grants")
    if os.path.exists(os.path.join(G, rid + ".complete")):
        return None, "grants/<id>.complete: the row finished"
    h = head1(os.path.join(G, rid + ".ended"))
    if not h:
        return None, "no grants/<id>.ended: the row has not ended (a STOP file with no end is `rm`-ed by its owner)"
    m = re.search(r"(?:^|\s)reason=(\S+)", h)
    if not (re.search(r"(^|\s)rc=75(\s|$)", h) and m and (m.group(1) in RESUME_REASONS or m.group(1).startswith("partial-"))):
        # RESUME-PARTIAL 2026-11-21: a job-declared resumable partial (filler_run15: rc=75 reason=partial-native-incomplete) resumes too
        return None, f"last end is not rc=75 reason=stopped|released-early|partial-* ({h[:90]!r})"
    mp = _manifest_anywhere(flags, rid)
    if not mp:
        return None, "no manifest for this id (never published, or removed): publish it"
    d = load_json(mp) or {}
    if not d.get("resumable"):
        return None, "row is not resumable (spec resumable: true): publish a successor id"
    return mp, None


def resume_row(flags, rid, by, reason, log=print, now=None):
    """`rowflow.py resume <id> --by <owner> --reason R`: owner-only requeue of a STOPPED / released-early RESUMABLE row under
    the SAME id. Its grants/<id>.ended (and .grant.released-early) move to grants/.resume/<id>.<ts>.*, the STOP file is
    removed, a FILED receipt of that end is archived to filing-done/.resumed/ (so the next end files again; write_filed is
    create-once), the manifest returns to ready/ and the existing PASS.json makes it grantable at once (no new smoke: the
    dry run already passed for this id). out/ and the job's resume ledger are never touched. Refused unless by == the row
    owner, the end qualifies (resumable_stopped), no job runs, the row is not superseded and PASS.json matches the launcher
    (else publish_row.py re-smokes). Logs ROW-RESUMED <id>. Returns the number of resumes of this id."""
    G = os.path.join(flags, "grants")
    reason = re.sub(r"\s+", "_", str(reason or "").strip())
    by = str(by or "").strip()
    need(reason, "resume: --reason is required")
    need(by, "resume: --by <owner> is required (or EPYC_AGENT_ID in the environment)")
    mp, why = resumable_stopped(flags, rid)
    need(mp, f"resume {rid}: {why}")
    owner = notify.row_owner(flags, rid) or str((load_json(mp) or {}).get("owner") or "")
    need(owner and owner == by, f"resume {rid}: owner is {owner or '(unknown)'}, caller is {by or '(none)'}; only the row owner may resume")
    need(not os.path.exists(os.path.join(G, rid + ".grant")), f"resume {rid}: grants/{rid}.grant is open")
    need(direct_run(flags, rid) is None, f"resume {rid}: a direct run is live")
    run = load_json(running_path(flags, rid))
    need(not (run and alive(run.get("pid"))), f"resume {rid}: a dry run is live (pid {(run or {}).get('pid')})")
    by = superseded_by(flags, rid)
    need(not by, f"resume {rid}: superseded by {by} (SUPERSEDED-BLOCK)")
    d = load_json(mp) or {}
    lp = (d.get("launcher") or {}).get("path") or ""
    p = load_json(pass_path(flags, rid))
    need(p and os.path.isfile(lp) and p.get("launcher_sha256") == sha256(lp),
         f"resume {rid}: no PASS.json matching the current launcher; republish with publish_row.py for a new smoke")
    now_t = time.time() if now is None else now
    ts = dt.datetime.fromtimestamp(now_t, dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rd = resume_dir(flags)
    os.makedirs(rd, exist_ok=True)
    for suf in (".ended", ".grant.released-early"):
        src = os.path.join(G, rid + suf)
        if os.path.exists(src):
            shutil.move(src, os.path.join(rd, f"{rid}.{ts}{suf}"))
    fd = os.path.join(flags, "filing-done")
    if os.path.exists(os.path.join(fd, rid + ".FILED")):
        ar = os.path.join(fd, ".resumed")
        os.makedirs(ar, exist_ok=True)
        for suf in (".FILED", ".verdict.json"):
            if os.path.exists(os.path.join(fd, rid + suf)):
                shutil.move(os.path.join(fd, rid + suf), os.path.join(ar, f"{rid}.{ts}{suf}"))
    sf = resolve_stop_path(d)
    if sf and os.path.exists(sf):
        try:
            os.unlink(sf)
        except OSError as e:
            raise Refused(f"resume {rid}: could not remove STOP {sf}: {e}")
    if mp != ready_path(flags, rid):
        os.makedirs(os.path.dirname(ready_path(flags, rid)), exist_ok=True)
        shutil.move(mp, ready_path(flags, rid))
    hp = os.path.join(rd, rid + ".history.json")
    hist = list((load_json(hp) or {}).get("resumed") or [])
    hist.append({"at": now_iso(), "by": by, "reason": reason})
    atomic_json(hp, {"id": rid, "resumed": hist})
    msg = f"ROW-RESUMED {rid} by={by} reason={reason} ({len(hist)} resume(s)); same id grantable, out/ and the resume ledger kept"
    log(msg)
    try:
        with open(os.path.join(flags, "ws58-calendar-keeper.log"), "a") as f:
            f.write(f"{now_iso()} {msg}\n")
    except OSError:
        pass
    return len(hist)


def contamination_exempt_pids(flags):
    """Review S3: pids never attributed as contamination - the keeper's own tree (this process, its parent keeper loop and
    their descendants) and every smoke harness named in dryrun/*/RUNNING.json or SMOKE-PLACED.json (with its tree)."""
    out = {os.getpid()}
    roots = [os.getpid(), os.getppid()]
    for n in ("RUNNING.json", "SMOKE-PLACED.json"):
        for f in glob.glob(os.path.join(flags, "dryrun", "*", n)):
            d = load_json(f) or {}
            roots += [x for x in (d.get("pid"), d.get("pgid")) if str(x or "").isdigit()]
    for r in roots:
        try:
            out |= {int(r)} | set(harness_tree(int(r), {}))
        except Exception:  # noqa: BLE001
            out.add(int(r))
    return out


def contamination_sample(flags, grants, log, census=None, prev=None, now=None, emit=None):
    """F7: per keeper sample, per quarter a grant holds, foreign processes above CONTAM_PCT CPU (last ran there, not
    the grant's own pids, not a build grant's job). CONTAM_SAMPLES consecutive -> appended to dryrun/<id>/CONTAMINATION.json
    {pid, comm, cmdline[:80], container, session env} and ONE `contamination` alert to the row owner per offender.
    Never kills. census/prev: hostutil.proc_census() results (tests). Returns {rid: [offender pids]} recorded now."""
    now = time.time() if now is None else now
    emit = emit or notify.emit
    sp = os.path.join(state_dir(flags), "contamination.json")
    st = load_json(sp) or {}
    census = hostutil.proc_census() if census is None else census
    prev_c = {int(k): tuple(v) for k, v in (st.get("census") or {}).items()} if prev is None else prev
    dt_s = now - float(st.get("t") or now)
    hits_prev = st.get("hits") or {}
    hits, out = {}, {}
    build_q = {q for g in grants if g["id"].startswith(BUILD_PREFIX) for q in g["holds"] if q in QUARTERS}
    exempt = contamination_exempt_pids(flags)
    if dt_s > 0:
        held = [(g, {q for q in QUARTERS if q in g["holds"]}) for g in grants if not g["id"].startswith(BUILD_PREFIX)]
        for g, qs in held:
            if not qs:
                continue
            try:
                own = own_pids(flags, g)
            except Exception:  # noqa: BLE001
                own = set()
            for pid, (birth, cpu, last, comm) in census.items():
                pv = prev_c.get(pid)
                if pid in own or pid in exempt or not pv or pv[0] != birth:
                    continue
                pct = 100.0 * (cpu - pv[1]) / dt_s
                q = hostutil.quarter_of_cpu(last)
                if pct <= CONTAM_PCT or q not in qs or q in build_q:
                    continue
                key = f"{g['id']}|{pid}|{birth}"
                n = int(hits_prev.get(key, 0)) + 1
                hits[key] = n
                if n != CONTAM_SAMPLES:
                    continue
                rec = {"at": now_iso(), "pid": pid, "comm": comm, "cmdline": _cmdline(pid)[:80], "cpu_pct": round(pct, 1),
                       "quarter": q, "container": pid_container_id(pid), "session_env": _session_env(pid)}
                p = os.path.join(dry_dir(flags, g["id"]), "CONTAMINATION.json")
                os.makedirs(os.path.dirname(p), exist_ok=True)
                cur = load_json(p) or {"id": g["id"], "offenders": []}
                cur["offenders"].append(rec)
                atomic_json(p, cur)
                out.setdefault(g["id"], []).append(pid)
                owner = str((load_json(ready_path(flags, g["id"])) or {}).get("owner") or "")
                log(f"CONTAMINATION {g['id']} {q}: pid {pid} {comm} {rec['cpu_pct']}% ({rec['cmdline']}) container={rec['container']}")
                try:
                    emit(flags, "contamination", g["id"], f"{pid}:{birth}", f"CONTAMINATION on {q} under {g['id']}: pid {pid} "
                         f"`{rec['cmdline']}` at {rec['cpu_pct']}% CPU for {CONTAM_SAMPLES} samples; container {rec['container']}, "
                         f"session {rec['session_env']}; record {p}", "warning", owner, rec)
                except Exception as ex:  # noqa: BLE001
                    log(f"CONTAMINATION {g['id']}: notify failed: {type(ex).__name__}: {ex}")
    try:
        atomic_json(sp, {"t": now, "census": {str(k): list(v) for k, v in census.items()}, "hits": hits})
    except OSError as ex:
        log(f"CONTAMINATION state write failed ({sp}): {ex}")
    return out


QUEUED_AGED_S = 7200   # F9 (AK audit B9): a smoke marker this old with no batch running tells its owner


def queued_aged_alerts(flags, now=None, log=print, emit=None):
    """F9: every dryrun/<id>/{SMOKE,GPU-SMOKE}-QUEUED.json older than QUEUED_AGED_S while no batch serves it (no GPU
    batch running for a GPU marker, no SMOKE-PLACED runner for a CPU one) -> ONE `queued-aged` alert per queueing to the
    row owner (marker spec owner, else the ready/unpublished manifest's). Returns the alerted ids."""
    now = time.time() if now is None else now
    emit = emit or notify.emit
    out = []
    gpu_run = None
    for name in ("SMOKE-QUEUED.json", "GPU-SMOKE-QUEUED.json"):
        for q in glob.glob(os.path.join(flags, "dryrun", "*", name)):
            rid = os.path.basename(os.path.dirname(q))
            d = load_json(q) or {}
            at = iso_epoch(d.get("queued_at")) if d.get("queued_at") else None
            try:
                at = at or os.path.getmtime(q)
            except OSError:
                continue
            if now - at < QUEUED_AGED_S:
                continue
            if name.startswith("GPU"):
                gpu_run = gpu_batch_running(flags) if gpu_run is None else gpu_run
                if gpu_run:
                    continue
            elif proc_alive((load_json(smoke_placed_path(flags, rid)) or {}).get("pid")):
                continue
            owner = str((d.get("spec") or {}).get("owner") or (load_json(ready_path(flags, rid)) or load_json(
                os.path.join(dry_dir(flags, rid), "unpublished.json")) or {}).get("owner") or "")
            h = int((now - at) // 3600)
            disc = str(d.get("queued_at") or int(at))
            try:
                if os.path.exists(notify._marker(flags, notify.event_key("queued-aged", rid, disc))):
                    continue   # already told for this queueing: no per-tick log noise
            except Exception:  # noqa: BLE001
                pass
            try:
                if emit(flags, "queued-aged", rid, disc, f"QUEUED-aged {rid}: its {name[:-5]} "
                        f"marker is {h}h old and no smoke batch has taken it; check `rowflow.py status {rid}` / the keeper log",
                        "warning", owner, {"marker": q, "age_s": int(now - at)}):
                    out.append(rid)
            except Exception as ex:  # noqa: BLE001
                log(f"QUEUED-AGED {rid}: notify failed: {type(ex).__name__}: {ex}")
    if out:
        log(f"QUEUED-AGED {len(out)} marker(s) > {QUEUED_AGED_S // 3600}h: {','.join(out[:8])}; owners alerted")
    return out


ORPHAN_MAX_AGE_S = 7 * 86400   # unpublished.json older than this is never alerted as orphaned


def orphaned_smoke_alerts(flags, log=print, emit=None, now=None, min_age_s=120):
    """B1 (AK audit: a queued smoke is a durable obligation): a dryrun/<id>/unpublished.json (a row waiting for its
    smoke) with NO queued marker, no live RUNNING/SMOKE-PLACED runner, no PASS/FAIL/QUEUED-DROPPED record newer than it
    and no withdrawal means its marker was removed outside PASS/FAIL/withdraw/drop (e.g. by hand). ONE
    `queued-smoke-orphaned` alert to the owner per orphaning; never re-queues on its own. Returns the alerted ids."""
    now = time.time() if now is None else now
    emit = emit or notify.emit
    out = []
    for up in glob.glob(os.path.join(flags, "dryrun", "*", "unpublished.json")):
        dd = os.path.dirname(up)
        rid = os.path.basename(dd)
        try:
            t_up = os.path.getmtime(up)
        except OSError:
            continue
        if now - t_up < min_age_s:
            continue   # a publish/batch in progress moves these files around
        if now - t_up > ORPHAN_MAX_AGE_S:
            continue   # review S3: week-old leftovers (11-01/11-04) are history, not a fresh orphaning
        if any(os.path.exists(os.path.join(dd, n)) for n in ("SMOKE-QUEUED.json", "GPU-SMOKE-QUEUED.json")):
            continue
        if os.path.exists(withdraw_pending_path(flags, rid)) or os.path.exists(os.path.join(withdrawn_dir(flags), rid + ".json")):
            continue
        if any(proc_alive((load_json(os.path.join(dd, n)) or {}).get("pid")) for n in ("RUNNING.json", "SMOKE-PLACED.json")):
            continue
        recs = [os.path.join(dd, "PASS.json")] + glob.glob(os.path.join(dd, "FAIL-*.json")) + glob.glob(os.path.join(dd, "QUEUED-DROPPED-*.json"))
        if any(os.path.exists(r) and os.path.getmtime(r) >= t_up - 1 for r in recs):
            continue
        row = load_json(up) or {}
        disc = str(int(t_up))
        try:
            if os.path.exists(notify._marker(flags, notify.event_key("queued-smoke-orphaned", rid, disc))):
                continue
        except Exception:  # noqa: BLE001
            pass
        try:
            emit(flags, "queued-smoke-orphaned", rid, disc, f"row {rid} waits for its smoke (dryrun/{rid}/unpublished.json) "
                 "but its queued marker is gone with no PASS/FAIL/withdraw/drop record; nothing will run it. Republish "
                 f"(publish_row.py <spec>) or withdraw it (rowflow.py withdraw {rid} --reason ...)", "warning",
                 str(row.get("owner") or ""), {"unpublished": up})
            out.append(rid)
            log(f"QUEUED-SMOKE-ORPHANED {rid}: marker removed outside PASS/FAIL/withdraw/drop; owner alerted")
        except Exception as ex:  # noqa: BLE001
            log(f"QUEUED-SMOKE-ORPHANED {rid}: notify failed: {type(ex).__name__}: {ex}")
    return out


def idle_warn_state_path(flags):
    return os.path.join(state_dir(flags), "idle_held_warn.json")


def idle_held_notify(flags, idle, grants, log, now=None, emit=None, wanted=None):
    """idle = idle_held()'s [(region, rid, pct)] for THIS tick; grants = the open grants. Returns the rids warned this
    tick. Pure bookkeeping + notify.emit; every failure is logged and swallowed (a warning never stops allocation).
    wanted = the queued candidates (allocate's cands): opt-in reclaim acts only when one of them wants the held regions."""
    now = time.time() if now is None else now
    emit = notify.emit if emit is None else emit
    sp = idle_warn_state_path(flags)
    st = load_json(sp) or {}
    open_ids = {g["id"] for g in grants}
    by_rid = {}
    for r, rid, v in idle:
        by_rid.setdefault(rid, []).append((r, v))
    # a grant that is open but not idle this tick (or gone) resets its clock
    st = {rid: e for rid, e in st.items() if rid in by_rid and rid in open_ids and isinstance(e, dict)}
    warned = []
    for rid in sorted(by_rid):
        e = st.setdefault(rid, {"idle_since": now, "warned_at": None, "warn_n": 0})
        idle_s = int(now - float(e.get("idle_since") or now))
        due = idle_s >= IDLE_WARN_AFTER_S and (e.get("warned_at") is None or now - float(e["warned_at"]) >= IDLE_WARN_REPEAT_S)
        regions = ",".join(r for r, _ in sorted(by_rid[rid]))
        pct = max(v for _, v in by_rid[rid])
        g = next((x for x in grants if x["id"] == rid), {})
        holds = ",".join(compress(g.get("holds") or set())) if g else "?"
        if idle_s >= IDLE_ESCALATE_AFTER_S:
            _idle_act(flags, rid, e, regions, pct, idle_s, holds, notify.row_owner(flags, rid), log, emit, wanted)
        if not due:
            continue
        n = int(e.get("warn_n") or 0) + 1
        owner = notify.row_owner(flags, rid)
        summary = (f"IDLE-HELD {regions} {rid}: measured {pct:.0f}% busy for {idle_s}s (warning {n}); the grant holds "
                   f"{holds} while rows queue. The keeper never ends it: check the job (stale lock? hung load?), fix or "
                   f"stop it (its stop file / rowflow.py withdraw); logs {dry_dir(flags, rid)}")
        try:
            mark = emit(flags, "idle-held", rid, f"{regions}:{n}", summary, "warning", owner,
                        {"regions": regions, "busy_pct": round(float(pct), 1), "idle_s": idle_s, "warning_n": n,
                         "repeat_s": IDLE_WARN_REPEAT_S, "holds": holds, "logs": dry_dir(flags, rid),
                         "fix_task": f"{rid} holds {holds} at {pct:.0f}% busy for {idle_s}s: unstick or stop the job"})
        except Exception as ex:  # noqa: BLE001 - notification never blocks allocation
            log(f"IDLE-HELD-WARN {regions} {rid}: notify failed: {type(ex).__name__}: {ex}")
            continue
        key = (mark or {}).get("record", {}).get("key") if isinstance(mark, dict) else None
        e.update(warned_at=now, warn_n=n)
        warned.append(rid)
        log(f"IDLE-HELD-WARN {regions} {rid}: {pct:.0f}% busy for {idle_s}s; warning {n} sent to owner={owner or FALLBACK_OWNER} "
            f"(repeat >= {IDLE_WARN_REPEAT_S}s) key={key or '-'}; logs {dry_dir(flags, rid)}")
    try:
        atomic_json(sp, st)
    except OSError as ex:
        log(f"IDLE-HELD-WARN state write failed ({sp}): {ex}")
    return warned


FALLBACK_OWNER = notify.FALLBACK_ASSIGNEE


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
        busy |= cpu_tokens(ws58_cpus(g.get("regions")), gpu_threads=True) & POCKET_TOKENS   # explicit sibling cpus (48-95,144-191)
        for r in g["holds"]:
            if r in REGIONS:
                holders.setdefault(r, g["id"])
    busy |= live_smoke_tokens(flags)
    busy |= {q for q in QUARTERS if expand({q}) & busy}   # a quarter with any held core/thread is not whole-free
    free = (set(REGIONS) | set(CORES) | set(THREADS)) - busy
    return busy, free, holders


# ---------------------------------------------------------------- keeper-scheduled smokes (operator 2026-11-05)
SMOKE_CPUS = 4
SMOKE_CPUS_MAX = 24   # D9 2026-11-18: spec smoke_cpus range is SMOKE_CPUS..SMOKE_CPUS_MAX; MAX may take a whole free quarter
# SMOKE POCKETS (pipeline audit 2026-11-10 #5, operator scope "Scheduling model"): per quarter, the 4 SMT siblings of its
# last 4 physical cores (q0 c20-23 -> t116-119, q1 t140-143, q2 t164-167). A whole-quarter grant never runs on them
# (grant_cpus: a-(a+23),(a+96)-(a+111)), so a pocket costs a quarter booking nothing; sub-quarter rows lose the one 4-core
# block under each pocket. q3 has none: its last 8 siblings are the MI210 host threads (GPU_HOST_THREADS).
SMOKE_POCKETS = {"q0": range(116, 120), "q1": range(140, 144), "q2": range(164, 168)}
POCKET_TOKENS = frozenset(f"t{n}" for r in SMOKE_POCKETS.values() for n in r)


def timing_quarters(flags, grants, allrows):
    """Quarters an open bench/timing grant holds any core of: their pockets stay empty (a smoke on the siblings would
    perturb the measurement). An unparsable row counts as timing (never risk a measurement)."""
    out = set()
    for g in grants:
        d = allrows.get(g["id"])
        try:
            bench = bool(contract_of(d, flags=flags)["bench"]) if d else False
        except Exception:  # noqa: BLE001
            bench = True
        if bench:
            out |= {q for q in QUARTERS if q in g["holds"] or g["holds"] & qcores(q)}
    return frozenset(out)
def drain_live(state, now=None):
    """drain_state.json entries whose T is still ahead ({row id: T})."""
    now = time.time() if now is None else now
    out = {}
    for k, v in (state or {}).items():
        try:
            if float(v) > now:
                out[k] = float(v)
        except (TypeError, ValueError):
            continue
    return out


def drain_state_next(last_drain, drain_prev, live_ids, assigned_ids, now=None):
    """PM-DRAINFIX 2026-11-22: the drain state persisted for the next tick. The planner's drain when it formed one;
    otherwise a previous drain is CARRIED while its T is ahead and its row is still waiting (a candidate or a
    WAIT-FOR-SMOKE row, not granted this tick). It was overwritten with {} on every tick without a drain (DRAIN-HELD,
    WAIT-FOR-SMOKE, a placed row), so the next drain recomputed T from the latest backfill end and slid later."""
    if last_drain:
        return {last_drain[0]["id"]: float(last_drain[1])}
    live, done = set(live_ids), set(assigned_ids)
    return {k: v for k, v in drain_live(drain_prev, now).items() if k in live and k not in done}


def quiet_host_drain_target(cands, drain_prev):
    """The quiet-host candidate the planner is draining for (drain_state.json), or None."""
    for c in cands:
        if c.get("shape") == "quiet-host" and c["id"] in (drain_prev or {}):
            return c["id"]
    return None


def quiet_host_smoke_live(flags, placed=()):
    """QUIET-HOST-SMOKE (2026-11-12, inf45-e5v2-stageb-r2 vs agg13-reingest-cpu-r2): pocket smokes sit on SMT siblings
    OUTSIDE every quarter token, so a quiet-host grant (holds q0-q3 + gpu-quiet) never saw them and was issued in the
    same tick a smoke was placed; its harness then refused the smoke's llama-servers. Ids of smokes placed this tick or
    still live (RUNNING.json / SMOKE-PLACED.json with a live pid); any -> no quiet-host grant this tick."""
    out = [rid for rid, _ in placed]
    for pat in ("RUNNING.json", "SMOKE-PLACED.json"):
        for p in glob.glob(os.path.join(flags, "dryrun", "*", pat)):
            r = load_json(p) or {}
            rid = os.path.basename(os.path.dirname(p))
            if r.get("pid") and alive(r["pid"]) and rid not in out:
                out.append(rid)
    return out


# E5 starvation fix A (2026-11-23, inf45-e5v2-stageb-r8-20261122): an orphaned llama-server (pid 2003761, :8080, launcher
# dead) ran outside every grant; the keeper granted E5 the whole host 4 times (23:22Z-04:35Z) and each time the row's
# clean-runtime gate refused ("existing llama processes would contaminate P-BENCH-3"), burning its auto-requeues. A
# quiet-host / whole-host row is now never granted while an inference server runs that no open grant, no live smoke
# and no orchestrator-stack service owns. Detection only: never kills (the stack, or the owner, decides).
INFER_SERVER_RE = re.compile(r"^(llama-server|sd-server|whisper[\w.-]*)$")
STACK_STATE_FILE = os.environ.get("ROWFLOW_STACK_STATE", "/mnt/raid0/llm/epyc-orchestrator/logs/orchestrator_state.json")
FOREIGN_GATE_SHAPES = ("quiet-host", "host")


def inference_server_procs(proc=None):
    """[{pid, ppid, pgid, birth, comm, cmd}] for every live llama-server / sd-server / whisper* process on the host.
    ROWFLOW_INFER_SCAN_ROOT replaces /proc (the test suite points it at an empty dir: a test never sees live servers)."""
    proc = proc or os.environ.get("ROWFLOW_INFER_SCAN_ROOT") or "/proc"
    out = []
    try:
        names = os.listdir(proc)
    except OSError:
        return out
    for q in names:
        if not q.isdigit():
            continue
        try:
            comm = open(f"{proc}/{q}/comm").read().strip()
        except OSError:
            continue
        if not INFER_SERVER_RE.match(comm):
            continue
        st = _proc_stat(int(q))
        if not st:
            continue
        out.append({"pid": int(q), "ppid": st[0], "pgid": st[1], "birth": st[2], "comm": comm, "cmd": _cmdline(q)})
    return out


def stack_service_pids(path=None):
    """{pid: port|None} of every service the orchestrator stack registered (its state file); {} when unreadable."""
    d = load_json(path or STACK_STATE_FILE) or {}
    out = {}
    for v in (d.values() if isinstance(d, dict) else ()):
        if isinstance(v, dict) and str(v.get("pid") or "").lstrip("-").isdigit() and int(v["pid"]) > 0:
            port = v.get("port")
            out[int(v["pid"])] = int(port) if str(port or "").isdigit() else None
    return out


def _stack_owns(p, stack):
    """A stack pid counts only when the process still serves the registered port (a stale state file's reused pid does not)."""
    if p["pid"] not in stack:
        return False
    port = stack[p["pid"]]
    return port is None or re.search(rf"--port[ =]{port}\b", p.get("cmd") or "") is not None


def _owner_roots(flags, grants):
    """Pids whose descendants are owned: every open grant's pid / ARMED pid / own_pids, every live smoke's roots."""
    roots = set()
    for g in grants:
        for x in (g.get("pid"), (load_json(armed_path(flags, g["id"])) or {}).get("pid")):
            if str(x or "").isdigit():
                roots.add(int(x))
        try:
            roots |= set(own_pids(flags, g))
        except Exception:  # noqa: BLE001 - an unreadable cgroup never hides the grant's root pid
            pass
    for pat in ("RUNNING.json", "SMOKE.lock", "SMOKE-PLACED.json"):   # the roots running_smoke_gpu_occupants walks
        for rp in glob.glob(os.path.join(flags, "dryrun", "*", pat)):
            d = load_json(rp) or {}
            for x in (d.get("pid"), d.get("pgid"), d.get("harness_pid")):
                if str(x or "").isdigit():
                    roots.add(int(x))
    return roots


def foreign_inference_servers(flags, grants, procs=None, stack=None, parent=None):
    """The inference servers no open grant, live smoke or stack service owns: [{pid, birth, comm, cmd, ...}]. Owned = its
    own pid or process group is an owner root, or any ancestor is one (harness_tree walked upwards, which also covers
    setsid'd children while their launcher lives). An orphan whose launcher died has no owning ancestor: foreign."""
    procs = inference_server_procs() if procs is None else procs
    if not procs:
        return []
    stack = stack_service_pids() if stack is None else stack
    pp = {int(p["pid"]): int(p.get("ppid") or 0) for p in procs}   # the scan's own ppids first, then /proc
    parent = parent or (lambda pid: pp[pid] if pid in pp else (_proc_stat(pid) or (0,))[0])
    roots = _owner_roots(flags, grants) | {p["pid"] for p in procs if _stack_owns(p, stack)}
    out = []
    for p in procs:
        if p["pid"] in roots or int(p.get("pgid") or 0) in roots:
            continue
        cur, owned = p["pid"], False
        for _ in range(64):
            cur = int(parent(cur) or 0)
            if cur <= 1:
                break
            if cur in roots:
                owned = True
                break
        if not owned:
            out.append(p)
    return out


def foreign_server_gate(flags, cands, grants, log, dry=False, procs=None, stack=None, parent=None, emit=None):
    """Fix A: -> (kept cands, [(row, reason)] for the removed quiet-host/whole-host rows). Logs one WAIT line per removed
    row per tick and raises ONE owner + pipeline alert per (row, foreign pid) (notify.emit is idempotent). Never kills."""
    gated = [c for c in cands if c.get("shape") in FOREIGN_GATE_SHAPES]
    if not gated:
        return cands, []
    try:
        foreign = foreign_inference_servers(flags, grants, procs=procs, stack=stack, parent=parent)
    except Exception as e:  # noqa: BLE001 - a scan fault never stops allocation; it is logged
        log(f"FOREIGN-SERVER scan failed: {type(e).__name__}: {e}")
        return cands, []
    if not foreign:
        return cands, []
    f0 = foreign[0]
    desc = f"foreign inference server pid={f0['pid']} cmd={f0['cmd'][:100]!r} (no grant owns it)"
    if len(foreign) > 1:
        desc += f" +{len(foreign) - 1} more (pids {','.join(str(p['pid']) for p in foreign[1:6])})"
    waits = []
    emit = emit or notify.emit
    for c in gated:
        log(f"WAIT {c['id']}: {desc}")
        waits.append((c, f"{c.get('shape')} row {c['id']} (rank {float(c['rank']):g}) WAIT: {desc}"))
        if dry:
            continue
        owner = str((load_json(ready_path(flags, c["id"])) or {}).get("owner") or "")
        for p in foreign:
            try:
                emit(flags, "foreign-inference-server", c["id"], f"{p['pid']}:{p['birth']}",
                     f"{c['id']} ({c.get('shape')}) not granted: foreign inference server pid {p['pid']} `{p['cmd'][:120]}` runs "
                     "outside every grant, smoke and stack service. The keeper never kills it: its owner or the stack must "
                     "stop it.", "warning", owner, {"pid": p.get("pid"), "birth": p.get("birth"), "comm": p.get("comm"), "cmd": str(p.get("cmd") or "")[:400]})
            except Exception as ex:  # noqa: BLE001 - an alert failure never stops allocation
                log(f"FOREIGN-SERVER {c['id']}: notify failed: {type(ex).__name__}: {ex}")
    return [c for c in cands if c not in gated], waits


# PM-KEEPER3 #1 (AK 2026-11-23): GDNPROJ r2, ak-cpu-aa-calibration-q-20261122-c and shexp r2 were granted into quarters
# that measured up to 48% busy from foreign load (unclaimed pytest pinned to 24-47, a neighbour's bandwidth-heavy row) and
# died on it. The planner only knew "free" from region locks, never the measured load. QUIET GATE:
#   * a row is QUIET when its spec declares `requires_quiet_host: true` (or `quiet_guard_regions`, which already means
#     "keep these idle for me"). Such a row is granted only onto quarters whose measured busy (the keeper's per-tick
#     hostutil reading, a quarter's 24 cores + their 24 SMT siblings - the same numbers as SNAPSHOT util / IDLE-WHY /
#     queue_status measured q*=%) is < QUIET_FOREIGN_MAX_PCT. A free quarter's busy is foreign by definition.
#   * and never on the same NUMA side (QUIET_NUMA_SIDES: q0+q1, q2+q3 - the two halves of the IO die) as an open
#     whole-host grant (shape host / quiet-host) or a BANDWIDTH-HEAVY grant. Bandwidth-heavy = spec `bandwidth_heavy: true`,
#     or (no explicit `bandwidth_heavy: false`) a DECLARED busy_fraction >= QUIET_HEAVY_BUSY (0.6). An undeclared
#     busy_fraction is not heavy (it would make every legacy row a blocker).
#   * the converse: a bandwidth-heavy candidate is not placed on the NUMA side of a running quiet row.
# A held-back row logs `WAIT <row>: foreign busy X% on <q> (quiet-host needs <15%)`, the reason joins IDLE-WHY, and
# QUIET-NOISE names the unclaimed processes on that quarter (pid, comm, cpu%, cmdline) so the owner of the noise is found.
QUIET_FOREIGN_MAX_PCT = 15.0
QUIET_HEAVY_BUSY = 0.6
# AK addendum 2026-11-23 (calibration -d on q0 died FUTILITY_CONTENTION with q0's own cores 0.7-4.9% busy: read BW
# 68-76 GB/s vs a 111 ceiling, co-tenants on q1/q2/q3 and a build claim on 72-87): contention is DRAM-wide, so the
# "side" is the WHOLE socket - a quiet row needs NO bandwidth-heavy / whole-host row and NO build claim on any quarter.
QUIET_NUMA_SIDES = (frozenset({"q0", "q1", "q2", "q3"}),)
QUIET_NOISE_MIN_PCT = 5.0
# QUIET RESERVE (2026-11-23, pipeline-mgmt): the reverse rule above only blocks a heavy row while a quiet row is RUNNING. While
# quiet rows merely WAIT (grantable, held because the host is loud) a new heavy row used to be placed, kept the host loud and
# starved them (ak-spec-id-noise-q38fn-cpu-r2 granted onto q0 with three quiet rows waiting). Now a waiting quiet row of equal
# or better priority_rank reserves the host: no NEW heavy row and no NEW build claim until it runs. Running rows are never
# pre-empted; whole-host / quiet-host (E5) rows keep their own precedence and are exempt. Anti-starvation: after
# QUIET_RESERVE_MAX_S of continuous reserve the reserve is released (env ROWFLOW_QUIET_RESERVE_MAX_S, else
# <flags>/allocator.json {"quiet_reserve_max_s": N}, else 90 min) and the release is logged.
QUIET_RESERVE_MAX_S = 5400
QUIET_RESERVE_STATE = "quiet_reserve.json"


def quiet_reserve_max_s(flags):
    v = os.environ.get("ROWFLOW_QUIET_RESERVE_MAX_S") or ((load_json(os.path.join(flags, "allocator.json")) or {}).get("quiet_reserve_max_s") if flags else None)
    try:
        return max(0.0, float(v)) if v is not None else float(QUIET_RESERVE_MAX_S)
    except (TypeError, ValueError):
        return float(QUIET_RESERVE_MAX_S)


def quiet_reserve_blocks_build(flags, now=None):
    """-> the waiting quiet row ids when a fresh (< 5 min old) un-released reserve is recorded, else []. Used by claim --build."""
    st = load_json(os.path.join(state_dir(flags), QUIET_RESERVE_STATE)) or {}
    t = time.time() if now is None else now
    if st.get("active") and not st.get("released") and t - float(st.get("ts") or 0) < 300:
        return list(st.get("rows") or [])
    return []


# BUILD LANE (coordinator 2026-11-23, QUIET-RESERVE starved 5 AutoKernel builds for 30+ refusals since 18:30Z): a non-light
# build claim refused for > BUILD_LANE_AFTER_S opens the lane - no NEW quiet row is granted and QUIET-RESERVE stops refusing
# build claims until that claim is granted. `rowflow.py build-window` opens the same hold explicitly (<= BUILD_WINDOW_MAX_MIN).
# Running quiet rows are never pre-empted (the running-quiet refusal in claim --build stays).
BUILD_LANE_AFTER_S = 900
BUILD_LANE_STALE_S = 600       # a refusal record not retried for this long is dead (its claimant gave up)
BUILD_WINDOW_MAX_MIN = 90
BUILD_REFUSALS = "build_refusals.json"
BUILD_WINDOW = "build_window.json"


def _build_key(owner, cpus):
    return f"{owner}|{str(cpus).strip()}"


def record_build_refusal(flags, owner, cpus, now=None):
    """A refused non-light build claim: remember when this owner+cpus first (continuously) asked."""
    now = time.time() if now is None else now
    p = os.path.join(state_dir(flags), BUILD_REFUSALS)
    st = load_json(p) or {}
    k = _build_key(owner, cpus)
    e = st.get(k) or {}
    if not e or now - float(e.get("last_at") or 0) > BUILD_LANE_STALE_S:
        e = {"owner": owner, "cpus": str(cpus).strip(), "first_at": now, "refusals": 0}
    e["last_at"], e["refusals"] = now, int(e.get("refusals") or 0) + 1
    st[k] = e
    atomic_json(p, st)


def clear_build_refusal(flags, owner, cpus):
    p = os.path.join(state_dir(flags), BUILD_REFUSALS)
    st = load_json(p) or {}
    if st.pop(_build_key(owner, cpus), None) is not None:
        atomic_json(p, st)


def build_lane_open(flags, now=None):
    """-> (label, kind) when the build lane is open ('' , '' when closed). kind: 'window' | 'claim'."""
    now = time.time() if now is None else now
    w = load_json(os.path.join(state_dir(flags), BUILD_WINDOW)) or {}
    if float(w.get("until") or 0) > now:
        return f"window by {w.get('by') or '?'} until {dt.datetime.fromtimestamp(float(w['until']), dt.timezone.utc):%H:%MZ} ({w.get('reason') or '-'})", "window"
    st = load_json(os.path.join(state_dir(flags), BUILD_REFUSALS)) or {}
    old = [(e["first_at"], k) for k, e in st.items() if now - float(e.get("first_at") or now) > BUILD_LANE_AFTER_S
           and now - float(e.get("last_at") or 0) <= BUILD_LANE_STALE_S]
    if old:
        k = min(old)[1]
        return f"{k} (refused {int((now - float(st[k]['first_at'])) / 60)} min)", "claim"
    return "", ""


def build_window(flags, minutes, by, reason, now=None, log=print):
    """`rowflow.py build-window --minutes N --by <owner> --reason R`: open the build lane explicitly for N (<= 90) minutes."""
    need(isinstance(minutes, int) and 1 <= minutes <= BUILD_WINDOW_MAX_MIN, f"--minutes must be 1..{BUILD_WINDOW_MAX_MIN}")
    need(str(by or "").strip(), "build-window: --by <owner> is required")
    reason = re.sub(r"\s+", "_", str(reason or "").strip())
    need(reason, "build-window: --reason is required")
    now = time.time() if now is None else now
    rec = {"by": by, "reason": reason, "at": now_iso(), "minutes": minutes, "until": now + minutes * 60}
    atomic_json(os.path.join(state_dir(flags), BUILD_WINDOW), rec)
    msg = (f"BUILD-WINDOW opened by {by} for {minutes} min until {dt.datetime.fromtimestamp(rec['until'], dt.timezone.utc):%H:%MZ} "
           f"(reason={reason}): no new quiet row is granted; QUIET-RESERVE does not refuse build claims; closes itself")
    _keeper_log_line(flags, msg)
    log(msg)
    return rec


def quiet_required(d):
    d = d or {}
    return d.get("requires_quiet_host") is True or bool(d.get("quiet_guard_regions"))


def bandwidth_heavy(d):
    d = d or {}
    if isinstance(d.get("bandwidth_heavy"), bool):
        return d["bandwidth_heavy"]
    # A GPU-lane row's busy_fraction is the DEVICE's busy share; its 8 host threads are no DRAM-wide load. Heavy only when
    # it declares `bandwidth_heavy: true` (2026-11-23 quiet-gate fix: c19-fold-a3b-gpu busy_fraction 1.0 starved q0-q2).
    if str(d.get("shape") or "") == "gpu-q3" or d.get("gpu_use") or "mi210" in str(d.get("regions") or "") or "gpu-quiet" in str(d.get("regions") or ""):
        return False
    b = d.get("busy_fraction")
    return isinstance(b, (int, float)) and not isinstance(b, bool) and float(b) >= QUIET_HEAVY_BUSY


def numa_side(qs):
    return frozenset().union(*[s for s in QUIET_NUMA_SIDES if s & set(qs)]) if qs else frozenset()


def option_quarters(o):
    out = set()
    for t in o:
        if t in QUARTERS:
            out.add(t)
        elif re.fullmatch(r"[ct]\d+", str(t)):
            out.add(hostutil.quarter_of_cpu(int(t[1:])))
    return out


def quiet_gate(cands, allrows, grants, util, flags=None, reserve=None):
    """PURE (flags only to read a grant's manifest when allrows lacks it). -> (kept cands, [(row, reason)], waits{rid: line}).
    Quiet candidates keep only options whose quarters measure < QUIET_FOREIGN_MAX_PCT and share no NUMA side with an open
    whole-host / bandwidth-heavy grant; bandwidth-heavy candidates keep only options off the side of a running quiet row.
    A candidate left with no option is removed (it waits; nothing is stopped).
    QUIET RESERVE: `reserve` (dict; in: since, now, max_s; out: active, released, rows, since, elapsed_s) - a quiet candidate
    the gate held back reserves the host against NEW bandwidth-heavy candidates of equal or worse rank until it is granted."""
    def man(rid):
        return allrows.get(rid) or (load_json(ready_path(flags, rid)) if flags else None) or {}
    loud, quiet_q = set(), set()
    running_quiet = []   # QUIET-SERIAL (AK ak-shexp-r5-quietgate-20261123): a RUNNING quiet row is loud to every other quiet candidate
    for g in grants:
        gq = option_quarters(g.get("holds") or ())
        d = man(g["id"])
        if not gq:
            continue
        if not g["id"].startswith(BUILD_PREFIX) and quiet_required(d):
            running_quiet.append(g["id"])
        if g["id"].startswith(BUILD_PREFIX):   # a build claim is bandwidth-heavy (AK addendum) - except a LIGHT test claim
            if not is_light_build(flags, g["id"]):
                loud |= gq
            continue
        if bandwidth_heavy(d) or set(QUARTERS) <= gq or str(d.get("shape") or "") in ("host", "quiet-host"):
            loud |= gq
        if quiet_required(d):
            quiet_q |= gq
    kept, waits, lines = [], [], {}
    for c in cands:
        d = man(c["id"])
        q_need, heavy = quiet_required(d), bandwidth_heavy(d)
        if not (q_need or heavy):
            kept.append(c)
            continue
        if q_need and running_quiet and c.get("shape") != "quiet-host" and str(d.get("shape") or "") not in ("host", "quiet-host"):
            lines[c["id"]] = f"QUIET-SERIAL {c['id']} waits for running quiet {running_quiet[0]}"
            waits.append((c, f"{c.get('shape') or c['kind']} row {c['id']} (rank {float(c['rank']):g}) WAIT: "
                             f"QUIET-SERIAL waits for running quiet {running_quiet[0]}"))
            continue
        ok, why = [], None
        for o in c["options"]:
            qs = option_quarters(o)
            side = numa_side(qs)
            if q_need:
                hot = [(q, (util or {}).get(q)) for q in sorted(qs)]
                bad = [(q, v) for q, v in hot if v is None or v >= QUIET_FOREIGN_MAX_PCT]
                if bad:
                    q, v = max(bad, key=lambda x: 1e9 if x[1] is None else x[1])
                    why = why or (f"foreign busy {'?' if v is None else f'{v:.0f}'}% on {q} (quiet-host needs "
                                  f"<{QUIET_FOREIGN_MAX_PCT:.0f}%)", q)
                    continue
                near = sorted(side & loud)
                if near:
                    why = why or (f"bandwidth-heavy/whole-host grant on {','.join(near)} shares its NUMA side "
                                  f"(quiet-host needs a quiet side)", near[0])
                    continue
            if heavy and not q_need:
                near = sorted(side & quiet_q)
                if near:
                    why = why or (f"bandwidth-heavy row not placed beside the running quiet-host row on {','.join(near)}", near[0])
                    continue
            ok.append(o)
        if ok:
            kept.append(c if len(ok) == len(c["options"]) else dict(c, options=ok))
            continue
        why = why or ("no quiet option", "")
        lines[c["id"]] = f"WAIT {c['id']}: {why[0]}"
        waits.append((c, f"{c.get('shape') or c['kind']} row {c['id']} (rank {float(c['rank']):g}) WAIT: {why[0]}"))
    # QUIET-SERIAL, shortest first: at most ONE quiet row is placed per pass; the shortest estimate_s wins, priority_rank breaks
    # the tie. Non-quiet and whole-host (quiet-host) candidates keep their normal order and are never dropped here.
    def _qser(c):
        d = man(c["id"])
        return quiet_required(d) and c.get("shape") != "quiet-host" and str(d.get("shape") or "") not in ("host", "quiet-host")
    qk = [c for c in kept if _qser(c)]
    if len(qk) > 1:
        def est(c):
            e = c.get("estimate_s") or man(c["id"]).get("estimate_s")
            return float(e) if e else float("inf")
        win = min(qk, key=lambda c: (est(c), float(c["rank"]), c["id"]))
        for c in qk:
            if c is not win:
                lines[c["id"]] = f"QUIET-SERIAL {c['id']} waits for running quiet {win['id']}"
                waits.append((c, f"{c.get('shape') or c['kind']} row {c['id']} (rank {float(c['rank']):g}) WAIT: "
                                 f"QUIET-SERIAL waits for running quiet {win['id']}"))
        drop = {c["id"] for c in qk if c is not win}
        kept = [c for c in kept if c["id"] not in drop]
    if reserve is not None:
        _quiet_reserve(cands, kept, waits, lines, man, reserve)
        kept = [c for c in kept if c["id"] not in reserve.get("held", ())]
    return kept, waits, lines


def _quiet_reserve(cands, kept, waits, lines, man, reserve):
    kept_ids = {c["id"] for c in kept}
    # reservers: quiet rows held back by the gate, AND quiet rows grantable this very tick (the heavy row must not be placed
    # beside a quiet row granted in the same pass); both ride the same anti-starvation clock
    wq = [c for c in cands if quiet_required(man(c["id"]))
          and str(man(c["id"]).get("shape") or "") not in ("host", "quiet-host") and c.get("shape") != "quiet-host"]
    now = float(reserve.get("now") or time.time())
    since = float(reserve.get("since") or now) if wq else None
    elapsed = (now - since) if wq else 0.0
    released = bool(wq) and elapsed > float(reserve.get("max_s", QUIET_RESERVE_MAX_S))
    reserve.update(active=bool(wq), released=released, rows=[c["id"] for c in wq], since=since, elapsed_s=elapsed, held=set())
    if not wq:
        return
    if released:
        lines["__quiet_reserve_release"] = (f"QUIET-RESERVE-RELEASE reserve for {','.join(c['id'] for c in wq)} held {elapsed / 60:.0f} min "
                                            f"> {float(reserve.get('max_s', QUIET_RESERVE_MAX_S)) / 60:.0f} min bound "
                                            f"(ROWFLOW_QUIET_RESERVE_MAX_S / allocator.json quiet_reserve_max_s): heavy rows placed")
        return
    for c in kept:
        d = man(c["id"])
        if quiet_required(d) or not bandwidth_heavy(d) or str(d.get("shape") or "") in ("host", "quiet-host") or c.get("shape") == "quiet-host":
            continue
        for q in sorted(wq, key=lambda x: float(x["rank"])):
            if float(q["rank"]) <= float(c["rank"]):
                reserve["held"].add(c["id"])
                lines[c["id"]] = f"QUIET-RESERVE {c['id']} held for {q['id']}"
                waits.append((c, f"{c.get('shape') or c['kind']} row {c['id']} (rank {float(c['rank']):g}) WAIT: "
                                 f"QUIET-RESERVE held for {q['id']} (rank {float(q['rank']):g})"))
                break


def quiet_noise(flags, quarters, grants, census=None, prev=None, dt_s=None):
    """Unclaimed processes on `quarters` (not a grant's own pid, not the keeper/smoke tree) above QUIET_NOISE_MIN_PCT CPU,
    from the contamination sampler's stored census vs a fresh one: [(q, pid, comm, pct, cmdline)], busiest first."""
    st = load_json(os.path.join(state_dir(flags), "contamination.json")) or {}
    census = hostutil.proc_census() if census is None else census
    prev = {int(k): tuple(v) for k, v in (st.get("census") or {}).items()} if prev is None else prev
    dt_s = (time.time() - float(st.get("t") or time.time())) if dt_s is None else dt_s
    if dt_s <= 0:
        return []
    own = set(contamination_exempt_pids(flags))
    for g in grants:
        try:
            own |= set(own_pids(flags, g))
        except Exception:  # noqa: BLE001
            pass
    out = []
    for pid, (birth, cpu, last, comm) in census.items():
        pv = prev.get(pid)
        if pid in own or not pv or pv[0] != birth:
            continue
        pct = 100.0 * (cpu - pv[1]) / dt_s
        q = hostutil.quarter_of_cpu(last)
        if pct >= QUIET_NOISE_MIN_PCT and q in quarters:
            out.append((q, pid, comm, round(pct, 1), _cmdline(pid)[:100]))
    return sorted(out, key=lambda x: -x[3])


# E5 starvation fix B (2026-11-23): before r8 was raised to rank 15, WAIT-FOR-SMOKE kept the rank-25 quiet-host row out of
# planning while 16 better-ranked GPU smokes stayed queued, so its drain never formed (the PM-DRAINFIX exemption covers
# formed drains only). A quiet-host row that has waited longer than this behind queued smokes enters planning anyway.
QH_SMOKE_WAIT_MAX_S = 1200


def qh_smoke_wait_max_s(flags):
    """env ROWFLOW_QH_SMOKE_WAIT_MAX_S, else <flags>/allocator.json {"quiet_smoke_wait_max_s": N}, else 20 min."""
    v = os.environ.get("ROWFLOW_QH_SMOKE_WAIT_MAX_S") or (load_json(os.path.join(flags, "allocator.json")) or {}).get("quiet_smoke_wait_max_s")
    try:
        return max(0.0, float(v)) if v is not None else float(QH_SMOKE_WAIT_MAX_S)
    except (TypeError, ValueError):
        return float(QH_SMOKE_WAIT_MAX_S)


def smoke_wait_starved(flags, worse, now=None, persist=True):
    """-> ids of quiet-host rows in `worse` (rows WAIT-FOR-SMOKE would remove) that have waited > qh_smoke_wait_max_s.
    The first-wait epoch per row lives in state/smoke_wait_since.json; a row that stops waiting is forgotten."""
    now = time.time() if now is None else now
    sp = os.path.join(state_dir(flags), "smoke_wait_since.json")
    prev = load_json(sp) or {}
    cur, out, lim = {}, [], qh_smoke_wait_max_s(flags)
    for c in worse:
        if c.get("shape") != "quiet-host":
            continue
        s0 = float(prev.get(c["id"]) or now)
        cur[c["id"]] = s0
        if now - s0 >= lim:
            out.append(c["id"])
    if persist and cur != prev:
        try:
            atomic_json(sp, cur)
        except OSError:
            pass
    return out


def smoke_queued_path(flags, rid): return os.path.join(dry_dir(flags, rid), "SMOKE-QUEUED.json")
def smoke_placed_path(flags, rid): return os.path.join(dry_dir(flags, rid), "SMOKE-PLACED.json")


def live_smoke_tokens(flags):
    """cpu tokens of every live CPU smoke (RUNNING.json from dryrun_run, SMOKE-PLACED.json from the keeper)."""
    out = set()
    for pat in ("RUNNING.json", "SMOKE-PLACED.json"):
        for p in glob.glob(os.path.join(flags, "dryrun", "*", pat)):
            r = load_json(p) or {}
            if r.get("pid") and alive(r["pid"]):
                out |= cpu_tokens(ws58_cpus(r.get("regions")), gpu_threads=True) | ({GPU} if r.get("gpu") else set())
    return out


def cpu_ranges(cs):
    cs, out = sorted(cs), []
    for c in cs:
        if out and c == out[-1][1] + 1:
            out[-1][1] = c
        else:
            out.append([c, c])
    return ",".join(f"{a}-{b}" if b > a else str(a) for a, b in out)


def pocket_tokens(q):
    """The smoke pocket of quarter q: SMOKE_POCKET_THREADS SMT-sibling thread tokens, () for q3."""
    return frozenset(f"t{n}" for n in SMOKE_POCKETS.get(q, ()))


def pick_smoke_cpus(free, n=SMOKE_CPUS, timing_q=frozenset()):
    """SMOKE POCKETS (pipeline audit 2026-11-10 #5): a <= SMOKE_CPUS-wide smoke runs in a quarter's fixed pocket - 4 SMT
    sibling threads no quarter booking ever takes (a whole-quarter grant runs on its 24 cores + 16 siblings, the last 8
    siblings are outside it) and no sub-quarter block is cut from (_sub_blocks). A pocket beside a timing grant
    (timing_q: quarters a bench/timing grant holds cores of) is never used - its siblings would perturb the measurement;
    an idle pocket's quarter first (the smoke then has the physical cores to itself). With every pocket busy or beside
    timing, or a wider smoke: n physical cores (+ siblings) of a PARTLY used quarter, never a whole free one, never the
    MI210 host threads. None when nothing fits (SMOKE-WAIT).
    D9 2026-11-18 SMOKE-CPUS: a row's spec may request smoke_cpus (SMOKE_CPUS..SMOKE_CPUS_MAX); a request of
    SMOKE_CPUS_MAX alone may take a whole FREE quarter (q0-q2 first; q3 only when every one of its cores is free here -
    the caller removes Q3_GUARD while a GPU row is queued)."""
    if n >= SMOKE_CPUS_MAX:
        for q in sorted(QUARTERS, key=lambda q: (q == "q3", q)):
            cs = qcores(q)
            if cs <= free and {f"t{int(c[1:]) + 96}" for c in cs} - {f"t{k}" for k in GPU_HOST_THREADS} - POCKET_TOKENS <= free:
                return cpu_ranges(sorted(int(c[1:]) for c in cs))
        return None
    if n <= SMOKE_CPUS:
        best = None
        for q in QUARTERS:
            pk = pocket_tokens(q)
            if not pk or q in timing_q or not pk <= free:
                continue
            busy_cores = sum(1 for t in pk if f"c{int(t[1:]) - 96}" not in free)
            if best is None or (busy_cores, q) < best[0]:
                best = ((busy_cores, q), sorted(int(t[1:]) for t in pk)[:n])
        if best:
            return cpu_ranges(best[1])
    best = None
    for q in QUARTERS:
        if q in free:
            continue   # a whole free quarter stays whole for a row (its pocket serves the smoke)
        cs = [int(c[1:]) for c in sorted(qcores(q), key=lambda t: int(t[1:]))
              if c in free and f"t{int(c[1:]) + 96}" in free and int(c[1:]) + 96 not in GPU_HOST_THREADS
              and f"t{int(c[1:]) + 96}" not in POCKET_TOKENS]
        if len(cs) < n:
            continue
        key = (q != "q3", q)   # q3's non-GPU cores first
        if best is None or key < best[0]:
            best = (key, cs[:n])
    return cpu_ranges(best[1]) if best else None


def place_smokes(flags, free, log=print, dry=False, n=SMOKE_CPUS, reserved=frozenset(), timing_q=frozenset(),
                 drain_reserved=frozenset(), gpu_queued=False, demand_reserved=frozenset()):
    """Every queued CPU smoke (dryrun/<id>/SMOKE-QUEUED.json, oldest first) gets its record's `cpus` (default n) free
    cores, and its smoke starts detached through publish_row.py --run-smoke (the same dryrun_run path). `free` is updated
    in place. No free cores is WAIT (logged), never a failure. Returns the placed (rid, cpus).
    D9 2026-11-18 SMOKE-CPUS: a wider-than-SMOKE_CPUS smoke never takes drain_reserved tokens (the regions of the row the
    planner is draining for - a smoke never pre-empts or delays a real grant); with gpu_queued no smoke takes q3's cores
    88-95 / SMT 184-191 (GPU-Q3-GUARD). demand_reserved (the options of grantable/armed rows that fit the free set this
    tick) is likewise never taken by a wide smoke: a waiting row's quarter stays its own. 4-core pocket smokes unchanged."""
    drain_reserved = frozenset(expand(set(drain_reserved)) | expand(set(demand_reserved)))
    placed = []
    qs = sorted(glob.glob(os.path.join(flags, "dryrun", "*", "SMOKE-QUEUED.json")),
                key=lambda p: (row_rank(load_json(ready_path(flags, os.path.basename(os.path.dirname(p)))) or (load_json(p) or {}).get("spec")),
                               (load_json(p) or {}).get("queued_at") or "", p))   # PM-SMOKEFIX: priority_rank, then FIFO
    for q in qs:
        rid = os.path.basename(os.path.dirname(q))
        pl = load_json(smoke_placed_path(flags, rid)) or {}
        if pl.get("pid") and alive(pl["pid"]):
            continue   # running; its cpus are already in busy
        if smoke_passed(flags, rid):   # a PASS is terminal: never re-smoke a grantable row
            _rm(q)
            log(f"SMOKE-DONE {rid}: PASS already recorded for this launcher; queue record dropped")
            continue
        want = int((load_json(q) or {}).get("cpus") or n)
        gt = gpu_touch(load_json(ready_path(flags, rid)) or {})
        if gt and GPU not in free:   # a /dev/kfd-capable smoke queues behind every GPU holder (exclusive grants first)
            log(f"SMOKE-WAIT {rid}: its job can touch the GPU and gpu-quiet is held; stays queued (not a failure)")
            continue
        avail = set(free) - set(reserved)
        if want > SMOKE_CPUS:
            avail -= drain_reserved
        if gpu_queued:
            avail -= Q3_GUARD | {"q3"}
        cpus = pick_smoke_cpus(avail, want, timing_q)
        if not cpus:
            log(f"SMOKE-WAIT {rid}: every smoke pocket is busy or beside a timing grant and no partly used quarter has "
                f"{want} free cores; stays queued (not a failure)")
            continue
        toks = cpu_tokens(cpus, gpu_threads=True) | ({GPU} if gt else set())
        free -= toks
        free -= {qq for qq in QUARTERS if expand({qq}) & toks}
        if dry:
            log(f"PLAN smoke {rid} cpus={cpus}"); placed.append((rid, cpus)); continue
        try:
            out = open(os.path.join(dry_dir(flags, rid), "smoke-runner.out"), "a")
            p = subprocess.Popen([sys.executable, os.path.join(_HERE, "publish_row.py"), "--run-smoke", rid,
                                  "--regions", cpus, "--flags", flags], stdout=out, stderr=subprocess.STDOUT,
                                 stdin=subprocess.DEVNULL, start_new_session=True)
            atomic_json(smoke_placed_path(flags, rid), {"id": rid, "pid": p.pid, "regions": cpus, "at": now_iso(), "gpu": gt})
            log(f"SMOKE-PLACE {rid} cpus={cpus} pid={p.pid} (log {os.path.join(dry_dir(flags, rid), 'launcher.out')})")
            placed.append((rid, cpus))
        except Exception as e:  # noqa: BLE001 - one smoke never stops the tick
            log(f"ERROR smoke {rid}: {type(e).__name__}: {e}")
    return placed


# ---------------------------------------------------------------- dry-run reconcile
SMOKE_MAX_WAITS = 3          # a smoke whose engine never reaches START is WAIT at most this many times, then FAIL never-started
DRYRUN_DEADLINE_GRACE_S = 120  # the harness enforces the deadline itself; the keeper steps in only after this grace


def proc_alive(pid):
    """/proc-based liveness (kill -0 is blind on this host; a zombie is dead)."""
    try:
        return bool(pid) and _proc_stat(int(pid)) is not None
    except (TypeError, ValueError):
        return False


def tree_pids(pgid):
    """Every live pid in process group / session `pgid` plus all their descendants (setsid'd grandchildren included)."""
    kids, members = {}, set()
    for q in os.listdir("/proc"):
        if not q.isdigit():
            continue
        try:
            f = open(f"/proc/{q}/stat").read().rsplit(")", 1)[1].split()
        except (OSError, IndexError):
            continue
        if f[0] == "Z":
            continue
        pid, ppid, pg, sid = int(q), int(f[1]), int(f[2]), int(f[3])
        kids.setdefault(ppid, []).append(pid)
        if pg == pgid or sid == pgid or pid == pgid:
            members.add(pid)
    out, todo = set(), list(members)
    while todo:
        x = todo.pop()
        if x not in out:
            out.add(x)
            todo.extend(kids.get(x, []))
    out.discard(os.getpid())
    return out


def kill_tree(pgid, grace=10):
    """TERM the group/session/descendants, wait, KILL, verify by /proc. Returns the pids still alive (empty = dead)."""
    for sig in (signal.SIGTERM, signal.SIGKILL):
        pids = tree_pids(pgid)
        for x in pids:
            try:
                os.kill(x, sig)
            except (ProcessLookupError, PermissionError):
                pass
        for _ in range(grace if sig == signal.SIGTERM else 3):
            if not any(proc_alive(x) for x in pids):
                break
            time.sleep(1)
    return {x for x in tree_pids(pgid) if proc_alive(x)}


def _rm(path):
    try:
        os.remove(path)
        return True
    except OSError:
        return False


def smoke_passed(flags, rid, d=None):
    """A PASS for the row's CURRENT launcher exists: the smoke is terminal (q38p4c-cpu-int8 2026-11-05: PASS at 12:52:12Z,
    then a reap-requeue + 'state grantable; nothing to do' counted as never-started and FAIL-1 overrode the PASS)."""
    p = load_json(pass_path(flags, rid))
    if not p:
        return False
    d = d or load_json(ready_path(flags, rid)) or load_json(os.path.join(dry_dir(flags, rid), "unpublished.json")) or {}
    try:
        return p.get("launcher_sha256") == sha256(d["launcher"]["path"])
    except (OSError, KeyError, TypeError):
        return "launcher_sha256" not in p


def smoke_wait_or_fail(flags, rid, d, why, log=print):
    """Count a never-started WAIT against the queued smoke; the SMOKE_MAX_WAITS-th one is FAIL reason=never-started.
    A PASS for the current launcher is terminal: the queue record is dropped, nothing is counted or failed.
    Returns WAIT | FAIL | PASS."""
    q = smoke_queued_path(flags, rid)
    if smoke_passed(flags, rid, d):
        _rm(q)
        log(f"SMOKE-DONE {rid}: PASS already recorded for this launcher; not re-smoked ({why[:120]})")
        return "PASS"
    qd = load_json(q) or {}
    n = int(qd.get("waits") or 0) + 1
    if n >= SMOKE_MAX_WAITS:
        if d:
            record_fail(flags, rid, d, f"never-started: {n} smoke attempts never reached engine START ({why})",
                        {"kind": "never-started", "waits": n})
        _rm(q)
        log(f"SMOKE-FAIL {rid}: never-started after {n} WAITs ({why})")
        return "FAIL"
    if qd or os.path.exists(q):
        qd["waits"] = n
        qd["last_wait"] = {"at": now_iso(), "why": why[:200]}
        atomic_json(q, qd)
    log(f"SMOKE-WAIT {rid}: {why}; requeued ({n}/{SMOKE_MAX_WAITS})")
    return "WAIT"


def reconcile_dryruns(flags, log=print, now=None, allrows=None):
    """Each keeper tick: every dryrun/<id>/RUNNING.json whose process is dead (by /proc, never kill -0) is reaped -
    RUNNING.json and the private dry-run grant removed, so its holds return to the free list the same tick; one whose
    dry-run grant deadline passed (+grace) and whose harness is gone or stuck is killed (group + descendants), then
    reaped with WAIT (never reached START; bounded retry) or FAIL (post-START). Returns [(rid, action)]."""
    now = time.time() if now is None else now
    allrows = rows(flags) if allrows is None else allrows
    out = []
    for rp in glob.glob(os.path.join(flags, "dryrun", "*", "RUNNING.json")):
        rid = os.path.basename(os.path.dirname(rp))
        r = load_json(rp) or {}
        dd = os.path.dirname(rp)
        grant = r.get("grant") or os.path.join(dd, "grants", rid + ".grant")
        pid = r.get("pid")
        dl = iso_epoch(r.get("deadline")) if r.get("deadline") else None
        if dl is None and os.path.exists(grant):
            dl = iso_epoch(dict(re.findall(r"(\w+)=(\S+)", head1(grant) or "")).get("end"))
        if dl is None and r.get("started"):   # pre-hotfix RUNNING.json with its grant already gone: the window dryrun_run used
            row = allrows.get(rid) or {}
            win = dryrun_window(row, int(row.get("first_progress_s") or FIRST_PROGRESS_S)) if row else 6 * 3600
            st0 = iso_epoch(r["started"])
            dl = st0 + win if st0 else None
        started = any("START regions=" in l for l in tail(os.path.join(dd, "launcher.out"), 400)[-200:])
        if proc_alive(pid):
            if dl is None or now < dl + DRYRUN_DEADLINE_GRACE_S:
                continue
            try:
                open(os.path.join(dd, "stop"), "a").close()   # the engine exits on STOP while waiting, too
            except OSError:
                pass
            surv = kill_tree(int(r.get("pgid") or pid))
            if surv:
                log(f"ALERT DRYRUN-DEADLINE {rid}: past deadline {r.get('deadline')}; pids {sorted(surv)} survive TERM+KILL; holds kept")
                out.append((rid, "unkillable")); continue
            phase = "post-START" if started else "pre-START"
            log(f"DRYRUN-DEADLINE {rid}: killed pgid {r.get('pgid') or pid} ({phase}, deadline {r.get('deadline')})")
            action = "deadline"
        else:
            phase = "post-START" if started else "pre-START"
            action = "reaped"
            log(f"DRYRUN-REAP {rid}: pid {pid} is dead; RUNNING.json and the private grant removed, holds released")
        _rm(rp); _rm(grant)
        sp = smoke_placed_path(flags, rid)
        if not proc_alive((load_json(sp) or {}).get("pid")):
            _rm(sp)
        d = allrows.get(rid) or load_json(ready_path(flags, rid)) or load_json(os.path.join(dd, "unpublished.json"))
        if action == "deadline" and phase == "post-START" and d:
            record_fail(flags, rid, d, f"deadline: dry-run grant end {r.get('deadline')} passed after engine START", {"kind": "deadline", "phase": phase})
            _rm(smoke_queued_path(flags, rid))
            out.append((rid, "FAIL")); continue
        if phase == "pre-START" and os.path.exists(smoke_queued_path(flags, rid)):
            out.append((rid, smoke_wait_or_fail(flags, rid, d, f"dry run {action} before engine START", log))); continue
        out.append((rid, action))
    return out


UNTRACKED_HOLDER = "untracked (no grant or smoke record: a region-lock hold or a smoke still exiting; resolves within a tick or two)"


def idle_partial_quarters(flags, free, busy, grants, holders):
    """IDLE-WHY for CPU quarters that are not whole-free but not held by a whole-quarter holder either: name the cores
    that keep each one off the free list and who holds them (grant / smoke / '?'), so a stuck hold is visible."""
    owners = {}
    for g in grants:
        for t in g["holds"]:
            owners.setdefault(t, set()).add(g["id"])
    for pat in ("RUNNING.json", "SMOKE-PLACED.json"):
        for p in glob.glob(os.path.join(flags, "dryrun", "*", pat)):
            r = load_json(p) or {}
            tag = f"smoke {os.path.basename(os.path.dirname(p))}" + ("" if proc_alive(r.get("pid")) else f" (pid {r.get('pid')} dead)")
            for t in cpu_tokens(ws58_cpus(r.get("regions") or ""), gpu_threads=True):
                owners.setdefault(t, set()).add(tag)
    out = {}
    for q in QUARTERS:
        if q in free or q in holders:
            continue
        toks = sorted((expand({q}) & busy) - {q}, key=lambda t: (t[0], int(t[1:]) if t[1:].isdigit() else 0))
        if not toks:
            continue
        who = sorted(set().union(*[owners.get(t, {UNTRACKED_HOLDER}) for t in toks]))
        nfree = len([c for c in qcores(q) if c in free])
        out[q] = f"not whole-free: {','.join(compress(set(toks)))} held by {', '.join(who)}; {nfree} cores free"
    return out


def queued_gpu_min_rank(flags):
    """Lowest priority_rank among queued GPU smokes (marker -> unpublished.json / ready manifest / queued spec), or None."""
    best = None
    for q in glob.glob(os.path.join(flags, "dryrun", "*", "GPU-SMOKE-QUEUED.json")):
        rid = os.path.basename(os.path.dirname(q))
        row = load_json(os.path.join(dry_dir(flags, rid), "unpublished.json")) or load_json(ready_path(flags, rid)) \
            or (load_json(q) or {}).get("spec") or {}
        r = row_rank(row)
        best = r if best is None else min(best, r)
    return best


def stopping_tokens(flags, grants, allrows):
    """PM-STOPRES: tokens held by open grants whose row STOP file exists (the owner STOPped it; it checkpoints, exits rc 75)."""
    out = set()
    for g in grants:
        sf = resolve_stop_path(allrows.get(g["id"]) or load_json(ready_path(flags, g["id"])) or {})
        if sf and os.path.exists(sf):
            out |= set(g.get("holds") or ())
    return out


def region_end_map(flags, grants, busy, now=None):
    """{token: end epoch | None} for every busy token: the latest end of the open grants holding it (None when a holding
    grant has no parsable end), live smokes now + SMOKE_HOLD_S; a quarter token, the latest end of its busy members.
    A busy token with no entry (a foreign region-lock hold) is unknown to earliest_start."""
    now = time.time() if now is None else now
    out = {}
    for g in grants:
        e = iso_epoch(g.get("end"))
        for r in expand(set(g.get("holds") or ())):
            if r in out and (out[r] is None or e is None):
                out[r] = None
            else:
                out[r] = e if r not in out else max(out[r], e)
    try:
        for r in live_smoke_tokens(flags):
            out.setdefault(r, now + SMOKE_HOLD_S)
    except Exception:  # noqa: BLE001 - an unreadable smoke record is an unknown end
        pass
    for q in QUARTERS:
        if q in busy and q not in out:
            members = (expand({q}) - {q}) & set(busy)
            if members and all(out.get(m) is not None for m in members):
                out[q] = max(out[m] for m in members)
    return out


def allocate(flags, keeper_log=None, log=print, dry=False):
    """dry=True: snapshot + plan only (PLAN lines); nothing healed, armed, granted or started."""
    keeper_log = keeper_log or os.path.join(flags, "ws58-calendar-keeper.log")
    holds = operator_holds(flags)
    if holds:   # the explicit operator emergency stop only (exact HOLD_<NAME>; *.lifted* / *.disabled* never match)
        log(f"HOLD present ({','.join(holds)}); nothing allocated"); return []
    seen = set()
    if not dry:
        try:   # D9: before filing/status passes - a row cut by our own drain cap is requeued under the same id
            capcut_requeue(flags, log)
        except Exception as e:  # noqa: BLE001 - never stops allocation
            log(f"CAPCUT-REQUEUE failed: {type(e).__name__}: {e}")
        try:   # operator 2026-11-21: bounded auto-requeue of resumable partial ends (same id, AUTOREQUEUE_MAX)
            autorequeue(flags, log)
        except Exception as e:  # noqa: BLE001 - never stops allocation
            log(f"AUTO-REQUEUE failed: {type(e).__name__}: {e}")
        try:
            finish_withdrawals(flags, log)
        except Exception as e:  # noqa: BLE001 - never stops allocation
            log(f"WITHDRAW-FINISH failed: {type(e).__name__}: {e}")
    admit_hold = None
    if not dry:
        try:   # operator 2026-11-07: disk pause state machine (SIGSTOP/SIGCONT of captured groups) then the admission gate
            diskpause.tick(flags, log=log)
        except Exception as e:  # noqa: BLE001 - never stops allocation
            log(f"DISK-PAUSE tick failed: {type(e).__name__}: {e}")
    try:   # HOLD-ADMISSIONS file and/or disk pause: no NEW grant/admission; running rows and healing continue
        admit_hold = diskpause.admission_gate(flags, log=log, persist=not dry, log_transition=log_transition)
    except Exception as e:  # noqa: BLE001 - a gate fault must not stop allocation
        log(f"ADMISSION-GATE failed: {type(e).__name__}: {e}")
    allrows = rows(flags)
    if not dry:
        try:   # dead / past-deadline dry runs release their holds this tick
            reconcile_dryruns(flags, log, allrows=allrows)
        except Exception as e:  # noqa: BLE001 - never stops allocation
            log(f"DRYRUN-RECONCILE failed: {type(e).__name__}: {e}")
    rl = rl_status()
    if not dry:
        try:   # F7: a build grant has no engine; its window end releases its quarter
            reap_build_grants(flags, log=log)
        except Exception as e:  # noqa: BLE001
            log(f"BUILD-END failed: {type(e).__name__}: {e}")
    grants = open_grants(flags) if dry else heal_grants(flags, open_grants(flags), rl, log, seen, allrows)
    gids = {g["id"] for g in grants}
    busy, free, holders = host_snapshot(flags, grants, rl)
    gpu_open = any(GPU in g["holds"] for g in grants)
    counts = lane_counts(flags, allrows)
    cands = []
    sup_blocked = {}
    try:
        sup_index = superseded_index(flags)
    except Exception as e:  # noqa: BLE001 - an unreadable manifest never stops allocation
        log(f"SUPERSEDED-INDEX failed: {type(e).__name__}: {e}")
        sup_index = {}
    gpu_queued = False   # D9 2026-11-18 GPU-Q3-GUARD: a GPU-lane row queued (grantable, armed or awaiting its smoke)
    for rid, d in allrows.items():
        sd = status(flags, rid, allrows)
        if d.get("lane") == "gpu" and sd.get("state") in GPU_QUEUED_STATES and not sd.get("precond_parked"):
            gpu_queued = True
        if not runnable(sd):
            continue  # operator 2026-11-02: the dry run is publish_row's smoke; only PASSed, unparked rows are granted
        sby = sup_index.get(rid, "")
        if sby:   # PM-KEEPER3 #3: a superseded predecessor is never granted again (a running one is not a candidate anyway)
            sup_blocked[rid] = f"SUPERSEDED-BLOCK {rid} by {sby}: not granted (its successor is published)"
            continue
        kind = "grant"
        # 2026-11-03 session review item 2: UNDERUSED alerts, never blocks (it de-granted r3 for its engine's spin).
        k = contract_of(d, flags=flags)
        since = (load_json(pass_path(flags, rid)) or {}).get("passed_at")
        window = int(d["window_s"])
        cands.append({"id": rid, "kind": kind, "lane": d["lane"], "rank": row_rank(d), "lane_count": counts[d["lane"]],
                      "gib": int(d.get("gib") or 0), "bench": k["bench"], "options": k["options"], "shape": k["shape"], "window_s": window,
                      "estimate_s": int(d.get("estimate_s") or 0), "min_window_s": int(d.get("min_window_s") or 0),
                      "book_s": int(book_s(d)), "resumable": bool(d.get("resumable")), "whole_host_need": bool(d.get("whole_host_need")),
                      "since": iso_epoch(since), "ports": list(d.get("ports") or []), "arm_fails": int(sd.get("arm_fails") or 0),
                      "busy_fraction": d.get("busy_fraction"), "lock": k["lock"],
                      "claim": k["claim"], "threads": k["threads"], "explicit": bool(k["explicit_cpus"])})
    log_transition(flags, "superseded-block", sup_blocked, log, persist=not dry)
    if admit_hold:
        cands = []   # operator 2026-11-07: nothing new is granted; the reason was logged once on its transition
    qh_hold = None
    # 2026-11-21 (GPU idle 05:50-06:0xZ, queued smokes unrun): a DISK-PAUSE set admit_hold and gated the smoke batch too. A
    # queued smoke is not a new admission the pause protects against; only an operator HOLD file stops the batch.
    smoke_block = smoke_batch_blocked(flags)
    if GPU in free and not dry and not smoke_block and not gpu_batch_running(flags) \
            and glob.glob(os.path.join(flags, "dryrun", "*", "GPU-SMOKE-QUEUED.json")):
        try:   # operator D9 2026-11-11 "Hold smokes": a quiet-host row about to start keeps the GPU free of a smoke batch
            qh_hold = quiet_host_smoke_hold(
                cands, free, mem_available_gib(), time.time(), queued_gpu_batch_s(flags), gpu_open,
                held_ports={int(p) for g in grants for p in ((allrows.get(g["id"]) or {}).get("ports") or [])},
                grant_ends=[e for e in (iso_epoch(g["end"]) for g in grants if g.get("end")) if e],
                region_ends=region_end_map(flags, grants, busy), quiet_ok=quiet_ok_now(flags))
        except Exception as e:  # noqa: BLE001 - a fault in the hold check never stops allocation; smokes run as before
            log(f"SMOKE-HOLD check failed: {type(e).__name__}: {e}")
            qh_hold = None
    if not dry and not smoke_block and smoke_hold_lapsed(flags, qh_hold):
        log(f"SMOKE-HOLD-LAPSED {qh_hold[0]['id']}: held the queued GPU smokes > {QH_SMOKE_HOLD_MAX_S}s without starting; "
            "smokes run")
        qh_hold = None
    if qh_hold:
        hc, S = qh_hold
        log_transition(flags, "smoke-hold", {hc["id"]: f"SMOKE-HOLD: quiet-host {hc['id']} (rank {hc['rank']:g}) can start by "
                       f"{dt.datetime.fromtimestamp(S, dt.timezone.utc):%H:%MZ} (<= {QH_SMOKE_HOLD_S}s); queued GPU smoke batch "
                       f"({queued_gpu_batch_s(flags)}s) not started"}, log, persist=True)
        short = short_gpu_smokes(flags)
        short_s = sum(x[1] for x in short)
        if short and GPU in free and not dry and not smoke_block and time.time() + short_s <= S \
                and start_gpu_batch(flags, log, max_smoke_s=SHORT_SMOKE_S):
            free.discard(GPU)   # PM-KEEPER3 #2: the short slot finishes before the held quiet-host row can start
    else:
        log_transition(flags, "smoke-hold", {}, log, persist=not dry)
        if GPU in free and not dry and not smoke_block and start_gpu_batch(flags, log):
            free.discard(GPU)  # queued GPU smokes run in the gap before the next GPU grant
    slot = {}
    if gpu_open and not dry:   # PM-KEEPER3 #2: short smokes are booked for the next GPU grant boundary (never a preemption)
        try:
            short = short_gpu_smokes(flags)
            if short:
                g0 = next((g for g in grants if GPU in g["holds"]), {})
                ids = ",".join(r for r, _ in short[:6]) + (f",+{len(short) - 6}" if len(short) > 6 else "")
                slot[ids] = (f"SMOKE-SLOT {ids}: GPU smoke(s) <= {SHORT_SMOKE_S}s take the GPU at the next grant boundary "
                             f"({g0.get('end') or '?'}, end of {g0.get('id') or '?'}), ahead of the next full GPU grant; the "
                             "running grant is not preempted")
        except Exception as e:  # noqa: BLE001
            log(f"SMOKE-SLOT check failed: {type(e).__name__}: {e}")
    log_transition(flags, "smoke-slot", slot, log, persist=not dry)
    smoke_waits = []   # [(row, reason)]: ready rows taken out of the planner by WAIT-FOR-SMOKE; still named in IDLE-WHY
    qr = queued_gpu_min_rank(flags)   # operator 2026-11-06: a queued smoke competes by its OWN rank against ready rows
    wait_lines = {}
    if qr is not None:
        # a held quiet-host row is exempt: its smoke-hold already keeps the queued batch off the GPU for it
        _dp = drain_live(load_json(os.path.join(flags, "drain_state.json")))
        # PM-DRAINFIX 2026-11-22: a row with a live drain is exempt too - removing it dropped the drain and its T slid
        worse = [c for c in cands if any(GPU in o for o in c["options"]) and c["rank"] > qr
                 and not (qh_hold and c["id"] == qh_hold[0]["id"]) and c["id"] not in _dp]
        # E5 fix B 2026-11-23: a quiet-host row never waits behind queued smokes indefinitely; past the limit its drain forms
        starved = set(smoke_wait_starved(flags, worse, persist=not dry))
        log_transition(flags, "smoke-starved", {rid: f"SMOKE-WAIT-LIMIT {rid}: quiet-host row waited > "
                       f"{int(qh_smoke_wait_max_s(flags))}s behind queued GPU smokes (rank {qr:g}); it enters planning and "
                       "its drain forms; the smokes run after it or inside the drain" for rid in sorted(starved)},
                       log, persist=not dry)
        worse = [c for c in worse if c["id"] not in starved]
        if worse:
            smoke_waits += [(c, f"{c.get('shape') or c['kind']} row {c['id']} (rank {float(c['rank']):g}) WAIT-FOR-SMOKE: "
                                f"queued GPU smoke rank {qr:g} runs first") for c in worse]
            cands = [c for c in cands if c not in worse]
            wl = f"WAIT-FOR-SMOKE: queued GPU smoke rank {qr:g} runs first; GPU row(s) {','.join(c['id'] for c in worse[:5])} (worse rank) wait"
            wait_lines[wl] = wl
    else:
        smoke_wait_starved(flags, [], persist=not dry)   # no smoke queued: every quiet-host wait clock resets
    log_transition(flags, "wait-for-smoke", wait_lines, log, persist=not dry)   # only when the waiting set changes
    # keeper-scheduled smokes (operator 2026-11-05 "that's the keeper's ENTIRE point"): placed ahead of every row on
    # genuinely free cores, packed onto partly used quarters; and
    # never breaking a whole free quarter a queued whole-quarter row would take (placement packing, operator "fix it")
    try:   # GPU exclusivity (2026-11-05 kvu16g2-ab): host-view occupancy gates and audits EXCLUSIVE gpu-quiet grants
        one_sample = set()
        gwhy = None if dry else gpu_quiet_gate(flags, grants, allrows, log, seen, cands=cands, one_sample=one_sample)
    except Exception as e:  # noqa: BLE001 - an unreadable sysfs never stops allocation; it never admits either
        gwhy = f"device occupancy unreadable ({type(e).__name__}: {e})"
    try:   # GPU fence safety net: a KFD client inside a grant without the GPU token
        if not dry:
            gpu_fence_breach(flags, grants, log, seen)
    except Exception as e:  # noqa: BLE001 - the net never stops allocation
        log(f"GPU-FENCE sampler failed: {type(e).__name__}: {e}")
    held_back = []
    if gwhy:
        held_back = [c for c in gpu_held_back(cands) if c["id"] not in one_sample]
        # coordinator 2026-11-10 (rank-2 floor slipped 19:07Z -> 21:11Z): a held-back EXCLUSIVE row stays visible to
        # the planner with its GPU token replaced by GPU_BLOCKED (never free, no known end), so it can never be placed but
        # still drains for its other regions; it was removed outright and every quarter it needed was backfilled.
        cands = [c for c in cands if c not in held_back] + [
            dict(c, options=[frozenset((set(o) - {GPU}) | {GPU_BLOCKED}) for o in c["options"]]) for c in held_back]
        if held_back:
            log(f"IDLE-WHY {GPU}: {gwhy}; EXCLUSIVE row(s) {','.join(c['id'] for c in held_back[:5])} wait")
            for c in held_back:
                log(f"WAIT {c['id']}: gpu-quiet EXCLUSIVE needs a quiet device: {gwhy}")
    dfile = os.path.join(flags, "drain_state.json")
    drain_prev = {k: v for k, v in (load_json(dfile) or {}).items() if k in allrows}
    qh_drain = quiet_host_drain_target(cands, drain_prev)
    placed_smokes = []
    if not admit_hold:
        if qh_drain:   # QUIET-HOST-SMOKE 2026-11-12: a pocket smoke never starts under a quiet-host drain
            if glob.glob(os.path.join(flags, "dryrun", "*", "SMOKE-QUEUED.json")):
                log(f"SMOKE-WAIT quiet-host drain {qh_drain}: no pocket smoke starts until it is granted (not a failure)")
        else:
            # D9 2026-11-18 SMOKE-CPUS: a wide smoke never takes the regions of a row being drained for
            d_res = set()
            for c in cands:
                if c["id"] in drain_prev:
                    for o in c["options"]:
                        d_res |= set(o)
            # coordinator 2026-11-18: nor any option of a grantable/armed row that fits the free set this tick
            efree = expand(set(free))
            dem = set()
            for c in cands:
                for o in c["options"]:
                    eo = expand(set(o))
                    if eo <= efree:
                        dem |= eo
            placed_smokes = place_smokes(flags, free, log, dry=dry, timing_q=timing_quarters(flags, grants, allrows),
                                         drain_reserved=frozenset(d_res), gpu_queued=gpu_queued,
                                         demand_reserved=frozenset(dem))
    quiet_ok = quiet_ok_now(flags)
    if quiet_ok:
        smoke_live = quiet_host_smoke_live(flags, placed_smokes)
        if smoke_live:
            quiet_ok = False
            if any(c.get("shape") == "quiet-host" for c in cands):
                log(f"QUIET-HOST-WAIT smoke(s) live in pockets ({','.join(smoke_live[:5])}): no quiet-host grant this tick")
    # E5 fix A 2026-11-23: no quiet-host / whole-host grant while a foreign inference server runs (never kills it)
    lane, _lk = build_lane_open(flags)
    if lane:   # BUILD LANE: no NEW quiet row is granted (running ones are never pre-empted)
        hold = [c for c in cands if quiet_required(allrows.get(c["id"])) or c.get("shape") == "quiet-host"]
        log_transition(flags, "build-lane", {"lane": f"BUILD-LANE open for {lane}: no new quiet row granted ({','.join(c['id'] for c in hold[:5]) or '-'} held)"},
                       log, persist=not dry)
        cands = [c for c in cands if c not in hold]
    else:
        log_transition(flags, "build-lane", {}, log, persist=not dry)
    cands, fwaits = foreign_server_gate(flags, cands, grants, log, dry=dry)
    smoke_waits = fwaits + smoke_waits   # named in this tick's IDLE-WHY lines for the regions the row needs
    held_ports = {int(p) for g in grants for p in ((allrows.get(g["id"]) or {}).get("ports") or [])}
    ends = [iso_epoch(g["end"]) for g in grants if g.get("end")]
    r_ends = region_end_map(flags, grants, busy)
    out, excluded, plan_free, ram = [], set(), set(free), mem_available_gib()
    util = measure_util()
    try:   # PM-KEEPER3 #1: quiet-host rows only onto quiet quarters, never beside whole-host / bandwidth-heavy rows
        qres = {"now": time.time(), "max_s": quiet_reserve_max_s(flags)}
        qst_p = os.path.join(state_dir(flags), QUIET_RESERVE_STATE)
        qst = load_json(qst_p) or {}
        qres["since"] = qst.get("since") if qst.get("active") else None
        cands, qwaits, qlines = quiet_gate(cands, allrows, grants, util, flags, reserve=qres)
        for line in qlines.values():
            log(line)
        if not dry:
            new = {"active": qres.get("active", False), "released": qres.get("released", False), "rows": qres.get("rows", []),
                   "since": qres.get("since"), "max_s": qres["max_s"], "ts": qres["now"]}
            try:
                atomic_json(qst_p, new)
            except Exception:  # noqa: BLE001
                pass
        smoke_waits = qwaits + smoke_waits
        noisy = {m.group(1) for line in qlines.values() for m in [re.search(r"foreign busy \S+ on (q\d)", line)] if m}
        if noisy and not dry:
            noise = quiet_noise(flags, noisy, grants)
            nl = {f"{q}:{pid}": f"QUIET-NOISE {q}: pid {pid} {comm} {pct}% ({cmd}) - unclaimed (no grant owns it); its "
                                f"owner must claim a region (rowflow.py claim --build) or move it"
                  for q, pid, comm, pct, cmd in noise[:8]}
            for line in nl.values():
                log(line)
    except Exception as e:  # noqa: BLE001 - a gate fault never stops allocation
        log(f"QUIET-GATE failed: {type(e).__name__}: {e}")
    idle_now = idle_held(flags, grants, holders, util, log, seen)
    if not dry:
        scratch_over(flags, grants, log)
        large_derived_check(flags, grants, log)
        try:   # operator 2026-11-05: IDLE-HELD tells the owner (notify-only; never ends a grant)
            idle_held_notify(flags, idle_now, grants, log, wanted=cands)
        except Exception as e:  # noqa: BLE001 - a warning never stops allocation
            log(f"IDLE-HELD-WARN failed: {type(e).__name__}: {e}")
        try:   # F6: a launcher alive over a dead job ends its grant (alert first, then the STOP file; never a kill)
            idle_after_crash(flags, grants, util, log)
        except Exception as e:  # noqa: BLE001
            log(f"IDLE-AFTER-CRASH failed: {type(e).__name__}: {e}")
        try:   # B1: a smoke marker removed outside PASS/FAIL/withdraw/drop reaches the owner
            orphaned_smoke_alerts(flags, log=log)
        except Exception as e:  # noqa: BLE001
            log(f"QUEUED-SMOKE-ORPHANED check failed: {type(e).__name__}: {e}")
        try:   # F9: aged smoke markers reach their owners
            queued_aged_alerts(flags, log=log)
        except Exception as e:  # noqa: BLE001
            log(f"QUEUED-AGED check failed: {type(e).__name__}: {e}")
        try:   # F7: foreign processes on held quarters, attributed (pid, comm, cmdline, container, session)
            contamination_sample(flags, grants, log)
        except Exception as e:  # noqa: BLE001
            log(f"CONTAMINATION check failed: {type(e).__name__}: {e}")
    # 2026-11-03 session review item 7: a row that fails to arm or is refused at admission no longer idles the regions
    # planned for it until the next tick - the tick re-plans the still-free regions without it (bounded by the number
    # of candidates); plan_order already puts arm-failed rows last so a healthy row is never behind one.
    for _pass in range(len(cands) + 1):
        bpol = build_pocket_policy(flags)
        bw = build_waiters(flags, rowids=set(allrows), log=log)
        assigned, idle, pending = plan(plan_free, [c for c in cands if c["id"] not in excluded], ram, gpu_open,
                                        grant_ends=[e for e in ends if e], quiet_ok=quiet_ok, held_ports=held_ports,
                                        drain_prev=drain_prev, region_ends=r_ends, region_holders=holders,
                                        gpu_queued=gpu_queued, build_waiting=bool(bw), build_policy=bpol,
                                        stopping=stopping_tokens(flags, grants, allrows))
        _srl = {}
        for lc, hc, res in plan.stop_reserves:
            _srl.setdefault(hc["id"], set()).update(res)
        for hid, res in _srl.items():
            log(f"RESERVE-FOR-STOPPING {hid} regions={','.join(compress(res))}: its other regions are held by grants being stopped; "
                f"worse-ranked rows may take them only if they end within {int(bpol.get('stopping_horizon_s', 600))}s")
        for rid_h in plan.build_held:
            log(f"BUILD-POCKET-HELD {rid_h}: long q0-q2 row not booked while a build claim waits "
                f"({'; '.join(w['who'] for w in bw)}); declare whole_host_need to opt out")
        if not dry:
            atomic_json(dfile, drain_state_next(plan.last_drain, drain_prev, [c["id"] for c in cands if c["id"] not in excluded]
                                                + [c["id"] for c, _ in smoke_waits], [c["id"] for c, _ in assigned]))
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
        deferred = {dc["id"]: S for dc, S in plan.drain_deferred}
        for did, S in deferred.items():   # once per state change, not every tick
            if _DRAIN_DEFERRED_LOGGED.get(did) != S:
                log(f"DRAIN-DEFERRED {did}: earliest start {dt.datetime.fromtimestamp(S, dt.timezone.utc):%Y-%m-%dT%H:%MZ} "
                    f"beyond {DRAIN_RESERVE_HORIZON_S // 3600}h horizon; no reservation, its regions are backfilled by any row")
        _DRAIN_DEFERRED_LOGGED.clear(); _DRAIN_DEFERRED_LOGGED.update(deferred)
        for nc, why in plan.no_reserve:
            if nc["id"] in deferred:
                continue
            log(f"NO-RESERVE {nc['id']} ({nc.get('shape')}): earliest start unknown - {why}; its free regions are backfilled by any row")
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
                done = terminal_success(flags, rid) if COMPLETE_BEFORE_RC14 else None
                if done:   # the job finished since this tick's status() - nothing to arm, nothing failed
                    log(f"COMPLETE {rid}: {done} present; not armed, no FAIL")
                    failed.append(rid); continue
                a = load_json(armed_path(flags, rid))
                if a and alive(a.get("pid")) and not armed_engine_ok(a.get("pid"), rid):
                    st = stop_row_poller(flags, rid, d, a.get("pid"), log)
                    if st in ("job", "survived"):   # never start a second poller beside it
                        log(f"RE-ARM-HOLD {rid}: ARMED pid {a.get('pid')} not replaced ({st})")
                        failed.append(rid); continue
                    log(f"RE-ARM {rid}: ARMED pid {a.get('pid')} runs no filler_run*.sh engine for this row ({st}; re-armed)")
                    a = None
                if not (a and alive(a.get("pid"))):
                    pid, msg = arm_one(flags, rid, d, regions, log=log)
                    log(f"ROW-ARM {msg}")
                    if not pid:
                        failed.append(rid); continue
                else:
                    pid = a["pid"]
                end_cap = plan.hard_end.get(rid)
                win = capped_window(d["window_s"], end_cap)
                ok, line = admit(flags, rid, d, pid, regions, win)
                if not ok:
                    done = terminal_success(flags, rid) if COMPLETE_BEFORE_RC14 else None
                    if done:   # a dead poller AFTER the job's own completion receipt is completion, not rc=14
                        log(f"COMPLETE {rid}: admission refused ({line[:120]}) but {done} present; counted as completion, no FAIL")
                        failed.append(rid); continue
                    n = record_arm_fail(flags, rid, d, "launch", f"admission refused the armed poller: {line[:300]}", log)
                    if _PRECOND_REFUSED in line:   # one FAIL, one alert, parked now
                        log(f"PARK {rid}: {line[:200]}; precond refusal is terminal for this launcher+spec (1 FAIL, 1 alert); "
                            f"retried after a launcher/spec edit or `rowflow.py unpark {rid}`")
                    else:
                        log(f"SKIP {rid}: {line[:200]} ({n} consecutive arming/launch failures since the PASS; parked at {MAX_FAILS})")
                    stop_poller_if_parked(flags, rid, d, pid, line, n, log)
                    failed.append(rid); continue
                # the engine's region-lock claim IS the contract: a CONTRACT_LOCK engine locks lock= instead of --claim-cpus
                gl = write_grant(flags, rid, regions, opt, win, (c.get("explicit_cpus") or lock_cpus(opt)) if c.get("lock") and c.get("claim") else "",
                                 end_cap=end_cap)
                if end_cap:
                    log(f"HARD-END-CAP {rid}: admitted by book_s {int(book_s(d))}s ahead of "
                        f"{dt.datetime.fromtimestamp(end_cap, dt.timezone.utc):%H:%MZ}; grant ends there (engine hard-end kills an overrun)")
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
    # pipeline audit 2026-11-10 #2: a row that failed to arm/launch this tick may have just parked (its MAX_FAILS-th
    # refusal, or a precond refusal); runnable() is asked again so it is never reported as "fits but was not placed".
    tried = excluded | set(failed)
    if tried and not dry:
        gone = {rid for rid in tried if not runnable(status(flags, rid, allrows))}
        if gone:
            cands = [c for c in cands if c["id"] not in gone]
            pending = [c for c in pending if c["id"] not in gone]
    for r, why in idle.items():
        if r == GPU and held_back:
            continue   # already reported above with the actual reason; the planner never saw these rows
        if r in plan.idle_entries:
            head, rest = plan.idle_entries[r]
            why = idle_why_line(head, rest + [w for c, w in smoke_waits if any(r in o for o in c["options"])])
        elif any(r in o for c, _ in smoke_waits for o in c["options"]):
            sw = [w for c, w in smoke_waits if any(r in o for o in c["options"])]
            why = idle_why_line(sw[0], sw[1:])
        if r == GPU:
            why = gpu_idle_smoke_note(flags, why, smoke_block, qh_hold)
        log(f"IDLE-WHY {r}: {why}")
    for r, why in idle_partial_quarters(flags, free, busy, grants, holders).items():   # idle CPU quarters too
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
        try:  # early warning at floor+40 GiB (2026-11-23): tell owners BEFORE the pause, with the top reclaimable dirs
            notify.disk_warn_check(flags, os.path.join(state_dir(flags), "disk_warn.json"), reclaim_root=TMP, log=log)
        except Exception as e:  # noqa: BLE001 - an alerting fault must not stop allocation
            log(f"DISK-WARN check failed: {type(e).__name__}: {e}")
        try:  # inference mailbox: a CRITICAL alert unacked for ROWFLOW_ALERT_ESCALATE_S -> operator alarm, exactly once
            if notify.is_live(flags):
                notify.escalate_stale(flags, lambda k, m, ev: route_alert(f"{k}-{ev['key']}", m, ev, log), log=log)
        except Exception as e:  # noqa: BLE001
            log(f"ALERT-UNACKED check failed: {type(e).__name__}: {e}")
        idle_violation(flags, free, cands, out, mem_available_gib(), gpu_open, held_ports, log, util=util)
        underused(flags, holders, log, seen, vram=vram_used_bytes() if GPU in holders else None)
        try:
            build_idle_release(flags, holders, log)
        except Exception as e:  # noqa: BLE001 - an auto-release fault must not stop allocation
            log(f"BUILD-AUTO-RELEASE failed: {type(e).__name__}: {e}")
        repeat_alert(flags, seen, log)
    return out


def gpu_held_back(cands):
    """Rows kept off the device while the quiet gate is closed: every EXCLUSIVE (bench) GPU row, plus any worse-ranked
    GPU row (2026-11-08 rank inversion: shared vidya-r234 r24 took the MI210 while exclusive c8-fold2 r14 waited 1/2)."""
    gpu = lambda c: any(GPU in o for o in c["options"])
    held = [c for c in cands if c["bench"] and gpu(c)]
    if held:
        best = min(c["rank"] for c in held)
        held += [c for c in cands if c not in held and gpu(c) and c["rank"] > best]
    return held


# ---------------------------------------------------------------- GPU exclusivity: host-view device occupancy
KFD_PROC = "/sys/class/kfd/kfd/proc"   # one dir per KFD client, HOST pids, every container (pid=host, privileged)
GPU_FOREIGN_VRAM_MAX = float(os.environ.get("ROWFLOW_GPU_FOREIGN_VRAM_GIB", "1")) * (1 << 30)
GPU_QUIET_SAMPLES = 2   # transient KFD clients come and go: two consecutive quiet samples before an exclusive grant


def gpu_occupancy():
    """{pid: vram bytes} of every KFD client on the host (other projects' dev containers included: their MI210 use is
    invisible to region-lock), plus the device's total VRAM in use from amdgpu sysfs."""
    pids = {}
    try:
        for q in os.listdir(KFD_PROC):
            if q.isdigit():
                v = 0
                for f in glob.glob(os.path.join(KFD_PROC, q, "vram_*")):
                    try:
                        v += int(open(f).read().strip() or 0)
                    except (OSError, ValueError):
                        pass
                pids[int(q)] = v
    except OSError:
        pass
    used = None
    for f in glob.glob("/sys/class/drm/card*/device/mem_info_vram_used"):
        try:
            used = max(used or 0, int(open(f).read().strip()))
        except (OSError, ValueError):
            pass
    return {"pids": pids, "vram_used": used}


def gpu_foreign(occ, own=frozenset()):
    """(foreign pids, their VRAM bytes): KFD clients outside `own` (a grant's process tree)."""
    f = {p: v for p, v in (occ.get("pids") or {}).items() if p not in own}
    return sorted(f), sum(f.values())


def running_smoke_gpu_occupants(flags, occ=None):
    """PM-SMOKEFIX 2026-11-22 (ak-ea-pool-screen-gpu-20261122-r3: the keeper's OWN GPU smoke, filler_run15 -> job.py ->
    llama-server, was reported "foreign KFD pids ... hold 26.9 GiB" and blocked every GPU grant). {smoke id: {"pids": the
    KFD pids of its tree, "until": window end or None}} for every LIVE smoke that holds the gpu: its dryrun/<id>/RUNNING.json
    pid (+ its pgid and harness_pid) and its SMOKE.lock sidecar pid, each with its descendants (harness_tree). A smoke counts
    as an occupant when its tree owns a KFD pid or its regions name the MI210; a CPU-only smoke is not a gpu-quiet holder."""
    occ_pids = (occ or {}).get("pids") or {}
    out = {}
    for rp in glob.glob(os.path.join(flags, "dryrun", "*", "RUNNING.json")) + glob.glob(os.path.join(flags, "dryrun", "*", "SMOKE.lock")):
        rid = os.path.basename(os.path.dirname(rp))
        d = load_json(rp) or {}
        roots = [int(x) for x in (d.get("pid"), d.get("pgid"), d.get("harness_pid")) if str(x or "").isdigit() and proc_alive(x)]
        if not roots:
            continue
        tree = set()
        for r in roots:
            try:
                tree |= {int(r)} | set(harness_tree(int(r), {}))
            except Exception:  # noqa: BLE001 - an unreadable /proc entry never hides a live root
                tree.add(int(r))
        mine = sorted(p for p in occ_pids if p in tree)
        rr = load_json(running_path(flags, rid)) or {}
        if not mine and "mi210" not in str(rr.get("regions") or ""):
            continue
        e = out.setdefault(rid, {"pids": [], "until": None})
        e["pids"] = sorted(set(e["pids"]) | set(mine))
        e["until"] = e["until"] or rr.get("deadline")
    return out


SMOKE_EXIT_FRESH_S = 1800   # the one-sample path is for a smoke that JUST exited; every PASSed row keeps a record, so age must bound it


def smoke_exited_path(flags, rid): return os.path.join(dry_dir(flags, rid), "SMOKE-EXITED.json")


def record_smoke_exit(flags, rid, pgid, tracked, survivors):
    """The harness's receipt that this smoke's tree was reaped. No receipt when anything survived. Never raises."""
    try:
        if survivors:
            _rm(smoke_exited_path(flags, rid))
        else:
            atomic_json(smoke_exited_path(flags, rid), {"id": rid, "pgid": int(pgid), "pids": sorted(int(x) for x in tracked), "exited_at": now_iso()})
    except (OSError, TypeError, ValueError):
        pass


def smoke_tree_proven_dead(flags, rid, now=None):
    """True only when rid's fresh exit receipt exists and ps proves nothing of its tree remains: no RUNNING.json, no live
    process in its session/pgid, no recorded pid or child of one. A recycled pid counts as NOT proven. Any doubt is False."""
    r = load_json(smoke_exited_path(flags, rid)) or {}
    if os.path.exists(running_path(flags, rid)) or not r.get("pids"):
        return False
    t = iso_epoch(r.get("exited_at"))
    if t is None or (time.time() if now is None else now) - t > SMOKE_EXIT_FRESH_S:
        return False
    try:
        pg, tracked = int(r["pgid"]), {int(x) for x in r["pids"]}
        ps = subprocess.run(["ps", "-eo", "pid=,ppid=,pgid=,sid=,stat="], capture_output=True, text=True, timeout=10)
        lines = [x.split() for x in ps.stdout.splitlines()]
        if ps.returncode != 0 or not lines:
            return False
        for f in lines:
            if not f[4].startswith("Z") and (int(f[2]) == pg or int(f[3]) == pg or int(f[0]) in tracked or int(f[1]) in tracked):
                return False
    except (KeyError, IndexError, TypeError, ValueError, OSError, subprocess.SubprocessError):
        return False
    return True


def gpu_one_sample_row(flags, occ, cands, last_kfd=None):
    """The one row allowed to go on a single quiet sample: the best-ranked waiting exclusive GPU row, its smoke proven dead, and
    no KFD owner of any size on a readable device, and none sighted since that smoke exited (last_kfd: the transient
    two samples exist for). Best-ranked only: never a rank inversion."""
    if occ.get("pids") or not os.path.isdir(KFD_PROC):
        return None
    ex = [c for c in gpu_held_back(cands) if c.get("bench")]
    if not ex:
        return None
    c = min(ex, key=lambda x: (x["rank"], x["id"]))
    if last_kfd:
        ex_at, seen = iso_epoch((load_json(smoke_exited_path(flags, c["id"])) or {}).get("exited_at")), iso_epoch(last_kfd)
        if ex_at is None or seen is None or ex_at <= seen:
            return None
    return c["id"] if smoke_tree_proven_dead(flags, c["id"]) else None


def gpu_quiet_gate(flags, grants, allrows, log, seen, cands=(), one_sample=None):
    """Before an EXCLUSIVE gpu-quiet grant: True only after GPU_QUIET_SAMPLES consecutive samples with no foreign KFD
    client holding >= GPU_FOREIGN_VRAM_MAX (no GPU grant open: every client is foreign). While an exclusive grant is held:
    a foreign client above the threshold alarms once and marks the grant contaminated (dryrun/<id>/CONTAMINATED.json).
    A sample that still waits may name, in `one_sample`, the single row whose own smoke exit justifies going now."""
    occ = gpu_occupancy()
    sp = os.path.join(state_dir(flags), "gpu_quiet.json")
    st = load_json(sp) or {}
    held = [g for g in grants if GPU in g["holds"]]
    last_kfd = now_iso() if occ.get("pids") else st.get("last_kfd_at")   # absent: none sighted since receipts began
    kfd_rec = {"last_kfd_at": last_kfd} if last_kfd else {}
    if not held:
        sm = running_smoke_gpu_occupants(flags, occ)   # a running smoke's own tree is an occupant, never foreign
        pids, v = gpu_foreign(occ, {p for e in sm.values() for p in e["pids"]})
        n = int(st.get("quiet_n") or 0) + 1 if v < GPU_FOREIGN_VRAM_MAX and not sm else 0
        # own-exit fast path (2026-11-07): our grant ended + its tree dead -> one quiet sample; any foreign sighting drops the record
        lo = st.get("last_owner") or {}
        own_exit = bool(lo.get("ids")) and n >= 1 and all(
            os.path.exists(os.path.join(flags, "grants", i + ".ended")) for i in lo["ids"]) and not any(
            alive(x) for x in lo.get("pids") or [])
        need = 1 if own_exit else GPU_QUIET_SAMPLES
        keep = {"last_owner": lo} if lo and 1 <= n < need else {}
        atomic_json(sp, {"quiet_n": n, "at": now_iso(), "foreign_pids": pids[:20], "foreign_vram": v, **keep, **kfd_rec})
        smoke_why = "; ".join(f"held by smoke {i} until {e['until'] or '?'}" for i, e in sorted(sm.items()))
        why = None if n >= need else (
            (smoke_why + (f"; plus foreign KFD pids {','.join(map(str, pids[:8]))} hold {v / (1 << 30):.1f} GiB"
                          if v >= GPU_FOREIGN_VRAM_MAX else "")) if sm else
            f"device not quiet (host view): foreign KFD pids {','.join(map(str, pids[:8])) or '-'} hold {v / (1 << 30):.1f} GiB"
            if v >= GPU_FOREIGN_VRAM_MAX else f"device quiet {n}/{GPU_QUIET_SAMPLES} samples")
        if why and n == 1 and one_sample is not None:
            rid = gpu_one_sample_row(flags, occ, cands, last_kfd)
            if rid:
                one_sample.add(rid)
                log(f"GPU-QUIET one sample for {rid}: its smoke exited, tree proven dead, no KFD owners")
        return why
    atomic_json(sp, {"quiet_n": 0, "at": now_iso(), **kfd_rec, "last_owner": {"ids": [g["id"] for g in held], "pids": sorted(
        {p for g in held for p in own_pids(flags, g, (occ.get("pids") or {}))})}})
    for g in held:
        d = allrows.get(g["id"]) or {}
        if not contract_of(d)["bench"]:
            continue
        pids, v = gpu_foreign(occ, own_pids(flags, g, (occ.get("pids") or {})))
        if v >= GPU_FOREIGN_VRAM_MAX:
            cp = os.path.join(dry_dir(flags, g["id"]), "CONTAMINATED.json")
            if not os.path.exists(cp):
                atomic_json(cp, {"id": g["id"], "at": now_iso(), "foreign_pids": pids[:50], "foreign_vram": v,
                                 "vram_used": occ.get("vram_used")})
                route_alert("gpu-contaminated", f"{g['id']}: gpu-quiet EXCLUSIVE grant shares the MI210 with foreign KFD "
                            f"pids {','.join(map(str, pids[:8]))} ({v / (1 << 30):.1f} GiB); its timing is contaminated",
                            {"row": g["id"], "foreign_pids": pids[:50], "foreign_vram": v}, log)
            log(f"GPU-CONTAMINATED {g['id']}: foreign KFD pids {','.join(map(str, pids[:8]))} hold {v / (1 << 30):.1f} GiB "
                f"under its EXCLUSIVE grant ({cp})")
            seen.add(f"gpu-contaminated:{g['id']}")
    return None


def gpu_fence_breach(flags, grants, log, seen, occ=None):
    """GPU FENCE safety net (operator 2026-11-05 "fix it"; codex3-cs8-stt5 r3/r4 ran the HIP whisper-cli from a CPU-lane
    Python job). filler_run15 fences every grant WITHOUT the GPU token off the MI210; each tick, any KFD client
    (/sys/class/kfd/kfd/proc, host pids) inside such a grant's process tree means the fence was bypassed: log
    `GPU-FENCE-BREACH <id> <pid>`, alert once per row, mark the row contaminated (dryrun/<id>/CONTAMINATED.json).
    Returns [(id, pid)]."""
    occ = gpu_occupancy() if occ is None else occ
    kfd = set(occ.get("pids") or {})
    out = []
    if not kfd:
        return out
    for g in grants:
        if GPU in g["holds"]:
            continue
        hit = sorted(kfd & own_pids(flags, g, kfd))
        for pid in hit:
            log(f"GPU-FENCE-BREACH {g['id']} {pid}")
            out.append((g["id"], pid))
        if not hit:
            continue
        seen.add(f"gpu-fence-breach:{g['id']}")
        cp = os.path.join(dry_dir(flags, g["id"]), "CONTAMINATED.json")
        if not os.path.exists(cp):
            os.makedirs(os.path.dirname(cp), exist_ok=True)
            atomic_json(cp, {"id": g["id"], "at": now_iso(), "reason": "gpu-fence-breach", "kfd_pids": hit[:50],
                             "vram": sum((occ.get("pids") or {}).get(p, 0) for p in hit)})
            route_alert("gpu-fence-breach", f"{g['id']}: grant without the GPU token opened the MI210 (KFD pids "
                        f"{','.join(map(str, hit[:8]))}); fence bypassed, row marked contaminated",
                        {"row": g["id"], "kfd_pids": hit[:50]}, log)
    return out


IDLE_VIOLATION_TICKS = 2


# the deployed engine (compute-flags/bin/rowflow/) has no ../coordination/: fall back to the repo's alarm channel
ALARM_CHANNEL_REAL = "/workspace/scripts/coordination/alarm_channel.py"


def _alarm_channel_path():
    env = os.environ.get("ROWFLOW_ALARM_CHANNEL")
    if env:
        return env
    near = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "coordination", "alarm_channel.py")
    if os.path.isfile(near):
        return near
    return ALARM_CHANNEL_REAL


ALARM_CHANNEL = _alarm_channel_path()


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


def smoke_batch_blocked(flags):
    """Why the allocator must not start a queued-GPU-smoke batch, else None: an operator HOLD_* file or the operator's
    HOLD-ADMISSIONS file. A DISK-PAUSE is NOT a reason (it gates new grants; a smoke is short and was starved by it)."""
    holds = operator_holds(flags)
    if holds:
        return holds[0]
    if os.path.exists(os.path.join(flags, diskpause.HOLD_FILE)):
        return diskpause.HOLD_FILE
    return None


def gpu_idle_smoke_note(flags, why, blocked=None, qh_hold=None):
    """IDLE-WHY gpu-quiet must name queued smokes: they are not planner candidates, so 'no runnable row needs it' lied."""
    q = sorted(os.path.basename(os.path.dirname(x)) for x in glob.glob(os.path.join(flags, "dryrun", "*", "GPU-SMOKE-QUEUED.json")))
    if not q:
        return why
    ids = ",".join(q[:5]) + (f",+{len(q) - 5}" if len(q) > 5 else "")
    if blocked:
        st = f"not started: operator hold {blocked}"
    elif qh_hold:
        st = f"held for quiet-host {qh_hold[0]['id']}"
    elif gpu_batch_running(flags):
        st = "batch running"
    else:
        st = "batch starts this tick"
    return f"{why}; {len(q)} queued GPU smoke(s) ({ids}) {st}"


def start_gpu_batch(flags, log, max_smoke_s=None):
    """GPU free + queued smokes: start ONE detached batch (publish_row.py --run-gpu-queue) under a lock. True = the
    batch owns the GPU this tick (running or just started), so no GPU grant is assigned. max_smoke_s: a SHORT SLOT batch
    that runs only the markers whose smoke_s <= it (PM-KEEPER3 #2)."""
    if gpu_batch_running(flags):
        return True
    if not (short_gpu_smokes(flags, max_smoke_s) if max_smoke_s else
            glob.glob(os.path.join(flags, "dryrun", "*", "GPU-SMOKE-QUEUED.json"))):
        return False
    os.makedirs(os.path.join(flags, "dryrun"), exist_ok=True)
    out = open(os.path.join(flags, "dryrun", "GPU-SMOKE-BATCH.out"), "a")
    argv = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "publish_row.py"),
            "--run-gpu-queue", "--flags", flags] + (["--max-smoke-s", str(int(max_smoke_s))] if max_smoke_s else [])
    p = subprocess.Popen(argv, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
    atomic_json(gpu_batch_lock(flags), {"pid": p.pid, "started": now_iso(), "max_smoke_s": max_smoke_s})
    log(f"GPU-SMOKE-BATCH started pid={p.pid}" + (f" (short slot: smokes <= {int(max_smoke_s)}s)" if max_smoke_s else ""))
    return True


# PM-KEEPER3 #2 (AK 2026-11-23): c19attr-a3b-gpu and c19-dtree-gpu-diag (30 s smokes) sat SMOKE-QUEUED from 10:01Z to
# 11:24Z behind vidya-r18d-aa-27b-r1's 2 h GPU grant. CHOSEN: option A, "place a short smoke at the next GPU grant
# boundary, ahead of the next full grant" - not option B (a reserved gap between grants). A uses the GPU only when a
# smoke exists, leaves grant windows and drain arithmetic untouched, and never idles the device; B would have to shorten
# or delay every GPU grant while smokes queue, i.e. carve idle reservations into the calendar. A running grant is never
# preempted. Mechanics: (1) while a GPU grant is open and smokes <= SHORT_SMOKE_S are queued, SMOKE-SLOT names them and
# the boundary; (2) at the boundary the batch starts before the planner (unchanged order) in priority_rank order; (3)
# when the quiet-host smoke hold would hold the FULL batch, a short-slot batch (only smokes <= SHORT_SMOKE_S) still starts
# if it finishes before the held row could start - the same "smokes run in gaps they finish before" rule, applied to the
# short budget instead of the whole queue.
SHORT_SMOKE_S = 300


def short_gpu_smokes(flags, max_s=SHORT_SMOKE_S):
    """[(rid, smoke_s)] of queued GPU smokes whose declared budget (marker smoke_s) is <= max_s."""
    out = []
    for q in glob.glob(os.path.join(flags, "dryrun", "*", "GPU-SMOKE-QUEUED.json")):
        try:
            s_ = int((load_json(q) or {}).get("smoke_s") or QUEUED_SMOKE_DEFAULT_S)
        except (TypeError, ValueError):
            s_ = QUEUED_SMOKE_DEFAULT_S
        if s_ <= max_s:
            out.append((os.path.basename(os.path.dirname(q)), s_))
    return sorted(out)


# HOLD SMOKES FOR A QUIET-HOST ROW (operator D9 2026-11-11 "Hold smokes (Recommended)"; 14:20Z: AutoKernel's queued GPU
# smokes took the GPU lock, so the inf85 quiet-host row waited while all 4 CPU quarters sat idle). The keeper does not
# START a GPU-SMOKE-BATCH while a quiet-host row is the next drain/placement candidate and could start within
# QH_SMOKE_HOLD_S. Smokes still run in gaps they finish before that row could start (now + batch_s <= S).
QH_SMOKE_HOLD_S = 600
QUEUED_SMOKE_DEFAULT_S = 300   # publish_row.SMOKE_TIMEOUT_S: a marker without smoke_s


def queued_gpu_batch_s(flags):
    """Upper bound of the queued batch's wall time: the sum of the markers' smoke_s (they run one after another)."""
    tot = 0
    for q in glob.glob(os.path.join(flags, "dryrun", "*", "GPU-SMOKE-QUEUED.json")):
        try:
            tot += int((load_json(q) or {}).get("smoke_s") or QUEUED_SMOKE_DEFAULT_S)
        except (TypeError, ValueError):
            tot += QUEUED_SMOKE_DEFAULT_S
    return tot


def quiet_host_smoke_hold(cands, free, ram, now, batch_s, gpu_grant_open=False, held_ports=(), grant_ends=(),
                          region_ends=None, quiet_ok=True, horizon_s=QH_SMOKE_HOLD_S):
    """PURE. (c, S) when a GPU smoke batch must NOT start this tick, else None.

    c is the quiet-host candidate at the head of plan_order that needs the GPU, is not failing to arm, has no held port,
    fits RAM, and is not out-ranked by a better placeable row on its regions (drain_blocker) - i.e. the next drain /
    placement candidate. S is when it could start: now when its option fits the free regions (GPU included) or its
    holders are past their end; else earliest_start's S. Hold iff S - now <= horizon_s AND now + batch_s > S (the batch
    would still hold the GPU at S). Unknown S (foreign hold, beyond the busy window) or quiet hours off -> no hold."""
    if not quiet_ok or batch_s <= 0:
        return None
    qh = sorted((c for c in cands if c.get("shape") == "quiet-host" and any(GPU in o for o in c["options"])), key=plan_order)
    for c in qh:
        if int(c.get("arm_fails") or 0) > 0:
            continue
        if {int(p) for p in held_ports} & {int(p) for p in (c.get("ports") or [])}:
            continue
        if ram - float(c.get("gib") or 0) < RAM_MARGIN_GIB:
            continue
        if drain_blocker(c, cands, free, ram, gpu_grant_open, held_ports) is not None:
            continue
        if any(o and o <= set(free) for o in c["options"]):
            S = now
        else:
            S, why = earliest_start(c, set(free), now, grant_ends, region_ends)
            if S is None:
                if why and "expired" in why:
                    S = now
                else:
                    return None
        if S - now <= horizon_s and now + batch_s > S:
            return c, S
        return None
    return None


QH_SMOKE_HOLD_MAX_S = 2 * QH_SMOKE_HOLD_S   # a hold whose row has not started by then lapses (no indefinite GPU idle)


def smoke_hold_lapsed(flags, hold, now=None):
    """Persist when the current smoke hold began (per held row id). True when the same row has held the batch off for
    more than QH_SMOKE_HOLD_MAX_S: the row did not start (a constraint the hold check cannot see), so smokes run again.
    hold None clears the state."""
    now = time.time() if now is None else now
    p = os.path.join(state_dir(flags), "smoke_hold.json")
    old = load_json(p) or {}
    if not hold:
        if old:
            atomic_json(p, {})
        return False
    rid = hold[0]["id"]
    since = float(old["since"]) if old.get("id") == rid and old.get("since") else now
    if old.get("id") != rid:
        atomic_json(p, {"id": rid, "since": since})
    return now - since > QH_SMOKE_HOLD_MAX_S


def gpu_batch(flags, log=print):
    """`rowflow.py gpu-batch` (session review 2026-11-03 §5 item 8): ANY session runs the queued GPU smokes on a GPU-free
    tick - the same start_gpu_batch the allocator calls on every allocate tick (that path is unchanged). One line out.
    Returns 0 (started / already running / nothing queued) or 3 (HOLD present or GPU busy: re-run later)."""
    me = f"python3 {os.path.abspath(__file__)} gpu-batch"
    queued = glob.glob(os.path.join(flags, "dryrun", "*", "GPU-SMOKE-QUEUED.json"))
    holds = operator_holds(flags)
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
    s = sub.add_parser("release", help="owner-only: end an idle/finished grant early, or shrink it with --regions q2,..; refused while its job runs (never kills)")
    s.add_argument("id"); s.add_argument("--by"); s.add_argument("--reason", required=True); s.add_argument("--regions")
    s = sub.add_parser("resume", help="owner-only: requeue a STOPPED / released-early resumable row under the SAME id (clears STOP + the terminal end, back to ready/, no new smoke)")
    s.add_argument("id"); s.add_argument("--by"); s.add_argument("--reason", required=True)
    s = sub.add_parser("unpark", help="operator: a parked row (precond refusal / arming failures) is grantable again next tick; its "
                                      "earlier arming FAIL records no longer count (dryrun/<id>/UNPARK.json)")
    s.add_argument("id"); s.add_argument("--by"); s.add_argument("--note", default="")
    s = sub.add_parser("allocate", help="ONE snapshot per tick: heal, assign dry runs + grants together, write grants, log IDLE-WHY/UNDERUSED")
    s.add_argument("--log", help="keeper log the detached dry runs append DRYRUN-RESULT to (default <flags>/ws58-calendar-keeper.log)")
    s.add_argument("--plan", action="store_true", help="snapshot + plan only; change nothing")
    s = sub.add_parser("claim", help="F7: claim a short build lane: claim --build --owner <id> --cpus N|LIST --minutes M (--cpus 72-87 = the q3 pocket, never 88-95/184-191)")
    s.add_argument("--build", action="store_true", required=True); s.add_argument("--owner", required=True)
    s.add_argument("--cpus", required=True); s.add_argument("--minutes", type=int, required=True)
    s.add_argument("--wait-pid", type=int, default=None, help="pid whose liveness keeps a refused claim's build-wait record live (default: the invoking parent)")
    s.add_argument("--light", action="store_true", help="LIGHT test claim: --cpus a subset of 84-87 (<= 4 cores), --minutes <= 15, one light claim host-wide, "
                   "not bandwidth-heavy (never blocks a quiet row); refused while a running quiet row logged a contended launch in the last 10 min. "
                   "ADVISORY contract (not enforced): " + "; ".join(LIGHT_ADVISORY).replace("%", "%%"))
    s = sub.add_parser("build-window", help="open the BUILD LANE for N minutes (<= 90): no new quiet row is granted and QUIET-RESERVE stops refusing build claims; closes itself")
    s.add_argument("--minutes", type=int, required=True); s.add_argument("--by", required=True); s.add_argument("--reason", required=True)
    s = sub.add_parser("deploy-guard", help="deploy_rowflow step 3: rc 75 when a changed engine file would reach LEGACY open grants")
    s.add_argument("--changed", nargs="*", default=[]); s.add_argument("--allow-open-grants", action="store_true")
    sub.add_parser("legacy-grants", help="ids of open grants whose poller still reads the live engine path (one per line)")
    sub.add_parser("gpu-batch", help="run the queued GPU smokes now if the GPU is free (any session; the allocator does the same every tick)")
    s = sub.add_parser("alerts", help="read the inference mailbox (<flags>/notify/inbox/inference.jsonl); --ack <key> marks one handled")
    s.add_argument("--since", help="ISO time, e.g. 2026-11-05T07:00:00Z"); s.add_argument("--row", help="row-id glob")
    s.add_argument("--unacked", action="store_true"); s.add_argument("--json", action="store_true")
    s.add_argument("--ack", metavar="KEY"); s.add_argument("--by"); s.add_argument("--note")
    s.add_argument("--force-ack", action="store_true", help="ack even though the row ended without a FILED receipt")
    s.add_argument("--file", metavar="VERDICT", help="with --ack and --commit: file the row via file_result.py --receipt, then ack")
    s.add_argument("--commit", metavar="SHA", help="the verdict commit (on origin/main) whose handoff box records the verdict")
    a = ap.parse_args(argv)
    if a.cmd == "alerts":
        if a.ack:
            unfiled = notify.unfiled_ended(a.flags, a.ack)
            if unfiled and a.file and a.commit:
                import subprocess as _sp
                task = str((load_json(os.path.join(a.flags, "ready", unfiled + ".json")) or {}).get("handoff_task") or "")
                if ":" not in task:
                    for _m in glob.glob(os.path.join(a.flags, "ready", "*", unfiled + ".json")) + glob.glob(os.path.join(a.flags, "ready", ".withdrawn", unfiled + ".json")):
                        task = str((load_json(_m) or {}).get("handoff_task") or ""); break
                if ":" not in task:
                    print(f"REFUSED: {unfiled} has no handoff_task <handoff.md>:<BOX-ID> in its manifest; run file_result.py {unfiled} --receipt <commit>:<handoff>#<BOX> yourself")
                    return 2
                task = handoff_ref.repoint(task)   # C4: file the receipt against the box's CURRENT handoff
                hp, box = task.rsplit(":", 1)
                fr_py = next((p for p in (os.path.join(_HERE, "..", "churn", "file_result.py"), "/workspace/scripts/coordination/churn/file_result.py") if os.path.isfile(p)), None)
                if not fr_py:
                    print("REFUSED: churn/file_result.py not found"); return 2
                r = _sp.run([sys.executable, fr_py, unfiled, "--flags", a.flags, "--receipt", f"{a.commit}:{hp}#{box}", "--verdict", a.file],
                            capture_output=True, text=True, timeout=300)
                print((r.stdout + r.stderr).strip())
                if r.returncode != 0:
                    print(f"REFUSED: filing {unfiled} through the receipt path failed (rc={r.returncode}); alert NOT acked")
                    return 2
                unfiled = notify.unfiled_ended(a.flags, a.ack)
            if unfiled and not a.force_ack:
                print(f"WARNING: row {unfiled} has ENDED with no filing-done/{unfiled}.FILED receipt. Acking an alert is not filing "
                      f"(124 INF-22 rows were left unfiled that way). File it: `file_result.py {unfiled} --receipt <commit>:<handoff>#<BOX-ID>` "
                      f"or `rowflow.py alerts --ack {a.ack} --file <verdict> --commit <sha>`; or pass --force-ack to ack anyway.")
                return 3
            if unfiled:
                print(f"FORCE-ACK: row {unfiled} acked without a FILED receipt")
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
        if a.cmd == "claim":
            gid, line = claim_build(a.flags, a.owner, a.cpus, a.minutes, wait_pid=a.wait_pid, light=a.light)
            print(f"BUILD-GRANT {gid} {line}")
            return 0
        if a.cmd == "build-window":
            build_window(a.flags, a.minutes, a.by, a.reason)
            return 0
        if a.cmd == "withdraw":
            r = withdraw(a.flags, a.id, a.reason)
            print(f"{r} {a.id}")
            return 0 if r in ("WITHDRAWN", "PENDING", "TERMINAL") else 2
        if a.cmd == "release":
            by = a.by or next((os.environ[k] for k in notify.PUBLISHER_ID_ENV if os.environ.get(k)), "")
            r = release_grant(a.flags, a.id, by, a.reason, a.regions)
            print(f"{r} {a.id}")
            return 0
        if a.cmd == "resume":
            by = a.by or next((os.environ[k] for k in notify.PUBLISHER_ID_ENV if os.environ.get(k)), "")
            resume_row(a.flags, a.id, by, a.reason)
            return 0
        if a.cmd == "unpark":
            known = (a.id in rows(a.flags) or os.path.isdir(dry_dir(a.flags, a.id))
                     or os.path.exists(os.path.join(a.flags, "operator-escalations", a.id + ".md")))
            need(known, f"{a.id}: not a ready/ row, a dryrun/ id or a parked lineage (operator-escalations/<lineage>.md)")
            rec = unpark(a.flags, a.id, a.by or "", a.note)
            if a.id in rows(a.flags):
                st = status(a.flags, a.id)
                print(f"UNPARKED {a.id} at {rec['at']}; state now {st['state']}: {st.get('reason', '')[:160]}")
            else:
                print(f"UNPARKED lineage {a.id} at {rec['at']}; its earlier failed dry runs no longer count; rows in it re-enter the keeper next tick")
            return 0
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
        if a.cmd == "deploy-guard":
            ok, line = deploy_guard(a.flags, a.changed, a.allow_open_grants)
            print(line)
            return 0 if ok else 75
        if a.cmd == "legacy-grants":
            for rid in legacy_open_grants(a.flags):
                print(rid)
            return 0
    except Refused as e:
        print(f"REFUSED: {e}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
