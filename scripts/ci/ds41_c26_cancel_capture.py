#!/usr/bin/env python3
"""Pinned whole-suite C26 native source CI capture; imported only on the hosted runner."""
from collections import Counter
import ast
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import stat
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath

ROOT_BRANCH = "codex/ni08-c26-cancel-native-recipe-20261007"
SOURCE_PIN = "0858dc64c752c0b683695198fc80e92d68f974c8"
LOCK_PIN = "70096b763939a43409a1f1827ab633d62425a6c1"
CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
LOCK_SHA256 = "7eae6b0447832155673e18f0e9f849fd4a65e3eb5839bf85f4165b13a4b06ca3"
REQUIREMENTS_SHA256 = "4ee14a40ffe8c3ae198a2a692100cd718c15c224f53eeca43a1d6067f3b6c1b7"
MANIFEST_PATH = "scripts/ci/ds41_c26_cancel_cases_junit_v2.json"
ROOT_MAP_PATH = "scripts/ci/ds41_c26_cancel_source_map.json"
CLOSURE_PATH = "scripts/ci/ds41_c26_cancel_closure.json"
LOCK_META_PATH = "scripts/ci/ds41_c26_cancel_lock_closure.json"
REQUIREMENTS_PATH = "scripts/ci/ds41_c26_cancel_requirements.txt"
CAPTURE_PATH = "scripts/ci/ds41_c26_cancel_capture.py"
VERIFY_PATH = "scripts/ci/ds41_c26_cancel_junit_verify.py"
WORKFLOW_PATH = ".github/workflows/ds41-c26-cancel-source-ci.yml"
ENV_KEYS = ("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTHONDONTWRITEBYTECODE", "PYTHONHASHSEED", "PYTHONNOUSERSITE", "PYTHONUNBUFFERED")
ENV_EXPECTED = {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0", "PYTHONNOUSERSITE": "1", "PYTHONUNBUFFERED": "1"}
CARRIER_FILES = {
    "scripts/ci/native_conformance.py": "2b8c63121e1472d10849224911ee8f4035b7f758ce1aefca7c766e2de263aa0e",
    "scripts/vidya/adapters/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "scripts/vidya/adapters/ci_conformance.py": "aceba149c1b3386e2edd0f8ce5b0bd6bb1d4489d0fe3b3275f8984050aeeb19c",
    "scripts/vidya/claim_tuple.py": "058749d2a1ce3487672e85cc5a18fd352b6f17e741a47d7f48bb55be278f4bfe",
    "scripts/vidya/lattice.py": "a889442eecf1887f5d5a4a1193dc0d7760efb668cf31cda21e1d226ec8b24da2",
    "scripts/vidya/frames.py": "f47f148218ae99d54c51b322bf4f3b0632d4458e49572843f5ed4aa424d15749",
    "scripts/vidya/canonical.py": "cda6809d24382cbbfa80308c9f8df4eca353f458039816753b1c20156adf1434",
}

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def stable(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())

def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.PIPE).decode().strip()

def require_pin(repo, expected, label):
    head = git(repo, "rev-parse", "HEAD")
    if head != expected or git(repo, "status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError(label + " checkout differs from the exact clean pin")
    return head

def regular_bytes(path):
    if path.is_symlink():
        raise RuntimeError("declared regular input is a symlink: " + str(path))
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise RuntimeError("declared input is not a single-link regular file: " + str(path))
        digest = hashlib.sha256(); data = bytearray()
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk); data.extend(chunk)
        after = os.fstat(fd)
        identity = lambda row: (row.st_dev, row.st_ino, row.st_mode, row.st_size, row.st_nlink, row.st_mtime_ns, row.st_ctime_ns)
        if identity(before) != identity(after) or len(data) != after.st_size:
            raise RuntimeError("input changed while being read: " + str(path))
        return bytes(data), digest.hexdigest(), stat.S_IMODE(after.st_mode)
    finally:
        os.close(fd)

