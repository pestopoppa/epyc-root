#!/usr/bin/env python3
"""promote_lane.py — P2-8 merge cadence: one lane onto main, one promotion at a time.

Owning handoff: handoffs/active/loop-owned-fleet-implementation.md (P2-8)
Plan of record: docs/design/loop-owned-fleet.html  (red-team finding R17)

WHAT THIS IS
------------
`worker_runner.py` finishes a batch and proposes a PROMOTION ROW (task ids, lane
worktree, commit range). This is the thing that consumes it: it takes the lane's
net diff over that range and lands it on the target branch — serialized, gated,
and pathspec-limited — or it REFUSES and says exactly which condition failed.

THREE MEASURED FAILURE CLASSES SHAPE EVERY DECISION HERE
--------------------------------------------------------
1. **Interleaved promotions.** Reconciliation went stale eight times against a
   five-writer tree and a fleet-wide freeze was needed to land one merge. So a
   promotion runs under a NAMED, O_EXCL lock keyed on the git COMMON DIR — every
   worktree of one clone contends for the same lock — and a second promotion is
   REFUSED with the holder named, never queued behind a silent wait. The lock is
   `serialized_push.acquire/release`: the same primitive as the push lock and the
   wrap-up lease, under the lock name `promote`. It is deliberately not a fourth
   implementation of O_EXCL-with-reclaim-rules; the reclaim rules are the hard
   part and there must be exactly one of them.

2. **Pathspec-less commits sweeping other sessions' work.** `git commit` with no
   pathspec commits whatever is staged, including hunks another session left in a
   shared file. So: `git apply` the lane patch, `git add -- <explicit paths>`,
   `git commit -m … -- <explicit paths>`. There is no code path in this file that
   runs `git add -A`, `git add .`, or a bare `git commit`; a test greps for that.
   Before applying anything, the target worktree is checked for UNCOMMITTED
   changes in any path this promotion touches — if another session is mid-edit in
   one of them, we refuse rather than land on top of it.

3. **Auto-resolved conflicts.** A conflict means the lane's premise about the
   tree is stale. This tool never resolves one: `git apply --check` runs first,
   and on failure the promotion is refused with the rejected paths named and the
   working tree untouched — no merge started, no `-X theirs`, no index left dirty.

GATES, IN ORDER (all refuse BEFORE anything is written)
--------------------------------------------------------
  * lane and target must be worktrees of the SAME repository (device+inode of the
    git common dir) — promoting across clones is not a merge.
  * `serialized_push.preflight` on the target: mid-merge/rebase/cherry-pick,
    detached HEAD, unmerged index. Upstream conditions are recorded as WARNINGS,
    not refusals: this lands a local commit and never pushes — publishing stays
    `serialized_push --push`'s job, and requiring a fetched upstream here would
    refuse valid promotions on an offline host.
  * containment: `base` must be an ancestor of the target HEAD (a lane forked
    from a tip main no longer has is exactly the stale-reconciliation shape), and
    `head` already contained means "already promoted" — a no-op, not an error.
  * `merge_gate.py`: the human-only path list. Gated ⇒ refuse, with the
    ready-to-relay token block printed.
  * D9 loop plane: any path under `scripts/coordination/**` requires
    `--operator-ack <ref>` naming the operator's acknowledgement. "No autonomous
    merges to the loop plane" is a ratified decision, so it is a gate, not a note.

DRY RUN IS THE DEFAULT. `--apply` writes.

Exit codes:
    0   promoted, dry-run plan produced, or already promoted (no-op)
    2   REFUSED — containment, dirty target, cross-repo, preflight
    3   REFUSED — the promote lock is held by someone else
    4   REFUSED — conflict; the patch does not apply cleanly
    5   REFUSED — merge gate (human-only path, or D9 loop plane without an ack)
    64  usage

Usage:
    promote_lane.py promote --agent mainB --task-id RTG-52 \\
        --lane-worktree /mnt/raid0/llm/worktrees/pool/lane0 --range abc123..def456
    promote_lane.py promote --agent mainB --request-json /path/to/promotion.json --apply
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.coordination import merge_gate, serialized_push  # noqa: E402
from scripts.coordination.serialized_push import (  # noqa: E402
    LockHeldError,
    PreflightError,
    SerializedPushError,
    acquire,
    release,
    repo_key,
)

LOCK_NAME = "promote"
DEFAULT_TARGET = "/workspace"

# D9: the loop plane. Changes here land as PROPOSED commits with operator ack.
LOOP_PLANE_PREFIXES = ("scripts/coordination/",)

# Preflight conditions that are about PUBLISHING, not about landing a local
# commit. Recorded as warnings so the operator sees them; not refusals, because
# this tool never pushes.
_PUBLISH_ONLY_CONDITIONS = {"no-upstream", "unknown-remote", "upstream-ref-not-fetched"}

EX_REFUSED = 2
EX_LOCK_HELD = 3
EX_CONFLICT = 4
EX_GATED = 5
EX_USAGE = 64


class PromotionRefused(RuntimeError):
    def __init__(self, message: str, condition: str, code: int = EX_REFUSED,
                 detail: Optional[dict] = None):
        super().__init__(message)
        self.condition = condition
        self.code = code
        self.detail = detail or {}


def _git(repo: Path, *args: str, check: bool = True,
         stdin: Optional[str] = None) -> subprocess.CompletedProcess:
    proc = subprocess.run(["git", "-C", str(repo), *args], input=stdin,
                          capture_output=True, text=True, timeout=300)
    if check and proc.returncode != 0:
        raise PromotionRefused(
            f"git {' '.join(args)} failed in {repo}: "
            f"{(proc.stderr or proc.stdout).strip()[:400]}",
            condition="git-command-failed")
    return proc


def _ok(repo: Path, *args: str) -> bool:
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, timeout=120).returncode == 0


# ------------------------------------------------------------------ request


def load_request(args: argparse.Namespace) -> dict:
    """A promotion request: task_id(s), lane worktree, commit range.

    Accepts the runner's own `promotion` block verbatim (`task_ids`, `worktree`,
    `commit_range`) so the row emitted by `worker_runner.promotion_row()` can be
    piped straight in without a translation layer nobody maintains.
    """
    req: dict[str, Any] = {}
    if args.request_json:
        raw = (sys.stdin.read() if args.request_json == "-"
               else Path(args.request_json).read_text(encoding="utf-8"))
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise PromotionRefused(f"request is not valid JSON: {exc}",
                                   condition="bad-request", code=EX_USAGE) from exc
        obj = obj.get("promotion", obj) if isinstance(obj, dict) else obj
        if not isinstance(obj, dict):
            raise PromotionRefused("request JSON is not an object",
                                   condition="bad-request", code=EX_USAGE)
        req = {
            "task_ids": obj.get("task_ids") or ([obj["task_id"]] if obj.get("task_id") else []),
            "lane_worktree": obj.get("lane_worktree") or obj.get("worktree"),
            "commit_range": obj.get("commit_range"),
        }
    if args.task_id:
        req["task_ids"] = [args.task_id]
    if args.lane_worktree:
        req["lane_worktree"] = args.lane_worktree
    if args.range:
        req["commit_range"] = args.range

    missing = [k for k in ("task_ids", "lane_worktree", "commit_range") if not req.get(k)]
    if missing:
        raise PromotionRefused(
            f"promotion request is missing {missing} — a promotion names WHICH rows, from "
            f"WHICH worktree, over WHICH commits; none of the three is inferable",
            condition="incomplete-request", code=EX_USAGE)
    return req


# ------------------------------------------------------------------- checks


def same_repository(lane: Path, target: Path) -> tuple[bool, str, str]:
    """Identity by device+inode of the git COMMON dir (serialized_push.repo_key).

    Path comparison would answer wrongly here: `/workspace/repos/<name>` is a
    symlink farm over `/mnt/raid0/llm/<name>`, and the fleet reaches the same
    clone by several names.
    """
    lk, tk = repo_key(lane), repo_key(target)
    return lk == tk, lk, tk


def resolve_range(lane: Path, commit_range: str) -> tuple[str, str]:
    if ".." in commit_range:
        base, head = commit_range.split("..", 1)
        base, head = base.strip(), (head.strip() or "HEAD")
    else:
        base, head = f"{commit_range}^", commit_range
    for ref, label in ((base, "base"), (head, "head")):
        if not _ok(lane, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"):
            raise PromotionRefused(
                f"commit range {commit_range!r}: {label} ref {ref!r} does not resolve in "
                f"{lane}", condition="unresolvable-range")
    return (_git(lane, "rev-parse", base).stdout.strip(),
            _git(lane, "rev-parse", head).stdout.strip())


def check_containment(target: Path, base: str, head: str) -> dict:
    """Is this lane actually promotable onto the target tip, as-is?

    Two questions, deliberately separate:
      * head already an ancestor of the target HEAD ⇒ ALREADY PROMOTED. Not an
        error: a retried promotion must be a no-op, not a duplicate commit.
      * base NOT an ancestor of the target HEAD ⇒ the lane forked from something
        the target no longer contains, or was never rebased onto it. That is the
        stale-reconciliation shape; the fix is a rebase in the lane, by its owner,
        and this tool refuses rather than guessing at the resolution.
    """
    target_head = _git(target, "rev-parse", "HEAD").stdout.strip()
    already = _ok(target, "merge-base", "--is-ancestor", head, target_head)
    base_contained = _ok(target, "merge-base", "--is-ancestor", base, target_head)
    return {"target_head": target_head, "already_promoted": already,
            "base_contained": base_contained}


def changed_paths(lane: Path, base: str, head: str) -> list[str]:
    """The lane's net changed paths.

    `--no-renames` on purpose: a rename listed only under its new name would give
    the commit pathspec a hole exactly the size of the deleted file, and the
    promotion would land the add without the delete.
    """
    out = _git(lane, "diff", "--no-renames", "--name-only", f"{base}..{head}").stdout
    return sorted({p for p in out.splitlines() if p.strip()})


def dirty_overlap(target: Path, paths: list[str]) -> list[str]:
    """Paths this promotion touches that the target worktree has uncommitted.

    This is the commit-sweep hazard checked BEFORE it can happen: landing a patch
    over a path another session is mid-edit in either fails to apply or silently
    entangles their work with ours. Either way the answer is refuse.
    """
    if not paths:
        return []
    proc = _git(target, "status", "--porcelain", "--", *paths, check=False)
    return sorted({ln[3:].strip().split(" -> ")[-1]
                   for ln in proc.stdout.splitlines() if ln.strip()})


def gate_check(paths: list[str], branch: str, repo_key_name: str,
               operator_ack: Optional[str]) -> dict:
    """merge_gate.py (human-only list) plus the D9 loop-plane gate."""
    result: dict[str, Any] = {"verdict": "autonomous", "hits": [], "loop_plane": [],
                              "token_block": None}
    try:
        gate = merge_gate.load_gate_list()
    except RuntimeError as exc:
        raise PromotionRefused(
            f"the merge gate list is unusable ({exc}) — an unverifiable trust boundary "
            f"cannot authorise a promotion", condition="gate-unusable", code=EX_GATED)
    classified = merge_gate.classify(repo_key_name, paths, branch, gate)
    result["hits"] = classified["hits"]
    if classified["verdict"] == "gated":
        result["verdict"] = "gated"
        result["token_block"] = merge_gate.token_block(classified, repo_key_name)

    loop = sorted(p for p in paths if p.startswith(LOOP_PLANE_PREFIXES))
    result["loop_plane"] = loop
    if loop and not operator_ack:
        result["verdict"] = "gated"
        result["loop_plane_gated"] = True
    result["operator_ack"] = operator_ack
    return result


# ------------------------------------------------------------------ the work


def build_patch(lane: Path, base: str, head: str, paths: list[str]) -> str:
    return _git(lane, "diff", "--no-renames", "--binary", f"{base}..{head}",
                "--", *paths).stdout


def apply_patch(target: Path, patch: str, *, check_only: bool) -> subprocess.CompletedProcess:
    args = ["apply", "--check"] if check_only else ["apply"]
    return _git(target, *args, "-", stdin=patch, check=False)


def commit_paths(target: Path, paths: list[str], message: str) -> str:
    """Stage and commit by EXPLICIT PATHSPEC. Never `-A`, never a bare commit.

    `git add -- <paths>` stages content and removals for exactly those paths;
    `git commit -- <paths>` builds the commit from HEAD plus those paths' working
    -tree state, so anything else another session left staged or modified in this
    shared tree is untouched and uncommitted. That is the whole point.
    """
    _git(target, "add", "--", *paths)
    _git(target, "commit", "-m", message, "--", *paths)
    return _git(target, "rev-parse", "HEAD").stdout.strip()


# --------------------------------------------------------------- the driver


def promote(req: dict, *, target: Path, agent: str, lock_dir: Path, apply: bool,
            operator_ack: Optional[str], dwell_s: float = 0.0,
            repo_key_name: str = "epyc-root") -> dict:
    """One promotion, under the lock. Returns the receipt; raises PromotionRefused."""
    lane = Path(req["lane_worktree"]).resolve()
    if not lane.exists():
        raise PromotionRefused(f"lane worktree {lane} does not exist",
                               condition="missing-lane")
    if not _ok(lane, "rev-parse", "--git-dir"):
        raise PromotionRefused(f"{lane} is not a git worktree", condition="missing-lane")
    if not _ok(target, "rev-parse", "--git-dir"):
        raise PromotionRefused(f"{target} is not a git worktree", condition="missing-target")

    # Every path below (diff --name-only, git apply, the commit pathspec) is
    # repo-root-relative, so both ends must BE the root. A promotion requested
    # from inside a subdirectory would otherwise apply the patch one level down.
    lane = Path(_git(lane, "rev-parse", "--show-toplevel").stdout.strip())
    target = Path(_git(target, "rev-parse", "--show-toplevel").stdout.strip())

    same, lane_key, target_key = same_repository(lane, target)
    if not same:
        raise PromotionRefused(
            f"lane {lane} (repo key {lane_key}) and target {target} (repo key {target_key}) "
            f"are different repositories — a promotion is a merge inside one clone, not a "
            f"transplant between two", condition="cross-repository")

    key = target_key
    try:
        holder = acquire(lock_dir, key, agent, str(target), mode="push", name=LOCK_NAME)
    except LockHeldError as exc:
        raise PromotionRefused(str(exc), condition="lock-held", code=EX_LOCK_HELD,
                               detail={"holder": exc.holder}) from exc

    receipt: dict[str, Any] = {
        "schema_version": "promotion_receipt.v1",
        "ts": serialized_push._utcnow_iso(),
        "agent": agent, "task_ids": req["task_ids"], "lane_worktree": str(lane),
        "target": str(target), "commit_range": req["commit_range"],
        "lock": {"name": LOCK_NAME, "key": key, "holder": holder.get("agent")},
        "applied": False, "dry_run": not apply, "warnings": [],
    }
    try:
        if dwell_s:
            # Test-visible hold: makes the critical section observable so the
            # serialization test can prove two promotions cannot interleave,
            # rather than asserting it from a race it cannot see.
            time.sleep(dwell_s)

        try:
            pf = serialized_push.preflight(target, require_fetched=False)
            receipt["branch"] = pf["branch"]
        except PreflightError as exc:
            if getattr(exc, "condition", None) in _PUBLISH_ONLY_CONDITIONS:
                receipt["warnings"].append(f"{exc.condition}: {exc}")
                receipt["branch"] = _git(
                    target, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
            else:
                raise PromotionRefused(str(exc), condition=getattr(exc, "condition", "preflight"))
        except SerializedPushError as exc:
            raise PromotionRefused(str(exc), condition=getattr(exc, "condition", "preflight"))

        base, head = resolve_range(lane, req["commit_range"])
        receipt["base"], receipt["head"] = base, head

        contain = check_containment(target, base, head)
        receipt["containment"] = contain
        if contain["already_promoted"]:
            receipt["already_promoted"] = True
            receipt["note"] = (f"{head[:12]} is already contained in {receipt.get('branch')} "
                               f"at {contain['target_head'][:12]} — no-op")
            return receipt
        if not contain["base_contained"]:
            raise PromotionRefused(
                f"lane base {base[:12]} is NOT contained in the target tip "
                f"{contain['target_head'][:12]} — the lane was never rebased onto current "
                f"{receipt.get('branch')}, so its diff assumes a tree that no longer exists. "
                f"Rebase the lane (its owner does that, in its own worktree) and re-request.",
                condition="lane-not-rebased")

        paths = changed_paths(lane, base, head)
        receipt["changed_paths"] = paths
        if not paths:
            raise PromotionRefused(
                f"the range {base[:12]}..{head[:12]} changes no files — there is nothing to "
                f"promote, and an empty promotion that reported success would be the "
                f"vacuous-pass shape", condition="empty-range")

        gate = gate_check(paths, receipt.get("branch") or "", repo_key_name, operator_ack)
        receipt["gate"] = gate
        if gate["verdict"] == "gated":
            reason = ("touches the human-only path list" if gate["hits"] else
                      f"touches the D9 loop plane {gate['loop_plane']} with no --operator-ack")
            raise PromotionRefused(
                f"REFUSED by the merge gate: this promotion {reason}. Promotions of gated "
                f"paths land as proposed commits with an operator acknowledgement, never "
                f"autonomously.", condition="gated", code=EX_GATED,
                detail={"gate": gate})

        dirty = dirty_overlap(target, paths)
        receipt["dirty_overlap"] = dirty
        if dirty:
            raise PromotionRefused(
                f"the target worktree has UNCOMMITTED changes in {len(dirty)} path(s) this "
                f"promotion touches ({', '.join(dirty[:5])}) — landing here would entangle "
                f"another session's in-flight work with this merge. Refusing.",
                condition="dirty-target")

        patch = build_patch(lane, base, head, paths)
        receipt["patch_bytes"] = len(patch)
        check = apply_patch(target, patch, check_only=True)
        if check.returncode != 0:
            raise PromotionRefused(
                f"CONFLICT: the lane's diff does not apply cleanly to "
                f"{receipt.get('branch')} at {contain['target_head'][:12]}.\n"
                f"{(check.stderr or check.stdout).strip()[:800]}\n"
                f"Nothing was applied and no merge was started. Resolving this is the lane "
                f"owner's job (rebase in the lane, re-run its tests, re-request); a "
                f"promotion that auto-resolved would land a resolution nobody reviewed.",
                condition="conflict", code=EX_CONFLICT,
                detail={"stderr": (check.stderr or check.stdout).strip()[:2000]})

        if not apply:
            receipt["plan"] = {
                "would_apply_paths": paths,
                "would_commit_with": f"git commit -m <msg> -- {' '.join(paths[:8])}"
                                     + (" …" if len(paths) > 8 else ""),
            }
            return receipt

        applied = apply_patch(target, patch, check_only=False)
        if applied.returncode != 0:
            raise PromotionRefused(
                f"the patch passed --check but failed to apply: "
                f"{(applied.stderr or applied.stdout).strip()[:600]}",
                condition="apply-failed", code=EX_CONFLICT)
        message = _commit_message(req, base, head, gate)
        receipt["commit"] = commit_paths(target, paths, message)
        receipt["applied"] = True
        receipt["commit_message"] = message
        return receipt
    finally:
        try:
            release(lock_dir, key, agent, name=LOCK_NAME)
        except SerializedPushError as exc:
            print(f"promote_lane: WARN could not release the promote lock: {exc}",
                  file=sys.stderr)


def _commit_message(req: dict, base: str, head: str, gate: dict) -> str:
    ids = ", ".join(req["task_ids"])
    lines = [f"promote({ids}): lane {Path(req['lane_worktree']).name} → main",
             "",
             f"Promoted range: {base[:12]}..{head[:12]}",
             f"Lane worktree: {req['lane_worktree']}",
             "Serialized through scripts/coordination/promote_lane.py (P2-8);",
             "committed by explicit pathspec.",
             ]
    if gate.get("operator_ack"):
        lines.append(f"Operator ack: {gate['operator_ack']}")
    return "\n".join(lines)


# ------------------------------------------------------------------- CLI


def cmd_promote(args: argparse.Namespace) -> int:
    try:
        req = load_request(args)
        receipt = promote(
            req, target=Path(args.target).resolve(), agent=args.agent,
            lock_dir=Path(args.lock_dir), apply=args.apply,
            operator_ack=args.operator_ack, dwell_s=args.dwell_s,
            repo_key_name=args.repo_key)
    except PromotionRefused as exc:
        out = {"refused": True, "condition": exc.condition, "message": str(exc),
               "detail": exc.detail}
        if exc.detail.get("gate", {}).get("token_block"):
            print(exc.detail["gate"]["token_block"], file=sys.stderr)
        print(json.dumps(out, indent=2, default=str))
        print(f"promote_lane: REFUSED ({exc.condition}) — {exc}", file=sys.stderr)
        return exc.code

    if args.receipt:
        Path(args.receipt).write_text(json.dumps(receipt, indent=2, default=str) + "\n",
                                      encoding="utf-8")
    print(json.dumps(receipt, indent=2, default=str))
    if not receipt.get("applied") and not receipt.get("already_promoted"):
        print("promote_lane: DRY RUN — nothing was written. Re-run with --apply.",
              file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="promote_lane.py",
                                description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("promote", help="promote one lane range onto the target branch")
    c.add_argument("--agent", required=True, help="your roster id; recorded as the lock holder")
    c.add_argument("--task-id", help="the row being promoted")
    c.add_argument("--lane-worktree", help="the pool lane worktree holding the commits")
    c.add_argument("--range", help="commit range, e.g. abc123..def456")
    c.add_argument("--request-json", help="promotion row JSON (or '-' for stdin)")
    c.add_argument("--target", default=os.environ.get("EPYC_PROMOTE_TARGET", DEFAULT_TARGET),
                   help="the worktree to promote INTO (default: %(default)s)")
    c.add_argument("--lock-dir", default=os.environ.get(
        "SERIALIZED_PUSH_LOCK_DIR", str(serialized_push.DEFAULT_LOCK_DIR)))
    c.add_argument("--repo-key", default="epyc-root", choices=sorted(merge_gate.REPO_PATHS),
                   help="which repo's rules the merge gate applies (default: %(default)s)")
    c.add_argument("--operator-ack",
                   help="reference to the operator's acknowledgement; required for any "
                        "path under the D9 loop plane (scripts/coordination/**)")
    c.add_argument("--apply", action="store_true",
                   help="actually land the commit. Without this, nothing is written.")
    c.add_argument("--receipt", help="write the receipt JSON here as well as stdout")
    c.add_argument("--dwell-s", type=float, default=0.0,
                   help="hold the promote lock this long inside the critical section; "
                        "exists so the serialization test can observe the window")
    c.set_defaults(func=cmd_promote)
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
