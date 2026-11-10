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
