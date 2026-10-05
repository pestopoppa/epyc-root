"""Tests for the live MTP acceptance report parser."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.benchmark import mtp_acceptance_report as report


TASK_LINE = (
    "119.50.749.183 I slot print_timing: id  0 | task 32843 | "
    "draft acceptance = 0.83432 (  282 accepted /   338 generated), "
    "mean acceptance length =  2.67, acceptance rate per position = (0.893, 0.775)"
)
CUMULATIVE_LINE = (
    "119.50.749.183 I slot print_timing: id  0 | task 32843 | "
    "statistics draft-mtp: #calls(b,g,a) = 229 22393 22393, #gen drafts = 22393, "
    "#acc drafts = 19662, #gen tokens = 44781, #acc tokens = 37046, "
    "#mean acc len = 2.65, #acc rate/pos = (0.878, 0.776), "
    "ttft = 12.34 ms, tps = 56.78"
)


def _write_attestation(path: Path) -> None:
    payload = {
        "sections": {
            "serving_config": [
                {
                    "port": 8072,
                    "pid": 1234,
                    "spec_type": "ngram-mod,draft-mtp",
                    "draft_model_path": "/models/draft.gguf",
                    "model_path": "/models/worker.gguf",
                    "numa_intent": {"role": "worker_general", "cpu_list": "0-95"},
                    "registry_matches": [{"role": "worker", "registry_section": "server_mode.worker"}],
                },
                {
                    "port": 8085,
                    "pid": 5678,
                    "spec_type": None,
                    "draft_model_path": None,
                    "model_path": "/models/long.gguf",
                    "numa_intent": {"role": "ingest_long_context", "cpu_list": "0-23,96-119"},
                    "registry_matches": [{"role": "ingest_long_context"}],
                },
            ]
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_parse_acceptance_lines() -> None:
    task = report.parse_task_acceptance_line(TASK_LINE, line_number=7)
    cumulative = report.parse_cumulative_stats_line(CUMULATIVE_LINE, line_number=8)

    assert task is not None
    assert task.task_id == 32843
    assert task.accepted_tokens == 282
    assert task.generated_tokens == 338
    assert task.acceptance_rate == 0.83432
    assert task.per_position_rates == [0.893, 0.775]
    assert task.line_number == 7

    assert cumulative is not None
    assert cumulative.spec_type == "draft-mtp"
    assert cumulative.generated_drafts == 22393
    assert cumulative.accepted_drafts == 19662
    assert cumulative.generated_tokens == 44781
    assert cumulative.accepted_tokens == 37046
    assert cumulative.token_acceptance_rate == 37046 / 44781
    assert cumulative.draft_acceptance_rate == 19662 / 22393


def test_port_inventory_detects_mtp_inside_combined_spec_type() -> None:
    inventory = report.PortInventory(
        port=8072,
        primary_role="worker_general",
        registry_roles=["worker_general"],
        pid=1234,
        spec_type="ngram-mod,draft-mtp",
        draft_model_path=None,
        model_path="/models/worker.gguf",
        cpu_intent=None,
    )

    assert inventory.mtp_configured is True


def test_build_report_uses_latest_cumulative_stats(tmp_path: Path) -> None:
    attestation = tmp_path / "latest.json"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _write_attestation(attestation)
    (logs_dir / "worker-explore-8072.log").write_text(
        "\n".join([TASK_LINE, CUMULATIVE_LINE]) + "\n",
        encoding="utf-8",
    )
    (logs_dir / "llama-server-8085.log").write_text(
        "common_speculative_init: no implementations specified for speculative decoding\n",
        encoding="utf-8",
    )

    result = report.build_report(attestation_path=attestation, logs_dir=logs_dir)

    roles = {role.role: role for role in result.roles}
    worker = roles["worker_general"]
    assert worker.status == "ok"
    assert worker.evidence_ports == [8072]
    assert worker.generated_tokens == 44781
    assert worker.accepted_tokens == 37046
    assert worker.token_acceptance_rate == 37046 / 44781

    ingest = roles["ingest_long_context"]
    assert ingest.status == "not_mtp_configured"
    assert ingest.generated_tokens == 0
    assert result.summary["failed_mtp_roles"] == []


def test_missing_mtp_evidence_is_a_failed_role(tmp_path: Path) -> None:
    attestation = tmp_path / "latest.json"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _write_attestation(attestation)
    (logs_dir / "worker-explore-8072.log").write_text("server started\n", encoding="utf-8")

    result = report.build_report(attestation_path=attestation, logs_dir=logs_dir)

    roles = {role.role: role for role in result.roles}
    assert roles["worker_general"].status == "missing_acceptance_evidence"
    assert result.summary["failed_mtp_roles"] == ["worker_general"]


def test_main_writes_json_and_markdown(tmp_path: Path, capsys) -> None:
    attestation = tmp_path / "latest.json"
    logs_dir = tmp_path / "logs"
    out_json = tmp_path / "report.json"
    out_md = tmp_path / "report.md"
    logs_dir.mkdir()
    _write_attestation(attestation)
    (logs_dir / "worker-explore-8072.log").write_text(CUMULATIVE_LINE + "\n", encoding="utf-8")

    rc = report.main(
        [
            "--attestation",
            str(attestation),
            "--logs-dir",
            str(logs_dir),
            "--output-json",
            str(out_json),
            "--output-md",
            str(out_md),
            "--no-write-defaults",
        ]
    )

    assert rc == 0
    stdout = json.loads(capsys.readouterr().out)
    assert stdout["failed_mtp_roles"] == []
    assert out_json.exists()
    assert out_md.exists()
    assert json.loads(out_json.read_text(encoding="utf-8"))["summary"]["generated_tokens"] == 44781
    assert "worker_general" in out_md.read_text(encoding="utf-8")
