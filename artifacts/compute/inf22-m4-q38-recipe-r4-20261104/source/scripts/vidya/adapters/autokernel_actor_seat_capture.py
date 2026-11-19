"""VB-AK-SEAT write-side contract: AutoKernel actor-seat call records and seat A/B arm records.

Producer: ``epyc-inference-research`` research lane ``lane/ak-actor-seat-20260924`` (``e9495971``).
Two native records, one contract:

* **Call record** -- one JSON line per actor call, appended by ``loop/actors.py _record_call`` to
  ``<workspace>/../actor-replies/actor-calls.jsonl``. Schema :data:`CALL_SCHEMA`.
* **Arm record** -- one JSON document per A/B arm, written by the seat A/B driver
  (``/mnt/raid0/llm/tmp/ak-seat-ab/driver.py``) as ``result-<arm>.json``. Schema
  :data:`ARM_SCHEMA`.

This module is the executable form of the field list the producer must write. It is stdlib-only
so a research-side producer can import it from an ``EPYC_ROOT`` checkout (the
``score_beam_run.py`` / ``beam_memory_capture`` precedent) or mirror it; either way
:func:`validate_call_record` / :func:`validate_arm_record` decide whether a record carries a
usable claim tuple, and the strict reader (``autokernel_actor_seat.py``) imports them, so writer
and reader share one definition. :func:`build_call_record` / :func:`build_arm_record` are the
reference writers: they take what the producer knows at write time, add the self-hash, and
refuse (``CaptureError``) rather than emit a record that would not validate.

What the contract refuses to let anyone pretend:

* **No protocol is claimed that does not exist.** Nothing under ``measurement/protocols/``
  codifies an actor-seat session measurement, so ``protocol_id`` is written empty and
  ``claim_tuple.grade()`` caps every projected tuple at ``Judged/Located`` -- an OBSERVATION,
  never decision-gating. The field exists so a later codified protocol lifts the same records
  without re-projection.
* **n = 1.** A call record is one call. An arm record is one planner session per arm, with no
  repeat and no noise floor. ``reps`` is 1 and says so.
* **The comparison scope is the producer's words, carried verbatim.** The DS41-C20 A/B arms
  differ by seat AND by prompt from the historical plain run; the arm record's ``scope`` field is
  where the producer says that, and the reader puts it in the claim text. A seat EFFECT is never
  asserted by this contract.
* **Censored sessions project nothing.** A call that timed out or died on a signal
  (``returncode < 0``) measured the budget or the kill, not the seat. Its record is valid and
  kept, and it emits zero tuples -- never a wall time that is really a lower bound.
* **Pre-hook stays pre-hook.** A record without :data:`CALL_SCHEMA` / :data:`ARM_SCHEMA` is the
  pre-hook shape (``ts/backend/agent/returncode/wall_s/prompt_chars/opencode_config`` lines, or
  the 2026-09-24 ``result-bounded-v1-stopped.json``) and is never retrofitted. A record whose
  session started before :data:`HOOK_SINCE`, or that was written more than the backfill limit
  after its session finished, is refused.

The metric vocabulary below (unit + direction) is fixed by the schema version: a producer that
writes ``epyc.autokernel.actor_call.v1`` / ``seat_ab_arm.v1`` records that vocabulary; the reader
never infers a direction from a metric name.

**Backend kinds (INF-78 OAB-2, 2026-09-25).** :data:`BACKEND_KINDS` now includes
``orchestrator`` alongside the three CLI kinds (``codex``/``claude``/``opencode``): the loop can
call the orchestrator's ``/chat`` instead of one model directly (``actor_orchestrator
.OrchestratorBackend``). No field was added -- the same closed ``CALL_FIELDS``/``SEAT_FIELDS``
carry it, so the schema stays ``epyc.autokernel.actor_call.v1`` -- but two things this kind must
never claim are now enforced in :func:`_server`:

* the orchestrator's seat is its own ``/chat`` scoped to ``task_root`` (the existing
  ``workspace`` field already carries the lane worktree path -- nothing new there) and it has no
  opencode config, so the generic "not opencode" branches of :func:`_seat` already force
  ``bounded=False`` and null the opencode-only fields for it, same as ``codex``/``claude``;
* ``server.endpoint`` for this kind must be the orchestrator's own loopback base URL (default
  ``http://127.0.0.1:8000``, or an ``AK_ORCHESTRATOR_URL`` override -- still loopback), never a
  model-serving port; and ``server.served_model`` must be null, because the orchestrator routes
  per call rather than serving one fixed model -- **model provenance for an orchestrator call is
  the ``ChatResponse``'s ``routed_to``/``role_history``, which rides on the sibling
  ``actor_call_metrics.v1`` row (``actor_orchestrator.collect`` -> ``record["orchestrator"]
  ["provenance"]``), not on this closed VB-AK-SEAT contract.** A producer that has a served model
  to report writes it under the ``opencode``/``codex``/``claude`` kinds as before; this rule only
  narrows what an ``orchestrator`` record itself may assert.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from datetime import datetime
from typing import Any

CALL_SCHEMA = "epyc.autokernel.actor_call.v1"
ARM_SCHEMA = "epyc.autokernel.seat_ab_arm.v1"
CALL_LOG_NAME = "actor-calls.jsonl"
ARM_RESULT_GLOB = "result-*.json"

#: The contract was filed 2026-09-24; every record on disk at filing time is pre-hook (the last
#: one, the stopped bounded-v1 arm, finished 11:19:39Z). A record claiming the v1 schema for a
#: session that started earlier is a retrofit, not a capture.
HOOK_SINCE = "2026-09-24T12:00:00Z"
#: A call record is appended as the call returns; minutes of lag already means "written later".
MAX_CALL_RECORD_LAG_S = 600
#: An arm record is written after the session export; a day later is a backfill (DF2-4).
MAX_ARM_RECORD_LAG_S = 24 * 3600
#: ``wall_s`` is monotonic; the UTC stamps are second-resolution. Allowed disagreement.
WALL_TOLERANCE_S = 5.0

ROLES = frozenset({"planner", "author", "critic"})
ARM_ROLES = frozenset({"planner", "author"})
#: INF-78 OAB-2 (2026-09-25): `orchestrator` added alongside the three CLI kinds -- the
#: loop calls the ORCHESTRATOR's `/chat`, not one model, via `actor_orchestrator
#: .OrchestratorBackend`. Same CALL_SCHEMA, no new fields: `_server` below gates what an
#: orchestrator record may say about which model answered (see its docstring).
BACKEND_KINDS = frozenset({"codex", "claude", "opencode", "orchestrator"})
CATEGORIES = frozenset({"BASELINE", "CANDIDATE"})
#: The arm's reply verdict, decided by the producer with ``actors._parse_reply`` /
#: ``_is_template_echo`` at write time. ``template_echo`` is the 2026-09-24 bounded-v1 failure
#: (``{"abstain": "<reason>"}`` quoted from the prompt), recorded as itself, never as an abstain.
VERDICTS = frozenset({"schema_valid", "abstain", "invalid", "template_echo", "transient"})
#: timeout in ``actors._run_agent`` is recorded with returncode -1.
TIMEOUT_RETURNCODE = -1

METRIC_CALL_WALL = "actor_call_wall_s"
METRIC_ARM_WALL = "seat_arm_wall_s"
METRIC_ARM_STEPS = "seat_arm_steps"
METRIC_ARM_TOOLS = "seat_arm_tool_calls"
METRIC_ARM_DECODED = "seat_arm_decoded_tokens"
METRIC_ARM_COMPACTIONS = "seat_arm_compactions"

#: metric -> (unit, direction, reps basis). Dict order is the emission order.
CALL_METRICS: dict[str, tuple[str, str, str]] = {
    METRIC_CALL_WALL: ("s", "lower_better", "scored:calls (one actor call)"),
}
_ARM_BASIS = "scored:arm_runs (one planner session per arm, no repeat, no noise floor)"
ARM_METRICS: dict[str, tuple[str, str, str]] = {
    METRIC_ARM_WALL: ("s", "lower_better", _ARM_BASIS),
    METRIC_ARM_STEPS: ("assistant_steps", "lower_better", _ARM_BASIS),
    METRIC_ARM_TOOLS: ("tool_calls", "lower_better", _ARM_BASIS),
    METRIC_ARM_DECODED: ("decoded_tokens", "lower_better", _ARM_BASIS),
    METRIC_ARM_COMPACTIONS: ("compactions", "lower_better", _ARM_BASIS),
}
#: arm metric -> the ``totals`` key it projects (wall comes from ``wall_s``).
ARM_METRIC_TOTALS = {
    METRIC_ARM_STEPS: "steps",
    METRIC_ARM_TOOLS: "tool_calls",
    METRIC_ARM_DECODED: "decoded_tokens",
    METRIC_ARM_COMPACTIONS: "compactions",
}

# --- closed field sets (the producer contract) -------------------------------------------------

PRODUCER_FIELDS = ("repo", "commit", "module")
BACKEND_FIELDS = ("kind", "model", "effort", "agent")
SERVER_FIELDS = ("endpoint", "served_model", "build_info")
PROMPT_FIELDS = ("sha256", "chars", "bytes")
FILE_REF_FIELDS = ("path", "sha256", "bytes")
SEAT_FIELDS = ("arm", "bounded", "fan_out", "steps", "opencode_version", "global_config_sha256",
               "config", "instructions")
CALL_FIELDS = ("schema", "call_id", "role", "workspace", "run_id", "producer", "seat", "backend",
               "server", "prompt", "protocol_id", "started_at", "finished_at", "wall_s",
               "returncode", "timed_out", "reply", "recorded_at", "record_sha256")
REPLY_FIELDS = ("stdout", "stderr")
ARM_FIELDS = ("schema", "ab_id", "arm_id", "arm", "category", "scope", "role", "producer",
              "driver", "seat", "backend", "server", "prompt", "protocol_id", "lane",
              "started_at", "finished_at", "wall_s", "call", "verdict", "sessions", "totals",
              "recorded_at", "record_sha256")
DRIVER_FIELDS = ("path", "sha256")
LANE_FIELDS = ("path", "anchor_commit", "edited")
ARM_CALL_FIELDS = ("returncode", "timed_out", "call_id")
SESSION_FIELDS = ("session_id", "root", "export", "steps", "tool_calls", "tools", "compactions",
                  "decoded_tokens", "uncached_prompt_tokens", "context_first", "context_max",
                  "tool_output_chars")
TOTALS_FIELDS = ("steps", "tool_calls", "compactions", "decoded_tokens",
                 "uncached_prompt_tokens", "tool_output_chars")

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_BARE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")


class CaptureError(ValueError):
    """The producer asked for a record the call or arm cannot honestly support."""


# --- primitives --------------------------------------------------------------------------------

def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


def content_hash(value: Any) -> str:
    try:
        return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()
    except (TypeError, ValueError) as exc:
        raise CaptureError(f"value is not canonical JSON: {exc}") from exc


def record_digest(record: Mapping[str, Any]) -> str:
    """Self-hash: sha256 of canonical JSON over every field except ``record_sha256``."""
    return content_hash({k: v for k, v in record.items() if k != "record_sha256"})


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def prompt_identity(prompt: str) -> dict[str, Any]:
    """The ``prompt`` object for a prompt string: digest over UTF-8 bytes, chars, bytes."""
    raw = prompt.encode("utf-8")
    return {"sha256": hashlib.sha256(raw).hexdigest(), "chars": len(prompt), "bytes": len(raw)}


def seat_digest(seat: Mapping[str, Any]) -> str:
    """One digest for the whole seat (arm, knobs, and every config file's digest)."""
    return content_hash(dict(seat))


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def _int(value: Any, minimum: int) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= minimum


def _finite_positive(value: Any) -> bool:
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value) and value > 0)


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _nullable_text(value: Any) -> bool:
    return value is None or _text(value)


