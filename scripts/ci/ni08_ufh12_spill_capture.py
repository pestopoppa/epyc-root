"""Capture UFH12 spill-summary context controls through ROOT's existing native CI carrier."""
from __future__ import annotations

from collections import Counter
import ast
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import tomllib

# Exact MAIN prospective enrollment; publication/capture still require final independent review.
ROOT_CONTEXT_PIN = "8b540512ed8017fc0ed80ea8f5d3a0381fc08ead"
ROOT_ENROLLMENT_READY = True
ROOT_BINDINGS: dict[str, str] = {'handoffs/active/tool-output-compression.md': '2836a06fb1279d0d8c535e5f1a062d24f3dcf2377e894c225f3a385704552614', 'scripts/vidya/adapters/README.md': '852c6968e643237ad9af4260baddeabebfbb29eb51ebf0e7cf1e2f67de3a8050', 'handoffs/active/vidya-belief-substrate-program.md': '00d4f916866d94e4c42f0a75ab70f60d37427b7ab2bf005d7041971b34d4ccf9'}
CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
APP_PIN = "63399d6f1a7ec5caea6ef31ee898c14e977e85c2"
APP_PARENT_PIN = "b87998e3b5a0cbb9da36c8db9fd2fcfbb69aba0d"
PYTHON_PIN = "3.13.15"
LITERAL_BRANCH = "codex/ni08-ufh12-spill-budget-recipe-20261007"
SELECTION = "tests/unit/test_repl_spill_output.py"
WORKFLOW = ".github/workflows/ni08-ufh12-spill-summary-capture.yml"
RUNNER = "scripts/ci/ni08_ufh12_spill_capture.py"
SOURCE_MAP = "scripts/ci/ni08_ufh12_spill_source_map.json"
FUNCTION_GRAPH = "scripts/ci/ni08_ufh12_executed_function_source_graph.json"
EXPECTED_CASES = "scripts/ci/ni08_ufh12_spill_expected_cases.json"
CLOSURE = "scripts/ci/ni08_ufh12_spill_import_closure.json"
REQUIREMENTS = "scripts/ci/ni08_ufh12_spill_requirements.txt"
REVIEW_NOTE = "README-UFH12-private-review.md"
RESULT_NAME = "ni08-ufh12-spill-summary"
SPILL_ROOT = "/mnt/raid0/llm/tmp"
SPILL_ROOT_SETUP = "spill-root-setup.json"
RUNNER_CONTEXT = "ubuntu-24.04"
EXECUTION_CONTEXT = "spill-summary-budget-injected-mock-worker-no-model"
INSTALL_COMMAND = (
    'python -m venv "$RUNNER_TEMP/ni08-ufh12-spill-summary/venv" && '
    '"$RUNNER_TEMP/ni08-ufh12-spill-summary/venv/bin/python" -m pip install '
    "--no-deps --only-binary=:all: --require-hashes -r "
    "recipe/scripts/ci/ni08_ufh12_spill_requirements.txt"
)
CONFIG_NAMES = {
    "pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini", "uv.lock",
    "requirements.txt", "requirements-dev.txt", "requirements-test.txt",
}
CONFIG_SUFFIXES = {".toml", ".ini", ".cfg", ".yaml", ".yml"}
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
        raise RuntimeError(f"declared input is missing or nonregular: {relative}")
    row = git(repo, "ls-tree", "HEAD", "--", relative).split("\t", 1)[0].split()
    if not row or row[0] not in {"100644", "100755"}:
        raise RuntimeError(f"declared input is not a regular tracked Git file: {relative}")
    return path.absolute()


def source_config_paths(repo: Path) -> list[Path]:
    paths = []
    for relative in git(repo, "ls-files", "-z").split("\0"):
        if not relative:
            continue
        pure = PurePosixPath(relative)
        if not (relative.endswith(".py") or pure.name in CONFIG_NAMES or pure.suffix in CONFIG_SUFFIXES):
            continue
        path = repo / relative
        if path.is_symlink():
            continue  # APP symlink topology is independently bound in the source map.
        paths.append(regular_file(repo, relative))
    return paths


