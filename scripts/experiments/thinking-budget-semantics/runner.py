"""Capture native llama-server behavior for three registered thinking requests."""

import argparse
import fcntl
import http.client
import json
import math
import os
import secrets
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from prepare import (ARMS, BUILD, BUILD_PINS, COMMIT, MAX_TOKENS, PORT, REQUEST_S,
                     ROW, SCRATCH, STARTUP_S, WINDOW_S, check_digest, digest,
                     read_json, verify_packet)

RESULT = SCRATCH / "native/RESULT.json"
SMOKE_DIR = f"{ROW.rsplit('-', 1)[0]}-native"
SCHEMA = "epyc.thinking-budget-semantics.native.v1"
CHAT_PATH = "/v1/chat/completions"
RESPONSE_LIMIT = 1024 * 1024


def atomic_json(path, body):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
    temp.replace(path)


def verify():
    inputs = verify_packet(HERE)
    import cmp4_runner as live
    import own_port_proof as owner

    if (inputs["model_path"], inputs["model_sha256"], inputs["template_sha256"]) != (
        str(live.MODEL), live.MODEL_SHA, live.TEMPLATE_SHA,
    ) or live.BIN.resolve() != BUILD / "bin":
        raise ValueError("serving helper differs from the registered v10 identity")
    for name, sha in BUILD_PINS.items():
        check_digest(BUILD / name, sha)
    live.verify_inputs({**inputs, "packet_sha256": read_json(HERE / "sha256.json")})
    return inputs, live, owner


def read_terminal(payload, request):
    body = json.loads(payload)
    if body["object"] != "chat.completion" or body["model"] != request["model"]:
        raise ValueError("native response object or served model differs")
    choice, = body["choices"]
    reason = choice["finish_reason"]
    message = choice["message"]
    if reason not in {"stop", "length"} or message["role"] != "assistant":
        raise ValueError("native response lacks an ordinary final chat choice")
    reasoning, content = message.get("reasoning_content"), message.get("content")
    if any(value is not None and not isinstance(value, str) for value in (reasoning, content)):
        raise ValueError("native response chat text has an invalid type")
    usage = body["usage"]
    prompt, completion, total = (usage[name] for name in (
        "prompt_tokens", "completion_tokens", "total_tokens",
    ))
    if (any(type(count) is not int for count in (prompt, completion, total))
            or prompt <= 0 or not 0 < completion <= request["max_tokens"]
            or total != prompt + completion):
        raise ValueError("native usage is missing, inconsistent or outside the token cap")
    verbose = body["__verbose"]
    tokens = verbose["tokens"]
    if not isinstance(tokens, list) or not tokens or any(type(token) is not int for token in tokens):
        raise ValueError("native response lacks decoded token IDs")
    return {
        "finish_reason": reason,
        "usage": usage,
        "reasoning_field_present": "reasoning_content" in message,
        "reasoning_content": reasoning,
        "content": content,
        "reasoning_nonempty": bool(reasoning and reasoning.strip()),
        "token_ids": tokens,
        "n_token_ids": len(tokens),
        "raw_content": verbose.get("content"),
        "rendered_prompt": verbose.get("prompt"),
        "generation_settings": verbose.get("generation_settings"),
        "system_fingerprint": body.get("system_fingerprint"),
    }


def request_timed_out(_signum, _frame):
    raise TimeoutError("native request exceeded its wall allowance")


