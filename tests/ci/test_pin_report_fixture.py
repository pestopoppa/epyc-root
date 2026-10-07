"""Prospective controls use the unchanged actual checker on synthetic Git roots."""
from __future__ import annotations
import copy
import hashlib
import importlib.util
import json
import shutil
import os
from pathlib import Path
import subprocess
import sys

import pytest
from scripts.ci.pin_report_fixture import (capture_report_fixture, project_report_fixture,
                                          read_report, read_report_fixture, validate_report, write_report)


def _report(tmp_path, world="current", *, track_checker=True):
    original = Path(os.environ["EPYC_INFERENCE_RESEARCH_REPO"]) / "scripts/benchmark/check_pin_staleness.py"
    assert original.is_file() and not original.is_symlink()
    root = tmp_path / "synthetic-research"
    source = root / "scripts/benchmark"
    source.mkdir(parents=True)
    checker = source / "check_pin_staleness.py"
    checker.write_bytes(original.read_bytes())
    target = root / "target.txt"
    target.write_bytes(b"current synthetic pin target\n")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    expression = repr(str(target)) if world != "unresolved" else "get_dynamic_target()"
    (source / "probe.py").write_text(
        f"EXPECTED_TARGET_SHA256 = {digest!r}\n"
        f"file_identity(Path({expression}), EXPECTED_TARGET_SHA256)\n")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "scripts/benchmark", "target.txt"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=Synthetic fixture",
                    "-c", "user.email=synthetic@example.invalid", "commit", "-qm", "synthetic source"], check=True)
    if not track_checker:
        subprocess.run(["git", "-C", str(root), "rm", "--cached", "scripts/benchmark/check_pin_staleness.py"], check=True)
    if world == "stale":
        target.write_bytes(b"changed synthetic target\n")
    elif world == "missing":
        target.unlink()
    name = "synthetic_pin_report_checker_" + hashlib.sha256(str(root).encode()).hexdigest()
    spec = importlib.util.spec_from_file_location(name, checker)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        return module.inspect_tree(root)
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize("world", ["current", "stale", "missing", "unresolved"])
def test_actual_report_roundtrip_preserves_current_stale_and_unknown(tmp_path, world):
    report = _report(tmp_path, world)
    assert report["counts"][world] == 1
    assert report["complete"] is (world in {"current", "stale"})
    pin = write_report(tmp_path, "report.json", report)
    reopened = read_report(tmp_path, "report.json", pin["sha256"])
    assert reopened == report
    if world == "stale":
        assert reopened["complete"] is True
        assert reopened["counts"]["stale"] == 1


@pytest.mark.parametrize("mutation", ["count", "complete", "git_stable", "checker_match", "boolean_count",
                                      "scope", "dirty_count", "unread_source", "path_normalization"])
def test_actual_report_metadata_drift_is_refused(tmp_path, mutation):
    report = copy.deepcopy(_report(tmp_path))
    if mutation == "count":
        report["counts"]["current"] += 1
    elif mutation == "complete":
        report["complete"] = False
    elif mutation == "git_stable":
        report["root_git"]["stable"] = False
    elif mutation == "checker_match":
        report["checker_source"]["matches_scanned_copy"] = False
    elif mutation == "boolean_count":
        report["counts"]["current"] = True
    elif mutation == "scope":
        report["stability_scope"] = "atomic whole-checkout proof"
    elif mutation == "dirty_count":
        for key in ("before", "after"):
            report["root_git"][key]["tracked_dirty"] = True
    elif mutation == "unread_source":
        report["source_file_identities"][1] = {"path": "scripts/benchmark/probe.py",
            "status": "missing", "reason": "source absent"}
    else:
        report["source_file_identities"][1]["path"] = "scripts//benchmark/probe.py"
        report["rows"][0]["source"] = "scripts//benchmark/probe.py"
    with pytest.raises(ValueError):
        write_report(tmp_path, "refused.json", report)
    assert not (tmp_path / "refused.json").exists()


def test_original_report_hash_and_duplicate_json_fields_are_refused(tmp_path):
    report = _report(tmp_path)
    pin = write_report(tmp_path, "report.json", report)
    path = tmp_path / "report.json"
    original = path.read_bytes()
    path.write_bytes(original + b" ")
    with pytest.raises(ValueError, match="digest differ"):
        read_report(tmp_path, "report.json", pin["sha256"])
    duplicate = original.replace(b'{"checker_source":', b'{"schema":"duplicate","checker_source":', 1)
    assert duplicate != original
    path.write_bytes(duplicate)
    with pytest.raises(ValueError, match="duplicate report JSON key"):
        read_report(tmp_path, "report.json", hashlib.sha256(duplicate).hexdigest())


