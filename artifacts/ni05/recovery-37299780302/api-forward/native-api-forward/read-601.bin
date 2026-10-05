from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "autopilot" / "planner_provider_health_report.py"
spec = importlib.util.spec_from_file_location("planner_provider_health_report", SCRIPT)
assert spec is not None and spec.loader is not None
reporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reporter)


def _write_tap(path: Path, blocks: list[str]) -> None:
    path.write_text("\n========================================================================\n".join(blocks))


def test_build_report_counts_local_draft_and_critique_success(tmp_path: Path) -> None:
    tap = tmp_path / "planner_tap.log"
    _write_tap(
        tap,
        [
            """[2026-07-06T06:03:11] PLANNER provider=local_frontdoor role=draft start
url: http://127.0.0.1:8000/v1/chat/completions
------------------------------------------------------------------------
[local:result:local_frontdoor:draft] ```json:autopilot_actions
{"type": "train_routing_models", "min_memories": 500}
```
```json:autopilot_rationale
{"hypothesis": "routing refresh is useful", "falsifier": "no gain"}
```
[END provider=local_frontdoor role=draft] result_chars=622""",
            """[2026-07-06T06:06:48] PLANNER provider=local_worker role=critique start
url: http://127.0.0.1:8000/v1/chat/completions
------------------------------------------------------------------------
[local:result:local_worker:critique] ```json:autopilot_critique
{"decision": "approve", "confidence": 1.0, "issues": []}
```
[END provider=local_worker role=critique] result_chars=137""",
        ],
    )

    report = reporter.build_report(
        tap_path=tap,
        stale_after_s=999999,
        scope_current_process=False,
    )

    assert report["ok"] is True
    assert report["status"] == "healthy"
    assert report["local"]["draft_successes"] == 1
    assert report["local"]["critique_successes"] == 1
    assert report["draft_actions"] == {"train_routing_models": 1}
    assert report["critic_decisions"] == {"approve": 1}
    assert report["providers"]["local_frontdoor"]["draft_successes"] == 1
    assert report["providers"]["local_worker"]["critique_successes"] == 1


def test_build_report_surfaces_local_failures_and_critic_rejections(tmp_path: Path) -> None:
    tap = tmp_path / "planner_tap.log"
    _write_tap(
        tap,
        [
            """[2026-07-06T05:39:53] PLANNER provider=local_frontdoor role=draft start
------------------------------------------------------------------------
[FAIL provider=local_frontdoor role=draft] Server disconnected without sending a response.""",
            """[2026-07-06T05:43:11] PLANNER provider=local_worker role=critique start
------------------------------------------------------------------------
[local:result:local_worker:critique] ```json:autopilot_critique
{"decision": "reject", "confidence": 0.9, "issues": ["Action type deep_eval is not recognized by the declared action space."], "revised_action": null}
```
[END provider=local_worker role=critique] result_chars=288""",
        ],
    )

    report = reporter.build_report(
        tap_path=tap,
        stale_after_s=999999,
        scope_current_process=False,
    )

    assert report["ok"] is False
    assert report["status"] == "attention"
    assert "no successful local draft event in planner tap window" in report["blockers"]
    assert report["local"]["failures"] == 1
    assert report["critic_decisions"] == {"reject": 1}
    assert any(
        issue["kind"] == "critic_issue" and "deep_eval" in issue["message"]
        for issue in report["recent_issues"]
    )


def test_build_report_scopes_to_current_process_window(tmp_path: Path) -> None:
    tap = tmp_path / "planner_tap.log"
    _write_tap(
        tap,
        [
            """[2026-07-06T05:37:05] PLANNER provider=codex role=draft start
------------------------------------------------------------------------
```json:autopilot_actions
{"type": "seed_batch", "n_questions": 10}
```
[END provider=codex role=draft] result_chars=100""",
            """[2026-07-06T06:03:11] PLANNER provider=local_frontdoor role=draft start
------------------------------------------------------------------------
```json:autopilot_actions
{"type": "deep_eval", "tier": 3}
```
[END provider=local_frontdoor role=draft] result_chars=100""",
            """[2026-07-06T06:06:48] PLANNER provider=local_worker role=critique start
------------------------------------------------------------------------
```json:autopilot_critique
{"decision": "approve", "confidence": 0.91, "issues": []}
```
[END provider=local_worker role=critique] result_chars=100""",
        ],
    )
    process_start_s = reporter._parse_event_timestamp("2026-07-06T06:02:00")

    report = reporter.build_report(
        tap_path=tap,
        process_start_s=process_start_s,
        stale_after_s=999999,
    )

    assert report["ok"] is True
    assert report["window"]["scope"] == "current_process"
    assert report["window"]["event_count"] == 2
    assert report["window"]["raw_event_count"] == 3
    assert report["local"]["fallback_provider_starts"] == 0
    assert "codex" not in report["providers"]
    assert report["draft_actions"] == {"deep_eval": 1}


def test_build_report_treats_no_current_events_as_waiting_when_not_planning(
    tmp_path: Path,
) -> None:
    tap = tmp_path / "planner_tap.log"
    phase = tmp_path / "phase.json"
    _write_tap(
        tap,
        [
            """[2026-07-06T05:37:05] PLANNER provider=local_frontdoor role=draft start
------------------------------------------------------------------------
```json:autopilot_actions
{"type": "seed_batch", "n_questions": 10}
```
[END provider=local_frontdoor role=draft] result_chars=100""",
        ],
    )
    phase.write_text(
        '{"pid": 1234, "phase": "dispatch_action", "action_type": "numeric_trial"}'
    )
    process_start_s = reporter._parse_event_timestamp("2026-07-06T06:02:00")

    report = reporter.build_report(
        tap_path=tap,
        phase_path=phase,
        process_start_s=process_start_s,
        stale_after_s=999999,
    )

    assert report["ok"] is True
    assert report["status"] == "waiting_for_planner_turn"
    assert report["blockers"] == []
    assert report["window"]["event_count"] == 0
    assert report["window"]["raw_event_count"] == 1
    assert report["window"]["phase"] == "dispatch_action"
    assert report["window"]["action_type"] == "numeric_trial"
    assert "current phase is dispatch_action" in report["window"]["no_event_reason"]


def test_build_report_keeps_no_current_events_attention_while_planning(
    tmp_path: Path,
) -> None:
    tap = tmp_path / "planner_tap.log"
    phase = tmp_path / "phase.json"
    _write_tap(
        tap,
        [
            """[2026-07-06T05:37:05] PLANNER provider=local_frontdoor role=draft start
------------------------------------------------------------------------
```json:autopilot_actions
{"type": "seed_batch", "n_questions": 10}
```
[END provider=local_frontdoor role=draft] result_chars=100""",
        ],
    )
    phase.write_text('{"pid": 1234, "phase": "planner_invoke"}')
    process_start_s = reporter._parse_event_timestamp("2026-07-06T06:02:00")

    report = reporter.build_report(
        tap_path=tap,
        phase_path=phase,
        process_start_s=process_start_s,
        stale_after_s=999999,
    )

    assert report["ok"] is False
    assert report["status"] == "attention"
    assert report["blockers"] == [
        "no planner provider events parsed from current process window"
    ]
    assert report["window"]["phase"] == "planner_invoke"


def test_build_report_missing_tap_is_not_ok(tmp_path: Path) -> None:
    report = reporter.build_report(tap_path=tmp_path / "missing.log")

    assert report["ok"] is False
    assert report["status"] == "missing"
    assert report["providers"] == {}
    assert report["blockers"]
