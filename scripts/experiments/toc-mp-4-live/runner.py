"""Run a sealed TOC-MP-4 matrix through the isolated frontdoor and real REPL."""
from __future__ import annotations

import argparse
import fcntl
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
from assessment import assess
from trial import BOUNDARY_TURN, CHECKPOINT_CODE, RECORD_CODE

HERE = Path(__file__).resolve().parent
SCRATCH = live.SCRATCH.parent / "mp4"
SOURCE = SCRATCH / "source"
ROW = "toc-mp-4-live-20261118"
PORT = 19369
ENDPOINT = f"http://127.0.0.1:{PORT}"
ARMS = ("summary_only", "summary_pointer", "pointer_only")
BUDGET = 16384
ATTEMPT_CAP_S = 1150
TIME_CAP_S = 7200
WEIGHT_RECEIPT_SHA = "3fcd6c2d01901a2a7266367b01179613ee9dd24109f6689d53e1dc183a8daaff"


def git(*args):
    return subprocess.check_output(["git", "-C", str(SOURCE), *args], text=True).strip()


def verify():
    inputs = live.read_json(HERE / "inputs.json")
    if (inputs["source"] != live.SOURCE_SHA or inputs["model_path"] != str(live.MODEL)
            or inputs["model_sha256"] != live.MODEL_SHA or inputs["template_sha256"] != live.TEMPLATE_SHA
            or inputs["cmp4_weight_receipt_sha256"] != WEIGHT_RECEIPT_SHA
            or git("rev-parse", "HEAD") != live.SOURCE_SHA or git("status", "--porcelain")):
        raise ValueError("source, model, template or original receipt pin mismatch")
    live.verify_inputs(inputs)
    if live.read_json(HERE / "schedule.json") != schedule(live.read_json(HERE / "cases.json")):
        raise ValueError("frozen schedule differs from paired case seeds")
    return inputs


def schedule(cases):
    if (len(cases) != 20 or len({case["label"] for case in cases}) != 20
            or len({case["needle"] for case in cases}) != 20
            or any(not re.fullmatch(r"[0-9a-f]{24}", case["needle"]) for case in cases)
            or len({seed for case in cases for seed in case["seeds"]}) != 40
            or any(len(case["seeds"]) != 2 for case in cases)):
        raise ValueError("fixture must have twenty distinct random receipts and forty unique paired seeds")
    rows = []
    for index, case in enumerate(cases):
        for repeat, seed in enumerate(case["seeds"]):
            rotation = (index + repeat) % len(ARMS)
            for arm in ARMS[rotation:] + ARMS[:rotation]:
                rows.append({
                    "run_id": f"{case['label']}/{repeat}/{arm}", "ordinal": len(rows),
                    "task_id": case["label"], "arm": arm, "repeat": repeat, "sampling_seed": seed,
                    "env": {
                        "ORCHESTRATOR_CONTEXT_ARM": arm,
                        "ORCHESTRATOR_CONTEXT_BUDGET_TOKENS": str(BUDGET),
                        "ORCHESTRATOR_CONTEXT_TRIGGER_FRACTION": "0.5",
                        "ORCHESTRATOR_CONTEXT_FORCE_TURNS": str(BOUNDARY_TURN),
                        "ORCHESTRATOR_CONTEXT_TRIAL_INDEX": str(repeat),
                        "ORCHESTRATOR_FRONTDOOR_REPL_NON_TOOL_N_TOKENS": "128",
                        "ORCHESTRATOR_TIMEOUTS_FRONTDOOR": "360",
                        "ORCHESTRATOR_TIMEOUTS_WORKER_SUMMARIZE": "360",
                        "ORCHESTRATOR_TIMEOUTS_WORKER_GENERAL": "360",
                        "ORCHESTRATOR_MAX_LOCK_HOLD_S": "390",
                    },
                })
    return rows


def task_prompt(case):
    return (
        f"Recover the exact receipt value from archive record {case['label']}. "
        f"For your first REPL turn, run exactly {RECORD_CODE} to print the one-time archive record. "
        f"For your second REPL turn, run exactly {CHECKPOINT_CODE} and wait for its response. "
        "After the checkpoint, if a Full log pointer is available, use a separate REPL turn with "
        "print(peek(500, file_path=...)) on that path to verify the original record. "
        "Then submit the exact receipt value (the 24 characters after receipt=) via FINAL. "
        "If you cannot recover it, submit FINAL('UNKNOWN'). Return one fenced Python block per turn."
    )


