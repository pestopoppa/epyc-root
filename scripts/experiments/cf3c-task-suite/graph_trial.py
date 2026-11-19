"""CF-3c trial subprocess using the pinned graph and its structured history renderer."""

import asyncio
import hashlib
import json
import os
import sys
from collections import Counter
from contextlib import ExitStack
from contextvars import ContextVar
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from binding import install_archive
from cmp4_graph_trial import wire_hooks
from prepare import ARMS, CONTEXT_TOKENS, MAX_COMPLETION_TOKENS, MAX_TURNS, PORT, SOURCE

ENDPOINT = f"http://127.0.0.1:{PORT}"
TEMPERATURE = 0.3
LATEST = 3
MASK_CHARS = 180


def history_projection(turns, arm):
    """Adapt the source turn records to the compressor's paired message contract."""
    from src.context_compression import CompressorConfig, ContextCompressor
    from src.repl_environment.types import TOOL_OUTPUT_END, TOOL_OUTPUT_START

    if arm not in ARMS:
        raise ValueError(f"unknown CF-3c arm: {arm}")
    outputs = [turn["output"] for turn in turns]
    actions = [i for i, turn in enumerate(turns) if turn["code"] or turn["output"]]
    reason = "control" if arm == "A0" else "no_eligible_observation_changed"
    threshold = None
    if arm.startswith("A1-"):
        threshold = int(arm.split("-k")[1])
        # The initial system and task instruction precede all executed turns.
        # These anchors represent their protected positions and are never rendered.
        messages = [{"role": "system", "content": ""}, {"role": "user", "content": ""}]
        tool_indexes = {}
        for i, turn in enumerate(turns):
            message = {"role": "assistant", "content": turn["code"]}
            messages.append(message)
            if i not in actions:
                continue
            call_id = f"repl-{i}"
            message["tool_calls"] = [{"id": call_id}]
            output = outputs[i]
            # Classify the actual REPL observation as REPL, or as an error when
            # the graph recorded a separate error. These markers never go on wire.
            content = f"{TOOL_OUTPUT_START}\n{output}\n{TOOL_OUTPUT_END}"
            if turn["error"]:
                content += "\nError: " + turn["error"]
            tool_indexes[i] = len(messages)
            messages.append(
                {"role": "tool", "tool_call_id": call_id, "content": content}
            )
        selected = ContextCompressor(
            CompressorConfig(tool_output_age_threshold=threshold)
        ).compress(messages)
        if selected.tool_pairs_fixed or len(selected.messages) != len(messages):
            raise ValueError("REPL projection changed tool pair custody")
        for i, index in tool_indexes.items():
            before, after = messages[index], selected.messages[index]
            if outputs[i] and after["content"] != before["content"]:
                outputs[i] = after["content"]
    elif arm == "A2":
        for i in actions[:-LATEST]:
            if len(outputs[i]) > MASK_CHARS:
                outputs[i] = outputs[i][:MASK_CHARS] + "\n[Older observation truncated]"
    elif arm == "A3":
        # record_turn() stores executed code, stdout and error, with no reasoning
        # field. Code may contain useful comments and must survive this control.
        reason = "historical_reasoning_absent_from_graph_projection"
    changed = [
        turn["turn"]
        for turn, output in zip(turns, outputs, strict=True)
        if output != turn["output"]
    ]
    projected = [
        {**turn, "output": output} for turn, output in zip(turns, outputs, strict=True)
    ]
    return projected, {
        "active": bool(changed),
        "inactive_reason": None if changed else reason,
        "changed_observation_turns": changed,
        "archived_actions": len(actions),
        "production_threshold": threshold,
        "production_stubbed": len(changed) if threshold is not None else 0,
        "reasoning_carrier": False,
    }


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def policy_receipt(fields, primary_attempt):
    receipt = {**fields, "primary_attempt": primary_attempt}
    receipt["selected_history_sha256"] = sha(receipt.pop("block"))
    return receipt


