#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""session_bus.py — bus library + CLI for the session bus (M1).

Runs under the orchestrator venv (matching compile_inference_batch.py) because
that is the interpreter carrying jsonschema; the system python3 does not.

Owning handoff: handoffs/active/session-bus-thin-dispatcher.md
Contract:       coordination/session-bus/BUS_PROTOCOL.md

Verbs
  append    schema-validated row -> a file the caller OWNS (refuses otherwise)
  fold      queue reconcile, latest-row-per-task_id wins (batch_ledger semantics)
  validate  whole-bus schema check + single-writer lint
  cursor    get/advance your own cursor (byte offsets)
  status    human summary: queue by status/lane, inbox depths, heartbeat ages
  drain     print your inbox past your cursor and advance it (--triage appends
            the routing standing-queue report)
  triage    the standing queue of messages ROUTED to you (needs_routing_to /
            action_required), printed IN FULL, cursor-independent — advancing a
            cursor never clears it; only a corr_id disposition from your own
            outbox does

Single-writer is STRUCTURAL, not advisory: `append` derives the required writer
from the target path and refuses a mismatch. One writer may own many files; no
file ever has two writers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

# REPO_ROOT is retained for anything that legitimately wants "wherever this
# copy of the repo lives" (there is none left in this module after the fix
# below, but it costs nothing to keep and other modules still import the
# pattern). It must NEVER be used to derive the bus root — see get_bus_root().
REPO_ROOT = Path(__file__).resolve().parents[2]


def get_bus_root() -> Path:
    """Resolve the ONE canonical session-bus root.

    Deliberately NOT __file__-relative. Under the worktree-per-main model
    (scripts/coordination/WORKTREE_MIGRATION.md), every main runs this exact
    script from its own worktree checkout, at a different filesystem path --
    a Path(__file__).resolve().parents[2] resolution (the old code here)
    would therefore derive FIVE independently-mutating bus directories, one
    per worktree, instead of the single shared runtime plane the whole
    protocol assumes: one queue, one set of per-agent cursors, one
    single-writer rule per file. There is exactly one live bus. It lives at
    the canonical /workspace checkout -- the versioned WORK happens in
    per-main worktrees, but the coordination RUNTIME plane does not fork.
    Every worktree's copy of this module must resolve to that same path.

    EPYC_BUS_ROOT overrides this, for tests only -- production code paths
    (agents, the coordinator-daemon, the hooks) never set it. Most tests
    instead isolate via an explicit --bus-root / bus_root argument (see
    tests/test_session_bus.py's tmp_path-based fixture); the env var exists
    for callers that cannot thread an argument through (e.g. shelling out to
    this script from a test without controlling its argv).
    """
    override = os.environ.get("EPYC_BUS_ROOT")
    if override:
        return Path(override)
    return Path("/workspace/coordination/session-bus")


DEFAULT_BUS_ROOT = get_bus_root()

COORDINATOR_DAEMON = "coordinator-daemon"

MSG_SCHEMA_VERSION = "session_bus.msg.v1"
QUEUE_SCHEMA_VERSION = "session_bus.queue.v1"

TERMINAL_STATES = frozenset(
    {"DONE_PASS", "DONE_MARGINAL_OBS", "FAILED", "CANCELLED"}
)


class BusError(RuntimeError):
    """Protocol or validation violation. Message is operator-facing."""


# --------------------------------------------------------------------------- io


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_jsonl(path: Path, start: int = 0) -> tuple[list[dict], int]:
    """Return (rows, end_offset). Reads from byte offset `start`."""
    if not path.exists():
        return [], start
    with path.open("rb") as fh:
        fh.seek(start)
        raw = fh.read()
        end = fh.tell()
    rows = []
    for line in raw.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise BusError(f"{path}: malformed JSONL near offset {start}: {e}") from e
    return rows, end


