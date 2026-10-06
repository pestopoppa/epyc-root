"""Capture the synthetic host activation core/hook regression modules with the native carrier."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT_CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
SOURCE_PIN = "f1311c1994a591def4dc6cbb967399fb3f24d17f"
WORKFLOW_PATH = ".github/workflows/host-activation-capture.yml"
CONFIG_NAMES = {
    "pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini", "uv.lock",
    "requirements.txt", "requirements-dev.txt", "requirements-test.txt", ".shellcheckrc", ".env",
}
FIXTURE_JSON_INPUTS = {"scripts/coordination/observer_registry.json"}
UNREAD_RUNTIME_ALIASES = {
    "coordination/session-bus/boundary_state.json",
    "coordination/session-bus/operator_escalation_state.json",
    "coordination/session-bus/scheduling_recommendation_state.json",
    "coordination/session-bus/stuck_state.json",
}
SELECTIONS = (
    "tests/vidya/test_host_supervision_activation.py", "tests/test_host_hygiene_tick.py",
)
EXPECTED_CASES = 81
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


def derive_git_manifest(repos: dict[str, Path]) -> tuple[dict, dict]:
    """Hash all tracked source/config classes before any result artifact access.

    Four unused live-state symlinks are bound as link blobs, never dereferenced.
    No selected fixture consumes their external targets.
    """
    extras = {
        "recipe": (WORKFLOW_PATH,),
        "carrier": ("scripts/ci/native_conformance.py",),
        "source": (),
    }
    manifest: dict[str, list[dict[str, str]]] = {}
    aliases: dict[str, list[dict[str, str]]] = {}
    for label, repo in repos.items():
        names = {name for name in git(repo, "ls-files", "-z").split("\0") if name}
        selected = {
            name for name in names
            if PurePosixPath(name).suffix in {".py", ".sh", ".yaml", ".yml", ".toml"}
            or PurePosixPath(name).name in CONFIG_NAMES or name in FIXTURE_JSON_INPUTS
        }
        selected.update(extras[label])
        selected.update(names & UNREAD_RUNTIME_ALIASES)
        entries = []
        alias_entries = []
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
            if (name in UNREAD_RUNTIME_ALIASES and len(mode_type_oid) == 3
                    and mode_type_oid[0] == "120000" and mode_type_oid[1] == "blob"):
                oid = mode_type_oid[2]
                data = subprocess.check_output(["git", "-C", str(repo), "cat-file", "blob", oid])
                if os.fsencode(os.readlink(repo / name)) != data:
                    raise RuntimeError(f"working alias differs from pinned link blob: {label}:{name}")
                alias_entries.append({"path": name, "mode": "120000", "git_blob": oid,
                                      "sha256": hashlib.sha256(data).hexdigest(),
                                      "link_target": os.fsdecode(data), "target_not_read": True})
                continue
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
        aliases[label] = alias_entries
    return manifest, aliases


def tool_context() -> dict:
    """Record actual external binaries; these are runner-asserted dependency facts."""
    tools = {}
    for name in ("bash", "awk", "date", "git", "grep", "sed", "sha256sum", "cat",
                 "mkdir", "sleep", "true", "du", "python3"):
        found = shutil.which(name)
        if not found:
            raise RuntimeError(f"required fixture tool is missing: {name}")
        resolved = Path(found).resolve(strict=True)
        data = resolved.read_bytes()
        tools[name] = {"path": found, "resolved": str(resolved),
                       "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    version = subprocess.check_output([tools["bash"]["path"], "--version"], text=True)
    tools["bash"]["version_output"] = version
    if Path(tools["python3"]["resolved"]) != Path(sys.executable).resolve():
        raise RuntimeError("shell python3 differs from the reviewed Python runtime")
    return tools


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
    result = runner_temp / "host-activation" / "result"
    status_path = result / "status.json"
    status: dict[str, object] = {
        "state": "preparing", "job": "host-activation-synthetic", "exit_code": None,
    }
    try:
        if os.environ.get("HOSTA_RUNNER_CONTEXT") != "ubuntu-latest":
            raise RuntimeError("runner context differs from reviewed recipe")
        if os.environ.get("HOSTA_EXECUTION_CONTEXT") != "offhost-synthetic-host-activation-tests":
            raise RuntimeError("execution context differs from reviewed recipe")
        if platform.python_version() != "3.13.15":
            raise RuntimeError(f"Python runtime differs from pin: {platform.python_version()}")
        if os.environ.get("HOSTA_INSTALL_COMMAND") != INSTALL_COMMAND:
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
        manifest, aliases = derive_git_manifest(repos)
        tools = tool_context()
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
            "runner_context": os.environ["HOSTA_RUNNER_CONTEXT"],
            "execution_context": os.environ["HOSTA_EXECUTION_CONTEXT"],
            "repositories": pins,
            "selections": list(SELECTIONS),
            "expected_case_count": EXPECTED_CASES,
            "install_command": INSTALL_COMMAND,
            "declared_dependencies": LOCKED_FIXTURE_PACKAGES,
            "git_path_blob_manifest": manifest,
            "unused_runtime_alias_bindings": aliases,
            "external_tool_context": tools,
            "readset_scope": (
                "All tracked Python/shell/YAML/TOML and named configs are bound. The only tracked "
                "JSON fixture input is scripts/coordination/observer_registry.json. Fixture registry/state/"
                "CPU-window/heartbeat/alarm/result JSON is created under hosted temporary directories. "
                "The native producer reads original runtime outputs captured in this bundle, not historical "
                "artifacts/* JSON. Shared grade imports Python only and consumes the new native receipt. "
                "Excluded tracked JSON histories and external live-state targets are not fixture read inputs."
            ),
            "git_path_counts": git_counts,
            "git_path_total": git_total,
            "runtime_contexts": runtime_contexts,
            "runtime_context_hashes": runtime_context_hashes,
            "isolation": (
                "Hosted synthetic core/hook conformance only. New module uses temporary canonical roots, "
                "fake Docker with inert pin handling and temporary crontab; no supervisor closure executes. "
                "Legacy tick controls create/reap owned temporary stand-ins and inspect ephemeral hosted /proc. "
                "Operational installation/heartbeat native rows remain dependency_evidence_only, ungraded. "
                "Only the outer existing fixture native receipt is projected/graded after capture. "
                "No production installer regression, host cron, kernel, model, server, inference, daemon "
                "handover or production cleanup executes. Four unused runtime aliases are Git/link-byte "
                "metadata; their external targets are not read. Runtime/tool context is runner-asserted."
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
        if passed:
            # ANALYSIS of the existing outer fixture receipt; native operational rows stay ungraded.
            originals = [*sorted(native.iterdir()), junit, freeze, environment]
            before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in originals}
            sys.path.insert(0, str(carrier))
            sys.path.insert(0, str(carrier / "scripts/vidya"))
            from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
            from claim_tuple import grade
            rows = native_rows(receipt_path)
            if len(rows) != 1:
                raise RuntimeError("outer original native receipt has no unique projection")
            claim = project_ci_conformance(rows[0])
            q, t, reasons = grade(claim)
            after = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in originals}
            if after != before:
                raise RuntimeError("outer shared-grade analysis changed an original")
            analysis = {
                "kind": "analysis_of_existing_outer_fixture_receipt",
                "receipt_file_sha256": before[str(receipt_path)],
                "receipt_self_sha256": receipt["receipt_sha256"],
                "measurement_id": claim.measurement_id, "metric": claim.metric,
                "value": claim.value, "claim": claim.claim, "source_kind": claim.source_kind,
                "binding_kind": claim.binding_kind, "grade": {"Q": q, "T": t, "reasons": reasons},
                "repositories": pins, "analysis_recipe": pins["recipe"],
                "native_original_hashes": before,
                "fixture_rerun": False, "operational_rows_graded": False,
                "new_native_receipt_authored_by_analysis": False,
            }
            with (result / "shared-grade.json").open("x") as out:
                json.dump(analysis, out, sort_keys=True, indent=2)
                out.write("\n")
            if (q, t) != ("Judged", "Located"):
                raise RuntimeError("outer fixture observation grade differs from reviewed expectation")
            status["shared_grade"] = analysis["grade"]
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
