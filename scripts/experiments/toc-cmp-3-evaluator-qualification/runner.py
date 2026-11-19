#!/usr/bin/env python3
"""Screen a prospective CMP-3 evaluator rubric on four fixed controls."""

import argparse
import os
import signal
import subprocess
import time
import urllib.error
from pathlib import Path

import cmp2_runner as base
from controls import cases as fixed_controls
from rubric import evaluator_messages, response_schema
from semantic import (
    canonical,
    digest,
    import_judgment,
    read_bound,
    strict_json,
)

HERE = Path(__file__).resolve().parent
SCRATCH = Path("/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp3-evalqual-r3")
ROW = "toc-cmp-3-evalqual-20261118-r3"
PORT = 19368
ALIAS = "toc-cmp-3-evalqual-r3-qwen36-35b-a3b"
MAX_SECONDS = 2100
REQUEST_TIMEOUT = 420
CONTROL_COUNT = 4
SMOKE_UNITS = ("control/paraphrase", "control/missing-external-evidence")


def select_attempts(cases, dry):
    if dry:
        return [row for row in cases if row["case"]["unit"] in SMOKE_UNITS]
    return cases


def verify():
    manifest = strict_json((HERE / "inputs.json").read_bytes())
    body = {key: value for key, value in manifest.items() if key != "sha256"}
    if digest(canonical(body)) != manifest["sha256"]:
        raise ValueError("semantic inputs seal mismatch")
    for name, expected in manifest["packet_sha256"].items():
        read_bound(HERE / name, expected)
    for name, expected in manifest["build_sha256"].items():
        read_bound(Path(manifest["bin_dir"]) / name, expected)
    if base.file_identity(Path(manifest["model"]["path"])) != manifest["model"]["stat_at_hash"]:
        raise ValueError("preverified evaluator model identity changed")
    cases = strict_json((HERE / "cases.json").read_bytes())
    if len(cases) != CONTROL_COUNT or cases != fixed_controls():
        raise ValueError("evaluator schedule differs from the four fixed controls")
    return manifest, cases


def evaluate(row, evaluator_id, out, attempt, deadline):
    case = row["case"]
    path = out / f"attempt-{attempt:02d}"
    path.mkdir()
    body = {"model": ALIAS, "messages": evaluator_messages(case), "max_tokens": 2048,
            "stream": False, "temperature": 0.0, "seed": 31415926, "cache_prompt": False,
            "chat_template_kwargs": {"enable_thinking": False, "preserve_reasoning": True},
            "response_format": {"type": "json_object", "schema": response_schema(case)}}
    request = base.json_bytes(body)
    (path / "request.json").write_bytes(request)
    try:
        raw = base.http("/v1/chat/completions", min(REQUEST_TIMEOUT, base.remaining(deadline)), body=body)
    except urllib.error.HTTPError as exc:
        (path / "http-error.body").write_bytes(exc.read(1_000_000))
        raise
    (path / "response.json").write_bytes(raw)
    base.remaining(deadline)
    try:
        choices = strict_json(raw)["choices"]
        if len(choices) != 1 or choices[0]["finish_reason"] != "stop":
            raise ValueError("judge did not return one complete response")
        content = choices[0]["message"]["content"]
        if not isinstance(content, str):
            raise TypeError("judge response has no text")
        judgment = import_judgment(case, content.encode("utf-8"), evaluator_id)
    except (LookupError, TypeError, ValueError) as exc:
        judgment = import_judgment(case, None, evaluator_id)
        judgment.update(reason="invalid_evaluator_transport_response", detail=str(exc))
    judgment.update(request_sha256=digest(request), response_sha256=digest(raw), attempt=path.name)
    labels = {field: item["verdict"] for field, item in judgment["judgments"].items()}
    control_pass = "reason" not in judgment and labels == row["expected"]
    if case["unit"] == "control/folded-conflict":
        citations = judgment["judgments"]["pinned_governance"]["evidence"]
        text = case["observed_messages"][0]["content"]
        folded_start = text.index("[End contract]\n") + len("[End contract]\n")
        control_pass &= any(span["start_char"] >= folded_start for span in citations)
    judgment.update(expected=row["expected"], control_pass=control_pass)
    base.atomic_json(path / "VERDICT.json", judgment)
    return judgment


def stop(_signal, _frame):
    raise TimeoutError("row stop signal")


