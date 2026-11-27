"""Prepare one deterministic objective report for each eligible representative GPU arm."""

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

CASES = ("PAW-5", "DS41-W-66", "NARIQ-LIBTRELLIS-MAP-1", "PFXC-A3")
PROFILES = ("on-coding", "off-recommended")
ROWS = tuple(f"gpu-{case}-{profile}" for case in CASES for profile in PROFILES)
PFXC_DOC = "docs/research/qwen3.6-35b-a3b-q8-gpu-mtp-cache-sizing.md"
FAILURES = {"oracle_fail", "no_candidate", "scope_violation"}
CONFOUNDS = ("wire_failures", "assistant_errors", "error", "export_error", "stop_reason",
             "interrupt_receipt", "generation_unknown_requests", "generated_budget_exhausted")
ENVIRONMENT = ("modulenotfounderror", "no module named", "permission denied", "permissionerror",
               "operation not permitted", "resource temporarily unavailable", "no space left on device",
               "command not found", "timed out waiting for response headers", "connection refused",
               "read-only file system", "pinned source capture hash changed")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def read(path, expected=None):
    data = path.read_bytes()
    if expected is not None and sha(data) != expected:
        raise ValueError(f"frozen input hash differs: {path}")
    return data


def identity(pid):
    try:
        root = Path("/proc") / str(pid)
        fields = (root / "stat").read_text().rsplit(")", 1)[1].split()
        if fields[0] != "Z":
            return {"pid": pid, "start_ticks": int(fields[19]), "cmdline_sha256": sha((root / "cmdline").read_bytes())}
    except (FileNotFoundError, ProcessLookupError):
        pass
    return None


def load_inputs(policy):
    base = json.loads(read(Path(policy["base_approval"]), policy["base_approval_sha256"]))
    manifest = json.loads(read(Path(policy["quality_manifest"]), policy["quality_manifest_sha256"]))
    grid = json.loads(read(Path(policy["grid"]), manifest["grid_sha256"]))
    if (policy["maximum_recovery_rounds"] != 1 or tuple(policy["initial_rows"]) != ROWS
            or base["approved_by"] != "main" or base["quality_manifest_sha256"] != policy["quality_manifest_sha256"]
            or not set(ROWS).issubset(base["initial_rows"])):
        raise ValueError("unapproved feedback scope")
    rows = {row["id"]: row for row in grid["rows"] if row["backend"] == "gpu" and row["profile"] in PROFILES}
    if set(rows) != set(ROWS):
        raise ValueError("quality grid does not contain the exact representative GPU arms")
    migration_path = Path(policy["pfxc_migration"])
    migration = json.loads(read(migration_path, policy["pfxc_migration_sha256"]))
    oracle = migration_path.parent / migration["oracle"]
    read(oracle, migration["oracle_sha256"])
    if migration["case"] != "PFXC-A3" or migration["version"] != "pfxc.exact-events.v4":
        raise ValueError("PFXC objective checker migration differs")
    return base, rows, grid["cases"], migration, oracle


def prior_guidance(epoch, initial):
    unit = epoch / "units" / (initial + "-guidance-1")
    if unit.exists():
        return {"status": "already-consumed", "unit": str(unit)}
    for path in sorted((epoch / "guidance-approvals").glob("*.json")):
        try:
            plan = json.loads(read(path))
        except FileNotFoundError:
            continue
        if any(row.get("initial_row") == initial and row.get("ordinal") == 1
               for row in plan.get("guidance_rows", [])):
            return {"status": "already-queued", "approval": str(path)}
    return None


def decision(status, reason, **details):
    return {"status": status, "reason": reason, **details}