def _closed(obj: Any, fields: tuple[str, ...], where: str) -> list[str]:
    if not isinstance(obj, Mapping):
        return [f"{where} must be an object"]
    p: list[str] = []
    missing = [k for k in fields if k not in obj]
    if missing:
        p.append(f"{where} missing fields: " + ", ".join(missing))
    unknown = sorted(set(obj) - set(fields))
    if unknown:
        p.append(f"{where} unknown fields (the schema is closed): " + ", ".join(unknown))
    return p


def _file_ref(obj: Any, where: str, *, bare: bool = False) -> list[str]:
    p = _closed(obj, FILE_REF_FIELDS, where)
    if p:
        return p
    path = obj["path"]
    if not _text(path) or (bare and (not _BARE_NAME.match(path) or path in (".", ".."))):
        p.append(f"{where}.path must be a {'bare file name' if bare else 'non-empty path'}")
    if not _SHA256.match(str(obj["sha256"])):
        p.append(f"{where}.sha256 must be a 64-hex digest of the file's bytes")
    if not _int(obj["bytes"], 0):
        p.append(f"{where}.bytes must be an integer >= 0")
    return p


def _producer(obj: Any) -> list[str]:
    p = _closed(obj, PRODUCER_FIELDS, "producer")
    if p:
        return p
    if not _text(obj["repo"]):
        p.append("producer.repo must name the producing repository")
    if not _GIT_SHA.match(str(obj["commit"])):
        p.append("producer.commit must be the 40-hex commit of the producing code")
    if not _text(obj["module"]):
        p.append("producer.module must name the producing module")
    return p


