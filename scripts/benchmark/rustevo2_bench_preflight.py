#!/usr/bin/env python3
"""Preflight and command emitter for the RustEvo2 Strand verification run.

This helper intentionally does not launch llama-server or run the benchmark.
It verifies the host-side prerequisites that previously blocked Phase B and
prints copy-pastable commands for the exclusive inference window.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path("/mnt/raid0/llm/epyc-root")
RUSTEVO_ROOT = Path("/workspace/tmp/rustevo/RustEvo")
RUSTEVO_PYTHON = Path("/workspace/tmp/rustevo/.venv/bin/python")
DATASET = RUSTEVO_ROOT / "Dataset" / "RustEvo^2.json"
API_DOCS = RUSTEVO_ROOT / "Dataset" / "APIDocs.json"
EVAL_SCRIPT = RUSTEVO_ROOT / "Evaluate" / "eval_models_rq1.py"
LLAMA_SERVER = Path("/mnt/raid0/llm/llama.cpp/build/bin/llama-server")
IK_LLAMA_SERVER = Path("/mnt/raid0/llm/ik_llama.cpp/build/bin/llama-server")
GEMMA_DRAFT = Path("/mnt/raid0/llm/models/gemma-4-26B-A4B-it-assistant-Q8_0.gguf")
# The AutoPilot daemon holds an exclusive flock on this file by construction
# (epyc-orchestrator state_ownership.py), so it is the authoritative,
# argv-independent identity channel — a renamed binary or a drifted argv still
# holds the lock. Mirrors inference_load_check.py's AUTOPILOT_LOCK.
AUTOPILOT_LOCK = Path("/mnt/raid0/llm/epyc-orchestrator/orchestration/.autopilot.lock")
# Adjacency-robust: `start` may follow any number of flags after the script path
# (the specimen's failure was a flag inserted between `.py` and `start`), and the
# supervisor is a liveness signal in its own right — mirror the canonical
# launcher's dual pattern (start_authority_daemon.py).
AUTOPILOT_PATTERN = r"scripts/autopilot/autopilot\.py( .*)? start|autopilot_supervisor\.py"
REQUIRED_RUST = [
    "1.71.0",
    "1.72.0",
    "1.73.0",
    "1.74.0",
    "1.75.0",
    "1.76.0",
    "1.77.0",
    "1.78.0",
    "1.79.0",
    "1.80.0",
    "1.81.0",
    "1.82.0",
    "1.83.0",
    "1.84.0",
]


@dataclass(frozen=True)
class ModelRun:
    alias: str
    model_path: Path
    server_bin: Path
    extra_server_args: tuple[str, ...] = ()


MODEL_RUNS = [
    ModelRun(
        alias="strand-rust-coder-14b",
        model_path=Path("/mnt/raid0/llm/models/strand-rust/Strand-Rust-Coder-14B-v1.Q4_K_M.gguf"),
        server_bin=LLAMA_SERVER,
    ),
    ModelRun(
        alias="qwen2.5-coder-14b-instruct",
        model_path=Path("/mnt/raid0/llm/models/qwen2.5-coder-14b-base/Qwen2.5-Coder-14B-Instruct-Q4_K_M.gguf"),
        server_bin=LLAMA_SERVER,
    ),
    ModelRun(
        alias="gemma4-26b-a4b-worker-general",
        model_path=Path("/mnt/raid0/llm/models/gemma-4-26B-A4B-it-Q4_K_M.gguf"),
        server_bin=IK_LLAMA_SERVER,
        extra_server_args=(
            "-md",
            str(GEMMA_DRAFT),
            "--spec-type",
            "mtp",
            "--draft-max",
            "2",
            "--draft-p-min",
            "0.0",
            "--threads-draft",
            "16",
        ),
    ),
]


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=False, text=True, capture_output=True)


def require_path(path: Path, label: str, executable: bool = False) -> list[str]:
    if not path.exists():
        return [f"missing {label}: {path}"]
    if executable and not path.is_file():
        return [f"{label} is not a file: {path}"]
    if executable and not path.stat().st_mode & 0o111:
        return [f"{label} is not executable: {path}"]
    return []


def _autopilot_lock_held() -> bool | None:
    """True iff AutoPilot's singleton flock is held; False if provably free;
    None when the lock cannot be tested.

    Read-only, mirroring inference_load_check.py's _autopilot_lock_held(): the
    lock is tested and immediately released, nothing is written.
    """
    if not AUTOPILOT_LOCK.exists():
        return False
    try:
        import fcntl

        fd = os.open(str(AUTOPILOT_LOCK), os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)
            return False
        except (BlockingIOError, OSError):
            return True
        finally:
            os.close(fd)
    except Exception:  # noqa: BLE001 — any failure means we cannot confirm a negative
        return None


def autopilot_state() -> dict:
    """Three-state AutoPilot identity: present | absent | unobservable.

    OBS-5 (2026-08-12). The old check was two-state: an EMPTY pgrep result read
    as a confident 'no AutoPilot' and green-lit the bench against a live one, and
    a missing pgrep binary raised FileNotFoundError out of run() before the
    (0,1)-returncode handling was reached. Now, per inference_load_check.py's
    polarity rule ("for EXCLUSION, unknown must mean busy"):

      * present      — the flock is held, or a process matches either pattern.
      * absent       — pgrep RAN clean AND the flock is provably free. Both
                       channels must have spoken; an empty pattern result is
                       never trusted alone.
      * unobservable — pgrep missing/errored, or the flock untestable. Callers
                       must FAIL CLOSED on this state.

    The flock channel also closes the residual the reference implementation
    names in its registry row: argv drift now reads as `present` (the drifted
    daemon still holds the lock), never as a positive 'none'.
    """
    pgrep_ok = False
    lines: list[str] = []
    try:
        proc = run(["pgrep", "-af", AUTOPILOT_PATTERN])
    except FileNotFoundError:
        pgrep_ok = False
    else:
        if proc.returncode in (0, 1):
            pgrep_ok = True
            lines = [
                line for line in proc.stdout.splitlines()
                if "pgrep" not in line and "rustevo2_bench_preflight" not in line
            ]
    lock_held = _autopilot_lock_held()

    if lock_held is True:
        lock_detail = "flock held"
    elif lock_held is False:
        lock_detail = "flock provably free"
    else:
        lock_detail = "flock untestable"
    pgrep_detail = f"pgrep ran clean, {len(lines)} match(es)" if pgrep_ok else "pgrep unavailable or errored"
    detail = f"{pgrep_detail}; {lock_detail}"

    if lock_held is True or (pgrep_ok and lines):
        return {"state": "present", "lines": lines, "detail": detail}
    if pgrep_ok and lock_held is False:
        return {"state": "absent", "lines": [], "detail": detail}
    return {"state": "unobservable", "lines": [], "detail": detail}


def verify_rust_toolchains() -> list[str]:
    failures: list[str] = []
    if shutil.which("rustup") is None:
        return ["rustup is not on PATH"]
    for version in REQUIRED_RUST:
        proc = run(["rustup", "run", version, "rustc", "--version"])
        if proc.returncode != 0:
            failures.append(f"rust {version} unavailable: {proc.stderr.strip() or proc.stdout.strip()}")
    return failures


def verify_python_harness() -> list[str]:
    failures: list[str] = []
    proc = run([str(RUSTEVO_PYTHON), "-m", "py_compile", str(EVAL_SCRIPT), str(RUSTEVO_ROOT / "Evaluate" / "unit.py")])
    if proc.returncode != 0:
        failures.append(proc.stderr.strip() or proc.stdout.strip())
    help_proc = run([str(RUSTEVO_PYTHON), str(EVAL_SCRIPT), "--help"])
    if help_proc.returncode != 0:
        failures.append(help_proc.stderr.strip() or help_proc.stdout.strip())
    elif "--models" not in help_proc.stdout or "--max_workers" not in help_proc.stdout:
        failures.append("eval_models_rq1.py help does not expose --models and --max_workers")
    return failures


def output_dir(default_run_id: str) -> Path:
    return ROOT / "progress" / default_run_id[:7] / f"{default_run_id}-rustevo2"


def shell_quote(path: Path | str) -> str:
    text = str(path)
    if all(ch.isalnum() or ch in "/._-:=" for ch in text):
        return text
    return "'" + text.replace("'", "'\"'\"'") + "'"


def server_command(model: ModelRun, port: int, artifact_dir: Path) -> str:
    log_path = artifact_dir / f"server_{model.alias}.log"
    base = [
        "OMP_PROC_BIND=spread",
        "OMP_PLACES=cores",
        "OMP_WAIT_POLICY=active",
        "numactl",
        "--interleave=all",
        "--",
        "taskset",
        "-c",
        "0-95",
        str(model.server_bin),
        "-m",
        str(model.model_path),
        "-a",
        model.alias,
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "-np",
        "1",
        "-c",
        "32768",
        "-t",
        "96",
        "-fa",
        "on",
        "--no-mmap",
        "--jinja",
        *model.extra_server_args,
    ]
    return " ".join(shell_quote(part) for part in base) + f" > {shell_quote(log_path)} 2>&1 &"


def eval_command(model: ModelRun, port: int, artifact_dir: Path) -> str:
    output = artifact_dir / f"rq1_{model.alias}.json"
    parts = [
        "API_KEY=dummy",
        f"BASE_URL=http://127.0.0.1:{port}/v1",
        str(RUSTEVO_PYTHON),
        str(EVAL_SCRIPT),
        "--file_a",
        str(DATASET),
        "--file_b",
        str(API_DOCS),
        "--output",
        str(output),
        "--models",
        model.alias,
        "--max_workers",
        "1",
    ]
    return " ".join(shell_quote(part) for part in parts)


def render_commands(port: int, run_id: str) -> str:
    artifact_dir = output_dir(run_id)
    blocks = [
        "# Run only after AutoPilot and other inference jobs are stopped.",
        f"mkdir -p {shell_quote(artifact_dir)}",
        "",
    ]
    for model in MODEL_RUNS:
        blocks.extend(
            [
                f"# {model.alias}",
                server_command(model, port, artifact_dir),
                "SERVER_PID=$!",
                f"# Wait for http://127.0.0.1:{port}/health to report healthy before continuing.",
                eval_command(model, port, artifact_dir),
                "kill ${SERVER_PID}",
                "wait ${SERVER_PID} || true",
                "",
            ]
        )
    return "\n".join(blocks).rstrip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=9091)
    parser.add_argument("--run-id", default=dt.date.today().isoformat())
    parser.add_argument("--strict-host-quiet", action="store_true", help="Fail when AutoPilot is active")
    parser.add_argument("--commands", action="store_true", help="Print command blocks after validation")
    args = parser.parse_args()

    failures: list[str] = []
    for path, label, executable in [
        (RUSTEVO_ROOT, "RustEvo checkout", False),
        (RUSTEVO_PYTHON, "RustEvo Python", True),
        (DATASET, "RustEvo dataset", False),
        (API_DOCS, "RustEvo API docs", False),
        (EVAL_SCRIPT, "RustEvo RQ1 evaluator", False),
    ]:
        failures.extend(require_path(path, label, executable=executable))
    for model in MODEL_RUNS:
        failures.extend(require_path(model.model_path, f"{model.alias} model"))
        failures.extend(require_path(model.server_bin, f"{model.alias} server binary", executable=True))
    failures.extend(require_path(GEMMA_DRAFT, "Gemma MTP draft model"))
    failures.extend(verify_python_harness())
    failures.extend(verify_rust_toolchains())

    autopilot = autopilot_state()
    if autopilot["state"] == "unobservable":
        # FAIL CLOSED in BOTH modes — this is not a severity question. The
        # polarity rule (inference_load_check.py: "for EXCLUSION, unknown must
        # mean busy"): a bench must not launch when the host cannot be confirmed
        # AutoPilot-free. Only `absent` (both channels spoke) is a go.
        failures.append(
            "AutoPilot state UNOBSERVABLE — cannot confirm the host is AutoPilot-free; "
            "blocking the bench. (" + autopilot["detail"] + ")"
        )
    elif autopilot["state"] == "present":
        message = "AutoPilot appears active; do not launch RustEvo2 yet:\n" + "\n".join(autopilot["lines"])
        if args.strict_host_quiet:
            failures.append(message)
        else:
            print("WARNING:", message)

    if failures:
        print("RustEvo2 preflight FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("RustEvo2 preflight OK")
    print(f"artifact_dir={output_dir(args.run_id)}")
    print(f"port={args.port}")
    print("models=" + ",".join(model.alias for model in MODEL_RUNS))
    if args.commands:
        print()
        print(render_commands(args.port, args.run_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
