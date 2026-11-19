"""Execute and verify a prospective FM-4 gate for an exact native Codex dispatch."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import stat
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source"
ROW = "vb-fm4-codex-gate-20261118"
SCHEMA = "fm4.codex_gate.row.v1"
PIN_SCHEMA = "fm4.codex_gate.row_inputs.v1"
FM4 = "scripts/experiments/fm4"
TESTS = ["tests/experiments/test_fm4_codex_gate_canary.py",
         "tests/experiments/test_fm4_native_canary.py", "tests/experiments/test_fm4_codex_dispatch.py",
         "tests/vidya/test_fm4_gate_acceptance.py"]
TASK_ID = "VB-FM4-CODEX-GATE-CANARY"
IDENTITIES = ("parent_session_id", "dispatch_tool_use_id", "child_agent_id", "task_id")
ROLES = ("parent", "child")
CAP_S = 300
THREADS = 4
RULE = {"selected_gate_count": 1, "refusal_count": 0, "task_outcome_claim_count": 0,
        "gate_pass_count": 1}
WRITABLE = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH


class Refusal(Exception):
    pass


def sealed(path, expected, *, readonly=False):
    mode = path.lstat().st_mode
    if path.resolve(strict=True) != path or not stat.S_ISREG(mode):
        raise Refusal("input_not_canonical_regular_file")
    if readonly and mode & WRITABLE:
        raise Refusal("input_not_read_only")
    body = path.read_bytes()
    if hashlib.sha256(body).hexdigest() != expected:
        raise Refusal("input_digest_drift")
    return body


def pins(digest):
    plan = json.loads(sealed(ROOT / "source-pins.json", digest))
    if (plan["schema"] != PIN_SCHEMA or plan["task_id"] != TASK_ID
            or set(plan["identity"]) != set(IDENTITIES)
            or plan["identity"]["task_id"] != TASK_ID or plan["gate_tests"] != TESTS):
        raise Refusal("pin_schema_or_membership_drift")
    required = {*TESTS, "pytest.ini", "tests/conftest.py", "tests/vidya/conftest.py",
                *(f"{FM4}/{name}.py" for name in (
                    "native_canary", "run_gate", "task_acceptance", "codex_dispatch")),
                "scripts/vidya/adapters/fm4_gate_acceptance.py",
                "scripts/vidya/coordinator_fm4_context.py", "scripts/vidya/loop_beliefs.py"}
    if not isinstance(plan["files"], dict) or not required <= plan["files"].keys():
        raise Refusal("incomplete_source_closure")
    return plan


def verify_inputs(plan, checkpoint):
    for name, digest in plan["files"].items():
        checkpoint()
        relative = PurePosixPath(name)
        if relative.is_absolute() or str(relative) != name or ".." in relative.parts:
            raise Refusal("invalid_source_pin_path")
        sealed(SOURCE / relative, digest)
    for role in ROLES:
        checkpoint()
        item = plan[role]
        sealed(Path(item["path"]), item["sha256"], readonly=True)


def parse_deadline(raw):
    if re.fullmatch(r"[0-9]{1,12}", raw):
        return int(raw)
    if not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
        r"(?:\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])", raw
    ):
        raise Refusal("invalid_grant_deadline")
    return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()


def grant_affinity(raw):
    allocated = set()
    for field in raw.split(","):
        if not re.fullmatch(r"[0-9]{1,4}(?:-[0-9]{1,4})?", field):
            raise Refusal("invalid_grant_cpu_list")
        first, _, last = field.partition("-")
        start, end = int(first), int(last or first)
        if start > end:
            raise Refusal("invalid_grant_cpu_list")
        allocated.update(range(start, end + 1))
    cpus = sorted(allocated & os.sched_getaffinity(0))[:THREADS]
    if len(cpus) != THREADS:
        raise Refusal("insufficient_grant_cpu_affinity")
    os.sched_setaffinity(0, cpus)
    if os.sched_getaffinity(0) != set(cpus):
        raise Refusal("grant_cpu_affinity_drift")
    return cpus


def publish(path, content):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False, mode="w") as stream:
        staging = Path(stream.name)
        try:
            json.dump(content, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
            os.link(staging, path)
            directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            staging.unlink()


def stopped(signum, _frame):
    raise Refusal("deadline" if signum == signal.SIGALRM else "stop_requested")


def gate_argv(plan):
    return [sys.executable, "-B", "-m", "pytest", "-q", *plan["gate_tests"]]


def run_gate(plan, output, remaining):
    timeout = remaining() - 2
    if timeout <= 0:
        raise Refusal("insufficient_time_for_gate")
    command = [sys.executable, "-I", "-B", str(SOURCE / FM4 / "run_gate.py"),
               "--cwd", str(SOURCE), "--out", str(output), "--timeout-s", str(timeout)]
    for key in IDENTITIES:
        command.extend(["--" + key.replace("_", "-"), plan["identity"][key]])
    command.extend(["--", *gate_argv(plan)])
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
               PYTEST_ADDOPTS=f"--basetemp {output.parent / 'pytest-temp'} -o cache_dir={output.parent / 'pytest-cache'}")
    for name in ("PYTHONPATH", "PYTHONHOME", "PYTEST_PLUGINS"):
        env.pop(name, None)
    process = subprocess.Popen(command, cwd=SOURCE, env=env, start_new_session=True,
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
    try:
        while True:
            try:
                status = process.wait(timeout=min(0.25, remaining()))
                break
            except subprocess.TimeoutExpired:
                continue
    except BaseException:
        signal.setitimer(signal.ITIMER_REAL, 0)
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        raise
    if status:
        raise Refusal("gate_runner_refused")


def verify_gate(plan, canary, run_dir, native=None):
    acceptance = run_dir / "acceptance.json"
    accepted = canary["inputs"]["acceptance"]
    if accepted["path"] != str(acceptance):
        raise Refusal("acceptance_locator_drift")
    digest = accepted["sha256"]
    record = json.loads(sealed(acceptance, digest, readonly=True))
    execution_digest = accepted["execution_sha256"]
    execution = json.loads(sealed(acceptance.with_suffix(".json.execution.json"), execution_digest))
    snapshot = run_dir / "evidence" / (execution_digest + ".bin")
    sealed(snapshot, execution_digest, readonly=True)
    if (record["evidence"] != {"path": str(snapshot), "sha256": execution_digest}
            or execution["schema"] != "fm4.gate_execution.v1"
            or execution["argv"] != gate_argv(plan) or execution["cwd"] != str(SOURCE)
            or type(execution["returncode"]) is not int or execution["returncode"] != 0
            or execution["timed_out"] is not False or execution["launch_error"] is not None
            or record["schema"] != "fm4.task_acceptance.v1" or record["gate_result"] != "pass"
            or any(record[key] != value or execution[key] != value
                   for key, value in plan["identity"].items())):
        raise Refusal("execution_or_acceptance_drift")

    claim = canary["claim"]
    expected_claim = {"claim_id": f"clm_fm4-gate-acceptance:{digest}",
                      "locator": f"{acceptance}#sha256={digest}", "tier": "harness",
                      "source_kind": "fm4-gate-acceptance", "grade": "Judged/Located",
                      "unit": "gate_pass_indicator", "value": 1, "not_evidence": True}
    if (canary["schema"] != "fm4.codex_gate.native_canary.v1"
            or canary["consumer"] != "coordination.fm4" or canary["task_id"] != TASK_ID
            or canary["excluded_consumer"] != "autokernel.planner"
            or canary["identity"] != plan["identity"]
            or canary["gate_result"] != "pass" or canary["task_outcome"] is not None
            or any(canary["inputs"][role] != plan[role] for role in ROLES)
            or (native is not None and canary["dispatch"] != native)
            or any(claim.get(key) != value for key, value in expected_claim.items())):
        raise Refusal("unexpected_coordinator_gate_claim")
    for key in ("excluded_claim_count", "unrelated_consumer_claim_count", "task_outcome_claim_count"):
        if key in canary and (type(canary[key]) is not int or canary[key] != 0):
            raise Refusal("gate_claim_leaked_to_unrelated_context")

    state = canary["ledger_state"]
    frontier = {key: state[key] for key in ("ledger_path", "frame_count", "head_seq", "head_hash")}
    ledger = run_dir / "reader" / "ledger.jsonl"
    digest = hashlib.sha256(json.dumps(frontier, sort_keys=True).encode()).hexdigest()
    if (state["fresh"] is not True or state["ledger_path"] != str(ledger) or not ledger.is_file()
            or canary["ledger_state_digest"] != f"sha256:{digest}"):
        raise Refusal("coordinator_ledger_state_drift")


def qualifies(report, expected, plan):
    if (any(report.get(key) != value for key, value in expected.items())
            or report["status"] != "passed" or report["task_outcome"] is not None
            or any(type(report[key]) is not int or report[key] != value for key, value in RULE.items())):
        return False
    cpus = report["cpus"]
    if (not isinstance(cpus, list) or len(cpus) != THREADS
            or any(type(cpu) is not int or cpu < 0 for cpu in cpus) or cpus != sorted(set(cpus))):
        return False
    run_dir = Path(report["run_dir"])
    if (run_dir.parent != ROOT or run_dir.resolve(strict=True) != run_dir
            or not run_dir.name.startswith(f"{expected['mode']}-")):
        return False
    verify_gate(plan, report["canary"], run_dir)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "complete"))
    parser.add_argument("--pins-sha256", required=True)
    args = parser.parse_args()
    smoke = os.environ.get("FILLER_DRYRUN") == "1"
    mode = "publisher_smoke" if smoke else "official"
    dry_path = os.environ.get("FILLER_DRYRUN_RESULT_PATH")
    if smoke and not dry_path:
        return 1
    output = Path(dry_path) if smoke else ROOT / "official" / "RESULT.json"
    expected = {"schema": SCHEMA, "id": ROW, "mode": mode, "source_pins_sha256": args.pins_sha256}
    errors = (OSError, RuntimeError, ValueError, KeyError, TypeError, ImportError, Refusal)
    if args.action == "complete":
        try:
            return int(not qualifies(json.loads(output.read_bytes()), expected, pins(args.pins_sha256)))
        except errors:
            return 1

    report = dict(expected, status="unknown", selected_gate_count=0, refusal_count=1,
                  task_outcome_claim_count=None, gate_pass_count=0, task_outcome=None)
    run_dir = None
    try:
        if (os.environ.get("FILLER_ID") != ROW
                or not all(os.environ.get(key) for key in ("FILLER_STOPFILE", "FILLER_DEADLINE", "FILLER_CPUS"))):
            raise Refusal("missing_grant")
        stop = Path(os.environ["FILLER_STOPFILE"])
        wall_cutoff = parse_deadline(os.environ["FILLER_DEADLINE"])
        monotonic_cutoff = time.monotonic() + CAP_S

        def remaining():
            if stop.exists():
                raise Refusal("stop_requested")
            seconds = min(wall_cutoff - time.time(), monotonic_cutoff - time.monotonic())
            if seconds <= 0:
                raise Refusal("deadline")
            return seconds

        signal.signal(signal.SIGTERM, stopped)
        signal.signal(signal.SIGINT, stopped)
        signal.signal(signal.SIGALRM, stopped)
        signal.setitimer(signal.ITIMER_REAL, remaining())
        report["cpus"] = grant_affinity(os.environ["FILLER_CPUS"])
        for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
            os.environ[name] = str(THREADS)

        plan = pins(args.pins_sha256)
        verify_inputs(plan, remaining)
        sys.path.insert(0, str(SOURCE))
        from scripts.experiments.fm4 import codex_dispatch, native_canary

        parent, child = (Path(plan[role]["path"]) for role in ROLES)
        native = codex_dispatch.collect(parent, child)
        if (native["disposition"] != "terminal_child" or native["child_turn"]["state"] != "completed"
                or native["task_outcome"] is not None
                or dict(native["identity"], task_id=TASK_ID) != plan["identity"]
                or any(native["inputs"][role] != plan[role] for role in ROLES)):
            raise Refusal("native_dispatch_identity_or_terminal_drift")

        run_dir = Path(tempfile.mkdtemp(prefix=f"{mode}-", dir=ROOT))
        report["run_dir"] = str(run_dir)
        acceptance = run_dir / "acceptance.json"
        run_gate(plan, acceptance, remaining)
        remaining()
        canary = native_canary.run_codex_gate(child, parent, TASK_ID, acceptance, run_dir / "reader")
        verify_gate(plan, canary, run_dir, native)
        verify_inputs(plan, remaining)
        remaining()
        report.update(RULE, status="passed", canary=canary)
        publish(output, report)
        signal.setitimer(signal.ITIMER_REAL, 0)
    except errors as exc:
        signal.setitimer(signal.ITIMER_REAL, 0)
        reason = str(exc) if isinstance(exc, Refusal) else "input_gate_or_reader_refused"
        report.update(status="unknown", selected_gate_count=0, refusal_count=1,
                      task_outcome_claim_count=None, gate_pass_count=0, refusal=reason)
        partial = run_dir / "RESULT.partial.json" if run_dir else output.with_suffix(".partial.json")
        if not partial.exists():
            publish(partial, report)
        print(f"FM-4 Codex selected gate refused: {reason}")
        return 1
    print("FM-4 Codex selected gate bound one exact coordinator observation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
