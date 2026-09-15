#!/usr/bin/env python3
"""AutoKernel disk sweep: classify leftover worktrees and tmp dirs, remove only reviewed rows.

DEFAULT IS DRY-RUN. The scan is read-only: it runs `git status`/`rev-list` with
GIT_OPTIONAL_LOCKS=0 (no index refresh writes), walks candidate trees with lstat only, and reads
/proc. It writes exactly two files: the manifest JSON and its `.sha256`, into --out-dir.

    # 1. dry-run (anyone, any time)
    python3 scripts/system/autokernel_disk_sweep.py --out-dir /mnt/raid0/llm/tmp/sub-aksweep

    # 2. apply: ONLY after the operator has reviewed that manifest and confirms, at a boundary the
    #    AutoKernel owner chooses. Needs a COMPLETE process probe, i.e. host root, so run the
    #    reviewed dry-run on the host as root too (apply re-uses the manifest's paths).
    sudo python3 scripts/system/autokernel_disk_sweep.py --apply \
        --manifest <manifest.json> --manifest-sha <sha256 printed by step 1>

Verdicts (first match wins, in this precedence):
  KEEP-active-session  under a live AutoKernel session footprint (codex process tree cwd/fds,
                       bus-heartbeat task lane, claims), branch/name carries the active task id,
                       or ANY file/dir changed within --recency-hours (default 24): an agent can
                       hold a path with no process sitting in it.
  KEEP-live            some other process has cwd/exe/fd/mmap/argv inside the candidate.
  KEEP-unverifiable    cannot be proven safe (orphaned worktree registration, nested git repo in a
                       plain dir, symlink, locked worktree, git errors, unknown owning repo).
  KEEP-dirty           worktree has modified or untracked non-ignored files.
  KEEP-unpushed        worktree HEAD, or a local branch named for it, is not contained in any
                       remote-tracking ref.
  KEEP-referenced      named by loop code/config/state (live dependency), a registered roster lane
                       under worktrees/mains/<roster-id>, or cited by an active handoff / retention
                       note with no evidence files to archive.
  ARCHIVE-evidence     holds evidence files (VERDICT*.json, *receipt*, *seal*, attestations,
                       ratifications; for worktrees only untracked-ignored ones). Never removed by
                       --apply: archive the evidence first, then re-scan.
  REMOVE               every check (a)-(e) passed.

Hard rules encoded here (origin: the 2026-08-12 five-lane loss and INC-20260731):
  * never `git worktree prune`, never `git gc`, never `worktree remove --force`;
  * a registered worktree is removed only by `git -C <owning repo> worktree remove <path>`;
  * --apply refuses unless --manifest-sha matches the manifest bytes, removes only REMOVE rows,
    and re-runs every check (active-session and recency included) immediately before each row;
  * --apply additionally requires the OPERATOR's interactive confirmation (TTY + typed sha
    prefix); agents never run --apply;
  * the process probe is three-state (COMPLETE / PARTIAL / UNKNOWN). --apply refuses the WHOLE
    run, not just the row, unless the probe is COMPLETE: unknown means busy.
  * this script never signals or kills a process.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

SCHEMA = "autokernel-disk-sweep-manifest/v1"
LLM = "/mnt/raid0/llm"

VERDICT_ORDER = [
    "KEEP-active-session",
    "KEEP-live",
    "KEEP-unverifiable",
    "KEEP-dirty",
    "KEEP-unpushed",
    "KEEP-referenced",
    "ARCHIVE-evidence",
    "REMOVE",
]

# Evidence = sealed/receipted measurement records. Deliberately narrow: a bare "seal"/"receipt"
# substring matched icon packages in node_modules, __pycache__ of receipt modules, and SEAL-paper
# benchmark copies in the first real dry-run (2026-09-15), which is noise, not evidence.
EVIDENCE_RE = re.compile(
    r"(?i)(^verdict[^/]*\.json$|^SHA256SUMS$|receipt[^/]*\.jsonl?$|(^|[._-])sealed([._-]|$)|"
    r"attestation[^/]*\.json$|^ratif[^/]*\.json$)"
)
EVIDENCE_SKIP_DIRS = {"node_modules", "__pycache__", ".pytest_cache", ".gitnexus", "CMakeFiles", ".mypy_cache"}
BASENAME_MIN_DISTINCT = 10  # shorter basenames (b3, d1, prof) only match as parent/child pairs
PATH_TOKEN_RE = re.compile(r"[A-Za-z0-9_.+\-/]*[A-Za-z0-9_+\-]")
NAME_TOKEN_RE = re.compile(r"[A-Za-z0-9_.+\-]{4,}")
RETENTION_RE = re.compile(
    r"(?i)(retain|retention|preserve|do not (delete|remove)|don't (delete|remove)|rollback anchor|keep (this|the|it)|kept)"
)

DEFAULT_WORKTREE_GLOBS = [
    f"{LLM}/worktrees/acceptance/*",
    f"{LLM}/worktrees/inf70/*",
    f"{LLM}/worktrees/mains/*",
]
DEFAULT_MAINS_NAME_RE = r"^(ak|aku|akx|autokernel|s3-aku|codex-s3-aku)"
DEFAULT_TMP_GLOBS = [
    f"{LLM}/tmp/aku*",
    f"{LLM}/tmp/autokernel-*",
    f"{LLM}/tmp/glm53-validation-*",
]
DEFAULT_ALLOWED_ROOTS = [f"{LLM}/worktrees", f"{LLM}/tmp"]
# epyc-root is `/workspace` inside the dev container and `/mnt/raid0/llm/epyc-root` on the host.
# Scan and apply must run in the SAME context (apply re-uses the manifest's paths), so pick one.
ROOT_DIR = "/workspace" if os.path.isdir("/workspace/coordination/session-bus") else f"{LLM}/epyc-root"
DEFAULT_PATH_ALIASES = ["/workspace=/mnt/raid0/llm/epyc-root"]  # only meaningful in-container
DEFAULT_BUS_ROOT = f"{ROOT_DIR}/coordination/session-bus"
# repo:ref:pathspec -- git-tracked text that the LOOP depends on (live references)
DEFAULT_LIVE_GIT_SOURCES = [
    f"{LLM}/epyc-inference-research:origin/main:.",
    f"{LLM}/epyc-inference-research:HEAD:.",
    f"{LLM}/epyc-orchestrator:origin/main:.",
    f"{LLM}/epyc-orchestrator:HEAD:.",
]
# repo:ref:pathspec -- citations (handoffs, docs) -> KEEP-referenced or ARCHIVE-evidence
DEFAULT_CITE_GIT_SOURCES = [
    f"{ROOT_DIR}:origin/main:handoffs/active",
    f"{ROOT_DIR}:origin/main:docs",
]
DEFAULT_CITE_FILE_GLOBS = [f"{ROOT_DIR}/handoffs/active/*.md"]
DEFAULT_RETENTION_GIT_SOURCES = [
    f"{ROOT_DIR}:origin/main:progress/2026-08",
    f"{ROOT_DIR}:origin/main:progress/2026-09",
]
# live loop state (non-git): small json/yaml/jsonl only
DEFAULT_STATE_PATHS = [
    f"{LLM}/autokernel/loop-memory",
    f"{LLM}/ak-claims",
    f"{ROOT_DIR}/coordination/session-bus/claims",
    f"{ROOT_DIR}/coordination/push-locks",
    f"{ROOT_DIR}/coordination/session-bus/heartbeats",
]
STATE_FILE_SUFFIXES = (".json", ".jsonl", ".yaml", ".yml", ".lock", ".toml")
STATE_FILE_MAX_BYTES = 8 * 1024 * 1024


# --------------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------------

def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso(ts: float | None) -> str | None:
    if ts is None:
        return None
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat(timespec="seconds")


def parse_aliases(items: Iterable[str]) -> list[tuple[str, str]]:
    out = []
    for item in items:
        src, _, dst = item.partition("=")
        if src and dst:
            out.append((src.rstrip("/"), dst.rstrip("/")))
    return out


def norm_path(p: str, aliases: list[tuple[str, str]]) -> str:
    p = p.split("\x00", 1)[0]
    if p.endswith(" (deleted)"):
        p = p[: -len(" (deleted)")]
    p = os.path.normpath(p) if p.startswith("/") else p
    for src, dst in aliases:
        if p == src or p.startswith(src + "/"):
            return dst + p[len(src):]
    return p


def is_within(child: str, parent: str) -> bool:
    return child == parent or child.startswith(parent.rstrip("/") + "/")


def _drop_privs():  # pragma: no cover - only meaningful under sudo
    uid, gid = os.environ.get("SUDO_UID"), os.environ.get("SUDO_GID")
    if os.geteuid() == 0 and uid and gid:
        os.setgid(int(gid))
        os.setuid(int(uid))


def git(repo_or_tree: str, *args: str, timeout: int = 600) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["GIT_OPTIONAL_LOCKS"] = "0"  # read-mostly: status must not rewrite the index
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    preexec = _drop_privs if (os.geteuid() == 0 and os.environ.get("SUDO_UID")) else None
    return subprocess.run(
        ["git", "-c", "safe.directory=*", "-C", repo_or_tree, *args],
        capture_output=True, text=True, timeout=timeout, env=env, preexec_fn=preexec,
    )


# --------------------------------------------------------------------------------------------
# process probe (three-state)
# --------------------------------------------------------------------------------------------

@dataclass
class Proc:
    pid: int
    ppid: int
    uid: int
    args: str
    cwd: str | None
    paths: set[str] = field(default_factory=set)  # exe, fds, mmaps (not cwd)
    argv_paths: set[str] = field(default_factory=set)
    readable: bool = True


@dataclass
class ProcSnapshot:
    state: str  # COMPLETE | PARTIAL | UNKNOWN
    procs: dict[int, Proc]
    unreadable: list[dict]
    error: str | None = None

    def summary(self) -> dict:
        by_uid: dict[str, int] = {}
        for u in self.unreadable:
            by_uid[str(u["uid"])] = by_uid.get(str(u["uid"]), 0) + 1
        return {
            "state": self.state,
            "processes_seen": len(self.procs),
            "unreadable": len(self.unreadable),
            "unreadable_by_uid": by_uid,
            "error": self.error,
        }


def _read(path: str, binary: bool = False):
    with open(path, "rb" if binary else "r", errors=None if binary else "replace") as fh:
        return fh.read()


def probe_processes(proc_root: str, aliases: list[tuple[str, str]]) -> ProcSnapshot:
    try:
        entries = [e for e in os.listdir(proc_root) if e.isdigit()]
    except OSError as exc:
        return ProcSnapshot("UNKNOWN", {}, [], error=f"cannot list {proc_root}: {exc}")
    procs: dict[int, Proc] = {}
    unreadable: list[dict] = []
    for name in entries:
        pid = int(name)
        base = os.path.join(proc_root, name)
        try:
            st = os.stat(base)
            statline = _read(os.path.join(base, "stat"))
        except FileNotFoundError:
            continue  # vanished
        except OSError:
            unreadable.append({"pid": pid, "uid": -1, "args": "", "why": "stat"})
            continue
        rparen = statline.rfind(")")
        fields = statline[rparen + 2:].split()
        pstate = fields[0] if fields else "?"
        ppid = int(fields[1]) if len(fields) > 1 else 0
        if pstate in ("Z", "X"):
            continue
        if pid == 2 or ppid == 2:
            continue  # kernel thread: no cwd, holds no user paths
        try:
            raw = _read(os.path.join(base, "cmdline"), binary=True)
        except FileNotFoundError:
            continue
        except OSError:
            raw = b""
        argv = [a.decode("utf-8", "replace") for a in raw.split(b"\x00") if a]
        p = Proc(pid=pid, ppid=ppid, uid=st.st_uid, args=" ".join(argv), cwd=None)
        for a in argv:
            for tok in re.split(r"[=:,\s]", a):
                if tok.startswith("/"):
                    p.argv_paths.add(norm_path(tok, aliases))
        try:
            p.cwd = norm_path(os.readlink(os.path.join(base, "cwd")), aliases)
        except FileNotFoundError:
            if not os.path.exists(base):
                continue
            p.readable = False
        except OSError:
            p.readable = False
        if p.readable:
            try:
                p.paths.add(norm_path(os.readlink(os.path.join(base, "exe")), aliases))
            except OSError:
                pass
            try:
                for fd in os.listdir(os.path.join(base, "fd")):
                    try:
                        tgt = os.readlink(os.path.join(base, "fd", fd))
                    except OSError:
                        continue
                    if tgt.startswith("/"):
                        p.paths.add(norm_path(tgt, aliases))
            except FileNotFoundError:
                pass
            except OSError:
                p.readable = False
            try:
                for line in _read(os.path.join(base, "maps")).splitlines():
                    parts = line.split(None, 5)
                    if len(parts) == 6 and parts[5].startswith("/"):
                        p.paths.add(norm_path(parts[5], aliases))
            except OSError:
                pass  # maps absence alone does not make the probe partial (fds + cwd suffice)
        if not p.readable:
            unreadable.append({"pid": pid, "uid": st.st_uid, "args": p.args[:160], "why": "cwd/fd"})
        procs[pid] = p
    if not procs:
        return ProcSnapshot("UNKNOWN", procs, unreadable, error="no processes readable")
    state = "COMPLETE" if not unreadable else "PARTIAL"
    return ProcSnapshot(state, procs, unreadable)


# --------------------------------------------------------------------------------------------
# active session footprint
# --------------------------------------------------------------------------------------------

@dataclass
class ActiveSession:
    agent: str
    task_id: str | None
    heartbeat: dict | None
    process_pids: list[int]
    cwds: set[str]
    paths: set[str]
    lanes: set[str]
    claim_paths: set[str]
    task_tokens: set[str]
    warnings: list[str]

    def to_json(self) -> dict:
        return {
            "agent": self.agent,
            "task_id": self.task_id,
            "heartbeat": self.heartbeat,
            "process_pids": sorted(self.process_pids),
            "cwds": sorted(self.cwds),
            "open_paths_under_llm": sorted(p for p in self.paths if p.startswith(LLM))[:200],
            "lanes": sorted(self.lanes),
            "claim_paths": sorted(self.claim_paths),
            "task_tokens": sorted(self.task_tokens),
            "warnings": self.warnings,
        }


def _json_strings(obj) -> Iterable[str]:
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k)
            yield from _json_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _json_strings(v)


def detect_active_session(snap: ProcSnapshot, args, aliases, scan_roots: list[str]) -> ActiveSession:
    warnings: list[str] = []
    bus = Path(args.bus_root)
    hb = None
    hb_path = bus / "heartbeats" / f"{args.active_agent}.json"
    try:
        hb = json.loads(hb_path.read_text())
    except (OSError, ValueError) as exc:
        warnings.append(f"heartbeat unreadable, active task UNKNOWN: {hb_path}: {exc}")
    task_id = args.active_task or (hb or {}).get("task_id")

    proc_re = re.compile(args.active_process_regex)
    children: dict[int, list[int]] = {}
    for p in snap.procs.values():
        children.setdefault(p.ppid, []).append(p.pid)
    roots = [p.pid for p in snap.procs.values() if proc_re.search(p.args)]
    session_pids: set[int] = set()
    stack = list(roots)
    while stack:
        pid = stack.pop()
        if pid in session_pids:
            continue
        session_pids.add(pid)
        stack.extend(children.get(pid, []))

    lanes: set[str] = set()
    if task_id:
        for mains in args.mains_roots:
            cand = os.path.join(mains, task_id)
            if os.path.isdir(cand):
                lanes.add(os.path.normpath(cand))
    tokens = {task_id} if task_id else set()
    tokens |= set(args.active_token or [])

    cwds: set[str] = set()
    paths: set[str] = set()
    for pid in session_pids:
        p = snap.procs[pid]
        if p.cwd:
            cwds.add(p.cwd)
        paths |= {x for x in p.paths if x.startswith("/")}
        paths |= p.argv_paths
        if not p.readable:
            warnings.append(f"session pid {pid} unreadable: its footprint is UNKNOWN")
    # processes (any owner) whose cwd sits in an active lane are session processes too
    for p in snap.procs.values():
        if p.cwd and any(is_within(p.cwd, lane) for lane in lanes):
            cwds.add(p.cwd)
    for c in list(cwds):
        if any(is_within(root, c) for root in scan_roots):
            warnings.append(f"session cwd {c} is an ancestor of a scan root: everything under it is KEEP")

    claim_paths: set[str] = set()
    claims_dir = bus / "claims"
    if claims_dir.is_dir():
        for f in claims_dir.glob("*.json"):  # top level only: claims/released/ are released
            try:
                data = json.loads(f.read_text())
            except (OSError, ValueError):
                continue
            if args.active_agent not in set(_json_strings(data)) and data.get("agent") != args.active_agent:
                continue
            for s in _json_strings(data):
                if s.startswith("/"):
                    claim_paths.add(norm_path(s, aliases))
    for lock_dir in args.lock_dirs:
        ld = Path(lock_dir)
        if not ld.is_dir():
            continue
        for f in ld.iterdir():
            if not f.is_file() or f.stat().st_size > STATE_FILE_MAX_BYTES:
                continue
            try:
                text = f.read_text(errors="replace")
            except OSError:
                continue
            if args.active_agent in text or (task_id and task_id in text):
                for tok in PATH_TOKEN_RE.findall(text):
                    if tok.startswith("/"):
                        claim_paths.add(norm_path(tok, aliases))
    return ActiveSession(
        agent=args.active_agent, task_id=task_id, heartbeat=hb, process_pids=sorted(session_pids),
        cwds=cwds, paths=paths, lanes=lanes, claim_paths=claim_paths, task_tokens=tokens,
        warnings=warnings,
    )


# --------------------------------------------------------------------------------------------
# reference corpus
# --------------------------------------------------------------------------------------------

@dataclass
class RefIndex:
    """Token sets per source class. `live` = loop code/config/state; `cite` = handoffs/docs;
    `retention` = retention-language contexts in progress logs."""
    names: dict[str, dict[str, str]] = field(default_factory=lambda: {"live": {}, "cite": {}, "retention": {}})
    pairs: dict[str, dict[str, str]] = field(default_factory=lambda: {"live": {}, "cite": {}, "retention": {}})
    sources: list[dict] = field(default_factory=list)

    def add_text(self, cls: str, text: str, origin: str) -> None:
        names, pairs = self.names[cls], self.pairs[cls]
        for tok in NAME_TOKEN_RE.findall(text):
            tok = tok.rstrip(".")
            names.setdefault(tok, origin)
        for tok in PATH_TOKEN_RE.findall(text):
            if "/" not in tok:
                continue
            comps = [c for c in tok.split("/") if c and c not in (".", "..")]
            for a, b in zip(comps, comps[1:]):
                pairs.setdefault(f"{a}/{b.rstrip('.')}", origin)

    def lookup(self, path: str) -> dict[str, str]:
        """Return {class: origin} for every class that references `path`."""
        base = os.path.basename(path)
        parent = os.path.basename(os.path.dirname(path))
        hits = {}
        for cls in ("live", "cite", "retention"):
            origin = self.pairs[cls].get(f"{parent}/{base}")
            if origin is None and len(base) >= BASENAME_MIN_DISTINCT and ("-" in base or "." in base):
                origin = self.names[cls].get(base)
            if origin is not None:
                hits[cls] = origin
        return hits


def _git_source_texts(spec: str) -> Iterable[tuple[str, str]]:
    repo, ref, pathspec = spec.split(":", 2)
    if not os.path.exists(repo):
        return
    rv = git(repo, "rev-parse", "--verify", "-q", ref)
    if rv.returncode != 0:
        return
    sha = rv.stdout.strip()
    pat = r"(/mnt/raid0/llm/|/workspace/|tmp/|worktrees/|\baku|autokernel-|akx-|s3-aku|glm53-validation)"
    res = git(repo, "grep", "-I", "-n", "-E", pat, sha, "--", pathspec, timeout=900)
    if res.returncode not in (0, 1):
        return
    yield f"{repo}@{ref}={sha[:12]}:{pathspec}", res.stdout


def _retention_texts(spec: str) -> Iterable[tuple[str, str]]:
    repo, ref, pathspec = spec.split(":", 2)
    if not os.path.exists(repo):
        return
    rv = git(repo, "rev-parse", "--verify", "-q", ref)
    if rv.returncode != 0:
        return
    sha = rv.stdout.strip()
    res = git(repo, "grep", "-I", "-n", "-C", "3", "-E", RETENTION_RE.pattern.replace("(?i)", ""),
              "-i", sha, "--", pathspec, timeout=900)
    if res.returncode not in (0, 1):
        return
    yield f"{repo}@{ref}={sha[:12]}:{pathspec} (retention contexts)", res.stdout


def build_ref_index(args) -> RefIndex:
    idx = RefIndex()

    def note(cls, origin, text):
        idx.add_text(cls, text, origin)
        idx.sources.append({"class": cls, "origin": origin,
                            "sha256": hashlib.sha256(text.encode()).hexdigest()[:16],
                            "bytes": len(text)})

    for spec in args.live_git_source:
        for origin, text in _git_source_texts(spec):
            note("live", origin, text)
    for spec in args.cite_git_source:
        for origin, text in _git_source_texts(spec):
            note("cite", origin, text)
    for spec in args.retention_git_source:
        for origin, text in _retention_texts(spec):
            note("retention", origin, text)
    for pattern in args.cite_file_glob:
        base = Path("/")
        for f in sorted(base.glob(pattern.lstrip("/"))):
            try:
                note("cite", str(f), f.read_text(errors="replace"))
            except OSError:
                continue
    # roster config: lanes declared by the bus are live references
    cfg = Path(args.bus_root) / "config.yaml"
    if cfg.is_file():
        note("live", str(cfg), cfg.read_text(errors="replace"))
    for sp in args.state_path:
        root = Path(sp)
        if not root.exists():
            continue
        files = [root] if root.is_file() else []
        if root.is_dir():
            for dirpath, dirnames, filenames in os.walk(root):
                depth = Path(dirpath).relative_to(root).parts
                if len(depth) >= 3:
                    dirnames[:] = []
                for fn in filenames:
                    if fn.endswith(STATE_FILE_SUFFIXES):
                        files.append(Path(dirpath) / fn)
        for f in files:
            try:
                if f.stat().st_size > STATE_FILE_MAX_BYTES:
                    continue
                note("live", str(f), f.read_text(errors="replace"))
            except OSError:
                continue
    return idx


# --------------------------------------------------------------------------------------------
# candidates
# --------------------------------------------------------------------------------------------

def roster_ids(bus_root: str) -> set[str]:
    cfg = Path(bus_root) / "config.yaml"
    ids: set[str] = set()
    try:
        for line in cfg.read_text().splitlines():
            m = re.match(r"\s*-\s*\{\s*id:\s*([A-Za-z0-9_.-]+)", line)
            if m and not line.lstrip().startswith("#"):
                ids.add(m.group(1))
    except OSError:
        pass
    return ids


def enumerate_candidates(args) -> list[tuple[str, str]]:
    """Return [(path, family)] -- family is 'worktree-root' or 'tmp'."""
    import glob

    mains_re = re.compile(args.mains_name_regex)
    out: dict[str, str] = {}
    for g in args.worktree_glob:
        for p in sorted(glob.glob(g)):
            if not os.path.isdir(p) and not os.path.islink(p):
                continue
            if any(os.path.dirname(os.path.normpath(p)) == os.path.normpath(m) for m in args.mains_roots):
                if not mains_re.search(os.path.basename(p)):
                    continue
            out[os.path.normpath(p)] = "worktree-root"
    for g in args.tmp_glob:
        for p in sorted(glob.glob(g)):
            if os.path.isdir(p) or os.path.islink(p):
                out.setdefault(os.path.normpath(p), "tmp")
    return sorted(out.items())


@dataclass
class WalkResult:
    newest: float
    newest_path: str
    files: int
    evidence: list[str]
    nested_git: list[str]
    error: str | None = None


def walk_tree(root: str, skip_top_git: bool) -> WalkResult:
    newest, newest_path, files = 0.0, root, 0
    skip_evidence: set[str] = set()
    evidence: list[str] = []
    nested: list[str] = []
    try:
        st = os.lstat(root)
        newest = max(st.st_mtime, st.st_ctime)
    except OSError as exc:
        return WalkResult(0.0, root, 0, [], [], error=str(exc))
    stack = [root]
    err = None
    while stack:
        d = stack.pop()
        try:
            it = os.scandir(d)
        except OSError as exc:
            err = f"scandir {d}: {exc}"
            continue
        with it:
            for e in it:
                try:
                    st = e.stat(follow_symlinks=False)
                except OSError:
                    continue
                t = max(st.st_mtime, st.st_ctime)
                if t > newest:
                    newest, newest_path = t, e.path
                if e.name == ".git":
                    if not (skip_top_git and d == root):
                        nested.append(os.path.relpath(e.path, root))
                    continue
                if stat.S_ISDIR(st.st_mode):
                    stack.append(e.path)
                    if e.name in EVIDENCE_SKIP_DIRS or d in skip_evidence:
                        skip_evidence.add(e.path)
                else:
                    files += 1
                    if d not in skip_evidence and EVIDENCE_RE.search(e.name):
                        evidence.append(os.path.relpath(e.path, root))
    return WalkResult(newest, newest_path, files, evidence, nested, error=err)


def is_network_url(url: str) -> bool:
    """A remote on this host's filesystem shares the clone's failure domain (evidence-retention
    §3.4 E2: "a local ref is insufficient"). `llama.cpp-cpu-fusion-20260829` has origin ->
    tmp/ak-loop-tree and prod -> /mnt/raid0/llm/llama.cpp, so `--remotes` alone would call
    local-only commits pushed."""
    if url.startswith("file://"):
        return False
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", url):
        return True
    return bool(re.match(r"^[^/\s]+@[^/:\s]+:", url)) or bool(re.match(r"^[A-Za-z0-9.-]+\.[A-Za-z]{2,}:", url))


@dataclass
class RepoCache:
    remote_counts: dict[str, int] = field(default_factory=dict)
    remote_args: dict[str, list[str]] = field(default_factory=dict)
    local_remotes: dict[str, list[str]] = field(default_factory=dict)
    heads: dict[str, list[str]] = field(default_factory=dict)
    checked_out: dict[str, dict[str, str]] = field(default_factory=dict)

    def load(self, repo: str) -> None:
        if repo in self.heads:
            return
        r = git(repo, "config", "--get-regexp", r"^remote\..*\.url$")
        net, local = [], []
        for line in r.stdout.splitlines():
            key, _, url = line.partition(" ")
            name = key[len("remote."):-len(".url")]
            (net if is_network_url(url.strip()) else local).append(name)
        self.remote_args[repo] = [f"--remotes={n}/*" for n in sorted(net)]
        self.local_remotes[repo] = sorted(local)
        count = 0
        for n in net:
            r = git(repo, "for-each-ref", "--format=%(refname)", f"refs/remotes/{n}")
            count += len(r.stdout.split()) if r.returncode == 0 else 0
        self.remote_counts[repo] = count
        r = git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads")
        self.heads[repo] = r.stdout.split() if r.returncode == 0 else []
        co: dict[str, str] = {}
        r = git(repo, "worktree", "list", "--porcelain")
        cur = None
        for line in r.stdout.splitlines():
            if line.startswith("worktree "):
                cur = os.path.normpath(line[9:])
            elif line.startswith("branch refs/heads/") and cur:
                co[line[len("branch refs/heads/"):]] = cur
        self.checked_out[repo] = co


def resolve_worktree(path: str) -> dict:
    """Inspect `<path>/.git`. Returns kind + owning repo + registration facts."""
    dotgit = os.path.join(path, ".git")
    if os.path.islink(path):
        return {"kind": "symlink"}
    if os.path.isdir(dotgit):
        return {"kind": "git-clone", "repo": path}
    if not os.path.isfile(dotgit):
        return {"kind": "plain"}
    try:
        text = Path(dotgit).read_text().strip()
    except OSError as exc:
        return {"kind": "worktree-orphan", "error": f"unreadable .git: {exc}"}
    if not text.startswith("gitdir:"):
        return {"kind": "worktree-orphan", "error": ".git file without gitdir"}
    admin = os.path.normpath(os.path.join(path, text[7:].strip()))
    if not os.path.isdir(admin):
        return {"kind": "worktree-orphan", "admin": admin, "error": "admin dir missing (registration lost)"}
    try:
        common_rel = Path(admin, "commondir").read_text().strip()
        common = os.path.normpath(os.path.join(admin, common_rel))
        back = Path(admin, "gitdir").read_text().strip()
    except OSError as exc:
        return {"kind": "worktree-orphan", "admin": admin, "error": f"admin files unreadable: {exc}"}
    back_norm = os.path.normpath(back if os.path.isabs(back) else os.path.join(admin, back))
    registered = os.path.realpath(back_norm) == os.path.realpath(dotgit)
    repo = os.path.dirname(common) if os.path.basename(common) == ".git" else common
    return {
        "kind": "git-worktree" if registered else "worktree-orphan",
        "repo": repo, "admin": admin, "locked": os.path.exists(os.path.join(admin, "locked")),
        "error": None if registered else f"admin gitdir points elsewhere: {back_norm}",
    }


# --------------------------------------------------------------------------------------------
# evaluation
# --------------------------------------------------------------------------------------------

@dataclass
class Context:
    args: argparse.Namespace
    aliases: list[tuple[str, str]]
    snap: ProcSnapshot
    session: ActiveSession
    refs: RefIndex
    roster: set[str]
    repos: RepoCache
    now: float


def live_hits(path: str, snap: ProcSnapshot, self_pid: int | None = None) -> list[str]:
    hits = []
    for p in snap.procs.values():
        where = None
        if p.cwd and is_within(p.cwd, path):
            where = f"cwd={p.cwd}"
        elif p.pid == self_pid:
            continue  # the sweep's own transient fds are not a holder; its cwd still is
        else:
            for x in p.paths:
                if is_within(x, path):
                    where = f"open={x}"
                    break
            if where is None:
                for x in p.argv_paths:
                    if is_within(x, path):
                        where = f"argv={x}"
                        break
        if where:
            hits.append(f"pid {p.pid} uid {p.uid} ({p.args[:80]}): {where}")
    return hits


def evaluate(path: str, family: str, ctx: Context, du_bytes: int | None = None) -> dict:
    a = ctx.args
    row: dict = {"path": path, "family": family, "size_bytes": du_bytes, "reasons": {}}
    reasons: dict[str, list[str]] = row["reasons"]

    def add(verdict, why):
        reasons.setdefault(verdict, []).append(why)

    info = resolve_worktree(path)
    row["kind"] = info["kind"]
    row["repo"] = info.get("repo")
    base = os.path.basename(path)

    # (active session) footprint, task tokens, recency
    s = ctx.session
    for c in s.cwds:
        if is_within(path, c) or is_within(c, path):
            add("KEEP-active-session", f"session cwd {c}")
    for x in s.paths | s.claim_paths:
        if is_within(x, path):
            add("KEEP-active-session", f"session open/claimed path {x}")
            break
    for lane in s.lanes:
        if is_within(path, lane) or is_within(lane, path):
            add("KEEP-active-session", f"active task lane {lane}")
    walk = walk_tree(path, skip_top_git=info["kind"] in ("git-worktree", "worktree-orphan", "git-clone"))
    row["newest_mtime"] = iso(walk.newest)
    row["newest_path"] = walk.newest_path
    row["files"] = walk.files
    cutoff = ctx.now - a.recency_hours * 3600
    if walk.newest >= cutoff:
        add("KEEP-active-session",
            f"recency guard: {walk.newest_path} changed {iso(walk.newest)} (< {a.recency_hours}h)")
    if walk.error:
        add("KEEP-unverifiable", f"walk incomplete: {walk.error}")

    # (c) live processes
    for h in live_hits(path, ctx.snap, self_pid=os.getpid()):
        add("KEEP-live", h)

    # (e) registered roster lane
    if any(os.path.dirname(path) == os.path.normpath(m) for m in a.mains_roots) and base in ctx.roster:
        add("KEEP-referenced", f"registered roster lane worktrees/mains/{base}")

    evidence = list(walk.evidence)
    if info["kind"] == "symlink":
        add("KEEP-unverifiable", "candidate is a symlink; not followed")
    elif info["kind"] == "worktree-orphan":
        add("KEEP-unverifiable", f"worktree registration broken: {info.get('error')}")
    elif info["kind"] == "git-clone":
        add("KEEP-unverifiable", "full clone (.git dir), not a worktree: out of scope")
    elif info["kind"] == "plain":
        if walk.nested_git:
            owners = sorted({describe_nested(path, n) for n in walk.nested_git})
            row["nested_git"] = {"count": len(walk.nested_git), "owners": owners[:10]}
            add("KEEP-unverifiable", f"contains {len(walk.nested_git)} nested git repo/worktree(s) "
                                     f"owned by {owners[:4]}: remove those per-worktree first")
    elif info["kind"] == "git-worktree":
        repo = info["repo"]
        if info.get("locked"):
            add("KEEP-unverifiable", "worktree is locked")
        if walk.nested_git:
            add("KEEP-unverifiable", f"contains nested git repo/worktree(s): {walk.nested_git[:3]}")
        ctx.repos.load(repo)
        # (a) clean
        st = git(path, "status", "--porcelain=v1", "-z", "--untracked-files=normal")
        if st.returncode != 0:
            add("KEEP-unverifiable", f"git status failed: {st.stderr.strip()[:200]}")
        elif st.stdout.strip("\x00"):
            entries = [e for e in st.stdout.split("\x00") if e]
            add("KEEP-dirty", f"{len(entries)} modified/untracked: {entries[:3]}")
            if a.landed_check:
                row["dirty_landed"] = dirty_landed(path, ctx.repos.remote_args.get(repo, []))
        # (b) pushed
        head = git(path, "rev-parse", "HEAD")
        row["head"] = head.stdout.strip() if head.returncode == 0 else None
        sym = git(path, "symbolic-ref", "-q", "--short", "HEAD")
        row["branch"] = sym.stdout.strip() if sym.returncode == 0 else None
        if ctx.repos.remote_counts.get(repo, 0) == 0:
            add("KEEP-unpushed", f"owning repo {repo} has no remote-tracking refs from a network remote "
                                 f"(local-path remotes ignored: {ctx.repos.local_remotes.get(repo)})")
        elif row["head"] is None:
            add("KEEP-unverifiable", "no resolvable HEAD")
        else:
            refs = [row["head"]]
            names = ["HEAD"]
            co = ctx.repos.checked_out.get(repo, {})
            for b in ctx.repos.heads.get(repo, []):
                if (b == row["branch"] or base in b) and co.get(b, path) == path:
                    refs.append(b)
                    names.append(b)
            for ref, nm in zip(refs, names):
                r = git(repo, "rev-list", "-n", "1", ref, "--not", *ctx.repos.remote_args[repo])
                if r.returncode != 0:
                    add("KEEP-unverifiable", f"rev-list {nm} failed: {r.stderr.strip()[:120]}")
                elif r.stdout.strip():
                    add("KEEP-unpushed", f"{nm} has commits not in any network remote-tracking ref "
                                         f"({r.stdout.strip()[:12]})")
        for tok in s.task_tokens:
            if tok and (tok in base or (row.get("branch") and tok in row["branch"])):
                add("KEEP-active-session", f"branch/name carries active task id {tok}")
        # only untracked (ignored) evidence is at risk; tracked evidence is in git
        if evidence:
            tracked = git(path, "ls-files", "-z", "--", *[f":(literal){e}" for e in evidence[:2000]])
            tset = set(tracked.stdout.split("\x00")) if tracked.returncode == 0 else set()
            evidence = [e for e in evidence if e not in tset]
    if info["kind"] != "git-worktree":
        for tok in s.task_tokens:
            if tok and tok in base:
                add("KEEP-active-session", f"name carries active task id {tok}")

    # (d) references
    hits = ctx.refs.lookup(path)
    if "live" in hits:
        add("KEEP-referenced", f"live loop reference: {hits['live']}")
    cite_origin = hits.get("cite") or hits.get("retention")
    row["evidence_files"] = len(evidence)
    row["evidence_sample"] = evidence[:10]
    if evidence:
        add("ARCHIVE-evidence",
            f"{len(evidence)} evidence file(s)" + (f"; cited by {cite_origin}" if cite_origin else ""))
    elif cite_origin:
        add("KEEP-referenced", f"cited: {cite_origin}")

    verdict = next((v for v in VERDICT_ORDER if v in reasons), "REMOVE")
    row["verdict"] = verdict
    row["reason"] = "; ".join(reasons.get(verdict, ["all checks (a)-(e) passed"]))[:600]
    return row


def describe_nested(root: str, rel: str) -> str:
    """Owning repo of a nested `.git` (file => worktree of some clone; dir => standalone clone)."""
    p = os.path.join(root, rel)
    if os.path.isdir(p):
        return "standalone-clone"
    try:
        text = Path(p).read_text().strip()
    except OSError:
        return "unreadable"
    gd = text[7:].strip() if text.startswith("gitdir:") else ""
    gd = os.path.normpath(gd if os.path.isabs(gd) else os.path.join(os.path.dirname(p), gd))
    marker = "/.git/worktrees/"
    return gd.split(marker)[0] if marker in gd else gd


def dirty_landed(tree: str, remote_args: list[str], cap: int = 200) -> dict:
    """Annotation only -- never changes the verdict. For each modified/untracked file, is its exact
    working-tree blob introduced at that path by some commit reachable from a remote-tracking ref?
    All-landed means the dirty content already survives in git (an operator-reviewed reset would
    make the tree clean); anything else means the tree holds the only copy."""
    st = git(tree, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    entries = [e for e in st.stdout.split("\x00") if e]
    out = {"files": len(entries), "landed": 0, "not_landed": [], "unknown": 0}
    if len(entries) > cap or not remote_args:
        out["unknown"] = len(entries)
        return out
    for e in entries:
        code, rel = e[:2], e[3:]
        if "D" in code or "R" in code or not os.path.isfile(os.path.join(tree, rel)):
            out["unknown"] += 1
            continue
        h = git(tree, "hash-object", "--", rel)
        if h.returncode != 0:
            out["unknown"] += 1
            continue
        lg = git(tree, "log", *remote_args, "-n", "1", "--format=%H", f"--find-object={h.stdout.strip()}",
                 "--", f":(literal){rel}", timeout=300)
        if lg.returncode == 0 and lg.stdout.strip():
            out["landed"] += 1
        else:
            out["not_landed"].append(rel)
    out["not_landed"] = out["not_landed"][:20]
    out["all_landed"] = out["landed"] == out["files"]
    return out


HOLDER_VERDICTS = ("KEEP-active-session", "KEEP-live")
HOLDER_STATE_SUFFIXES = (".json", ".jsonl", ".yaml", ".yml", ".toml", ".sh", ".md", ".txt")


def family_key(base: str) -> str | None:
    """`aku12a-glm53-five-loop-store` -> `aku12a-glm53-five-loop`: siblings a live store writes to
    (its -builds/-workers/-inputs/-output) share every name component but the last."""
    parts = [p for p in re.split(r"[-.]", base) if p]
    return "-".join(parts[:-1]) if len(parts) >= 3 else None


def holder_index(rows: list[dict], max_files: int = 2000) -> tuple[RefIndex, dict[str, str]]:
    """Cross-row guards. A candidate held by a live session can reference siblings from its own
    state (loop-status.json, recipes) or from a SQLite db we cannot grep. So: (1) index the small
    text state files (depth <= 2) of every held candidate; (2) key every held candidate's name
    family. Both feed KEEP-referenced for otherwise-REMOVE rows."""
    idx = RefIndex()
    families: dict[str, str] = {}
    for r in rows:
        if r.get("verdict") not in HOLDER_VERDICTS:
            continue
        root = r["path"]
        fk = family_key(os.path.basename(root))
        if fk:
            families.setdefault(fk, root)
        seen = 0
        for dirpath, dirnames, filenames in os.walk(root):
            if len(Path(dirpath).relative_to(root).parts) >= 2:
                dirnames[:] = []
            dirnames[:] = [d for d in dirnames if d not in EVIDENCE_SKIP_DIRS and d != ".git"]
            for fn in filenames:
                if not fn.endswith(HOLDER_STATE_SUFFIXES):
                    continue
                fp = os.path.join(dirpath, fn)
                try:
                    if os.lstat(fp).st_size > STATE_FILE_MAX_BYTES:
                        continue
                    idx.add_text("live", Path(fp).read_text(errors="replace"), f"held candidate state {fp}")
                except OSError:
                    continue
                seen += 1
                if seen >= max_files:
                    break
            if seen >= max_files:
                break
    return idx, families


def apply_holder_guards(row: dict, idx: RefIndex, families: dict[str, str]) -> dict:
    if row.get("verdict") != "REMOVE":
        return row
    why = []
    hit = idx.lookup(row["path"]).get("live")
    if hit:
        why.append(f"referenced by {hit}")
    fk = family_key(os.path.basename(row["path"]))
    if fk and fk in families and families[fk] != row["path"]:
        why.append(f"name family '{fk}' of held candidate {families[fk]}")
    if why:
        row["reasons"].setdefault("KEEP-referenced", []).extend(why)
        row["verdict"] = "KEEP-referenced"
        row["reason"] = "; ".join(row["reasons"]["KEEP-referenced"])[:600]
    return row


def du_sizes(paths: list[str]) -> dict[str, int]:
    """One `du` call so hardlinks are counted once (reclaim totals are not inflated)."""
    if not paths:
        return {}
    res = subprocess.run(["du", "-s", "-B1", "--files0-from=-"], input="\x00".join(paths) + "\x00",
                         capture_output=True, text=True)
    out = {}
    for line in res.stdout.splitlines():
        size, _, p = line.partition("\t")
        if size.isdigit():
            out[os.path.normpath(p)] = int(size)
    return out


def make_context(args, need_refs: bool = True, refs: RefIndex | None = None) -> Context:
    aliases = parse_aliases(args.path_alias)
    snap = probe_processes(args.proc_root, aliases)
    scan_roots = sorted({os.path.dirname(g) for g in args.worktree_glob + args.tmp_glob})
    session = detect_active_session(snap, args, aliases, scan_roots)
    if refs is None:
        refs = build_ref_index(args) if need_refs else RefIndex()
    return Context(args=args, aliases=aliases, snap=snap, session=session, refs=refs,
                   roster=roster_ids(args.bus_root), repos=RepoCache(), now=time.time())


def summarize(rows: list[dict]) -> dict:
    summary: dict[str, dict] = {v: {"count": 0, "bytes": 0} for v in VERDICT_ORDER}
    for r in rows:
        s = summary[r["verdict"]]
        s["count"] += 1
        s["bytes"] += r.get("size_bytes") or 0
    return summary


def scan(args) -> int:
    t0 = time.time()
    ctx = make_context(args)
    cands = enumerate_candidates(args)
    sizes = du_sizes([p for p, _ in cands]) if not args.no_du else {}
    rows: list[dict] = []
    with cf.ThreadPoolExecutor(max_workers=args.jobs) as ex:
        futs = {ex.submit(evaluate, p, fam, ctx, sizes.get(p)): p for p, fam in cands}
        for f in cf.as_completed(futs):
            try:
                rows.append(f.result())
            except Exception as exc:  # never let one row abort; unknown = keep
                rows.append({"path": futs[f], "verdict": "KEEP-unverifiable", "reason": f"evaluate crashed: {exc!r}",
                             "reasons": {"KEEP-unverifiable": [repr(exc)]}, "size_bytes": sizes.get(futs[f])})
    rows.sort(key=lambda r: r["path"])
    for _ in range(3):  # fixpoint: a guard never creates a new holder, but stay bounded
        idx, families = holder_index(rows)
        before = sum(r["verdict"] == "REMOVE" for r in rows)
        rows = [apply_holder_guards(r, idx, families) for r in rows]
        if sum(r["verdict"] == "REMOVE" for r in rows) == before:
            break
    manifest = {
        "schema": SCHEMA,
        "generated_at": now_utc().isoformat(timespec="seconds"),
        "host": socket.gethostname(),
        "euid": os.geteuid(),
        "mode": "dry-run",
        "params": {k: v for k, v in vars(args).items() if k not in ("manifest", "manifest_sha", "apply")},
        "process_probe": ctx.snap.summary(),
        "active_session": ctx.session.to_json(),
        "reference_sources": ctx.refs.sources,
        "summary": summarize(rows),
        "elapsed_s": round(time.time() - t0, 1),
        "rows": rows,
    }
    os.makedirs(args.out_dir, exist_ok=True)
    stamp = now_utc().strftime("%Y%m%dT%H%M%SZ")
    mpath = os.path.join(args.out_dir, f"autokernel-disk-sweep-manifest-{stamp}.json")
    data = json.dumps(manifest, indent=1, sort_keys=True).encode()
    with open(mpath, "wb") as fh:
        fh.write(data)
    sha = hashlib.sha256(data).hexdigest()
    with open(mpath + ".sha256", "w") as fh:
        fh.write(f"{sha}  {os.path.basename(mpath)}\n")
    print(json.dumps({"manifest": mpath, "manifest_sha256": sha, "process_probe": ctx.snap.state,
                      "summary": {k: {"count": v["count"], "GB": round(v["bytes"] / 1e9, 1)}
                                  for k, v in manifest["summary"].items()}}, indent=1))
    return 0


# --------------------------------------------------------------------------------------------
# apply
# --------------------------------------------------------------------------------------------

# params that decide a verdict come from the reviewed manifest, not from the apply command line
CLASSIFY_KEYS = (
    "worktree_glob", "tmp_glob", "mains_roots", "mains_name_regex", "allowed_root", "proc_root",
    "path_alias", "bus_root", "active_agent", "active_task", "active_token", "active_process_regex",
    "lock_dirs", "live_git_source", "cite_git_source", "cite_file_glob", "retention_git_source",
    "state_path",
)


def operator_confirm(todo: list[dict], sha: str) -> bool:
    """Operator rule (2026-09-15): every deletion needs the operator's manual confirmation.

    Interactive only: stdin must be a TTY and the operator must type the first 12 hex chars of
    the reviewed manifest's sha256. A pipe, a heredoc or an agent harness cannot satisfy it."""
    if not sys.stdin.isatty():
        return False
    gb = sum(r.get("size_bytes") or 0 for r in todo) / 1e9
    print(f"About to remove {len(todo)} REMOVE rows (~{gb:.1f} GB) after per-row re-checks.", file=sys.stderr)
    try:
        typed = input("Operator: type the first 12 hex chars of the manifest sha256 to confirm: ")
    except EOFError:
        return False
    return typed.strip().lower() == sha[:12]