def primary_call_key(record):
    turn, attempt = record.get("graph_turn"), record.get("primary_attempt")
    if type(turn) is not int or turn < 1 or type(attempt) is not int or attempt < 1:
        raise ValueError("native primary request lacks a valid attempt label")
    return turn, attempt


def validate_primary_calls(wire, prompts):
    receipts = {}
    for record in wire:
        if record["call_kind"] == "graph_turn":
            key = primary_call_key(record)
            receipt = record["policy_receipt"]
            if (
                key in receipts
                or key not in prompts
                or receipt != policy_receipt(prompts[key], key[1])
            ):
                raise ValueError("native graph generations and render custody disagree")
            receipts[key] = receipt
    if receipts.keys() != prompts.keys():
        raise ValueError("native graph generations and render custody disagree")
    return list(receipts.values())


class HistoryRenderer:
    """Project the current view while leaving the graph's record and full log intact."""

    def __init__(self, native_render, arm):
        self.native_render = native_render
        self.arm = arm
        self.latest = None

    def __call__(self, state, repl=None, count_tokens=None):
        original = state.history_turns
        projected, policy = history_projection(original, self.arm)
        state.history_turns = projected
        try:
            block = self.native_render(state, repl, count_tokens)
        finally:
            state.history_turns = original
        self.latest = {"turn": state.turns, "block": block, **policy}
        return block


def validate_private_request(request):
    if (request.url.scheme, request.url.host, request.url.port) != (
        "http",
        "127.0.0.1",
        PORT,
    ):
        raise ValueError(f"model request escaped private endpoint: {request.url.host}")


def install_trial_scope(attempt):
    from src.repl_environment.task_root import begin_request_scope

    workspace = attempt / "workspace"
    artifacts = attempt / "repl-artifacts"
    workspace.mkdir(mode=0o700)
    artifacts.mkdir(mode=0o700)
    return begin_request_scope(str(workspace), read_roots=[str(artifacts)])


def guarded_wire_hooks(attempt, seed, failures, wire, call_context, prompts):
    capture_request, capture_response = wire_hooks(
        attempt, seed, failures, wire, request_context=call_context
    )

    def note_request(request):
        try:
            validate_private_request(request)
            if request.url.path in {"/completion", "/v1/chat/completions"}:
                call = call_context.get()
                if call is None or call.get("call_kind") not in {
                    "graph_turn",
                    "repl_helper",
                }:
                    raise ValueError("generation escaped attributed graph primitive")
                capture_request(request)
                body = json.loads(request.content)
                limit = body.get("max_tokens", body.get("n_predict"))
                if type(limit) is not int or not 0 < limit <= MAX_COMPLETION_TOKENS:
                    raise ValueError(
                        "native request exceeded its registered completion cap"
                    )
                if call["call_kind"] == "graph_turn":
                    from src.security.control_tokens import neutralise_control_tokens

                    selected = neutralise_control_tokens(
                        prompts[primary_call_key(call)]["block"]
                    )
                    messages = body.get("messages") or []
                    candidates = [body.get("prompt")] + [
                        m.get("content") for m in messages
                    ]
                    if not selected or any(
                        isinstance(text, str) and selected in text
                        for text in candidates
                    ):
                        return
                    # The pinned chat adapter strips outer user-content whitespace.
                    # A history block at the end of the prompt loses its final newline.
                    trimmed = selected.rstrip()
                    if (
                        request.url.path != "/v1/chat/completions"
                        or not trimmed
                        or not any(
                            m.get("role") == "user"
                            and isinstance(m.get("content"), str)
                            and m["content"].endswith("\n\n" + trimmed)
                            for m in messages
                        )
                    ):
                        raise ValueError("selected history missing from native request")
        except (ValueError, KeyError, TypeError) as exc:
            failures.append(str(exc))
            raise

    return note_request, capture_response