def test_report_writer_refuses_overwrite_and_symlink_parents(tmp_path):
    report = _report(tmp_path)
    pin = write_report(tmp_path, "report.json", report)
    with pytest.raises(FileExistsError):
        write_report(tmp_path, "report.json", report)
    assert read_report(tmp_path, "report.json", pin["sha256"]) == report
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (tmp_path / "link").symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(OSError):
        write_report(tmp_path, "link/report.json", report)
    assert not (elsewhere / "report.json").exists()


def test_missing_scanned_checker_remains_incomplete_without_tuple_upgrade(tmp_path):
    report = _report(tmp_path, track_checker=False)
    assert report["checker_source"]["matches_scanned_copy"] is None
    assert report["counts"]["unresolved"] == 1
    assert validate_report(report)["complete"] is False
    pin = write_report(tmp_path, "incomplete-report.json", report)
    assert read_report(tmp_path, "incomplete-report.json", pin["sha256"]) == report


@pytest.mark.parametrize("fail_call", [1, 2], ids=["file", "directory"])
def test_failed_file_or_directory_fsync_removes_only_owned_report_for_retry(tmp_path, monkeypatch, fail_call):
    from scripts.ci import pin_report_fixture as writer
    report = _report(tmp_path)
    unrelated = tmp_path / "unrelated.json"
    unrelated.write_bytes(b"retain unrelated output\n")
    real_fsync = writer.os.fsync
    calls = 0
    def fail_once(fd):
        nonlocal calls
        calls += 1
        if calls == fail_call:
            raise OSError("injected report fsync failure")
        return real_fsync(fd)
    monkeypatch.setattr(writer.os, "fsync", fail_once)
    with pytest.raises(OSError, match="injected report fsync failure"):
        write_report(tmp_path, "report.json", report)
    assert not (tmp_path / "report.json").exists()
    assert unrelated.read_bytes() == b"retain unrelated output\n"
    monkeypatch.setattr(writer.os, "fsync", real_fsync)
    pin = write_report(tmp_path, "report.json", report)
    assert read_report(tmp_path, "report.json", pin["sha256"]) == report


def _native_report(tmp_path, monkeypatch, outcome="true", world="current"):
    report = _report(tmp_path, world)
    synthetic = Path(report["root"])
    if world in {"stale", "missing"}:
        # Native carrier requires clean tracked Git. Preserve the deliberately old
        # probe digest while committing the actual changed/deleted target world.
        subprocess.run(["git", "-C", str(synthetic), "add", "-u", "--", "target.txt"], check=True)
        subprocess.run(["git", "-C", str(synthetic), "-c", "user.name=Synthetic fixture",
                        "-c", "user.email=synthetic@example.invalid", "commit", "-qm", "synthetic target world"], check=True)
    case = synthetic / "test_actual_report_attachment.py"
    # This generated source is captured as a read input before actual pytest.
    case.write_text(
        "import runpy\nfrom pathlib import Path\nimport pytest\n"
        "from scripts.ci.pin_report_fixture import write_report\n"
        "def test_actual_report_attachment():\n"
        f"    source = runpy.run_path({str(synthetic / 'scripts/benchmark/check_pin_staleness.py')!r})\n"
        f"    report = source['inspect_tree'](Path({str(synthetic)!r}))\n"
        f"    assert report['counts'][{world!r}] == 1\n"
        f"    write_report(Path({str(synthetic)!r}), 'pin-report.json', report)\n"
        + ("    pytest.skip('explicit unexecuted fixture verdict')\n" if outcome == "null" else
           "    assert False, 'explicit native FALSE control'\n" if outcome == "false" else
           f"    assert report['complete'] is {world in {'current', 'stale'}}\n"))
    root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("PYTHONPATH", str(root))
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    monkeypatch.setenv("PYTEST_ADDOPTS", "")
    monkeypatch.setenv("PYTEST_PLUGINS", "")
    output = tmp_path / "captured-original"
    capture_report_fixture(report_relative="pin-report.json",
        argv=[sys.executable, "-m", "pytest", "--noconftest", "-c", "/dev/null",
              "--import-mode=importlib", "--rootdir=" + str(synthetic), "--junitxml=" + str(synthetic / "original.junit.xml"), str(case)],
        cwd=synthetic, junit=synthetic / "original.junit.xml", output=output,
        repositories={"synthetic_research": synthetic},
        read_paths=[case, synthetic / "scripts/benchmark/check_pin_staleness.py",
                    synthetic / "scripts/benchmark/probe.py", root / "scripts/ci/pin_report_fixture.py"],
        selections=[str(case) + "::test_actual_report_attachment"])
    return output / "receipt.json"


@pytest.mark.parametrize("outcome,world", [("true", "current"), ("true", "stale"), ("true", "missing"), ("true", "unresolved"),
                                            ("false", "current"), ("null", "current")],
                         ids=["current_TRUE", "stale_TRUE", "missing_TRUE", "unresolved_TRUE", "current_FALSE", "current_NULL"])
