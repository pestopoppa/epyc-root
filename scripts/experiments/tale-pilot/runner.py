"""Run the isolated PRB-T4 CPU instrument through its allocator entry point."""

import argparse
import fcntl
import http.client
import json
import math
import os
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import cmp4_runner as live
import confined_score
import eval_tale_budget as reference
import orch_debug_scorer as scorer
import own_port_proof as owner
from native_probe import atomic_json, read_terminal, request_timed_out, stop_process
from seal import (ANSWER_CAP, ARMS, BUILD, BUILD_PINS, CPU_COMMIT, PORT, REQUEST_S, ROW,
                  SCRATCH, SEED, STARTUP_S, TEMPERATURE, WINDOW_S, check_digest, digest,
                  read_json, verify_packet)

RESULT = SCRATCH / "native/RESULT.json"
SMOKE_DIR = f"{ROW}-native"
SCHEMA = "epyc.prb-t4.cpu-pilot.native.v1"
RESPONSE_LIMIT = 1024 * 1024
ESTIMATOR_S = 45
FAILURES = (live.WindowEnded, OSError, ValueError, KeyError, TypeError,
            http.client.HTTPException, subprocess.SubprocessError)


def verify():
    inputs, cases = verify_packet(HERE)
    if (inputs["model_path"], inputs["model_sha256"], inputs["template_sha256"]) != (
        str(live.MODEL), live.MODEL_SHA, live.TEMPLATE_SHA,
    ) or live.BIN.resolve() != BUILD / "bin":
        raise ValueError("native serving helper differs from registered v10 identity")
    for name, sha in BUILD_PINS.items():
        check_digest(BUILD / name, sha)
    live.verify_inputs({**inputs, "packet_sha256": read_json(HERE / "SHA256.json")})
    return inputs, cases


def request_body(case, arm, beta=None):
    question = case["prompt"]
    if arm == "baseline":
        prompt = question
    elif arm == "static":
        limit = reference.STATIC_LIMITS.get(case["suite"], reference.STATIC_LIMITS["general"])
        prompt = f"{limit}\n\n{question}"
    elif arm == "estimator":
        prompt = reference.TALE_PREPASS_PROMPT_TOKENS.format(question=question)
    elif arm == "tale" and type(beta) is int:
        prompt = reference.build_tale_prompt(question, beta, "tokens")
    else:
        raise ValueError("unknown arm or missing TALE estimator")
    return {
        "model": live.MODEL.name,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": reference.ESTIMATOR_MAX_TOKENS if arm == "estimator" else ANSWER_CAP,
        "temperature": TEMPERATURE,
        "seed": SEED,
        "stream": False,
        "cache_prompt": False,
        "verbose": True,
        "return_tokens": True,
        "chat_template_kwargs": {"enable_thinking": False},
    }


def capture(attempt, request, key, timeout, deadline):
    wire = (json.dumps(request, sort_keys=True, separators=(",", ":")) + "\n").encode()
    (attempt / "REQUEST.json").write_bytes(wire)
    timeout = min(timeout, deadline - time.time())
    if timeout <= 0:
        raise TimeoutError("grant elapsed before native request")
    connection = http.client.HTTPConnection("127.0.0.1", PORT, timeout=timeout)
    old_handler = signal.signal(signal.SIGALRM, request_timed_out)
    signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        connection.request("POST", "/v1/chat/completions", body=wire, headers={
            "Authorization": f"Bearer {key}", "Content-Type": "application/json",
            "Accept": "application/json", "Connection": "close",
        })
        with connection.getresponse() as response, (attempt / "RESPONSE.json").open("wb") as output:
            atomic_json(attempt / "HTTP.json", {"status": response.status,
                                                "headers": response.getheaders()})
            total = 0
            while chunk := response.read1(16384):
                output.write(chunk)
                total += len(chunk)
                if total > RESPONSE_LIMIT:
                    raise ValueError("native response exceeded the byte cap")
            if response.length not in (None, 0):
                raise ValueError("native response ended before its declared length")
            if response.status != 200:
                raise ValueError(f"native chat returned HTTP {response.status}")
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)
        connection.close()
    return read_terminal((attempt / "RESPONSE.json").read_bytes(), request)