def _backend(obj: Any) -> list[str]:
    p = _closed(obj, BACKEND_FIELDS, "backend")
    if p:
        return p
    if obj["kind"] not in BACKEND_KINDS:
        p.append(f"backend.kind must be one of {sorted(BACKEND_KINDS)}")
    for key in ("model", "effort"):
        if not _text(obj[key]):
            p.append(f"backend.{key} must be recorded")
    if not _nullable_text(obj["agent"]):
        p.append("backend.agent must be a non-empty string or null")
    return p


#: INF-78 OAB-2: the orchestrator's own base URL is always loopback (`AK_ORCHESTRATOR_URL`
#: defaults to ``http://127.0.0.1:8000``; an operator override still targets this host).
#: A model-serving port (e.g. ``:8083``, a llama-server slot) belongs to `served_model`,
#: which the orchestrator kind is never allowed to fill in -- see below.
_ORCHESTRATOR_ENDPOINT = re.compile(r"^https?://(127\.0\.0\.1|localhost)(:\d+)?/?$")


def _server(obj: Any, backend: Any) -> list[str]:
    p = _closed(obj, SERVER_FIELDS, "server")
    if p:
        return p
    if not _text(obj["endpoint"]):
        p.append("server.endpoint must be recorded (a local base URL, or 'hosted:<kind>'), "
                 "never guessed")
    kind = backend.get("kind") if isinstance(backend, Mapping) else None
    if kind == "orchestrator":
        if not _ORCHESTRATOR_ENDPOINT.match(str(obj["endpoint"])):
            p.append("server.endpoint for the orchestrator kind must be its own loopback base "
                     "URL (e.g. http://127.0.0.1:8000), never a model-serving port")
        if obj["served_model"] is not None:
            p.append("server.served_model must be null for the orchestrator kind: there is no "
                     "single served model at this layer -- the orchestrator routes per call, so "
                     "model provenance is the ChatResponse's routed_to/role_history, carried on "
                     "the sibling actor_call_metrics.v1 row, never guessed into this field")
    for key in ("served_model", "build_info"):
        if not _nullable_text(obj[key]):
            p.append(f"server.{key} must be a non-empty string or null (null = not captured)")
    return p


