"""Explicit ingest ledger flags must resolve before any real ledger or lock opens."""

import sys
from contextlib import nullcontext
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
import cli

# autokernel-experiments has its own explicit-target/dry-run guard, covered by
# test_autokernel_experiments. Every other route constructs through _ledger_path.
ADAPTERS = ("intake", "autokernel", "inf70", "autokernel-serving", *cli._FILE_SOURCES)


def _run_without_opening_ledger(monkeypatch, argv, expected):
    selected = []

    class ProbeLedger:
        def write_lock(self):
            return nullcontext()

    marker = ProbeLedger()

    def constructor(path):
        # This assertion fires at the boundary, before a wrong path could open.
        assert Path(path) == expected
        selected.append(Path(path))
        return marker

    def dispatch(args):
        assert cli._ledger(args) is marker
        return 0

    monkeypatch.setattr(cli, "Ledger", constructor)
    monkeypatch.setattr(cli, "_cmd_ingest", dispatch)
    assert cli.main(argv) == 0
    assert selected and all(path == expected for path in selected)
    assert not expected.exists()


@pytest.mark.parametrize("adapter", ADAPTERS)
@pytest.mark.parametrize("position", ("global", "ingest"))
def test_all_ingest_routes_honor_explicit_ledger(
    monkeypatch, tmp_path, adapter, position
):
    target = tmp_path / "private.jsonl"
    args = [
        "ingest",
        adapter,
        "--root",
        str(tmp_path),
        "--as-of",
        "2026-10-29T00:00:00Z",
    ]
    flag = ["--ledger", str(target)]
    argv = flag + args if position == "global" else args + flag
    _run_without_opening_ledger(monkeypatch, argv, target)


def test_post_ingest_ledger_keeps_existing_precedence_when_both_are_given(
    monkeypatch, tmp_path
):
    global_target = tmp_path / "global.jsonl"
    ingest_target = tmp_path / "ingest.jsonl"
    _run_without_opening_ledger(
        monkeypatch,
        [
            "--ledger",
            str(global_target),
            "ingest",
            "calendar-overrun",
            "--ledger",
            str(ingest_target),
        ],
        ingest_target,
    )
    assert not global_target.exists()


@pytest.mark.parametrize(
    "mode", ("default", "environment", "scratch-flag", "scratch-environment")
)
def test_default_environment_and_scratch_fallbacks_are_unchanged(
    monkeypatch, tmp_path, mode
):
    monkeypatch.delenv("VIDYA_LEDGER", raising=False)
    monkeypatch.delenv("VIDYA_SCRATCH", raising=False)
    monkeypatch.setenv("VIDYA_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setattr(cli, "REPO_ROOT", tmp_path / "worktree")
    target = tmp_path / "state" / "ledger.jsonl"
    prefix = []
    if mode == "environment":
        target = tmp_path / "environment.jsonl"
        monkeypatch.setenv("VIDYA_LEDGER", str(target))
    elif mode == "scratch-flag":
        prefix = ["--scratch"]
        target = cli.scratch_ledger_path(cli.REPO_ROOT)
        monkeypatch.setenv("VIDYA_LEDGER", str(tmp_path / "environment.jsonl"))
    elif mode == "scratch-environment":
        monkeypatch.setenv("VIDYA_SCRATCH", "1")
        target = cli.scratch_ledger_path(cli.REPO_ROOT)
    _run_without_opening_ledger(
        monkeypatch, prefix + ["ingest", "calendar-overrun"], target
    )


@pytest.mark.parametrize("position", ("global", "ingest"))
def test_explicit_ledger_still_beats_scratch_and_environment(
    monkeypatch, tmp_path, position
):
    target = tmp_path / "explicit.jsonl"
    monkeypatch.setenv("VIDYA_LEDGER", str(tmp_path / "environment.jsonl"))
    monkeypatch.setenv("VIDYA_SCRATCH", "1")
    flag = ["--ledger", str(target)]
    command = ["ingest", "calendar-overrun"]
    argv = ["--scratch", *(flag + command if position == "global" else command + flag)]
    _run_without_opening_ledger(monkeypatch, argv, target)