def _receipt(fh, **kw):
    kw["ts"] = now_utc().isoformat(timespec="seconds")
    fh.write(json.dumps(kw, sort_keys=True) + "\n")
    fh.flush()


def apply(args) -> int:
    data = Path(args.manifest).read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    if sha != args.manifest_sha:
        print(f"REFUSED: manifest sha256 {sha} != --manifest-sha {args.manifest_sha}", file=sys.stderr)
        return 2
    manifest = json.loads(data)
    if manifest.get("schema") != SCHEMA:
        print(f"REFUSED: unknown manifest schema {manifest.get('schema')}", file=sys.stderr)
        return 2
    gen = dt.datetime.fromisoformat(manifest["generated_at"])
    age_h = (now_utc() - gen).total_seconds() / 3600
    if age_h > args.max_manifest_age_hours:
        print(f"REFUSED: manifest is {age_h:.1f}h old (> {args.max_manifest_age_hours}h); re-scan and re-review",
              file=sys.stderr)
        return 2
    params = manifest.get("params", {})
    for k in CLASSIFY_KEYS:
        if k in params:
            setattr(args, k, params[k])
    args.recency_hours = max(args.recency_hours, float(params.get("recency_hours", 0)))
    allowed = [os.path.normpath(r) for r in args.allowed_root]
    todo = [r for r in manifest["rows"] if r["verdict"] == "REMOVE"]
    if not operator_confirm(todo, sha):
        print("REFUSED: operator manual confirmation required (interactive TTY, typed sha prefix)",
              file=sys.stderr)
        return 4
    receipt_path = args.manifest + f".apply-{now_utc().strftime('%Y%m%dT%H%M%SZ')}.jsonl"
    refs: RefIndex | None = None
    refs_at = 0.0
    holders: tuple[RefIndex, dict[str, str]] | None = None
    removed = skipped = 0
    with open(receipt_path, "w") as rf:
        _receipt(rf, event="start", manifest=args.manifest, manifest_sha=sha, rows=len(todo))
        for row in todo:
            path = row["path"]
            if refs is None or time.time() - refs_at > args.refs_refresh_s:
                refs = build_ref_index(args)
                holders = holder_index(manifest["rows"])
                refs_at = time.time()
            ctx = make_context(args, refs=refs)
            if ctx.snap.state != "COMPLETE":
                msg = (f"REFUSED (whole run): process probe {ctx.snap.state} "
                       f"({ctx.snap.summary()['unreadable']} unreadable, by uid "
                       f"{ctx.snap.summary()['unreadable_by_uid']}). Unknown means busy; run as host root.")
                _receipt(rf, event="refuse-run", reason=msg, probe=ctx.snap.summary())
                print(msg, file=sys.stderr)
                print(f"removed={removed} skipped={skipped} receipt={receipt_path}")
                return 3
            if any("UNKNOWN" in w for w in ctx.session.warnings):
                msg = f"REFUSED (whole run): active-session footprint unknown: {ctx.session.warnings}"
                _receipt(rf, event="refuse-run", reason=msg)
                print(msg, file=sys.stderr)
                print(f"removed={removed} skipped={skipped} receipt={receipt_path}")
                return 3
            if not os.path.lexists(path):
                _receipt(rf, event="skip", path=path, reason="already gone")
                skipped += 1
                continue
            real = os.path.realpath(path)
            if real != os.path.normpath(path) or not any(is_within(real, r) and real != r for r in allowed):
                _receipt(rf, event="skip", path=path, reason=f"outside allowed roots or symlinked ({real})")
                skipped += 1
                continue
            fresh = apply_holder_guards(evaluate(path, row.get("family", "tmp"), ctx), *holders)
            if fresh["verdict"] != "REMOVE" or fresh["kind"] != row.get("kind") or \
                    (row.get("head") and fresh.get("head") != row.get("head")):
                _receipt(rf, event="skip", path=path, reason="re-check changed verdict/kind/head",
                         fresh_verdict=fresh["verdict"], fresh_reason=fresh["reason"])
                skipped += 1
                continue
            if fresh["kind"] == "git-worktree":
                r = git(fresh["repo"], "worktree", "remove", path)  # NEVER --force, NEVER prune
                ok = r.returncode == 0
                _receipt(rf, event="removed" if ok else "remove-failed", path=path, kind="git-worktree",
                         repo=fresh["repo"], head=fresh.get("head"), size_bytes=row.get("size_bytes"),
                         stderr=r.stderr.strip()[:400])
            elif fresh["kind"] == "plain":
                try:
                    shutil.rmtree(path)
                    ok = True
                    err = ""
                except OSError as exc:
                    ok, err = False, str(exc)
                _receipt(rf, event="removed" if ok else "remove-failed", path=path, kind="plain",
                         size_bytes=row.get("size_bytes"), error=err)
            else:
                ok = False
                _receipt(rf, event="skip", path=path, reason=f"kind {fresh['kind']} is never removed")
            removed += 1 if ok else 0
            skipped += 0 if ok else 1
        _receipt(rf, event="end", removed=removed, skipped=skipped)
    print(f"removed={removed} skipped={skipped} receipt={receipt_path}")
    return 0


