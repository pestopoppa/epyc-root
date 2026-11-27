"""Start only an approved persistent callback once its exact slot owners drain."""
import argparse
from contextlib import contextmanager
import fcntl
from hashlib import file_digest
import importlib.util
import json
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
COVERAGE = HERE.parent
SOURCE_ROOT = COVERAGE / "persistent-callback"
SOURCE_SEAL = "e203f1389e8753223da7ff9623ce67fad0f627716dd735c39117cce8344c5803"
W66_ROOT = COVERAGE / "persistent-w66-light-12"
STOP = threading.Event()

PREDECESSORS = {
    "w66-off": ("light-01", "gpu-DS41-W-66-off-common-light-v2", 2,
                "77674acc57934b69f84fa6ee49dab7ed5df020b0077733d5e510cf90125a55a1",
                "244ccc9bfe42382b7f6cc035a6d625f24c4af38a6b3131f0b8db089eae2fb6c0"),
}
QUEUES = {
    "mm-mechanical": (COVERAGE / "persistent-mm-mechanical", "e3aa4a7988d96c51a5e76ce1187dfaeb3a505830fd05a6436038a399dd9f8a03", "MM-MECHANICAL-3-PLAN.json",
                      "1e3449f82475692c72cce1a10b0e2f670c0ae089cc0518b4b96ec34c05bc4fad",
                      "mechanical-01", ("w66-off",)),
}

def read(path):
    return json.loads(path.read_text())


