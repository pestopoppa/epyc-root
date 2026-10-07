"""Hosted actual experimental SSM rollback initializer/backend CPU controls through unchanged native CI grade."""
from __future__ import annotations
import ast
import collections
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import shutil
import shlex
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[2]
PYTHON_PIN = "3.13.15"
LOCK_SOURCE_COMMIT = "70096b763939a43409a1f1827ab633d62425a6c1"
LOCK_SOURCE_BLOB = "ef2306018773ff9a1e80389970d92f66fcf8d5b7"
SOURCE_COMMIT = "8e09a5e003f61b7ce7d58088f2f34595118068b4"
CONTEXT_COMMIT = "e6afe15f966d175d20756d8cff3fcbcc1becf756"
CARRIER_COMMIT = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
PACKAGES = {"pytest": "9.0.3", "iniconfig": "2.3.0", "packaging": "26.0", "pluggy": "1.6.0", "pygments": "2.20.0"}
WORKFLOW_INPUTS = ('.github/workflows/rvp-rollback-native.yml', 'scripts/ci/rvp_rollback_capture.py', 'scripts/ci/rvp_rollback_requirements.txt', 'scripts/ci/rvp_rollback_inputs.json', 'scripts/ci/rvp_native_case.py', 'scripts/ci/rvp_native_control/CMakeLists.txt', 'scripts/ci/rvp_native_control/rvp_actual_initializer.cpp')

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def verify_locked_packages(lock_source: Path, requirements: Path) -> dict[str, str]:
    if subprocess.check_output(["git", "-C", str(lock_source), "rev-parse", "HEAD"], text=True).strip() != LOCK_SOURCE_COMMIT:
        raise RuntimeError("APP pytest lock source commit differs from reviewed pin")
    if subprocess.check_output(["git", "-C", str(lock_source), "rev-parse", "HEAD:uv.lock"], text=True).strip() != LOCK_SOURCE_BLOB:
        raise RuntimeError("APP uv.lock blob differs from reviewed pin")
    if subprocess.check_output(["git", "-C", str(lock_source), "status", "--porcelain", "--untracked-files=no"], text=True).strip():
        raise RuntimeError("APP pytest lock checkout has tracked modifications")
    locked = {item["name"].lower(): item for item in tomllib.loads(
        (lock_source / "uv.lock").read_text(encoding="utf-8"))["package"]}
    text = requirements.read_text(encoding="utf-8")
    declared: dict[str, set[str]] = {}
    current = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line[:1].isspace():
            match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+) \\", stripped)
            if not match:
                raise RuntimeError("invalid exact requirement declaration")
            current = match.group(1).lower()
            if match.group(2) != PACKAGES.get(current):
                raise RuntimeError(f"requirements version differs for {current}")
            declared[current] = set()
        else:
            match = re.fullmatch(r"--hash=sha256:([0-9a-f]{64})", stripped)
            if not match or current is None:
                raise RuntimeError("invalid or orphan package hash")
            declared[current].add(match.group(1))
    if set(declared) != set(PACKAGES):
        raise RuntimeError("requirements differ from the five-package selected closure")
    for name, version in PACKAGES.items():
        item = locked.get(name)
        if not item or item["version"] != version:
            raise RuntimeError(f"locked source does not pin {name}=={version}")
        wheel_hashes = {row["hash"].removeprefix("sha256:") for row in item.get("wheels", [])}
        if not wheel_hashes or declared[name] != wheel_hashes:
            raise RuntimeError(f"requirements hashes differ from the all locked wheels for {name}")
    installed = {name: importlib.metadata.version(name) for name in PACKAGES}
    if installed != PACKAGES:
        raise RuntimeError("installed package versions differ from the exact selected lock closure")
    return installed

def regular_bytes(path: Path) -> bytes:
    import stat
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise RuntimeError(f"source/result input is not a regular file: {path}")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            return handle.read()
    finally:
        os.close(fd)

def source_snapshot(paths: list[Path]) -> dict[str, dict[str, object]]:
    return {str(path): {"bytes": len(data), "sha256": digest(data)}
            for path in paths for data in [regular_bytes(path)]}

def result_snapshot(root: Path, *, exclude_status: bool = True) -> dict[str, dict[str, object]]:
    snapshot = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise RuntimeError(f"result tree contains a symlink: {path}")
        relative = path.relative_to(root).as_posix()
        if exclude_status and relative == "status.json":
            continue
        if path.is_dir():
            snapshot[relative + "/"] = {"kind": "directory"}
            continue
        data = regular_bytes(path)
        snapshot[relative] = {"kind": "regular_file", "bytes": len(data), "sha256": digest(data)}
    return snapshot

