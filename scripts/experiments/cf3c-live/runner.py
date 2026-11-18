"""Run a fixed CF-3c replay pilot on a private allocator-owned CPU frontdoor."""
import argparse
import fcntl
import json
import math
import os
from pathlib import Path
import re
import secrets
import signal
import subprocess
import sys
import tempfile
import time
import http.client
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # Only the sealed packet, also under python -I.
import cmp4_runner as live
from prepare import BASE, HARNESS_REF, SCRATCH, SOURCE, WEIGHT_RECEIPT_SHA

ROW = "cf3c-pilot-20261118"
PORT = 19379
ENDPOINT = f"http://127.0.0.1:{PORT}"
SCHEMA = "epyc.cf3c.native.v1"
CONTEXT_BUDGET = 12288
DECODE_CAP = 96
CELL_CAP_S = 180
WINDOW_CAP_S = 3600
RESULT_PATH = SCRATCH / "native/RESULT.json"
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def source():
    def git(*args):
        return subprocess.check_output(["git", "-C", str(SOURCE), *args], text=True).strip()

    if git("rev-parse", "HEAD") != BASE or git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("orchestrator worktree differs from the pinned clean commit")
    sys.path.insert(0, str(SOURCE))
    import policies
    from scripts.benchmark import own_port_proof

    for module in (sys.modules["src.context_compression"], own_port_proof):
        if not Path(module.__file__).resolve().is_relative_to(SOURCE.resolve()):
            raise ValueError(f"dependency escaped pinned source: {module.__name__}")
    return policies, own_port_proof


def matrix(policies, cases):
    if [{k: c[k] for k in ("id", "steps", "target", "early")} for c in cases] != list(policies.CASES):
        raise ValueError("fixture dimensions disagree with the registered cases")
    seeds = [c["seed"] for c in cases]
    values = [v for c in cases for v in (c["answer"], *c["decoys"])]
    if (len(set(seeds)) != len(cases) or any(type(s) is not int or not 0 < s < 2**31 for s in seeds)
            or any(len(c["decoys"]) != c["steps"] for c in cases) or len(values) != len(set(values))
            or any(not re.fullmatch(r"[0-9a-f]{16}", value) for value in values)):
        raise ValueError("bad paired fixture")
    rows = []
    for index, case in enumerate(cases):
        for arm in policies.ARMS[index:] + policies.ARMS[:index]:
            rows.append({"unit": f"{case['id']}/{arm}", "ordinal": len(rows),
                         "case": case["id"], "arm": arm, "seed": case["seed"]})
    return rows


def verify():
    inputs = live.read_json(HERE / "inputs.json")
    if (inputs["source"] != BASE or inputs["cmp4_harness_ref"] != HARNESS_REF
            or inputs["cmp4_weight_receipt_sha256"] != WEIGHT_RECEIPT_SHA
            or live.digest(HERE / "prior-model-receipt.json") != WEIGHT_RECEIPT_SHA):
        raise ValueError("source, harness or retained weight receipt pin mismatch")
    receipt = live.read_json(HERE / "prior-model-receipt.json")
    if (inputs["model_path"] != str(live.MODEL) or inputs["model_sha256"] != live.MODEL_SHA
            or inputs["template_sha256"] != live.TEMPLATE_SHA
            or any(inputs[key] != receipt[key] for key in
                   ("model_path", "model_sha256", "model_stat", "template_sha256", "build_sha256"))):
        raise ValueError("prepared serving inputs do not match the original verified receipt")
    live.verify_inputs(inputs)
    policies, owner = source()
    cases = live.read_json(HERE / "cases.json")
    rows = matrix(policies, cases)
    return inputs, policies, owner, {c["id"]: c for c in cases}, rows


