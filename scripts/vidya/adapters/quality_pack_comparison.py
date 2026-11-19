"""Project sealed V9-8 comparisons as scoped diagnostic observations."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import ModuleType

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames

ADAPTER_ID = "vidya.adapters.quality_pack_comparison/v1"
SOURCE_KIND = "quality-pack-comparison"
AUTHORITY = "measurement"
PLANNER_CONSUMER = "autokernel.planner"
VALIDATOR = (
    Path(__file__).resolve().parents[3] / ".claude/skills/kernel-promotion/scripts/quality_parity.py"
)
FIELDS = {
    "schema", "completed_at", "validator_source_sha256", "prospective_pack_sha256", "pack",
    "candidate", "report", "error", "coverage", "checks", "content_sha256",
}


def _validator():
    # Execute the checked-in source rather than a potentially stale bytecode cache. The native
    # tool requires its pack to have been built with exactly these source bytes.
    source = VALIDATOR.read_bytes()
    module = ModuleType("_vidya_quality_parity")
    module.__file__ = str(VALIDATOR)
    exec(compile(source, str(VALIDATOR), "exec"), module.__dict__)
    return module, module._sha256(source)


def _original(tool, snapshot):
    tool._fields(snapshot, {"bytes_b64", "sha256"}, "original input")
    raw = tool.base64.b64decode(snapshot["bytes_b64"], validate=True)
    if tool._input_snapshot(raw) != snapshot:
        raise ValueError("original input byte hash or encoding differs")
    return raw


def _validate(path, payload):
    try:
        tool, validator_hash = _validator()
        record = tool._parse(payload)
        tool._fields(record, FIELDS, "sealed comparison")
        if record["schema"] != tool.CAPTURE_SCHEMA:
            raise ValueError("unsupported sealed comparison schema")
        body = {key: value for key, value in record.items() if key != "content_sha256"}
        if record["content_sha256"] != tool._json_hash(body):
            raise ValueError("comparison content seal differs")
        completed = datetime.strptime(record["completed_at"], "%Y-%m-%dT%H:%M:%SZ")
        if completed.strftime("%Y-%m-%dT%H:%M:%SZ") != record["completed_at"]:
            raise ValueError("comparison timestamp lacks canonical UTC format")
        if record["validator_source_sha256"] != validator_hash:
            raise ValueError("comparison validator source differs from the installed source")
        pack = _original(tool, record["pack"])
        candidate = _original(tool, record["candidate"])
        replay = tool._capture_outcome(pack, record["prospective_pack_sha256"], candidate)
        recorded = {key: record[key] for key in replay}
        if tool.canonical_json(replay) != tool.canonical_json(recorded):
            raise ValueError("native comparison outcome or coverage does not re-derive")
        return record
    except (OSError, KeyError, ValueError, TypeError, RecursionError) as exc:
        raise ProjectionError(f"{SOURCE_KIND} {path}: {exc}") from exc


def _eligible(record):
    report = record["report"]
    return (
        report is not None
        and report["status"] in {"pass", "fail"}
        and not report.get("missing_token_ids")
        and not report.get("missing_completion_counts")
    )


def native_rows(path):
    path = Path(path)
    if not path.is_file():
        return ()
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise ProjectionError(f"{SOURCE_KIND} {path}: unreadable comparison") from exc
    record = _validate(path, payload)
    return ({"path": str(path), "payload": payload},) if _eligible(record) else ()


def units(path):
    path = Path(path)
    return [path] if path.is_file() else sorted(path.rglob("quality_pack_comparison*.json"))


@register(SOURCE_KIND)
def project(native):
    if not isinstance(native, dict) or set(native) != {"path", "payload"}:
        raise ProjectionError(f"{SOURCE_KIND}: native row missing")
    path = native["path"]
    record = _validate(path, native["payload"])
    if not _eligible(record):
        raise ProjectionError(f"{SOURCE_KIND} {path}: comparison lacks a complete pass or fail disposition")
    report = record["report"]
    failures = report.get("failures", {})
    checked = len(record["checks"])
    mismatches = len(failures)
    claim = (
        f"V9-8 quality parity comparator reported {report['status']} with {mismatches} mismatching "
        f"items among {checked} checked items for pinned pack {record['pack']['sha256']} and "
        f"candidate capture {record['candidate']['sha256']}. Scope is this exact capture pair. "
        "Supplied runtime and model identities are declarations. Live serving identity, quality transfer "
        "and promotion are outside the offline comparison."
    )
    return ClaimTuple(
        measurement_id=f"{SOURCE_KIND}:{record['content_sha256']}",
        metric="quality_pack_mismatching_items", value=mismatches, date=record["completed_at"][:10],
        category="CANDIDATE", claim=claim, metric_direction="lower_better", unit="items",
        protocol_id="", reps=1, reps_basis="one native comparison of the pinned packs",
        attestation_path=path, attestation_sha256=record["content_sha256"],
        attestation_locator=f"{SOURCE_KIND}:{path}", attestation_present=True,
        attestation_verified=True, source_kind=SOURCE_KIND,
        applicability={"consumer": PLANNER_CONSUMER},
        observation={"outcome_native": report["status"]},
        extra={"adapter": ADAPTER_ID, "checked_items": checked, "coverage": record["coverage"],
               "validator_source_sha256": record["validator_source_sha256"],
               "pack_sha256": record["pack"]["sha256"],
               "candidate_sha256": record["candidate"]["sha256"],
               "failures": failures, "next_action": report["next_action"]},
    )


def frames_for_path(path, *, as_of):
    return [
        frame
        for native in native_rows(path)
        for frame in to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY)
    ]
