#!/usr/bin/env python3
"""cpu_str helper, template use, and the CPUS-IN-ARGV lint (2026-11-24)."""
import json
import os
import sys

_T = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_T), "rowflow"))
import ak_row_harness as H  # noqa: E402
import ak_row_lint as LINT  # noqa: E402
import mk_ak_row as MK  # noqa: E402


def test_cpu_str_ranges():
    assert H.cpu_str(list(range(24)) + list(range(48, 72))) == "0-23,48-71"
    assert H.cpu_str([5, 3, 4, 9, 3]) == "3-5,9"
    assert H.cpu_str([7]) == "7" and H.cpu_str("84-87") == "84-87" and H.cpu_str([]) == ""


def test_template_has_cpu_str_and_uses_it():
    src = open(MK.__file__).read()
    assert "def cpu_str():" in src and "H.cpu_str(cpus())" in src
    assert "cpus()," not in src.replace("H.cpu_str(cpus())", "")  # the template builds no argv with the raw list


def _lint(tmp_path, body):
    d = tmp_path / "ak-t-20261124"
    d.mkdir()
    (d / "job.py").write_text(body)
    (d / "launch.sh").write_text("")
    (d / "spec.json").write_text(json.dumps({"id": "ak-t-20261124"}))
    return {(l, c) for l, c, _ in LINT.lint_dir(str(d), selftest=False)}


def test_lint_catches_list_in_argv(tmp_path):
    assert ("WARN", "CPUS-IN-ARGV") in _lint(tmp_path, 'argv = ["taskset", "-c", cpus(), "x"]\n')


def test_lint_catches_concat(tmp_path):
    assert any(c == "CPUS-IN-ARGV" for _, c in _lint(tmp_path, 'argv = ["taskset", "-c"] + [H.grant_cpus()]\n'))


def test_lint_passes_cpu_str(tmp_path):
    assert not any(c == "CPUS-IN-ARGV" for _, c in _lint(
        tmp_path, 'a = ["taskset", "-c", cpu_str(), "x"]\nb = ["taskset", "-c", ",".join(map(str, cpus()))]\n'))


if __name__ == "__main__":
    raise SystemExit("REFUSING: pytest-fixture suite; run: python -m pytest scripts/coordination/tests/test_cpu_str_lint.py -q")
