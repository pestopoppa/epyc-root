"""Preserve original grant and raw arms around a private P5 scorer invocation."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import signal
import subprocess
import sys
import tempfile
import time

ROW = "vb-p5-sphinx-scorer-native-20261118"
ROOT = Path(__file__).resolve().parent


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cpu_set(value):
    if not re.fullmatch(r"\d{1,3}(?:-\d{1,3})?(?:,\d{1,3}(?:-\d{1,3})?)*", value):
        raise ValueError("invalid grant CPU syntax")
    result = set()
    for block in value.split(","):
        low, _, high = block.partition("-")
        low, high = int(low), int(high or low)
        if high < low:
            raise ValueError("reversed CPU range")
        result.update(range(low, high + 1))
    return result


def grant_context(attempt, env, actual, now):
    smoke = env.get("FILLER_DRYRUN") == "1"
    if (env["FILLER_ID"] != ROW or env.get("FILLER_NEEDGPU") != "0"
            or smoke != (env.get("FILLER_SMOKE") == "1")):
        raise ValueError("wrong row or allocation mode")
    flags = Path(env.get("FILLER_FLAGS_DIR", "/mnt/raid0/llm/tmp/compute-flags"))
    grants = Path(env["FILLER_DRYRUN_DIR"]) / "grants" if smoke else flags / "grants"
    path = grants / (ROW + ".grant")
    contents = path.read_bytes()
    snapshot = attempt / "rowflow.grant"
    snapshot.write_bytes(contents)
    fields = dict(field.split("=", 1) for field in contents.decode().split())
    start, end = (datetime.fromisoformat(fields[key]).timestamp() for key in ("start", "end"))
    deadline = int(env["FILLER_DEADLINE"])
    granted = cpu_set(fields["regions"])
    declared = cpu_set(env["FILLER_CPUS"])
    if (fields.get("id", ROW) != ROW or smoke != (fields.get("kind") == "rowflow-dryrun")
            or not actual or actual != declared or not actual <= granted
            or (smoke and (fields.get("id") != ROW or len(actual) != 4))
            or not start <= now < deadline == end - 90):
        raise ValueError("grant window, CPU placement or identity refused")
    return {"row": ROW, "mode": "smoke" if smoke else "official",
            "source": str(path), "snapshot_sha256": sha(snapshot),
            "actual_cpus": sorted(actual), "granted_cpus": sorted(granted),
            "deadline_epoch": deadline}


def write_result(path, result):
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
            os.link(temporary, path)
        finally:
            temporary.unlink()


def preserve_arms(attempt, raw):
    artifacts = {}
    for arm, record in raw.get("arm_attempts", raw["arms"]).items():
        if arm not in {"gold", "negative"}:
            raise ValueError("unexpected scorer arm")
        for field in ("native_report", "test_log"):
            source = Path(record[field]).resolve()
            if ROOT / "logs" / "run_evaluation" not in source.parents:
                raise ValueError("scorer arm path leaves the private log root")
            if not source.is_file():
                continue
            name = f"{arm}-{source.name}"
            (attempt / name).write_bytes(source.read_bytes())
            artifacts[name] = sha(attempt / name)
    return artifacts


def result_path():
    smoke = os.environ.get("FILLER_DRYRUN") == "1"
    path = Path(os.environ["FILLER_DRYRUN_RESULT_PATH"]) if smoke else ROOT / "official/RESULT.json"
    if smoke and Path(os.environ["FILLER_DRYRUN_DIR"]).resolve() not in path.resolve().parents:
        raise ValueError("publisher result leaves its private output directory")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def stop_now(_signum, _frame):
    raise SystemExit(75)


def run():
    path = result_path()
    attempt = Path(tempfile.mkdtemp(prefix="attempt-", dir=path.parent))
    result = {"schema": "epyc.p5.scorer-control-capture.v1", "id": ROW, "status": "UNKNOWN",
              "attempt": attempt.name, "started_utc": utc(),
              "source_manifest_sha256": sha(ROOT / "SOURCE.sha256"),
              "launcher_sha256": sha(ROOT / "launch.sh"), "grant": None,
              "mode": "smoke" if os.environ.get("FILLER_DRYRUN") == "1" else "official"}
    rc = 1
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, stop_now)
    raw_path = attempt / "native.json"
    try:
        result["grant"] = grant_context(attempt, os.environ, os.sched_getaffinity(0), time.time())
        if Path(os.environ["FILLER_STOPFILE"]).exists():
            raise SystemExit(75)
        os.environ["P5_NATIVE_RESULT"] = str(raw_path)
        os.environ["P5_INSTRUMENT_DEADLINE"] = str(min(time.time() + 270, result["grant"]["deadline_epoch"]))
        os.environ["TMPDIR"] = str(attempt)
        with (attempt / "controls.log").open("w") as log:
            subprocess.run([sys.executable, "-B", str(ROOT / "run-controls.py")], check=True,
                           stdout=log, stderr=subprocess.STDOUT, cwd=ROOT,
                           timeout=float(os.environ["P5_INSTRUMENT_DEADLINE"]) - time.time())
        runpy.run_path(str(ROOT / "scorer.py"), run_name="__main__")
        rc = 0
    except (Exception, SystemExit) as exc:
        result["error"] = repr(exc)
        rc = 75 if isinstance(exc, SystemExit) and exc.code == 75 else 1
    finally:
        try:
            if raw_path.is_file():
                result["native_sha256"] = sha(raw_path)
                raw = json.loads(raw_path.read_bytes())
                result["arm_artifacts_sha256"] = preserve_arms(attempt, raw)
                if rc == 0:
                    from complete import validate_native
                    result["decision"] = validate_native(raw, json.loads((ROOT / "case.json").read_bytes()))
                    if time.time() >= result["grant"]["deadline_epoch"] or Path(os.environ["FILLER_STOPFILE"]).exists():
                        raise ValueError("allocation closed at completion")
                    result["status"] = "COMPLETE"
            elif rc == 0:
                raise ValueError("scorer returned without original outcome")
        except Exception as exc:
            result["capture_error"] = repr(exc)
            rc = rc or 1
        if (attempt / "controls.log").is_file():
            result["controls_sha256"] = sha(attempt / "controls.log")
        result["completion_utc"] = utc()
        result["runner_rc"] = rc
        write_result(attempt / "terminal.json", result)
        if rc == 0:
            os.link(attempt / "terminal.json", path)
    return rc


def complete():
    from complete import validate_native

    path = result_path()
    result = json.loads(path.read_bytes())
    attempt = path.parent / result["attempt"]
    mode = "smoke" if os.environ.get("FILLER_DRYRUN") == "1" else "official"
    if (attempt.resolve(strict=True).parent != path.parent.resolve(strict=True)
            or result["status"] != "COMPLETE" or result["runner_rc"] != 0
            or result["id"] != ROW or result["mode"] != mode
            or result["grant"]["mode"] != mode or result["grant"]["row"] != ROW
            or result["source_manifest_sha256"] != sha(ROOT / "SOURCE.sha256")
            or result["launcher_sha256"] != sha(ROOT / "launch.sh")
            or result["grant"]["snapshot_sha256"] != sha(attempt / "rowflow.grant")
            or result["native_sha256"] != sha(attempt / "native.json")
            or result["controls_sha256"] != sha(attempt / "controls.log")):
        raise ValueError("terminal custody refused")
    raw = json.loads((attempt / "native.json").read_bytes())
    expected = {f"{arm}-{name}" for arm in ("gold", "negative") for name in ("report.json", "test_output.txt")}
    artifacts = result["arm_artifacts_sha256"]
    if (expected != set(artifacts) or any(sha(attempt / name) != digest for name, digest in artifacts.items())
            or raw["producer_source_manifest_sha256"] != result["source_manifest_sha256"]
            or raw["producer_launcher_sha256"] != result["launcher_sha256"]
            or validate_native(raw, json.loads((ROOT / "case.json").read_bytes())) != result["decision"]):
        raise ValueError("original scorer result binding refused")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["run"]:
        sys.exit(run())
    if sys.argv[1:] == ["complete"]:
        try:
            sys.exit(complete())
        except (OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
            sys.exit(str(exc))
    sys.exit("expected run or complete")
