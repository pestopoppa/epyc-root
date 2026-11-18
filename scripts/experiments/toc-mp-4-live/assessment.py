"""Assess exact-value submissions only after proving the assigned exposure."""
import json
from pathlib import Path

import cmp4_runner as live
from cmp3_live import captured, request_text, response_text
from trial import (
    BOUNDARY_TURN,
    CHECKPOINT_CODE,
    RECORD_CODE,
    checkpoint_output,
    record_output,
    sha,
)


def _generation_hit_token_limit(attempt, record):
    response = captured(attempt, record, "response").decode("utf-8")
    payloads = [response]
    if record["stream_requested"]:
        payloads = [line[6:] for line in response.splitlines()
                    if line.startswith("data: ") and line[6:] != "[DONE]"]
    for payload in payloads:
        body = json.loads(payload)
        if body.get("stop_type") == "limit" or any(
            choice.get("finish_reason") == "length" for choice in body.get("choices", [])
        ):
            return True
    return False


def assess(attempt, row, case):
    needle = case["needle"]
    graph = live.read_json(attempt / "GRAPH.json")
    if graph["context_counter"]["total_calls"] <= 0 or graph["context_counter"]["fallback_count"] != 0:
        raise ValueError("served tokenizer custody incomplete")
    events = live.read_jsonl(attempt / "trial.trajectory.jsonl")
    audit = live.read_json(attempt / "FIXTURE-AUDIT.json")
    executions = [entry for entry in audit if entry["kind"] == "execute"]
    turns = {event["turn"]: event for event in events if event["event"] == "turn"}
    observed = live.trajectory_metrics(events, row, smoke=True)
    evidence = {"correct": None, "status": "unknown", "reason": "boundary_not_reached",
                "terminal_state": observed["terminal_state"], "boundary": observed.get("boundary")}

    def failed_custody(reason):
        return {**evidence, "reason": reason, "instrument_error": True}

    wire = graph["wire"]
    texts = []
    for record in wire:
        captured(attempt, record, "original_request")
        prompt = request_text(attempt, record)
        response = response_text(attempt, record)
        if (record["call_kind"] not in {"summary", "generation"} or not prompt or not response.strip()
                or record["sampling"]["cache_prompt"] is not False
                or record["sampling"]["seed"] != row["sampling_seed"]):
            raise ValueError("incomplete or unbound generation custody")
        texts.append((record, "\n".join(prompt), response))
    scopes = [entry for entry in audit if entry["kind"] == "scope"]
    task_scope = {"task_root": str((attempt / "repl").resolve()), "edit_mode": "none", "read_roots": []}
    if len(scopes) != 1 or scopes[0]["scope"] != task_scope or len(scopes[0]["denied"]) != 4:
        return failed_custody("private_source_confinement_unverified")
    if not observed["boundary_reached"]:
        if events[-1]["turns"] >= BOUNDARY_TURN:
            return failed_custody("assigned_boundary_missing")
        return evidence
    boundary = observed["boundary"]
    tails = [entry for entry in audit if entry["kind"] == "tail"]
    if len(tails) != 1 or tails[0].get("turn") != BOUNDARY_TURN:
        return failed_custody("boundary_generation_tail_observation_missing")
    if tails[0]["scope"] != task_scope:
        return failed_custody("private_source_confinement_unverified")
    if (tails[0]["boundaries"] != [BOUNDARY_TURN] or tails[0]["turns"] != [2]
            or tails[0]["has_needle"] is not False):
        return failed_custody("needle_eviction_from_native_tail_unverified")

    before = [entry for entry in executions if entry["turn"] < BOUNDARY_TURN]
    expected = [(RECORD_CODE, record_output(case)), (CHECKPOINT_CODE, checkpoint_output(case))]
    if [entry["turn"] for entry in before] != [1, 2] or any(
        entry["code"].strip() != code or entry["output_sha256"] != sha(output)
        or entry["output_chars"] != len(output) or entry["needle_occurrences"] != (index == 0)
        or entry["error"] or entry["is_final"] or entry["emitted"] != 1 or entry["record_available"]
        or entry["user_globals"] or entry["repl_context_has_needle"] or entry["state_context_has_needle"]
        or entry["repl_artifacts_have_needle"]
        or turns.get(entry["turn"], {}).get("code_sha256") != sha(entry["code"])
        for index, (entry, (code, output)) in enumerate(zip(before, expected, strict=True))
    ):
        return failed_custody("fixture_or_persistent_state_unverified")

    early = [(record, text) for record, text, _ in texts
             if record["call_kind"] == "generation" and record["graph_turn"] < BOUNDARY_TURN]
    if ([record["graph_turn"] for record, _ in early] != [1, 2]
            or any(record["history_boundaries"] for record, _ in early)
            or needle in early[0][1] or needle not in early[1][1]):
        return failed_custody("initial_needle_exposure_unverified")

    continuations = [(record, text) for record, text, _ in texts
                     if record["call_kind"] == "generation" and record["graph_turn"] >= BOUNDARY_TURN]
    if (not continuations or continuations[0][0]["graph_turn"] != BOUNDARY_TURN
            or len({record["graph_turn"] for record, _ in continuations}) != len(continuations)
            or any(record["history_boundaries"] != [BOUNDARY_TURN] for record, _ in continuations)
            or not turns.get(BOUNDARY_TURN, {}).get("prompt_tokens")):
        return failed_custody("continuation_not_observed")

    summary = ""
    summaries = [(record, text, response) for record, text, response in texts if record["call_kind"] == "summary"]
    if row["arm"] == "pointer_only":
        if summaries or boundary["summary_tokens"] != 0:
            return failed_custody("unexpected_summary")
    else:
        if (len(summaries) != 1 or summaries[0][0]["graph_turn"] != BOUNDARY_TURN
                or boundary["summary_tokens"] <= 0 or summaries[0][1].count(needle) != 1):
            return failed_custody("summary_generation_unverified")
        summary = summaries[0][2]

    first_prompt = continuations[0][1]
    # Remove the generated summary itself from the actual request. A summary
    # retaining the exact value is a valid recovery path for arms 1 and 2.
    if summary and first_prompt.count(summary) != 1:
        return failed_custody("generated_summary_not_delivered")
    raw_prompt = first_prompt.replace(summary, "", 1) if summary else first_prompt
    if needle in raw_prompt or "[Turn 1 role=" in raw_prompt or "[Turn 2 role=" not in raw_prompt:
        return failed_custody("needle_eviction_from_raw_tail_unverified")

    logs = list(attempt.rglob("session.verbatim.md"))
    if len(logs) != 1 or record_output(case) not in logs[0].read_text():
        return failed_custody("native_verbatim_log_unverified")
    log = logs[0].resolve()
    pointer = 'Full log: peek(' in raw_prompt and f'file_path="{log}"' in raw_prompt
    if pointer != (row["arm"] != "summary_only"):
        return failed_custody("assigned_log_pointer_unverified")

    final_entries = [entry for entry in executions if entry["is_final"]]
    generation_by_turn = {record["graph_turn"]: response for record, _, response in texts
                          if record["call_kind"] == "generation"}
    submitted = (len(final_entries) == 1 and final_entries[0]["turn"] >= BOUNDARY_TURN
                 and turns.get(final_entries[0]["turn"], {}).get("outcome") == "final"
                 and turns[final_entries[0]["turn"]]["code_sha256"] == sha(final_entries[0]["code"])
                 and "FINAL(" in final_entries[0]["code"]
                 and final_entries[0]["code"].strip() in generation_by_turn.get(final_entries[0]["turn"], ""))
    final_turn = final_entries[0]["turn"] if submitted else events[-1]["turns"]
    reads = [entry for entry in audit if entry["kind"] == "registered_read"
             and BOUNDARY_TURN <= entry["turn"] <= final_turn and entry["needle_returned"]]
    if any(Path(entry["path"]).resolve() != log for entry in reads):
        return failed_custody("alternate_needle_source_read")
    log_read_turns = sorted({entry["turn"] for entry in reads
                             if any(Path(follow["path"]).resolve() == log for follow in
                                    turns.get(entry["turn"], {}).get("log_follows", []))})
    exact = bool(submitted and graph["success"] and final_entries[0]["final_answer"] == needle
                 and graph["answer"] == needle)
    if exact and needle not in summary and not log_read_turns:
        return failed_custody("exact_answer_without_observed_recovery_source")
    # A complete HTTP/SSE transcript can still contain a capped generation.
    if any(_generation_hit_token_limit(attempt, record) for record in wire):
        return {**evidence, "reason": "generation_token_limit_reached"}
    return {**evidence, "correct": exact, "status": "observed", "reason": None,
            "summary_has_needle": needle in summary, "log_read_turns": log_read_turns,
            "final_submission_observed": bool(submitted), "final_turn": final_turn,
            "raw_tail_needle_absent": True, "verbatim_log": str(log),
            "summary_request": summaries[0][0]["request_file"] if summaries else None,
            "continuation_request": continuations[0][0]["request_file"]}
