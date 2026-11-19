#!/usr/bin/python3
"""Validate pinned inputs and execute one observation-only sealed lifecycle calibration."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

PACKET = Path(__file__).resolve().parent
SNAPSHOT = PACKET / "sources/root"
RUNNER = SNAPSHOT / "scripts/benchmark/kernel_promotion_resident_runner.py"
MODEL = Path("/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf")
BINARY = Path("/mnt/raid0/llm/kernels/builds/cpu-20260921-ffc1bac82/bin/llama-server")
EVIDENCE = SNAPSHOT / "scripts/benchmark/kernel_promotion_evidence.py"
BINARY_SHA = "4483bcfc92c5c3bb0005df31e1c668cb565d49f7b40ba94f4df5a126cbbb648c"
K35 = Path("/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/k35_stack_context_matrix_runner.py")
K35_SHA = "c519611dd834eddb18cf957e83501088f1f514e7c2690e974438c2706d990020"
REGION_LOCK = "/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock"
ID = "vb-v9-8-lifecycle-native-20261118"
OUT = PACKET / "out"
RESULT = OUT / "RESULT.json"
SMOKE_RESULT = OUT / "smoke" / f"{ID}.json"
TESTS = (
    "tests/test_kernel_promotion_resident_plan.py",
    "tests/test_kernel_promotion_resident_runner.py",
    "tests/test_kernel_promotion_fresh_replay.py",
    "tests/test_kernel_promotion_evidence.py",
    "tests/test_kernel_promotion_quality_parity.py",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_inputs():
    pins = read(PACKET / "pins.json")
    stat = MODEL.stat()
    identity = [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns]
    require(identity == pins["model_stat"], "model identity changed after the pre-grant digest")
    require((PACKET / "model.sha256").read_text().split() == [pins["model_sha256"], str(MODEL)],
            "model digest record differs from the pinned model identity")
    for path, expected in (
        (RUNNER, pins["runner_sha256"]),
        (PACKET / "plan.json", pins["plan_sha256"]),
        (PACKET / "cohorts.json", pins["cohorts_sha256"]),
        (BINARY, BINARY_SHA),
        (K35, K35_SHA),
    ):
        require(digest(path) == expected, f"digest changed: {path}")
    plan = read(PACKET / "plan.json")
    cohorts = plan["cohorts"]
    require(len(cohorts) == 1 and len(cohorts[0]["requests"]) == 20 and len(cohorts[0]["warmups"]) == 2,
            "expected one cohort with twenty requests and two arm-specific warmup templates")
    return plan


def evidence_pins():
    pins = read(PACKET / "pins.json")
    wanted = (
        "libggml-base.so.", "libggml-cpu.so.", "libggml.so.", "libllama.so.",
        "libllama-common.so.", "libllama-server-impl.so", "libmtmd.so.",
    )
    expected = {}
    for line in (PACKET / "sources/store-SHA256SUMS").read_text().splitlines():
        sha256, path = line.split()
        file = Path(path)
        if file.parent == Path("bin") and file.name.startswith(wanted):
            expected[file.name] = sha256
    require(len(expected) == len(wanted), "pinned CPU runtime needs seven hot libraries")
    image = {
        "binary_path": str(BINARY), "binary_sha256": BINARY_SHA, "libraries": expected,
        "commit": "ffc1bac82eeca6f9099e1ccd9ba49703c460a115", "server_version": 10303,
    }
    return {
        "source_manifest_sha256": digest(PACKET / "SOURCE.sha256"),
        "plan_sha256": pins["plan_sha256"], "k35_sha256": K35_SHA, "kv_mode": "split",
        "models": {str(MODEL): {"stat": pins["model_stat"], "sha256": pins["model_sha256"]}},
        "arms": dict.fromkeys(("production", "candidate"), image),
    }


def invocation(output, pins):
    return [
        sys.executable, "-I", "-B", str(RUNNER), "--compare-fresh", "--evidence-pins", str(pins),
        "--plan", str(PACKET / "plan.json"), "--output", str(output),
        "--k35-sha256", K35_SHA, "--production-binary", str(BINARY),
        "--production-sha256", BINARY_SHA, "--candidate-binary", str(BINARY),
        "--candidate-sha256", BINARY_SHA, "--kv-mode", "split", "--base-port", "19364",
        "--startup-timeout", "300", "--request-timeout", "120",
    ]


def smoke(plan, *, fixtures):
    attempt = OUT / "smoke" / uuid.uuid4().hex
    attempt.mkdir(parents=True)
    pins = attempt / "pins.json"
    write(pins, evidence_pins())
    result = subprocess.run(invocation(attempt / "unused-capture", pins), check=True,
                            capture_output=True, text=True, timeout=60)
    require(plan["schedule_sha256"] in result.stdout, "non-apply runner did not confirm the plan digest")
    report = {"ok": True, "mode": "validated-real-inputs-no-model-load",
              "schedule_sha256": plan["schedule_sha256"], "runner_stdout": result.stdout.strip()}
    if not fixtures:
        write(attempt / "dryrun.json", report)
        return 0
    cpus = os.environ["WS58_REGIONS"]
    expected = set()
    for piece in cpus.split(","):
        start, _, end = piece.partition("-")
        expected.update(range(int(start), int(end or start) + 1))
    require(len(expected) == 4 and os.sched_getaffinity(0) == expected,
            "fixture smoke requires the four CPU mask reserved by the keeper")
    cmd = ["/usr/bin/pytest", "-q", "-p", "no:cacheprovider",
           f"--basetemp={attempt / 'pytest-tmp'}", *TESTS,
           str(PACKET / "test_native_packet.py")]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    for key in ("PYTHONPATH", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"):
        env.pop(key, None)
    log = attempt / "pytest.log"
    with log.open("w") as stream:
        pytest = subprocess.run(cmd, cwd=SNAPSHOT, env=env, stdout=stream,
                                stderr=subprocess.STDOUT, timeout=180)
    print(log.read_text(), end="")
    report.update(pytest_exit=pytest.returncode, pytest_log=str(log), pytest_argv=cmd, cpus=cpus)
    require(pytest.returncode == 0, f"fixture pytest exit {pytest.returncode}; see {log}")
    write(SMOKE_RESULT, report)
    return 0


def verify_close(open_path, close_path, rc):
    opened, closed = read(open_path), read(close_path)
    require(closed["schema"] == "region-lock-claim.v1" and closed["phase"] == "close",
            "provider close receipt is malformed")
    require(closed["open_sha256"] == digest(open_path) and closed["claim_id"] == opened["claim_id"]
            and closed["open_path"] == str(open_path.resolve())
            and closed["provider_pid"] == opened["provider_pid"]
            and closed["provider_pid_starttime"] == opened["provider_pid_starttime"],
            "provider close receipt does not bind the open receipt")
    require(closed["child_rc"] == rc, "provider receipt and subprocess exit differ")
    return opened


def run(_plan):
    require(os.environ["FILLER_CPUS"] == "0-95", "grant CPU scope is not 0-95")
    if int(os.environ["FILLER_DEADLINE"]) - time.time() < 300 or Path(os.environ["FILLER_STOPFILE"]).exists():
        return 75
    OUT.mkdir(exist_ok=True)
    attempt = uuid.uuid4().hex
    prefix = OUT / f"claim-{attempt}"
    stage = OUT / f".capture-{attempt}"
    stage.mkdir(mode=0o700)
    capture = stage / "resident"
    sealed = OUT / f"sealed-{attempt}"
    pins = stage / "pins.json"
    write(pins, evidence_pins())
    for original, name in (("plan.json", "input-plan.json"), ("SOURCE.sha256", "SOURCE.sha256"),
                           ("model.sha256", "model.sha256")):
        shutil.copyfile(PACKET / original, stage / name)
    opened = prefix.with_suffix(".open.json")
    closed = prefix.with_suffix(".close.json")
    grants = Path(os.environ.get("FILLER_GRANTS_DIR", "/mnt/raid0/llm/tmp/compute-flags/grants"))
    cmd = [
        REGION_LOCK, "run", "--cpu-list", "0-95", "--role", "bench", "--tag", f"filler-{ID}",
        "--timeout-s", "1", "--claim-receipt-prefix", str(prefix),
        "--claim-grant-file", str(grants / f"{ID}.grant"), "--", *invocation(capture, pins),
        "--claim-open", str(opened), "--apply",
    ]
    proc = subprocess.run(cmd)
    if proc.returncode == 75 and not opened.exists():
        return 75
    try:
        receipt = verify_close(opened, closed, proc.returncode)
        shutil.copyfile(opened, stage / "provider.open.json")
        shutil.copyfile(closed, stage / "provider.close.json")
        shutil.copyfile(receipt["grant_copy_path"], stage / "provider.grant")
        if proc.returncode == 78:
            reports = [capture / "capture.json", capture / "fresh-replay/capture.json"]
            for path in reports:
                if path.is_file():
                    report = read(path)
                    if (str(report.get("failure", "")).startswith("InterruptedError(")
                            and report["cleanup_proved"] is True):
                        return 75
        tool = [sys.executable, "-I", "-B", str(EVIDENCE)]
        result = subprocess.run([*tool, str(stage), "--seal-to", str(sealed)], check=True,
                                capture_output=True, text=True, timeout=120)
        comparison = json.loads(result.stdout)
        native = subprocess.run([sys.executable, "-I", "-B", str(PACKET / "native_check.py"), str(sealed)],
                                check=True, capture_output=True, text=True, timeout=120)
        native_report = json.loads(native.stdout)
        write(OUT / f"native-check-{attempt}.json", native_report)
        verdict = {"exact": "diagnostic_complete", "different": "diagnostic_mismatch",
                   "incomplete": "diagnostic_incomplete"}[comparison["verdict"]]
        write(RESULT, {"unit_id": ID, "status": "complete", "verdict": verdict,
                       "sealed": str(sealed), "manifest_sha256": digest(sealed / "MANIFEST.json"),
                       "comparison": str(sealed / "comparison.json"),
                       "native_check": str(OUT / f"native-check-{attempt}.json"), "runner_exit": proc.returncode,
                       "resident_complete": comparison["resident_complete"],
                       "fresh_complete": comparison["fresh_complete"], "observation_only": True})
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        reason = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) and exc.stderr else str(exc)
        write(RESULT, {"unit_id": ID, "status": "failed", "verdict": "diagnostic_failure",
                       "reason": reason, "staging": str(stage), "claim_close": str(closed),
                       "runner_exit": proc.returncode, "observation_only": True})
        print(f"REFUSED: {reason}", file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    for flag in ("precond", "complete", "smoke-predicate"):
        mode.add_argument(f"--{flag}", action="store_true")
    args = parser.parse_args()
    try:
        if args.complete:
            record = read(RESULT)
            if (record["unit_id"] != ID or record["status"] != "complete"
                    or record["verdict"] not in {"diagnostic_complete", "diagnostic_incomplete", "diagnostic_mismatch"}
                    or record["observation_only"] is not True):
                return 1
            sealed = Path(record["sealed"])
            require(sealed.parent == OUT and sealed.name.startswith("sealed-")
                    and digest(sealed / "MANIFEST.json") == record["manifest_sha256"],
                    "sealed path or manifest identity changed")
            return subprocess.run([sys.executable, "-I", "-B", str(PACKET / "native_check.py"), str(sealed)],
                                  stdout=subprocess.DEVNULL, timeout=120).returncode
        if args.smoke_predicate:
            fresh = SMOKE_RESULT.stat().st_mtime >= int(os.environ["FILLER_SMOKE_T0"])
            record = read(SMOKE_RESULT)
            return 0 if fresh and record["ok"] is True and record["pytest_exit"] == 0 else 1
        plan = verify_inputs()
        if args.precond:
            return 0
        if os.environ.get("FILLER_SMOKE") == "1":
            return smoke(plan, fixtures=True)
        if os.environ.get("FILLER_DRYRUN") == "1":
            return smoke(plan, fixtures=False)
        return run(plan)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
