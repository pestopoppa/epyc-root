#!/usr/bin/env python3
"""rowflow.py - the simplified inference-row pipeline (ws58, operator ruling 2026-11-01: remove every gate that is
not indispensable).

OWNER CONTRACT (two things): the launcher script and a small spec. `publish_row.py <spec.json>` derives the rest.

    spec (JSON)      required: id, owner, launcher (abs path, runs filler_run15.sh), lane (cpu|gpu),
                               result_path (what the filer reads), decision_rule, estimate_s, handoff_task
                     optional: result_format (jsonl|json|csv|tsv|text-lines|markdown-table|custom:<cmd>; default by
                               extension), regions (default gpu -> mi210_0,184-191; cpu -> any-cpu-quarter),
                               ram_gib (48), priority_rank (100), scratch_root (launcher's job dir), keep (globs),
                               dryrun_timeout_s (900 cpu / 1500 gpu), dryrun_native_result (count a unique per-attempt native JSON unit
                               without touching result_path), lineage, lineage_reset, supersedes, snapshot (true forces the snapshot below)

    SNAPSHOT RULE   a launcher, engine or job file under worktrees/ or /workspace (or a /workspace/repos/<x> target) is
                    copied at publish time into <scratch_root>/snapshot/ (git archive HEAD of its directory when the
                    worktree is clean, else a working-tree copy with dirty=true), paths rewritten, files chmod a-w; the
                    row's launcher/engine/result paths point INTO the snapshot. Row field `snapshot` records it.

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
    (the dry run is publish_row.py's smoke: rowflow.dryrun_run in the owner's turn; no CLI, no grant)
    status <id>               needs-dryrun | dryrun-running | failed | parked | stale | grantable | armed | running | done

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
STOP_GRACE_S = 600  # a job may finish its current item before honouring the stop file
DEFAULT_KEEP = ["**/*.json", "**/*.jsonl", "**/*.md", "**/*.txt", "**/*.csv", "**/*.tsv", "**/*.sh", "**/*.py"]
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
    return o


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
    # feet (lane merges before every resume, removal at session end), so it is snapshotted into the row's own scratch_root
    # and the row points INTO the snapshot - the dry run and the real run execute the same bytes by construction
    volatile = [p for p in [launcher] + referenced_paths(o) if volatile_root(p)]
    snap = None
    if volatile or spec.get("snapshot") is True:
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
    keep = list(spec.get("keep") or DEFAULT_KEEP)
    if result_path.startswith(scratch + "/"):
        rel = os.path.relpath(result_path, scratch)
        if rel not in keep:
            keep.append(rel)
    fmt = str(spec.get("result_format") or guess_format(result_path))
    need(fmt in ("jsonl", "json", "csv", "tsv", "text-lines", "markdown-table") or fmt.startswith("custom:"), f"unknown result_format {fmt}")
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
        "dryrun_timeout_s": int(spec.get("dryrun_timeout_s") or (1500 if lane == "gpu" else 900)),
        "published_at": now_iso(), "published_from": source or "spec",
    }
    if spec.get("total_units") is not None:
        row["total_units"] = int(spec["total_units"])
    if spec.get("admission_class") is not None:
        row["admission_class"] = spec["admission_class"]
    if snap:
        row["snapshot"] = snap
    elif isinstance(spec.get("snapshot"), dict):  # a republish from ready/<id>.json (publish_row.py --repair) keeps its snapshot record
        row["snapshot"] = spec["snapshot"]
    for k in ("lineage", "lineage_reset", "supersedes", "notes", "row", "dryrun_native_result"):
        if spec.get(k) is not None:
            row[k] = spec[k]
    if spec.get("shape") is not None:
        need(str(spec["shape"]) in SHAPES or re.fullmatch(r"multi-quarter\([2-3]\)", str(spec["shape"])), f"shape must be one of {SHAPES} or multi-quarter(n)")
        row["shape"] = str(spec["shape"])
    row["shape"] = shape_of(row, o)   # recorded: quarter | multi-quarter(n) | host | quiet-host | gpu
    atomic_json(ready_path(flags, rid), row)
    return row


def published_line(row, flags):
    return (f"PUBLISHED {row['id']} lane={row['lane']} regions={row['regions']} window_s={row['window_s']} min_window_s={row['min_window_s']} "
            f"gib={row['gib']} ports={row['ports']} result={row['result_path']} ({row['result_format']}) -> {ready_path(flags, row['id'])}")


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
            "estimate_s": int(m.get("window_s") or 3600), "handoff_task": m.get("row") or m.get("handoff") or "FILLERS:" + str(m.get("id")),
            "priority_rank": m.get("priority_rank", 100), "ram_gib": m.get("gib"), "scratch_root": m.get("scratch_root"),
            "min_window_s": o["min_window"]}
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


SHAPES = ("quarter", "multi-quarter", "host", "quiet-host", "gpu")
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


def row_rank(d):
    """A row's priority_rank as a float; absent/blank -> 100. (`or 100` turned an explicit rank 0 into 100.)"""
    r = (d or {}).get("priority_rank")
    try:
        return 100.0 if r is None or r == "" else float(r)
    except (TypeError, ValueError):
        return 100.0