def custody(process, inputs):
    listeners = owner.listen_inodes(PORT)
    if process.poll() is not None or not listeners or not listeners <= owner.pid_socket_inodes(process.pid):
        raise ValueError("private listener is absent or is not owned by the captured PID")
    if inputs["model_stat"] != live.file_identity(live.MODEL):
        raise ValueError("attested GGUF file identity changed")


def estimate(text):
    parsed = reference.parse_budget(text or "", "tokens")
    return {"beta": reference.BUDGET_CLAMPS["tokens"][2] if parsed is None else parsed,
            "fallback": parsed is None}


def score(attempt, case, text):
    config = case.get("scoring_config")
    method = case["scoring_method"]
    if not text:
        return {"correct": None, "scoring_error": "empty answer"}
    try:
        if method != "code_execution":
            correct = scorer.score_answer(text, case["expected"], method, config)
            return {"correct": correct}
        if not os.access("/sys/fs/cgroup", os.W_OK):
            return {"correct": None, "scoring_error": "confined scorer cgroup is unavailable"}
        sandbox_work = attempt / "scorer"
        sandbox_work.mkdir(mode=0o700)
        for name in ("scorer_child.py", "sandbox.py", "orch_debug_scorer.py"):
            shutil.copyfile(HERE / name, sandbox_work / name)
        original = confined_score.D
        confined_score.D = sandbox_work
        try:
            correct = confined_score.score(text, case)
            receipt = dict(confined_score.LAST)
        finally:
            confined_score.D = original
        verdict = {"correct": correct, "scoring_receipt": receipt}
        if correct is None:
            verdict["scoring_error"] = "confined scorer returned UNKNOWN"
        return verdict
    except (scorer.ScoringUnavailableError, OSError, ValueError, KeyError) as exc:
        return {"correct": None, "scoring_error": f"{type(exc).__name__}: {exc}"}


def schedule(cases, smoke):
    tasks = [(case, arm) for case in cases for arm in ARMS]
    return tasks[:1] if smoke else tasks


def unit(case, arm):
    return f"{case['suite']}/{case['id']}/{arm}"