def post(attempt, event, path, payload, key, deadline):
    live.check_window(deadline)
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    request = urllib.request.Request(ENDPOINT + path, data=data, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json",
    })
    request_path = attempt / f"{event}.request.body"
    response_path = attempt / f"{event}.response.body"
    request_path.write_bytes(data)
    started = time.monotonic()
    status = None
    try:
        try:
            reply = HTTP.open(request, timeout=max(0.1, deadline - time.time()))
        except urllib.error.HTTPError as exc:
            reply = exc
        with reply:
            status = reply.status
            with response_path.open("wb") as body:
                while chunk := reply.read1(65536):
                    body.write(chunk)
                    live.check_window(deadline)
        if status != 200:
            raise ValueError(f"{path} returned HTTP {status}; see {response_path}")
        return live.read_json(response_path)
    finally:
        live.atomic_json(attempt / f"{event}.http.json", {
            "endpoint": path, "http_status": status, "wall_s": time.monotonic() - started,
            "request_sha256": live.digest(request_path),
            "response_sha256": live.digest(response_path) if response_path.exists() else None,
        })


def grade(reply, prompt_tokens, answer, max_tokens):
    if reply["model"] != live.MODEL.name or len(reply["choices"]) != 1:
        raise ValueError("native response model or choice count mismatch")
    choice = reply["choices"][0]
    usage = reply["usage"]
    if (usage["prompt_tokens"] != prompt_tokens or type(usage["completion_tokens"]) is not int
            or not 0 <= usage["completion_tokens"] <= max_tokens
            or usage["total_tokens"] != prompt_tokens + usage["completion_tokens"]):
        raise ValueError("native token usage does not reconcile with the served prompt and decode cap")
    finish = choice["finish_reason"]
    result = {"finish_reason": finish, "usage": usage, "correct": None, "answer": "NA"}
    if finish in ("length", "tool_calls"):
        return {**result, "status": "NA", "non_termination": 1}
    if finish != "stop" or choice["message"]["role"] != "assistant" or choice["message"].get("tool_calls"):
        raise ValueError(f"unexpected native final choice: {finish}")
    content = choice["message"].get("content")
    if not isinstance(content, str):
        raise ValueError("terminal answer has no textual content")
    answer_text = content.strip()
    if not answer_text or answer_text == "UNKNOWN":
        return {**result, "answer": answer_text or "NA", "status": "abstained", "non_termination": 0}
    return {**result, "answer": answer_text, "status": "graded", "non_termination": 0,
            "correct": answer_text == answer}