def test_actual_native_attachment_projection_preserves_true_false_null(tmp_path, monkeypatch, outcome, world):
    receipt = _native_report(tmp_path, monkeypatch, outcome, world)
    original = {str(p.relative_to(receipt.parent)): p.read_bytes()
                for p in receipt.parent.rglob("*") if p.is_file()}
    record, digest, report = read_report_fixture(receipt, "pin-report.json")
    tuples, reopened = project_report_fixture(receipt, "pin-report.json")
    assert reopened == report
    expected = {"true": True, "false": False, "null": None}[outcome]
    assert record["fixture_execution_conformant"] is expected
    assert record["summary"]["cases"] == [{"classname": "test_actual_report_attachment",
        "name": "test_actual_report_attachment",
        "status": {"true": "passed", "false": "failure", "null": "skipped"}[outcome]}]
    if expected is None:
        assert tuples == ()
    else:
        from claim_tuple import grade
        assert len(tuples) == 1
        assert tuples[0].metric == "fixture_execution_conformant"
        assert tuples[0].value is expected
        assert grade(tuples[0])[:2] == ("Judged", "Located")
    if world == "stale":
        assert report["complete"] is True and report["counts"]["stale"] == 1
    assert digest
    assert original == {str(p.relative_to(receipt.parent)): p.read_bytes()
                        for p in receipt.parent.rglob("*") if p.is_file()}


@pytest.mark.parametrize("damage", ["absent", "tampered", "mixed"])
def test_actual_original_attachment_refuses_absent_tampered_or_mixed_receipts(tmp_path, monkeypatch, damage):
    left = tmp_path / "left"
    left.mkdir()
    receipt = _native_report(left, monkeypatch)
    damaged = tmp_path / "damaged-copy"
    shutil.copytree(receipt.parent, damaged)
    if damage == "absent":
        with pytest.raises(ValueError, match="attachment absent"):
            read_report_fixture(damaged / "receipt.json", "undeclared-report.json")
    elif damage == "tampered":
        record = json.loads((damaged / "receipt.json").read_bytes())
        target = damaged / record["generated_outputs"][0]["artifact"]["name"]
        target.write_bytes(target.read_bytes() + b" ")
        with pytest.raises(ValueError):
            project_report_fixture(damaged / "receipt.json", "pin-report.json")
    else:
        right = tmp_path / "right"
        right.mkdir()
        other = _native_report(right, monkeypatch, world="stale")
        (damaged / "receipt.json").write_bytes(other.read_bytes())
        with pytest.raises(ValueError):
            project_report_fixture(damaged / "receipt.json", "pin-report.json")
    assert read_report_fixture(receipt, "pin-report.json")[2]["counts"]["current"] == 1


def test_partial_write_is_removed_without_deleting_unrelated_output(tmp_path, monkeypatch):
    from scripts.ci import pin_report_fixture as writer
    report = _report(tmp_path)
    unrelated = tmp_path / "retained.json"
    unrelated.write_bytes(b"unrelated original\n")
    real_fdopen = writer.os.fdopen
    class ShortWriter:
        def __init__(self, handle):
            self.handle = handle
        def __enter__(self):
            self.handle.__enter__()
            return self
        def __exit__(self, *args):
            return self.handle.__exit__(*args)
        def write(self, data):
            return self.handle.write(data[:len(data) // 2])
    monkeypatch.setattr(writer.os, "fdopen", lambda fd, mode: ShortWriter(real_fdopen(fd, mode)))
    with pytest.raises(OSError, match="short report write"):
        write_report(tmp_path, "partial.json", report)
    assert not (tmp_path / "partial.json").exists()
    assert unrelated.read_bytes() == b"unrelated original\n"
    monkeypatch.setattr(writer.os, "fdopen", real_fdopen)
    pin = write_report(tmp_path, "partial.json", report)
    assert read_report(tmp_path, "partial.json", pin["sha256"]) == report


def test_failure_cleanup_refuses_to_unlink_replaced_exclusive_name(tmp_path, monkeypatch):
    from scripts.ci import pin_report_fixture as writer
    report = _report(tmp_path)
    path = tmp_path / "report.json"
    real_fsync = writer.os.fsync
    def replace_then_fail(fd):
        path.unlink()
        path.write_bytes(b"different owner's replacement\n")
        raise OSError("injected replacement during failed write")
    monkeypatch.setattr(writer.os, "fsync", replace_then_fail)
    with pytest.raises(RuntimeError, match="lost exclusive output ownership"):
        write_report(tmp_path, "report.json", report)
    assert path.read_bytes() == b"different owner's replacement\n"
    monkeypatch.setattr(writer.os, "fsync", real_fsync)
    with pytest.raises(FileExistsError):
        write_report(tmp_path, "report.json", report)
    assert path.read_bytes() == b"different owner's replacement\n"
