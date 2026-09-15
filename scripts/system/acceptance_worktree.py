#!/usr/bin/env python3
"""Create and retire owner-bound acceptance worktrees without silent deletion."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import uuid
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "epyc.acceptance_worktree_receipt.v1"
DEFAULT_ACCEPTANCE_ROOT = Path("/mnt/raid0/llm/worktrees/acceptance")
DEFAULT_RECEIPT_ROOT = Path("/mnt/raid0/llm/autokernel/acceptance-worktree-receipts")
OPEN_STATES = {"created", "retained"}
NETWORK_PREFIXES = ("https://", "ssh://", "git://", "git@")


class Refusal(RuntimeError):
    """The requested transition is unsafe and changed no worktree state."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_git(
    repo: Path, *args: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise Refusal(
            f"git {' '.join(args)} failed in {repo}: "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    return result


def canonical_existing_dir(path: Path, label: str) -> Path:
    resolved = path.expanduser().resolve(strict=True)
    if not resolved.is_dir():
        raise Refusal(f"{label} is not a directory: {resolved}")
    return resolved


def canonical_new_path(path: Path, root: Path) -> Path:
    if not path.is_absolute():
        raise Refusal("worktree path must be absolute")
    if path.exists() or path.is_symlink():
        raise Refusal(f"worktree path already exists: {path}")
    resolved_root = canonical_existing_dir(root, "acceptance root")
    resolved_parent = path.parent.resolve(strict=True)
    candidate = resolved_parent / path.name
    try:
        candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise Refusal(
            f"worktree path {candidate} is outside acceptance root {resolved_root}"
        ) from exc
    return candidate


def fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    encoded = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_CLOEXEC, 0o644)
    try:
        if os.write(fd, encoded) != len(encoded):
            raise OSError(f"short append to {path}")
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    encoded = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, 0o644)
        if os.write(fd, encoded) != len(encoded):
            raise OSError(f"short write to {temporary}")
        os.fsync(fd)
    finally:
        os.close(fd)
    try:
        os.replace(temporary, path)
        fsync_dir(path.parent)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def record(
    receipt_path: Path, receipt: dict[str, Any], event: str, **updates: Any
) -> None:
    receipt.update(updates)
    receipt["sequence"] = int(receipt.get("sequence", 0)) + 1
    receipt["updated_at"] = utc_now()
    event_row = dict(receipt)
    event_row["event"] = event
    append_jsonl(receipt_path.with_suffix(".jsonl"), event_row)
    atomic_json(receipt_path, receipt)


