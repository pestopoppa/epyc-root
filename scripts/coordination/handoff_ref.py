"""handoff_ref - the ONE parser of a row's handoff reference (pipeline audit 2026-11-10 #8).

A row names its handoff as ``x.md``, ``handoffs/<state>/x.md``, or either with ``:TASK`` (``handoff_task``; TASK is a
row/box id or a 1-based line number). Every consumer (publish, filing receipts, the pipeline dashboard, backlog_gen,
handoff_sessions) reduces it here, so a new consumer cannot mis-key it. Stdlib only; installed to bin/, bin/rowflow/
and bin/churn/ (scripts/coordination/INSTALL.manifest).

    parse(ref)      -> Ref(state, file, task)   state is None unless the ref spells handoffs/<state>/
    file_of(ref)    -> "x.md" | None            the bare file (the graph node's ``handoff``)
    key(ref)        -> "x.md:TASK" | "x.md" | None   the canonical form stored in manifests
    repo_path(ref)  -> "handoffs/<state>/x.md" | None   a bare file defaults to handoffs/active/
"""
from __future__ import annotations

from typing import NamedTuple

STATES = ("active", "blocked", "completed", "archived")


class Ref(NamedTuple):
    state: str | None
    file: str | None
    task: str | None


def parse(ref) -> Ref:
    if not isinstance(ref, str):
        return Ref(None, None, None)
    path, _, task = ref.strip().partition(":")
    parts = [p for p in path.strip().strip("/").split("/") if p]
    base = parts[-1] if parts else ""
    f = base if base.endswith(".md") else None
    state = parts[-2] if (f and len(parts) >= 3 and parts[-3] == "handoffs" and parts[-2] in STATES) else None
    return Ref(state, f, task.strip() or None)


def file_of(ref) -> str | None:
    return parse(ref).file


def key(ref) -> str | None:
    r = parse(ref)
    if not r.file:
        return None
    return f"{r.file}:{r.task}" if r.task else r.file


def repo_path(ref, default_state: str = "active") -> str | None:
    """Repo-relative path of the handoff file. A ref that already names a directory is kept as written (a receipt may
    point at any repo-relative .md); a bare ``x.md`` lives under handoffs/<default_state>/."""
    if not isinstance(ref, str):
        return None
    path = ref.strip().partition(":")[0].strip()
    if not path.endswith(".md"):
        return None
    return path if "/" in path else f"handoffs/{default_state}/{path}"


# ------------------------------------------------------------------ handoff standard C4: box moves (repointing)
# Every whole-track split / box move writes one JSONL line per moved box to handoffs/active/.moves.jsonl:
#   {"box_id", "text_sha", "from": "a.md", "to": "b.md", "at"}
# Readers resolve a row's handoff_task through it, so a row published before a split still finds its box.
MOVES_REL = "handoffs/active/.moves.jsonl"


def load_moves(root) -> list:
    import json
    import os
    p = os.path.join(str(root), MOVES_REL)
    out = []
    try:
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if isinstance(d, dict) and d.get("to"):
                    out.append(d)
    except OSError:
        pass
    return out


def moved_file(ref, root, sha=None, moves=None):
    """The file a ref's box lives in NOW: follow .moves.jsonl by (text_sha) first, then by box id (the ref's TASK),
    from the ref's file; returns the ref's own file when nothing moved it. Chains are followed (a.md -> b.md -> c.md)."""
    r = parse(ref)
    f, task = r.file, r.task
    moves = load_moves(root) if moves is None else moves
    seen = set()
    while f and f not in seen:
        seen.add(f)
        hit = None
        for m in moves:
            if m.get("from") != f:
                continue
            if (sha and m.get("text_sha") == sha) or (task and not str(task).isdigit() and m.get("box_id") == task):
                hit = m
        if not hit:
            break
        f = hit["to"]
    return f


def resolve(ref, root, sha=None) -> str | None:
    """`key(ref)` with its file repointed through the moves log (C4); None when the ref names no file."""
    k = key(ref)
    if not k:
        return None
    f = moved_file(ref, root, sha)
    t = parse(ref).task
    return f"{f}:{t}" if t else f


DEFAULT_ROOT_ENV = ("ROWFLOW_REPO", "EPYC_ROOT")
DEFAULT_ROOT = "/mnt/raid0/llm/views/epyc-root-main"   # tracks origin/main (publish_row.REPO)


def default_root() -> str:
    import os
    for k in DEFAULT_ROOT_ENV:
        v = os.environ.get(k)
        if v:
            return v
    return DEFAULT_ROOT


def repoint(ref, root=None, sha=None, moves=None):
    """The ref as written, with only its file name replaced when .moves.jsonl moved its box (C4 gap 4: every
    handoff_task consumer - rowflow owner routing / legacy migration / unfiled-ack filing, backlog_gen, filing - routes
    a moved box to its NEW file). Keeps any `handoffs/<state>/` prefix and the `:TASK` suffix; never raises: a
    non-string, a ref without a .md file, or an unreadable moves log returns the ref unchanged."""
    if not isinstance(ref, str) or not parse(ref).file:
        return ref
    try:
        new = moved_file(ref, root if root is not None else default_root(), sha, moves)
    except Exception:  # noqa: BLE001 - a routing helper must never break its caller
        return ref
    old = parse(ref).file
    if not new or new == old:
        return ref
    path, sep, task = ref.strip().partition(":")
    head = path[: len(path) - len(old)] if path.endswith(old) else ""
    return f"{head}{new}{sep}{task}"
