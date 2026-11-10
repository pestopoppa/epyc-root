#!/usr/bin/env python3
"""Row-owned git worktrees: they live UNDER the row's scratch_root so they die with the row.

    row_worktree.py add --row <id> --repo <repo path> [--ref origin/main] [--name wt] [--flags DIR] [--tmp-root DIR]
        -> git -C <repo> worktree add --detach <scratch_root>/worktrees/<name> <ref>; prints the path.
           Refuses (exit 6) when the manifest has no absolute scratch_root under the tmp root, refuses (exit 3) to
           overwrite an existing path.
    row_worktree.py release --row <id> [--apply] [--flags DIR] [--salvage-dir DIR] [--json]
        -> release_row_worktrees(): every registered linked worktree (worktree_gate.list_worktrees over
           worktree_gate.DEFAULT_REPOS) whose realpath is under scratch_root goes through
           worktree_salvage.retire() (clean+landed -> removed; dirty/unlanded -> salvaged, trashed via
           guarded_rm, deregistered; refusals are reported, never forced). Dry-run unless --apply.

Never `--force`, never `git worktree prune`. reclaim_row.py imports release_row_worktrees() from here.
Tmp root: --tmp-root, else $RECLAIM_TMP_ROOT, else /mnt/raid0/llm/tmp. Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(os.path.dirname(HERE))
for _p in (os.path.join(SCRIPTS, "system"), os.path.join(SCRIPTS, "coordination", "churn"),
           os.path.join(SCRIPTS, "coordination")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import worktree_gate as wg  # noqa: E402
import worktree_salvage as ws  # noqa: E402

DEFAULT_FLAGS = os.environ.get("ROWFLOW_FLAGS", "/mnt/raid0/llm/tmp/compute-flags")
DEFAULT_TRASH = "/mnt/raid0/llm/.trash-reap"
# same protected first-level names as the keeper's valid_root (ws58-calendar-keeper-v13.sh PROTECT)
PROTECT = {"compute-flags", "disk-audit-20261028", "ws58-loop-audit"}


def tmp_root(override: str | None = None) -> str:
    return os.path.realpath(override or os.environ.get("RECLAIM_TMP_ROOT") or "/mnt/raid0/llm/tmp")


def trash_root() -> str:
    return os.environ.get("RECLAIM_TRASH_ROOT") or DEFAULT_TRASH


def scratch_root_error(sr, tmp: str | None = None) -> str | None:
    """None when `sr` is an absolute dir path strictly below the tmp root (and not a protected first-level dir)."""
    if not isinstance(sr, str) or not sr or not os.path.isabs(sr):
        return "no scratch_root"
    t = tmp_root(tmp)
    n = os.path.normpath(sr)
    if ".." in sr.split("/"):
        return "scratch_root has '..'"
    if not n.startswith(t + "/"):
        return f"scratch_root not under {t}/"
    if n[len(t) + 1:].split("/")[0] in PROTECT:
        return "scratch_root protected"
    return None


def load_manifest(flags: str, rid: str):
    import file_result
    return file_result.load_manifest(flags, rid)


def _under(path: str, root: str) -> bool:
    rp, rr = os.path.realpath(path), os.path.realpath(root)
    return rp != rr and rp.startswith(rr + "/")


def row_worktrees(scratch_root: str, repos=None) -> list:
    out = []
    for repo in (repos if repos is not None else wg.DEFAULT_REPOS):
        if not os.path.isdir(repo):
            continue
        try:
            wts = wg.list_worktrees(repo)
        except (RuntimeError, OSError, subprocess.TimeoutExpired):
            continue
        out += [w for w in wts if _under(w.path, scratch_root)]
    return out


def release_row_worktrees(scratch_root: str, apply: bool = False, *, salvage_dir: str = ws.DEFAULT_SALVAGE_DIR,
                          probe=None, base: str = wg.DEFAULT_BASE, trash: str | None = None, repos=None) -> list:
    """Retire every registered linked worktree under scratch_root. Returns worktree_salvage.retire() dicts."""
    wts = row_worktrees(scratch_root, repos)
    if not wts:
        return []
    probe = probe if probe is not None else wg.gather_probe()
    return [ws.retire(w.path, apply=apply, salvage_dir=salvage_dir, probe=probe, base=base,
                      trash_root=trash or trash_root()) for w in wts]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("add")
    a1.add_argument("--row", required=True)
    a1.add_argument("--repo", required=True)
    a1.add_argument("--ref", default="origin/main")
    a1.add_argument("--name", default="wt")
    a1.add_argument("--flags", default=DEFAULT_FLAGS)
    a1.add_argument("--tmp-root")
    a2 = sub.add_parser("release")
    a2.add_argument("--row", required=True)
    a2.add_argument("--apply", action="store_true")
    a2.add_argument("--flags", default=DEFAULT_FLAGS)
    a2.add_argument("--tmp-root")
    a2.add_argument("--salvage-dir", default=ws.DEFAULT_SALVAGE_DIR)
    a2.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    _mp, m = load_manifest(a.flags, a.row)
    if not m:
        print(f"ERROR {a.row}: no manifest in {a.flags}/ready/", file=sys.stderr)
        return 2
    sr = m.get("scratch_root")
    err = scratch_root_error(sr, a.tmp_root)
    if err:
        print(f"REFUSED {a.row}: {err}", file=sys.stderr)
        return 6
    sr = os.path.normpath(sr)
    if a.cmd == "add":
        name = a.name
        if not name or "/" in name or name in (".", ".."):
            print(f"REFUSED {a.row}: bad --name {name!r}", file=sys.stderr)
            return 6
        if not os.path.isdir(sr):
            print(f"REFUSED {a.row}: scratch_root {sr} missing", file=sys.stderr)
            return 6
        dest = os.path.join(sr, "worktrees", name)
        if os.path.lexists(dest):
            print(f"REFUSED {a.row}: {dest} exists (never overwritten)", file=sys.stderr)
            return 3
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        cp = subprocess.run(["git", "-C", a.repo, "worktree", "add", "--detach", dest, a.ref],
                            capture_output=True, text=True, timeout=1800)
        if cp.returncode != 0:
            print(f"ERROR {a.row}: git worktree add failed: {cp.stderr.strip()[:300]}", file=sys.stderr)
            return 1
        print(dest)
        return 0
    res = release_row_worktrees(sr, a.apply, salvage_dir=a.salvage_dir)
    if a.json:
        print(json.dumps(res, indent=1, sort_keys=True, default=str))
    else:
        for r in res:
            print(f"WORKTREE{'' if a.apply else '-DRYRUN'} row={a.row} path={r['path']} action={r['action']} "
                  f"refused={r.get('refused')} error={r.get('error')}")
        print(f"SUMMARY row={a.row} worktrees={len(res)} apply={a.apply}")
    return 1 if any(r.get("error") for r in res) else 0


if __name__ == "__main__":
    sys.exit(main())
