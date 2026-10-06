"""Capture the bounded synthetic DTAP failure-ledger controls with the pinned native CI reader in native CI."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import platform
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT_PIN = "1f09dde6818df8756be86feaabcedeb9f3a60748"
READSET_REL = Path("artifacts/ni07-14-tu-led1a/ni07-14-tu-led1a-readset.json")
SELECTION = [
    "scripts/autopilot/evals/dtap/tests/test_tool_contract.py",
    "scripts/autopilot/evals/dtap/tests/test_dtap_harness.py",
    "scripts/autopilot/evals/dtap/tests/test_judge_guard.py",
    "scripts/autopilot/evals/dtap/tests/test_failure_ledger.py",
]
CONFIG_NAMES = {"pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini"}


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tracked_python_config_paths(repo: Path, pin: str) -> set[str]:
    names = git(repo, "ls-tree", "-r", "--name-only", pin).splitlines()
    return {name for name in names
            if PurePosixPath(name).suffix == ".py" or PurePosixPath(name).name in CONFIG_NAMES}


def declared_app_paths(app: Path) -> set[str]:
    tracked = git(app, "ls-files", "-z").split("\0")
    paths = {"pyproject.toml", "uv.lock", "scripts/autopilot/evals/dtap/cases.json",
             "scripts/autopilot/evals/dtap/manifest.json"}
    for name in filter(None, tracked):
        path = PurePosixPath(name)
        under_harness = path.is_relative_to("scripts/autopilot/evals/dtap/harness")
        under_tests = path.is_relative_to("scripts/autopilot/evals/dtap/tests")
        under_fixtures = path.is_relative_to("scripts/autopilot/evals/dtap/fixtures")
        under_judges = path.is_relative_to("scripts/autopilot/evals/dtap/judges")
        if ((under_harness and path.suffix in {".py", ".json"})
                or (under_tests and path.suffix == ".py")
                or (under_fixtures and path.suffix == ".json")
                or (under_judges and path.name == "judge.py")):
            paths.add(name)
    return paths


def validate_readset(app: Path, inventory_path: Path, record: dict) -> list[Path]:
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    if inventory.get("schema") != "ni07-14-tu-led1a-source-readset.v1":
        raise ValueError("unsupported NI07 source-readset schema")
    if git(app, "rev-parse", "HEAD") != inventory.get("app_pin"):
        raise ValueError("application checkout differs from the readset pin")
    if os.environ.get("NI07_APP_PIN") != inventory.get("app_pin"):
        raise ValueError("workflow application pin differs from the readset")
    if os.environ.get("NI07_ROOT_PIN") != ROOT_PIN:
        raise ValueError("workflow native-producer pin differs from this recipe")
    listed = inventory.get("dtap_case_fixture_judge_harness_config_files")
    if not isinstance(listed, list):
        raise ValueError("application readset is missing its path list")
    expected = set()
    resolved = []
    for item in listed:
        if not isinstance(item, dict) or set(item) != {"path", "git_blob", "sha256"}:
            raise ValueError("malformed application source readset row")
        name = item["path"]
        if not isinstance(name, str):
            raise ValueError("source readset path is not normalized and relative")
        posix = PurePosixPath(name)
        if (posix.is_absolute() or posix.as_posix() != name
                or any(part in {"", ".", ".."} for part in posix.parts)):
            raise ValueError("source readset path is not normalized and relative")
        if name in expected:
            raise ValueError("duplicate application source readset path")
        expected.add(name)
        data = (app / name).read_bytes()
        blob = git(app, "rev-parse", f"{inventory['app_pin']}:{name}")
        if blob != item["git_blob"] or sha256(data) != item["sha256"]:
            raise ValueError(f"application source differs from pinned readset: {name}")
        resolved.append((app / name).resolve())
    if expected != declared_app_paths(app):
        raise ValueError("declared app readset does not cover the full DTAP import/config closure")
    if inventory.get("selection") != SELECTION:
        raise ValueError("readset test selection differs from the capture recipe")
    if inventory.get("root_carrier_pin") != ROOT_PIN:
        raise ValueError("readset native producer pin differs from this recipe")
    record["app_readset_paths"] = len(resolved)
    return resolved


def validate_pinned_paths(repo: Path, pin: str, rows: list[dict]) -> list[Path]:
    paths = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "git_blob", "sha256"}:
            raise ValueError("malformed pinned source path row")
        name = row["path"]
        if not isinstance(name, str):
            raise ValueError("pinned source path is not normalized and relative")
        rel = PurePosixPath(name)
        if (rel.is_absolute() or rel.as_posix() != name
                or any(part in {"", ".", ".."} for part in rel.parts)):
            raise ValueError("pinned source path is not normalized and relative")
        data = (repo / name).read_bytes()
        blob = git(repo, "rev-parse", f"{pin}:{name}")
        if blob != row["git_blob"] or sha256(data) != row["sha256"]:
            raise ValueError(f"pinned source differs from readset: {name}")
        paths.append((repo / name).resolve())
    return paths


def _write_exclusive(path: Path, data: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(data)


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, root, app = workspace / "recipe", workspace / "root", workspace / "app"
    output_root = temp / "ni07-14-tu-led1a" / "result"
    native_output = output_root / "native"
    status_path = output_root / "status.json"
    status = {"schema": "ni07-14-tu-led1a-ci-status.v1", "state": "preparing", "exit_code": None}
    try:
        if git(root, "rev-parse", "HEAD") != ROOT_PIN:
            raise ValueError("native-conformance carrier checkout is not the approved pin")
        inventory_path = recipe / READSET_REL
        capture_script = recipe / "scripts/ci/ni07_14_tu_led1a_capture.py"
        workflow_path = recipe / ".github/workflows/ni07-14-tu-led1a.yml"
        if not inventory_path.is_file() or not capture_script.is_file() or not workflow_path.is_file():
            raise ValueError("recipe inventory, capture script, or workflow is missing")
        app_paths = validate_readset(app, inventory_path, status)
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        if (inventory.get("app_repository") != "epyc-orchestrator"
                or inventory.get("root_carrier_repository") != "epyc-root"
                or inventory.get("recipe_repository") != "epyc-root"):
            raise ValueError("source readset repository identities are inconsistent")
        app_pin = inventory["app_pin"]
        recipe_pin = git(recipe, "rev-parse", "HEAD")
        app_closure_rows = inventory.get("app_python_config_closure", [])
        root_rows = inventory.get("root_carrier_files", [])
        recipe_rows = inventory.get("recipe_files", [])
        if {item.get("path") for item in app_closure_rows} != tracked_python_config_paths(app, app_pin):
            raise ValueError("app Python/config closure is incomplete")
        if {item.get("path") for item in root_rows} != tracked_python_config_paths(root, ROOT_PIN):
            raise ValueError("native producer ROOT Python/config closure is incomplete")
        recipe_expected = {"scripts/ci/ni07_14_tu_led1a_capture.py", ".github/workflows/ni07-14-tu-led1a.yml"}
        recipe_expected |= {name for name in git(recipe, "ls-tree", "-r", "--name-only", recipe_pin).splitlines()
                            if PurePosixPath(name).name in CONFIG_NAMES}
        if {item.get("path") for item in recipe_rows} != recipe_expected:
            raise ValueError("recipe Python/config/workflow readset is incomplete")
        app_closure = validate_pinned_paths(app, app_pin, app_closure_rows)
        root_paths = validate_pinned_paths(root, ROOT_PIN, root_rows)
        recipe_paths = validate_pinned_paths(recipe, recipe_pin, recipe_rows)
        status["app_python_config_paths"] = len(app_closure)
        status["root_carrier_python_config_paths"] = len(root_paths)
        status["recipe_source_paths"] = len(recipe_paths)
        if inventory.get("recipe_readset_path") != READSET_REL.as_posix():
            raise ValueError("recipe readset self-path does not match capture recipe")

        # Capture only a safe, named environment allowlist; never serialize ambient env/secrets.
        context = {
            "python": sys.version,
            "platform": platform.platform(),
            "install_command": os.environ.get("NI07_INSTALL_COMMAND", ""),
            "repositories": {"root_carrier": ROOT_PIN, "app": git(app, "rev-parse", "HEAD"),
                             "recipe": git(recipe, "rev-parse", "HEAD")},
            "environment": {key: os.environ.get(key) for key in (
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTHONDONTWRITEBYTECODE", "PYTHONPATH",
                "PYTHONUNBUFFERED", "NI07_ROOT_PIN", "NI07_APP_PIN", "NI07_INSTALL_COMMAND",
            )},
            "selection": SELECTION,
        }
        _write_exclusive(output_root / "context.json", (json.dumps(context, sort_keys=True, indent=2) + "\n").encode())
        freeze = subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"])
        _write_exclusive(output_root / "pip-freeze.txt", freeze)

        junit = output_root / "tu-led1a.junit.xml"
        if junit.exists() or native_output.exists():
            raise ValueError("native capture output already exists; refusing to reseal an earlier run")
        app_cwd = app
        pytest_command = [
            sys.executable, "-m", "pytest", "-o", "addopts=", "--noconftest",
            "-p", "no:cacheprovider", "-q", *SELECTION, f"--junitxml={junit}",
        ]
        producer = root / "scripts/ci/native_conformance.py"
        producer_argv = [
            sys.executable, str(producer), "--cwd", str(app_cwd), "--junit", str(junit),
            "--output", str(native_output), "--repo", f"root={root}",
            "--repo", f"recipe={recipe}", "--repo", f"orchestrator={app}",
        ]
        inputs = [inventory_path, capture_script, workflow_path, output_root / "context.json",
                  output_root / "pip-freeze.txt", *app_paths, *app_closure,
                  *root_paths, *recipe_paths]
        for path in inputs:
            producer_argv.extend(["--read-path", str(path.resolve())])
        for selection in SELECTION:
            producer_argv.extend(["--select", selection])
        status.update(state="running", selection=SELECTION)
        status_path.write_text(json.dumps(status, sort_keys=True, indent=2) + "\n")
        exit_code = subprocess.call([*producer_argv, "--", *pytest_command], cwd=app_cwd)
        status["exit_code"] = exit_code
        status["state"] = "passed" if exit_code == 0 else "failed"

        # Re-open the original through the existing shared reader; do not project or grade it.
        reader_path = producer
        spec = importlib.util.spec_from_file_location("ni07_native_conformance", reader_path)
        if spec is None or spec.loader is None:
            raise ValueError("cannot load pinned native receipt reader")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        receipt, receipt_sha = module.read_receipt(native_output / "receipt.json")
        status["receipt_sha256"] = receipt_sha
        status["fixture_execution_conformant"] = receipt["fixture_execution_conformant"]
        status["junit_counts"] = receipt.get("summary", {}).get("counts")
        if exit_code != 0 or receipt["fixture_execution_conformant"] is not True:
            status["state"] = "failed"
            status_path.write_text(json.dumps(status, sort_keys=True, indent=2) + "\n")
            return 1
        status_path.write_text(json.dumps(status, sort_keys=True, indent=2) + "\n")
        return 0
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1,
                      error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        if output_root.exists():
            status_path.write_text(json.dumps(status, sort_keys=True, indent=2) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
