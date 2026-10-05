"""Tests for the deterministic per-role MTP/spec-dec alpha-from-logs parser.

Covers: line parsing for both observed log formats, per-role aggregation
(including two ports sharing one role), the headline alpha = acc/gen math, the
per-spec-type breakdown, and the LOUD-FAIL-on-zero-lines contract (both the
requested-role path and the global no-evidence path).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.benchmark import mtp_alpha_from_logs as alpha


# --- Real-shaped fixture lines --------------------------------------------- #
# v6 production slot line + cumulative statistics line.
TASK_LINE_V6 = (
    "301.39.147.975 I slot print_timing: id  0 | task 35853 | "
    "draft acceptance = 0.90000 (   90 accepted /   100 generated), "
    "mean acceptance length =  4.50, acceptance rate per position = (1.000, 0.900)"
)
STATS_LINE_V6 = (
    "301.39.148.004 I statistics        draft-mtp: #calls(b,g,a) =    1     25     25, "
    "#gen drafts =     25, #acc drafts =    24, #gen tokens =    100, #acc tokens =    90, "
    "#mean acc len = 4.50, #acc rate/pos = (1.000, 0.900), dur(b,g,a) = 0.004, 897.067, 0.025 ms"
)
# ngram-mod cumulative that contributed no accepted tokens (combined-slot case).
STATS_LINE_NGRAM = (
    "147.22.954.625 I statistics        ngram-mod: #calls(b,g,a) =    1      7      0, "
    "#gen drafts =      0, #acc drafts =     0, #gen tokens =      0, #acc tokens =     0, "
    "dur(b,g,a) = 0.024, 0.016, 0.000 ms"
)
# Older research-tree format (no timestamp; 'rate ='; stats without mean/rate-pos).
TASK_LINE_TREE = "draft acceptance rate = 0.71901 (  174 accepted /   242 generated)"
STATS_LINE_TREE = (
    "statistics tree: #calls(b,g,a) = 1 81 66, #gen drafts = 81, #acc drafts = 66, "
    "#gen tokens = 243, #acc tokens = 174, dur(b,g,a) = 0.001, 12764.737, 0.035 ms"
)


def test_parse_task_line_v6() -> None:
    task = alpha.parse_task_line(TASK_LINE_V6, line_number=7)
    assert task is not None
    assert task.task_id == 35853
    assert task.accepted_tokens == 90
    assert task.generated_tokens == 100
    assert task.rate == pytest.approx(0.90000)
    assert task.mean_acceptance_length == pytest.approx(4.50)
    assert task.line_number == 7


def test_parse_task_line_tree_variant() -> None:
    task = alpha.parse_task_line(TASK_LINE_TREE)
    assert task is not None
    assert task.task_id is None  # no 'task N' token in this variant
    assert task.accepted_tokens == 174
    assert task.generated_tokens == 242
    assert task.mean_acceptance_length is None


def test_stats_line_is_not_a_task_line() -> None:
    # The cumulative statistics line must never be mistaken for a per-task line.
    assert alpha.parse_task_line(STATS_LINE_V6) is None


def test_parse_cumulative_line_v6() -> None:
    stat = alpha.parse_cumulative_line(STATS_LINE_V6, line_number=8)
    assert stat is not None
    assert stat.spec_type == "draft-mtp"
    assert stat.generated_drafts == 25
    assert stat.accepted_drafts == 24
    assert stat.generated_tokens == 100
    assert stat.accepted_tokens == 90
    assert stat.mean_acceptance_length == pytest.approx(4.50)


def test_parse_cumulative_line_tree_variant() -> None:
    stat = alpha.parse_cumulative_line(STATS_LINE_TREE)
    assert stat is not None
    assert stat.spec_type == "tree"
    assert stat.generated_tokens == 243
    assert stat.accepted_tokens == 174
    assert stat.mean_acceptance_length is None  # absent in this variant


def test_port_from_log_name() -> None:
    assert alpha.port_from_log_name(Path("logs/llama-server-8070.log")) == 8070
    assert alpha.port_from_log_name(Path("logs/worker-explore-8072.log")) == 8072
    assert alpha.port_from_log_name(Path("logs/autopilot.log")) is None


# --- Fixture scaffolding ---------------------------------------------------- #
def _write_attestation(path: Path) -> None:
    payload = {
        "sections": {
            "serving_config": [
                {"port": 8070, "numa_intent": {"role": "worker_general"}},
                {"port": 8082, "numa_intent": {"role": "worker_general"}},
                {"port": 8085, "numa_intent": {"role": "reviewer_glm"}},
            ]
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _make_env(tmp_path: Path) -> tuple[Path, Path]:
    """Create a logs dir with two worker_general logs and one empty reviewer log."""
    logs = tmp_path / "logs"
    logs.mkdir()

    # port 8070 (worker_general): two tasks, draft-mtp only.
    (logs / "llama-server-8070.log").write_text(
        "\n".join(
            [
                TASK_LINE_V6,  # 90 / 100
                STATS_LINE_V6,  # cumulative gen=100 acc=90
                "301.45.839.875 I slot print_timing: id  0 | task 35897 | "
                "draft acceptance = 0.80000 (   80 accepted /   100 generated), "
                "mean acceptance length =  4.00, acceptance rate per position = (0.960, 0.840)",
                "301.45.839.918 I statistics        draft-mtp: #calls(b,g,a) = 2 50 50, "
                "#gen drafts = 50, #acc drafts = 47, #gen tokens = 200, #acc tokens = 170, "
                "#mean acc len = 4.20, #acc rate/pos = (0.982, 0.893), dur(b,g,a) = 0.006, 1.0, 0.05 ms",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    # port 8082 (also worker_general): one task, draft-mtp + a zero ngram-mod line.
    (logs / "worker-explore-8082.log").write_text(
        "\n".join(
            [
                "147.22.954.598 I slot print_timing: id  0 | task 14317 | "
                "draft acceptance = 1.00000 (   50 accepted /    50 generated), "
                "mean acceptance length =  2.86, acceptance rate per position = (1.000, 0.857)",
                STATS_LINE_NGRAM,  # ngram-mod: 0/0
                "147.22.954.628 I statistics        draft-mtp: #calls(b,g,a) = 1 7 7, "
                "#gen drafts = 12, #acc drafts = 12, #gen tokens = 50, #acc tokens = 50, "
                "#mean acc len = 4.16, #acc rate/pos = (1.000, 0.857), dur(b,g,a) = 0.004, 98.6, 0.006 ms",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    # port 8085 (reviewer_glm): running, but NO acceptance lines at all.
    (logs / "llama-server-8085.log").write_text(
        "load_tensors: loaded\nslot launch_slot: processing\nHTTP 200 GET /health\n",
        encoding="utf-8",
    )

    attestation = tmp_path / "attestation.json"
    _write_attestation(attestation)
    return logs, attestation


# --- Aggregation + math ----------------------------------------------------- #
def test_worker_general_alpha_aggregates_two_ports(tmp_path: Path) -> None:
    logs, attestation = _make_env(tmp_path)
    report = alpha.build_report(
        logs_dir=logs,
        attestation_path=attestation,
        requested_roles=["worker_general"],
        explicit_logs=[],
        min_lines=1,
    )
    roles = {r["role"]: r for r in report["roles"]}
    wg = roles["worker_general"]

    # acc = 90 + 80 + 50 = 220 ; gen = 100 + 100 + 50 = 250 ; alpha = 0.88 ; n = 3
    assert wg["accepted_tokens"] == 220
    assert wg["generated_tokens"] == 250
    assert wg["n_task_lines"] == 3
    assert wg["alpha"] == pytest.approx(0.88)
    assert wg["ports"] == [8070, 8082]

    # spec breakdown: draft-mtp best-cumulative summed (200+50 gen, 170+50 acc)=0.88; ngram-mod 0/0.
    specs = wg["spec_breakdown"]
    assert specs["draft-mtp"]["token_alpha"] == pytest.approx(0.88)
    assert specs["ngram-mod"]["token_alpha"] is None  # 0 generated -> undefined, not 0
    assert report["attestation_used"] is True
    assert report["zero_inference"] is True


def test_requested_role_with_zero_lines_loud_fails(tmp_path: Path) -> None:
    logs, attestation = _make_env(tmp_path)
    with pytest.raises(alpha.NoAcceptanceEvidenceError) as exc:
        alpha.build_report(
            logs_dir=logs,
            attestation_path=attestation,
            requested_roles=["reviewer_glm"],
            explicit_logs=[],
            min_lines=1,
        )
    assert "reviewer_glm" in str(exc.value)


def test_min_lines_threshold_loud_fails(tmp_path: Path) -> None:
    logs, attestation = _make_env(tmp_path)
    with pytest.raises(alpha.NoAcceptanceEvidenceError):
        alpha.build_report(
            logs_dir=logs,
            attestation_path=attestation,
            requested_roles=["worker_general"],
            explicit_logs=[],
            min_lines=99,  # more than the 3 lines available
        )


def test_global_no_evidence_loud_fails(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "llama-server-9999.log").write_text("no acceptance here\nHTTP 200\n", encoding="utf-8")
    with pytest.raises(alpha.NoAcceptanceEvidenceError):
        alpha.build_report(
            logs_dir=logs,
            attestation_path=tmp_path / "missing.json",
            requested_roles=[],
            explicit_logs=[],
            min_lines=1,
        )


# --- CLI end-to-end --------------------------------------------------------- #
def test_main_success_and_json_out(tmp_path: Path) -> None:
    logs, attestation = _make_env(tmp_path)
    out = tmp_path / "alpha.json"
    rc = alpha.main(
        [
            "--logs-dir", str(logs),
            "--attestation", str(attestation),
            "--role", "worker_general",
            "--json-out", str(out),
        ]
    )
    assert rc == alpha.EXIT_OK
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["roles"][0]["role"] == "worker_general"
    assert payload["roles"][0]["alpha"] == pytest.approx(0.88)


def test_main_loud_fail_returns_nonzero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    logs, attestation = _make_env(tmp_path)
    rc = alpha.main(
        ["--logs-dir", str(logs), "--attestation", str(attestation), "--role", "reviewer_glm"]
    )
    assert rc == alpha.EXIT_NO_EVIDENCE
    assert "LOUD-FAIL" in capsys.readouterr().err


def test_main_missing_logs_dir_is_usage_error(tmp_path: Path) -> None:
    rc = alpha.main(["--logs-dir", str(tmp_path / "does-not-exist")])
    assert rc == alpha.EXIT_USAGE


def test_main_explicit_log_role_mapping(tmp_path: Path) -> None:
    logs, _ = _make_env(tmp_path)
    rc = alpha.main(
        [
            "--log", f"drafter_probe={logs / 'llama-server-8070.log'}",
            "--role", "drafter_probe",
            "--stdout-json",
        ]
    )
    assert rc == alpha.EXIT_OK
