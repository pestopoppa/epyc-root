"""Rowflow-owned private frontdoor diagnostic for the frozen TOC-CMP-4 pilot."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from collections import Counter
from pathlib import Path

from analysis import calculate_baps

HERE = Path(__file__).resolve().parent
SCRATCH = Path("/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp4")
SOURCE = SCRATCH / "source"
PYTHON = Path("/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python")
SOURCE_SHA = "12afe2858f9dbd4691447926d6cf1864de64348c"
POINTS_SHA = "9de7e3bad1714675d1550421aa920840dc7ab7ff2ccb22dded16b853bad2655a"
MODEL = Path("/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf")
MODEL_SHA = "c1283d8b80c3e38b2735ddbc9766d3b3126f44d6c484be419d4e101d09a76131"
BIN = Path("/mnt/raid0/llm/kernels/production/cpu")
SERVER_SHA = "4483bcfc92c5c3bb0005df31e1c668cb565d49f7b40ba94f4df5a126cbbb648c"
TEMPLATE_SHA = "1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551"
TEMPLATE = MODEL.parent / "chat-templates/sha256" / f"{TEMPLATE_SHA}.jinja"
LINKAGE = Path("/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh")
ROW = "toc-cmp-4-pilot96-20261117"
PORT = 19359
ENDPOINT = f"http://127.0.0.1:{PORT}"
NSLOTS = 4
SLOT_CTX = 65536
PILOT_POINTS = 8
REPEATS = 4
PLANNED = 96
TEMPERATURE = 0.3
ATTEMPT_S = 480
STOP = False


class WindowEnded(BaseException):
    """Leave the upstream scheduler without counting a keeper stop as a drop."""


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def atomic_json(path, body):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(body, sort_keys=True, indent=2) + "\n")
    tmp.replace(path)


def read_json(path):
    return json.loads(path.read_text())


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def file_identity(path):
    stat = path.stat()
    return [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns]


def verify_source():
    def git(*args):
        return subprocess.check_output(["git", "-C", str(SOURCE), *args], text=True).strip()

    if git("rev-parse", "HEAD") != SOURCE_SHA or git("status", "--porcelain", "--untracked-files=no"):
        raise ValueError("orchestrator HEAD or tracked source differs from the frozen candidate")
    sys.path.insert(0, str(SOURCE))
    from scripts.benchmark import own_port_proof, toc_cmp4_runner

    return toc_cmp4_runner, own_port_proof


def build_pins():
    bin_dir = BIN.resolve()
    paths = [bin_dir / "llama-server", bin_dir / "libllama-server-impl.so", *sorted(bin_dir.glob("libggml*.so.*.*")),
             *sorted(bin_dir.glob("libllama*.so.*.*"))]
    actual = {str(path): digest(path) for path in paths if not path.is_symlink()}
    expected = {str(bin_dir.parent / rel): sha for sha, rel in (
        line.split(maxsplit=1) for line in (bin_dir.parent / "SHA256SUMS").read_text().splitlines()
        if line.strip()
    )}
    if actual.get(str(paths[0])) != SERVER_SHA or any(expected.get(p) != sha for p, sha in actual.items()):
        raise ValueError("production store binary/library digest mismatch")
    return actual


def verify_inputs(manifest):
    if manifest["model_stat"] != file_identity(MODEL):
        raise ValueError("GGUF custody changed since preparation")
    if manifest["build_sha256"] != build_pins() or digest(TEMPLATE) != TEMPLATE_SHA:
        raise ValueError("server build or template changed")
    for name, sha in manifest["packet_sha256"].items():
        if digest(HERE / name) != sha:
            raise ValueError(f"packet changed: {name}")


def prepare():
    runner, _ = verify_source()
    draw_path = SOURCE / "benchmarks/toc_cmp4/points-20261109.json"
    pool_path = SOURCE / "benchmarks/prompts/core_v2.jsonl"
    cases = {case["id"]: case for case in read_jsonl(pool_path) if "id" in case}
    draw = read_json(draw_path)
    if (runner.points_sha256(draw["points"]) != POINTS_SHA
            or runner.draw_points(cases, seed=draw["seed"]) != draw["points"]
            or runner.draw_reserves(cases, seed=draw["seed"]) != draw["reserves"]):
        raise ValueError("frozen point draw or reserve mismatch")
    model_stat = file_identity(MODEL)
    manifest_path = HERE / "inputs.json"
    prior = read_json(manifest_path) if manifest_path.exists() else {}
    cached = prior.get("model_sha256") == MODEL_SHA and prior.get("model_stat") == model_stat
    if (not cached and digest(MODEL) != MODEL_SHA) or model_stat != file_identity(MODEL):
        raise ValueError("GGUF content does not match the frontdoor registry")
    packet_names = ["runner.py", "graph_trial.py", "analysis.py", "launcher.sh", "spec.json"]
    atomic_json(manifest_path, {
        "source": SOURCE_SHA, "model_path": str(MODEL), "model_sha256": MODEL_SHA,
        "model_stat": model_stat, "build_sha256": build_pins(), "template_sha256": TEMPLATE_SHA,
        "packet_sha256": {name: digest(HERE / name) for name in packet_names if (HERE / name).is_file()},
        "points_source_sha256": digest(draw_path), "draw": draw, "pool_sha256": digest(pool_path),
    })


def check_window(deadline):
    if STOP or time.time() >= deadline or Path(os.environ["FILLER_STOPFILE"]).exists():
        raise WindowEnded("keeper STOP or deadline")


def file_port_available(port=PORT):
    try:
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(("127.0.0.1", port))
    except OSError:
        return False
    return True


def request(path, key, timeout=3, *, endpoint=ENDPOINT):
    req = urllib.request.Request(endpoint + path, headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def split_kv_observed(log):
    return bool(re.search(r"""kv_unified\s*=\s*(?:'false'|"false"|false|0)(?=\s|,|$)""", log))


def server_argv(threads, port=PORT):
    return [str(BIN / "llama-server"), "--model", str(MODEL), "--alias", MODEL.name, "--host", "127.0.0.1",
            "--port", str(port), "--threads", str(threads), "--threads-batch", str(threads),
            "--ctx-size", str(NSLOTS * SLOT_CTX), "--parallel", str(NSLOTS), "--slots",
            "--no-kv-unified", "-ctk", "q8_0", "-ctv", "q8_0", "-b", "2048", "-ub", "2048",
            "--n-gpu-layers", "0", "--jinja", "--reasoning", "off", "--chat-template-file", str(TEMPLATE),
            "--flash-attn", "on", "--spec-type", "draft-mtp", "--spec-draft-n-max", "4",
            "--cache-ram", "0", "--ctx-checkpoints", "32"]


def server_ready(proc, port_proof, key, deadline, log_path, *, port=PORT):
    endpoint = f"http://127.0.0.1:{port}"
    while True:
        check_window(deadline)
        if proc.poll() is not None:
            raise ValueError(f"private server exited with status {proc.returncode}; see {log_path}")
        if port_proof.listen_inodes(port) & port_proof.pid_socket_inodes(proc.pid):
            try:
                if request("/health", key, endpoint=endpoint)["status"] == "ok":
                    break
            except OSError:
                pass
        time.sleep(0.25)
    evidence = {}
    for name, path in (("props", "/props"), ("models", "/v1/models"), ("slots", "/slots")):
        evidence[name] = request(path, key, endpoint=endpoint)
        atomic_json(log_path.parent / f"SERVER-{name.upper()}.json", evidence[name])
    props, models, slots = (evidence[key] for key in ("props", "models", "slots"))
    actual_slots = [slot.get("n_ctx") for slot in slots]
    log = log_path.read_text(errors="replace")
    if (actual_slots != [SLOT_CTX] * NSLOTS or props.get("total_slots") != NSLOTS
            or Path(props.get("model_path", "")) != MODEL
            or [model["id"] for model in models["data"]] != [MODEL.name]
            or not split_kv_observed(log)):
        raise ValueError(f"served model, slot or split-KV pin mismatch: {actual_slots}")
    maps = Path(f"/proc/{proc.pid}/maps").read_text().splitlines()
    mapped = {Path(row.split()[-1]) for row in maps
              if re.search(r"/lib(?:ggml|llama)[^/ ]*\.so", row)}
    affinity = sorted(os.sched_getaffinity(proc.pid))
    if (Path(f"/proc/{proc.pid}/exe").resolve() != BIN.resolve() / "llama-server"
            or affinity != sorted(os.sched_getaffinity(0))
            or any(path.parent != BIN.resolve() for path in mapped)
            or not any(path.name.startswith("libggml-cpu.so") for path in mapped)
            or not any(path.name.startswith("libllama.so") for path in mapped)):
        raise ValueError("private server binary, affinity or mapped-library mismatch")
    return {"pid": proc.pid, "affinity": affinity, "model": models["data"][0],
            "n_ctx_per_slot": actual_slots, "kv_unified": False, "endpoint": endpoint,
            "mapped_libraries": sorted(map(str, mapped))}


def trajectory_metrics(events, row, *, smoke=False):
    finals = [event for event in events if event["event"] == "final"]
    if len(finals) != 1 or events[-1] != finals[0]:
        raise ValueError("missing or malformed final trajectory record")
    final = finals[0]
    expected = row["env"]
    for field, value in {
        "arm": row["arm"], "trial_index": row["repeat"],
        "context_budget_tokens": int(expected["ORCHESTRATOR_CONTEXT_BUDGET_TOKENS"]),
        "effective_context_budget_tokens": int(expected["ORCHESTRATOR_CONTEXT_BUDGET_TOKENS"]),
        "trigger_fraction": float(expected["ORCHESTRATOR_CONTEXT_TRIGGER_FRACTION"]),
        "history_valid": True,
    }.items():
        if final.get(field) != value:
            raise ValueError(f"trajectory pin mismatch: {field}")
    boundary_turn = int(expected["ORCHESTRATOR_CONTEXT_FORCE_TURNS"])
    boundaries = [event for event in events if event["event"] == "boundary"]
    if not boundaries:
        return {"boundary_reached": False, "baps": None, "terminal_state": final["terminal_state"]}
    if [event["turn"] for event in boundaries] != [boundary_turn]:
        raise ValueError("trajectory did not compact at exactly the assigned boundary")
    boundary = boundaries[0]
    # TOC-MP-3(b) specifies the numeric turns b+1 through b+5.
    turns = [event for event in events[events.index(boundary) + 1:]
             if event["event"] == "turn" and boundary_turn < event["turn"] <= boundary_turn + 5]
    if not turns and smoke:
        return {"boundary_reached": True, "baps": None, "actions": 0,
                "boundary": boundary, "terminal_state": final["terminal_state"]}
    if not turns or any(type(t.get("blocked")) is not bool or "log_follows" not in t
                        or "log_follow_attempts" not in t for t in turns):
        raise ValueError("missing post-boundary action or measurement fields")
    actions = [{"blocked": t["blocked"], "error": t["outcome"] == "error",
                "deliberate_reread": bool(t["log_follows"]) and t["outcome"] != "error"
                and t["tool_calls"]["execution"] == 0
                and t["tool_calls"]["retrieval"] == len(t["log_follows"])}
               for t in turns]
    score = calculate_baps(actions)
    blocked = sum(not action["deliberate_reread"] and (action["blocked"] or action["error"]) for action in actions)
    return {"boundary_reached": True, **score, "blocked_actions": blocked,
            "actions": len(turns), "log_follows": sum(len(t["log_follows"]) for t in turns),
            "log_follow_attempts": sum(len(t["log_follow_attempts"]) for t in turns),
            "boundary": boundary, "terminal_state": final["terminal_state"]}


def summarize_ledger(out, schedule, draw):
    records = read_jsonl(out / "ledger.jsonl")
    voided = {r["point_id"] for r in records if r["status"] == "void_point"}
    replacements = [r for r in records if r["status"] == "replacement"]
    strata = {p["point_id"]: p["stratum"] for p in draw["points"]}
    strata.update({p["point_id"]: p["stratum"] for group in draw["reserves"].values() for p in group})
    runs = []
    for rec in records:
        if "run_id" not in rec:
            continue
        point, arm, repeat = rec["run_id"].rsplit("|", 2)
        result = rec.get("result", {})
        valid = rec["status"] == "ok" and point not in voided
        runs.append({"run_id": rec["run_id"], "point_id": point, "stratum": strata[point], "arm": arm,
                     "repeat": int(repeat[1:]), "valid": valid, "status": rec["status"],
                     "baps": result.get("baps") if valid else None,
                     "correct": result.get("correct") if valid else None, "wall_s": result.get("wall_s"),
                     "attempts": rec.get("attempts"), "void_point": point in voided})
    temp = out / "RUNS.tmp"
    temp.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in runs))
    temp.replace(out / "RUNS.jsonl")
    active = {row["point_id"] for row in schedule} | {r["replacement"] for r in replacements}
    active -= voided
    expected = {(p, row["arm"], row["repeat"]) for p in active for row in schedule}
    observed = {(r["point_id"], r["arm"], r["repeat"]) for r in runs
                if r["point_id"] in active and r["status"] in {"ok", "dropped"}}
    dropped = sum(r["status"] == "dropped" and r["point_id"] not in voided for r in runs)
    completed = sum(r["valid"] for r in runs)
    return {"completed": completed, "processed": len(observed), "planned": PLANNED,
            "dropped": dropped, "drop_limit_exceeded": dropped * 10 > PLANNED,
            "active_points": sorted(active), "points_voided": sorted(voided),
            "voided_per_stratum": dict(Counter(strata[point] for point in voided)),
            "replacements": replacements, "reserve_exhausted": len(active) < PILOT_POINTS,
            "schedule_exhausted": observed == expected,
            "coverage_complete": len(active) == PILOT_POINTS and observed == expected and completed == PLANNED}


def graph_env(row, attempt, key):
    env = {k: v for k, v in os.environ.items() if k.startswith("FILLER_") or k in {"PATH", "LANG", "LC_ALL"}}
    env.update(row["env"])
    env.update({"TOC_CMP4_API_KEY": key, "PYTHONNOUSERSITE": "1", "TMPDIR": str(attempt),
                "ORCHESTRATOR_PATHS_TMP_DIR": str(attempt), "ORCHESTRATOR_TRAJECTORY_ARTIFACT_DIR": str(attempt),
                "ORCHESTRATOR_SESSION_SUMMARY_PROMPT": "openclaw_0e7b5c3"})
    return env


def run():
    if os.environ.get("FILLER_ID") != ROW:
        raise ValueError("rowflow grant/smoke environment required")
    dry = os.environ.get("FILLER_DRYRUN") == "1"
    out = Path(os.environ["FILLER_DRYRUN_DIR"]) / "cmp4-native" if dry else SCRATCH / "native"
    out.mkdir(parents=True, exist_ok=True)
    window = Path(tempfile.mkdtemp(prefix="window-", dir=out))
    manifest = read_json(HERE / "inputs.json")
    verify_inputs(manifest)
    runner, port_proof = verify_source()
    pool_path = SOURCE / "benchmarks/prompts/core_v2.jsonl"
    if digest(pool_path) != manifest["pool_sha256"]:
        raise ValueError("benchmark pool changed")
    cases = {case["id"]: case for case in read_jsonl(pool_path) if "id" in case}
    draw = manifest["draw"]
    schedule = runner.build_schedule(draw["points"][:PILOT_POINTS], repeats=REPEATS, seed=draw["seed"])
    if len(schedule) != PLANNED:
        raise ValueError("frozen pilot does not have 96 runs")
    cpus = sorted(os.sched_getaffinity(0))
    threads = int(os.environ["FILLER_THREADS"])
    if threads != 4 or len(cpus) != 4 or not file_port_available() or port_proof.listen_inodes(PORT):
        raise ValueError("expected four allocated threads and an unused private frontdoor port")
    deadline = int(os.environ["FILLER_DEADLINE"])
    argv = server_argv(threads)
    receipt = {"mode": "isolated_frontdoor_pilot", "registered_endpoint": "http://127.0.0.1:8070",
               "actual_endpoint": ENDPOINT, "source": SOURCE_SHA, "input_sha256": digest(HERE / "inputs.json"),
               "frozen_points_sha256": draw["points_sha256"], "reserves": draw["reserves"],
               "seed": draw["seed"], "pilot_schedule": schedule, "region": cpus, "argv": argv,
               "dry_run": dry, "temperature": TEMPERATURE}
    receipt_path = (window if dry else out) / "RECEIPT.json"
    if receipt_path.exists() and read_json(receipt_path) != receipt:
        raise ValueError("resume receipt differs from frozen run, serving build, or CPU region")
    atomic_json(receipt_path, receipt)
    key = secrets.token_urlsafe(24)
    server_env = {key: value for key, value in os.environ.items()
                  if not key.startswith(("LLAMA_", "GGML_", "OMP_", "KMP_", "GOMP_"))}
    server_env["LD_LIBRARY_PATH"] = str(BIN.resolve())
    server_env["LLAMA_API_KEY"] = key
    link = subprocess.run(["bash", str(LINKAGE), argv[0], str(BIN.resolve())], env=server_env,
                          check=True, capture_output=True, text=True, timeout=20)
    (window / "LINKAGE.txt").write_text(link.stdout)
    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)
    log_path = window / "server.log"
    error = None
    stopped = False
    smoke_result = None

    with log_path.open("wb") as log:
        proc = subprocess.Popen(argv, env=server_env, stdout=log, stderr=subprocess.STDOUT)
        try:
            with open(os.environ["FILLER_PIDFILE"], "a") as pids:
                pids.write(f"{proc.pid}\n")
            server = server_ready(proc, port_proof, key, min(deadline, time.time() + 160), log_path)
            atomic_json(window / "SERVER.json", server)

            def submit(row, smoke=False):
                check_window(deadline)
                if proc.poll() is not None or not (port_proof.listen_inodes(PORT) & port_proof.pid_socket_inodes(proc.pid)):
                    raise OSError("private listener ownership lost")
                if not smoke:
                    progress = summarize_ledger(out, schedule, draw)
                    if progress["drop_limit_exceeded"]:
                        raise WindowEnded("more than 10% of the nominal pilot schedule dropped")
                attempt = Path(tempfile.mkdtemp(prefix="trial-", dir=window))
                case = cases[row["task_id"]] if not smoke else {
                    "prompt": "Output only a Python code block calling FINAL(5).",
                }
                if case.get("image_path"):
                    atomic_json(attempt / "INPUT_UNAVAILABLE.json", {
                        "row": row, "reason": "image input requires a vision backend"})
                    raise ValueError(f"required image input unsupported; see {attempt}")
                atomic_json(attempt / "INPUT.json", {"row": row, "case": case, "source": str(SOURCE),
                    "temperature": TEMPERATURE, "endpoint": ENDPOINT, "smoke": smoke})
                started = time.monotonic()
                with (attempt / "child.log").open("wb") as child_log:
                    try:
                        subprocess.run([str(PYTHON), "-B", str(HERE / "graph_trial.py"), str(attempt)],
                                       cwd=attempt, env=graph_env(row, attempt, key), check=True,
                                       stdout=child_log, stderr=subprocess.STDOUT,
                                       timeout=min(ATTEMPT_S, max(0.1, deadline - time.time())))
                    except subprocess.SubprocessError as exc:
                        check_window(deadline)
                        raise OSError(f"graph trial failed; see {attempt / 'child.log'}") from exc
                check_window(deadline)
                graph = read_json(attempt / "GRAPH.json")
                path = attempt / "trial.trajectory.jsonl"
                metrics = trajectory_metrics(read_jsonl(path), row, smoke=smoke)
                result = {**metrics, "wall_s": time.monotonic() - started, "correct": graph["correct"],
                          "grade_reason": graph["grade_reason"], "trajectory": str(path),
                          "trajectory_sha256": digest(path), "graph": str(attempt / "GRAPH.json"),
                          "pins": {"model_pin": {"artifact": MODEL.name, "sha256": MODEL_SHA, "server": server},
                                   "build": {"orchestrator": SOURCE_SHA, "llama_server": SERVER_SHA, "template": TEMPLATE_SHA},
                                   "sampling_config": [wire["sampling"] for wire in graph["wire"]],
                                   "region": cpus, "prompt_hashes": [wire["prompt_sha256"] for wire in graph["wire"]],
                                   **{name: row["env"][name] for name in (
                                       "ORCHESTRATOR_CONTEXT_BUDGET_TOKENS", "ORCHESTRATOR_CONTEXT_TRIGGER_FRACTION")}}}
                atomic_json(attempt / "METRICS.json", result)
                if not smoke:
                    atomic_json(out / "PROGRESS.json", {"unit": row["run_id"], "boundary_reached": metrics["boundary_reached"]})
                return result

            if dry:
                smoke_row = next(row for row in schedule if row["arm"] == "pointer_only")
                smoke_result = submit(smoke_row, smoke=True)
            else:
                runner.run_schedule(schedule, submit, out / "ledger.jsonl", reserves=draw["reserves"],
                                    repeats=REPEATS, seed=draw["seed"])
        except WindowEnded as exc:
            stopped = True
            error = str(exc)
        except (OSError, ValueError, TypeError, LookupError, subprocess.SubprocessError) as exc:
            error = f"{type(exc).__name__}: {exc}"
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=6)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=6)

    if dry:
        if smoke_result is not None and error is None:
            atomic_json(out / "SMOKE.json", {"unit": smoke_row["run_id"], "server_exited": proc.poll() is not None,
                                           "transport_and_graph": True, "smoke": smoke_result})
            return 0
        print(error, file=sys.stderr)
        return 1
    result = summarize_ledger(out, schedule, draw)
    result.update({"error": error, "server_exited": proc.poll() is not None,
                   "scope": "isolated frontdoor, early-only timing and variance pilot"})
    if result["coverage_complete"] and not error:
        from analysis import analyze

        result["analysis"] = analyze(read_jsonl(out / "RUNS.jsonl"), "pilot", seed=draw["seed"])
        atomic_json(out / "RESULT.json", result)
        return 0
    atomic_json(out / "PARTIAL.json", result)
    return 0 if stopped and not result["drop_limit_exceeded"] else 1


def handle_stop(_signum, _frame):
    global STOP
    STOP = True


def smoke_predicate():
    try:
        started = float(os.environ.get("FILLER_SMOKE_T0", ""))
    except ValueError:
        return 1
    if not math.isfinite(started) or started <= 0:
        return 1
    root = os.environ.get("FILLER_DRYRUN_DIR")
    path = Path(root or ".") / "cmp4-native/SMOKE.json"
    if not root or not path.is_file():
        return 1
    data = read_json(path)
    return int(not (data.get("transport_and_graph") is True and data.get("server_exited") is True
                    and path.stat().st_mtime >= started))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run", "smoke", "complete", "precondition"))
    mode = parser.parse_args().mode
    if mode == "prepare":
        prepare()
        return 0
    if mode == "smoke":
        return smoke_predicate()
    if mode == "precondition":
        return int(not file_port_available())
    if mode == "complete":
        result_path = SCRATCH / "native/RESULT.json"
        return int(not (result_path.is_file() and read_json(result_path).get("coverage_complete") is True))
    return run()


if __name__ == "__main__":
    sys.exit(main())
