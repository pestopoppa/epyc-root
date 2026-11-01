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
    dryrun-pick               next row needing a dry run whose lane is free (one per lane per tick; starved lane first)
    dryrun-run <id>           THE dry run: the exact launcher, through its engine, under the real region-lock on the real
                              lane, with a real short grants/<id>.grant. PASS only when the first unit of measured output
                              lands in result_path in the filer's format AND the job then exits or stops cleanly on the
                              stop file (rc 0/75). GPU rows must also show VRAM in use. Records
                              compute-flags/dryrun/<id>/PASS.json {launcher_sha256, result_path, units, vram...} or
                              FAIL-<n>.json {reason, launcher.out tail}. A FAIL is the owner's one fix task; it is not
                              retried until the launcher changes (sha). 3 FAILs in a lineage -> parked + escalation note.
    arm-tick                  start the poller of every grantable row and append its queue line (writers grant it)
    status <id> [--grant]     needs-dryrun | dryrun-running | failed | parked | stale | grantable | armed | running | done
                              --grant: exit 0 only when the row may be granted NOW (PASS present, launcher sha unchanged)

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


def publish(spec, flags=FLAGS, source=None, allow_legacy_engine=False):
    for k in ("id", "owner", "launcher", "lane", "result_path", "decision_rule", "estimate_s", "handoff_task"):
        need(k in spec and spec[k] not in (None, ""), f"spec.{k} missing")
    rid = str(spec["id"])
    need(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]+", rid), "bad id")
    need(spec["lane"] in ("cpu", "gpu"), "lane must be cpu or gpu")
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
    if snap:
        row["snapshot"] = snap
    for k in ("lineage", "lineage_reset", "supersedes", "notes", "row"):
        if spec.get(k) is not None:
            row[k] = spec[k]
    atomic_json(ready_path(flags, rid), row)
    return row


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


# ---------------------------------------------------------------- lane state
def rl_free():
    try:
        st = subprocess.run([RL, "status"], capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.TimeoutExpired):
        return set()
    free = set()
    for l in st.splitlines():
        b = l.split()
        if len(b) > 1 and b[1] == "free" and b[0] in ("q0", "q1", "q2", "q3", "gpu-quiet"):
            free.add(b[0])
    return free


def quarters_of(regions):
    qs = set()
    for tok in str(regions).split(","):
        tok = tok.strip()
        if re.fullmatch(r"q[0-3]", tok):
            qs.add(tok)
        elif re.fullmatch(r"\d+(-\d+)?", tok):
            a, b = (tok.split("-") + [tok])[:2]
            a, b = int(a), int(b)
            for q in range(4):
                lo = q * 24
                if a <= lo + 23 and b >= lo and a < 96:
                    qs.add(f"q{q}")
    return qs


def open_grants(flags):
    out = []
    for g in glob.glob(os.path.join(flags, "grants", "*.grant")):
        try:
            first = open(g).readline()
        except OSError:
            continue
        m = re.search(r"regions=(\S+)", first)
        out.append((os.path.basename(g)[:-6], m.group(1) if m else ""))
    return out


def lane_free(flags, regions, free=None, grants=None):
    free = rl_free() if free is None else free
    grants = open_grants(flags) if grants is None else grants
    if glob.glob(os.path.join(flags, "HOLD_*")):
        return False
    if "mi210_0" in regions:
        if "gpu-quiet" not in free:
            return False
        return not any("mi210" in r for _, r in grants)
    need_q = quarters_of(regions)
    if not need_q or not need_q <= free:
        return False
    for _, r in grants:
        if r == "0-95" or quarters_of(r) & need_q:
            return False
    return True


