"""Capture the synthetic declared-root KEEP-marker regression module with the native carrier."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT_CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
SOURCE_PIN = "7f1aa593dd2ea23aceaa9d1b2d3c78b38d4dd906"
WORKFLOW_PATH = ".github/workflows/ni07-32-root-keep-capture.yml"
CONFIG_NAMES = {
    "pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini", "uv.lock",
    "requirements.txt", "requirements-dev.txt", "requirements-test.txt",
}
SELECTIONS = ("tests/test_scratch_cleanup.py",)
EXPECTED_CASES = 27
LOCKED_FIXTURE_PACKAGES = {
    "pytest": "9.0.3",
    "iniconfig": "2.3.0",
    "packaging": "26.0",
    "pluggy": "1.6.0",
    "Pygments": "2.20.0",
}
INSTALL_COMMAND = (
    "python -m pip install pytest==9.0.3 iniconfig==2.3.0 packaging==26.0 "
    "pluggy==1.6.0 Pygments==2.20.0"
)


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def require_clean(repo: Path, label: str, expected: str) -> str:
    status = git(repo, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise RuntimeError(f"{label} checkout is not clean: {status}")
    actual = git(repo, "rev-parse", "HEAD")
    if actual != expected:
        raise RuntimeError(f"{label} checkout is {actual}, expected {expected}")
    return actual


def regular_repo_file(repo: Path, name: str) -> Path:
    path = repo
    if path.is_symlink():
        raise RuntimeError(f"repository checkout is a symlink: {repo}")
    for part in Path(name).parts:
        path = path / part
        if path.is_symlink():
            raise RuntimeError(f"declared read traverses a symlink: {name}")
    if not path.is_file():
        raise RuntimeError(f"declared read is missing or not a regular file: {name}")
    return path.absolute()


def derive_git_manifest(repos: dict[str, Path]) -> dict[str, list[dict[str, str]]]:
    """Hash tracked Python/config bytes plus the explicit workflow before receipt creation."""
    extras = {
        "recipe": (WORKFLOW_PATH,),
        "carrier": ("scripts/ci/native_conformance.py",),
        "source": (),
    }
    manifest: dict[str, list[dict[str, str]]] = {}
    for label, repo in repos.items():
        names = {name for name in git(repo, "ls-files", "-z").split("\0") if name}
        selected = {
            name for name in names
            if PurePosixPath(name).suffix == ".py" or PurePosixPath(name).name in CONFIG_NAMES
        }
        selected.update(extras[label])
        entries = []
        for name in sorted(selected):
            if name not in names:
                raise RuntimeError(f"manifest path is not tracked in {label}: {name}")
            record = subprocess.check_output(
                ["git", "-C", str(repo), "ls-tree", "-z", "HEAD", "--", name]
            )
            rows = [row for row in record.split(b"\0") if row]
            if len(rows) != 1 or b"\t" not in rows[0]:
                raise RuntimeError(f"expected one tree entry for {label}:{name}")
            metadata, raw_name = rows[0].split(b"\t", 1)
            mode_type_oid = metadata.decode("ascii").split()
            if (raw_name.decode("utf-8") != name or len(mode_type_oid) != 3
                    or mode_type_oid[0] not in {"100644", "100755"}
                    or mode_type_oid[1] != "blob"):
                raise RuntimeError(f"manifest path is not a regular Git blob: {label}:{name}")
            oid = mode_type_oid[2]
            git_bytes = subprocess.check_output(["git", "-C", str(repo), "cat-file", "blob", oid])
            working_bytes = regular_repo_file(repo, name).read_bytes()
            sha256 = hashlib.sha256(git_bytes).hexdigest()
            if hashlib.sha256(working_bytes).hexdigest() != sha256:
                raise RuntimeError(f"working file differs from pinned Git blob: {label}:{name}")
            entries.append({"path": name, "mode": mode_type_oid[0], "git_blob": oid,
                            "sha256": sha256})
        manifest[label] = entries
    return manifest


def verify_packages() -> None:
    for name, expected in LOCKED_FIXTURE_PACKAGES.items():
        actual = importlib.metadata.version(name)
        if actual != expected:
            raise RuntimeError(f"{name} is {actual}, expected {expected}")


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, carrier, source = (workspace / name for name in ("recipe", "carrier", "source"))
    repos = {"recipe": recipe, "carrier": carrier, "source": source}
    result = runner_temp / "ni07-32-root-keep" / "result"
    status_path = result / "status.json"
    status: dict[str, object] = {
        "state": "preparing", "job": "root-keep-synthetic", "exit_code": None,
    }
    try:
        if os.environ.get("NI32_RUNNER_CONTEXT") != "ubuntu-latest":
            raise RuntimeError("runner context differs from reviewed recipe")
        if os.environ.get("NI32_EXECUTION_CONTEXT") != "offhost-synthetic-root-cleanup-tests":
            raise RuntimeError("execution context differs from reviewed recipe")
        if platform.python_version() != "3.13.15":
            raise RuntimeError(f"Python runtime differs from pin: {platform.python_version()}")
        if os.environ.get("NI32_INSTALL_COMMAND") != INSTALL_COMMAND:
            raise RuntimeError("install command differs from reviewed recipe")
        for name, value in {
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONUNBUFFERED": "1",
        }.items():
            if os.environ.get(name) != value:
                raise RuntimeError(f"{name} differs from reviewed recipe")
        if os.environ.get("PYTEST_ADDOPTS", ""):
            raise RuntimeError("ambient PYTEST_ADDOPTS must be empty")
        if os.environ.get("ROOT_CARRIER_PIN") != ROOT_CARRIER_PIN:
            raise RuntimeError("workflow carrier pin differs from recipe")
        if os.environ.get("SOURCE_PIN") != SOURCE_PIN:
            raise RuntimeError("workflow source pin differs from recipe")
        expected = {
            "recipe": os.environ["GITHUB_SHA"],
            "carrier": ROOT_CARRIER_PIN,
            "source": SOURCE_PIN,
        }
        pins = {name: require_clean(path, name, expected[name]) for name, path in repos.items()}
        verify_packages()

        # This source-first Git manifest is computed before local capture outputs are opened.
        manifest = derive_git_manifest(repos)
        git_counts = {name: len(rows) for name, rows in manifest.items()}
        git_total = sum(git_counts.values())

        result.mkdir(parents=True, exist_ok=True)
        existing = list(result.iterdir())
        if any(path != status_path for path in existing):
            raise RuntimeError("capture result directory already contains outputs")
        if status_path.is_symlink() or (status_path.exists() and not status_path.is_file()):
            raise RuntimeError("initial status artifact is not a regular file")
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")

        freeze = result / "pip-freeze.txt"
        freeze_bytes = subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"])
        freeze.write_bytes(freeze_bytes)
        environment = result / "environment.json"
        runtime_contexts = ["environment.json", "pip-freeze.txt"]
        runtime_context_hashes = {"pip-freeze.txt": hashlib.sha256(freeze_bytes).hexdigest()}
        environment_data = {
            "python": sys.version,
            "platform": platform.platform(),
            "runner_context": os.environ["NI32_RUNNER_CONTEXT"],
            "execution_context": os.environ["NI32_EXECUTION_CONTEXT"],
            "repositories": pins,
            "selections": list(SELECTIONS),
            "expected_case_count": EXPECTED_CASES,
            "install_command": INSTALL_COMMAND,
            "declared_dependencies": LOCKED_FIXTURE_PACKAGES,
            "git_path_blob_manifest": manifest,
            "git_path_counts": git_counts,
            "git_path_total": git_total,
            "runtime_contexts": runtime_contexts,
            "runtime_context_hashes": runtime_context_hashes,
            "isolation": (
                "The selected ROOT-only test module uses temporary directories and temporary local bare Git repos; "
                "all Git clones, pushes, fetches and worktree removals target those temporary repos. A legacy "
                "busy-path test creates one temporary sleep process, reads the ephemeral GitHub runner's /proc "
                "to identify it, then kills and reaps it in finally. Fake guarded_rm scripts act only on temp paths. "
                "No APP, external network service, model, kernel, server, inference or production cleanup is invoked. "
                "This hosted fixture run is not evidence about production host processes or cleanup safety beyond "
                "the selected deterministic source cases."
            ),
        }
        environment_bytes = (json.dumps(environment_data, sort_keys=True, indent=2) + "\n").encode()
        environment.write_bytes(environment_bytes)
        read_paths = []
        for label, repo in repos.items():
            read_paths.extend(regular_repo_file(repo, item["path"]) for item in manifest[label])
        read_paths.extend((freeze, environment))
        junit = result / "original-junit.xml"
        native = result / "native"
        if junit.exists() or native.exists():
            raise RuntimeError("refusing to overwrite existing native capture outputs")
        producer = [
            sys.executable, str(carrier / "scripts/ci/native_conformance.py"),
            "--cwd", str(source), "--junit", str(junit), "--output", str(native),
            "--repo", f"recipe={recipe}", "--repo", f"carrier={carrier}", "--repo", f"source={source}",
        ]
        for path in dict.fromkeys(p.resolve() for p in read_paths):
            producer.extend(("--read-path", str(path)))
        for selection in SELECTIONS:
            producer.extend(("--select", selection))
        command = [
            sys.executable, "-m", "pytest", "--noconftest", "-o", "addopts=",
            "-p", "no:cacheprovider", "-q", *SELECTIONS, f"--junitxml={junit}",
        ]
        status.update(state="running", repositories=pins, git_path_counts=git_counts,
                      runtime_contexts=runtime_contexts, selected_nodes=len(SELECTIONS),
                      expected_case_count=EXPECTED_CASES)
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
        code = subprocess.call([*producer, "--", *command], cwd=source)
        receipt_path = native / "receipt.json"
        if not receipt_path.is_file():
            status.update(state="capture_failed", exit_code=code or 1,
                          native_metric=None, diagnostic="native receipt was not produced")
            return code or 1
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        counts = (receipt.get("summary") or {}).get("counts") or {}
        passed = (
            code == 0
            and receipt.get("fixture_execution_conformant") is True
            and counts.get("collected") == EXPECTED_CASES
            and counts.get("executed") == EXPECTED_CASES
            and counts.get("passed") == EXPECTED_CASES
            and counts.get("failure") == 0
            and counts.get("error") == 0
            and counts.get("skipped") == 0
        )
        status.update(state="passed" if passed else "failed", exit_code=0 if passed else (code or 1),
                      native_metric=receipt.get("fixture_execution_conformant"),
                      junit_counts=counts, expected_case_count=EXPECTED_CASES,
                      all_cases_executed=counts.get("executed") == EXPECTED_CASES)
        return 0 if passed else (code or 1)
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1,
                      error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        if status_path.parent.exists():
            status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