def digest(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def checked(path, expected):
    if digest(path) != expected:
        raise RuntimeError(f"approved bytes changed: {path}")


def qualified(queue):
    root, seal, plan_name, plan_sha, out_name, predecessors = QUEUES[queue]
    source = root / "RUNNER-SEAL.json"
    checked(source, seal)
    for name, sha in read(source)["sha256"].items():
        checked(root / name, sha)
    path = root / plan_name
    checked(path, plan_sha)
    plan = read(path)
    wanted = [PREDECESSORS[key][2] for key in predecessors]
    if sorted(job["row"]["slot"] for job in plan["jobs"] if job["row"]["backend"] == "gpu") != wanted:
        raise ValueError("approved target does not match exactly the dependent GPU slots")
    if len(plan["jobs"]) != len(wanted):
        raise ValueError("approved target includes an unexpected job")
    return plan, root / "runs" / out_name


def load_base():
    checked(SOURCE_ROOT / "RUNNER-SEAL.json", SOURCE_SEAL)
    checked(SOURCE_ROOT / "callback.py", read(SOURCE_ROOT / "RUNNER-SEAL.json")["sha256"]["callback.py"])
    code = importlib.util.spec_from_file_location("approved_persistent_custody", SOURCE_ROOT / "callback.py")
    base = importlib.util.module_from_spec(code)
    code.loader.exec_module(base)
    return base, base.sources()


def approval_command(queue, path, approval_sha):
    checked(path, approval_sha)
    root, seal, plan_name, plan_sha, out_name, _ = QUEUES[queue]
    if read(path) != {"approved_by": "main", "runner_seal_sha256": seal,
                      "plan": str(root / plan_name), "plan_sha256": plan_sha}:
        raise ValueError("main approval must name the exact fixed callback, plan and digest")
    return ["/usr/bin/python3", "-B", "-u", str(root / "callback.py"), "launch", "--seal", seal,
            "--approval", str(path), "--approval-sha256", approval_sha, "--out", str(root / "runs" / out_name)]


def predecessor(name, lease):
    dirname, row_id, slot, plan_sha, approval_sha = PREDECESSORS[name]
    run = W66_ROOT / "runs" / dirname
    planned, approved = run / "PLAN.json", run / "APPROVAL.json"
    checked(planned, plan_sha)
    checked(approved, approval_sha)
    plan = read(planned)
    jobs = [job for job in plan["jobs"] if job["id"] == row_id]
    if (len(jobs) != 1 or plan["lease"] != lease or jobs[0]["row"]["slot"] != slot
            or jobs[0]["row"]["backend"] != "gpu"):
        raise RuntimeError("predecessor did not own the specific persistent GPU slot")
    target = run / "units" / row_id / "CALLBACK-RESULT.json"
    if not target.exists():
        return None
    evidence = read(target)
    if (evidence["id"] != row_id or evidence["backend"] != "gpu" or evidence["slot"] != slot
            or not evidence.get("terminal_at") or not evidence["cleanup"]["removed_verified"]
            or evidence["supervision"]["returncode"] is None):
        raise RuntimeError(f"predecessor terminal custody is incomplete: {target}")
    return {"receipt": str(target), "sha256": digest(target), "slot": slot,
            "status": evidence["status"], "terminal_at": evidence["terminal_at"]}


@contextmanager
def locks_free(lease, slots):
    handles = []
    try:
        for slot in slots:
            handle = (lease.LOCKS / f"gpu-{slot}.lock").open("rb")
            handles.append(handle)
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                yield False
                return
        yield True
    finally:
        for handle in reversed(handles):
            handle.close()


def poll(queue, ctx, plan):
    bridge, engine, legacy, _, _, mechanical = ctx
    lease = plan["lease"]
    route = bridge.lease.prove(engine, legacy, mechanical, lease, "gpu")
    preceding = [predecessor(key, lease) for key in QUEUES[queue][-1]]
    if any(item is None for item in preceding):
        return None
    slots = [item["slot"] for item in preceding]
    with locks_free(bridge.lease, slots) as free:
        if not free:
            return None
        try:
            native_idle = all(bridge.slot_idle(route["port"], slot) for slot in slots)
        except OSError:
            # Temporary native HTTP latency is pending readiness. The live
            # owner proof above still fails closed outside this probe.
            return None
        if not native_idle:
            return None
    return {"predecessor_terminal": preceding, "all_slot_locks_released": True,
            "native_slots_idle": slots, "provider": route, "ready_observed_at": time.time()}


def run(queue, args):
    plan, output = qualified(queue)
    _, ctx = load_base()
    bridge, engine, legacy, _, _, mechanical = ctx
    bridge.lease.verify_receipts(legacy, plan["lease"])
    deadline = read(bridge.lease.LIVE / "READY.json")["ready_at"] + 7200
    if args.probe:
        print(json.dumps({"queue": queue, "ready": poll(queue, ctx, plan) is not None,
                          "no_launch": True}))
        return
    argv = approval_command(queue, args.approval, args.approval_sha256)
    if output.exists():
        raise RuntimeError("approved output already exists")
    audit = args.audit.resolve()
    if not audit.is_relative_to(HERE / "runs") or audit == HERE / "runs":
        raise ValueError("use a new private audit directory beneath this watcher")
    audit.mkdir(parents=True, mode=0o700)
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, lambda *_: STOP.set())
    with (HERE / f"{queue}.watch.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        legacy.write(audit / "WAITING.json", {"queue": queue, "argv": argv, "lease": plan["lease"],
                     "approval_sha256": args.approval_sha256, "started_at": time.time(), "deadline": deadline})
        try:
            while not STOP.is_set() and time.time() < deadline:
                readiness = poll(queue, ctx, plan)
                if readiness is not None:
                    break
                STOP.wait(1)
            else:
                raise RuntimeError("watch cancelled or owner deadline reached before submission")
            current, _ = qualified(queue)
            if current != plan or approval_command(queue, args.approval, args.approval_sha256) != argv:
                raise RuntimeError("queued command changed at final admission")
            bridge.lease.verify_receipts(legacy, plan["lease"])
            bridge.lease.prove(engine, legacy, mechanical, plan["lease"], "gpu")
            if STOP.is_set() or time.time() >= deadline or output.exists():
                raise RuntimeError("owner closed at submission boundary")
            legacy.write(audit / "ADMISSION.json", {**readiness, "argv": argv,
                         "approval_sha256": args.approval_sha256, "lease": plan["lease"]})
            with (audit / "callback.log").open("xb") as log:
                process = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                legacy.write(audit / "LAUNCH.json", {"pid": process.pid, "argv": argv, "started_at": time.time(),
                             "admission_sha256": digest(audit / "ADMISSION.json")})
                note = None
                while process.poll() is None:
                    try:
                        bridge.lease.prove(engine, legacy, mechanical, plan["lease"], "gpu")
                    except (OSError, RuntimeError) as error:
                        note = repr(error)
                    if STOP.is_set() or time.time() >= deadline or note:
                        process.send_signal(signal.SIGINT)
                        break
                    try:
                        process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        pass
                returncode = process.wait()
            legacy.write(audit / "TERMINAL.json", {"returncode": returncode, "ended_at": time.time(),
                                                  "owner_loss": note, "output": str(output)})
            if returncode:
                raise SystemExit(returncode)
        except BaseException as error:
            legacy.write(audit / "FAILURE.json", {"error": repr(error), "at": time.time(),
                                                 "submitted": (audit / "LAUNCH.json").exists()})
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("queue", choices=QUEUES.keys())
    parser.add_argument("--seal", required=True)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--approval-sha256")
    parser.add_argument("--audit", type=Path)
    args = parser.parse_args()
    seal = HERE / "WATCHER-SEAL.json"
    checked(seal, args.seal)
    for name, sha in read(seal)["sha256"].items():
        checked(HERE / name, sha)
    if not args.probe and (args.approval is None or not args.approval_sha256 or args.audit is None):
        parser.error("exact main approval, approval digest, and audit path are required")
    if args.approval:
        args.approval = args.approval.resolve()
    run(args.queue, args)


if __name__ == "__main__":
    main()