def typed_tree(root, *, omit_status=True, omit_self=None):
    if root.is_symlink() or not stat.S_ISDIR(root.lstat().st_mode):
        raise RuntimeError("custody root is not a real directory")
    found = {".": {"kind": "directory", "mode": stat.S_IMODE(root.lstat().st_mode)}}
    def walk(directory):
        for entry in sorted(os.scandir(directory), key=lambda row: row.name):
            path = Path(entry.path); mode = entry.stat(follow_symlinks=False).st_mode
            rel = path.relative_to(root).as_posix()
            if omit_status and rel == "status.json":
                continue
            if omit_self and rel == omit_self:
                continue
            if stat.S_ISLNK(mode):
                target = os.readlink(path).encode("utf-8", "surrogateescape")
                found[rel] = {"kind": "symlink_opaque", "mode": stat.S_IMODE(mode), "target_bytes": len(target), "target_sha256": sha(target)}
            elif stat.S_ISDIR(mode):
                found[rel + "/"] = {"kind": "directory", "mode": stat.S_IMODE(mode)}; walk(path)
            elif stat.S_ISREG(mode):
                raw, digest, actual_mode = regular_bytes(path)
                found[rel] = {"kind": "regular", "mode": actual_mode, "bytes": len(raw), "sha256": digest}
            else:
                raise RuntimeError("special custody entry: " + rel)
    walk(root)
    return found

def durable_json(path, value):
    if path.exists() or path.is_symlink():
        raise RuntimeError("refusing to overwrite custody record: " + path.name)
    payload = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        row = os.fstat(fd)
        if not stat.S_ISREG(row.st_mode) or row.st_nlink != 1:
            raise RuntimeError("custody record is not a single-link regular file")
        os.write(fd, payload); os.fsync(fd)
    finally:
        os.close(fd)


def norm_dist(name):
    return "-".join(filter(None, re.split(r"[-_.]+", name.lower())))

def verify_locked_closure(lock_raw, lock_meta, requirements_raw):
    lock = tomllib.loads(lock_raw.decode("utf-8"))
    packages = {norm_dist(row["name"]): row for row in lock["package"]}
    roots = lock_meta["external_module_to_distribution"]
    todo = list(dict.fromkeys(roots.values())); chosen = set(); skipped = []
    while todo:
        name = norm_dist(todo.pop())
        if name in chosen:
            continue
        row = packages.get(name)
        if row is None:
            raise RuntimeError("APP lock is missing selected external distribution: " + name)
        chosen.add(name)
        for dep in row.get("dependencies", []):
            marker = dep.get("marker", "")
            if not marker:
                todo.append(dep["name"])
            elif marker == "sys_platform == 'win32'":
                skipped.append({"package": name, "dependency": norm_dist(dep["name"]), "marker": marker, "reason": "workflow runner is ubuntu-24.04"})
            elif marker == "python_full_version < '3.13'":
                skipped.append({"package": name, "dependency": norm_dist(dep["name"]), "marker": marker, "reason": "workflow Python is 3.13.15"})
            elif "extra ==" in marker:
                skipped.append({"package": name, "dependency": norm_dist(dep["name"]), "marker": marker, "reason": "no extras selected"})
            else:
                raise RuntimeError("unreviewed dependency marker in exact APP lock: " + repr((name, dep)))
    if chosen != {norm_dist(row["name"]) for row in lock_meta["packages"]}:
        raise RuntimeError("transitive actual APP-lock package closure differs")
    if sorted(skipped, key=lambda row: json.dumps(row, sort_keys=True)) != sorted(lock_meta["skipped_marked_dependencies"], key=lambda row: json.dumps(row, sort_keys=True)):
        raise RuntimeError("actual APP-lock marker dispositions differ")
    actual_records = []
    for name in sorted(chosen):
        row = packages[name]
        hashes = sorted(wheel["hash"] for wheel in row.get("wheels", []))
        expected = next(item for item in lock_meta["packages"] if norm_dist(item["name"]) == name)
        if row["version"] != expected["version"] or hashes != sorted(expected["wheel_hashes"]):
            raise RuntimeError("exact package version/wheel hashes differ from lock metadata: " + name)
        actual_records.append((name, row["version"], hashes))
    parsed = {}; current = None
    for line in requirements_raw.decode("utf-8").splitlines():
        if "==" in line:
            left = line.split("\\", 1)[0].strip()
            name, version = left.split("==", 1)
            current = norm_dist(name); parsed[current] = {"version": version, "hashes": []}
        elif "--hash=sha256:" in line:
            if current is None:
                raise RuntimeError("requirements hash is not attached to a locked package")
            parsed[current]["hashes"].append("sha256:" + line.split("--hash=sha256:", 1)[1].split()[0].rstrip("\\"))
        elif line.strip():
            raise RuntimeError("unexpected locked requirements syntax")
    if set(parsed) != chosen:
        raise RuntimeError("requirements package set differs from transitive lock closure")
    for name, version, hashes in actual_records:
        if parsed[name]["version"] != version or sorted(parsed[name]["hashes"]) != sorted(hashes):
            raise RuntimeError("requirements versions or all-wheel hash rows differ: " + name)
    if sum(len(hashes) for _, _, hashes in actual_records) != lock_meta["all_wheel_hash_records"]:
        raise RuntimeError("all locked wheel-hash record count differs")
    return actual_records

