"""Capture DCP2 finite-score source controls through the existing native CI carrier."""
from __future__ import annotations

from collections import Counter
import ast
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import stat
import subprocess
import sys
import tomllib

ROOT_CONTEXT_PIN = "f71cc137fc3bc17325d6255884eaed7e9dee98c9"
CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
APP_PIN = "b21e45af6fea25340bddf15e28b633ccc99b0604"
APP_PARENT_PIN = "6c050e783b05a5c7354ee1b61a6a90227664b9fe"
PYTHON_PIN = "3.13.15"
LITERAL_BRANCH = "codex/ni08-dcp2-colgrep-recipe-20261007"
SELECTION = "tests/unit/test_context_discovery.py"
WORKFLOW = ".github/workflows/ni08-dcp2-colgrep-score-capture.yml"
RUNNER = "scripts/ci/ni08_dcp2_colgrep_capture.py"
SOURCE_MAP = "scripts/ci/ni08_dcp2_colgrep_source_map.json"
EXPECTED_CASES = "scripts/ci/ni08_dcp2_colgrep_expected_cases.json"
REQUIREMENTS = "scripts/ci/ni08_dcp2_colgrep_requirements.txt"
RESULT_NAME = "ni08-dcp2-colgrep-score"
RUNNER_CONTEXT = "ubuntu-24.04"
EXECUTION_CONTEXT = "finite-score-injected-search-no-colgrep-or-model"
INSTALL_COMMAND = (
    'python -m venv "$RUNNER_TEMP/ni08-dcp2-colgrep-score/venv" && '
    '"$RUNNER_TEMP/ni08-dcp2-colgrep-score/venv/bin/python" -m pip install '
    "--no-deps --only-binary=:all: --require-hashes -r "
    "recipe/scripts/ci/ni08_dcp2_colgrep_requirements.txt"
)
CONFIG_NAMES = {
    "pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini", "uv.lock",
    "requirements.txt", "requirements-dev.txt", "requirements-test.txt",
}
CONFIG_SUFFIXES = {".toml", ".ini", ".cfg", ".yaml", ".yml"}
ROOT_BINDINGS = {
    "handoffs/active/delegation-context-preassembly.md": "eab9dd6a3474d298ad2c6dabfb02b5965c6abc8d56b7c6f2d36e4cafad0d8cde",
    "scripts/vidya/adapters/README.md": "954a0aaf163c44880bef842e48b5798d9662be5a8313e52096f661454dcc7338",
    "handoffs/active/vidya-belief-substrate-program.md": "b5da633e12fe71e9be31b54d680a36b0fed2babe5e699e37d2a2ddfdfd6844f0",
}
CARRIER_READS = (
    "scripts/ci/native_conformance.py",
    "scripts/vidya/adapters/ci_conformance.py",
    "scripts/vidya/claim_tuple.py",
)


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def regular_file(repo: Path, relative: str) -> Path:
    path = repo
    for part in PurePosixPath(relative).parts:
        path = path / part
        if path.is_symlink():
            raise RuntimeError(f"declared input traverses symlink: {relative}")
    if not path.is_file() or not stat.S_ISREG(path.lstat().st_mode):
        raise RuntimeError(f"declared input missing or nonregular: {relative}")
    tree = git(repo, "ls-tree", "HEAD", "--", relative).split("\t", 1)[0].split()
    if not tree or tree[0] not in {"100644", "100755"}:
        raise RuntimeError(f"declared input is not a regular tracked Git file: {relative}")
    return path.absolute()


def source_config_paths(repo: Path) -> list[Path]:
    """Return only regular source/config leaves; symlink topology is bound by Git pins/maps."""
    result = []
    for relative in git(repo, "ls-files", "-z").split("\0"):
        if not relative:
            continue
        pure = PurePosixPath(relative)
        if not (relative.endswith(".py") or pure.name in CONFIG_NAMES or pure.suffix in CONFIG_SUFFIXES):
            continue
        candidate = repo / relative
        if candidate.is_symlink():
            continue
        result.append(regular_file(repo, relative))
    return result