def capture(attempt, cell, key, deadline):
    request = cell["body"]
    wire = (json.dumps(request, sort_keys=True, separators=(",", ":")) + "\n").encode()
    (attempt / "REQUEST.json").write_bytes(wire)
    timeout = min(REQUEST_S, deadline - time.time())
    if timeout <= 0:
        raise TimeoutError("grant elapsed before the native request")
    connection = http.client.HTTPConnection("127.0.0.1", PORT, timeout=timeout)
    old_handler = signal.signal(signal.SIGALRM, request_timed_out)
    signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        connection.request("POST", CHAT_PATH, body=wire, headers={
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


def own_listener(process, owner):
    listeners = owner.listen_inodes(PORT)
    if process.poll() is not None or not listeners or not listeners <= owner.pid_socket_inodes(process.pid):
        raise ValueError("private listener is absent or is not owned by the captured process")


def stop_process(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=6)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=6)


def run_attempts(window, cells, process, owner, key, deadline, live, inputs, results):
    for ordinal, cell in enumerate(cells):
        attempt = window / f"attempt-{ordinal:02d}"
        attempt.mkdir()
        outcome = {"unit": cell["unit"], "attempt": str(attempt), "status": "UNKNOWN"}
        try:
            live.check_window(deadline)
            own_listener(process, owner)
            if inputs["model_stat"] != live.file_identity(live.MODEL):
                raise ValueError("GGUF custody changed before request")
            evidence = capture(attempt, cell, key, deadline)
            live.check_window(deadline)
            own_listener(process, owner)
            if inputs["model_stat"] != live.file_identity(live.MODEL):
                raise ValueError("GGUF custody changed during request")
            outcome.update(evidence, status="captured")
        except (live.WindowEnded, OSError, ValueError, KeyError, TypeError, http.client.HTTPException) as exc:
            outcome["error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            results.append(outcome)
            atomic_json(attempt / "OUTCOME.json", outcome)


def run_window(window, dry):
    results, error, exited = [], None, False
    manifest_sha = None
    window_errors = (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, http.client.HTTPException)
    planned = ARMS[:1] if dry else ARMS
    try:
        inputs, live, owner = verify()
        window_errors += (live.WindowEnded,)
        manifest_sha = digest(HERE / "sha256.json")
        deadline = min(int(os.environ["FILLER_DEADLINE"]), time.time() + WINDOW_S)
        cpus = live.bind_four_cores()
        if not live.file_port_available(PORT) or owner.listen_inodes(PORT):
            raise ValueError("private listener port is unavailable")
        argv = live.server_argv(4, PORT)
        key = secrets.token_urlsafe(24)
        env = {name: os.environ[name] for name in ("PATH", "LANG", "LC_ALL") if name in os.environ}
        env.update(LD_LIBRARY_PATH=str(live.BIN.resolve()), LLAMA_API_KEY=key,
                   FILLER_ID=os.environ["FILLER_ID"], FILLER_STOPFILE=os.environ["FILLER_STOPFILE"])
        signal.signal(signal.SIGTERM, live.handle_stop)
        signal.signal(signal.SIGINT, live.handle_stop)
        registration = read_json(HERE / "requests.json")
        cells = registration[:len(planned)]
        atomic_json(window / "WINDOW.json", {
            "schema": SCHEMA, "row": ROW, "smoke": dry, "inputs": inputs,
            "packet_manifest_sha256": manifest_sha,
            "source_commit": COMMIT, "argv": argv, "affinity": cpus,
            "library_path": env["LD_LIBRARY_PATH"], "effective_deadline": deadline,
            "request_wall_s": REQUEST_S, "max_tokens": MAX_TOKENS, "planned": planned,
        })
        live.check_window(deadline)
        linkage = subprocess.run(
            ["bash", str(HERE / "verify_ggml_linkage.sh"), argv[0], env["LD_LIBRARY_PATH"]],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=20,
        )
        (window / "LINKAGE.txt").write_bytes(linkage.stdout)
        linkage.check_returncode()
        log_path = window / "server.log"
        with log_path.open("wb") as log:
            process = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                with open(os.environ["FILLER_PIDFILE"], "a", encoding="utf-8") as pids:
                    pids.write(f"{process.pid}\n")
                server = live.server_ready(process, owner, key,
                                           min(deadline, time.time() + STARTUP_S), log_path, port=PORT)
                atomic_json(window / "SERVER.json", server)
                run_attempts(window, cells, process, owner, key, deadline, live, inputs, results)
            finally:
                stop_process(process)
                exited = process.poll() is not None and not owner.listen_inodes(PORT)
    except window_errors as exc:
        error = f"{type(exc).__name__}: {exc}"
    completed = sum(item["status"] == "captured" for item in results)
    ok = completed == len(planned) and exited and error is None
    report = {
        "schema": SCHEMA, "row": ROW, "status": "captured" if ok else "UNKNOWN",
        "window": str(window), "smoke": dry, "server_exited": exited, "error": error,
        "completed": completed, "planned": planned, "outcomes": results,
        "unattempted_unknown": list(planned[len(results):]),
        "unit": results[-1]["unit"] if results else None,
        "packet_manifest_sha256": manifest_sha,
        "files_sha256": {str(path.relative_to(window)): digest(path)
                         for path in sorted(window.rglob("*")) if path.is_file()},
    }
    name = ("SMOKE.json" if dry else "RESULT.json") if ok else "PARTIAL.json"
    atomic_json(window / name, report)
    if not dry:
        atomic_json(RESULT.parent / name, report)
    return 0 if ok else 75


def run():
    if os.environ.get("FILLER_ID") != ROW:
        raise ValueError("allocator-owned run environment required")
    dry = os.environ.get("FILLER_DRYRUN") == "1"
    out = Path(os.environ["FILLER_DRYRUN_DIR"]) / SMOKE_DIR if dry else RESULT.parent
    out.mkdir(mode=0o700, exist_ok=True)
    with (out / "run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not dry and any(out.glob("window-*")):
            raise ValueError("official probe already attempted")
        window = Path(tempfile.mkdtemp(prefix="window-", dir=out))
        return run_window(window, dry)


def qualified(path, planned, *, smoke, started=0):
    try:
        if path.stat().st_mtime < started:
            return False
        report = read_json(path)
        window = Path(report["window"])
        if smoke and path.parent != window:
            return False
        if (report["row"] != ROW or report["smoke"] is not smoke or report["status"] != "captured"
                or report["server_exited"] is not True or report["completed"] != len(planned)
                or report["packet_manifest_sha256"] != digest(HERE / "sha256.json")
                or [item["unit"] for item in report["outcomes"]] != list(planned)):
            return False
        registered = read_json(HERE / "requests.json")
        for ordinal, outcome in enumerate(report["outcomes"]):
            if outcome["status"] != "captured":
                return False
            for name in ("REQUEST.json", "RESPONSE.json", "OUTCOME.json"):
                relative = f"attempt-{ordinal:02d}/{name}"
                check_digest(window / relative, report["files_sha256"][relative])
            attempt = window / f"attempt-{ordinal:02d}"
            request = read_json(attempt / "REQUEST.json")
            if request != registered[ordinal]["body"] or read_json(attempt / "OUTCOME.json") != outcome:
                return False
            terminal = read_terminal((attempt / "RESPONSE.json").read_bytes(), request)
            if any(outcome.get(key) != value for key, value in terminal.items()):
                return False
        return True
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
    return int(not any(qualified(path, ARMS[:1], smoke=True, started=started)
                       for path in root.glob("window-*/SMOKE.json")))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("verify", "run", "smoke", "complete", "precondition"))
    mode = parser.parse_args().mode
    if mode == "verify":
        verify()
        return 0
    if mode == "precondition":
        import cmp4_runner as live
        import own_port_proof as owner
        return int(not live.file_port_available(PORT) or bool(owner.listen_inodes(PORT)))
    if mode == "complete":
        return int(not qualified(RESULT, ARMS, smoke=False))
    return {"run": run, "smoke": smoke}[mode]()


if __name__ == "__main__":
    sys.exit(main())
