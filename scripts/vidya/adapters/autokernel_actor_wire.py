"""VB-AK-NATIVE-WIRE-WRITE: strict reader/projection for AutoKernel native actor-wire matrix finalization.

Source: research ``loop/actor_wire_gate.py`` (``epyc.autokernel.actor_wire.v1`` request/PASS record) and
``loop/actor_wire_test.py`` (``matrix-results.json`` + per-seat evidence ``<seat-digest>.json``).

AUDIT (2026-11-03). ``autokernel_actor_seat`` reads only ``epyc.autokernel.actor_call.v1`` lines and
``epyc.autokernel.seat_ab_arm.v1`` arms; ``actor_wire.v1`` is a foreign schema to it (skipped), and
the actor-call *metrics* rows carry no wire checks. So the ladder is reused, not the reader:
this adapter is a **verifier-class** projection (SC57) and ``claim_tuple.grade()`` decides.

PRODUCER GAP. The producer today writes ``actor-wire-pass.json`` ONLY on PASS (a FAIL/abort unlinks it)
and a schema-less, unhashed ``matrix-results.json``. Neither binds the decided request, the per-seat
evidence digests and the cleanup state under one self-hash, and neither survives as a FAIL/aborted
record. This reader therefore consumes a *finalization record* the matrix driver must write at the end
of every run, whatever the outcome (``epyc.autokernel.actor_wire_final.v1``, closed field set below).
Legacy ``actor-wire-pass.json`` / ``matrix-results.json`` / evidence files DECLINE: a tuple built from
them would be a retroactive warrant.

Doctrine: native wire outputs are verifier findings, not model-quality measurements; no timing and no
merge-validity claim; PASS, FAIL, aborted and unvisited ride verbatim; the six native-provider checks
and the three mocked process controls are projected as SEPARATE tuples and are never merged.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

ADAPTER_ID = "vidya.adapters.autokernel_actor_wire/v1"
AUTHORITY = "verifier_finding_no_timing_no_merge_validity_no_retroactive_warrant"
SOURCE_KIND = "autokernel-actor-wire"
#: The planning consumer these harness verifier findings are scoped to (VB-AK-WIRE-PLANNER-TIER).
PLANNER_CONSUMER = "autokernel.planner"
FINAL_SCHEMA = "epyc.autokernel.actor_wire_final.v1"
WIRE_SCHEMA = "epyc.autokernel.actor_wire.v1"
#: Prospective only: a finalization stamped before this is refused, never projected.
HOOK_SINCE = "2026-11-03T00:00:00Z"

# Pinned mirror of research actor_wire_gate.CHECKS / EVIDENCE_KINDS (a drift fails the self-test).
CHECKS = ("native_provider_reply", "large_reply_byte_exact", "large_prompt_on_wire",
          "role_options_on_wire", "readonly_denial_continues", "actor_timeout",
          "rc1_salvage", "signal_transient", "template_echo_rejected")
NATIVE_CHECKS = CHECKS[:6]
MOCKED_CONTROLS = CHECKS[6:]
EVIDENCE_KINDS = {"native_provider": list(NATIVE_CHECKS), "mocked_process_controls": list(MOCKED_CONTROLS)}
PROTOCOLS = {"codex": "responses", "claude": "messages", "opencode": "chat/completions"}

FINAL_FIELDS = {"schema", "finalized_utc", "producer", "request", "status", "outcomes", "attempted",
                "expected", "abort", "unvisited", "results", "evidence", "cleanup", "record_sha256"}
PRODUCER_FIELDS = {"repo", "commit", "module"}
REQUEST_FIELDS = {"schema", "seats", "actor_config_digest", "suite"}
OUTCOME_FIELDS = {"seat", "backend", "role", "status"}
RESULT_FIELDS = {"checks", "evidence_kinds", "requests_sha256", "request_count", "provider_protocol",
                 "readonly_denial"}
CLEANUP_FIELDS = {"cleanup_uncertain", "seats"}
CLEANUP_SEAT_FIELDS = {"receipts", "all_verified"}

METRIC_NATIVE = "actor_wire_seat_native_provider_checks_passed"
METRIC_MOCKED = "actor_wire_seat_mocked_process_controls_passed"
METRIC_SEAT_FAIL = "actor_wire_seat_passed"
METRIC_MATRIX = "actor_wire_matrix_complete"

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _hex(value: Any) -> bool:
    return isinstance(value, str) and bool(_HEX64.match(value))


def _int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def seal(record: dict) -> dict:
    """Reference writer for the producer: return ``record`` with its ``record_sha256`` set."""
    body = {k: v for k, v in record.items() if k != "record_sha256"}
    return {**body, "record_sha256": digest(body)}


def _exact(value: Any, fields: set, what: str, problems: list) -> bool:
    if not isinstance(value, dict) or set(value) != fields:
        got = sorted(value) if isinstance(value, dict) else type(value).__name__
        problems.append(f"{what}: fields must be exactly {sorted(fields)}, got {got}")
        return False
    return True


def validate_final(record: Any) -> list[str]:
    """Every reason ``record`` is not a producer-authored, internally consistent finalization."""
    problems: list[str] = []
    if not _exact(record, FINAL_FIELDS, "finalization", problems):
        return problems
    if record["schema"] != FINAL_SCHEMA:
        problems.append(f"schema must be {FINAL_SCHEMA}")
    if not isinstance(record["finalized_utc"], str) or not _UTC.match(record["finalized_utc"]):
        problems.append("finalized_utc must be YYYY-MM-DDTHH:MM:SSZ")
    elif record["finalized_utc"] < HOOK_SINCE:
        problems.append(f"finalized_utc precedes the prospective hook {HOOK_SINCE}")
    body = {k: v for k, v in record.items() if k != "record_sha256"}
    try:
        if record["record_sha256"] != digest(body):
            problems.append("record_sha256 does not re-derive")
    except (TypeError, ValueError):
        problems.append("record is not canonical JSON")
        return problems
    if _exact(record["producer"], PRODUCER_FIELDS, "producer", problems):
        if not all(isinstance(record["producer"][k], str) and record["producer"][k]
                   for k in PRODUCER_FIELDS):
            problems.append("producer fields must be nonempty strings")

    request = record["request"]
    if not _exact(request, REQUEST_FIELDS, "request", problems):
        return problems
    seats = request["seats"]
    if request["schema"] != WIRE_SCHEMA:
        problems.append(f"request.schema must be {WIRE_SCHEMA}")
    if not isinstance(seats, list) or not seats or not all(isinstance(s, dict) for s in seats):
        problems.append("request.seats must be a nonempty list of seat objects")
        return problems
    for i, seat in enumerate(seats):
        backend = seat.get("backend")
        if (not isinstance(backend, dict) or backend.get("kind") not in PROTOCOLS
                or not isinstance(seat.get("role"), str) or not _hex(seat.get("client_sha256"))
                or not isinstance(seat.get("seat"), dict) or not isinstance(seat.get("read_only"), bool)
                or not isinstance(seat.get("launch_config"), dict)
                or not isinstance(seat.get("timeout_s"), (int, float))
                or isinstance(seat.get("timeout_s"), bool)):
            problems.append(f"request.seats[{i}]: missing seat/client/config identity")
            return problems
        if seat["read_only"] != (seat["role"] == "critic"):
            problems.append(f"request.seats[{i}]: read_only contradicts role")
    keyed = {digest(s): s for s in seats}
    if seats != [keyed[k] for k in sorted(keyed)]:
        problems.append("request.seats must be unique and normalized (sorted by seat digest)")
        return problems
    if request["actor_config_digest"] != digest(seats):
        problems.append("request.actor_config_digest does not re-derive")
    suite = request["suite"]
    if not isinstance(suite, dict) or not suite or not all(
            isinstance(k, str) and _hex(v) for k, v in suite.items()):
        problems.append("request.suite must map source names to sha256")

    order = [digest(s) for s in seats]
    outcomes = record["outcomes"]
    if not isinstance(outcomes, list) or not all(
            _exact(o, OUTCOME_FIELDS | ({"error"} if isinstance(o, dict) and o.get("status") == "FAIL"
                                       else set()), "outcome", problems) for o in outcomes):
        return problems
    if not _int(record["attempted"]) or record["attempted"] != len(outcomes):
        problems.append("attempted must equal len(outcomes)")
    if not _int(record["expected"]) or record["expected"] != len(seats):
        problems.append("expected must equal len(request.seats)")
    if len(outcomes) > len(seats):
        problems.append("more outcomes than requested seats")
        return problems
    for i, o in enumerate(outcomes):
        if o["seat"] != order[i]:
            problems.append(f"outcomes[{i}].seat is not request seat {i} (the matrix runs in order)")
            continue
        if o["backend"] != seats[i]["backend"]["kind"] or o["role"] != seats[i]["role"]:
            problems.append(f"outcomes[{i}] backend/role contradict the request seat")
        if o["status"] not in ("PASS", "FAIL"):
            problems.append(f"outcomes[{i}].status must be PASS or FAIL verbatim")
        if o["status"] == "FAIL" and (not isinstance(o["error"], str) or not o["error"].strip()):
            problems.append(f"outcomes[{i}]: a FAIL carries its error text verbatim")
    if record["unvisited"] != order[len(outcomes):]:
        problems.append("unvisited must be exactly the request seats after the last outcome")

    abort = record["abort"]
    if abort is not None and (not isinstance(abort, str) or not abort.strip()):
        problems.append("abort must be null or the verbatim abort text")
    fails = [o for o in outcomes if o["status"] == "FAIL"]
    complete = len(outcomes) == len(seats) and abort is None
    expected_status = "PASS" if complete and not fails else "FAIL"
    if record["status"] != expected_status:
        problems.append(f"status {record['status']!r} contradicts outcomes/abort/unvisited "
                        f"(re-derives to {expected_status!r})")

    passes = {o["seat"]: seats[i] for i, o in enumerate(outcomes)
              if i < len(seats) and o["status"] == "PASS"}
    results = record["results"]
    if not isinstance(results, dict) or set(results) != set(passes):
        problems.append("results must cover exactly the PASS outcomes")
    else:
        for key, result in results.items():
            seat = passes[key]
            if not _exact(result, RESULT_FIELDS, f"results[{key[:12]}]", problems):
                continue
            if result["checks"] != {c: True for c in CHECKS}:
                problems.append(f"results[{key[:12]}]: a PASS needs all nine checks exactly true")
            if result["evidence_kinds"] != EVIDENCE_KINDS:
                problems.append(f"results[{key[:12]}]: native provider checks and mocked controls "
                                "must be distinguished exactly")
            if not _hex(result["requests_sha256"]) or not _int(result["request_count"]) \
                    or result["request_count"] < 1:
                problems.append(f"results[{key[:12]}]: native provider requests were not captured")
            if result["provider_protocol"] != PROTOCOLS[seat["backend"]["kind"]]:
                problems.append(f"results[{key[:12]}]: provider_protocol contradicts the backend")
            want = "passed" if seat["read_only"] else "not-readonly"
            if result["readonly_denial"] != want:
                problems.append(f"results[{key[:12]}]: readonly_denial contradicts the role")

    evidence = record["evidence"]
    attempted_keys = {o["seat"] for o in outcomes}
    if not isinstance(evidence, dict) or set(evidence) != attempted_keys:
        problems.append("evidence must have one entry per attempted seat")
    else:
        for key, entry in evidence.items():
            if not _exact(entry, {"sha256"}, f"evidence[{key[:12]}]", problems):
                continue
            if entry["sha256"] is not None and not _hex(entry["sha256"]):
                problems.append(f"evidence[{key[:12]}].sha256 must be sha256 or null (not written)")

    cleanup = record["cleanup"]
    if _exact(cleanup, CLEANUP_FIELDS, "cleanup", problems):
        if not isinstance(cleanup["cleanup_uncertain"], bool):
            problems.append("cleanup.cleanup_uncertain must be a bool")
        cs = cleanup["seats"]
        if not isinstance(cs, dict) or set(cs) != attempted_keys:
            problems.append("cleanup.seats must have one entry per attempted seat")
        elif isinstance(cleanup["cleanup_uncertain"], bool):
            for key, entry in cs.items():
                if not _exact(entry, CLEANUP_SEAT_FIELDS, f"cleanup[{key[:12]}]", problems):
                    continue
                if not _int(entry["receipts"]) or not isinstance(entry["all_verified"], bool):
                    problems.append(f"cleanup[{key[:12]}] malformed")
                elif key in passes and (entry["receipts"] < 1 or not entry["all_verified"]):
                    problems.append(f"cleanup[{key[:12]}]: a PASS seat needs verified owned-call cleanup")
            if cleanup["cleanup_uncertain"] and not (record["status"] == "FAIL" and abort):
                problems.append("cleanup uncertainty must finalize as an aborted FAIL")
    return problems


def _evidence_state(directory: Path, record: dict, key: str) -> dict:
    """Re-read one seat's native evidence snapshot. Absent -> state only; tampered -> refuse."""
    entry = record["evidence"][key]
    path = directory / f"{key}.json"
    if entry["sha256"] is None:
        return {"present": False, "path": str(path), "sha256": None, "reason": "producer wrote none"}
    if not path.is_file():
        return {"present": False, "path": str(path), "sha256": entry["sha256"],
                "reason": "evidence file absent"}
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
        raise ProjectionError(f"{path}: seat evidence differs from the finalization pin")
    try:
        body = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProjectionError(f"{path}: seat evidence is not JSON ({exc})") from exc
    seats = {digest(s): s for s in record["request"]["seats"]}
    if not isinstance(body, dict) or body.get("seat") != seats[key]:
        raise ProjectionError(f"{path}: seat evidence does not describe its request seat")
    if body.get("suite") != record["request"]["suite"]:
        raise ProjectionError(f"{path}: seat evidence suite differs from the finalized request suite")
    result = record["results"].get(key)
    if result is not None:
        reqs = body.get("requests")
        if (not isinstance(reqs, list) or digest(reqs) != result["requests_sha256"]
                or len(reqs) != result["request_count"]):
            raise ProjectionError(f"{path}: captured requests do not re-derive requests_sha256")
    for name, cap in (body.get("native_captures") or {}).items():
        try:
            if hashlib.sha256(base64.b64decode(cap["bytes_base64"], validate=True)).hexdigest() \
                    != cap["sha256"]:
                raise ValueError("digest mismatch")
        except (KeyError, TypeError, ValueError) as exc:
            raise ProjectionError(f"{path}: native capture {name!r} does not re-derive ({exc})") from exc
    return {"present": True, "path": str(path), "sha256": entry["sha256"], "reason": None}