def resolve_regions(flags, regions, free=None, grants=None):
    """any-cpu-quarter / any-of qA,qB -> a concrete free quarter's cpu list; else regions unchanged if free."""
    free = rl_free() if free is None else free
    grants = open_grants(flags) if grants is None else grants
    if regions == "any-cpu-quarter" or regions.startswith("any-of"):
        cands = ["q0", "q1", "q2", "q3"] if regions == "any-cpu-quarter" else [x.strip() for x in regions[len("any-of"):].split(",") if x.strip()]
        for q in cands:
            lo = int(q[1]) * 24
            r = f"{lo}-{lo + 23}"
            if lane_free(flags, r, free, grants):
                return r
        return None
    return regions if lane_free(flags, regions, free, grants) else None


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
    if last_fail and last_fail.get("launcher_sha256") == cur and last_fail.get("row_sha256", row_sha(flags, rid)) == row_sha(flags, rid) \
            and last_fail.get("rowflow_sha256", sha256(__file__)) == sha256(__file__):  # a spec edit or a rowflow fix retries the row
        out.update(state="failed", reason=str(last_fail.get("reason"))[:300], fail_file=fail_paths(flags, rid)[-1],
                   fix_task=last_fail.get("fix_task")); return out
    if p:
        out.update(state="stale", reason="launcher changed since the passing dry run; a new dry run is needed"); return out
    out.update(state="needs-dryrun", reason="no dry run for the current launcher"); return out


def grant_check(flags, rid):
    """One line + rc for grant_ok: 0 grantable now, 2 refuse."""
    st = status(flags, rid)
    if st["state"] in ("grantable", "armed"):
        return 0, f"ok: dry-run PASS, launcher sha {st['launcher_sha256'][:12]} unchanged"
    return 2, f"refuse: row state {st['state']}: {st.get('reason', '')}"


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


def dryrun_run(flags, rid, regions=None):
    """The dry run. Returns (verdict, message). verdict in PASS | FAIL | WAIT."""
    allrows = rows(flags)
    d = allrows.get(rid)
    need(d, "no v3 row")
    st = status(flags, rid, allrows)["state"]
    if st not in ("needs-dryrun", "stale"):
        return "WAIT", f"state {st}; nothing to do"
    dd = dry_dir(flags, rid)
    os.makedirs(os.path.join(dd, "state"), exist_ok=True)
    regions = regions or resolve_regions(flags, d["regions"])
    if not regions:
        return "WAIT", f"regions {d['regions']} not free"
    G = os.path.join(flags, "grants")
    grant = os.path.join(G, rid + ".grant")
    if os.path.exists(grant):
        return "WAIT", "grant already open"
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
               FILLER_POLL="5", WS58_REGIONS=regions, FILLER_OWNER=str(d["owner"]), FILLER_EST_WALL_S=str(d["estimate_s"]))
    with open(grant, "w") as f:
        f.write(f"regions={regions} start={start:%Y-%m-%dT%H:%MZ} end={end:%Y-%m-%dT%H:%MZ}\n")
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
    try:
        while True:
            time.sleep(5)
            if gpu:
                v = vram_used_bytes()
                if v is not None:
                    vram_max = max(vram_max or 0, v)
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


def dryrun_pick(flags):
    """Rows to dry-run this tick: at most one per lane, by (starved lane, priority_rank). Prints `id<TAB>regions`."""
    if glob.glob(os.path.join(flags, "HOLD_*")):
        return []
    allrows = rows(flags)
    free, grants = rl_free(), open_grants(flags)
    counts = lane_counts(flags, allrows)
    busy_lane = set()
    for rid in allrows:
        r = load_json(running_path(flags, rid))
        if r and alive(r.get("pid")):
            busy_lane.add(allrows[rid]["lane"])
    cands = []
    for rid, d in allrows.items():
        st = status(flags, rid, allrows)
        if st["state"] in ("needs-dryrun", "stale") and d["lane"] not in busy_lane:
            cands.append((counts[d["lane"]], float(d.get("priority_rank") or 100), rid))
    picked, lanes = [], set()
    for _, _, rid in sorted(cands):
        d = allrows[rid]
        if d["lane"] in lanes:
            continue
        regs = resolve_regions(flags, d["regions"], free, grants)
        if not regs:
            continue
        picked.append((rid, regs)); lanes.add(d["lane"])
        # the picked regions are taken for this tick
        grants = grants + [(rid, regs)]
    return picked


