"""Prepare complete declared source/config readset, then invoke native capture."""
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT_TESTS = [
    "tests/test_index_state_prune.py",
    "tests/test_index_state_citation_gate.py",
    "tests/test_index_state_dep_cycles.py",
    "tests/test_index_state_readiness.py",
    "tests/test_index_state_graph_freshness.py",
]
CONFIG_NAMES = {"pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini"}


def tracked_inputs(repo):
    names = subprocess.check_output(
        ["git", "-C", str(repo), "ls-files", "-z"]
    ).decode().split("\0")
    for name in names:
        if not name:
            continue
        path = repo / name
        # Selected fixtures read synthetic/temp data; capture their source plus
        # pytest configuration, rather than unrelated historical result corpora.
        if path.suffix.lower() == ".py" or path.name in CONFIG_NAMES:
            if not path.is_file():
                raise RuntimeError(f"tracked declared input is missing: {path}")
            yield path.resolve()


def main():
    job = os.environ["NI06_JOB"]
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    root = workspace / "root"
    recipe = workspace / "recipe"
    tested = root if job == "root-graph" else workspace / "app"
    result = Path(os.environ["RUNNER_TEMP"]) / "ni06" / "result" / job
    result.mkdir(parents=True, exist_ok=True)
    status = {"job": job, "state": "preparing", "exit_code": None}
    status_path = result / "status.json"
    try:
        freeze = result / "pip-freeze.txt"
        freeze.write_bytes(subprocess.check_output(
            [sys.executable, "-m", "pip", "freeze", "--all"]
        ))
        environment = result / "environment.json"
        environment.write_text(json.dumps({
            "python": sys.version,
            "platform": platform.platform(),
            "install_command": os.environ["NI06_INSTALL_COMMAND"],
            "environment": {key: os.environ.get(key) for key in (
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTHONDONTWRITEBYTECODE",
                "PYTHONPATH", "ORCHESTRATOR_MOCK_MODE", "ORCHESTRATOR_LOG_DIR",
                "KB_RAG_QUERY_LENGTH_LOG",
            )},
            "isolation": "inert package shells; fake-only noninstantiable LLMPrimitives sentinel; real class/getter branch excluded" if job == "cj13" else "normal imports",
        }, indent=2) + "\n")
        junit = result / "junit.xml"
        if junit.exists():
            raise RuntimeError("JUnit must be absent before producer starts")
        os.environ["NI06_JUNIT_XML"] = str(junit)
        selections = ROOT_TESTS if job == "root-graph" else [
            "tests/unit/test_typed_decisions_judge_redundancy.py" if job == "cj13"
            else "tests/unit/test_kb_rag_tokenizer_identity.py"
        ]
        harness = recipe / "scripts/ci/ni06_reader_b_pytest.py"
        command = [sys.executable, str(harness)] if job == "cj13" else [
            sys.executable, "-m", "pytest", "-o", "addopts=", "--noconftest",
            "-p", "no:cacheprovider", "-q", *selections, f"--junitxml={junit}",
        ]
        repos = {"root": root, "recipe": recipe}
        if tested != root:
            repos["orchestrator"] = tested
        inputs = [freeze, environment, Path(__file__).resolve(), harness,
                  recipe / ".github/workflows/ni06.yml"]
        for repo in repos.values():
            inputs.extend(tracked_inputs(repo))
        inputs.extend(tested / selected for selected in selections)
        argv = [sys.executable, str(root / "scripts/ci/native_conformance.py"),
                "--cwd", str(tested), "--junit", str(junit),
                "--output", str(result / "native")]
        for label, repo in repos.items():
            argv.extend(["--repo", f"{label}={repo}"])
        for path in dict.fromkeys(inputs):
            argv.extend(["--read-path", str(path)])
        for selected in selections:
            argv.extend(["--select", selected])
        status["state"] = "running"
        status_path.write_text(json.dumps(status, indent=2) + "\n")
        exit_code = subprocess.call([*argv, "--", *command], cwd=tested)
        status.update(state="passed" if exit_code == 0 else "failed", exit_code=exit_code)
        return exit_code
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1, error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, indent=2) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
