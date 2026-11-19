#!/usr/bin/env python3
"""Keeper-only, one-arm GPQA-CoT driver with validated per-item checkpoints.

Inputs are prepared before publication. No weights are hashed in the grant.
The pinned v7 runner owns prompting, scoring and its native capture schema.
This driver owns process custody, cutoff, device evidence and consolidation.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import threading
import time
import urllib.request

SUITE = "gpqa_diamond_cot"
MANIFEST_SHA = "14e807dd11736b022f337466efc0fb5c95bf6e521a4514a09d0f25916524ecee"


class Cutoff(Exception):
    pass


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def prepare(config):
    """Validate small source pins and pre-verified weight stat identities."""
    for pin in config["sources"]:
        if digest(pin["path"]) != pin["sha256"]:
            raise ValueError(f"source pin changed: {pin['path']}")
    for pin in config["weights"]:
        stat = Path(pin["path"]).stat()
        if [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns] != pin["stat"]:
            raise ValueError(f"prepared weight identity changed: {pin['path']}")
    if digest(config["manifest"]) != MANIFEST_SHA:
        raise ValueError("manifest pin mismatch")
    questions = json.loads(Path(config["manifest"]).read_text())["suites"][SUITE]
    ids = [q["id"] for q in questions]
    if len(ids) != 198 or len(set(ids)) != 198 or any(not isinstance(i, str) or not i for i in ids):
        raise ValueError("expected exactly 198 unique nonempty question IDs")
    # One slot; byte-count bound reserves ample space for template overhead.
    if config["context"] < config["max_tokens"] + max(len(q["prompt"].encode()) for q in questions) + 2048:
        raise ValueError("insufficient context for prompt plus output and template reserve")
    return questions


class Budget:
    def __init__(self, deadline, stopfile, clock=time.time):
        self.deadline, self.stopfile, self.clock = deadline, Path(stopfile), clock
        self.interrupted = False

    def check(self):
        if self.interrupted or self.stopfile.exists() or self.clock() >= self.deadline:
            raise Cutoff("keeper cutoff: incomplete work is resumable")


def terminate(child):
    """Only a captured child PID is signalled; wait proves it was reaped."""
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=3)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=3)
    if child.poll() is None:
        raise RuntimeError(f"child {child.pid} survived cleanup")


def run_child(command, output, budget, timeout, observer=None, env=None, cwd=None):
    """Cancel in-flight requests on STOP, deadline, signal or request timeout."""
    budget.check()
    with Path(output).open("w") as log:
        child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env, cwd=cwd)
        end = time.monotonic() + timeout
        try:
            while True:
                budget.check()
                if time.monotonic() >= end:
                    raise TimeoutError("bounded child request timed out")
                if observer:
                    observer()
                try:
                    return child.wait(timeout=0.1)
                except subprocess.TimeoutExpired:
                    pass
        finally:
            terminate(child)


def residency(pid, library_dir):
    """Sample this server's mapped HIP backend, KFD process and allocated VRAM."""
    proc = Path(f"/proc/{pid}")
    maps = (proc / "maps").read_text()
    expected = str((Path(library_dir) / "libggml-hip.so").resolve())
    mapped = any(line.split()[-1] == expected for line in maps.splitlines() if line.split())
    approved = Path(library_dir).resolve()
    libraries = {line.split()[-1] for line in maps.splitlines() if line.split() and line.split()[-1].startswith("/")
                 and Path(line.split()[-1]).name.startswith(("libggml", "libllama"))}
    if any(not Path(p).resolve().is_relative_to(approved) for p in libraries):
        raise ValueError("foreign ggml/llama library mapped in captured server")
    kfd = Path(f"/sys/class/kfd/kfd/proc/{pid}")
    vram = sum(int(p.read_text().strip()) for p in kfd.glob("vram_*")) if kfd.exists() else 0
    if not mapped or not kfd.exists() or vram <= 0:
        raise ValueError("missing process-specific HIP/KFD/nonzero-VRAM residency")
    return {"at": time.time(), "pid": pid, "hip_library": expected, "vram_bytes": vram, "kfd": str(kfd)}


def context_capacity(log, expected):
    values = [int(v) for v in re.findall(r"\bn_ctx_per_seq\s*=\s*(\d+)", Path(log).read_text(errors="replace"))]
    if not values or any(v != expected for v in values):
        raise ValueError("actual per-slot context not established by runtime log")
    return expected


