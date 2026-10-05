from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "benchmark" / "xmas_live_ab.py"
SPEC = importlib.util.spec_from_file_location("xmas_live_ab", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
xmas_live_ab = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(xmas_live_ab)


def test_arm_sequence_uses_abba_order() -> None:
    assert xmas_live_ab.arm_sequence(1) == ["baseline", "xmas"]
    assert xmas_live_ab.arm_sequence(2) == ["baseline", "xmas", "xmas", "baseline"]


def test_reload_env_sets_launch_time_xmas_flags(tmp_path: Path) -> None:
    table = tmp_path / "xmas_winner_table.yaml"

    baseline = xmas_live_ab.reload_env("baseline", table)
    assert baseline["ORCHESTRATOR_XMAS_ROUTING_MODE"] == "off"
    assert baseline["ORCHESTRATOR_XMAS_WINNER_TABLE_PATH"] == ""

    candidate = xmas_live_ab.reload_env("xmas", table)
    assert candidate["ORCHESTRATOR_XMAS_ROUTING_MODE"] == "enforce"
    assert candidate["ORCHESTRATOR_XMAS_WINNER_TABLE_PATH"] == str(table)


def test_validate_table_requires_function_axis(monkeypatch, tmp_path: Path) -> None:
    table = tmp_path / "xmas_winner_table.yaml"
    table.write_text("version: test\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_run(cmd, *, cwd, capture_output, text, timeout):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        captured["capture_output"] = capture_output
        captured["text"] = text
        captured["timeout"] = timeout
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(xmas_live_ab.subprocess, "run", fake_run)

    xmas_live_ab.validate_table(table)

    assert "--require-function-axis" in captured["cmd"]
    assert captured["cwd"] == xmas_live_ab.ORCH


def test_load_prompts_accepts_builtin_json_and_jsonl(tmp_path: Path) -> None:
    builtin = xmas_live_ab.load_prompts(None)
    assert builtin
    assert {item["domain"] for item in builtin} >= {"math", "code", "reasoning"}

    json_path = tmp_path / "prompts.json"
    json_path.write_text('{"prompts": [{"id": "a", "prompt": "A"}]}', encoding="utf-8")
    assert xmas_live_ab.load_prompts(json_path) == [{"id": "a", "prompt": "A"}]

    jsonl_path = tmp_path / "prompts.jsonl"
    jsonl_path.write_text('{"id": "a", "prompt": "A"}\n{"id": "b", "prompt": "B"}\n', encoding="utf-8")
    assert [item["id"] for item in xmas_live_ab.load_prompts(jsonl_path)] == ["a", "b"]


def test_load_result_rows_accepts_jsonl(tmp_path: Path) -> None:
    rows_path = tmp_path / "results.jsonl"
    rows_path.write_text('{"arm": "baseline"}\n{"arm": "xmas"}\n', encoding="utf-8")

    assert [row["arm"] for row in xmas_live_ab.load_result_rows(rows_path)] == [
        "baseline",
        "xmas",
    ]


def test_real_run_requires_explicit_prompt_manifest(tmp_path: Path) -> None:
    args = SimpleNamespace(
        table=tmp_path / "xmas_winner_table.yaml",
        prompts=None,
        summarize_results=None,
        output=tmp_path / "out",
        dry_run=False,
    )

    try:
        xmas_live_ab.run(args)
    except SystemExit as exc:
        assert "pass --prompts with a held-out prompt manifest" in str(exc)
    else:
        raise AssertionError("real X-MAS A/B must reject built-in smoke prompts")


def test_ensure_host_quiet_blocks_known_competing_runners(monkeypatch) -> None:
    def fake_run(cmd, *, capture_output, text):
        assert cmd[:2] == ["pgrep", "-af"]
        pattern = cmd[2]
        stdout = ""
        if pattern == "scripts/autopilot/autopilot.py start":
            stdout = "123 uv run python scripts/autopilot/autopilot.py start --max-trials 930\n"
        elif pattern == "dcp_j7_ab.py":
            stdout = "456 python scripts/benchmark/dcp_j7_ab.py --host-quiet-confirmed\n"
        return SimpleNamespace(stdout=stdout)

    monkeypatch.setattr(xmas_live_ab.subprocess, "run", fake_run)

    try:
        xmas_live_ab.ensure_host_quiet()
    except RuntimeError as exc:
        message = str(exc)
        assert "host is not inference-quiet" in message
        assert "AutoPilot: 123" in message
        assert "DCP J7 A/B: 456" in message
    else:
        raise AssertionError("competing runners must block X-MAS real runs")


def test_ensure_host_quiet_filters_current_process(monkeypatch) -> None:
    current_pid = xmas_live_ab.os.getpid()

    def fake_run(cmd, *, capture_output, text):
        return SimpleNamespace(
            stdout=f"{current_pid} python scripts/benchmark/xmas_live_ab.py\n"
        )

    monkeypatch.setattr(xmas_live_ab.subprocess, "run", fake_run)

    xmas_live_ab.ensure_host_quiet()


def test_pgrep_lines_ignores_script_names_embedded_in_planner_prompt(monkeypatch) -> None:
    def fake_run(cmd, *, capture_output, text):
        assert cmd == ["pgrep", "-af", "seed_specialist_routing.py"]
        return SimpleNamespace(
            stdout=(
                "123 claude -p Consider scripts/benchmark/seed_specialist_routing.py later\n"
                "456 uv run python scripts/benchmark/seed_specialist_routing.py --dry-run\n"
            )
        )

    monkeypatch.setattr(xmas_live_ab.subprocess, "run", fake_run)

    assert xmas_live_ab._pgrep_lines("seed_specialist_routing.py") == [
        "456 uv run python scripts/benchmark/seed_specialist_routing.py --dry-run"
    ]


def test_real_run_reports_clean_host_quiet_refusal(monkeypatch, tmp_path: Path) -> None:
    prompts = tmp_path / "prompts.jsonl"
    prompts.write_text(
        '{"id": "a", "domain": "math", "function": "solve", "prompt": "2+2", "expected": "4"}\n',
        encoding="utf-8",
    )
    called = {"restart": False}

    def fail_restart(*args, **kwargs):
        called["restart"] = True
        raise AssertionError("busy host must fail before orchestrator reload")

    monkeypatch.setattr(xmas_live_ab, "validate_table", lambda _table: None)
    monkeypatch.setattr(
        xmas_live_ab,
        "ensure_host_quiet",
        lambda: (_ for _ in ()).throw(RuntimeError("host is not inference-quiet: AutoPilot: 123")),
    )
    monkeypatch.setattr(xmas_live_ab, "restart_orchestrator", fail_restart)

    try:
        xmas_live_ab.run(
            SimpleNamespace(
                table=tmp_path / "xmas_winner_table.yaml",
                prompts=prompts,
                summarize_results=None,
                sample_size=None,
                reps=1,
                output=tmp_path / "out",
                max_turns=1,
                dry_run=False,
                host_quiet_confirmed=True,
                timeout_s=1.0,
                min_decision_prompts=1,
                min_score_delta=0.05,
                max_domain_regression=0.0,
                max_latency_ratio=1.10,
                restore_baseline=True,
            )
        )
    except SystemExit as exc:
        assert str(exc) == (
            "REFUSING real run: host is not inference-quiet: AutoPilot: 123"
        )
    else:
        raise AssertionError("busy host must refuse real X-MAS A/B")
    assert called == {"restart": False}


def test_dry_run_can_use_builtin_smoke_set_without_inference(
    monkeypatch,
    tmp_path: Path,
) -> None:
    called = {"chat": False, "restart": False}

    def fail_chat(*args, **kwargs):
        called["chat"] = True
        raise AssertionError("dry-run must not call chat")

    def fail_restart(*args, **kwargs):
        called["restart"] = True
        raise AssertionError("dry-run must not restart orchestrator")

    monkeypatch.setattr(xmas_live_ab, "validate_table", lambda _table: None)
    monkeypatch.setattr(xmas_live_ab, "chat", fail_chat)
    monkeypatch.setattr(xmas_live_ab, "restart_orchestrator", fail_restart)
    output = tmp_path / "dryrun"
    args = SimpleNamespace(
        table=tmp_path / "xmas_winner_table.yaml",
        prompts=None,
        summarize_results=None,
        sample_size=1,
        reps=1,
        output=output,
        max_turns=1,
        dry_run=True,
        host_quiet_confirmed=False,
        timeout_s=1.0,
        min_decision_prompts=25,
        min_score_delta=0.05,
        max_domain_regression=0.0,
        max_latency_ratio=1.10,
        restore_baseline=True,
    )

    assert xmas_live_ab.run(args) == 0
    assert called == {"chat": False, "restart": False}
    meta = json.loads((output / "meta.json").read_text())
    assert meta["prompt_manifest"] == "builtin_smoke"
    assert meta["xmas_policy"] == xmas_live_ab.XMAS_EVIDENCE_POLICY_ID
    assert meta["xmas_policy_min_commit"] == "b108f865"
    summary = json.loads((output / "summary.json").read_text())
    assert summary["dry_run"] is True
    assert summary["xmas_policy"] == xmas_live_ab.XMAS_EVIDENCE_POLICY_ID
    assert summary["xmas_policy_min_commit"] == "b108f865"


def test_real_run_records_xmas_meta_without_inference(monkeypatch, tmp_path: Path) -> None:
    prompts = tmp_path / "prompts.jsonl"
    prompts.write_text(
        '{"id": "a", "domain": "math", "function": "solve", "prompt": "2+2", "expected": "4"}\n',
        encoding="utf-8",
    )
    xmas_meta = {
        "mode": "enforce",
        "applied": True,
        "suggested_role": "worker_general",
        "apply_reason": "evidence_quality_lift",
    }

    monkeypatch.setattr(xmas_live_ab, "validate_table", lambda _table: None)
    monkeypatch.setattr(xmas_live_ab, "ensure_host_quiet", lambda: None)
    monkeypatch.setattr(xmas_live_ab, "restart_orchestrator", lambda _env: "ok")
    monkeypatch.setattr(
        xmas_live_ab,
        "chat",
        lambda *args, **kwargs: {
            "status": 200,
            "elapsed_s": 0.1,
            "body": {
                "answer": "<answer>4</answer>",
                "routed_to": "worker_general",
                "routing_strategy": "xmas_enforce:learned",
                "xmas_meta": xmas_meta,
                "role_history": ["worker_general"],
            },
        },
    )

    output = tmp_path / "real"
    rc = xmas_live_ab.run(
        SimpleNamespace(
            table=tmp_path / "xmas_winner_table.yaml",
            prompts=prompts,
            summarize_results=None,
            sample_size=None,
            reps=1,
            output=output,
            max_turns=1,
            dry_run=False,
            host_quiet_confirmed=True,
            timeout_s=1.0,
            min_decision_prompts=1,
            min_score_delta=0.05,
            max_domain_regression=0.0,
            max_latency_ratio=1.10,
            restore_baseline=True,
        )
    )

    assert rc == 0
    rows = [json.loads(line) for line in (output / "results.jsonl").read_text().splitlines()]
    assert rows[0]["xmas_meta"] == xmas_meta


def test_summarize_results_mode_does_not_reload_or_chat(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    called = {"chat": False, "restart": False, "validate": False}

    def fail_chat(*args, **kwargs):
        called["chat"] = True
        raise AssertionError("summarize mode must not call chat")

    def fail_restart(*args, **kwargs):
        called["restart"] = True
        raise AssertionError("summarize mode must not restart orchestrator")

    def fail_validate(*args, **kwargs):
        called["validate"] = True
        raise AssertionError("summarize mode must not validate live table")

    rows_path = tmp_path / "results.jsonl"
    rows_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "block": 0,
                        "arm": "baseline",
                        "prompt_id": "math_1",
                        "domain": "math",
                        "score": False,
                        "elapsed_s": 10.0,
                    }
                ),
                json.dumps(
                    {
                        "block": 0,
                        "arm": "baseline",
                        "prompt_id": "code_1",
                        "domain": "code",
                        "score": True,
                        "elapsed_s": 10.0,
                    }
                ),
                json.dumps(
                    {
                        "block": 1,
                        "arm": "xmas",
                        "prompt_id": "math_1",
                        "domain": "math",
                        "score": True,
                        "elapsed_s": 9.0,
                        "routing_strategy": "xmas_enforce:worker_general",
                    }
                ),
                json.dumps(
                    {
                        "block": 1,
                        "arm": "xmas",
                        "prompt_id": "code_1",
                        "domain": "code",
                        "score": True,
                        "elapsed_s": 9.0,
                        "routing_strategy": "xmas_enforce:coder_escalation",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    rows_path.with_name("meta.json").write_text(
        json.dumps(
            {
                "mode": "real",
                "prompt_manifest": "/tmp/held-out/prompts.jsonl",
                "prompt_ids": ["math_1", "code_1"],
                "arm_sequence": ["baseline", "xmas"],
                "xmas_policy": xmas_live_ab.XMAS_EVIDENCE_POLICY_ID,
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "summary"
    monkeypatch.setattr(xmas_live_ab, "chat", fail_chat)
    monkeypatch.setattr(xmas_live_ab, "restart_orchestrator", fail_restart)
    monkeypatch.setattr(xmas_live_ab, "validate_table", fail_validate)

    rc = xmas_live_ab.run(
        SimpleNamespace(
            summarize_results=rows_path,
            output=output,
            min_decision_prompts=1,
            min_score_delta=0.05,
            max_domain_regression=0.0,
            max_latency_ratio=1.10,
        )
    )

    assert rc == 0
    assert called == {"chat": False, "restart": False, "validate": False}
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["decision"]["status"] == "promote_candidate"
    assert "source_results" in summary
    assert summary["xmas_policy"] == xmas_live_ab.XMAS_EVIDENCE_POLICY_ID
    assert summary["required_xmas_policy"] == xmas_live_ab.XMAS_EVIDENCE_POLICY_ID
    assert summary["required_xmas_policy_min_commit"] == "b108f865"
    report = (output / "report.md").read_text(encoding="utf-8")
    assert "X-MAS held-out replay report" in report
    assert "prompt manifest: `/tmp/held-out/prompts.jsonl`" in report
    assert "decision: `promote_candidate`" in report
    assert "summarized 4 rows" in capsys.readouterr().out


def test_summarize_results_marks_unversioned_replay_as_legacy(tmp_path: Path) -> None:
    rows_path = tmp_path / "results.jsonl"
    rows_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "block": 0,
                        "arm": "baseline",
                        "prompt_id": "math_1",
                        "domain": "math",
                        "score": False,
                        "elapsed_s": 10.0,
                    }
                ),
                json.dumps(
                    {
                        "block": 1,
                        "arm": "xmas",
                        "prompt_id": "math_1",
                        "domain": "math",
                        "score": True,
                        "elapsed_s": 9.0,
                        "routing_strategy": "xmas_enforce:worker_general",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    rows_path.with_name("meta.json").write_text(
        json.dumps(
            {
                "mode": "real",
                "prompt_manifest": "/tmp/held-out/prompts.jsonl",
                "prompt_ids": ["math_1"],
                "arm_sequence": ["baseline", "xmas"],
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "summary"

    assert (
        xmas_live_ab.run(
            SimpleNamespace(
                summarize_results=rows_path,
                output=output,
                min_decision_prompts=1,
                min_score_delta=0.05,
                max_domain_regression=0.0,
                max_latency_ratio=1.10,
            )
        )
        == 0
    )

    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["decision"]["status"] == "promote_candidate"
    assert summary["xmas_policy"] == "unknown_legacy"
    assert summary["required_xmas_policy"] == xmas_live_ab.XMAS_EVIDENCE_POLICY_ID


def test_summarize_results_rejects_mismatched_run_bundle(tmp_path: Path) -> None:
    rows_path = tmp_path / "results.jsonl"
    rows_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "block": 0,
                        "arm": "baseline",
                        "prompt_id": "math_1",
                        "domain": "math",
                        "score": True,
                        "elapsed_s": 10.0,
                    }
                ),
                json.dumps(
                    {
                        "block": 0,
                        "arm": "baseline",
                        "prompt_id": "code_1",
                        "domain": "code",
                        "score": True,
                        "elapsed_s": 10.0,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    rows_path.with_name("meta.json").write_text(
        json.dumps(
            {
                "mode": "real",
                "prompt_manifest": "/tmp/held-out/prompts.jsonl",
                "prompt_ids": ["math_1", "code_1"],
                "arm_sequence": ["baseline", "xmas"],
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "summary"

    try:
        xmas_live_ab.run(
            SimpleNamespace(
                summarize_results=rows_path,
                output=output,
                min_decision_prompts=1,
                min_score_delta=0.05,
                max_domain_regression=0.0,
                max_latency_ratio=1.10,
            )
        )
    except SystemExit as exc:
        assert "run bundle validation failed" in str(exc)
        assert "row count 2 does not match prompt_ids(2) * arm_sequence(2)" in str(exc)
    else:
        raise AssertionError("mismatched replay bundle must fail validation")


def test_score_answer_supports_common_methods() -> None:
    assert xmas_live_ab.score_answer("The answer is 36.", {"expected": "36"}) is True
    assert xmas_live_ab.score_answer("36", {"expected": "36", "scoring": "exact_match"}) is True
    assert xmas_live_ab.score_answer("<answer>valid</answer>", {"expected": "valid", "scoring": "exact_match"}) is True
    assert xmas_live_ab.score_answer("<answer>42</answer>", {"expected": "42"}) is True
    assert xmas_live_ab.score_answer("Answer: A", {"expected": "A", "scoring": "multiple_choice"}) is True
    assert xmas_live_ab.score_answer("<answer>A</answer>", {"expected": "A", "scoring": "multiple_choice"}) is True
    assert xmas_live_ab.score_answer("Answer: B", {"expected": "A", "scoring": "multiple_choice"}) is False
    assert xmas_live_ab.score_answer("anything", {}) is None


def test_chat_records_http_errors(monkeypatch) -> None:
    class FailingClient:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def post(self, url: str, json: dict):
            raise xmas_live_ab.httpx.ReadTimeout("timed out")

    monkeypatch.setattr(xmas_live_ab.httpx, "Client", FailingClient)

    result = xmas_live_ab.chat("prompt", timeout_s=1.0, session_id="s", max_turns=1)

    assert result["status"] == 0
    assert result["body"]["answer"] == ""
    assert result["body"]["error_code"] == "ReadTimeout"


def test_summarize_reports_routes_scores_and_xmas_apply_count() -> None:
    rows = [
        {
            "arm": "baseline",
            "prompt_id": "p1",
            "score": True,
            "elapsed_s": 10.0,
            "routing_strategy": "rules",
            "routed_to": "frontdoor",
        },
        {
            "arm": "baseline",
            "prompt_id": "p2",
            "score": False,
            "elapsed_s": 20.0,
            "routing_strategy": "rules",
            "routed_to": "frontdoor",
        },
        {
            "arm": "xmas",
            "prompt_id": "p1",
            "score": True,
            "elapsed_s": 7.0,
            "routing_strategy": "xmas_enforce:rules",
            "routed_to": "worker_general",
        },
        {
            "arm": "xmas",
            "prompt_id": "p2",
            "score": True,
            "elapsed_s": 9.0,
            "routing_strategy": "rules",
            "routed_to": "frontdoor",
        },
    ]

    summary = xmas_live_ab.summarize(rows)

    assert summary["arms"]["baseline"]["score_rate"] == 0.5
    assert summary["arms"]["xmas"]["score_rate"] == 1.0
    assert summary["arms"]["xmas"]["xmas_applied_n"] == 1
    assert summary["arms"]["xmas"]["routed_to_counts"] == {
        "frontdoor": 1,
        "worker_general": 1,
    }
    assert summary["score_delta_xmas_minus_baseline"] == 0.5
    assert summary["diagnostics"]["route_transition_counts"] == {
        "frontdoor->frontdoor": 1,
        "frontdoor->worker_general": 1,
    }


def test_diagnostics_summary_explains_prompt_level_regressions() -> None:
    rows = [
        {
            "arm": "baseline",
            "prompt_id": "math_1",
            "domain": "math",
            "function": "solve",
            "score": True,
            "elapsed_s": 10.0,
            "routing_strategy": "learned",
            "routed_to": "coder_escalation",
        },
        {
            "arm": "xmas",
            "prompt_id": "math_1",
            "domain": "math",
            "function": "solve",
            "score": False,
            "elapsed_s": 60.0,
            "routing_strategy": "xmas_enforce:learned",
            "routed_to": "worker_general",
        },
        {
            "arm": "baseline",
            "prompt_id": "code_1",
            "domain": "code",
            "function": "solve",
            "score": True,
            "elapsed_s": 5.0,
            "routing_strategy": "learned",
            "routed_to": "coder_escalation",
        },
        {
            "arm": "xmas",
            "prompt_id": "code_1",
            "domain": "code",
            "function": "solve",
            "score": False,
            "elapsed_s": 100.0,
            "routing_strategy": "",
            "routed_to": "",
            "status": 0,
            "error_code": "ReadTimeout",
        },
    ]

    diagnostics = xmas_live_ab.diagnostics_summary(rows)

    assert diagnostics["paired_prompt_count"] == 2
    assert diagnostics["score_flips"] == {"baseline_only_better": 2}
    assert diagnostics["route_transition_counts"] == {
        "coder_escalation-><none>": 1,
        "coder_escalation->worker_general": 1,
    }
    assert diagnostics["timeout_counts_by_arm"] == {"xmas": 1}
    assert diagnostics["xmas_override_prompt_count"] == 1
    assert diagnostics["latency_regression_prompt_count"] == 2
    assert diagnostics["top_latency_regressions"][0]["prompt_id"] == "code_1"
    assert diagnostics["by_cell"]["math:solve"]["score_delta_xmas_minus_baseline"] == -1.0
    assert diagnostics["by_cell"]["math:solve"]["latency_ratio_xmas_over_baseline"] == 6.0


def test_render_report_includes_diagnostics(tmp_path: Path) -> None:
    summary = {
        "mode": "replay",
        "decision": {
            "status": "hold",
            "blockers": ["latency ratio 6.000 > allowed 1.100"],
            "lift_domains": [],
            "regression_domains": ["math"],
        },
        "score_delta_xmas_minus_baseline": -1.0,
        "latency_ratio_xmas_over_baseline": 6.0,
        "diagnostics": {
            "score_flips": {"baseline_only_better": 1},
            "timeout_counts_by_arm": {"xmas": 1},
            "route_transition_counts": {"coder_escalation->worker_general": 1},
            "top_latency_regressions": [
                {
                    "prompt_id": "math_1",
                    "cell": "math:solve",
                    "baseline_route": "coder_escalation",
                    "xmas_route": "worker_general",
                    "baseline_score": 1.0,
                    "xmas_score": 0.0,
                    "baseline_latency_s": 10.0,
                    "xmas_latency_s": 60.0,
                    "latency_ratio": 6.0,
                }
            ],
        },
    }

    report = xmas_live_ab.render_report(
        summary,
        source_results=tmp_path / "results.jsonl",
    )

    assert "## Diagnostics" in report
    assert "baseline_only_better=1" in report
    assert "timeouts/errors: xmas=1" in report
    assert "coder_escalation->worker_general (1)" in report
    assert "math_1 math:solve" in report


def test_summarize_marks_promote_candidate_when_gates_pass() -> None:
    rows = [
        {
            "arm": "baseline",
            "prompt_id": "math_1",
            "domain": "math",
            "score": True,
            "elapsed_s": 10.0,
            "routing_strategy": "rules",
            "routed_to": "frontdoor",
        },
        {
            "arm": "baseline",
            "prompt_id": "code_1",
            "domain": "code",
            "score": True,
            "elapsed_s": 10.0,
            "routing_strategy": "rules",
            "routed_to": "coder_escalation",
        },
        {
            "arm": "xmas",
            "prompt_id": "math_1",
            "domain": "math",
            "score": True,
            "elapsed_s": 9.0,
            "routing_strategy": "xmas_enforce:worker_general",
            "routed_to": "worker_general",
        },
        {
            "arm": "xmas",
            "prompt_id": "code_1",
            "domain": "code",
            "score": True,
            "elapsed_s": 10.0,
            "routing_strategy": "xmas_enforce:coder_escalation",
            "routed_to": "coder_escalation",
        },
        {
            "arm": "baseline",
            "prompt_id": "math_2",
            "domain": "math",
            "score": False,
            "elapsed_s": 10.0,
            "routing_strategy": "rules",
            "routed_to": "frontdoor",
        },
        {
            "arm": "xmas",
            "prompt_id": "math_2",
            "domain": "math",
            "score": True,
            "elapsed_s": 9.0,
            "routing_strategy": "xmas_enforce:worker_general",
            "routed_to": "worker_general",
        },
    ]

    summary = xmas_live_ab.summarize(
        rows,
        min_prompts_per_arm=3,
        min_score_delta=0.05,
        max_domain_regression=0.0,
        max_latency_ratio=1.10,
    )

    assert summary["latency_ratio_xmas_over_baseline"] < 1.0
    assert summary["domains"]["math"]["score_delta_xmas_minus_baseline"] == 0.5
    assert summary["decision"]["status"] == "promote_candidate"
    assert summary["decision"]["lift_domains"] == ["math"]
    assert summary["decision"]["blockers"] == []


def test_summarize_marks_insufficient_evidence_for_small_runs() -> None:
    rows = [
        {
            "arm": "baseline",
            "domain": "math",
            "score": True,
            "elapsed_s": 10.0,
            "routing_strategy": "rules",
            "routed_to": "frontdoor",
        },
        {
            "arm": "xmas",
            "domain": "math",
            "score": True,
            "elapsed_s": 10.0,
            "routing_strategy": "xmas_enforce:worker_general",
            "routed_to": "worker_general",
        },
    ]

    summary = xmas_live_ab.summarize(rows, min_prompts_per_arm=25)

    assert summary["decision"]["status"] == "insufficient_evidence"
    assert summary["decision"]["blockers"][0].startswith("insufficient prompts per arm")
