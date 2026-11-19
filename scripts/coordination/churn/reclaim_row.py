#!/usr/bin/env python3
"""RECLAIM-AT-FILING: free a filed row's declared RAW scratch the moment its verdict is filed.

    reclaim_row.py <row-id> [--flags DIR] [--apply] [--pre-filed] [--salvage-dir DIR] [--tmp-root DIR] [--json]

Dry-run unless --apply. Complement of the keeper's REAP-AFTER-FILING (ws58-calendar-keeper-v13.sh section 6),
never looser than it:
  * refusals: exit 2 no manifest / no end record (grants/<id>.ended|.complete); exit 6 no absolute scratch_root
    under the tmp root, no filing-done/<id>.FILED (unless --pre-filed), or a raw glob that is absolute / has '..'.
  * RAW is declared, never inferred: manifest `raw` (list of relative globs) else `raw_globs=a,b` in notes.
    Retention: manifest `retention: {"raw_days": N}` else `raw_days=N` in notes (default 0). End record younger
    than N days -> HOLD. No raw declaration -> NO-RAW (the keeper's 1-day backstop applies).
  * KEEP SET (a raw match is reaped only if neither it, an ancestor, nor any descendant is kept): keep globs,
    result_path (+ RESULT*/results* siblings), INPUT RULE files (mtime before `started=` in the end record, else the
    manifest mtime), KEEP markers (worktree_gate.KEEP_MARKERS, *.epyc-keep) at any depth, evidence names
    (worktree_gate.EVIDENCE_RE), FILED/receipt files, registered git worktrees (released separately), anything
    resolving outside scratch_root.
  * SHARED-LIVE GUARD: another NON-TERMINAL row (ready/, armed, open grant) whose scratch_root, workdir, --workdir or
    result_path resolves (realpath) to the same dir, a parent or a child, or a row pinned in <flags>/filing-no-reclaim.globs
    -> nothing reclaimed, RECLAIM-SKIPPED-SHARED (scratch_guard.py; filing still stands).
  * BUSY (a live cwd/argv/environ names the root, or an open fd under it) -> nothing done. SHARED (another
    manifest naming an overlapping scratch_root is not filed) -> nothing done.
  * --apply: each candidate goes through scripts/safety/guarded_rm.sh (TRASH_ROOT = $RECLAIM_TRASH_ROOT or
    /mnt/raid0/llm/.trash-reap); then row-owned worktrees (row_worktree.release_row_worktrees -> worktree_salvage.retire).
Receipt: <flags>/filing-done/<id>.reclaim.json on every run past the refusals. Exit 0, or 7 when a deletion failed.
This file has no deletion primitive of its own: guarded_rm and worktree_salvage are the only deletion paths.
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(os.path.dirname(HERE))
for _p in (HERE, os.path.join(SCRIPTS, "system"), os.path.join(SCRIPTS, "coordination", "job_templates")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import filing  # noqa: E402  (the end-record / manifest readers)
import scratch_guard  # noqa: E402
import row_worktree as rw  # noqa: E402
import worktree_gate as wg  # noqa: E402
import worktree_salvage as ws  # noqa: E402

DEFAULT_FLAGS = os.environ.get("ROWFLOW_FLAGS", "/mnt/raid0/llm/tmp/compute-flags")


def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def raw_decl(m: dict):
    """-> (globs list | None, retention_days float)."""
    notes = str(m.get("notes") or "")
    raw = m.get("raw")
    if raw is None:
        mm = re.search(r"\braw_globs=(\S+)", notes)
        raw = [g for g in mm.group(1).split(",") if g] if mm else None
    if raw is not None and not (isinstance(raw, list) and all(isinstance(g, str) for g in raw)):
        raw = [str(raw)]
    ret = m.get("retention")
    days = _num(ret.get("raw_days")) if isinstance(ret, dict) else None
    if days is None:
        mm = re.search(r"\braw_days=([0-9.]+)", notes)
        days = _num(mm.group(1)) if mm else None
    return raw, (days or 0.0)


def bad_glob(g: str) -> bool:
    return not g or g.startswith("/") or ".." in g.replace("\\", "/").split("/")


def iso_epoch(s: str):
    s = s.strip().split()[0] if s.strip() else ""
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def start_cutoff(ep: str, mp: str):
    """INPUT RULE cutoff: `started=` in the end record, else the manifest mtime."""
    try:
        with open(ep, errors="replace") as fh:
            for ln in fh:
                if ln.startswith("started="):
                    e = iso_epoch(ln[8:])
                    if e:
                        return e, "started="
    except OSError:
        pass
    return os.path.getmtime(mp), "manifest mtime"


def is_marker(name: str) -> bool:
    return name in wg.KEEP_MARKERS or name.endswith(".epyc-keep")


def is_receipt(name: str) -> bool:
    return name == "FILED" or name.endswith(".FILED") or "receipt" in name.lower()


def open_fd_under(root: str, proc_root: str = "/proc"):
    """Read-only walk of /proc/*/fd: first `pid path` with an open fd under root, else None."""
    rr = os.path.realpath(root)
    me = str(os.getpid())
    try:
        pids = [p for p in os.listdir(proc_root) if p.isdigit() and p != me]
    except OSError:
        return None
    for pid in pids:
        d = f"{proc_root}/{pid}/fd"
        try:
            fds = os.listdir(d)
        except OSError:
            continue
        for fd in fds:
            try:
                t = os.readlink(f"{d}/{fd}")
            except OSError:
                continue
            if t == rr or t.startswith(rr + "/"):
                return f"pid {pid} fd -> {t}"
    return None


def shared_unfiled(flags: str, rid: str, root: str):
    """Another manifest (ready/, ready/*/) naming an overlapping scratch_root that is not filed -> its id."""
    rr = os.path.normpath(root)
    for p in glob.glob(os.path.join(flags, "ready", "*.json")) + glob.glob(os.path.join(flags, "ready", "*", "*.json")):
        try:
            with open(p) as fh:
                m = json.load(fh)
        except (OSError, ValueError):
            continue
        if not isinstance(m, dict) or m.get("id") in (None, rid):
            continue
        sr = m.get("scratch_root")
        if not isinstance(sr, str) or not os.path.isabs(sr):
            continue
        o = os.path.normpath(sr)
        if o == rr or o.startswith(rr + "/") or rr.startswith(o + "/"):
            if not os.path.exists(os.path.join(flags, "filing-done", str(m["id"]) + ".FILED")):
                return str(m["id"])
    return None


def keep_map(root: str, m: dict, cutoff: float, worktree_paths) -> dict:
    """realpath -> why, for every directly kept path under root."""
    rr = os.path.realpath(root)
    kept: dict = {}

    def add(p, why):
        kept.setdefault(os.path.realpath(p), why)

    for g in m.get("keep") or []:
        if isinstance(g, str) and not bad_glob(g):
            for p in glob.glob(os.path.join(root, g), recursive=True):
                add(p, "keep-glob")
    rp = m.get("result_path")
    if isinstance(rp, str) and rp:
        for p in (glob.glob(rp) if any(c in rp for c in "*?[") else [rp]):
            add(p, "result")
            par = os.path.dirname(p)
            for s in glob.glob(os.path.join(par, "RESULT*")) + glob.glob(os.path.join(par, "results*")):
                add(s, "result-sibling")
    for w in worktree_paths:
        add(w, "worktree")
    for dp, dns, fns in os.walk(rr):
        if os.path.realpath(dp) in kept and kept[os.path.realpath(dp)] == "worktree":
            dns[:] = []
            continue
        for n in fns + dns:
            p = os.path.join(dp, n)
            if is_marker(n):
                add(p, "keep-marker")
            elif wg.EVIDENCE_RE.search(n):
                add(p, "evidence")
            elif is_receipt(n):
                add(p, "receipt")
        for n in fns:
            p = os.path.join(dp, n)
            try:
                if os.lstat(p).st_mtime < cutoff:
                    add(p, "input")
            except OSError:
                add(p, "stat-error")
        for n in list(dns):
            p = os.path.join(dp, n)
            if os.path.islink(p):
                continue
            try:
                if not os.listdir(p) and os.lstat(p).st_mtime < cutoff:
                    add(p, "input")
            except OSError:
                add(p, "stat-error")
    return kept


def keep_reason(path: str, kept: dict, kept_anc: dict, root: str):
    rp = os.path.realpath(path)
    rr = os.path.realpath(root)
    if not rp.startswith(rr + "/"):
        return "outside-root"
    if rp in kept:
        return kept[rp]
    if rp in kept_anc:
        return "holds-" + kept_anc[rp]
    a = os.path.dirname(rp)
    while a.startswith(rr + "/"):
        if a in kept:
            return "inside-" + kept[a]
        a = os.path.dirname(a)
    return None


def size_of(p: str) -> int:
    try:
        if os.path.isdir(p) and not os.path.islink(p):
            t = 0
            for dp, _dn, fns in os.walk(p):
                for f in fns:
                    try:
                        t += os.lstat(os.path.join(dp, f)).st_size
                    except OSError:
                        pass
            return t
        return os.lstat(p).st_size
    except OSError:
        return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("row_id")
    ap.add_argument("--flags", default=DEFAULT_FLAGS)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--pre-filed", action="store_true", help="caller has just written the FILED receipt")
    ap.add_argument("--salvage-dir", default=ws.DEFAULT_SALVAGE_DIR)
    ap.add_argument("--tmp-root")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    rid, flags = a.row_id, a.flags
    mp, m = filing.load_manifest(flags, rid)
    if not m:
        print(f"REFUSED {rid}: no manifest", file=sys.stderr); return 2
    sr = m.get("scratch_root")
    err = rw.scratch_root_error(sr, a.tmp_root)
    if err:
        print(f"REFUSED {rid}: {err}"); return 6
    root = os.path.normpath(sr)
    ep, _rc, _line = filing.load_end(flags, rid)
    if ep is None:
        print(f"REFUSED {rid}: no end record"); return 2
    done = os.path.join(flags, "filing-done")
    if not a.pre_filed and not os.path.exists(os.path.join(done, rid + ".FILED")):
        print(f"REFUSED {rid}: not filed (no filing-done/{rid}.FILED)"); return 6
    raw, days = raw_decl(m)
    if raw and any(bad_glob(g) for g in raw):
        print(f"REFUSED {rid}: raw glob absolute or with '..': {raw}"); return 6
    tag = "RECLAIM" if a.apply else "RECLAIM-DRYRUN"
    rec = {"id": rid, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "apply": a.apply, "raw": raw, "retention_days": days, "scratch_root": root, "candidates": [], "kept": [],
           "worktrees": [], "bytes_reclaimed": 0, "state": None, "reason": None}

    def finish(state, reason=None, code=0):
        rec["state"], rec["reason"] = state, reason
        os.makedirs(done, exist_ok=True)
        with open(os.path.join(done, rid + ".reclaim.json"), "w") as fh:
            json.dump(rec, fh, indent=1, sort_keys=True)
        print(f"SUMMARY {tag} row={rid} state={state} candidates={len(rec['candidates'])} kept={len(rec['kept'])} "
              f"worktrees={len(rec['worktrees'])} bytes_reclaimed={rec['bytes_reclaimed']}" + (f" reason={reason}" if reason else ""))
        if a.json:
            print(json.dumps(rec, sort_keys=True))
        return code

    if days > 0 and (time.time() - os.path.getmtime(ep)) < days * 86400:
        return finish("HOLD", f"retention raw_days={days:g}")
    if not os.path.isdir(root):
        return finish("NO-ROOT", "scratch_root missing")
    wts = rw.row_worktrees(root)
    if not raw and not wts:
        return finish("NO-RAW", "no raw declaration (keeper 1-day backstop applies)")
    pin = scratch_guard.pinned(flags, rid)
    if pin:
        print(f"RECLAIM-SKIPPED-SHARED {rid}: pinned by filing-no-reclaim.globs ({pin}); a successor will reuse {root}")
        return finish("SHARED", f"pinned by filing-no-reclaim.globs: {pin}")
    live = scratch_guard.live_overlap(flags, rid, root)
    if live:
        print(f"RECLAIM-SKIPPED-SHARED {rid}: live row {live} overlaps {root}")
        return finish("SHARED", f"live row {live} overlaps scratch_root")
    sh = shared_unfiled(flags, rid, root)
    if sh:
        return finish("SHARED", f"unfiled row {sh} names an overlapping scratch_root")
    probe = wg.gather_probe()
    busy = probe.busy(root) or open_fd_under(root)
    if busy:
        return finish("BUSY", busy)
    errors = 0
    if raw:
        cutoff, _src = start_cutoff(ep, mp)
        kept = keep_map(root, m, cutoff, [w.path for w in wts])
        kept_anc: dict = {}
        rr = os.path.realpath(root)
        for k, why in kept.items():
            d = os.path.dirname(k)
            while d.startswith(rr + "/"):
                kept_anc.setdefault(d, why)
                d = os.path.dirname(d)
        matches = []
        for g in raw:
            for p in sorted(glob.glob(os.path.join(root, g), recursive=True)):
                if p not in matches:
                    matches.append(p)
        # a match inside another match is covered by the outer one (if the outer is reaped)
        chosen = []
        for p in matches:
            why = keep_reason(p, kept, kept_anc, root)
            n = size_of(p)
            if why:
                rec["kept"].append({"path": p, "why": why})
                print(f"{tag} row={rid} path={p} bytes={n} verdict=KEEP-{why}")
                continue
            if any(p.startswith(c + "/") for c in chosen):
                continue
            chosen.append(p)
            rec["candidates"].append({"path": p, "bytes": n})
            print(f"{tag} row={rid} path={p} bytes={n} verdict=REAP")
        if a.apply:
            env = dict(os.environ, TRASH_ROOT=rw.trash_root())
            for c in rec["candidates"]:
                cp = subprocess.run(["bash", ws.GUARDED_RM, c["path"]], capture_output=True, text=True,
                                    timeout=3600, env=env)
                if cp.returncode != 0 or os.path.lexists(c["path"]):
                    c["error"] = (cp.stderr or cp.stdout).strip()[:300] or f"rc={cp.returncode}"
                    errors += 1
                    print(f"{tag} row={rid} path={c['path']} bytes={c['bytes']} verdict=ERROR {c['error']}")
                else:
                    rec["bytes_reclaimed"] += c["bytes"]
    else:
        print(f"{tag} row={rid} path={root} bytes=0 verdict=KEEP-no-raw-declaration")
    rec["worktrees"] = rw.release_row_worktrees(root, a.apply, salvage_dir=a.salvage_dir, probe=probe)
    for w in rec["worktrees"]:
        print(f"{tag} row={rid} path={w['path']} bytes=0 verdict=WORKTREE-{w['action']}"
              + (f" refused={w['refused']}" if w.get("refused") else "") + (f" error={w['error']}" if w.get("error") else ""))
        errors += 1 if w.get("error") else 0
    state = ("RECLAIMED" if a.apply else "DRYRUN") if not errors else "PARTIAL"
    if not raw:
        state = "NO-RAW+WORKTREES"
    return finish(state, None, 7 if errors else 0)


if __name__ == "__main__":
    sys.exit(main())