def run():
    if os.environ.get("FILLER_ID") != ROW:
        raise ValueError("evaluator qualification requires its rowflow-managed grant")
    dry = os.environ.get("FILLER_DRYRUN") == "1"
    out = Path(os.environ["FILLER_DRYRUN_DIR"]) / "cmp3-evalqual-r3-native" if dry else SCRATCH / "native"
    # Allow the retained preparation archive alongside fresh run files.
    out.mkdir(parents=True, exist_ok=True)
    if any(path.name != "prepared" for path in out.iterdir()):
        raise ValueError("prior evaluator qualification capture exists")
    deadline = min(time.time() + MAX_SECONDS, int(os.environ["FILLER_DEADLINE"]))
    manifest, cases = verify()
    attempts = select_attempts(cases, dry)
    results = []
    error = None
    server_exited = False
    proc = None
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    evaluator_id = f"{ALIAS}:inputs:{manifest['sha256']}"
    try:
        base.PORT = PORT
        cpus = base.bind_four_cores()
        bin_dir = Path(manifest["bin_dir"])
        server = str(bin_dir / "llama-server")
        server_env = {name: value for name, value in os.environ.items()
                      if not name.startswith(("LLAMA_", "GGML_", "OMP_", "KMP_", "GOMP_"))}
        server_env.update(LD_LIBRARY_PATH=str(bin_dir))
        linkage = subprocess.run(["bash", str(HERE / "verify_ggml_linkage.sh"), server, str(bin_dir)],
                                 env=server_env, check=True, capture_output=True, text=True, timeout=20)
        argv = [server, "--model", manifest["model"]["path"], "--alias", ALIAS, "--host", "127.0.0.1",
                "--port", str(PORT), "--threads", "4", "--threads-batch", "4", "--ctx-size", "16384",
                "--parallel", "1", "--n-gpu-layers", "0", "--jinja", "--reasoning", "off",
                "--chat-template-file", str(HERE / "chat-template.jinja"),
                "-ctk", "q8_0", "-ctv", "q8_0", "--flash-attn", "on", "--cache-ram", "0"]
        base.atomic_json(out / "RECEIPT.json", {
            "input_sha256": manifest["sha256"], "units": [row["case"]["unit"] for row in attempts],
            "evaluator_id": evaluator_id, "argv": argv, "affinity": cpus, "linkage": linkage.stdout,
        })
        base.remaining(deadline)
        with (out / "server.log").open("wb") as log:
            proc = subprocess.Popen(argv, env=server_env, stdout=log, stderr=subprocess.STDOUT)
            with Path(os.environ["FILLER_PIDFILE"]).open("a") as pids:
                pids.write(f"{proc.pid}\n")
            models = base.server_ready(proc, deadline)
            if [item["id"] for item in models["data"]] != [ALIAS]:
                raise ValueError("unexpected evaluator model")
            base.atomic_json(out / "SERVER.json", {"models": models, **base.server_identity(proc, bin_dir)})
            for index, row in enumerate(attempts, 1):
                if proc.poll() is not None or not base.owns_listener(proc.pid):
                    raise OSError("private evaluator listener ownership lost")
                outcome = evaluate(row, evaluator_id, out, index, deadline)
                results.append(outcome)
                if "reason" in outcome or outcome.get("control_pass") is False:
                    raise ValueError(f"invalid judge response or failed control: {outcome['unit']}")
                base.atomic_json(out / "PROGRESS.json", {"unit": outcome["unit"], "completed": len(results)})
    except (OSError, LookupError, ValueError, TypeError, subprocess.SubprocessError) as exc:
        error = f"{type(exc).__name__}: {exc}"
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        if proc is not None:
            try:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=5)
                server_exited = proc.poll() is not None
            except (OSError, subprocess.SubprocessError) as exc:
                error = f"private evaluator cleanup failed: {exc}"

    completed = sum("reason" not in outcome and outcome.get("control_pass") is not False for outcome in results)
    success = completed == len(attempts) and server_exited and error is None
    name = ("SMOKE.json" if dry else "RESULT.json") if success else "PARTIAL.json"
    base.atomic_json(out / name, {
        "unit": ROW, "completed": completed, "planned": len(attempts), "coverage_complete": success,
        "server_exited": server_exited, "error": error, "results": results,
        "unobserved": [row["case"]["unit"] for row in attempts[len(results):]],
        "scope": "fixed evaluator controls only",
    })
    return int(not success)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("verify", "run", "smoke", "complete"))
    args = parser.parse_args()
    if args.mode == "verify":
        verify()
        return 0
    if args.mode == "run":
        return run()
    if args.mode == "smoke":
        root = os.environ.get("FILLER_DRYRUN_DIR")
        if not root:
            return 1
        path = Path(root) / "cmp3-evalqual-r3-native/SMOKE.json"
        min_time = float(os.environ["FILLER_SMOKE_T0"])
        expected = len(SMOKE_UNITS)
        if not path.is_file() or path.stat().st_mtime < min_time:
            return 1
    else:
        path = SCRATCH / "native/RESULT.json"
        expected = CONTROL_COUNT
    if not path.is_file():
        return 1
    result = strict_json(path.read_bytes())
    units = SMOKE_UNITS if args.mode == "smoke" else tuple(
        row["case"]["unit"] for row in fixed_controls())
    return int(not (
        result["unit"] == ROW and result["completed"] == result["planned"] == expected
        and result["coverage_complete"] is True and result["server_exited"] is True
        and result["error"] is None and result["unobserved"] == []
        and tuple(outcome["unit"] for outcome in result["results"]) == units
        and all(outcome["control_pass"] is True for outcome in result["results"])
    ))


if __name__ == "__main__":
    raise SystemExit(main())