def load_runner(path):
    import sys
    sys.path.insert(0, str(Path(path).parent))
    spec = importlib.util.spec_from_file_location("gpqa_native_runner", path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    return runner


def validate_record(row, question, config, runner):
    if (row.get("id") != question["id"] or row.get("arm") != config["arm"]
            or row.get("seed") != 42 or row.get("rep") != 0
            or not runner.valid_resume_row(row, SUITE, question)):
        raise ValueError("invalid/stale/wrong-arm item capture")
    expected = {"endpoint": "chat", "request_path": "/v1/chat/completions", "temperature": 0.6,
                "top_p": 0.95, "top_k": 20, "enable_thinking": False}
    if row.get("effective_request") != expected:
        raise ValueError("effective sampler differs from declared protocol")
    if (row.get("extracted") != runner.extract_letter_answer(row["response"])
            or row.get("correct") != bool(row["response"] and runner.score_response(row["response"], question["expected"], question))
            or row.get("truncated") != (row.get("finish_reason") == "length")):
        raise ValueError("capture score/extraction/truncation differs from canonical scorer")
    if (not isinstance(row.get("prompt_tokens"), int) or row["prompt_tokens"] <= 0
            or row["prompt_tokens"] + config["max_tokens"] > config["context"]):
        raise ValueError("runtime prompt/output exceeds proven slot capacity")


def checkpoint(path, question, config, runner):
    value = json.loads(Path(path).read_text())
    if value.get("protocol") != fingerprint(config):
        raise ValueError("checkpoint protocol/model/source fingerprint changed")
    validate_record(value["record"], question, config, runner)
    samples = value.get("device_samples", [])
    if (len(samples) < 2 or any(s.get("vram_bytes", 0) <= 0 or not s.get("hip_library") or not s.get("kfd")
                               or s.get("slot_processing") is not True for s in samples)
            or samples[0]["at"] >= samples[-1]["at"]
            or any(s["pid"] != samples[0]["pid"] for s in samples)
            or not all(value["request_start"] <= s["at"] <= value["request_end"] for s in samples)):
        raise ValueError("missing overlapping two-sample device evidence")
    return value


def raw_record(path):
    records = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    if len(records) != 1:
        raise ValueError("one-item runner must produce exactly one record")
    return records[0]


def consolidate(questions, config, runner, out):
    values = [checkpoint(out / f"{i:03d}" / "accepted.json", q, config, runner) for i, q in enumerate(questions)]
    rows = [v["record"] for v in values]
    if len(rows) != 198 or len({r["id"] for r in rows}) != 198:
        raise ValueError("incomplete cohort; full verdict refused")
    return {"status": "complete", "arm": config["arm"], "protocol": fingerprint(config),
            "n": 198, "correct": sum(bool(r["correct"]) for r in rows),
            "accuracy": sum(bool(r["correct"]) for r in rows) / 198,
            "truncated": sum(bool(r["truncated"]) for r in rows),
            "noparse": sum(not r.get("extracted") for r in rows),
            "provenance": config, "items": values}


def execute(config, budget, out):
    # A failed revalidation must never leave a previous complete verdict visible.
    (out / "RESULT.json").unlink(missing_ok=True)
    questions = prepare(config)
    runner = load_runner(config["runner"])
    out.mkdir(parents=True, exist_ok=True)
    completed = {}
    for i, question in enumerate(questions):
        path = out / f"{i:03d}" / "accepted.json"
        if path.exists():
            completed[i] = checkpoint(path, question, config, runner)
    if len(completed) == 198:
        atomic_json(out / "RESULT.json", consolidate(questions, config, runner, out))
        return
    budget.check()
    cpus = os.environ["FILLER_CPUS"]
    threads = str(min(8, int(os.environ["FILLER_THREADS"])))
    port = int(os.environ["FILLER_PORTS"].split(",")[0])
    env = dict(os.environ, LD_LIBRARY_PATH=config["library_dir"], RUNNER_REQUEST_TIMEOUT_S="1800")
    server_log = out / "server.log"
    command = ["taskset", "-c", cpus, config["binary"], "--host", "127.0.0.1", "--port", str(port),
               "-m", config["model"], "-np", "1", "-c", str(config["context"]), "-t", threads, "-tb", threads,
               "-b", "2048", "-ub", "2048", "-ctk", "f16", "-ctv", "f16", "--device", "ROCm0", "-ngl", "99",
               "-fa", "on", "--reasoning", "off", "--slots", *config["spec_flags"]]
    atomic_json(out / "server-command.json", {"argv": command, "LD_LIBRARY_PATH": env["LD_LIBRARY_PATH"]})
    with server_log.open("w") as log:
        server = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env)
        try:
            if os.environ.get("FILLER_PIDFILE"):
                with open(os.environ["FILLER_PIDFILE"], "a") as pids:
                    pids.write(f"{server.pid}\n")
            end = time.monotonic() + 240
            while True:
                budget.check()
                if server.poll() is not None or time.monotonic() >= end:
                    raise RuntimeError("server failed or startup bound exceeded")
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=0.5) as response:
                        if response.status == 200:
                            break
                except OSError:
                    pass
                threading.Event().wait(0.1)
            context_capacity(server_log, config["context"])
            for i, question in enumerate(questions):
                budget.check()
                if i in completed:
                    continue
                item = out / f"{i:03d}"
                item.mkdir(exist_ok=True)
                # Preserve interrupted attempts; never feed a stale capture to native resume.
                attempt = item / str(time.time_ns())
                attempt.mkdir()
                source = Path(config["items_dir"]) / f"{i:03d}.json"
                if json.loads(source.read_text()) != {"suites": {SUITE: [question]}}:
                    raise ValueError("prepared split changed")
                samples = []
                start = time.time()

                def observe():
                    if server.poll() is not None:
                        raise RuntimeError("server died during request")
                    if len(samples) < 2 or time.time() - samples[-1]["at"] >= 1:
                        with urllib.request.urlopen(f"http://127.0.0.1:{port}/slots", timeout=0.5) as response:
                            slots = json.load(response)
                        if len(slots) != 1:
                            raise ValueError("expected one runtime slot")
                        if slots[0].get("is_processing") is True:
                            sample = residency(server.pid, config["library_dir"])
                            sample["slot_processing"] = True
                            samples.append(sample)

                args = [config["python"], "-B", config["runner"], "--host", "127.0.0.1", "--port", str(port),
                        "--suites", SUITE, "--n", "1", "--seed", "42", "--max-tokens", str(config["max_tokens"]),
                        "--repeats", "1", "--temperature", "0.6", "--top-p", "0.95", "--top-k", "20",
                        "--no-enable-thinking", "--endpoint", "chat", "--arm", config["arm"],
                        "--kernel", config["kernel"], "--binary", config["binary"], "--models", config["model"],
                        "--questions-in", str(source), "--per-question-out", str(attempt / "per_question.jsonl"),
                        "--output", str(attempt / "result.json")]
                rc = run_child(args, attempt / "runner.log", budget, 1800, observe, env, config["research_repo"])
                if rc:
                    raise RuntimeError(f"native runner exited {rc}")
                value = {"protocol": fingerprint(config), "record": raw_record(attempt / "per_question.jsonl"),
                         "request_start": start, "request_end": time.time(), "device_samples": samples}
                # Validate before publishing a resumable, atomic item checkpoint.
                atomic_json(attempt / "candidate.json", value)
                checkpoint(attempt / "candidate.json", question, config, runner)
                atomic_json(item / "accepted.json", value)
                # A real native item, retained in its own directory, is smoke progress.
                with (out / "progress.jsonl").open("a") as progress:
                    progress.write(json.dumps({"id": question["id"], "arm": config["arm"],
                                               "protocol": fingerprint(config), "item": str(item / "accepted.json"),
                                               "correct": value["record"]["correct"]}) + "\n")
                    progress.flush()
                    os.fsync(progress.fileno())
        finally:
            terminate(server)
    budget.check()
    atomic_json(out / "RESULT.json", consolidate(questions, config, runner, out))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if not os.environ.get("FILLER_ID"):
        parser.error("keeper grant environment required")
    budget = Budget(float(os.environ["FILLER_DEADLINE"]) - 10, os.environ["FILLER_STOPFILE"])

    def interrupt(signum, frame):
        budget.interrupted = True

    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    try:
        execute(json.loads(args.config.read_text()), budget, args.output)
    except Cutoff as exc:
        atomic_json(args.output / "partial.json", {"status": "partial", "reason": str(exc)})
        return 75
    except Exception as exc:
        atomic_json(args.output / "invalid.json", {"status": "invalid", "reason": str(exc)})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
