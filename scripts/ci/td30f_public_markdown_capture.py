"""Native hosted capture wrapper for the TD-30f public-Markdown aggregate."""
from __future__ import annotations

import hashlib
import ast
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import tomllib
from pathlib import Path, PurePosixPath

ROOT_PIN = "9a18693b627487122c306bdadfb2e64fc254536a"
APP_PIN = "79abe3eca50c911d89e5e9855bbd6392bae2b35d"
CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
SELECTIONS = (
    "tests/ci/test_td30f_public_markdown_report.py::test_original_aggregate_is_218_row_public_successor_and_non_gold",
    "tests/ci/test_td30f_public_markdown_report.py::test_word_trigram_guards_keep_strict_threshold_and_minimum_boundaries",
    "tests/ci/test_td30f_public_markdown_report.py::test_streaming_block_controls_are_body_only_and_match_pinned_boundaries",
    "tests/ci/test_td30f_public_markdown_report.py::test_streaming_precondition_exclusions_use_tail_line_count",
)
EXPECTED_CASES = 4
LOCKED_PACKAGES = {"pytest": "9.0.3", "iniconfig": "2.3.0", "packaging": "26.0",
                   "pluggy": "1.6.0", "Pygments": "2.20.0"}
INSTALL_COMMAND = ("python -m pip install pytest==9.0.3 iniconfig==2.3.0 packaging==26.0 "
                   "pluggy==1.6.0 Pygments==2.20.0")
WORKFLOW = ".github/workflows/td30f-public-markdown-capture.yml"
REPORT = "scripts/ci/td30f_public_markdown_report.py"
CAPTURE = "scripts/ci/td30f_public_markdown_capture.py"
RUNNER = "scripts/ci/td30f_public_markdown_run.py"
TEST = "tests/ci/test_td30f_public_markdown_report.py"
GENERATED = "generated/td30f-public-markdown-aggregate.json"
APP_SOURCE_READS = (
    "src/classifiers/quality_detector.py", "src/config/__init__.py", "src/config/models.py",
    "src/pipeline_monitor/anomaly.py", "orchestration/anomaly_signals.yaml",
    "src/llm_primitives/inference.py",
)
CONFIG_NAMES = {"pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini", "uv.lock",
                "requirements.txt", "requirements-dev.txt", "requirements-test.txt"}


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def require_clean(repo: Path, label: str, expected: str) -> str:
    status = git(repo, "status", "--porcelain", "--untracked-files=all")
    actual = git(repo, "rev-parse", "HEAD")
    if status or actual != expected:
        raise RuntimeError(f"{label} checkout identity mismatch")
    return actual


def regular_file(repo: Path, name: str) -> Path:
    path = repo
    for part in Path(name).parts:
        path = path / part
        if path.is_symlink():
            raise RuntimeError(f"declared read traverses symlink: {name}")
    if not path.is_file():
        raise RuntimeError(f"declared read is missing: {name}")
    return path.absolute()


def tracked_python_config(repo: Path) -> list[Path]:
    found = []
    for name in git(repo, "ls-files", "-z").split("\0"):
        if name and (name.endswith(".py") or PurePosixPath(name).name in CONFIG_NAMES):
            found.append(regular_file(repo, name))
    return found