def pinned(repo: Path, commit: str, label: str) -> None:
    if subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip() != commit:
        raise RuntimeError(f"{label} HEAD differs from the reviewed pin")
    if subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=all"], text=True).strip():
        raise RuntimeError(f"{label} checkout is not clean")


def compiler_input_context(toolchain: dict, build: Path) -> tuple[dict, list[Path]]:
    """Bind actual GCC driver children and inputs named by generated build metadata."""
    records = {"children": [], "driver_queries": [], "link_inputs": []}
    reads = []
    compilers = [toolchain[name]["invoked_path"] for name in ("gcc", "g++")]
    def bind(raw: str) -> Path:
        candidate = Path(raw)
        if not candidate.is_absolute():
            located = shutil.which(raw)
            if not located:
                raise RuntimeError(f"compiler child/input does not resolve: {raw}")
            candidate = Path(located)
        resolved = candidate.resolve(strict=True)
        data = regular_bytes(resolved)
        reads.append(resolved)
        return resolved
    for compiler in compilers:
        for name in ("cc1", "cc1plus", "collect2", "as", "lto-wrapper"):
            argv = [compiler, "--print-prog-name=" + name]
            completed = subprocess.run(argv, text=True, capture_output=True, check=False)
            if completed.returncode or not completed.stdout.strip():
                raise RuntimeError("compiler child discovery failed")
            resolved = bind(completed.stdout.strip())
            records["children"].append({"argv": argv, "stdout": completed.stdout,
                "stderr": completed.stderr, "resolved_path": str(resolved),
                "sha256": digest(regular_bytes(resolved))})
    commands_argv = ["ninja", "-C", str(build), "-t", "commands"]
    commands = subprocess.check_output(commands_argv, text=True)
    records["commands_argv"] = commands_argv
    records["original_generated_commands"] = commands
    compiler_paths = {Path(value).resolve(strict=True) for value in compilers}
    for line in commands.splitlines():
        tokens = shlex.split(line)
        invocation = None
        for index, token in enumerate(tokens):
            if token in {"&&", ";", "||"}:
                continue
            located = shutil.which(token) if "/" not in token else token
            if located and Path(located).exists() and Path(located).resolve() in compiler_paths:
                end = next((i for i in range(index + 1, len(tokens)) if tokens[i] in {"&&", ";", "||"}), len(tokens))
                invocation = tokens[index:end]
                break
        if invocation is None:
            continue
        argv = invocation + ["-###"]
        completed = subprocess.run(argv, cwd=build, text=True, capture_output=True, check=False)
        if completed.returncode:
            raise RuntimeError("actual generated compiler command introspection failed")
        records["driver_queries"].append({"argv": argv, "cwd": str(build),
            "stdout": completed.stdout, "stderr": completed.stderr})
        for item in shlex.split(completed.stderr):
            if item.startswith("/") and Path(item).is_file():
                bind(item)
        # GCC's emitted link metadata names the selected start files and -l inputs.
        requested = {Path(item).name for item in shlex.split(completed.stderr)
                     if item.startswith("/") and Path(item).is_file() and item.endswith(".o")}
        libraries = {item[2:] for item in shlex.split(completed.stderr) if item.startswith("-l") and len(item) > 2}
        requested.update("lib" + name + suffix for name in libraries for suffix in (".so", ".a"))
        for name in sorted(requested):
            query = [invocation[0], "--print-file-name=" + name]
            result = subprocess.run(query, text=True, capture_output=True, check=False)
            raw = result.stdout.strip()
            if result.returncode:
                raise RuntimeError("compiler link-input discovery failed")
            if raw == name:
                records["link_inputs"].append({"argv": query, "stdout": result.stdout,
                    "stderr": result.stderr, "available": False})
                continue
            resolved = bind(raw)
            data = regular_bytes(resolved)
            records["link_inputs"].append({"argv": query, "stdout": result.stdout,
                "stderr": result.stderr, "available": True, "resolved_path": str(resolved),
                "bytes": len(data), "sha256": digest(data)})
    if not records["driver_queries"] or not records["link_inputs"]:
        raise RuntimeError("generated compiler/link input metadata is empty")
    return records, list(dict.fromkeys(reads))

