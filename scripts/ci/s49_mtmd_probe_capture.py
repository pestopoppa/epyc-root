#!/usr/bin/env python3
"""Prospective hosted capture for the bounded synthetic S49 MTMD probe suite."""
from __future__ import annotations

import collections
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
APP_PIN = "0b0f35ac4bd4e4520ab95c6c073bdcdcd0458ba6"
APP_INPUTS = (
    "scripts/lib/env.sh", "scripts/lib/mtmd_probe.sh",
    "src/__init__.py", "src/services/__init__.py", "src/services/lightonocr_llama_server.py",
    "src/services/mtmd_probe.py", "src/vision/__init__.py", "src/vision/analyzers/__init__.py",
    "src/vision/analyzers/base.py", "src/vision/analyzers/clip_embed.py", "src/vision/analyzers/exif.py",
    "src/vision/analyzers/face_detect.py", "src/vision/analyzers/face_embed.py",
    "src/vision/analyzers/insightface_loader.py", "src/vision/analyzers/vl_describe.py",
    "src/vision/config.py", "src/structured_output/repair.py", "src/prompt_builders/code_utils.py",
    "src/config/__init__.py", "src/config/models.py", "src/config/validation.py",
    "src/chat_completions_roles.py", "src/db/__init__.py", "src/db/chroma_client.py",
    "src/env_parsing.py", "src/escalation.py", "src/features.py", "src/fleet.py", "src/roles.py",
    "src/registry/__init__.py", "src/registry/kernel_paths.py", "src/registry/model_descriptors.py",
    "src/registry/registry_loader.py", "src/registry/stack_priors.py", "src/runtime/instance_topology.py",
    "tests/__init__.py", "tests/unit/__init__.py", "tests/unit/test_mtmd_probe.py",
    "pyproject.toml", "uv.lock", "orchestration/model_registry.yaml", "config/gates.yaml",
    "config/kb_rag_config.yaml", "config/searxng/settings.yml",
)
ROOT_INPUTS = (
    ".github/workflows/s49-mtmd-probe.yml", "scripts/ci/s49_mtmd_probe_capture.py",
    "scripts/ci/s49_mtmd_probe_cases.json",
    "scripts/ci/s49_mtmd_probe_requirements.txt", "scripts/ci/s49_mtmd_probe_packages.json",
    "scripts/ci/ni08_source_context.py", "scripts/ci/native_conformance.py",
    "scripts/vidya/adapters/README.md", "scripts/vidya/adapters/__init__.py",
    "scripts/vidya/adapters/ci_conformance.py", "scripts/vidya/claim_tuple.py",
    "scripts/vidya/canonical.py", "scripts/vidya/frames.py", "scripts/vidya/lattice.py",
    "scripts/vidya/measurement_record.py", "scripts/vidya/cli.py", "scripts/vidya/ingest_sources.py",
    "handoffs/active/vidya-belief-substrate-program.md",
    "handoffs/active/standardized-stack-update-pipeline-finalization.md",
)
PACKAGES = json.loads((ROOT / "scripts/ci/s49_mtmd_probe_packages.json").read_text())
PACKAGES = PACKAGES["versions"]


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def regular_bytes(path: Path) -> bytes:
    """Read a single-link regular file without following any path component."""
    path = Path(os.path.abspath(path))
    parts = path.parts
    dfd = os.open(parts[0], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[1:-1]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                              dir_fd=dfd)
            os.close(dfd)
            dfd = next_fd
        before_name = os.stat(parts[-1], dir_fd=dfd, follow_symlinks=False)
        if not stat.S_ISREG(before_name.st_mode) or before_name.st_nlink != 1:
            raise RuntimeError(f"input is not a single-link regular file: {path}")
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dfd)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise RuntimeError(f"input changed type while opening: {path}")
            named = (before_name.st_dev, before_name.st_ino, before_name.st_mode,
                     before_name.st_nlink)
            opened = (before.st_dev, before.st_ino, before.st_mode, before.st_nlink)
            if named != opened:
                raise RuntimeError(f"input was replaced during open: {path}")
            chunks = []
            while block := os.read(fd, 1024 * 1024):
                chunks.append(block)
            after = os.fstat(fd)
            after_name = os.stat(parts[-1], dir_fd=dfd, follow_symlinks=False)
            identity = lambda st: (st.st_dev, st.st_ino, st.st_mode, st.st_nlink,
                                   st.st_size, st.st_mtime_ns, st.st_ctime_ns)
            if (identity(before) != identity(after) or identity(after) != identity(after_name)
                    or sum(map(len, chunks)) != after.st_size):
                raise RuntimeError(f"input changed while reading: {path}")
            return b"".join(chunks)
        finally:
            os.close(fd)
    finally:
        os.close(dfd)