# ---------------------------------------------------------------- arm
def newest_quarter_queue(flags):
    day = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=5, minutes=52)).strftime("%Y%m%d")
    return os.path.join(flags, f"ws58-quarters-{day}.queue")


def arm_one(flags, rid, d, free, grants):
    regions = resolve_regions(flags, d["regions"], free, grants) if "mi210_0" not in d["regions"] else d["regions"]
    if not regions:
        return None, f"wait: regions {d['regions']} not free for arming"
    dd = dry_dir(flags, rid)
    os.makedirs(os.path.join(dd, "state"), exist_ok=True)
    log = os.path.join(dd, "poller.out")
    before = sum(1 for l in tail(log, 100000) if "launcher up pid=" in l)
    env = dict(os.environ, WS58_REGIONS=regions, FILLER_OWNER=str(d["owner"]), FILLER_EST_WALL_S=str(d["estimate_s"]),
               FILLER_STATE_DIR=os.path.join(dd, "state"), FILLER_FLAGS_DIR=flags, FILLER_GRANTS_DIR=os.path.join(flags, "grants"))
    for k in ("FILLER_DRYRUN", "FILLER_DRYRUN_DIR"):
        env.pop(k, None)
    with open(log, "a") as out:
        out.write(f"\n==== arm {now_iso()} regions={regions}\n")
        subprocess.Popen(["bash", d["launcher"]["path"]], cwd=flags, env=env, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
    pid = None
    for _ in range(30):
        time.sleep(1)
        pids = [int(m.group(1)) for l in tail(log, 100000) for m in [re.search(r"launcher up pid=(\d+)", l)] if m]
        if len(pids) > before:
            pid = pids[-1]; break
    if not pid:
        record_fail(flags, rid, d, "poller did not log 'launcher up pid=' within 30 s of arming", {"regions": regions})
        return None, "fail: no launcher pid within 30 s"
    gpu = "mi210_0" in regions
    if gpu:
        q = os.path.join(flags, "ws58-gpu.queue")
        line = f"{rid}|{pid}|{d['window_s']}|{d['min_window_s']}|{d['gib']}|^ *gpu-quiet|{regions}\n"
    else:
        q = newest_quarter_queue(flags)
        if not os.path.exists(q):
            with open(q, "a") as f:
                f.write("# quarter queue (id|launcher_pid|window_s|gib|regions); created by rowflow arm\n")
        line = f"{rid}|{pid}|{d['window_s']}|{d['gib']}|{regions}\n"
    with open(q, "a") as f:
        f.write(line)
    atomic_json(armed_path(flags, rid), {"id": rid, "pid": pid, "regions": regions, "queue": os.path.basename(q), "at": now_iso(),
                                         "launcher_sha256": sha256(d["launcher"]["path"])})
    return pid, f"ARMED {rid} pid={pid} queue={os.path.basename(q)} regions={regions}"


def arm_tick(flags):
    msgs = []
    if glob.glob(os.path.join(flags, "HOLD_*")):
        return ["hold present; not arming"]
    allrows = rows(flags)
    free, grants = rl_free(), open_grants(flags)
    for rid, d in sorted(allrows.items(), key=lambda kv: float(kv[1].get("priority_rank") or 100)):
        if status(flags, rid, allrows)["state"] != "grantable":
            continue
        pid, msg = arm_one(flags, rid, d, free, grants)
        msgs.append(msg)
        if pid and "mi210_0" not in d["regions"]:
            grants = grants + [(rid, (load_json(armed_path(flags, rid)) or {}).get("regions", ""))]
    return msgs


# ---------------------------------------------------------------- adopt legacy armed rows (one-time bridge, 2026-11-01)
def adopt_armed(flags=FLAGS):
    """Legacy rows that were ARMED under the old flow (live poller in a queue, no .complete) keep their place: a v3 row
    is written from ready/armed/<id>.json (or the poller's argv), PASS.json is marked adopted (the old-flow receipt was
    its qualification) and ARMED.json names the live poller. grant_ok v4 then admits them exactly as before; their
    old engine keeps its own grant-time checks. Nothing is started or stopped. Idempotent."""
    out = []
    queues = [os.path.join(flags, "ws58-gpu.queue")] + sorted(glob.glob(os.path.join(flags, "ws58-quarters-*.queue")))
    done_lists = set()
    for dl in glob.glob(os.path.join(flags, "ws58-quarters-*.queue.done")) + [os.path.join(flags, "ws58-gpu.queue.held")]:
        try:
            done_lists |= set(open(dl).read().split())
        except OSError:
            pass
    existing = rows(flags)
    for q in queues:
        try:
            lines = open(q).read().splitlines()
        except OSError:
            continue
        gpu = q.endswith("ws58-gpu.queue")
        for line in lines:
            f = line.split("|")
            if len(f) < 5 or f[0].startswith("#"):
                continue
            rid, pid = f[0], f[1]
            regions = f[6] if gpu and len(f) > 6 else f[4]
            if rid in done_lists or os.path.exists(os.path.join(flags, "grants", rid + ".complete")) or not alive(pid):
                continue
            if rid in existing and os.path.exists(pass_path(flags, rid)):
                continue
            m = None
            for d in ("ready/armed", "ready", "ready/legacy-20261101"):
                m = load_json(os.path.join(flags, d, rid + ".json"))
                if m:
                    break
            try:
                argv = open(f"/proc/{int(pid)}/cmdline", "rb").read().split(b"\0")
            except (OSError, ValueError):
                argv = []
            argv = [a.decode("utf8", "replace") for a in argv]
            eng = next((a for a in argv if ENGINE_RE.search(a)), None)
            try:
                # the poller's argv is the truth for an armed legacy row: no launcher parsing, no publish() rules
                need(eng and os.path.isfile(eng), "no filler_run engine in the poller argv")
                def opt(flag, default=None):
                    return argv[argv.index(flag) + 1] if flag in argv and argv.index(flag) + 1 < len(argv) else default
                m = m or {}
                L = m.get("launcher")
                lp = L.get("path") if isinstance(L, dict) else (L if isinstance(L, str) else None)
                lp = lp if isinstance(lp, str) and os.path.isfile(lp) else eng
                minwin = int(opt("--min-window", m.get("min_window_s") or 0) or 0)
                cls = opt("--class", "")
                ports = [int(x) for x in str(opt("--port", "")).split(",") if x.isdigit()]
                lane = "gpu" if "mi210" in regions else "cpu"
                scratch = m.get("scratch_root") if isinstance(m.get("scratch_root"), str) else None
                if not (scratch and lp.startswith(os.path.normpath(scratch) + "/")):
                    scratch = TMP + lp[len(TMP):].split("/")[0] if lp.startswith(TMP) else os.path.dirname(lp)
                kp = m.get("keep")
                if isinstance(kp, str):
                    kp = [x.strip() for x in kp.split(",") if x.strip()]
                rp = m.get("result_path") if isinstance(m.get("result_path"), str) else os.path.join(scratch, "ADOPTED-LEGACY-no-result_path")
                row = {"schema": SCHEMA, "id": rid, "owner": str(m.get("owner") or "unknown-legacy"), "lane": lane, "regions": regions,
                       "launcher": {"path": lp, "sha256": sha256(lp)}, "engine": {"path": eng, "sha256": sha256(eng)},
                       "result_path": rp, "result_format": guess_format(rp), "decision_rule": m.get("decision_rule") or "ADOPTED legacy armed row (see FILLERS.md / its manifest)",
                       "handoff_task": m.get("row") or m.get("handoff") or "FILLERS:" + rid, "estimate_s": int(f[2]), "min_window_s": minwin,
                       "window_s": int(f[2]), "gib": int(f[4] if gpu else f[3]), "ports": ports, "priority_rank": float(m.get("priority_rank") or 100),
                       "scratch_root": os.path.normpath(scratch), "keep": kp or DEFAULT_KEEP, "workdir": opt("--workdir", "/workspace"),
                       "stop_file": opt("--stop", ""), "dryrun_timeout_s": 900, "published_at": now_iso(), "published_from": "adopt-armed",
                       "adopted_legacy": {"engine": os.path.basename(eng), "class": cls, "manifest_had": sorted(m.keys())[:12]}}
                atomic_json(ready_path(flags, rid), row)
                os.makedirs(dry_dir(flags, rid), exist_ok=True)
                atomic_json(pass_path(flags, rid), {"id": rid, "passed_at": now_iso(), "launcher_sha256": row["launcher"]["sha256"], "adopted": True,
                                                    "note": "legacy armed row adopted 2026-11-01: qualified under the retired flow (old receipt); not re-dry-run",
                                                    "units": None, "result_path": rp, "regions": regions})
                atomic_json(armed_path(flags, rid), {"id": rid, "pid": int(pid), "regions": regions, "queue": os.path.basename(q), "at": now_iso(),
                                                     "launcher_sha256": row["launcher"]["sha256"], "adopted": True})
                existing[rid] = row
                out.append(f"ADOPTED {rid} pid={pid} queue={os.path.basename(q)} regions={regions} engine={os.path.basename(eng)}")
            except Refused as e:
                out.append(f"REFUSED {rid}: {e}")
    return out


# ---------------------------------------------------------------- cli
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--flags", default=FLAGS)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("publish"); s.add_argument("spec"); s.add_argument("--migrate", action="store_true", help="spec is a legacy ready/<id>.json manifest")
    s = sub.add_parser("status"); s.add_argument("id"); s.add_argument("--grant", action="store_true"); s.add_argument("--json", action="store_true")
    sub.add_parser("list")
    sub.add_parser("dryrun-pick")
    s = sub.add_parser("dryrun-run"); s.add_argument("id"); s.add_argument("--regions")
    sub.add_parser("arm-tick")
    sub.add_parser("adopt-armed")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "publish":
            spec = load_json(a.spec)
            need(spec, f"{a.spec} is not a JSON object")
            if a.migrate:
                spec = spec_from_legacy(spec, a.flags)
            row = publish(spec, a.flags, source=os.path.abspath(a.spec))
            print(f"PUBLISHED {row['id']} lane={row['lane']} regions={row['regions']} window_s={row['window_s']} min_window_s={row['min_window_s']} "
                  f"gib={row['gib']} ports={row['ports']} result={row['result_path']} ({row['result_format']}) -> {ready_path(a.flags, row['id'])}")
            return 0
        if a.cmd == "status":
            if a.grant:
                rc, msg = grant_check(a.flags, a.id); print(msg); return rc
            st = status(a.flags, a.id)
            print(json.dumps(st, indent=1) if a.json else f"{st['state']}\t{st.get('reason', '')}")
            return 0 if st["state"] != "unknown" else 2
        if a.cmd == "list":
            allrows = rows(a.flags)
            for rid in sorted(allrows, key=lambda r: float(allrows[r].get("priority_rank") or 100)):
                st = status(a.flags, rid, allrows)
                print(f"{st['state']:15} {allrows[rid]['lane']:3} rank={allrows[rid].get('priority_rank')} {rid}  {st.get('reason', '')[:100]}")
            return 0
        if a.cmd == "dryrun-pick":
            for rid, regs in dryrun_pick(a.flags):
                print(f"{rid}\t{regs}")
            return 0
        if a.cmd == "dryrun-run":
            v, msg = dryrun_run(a.flags, a.id, a.regions)
            print(f"{v}\t{a.id}\t{msg}")
            return {"PASS": 0, "WAIT": 1}.get(v, 2)
        if a.cmd == "arm-tick":
            for m in arm_tick(a.flags):
                print(m)
            return 0
        if a.cmd == "adopt-armed":
            for m in adopt_armed(a.flags):
                print(m)
            return 0
    except Refused as e:
        print(f"REFUSED: {e}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