def read_wire(folder):
    return [
        json.loads(path.read_text())
        for path in sorted(folder.glob("wire/*/record.json"))
    ]


def completed_wire(folder, record):
    status = record.get("http_status")
    streaming = record["stream_requested"]
    if (
        type(status) is not int
        or not 200 <= status < 300
        or "request_error" in record
        or "response_error" in record
    ):
        raise ValueError("incomplete or failed native generation exchange")
    for field in ("original_request", "request", "response"):
        path = folder / record[f"{field}_file"]
        if not path.resolve().is_relative_to(folder.resolve()):
            raise ValueError("native exchange path escaped trial custody")
        if hashlib.sha256(path.read_bytes()).hexdigest() != record[f"{field}_sha256"]:
            raise ValueError("native exchange digest mismatch")
    usage = native_usage((folder / record["response_file"]).read_text(), streaming)
    if streaming and record["endpoint"] == "/completion":
        # The pinned raw backend exits at the server's stop frame, before EOF.
        complete = usage["native_stop"]
    else:
        complete = (
            record.get("response_sse_done")
            if streaming
            else record.get("response_complete")
        )
    if complete is not True or not usage["finish_reason"]:
        raise ValueError("native generation is missing its endpoint's terminal frame")
    return {**usage, "exchange_complete": True}


def native_usage(raw, streaming):
    """Read only server-reported counters, retaining nullable usage fields."""
    values = {
        "prompt_tokens": None,
        "completion_tokens": None,
        "cached_prompt_tokens": None,
        "finish_reason": None,
        "native_stop": False,
    }
    payloads = (
        (
            json.loads(line[6:])
            for line in raw.splitlines()
            if line.startswith("data: ") and line != "data: [DONE]"
        )
        if streaming
        else (json.loads(raw),)
    )
    for payload in payloads:
        usage = payload.get("usage") or {}
        details = usage.get("prompt_tokens_details") or {}
        timings = payload.get("timings") or {}
        for key, value in (
            (
                "prompt_tokens",
                usage.get("prompt_tokens", payload.get("tokens_evaluated")),
            ),
            (
                "completion_tokens",
                usage.get("completion_tokens", payload.get("tokens_predicted")),
            ),
            (
                "cached_prompt_tokens",
                details.get("cached_tokens", timings.get("cache_n")),
            ),
        ):
            if type(value) is int and value >= 0:
                values[key] = value
        if payload.get("stop") is True:
            values["native_stop"] = True
        finish = payload.get("stop_type") or payload.get("finish_reason")
        if not finish and payload.get("stop") is True:
            finish = "stop"
        for choice in payload.get("choices", ()):
            finish = choice.get("finish_reason") or finish
        if isinstance(finish, str) and finish:
            values["finish_reason"] = finish
    return values


def partial_wire_usage(folder, record):
    """Recover fully received SSE frames from a canceled call's captured prefix."""
    if record.get("stream_requested") is not True or record.get("http_status") != 200:
        return None
    path = folder / record.get("response_file", "")
    if not path.is_file() or not path.resolve().is_relative_to(folder.resolve()):
        return None
    prefix = path.read_bytes().rpartition(b"\n")[0].decode()
    return {**native_usage(prefix, streaming=True), "exchange_complete": False}


