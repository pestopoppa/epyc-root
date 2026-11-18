"""Run and verify a bounded paired CMP-3 probe on the real isolated REPL graph."""
from __future__ import annotations

import argparse
import hashlib
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
from pathlib import Path

import cmp4_runner as live

HERE = Path(__file__).resolve().parent
SCRATCH = live.SCRATCH.parent / "cmp3-live"
SOURCE = SCRATCH / "source"
ROW = "toc-cmp-3-live-20261118"
PORT = 19368
ENDPOINT = f"http://127.0.0.1:{PORT}"
ARMS = ("baseline_summary_only", "contract_summary_only", "contract_verbatim_manifest")
BOUNDARY_TURN = 3
BUDGET = 8192
TIME_CAP_S = 2700
ATTEMPT_CAP_S = 660
PATCH_SHA = "1b679a01e14e631ea58e6bcfe94f15e59195245b2309aab072d0bbfaaffaa0c3"
MANIFEST_HEADER = "[Verbatim manifest:"
SPAN = re.compile(
    r'^Turn (\d+) (code|output|error) chars=(\d+) sha256=([0-9a-f]{64}) '
    r'peek\((\d+), file_path="([^"\n]+)", offset=(\d+)\)$', re.M
)


def git(*args):
    return subprocess.check_output(["git", "-C", str(SOURCE), *args])


def verify():
    inputs = live.read_json(HERE / "inputs.json")
    if (inputs["model_path"] != str(live.MODEL) or inputs["model_sha256"] != live.MODEL_SHA
            or inputs["template_sha256"] != live.TEMPLATE_SHA or inputs["source"] != live.SOURCE_SHA
            or inputs["candidate_patch_sha256"] != PATCH_SHA
            or live.digest(HERE / "orchestrator.patch") != PATCH_SHA):
        raise ValueError("candidate, model or template identity mismatch")
    live.verify_inputs(inputs)
    if (git("rev-parse", "HEAD").decode().strip() != live.SOURCE_SHA
            or git("diff", "--name-only") or git("ls-files", "--others", "--exclude-standard")
            or hashlib.sha256(git("diff", "--cached", "--binary")).hexdigest() != PATCH_SHA
            or inputs["source_diff_sha256"] != PATCH_SHA):
        raise ValueError("candidate source diverged from the prepared patch")
    git("apply", "--check", "--index", "--reverse", str(HERE / "orchestrator.patch"))
    return inputs


def schedule(cases):
    if len(cases) != 2 or len({case["id"] for case in cases}) != 2:
        raise ValueError("expected two distinct frozen cases")
    rows = []
    for index, case in enumerate(cases):
        order = ARMS if index == 0 else reversed(ARMS)
        for order_index, arm in enumerate(order):
            history_arm = "verbatim_manifest" if arm.endswith("verbatim_manifest") else "summary_only"
            rows.append({
                "run_id": f'{case["id"]}/{arm}',
                "task_id": case["id"], "arm": history_arm, "label": arm, "order": order_index,
                "contract": arm != "baseline_summary_only",
                "repeat": 0, "sampling_seed": case["seed"],
                "env": {
                    "ORCHESTRATOR_CONTEXT_ARM": history_arm,
                    "ORCHESTRATOR_CONTEXT_BUDGET_TOKENS": str(BUDGET),
                    "ORCHESTRATOR_CONTEXT_TRIGGER_FRACTION": "0.5",
                    "ORCHESTRATOR_CONTEXT_FORCE_TURNS": str(BOUNDARY_TURN),
                    "ORCHESTRATOR_CONTEXT_TRIAL_INDEX": "0",
                    "ORCHESTRATOR_FRONTDOOR_REPL_NON_TOOL_N_TOKENS": "128",
                },
            })
    return rows


def trial_case(case):
    return {
        "prompt": (
            "Use exactly three separate Python REPL turns to recover a ticket. "
            "Turn 1: use only print(context.rsplit('\\n', 1)[-1]) to read the source record. "
            f"Turn 2: use only print({case['receipt']!r}) to acknowledge the read. "
            "Turn 3: use FINAL with the exact ticket value after 'ticket=' in the source. "
            "Wait for the REPL feedback after each action. Return one fenced Python code block per turn."
        ),
        "context": f"{case['marker']}{' q7' * 1000} | ticket={case['ticket']}",
        "governance": case["governance"], "expected": case["ticket"], "scoring_method": "exact_match",
    }