def objective(prior, result, row, case, migration, oracle, scratch):
    status = result["status"]
    if (any(result.get(key) for key in CONFOUNDS) or not result.get("initial_wire")
            or "error" in (result.get("assistant_finish_reasons") or [])):
        return None, {"reason": "harness_environment_or_transport_confounded"}
    if status == "no_candidate":
        return "No declared deliverable changed.", {}
    if status == "scope_violation":
        paths = (result.get("outside_scope") or []) + (result.get("unsafe_paths") or [])
        if not paths:
            return None, {"reason": "missing_scoped_failure_evidence"}
        return "Out-of-scope or unsafe paths remain: " + json.dumps(paths)[:500], {}

    score = result.get("oracle") or {}
    expected = case.get("active_oracle_sha256", case["oracle_sha256"])
    if score.get("oracle_sha256") != expected or score.get("rc") != (0 if status == "oracle_pass" else 1):
        return None, {"reason": "unverifiable_original_acceptance"}
    stdout = read(prior / "ORACLE.stdout.log", score["stdout_sha256"]).decode(errors="replace")
    stderr = read(prior / "ORACLE.stderr.log", score["stderr_sha256"]).decode(errors="replace")
    if any(marker in (stdout + stderr).lower() for marker in ENVIRONMENT):
        return None, {"reason": "acceptance_environment_failure"}
    if row["case"] == "PFXC-A3":
        changes = result.get("changed_files") or {}
        if list(changes) != [PFXC_DOC] or result.get("outside_scope") or result.get("unsafe_paths"):
            return None, {"reason": "no_closed_scoped_pfxc_candidate"}
        source = prior / "independent/work" / PFXC_DOC
        candidate_sha = changes[PFXC_DOC]["sha256"]
        candidate = read(source, candidate_sha)
        read(prior / "sandbox/work" / PFXC_DOC, candidate_sha)
        with tempfile.TemporaryDirectory(prefix="pfxc-v4-", dir=scratch) as clean:
            path = Path(clean) / PFXC_DOC
            path.parent.mkdir(parents=True)
            path.write_bytes(candidate)
            proc = subprocess.run([sys.executable, "-IB", str(oracle), clean], capture_output=True, timeout=30)
        read(source, candidate_sha)
        read(oracle, migration["oracle_sha256"])
        text = proc.stderr.decode(errors="replace").strip()
        receipt = {"candidate_sha256": candidate_sha, "oracle_sha256": migration["oracle_sha256"],
                   "acceptance_version": migration["version"], "rc": proc.returncode,
                   "stdout_sha256": sha(proc.stdout), "stderr_sha256": sha(proc.stderr)}
        if proc.returncode == 0:
            return None, {"reason": "passes_revised_acceptance", "pfxc_reassessment": receipt}
        if (proc.returncode != 1 or not text or "\n" in text or
                any(marker in text.lower() for marker in ENVIRONMENT)):
            return None, {"reason": "revised_acceptance_environment_or_ambiguous", "pfxc_reassessment": receipt}
        return "PFXC acceptance failed: " + text[:500], {"pfxc_reassessment": receipt}
    if status == "oracle_pass":
        return None, {"reason": "already_passes_acceptance"}
    failures = re.findall(r"^AssertionError:[ \t]*(.+)$", stderr, re.M)
    return "Acceptance assertion failed: " + (failures[-1][:500] if failures else "independent check returned nonzero"), {}


def select(policy, inputs, initial, scratch):
    _, rows, cases, migration, oracle = inputs
    epoch = Path(policy["epoch"])
    if existing := prior_guidance(epoch, initial):
        return existing, None
    prior = epoch / "units" / initial
    result_path = prior / "RESULT.json"
    if not result_path.exists():
        return decision("pending", "no_result_receipt"), None
    raw = read(result_path)
    result = json.loads(raw)
    terminal = result.get("terminal_at")
    if (not isinstance(terminal, (int, float)) or isinstance(terminal, bool)
            or not math.isfinite(terminal) or terminal <= 0
            or result.get("status") in {"starting", "running"}):
        return decision("pending", "nonterminal"), None
    row = rows[initial]
    if result.get("status") not in FAILURES | {"oracle_pass"}:
        return decision("skipped", "ineligible_terminal_status", initial_status=result["status"]), None
    if (result.get("manifest_sha256") != policy["quality_manifest_sha256"]
            or any(result.get(key) != row[key] for key in ("id", "case", "backend", "profile", "slot", "thinking", "sampling"))):
        return decision("skipped", "result_ancestry_mismatch"), None
    session_path = prior / "OPEN-CODE-SESSION.json"
    if not session_path.exists():
        return decision("skipped", "missing_terminal_session_receipt"), None
    session = read(session_path)
    export = json.loads(session)
    if (not result.get("session") or result["session"] != export.get("info", {}).get("id")
            or not isinstance(export.get("messages"), list)):
        return decision("skipped", "session_ancestry_mismatch"), None
    report, proof = objective(prior, result, row, cases[row["case"]], migration, oracle, scratch)
    if report is None:
        return {"status": "skipped", **proof}, None
    read(result_path, sha(raw))
    read(session_path, sha(session))
    return {"status": "eligible", "report": report, **proof}, (prior, sha(raw), sha(session))