def sha256_path(path: Path) -> str:
    if path.is_symlink() or not path.is_file() or not stat.S_ISREG(path.lstat().st_mode):
        raise RuntimeError(f"evidence input is missing/nonregular: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_clean_pin(label: str, repo: Path, expected: str) -> str:
    pin = git(repo, "rev-parse", "HEAD")
    if pin != expected:
        raise RuntimeError(f"{label} pin differs: {pin}")
    if git(repo, "status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError(f"{label} checkout is not clean")
    return pin


def app_envelope_matches(app: Path, source_map: dict) -> list[Path]:
    records = source_map["APP_full_source_config_envelope"]["files"]
    by_path = {row["path"]: row for row in records}
    all_tracked = git(app, "ls-files", "-z").split("\0")
    selected = [name for name in all_tracked if name and
                (name.endswith(".py") or PurePosixPath(name).name in CONFIG_NAMES
                 or PurePosixPath(name).suffix in CONFIG_SUFFIXES)]
    if set(selected) != set(by_path) or len(selected) != len(records):
        raise RuntimeError("APP Python/config source envelope path set differs from frozen map")
    tree_rows = {}
    raw = subprocess.check_output(["git", "-C", str(app), "ls-tree", "-r", "-z", "HEAD"])
    for row in raw.split(b"\0"):
        if not row:
            continue
        meta, path = row.split(b"\t", 1)
        mode, kind, oid = meta.decode().split()
        name = path.decode()
        if name in by_path:
            tree_rows[name] = (mode, oid)
    for name, expected in by_path.items():
        if tree_rows.get(name) != (expected["mode"], expected["blob"]):
            raise RuntimeError(f"APP tracked blob/mode differs from static map: {name}")
        path = app / name
        if expected["mode"] == "120000":
            if not path.is_symlink():
                raise RuntimeError(f"APP source/config symlink topology differs: {name}")
            target = os.readlink(path).encode("utf-8")
            if len(target) != expected["size"] or hashlib.sha256(target).hexdigest() != expected["sha256"]:
                raise RuntimeError(f"APP source/config symlink target differs: {name}")
        else:
            if sha256_path(path) != expected["sha256"]:
                raise RuntimeError(f"APP source/config bytes differ from static map: {name}")
    return source_config_paths(app)


def verify_frozen_envelope(repo: Path, envelope: dict, pin: str, *, recipe_self_excludes: str | None = None) -> None:
    """Compare complete source/config path, mode and Git blob envelope at an exact commit."""
    envelope_pin=envelope.get("git_pin", envelope.get("base_git_pin"))
    if recipe_self_excludes is None and envelope_pin != pin:
        raise RuntimeError("source-map envelope Git pin differs")
    if recipe_self_excludes is not None and subprocess.run(["git","-C",str(repo),"merge-base","--is-ancestor",envelope_pin,pin]).returncode != 0:
        raise RuntimeError("recipe source/config envelope base is not an ancestor of the exact recipe commit")
    expected = {row["path"]:row for row in envelope.get("files",[])}
    raw = subprocess.check_output(["git","-C",str(repo),"ls-tree","-r","-z",pin])
    actual = {}
    for item in raw.split(b"\0"):
        if not item: continue
        meta,name=item.split(b"\t",1); mode,kind,oid=meta.decode().split(); name=name.decode()
        pure=PurePosixPath(name)
        if not (name.endswith(".py") or pure.name in CONFIG_NAMES or pure.suffix in CONFIG_SUFFIXES): continue
        if name==recipe_self_excludes: continue
        actual[name]=(mode,oid)
    if recipe_self_excludes is not None and recipe_self_excludes in actual:
        actual.pop(recipe_self_excludes)
    if set(actual)!=set(expected): raise RuntimeError("complete source/config envelope path set differs")
    for name,row in expected.items():
        wanted=(row.get("mode"),row.get("candidate_git_blob",row.get("blob")))
        if actual[name]!=wanted: raise RuntimeError(f"source/config Git blob/mode differs: {name}")
    if len(actual)!=envelope.get("file_count"): raise RuntimeError("source/config envelope count differs")

def derive_case_ids(test_path: Path) -> list[tuple[str, str]]:
    """Resolve pytest identities from AST names and literal IDs only; never evaluate values."""
    tree = ast.parse(test_path.read_text(encoding="utf-8"))
    assembly_path = test_path.parents[2] / "src" / "context_assembly.py"
    assembly = ast.parse(assembly_path.read_text(encoding="utf-8"))
    constants = {}
    for node in assembly.body:
        if isinstance(node, ast.ClassDef) and node.name == "InclusionMode":
            for child in node.body:
                if (isinstance(child, ast.Assign) and len(child.targets) == 1
                        and isinstance(child.targets[0], ast.Name)
                        and isinstance(child.value, ast.Constant)
                        and isinstance(child.value.value, str)):
                    constants["InclusionMode." + child.targets[0].id] = child.value.value

    def id_value(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, float, bool)):
            return str(node.value)
        if isinstance(node, ast.Attribute):
            return constants.get(ast.unparse(node))
        return None

    rows = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not node.name.startswith("test_"):
            continue
        parameter = next((item for item in node.decorator_list
                          if isinstance(item, ast.Call) and ast.unparse(item.func).endswith("parametrize")), None)
        if parameter is None:
            rows.append(("tests.unit.test_context_discovery", node.name))
            continue
        ids = None
        for keyword in parameter.keywords:
            if keyword.arg == "ids" and isinstance(keyword.value, (ast.Tuple, ast.List)):
                if all(isinstance(item, ast.Constant) and isinstance(item.value, str) for item in keyword.value.elts):
                    ids = [item.value for item in keyword.value.elts]
        values = parameter.args[1] if len(parameter.args) > 1 else None
        if ids is None and isinstance(values, (ast.Tuple, ast.List)):
            literal_ids = [id_value(item) for item in values.elts]
            if all(item is not None for item in literal_ids):
                ids = literal_ids
        if ids is None:
            raise RuntimeError(f"could not statically bind pytest IDs for {node.name}")
        rows.extend(("tests.unit.test_context_discovery", node.name + "[" + item + "]") for item in ids)
    return rows


def verify_locked_requirements(app: Path, requirements: Path, source_map: dict) -> dict[str, str]:
    lock_path = regular_file(app, "uv.lock")
    lock_bytes = lock_path.read_bytes()
    if hashlib.sha256(lock_bytes).hexdigest() != source_map["dependencies"]["uv_lock_sha256"]:
        raise RuntimeError("APP uv.lock differs from frozen source map")
    lock = tomllib.loads(lock_bytes.decode("utf-8"))
    records = {row["name"].lower().replace("_", "-"): row for row in lock["package"]}
    declared = {}
    hashes = {}
    current = None
    for line in requirements.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        import re
        match = re.match(r"^([A-Za-z0-9_.-]+)==([^\s]+)", stripped)
        if match:
            current = match.group(1).lower().replace("_", "-")
            declared[current] = match.group(2)
            hashes[current] = set()
        if current:
            hashes[current].update(re.findall(r"--hash=sha256:([0-9a-f]{64})", stripped))
    # Recompute the full platform-independent closure from the one declared direct root: pytest.
    todo = ["pytest"]
    expected = set()
    while todo:
        name = todo.pop().lower().replace("_", "-")
        if name in expected:
            continue
        row = records.get(name)
        if not row:
            raise RuntimeError(f"missing locked dependency {name}")
        expected.add(name)
        for dependency in row.get("dependencies", []):
            marker = dependency.get("marker", "").replace('"', "'")
            if "sys_platform == 'win32'" in marker:
                continue
            if "extra ==" in marker:
                raise RuntimeError(f"unresolved extra-conditioned dependency: {name}")
            todo.append(dependency["name"])
    if set(declared) != expected:
        raise RuntimeError("requirements do not equal the complete pytest lock closure")
    for name in sorted(expected):
        row = records[name]
        allowed = {wheel["hash"].removeprefix("sha256:") for wheel in row.get("wheels", [])}
        if not allowed or hashes[name] != allowed or declared[name] != row["version"]:
            raise RuntimeError(f"locked version or all-wheel hashes differ for {name}")
        if importlib.metadata.version(name) != row["version"]:
            raise RuntimeError(f"installed {name} differs from APP uv.lock")
    if hashlib.sha256(requirements.read_bytes()).hexdigest() != source_map["dependencies"]["requirements_sha256"]:
        raise RuntimeError("requirements bytes differ from static map")
    return {name: declared[name] for name in sorted(expected)}



def hash_regular(path: Path) -> str:
    """Hash one no-follow regular input and reject replacement during the read."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise RuntimeError(f"custody input is not a single-link regular file: {path}")
        digest = hashlib.sha256()
        total = 0
        while True:
            data = os.read(fd, 1024 * 1024)
            if not data:
                break
            digest.update(data)
            total += len(data)
        after = os.fstat(fd)
        identity = lambda row: (row.st_dev, row.st_ino, row.st_mode, row.st_size, row.st_nlink, row.st_mtime_ns, row.st_ctime_ns)
        if identity(before) != identity(after) or total != after.st_size:
            raise RuntimeError(f"custody input changed while hashing: {path}")
        if identity(after) != identity(path.lstat()):
            raise RuntimeError(f"custody input path changed while hashing: {path}")
        return digest.hexdigest()
    finally:
        os.close(fd)

def typed_tree(root: Path, *, omit_status: bool = True) -> dict:
    """Sorted lstat inventory. Symlinks are opaque metadata and are never traversed."""
    if root.is_symlink() or not stat.S_ISDIR(root.lstat().st_mode):
        raise RuntimeError(f"result root is not a real directory: {root}")
    found = {".": {"kind": "directory"}}
    def walk(directory: Path) -> None:
        for entry in sorted(os.scandir(directory), key=lambda row: row.name):
            path = Path(entry.path)
            mode = entry.stat(follow_symlinks=False).st_mode
            rel = path.relative_to(root).as_posix()
            if omit_status and rel == "status.json":
                continue
            if stat.S_ISLNK(mode):
                target = os.readlink(path).encode("utf-8", "surrogateescape")
                found[rel] = {"kind": "symlink_opaque", "target_bytes": len(target), "target_sha256": hashlib.sha256(target).hexdigest()}
            elif stat.S_ISDIR(mode):
                found[rel + "/"] = {"kind": "directory"}
                walk(path)
            elif stat.S_ISREG(mode):
                found[rel] = {"kind": "regular", "bytes": path.lstat().st_size, "sha256": hash_regular(path)}
            else:
                raise RuntimeError(f"result tree contains a special file: {rel}")
    walk(root)
    return found

def stable_digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def durable_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    if temporary.exists() or temporary.is_symlink() or path.exists() or path.is_symlink():
        raise RuntimeError(f"refusing to overwrite custody record: {path.name}")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, sort_keys=True, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)

def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, carrier, app = (workspace / name for name in ("recipe", "carrier", "app"))
    result = runner_temp / RESULT_NAME / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status = {"state": "preparing", "exit_code": None, "native_conformance": None, "native_receipt_state": "no_receipt", "capture_started": False}
    boundary = "setup"
    error_record = None
    read_paths = []
    source_before = None
    result_before = None
    result_after_capture = None
    receipt = None
    exit_code = None
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
    try:
        expected_env = {
            "DCP2_RUNNER_CONTEXT": RUNNER_CONTEXT,
            "DCP2_EXECUTION_CONTEXT": EXECUTION_CONTEXT,
            "DCP2_INSTALL_COMMAND": INSTALL_COMMAND,
            "APP_PIN": APP_PIN,
            "ROOT_CARRIER_PIN": CARRIER_PIN,
            "ROOT_CONTEXT_PIN": ROOT_CONTEXT_PIN,
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTEST_ADDOPTS": "",
            "PYTEST_PLUGINS": "",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "ORCHESTRATOR_MOCK_MODE": "1",
            "CI": "true",
            "PYTHONUNBUFFERED": "1",
            "PYTHONNOUSERSITE": "1",
        }
        for key, value in expected_env.items():
            if os.environ.get(key) != value:
                raise RuntimeError(f"{key} differs from frozen recipe")
        if platform.python_version() != PYTHON_PIN:
            raise RuntimeError(f"Python runtime differs: {platform.python_version()}")
        expected_venv = (runner_temp / RESULT_NAME / "venv").resolve()
        if sys.prefix == sys.base_prefix or Path(sys.prefix).resolve() != expected_venv:
            raise RuntimeError("capture interpreter is not the isolated reviewed venv")
        if os.environ.get("DCP2_INSTALL_COMMAND") != INSTALL_COMMAND:
            raise RuntimeError("dependency install command differs")
        absent_binary = Path(os.environ["REPL_COLGREP_BIN"])
        if not absent_binary.is_absolute() or absent_binary.exists() or os.access(absent_binary, os.X_OK):
            raise RuntimeError("REPL_COLGREP_BIN must name a verified absent runner-temp path")
        if shutil.which("colgrep") is not None:
            raise RuntimeError("a ColGREP executable is present on PATH")
        # No endpoint or credential is permitted in this injected-input fixture recipe.
        for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_BASE_URL", "ANTHROPIC_BASE_URL"):
            if os.environ.get(key):
                raise RuntimeError(f"unexpected model endpoint/credential environment: {key}")

        recipe_pin = git(recipe, "rev-parse", "HEAD")
        carrier_pin = check_clean_pin("carrier", carrier, CARRIER_PIN)
        app_pin = check_clean_pin("APP", app, APP_PIN)
        if subprocess.run(["git", "-C", str(app), "merge-base", "--is-ancestor", APP_PARENT_PIN, APP_PIN]).returncode != 0:
            raise RuntimeError("declared APP source parent is not in exact source ancestry")
        if Path(os.environ.get("PYTHONPATH", "")).resolve() != app.resolve():
            raise RuntimeError("PYTHONPATH is not the exact APP checkout")
        if os.environ.get("GITHUB_REF") != "refs/heads/" + LITERAL_BRANCH or os.environ.get("GITHUB_EVENT_NAME") != "push":
            raise RuntimeError("workflow trigger is not the exact reviewed literal branch push")
        if recipe_pin != os.environ.get("GITHUB_SHA"):
            raise RuntimeError("recipe checkout does not match triggering GITHUB_SHA")
        if git(recipe, "status", "--porcelain", "--untracked-files=all"):
            raise RuntimeError("recipe checkout is not clean")
        if subprocess.run(["git", "-C", str(recipe), "merge-base", "--is-ancestor", ROOT_CONTEXT_PIN, "HEAD"]).returncode != 0:
            raise RuntimeError("recipe does not descend from the enrolled ROOT context")

        workflow = regular_file(recipe, WORKFLOW)
        runner = regular_file(recipe, RUNNER)
        source_map_path = regular_file(recipe, SOURCE_MAP)
        expected_path = regular_file(recipe, EXPECTED_CASES)
        requirements = regular_file(recipe, REQUIREMENTS)
        source_map = json.loads(source_map_path.read_text(encoding="utf-8"))
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        envelopes = source_map["source_readset_contract"]
        verify_frozen_envelope(recipe, envelopes["ROOT_enrolled_context_source_config_envelope"], ROOT_CONTEXT_PIN)
        verify_frozen_envelope(carrier, envelopes["existing_carrier_source_config_envelope"], CARRIER_PIN)
        verify_frozen_envelope(recipe, envelopes["recipe_source_config_envelope"], recipe_pin, recipe_self_excludes=SOURCE_MAP)
        if source_map["binding"]["ROOT_parent"] != ROOT_CONTEXT_PIN:
            raise RuntimeError("static map ROOT parent differs")
        if (source_map["binding"]["APP_source"] != APP_PIN
                or source_map["binding"]["APP_source_parent"] != APP_PARENT_PIN
                or source_map["binding"]["existing_carrier"] != CARRIER_PIN):
            raise RuntimeError("static map APP/carrier pin differs")
        for relative, digest in ROOT_BINDINGS.items():
            path = regular_file(recipe, relative)
            if sha256_path(path) != digest:
                raise RuntimeError(f"ROOT enrollment/context bytes differ: {relative}")

        app_paths = app_envelope_matches(app, source_map)
        expected_ids = [(row["classname"], row["name"]) for row in expected["case_identities"]]
        mapped_ids = [(row["classname"], row["name"]) for row in source_map["AST"]["case_identities"]]
        actual_ids = derive_case_ids(regular_file(app, SELECTION))
        if (Counter(actual_ids) != Counter(expected_ids) or Counter(mapped_ids) != Counter(expected_ids)
                or len(actual_ids) != 25):
            raise RuntimeError("whole-module AST case identities differ from frozen manifest")
        if (expected["case_count"] != 25 or expected["app_pin"] != APP_PIN
                or expected.get("parameter_values_evaluated") is not False
                or source_map["AST"].get("param_values_evaluated") is not False):
            raise RuntimeError("expected case manifest pin/count/static-identity boundary differs")
        package_versions = verify_locked_requirements(app, requirements, source_map)
        installed = {dist.metadata.get("Name", "").lower().replace("_", "-")
                     for dist in importlib.metadata.distributions()}
        if installed != set(package_versions) | {"pip"}:
            raise RuntimeError("venv contains packages outside the locked closure and pip bootstrap")

        install_log = result / "dependency-install.log"
        if not install_log.is_file() or install_log.is_symlink():
            raise RuntimeError("original dependency installation log is missing or symlinked")
        freeze = result / "pip-freeze.txt"
        freeze.write_bytes(subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"]))
        environment = result / "runner-environment.json"
        environment.write_text(json.dumps({
            "python": sys.version, "platform": platform.platform(),
            "runner_context": RUNNER_CONTEXT, "execution_context": EXECUTION_CONTEXT,
            "repositories": {"recipe": recipe_pin, "carrier": carrier_pin, "app": app_pin},
            "selected_test": SELECTION, "case_count": 25,
            "install_command": INSTALL_COMMAND, "dependency_versions": package_versions,
            "source_map_sha256": sha256_path(source_map_path),
            "requirements_sha256": sha256_path(requirements),
            "environment": {key: os.environ.get(key) for key in (
                "CI", "ORCHESTRATOR_MOCK_MODE", "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTEST_ADDOPTS",
                "PYTEST_PLUGINS", "PYTHONDONTWRITEBYTECODE", "PYTHONHASHSEED", "PYTHONPATH",
                "REPL_COLGREP_BIN", "DCP2_RUNNER_CONTEXT", "DCP2_EXECUTION_CONTEXT",
            )},
            "scope": "Whole exact synthetic source module; parser and direct-hit routes receive injected fixtures. No ColGREP executable, live search, model, embedding, API endpoint, index, corpus, performance or inference.",
        }, sort_keys=True, indent=2) + "\n", encoding="utf-8")

        junit = result / "original-junit.xml"
        native = result / "native"
        stdout_path = result / "original-runner-stdout.log"
        stderr_path = result / "original-runner-stderr.log"
        command_record = result / "original-command.json"
        if any(path.exists() for path in (junit, native, stdout_path, stderr_path, command_record)):
            raise RuntimeError("refusing to overwrite original capture artifacts")
        read_paths = [
            workflow, runner, source_map_path, expected_path, requirements, install_log,
            regular_file(recipe, "README-DCP2-private-review.md"),
            regular_file(recipe, "handoffs/active/delegation-context-preassembly.md"),
            regular_file(recipe, "scripts/vidya/adapters/README.md"),
            regular_file(recipe, "handoffs/active/vidya-belief-substrate-program.md"),
            *source_config_paths(recipe), *source_config_paths(carrier), *app_paths,
            *(regular_file(carrier, item) for item in CARRIER_READS),
            regular_file(app, "uv.lock"), freeze, environment, command_record,
        ]
        junit_arg = str(junit)
        producer = [sys.executable, str(carrier / "scripts/ci/native_conformance.py"),
                    "--cwd", str(app), "--junit", junit_arg, "--output", str(native),
                    "--repo", f"recipe={recipe}", "--repo", f"carrier={carrier}", "--repo", f"app={app}"]
        for path in dict.fromkeys(item.resolve() for item in read_paths):
            producer.extend(("--read-path", str(path)))
        producer.extend(("--select", SELECTION))
        test_command = [sys.executable, "-m", "pytest", "-c", "/dev/null", "--rootdir", str(app),
                        "--noconftest", "-o", "addopts=", "-p", "no:cacheprovider", "-q",
                        SELECTION, f"--junitxml={junit_arg}"]
        command_record.write_text(json.dumps({"producer_argv": producer, "test_argv": test_command,
                                              "cwd": str(app), "capture_read_paths": [str(path) for path in dict.fromkeys(item.resolve() for item in read_paths)], "environment": {
                                                  "PYTHONPATH": str(app),
                                                  "REPL_COLGREP_BIN": str(absent_binary),
                                              }}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        boundary = "pre_capture_inventory"
        source_before = {str(path): hash_regular(path) for path in dict.fromkeys(p.resolve() for p in read_paths)}
        result_before = typed_tree(result)
        durable_json(result / "pre-capture-custody.json", {
            "phase": "before_native_invocation", "source_inventory": source_before,
            "source_inventory_sha256": stable_digest(source_before),
            "typed_result_tree": result_before, "typed_result_tree_sha256": stable_digest(result_before),
            "status_excluded_from_tree": True, "scope": "regular source/config inputs and typed existing result tree; symlinks opaque"})
        boundary = "capture"
        status.update(state="running", capture_started=True, repositories={"recipe": recipe_pin, "carrier": carrier_pin, "app": app_pin})
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
        run_env = dict(os.environ, PYTHONPATH=str(app), REPL_COLGREP_BIN=str(absent_binary))
        completed = subprocess.run([*producer, "--", *test_command], cwd=app, env=run_env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        stdout_path.write_bytes(completed.stdout)
        stderr_path.write_bytes(completed.stderr)
        exit_code = completed.returncode
        receipt_path = native / "receipt.json"
        if not receipt_path.is_file() or receipt_path.is_symlink():
            status.update(state="capture_failed", exit_code=exit_code or 1, native_receipt_state="no_receipt")
            boundary = "missing_receipt"
            raise RuntimeError("native producer did not create a regular original receipt")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        metric_value = receipt.get("fixture_execution_conformant")
        status["native_receipt_state"] = ("native_null" if metric_value is None else "native_true" if metric_value is True else "native_false" if metric_value is False else "native_invalid_type")
        summary = receipt.get("summary") or {}
        counts = summary.get("counts") or {}
        rows = summary.get("cases") or []
        actual = [(row.get("classname"), row.get("name")) for row in rows]
        cases_ok = (Counter(actual) == Counter(expected_ids) and len(actual) == 25
                    and counts.get("collected") == 25 and counts.get("executed") == 25
                    and counts.get("skipped") == 0 and counts.get("failure") == 0 and counts.get("error") == 0)
        # Hash source, environment, runner outputs and native originals before shared grading.
        def originals():
            native_files = sorted(native.rglob("*"))
            if any(path.is_symlink() for path in native_files):
                raise RuntimeError("native original tree contains symlink")
            outputs = [path for path in native_files if path.is_file()]
            originals_list = list(dict.fromkeys([*read_paths, freeze, environment, command_record,
                                                  junit, stdout_path, stderr_path, *outputs]))
            return originals_list
        boundary = "post_capture_inventory"
        original_before_paths = originals()
        original_before = {str(path): hash_regular(path) for path in original_before_paths}
        source_after_capture = {str(path): hash_regular(path) for path in dict.fromkeys(p.resolve() for p in read_paths)}
        result_after_capture = typed_tree(result)
        durable_json(result / "post-capture-custody.json", {
            "phase": "after_capture_before_grade", "source_before_capture": source_before,
            "source_after_capture": source_after_capture, "source_stable": source_before == source_after_capture,
            "source_after_capture_sha256": stable_digest(source_after_capture),
            "typed_result_tree_before_capture": result_before, "typed_result_tree_after_capture_before_grade": result_after_capture,
            "typed_result_tree_after_capture_sha256": stable_digest(result_after_capture),
            "native_receipt_state": status["native_receipt_state"], "native_metric_value": metric_value,
            "original_exit_code": exit_code, "exact_case_set": cases_ok,
            "inventory_self_exclusion":"this custody record is excluded from its embedded tree; the following result tree includes it"})
        result_after_capture = typed_tree(result)
        boundary = "shared_grade"
        if metric_value is None:
            projected = ()
            grade_rows = []
        else:
            sys.path.insert(0, str(carrier))
            sys.path.insert(0, str(carrier / "scripts/vidya"))
            from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
            from claim_tuple import grade
            projected = native_rows(receipt_path)
            if len(projected) != 1:
                raise RuntimeError("existing CI adapter did not project exactly one non-NULL native row")
            claim = project_ci_conformance(projected[0])
            quality, trust, reasons = grade(claim)
            grade_rows = [{"measurement_id": claim.measurement_id, "source_kind": claim.source_kind, "binding_kind": claim.binding_kind, "Q": quality, "T": trust, "reasons": reasons}]
        original_after_paths = originals()
        original_after = {str(path): sha256_path(path) for path in original_after_paths}
        if [str(path) for path in original_after_paths] != [str(path) for path in original_before_paths]:
            raise RuntimeError("shared grade changed original evidence membership")
        if original_after != original_before:
            raise RuntimeError("shared grade changed original source/result/error/native evidence")
        result_after_grade = typed_tree(result)
        source_after_grade = {str(path): hash_regular(path) for path in dict.fromkeys(p.resolve() for p in read_paths)}
        if source_before != source_after_capture or source_after_capture != source_after_grade:
            raise RuntimeError("regular source/config readset changed across capture or grading")
        if result_after_capture != result_after_grade:
            raise RuntimeError("typed result/error tree changed during shared grading")
        durable_json(result / "shared-grade-custody.json", {
            "phase": "after_existing_shared_grade", "source_before_capture": source_before,
            "source_after_grade": source_after_grade, "source_stable": source_before == source_after_grade,
            "source_after_grade_sha256": stable_digest(source_after_grade),
            "typed_result_tree_before_capture": result_before, "typed_result_tree_after_capture_before_grade": result_after_capture,
            "typed_result_tree_after_grade": result_after_grade, "typed_result_tree_after_grade_sha256": stable_digest(result_after_grade),
            "native_receipt_state": status["native_receipt_state"], "native_metric_value": metric_value,
            "grade_projection": grade_rows, "grade_projection_expected": metric_value is not None,
            "new_grade_authored": False})
        fixture_metric = receipt.get("fixture_execution_conformant")
        passed = (exit_code == 0 and fixture_metric is True and cases_ok)
        status.update(state="passed" if passed else "failed", exit_code=0 if passed else (exit_code or 1),
                      fixture_execution_conformant=fixture_metric, junit_counts=counts,
                      exact_case_set=cases_ok, expected_case_count=25,
                      shared_grade=grade_rows, grade_projection_expected=metric_value is not None)
        return 0 if passed else (exit_code or 1)
    except Exception as exc:
        error_record = {"stage": boundary, "capture_started": status.get("capture_started", False),
                        "native_receipt_state": status.get("native_receipt_state", "no_receipt"),
                        "native_metric_value": (receipt.get("fixture_execution_conformant") if receipt else None),
                        "error_type": type(exc).__name__, "error_message": str(exc),
                        "original_exit_code": exit_code, "receipt_present": bool(receipt),
                        "source_before_capture": source_before, "source_before_capture_sha256": stable_digest(source_before) if source_before is not None else None,
                        "typed_result_tree_before_capture": result_before, "typed_result_tree_after_capture_before_grade": result_after_capture,
                        "proposition_invented": False}
        status.update(state="capture_failed", exit_code=1, error_type=type(exc).__name__, error_message=str(exc),
                      failure_stage=boundary, error_custody_state="pending_finalized")
        return 1
    finally:
        try:
            if error_record is not None and not (result / "error-custody.json").exists():
                try:
                    source_current = {str(path): hash_regular(path) for path in dict.fromkeys(p.resolve() for p in read_paths) if p.is_file() and not p.is_symlink()}
                    tree_current = typed_tree(result)
                    error_record.update(phase="after_error_before_final_status", source_after_error=source_current,
                                        source_after_error_sha256=stable_digest(source_current),
                                        typed_result_tree_after_error=tree_current,
                                        typed_result_tree_after_error_sha256=stable_digest(tree_current),
                                        status_excluded=True, error_record_self_excluded=True)
                except Exception as custody_exc:
                    error_record["custody_snapshot_error"] = type(custody_exc).__name__ + ": " + str(custody_exc)
                durable_json(result / "error-custody.json", error_record)
                status["error_custody_state"] = "written_before_final_status; inventory excludes mutable status and its own final error record"
        except Exception as custody_exc:
            status["error_custody_state"] = "failed"
            status["error_custody_error"] = type(custody_exc).__name__ + ": " + str(custody_exc)
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
