"""Exercise the TU-GR-1 acceptance test on hosts where real unshare may be blocked."""
from __future__ import annotations

import os
import secrets
import shlex
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

_PERMISSION_REFUSAL = "unshare: write failed /proc/self/uid_map: Operation not permitted"
_SETUP_FAILURE = "unshare: simulated namespace setup failure"
_MOUNT_REFUSAL = "mount: simulated tmpfs setup: Operation not permitted"
_CONTROL = "test_reachable_grader_is_flagged"
_ISOLATED = "test_isolated_launch_denies"
_WORK_FILE = "test_grader_isolation.py"
_WORK_PATH = f"scripts/autopilot/evals/dtap/tests/{_WORK_FILE}"

_UNSHARE = r"""#!/bin/sh
set -eu
if [ "${TASKFLOW_NAMESPACE_ERROR:-}" ]; then
    printf '%s\n' "$TASKFLOW_NAMESPACE_ERROR" >&2
    exit 1
fi
while [ "$#" -gt 0 ]; do
    case "$1" in
        --user|--map-root-user|--mount|--net|--fork) shift ;;
        --propagation) shift 2 ;;
        --propagation=*) shift ;;
        -[Urmnf]*)
            case "${1#-}" in *[!Urmnf]*) exit 64 ;; esac
            shift
            ;;
        --) shift; break ;;
        *) break ;;
    esac
done
if [ "${TASKFLOW_REWRITE_PROBE:-}" ]; then
    exec "$TASKFLOW_REWRITE_PROBE" "$@"
fi
exec "$@"
"""

# This shim only mutates the verifier-owned disposable pytest tree. Renaming
# the mount target exposes an empty directory at the same path to the child.
_MOUNT = """import argparse
import os
import sys
import tempfile
from pathlib import Path

# Propagation setup changes no test files and supplies no mount receipt.
if len(sys.argv) == 3 and sys.argv[1] in {
    "--make-private", "--make-rprivate", "--make-slave", "--make-rslave",
}:
    sys.exit(0)

parser = argparse.ArgumentParser()
parser.add_argument("-t", "--types", required=True, choices=["tmpfs"])
parser.add_argument("-o", "--options", action="append")
parser.add_argument("source")
parser.add_argument("target")
target = Path(parser.parse_args().target).resolve()
base = Path(os.environ["TASKFLOW_PYTEST_TMP"]).resolve()
if base not in target.parents or not target.is_dir() or not any(target.iterdir()):
    sys.exit(f"mount target is not a nonempty directory inside the test scratch: {target}")
if os.environ["TASKFLOW_MOUNT_ERROR"]:
    Path(os.environ["TASKFLOW_FAULT_RECEIPT"]).touch()
    sys.exit(os.environ["TASKFLOW_MOUNT_ERROR"])
hidden = Path(tempfile.mkdtemp(prefix="hidden-", dir=base)) / "contents"
target.rename(hidden)
target.mkdir()
Path(os.environ["TASKFLOW_MOUNT_RECEIPT"]).write_text(str(target))
"""

# Keep the worker's child JSON shape and alter only its access errnos.
_REWRITE_PROBE = """import errno
import json
import os
import subprocess
import sys
from pathlib import Path

child = subprocess.run(sys.argv[1:], capture_output=True)
sys.stderr.buffer.write(child.stderr)
if child.returncode:
    sys.stdout.buffer.write(child.stdout)
    sys.exit(child.returncode)
try:
    result = json.loads(child.stdout)
except ValueError:
    result = {}
if not isinstance(result, dict) or not {"open_errno", "listdir_errno"}.issubset(result):
    sys.stdout.buffer.write(child.stdout)
    sys.exit(0)
result["open_errno"] = errno.EROFS
result["listdir_errno"] = errno.EROFS
Path(os.environ["TASKFLOW_FAULT_RECEIPT"]).touch()
print(json.dumps(result))
"""

_DIRECT_PROBE = """import errno
import sys
from pathlib import Path

sys.path.insert(0, str(Path('scripts/autopilot/evals/dtap').resolve()))
from harness.isolation import (
    GraderReachable, assert_grader_unreachable, probe_grader_access,
)

sentinel = Path(sys.argv[1])
result = probe_grader_access(sentinel, launcher=[])
assert result["open_ok"] is True, f"plain child did not read the sentinel: {result}"
try:
    assert_grader_unreachable(result)
except GraderReachable:
    pass
else:
    raise AssertionError("successful read did not raise GraderReachable")

missing = probe_grader_access(sentinel.with_name("absent"), launcher=[])
assert missing["open_ok"] is False and missing["open_errno"] == errno.ENOENT, missing

for code in ("raise SystemExit(27)", "print('not JSON')", "pass"):
    try:
        error = probe_grader_access(sentinel, launcher=[sys.executable, "-c", code])
    except GraderReachable as exc:
        raise AssertionError("launcher failure counted as grader access") from exc
    except Exception:
        pass
    else:
        assert error.get("launcher_error"), f"failed launcher returned an access result: {error}"
        try:
            assert_grader_unreachable(error)
        except GraderReachable as exc:
            raise AssertionError("launcher failure counted as grader access") from exc
        except Exception:
            pass
        else:
            raise AssertionError("launcher failure counted as denial")
"""


