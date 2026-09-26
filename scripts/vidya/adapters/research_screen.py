"""Prospective research-screen receipt writer and strict Vidya projection.

The receipt is authored by the producer at run end. Historical journals are inputs,
never upgraded into receipts by this reader. This module validates evidence and
projects a ClaimTuple; claim_tuple.grade() alone assigns warrant.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

ADAPTER_ID = "vidya.adapters.research_screen/v1"
AUTHORITY = "measurement"
PROJECTION_NAME = "research_screen"
SCHEMA = "epyc.research_screen.v1"
CLASSES = frozenset(
    {
        "mechanism_feasibility",
        "benchmark_performance",
        "selector_causality",
        "license_status",
    }
)
ARMS = frozenset({"current", "score_only", "shinka", "dgm", "hgm"})
SHA = re.compile(r"^[0-9a-f]{64}$")
TOP = frozenset(
    {
        "schema",
        "receipt_id",
        "run_id",
        "timestamp",
        "source",
        "producer",
        "input_manifest",
        "baseline",
        "raw_outputs",
        "window",
        "counts",
        "rule",
        "disposition",
        "claim",
        "profile",
        "receipt_sha256",
    }
)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _obj(value: Any, label: str, required: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, dict) or not required.issubset(value):
        raise ProjectionError(f"{label} requires {sorted(required)}")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProjectionError(f"{label} must be nonempty producer text")
    return value


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or SHA.fullmatch(value) is None:
        raise ProjectionError(f"{label} must be a SHA-256 hex digest")
    return value


def _count(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ProjectionError(f"{label} must be a nonnegative integer")
    return value


def _artifact(spec: Any, label: str, base: Path, *, jsonl: bool = False) -> int | None:
    item = _obj(spec, label, {"path", "sha256"})
    location = Path(_text(item["path"], f"{label}.path"))
    if not location.is_absolute():
        location = base / location
    _sha(item["sha256"], f"{label}.sha256")
    try:
        raw = location.read_bytes()
    except OSError as exc:
        raise ProjectionError(f"{label} evidence unavailable: {location}") from exc
    if hashlib.sha256(raw).hexdigest() != item["sha256"]:
        raise ProjectionError(f"{label} bytes do not match producer digest")
    if not jsonl:
        return None
    lines = raw.splitlines()
    if any(not line.strip() for line in lines):
        raise ProjectionError(f"{label} contains an empty row")
    for line in lines:
        try:
            if not isinstance(json.loads(line), dict):
                raise ValueError("row is not an object")
        except (ValueError, UnicodeError) as exc:
            raise ProjectionError(f"{label} contains a non-JSON object row") from exc
    if _count(item.get("row_count"), f"{label}.row_count") != len(lines):
        raise ProjectionError(f"{label} row_count differs from raw row bytes")
    return len(lines)


def _json_evidence(spec: Any, label: str, base: Path) -> Mapping[str, Any]:
    _artifact(spec, label, base)
    location = Path(spec["path"])
    if not location.is_absolute():
        location = base / location
    try:
        raw = location.read_bytes()
        if hashlib.sha256(raw).hexdigest() != spec["sha256"]:
            raise ProjectionError(f"{label} bytes changed during validation")
        return _obj(json.loads(raw), label, set())
    except (ValueError, UnicodeError) as exc:
        raise ProjectionError(f"{label} is not a JSON object") from exc


def _timing(spec: Any, label: str, base: Path) -> None:
    obj = _json_evidence(spec, label, base)
    samples = obj.get("samples_ms")
    if (
        not isinstance(samples, list)
        or not samples
        or any(
            type(value) not in (int, float) or not math.isfinite(value) or value < 0
            for value in samples
        )
    ):
        raise ProjectionError(f"{label}.samples_ms requires measured finite samples")


def _billing(spec: Any, base: Path) -> None:
    obj = _json_evidence(spec, "profile.billing.evidence", base)
    value = obj.get("billed_cost")
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ProjectionError("profile.billing.evidence requires finite billed_cost")
    _text(obj.get("currency"), "profile.billing.evidence.currency")
    if _count(obj.get("requests"), "profile.billing.evidence.requests") == 0:
        raise ProjectionError("profile.billing.evidence.requests must be positive")


def _counts(value: Any) -> Mapping[str, int]:
    c = _obj(
        value, "counts", {"eligible", "scored", "failure", "invalid", "abstention"}
    )
    result = {
        key: _count(c[key], f"counts.{key}")
        for key in ("eligible", "scored", "failure", "invalid", "abstention")
    }
    if result["eligible"] != sum(
        result[key] for key in ("scored", "failure", "invalid", "abstention")
    ):
        raise ProjectionError(
            "eligible denominator must include scored, failure, invalid, abstention"
        )
    return result


def _item_rows(
    spec: Mapping[str, Any], base: Path, counts: Mapping[str, int], *, kind: str
) -> tuple[set[str], set[str]]:
    path = Path(spec["path"])
    if not path.is_absolute():
        path = base / path
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != spec["sha256"]:
        raise ProjectionError("raw_outputs bytes changed during validation")
    rows = [json.loads(line) for line in raw.splitlines()]
    tally = {key: 0 for key in ("scored", "failure", "invalid", "abstention")}
    identifiers: set[str] = set()
    scored_identifiers: set[str] = set()
    seen_arms: set[str] = set()
    for row in rows:
        ident = _text(row.get("item_id"), "raw_outputs.item_id")
        arm = (
            _text(row.get("arm"), "raw_outputs.arm")
            if kind == "selector_replay"
            else ""
        )
        if kind == "selector_replay" and arm not in ARMS:
            raise ProjectionError("raw_outputs.arm is not a declared selector arm")
        seen_arms.add(arm)
        item_key = f"{arm}:{ident}"
        if item_key in identifiers:
            raise ProjectionError("raw_outputs has duplicate item_id")
        identifiers.add(item_key)
        status = row.get("status")
        if status not in tally:
            raise ProjectionError(
                "raw_outputs.status must be scored, failure, invalid, or abstention"
            )
        tally[status] += 1
        if status == "scored":
            scored_identifiers.add(item_key)
        if kind == "typed_decision_shadow" and status == "scored":
            if (
                "output" not in row
                or not isinstance(row.get("probabilities"), dict)
                or not row["probabilities"]
            ):
                raise ProjectionError(
                    "typed scored row requires output and probabilities in raw bytes"
                )
            probs = row["probabilities"]
            if (
                any(
                    type(p) not in (int, float)
                    or not math.isfinite(p)
                    or p < 0
                    or p > 1
                    for p in probs.values()
                )
                or abs(sum(probs.values()) - 1) > 1e-6
            ):
                raise ProjectionError(
                    "typed probabilities must be a finite normalized distribution"
                )
    if tally != {key: counts[key] for key in tally}:
        raise ProjectionError("raw per-item statuses do not match denominator counts")
    if kind == "selector_replay" and seen_arms != ARMS:
        raise ProjectionError(
            "raw_outputs must contain decisions for all five selector arms"
        )
    return identifiers, scored_identifiers


def _selector_keys(
    spec: Mapping[str, Any], label: str, base: Path, required_field: str
) -> set[str]:
    path = Path(spec["path"])
    if not path.is_absolute():
        path = base / path
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != spec["sha256"]:
        raise ProjectionError(f"{label} bytes changed during validation")
    keys: set[str] = set()
    for line in raw.splitlines():
        row = json.loads(line)
        arm = _text(row.get("arm"), f"{label}.arm")
        if arm not in ARMS or required_field not in row:
            raise ProjectionError(
                f"{label} requires a declared arm and {required_field}"
            )
        key = f"{arm}:{_text(row.get('item_id'), f'{label}.item_id')}"
        if key in keys:
            raise ProjectionError(f"{label} has duplicate decision rows")
        keys.add(key)
    return keys


def _profile(
    value: Any,
    base: Path,
    counts: Mapping[str, int],
    raw_keys: set[str],
    scored_keys: set[str],
) -> None:
    profile = _obj(value, "profile", {"kind"})
    kind = profile["kind"]
    if kind == "selector_replay":
        required = {
            "journal",
            "candidate_graph",
            "task_order",
            "policy_revision",
            "scorer_revision",
            "selector_id",
            "scheduler_id",
            "archive_id",
            "endpoint_id",
            "eligibility_denominator",
            "parent_choices",
            "paired_continuations",
            "arms",
            "holdout_id",
            "tokens",
            "cost",
        }
        _obj(profile, "selector_replay", required)
        for key in ("journal", "candidate_graph", "task_order"):
            _artifact(profile[key], f"profile.{key}", base)
        parents = _artifact(
            profile["parent_choices"], "profile.parent_choices", base, jsonl=True
        )
        continuations = _artifact(
            profile["paired_continuations"],
            "profile.paired_continuations",
            base,
            jsonl=True,
        )
        if parents != counts["eligible"] or continuations != counts["scored"]:
            raise ProjectionError(
                "selector parent/continuation counts differ from eligible/scored"
            )
        if (
            _selector_keys(profile["parent_choices"], "parent_choices", base, "parent")
            != raw_keys
            or _selector_keys(
                profile["paired_continuations"], "paired_continuations", base, "result"
            )
            != scored_keys
        ):
            raise ProjectionError(
                "selector parent/continuation decisions differ from raw item rows"
            )
        for key in (
            "policy_revision",
            "scorer_revision",
            "selector_id",
            "scheduler_id",
            "archive_id",
            "endpoint_id",
            "holdout_id",
        ):
            _text(profile[key], f"profile.{key}")
        if (
            not isinstance(profile["arms"], list)
            or set(profile["arms"]) != ARMS
            or len(profile["arms"]) != len(ARMS)
        ):
            raise ProjectionError(
                "selector replay must include current, score_only, shinka, dgm, hgm"
            )
        if (
            _count(profile["eligibility_denominator"], "eligibility_denominator")
            != counts["eligible"]
        ):
            raise ProjectionError(
                "eligibility_denominator differs from counts.eligible"
            )
        for key in ("tokens", "cost"):
            number = profile[key]
            if number is not None and (
                type(number) not in (int, float)
                or not math.isfinite(number)
                or number < 0
            ):
                raise ProjectionError(
                    f"profile.{key} must be nonnegative finite or null"
                )
    elif kind == "typed_decision_shadow":
        required = {
            "requested_model",
            "resolved_model",
            "model_base",
            "model_head",
            "hosted_revision",
            "adapter_revision",
            "config",
            "dataset_manifest",
            "component_timing",
            "sequential_timing",
            "billing",
            "protocol_scope",
        }
        _obj(profile, "typed_decision_shadow", required)
        for key in (
            "requested_model",
            "resolved_model",
            "adapter_revision",
            "protocol_scope",
        ):
            _text(profile[key], f"profile.{key}")
        if not any(
            isinstance(profile[key], str) and profile[key].strip()
            for key in ("model_base", "model_head", "hosted_revision")
        ):
            raise ProjectionError(
                "typed decision model base/head or hosted revision is required"
            )
        for key in ("config", "dataset_manifest"):
            _artifact(profile[key], f"profile.{key}", base)
        for key in ("component_timing", "sequential_timing"):
            _timing(profile[key], f"profile.{key}", base)
        billing = _obj(profile["billing"], "billing", {"hosted", "evidence"})
        if type(billing["hosted"]) is not bool:
            raise ProjectionError("billing.hosted must be boolean")
        if billing["hosted"]:
            _text(profile["hosted_revision"], "profile.hosted_revision")
            _billing(billing["evidence"], base)
        elif billing["evidence"] is not None:
            _billing(billing["evidence"], base)
    elif kind == "deterministic_primitive":
        required = {"primitive_id", "conformance_artifact", "provenance_artifact"}
        _obj(profile, "deterministic_primitive", required)
        _text(profile["primitive_id"], "profile.primitive_id")
        for key in ("conformance_artifact", "provenance_artifact"):
            _artifact(profile[key], f"profile.{key}", base)
    else:
        raise ProjectionError(f"unsupported research-screen profile {kind!r}")


def validate(receipt: Mapping[str, Any], base: Path) -> None:
    """Refuse incomplete, internally inconsistent, or unattested producer records."""
    if not isinstance(receipt, dict) or set(receipt) != TOP:
        raise ProjectionError(
            f"research-screen envelope requires exactly {sorted(TOP)}"
        )
    if receipt["schema"] != SCHEMA:
        raise ProjectionError("unsupported research-screen schema")
    body = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    if _sha(receipt["receipt_sha256"], "receipt_sha256") != _digest(body):
        raise ProjectionError("research-screen receipt self-hash mismatch")
    for key in ("receipt_id", "run_id", "timestamp"):
        _text(receipt[key], key)
    try:
        stamp = datetime.fromisoformat(receipt["timestamp"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProjectionError("timestamp must be an ISO-8601 UTC timestamp") from exc
    if stamp.tzinfo is None or stamp.utcoffset() != timezone.utc.utcoffset(stamp):
        raise ProjectionError("timestamp must be an ISO-8601 UTC timestamp")
    for key, required in (
        ("source", {"kind", "revision"}),
        ("producer", {"name", "revision"}),
        ("baseline", {"id", "revision"}),
        ("rule", {"id", "revision", "statement"}),
        ("disposition", {"decision", "reason"}),
    ):
        obj = _obj(receipt[key], key, required)
        for field in required:
            _text(obj[field], f"{key}.{field}")
    _artifact(receipt["input_manifest"], "input_manifest", base)
    raw_rows = _artifact(receipt["raw_outputs"], "raw_outputs", base, jsonl=True)
    counts = _counts(receipt["counts"])
    if raw_rows != counts["eligible"]:
        raise ProjectionError("raw output rows must account for every eligible item")
    profile = _obj(receipt["profile"], "profile", {"kind"})
    raw_keys, scored_keys = _item_rows(
        receipt["raw_outputs"], base, counts, kind=profile["kind"]
    )
    window = _obj(receipt["window"], "window", {"kind", "id", "reason"})
    if window["kind"] not in ("holdout", "later_window", "inapplicable"):
        raise ProjectionError(
            "window.kind must be holdout, later_window, or inapplicable"
        )
    _text(window["id"], "window.id")
    if window["kind"] == "inapplicable":
        reason = _text(window["reason"], "window.reason").lower()
        if (
            len(reason) < 30
            or "deterministic" not in reason
            or not any(word in reason for word in ("conformance", "provenance"))
        ):
            raise ProjectionError(
                "inapplicable holdout needs a deterministic conformance reason"
            )
    elif window["reason"] not in ("", None):
        raise ProjectionError("window.reason is reserved for inapplicable holdouts")
    claim = _obj(
        receipt["claim"],
        "claim",
        {
            "class",
            "metric",
            "value",
            "unit",
            "direction",
            "category",
            "protocol_id",
            "text",
            "reps_basis",
        },
    )
    if claim["class"] not in CLASSES:
        raise ProjectionError(
            "claim.class must preserve a declared research claim class"
        )
    for key in ("metric", "unit", "direction", "category", "text"):
        _text(claim[key], f"claim.{key}")
    if type(claim["value"]) not in (int, float) or not math.isfinite(claim["value"]):
        raise ProjectionError("claim.value must be a finite producer number")
    if not isinstance(claim["protocol_id"], str):
        raise ProjectionError("claim.protocol_id must be producer text or empty")
    _text(claim["reps_basis"], "claim.reps_basis")
    _profile(receipt["profile"], base, counts, raw_keys, scored_keys)
    if receipt["profile"]["kind"] == "selector_replay" and window["kind"] != "holdout":
        raise ProjectionError("selector replay requires a frozen holdout")
    if (
        receipt["profile"]["kind"] == "selector_replay"
        and window["id"] != receipt["profile"]["holdout_id"]
    ):
        raise ProjectionError("selector holdout identity differs from shared envelope")
    if (
        window["kind"] == "inapplicable"
        and receipt["profile"]["kind"] != "deterministic_primitive"
    ):
        raise ProjectionError(
            "only deterministic primitives may mark holdout inapplicable"
        )


def write_receipt(path: Path, body: Mapping[str, Any]) -> dict[str, Any]:
    """Producer API: seal a complete body after raw evidence files have been written."""
    record = dict(body)
    if "receipt_sha256" in record:
        raise ProjectionError("producer body must not supply receipt_sha256")
    record["receipt_sha256"] = _digest(record)
    validate(record, Path(path).parent)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = _canonical(record) + b"\n"
    if path.exists():
        if path.read_bytes() != raw:
            raise ProjectionError("receipt path already holds different bytes")
        return record
    try:
        with path.open("xb") as stream:
            stream.write(raw)
    except FileExistsError as exc:
        raise ProjectionError("receipt path was written concurrently") from exc
    return record


def native_rows(path: Path) -> list[dict[str, Any]]:
    """One file is one run; a corrupt file never yields a partial claim."""
    try:
        raw_bytes = Path(path).read_bytes()
        raw = json.loads(raw_bytes)
    except (OSError, ValueError) as exc:
        raise ProjectionError(f"research-screen receipt is unreadable: {path}") from exc
    validate(raw, Path(path).parent)
    return [
        {
            "receipt": raw,
            "path": str(path),
            "file_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        }
    ]


@register(PROJECTION_NAME, source_class="measurement")
def project(native: Mapping[str, Any]) -> ClaimTuple:
    """Project producer fields; grading remains in claim_tuple.grade()."""
    receipt = native["receipt"]
    claim = receipt["claim"]
    counts = receipt["counts"]
    return ClaimTuple(
        measurement_id=receipt["receipt_id"],
        metric=claim["metric"],
        value=claim["value"],
        date=receipt["timestamp"][:10],
        category=claim["category"],
        claim=claim["text"],
        metric_direction=claim["direction"],
        protocol_id=claim["protocol_id"],
        reps=counts["scored"] or None,
        reps_basis=claim["reps_basis"],
        unit=claim["unit"],
        attestation_path=native["path"],
        attestation_sha256=native["file_sha256"],
        attestation_present=True,
        attestation_verified=True,
        attestation_locator=receipt["run_id"],
        source_kind=receipt["source"]["kind"],
        extra={
            "claim_class": claim["class"],
            "receipt_schema": receipt["schema"],
            "receipt_sha256": receipt["receipt_sha256"],
            "profile": receipt["profile"],
            "counts": counts,
            "baseline": receipt["baseline"],
            "window": receipt["window"],
            "rule": receipt["rule"],
            "disposition": receipt["disposition"],
            "input_manifest": receipt["input_manifest"],
            "raw_outputs": receipt["raw_outputs"],
            "producer": receipt["producer"],
            "source": receipt["source"],
        },
    )
