#!/usr/bin/env python3
"""Retire archived KEEP-dirty AutoKernel worktrees through a fail-closed state machine.

The default is a read-only dry-run.  ``--apply`` requires an interactive operator confirmation
and operates only on exact archive records selected with ``--record``.  It never discovers
targets by name, prunes worktrees, runs gc, or passes ``--force``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import autokernel_dirty_preserve as preserve
import autokernel_disk_sweep as sweep

RECEIPT_SCHEMA = "autokernel-dirty-worktree-retirement/v1"
DEFAULT_RECEIPT_ROOT = Path(
    "/mnt/raid0/llm/archives/autokernel/dirty-worktree-retirement-receipts"
)
DEFAULT_ALLOWED_ROOTS = (
    Path("/mnt/raid0/llm/worktrees/acceptance"),
    Path("/mnt/raid0/llm/worktrees/inf70"),
    Path("/mnt/raid0/llm/worktrees/mains"),
)
RESUME_STATES = {
    "verified",
    "reset_authorized",
    "tracked_reset",
    "untracked_remove_authorized",
    "untracked_removed",
    "worktree_remove_authorized",
    "removed",
}


class RetireError(RuntimeError):
    """A safety predicate failed; the row must remain retained."""


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(json.dumps(value, indent=2, sort_keys=True).encode() + b"\n")
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
        fsync_dir(path.parent)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def receipt_event(
    receipt_path: Path,
    receipt: dict[str, Any],
    event: str,
    *,
    state: str | None = None,
    **updates: Any,
) -> None:
    if state is not None:
        receipt["state"] = state
    receipt.update(updates)
    receipt["sequence"] = int(receipt.get("sequence", 0)) + 1
    receipt["updated_at"] = sweep.now_utc().isoformat(timespec="seconds")
    row = dict(receipt)
    row["event"] = event
    ledger = receipt_path.with_suffix(".jsonl")
    ledger.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_json(row)
    fd = os.open(ledger, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_CLOEXEC, 0o644)
    try:
        written = os.write(fd, encoded)
        if written != len(encoded):
            raise OSError(f"short receipt append to {ledger}")
        os.fsync(fd)
    finally:
        os.close(fd)
    atomic_json(receipt_path, receipt)


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        raise RetireError(f"cannot read {label} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RetireError(f"{label} is not a JSON object: {path}")
    return value


def load_manifest(
    path: Path, expected_sha: str, max_age_hours: float
) -> tuple[dict, str]:
    data = path.read_bytes()
    actual = sha256_bytes(data)
    if actual != expected_sha.lower():
        raise RetireError(
            f"manifest sha256 {actual} != reviewed --manifest-sha {expected_sha}"
        )
    manifest = json.loads(data)
    if manifest.get("schema") != sweep.SCHEMA:
        raise RetireError(
            f"unsupported sweep manifest schema: {manifest.get('schema')}"
        )
    generated = manifest.get("generated_at")
    if not generated:
        raise RetireError("reviewed manifest has no generated_at timestamp")
    if max_age_hours >= 0:
        age = (
            sweep.now_utc() - sweep.dt.datetime.fromisoformat(generated)
        ).total_seconds() / 3600
        if age > max_age_hours:
            raise RetireError(
                f"reviewed manifest is {age:.1f}h old (> {max_age_hours}h); re-scan and re-review"
            )
    return manifest, actual


def canonical_target(path_text: str, allowed_roots: list[Path]) -> Path:
    raw = Path(path_text)
    if not raw.is_absolute() or not raw.exists() or raw.is_symlink():
        raise RetireError(
            f"target must be an existing absolute non-symlink path: {raw}"
        )
    target = raw.resolve(strict=True)
    if str(target) != os.path.normpath(path_text):
        raise RetireError(
            f"target spelling is not its exact canonical path: {path_text} != {target}"
        )
    roots = [root.resolve(strict=True) for root in allowed_roots]
    if target.parent not in roots:
        raise RetireError(f"target is outside exact allowed roots {roots}: {target}")
    return target


def manifest_row(manifest: dict, path: str) -> dict:
    rows = [row for row in manifest.get("rows", []) if row.get("path") == path]
    if len(rows) != 1:
        raise RetireError(
            f"reviewed manifest must contain exactly one row for {path}; got {len(rows)}"
        )
    row = rows[0]
    if row.get("verdict") != "KEEP-dirty":
        raise RetireError(
            f"reviewed row is not KEEP-dirty: {path} ({row.get('verdict')})"
        )
    if row.get("kind") != "git-worktree":
        raise RetireError(
            f"reviewed KEEP-dirty row is not a registered git worktree: {path}"
        )
    return row


def registered_worktree(repo: Path, target: Path) -> bool:
    result = sweep.git(str(repo), "worktree", "list", "--porcelain")
    if result.returncode:
        raise RetireError(
            f"cannot enumerate worktrees in {repo}: {result.stderr.strip()}"
        )
    return any(line == f"worktree {target}" for line in result.stdout.splitlines())


def ignored_paths(target: Path) -> list[str]:
    output = preserve.git(
        target, "ls-files", "--others", "--ignored", "--exclude-standard", "-z"
    )
    return [preserve.safe_relative(raw) for raw in preserve.nul_items(output)]


def verify_unpushed_bundle(
    archive: Path, expected_head: str, source_repo: Path
) -> None:
    with tarfile.open(archive, "r:") as tf:
        try:
            member = tf.getmember("unpushed-head.bundle")
        except KeyError as exc:
            raise RetireError(
                "archive record requires an unpushed-HEAD bundle, but none exists"
            ) from exc
        stream = tf.extractfile(member)
        if stream is None:
            raise RetireError("unpushed-HEAD bundle is not a regular archive member")
        fd, temporary = tempfile.mkstemp(prefix="autokernel-retire-", suffix=".bundle")
        try:
            with os.fdopen(fd, "wb") as output:
                while chunk := stream.read(1024 * 1024):
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            verified = subprocess.run(
                ["git", "-C", str(source_repo), "bundle", "verify", temporary],
                text=True,
                capture_output=True,
                check=False,
            )
            if verified.returncode:
                raise RetireError(
                    f"unpushed-HEAD bundle verification failed: {verified.stderr.strip()}"
                )
            heads = subprocess.run(
                ["git", "bundle", "list-heads", temporary],
                text=True,
                capture_output=True,
                check=False,
            )
            if heads.returncode or not any(
                line.split(maxsplit=1)[0] == expected_head
                for line in heads.stdout.splitlines()
                if line.strip()
            ):
                raise RetireError(
                    f"unpushed-HEAD bundle does not advertise exact HEAD {expected_head}"
                )
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def verify_archive_record(
    record_path: Path, manifest_sha: str, row: dict
) -> dict[str, Any]:
    record = load_json(record_path, "archive record")
    if record.get("schema") != preserve.RECORD_SCHEMA:
        raise RetireError(f"unsupported archive record schema: {record.get('schema')}")
    required = {
        "path",
        "head",
        "source_fingerprint",
        "archive_sha256",
        "archive",
        "unpushed_bundle",
        "sweep_manifest_sha256",
    }
    missing = sorted(required.difference(record))
    if missing:
        raise RetireError(f"archive record is missing fields: {missing}")
    if record["path"] != row["path"]:
        raise RetireError("archive record path does not exactly match the reviewed row")
    if record["sweep_manifest_sha256"] != manifest_sha:
        raise RetireError(
            "archive record was not produced from the reviewed manifest SHA"
        )
    archive = Path(record["archive"])
    owner = Path(row["repo"])
    verified = preserve.verify_archive(archive, owner if owner.is_dir() else None)
    if verified["archive_sha256"] != record["archive_sha256"]:
        raise RetireError("archive bytes do not match the archive record SHA-256")
    metadata = verified["metadata"]
    if metadata.get("source_path") != row["path"]:
        raise RetireError(
            "archive metadata source path does not match the reviewed row"
        )
    if metadata.get("sweep_manifest_sha256") != manifest_sha:
        raise RetireError("archive metadata does not bind the reviewed manifest SHA")
    if metadata.get("sweep_row") != row:
        raise RetireError(
            "archive metadata sweep row does not exactly match the reviewed row"
        )
    if metadata.get("head") != record["head"]:
        raise RetireError("archive metadata HEAD does not match the archive record")
    if bool(metadata.get("head_unpushed_to_network_remote")) != bool(
        record["unpushed_bundle"]
    ):
        raise RetireError("archive bundle claim does not match the durable record")
    if record["unpushed_bundle"]:
        verify_unpushed_bundle(archive, record["head"], owner)
    return {"record": record, "metadata": metadata, "archive": archive}


def exact_worktree_identity(target: Path, row: dict, metadata: dict) -> Path:
    info = sweep.resolve_worktree(str(target))
    if info.get("kind") != "git-worktree" or info.get("locked"):
        raise RetireError(f"target is not an unlocked registered worktree: {info}")
    repo = Path(info["repo"]).resolve(strict=True)
    if row.get("repo") and Path(row["repo"]).resolve(strict=True) != repo:
        raise RetireError("owning repository changed since the reviewed sweep")
    common = Path(
        preserve.git(target, "rev-parse", "--path-format=absolute", "--git-common-dir")
        .decode()
        .strip()
    ).resolve(strict=True)
    if common != Path(metadata["git_common_dir"]).resolve(strict=True):
        raise RetireError("git common-dir identity differs from the archive record")
    if not registered_worktree(repo, target):
        raise RetireError("target is not registered at its exact path")
    return repo


def process_guard(target: Path, proc_root: str, aliases: list[tuple[str, str]]) -> dict:
    snapshot = sweep.probe_processes(proc_root, aliases)
    if snapshot.state != "COMPLETE":
        raise RetireError(
            f"process probe is {snapshot.state}, not COMPLETE: {snapshot.summary()}"
        )
    holders = sweep.live_hits(str(target), snapshot, self_pid=os.getpid())
    if holders:
        raise RetireError(f"target has live holders: {holders}")
    return snapshot.summary()


def untracked_metadata(target: Path) -> list[dict[str, Any]]:
    status = preserve.git(
        target, "status", "--porcelain=v2", "-z", "--untracked-files=all"
    )
    tracked = [
        entry for entry in preserve.nul_items(status) if not entry.startswith(b"? ")
    ]
    if tracked:
        raise RetireError(f"tracked state is not reset ({len(tracked)} status rows)")
    return [entry.metadata() for entry in preserve.read_untracked(target, status)]


def verify_reset_state(
    target: Path, record: dict, metadata: dict
) -> list[dict[str, Any]]:
    head = preserve.git(target, "rev-parse", "HEAD").decode().strip()
    if head != record["head"]:
        raise RetireError(f"HEAD changed after archive: {head} != {record['head']}")
    ignored = ignored_paths(target)
    if ignored:
        raise RetireError(
            f"ignored content is never deleted by retirement: {ignored[:10]}"
        )
    current = untracked_metadata(target)
    archived = {entry["path"]: entry for entry in metadata.get("untracked", [])}
    for entry in current:
        if archived.get(entry["path"]) != entry:
            raise RetireError(
                f"post-reset untracked path is new or differs from archive: {entry['path']}"
            )
    return current


def receipt_path_for(root: Path, manifest_sha: str, record: dict) -> Path:
    key = sha256_bytes(
        canonical_json(
            {
                "manifest_sha256": manifest_sha,
                "path": record["path"],
                "archive_sha256": record["archive_sha256"],
            }
        )
    )
    return root / key[:2] / f"{key}.json"


def load_receipt(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    receipt = load_json(path, "retirement receipt")
    if (
        receipt.get("schema") != RECEIPT_SCHEMA
        or receipt.get("state") not in RESUME_STATES
    ):
        raise RetireError(f"invalid or non-resumable retirement receipt: {path}")
    return receipt


def verify_receipt_identity(
    receipt: dict, manifest_sha: str, record_path: Path, record: dict
) -> None:
    expected = {
        "manifest_sha256": manifest_sha,
        "archive_record": str(record_path),
        "archive_sha256": record["archive_sha256"],
        "path": record["path"],
        "head": record["head"],
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise RetireError(f"retirement receipt identity mismatch for {key}")


def preflight_record(
    record_path: Path,
    manifest: dict,
    manifest_sha: str,
    allowed_roots: list[Path],
    receipt_root: Path,
    proc_root: str,
    aliases: list[tuple[str, str]],
) -> dict[str, Any]:
    raw_record = load_json(record_path, "archive record")
    row = manifest_row(manifest, raw_record.get("path", ""))
    verified = verify_archive_record(record_path, manifest_sha, row)
    record, metadata = verified["record"], verified["metadata"]
    receipt_path = receipt_path_for(receipt_root, manifest_sha, record)
    receipt = load_receipt(receipt_path)
    if receipt:
        verify_receipt_identity(receipt, manifest_sha, record_path, record)

    target_raw = Path(record["path"])
    if (
        receipt
        and receipt["state"] in {"worktree_remove_authorized", "removed"}
        and not target_raw.exists()
    ):
        repo = Path(row["repo"]).resolve(strict=True)
        if registered_worktree(repo, target_raw):
            raise RetireError(
                "target path is absent but its worktree registration remains"
            )
        return {
            "row": row,
            "record": record,
            "metadata": metadata,
            "record_path": record_path,
            "receipt_path": receipt_path,
            "receipt": receipt,
            "target": target_raw,
            "repo": repo,
            "probe": None,
            "remaining_untracked": [],
            "already_absent": True,
        }

    if receipt and receipt["state"] == "removed":
        raise RetireError("receipt says removed but the target path still exists")

    target = canonical_target(record["path"], allowed_roots)
    durable_paths = {
        "archive record": record_path,
        "archive object": Path(record["archive"]).resolve(strict=True),
        "receipt root": receipt_root,
    }
    for label, durable in durable_paths.items():
        if durable == target or durable.is_relative_to(target):
            raise RetireError(
                f"{label} is inside the worktree being retired: {durable}"
            )
    repo = exact_worktree_identity(target, row, metadata)
    probe = process_guard(target, proc_root, aliases)
    ignored = ignored_paths(target)
    if ignored:
        raise RetireError(
            f"ignored content is never archived or deleted: {ignored[:10]}"
        )

    state = receipt["state"] if receipt else "new"
    if state in {"new", "verified"}:
        snapshot = preserve.capture(target, manifest_sha, row, include_bundle=False)
        if snapshot.metadata["head"] != record["head"]:
            raise RetireError("fresh source HEAD does not match the archive record")
        if snapshot.fingerprint() != record["source_fingerprint"]:
            raise RetireError(
                "fresh source fingerprint does not exactly match the archive record"
            )
        remaining = [entry.metadata() for entry in snapshot.untracked]
    else:
        remaining = verify_reset_state(target, record, metadata)
    return {
        "row": row,
        "record": record,
        "metadata": metadata,
        "record_path": record_path,
        "receipt_path": receipt_path,
        "receipt": receipt,
        "target": target,
        "repo": repo,
        "probe": probe,
        "remaining_untracked": remaining,
        "already_absent": False,
    }


def remove_enumerated(target: Path, entries: list[dict[str, Any]]) -> None:
    for entry in sorted(entries, key=lambda item: item["path"], reverse=True):
        candidate = target / entry["path"]
        try:
            current = preserve.read_untracked(
                target,
                preserve.git(
                    target, "status", "--porcelain=v2", "-z", "--untracked-files=all"
                ),
            )
        except preserve.PreserveError as exc:
            raise RetireError(str(exc)) from exc
        current_by_path = {item.path: item.metadata() for item in current}
        if current_by_path.get(entry["path"]) != entry:
            raise RetireError(
                f"authorized untracked path changed before unlink: {entry['path']}"
            )
        candidate.unlink()


def apply_plan(
    plan: dict[str, Any], proc_root: str, aliases: list[tuple[str, str]]
) -> str:
    record = plan["record"]
    target: Path = plan["target"]
    repo: Path = plan["repo"]
    receipt_path: Path = plan["receipt_path"]
    receipt = plan["receipt"]
    if receipt is None:
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "sequence": 0,
            "state": "verified",
            "created_at": sweep.now_utc().isoformat(timespec="seconds"),
            "updated_at": sweep.now_utc().isoformat(timespec="seconds"),
            "host": socket.gethostname(),
            "operator_pid": os.getpid(),
            "manifest_sha256": plan["row_manifest_sha"],
            "archive_record": str(plan["record_path"]),
            "archive_sha256": record["archive_sha256"],
            "path": record["path"],
            "repo": str(repo),
            "head": record["head"],
            "unpushed_bundle_verified": bool(record["unpushed_bundle"]),
        }
        receipt_event(
            receipt_path,
            receipt,
            "verified",
            state="verified",
            source_fingerprint=record["source_fingerprint"],
            process_probe=plan["probe"],
        )
    if receipt["state"] == "removed":
        return "already-removed"
    if plan["already_absent"]:
        receipt_event(receipt_path, receipt, "removed-recovered", state="removed")
        return "removed-recovered"

    try:
        if receipt["state"] == "verified":
            fresh = preserve.capture(
                target, plan["row_manifest_sha"], plan["row"], include_bundle=False
            )
            if fresh.fingerprint() != record["source_fingerprint"]:
                raise RetireError(
                    "source changed after preflight and before reset authorization"
                )
            process_guard(target, proc_root, aliases)
            receipt_event(
                receipt_path,
                receipt,
                "reset-authorized",
                state="reset_authorized",
                command=["git", "-C", str(target), "reset", "--hard", record["head"]],
            )
            reset = sweep.git(str(target), "reset", "--hard", record["head"])
            if reset.returncode:
                raise RetireError(f"tracked reset failed: {reset.stderr.strip()}")
        if receipt["state"] == "reset_authorized":
            remaining = verify_reset_state(target, record, plan["metadata"])
            receipt_event(
                receipt_path,
                receipt,
                "tracked-reset",
                state="tracked_reset",
                remaining_untracked=remaining,
            )
        if receipt["state"] == "tracked_reset":
            remaining = verify_reset_state(target, record, plan["metadata"])
            process_guard(target, proc_root, aliases)
            receipt_event(
                receipt_path,
                receipt,
                "untracked-remove-authorized",
                state="untracked_remove_authorized",
                authorized_untracked=remaining,
            )
        if receipt["state"] == "untracked_remove_authorized":
            current = verify_reset_state(target, record, plan["metadata"])
            process_guard(target, proc_root, aliases)
            authorized = {
                entry["path"]: entry
                for entry in receipt.get("authorized_untracked", [])
            }
            if any(authorized.get(entry["path"]) != entry for entry in current):
                raise RetireError(
                    "remaining untracked content exceeds its durable authorization"
                )
            remove_enumerated(target, current)
            if verify_reset_state(target, record, plan["metadata"]):
                raise RetireError(
                    "untracked content remains after exact enumerated removal"
                )
            receipt_event(
                receipt_path, receipt, "untracked-removed", state="untracked_removed"
            )
        if receipt["state"] == "untracked_removed":
            if preserve.git(
                target,
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
                "--ignored",
            ):
                raise RetireError("worktree is not completely clean before removal")
            process_guard(target, proc_root, aliases)
            receipt_event(
                receipt_path,
                receipt,
                "worktree-remove-authorized",
                state="worktree_remove_authorized",
                command=["git", "-C", str(repo), "worktree", "remove", str(target)],
            )
        if receipt["state"] == "worktree_remove_authorized":
            if target.exists():
                process_guard(target, proc_root, aliases)
                if preserve.git(
                    target,
                    "status",
                    "--porcelain=v1",
                    "--untracked-files=all",
                    "--ignored",
                ):
                    raise RetireError("worktree changed after remove authorization")
                removed = sweep.git(str(repo), "worktree", "remove", str(target))
                if removed.returncode:
                    raise RetireError(
                        f"exact non-force worktree removal failed: {removed.stderr.strip()}"
                    )
            if target.exists() or registered_worktree(repo, target):
                raise RetireError(
                    "worktree removal returned without removing path and registration"
                )
            receipt_event(receipt_path, receipt, "removed", state="removed")
        return receipt["state"]
    except Exception as exc:
        receipt_event(
            receipt_path,
            receipt,
            "retained",
            last_error={
                "at": sweep.now_utc().isoformat(timespec="seconds"),
                "message": str(exc),
            },
        )
        raise


def operator_confirm(plans: list[dict[str, Any]], manifest_sha: str) -> bool:
    if not sys.stdin.isatty():
        return False
    print(
        f"About to restore and retire {len(plans)} archived KEEP-dirty worktree(s).",
        file=sys.stderr,
    )
    try:
        typed = input(
            "Operator: type the first 12 hex chars of the reviewed manifest sha256 to confirm: "
        )
    except EOFError:
        return False
    return typed.strip().lower() == manifest_sha[:12]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha", required=True)
    parser.add_argument(
        "--record",
        type=Path,
        action="append",
        required=True,
        help="exact archive record",
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--allowed-root", type=Path, action="append")
    parser.add_argument("--receipt-root", type=Path, default=DEFAULT_RECEIPT_ROOT)
    parser.add_argument("--proc-root", default="/proc")
    parser.add_argument("--path-alias", action="append", default=[])
    parser.add_argument("--max-manifest-age-hours", type=float, default=72.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest, manifest_sha = load_manifest(
            args.manifest, args.manifest_sha, args.max_manifest_age_hours
        )
        records = [path.expanduser().resolve(strict=True) for path in args.record]
        if len(records) != len(set(records)):
            raise RetireError("duplicate --record path")
        allowed_roots = args.allowed_root or list(DEFAULT_ALLOWED_ROOTS)
        receipt_root = args.receipt_root.expanduser().resolve()
        aliases = sweep.parse_aliases(args.path_alias)
        plans = []
        for record_path in records:
            plan = preflight_record(
                record_path,
                manifest,
                manifest_sha,
                allowed_roots,
                receipt_root,
                args.proc_root,
                aliases,
            )
            plan["row_manifest_sha"] = manifest_sha
            plans.append(plan)
        targets = [str(plan["target"]) for plan in plans]
        if len(targets) != len(set(targets)):
            raise RetireError(
                "multiple archive records select the same target worktree"
            )
        if not args.apply:
            print(
                json.dumps(
                    {
                        "mode": "dry-run",
                        "manifest_sha256": manifest_sha,
                        "rows": [
                            {
                                "path": str(plan["target"]),
                                "archive_sha256": plan["record"]["archive_sha256"],
                                "receipt": str(plan["receipt_path"]),
                                "resume_state": (
                                    plan["receipt"]["state"]
                                    if plan["receipt"]
                                    else None
                                ),
                                "probe": plan["probe"],
                            }
                            for plan in plans
                        ],
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if not operator_confirm(plans, manifest_sha):
            raise RetireError(
                "operator manual confirmation required (interactive TTY, typed SHA prefix)"
            )
        results = []
        for plan in plans:
            try:
                state = apply_plan(plan, args.proc_root, aliases)
                results.append({"path": str(plan["target"]), "state": state})
            except Exception as exc:  # noqa: BLE001 - durable receipt makes batch resumable
                results.append(
                    {
                        "path": str(plan["target"]),
                        "state": "retained",
                        "error": str(exc),
                    }
                )
        print(
            json.dumps({"mode": "apply", "results": results}, indent=2, sort_keys=True)
        )
        return 1 if any(row["state"] == "retained" for row in results) else 0
    except (RetireError, preserve.PreserveError, OSError, ValueError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