def native_rows(path: str | Path) -> tuple[dict, ...]:
    """Natives from one finalization file. Foreign/legacy/absent -> (); invalid v1 -> ProjectionError."""
    p = Path(path)
    if not p.is_file():
        return ()
    raw = p.read_bytes()
    try:
        record = json.loads(raw)
    except json.JSONDecodeError:
        return ()
    if not isinstance(record, dict) or record.get("schema") != FINAL_SCHEMA:
        return ()  # legacy actor-wire-pass.json / matrix-results.json / evidence: never retrofitted
    problems = validate_final(record)
    if problems:
        raise ProjectionError(f"{p}: actor-wire finalization does not re-derive: " + "; ".join(problems))
    file_sha = hashlib.sha256(raw).hexdigest()
    base = {"record": record, "path": str(p), "file_sha256": file_sha}
    rows = [{**base, "kind": "matrix", "metric": METRIC_MATRIX}]
    for i, outcome in enumerate(record["outcomes"]):
        key = outcome["seat"]
        evidence = _evidence_state(p.parent, record, key)
        if outcome["status"] == "PASS":
            for metric in (METRIC_NATIVE, METRIC_MOCKED):
                rows.append({**base, "kind": "seat", "metric": metric, "seat_digest": key,
                             "index": i, "evidence": evidence})
        else:
            rows.append({**base, "kind": "seat", "metric": METRIC_SEAT_FAIL, "seat_digest": key,
                         "index": i, "evidence": evidence})
    return tuple(rows)