def seal(path, value):
    """Publish an immutable JSON receipt without overwriting an existing path."""
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
        pending = Path(stream.name)
        try:
            json.dump(value, stream, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
            path.hardlink_to(pending)
        finally:
            pending.unlink()


def files_digest(attempt):
    return {str(path.relative_to(attempt)): live.digest(path) for path in sorted(attempt.rglob("*"))
            if path.is_file() and not path.is_symlink() and path.name != "METRICS.json"}


def units(out, rows, packet_hash):
    found = []
    for row in rows:
        attempt = out / "units" / f"{row['ordinal']:03}"
        if not attempt.is_dir():
            continue
        metrics_path = attempt / "METRICS.json"
        if not metrics_path.exists():
            # The unit directory reserves the only sampling opportunity. A
            # keeper/host interruption preserves every byte and never replays it.
            seal(metrics_path, {"unit": row["run_id"], "status": "unknown", "correct": None,
                 "reason": "interrupted_before_immutable_trial_receipt", "completed": False,
                 "packet_sha256": packet_hash, "files_sha256": files_digest(attempt)})
        metric = live.read_json(metrics_path)
        if (metric["unit"] != row["run_id"] or metric["packet_sha256"] != packet_hash
                or metric["files_sha256"] != files_digest(attempt)):
            raise ValueError(f"immutable trial receipt mismatch: {attempt}")
        if "window" in metric:
            window = Path(metric["window"]).resolve()
            if window.parent != out.resolve() or not window.name.startswith("window-"):
                raise ValueError(f"trial names an unowned runtime window: {attempt}")
            if metric["runtime_sha256"] != runtime_digests(window):
                raise ValueError(f"runtime custody changed for trial: {attempt}")
        found.append(metric)
    return found


def summarize(rows, results):
    by_id = {result["unit"]: result for result in results}
    counts = {}
    for arm in ARMS:
        expected = [row["run_id"] for row in rows if row["arm"] == arm]
        observed = [by_id[unit] for unit in expected if unit in by_id]
        correct = sum(result["correct"] is True for result in observed)
        incorrect = sum(result["correct"] is False for result in observed)
        counts[arm] = {"scheduled": len(expected), "recorded": len(observed),
                       "completed": sum(result["completed"] for result in observed),
                       "eligible": correct + incorrect, "correct": correct, "incorrect": incorrect,
                       "unknown": len(observed) - correct - incorrect,
                       "unattempted": len(expected) - len(observed)}
    pairs = {}
    for row in rows:
        pair = pairs.setdefault((row["task_id"], row["repeat"]), {})
        pair[row["arm"]] = by_id.get(row["run_id"], {}).get("correct")
    paired = {"both_correct": 0, "both_incorrect": 0, "pointer_only_correct": 0,
              "summary_pointer_correct": 0, "unknown": 0}
    discordances = []
    for (task, repeat), pair in pairs.items():
        a, b = pair["pointer_only"], pair["summary_pointer"]
        if None in (a, b):
            paired["unknown"] += 1
        elif a == b:
            paired["both_correct" if a else "both_incorrect"] += 1
        else:
            paired["pointer_only_correct" if a else "summary_pointer_correct"] += 1
            discordances.append({"task_id": task, "repeat": repeat, **pair})
    complete = len(results) == len(rows)
    eligible = sum(arm["eligible"] for arm in counts.values())
    decision = "UNKNOWN"
    if complete and eligible == len(rows):
        decision = ("retain_pointer_only_candidate"
                    if counts["pointer_only"]["correct"] >= counts["summary_pointer"]["correct"]
                    else "fire_M-MP2")
    return {"recorded": len(results), "completed": sum(result["completed"] for result in results),
            "eligible": eligible, "scheduled": len(rows), "coverage_complete": complete,
            "eligibility_complete": eligible == len(rows), "decision": decision, "arms": counts,
            "paired": paired, "discordances": discordances, "results": results}


def run_trial(attempt, config, packet_hash, case, window, key, deadline):
    row = config["row"]
    seal(attempt / "INPUT.json", config)
    started = time.monotonic()
    completed = False
    try:
        with (attempt / "child.log").open("wb") as log:
            subprocess.run([str(live.PYTHON), "-B", str(HERE / "trial.py"), str(attempt)],
                           input=json.dumps(case).encode(), cwd=attempt, env=live.graph_env(row, attempt, key),
                           stdout=log, stderr=subprocess.STDOUT, check=True,
                           timeout=min(ATTEMPT_CAP_S, max(0.1, deadline - time.time())))
        completed = True
        result = assess(attempt, row, case)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        result = {"status": "unknown", "correct": None, "reason": f"{type(exc).__name__}: {exc}",
                  "instrument_error": True}
    receipt = {"unit": row["run_id"], "completed": completed, "packet_sha256": packet_hash,
               "attempt": str(attempt), "window": str(window), "runtime_sha256": runtime_digests(window),
               "wall_s": time.monotonic() - started, "files_sha256": files_digest(attempt), **result}
    seal(attempt / "METRICS.json", receipt)
    return receipt


def runtime_digests(window):
    return {name: live.digest(window / name) for name in (
        "WINDOW.json", "SERVER.json", "SERVER-PROPS.json", "SERVER-MODELS.json",
        "SERVER-SLOTS.json", "LINKAGE.txt")}


def run_window(out, rows, cases, inputs, dry, packet_hash):
    cpus = live.bind_four_cores()
    sys.path.insert(0, str(SOURCE))
    from scripts.benchmark import own_port_proof

    if not live.file_port_available(PORT) or own_port_proof.listen_inodes(PORT):
        raise ValueError("private listener port unavailable")
    window = Path(tempfile.mkdtemp(prefix="window-", dir=out))
    argv = live.server_argv(4, PORT)
    seal(window / "WINDOW.json", {"packet_sha256": packet_hash, "source": inputs["source"],
         "model": inputs["model_path"], "model_sha256": inputs["model_sha256"],
         "template_sha256": inputs["template_sha256"], "build_sha256": inputs["build_sha256"],
         "ggml_linkage_script_sha256": inputs["packet_sha256"]["verify_ggml_linkage.sh"],
         "affinity": cpus, "argv": argv, "grant_id": os.environ["FILLER_ID"], "dry_run": dry})
    deadline = min(int(os.environ["FILLER_DEADLINE"]), time.time() + TIME_CAP_S)
    key = secrets.token_urlsafe(24)
    env = {name: value for name, value in os.environ.items()
           if not name.startswith(("LLAMA_", "GGML_", "OMP_", "KMP_", "GOMP_"))}
    env.update(LD_LIBRARY_PATH=str(live.BIN.resolve()), LLAMA_API_KEY=key)
    signal.signal(signal.SIGTERM, live.handle_stop)
    signal.signal(signal.SIGINT, live.handle_stop)
    server_exited = False
    stopped = False
    error = None
    try:
        live.check_window(deadline)
        linkage = subprocess.run(["bash", str(HERE / "verify_ggml_linkage.sh"), argv[0], str(live.BIN.resolve())],
                                 env=env, check=True, capture_output=True, text=True, timeout=20)
        (window / "LINKAGE.txt").write_text(linkage.stdout)
        log_path = window / "server.log"
        with log_path.open("wb") as log:
            proc = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                with open(os.environ["FILLER_PIDFILE"], "a", encoding="utf-8") as pids:
                    pids.write(f"{proc.pid}\n")
                server = live.server_ready(proc, own_port_proof, key, min(deadline, time.time() + 160),
                                           log_path, port=PORT)
                seal(window / "SERVER.json", server)
                for row in rows:
                    live.check_window(deadline)
                    if not dry and deadline - time.time() < ATTEMPT_CAP_S + 15:
                        raise live.WindowEnded("remaining grant cannot fit a full bounded trial")
                    if proc.poll() is not None or not (own_port_proof.listen_inodes(PORT)
                                                       & own_port_proof.pid_socket_inodes(proc.pid)):
                        raise OSError("private listener ownership lost")
                    attempt = out / "units" / f"{row['ordinal']:03}"
                    attempt.mkdir()
                    case = cases[row["task_id"]]
                    config = {"row": row, "case": {"prompt": task_prompt(case)}, "source": str(SOURCE),
                              "temperature": live.TEMPERATURE, "endpoint": ENDPOINT, "smoke": True}
                    result = run_trial(attempt, config, packet_hash, case, window, key, deadline)
                    live.atomic_json(out / "PROGRESS.json", {"unit": result["unit"], "status": result["status"]})
                    if result.get("instrument_error"):
                        live.check_window(deadline)
                        raise ValueError(f"trial instrument failure: {result['reason']}")
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
        stopped, error = True, str(exc)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        error = f"{type(exc).__name__}: {exc}"
    seal(window / "EXIT.json", {"server_exited": server_exited, "stopped": stopped, "error": error,
         "server_log_sha256": live.digest(log_path) if (log_path := window / "server.log").is_file() else None})
    return server_exited, stopped, error


def run():
    env_id = os.environ.get("FILLER_ID", "")
    if not re.fullmatch(re.escape(ROW) + r"(?:-r[2-9][0-9]*|-r1[0-9]+)?", env_id):
        raise ValueError("rowflow grant or smoke environment required")
    inputs = verify()
    dry = os.environ.get("FILLER_DRYRUN") == "1"
    out = Path(os.environ["FILLER_DRYRUN_DIR"]) / "mp4-native" if dry else SCRATCH / "native"
    (out / "units").mkdir(parents=True, exist_ok=True)
    packet_hash = live.digest(HERE / "inputs.json")
    cases = {case["label"]: case for case in live.read_json(HERE / "cases.json")}
    rows = live.read_json(HERE / "schedule.json")
    if dry:
        rows = [next(row for row in rows if row["arm"] == "summary_pointer")]
    with (out / "run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        bound = out / "MATRIX.json"
        identity = {"packet_sha256": packet_hash, "schedule_sha256": live.digest(HERE / "schedule.json"),
                    "case_sha256": live.digest(HERE / "cases.json")}
        if bound.exists() and (dry or live.read_json(bound) != identity):
            raise ValueError("existing matrix does not match this sealed packet")
        if not bound.exists():
            seal(bound, identity)
        if not dry and (out / "RESULT.json").is_file():
            return complete()
        existing = {result["unit"] for result in units(out, rows, packet_hash)}
        remaining = [row for row in rows if row["run_id"] not in existing]
        server_exited, stopped, error = (run_window(out, remaining, cases, inputs, dry, packet_hash)
                                         if remaining else (True, False, None))
        results = units(out, rows, packet_hash)
        if dry:
            qualified = bool(server_exited and not error and len(results) == 1
                             and results[0]["correct"] is True and results[0]["summary_request"]
                             and results[0]["log_read_turns"]
                             and min(results[0]["log_read_turns"]) < results[0]["final_turn"])
            seal(out / ("SMOKE.json" if qualified else "PARTIAL.json"),
                 {"qualified": qualified, "server_exited": server_exited, "error": error, "results": results})
            return 0 if qualified else 1
        result = summarize(rows, results)
        result.update({"server_exited": server_exited, "error": error, "packet_sha256": packet_hash,
                       "unit": results[-1]["unit"] if results else None})
        if result["coverage_complete"] and server_exited and not error:
            seal(out / "RESULT.json", result)
            return 0
        live.atomic_json(out / "PARTIAL.json", result)
        return 75 if stopped else 1


def complete():
    path = SCRATCH / "native/RESULT.json"
    return int(not (path.is_file() and live.read_json(path)["coverage_complete"] is True))


def smoke_predicate():
    root = os.environ.get("FILLER_DRYRUN_DIR")
    try:
        started = float(os.environ.get("FILLER_SMOKE_T0", ""))
    except ValueError:
        return 1
    if not root or not math.isfinite(started) or started <= 0:
        return 1
    path = Path(root) / "mp4-native/SMOKE.json"
    return int(not (path.is_file() and path.stat().st_mtime >= started
                    and live.read_json(path)["qualified"] is True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("verify", "run", "smoke", "complete", "precondition"))
    mode = parser.parse_args().mode
    if mode == "verify":
        verify()
        return 0
    if mode == "precondition":
        return int(not live.file_port_available(PORT))
    return {"run": run, "smoke": smoke_predicate, "complete": complete}[mode]()


if __name__ == "__main__":
    sys.exit(main())
