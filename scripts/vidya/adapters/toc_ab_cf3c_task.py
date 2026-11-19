"""Strict task-native profile of the existing TOC projection; no grading ladder.

Replay only the allowlisted, sealed finite environment, never policy/runner code or
inference. Policy semantics remain source-pinned; native activation, histories,
rendering, actions and oracle receipts are checked against the exact sealed bytes.
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

from adapters import toc_ab_cf3c as cf

SCHEMA = "epyc.cf3c.task.native.v1"
POLICY = "f3113461a3437c1b72077602fb60c349a11de667aa6a5a1d011422698d1f80a7"
ENVIRONMENT = "56f18917e00b650068a298422e48c38daf429475e5efdcd0a4cd134c94d4ada4"
ARMS = ("A0", "A1-k4", "A1-k8", "A1-k12", "A2", "A3")
OBSERVED = {"graded", "abstained", "NA"}


def _require(condition, message):
    if not condition:
        cf._refuse(f"task-level {message}")


def _environment(packet):
    # Exact source digest is allowlisted above and checked before execution. A
    # transient module supports dataclasses without altering imports permanently.
    name = "_vidya_cf3c_sealed_environment"
    module = types.ModuleType(name)
    previous = sys.modules.get(name)
    sys.modules[name] = module
    try:
        exec(compile((packet / "environment.py").read_bytes(), str(packet / "environment.py"), "exec"),
             module.__dict__)
        return module
    finally:
        if previous is None:
            del sys.modules[name]
        else:
            sys.modules[name] = previous


def _occurrences(messages, value):
    return [{"message": i, "field": key, "count": count}
            for i, m in enumerate(messages) for key, data in m.items()
            if (count := json.dumps(data, ensure_ascii=False).count(value))]


def _turns(folder, cell, case, environment, limits):
    service = environment.OrderService(**{k: case[k] for k in
        ("order", "desk", "receipt", "challenge", "confirmation")})
    turns = cell.get("turns")
    _require(isinstance(turns, list) and len(turns) <= limits["generation_turns"], "invalid turns")
    history, witnesses, usage = None, [], []
    terminal = None
    requests_started = 0
    actions = 0
    for number, turn in enumerate(turns, 1):
        prefix = f"turn-{number:02d}"
        evidence = cell["evidence_sha256"]

        def has(name):
            return f"{prefix}/{name}" in evidence

        def load(name):
            _require(has(name), f"missing {prefix}/{name}")
            return cf._load(folder / prefix / name)

        _require(terminal is None, "turn after terminal")
        preflight = load("PREFLIGHT.json")
        _require(preflight == {k: v for k, v in turn.items()
                              if k not in ("usage", "finish_reason", "tool_events")},
                 "turn disagrees with preflight")
        _require(turn.get("turn") == number, "turn order")
        original = load("original-messages.json")
        request = load("template.request.body")
        selected = request.get("messages")
        policy = turn.get("policy", {})
        _require(isinstance(original, list) and isinstance(selected, list)
                 and len(original) == len(selected) and len(original) >= 23
                 and all(isinstance(m, dict) for m in original + selected), "invalid histories")
        if history is not None:
            _require(original == history, "continuation history disagrees with executed actions")
        _require(policy.get("arm") == cell["arm"], "policy arm")
        for key, role in (("changed_observations", "tool"), ("changed_assistant_entries", "assistant")):
            changed = [i for i, (a, b) in enumerate(zip(original, selected))
                       if a.get("role") == role and a != b]
            _require(policy.get(key) == changed, "activation changed-index receipt")
        active = original != selected
        _require(policy.get("active") is active and active == (cell["arm"] != "A0"), "activation state")
        _require(policy.get("pairs_fixed") == 0 and policy.get("compaction_model_calls") == 0,
                 "tool-pair/model-call custody")
        for before, after in zip(original, selected):
            fields = ("content",) if before["role"] == "tool" else (
                ("content", "reasoning_content") if before["role"] == "assistant" else ())
            _require({k: v for k, v in before.items() if k not in fields}
                     == {k: v for k, v in after.items() if k not in fields}, "protected history fields")
        if cell["arm"].startswith("A1-"):
            _require(policy.get("production_threshold") == int(cell["arm"].split("-k")[1])
                     and policy.get("production_stubbed") == len(policy["changed_observations"])
                     and policy["production_stubbed"] >= 6, "active threshold witness")
        expected = (cell["arm"] != "A3" if case["location"] == "assistant-reasoning" else
                    cell["arm"] in (("A0", "A2", "A3") if case["location"] == "tool-head" else ("A0", "A3")))
        index = 2 * case["desk"] + (case["location"] != "assistant-reasoning")
        field = "reasoning_content" if case["location"] == "assistant-reasoning" else "content"
        placement = [{"message": index, "field": field, "count": 1}]
        _require(_occurrences(original[:23], case["receipt"]) == placement, "original receipt placement")
        occurrences = _occurrences(selected, case["receipt"])
        _require([o for o in occurrences if o["message"] < 23] == (placement if expected else [])
                 and turn.get("archive_receipt_exposed") is expected
                 and turn.get("receipt_occurrences") == occurrences, "receipt exposure witness")
        prompt = load("template.response.body").get("prompt")
        _require(isinstance(prompt, str), "invalid rendered prompt")
        markers = [case["receipt"]] + [f"Archive{kind}{desk:02d}"
                   for desk in range(1, 11) for kind in ("Head", "Tail", "Thinking")]
        _require(all(prompt.count(marker) == sum(o["count"] for o in _occurrences(selected, marker))
                     for marker in markers), "native-rendered exposure")
        tokens = load("tokenize.response.body").get("tokens")
        _require(load("tokenize.request.body").get("content") == prompt
                 and isinstance(tokens, list) and tokens and all(type(t) is int for t in tokens)
                 and turn.get("native_prompt_tokens") == len(tokens), "native tokenization")
        _require(request.get("tools") == environment.TOOLS
                 and request.get("seed") == (cell["seed"] + number - 1) % (2**31)
                 and request.get("max_tokens") == limits["decode_tokens_per_turn"]
                 and request.get("chat_template_kwargs") == {"enable_thinking": False, "preserve_reasoning": True},
                 "native request custody")
        witnesses.append({"preflight": preflight, "evidence_sha256": {
            k: v for k, v in evidence.items() if k.startswith(prefix + "/")}})
        if has("completion.request.body"):
            requests_started += 1
            _require(load("completion.request.body") == request, "generation request differs from template")
        if "usage" not in turn:
            _require(not turn.get("tool_events") and number == len(turns),
                     "unobserved generation executed tools or continued")
            continue
        _require(has("completion.request.body"), "usage without request")
        reply = load("completion.response.body")
        _require(reply.get("usage") == turn["usage"] and len(reply.get("choices", [])) == 1,
                 "native completion usage/choice")
        u = turn["usage"]
        _require(all(cf.ns.nonneg_int(u.get(k)) for k in ("prompt_tokens", "completion_tokens", "total_tokens"))
                 and u["prompt_tokens"] == len(tokens)
                 and u["completion_tokens"] <= limits["decode_tokens_per_turn"]
                 and u["total_tokens"] == u["prompt_tokens"] + u["completion_tokens"], "token accounting")
        usage.append(u)
        choice = reply["choices"][0]
        finish, message = choice.get("finish_reason"), choice.get("message", {})
        _require(finish == turn.get("finish_reason") and finish in ("stop", "length", "tool_calls")
                 and message.get("role") == "assistant" and reply.get("model") == request.get("model"), "finish state")
        if finish == "stop":
            terminal = service.score(message.get("content"))
        elif finish == "length" or number == limits["generation_turns"]:
            terminal = {"status": "NA", "correct": False, "answer": None, "non_termination": 1,
                        "finish_reason": "decode_cap" if finish == "length" else "turn_cap"}
        else:
            calls = message.get("tool_calls")
            _require(isinstance(calls, list) and calls, "missing tool calls")
            observations, events = service.execute(calls)
            action = load("ACTION.json")
            _require(action == {"observations": observations, "tool_events": events}
                     and turn.get("tool_events") == events, "executed tool outputs/events")
            actions += len(events)
            history = original + [message, *observations]
    if terminal is not None:
        _require(all(cell.get(k) == v for k, v in terminal.items()), "task success oracle")
    elif cell["status"] in OBSERVED:
        _require(cell["status"] == "NA" and cell.get("correct") is False
                 and cell.get("finish_reason") in ("context_budget", "task_wall_budget")
                 and cell.get("non_termination") == 1 and cell.get("answer") is None,
                 "observed outcome without terminal oracle")
    _require(cell.get("inspected") is service.inspected and cell.get("released") is service.released
             and cell.get("live_tools_executed") == actions, "environment state")
    total = {k: sum(u[k] for u in usage) for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
    _require(cell.get("observed_usage") == total and cell.get("generation_turns") == len(usage)
             and cell.get("generation_requests_started") == requests_started
             and cell.get("usage_complete") is (requests_started == len(usage)), "cumulative usage")
    return witnesses


def read_unit(path: Path, result: dict) -> dict:
    _require(result.get("server_exited") is True and result.get("diagnostic_only") is True
             and result.get("category") in cf.ns.CATEGORIES, "result custody")
    window = cf._window(path, result)
    cf._verify_seal(window, result.get("window_sha256"))
    w = cf._load(window / "WINDOW.json")
    _require(w.get("schema") == SCHEMA and w.get("smoke") is False
             and w.get("grant") == "cf3c-task-level-20261118", "producer/smoke profile")
    packet = path.parent.parent / "packet"
    _require(cf._sha(packet / "inputs.json") == result.get("packet_sha256"), "packet digest")
    inputs = cf._load(packet / "inputs.json")
    _require(inputs == w.get("inputs") and inputs.get("source") == w.get("source") == result.get("source")
             and w.get("packet_sha256") == result["packet_sha256"], "source/input custody")
    pins = inputs.get("packet_sha256", {})
    cf._verify_seal(packet, {**pins, "inputs.json": result["packet_sha256"]})
    _require(pins.get("policies.py") == POLICY and pins.get("environment.py") == ENVIRONMENT
             and pins.get("protocol.md"), "unrecognized policy/environment")
    cases = cf._load(packet / "cases.json")
    _require([(c["id"], c["location"]) for c in cases] == [
        ("archive-tail", "tool-tail"), ("archive-head", "tool-head"),
        ("archive-reasoning", "assistant-reasoning")], "finite environment inventory")
    schedule = []
    for i, case in enumerate(cases):
        for arm in ARMS[i:] + ARMS[:i]:
            schedule.append(dict(case=case["id"], arm=arm, seed=case["seed"],
                unit=f"{case['id']}/{arm}", ordinal=len(schedule), render_only=False))
    _require(w.get("schedule") == schedule and result.get("scheduled") == len(schedule), "paired schedule")
    environment = _environment(packet)
    cells, witnesses = [], {}
    paired = result.get("paired", {})
    for entry in schedule:
        prefix = f"task-{entry['ordinal']:02d}"
        rel = prefix + "/TRAJECTORY.json"
        native = paired.get(entry["case"], {}).get("arms", {}).get(entry["arm"])
        _require(paired.get(entry["case"], {}).get("seed") == entry["seed"], "paired seed")
        identity = {k: v for k, v in entry.items() if k != "render_only"}
        if rel not in result["window_sha256"]:
            _require(native == {**identity, "status": "unattempted", "correct": None}, "unattempted marker")
            cells.append(native)
            continue
        cell = cf._load(window / rel)
        _require(all(cell.get(k) == v for k, v in identity.items()) and cell == native,
                 "trajectory/schedule/paired identity")
        _require(all(cell.get(k) == result.get(k) for k in ("schema", "category", "source", "packet_sha256"))
                 and cell.get("status") in OBSERVED | {"UNKNOWN"}, "trajectory custody/status")
        _require(cf.ns.finite(cell.get("wall_s")) and cell["wall_s"] >= 0, "wall time")
        if cell["status"] == "UNKNOWN":
            _require(cell.get("correct") is None, "UNKNOWN carries verdict")
        ev = cell.get("evidence_sha256")
        _require(isinstance(ev, dict) and all(result["window_sha256"].get(f"{prefix}/{k}") == v
                                            for k, v in ev.items()), "unsealed evidence")
        _require(set(ev) == {k[len(prefix)+1:] for k in result["window_sha256"]
                            if k.startswith(prefix + "/") and k != rel}, "incomplete evidence map")
        case = next(c for c in cases if c["id"] == cell["case"])
        witnesses[cell["unit"]] = _turns(window / prefix, cell, case, environment, w["limits"])
        cells.append(cell)
    _require(sum(len(p.get("arms", {})) for p in paired.values()) == len(schedule), "extra paired cells")
    recorded = sum(c["status"] != "unattempted" for c in cells)
    completed = sum(c["status"] in OBSERVED for c in cells)
    _require(result.get("recorded") == recorded and result.get("completed") == completed
             and result.get("coverage_complete") is (recorded == len(schedule)), "coverage counts")
    derived = {}
    _require(set(result.get("arms", {})) == set(ARMS), "summary arms")
    for arm in ARMS:
        group = [c for c in cells if c["arm"] == arm]
        attempted = [c for c in group if c["status"] != "unattempted"]
        observed = [c for c in attempted if c["status"] in OBSERVED]
        complete = [c for c in observed if c["usage_complete"]]
        incomplete = [c for c in observed if not c["usage_complete"]]
        correct = sum(c["correct"] is True for c in observed)
        summary = dict(scheduled=len(group), attempted=len(attempted), observed=len(observed), correct=correct,
            accuracy_over_observed=correct / len(observed) if observed else None,
            non_termination=sum(c["non_termination"] == 1 for c in observed),
            complete_cost_tasks=len(complete), incomplete_cost_tasks=len(incomplete),
            incomplete_token_lower_bound_total=sum(c["observed_usage"]["total_tokens"] for c in incomplete),
            mean_live_tokens_per_complete_cost_task=(sum(c["observed_usage"]["total_tokens"] for c in complete)
                                                    / len(complete) if complete else None),
            mean_live_wall_s_per_observed_task=sum(c["wall_s"] for c in observed) / len(observed) if observed else None,
            **{s: sum(c["status"] == s for c in attempted) for s in ("graded", "abstained", "NA", "UNKNOWN")})
        _require(set(result["arms"][arm]) == set(summary) and all(
            cf._close(result["arms"][arm][k], v) for k, v in summary.items()), "summary does not re-derive")
        # Generic TOC cost means use only the producer's observed, complete-cost
        # cohort. UNKNOWN costs remain retained below as lower bounds, not means.
        projected = [{**c, "usage": c["observed_usage"] if c in complete else None,
                      "wall_s": c.get("wall_s") if c in observed else None} for c in group]
        d = cf._derive(projected)[arm]
        d["cost_accounting"] = {**summary, "all_attempted_token_lower_bound_total":
            sum(c["observed_usage"]["total_tokens"] for c in attempted),
            "incomplete_attempted_tasks": sum(not c["usage_complete"] for c in attempted)}
        derived[arm] = d
    delta_cells = [{**c, "usage": c.get("observed_usage") if c.get("usage_complete") else None} for c in cells]
    return dict(result_path=str(path), result_sha256=cf._sha(path), result=result, window=str(window),
        cells=cells, derived=derived, activation_witnesses=witnesses, paired_deltas=cf._deltas(delta_cells),
        scope=cf._scope(window, inputs, w.get("argv")), profile=dict(producer="cf3c-task-level",
            label="finite multi-turn task-environment diagnostics", packet_sha256=pins,
            interpretation="seeded historical prefix; not production trajectories; no one-point adoption test"))
