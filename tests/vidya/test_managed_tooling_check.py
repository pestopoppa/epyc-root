"""Prospective named managed-interpreter import receipt and CLI fixtures.

The interpreter is the off-host CI runner's Python; imported modules and spawned
descendants are synthetic. No host health check, installer or kernel is invoked.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import venv

import pytest

ROOT = Path(__file__).resolve().parents[2]
PRODUCER = ROOT / "scripts" / "session" / "managed_tooling_check.py"
VIDYA = ROOT / "scripts" / "vidya"
sys.path.insert(0, str(VIDYA))
import cli  # noqa: E402
from adapters import managed_tooling_check as adapter  # noqa: E402
from claim_tuple import grade  # noqa: E402

AS_OF = "2026-10-05T00:00:00Z"


def _artifact_root(test_name: str, tmp_path: Path) -> Path:
    root = Path(os.environ.get("NI35_FIXTURE_ARTIFACT_ROOT", tmp_path / "retained"))
    path = root / test_name
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


def _kill_captured_group(pgid: int) -> None:
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.02)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.02)
    raise AssertionError(f"fixture-owned process group {pgid} survived TERM/KILL")


def _invoke(tmp_path: Path, *, test_name: str, interpreter: Path | None = None,
            module_source: str = "value = 1\n", extra_env: dict[str, str] | None = None,
            pythonpath: Path | None = None, check_source_exists: bool = True,
            timeout: int = 45) -> tuple[subprocess.CompletedProcess,
                                                                         Path, Path]:
    root = _artifact_root(test_name, tmp_path)
    source = tmp_path / f"{test_name}.check-source"
    if check_source_exists:
        source.write_text("named managed import check fixture\n")
    import_dir = tmp_path / f"{test_name}.modules"
    import_dir.mkdir()
    (import_dir / "pytest.py").write_text(module_source)
    output = root / "capture"
    output.mkdir(mode=0o700)
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["NI35_OUTPUT_ROOT"] = str(output)
    env["NI35_MUTATE_CHECK_SOURCE"] = str(source)
    if pythonpath is not None:
        env["PYTHONPATH"] = str(pythonpath)
    elif module_source:
        env["PYTHONPATH"] = str(import_dir)
    if extra_env:
        env.update(extra_env)
    actual_interpreter = interpreter or Path(sys.executable)
    argv = [sys.executable, str(PRODUCER), "--check-id", "epyc-orchestrator-pytest-import",
            "--interpreter", str(actual_interpreter), "--module", "pytest",
            "--check-source", str(source), "--output-root", str(output)]
    try:
        completed = subprocess.run(argv, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        group_marker = env.get("NI35_PROCESS_GROUP")
        if group_marker and Path(group_marker).is_file():
            _kill_captured_group(int(Path(group_marker).read_text()))
        raise
    run_dirs = sorted(p for p in output.iterdir() if p.is_dir())
    assert len(run_dirs) == 1, completed.stderr.decode(errors="replace")
    return completed, run_dirs[0], root


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _reseal_receipt(run_dir: Path, record: dict) -> None:
    record.pop("receipt_sha256", None)
    record["receipt_sha256"] = hashlib.sha256(_canonical(record)).hexdigest()
    path = run_dir / "receipt.json"
    path.chmod(0o600)
    path.write_bytes(_canonical(record))
    path.chmod(0o400)


def _cli_dry_run(receipt: Path, tmp_path: Path, capsys) -> dict:
    ledger = tmp_path / "dry-run-ledger.jsonl"
    rc = cli.main(["--ledger", str(ledger), "--json", "ingest", "managed-tooling-check",
                   "--path", str(receipt), "--as-of", AS_OF, "--dry-run"])
    report = json.loads(capsys.readouterr().out)
    assert rc == 0, report
    assert report["dry_run"] is True
    assert not ledger.exists() or ledger.stat().st_size == 0
    return report


def test_named_positive_import_keeps_original_child_evidence_and_cli_row(tmp_path, capsys):
    module = "import sys\nprint('fixture stdout')\nprint('fixture stderr', file=sys.stderr)\n"
    completed, run_dir, _ = _invoke(tmp_path, test_name="positive", module_source=module)
    assert completed.returncode == 0, completed.stderr.decode(errors="replace")
    record, _ = adapter.read_receipt(run_dir / "receipt.json")
    assert record["verdict"] is True and record["exit_code"] == 0
    assert record["child_pid"] > 0 and record["child_cleanup_ok"] is True
    assert record["stdout"]["name"] == "stdout.bin"
    assert record["stderr"]["name"] == "stderr.bin"
    assert (run_dir / "stdout.bin").read_bytes() == b"fixture stdout\n"
    assert (run_dir / "stderr.bin").read_bytes() == b"fixture stderr\n"
    child = json.loads((run_dir / "child-metadata.bin").read_bytes())
    assert child["python"] == record["interpreter"]
    assert child["module"]["origin"].endswith("/pytest.py")
    assert child["module"]["name"] == record["module_name"]
    claim = adapter.project_managed_tooling_check(adapter.native_rows(
        run_dir / "receipt.json")[0])
    assert claim.value is True and grade(claim)[:2] == ("Judged", "Located")
    report = _cli_dry_run(run_dir / "receipt.json", tmp_path, capsys)
    assert report["units_matched"] == report["units_projected"] == 1
    assert report["rows_projected"] == 1 and report["frames_emitted"] == 3
    assert report["declined"] == [] and report["refused"] == []


def test_missing_module_is_an_executed_false_import_and_cli_row(tmp_path, capsys):
    venv_dir = tmp_path / "empty-venv"
    venv.EnvBuilder(with_pip=False).create(venv_dir)
    interpreter = venv_dir / "bin" / "python"
    completed, run_dir, _ = _invoke(tmp_path, test_name="missing-module",
                                    interpreter=interpreter, module_source="", pythonpath=None)
    assert completed.returncode == 1
    record, _ = adapter.read_receipt(run_dir / "receipt.json")
    assert record["execution_started"] is True and record["child_pid"] > 0
    assert record["exit_code"] != 0 and record["verdict"] is False
    assert record["import_succeeded"] is False
    assert record["import_error"]["type"] == "ModuleNotFoundError"
    assert "attempted to import module pytest" in record["decided_proposition"]
    claim = adapter.project_managed_tooling_check(adapter.native_rows(
        run_dir / "receipt.json")[0])
    assert claim.value is False and grade(claim)[:2] == ("Judged", "Located")
    report = _cli_dry_run(run_dir / "receipt.json", tmp_path, capsys)
    assert report["units_projected"] == 1 and report["rows_projected"] == 1
    assert report["frames_emitted"] == 3 and report["declined"] == []


def test_missing_interpreter_is_preexecution_diagnostic_and_cli_decline(tmp_path, capsys):
    missing = tmp_path / "does-not-exist-python"
    completed, run_dir, _ = _invoke(tmp_path, test_name="missing-interpreter",
                                    interpreter=missing)
    assert completed.returncode == 1
    record, _ = adapter.read_receipt(run_dir / "receipt.json")
    assert record["execution_started"] is False and record["child_pid"] is None
    assert record["exit_code"] is None and record["verdict"] is None
    assert "interpreter unavailable before execution" in record["diagnostic"]
    assert adapter.native_rows(run_dir / "receipt.json") == ()
    report = _cli_dry_run(run_dir / "receipt.json", tmp_path, capsys)
    assert report["units_matched"] == 1 and report["units_projected"] == 0
    assert report["rows_projected"] == 0 and report["frames_emitted"] == 0
    assert len(report["declined"]) == 1 and report["refused"] == []


def test_missing_check_source_is_preexecution_diagnostic_and_cli_decline(tmp_path, capsys):
    marker = tmp_path / "single-fallback-import"
    module = ("from pathlib import Path\n"
              "import os\n"
              "with Path(os.environ['NI35_FALLBACK_IMPORT']).open('a') as handle: handle.write('x')\n")
    completed, run_dir, _ = _invoke(tmp_path, test_name="missing-check-source",
        module_source=module, check_source_exists=False,
        extra_env={"NI35_FALLBACK_IMPORT": str(marker)})
    assert completed.returncode == 0
    assert marker.read_text() == "x"
    record, _ = adapter.read_receipt(run_dir / "receipt.json")
    assert record["execution_started"] is False and record["child_pid"] is None
    assert record["exit_code"] is None and record["verdict"] is None
    assert "check source unavailable" in record["diagnostic"]
    assert adapter.native_rows(run_dir / "receipt.json") == ()
    report = _cli_dry_run(run_dir / "receipt.json", tmp_path, capsys)
    assert report["units_matched"] == 1 and report["units_projected"] == 0
    assert report["rows_projected"] == 0 and report["frames_emitted"] == 0
    assert len(report["declined"]) == 1 and report["refused"] == []


def test_check_source_drift_is_diagnostic_null_not_false_import(tmp_path, capsys):
    module = ("from pathlib import Path\n"
              "import os\n"
              "Path(os.environ['NI35_MUTATE_CHECK_SOURCE']).write_text('changed during import\\n')\n")
    completed, run_dir, _ = _invoke(tmp_path, test_name="source-drift", module_source=module,
                                    extra_env=None)
    assert completed.returncode == 0
    record, _ = adapter.read_receipt(run_dir / "receipt.json")
    assert record["exit_code"] == 0 and record["verdict"] is None
    assert "check source identity drifted" in record["diagnostic"]
    assert adapter.native_rows(run_dir / "receipt.json") == ()
    report = _cli_dry_run(run_dir / "receipt.json", tmp_path, capsys)
    assert report["units_matched"] == 1 and report["units_projected"] == 0
    assert report["rows_projected"] == 0 and report["frames_emitted"] == 0
    assert len(report["declined"]) == 1 and report["refused"] == []


def test_timeout_kills_owned_term_ignoring_descendant_and_does_not_retry(tmp_path):
    marker = tmp_path / "descendant.pid"
    count = tmp_path / "imports.count"
    module = ("from pathlib import Path\n"
              "import os, signal, subprocess, sys, time\n"
              "Path(os.environ['NI35_PROCESS_GROUP']).write_text(str(os.getpgrp()))\n"
              "count = Path(os.environ['NI35_IMPORT_COUNT'])\n"
              "count.write_text(count.read_text() + 'x' if count.exists() else 'x')\n"
              "child = subprocess.Popen([sys.executable, '-c', "
              "'import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(90)'], "
              "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
              "Path(os.environ['NI35_DESCENDANT_PID']).write_text(str(child.pid))\n"
              "time.sleep(90)\n")
    completed, run_dir, _ = _invoke(tmp_path, test_name="timeout", module_source=module,
        extra_env={"NI35_DESCENDANT_PID": str(marker), "NI35_IMPORT_COUNT": str(count),
                   "NI35_PROCESS_GROUP": str(tmp_path / "owned-pgid")}, timeout=40)
    assert completed.returncode == 1
    record, _ = adapter.read_receipt(run_dir / "receipt.json")
    assert record["child_timed_out"] is True and record["verdict"] is None
    assert adapter.native_rows(run_dir / "receipt.json") == ()
    assert record["child_pid"] > 0 and record["exit_code"] in (-signal.SIGTERM, -signal.SIGKILL)
    assert record["child_cleanup_ok"] is True
    assert count.read_text() == "x", "timeout handling must not retry the import"
    descendant = int(marker.read_text())
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        proc_stat = Path(f"/proc/{descendant}/stat")
        if not proc_stat.exists():
            break
        fields = proc_stat.read_text().split()
        if len(fields) > 2 and fields[2] in ("Z", "X"):
            break
        time.sleep(0.05)
    else:
        pytest.fail(f"owned descendant {descendant} survived bounded cleanup")


def test_postexecution_seal_failure_does_not_repeat_import(tmp_path):
    count = tmp_path / "seal-failure.count"
    module = ("from pathlib import Path\n"
              "import os\n"
              "count = Path(os.environ['NI35_SEAL_COUNT'])\n"
              "count.write_text(count.read_text() + 'x' if count.exists() else 'x')\n"
              "root = Path(os.environ['NI35_OUTPUT_ROOT'])\n"
              "run_dir = next(path for path in root.iterdir() if path.is_dir())\n"
              "(run_dir / 'receipt.json').write_text('intentional seal collision')\n")
    completed, run_dir, _ = _invoke(tmp_path, test_name="seal-failure", module_source=module,
        extra_env={"NI35_SEAL_COUNT": str(count)})
    assert completed.returncode == 0
    assert count.read_text() == "x", "seal failure after child start must not trigger fallback"
    assert (run_dir / "receipt.json").read_text() == "intentional seal collision"


def test_resealed_wrong_interpreter_metadata_and_child_status_are_refused(tmp_path):
    completed, original, _ = _invoke(tmp_path, test_name="reseal-controls")
    assert completed.returncode == 0
    for test_case, mutate in (
        ("wrong-interpreter", lambda record: record["interpreter"]["executable"].update(
            path="/usr/bin/false", sha256="0" * 64)),
        ("metadata-contradiction", lambda record: record.update(import_succeeded=False)),
        ("capture-status-contradiction", lambda record: record.update(exit_code=2)),
    ):
        case_dir = original.parent / test_case
        case_dir.mkdir(mode=0o700)
        for item in original.iterdir():
            if item.is_file():
                target = case_dir / item.name
                target.write_bytes(item.read_bytes())
                target.chmod(0o400)
        record = json.loads((case_dir / "receipt.json").read_bytes())
        mutate(record)
        _reseal_receipt(case_dir, record)
        with pytest.raises(ValueError):
            adapter.read_receipt(case_dir / "receipt.json")


def test_cli_file_source_list_and_adapter_authority_are_explicit():
    assert "managed-tooling-check" in cli._FILE_SOURCES
    source = __import__("ingest_sources").SOURCES["managed-tooling-check"]
    assert source.module == "managed_tooling_check"
    assert adapter.AUTHORITY == "named_managed_import_check_no_promotion"
