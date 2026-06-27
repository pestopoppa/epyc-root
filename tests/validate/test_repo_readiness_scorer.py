from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "validate" / "repo_readiness_scorer.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("repo_readiness_scorer", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_repo_level_requires_80_percent_each_level():
    scorer = _load_module()

    maturity = scorer._repo_level({1: 0.80, 2: 0.79, 3: 1.0, 4: 1.0, 5: 1.0})

    assert maturity["achieved_level"] == 1
    assert maturity["next_level"] == 2
    assert maturity["next_label"] == "Documented"


def test_default_repos_resolve_local_overrides(tmp_path, monkeypatch):
    scorer = _load_module()
    monkeypatch.setenv("EPYC_ROOT_REPO", str(tmp_path / "alt-root"))
    monkeypatch.setenv("EPYC_ORCHESTRATOR_REPO", str(tmp_path / "alt-orchestrator"))
    monkeypatch.setenv("EPYC_INFERENCE_RESEARCH_REPO", str(tmp_path / "alt-research"))
    monkeypatch.setenv("EPYC_LLAMA_REPO", str(tmp_path / "alt-llama"))

    repos = scorer._build_default_repos()

    assert repos["epyc-root"] == tmp_path / "alt-root"
    assert repos["epyc-orchestrator"] == tmp_path / "alt-orchestrator"
    assert repos["epyc-inference-research"] == tmp_path / "alt-research"
    assert repos["epyc-llama"] == tmp_path / "alt-llama"


def test_score_repositories_uses_concrete_detectors(tmp_path):
    scorer = _load_module()
    repo = tmp_path / "repo"
    _write(repo / "README.md", "Setup with make. Run pytest. See logs and benchmark metrics.")
    _write(repo / "pyproject.toml", "[tool.ruff]\n")
    _write(repo / "tests" / "test_smoke.py", "def test_ok():\n    assert True\n")
    _write(repo / "AGENTS.md", "Handoff backlog and security policy. Use ruff lint.")
    _write(repo / ".gitignore", "*.secret\n")
    _write(repo / "scripts" / "setup.sh", "#!/bin/bash\n")
    _write(repo / "logs" / "agent_audit.log", "{}\n")
    _write(repo / "orchestration" / "reports" / "sample.md", "# report\n")

    report = scorer.score_repositories({"sample": repo})
    sample = report["repos"]["sample"]

    assert sample["level_rates"][1] == 1.0
    assert sample["maturity"]["achieved_level"] >= 1
    assert any(c["id"] == "L1.tests_present" and c["passed"] for c in sample["criteria"])


def test_markdown_report_includes_blocking_criteria(tmp_path):
    scorer = _load_module()
    repo = tmp_path / "empty"
    repo.mkdir()

    report = scorer.score_repositories({"empty": repo})
    markdown = scorer.render_markdown(report)

    assert "# EPYC Repo Readiness Report" in markdown
    assert "Lowest Portfolio Criteria" in markdown
    assert "Per-Repo Blocking Criteria" in markdown
    assert "Below Functional" in markdown


def test_remediation_queue_exports_failed_criteria_as_actionable_items(tmp_path):
    scorer = _load_module()
    repo = tmp_path / "empty"
    repo.mkdir()

    report = scorer.score_repositories({"empty": repo})
    queue = report["remediation_queue"]
    first_item = queue["items"][0]

    assert queue["version"] == 1
    assert queue["item_count"] == 45
    assert first_item["id"] == "readiness:empty:L1.style_config"
    assert first_item["status"] == "open"
    assert first_item["priority"] == "P0"
    assert first_item["category"] == "repo_readiness"
    assert first_item["repo"] == "empty"
    assert first_item["criterion_id"] == "L1.style_config"
    assert first_item["level"] == 1
    assert first_item["level_label"] == "Functional"
    assert first_item["pillar"] == "Style & Validation"
    assert first_item["blocking_next_gate"] is True
    assert first_item["portfolio_coverage"] == 0.0
    assert "passes for `empty`" in first_item["acceptance"]
    assert first_item["source"] == "scripts/validate/repo_readiness_scorer.py"


