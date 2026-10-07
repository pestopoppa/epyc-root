"""Capture one existing documentation-reference validator execution via native CI receipt."""
from __future__ import annotations

import importlib.metadata
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[2]
PYTHON_PIN = "3.13.15"
CASES = ("scripts/ci/evl38_references_case.py::test_existing_governance_reference_validator_accepts_pinned_tree",)
LOCK_SOURCE_COMMIT = "70096b763939a43409a1f1827ab633d62425a6c1"
LOCK_SOURCE_BLOB = "ef2306018773ff9a1e80389970d92f66fcf8d5b7"
CONTEXT_COMMIT = "83004c1137015a9fc8d0cf411e648432bc51a1c9"
CARRIER_COMMIT = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
PACKAGES = {"pytest": "9.0.3", "iniconfig": "2.3.0", "packaging": "26.0",
            "pluggy": "1.6.0", "pygments": "2.20.0"}
WORKFLOW_INPUTS = (
    "scripts/ci/evl38_references_case.py", "scripts/ci/evl38_references_capture.py",
    "scripts/ci/evl38_references_requirements.txt", ".github/workflows/evl38-references-native.yml",
)


def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tracked_md_names() -> list[str]:
    names = subprocess.check_output(["git", "-C", str(ROOT), "ls-files", "-z"], text=False)
    return sorted(value.decode() for value in names.split(b"\0") if value.endswith(b".md"))


def _assignment(tree: ast.Module, name: str) -> ast.AST:
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == name for target in targets):
                return node.value
    raise RuntimeError(f"pinned validator no longer declares {name}")


def _constant_strings(node: ast.AST) -> list[str]:
    return [item.value for item in ast.walk(node)
            if isinstance(item, ast.Constant) and isinstance(item.value, str)]


def _rooted_path(node: ast.AST) -> str:
    if isinstance(node, ast.Name) and node.id == "ROOT":
        return ""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return "/".join(part for part in (_rooted_path(node.left), _rooted_path(node.right)) if part)
    raise RuntimeError("validator scan path expression changed")


