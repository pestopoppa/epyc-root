"""CH-18 fresh-production merge trial -> strict reader -> shared grade (VB-CH18-MERGE-TRIAL-WIRE).

Projects only a SEALED native record written by the trial at its own boundary
(``epyc.ch18_merge_trial.v1``). The pre-hook ``conflicts.json`` (kind experimental_merge_trial, no
schema/seal/tool/cleanup) is refused: it is a committed conclusion, never a reconstructed measurement.
The count is a diagnostic OBSERVATION of an unresolved merge; it is not a build, champion
reconciliation or promotion verdict. ``ClaimTuple.grade()`` is the only grader.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

ADAPTER_ID = "vidya.adapters.ch18_merge_trial/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "ch18-merge-trial"
SCHEMA = "epyc.ch18_merge_trial.v1"
FIELDS = frozenset({
    "schema", "kind", "production_base", "upstream_tip", "merge_strategy", "tool", "completed_at",
    "state", "conflict_count", "conflicting_paths", "conflicts_by_root", "cleanup", "limitation",
    "content_sha256"})
STATES = frozenset({"complete", "incomplete", "failed"})
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")


def _bad(where: str, why: str) -> None:
    raise ProjectionError(f"ch18-merge-trial {where}: {why}")


def seal(rec: dict) -> str:
    """Producer hash rule: sha256 of the sorted-key compact JSON body without content_sha256."""
    body = {k: v for k, v in rec.items() if k != "content_sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _validate(rec: Any, where: str) -> dict:
    if not isinstance(rec, dict):
        _bad(where, "record is not an object")
    if "schema" not in rec:
        _bad(where, "pre-hook record (no schema/seal/tool/cleanup): committed conclusion only, never a measurement")
    if rec["schema"] != SCHEMA or set(rec) != FIELDS:
        _bad(where, "schema or field set differs from epyc.ch18_merge_trial.v1")
    if rec["kind"] != "experimental_merge_trial" or rec["state"] not in STATES:
        _bad(where, "kind/state invalid")
    if not (isinstance(rec["content_sha256"], str) and SHA64.match(rec["content_sha256"])
            and rec["content_sha256"] == seal(rec)):
        _bad(where, "content seal does not re-derive")
    for key in ("production_base", "upstream_tip"):
        if not (isinstance(rec[key], str) and SHA40.match(rec[key])):
            _bad(where, f"{key} is not a full 40-hex commit")
    tool = rec["tool"]
    if not (isinstance(tool, dict) and set(tool) == {"name", "version"}
            and all(isinstance(v, str) and v for v in tool.values())):
        _bad(where, "tool identity (name, version) missing")
    if not (isinstance(rec["merge_strategy"], str) and rec["merge_strategy"]):
        _bad(where, "merge strategy missing")
    cleanup = rec["cleanup"]
    if not (isinstance(cleanup, dict) and set(cleanup) == {"worktree_removed", "merge_aborted"}
            and all(type(v) is bool for v in cleanup.values())):
        _bad(where, "cleanup record missing")
    try:
        datetime.datetime.strptime(rec["completed_at"], "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError) as exc:
        raise ProjectionError(f"ch18-merge-trial {where}: completed_at is not a UTC timestamp") from exc
    paths = rec["conflicting_paths"]
    if not (isinstance(paths, list) and all(isinstance(p, str) and p and not p.startswith("/") for p in paths)
            and len(set(paths)) == len(paths)):
        _bad(where, "conflicting_paths must be unique relative path strings")
    if type(rec["conflict_count"]) is not int or rec["conflict_count"] != len(paths):
        _bad(where, "conflict_count differs from the conflicting path list")
    roots: dict[str, int] = {}
    for p in paths:
        r = p.split("/", 1)[0]
        roots[r] = roots.get(r, 0) + 1
    if rec["conflicts_by_root"] != roots:
        _bad(where, "conflicts_by_root does not re-derive from the path list")
    if not (isinstance(rec["limitation"], str) and "not" in rec["limitation"]):
        _bad(where, "scope limitation missing")
    return rec


def native_rows(path: str | Path) -> tuple[dict, ...]:
    p = Path(path)
    if not p.is_file():
        return ()
    try:
        rec = json.loads(p.read_text())
    except (OSError, ValueError) as exc:
        raise ProjectionError(f"ch18-merge-trial {p}: unreadable JSON") from exc
    rec = _validate(rec, str(p))
    if rec["state"] != "complete":
        return ()                                    # incomplete/failed: no count claim, never a zero
    return ({"path": str(p), "record": rec},)


def units(path: Path) -> list[Path]:
    path = Path(path)
    if path.is_file():
        return [path]
    return sorted(path.glob("**/merge_trial*.json")) if path.is_dir() else []


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or set(native) != {"path", "record"}:
        raise ProjectionError("ch18-merge-trial native row missing")
    rec = _validate(native["record"], native["path"])
    k = rec["conflict_count"]
    claim = (f"Unresolved merge trial of upstream {rec['upstream_tip'][:12]} into production base "
             f"{rec['production_base'][:12]} ({rec['merge_strategy']}; {rec['tool']['name']} "
             f"{rec['tool']['version']}) left {k} conflicted paths; cleanup worktree_removed="
             f"{rec['cleanup']['worktree_removed']}, merge_aborted={rec['cleanup']['merge_aborted']}. "
             "A conflict inventory only: contents not reconciled, built, tested or promoted.")
    return ClaimTuple(
        measurement_id=(f"ch18-merge-trial:{rec['production_base'][:12]}:{rec['upstream_tip'][:12]}:"
                        f"{rec['content_sha256'][:16]}"),
        metric="ch18_merge_conflicted_paths", value=k, date=rec["completed_at"][:10],
        category="CANDIDATE", claim=claim, metric_direction="lower_better", protocol_id="",
        reps=1, reps_basis="one trial merge at the native boundary", unit="paths",
        attestation_path=native["path"], attestation_sha256=rec["content_sha256"],
        attestation_locator=f"ch18-merge-trial:{native['path']}", attestation_present=True,
        attestation_verified=True, source_kind=SOURCE_KIND,
        observation={"outcome_native": f"{k} conflicted paths"},
        extra={"adapter": ADAPTER_ID, "production_base": rec["production_base"],
               "upstream_tip": rec["upstream_tip"], "merge_strategy": rec["merge_strategy"],
               "tool": rec["tool"], "cleanup": rec["cleanup"], "conflicts_by_root": rec["conflicts_by_root"],
               "conflicting_paths": rec["conflicting_paths"], "limitation": rec["limitation"]})


def frames_for_path(path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY))
    return frames


__all__ = ["ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "SCHEMA", "seal", "native_rows", "project", "units",
           "frames_for_path"]