def _seat_text(record: dict, key: str, index: int) -> str:
    seat = record["request"]["seats"][index]
    b = seat["backend"]
    cfg = digest(seat["seat"])[:12]
    return (f"seat {key[:12]} ({b['kind']}:{b.get('model')} role {seat['role']}, client sha256 "
            f"{seat['client_sha256'][:12]}, seat-config {cfg}, launch-config "
            f"{digest(seat['launch_config'])[:12]}, timeout {seat['timeout_s']}s) of request "
            f"{record['request']['actor_config_digest'][:12]} / suite {digest(record['request']['suite'])[:12]}")


_TAIL = ("Verifier finding of the wire-admission suite, not a model-quality measurement; no timing and "
         "no merge-validity claim.")


def _matrix_proposition(record: dict) -> str:
    outcomes = record["outcomes"]
    p = sum(o["status"] == "PASS" for o in outcomes)
    f = len(outcomes) - p
    abort = record["abort"] if record["abort"] is not None else "none"
    return (f"AutoKernel native actor-wire matrix finalization {record['record_sha256'][:12]} for request "
            f"{record['request']['actor_config_digest'][:12]} (suite {digest(record['request']['suite'])[:12]}), "
            f"finalized {record['finalized_utc']}: status {record['status']}; attempted "
            f"{record['attempted']} of {record['expected']} seats (PASS {p}, FAIL {f}); unvisited "
            f"{[u[:12] for u in record['unvisited']]}; abort: {abort!r}; cleanup uncertain: "
            f"{str(record['cleanup']['cleanup_uncertain']).lower()}. {_TAIL}")


