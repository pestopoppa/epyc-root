#!/usr/bin/env python3
"""Capture structured Codex dispatch evidence from two rollout files."""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import sys


SCHEMA = "fm4.codex_dispatch.v1"


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _identifier(value):
    return value if isinstance(value, str) and value.strip() else None


def _mapping(value):
    return value if isinstance(value, dict) else {}


def _canonical_agent_path(value):
    path = PurePosixPath(value)
    return (len(path.parts) > 2 and path.parts[:2] == ("/", "root")
            and ".." not in path.parts and str(path) == value)


def _result_error(fields):
    return (fields.get("is_error") is True or fields.get("isError") is True
            or fields.get("error") is not None
            or fields.get("status") in ("error", "failed", "failure"))


def _sha256(path):
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError(f"expected a regular rollout file: {path}")
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _read(path, digest, *, parent):
    metadata = []
    calls = defaultdict(list)
    results = defaultdict(list)
    turns = []
    read_digest = hashlib.sha256()
    with path.open("rb") as stream:
        for line, raw in enumerate(stream, 1):
            read_digest.update(raw)
            try:
                if not raw.endswith(b"\n"):
                    raise ValueError("incomplete JSONL line")
                record = json.loads(raw, object_pairs_hook=_object)
                if not isinstance(record, dict) or not isinstance(record.get("payload"), dict):
                    raise ValueError("expected a rollout record with an object payload")
            except (ValueError, UnicodeError) as exc:
                raise ValueError(f"invalid_rollout: {path}:{line}: {exc}") from exc
            payload = record["payload"]
            kind = payload.get("type")
            if record.get("type") == "session_meta":
                metadata.append((line, payload))
            elif parent and record.get("type") == "response_item":
                call_id = _identifier(payload.get("call_id"))
                if call_id is None:
                    continue
                if kind in ("function_call", "custom_tool_call"):
                    calls[call_id].append((line, kind, payload.get("namespace"), payload.get("name")))
                elif kind in ("function_call_output", "custom_tool_call_output"):
                    output = payload.get("output")
                    try:
                        output = json.loads(output, object_pairs_hook=_object) if isinstance(output, str) else output
                    except ValueError:
                        output = None
                    output = _mapping(output)
                    results[call_id].append((line, kind, _identifier(output.get("agent_id")),
                                             _identifier(output.get("task_name")),
                                             _result_error(payload) or _result_error(output)))
            elif not parent and record.get("type") == "event_msg" and kind in (
                    "task_started", "task_complete", "turn_aborted"):
                turns.append((line, kind, _identifier(payload.get("turn_id")),
                              bool(payload.get("error")),
                              bool(_identifier(payload.get("last_agent_message")))))
    if read_digest.hexdigest() != digest:
        raise ValueError(f"changed_input: {path}")
    return metadata, calls, results, turns


def _child_turn(turns):
    first = next((row for row in turns if row[1] == "task_started"), None)
    if first is None or first[2] is None:
        return {"state": "no_child_turn"}
    start, _, turn_id, _, _ = first
    matching = [row for row in turns if row[2] == turn_id]
    evidence = {"turn_id": turn_id, "start_line": start}
    if matching[0] != first or len(matching) > 2 or any(
            row[1] == "task_started" for row in matching[1:]):
        return dict(evidence, state="ambiguous_child_turn")
    if len(matching) == 1:
        return dict(evidence, state="launch_only")
    line, kind, _, error, final_message = matching[1]
    state = "completed" if kind == "task_complete" and not error else "ended_with_error"
    return dict(evidence, state=state, terminal_event=kind, terminal_line=line,
                final_message_present=final_message)