def run_attempts(window, tasks, process, key, inputs, deadline, outcomes):
    estimates = {}
    for ordinal, (case, arm) in enumerate(tasks):
        attempt = window / f"attempt-{ordinal:02d}"
        attempt.mkdir()
        outcome = {"unit": unit(case, arm), "suite": case["suite"], "question_id": case["id"],
                   "arm": arm, "status": "UNKNOWN"}
        prepass = estimates.get(case["id"]) if arm == "tale" else None
        try:
            live.check_window(deadline)
            custody(process, inputs)
            request = request_body(case, arm, None if prepass is None else prepass["beta"])
            started = time.monotonic()
            outcome["started_epoch"] = time.time()
            try:
                evidence = capture(attempt, request, key,
                                   ESTIMATOR_S if arm == "estimator" else REQUEST_S, deadline)
            finally:
                outcome["wall_s"] = time.monotonic() - started
                outcome["ended_epoch"] = time.time()
            live.check_window(deadline)
            custody(process, inputs)
            if evidence["reasoning_nonempty"]:
                raise ValueError("thinking-disabled request returned a reasoning channel")
            outcome.update(evidence)
            if arm == "estimator":
                outcome.update(estimate(evidence["content"]))
                estimates[case["id"]] = outcome
            else:
                outcome.update(score(attempt, case, evidence["content"]))
            live.check_window(deadline)
            outcome["status"] = "captured"
        except (*FAILURES, RuntimeError) as exc:
            outcome["error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            outcomes.append(outcome)
            atomic_json(attempt / "OUTCOME.json", outcome)


def cost(outcome):
    usage = outcome["usage"]
    return {**{key: usage[key] for key in ("prompt_tokens", "completion_tokens", "total_tokens")},
            "wall_s": outcome["wall_s"]}


def metrics(outcomes):
    rows = {}
    for outcome in outcomes:
        row = rows.setdefault(outcome["suite"], {})
        if outcome["status"] != "captured":
            continue
        arm = outcome["arm"]
        observed = cost(outcome)
        if arm == "estimator":
            row[arm] = {**observed, "beta": outcome["beta"], "fallback": outcome["fallback"]}
            continue
        net = observed if arm != "tale" else {k: value + row["estimator"][k]
                                              for k, value in observed.items()}
        row[arm] = {"answer_only": observed, "including_estimator": net,
                    "correct": outcome["correct"], "finish_reason": outcome["finish_reason"]}
        if arm != "baseline":
            baseline = row["baseline"]["answer_only"]
            row[arm]["delta_from_baseline"] = {k: value - baseline[k] for k, value in net.items()}
        if arm == "tale":
            static = row["static"]["answer_only"]
            row[arm]["delta_from_static"] = {k: value - static[k] for k, value in net.items()}
    return rows


def run_window(window, smoke):
    outcomes, cleanup, error = [], {}, None
    manifest_sha = None
    tasks = schedule(read_json(HERE / "cases.json"), smoke)
    planned = [unit(case, arm) for case, arm in tasks]
    try:
        inputs, _ = verify()
        manifest_sha = digest(HERE / "SHA256.json")
        deadline = min(int(os.environ["FILLER_DEADLINE"]), time.time() + WINDOW_S)
        affinity = live.bind_four_cores()
        if not live.file_port_available(PORT) or owner.listen_inodes(PORT):
            raise ValueError("private listener port is unavailable")
        argv = live.server_argv(4, PORT)
        key = secrets.token_urlsafe(24)
        env = {name: os.environ[name] for name in ("PATH", "LANG", "LC_ALL") if name in os.environ}
        env.update(LD_LIBRARY_PATH=str(live.BIN.resolve()), LLAMA_API_KEY=key,
                   FILLER_ID=os.environ["FILLER_ID"], FILLER_STOPFILE=os.environ["FILLER_STOPFILE"])
        signal.signal(signal.SIGTERM, live.handle_stop)
        signal.signal(signal.SIGINT, live.handle_stop)
        atomic_json(window / "WINDOW.json", {
            "schema": SCHEMA, "row": ROW, "smoke": smoke, "inputs": inputs, "planned": planned,
            "packet_manifest_sha256": manifest_sha, "cpu_commit": CPU_COMMIT, "argv": argv,
            "affinity": affinity, "library_path": env["LD_LIBRARY_PATH"], "effective_deadline": deadline,
            "request_wall_s": REQUEST_S, "estimator_wall_s": ESTIMATOR_S,
        })
        live.check_window(deadline)
        linkage = subprocess.run(["bash", str(HERE / "verify_ggml_linkage.sh"), argv[0], env["LD_LIBRARY_PATH"]],
                                 env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
        (window / "LINKAGE.txt").write_bytes(linkage.stdout)
        linkage.check_returncode()
        log_path = window / "server.log"
        with log_path.open("wb") as log:
            process = subprocess.Popen(argv, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
            try:
                with open(os.environ["FILLER_PIDFILE"], "a", encoding="utf-8") as pids:
                    pids.write(f"{process.pid}\n")
                server = live.server_ready(process, owner, key,
                                           min(deadline, time.time() + STARTUP_S), log_path, port=PORT)
                atomic_json(window / "SERVER.json", server)
                run_attempts(window, tasks, process, key, inputs, deadline, outcomes)
            finally:
                stop_process(process)
                cleanup = {"pid": process.pid, "wait_returncode": process.returncode,
                           "listener_empty": not owner.listen_inodes(PORT), "finished_epoch": time.time()}
                atomic_json(window / "CLEANUP.json", cleanup)
                if process.poll() is None or not cleanup["listener_empty"]:
                    raise ValueError("private listener did not drain after captured PID exit")
    except (*FAILURES, RuntimeError) as exc:
        error = f"{type(exc).__name__}: {exc}"
    completed = sum(item["status"] == "captured" for item in outcomes)
    ok = completed == len(planned) and cleanup.get("listener_empty") and error is None
    report = {
        "schema": SCHEMA, "row": ROW, "smoke": smoke, "window": str(window),
        "status": "captured" if ok else "UNKNOWN", "error": error, "completed": completed,
        "planned": planned, "cleanup": cleanup, "outcomes": outcomes,
        "unattempted_unknown": planned[len(outcomes):], "suite_costs": metrics(outcomes),
        "unit": outcomes[-1]["unit"] if outcomes else None, "packet_manifest_sha256": manifest_sha,
        "files_sha256": {str(path.relative_to(window)): digest(path)
                         for path in sorted(window.rglob("*")) if path.is_file()},
    }
    name = ("SMOKE.json" if smoke else "RESULT.json") if ok else "PARTIAL.json"
    atomic_json(window / name, report)
    if not smoke:
        atomic_json(RESULT.parent / name, report)
    return 0 if ok else 75


def run():
    if os.environ.get("FILLER_ID") != ROW:
        raise ValueError("allocator-owned run environment required")
    smoke = os.environ.get("FILLER_DRYRUN") == "1"
    out = Path(os.environ["FILLER_DRYRUN_DIR"]) / SMOKE_DIR if smoke else RESULT.parent
    out.mkdir(mode=0o700, exist_ok=True)
    with (out / "run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not smoke and any(out.glob("window-*")):
            raise ValueError("official pilot already attempted")
        window = Path(tempfile.mkdtemp(prefix="window-", dir=out))
        return run_window(window, smoke)


def qualified(path, smoke, started=0):
    try:
        if path.stat().st_mtime < started or path.is_symlink():
            return False
        report = read_json(path)
        window = Path(report["window"])
        cases = read_json(HERE / "cases.json")
        planned = schedule(cases, smoke)
        cleanup = report["cleanup"]
        if ((path.parent != window if smoke else window.parent != RESULT.parent)
                or report["schema"] != SCHEMA or report["row"] != ROW or report["smoke"] is not smoke
                or report["status"] != "captured" or report["completed"] != len(planned)
                or type(cleanup["wait_returncode"]) is not int or not cleanup["listener_empty"]
                or cleanup["finished_epoch"] < started
                or report["packet_manifest_sha256"] != digest(HERE / "SHA256.json")
                or report["planned"] != [unit(case, arm) for case, arm in planned]):
            return False
        for name in ("WINDOW.json", "LINKAGE.txt", "SERVER.json", "CLEANUP.json"):
            check_digest(window / name, report["files_sha256"][name])
        if (cleanup != read_json(window / "CLEANUP.json")
                or cleanup["pid"] != read_json(window / "SERVER.json")["pid"]):
            return False
        betas = {}
        for ordinal, ((case, arm), outcome) in enumerate(zip(planned, report["outcomes"], strict=True)):
            attempt = window / f"attempt-{ordinal:02d}"
            for name in ("REQUEST.json", "RESPONSE.json", "HTTP.json", "OUTCOME.json"):
                relative = str((attempt / name).relative_to(window))
                check_digest(attempt / name, report["files_sha256"][relative])
            request = read_json(attempt / "REQUEST.json")
            terminal = read_terminal((attempt / "RESPONSE.json").read_bytes(), request)
            if (request != request_body(case, arm, betas.get(case["id"]))
                    or read_json(attempt / "OUTCOME.json") != outcome or outcome["status"] != "captured"
                    or outcome["unit"] != unit(case, arm) or read_json(attempt / "HTTP.json")["status"] != 200
                    or outcome["started_epoch"] < started or terminal["reasoning_nonempty"]
                    or any(outcome.get(key) != value for key, value in terminal.items())):
                return False
            if arm == "estimator":
                budget = estimate(terminal["content"])
                if any(outcome[k] != value for k, value in budget.items()):
                    return False
                betas[case["id"]] = budget["beta"]
        return report["suite_costs"] == metrics(report["outcomes"])
    except (OSError, ValueError, KeyError, TypeError):
        return False


def smoke():
    try:
        root = Path(os.environ["FILLER_DRYRUN_DIR"]) / SMOKE_DIR
        started = float(os.environ["FILLER_SMOKE_T0"])
    except (KeyError, ValueError):
        return 1
    if not math.isfinite(started) or started <= 0:
        return 1
    return int(not any(qualified(path, True, started) for path in root.glob("window-*/SMOKE.json")))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("verify", "run", "smoke", "complete", "precondition"))
    mode = parser.parse_args().mode
    if mode == "verify":
        verify()
        return 0
    if mode == "precondition":
        return int(not live.file_port_available(PORT) or bool(owner.listen_inodes(PORT)))
    if mode == "complete":
        return int(not qualified(RESULT, False))
    return {"run": run, "smoke": smoke}[mode]()


if __name__ == "__main__":
    sys.exit(main())