def snapshot(paths: list[Path]) -> dict[str, dict[str, object]]:
    return {str(path): {"bytes": len(data), "sha256": sha(data)}
            for path in paths for data in (regular_bytes(path),)}


def inventory(root: Path) -> dict[str, dict[str, object]]:
    """Typed no-follow inventory; omit only the exact runner status file."""
    root = Path(os.path.abspath(root))
    root_info = os.lstat(root)
    if not stat.S_ISDIR(root_info.st_mode):
        raise RuntimeError("result root is not a real directory")
    result: dict[str, dict[str, object]] = {
        ".": {"type": "directory", "mode": stat.S_IMODE(root_info.st_mode),
              "identity": _stat_identity(root_info)}
    }

    def walk(directory: Path) -> None:
        before_dir = os.lstat(directory)
        if not stat.S_ISDIR(before_dir.st_mode):
            raise RuntimeError(f"result directory changed type: {directory}")
        if directory == root and _stat_identity(root_info) != _stat_identity(before_dir):
            raise RuntimeError("result root changed while inventorying")
        with os.scandir(directory) as entries:
            children = sorted(list(entries), key=lambda item: item.name)
        for entry in children:
            path = directory / entry.name
            rel = path.relative_to(root).as_posix()
            if rel == "status.json":
                continue
            info = entry.stat(follow_symlinks=False)
            if stat.S_ISLNK(info.st_mode):
                target = os.readlink(path)
                after_link = os.lstat(path)
                if _stat_identity(info) != _stat_identity(after_link):
                    raise RuntimeError(f"result symlink changed while inventorying: {rel}")
                result[rel] = {"type": "symlink", "mode": stat.S_IMODE(info.st_mode),
                               "identity": _stat_identity(info), "target": target,
                               "target_sha256": sha(os.fsencode(target))}
            elif stat.S_ISDIR(info.st_mode):
                result[rel] = {"type": "directory", "mode": stat.S_IMODE(info.st_mode),
                               "identity": _stat_identity(info)}
                walk(path)
                after_dir = os.lstat(path)
                if _stat_identity(info) != _stat_identity(after_dir):
                    raise RuntimeError(f"result directory changed while inventorying: {rel}")
            elif stat.S_ISREG(info.st_mode):
                if info.st_nlink != 1:
                    raise RuntimeError(f"hardlinked result file: {rel}")
                data = regular_bytes(path)
                after_file = os.lstat(path)
                if _stat_identity(info) != _stat_identity(after_file):
                    raise RuntimeError(f"result file changed while inventorying: {rel}")
                result[rel] = {"type": "file", "mode": stat.S_IMODE(info.st_mode),
                               "identity": _stat_identity(info), "bytes": len(data),
                               "sha256": sha(data)}
            else:
                raise RuntimeError(f"special file in result tree: {rel}")
        after_dir = os.lstat(directory)
        if _stat_identity(before_dir) != _stat_identity(after_dir):
            raise RuntimeError(f"result directory changed while inventorying: {directory}")

    walk(root)
    return result


def _stat_identity(info: os.stat_result) -> tuple[int, ...]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def input_paths(app: Path, context: Path) -> list[Path]:
    return ([ROOT / name for name in ROOT_INPUTS]
            + [ROOT / "scripts/ci/s49_mtmd_probe_input_map.json"]
            + [app / name for name in APP_INPUTS]
            + [context])


def validate_task_enrollment() -> None:
    task_id = "VB-S49-MTMD-PROBE-CONFORMANCE"
    task_lines = regular_bytes(ROOT / "handoffs/active/vidya-belief-substrate-program.md").decode("utf-8").splitlines()
    source_lines = regular_bytes(ROOT / "scripts/vidya/adapters/README.md").decode("utf-8").splitlines()
    if not any(task_id in line and line.startswith(("- [ ] **", "- [x] **")) for line in task_lines):
        raise RuntimeError("canonical S49 conformance task is not enrolled before capture")
    if not any(task_id in line for line in source_lines):
        raise RuntimeError("S49 source-table row is not enrolled before capture")


