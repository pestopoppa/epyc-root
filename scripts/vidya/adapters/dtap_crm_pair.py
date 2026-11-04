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
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from claim_tuple import ClaimTuple, ProjectionError, register

SCHEMA = "dtap.crm_pair_receipt.v1"
SOURCE_KIND = "dtap-crm-pair"
ADAPTER_ID = "vidya.adapters.dtap_crm_pair/v1"
AUTHORITY = "producer_reported_observation_no_issuer_runtime_or_physical_warrant"
CASE = "crm-malicious-indirect-general-ai-restrictions-004"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
PRODUCER_SHA256 = "432719690780f2512350258c14246ab675bf662a503da936b7316a0d4597709c"
PROVIDER_SHA256 = "43595426ec4a447c06e192ba533b01384674a6217a5005be9980d337974dd961"
LOCK_SHA256 = "24a4a377fe5050e0f34514294e7d14bcc94db4c99fe89b91881d68ae81ece56c"
RECEIPT_SHA256 = "cee7fc7f4ab8dc7fe756b3720c6ee126f8f8b9708de5c62ca74ac18fed290801"
LOCK_ROOT = Path("/mnt/raid0/llm/tmp")
GRANT_ROOT = Path("/mnt/raid0/llm/tmp/compute-flags/grants")
DTAP = "scripts/autopilot/evals/dtap/"
SOURCE_FILES = tuple(DTAP + p for p in (
    "harness/crm_pair_capture.py", "harness/crm_pair_seal.py", "harness/crm_pair.py",
    "harness/crm_receipt.py", "harness/crm_services.py", "harness/crm_provision.py",
    "harness/crm_source_manifest.py", "harness/runner.py", "harness/endpoint.py",
    "harness/tool_contract.py", "harness/tool_schemas.json", "harness/judge_guard.py",
    "cases.json", "manifest.json", "judges/crm-malicious-indirect-general-ai-restrictions-004/judge.py",
    "tools/crm_prepare.py", "tools/crm_row_fixture.py", "tools/crm_qual_server.py", "tools/crm_qual_worker.py",
)) + ("src/runtime/region_claim_receipt.py", "src/runtime/region_lock_cli.py", "src/runtime/cpu_region_lock.py")


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


def _cpu_set(text: str) -> set[int]:
    if not isinstance(text, str) or not text:
        raise ValueError("CPU list missing")
    result: set[int] = set()
    for part in text.split(","):
        if not re.fullmatch(r"\d+(?:-\d+)?", part):
            raise ValueError("invalid CPU list")
        lo, _, hi = part.partition("-")
        start, end = int(lo), int(hi or lo)
        if end < start or end > 191:
            raise ValueError("CPU range invalid")
        result.update(range(start, end + 1))
    return result


