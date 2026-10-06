"""Capture bounded synthetic perf-period scanner controls with native CI custody."""
from __future__ import annotations
import hashlib, json, os, platform, re, subprocess, sys
from pathlib import Path, PurePosixPath

ROOT_CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
SOURCE_PIN = "89d669b2bc81b21a53295ab7640b045810d09081"
WORKFLOW_PATH = ".github/workflows/toc-rd-1b-pii-period.yml"
CASE_IDENTITIES_PATH = "scripts/ci/toc_rd_1b_expected_case_identities.json"
CONFIG_NAMES = {
    "pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini", "uv.lock",
    "Pipfile.lock", "poetry.lock", "requirements.txt",
}
TRACKED_RUNTIME_SUFFIXES = {".py", ".yaml", ".yml", ".toml", ".ini", ".cfg"}
SELECTIONS = (
    "scripts/hooks/tests/test_pii_staged_capture.py",
)
EXPECTED_CASES = 73
PINNED_WHEELS = {
    "iniconfig": ("2.3.0", "f631c04d2c48c52b84d0d0549c99ff3859c98df65b3101406327ecc7d53fbf12"),
    "packaging": ("26.0", "b36f1fef9334a5588b4166f8bcd26a14e521f2b55e6b9de3aaa80d3ff7a37529"),
    "pluggy": ("1.6.0", "e920276dd6813095e9377c0bc5566d94c932c33b27a3e3945d8389c374dd4746"),
    "pygments": ("2.20.0", "81a9e26dd42fd28a23a2d169d86d7ac03b46e2f8b59ed4698fb4785f946d0176"),
    "pytest": ("9.0.3", "2c5efc453d45394fdd706ade797c0a81091eccd1d6e4bccfcd476e2b8e0ab5d9"),
}
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


def is_runtime_input(name: str) -> bool:
    relative = PurePosixPath(name)
    return (relative.suffix in TRACKED_RUNTIME_SUFFIXES or relative.name in CONFIG_NAMES or
            (relative.name.startswith("requirements") and relative.suffix == ".txt"))


def tracked_runtime_inputs(repo: Path) -> list[Path]:
    paths = []
    for name in git(repo, "ls-files", "-z").split("\0"):
        if name and is_runtime_input(name):
            paths.append(regular_repo_file(repo, name))
    return paths

def verify_dependency_lock(requirements: Path, freeze: bytes) -> list[dict[str, str]]:
    lines = requirements.read_text(encoding="utf-8").splitlines()
    locked = {}
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if not line.endswith("\\") or index + 1 >= len(lines) or "==" not in line[:-1]:
            raise RuntimeError("requirements lock format differs from reviewed pins")
        name_raw, version = (part.strip() for part in line[:-1].split("==", 1))
        if not name_raw or not version:
            raise RuntimeError("requirements lock package pin is malformed")
        hash_match = re.fullmatch(r"--hash=sha256:([0-9a-f]{64})", lines[index + 1].strip())
        if not hash_match:
            raise RuntimeError("requirements lock lacks one reviewed SHA-256 per wheel")
        name = name_raw.lower().replace("_", "-")
        if name in locked:
            raise RuntimeError("duplicate package in requirements lock")
        locked[name] = (version, hash_match.group(1))
        index += 2
    if locked != PINNED_WHEELS:
        raise RuntimeError("requirements lock package/version/hash set differs from reviewed pins")
    installed = {}
    for line in freeze.decode("utf-8").splitlines():
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^=]+)", line.strip())
        if match:
            installed[match.group(1).lower().replace("_", "-")] = match.group(2)
    for name, (version, _) in PINNED_WHEELS.items():
        if installed.get(name) != version:
            raise RuntimeError(f"installed dependency differs from reviewed pin: {name}")
    return [{"name": name, "version": version, "sha256": digest}
            for name, (version, digest) in sorted(PINNED_WHEELS.items())]