def _prompt(obj: Any) -> list[str]:
    p = _closed(obj, PROMPT_FIELDS, "prompt")
    if p:
        return p
    if not _SHA256.match(str(obj["sha256"])):
        p.append("prompt.sha256 must be the 64-hex digest of the prompt's UTF-8 bytes")
    for key in ("chars", "bytes"):
        if not _int(obj[key], 1):
            p.append(f"prompt.{key} must be an integer >= 1")
    if not p and obj["bytes"] < obj["chars"]:
        p.append("prompt.bytes cannot be fewer than prompt.chars")
    return p


def _seat(obj: Any, backend: Any) -> list[str]:
    p = _closed(obj, SEAT_FIELDS, "seat")
    if p:
        return p
    if not _text(obj["arm"]):
        p.append("seat.arm must name the seat arm (e.g. 'plain', 'bounded')")
    for key in ("bounded", "fan_out"):
        if not isinstance(obj[key], bool):
            p.append(f"seat.{key} must be a boolean")
    kind = backend.get("kind") if isinstance(backend, Mapping) else None
    if kind == "opencode":
        if not _text(obj["opencode_version"]):
            p.append("seat.opencode_version must be recorded for an opencode backend")
        if not _SHA256.match(str(obj["global_config_sha256"])):
            p.append("seat.global_config_sha256 must digest ~/.config/opencode/opencode.jsonc "
                     "(opencode merges the per-run config OVER it, so it is part of the seat)")
    else:
        if obj["opencode_version"] is not None or obj["global_config_sha256"] is not None:
            p.append("seat.opencode_version/global_config_sha256 are opencode-only; null otherwise")
    if obj["bounded"] is True:
        if kind != "opencode":
            p.append("a bounded seat exists only for the opencode backend")
        if not _int(obj["steps"], 1):
            p.append("seat.steps must be the step cap (integer >= 1) for a bounded seat")
        if obj["config"] is None:
            p.append("seat.config must reference the per-run opencode config for a bounded seat")
    elif obj["bounded"] is False:
        if obj["config"] is not None or obj["instructions"] is not None or obj["steps"] is not None:
            p.append("a plain seat has no per-run config, instructions or step cap (write null)")
        if obj["fan_out"] is True:
            p.append("seat.fan_out is a bounded-seat knob; a plain seat records false")
    if obj["config"] is not None:
        p.extend(_file_ref(obj["config"], "seat.config"))
    if obj["instructions"] is not None:
        p.extend(_file_ref(obj["instructions"], "seat.instructions"))
    return p