# --------------------------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="remove REMOVE rows of a reviewed manifest")
    ap.add_argument("--manifest", help="manifest JSON to apply")
    ap.add_argument("--manifest-sha", help="sha256 of the manifest bytes (from the dry-run output)")
    ap.add_argument("--max-manifest-age-hours", type=float, default=72.0)
    ap.add_argument("--out-dir", default=f"{LLM}/tmp/sub-aksweep")
    ap.add_argument("--recency-hours", type=float, default=24.0,
                    help="KEEP-active-session if anything inside changed within this window")
    ap.add_argument("--worktree-glob", action="append")
    ap.add_argument("--tmp-glob", action="append")
    ap.add_argument("--mains-root", dest="mains_roots", action="append")
    ap.add_argument("--mains-name-regex", default=DEFAULT_MAINS_NAME_RE)
    ap.add_argument("--allowed-root", action="append")
    ap.add_argument("--proc-root", default="/proc")
    ap.add_argument("--path-alias", action="append", help="SRC=DST prefix mapping for /proc paths")
    ap.add_argument("--bus-root", default=DEFAULT_BUS_ROOT)
    ap.add_argument("--active-agent", default="inference")
    ap.add_argument("--active-task", default=None, help="default: task_id from the agent's bus heartbeat")
    ap.add_argument("--active-token", action="append", help="extra name tokens owned by the active session")
    ap.add_argument("--active-process-regex", default=r"(^|/)codex(\s|$)|@openai/codex|codex-linux")
    ap.add_argument("--lock-dir", dest="lock_dirs", action="append")
    ap.add_argument("--live-git-source", action="append", help="repo:ref:pathspec (loop code/config)")
    ap.add_argument("--cite-git-source", action="append", help="repo:ref:pathspec (handoffs/docs)")
    ap.add_argument("--cite-file-glob", action="append")
    ap.add_argument("--retention-git-source", action="append")
    ap.add_argument("--state-path", action="append", help="loop state file/dir (json/yaml/jsonl scanned)")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--no-du", action="store_true")
    ap.add_argument("--no-landed-check", dest="landed_check", action="store_false",
                    help="skip the dirty-content-landed annotation (it never changes a verdict)")
    ap.add_argument("--refs-refresh-s", type=float, default=120.0)
    return ap