def verify_selection_contract(recipe: Path) -> None:
    runner_tree = ast.parse(regular_file(recipe, RUNNER).read_text(encoding="utf-8"))
    selected_nodes = [node for node in runner_tree.body if isinstance(node, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id == "SELECTIONS"
                              for target in node.targets)]
    if len(selected_nodes) != 1:
        raise RuntimeError("capture runner must declare exactly one static SELECTIONS tuple")
    runner_selections = ast.literal_eval(selected_nodes[0].value)
    test_tree = ast.parse(regular_file(recipe, TEST).read_text(encoding="utf-8"))
    test_names = {node.name for node in test_tree.body
                  if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")}
    driver_names = {selection.rsplit("::", 1)[-1] for selection in SELECTIONS}
    runner_names = {selection.rsplit("::", 1)[-1] for selection in runner_selections}
    if (tuple(runner_selections) != SELECTIONS or len(SELECTIONS) != EXPECTED_CASES
            or driver_names != test_names or runner_names != test_names):
        raise RuntimeError("native selection metadata, writer runner, and exact test identities differ")


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, carrier, corpus, app = (workspace / name for name in ("recipe", "carrier", "corpus", "app"))
    result = runner_temp / "td30f-public-markdown-capture" / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status = {"state": "preparing", "job": "td30f-public-markdown-successor-capture", "exit_code": None}
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
    try:
        if os.environ.get("TD30F_RUNNER_CONTEXT") != "ubuntu-latest":
            raise RuntimeError("runner context differs from reviewed recipe")
        if os.environ.get("TD30F_EXECUTION_CONTEXT") != "public-markdown-offline-guard-body-replay":
            raise RuntimeError("execution context differs from reviewed recipe")
        if platform.python_version() != "3.13.15":
            raise RuntimeError(f"Python runtime differs from pin: {platform.python_version()}")
        if os.environ.get("TD30F_INSTALL_COMMAND") != INSTALL_COMMAND:
            raise RuntimeError("dependency installation command differs from reviewed recipe")
        pins = {
            "recipe": require_clean(recipe, "recipe", os.environ["GITHUB_SHA"]),
            "carrier": require_clean(carrier, "carrier", CARRIER_PIN),
            "corpus": require_clean(corpus, "corpus", ROOT_PIN),
            "app": require_clean(app, "app", APP_PIN),
        }
        if pins["recipe"] != os.environ["GITHUB_SHA"]:
            raise RuntimeError("recipe checkout does not match event SHA")
        for env_name, expected in (("ROOT_CORPUS_PIN", ROOT_PIN), ("APP_PIN", APP_PIN),
                                   ("ROOT_CARRIER_PIN", CARRIER_PIN)):
            if os.environ.get(env_name) != expected:
                raise RuntimeError(f"workflow {env_name} differs from reviewed pin")
        lock = tomllib.loads((app / "uv.lock").read_text(encoding="utf-8"))
        locked = {item["name"].lower(): item["version"] for item in lock["package"]}
        for name, version in LOCKED_PACKAGES.items():
            if locked.get(name.lower()) != version or importlib.metadata.version(name) != version:
                raise RuntimeError(f"test dependency differs from APP uv.lock: {name}")

        report_builder = regular_file(recipe, REPORT)
        runner = regular_file(recipe, RUNNER)
        verify_selection_contract(recipe)
        generated = recipe / GENERATED
        generated.parent.mkdir(parents=True, exist_ok=True)
        if generated.exists():
            raise RuntimeError("refusing to overwrite generated aggregate")

        freeze = result / "pip-freeze.txt"
        freeze.write_bytes(subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"]))
        environment = result / "environment.json"
        environment.write_text(json.dumps({
            "python": sys.version, "platform": platform.platform(), "runner_context": "ubuntu-latest",
            "execution_context": "public-markdown-offline-guard-body-replay",
            "repositories": pins, "selections": list(SELECTIONS), "expected_case_count": EXPECTED_CASES,
            "install_command": INSTALL_COMMAND, "declared_dependencies": LOCKED_PACKAGES,
            "scope": "Pinned authored Markdown text; AST-isolated detector bodies only; no APP imports or project runtime.",
            "interpretation": "Aggregate trigger shares have provenance-only labels. Native conformance grades capture integrity, not detector quality.",
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        junit, native = result / "original-junit.xml", result / "native"
        read_paths = [freeze, environment, regular_file(recipe, WORKFLOW), report_builder,
                      regular_file(recipe, CAPTURE), runner, regular_file(recipe, TEST),
                      *tracked_python_config(recipe), *tracked_python_config(carrier),
                      *tracked_python_config(app), regular_file(app, "uv.lock"),
                      *(regular_file(app, relative) for relative in APP_SOURCE_READS)]
        producer = [sys.executable, str(carrier / "scripts/ci/native_conformance.py"),
                    "--cwd", str(recipe), "--junit", str(junit), "--output", str(native),
                    "--repo", f"recipe={recipe}", "--repo", f"carrier={carrier}",
                    "--repo", f"corpus={corpus}", "--repo", f"app={app}",
                    "--generated-output", GENERATED]
        for path in dict.fromkeys(p.resolve() for p in read_paths):
            producer.extend(["--read-path", str(path)])
        for selection in SELECTIONS:
            producer.extend(["--select", selection])
        command = [sys.executable, str(runner), "--root-corpus", str(corpus), "--app", str(app),
                   "--output", GENERATED, "--junit", str(junit)]
        status.update(state="running", repositories=pins, selections=list(SELECTIONS))
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
        code = subprocess.call([*producer, "--", *command], cwd=recipe)
        receipt_path = native / "receipt.json"
        if not receipt_path.is_file():
            status.update(state="capture_failed", exit_code=code or 1,
                          diagnostic="native receipt was not produced")
            return code or 1
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        counts = (receipt.get("summary") or {}).get("counts") or {}
        originals = [*sorted(native.iterdir()), junit, freeze, environment]
        before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in originals}
        sys.path.insert(0, str(carrier))
        sys.path.insert(0, str(carrier / "scripts/vidya"))
        from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
        from claim_tuple import grade
        rows = native_rows(receipt_path)
        analysis = {"kind": "analysis_of_existing_capture_receipt", "native_original_hashes": before,
                    "repositories": pins, "fixture_rerun": False,
                    "new_native_receipt_authored_by_analysis": False, "grade": None}
        if len(rows) != 1:
            raise RuntimeError("native receipt does not project to one existing shared CI claim")
        claim = project_ci_conformance(rows[0])
        q, t, reasons = grade(claim)
        analysis.update(measurement_id=claim.measurement_id, source_kind=claim.source_kind,
                        binding_kind=claim.binding_kind, grade={"Q": q, "T": t, "reasons": reasons})
        if (q, t) != ("Judged", "Located"):
            raise RuntimeError("shared CI claim grade differs from reviewed runner-integrity expectation")
        after = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in originals}
        if before != after:
            raise RuntimeError("shared-grade analysis changed an original capture member")
        (result / "shared-grade.json").write_text(json.dumps(analysis, indent=2, sort_keys=True) + "\n",
                                                   encoding="utf-8")
        passed = (code == 0 and receipt.get("fixture_execution_conformant") is True
                  and counts.get("collected") == EXPECTED_CASES
                  and counts.get("executed") == EXPECTED_CASES
                  and counts.get("skipped") == counts.get("failure") == counts.get("error") == 0)
        status.update(state="passed" if passed else "failed", exit_code=0 if passed else (code or 1),
                      native_metric=receipt.get("fixture_execution_conformant"), junit_counts=counts,
                      expected_case_count=EXPECTED_CASES)
        return 0 if passed else (code or 1)
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1, error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
