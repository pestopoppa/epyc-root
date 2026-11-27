"""Run the pinned TU checker with read-only mounts, no network, and owned cleanup."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent / "legacy-comparison"
CASE_ENV = PACKAGE / "cases/TU-GR-1/task-env.json"
IMAGE = "sha256:9c429a17180a9b3ce2bce942d1bb05a7b7dfbf8218edbc267d190c35fe2b7635"
ENV_SHA = "65abb3f4db8cc69ac0a53eca561fa9bc71fbb92dc832ff913f16d125e5289cc2"
TEST = "scripts/autopilot/evals/dtap/tests/test_grader_isolation.py"
DEPS = PACKAGE / "python-packages"
VERIFY = (
    "import sys;sys.path.insert(0,'/oracles');from pathlib import Path;"
    "import tu_grader_isolation as t;"
    f"d=t.validate(Path('/case'),'python3 -m pytest -q {TEST}',120);"
    "print('TU-GR-1 contract passed' if d is None else d);"
    "raise SystemExit(0 if d is None else 1)"
)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def grade_command(lane, checker, name, label, seconds):
    if digest(CASE_ENV) != ENV_SHA:
        raise RuntimeError("contained TU evaluator environment changed")
    mounts = {"/case": lane, "/python-packages": DEPS, "/oracles/tu_grader_isolation.py": checker}
    command = ["docker", "create", "--pull", "never", "--name", name,
               "--label", "taskflow.tu-auto-ci=" + label, "--network", "none", "--read-only",
               "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
               "--user", f"{os.getuid()}:{os.getgid()}", "--cpuset-cpus", "180-183",
               "--pids-limit", "64", "--memory", "2g",
               "--tmpfs", "/tmp:rw,exec,nosuid,nodev,size=512m", "--workdir", "/case"]
    for dest, source in mounts.items():
        command += ["--mount", f"type=bind,source={source},target={dest},readonly"]
    for key, value in json.loads(CASE_ENV.read_bytes()).items():
        command += ["--env", key + "=" + value]
    command += ["--entrypoint", "/usr/bin/timeout", IMAGE, "--kill-after=2s", f"{seconds}s",
                "/usr/bin/nice", "-n", "19", "/usr/bin/python3", "-B", "-c", VERIFY]
    return command, mounts


def inspect(identity):
    reply = subprocess.run(["docker", "inspect", "--type", "container", identity],
                           capture_output=True, text=True, timeout=8)
    if reply.returncode == 0:
        return json.loads(reply.stdout)[0]
    if "No such" in reply.stderr:
        return None
    raise RuntimeError(reply.stderr[-1000:])


def verify(container, label, mounts):
    info = container["HostConfig"]
    actual_mounts = {m["Destination"]: (m["Source"], m["RW"]) for m in container["Mounts"]}
    if (container["Image"] != IMAGE
            or container["Config"]["Labels"].get("taskflow.tu-auto-ci") != label
            or actual_mounts != {k: (str(v), False) for k, v in mounts.items()}
            or info["NetworkMode"] != "none" or not info["ReadonlyRootfs"]
            or "ALL" not in info["CapDrop"] or info["Privileged"]
            or "no-new-privileges" not in info["SecurityOpt"]
            or info["Memory"] != 2 * 1024 ** 3 or info["PidsLimit"] != 64):
        raise RuntimeError("created TU evaluator does not match its approved isolation")


def run(lane, checker, output, deadline, cancelled):
    """Return a checked outcome and always remove the exact owned evaluator."""
    output.mkdir()
    started = time.monotonic()
    if cancelled() or deadline - started < 30:
        raise TimeoutError("insufficient owner time for contained grading")
    label = uuid.uuid4().hex
    name = "ws58-tu-ci-" + label
    command, mounts = grade_command(lane, checker, name, label, min(175, int(deadline - started) - 20))
    (output / "CONTAINER-INTENT.json").write_text(json.dumps({"name": name, "label": label,
                                                             "argv": command}) + "\n")
    result, reason = None, None
    try:
        subprocess.run(command, capture_output=True, check=True, timeout=8)
        container = inspect(name)
        if container is None:
            raise RuntimeError("created evaluator container is absent")
        verify(container, label, mounts)
        identity = container["Id"]
        with (output / "stdout.log").open("xb") as out, (output / "stderr.log").open("xb") as err:
            if not cancelled() and time.monotonic() < deadline - 12:
                process = subprocess.Popen(["docker", "start", "--attach", identity],
                                           stdout=out, stderr=err, start_new_session=True)
                try:
                    while process.poll() is None:
                        reason = cancelled()
                        if reason or time.monotonic() >= deadline - 12:
                            reason = reason or "checker_owner_deadline"
                            break
                        try:
                            process.wait(timeout=.25)
                        except subprocess.TimeoutExpired:
                            pass
                    if reason is None:
                        result = process.returncode
                finally:
                    if process.poll() is None:
                        process.send_signal(signal.SIGINT)
                        try:
                            process.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=2)
            else:
                reason = "checker_owner_deadline_or_cancelled"
    finally:
        still_present = inspect(name)
        if still_present is not None:
            verify(still_present, label, mounts)
            identity = still_present["Id"]
            subprocess.run(["docker", "rm", "--force", identity], capture_output=True,
                           check=True, timeout=8)
            if inspect(identity) is not None:
                raise RuntimeError("owned evaluator survived cleanup")
    return {"rc": result, "reason": reason, "cleanup_verified": True,
            "elapsed_s": round(time.monotonic() - started, 3)}