def _times(record: Mapping[str, Any], max_lag_s: int) -> list[str]:
    p: list[str] = []
    started, finished = _parse_utc(record.get("started_at")), _parse_utc(record.get("finished_at"))
    recorded = _parse_utc(record.get("recorded_at"))
    if started is None or finished is None or recorded is None:
        return ["started_at, finished_at and recorded_at must be UTC timestamps"]
    if finished < started:
        p.append("finished_at precedes started_at")
    if started < _parse_utc(HOOK_SINCE):
        p.append(f"session started {record['started_at']}, before the VB-AK-SEAT hook "
                 f"({HOOK_SINCE}); a pre-hook session stays pre-hook")
    lag = (recorded - finished).total_seconds()
    if lag < 0:
        p.append("recorded_at precedes finished_at")
    elif lag > max_lag_s:
        p.append(f"record written {lag:.0f}s after the session finished (limit {max_lag_s}s); "
                 "the hook captures at write time and never backfills")
    wall = record.get("wall_s")
    if not _finite_positive(wall):
        p.append("wall_s must be a finite number > 0 (monotonic seconds)")
    elif finished >= started and abs((finished - started).total_seconds() - wall) > WALL_TOLERANCE_S:
        p.append("wall_s disagrees with finished_at - started_at by more than "
                 f"{WALL_TOLERANCE_S:.0f}s")
    return p


def _self_hash(record: Mapping[str, Any]) -> list[str]:
    if not _SHA256.match(str(record.get("record_sha256", ""))):
        return ["record_sha256 must be a 64-hex self-hash"]
    try:
        if record_digest(record) != record["record_sha256"]:
            return ["record_sha256 does not bind the record content"]
    except CaptureError as exc:
        return [f"record is not canonically hashable: {exc}"]
    return []


def censored(record: Mapping[str, Any]) -> bool:
    """True when the session never finished on its own: timeout or signal death."""
    rc = record["returncode"] if "returncode" in record else record["call"]["returncode"]
    timed_out = record["timed_out"] if "timed_out" in record else record["call"]["timed_out"]
    return bool(timed_out) or rc < 0


# --- the call record ---------------------------------------------------------------------------

