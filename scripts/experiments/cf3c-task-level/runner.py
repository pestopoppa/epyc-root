#!/usr/bin/env python3
"""Run bounded CF-3c tool tasks against an allocator-owned native frontdoor."""

import argparse
import fcntl
import http.client
import json
import math
import os
import re
import secrets
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # Keep the sealed dependencies available under python -I.
import cmp4_runner as live
from environment import TOOLS, OrderService
from prepare import (
    BASE,
    CASE_PLAN,
    COPIED,
    FILES,
    HARNESS_REF,
    SCRATCH,
    SERVING,
    SOURCE,
    WEIGHT_RECEIPT_SHA,
)

ROW = "cf3c-task-level-20261118"
SCHEMA = "epyc.cf3c.task.native.v1"
PORT = 19381
ENDPOINT = f"http://127.0.0.1:{PORT}"
CONTEXT_TOKENS = 12288
TURN_TOKENS = 112
MAX_TURNS = 4
TASK_S = 420
WINDOW_S = 8280
RESULT = SCRATCH / "native/RESULT.json"
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
OBSERVED = ("graded", "abstained", "NA")
TEMPLATE_OPTIONS = {"enable_thinking": False, "preserve_reasoning": True}


class TaskDeadline(Exception):
    """The per-task wall budget was exhausted."""


def pinned_modules():
    def git(*args):
        return subprocess.check_output(
            ["git", "-C", str(SOURCE), *args], text=True
        ).strip()

    if git("rev-parse", "HEAD") != BASE or git(
        "status", "--porcelain", "--untracked-files=all"
    ):
        raise ValueError(
            "detached orchestrator source differs from the registered clean commit"
        )
    sys.path.insert(0, str(SOURCE))
    import policies

    from scripts.benchmark import own_port_proof

    for module in (sys.modules["src.context_compression"], own_port_proof):
        if not Path(module.__file__).resolve().is_relative_to(SOURCE.resolve()):
            raise ValueError(f"dependency escaped pinned source: {module.__name__}")
    return policies, own_port_proof


def matrix(policies, cases):
    if [
        tuple(c[k] for k in ("id", "location", "desk", "order", "seed")) for c in cases
    ] != list(CASE_PLAN):
        raise ValueError("case schedule differs from the registered plan")
    for name, length in (("receipt", 12), ("challenge", 8), ("confirmation", 12)):
        if any(not re.fullmatch(rf"[0-9a-f]{{{length}}}", c[name]) for c in cases):
            raise ValueError(f"invalid sealed case {name}")
    secrets_used = [
        case[name]
        for case in cases
        for name in ("receipt", "challenge", "confirmation")
    ]
    if len(secrets_used) != len(set(secrets_used)) or any(
        value in other
        for value in secrets_used
        for other in secrets_used
        if value != other
    ):
        raise ValueError("sealed case data collide")

    rows = []
    for index, case in enumerate(cases):
        for arm in policies.ARMS[index:] + policies.ARMS[:index]:
            rows.append(
                {
                    "unit": f"{case['id']}/{arm}",
                    "ordinal": len(rows),
                    "case": case["id"],
                    "arm": arm,
                    "seed": case["seed"],
                }
            )
    return rows


def verify():
    inputs = live.read_json(HERE / "inputs.json")
    if (
        inputs["source"] != BASE
        or inputs["cmp4_harness_ref"] != HARNESS_REF
        or inputs["cmp4_weight_receipt_sha256"] != WEIGHT_RECEIPT_SHA
        or set(inputs["packet_sha256"]) != set(FILES + COPIED)
        or live.digest(HERE / "prior-model-receipt.json") != WEIGHT_RECEIPT_SHA
    ):
        raise ValueError("packet or prior serving receipt pin mismatch")
    receipt = live.read_json(HERE / "prior-model-receipt.json")
    if (
        inputs["model_path"] != str(live.MODEL)
        or inputs["model_sha256"] != live.MODEL_SHA
        or inputs["template_sha256"] != live.TEMPLATE_SHA
        or any(inputs[name] != receipt[name] for name in SERVING)
    ):
        raise ValueError("prepared inputs differ from prior verified serving identity")
    live.verify_inputs(inputs)
    policies, owner = pinned_modules()
    cases = live.read_json(HERE / "cases.json")
    rows = matrix(policies, cases)
    for row in rows:
        case = next(case for case in cases if case["id"] == row["case"])
        original = policies.archive(case)
        selected, policy = policies.select(original, row["arm"])
        policies.verify_structured(case, original, selected, row["arm"], policy)
        for private in (case["challenge"], case["confirmation"]):
            if policies.occurrences(original, private) or private in json.dumps(TOOLS):
                raise ValueError("fresh tool data present in initial prompt")
        if case["receipt"] in json.dumps(TOOLS):
            raise ValueError("archive evidence present in tool schema")
    return inputs, policies, owner, {case["id"]: case for case in cases}, rows


