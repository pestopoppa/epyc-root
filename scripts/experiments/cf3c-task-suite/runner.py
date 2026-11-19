"""Run the fixed CF-3c coverage shard in an allocator-owned private window."""

import argparse
import fcntl
import json
import math
import os
import secrets
import signal
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cmp4_runner as live
import prepare as profile
from graph_trial import ENDPOINT, completed_wire, partial_wire_usage, read_wire, sha
from prepare import (
    ARMS,
    BASE,
    CONTEXT_TOKENS,
    COVERAGE_CASES,
    MAX_COMPLETION_TOKENS,
    MAX_TURNS,
    PORT,
    PYTHON,
    ROW,
    SCRATCH,
    SOURCE,
    TASK_S,
    WINDOW_S,
    verify_packet,
)

SCHEMA = "epyc.cf3c.suite.native.v1"
RESULT = SCRATCH / "native/RESULT.json"
SMOKE_DIR = "cf3c-suite-native"
USAGE_FIELDS = ("prompt_tokens", "completion_tokens", "cached_prompt_tokens")


class TaskWallBudget(Exception):
    """The registered task wall allowance expired before a native terminal."""


def verify():
    inputs = verify_packet(HERE)
    if (inputs["model_path"], inputs["model_sha256"], inputs["template_sha256"]) != (
        str(live.MODEL),
        live.MODEL_SHA,
        live.TEMPLATE_SHA,
    ):
        raise ValueError("CMP4 serving helper differs from the registered receipt")
    live.verify_inputs(inputs)
    sys.path[:0] = [str(SOURCE), str(SOURCE / "scripts/benchmark")]
    from scripts.benchmark.seeding_scoring import score_answer_or_error

    from scripts.benchmark import own_port_proof

    for callable_or_module in (
        own_port_proof,
        sys.modules[score_answer_or_error.__module__],
    ):
        if not Path(callable_or_module.__file__).resolve().is_relative_to(SOURCE):
            raise ValueError("process dependency escaped the pinned source")
    return inputs, own_port_proof, score_answer_or_error


def usage_totals(usage, wire_count):
    totals, complete, observed = {}, {}, {}
    exchanges_complete = len(usage) == wire_count and all(
        entry["exchange_complete"] is True for entry in usage
    )
    for field in USAGE_FIELDS:
        counters = [entry[field] for entry in usage if entry[field] is not None]
        totals[field] = sum(counters)
        observed[field] = len(counters)
        complete[field] = exchanges_complete and len(counters) == wire_count
    totals["total_tokens"] = totals["prompt_tokens"] + totals["completion_tokens"]
    complete["total_tokens"] = (
        complete["prompt_tokens"] and complete["completion_tokens"]
    )
    return {
        "observed_usage": totals,
        "usage_complete": complete,
        "usage_observed_requests": observed,
    }


def observed_outcome(graph, case, inventory, score):
    terminal = graph["terminal_state"]
    method = inventory["scoring_method"]
    if terminal in {"turn-exhausted", "context-exhausted", "killed", "wall-exhausted"}:
        # Native task failure counts as no answer. Only the predeclared accuracy
        # cohort contributes to an accuracy denominator.
        correct = False if inventory["grade_cohort"] else None
        return {
            "status": "NA",
            "correct": correct,
            "grade_reason": inventory["grade_reason"],
            "scoring_method": method,
            "no_answer": True,
        }
    if terminal != "finished":
        raise ValueError(f"unrecognized native task terminal: {terminal}")
    answer = graph["answer"]
    if not isinstance(answer, str):
        raise TypeError("native graph answer must be text")
    if not answer.strip():
        return {
            "status": "NA",
            "correct": False if inventory["grade_cohort"] else None,
            "grade_reason": inventory["grade_reason"],
            "scoring_method": method,
            "no_answer": True,
        }
    if not inventory["grade_cohort"]:
        return {
            "status": "grade_unavailable",
            "correct": None,
            "grade_reason": inventory["grade_reason"],
            "scoring_method": method,
            "no_answer": False,
        }
    correct, reason = score(
        answer, case["expected"], method, case.get("scoring_config")
    )
    return {
        "status": "graded" if type(correct) is bool else "grade_unavailable",
        "correct": correct,
        "grade_reason": reason,
        "scoring_method": method,
        "no_answer": False,
    }