def main() -> int:
    if len(sys.argv) != 5:
        raise SystemExit("usage: rvp_rollback_capture.py EXPERIMENTAL_SOURCE CARRIER LOCK_SOURCE CONTEXT")
    source, carrier_root, lock_source, context = [Path(value).resolve() for value in sys.argv[1:]]
    if not os.environ.get("GITHUB_SHA"):
        raise RuntimeError("triggering recipe SHA is absent")
    for repo, commit, label in [(ROOT, os.environ["GITHUB_SHA"], "recipe"),
            (source, SOURCE_COMMIT, "experimental source"),
            (carrier_root, CARRIER_COMMIT, "native carrier"), (context, CONTEXT_COMMIT, "enrollment context")]:
        pinned(repo, commit, label)
    if sys.version.split()[0] != PYTHON_PIN:
        raise RuntimeError("Python patch differs from the reviewed pin")
    if os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD") != "1" or os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise RuntimeError("pytest autoload and bytecode controls must be disabled")
    if os.environ.get("PYTEST_ADDOPTS", "") or os.environ.get("PYTEST_PLUGINS", ""):
        raise RuntimeError("inherited pytest options/plugins must be empty")
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    if Path(sys.prefix).resolve() != runner_temp / "rvp-rollback" / "venv":
        raise RuntimeError("capture must run inside the isolated runner virtualenv")
    result = runner_temp / "rvp-rollback" / "result"
    if not result.is_dir() or not (result / "status.json").is_file() or os.path.lexists(result / "native"):
        raise RuntimeError("workflow result envelope absent or native output not fresh")
    installed = verify_locked_packages(lock_source, ROOT / "scripts/ci/rvp_rollback_requirements.txt")
    manifest_path = ROOT / "scripts/ci/rvp_rollback_inputs.json"
    manifest = json.loads(regular_bytes(manifest_path))
    if manifest["schema"] != "epyc.rvp.rollback.inputs/v1":
        raise RuntimeError("source manifest schema differs")
    roots = {"source": source, "carrier": carrier_root, "context": context, "lock_source": lock_source}
    reads = [ROOT / name for name in WORKFLOW_INPUTS]
    for label, rows in manifest["inputs"].items():
        for row in rows:
            path = roots[label] / row["path"]
            data = regular_bytes(path)
            blob = subprocess.check_output(["git", "-C", str(roots[label]), "rev-parse", "HEAD:" + row["path"]], text=True).strip()
            if blob != row["blob"] or len(data) != row["bytes"] or digest(data) != row["sha256"]:
                raise RuntimeError(f"reviewed source binding differs: {label}/{row['path']}")
            reads.append(path)
    for relative in ("scripts/vidya/adapters/README.md", "handoffs/active/vidya-belief-substrate-program.md"):
        if "VB-RVP-SSM-ROLLBACK-CONFORMANCE" not in (context / relative).read_text(encoding="utf-8"):
            raise RuntimeError("prospective RVP source enrollment absent")
    environment = result / "environment.json"
    environment.write_text(json.dumps({"python": sys.version, "executable": sys.executable,
        "packages": installed, "pytest_plugin_autoload": os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"],
        "bytecode_disabled": os.environ["PYTHONDONTWRITEBYTECODE"],
        "scope": "actual source-built CPU rollback initializer and backend graph controls; no models or serving"}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.environ["PYTHONPATH"] = str(ROOT)
    inputs = result / "source-context.json"
    inputs.write_text(json.dumps({"repositories": {key: str(value) for key, value in roots.items()},
        "source_manifest": manifest, "expected_cases": manifest["expected_cases"],
        "pytest_environment": {key: os.environ.get(key, "") for key in ("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTHONDONTWRITEBYTECODE", "PYTHONPATH")}}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    reads += [environment, inputs, result / "install.log", result / "pip-freeze.txt"]
    reads = list(dict.fromkeys(path.resolve() for path in reads))
    for name in ("CC", "CXX", "CFLAGS", "CXXFLAGS", "LDFLAGS", "LD_PRELOAD", "LD_LIBRARY_PATH"):
        if os.environ.get(name, ""):
            raise RuntimeError(f"inherited build/runtime override must be empty: {name}")
    source_before_build = source_snapshot(reads)
    build = runner_temp / "rvp-rollback" / "build"
    if os.path.lexists(build):
        raise RuntimeError("build output must be fresh")
    toolchain = {}
    for name in ("cmake", "ninja", "gcc", "g++", "ld", "ar", "git"):
        binary = shutil.which(name)
        if not binary:
            raise RuntimeError(f"required build tool absent: {name}")
        resolved = Path(binary).resolve(strict=True)
        toolchain[name] = {"invoked_path": binary, "resolved_path": str(resolved),
            "bytes_sha256": digest(regular_bytes(resolved)),
            "version": subprocess.check_output([binary, "--version"], text=True)}
        reads.append(resolved)
    packages = subprocess.check_output(["dpkg-query", "-W"], text=True)
    toolchain_path = result / "toolchain.json"
    toolchain_path.write_text(json.dumps({"tools": toolchain, "dpkg_packages": packages,
        "build_type": "Release", "generator": "Ninja", "parallel_jobs": 2,
        "environment": {key: os.environ.get(key, "") for key in ("PATH", "CC", "CXX", "CFLAGS", "CXXFLAGS", "LDFLAGS", "LD_PRELOAD", "LD_LIBRARY_PATH")},
        "scope": "CPU static C++ source controls only"}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    configure = ["cmake", "-S", str(ROOT / "scripts/ci/rvp_native_control"), "-B", str(build),
        "-G", "Ninja", "-DCMAKE_BUILD_TYPE=Release", f"-DEPYC_EXPERIMENTAL_SOURCE={source}"]
    commands = [(configure, result / "configure.log"),
        (["cmake", "--build", str(build), "--parallel", "2", "--target", "rvp-actual-initializer", "test-backend-ops"], result / "build.log")]
    source_before_build_paths = list(dict.fromkeys(reads))
    source_before_build = source_snapshot(source_before_build_paths)
    for command_index, (argv, log) in enumerate(commands):
        completed = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=1200, check=False)
        log.write_bytes(completed.stdout)
        if completed.returncode:
            raise RuntimeError(f"hosted build command failed: {argv[0]}")
        if command_index == 0:
            if source_snapshot(source_before_build_paths) != source_before_build:
                raise RuntimeError("declared source/toolchain changed during configure")
            compiler_context, compiler_reads = compiler_input_context(toolchain, build)
            reads += compiler_reads
            toolchain_record = json.loads(regular_bytes(toolchain_path))
            toolchain_record["compiler_driver_context"] = compiler_context
            toolchain_path.write_text(json.dumps(toolchain_record, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            source_before_build_paths = list(dict.fromkeys(reads))
            source_before_build = source_snapshot(source_before_build_paths)
    if source_snapshot(source_before_build_paths) != source_before_build:
        raise RuntimeError("declared source changed during hosted build")
    # Ninja retains actual compile dependencies, including system headers from -MD.
    dependencies = subprocess.check_output(["ninja", "-C", str(build), "-t", "deps"], text=True)
    dependency_log = result / "ninja-dependencies.txt"
    dependency_log.write_text(dependencies, encoding="utf-8")
    header_bindings = []
    for line in dependencies.splitlines():
        if not line.startswith("    "):
            continue
        name = line.strip()
        path = Path(name)
        if not path.is_absolute():
            path = build / path
        resolved = path.resolve(strict=True)
        data = regular_bytes(resolved)
        header_bindings.append({"dependency_path": str(path), "resolved_path": str(resolved),
            "bytes": len(data), "sha256": digest(data)})
        reads.append(resolved)
    if not header_bindings:
        raise RuntimeError("actual C++ build produced no Ninja header dependency closure")
    dependency_binding = result / "resolved-header-bindings.json"
    dependency_binding.write_text(json.dumps(header_bindings, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    build_before_capture = result_snapshot(build, exclude_status=False)
    reads += [path for path in sorted(build.rglob("*")) if path.is_file()]
    reads += [toolchain_path, dependency_log, dependency_binding, result / "configure.log", result / "build.log"]
    initializer = list(build.rglob("rvp-actual-initializer"))
    backend = list(build.rglob("test-backend-ops"))
    if len(initializer) != 1 or len(backend) != 1 or not all(p.is_file() and not p.is_symlink() for p in initializer + backend):
        raise RuntimeError("actual source-built control executables are absent or ambiguous")
    runtime_dependencies = []
    for binary in initializer + backend:
        completed = subprocess.run(["ldd", str(binary)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        if completed.returncode:
            raise RuntimeError("actual CPU control executable runtime dependency scan failed")
        output = completed.stdout.decode()
        if "not found" in output:
            raise RuntimeError("actual CPU control executable has unresolved runtime dependencies")
        (result / (binary.name + ".ldd.txt")).write_bytes(completed.stdout)
        reads.append(result / (binary.name + ".ldd.txt"))
        for name in re.findall(r"(?:=>\s*)?(/[^\s()]+)", output):
            path = Path(name).resolve(strict=True)
            data = regular_bytes(path)
            runtime_dependencies.append({"executable": str(binary), "dependency": name,
                "resolved_path": str(path), "bytes": len(data), "sha256": digest(data)})
            reads.append(path)
    runtime_binding = result / "runtime-library-bindings.json"
    runtime_binding.write_text(json.dumps(runtime_dependencies, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    reads.append(runtime_binding)
    controls = result / "native-controls"
    controls.mkdir(exist_ok=False)
    os.environ["RVP_NATIVE_OUTPUT_ROOT"] = str(controls)
    os.environ["RVP_INITIALIZER_BINARY"] = str(initializer[0])
    os.environ["RVP_BACKEND_BINARY"] = str(backend[0])
    reads = list(dict.fromkeys(path.resolve() for path in reads))
    before = source_snapshot(reads)
    before_result = result_snapshot(result)
    junit = result / "selected.xml"
    selections = manifest["selected_modules"]
    command = [sys.executable, "-m", "pytest", "--noconftest", "-c", "/dev/null", "--rootdir", str(ROOT),
        "--import-mode=importlib", "-o", "addopts=", "-p", "no:cacheprovider", "-q", f"--junitxml={junit}",
        *[str(ROOT / name) for name in selections]]
    sys.path.insert(0, str(carrier_root))
    sys.path.insert(1, str(carrier_root / "scripts" / "vidya"))
    from scripts.ci import native_conformance as carrier
    if Path(carrier.__file__).resolve() != carrier_root / "scripts/ci/native_conformance.py":
        raise RuntimeError("native carrier import identity differs")
    record = carrier.capture_fixture_execution(argv=command, cwd=ROOT, junit=junit, output=result / "native",
        repositories={"recipe": ROOT, **roots}, read_paths=reads, selections=selections)
    if result_snapshot(build, exclude_status=False) != build_before_capture:
        raise RuntimeError("source-built output tree changed during native capture")
    after_capture = source_snapshot(reads)
    if after_capture != before:
        raise RuntimeError("source bytes changed during native execution")
    summary = record.get("summary")
    cases = summary.get("cases") if isinstance(summary, dict) else None
    expected = collections.Counter((row["classname"], row["name"]) for row in manifest["expected_cases"])
    if not isinstance(cases, list) or collections.Counter((row["classname"], row["name"]) for row in cases) != expected:
        (result / "native-outcome.json").write_text(json.dumps({"fixture_execution_conformant": None,
            "diagnostic": "native case identities differ from the three-case manifest", "record_diagnostic": record.get("diagnostic"),
            "observed_cases": cases, "receipt": "native/receipt.json"}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        return 1
    before_grade_result = result_snapshot(result)
    from scripts.vidya.adapters import ci_conformance
    from claim_tuple import grade
    rows = ci_conformance.native_rows(result / "native/receipt.json")
    if len(rows) != 1:
        (result / "native-outcome.json").write_text(json.dumps({"fixture_execution_conformant": record.get("fixture_execution_conformant"),
            "diagnostic": "original receipt yielded no projectable row", "receipt": "native/receipt.json"}, sort_keys=True) + "\n", encoding="utf-8")
        return 1
    claim = ci_conformance.project_ci_conformance(rows[0])
    judgment = grade(claim)
    after_grade = source_snapshot(reads)
    after_grade_result = result_snapshot(result)
    if result_snapshot(build, exclude_status=False) != build_before_capture:
        raise RuntimeError("source-built output tree changed during shared grade")
    if before != after_grade or before_grade_result != after_grade_result:
        raise RuntimeError("source or original result artifacts changed during shared grade")
    (result / "custody-snapshots.json").write_text(json.dumps({"source_before_build": source_before_build, "build_before_capture": build_before_capture, "source_before_capture": before,
        "source_after_capture": after_capture, "source_after_grade": after_grade,
        "result_before_capture": before_result, "result_before_grade": before_grade_result,
        "result_after_grade": after_grade_result, "excluded_mutable_status": "root status.json only"}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (result / "shared-grade.json").write_text(json.dumps({"receipt_sha256": rows[0]["receipt_sha256"],
        "value": claim.value, "grade": list(judgment)}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"fixture_execution_conformant": record.get("fixture_execution_conformant"), "case_count": len(cases), "grade": list(judgment)}))
    return 0 if record.get("fixture_execution_conformant") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