def _seat_proposition(native: dict) -> str:
    record, key, i = native["record"], native["seat_digest"], native["index"]
    who = _seat_text(record, key, i)
    clean = record["cleanup"]["seats"][key]
    tail = (f" Owned-call cleanup receipts {clean['receipts']}, all verified: "
            f"{str(clean['all_verified']).lower()}. {_TAIL}")
    if native["metric"] == METRIC_NATIVE:
        return (f"AutoKernel {who} passed the six NATIVE-provider checks {list(NATIVE_CHECKS)} against the "
                f"installed client over {record['results'][key]['provider_protocol']} "
                f"({record['results'][key]['request_count']} requests captured, sha256 "
                f"{record['results'][key]['requests_sha256'][:12]})." + tail)
    if native["metric"] == METRIC_MOCKED:
        return (f"AutoKernel {who} passed the three MOCKED process controls {list(MOCKED_CONTROLS)}; these "
                "are failure-path controls on fake processes and are not native protocol proof." + tail)
    error = record["outcomes"][i]["error"]
    return (f"AutoKernel {who} FAILED its wire checks; producer error verbatim: {error!r}. The producer "
            "does not decompose which check failed." + tail)


def _extra(native: dict) -> dict:
    record = native["record"]
    return {"authority": AUTHORITY, "schema": record["schema"], "producer": record["producer"],
            "record_path": native["path"], "record_file_sha256": native["file_sha256"],
            "record_sha256": record["record_sha256"], "finalized_utc": record["finalized_utc"],
            "status": record["status"], "attempted": record["attempted"], "expected": record["expected"],
            "abort": record["abort"], "unvisited": list(record["unvisited"]),
            "outcomes": record["outcomes"], "cleanup": record["cleanup"],
            "request_actor_config_digest": record["request"]["actor_config_digest"],
            "suite": record["request"]["suite"]}


