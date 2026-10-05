"""Prospective gap-extractor timestamp-pair integrity observations, never TTL policy."""
from __future__ import annotations

import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))
from claim_tuple import ClaimTuple, ProjectionError, register
import session_gap_measure as producer

ADAPTER_ID = "vidya.adapters.session_intercall_gap/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "session-intercall-gap-integrity"


def _file(path: Path, expected: str) -> bytes:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ProjectionError(f"gap extraction artifact hash differs: {path}")
    return raw


def native_rows(path: Path) -> list[dict]:
    path = Path(path)
    if not path.is_file():
        return []
    try:
        path = path.resolve()
        receipt_raw = path.read_bytes()
        receipt_sha = hashlib.sha256(receipt_raw).hexdigest()
        manifest_path = path.parent / "manifest.json"
        manifest_raw = manifest_path.read_bytes()
        manifest_sha = hashlib.sha256(manifest_raw).hexdigest()
        manifest = json.loads(manifest_raw)
        if manifest.get("schema") != "epyc.session_gap_manifest.v1" or manifest.get("method") != producer.METHOD:
            raise ProjectionError("gap extraction manifest or method differs")
        if (manifest.get("method_sha256") != producer.digest(producer.METHOD)
                or manifest.get("timestamp_precision") != producer.METHOD["timestamp_precision"]):
            raise ProjectionError("gap extraction method digest or timestamp precision differs")
        _file(path.parent / "extractor.py", manifest["extractor_sha256"])
        records, record_sources = {}, {}
        for source in manifest["sources"]:
            snapshot = Path(source["path"]).resolve()
            if snapshot.parent != path.parent.resolve():
                raise ProjectionError("gap snapshot escapes extraction directory")
            raw = _file(snapshot, source["sha256"])
            for line in raw.splitlines(keepends=True):
                if not line.endswith(b"\n"):
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if isinstance(record, dict) and record.get("schema") == producer.METHOD["serving_call_schema"]:
                    rid = record.get("record_id")
                    if not isinstance(rid, str) or not rid:
                        continue
                    if rid in records and records[rid] != record:
                        raise ProjectionError("gap source has conflicting record identities")
                    if rid not in records:
                        records[rid] = record
                        record_sources[rid] = {"path": str(snapshot), "sha256": source["sha256"]}
        from collections import defaultdict
        groups = defaultdict(list)
        for rid, record in records.items():
            call = producer.native_call(record, record_sources[rid])
            if call is not None:
                groups[(call["session_hash"], call["role"], call["client_class"])].append(call)
        adjacent = set()
        for group in groups.values():
            group.sort(key=lambda call: Decimal(call["sort_at"]))
            adjacent.update((first["record_id"], next_call["record_id"])
                            for first, next_call in zip(group, group[1:]))
        result = []
        seen = set()
        for line in receipt_raw.decode().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            producer.validate_row(row)
            if row["pair_id"] in seen:
                raise ProjectionError("gap capture duplicates a pair")
            seen.add(row["pair_id"])
            if row["manifest_sha256"] != manifest_sha or row["extractor_sha256"] != manifest["extractor_sha256"]:
                raise ProjectionError("gap capture does not bind its extraction manifest")
            if row["window"] not in manifest["windows"]:
                raise ProjectionError("gap window is not declared by the extraction manifest")
            if (row["first_record"], row["next_record"]) not in adjacent:
                raise ProjectionError("gap calls are not adjacent under the declared grouping")
            first, next_call = records[row["first_record"]], records[row["next_record"]]
            if row["source"] != record_sources[row["next_record"]]:
                raise ProjectionError("gap source does not bind the next native call")
            for record in (first, next_call):
                caller = record.get("caller") or {}
                session = (caller.get("trace_keys") or {}).get("x_session_id") or caller.get("session_id")
                if hashlib.sha256(session.encode()).hexdigest() != row["session_hash"]:
                    raise ProjectionError("gap session hash does not bind its native calls")
                if record["role"] != row["role"] or (caller.get("client_class") or "unknown") != row["client_class"]:
                    raise ProjectionError("gap role or class does not bind its native calls")
            if first.get("outcome") != "ok" or first.get("dispatched") is not True:
                raise ProjectionError("gap completion is not a completed dispatched call")
            if Decimal(row["t_done"]) != producer.epoch(first["ts_end"]):
                raise ProjectionError("gap completion timestamp differs from native call")
            queue = next_call.get("queue") or {}
            if row["timestamp_basis"] == "exact_backend_enqueue":
                enqueue = Decimal(str(queue["enqueue_ts_epoch"]))
            else:
                if "enqueue_ts_epoch" in queue:
                    raise ProjectionError("an exact enqueue was falsely labelled a proxy")
                enqueue = producer.epoch(next_call["ts_start"]) - Decimal(str(queue["pre_dispatch_wait_ms"])) / 1000
            if Decimal(row["t_next"]) != enqueue:
                raise ProjectionError("gap next timestamp differs from native call")
            result.append({"row": row, "manifest_path": str(manifest_path),
                           "receipt_path": str(path), "receipt_sha256": receipt_sha})
        return result
    except ProjectionError:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError, ArithmeticError) as exc:
        raise ProjectionError(f"gap extraction receipt refused: {exc}") from exc


@register(SOURCE_KIND, source_class="verifier", decided_proposition_field="row.claim")
def project(native: dict) -> ClaimTuple:
    try:
        row = native["row"]
        captured = next((item for item in native_rows(Path(native["receipt_path"]))
                         if item["row"]["pair_id"] == row["pair_id"]), None)
        if captured != native:
            raise ProjectionError("gap native input differs from its reverified receipt custody")
    except (ValueError, KeyError, TypeError, ArithmeticError, OSError) as exc:
        raise ProjectionError(f"gap receipt refused: {exc}") from exc
    return ClaimTuple(
        measurement_id=row["pair_id"], metric="session_gap.timestamp_pair_integrity", value=1,
        date=row["extracted_at"][:10], category="CANDIDATE", metric_direction="higher_better",
        claim=row["claim"], decided_proposition=row["claim"], source_class="verifier",
        binding_kind="identity", protocol_id="", unit="boolean",
        attestation_locator=f"{native['receipt_path']}#pair:{row['pair_id']};manifest:{native['manifest_path']}",
        source_kind=SOURCE_KIND, extra={"gap_s": row["gap_s"], "t_done": row["t_done"],
            "t_next": row["t_next"], "timestamp_basis": row["timestamp_basis"], "window": row["window"],
            "precision": row["precision"], "source": row["source"], "session_hash": row["session_hash"],
            "manifest_path": native["manifest_path"], "manifest_sha256": row["manifest_sha256"],
            "receipt_path": native["receipt_path"], "receipt_sha256": native["receipt_sha256"],
            "extractor_sha256": row["extractor_sha256"], "extracted_at": row["extracted_at"],
            "authority": "observation_only_no_optimization_or_ttl_policy"},
    )
