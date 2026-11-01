#!/usr/bin/env python3
"""rowflow.py - the simplified inference-row pipeline (ws58, operator ruling 2026-11-01: remove every gate that is
not indispensable).

OWNER CONTRACT (two things): the launcher script and a small spec. `publish_row.py <spec.json>` derives the rest.

    spec (JSON)      required: id, owner, launcher (abs path, runs filler_run15.sh), lane (cpu|gpu),
                               result_path (what the filer reads), decision_rule, estimate_s, handoff_task
                     optional: result_format (jsonl|json|csv|tsv|text-lines|markdown-table|custom:<cmd>; default by
                               extension), regions (default gpu -> mi210_0,184-191; cpu -> any-cpu-quarter),
                               ram_gib (48), priority_rank (100), scratch_root (launcher's job dir), keep (globs),
                               dryrun_timeout_s (900 cpu / 1500 gpu), lineage, lineage_reset, supersedes,
                               snapshot (true forces the snapshot below)

    SNAPSHOT RULE   a launcher, engine or job file under worktrees/ or /workspace (or a /workspace/repos/<x> target) is
                    copied at publish time into <scratch_root>/snapshot/ (git archive HEAD of its directory when the
                    worktree is clean, else a working-tree copy with dirty=true), paths rewritten, files chmod a-w; the
                    row's launcher/engine/result paths point INTO the snapshot. Row field `snapshot` records it.

    published row    compute-flags/ready/<id>.json  schema epyc.row.v3 (derived: engine, min_window_s, window_s,
                     ports, gib, launcher sha256, scratch_root/keep for the reaper)

KEEPER SIDE (deterministic, no LLM): the keeper is the qualifier.
    allocate                  THE allocator (2026-11-01, operator "compute keeps idling because of scheduling races"): ONE
                              snapshot per tick (region-lock, open grants' holds=, live dry runs); dry runs and grants are
                              assigned together from it (starved lane first, then priority_rank, a grantable row before a
                              dry run; a region is never handed twice; any-cpu-quarter is resolved only here); it arms the
                              poller, admits through grant_ok_launcher (the one parser), WRITES the grant, spawns the dry
                              runs. Self-healing every tick: HEAL stale-grant / HEAL conflict (re-assigned) / CONFLICT,
                              IDLE-WHY <region>: <reason>, UNDERUSED (<5 % of a held quarter for 10 min -> owner fix task,
                              never killed), ALERT on the 3rd repeat (ws58-keeper-alerts.jsonl). A multi-quarter row is
                              dry-run on ONE quarter (FILLER_DRYRUN_ONE_QUARTER) unless the spec says dryrun_whole_host.
    dryrun-run <id> --regions THE dry run: the exact launcher, through its engine, under the real region-lock on the real
                              lane, with a real short grants/<id>.grant. PASS only when the first unit of measured output
                              lands in result_path in the filer's format AND the job then exits or stops cleanly on the
                              stop file (rc 0/75). GPU rows must also show VRAM in use. Records
                              compute-flags/dryrun/<id>/PASS.json {launcher_sha256, result_path, units, vram...} or
                              FAIL-<n>.json {reason, launcher.out tail}. A FAIL is the owner's one fix task; it is not
                              retried until the launcher changes (sha). 3 FAILs in a lineage -> parked + escalation note.
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
        "gib": int(spec.get("ram_gib") or 48), "ports": o["ports"], "priority_rank": rank,
        "scratch_root": scratch, "keep": keep, "stop_file": o["stop"], "workdir": o["workdir"],
        "dryrun_timeout_s": int(spec.get("dryrun_timeout_s") or (1500 if lane == "gpu" else 900)),
        "published_at": now_iso(), "published_from": source or "spec",
    }
    if spec.get("admission_class") is not None:
        row["admission_class"] = spec["admission_class"]
    if snap:
        row["snapshot"] = snap
    elif isinstance(spec.get("snapshot"), dict):  # a republish from ready/<id>.json (publish_row.py --repair) keeps its snapshot record
        row["snapshot"] = spec["snapshot"]
    for k in ("lineage", "lineage_reset", "supersedes", "notes", "row", "dryrun_whole_host"):
        if spec.get(k) is not None:
            row[k] = spec[k]
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


def row_shape(d):
    """(options, bench): the alternative region sets (frozensets over q0..q3/gpu-quiet) a row must hold at once, derived
    from the row's regions AND its launcher's region-lock claim (static parse; the engine's own defaults). bench = a
    timing row (keeps off q3 while a GPU grant is open)."""
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
    if cc and not (nofold and cls == "gpu"):
        extra |= quarters_of(cc, fold=True)
    if regs == "any-cpu-quarter":
        bases = [{q} for q in QUARTERS]
    elif regs.startswith("any-of"):
        bases = [{x.strip()} for x in regs[len("any-of"):].split(",") if re.fullmatch(r"q[0-3]", x.strip())]
    else:
        bases = [quarters_of(regs)]
    opts = []
    for b in bases:
        fs = frozenset(b | extra)
        if fs and fs not in opts:
            opts.append(fs)
    return opts, (gq == "exclusive" or o.get("role") == "bench")


def dryrun_shape(d, opts, flags=None):
    """A dry run never holds more than it needs: a row booking several quarters is dry-run on ONE quarter (the engine
    claims the grant's cpus under FILLER_DRYRUN_ONE_QUARTER=1) unless the spec says dryrun_whole_host. Only the INSTALLED
    engine honours that env (a private engine copy, or a wrapper that re-execs its own engine, cannot be constrained), so
    any other engine keeps its whole shape and waits until all of it is free."""
    eng = d.get("engine", {}).get("path") if isinstance(d.get("engine"), dict) else None
    installed = os.path.join(flags or FLAGS, "bin", "rowflow", CANONICAL_ENGINE)
    if d.get("dryrun_whole_host") or (eng and os.path.realpath(eng) != os.path.realpath(installed)):
        return opts, False
    out = []
    for o in opts:
        qs = sorted(q for q in o if q in QUARTERS)
        if len(qs) <= 1:
            out.append(o)
            continue
        keep = {GPU} if GPU in o else set()
        for q in (["q3"] if GPU in o else qs):
            fs = frozenset(keep | {q})
            if fs not in out:
                out.append(fs)
    return out, any(len([q for q in o if q in QUARTERS]) > 1 for o in opts)


def grant_regions(d, option, one_quarter):
    """The regions= string of a grant for `option`: the row's own regions when concrete, else the chosen quarter."""
    regs = str(d.get("regions") or "")
    if "mi210" in regs:
        return regs
    if regs == "any-cpu-quarter" or regs.startswith("any-of") or one_quarter:
        qs = sorted(q for q in option if q in QUARTERS)
        return cpu_list(qs[0]) if qs else regs
    return regs


def plan(free, cands, ram_gib, gpu_grant_open=False):
    """PURE. One snapshot -> assignments. free: free regions; cands: [{id, kind: grant|dryrun, lane, rank, lane_count, gib,
    bench, options: [frozenset]}]; ram_gib: MemAvailable now. Order: starved lane (fewest live rows) first, then rank,
    then a grantable row before a dry run. Fixpoint: as long as any pending candidate fits the remaining free regions and
    RAM it is placed, so no region stays idle while a fitting row waits. Never hands a region twice.
    Returns (assigned [(cand, option)], idle {region: reason}, pending)."""
    pending = sorted(cands, key=lambda c: (c["lane_count"], float(c["rank"]), 0 if c["kind"] == "grant" else 1, c["id"]))
    free, ram, out = set(free), float(ram_gib), []
    while pending:
        placed = None
        for c in pending:
            opts = [o for o in c["options"] if o and o <= free]
            if c.get("bench") and gpu_grant_open:
                opts = [o for o in opts if "q3" not in o]
            if not opts or ram - float(c.get("gib") or 0) < RAM_MARGIN_GIB:
                continue
            # prefer the smallest option, then the one other pending rows want least (keeps their alternatives open)
            demand = {r: sum(1 for x in pending if x is not c for o2 in x["options"] if r in o2) for r in free}
            o = min(opts, key=lambda o: (len(o), sum(demand[r] for r in o), sorted(o)))
            placed = (c, o)
            break
        if not placed:
            break
        c, o = placed
        out.append(placed); free -= o; ram -= float(c.get("gib") or 0); pending.remove(c)
    idle = {}
    for r in sorted(free):
        want = [c for c in pending if any(r in o for o in c["options"])]
        if not want:
            idle[r] = "no runnable row needs it (every grantable/dry-runnable row is placed, running, failed or parked)"
            continue
        c = want[0]; why = []
        for o in c["options"]:
            if r in o:
                miss = o - free
                if miss:
                    why.append(f"needs {','.join(sorted(o))}: {','.join(sorted(miss))} busy")
                elif c.get("bench") and gpu_grant_open and "q3" in o:
                    why.append("timing row keeps off q3 while a GPU grant is open")
                elif ram - float(c.get("gib") or 0) < RAM_MARGIN_GIB:
                    why.append(f"RAM: {c.get('gib')} GiB would leave {ram - float(c.get('gib') or 0):.0f} GiB < {RAM_MARGIN_GIB} margin")
        idle[r] = f"{c['kind']} {c['id']} " + ("; ".join(why) or "blocked")
    return out, idle, pending


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


def dryrun_run(flags, rid, regions, one_quarter=False):
    """The dry run on the regions the allocator assigned. Returns (verdict, message). verdict in PASS | FAIL | WAIT."""
    allrows = rows(flags)
    d = allrows.get(rid)
    need(d, "no v3 row")
    st = status(flags, rid, allrows)["state"]
    if st not in ("needs-dryrun", "stale"):
        return "WAIT", f"state {st}; nothing to do"
    dd = dry_dir(flags, rid)
    os.makedirs(os.path.join(dd, "state"), exist_ok=True)
    need(regions, "dryrun-run needs --regions (the allocator assigns them from its snapshot)")
    G = os.path.join(flags, "grants")
    grant = os.path.join(G, rid + ".grant")
    if os.path.exists(grant):
        return "WAIT", "grant already open"
    holds = quarters_of(regions) | ({GPU} if "mi210" in regions else set())
    rl = rl_status()
    taken = [r for r in holds if rl.get(r, ("free",))[0] != "free"] + [g["id"] for g in open_grants(flags) if g["holds"] & holds]
    if taken:
        return "WAIT", f"regions {regions} taken since the snapshot: {taken}"
    lp = d["launcher"]["path"]
    lsha = sha256(lp)
    timeout = int(d.get("dryrun_timeout_s") or 900)
    window = max(int(d["min_window_s"]) + 300, timeout + STOP_GRACE_S + 300)
    start = dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0) - dt.timedelta(minutes=1)
    end = start + dt.timedelta(seconds=window)
    for stale in ("stop", "ended", "complete"):
        try:
            os.remove(os.path.join(dd, stale))
        except OSError:
            pass
    units0 = count_units(d["result_path"], d["result_format"], d.get("workdir"))
    env = dict(os.environ, FILLER_DRYRUN="1", FILLER_DRYRUN_DIR=dd, FILLER_STATE_DIR=os.path.join(dd, "state"),
               FILLER_FLAGS_DIR=flags, FILLER_GRANTS_DIR=G,
               FILLER_POLL="5", FILLER_OWNER=str(d["owner"]), FILLER_EST_WALL_S=str(d["estimate_s"]),
               FILLER_DRYRUN_ONE_QUARTER="1" if one_quarter else "0")
    with open(grant, "w") as f:
        f.write(dryrun_grant_text(rid, d.get("admission_class"), regions, holds, start, end))
    out = open(os.path.join(dd, "launcher.out"), "a")
    out.write(f"\n==== dry run {now_iso()} regions={regions} launcher_sha={lsha} units_before={units0}\n"); out.flush()
    p = subprocess.Popen(["bash", lp], cwd=flags, env=env, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
    atomic_json(running_path(flags, rid), {"pid": p.pid, "started": now_iso(), "regions": regions, "launcher_sha256": lsha, "grant": grant})
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
    cpu0 = cpu_sample()
    hold_cpus = [c for q in holds if q in QUARTERS for lo in [int(q[1]) * 24] for c in list(range(lo, lo + 24)) + list(range(lo + 96, lo + 120))]
    try:
        while True:
            time.sleep(5)
            if gpu:
                v = vram_used_bytes()
                if v is not None:
                    vram_max = max(vram_max or 0, v)
            # a dry run must never wait on a lock: a region-lock acquire for regions outside what this dry run holds, or one
            # not satisfied within 60 s, is the row's defect (whole-host claim on a one-quarter dry run)
            waits = lock_waits(tail(lout, 10**6)[out_lines0:], holds)
            if waits and (waits[0] - holds or time.time() - t0 > 60):
                verdict, reason = "FAIL", (f"job waits on region-lock for {','.join(sorted(waits[0]))} while the dry run holds "
                                           f"{','.join(sorted(holds))}: whole-host claim; cannot dry-run on one quarter (constrain "
                                           "--claim-cpus / the job's own claim, or set dryrun_whole_host: true in the spec)")
                break
            if first_unit_at is None and hold_cpus and not gpu and time.time() - t0 > 300:
                pct = busy_pct(cpu0, cpu_sample(), hold_cpus)
                if pct < UNDERUSED_PCT:
                    verdict, reason = "FAIL", (f"single-threaded preflight: job used {pct:.1f}% of its {len(hold_cpus)} claimed cpus for "
                                               f"{int(time.time() - t0)}s with no unit (a quarter row must use the quarter: shrink its regions or fix the launcher)")
                    break
            units = count_units(d["result_path"], d["result_format"], d.get("workdir"))
            new_units = units - units0
            if new_units > 0 and first_unit_at is None:
                first_unit_at = now_iso()
                out.write(f"==== first unit at {first_unit_at}: {new_units} new unit(s) in {d['result_path']}\n"); out.flush()
                if not os.path.exists(ended):
                    open(os.path.join(dd, "stop"), "w").close()
                    stop_requested = time.time()
            if os.path.exists(ended) or p.poll() is not None:
                rc_line = (head1(ended) or "rc=? (no ended record)")
                m = re.match(r"rc=(\d+)", rc_line)
                rc = int(m.group(1)) if m else -1
                units = count_units(d["result_path"], d["result_format"], d.get("workdir")) - units0
                if "reason=disk-floor" in rc_line or "reason=hard-end" in rc_line and units <= 0 and time.time() - t0 < 60:
                    verdict, reason = "WAIT", f"host condition, not the row: {rc_line[:100]} (free disk under the 150 GiB floor); retried later, no FAIL recorded"
                    break
                if units <= 0:
                    verdict, reason = "FAIL", f"job ended ({rc_line[:120]}) before writing a unit to {d['result_path']} ({d['result_format']})"
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
                    verdict, reason = "PASS", f"{count_units(d['result_path'], d['result_format'], d.get('workdir')) - units0} unit(s); {warning}"
                break
            if time.time() - t0 > timeout:
                started = any("START regions=" in l for l in tail(os.path.join(dd, "launcher.out"), 400))
                verdict, reason = "FAIL", f"no unit in {d['result_path']} ({d['result_format']}) within dryrun_timeout_s={timeout}" + \
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
        orphans = row_orphans(rid)
        if orphans:  # a sudo/chroot/setsid wrapper detached them from the launcher's group; reported, never killed by pattern
            warning = (warning + "; " if warning else "") + f"ORPHANS {orphans}: processes still naming this row after the dry run ended (a wrapper detached them; the owner stops them by pid)"
            out.write(f"==== {warning}\n")
        try:
            os.remove(grant)
        except OSError:
            pass
        try:
            os.remove(running_path(flags, rid))
        except OSError:
            pass
        out.write(f"==== dry run {verdict}: {reason} ({now_iso()})\n"); out.close()
    cur_sha = sha256(lp) if os.path.isfile(lp) else None
    if verdict == "PASS" and cur_sha != lsha:
        verdict, reason = "FAIL", "launcher changed while the dry run was running"
    rec = {"regions": regions, "units": count_units(d["result_path"], d["result_format"], d.get("workdir")) - units0, "result_path": d["result_path"],
           "result_format": d["result_format"], "first_unit_at": first_unit_at, "vram_used_max_bytes": vram_max,
           "engine_sha256": sha256(d["engine"]["path"]) if os.path.isfile(d["engine"]["path"]) else None,
           "ended": head1(ended) or None, "warning": warning, "dryrun_log": os.path.join(dd, "launcher.out"), "elapsed_s": int(time.time() - t0)}
    if verdict == "WAIT":
        return verdict, reason
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
def arm_one(flags, rid, d):
    """Start the row's poller (the exact launcher through its engine, polling grants/<id>.grant). Regions are NOT
    resolved here: the grant the allocator writes later carries them."""
    dd = dry_dir(flags, rid)
    os.makedirs(os.path.join(dd, "state"), exist_ok=True)
    log = os.path.join(dd, "poller.out")
    before = sum(1 for l in tail(log, 100000) if "launcher up pid=" in l)
    env = dict(os.environ, FILLER_OWNER=str(d["owner"]), FILLER_EST_WALL_S=str(d["estimate_s"]),
               FILLER_STATE_DIR=os.path.join(dd, "state"), FILLER_FLAGS_DIR=flags, FILLER_GRANTS_DIR=os.path.join(flags, "grants"))
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
    import grant_ok_launcher as gate
    cls = "gpu" if "mi210" in regions else ("whole-host" if regions == "0-95" else "block-correctness")
    a = _ap.Namespace(row=rid, pid=int(pid), window_s=int(window_s), regions=regions, reserve=None, derived_class=cls, fillers="/dev/null", proc="/proc")
    try:
        return True, gate.check(a)
    except gate.Refuse as r:
        return False, f"refuse rc={r.code}: {r}"
    except (OSError, UnicodeDecodeError) as e:
        return False, f"refuse: launcher check could not read its inputs: {e}"


def write_grant(flags, rid, regions, holds, window_s):
    start = dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0) - dt.timedelta(minutes=1)
    end = start + dt.timedelta(seconds=int(window_s))
    line = f"regions={regions} start={start:%Y-%m-%dT%H:%MZ} end={end:%Y-%m-%dT%H:%MZ} holds={','.join(sorted(holds))}\n"
    p = os.path.join(flags, "grants", rid + ".grant")
    with open(p + ".tmp", "w") as f:
        f.write(line)
    os.replace(p + ".tmp", p)
    return line.strip()


def spawn_dryrun(flags, rid, regions, one_quarter, keeper_log):
    dd = dry_dir(flags, rid)
    os.makedirs(dd, exist_ok=True)
    q = shlex.quote
    cmd = (f"r=$(python3 -I {q(os.path.abspath(__file__))} --flags {q(flags)} dryrun-run {q(rid)} --regions {q(regions)}"
           f"{' --one-quarter' if one_quarter else ''} 2>>{q(os.path.join(dd, 'keeper.err'))}); "
           f"echo \"$(date -u +%FT%TZ) DRYRUN-RESULT $r\" >> {q(keeper_log)}")
    subprocess.Popen(["bash", "-c", cmd], cwd=flags, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


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
        foreign = [r for r in g["holds"] if r in rl and rl[r][0] != "free" and rl[r][1] not in ("", f"filler-{rid}")]
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
    busy = {r for r, (s, _) in rl.items() if s != "free"}
    holders = {r: t[len("filler-"):] for r, (s, t) in rl.items() if s != "free" and t.startswith("filler-")}
    for g in grants:
        busy |= g["holds"]
        for r in g["holds"]:
            holders.setdefault(r, g["id"])
    free = set(REGIONS) - busy
    gpu_open = any(GPU in g["holds"] for g in grants)
    counts = lane_counts(flags, allrows)
    cands, shapes = [], {}
    for rid, d in allrows.items():
        st = status(flags, rid, allrows)["state"]
        if st in ("grantable", "armed"):
            kind = "grant"
        elif st in ("needs-dryrun", "stale"):
            kind = "dryrun"
        else:
            continue
        opts, bench = row_shape(d)
        one_q = False
        if kind == "dryrun":
            opts, one_q = dryrun_shape(d, opts, flags)
        shapes[rid] = (opts, one_q)
        cands.append({"id": rid, "kind": kind, "lane": d["lane"], "rank": float(d.get("priority_rank") or 100), "lane_count": counts[d["lane"]],
                      "gib": int(d.get("gib") or 0), "bench": bench, "options": opts})
    assigned, idle, pending = plan(free, cands, mem_available_gib(), gpu_open)
    log(f"SNAPSHOT free={','.join(sorted(free)) or '-'} busy={','.join(f'{r}:{holders.get(r, '?')}' for r in sorted(busy)) or '-'} "
        f"cands={len(cands)} assigned={len(assigned)} lanes cpu={counts['cpu']} gpu={counts['gpu']}")
    out = []
    for c, opt in assigned:
        rid, d = c["id"], allrows[c["id"]]
        regions = grant_regions(d, opt, shapes[rid][1])
        if dry:
            log(f"PLAN {c['kind']} {rid} regions={regions} holds={','.join(sorted(opt))} lane={c['lane']} rank={c['rank']:g}"); continue
        if c["kind"] == "dryrun":
            spawn_dryrun(flags, rid, regions, shapes[rid][1], keeper_log)
            log(f"DRYRUN-START {rid} regions={regions} holds={','.join(sorted(opt))}{' one-quarter' if shapes[rid][1] else ''}")
            out.append(("dryrun", rid, regions)); continue
        a = load_json(armed_path(flags, rid))
        if not (a and alive(a.get("pid"))):
            pid, msg = arm_one(flags, rid, d)
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
    for r, why in idle.items():
        log(f"IDLE-WHY {r}: {why}")
    left = free - set().union(*[o for _, o in assigned]) if assigned else free
    for c in pending:
        if c["kind"] == "grant" and any(o <= left for o in c["options"]) and not (c.get("bench") and gpu_open):
            seen.add(f"idle-violation:{c['id']}"); log(f"IDLE-VIOLATION {c['id']} fits {','.join(sorted(free))} but was not placed")
    if not dry:
        underused(flags, holders, log, seen, vram=vram_used_bytes() if GPU in holders else None)
        repeat_alert(flags, seen, log)
    return out


# ---------------------------------------------------------------- cli
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--flags", default=FLAGS)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("publish"); s.add_argument("spec"); s.add_argument("--migrate", action="store_true", help="spec is a legacy ready/<id>.json manifest")
    s = sub.add_parser("status"); s.add_argument("id"); s.add_argument("--json", action="store_true")
    sub.add_parser("list")
    s = sub.add_parser("dryrun-run"); s.add_argument("id"); s.add_argument("--regions", required=True); s.add_argument("--one-quarter", action="store_true")
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
            for rid in sorted(allrows, key=lambda r: float(allrows[r].get("priority_rank") or 100)):
                st = status(a.flags, rid, allrows)
                print(f"{st['state']:15} {allrows[rid]['lane']:3} rank={allrows[rid].get('priority_rank')} {rid}  {st.get('reason', '')[:100]}")
            return 0
        if a.cmd == "dryrun-run":
            v, msg = dryrun_run(a.flags, a.id, a.regions, a.one_quarter)
            print(f"{v}\t{a.id}\t{msg}")
            return {"PASS": 0, "WAIT": 1}.get(v, 2)
        if a.cmd == "allocate":
            allocate(a.flags, a.log, dry=a.plan)
            return 0
    except Refused as e:
        print(f"REFUSED: {e}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
