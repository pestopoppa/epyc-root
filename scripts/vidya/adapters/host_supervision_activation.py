"""Write and classify prospective host-supervision activation dependency evidence.

This is native operational evidence only. It deliberately has no ClaimTuple projection,
grade, belief frame, or read-side reconstruction. The event is eligible only when written
at the installer apply boundary and when a later hygiene flush consumes its pending marker.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

SOURCE_SCHEMA = "epyc.operational.host_supervision_activation.v1"
CLASSIFICATION = "dependency_evidence_only"
SUPPORT_SCOPE = "installation_run"
EXPECTED_OBSERVERS = {"host_hygiene_tick", "opencode_event_reaper"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")


class ReceiptError(ValueError):
    pass


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise ReceiptError(f"{label} must be lowercase SHA-256")
    return value


def _aware(value: object, label: str) -> dt.datetime:
    if not isinstance(value, str):
        raise ReceiptError(f"{label} must be timezone-aware RFC3339")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReceiptError(f"{label} must be timezone-aware RFC3339") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ReceiptError(f"{label} must be timezone-aware RFC3339")
    return parsed.astimezone(dt.timezone.utc)


def _safe_path(root: Path, path: Path) -> Path:
    root = root.resolve(strict=True)
    if ".." in path.parts:
        raise ReceiptError("parent traversal refused")
    path = path if path.is_absolute() else root / path
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise ReceiptError(f"path escapes canonical root: {path}") from exc
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        try:
            mode = cursor.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            raise ReceiptError(f"symlink refused: {cursor}")
    return path



def _json(data: bytes) -> object:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ReceiptError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(
                          ReceiptError(f"invalid JSON constant: {value}")))


def _uuid(value: object) -> str:
    if not isinstance(value, str):
        raise ReceiptError("install_id must be a canonical UUID")
    try:
        parsed = str(uuid.UUID(value))
    except ValueError as exc:
        raise ReceiptError("install_id must be a canonical UUID") from exc
    if parsed != value:
        raise ReceiptError("install_id must be a canonical UUID")
    return parsed


def _relative(value: object) -> str:
    if not isinstance(value, str) or not value or Path(value).is_absolute() \
            or ".." in Path(value).parts or str(Path(value)) != value:
        raise ReceiptError("receipt locator must be a normalized relative path")
    return value


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) |
                 getattr(os, "O_NOFOLLOW", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextmanager
def _lock(root: Path, base: Path):
    _mkdirs(root, base)
    lock_path = _safe_path(root, base / ".activation.lock")
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ReceiptError("activation lock must be regular")
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)

def _read_bytes(root: Path, path: Path, *, sync: bool = False) -> bytes:
    path = _safe_path(root, path)
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ReceiptError(f"not a regular file: {path}")
        chunks = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        if sync:
            os.fsync(fd)  # Sync the exact opened inode whose bytes were read.
            _fsync_dir(path.parent)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _self_hash(row: dict) -> dict:
    body = dict(row)
    body["evidence_sha256"] = _sha(_canonical(body))
    return body


def _verify_self_hash(row: dict) -> None:
    supplied = _digest(row.get("evidence_sha256"), "evidence_sha256")
    body = {key: value for key, value in row.items() if key != "evidence_sha256"}
    if supplied != _sha(_canonical(body)):
        raise ReceiptError("evidence_sha256 does not bind native row")


def _mkdirs(root: Path, path: Path) -> None:
    root = root.resolve(strict=True)
    path = _safe_path(root, path)
    relative = path.relative_to(root)
    cursor = root
    for part in relative.parts:
        parent = cursor
        cursor = cursor / part
        try:
            cursor.mkdir()
            _fsync_dir(parent)
        except FileExistsError:
            pass
        if stat.S_ISLNK(cursor.lstat().st_mode) or not cursor.is_dir():
            raise ReceiptError(f"unsafe receipt directory: {cursor}")


def _write_once(root: Path, path: Path, value: dict) -> bytes:
    path = _safe_path(root, path)
    _mkdirs(root, path.parent)
    payload = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False,
                         allow_nan=False).encode("utf-8") + b"\n"
    temp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(fd)
        os.link(temp, path, follow_symlinks=False)
        dirfd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    finally:
        os.close(fd)
        try:
            temp.unlink()
        except FileNotFoundError:
            pass
    return payload


def _signed(kind: str, fields: dict) -> dict:
    body = {"schema": SOURCE_SCHEMA, "event": kind, "classification": CLASSIFICATION,
            "support_scope": SUPPORT_SCOPE, **fields}
    body["evidence_sha256"] = _sha(_canonical(body))
    return body


def classify_receipt(row: object) -> dict:
    """Strictly verify an install or heartbeat row; return dependency-only classification."""
    if not isinstance(row, dict) or row.get("schema") != SOURCE_SCHEMA:
        raise ReceiptError("unsupported host-supervision receipt schema")
    _verify_self_hash(row)
    if row.get("classification") != CLASSIFICATION or row.get("support_scope") != SUPPORT_SCOPE:
        raise ReceiptError("receipt changed its dependency-only authority boundary")
    install_id = _uuid(row.get("install_id"))
    common = {"schema", "event", "classification", "support_scope", "install_id",
              "installed_at", "evidence_sha256"}
    installed = _aware(row.get("installed_at"), "installed_at")
    if row.get("event") == "installation_applied":
        fields = {"supervisor_pin", "installer_sha256", "registry_bytes_sha256",
                  "registry_projection_sha256", "crontab_backup_sha256",
                  "selected_cron_sha256", "registry_scope", "installer_path",
                  "registry_path", "crontab_backup_path", "selected_cron_entries", "heartbeat_at"}
        if set(row) != common | fields:
            raise ReceiptError("unexpected installation receipt fields")
        if not isinstance(row.get("supervisor_pin"), str) or not HEX40.fullmatch(row["supervisor_pin"]):
            raise ReceiptError("supervisor_pin must be a full commit id")
        for key in ("installer_sha256", "registry_bytes_sha256", "registry_projection_sha256",
                    "crontab_backup_sha256", "selected_cron_sha256"):
            _digest(row.get(key), key)
        if row.get("registry_scope") != "canonical_snapshot_only_not_deployment_proof":
            raise ReceiptError("registry snapshot must not be represented as deployed projection")
        for key in ("installer_path", "registry_path", "crontab_backup_path"):
            _relative(row.get(key))
        entries = row.get("selected_cron_entries")
        if not isinstance(entries, list) or len(entries) != 2 or any(
                not isinstance(item, str) or not item for item in entries):
            raise ReceiptError("selected cron entries must contain exactly the two supervision rows")
        if _sha(_canonical(entries)) != row["selected_cron_sha256"]:
            raise ReceiptError("selected cron digest does not bind selected entries")
        _cron_entries(entries, row["supervisor_pin"])
        if row.get("heartbeat_at") is not None:
            raise ReceiptError("installation event cannot carry a future heartbeat")
    elif row.get("event") == "first_heartbeat":
        if set(row) != common | {"heartbeat_at", "installation_evidence_sha256",
                                 "state_bytes_sha256", "state_path", "marker_created_at"}:
            raise ReceiptError("unexpected heartbeat receipt fields")
        marker_time = _aware(row.get("marker_created_at"), "marker_created_at")
        if marker_time < installed:
            raise ReceiptError("marker cannot predate installation")
        heartbeat = _aware(row.get("heartbeat_at"), "heartbeat_at")
        if heartbeat <= marker_time:
            raise ReceiptError("heartbeat must be strictly later than marker creation")
        _digest(row.get("installation_evidence_sha256"), "installation_evidence_sha256")
        _digest(row.get("state_bytes_sha256"), "state_bytes_sha256")
        _relative(row.get("state_path"))
    else:
        raise ReceiptError("unknown host-supervision event")
    return {"classification": CLASSIFICATION, "event": row["event"],
            "install_id": install_id, "evidence_sha256": row["evidence_sha256"],
            "performance_measurement": False, "corroborating_witness": False,
            "belief_measurement_emitted": False, "claim_tuple_emitted": False,
            "support_frame_emitted": False}



def _cron_entries(entries: list[str], supervisor_pin: str) -> None:
    if not isinstance(entries, list) or len(entries) != 2 or any(
            not isinstance(item, str) or not item or "\n" in item for item in entries):
        raise ReceiptError("exactly two selected cron entries are required")
    if sum("# epyc-op9-hub-supervisor" in item for item in entries) != 1 \
            or sum("# epyc-fw3-fleet-watch" in item for item in entries) != 1:
        raise ReceiptError("selected cron entries do not identify each expected supervision row")
    hub_line = next(item for item in entries if "# epyc-op9-hub-supervisor" in item)
    if not hub_line.endswith("# epyc-op9-hub-supervisor") or "# epyc-fw3-fleet-watch" in hub_line:
        raise ReceiptError("hub cron marker must be distinct and terminal")
    fw_line = next(item for item in entries if "# epyc-fw3-fleet-watch" in item)
    if not fw_line.endswith("# epyc-fw3-fleet-watch") or "# epyc-op9-hub-supervisor" in fw_line:
        raise ReceiptError("fleet cron marker must be distinct and terminal")
    if f"/hub-supervisor/{supervisor_pin}/scripts/dashboard/hub_supervisor.sh" not in hub_line:
        raise ReceiptError("selected hub cron line does not bind the requested supervisor pin")


def _registry_projection(data: bytes) -> str:
    registry = _json(data)
    observers = registry.get("observers") if isinstance(registry, dict) else None
    if not isinstance(observers, list):
        raise ReceiptError("observer registry has no observers array")
    selected = [item for item in observers if isinstance(item, dict)
                and isinstance(item.get("id"), str) and item["id"] in EXPECTED_OBSERVERS]
    if len(selected) != 2 or {item["id"] for item in selected} != EXPECTED_OBSERVERS:
        raise ReceiptError("registry must contain exactly one row per expected observer")
    return _sha(_canonical(sorted(selected, key=lambda item: item["id"])))


def preflight_capture(root: Path, installer_path: Path, registry_path: Path,
                      backup_dir: Path, installer_sha256: str) -> dict:
    """Read-only checks run as the future node writer before installer mutation."""
    root = root.resolve(strict=True)
    expected = root / "scripts/operator/install_supervision_cron_20260916.sh"
    if _safe_path(root, installer_path) != expected:
        raise ReceiptError("capture requires the canonical regular installer source")
    if _sha(_read_bytes(root, installer_path)) != _digest(installer_sha256, "installer_sha256"):
        raise ReceiptError("host and node installer source bytes differ")
    if _safe_path(root, registry_path) != root / "scripts/coordination/observer_registry.json":
        raise ReceiptError("capture requires canonical observer registry")
    _registry_projection(_read_bytes(root, registry_path))
    backup_dir = _safe_path(root, backup_dir)
    if not backup_dir.is_dir() or not os.access(backup_dir, os.W_OK | os.X_OK):
        raise ReceiptError("capture backup directory must exist and be writable by node")
    base = root / "logs/hygiene/host-supervision-activation"
    for child in ("pending", "consumed", ".activation.lock"):
        path = _safe_path(root, base / child)
        if path.exists():
            if child == ".activation.lock":
                _read_bytes(root, path)
                if not os.access(path, os.W_OK):
                    raise ReceiptError("activation lock must be writable by node")
            elif not path.is_dir() or not os.access(path, os.W_OK | os.X_OK):
                raise ReceiptError("marker directory must be writable by node")
    for path in (backup_dir, base):
        path = _safe_path(root, path)
        while not path.exists():
            path = path.parent
        if not path.is_dir() or not os.access(path, os.W_OK | os.X_OK):
            raise ReceiptError(f"receipt writer cannot use directory: {path}")
    return {"install_id": str(uuid.uuid4()), "installer_sha256": installer_sha256}

def capture_install(*, root: Path, install_id: str, supervisor_pin: str,
                    installer_path: Path, registry_path: Path, backup_path: Path,
                    selected_cron_entries: list[str], installer_sha256: str,
                    installed_at: str | None = None) -> Path:
    """Capture exact producer inputs after successful installer application and cron readback."""
    root = root.resolve(strict=True)
    if _safe_path(root, installer_path) != root / "scripts/operator/install_supervision_cron_20260916.sh":
        raise ReceiptError("capture requires canonical installer source")
    installed = installed_at or dt.datetime.now(dt.timezone.utc).isoformat()
    _aware(installed, "installed_at")
    if not isinstance(supervisor_pin, str) or not HEX40.fullmatch(supervisor_pin):
        raise ReceiptError("supervisor pin must be a full commit id")
    _digest(installer_sha256, "installer_sha256")
    _cron_entries(selected_cron_entries, supervisor_pin)
    installer_path = _safe_path(root, installer_path)
    registry_path = _safe_path(root, registry_path)
    backup_path = _safe_path(root, backup_path)
    installer_bytes = _read_bytes(root, installer_path)
    registry_bytes = _read_bytes(root, registry_path)
    backup_bytes = _read_bytes(root, backup_path)
    backup_fd = os.open(backup_path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        os.fsync(backup_fd)
    finally:
        os.close(backup_fd)
    _fsync_dir(backup_path.parent)
    if _sha(installer_bytes) != installer_sha256:
        raise ReceiptError("installer source changed between startup capture and receipt write")
    projection_sha = _registry_projection(registry_bytes)
    parsed_id = _uuid(install_id)
    fields = {
        "install_id": parsed_id, "installed_at": installed,
        "supervisor_pin": supervisor_pin,
        "installer_path": str(installer_path.relative_to(root)),
        "installer_sha256": installer_sha256,
        "registry_path": str(registry_path.relative_to(root)),
        "registry_bytes_sha256": _sha(registry_bytes),
        "registry_projection_sha256": projection_sha,
        "registry_scope": "canonical_snapshot_only_not_deployment_proof",
        "crontab_backup_path": str(backup_path.relative_to(root)),
        "crontab_backup_sha256": _sha(backup_bytes),
        "selected_cron_entries": selected_cron_entries,
        "selected_cron_sha256": _sha(_canonical(selected_cron_entries)),
        "heartbeat_at": None,
    }
    receipt = _signed("installation_applied", fields)
    classify_receipt(receipt)
    base = root / "logs" / "hygiene" / "host-supervision-activation"
    install_path = base / f"install-{parsed_id}.json"
    pending_path = base / "pending" / f"{parsed_id}.json"
    consumed_path = base / "consumed" / f"{parsed_id}.json"
    with _lock(root, base):
        if install_path.exists():
            existing_install = _json(_read_bytes(root, install_path))
            if existing_install != receipt:
                raise ReceiptError("existing installation receipt differs; preserve it")
        else:
            _write_once(root, install_path, receipt)
        if pending_path.exists() or consumed_path.exists():
            marker = _json(_read_bytes(root, pending_path if pending_path.exists() else consumed_path))
            _verify_marker(marker, install_path, receipt, root)
        else:
            marker = _signed("pending_first_heartbeat", {
                "install_id": parsed_id, "installed_at": installed,
                "marker_created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "installation_path": str(install_path.relative_to(root)),
                "installation_evidence_sha256": receipt["evidence_sha256"],
            })
            _verify_marker(marker, install_path, receipt, root)
            _write_once(root, pending_path, marker)
    return install_path



def _verify_marker(marker: object, install_path: Path, install: dict, root: Path) -> None:
    if not isinstance(marker, dict) or set(marker) != {
        "schema", "event", "classification", "support_scope", "evidence_sha256",
        "install_id", "installed_at", "marker_created_at", "installation_path",
        "installation_evidence_sha256",
    }:
        raise ReceiptError("malformed pending marker; preserve it")
    _verify_self_hash(marker)
    if marker["schema"] != SOURCE_SCHEMA or marker["event"] != "pending_first_heartbeat" \
            or marker["classification"] != CLASSIFICATION or marker["support_scope"] != SUPPORT_SCOPE:
        raise ReceiptError("pending marker authority/schema changed")
    if _uuid(marker["install_id"]) != install["install_id"] \
            or marker["installed_at"] != install["installed_at"] \
            or _relative(marker["installation_path"]) != str(install_path.relative_to(root)) \
            or marker["installation_evidence_sha256"] != install["evidence_sha256"]:
        raise ReceiptError("pending marker does not bind exact installation")
    if _aware(marker["marker_created_at"], "marker_created_at") < _aware(install["installed_at"], "installed_at"):
        raise ReceiptError("marker predates installation")


def capture_pending_heartbeat(root: Path, state_path: Path, heartbeat_at: str) -> list[Path]:
    """Consume the first eligible post-marker durable state observed by this hook.

    The exact opened state inode and parent directory are synced before eligibility.
    This records successful sync calls, not a power-loss witness. It does not guarantee
    the first physical heartbeat or exclude a publication race.
    LR8 owns callback integration; merely importing this module activates no hook.
    """
    root = root.resolve(strict=True)
    base = root / "logs/hygiene/host-supervision-activation"
    pending_dir = _safe_path(root, base / "pending")
    if not pending_dir.exists() or not list(pending_dir.glob("*.json")):
        return []  # No state read, sync, lock or native write without a marker.
    results = []
    with _lock(root, base):
        pending_paths = sorted(pending_dir.glob("*.json"))
        if not pending_paths:
            return []
        state_path = _safe_path(root, state_path)
        state_bytes = _read_bytes(root, state_path, sync=True)
        state = _json(state_bytes)
        if not isinstance(state, dict) or state.get("heartbeat_at") != heartbeat_at:
            raise ReceiptError("synced state does not match requested heartbeat timestamp")
        actual_heartbeat = _aware(heartbeat_at, "heartbeat_at")
        for marker_path in pending_paths:
            install_id = _uuid(marker_path.stem)
            marker_bytes = _read_bytes(root, marker_path)
            marker = _json(marker_bytes)
            install_path = base / f"install-{install_id}.json"
            install_row = _json(_read_bytes(root, install_path))
            if classify_receipt(install_row)["event"] != "installation_applied":
                raise ReceiptError("marker target is not installation evidence")
            _verify_marker(marker, install_path, install_row, root)
            receipt_path = base / f"heartbeat-{install_id}.json"
            if receipt_path.exists():
                existing = _json(_read_bytes(root, receipt_path))
                prior = classify_receipt(existing)
                if prior["event"] != "first_heartbeat" or existing["install_id"] != install_id \
                        or existing["installed_at"] != install_row["installed_at"] \
                        or existing["marker_created_at"] != marker["marker_created_at"] \
                        or existing["installation_evidence_sha256"] != install_row["evidence_sha256"]:
                    raise ReceiptError("existing heartbeat does not bind this marker/installation")
            else:
                if actual_heartbeat <= _aware(marker["marker_created_at"], "marker_created_at"):
                    continue  # Noneligible states leave the marker available for a later tick.
                row = _signed("first_heartbeat", {
                    "install_id": install_id, "installed_at": install_row["installed_at"],
                    "marker_created_at": marker["marker_created_at"], "heartbeat_at": heartbeat_at,
                    "installation_evidence_sha256": install_row["evidence_sha256"],
                    "state_path": str(state_path.relative_to(root)), "state_bytes_sha256": _sha(state_bytes),
                })
                classify_receipt(row)
                _write_once(root, receipt_path, row)
            consumed_dir = _safe_path(root, base / "consumed")
            _mkdirs(root, consumed_dir)
            consumed = consumed_dir / marker_path.name
            try:
                os.link(marker_path, consumed, follow_symlinks=False)
            except FileExistsError:
                if _read_bytes(root, consumed) != marker_bytes:
                    raise ReceiptError("consumed marker differs; preserve both")
            _fsync_dir(consumed_dir)
            marker_path.unlink()
            _fsync_dir(pending_dir)
            results.append(receipt_path)
    return results

def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    cap = sub.add_parser("capture-install")
    cap.add_argument("--root", type=Path, required=True)
    cap.add_argument("--install-id", required=True)
    cap.add_argument("--supervisor-pin", required=True)
    cap.add_argument("--installer", type=Path, required=True)
    cap.add_argument("--installer-sha256", required=True)
    cap.add_argument("--registry", type=Path, required=True)
    cap.add_argument("--backup", type=Path, required=True)
    cap.add_argument("--selected-cron-entry", action="append", required=True)
    pre = sub.add_parser("preflight")
    pre.add_argument("--root", type=Path, required=True)
    pre.add_argument("--installer", type=Path, required=True)
    pre.add_argument("--installer-sha256", required=True)
    pre.add_argument("--registry", type=Path, required=True)
    pre.add_argument("--backup-dir", type=Path, required=True)
    cls = sub.add_parser("classify")
    cls.add_argument("receipt", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "preflight":
            result = preflight_capture(args.root, args.installer, args.registry,
                                       args.backup_dir, args.installer_sha256)
            print(result["install_id"])
        elif args.command == "capture-install":
            path = capture_install(root=args.root, install_id=args.install_id,
                supervisor_pin=args.supervisor_pin, installer_path=args.installer,
                registry_path=args.registry, backup_path=args.backup,
                selected_cron_entries=args.selected_cron_entry,
                installer_sha256=args.installer_sha256)
            print(path)
        else:
            row = _json(args.receipt.read_bytes())
            print(json.dumps(classify_receipt(row), sort_keys=True))
    except (OSError, ValueError, ReceiptError) as exc:
        print(f"host-supervision receipt error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))


__all__ = ["CLASSIFICATION", "SOURCE_SCHEMA", "ReceiptError", "capture_install",
           "capture_pending_heartbeat", "classify_receipt"]
