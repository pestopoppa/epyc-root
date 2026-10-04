#!/usr/bin/env python3
"""Codex (~/.codex) retention reaper — NIB2-84. DEFAULT IS A DRY-RUN REPORT.

`~/.codex` had no retention and no reaper: it grows ~0.75 GB/day under delegation load
(2026-10-04: ~33 GB — sessions/ 23G of rollout JSONL, packages/ 3.6G of superseded codex
releases, thread_history_1/state_5/logs_2 sqlite ~6 GB). This tool bounds the two classes that
can be reclaimed WITHOUT touching anything codex holds:

  rollouts  sessions/YYYY/MM/DD/rollout-*.jsonl older than N days whose byte-identical copy
            exists in the host vault (default /mnt/raid0/llm/cloud-llm-vault/epyc/codex, which
            mirrors sessions/ path-for-path: vault/<YYYY/MM/DD/rollout-*.jsonl>).
  packages  packages/<pkg>/releases/<release> directories no running process references and
            that are neither `current`, the auto-update target, the latest version, nor among
            the newest --keep-releases.

The sqlite DBs are REPORTED ONLY in v1 (size, WAL size, whether a process holds them open).
Nothing here ever opens them: codex app-server runs as a managed daemon and holds them.

    # report (read-only on ~/.codex; cheap enough for a scheduled hygiene tick)
    python3 scripts/system/codex_retention_reaper.py report --json > /path/report.json

    # apply: ONLY after the operator reviewed a report and confirms. Acts on exactly the list
    # that report printed (its manifest), re-verifying every entry just before unlink.
    python3 scripts/system/codex_retention_reaper.py apply --older-than-days 14 --confirm-token <tok>

ROLLOUT VERDICTS (only files older than --older-than-days by mtime are classified):
  open        some process holds the file open (read-only /proc/*/fd walk), OR the walk is
              blind (no /proc, nothing inspectable, or an uninspectable process whose argv says
              codex) — fail closed: blind means open. Never eligible.
  unarchived  no vault copy, a size mismatch, a sha256 mismatch, or the vault path is the same
              inode (a hard link/symlink frees nothing). Never eligible in v1.
  unverified  sizes match but the sha256 pair is not known yet: not hashed within this run's
              --max-hash-gib budget. Not eligible until a later report verifies it.
  archived    size equal AND sha256 equal to the vault copy. ELIGIBLE.

HASHING IS BOUNDED. Only size-matched old files are hashed (never a non-candidate), oldest
first, both sides charged against --max-hash-gib (default 4). Digests are cached in
<state-dir>/hash_cache.json keyed by (path, size, mtime_ns, inode), so the backlog is cleared
incrementally across ticks and a steady-state tick hashes ~one day's worth. `apply` NEVER trusts
the cache: it re-hashes both sides of every entry immediately before the unlink.

THE CONFIRM TOKEN. `report` writes the eligible list to <state-dir>/manifests/<token>.json; the
token is a sha256 prefix over the manifest's canonical content and is recomputed on load, so
`apply` refuses a missing, edited, stale (>7 days) or mismatched (--home/--vault/N) manifest.
Every unlink/rmtree (and every skip) is appended to <state-dir>/ledger.jsonl, fsynced.

CODEX OBSERVER (three-state, read-only, mirrors observer_guard.sh's fold): channel proc_scan
(a process whose exe/argv0 lives under <home>/packages or whose argv0 basename is `codex`) and
channel db_fd (a process holds <home>/*.sqlite open). present / absent when both channels agree
and neither is blind; unobservable otherwise. v1 consumer: sqlite actions are withheld in every
state (report-only); the verdict is reported so a v2 VACUUM path can gate on `absent` only.
This tool never launches, signals or kills any process.

Exit codes:
  0  report produced / apply finished (per-entry skips are normal and are ledgered)
  2  usage error
  3  --home missing or unreadable (fail closed: nothing classified)
  4  apply REFUSED: missing/invalid/edited/stale token or manifest, argument mismatch,
     ledger unwritable, or the /proc walk is blind at apply start
  5  apply hit an OS error on at least one entry (partial progress is in the ledger)

stdlib only. Runs at nice +10.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

SCHEMA = "codex-retention-report/v1"
MANIFEST_SCHEMA = "codex-retention-manifest/v1"
DEFAULT_HOME = os.path.expanduser("~/.codex")
DEFAULT_VAULT = "/mnt/raid0/llm/cloud-llm-vault/epyc/codex"
DEFAULT_STATE_DIR = "/mnt/raid0/llm/tmp/codex-reaper"
DEFAULT_OLDER_THAN_DAYS = 14.0
DEFAULT_MAX_HASH_GIB = 4.0
DEFAULT_KEEP_RELEASES = 2
DEFAULT_PACKAGE_MIN_AGE_DAYS = 2.0
MANIFEST_MAX_AGE_S = 7 * 86400
TOKEN_LEN = 20
TOKEN_RE = re.compile(rf"^[0-9a-f]{{{TOKEN_LEN}}}$")
CODEX_PID_REFRESH_S = 1.0

EXIT_OK, EXIT_USAGE, EXIT_HOME, EXIT_REFUSED, EXIT_ERRORS = 0, 2, 3, 4, 5


# --------------------------------------------------------------------------- #
# /proc view (read-only). Fail closed: anything we could not look at is "blind".
# --------------------------------------------------------------------------- #

class ProcView:
    """One read-only walk of /proc.

    open_targets  every fd readlink target of every inspectable process (self excluded)
    codex_pids    processes identified as codex (exe/argv0 under <home>/packages, argv0 `codex`)
    pkg_refs      exe/cwd/argv/maps/fd strings that point under <home>/packages
    blind         reasons the walk cannot be trusted as a negative (empty == trustworthy)
    """

    def __init__(self, home: str, proc: str = "/proc"):
        self.home = home
        self.home_real = os.path.realpath(home)
        self.pkg_prefixes = tuple({os.path.join(home, "packages") + "/",
                                   os.path.join(self.home_real, "packages") + "/"})
        self.proc = proc
        self.open_targets: set[str] = set()
        self.codex_pids: set[int] = set()
        self.pkg_refs: set[str] = set()
        self.blind: list[str] = []
        self.inspected = 0
        self._scan()

    def _is_pkg_path(self, s: str) -> bool:
        return s.startswith(self.pkg_prefixes)

    @staticmethod
    def _codexish(cmdline: str) -> bool:
        return "codex" in cmdline.lower()

    def _identify_codex(self, exe: str | None, argv: list[str]) -> bool:
        if exe and self._is_pkg_path(exe):
            return True
        if argv:
            a0 = argv[0]
            if self._is_pkg_path(a0) or os.path.basename(a0) == "codex":
                return True
        return False

    def _scan(self) -> None:
        me = os.getpid()
        try:
            pids = [int(d) for d in os.listdir(self.proc) if d.isdigit()]
        except OSError as exc:
            self.blind.append(f"/proc not listable: {exc}")
            return
        for pid in pids:
            if pid == me:
                continue
            base = f"{self.proc}/{pid}"
            try:
                raw = Path(f"{base}/cmdline").read_bytes()
            except (FileNotFoundError, ProcessLookupError):
                continue
            except OSError as exc:
                self.blind.append(f"pid {pid}: cmdline unreadable ({exc.__class__.__name__})")
                continue
            argv = [a.decode(errors="replace") for a in raw.split(b"\0") if a]
            cmd = " ".join(argv)
            try:
                exe = os.readlink(f"{base}/exe")
            except OSError:
                exe = None
            try:
                fds = os.listdir(f"{base}/fd")
            except (FileNotFoundError, ProcessLookupError):
                continue
            except OSError:
                # Uninspectable (another uid, kernel thread). Harmless unless it could be codex.
                if self._codexish(cmd) or (exe and "codex" in exe.lower()):
                    self.blind.append(f"pid {pid}: codex-like process with unreadable fds")
                continue
            self.inspected += 1
            is_codex = self._identify_codex(exe, argv)
            if is_codex:
                self.codex_pids.add(pid)
            for fd in fds:
                try:
                    t = os.readlink(f"{base}/fd/{fd}")
                except (FileNotFoundError, ProcessLookupError):
                    continue
                except OSError:
                    if is_codex or self._codexish(cmd):
                        self.blind.append(f"pid {pid}: fd {fd} unreadable")
                    continue
                self.open_targets.add(t)
                if self._is_pkg_path(t):
                    self.pkg_refs.add(t)
            if exe and self._is_pkg_path(exe):
                self.pkg_refs.add(exe)
            try:
                cwd = os.readlink(f"{base}/cwd")
                if self._is_pkg_path(cwd):
                    self.pkg_refs.add(cwd)
            except OSError:
                pass
            for tok in argv:
                if "packages" in tok:
                    for cand in (tok, os.path.realpath(tok) if tok.startswith("/") else tok):
                        if self._is_pkg_path(cand):
                            self.pkg_refs.add(cand)
            if is_codex or self._codexish(cmd):
                try:
                    with open(f"{base}/maps", "rb") as fh:
                        for line in fh:
                            parts = line.split(None, 5)
                            if len(parts) == 6:
                                p = parts[5].strip().decode(errors="replace")
                                if self._is_pkg_path(p):
                                    self.pkg_refs.add(p)
                except (FileNotFoundError, ProcessLookupError):
                    pass
                except OSError:
                    self.blind.append(f"pid {pid}: maps unreadable")
        if self.inspected == 0:
            self.blind.append("no /proc/<pid>/fd directory was inspectable")

    @property
    def ok(self) -> bool:
        return not self.blind

    def holds(self, path: str) -> bool:
        real = os.path.realpath(path)
        return path in self.open_targets or real in self.open_targets


def codex_fds_hold(pids: set[int], real: str, proc: str = "/proc") -> bool | None:
    """Cheap per-file re-check over the codex pids only. None == could not tell."""
    for pid in pids:
        try:
            fds = os.listdir(f"{proc}/{pid}/fd")
        except (FileNotFoundError, ProcessLookupError):
            continue
        except OSError:
            return None
        for fd in fds:
            try:
                if os.readlink(f"{proc}/{pid}/fd/{fd}") == real:
                    return True
            except (FileNotFoundError, ProcessLookupError):
                continue
            except OSError:
                return None
    return False


def observe_codex(view: ProcView, home: str) -> dict:
    """Three-state fold over proc_scan and db_fd (observer_guard.sh semantics)."""
    channels: dict[str, str] = {}
    blind = not view.ok
    channels["proc_scan"] = "unavailable" if blind else ("present" if view.codex_pids else "absent")
    dbs = sorted(Path(home).glob("*.sqlite"))
    if not dbs:
        pass  # no DB on disk: the channel is not configured (omitted), not a negative
    elif blind:
        channels["db_fd"] = "unavailable"
    else:
        held = any(view.holds(str(p) + sfx) for p in dbs for sfx in ("", "-wal", "-shm"))
        channels["db_fd"] = "present" if held else "absent"
    vals = set(channels.values())
    if "unavailable" in vals:
        state, why = "unobservable", "a channel could not be evaluated"
    elif len(vals) == 1:
        state, why = vals.pop(), "channels agree"
    else:
        state, why = "unobservable", "channels disagree"
    if blind:
        why += "; " + "; ".join(view.blind[:3])
    return {
        "state": state, "why": why, "channels": channels,
        "codex_pids": sorted(view.codex_pids),
        "sqlite_action": "withheld (v1 is report-only for sqlite in every state)",
    }


# --------------------------------------------------------------------------- #
# Hashing with a (path,size,mtime_ns,inode)-keyed cache
# --------------------------------------------------------------------------- #

def sha256_file(path: str) -> str:
    with open(path, "rb") as fh:
        if hasattr(hashlib, "file_digest"):
            return hashlib.file_digest(fh, "sha256").hexdigest()
        h = hashlib.sha256()
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
        return h.hexdigest()


class HashCache:
    def __init__(self, path: Path | None):
        self.path = path
        self.old: dict = {}
        self.new: dict = {}
        self.hits = 0
        if path and path.exists():
            try:
                self.old = json.loads(path.read_text()).get("entries", {})
            except (OSError, ValueError):
                self.old = {}

    @staticmethod
    def _key(st: os.stat_result) -> list:
        return [st.st_size, st.st_mtime_ns, st.st_ino]

    def get(self, path: str, st: os.stat_result) -> str | None:
        e = self.old.get(path) or self.new.get(path)
        if e and e[:3] == self._key(st):
            self.hits += 1
            self.new[path] = e
            return e[3]
        return None

    def put(self, path: str, st: os.stat_result, digest: str) -> None:
        self.new[path] = self._key(st) + [digest]

    def save(self) -> str | None:
        if not self.path:
            return None
        try:
            _atomic_write(self.path, json.dumps({"entries": self.new}, separators=(",", ":")))
            return None
        except OSError as exc:
            return f"hash cache not saved: {exc}"


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


# --------------------------------------------------------------------------- #
# Classification
# --------------------------------------------------------------------------- #

def _iter_rollouts(sessions: str):
    for root, dirs, files in os.walk(sessions, followlinks=False):
        dirs.sort()
        for name in files:
            if name.startswith("rollout-") and name.endswith(".jsonl"):
                yield os.path.join(root, name)


def classify_rollouts(home: str, vault: str, older_than_days: float, view: ProcView,
                      cache: HashCache, budget_bytes: int, now: float) -> dict:
    sessions = os.path.join(home, "sessions")
    cutoff = now - older_than_days * 86400
    young = {"count": 0, "bytes": 0}
    skipped = {"count": 0, "bytes": 0}
    old: list[tuple[str, os.stat_result]] = []
    for p in _iter_rollouts(sessions):
        try:
            st = os.lstat(p)
        except OSError:
            continue
        if not os.path.isfile(p) or os.path.islink(p):
            skipped["count"] += 1
            continue
        if st.st_mtime >= cutoff:
            young["count"] += 1
            young["bytes"] += st.st_size
        else:
            old.append((p, st))
    old.sort(key=lambda t: t[1].st_mtime_ns)  # oldest first: the budget clears the backlog by age

    classes = {k: [] for k in ("archived", "unarchived", "unverified", "open")}
    hashed = 0
    for p, st in old:
        rel = os.path.relpath(p, sessions)
        rec = {"rel": rel, "size": st.st_size, "mtime_ns": st.st_mtime_ns, "ino": st.st_ino}
        if not view.ok:
            rec["reason"] = "proc walk blind (fail closed)"
            classes["open"].append(rec)
            continue
        if view.holds(p):
            rec["reason"] = "held open by a process"
            classes["open"].append(rec)
            continue
        vp = os.path.join(vault, rel)
        try:
            vst = os.stat(vp)
        except OSError:
            rec["reason"] = "no vault copy"
            classes["unarchived"].append(rec)
            continue
        if (vst.st_dev, vst.st_ino) == (st.st_dev, st.st_ino):
            rec["reason"] = "vault path is the same inode (frees nothing)"
            classes["unarchived"].append(rec)
            continue
        if vst.st_size != st.st_size:
            rec["reason"] = f"size mismatch (vault {vst.st_size})"
            classes["unarchived"].append(rec)
            continue
        lh, vh = cache.get(p, st), cache.get(vp, vst)
        cost = (0 if lh else st.st_size) + (0 if vh else vst.st_size)
        if cost and hashed + cost > budget_bytes:
            rec["reason"] = "size match; sha256 pending (hash budget exhausted)"
            classes["unverified"].append(rec)
            continue
        try:
            if not lh:
                lh = sha256_file(p)
                cache.put(p, st, lh)
                hashed += st.st_size
            if not vh:
                vh = sha256_file(vp)
                cache.put(vp, vst, vh)
                hashed += vst.st_size
        except OSError as exc:
            rec["reason"] = f"hash failed ({exc.__class__.__name__})"
            classes["unarchived"].append(rec)
            continue
        if lh != vh:
            rec["reason"] = "size match but sha256 differs"
            classes["unarchived"].append(rec)
            continue
        rec["sha256"] = lh
        classes["archived"].append(rec)
    return {"classes": classes, "young": young, "skipped_non_regular": skipped,
            "hashed_bytes": hashed, "cutoff_epoch": cutoff}


def _dir_bytes(path: str) -> tuple[int, int]:
    total = files = 0
    for root, _dirs, fnames in os.walk(path, followlinks=False):
        for f in fnames:
            try:
                total += os.lstat(os.path.join(root, f)).st_size
                files += 1
            except OSError:
                pass
    return total, files


def classify_packages(home: str, view: ProcView, keep_releases: int,
                      min_age_days: float, now: float, sizes: bool = True) -> list[dict]:
    out = []
    pkgroot = os.path.join(home, "packages")
    try:
        pkgs = sorted(os.listdir(pkgroot))
    except OSError:
        return out
    latest = None
    try:
        latest = json.loads(Path(home, "version.json").read_text()).get("latest_version")
    except (OSError, ValueError, AttributeError):
        pass
    for pkg in pkgs:
        rdir = os.path.join(pkgroot, pkg, "releases")
        try:
            names = [n for n in os.listdir(rdir) if os.path.isdir(os.path.join(rdir, n))
                     and not os.path.islink(os.path.join(rdir, n))]
        except OSError:
            continue
        cur = None
        try:
            cur = os.path.realpath(os.path.join(pkgroot, pkg, "current"))
        except OSError:
            pass
        try:
            auto = Path(pkgroot, pkg, "auto-update-version").read_text().strip()
        except OSError:
            auto = None
        mt = {}
        for n in names:
            try:
                mt[n] = os.stat(os.path.join(rdir, n)).st_mtime
            except OSError:
                mt[n] = now
        newest = set(sorted(names, key=lambda n: mt[n], reverse=True)[:max(keep_releases, 0)])
        for n in sorted(names, key=lambda n: mt[n]):
            path = os.path.join(rdir, n)
            real = os.path.realpath(path)
            keep = []
            if cur and (cur == real or cur.startswith(real + "/")):
                keep.append("current")
            if auto and n == auto:
                keep.append("auto-update-version")
            if latest and (n == latest or n.startswith(f"{latest}-")):
                keep.append("latest_version")
            if n in newest:
                keep.append(f"newest-{keep_releases}")
            if not view.ok:
                keep.append("proc walk blind (fail closed)")
            elif any(r == path or r == real or r.startswith(path + "/") or r.startswith(real + "/")
                     for r in view.pkg_refs):
                keep.append("referenced by a running process")
            if now - mt[n] < min_age_days * 86400:
                keep.append(f"younger than {min_age_days}d")
            b, f = _dir_bytes(path) if sizes else (0, 0)
            out.append({"pkg": pkg, "release": n, "bytes": b, "files": f,
                        "mtime": int(mt[n]), "verdict": "keep" if keep else "eligible",
                        "keep_reasons": keep})
    return out


def sqlite_sizes(home: str, view: ProcView) -> list[dict]:
    out = []
    for p in sorted(Path(home).glob("*.sqlite")):
        rec = {"name": p.name}
        for sfx, key in (("", "bytes"), ("-wal", "wal_bytes"), ("-shm", "shm_bytes")):
            try:
                rec[key] = os.stat(str(p) + sfx).st_size
            except OSError:
                rec[key] = 0
        rec["held_open"] = (None if not view.ok else
                            any(view.holds(str(p) + s) for s in ("", "-wal", "-shm")))
        rec["action"] = "report-only (v1)"
        out.append(rec)
    return out


# --------------------------------------------------------------------------- #
# Manifest / token
# --------------------------------------------------------------------------- #

def _manifest_body(home: str, vault: str, older: float, rollouts: list, packages: list) -> dict:
    return {
        "home": home, "vault": vault, "older_than_days": older,
        "rollouts": [{k: r[k] for k in ("rel", "size", "mtime_ns", "ino", "sha256")}
                     for r in rollouts],
        "packages": [{k: p[k] for k in ("pkg", "release", "bytes", "files", "mtime")}
                     for p in packages],
    }


def _token_for(body: dict) -> str:
    canon = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()[:TOKEN_LEN]


def _summ(recs: list, limit: int) -> dict:
    d = {"count": len(recs), "bytes": sum(r["size"] for r in recs),
         "sample": [r["rel"] for r in recs[:limit]]}
    reasons: dict[str, int] = {}
    for r in recs:
        if "reason" in r:
            k = re.sub(r"\(vault \d+\)", "(vault N)", r["reason"])
            reasons[k] = reasons.get(k, 0) + 1
    if reasons:
        d["reasons"] = reasons
    return d


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #

def cmd_report(a) -> int:
    home, vault, state = a.home, a.vault, Path(a.state_dir)
    if not os.path.isdir(home) or not os.access(home, os.R_OK | os.X_OK):
        print(f"codex home {home} missing or unreadable", file=sys.stderr)
        return EXIT_HOME
    now = time.time()
    warnings: list[str] = []
    view = ProcView(home)
    cache = HashCache(state / "hash_cache.json")
    budget = int(a.max_hash_gib * (1 << 30))
    ro = classify_rollouts(home, vault, a.older_than_days, view, cache, budget, now)
    w = cache.save()
    if w:
        warnings.append(w)
    pk = classify_packages(home, view, a.keep_releases, a.package_min_age_days, now)
    sq = sqlite_sizes(home, view)
    cls = ro["classes"]
    eligible_pk = [p for p in pk if p["verdict"] == "eligible"]
    if not os.path.isdir(vault):
        warnings.append(f"vault {vault} not found: every old rollout reads unarchived")

    token = manifest_path = None
    if cls["archived"] or eligible_pk:
        body = _manifest_body(home, vault, a.older_than_days, cls["archived"], eligible_pk)
        token = _token_for(body)
        manifest = dict(body, schema=MANIFEST_SCHEMA, token=token, generated_at=now)
        manifest_path = state / "manifests" / f"{token}.json"
        try:
            _atomic_write(manifest_path, json.dumps(manifest, indent=1))
        except OSError as exc:
            warnings.append(f"manifest not written ({exc}); no confirm token issued")
            token = manifest_path = None

    _prune_manifests(state / "manifests", now, keep=manifest_path)

    rb = {
        "rollouts_archived": sum(r["size"] for r in cls["archived"]),
        "packages_eligible": sum(p["bytes"] for p in eligible_pk),
    }
    rb["total"] = rb["rollouts_archived"] + rb["packages_eligible"]
    rb["rollouts_pending_hash"] = sum(r["size"] for r in cls["unverified"])
    lim = a.max_list
    report = {
        "schema": SCHEMA,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        "home": home, "vault": vault, "state_dir": str(state),
        "older_than_days": a.older_than_days,
        "cutoff": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ro["cutoff_epoch"])),
        "observer": observe_codex(view, home),
        "rollouts": {
            "classes": {k: _summ(v, lim) for k, v in cls.items()},
            "young": ro["young"],
            "skipped_non_regular": ro["skipped_non_regular"],
        },
        "packages": {
            "keep_releases": a.keep_releases, "min_age_days": a.package_min_age_days,
            "releases": pk,
            "eligible": {"count": len(eligible_pk), "bytes": rb["packages_eligible"]},
        },
        "sqlite": sq,
        "reclaimable_bytes": rb,
        "hashing": {"budget_bytes": budget, "hashed_bytes": ro["hashed_bytes"],
                    "cache_hits": cache.hits},
        "confirm_token": token,
        "manifest": str(manifest_path) if manifest_path else None,
        "apply_command": (f"python3 scripts/system/codex_retention_reaper.py apply "
                          f"--older-than-days {a.older_than_days:g} --confirm-token {token}"
                          + ("" if home == DEFAULT_HOME else f" --home {home}")
                          + ("" if vault == DEFAULT_VAULT else f" --vault {vault}")
                          + ("" if str(state) == DEFAULT_STATE_DIR else f" --state-dir {state}")
                          if token else None),
        "warnings": warnings,
    }
    try:
        _atomic_write(state / "last_report.json", json.dumps(report, indent=1))
    except OSError as exc:
        report["warnings"].append(f"last_report.json not written: {exc}")
    if a.json:
        print(json.dumps(report, indent=1))
    else:
        _print_human(report)
    return EXIT_OK


def _prune_manifests(mdir: Path, now: float, keep: Path | None) -> None:
    """Manifests past MANIFEST_MAX_AGE_S can never be applied; drop them (own state dir only)."""
    try:
        entries = list(mdir.glob("*.json"))
    except OSError:
        return
    for m in entries:
        try:
            if m != keep and now - m.stat().st_mtime > MANIFEST_MAX_AGE_S:
                m.unlink()
        except OSError:
            pass


def _gb(n: int) -> str:
    return f"{n / 1e9:.2f} GB"


def _print_human(r: dict) -> None:
    print(f"codex retention report  {r['generated_at']}  home={r['home']}")
    print(f"  vault={r['vault']}  older-than={r['older_than_days']:g}d (cutoff {r['cutoff']})")
    o = r["observer"]
    print(f"  codex observer: {o['state']} ({o['why']}) channels={o['channels']}")
    print("  rollouts:")
    for k, v in r["rollouts"]["classes"].items():
        print(f"    {k:<11} {v['count']:>6} files  {_gb(v['bytes'])}  {v.get('reasons', '')}")
    y = r["rollouts"]["young"]
    print(f"    {'young':<11} {y['count']:>6} files  {_gb(y['bytes'])}  (inside the window)")
    print("  packages:")
    for p in r["packages"]["releases"]:
        print(f"    {p['pkg']}/{p['release']:<40} {_gb(p['bytes'])}  {p['verdict']}"
              f"  {','.join(p['keep_reasons'])}")
    print("  sqlite (report-only):")
    for s in r["sqlite"]:
        print(f"    {s['name']:<28} {_gb(s['bytes'])}  wal {_gb(s['wal_bytes'])}"
              f"  held_open={s['held_open']}")
    rb = r["reclaimable_bytes"]
    print(f"  reclaimable: rollouts {_gb(rb['rollouts_archived'])} + packages "
          f"{_gb(rb['packages_eligible'])} = {_gb(rb['total'])}"
          f"  (pending hash: {_gb(rb['rollouts_pending_hash'])})")
    h = r["hashing"]
    print(f"  hashed {_gb(h['hashed_bytes'])} of budget {_gb(h['budget_bytes'])}, "
          f"cache hits {h['cache_hits']}")
    for w in r["warnings"]:
        print(f"  WARNING: {w}")
    if r["confirm_token"]:
        print(f"  confirm token: {r['confirm_token']}\n  to apply (operator-confirmed only):"
              f"\n    {r['apply_command']}")
    else:
        print("  nothing eligible; no confirm token issued")


class Ledger:
    def __init__(self, path: Path, token: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.fh = open(path, "a", encoding="utf-8")
        self.token = token

    def write(self, **rec) -> None:
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "token": self.token, **rec}
        self.fh.write(json.dumps(rec, sort_keys=True) + "\n")
        self.fh.flush()
        os.fsync(self.fh.fileno())


def _refuse(msg: str) -> int:
    print(f"REFUSED: {msg}", file=sys.stderr)
    return EXIT_REFUSED


def cmd_apply(a) -> int:
    # OPERATOR DIRECTIVE 2026-10-04 (hard rule): "Claude/codex backup logs should NOT BE TOUCHED UNDER ANY
    # CIRCUMSTANCES. They are historical transcripts used by a root filesystem project far more senior to
    # anything performed in this project repo." apply is permanently disabled; this tool is report-only.
    print("codex_retention_reaper: apply is PERMANENTLY DISABLED by operator directive (2026-10-04): "
          "Claude/codex session logs and backups are never deleted by this project. Report-only.", file=sys.stderr)
    return 4

def _cmd_apply_disabled_original(a) -> int:
    home, vault, state = a.home, a.vault, Path(a.state_dir)
    if not os.path.isdir(home):
        print(f"codex home {home} missing", file=sys.stderr)
        return EXIT_HOME
    tok = a.confirm_token or ""
    if not TOKEN_RE.match(tok):
        return _refuse("--confirm-token is missing or malformed; run `report` and review it first")
    mpath = state / "manifests" / f"{tok}.json"
    try:
        man = json.loads(mpath.read_text())
    except (OSError, ValueError):
        return _refuse(f"no readable manifest for token {tok} under {state}/manifests")
    body = {k: man.get(k) for k in ("home", "vault", "older_than_days", "rollouts", "packages")}
    if man.get("schema") != MANIFEST_SCHEMA or _token_for(body) != tok:
        return _refuse("manifest content does not hash to the token (edited or corrupt)")
    if body["home"] != home or body["vault"] != vault:
        return _refuse(f"manifest was made for home={body['home']} vault={body['vault']}")
    if float(body["older_than_days"]) != float(a.older_than_days):
        return _refuse(f"manifest was made with --older-than-days {body['older_than_days']}")
    now = time.time()
    if now - float(man.get("generated_at", 0)) > MANIFEST_MAX_AGE_S:
        return _refuse("manifest is older than 7 days; run a fresh report")
    try:
        ledger = Ledger(state / "ledger.jsonl", tok)
    except OSError as exc:
        return _refuse(f"ledger not writable: {exc}")
    view = ProcView(home)
    if not view.ok:
        return _refuse("the /proc walk is blind: " + "; ".join(view.blind[:3]))

    sessions = os.path.join(home, "sessions")
    cutoff = now - a.older_than_days * 86400
    done = {"unlinked": 0, "unlinked_bytes": 0, "rmtree": 0, "rmtree_bytes": 0,
            "skipped": 0, "errors": 0}
    codex_pids, refreshed = set(view.codex_pids), time.monotonic()

    def skip(kind: str, path: str, reason: str) -> None:
        done["skipped"] += 1
        ledger.write(action="skip", kind=kind, path=path, reason=reason)

    for e in body["rollouts"]:
        p = os.path.join(sessions, e["rel"])
        vp = os.path.join(vault, e["rel"])
        try:
            st = os.lstat(p)
        except OSError:
            skip("rollout", p, "gone")
            continue
        if not os.path.isfile(p) or os.path.islink(p):
            skip("rollout", p, "not a regular file")
            continue
        if [st.st_size, st.st_mtime_ns, st.st_ino] != [e["size"], e["mtime_ns"], e["ino"]]:
            skip("rollout", p, "changed since report (size/mtime/inode)")
            continue
        if st.st_mtime >= cutoff:
            skip("rollout", p, "inside the retention window")
            continue
        if view.holds(p):
            skip("rollout", p, "held open (apply-start scan)")
            continue
        try:
            vst = os.stat(vp)
        except OSError:
            skip("rollout", p, "vault copy gone")
            continue
        if (vst.st_dev, vst.st_ino) == (st.st_dev, st.st_ino) or vst.st_size != st.st_size:
            skip("rollout", p, "vault copy no longer a separate same-size file")
            continue
        try:
            lh, vh = sha256_file(p), sha256_file(vp)
        except OSError as exc:
            skip("rollout", p, f"re-hash failed ({exc.__class__.__name__})")
            continue
        if not (lh == vh == e["sha256"]):
            skip("rollout", p, "sha256 re-verification failed")
            continue
        if time.monotonic() - refreshed > CODEX_PID_REFRESH_S:
            fresh = ProcView(home)
            if not fresh.ok:
                skip("rollout", p, "proc walk went blind")
                continue
            codex_pids, refreshed = set(fresh.codex_pids), time.monotonic()
        held = codex_fds_hold(codex_pids, os.path.realpath(p))
        if held is not False:
            skip("rollout", p, "held open by codex (pre-unlink check)" if held
                 else "codex fds unreadable (pre-unlink check)")
            continue
        try:
            st2 = os.lstat(p)
            if [st2.st_size, st2.st_mtime_ns, st2.st_ino] != [e["size"], e["mtime_ns"], e["ino"]]:
                skip("rollout", p, "changed during verification")
                continue
            os.unlink(p)
        except OSError as exc:
            done["errors"] += 1
            ledger.write(action="error", kind="rollout", path=p, error=str(exc))
            continue
        done["unlinked"] += 1
        done["unlinked_bytes"] += st.st_size
        ledger.write(action="unlink", kind="rollout", path=p, vault_path=vp,
                     size=st.st_size, mtime_ns=st.st_mtime_ns, sha256=lh)

    if body["packages"]:
        fresh = ProcView(home)
        current = {(p["pkg"], p["release"]): p for p in
                   classify_packages(home, fresh, a.keep_releases, a.package_min_age_days,
                                     now, sizes=False)}
        for e in body["packages"]:
            path = os.path.join(home, "packages", e["pkg"], "releases", e["release"])
            c = current.get((e["pkg"], e["release"]))
            if c is None:
                skip("package_release", path, "gone")
                continue
            if c["verdict"] != "eligible":
                skip("package_release", path, "no longer eligible: " + ",".join(c["keep_reasons"]))
                continue
            lock = os.path.join(home, "packages", e["pkg"], "install.lock")
            lfh = None
            try:
                if os.path.exists(lock):
                    lfh = open(lock, "rb")
                    fcntl.flock(lfh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                if lfh:
                    lfh.close()
                skip("package_release", path, "install.lock busy (codex updating)")
                continue
            try:
                b, f = _dir_bytes(path)
                shutil.rmtree(path)
            except OSError as exc:
                done["errors"] += 1
                ledger.write(action="error", kind="package_release", path=path, error=str(exc))
                continue
            finally:
                if lfh:
                    lfh.close()
            done["rmtree"] += 1
            done["rmtree_bytes"] += b
            ledger.write(action="rmtree", kind="package_release", path=path, bytes=b, files=f)

    print(json.dumps({"token": tok, "ledger": str(state / "ledger.jsonl"), **done}, indent=1))
    return EXIT_ERRORS if done["errors"] else EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="codex_retention_reaper.py",
        description="Bounded retention for ~/.codex (NIB2-84). Default: dry-run report.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="exit codes: 0 ok, 2 usage, 3 home missing, 4 apply refused, 5 apply errors")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--home", default=DEFAULT_HOME, help="codex home (default ~/.codex)")
    common.add_argument("--vault", default=DEFAULT_VAULT,
                        help=f"rollout vault mirroring sessions/ (default {DEFAULT_VAULT})")
    common.add_argument("--state-dir", default=DEFAULT_STATE_DIR,
                        help=f"cache/manifests/ledger dir (default {DEFAULT_STATE_DIR})")
    common.add_argument("--keep-releases", type=int, default=DEFAULT_KEEP_RELEASES,
                        help="always keep this many newest package releases (default 2)")
    common.add_argument("--package-min-age-days", type=float, default=DEFAULT_PACKAGE_MIN_AGE_DAYS,
                        help="a package release must be at least this old (default 2)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report", parents=[common], help="dry-run report (read-only on --home)")
    r.add_argument("--json", action="store_true", help="machine-readable output")
    r.add_argument("--older-than-days", type=float, default=DEFAULT_OLDER_THAN_DAYS)
    r.add_argument("--max-hash-gib", type=float, default=DEFAULT_MAX_HASH_GIB,
                   help="sha256 budget per run over size-matched candidates (default 4)")
    r.add_argument("--max-list", type=int, default=20, help="sample paths listed per class")
    p = sub.add_parser("apply", parents=[common], help="DISABLED (operator 2026-10-04): never deletes codex/claude logs")
    p.add_argument("--older-than-days", type=float, required=True)
    p.add_argument("--confirm-token", default=None)
    return ap


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    a.home = os.path.abspath(os.path.expanduser(a.home))
    a.vault = os.path.abspath(os.path.expanduser(a.vault))
    try:
        os.nice(10)
    except OSError:
        pass
    return cmd_report(a) if a.cmd == "report" else cmd_apply(a)


if __name__ == "__main__":
    sys.exit(main())
