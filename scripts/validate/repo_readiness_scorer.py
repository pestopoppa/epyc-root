#!/usr/bin/env python3
"""Deterministic repo-readiness scorer for the EPYC repo map.

The rubric is adapted from the Factory-style model captured in
handoffs/active/repo-readiness-scorer.md:

- five maturity levels;
- nine technical pillars;
- unlock the next level by passing at least 80% of the previous level;
- score each criterion over the four EPYC sub-app repositories.

This script intentionally uses concrete file/pattern checks only. It should be
stable enough for repeated CI/dashboard use and conservative enough to produce
actionable remediation work instead of model-judged prose.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Iterable


ROOT = Path("/mnt/raid0/llm/epyc-root")

DEFAULT_REPOS = {
    "epyc-root": ROOT,
    "epyc-orchestrator": Path("/mnt/raid0/llm/epyc-orchestrator"),
    "epyc-inference-research": Path("/mnt/raid0/llm/epyc-inference-research"),
    "epyc-llama": Path("/mnt/raid0/llm/llama.cpp"),
}

LEVELS = {
    1: "Functional",
    2: "Documented",
    3: "Standardized",
    4: "Optimized",
    5: "Autonomous",
}

PILLARS = [
    "Style & Validation",
    "Build System",
    "Testing",
    "Documentation",
    "Dev Environment",
    "Debugging & Observability",
    "Security",
    "Task Discovery",
    "Product & Experimentation",
]

UNLOCK_THRESHOLD = 0.80
MAX_READ_BYTES = 256_000
QUEUE_VERSION = 1
IGNORED_PARTS = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "repos",
}


@dataclass(frozen=True)
class CheckResult:
    passed: bool
    evidence: list[str]


Detector = Callable[[Path], CheckResult]


@dataclass(frozen=True)
class Criterion:
    id: str
    level: int
    pillar: str
    description: str
    detectors: tuple[Detector, ...]

    def evaluate(self, repo_root: Path) -> CheckResult:
        evidence: list[str] = []
        for detector in self.detectors:
            result = detector(repo_root)
            evidence.extend(result.evidence)
            if result.passed:
                return CheckResult(True, result.evidence[:5])
        return CheckResult(False, evidence[:5])


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _ignored(path: Path, root: Path) -> bool:
    rel = Path(_rel(path, root))
    for part in rel.parts:
        if part in IGNORED_PARTS:
            return True
        if ".bak-" in part:
            return True
        if part == "build" or part.startswith("build-"):
            return True
    return False


def _iter_matches(root: Path, patterns: Iterable[str]) -> list[Path]:
    matches: list[Path] = []
    for pattern in patterns:
        matches.extend(p for p in root.glob(pattern) if p.exists() and not _ignored(p, root))
    unique = sorted(set(matches), key=lambda p: _rel(p, root))
    return unique


def exists_any(*patterns: str) -> Detector:
    def _detector(root: Path) -> CheckResult:
        matches = _iter_matches(root, patterns)
        return CheckResult(bool(matches), [_rel(p, root) for p in matches[:5]])

    return _detector


def file_contains(patterns: Iterable[str], needles: Iterable[str]) -> Detector:
    compiled = [re.compile(n, re.IGNORECASE) for n in needles]
    glob_patterns = tuple(patterns)

    def _detector(root: Path) -> CheckResult:
        evidence: list[str] = []
        for path in _iter_matches(root, glob_patterns):
            if not path.is_file() or path.stat().st_size > MAX_READ_BYTES:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if any(rx.search(text) for rx in compiled):
                evidence.append(_rel(path, root))
                if len(evidence) >= 5:
                    break
        return CheckResult(bool(evidence), evidence)

    return _detector


def path_name_contains(*needles: str) -> Detector:
    lowered = tuple(n.lower() for n in needles)

    def _detector(root: Path) -> CheckResult:
        evidence: list[str] = []
        for path in root.rglob("*"):
            if _ignored(path, root):
                continue
            rel = _rel(path, root)
            low = rel.lower()
            if any(n in low for n in lowered):
                evidence.append(rel)
                if len(evidence) >= 5:
                    break
        return CheckResult(bool(evidence), evidence)

    return _detector


def has_make_target(*targets: str) -> Detector:
    target_res = [re.compile(rf"^{re.escape(target)}\s*:", re.MULTILINE) for target in targets]

    def _detector(root: Path) -> CheckResult:
        makefile = root / "Makefile"
        if not makefile.exists():
            return CheckResult(False, [])
        text = makefile.read_text(encoding="utf-8", errors="replace")
        if any(rx.search(text) for rx in target_res):
            return CheckResult(True, ["Makefile"])
        return CheckResult(False, ["Makefile"])

    return _detector


DOC_FILES = (
    "README*",
    "AGENTS.md",
    "CLAUDE.md",
    "docs/**/*.md",
    "handoffs/**/*.md",
    "wiki/**/*.md",
)

CONFIG_FILES = (
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "CMakeLists.txt",
    "Makefile",
    ".pre-commit-config.yaml",
    ".github/workflows/*",
    "*.yaml",
    "*.yml",
)


def build_criteria() -> list[Criterion]:
    """Return the v1 criteria catalog: 5 levels x 9 pillars."""
    c: list[Criterion] = []

    def add(
        level: int,
        pillar: str,
        slug: str,
        description: str,
        *detectors: Detector,
    ) -> None:
        c.append(
            Criterion(
                id=f"L{level}.{slug}",
                level=level,
                pillar=pillar,
                description=description,
                detectors=detectors,
            )
        )

    # Level 1: Functional.
    add(1, "Style & Validation", "style_config", "Has a formatter/linter/style config.",
        exists_any("pyproject.toml", "ruff.toml", ".pre-commit-config.yaml", ".clang-format",
                   ".github/workflows/*", "scripts/validate/**"))
    add(1, "Build System", "build_entry", "Has a build/install entry point.",
        exists_any("pyproject.toml", "package.json", "Cargo.toml", "CMakeLists.txt", "Makefile",
                   "scripts/setup.sh", "scripts/clone-repos.sh"))
    add(1, "Testing", "tests_present", "Has a test tree or test files.",
        exists_any("tests/**", "test/**", "**/test_*.py", "**/*_test.cpp"))
    add(1, "Documentation", "readme_docs", "Has user/developer documentation.",
        exists_any("README*", "docs/**", "wiki/**"))
    add(1, "Dev Environment", "setup_surface", "Has setup or environment entry points.",
        exists_any("scripts/setup.*", "setup.*", "requirements*.txt", ".devcontainer/**"))
    add(1, "Debugging & Observability", "basic_logs", "Has logs, health checks, or logging code.",
        exists_any("logs/**", "scripts/session/health_check.sh"),
        file_contains(("src/**/*.py", "scripts/**/*.py"), (r"\blogging\b", r"\blog\.")))
    add(1, "Security", "basic_security", "Has basic secret-exclusion or security files.",
        exists_any(".gitignore", "SECURITY.md", "scripts/hooks/pii_precommit.sh"))
    add(1, "Task Discovery", "task_surface", "Has a task/backlog/agent-discovery surface.",
        exists_any("AGENTS.md", "CLAUDE.md", "handoffs/active/**", ".github/ISSUE_TEMPLATE/**", "TODO*"))
    add(1, "Product & Experimentation", "experiment_surface", "Has benchmark/eval/report artifacts.",
        exists_any("benchmarks/**", "scripts/benchmark/**", "orchestration/reports/**", "progress/**"))

    # Level 2: Documented.
    add(2, "Style & Validation", "style_docs", "Documents lint/format/style commands.",
        file_contains(DOC_FILES, (r"\blint\b", r"\bformat\b", r"\bruff\b", r"pre-commit")))
    add(2, "Build System", "build_docs", "Documents build/install/setup commands.",
        file_contains(DOC_FILES, (r"\bbuild\b", r"\binstall\b", r"\bsetup\b", r"\bmake\b")))
    add(2, "Testing", "test_docs", "Documents test commands or test policy.",
        file_contains(DOC_FILES, (r"\bpytest\b", r"\bctest\b", r"\btest(s|ing)?\b")))
    add(2, "Documentation", "agent_docs", "Documents agent/project operating rules.",
        exists_any("AGENTS.md", "CLAUDE.md"))
    add(2, "Dev Environment", "dev_env_docs", "Documents container/venv/dev setup.",
        exists_any(".devcontainer/devcontainer.json"),
        file_contains(DOC_FILES, (r"devcontainer", r"\bvenv\b", r"\bcontainer\b", r"\benvironment\b")))
    add(2, "Debugging & Observability", "debug_docs", "Documents debug/log/health workflows.",
        file_contains(DOC_FILES, (r"\bdebug", r"\blog(s|ging)?\b", r"health[_ -]?check", r"troubleshoot")))
    add(2, "Security", "security_docs", "Documents secret, PII, or security handling.",
        exists_any("SECURITY.md"),
        file_contains(DOC_FILES, (r"\bsecret", r"\bpii\b", r"\bsecurity\b")))
    add(2, "Task Discovery", "task_docs", "Documents backlog/handoff/issue workflow.",
        file_contains(DOC_FILES, (r"\bhandoff", r"\bbacklog\b", r"\bissue\b", r"\btask discovery\b")))
    add(2, "Product & Experimentation", "measurement_docs", "Documents metrics, evals, or experiments.",
        exists_any("MEASUREMENT.md"),
        file_contains(DOC_FILES, (r"\bmetric", r"\beval", r"\bbenchmark", r"\bexperiment")))

    # Level 3: Standardized.
    add(3, "Style & Validation", "style_enforced", "Automates lint/style validation.",
        exists_any(".github/workflows/*", ".pre-commit-config.yaml", "scripts/hooks/*"),
        has_make_target("lint", "format-check"))
    add(3, "Build System", "repro_build", "Uses reproducible build metadata or lock/config files.",
        exists_any("uv.lock", "poetry.lock", "package-lock.json", "Cargo.lock", "CMakePresets.json",
                   ".devcontainer/Dockerfile", ".devcontainer/devcontainer.json"))
    add(3, "Testing", "test_automation", "Automates test execution through CI/config/scripts.",
        exists_any(".github/workflows/*", "pytest.ini"),
        has_make_target("test", "tests"))
    add(3, "Documentation", "doc_validation", "Has documentation validation or generated-doc tooling.",
        exists_any("scripts/validate/validate_doc_drift.py", "scripts/docs/**", "docs/**"))
    add(3, "Dev Environment", "standard_dev_env", "Standardizes local environment setup.",
        exists_any(".devcontainer/**", "scripts/setup.sh", "scripts/session/session_init.sh"))
    add(3, "Debugging & Observability", "structured_obs", "Has structured logs, trace, or metrics plumbing.",
        exists_any("scripts/halo/**", "logs/agent_audit.log", "orchestration/instrument_eras.yaml"),
        file_contains(("src/**/*.py", "scripts/**/*.py"), (r"jsonl", r"trace", r"metrics?")))
    add(3, "Security", "security_automation", "Automates secret/PII/security checks.",
        exists_any("scripts/hooks/pii_precommit.sh", ".github/workflows/*dependabot*", ".github/dependabot.yml"))
    add(3, "Task Discovery", "machine_task_index", "Has structured or indexed task coordination.",
        exists_any("handoffs/active/master-handoff-index.md", ".claude/dependency-map.json",
                   "orchestration/autopilot_journal.jsonl"))
    add(3, "Product & Experimentation", "structured_experiments", "Has structured reports/journals/configured evals.",
        exists_any("orchestration/autopilot_journal.jsonl", "orchestration/reports/**",
                   "orchestration/eval_registry.yaml", "data/**"))

    # Level 4: Optimized.
    add(4, "Style & Validation", "incremental_validation", "Supports incremental or changed-file validation.",
        exists_any("scripts/gitnexus-analyze.sh", "scripts/validate/check_numeric_literals.py"),
        file_contains(("scripts/**/*.py", "scripts/**/*.sh", "Makefile"), (r"git diff", r"changed files?", r"incremental")))
    add(4, "Build System", "build_speed", "Has build caching, profiling, or optimized build lanes.",
        path_name_contains("ccache", "pgo", "bolt", "cache"),
        file_contains(CONFIG_FILES, (r"cache", r"pgo", r"bolt", r"ccache")))
    add(4, "Testing", "fast_safe_tests", "Has parallel, flaky, or safety-aware test controls.",
        exists_any("scripts/hooks/check_pytest_safety.sh"),
        file_contains(("pyproject.toml", "pytest.ini", "scripts/**/*.py", "scripts/**/*.sh"),
                      (r"xdist", r"pytest-xdist", r"flaky", r"timeout")))
    add(4, "Documentation", "generated_docs", "Builds or refreshes docs/site/wiki from sources.",
        exists_any("scripts/docs/**", "site/**", "wiki/**"))
    add(4, "Dev Environment", "health_automation", "Has health/session/storage automation.",
        exists_any("scripts/session/health_check.sh", "scripts/session/session_init.sh",
                   "scripts/session/monitor_storage.sh"))
    add(4, "Debugging & Observability", "analysis_reports", "Has analyzers or report generators over logs/traces.",
        exists_any("scripts/utils/agent_log_analyze.sh", "scripts/analysis/**", "orchestration/reports/**"))
    add(4, "Security", "security_audit", "Has security-review, audit, or hardening surfaces.",
        exists_any("handoffs/active/security-review-skill.md", "scripts/hooks/pii_precommit.sh",
                   "scripts/hooks/earlyoom_audit.sh"))
    add(4, "Task Discovery", "prioritized_tasks", "Prioritizes tasks with dependencies and reporting rules.",
        file_contains(("handoffs/active/*.md", "AGENTS.md", "CLAUDE.md"),
                      (r"Dependency graph", r"Prioritized task", r"Reporting instructions")))
    add(4, "Product & Experimentation", "replay_analysis", "Can replay/analyze experiments without rerunning them.",
        exists_any("scripts/analysis/**", "orchestration/reports/**"),
        file_contains(("scripts/**/*.py", "handoffs/active/*.md"), (r"replay", r"Pareto", r"frontier")))

    # Level 5: Autonomous.
    add(5, "Style & Validation", "agent_guards", "Agent-facing guards prevent unsafe edits/actions.",
        exists_any("scripts/hooks/agents_schema_guard.sh", "scripts/hooks/check_filesystem_path.sh",
                   "AGENTS.md"))
    add(5, "Build System", "autonomous_runner", "Has autonomous/nightshift runner infrastructure.",
        exists_any("scripts/nightshift/**", "scripts/autopilot/**"))
    add(5, "Testing", "auto_eval_gates", "Has automated eval/safety gates for candidate changes.",
        exists_any("scripts/autopilot/**", "src/eval_tower.py", "src/safety_gate.py",
                   "orchestration/eval_registry.yaml"))
    add(5, "Documentation", "agent_doc_loop", "Agents have durable handoff/progress documentation loops.",
        exists_any("handoffs/active/master-handoff-index.md", "progress/**", ".claude/commands/**"))
    add(5, "Dev Environment", "self_healing_ops", "Has self-healing/restart or stale-process controls.",
        exists_any("scripts/session/emergency_cleanup.sh", "scripts/nightshift/inference_guard.sh",
                   "scripts/server/orchestrator_stack.py"))
    add(5, "Debugging & Observability", "closed_loop_obs", "Feeds traces/logs into closed-loop analysis.",
        exists_any("logs/agent_audit.log", "scripts/halo/convert_tap_to_otel.py",
                   "orchestration/repl_memory/**"))
    add(5, "Security", "autonomous_security_review", "Has agent-usable security review or policy gates.",
        exists_any("handoffs/active/security-review-skill.md", "scripts/hooks/pii_precommit.sh",
                   ".claude/skills/security-review/**"))
    add(5, "Task Discovery", "auto_remediation_queue", "Has an autopilot/remediation queue or self-running lab.",
        exists_any("scripts/autopilot/**", "handoffs/active/frontier-f2-self-running-lab.md",
                   "handoffs/active/master-handoff-index.md"))
    add(5, "Product & Experimentation", "self_optimizing_loop", "Has Pareto/evolutionary optimization loops.",
        exists_any("scripts/autopilot/**", "orchestration/autopilot_journal.jsonl",
                   "orchestration/pareto_archive.json"))

    return c


def _repo_level(pass_rates: dict[int, float]) -> dict[str, object]:
    achieved = 0
    blocked_by: int | None = None
    for level in range(1, 6):
        if pass_rates.get(level, 0.0) >= UNLOCK_THRESHOLD:
            achieved = level
        else:
            blocked_by = level
            break
    return {
        "achieved_level": achieved,
        "achieved_label": LEVELS.get(achieved, "Below Functional"),
        "next_level": blocked_by,
        "next_label": LEVELS.get(blocked_by or 0),
    }


def score_repositories(repos: dict[str, Path]) -> dict[str, object]:
    criteria = build_criteria()
    repo_results: dict[str, object] = {}
    criterion_coverage: dict[str, object] = {}

    for name, path in repos.items():
        criterion_results: list[dict[str, object]] = []
        by_level: dict[int, list[bool]] = {level: [] for level in LEVELS}
        by_pillar: dict[str, list[bool]] = {pillar: [] for pillar in PILLARS}

        for criterion in criteria:
            result = criterion.evaluate(path)
            by_level[criterion.level].append(result.passed)
            by_pillar[criterion.pillar].append(result.passed)
            criterion_results.append(
                {
                    "id": criterion.id,
                    "level": criterion.level,
                    "pillar": criterion.pillar,
                    "description": criterion.description,
                    "passed": result.passed,
                    "evidence": result.evidence,
                }
            )

        level_rates = {
            level: (sum(values) / len(values) if values else 0.0)
            for level, values in by_level.items()
        }
        pillar_rates = {
            pillar: (sum(values) / len(values) if values else 0.0)
            for pillar, values in by_pillar.items()
        }
        maturity = _repo_level(level_rates)
        repo_results[name] = {
            "path": str(path),
            "exists": path.exists(),
            "maturity": maturity,
            "level_rates": level_rates,
            "pillar_rates": pillar_rates,
            "criteria": criterion_results,
        }

    for criterion in criteria:
        passed_repos: list[str] = []
        failed_repos: list[str] = []
        for name, repo_result in repo_results.items():
            repo_criteria = repo_result["criteria"]  # type: ignore[index]
            match = next(r for r in repo_criteria if r["id"] == criterion.id)
            if match["passed"]:
                passed_repos.append(name)
            else:
                failed_repos.append(name)
        criterion_coverage[criterion.id] = {
            "level": criterion.level,
            "pillar": criterion.pillar,
            "description": criterion.description,
            "coverage": len(passed_repos) / len(repos) if repos else 0.0,
            "passed_repos": passed_repos,
            "failed_repos": failed_repos,
        }

    portfolio_level_rates = {
        level: sum(
            item["level_rates"][level] for item in repo_results.values()  # type: ignore[index]
        ) / len(repo_results)
        for level in LEVELS
    }
    portfolio_maturity = _repo_level(portfolio_level_rates)
    generated_at = datetime.now(UTC).isoformat()
    report = {
        "generated_at": generated_at,
        "unlock_threshold": UNLOCK_THRESHOLD,
        "levels": LEVELS,
        "pillars": PILLARS,
        "repos": repo_results,
        "criterion_coverage": criterion_coverage,
        "portfolio": {
            "maturity": portfolio_maturity,
            "level_rates": portfolio_level_rates,
        },
    }
    report["remediation_queue"] = build_remediation_queue(report)
    return report


def _queue_priority(criterion_level: int, next_level: int | None) -> str:
    if next_level is not None and criterion_level == next_level:
        return "P0"
    if next_level is not None and criterion_level < next_level:
        return "P1"
    return "P2"


def build_remediation_queue(report: dict[str, object]) -> dict[str, object]:
    """Build deterministic agent-ready work items from failed readiness criteria."""
    repos = report["repos"]  # type: ignore[index]
    coverage = report["criterion_coverage"]  # type: ignore[index]
    items: list[dict[str, object]] = []

    priority_rank = {"P0": 0, "P1": 1, "P2": 2}
    pillar_rank = {pillar: index for index, pillar in enumerate(PILLARS)}

    for repo_name, repo_data in repos.items():  # type: ignore[union-attr]
        maturity = repo_data["maturity"]
        next_level = maturity["next_level"]
        for criterion in repo_data["criteria"]:
            if criterion["passed"]:
                continue
            criterion_id = criterion["id"]
            criterion_coverage = coverage[criterion_id]
            priority = _queue_priority(criterion["level"], next_level)
            items.append(
                {
                    "id": f"readiness:{repo_name}:{criterion_id}",
                    "status": "open",
                    "priority": priority,
                    "category": "repo_readiness",
                    "repo": repo_name,
                    "repo_path": repo_data["path"],
                    "criterion_id": criterion_id,
                    "level": criterion["level"],
                    "level_label": LEVELS[criterion["level"]],
                    "pillar": criterion["pillar"],
                    "title": f"{repo_name}: satisfy {criterion_id}",
                    "objective": criterion["description"],
                    "acceptance": (
                        f"`{criterion_id}` passes for `{repo_name}` on the next "
                        "repo readiness scorer run."
                    ),
                    "reason": (
                        f"{repo_name} is at {maturity['achieved_label']} "
                        f"(L{maturity['achieved_level']}); next gate is "
                        f"{maturity['next_label'] or 'complete'}."
                    ),
                    "blocking_next_gate": next_level is not None
                    and criterion["level"] == next_level,
                    "portfolio_coverage": criterion_coverage["coverage"],
                    "evidence": criterion["evidence"],
                    "source": "scripts/validate/repo_readiness_scorer.py",
                }
            )

    items.sort(
        key=lambda item: (
            priority_rank[str(item["priority"])],
            int(item["level"]),
            -float(item["portfolio_coverage"]),
            pillar_rank[str(item["pillar"])],
            str(item["repo"]),
            str(item["criterion_id"]),
        )
    )
    return {
        "version": QUEUE_VERSION,
        "generated_at": report["generated_at"],
        "item_count": len(items),
        "items": items,
    }


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def render_markdown(report: dict[str, object]) -> str:
    repos = report["repos"]  # type: ignore[index]
    portfolio = report["portfolio"]  # type: ignore[index]
    lines = [
        "# EPYC Repo Readiness Report",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Unlock threshold: `{_pct(float(report['unlock_threshold']))}`",
        "",
        "## Portfolio Summary",
        "",
        f"- Portfolio level: **{portfolio['maturity']['achieved_label']}** "  # type: ignore[index]
        f"(L{portfolio['maturity']['achieved_level']})",  # type: ignore[index]
        "",
        "| Level | Name | Pass rate |",
        "|---:|---|---:|",
    ]
    for level, label in LEVELS.items():
        rate = portfolio["level_rates"][level]  # type: ignore[index]
        lines.append(f"| {level} | {label} | {_pct(rate)} |")

    lines.extend([
        "",
        "## Repo Summary",
        "",
        "| Repo | Level | Next gate | L1 | L2 | L3 | L4 | L5 |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ])
    for name, data in repos.items():  # type: ignore[union-attr]
        maturity = data["maturity"]
        next_label = maturity["next_label"] or "complete"
        rates = data["level_rates"]
        lines.append(
            f"| {name} | {maturity['achieved_label']} (L{maturity['achieved_level']}) "
            f"| {next_label} | "
            f"{_pct(rates[1])} | {_pct(rates[2])} | {_pct(rates[3])} | "
            f"{_pct(rates[4])} | {_pct(rates[5])} |"
        )

    lines.extend([
        "",
        "## Lowest Portfolio Criteria",
        "",
        "| Criterion | Level | Pillar | Coverage | Failed repos |",
        "|---|---:|---|---:|---|",
    ])
    coverage = sorted(
        report["criterion_coverage"].items(),  # type: ignore[index]
        key=lambda kv: (kv[1]["coverage"], kv[1]["level"], kv[0]),
    )
    for cid, data in coverage[:15]:
        failed = ", ".join(data["failed_repos"]) or "-"
        lines.append(
            f"| `{cid}` | {data['level']} | {data['pillar']} | "
            f"{_pct(data['coverage'])} | {failed} |"
        )

    lines.extend(["", "## Per-Repo Blocking Criteria", ""])
    for name, data in repos.items():  # type: ignore[union-attr]
        maturity = data["maturity"]
        next_level = maturity["next_level"]
        lines.append(f"### {name}")
        if next_level is None:
            lines.append("")
            lines.append("All levels meet the unlock threshold.")
            lines.append("")
            continue
        lines.append("")
        lines.append(f"Next gate: L{next_level} {maturity['next_label']}")
        lines.append("")
        lines.append("| Criterion | Pillar | Status | Evidence |")
        lines.append("|---|---|---|---|")
        for criterion in data["criteria"]:
            if criterion["level"] != next_level:
                continue
            status = "pass" if criterion["passed"] else "fail"
            evidence = ", ".join(criterion["evidence"]) or "-"
            lines.append(
                f"| `{criterion['id']}` | {criterion['pillar']} | {status} | {evidence} |"
            )
        lines.append("")

    lines.extend([
        "## Notes",
        "",
        "- Criteria are deterministic file/pattern checks, not LLM judgments.",
        "- A pass means the artifact exists; it does not certify quality.",
        "- Failed criteria are intended to seed a remediation queue.",
    ])
    return "\n".join(lines) + "\n"


def _parse_repo_arg(values: list[str] | None) -> dict[str, Path]:
    if not values:
        return DEFAULT_REPOS
    repos: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit(f"--repo expects name=/abs/path, got {value!r}")
        name, raw_path = value.split("=", 1)
        repos[name] = Path(raw_path)
    return repos


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        action="append",
        help="Override repo set with name=/abs/path. Repeatable.",
    )
    parser.add_argument("--output-json", type=Path, help="Write JSON report to this path.")
    parser.add_argument("--output-md", type=Path, help="Write Markdown report to this path.")
    parser.add_argument(
        "--output-remediation-json",
        type=Path,
        help="Write failed readiness criteria as deterministic remediation queue JSON.",
    )
    parser.add_argument(
        "--min-portfolio-level",
        type=int,
        default=0,
        help="Exit non-zero if the portfolio achieved level is below this value.",
    )
    args = parser.parse_args(argv)

    report = score_repositories(_parse_repo_arg(args.repo))
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if args.output_remediation_json:
        args.output_remediation_json.parent.mkdir(parents=True, exist_ok=True)
        queue_json = json.dumps(report["remediation_queue"], indent=2, sort_keys=True)
        args.output_remediation_json.write_text(queue_json, encoding="utf-8")
    markdown = render_markdown(report)
    if args.output_md:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(markdown, encoding="utf-8")
    else:
        print(markdown)

    achieved = report["portfolio"]["maturity"]["achieved_level"]  # type: ignore[index]
    if achieved < args.min_portfolio_level:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