def _spawn_candidates(calls, results, child_id, agent_path):
    candidates = []
    for call_id, entries in calls.items():
        spawns = [entry for entry in entries
                  if entry[1:] == ("function_call", "collaboration", "spawn_agent")]
        if not spawns:
            continue
        outputs = results[call_id]
        for line, kind, agent_id, task_name, error in outputs:
            if agent_id != child_id and (agent_path is None or task_name != agent_path):
                continue
            candidate = {"call_id": call_id, "call_line": spawns[0][0], "result_line": line,
                         "result_agent_id": agent_id, "result_task_name": task_name,
                         "result_error": error}
            if len(entries) != 1 or len(outputs) != 1 or kind != "function_call_output" or line <= spawns[0][0]:
                return [candidate], "ambiguous_spawn_result"
            candidates.append(candidate)

    if len(candidates) != 1:
        return candidates, "ambiguous_spawn_result" if candidates else "missing_spawn_result"
    candidate = candidates[0]
    if candidate["result_error"]:
        return candidates, "spawn_result_error"
    if candidate["result_agent_id"] is None:
        return candidates, "native_agent_path"
    if (candidate["result_agent_id"] != child_id or
            (candidate["result_task_name"] is not None and agent_path is not None
             and candidate["result_task_name"] != agent_path)):
        return candidates, "spawn_child_identity_mismatch"
    return candidates, "direct_agent_id"


def collect(parent, child):
    """Return an identity receipt and state derived from the child's initial turn."""
    parent, child = parent.resolve(strict=True), child.resolve(strict=True)
    if parent.samefile(child):
        raise ValueError("parent and child rollouts must be distinct")
    paths = {"parent": parent, "child": child}
    inputs = {role: {"path": str(path), "sha256": _sha256(path)} for role, path in paths.items()}
    parents, calls, results, _ = _read(parent, inputs["parent"]["sha256"], parent=True)
    children, _, _, turns = _read(child, inputs["child"]["sha256"], parent=False)
    for role, path in paths.items():
        if _sha256(path) != inputs[role]["sha256"]:
            raise ValueError(f"changed_input: {path}")
    receipt = {"schema": SCHEMA, "inputs": inputs, "identity": None, "binding_kind": None,
               "task_outcome": None,
               "lineage": None, "spawn_candidates": [], "child_turn": _child_turn(turns)}
    if (len(parents) != 1 or len(children) != 1
            or parents[0][0] != 1 or children[0][0] != 1):
        return dict(receipt, disposition="invalid_session_metadata")
    parent_meta, child_meta = parents[0][1], children[0][1]
    parent_id, child_id = _identifier(parent_meta.get("id")), _identifier(child_meta.get("id"))
    source = _mapping(child_meta.get("source"))
    spawn = _mapping(_mapping(source.get("subagent")).get("thread_spawn"))
    parent_thread = _identifier(spawn.get("parent_thread_id"))
    agent_path = _identifier(spawn.get("agent_path"))
    receipt["lineage"] = {"parent_session_id": parent_id, "child_session_id": child_id,
                          "child_parent_thread_id": parent_thread, "child_agent_path": agent_path}
    if parent_id is None or child_id is None or parent_thread is None:
        return dict(receipt, disposition="missing_session_identity")
    if parent_thread != parent_id or child_id == parent_id:
        return dict(receipt, disposition="parent_child_identity_mismatch")
    if agent_path is not None and not _canonical_agent_path(agent_path):
        return dict(receipt, disposition="invalid_child_agent_path")

    candidates, disposition = _spawn_candidates(calls, results, child_id, agent_path)
    receipt["spawn_candidates"] = candidates
    if disposition in ("direct_agent_id", "native_agent_path"):
        if receipt["child_turn"]["state"] == "ambiguous_child_turn":
            return dict(receipt, disposition="ambiguous_child_turn")
        receipt["identity"] = {"parent_session_id": parent_id, "child_agent_id": child_id,
                               "dispatch_tool_use_id": candidates[0]["call_id"]}
        receipt["binding_kind"] = disposition
        disposition = "terminal_child" if "terminal_event" in receipt["child_turn"] else "launch_only"
    return dict(receipt, disposition=disposition)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--child", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        receipt = collect(args.parent, args.child)
    except (OSError, ValueError) as exc:
        print(f"FM-4 Codex dispatch refused: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["disposition"] == "terminal_child" else 1


if __name__ == "__main__":
    raise SystemExit(main())
