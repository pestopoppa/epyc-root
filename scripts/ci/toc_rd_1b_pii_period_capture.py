"""Capture bounded synthetic perf-period scanner controls with native CI custody."""
from __future__ import annotations
import hashlib, json, os, platform, subprocess, sys
from pathlib import Path, PurePosixPath

ROOT_CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
SOURCE_PIN = "91cb89c588d0ac1c91d6e024aed0015c8c40643d"
WORKFLOW_PATH = ".github/workflows/toc-rd-1b-pii-period.yml"
CONFIG_NAMES = {"pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini", "uv.lock"}
SELECTIONS = (
    "scripts/hooks/tests/test_pii_staged_capture.py",
)
EXPECTED_CASES = 75
INSTALL_COMMAND = (
    "python -m pip install --require-hashes -r recipe/requirements-pii-capture.txt"
)

def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()

def require_clean(repo: Path, label: str) -> str:
    status = git(repo, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise RuntimeError(f"{label} checkout is not clean: {status}")
    return git(repo, "rev-parse", "HEAD")

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

def tracked_python_config(repo: Path) -> list[Path]:
    paths = []
    for name in git(repo, "ls-files", "-z").split("\0"):
        if not name:
            continue
        relative = PurePosixPath(name)
        if relative.suffix == ".py" or relative.name in CONFIG_NAMES:
            paths.append(regular_repo_file(repo, name))
    return paths

def derive_git_manifest(repos: dict[str, Path]) -> dict[str, list[dict[str, str]]]:
    """Hash the three exact Git closures before creating capture outputs."""
    extras = {
        "recipe": (WORKFLOW_PATH, "requirements-pii-capture.txt"),
        "carrier": ("scripts/ci/native_conformance.py",),
        "source": ("scripts/hooks/pii_precommit.sh",),
    }
    manifest: dict[str, list[dict[str, str]]] = {}
    for label, repo in repos.items():
        names = set(git(repo, "ls-files", "-z").split("\0"))
        selected = {name for name in names if name and (
            PurePosixPath(name).suffix == ".py" or PurePosixPath(name).name in CONFIG_NAMES
        )}
        selected.update(extras[label])
        entries = []
        for name in sorted(selected):
            if name not in names:
                raise RuntimeError(f"manifest path is not tracked in {label}: {name}")
            mode_type_oid = git(repo, "ls-tree", "HEAD", "--", name).split("\t", 1)[0].split()
            if len(mode_type_oid) != 3 or mode_type_oid[0] not in {"100644", "100755"} or mode_type_oid[1] != "blob":
                raise RuntimeError(f"manifest path is not a regular Git blob: {label}:{name}")
            blob = mode_type_oid[2]
            raw = subprocess.check_output(["git", "-C", str(repo), "cat-file", "blob", blob])
            entries.append({"path": name, "mode": mode_type_oid[0], "git_blob": blob,
                            "sha256": hashlib.sha256(raw).hexdigest()})
        manifest[label] = entries
    return manifest

def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, carrier, source = (workspace / n for n in ("recipe", "carrier", "source"))
    repos = {"recipe": recipe, "carrier": carrier, "source": source}
    result = runner_temp / "toc-rd-1b-pii-period" / "result"
    status_path = result / "status.json"
    status = {"state": "preparing", "job": "toc-rd-1b-pii-period-capture", "exit_code": None}
    try:
        if os.environ.get("TOCRD1B_RUNNER_CONTEXT") != "ubuntu-latest":
            raise RuntimeError("runner context differs from reviewed recipe")
        if os.environ.get("TOCRD1B_EXECUTION_CONTEXT") != "offhost-synthetic-staged-index-fixtures":
            raise RuntimeError("execution context differs from reviewed recipe")
        if platform.python_version() != "3.13.15":
            raise RuntimeError(f"Python runtime differs from pin: {platform.python_version()}")
        if os.environ.get("TOCRD1B_INSTALL_COMMAND") != INSTALL_COMMAND:
            raise RuntimeError("install command differs from reviewed recipe")
        if os.environ.get("ROOT_CARRIER_PIN") != ROOT_CARRIER_PIN or os.environ.get("SOURCE_PIN") != SOURCE_PIN:
            raise RuntimeError("workflow source/carrier pin differs from recipe-pinned SHA")
        expected = {"recipe": os.environ["GITHUB_SHA"], "carrier": ROOT_CARRIER_PIN, "source": SOURCE_PIN}
        pins = {}
        for label, repo in repos.items():
            pins[label] = require_clean(repo, label)
            if pins[label] != expected[label]:
                raise RuntimeError(f"{label} checkout differs from reviewed pin")
        if os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD") != "1":
            raise RuntimeError("pytest plugin autoload must remain disabled")
        if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
            raise RuntimeError("bytecode writes must remain disabled")

        git_manifest = derive_git_manifest(repos)
        result.mkdir(parents=True, exist_ok=True)
        existing = list(result.iterdir())
        if any(path != status_path for path in existing):
            raise RuntimeError("capture result directory already contains outputs")
        if status_path.is_symlink() or (status_path.exists() and not status_path.is_file()):
            raise RuntimeError("initial status artifact is not a regular file")
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
        freeze = result / "pip-freeze.txt"
        freeze.write_bytes(subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"]))
        environment = result / "environment.json"
        environment.write_text(json.dumps({
            "python": sys.version, "platform": platform.platform(),
            "runner_context": os.environ["TOCRD1B_RUNNER_CONTEXT"],
            "execution_context": os.environ["TOCRD1B_EXECUTION_CONTEXT"],
            "repositories": pins, "selections": list(SELECTIONS),
            "expected_case_count": EXPECTED_CASES, "install_command": INSTALL_COMMAND,
            "git_path_blob_manifest": git_manifest,
            "runtime_contexts": ["environment.json", "pip-freeze.txt"],
            "dependency_basis": "Pinned pytest 9.0.3 and exact runtime closure only; the selected ROOT hook fixtures use stdlib plus pytest.",
            "isolation": "Entire disposable-index PII capture suite (75 collected cases), including fabricated perf rows and synthetic secret controls; no historical prompt/PII source, production repo, APP, model, kernel, or inference calls.",
            "environment": {key: os.environ.get(key) for key in (
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTHONDONTWRITEBYTECODE", "PYTHONHASHSEED",
                "PYTHONPATH", "PYTHONUNBUFFERED", "TOCRD1B_EXECUTION_CONTEXT")},
        }, sort_keys=True, indent=2) + "\n", encoding="utf-8")

        junit, native = result / "original-junit.xml", result / "native"
        if junit.exists() or native.exists():
            raise RuntimeError("refusing to overwrite existing native capture outputs")
        read_paths = [freeze, environment, *(path for repo in repos.values() for path in tracked_python_config(repo))]
        read_paths.extend((recipe / WORKFLOW_PATH, recipe / "requirements-pii-capture.txt", source / "scripts/hooks/pii_precommit.sh"))
        producer = [sys.executable, str(carrier / "scripts/ci/native_conformance.py"),
                    "--cwd", str(source), "--junit", str(junit), "--output", str(native),
                    "--repo", f"recipe={recipe}", "--repo", f"carrier={carrier}", "--repo", f"source={source}"]
        for path in dict.fromkeys(p.resolve() for p in read_paths):
            producer.extend(("--read-path", str(path)))
        for selection in SELECTIONS:
            producer.extend(("--select", selection))
        command = [sys.executable, "-m", "pytest", "--noconftest", "-o", "addopts=",
                   "-p", "no:cacheprovider", "-q", *SELECTIONS, f"--junitxml={junit}"]
        status.update(state="running", repositories=pins, selections=list(SELECTIONS))
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
        code = subprocess.call([*producer, "--", *command], cwd=source)
        receipt_path = native / "receipt.json"
        if not receipt_path.is_file():
            status.update(state="capture_failed", exit_code=code or 1,
                          native_metric=None, diagnostic="native receipt was not produced")
            return code or 1
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        metric = receipt.get("fixture_execution_conformant")
        counts = (receipt.get("summary") or {}).get("counts") or {}
        case_gate = (counts.get("collected") == EXPECTED_CASES and counts.get("executed") == EXPECTED_CASES
                     and counts.get("skipped") == 0 and counts.get("failure") == 0 and counts.get("error") == 0)
        passed = code == 0 and metric is True and case_gate
        status.update(state="passed" if passed else "failed", exit_code=0 if passed else (code or 1),
                      native_metric=metric, junit_counts=counts, expected_case_count=EXPECTED_CASES,
                      all_cases_executed=case_gate)
        return 0 if passed else (code or 1)
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1, error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        if result.exists():
            status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")

if __name__ == "__main__":
    raise SystemExit(main())
