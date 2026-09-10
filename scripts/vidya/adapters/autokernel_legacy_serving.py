"""Direct serving observations; no protocol, eligibility, or placement warrant.

Only prospective producer captures are admitted. The native comparison is reopened
and rederived, including original vectors, input identity and CPU dependency bytes.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

from claim_tuple import ClaimTuple, ProjectionError, register

ADAPTER_ID = "vidya.adapters.autokernel_legacy_serving/v1"
RECEIPT_SCHEMA = "epyc.vidya.legacy_serving_receipt.v1"
_CAPTURE = "epyc.vidya.legacy_serving_capture.v1"
_MAX_BYTES = 64 << 20


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


def _source(receipt, locator):
    if set(receipt) != {"schema", "capture_id", "capture_sha256", "native_reference"}:
        raise ProjectionError("legacy serving receipt fields differ")
    ident = receipt["capture_id"]
    if not isinstance(ident, str) or not re.fullmatch("[0-9a-f]{64}", ident):
        raise ProjectionError("legacy serving capture ID is malformed")
    ref = receipt["native_reference"]
    if (not isinstance(ref, dict) or set(ref) != {"path", "sha256", "size"}
            or ref["path"] != f"sources/{ident}.json"
            or type(ref["size"]) is not int or not 0 < ref["size"] <= _MAX_BYTES):
        raise ProjectionError("legacy serving source reference differs")
    if not locator.startswith("autokernel:"):
        raise ProjectionError("legacy serving receipt needs its original file locator")
    directory = Path(locator.removeprefix("autokernel:")).parent
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    root_fd = os.open(directory, flags | os.O_DIRECTORY)
    try:
        sources_fd = os.open("sources", flags | os.O_DIRECTORY, dir_fd=root_fd)
        try:
            fd = os.open(f"{ident}.json", flags, dir_fd=sources_fd)
            try:
                before = os.fstat(fd)
                if not stat.S_ISREG(before.st_mode) or before.st_size != ref["size"]:
                    raise ProjectionError("legacy serving source is not the original bounded file")
                with os.fdopen(fd, "rb", closefd=False) as stream:
                    raw = stream.read(_MAX_BYTES + 1)
                after = os.fstat(fd)
                if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                    raise ProjectionError("legacy serving source changed during read")
            finally:
                os.close(fd)
        finally:
            os.close(sources_fd)
    finally:
        os.close(root_fd)
    if len(raw) != ref["size"] or hashlib.sha256(raw).hexdigest() != ref["sha256"]:
        raise ProjectionError("legacy serving source digest differs")
    return json.loads(raw)


def _rows(source, receipt):
    if not isinstance(source, dict) or not isinstance(source.get("comparison"), dict):
        raise ProjectionError("legacy serving native comparison is not an object")
    comparison = source["comparison"]
    capture = comparison["belief_capture"]
    if (not isinstance(capture, dict)
            or set(capture) != {"schema", "inputs", "capture_id", "native_sha256", "belief_measurements", "capture_sha256"}
            or capture["schema"] != _CAPTURE
            or capture["capture_sha256"] != receipt["capture_sha256"]
            or _digest({key: value for key, value in capture.items() if key != "capture_sha256"}) != capture["capture_sha256"]):
        raise ProjectionError("legacy serving prospective capture differs")
    inputs = capture["inputs"]
    if (set(inputs) != {"producer", "issued_at", "recipe", "pairs", "resolved_arms", "build_paths", "requests",
                       "protocol_id", "loaded_instrument_attestation"}
            or inputs["producer"] != "autokernel.loop.serving_beliefs/v1"
            or inputs["protocol_id"] != ""
            or inputs["loaded_instrument_attestation"] != "not_recorded"):
        raise ProjectionError("legacy serving inputs imply unsupported authority")
    issued = datetime.fromisoformat(inputs["issued_at"])
    if issued.tzinfo is None:
        raise ProjectionError("legacy serving issue time lacks a timezone")
    native = {key: value for key, value in comparison.items()
              if key not in {"belief_capture", "surface", "baseline_scope"}}
    digest = _digest(native)
    if (native["schema"] != "epyc.autokernel.serving_ab.v1"
            or native["metric"] != "aggregate_tok_s"
            or inputs["recipe"]["metric"] != native["metric"]
            or _digest(inputs["recipe"]) != native["recipe_hash"]
            or native["np"] != inputs["recipe"]["np"]
            or capture["native_sha256"] != digest
            or capture["capture_id"] != receipt["capture_id"]
            or _digest({"native_sha256": digest, "inputs": inputs}) != capture["capture_id"]):
        raise ProjectionError("legacy serving native/input binding differs")
    pairs = inputs["pairs"]
    if type(pairs) is not int or not 1 <= pairs <= 64 or pairs != native["pairs"]:
        raise ProjectionError("legacy serving original launch count differs")
    if set(inputs["resolved_arms"]) != {"anchor", "candidate"}:
        raise ProjectionError("legacy serving original arm identity differs")
    if (not isinstance(inputs["build_paths"], dict) or set(inputs["build_paths"]) != {"anchor", "candidate"}
            or any(not isinstance(value, str) or not value for value in inputs["build_paths"].values())):
        raise ProjectionError("legacy serving supplied build paths are missing")
    for arm, resolved in inputs["resolved_arms"].items():
        if resolved is not None and (not isinstance(resolved, dict)
                                    or resolved.get("build_dir") != inputs["build_paths"][arm]):
            raise ProjectionError("legacy serving resolved/supplied build path differs")
    requests = inputs["requests"]
    if requests is not None:
        if (not isinstance(requests, list) or len(requests) != native["np"]
                or any(not isinstance(row, list) or len(row) != 2
                       or not isinstance(row[0], str) or not row[0]
                       or not isinstance(row[1], str) or not re.fullmatch("[0-9a-f]{64}", row[1]) for row in requests)
                or len({row[0] for row in requests}) != len(requests)):
            raise ProjectionError("legacy serving request rows differ")
        request_digest = hashlib.sha256(json.dumps(requests, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        if (native.get("request_digest") != request_digest
                or native.get("floor_request_digest") != (request_digest if native["noise_floor_pct"] is not None else None)):
            raise ProjectionError("legacy serving request/floor identity differs")
    rows = []
    for arm, category in (("anchor", "BASELINE"), ("candidate", "CANDIDATE")):
        samples, windows = native[f"{arm}_samples"], native[f"{arm}_residency"]
        resolved = inputs["resolved_arms"][arm]
        if (len(samples) != pairs or len(windows) != pairs
                or any(type(value) not in (int, float) or not math.isfinite(value) or value < 0 for value in samples)
                or median(samples) != native[f"{arm}_tok_s"]):
            raise ProjectionError("legacy serving original process vectors do not rederive")
        if any(not math.isfinite(row["window_end"]) or row["window_end"] < row["window_start"]
               for row in windows):
            raise ProjectionError("legacy serving observation window differs")
        date = datetime.fromtimestamp(max(row["window_end"] for row in windows), timezone.utc).isoformat()
        rows.append({"measurement_id": f"legacy-serving:{capture['capture_id']}:{arm}",
                     "metric": native["metric"], "value": native[f"{arm}_tok_s"],
                     "unit": "t/s", "metric_direction": "higher_better", "category": category,
                     "claim": f"{arm} observed median aggregate serving rate; protocol and scientific witnesses unqualified",
                     "date": date, "protocol_id": "", "reps": pairs,
                     "reps_basis": "scored:original independent server launches; not threads/prompts/affinity samples",
                     "extra": {"arm": arm, "capture_id": capture["capture_id"],
                               "native_sha256": digest,
                               "build_path": inputs["build_paths"][arm],
                               "recipe_hash": native["recipe_hash"],
                               "request_digest": native.get("request_digest"),
                               "resolved_snapshot_digest": None if resolved is None else resolved.get("snapshot_digest"),
                               "execution_digest": None if resolved is None else resolved.get("execution_digest"),
                               "model_path": inputs["recipe"]["model"],
                               "applicability": "direct_serving_observation_only",
                               "cpu_facts": "dependency_only_not_placement_or_contention_proof"}})
    if rows != capture["belief_measurements"]:
        raise ProjectionError("legacy serving belief rows differ from original observations")
    return rows


def native_rows(receipt, *, receipt_locator, receipt_sha256, attestation_present=True):
    if not isinstance(receipt, dict) or receipt.get("schema") != RECEIPT_SCHEMA:
        return []
    try:
        source = _source(receipt, receipt_locator)
        rows = _rows(source, receipt)
    except (OSError, ValueError, KeyError, TypeError, OverflowError, RecursionError) as exc:
        raise ProjectionError(f"legacy serving source refused: {exc}") from exc
    return [{"receipt": receipt, "receipt_locator": receipt_locator,
             "receipt_sha256": receipt_sha256, "attestation_present": attestation_present,
             "claim": row} for row in rows]


@register("autokernel-legacy-serving")
def project(native):
    rows = native_rows(native["receipt"], receipt_locator=native["receipt_locator"],
                       receipt_sha256=native["receipt_sha256"],
                       attestation_present=native["attestation_present"])
    if native not in rows:
        raise ProjectionError("legacy serving projected row differs")
    return ClaimTuple(**native["claim"], source_kind="autokernel-legacy-serving",
                      attestation_locator=native["receipt_locator"],
                      attestation_sha256=native["receipt_sha256"],
                      attestation_present=native["attestation_present"])


class PlannerFeedback:
    """One loop's bounded observation recall, not scientific admission or ranking.

    The loop serializes access. Its private store ledger has one writer; the global
    belief ledger is never modified. Numeric/scope facts come from original source
    bytes because ClaimTuple frames intentionally do not carry those fields.
    """

    MAX_RECEIPTS = 128
    MAX_LEDGER_BYTES = 8 << 20
    MAX_LEDGER_FRAMES = 8192
    MAX_CONTEXT_ROWS = 12
    MAX_CONTEXT_BYTES = 32 << 10
    MAX_READ_BYTES = 128 << 20

    def __init__(self, store_root):
        from ledger import Ledger

        self.root = Path(store_root) / "serving-beliefs"
        self.ledger = Ledger(self.root / "feedback-ledger.jsonl")
        self.paths = {}
        self.notes = []
        self._records()
        consumed = 0
        # One bounded shallow discovery at startup, never a corpus walk per prompt.
        with os.scandir(self.root) as entries:
            for index, entry in enumerate(entries):
                if index >= self.MAX_RECEIPTS + 2:
                    self.notes.append("startup receipt scan bound reached; history recall is unchanged")
                    break
                if not re.fullmatch(r"[0-9a-f]{64}\.json", entry.name):
                    continue
                try:
                    receipt, _ = self._receipt(Path(entry.path))
                    consumed += receipt["native_reference"]["size"]
                    if consumed > self.MAX_READ_BYTES:
                        self.notes.append("startup source byte bound reached")
                        break
                    self.ingest(Path(entry.path))
                except Exception as exc:  # noqa: BLE001 - diagnostic recall never aborts a loop
                    self.notes.append(f"{entry.name}: {type(exc).__name__}: {exc}")
        self.notes = self.notes[-12:]

    def _records(self):
        if not self.ledger.path.exists():
            return []  # Fresh, not yet created; do not attest an existing empty ledger.
        if self.ledger.path.exists() and self.ledger.path.stat().st_size > self.MAX_LEDGER_BYTES:
            raise ProjectionError("serving feedback ledger byte bound reached")
        records = self.ledger.read_all()
        if len(records) > self.MAX_LEDGER_FRAMES:
            raise ProjectionError("serving feedback ledger frame bound reached")
        if self.ledger.verify():
            raise ProjectionError("serving feedback ledger integrity failed")
        return records

    def _receipt(self, path):
        if path.parent != self.root or not re.fullmatch(r"[0-9a-f]{64}\.json", path.name):
            raise ProjectionError("serving feedback requires its exact local receipt")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= 16384:
                raise ProjectionError("serving feedback receipt is not a bounded regular file")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                raw = stream.read(16385)
            if os.fstat(fd) != before or len(raw) != before.st_size:
                raise ProjectionError("serving feedback receipt changed during read")
        finally:
            os.close(fd)
        receipt = json.loads(raw)
        if receipt.get("schema") != RECEIPT_SCHEMA or path.stem != receipt.get("capture_id"):
            raise ProjectionError("serving feedback receipt identity differs")
        return receipt, hashlib.sha256(raw).hexdigest()

    def _read(self, path):
        receipt, receipt_sha256 = self._receipt(path)
        source = _source(receipt, f"autokernel:{path}")
        rows = _rows(source, receipt)
        return receipt, receipt_sha256, source, rows

    def ingest(self, path):
        """Ingest only this exported ID; exact frame IDs survive partial append/restart."""
        from claim_tuple import to_frames

        path = Path(path)
        receipt, receipt_sha256, source, rows = self._read(path)
        records = self._records()
        known = {record.frame.get("frame_id") for record in records}
        # Original archive time, not each import's wall clock, makes retries identical.
        stamp = source["recorded_at"]
        tuples = [ClaimTuple(**row, source_kind="autokernel-legacy-serving",
                            attestation_locator=f"autokernel:{path}",
                            attestation_sha256=receipt_sha256, attestation_present=True)
                  for row in rows]
        frames = [frame for item in tuples for frame in to_frames(
            item, as_of=stamp, adapter_id=ADAPTER_ID)]
        missing = [frame for frame in frames if frame["frame_id"] not in known]
        if len(records) + len(missing) > self.MAX_LEDGER_FRAMES:
            raise ProjectionError("serving feedback ledger frame bound reached")
        current_bytes = self.ledger.path.stat().st_size if self.ledger.path.exists() else 0
        if current_bytes + sum(len(json.dumps(frame).encode()) + 1024 for frame in missing) > self.MAX_LEDGER_BYTES:
            raise ProjectionError("serving feedback ledger byte bound reached")
        for frame in missing:
            self.ledger.append(frame)
        self.paths.pop(receipt["capture_id"], None)
        self.paths[receipt["capture_id"]] = (path, source["recorded_at"])
        if len(self.paths) > self.MAX_RECEIPTS:
            self.paths.pop(next(iter(self.paths)))
        return len(missing)

    def context(self, scope, *, as_of):
        from fold import fold
        from gate import UsePolicy, evaluate
        from lattice import parse_grade

        result = {"status": "observations_only", "rows": [], "errors": list(self.notes),
                  "scope": scope, "qualified_measurement": False}
        if not scope or any(scope.get(key) is None for key in (
                "epoch", "model", "recipe_hash", "request_digest", "anchor_execution_digest", "anchor_build")):
            result.update(status="scope_unavailable")
            return result
        folded = fold([record.frame for record in self._records()], as_of=as_of)
        policy = UsePolicy(use="planning-observation-recall-not-ranking",
                           floor=parse_grade("Judged/Located"))
        consumed = 0
        for path, _ in sorted(self.paths.values(), key=lambda item: item[1], reverse=True):
            if len(result["rows"]) >= self.MAX_CONTEXT_ROWS:
                break
            try:
                ref, _ = self._receipt(path)
                consumed += ref["native_reference"]["size"]
                if consumed > self.MAX_READ_BYTES:
                    result["errors"].append("query source byte bound reached")
                    break
                receipt, _, source, rows = self._read(path)
                native = source["comparison"]
                inputs = native["belief_capture"]["inputs"]
                arms = inputs["resolved_arms"]
                if (source.get("epoch") != scope["epoch"]
                        or native["recipe_hash"] != scope["recipe_hash"]
                        or native.get("request_digest") != scope["request_digest"]
                        or any(not isinstance(arm, dict) or arm.get("model") != scope["model"] for arm in arms.values())
                        or arms["anchor"].get("execution_digest") != scope["anchor_execution_digest"]
                        or inputs["build_paths"]["anchor"] != scope["anchor_build"]):
                    continue
                decisions = [evaluate(f"clm_{row['measurement_id']}", folded, policy).as_dict() for row in rows]
                entry = {"capture_id": receipt["capture_id"], "source": str(path),
                         "source_sha256": receipt["native_reference"]["sha256"],
                         "recorded_at": source["recorded_at"], "mechanism_id": source.get("mechanism_id"),
                         "epoch": source["epoch"], "belief_status": decisions,
                         "native_decisive": native["decisive"],
                         "recipe_hash": native["recipe_hash"], "request_digest": native["request_digest"],
                         "anchor_execution_digest": arms["anchor"]["execution_digest"],
                         "candidate_execution_digest": arms["candidate"]["execution_digest"],
                         "cpu_placement": native.get("cpu_placement", "unproven"),
                         "contention": native.get("contention", "unproven")}
                # Even a retracted/conflicted observation remains remembered by the
                # separate archive path; disputed numeric support is not current.
                if all(item["result"] == "allow" for item in decisions):
                    entry.update(anchor_tok_s=native["anchor_tok_s"], candidate_tok_s=native["candidate_tok_s"],
                                 pairs=native["pairs"], noise_floor_pct=native["noise_floor_pct"])
                result["rows"].append(entry)
                if len(json.dumps(result).encode()) > self.MAX_CONTEXT_BYTES:
                    result["rows"].pop()
                    result["errors"].append("context byte bound reached")
                    break
            except Exception as exc:  # noqa: BLE001 - retain visible refusal beside historical recall
                result["errors"].append(f"{path.name}: {type(exc).__name__}: {exc}")
        result["errors"] = [message[:400] for message in result["errors"][-12:]]
        result["frontier"] = folded.frontier
        result["as_of"] = as_of
        return result