def validate_call_record(record: Any) -> list[str]:
    """Every problem with one call record. Empty list == it carries a usable claim tuple."""
    if not isinstance(record, Mapping):
        return ["call record is not a JSON object"]
    p: list[str] = []
    if record.get("schema") != CALL_SCHEMA:
        p.append(f"schema must be {CALL_SCHEMA!r} (a line without it is pre-hook)")
    p.extend(_closed(record, CALL_FIELDS, "call record"))
    if p:
        return p
    if not _text(record["call_id"]):
        p.append("call_id must be a non-empty string unique to this call")
    if record["role"] not in ROLES:
        p.append(f"role must be one of {sorted(ROLES)}")
    if not _text(record["workspace"]):
        p.append("workspace must be the actor's worktree path")
    if not _nullable_text(record["run_id"]):
        p.append("run_id must be a non-empty string or null")
    if not isinstance(record["protocol_id"], str):
        p.append("protocol_id must be a string (empty: no codified protocol exists)")
    p.extend(_producer(record["producer"]))
    p.extend(_backend(record["backend"]))
    p.extend(_seat(record["seat"], record["backend"]))
    p.extend(_server(record["server"], record["backend"]))
    p.extend(_prompt(record["prompt"]))
    p.extend(_times(record, MAX_CALL_RECORD_LAG_S))
    rc = record["returncode"]
    if isinstance(rc, bool) or not isinstance(rc, int):
        p.append("returncode must be an integer")
    if not isinstance(record["timed_out"], bool):
        p.append("timed_out must be a boolean")
    elif record["timed_out"] and rc != TIMEOUT_RETURNCODE:
        p.append(f"a timed-out call is recorded with returncode {TIMEOUT_RETURNCODE}")
    reply = record["reply"]
    if reply is not None:
        rp = _closed(reply, REPLY_FIELDS, "reply")
        if not rp:
            for key in REPLY_FIELDS:
                rp.extend(_file_ref(reply[key], f"reply.{key}", bare=True))
        p.extend(rp)
    p.extend(_self_hash(record))
    return p


def build_call_record(
    *, call_id: str, role: str, workspace: str, producer: Mapping[str, Any],
    seat: Mapping[str, Any], backend: Mapping[str, Any], server: Mapping[str, Any],
    prompt: str, started_at: str, finished_at: str, wall_s: float, returncode: int,
    timed_out: bool, recorded_at: str, reply: Mapping[str, Any] | None = None,
    run_id: str | None = None, protocol_id: str = "",
) -> dict[str, Any]:
    """Reference writer for one ``actor-calls.jsonl`` line. Raises rather than emit a bad one."""
    record: dict[str, Any] = {
        "schema": CALL_SCHEMA, "call_id": call_id, "role": role, "workspace": workspace,
        "run_id": run_id, "producer": dict(producer), "seat": json.loads(json.dumps(seat)),
        "backend": dict(backend), "server": dict(server), "prompt": prompt_identity(prompt),
        "protocol_id": protocol_id, "started_at": started_at, "finished_at": finished_at,
        "wall_s": wall_s, "returncode": returncode, "timed_out": timed_out,
        "reply": json.loads(json.dumps(reply)) if reply is not None else None,
        "recorded_at": recorded_at,
    }
    record["record_sha256"] = record_digest(record)
    problems = validate_call_record(record)
    if problems:
        raise CaptureError("refusing to write an invalid call record: " + "; ".join(problems))
    return record


# --- the arm record ----------------------------------------------------------------------------