def _append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def _write_atomic(path: Path, payload: dict) -> None:
    """tmp+rename — heartbeats and cursors are overwritten, never appended."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


# ------------------------------------------------------------------- ownership


def required_writer(bus_root: Path, target: Path) -> str:
    """The ONE agent id permitted to write `target`.

    queue.jsonl and inbox/* belong to the coordinator-daemon; outbox/<a>,
    heartbeats/<a> and cursors/<a> belong to <a>.
    """
    try:
        rel = target.resolve().relative_to(bus_root.resolve())
    except ValueError as e:
        raise BusError(f"{target} is outside the bus root {bus_root}") from e
    parts = rel.parts
    if rel.name in {"queue.jsonl", "advisory.jsonl", "boundary_state.json",
                    "stuck_state.json", "operator_escalation_state.json"} and len(parts) == 1:
        return COORDINATOR_DAEMON
    if len(parts) == 2:
        area, fname = parts
        stem = fname.split(".")[0]
        if area == "inbox":
            return COORDINATOR_DAEMON
        if area in {"outbox", "heartbeats", "cursors"}:
            return stem
    raise BusError(f"{rel} is not a writable bus file (no single-writer rule covers it)")


def _roster_ids(bus_root: Path) -> set[str]:
    """Read declared agent identities; malformed roster data is fail-closed."""
    try:
        import yaml
        cfg = yaml.safe_load((bus_root / "config.yaml").read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001 — caller needs an operator-facing error
        raise BusError(f"could not read config.yaml roster: {exc}") from exc
    roster = cfg.get("roster") if isinstance(cfg, dict) else None
    if not isinstance(roster, list):
        raise BusError("config.yaml roster is missing or malformed; refusing an unverified writer")
    ids = {str(row.get("id", "")).strip() for row in roster if isinstance(row, dict)} - {""}
    if not ids:
        raise BusError("config.yaml roster has no ids; refusing an unverified writer")
    return ids


def _require_roster_id(bus_root: Path, agent: str) -> None:
    ids = _roster_ids(bus_root)
    if agent not in ids:
        raise BusError(f"{agent!r} is not a roster id in config.yaml (have: {', '.join(sorted(ids))}). "
                       "Add the roster row first; task ids belong in the task_id field.")


# --------------------------------------------------------------------- schema


def _load_schema(bus_root: Path) -> dict:
    path = bus_root / "session_bus.schema.json"
    if not path.exists():
        raise BusError(f"schema not found at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


# ----------------------------------------------- vendored draft-7 validator
#
# C34 (2026-08-11): the two sides of this bus ran DIFFERENT validators, so a row
# could pass authoring and be refused at relay — written but never sent, and
# nobody told. Agents author with `python3 scripts/coordination/session_bus.py`
# (/usr/bin/python3, 3.13, no jsonschema); the coordinator-daemon runs under the
# orchestrator venv (3.11, jsonschema 4.26) and validates in full.
#
# Pinning an interpreter in the documented command was the obvious fix and is the
# wrong one: it is a CONVENTION, and the next task brief, wrapper or doc that
# spells the command the old way silently reopens the identical gap. The two
# interpreters are also ABI-incompatible (3.13 vs 3.11, and jsonschema pulls the
# compiled rpds-py), so the venv's site-packages cannot simply be borrowed.
#
# So agreement is made STRUCTURAL: when jsonschema is absent, validate against
# the same schema file with a vendored draft-7 subset. It has no dependencies, so
# it works under any interpreter, and `tests/test_session_bus.py` asserts it
# agrees with jsonschema verdict-for-verdict over the whole live bus corpus plus
# a mutant battery. If the schema ever grows a keyword this does NOT implement,
# construction REFUSES rather than ignoring the keyword — a validator that skips
# what it does not understand is the C34 fail-open wearing a different hat.


class _UnsupportedSchema(Exception):
    """The schema uses a construct the vendored validator does not implement."""


class _MiniError:
    """Shaped like `jsonschema.ValidationError` for the three attributes this
    module and `session_bus_coordinator.py` actually read: path, message,
    validator (the failing keyword)."""

    __slots__ = ("path", "message", "validator")

    def __init__(self, path: list, message: str, validator: str) -> None:
        self.path = list(path)
        self.message = message
        self.validator = validator

    def __repr__(self) -> str:  # pragma: no cover — debugging aid
        where = "/".join(str(p) for p in self.path) or "<root>"
        return f"<_MiniError {where}: {self.message}>"


# Keywords the vendored validator ENFORCES.
_MINI_ASSERTIONS = frozenset({
    "$ref", "type", "enum", "const", "required", "properties",
    "additionalProperties", "items", "minItems", "maxItems", "uniqueItems",
    "minLength", "maxLength", "pattern", "minimum", "maximum",
    "exclusiveMinimum", "exclusiveMaximum", "allOf", "anyOf", "oneOf", "not",
    "if", "then", "else",
})
# Keywords that assert nothing — safe to carry without enforcing.
_MINI_ANNOTATIONS = frozenset({
    "$schema", "$id", "$comment", "title", "description", "default",
    "examples", "deprecated", "readOnly", "writeOnly", "definitions",
})
# Where subschemas live, by keyword shape.
_MINI_SUBSCHEMA = frozenset({"not", "if", "then", "else"})
_MINI_SUBSCHEMA_LIST = frozenset({"allOf", "anyOf", "oneOf"})
_MINI_SUBSCHEMA_MAP = frozenset({"properties", "definitions"})

_MINI_TYPES = frozenset({"object", "array", "string", "number", "integer",
                         "boolean", "null"})

_MINI_TRUE = object()
_MINI_FALSE = object()


def _mini_unbool(value: Any) -> Any:
    """JSON-Schema equality keeps True distinct from 1 (and False from 0) while
    treating 1 and 1.0 as equal. Swapping the bools for sentinels buys both."""
    if value is True:
        return _MINI_TRUE
    if value is False:
        return _MINI_FALSE
    return value


def _mini_equal(a: Any, b: Any) -> bool:
    a, b = _mini_unbool(a), _mini_unbool(b)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_mini_equal(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_mini_equal(a[k], b[k]) for k in a)
    if isinstance(a, (list, dict)) or isinstance(b, (list, dict)):
        return False
    return a == b


def _mini_is_type(value: Any, kind: str) -> bool:
    if kind == "object":
        return isinstance(value, dict)
    if kind == "array":
        return isinstance(value, list)
    if kind == "string":
        return isinstance(value, str)
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "null":
        return value is None
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "integer":
        # draft-6+ widened "integer" to any number with zero fractional part.
        if isinstance(value, bool):
            return False
        if isinstance(value, int):
            return True
        return isinstance(value, float) and value.is_integer()
    raise _UnsupportedSchema(f"unknown type {kind!r}")


def _mini_extras_msg(extras: Iterable[str]) -> str:
    extras = sorted(extras)
    verb = "was" if len(extras) == 1 else "were"
    listed = ", ".join(repr(e) for e in extras)
    return f"Additional properties are not allowed ({listed} {verb} unexpected)"


def _mini_audit(schema: Any, where: str = "<root>") -> None:
    """Refuse a schema this validator would only partially enforce.

    Walking the schema up front is the whole safety argument: an unknown
    keyword must surface as a REFUSAL to validate, never as a keyword quietly
    skipped, or the vendored path becomes the fail-open it was written to close.
    """
    if isinstance(schema, bool):
        return
    if not isinstance(schema, dict):
        raise _UnsupportedSchema(f"{where}: schema is {type(schema).__name__}, not an object")
    for key, value in schema.items():
        spot = f"{where}/{key}"
        if key in _MINI_SUBSCHEMA:
            _mini_audit(value, spot)
        elif key in _MINI_SUBSCHEMA_LIST:
            if not isinstance(value, list):
                raise _UnsupportedSchema(f"{spot}: expected a list of schemas")
            for i, sub in enumerate(value):
                _mini_audit(sub, f"{spot}/{i}")
        elif key in _MINI_SUBSCHEMA_MAP:
            if not isinstance(value, dict):
                raise _UnsupportedSchema(f"{spot}: expected an object of schemas")
            for name, sub in value.items():
                _mini_audit(sub, f"{spot}/{name}")
        elif key == "items":
            if isinstance(value, list):
                for i, sub in enumerate(value):
                    _mini_audit(sub, f"{spot}/{i}")
            else:
                _mini_audit(value, spot)
        elif key == "additionalProperties":
            if not isinstance(value, bool):
                _mini_audit(value, spot)
        elif key == "type":
            kinds = value if isinstance(value, list) else [value]
            for kind in kinds:
                if kind not in _MINI_TYPES:
                    raise _UnsupportedSchema(f"{spot}: unknown type {kind!r}")
        elif key == "$ref":
            if not isinstance(value, str) or not value.startswith("#/"):
                raise _UnsupportedSchema(f"{spot}: only local '#/...' $ref is supported, got {value!r}")
        elif key in _MINI_ASSERTIONS or key in _MINI_ANNOTATIONS:
            continue
        else:
            raise _UnsupportedSchema(
                f"{spot}: keyword {key!r} is not implemented by the vendored validator")


class _MiniDraft7Validator:
    """A dependency-free draft-7 validator covering exactly the constructs
    `session_bus.schema.json` uses. Interface-compatible with
    `jsonschema.Draft7Validator` for `iter_errors` / `is_valid`."""

    def __init__(self, schema: dict) -> None:
        _mini_audit(schema)
        self.schema = schema

    # -- public ------------------------------------------------------------

    def iter_errors(self, instance: Any) -> Iterable[_MiniError]:
        yield from self._errors(self.schema, instance, [])

    def is_valid(self, instance: Any) -> bool:
        for _ in self.iter_errors(instance):
            return False
        return True

    # -- internals ---------------------------------------------------------

    def _resolve(self, ref: str) -> Any:
        node: Any = self.schema
        for part in ref[2:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            if not isinstance(node, dict) or part not in node:
                raise _UnsupportedSchema(f"$ref {ref!r} does not resolve")
            node = node[part]
        return node

    def _valid(self, schema: Any, instance: Any) -> bool:
        for _ in self._errors(schema, instance, []):
            return False
        return True

    def _errors(self, schema: Any, inst: Any, path: list) -> Iterable[_MiniError]:
        if schema is True or schema == {}:
            return
        if schema is False:
            yield _MiniError(path, f"{inst!r} is not allowed", "schema")
            return
        # draft-7: a $ref supersedes its siblings.
        if "$ref" in schema:
            yield from self._errors(self._resolve(schema["$ref"]), inst, path)
            return

        if "type" in schema:
            kinds = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
            if not any(_mini_is_type(inst, k) for k in kinds):
                listed = ", ".join(repr(k) for k in kinds)
                yield _MiniError(path, f"{inst!r} is not of type {listed}", "type")
                # Deliberately NOT an early return: jsonschema evaluates every
                # keyword independently, and the type-specific blocks below are
                # already isinstance-guarded. Returning here would suppress the
                # enum/const/combinator errors jsonschema still reports, and the
                # differential test compares the whole error set, not just the
                # verdict.
        if "enum" in schema and not any(_mini_equal(inst, c) for c in schema["enum"]):
            yield _MiniError(path, f"{inst!r} is not one of {schema['enum']!r}", "enum")
        if "const" in schema and not _mini_equal(inst, schema["const"]):
            yield _MiniError(path, f"{schema['const']!r} was expected", "const")

        if isinstance(inst, str):
            yield from self._string_errors(schema, inst, path)
        if isinstance(inst, (int, float)) and not isinstance(inst, bool):
            yield from self._number_errors(schema, inst, path)
        if isinstance(inst, list):
            yield from self._array_errors(schema, inst, path)
        if isinstance(inst, dict):
            yield from self._object_errors(schema, inst, path)

        yield from self._combinator_errors(schema, inst, path)

    def _string_errors(self, schema: dict, inst: str, path: list) -> Iterable[_MiniError]:
        if "minLength" in schema and len(inst) < schema["minLength"]:
            yield _MiniError(path, f"{inst!r} is too short", "minLength")
        if "maxLength" in schema and len(inst) > schema["maxLength"]:
            yield _MiniError(path, f"{inst!r} is too long", "maxLength")
        if "pattern" in schema and re.search(schema["pattern"], inst) is None:
            yield _MiniError(path, f"{inst!r} does not match {schema['pattern']!r}", "pattern")

    def _number_errors(self, schema: dict, inst: Any, path: list) -> Iterable[_MiniError]:
        if "minimum" in schema and inst < schema["minimum"]:
            yield _MiniError(path, f"{inst!r} is less than the minimum of "
                                   f"{schema['minimum']!r}", "minimum")
        if "maximum" in schema and inst > schema["maximum"]:
            yield _MiniError(path, f"{inst!r} is greater than the maximum of "
                                   f"{schema['maximum']!r}", "maximum")
        if "exclusiveMinimum" in schema and inst <= schema["exclusiveMinimum"]:
            yield _MiniError(path, f"{inst!r} is less than or equal to the exclusive minimum "
                                   f"of {schema['exclusiveMinimum']!r}", "exclusiveMinimum")
        if "exclusiveMaximum" in schema and inst >= schema["exclusiveMaximum"]:
            yield _MiniError(path, f"{inst!r} is greater than or equal to the exclusive maximum "
                                   f"of {schema['exclusiveMaximum']!r}", "exclusiveMaximum")

    def _array_errors(self, schema: dict, inst: list, path: list) -> Iterable[_MiniError]:
        if "minItems" in schema and len(inst) < schema["minItems"]:
            yield _MiniError(path, f"{inst!r} is too short", "minItems")
        if "maxItems" in schema and len(inst) > schema["maxItems"]:
            yield _MiniError(path, f"{inst!r} is too long", "maxItems")
        if schema.get("uniqueItems"):
            seen: list = []
            for item in inst:
                if any(_mini_equal(item, s) for s in seen):
                    yield _MiniError(path, f"{inst!r} has non-unique elements", "uniqueItems")
                    break
                seen.append(item)
        if "items" in schema:
            items = schema["items"]
            if isinstance(items, list):
                for i, (sub, value) in enumerate(zip(items, inst)):
                    yield from self._errors(sub, value, path + [i])
            else:
                for i, value in enumerate(inst):
                    yield from self._errors(items, value, path + [i])

    def _object_errors(self, schema: dict, inst: dict, path: list) -> Iterable[_MiniError]:
        for key in schema.get("required", []):
            if key not in inst:
                yield _MiniError(path, f"{key!r} is a required property", "required")
        props = schema.get("properties")
        if schema.get("additionalProperties") is False:
            extras = [k for k in inst if k not in (props or {})]
            if extras:
                yield _MiniError(path, _mini_extras_msg(extras), "additionalProperties")
        elif isinstance(schema.get("additionalProperties"), dict):
            for key, value in inst.items():
                if key not in (props or {}):
                    yield from self._errors(schema["additionalProperties"], value, path + [key])
        if props:
            for key, sub in props.items():
                if key in inst:
                    yield from self._errors(sub, inst[key], path + [key])

    def _combinator_errors(self, schema: dict, inst: Any, path: list) -> Iterable[_MiniError]:
        for sub in schema.get("allOf", []):
            yield from self._errors(sub, inst, path)
        if "anyOf" in schema and not any(self._valid(s, inst) for s in schema["anyOf"]):
            yield _MiniError(path, f"{inst!r} is not valid under any of the given schemas",
                             "anyOf")
        if "oneOf" in schema:
            matched = sum(1 for s in schema["oneOf"] if self._valid(s, inst))
            if matched == 0:
                yield _MiniError(path, f"{inst!r} is not valid under any of the given schemas",
                                 "oneOf")
            elif matched > 1:
                yield _MiniError(path, f"{inst!r} is valid under each of the given schemas",
                                 "oneOf")
        if "not" in schema and self._valid(schema["not"], inst):
            yield _MiniError(path, f"{inst!r} should not be valid under {schema['not']!r}", "not")
        if "if" in schema:
            branch = "then" if self._valid(schema["if"], inst) else "else"
            if branch in schema:
                yield from self._errors(schema[branch], inst, path)


def _validator(schema: dict, definition: str):
    """The validator for one definition, IDENTICAL on both sides of the bus.

    Prefers `jsonschema` when present (the daemon's interpreter has it) and
    otherwise uses the vendored draft-7 subset above, so authoring under
    `/usr/bin/python3` applies the same schema the relay applies. Returns None
    only when neither can validate — see `validate_row` for that degrade.
    """
    sub = {"$schema": schema["$schema"], "definitions": schema["definitions"],
           "$ref": f"#/definitions/{definition}"}
    try:
        import jsonschema  # type: ignore
        return jsonschema.Draft7Validator(sub)
    except ImportError:
        pass
    try:
        return _MiniDraft7Validator(sub)
    except _UnsupportedSchema as exc:
        print(f"session_bus: WARNING — jsonschema is unavailable under {sys.executable} AND the "
              f"vendored fallback validator refuses this schema ({exc}). Someone added a schema "
              f"construct the fallback does not implement; implement it in _MiniDraft7Validator "
              f"rather than leaving authoring on the partial check.", file=sys.stderr)
        return None


def validate_row(bus_root: Path, row: dict, definition: str) -> None:
    """Raise BusError on a structural violation, against the FULL schema, under
    any interpreter.

    C34, filed 2026-07-29, closed 2026-08-11. The two sides of this bus run
    different interpreters — agents author with `python3
    scripts/coordination/session_bus.py append ...` (the command CLAUDE.md,
    BUS_PROTOCOL.md and every task brief specify, i.e. `/usr/bin/python3`, which
    has no jsonschema), while the coordinator-daemon runs under the orchestrator
    venv, which has 4.26.0 — and until today only ONE of them validated. Authoring
    degraded to a six-required-key check, relay applied the whole schema, so a
    message could pass authoring and be REFUSED at relay: the write succeeded, the
    send did not, and nobody was told. Measured on the live bus 2026-08-11: 368 of
    1137 outbox rows (32%) were in exactly that state, including both C27 operator
    gates.

    `_validator` now falls back to a vendored draft-7 subset instead of returning
    None, so both sides apply `session_bus.schema.json` itself and CANNOT disagree.
    Consequence, and the point: `append` now REFUSES at the author what the relay
    would have refused later. That is the correct place to fail — the rows it
    refuses were never being delivered.

    The partial-check degrade below survives for one case only: the schema grows a
    construct the vendored validator does not implement, which it reports rather
    than skipping. It stays fail-open-with-a-warning because refusing there would
    take the whole fleet's bus down over a schema edit, and the warning is
    unconditional on stderr because a degradation nobody sees is not a degradation
    anyone acts on.
    """
    validator = _validator(_load_schema(bus_root), definition)
    if validator is None:
        required = {"msg": ["schema_version", "id", "ts", "from", "to", "kind"],
                    "queue_row": ["schema_version", "ts", "task_id", "status", "lane",
                                  "gating", "epoch"]}[definition]
        print(f"session_bus: WARNING — no validator could be built under {sys.executable}, so "
              f"this {definition} was checked for {len(required)} required keys ONLY, not against "
              f"session_bus.schema.json. The coordinator-daemon DOES validate in full and will "
              f"refuse to relay a row this partial check let through. See the _UnsupportedSchema "
              f"warning above and implement the missing keyword in _MiniDraft7Validator.",
              file=sys.stderr)
        missing = [k for k in required if k not in row]
        if missing:
            raise BusError(f"missing required field(s) {missing} (jsonschema unavailable — "
                           "structural check was partial)")
        return
    errors = sorted(validator.iter_errors(row), key=lambda e: list(e.path))
    if errors:
        detail = "; ".join(f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}"
                           for e in errors[:5])
        raise BusError(f"schema violation: {detail}")


# ----------------------------------------------------------------------- fold


def fold_queue(bus_root: Path) -> dict[str, dict]:
    """Latest row per task_id wins — batch_ledger.reconcile semantics."""
    rows, _ = _read_jsonl(bus_root / "queue.jsonl")
    latest: dict[str, dict] = {}
    for row in rows:
        tid = row.get("task_id")
        if tid:
            latest[tid] = row
    return latest


# -------------------------------------------------------------- routing intent
#
# 2026-07-29: two routed messages were missed because routing intent lived as
# PROSE inside `payload` ("FOR FABLE-AUDITOR RELEVANT TO THE C9 REVIEW" in a
# defect_3 string; "action: DOC FIX requested … operator-directed relay") and a
# context-economy payload truncation cut exactly the sentences carrying it. No
# tool could have known better, because nothing structural said "this must reach
# agent X" or "this needs action". These fields and the triage view make that
# intent machine-readable, delivery-independent, and impossible to consume by
# advancing a cursor.

ROUTING_FIELD = "needs_routing_to"
ACTION_FIELD = "action_required"

# ------------------------------------------------------------ addressing (2026-08-12)
#
# The schema had NO FYI CONCEPT. One `action_required` boolean applied to every
# member of `needs_routing_to`, so a fleet-wide report marked EVERY reader as
# owing an action — and the relay then rewrote `to` on each fan-out copy, so a CC
# was structurally indistinguishable from an assignment on arrival. Measured
# 2026-08-12 across the fleet's inboxes: 499 `action_required` rows, only 86
# sole-target — 83% of what an agent had to triage was not its own (73-89%
# per agent). A triage queue that is 83% other people's work is not read.
#
# The split: `assignee` is the ONE party that must act; `cc` is reach-only and
# owes nothing. MUST-ACT items get full detail and a disposition; FYI items get
# one line and are cleared by advancing a cursor.
ASSIGNEE_FIELD = "assignee"
CC_FIELD = "cc"
CC_DELIVERY_FIELD = "cc_delivery"

# What clears an action_required item: any substantive response, or an ack that
# says WHAT HAPPENED. A bare ack is receipt, not action.
TERMINAL_DISPOSITIONS = frozenset({"done", "declined", "handed-off", "superseded"})

_ROUTING_KEYWORD = (r"(?:\bfor\b|\brelay\b|\broute\b|\bforward\b|\battention\b|"
                    r"\brelevant\b|\bmust\s+reach\b)")
_ACTION_PROSE = re.compile(
    r"\baction[\s_-]*(?:required|requested)\b|\brequires\s+action\b", re.IGNORECASE)


def logical_id(row: dict) -> str:
    """One id per logical message: a daemon relay copy (relayed_src set) and its
    outbox original are the SAME message to triage, so a disposition against
    either id clears both."""
    return str(row.get("relayed_src") or row.get("id") or "")


def action_addressees(row: dict) -> list[str]:
    """The parties this row says must ACT — in precedence order.

    `assignee` wins outright (it is singular by construction). Otherwise the
    legacy resolution: `needs_routing_to` if set, else a concrete `to`. Returns
    [] when the row asks nobody to act. A list LONGER THAN ONE is the defect this
    refactor exists to kill: `append` refuses to write one, and triage treats a
    legacy multi-target action row as FYI for everyone, because a request N
    agents share is a request none of them owns.
    """
    if not row.get(ACTION_FIELD) and not row.get(ASSIGNEE_FIELD):
        return []
    assignee = row.get(ASSIGNEE_FIELD)
    if assignee:
        return [str(assignee)]
    targets = row.get(ROUTING_FIELD)
    if isinstance(targets, list) and targets:
        return [str(t) for t in targets]
    to = str(row.get("to") or "")
    if to and to != "*":
        return [to]
    return []


def cc_targets(row: dict) -> list[str]:
    """Reach-only readers: the explicit `cc` list, plus every `needs_routing_to`
    entry that is not the assignee. A routed-to agent that is not the assignee
    was always reach-only in substance; now it is reach-only in the report."""
    out: list[str] = []
    cc = row.get(CC_FIELD)
    if isinstance(cc, list):
        out += [str(c) for c in cc]
    acting = set(action_addressees(row)) if len(action_addressees(row)) == 1 else set()
    targets = row.get(ROUTING_FIELD)
    if isinstance(targets, list):
        out += [str(t) for t in targets if str(t) not in acting]
    seen: set[str] = set()
    return [t for t in out if not (t in seen or seen.add(t))]


def must_act(row: dict, agent: str) -> bool:
    """Does `agent` personally owe an action on this row? True only for a SOLE
    action addressee — never for one of several."""
    addressees = action_addressees(row)
    return len(addressees) == 1 and addressees[0] == agent


def routing_targets(row: dict) -> list[str]:
    """Every roster id this message must REACH — assignee, cc, and legacy
    `needs_routing_to`. Empty list = not routed (ordinary mail; drain covers
    it). Reaching is not acting: see `must_act` for the latter."""
    out: list[str] = []
    for t in action_addressees(row) + cc_targets(row):
        if t and t not in out:
            out.append(t)
    return out


def prose_routing_warnings(row: dict, roster_ids: set[str]) -> list[str]:
    """Warn on the exact shape that failed 2026-07-29: routing/action intent
    written as payload prose while the structural field is unset. Advisory —
    never a failure — so existing history stays valid."""
    payload = row.get("payload")
    if not isinstance(payload, dict):
        return []
    text = json.dumps(payload, sort_keys=True)
    warnings: list[str] = []
    if not row.get(ROUTING_FIELD):
        excluded = {str(row.get("from") or ""), str(row.get("to") or "")}
        for rid in sorted(roster_ids - excluded):
            pattern = re.compile(
                _ROUTING_KEYWORD + r"[^\n]{0,60}" + re.escape(rid) + r"|" + re.escape(rid)
                + r"[^\n]{0,60}(?:\brelevant\b|\battention\b|\bmust\b)", re.IGNORECASE)
            if pattern.search(text):
                warnings.append(
                    f"payload names {rid!r} in a routing phrase but {ROUTING_FIELD} is unset — "
                    f"prose routing intent is invisible to tools and was truncated away on "
                    f"2026-07-29; set {ROUTING_FIELD}: [\"{rid}\"]")
                break
    # LINTER SYMMETRY, half 1 (2026-08-12): a DISPOSITION quoting the request it
    # answers is not a new request. This lint fired on any payload matching
    # "action required" — including an `ack` that quoted its own corr_id's text —
    # and then told the author to SET the bit, which would have re-armed the item
    # it was clearing. A row carrying a corr_id/corr_ids, or of kind `ack`, is by
    # construction ABOUT an existing request; exempt it.
    answering = bool(row.get("corr_id") or row.get("corr_ids") or row.get("kind") == "ack")
    if not row.get(ACTION_FIELD) and not answering and (
            isinstance(payload.get("action"), str) or _ACTION_PROSE.search(text)):
        warnings.append(
            f"payload carries an action request in prose but {ACTION_FIELD} is unset — set "
            f"{ACTION_FIELD}: true AND name the one party in {ASSIGNEE_FIELD} so the request "
            f"sits in that agent's MUST-ACT queue until dispositioned instead of dying in a "
            f"truncated summary")
    # LINTER SYMMETRY, half 2: the MISSING opposite polarity. The lint above only
    # ever pushed the bit ON, which is half of how 499 action_required rows
    # accumulated with 86 sole targets. A report kind broadcast to several agents
    # is an FYI wearing an assignment's clothes.
    if row.get(ACTION_FIELD) and row.get("kind") in {"finding", "status", "task-complete"}:
        addressees = action_addressees(row)
        if len(addressees) > 1:
            warnings.append(
                f"kind={row.get('kind')!r} with {ACTION_FIELD} and {len(addressees)} targets "
                f"{addressees} — this looks like FYI; use `{CC_FIELD}`. A report several agents "
                f"read is nobody's assignment: keep {ASSIGNEE_FIELD} for the one party that "
                f"must act (or drop {ACTION_FIELD} entirely) and cc the rest")
    return warnings


def routed_view(bus_root: Path, agent: str) -> dict[str, list[dict]]:
    """The standing routing queue for `agent`, derived from bus files alone.

    DISCOVERY IS DELIVERY-INDEPENDENT: the agent's full inbox (from byte 0 —
    cursors are never consulted, so draining cannot consume this queue) PLUS
    every outbox, so a message stuck in a sender's outbox because the relay
    never ran (defect C2's shape) is still visible to its target. Reading
    another agent's outbox is legal — single-writer governs writes.

    STATE per logical message, judged only from the agent's OWN outbox rows
    whose corr_id resolves (via relay-copy aliases) to the message:
      pending   -> no reference at all
      acked     -> bare ack(s) only; clears reach-only messages, but an
                   action_required message KEEPS APPEARING (receipt != action)
      actioned  -> any non-ack kind, or an ack with payload.disposition in
                   TERMINAL_DISPOSITIONS; drops off the queue
    Self-authored messages are excluded: the writer cannot miss its own mail.
    """
    inbox_rows, _ = _read_jsonl(bus_root / "inbox" / f"{agent}.jsonl")
    alias = {str(r.get("id")): logical_id(r) for r in inbox_rows if r.get("relayed_src")}
    entries: dict[str, dict] = {}

    def note(row: dict, source: str, delivered: bool) -> None:
        if str(row.get("from") or "") == agent or agent not in routing_targets(row):
            return
        entry = entries.setdefault(logical_id(row),
                                   {"row": row, "sources": [], "delivered": False})
        entry["sources"].append(source)
        if delivered:
            entry["row"] = row
            entry["delivered"] = True

    for row in inbox_rows:
        note(row, f"inbox/{agent}.jsonl", True)
    for path in sorted((bus_root / "outbox").glob("*.jsonl")):
        rows, _ = _read_jsonl(path)
        for row in rows:
            note(row, f"outbox/{path.name}", False)

    my_outbox, _ = _read_jsonl(bus_root / "outbox" / f"{agent}.jsonl")
    state: dict[str, str] = {}
    for row in my_outbox:
        # C23: a row clears every id it names — scalar `corr_id`, plus `corr_ids`.
        #
        # The rule this replaces was NOT PERFORMABLE. Clearing triage took one
        # `corr_id` per item, so a session holding ONE answer for N routed items had
        # no compliant way to send it once; `BUS_PROTOCOL.md` told authors to "write
        # it once and reference it" while no mechanism to reference it existed.
        # Measured 2026-07-29 from a careful main: 3 byte-identical payloads at
        # 17:41Z, 6 more at 17:44Z differing only in `corr_id` — nine in ten minutes,
        # hours after the discipline rule was written. Fan-out multiplies it, since
        # N dispositions × M routing targets is N×M triage entries fleet-wide.
        # Discipline cannot fix a protocol that makes the spam the only compliant
        # move, and the honest reading of two failures in ten minutes is that the
        # rule was the defect.
        corrs = [str(row["corr_id"])] if row.get("corr_id") else []
        corrs += [str(c) for c in (row.get("corr_ids") or [])]
        if not corrs:
            continue
        disposition = (row.get("payload") or {}).get("disposition")
        actioned = row.get("kind") != "ack" or disposition in TERMINAL_DISPOSITIONS
        for corr in corrs:
            lid = alias.get(corr, corr)
            if lid not in entries:
                continue
            if actioned:
                state[lid] = "actioned"
            else:
                state.setdefault(lid, "acked")

    # FYI is CURSOR-CLEARED, but only for rows that reached this agent as an
    # explicit `cc` delivery. Legacy reach-only `needs_routing_to` keeps its
    # bare-ack contract: those rows were authored under a protocol that promised
    # "advancing a cursor never clears it", and retroactively clearing them by
    # cursor would consume mail whose sender is still waiting on a receipt. They
    # simply render as one-liners now instead of full bodies.
    undrained: set[str] = set()
    try:
        undrained_rows, _ = _read_jsonl(bus_root / "inbox" / f"{agent}.jsonl",
                                        _cursor_get(bus_root, agent))
        undrained = {logical_id(r) for r in undrained_rows}
    except Exception:  # noqa: BLE001 — a missing cursor must not hide the queue
        undrained = {lid for lid in entries}

    pending: list[dict] = []
    acked_awaiting: list[dict] = []
    fyi: list[dict] = []
    for lid in sorted(entries):
        entry = entries[lid]
        row = entry["row"]
        status = state.get(lid)
        if status == "actioned":
            continue
        if must_act(row, agent):
            if status == "acked":
                if row.get(ACTION_FIELD):
                    acked_awaiting.append(entry)
                continue
            pending.append(entry)
            continue
        # Reach-only for this agent.
        if status == "acked":
            continue
        explicit_cc = bool(row.get(CC_DELIVERY_FIELD)) or agent in [
            str(c) for c in (row.get(CC_FIELD) or [])]
        # BROADCAST is the other FYI shape: a row whose action or reach went to
        # several agents at once. That is where the measured 83% came from — nobody
        # owns a request N agents share. A row routed to YOU ALONE keeps full
        # detail even without an assignee, because it IS addressed to you; the
        # collapse is for mail you got because it went to everyone.
        broadcast = (len(action_addressees(row)) > 1
                     or len(row.get(ROUTING_FIELD) or []) > 1)
        if explicit_cc and entry["delivered"] and lid not in undrained:
            continue  # cursor advance IS the disposition for a cc
        if explicit_cc or broadcast:
            fyi.append(entry)
            continue
        pending.append(entry)
    return {"pending": pending, "acked_awaiting_action": acked_awaiting, "fyi": fyi}


def print_triage(bus_root: Path, agent: str) -> None:
    """Print the standing queue IN FULL, in a TRUNCATION-EVIDENT frame.

    A message a tool shortened for context economy is exactly how the two
    2026-07-29 routed messages were lost — so this report is built to make any
    downstream truncation VISIBLY wrong rather than quietly lossy: every item
    sits between numbered BEGIN/END fences carrying its byte count and body
    sha256, and the report ends with a COMPLETE trailer. A copy missing an END
    fence or the trailer is provably cut; a fence whose byte count or digest
    disagrees with its body is provably altered.
    """
    import hashlib

    view = routed_view(bus_root, agent)
    pending, acked = view["pending"], view["acked_awaiting_action"]
    fyi = view.get("fyi") or []
    if not pending and not acked and not fyi:
        print(f"(triage: no routed messages awaiting {agent})")
        return

    total = len(pending) + len(acked)
    body_bytes = 0
    index = 0

    def fenced(entry: dict, section: str) -> None:
        nonlocal index, body_bytes
        index += 1
        body = json.dumps(entry["row"], indent=2, sort_keys=True)
        body_bytes += len(body.encode("utf-8"))
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
        print(f"--- BEGIN ROUTED MESSAGE {index}/{total} id={logical_id(entry['row'])} "
              f"section={section} bytes={len(body.encode('utf-8'))} sha256={digest} ---")
        undelivered = ("" if entry["delivered"] else
                       "   [NOT in your inbox — found by outbox scan; the relay may never "
                       "have delivered it]")
        # C40: age on the `via:` line, NOT inside `body`. The fence's byte count and
        # sha256 are computed over `body` precisely so a downstream truncation is
        # provable; decorating the body would either invalidate that or force the
        # digest to cover text the sender never wrote. The framing lines are where
        # this report already says things ABOUT a message.
        age = message_age_h(entry["row"])
        stale = ("" if age is None or age < DEFAULT_STALE_AFTER_H else
                 f"   [{age / 24:.1f} DAYS OLD — verify the work is not already done]")
        print(f"via: {' + '.join(entry['sources'])}{undelivered}{stale}")
        print(body)
        print(f"--- END ROUTED MESSAGE {index}/{total} id={logical_id(entry['row'])} ---")

    print(f"== TRIAGE STANDING QUEUE for {agent}: {total} MUST-ACT item(s)"
          f"{f' + {len(fyi)} FYI' if fyi else ''}. The MUST-ACT items are REPRODUCED IN FULL — "
          f"DO NOT TRUNCATE OR SUMMARIZE: a shortened copy of this report loses routed "
          f"intent (the 2026-07-29 failure shape). Every item has an END fence; the report "
          f"ends with a COMPLETE trailer. ==")
    if pending or acked:
        print(f"== MUST-ACT ({total}): you are the addressee. Each needs a disposition from "
              f"YOUR outbox. ==")
    if pending:
        print(f"-- {len(pending)} awaiting disposition --")
        for entry in pending:
            fenced(entry, "pending")
    if acked:
        print(f"-- {len(acked)} action_required ACKED but NOT actioned (a bare ack is "
              f"receipt, not action) --")
        for entry in acked:
            fenced(entry, "acked-awaiting-action")
    if fyi:
        # ONE LINE EACH, and that is the whole point. These reached you as a `cc`
        # or as a broadcast; you owe NO disposition and NO ack, and an explicit cc
        # is cleared by advancing your cursor. Measured 2026-08-12: 83% of the
        # fleet's action_required rows were this, printed at full length inside
        # everyone's MUST-ACT queue, which is how the queue stopped being read.
        print(f"== FYI ({len(fyi)}): reach-only — NO disposition owed, NO ack owed. A cc "
              f"clears when you advance your cursor. Read, or don't. ==")
        for entry in fyi:
            row = entry["row"]
            summary = json.dumps(row.get("payload") or {}, sort_keys=True)
            if len(summary) > 160:
                summary = summary[:157] + "..."
            marks = []
            if not entry["delivered"]:
                marks.append("NOT-IN-INBOX")
            if row.get(CC_DELIVERY_FIELD):
                marks.append("cc")
            age = message_age_h(row)
            if age is not None and age >= DEFAULT_STALE_AFTER_H:
                marks.append(f"{age / 24:.1f}d-old")
            flag = f" [{' '.join(marks)}]" if marks else ""
            print(f"   FYI {logical_id(row)} from={row.get('from', '?')} "
                  f"kind={row.get('kind', '?')} to={row.get('to', '?')}{flag} {summary}")
    if not pending and not acked:
        print(f"triage: nothing requires your action.")
        print(f"== TRIAGE REPORT COMPLETE: 0 MUST-ACT item(s), {len(fyi)} FYI. ==")
        return
    print(f"triage: to clear an item, append to YOUR outbox a row with corr_id=<its id> — any "
          f"substantive kind, or kind=ack with payload.disposition in "
          f"{sorted(TERMINAL_DISPOSITIONS)}. Advancing your cursor never clears this list.")
    if total > 1:
        # C23: say the bulk form exists at the exact moment it is needed. The
        # previous instruction implied one row per item was the only way, which is
        # how nine byte-identical payloads got sent in ten minutes by someone
        # following it correctly.
        print(f"       ONE answer for several of them? Send ONE row carrying "
              f"corr_ids: [<id>, <id>, ...] instead of repeating the payload per id. "
              f"Use it only when the answer really is the same — N distinct answers "
              f"still want N rows.")
    print(f"== TRIAGE REPORT COMPLETE: {total} MUST-ACT item(s), {body_bytes} body bytes, "
          f"{len(fyi)} FYI. A copy of this report missing any END fence or this trailer has "
          f"been TRUNCATED and has lost routed intent. ==")


def _roster_roles(bus_root: Path) -> dict[str, str]:
    """id -> role for every roster row. Same fail-closed posture as _roster_ids."""
    try:
        import yaml
        cfg = yaml.safe_load((bus_root / "config.yaml").read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001
        raise BusError(f"could not read config.yaml roster: {exc}") from exc
    roster = cfg.get("roster") if isinstance(cfg, dict) else None
    if not isinstance(roster, list):
        raise BusError("config.yaml roster is missing or malformed")
    return {str(r.get("id", "")).strip(): str(r.get("role") or "").strip()
            for r in roster if isinstance(r, dict) and str(r.get("id", "")).strip()}


def _check_routing_intent(bus_root: Path, row: dict) -> None:
    """Fail-closed authoring checks for the structural routing fields."""
    targets = row.get(ROUTING_FIELD)
    # --- addressing (2026-08-12): assignee/cc must resolve, same fail-closed
    # posture as needs_routing_to. Routing intent that does not resolve is prose
    # in disguise; that argument does not change with the field name.
    named = [str(row.get(ASSIGNEE_FIELD))] if row.get(ASSIGNEE_FIELD) else []
    named += [str(c) for c in (row.get(CC_FIELD) or [])]
    if named:
        roster = _roster_ids(bus_root)
        unknown = sorted(set(named) - roster)
        if unknown:
            raise BusError(
                f"{ASSIGNEE_FIELD}/{CC_FIELD} names non-roster id(s) {unknown} — an addressee "
                f"must be resolvable (have: {', '.join(sorted(roster))})")
        roles = _roster_roles(bus_root)
        if row.get(ASSIGNEE_FIELD) and roles.get(str(row[ASSIGNEE_FIELD])) == "retired":
            raise BusError(
                f"{ASSIGNEE_FIELD} is the retired roster row {row[ASSIGNEE_FIELD]!r} — nothing "
                f"drains a retired agent's inbox, so assigning there is a silent discard with "
                f"extra steps. Assign to the live owner of that scope instead.")
    if row.get(ASSIGNEE_FIELD) and row.get(ASSIGNEE_FIELD) in (row.get(CC_FIELD) or []):
        raise BusError(
            f"{row[ASSIGNEE_FIELD]!r} is both the {ASSIGNEE_FIELD} and on {CC_FIELD} — one "
            f"agent, two contradictory obligations. Pick: {ASSIGNEE_FIELD} means they must "
            f"act; {CC_FIELD} means they owe nothing.")

    # THE REFUSAL (2026-08-12): one assignee per action. Measured before this
    # landed: 499 action_required rows fleet-wide, 86 sole-target — so 83% of
    # every agent's triage queue was somebody else's work, and the queue stopped
    # being read. A boolean that applies to N addressees does not assign work to
    # N agents; it assigns it to nobody.
    if row.get(ACTION_FIELD):
        addressees = action_addressees(row)
        if len(addressees) > 1:
            raise BusError(
                f"{ACTION_FIELD} is set with {len(addressees)} routing targets {addressees} — "
                f"one assignee per action; N agents each owing a distinct action = N messages; "
                f"reach-only readers go in `{CC_FIELD}`. Set {ASSIGNEE_FIELD}: \"<one roster "
                f"id>\" and move the rest to {CC_FIELD}: {sorted(set(addressees[1:]))}.")

    if targets:
        roster = _roster_ids(bus_root)
        unknown = sorted({str(t) for t in targets} - roster)
        if unknown:
            raise BusError(
                f"{ROUTING_FIELD} names non-roster id(s) {unknown} — routing intent must be "
                f"resolvable or it is prose in disguise (have: {', '.join(sorted(roster))})")
        roles = _roster_roles(bus_root)
        retired = sorted(t for t in {str(t) for t in targets} if roles.get(t) == "retired")
        if retired:
            raise BusError(
                f"{ROUTING_FIELD} names retired roster row(s) {retired} — nothing drains a "
                f"retired agent's inbox, so routing there is a silent discard with extra "
                f"steps. Route to the live owner of that scope instead.")
    if row.get(ACTION_FIELD) and not targets and str(row.get("to") or "*") == "*":
        raise BusError(
            f"{ACTION_FIELD} is set but the message has no concrete addressee (to='*' and "
            f"{ROUTING_FIELD} unset) — intent with no addressee is the 2026-07-29 failure "
            f"shape; name the agent(s) in {ROUTING_FIELD}")


# --------------------------------------------------- AUD-2: typed task-assign
#
# Measured 2026-08-12: 171 DISTINCT payload keys across 55 task-assign messages.
# That is why no content rule about a dispatch was mechanizable — there was no
# vocabulary to write a rule against, so every rule had to be prose addressed to
# the author, and prose is not a channel tools act on.
#
# The schema now carries the vocabulary; these are the checks draft-7 cannot
# express (a size cap) or must not express here (a `required` that would retro-
# invalidate the 119 pre-migration rows on the live bus). AUTHORING-SIDE ONLY:
# `validate` never fails on a legacy row, and the relay keeps delivering them.

# A dispatch bigger than this belongs in a file. The number is the point at which
# a task-assign stops fitting in a triage report a reader will actually read.
TASK_ASSIGN_PAYLOAD_MAX_BYTES = 4096

# The typed vocabulary. A key outside it WARNS (never refuses) — the 171-key
# sprawl is a habit, and refusing mid-flight senders would just move the failure.
_TASK_ASSIGN_KEYS = frozenset({
    "lane", "lease_expires_ts", "epoch", "spec_ref", "inline_spec",
    "task_text", "row_ref", "screened_by", "expected_occupancy", "constraints",
    "brief_path", "operator_signature_needed",
})


def check_task_assign(row: dict) -> list[str]:
    """Fail-closed authoring checks for `task-assign`. Returns WARNINGS; raises
    BusError on the two conditions that make a dispatch unusable. Gated on
    kind == task-assign, so no other kind is affected."""
    if row.get("kind") != "task-assign":
        return []
    payload = row.get("payload")
    if not isinstance(payload, dict):
        raise BusError("task-assign requires a payload object")

    text = payload.get("task_text")
    if not (isinstance(text, str) and text.strip()):
        raise BusError(
            "task-assign payload is missing `task_text` — the dispatch IDENTITY. A "
            "`row_ref` is a hint, not an identity: anchor rot measured 34.5% queue-wide "
            "on 2026-08-11 (27% twelve days earlier), so `file.md:LINE` names a different "
            "row every few weeks. Put the backlog row's TEXT in payload.task_text; "
            "re-resolve it with scripts/coordination/backlog_row_check.py --row \"<text>\".")

    size = len(json.dumps(payload, sort_keys=True).encode("utf-8"))
    if size > TASK_ASSIGN_PAYLOAD_MAX_BYTES and not payload.get("brief_path"):
        raise BusError(
            f"task-assign payload is {size} bytes (cap {TASK_ASSIGN_PAYLOAD_MAX_BYTES}) and "
            f"carries no `brief_path` — a dispatch too big to read inside a triage report "
            f"gets read as a wall and skimmed. Write the brief to a file and send the "
            f"pointer: payload.brief_path plus task_text, lane, lease_expires_ts, epoch.")

    warnings: list[str] = []
    unknown = sorted(set(payload) - _TASK_ASSIGN_KEYS)
    if unknown:
        warnings.append(
            f"task-assign payload carries key(s) outside the typed vocabulary: {unknown} — "
            f"171 distinct payload keys across 55 dispatches is why no content rule about a "
            f"dispatch is mechanizable. Use {sorted(_TASK_ASSIGN_KEYS)} or put it in the brief.")
    if isinstance(payload.get("constraints"), str):
        warnings.append(
            "task-assign `constraints` is a prose string — a restated constraint cites the "
            "line it derives from or it is not a constraint (F-20: a brief asserted "
            "`lanes: [none]` that the roster never imposed). Use the typed form: "
            "[{\"constraint\": \"...\", \"source\": \"file:line | msg-id | config key\"}].")
    if not payload.get("expected_occupancy"):
        warnings.append(
            "task-assign has no `expected_occupancy` — how long should this hold the "
            "hardware? F-14: seconds-long work was queued at a card that needed hours, and "
            "nothing in the dispatch made the mismatch expressible. State est_h + basis.")
    if not payload.get("screened_by"):
        warnings.append(
            "task-assign has no `screened_by` receipt — run backlog_row_check.py on the row "
            "first. (It proves WELL-FORMED, not STILL-NEEDED: four of eight rows screened on "
            "2026-08-12 were already satisfied, so verify the premise too.)")
    return warnings


# ------------------------------------------------------------------ commands


def cmd_append(args: argparse.Namespace) -> int:
    bus_root = Path(args.bus_root)
    row = json.loads(args.json)

    if args.target in {"outbox", "heartbeat"}:
        _require_roster_id(bus_root, args.agent)

    if args.target == "queue":
        path = bus_root / "queue.jsonl"
        definition = "queue_row"
        row.setdefault("schema_version", QUEUE_SCHEMA_VERSION)
    elif args.target == "inbox":
        if not args.to:
            raise BusError("--target inbox requires --to <agent>")
        path = bus_root / "inbox" / f"{args.to}.jsonl"
        definition = "msg"
    elif args.target == "outbox":
        path = bus_root / "outbox" / f"{args.agent}.jsonl"
        definition = "msg"
    else:  # heartbeat
        path = bus_root / "heartbeats" / f"{args.agent}.json"
        owner = required_writer(bus_root, path)
        if owner != args.agent:
            raise BusError(f"{args.agent} may not write {path.name} (owner: {owner})")
        row.setdefault("agent", args.agent)
        row.setdefault("ts", _utcnow_iso())
        _write_atomic(path, row)
        print(f"heartbeat: {path}")
        return 0

    owner = required_writer(bus_root, path)
    if owner != args.agent:
        raise BusError(
            f"single-writer violation: {args.agent} may not write {path.relative_to(bus_root)} "
            f"— that file's only writer is {owner}"
        )

    row.setdefault("ts", _utcnow_iso())
    if definition == "msg":
        row.setdefault("schema_version", MSG_SCHEMA_VERSION)
        row.setdefault("from", args.agent)
        existing, _ = _read_jsonl(path)
        # Compact UTC stamp: sortable and free of '+' / offset punctuation, so
        # the id stays a single clean token. `ts` keeps the full ISO form.
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        row.setdefault("id", f"msg-{stamp}-{len(existing) + 1}-{args.agent}")

    validate_row(bus_root, row, definition)
    if definition == "msg":
        _check_routing_intent(bus_root, row)
        task_assign_warnings = check_task_assign(row)
        try:
            roster = _roster_ids(bus_root)
        except BusError:
            roster = set()
        for warning in prose_routing_warnings(row, roster) + task_assign_warnings:
            print(f"session_bus: WARN {warning}", file=sys.stderr)
    _append_jsonl(path, row)
    print(f"appended -> {path.relative_to(bus_root)}  ({row.get('id') or row.get('task_id')})")
    return 0


def cmd_fold(args: argparse.Namespace) -> int:
    latest = fold_queue(Path(args.bus_root))
    if args.json:
        print(json.dumps(latest, indent=2, sort_keys=True))
        return 0
    if not latest:
        print("(queue empty)")
        return 0
    print(f"{'task_id':<28} {'status':<18} {'lane':<5} {'gating':<6} {'owner':<18} epoch")
    for tid in sorted(latest):
        r = latest[tid]
        print(f"{tid:<28} {r.get('status',''):<18} {r.get('lane',''):<5} "
              f"{r.get('gating',''):<6} {str(r.get('owner') or '-'):<18} {r.get('epoch','')}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    bus_root = Path(args.bus_root)
    problems: list[str] = []
    warnings: list[str] = []
    checked = 0
    try:
        roster_ids = _roster_ids(bus_root)
    except BusError as exc:
        problems.append(str(exc))
        roster_ids = set()

    # C8: a roster row whose endpoint has no working delivery path is unreachable
    # by BOTH channels — nothing pushes to it, and tmux_adapter refuses to nudge a
    # non-tmux endpoint — so assigned work accumulates unread and rots silently.
    # Observed 2026-07-28: a task-assign to an idle `monitor:file` agent sat
    # undelivered at unread=1. Surface it; never let it be silent.
    try:
        cfg_path = bus_root / "config.yaml"
        import yaml  # lazy: keeps the rest of the CLI dependency-free
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        for entry in (cfg.get("roster") or []):
            if not isinstance(entry, dict):
                continue
            aid = str(entry.get("id", "")).strip()
            ep = str(entry.get("endpoint") or "")
            if not aid or ep.startswith("tmux:"):
                continue
            try:
                pending, _ = _read_jsonl(bus_root / "inbox" / f"{aid}.jsonl",
                                         _cursor_get(bus_root, aid))
                unread = len(pending)
            except Exception:  # noqa: BLE001
                unread = "unknown"
            warnings.append(
                f"roster/{aid}: endpoint {ep!r} has no push delivery and cannot be "
                f"nudged (not a tmux endpoint) — assigned work can rot unread "
                f"(currently {unread}). Re-point it at a tmux window or give "
                f"{ep!r} a real push mechanism.")
    except Exception as exc:  # noqa: BLE001 - never let the lint itself fail closed
        warnings.append(f"roster endpoint check skipped: {exc}")

    queue = bus_root / "queue.jsonl"
    if queue.exists():
        rows, _ = _read_jsonl(queue)
        for i, row in enumerate(rows, 1):
            checked += 1
            try:
                validate_row(bus_root, row, "queue_row")
            except BusError as e:
                problems.append(f"queue.jsonl:{i}: {e}")

    for area in ("inbox", "outbox"):
        for path in sorted((bus_root / area).glob("*.jsonl")):
            if area == "outbox" and path.stem not in roster_ids:
                warnings.append(f"outbox/{path.name}: non-roster writer file is ignored; preserved "
                                "pending operator disposition")
            expected = required_writer(bus_root, path)
            rows, _ = _read_jsonl(path)
            for i, row in enumerate(rows, 1):
                checked += 1
                try:
                    validate_row(bus_root, row, "msg")
                except BusError as e:
                    problems.append(f"{area}/{path.name}:{i}: {e}")
                # Routing-intent-in-prose lint (2026-07-29) — authoring side only
                # (outbox), so one logical message warns once, not once per relay
                # copy. The exact shape that lost two routed messages today.
                if area == "outbox":
                    for w in prose_routing_warnings(row, roster_ids):
                        warnings.append(f"{area}/{path.name}:{i} ({row.get('id')}): {w}")
                # Single-writer lint: every row in an outbox must be FROM its owner.
                if area == "outbox" and row.get("from") != expected:
                    problems.append(
                        f"{area}/{path.name}:{i}: single-writer violation — from="
                        f"{row.get('from')!r} but this file's only writer is {expected!r}"
                    )

    for path in sorted((bus_root / "heartbeats").glob("*.json")):
        if path.stem not in roster_ids and path.stem != COORDINATOR_DAEMON:
            warnings.append(f"heartbeats/{path.name}: non-roster writer file is ignored; preserved "
                            "pending operator disposition")
        checked += 1
        try:
            hb = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            problems.append(f"heartbeats/{path.name}: malformed: {e}")
            continue
        expected = required_writer(bus_root, path)
        if hb.get("agent") != expected:
            problems.append(f"heartbeats/{path.name}: agent={hb.get('agent')!r} != {expected!r}")
        if hb.get("state") not in {"idle", "working", "draining", None}:
            problems.append(f"heartbeats/{path.name}: bad state {hb.get('state')!r}")

    # R7: the trust-boundary list is hash-pinned. The PreToolUse hook stops the
    # ordinary edit path, but a direct shell write bypasses hooks entirely — so
    # the pin is the layer that still catches it, after the fact.
    problems.extend(check_trust_boundary_pin(bus_root))
    checked += 1

    print(f"checked {checked} record(s)")
    for warning in warnings:
        print(f"  WARN {warning}")
    if problems:
        for p in problems:
            print(f"  FAIL {p}")
        return 1
    print("  OK — schema clean, single-writer clean, trust-boundary pin intact")
    return 0


def check_trust_boundary_pin(bus_root: Path) -> list[str]:
    """Compare human_only_paths.yaml against its recorded sha256.

    Returns a list of problem strings (empty when intact). A missing pair is
    reported, not ignored: an absent gate list means nothing is enforced, which
    is worse than a drifted one because it looks like nothing is wrong.
    """
    gate = bus_root / "human_only_paths.yaml"
    pin = bus_root / "human_only_paths.sha256"
    if not gate.exists() and not pin.exists():
        return ["trust boundary: human_only_paths.yaml and its .sha256 pin are both absent — "
                "nothing is enforced"]
    if not gate.exists():
        return ["trust boundary: pin exists but human_only_paths.yaml is missing"]
    if not pin.exists():
        return ["trust boundary: human_only_paths.yaml exists but its .sha256 pin is missing — "
                "drift would be undetectable"]
    import hashlib

    actual = hashlib.sha256(gate.read_bytes()).hexdigest()
    expected = pin.read_text(encoding="utf-8").split()[0].strip() if pin.read_text().strip() else ""
    if actual != expected:
        return [f"trust boundary DRIFT: human_only_paths.yaml is {actual[:16]}… but the pin says "
                f"{expected[:16] or '(empty)'}… — the gate list changed outside the operator path. "
                f"Re-pin deliberately or revert."]
    return []


def _cursor_path(bus_root: Path, agent: str) -> Path:
    return bus_root / "cursors" / f"{agent}.json"


def _cursor_get(bus_root: Path, agent: str) -> int:
    """Read position, defaulting to 0 — which REPLAYS rather than skips.

    THREE STATES, NOT TWO (`mainB`, 2026-08-12, routed rather than committed because
    the fix belonged with the loaded test suite). A cursor can be MISSING (handled:
    replay), CORRUPT (handled: replay), or PRESENT-BUT-UNREADABLE — bad mode, bad ACL,
    I/O error. That last one raised `OSError` straight out of the drain, so the agent
    neither replayed nor skipped: it CRASHED, and presented as a stuck agent, which is
    the exact signature improved at cc81c119. Only two of the three were covered.

    `OSError` also closes a TOCTOU hole the `exists()` check opens: on a bus whose
    runtime was wiped mid-flight, the file can vanish between the check and the read,
    and `FileNotFoundError` is an `OSError`.

    Defaulting to 0 is the deliberate fail-SAFE direction, verified by `mainB` on
    themselves: a lost cursor costs duplicate delivery and noise, never lost messages.
    """
    path = _cursor_path(bus_root, agent)
    try:
        if not path.exists():
            return 0
        return int(json.loads(path.read_text(encoding="utf-8")).get("offset", 0))
    except (json.JSONDecodeError, ValueError, TypeError, OSError):
        return 0


def cmd_cursor(args: argparse.Namespace) -> int:
    bus_root = Path(args.bus_root)
    # C29: `required_writer` below accepts ANY stem under `cursors/`, so it answers
    # "may this agent write this path" and never "is this agent real". Verified
    # 2026-07-29: `cursor --agent another-ghost --set 5` exited 0 and created
    # `cursors/another-ghost.json`. A cursor is a read POSITION for an identity; one
    # for an identity that does not exist is a claim about nobody, and it makes the
    # ghost look provisioned to anything that lists that directory.
    _require_roster_id(bus_root, args.agent)
    path = _cursor_path(bus_root, args.agent)
    owner = required_writer(bus_root, path)
    if owner != args.agent:
        raise BusError(f"{args.agent} may not write another agent's cursor")
    if args.set is None:
        print(_cursor_get(bus_root, args.agent))
        return 0
    current = _cursor_get(bus_root, args.agent)
    if args.set < current:
        raise BusError(f"cursor[{args.agent}] cannot rewind from {current} to {args.set}; "
                       "BUS_PROTOCOL rule 4 permits only equal or advancing offsets")
    _write_atomic(path, {"agent": args.agent, "offset": int(args.set), "ts": _utcnow_iso()})
    print(f"cursor[{args.agent}] = {args.set}")
    return 0


DEFAULT_STALE_AFTER_H = 24.0


def message_age_h(row: dict, now: float | None = None) -> float | None:
    """Hours since the message was authored, or None if its `ts` is unusable."""
    try:
        authored = datetime.fromisoformat(str(row.get("ts"))).timestamp()
    except (TypeError, ValueError):
        return None
    return max(0.0, ((time.time() if now is None else now) - authored) / 3600.0)


def daemon_argv(pid: int) -> str | None:
    """argv of `pid`, or None where it cannot be read (no /proc is a portability
    fact, never evidence of death). Separate so a test can isolate identity from
    liveness — pytest's own pid is alive and is legitimately not the daemon."""
    try:
        raw = (Path("/proc") / str(pid) / "cmdline").read_bytes()
    except OSError:
        return None
    return raw.replace(b"\0", b" ").decode("utf-8", "replace").strip() or None


def daemon_is_serving(bus_root: Path, tick_s: float = 45.0,
                      missed_ticks: int = 10) -> tuple[bool, str]:
    """Is the coordinator-daemon alive, itself, and ticking? (ok, reason)

    C37, second half (2026-08-11). The identity and freshness checks landed in
    `session_bus_coordinator.py status`, and that fixed the REPORT — but the report
    was pull-only, and for 243 hours nobody pulled. The supervisor that would have
    noticed was dead too, so "something will catch it" had no floor.

    This is the floor, and it needs no host change and no new daemon: **every agent
    runs `drain` at every task boundary**, by CLAUDE.md and by every task brief. So
    the check runs there, dozens of times an hour across the fleet, and the outage
    becomes visible within ONE task boundary instead of ten days.

    Deliberately duplicated rather than imported: `session_bus.py` is the agent-side
    tool and must not depend on the coordinator module to tell an agent the bus is
    dead — a check that imports the thing it is checking on is the shape that fails
    exactly when it is needed. It is also read-only and cheap: one stat, one small
    read, one `os.kill(pid, 0)`.
    """
    path = bus_root / "heartbeats" / f"{COORDINATOR_DAEMON}.json"
    try:
        hb = json.loads(path.read_text(encoding="utf-8"))
        age = time.time() - path.stat().st_mtime
    except (OSError, json.JSONDecodeError):
        return False, f"no readable {COORDINATOR_DAEMON} heartbeat at {path}"

    pid = hb.get("pid")
    try:
        pid = int(pid)
        os.kill(pid, 0)
    except (TypeError, ValueError):
        return False, f"heartbeat carries no usable pid ({hb.get('pid')!r})"
    except ProcessLookupError:
        return False, f"pid {pid} does not exist — the daemon is DEAD"
    except PermissionError:
        pass                                    # exists under another uid
    except OSError as exc:
        return True, f"pid {pid} liveness unknown ({exc}); heartbeat {age:.0f}s old"

    argv = daemon_argv(pid)
    if argv is not None and "session_bus_coordinator" not in argv:
        return False, (f"pid {pid} exists but is running {argv[:48]!r}, NOT the daemon — "
                       f"the recorded pid was recycled")

    limit = max(tick_s * missed_ticks, 120.0)
    if age > limit:
        return False, (f"pid {pid} is alive but the heartbeat is {age:.0f}s old, past the "
                       f"{limit:.0f}s bound — the daemon is WEDGED, not serving")
    return True, f"pid {pid} alive, heartbeat {age:.0f}s old"


def _print_daemon_health(bus_root: Path) -> None:
    """Say it only when it is BAD. A line on every drain is a line nobody reads."""
    ok, why = daemon_is_serving(bus_root)
    if ok:
        return
    print(f"\n!! COORDINATOR-DAEMON IS NOT SERVING THIS BUS: {why}.\n"
          f"   Nothing is relaying outbox messages, so anything you send now sits "
          f"undelivered and anything sent to you will not arrive. This is the 243h "
          f"outage of 2026-08-01..11 repeating; report it rather than working past it.",
          file=sys.stderr)


def _print_staleness(rows: list[dict], stale_after_h: float) -> None:
    """Say, out loud, which of the messages just drained are OLD.

    C40 (2026-08-11). When the coordinator-daemon came back from its 243h outage it
    relayed 703 messages in one burst. `mainA` and `mainB`, spawned minutes earlier,
    drained that backlog and BOTH self-assigned `p2-5l-stack-numa-doc-debt` — work
    `auditor` had completed on 2026-07-29 as `ae40ee8b`. They burned tokens on it
    until the coordinator could redirect them.

    Nothing was delivered wrongly; that is C28's subject and this is not it. The
    delivery was correct and the AGE was invisible: `ts` is printed inside each JSON
    body and nowhere else, so "is this still current?" was a judgement every reader
    had to make per message, and a session with no history makes it wrong. A fresh
    main cannot tell this minute's assignment from twelve-day-old mail, and both
    look equally like instructions.

    Written to STDERR on purpose. Stdout is JSONL and consumers parse it; the msg
    schema sets `additionalProperties: false`, so decorating the rows themselves
    would make anything that re-validates a drained row start failing. The framing
    that is already on stderr is where a human reads, and this joins it.
    """
    aged = [(row, message_age_h(row)) for row in rows]
    stale = [(row, age) for row, age in aged if age is not None and age >= stale_after_h]
    if not stale:
        return
    print(f"\n!! {len(stale)} of {len(rows)} message(s) are OLDER THAN {stale_after_h:g}h. "
          f"Check whether the work is already done before acting on them — a relayed "
          f"backlog looks exactly like fresh instructions.", file=sys.stderr)
    for row, age in sorted(stale, key=lambda pair: -pair[1]):
        days = age / 24.0
        stamp = f"{days:.1f}d" if days >= 1 else f"{age:.0f}h"
        print(f"   {stamp:>6} old  {row.get('kind', '?')} from {row.get('from', '?')}"
              f"  task={row.get('task_id')}  id={row.get('id')}", file=sys.stderr)


# ------------------------------------------------- AUD-3: drain boundary checks
#
# `drain` is the role's ONE PROVEN CHECKPOINT. Guardrail 1 makes it mandatory at
# every task boundary, which makes it the only place a check is certain to run —
# every other reminder competes with retrieval-at-the-moment-of-emission and
# loses. Three readings that were each missed repeatedly, moved to the one place
# they cannot be missed. All three are stderr framing: stdout is JSONL.
#
# Each is best-effort and NEVER fails the drain — but "best-effort" is not
# "silent": a check that cannot read its input SAYS SO, because a missing reading
# rendered as a clean one is the failure class this whole refactor exists to close.

FLEET_WATCH_LOG = "logs/fleet_watch.log"
FLEET_WATCH_STALE_S = 900.0
_OCCUPANCY_MARKERS = ("COMPUTE-IDLE", "IDLE-CANDIDATE")


def _repo_root(bus_root: Path) -> Optional[Path]:
    """The repo the bus lives in: <repo>/coordination/session-bus."""
    try:
        root = bus_root.resolve().parents[1]
    except IndexError:
        return None
    return root if (root / ".git").exists() else None


def _print_scripts_hygiene(bus_root: Path) -> None:
    """Untracked/modified counts under `scripts/`. Agent infrastructure rotting
    uncommitted in a shared tree is invisible until someone else's pathspec
    commit sweeps it up or a checkout reverts it with no reflog."""
    root = _repo_root(bus_root)
    if root is None:
        print("boundary: scripts/ hygiene UNREADABLE — no repo root above the bus root",
              file=sys.stderr)
        return
    try:
        out = subprocess.run(["git", "status", "--porcelain", "--", "scripts/"],
                             cwd=str(root), capture_output=True, text=True, timeout=20)
    except Exception as exc:  # noqa: BLE001
        print(f"boundary: scripts/ hygiene UNREADABLE ({exc})", file=sys.stderr)
        return
    if out.returncode != 0:
        print(f"boundary: scripts/ hygiene UNREADABLE (git exit {out.returncode}: "
              f"{out.stderr.strip()[:120]})", file=sys.stderr)
        return
    lines = [l for l in out.stdout.splitlines() if l.strip()]
    untracked = sum(1 for l in lines if l.startswith("??"))
    modified = len(lines) - untracked
    if not lines:
        print(f"boundary: scripts/ clean (0 modified, 0 untracked) in {root}", file=sys.stderr)
        return
    print(f"boundary: scripts/ has {modified} modified + {untracked} untracked file(s) in "
          f"{root} — commit what you changed with a PATHSPEC-limited commit before this "
          f"boundary closes; a shared tree sweeps uncommitted hunks into whoever commits next.",
          file=sys.stderr)


def _print_owed_actions(bus_root: Path, agent: str) -> None:
    """The action_required items THIS agent owes, with AGE. The triage machinery
    already knew them; it never said how old they were, so a two-week-old
    unanswered request read exactly like this minute's."""
    try:
        view = routed_view(bus_root, agent)
    except Exception as exc:  # noqa: BLE001
        print(f"boundary: owed-action check UNREADABLE ({exc})", file=sys.stderr)
        return
    owed = [e for e in (view["pending"] + view["acked_awaiting_action"])
            if must_act(e["row"], agent)]
    if not owed:
        print(f"boundary: 0 action_required rows owed by {agent}.", file=sys.stderr)
        return
    print(f"boundary: {len(owed)} action_required row(s) OWED BY YOU and unanswered:",
          file=sys.stderr)
    def _age(entry: dict) -> float:
        return message_age_h(entry["row"]) or 0.0
    for entry in sorted(owed, key=_age, reverse=True):
        row, age = entry["row"], message_age_h(entry["row"])
        stamp = "age?" if age is None else (
            f"{age / 24:.1f}d" if age >= 24 else f"{age:.0f}h")
        print(f"   {stamp:>6} old  {row.get('kind', '?')} from {row.get('from', '?')}  "
              f"id={logical_id(row)}", file=sys.stderr)


def _print_fleet_watch_occupancy(bus_root: Path) -> None:
    """The last COMPUTE-IDLE / IDLE-CANDIDATE line, VERBATIM, with its path.

    The staleness guard is MANDATORY, not decoration: fleet_watch runs
    unsupervised, so its log going quiet is indistinguishable from the fleet
    being busy. Relaying a stale line as current is exactly the failure class
    this refactor exists to close, and a reading whose window does not overlap
    the phenomenon is not evidence about the phenomenon.
    """
    root = _repo_root(bus_root)
    path = (root / FLEET_WATCH_LOG) if root else Path(FLEET_WATCH_LOG)
    if not path.exists():
        print(f"boundary: occupancy UNKNOWN — {path} does not exist (fleet_watch not "
              f"running?). Do not report the fleet as busy or idle on this evidence.",
              file=sys.stderr)
        return
    try:
        age_s = time.time() - path.stat().st_mtime
        line = ""
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if any(m in raw for m in _OCCUPANCY_MARKERS):
                line = raw
    except Exception as exc:  # noqa: BLE001
        print(f"boundary: occupancy UNREADABLE ({path}: {exc})", file=sys.stderr)
        return
    if age_s > FLEET_WATCH_STALE_S:
        print(f"boundary: occupancy STALE — {path} last written {age_s / 60:.0f} min ago "
              f"(> {FLEET_WATCH_STALE_S / 60:.0f} min). The line below is HISTORY, not the "
              f"current state; do NOT relay it as current. Check fleet_watch is alive first.",
              file=sys.stderr)
    if not line:
        print(f"boundary: no {'/'.join(_OCCUPANCY_MARKERS)} line in {path}", file=sys.stderr)
        return
    freshness = "STALE" if age_s > FLEET_WATCH_STALE_S else f"{age_s / 60:.0f}m old"
    print(f"boundary: last occupancy line ({freshness}) from {path}:", file=sys.stderr)
    print(f"   {line}", file=sys.stderr)


def cmd_drain(args: argparse.Namespace) -> int:
    """Print this agent's inbox past its cursor and advance. The one-liner
    agents run at every task boundary."""
    bus_root = Path(args.bus_root)
    # C29 (2026-07-29): the two halves of this CLI disagreed about whether an identity
    # must EXIST. `append --agent <ghost>` fails closed with the valid id list, while
    # this checked only that the inbox FILE exists (the C3 guard) — so an unknown id
    # with a leftover inbox exited 0, printed messages addressed to somebody else,
    # advanced a cursor, and never said the identity has no roster row. Reproduced:
    # exit 0, 10 rows printed, `cursors/<ghost>.json` created.
    #
    # Not academic, and C28 is why: relay RECREATES old-id inboxes, so the
    # file-exists check passes for exactly the ids that no longer exist. A session
    # still using its pre-rename id drains a ghost inbox cleanly, sees "no new
    # messages", and concludes it is up to date — the precise C3 failure, one identity
    # check short of being fixed.
    #
    # REFUSE rather than warn, deliberately. A warning would leave the cursor advance
    # in place, which silently CONSUMES another agent's mail — the read is the damage,
    # not the exit code. The mid-rename hazard the defect note raises is real but
    # measured-bounded: no automated caller uses a stale id (the daemon interpolates
    # roster-derived ids), and the only stale reference is one line in an archived
    # task file.
    _require_roster_id(bus_root, args.agent)
    inbox = bus_root / "inbox" / f"{args.agent}.jsonl"

    # C3: fail CLOSED on an unprovisioned route. _read_jsonl returns empty for a
    # missing file, which made "never provisioned" indistinguishable from "nothing
    # new" — the coordinator-agent drained clean for a whole session while messages
    # addressed to it were being dropped (defect C1, 2026-07-28). A missing inbox is
    # a bootstrap error, never a quiet no-op.
    if not inbox.exists():
        print(f"session_bus: no inbox for '{args.agent}' at {inbox} — route not "
              f"provisioned. Every roster member needs 4 files (inbox/outbox/"
              f"heartbeat/cursor); run `session_bus.py provision --agent {args.agent}`.",
              file=sys.stderr)
        # The triage view is delivery-independent (outbox scan), so it still
        # works — and matters MOST — when the inbox route is broken.
        if getattr(args, "triage", False):
            print_triage(bus_root, args.agent)
        return 2

    start = _cursor_get(bus_root, args.agent)
    rows, end = _read_jsonl(inbox, start)

    if rows:
        for row in rows:
            print(json.dumps(row, sort_keys=True))
        if not args.peek:
            _write_atomic(_cursor_path(bus_root, args.agent),
                          {"agent": args.agent, "offset": end, "ts": _utcnow_iso()})
        print(f"-- {len(rows)} message(s); cursor {start} -> {end}"
              f"{' (peek: not advanced)' if args.peek else ''}", file=sys.stderr)
        _print_staleness(rows, args.stale_after_h)
    else:
        print(f"(no new messages for {args.agent})")
    # C37: on EVERY drain, including the empty one. "(no new messages)" is precisely
    # what a dead relay looks like from inside an agent — an all-clear that is really
    # a silence. This is the check that would have caught the 243h outage on its
    # first task boundary.
    _print_daemon_health(bus_root)
    # AUD-3: the three boundary readings. On EVERY drain, empty or not — the
    # empty drain is exactly when a boundary check is most needed and least run.
    if not getattr(args, "no_boundary_checks", False):
        _print_scripts_hygiene(bus_root)
        _print_owed_actions(bus_root, args.agent)
        _print_fleet_watch_occupancy(bus_root)
    if getattr(args, "triage", False):
        print_triage(bus_root, args.agent)
    return 0


def _claim_key(row: str) -> str:
    """sha1 of the row's TEXT, whitespace-normalised and case-folded.

    Keyed on text, never on `file:line`. The dispatch queue states its own rule —
    *"line numbers are a hint, task text is the identity"* — because mains close rows
    live and every anchor below a closure shifts. Two mains reading the same row at
    different line numbers must still collide on the same key.
    """
    return hashlib.sha1(" ".join(row.split()).casefold().encode("utf-8")).hexdigest()


def cmd_claim(args: argparse.Namespace) -> int:
    """Take exclusive ownership of a backlog row, enforced by the filesystem.

    WHY THIS EXISTS. Observed 2026-07-29, not hypothetical: `mainD` claimed TOP-40 #5
    (the RLM E1a NIAH scorer) at 16:00:07 and reported it done at 16:03:51, while
    `mainC` was independently building the same thing; `mainC` found the flipped
    checkbox at 16:05:05 and withdrew its duplicate implementation
    (`outcome: collision-with-completed-work`). Two mains, one row, five minutes
    apart, one implementation thrown away — inside the first ten minutes of three
    mains working a shared 232-row queue.

    The collision map could not prevent it: it partitions FILES, not ROWS, and it is
    advisory prose. Claiming was by convention — an outbox message — and a claim only
    helps if the other main happens to DRAIN between the claim and starting work.
    Self-selection from a shared list with pull-based notification is a race by
    construction, and the window is minutes.

    So the claim is a FILE CREATED WITH O_EXCL. The create either succeeds (you own
    the row) or fails (somebody else does); there is no window between checking and
    taking, because there is no check. It needs no daemon, no authority change and no
    protocol round-trip, and it stays single-writer-clean because each claim file has
    exactly one writer for its whole life.

    ADDITIVE BY DESIGN: nothing in this module or the daemon reads `claims/`. Whether
    the fleet adopts it is the coordinator's call — this only removes the delay
    between that decision and having the mechanism.
    """
    bus_root = Path(args.bus_root)
    _require_roster_id(bus_root, args.agent)          # C29: same identity rule as everything else
    claims = bus_root / "claims"

    if args.list:
        rows = []
        for p in sorted(claims.glob("*.json")):
            try:
                rows.append(json.loads(p.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                print(f"session_bus: WARNING unreadable claim {p.name}", file=sys.stderr)
        if not rows:
            print("(no rows claimed)")
        # STALE MARKING (2026-08-12, `mainC`, on `mainB`'s finding). A claim has no
        # expiry, so a claim held by a session that died behaves as a lock nobody
        # remembers taking — and it is INVISIBLE as a blocker, because the row simply
        # never gets pulled. Measured when this was added: 15 claims, 8 of them older
        # than 300 HOURS, all from the 2026-07-29 fleet death. Two consequences seen
        # in that same set: `mainB` declined to work a row solely because `mainC` held
        # a 14-day-old claim on it, and one stale claim OUTLIVED ITS OWN ROW'S
        # CLOSURE — the legacy ComparativeResult path it names was closed in
        # `e108ec9f` while the claim stayed held.
        #
        # This only MARKS; it never releases. A claim is single-writer by design and
        # only its owner may drop it, so auto-expiry here would break the one property
        # that makes the O_EXCL scheme sound. Marking is enough: it makes the lock
        # visible to the owner and to whoever is blocked.
        # OWNER LIVENESS BEATS AGE (2026-08-12, `mainC`). The 24h rule cannot see the
        # case that actually bit this fleet: 18 claims on the books at dawn, 16 of them
        # taken THAT NIGHT — so unmarked — while their owners had gone idle and stated
        # in writing, repeatedly, that they held no claims. Age answers "how long has
        # this been here"; the question a blocked reader has is "is anyone working it".
        #
        # So the owner's heartbeat is read as a POSITIVE signal, the same way the
        # dispatch generator reads a do-not-dispatch declaration rather than inferring
        # from absence. An idle owner is not proof the row is abandoned, which is why
        # this still only MARKS — a claim is single-writer and only its owner may drop
        # it, so auto-expiry here would break the one property making O_EXCL sound.
        # It distinguishes the two cases age conflates: at the time this was written,
        # `mainA` was idle with 4 claims (residue, and they had said so) while the
        # `auditor` was working with 13 (possibly live). Age alone marked NEITHER.
        heartbeats = bus_root / "heartbeats"

        def _owner_state(agent: str) -> tuple:
            try:
                hb = json.loads((heartbeats / f"{agent}.json").read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, TypeError):
                return None, None
            return hb.get("state"), hb.get("ts")

        now = datetime.now(timezone.utc)
        for r in rows:
            marks = []
            try:
                age_h = (now - datetime.fromisoformat(r.get("ts"))).total_seconds() / 3600.0
                if age_h >= 24:
                    marks.append(f"STALE {age_h:.0f}h — owner should release or re-affirm")
            except (TypeError, ValueError):
                marks.append("unparseable ts")
            state, hb_ts = _owner_state(r.get("agent"))
            if state == "idle":
                marks.append(f"OWNER IDLE since {hb_ts} — likely residue, owner should release")
            elif state is None:
                marks.append("OWNER HAS NO HEARTBEAT — cannot tell if this is being worked")
            mark = ("  [" + " | ".join(marks) + "]") if marks else ""
            print(f"{r.get('agent'):18s} {r.get('ts')}  {r.get('row')}{mark}")
        return 0

    if not args.row:
        raise BusError("claim needs --row '<task text>' (or --list)")
    path = claims / f"{_claim_key(args.row)}.json"
    payload = {"agent": args.agent, "row": args.row, "ts": _utcnow_iso()}

    if args.release:
        # Release only what you own. Never delete another agent's claim — that would
        # reintroduce the race this closes, with the added twist of doing it silently.
        if not path.exists():
            print(f"(not claimed: {args.row[:70]})")
            return 0
        try:
            owner = json.loads(path.read_text(encoding="utf-8")).get("agent")
        except (OSError, json.JSONDecodeError):
            owner = None
        if owner != args.agent:
            raise BusError(f"{args.agent!r} may not release a row claimed by {owner!r}")
        path.unlink()
        print(f"released: {args.row[:70]}")
        return 0

    claims.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        try:
            held = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            held = {}
        owner = held.get("agent")
        if owner == args.agent:
            # Re-claiming your OWN row is not a collision; a main that restarts
            # mid-task must not be locked out of the work it is holding.
            print(f"already yours since {held.get('ts')}: {args.row[:70]}")
            return 0
        print(f"REFUSING: claimed by {owner!r} since {held.get('ts')} — {args.row[:70]}",
              file=sys.stderr)
        return 2
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, sort_keys=True)
        fh.write("\n")
    print(f"claimed by {args.agent}: {args.row[:70]}")
    return 0


def cmd_triage(args: argparse.Namespace) -> int:
    """The routing standing queue. Never reads or writes cursors: a routed
    message cannot be consumed by draining — only a corr_id disposition from the
    target's own outbox clears it."""
    bus_root = Path(args.bus_root)
    # C29, and this is the WORSE half. `routed_view` filters on
    # `agent in routing_targets(row)`, so an unknown id matches nothing and this printed
    # the reassuring `(triage: no routed messages awaiting <id>)` — exit 0, indistinguishable
    # from "you are clear". The triage report is designed to be the LOUDEST signal on
    # this bus, the one thing that survives a broken delivery path; a typo'd or stale id
    # turned it into a silent all-clear. Verified 2026-07-29: `triage --agent
    # totally-bogus-id` exited 0 with no diagnostic at all.
    _require_roster_id(bus_root, args.agent)
    print_triage(bus_root, args.agent)
    return 0


def corrections_for(bus_root: Path, agent: str) -> list[dict]:
    """Every `finding` in `agent`'s OWN outbox that carries payload.corrects.

    AUD-4. Five corrections were silently missing from the 2026-08-12 wrap-up.
    Not because anyone decided to omit them — because a correction looked like
    any other finding, so nothing could enumerate them and the omission was
    invisible on both sides. Typing the relation makes the omission visible:
    this returns the list, the wrap-up section is generated from it, and a
    correction that is not in the section is now a diff, not a memory lapse.
    """
    rows, _ = _read_jsonl(bus_root / "outbox" / f"{agent}.jsonl")
    out: list[dict] = []
    for row in rows:
        if row.get("kind") != "finding":
            continue
        payload = row.get("payload") or {}
        if not isinstance(payload, dict) or not payload.get("corrects"):
            continue
        out.append(row)
    return out


def cmd_corrections(args: argparse.Namespace) -> int:
    """Generate the wrap-up corrections section from typed `finding` rows."""
    bus_root = Path(args.bus_root)
    _require_roster_id(bus_root, args.agent)
    rows = corrections_for(bus_root, args.agent)
    since = getattr(args, "since", None)
    if since:
        rows = [r for r in rows if str(r.get("ts") or "") >= since]
    if args.json:
        print(json.dumps(rows, indent=2, sort_keys=True))
        return 0
    if not rows:
        print(f"(no corrections recorded by {args.agent}"
              f"{f' since {since}' if since else ''} — no `finding` rows carry "
              f"payload.corrects)")
        return 0
    print(f"## Corrections ({len(rows)})\n")
    print(f"Generated from {args.agent}'s outbox: `kind: finding` rows carrying "
          f"`payload.corrects`. AUD-4 — five corrections went missing from the "
          f"2026-08-12 wrap-up because nothing could enumerate them.\n")
    for row in rows:
        payload = row.get("payload") or {}
        prov = payload.get("provenance") or "provenance-unstated"
        detail = payload.get("correction") or payload.get("detail") or payload.get(
            "summary") or json.dumps({k: v for k, v in payload.items()
                                      if k not in ("corrects", "provenance")}, sort_keys=True)
        print(f"- **corrects `{payload['corrects']}`** ({prov}) — {detail}")
        print(f"  <sub>source: `{row.get('id')}` @ {row.get('ts')}</sub>")
    unstated = [r for r in rows if not (r.get("payload") or {}).get("provenance")]
    if unstated:
        print(f"\n> {len(unstated)} of these state no `provenance`. Add "
              f"`operator-verbatim` / `paraphrase` / `inferred` — a correction whose "
              f"standing is unstated gets read as the operator's own words.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    bus_root = Path(args.bus_root)
    latest = fold_queue(bus_root)

    by_status: dict[str, int] = {}
    by_lane: dict[str, int] = {}
    for row in latest.values():
        by_status[row.get("status", "?")] = by_status.get(row.get("status", "?"), 0) + 1
        by_lane[row.get("lane", "?")] = by_lane.get(row.get("lane", "?"), 0) + 1

    print("queue by status:", ", ".join(f"{k}={v}" for k, v in sorted(by_status.items())) or "(empty)")
    print("queue by lane  :", ", ".join(f"{k}={v}" for k, v in sorted(by_lane.items())) or "(empty)")

    ready_none = sum(1 for r in latest.values()
                     if r.get("status") == "READY" and r.get("lane") == "none")
    print(f"lane:none READY depth: {ready_none}"
          + ("   <-- ALARM: never-block needs a non-empty none-lane backlog" if ready_none == 0 and latest else ""))

    print("\ninbox depths (unread past each cursor):")
    for path in sorted((bus_root / "inbox").glob("*.jsonl")):
        agent = path.stem
        rows, _ = _read_jsonl(path, _cursor_get(bus_root, agent))
        print(f"  {agent:<20} {len(rows)}")

    print("\nheartbeats:")
    now = time.time()
    hbs = sorted((bus_root / "heartbeats").glob("*.json"))
    if not hbs:
        print("  (none)")
    for path in hbs:
        try:
            hb = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"  {path.stem:<20} MALFORMED")
            continue
        age = now - path.stat().st_mtime
        print(f"  {path.stem:<20} {hb.get('state','?'):<9} age={age:6.0f}s  task={hb.get('task_id') or '-'}")

    pending = bus_root / "tokens" / "token-queue.md"
    if pending.exists():
        text = pending.read_text(encoding="utf-8")
        print(f"\npending operator tokens: {text.count('- [ ]')} ungranted, {text.count('- [x]')} granted")
    return 0


def cmd_rebuild(args: argparse.Namespace) -> int:
    """R7 reconstructibility — everything a fresh coordinator-agent needs, from files alone.

    `BUS_PROTOCOL.md` rule 9 asserts that coordinator-agent state must be
    rebuildable from bus files, and that authority living only in a session's
    context is a design defect. An assertion nobody can run is not a guarantee,
    so this verb IS the check: if a fresh session can act correctly from this
    output, the invariant holds. If something it needs is missing here, that
    absence is the defect.
    """
    bus_root = Path(args.bus_root)
    latest = fold_queue(bus_root)
    roster_ids = _roster_ids(bus_root)

    def _read(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError):
            return ""

    token_text = _read(bus_root / "tokens" / "token-queue.md")
    state = {
        "rebuilt_at": _utcnow_iso(),
        "source": "bus files only — no session context consulted",
        "queue": {
            "count": len(latest),
            "by_status": {s: sum(1 for r in latest.values() if r.get("status") == s)
                          for s in sorted({r.get("status", "?") for r in latest.values()})},
            "live": {tid: r for tid, r in sorted(latest.items())
                     if r.get("status") not in TERMINAL_STATES},
        },
        "pending_operator_tokens": [
            line.strip() for line in token_text.splitlines() if line.lstrip().startswith("- [ ]")
        ],
        "granted_operator_tokens": [
            line.strip() for line in token_text.splitlines() if line.lstrip().startswith("- [x]")
        ],
        "agents": {},
        "trust_boundary": {
            "pin_problems": check_trust_boundary_pin(bus_root),
            "gate_list": "human_only_paths.yaml (human-amendment-only, hash-pinned)",
        },
    }
    for aid in sorted(roster_ids):
        hb_path = bus_root / "heartbeats" / f"{aid}.json"
        try:
            hb = json.loads(hb_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            hb = {"error": "unreadable"}
        unread, _ = _read_jsonl(bus_root / "inbox" / f"{aid}.jsonl", _cursor_get(bus_root, aid))
        state["agents"][aid] = {"heartbeat": hb, "cursor": _cursor_get(bus_root, aid),
                                "inbox_unread": len(unread)}

    if args.json:
        print(json.dumps(state, indent=2, sort_keys=True, default=str))
        return 0
    print(f"rebuilt from bus files at {state['rebuilt_at']}")
    print(f"  queue: {state['queue']['count']} rows, {state['queue']['by_status']}")
    print(f"  live (non-terminal): {list(state['queue']['live']) or '(none)'}")
    print(f"  operator tokens: {len(state['pending_operator_tokens'])} pending, "
          f"{len(state['granted_operator_tokens'])} granted")
    for aid, a in state["agents"].items():
        hb = a["heartbeat"]
        print(f"  {aid:<20} state={hb.get('state')} task={hb.get('task_id')} "
              f"cursor={a['cursor']} unread={a['inbox_unread']}")
    probs = state["trust_boundary"]["pin_problems"]
    print(f"  trust boundary: {'intact' if not probs else probs}")
    return 0


def cmd_provision(args: argparse.Namespace) -> int:
    """Create the 4 files a roster member needs. Idempotent.

    config.yaml states 'adding a main = 1 roster row + 4 files (inbox/outbox/
    heartbeat/cursor)', but nothing enforced it: coordinator-agent was added as a
    roster row with only 3 of the 4 and its inbound route silently did not exist
    (defect C1, 2026-07-28). This makes the documented step executable.
    """
    bus_root = Path(args.bus_root)
    agent = args.agent

    try:
        import yaml  # lazy: keeps the rest of the CLI dependency-free
        cfg = yaml.safe_load((bus_root / "config.yaml").read_text()) or {}
        roster = [r.get("id") for r in (cfg.get("roster") or []) if isinstance(r, dict)]
    except Exception as exc:  # noqa: BLE001 - config is advisory here
        print(f"session_bus: could not read roster ({exc}); provisioning anyway",
              file=sys.stderr)
        roster = []

    if roster and agent not in roster:
        print(f"session_bus: '{agent}' is not a roster id in config.yaml "
              f"(have: {', '.join(roster)}). Add the roster row first.", file=sys.stderr)
        return 2

    created, existed = [], []
    for rel in (f"inbox/{agent}.jsonl", f"outbox/{agent}.jsonl"):
        path = bus_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            existed.append(rel)
        else:
            path.touch()
            created.append(rel)

    cursor = _cursor_path(bus_root, agent)
    if cursor.exists():
        existed.append(f"cursors/{agent}.json")
    else:
        _write_atomic(cursor, {"agent": agent, "offset": 0, "ts": _utcnow_iso()})
        created.append(f"cursors/{agent}.json")

    hb = bus_root / "heartbeats" / f"{agent}.json"
    if hb.exists():
        existed.append(f"heartbeats/{agent}.json")
    else:
        hb.parent.mkdir(parents=True, exist_ok=True)
        _write_atomic(hb, {"agent": agent, "state": "idle", "ts": _utcnow_iso()})
        created.append(f"heartbeats/{agent}.json")

    for rel in created:
        print(f"created  {rel}")
    for rel in existed:
        print(f"exists   {rel}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="session_bus.py", description=__doc__.split("\n")[0])
    p.add_argument("--bus-root", default=str(DEFAULT_BUS_ROOT))
    p.add_argument("--print-root", action="store_true",
                    help="print the resolved canonical bus root (get_bus_root()) and exit; "
                         "does not require a subcommand -- handled before subparser dispatch "
                         "so this works standalone, e.g. from a fresh worktree checkout")
    sub = p.add_subparsers(dest="cmd", required=True)

    ap = sub.add_parser("append", help="append a schema-validated row to a file you own")
    ap.add_argument("--agent", required=True)
    ap.add_argument("--target", required=True, choices=["queue", "inbox", "outbox", "heartbeat"])
    ap.add_argument("--to", help="recipient agent (required for --target inbox)")
    ap.add_argument("--json", required=True, help="the row/message as a JSON object")
    ap.set_defaults(func=cmd_append)

    fp = sub.add_parser("fold", help="latest-row-per-task_id view of the queue")
    fp.add_argument("--json", action="store_true")
    fp.set_defaults(func=cmd_fold)

    vp = sub.add_parser("validate", help="whole-bus schema + single-writer lint")
    vp.set_defaults(func=cmd_validate)

    cp = sub.add_parser("cursor", help="get or set your own cursor")
    cp.add_argument("--agent", required=True)
    cp.add_argument("--set", type=int, default=None)
    cp.set_defaults(func=cmd_cursor)

    dp = sub.add_parser("drain", help="print your inbox past your cursor and advance")
    dp.add_argument("--agent", required=True)
    dp.add_argument("--peek", action="store_true", help="print without advancing the cursor")
    dp.add_argument("--triage", action="store_true",
                    help="also print the routing standing queue (cursor-independent, in full)")
    dp.add_argument("--no-boundary-checks", action="store_true",
                    help="skip the AUD-3 boundary readings (scripts/ hygiene, owed "
                         "action_required rows, last fleet_watch occupancy line). For "
                         "tests and non-interactive callers only — an agent at a task "
                         "boundary wants them.")
    dp.add_argument("--stale-after-h", type=float, default=DEFAULT_STALE_AFTER_H,
                    help=f"flag drained messages older than this many hours "
                         f"(default {DEFAULT_STALE_AFTER_H:g}; C40)")
    dp.set_defaults(func=cmd_drain)

    tp = sub.add_parser("triage", help="standing queue of messages routed to you "
                                       "(needs_routing_to / action_required); cursor-independent, "
                                       "printed in full, cleared only by corr_id disposition")
    tp.add_argument("--agent", required=True)
    tp.set_defaults(func=cmd_triage)

    cl = sub.add_parser("claim", help="take exclusive ownership of a backlog row (O_EXCL)")
    cl.add_argument("--agent", required=True)
    cl.add_argument("--row", help="the task TEXT (not file:line — anchors shift, text is identity)")
    cl.add_argument("--release", action="store_true", help="release a row you own")
    cl.add_argument("--list", action="store_true", help="show all currently claimed rows")
    cl.set_defaults(func=cmd_claim)

    pp = sub.add_parser("provision", help="create the 4 files a roster member needs (idempotent)")
    pp.add_argument("--agent", required=True)
    pp.set_defaults(func=cmd_provision)

    co = sub.add_parser("corrections",
                        help="wrap-up corrections section, generated from your own "
                             "`finding` rows carrying payload.corrects (AUD-4)")
    co.add_argument("--agent", required=True)
    co.add_argument("--since", help="only rows with ts >= this ISO stamp")
    co.add_argument("--json", action="store_true")
    co.set_defaults(func=cmd_corrections)

    sp = sub.add_parser("status", help="human summary of bus state")
    sp.set_defaults(func=cmd_status)

    rb = sub.add_parser("rebuild", help="derive full coordinator state from bus files alone (R7)")
    rb.add_argument("--json", action="store_true")
    rb.set_defaults(func=cmd_rebuild)
    return p


def main(argv: Optional[list[str]] = None) -> int:
    # --print-root is handled before the subparsers' `required=True` check so
    # it works with no subcommand at all (`session_bus.py --print-root`) --
    # the verification idiom a fresh worktree checkout is expected to run.
    raw = list(sys.argv[1:] if argv is None else argv)
    if "--print-root" in raw:
        print(get_bus_root())
        return 0
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except BusError as e:
        print(f"session_bus: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