def check_deadlines(window_deadline, task_deadline):
    live.check_window(window_deadline)
    if time.time() >= task_deadline:
        raise TaskDeadline()


def post(folder, label, path, payload, key, window_deadline, task_deadline):
    check_deadlines(window_deadline, task_deadline)
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    sent, received = (
        folder / f"{label}.{kind}.body" for kind in ("request", "response")
    )
    sent.write_bytes(data)
    request = urllib.request.Request(
        ENDPOINT + path,
        data=data,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    started = time.monotonic()
    status = None
    try:
        try:
            reply = HTTP.open(
                request,
                timeout=max(0.1, min(window_deadline, task_deadline) - time.time()),
            )
        except urllib.error.HTTPError as exc:
            reply = exc
        with reply, received.open("wb") as body:
            status = reply.status
            while chunk := reply.read1(65536):
                body.write(chunk)
                check_deadlines(window_deadline, task_deadline)
        if status != 200:
            raise ValueError(f"{path} returned HTTP {status}; see {received}")
        check_deadlines(window_deadline, task_deadline)
        return live.read_json(received)
    except TimeoutError:
        check_deadlines(window_deadline, task_deadline)
        raise
    finally:
        live.atomic_json(
            folder / f"{label}.http.json",
            {
                "endpoint": path,
                "http_status": status,
                "wall_s": time.monotonic() - started,
                "request_sha256": live.digest(sent),
                "response_sha256": live.digest(received) if received.exists() else None,
            },
        )


def request_for(messages, seed):
    return {
        "model": live.MODEL.name,
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto",
        "parallel_tool_calls": False,
        "seed": seed,
        "temperature": 0.3,
        "cache_prompt": False,
        "max_tokens": TURN_TOKENS,
        "stream": False,
        "chat_template_kwargs": TEMPLATE_OPTIONS,
    }


def preflight(folder, row, case, policies, original, turn, send):
    selected, policy = policies.select(original, row["arm"])
    custody = policies.verify_structured(case, original, selected, row["arm"], policy)
    if turn == 1:
        for private in (case["challenge"], case["confirmation"]):
            if policies.occurrences(selected, private):
                raise ValueError("first request contains private environment output")
    live.atomic_json(folder / "original-messages.json", original)
    request = request_for(selected, (row["seed"] + turn - 1) % (2**31))
    prompt = send(folder, "template", "/apply-template", request)["prompt"]
    policies.verify_render(case, selected, prompt, custody)
    tokens = send(
        folder,
        "tokenize",
        "/tokenize",
        {"content": prompt, "add_special": True, "parse_special": True},
    )["tokens"]
    if (
        not isinstance(tokens, list)
        or not tokens
        or any(type(token) is not int for token in tokens)
    ):
        raise ValueError("invalid native tokenization")
    evidence = {
        "turn": turn,
        "policy": policy,
        **custody,
        "native_prompt_tokens": len(tokens),
    }
    live.atomic_json(folder / "PREFLIGHT.json", evidence)
    return request, evidence


def validate_completion(reply, prompt_tokens):
    if reply["model"] != live.MODEL.name or len(reply["choices"]) != 1:
        raise ValueError("native completion has unexpected model or choice count")
    usage = reply["usage"]
    if (
        type(usage["prompt_tokens"]) is not int
        or usage["prompt_tokens"] != prompt_tokens
        or type(usage["completion_tokens"]) is not int
        or not 0 <= usage["completion_tokens"] <= TURN_TOKENS
        or type(usage["total_tokens"]) is not int
        or usage["total_tokens"] != prompt_tokens + usage["completion_tokens"]
    ):
        raise ValueError("native completion token accounting disagrees with preflight")
    choice = reply["choices"][0]
    message = choice["message"]
    finish, calls = choice["finish_reason"], message.get("tool_calls") or []
    if (
        message["role"] != "assistant"
        or finish not in ("length", "stop", "tool_calls")
        or (finish != "length" and (finish == "tool_calls") != bool(calls))
    ):
        raise ValueError("native completion has an invalid finish state")
    for call in calls if finish == "tool_calls" else ():
        if (
            call["type"] != "function"
            or not isinstance(call["id"], str)
            or not call["id"]
            or not isinstance(call["function"]["name"], str)
            or not isinstance(call["function"]["arguments"], str)
        ):
            raise ValueError("native tool-call envelope is malformed")
    return message, finish, usage


def no_answer(reason):
    return {
        "status": "NA",
        "answer": None,
        "correct": False,
        "non_termination": 1,
        "finish_reason": reason,
    }


def trajectory(
    folder, row, case, policies, key, deadline, packet_hash, *, render_only=False
):
    folder.mkdir()
    started = time.monotonic()
    task_deadline = time.time() + TASK_S
    history = policies.archive(case)
    service = OrderService(
        **{
            name: case[name]
            for name in ("order", "desk", "receipt", "challenge", "confirmation")
        }
    )
    result = {
        "status": "UNKNOWN",
        "correct": None,
        "answer": None,
        "non_termination": None,
        "finish_reason": "instrument_failure",
        "turns": [],
    }
    requests_started = 0

    def send(turn_folder, label, path, payload):
        return post(turn_folder, label, path, payload, key, deadline, task_deadline)

    try:
        for number in range(1, MAX_TURNS + 1):
            turn_folder = folder / f"turn-{number:02d}"
            turn_folder.mkdir()
            request, turn = preflight(
                turn_folder, row, case, policies, history, number, send
            )
            result["turns"].append(turn)
            if turn["native_prompt_tokens"] + TURN_TOKENS > CONTEXT_TOKENS:
                result.update(no_answer("context_budget"))
                break
            if render_only:
                result.update(
                    status="rendered", finish_reason="render_only", non_termination=0
                )
                break

            requests_started += 1
            reply = send(turn_folder, "completion", "/v1/chat/completions", request)
            message, finish, usage = validate_completion(
                reply, turn["native_prompt_tokens"]
            )
            turn.update(usage=usage, finish_reason=finish)
            if finish == "length":
                result.update(no_answer("decode_cap"))
                break
            if finish == "stop":
                result.update(service.score(message.get("content")))
                break
            if number == MAX_TURNS:
                result.update(no_answer("turn_cap"))
                break

            calls = message["tool_calls"]
            used = {m["tool_call_id"] for m in history if m["role"] == "tool"}
            ids = [call["id"] for call in calls]
            if len(ids) != len(set(ids)) or any(call_id in used for call_id in ids):
                raise ValueError("native tool call ID repeated within one task")
            observations, events = service.execute(calls)
            history.extend((message, *observations))
            turn["tool_events"] = events
            live.atomic_json(
                turn_folder / "ACTION.json",
                {"tool_events": events, "observations": observations},
            )
    except TaskDeadline:
        result.update(no_answer("task_wall_budget"))
    except live.WindowEnded as exc:
        result["error"] = str(exc)
        raise
    except (OSError, ValueError, TypeError, KeyError, http.client.HTTPException) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        usage = [turn["usage"] for turn in result["turns"] if "usage" in turn]
        usage_complete = requests_started == len(usage)
        result.update(
            row,
            schema=SCHEMA,
            category="CANDIDATE",
            instrument_class="bench",
            source=BASE,
            packet_sha256=packet_hash,
            wall_s=time.monotonic() - started,
            generation_turns=len(usage),
            generation_requests_started=requests_started,
            live_tools_executed=sum(
                len(turn.get("tool_events", [])) for turn in result["turns"]
            ),
            inspected=service.inspected,
            released=service.released,
            usage_complete=usage_complete,
            observed_usage={
                key: sum(entry[key] for entry in usage)
                for key in ("prompt_tokens", "completion_tokens", "total_tokens")
            },
            evidence_sha256={
                str(path.relative_to(folder)): live.digest(path)
                for path in sorted(folder.rglob("*"))
                if path.is_file()
            },
        )
        live.atomic_json(folder / "TRAJECTORY.json", result)
    return result


def summarize(rows, results, arms):
    recorded = {result["unit"]: result for result in results}
    paired, metrics = {}, {}
    for row in rows:
        paired.setdefault(row["case"], {"seed": row["seed"], "arms": {}})["arms"][
            row["arm"]
        ] = recorded.get(row["unit"], {**row, "status": "unattempted", "correct": None})
    for arm in arms:
        entries = [record for record in results if record["arm"] == arm]
        observed = [record for record in entries if record["status"] in OBSERVED]
        all_costs = [
            record["observed_usage"]["total_tokens"]
            for record in observed
            if record["usage_complete"]
        ]
        partial_costs = [
            record["observed_usage"]["total_tokens"]
            for record in observed
            if not record["usage_complete"]
        ]
        correct = sum(record["correct"] is True for record in observed)
        metrics[arm] = {
            "scheduled": sum(row["arm"] == arm for row in rows),
            "attempted": len(entries),
            "observed": len(observed),
            "correct": correct,
            "accuracy_over_observed": correct / len(observed) if observed else None,
            "graded": sum(record["status"] == "graded" for record in entries),
            "abstained": sum(record["status"] == "abstained" for record in entries),
            "NA": sum(record["status"] == "NA" for record in entries),
            "UNKNOWN": sum(record["status"] == "UNKNOWN" for record in entries),
            "non_termination": sum(
                record["non_termination"] == 1 for record in observed
            ),
            "complete_cost_tasks": len(all_costs),
            "incomplete_cost_tasks": len(partial_costs),
            "incomplete_token_lower_bound_total": sum(partial_costs),
            "mean_live_tokens_per_complete_cost_task": sum(all_costs) / len(all_costs)
            if all_costs
            else None,
            "mean_live_wall_s_per_observed_task": (
                sum(record["wall_s"] for record in observed) / len(observed)
                if observed
                else None
            ),
        }
    return {
        "scheduled": len(rows),
        "recorded": len(results),
        "completed": sum(result["status"] in OBSERVED for result in results),
        "arms": metrics,
        "paired": paired,
    }


def run():
    if os.environ.get("FILLER_ID") != ROW:
        raise ValueError("allocator grant or publisher smoke environment required")
    inputs, policies, owner, cases, rows = verify()
    dry = os.environ.get("FILLER_DRYRUN") == "1"
    out = (
        Path(os.environ["FILLER_DRYRUN_DIR"]) / "cf3c-task-native"
        if dry
        else SCRATCH / "native"
    )
    out.mkdir(mode=0o700, exist_ok=True)
    with (out / "run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not dry and any(out.glob("window-*")):
            raise ValueError(
                "fixed diagnostic grant already attempted; retain the partial window"
            )
        return run_window(out, dry, inputs, policies, owner, cases, rows)


def run_window(out, dry, inputs, policies, owner, cases, rows):
    cpus = live.bind_four_cores()
    if not live.file_port_available(PORT) or owner.listen_inodes(PORT):
        raise ValueError("private listener port is unavailable")
    window = Path(tempfile.mkdtemp(prefix="window-", dir=out))
    packet_hash = live.digest(HERE / "inputs.json")
    argv = live.server_argv(4, PORT)
    env = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith(("LLAMA_", "GGML_", "OMP_", "KMP_", "GOMP_"))
    }
    key = secrets.token_urlsafe(24)
    env.update(LD_LIBRARY_PATH=str(live.BIN.resolve()), LLAMA_API_KEY=key)
    deadline = min(int(os.environ["FILLER_DEADLINE"]), time.time() + WINDOW_S)
    signal.signal(signal.SIGTERM, live.handle_stop)
    signal.signal(signal.SIGINT, live.handle_stop)
    if dry:
        schedule = [(row, True) for row in rows if row["case"] == "archive-reasoning"]
        schedule.extend(
            (row, False)
            for row in rows
            if row["case"] == "archive-head" and row["arm"] == "A0"
        )
    else:
        schedule = [(row, False) for row in rows]
    limits = {
        "context_tokens": CONTEXT_TOKENS,
        "decode_tokens_per_turn": TURN_TOKENS,
        "generation_turns": MAX_TURNS,
        "task_wall_s": TASK_S,
        "window_wall_s": WINDOW_S,
    }
    live.atomic_json(
        window / "WINDOW.json",
        {
            "schema": SCHEMA,
            "source": BASE,
            "packet_sha256": packet_hash,
            "grant": ROW,
            "inputs": inputs,
            "model_affinity": cpus,
            "argv": argv,
            "smoke": dry,
            "effective_deadline": deadline,
            "limits": limits,
            "schedule": [
                {**row, "render_only": render_only} for row, render_only in schedule
            ],
        },
    )
    results = []
    exited, error = False, None
    try:
        live.check_window(deadline)
        linkage = subprocess.run(
            [
                "bash",
                str(HERE / "verify_ggml_linkage.sh"),
                argv[0],
                str(live.BIN.resolve()),
            ],
            env=env,
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        (window / "LINKAGE.txt").write_text(linkage.stdout)
        server_log = window / "server.log"
        startup = time.monotonic()
        with server_log.open("wb") as log:
            proc = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                with open(os.environ["FILLER_PIDFILE"], "a", encoding="utf-8") as pids:
                    pids.write(f"{proc.pid}\n")
                server = live.server_ready(
                    proc,
                    owner,
                    key,
                    min(deadline, time.time() + 160),
                    server_log,
                    port=PORT,
                )
                live.atomic_json(
                    window / "SERVER.json",
                    {**server, "startup_wall_s": time.monotonic() - startup},
                )
                for row, render_only in schedule:
                    live.check_window(deadline)
                    if not dry and deadline - time.time() < TASK_S + 12:
                        raise live.WindowEnded("remaining grant cannot fit a full task")
                    if proc.poll() is not None or not (
                        owner.listen_inodes(PORT) & owner.pid_socket_inodes(proc.pid)
                    ):
                        raise OSError("private listener ownership lost")
                    folder = window / f"task-{row['ordinal']:02d}"
                    try:
                        trajectory(
                            folder,
                            row,
                            cases[row["case"]],
                            policies,
                            key,
                            deadline,
                            packet_hash,
                            render_only=render_only,
                        )
                    finally:
                        if (folder / "TRAJECTORY.json").is_file():
                            results.append(live.read_json(folder / "TRAJECTORY.json"))
                    status = results[-1]["status"]
                    live.atomic_json(
                        out / "PROGRESS.json",
                        {"schema": SCHEMA, "unit": row["unit"], "status": status},
                    )
                    if status == "UNKNOWN":
                        raise ValueError(results[-1]["error"])
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=6)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=6)
                exited = proc.poll() is not None and not owner.listen_inodes(PORT)
    except (
        live.WindowEnded,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.SubprocessError,
    ) as exc:
        error = f"{type(exc).__name__}: {exc}"

    stats = summarize([row for row, _ in schedule], results, policies.ARMS)
    complete = not dry and stats["completed"] == len(rows) and exited and error is None
    result = {
        **stats,
        "schema": SCHEMA,
        "row": ROW,
        "source": BASE,
        "category": "CANDIDATE",
        "instrument_class": "bench",
        "packet_sha256": packet_hash,
        "window": str(window),
        "window_sha256": {
            str(path.relative_to(window)): live.digest(path)
            for path in sorted(window.rglob("*"))
            if path.is_file()
        },
        "server_exited": exited,
        "error": error,
        "coverage_complete": complete,
        "diagnostic_only": True,
        "scope": "live continuation from a seeded historical prefix",
        "unit": results[-1]["unit"] if results else None,
    }
    if dry:
        renders = [r for r in results if r["status"] == "rendered"]
        controls = [
            r for r in results if r["case"] == "archive-head" and r["arm"] == "A0"
        ]
        result["qualified"] = (
            exited
            and error is None
            and len(renders) == len(policies.ARMS)
            and len(controls) == 1
            and all(
                r["turns"][0]["archive_receipt_exposed"] == (r["arm"] != "A3")
                for r in renders
            )
            and controls[0]["correct"] is True
            and controls[0]["live_tools_executed"] >= 2
            and controls[0]["generation_turns"] >= 3
        )
        live.atomic_json(
            out / ("SMOKE.json" if result["qualified"] else "PARTIAL.json"), result
        )
        return int(not result["qualified"])
    live.atomic_json(out / ("RESULT.json" if complete else "PARTIAL.json"), result)
    return int(not complete)