@contextmanager
def queue_lock(epoch):
    with (epoch / "guidance-approvals/.deterministic-feedback-v5.lock").open("ab") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def stable_write(path, data):
    """Create an immutable file without replacing an existing file of the same name."""
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".policy-v5-", delete=False) as tmp:
        temp_path = Path(tmp.name)
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
    try:
        try:
            os.link(temp_path, path)
            return True
        except FileExistsError:
            return False
    finally:
        temp_path.unlink()


def publish(policy, inputs, initial, guard):
    epoch, output = Path(policy["epoch"]), Path(policy["output"])
    with queue_lock(epoch):
        if not guard():
            return decision("pending", "controller_stopped_before_publish")
        selection, ancestry = select(policy, inputs, initial, output)
        if ancestry is None:
            return selection
        prior, result_sha, session_sha = ancestry
        message = (
            "Continue the same approved task and scope. This deterministic acceptance report records the objective failure:\n\n"
            + selection["report"] + "\n\nCorrect the deliverable against the original brief and staged evidence, then run "
            "the task-local check. Preserve the staged references and independent check.\n"
        ).encode()
        feedback = output / f"{initial}-{result_sha[:12]}.txt"
        if not stable_write(feedback, message) and read(feedback) != message:
            raise ValueError(f"feedback collision: {feedback}")
        if not guard():
            return decision("pending", "controller_stopped_before_publish")
        if existing := prior_guidance(epoch, initial):
            return existing
        read(prior / "RESULT.json", result_sha)
        read(prior / "OPEN-CODE-SESSION.json", session_sha)
        base, *_ = inputs
        approval = {key: value for key, value in base.items() if key != "initial_rows"}
        approval["guidance_rows"] = [{
            "initial_row": initial, "ordinal": 1, "prior": str(prior),
            "prior_result_sha256": result_sha, "prior_session_sha256": session_sha,
            "feedback": str(feedback), "feedback_sha256": sha(message),
            "feedback_source": "deterministic acceptance report", "main_model_feedback_calls": 0,
        }]
        if "pfxc_reassessment" in selection:
            approval["acceptance_migration"] = policy["pfxc_migration"]
            approval["pfxc_reassessment"] = selection["pfxc_reassessment"]
        target = epoch / "guidance-approvals" / f"auto-{initial}.json"
        if not stable_write(target, json_bytes(approval)):
            return prior_guidance(epoch, initial) or decision("skipped", "approval_filename_collision")
        return {**selection, "status": "queued", "approval": str(target), "feedback_sha256": sha(message)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("policy", type=Path)
    parser.add_argument("--sha256", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--activate", action="store_true")
    args = parser.parse_args()
    policy = json.loads(read(args.policy, args.sha256))
    read(Path(__file__), policy["helper_sha256"])
    inputs = load_inputs(policy)
    previous = policy["predecessor"]
    controller = policy["controller"]
    def previous_active():
        return identity(previous["pid"]) == previous
    def controller_active():
        return identity(controller["pid"]) == controller and not (Path(policy["epoch"]) / "STOP").exists()
    if args.verify:
        print(json.dumps({"verified_rows": list(ROWS), "controller_active": controller_active(),
                          "predecessor_active": previous_active(), "queue_writes": 0}))
        return
    if policy.get("approved_by") != "main" or not controller_active() or previous_active():
        raise RuntimeError("activation requires main's exact policy approval, live owner, and stopped predecessor")
    output = Path(policy["output"])
    output.mkdir(parents=True, exist_ok=True)
    ledger = output / "DECISIONS.json"
    decisions = json.loads(read(ledger)) if ledger.exists() else {}
    guard = lambda: controller_active() and not previous_active()
    while guard():
        for initial in ROWS:
            if decisions.get(initial, {}).get("status") in {"queued", "already-queued", "already-consumed", "skipped"}:
                continue
            decision_row = publish(policy, inputs, initial, guard)
            if decision_row != decisions.get(initial):
                print(json.dumps({initial: decision_row}), flush=True)
                decisions[initial] = decision_row
        temp = ledger.with_suffix(".tmp")
        temp.write_bytes(json_bytes(decisions))
        os.replace(temp, ledger)
        if all(decisions.get(initial, {}).get("status") != "pending" for initial in ROWS):
            break
        time.sleep(1)
    print(json.dumps({"processed": decisions, "main_model_calls": 0}), flush=True)


if __name__ == "__main__":
    main()
