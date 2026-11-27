"""Qualify TU V4 against exact source positives and independent fault witnesses."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
V2 = ROOT / "tu-oracle-v2"
V3 = ROOT / "tu-oracle-v3"
MAIN = ROOT / "coverage/legacy-direct-repair/runs/TU-GR-1/direct-repair-1/lane"
ACTUAL_CPU = ROOT / (
    "coverage/persistent-callback/runs/cpu-tu-mm-01/units/cpu-TU-GR-1-off-recommended-paid-2/grade-lane"
)
ACTUAL_AUTO = ROOT / (
    "coverage/persistent-tu-off-auto-ci/runs/auto-01/units/gpu-TU-GR-1-off-common-on-sampling-auto-ci-2/grade-lane"
)
CASE = ROOT / "coverage/legacy-comparison/cases/TU-GR-1"
TEST = Path("scripts/autopilot/evals/dtap/tests/test_grader_isolation.py")
HARNESS = Path("scripts/autopilot/evals/dtap/harness/isolation.py")
PRIOR_FAILED = ROOT / "tu-oracle-v4"
HARNESS_ERRNO = "or (not ok and (type(error) is not int or error <= 0))"
BOUNDARY = CASE / (
    "baseline/.taskflow-refs/epyc-root@3b11e6c8244897cc9db02d366d8f63a885f62d0d"
    "/docs/design/tu-grader-isolation-boundary.md"
)
SKIP = "            pytest.skip(str(exc))"
PREFIX = "    assert result"
DIR_ERRNO = PREFIX + '["listdir_errno"] in (errno.ENOENT, errno.EACCES)'
VERIFIED = {
    PRIOR_FAILED / "controls/v4-accept-null-listdir-errno/RESULT.json": "163f7459487fdb2c384b31bd19ea8437147373dbda00527e1e6c86e92967e2a9",
    MAIN / HARNESS: "f0a04529dd91454887fad7a8bc62fa0cc6b3956bc85168ec2c55b125b67d9fbc",
    PRIOR_FAILED / "SOURCE-CONTROL.sha256": "0b363fa287f5c0ad6a0275fc36f12127eb1774fe53972e039d84dec703bb2640",
    V2 / "controls.py": "88d04027135b5492bca408ce35396de12cf2ba57a31ada2c7cd5ed3eb6a555b6",
    V3 / "SOURCE-CONTROL.sha256": "f0f7978b540f0f83d5c5fef3e4f8e45badb11475d4c4d35cae74ea8584816c4b",
    CASE / "case.json": "d7a455b74aa99393979341d60bae2d5f62a2b2edfd623425c952561dfe4f2aba",
    BOUNDARY: "932f3b0d16e5bbd8f439d0f5d9df3d8507955dae5482e0207ad3ae0cb15c2dbb",
    MAIN / TEST: "92e8c58690675e54b8cc30704a1303a97513b61749bbf01910e5885709547ede",
    ACTUAL_CPU / TEST: "ec4b7a967e6e2450e0ee7662e62890424b917f492fa375d29078e47fe0cf8c8c",
}


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def check(path, expected):
    if digest(path) != expected:
        raise ValueError(f"control input changed: {path}")


def stage_control_sources(scratch):
    for path, expected in VERIFIED.items():
        check(path, expected)
    for line in (V3 / "SOURCE-CONTROL.sha256").read_text().splitlines():
        expected, name = line.split(maxsplit=1)
        check(V3 / name, expected)
    spec = importlib.util.spec_from_file_location("unchanged_tu_parser_controls", V2 / "controls.py")
    prior = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prior)
    parser_checks = prior.parser_controls(scratch)
    original = (MAIN / TEST).read_text()
    if original.count(SKIP) != 1 or original.count(DIR_ERRNO) != 1:
        raise RuntimeError("canonical accepted source no longer matches expected witness points")
    extra_refusal = (
        '        if "cannot unshare" in str(exc).lower():\n'
        '            pytest.skip(str(exc))\n'
    )
    extra_mount_skip = (
        '        if "unshare" in str(exc).lower() and "operation not permitted" in str(exc).lower():\n'
        '            pytest.skip(str(exc))\n'
    )
    # Each mutation widens one condition only. All other candidate logic stays exact.
    witnesses = {
        "accepted-main-class": prior.qualified_class(original),
        "skip-invalid-namespace": original.replace(SKIP, SKIP + "\n" + extra_refusal.rstrip()),
        "skip-mount-path-marker": original.replace(SKIP, SKIP + "\n" + extra_mount_skip.rstrip()),
        "accept-wrong-listdir-errno": original.replace(DIR_ERRNO, PREFIX + '["listdir_errno"] is not None'),
        "accept-null-listdir-errno": original.replace(DIR_ERRNO, DIR_ERRNO[:-1] + ", None)"),
    }
    for name, text in witnesses.items():
        compile(text, str(TEST), "exec")
        path = scratch / name
        shutil.copytree(MAIN, path, ignore=shutil.ignore_patterns(".pytest_cache", "__pycache__"))
        (path / TEST).write_text(text)
        if name == "accept-null-listdir-errno":
            # The original helper rejects a null failing errno before its caller
            # can see it. Relax only the listdir/null pair in this mutant.
            helper = (MAIN / HARNESS).read_text()
            if helper.count(HARNESS_ERRNO) != 1:
                raise RuntimeError("canonical helper's errno validation changed")
            helper = helper.replace(HARNESS_ERRNO,
                'or (not ok and not (operation == "listdir" and error is None) '
                'and (type(error) is not int or error <= 0))')
            compile(helper, str(HARNESS), "exec")
            (path / HARNESS).write_text(helper)
    return parser_checks


def run(group, oracle, lane, rc, marker):
    before = {str(path): digest(lane / path) for path in (TEST, HARNESS)}
    proc = subprocess.run([sys.executable, "-IB", str(oracle), str(lane)],
                          timeout=185, capture_output=True)
    if {str(path): digest(lane / path) for path in (TEST, HARNESS)} != before:
        raise RuntimeError("contained evaluator changed candidate bytes")
    result = (proc.stdout or proc.stderr).decode(errors="replace").splitlines()[:1]
    record = {"group": group, "rc": proc.returncode,  "first_diagnostic": result,
              "test_sha256": before[str(TEST)], "harness_sha256": before[str(HARNESS)],
              "oracle_sha256": digest(oracle), "expected_rc": rc, "expected_marker": marker}
    out = HERE / "controls" / group
    out.mkdir(parents=True)
    (out / "stdout.log").write_bytes(proc.stdout)
    (out / "stderr.log").write_bytes(proc.stderr)
    (out / "RESULT.json").write_text(json.dumps(record, indent=2) + "\n")
    if proc.returncode != rc or not result or marker not in result[0]:
        raise RuntimeError(f"V4 controlled witness failed: {record}")
    return record


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--execute", action="store_true")
    args = cli.parse_args()
    with tempfile.TemporaryDirectory(prefix="v4-controls-", dir=HERE) as temp:
        scratch = Path(temp)
        parser_checks = stage_control_sources(scratch)
        if not args.execute:
            print(json.dumps({"prepared": True, "parser_checks": parser_checks,
                              "candidate_executions": 0, "model_calls": 0}))
            return
        v3, v4 = V3 / "oracle.py", HERE / "oracle.py"
        # Qualify the unmodified known positives before interpreting any new rejection.
        observations = [
            run("main-function-positive", v4, MAIN, 0, "TU-GR-1 contract passed"),
            run("main-class-positive", v4, scratch / "accepted-main-class", 0, "TU-GR-1 contract passed"),
        ]
        cases = [
            ("skip-invalid-namespace", "namespace-invalid-argument"),
            ("skip-mount-path-marker", "mount-permission-path-unshare"),
            ("accept-wrong-listdir-errno", "wrong-listdir-errno-only"),
            ("accept-null-listdir-errno", "null-listdir-errno-only"),
        ]
        for name, marker in cases:
            lane = scratch / name
            observations.append(run("v3-" + name, v3, lane, 0, "TU-GR-1 contract passed"))
            observations.append(run("v4-" + name, v4, lane, 1, "simulated namespace " + marker))
        observations += [
            run("actual-cpu-paid2-v3", v3, ACTUAL_CPU, 0, "TU-GR-1 contract passed"),
            run("actual-cpu-paid2-v4", v4, ACTUAL_CPU, 1, "simulated namespace namespace-invalid-argument"),
            run("actual-auto-ci2-v3", v3, ACTUAL_AUTO, 0, "TU-GR-1 contract passed"),
            run("actual-auto-ci2-v4", v4, ACTUAL_AUTO, 1, "simulated namespace mount-permission-path-unshare"),
        ]
        output = {"schema": "tu-grader-isolation.v4.controls", "rows": observations,
                  "parser_controls_unchanged": parser_checks, "model_calls": 0,
                  "previous_grade_artifacts_unchanged": True}
        with (HERE / "CONTROL.json").open("x") as handle:
            json.dump(output, handle, indent=2)
            handle.write("\n")
        print(json.dumps({"qualified_rows": len(observations), "model_calls": 0}))


if __name__ == "__main__":
    main()
