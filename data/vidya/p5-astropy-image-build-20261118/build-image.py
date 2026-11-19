"""Acquire original custody for a prospective network-disabled Astropy image build."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent
ROW = "vb-p5-astropy-image-rebuild-20261118"
BASE = ("swebench/sweb.eval.x86_64.astropy_1776_astropy-12907"
        "@sha256:7485c1e3c8861efd0c6a4a78b952857592e541031039000d25e9481f045dc4a3")
BASE_ID = "sha256:9b1cabf7bcd83a28469f67e3852d8e2207e90d45aa71f436bb7e600bdee8bae2"
CONTEXT_SHA = "4becb58802aaa44d792030e83090dede6f97251c0bb692428d76bf643360063e"
DOCKERFILE_SHA = "2066d6a5800a1010ed1949ff89b39e2774389a345c01460730ae5f20f631d2ff"
CAP_SECONDS = 270


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat()


def epoch(value):
    timestamp = datetime.fromisoformat(value)
    if timestamp.utcoffset() != timezone.utc.utcoffset(None):
        raise ValueError("expected an explicit UTC timestamp")
    return timestamp.timestamp()


def cpus(value):
    result = set()
    for part in value.split(","):
        if not re.fullmatch(r"\d{1,3}(?:-\d{1,3})?", part):
            raise ValueError("invalid CPU list")
        left, _, right = part.partition("-")
        first, last = int(left), int(right or left)
        if first > last:
            raise ValueError("reversed CPU range")
        result.update(range(first, last + 1))
    return result


def cpu_string(values):
    return ",".join(map(str, sorted(values)))


def image_id(reference):
    return subprocess.check_output(
        ["docker", "image", "inspect", "--format", "{{.Id}}", reference],
        text=True, timeout=10,
    ).strip()


def verify_context():
    context = ROOT / "context"
    manifest = context / "SOURCE.sha256"
    if manifest.is_symlink() or sha(manifest) != CONTEXT_SHA:
        raise ValueError("original build context manifest changed")
    expected = {"SOURCE.sha256"}
    for line in manifest.read_text().splitlines():
        digest, name = line.split("  ", 1)
        path = context / name
        if path.is_symlink() or not path.is_file() or sha(path) != digest:
            raise ValueError(f"original build input differs: {name}")
        expected.add(name)
    for path in context.rglob("*"):
        if path.is_symlink() or (path.is_dir() and path != context / "wheelhouse"):
            raise ValueError(f"unexpected context entry: {path}")
    if {str(p.relative_to(context)) for p in context.rglob("*") if not p.is_dir()} != expected:
        raise ValueError("unexpected context files")
    if sha(context / "Dockerfile") != DOCKERFILE_SHA:
        raise ValueError("original Dockerfile changed")


def preflight():
    verify_context()
    if image_id(BASE) != BASE_ID:
        raise ValueError("pinned base manifest does not resolve to the original config")


def output():
    smoke = os.environ.get("FILLER_DRYRUN") == "1"
    if smoke:
        path = Path(os.environ["FILLER_DRYRUN_RESULT_PATH"])
        root = Path(os.environ["FILLER_DRYRUN_DIR"]).resolve()
        if root not in path.resolve().parents:
            raise ValueError("publisher result leaves its private root")
        return path, "smoke"
    return ROOT / "official/RESULT.json", "official"


def grant_fields(raw, mode):
    tokens = [field.split("=", 1) for field in raw.decode().split()]
    fields = dict(tokens)
    smoke = mode == "smoke"
    if (len(fields) != len(tokens) or fields.get("id", ROW) != ROW
            or smoke != (fields.get("kind") == "rowflow-dryrun")
            or (smoke and fields.get("id") != ROW)):
        raise ValueError("wrong original grant identity or mode")
    start = epoch(fields["start"])
    deadline = epoch(fields["end"]) - 90
    return start, deadline, cpus(fields["regions"])


def bind_grant(attempt, mode, started):
    env = os.environ
    smoke = mode == "smoke"
    if (env["FILLER_ID"] != ROW or env["FILLER_NEEDGPU"] != "0"
            or smoke != (env.get("FILLER_SMOKE") == "1")):
        raise ValueError("wrong row or CPU allocation mode")
    root = (env["FILLER_DRYRUN_DIR"] if smoke else
            env.get("FILLER_FLAGS_DIR", "/mnt/raid0/llm/tmp/compute-flags"))
    raw = (Path(root) / "grants" / f"{ROW}.grant").read_bytes()
    snapshot = attempt / "rowflow.grant"
    snapshot.write_bytes(raw)
    start, deadline, granted = grant_fields(raw, mode)
    actual = os.sched_getaffinity(0)
    if (not start <= started < deadline == int(env["FILLER_DEADLINE"])
            or actual != cpus(env["FILLER_CPUS"]) or not actual <= granted
            or len(actual) < 4 or (smoke and len(actual) != 4)):
        raise ValueError("grant window or CPU placement refused")
    return {
        "grant_sha256": sha(snapshot), "grant_start_epoch": start, "deadline_epoch": deadline,
        "actual_cpus": cpu_string(actual), "build_cpus": cpu_string(sorted(actual)[:4]),
    }


class BuildStopped(Exception):
    pass


def stop(_signum, _frame):
    raise BuildStopped("interrupted")


def stop_if_due(deadline):
    if time.time() >= deadline or Path(os.environ["FILLER_STOPFILE"]).exists():
        raise BuildStopped("allocation deadline, build cap, or STOP")


def build(attempt, binding, deadline):
    iid = attempt / "image.iid"
    cmd = ["docker", "build", "--pull=false", "--network=none", "--no-cache", "--force-rm",
           "--cpuset-cpus", binding["build_cpus"], "--cpu-period", "100000",
           "--cpu-quota", "400000", "--memory", "6g", "--iidfile", str(iid),
           str(ROOT / "context")]
    stop_if_due(deadline)
    with (attempt / "build.log").open("xb") as log:
        child = subprocess.Popen(cmd, env=dict(os.environ, DOCKER_BUILDKIT="0"),
                                 stdout=log, stderr=subprocess.STDOUT)
        try:
            while child.poll() is None:
                stop_if_due(deadline)
                time.sleep(0.25)
            if child.returncode:
                raise subprocess.CalledProcessError(child.returncode, cmd)
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
    candidate = iid.read_text().strip()
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", candidate) or image_id(candidate) != candidate:
        raise ValueError("derived Docker image is unavailable")
    return candidate


def capture():
    path, mode = output()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    attempt = Path(tempfile.mkdtemp(prefix="build-", dir=path.parent))
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, stop)
    started = time.time()
    log = attempt / "build.log"
    receipt = {
        "schema": "epyc.p5.image-build-capture.v1", "status": "UNKNOWN",
        "id": ROW, "mode": mode, "started_utc": utc(started), "base_image_id": BASE_ID,
        "base_ref": BASE, "dockerfile_sha256": DOCKERFILE_SHA, "context_sha256": CONTEXT_SHA,
        "launcher_sha256": sha(ROOT / "launch.sh"), "source_manifest_sha256": sha(ROOT / "SOURCE.sha256"),
    }
    try:
        receipt.update(bind_grant(attempt, mode, started))
        deadline = min(started + CAP_SECONDS, receipt["deadline_epoch"])
        if deadline - started <= 60:
            raise BuildStopped("insufficient build window")
        stop_if_due(deadline)
        preflight()
        receipt["image_id"] = build(attempt, receipt, deadline)
        preflight()
        stop_if_due(deadline)
        rc = 0
        receipt["status"] = "COMPLETE"
    except Exception as exc:
        rc = 75 if isinstance(exc, BuildStopped) else 1
        receipt["error"] = repr(exc)
    finally:
        if log.exists():
            receipt.update(build_log=str(log), build_log_sha256=sha(log))
        snapshot = attempt / "rowflow.grant"
        if snapshot.exists():
            receipt["grant_sha256"] = sha(snapshot)
        receipt.update(runner_rc=rc, completion_utc=utc(time.time()))
        terminal = attempt / ("receipt.json" if rc == 0 else "terminal.json")
        with terminal.open("x") as stream:
            json.dump(receipt, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        if rc == 0:
            os.link(terminal, path)
    return rc


def complete():
    path, mode = output()
    receipt = json.loads(path.read_bytes())
    log = Path(receipt["build_log"]).resolve(strict=True)
    attempt = log.parent
    if (attempt.parent != path.parent.resolve(strict=True) or not attempt.name.startswith("build-")
            or log.name != "build.log" or not os.path.samefile(path, attempt / "receipt.json")):
        raise ValueError("completion path leaves its original attempt")
    snapshot = attempt / "rowflow.grant"
    start, deadline, granted = grant_fields(snapshot.read_bytes(), mode)
    actual = cpus(receipt["actual_cpus"])
    build_cpus = cpus(receipt["build_cpus"])
    started, ended = (epoch(receipt[field]) for field in ("started_utc", "completion_utc"))
    image = receipt["image_id"]
    if (receipt["schema"] != "epyc.p5.image-build-capture.v1"
            or receipt["id"] != ROW or receipt["mode"] != mode
            or receipt["status"] != "COMPLETE" or receipt["runner_rc"] != 0
            or receipt["base_ref"] != BASE or receipt["base_image_id"] != BASE_ID
            or receipt["context_sha256"] != CONTEXT_SHA or receipt["dockerfile_sha256"] != DOCKERFILE_SHA
            or receipt["launcher_sha256"] != sha(ROOT / "launch.sh")
            or receipt["source_manifest_sha256"] != sha(ROOT / "SOURCE.sha256")
            or receipt["grant_sha256"] != sha(snapshot) or receipt["build_log_sha256"] != sha(log)
            or start != receipt["grant_start_epoch"] or deadline != receipt["deadline_epoch"]
            or not start <= started <= ended < min(deadline, started + CAP_SECONDS)
            or not build_cpus <= actual <= granted or len(build_cpus) != 4
            or (mode == "smoke" and len(actual) != 4)
            or (attempt / "image.iid").read_text().strip() != image
            or not re.fullmatch(r"sha256:[a-f0-9]{64}", image) or image_id(image) != image):
        raise ValueError("original build custody refused")


if __name__ == "__main__":
    actions = {"--preflight": preflight, "--job": capture, "--complete": complete}
    if len(sys.argv) != 2 or sys.argv[1] not in actions:
        sys.exit("expected --preflight, --job or --complete")
    sys.exit(actions[sys.argv[1]]())