def cell(folder, row, case, policies, key, deadline, packet_hash, *, render_only=False):
    folder.mkdir()
    started = time.monotonic()
    deadline = min(deadline, time.time() + CELL_CAP_S)
    final = {"status": "UNKNOWN", "correct": None, "answer": "NA", "non_termination": None}
    limits = {"context_tokens": CONTEXT_BUDGET, "completion_tokens": DECODE_CAP,
              "cell_wall_s": CELL_CAP_S, "max_generation_requests": 1}
    try:
        original = policies.make_messages(case)
        live.atomic_json(folder / "original-messages.json", original)
        selected, policy = policies.apply_policy(original, row["arm"])
        live.atomic_json(folder / "policy.json", policy)
        req = {
            "model": live.MODEL.name, "messages": selected, "tools": policies.TOOLS,
            "tool_choice": "none", "seed": row["seed"], "temperature": 0.3, "cache_prompt": False,
            "max_tokens": DECODE_CAP, "stream": False,
            "chat_template_kwargs": {"enable_thinking": False, "preserve_reasoning": True},
        }
        rendered = post(folder, "template", "/apply-template", req, key, deadline)["prompt"]
        policies.verify_render(case, selected, rendered)
        if row["arm"] == "A0" and selected != original:
            raise ValueError("A0 mutated the control history")
        tokens = post(folder, "tokenize", "/tokenize",
                      {"content": rendered, "add_special": True, "parse_special": True}, key, deadline)["tokens"]
        prompt_tokens = len(tokens)
        if not prompt_tokens:
            raise ValueError("native tokenizer returned no prompt tokens")
        final["native_prompt_tokens"] = prompt_tokens
        if prompt_tokens + DECODE_CAP > CONTEXT_BUDGET:
            final.update(status="NA", finish_reason="context_budget", non_termination=1)
        elif render_only:
            final.update(status="rendered", finish_reason="no_generation_requested", non_termination=0)
        else:
            reply = post(folder, "completion", "/v1/chat/completions", req, key, deadline)
            final.update(grade(reply, prompt_tokens, case["answer"], DECODE_CAP))
    except live.WindowEnded:
        final["error"] = "keeper STOP or deadline"
        raise
    except (OSError, ValueError, TypeError, KeyError, http.client.HTTPException) as exc:
        final["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        evidence = {p.name: live.digest(p) for p in sorted(folder.iterdir())}
        final.update(row, schema=SCHEMA, category="CANDIDATE", instrument_class="bench", packet_sha256=packet_hash, source=BASE, limits=limits,
                     wall_s=time.monotonic() - started, evidence_sha256=evidence)
        live.atomic_json(folder / "TRAJECTORY.json", final)
    return final


def summarize(rows, results, arms):
    by_unit = {result["unit"]: result for result in results}
    paired = {}
    for row in rows:
        paired.setdefault(row["case"], {"seed": row["seed"], "arms": {}})["arms"][row["arm"]] = (
            by_unit.get(row["unit"], {"status": "unattempted", "correct": None})
        )
    output = {}
    for arm in arms:
        entries = [result for result in results if result["arm"] == arm]
        graded = [entry for entry in entries if entry["status"] == "graded"]
        measured = [entry["usage"]["total_tokens"] for entry in entries if "usage" in entry]
        correct = sum(entry["correct"] is True for entry in graded)
        output[arm] = {"scheduled": sum(row["arm"] == arm for row in rows), "attempted": len(entries), "graded": len(graded), "correct": correct,
                       "accuracy_among_graded": correct / len(graded) if graded else None,
                       "accuracy_over_attempted": correct / len(entries) if entries else None,
                       "non_termination": sum(entry["non_termination"] == 1 for entry in entries),
                       "NA": sum(entry["status"] == "NA" for entry in entries),
                       "abstained": sum(entry["status"] == "abstained" for entry in entries),
                       "UNKNOWN": sum(entry["status"] == "UNKNOWN" for entry in entries),
                       "tokens_cases": len(measured),
                       "mean_total_tokens": sum(measured) / len(measured) if measured else None,
                       "mean_wall_s": sum(entry["wall_s"] for entry in entries) / len(entries) if entries else None}
    return {"scheduled": len(rows), "recorded": len(results),
            "completed": sum(result["status"] in ("graded", "abstained", "NA") for result in results),
            "arms": output, "paired": paired}


def run():
    if os.environ.get("FILLER_ID") != ROW:
        raise ValueError("allocator grant or publisher smoke environment required")
    inputs, policies, owner, cases, rows = verify()
    dry = os.environ.get("FILLER_DRYRUN") == "1"
    out = Path(os.environ["FILLER_DRYRUN_DIR"]) / "cf3c-native" if dry else SCRATCH / "native"
    out.mkdir(mode=0o700, exist_ok=True)
    with (out / "run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not dry and any(out.glob("window-*")):
            raise ValueError("fixed diagnostic grant already attempted; retain partial results")
        return run_window(out, dry, inputs, policies, owner, cases, rows)


def run_window(out, dry, inputs, policies, owner, cases, rows):
    cpus = live.bind_four_cores()
    if not live.file_port_available(PORT) or owner.listen_inodes(PORT):
        raise ValueError("private listener port is unavailable")
    window = Path(tempfile.mkdtemp(prefix="window-", dir=out))
    packet_hash = live.digest(HERE / "inputs.json")
    argv = live.server_argv(4, PORT)
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("LLAMA_", "GGML_", "OMP_", "KMP_", "GOMP_"))}
    key = secrets.token_urlsafe(24)
    env.update(LD_LIBRARY_PATH=str(live.BIN.resolve()), LLAMA_API_KEY=key)
    deadline = min(int(os.environ["FILLER_DEADLINE"]), time.time() + WINDOW_CAP_S)
    signal.signal(signal.SIGTERM, live.handle_stop)
    signal.signal(signal.SIGINT, live.handle_stop)
    selected = [row for row in rows if row["case"] == "recent"] if dry else rows
    live.atomic_json(window / "WINDOW.json", {"schema": SCHEMA, "source": BASE, "packet_sha256": packet_hash,
         "grant": os.environ["FILLER_ID"], "inputs": inputs, "model_affinity": cpus, "argv": argv, "smoke": dry,
         "effective_deadline": deadline, "schedule": selected})
    results = []
    exited = False
    error = None
    try:
        live.check_window(deadline)
        linkage = subprocess.run(["bash", str(HERE / "verify_ggml_linkage.sh"), argv[0], str(live.BIN.resolve())],
                                 env=env, check=True, capture_output=True, text=True, timeout=20)
        (window / "LINKAGE.txt").write_text(linkage.stdout)
        server_log = window / "server.log"
        startup = time.monotonic()
        with server_log.open("wb") as log:
            proc = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                with open(os.environ["FILLER_PIDFILE"], "a", encoding="utf-8") as pids:
                    pids.write(f"{proc.pid}\n")
                server = live.server_ready(proc, owner, key, min(deadline, time.time() + 160), server_log, port=PORT)
                live.atomic_json(window / "SERVER.json", {**server, "startup_wall_s": time.monotonic() - startup})
                for row in selected:
                    live.check_window(deadline)
                    if not dry and deadline - time.time() < CELL_CAP_S + 12:
                        raise live.WindowEnded("remaining grant cannot fit a full cell")
                    if proc.poll() is not None or not (owner.listen_inodes(PORT) & owner.pid_socket_inodes(proc.pid)):
                        raise OSError("private listener ownership lost")
                    folder = window / f"cell-{row['ordinal']:02}"
                    try:
                        cell(folder, row, cases[row["case"]], policies, key, deadline, packet_hash,
                             render_only=dry and row["arm"] != "A0")
                    finally:
                        if (folder / "TRAJECTORY.json").is_file():
                            results.append(live.read_json(folder / "TRAJECTORY.json"))
                    status = results[-1]["status"]
                    live.atomic_json(out / "PROGRESS.json", {"schema": SCHEMA, "unit": row["unit"], "status": status})
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
    except (live.WindowEnded, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        error = f"{type(exc).__name__}: {exc}"
    seal = {str(path.relative_to(window)): live.digest(path)
            for path in sorted(window.rglob("*")) if path.is_file()}
    result = {**summarize(selected, results, policies.ARMS), "schema": SCHEMA, "source": BASE,
              "packet_sha256": packet_hash, "window": str(window), "window_sha256": seal, "server_exited": exited,
              "category": "CANDIDATE", "instrument_class": "bench",
              "error": error, "coverage_complete": len(results) == len(selected), "diagnostic_only": True,
              "unit": results[-1]["unit"] if results else None}
    if dry:
        result["qualified"] = (exited and error is None and len(results) == len(selected)
                               and all(r["status"] in (("graded", "abstained") if r["arm"] == "A0"
                                                      else ("rendered",)) for r in results))
        live.atomic_json(out / ("SMOKE.json" if result["qualified"] else "PARTIAL.json"), result)
        return int(not result["qualified"])
    complete = exited and error is None and result["coverage_complete"]
    live.atomic_json(out / ("RESULT.json" if complete else "PARTIAL.json"), result)
    return int(not complete)


def smoke():
    root = os.environ.get("FILLER_DRYRUN_DIR")
    try:
        started = float(os.environ.get("FILLER_SMOKE_T0", ""))
    except ValueError:
        return 1
    if not root or not math.isfinite(started) or started <= 0:
        return 1
    path = Path(root) / "cf3c-native/SMOKE.json"
    return int(not (path.is_file() and path.stat().st_mtime >= started
                    and live.read_json(path)["qualified"] is True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("dimensions", "verify", "run", "smoke", "complete", "precondition"))
    mode = parser.parse_args().mode
    if mode == "dimensions":
        policies, _ = source()
        print(json.dumps({"cases": policies.CASES, "arms": policies.ARMS}))
    elif mode == "verify":
        verify()
    elif mode == "precondition":
        return int(not live.file_port_available(PORT))
    elif mode == "complete":
        return int(not (RESULT_PATH.is_file() and live.read_json(RESULT_PATH)["coverage_complete"] is True))
    else:
        return {"run": run, "smoke": smoke}[mode]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
