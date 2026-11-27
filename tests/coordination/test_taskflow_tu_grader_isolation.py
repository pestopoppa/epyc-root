import shlex
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "coordination"))
from taskflow import dispatch, tu_grader_isolation, verify  # noqa: E402


_TEST_FILE = "scripts/autopilot/evals/dtap/tests/test_grader_isolation.py"
_ACCEPTANCE = f"{shlex.quote(sys.executable)} -m pytest -q {_TEST_FILE}"


@pytest.fixture
def lane(tmp_path):
    patch = Path(__file__).with_name("taskflow_tu_grader_isolation_sound.patch")
    subprocess.run(["git", "apply", str(patch)], cwd=tmp_path, check=True)
    return tmp_path


def test_contract_accepts_correct_probe_and_narrow_skip(lane):
    test = lane / _TEST_FILE
    original = test.read_text()
    test.write_text(original.replace('"--user", "--map-root-user", "--mount"', '"-Urnm"')
                    .replace('mount -t tmpfs none', 'mount --make-rprivate / && mount -t tmpfs -o mode=0700 tmpfs')
                    .replace("    try:\n        result = probe_grader_access(sentinel, launcher)",
                             '    try:\n        subprocess.run(["unshare", "-Urnm", "true"], check=True, '
                             "capture_output=True, text=True)\n"
                             "        result = probe_grader_access(sentinel, launcher)"))
    wrapper = lane / "python.sh"
    wrapper.write_text(f'exec {shlex.quote(sys.executable)} "$@"\n')
    cmd = f"bash {shlex.quote(str(wrapper))} -m pytest -q {_TEST_FILE}"

    assert tu_grader_isolation.validate(lane, cmd, 120) is None


def test_contract_rejects_broad_skip_after_the_capable_case_passes(lane):
    file = lane / _TEST_FILE
    original = file.read_text()
    start = original.index("        if diagnostic in {")
    end = original.index("        }:", start) + len("        }:")
    file.write_text(original[:start] + "        if diagnostic:" + original[end:])

    assert "simulated namespace unrelated-failure" in tu_grader_isolation.validate(lane, _ACCEPTANCE, 120)


def test_contract_rejects_mount_eperm_as_a_sanctioned_skip(lane):
    file = lane / _TEST_FILE
    original = file.read_text()
    file.write_text(original.replace("        if diagnostic in {", '        if diagnostic.startswith("mount:") or diagnostic in {'))

    assert "simulated namespace mount-permission-refusal" in tu_grader_isolation.validate(lane, _ACCEPTANCE, 120)


def test_contract_requires_an_access_errno_instead_of_erofs(lane):
    file = lane / _TEST_FILE
    file.write_text(file.read_text().replace("in {errno.ENOENT, errno.EACCES}", "in {errno.ENOENT, errno.EACCES, errno.EROFS}"))

    assert "simulated namespace wrong-access-errno" in tu_grader_isolation.validate(lane, _ACCEPTANCE, 120)


def test_contract_accepts_class_based_pytest_tests(lane):
    file = lane / _TEST_FILE
    original = file.read_text()
    start = original.index("def test_reachable_grader_is_flagged(")
    body = original[start:].replace("(sentinel):", "(self, sentinel):")
    file.write_text(original[:start] + "class TestGraderIsolation:\n" + textwrap.indent(body, "    "))

    assert tu_grader_isolation.validate(lane, _ACCEPTANCE, 120) is None


def test_contract_rejects_foreign_and_duplicate_junit_results(tmp_path):
    path = tmp_path / "report.xml"
    exact = f'<testcase file="{_TEST_FILE}" classname="test_grader_isolation.TestGraderIsolation" name="test_isolated_launch_denies"/>'
    foreign = '<testcase file="other/test_grader_isolation.py" classname="test_grader_isolation" name="test_isolated_launch_denies"/>'
    path.write_text(f"<testsuite>{foreign}{exact}</testsuite>")
    assert tu_grader_isolation._outcomes(path) == {"test_isolated_launch_denies": ("passed", "")}
    path.write_text(f"<testsuite>{exact}{exact}</testsuite>")
    with pytest.raises(ValueError, match="duplicate results"):
        tu_grader_isolation._outcomes(path)