def _session(obj: Any, i: int) -> list[str]:
    where = f"sessions[{i}]"
    p = _closed(obj, SESSION_FIELDS, where)
    if p:
        return p
    if not _text(obj["session_id"]):
        p.append(f"{where}.session_id must be recorded")
    if not isinstance(obj["root"], bool):
        p.append(f"{where}.root must be a boolean")
    p.extend(_file_ref(obj["export"], f"{where}.export"))
    for key in ("steps", "tool_calls", "compactions", "decoded_tokens",
                "uncached_prompt_tokens", "tool_output_chars"):
        if not _int(obj[key], 0):
            p.append(f"{where}.{key} must be an integer >= 0 (an unparsed export is not a "
                     "session record; do not write the arm)")
    for key in ("context_first", "context_max"):
        if obj[key] is not None and not _int(obj[key], 0):
            p.append(f"{where}.{key} must be an integer >= 0 or null")
    tools = obj["tools"]
    if not isinstance(tools, Mapping) or not all(_text(k) and _int(v, 0) for k, v in tools.items()):
        p.append(f"{where}.tools must map tool name -> count")
    elif _int(obj["tool_calls"], 0) and sum(tools.values()) != obj["tool_calls"]:
        p.append(f"{where}.tools does not sum to {where}.tool_calls")
    return p


def derive_totals(sessions: list[Mapping[str, Any]]) -> dict[str, int]:
    """Totals over the root session AND its scouts: the GPU paid for every one of them."""
    return {key: sum(int(s[key]) for s in sessions) for key in TOTALS_FIELDS}


def arm_values(record: Mapping[str, Any]) -> dict[str, float]:
    values: dict[str, float] = {METRIC_ARM_WALL: record["wall_s"]}
    for metric, key in ARM_METRIC_TOTALS.items():
        values[metric] = record["totals"][key]
    return values


def validate_arm_record(record: Any) -> list[str]:
    """Every problem with one arm record. Empty list == it carries usable claim tuples."""
    if not isinstance(record, Mapping):
        return ["arm record is not a JSON object"]
    p: list[str] = []
    if record.get("schema") != ARM_SCHEMA:
        p.append(f"schema must be {ARM_SCHEMA!r} (a result without it is pre-hook)")
    p.extend(_closed(record, ARM_FIELDS, "arm record"))
    if p:
        return p
    for key in ("ab_id", "arm_id", "arm"):
        if not _text(record[key]):
            p.append(f"{key} must be a non-empty string")
    if not _text(record["scope"]) or len(record["scope"].strip()) < 20:
        p.append("scope must state the comparison scope in the producer's words (n, repeat, "
                 "noise floor, what else differs between arms) -- it is the claim's scope")
    if record["category"] not in CATEGORIES:
        p.append(f"category must be one of {sorted(CATEGORIES)} (recorded, never inferred)")
    if record["role"] not in ARM_ROLES:
        p.append(f"role must be one of {sorted(ARM_ROLES)}")
    if not isinstance(record["protocol_id"], str):
        p.append("protocol_id must be a string (empty: no codified protocol exists)")
    if record["verdict"] not in VERDICTS:
        p.append(f"verdict must be one of {sorted(VERDICTS)}")
    p.extend(_producer(record["producer"]))
    dp = _closed(record["driver"], DRIVER_FIELDS, "driver")
    if not dp:
        if not _text(record["driver"]["path"]):
            dp.append("driver.path must be recorded")
        if not _SHA256.match(str(record["driver"]["sha256"])):
            dp.append("driver.sha256 must digest the driver source that ran the arm")
    p.extend(dp)
    p.extend(_backend(record["backend"]))
    p.extend(_seat(record["seat"], record["backend"]))
    if isinstance(record["seat"], Mapping) and record["seat"].get("arm") != record["arm"]:
        p.append("arm must equal seat.arm")
    p.extend(_server(record["server"], record["backend"]))
    p.extend(_prompt(record["prompt"]))
    lp = _closed(record["lane"], LANE_FIELDS, "lane")
    if not lp:
        if not _text(record["lane"]["path"]):
            lp.append("lane.path must be recorded")
        if not _GIT_SHA.match(str(record["lane"]["anchor_commit"])):
            lp.append("lane.anchor_commit must be the 40-hex commit the lane was reset to")
        if not isinstance(record["lane"]["edited"], bool):
            lp.append("lane.edited must be a boolean")
    p.extend(lp)
    p.extend(_times(record, MAX_ARM_RECORD_LAG_S))
    cp = _closed(record["call"], ARM_CALL_FIELDS, "call")
    if not cp:
        call = record["call"]
        if isinstance(call["returncode"], bool) or not isinstance(call["returncode"], int):
            cp.append("call.returncode must be an integer")
        if not isinstance(call["timed_out"], bool):
            cp.append("call.timed_out must be a boolean")
        elif call["timed_out"] and call["returncode"] != TIMEOUT_RETURNCODE:
            cp.append(f"a timed-out call is recorded with returncode {TIMEOUT_RETURNCODE}")
        if not _nullable_text(call["call_id"]):
            cp.append("call.call_id must name the actor-calls.jsonl record, or be null")
    p.extend(cp)

    sessions = record["sessions"]
    if not isinstance(sessions, list) or not sessions:
        p.append("sessions must be a non-empty list (root session plus any scouts)")
        return p + _self_hash(record)
    session_problems: list[str] = []
    for i, s in enumerate(sessions):
        session_problems.extend(_session(s, i))
    p.extend(session_problems)
    if not session_problems:
        if sum(1 for s in sessions if s["root"]) != 1:
            p.append("exactly one session must be the root session")
        if len({s["session_id"] for s in sessions}) != len(sessions):
            p.append("session ids must be unique")
        tp = _closed(record["totals"], TOTALS_FIELDS, "totals")
        if tp:
            p.extend(tp)
        elif dict(record["totals"]) != derive_totals(sessions):
            p.append("totals do not re-derive from sessions (basis: root + scouts)")
    p.extend(_self_hash(record))
    return p


