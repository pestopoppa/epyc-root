"""Capture one scheduled root candidate-eval gate as an existing CI verifier receipt."""
from __future__ import annotations

import json
import importlib.metadata
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    if len(sys.argv) != 6:
        raise SystemExit("usage: evl38_run_capture.py APP RESEARCH LLAMA OUTPUT_DIR DEPENDENCY_MANIFEST")
    app, research, llama, output, dependency_manifest = map(Path, sys.argv[1:])
    required = {"app": app, "research": research, "llama": llama}
    if any(not (path / ".git").exists() for path in required.values()):
        raise SystemExit("all three source checkouts with Git identity are required")
    os.environ["EPYC_ORCHESTRATOR_REPO"] = str(app.resolve())
    os.environ["EPYC_INFERENCE_RESEARCH_REPO"] = str(research.resolve())
    os.environ["EPYC_LLAMA_REPO"] = str(llama.resolve())

    environment = {
        "python": sys.version,
        "pip": subprocess.check_output(
            [sys.executable, "-m", "pip", "--version"], cwd=ROOT, text=True
        ).strip(),
        "candidate_gate_locked_packages": {
            name: importlib.metadata.version(name)
            for name in ("pytest", "iniconfig", "packaging", "pluggy", "Pygments", "PyYAML")
        },
        "constraints_file": str((ROOT / "scripts/ci/evl38-constraints.txt").resolve()),
        "runner_executable": str(Path(sys.executable).resolve()),
    }
    dependency_manifest = dependency_manifest.resolve()
    with dependency_manifest.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(environment, sort_keys=True, indent=2) + "\n")

    junit = output / "candidate-eval-gate.junit.xml"
    repos = [ROOT, app, research, llama]
    read_paths = [
        ROOT / "scripts/validate/candidate_eval_gate.sh",
        ROOT / "scripts/ci/evl38_run_capture.py",
        ROOT / ".github/workflows/evl38-periodic-candidate-gate.yml",
        ROOT / "scripts/ci/evl38-constraints.txt",
        dependency_manifest,
        ROOT / "tests/validate/test_candidate_eval_gate_periodic.py",
        ROOT / "scripts/validate/repo_readiness_scorer.py",
        ROOT / "scripts/validate/validate_agents_structure.py",
        ROOT / "scripts/validate/validate_agents_references.py",
        ROOT / "scripts/validate/validate_claude_md_matrix.py",
        ROOT / "scripts/validate/validate_doc_drift.py",
        ROOT / "scripts/validate/validate_registry.py",
        ROOT / "scripts/validate/check_model_probe_scoreboard_guard.py",
        ROOT / "scripts/validate/check_stack_fact_migration_discipline.py",
        ROOT / "scripts/validate/pii_fixture_eval.py",
        ROOT / "tests/validate/test_repo_readiness_scorer.py",
        ROOT / "tests/validate/test_check_model_probe_scoreboard_guard.py",
        ROOT / "tests/validate/test_check_stack_fact_migration_discipline.py",
        ROOT / "docs/reference/agent-config/CLAUDE_MD_MATRIX.md",
        ROOT / "docs/reference/agent-config/claude_md_matrix.json",
        app / "orchestration/model_registry.yaml",
        research / "orchestration/model_registry.yaml",
        ROOT / "research/fixtures/pii_hygiene_eval.jsonl",
        ROOT / "scripts/hooks/pii_precommit.sh",
    ]
    # These documents and configuration files are traversed by the actual
    # validator/scorer. The repository identities bind each complete tracked
    # source tree; explicit read paths retain the principal content inputs.
    for pattern in ("agents/*.md", "agents/shared/*.md", "docs/guides/agent-workflows/*.md"):
        read_paths.extend(path for path in ROOT.glob(pattern) if path.is_file())
    read_paths.extend(path for path in [
        ROOT / "AGENTS.md", ROOT / "CLAUDE.md", ROOT / "CLAUDE_GUIDE.md",
        ROOT / "README.md", ROOT / "Makefile", ROOT / "pyproject.toml",
        ROOT / ".pre-commit-config.yaml",
    ] if path.is_file())
    command = [
        sys.executable, "-m", "pytest", "-q", "--noconftest",
        "-c", "/dev/null", "--rootdir", str(ROOT), "-o", "addopts=",
        "-p", "no:cacheprovider",
        "--junitxml", str(junit),
        str(ROOT / "tests/validate/test_candidate_eval_gate_periodic.py"),
    ]
    carrier = ROOT / "scripts/ci/native_conformance.py"
    invocation = [
        sys.executable, str(carrier),
        "--cwd", str(ROOT),
        "--junit", str(junit),
        "--output", str(output / "receipt"),
        *[item for name, path in (("root", ROOT), ("app", app),
                                  ("research", research), ("llama", llama))
          for item in ("--repo", f"{name}={path.resolve()}")],
        *[item for path in read_paths for item in ("--read-path", str(path))],
        "--select", "tests/validate/test_candidate_eval_gate_periodic.py::test_candidate_eval_gate_exits_zero",
        "--select", "scripts/validate/candidate_eval_gate.sh full exact invocation",
        "--", *command,
    ]
    # native_conformance's argparse REMAINDER consumes a literal -- delimiter.
    return subprocess.run(invocation, cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