@pytest.mark.parametrize(("addition", "phase"), [
    ('diagnostic.endswith("Invalid argument")', "namespace-invalid-argument"),
    ('"unshare" in diagnostic and "Operation not permitted" in diagnostic', "mount-permission-path-unshare"),
])
def test_contract_rejects_other_errors_that_resemble_permission_refusals(lane, addition, phase):
    file = lane / _TEST_FILE
    file.write_text(file.read_text().replace("if diagnostic in {", f"if ({addition}) or diagnostic in {{"))

    assert f"simulated namespace {phase}" in tu_grader_isolation.validate(lane, _ACCEPTANCE, 120)


def test_contract_rejects_skipping_on_an_absent_launcher(lane):
    file = lane / _TEST_FILE
    source = file.read_text().replace("import secrets", "import secrets\nimport shutil")
    file.write_text(source.replace(
        '    scratch = sentinel.parent.parent',
        '    if shutil.which("unshare") is None:\n        pytest.skip("unshare unavailable")\n'
        '    scratch = sentinel.parent.parent',
    ))

    assert "simulated namespace missing-launcher" in tu_grader_isolation.validate(lane, _ACCEPTANCE, 120)


@pytest.mark.parametrize(("accepted_errno", "phase"), [
    ("errno.EROFS", "wrong-listdir-errno-only"),
    ("None", "null-listdir-errno-only"),
])
def test_contract_rejects_invalid_directory_errno_with_valid_open_errno(lane, accepted_errno, phase):
    file = lane / _TEST_FILE
    source = file.read_text()
    file.write_text(source.replace(
        'result["listdir_errno"] in {errno.ENOENT, errno.EACCES}',
        f'result["listdir_errno"] in {{errno.ENOENT, errno.EACCES, {accepted_errno}}}',
    ))

    assert f"simulated namespace {phase}" in tu_grader_isolation.validate(lane, _ACCEPTANCE, 120)


def test_contract_keeps_propagation_setup_separate_from_hiding_the_sentinel(lane):
    file = lane / _TEST_FILE
    original = file.read_text()
    original = original.replace('mount -t tmpfs none "$1"', 'mount --make-rprivate /')
    file.write_text(original[:original.index('    assert result["open_ok"] is False')])

    assert "passed without mounting" in tu_grader_isolation.validate(lane, _ACCEPTANCE, 120)


@pytest.mark.parametrize("timeout", [True, False], ids=["timeout", "no-junit-report"])
def test_contract_checker_failures_abort_with_a_diagnostic(tmp_path, monkeypatch, timeout):
    def run(cmd, **kwargs):
        if timeout:
            raise subprocess.TimeoutExpired(cmd, 1)
        return subprocess.CompletedProcess(cmd, 127, "", "pytest: not found")

    monkeypatch.setattr(tu_grader_isolation.subprocess, "run", run)
    expected = "timed out" if timeout else "pytest produced no report"
    with pytest.raises(RuntimeError, match=expected):
        tu_grader_isolation.validate(tmp_path, _ACCEPTANCE, 1)


@pytest.mark.parametrize("outcome,reason,failure_class", [
    ("probe did not access sentinel", "contract-fail", "model-limitation"),
    (ImportError("checker module missing"), "contract-unavailable", "harness"),
])
def test_verifier_contract_failure_blocks_reviewer(tmp_path, monkeypatch, outcome, reason, failure_class):
    def run(lane, acceptance, timeout):
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(tu_grader_isolation, "validate", run)
    monkeypatch.setattr(verify, "_git", lambda *args: "test\n")
    monkeypatch.setattr(verify, "run_tests", lambda *args: [])

    def reviewer(*args):
        pytest.fail("reviewer called after contract failure")

    task = {"id": "TU-GR-1", "outputs": ["test"], "acceptance": _ACCEPTANCE}
    result = verify.verify(task, tmp_path, "base", reviewer=reviewer)
    assert result["verdict"] == "rejected"
    assert result["reason"] == reason
    assert result["checks"][-1]["check"] == "candidate-contract"
    worker = {"usage": {"steps": 2}, "tools": ["write"], "tool_errors": ["denied"]}
    assert dispatch.failure_class(worker, result, task) == failure_class