def captured(attempt, record, kind):
    path = (attempt / record[f"{kind}_file"]).resolve()
    if not path.is_relative_to(attempt.resolve()) or live.digest(path) != record[f"{kind}_sha256"]:
        raise ValueError(f"wire {kind} custody mismatch")
    return path.read_bytes()


def request_text(attempt, record):
    body = json.loads(captured(attempt, record, "request"))
    prompt = body.get("prompt")
    if isinstance(prompt, str):
        return [prompt]
    return [message["content"] for message in body.get("messages", [])
            if isinstance(message.get("content"), str)]


def response_text(attempt, record):
    payload = captured(attempt, record, "response").decode("utf-8")
    if record.get("http_status") != 200 or record.get("response_error"):
        raise ValueError("generation response failed")
    if not record.get("response_complete"):
        return ""

    def content(body):
        if "content" in body:
            return body["content"] or ""
        return "".join((choice.get("delta") or choice.get("message") or {}).get("content") or ""
                       for choice in body.get("choices", []))

    if record["stream_requested"]:
        return "".join(content(json.loads(line[6:])) for line in payload.splitlines()
                       if line.startswith("data: ") and line[6:] != "[DONE]")
    return content(json.loads(payload))


def verify_manifest(attempt, prompt, case):
    entries = list(SPAN.finditer(prompt))
    if not entries:
        return []
    witness = []
    for entry in entries:
        turn, kind, chars, sha256, peek_chars, path_text, offset = entry.groups()
        path = Path(path_text).resolve()
        if not path.is_relative_to(attempt.resolve()) or path.name != "session.verbatim.md":
            raise ValueError("omission manifest names a log outside the trial")
        log = path.read_bytes().decode("utf-8")
        start, count = int(offset), int(chars)
        span = log[start:start + count]
        if (chars != peek_chars or len(span) != count or start > len(log)
                or hashlib.sha256(span.encode("utf-8")).hexdigest() != sha256):
            raise ValueError("omission manifest digest or span mismatch")
        witness.append({"turn": int(turn), "kind": kind, "chars": count, "offset": start,
                        "sha256": sha256, "path": str(path),
                        "matches_fixture": kind == "output" and case["marker"] in span})
    return witness


