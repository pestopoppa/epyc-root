from __future__ import annotations

import datetime as dt

from scripts.tasks import probe_real_task_token_coverage as probe


def test_build_deployment_check_flags_autopilot_started_before_telemetry() -> None:
    deployment = probe.build_deployment_check(
        processes=[
            {
                "pid": 123,
                "started_at": "2026-06-20T17:29:27+00:00",
                "elapsed_s": 10,
                "cmd": "python scripts/autopilot/autopilot.py start",
            }
        ],
        telemetry_files={"src/api/routes/chat_pipeline/telemetry.py": "2026-06-20T23:02:05+00:00"},
    )

    assert deployment["stale_process_for_token_telemetry"] is True
    assert deployment["stale_autopilot_pids"] == [123]
    assert deployment["active_autopilot_pid"] == 123


def test_summarize_probe_reports_token_coverage_and_privacy_status(tmp_path) -> None:
    summary = probe.summarize_probe(
        manifest={
            "counts": {
                "written": 2,
                "training_eligible": 2,
                "duplicates_collapsed": 1,
                "by_class": {"code_change_implementation": 2},
            },
            "sources": {"progress": {"records": 5, "skipped": {"open_task": 1}}},
        },
        rows=[
            {"task_id": "a", "wall_s": 1.0, "tokens": {"total": 10}, "prompt": ""},
            {"task_id": "b", "wall_s": 2.0, "tokens": None, "prompt": ""},
        ],
        generated_at="2026-06-21T00:00:00+00:00",
        output_path=tmp_path / "rows.jsonl",
        manifest_path=tmp_path / "manifest.json",
        start_date="2026-06-21",
        end_date="2026-06-21",
        deployment_check={"stale_process_for_token_telemetry": False},
    )

    assert summary["schema_version"] == "live_token_probe_summary.v2"
    assert summary["counts"]["token_payload_rows"] == 1
    assert summary["counts"]["wall_time_rows"] == 2
    assert summary["counts"]["prompt_text_rows"] == 0
    assert summary["gate_readout"]["token_payload_coverage"] is True
    assert summary["gate_readout"]["privacy_prompt_text_free"] is True
    assert summary["gate_readout"]["status"] == "token_payload_coverage_present"


def test_active_autopilot_processes_parses_ps_output(monkeypatch) -> None:
    class Result:
        returncode = 0
        stdout = "123 30 /venv/bin/python scripts/autopilot/autopilot.py start --max-trials 930\n"

    monkeypatch.setattr(probe.subprocess, "run", lambda *args, **kwargs: Result())

    rows = probe.active_autopilot_processes(now=dt.datetime(2026, 6, 21, 0, 0, tzinfo=dt.UTC))

    assert rows == [
        {
            "pid": 123,
            "started_at": "2026-06-20T23:59:30+00:00",
            "elapsed_s": 30,
            "cmd": "/venv/bin/python scripts/autopilot/autopilot.py start --max-trials 930",
        }
    ]