def build_arm_record(
    *, ab_id: str, arm_id: str, category: str, scope: str, role: str,
    producer: Mapping[str, Any], driver: Mapping[str, Any], seat: Mapping[str, Any],
    backend: Mapping[str, Any], server: Mapping[str, Any], prompt: str,
    lane: Mapping[str, Any], started_at: str, finished_at: str, wall_s: float,
    call: Mapping[str, Any], verdict: str, sessions: list[Mapping[str, Any]],
    recorded_at: str, protocol_id: str = "",
) -> dict[str, Any]:
    """Reference writer for one ``result-<arm>.json``. Raises rather than emit a bad one."""
    session_list = json.loads(json.dumps(list(sessions)))
    try:
        totals = derive_totals(session_list)
    except (KeyError, TypeError, ValueError) as exc:
        raise CaptureError(f"sessions cannot be totalled: {exc!r}") from exc
    record: dict[str, Any] = {
        "schema": ARM_SCHEMA, "ab_id": ab_id, "arm_id": arm_id,
        "arm": seat.get("arm") if isinstance(seat, Mapping) else None,
        "category": category, "scope": scope, "role": role, "producer": dict(producer),
        "driver": dict(driver), "seat": json.loads(json.dumps(seat)), "backend": dict(backend),
        "server": dict(server), "prompt": prompt_identity(prompt), "protocol_id": protocol_id,
        "lane": dict(lane), "started_at": started_at, "finished_at": finished_at,
        "wall_s": wall_s, "call": dict(call), "verdict": verdict, "sessions": session_list,
        "totals": totals, "recorded_at": recorded_at,
    }
    record["record_sha256"] = record_digest(record)
    problems = validate_arm_record(record)
    if problems:
        raise CaptureError("refusing to write an invalid arm record: " + "; ".join(problems))
    return record


def measurement_identity(*, kind: str, record_id: str, metric: str, record_sha256: str) -> str:
    digest = content_hash({"kind": kind, "record_id": record_id, "metric": metric,
                           "record_sha256": record_sha256})
    return f"akseat_{digest[:24]}"


__all__ = [
    "ARM_FIELDS", "ARM_METRICS", "ARM_RESULT_GLOB", "ARM_SCHEMA", "CALL_FIELDS", "CALL_LOG_NAME",
    "CALL_METRICS", "CALL_SCHEMA", "CaptureError", "HOOK_SINCE", "MAX_ARM_RECORD_LAG_S",
    "MAX_CALL_RECORD_LAG_S", "SEAT_FIELDS", "SESSION_FIELDS", "VERDICTS", "arm_values",
    "build_arm_record", "build_call_record", "censored", "content_hash", "derive_totals",
    "measurement_identity", "prompt_identity", "record_digest", "seat_digest", "text_sha256",
    "validate_arm_record", "validate_call_record",
]
