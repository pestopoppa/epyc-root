#!/usr/bin/env python3
"""Capture the real stack-change promotion-gate controls on an isolated runner."""
from __future__ import annotations

import collections
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts/vidya"))
APP_PIN = "bec3263e6a83f446bf291b7dee938e326cffddfc"
APP_LOCK_BLOB = "ef2306018773ff9a1e80389970d92f66fcf8d5b7"
PYTHON_PIN = "3.13.15"
WORKFLOW = ".github/workflows/w4-stack-change-native.yml"
DRIVER = "scripts/ci/w4_native_capture.py"
EXPECTED_CASES = [
    {"classname": "tests.unit.test_stack_change_pipeline_real_promotion_gate",
     "name": "test_real_promotion_gate_accepts_each_approved_swapped_temporary_world"},
    {"classname": "tests.unit.test_stack_change_pipeline_real_promotion_gate",
     "name": "test_real_promotion_gate_does_not_run_after_a_bad_temporary_world"},
]
APP_TESTS = (
    "tests/unit/test_stack_change_pipeline_real_promotion_gate.py",
    "tests/unit/test_stack_change_pipeline_simulated_fixtures.py",
    "tests/unit/test_build_server_command_helpers.py",
    "tests/unit/test_seeding_infra.py",
    "tests/unit/test_seeding_infra_additional.py",
    "tests/unit/test_seeding_infra_branching.py",
    "tests/unit/test_seed_specialist_routing_main_and_retry.py",
)
INNER_MODULES = (
    "tests.unit.test_stack_change_pipeline_simulated_fixtures",
    "tests.unit.test_build_server_command_helpers",
    "tests.unit.test_seeding_infra",
    "tests.unit.test_seeding_infra_additional",
    "tests.unit.test_seeding_infra_branching",
    "tests.unit.test_seed_specialist_routing_main_and_retry",
)
ABSENT_BINARY_OVERRIDES = {
    "ORCHESTRATOR_PATHS_LLAMA_CPP_BIN": "llama-server",
    "ORCHESTRATOR_PATHS_LLAMA_MTMD": "mtmd-cli",
    "ORCHESTRATOR_PATHS_LLAMA_SERVER": "llama-server-wrapper",
}
APP_READS = (
    "uv.lock", "pyproject.toml",
    "orchestration/repl_memory/__init__.py", "orchestration/repl_memory/embedder.py",
    "orchestration/repl_memory/episodic_store.py", "orchestration/repl_memory/failure_graph.py",
    "orchestration/repl_memory/faiss_store.py", "orchestration/repl_memory/graph_router_predictor.py",
    "orchestration/repl_memory/hybrid_router.py", "orchestration/repl_memory/hypothesis_graph.py",
    "orchestration/repl_memory/indexed_memory_policy.py", "orchestration/repl_memory/memory_record.py",
    "orchestration/repl_memory/progress_logger.py", "orchestration/repl_memory/q_judge.py",
    "orchestration/repl_memory/q_reward.py", "orchestration/repl_memory/q_scorer.py",
    "orchestration/repl_memory/retrieval_config.py", "orchestration/repl_memory/retriever.py",
    "orchestration/repl_memory/routing_classifier.py", "orchestration/repl_memory/routing_fast_path.py",
    "orchestration/repl_memory/routing_risk.py", "orchestration/repl_memory/skill_bank.py",
    "orchestration/repl_memory/skill_retriever.py", "orchestration/repl_memory/staged_scorer.py",
    "scripts/graph_router/action_space.py", "scripts/registry/render_stack_summary.py",
    "scripts/registry/stack_change_pipeline.py", "scripts/registry/sync_procedure_role_enums.py",
    "scripts/server/bench_core_claim.py", "scripts/server/fleet_markers.py",
    "scripts/server/orchestrator_stack.py", "scripts/server/realized_fleet.py",
    "scripts/server/runtime_facts_manifest.py", "scripts/server/stack_checkpoint.py",
    "scripts/server/stack_commands.py", "scripts/server/stack_docker.py",
    "scripts/server/stack_env.py", "scripts/server/stack_health.py",
    "scripts/server/stack_host.py", "scripts/server/stack_log_banner.py",
    "scripts/server/stack_manifest.py", "scripts/server/stack_numa.py",
    "scripts/server/stack_numa_evict.py", "scripts/server/stack_numa_mode.py",
    "scripts/server/stack_paths.py", "scripts/server/stack_prewarm.py",
    "scripts/server/stack_processes.py", "scripts/server/stack_runtime.py",
    "scripts/server/stack_state.py", "scripts/validate/check_shared_with_derivations.py",
    "scripts/validate/reasoning_effort_certifications.py", "scripts/validate/stack_change_guard.py",
    "scripts/benchmark/seed_specialist_routing.py", "scripts/benchmark/seed_specialist_routing_v2.py",
    "scripts/benchmark/seeding_checkpoint.py", "scripts/benchmark/seeding_cli_config.py",
    "scripts/benchmark/seeding_eval.py", "scripts/benchmark/seeding_infra.py",
    "scripts/benchmark/seeding_injection.py", "scripts/benchmark/seeding_legacy.py",
    "scripts/benchmark/seeding_orchestrator.py", "scripts/benchmark/seeding_rewards.py",
    "scripts/benchmark/seeding_sampling.py", "scripts/benchmark/seeding_scoring.py",
    "scripts/benchmark/seeding_telemetry.py", "scripts/benchmark/seeding_types.py",
    "src/autopilot_core/measurement_guards.py", "src/classifiers/role_taxonomy.py",
    "src/api/admission.py", "src/api/health_tracker.py", "src/api/state.py",
    "src/config/__init__.py", "src/env_parsing.py", "src/features.py", "src/inference_lock.py",
    "src/models/__init__.py", "src/retrieval/kb_rag_query_telemetry.py",
    "src/orchestration/interaction.py", "src/pipeline_monitor/change_log.py",
    "src/pipeline_monitor/claude_debugger.py", "src/prompt_builders/resolver.py",
    "src/registry/kernel_paths.py", "src/registry/model_descriptors.py",
    "src/registry/stack_priors.py", "src/registry_loader.py", "src/roles.py",
    "src/workload_model.py", "tests/__init__.py", "tests/conftest.py",
    "tests/unit/__init__.py", *APP_TESTS,
)
ROOT_READS = (
    WORKFLOW, DRIVER, "scripts/ci/w4_native_requirements.txt",
    "scripts/ci/native_conformance.py", "scripts/ci/ni08_source_context.py",
    "scripts/vidya/adapters/README.md", "scripts/vidya/adapters/__init__.py",
    "scripts/vidya/adapters/ci_conformance.py", "scripts/vidya/claim_tuple.py",
    "scripts/vidya/lattice.py", "scripts/vidya/frames.py", "scripts/vidya/canonical.py",
    "scripts/vidya/measurement_record.py", "handoffs/active/vidya-belief-substrate-program.md",
)
PACKAGES = {
    "annotated-types": "0.7.0", "anyio": "4.13.0", "certifi": "2026.2.25",
    "h11": "0.16.0", "httpcore": "1.0.9", "httpx": "0.28.1", "idna": "3.11",
    "iniconfig": "2.3.0", "packaging": "26.0", "pluggy": "1.6.0",
    "numpy": "2.4.4", "Pygments": "2.20.0", "pydantic": "2.13.0",
    "pydantic-core": "2.46.0", "pydantic-settings": "2.13.1",
    "pytest": "9.0.3", "PyYAML": "6.0.3", "python-dotenv": "1.2.2",
    "typing-extensions": "4.15.0", "typing-inspection": "0.4.2",
}


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def require_clean(repo: Path, label: str) -> str:
    status = git(repo, "status", "--porcelain", "--untracked-files=no")
    if status:
        raise RuntimeError(f"{label} checkout has tracked changes: {status}")
    return git(repo, "rev-parse", "HEAD")