def child_env(attempt, row, key):
    env = {k: v for k, v in os.environ.items() if k in {"PATH", "LANG", "LC_ALL"}}
    env.update(
        {
            "CF3C_SUITE_API_KEY": key,
            "TMPDIR": str(attempt),
            "ORCHESTRATOR_PATHS_LLM_ROOT": str(attempt),
            "ORCHESTRATOR_PATHS_TMP_DIR": str(attempt / "repl-artifacts"),
            "ORCHESTRATOR_TRAJECTORY_ARTIFACT_DIR": str(attempt),
            "ORCHESTRATOR_CONTEXT_ARM": "full_history",
            "ORCHESTRATOR_CONTEXT_BUDGET_TOKENS": str(CONTEXT_TOKENS),
            "ORCHESTRATOR_CONTEXT_TRIGGER_FRACTION": "0.5",
            "ORCHESTRATOR_CONTEXT_TRIAL_INDEX": str(row["repeat"]),
        }
    )
    return env


def stop_process(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=6)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=6)
    return process.poll() is not None


def wall_budget_outcome(folder):
    path = folder / "trial.trajectory.jsonl"
    events = []
    if path.is_file():
        captured = path.read_bytes().rpartition(b"\n")[0]
        events = [json.loads(line) for line in captured.splitlines() if line]
    turns = [e for e in events if e["event"] == "turn"]
    return {
        "answer": None,
        "terminal_state": "wall-exhausted",
        "terminal_reason": "task_wall_budget",
        "turns": max((e["turn"] for e in turns), default=0),
        "give_up_proxy": False,
        "policy_receipts": [
            record["policy_receipt"]
            for record in read_wire(folder)
            if record.get("policy_receipt") and record.get("http_status") == 200
        ],
        "tool_calls": {
            key: sum(turn["tool_calls"][key] for turn in turns)
            for key in ("retrieval", "execution")
        },
        "trajectory_complete": False,
    }