def assess(attempt, row, case):
    graph = live.read_json(attempt / "GRAPH.json")
    trajectory = attempt / "trial.trajectory.jsonl"
    events = live.read_jsonl(trajectory)
    observed = live.trajectory_metrics(events, row, smoke=True)
    final = events[-1]
    evidence = {
        "unit": row["run_id"], "row": row, "trajectory": str(trajectory),
        "trajectory_sha256": live.digest(trajectory), "graph": str(attempt / "GRAPH.json"),
        "terminal_state": final["terminal_state"], "boundary_reached": observed["boundary_reached"],
        "correct": graph["correct"], "grade_reason": graph["grade_reason"],
        "contract_delivered": None, "status": "unknown",
    }
    if not observed["boundary_reached"]:
        return {**evidence, "reason": "boundary_not_reached"}
    boundary = observed["boundary"]
    evidence["boundary"] = boundary
    wire = graph["wire"]
    if any(record.get("call_kind") not in {"generation", "summary"} for record in wire):
        raise ValueError("generation request lacks a graph call binding")
    continuations = [record for record in wire
                     if record["call_kind"] == "generation" and record["graph_turn"] == BOUNDARY_TURN]
    continuation_events = [event for event in events[events.index(boundary) + 1:]
                           if event["event"] == "turn" and event["turn"] == BOUNDARY_TURN]
    if not continuations or not continuation_events:
        return {**evidence, "reason": "continuation_not_observed"}
    if len(continuations) != 1 or len(continuation_events) != 1:
        raise ValueError("continuation is ambiguous")
    continuation, turn = continuations[0], continuation_events[0]
    if continuation["history_boundaries"] != [BOUNDARY_TURN]:
        raise ValueError("generation was not bound to the assigned boundary")
    evidence["continuation_request"] = continuation
    evidence["continuation_prompt_tokens"] = turn.get("prompt_tokens")
    evidence["continuation_completion_tokens"] = turn.get("completion_tokens")
    if not response_text(attempt, continuation).strip():
        return {**evidence, "reason": "continuation_generation_incomplete"}
    texts = request_text(attempt, continuation)
    expected = (attempt / "EXPECTED-CONTRACT.txt").read_bytes().decode("utf-8")
    evidence["contract_sha256"] = hashlib.sha256(expected.encode("utf-8")).hexdigest()
    evidence["contract_delivered"] = sum(text.count(expected) for text in texts) == 1
    if evidence["contract_delivered"] != row["contract"] or (
            not row["contract"] and any("[Execution brief v1]" in text for text in texts)):
        return {**evidence, "status": "failed", "reason": "contract_delivery_mismatch"}
    summaries = [record for record in wire if record["call_kind"] == "summary"]
    if row["arm"] == "summary_only":
        if not summaries and boundary["summary_tokens"] == 0:
            return {**evidence, "reason": "no_history_folded"}
        if len(summaries) != 1 or summaries[0]["graph_turn"] != BOUNDARY_TURN or boundary["summary_tokens"] <= 0:
            raise ValueError("unexpected summary schedule")
        summary = summaries[0]
        evidence["summary_request"] = summary
        if not response_text(attempt, summary).strip():
            return {**evidence, "reason": "summary_generation_incomplete"}
        if not any(case["marker"] in text for text in request_text(attempt, summary)):
            return {**evidence, "reason": "fixture_source_not_in_summary_input"}
    else:
        if summaries or boundary["summary_tokens"] != 0:
            raise ValueError("manifest arm generated a summary")
        manifests = [text for text in texts if MANIFEST_HEADER in text]
        if len(manifests) != 1:
            return {**evidence, "status": "failed", "reason": "manifest_not_delivered"}
        spans = verify_manifest(attempt, manifests[0], case)
        evidence["omitted_spans"] = spans
        if not any(span["matches_fixture"] for span in spans):
            return {**evidence, "reason": "fixture_source_not_omitted"}
    if not isinstance(turn.get("prompt_tokens"), int) or turn["prompt_tokens"] <= 0:
        return {**evidence, "reason": "continuation_prompt_tokens_unobserved"}
    return {**evidence, "status": "observed"}


def run_trial(window, row, case, proc, port_proof, key, deadline, smoke):
    live.check_window(deadline)
    if proc.poll() is not None or not (port_proof.listen_inodes(PORT) & port_proof.pid_socket_inodes(proc.pid)):
        raise OSError("private listener ownership lost")
    attempt = Path(tempfile.mkdtemp(prefix="trial-", dir=window))
    live.atomic_json(attempt / "INPUT.json", {"row": row, "case": trial_case(case),
        "source": str(SOURCE), "temperature": live.TEMPERATURE, "endpoint": ENDPOINT, "smoke": smoke})
    started = time.monotonic()
    try:
        with (attempt / "child.log").open("wb") as log:
            subprocess.run([str(live.PYTHON), "-B", str(HERE / "trial.py"), str(attempt)],
                           cwd=attempt, env=live.graph_env(row, attempt, key),
                           stdout=log, stderr=subprocess.STDOUT, check=True,
                           timeout=min(ATTEMPT_CAP_S, max(0.1, deadline - time.time())))
        result = assess(attempt, row, case)
    except subprocess.SubprocessError as exc:
        live.check_window(deadline)
        raise OSError(f"graph trial failed; see {attempt / 'child.log'}") from exc
    result["wall_s"] = time.monotonic() - started
    live.atomic_json(attempt / "METRICS.json", result)
    return result


