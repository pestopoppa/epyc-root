from __future__ import annotations

from pathlib import Path

from scripts.lab import quiet_window_queue_report


def _write_queue(root: Path, *, stale: bool = False) -> None:
    active = root / "handoffs" / "active"
    active.mkdir(parents=True)
    table = (
        "| E1 dense-control / P-BENCH-3 batched-decode sweep | x |\n"
        "| J12 think-loop probe | real_suite_v1 |\n"
        "| W8/Fable readiness refresh | x |\n"
    )
    if stale:
        table += "| DS-E1 KV measurement | stale |\n"
    (active / "master-handoff-index.md").write_text(table)
    (active / "bulk-inference-campaign.md").write_text(table)
    (active / "routing-and-optimization-index.md").write_text(
        "E1 dense-control\n"
        "real_suite_v1\n"
        "W8/Fable readiness\n"
        "E2 activation/rollback is closed and DS-E1 is decision-ready, "
        "so neither should be scheduled as next-run work.\n"
    )


def test_quiet_window_queue_report_accepts_current_queue(tmp_path: Path) -> None:
    _write_queue(tmp_path)

    report = quiet_window_queue_report.build_report(tmp_path)

    assert report["schema_version"] == "quiet_window_queue_report.v1"
    assert report["ok"] is True
    assert report["status"] == "ok"
    assert report["blockers"] == []
    assert report["findings"] == []


def test_quiet_window_queue_report_flags_stale_active_rows(tmp_path: Path) -> None:
    _write_queue(tmp_path, stale=True)

    report = quiet_window_queue_report.build_report(tmp_path)

    assert report["ok"] is False
    assert report["status"] == "attention"
    assert "DS-E1 appears as an active quiet-window task" in report["blockers"]
    assert report["findings"][0]["severity"] == "high"


def test_quiet_window_queue_report_flags_missing_routing_guard(tmp_path: Path) -> None:
    _write_queue(tmp_path)
    routing = tmp_path / "handoffs" / "active" / "routing-and-optimization-index.md"
    routing.write_text("E1 dense-control\nreal_suite_v1\nW8/Fable readiness\n")

    report = quiet_window_queue_report.build_report(tmp_path)

    assert report["ok"] is False
    assert any(
        "routing index does not explicitly keep closed E2" in finding["issue"]
        for finding in report["findings"]
    )
