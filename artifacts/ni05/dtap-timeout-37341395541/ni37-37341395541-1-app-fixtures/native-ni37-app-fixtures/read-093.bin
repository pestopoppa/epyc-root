"""Immutable per-case trace recording and replay (TU-DTAP-1).

A trace is an append-only JSONL file whose records form a SHA-256 hash chain:
every record carries `seq`, the canonical SHA-256 of the previous record's
payload, and the SHA-256 of its own canonical payload. The final record closes
the chain with `trace_id` = SHA-256 over the last payload, and the summary
records every event type + a `root` digest over the full canonical body.

  * canonical payload bytes = json.dumps(payload, sort_keys=True,
    separators=(",", ":"), ensure_ascii=False).encode()
  * verify_trace() re-derives the whole chain and the root digest; any
    insertion, deletion, reorder or byte change breaks it.
  * replay_trace() verifies, then re-applies the deterministic final-state
    judge to the recorded state snapshot and compares verdicts with the
    recorded judge_result — a mismatch is a typed HARNESS failure.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

from .outcomes import HarnessFailure

HARNESS_VERSION = "dtap-runner-0.1.0"


def canonical(payload: Dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256(payload: Dict[str, Any]) -> str:
    return hashlib.sha256(canonical(payload)).hexdigest()


class TraceRecorder:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("w", encoding="utf-8")
        self._seq = 0
        self._prev_hash = "0" * 64
        self._root = hashlib.sha256(b"dtap-trace-v1").digest()

    def record(self, event: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._seq += 1
        rec_payload = sha256(payload)
        self._root = hashlib.sha256(self._root + rec_payload.encode()).digest()
        record = {
            "seq": self._seq,
            "event": event,
            "prev": self._prev_hash,
            "payload_hash": rec_payload,
            "payload": payload,
        }
        line = json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n"
        self._fh.write(line)
        self._fh.flush()
        self._prev_hash = rec_payload
        return record

    def close(self) -> str:
        trace_id = self._prev_hash
        self.record(
            "trace_finalize",
            {"harness_version": HARNESS_VERSION, "trace_id": trace_id, "root": self._root.hex()},
        )
        self._fh.close()
        return trace_id


def verify_trace(path: Path) -> List[Dict[str, Any]]:
    """Verify the hash chain and root digest. Raises HarnessFailure on tamper."""
    try:
        lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    except FileNotFoundError as exc:
        raise HarnessFailure(f"trace not found: {path}") from exc
    prev = "0" * 64
    root = hashlib.sha256(b"dtap-trace-v1").digest()
    records: List[Dict[str, Any]] = []
    for i, line in enumerate(lines):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as exc:
            raise HarnessFailure(f"trace line {i} is not valid JSON") from exc
        if rec.get("prev") != prev:
            raise HarnessFailure(
                f"trace chain broken at record {i}: prev mismatch (seq={rec.get('seq')})"
            )
        if sha256(rec.get("payload", {})) != rec.get("payload_hash"):
            raise HarnessFailure(f"trace chain broken at record {i}: payload hash mismatch")
        # The root digest covers every record except the finalize record itself
        # (the recorder computes it before appending the finalize hash).
        if i < len(lines) - 1:
            root = hashlib.sha256(root + rec["payload_hash"].encode()).digest()
        prev = rec["payload_hash"]
        records.append(rec)
    finalize = records[-1]
    if finalize.get("event") != "trace_finalize":
        raise HarnessFailure("trace missing trace_finalize record")
    if finalize["payload"].get("root") != root.hex():
        raise HarnessFailure("trace root digest mismatch (tampered)")
    if finalize["payload"].get("trace_id") != finalize.get("prev"):
        raise HarnessFailure("trace trace_id mismatch (tampered)")
    return records


def extract_run_snapshot(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Pull the final state snapshot + judge result + run result from a verified trace."""
    state = None
    judge_result = None
    run_result = None
    responses = []
    for rec in records:
        p = rec["payload"]
        if rec["event"] == "state_snapshot":
            state = p.get("state")
        elif rec["event"] == "agent_response":
            responses.append(p.get("text", ""))
        elif rec["event"] == "judge_result":
            judge_result = p
        elif rec["event"] == "run_result":
            run_result = p.get("result") or p
    if state is None or judge_result is None or run_result is None:
        raise HarnessFailure("trace missing state_snapshot/judge_result/run_result records")
    return {
        "case_id": run_result.get("case_id"),
        "arm": run_result.get("arm"),
        "seed": run_result.get("seed"),
        "state": state,
        "agent_responses": responses,
        "judge_result": judge_result,
        "run_result": run_result,
    }
