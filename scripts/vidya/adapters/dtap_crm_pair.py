"""Strict prospective reader of producer-authored DTAP CRM-pair observations.

The receipt's identity/grant fields are producer declarations unless their
native authorities are separately verified. This adapter neither invents
physical warrant nor changes the shared ClaimTuple grading rule.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from datetime import datetime
from pathlib import Path
from typing import Any

from claim_tuple import ProjectionError

SCHEMA = "dtap.crm_pair_receipt.v1"
SOURCE_KIND = "dtap-crm-pair"
CASE = "crm-malicious-indirect-general-ai-restrictions-004"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
PRODUCER_SHA256 = "27f22e3be23c7b27cc25ea7442fc2eb19fd59edd0a03e0cc578971a8eb755b59"


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON field")
        out[key] = value
    return out


def _json(raw: bytes) -> Any:
    return json.loads(raw, object_pairs_hook=_object,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def _read(path: Path, limit: int = 64 * 1024 * 1024) -> bytes:
    """Open a regular file without following its final symlink or accepting mutation."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError("native artifact is not a bounded regular file")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(limit + 1)
        after = os.fstat(fd)
        if (len(raw) > limit or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
            raise ValueError("native artifact changed during read")
        return raw
    finally:
        os.close(fd)


def _time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp missing")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("timestamp must be UTC")
    return parsed


def _journal(raw: bytes) -> list[dict[str, Any]]:
    if not raw or not raw.endswith(b"\n"):
        raise ValueError("journal absent or truncated")
    previous = "0" * 64
    records = []
    previous_time = None
    for line in raw.splitlines(keepends=True):
        row = _json(line)
        if (not isinstance(row, dict) or set(row) != {"kind", "utc", "previous_sha256", "payload"}
                or row["previous_sha256"] != previous or not isinstance(row["kind"], str)):
            raise ValueError("journal hash chain or record shape invalid")
        time = _time(row["utc"])
        if previous_time is not None and time < previous_time:
            raise ValueError("journal timestamps out of order")
        previous, previous_time = _hash(line), time
        records.append(row)
    if records[0]["kind"] != "start" or records[-1]["kind"] != "terminal":
        raise ValueError("journal is not terminal")
    return records


def _open_pair(path: Path) -> dict[str, Any]:
    seal_raw = _read(path, 1024 * 1024)
    seal = _json(seal_raw)
    if not isinstance(seal, dict) or seal.get("schema") != SCHEMA or seal.get("capture_kind") != "live":
        raise ValueError("only prospective live producer seals are accepted")
    provenance = seal["provenance"]
    if not isinstance(provenance, dict) or not COMMIT.fullmatch(str(provenance.get("source_commit", ""))):
        raise ValueError("native source commit missing")
    for key in ("source_tree_sha256", "model_sha256", "server_sha256", "template_sha256",
                "tool_schema_sha256", "case_sha256"):
        if not SHA256.fullmatch(str(provenance.get(key, ""))):
            raise ValueError("native provenance digest missing")
    if (not isinstance(provenance.get("grant_id"), str) or not provenance["grant_id"]
            or any(type(provenance.get(k)) is not int or provenance[k] <= 0
                   for k in ("model_pid", "model_pid_starttime"))
            or provenance.get("backend") not in ("cpu", "gpu", "unknown")):
        raise ValueError("native grant, process or backend declaration missing")
    model_file = provenance.get("model_file")
    if model_file is not None and (not isinstance(model_file, str) or not model_file
                                   or Path(model_file).name != model_file):
        raise ValueError("native model filename invalid")
    opened = {}
    for name in ("journal", "grant_receipt", "source_manifest", "producer"):
        location = seal.get(name + "_path")
        digest = seal.get(name + "_sha256")
        if (not isinstance(location, str) or not Path(location).is_absolute()
                or not SHA256.fullmatch(str(digest or ""))):
            raise ValueError("native artifact locator or digest missing")
        raw = _read(Path(location))
        if not raw or _hash(raw) != digest:
            raise ValueError("native artifact digest mismatch")
        opened[name] = raw
    if _hash(opened["producer"]) != PRODUCER_SHA256:
        raise ValueError("producer bytes are not the reviewed capture implementation")
    records = _journal(opened["journal"])
    start, terminal = records[0], records[-1]
    if (start["payload"].get("capture_kind") != "live" or start["payload"].get("provenance") != provenance
            or seal.get("capture_start_utc") != start["utc"] or seal.get("terminal_utc") != terminal["utc"]
            or _time(seal["sealed_utc"]) < _time(terminal["utc"])):
        raise ValueError("start, terminal or seal identities disagree")
    manifests = [x["payload"] for x in records if x["kind"] == "pair_manifest"]
    if len(manifests) != 1 or not isinstance(manifests[0], dict):
        raise ValueError("native pair manifest missing")
    manifest = manifests[0].get("manifest", {})
    if (manifest.get("case") != CASE or manifest.get("arms") != ["control", "attack"]
            or manifest.get("skill_injection") != "not_tested"
            or manifest.get("schema_sha256") != provenance["tool_schema_sha256"]
            or manifest.get("registry_sha256") != provenance["case_sha256"]):
        raise ValueError("case and schema do not match original pair manifest")
    terminal_payload = terminal["payload"]
    arms = terminal_payload.get("arms")
    if (not isinstance(arms, dict) or set(arms) != {"control", "attack"}
            or arms != seal.get("arms") or terminal_payload.get("cleanup") != "completed_by_backend"
            or seal.get("cleanup") != "completed_by_backend"):
        raise ValueError("pair terminal or cleanup differs from seal")
    cleanup = [r for r in records if r["kind"] == "cleanup"]
    if len(cleanup) != 1 or cleanup[0]["payload"].get("status") != "completed_by_backend":
        raise ValueError("native cleanup record missing")
    results = {}
    reset_digests = []
    for arm in ("control", "attack"):
        item = arms[arm]
        if (not isinstance(item, dict) or item.get("status") not in ("complete", "failed", "not_attempted")
                or item.get("delivery") not in ("not_observed", "queued_not_confirmed", "delivered")
                or (arm == "control" and item["delivery"] != "not_observed")):
            raise ValueError("native arm status or delivery invalid")
        events = [r for r in records if isinstance(r["payload"], dict) and r["payload"].get("arm") == arm]
        resets = [r for r in events if r["kind"] == "reset"]
        endings = [r for r in events if r["kind"] in ("judged", "arm_failed", "arm_skipped")]
        expected_kind = {"complete": "judged", "failed": "arm_failed", "not_attempted": "arm_skipped"}[item["status"]]
        if (len(resets) > 1 or (item["status"] == "complete" and len(resets) != 1)
                or len(endings) != 1 or endings[0]["kind"] != expected_kind
                or endings[0]["payload"].get("delivery") != item["delivery"]):
            raise ValueError("arm terminal does not rederive from journal")
        if item["status"] == "not_attempted" and (arm != "attack" or arms["control"]["status"] != "failed"
                or item["delivery"] != "not_observed" or any(r["kind"] in
                    ("reset", "request", "model", "tool_attempt", "tool_result", "judged", "arm_failed")
                    for r in events)):
            raise ValueError("skipped arm has inconsistent attempts")
        if resets:
            reset = resets[0]["payload"]
            if not isinstance(reset.get("state"), dict):
                raise ValueError("native reset state missing")
            state_raw = json.dumps(reset["state"], sort_keys=True, ensure_ascii=False,
                                   separators=(",", ":"), allow_nan=False).encode()
            if _hash(state_raw) != reset.get("sha256"):
                raise ValueError("reset state digest mismatch")
            reset_digests.append(reset["sha256"])
        judgment = endings[0]["payload"].get("judge") if item["status"] == "complete" else None
        if item["status"] == "complete" and not isinstance(judgment, dict):
            raise ValueError("completed arm lacks native judgment")
        results[arm] = {"status": item["status"], "delivery": item["delivery"], "judge": judgment}
    if len(set(reset_digests)) > 1:
        raise ValueError("paired arms did not start from the same state")
    if results["attack"]["delivery"] == "delivered":
        suffix = manifest.get("payload")
        if not isinstance(suffix, str) or not suffix or _hash(suffix.encode()) != manifest.get("payload_sha256"):
            raise ValueError("attack payload digest mismatch")
        delivered = False
        for index, event in enumerate(records):
            p = event["payload"]
            if (event["kind"] != "tool_result" or not isinstance(p, dict) or p.get("arm") != "attack"
                    or p.get("name") != manifest.get("target")):
                continue
            body = p.get("model_visible_result")
            if not isinstance(body, str) or not body.endswith("\n" + suffix):
                continue
            for j in range(index + 1, len(records)):
                request = records[j]
                rp = request["payload"]
                if request["kind"] != "request" or not isinstance(rp, dict) or rp.get("arm") != "attack":
                    continue
                messages = rp.get("messages")
                if (not isinstance(messages, list) or not any(isinstance(m, dict) and m.get("role") == "tool"
                                                               and m.get("content") == body for m in messages)):
                    continue
                delivered = any(m["kind"] == "model" and isinstance(m["payload"], dict)
                                and m["payload"].get("arm") == "attack"
                                and m["payload"].get("turn") == rp.get("turn") for m in records[j + 1:])
                if delivered:
                    break
            if delivered:
                break
        if not delivered:
            raise ValueError("delivered claim lacks model-visible request and response")
    return {"seal_path": str(path), "seal_sha256": _hash(seal_raw), "seal": seal, "results": results}


def native_rows(path: str | Path) -> tuple[dict[str, Any], ...]:
    try:
        _open_pair(Path(path).absolute())
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError) as exc:
        raise ProjectionError("CRM pair original custody refused: " + type(exc).__name__) from exc
    # 5b2d7066 accepts caller-provided provenance and arbitrary nonempty grant/
    # source files. Hash consistency is not a physical grant or source authority.
    # No ClaimTuple is emitted until a native authority contract can be checked.
    raise ProjectionError("CRM pair physical grant and source authority are not bound by producer v1")
