"""Real pytest9 exporter controls; synthetic files only, no original run replay."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.ci import native_conformance as nc

PLUGIN_DIR = Path(nc.__file__).parent


def run_pytest(tmp_path, source, *, plugin=True, workers=False, collection_skip=False):
    (tmp_path / "test_parent.py").write_text(source)
    if collection_skip:
        (tmp_path / "test_optional.py").write_text(
            'import pytest\npytest.skip("optional", allow_module_level=True)\n')
    junit = tmp_path / "junit.xml"
    env = dict(os.environ, PYTHONPATH=str(PLUGIN_DIR), PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    argv = [sys.executable, "-m", "pytest", str(tmp_path), "--junitxml", str(junit),
            "-q", "-p", "no:cacheprovider"]
    if plugin:
        argv.extend(["-p", "epyc_pytest_junit_compat"])
    if workers:
        argv.extend(["-p", "xdist.plugin", "-n", "2"])
    completed = subprocess.run(argv, cwd=tmp_path, env=env, capture_output=True, timeout=45)
    assert junit.exists(), completed.stdout.decode() + completed.stderr.decode()
    return completed.returncode, junit.read_bytes()


@pytest.mark.parametrize("workers", [False, True])
def test_real_passed_subtest_reports_have_no_invented_case_identity(tmp_path, workers):
    code, xml = run_pytest(tmp_path,
        'def test_parent(subtests):\n'
        '    for i in range(6):\n'
        '        with subtests.test(i=i):\n'
        '            assert i >= 0\n', workers=workers, collection_skip=True)
    summary = nc.junit_summary(xml)
    assert code == 0
    assert summary["counts"] == dict(passed=1, failure=0, error=0, skipped=0, collected=1, executed=1)
    assert len(summary["cases"]) == 1 and summary["cases"][0]["name"] == "test_parent"
    assert len(summary["collection_skips"]) == 1
    assert summary["subtest_accounting"]["excluded_passed_subtest_reports"] == 6
    assert nc.decide(summary, code) == (True, "")


def test_unmodified_exporter_surplus_remains_a_mismatch(tmp_path):
    code, xml = run_pytest(tmp_path,
        'def test_parent(subtests):\n'
        '    with subtests.test(i=0):\n'
        '        assert True\n', plugin=False)
    assert code == 0
    with pytest.raises(ValueError, match="inconsistent JUnit suite counts"):
        nc.junit_summary(xml)


def test_failed_subtest_never_becomes_true(tmp_path):
    code, xml = run_pytest(tmp_path,
        'def test_parent(subtests):\n'
        '    with subtests.test(i=0):\n'
        '        assert False\n')
    assert code != 0
    try:
        summary = nc.junit_summary(xml)
    except ValueError as exc:
        assert str(exc) in {"ambiguous case status", "inconsistent JUnit suite counts"}
        return  # Ambiguous exporter output remains diagnostic.
    assert summary["counts"]["failure"] > 0
    assert nc.decide(summary, code)[0] is False


def test_plugin_without_subtests_keeps_plain_summary_shape(tmp_path):
    code, xml = run_pytest(tmp_path, 'def test_parent():\n    assert True\n')
    summary = nc.junit_summary(xml)
    assert code == 0 and set(summary) == {"cases", "counts"}


@pytest.mark.parametrize("source", [
    'def test_parent():\n    assert False\n',
    'import pytest\n@pytest.fixture(autouse=True)\n'
    'def broken():\n    raise RuntimeError("setup failure")\n'
    'def test_parent():\n    assert True\n',
    'import pytest\n@pytest.fixture(autouse=True)\n'
    'def broken():\n    yield\n    raise RuntimeError("teardown failure")\n'
    'def test_parent():\n    assert True\n',
])
def test_real_parent_setup_and_teardown_failures_never_become_true(tmp_path, source):
    code, xml = run_pytest(tmp_path, source)
    assert code != 0
    try:
        summary = nc.junit_summary(xml)
    except ValueError as exc:
        assert str(exc) in {"ambiguous case status", "inconsistent JUnit suite counts"}
        return
    assert summary["counts"]["failure"] + summary["counts"]["error"] > 0
    assert nc.decide(summary, code)[0] is False
