"""Run MM-5 v2 only in the pinned, network-isolated evaluator environment."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
CASE = HERE.parent / "coverage/legacy-comparison/cases/MM-5"
DEPS = CASE.parents[1] / "python-packages"
IMAGE = "sha256:9c429a17180a9b3ce2bce942d1bb05a7b7dfbf8218edbc267d190c35fe2b7635"
ORIGINAL_SUPPORT_SHA = "ebf06226092574fd21faeb026624618074308a82fa5307cbe488861482215cbb"
TASK_ENV_SHA = "65abb3f4db8cc69ac0a53eca561fa9bc71fbb92dc832ff913f16d125e5289cc2"


def verified(path, expected):
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != expected:
        raise RuntimeError(f"sealed oracle input changed: {path}")
    return content


def main():
    lane = Path(sys.argv[1]).resolve(strict=True)
    if not lane.is_dir():
        raise SystemExit("candidate must be a directory")
    env = json.loads(verified(CASE / "task-env.json", TASK_ENV_SHA))
    support = CASE / "evaluator-support"
    verified(support / "vision_contract.py", ORIGINAL_SUPPORT_SHA)
    cmd = [
        "docker", "run", "--rm", "--pull", "never", "--network", "none", "--read-only",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--user", f"{os.getuid()}:{os.getgid()}", "--cpuset-cpus", "180-183",
        "--pids-limit", "64", "--memory", "2g",
        "--tmpfs", "/tmp:rw,exec,nosuid,nodev,size=512m",
        "--mount", f"type=bind,source={lane},target=/case,readonly",
        "--mount", f"type=bind,source={DEPS},target=/python-packages,readonly",
        "--mount", f"type=bind,source={support},target=/oracles,readonly",
        "--mount", f"type=bind,source={HERE / 'vision_contract_v2.py'},target=/v2.py,readonly",
        "--workdir", "/case",
    ]
    for key, value in env.items():
        cmd += ["--env", key + "=" + value]
    cmd += ["--entrypoint", "/usr/bin/timeout", IMAGE, "--kill-after=2s", "175s",
            "/usr/bin/nice", "-n", "19", "/usr/bin/python3", "-B", "/v2.py", "/case"]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=180)
    except subprocess.TimeoutExpired as exc:
        sys.stdout.buffer.write(exc.stdout or b"")
        sys.stderr.buffer.write(exc.stderr or b"")
        raise SystemExit(124) from exc
    sys.stdout.buffer.write(proc.stdout)
    sys.stderr.buffer.write(proc.stderr)
    raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
