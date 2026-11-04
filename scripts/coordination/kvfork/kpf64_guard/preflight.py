#!/usr/bin/env python3
"""Fail-closed validation of the frozen KPF-64 family parent/child schedule."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def _issue(kind: str, parent: str | None, reason: str, **extra: Any) -> dict[str, Any]:
    return {"type": kind, "parent": parent, "reason": reason, **extra}


def find_unreachable(manifest_path: Path, sessions_dir: Path) -> list[dict[str, Any]]:
    """Return structural or scheduling defects without mutating either input.

    Child ids are joined through the manifest's `parent` fields and each parent's session JSON.
    Non-replayable virtual anchors accept any nonnegative integer parent_turn, because
    replay_driver.run_virtual() dispatches their children in index order without indexing turns.
    Replayable parents additionally require parent_turn < the retained turn count.
    """
    manifest = json.loads(Path(manifest_path).read_text())
    rows = manifest.get("sessions")
    if not isinstance(rows, list):
        return [_issue("bad_manifest", None, "manifest sessions must be a list")]

    problems: list[dict[str, Any]] = []
    id_counts = Counter(r.get("id") for r in rows if isinstance(r, dict) and r.get("id") is not None)
    for sid, count in id_counts.items():
        if count > 1:
            problems.append(_issue("duplicate_manifest_id", None, "manifest session id is duplicated",
                                   child=sid, count=count))

    # IDs become filenames for parent session records. Keep them to one safe path
    # component before any filesystem access; this also rejects NULs and separators.
    for row in rows:
        if not isinstance(row, dict):
            continue
        sid = row.get("id")
        if isinstance(sid, str) and (not sid or sid in {".", ".."} or "\x00" in sid or
                                     Path(sid).name != sid or "/" in sid or "\\" in sid):
            problems.append(_issue("unsafe_session_id", None,
                                   "manifest session id must be a single safe filename component",
                                   child=sid))

    by_id = {r["id"]: r for r in rows if isinstance(r, dict) and isinstance(r.get("id"), str)}
    parents = [r for r in rows if isinstance(r, dict) and isinstance(r.get("id"), str) and not r.get("parent")]
    parent_ids = {r["id"] for r in parents}
    for row in rows:
        if not isinstance(row, dict) or not row.get("parent"):
            continue
        declared_parent = row.get("parent")
        if not isinstance(declared_parent, str) or declared_parent not in parent_ids:
            problems.append(_issue("orphan_manifest_parent", declared_parent if isinstance(declared_parent, str) else None,
                                   "manifest child parent must name a root parent session",
                                   child=row.get("id"), manifest_parent=declared_parent))
    for parent in parents:
        pid = parent["id"]
        if not pid or pid in {".", ".."} or "\x00" in pid or Path(pid).name != pid or "/" in pid or "\\" in pid:
            continue
        parent_file = Path(sessions_dir) / f"{pid}.json"
        try:
            session = json.loads(parent_file.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(_issue("missing_or_invalid_parent_session", pid,
                                   f"cannot read parent session {parent_file}: {exc}"))
            continue

        turns = session.get("turns")
        nturns = len(turns) if isinstance(turns, list) else None
        if nturns is None:
            problems.append(_issue("invalid_parent_turns", pid, "parent session turns must be a list"))

        actual_children = session.get("children") or []
        if not isinstance(actual_children, list):
            problems.append(_issue("invalid_children_list", pid, "parent session children must be a list"))
            continue

        actual_ids = [c.get("id") if isinstance(c, dict) else None for c in actual_children]
        actual_counts = Counter(cid for cid in actual_ids if isinstance(cid, str))
        for cid, count in actual_counts.items():
            if count > 1:
                problems.append(_issue("duplicate_child_id", pid, "parent session lists a child id more than once",
                                       child=cid, count=count))

        expected_rows = [r for r in rows if isinstance(r, dict) and r.get("parent") == pid]
        expected_ids = {r.get("id") for r in expected_rows if isinstance(r.get("id"), str)}
        actual_set = {cid for cid in actual_ids if isinstance(cid, str)}

        for child_row in expected_rows:
            cid = child_row.get("id")
            if cid not in actual_set:
                problems.append(_issue("manifest_child_missing_from_parent", pid,
                                       "manifest claims a child that the parent session does not list", child=cid))
        for child in actual_children:
            if not isinstance(child, dict):
                problems.append(_issue("invalid_child_record", pid, "parent children entries must be objects"))
                continue
            cid = child.get("id")
            if not isinstance(cid, str) or not cid:
                problems.append(_issue("invalid_child_id", pid, "child id must be a nonempty string", child=cid))
                continue
            row = by_id.get(cid)
            if row is None:
                problems.append(_issue("unknown_child", pid, "parent session lists a child absent from the manifest",
                                       child=cid))
            elif row.get("parent") != pid:
                problems.append(_issue("child_parent_mismatch", pid,
                                       "manifest child belongs to a different parent", child=cid,
                                       manifest_parent=row.get("parent")))

            idx = child.get("parent_turn")
            # bool is an int subclass in Python, but is not a valid turn index.
            if isinstance(idx, bool) or not isinstance(idx, int) or idx < 0:
                problems.append(_issue("invalid_parent_turn", pid,
                                       "child parent_turn must be a nonnegative integer", child=cid,
                                       parent_turn=idx))
            elif parent.get("replayable", session.get("replayable", True)) and nturns is not None and idx >= nturns:
                problems.append(_issue("unreachable_parent_turn", pid,
                                       "replayable parent has no retained turn at the frozen parent_turn; exact schedule unavailable",
                                       child=cid, parent_turn=idx, parent_retained_turns=nturns,
                                       child_requests=(row or {}).get("requests")))

        declared_count = parent.get("children")
        if isinstance(declared_count, int) and not isinstance(declared_count, bool) and declared_count != len(actual_children):
            problems.append(_issue("child_count_mismatch", pid,
                                   "manifest parent child count disagrees with parent session children list",
                                   manifest_count=declared_count, session_count=len(actual_children)))
        if expected_ids != actual_set:
            # Specific missing/unknown diagnostics above carry the IDs; this records set-level disagreement.
            problems.append(_issue("child_set_mismatch", pid,
                                   "manifest child rows and parent session child list differ",
                                   manifest_children=sorted(expected_ids), session_children=sorted(actual_set)))

    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--sessions", type=Path, required=True)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    problems = find_unreachable(args.manifest, args.sessions)
    report = {"status": "REJECTED" if problems else "PASS",
              "guard": "kpf64-family-parent-child-reachability", "problems": problems,
              "count": len(problems)}
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n")
    return 42 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