def _outcomes(report: Path) -> dict[str, tuple[str, str]]:
    """Read the two exact test names from the expected pytest source file."""
    if not report.is_file():
        return {}
    out = {}
    for test in ET.parse(report).iter("testcase"):
        name = test.get("name")
        if test.get("file") != _WORK_PATH or name not in {_CONTROL, _ISOLATED}:
            continue
        if name in out:
            raise ValueError(f"JUnit report has duplicate results for {_WORK_PATH}::{name}")
        result = next((node for node in test if node.tag in {"skipped", "failure", "error"}), None)
        out[name] = ("passed", "") if result is None else (result.tag, result.get("message", ""))
    return out


def validate(lane: Path, acceptance: str, timeout: float) -> str | None:
    """Return a failure diagnostic or None after checking capable/error paths."""
    if "pytest" not in acceptance or _WORK_FILE not in acceptance:
        return f"acceptance must run pytest on {_WORK_FILE}"
    with tempfile.TemporaryDirectory(prefix="taskflow-tu-grader-") as scratch:
        tmp = Path(scratch)
        rewriter = tmp / "rewrite-probe"
        python = f"#!{sys.executable}\n"
        for name, code in (("unshare", _UNSHARE), ("mount", python + _MOUNT), (rewriter.name, python + _REWRITE_PROBE)):
            shim = tmp / name
            shim.write_text(code)
            shim.chmod(0o700)
        phases = (
            ("capable", 0, "passed", {}),
            ("permission-refusal", 0, "skipped", {"TASKFLOW_NAMESPACE_ERROR": _PERMISSION_REFUSAL}),
            ("unrelated-failure", 1, "failure", {"TASKFLOW_NAMESPACE_ERROR": _SETUP_FAILURE}),
            ("mount-permission-refusal", 1, "failure", {"TASKFLOW_MOUNT_ERROR": _MOUNT_REFUSAL}),
            ("wrong-access-errno", 1, "failure", {"TASKFLOW_REWRITE_PROBE": str(rewriter)}),
        )
        for phase, rc, isolated_status, overrides in phases:
            base = tmp / phase
            report = tmp / f"{phase}.xml"
            mount_receipt = tmp / f"{phase}-mount-target"
            fault_receipt = tmp / f"{phase}-fault"
            env = dict(os.environ, LC_ALL="C", PATH=f"{tmp}{os.pathsep}{os.environ.get('PATH', os.defpath)}",
                       TASKFLOW_PYTEST_TMP=str(base), TASKFLOW_NAMESPACE_ERROR="", TASKFLOW_MOUNT_ERROR="",
                       TASKFLOW_REWRITE_PROBE="", TASKFLOW_MOUNT_RECEIPT=str(mount_receipt),
                       TASKFLOW_FAULT_RECEIPT=str(fault_receipt))
            env.update(overrides)
            # xunit1 retains pytest's source file attribute for functions and class methods.
            cmd = (f"{acceptance} --basetemp {shlex.quote(str(base))} "
                   f"--junitxml {shlex.quote(str(report))} -o junit_family=xunit1")
            try:
                run = subprocess.run(cmd, cwd=lane, env=env, shell=True, capture_output=True, text=True, timeout=timeout)
                results = _outcomes(report)
            except (subprocess.TimeoutExpired, OSError, ET.ParseError, ValueError) as exc:
                raise RuntimeError(f"simulated namespace {phase}: {exc}") from exc
            if not report.is_file():
                raise RuntimeError(f"simulated namespace {phase}: pytest produced no report (rc={run.returncode})\n"
                                   f"{run.stdout[-500:]}{run.stderr[-500:]}")
            observed, reason = results.get(_ISOLATED, ("missing", ""))
            if run.returncode != rc or results.get(_CONTROL, ("missing", ""))[0] != "passed" or observed != isolated_status:
                return (f"simulated namespace {phase}: expected rc={rc} and control passed / isolated {isolated_status}, "
                        f"got rc={run.returncode} and {results!r}\n{run.stdout[-1000:]}{run.stderr[-500:]}")
            if phase == "capable" and not mount_receipt.is_file():
                return "simulated namespace capable: isolated test passed without mounting over its scratch directory"
            if phase == "permission-refusal" and _PERMISSION_REFUSAL not in reason:
                return f"simulated namespace permission-refusal: skip did not preserve the actual diagnostic: {reason}"
            if phase in ("mount-permission-refusal", "wrong-access-errno") and not fault_receipt.is_file():
                return f"simulated namespace {phase}: worker did not reach the injected fault"

        sentinel = tmp / "sentinel"
        sentinel.write_text(secrets.token_hex(16))
        args = shlex.split(acceptance)
        module_index = args.index("-m") if "-m" in args else len(args)
        interpreter = args[:module_index] if args[module_index:module_index + 2] == ["-m", "pytest"] else [sys.executable]
        try:
            run = subprocess.run([*interpreter, "-c", _DIRECT_PROBE, str(sentinel)], cwd=lane,
                                 capture_output=True, text=True, timeout=timeout)
        except (subprocess.TimeoutExpired, OSError) as exc:
            raise RuntimeError(f"direct control probe: {exc}") from exc
        if run.returncode:
            return f"direct control probe rc={run.returncode}: {run.stderr[-1000:]}{run.stdout[-300:]}"
    return None
