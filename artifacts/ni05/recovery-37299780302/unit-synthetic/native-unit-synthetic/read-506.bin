from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "analysis"
    / "mine_repl_patterns.py"
)
_SPEC = importlib.util.spec_from_file_location("mine_repl_patterns_test", MODULE_PATH)
_MOD = importlib.util.module_from_spec(_SPEC)
sys.modules["mine_repl_patterns_test"] = _MOD
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_MOD)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_multi_tool_telemetry_and_chain_ranking(tmp_path: Path, monkeypatch) -> None:
    registry = tmp_path / "tool_registry.yaml"
    registry.write_text(
        "\n".join(
            [
                "tools:",
                "  read_file:",
                "    side_effects: [\"read_only\"]",
                "  list_directory:",
                "    side_effects: [\"read_only\"]",
                "  write_file:",
                "    side_effects: [\"system_state\"]",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(_MOD, "TOOL_REGISTRY_YAML", registry)
    monkeypatch.setattr(_MOD, "AUTOPILOT_LOG", tmp_path / "autopilot.log")
    monkeypatch.setattr(_MOD, "DIAGNOSTICS_JSONL", tmp_path / "seeding_diagnostics.jsonl")
    monkeypatch.setattr(_MOD, "REPORT_OUT", tmp_path / "repl_pattern_analysis.md")

    diag_path = tmp_path / "seeding_diagnostics.jsonl"
    _write_jsonl(
        diag_path,
        [
            {
                "question_id": "q1",
                "suite": "suite_a",
                "mode": "repl",
                "passed": True,
                "tools_used": 2,
                "anomaly_signals": {},
                "tokens_generated": 10,
                "elapsed_s": 1.0,
                "parallel_tools_used": False,
                "tools_called": ["read_file", "list_directory"],
                "tool_chains": [{"tools": ["read_file", "list_directory"]}],
            },
            {
                "question_id": "q2",
                "suite": "suite_b",
                "mode": "repl",
                "passed": False,
                "tools_used": 2,
                "anomaly_signals": {},
                "tokens_generated": 12,
                "elapsed_s": 2.0,
                "parallel_tools_used": True,
                "tools_called": ["read_file", "write_file"],
                "tool_chains": [{"tools": ["read_file", "write_file"]}],
            },
        ],
    )

    records = _MOD.parse_diagnostics(diag_path)
    read_only_tools = _MOD.load_explicit_read_only_tools(registry)
    diag = _MOD.analyze_diagnostics(records, read_only_tools=read_only_tools)

    assert diag["repl_records"] == 2
    assert diag["repl_multi_tools"] == 2
    assert diag["repl_multi_tools_read_only"] == 1
    assert diag["repl_multi_tools_read_only_eligible"] == 2
    assert diag["repl_multi_tools_with_parallel"] == 1
    assert diag["read_only_tools_available"] is True
    assert diag["tool_chain_counts"][("read_file", "list_directory")] == 1
    assert diag["tool_chain_counts"][("read_file", "write_file")] == 1

    sessions = [
        _MOD.ReplSession(
            timestamp="2026-07-06 00:00:00,000",
            outcome="PASS",
            elapsed_s=1.0,
            tps=10.0,
            tokens=10,
            tool_count=2,
            tool_types=[],
            tool_calls=[
                ("read_file", 10, "ok"),
                ("write_file", 12, "ok"),
            ],
        )
    ]
    session_analysis = _MOD.analyze_sessions(sessions)
    chain_candidates = _MOD.rank_tool_chain_candidates(session_analysis, diag)

    assert chain_candidates[0]["pattern"] == "read_file -> write_file"
    assert chain_candidates[0]["count"] == 2
    assert chain_candidates[0]["sources"] == {
        "autopilot_bigrams": 1,
        "tool_chains": 1,
    }

    report = _MOD.generate_report(
        session_analysis,
        diag,
        _MOD.rank_combined_ops(session_analysis),
        chain_candidates,
        instrumentation_gaps=[],
    )

    assert "REPL records with >=2 tools_called: 2" in report
    assert "explicit read-only tool chains: 1 (50.0% of multi-tool REPL records)" in report
    assert "REPL records with parallel_tools_used=True: 1 (50.0% of multi-tool REPL records)" in report
    assert "## Tool Chain Candidates" in report
    assert "| read_file -> write_file | 2 | ~1 | autopilot_bigrams:1, tool_chains:1 |" in report


def test_load_explicit_read_only_tools_includes_registry_annotations() -> None:
    read_only_tools = _MOD.load_explicit_read_only_tools(_MOD.TOOL_REGISTRY_YAML)

    assert {
        "http_get",
        "search_wikipedia",
        "json_query",
        "statistics",
        "matrix_solve",
        "read_file",
    }.issubset(read_only_tools)
    # archive_search was a registry entry until 2026-09-17 (0c03e658, NIB2-79): its
    # handler never existed, and it is a stateful REPL builtin
    # (src/repl_environment/archive_tools.py), not a registry tool. It must not
    # resurface as a registry-annotated read-only tool.
    assert "archive_search" not in read_only_tools
    assert "python_eval" not in read_only_tools
    assert "calculate" not in read_only_tools
    assert "embed_text" not in read_only_tools
    assert "vision_analyze" not in read_only_tools