def validator_inputs() -> tuple[list[Path], list[Path], list[dict[str, object]]]:
    """Derive scan sources/targets from the pinned validator AST and exact regex literals."""
    source = ROOT / "scripts/validate/validate_agents_references.py"
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    fixed_expr = _assignment(tree, "FIXED_FILES")
    if not isinstance(fixed_expr, (ast.List, ast.Tuple)):
        raise RuntimeError("validator FIXED_FILES is not a literal path list")
    fixed_values = [_rooted_path(item) for item in fixed_expr.elts]
    expected_fixed = ["CLAUDE.md", "agents/README.md", "agents/AGENT_INSTRUCTIONS.md",
                      "docs/guides/agent-workflows/INDEX.md",
                      "docs/reference/agent-config/CLAUDE_MD_MATRIX.md",
                      ".claude/commands/agent-files.md", ".claude/commands/agent-governance.md"]
    if fixed_values != expected_fixed:
        raise RuntimeError("validator FIXED_FILES shape changed; review readset derivation")
    scan_function = next((node for node in tree.body
                          if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                          and node.name == "scan_files"), None)
    if scan_function is None:
        raise RuntimeError("validator scan_files function is absent")
    glob_calls = [call for call in ast.walk(scan_function)
             if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
             and call.func.attr == "glob" and call.args
             and isinstance(call.args[0], ast.Constant)]
    globs = [(_rooted_path(call.func.value), call.args[0].value) for call in glob_calls]
    expected_globs = [("agents", "*.md"), ("agents/shared", "*.md"),
                      ("docs/guides/agent-workflows", "*.md")]
    if globs != expected_globs:
        raise RuntimeError("validator scan glob shape changed; review source enumeration")
    source_dirs = [directory for directory, _pattern in globs]
    names = set(fixed_values)
    for name in tracked_md_names():
        if any(name.startswith(prefix + "/") and "/" not in name[len(prefix) + 1:]
               for prefix in source_dirs):
            names.add(name)
    source_paths = sorted(ROOT / name for name in names)
    if any(not path.is_file() for path in source_paths):
        raise RuntimeError("a declared validator scan source is missing")

    regexes = {}
    for name in ("CODE_REF", "MD_LINK", "ANCHOR_LINK", "HEADING"):
        values = _constant_strings(_assignment(tree, name))
        if len(values) != 1:
            raise RuntimeError(f"validator regex {name} did not resolve to one literal")
        regexes[name] = re.compile(values[0], re.MULTILINE if name == "HEADING" else 0)
    targets: dict[str, dict[str, object]] = {}
    for path in source_paths:
        text = path.read_text(encoding="utf-8")
        ordinary = set(regexes["CODE_REF"].findall(text)) | set(regexes["MD_LINK"].findall(text))
        anchored = set(regexes["ANCHOR_LINK"].findall(text))
        references = {(ref, None) for ref in ordinary} | anchored
        for ref, anchor in sorted(references, key=lambda item: (item[0], item[1] or "")):
            cleaned = ref.split(":", 1)[0]
            ignored = (ref.startswith(("http://", "https://")) or any(ch in cleaned for ch in "*<>")
                       or any(token in cleaned for token in ("YYYY", "MM-DD", "NNN")))
            if ignored or cleaned == "SKILL.md":
                continue
            candidate = Path(cleaned)
            if not candidate.is_absolute():
                local = (path.parent / candidate).resolve()
                candidate = local if local.exists() else (ROOT / candidate).resolve()
            exists = candidate.exists()
            key = str(candidate)
            row = targets.setdefault(key, {"path": key, "exists": exists, "references": []})
            row["references"].append({"source": str(path), "ref": ref, "anchor": anchor})
    captured = {path.resolve() for path in source_paths}
    for row in targets.values():
        path = Path(row["path"])
        if row["exists"] and path.is_file():
            captured.add(path.resolve())
    return (source_paths, sorted(captured),
            sorted(targets.values(), key=lambda row: str(row["path"])))


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