def run_trial(attempt):
    config = json.loads((attempt / "INPUT.json").read_text())
    if config["endpoint"] != ENDPOINT or config["source"] != str(SOURCE):
        raise ValueError("private endpoint or source path mismatch")
    sys.path[:0] = [str(SOURCE), str(SOURCE / "scripts/benchmark")]
    from src.features import Features, set_features

    set_features(
        Features(
            context_arm_ab=True,
            session_log=True,
            session_log_verbatim=True,
            output_spill_to_file=True,
            trajectory_artifact=True,
            accurate_token_counting=True,
            model_fallback=False,
        )
    )
    from src.autopilot_core.measurement_guards import infra_failure_reason
    from src.graph import context_arm_ab, trajectory_artifact
    from src.graph.graph import run_task
    from src.graph.state import GraphConfig, TaskDeps, TaskState
    from src.llm_primitives import LLMPrimitives
    from src.pipeline_monitor.anomaly import detect_assistant_help_request
    from src.registry.registry_loader import RegistryLoader
    from src.repl_environment.environment import REPLEnvironment
    from src.repl_environment.task_root import clear_request_scope

    if context_arm_ab.settings() != ("full_history", CONTEXT_TOKENS, 0.5, set()):
        raise ValueError("native history base is not the frozen full-history render")
    row = config["row"]
    renderer = HistoryRenderer(context_arm_ab.render, row["arm"])
    failures, wire, prompts = [], [], {}
    primary_counts = Counter()
    call_context = ContextVar("cf3c_graph_call", default=None)
    roles = {"frontdoor", "worker", "worker_general", "worker_summarize"}
    prompt, context = config["prompt"], config.get("context")
    context = prompt + ("\n\nContext:\n" + context if context else "")
    state = TaskState(
        task_id="trial", prompt=prompt, context=context, max_turns=MAX_TURNS
    )

    class PrivatePrimitives(LLMPrimitives):
        def llm_call(self, prompt, context_slice="", role="worker", **kwargs):
            if str(role) not in roles:
                raise PermissionError(f"unbound experiment role: {role}")
            parent = call_context.get()
            primary = (
                str(role) == "frontdoor"
                and parent is None
                and kwargs.get("skip_suffix") is True
            )
            label = {
                "call_kind": "repl_helper",
                "graph_turn": state.turns,
                "role": str(role),
            }
            if primary:
                if renderer.latest is None or renderer.latest["turn"] != state.turns:
                    failures.append("graph generation lacks timely render receipt")
                    raise ValueError(failures[-1])
                primary_counts[state.turns] += 1
                primary_attempt = primary_counts[state.turns]
                prompts[state.turns, primary_attempt] = renderer.latest
                label.update(
                    call_kind="graph_turn",
                    primary_attempt=primary_attempt,
                    policy_receipt=policy_receipt(renderer.latest, primary_attempt),
                )
            requested = kwargs.get("n_tokens")
            cap = (
                min(requested, MAX_COMPLETION_TOKENS)
                if type(requested) is int and requested > 0
                else MAX_COMPLETION_TOKENS
            )
            kwargs.update(seed=row["seed"], temperature=TEMPERATURE, n_tokens=cap)
            token = call_context.set(label)
            try:
                return super().llm_call(prompt, context_slice, role=role, **kwargs)
            except Exception as exc:
                failures.append(f"{role} generation: {type(exc).__name__}")
                raise
            finally:
                call_context.reset(token)

        def chat_completion_call(self, messages, *, role, **kwargs):
            raise PermissionError(
                f"independent chat primitive unavailable in this graph: {role}"
            )

        def llm_batch(self, prompts, role="worker", **kwargs):
            # Route model-selected REPL batches through the same seeded, capped private call.
            return [self.llm_call(prompt, role=role, **kwargs) for prompt in prompts]

    primitives = PrivatePrimitives(
        mock_mode=False,
        registry=RegistryLoader(
            SOURCE / "orchestration/model_registry.yaml", validate_paths=False
        ),
        server_urls={role: ENDPOINT for role in sorted(roles)},
        server_urls_source="request",
        num_slots=4,
    )
    tokenizer = primitives._tokenizer
    if tokenizer is None or set(primitives._backends) != roles:
        raise ValueError("served tokenizer or private role bindings missing")
    clients = {primitives._backends[role].backend.client for role in roles}
    key = os.environ["CF3C_SUITE_API_KEY"]
    note_request, note_response = guarded_wire_hooks(
        attempt, row["seed"], failures, wire, call_context, prompts
    )
    try:
        for client in clients:
            client.headers.update(
                {"Authorization": f"Bearer {key}", "Accept-Encoding": "identity"}
            )
            client.event_hooks["request"].append(note_request)
            client.event_hooks["response"].append(note_response)
        tokenizer._client.headers["Authorization"] = f"Bearer {key}"
        tokenizer._client.event_hooks["request"].append(validate_private_request)
        install_trial_scope(attempt)
        try:
            with ExitStack() as captures:
                recovery_capture = None
                if config.get("recovery_probe_v1"):
                    from recovery_probe import capture_peeks
                    recovery_capture = captures.enter_context(
                        capture_peeks(REPLEnvironment, config["initial_history"]))
                repl = REPLEnvironment(
                    context,
                    llm_primitives=primitives,
                    role="frontdoor",
                    task_id="trial",
                    tool_context={"no_web": True},
                )
                archive_receipt = None
                if "initial_history" in config:
                    archive_receipt = install_archive(
                        state, repl, config["initial_history"]
                    )
                if recovery_capture is not None:
                    recovery_capture["log_path"] = state.history_log_path
                with patch.object(context_arm_ab, "render", renderer):
                    result = asyncio.run(
                        run_task(
                            state,
                            TaskDeps(
                                primitives=primitives,
                                repl=repl,
                                config=GraphConfig(max_escalations=0, max_turns=MAX_TURNS),
                            ),
                        )
                    )
        finally:
            clear_request_scope()
        events = trajectory_artifact.read_events(attempt / "trial.trajectory.jsonl")
        final = events[-1]
        if (
            sum(e["event"] == "final" for e in events) != 1
            or final["event"] != "final"
            or final["turns"] != state.turns
            or final["solved"] is not result.success
            or final["arm"] != "full_history"
            or final["history_valid"] is not True
        ):
            raise ValueError("invalid native terminal trajectory")
        pregen = (
            not wire
            and state.turns == 1
            and state.history_context_exhausted
            and (state.artifacts.get("_context_budget_exhausted") is True)
            and final["terminal_state"] == "context-exhausted"
        )
        if (
            failures
            or (not wire and not pregen)
            or tokenizer.fallback_count
            or not tokenizer.total_calls
        ):
            raise ValueError(
                f"incomplete graph/tokenizer capture: {failures}, requests={len(wire)}"
            )
        reason = infra_failure_reason(
            error=result.answer if not result.success and not pregen else None
        )
        if reason:
            raise ValueError(f"graph infrastructure failure: {reason}")
        receipts = validate_primary_calls(wire, prompts)
        usage = [completed_wire(attempt, record) for record in wire]
        actual_final = any(
            event["event"] == "turn" and event.get("outcome") == "final"
            for event in events
        )
        suppressed_rescue = (
            result.success and not actual_final and state.turns >= MAX_TURNS
        )
        payload = {
            "answer": result.answer,
            "graph_success": result.success,
            "terminal_state": "turn-exhausted"
            if suppressed_rescue
            else final["terminal_state"],
            "terminal_reason": "graph returned a max-turns rescue"
            if suppressed_rescue
            else final["terminal_reason"],
            "turns": state.turns,
            "role_history": [str(role) for role in state.role_history],
            "give_up_proxy": bool(
                result.success
                and not suppressed_rescue
                and detect_assistant_help_request(result.answer)
            ),
            "pre_generation_budget_exhausted": bool(pregen),
            "policy_receipts": receipts,
            "initial_history_receipt": archive_receipt,
            "recovery_capture": recovery_capture,
            "tool_calls": final["tool_calls"],
            "native_usage": usage,
            "context_counter": tokenizer.get_stats(),
            "wire_requests": len(wire),
        }
        tmp = attempt / "GRAPH.tmp"
        tmp.write_text(json.dumps(payload, indent=2) + "\n")
        tmp.replace(attempt / "GRAPH.json")
    finally:
        for client in clients | {tokenizer._client}:
            client.close()


if __name__ == "__main__":
    run_trial(Path(sys.argv[1]))