def plan_order(c):
    """Candidate order. Urgent rows (rank < URGENT_RANK) go first by rank; within a rank, and for every other row,
    the starved lane (fewest live rows) goes first, then rank, then a grantable row before a dry run."""
    r = float(c["rank"])
    return (min(r, URGENT_RANK), c["lane_count"], r, 0 if c["kind"] == "grant" else 1, c["id"])


def drain_blocker(c, pending):
    """The best-ranked pending row (strictly better rank than c) that wants any region c's drain would hold, or None.
    A drain is never set for c while such a row is runnable: rank decides who gets the regions when they free."""
    need = set().union(*c["options"]) if c["options"] else set()
    better = [x for x in pending if x is not c and float(x["rank"]) < float(c["rank"]) and any(o & need for o in x["options"])]
    return min(better, key=plan_order) if better else None


def _fits(c, free, ram, gpu_grant_open):
    opts = [o for o in c["options"] if o and o <= free]
    if c.get("bench") and gpu_grant_open:
        opts = [o for o in opts if not (o & expand({"q3"}))]
    if ram - float(c.get("gib") or 0) < RAM_MARGIN_GIB:
        return []
    return opts


def plan(free, cands, ram_gib, gpu_grant_open=False, now=None, grant_ends=(), quiet_ok=True, held_ports=(), drain_prev=None):
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
    A row is neither promoted nor drained for while a better-ranked pending row wants any of its regions (drain_blocker);
    plan.drain_held = [(row, blocker)] names those rows for the log.
    PORTS (ws58 2026-11-02): a candidate whose cand["ports"] meet held_ports (running grants) or a port placed this tick
    waits; two rows declaring the same port are never co-scheduled.
    Returns (assigned [(cand, option)], idle {region: reason}, pending); plan.last_drain = (cand, T) or None."""
    now = time.time() if now is None else now
    free = set(free)
    if not any(t in CORES or t in THREADS for t in free):
        # abstract caller (regions only): a free quarter's cores/threads are free, and so are the MI210's host threads
        free = expand(free) | ({f"t{k}" for k in range(184, 192)} if GPU in free else set())
    else:   # token-level caller: a quarter is free for a whole-quarter row only when every core/thread it runs on is
        free = {t for t in free if t not in QUARTERS or expand({t}) <= free}
    for c in cands:   # ws58 sub-quarter: a whole quarter also holds its core tokens
        c["options"] = [frozenset(expand(o)) for o in c["options"]]
    pending = sorted(cands, key=plan_order)
    if not quiet_ok:
        pending = [c for c in pending if c.get("shape") != "quiet-host"]
    free, ram, out = set(free), float(ram_gib), []
    ports = {int(x) for x in held_ports}
    drain, T = None, None
    plan.drain_held = []
    for c in pending:
        big = any(len([r for r in o if r in QUARTERS]) >= 2 for o in c["options"])
        if big and (c.get("shape") == "quiet-host" or now - float(c.get("since") or now) >= DRAIN_AFTER_S):
            blocker = drain_blocker(c, pending)
            if blocker is not None:   # ws58 2026-11-02: a better-ranked row wants these regions; no promotion, no drain
                plan.drain_held.append((c, blocker))
                continue
            pending.remove(c); pending.insert(0, c)   # the drain row goes FIRST: at T it takes the host before any quarter row
            if not _fits(c, free, ram, gpu_grant_open):
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
            opts = _fits(c, free, ram, gpu_grant_open)
            if late:   # a row ending after T may only take regions the drain row does not need (T bounds backfill, never kills)
                opts = [o for o in opts if not (o & need_r)]
            if ports & {int(x) for x in (c.get("ports") or [])}:
                continue  # its port is held by a running grant: it waits
            if not opts:
                continue
            # prefer the smallest option, then the one other pending rows want least (keeps their alternatives open)
            demand = {r: sum(1 for x in pending if x is not c for o2 in x["options"] if r in o2) for r in free}
            o = min(opts, key=lambda o: (len(o), sum(demand[r] for r in o), sorted(o)))
            placed = (c, o)
            break
        if not placed:
            break
        c, o = placed
        out.append((c, frozenset(compress(o)))); free -= o; ram -= float(c.get("gib") or 0); pending.remove(c)
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


def status(flags, rid, allrows=None):
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
    if os.path.exists(os.path.join(G, rid + ".grant")) and not os.path.exists(running_path(flags, rid)):
        out.update(state="running", reason="grants/<id>.grant open"); return out
    run = load_json(running_path(flags, rid))
    if run and alive(run.get("pid")):
        out.update(state="dryrun-running", reason=f"dry run pid {run.get('pid')} since {run.get('started')}"); return out
    p = load_json(pass_path(flags, rid))
    fails = [load_json(x) or {} for x in fail_paths(flags, rid)]
    last_fail = fails[-1] if fails else None
    if p and p.get("launcher_sha256") == cur:
        a = load_json(armed_path(flags, rid))
        if a and alive(a.get("pid")):
            out.update(state="armed", reason=f"poller pid {a['pid']} on {a.get('queue')} regions={a.get('regions')}", regions=a.get("regions")); return out
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


_ACQ = re.compile(r"\[region-lock\] acquiring regions \[([^\]]*)\]")
_HELD = re.compile(r"\[region-lock\] held \[([^\]]*)\]")


def lock_waits(lines, holds):
    """Region sets a job asked region-lock for and has NOT been granted (acquire lines without a matching held line)."""
    asked = []
    for l in lines:
        m = _ACQ.search(l)
        if m:
            asked.append({x.strip().strip("'\"") for x in m.group(1).split(",") if x.strip()})
            continue
        m = _HELD.search(l)
        if m:
            got = {x.strip().strip("'\"") for x in m.group(1).split(",") if x.strip()}
            asked = [a for a in asked if a != got]
    return asked


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


def _same(pid, birth):
    st = _proc_stat(pid)
    return st is not None and st[2] == birth


def reap_pids(tracked, grace=20):
    """TERM every still-same process (and every process group one of them leads), wait up to grace s, KILL, verify via
    /proc. Only pids this harness started (or captured by row id) with a matching start time are signalled. Returns
    (reaped, survivors)."""
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


def row_dir_procs(rid, dirs):
    """pids (not ours) whose argv names rid or whose cwd lies under one of the row's own dirs, with start times."""
    out = {}
    dirs = [os.path.realpath(x) + os.sep for x in dirs if x and rid in x]  # only dirs that are the row's own
    for q in os.listdir("/proc"):
        if not q.isdigit() or int(q) == os.getpid():
            continue
        try:
            hit = rid in open(f"/proc/{q}/cmdline", "rb").read().decode("utf8", "replace")
            if not hit and dirs:
                cwd = os.path.realpath(os.readlink(f"/proc/{q}/cwd")) + os.sep
                hit = any(cwd.startswith(x) for x in dirs)
        except OSError:
            continue
        st = _proc_stat(int(q))
        if hit and st:
            out[int(q)] = st[2]
    return out


