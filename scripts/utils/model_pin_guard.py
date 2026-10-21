#!/usr/bin/env python3
"""model_pin_guard.py — SEC-ART-7 re-pull drift check (handoffs/active/model-artifact-integrity.md).

A registered artifact is one whose model row in the orchestrator registry carries the SEC-ART-1 pins:
`roles.<role>.model.{path, hf_repo, hf_revision, sha256}` (hf_revision = 40-hex commit, sha256 = the GGUF's LFS
oid). Re-pulling such a repo must not silently change what we serve (intake-2191#record: a re-uploaded repo is the
supply-chain move; intake-2197#record: relays repackage trusted weights). `scripts/utils/safe_download.py` calls
`evaluate()` BEFORE it runs the download and REFUSES (exit 2) when:

  commit drift    the commit the ref resolves to differs from a registered `hf_revision` for that repo;
  oid drift       a registered `sha256` is not the LFS oid of any file at the resolved commit, or the file with
                  the registered file name now carries a different oid (registry oid vs upstream oid reported);
  unverifiable    the repo has registry pins but the ref could not be resolved (--no-resolve), or a download
                  without --hf-repo would write into a directory that holds a registered artifact.

The refusal is lifted only by a REVIEW RECORD (`--review-record FILE`, JSON) that matches this exact drift:
`{"schema": "model-review-record/1", "hf_repo": ..., "to_revision": <the resolved sha>, "decision": "approve",
"reviewer": ..., "reviewed_at": ...}`. `to_revision` must equal the sha this run resolved, so an old approval
cannot bless a later upstream change. SEC-ART-3 owns the full review record (provenance, base-model diff, flag
audit) and its stack-change gate; this module reads only the fields above and ignores the rest, so SEC-ART-3 can
extend the record without changing the guard. The guard is a check on an HONEST author's mistakes and on a
repo that moved under us (AK-gate threat model); a session able to forge a review file is SEC-ART-3's problem.

Registry with no pins for a repo (SEC-ART-1.1 backfill pending) means nothing is registered, so nothing can
drift: the run proceeds and says so. A registry file that exists but cannot be parsed REFUSES (a corrupt
registry must not silently disable the check); a missing registry file warns, or refuses with
--require-registry / SAFE_DOWNLOAD_REQUIRE_REGISTRY=1.

Pure functions plus one loader; the HTTP tree read is injected (`fetch_tree`) so tests use a mocked HF tree-API
response. Tests: tests/test_model_pin_guard.py
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

DEFAULT_REGISTRY = os.environ.get(
    "SAFE_DOWNLOAD_REGISTRY", "/mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml")
REVIEW_SCHEMA = "model-review-record/1"


class RegistryError(RuntimeError):
    """The registry exists but cannot be read as a registry (refuse, do not skip)."""


@dataclass(frozen=True)
class Pin:
    role: str
    path: str
    hf_repo: str
    hf_revision: str | None
    sha256: str | None


@dataclass
class Verdict:
    """What evaluate() decided. `refuse` is the only field callers act on; the rest is for the message/ledger."""
    refuse: bool = False
    drifts: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    review_used: dict[str, Any] | None = None


def load_pins(registry_path: str | os.PathLike[str], *, require: bool = False) -> list[Pin] | None:
    """Pins for every `roles.<role>.model` carrying an `hf_repo`. None = registry file absent (and not required)."""
    p = Path(registry_path)
    if not p.exists():
        if require:
            raise RegistryError(f"registry {p} does not exist (--require-registry)")
        return None
    try:
        import yaml  # noqa: PLC0415 - only the registry read needs it
        loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
        data = yaml.load(p.read_text(), Loader=loader)  # noqa: S506 - safe loader
    except Exception as exc:  # noqa: BLE001
        raise RegistryError(f"cannot parse registry {p}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("roles"), dict):
        raise RegistryError(f"registry {p} has no `roles` mapping")
    pins: list[Pin] = []
    for role, cfg in sorted(data["roles"].items()):
        model = cfg.get("model") if isinstance(cfg, dict) else None
        if not isinstance(model, dict) or not model.get("hf_repo"):
            continue
        pins.append(Pin(
            role=str(role),
            path=str(model.get("path") or model.get("full_path") or ""),
            hf_repo=str(model["hf_repo"]),
            hf_revision=str(model["hf_revision"]) if model.get("hf_revision") else None,
            sha256=str(model["sha256"]).lower() if model.get("sha256") else None,
        ))
    return pins


def pins_for_repo(pins: list[Pin], repo: str) -> list[Pin]:
    return [p for p in pins if p.hf_repo.lower() == repo.lower()]


def registered_under(pins: list[Pin], dest: str | os.PathLike[str]) -> list[Pin]:
    """Pins whose registered file path lies inside `dest` (the artifact a no-repo download could overwrite)."""
    base = os.path.realpath(dest)
    out = []
    for p in pins:
        if p.path and os.path.realpath(p.path).startswith(base.rstrip("/") + "/"):
            out.append(p)
    return out


def load_review(path: str | os.PathLike[str] | None) -> dict[str, Any] | None:
    if not path:
        return None
    try:
        rec = json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise ValueError(f"review record {path} unreadable: {exc}") from exc
    if not isinstance(rec, dict):
        raise ValueError(f"review record {path} is not a JSON object")
    return rec


def review_problem(review: dict[str, Any] | None, repo: str | None, resolved_sha: str | None) -> str | None:
    """None when `review` approves this exact repo+commit; else why not. repo/sha None = generic approval only."""
    if review is None:
        return "no review record passed"
    if review.get("schema") != REVIEW_SCHEMA:
        return f"review record schema is {review.get('schema')!r}, need {REVIEW_SCHEMA!r}"
    if review.get("decision") != "approve":
        return f"review decision is {review.get('decision')!r}, need 'approve'"
    if not str(review.get("reviewer") or "").strip():
        return "review record has no reviewer"
    if repo is not None and str(review.get("hf_repo", "")).lower() != repo.lower():
        return f"review is for {review.get('hf_repo')!r}, not {repo!r}"
    if resolved_sha is not None and review.get("to_revision") != resolved_sha:
        return f"review approves revision {review.get('to_revision')!r}, this run resolved {resolved_sha}"
    return None


def _tree_by_oid(tree: list[dict[str, Any]]) -> tuple[dict[str, dict], dict[str, list[dict]]]:
    by_oid: dict[str, dict] = {}
    by_name: dict[str, list[dict]] = {}
    for e in tree:
        if e.get("type") != "file":
            continue
        oid = (e.get("lfs") or {}).get("oid")
        if oid:
            by_oid[str(oid).lower()] = e
        by_name.setdefault(e["path"].rsplit("/", 1)[-1], []).append(e)
    return by_oid, by_name


def find_drift(repo_pins: list[Pin], resolved_sha: str, tree: list[dict[str, Any]] | None) -> list[str]:
    """Differences between the registry pins for one repo and the commit this run would fetch."""
    drifts: list[str] = []
    by_oid, by_name = _tree_by_oid(tree or [])
    for pin in repo_pins:
        who = f"role {pin.role} ({pin.path.rsplit('/', 1)[-1] or pin.hf_repo})"
        if pin.hf_revision and pin.hf_revision != resolved_sha:
            drifts.append(f"commit drift: {who} is pinned at {pin.hf_revision}, {pin.hf_repo} now resolves to {resolved_sha}")
        if not pin.sha256 or tree is None:
            continue
        if pin.sha256 in by_oid:
            continue
        same_name = by_name.get(pin.path.rsplit("/", 1)[-1], [])
        if same_name:
            upstream = ", ".join(sorted({str((e.get("lfs") or {}).get("oid") or e.get("oid")) for e in same_name}))
            drifts.append(f"oid drift: {who} registry sha256 {pin.sha256} but upstream file now has {upstream}")
        else:
            drifts.append(f"oid drift: {who} registry sha256 {pin.sha256} matches no LFS file at {resolved_sha}")
    return drifts


def evaluate(
    *,
    repo: str | None,
    resolved_sha: str | None,
    dest: str,
    pins: list[Pin] | None,
    fetch_tree: Callable[[str, str], list[dict[str, Any]]],
    review: dict[str, Any] | None = None,
) -> Verdict:
    """Decide whether this download may proceed. `pins is None` = registry absent (caller already warned)."""
    v = Verdict()
    if pins is None:
        v.notes.append("registry not found: drift check skipped")
        return v
    if repo is None:
        held = registered_under(pins, dest)
        if held:
            v.drifts.append(
                "unverifiable: --dest holds registered artifact(s) "
                + ", ".join(sorted({p.path.rsplit('/', 1)[-1] for p in held}))
                + "; pass --hf-repo ORG/REPO so the re-pull can be compared with the registry pin")
        return _decide(v, review, None, None)
    repo_pins = pins_for_repo(pins, repo)
    if not repo_pins:
        v.notes.append(f"no registry pins for {repo}: nothing registered, drift check not applicable")
        return v
    if resolved_sha is None:
        v.drifts.append(f"unverifiable: {repo} has registry pins but its revision was not resolved (--no-resolve)")
        return _decide(v, review, repo, None)
    tree = None
    if any(p.sha256 for p in repo_pins):
        try:
            tree = fetch_tree(repo, resolved_sha)
        except Exception as exc:  # noqa: BLE001 - cannot compare oids: that is a refusal, not a pass
            v.drifts.append(f"unverifiable: tree API read for {repo}@{resolved_sha} failed ({exc})")
            return _decide(v, review, repo, resolved_sha)
    v.drifts.extend(find_drift(repo_pins, resolved_sha, tree))
    if not v.drifts:
        v.notes.append(f"{repo}@{resolved_sha}: matches {len(repo_pins)} registry pin(s)")
    return _decide(v, review, repo, resolved_sha)


def _decide(v: Verdict, review: dict[str, Any] | None, repo: str | None, sha: str | None) -> Verdict:
    if not v.drifts:
        return v
    problem = review_problem(review, repo, sha)
    if problem is None:
        v.review_used = review
        v.notes.append(f"drift accepted by review record (reviewer {review.get('reviewer')})")
        return v
    v.refuse = True
    v.notes.append(f"not lifted: {problem}")
    return v
