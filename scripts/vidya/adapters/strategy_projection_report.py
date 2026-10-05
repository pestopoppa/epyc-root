"""Strict private reader for one prospective StrategyStore report capture."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

SCHEMA = "epyc.strategy_projection_report_capture.v1"
REQUEST_SCHEMA = "epyc.strategy_projection_report_request.v1"
ADAPTER_ID = "vidya.adapters.strategy_projection_report/v1"
AUTHORITY = "strategy_projection_report_integrity_only"
PROPOSITION = (
    "The original StrategyStore projection report recorded report.ok as the exact boolean "
    "result of its journal-derived projection comparison; counts are descriptive only."
)
# Set to the source hash of the reviewed, immutable native producer before source publication.
TRUSTED_PRODUCER_SHA256 = "78feefe306ebd48b8d0dfaddb8be4b8907d9da227495aed896a88eaba2a304db"
TRUSTED_APP_SOURCES = {
    "report-source.bin": "08286a31d98404758b7d09eecc5a2ab90181bf63484f66566361906c0e7d1f1b",
    "journal-source.bin": "f5f29d0d99311e45b4f0aa50f812622993fe714f7652218e86c2906c1135d756",
    "shards-source.bin": "d7ed426ccc3972b6950f23a1af0e26ae6ed5e3e9dde7e6401f963cd63923adda",
    "store-source.bin": "8a5cd857d9723827ec2f5346057aa89d5ec358a2fdceeaf7a4566e2ae7889f64",
    "faiss-source.bin": "ac73aade178f0a13430c3ea01cd50d7c971e6059817673d3976fd13347f6f39d",
    "embedder-source.bin": "4697fd6f877fd1a1d9792c78300319c4bae96b75309e5a71b9f921354bb4bf75",
    "memory-record-source.bin": "7a41ca1bc46febe0efbaaa1a6b96f84e40b4338d6a690dae0ca09b9e7d85fe2b",
    "src-package-source.bin": "16e20bce77e6470646b90def0e3d653a3bd9fb024b484f7cd034f96ff8a0a5f8",
    "lock-source.bin": "642b6a902a8c45949402d23aaf3237327619d338ee80f27f141ecb0dbb49f2c0",
    "tier-spec-source.bin": "89ee24c066c8bed1b18a4c6c577fef530a447abd3db9fbf0fd308974ea18d095",
}
APP_ARTIFACTS = set(TRUSTED_APP_SOURCES)
ARTIFACT_LIMITS = {
    "execution-request.json": 2 * 1024 * 1024,
    "producer-source.bin": 8 * 1024 * 1024,
    **{name: 8 * 1024 * 1024 for name in APP_ARTIFACTS},
    "stdout.bin": 32 * 1024 * 1024,
    "stderr.bin": 32 * 1024 * 1024,
    "report-markdown.bin": 32 * 1024 * 1024,
    "terminal.json": 1024 * 1024,
    "post-input-identity.json": 4 * 1024 * 1024,
}
ARTIFACT_NAMES = set(ARTIFACT_LIMITS)
RECEIPT_FIELDS = {"schema", "capture_id", "applicability", "started_utc", "ended_utc",
                  "execution_started", "exit_code", "exception_type", "report_ok",
                  "integrity_proposition", "custody_complete", "post_identity_error",
                  "capture_complete",
                  "request", "stdout", "stderr", "terminal", "report_markdown",
                  "post_input_identity", "receipt_sha256"}
REQUEST_FIELDS = {"schema", "capture_id", "started_utc", "producer_source",
                  "applicability", "application_root", "application_sources", "input_roots",
                  "declared_inputs", "mode",
                  "integrity_proposition", "input_claim", "exclusions"}
EXCLUSIONS = ["transitive dependency completeness", "environment contents",
              "embedding quality", "historical pre-hook output", "whole-host health",
              "immutable SQLite snapshot", "auxiliary StrategyStore temporary-file cleanup"]


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _strict_json(raw: bytes) -> Any:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON member")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _x: (_ for _ in ()).throw(ValueError("non-finite JSON")))


def _private_chain(path: Path) -> None:
    absolute = Path(os.path.abspath(path))
    for candidate in (Path("/"), *absolute.parents[::-1], absolute):
        info = candidate.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ValueError("private custody chain contains a symlink or non-directory")
        if info.st_uid not in (0, os.geteuid()):
            raise ValueError("private custody chain has an untrusted owner")
        if stat.S_IMODE(info.st_mode) & 0o022 and not (
                info.st_uid == 0 and info.st_mode & stat.S_ISVTX):
            raise ValueError("private custody chain has a writable untrusted ancestor")


def _read_regular(path: Path, limit: int) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) not in (0o400, 0o600)):
            raise ValueError("artifact is not an owned private regular file")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            raw = handle.read(limit + 1)
        if len(raw) > limit:
            raise ValueError("artifact exceeds its bounded byte limit")
        return raw
    finally:
        os.close(fd)


def _artifact(run_dir: Path, ref: Any) -> bytes:
    if (not isinstance(ref, dict) or set(ref) != {"name", "sha256", "size"}
            or ref["name"] not in ARTIFACT_NAMES or type(ref["size"]) is not int
            or ref["size"] < 0 or not isinstance(ref["sha256"], str)
            or len(ref["sha256"]) != 64):
        raise ValueError("malformed artifact reference")
    raw = _read_regular(run_dir / ref["name"], ARTIFACT_LIMITS[ref["name"]])
    if len(raw) != ref["size"] or _sha(raw) != ref["sha256"]:
        raise ValueError("original artifact bytes differ from their receipt reference")
    return raw


def _utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("capture timestamps must be UTC strings")
    return datetime.fromisoformat(value[:-1] + "+00:00")


def _is_uuid_hex(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 32:
        return False
    try:
        return uuid.UUID(hex=value).hex == value
    except ValueError:
        return False


def _validate_inputs(rows: Any, roots: list[dict]) -> None:
    if not isinstance(rows, list) or len(rows) > 4101:
        raise ValueError("declared input identities must be a bounded list")
    paths = set()
    shard_roles = []
    shard_paths = []
    fixed_roles = []
    fixed_members = {"sqlite-db": "strategies.db", "sqlite-wal": "strategies.db-wal",
                     "sqlite-shm": "strategies.db-shm",
                     "faiss-index": "strategy_embeddings.faiss",
                     "faiss-id-map": "strategy_id_map.npy"}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("declared input identity is not an object")
        role = row.get("role")
        expected = {"role", "path", "state"}
        if row.get("state") == "present":
            expected |= {"sha256", "size", "device", "inode", "mtime_ns"}
        if set(row) != expected or not isinstance(role, str):
            raise ValueError("declared input identity fields are incomplete or unknown")
        path = row.get("path")
        if not isinstance(path, str) or not Path(path).is_absolute() or path in paths:
            raise ValueError("declared input paths must be unique absolute paths")
        paths.add(path)
        if role.startswith("journal-shard-"):
            shard_roles.append(role)
            shard_paths.append(path)
            if row["state"] != "present":
                raise ValueError("listed journal shard cannot be absent")
        elif role in {"sqlite-db", "sqlite-wal", "sqlite-shm", "faiss-index", "faiss-id-map"}:
            fixed_roles.append(role)
            if Path(path).name != fixed_members[role]:
                raise ValueError("store input role does not bind its canonical member name")
        else:
            raise ValueError("undeclared input role")
        if row["state"] not in {"present", "absent"}:
            raise ValueError("invalid declared input state")
        if row["state"] == "present":
            if (not isinstance(row["sha256"], str)
                    or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"])
                    or type(row["size"]) is not int or row["size"] < 0
                    or type(row["device"]) is not int or type(row["inode"]) is not int
                    or type(row["mtime_ns"]) is not int):
                raise ValueError("present input identity has invalid metadata")
    if len(fixed_roles) != 5 or set(fixed_roles) != {
            "sqlite-db", "sqlite-wal", "sqlite-shm", "faiss-index", "faiss-id-map"}:
        raise ValueError("store input roles must bind the exact SQLite and FAISS member set")
    if shard_roles != [f"journal-shard-{i}" for i in range(len(shard_roles))]:
        raise ValueError("journal shard roles are not a contiguous ordered list")
    shard_pattern = re.compile(r"^autopilot_journal(?:_(\d+))?\.jsonl$")
    batch_ids = []
    for shard in shard_paths:
        match = shard_pattern.fullmatch(shard.name)
        if match is None:
            raise ValueError("journal input has a noncanonical shard filename")
        batch = 0 if match.group(1) is None else int(match.group(1))
        if match.group(1) is not None and match.group(1) != str(batch):
            raise ValueError("journal shard suffix is noncanonical")
        if batch == 0 and match.group(1) is not None:
            raise ValueError("batch zero must use the base journal filename")
        batch_ids.append(batch)
    if batch_ids != sorted(batch_ids) or len(batch_ids) != len(set(batch_ids)):
        raise ValueError("journal shard identities are duplicated or out of order")
    roots_by_role = {row["role"]: Path(row["path"]) for row in roots}
    for row in rows:
        path = Path(row["path"])
        if row["role"].startswith("journal-shard-"):
            if path.parent != roots_by_role["journal-directory"]:
                raise ValueError("journal shard path is outside its declared root")
        else:
            if path.parent != roots_by_role["strategy-store-directory"]:
                raise ValueError("store member path is outside its declared root")


def _validate_post_identity(raw: bytes, record: dict, request: dict) -> bool:
    post = _strict_json(raw[:-1] if raw.endswith(b"\n") else raw)
    if (not isinstance(post, dict)
            or set(post) != {"schema", "capture_id", "captured_utc", "roots", "files",
                             "application_source_sha256"}
            or raw != _canonical(post) + b"\n"
            or post["schema"] != SCHEMA + ".input-identity"
            or post["capture_id"] != record["capture_id"]):
        raise ValueError("post-call input identity capsule is malformed")
    _utc(post["captured_utc"])
    roots = post["roots"]
    if (not isinstance(roots, list) or len(roots) != 2
            or any(not isinstance(row, dict) for row in roots)
            or {row.get("role") for row in roots} !=
            {"journal-directory", "strategy-store-directory"}):
        raise ValueError("post-call roots do not bind the journal and store")
    for root in roots:
        if (set(root) != {"role", "path", "device", "inode", "mtime_ns"}
                or type(root["device"]) is not int or type(root["inode"]) is not int
                or type(root["mtime_ns"]) is not int or not Path(root["path"]).is_absolute()):
            raise ValueError("post-call root identity is malformed")
    _validate_inputs(post["files"], roots)
    pre_roots = {row["role"]: row for row in request["input_roots"]}
    post_roots = {row["role"]: row for row in roots}
    if any(pre_roots[role]["path"] != post_roots[role]["path"]
           or pre_roots[role]["device"] != post_roots[role]["device"]
           or pre_roots[role]["inode"] != post_roots[role]["inode"]
           for role in pre_roots):
        raise ValueError("input root path or inode changed during the report invocation")
    pre_journal = [row for row in request["declared_inputs"]
                   if row["role"].startswith("journal-shard-")]
    post_journal = [row for row in post["files"]
                    if row["role"].startswith("journal-shard-")]
    journal_stable = (pre_roots["journal-directory"] == post_roots["journal-directory"]
                      and pre_journal == post_journal)
    pre_source_hashes = {name: ref["sha256"] for name, ref in request["application_sources"].items()}
    source_stable = post["application_source_sha256"] == pre_source_hashes
    return journal_stable and source_stable


def read_receipt(path: str | Path) -> tuple[dict, str]:
    receipt_path = Path(os.path.abspath(path))
    if receipt_path.name != "receipt.json":
        raise ValueError("receipt must use its canonical filename")
    run_dir = receipt_path.parent
    _private_chain(run_dir)
    info = run_dir.lstat()
    if (info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700
            or not _is_uuid_hex(run_dir.name)):
        raise ValueError("capture directory must be UUID-named, owned, and private (0700)")
    raw = _read_regular(receipt_path, 1024 * 1024)
    record = _strict_json(raw)
    if not isinstance(record, dict) or set(record) != RECEIPT_FIELDS or record.get("schema") != SCHEMA:
        raise ValueError("foreign or incomplete StrategyStore report receipt")
    claimed = record["receipt_sha256"]
    unsigned = dict(record)
    unsigned.pop("receipt_sha256")
    digest = _sha(_canonical(unsigned))
    if claimed != digest or raw != _canonical(record) + b"\n":
        raise ValueError("receipt self-hash or canonical encoding mismatch")
    if record["capture_id"] != run_dir.name or not _is_uuid_hex(record["capture_id"]):
        raise ValueError("receipt UUID does not bind its original directory")
    started, ended = _utc(record["started_utc"]), _utc(record["ended_utc"])
    if ended < started or type(record["execution_started"]) is not bool:
        raise ValueError("terminal time or execution-start binding is invalid")
    if record["applicability"] not in {"captured_cli", "synthetic_fixture"}:
        raise ValueError("undeclared capture applicability")
    for key in ("exit_code", "exception_type"):
        value = record[key]
        if key == "exit_code" and value is not None and type(value) is not int:
            raise ValueError("original CLI status must be an integer or null")
        if key == "exception_type" and value is not None and not isinstance(value, str):
            raise ValueError("exception type must be a string or null")
    for key in ("exception_type", "post_identity_error"):
        value = record[key]
        if value is not None and (not isinstance(value, str)
                                  or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.]{0,127}", value)):
            raise ValueError("diagnostic codes must be bounded type names")
    if record["report_ok"] is not None and type(record["report_ok"]) is not bool:
        raise ValueError("report.ok must remain a strict boolean or null")
    if type(record["custody_complete"]) is not bool:
        raise ValueError("custody completeness must be a strict boolean")
    if type(record["capture_complete"]) is not bool:
        raise ValueError("capture completeness must be a strict boolean")
    request_raw = _artifact(run_dir, record["request"])
    if record["request"]["name"] != "execution-request.json":
        raise ValueError("request artifact has a noncanonical name")
    request = _strict_json(request_raw[:-1] if request_raw.endswith(b"\n") else request_raw)
    if (not isinstance(request, dict) or set(request) != REQUEST_FIELDS
            or request_raw != _canonical(request) + b"\n"
            or request["schema"] != REQUEST_SCHEMA
            or request["capture_id"] != record["capture_id"]
            or request["started_utc"] != record["started_utc"]
            or request["applicability"] != record["applicability"]
            or request["integrity_proposition"] != PROPOSITION
            or request["input_claim"] != "hash_only_declared_identity_no_transitive_completeness"
            or request["exclusions"] != EXCLUSIONS):
        raise ValueError("pre-call request is incomplete or contradicts the terminal receipt")
    if (not isinstance(request["mode"], dict)
            or set(request["mode"]) != {"write_missing", "allow_hash_fallback", "strict"}
            or type(request["mode"]["write_missing"]) is not bool
            or type(request["mode"]["allow_hash_fallback"]) is not bool
            or request["mode"]["strict"] is not True):
        raise ValueError("capture mode fields are invalid")
    roots = request["input_roots"]
    if (not isinstance(roots, list) or len(roots) != 2
            or any(not isinstance(row, dict) for row in roots)
            or {row.get("role") for row in roots} !=
            {"journal-directory", "strategy-store-directory"}):
        raise ValueError("input roots must bind the journal and store directories")
    for root in roots:
        if (set(root) != {"role", "path", "device", "inode", "mtime_ns"}
                or not isinstance(root["path"], str) or not Path(root["path"]).is_absolute()
                or any(type(root[key]) is not int for key in ("device", "inode", "mtime_ns"))):
            raise ValueError("input root identity is malformed")
    if roots[0]["path"] == roots[1]["path"]:
        raise ValueError("journal and strategy-store roots must be distinct")
    if (not isinstance(request["application_root"], str)
            or not Path(request["application_root"]).is_absolute()):
        raise ValueError("application source root must be an absolute path")
    _validate_inputs(request["declared_inputs"], roots)
    source_refs = request["application_sources"]
    if not isinstance(source_refs, dict) or set(source_refs) != APP_ARTIFACTS:
        raise ValueError("trusted application source set is incomplete")
    for name, ref in source_refs.items():
        if not isinstance(ref, dict) or ref.get("name") != name:
            raise ValueError("application source snapshot reference is invalid")
        _artifact(run_dir, ref)
        if ref["sha256"] != TRUSTED_APP_SOURCES[name]:
            raise ValueError("application source snapshot differs from trusted reviewed identity")
    producer_bytes = _artifact(run_dir, request["producer_source"])
    if (request["producer_source"]["name"] != "producer-source.bin"
            or TRUSTED_PRODUCER_SHA256 == "PENDING"
            or _sha(producer_bytes) != TRUSTED_PRODUCER_SHA256):
        raise ValueError("native producer is not pinned to a reviewed implementation")
    stdout = _artifact(run_dir, record["stdout"])
    stderr = _artifact(run_dir, record["stderr"])
    if record["stdout"]["name"] != "stdout.bin" or record["stderr"]["name"] != "stderr.bin":
        raise ValueError("captured standard streams have noncanonical artifact names")
    terminal_raw = _artifact(run_dir, record["terminal"])
    if record["terminal"]["name"] != "terminal.json":
        raise ValueError("terminal artifact has a noncanonical name")
    terminal = _strict_json(terminal_raw[:-1] if terminal_raw.endswith(b"\n") else terminal_raw)
    expected_terminal = {"schema": SCHEMA + ".terminal", "capture_id": record["capture_id"],
                         "started_utc": record["started_utc"], "ended_utc": record["ended_utc"],
                         "execution_started": record["execution_started"],
                         "exit_code": record["exit_code"], "exception_type": record["exception_type"],
                         "custody_complete": record["custody_complete"],
                         "capture_complete": record["capture_complete"],
                         "post_identity_error": record["post_identity_error"]}
    if (terminal_raw != _canonical(terminal) + b"\n"
            or set(terminal) != set(expected_terminal) or terminal != expected_terminal):
        raise ValueError("original terminal sidecar contradicts receipt status")
    post_ref = record["post_input_identity"]
    journal_source_stable = False
    if post_ref is not None:
        post_raw = _artifact(run_dir, post_ref)
        if post_ref["name"] != "post-input-identity.json":
            raise ValueError("post-call identity artifact is misnamed")
        journal_source_stable = _validate_post_identity(post_raw, record, request)
    if record["custody_complete"]:
        if record["post_identity_error"] is not None or not isinstance(post_ref, dict):
            raise ValueError("complete custody lacks an original post-call input identity")
        if not journal_source_stable:
            raise ValueError("complete custody contradicts the original journal/source post-identity")
    elif record["post_identity_error"] is None:
        raise ValueError("incomplete custody must preserve its post-identity failure")
    elif post_ref is not None and journal_source_stable:
        raise ValueError("incomplete custody lacks demonstrated journal/source drift")
    if record["capture_complete"] and not record["custody_complete"]:
        raise ValueError("complete capture cannot have incomplete custody")
    if record["report_ok"] is None:
        if record["integrity_proposition"] is not None:
            raise ValueError("diagnostic/null capture cannot carry a proposition")
        if record["execution_started"]:
            if record["exit_code"] is None and record["exception_type"] is None:
                raise ValueError("incomplete execution lacks its original exception or CLI status")
        elif record["exit_code"] is not None or record["exception_type"] is None:
            raise ValueError("pre-execution diagnostic has contradictory terminal fields")
    else:
        if record["integrity_proposition"] != PROPOSITION:
            raise ValueError("original report proposition is incomplete")
        if record["report_ok"] not in (True, False):
            raise ValueError("report result is not a strict boolean")
        if record["exit_code"] != (0 if record["report_ok"] else 1):
            raise ValueError("captured strict CLI return code contradicts original report.ok")
        if not stdout.endswith(b"\n") or b"\n" in stdout[:-1]:
            raise ValueError("original CLI stdout is not exactly one JSON line")
        report = _strict_json(stdout[:-1])
        if (not isinstance(report, dict)
                or type(report.get("ok")) is not bool or report["ok"] is not record["report_ok"]):
            raise ValueError("original CLI JSON does not carry the exact captured report.ok")
        if record["execution_started"] is not True or not Path(request["application_root"]).is_absolute():
            raise ValueError("captured application root identity is malformed")
    if record["report_markdown"] is not None:
        markdown = _artifact(run_dir, record["report_markdown"])
        if record["report_markdown"]["name"] != "report-markdown.bin" or not markdown:
            raise ValueError("preserved markdown artifact is invalid")
    if record["capture_complete"] and (record["report_ok"] is None
                                         or record["report_markdown"] is None
                                         or record["exception_type"] is not None):
        raise ValueError("complete capture lacks the original report outputs")
    return record, digest


def public_locator(path: str | Path) -> str:
    try:
        record, digest = read_receipt(_receipt_path(path))
        return "strategy-projection-report:" + record["capture_id"] + ":" + digest[:16]
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return "strategy-projection-report:unresolved"


def native_rows(path: str | Path) -> tuple[dict, ...]:
    try:
        receipt_path = _receipt_path(path)
        record, digest = read_receipt(receipt_path)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, json.JSONDecodeError):
        raise ProjectionError("StrategyStore report custody refused") from None
    if not record["capture_complete"] or record["report_ok"] is None:
        return ()
    return ({"record": record, "receipt_path": str(receipt_path),
             "receipt_sha256": digest},)


def _receipt_path(path: str | Path) -> Path:
    candidate = Path(path).absolute()
    return candidate if candidate.name == "receipt.json" else candidate / "receipt.json"


@register("strategy-projection-report", source_class="verifier",
          decided_proposition_field="integrity_proposition")
def project_strategy_projection_report(native: dict) -> ClaimTuple:
    try:
        rows = native_rows(native["receipt_path"])
        if len(rows) != 1 or rows[0] != native:
            raise ValueError("receipt changed after original read")
        record = native["record"]
        value = record["report_ok"]
        if type(value) is not bool or record["integrity_proposition"] != PROPOSITION:
            raise ValueError("original report integrity proposition is incomplete")
        request, _ = _request_for_native(native["receipt_path"])
        return ClaimTuple(
            measurement_id="strategy-projection-report:" + native["receipt_sha256"],
            metric="strategy_projection_report_ok", value=value,
            date=record["ended_utc"], category="CANDIDATE", metric_direction="higher_better",
            protocol_id="", claim=PROPOSITION, decided_proposition=PROPOSITION,
            source_class="verifier", source_kind=ADAPTER_ID, binding_kind="identity",
            attestation_locator=public_locator(native["receipt_path"]),
            extra={"receipt_sha256": native["receipt_sha256"],
                   "capture_id": record["capture_id"], "applicability": record["applicability"],
                   "write_missing": request["mode"]["write_missing"],
                   "allow_hash_fallback": request["mode"]["allow_hash_fallback"],
                   "input_claim": request["input_claim"],
                   "exclusions": request["exclusions"]})
    except (KeyError, TypeError, ValueError, OSError, ProjectionError):
        raise ProjectionError("StrategyStore report projection refused") from None


def _request_for_native(path: str | Path) -> tuple[dict, str]:
    record, digest = read_receipt(path)
    request = _strict_json(_artifact(Path(path).absolute().parent, record["request"]).rstrip(b"\n"))
    return request, digest