def run():
    if os.environ.get("FILLER_ID") != ROW:
        raise ValueError("rowflow grant or smoke environment required")
    verify()
    dry = os.environ.get("FILLER_DRYRUN") == "1"
    out = Path(os.environ["FILLER_DRYRUN_DIR"]) / "cmp3-live-native" if dry else SCRATCH / "native"
    out.mkdir(parents=True, exist_ok=True)
    cases = {case["id"]: case for case in live.read_json(HERE / "cases.json")}
    rows = schedule(list(cases.values()))
    attempts = [rows[1]] if dry else rows
    cpus = sorted(os.sched_getaffinity(0))
    threads = int(os.environ["FILLER_THREADS"])
    if threads != 4 or len(cpus) != 4 or not live.file_port_available(PORT):
        raise ValueError("expected four allocated threads and an unused private port")
    sys.path.insert(0, str(SOURCE))
    from scripts.benchmark import own_port_proof

    if own_port_proof.listen_inodes(PORT):
        raise ValueError("private port listener already exists")
    window = Path(tempfile.mkdtemp(prefix="window-", dir=out))
    receipt = {"input_sha256": live.digest(HERE / "inputs.json"), "schedule": attempts, "affinity": cpus,
               "endpoint": ENDPOINT, "server_argv": live.server_argv(threads, PORT),
               "temperature": live.TEMPERATURE, "dry_run": dry}
    receipt_path = (window if dry else out) / "RECEIPT.json"
    with receipt_path.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2)
    deadline = min(int(os.environ["FILLER_DEADLINE"]), time.time() + TIME_CAP_S)
    key = secrets.token_urlsafe(24)
    server_env = {name: value for name, value in os.environ.items()
                  if not name.startswith(("LLAMA_", "GGML_", "OMP_", "KMP_", "GOMP_"))}
    server_env.update(LD_LIBRARY_PATH=str(live.BIN.resolve()), LLAMA_API_KEY=key)
    results = []
    error = None
    server_exited = False
    signal.signal(signal.SIGTERM, live.handle_stop)
    signal.signal(signal.SIGINT, live.handle_stop)
    try:
        live.check_window(deadline)
        argv = receipt["server_argv"]
        linkage = subprocess.run(["bash", str(HERE / "verify_ggml_linkage.sh"), argv[0], str(live.BIN.resolve())],
                                 env=server_env, check=True, capture_output=True, text=True, timeout=20)
        (window / "LINKAGE.txt").write_text(linkage.stdout)
        log_path = window / "server.log"
        with log_path.open("wb") as log:
            proc = subprocess.Popen(argv, env=server_env, stdout=log, stderr=subprocess.STDOUT)
            try:
                with open(os.environ["FILLER_PIDFILE"], "a", encoding="utf-8") as pids:
                    pids.write(f"{proc.pid}\n")
                server = live.server_ready(proc, own_port_proof, key, min(deadline, time.time() + 160),
                                           log_path, port=PORT)
                live.atomic_json(window / "SERVER.json", server)
                for row in attempts:
                    result = run_trial(window, row, cases[row["task_id"]], proc, own_port_proof,
                                       key, deadline, dry)
                    results.append(result)
                    if result["status"] == "failed":
                        raise ValueError(result["reason"])
                    live.atomic_json(out / "PROGRESS.json", {"unit": row["run_id"], "status": result["status"]})
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=6)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=6)
                server_exited = proc.poll() is not None and not own_port_proof.listen_inodes(PORT)
    except live.WindowEnded as exc:
        error = str(exc)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        error = f"{type(exc).__name__}: {exc}"

    completed = sum(result["status"] == "observed" for result in results)
    coverage = completed == len(attempts) and server_exited and error is None
    missing = sorted({row["run_id"] for row in attempts} - {result["unit"] for result in results})
    result = {"unit": attempts[-1]["run_id"], "completed": completed, "coverage_complete": coverage,
              "server_exited": server_exited, "error": error, "results": results, "unobserved": missing,
              "scope": "descriptive isolated REPL integration"}
    result_name = "SMOKE.json" if dry and coverage else "RESULT.json" if coverage else "PARTIAL.json"
    live.atomic_json(out / result_name, result)
    return int(not coverage)


def smoke_predicate():
    root = os.environ.get("FILLER_DRYRUN_DIR")
    try:
        started = float(os.environ.get("FILLER_SMOKE_T0", ""))
    except ValueError:
        return 1
    if not root or not math.isfinite(started) or started <= 0:
        return 1
    path = Path(root) / "cmp3-live-native/SMOKE.json"
    return int(not (path.is_file() and path.stat().st_mtime >= started
                    and live.read_json(path).get("coverage_complete") is True
                    and live.read_json(path).get("server_exited") is True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("verify", "run", "smoke", "complete", "precondition"))
    mode = parser.parse_args().mode
    if mode == "verify":
        verify()
        return 0
    if mode == "smoke":
        return smoke_predicate()
    if mode == "precondition":
        return int(not live.file_port_available(PORT))
    if mode == "complete":
        path = SCRATCH / "native/RESULT.json"
        return int(not (path.is_file() and live.read_json(path).get("coverage_complete") is True))
    return run()


if __name__ == "__main__":
    sys.exit(main())
