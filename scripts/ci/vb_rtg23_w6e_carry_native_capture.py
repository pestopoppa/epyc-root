"""Capture the full W6 journal adapter test module against the pinned real writer."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import stat
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
ROOT_CONTEXT_PIN = "7981a9acf2b8e2c328b9add8e21a68656c99c1d6"
ROOT_SOURCE_PIN = "5a865fd0242bd911d668152c48af238a44f89581"
APP_PIN = "129a58c29d3ed1814caa1acfa29d14f604020886"
APP_LOCK_PIN = "3fc9f947bd3240fdb65daa719f37625e3ac6c7df"
PYTHON_PIN = "3.13.15"
WORKFLOW = ".github/workflows/vb-rtg23-w6e-carry-native.yml"
DRIVER = "scripts/ci/vb_rtg23_w6e_carry_native_capture.py"
CASES = "scripts/ci/vb_rtg23_w6e_carry_native_cases.json"
REQUIREMENTS = "scripts/ci/vb_rtg23_w6e_carry_native_requirements.txt"
TASK = "handoffs/active/objective-task-rate-goodput.md"
SOURCE_TABLE = "scripts/vidya/adapters/README.md"
VB_PROGRAM = "handoffs/active/vidya-belief-substrate-program.md"
SELECTIONS = ("tests/vidya/test_autopilot_journal_adapter.py",)
ENV = {
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0", "PYTHONUNBUFFERED": "1", "PYTEST_ADDOPTS": "",
    "PYTEST_PLUGINS": "", "ORCHESTRATOR_IGNORE_RUNTIME_STACK_FACTS": "1",
    "ORCHESTRATOR_MOCK_MODE": "1", "PYTHONNOUSERSITE": "1",
}


def file_identity(info):
    return (info.st_dev,info.st_ino,info.st_mode,info.st_nlink,info.st_size,info.st_mtime_ns,info.st_ctime_ns)

def regular_bytes(path: Path) -> bytes:
    path=Path(os.path.abspath(path));parts=path.parts
    dfd=os.open(parts[0],os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    fd=None
    try:
        for part in parts[1:-1]:
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=dfd)
            os.close(dfd);dfd=child
        named_before=os.stat(parts[-1],dir_fd=dfd,follow_symlinks=False)
        fd=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=dfd)
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or file_identity(before)!=file_identity(named_before):
            raise RuntimeError(f"not a stable single-link regular file: {path}")
        chunks=[]
        while True:
            data=os.read(fd,1<<20)
            if not data:break
            chunks.append(data)
        after=os.fstat(fd);named_after=os.stat(parts[-1],dir_fd=dfd,follow_symlinks=False)
        if file_identity(before)!=file_identity(after) or file_identity(after)!=file_identity(named_after):
            raise RuntimeError(f"file changed while reading: {path}")
        return b"".join(chunks)
    finally:
        if fd is not None:os.close(fd)
        os.close(dfd)

def sha(path: Path) -> str:
    return hashlib.sha256(regular_bytes(path)).hexdigest()

def durable_custody(path: Path, record: dict) -> None:
    with path.open("xb") as handle:
        handle.write((json.dumps(record,sort_keys=True,indent=2)+"\n").encode())
        handle.flush();os.fsync(handle.fileno())
    fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def tracked(repo: Path, relative: str) -> Path:
    path = repo
    parts = Path(relative).parts
    if Path(relative).is_absolute() or not parts or any(p in {"", ".", ".."} for p in parts):
        raise RuntimeError(f"non-normalized input: {relative}")
    for i, part in enumerate(parts):
        path = path / part
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or (i < len(parts) - 1 and not stat.S_ISDIR(info.st_mode)):
            raise RuntimeError(f"input traverses a non-directory or symlink: {relative}")
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise RuntimeError(f"input is not a single-link file: {relative}")
    entry = git(repo, "ls-tree", "HEAD", "--", relative).split()
    if len(entry) < 3 or entry[1] != "blob" or entry[0] not in {"100644", "100755"}:
        raise RuntimeError(f"input is not a tracked regular blob: {relative}")
    return path


def tree_entry(repo: Path, relative: str) -> tuple[str, str]:
    raw = git(repo, "ls-tree", "HEAD", "--", relative)
    meta, sep, name = raw.partition("\t")
    fields = meta.split()
    if not sep or name != relative or len(fields) != 3 or fields[1] != "blob" or fields[0] not in {"100644", "100755"}:
        raise RuntimeError(f"expected regular tracked file {relative}")
    return fields[0], fields[2]


def optional_state(repo: Path, relative: str) -> dict:
    """Record a declared optional runtime data file without following any symlink."""
    path = repo
    parts = Path(relative).parts
    for index, part in enumerate(parts):
        path = path / part
        try:
            info = path.lstat()
        except FileNotFoundError:
            return {"state": "absent", "path": relative}
        if stat.S_ISLNK(info.st_mode):
            raise RuntimeError(f"runtime data path traverses a symlink: {relative}")
        if index < len(parts) - 1 and not stat.S_ISDIR(info.st_mode):
            raise RuntimeError(f"runtime data parent is not a directory: {relative}")
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise RuntimeError(f"runtime data is not a single-link regular file: {relative}")
    return {"state": "regular", "path": relative, "size": info.st_size,
            "sha256": sha(path), "mode": stat.S_IMODE(info.st_mode)}


def snapshot(root: Path, omit: set[str] = frozenset()) -> dict[str, str]:
    if not stat.S_ISDIR(root.lstat().st_mode):
        raise RuntimeError("result root is not a directory")
    found = {".": "directory"}
    stack = [(root, "")]
    while stack:
        directory, prefix = stack.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                rel = f"{prefix}/{entry.name}" if prefix else entry.name
                if rel in omit:
                    continue
                mode = entry.stat(follow_symlinks=False).st_mode
                if stat.S_ISLNK(mode):
                    found[rel] = f"symlink:{os.readlink(entry.path)}"
                elif stat.S_ISDIR(mode):
                    found[rel + "/"] = "directory"
                    stack.append((Path(entry.path), rel))
                elif stat.S_ISREG(mode) and entry.stat(follow_symlinks=False).st_nlink == 1:
                    found[rel] = sha(Path(entry.path))
                else:
                    raise RuntimeError(f"unsupported run-root object: {rel}")
    return dict(sorted(found.items()))


def verify_repo(repo: Path, pin: str, label: str) -> None:
    if git(repo, "rev-parse", "HEAD") != pin or git(repo, "status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError(f"{label} identity or tracked state mismatch")


def verify_map(repo: Path, entries: list[dict], label: str) -> list[Path]:
    result = []
    for item in entries:
        path = tracked(repo, item["path"])
        mode, oid = tree_entry(repo, item["path"])
        if mode != item["git_mode"] or oid != item["git_blob"] or sha(path) != item["sha256"]:
            raise RuntimeError(f"{label} source map mismatch: {item['path']}")
        result.append(path)
    return result


def main() -> int:
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    result = runner_temp / "vb-w6e-carry" / "result"
    status_path = result / "status.json"
    status = {"state": "preparing", "job": "vb-rtg23-w6e-carry-conformance", "exit_code": None,
              "fixture_execution_conformant": None, "promotion_or_release_acceptance": None}
    read_paths=[];app_source=None;boundary="setup"
    try:
        for key in ("LD_LIBRARY_PATH","LD_PRELOAD","PYTHONHOME","PYTHONPATH"):
            os.environ.pop(key,None)
        os_release = platform.freedesktop_os_release() if hasattr(platform, "freedesktop_os_release") else {}
        if (platform.python_version() != PYTHON_PIN or sys.platform != "linux"
                or platform.machine() != "x86_64" or platform.python_implementation() != "CPython"
                or Path(sys.prefix).resolve() != runner_temp / "vb-w6e-carry" / "venv" or sys.prefix == sys.base_prefix
                or os_release.get("ID") != "ubuntu" or os_release.get("VERSION_ID") != "24.04"):
            raise RuntimeError("runner, OS, architecture, Python, or isolated venv differs from recipe")
        if (os.environ.get("GITHUB_EVENT_NAME") != "push"
                or os.environ.get("GITHUB_REF") != "refs/heads/codex/rtg23-w6e-carry-native-recipe-20261007"
                or os.environ.get("GITHUB_SHA") != os.environ.get("RECIPE_PIN")):
            raise RuntimeError("event/ref/recipe SHA differs from exact private recipe candidate")
        for key, value in ENV.items():
            if os.environ.get(key) != value:
                raise RuntimeError(f"environment mismatch: {key}")
        isolated = {
            "EPYC_ORCH_ROOT": str(workspace / "app_source"),
            "VIDYA_ORCH_WRITER_ROOT": str(workspace / "app_source"),
            "TMPDIR": str(result / "tmp"),
            "HOME": str(result / "home"),
            "ORCHESTRATOR_PATHS_LLM_ROOT": str(runner_temp / "isolated-llm"),
            "ORCHESTRATOR_PATHS_LLAMA_CPP_BIN": str(runner_temp / "vb-w6e-carry" / "absent" / "cpu"),
            "ORCHESTRATOR_PATHS_LLAMA_MTMD": str(runner_temp / "vb-w6e-carry" / "absent" / "llama-mtmd-cli"),
            "ORCHESTRATOR_PATHS_LLAMA_SERVER": str(runner_temp / "vb-w6e-carry" / "absent" / "llama-server"),
        }
        if any(os.environ.get(key) != value for key, value in isolated.items()):
            raise RuntimeError("writer or serving paths differ from isolated workflow bootstrap")
        isolated_llm = Path(isolated["ORCHESTRATOR_PATHS_LLM_ROOT"])
        if not isolated_llm.is_dir() or any(isolated_llm.iterdir()):
            raise RuntimeError("isolated model root must exist and be empty")
        absent_binaries = [Path(isolated[key]) for key in ("ORCHESTRATOR_PATHS_LLAMA_CPP_BIN",
                            "ORCHESTRATOR_PATHS_LLAMA_MTMD", "ORCHESTRATOR_PATHS_LLAMA_SERVER")]
        if any(path.exists() for path in absent_binaries):
            raise RuntimeError("an inference-serving binary exists at an isolated absent path")
        if "ORCHESTRATOR_STACK_NUMA_MODE" in os.environ:
            raise RuntimeError("runner supplied an unreviewed stack NUMA mode")
        root_source, app_source = workspace / "root_source", workspace / "app_source"
        context, carrier, app_lock, recipe = (workspace / n for n in ("context", "carrier", "app_lock", "recipe"))
        recipe_pin = os.environ.get("RECIPE_PIN", "")
        for repo, pin, label in ((root_source, ROOT_SOURCE_PIN, "ROOT source"),
                                 (app_source, APP_PIN, "APP source"),
                                 (context, ROOT_CONTEXT_PIN, "context"),
                                 (carrier, ROOT_PIN, "carrier"),
                                 (app_lock, APP_LOCK_PIN, "APP lock"),
                                 (recipe, recipe_pin, "recipe")):
            verify_repo(repo, pin, label)
        for ancestor in (ROOT_SOURCE_PIN, "91882528d942f8d35965a139cf8b78c6e37d7442"):
            git(recipe, "merge-base", "--is-ancestor", ancestor, "HEAD")
        cases_path, req_path = tracked(recipe, CASES), tracked(recipe, REQUIREMENTS)
        cases = json.loads(cases_path.read_text(encoding="utf-8"))
        if (cases.get("schema") != "epyc.vb.rtg23.w6e_carry.selected_cases.v1"
                or cases.get("count") != 31 or cases.get("root_source_commit") != ROOT_SOURCE_PIN
                or cases.get("app_source_commit") != APP_PIN):
            raise RuntimeError("selected-case manifest schema/count/source pin mismatch")
        expected_ancestry = ["d882143900b323093460d8286cbf973d41985213",
                             "419f4250b52d2a424e40da017992ede3c0251cdf",
                             "7a5e8852cf57c9cc94c343e288fc437482b3a728", ROOT_SOURCE_PIN]
        if cases.get("root_source_ancestry") != expected_ancestry:
            raise RuntimeError("ROOT source ancestry differs from the reviewed adapter/write/trace sequence")
        for source_commit in expected_ancestry[:-1]:
            if subprocess.run(["git", "-C", str(root_source), "merge-base", "--is-ancestor",
                               source_commit, ROOT_SOURCE_PIN]).returncode != 0:
                raise RuntimeError("reviewed ROOT source ancestry is incomplete")
        rows = cases.get("cases")
        if not isinstance(rows, list) or len(rows) != 31 or len({r.get("nodeid") for r in rows}) != 31:
            raise RuntimeError("selected identities are incomplete or duplicated")
        expected = {(r["classname"], r["name"]) for r in rows}
        if len(expected) != 31 or any(r.get("nodeid") != f"tests/vidya/test_autopilot_journal_adapter.py::{r['name']}" for r in rows):
            raise RuntimeError("case identity does not match the complete module")
        root_paths = verify_map(root_source, cases["root_source_files"], "ROOT")
        app_paths = verify_map(app_source, cases["app_source_files"], "APP")
        if len(cases["root_source_files"]) != 11 or len(cases["app_source_files"]) != 22:
            raise RuntimeError("static import/data closure count differs from reviewed map")
        lock = tracked(app_lock, "uv.lock")
        lock_entry = tomllib.loads(lock.read_text(encoding="utf-8"))
        requirement_text = req_path.read_text(encoding="utf-8")
        req_rows = {}
        active = None
        for line in requirement_text.splitlines():
            import re
            match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^ ]+) \\", line)
            if match:
                name = match.group(1).lower().replace("_", "-")
                if name in req_rows:
                    raise RuntimeError(f"duplicate locked requirement: {name}")
                active = name
                req_rows[name] = {"version": match.group(2), "hashes": set()}
            else:
                match = re.fullmatch(r"\s+--hash=sha256:([0-9a-f]{64})(?: \\)?", line)
                if match and active:
                    req_rows[active]["hashes"].add("sha256:" + match.group(1))
                elif line.strip() and not line.lstrip().startswith("#"):
                    raise RuntimeError("unexpected lock requirement syntax")
        expected_names = {"iniconfig", "packaging", "pluggy", "pygments", "pytest", "pyyaml"}
        packages = {p["name"].lower().replace("_", "-"): p for p in lock_entry["package"]}
        if set(req_rows) != expected_names or len(req_rows) != 6:
            raise RuntimeError("requirement set is not the exact six-package test closure")
        installed = {d.metadata["Name"].lower().replace("_", "-"): d.version
                     for d in __import__("importlib.metadata", fromlist=["distributions"]).distributions()}
        locked_dependencies = {}
        for name in sorted(expected_names):
            pkg = packages.get(name)
            if not pkg:
                raise RuntimeError(f"package absent from pinned APP lock: {name}")
            wheels = {w["hash"] for w in pkg.get("wheels", []) if w.get("hash", "").startswith("sha256:")}
            if (not wheels or req_rows[name]["version"] != pkg["version"]
                    or req_rows[name]["hashes"] != wheels or installed.get(name) != pkg["version"]):
                raise RuntimeError(f"exact package version or complete wheel-hash set mismatch: {name}")
            locked_dependencies[name] = {"version": pkg["version"], "wheel_hashes": sorted(wheels)}
        mode, oid = tree_entry(app_lock, "uv.lock")
        if mode != "100644" or oid != tree_entry(app_source, "uv.lock")[1]:
            raise RuntimeError("APP lock pin differs from writer checkout lock")

        for relative in (TASK, SOURCE_TABLE, VB_PROGRAM):
            if "VB-RTG23-W6E-DIAGNOSTIC-CARRY" not in tracked(context, relative).read_text(encoding="utf-8"):
                raise RuntimeError("pinned enrollment context lacks exact carry identity")
        workflow, driver = tracked(recipe, WORKFLOW), tracked(recipe, DRIVER)
        carrier_files = [tracked(carrier, "scripts/ci/native_conformance.py")]
        root_carrier_file = tracked(root_source, "scripts/ci/native_conformance.py")
        if sha(root_carrier_file) != sha(carrier_files[0]):
            raise RuntimeError("ROOT source does not carry the exact reviewed shared native implementation")
        context_paths = [tracked(context, TASK), tracked(context, SOURCE_TABLE), tracked(context, VB_PROGRAM)]
        source_manifest = result / "source-manifest.json"
        environment_path = result / "environment.json"
        pre_status = result / "pre-status.json"
        install_log = result / "pip-install.log"
        freeze_file = result / "pip-freeze.txt"
        read_paths = [workflow, driver, cases_path, req_path, lock, *root_paths, *app_paths,
                      *carrier_files, *context_paths, source_manifest, environment_path,
                      pre_status, install_log, freeze_file]
        source_trace_state = optional_state(app_source, "data/trace/events.sqlite")
        manifest_rows = []
        for repo, pin, entries in ((root_source, ROOT_SOURCE_PIN, cases["root_source_files"]),
                                   (app_source, APP_PIN, cases["app_source_files"])):
            for item in entries:
                manifest_rows.append({"repository": str(repo.name), "pin": pin,
                                      "size_bytes": tracked(repo, item["path"]).stat().st_size, **item})
        for label, repo, pin, relatives in (
                ("context", context, ROOT_CONTEXT_PIN, (TASK, SOURCE_TABLE, VB_PROGRAM)),
                ("carrier", carrier, ROOT_PIN, ("scripts/ci/native_conformance.py",)),
                ("app_lock", app_lock, APP_LOCK_PIN, ("uv.lock",))):
            for relative in relatives:
                path = tracked(repo, relative)
                mode, oid = tree_entry(repo, relative)
                manifest_rows.append({"repository": label, "pin": pin, "path": relative,
                                      "git_mode": mode, "git_blob": oid, "sha256": sha(path),
                                      "size_bytes": path.stat().st_size})
        for relative in (WORKFLOW, DRIVER, CASES, REQUIREMENTS):
            path = tracked(recipe, relative)
            mode, oid = tree_entry(recipe, relative)
            manifest_rows.append({"repository": "recipe", "pin": recipe_pin, "path": relative,
                                  "git_mode": mode, "git_blob": oid, "sha256": sha(path),
                                  "size_bytes": path.stat().st_size})
        source_manifest.write_text(json.dumps({
            "schema": "epyc.vb.rtg23.w6e_carry.source_manifest.v1",
            "repositories": {"root_source": ROOT_SOURCE_PIN, "app_source": APP_PIN,
                             "context": ROOT_CONTEXT_PIN, "carrier": ROOT_PIN,
                             "app_lock": APP_LOCK_PIN, "recipe": recipe_pin},
            "inputs": manifest_rows,
            "runtime_data_inputs": [source_trace_state],
            "locked_dependencies_from_app_uv_lock": locked_dependencies,
            "selected_cases": {"count": 31, "identities": [r["nodeid"] for r in rows]},
        }, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        if not pre_status.is_file():
            raise RuntimeError("bootstrap pre-status missing")
        for required in (pre_status, install_log, freeze_file):
            sha(required)
        environment_path.write_text(json.dumps({
            "python_version": platform.python_version(), "python_executable": sys.executable,
            "venv_prefix": sys.prefix, "base_prefix": sys.base_prefix,
            "repositories": {"root_source": ROOT_SOURCE_PIN, "app_source": APP_PIN,
                             "context": ROOT_CONTEXT_PIN, "carrier": ROOT_PIN,
                             "app_lock": APP_LOCK_PIN, "recipe": recipe_pin},
            "expected_environment": {**ENV, **isolated}, "event": os.environ.get("GITHUB_EVENT_NAME"),
            "ref": os.environ.get("GITHUB_REF"), "sha": os.environ.get("GITHUB_SHA"),
            "host": platform.platform(), "architecture": platform.machine(), "os_release": os_release,
            "pytest_disable_plugin_autoload": True, "conftest_disabled": True,
            "bytecode_disabled": True, "whole_test_module": True,
            "selected_case_count": 31, "decision_acceptance": None,
        }, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        for required in (pre_status, install_log, freeze_file, source_manifest, environment_path):
            sha(required)
        readset_before = {str(p): sha(p) for p in dict.fromkeys(read_paths)}
        from importlib.util import module_from_spec, spec_from_file_location
        carrier_file = carrier_files[0]
        spec = spec_from_file_location("pinned_native_conformance", carrier_file)
        api = module_from_spec(spec)
        sys.modules[spec.name] = api
        spec.loader.exec_module(api)
        pytest_tmp = result / "pytest-tmp"
        pytest_tmp.mkdir()
        junit = result / "original-junit.xml"
        argv = [sys.executable, "-m", "pytest", "-c", "/dev/null", "--noconftest",
                "--rootdir", str(root_source), "--import-mode=importlib", "-p", "no:cacheprovider",
                "-o", "addopts=", "-q", *SELECTIONS, f"--basetemp={pytest_tmp}", f"--junitxml={junit}"]
        os.environ["PYTHONPATH"] = os.pathsep.join((str(root_source), str(app_source)))
        status.update(state="running", selected_case_count=31,
                      repositories={"root_source": ROOT_SOURCE_PIN, "app_source": APP_PIN,
                                    "context": ROOT_CONTEXT_PIN, "carrier": ROOT_PIN,
                                    "app_lock": APP_LOCK_PIN, "recipe": recipe_pin})
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
        result_before_capture = snapshot(result, {"status.json"})
        boundary="capture"
        durable_custody(result/"pre-capture-custody.json", {"source_readset_before":readset_before,"source_default_trace_db_before":source_trace_state,"full_typed_result_tree_before_capture":result_before_capture})
        record = api.capture_fixture_execution(
            argv=argv, cwd=root_source, junit=junit, output=result / "native",
            repositories={"root_source": root_source, "app_source": app_source,
                          "context": context, "carrier": carrier, "app_lock": app_lock,
                          "recipe": recipe}, read_paths=read_paths, selections=list(r["nodeid"] for r in rows))
        status.update(fixture_execution_conformant=record.get("fixture_execution_conformant"),
                      original_outcome_preserved=True, promotion_or_release_acceptance=None)
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
        after_capture_before_shared_grade = snapshot(result, {"status.json"})
        source_readset_after_capture = {str(p): sha(p) for p in dict.fromkeys(read_paths)}
        source_trace_after_capture = optional_state(app_source, "data/trace/events.sqlite")
        if source_trace_state != source_trace_after_capture:
            raise RuntimeError("APP checkout default trace database changed during capture")
        if readset_before != source_readset_after_capture:
            raise RuntimeError("declared source/environment/setup readset changed during capture")
        junit_path = result / "native" / "original-junit.xml"
        actual = set()
        try:
            info = junit_path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise RuntimeError("captured JUnit is not a single-link regular file")
            junit_root = ET.fromstring(regular_bytes(junit_path))
            actual = {(x.get("classname", ""), x.get("name", ""))
                      for x in junit_root.iter("testcase")}
        except FileNotFoundError:
            pass
        native_ok = record.get("fixture_execution_conformant") is True
        counts = ((record.get("summary") or {}).get("counts") or {})
        exact_cases = (actual == expected and len(actual) == 31
                       and counts.get("collected") == 31 and counts.get("executed") == 31
                       and counts.get("passed") == 31 and counts.get("skipped") == 0
                       and counts.get("failure") == 0 and counts.get("error") == 0)
        after_capture_readset = {str(p): sha(p) for p in dict.fromkeys(read_paths)}
        source_trace_after_capture = optional_state(app_source, "data/trace/events.sqlite")
        if source_trace_state != source_trace_after_capture:
            raise RuntimeError("APP checkout default trace database changed during test capture")
        sys.path.insert(0, str(root_source))
        sys.path.insert(0, str(root_source / "scripts" / "vidya"))
        from adapters import autopilot_journal as apj
        import measurement_record
        original_repo_root = measurement_record.REPO_ROOT
        custody_rows = cases.get("real_writer_cases")
        if not isinstance(custody_rows, list) or len(custody_rows) != 3 or cases.get("real_writer_row_count") != 4:
            raise RuntimeError("real-writer custody manifest must name three cases and four original rows")
        custody_cases = {row["case_id"]: row for row in custody_rows}
        if len(custody_cases) != 3 or sum(row.get("expected_rows") for row in custody_rows) != 4:
            raise RuntimeError("real-writer custody case identities or row totals are invalid")
        custody = []
        custody_error = None
        boundary="journal_and_outer_grade"
        durable_custody(result/"pre-grade-custody.json", {"source_readset_before":readset_before,"source_readset_after_capture_before_grade":source_readset_after_capture,"source_default_trace_db_before":source_trace_state,"source_default_trace_db_after_capture_before_grade":source_trace_after_capture,"full_typed_result_tree_after_capture_before_grade":after_capture_before_shared_grade,"original_native_record":record})
        original_pregrade_tree=snapshot(result,{"status.json"})
        grade_rows = []
        marker_paths = sorted(pytest_tmp.rglob(".vidya-real-writer-custody.json"))
        try:
            if len(marker_paths) != 3:
                raise RuntimeError(f"expected three per-test real-writer custody markers, got {len(marker_paths)}")
            seen_cases = set()
            for marker_path in marker_paths:
                marker_bytes_hash = sha(marker_path)
                marker = json.loads(regular_bytes(marker_path).decode("utf-8"))
                case_id = marker.get("case_id")
                if marker.get("schema") != "epyc.vidya.real_writer_custody.v1" or case_id not in custody_cases or case_id in seen_cases:
                    raise RuntimeError("invalid, duplicate, or unexpected real-writer case marker")
                seen_cases.add(case_id)
                case_root = marker_path.parent.resolve()
                if marker.get("root") != ".":
                    raise RuntimeError("custody marker root must be its test's tmp_path")
                def generated_input(relative):
                    parts = Path(relative).parts
                    if not parts or Path(relative).is_absolute() or any(p in {"", ".", ".."} for p in parts):
                        raise RuntimeError("non-normalized custody output path")
                    path = case_root
                    for index, part in enumerate(parts):
                        path = path / part
                        info = path.lstat()
                        if stat.S_ISLNK(info.st_mode) or (index < len(parts)-1 and not stat.S_ISDIR(info.st_mode)):
                            raise RuntimeError("custody output path traverses symlink/non-directory")
                    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                        raise RuntimeError("custody output is not a single-link regular file")
                    return path
                shard = generated_input(marker.get("journal_path", ""))
                trace_db = generated_input(marker.get("trace_path", ""))
                if sha(shard) != marker.get("journal_sha256") or sha(trace_db) != marker.get("trace_sha256"):
                    raise RuntimeError("real-writer journal or isolated SQLite hash differs from original custody marker")
                case_manifest = custody_cases[case_id]
                expected_shard = (Path(apj.ORCH_REL) / "orchestration" / "autopilot_journal.jsonl").as_posix()
                if (marker.get("journal_path") != expected_shard
                        or marker.get("journal_path") != case_manifest.get("journal_path")
                        or marker.get("trace_path") != case_manifest.get("trace_path")):
                    raise RuntimeError("custody marker points outside the exact test-local journal/trace paths")
                measurement_record.REPO_ROOT = case_root
                measured = [(src, row) for src, row in apj.iter_measured_rows(case_root)
                            if src.resolve() == shard.resolve()]
                if len(measured) != case_manifest["expected_rows"]:
                    raise RuntimeError(f"unexpected real rows for {case_id}: {len(measured)}")
                for src, row in measured:
                    rec = apj.as_record(src, row)
                    q, t, reasons = measurement_record.grade(rec)
                    grade_rows.append({"case_id": case_id, "case_root": str(case_root),
                                       "shard": str(src), "trial_id": row.get("trial_id"),
                                       "journal_sha256": marker["journal_sha256"],
                                       "trace_sha256": marker["trace_sha256"],
                                       "Q": q, "T": t, "reasons": reasons})
                custody.append({"case_id": case_id, "marker": str(marker_path),
                                "marker_sha256": marker_bytes_hash,
                                "root": str(case_root), "journal_path": str(shard),
                                "journal_sha256": marker["journal_sha256"],
                                "trace_path": str(trace_db), "trace_sha256": marker["trace_sha256"],
                                "measured_rows": len(measured)})
            if seen_cases != set(custody_cases) or len(grade_rows) != cases["real_writer_row_count"]:
                raise RuntimeError("real-writer custody did not resolve exactly four original rows")
        except Exception as exc:
            custody_error = f"{type(exc).__name__}: {exc}"
        finally:
            measurement_record.REPO_ROOT = original_repo_root

        # Grade only the native receipt through the existing CI verifier adapter and ClaimTuple ladder.
        # Original FALSE/NULL remain FALSE/NULL; this never authors candidate acceptance.
        outer_grade = None
        outer_grade_error = None
        try:
            sys.path.insert(0, str(root_source))
            sys.path.insert(0, str(root_source / "scripts" / "vidya"))
            from adapters import ci_conformance
            from claim_tuple import grade as claim_grade
            outer_rows = ci_conformance.native_rows(result / "native" / "receipt.json")
            if outer_rows:
                outer_claim = ci_conformance.project_ci_conformance(outer_rows[0])
                outer_grade = {"receipt_sha256": outer_rows[0]["receipt_sha256"],
                               "value": outer_claim.value, "grade": list(claim_grade(outer_claim))}
        except Exception as exc:
            outer_grade_error = f"{type(exc).__name__}: {exc}"

        if custody_error is not None or outer_grade_error is not None:
            durable_custody(result/"grade-error-custody.json", {
                "journal_grade_error":custody_error,"outer_grade_error":outer_grade_error,
                "source_readset_after_grade_error":{str(path):sha(path) for path in dict.fromkeys(read_paths)},
                "source_default_trace_db_after_grade_error":optional_state(app_source,"data/trace/events.sqlite"),
                "full_typed_result_tree_after_grade_error":snapshot(result,{"status.json"}),
                "original_native_record":record})

        (result / "journal-source-grades.json").write_text(json.dumps({
            "schema": "epyc.vb.rtg23.w6e_carry.original_writer_rows.v1",
            "custody_markers": custody, "rows": grade_rows if custody_error is None else [],
            "row_count": len(grade_rows) if custody_error is None else None,
            "diagnostic": custody_error,
            "grade_source": "existing measurement_record.grade; no new ladder or acceptance",
        }, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        (result / "shared-grade.json").write_text(json.dumps({
            "schema": "epyc.vidya.ci_fixture_shared_grade.v1",
            "outer_native_receipt": outer_grade,
            "diagnostic": outer_grade_error,
            "grade_source": "scripts/vidya/adapters/ci_conformance.py -> claim_tuple.grade",
            "promotion_or_release_acceptance": None,
        }, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        source_readset_after_grade = {str(p): sha(p) for p in dict.fromkeys(read_paths)}
        source_trace_after_grade = optional_state(app_source, "data/trace/events.sqlite")
        if source_trace_after_capture != source_trace_after_grade or source_readset_after_capture != source_readset_after_grade:
            raise RuntimeError("source or APP default trace DB changed during outer shared grade")
        after_grade = snapshot(result, {"status.json"})
        if any(after_grade.get(path)!=value for path,value in original_pregrade_tree.items()):
            raise RuntimeError("original result files or topology changed during grades")
        inventory = {"schema": "epyc.vb.rtg23.w6e_carry.run_root_inventory.v2",
                     "before_capture": result_before_capture,
                     "after_capture_before_shared_grade": after_capture_before_shared_grade,
                     "after_shared_grade": after_grade,
                     "source_readset_before": readset_before,
                     "source_readset_after_capture": source_readset_after_capture,
                     "source_readset_after_shared_grade": source_readset_after_grade,
                     "source_default_trace_db_before": source_trace_state,
                     "source_default_trace_db_after_capture": source_trace_after_capture,
                     "source_default_trace_db_after_shared_grade": source_trace_after_grade,
                     "real_writer_custody_count": len(custody),
                     "real_writer_row_grade_count": len(grade_rows) if custody_error is None else None,
                     "outer_shared_grade": outer_grade,
                     "promotion_or_release_acceptance": None}
        (result / "run-root-inventory.json").write_text(json.dumps(inventory, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        passed = (native_ok and exact_cases and custody_error is None and outer_grade_error is None
                  and outer_grade is not None and outer_grade.get("value") is True
                  and outer_grade.get("grade",[])[:2] == ["Judged","Located"])
        status.update(state="passed" if passed else "native_outcome_retained",
                      exit_code=0 if passed else 1,
                      fixture_execution_conformant=record.get("fixture_execution_conformant"),
                      junit_exact_case_set=exact_cases, selected_case_count=31,
                      real_writer_custody_count=len(custody),
                      real_writer_shared_grade_count=len(grade_rows) if custody_error is None else None,
                      real_writer_custody_diagnostic=custody_error,
                      outer_shared_grade=outer_grade, outer_shared_grade_diagnostic=outer_grade_error,
                      original_outcome_preserved=True, promotion_or_release_acceptance=None)
        return 0 if passed else 1
    except Exception as exc:
        error_record={"boundary":boundary,"error":f"{type(exc).__name__}: {exc}","source_snapshots":{},"snapshot_errors":{}}
        for source in dict.fromkeys(read_paths):
            try:error_record["source_snapshots"][str(source)]=sha(source)
            except Exception as snapshot_error:error_record["snapshot_errors"][str(source)]=f"{type(snapshot_error).__name__}: {snapshot_error}"
        try:error_record["full_typed_result_tree_after_exception"]=snapshot(result,{"status.json"})
        except Exception as snapshot_error:error_record["result_snapshot_error"]=f"{type(snapshot_error).__name__}: {snapshot_error}"
        if app_source is not None:
            try:error_record["source_default_trace_db_after_exception"]=optional_state(app_source,"data/trace/events.sqlite")
            except Exception as snapshot_error:error_record["default_db_snapshot_error"]=f"{type(snapshot_error).__name__}: {snapshot_error}"
        try:durable_custody(result/"error-custody.json",error_record)
        except Exception as custody_error:status["custody_error"]=f"{type(custody_error).__name__}: {custody_error}"
        status.update(state="capture_failed", exit_code=1, error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        result.mkdir(parents=True, exist_ok=True)
        status_path.write_text(json.dumps(status, sort_keys=True, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