def run_trial(folder, row, case, inventory, score, key, deadline):
    folder.mkdir(mode=0o700)
    # Only user-visible inputs are written for the graph. The parent's grader
    # retains the source oracle and scoring configuration outside this scope.
    live.atomic_json(
        folder / "INPUT.json",
        {
            "source": str(SOURCE),
            "endpoint": ENDPOINT,
            "row": row,
            "prompt": case["prompt"],
            "context": case.get("context"),
            **({"recovery_probe_v1": True} if case.get("schema") == "epyc.cf3c.native-recovery-probe.v1" else {}),
            **(
                {"initial_history": case["initial_history"]}
                if "initial_history" in case
                else {}
            ),
        },
    )
    started = time.monotonic()
    graph_file = folder / "GRAPH.json"
    graph, stopped = None, False
    try:
        with (folder / "trial.log").open("wb") as log:
            process = subprocess.Popen(
                [str(PYTHON), "-I", "-B", str(HERE / "graph_trial.py"), str(folder)],
                cwd=folder,
                env=child_env(folder, row, key),
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            try:
                while process.poll() is None:
                    live.check_window(deadline)
                    if time.monotonic() - started >= TASK_S:
                        raise TaskWallBudget(
                            "trial wall cap interrupted graph before terminal"
                        )
                    try:
                        process.wait(timeout=0.5)
                    except subprocess.TimeoutExpired:
                        pass
            finally:
                stopped = stop_process(process)
        if process.returncode or not graph_file.is_file():
            raise ValueError(f"native graph child failed: rc={process.returncode}")
        graph = live.read_json(graph_file)
        result = observed_outcome(graph, case, inventory, score)
    except TaskWallBudget:
        if not stopped:
            raise RuntimeError(
                "task wall allowance expired without confirmed child exit"
            )
        graph = wall_budget_outcome(folder)
        result = observed_outcome(graph, case, inventory, score)
    except (
        live.WindowEnded,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.SubprocessError,
    ) as exc:
        result = {
            "status": "UNKNOWN",
            "correct": None,
            "no_answer": None,
            "error": f"{type(exc).__name__}: {exc}",
        }
    if (
        graph is None
        or graph.get("trajectory_complete") is False
        or result["status"] == "UNKNOWN"
    ):
        wire = read_wire(folder)
        # Pending or failed requests contribute neither an invented zero nor an
        # estimated count. Already finished exchanges remain a lower bound.
        usage = []
        for record in wire:
            try:
                usage.append(completed_wire(folder, record))
            except (OSError, ValueError, KeyError, TypeError):
                try:
                    partial = partial_wire_usage(folder, record)
                except (OSError, ValueError, TypeError):
                    partial = None
                if partial is not None:
                    usage.append(partial)
        wire_count = max(len(wire), len(list(folder.glob("wire/*"))))
    else:
        usage, wire_count = graph["native_usage"], graph["wire_requests"]
    record = {
        **row,
        **result,
        **usage_totals(usage, wire_count),
        "wall_s": time.monotonic() - started,
        "child_exited": stopped,
        "wire_requests": wire_count,
        "native_usage": usage,
        "grade_cohort": inventory["grade_cohort"],
        "native_result": graph,
        "attempt": str(folder),
    }
    live.atomic_json(folder / "OUTCOME.json", record)
    return record


def summarize(schedule, results):
    by_arm = {}
    for arm in ARMS:
        attempted = [r for r in results if r["arm"] == arm]
        observed = [r for r in attempted if r["status"] != "UNKNOWN"]
        graded = [r for r in observed if type(r["correct"]) is bool]
        complete_cost = [
            r
            for r in attempted
            if r["usage_complete"]["total_tokens"] and r["status"] != "UNKNOWN"
        ]
        policy_active = sum(
            any(receipt["active"] for receipt in r["native_result"]["policy_receipts"])
            for r in observed
        )
        by_arm[arm] = {
            "planned": sum(row["arm"] == arm for row in schedule),
            "attempted": len(attempted),
            "observed": len(observed),
            "status_counts": dict(Counter(r["status"] for r in attempted)),
            "terminal_states": dict(
                Counter(r["native_result"]["terminal_state"] for r in observed)
            ),
            "accuracy_denominator": len(graded),
            "correct": sum(r["correct"] for r in graded),
            "accuracy": sum(r["correct"] for r in graded) / len(graded)
            if graded
            else None,
            "no_answer": sum(r["no_answer"] for r in observed),
            "give_up_proxy": sum(r["native_result"]["give_up_proxy"] for r in observed),
            "policy_active": policy_active,
            "retrieval_calls": sum(
                r["native_result"]["tool_calls"]["retrieval"] for r in observed
            ),
            "cost_complete_tasks": len(complete_cost),
            "tokens_per_complete_cost_task": (
                sum(r["observed_usage"]["total_tokens"] for r in complete_cost)
                / len(complete_cost)
                if complete_cost
                else None
            ),
            "tokens_observed_lower_bound": sum(
                r["observed_usage"]["total_tokens"] for r in attempted
            ),
            "wall_s_per_observed_task": sum(r["wall_s"] for r in observed)
            / len(observed)
            if observed
            else None,
        }
    completed = sum(r["status"] != "UNKNOWN" for r in results)
    return {
        "planned": len(schedule),
        "attempted": len(results),
        "completed": completed,
        "unknown": len(results) - completed,
        "unattempted": len(schedule) - len(results),
        "by_arm": by_arm,
        "scaling_futility": (
            completed == len(schedule)
            and not any(by_arm[arm]["policy_active"] for arm in ARMS[1:-1])
        ),
    }


def smoke_history_seen(folder):
    """Require a completed generation after the graph sent nonempty selected history."""
    for record in read_wire(folder):
        receipt = record.get("policy_receipt")
        if (
            record["call_kind"] != "graph_turn"
            or record["graph_turn"] < 2
            or not receipt
            or receipt["selected_history_sha256"] == sha("")
        ):
            continue
        try:
            usage = completed_wire(folder, record)
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if (
            usage["prompt_tokens"] is not None
            and usage["completion_tokens"] is not None
        ):
            return True
    return False


def recovery_control_row(probe):
    """Use the complete native trial row contract for the separate control."""
    return {"ordinal": 1, "unit": probe["id"], "case": probe["id"],
            "arm": probe["arm"], "seed": probe["seed"], "repeat": 0}


def run_window(out, dry, inputs, owner, score, cases, inventory, coverage):
    cpus = live.bind_four_cores()
    if not live.file_port_available(PORT) or owner.listen_inodes(PORT):
        raise ValueError("private listener port is unavailable")
    smoke_cases = {COVERAGE_CASES[1], COVERAGE_CASES[-1]}
    binding = getattr(profile, "BINDING_PROFILE", False)
    schedule = (
        [r for r in coverage if r["arm"] == "A1-k12" and r["case"] == "binding_deep_v1"]
        if dry and binding
        else (
        [r for r in coverage if r["arm"] == "A0" and r["case"] in smoke_cases]
        if dry
        else coverage
        )
    )
    recovery_probe = None
    if dry and getattr(profile, "RECOVERY_PROBE_V1", False):
        from recovery_probe import compile_probe
        recovery_probe = compile_probe(profile.cohort())
        identity = recovery_probe["id"]
        cases = {identity: recovery_probe}
        inventory = {identity: {"id": identity, "grade_cohort": False,
                               "scoring_method": "ungraded",
                               "grade_reason": "separate recovery instrument control"}}
        schedule = [recovery_control_row(recovery_probe)]
    window = Path(tempfile.mkdtemp(prefix="window-", dir=out))
    packet_hash = live.digest(HERE / "inputs.json")
    argv = live.server_argv(4, PORT)
    env = {k: v for k, v in os.environ.items() if k in {"PATH", "LANG", "LC_ALL"}}
    key = secrets.token_urlsafe(24)
    env.update(LD_LIBRARY_PATH=str(live.BIN.resolve()), LLAMA_API_KEY=key)
    deadline = min(int(os.environ["FILLER_DEADLINE"]), time.time() + WINDOW_S)
    signal.signal(signal.SIGTERM, live.handle_stop)
    signal.signal(signal.SIGINT, live.handle_stop)
    live.atomic_json(
        window / "WINDOW.json",
        {
            "schema": SCHEMA,
            "inputs": inputs,
            "packet_sha256": packet_hash,
            "argv": argv,
            "model_affinity": cpus,
            "schedule": schedule,
            "effective_deadline": deadline,
            "smoke": dry,
            "limits": {
                "turns": MAX_TURNS,
                "completion_tokens_per_call": MAX_COMPLETION_TOKENS,
                "context_tokens": CONTEXT_TOKENS,
                "task_wall_s": TASK_S,
                "window_wall_s": WINDOW_S,
            },
        },
    )
    results = []
    exited, error = False, None
    try:
        live.check_window(deadline)
        linkage = subprocess.run(
            [
                "bash",
                str(getattr(profile, "LINKAGE", HERE / "verify_ggml_linkage.sh")),
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
        with server_log.open("wb") as log:
            process = subprocess.Popen(
                argv, env=env, stdout=log, stderr=subprocess.STDOUT
            )
            try:
                with open(os.environ["FILLER_PIDFILE"], "a", encoding="utf-8") as pids:
                    pids.write(f"{process.pid}\n")
                server = live.server_ready(
                    process,
                    owner,
                    key,
                    min(deadline, time.time() + 160),
                    server_log,
                    port=PORT,
                )
                live.atomic_json(window / "SERVER.json", server)
                for row in schedule:
                    live.check_window(deadline)
                    if not dry and deadline - time.time() < TASK_S + 12:
                        raise live.WindowEnded("remaining grant cannot fit a full task")
                    if process.poll() is not None or not owner.listen_inodes(
                        PORT
                    ) & owner.pid_socket_inodes(process.pid):
                        raise OSError("private listener ownership lost")
                    record = run_trial(
                        window / f"task-{row['ordinal']:02d}",
                        row,
                        cases[row["case"]],
                        inventory[row["case"]],
                        score,
                        key,
                        deadline,
                    )
                    results.append(record)
                    live.atomic_json(
                        out / "PROGRESS.json",
                        {
                            "schema": SCHEMA,
                            "unit": row["unit"],
                            "status": record["status"],
                        },
                    )
                    if record["status"] == "UNKNOWN":
                        raise ValueError(record["error"])
            finally:
                exited = stop_process(process) and not owner.listen_inodes(PORT)
    except (
        live.WindowEnded,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.SubprocessError,
    ) as exc:
        error = f"{type(exc).__name__}: {exc}"

    stats = summarize(schedule, results)
    complete = (
        not dry and stats["completed"] == len(coverage) and exited and error is None
    )
    report = {
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
        "adoption_margin_resolved": False,
        "unit": results[-1]["unit"] if results else None,
    }
    if dry:
        if recovery_probe is not None:
            from recovery_probe import qualify
            trial = results[0] if len(results) == 1 else {}
            capture = (trial.get("native_result") or {}).get("recovery_capture") or {}
            report["recovery_control"] = qualify(
                recovery_probe, trial, capture, server_exited=exited, error=error)
            report["qualified"] = report["recovery_control"]["qualified"]
            report["quality_cells_observed"] = 0
            live.atomic_json(out / ("SMOKE.json" if report["qualified"] else "PARTIAL.json"), report)
            return int(not report["qualified"])
        if binding:
            trial = results[0] if len(results) == 1 else None
            native = trial["native_result"] if trial else {}
            receipts = native.get("policy_receipts", [])
            report["active_first_generation"] = bool(receipts and receipts[0]["active"])
            report["native_log_recovery"] = bool(
                trial and trial["correct"] is True
                and native.get("tool_calls", {}).get("retrieval", 0) > 0
                and native.get("initial_history_receipt", {}).get("observations") == 10
            )
            report["qualified"] = bool(
                exited and error is None and trial and trial["child_exited"]
                and trial["usage_complete"]["total_tokens"]
                and report["active_first_generation"] and report["native_log_recovery"]
            )
            live.atomic_json(out / ("SMOKE.json" if report["qualified"] else "PARTIAL.json"), report)
            return int(not report["qualified"])
        multi_turn = next((r for r in results if r["case"] == COVERAGE_CASES[1]), None)
        oversized = next((r for r in results if r["case"] == COVERAGE_CASES[-1]), None)
        report["selected_history_exchange_complete"] = bool(
            error is None
            and multi_turn
            and smoke_history_seen(Path(multi_turn["attempt"]))
        )
        report["qualified"] = bool(
            exited
            and error is None
            and multi_turn
            and oversized
            and multi_turn["status"] in {"graded", "grade_unavailable", "NA"}
            and report["selected_history_exchange_complete"]
            and oversized["status"] == "NA"
            and oversized["native_result"]["pre_generation_budget_exhausted"]
        )
        live.atomic_json(
            out / ("SMOKE.json" if report["qualified"] else "PARTIAL.json"), report
        )
        return int(not report["qualified"])
    live.atomic_json(out / ("RESULT.json" if complete else "PARTIAL.json"), report)
    return int(not complete)


def run():
    if os.environ.get("FILLER_ID") != ROW:
        raise ValueError("allocator-owned run environment required")
    inputs, owner, score = verify()
    cases = {case["id"]: case for case in live.read_json(HERE / "cases.json")}
    inventory = {row["id"]: row for row in live.read_json(HERE / "inventory.json")}
    coverage = live.read_json(HERE / "schedule.json")["coverage"]
    dry = os.environ.get("FILLER_DRYRUN") == "1"
    out = Path(os.environ["FILLER_DRYRUN_DIR"]) / SMOKE_DIR if dry else RESULT.parent
    out.mkdir(mode=0o700, exist_ok=True)
    with (out / "run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not dry and any(out.glob("window-*")):
            raise ValueError("fixed coverage shard already attempted")
        return run_window(out, dry, inputs, owner, score, cases, inventory, coverage)


def check_report(path, flag, *, required_completed=None):
    if not path.is_file():
        return 1
    report = live.read_json(path)
    return int(
        not (
            report[flag] is True
            and report["server_exited"] is True
            and report["row"] == ROW
            and report["packet_sha256"] == live.digest(HERE / "inputs.json")
            and (
                required_completed is None or report["completed"] == required_completed
            )
        )
    )


def smoke():
    root = os.environ.get("FILLER_DRYRUN_DIR")
    try:
        started = float(os.environ["FILLER_SMOKE_T0"])
    except (KeyError, ValueError):
        return 1
    if not root or not math.isfinite(started) or started <= 0:
        return 1
    path = Path(root) / SMOKE_DIR / "SMOKE.json"
    if not path.is_file() or path.stat().st_mtime < started:
        return 1
    return check_report(path, "qualified")


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
    if mode == "complete":
        return check_report(
            RESULT,
            "coverage_complete",
            required_completed=len(ARMS) * len(COVERAGE_CASES),
        )
    return {"run": run, "smoke": smoke}[mode]()


if __name__ == "__main__":
    sys.exit(main())