def tracked(repo: Path, relative: str) -> Path:
    path = repo
    for part in Path(relative).parts:
        path = path / part
        if path.is_symlink():
            raise RuntimeError(f"declared source traverses a symlink: {relative}")
    entry = git(repo, "ls-tree", "HEAD", "--", relative).split()
    if len(entry) < 3 or entry[0] not in {"100644", "100755"} or entry[1] != "blob":
        raise RuntimeError(f"declared source is not a tracked regular blob: {relative}")
    return path.absolute()


def regular_bytes(path: Path) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise RuntimeError(f"not a regular file: {path}")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            return handle.read()
    finally:
        os.close(fd)


def snapshots(paths: list[Path]) -> dict[str, dict[str, object]]:
    return {str(path): {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            for path in paths for data in [regular_bytes(path)]}


def result_snapshot(root: Path) -> dict[str, dict[str, object]]:
    snapshot = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise RuntimeError(f"native result tree contains a symlink: {path}")
        relative = path.relative_to(root).as_posix()
        if relative == "status.json":
            continue
        if path.is_dir():
            snapshot[relative + "/"] = {"kind": "directory"}
            continue
        data = regular_bytes(path)
        snapshot[str(path.relative_to(root))] = {
            "kind": "regular_file", "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    return snapshot


def require_absent_binary_overrides(runner_temp: Path) -> dict[str, str]:
    expected = {
        key: str(runner_temp / "w4-stack-change" / "absent-binaries" / leaf)
        for key, leaf in ABSENT_BINARY_OVERRIDES.items()
    }
    if any(os.environ.get(key) != value for key, value in expected.items()):
        raise RuntimeError("runner must use the three declared absent-binary config overrides")
    if any(os.path.lexists(value) for value in expected.values()):
        raise RuntimeError("an absent-binary config path unexpectedly exists")
    return expected


def load_carrier():
    path = ROOT / "scripts/ci/native_conformance.py"
    spec = importlib.util.spec_from_file_location("w4_native_conformance", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load existing native fixture carrier")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def install_and_verify(app: Path, result: Path) -> tuple[Path, Path, Path]:
    requirements = ROOT / "scripts/ci/w4_native_requirements.txt"
    if git(app, "rev-parse", "HEAD:uv.lock") != APP_LOCK_BLOB:
        raise RuntimeError("APP lock blob differs from the dependency source used for wheel selection")
    lock = tomllib.loads(regular_bytes(app / "uv.lock").decode("utf-8"))
    locked = {row["name"].lower().replace("_", "-"): row for row in lock["package"]}
    declared: dict[str, dict[str, object]] = {}
    current = None
    for line in regular_bytes(requirements).decode("utf-8").splitlines():
        row = line.strip()
        if not row:
            continue
        if not line[:1].isspace():
            if not row.endswith("\\"):
                raise RuntimeError("exact requirement row lacks a continuation")
            match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)", row[:-1].rstrip())
            if not match:
                raise RuntimeError("invalid exact package row in hash-locked requirements")
            current = match.group(1).lower().replace("_", "-")
            declared[current] = {"version": match.group(2), "hashes": set()}
        else:
            match = re.fullmatch(r"--hash=sha256:([0-9a-f]{64})", row)
            if not match or current is None:
                raise RuntimeError("invalid or orphan wheel hash in requirements")
            declared[current]["hashes"].add(match.group(1))
    if set(declared) != {name.lower() for name in PACKAGES}:
        raise RuntimeError("requirements package set differs from the tested import closure")
    for name, version in PACKAGES.items():
        key = name.lower().replace("_", "-")
        package = locked.get(key)
        if not package or package["version"] != version or declared[key]["version"] != version:
            raise RuntimeError(f"locked package version differs: {name}=={version}")
        compatible = {
            wheel["hash"].removeprefix("sha256:") for wheel in package.get("wheels", [])
            if (wheel["url"].lower().endswith("-py3-none-any.whl")
                or ("cp313-cp313-manylinux" in wheel["url"].lower()
                    and "x86_64" in wheel["url"].lower()))
        }
        if not compatible or declared[key]["hashes"] != compatible:
            raise RuntimeError(f"requirements wheel hashes differ from APP lock: {name}")
    install_log = result / "dependency-install.log"
    install = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--require-hashes", "--no-deps",
         "--only-binary=:all:", "-r", str(requirements)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    install_log.write_bytes(install.stdout)
    if install.returncode:
        raise RuntimeError(f"hash-locked wheel installation failed ({install.returncode})")
    versions = {name: importlib.metadata.version(name) for name in PACKAGES}
    if versions != PACKAGES:
        raise RuntimeError(f"installed packages differ from pins: {versions}")
    freeze = subprocess.run([sys.executable, "-m", "pip", "freeze", "--all"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if freeze.returncode:
        raise RuntimeError("pip freeze failed")
    freeze_path = result / "pip-freeze.txt"
    freeze_path.write_bytes(freeze.stdout)
    env_path = result / "environment.json"
    env_path.write_text(json.dumps({"python": sys.version,
                                   "python_version": platform.python_version(),
                                   "platform": platform.platform(), "packages": versions,
                                   "app_pin": APP_PIN}, sort_keys=True) + "\n", encoding="utf-8")
    return install_log, freeze_path, env_path


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: w4_native_capture.py APP_ROOT")
    app = Path(sys.argv[1]).resolve()
    if os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD") != "1" or os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise RuntimeError("pytest autoload and bytecode controls differ from the reviewed recipe")
    if os.environ.get("PYTEST_ADDOPTS", "") or os.environ.get("PYTEST_PLUGINS", ""):
        raise RuntimeError("inherited pytest options/plugins must be empty")
    if not os.environ.get("GITHUB_SHA") or git(ROOT, "rev-parse", "HEAD") != os.environ["GITHUB_SHA"]:
        raise RuntimeError("ROOT checkout differs from the triggering recipe commit")
    for relative in ("scripts/vidya/adapters/README.md", "handoffs/active/vidya-belief-substrate-program.md"):
        if "VB-W4-STACK-CHANGE-GATE" not in (ROOT / relative).read_text(encoding="utf-8"):
            raise RuntimeError("prospective W4 enrollment is absent")
    runner_temp_value = os.environ.get("RUNNER_TEMP")
    if not runner_temp_value:
        raise RuntimeError("RUNNER_TEMP is required")
    runner_temp = Path(runner_temp_value).resolve()
    absent_binary_paths = require_absent_binary_overrides(runner_temp)
    expected_venv = runner_temp / "w4-stack-change" / "venv"
    if Path(sys.prefix).resolve() != expected_venv.resolve():
        raise RuntimeError("capture is not running in the isolated RUNNER_TEMP virtualenv")
    if platform.python_implementation() != "CPython" or platform.python_version() != PYTHON_PIN:
        raise RuntimeError(f"capture requires CPython {PYTHON_PIN}")
    if os.environ.get("APP_PIN") != APP_PIN or git(app, "rev-parse", "HEAD") != APP_PIN:
        raise RuntimeError("APP checkout differs from the reviewed fixture source")
    result = runner_temp / "w4-stack-change" / "result"
    if not result.is_relative_to(runner_temp) or os.path.lexists(result / "native"):
        raise RuntimeError("native output path is not fresh and RUNNER_TEMP-contained")
    result.mkdir(parents=True, exist_ok=True)
    world_root = result / "per-world"
    if os.path.lexists(world_root) or not world_root.is_relative_to(result):
        raise RuntimeError("per-world output path must be fresh and contained under the result")
    app_pin = require_clean(app, "APP")
    root_pin = require_clean(ROOT, "ROOT")
    if app_pin != APP_PIN:
        raise RuntimeError("APP HEAD differs from exact reviewed source")
    install_log, freeze_path, env_path = install_and_verify(app, result)
    environment = json.loads(regular_bytes(env_path))
    environment["absent_binary_config_overrides"] = absent_binary_paths
    env_path.write_text(json.dumps(environment, sort_keys=True) + "\n", encoding="utf-8")
    source_context = result / "source-context.json"
    subprocess.run([sys.executable, str(ROOT / "scripts/ci/ni08_source_context.py"),
                    "--repo", f"root={ROOT}", "--repo", f"app={app}",
                    "--output", str(source_context)], check=True)
    os.environ["W4_PROMOTION_GATE_CAPTURE_DIR"] = str(world_root)
    junit = result / "outer.junit.xml"
    selection = "tests/unit/test_stack_change_pipeline_real_promotion_gate.py"
    command = [sys.executable, "-m", "pytest", "--noconftest", "-c", "/dev/null",
               "--rootdir", str(app), "-o", "addopts=", "-p", "no:cacheprovider",
               "--import-mode=importlib", "-q", f"--junitxml={junit}", selection]
    read_paths = ([tracked(ROOT, name) for name in ROOT_READS]
                  + [tracked(app, name) for name in APP_READS]
                  + [source_context, install_log, freeze_path, env_path])
    source_before_capture = snapshots(read_paths)
    carrier = load_carrier()
    record = carrier.capture_fixture_execution(
        argv=command, cwd=app, junit=junit, output=result / "native",
        repositories={"root": ROOT, "app": app}, read_paths=read_paths,
        selections=[selection],
    )
    if require_absent_binary_overrides(runner_temp) != absent_binary_paths:
        raise RuntimeError("absent-binary config overrides changed during inner gate execution")
    actual = record.get("summary")
    if (not isinstance(actual, dict) or not isinstance(actual.get("cases"), list)
            or collections.Counter((row["classname"], row["name"]) for row in actual["cases"])
            != collections.Counter((row["classname"], row["name"]) for row in EXPECTED_CASES)
            or record.get("fixture_execution_conformant") is not True):
        raise RuntimeError("native outer JUnit/exit differs from the exact two-case source manifest")
    worlds = json.loads(regular_bytes(world_root / "worlds.json"))
    expected_worlds = {"frontdoor", "worker", "vision", "ingest"}
    world_rows = worlds.get("worlds", [])
    if not isinstance(world_rows, list) or {row.get("world") for row in world_rows} != expected_worlds:
        raise RuntimeError("the real gate did not retain all four swapped-world results")
    world_identities = []
    for world in world_rows:
        if (world.get("gate_status") != "ok" or not world.get("tests")
                or world.get("test_count") != len(world["tests"])):
            raise RuntimeError("a swapped world lacks a passing actual inner-suite record")
        classnames = {case["classname"] for case in world["tests"]}
        module_names = {module for module in INNER_MODULES
                        if any(name == module or name.startswith(module + ".") for name in classnames)}
        if set(INNER_MODULES) - module_names:
            raise RuntimeError("an original promotion target suite is absent from the inner JUnit")
        junit_path = Path(world.get("inner_junit", ""))
        try:
            junit_path.resolve().relative_to(world_root.resolve())
        except ValueError as exc:
            raise RuntimeError("inner JUnit path escaped the retained per-world result tree") from exc
        if not junit_path.is_file() or junit_path.is_symlink():
            raise RuntimeError("an inner promotion-target JUnit is missing or not a regular leaf")
        junit_root = ET.fromstring(regular_bytes(junit_path))
        junit_nodes = list(junit_root.iter("testcase"))
        actual_cases = [{"classname": node.attrib.get("classname"),
                         "name": node.attrib.get("name")} for node in junit_nodes]
        if (not actual_cases or actual_cases != world["tests"]
                or len(actual_cases) != world["test_count"]
                or any(not case["classname"] or not case["name"] for case in actual_cases)
                or any(node.find(tag) is not None
                       for node in junit_nodes for tag in ("failure", "error", "skipped"))):
            raise RuntimeError("inner JUnit identities, counts, or statuses differ from retained world data")
        world_identities.append(set((case["classname"], case["name"]) for case in actual_cases))
    if any(identity_set != world_identities[0] for identity_set in world_identities[1:]):
        raise RuntimeError("the four swapped worlds did not retain the same complete inner case set")
    refusal = json.loads(regular_bytes(world_root / "refusal.json"))
    if (refusal.get("report_ok") is not False or refusal.get("gate_status") != "skipped"
            or refusal.get("gate_errors")):
        raise RuntimeError("bad temporary-world refusal was not retained as a skipped gate")
    source_before = snapshots(read_paths)
    if source_before != source_before_capture:
        raise RuntimeError("declared source changed during native execution")
    original_results_before = result_snapshot(result)
    from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
    from claim_tuple import grade
    rows = native_rows(str(result / "native/receipt.json"))
    if len(rows) != 1:
        raise RuntimeError("native CI adapter did not produce exactly one shared-grade row")
    judgment = grade(project_ci_conformance(rows[0]))
    source_after = snapshots(read_paths)
    original_results_after = result_snapshot(result)
    if source_before != source_after or original_results_before != original_results_after:
        raise RuntimeError("declared source or original capture bytes changed during shared grading")
    if judgment[0:2] != ("Judged", "Located"):
        raise RuntimeError("existing shared ClaimTuple ladder did not return Judged/Located")
    summary = {"outer_case_count": len(actual["cases"]), "worlds": 4,
               "inner_identity_count_per_world": world_rows[0]["test_count"],
               "inner_world_case_counts": {row["world"]: row["test_count"] for row in world_rows},
               "shared_grade": judgment[0], "location": judgment[1],
               "scope": "real six-target promotion gate over temporary swapped worlds",
               "source_inputs_before_capture": source_before_capture,
               "source_inputs_before": source_before, "source_inputs_after": source_after,
               "original_results_before": original_results_before,
               "original_results_after": original_results_after}
    (result / "shared-grade-check.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