def source_rows(source, closure):
    tree = {}
    raw = subprocess.check_output(["git", "-C", str(source), "ls-tree", "-r", "-z", "--full-tree", SOURCE_PIN])
    for item in raw.split(b"\0"):
        if not item:
            continue
        meta, path = item.split(b"\t", 1)
        mode, kind, oid = meta.decode().split()
        tree[path.decode("utf-8", "surrogateescape")] = (mode, kind, oid)
    rows = closure["full_python_config_envelope"]["files"]
    expected_paths = {row["path"] for row in rows}
    selected = set()
    for path, (mode, kind, oid) in tree.items():
        name = PurePosixPath(path).name; suffix = PurePosixPath(path).suffix
        if kind == "blob" and mode in ("100644", "100755") and (path.endswith(".py") or name in {"pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini", "uv.lock", "requirements.txt", "requirements-dev.txt", "requirements-test.txt"} or suffix in {".toml", ".ini", ".cfg", ".yaml", ".yml"}):
            selected.add(path)
    if selected != expected_paths or len(rows) != len(expected_paths):
        raise RuntimeError("full tracked Python/config envelope path set differs")
    actual_rows = {}
    for row in rows:
        path = source / row["path"]
        raw, digest, mode = regular_bytes(path)
        tree_mode, kind, oid = tree.get(row["path"], (None, None, None))
        git_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if (kind, tree_mode, oid, git_blob, len(raw), digest, f"{mode:04o}") != ("blob", row["mode"], row["blob"], row["blob"], row["bytes"], row["sha256"], format(int(row["mode"], 8) & 0o777, "04o")):
            raise RuntimeError("source envelope blob/mode/bytes/hash differs: " + row["path"])
        actual_rows[row["path"]] = digest
    return actual_rows

def junit_cases(path):
    root = ET.parse(path).getroot()
    rows = []
    for node in root.iter("testcase"):
        identity = (node.attrib.get("classname", ""), node.attrib.get("name", ""))
        if not all(identity):
            raise RuntimeError("JUnit testcase lacks exact classname/name")
        if any(node.find(name) is not None for name in ("failure", "error", "skipped")):
            raise RuntimeError("JUnit contains failure/error/skip: " + repr(identity))
        rows.append(identity)
    if len(rows) != len(set(rows)):
        raise RuntimeError("JUnit contains duplicate identities")
    return rows