def validate_source_map(app: Path) -> None:
    manifest = json.loads(regular_bytes(ROOT / "scripts/ci/s49_mtmd_probe_input_map.json"))
    if manifest.get("schema") != "epyc.s49.source-map/v1" or manifest.get("app_commit") != APP_PIN:
        raise RuntimeError("source map schema or APP pin differs from reviewed candidate")
    rows = manifest.get("entries")
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("source map has no bound source inputs")
    expected = {("root", name) for name in ROOT_INPUTS}
    expected |= {("app", name) for name in APP_INPUTS}
    identities = [(row.get("repo"), row.get("path")) for row in rows]
    if len(identities) != len(set(identities)) or set(identities) != expected:
        raise RuntimeError("source map membership differs from declared inputs; only the map itself is excluded")
    if ("root", "scripts/ci/s49_mtmd_probe_input_map.json") in identities:
        raise RuntimeError("source map must explicitly exclude only itself from membership")
    for row in rows:
        repo = ROOT if row.get("repo") == "root" else app if row.get("repo") == "app" else None
        if repo is None:
            raise RuntimeError("source map contains an unknown repository")
        rel = Path(row["path"])
        if rel.is_absolute() or ".." in rel.parts or rel.as_posix() != row["path"]:
            raise RuntimeError("source map contains a non-normalized path")
        path = repo / rel
        data = regular_bytes(path)
        if len(data) != row.get("bytes") or sha(data) != row.get("sha256"):
            raise RuntimeError(f"source-map digest mismatch: {row['repo']}:{row['path']}")
        mode = git(repo, "ls-tree", "HEAD", "--", row["path"]).split(" ", 1)[0]
        if mode != row.get("git_mode"):
            raise RuntimeError(f"source-map Git mode mismatch: {row['repo']}:{row['path']}")
        blob = row.get("git_blob")
        if not blob or git(repo, "rev-parse", f"HEAD:{row['path']}") != blob:
            raise RuntimeError(f"source-map Git blob mismatch: {row['repo']}:{row['path']}")


def source_context(app: Path, output: Path) -> None:
    command = [sys.executable, str(ROOT / "scripts/ci/ni08_source_context.py"),
               "--repo", f"root={ROOT}", "--repo", f"app={app}", "--output", str(output)]
    proc = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, check=False)
    if proc.returncode:
        raise RuntimeError(f"source-context generation failed: {proc.stdout[-2000:]}")