@register(SOURCE_KIND, source_class="verifier", decided_proposition_field="proposition")
def project(native: Any) -> ClaimTuple:
    """Projection only. Re-reads the file so a caller cannot hand in a row the reader would refuse."""
    if not isinstance(native, dict) or not isinstance(native.get("path"), str):
        raise ProjectionError("actor-wire native row must retain its finalization path")
    fresh = native_rows(native["path"])
    if native not in fresh:
        raise ProjectionError("actor-wire native row differs from its re-read finalization")
    record = native["record"]
    extra = _extra(native)
    if native["kind"] == "matrix":
        text = _matrix_proposition(record)
        value = int(record["status"] == "PASS")
        mid = f"ak-actor-wire:{record['record_sha256'][:16]}:matrix"
        sha, verified, present = native["file_sha256"], True, True
        locator = f"ak-actor-wire:{native['path']}"
    else:
        text = _seat_proposition(native)
        value = int(native["metric"] != METRIC_SEAT_FAIL)
        key, ev = native["seat_digest"], native["evidence"]
        mid = f"ak-actor-wire:{record['record_sha256'][:16]}:{key[:16]}:{native['metric']}"
        extra.update({"seat_digest": key, "seat": record["request"]["seats"][native["index"]],
                      "outcome": record["outcomes"][native["index"]],
                      "result": record["results"].get(key), "evidence": ev,
                      "evidence_kind": {METRIC_NATIVE: "native_provider",
                                        METRIC_MOCKED: "mocked_process_controls"}.get(native["metric"])})
        present = ev["present"]
        sha = ev["sha256"] or native["file_sha256"]
        verified = True if present else None
        locator = f"ak-actor-wire:{ev['path'] if present else native['path']}#seat:{key}"
    return ClaimTuple(
        measurement_id=mid, metric=native["metric"], value=value, date=record["finalized_utc"][:10],
        category="CANDIDATE", metric_direction="higher_better", protocol_id="", unit="boolean",
        claim=text, decided_proposition=text, source_class="verifier", binding_kind="identity",
        attestation_sha256=sha, attestation_locator=locator, attestation_present=present,
        attestation_verified=verified, source_kind=SOURCE_KIND, extra=extra,
        applicability={"consumer": PLANNER_CONSUMER, "scope_basis": "native"})


def frames_for_path(path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY))
    return frames


__all__ = ["ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "FINAL_SCHEMA", "frames_for_path", "native_rows",
           "project", "seal", "validate_final"]