def apply_defaults(args) -> None:
    defaults = {
        "worktree_glob": DEFAULT_WORKTREE_GLOBS, "tmp_glob": DEFAULT_TMP_GLOBS,
        "mains_roots": [f"{LLM}/worktrees/mains"], "allowed_root": DEFAULT_ALLOWED_ROOTS,
        "path_alias": DEFAULT_PATH_ALIASES, "lock_dirs": [f"{ROOT_DIR}/coordination/push-locks"],
        "live_git_source": DEFAULT_LIVE_GIT_SOURCES, "cite_git_source": DEFAULT_CITE_GIT_SOURCES,
        "cite_file_glob": DEFAULT_CITE_FILE_GLOBS, "retention_git_source": DEFAULT_RETENTION_GIT_SOURCES,
        "state_path": DEFAULT_STATE_PATHS,
    }
    for k, v in defaults.items():
        if getattr(args, k) is None:
            setattr(args, k, list(v))


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    apply_defaults(args)
    if args.apply:
        if not (args.manifest and args.manifest_sha):
            ap.error("--apply requires --manifest and --manifest-sha")
        return apply(args)
    if args.manifest or args.manifest_sha:
        ap.error("--manifest/--manifest-sha are only meaningful with --apply")
    return scan(args)


if __name__ == "__main__":
    sys.exit(main())
