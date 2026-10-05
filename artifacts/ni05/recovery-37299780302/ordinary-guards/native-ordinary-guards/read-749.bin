from datetime import date

from scripts.analysis import searxng_health_report as report


def test_configured_engines_match_live_settings_profile():
    assert report.CONFIGURED_ENGINES == {"bing", "brave", "wikipedia"}


def test_single_brave_failure_is_not_bad_query(monkeypatch, tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "orchestrator.log").write_text(
        "2026-07-06 searxng unresponsive_engines: brave (query='x')\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(report, "SERVER_LOG_DIR", log_dir)
    monkeypatch.setattr(report, "LOG_DIR", tmp_path / "progress")

    tel = report.collect_telemetry(date(2026, 7, 6), date(2026, 7, 6))

    assert tel["unresponsive_events"] == 1
    assert tel["bad_queries"] == 0
    assert tel["engine_failure_counts"]["brave"] == 1


def test_two_engine_failure_is_bad_query(monkeypatch, tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "orchestrator.log").write_text(
        "2026-07-06 searxng unresponsive_engines: brave, wikipedia (query='x')\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(report, "SERVER_LOG_DIR", log_dir)
    monkeypatch.setattr(report, "LOG_DIR", tmp_path / "progress")

    tel = report.collect_telemetry(date(2026, 7, 6), date(2026, 7, 6))

    assert tel["unresponsive_events"] == 1
    assert tel["bad_queries"] == 1


def test_human_report_names_configured_engines():
    tel = {
        "days_scanned": 1,
        "searxng_queries": 20,
        "ddg_queries": 0,
        "unresponsive_events": 1,
        "fallback_events": 0,
        "bad_queries": 0,
        "engine_failure_counts": {},
    }
    verdict = {
        "searxng_p50_ms": 0,
        "searxng_p95_ms": 0,
        "ddg_p50_ms": 0,
        "ddg_p95_ms": 0,
        "latency_ratio": 0,
        "bad_query_rate_pct": 0,
        "fallback_rate_pct": 0,
        "verdict": "PROCEED",
        "reasons": [],
    }

    text = report.format_human(tel, verdict)

    assert "configured engines      : bing, brave, wikipedia" in text