def derive_git_manifest(repos: dict[str, Path]) -> dict[str, list[dict[str, str]]]:
    """Hash the three exact Git closures before creating capture outputs."""
    extras = {
        "recipe": (WORKFLOW_PATH, "requirements-pii-capture.txt", CASE_IDENTITIES_PATH),
        "carrier": ("scripts/ci/native_conformance.py",),
        "source": ("scripts/hooks/pii_precommit.sh",),
    }
    manifest: dict[str, list[dict[str, str]]] = {}
    for label, repo in repos.items():
        names = set(git(repo, "ls-files", "-z").split("\0"))
        selected = {name for name in names if name and is_runtime_input(name)}
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
        freeze_bytes = subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"])
        locked_dependencies = verify_dependency_lock(recipe / "requirements-pii-capture.txt", freeze_bytes)
        freeze.write_bytes(freeze_bytes)
        environment = result / "environment.json"
        environment.write_text(json.dumps({
            "python": sys.version, "platform": platform.platform(),
            "runner_context": os.environ["TOCRD1B_RUNNER_CONTEXT"],
            "execution_context": os.environ["TOCRD1B_EXECUTION_CONTEXT"],
            "repositories": pins, "selections": list(SELECTIONS),
            "expected_case_count": EXPECTED_CASES, "install_command": INSTALL_COMMAND,
            "locked_dependencies": locked_dependencies,
            "expected_case_identity_file": CASE_IDENTITIES_PATH,
            "git_path_blob_manifest": git_manifest,
            "runtime_contexts": ["environment.json", "pip-freeze.txt"],
            "dependency_basis": "Full test file plus selected CLI and shared-grade import paths are source-bound in the immutable Git map. Imports use pytest and stdlib only; no YAML parser is imported on this path. The five wheel pins and hashes are checked against the requirements lock, and installed versions are checked against pip freeze.",
            "isolation": "Entire disposable-index PII capture suite (73 collected cases), including fabricated perf rows and synthetic secret controls; no historical prompt/PII source, production repo, APP, model, kernel, or inference calls.",
            "environment": {key: os.environ.get(key) for key in (
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTHONDONTWRITEBYTECODE", "PYTHONHASHSEED",
                "PYTHONPATH", "PYTHONUNBUFFERED", "TOCRD1B_EXECUTION_CONTEXT")},
        }, sort_keys=True, indent=2) + "\n", encoding="utf-8")

        junit, native = result / "original-junit.xml", result / "native"
        if junit.exists() or native.exists():
            raise RuntimeError("refusing to overwrite existing native capture outputs")
        read_paths = [freeze, environment, *(path for repo in repos.values() for path in tracked_runtime_inputs(repo))]
        read_paths.extend((recipe / WORKFLOW_PATH, recipe / "requirements-pii-capture.txt",
                           recipe / CASE_IDENTITIES_PATH, source / "scripts/hooks/pii_precommit.sh"))
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
        summary = receipt.get("summary") or {}
        counts = summary.get("counts") or {}
        expected_doc = json.loads((recipe / CASE_IDENTITIES_PATH).read_text(encoding="utf-8"))
        test_path = regular_repo_file(source, SELECTIONS[0])
        source_test_sha = hashlib.sha256(test_path.read_bytes()).hexdigest()
        expected_pairs = [(row["classname"], row["name"])
                          for row in expected_doc.get("case_identities", [])]
        actual_cases = summary.get("cases") or []
        actual_pairs = [(row.get("classname"), row.get("name")) for row in actual_cases]
        identity_gate = (
            expected_doc.get("schema") == "tocrd1b-junit-identities-v1"
            and expected_doc.get("source_path") == SELECTIONS[0]
            and expected_doc.get("source_sha256") == source_test_sha
            and expected_doc.get("expected_case_count") == EXPECTED_CASES
            and len(expected_pairs) == EXPECTED_CASES
            and len(set(expected_pairs)) == EXPECTED_CASES
            and len(actual_pairs) == EXPECTED_CASES
            and len(set(actual_pairs)) == EXPECTED_CASES
            and set(actual_pairs) == set(expected_pairs)
        )
        case_gate = (identity_gate and counts.get("collected") == EXPECTED_CASES
                     and counts.get("executed") == EXPECTED_CASES
                     and counts.get("skipped") == 0 and counts.get("failure") == 0
                     and counts.get("error") == 0)
        # Re-open and grade the ORIGINAL native receipt through the existing
        # ci_conformance adapter. This is analysis only; it cannot author a
        # receipt or alter the native result.
        originals = [*sorted(path for path in native.rglob("*") if path.is_file()), junit, freeze, environment]
        before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in originals}
        sys.path.insert(0, str(carrier))
        sys.path.insert(0, str(carrier / "scripts" / "vidya"))
        from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
        from claim_tuple import grade
        rows = native_rows(receipt_path)
        analysis = {
            "kind": "analysis_of_existing_fixture_receipt",
            "native_original_hashes": before,
            "repositories": pins,
            "fixture_rerun": False,
            "new_native_receipt_authored_by_analysis": False,
            "metric": metric,
            "case_counts": counts,
            "grade": None,
        }
        if len(rows) != 1:
            raise RuntimeError("expected exactly one original ci_conformance row")
        claim = project_ci_conformance(rows[0])
        q, t, reasons = grade(claim)
        analysis.update(measurement_id=claim.measurement_id, source_kind=claim.source_kind,
                        binding_kind=claim.binding_kind,
                        grade={"Q": q, "T": t, "reasons": reasons})
        if (q, t) != ("Judged", "Located"):
            raise RuntimeError("original fixture receipt shared grade differs from reviewed expectation")
        after = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in originals}
        if after != before:
            raise RuntimeError("shared-grade analysis changed an original receipt or context")
        with (result / "shared-grade.json").open("x", encoding="utf-8") as handle:
            json.dump(analysis, handle, indent=2, sort_keys=True)
            handle.write("\n")
        passed = code == 0 and metric is True and case_gate
        status.update(state="passed" if passed else "failed", exit_code=0 if passed else (code or 1),
                      native_metric=metric, junit_counts=counts, expected_case_count=EXPECTED_CASES,
                      all_cases_executed=case_gate, exact_case_identities=identity_gate)
        return 0 if passed else (code or 1)
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1, error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        if result.exists():
            status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")

if __name__ == "__main__":
    raise SystemExit(main())