def result_snapshot(root: Path) -> dict[str, dict[str, object]]:
    snapshot = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise RuntimeError(f"result tree contains a symlink: {path}")
        relative = path.relative_to(root).as_posix()
        if relative == "status.json":
            continue
        if path.is_dir():
            snapshot[relative + "/"] = {"kind": "directory"}
            continue
        data = regular_bytes(path)
        snapshot[relative] = {"kind": "regular_file", "bytes": len(data), "sha256": digest(data)}
    return snapshot


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit("usage: evl38_references_capture.py CARRIER_ROOT LOCK_SOURCE_ROOT CONTEXT_ROOT")
    carrier_root = Path(sys.argv[1]).resolve()
    lock_source = Path(sys.argv[2]).resolve()
    context_root = Path(sys.argv[3]).resolve()
    if subprocess.check_output(["git", "-C", str(context_root), "rev-parse", "HEAD"], text=True).strip() != CONTEXT_COMMIT:
        raise SystemExit("enrollment context differs from the reviewed pin")
    if subprocess.check_output(["git", "-C", str(context_root), "status", "--porcelain", "--untracked-files=no"], text=True).strip():
        raise SystemExit("enrollment context has tracked modifications")
    expected_root = os.environ.get("GITHUB_SHA")
    if not expected_root or git("rev-parse", "HEAD") != expected_root:
        raise SystemExit("EVL38 references checkout differs from the triggering GitHub commit")
    if git("status", "--porcelain", "--untracked-files=no"):
        raise SystemExit("EVL38 references ROOT has tracked modifications")
    if sys.version.split()[0] != PYTHON_PIN:
        raise SystemExit("EVL38 references runner Python mismatch")
    if os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD") != "1":
        raise SystemExit("pytest plugin autoload must be disabled")
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise SystemExit("bytecode writes must be disabled")
    if os.environ.get("PYTEST_ADDOPTS", "") or os.environ.get("PYTEST_PLUGINS", ""):
        raise SystemExit("inherited pytest options and plugins must be empty")
    if (subprocess.check_output(["git", "-C", str(carrier_root), "rev-parse", "HEAD"], text=True).strip()
            != CARRIER_COMMIT):
        raise SystemExit("immutable native carrier checkout differs from the reviewed pin")
    if subprocess.check_output(["git", "-C", str(carrier_root), "status", "--porcelain", "--untracked-files=no"], text=True).strip():
        raise SystemExit("immutable native carrier checkout has tracked modifications")
    installed_packages = verify_locked_packages(lock_source, ROOT / "scripts/ci/evl38_references_requirements.txt")

    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    venv_path = runner_temp / "evl38-references" / "venv"
    if Path(sys.prefix).resolve() != venv_path:
        raise SystemExit("capture is not running inside the isolated RUNNER_TEMP environment")
    result = runner_temp / "evl38-references" / "result"
    if not result.is_dir() or not (result / "status.json").is_file():
        raise SystemExit("workflow artifact envelope was not initialized before setup")
    if os.path.lexists(result / "native"):
        raise SystemExit("native capture output already exists")
    junit = result / "selected.xml"
    capture = result / "native"
    (result / "environment.json").write_text(
        json.dumps({"python": sys.version, "executable": sys.executable,
                    "packages": installed_packages,
                    "pytest_plugin_autoload": os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"],
                    "pytest_addopts": os.environ.get("PYTEST_ADDOPTS", ""),
                    "pytest_plugins": os.environ.get("PYTEST_PLUGINS", ""),
                    "bytecode_disabled": os.environ["PYTHONDONTWRITEBYTECODE"]},
                   sort_keys=True, indent=2) + "\n", encoding="utf-8")
    pytest = Path(sys.executable)
    command = [str(pytest), "-m", "pytest", "-q", "--noconftest", "-c", "/dev/null",
               "--rootdir", str(ROOT), "--import-mode=importlib", "-o", "addopts=", "-p", "no:cacheprovider",
               f"--junitxml={junit}", "scripts/ci/evl38_references_case.py"]
    source_paths, captured_paths, targets = validator_inputs()
    enrollment = {
        "source_table": "scripts/vidya/adapters/README.md",
        "task": "handoffs/active/vidya-belief-substrate-program.md",
        "task_id": "VB-EVL38-REFERENCE-CONFORMANCE",
    }
    for relative in (enrollment["source_table"], enrollment["task"]):
        if enrollment["task_id"] not in (context_root / relative).read_text(encoding="utf-8"):
            raise RuntimeError("reviewed EVL38 references enrollment is absent from the pinned context commit")
    source_context = result / "validator-input-map.json"
    source_context.write_text(json.dumps({"schema": "epyc.evl38.references.inputs/v1",
        "validator": "scripts/validate/validate_agents_references.py",
        "scan_sources": [str(path) for path in source_paths], "resolved_targets": targets,
        "enrollment": enrollment}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    carrier_path = carrier_root / "scripts/ci/native_conformance.py"
    adapter_path = carrier_root / "scripts/vidya/adapters/ci_conformance.py"
    adapter_init_path = carrier_root / "scripts/vidya/adapters/__init__.py"
    claim_tuple_path = carrier_root / "scripts/vidya/claim_tuple.py"
    grade_dependencies = [carrier_root / f"scripts/vidya/{name}.py"
                          for name in ("canonical", "frames", "lattice")]
    if git("rev-parse", "HEAD") != expected_root:
        raise SystemExit("ROOT changed while the validator readset was derived")
    read_paths = ([ROOT / name for name in WORKFLOW_INPUTS]
                  + [ROOT / "scripts/validate/validate_agents_references.py",
                     context_root / enrollment["source_table"], context_root / enrollment["task"], source_context,
                     result / "install.log", result / "pip-freeze.txt", result / "environment.json"]
                  + captured_paths + [carrier_path, adapter_path, adapter_init_path, claim_tuple_path,
                                  *grade_dependencies, lock_source / "uv.lock"])
    read_paths = list(dict.fromkeys(path.resolve() for path in read_paths))
    for path in read_paths:
        regular_bytes(path)
    result_before_capture = result_snapshot(result)
    (result / "result-before-capture.json").write_text(
        json.dumps(result_before_capture, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    read_paths.append(result / "result-before-capture.json")
    read_paths = list(dict.fromkeys(path.resolve() for path in read_paths))
    source_before = source_snapshot(read_paths)
    sys.path.insert(0, str(carrier_root))
    sys.path.insert(1, str(carrier_root / "scripts" / "vidya"))
    import scripts.ci.native_conformance as pinned_imported_carrier
    carrier = pinned_imported_carrier
    if pinned_imported_carrier.__file__ != str(carrier_path):
        raise RuntimeError("shared-grade adapter would resolve a different native carrier")
    from scripts.vidya.adapters import ci_conformance
    from claim_tuple import grade

    record = carrier.capture_fixture_execution(
        argv=command, cwd=ROOT, junit=junit, output=capture,
        repositories={"root": ROOT, "carrier": carrier_root, "pytest_lock_source": lock_source, "enrollment_context": context_root},
        read_paths=read_paths, selections=list(CASES),
    )
    summary = record.get("summary")
    cases = summary.get("cases") if isinstance(summary, dict) else None
    if not isinstance(cases, list):
        (result / "native-outcome.json").write_text(json.dumps({
            "fixture_execution_conformant": None,
            "diagnostic": record.get("diagnostic", "native receipt has no JUnit summary"),
            "receipt": "native/receipt.json"}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        return 1
    expected_identity = {"classname": "scripts.ci.evl38_references_case",
                         "name": "test_existing_governance_reference_validator_accepts_pinned_tree"}
    if (len(cases) != 1 or any(cases[0].get(key) != value
                               for key, value in expected_identity.items())):
        (result / "native-outcome.json").write_text(json.dumps({
            "fixture_execution_conformant": None,
            "diagnostic": "native JUnit identities differ from the one declared validator case",
            "observed_cases": cases, "receipt": "native/receipt.json"}, sort_keys=True, indent=2) + "\n",
            encoding="utf-8")
        return 1
    before_grade_result = result_snapshot(result)
    rows = ci_conformance.native_rows(capture / "receipt.json")
    if len(rows) != 1:
        (result / "native-outcome.json").write_text(json.dumps({
            "fixture_execution_conformant": record.get("fixture_execution_conformant"),
            "diagnostic": "native adapter did not yield one projectable row",
            "receipt": "native/receipt.json"}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        return 1
    claim = ci_conformance.project_ci_conformance(rows[0])
    shared = grade(claim)
    source_after_grade = source_snapshot(read_paths)
    after_grade_result = result_snapshot(result)
    if source_after_grade != source_before:
        raise SystemExit("pinned source/readset bytes changed across execution and shared grading")
    if after_grade_result != before_grade_result:
        raise SystemExit("original result artifacts changed during shared grading")
    (result / "custody-snapshots.json").write_text(json.dumps({
        "source_before_capture_and_grade": source_before,
        "source_after_grade": source_after_grade,
        "result_before_capture": result_before_capture,
        "result_before_grade": before_grade_result,
        "result_after_grade": after_grade_result,
        "excluded_mutable_status": "status.json only"}, sort_keys=True, indent=2) + "\n",
        encoding="utf-8")
    (result / "shared-grade.json").write_text(
        json.dumps({"receipt_sha256": rows[0]["receipt_sha256"],
                    "value": claim.value, "grade": list(shared)}, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    (result / "driver-summary.json").write_text(
        json.dumps({"case_count": record["summary"]["counts"]["collected"],
                    "cases": record["summary"]["cases"],
                    "conformant": record["fixture_execution_conformant"],
                    "receipt": "native/receipt.json"}, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"result": str(result), "conformant": record["fixture_execution_conformant"],
                      "grade": list(shared)}))
    return 0 if record.get("fixture_execution_conformant") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