def record_fail(flags, rid, d, reason, extra):
    n = len(fail_paths(flags, rid)) + 1
    rec = {"id": rid, "at": now_iso(), "launcher_sha256": sha256(d["launcher"]["path"]) if os.path.isfile(d["launcher"]["path"]) else None,
           "row_sha256": row_sha(flags, rid), "rowflow_sha256": sha256(__file__), "reason": reason, "launcher_out_tail": tail(os.path.join(dry_dir(flags, rid), "launcher.out")),
           "fix_task": f"fix dry-run failure of {rid}: {reason} (see compute-flags/dryrun/{rid}/launcher.out; the keeper retries as soon as the launcher file changes)",
           **extra}
    atomic_json(os.path.join(dry_dir(flags, rid), f"FAIL-{n}.json"), rec)
    return rec


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
    Operator 2026-11-02: this is publish_row's pre-publish smoke, run in the owner's turn on 4 cpus (timeout smoke_s,
    FILLER_SMOKE=1 / FILLER_SMOKE_UNITS=1 for launchers that can shrink their unit count). Its admission token lives in
    the row's private dryrun dir, never in grants/: nothing is scheduled around a dry run."""
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
    timeout = int(smoke_s or d.get("dryrun_timeout_s") or 900)
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
    with open(grant, "w") as f:
        f.write(dryrun_grant_text(rid, d.get("admission_class"), regions, holds, start, end))
    out = open(os.path.join(dd, "launcher.out"), "a")
    out.write(f"\n==== dry run {now_iso()} regions={regions} launcher_sha={lsha} units_before={units0}\n"); out.flush()
    p = subprocess.Popen(["bash", lp], cwd=flags, env=env, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
    tracked = harness_tree(p.pid, {p.pid: (_proc_stat(p.pid) or (0, 0, None))[2]})  # setsid'd group: pgid == p.pid
    atomic_json(running_path(flags, rid), {"pid": p.pid, "pgid": p.pid, "started": now_iso(), "regions": regions, "launcher_sha256": lsha, "grant": grant})
    t0 = time.time()
    vram_max = None
    gpu = "mi210_0" in regions
    first_unit_at = None
    stop_requested = None
    warning = None
    ended = os.path.join(dd, "ended")
    verdict, reason = None, None
    lout = os.path.join(dd, "launcher.out")
    out_lines0 = len(tail(lout, 10**6))
    try:
        while True:
            for _ in range(5):
                time.sleep(1)
                harness_tree(p.pid, tracked)
            if gpu:
                v = vram_used_bytes()
                if v is not None:
                    vram_max = max(vram_max or 0, v)
            # a dry run must never wait on a lock: a region-lock acquire for regions outside what this dry run holds, or one
            # not satisfied within 60 s, is the row's defect (the job's own claim ignores WS58_REGIONS)
            waits = lock_waits(tail(lout, 10**6)[out_lines0:], holds)
            if waits and (waits[0] - holds or time.time() - t0 > 60):
                verdict, reason = "FAIL", (f"job waits on region-lock for {','.join(sorted(waits[0]))} while the dry run holds "
                                           f"{','.join(sorted(holds))}: a smoke never waits on a held region; the job's own "
                                           "region-lock claim must honour WS58_REGIONS under FILLER_SMOKE)")
                break
            units = count_units(result_path, result_format, d.get("workdir"))
            new_units = units - units0
            if new_units > 0 and first_unit_at is None:
                first_unit_at = now_iso()
                out.write(f"==== first unit at {first_unit_at}: {new_units} new unit(s) in {result_path}\n"); out.flush()
                if not os.path.exists(ended):
                    open(os.path.join(dd, "stop"), "w").close()
                    stop_requested = time.time()
            if os.path.exists(ended) or p.poll() is not None:
                rc_line = (head1(ended) or "rc=? (no ended record)")
                m = re.match(r"rc=(\d+)", rc_line)
                rc = int(m.group(1)) if m else -1
                units = count_units(result_path, result_format, d.get("workdir")) - units0
                if "reason=disk-floor" in rc_line or "reason=hard-end" in rc_line and units <= 0 and time.time() - t0 < 60:
                    verdict, reason = "WAIT", f"host condition, not the row: {rc_line[:100]} (free disk under the 150 GiB floor); retried later, no FAIL recorded"
                    break
                if units <= 0:
                    verdict, reason = "FAIL", f"job ended ({rc_line[:120]}) before writing a unit to {result_path} ({d['result_format']})"
                elif rc not in (0, 75):
                    verdict, reason = "FAIL", f"first unit written but the job ended {rc_line[:120]}"
                elif gpu and (vram_max is None or vram_max < 64 << 20):
                    verdict, reason = "FAIL", f"GPU row produced a unit but VRAM never showed residency (max {vram_max} B sampled during the run)"
                else:
                    verdict, reason = "PASS", f"{units} unit(s), {rc_line[:80]}"
                break
            if stop_requested and time.time() - stop_requested > STOP_GRACE_S:
                # the engine's hard-end kill is production's truncation path too: PASS with a warning, then stop the group
                warning = f"job did not stop within {STOP_GRACE_S}s of the stop file (FILLER_STOPFILE not honoured between items); truncated by signal"
                if gpu and (vram_max is None or vram_max < 64 << 20):
                    verdict, reason = "FAIL", f"GPU row produced a unit but VRAM never showed residency (max {vram_max} B sampled during the run)"
                else:
                    verdict, reason = "PASS", f"{count_units(result_path, result_format, d.get('workdir')) - units0} unit(s); {warning}"
                break
            if time.time() - t0 > timeout:
                started = any("START regions=" in l for l in tail(os.path.join(dd, "launcher.out"), 400))
                verdict, reason = "FAIL", f"no unit in {result_path} ({d['result_format']}) within dryrun_timeout_s={timeout}" + \
                                 (" (the job ran: if result_path is only a completion marker, point the spec at the job's per-item output, or raise dryrun_timeout_s)" if started
                                  else " and the engine never reached START (admission/precond/port refusal; see launcher.out)")
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
        # included): TERM the group + tracked descendants, 20 s, KILL, verify. Then anything still naming the row (argv,
        # or cwd under the row's own dirs) is stopped by its captured pid. Never left for the owner, never by name.
        harness_tree(p.pid, tracked)
        reaped, surv = reap_pids(tracked)
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        if reaped:
            out.write(f"==== REAPED {reaped}\n")
        orphans = row_dir_procs(rid, [x for x in (dd, d.get("workdir")) if x and rid in x])  # a shared workdir never counts
        if orphans:
            r2, s2 = reap_pids(orphans)
            out.write(f"==== ORPHANS {sorted(orphans)} still naming this row after the dry run ended; REAPED {r2}\n")
            surv += s2
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
        if verdict == "FAIL" and one_quarter:
            reason += (f" [dry run held ONE quarter, WS58_REGIONS={ws58_cpus(regions)}; a launcher whose own taskset/claim "
                       "hard-codes a wider cpu list must honour WS58_REGIONS under FILLER_DRYRUN]")
        out.write(f"==== dry run {verdict}: {reason} ({now_iso()})\n"); out.close()
    cur_sha = sha256(lp) if os.path.isfile(lp) else None
    if verdict == "PASS" and cur_sha != lsha:
        verdict, reason = "FAIL", "launcher changed while the dry run was running"
    rec = {"regions": regions, "units": count_units(result_path, result_format, d.get("workdir")) - units0, "result_path": result_path,
           "result_format": result_format, "first_unit_at": first_unit_at, "vram_used_max_bytes": vram_max,
           "engine_sha256": sha256(d["engine"]["path"]) if os.path.isfile(d["engine"]["path"]) else None,
           "ended": head1(ended) or None, "warning": warning, "dryrun_log": os.path.join(dd, "launcher.out"), "elapsed_s": int(time.time() - t0)}
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
def arm_one(flags, rid, d, regions=None):
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
        record_fail(flags, rid, d, "poller did not log 'launcher up pid=' within 30 s of arming", {})
        return None, "fail: no launcher pid within 30 s"
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


def admit(flags, rid, d, pid, regions, window_s):
    """The ONE launcher-side admission (grant_ok_launcher.check: the parser of the live poller's argv, window >= min+300,
    regions survive its parse and cover its claim, --precond-cmd). Returns (ok, line)."""
    import argparse as _ap
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:  # the keeper runs `python3 -I`: isolated mode does not put the script's directory on sys.path
        sys.path.insert(0, here)
    import grant_ok_launcher as gate
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


def heal_grants(flags, grants, rl, log, seen):
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


# ---------------------------------------------------------------- allocate: ONE snapshot, dry runs + grants together
def allocate(flags, keeper_log=None, log=print, dry=False):
    """dry=True: snapshot + plan only (PLAN lines); nothing healed, armed, granted or started."""
    keeper_log = keeper_log or os.path.join(flags, "ws58-calendar-keeper.log")
    if glob.glob(os.path.join(flags, "HOLD_*")):
        log("HOLD present; nothing allocated"); return []
    seen = set()
    allrows = rows(flags)
    rl = rl_status()
    grants = open_grants(flags) if dry else heal_grants(flags, open_grants(flags), rl, log, seen)
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
    busy |= {q for q in QUARTERS if expand({q}) & busy}   # a quarter with any held core/thread is not whole-free
    free = (set(REGIONS) | set(CORES) | set(THREADS)) - busy
    gpu_open = any(GPU in g["holds"] for g in grants)
    if GPU in free and not dry and start_gpu_batch(flags, log):
        free.discard(GPU)  # queued GPU smokes run in the gap before the next GPU grant
    counts = lane_counts(flags, allrows)
    cands = []
    for rid, d in allrows.items():
        st = status(flags, rid, allrows)["state"]
        if st not in ("grantable", "armed"):
            continue  # operator 2026-11-02: the dry run is publish_row's smoke; only PASSed rows are granted
        kind = "grant"
        # ws58 2026-11-01: a row flagged UNDERUSED is never granted again until its owner republishes it (a single-core
        # prep step inside a quarter/host grant idles compute; kvu-vkq3 took the whole host to run llama-tokenize).
        uu = os.path.join(flags, "dryrun", rid, "UNDERUSED.json")
        mf = os.path.join(flags, "ready", rid + ".json")
        if os.path.exists(uu) and os.path.exists(mf) and os.path.getmtime(uu) >= os.path.getmtime(mf):
            continue
        opts, bench = row_shape(d)
        since = (load_json(pass_path(flags, rid)) or {}).get("passed_at")
        window = int(d["window_s"])
        cands.append({"id": rid, "kind": kind, "lane": d["lane"], "rank": row_rank(d), "lane_count": counts[d["lane"]],
                      "gib": int(d.get("gib") or 0), "bench": bench, "options": opts, "shape": shape_of(d), "window_s": window,
                      "since": iso_epoch(since), "ports": list(d.get("ports") or [])})
    dfile = os.path.join(flags, "drain_state.json")
    drain_prev = {k: v for k, v in (load_json(dfile) or {}).items() if k in allrows}
    held_ports = {int(p) for g in grants for p in ((allrows.get(g["id"]) or {}).get("ports") or [])}
    ends = [iso_epoch(g["end"]) for g in grants if g.get("end")]
    assigned, idle, pending = plan(free, cands, mem_available_gib(), gpu_open, grant_ends=[e for e in ends if e], quiet_ok=quiet_ok_now(flags),
                                    held_ports=held_ports, drain_prev=drain_prev)
    if not dry:
        atomic_json(dfile, {plan.last_drain[0]["id"]: plan.last_drain[1]} if plan.last_drain else {})
    for hc, bc in plan.drain_held:
        log(f"DRAIN-HELD {hc['id']} (rank {hc['rank']:g}, {hc.get('shape')}): better-ranked {bc['id']} (rank {bc['rank']:g}) wants its regions; no drain")
    if plan.last_drain:
        dc, T = plan.last_drain
        log(f"DRAIN {dc['id']} ({dc.get('shape')}) until {dt.datetime.fromtimestamp(T, dt.timezone.utc):%Y-%m-%dT%H:%MZ}: new rows only if they end before then")
    log(f"SNAPSHOT free={','.join(compress(free)) or '-'} busy={','.join(f'{r}:{holders.get(r, '?')}' for r in compress(busy)) or '-'} "
        f"cands={len(cands)} assigned={len(assigned)} lanes cpu={counts['cpu']} gpu={counts['gpu']}")
    out = []
    for c, opt in assigned:
        rid, d = c["id"], allrows[c["id"]]
        regions = grant_regions(d, opt)
        if dry:
            log(f"PLAN {c['kind']} {rid} regions={regions} holds={','.join(compress(opt))} lane={c['lane']} rank={c['rank']:g}"); continue
        try:  # one row's failure never aborts the tick (22:33Z: an import error after ROW-ARM left q0 ungranted for 3 ticks)
            a = load_json(armed_path(flags, rid))
            if not (a and alive(a.get("pid"))):
                pid, msg = arm_one(flags, rid, d, regions)
                log(f"ROW-ARM {msg}")
                if not pid:
                    continue
            else:
                pid = a["pid"]
            ok, line = admit(flags, rid, d, pid, regions, d["window_s"])
            if not ok:
                log(f"SKIP {rid}: {line[:200]}"); continue
            gl = write_grant(flags, rid, regions, opt, d["window_s"])
            log(f"GRANT {rid} {gl} ({line[:160]})")
            out.append(("grant", rid, regions))
        except Exception as e:  # noqa: BLE001 - logged, counted, alerted on repeat
            log(f"ERROR {rid}: {type(e).__name__}: {e}")
            seen.add(f"error:{rid}")
    for r, why in idle.items():
        log(f"IDLE-WHY {r}: {why}")
    left = free - expand(set().union(*[o for _, o in assigned])) if assigned else free
    for c in pending:
        if c["kind"] == "grant" and any(o <= left for o in c["options"]) and not (c.get("bench") and gpu_open):
            seen.add(f"idle-violation:{c['id']}"); log(f"IDLE-VIOLATION {c['id']} fits {','.join(compress(free))} but was not placed")
    if not dry:
        underused(flags, holders, log, seen, vram=vram_used_bytes() if GPU in holders else None)
        repeat_alert(flags, seen, log)
    return out


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


# ---------------------------------------------------------------- cli
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--flags", default=FLAGS)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("publish"); s.add_argument("spec"); s.add_argument("--migrate", action="store_true", help="spec is a legacy ready/<id>.json manifest")
    s = sub.add_parser("status"); s.add_argument("id"); s.add_argument("--json", action="store_true")
    sub.add_parser("list")
    s = sub.add_parser("allocate", help="ONE snapshot per tick: heal, assign dry runs + grants together, write grants, log IDLE-WHY/UNDERUSED")
    s.add_argument("--log", help="keeper log the detached dry runs append DRYRUN-RESULT to (default <flags>/ws58-calendar-keeper.log)")
    s.add_argument("--plan", action="store_true", help="snapshot + plan only; change nothing")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "publish":
            spec = load_json(a.spec)
            need(spec, f"{a.spec} is not a JSON object")
            if a.migrate:
                spec = spec_from_legacy(spec, a.flags)
            print(published_line(publish(spec, a.flags, source=os.path.abspath(a.spec)), a.flags))
            return 0
        if a.cmd == "status":
            st = status(a.flags, a.id)
            print(json.dumps(st, indent=1) if a.json else f"{st['state']}\t{st.get('reason', '')}")
            return 0 if st["state"] != "unknown" else 2
        if a.cmd == "list":
            allrows = rows(a.flags)
            for rid in sorted(allrows, key=lambda r: row_rank(allrows[r])):
                st = status(a.flags, rid, allrows)
                print(f"{st['state']:15} {allrows[rid]['lane']:3} rank={allrows[rid].get('priority_rank')} {rid}  {st.get('reason', '')[:100]}")
            return 0
        if a.cmd == "allocate":
            allocate(a.flags, a.log, dry=a.plan)
            return 0
    except Refused as e:
        print(f"REFUSED: {e}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