def test_cli_writes_remediation_queue_json(tmp_path):
    scorer = _load_module()
    repo = tmp_path / "repo"
    repo.mkdir()
    output = tmp_path / "queue.json"
    markdown = tmp_path / "report.md"

    rc = scorer.main([
        "--repo",
        f"sample={repo}",
        "--output-md",
        str(markdown),
        "--output-remediation-json",
        str(output),
    ])

    queue = json.loads(output.read_text(encoding="utf-8"))
    assert rc == 0
    assert markdown.exists()
    assert queue["version"] == 1
    assert queue["item_count"] == 45
    assert queue["items"][0]["id"] == "readiness:sample:L1.style_config"


def test_remediation_queue_markdown_is_advisory_and_limitable(tmp_path):
    scorer = _load_module()
    repo = tmp_path / "empty"
    repo.mkdir()

    report = scorer.score_repositories({"empty": repo})
    markdown = scorer.render_remediation_markdown(
        report["remediation_queue"],
        limit=2,
    )

    assert "# EPYC Repo Readiness Remediation Queue" in markdown
    assert "not an\nAutoPilot authority gate" in markdown
    assert markdown.count("| P0 | empty |") == 2
    assert "Showing first 2 items" in markdown


def test_cli_writes_remediation_queue_markdown(tmp_path):
    scorer = _load_module()
    repo = tmp_path / "repo"
    repo.mkdir()
    output = tmp_path / "queue.md"

    rc = scorer.main([
        "--repo",
        f"sample={repo}",
        "--output-remediation-md",
        str(output),
        "--remediation-md-limit",
        "1",
    ])

    markdown = output.read_text(encoding="utf-8")
    assert rc == 0
    assert "EPYC Repo Readiness Remediation Queue" in markdown
    assert markdown.count("| P0 | sample |") == 1


def test_autopilot_remediation_pickup_is_passive_and_limitable(tmp_path):
    scorer = _load_module()
    repo = tmp_path / "empty"
    repo.mkdir()

    report = scorer.score_repositories({"empty": repo})
    pickup = scorer.build_autopilot_remediation_pickup(
        report["remediation_queue"],
        limit=2,
    )

    assert pickup["mode"] == "advisory_only"
    assert pickup["authority_gate"] is False
    assert pickup["item_count"] == 2
    assert pickup["source_queue_version"] == report["remediation_queue"]["version"]
    assert pickup["items"][0]["status"] == "candidate"
    assert "run GitNexus impact" in pickup["items"][0]["required_preflight"][1]
    assert "not an acceptance criterion" in pickup["pickup_rules"][-1]


def test_cli_writes_autopilot_remediation_pickup_json(tmp_path):
    scorer = _load_module()
    repo = tmp_path / "repo"
    repo.mkdir()
    output = tmp_path / "pickup.json"

    rc = scorer.main([
        "--repo",
        f"sample={repo}",
        "--output-autopilot-remediation-json",
        str(output),
        "--autopilot-remediation-limit",
        "1",
    ])

    pickup = json.loads(output.read_text(encoding="utf-8"))
    assert rc == 0
    assert pickup["mode"] == "advisory_only"
    assert pickup["authority_gate"] is False
    assert pickup["item_count"] == 1
    assert pickup["items"][0]["id"] == "readiness:sample:L1.style_config"


def test_security_audit_accepts_scripts_security_surface(tmp_path):
    scorer = _load_module()
    repo = tmp_path / "repo"
    _write(repo / "scripts" / "security" / "audit_repository.py", "#!/usr/bin/env python3\n")

    report = scorer.score_repositories({"sample": repo})
    security_audit = next(
        item
        for item in report["repos"]["sample"]["criteria"]
        if item["id"] == "L4.security_audit"
    )

    assert security_audit["passed"] is True
    assert "scripts/security/audit_repository.py" in security_audit["evidence"]
