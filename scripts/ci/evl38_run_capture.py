"""Capture the complete EVL-38 gate outcome through the existing native verifier."""
from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
LLAMA_PIN = "ffc1bac82eeca6f9099e1ccd9ba49703c460a115"
PACKAGES = {"pytest": "9.0.3", "iniconfig": "2.3.0", "packaging": "26.0",
            "pluggy": "1.6.0", "Pygments": "2.20.0", "PyYAML": "6.0.3"}
EXPECTED_ID = ("tests.validate.test_candidate_eval_gate_periodic",
               "test_candidate_eval_gate_records_exact_outcome")


def _write_once(path: Path, data: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(data)


def _load_carrier():
    path = ROOT / "scripts/ci/native_conformance.py"
    spec = importlib.util.spec_from_file_location("evl38_native_conformance", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the pinned native conformance carrier")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _artifact_snapshot(paths: tuple[Path, ...]) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in paths:
        if path.is_dir() and not path.is_symlink():
            for leaf in sorted(path.rglob("*")):
                if leaf.is_file() and not leaf.is_symlink():
                    result[str(leaf)] = hashlib.sha256(leaf.read_bytes()).hexdigest()
                elif leaf.is_symlink():
                    result[str(leaf)] = "symlink-refused"
        elif path.is_file() and not path.is_symlink():
            result[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            result[str(path)] = "absent-or-nonregular"
    return result


def _git_head(path: Path) -> str:
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def _git_status(path: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(path), "status", "--porcelain", "--untracked-files=all"],
        text=True,
    )


def _input_paths(app: Path, research: Path, llama: Path, manifest: Path,
                 environment: Path, install_log: Path) -> list[Path]:
    paths = [
        ROOT / ".github/workflows/evl38-periodic-candidate-gate.yml",
        ROOT / "scripts/ci/evl38_run_capture.py",
        ROOT / "scripts/ci/evl38_source_context.py",
        ROOT / "scripts/ci/evl38_expected_cases.json",
        ROOT / "scripts/ci/evl38-constraints.txt",
        ROOT / "scripts/ci/native_conformance.py",
        ROOT / "scripts/validate/candidate_eval_gate.sh",
        ROOT / "scripts/validate/repo_readiness_scorer.py",
        ROOT / "scripts/validate/validate_agents_structure.py",
        ROOT / "scripts/validate/validate_agents_references.py",
        ROOT / "scripts/validate/validate_claude_md_matrix.py",
        ROOT / "scripts/validate/validate_doc_drift.py",
        ROOT / "scripts/validate/validate_registry.py",
        ROOT / "scripts/validate/check_model_probe_scoreboard_guard.py",
        ROOT / "scripts/validate/check_stack_fact_migration_discipline.py",
        ROOT / "scripts/validate/pii_fixture_eval.py",
        ROOT / "tests/validate/test_candidate_eval_gate_periodic.py",
        ROOT / "tests/validate/test_repo_readiness_scorer.py",
        ROOT / "tests/validate/test_check_model_probe_scoreboard_guard.py",
        ROOT / "tests/validate/test_check_stack_fact_migration_discipline.py",
        ROOT / "tests/conftest.py",  # loaded by the inner, unmodified gate pytest command
        ROOT / "tests/__init__.py",
        ROOT / "docs/reference/agent-config/CLAUDE_MD_MATRIX.md",
        ROOT / "docs/reference/agent-config/claude_md_matrix.json",
        ROOT / "handoffs/active/vidya-belief-substrate-program.md",
        ROOT / "scripts/vidya/adapters/README.md",
        ROOT / "scripts/vidya/claim_tuple.py",
        ROOT / "scripts/vidya/measurement_record.py",
        ROOT / "scripts/vidya/frames.py",
        ROOT / "scripts/vidya/adapters/__init__.py",
        ROOT / "scripts/vidya/adapters/ci_conformance.py",
        ROOT / "scripts/hooks/pii_precommit.sh",
        ROOT / "research/fixtures/pii_hygiene_eval.jsonl",
        app / "orchestration/model_registry.yaml",
        research / "orchestration/model_registry.yaml",
        manifest,
        environment,
        install_log,
    ]
    optional_root_inputs = [
        ROOT / "AGENTS.md", ROOT / "CLAUDE.md", ROOT / "CLAUDE_GUIDE.md",
        ROOT / "README.md", ROOT / "Makefile", ROOT / "pyproject.toml",
        ROOT / ".pre-commit-config.yaml", ROOT / ".claude/dependency-map.json",
    ]
    paths.extend(path for path in optional_root_inputs if path.is_file())
    return list(dict.fromkeys(path.resolve() for path in paths))


def main() -> int:
    if len(sys.argv) != 7:
        raise SystemExit("usage: evl38_run_capture.py APP RESEARCH LLAMA RESULT_DIR INSTALL_LOG DEPENDENCY_MANIFEST")
    app, research, llama, result_dir, install_log, dependency_manifest = map(Path, sys.argv[1:])
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    result_dir = result_dir.resolve()
    install_log = install_log.resolve()
    dependency_manifest = dependency_manifest.resolve()
    expected_venv = (runner_temp / "evl38" / "venv").resolve()
    if not result_dir.is_relative_to(runner_temp) or os.path.lexists(result_dir):
        raise SystemExit("result directory must be a fresh path under RUNNER_TEMP")
    result_dir.mkdir(parents=True, mode=0o700)
    if Path(sys.prefix).resolve() != expected_venv:
        raise SystemExit("capture must run from the exact isolated EVL38 venv")
    if platform.python_implementation() != "CPython" or platform.python_version() != "3.13.15":
        raise SystemExit("capture requires CPython 3.13.15")
    installed = {name: importlib.metadata.version(name) for name in PACKAGES}
    if installed != PACKAGES:
        raise SystemExit(f"installed locked package versions differ: {installed}")
    if not install_log.is_file():
        raise SystemExit("original dependency-install log is missing")
    if any(not (path / ".git").exists() for path in (app, research, llama)):
        raise SystemExit("all three source checkouts with Git identity are required")
    heads = {"root": _git_head(ROOT), "app": _git_head(app),
             "research": _git_head(research), "llama": _git_head(llama)}
    if heads["llama"] != LLAMA_PIN:
        raise SystemExit("llama checkout differs from the immutable ffc1 serving-source pin")

    pip_version = subprocess.check_output([sys.executable, "-m", "pip", "--version"],
                                          cwd=ROOT, text=True).strip()
    environment = {
        "python": sys.version,
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "pip": pip_version,
        "packages": installed,
        "venv": str(expected_venv),
        "llama_expected_commit": LLAMA_PIN,
        "subrepo_heads_at_driver_start": heads,
    }
    _write_once(dependency_manifest, (json.dumps(environment, sort_keys=True, indent=2) + "\n").encode())

    source_context = result_dir / "source-context.json"
    context_command = [sys.executable, str(ROOT / "scripts/ci/evl38_source_context.py"),
                       "--repo", f"root={ROOT}", "--repo", f"app={app}",
                       "--repo", f"research={research}", "--repo", f"llama={llama}",
                       "--output", str(source_context)]
    context_run = subprocess.run(context_command, cwd=ROOT, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True, check=False)
    _write_once(result_dir / "source-context-generator.log", context_run.stdout.encode())
    if context_run.returncode:
        raise SystemExit(f"source context failed with {context_run.returncode}")

    cases_path = ROOT / "scripts/ci/evl38_expected_cases.json"
    cases_doc = json.loads(cases_path.read_bytes())
    expected = cases_doc.get("root") if cases_doc.get("schema") == "epyc.evl38.expected_cases/v1" else None
    wanted = [{"classname": EXPECTED_ID[0], "name": EXPECTED_ID[1]}]
    if expected != wanted:
        raise SystemExit("expected case manifest differs from the reviewed one-case gate wrapper")
    os.environ.update({
        "EPYC_ORCHESTRATOR_REPO": str(app.resolve()),
        "EPYC_INFERENCE_RESEARCH_REPO": str(research.resolve()),
        "EPYC_LLAMA_REPO": str(llama.resolve()),
        "CANDIDATE_EVAL_REQUIRE_DEPS": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "PYTHONUNBUFFERED": "1",
        "EVL38_GATE_LOG": str(result_dir / "gate.log"),
        "EVL38_GATE_EXIT_FILE": str(result_dir / "gate-exit-code.txt"),
    })
    junit = result_dir / "original-junit.xml"
    native_dir = result_dir / "native"
    read_paths = _input_paths(app, research, llama, source_context, dependency_manifest, install_log)
    read_paths.append(result_dir / "source-context-generator.log")
    nodeid = f"{EXPECTED_ID[0].replace('.', '/')}.py::{EXPECTED_ID[1]}"
    argv = [sys.executable, "-m", "pytest", "-q", "--noconftest", "-c", "/dev/null",
            f"--rootdir={ROOT}", "-o", "addopts=", "-p", "no:cacheprovider",
            f"--junitxml={junit}", nodeid]
    carrier = _load_carrier()
    record = carrier.capture_fixture_execution(
        argv=argv, cwd=ROOT, junit=junit, output=native_dir,
        repositories={"root": str(ROOT), "app": str(app), "research": str(research),
                      "llama": str(llama)},
        read_paths=read_paths,
        selections=[nodeid, "complete candidate_eval_gate.sh result captured verbatim"],
    )

    source_context_after = result_dir / "source-context-after.json"
    context_after_command = [sys.executable, str(ROOT / "scripts/ci/evl38_source_context.py"),
                             "--repo", f"root={ROOT}", "--repo", f"app={app}",
                             "--repo", f"research={research}", "--repo", f"llama={llama}",
                             "--output", str(source_context_after)]
    context_after_run = subprocess.run(context_after_command, cwd=ROOT, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, check=False)
    context_after_log = result_dir / "source-context-after-generator.log"
    _write_once(context_after_log, context_after_run.stdout.encode())
    if context_after_run.returncode:
        raise SystemExit(f"post-gate source context failed with {context_after_run.returncode}")
    if hashlib.sha256(source_context_after.read_bytes()).digest() != hashlib.sha256(
            source_context.read_bytes()).digest():
        raise SystemExit("physical Git source/config context changed during the full gate")
    read_paths.extend((source_context_after, context_after_log))

    gate_exit_path = result_dir / "gate-exit-code.txt"
    gate_log = result_dir / "gate.log"
    try:
        gate_exit_code = int(gate_exit_path.read_text(encoding="ascii").strip())
    except (OSError, ValueError) as exc:
        raise SystemExit(f"exact candidate gate exit was not retained: {exc}")
    if gate_exit_code < 0 or not gate_log.is_file():
        raise SystemExit("candidate gate process status/log is incomplete")
    summary = record.get("summary")
    expected_status = "passed" if gate_exit_code == 0 else "failure"
    if (not isinstance(summary, dict) or summary.get("cases") !=
            [{"classname": EXPECTED_ID[0], "name": EXPECTED_ID[1], "status": expected_status}]):
        raise SystemExit("native JUnit identity/status differs from the exact gate exit")
    expected_native = gate_exit_code == 0
    if record.get("fixture_execution_conformant") is not expected_native:
        raise SystemExit("native TRUE/FALSE value does not match the full-gate outcome")

    receipt_path = native_dir / "receipt.json"
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "scripts/vidya"))
    from adapters.ci_conformance import native_rows, project_ci_conformance
    from claim_tuple import grade

    before = _artifact_snapshot((*read_paths, result_dir, install_log))
    rows = native_rows(receipt_path)
    if len(rows) != 1:
        raise SystemExit("existing CI adapter must yield exactly one TRUE/FALSE ClaimTuple")
    tuple_ = project_ci_conformance(rows[0])
    q, t, reasons = grade(tuple_)
    rows_after = native_rows(receipt_path)
    if len(rows_after) != 1:
        raise SystemExit("existing CI adapter failed to reopen exactly one native tuple")
    q_after, t_after, reasons_after = grade(project_ci_conformance(rows_after[0]))
    after = _artifact_snapshot((*read_paths, result_dir, install_log))
    heads_after_grade = {"root": _git_head(ROOT), "app": _git_head(app),
                         "research": _git_head(research), "llama": _git_head(llama)}
    clean_after_grade = all(not _git_status(path) for path in (ROOT, app, research, llama))
    validation = {
        "schema": "epyc.evl38.capture_validation/v1",
        "native_value": record.get("fixture_execution_conformant"),
        "candidate_gate_exit_code": gate_exit_code,
        "candidate_gate_verdict": "green" if gate_exit_code == 0 else "red",
        "candidate_gate_log_sha256": hashlib.sha256(gate_log.read_bytes()).hexdigest(),
        "selected_case_summary": summary,
        "shared_grade": {"Q": q, "T": t},
        "shared_grade_reopened": {"Q": q_after, "T": t_after},
        "shared_grade_reasons": list(reasons),
        "shared_grade_reopened_reasons": list(reasons_after),
        "source_context_sha256": hashlib.sha256(source_context.read_bytes()).hexdigest(),
        "install_log_sha256": hashlib.sha256(install_log.read_bytes()).hexdigest(),
        "subrepo_heads": heads,
        "repository_heads_after_shared_grade": heads_after_grade,
        "repositories_clean_after_shared_grade": clean_after_grade,
        "artifact_membership_and_hashes_before_shared_grade": before,
        "artifact_membership_and_hashes_after_shared_grade": after,
        "all_inputs_and_originals_unchanged": before == after,
        "scope": "verified scheduled full-gate execution; a red gate is retained and fails workflow after artifact upload; no readiness, promotion, continuous-health, inference, or performance claim",
    }
    _write_once(result_dir / "validation.json",
                (json.dumps(validation, sort_keys=True, indent=2) + "\n").encode())
    if ((q, t) != ("Judged", "Located") or (q_after, t_after) != ("Judged", "Located")
            or before != after or heads_after_grade != heads
            or not clean_after_grade or record.get("fixture_execution_conformant") is None):
        return 1
    # TRUE or FALSE is a captured checker result. The workflow separately reflects
    # the exact inner shell exit after uploading the retained native originals.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