def _claim(seal: dict[str, Any], grant_raw: bytes, provenance: dict[str, Any]) -> dict[str, Any]:
    """Reopen provider receipts; the stored /proc/locks rows remain provider-reported."""
    pins = {"provider_sha256": PROVIDER_SHA256, "lock_sha256": LOCK_SHA256,
            "receipt_sha256": RECEIPT_SHA256, "expected_lock_root": str(LOCK_ROOT)}
    if seal.get("claim_pins") != pins:
        raise ValueError("provider pins differ from reviewed production sources")
    raw = {}
    for name in ("claim_open", "claim_close"):
        path, expected = seal.get(name + "_path"), seal.get(name + "_sha256")
        if not isinstance(path, str) or not Path(path).is_absolute() or not SHA256.fullmatch(str(expected or "")):
            raise ValueError("provider receipt locator missing")
        raw[name] = _read(Path(path), 1024 * 1024)
        if _hash(raw[name]) != expected:
            raise ValueError("provider receipt digest mismatch")
    opened, closed = _json(raw["claim_open"]), _json(raw["claim_close"])
    if (opened.get("schema") != "region-lock-claim.v1" or opened.get("phase") != "open"
            or opened.get("provider") != "region-lock" or closed.get("schema") != "region-lock-claim.v1"
            or closed.get("phase") != "close" or opened.get("lock_root") != str(LOCK_ROOT)):
        raise ValueError("provider identity or production lock root mismatch")
    if (not re.fullmatch(r"[0-9a-f]{32}", str(opened.get("claim_id", "")))
            or any(type(opened.get(k)) is not int or opened[k] <= 0 for k in ("provider_pid", "provider_pid_starttime"))
            or any(opened.get(k) != closed.get(k) for k in ("claim_id", "provider_pid", "provider_pid_starttime"))
            or type(closed.get("child_rc")) is not int
            or closed.get("open_path") != seal["claim_open_path"]
            or closed.get("open_sha256") != _hash(raw["claim_open"])):
        raise ValueError("provider open/close identity mismatch")
    for field, expected in (("provider", PROVIDER_SHA256), ("lock", LOCK_SHA256), ("receipt", RECEIPT_SHA256)):
        path = opened.get(field + "_source_path")
        if (opened.get(field + "_source_sha256") != expected or not isinstance(path, str)
                or not Path(path).is_absolute() or _hash(_read(Path(path))) != expected):
            raise ValueError("provider source bytes differ from reviewed pin")
    grant_id = provenance["grant_id"]
    if (not re.fullmatch(r"[A-Za-z0-9_-]+", grant_id)
            or opened.get("grant_id") != grant_id
            or opened.get("grant_path") != str(GRANT_ROOT / (grant_id + ".grant"))
            or opened.get("grant_copy_path") != seal["grant_receipt_path"]
            or opened.get("grant_sha256") != _hash(grant_raw)):
        raise ValueError("grant path, ID or captured bytes differ")
    fields = {}
    for entry in grant_raw.decode().split():
        key, sep, val = entry.partition("=")
        if not sep or not val or key in fields:
            raise ValueError("grant bytes malformed")
        fields[key] = val
    regions = opened.get("regions")
    if (not isinstance(regions, list) or not regions or len(set(regions)) != len(regions)
            or any(x not in ("q0", "q1", "q2", "q3") for x in regions)):
        raise ValueError("provider region list malformed")
    cpus = {cpu for region in regions for cpu in range(int(region[1]) * 24, (int(region[1]) + 1) * 24)}
    if (_cpu_set(opened.get("cpu_list")) != cpus or _cpu_set(fields.get("regions")) != cpus
            or fields.get("start") != opened.get("grant_start") or fields.get("end") != opened.get("grant_end")):
        raise ValueError("grant and claimed CPU scope differ")
    proof = opened.get("flock_proof")
    if not isinstance(proof, list) or len(proof) != len(regions) or {p.get("region") for p in proof if isinstance(p, dict)} != set(regions):
        raise ValueError("provider flock records incomplete")
    for item in proof:
        if item.get("path") != str(LOCK_ROOT / f"cpu_region.GLOBAL.{item['region']}.lock"):
            raise ValueError("provider flock path mismatch")
        parts = str(item.get("proc_locks_row", "")).split()
        try:
            major, minor, inode = parts[5].split(":")
            if (parts[1:4] != ["FLOCK", "ADVISORY", "WRITE"] or int(parts[4]) != opened["provider_pid"]
                    or (int(major, 16), int(minor, 16), int(inode)) !=
                    (item["device_major"], item["device_minor"], item["inode"])):
                raise ValueError("provider flock record inconsistent")
        except (IndexError, TypeError, ValueError, KeyError) as exc:
            raise ValueError("provider flock record invalid") from exc
    began, ended = _time(seal["capture_start_utc"]), _time(seal["terminal_utc"])
    if not (_time(fields["start"]) <= _time(opened["opened_utc"]) <= began <= ended
            <= _time(closed["closed_utc"]) <= _time(seal["sealed_utc"])
            and ended <= _time(fields["end"])):
        raise ValueError("capture is outside declared claim or grant window")
    return {"claim_id": opened["claim_id"], "regions": regions, "grant_id": grant_id,
            "provider_pid": opened["provider_pid"], "child_rc": closed["child_rc"],
            "scope": "provider-reported flock witness; issuer and loaded-bytecode identity unverified"}


