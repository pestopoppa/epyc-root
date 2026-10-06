"""Declare exact fixture source/config/context readset before native execution."""
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

CONTEXT_NAMES = {"AGENTS.md", "CLAUDE.md", "README.md"}
CONFIG_SUFFIXES = {".cfg", ".ini", ".toml", ".yaml", ".yml"}
CONFIG_NAMES = {"pytest.ini", "setup.cfg", "tox.ini"}
SELECTIONS = [
    "tests/unit/test_kb_catalog_dependency.py",
    "tests/unit/test_colbert_lock_contract.py",
    "tests/unit/test_kb_rag_caps.py",
    "tests/unit/test_kb_rag_tokenizer_identity.py",
    "tests/unit/test_kb_rag_force_dedup.py",
]


def tracked_inputs(repo):
    names = subprocess.check_output(
        ["git", "-C", str(repo), "ls-files", "-z"]
    ).decode().split("\0")
    for name in names:
        if not name:
            continue
        path = repo / name
        is_workflow = ".github/workflows" in path.as_posix() and path.suffix.lower() in {".yml", ".yaml"}
        is_config = path.name in CONFIG_NAMES or path.suffix.lower() in CONFIG_SUFFIXES
        if path.suffix.lower() == ".py" or path.name in CONTEXT_NAMES or is_config or is_workflow:
            if not path.is_file():
                raise RuntimeError(f"tracked declared input is missing: {path}")
            yield path.resolve()


def main():
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    repos = {"root": workspace / "root", "recipe": workspace / "recipe",
             "orchestrator": workspace / "app"}
    result = Path(os.environ["RUNNER_TEMP"]) / "ni07" / "result" / "force-dedup"
    result.mkdir(parents=True, exist_ok=True)
    status = {"job": "force-dedup", "state": "preparing", "exit_code": None}
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
            "install_command": os.environ["NI07_INSTALL_COMMAND"],
            "environment": {key: os.environ.get(key) for key in (
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTHONDONTWRITEBYTECODE",
                "PYTHONPATH", "ORCHESTRATOR_MOCK_MODE", "ORCHESTRATOR_LOG_DIR",
                "KB_RAG_QUERY_LENGTH_LOG",
            )},
            "isolation": (
                "fake encoder/session/tokenizer only; temporary corpus/catalog/vector files; "
                "SQLite FTS5 required by force-dedup cases; no model, inference, embedding, "
                "ONNX, kernel, build, server, or live-index access"
            ),
        }, indent=2) + "\n")
        junit = result / "junit.xml"
        if junit.exists():
            raise RuntimeError("JUnit must be absent before producer starts")
        workflow = repos["recipe"] / ".github/workflows/ni07-kb-force-dedup.yml"
        inputs = [freeze, environment, Path(__file__).resolve(), workflow]
        for repo in repos.values():
            inputs.extend(tracked_inputs(repo))
        inputs.extend(repos["orchestrator"] / name for name in SELECTIONS)
        producer = repos["root"] / "scripts/ci/native_conformance.py"
        argv = [sys.executable, str(producer), "--cwd", str(repos["orchestrator"]),
                "--junit", str(junit), "--output", str(result / "native")]
        for label, repo in repos.items():
            argv.extend(["--repo", f"{label}={repo}"])
        for path in dict.fromkeys(inputs):
            argv.extend(["--read-path", str(path)])
        for name in SELECTIONS:
            argv.extend(["--select", name])
        command = [sys.executable, "-m", "pytest", "-o", "addopts=", "--noconftest",
                   "-p", "no:cacheprovider", "-q", *SELECTIONS, f"--junitxml={junit}"]
        status["state"] = "running"
        status_path.write_text(json.dumps(status, indent=2) + "\n")
        code = subprocess.call([*argv, "--", *command], cwd=repos["orchestrator"])
        status.update(state="passed" if code == 0 else "failed", exit_code=code)
        return code
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1,
                      error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, indent=2) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
