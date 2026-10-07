"""Capture scoped AP60 offline fixtures through the unchanged native carrier."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET

APP_PIN = "a4132e57c96edb78088dedcfb7eb315497ef28db"
CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
PACKAGES = {
    "annotated-doc": "0.0.4", "annotated-types": "0.7.0", "anyio": "4.13.0",
    "attrs": "26.1.0", "certifi": "2026.2.25", "charset-normalizer": "3.4.7",
    "faiss-cpu": "1.13.2", "fastapi": "0.135.3", "h11": "0.16.0",
    "httpcore": "1.0.9", "httpx": "0.28.1", "idna": "3.11",
    "iniconfig": "2.3.0", "jsonpatch": "1.33", "jsonpointer": "3.1.1",
    "jsonschema": "4.26.0", "jsonschema-specifications": "2025.9.1",
    "langchain-core": "1.2.28", "langgraph": "1.1.6",
    "langgraph-checkpoint": "4.0.1", "langgraph-prebuilt": "1.0.9",
    "langgraph-sdk": "0.3.13", "langsmith": "0.7.30", "logfire-api": "4.32.0",
    "numpy": "2.4.4", "orjson": "3.11.8", "ormsgpack": "1.12.2",
    "packaging": "26.0", "pluggy": "1.6.0", "pydantic": "2.13.0",
    "pydantic-core": "2.46.0", "pydantic-graph": "1.80.0", "pygments": "2.20.0",
    "pytest": "9.0.3", "pyyaml": "6.0.3", "python-multipart": "0.0.26",
    "referencing": "0.37.0",
    "requests": "2.33.1", "requests-toolbelt": "1.0.0", "rpds-py": "0.30.0",
    "scipy": "1.17.1", "starlette": "1.0.0", "tenacity": "9.1.4",
    "typing-extensions": "4.15.0", "typing-inspection": "0.4.2",
    "urllib3": "2.6.3", "uuid-utils": "0.14.1", "xxhash": "3.6.0",
    "zstandard": "0.25.0",
}
INSTALL_REQUIREMENTS = "scripts/ci/ap60_requirements.txt"
INSTALL = (
    'python -m venv "$RUNNER_TEMP/ap60-instance-settings/venv" && '
    '"$RUNNER_TEMP/ap60-instance-settings/venv/bin/python" -m pip install '
    "--require-hashes --no-deps --only-binary=:all: -r recipe/scripts/ci/ap60_requirements.txt"
)
CONFIG_NAMES = {"pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini", "uv.lock",
                "requirements.txt", "requirements-dev.txt", "requirements-test.txt"}
APP_CONFIG_EXTRAS = (
    "orchestration/model_registry.yaml",
    "orchestration/model_descriptors.yaml",
    "orchestration/derived/stack_priors.yaml",
    "orchestration/derived/duration_baselines_by_role.json",
    "orchestration/workload_model.yaml",
)
ROOT_TASK = "handoffs/active/autopilot-continuous-optimization.md"
ROOT_TASK_SHA256 = "bd8ef4bbf4b90fbcf211986de11b804f0e59a1ff13c4a9d86631524c8f822c16"
ROOT_VB_TABLE = "scripts/vidya/adapters/README.md"
ROOT_VB_TABLE_SHA256 = "139ef409529f02b987dcd4dbd850320d415ee073de1fd9aba9bdf444464b67e1"
TEST_FILES = (
    "tests/unit/test_q_td_write_path.py",
    "tests/unit/test_episodic_work_payload.py",
    "tests/unit/test_q_scorer_update_path_preserves_work.py",
    "tests/unit/test_q_scorer.py",
)


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def regular_file(repo: Path, relative: str) -> Path:
    path = repo
    for part in Path(relative).parts:
        path = path / part
        if path.is_symlink():
            raise RuntimeError(f"declared input traverses symlink: {relative}")
    if not path.is_file():
        raise RuntimeError(f"declared input missing or nonregular: {relative}")
    return path.absolute()


def tracked_sources(repo: Path) -> list[Path]:
    result = []
    for name in git(repo, "ls-files", "-z").split("\0"):
        if not name:
            continue
        rel = PurePosixPath(name)
        if rel.suffix == ".py" or rel.name in CONFIG_NAMES:
            result.append(regular_file(repo, name))
    return result


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, carrier, app = (workspace / n for n in ("recipe", "carrier", "app"))
    result = temp / "ap60-instance-settings" / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status = {"state": "preparing", "exit_code": None}
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n")
    try:
        if os.environ.get("AP60_RUNNER_CONTEXT") != "ubuntu-24.04":
            raise RuntimeError("runner context differs from reviewed recipe")
        if os.environ.get("AP60_EXECUTION_CONTEXT") != "offline-qscorer-fixtures-temp-sqlite-faiss":
            raise RuntimeError("execution context differs from reviewed recipe")
        if os.environ.get("AP60_INSTALL_COMMAND") != INSTALL:
            raise RuntimeError("install command differs from reviewed recipe")
        if platform.python_version() != "3.13.15":
            raise RuntimeError(f"Python runtime differs from pin: {platform.python_version()}")
        expected_venv = (Path(os.environ["RUNNER_TEMP"]) / "ap60-instance-settings" / "venv").resolve()
        if sys.prefix == sys.base_prefix or Path(sys.prefix).resolve() != expected_venv:
            raise RuntimeError("capture interpreter is not the reviewed isolated venv")
        pins = {"recipe": git(recipe, "rev-parse", "HEAD"),
                "carrier": git(carrier, "rev-parse", "HEAD"),
                "app": git(app, "rev-parse", "HEAD")}
        expected = {"recipe": os.environ["GITHUB_SHA"], "carrier": CARRIER_PIN, "app": APP_PIN}
        for key, repo in (("recipe", recipe), ("carrier", carrier), ("app", app)):
            if pins[key] != expected[key]:
                raise RuntimeError(f"{key} checkout differs from exact pin")
            if git(repo, "status", "--porcelain", "--untracked-files=all"):
                raise RuntimeError(f"{key} checkout is not clean")
        if os.environ.get("APP_PIN") != APP_PIN or os.environ.get("ROOT_CARRIER_PIN") != CARRIER_PIN:
            raise RuntimeError("workflow source or carrier pin differs")
        lock = tomllib.loads(regular_file(app, "uv.lock").read_text(encoding="utf-8"))
        locked = {p["name"].lower(): p for p in lock["package"]}
        requirements_path = regular_file(recipe, INSTALL_REQUIREMENTS)
        requirements_text = requirements_path.read_text(encoding="utf-8")
        requirement_versions = dict(re.findall(
            r"(?m)^([A-Za-z0-9_.-]+)==([^\s]+)", requirements_text
        ))
        normalized_requirements = {name.lower().replace("_", "-"): version
                                   for name, version in requirement_versions.items()}
        if normalized_requirements != PACKAGES:
            raise RuntimeError("requirements package/version set differs from the 49-package APP closure")
        declared_wheels = {}
        current_package = None
        for line in requirements_text.splitlines():
            stripped = line.strip()
            match = re.match(r"^([A-Za-z0-9_.-]+)==", stripped)
            if match:
                current_package = match.group(1).lower().replace("_", "-")
                declared_wheels[current_package] = set()
            if current_package is not None:
                declared_wheels[current_package].update(
                    re.findall(r"--hash=sha256:([0-9a-f]{64})", stripped)
                )
        expected_wheels = {}
        for name, version in PACKAGES.items():
            record = locked.get(name.lower())
            if not record or record["version"] != version:
                raise RuntimeError(f"{name} version differs from APP uv.lock")
            wheel_hashes = {
                wheel["hash"].removeprefix("sha256:")
                for wheel in record.get("wheels", [])
            }
            if not wheel_hashes:
                raise RuntimeError(f"{name} has no wheel in APP uv.lock")
            expected_wheels[name] = wheel_hashes
            for wheel_hash in wheel_hashes:
                if f"--hash=sha256:{wheel_hash}" not in requirements_text:
                    raise RuntimeError(f"hash-locked requirements omit a locked wheel for {name}")
            if importlib.metadata.version(name) != version:
                raise RuntimeError(f"installed {name} differs from reviewed pin")
        if declared_wheels != expected_wheels:
            raise RuntimeError("requirements wheel hashes differ from the exact APP-locked per-package wheel set")

        manifest_path = regular_file(recipe, "scripts/ci/ap60_expected_cases.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("source_commit") != APP_PIN or manifest.get("count") != 115:
            raise RuntimeError("expected-case manifest pin/count differs")
        cases = manifest["cases"]
        if len(cases) != 115 or len({(c["path"], c.get("class", ""), c["name"]) for c in cases}) != 115:
            raise RuntimeError("expected-case manifest is incomplete or duplicated")
        selections = []
        expected_junit = set()
        for case in cases:
            module = case["path"][:-3].replace("/", ".")
            cls = case.get("class")
            selections.append(f"{case['path']}::{cls + '::' if cls else ''}{case['name']}")
            expected_junit.add((f"{module}.{cls}" if cls else module, case["name"]))

        freeze = result / "pip-freeze.txt"
        freeze.write_bytes(subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"]))
        install_log = regular_file(result, "dependency-install.log")
        environment = result / "environment.json"
        environment.write_text(json.dumps({
            "python": sys.version, "platform": platform.platform(), "repositories": pins,
            "runner_context": os.environ["AP60_RUNNER_CONTEXT"],
            "execution_context": os.environ["AP60_EXECUTION_CONTEXT"],
            "selection_count": len(selections), "selections": selections,
            "expected_case_count": 115, "expected_case_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "install_command": INSTALL, "requirements_path": INSTALL_REQUIREMENTS,
            "requirements_sha256": hashlib.sha256(requirements_path.read_bytes()).hexdigest(),
            "dependency_install_log_sha256": hashlib.sha256(install_log.read_bytes()).hexdigest(),
            "declared_dependencies": PACKAGES,
            "dependency_basis": "49-package Linux/Python 3.13.15 closure from the pinned APP uv.lock; module-scope transitive closure includes the eager src.api.routes package tree (388 local APP modules, including telemetry), plus exercised lazy imports for FAISS, YAML priors, and pytest. All wheels are hash-locked, installed with --no-deps --only-binary=:all:, and the native readset binds requirements, uv.lock, pip-freeze, and dependency-install.log. No model-serving or ONNX runtime package is installed.",
            "runtime_data_inputs": list(APP_CONFIG_EXTRAS),
            "root_task_source": {"path": ROOT_TASK, "sha256": ROOT_TASK_SHA256},
            "root_vb_source_table": {"path": ROOT_VB_TABLE, "sha256": ROOT_VB_TABLE_SHA256},
            "isolation": "Selected tests use deterministic fake embedders and temporary SQLite/FAISS stores. ReplayEngine.__new__ compatibility is statically reviewed: its path calls _compute_reward and does not read newly snapshotted write flags. No model, ONNX, endpoint, GPU, serving process, corpus store, or inference is invoked.",
            "pytest_environment": {k: os.environ.get(k) for k in ("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTHONDONTWRITEBYTECODE", "PYTHONHASHSEED", "PYTHONPATH", "PYTHONUNBUFFERED")}
        }, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        junit, native = result / "original-junit.xml", result / "native"
        if junit.exists() or native.exists():
            raise RuntimeError("refusing to overwrite capture outputs")
        workflow = regular_file(recipe, ".github/workflows/ap60-instance-settings-capture.yml")
        root_task = regular_file(recipe, ROOT_TASK)
        root_vb_table = regular_file(recipe, ROOT_VB_TABLE)
        if hashlib.sha256(root_task.read_bytes()).hexdigest() != ROOT_TASK_SHA256:
            raise RuntimeError("ROOT AP60 task bytes differ from the reviewed pin")
        if hashlib.sha256(root_vb_table.read_bytes()).hexdigest() != ROOT_VB_TABLE_SHA256:
            raise RuntimeError("ROOT AP60 source-table bytes differ from the reviewed pin")
        app_config_paths = [regular_file(app, name) for name in APP_CONFIG_EXTRAS]
        for relative in APP_CONFIG_EXTRAS:
            mode = git(app, "ls-tree", "HEAD", "--", relative).split(maxsplit=1)
            if not mode or mode[0] != "100644":
                raise RuntimeError(f"APP runtime data is not a tracked regular file: {relative}")
        read_paths = [workflow, manifest_path, requirements_path, install_log, freeze, environment, root_task, root_vb_table, *app_config_paths,
                      *tracked_sources(recipe), *tracked_sources(carrier), *tracked_sources(app)]
        command = [sys.executable, "-m", "pytest", "--noconftest", "-o", "addopts=",
                   "-p", "no:cacheprovider", "-q", *selections, f"--junitxml={junit}"]
        producer = [sys.executable, str(carrier / "scripts/ci/native_conformance.py"),
                    "--cwd", str(app), "--junit", str(junit), "--output", str(native),
                    "--repo", f"recipe={recipe}", "--repo", f"carrier={carrier}", "--repo", f"app={app}"]
        for path in dict.fromkeys(p.resolve() for p in read_paths):
            producer.extend(("--read-path", str(path)))
        for selection in TEST_FILES:
            producer.extend(("--select", selection))
        status.update(state="running", repositories=pins, selection_count=len(selections))
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n")
        exit_code = subprocess.call([*producer, "--", *command], cwd=app)
        if not junit.is_file() or not (native / "receipt.json").is_file():
            status.update(state="capture_failed", exit_code=exit_code or 1, diagnostic="missing original JUnit or native receipt")
            return exit_code or 1
        root = ET.parse(junit).getroot()
        observed = [(item.get("classname", ""), item.get("name", "")) for item in root.iter("testcase")]
        counts = {"collected": len(observed), "unique": len(set(observed)),
                  "expected": len(expected_junit), "missing": sorted(expected_junit - set(observed)),
                  "unexpected": sorted(set(observed) - expected_junit)}
        receipt_path = native / "receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        summary = receipt.get("summary")
        native_counts = (summary or {}).get("counts") or {}
        original_files = [p for p in native.rglob("*") if p.is_file()] + [junit, freeze, environment, install_log, requirements_path]
        before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in original_files}
        sys.path.insert(0, str(carrier))
        sys.path.insert(0, str(carrier / "scripts/vidya"))
        from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
        from claim_tuple import grade
        rows = native_rows(receipt_path)
        if len(rows) != 1:
            raise RuntimeError("native receipt projection is not exactly one row")
        claim = project_ci_conformance(rows[0])
        quality, time_grade, reasons = grade(claim)
        grade_record = {"measurement_id": claim.measurement_id, "source_kind": claim.source_kind,
                        "binding_kind": claim.binding_kind, "Q": quality, "T": time_grade,
                        "reasons": reasons, "interpretation": "shared carrier grade only; fixture conformance is not product or scientific evidence"}
        if (quality, time_grade) != ("Judged", "Located"):
            raise RuntimeError("shared carrier grade differs from accepted fixture expectation")
        after = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in original_files}
        if after != before:
            raise RuntimeError("shared-grade projection changed an original artifact")
        grade_record["original_before_sha256"] = before
        grade_record["original_after_sha256"] = after
        with (result / "shared-grade.json").open("x", encoding="utf-8") as handle:
            json.dump(grade_record, handle, sort_keys=True, indent=2)
            handle.write("\n")
        all_pass = (exit_code == 0 and counts["collected"] == 115 and counts["unique"] == 115
                    and not counts["missing"] and not counts["unexpected"]
                    and native_counts.get("collected") == 115 and native_counts.get("executed") == 115
                    and native_counts.get("skipped") == 0 and native_counts.get("failure") == 0
                    and native_counts.get("error") == 0
                    and receipt.get("fixture_execution_conformant") is True
                    and (quality, time_grade) == ("Judged", "Located"))
        status.update(state="passed" if all_pass else "failed", exit_code=0 if all_pass else (exit_code or 1),
                      junit_identity_check=counts, native_summary=summary,
                      fixture_execution_conformant=receipt.get("fixture_execution_conformant"))
        return 0 if all_pass else (exit_code or 1)
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1, error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