def read_receipt(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise Refusal(f"cannot read receipt {path}: {exc}") from exc
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise Refusal(f"receipt {path} is not {SCHEMA}")
    return value


def worktree_records(repo: Path) -> dict[Path, dict[str, str]]:
    output = run_git(repo, "worktree", "list", "--porcelain").stdout
    records: dict[Path, dict[str, str]] = {}
    current: dict[str, str] = {}
    for line in output.splitlines() + [""]:
        if not line:
            if "worktree" in current:
                records[Path(current["worktree"]).resolve()] = dict(current)
            current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value
    return records


def repository_identity(repo: Path) -> tuple[Path, Path]:
    top = canonical_existing_dir(repo, "repository")
    common = run_git(
        top, "rev-parse", "--path-format=absolute", "--git-common-dir"
    ).stdout.strip()
    if not common:
        raise Refusal(f"cannot resolve git common directory for {top}")
    return top, Path(common).resolve()


def ensure_text(value: str, label: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise Refusal(f"{label} must be non-empty")
    return stripped


def create(args: argparse.Namespace) -> Path:
    repo, common_dir = repository_identity(args.repo)
    acceptance_root = canonical_existing_dir(args.acceptance_root, "acceptance root")
    path = canonical_new_path(args.path, acceptance_root)
    owner = ensure_text(args.owner, "owner")
    task = ensure_text(args.task, "task")
    purpose = ensure_text(args.purpose, "purpose")
    branch = ensure_text(args.branch, "branch")
    if not branch.startswith("accept/"):
        raise Refusal("acceptance branch must start with 'accept/'")
    if (
        run_git(
            repo, "show-ref", "--verify", f"refs/heads/{branch}", check=False
        ).returncode
        == 0
    ):
        raise Refusal(f"branch already exists: {branch}")
    base_commit = run_git(
        repo, "rev-parse", "--verify", f"{args.base}^{{commit}}"
    ).stdout.strip()
    if not base_commit:
        raise Refusal(f"base does not resolve to a commit: {args.base}")

    receipt_root = args.receipt_root.expanduser().resolve()
    receipt_root.mkdir(parents=True, exist_ok=True)
    fsync_dir(receipt_root)
    receipt_id = f"akaw-{uuid.uuid4().hex}"
    receipt_path = receipt_root / f"{receipt_id}.json"
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "receipt_id": receipt_id,
        "sequence": 0,
        "state": "planned",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "host": socket.gethostname(),
        "creator_pid": os.getpid(),
        "owner": owner,
        "task": task,
        "purpose": purpose,
        "repo": str(repo),
        "git_common_dir": str(common_dir),
        "acceptance_root": str(acceptance_root),
        "receipt_root": str(receipt_root),
        "worktree": str(path),
        "branch": branch,
        "base_ref": args.base,
        "base_commit": base_commit,
        "outcome": None,
    }
    record(receipt_path, receipt, "planned")
    result = run_git(
        repo, "worktree", "add", "-b", branch, str(path), base_commit, check=False
    )
    if result.returncode != 0:
        record(
            receipt_path,
            receipt,
            "create_refused",
            state="create_refused",
            refusal=result.stderr.strip() or result.stdout.strip(),
        )
        raise Refusal(f"git worktree add failed: {receipt['refusal']}")
    record(
        receipt_path,
        receipt,
        "created",
        state="created",
        created_head=run_git(path, "rev-parse", "HEAD").stdout.strip(),
    )
    return receipt_path


def dirty_rows(worktree: Path) -> list[str]:
    output = run_git(
        worktree,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--ignored",
    ).stdout
    return [line for line in output.splitlines() if line]


def network_remote(url: str) -> bool:
    return url.startswith(NETWORK_PREFIXES) or (
        ":" in url and "@" in url.partition(":")[0] and not url.startswith("file:")
    )


def live_holders(path: Path) -> list[dict[str, Any]]:
    prefix = str(path) + os.sep
    holders: list[dict[str, Any]] = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        references: list[str] = []
        for name in ("cwd", "exe"):
            try:
                target = os.readlink(proc / name)
            except OSError:
                continue
            if target == str(path) or target.startswith(prefix):
                references.append(f"{name}:{target}")
        try:
            fds: Iterable[Path] = (proc / "fd").iterdir()
        except OSError:
            fds = ()
        for fd in fds:
            try:
                target = os.readlink(fd)
            except OSError:
                continue
            if target == str(path) or target.startswith(prefix):
                references.append(f"fd:{fd.name}:{target}")
        if references:
            holders.append({"pid": int(proc.name), "references": references})
    return sorted(holders, key=lambda item: item["pid"])


def refuse_close(
    receipt_path: Path, receipt: dict[str, Any], reasons: list[str]
) -> None:
    record(
        receipt_path,
        receipt,
        "close_refused",
        state="retained",
        last_refusal={"at": utc_now(), "reasons": reasons},
    )
    raise Refusal("; ".join(reasons))


def close(args: argparse.Namespace) -> None:
    receipt_path = args.receipt.expanduser().resolve(strict=True)
    receipt = read_receipt(receipt_path)
    required = {
        "owner",
        "repo",
        "git_common_dir",
        "acceptance_root",
        "receipt_root",
        "worktree",
        "branch",
        "base_commit",
    }
    missing = sorted(required.difference(receipt))
    if missing:
        raise Refusal(f"receipt is missing required fields: {missing}")
    receipt_root = canonical_existing_dir(Path(receipt["receipt_root"]), "receipt root")
    if receipt_path.parent != receipt_root:
        raise Refusal(f"receipt is outside its recorded receipt root: {receipt_path}")
    if receipt.get("state") not in OPEN_STATES:
        raise Refusal(f"receipt state {receipt.get('state')!r} is not open")
    if ensure_text(args.owner, "owner") != receipt.get("owner"):
        raise Refusal("owner does not match the creation receipt")

    repo, common_dir = repository_identity(Path(receipt["repo"]))
    if str(common_dir) != receipt.get("git_common_dir"):
        raise Refusal("repository common-dir identity changed")
    acceptance_root = canonical_existing_dir(
        Path(receipt["acceptance_root"]), "recorded acceptance root"
    )
    worktree = Path(receipt["worktree"]).resolve(strict=True)
    try:
        worktree.relative_to(acceptance_root)
    except ValueError as exc:
        raise Refusal(
            f"recorded worktree {worktree} is outside acceptance root {acceptance_root}"
        ) from exc
    if not str(receipt["branch"]).startswith("accept/"):
        raise Refusal("recorded branch is not an acceptance branch")
    records = worktree_records(repo)
    registered = records.get(worktree)
    if registered is None:
        refuse_close(
            receipt_path, receipt, ["worktree is not registered at its exact path"]
        )
    expected_ref = f"refs/heads/{receipt['branch']}"
    if registered.get("branch") != expected_ref:
        refuse_close(
            receipt_path,
            receipt,
            [f"registered branch {registered.get('branch')!r} != {expected_ref!r}"],
        )

    reasons: list[str] = []
    dirty = dirty_rows(worktree)
    if dirty:
        reasons.append(
            f"worktree is dirty or carries ignored files ({len(dirty)} rows)"
        )
    holders = live_holders(worktree)
    if holders:
        reasons.append(f"worktree has live holders: {holders}")
    head = run_git(worktree, "rev-parse", "HEAD").stdout.strip()

    pushed_witness: dict[str, str] | None = None
    if args.outcome == "commit-push":
        ahead = int(
            run_git(
                repo, "rev-list", "--count", f"{receipt['base_commit']}..{head}"
            ).stdout
        )
        if ahead < 1:
            reasons.append(
                "commit-push requires at least one commit beyond the recorded base"
            )
        remote = args.remote
        url_result = run_git(repo, "remote", "get-url", remote, check=False)
        if url_result.returncode != 0:
            reasons.append(f"remote does not exist: {remote}")
        else:
            url = url_result.stdout.strip()
            if not network_remote(url):
                reasons.append(f"remote {remote} is not a network remote: {url}")
            remote_ref = f"refs/remotes/{remote}/{receipt['branch']}"
            remote_head = run_git(
                repo, "rev-parse", "--verify", remote_ref, check=False
            )
            if remote_head.returncode != 0 or remote_head.stdout.strip() != head:
                reasons.append(f"{remote_ref} does not point exactly at HEAD {head}")
            else:
                pushed_witness = {
                    "remote": remote,
                    "url": url,
                    "ref": remote_ref,
                    "commit": head,
                }
    else:
        if head != receipt["base_commit"]:
            reasons.append(
                "discard requires HEAD to equal the recorded base; local commits are retained, never deleted"
            )

    if reasons:
        refuse_close(receipt_path, receipt, reasons)

    record(
        receipt_path,
        receipt,
        "remove_authorized",
        state="remove_authorized",
        outcome=args.outcome,
        terminal_head=head,
        clean=True,
        live_holders=[],
        pushed_witness=pushed_witness,
        remove_command=["git", "-C", str(repo), "worktree", "remove", str(worktree)],
    )
    # Exact registered path, clean tree, no --force. The durable authorization above
    # intentionally precedes the irreversible filesystem transition.
    run_git(repo, "worktree", "remove", str(worktree))
    if worktree.exists() or worktree in worktree_records(repo):
        record(receipt_path, receipt, "remove_incomplete", state="remove_incomplete")
        raise Refusal(
            "git worktree remove returned success but the path or registration remains"
        )

    branch_deleted = False
    if args.outcome == "discard":
        deleted = run_git(repo, "branch", "-d", receipt["branch"], check=False)
        branch_deleted = deleted.returncode == 0
    record(
        receipt_path,
        receipt,
        "removed",
        state="removed",
        removed_at=utc_now(),
        branch_deleted=branch_deleted,
    )


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)

    create_cmd = commands.add_parser(
        "create", help="create and register an owned worktree"
    )
    create_cmd.add_argument("--repo", type=Path, required=True)
    create_cmd.add_argument("--path", type=Path, required=True)
    create_cmd.add_argument("--branch", required=True)
    create_cmd.add_argument("--base", default="origin/main")
    create_cmd.add_argument("--owner", required=True)
    create_cmd.add_argument("--task", required=True)
    create_cmd.add_argument("--purpose", required=True)
    create_cmd.add_argument(
        "--acceptance-root", type=Path, default=DEFAULT_ACCEPTANCE_ROOT
    )
    create_cmd.add_argument("--receipt-root", type=Path, default=DEFAULT_RECEIPT_ROOT)

    close_cmd = commands.add_parser(
        "close", help="retire after explicit commit-push or discard"
    )
    close_cmd.add_argument("--receipt", type=Path, required=True)
    close_cmd.add_argument("--owner", required=True)
    close_cmd.add_argument(
        "--outcome", choices=("commit-push", "discard"), required=True
    )
    close_cmd.add_argument("--remote", default="origin")
    return cli


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "create":
            receipt = create(args)
            print(
                json.dumps(
                    {"status": "created", "receipt": str(receipt)}, sort_keys=True
                )
            )
        else:
            close(args)
            print(
                json.dumps(
                    {"status": "removed", "receipt": str(args.receipt)}, sort_keys=True
                )
            )
    except Refusal as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
