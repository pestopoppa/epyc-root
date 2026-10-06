"""Capture one named synthetic prompt-builder module with native CI custody."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import platform
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
READSET_REL = Path("artifacts/ni07-19-tool-repair/ni07-19-tool-repair-readset.json")
SELECTION = ["tests/unit/test_prompt_builders.py"]
CONFIG_NAMES = {"pytest.ini", "setup.cfg", "tox.ini"}
CONFIG_SUFFIXES = {".ini", ".cfg", ".toml", ".yaml", ".yml"}


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def assert_clean_tracked(repo: Path, label: str) -> str:
    if git(repo, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError(f"{label} checkout has tracked changes")
    return git(repo, "rev-parse", "HEAD")


def source_path(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        path.suffix == ".py"
        or path.suffix in CONFIG_SUFFIXES
        or path.name in CONFIG_NAMES | {"pyproject.toml", "uv.lock"}
    )


def tracked_source_paths(repo: Path, pin: str) -> set[str]:
    names = git(repo, "ls-tree", "-r", "--name-only", pin).splitlines()
    return {name for name in names if source_path(name)}


def validate_source_rows(repo: Path, pin: str, rows: object, label: str) -> list[Path]:
    if not isinstance(rows, list):
        raise TypeError(f"{label} readset is not a path list")
    expected = tracked_source_paths(repo, pin)
    seen: set[str] = set()
    resolved: list[Path] = []
    for item in rows:
        if not isinstance(item, dict) or set(item) != {"path", "git_blob", "sha256"}:
            raise ValueError(f"malformed {label} source row")
        name = item["path"]
        if not isinstance(name, str):
            raise TypeError(f"{label} source path is not a string")
        rel = PurePosixPath(name)
        if (
            rel.is_absolute()
            or rel.as_posix() != name
            or any(part in {"", ".", ".."} for part in rel.parts)
        ):
            raise ValueError(f"{label} source path is not normalized and relative")
        if name in seen:
            raise ValueError(f"duplicate {label} source path: {name}")
        seen.add(name)
        data = (repo / name).read_bytes()
        blob = git(repo, "rev-parse", f"{pin}:{name}")
        if blob != item["git_blob"] or sha256(data) != item["sha256"]:
            raise ValueError(f"{label} source differs from pinned readset: {name}")
        resolved.append((repo / name).resolve())
    if seen != expected:
        raise ValueError(
            f"{label} readset does not cover its full tracked Python/config/lock closure"
        )
    return resolved


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, root, app = workspace / "recipe", workspace / "root", workspace / "app"
    output_root = temp / "ni07-19-tool-repair" / "result"
    status_path = output_root / "status.json"
    status: dict[str, object] = {
        "schema": "ni07-19-tool-repair-ci-status.v1",
        "state": "preparing",
        "exit_code": None,
    }
    try:
        if not output_root.is_dir() or {
            path.name for path in output_root.iterdir()
        } != {"status.json"}:
            raise ValueError(
                "capture output directory is missing or already contains prior artifacts"
            )
        recipe_pin = assert_clean_tracked(recipe, "recipe")
        root_pin = assert_clean_tracked(root, "ROOT carrier")
        app_pin = assert_clean_tracked(app, "APP")
        if recipe_pin != os.environ.get("GITHUB_SHA"):
            raise ValueError("recipe checkout differs from triggering GITHUB_SHA")
        if root_pin != ROOT_PIN or os.environ.get("NI07_ROOT_PIN") != ROOT_PIN:
            raise ValueError("ROOT checkout differs from the pinned native producer")
        if app_pin != os.environ.get("NI07_APP_PIN"):
            raise ValueError("APP checkout differs from the approved source candidate")

        readset_path = recipe / READSET_REL
        inventory = json.loads(readset_path.read_text(encoding="utf-8"))
        if inventory.get("schema") != "ni07-19-tool-repair-readset.v1":
            raise ValueError("unsupported source-readset schema")
        if inventory.get("selection") != SELECTION:
            raise ValueError("selected test module differs from the readset")
        if inventory.get("app_pin") != app_pin or inventory.get("root_pin") != ROOT_PIN:
            raise ValueError("readset APP/ROOT pins differ from checked-out sources")
        app_paths = validate_source_rows(
            app, app_pin, inventory.get("app_source_files"), "APP"
        )
        root_paths = validate_source_rows(
            root, root_pin, inventory.get("root_source_files"), "ROOT"
        )
        recipe_paths = validate_source_rows(
            recipe, recipe_pin, inventory.get("recipe_source_files"), "recipe"
        )
        for repo_name, expected in (
            ("epyc-orchestrator", "app"),
            ("epyc-root-carrier", "root"),
            ("epyc-root-recipe", "recipe"),
        ):
            if inventory.get("repositories", {}).get(repo_name) != expected:
                raise ValueError("source-readset repository mapping is inconsistent")

        # Keep only the named runtime context; ambient environment and credentials stay private.
        context_path = output_root / "context.json"
        freeze_path = output_root / "pip-freeze.txt"
        context = {
            "python": sys.version,
            "platform": platform.platform(),
            "install_command": os.environ.get("NI07_INSTALL_COMMAND", ""),
            "repositories": {
                "app": app_pin,
                "root_carrier": root_pin,
                "recipe": recipe_pin,
            },
            "selection": SELECTION,
            "environment": {
                key: os.environ.get(key)
                for key in (
                    "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
                    "PYTHONDONTWRITEBYTECODE",
                    "PYTHONPATH",
                    "PYTHONUNBUFFERED",
                    "NI07_APP_PIN",
                    "NI07_ROOT_PIN",
                    "NI07_INSTALL_COMMAND",
                )
            },
        }
        context_path.write_text(
            json.dumps(context, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        freeze = subprocess.check_output(
            [sys.executable, "-m", "pip", "freeze", "--all"]
        )
        freeze_path.write_bytes(freeze)

        junit_path = output_root / "prompt-builders.junit.xml"
        native_output = output_root / "native"
        if junit_path.exists() or native_output.exists():
            raise ValueError(
                "capture output already exists; refusing to overwrite a previous result"
            )
        pytest_argv = [
            sys.executable,
            "-m",
            "pytest",
            "-o",
            "addopts=",
            "--noconftest",
            "-p",
            "no:cacheprovider",
            "-q",
            *SELECTION,
            f"--junitxml={junit_path}",
        ]
        producer = root / "scripts/ci/native_conformance.py"
        producer_argv = [
            sys.executable,
            str(producer),
            "--cwd",
            str(app),
            "--junit",
            str(junit_path),
            "--output",
            str(native_output),
            "--repo",
            f"root={root}",
            "--repo",
            f"recipe={recipe}",
            "--repo",
            f"orchestrator={app}",
        ]
        inputs = [
            readset_path,
            *app_paths,
            *root_paths,
            *recipe_paths,
            context_path,
            freeze_path,
        ]
        for path in inputs:
            producer_argv.extend(["--read-path", str(path.resolve())])
        for selection in SELECTION:
            producer_argv.extend(["--select", selection])
        status.update(state="running", selection=SELECTION)
        status_path.write_text(
            json.dumps(status, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        exit_code = subprocess.call([*producer_argv, "--", *pytest_argv], cwd=app)
        status["exit_code"] = exit_code
        status["state"] = "passed" if exit_code == 0 else "failed"

        spec = importlib.util.spec_from_file_location(
            "ni07_native_conformance", producer
        )
        if spec is None or spec.loader is None:
            raise ValueError("cannot load the pinned native receipt reader")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        receipt, receipt_sha = module.read_receipt(native_output / "receipt.json")
        status["receipt_sha256"] = receipt_sha
        status["fixture_execution_conformant"] = receipt["fixture_execution_conformant"]
        status["junit_counts"] = receipt.get("summary", {}).get("counts")
        if exit_code != 0 or receipt["fixture_execution_conformant"] is not True:
            status["state"] = "failed"
            status_path.write_text(
                json.dumps(status, sort_keys=True, indent=2) + "\n", encoding="utf-8"
            )
            return 1
        status_path.write_text(
            json.dumps(status, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        return 0
    except Exception as exc:  # noqa: BLE001 - preserve capture diagnostics in status artifact
        status.update(
            state="capture_failed", exit_code=1, error=f"{type(exc).__name__}: {exc}"
        )
        return 1
    finally:
        if output_root.exists():
            status_path.write_text(
                json.dumps(status, sort_keys=True, indent=2) + "\n", encoding="utf-8"
            )


if __name__ == "__main__":
    raise SystemExit(main())