def _source(manifest_raw: bytes, provenance: dict[str, Any], seal: dict[str, Any]) -> dict[str, Any]:
    """Independently re-read Git blobs and source files; loaded code remains unknown."""
    data = _json(manifest_raw)
    if (not isinstance(data, dict) or data.get("schema") != "dtap.crm_source_manifest.v1"
            or data.get("source_commit") != provenance["source_commit"]):
        raise ValueError("source manifest schema or commit mismatch")
    files = data.get("files")
    root = data.get("repo_path")
    if (not isinstance(files, dict) or set(files) != set(SOURCE_FILES)
            or not isinstance(root, str) or not Path(root).is_absolute()):
        raise ValueError("source manifest membership or repo missing")
    mapping = json.dumps(files, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    if _hash(mapping) != data.get("source_tree_sha256") or data["source_tree_sha256"] != provenance["source_tree_sha256"]:
        raise ValueError("source manifest tree digest mismatch")
    repo = Path(root)
    for name in SOURCE_FILES:
        digest = files[name]
        if not SHA256.fullmatch(str(digest or "")) or _hash(_read(repo / name)) != digest:
            raise ValueError("original source file differs from manifest")
        result = subprocess.run(["git", "-C", str(repo), "show", f'{provenance["source_commit"]}:{name}'],
                                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        if _hash(result.stdout) != digest:
            raise ValueError("source bytes differ from declared Git commit")
    if files[DTAP + "harness/crm_pair_capture.py"] != PRODUCER_SHA256:
        raise ValueError("capture producer differs from reviewed source")
    if _hash(_read(Path(seal["producer_path"]))) != files[DTAP + "harness/crm_pair_capture.py"]:
        raise ValueError("captured producer differs from source manifest")
    return {"source_commit": provenance["source_commit"], "source_tree_sha256": data["source_tree_sha256"],
            "scope": "working files and Git blobs only; loaded bytecode and runtime identity unverified"}


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
        native = _open_pair(Path(path).absolute())
        seal = native["seal"]
        native["claim_scope"] = _claim(seal, _read(Path(seal["grant_receipt_path"])), seal["provenance"])
        native["source_scope"] = _source(_read(Path(seal["source_manifest_path"])), seal["provenance"], seal)
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError, subprocess.SubprocessError) as exc:
        raise ProjectionError("CRM pair original custody refused: " + type(exc).__name__) from exc
    return (native,)


@register(SOURCE_KIND)
def project(native: dict[str, Any]) -> ClaimTuple:
    """Project only the producer-reported pair completion, never its authority."""
    reopened = native_rows(native["seal_path"])
    if len(reopened) != 1 or reopened[0] != native:
        raise ProjectionError("CRM pair changed since original reader pass")
    seal = native["seal"]
    provenance = seal["provenance"]
    arms = native["results"]
    count = sum(arms[arm]["status"] == "complete" for arm in ("control", "attack"))
    caveat = ("Producer-reported CRM diagnostic only; scheduler issuer, same-UID forgery resistance, "
              "loaded code, actual model identity and physical-authority warrant are UNKNOWN. "
              "No security efficacy, promotion or policy claim.")
    return ClaimTuple(
        measurement_id="dtap-crm-pair:" + native["seal_sha256"], metric="producer_reported_completed_arms",
        value=count, unit="arms", date=seal["terminal_utc"], category="CANDIDATE",
        metric_direction="higher_better", protocol_id="", reps=1,
        reps_basis="one producer-reported pair; no population or independent replicate",
        claim=f"Producer reports {count} completed arms in one CRM diagnostic. {caveat}",
        attestation_locator="dtap-crm-pair:" + native["seal_sha256"],
        attestation_sha256=native["seal_sha256"], source_kind=SOURCE_KIND,
        observation={"outcome_native": "; ".join(
            f"{arm}={arms[arm]['status']}/{arms[arm]['delivery']}" for arm in ("control", "attack"))},
        extra={"seal_sha256": native["seal_sha256"], "source_commit": provenance["source_commit"],
               "source_tree_sha256": provenance["source_tree_sha256"], "scope": caveat,
               "producer_declared_model_sha256": provenance["model_sha256"],
               "producer_declared_backend": provenance.get("backend", "unknown"),
               "skill_injection": "not_tested", "provider_flock_witness": "provider_reported",
               "scheduler_issuer": "UNKNOWN", "loaded_code": "UNKNOWN", "physical_authority": "UNKNOWN"},
    )