def load_carrier():
    path = ROOT / "scripts/ci/native_conformance.py"
    spec = importlib.util.spec_from_file_location("s49_native_conformance", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load existing fixture carrier")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def exact_cases(junit: Path) -> list[tuple[str, str]]:
    root = ET.parse(junit).getroot()
    rows = [(case.get("classname", ""), case.get("name", "")) for case in root.iter("testcase")]
    if not rows or any(not a or not b for a, b in rows) or len(rows) != len(set(rows)):
        raise RuntimeError("JUnit case identities are empty or duplicated")
    return rows


def write_custody(path: Path, payload: dict[str, object]) -> None:
    data = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    temporary = path.with_name(path.name + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.lexists(temporary):
            os.unlink(temporary)


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: s49_mtmd_probe_capture.py APP_ROOT RESULT_DIR")
    app, result = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    rt = Path(os.environ["RUNNER_TEMP"]).resolve()
    venv = (rt / "s49" / "venv").resolve()
    if Path(sys.prefix).resolve() != venv or platform.python_implementation() != "CPython" or platform.python_version() != "3.13.15":
        raise RuntimeError("expected pinned CPython 3.13.15 isolated RUNNER_TEMP environment")
    if git(app, "rev-parse", "HEAD") != APP_PIN or git(app, "status", "--porcelain"):
        raise RuntimeError("APP checkout identity or cleanliness differs from reviewed S49 source")
    recipe_pin = os.environ.get("GITHUB_SHA")
    if (not recipe_pin or git(ROOT, "rev-parse", "HEAD") != recipe_pin
            or git(ROOT, "status", "--porcelain")):
        raise RuntimeError("recipe checkout identity or cleanliness differs from exact hosted source commit")
    if not result.is_relative_to(rt) or os.path.lexists(result):
        raise RuntimeError("capture result must be a fresh RUNNER_TEMP child")
    for key in ("LD_LIBRARY_PATH", "LD_PRELOAD", "PYTHONPATH", "PYTHONHOME"):
        if key in os.environ:
            raise RuntimeError(f"ambient {key} must be removed before capture")
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise RuntimeError("bytecode writes must be disabled for source immutability")
    if os.environ.get("EPYC_RUN_HOSTED_TIMEOUT_CONTROL") != "1":
        raise RuntimeError("hosted-only bounded timeout control was not explicitly enabled")
    if os.environ.get("ORCHESTRATOR_MOCK_MODE") != "1":
        raise RuntimeError("synthetic APP controls require explicit mock mode")
    absent_paths = {
        "ORCHESTRATOR_PATHS_LLAMA_CPP_BIN": rt / "s49" / "absent" / "llama-cli",
        "ORCHESTRATOR_PATHS_LLAMA_MTMD": rt / "s49" / "absent" / "llama-mtmd-cli",
        "ORCHESTRATOR_PATHS_LLAMA_SERVER": rt / "s49" / "absent" / "llama-server",
    }
    if any(path.exists() or path.is_symlink() for path in absent_paths.values()):
        raise RuntimeError("configured llama executable sentinel unexpectedly exists")
    absent = absent_paths["ORCHESTRATOR_PATHS_LLAMA_MTMD"]
    result.mkdir(parents=True, exist_ok=False)
    (result / "tmp").mkdir()
    requirements = ROOT / "scripts/ci/s49_mtmd_probe_requirements.txt"
    install = subprocess.run([sys.executable, "-m", "pip", "install", "--require-hashes", "--no-deps",
                              "--only-binary=:all:", "-r", str(requirements)],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
    (result / "dependency-install.log").write_text(install.stdout)
    if install.returncode:
        raise RuntimeError("locked wheel install failed")
    if {name: importlib.metadata.version(name) for name in PACKAGES} != PACKAGES:
        raise RuntimeError("installed source-eager package versions differ from full pinned closure")
    env = {"python": sys.version, "python_version": platform.python_version(), "platform": platform.platform(),
           "packages": PACKAGES, "app_pin": APP_PIN, "recipe_pin": recipe_pin}
    (result / "environment.json").write_text(json.dumps(env, sort_keys=True, separators=(",", ":")) + "\n")
    freeze = subprocess.run([sys.executable, "-m", "pip", "freeze", "--all"], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, check=False)
    if freeze.returncode:
        raise RuntimeError("cannot inventory isolated packages")
    (result / "pip-freeze.txt").write_text(freeze.stdout)
    validate_task_enrollment()
    source_context(app, result / "source-context.json")
    validate_source_map(app)
    junit = result / "selected-junit.xml"
    native_dir = result / "native"
    case_manifest = json.loads(regular_bytes(ROOT / "scripts/ci/s49_mtmd_probe_cases.json"))
    expected = [(item["classname"], item["name"]) for item in case_manifest["cases"]]
    if len(expected) != 11 or len(set(expected)) != len(expected):
        raise RuntimeError("S49 case manifest must bind exactly eleven unique cases")
    pytest_env = ["env", "-i", f"PATH={venv / 'bin'}:/usr/bin:/bin", f"HOME={rt / 's49/home'}",
                  f"TMPDIR={result / 'tmp'}", f"RUNNER_TEMP={rt}", "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1",
                  "PYTEST_ADDOPTS=", "PYTEST_PLUGINS=", "PYTHONDONTWRITEBYTECODE=1",
                  "PYTHONHASHSEED=0", "PYTHONUNBUFFERED=1", "PYTHONNOUSERSITE=1",
                  "EPYC_RUN_HOSTED_TIMEOUT_CONTROL=1", "ORCHESTRATOR_MOCK_MODE=1",
                  *[f"{key}={path}" for key, path in absent_paths.items()]]
    command = pytest_env + [sys.executable, "-m", "pytest", "-c", "/dev/null", "--rootdir", str(app),
                            "-o", "addopts=", "-p", "no:cacheprovider", "--noconftest", "-q",
                            f"--junitxml={junit}", "--basetemp", str(result / "pytest-tmp"),
                            "tests/unit/test_mtmd_probe.py"]
    readset = input_paths(app, result / "source-context.json")
    before = snapshot(readset)
    before_tree = inventory(result.parent)
    carrier = load_carrier()
    custody_path = rt / "s49" / "capture-custody.json"
    try:
        record = carrier.capture_fixture_execution(argv=command, cwd=app, junit=junit, output=native_dir,
            repositories={"root": ROOT, "app": app}, read_paths=readset,
            selections=["tests/unit/test_mtmd_probe.py"])
    except Exception as exc:
        after_capture_sources = snapshot(readset)
        after_capture_tree = inventory(result.parent)
        write_custody(custody_path, {
            "native_record": None,
            "capture_error": f"{type(exc).__name__}: {exc}",
            "recipe_pin": recipe_pin,
            "source_before_capture": before,
            "source_after_capture": after_capture_sources,
            "result_before_capture": before_tree,
            "result_after_capture": after_capture_tree,
            "grade_state": "not_attempted",
        })
        raise
    after_capture_sources = snapshot(readset)
    after_capture_tree = inventory(result.parent)
    write_custody(custody_path, {
        "native_record": record,
        "recipe_pin": recipe_pin,
        "source_before_capture": before,
        "source_after_capture": after_capture_sources,
        "result_before_capture": before_tree,
        "result_after_capture": after_capture_tree,
        "grade_state": "not_attempted",
    })
    if before != after_capture_sources:
        raise RuntimeError("declared source/context inputs changed during capture; custody preserved")
    if record.get("fixture_execution_conformant") is not True:
        raise RuntimeError("native carrier did not report conformant selected fixture execution; custody preserved")
    if exact_cases(junit) != expected:
        raise RuntimeError("original JUnit cases differ from exact S49 manifest")
    counts = record["summary"]["counts"]
    if counts != {"collected": 11, "executed": 11, "passed": 11, "failure": 0, "error": 0, "skipped": 0}:
        raise RuntimeError("S49 native counts differ from eleven passing cases")
    if any(path.exists() or path.is_symlink() for path in absent_paths.values()):
        raise RuntimeError("configured llama executable sentinel was created during capture")
    write_custody(custody_path, {
        "native_record": record,
        "recipe_pin": recipe_pin,
        "source_before_capture": before,
        "source_after_capture": after_capture_sources,
        "result_before_capture": before_tree,
        "result_after_capture": after_capture_tree,
        "grade_state": "running",
    })
    sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts/vidya"))
    try:
        from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
        from claim_tuple import grade
        rows = native_rows(str(native_dir / "receipt.json"))
        if len(rows) != 1:
            raise RuntimeError("unchanged CI adapter refused or duplicated the native row")
        judgment = grade(project_ci_conformance(rows[0]))
        after_grade_sources = snapshot(readset)
        after_grade_tree = inventory(result.parent)
    except Exception as exc:
        write_custody(custody_path, {
            "native_record": record,
            "recipe_pin": recipe_pin,
            "source_before_capture": before,
            "source_after_capture": after_capture_sources,
            "source_after_grade": snapshot(readset),
            "result_before_capture": before_tree,
            "result_after_capture": after_capture_tree,
            "result_after_grade": inventory(result.parent),
            "grade_error": f"{type(exc).__name__}: {exc}",
            "grade_state": "failed",
        })
        raise
    write_custody(custody_path, {
        "native_record": record,
        "recipe_pin": recipe_pin,
        "source_before_capture": before,
        "source_after_capture": after_capture_sources,
        "source_after_grade": after_grade_sources,
        "result_before_capture": before_tree,
        "result_after_capture": after_capture_tree,
        "result_after_grade": after_grade_tree,
        "grade": [judgment[0], judgment[1]],
        "grade_state": "complete",
    })
    if judgment[0:2] != ("Judged", "Located"):
        raise RuntimeError("unchanged shared ClaimTuple ladder did not return Judged/Located")
    if before != after_grade_sources or after_capture_tree != after_grade_tree:
        raise RuntimeError("source inputs or captured originals changed during grade")
    if any(path.exists() or path.is_symlink() for path in absent_paths.values()):
        raise RuntimeError("configured llama executable sentinel exists after grade")
    grade_record = {"native_receipt": str(native_dir / "receipt.json"), "cases": expected,
                    "counts": counts, "grade": judgment[0], "location": judgment[1],
                    "scope": "synthetic executable-discovery controls; no inference or runtime warrant",
                    "source_before_capture": before, "source_after_capture": after_capture_sources,
                    "source_after_grade": after_grade_sources, "result_before_capture": before_tree,
                    "result_after_capture": after_capture_tree, "result_after_grade": after_grade_tree}
    grade_path = rt / "s49" / "shared-grade-check.json"
    with grade_path.open("xb") as stream:
        stream.write((json.dumps(grade_record, sort_keys=True, separators=(",", ":")) + "\n").encode())
    print(json.dumps({"cases": len(expected), "grade": judgment[0], "location": judgment[1]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
