"""Project only prospective named managed-interpreter import check receipts."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
from claim_tuple import ClaimTuple, ProjectionError, register

SCHEMA = "epyc.managed_tooling_check.v1"
ADAPTER_ID = "vidya.adapters.managed_tooling_check/v1"
AUTHORITY = "named_managed_import_check_no_promotion"
TRUSTED_PRODUCER_SHA256 = "8d5858cbedd35cdb3bd805943eaf781d4b73d743591d976232877197aec63c14"
TRUSTED_DRIVER_SHA256 = "12814b698fc6b2417cc7247d691f05a7f0d0aac36f4bfa18d527177fc10da396"
ALLOWED_CHECKS = {"epyc-orchestrator-pytest-import", "epyc-inference-research-pytest-import"}
EXCLUSIONS = ["transitive dependency completeness", "ambient environment contents",
              "whole-host health", "installation or repair outcome",
              "historical or pre-hook output"]
RECEIPT_FIELDS = {"schema", "check_id", "module_name", "requested_interpreter",
                  "requested_interpreter_realpath", "interpreter_prebind", "check_source",
                  "started_utc", "ended_utc",
                  "execution_started", "exit_code", "child_timed_out", "child_cleanup_ok",
                  "child_pid",
                  "verdict", "diagnostic", "interpreter",
                  "module", "stdout", "stderr", "import_error", "import_succeeded",
                  "metadata_error", "argv", "request", "decided_proposition", "exclusions",
                  "child_metadata", "child_terminal",
                  "producer", "import_driver_sha256", "argv_template", "receipt_sha256"}
ARTIFACT_NAMES = {"execution-request.json", "check-source.bin", "producer-source.bin",
                  "import-driver.bin", "stdout.bin", "stderr.bin", "child-metadata.bin",
                  "child-terminal.json"}


def _regular_bytes(path: Path, limit: int = 20 * 1024 * 1024) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) not in (0o400, 0o600)):
            raise ValueError("artifact is not a regular file")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            data = handle.read(limit + 1)
        if len(data) > limit:
            raise ValueError("artifact exceeds bounded size")
        return data
    finally:
        os.close(fd)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _artifact(run_dir: Path, reference: dict) -> bytes:
    if (not isinstance(reference, dict) or set(reference) != {"name", "sha256", "size"}
            or not isinstance(reference["name"], str) or reference["name"] not in ARTIFACT_NAMES
            or not isinstance(reference["sha256"], str) or len(reference["sha256"]) != 64
            or not isinstance(reference["size"], int) or reference["size"] < 0):
        raise ValueError("malformed artifact reference")
    data = _regular_bytes(run_dir / reference["name"])
    if len(data) != reference["size"] or _sha(data) != reference["sha256"]:
        raise ValueError("artifact bytes do not match their producer pin")
    return data


def read_receipt(path: str | Path) -> tuple[dict, str]:
    receipt_path = Path(path).absolute()
    run_dir = receipt_path.parent
    directory_info = run_dir.lstat()
    if (not stat.S_ISDIR(directory_info.st_mode) or directory_info.st_uid != os.geteuid()
            or stat.S_IMODE(directory_info.st_mode) != 0o700):
        raise ValueError("receipt run directory must be an owned private directory (mode 0700)")
    raw = _regular_bytes(receipt_path)
    record = json.loads(raw)
    if not isinstance(record, dict) or record.get("schema") != SCHEMA:
        raise ValueError("foreign managed-tooling receipt")
    if set(record) != RECEIPT_FIELDS:
        raise ValueError("receipt fields are incomplete or undeclared")
    claimed_digest = record.get("receipt_sha256")
    without_digest = dict(record)
    without_digest.pop("receipt_sha256", None)
    digest = _sha(_canonical(without_digest))
    if claimed_digest != digest or raw != _canonical(record):
        raise ValueError("receipt self-hash or canonical encoding mismatch")
    if record.get("check_id") not in ALLOWED_CHECKS or record.get("module_name") != "pytest":
        raise ValueError("undeclared managed tooling check")
    if record.get("exclusions") != EXCLUSIONS:
        raise ValueError("managed-tooling claim scope exclusions changed")
    if (not isinstance(record.get("execution_started"), bool)
            or not isinstance(record.get("child_timed_out"), bool)
            or not isinstance(record.get("child_cleanup_ok"), bool)
            or (record.get("child_pid") is not None
                and (not isinstance(record["child_pid"], int)
                     or isinstance(record["child_pid"], bool)
                     or record["child_pid"] <= 0))
            or (record.get("exit_code") is not None
                and (not isinstance(record["exit_code"], int)
                     or isinstance(record["exit_code"], bool)))):
        raise ValueError("child terminal status fields have invalid types")
    if (record["execution_started"] != (record["child_pid"] is not None)
            or (record["child_timed_out"] and not record["execution_started"])
            or (not record["execution_started"] and record["exit_code"] is not None)):
        raise ValueError("child PID, launch boundary, timeout, and exit status disagree")
    for field in ("started_utc", "ended_utc"):
        value = record.get(field)
        if not isinstance(value, str) or not value.endswith("Z"):
            raise ValueError(f"missing {field}")
        datetime.fromisoformat(value[:-1] + "+00:00")
    if datetime.fromisoformat(record["ended_utc"][:-1] + "+00:00") < datetime.fromisoformat(
            record["started_utc"][:-1] + "+00:00"):
        raise ValueError("capture end precedes start")
    terminal_bytes = _artifact(run_dir, record.get("child_terminal"))
    if record["child_terminal"]["name"] != "child-terminal.json":
        raise ValueError("child terminal sidecar has a noncanonical name")
    terminal = json.loads(terminal_bytes)
    expected_terminal = {"schema": "epyc.managed_tooling_child_terminal.v1",
                         "check_id": record["check_id"], "started_utc": record["started_utc"],
                         "ended_utc": record["ended_utc"],
                         "execution_started": record["execution_started"],
                         "exit_code": record["exit_code"],
                         "timed_out": record["child_timed_out"],
                         "cleanup_ok": record["child_cleanup_ok"],
                         "child_pid": record["child_pid"],
                         "argv": record["argv"]}
    if (terminal_bytes != _canonical(terminal) or terminal_bytes != _canonical(expected_terminal)
            or set(terminal) != set(expected_terminal)):
        raise ValueError("original child terminal sidecar contradicts the receipt")
    child_metadata = None
    if record.get("child_metadata") is not None:
        if record["child_metadata"].get("name") != "child-metadata.bin":
            raise ValueError("child metadata sidecar has a noncanonical name")
        child_metadata_bytes = _artifact(run_dir, record["child_metadata"])
        if child_metadata_bytes:
            try:
                child_metadata = json.loads(child_metadata_bytes)
            except (json.JSONDecodeError, UnicodeDecodeError):
                child_metadata = None
            if child_metadata is not None and child_metadata_bytes != _canonical(child_metadata):
                raise ValueError("child metadata sidechannel is not canonical JSON")
    if child_metadata is not None:
        if not isinstance(child_metadata, dict) or set(child_metadata) != {
                "python", "module", "import_error", "import_succeeded", "metadata_error"}:
            raise ValueError("original child metadata fields are incomplete or undeclared")
        expected_metadata = {"python": record.get("interpreter"),
                             "module": record.get("module"),
                             "import_error": record.get("import_error"),
                             "import_succeeded": record.get("import_succeeded"),
                             "metadata_error": record.get("metadata_error")}
        if child_metadata_bytes != _canonical(expected_metadata):
            raise ValueError("receipt metadata differs from original child metadata bytes")
        if (not isinstance(child_metadata["module"], dict)
                or child_metadata["module"].get("name") != record["module_name"]):
            raise ValueError("original child metadata names a different imported module")
    elif record.get("execution_started") and record.get("verdict") is not None:
        raise ValueError("projectable execution lacks original child metadata bytes")
    request_ref = record.get("request")
    if request_ref is None:
        if record.get("verdict") is not None or not record.get("diagnostic"):
            raise ValueError("missing request is permitted only for a diagnostic/null capture")
        return record, digest
    if (not isinstance(request_ref, dict)
            or set(request_ref) != {"schema", "check_id", "module_name", "requested_interpreter",
                                   "check_source", "producer", "import_driver_sha256",
                                   "argv_template", "check_source_sha256", "interpreter_prebind",
                                   "readset", "artifact"}):
        raise ValueError("terminal request reference is incomplete or undeclared")
    request_bytes = _artifact(run_dir, request_ref.get("artifact"))
    if request_ref["artifact"]["name"] != "execution-request.json":
        raise ValueError("execution request artifact has a noncanonical name")
    request = json.loads(request_bytes)
    if not isinstance(request, dict) or request_bytes != _canonical(request) or request != {
            key: request_ref[key] for key in request}:
        raise ValueError("execution request differs from terminal receipt")
    if set(request) != {"schema", "check_id", "module_name", "requested_interpreter",
                        "check_source", "producer", "import_driver_sha256", "argv_template",
                        "check_source_sha256", "interpreter_prebind", "readset"}:
        raise ValueError("request fields are incomplete or undeclared")
    if (request.get("schema") != SCHEMA or request.get("check_id") != record["check_id"]
            or request.get("module_name") != record["module_name"]
            or request.get("requested_interpreter") != record["requested_interpreter"]
            or request.get("check_source") != record["check_source"]
            or request.get("producer") != record["producer"]
            or request.get("import_driver_sha256") != record.get("import_driver_sha256")
            or request.get("interpreter_prebind") != record.get("interpreter_prebind")
            or request.get("argv_template") != record.get("argv_template")):
        raise ValueError("execution request identity differs from terminal receipt")
    expected_roles = {"check_source", "producer", "import_driver", "interpreter_prebind"}
    readset = request.get("readset")
    if (not isinstance(readset, list) or len(readset) != len(expected_roles)
            or any(not isinstance(item, dict) for item in readset)
            or {item.get("role") for item in readset} != expected_roles):
        raise ValueError("explicit bounded readset is incomplete or contains undeclared inputs")
    expected_artifacts = {"check_source": "check-source.bin", "producer": "producer-source.bin",
                          "import_driver": "import-driver.bin"}
    for item in readset:
        role = item["role"]
        if role == "interpreter_prebind":
            if set(item) != {"role", "identity"} or item["identity"] != request.get("interpreter_prebind"):
                raise ValueError("pre-execution interpreter identity is not bound in the readset")
        elif (set(item) != {"role", "artifact"} or not isinstance(item["artifact"], dict)
                or item["artifact"].get("name") != expected_artifacts[role]):
            raise ValueError("readset artifact role or path is not canonical")
    artifacts = {item["role"]: _artifact(run_dir, item["artifact"])
                 for item in readset if item["role"] != "interpreter_prebind"}
    if _sha(artifacts["check_source"]) != request.get("check_source_sha256"):
        raise ValueError("check source bytes differ from their declared identity")
    if (not isinstance(record.get("producer"), dict)
            or _sha(artifacts["producer"]) != record["producer"].get("sha256")
            or _sha(artifacts["producer"]) != TRUSTED_PRODUCER_SHA256):
        raise ValueError("producer source bytes differ from the trusted producer identity")
    if (_sha(artifacts["import_driver"]) != record.get("import_driver_sha256")
            or _sha(artifacts["import_driver"]) != TRUSTED_DRIVER_SHA256):
        raise ValueError("single-import driver bytes differ from the trusted driver identity")
    if request_ref.get("check_source_sha256") != request.get("check_source_sha256"):
        raise ValueError("check source identity is not repeated consistently")
    driver_pin = "<import-driver sha256=" + str(record.get("import_driver_sha256")) + ">"
    if request.get("argv_template") != [record["requested_interpreter"], "-c", driver_pin,
                                         record["module_name"], "<private metadata fd>"]:
        raise ValueError("requested argv template differs from the pinned import driver")
    prebind = request.get("interpreter_prebind")
    if prebind is not None and (not isinstance(prebind, dict)
            or set(prebind) != {"path", "sha256"}
            or not isinstance(prebind.get("path"), str)
            or not isinstance(prebind.get("sha256"), str)
            or len(prebind["sha256"]) != 64):
        raise ValueError("pre-execution interpreter identity is malformed")
    if (prebind is not None
            and record.get("requested_interpreter_realpath") != prebind.get("path")):
        raise ValueError("requested interpreter path differs from its pre-execution identity")
    if record["verdict"] is not None:
        if (not isinstance(prebind, dict) or set(prebind) != {"path", "sha256"}
                or prebind.get("path") != record.get("requested_interpreter_realpath")
                or not isinstance(prebind.get("sha256"), str)
                or len(prebind["sha256"]) != 64):
            raise ValueError("projectable check lacks its pre-execution interpreter identity pin")
    for name in ("stdout", "stderr"):
        reference = record.get(name)
        if reference is not None:
            expected_name = name + ".bin"
            if not isinstance(reference, dict) or reference.get("name") != expected_name:
                raise ValueError(f"{name} artifact has a noncanonical name")
            _artifact(run_dir, reference)
    if record.get("verdict") is None:
        if not record.get("diagnostic"):
            raise ValueError("null verdict requires an explicit diagnostic")
        return record, digest
    if not isinstance(record["verdict"], bool) or record.get("diagnostic"):
        raise ValueError("projectable verdict must be boolean without capture diagnostics")
    if not record.get("execution_started") or not isinstance(record.get("exit_code"), int):
        raise ValueError("projectable verdict requires one completed child execution")
    if record["child_timed_out"] or not record["child_cleanup_ok"]:
        raise ValueError("timed out or unclean child execution cannot be projectable")
    if record["verdict"] != (record["exit_code"] == 0):
        raise ValueError("verdict contradicts original child exit status")
    if record.get("stdout") is None or record.get("stderr") is None:
        raise ValueError("completed execution must retain original stdout and stderr bytes")
    if child_metadata is None:
        raise ValueError("completed execution lacks parseable original child metadata bytes")
    interpreter = record.get("interpreter") or {}
    executable = interpreter.get("executable") or {}
    module = record.get("module") or {}
    if (not executable.get("path") or not executable.get("sha256")
            or executable.get("path") != record.get("requested_interpreter_realpath")
            or executable.get("path") != prebind.get("path")
            or executable.get("sha256") != prebind.get("sha256")
            or not isinstance(interpreter.get("version"), str)
            or not isinstance(interpreter.get("implementation"), str)):
        raise ValueError("actual child interpreter identity is incomplete or mismatched")
    if record["verdict"] and not (module.get("origin") and module.get("sha256")):
        raise ValueError("successful import has no resolved module identity")
    if record["verdict"] and (not record.get("import_succeeded") or record.get("metadata_error")):
        raise ValueError("successful check lacks complete same-process import metadata")
    if not record["verdict"] and (record.get("import_succeeded") is not False
                                   or not isinstance(record.get("import_error"), dict)):
        raise ValueError("failed import lacks the child's original import exception")
    argv = record.get("argv")
    expected_driver = "<import-driver sha256=" + record["import_driver_sha256"] + ">"
    if (not isinstance(argv, list) or len(argv) != 5
            or argv[:2] != [record["requested_interpreter"], "-c"]
            or argv[2] != expected_driver or argv[3] != record["module_name"]
            or not str(argv[4]).isdigit()):
        raise ValueError("captured child argv does not match its pinned single-import request")
    expected_proposition = proposition(record)
    if record.get("decided_proposition") != expected_proposition:
        raise ValueError("producer proposition does not match its original capture")
    return record, digest


def proposition(record: dict) -> str:
    interpreter = record["interpreter"]["executable"]
    module = record["module"]
    action = "imported module" if record["verdict"] else "attempted to import module"
    return (f"Named managed import check {record['check_id']} {action} "
            f"{record['module_name']} using interpreter {interpreter['path']} sha256 "
            f"{interpreter['sha256']}; resolved module origin {module.get('origin')!r} "
            f"sha256 {module.get('sha256')!r}; check source sha256 "
            f"{record['request']['check_source_sha256']}; exit status {record['exit_code']} "
            f"at {record['ended_utc']}; passed: {str(record['verdict']).lower()}.")


def native_rows(path):
    try:
        record, digest = read_receipt(path)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ProjectionError(f"managed-tooling receipt refused: {exc}") from exc
    if record["verdict"] is None:
        return ()
    return ({"record": record, "receipt_path": str(Path(path).resolve()),
             "receipt_sha256": digest},)


@register("managed-tooling-check", source_class="verifier",
          decided_proposition_field="decided_proposition")
def project_managed_tooling_check(native):
    try:
        rows = native_rows(native["receipt_path"])
        if len(rows) != 1 or rows[0] != native:
            raise ProjectionError("managed-tooling receipt changed since reopening")
        record = native["record"]
        proposition_text = record["decided_proposition"]
        return ClaimTuple(
            measurement_id="managed-tooling:" + native["receipt_sha256"],
            metric="named_managed_import_passed", value=record["verdict"],
            date=record["ended_utc"], category="CANDIDATE",
            metric_direction="higher_better", protocol_id="", claim=proposition_text,
            decided_proposition=proposition_text, source_class="verifier",
            source_kind=ADAPTER_ID, binding_kind="identity",
            attestation_locator=native["receipt_path"],
            extra={"receipt_sha256": native["receipt_sha256"],
                   "check_id": record["check_id"], "module": record["module"],
                   "interpreter": record["interpreter"], "argv": record["argv"],
                   "stdout": record["stdout"], "stderr": record["stderr"],
                   "request": record["request"], "exclusions": record["exclusions"]})
    except (KeyError, TypeError, ValueError) as exc:
        raise ProjectionError(f"managed-tooling projection refused: {exc}") from exc