def smoke():
    root = os.environ.get("FILLER_DRYRUN_DIR")
    try:
        started = float(os.environ["FILLER_SMOKE_T0"])
    except (KeyError, ValueError):
        return 1
    if not root or not math.isfinite(started) or started <= 0:
        return 1
    path = Path(root) / "cf3c-task-native/SMOKE.json"
    if not path.is_file() or path.stat().st_mtime < started:
        return 1
    record = live.read_json(path)
    return int(
        not (
            record["qualified"] is True
            and record["server_exited"] is True
            and record["row"] == ROW
            and record["packet_sha256"] == live.digest(HERE / "inputs.json")
        )
    )


def complete():
    if not RESULT.is_file():
        return 1
    record = live.read_json(RESULT)
    return int(
        not (
            record["coverage_complete"] is True
            and record["completed"] == 18
            and record["row"] == ROW
            and record["packet_sha256"] == live.digest(HERE / "inputs.json")
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode", choices=("verify", "run", "smoke", "complete", "precondition")
    )
    mode = parser.parse_args().mode
    if mode == "verify":
        verify()
        return 0
    if mode == "precondition":
        return int(not live.file_port_available(PORT))
    return {"run": run, "smoke": smoke, "complete": complete}[mode]()


if __name__ == "__main__":
    sys.exit(main())