def main():
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    repos = {name: workspace / name for name in ("recipe", "context", "source", "locksource", "carrier")}
    run = temp / "ds41-c26"
    result = run / "result"; status_path = result / "status.json"
    if run.is_symlink() or not run.is_dir() or result.is_symlink() or not result.is_dir() or status_path.is_symlink() or not status_path.is_file():
        raise RuntimeError("workflow-created C26 custody root/status is missing or unsafe")
    status = json.loads(regular_bytes(status_path)[0])
    for leaf in ("home", "tmp"):
        private = run / leaf
        if private.exists() or private.is_symlink():
            raise RuntimeError("refusing existing private runner home/temp path")
        private.mkdir(mode=0o700)
        os.environ["HOME" if leaf == "home" else "TMPDIR"] = str(private)
    for key in ("LD_LIBRARY_PATH", "LD_PRELOAD", "PYTHONHOME", "PYTHONPATH"):
        os.environ.pop(key, None)
    if status.get("capture_started") is not False or status.get("state") != "setup_pending":
        raise RuntimeError("workflow status is not the original pre-capture setup record")
    read_paths = []; boundary = "setup"; native_receipt = None; junit = result / "original-junit.xml"
    error_record = None
    try:
        if platform.system() != "Linux" or platform.python_version() != "3.13.15":
            raise RuntimeError("runtime differs from the reviewed Linux/Python 3.13.15 context")
        if Path(sys.prefix).resolve() != (temp / "c26-venv").resolve() or sys.prefix == sys.base_prefix:
            raise RuntimeError("isolated venv identity differs")
        if {key: os.environ.get(key) for key in ENV_KEYS} != ENV_EXPECTED:
            raise RuntimeError("reviewed deterministic pytest environment differs")
        if os.environ.get("SOURCE_PIN") != SOURCE_PIN or os.environ.get("LOCK_PIN") != LOCK_PIN or os.environ.get("CARRIER_PIN") != CARRIER_PIN:
            raise RuntimeError("workflow pins differ from this reviewed runner")
        if os.environ.get("GITHUB_EVENT_NAME") != "push" or os.environ.get("GITHUB_REF") != "refs/heads/" + ROOT_BRANCH:
            raise RuntimeError("only the exact reviewed push event on the frozen recipe branch is allowed")
        source_pin = require_pin(repos["source"], SOURCE_PIN, "source")
        lock_pin = require_pin(repos["locksource"], LOCK_PIN, "lock source")
        carrier_pin = require_pin(repos["carrier"], CARRIER_PIN, "native CI carrier")
        recipe_pin = require_pin(repos["recipe"], os.environ["GITHUB_SHA"], "recipe")
        root_map_path = repos["recipe"] / ROOT_MAP_PATH
        root_map = json.loads(regular_bytes(root_map_path)[0])
        if root_map.get("schema") != "private.ds41_c26_native_recipe_binding.draft.v1" or root_map.get("source_pin") != SOURCE_PIN or root_map.get("lock_pin") != LOCK_PIN or root_map.get("carrier_pin") != CARRIER_PIN:
            raise RuntimeError("native recipe map source/lock/carrier bindings differ")
        context_pin = root_map.get("root_context_pin")
        if not context_pin or context_pin != os.environ.get("ROOT_CONTEXT_PIN"):
            raise RuntimeError("MAIN-applied root enrollment/context pin is absent or differs from workflow")
        require_pin(repos["context"], context_pin, "ROOT enrollment context")
        for row in root_map.get("root_context_files", []):
            data, digest, mode = regular_bytes(repos["context"] / row["path"])
            if digest != row["sha256"] or mode != int(row["mode"], 8) & 0o777:
                raise RuntimeError("MAIN-applied ROOT enrollment file bytes/mode differ: " + row["path"])
            content = data.decode("utf-8")
            if any(marker not in content for marker in row.get("required_markers", [])):
                raise RuntimeError("MAIN-applied ROOT enrollment marker missing: " + row["path"])
        if sys.prefix == sys.base_prefix:
            raise RuntimeError("test runner is not isolated")
        manifest_path = repos["recipe"] / MANIFEST_PATH
        closure_path = repos["recipe"] / CLOSURE_PATH
        lock_meta_path = repos["recipe"] / LOCK_META_PATH
        requirements_path = repos["recipe"] / REQUIREMENTS_PATH
        manifest = json.loads(regular_bytes(manifest_path)[0])
        root_map = json.loads(regular_bytes(root_map_path)[0])
        source_map = root_map
        closure = json.loads(regular_bytes(closure_path)[0])
        lock_meta = json.loads(regular_bytes(lock_meta_path)[0])
        if manifest["source_pin"] != SOURCE_PIN or manifest["expected_total"] != 46:
            raise RuntimeError("whole-case manifest pin/count differs")
        if root_map.get("case_manifest_sha256") != sha(regular_bytes(manifest_path)[0]) or root_map.get("closure_sha256") != sha(regular_bytes(closure_path)[0]) or root_map.get("lock_meta_sha256") != sha(regular_bytes(lock_meta_path)[0]) or root_map.get("requirements_sha256") != sha(regular_bytes(requirements_path)[0]):
            raise RuntimeError("frozen C26 manifest/closure/lock/requirements bindings differ")
        lock_raw = regular_bytes(repos["locksource"] / "uv.lock")[0]
        lock_git_row = git(repos["locksource"], "ls-tree", LOCK_PIN, "--", "uv.lock").split()
        lock_binding = root_map.get("dependency_lock_git_input", {})
        requirements_raw = regular_bytes(requirements_path)[0]
        if sha(lock_raw) != LOCK_SHA256 or lock_meta["lock_sha256"] != LOCK_SHA256 or root_map.get("lock_sha256") != LOCK_SHA256 or (len(lock_raw), sha(lock_raw), lock_git_row[0], lock_git_row[2]) != (lock_binding["bytes"], lock_binding["sha256"], lock_binding["mode"], lock_binding["blob"]):
            raise RuntimeError("actual APP lock Git mode/blob/bytes differ")
        if sha(requirements_raw) != REQUIREMENTS_SHA256:
            raise RuntimeError("locked requirement bytes differ")
        verify_locked_closure(lock_raw, lock_meta, requirements_raw)
        installed = {pkg["name"].lower().replace("_", "-"): importlib.metadata.version(pkg["name"]) for pkg in lock_meta["packages"]}
        expected_versions = {pkg["name"].lower().replace("_", "-"): pkg["version"] for pkg in lock_meta["packages"]}
        if installed != expected_versions:
            raise RuntimeError("installed dependency versions differ from the locked closure")
        source_digests = source_rows(repos["source"], closure)
        for row in source_map.get("source_product_files", []):
            raw, digest, mode = regular_bytes(repos["source"] / row["path"])
            tree_row = git(repos["source"], "ls-tree", SOURCE_PIN, "--", row["path"]).split()
            ast_digest = sha(ast.dump(ast.parse(raw.decode("utf-8"), filename=row["path"]), include_attributes=False).encode())
            if (len(raw), digest, mode, tree_row[0], tree_row[2], ast_digest) != (row["bytes"], row["sha256"], int(row["mode"], 8) & 0o777, row["mode"], row["blob"], row["ast_sha256"]):
                raise RuntimeError("exact four-file source product blob/mode/bytes/AST differs: " + row["path"])
        expected_cases = [(row["classname"], row["name"]) for row in manifest["testcases"]]
        if len(expected_cases) != 46 or len(set(expected_cases)) != 46 or closure.get("case_total") != 46:
            raise RuntimeError("expected JUnit identity inventory is not 46 unique cases")
        read_paths = [repos["carrier"] / p for p in CARRIER_FILES]
        carrier_rows = {row["path"]: row for row in source_map.get("carrier_files", [])}
        if set(carrier_rows) != set(CARRIER_FILES):
            raise RuntimeError("unchanged native carrier full exact file inventory differs")
        for relative, expected_sha in CARRIER_FILES.items():
            raw, digest, mode = regular_bytes(repos["carrier"] / relative)
            tree_row = git(repos["carrier"], "ls-tree", CARRIER_PIN, "--", relative).split()
            frozen = carrier_rows[relative]
            if digest != expected_sha or (len(raw), digest, mode, tree_row[0], tree_row[2]) != (frozen["bytes"], frozen["sha256"], int(frozen["mode"], 8) & 0o777, frozen["mode"], frozen["blob"]):
                raise RuntimeError("unchanged native carrier source blob/mode/bytes differ: " + relative)
        read_paths += [repos["source"] / p for p in closure["selection"]]
        read_paths += [repos["source"] / row["path"] for row in closure["full_python_config_envelope"]["files"]]
        read_paths += [manifest_path, root_map_path, closure_path, lock_meta_path, requirements_path,
                       repos["recipe"] / CAPTURE_PATH, repos["recipe"] / VERIFY_PATH, repos["recipe"] / WORKFLOW_PATH,
                       repos["locksource"] / "uv.lock"]
        # MAIN-applied source owner/VB/table records are pinned and added to context readset
        # by the final source map; no locally invented source or grading class is used here.
        read_paths += [repos["context"] / "handoffs/active/deepseek-v41-flash-evaluation.md",
                       repos["context"] / "handoffs/active/vidya-belief-substrate-program.md",
                       repos["context"] / "scripts/vidya/adapters/README.md"]
        read_paths = list(dict.fromkeys(path.resolve() for path in read_paths))
        recipe_file_rows = source_map.get("recipe_files", [])
        if any(row.get("path") == ROOT_MAP_PATH for row in recipe_file_rows):
            raise RuntimeError("recursive source-map row must remain self-excluded")
        for row in recipe_file_rows:
            data, digest, mode = regular_bytes(repos["recipe"] / row["path"])
            if len(data) != row["bytes"] or digest != row["sha256"] or mode != int(row["mode"], 8) & 0o777:
                raise RuntimeError("ROOT recipe source-file bytes/mode differ: " + row["path"])
            if hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() != row["blob"]:
                raise RuntimeError("ROOT recipe source-file blob differs: " + row["path"])
        for path in read_paths:
            regular_bytes(path)
        environment = {key: os.environ.get(key) for key in (*ENV_KEYS, "PATH", "HOME", "TMPDIR", "PYTHONPATH", "PYTHONHOME", "LD_LIBRARY_PATH", "LD_PRELOAD", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA", "GITHUB_REF", "GITHUB_JOB")}
        (result / "environment.json").write_text(json.dumps({"python": sys.version, "platform": platform.platform(), "env": environment, "source_claim": "whole C26 stop-cancellation source controls only", "excluded_warrants": ["live DS41 runtime", "model/inference behavior", "quality/performance", "host lock/actor behavior"]}, sort_keys=True, indent=2) + "\n")
        (result / "pip-freeze.txt").write_text("\n".join(f"{name}=={version}" for name, version in sorted(installed.items())) + "\n")
        source_before = {str(path): regular_bytes(path)[1] for path in read_paths}
        pre_capture_tree = typed_tree(result)
        durable_json(result / "pre-capture-custody.json", {"phase": "before_native_invocation", "source_inventory": source_before, "source_inventory_sha256": stable(source_before), "typed_result_tree_before_capture": pre_capture_tree, "typed_result_tree_sha256": stable(pre_capture_tree), "scope": "complete selected source/config envelope, runner, lock and pre-run result tree; modes included, symlinks opaque"})
        test_command = [sys.executable, "-m", "pytest", "--noconftest", "-c", "/dev/null", "--import-mode=importlib", "--rootdir=" + str(repos["source"]), "-o", "addopts=", "-p", "no:cacheprovider", "-q", *[str(p) for p in closure["selection"]], "--basetemp=" + str(result / "pytest-worlds"), "--junitxml=" + str(junit)]
        env = dict(os.environ); env["PYTHONPATH"] = str(repos["source"] / "scripts/kernel_rnd") + os.pathsep + str(repos["source"])
        argv = [sys.executable, str(repos["carrier"] / "scripts/ci/native_conformance.py"), "--cwd", str(repos["source"]), "--junit", str(junit), "--output", str(result / "native"), "--repo", "recipe=" + str(repos["recipe"]), "--repo", "context=" + str(repos["context"]), "--repo", "source=" + str(repos["source"]), "--repo", "lock=" + str(repos["locksource"]), "--repo", "carrier=" + str(repos["carrier"])]
        for path in read_paths:
            argv += ["--read-path", str(path)]
        for row in manifest["testcases"]:
            argv += ["--select", row["classname"] + "::" + row["name"]]
        boundary = "capture"; status.update(state="running", capture_started=True, repositories={"recipe": recipe_pin, "context": context_pin, "source": source_pin, "lock": lock_pin, "carrier": carrier_pin}); status_path.write_text(json.dumps(status, sort_keys=True) + "\n")
        result_code = subprocess.run([*argv, "--", *test_command], cwd=repos["source"], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        (result / "native-command.stdout").write_bytes(result_code.stdout)
        (result / "native-command.exit").write_text(str(result_code.returncode) + "\n")
        receipt_path = result / "native" / "receipt.json"
        if not receipt_path.is_file() or receipt_path.is_symlink():
            raise RuntimeError("native carrier produced no original receipt")
        native_receipt = json.loads(regular_bytes(receipt_path)[0]); status["native_receipt_state"] = "native_true" if native_receipt.get("fixture_execution_conformant") is True else "native_false_or_null"
        summary = native_receipt.get("summary") or {}; counts = summary.get("counts") or {}; summary_cases = summary.get("cases") or []
        receipt_exact = Counter((row.get("classname"), row.get("name")) for row in summary_cases) == Counter(expected_cases)
        sys.path.insert(0, str(repos["recipe"] / "scripts/ci"))
        from ds41_c26_cancel_junit_verify import verify as verify_original_junit
        try:
            case_verification = verify_original_junit(repos["source"], manifest_path, junit)
            junit_exact = True
        except Exception as verify_error:
            case_verification = {"result": "FAIL", "error_type": type(verify_error).__name__, "error": str(verify_error)}
            junit_exact = False
        (result / "junit-verification.json").write_text(json.dumps({"source_body_parameter_and_junit_verification": case_verification, "carrier_receipt_exact_identities": receipt_exact, "expected_case_total": 46}, sort_keys=True, indent=2) + "\n")
        source_before_grade = {str(path): regular_bytes(path)[1] for path in read_paths}
        pregrade_tree_without_record = typed_tree(result)
        boundary = "pre_grade"
        durable_json(result / "pre-grade-custody.json", {"phase": "original_receipt_before_existing_shared_grade", "source_before_capture": source_before, "source_after_capture_before_grade": source_before_grade, "source_stable": source_before == source_before_grade, "carrier_receipt_exact_cases": receipt_exact, "junit_exact_cases": junit_exact, "typed_result_tree_after_capture_before_pregrade_record": pregrade_tree_without_record, "typed_result_tree_sha256": stable(pregrade_tree_without_record), "native_receipt": native_receipt, "original_exit_code": result_code.returncode})
        result_before_grade = typed_tree(result)
        # The existing carrier, projector and shared grade are the unchanged authorities.
        sys.path.insert(0, str(repos["carrier"])); sys.path.insert(0, str(repos["carrier"] / "scripts/vidya"))
        from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
        from claim_tuple import grade
        grades = []
        for row in native_rows(receipt_path):
            claim = project_ci_conformance(row); q, t, reasons = grade(claim)
            grades.append({"measurement_id": claim.measurement_id, "Q": q, "T": t, "reasons": reasons})
        source_after_grade = {str(path): regular_bytes(path)[1] for path in read_paths}
        result_after_grade = typed_tree(result)
        source_stable = source_before == source_before_grade == source_after_grade
        result_stable_across_grade = result_before_grade == result_after_grade
        durable_json(result / "shared-grade-custody.json", {"phase": "unchanged_existing_native_CI_projector_and_shared_grader", "typed_result_tree_before_grade": result_before_grade, "typed_result_tree_after_grade_before_this_record": result_after_grade, "source_before_capture": source_before, "source_before_grade": source_before_grade, "source_after_grade": source_after_grade, "source_stable": source_stable, "result_stable_across_grade": result_stable_across_grade, "grades": grades, "new_grade_authored": False})
        if not receipt_exact or not junit_exact:
            raise RuntimeError("original native/JUnit identities differ from the full source-body/parameter manifest")
        if result_code.returncode != 0 or native_receipt.get("fixture_execution_conformant") is not True:
            raise RuntimeError("whole native source-control suite did not conform")
        if counts.get("collected") != 46 or counts.get("executed") != 46 or counts.get("passed") != 46 or any(counts.get(key, 0) for key in ("failure", "error", "skipped")):
            raise RuntimeError("native receipt full-suite counts are not exactly 46 passed")
        if not source_stable or not result_stable_across_grade:
            raise RuntimeError("frozen source/result tree changed across native execution or shared grade")
        if len(grades) != 1 or (grades[0]["Q"], grades[0]["T"]) != ("Judged", "Located"):
            raise RuntimeError("existing shared grader did not give the original conformant CI row its native grade")
        final_tree = typed_tree(result)
        status.update(state="passed", exit_code=0, fixture_execution_conformant=True, junit_counts=counts, exact_cases=True, shared_grade=grades, final_typed_tree_sha256=stable(final_tree), native_receipt_state="native_true")
        return 0
    except Exception as exc:
        error_record = {"phase": boundary, "capture_started": status.get("capture_started", False), "native_receipt_state": status.get("native_receipt_state", "no_receipt"), "error_type": type(exc).__name__, "error_message": str(exc), "native_receipt": native_receipt, "source_inventory_before_capture": source_before if "source_before" in locals() else None, "proposition_invented": False}
        status.update(state="capture_failed", exit_code=1, failure_stage=boundary, error_type=type(exc).__name__, error_message=str(exc))
        return 1
    finally:
        try:
            if error_record is not None and not (result / "error-custody.json").exists():
                snapshots = {}
                for path in read_paths:
                    try: snapshots[str(path)] = regular_bytes(path)[1]
                    except Exception as exc: snapshots[str(path)] = {"snapshot_error": type(exc).__name__}
                error_record.update(source_after_error=snapshots, source_after_error_sha256=stable(snapshots), typed_result_tree_after_error=typed_tree(result, omit_self="error-custody.json"), status_excluded=True, error_record_self_excluded=True)
                durable_json(result / "error-custody.json", error_record)
                status["error_custody_state"] = "written before final status"
        except Exception as custody_exc:
            status["error_custody_state"] = "failed: " + type(custody_exc).__name__
        try:
            final_path = result / "final-custody.json"
            if not final_path.exists() and not final_path.is_symlink():
                final_tree = typed_tree(result, omit_self="final-custody.json")
                final_sources = {}
                for path in read_paths:
                    try: final_sources[str(path)] = regular_bytes(path)[1]
                    except Exception as source_exc: final_sources[str(path)] = {"snapshot_error": type(source_exc).__name__}
                durable_json(final_path, {"phase": "final_terminal_capture_state", "status_before_final_status_write": status, "native_receipt": native_receipt, "source_inventory_at_final": final_sources, "source_inventory_sha256": stable(final_sources), "typed_result_tree_before_final_custody_record": final_tree, "typed_result_tree_sha256": stable(final_tree), "status_excluded": True, "final_record_self_excluded": True, "error_record_must_precede_final_record": error_record is None or (result / "error-custody.json").is_file()})
                status["final_custody_state"] = "written before final status"
        except Exception as final_exc:
            status["final_custody_state"] = "failed: " + type(final_exc).__name__
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n")

if __name__ == "__main__":
    raise SystemExit(main())