def sha256_path(path: Path) -> str:
    if path.is_symlink() or not path.is_file() or not stat.S_ISREG(path.lstat().st_mode):
        raise RuntimeError(f"evidence input is missing or nonregular: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_clean_pin(label: str, repo: Path, expected: str) -> str:
    pin = git(repo, "rev-parse", "HEAD")
    if pin != expected:
        raise RuntimeError(f"{label} checkout differs from pin: {pin}")
    if git(repo, "status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError(f"{label} checkout is not clean")
    return pin


def app_envelope_matches(app: Path, source_map: dict) -> list[Path]:
    records = source_map["APP_full_python_config_envelope"]["files"]
    by_path = {row["path"]: row for row in records}
    tracked = git(app, "ls-files", "-z").split("\0")
    selected = [name for name in tracked if name and
                (name.endswith(".py") or PurePosixPath(name).name in CONFIG_NAMES
                 or PurePosixPath(name).suffix in CONFIG_SUFFIXES)]
    if set(selected) != set(by_path) or len(selected) != len(records):
        raise RuntimeError("APP Python/config envelope path set differs from static map")
    tree = {}
    raw = subprocess.check_output(["git", "-C", str(app), "ls-tree", "-r", "-z", "HEAD"])
    for item in raw.split(b"\0"):
        if not item:
            continue
        metadata, name_bytes = item.split(b"\t", 1)
        mode, _kind, oid = metadata.decode().split()
        name = name_bytes.decode()
        if name in by_path:
            tree[name] = (mode, oid)
    regular = []
    for name, expected in by_path.items():
        if tree.get(name) != (expected["mode"], expected["blob"]):
            raise RuntimeError(f"APP Git blob/mode differs from static map: {name}")
        path = app / name
        if expected["mode"] == "120000":
            if not path.is_symlink():
                raise RuntimeError(f"APP symlink topology differs: {name}")
            target = os.readlink(path).encode("utf-8")
            if len(target) != expected["size"] or hashlib.sha256(target).hexdigest() != expected["sha256"]:
                raise RuntimeError(f"APP symlink target differs from source map: {name}")
        else:
            if sha256_path(path) != expected["sha256"]:
                raise RuntimeError(f"APP source/config bytes differ from static map: {name}")
            regular.append(path.absolute())
    return regular


def derive_case_ids(test_path: Path) -> list[tuple[str, str]]:
    """Derive module/class/function names from AST only; do not run pytest collection."""
    tree = ast.parse(test_path.read_text(encoding="utf-8"))
    rows = []
    module = "tests.unit.test_repl_spill_output"
    for cls in tree.body:
        if not isinstance(cls, ast.ClassDef):
            continue
        for node in cls.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                rows.append((module + "." + cls.name, node.name))
    return rows


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

def verify_locked_requirements(app: Path, requirements: Path, source_map: dict) -> dict[str, str]:
    lock_path = regular_file(app, "uv.lock")
    lock_bytes = lock_path.read_bytes()
    if hashlib.sha256(lock_bytes).hexdigest() != source_map["dependencies"]["app_uv_lock_sha256"]:
        raise RuntimeError("APP uv.lock differs from the static source map")
    lock = tomllib.loads(lock_bytes.decode("utf-8"))
    packages = {row["name"].lower().replace("_", "-"): row for row in lock["package"]}
    declared: dict[str, str] = {}
    declared_hashes: dict[str, set[str]] = {}
    current = None
    for line in requirements.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        match = re.match(r"^([A-Za-z0-9_.-]+)==([^\s]+)", stripped)
        if match:
            current = match.group(1).lower().replace("_", "-")
            declared[current] = match.group(2)
            declared_hashes[current] = set()
        if current:
            declared_hashes[current].update(re.findall(r"--hash=sha256:([0-9a-f]{64})", stripped))
    roots = set(source_map["dependencies"]["external_distribution_roots"].values())
    todo = [name.lower().replace("_", "-") for name in roots]
    closure = set()
    while todo:
        name = todo.pop()
        if name in closure:
            continue
        row = packages.get(name)
        if not row:
            raise RuntimeError(f"missing APP locked distribution: {name}")
        closure.add(name)
        for dep in row.get("dependencies", []):
            marker = dep.get("marker", "").replace('"', "'")
            if "sys_platform == 'win32'" in marker:
                continue
            if "extra ==" in marker:
                raise RuntimeError(f"unresolved extra-conditioned dependency: {name}")
            todo.append(dep["name"].lower().replace("_", "-"))
    if closure != set(declared):
        raise RuntimeError("requirements differ from complete static external import closure")
    locked_map = {item["name"].lower().replace("_", "-"): item
                  for item in source_map["dependencies"]["packages"]}
    if set(locked_map) != closure:
        raise RuntimeError("source-map package records differ from recomputed lock closure")
    for name in sorted(closure):
        row = packages[name]
        allowed = {wheel["hash"].removeprefix("sha256:") for wheel in row.get("wheels", [])}
        recorded = {value.removeprefix("sha256:") for value in locked_map[name]["wheel_hashes"]}
        if not allowed or allowed != recorded or allowed != declared_hashes[name]:
            raise RuntimeError(f"all-wheel hashes differ from APP uv.lock: {name}")
        if declared[name] != row["version"] or locked_map[name]["version"] != row["version"]:
            raise RuntimeError(f"locked distribution version differs: {name}")
        if importlib.metadata.version(name) != row["version"]:
            raise RuntimeError(f"installed distribution differs from lock: {name}")
    if hashlib.sha256(requirements.read_bytes()).hexdigest() != source_map["dependencies"]["requirements_sha256"]:
        raise RuntimeError("requirements file digest differs from source map")
    return {name: declared[name] for name in sorted(closure)}



def hash_regular(path: Path) -> str:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise RuntimeError(f"custody input is not a single-link regular file: {path}")
        digest = hashlib.sha256(); total = 0
        while True:
            data = os.read(fd, 1024 * 1024)
            if not data: break
            digest.update(data); total += len(data)
        after = os.fstat(fd)
        identity = lambda row: (row.st_dev,row.st_ino,row.st_mode,row.st_size,row.st_nlink,row.st_mtime_ns,row.st_ctime_ns)
        if identity(before) != identity(after) or total != after.st_size or identity(after) != identity(path.lstat()):
            raise RuntimeError(f"custody input changed while hashing: {path}")
        return digest.hexdigest()
    finally: os.close(fd)

def typed_tree(root: Path, *, omit_status: bool = True) -> dict:
    if root.is_symlink() or not stat.S_ISDIR(root.lstat().st_mode): raise RuntimeError("result root is not a real directory")
    found = {".": {"kind":"directory", "mode":stat.S_IMODE(root.lstat().st_mode)}}
    def walk(directory: Path) -> None:
        for entry in sorted(os.scandir(directory),key=lambda row:row.name):
            path=Path(entry.path); mode=entry.stat(follow_symlinks=False).st_mode; rel=path.relative_to(root).as_posix()
            if omit_status and rel=="status.json": continue
            if stat.S_ISLNK(mode):
                target=os.readlink(path).encode("utf-8","surrogateescape")
                found[rel]={"kind":"symlink_opaque","mode":stat.S_IMODE(mode),"target_bytes":len(target),"target_sha256":hashlib.sha256(target).hexdigest()}
            elif stat.S_ISDIR(mode): found[rel+"/"]={"kind":"directory", "mode":stat.S_IMODE(mode)}; walk(path)
            elif stat.S_ISREG(mode): found[rel]={"kind":"regular","mode":stat.S_IMODE(mode),"bytes":path.lstat().st_size,"sha256":hash_regular(path)}
            else: raise RuntimeError(f"special result entry: {rel}")
    walk(root); return found

def stable_digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def durable_json(path: Path, value: dict) -> None:
    tmp=path.with_suffix(path.suffix+".tmp")
    if tmp.exists() or tmp.is_symlink() or path.exists() or path.is_symlink(): raise RuntimeError(f"refusing to overwrite custody: {path.name}")
    with tmp.open("x",encoding="utf-8") as handle:
        json.dump(value,handle,sort_keys=True,indent=2); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
    os.replace(tmp,path)

def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, carrier, app = (workspace / value for value in ("recipe", "carrier", "app"))
    result = runner_temp / RESULT_NAME / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status = {"state": "preparing", "exit_code": None, "fixture_execution_conformant": None, "native_receipt_state": "no_receipt", "capture_started": False}
    boundary = "setup"
    error_record = None
    read_paths = []
    source_before = None
    result_before = None
    result_after_capture = None
    fixture_before_capture = None
    fixture_after_capture = None
    fixture_after_grade = None
    spill_root = Path(SPILL_ROOT)
    receipt = None
    exit_code = None
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
    try:
        if not ROOT_ENROLLMENT_READY or not ROOT_BINDINGS:
            raise RuntimeError("exact MAIN enrollment binding is absent")
        expected_env = {
            "UFH12_RUNNER_CONTEXT": RUNNER_CONTEXT,
            "UFH12_EXECUTION_CONTEXT": EXECUTION_CONTEXT,
            "UFH12_INSTALL_COMMAND": INSTALL_COMMAND,
            "ROOT_CONTEXT_PIN": ROOT_CONTEXT_PIN,
            "ROOT_CARRIER_PIN": CARRIER_PIN,
            "APP_PIN": APP_PIN,
            "UFH12_SPILL_ROOT": SPILL_ROOT,
            "CI": "true",
            "ORCHESTRATOR_MOCK_MODE": "1",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTEST_ADDOPTS": "",
            "PYTEST_PLUGINS": "",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONUNBUFFERED": "1",
            "PYTHONNOUSERSITE": "1",
        }
        for key, value in expected_env.items():
            if os.environ.get(key) != value:
                raise RuntimeError(f"{key} differs from frozen recipe")
        if os.environ.get("SPILL_ROOT_SETUP_OUTCOME") != "success":
            raise RuntimeError("GitHub-only owned spill-root setup step did not succeed")
        setup_path = result / SPILL_ROOT_SETUP
        if setup_path.is_symlink() or not setup_path.is_file() or not stat.S_ISREG(setup_path.lstat().st_mode):
            raise RuntimeError("GitHub spill-root setup record is missing or nonregular")
        setup_record = json.loads(setup_path.read_text(encoding="utf-8"))
        if (setup_record.get("state") != "created_owned_empty" or setup_record.get("path") != SPILL_ROOT
                or setup_record.get("runner_uid") != os.getuid() or setup_record.get("runner_gid") != os.getgid()
                or setup_record.get("uid") != os.getuid() or setup_record.get("gid") != os.getgid()
                or setup_record.get("mode") != 0o700 or setup_record.get("empty_at_creation") is not True):
            raise RuntimeError("owned spill-root setup receipt differs")
        spill_stat = spill_root.lstat()
        if (not stat.S_ISDIR(spill_stat.st_mode) or stat.S_ISLNK(spill_stat.st_mode)
                or spill_stat.st_uid != os.getuid() or spill_stat.st_gid != os.getgid()
                or stat.S_IMODE(spill_stat.st_mode) != 0o700
                or spill_stat.st_dev != setup_record.get("device") or spill_stat.st_ino != setup_record.get("inode")):
            raise RuntimeError("spill root path identity, ownership, or mode changed after setup")
        expected_chain = ["/", "/mnt", "/mnt/raid0", "/mnt/raid0/llm", SPILL_ROOT]
        identities = setup_record.get("ancestor_identity")
        if not isinstance(identities, list) or [row.get("path") for row in identities] != expected_chain:
            raise RuntimeError("spill root setup ancestor chain differs from the exact reviewed path")
        for identity in identities:
            ancestor=Path(identity["path"]); actual=ancestor.lstat()
            if (stat.S_ISLNK(actual.st_mode) or not stat.S_ISDIR(actual.st_mode)
                    or (actual.st_dev,actual.st_ino,actual.st_uid,actual.st_gid,stat.S_IMODE(actual.st_mode))
                    != (identity["device"],identity["inode"],identity["uid"],identity["gid"],identity["mode"])):
                raise RuntimeError("spill root ancestor identity changed after setup")
        if any(os.scandir(spill_root)):
            raise RuntimeError("spill root is not empty immediately before original whole-module run")
        if platform.python_version() != PYTHON_PIN:
            raise RuntimeError(f"Python runtime differs: {platform.python_version()}")
        venv = (runner_temp / RESULT_NAME / "venv").resolve()
        if sys.prefix == sys.base_prefix or Path(sys.prefix).resolve() != venv:
            raise RuntimeError("capture interpreter is not the isolated reviewed venv")

        recipe_pin = git(recipe, "rev-parse", "HEAD")
        carrier_pin = check_clean_pin("carrier", carrier, CARRIER_PIN)
        app_pin = check_clean_pin("APP", app, APP_PIN)
        if subprocess.run(["git", "-C", str(app), "merge-base", "--is-ancestor", APP_PARENT_PIN, APP_PIN]).returncode != 0:
            raise RuntimeError("declared APP source parent is not in exact source ancestry")
        if os.environ.get("GITHUB_REF") != "refs/heads/" + LITERAL_BRANCH or os.environ.get("GITHUB_EVENT_NAME") != "push":
            raise RuntimeError("workflow trigger is not the exact reviewed literal branch push")
        if recipe_pin != os.environ.get("GITHUB_SHA"):
            raise RuntimeError("recipe checkout differs from triggering GitHub SHA")
        if git(recipe, "status", "--porcelain", "--untracked-files=all"):
            raise RuntimeError("recipe checkout is not clean")
        if subprocess.run(["git", "-C", str(recipe), "merge-base", "--is-ancestor", ROOT_CONTEXT_PIN, "HEAD"]).returncode:
            raise RuntimeError("recipe does not descend from enrolled ROOT parent")
        if Path(os.environ.get("PYTHONPATH", "")).resolve() != app.resolve():
            raise RuntimeError("PYTHONPATH differs from exact APP checkout")
        for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_BASE_URL", "ANTHROPIC_BASE_URL"):
            if os.environ.get(key):
                raise RuntimeError(f"unexpected model endpoint/credential environment: {key}")

        workflow = regular_file(recipe, WORKFLOW)
        runner = regular_file(recipe, RUNNER)
        source_map_path = regular_file(recipe, SOURCE_MAP)
        function_graph_path = regular_file(recipe, FUNCTION_GRAPH)
        expected_path = regular_file(recipe, EXPECTED_CASES)
        closure_path = regular_file(recipe, CLOSURE)
        requirements = regular_file(recipe, REQUIREMENTS)
        review_note = regular_file(recipe, REVIEW_NOTE)
        source_map = json.loads(source_map_path.read_text(encoding="utf-8"))
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        function_graph = json.loads(function_graph_path.read_text(encoding="utf-8"))
        graph_record = source_map["executed_function_source_graph"]
        if (hashlib.sha256(function_graph_path.read_bytes()).hexdigest() != graph_record["sha256"]
                or len(function_graph["nodes"]) != graph_record["node_count"]
                or len(function_graph["resolved_static_call_edges"]) != graph_record["edge_count"]
                or function_graph["case_count"] != 15):
            raise RuntimeError("executed-function AST source graph digest/count mismatch")
        envelopes = source_map["source_readset_contract"]
        verify_frozen_envelope(recipe, envelopes["ROOT_enrolled_context_source_config_envelope"], ROOT_CONTEXT_PIN)
        verify_frozen_envelope(carrier, envelopes["existing_carrier_source_config_envelope"], CARRIER_PIN)
        verify_frozen_envelope(recipe, envelopes["recipe_source_config_envelope"], recipe_pin, recipe_self_excludes=SOURCE_MAP)
        binding = source_map["enrollment_binding"]
        if (binding.get("ROOT_enrollment") != ROOT_CONTEXT_PIN
                or binding.get("APP_source_candidate") != APP_PIN
                or binding.get("APP_source_parent") != APP_PARENT_PIN
                or binding.get("existing_native_carrier") != CARRIER_PIN
                or binding.get("ROOT_document_sha256") != ROOT_BINDINGS):
            raise RuntimeError("exact ROOT enrollment, APP source, or carrier binding differs")
        if hashlib.sha256(closure_path.read_bytes()).hexdigest() != source_map["dependencies"]["closure_sha256"]:
            raise RuntimeError("static import closure file changed")
        if hashlib.sha256(review_note.read_bytes()).hexdigest() != source_map.get("review_note_sha256"):
            raise RuntimeError("review-note bytes are not bound to final ROOT enrollment")

        app_paths = app_envelope_matches(app, source_map)
        expected_ids = [(row["classname"], row["name"]) for row in expected["case_identities"]]
        mapped_ids = [(row["classname"], row["name"]) for row in source_map["AST"]["case_identities"]]
        actual_ids = derive_case_ids(regular_file(app, SELECTION))
        if (Counter(actual_ids) != Counter(expected_ids) or Counter(mapped_ids) != Counter(expected_ids)
                or len(actual_ids) != 15):
            raise RuntimeError("whole-module AST identities differ from frozen 15-case map")
        if expected["case_count"] != 15 or expected["app_pin"] != APP_PIN:
            raise RuntimeError("expected case manifest pin/count differs")
        package_versions = verify_locked_requirements(app, requirements, source_map)
        installed = {dist.metadata.get("Name", "").lower().replace("_", "-")
                     for dist in importlib.metadata.distributions()}
        if installed != set(package_versions) | {"pip"}:
            raise RuntimeError("isolated venv contains packages outside lock closure and pip bootstrap")

        install_log = result / "dependency-install.log"
        if not install_log.is_file() or install_log.is_symlink():
            raise RuntimeError("original dependency-install log is missing/nonregular")
        freeze = result / "pip-freeze.txt"
        freeze.write_bytes(subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"]))
        environment = result / "runner-environment.json"
        environment.write_text(json.dumps({
            "python": sys.version, "platform": platform.platform(),
            "runner_context": RUNNER_CONTEXT, "execution_context": EXECUTION_CONTEXT,
            "repositories": {"recipe": recipe_pin, "carrier": carrier_pin, "app": app_pin},
            "selection": SELECTION, "case_count": 15,
            "install_command": INSTALL_COMMAND, "locked_versions": package_versions,
            "source_map_sha256": sha256_path(source_map_path),
            "requirements_sha256": sha256_path(requirements),
            "environment": {key: os.environ.get(key) for key in (
                "CI", "ORCHESTRATOR_MOCK_MODE", "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTEST_ADDOPTS",
                "PYTEST_PLUGINS", "PYTHONDONTWRITEBYTECODE", "PYTHONHASHSEED", "PYTHONPATH",
                "UFH12_RUNNER_CONTEXT", "UFH12_EXECUTION_CONTEXT", "UFH12_SPILL_ROOT", "SPILL_ROOT_SETUP_OUTCOME",
            )},
            "scope": "Synthetic REPL spill summary context budget controls using MagicMock worker responses and temporary spill files; no model, endpoint, ColGREP, embedding or live corpus.",
        }, sort_keys=True, indent=2) + "\n", encoding="utf-8")

        junit = result / "original-junit.xml"
        native = result / "native"
        stdout = result / "original-runner-stdout.log"
        stderr = result / "original-runner-stderr.log"
        command_record = result / "original-command.json"
        if any(path.exists() for path in (junit, native, stdout, stderr, command_record)):
            raise RuntimeError("refusing to overwrite original capture custody")
        root_context_paths = [regular_file(recipe, name) for name in ROOT_BINDINGS if name != REVIEW_NOTE]
        read_paths = [workflow, runner, source_map_path, function_graph_path, expected_path, closure_path, requirements,
                      review_note, install_log, setup_path, *root_context_paths,
                      *source_config_paths(recipe), *source_config_paths(carrier), *app_paths,
                      *(regular_file(carrier, path) for path in CARRIER_READS),
                      regular_file(app, "uv.lock"), freeze, environment, command_record]
        producer = [sys.executable, str(carrier / "scripts/ci/native_conformance.py"),
                    "--cwd", str(app), "--junit", str(junit), "--output", str(native),
                    "--repo", f"recipe={recipe}", "--repo", f"carrier={carrier}", "--repo", f"app={app}"]
        for path in dict.fromkeys(item.resolve() for item in read_paths):
            producer.extend(("--read-path", str(path)))
        producer.extend(("--select", SELECTION))
        test_command = [sys.executable, "-m", "pytest", "-c", "/dev/null", "--rootdir", str(app),
                        "--noconftest", "-o", "addopts=", "-p", "no:cacheprovider", "-q",
                        SELECTION, f"--junitxml={junit}"]
        command_record.write_text(json.dumps({"producer_argv": producer, "test_argv": test_command,
                                              "cwd": str(app),
                                              "read_paths": [str(path.resolve()) for path in dict.fromkeys(read_paths)],
                                              "environment": {"PYTHONPATH": str(app)},
                                              "outputs": {"junit": str(junit), "native": str(native)},
        }, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        boundary = "pre_capture_inventory"
        fixture_before_capture = typed_tree(spill_root, omit_status=False)
        if fixture_before_capture != {".": {"kind":"directory", "mode":0o700}}:
            raise RuntimeError("owned spill fixture root is not empty at pre-capture inventory")
        source_before = {str(path):hash_regular(path) for path in dict.fromkeys(p.resolve() for p in read_paths)}
        result_before = typed_tree(result)
        durable_json(result / "pre-capture-custody.json", {"phase":"before_native_invocation", "source_inventory":source_before,
            "source_inventory_sha256":stable_digest(source_before), "typed_result_tree":result_before,
            "typed_result_tree_sha256":stable_digest(result_before),"typed_fixture_tree_before_capture":fixture_before_capture,
            "typed_fixture_tree_before_capture_sha256":stable_digest(fixture_before_capture),"status_excluded_from_tree":True,
            "scope":"regular source/config reads and typed existing result tree; symlinks opaque"})
        boundary = "capture"
        status.update(state="running", capture_started=True, repositories={"recipe": recipe_pin, "carrier": carrier_pin, "app": app_pin})
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
        run_env = dict(os.environ, PYTHONPATH=str(app))
        completed = subprocess.run([*producer, "--", *test_command], cwd=app, env=run_env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        stdout.write_bytes(completed.stdout)
        stderr.write_bytes(completed.stderr)
        exit_code = completed.returncode
        receipt_path = native / "receipt.json"
        if not receipt_path.is_file() or receipt_path.is_symlink():
            status.update(state="capture_failed", exit_code=exit_code or 1, native_receipt_state="no_receipt")
            boundary = "missing_receipt"
            raise RuntimeError("native producer created no regular original receipt")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        metric = receipt.get("fixture_execution_conformant")
        status["native_receipt_state"] = ("native_null" if metric is None else "native_true" if metric is True else "native_false" if metric is False else "native_invalid_type")
        summary = receipt.get("summary") or {}
        counts = summary.get("counts") or {}
        rows = summary.get("cases") or []
        actual = [(row.get("classname"), row.get("name")) for row in rows]
        exact = (Counter(actual) == Counter(expected_ids) and len(actual) == 15
                 and counts.get("collected") == 15 and counts.get("executed") == 15
                 and counts.get("skipped") == 0 and counts.get("failure") == 0 and counts.get("error") == 0)

        def originals():
            native_items = sorted(native.rglob("*"))
            if any(path.is_symlink() for path in native_items):
                raise RuntimeError("native output contains a symlink")
            native_files = [path for path in native_items if path.is_file()]
            return list(dict.fromkeys([*read_paths, junit, stdout, stderr, freeze, environment,
                                       command_record, *native_files]))

        boundary = "post_capture_inventory"
        fixture_after_capture = typed_tree(spill_root, omit_status=False)
        fixture_record_path = result / "spill-fixture-tree-after-capture.json"
        durable_json(fixture_record_path, {"phase":"after_original_tests_and_actual_fixture_teardowns",
            "root_setup":setup_record,"typed_fixture_tree":fixture_after_capture,
            "typed_fixture_tree_sha256":stable_digest(fixture_after_capture),
            "qualification":"captures only files remaining after each test's real teardown; the two new tmp_path controls assert exact spill bytes before pytest removes their temporary fixture directories"})
        before_paths = originals()
        before = {str(path): hash_regular(path) for path in before_paths}
        source_after_capture = {str(path):hash_regular(path) for path in dict.fromkeys(p.resolve() for p in read_paths)}
        result_after_capture = typed_tree(result)
        durable_json(result / "post-capture-custody.json", {"phase":"after_capture_before_grade",
            "source_before_capture":source_before,"source_after_capture":source_after_capture,
            "source_stable":source_before==source_after_capture,"source_after_capture_sha256":stable_digest(source_after_capture),
            "typed_result_tree_before_capture":result_before,"typed_result_tree_after_capture_before_grade":result_after_capture,
            "typed_result_tree_after_capture_sha256":stable_digest(result_after_capture),"native_receipt_state":status["native_receipt_state"],
            "native_metric_value":metric,"original_exit_code":exit_code,"exact_case_set":exact,
            "typed_fixture_tree_before_capture":fixture_before_capture,"typed_fixture_tree_after_capture":fixture_after_capture,
            "typed_fixture_tree_after_capture_sha256":stable_digest(fixture_after_capture),
            "inventory_self_exclusion":"this custody record is excluded from its embedded tree; the following result tree includes it"})
        result_after_capture=typed_tree(result)
        boundary = "shared_grade"
        grade_rows = []
        if metric is not None:
            sys.path.insert(0, str(carrier))
            sys.path.insert(0, str(carrier / "scripts/vidya"))
            from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
            from claim_tuple import grade
            projected = native_rows(receipt_path)
            if len(projected) != 1:
                raise RuntimeError("existing CI adapter did not project one non-NULL native receipt")
            claim = project_ci_conformance(projected[0])
            quality, trust, reasons = grade(claim)
            grade_rows = [{"measurement_id":claim.measurement_id,"source_kind":claim.source_kind,"binding_kind":claim.binding_kind,"Q":quality,"T":trust,"reasons":reasons}]
        after_paths = originals()
        after = {str(path): hash_regular(path) for path in after_paths}
        if [str(path) for path in after_paths] != [str(path) for path in before_paths] or before != after:
            raise RuntimeError("shared grading changed original typed source/result/error custody")
        fixture_after_grade = typed_tree(spill_root, omit_status=False)
        if fixture_after_capture != fixture_after_grade:
            raise RuntimeError("typed spill fixture tree changed during shared grading")
        result_after_grade = typed_tree(result)
        source_after_grade = {str(path):hash_regular(path) for path in dict.fromkeys(p.resolve() for p in read_paths)}
        if source_before != source_after_capture or source_after_capture != source_after_grade:
            raise RuntimeError("regular source/config readset changed across capture or grading")
        if result_after_capture != result_after_grade:
            raise RuntimeError("typed result/error tree changed during shared grading")
        durable_json(result / "shared-grade-custody.json", {"phase":"after_existing_shared_grade",
            "source_before_capture":source_before,"source_after_grade":source_after_grade,
            "source_stable":source_before==source_after_grade,"source_after_grade_sha256":stable_digest(source_after_grade),
            "typed_result_tree_before_capture":result_before,"typed_result_tree_after_capture_before_grade":result_after_capture,
            "typed_result_tree_after_grade":result_after_grade,"typed_result_tree_after_grade_sha256":stable_digest(result_after_grade),
            "typed_fixture_tree_before_capture":fixture_before_capture,"typed_fixture_tree_after_capture":fixture_after_capture,
            "typed_fixture_tree_after_capture_sha256":stable_digest(fixture_after_capture),
            "typed_fixture_tree_after_grade":fixture_after_grade,"typed_fixture_tree_after_grade_sha256":stable_digest(fixture_after_grade),
            "native_receipt_state":status["native_receipt_state"],"native_metric_value":metric,
            "grade_projection":grade_rows,"grade_projection_expected":metric is not None,"new_grade_authored":False})
        passed = exit_code == 0 and metric is True and exact
        status.update(state="passed" if passed else "failed", exit_code=0 if passed else (exit_code or 1),
                      fixture_execution_conformant=metric, junit_counts=counts,
                      exact_case_set=exact, expected_case_count=15,
                      shared_grade=grade_rows, grade_projection_expected=metric is not None)
        return 0 if passed else (exit_code or 1)
    except Exception as exc:
        error_record={"stage":boundary,"capture_started":status.get("capture_started",False),
            "native_receipt_state":status.get("native_receipt_state","no_receipt"),
            "native_metric_value":receipt.get("fixture_execution_conformant") if receipt else None,
            "error_type":type(exc).__name__,"error_message":str(exc),"original_exit_code":exit_code,
            "receipt_present":bool(receipt),"source_before_capture":source_before,
            "source_before_capture_sha256":stable_digest(source_before) if source_before is not None else None,
            "typed_result_tree_before_capture":result_before,"typed_result_tree_after_capture_before_grade":result_after_capture,
            "typed_spill_fixture_tree_before_capture":fixture_before_capture,
            "typed_spill_fixture_tree_after_error":typed_tree(spill_root,omit_status=False) if spill_root.is_dir() and not spill_root.is_symlink() else None,
            "proposition_invented":False}
        status.update(state="capture_failed",exit_code=1,error_type=type(exc).__name__,error_message=str(exc),
                      failure_stage=boundary,error_custody_state="pending_finalized")
        return 1
    finally:
        try:
            if error_record is not None and not (result/"error-custody.json").exists():
                try:
                    current={str(path):hash_regular(path) for path in dict.fromkeys(p.resolve() for p in read_paths) if p.is_file() and not p.is_symlink()}
                    tree=typed_tree(result)
                    error_record.update(phase="after_error_before_final_status",source_after_error=current,
                        source_after_error_sha256=stable_digest(current),typed_result_tree_after_error=tree,
                        typed_result_tree_after_error_sha256=stable_digest(tree),status_excluded=True,error_record_self_excluded=True)
                except Exception as custody_exc: error_record["custody_snapshot_error"]=type(custody_exc).__name__+": "+str(custody_exc)
                durable_json(result/"error-custody.json",error_record)
                status["error_custody_state"]="written before final status; inventory excludes mutable status and its own final record"
        except Exception as custody_exc:
            status["error_custody_state"]="failed"
            status["error_custody_error"]=type(custody_exc).__name__+": "+str(custody_exc)
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
