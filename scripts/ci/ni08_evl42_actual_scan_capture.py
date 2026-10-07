#!/usr/bin/env python3
"""Capture one unchanged Research pin scan through the existing CI carrier."""
from __future__ import annotations
import hashlib
from collections import Counter
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import stat
import subprocess
import sys
import tomllib

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.ci.pin_report_fixture import (capture_report_fixture,
    read_scan_invocation_fixture)
from scripts.ci.native_conformance import capture_fixture_execution, read_receipt

RESEARCH_PIN = "5c945406cd49f424694de9be4b8716b88e9aa6f9"
ROOT_SOURCE_BASE = "7123a103e5a9e185d819e218e6759ba739c180d2"
CHECKER_SHA256 = "2fc0680f070cc2f051bd8d74b66748a1c00e09f3d8d8f229ab46b9167152e666"
SOURCE_MAP_SHA256 = "253de0744c1116d56bb59a91c9bc05e73e7630fa110ee0fd57a4aaaaca537c1c"
LOCK_PIN = "70096b763939a43409a1f1827ab633d62425a6c1"
LOCK_SHA256 = "7eae6b0447832155673e18f0e9f849fd4a65e3eb5839bf85f4165b13a4b06ca3"
LOCK_BLOB = "ef2306018773ff9a1e80389970d92f66fcf8d5b7"
LOCKED_PACKAGES = {"iniconfig": "2.3.0", "packaging": "26.0", "pluggy": "1.6.0",
                   "Pygments": "2.20.0", "pytest": "9.0.3"}
LITERAL_BRANCH = "codex/ni08-evl42-actual-scan-20261007"
CASE = "test_actual_research_pin_scan_attachment"
CONTROL_CASES = (
    "test_actual_report_roundtrip_preserves_current_stale_and_unknown",
    "test_actual_report_metadata_drift_is_refused",
    "test_original_report_hash_and_duplicate_json_fields_are_refused",
    "test_report_writer_refuses_overwrite_and_symlink_parents",
    "test_missing_scanned_checker_remains_incomplete_without_tuple_upgrade",
    "test_failed_file_or_directory_fsync_removes_only_owned_report_for_retry",
    "test_actual_native_attachment_projection_preserves_true_false_null",
    "test_actual_original_attachment_refuses_absent_tampered_or_mixed_receipts",
    "test_partial_write_is_removed_without_deleting_unrelated_output",
    "test_failure_cleanup_refuses_to_unlink_replaced_exclusive_name",
    "test_scan_invocation_sidecar_preserves_exact_output_bytes",
    "test_scan_invocation_refusal_preserves_original_error_without_report",
    "test_scan_invocation_strict_reader_controls",
    "test_scan_extra_output_declaration_rejects_overlap",
)
CONTROL_CASE_COUNT = 44  # 29 unchanged compatibility instances + 15 new controls
EXPECTED_CONTROL_CASES = (
    ('tests.ci.test_pin_report_fixture', 'test_actual_report_roundtrip_preserves_current_stale_and_unknown[current]'),
    ('tests.ci.test_pin_report_fixture', 'test_actual_report_roundtrip_preserves_current_stale_and_unknown[stale]'),
    ('tests.ci.test_pin_report_fixture', 'test_actual_report_roundtrip_preserves_current_stale_and_unknown[missing]'),
    ('tests.ci.test_pin_report_fixture', 'test_actual_report_roundtrip_preserves_current_stale_and_unknown[unresolved]'),
    ('tests.ci.test_pin_report_fixture', 'test_actual_report_metadata_drift_is_refused[count]'),
    ('tests.ci.test_pin_report_fixture', 'test_actual_report_metadata_drift_is_refused[complete]'),
    ('tests.ci.test_pin_report_fixture', 'test_actual_report_metadata_drift_is_refused[git_stable]'),
    ('tests.ci.test_pin_report_fixture', 'test_actual_report_metadata_drift_is_refused[checker_match]'),
    ('tests.ci.test_pin_report_fixture', 'test_actual_report_metadata_drift_is_refused[boolean_count]'),
    ('tests.ci.test_pin_report_fixture', 'test_actual_report_metadata_drift_is_refused[scope]'),
    ('tests.ci.test_pin_report_fixture', 'test_actual_report_metadata_drift_is_refused[dirty_count]'),
    ('tests.ci.test_pin_report_fixture', 'test_actual_report_metadata_drift_is_refused[unread_source]'),
    ('tests.ci.test_pin_report_fixture', 'test_actual_report_metadata_drift_is_refused[path_normalization]'),
    ('tests.ci.test_pin_report_fixture', 'test_original_report_hash_and_duplicate_json_fields_are_refused'),
    ('tests.ci.test_pin_report_fixture', 'test_report_writer_refuses_overwrite_and_symlink_parents'),
    ('tests.ci.test_pin_report_fixture', 'test_missing_scanned_checker_remains_incomplete_without_tuple_upgrade'),
    ('tests.ci.test_pin_report_fixture', 'test_failed_file_or_directory_fsync_removes_only_owned_report_for_retry[file]'),
    ('tests.ci.test_pin_report_fixture', 'test_failed_file_or_directory_fsync_removes_only_owned_report_for_retry[directory]'),
    ('tests.ci.test_pin_report_fixture', 'test_actual_native_attachment_projection_preserves_true_false_null[current_TRUE]'),
    ('tests.ci.test_pin_report_fixture', 'test_actual_native_attachment_projection_preserves_true_false_null[stale_TRUE]'),
    ('tests.ci.test_pin_report_fixture', 'test_actual_native_attachment_projection_preserves_true_false_null[missing_TRUE]'),
    ('tests.ci.test_pin_report_fixture', 'test_actual_native_attachment_projection_preserves_true_false_null[unresolved_TRUE]'),
    ('tests.ci.test_pin_report_fixture', 'test_actual_native_attachment_projection_preserves_true_false_null[current_FALSE]'),
    ('tests.ci.test_pin_report_fixture', 'test_actual_native_attachment_projection_preserves_true_false_null[current_NULL]'),
    ('tests.ci.test_pin_report_fixture', 'test_actual_original_attachment_refuses_absent_tampered_or_mixed_receipts[absent]'),
    ('tests.ci.test_pin_report_fixture', 'test_actual_original_attachment_refuses_absent_tampered_or_mixed_receipts[tampered]'),
    ('tests.ci.test_pin_report_fixture', 'test_actual_original_attachment_refuses_absent_tampered_or_mixed_receipts[mixed]'),
    ('tests.ci.test_pin_report_fixture', 'test_partial_write_is_removed_without_deleting_unrelated_output'),
    ('tests.ci.test_pin_report_fixture', 'test_failure_cleanup_refuses_to_unlink_replaced_exclusive_name'),
    ('tests.ci.test_pin_report_fixture', 'test_scan_invocation_sidecar_preserves_exact_output_bytes[current_rc0]'),
    ('tests.ci.test_pin_report_fixture', 'test_scan_invocation_sidecar_preserves_exact_output_bytes[stale_rc1]'),
    ('tests.ci.test_pin_report_fixture', 'test_scan_invocation_refusal_preserves_original_error_without_report'),
    ('tests.ci.test_pin_report_fixture', 'test_scan_invocation_strict_reader_controls[sidecar_tamper]'),
    ('tests.ci.test_pin_report_fixture', 'test_scan_invocation_strict_reader_controls[report_tamper]'),
    ('tests.ci.test_pin_report_fixture', 'test_scan_invocation_strict_reader_controls[rc_mismatch]'),
    ('tests.ci.test_pin_report_fixture', 'test_scan_invocation_strict_reader_controls[report_absent]'),
    ('tests.ci.test_pin_report_fixture', 'test_scan_invocation_strict_reader_controls[sidecar_absent]'),
    ('tests.ci.test_pin_report_fixture', 'test_scan_invocation_strict_reader_controls[duplicate]'),
    ('tests.ci.test_pin_report_fixture', 'test_scan_invocation_strict_reader_controls[malformed_stdout]'),
    ('tests.ci.test_pin_report_fixture', 'test_scan_invocation_strict_reader_controls[raw_bytes]'),
    ('tests.ci.test_pin_report_fixture', 'test_scan_extra_output_declaration_rejects_overlap[duplicate_report]'),
    ('tests.ci.test_pin_report_fixture', 'test_scan_extra_output_declaration_rejects_overlap[duplicate_extra]'),
    ('tests.ci.test_pin_report_fixture', 'test_scan_extra_output_declaration_rejects_overlap[report_parent]'),
    ('tests.ci.test_pin_report_fixture', 'test_scan_extra_output_declaration_rejects_overlap[extra_parent]'),
)
REPORT_RELATIVE = "ci-capture-output/pin-report.json"
INVOCATION_RELATIVE = "ci-capture-output/pin-invocation.json"
ENVIRONMENT = {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTEST_ADDOPTS": "",
    "PYTEST_PLUGINS": "", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0",
    "PYTHONUNBUFFERED": "1"}


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def require_clean(repo: Path, label: str) -> str:
    if git(repo, "status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError(label + " checkout is not clean before capture")
    head = git(repo, "rev-parse", "HEAD")
    if len(head) != 40 or any(char not in "0123456789abcdef" for char in head):
        raise RuntimeError(label + " HEAD is invalid")
    return head


def file_identity(path: Path) -> dict:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise RuntimeError("scan input is not a single-link regular file: " + str(path))
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            total += len(chunk)
        after = os.fstat(fd)
        key = lambda item: (item.st_dev, item.st_ino, item.st_mode, item.st_size,
                            item.st_nlink, item.st_mtime_ns, item.st_ctime_ns)
        if key(before) != key(after) or total != after.st_size:
            raise RuntimeError("scan input changed while reading: " + str(path))
        named = path.lstat()
        if key(after) != key(named):
            raise RuntimeError("scan input path changed while reading: " + str(path))
        return {"mode": stat.S_IMODE(after.st_mode), "bytes": total,
                "sha256": digest.hexdigest()}
    finally:
        os.close(fd)


def tracked_scan_files(root: Path) -> dict[str, dict]:
    raw = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z", "--",
                                   "scripts/benchmark"])
    paths = sorted(item.decode("utf-8") for item in raw.split(b"\0")
                   if item.endswith(b".py"))
    if not paths or len(paths) != len(set(paths)):
        raise RuntimeError("tracked Research benchmark Python inventory is empty or duplicated")
    result = {}
    for relative in paths:
        parsed = PurePosixPath(relative)
        if (parsed.is_absolute() or parsed.as_posix() != relative or ".." in parsed.parts
                or parsed.parts[:2] != ("scripts", "benchmark") or parsed.suffix != ".py"):
            raise RuntimeError("unsafe tracked scan member: " + relative)
        path = root.joinpath(*parsed.parts)
        mode = git(root, "ls-tree", "HEAD", "--", relative).split("\t", 1)[0].split()
        if not mode or mode[0] not in {"100644", "100755"}:
            raise RuntimeError("tracked scan member is not a regular Git blob: " + relative)
        result[relative] = file_identity(path)
    return result


def verify_requirements(requirements: Path, lock_path: Path) -> None:
    versions, hashes, pending = {}, {}, ""
    for raw in requirements.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        continued = line.endswith("\\")
        pending += " " + (line[:-1].rstrip() if continued else line)
        if continued:
            continue
        match = re.fullmatch(r"\s*([A-Za-z0-9_.-]+)==([^\s]+)\s+((?:--hash=sha256:[0-9a-f]{64}\s*)+)", pending)
        if not match:
            raise RuntimeError("malformed exact hash-locked requirement")
        name, version, wheel_tokens = match.groups()
        name = name.lower()
        if name in versions:
            raise RuntimeError("duplicate locked requirement")
        versions[name] = version
        hashes[name] = set(re.findall(r"--hash=sha256:([0-9a-f]{64})", wheel_tokens))
        pending = ""
    if pending or versions != {name.lower(): version for name, version in LOCKED_PACKAGES.items()}:
        raise RuntimeError("minimal pinned pytest closure differs")
    packages = {item["name"].lower(): item for item in
                tomllib.loads(lock_path.read_text(encoding="utf-8"))["package"]}
    for raw_name, version in LOCKED_PACKAGES.items():
        name = raw_name.lower()
        item = packages.get(name)
        expected_hashes = {wheel.get("hash", "").removeprefix("sha256:")
                           for wheel in (item or {}).get("wheels", [])
                           if re.fullmatch(r"sha256:[0-9a-f]{64}", wheel.get("hash", ""))}
        if (not item or item.get("version") != version or not expected_hashes
                or expected_hashes != hashes[name]):
            raise RuntimeError("ALL-wheel APP lock closure differs: " + name)


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    recipe = workspace / "recipe"
    research = workspace / "research"
    lock_source = workspace / "lock-source"
    run = Path(os.environ["RUNNER_TEMP"]).resolve() / "evl42-actual-scan"
    status_path = run / "status.json"
    status = {"state": "preparing", "native_metric": None}
    if run.is_symlink() or not run.is_dir() or status_path.is_symlink() or not status_path.is_file():
        raise RuntimeError("fresh hosted capture directory/status file missing")
    try:
        if platform.python_version() != "3.13.15" or platform.system() != "Linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
            raise RuntimeError("reviewed Python/Linux runtime differs")
        if Path(sys.prefix).resolve() != run / "venv" or sys.prefix == sys.base_prefix:
            raise RuntimeError("isolated reviewed venv differs")
        for name, value in ENVIRONMENT.items():
            if os.environ.get(name) != value:
                raise RuntimeError("pytest environment differs: " + name)
        pins = {"recipe": os.environ["GITHUB_SHA"],
                "research": RESEARCH_PIN,
                "lock-source": LOCK_PIN}
        repos = {"recipe": recipe, "research": research, "lock-source": lock_source}
        actual = {name: require_clean(path, name) for name, path in repos.items()}
        if actual != pins:
            raise RuntimeError("pinned checkout identities differ")
        subprocess.run(["git", "-C", str(recipe), "merge-base", "--is-ancestor",
                        ROOT_SOURCE_BASE, "HEAD"], check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.PIPE)
        if (os.environ.get("GITHUB_REF") != "refs/heads/" + LITERAL_BRANCH
                or os.environ.get("GITHUB_EVENT_NAME") != "push"):
            raise RuntimeError("only the exact literal private push branch is eligible")
        if git(lock_source, "rev-parse", "HEAD:uv.lock") != LOCK_BLOB:
            raise RuntimeError("explicit APP lock blob differs")
        lock = lock_source / "uv.lock"
        if hashlib.sha256(lock.read_bytes()).hexdigest() != LOCK_SHA256:
            raise RuntimeError("explicit APP lock bytes differ")
        requirement_file = recipe / "scripts/ci/ni08_evl42_report_requirements.txt"
        verify_requirements(requirement_file, lock)
        if {name: importlib.metadata.version(name) for name in LOCKED_PACKAGES} != LOCKED_PACKAGES:
            raise RuntimeError("installed dependency versions differ")
        install_log = run / "dependency-install.log"
        pip_freeze = run / "pip-freeze.txt"
        if not install_log.is_file() or not pip_freeze.is_file():
            raise RuntimeError("original dependency installation/freeze evidence is absent")
        outputs = (recipe / "ci-capture-output",)
        if any(path.exists() or path.is_symlink() for path in outputs):
            raise RuntimeError("actual-scan output path already exists")

        handoff = recipe / "handoffs/active/vidya-belief-substrate-program.md"
        adapter_table = recipe / "scripts/vidya/adapters/README.md"
        if "SC-EVL42-PIN-REPORT-WIRING" not in handoff.read_text(encoding="utf-8"):
            raise RuntimeError("current owning handoff marker missing")
        if "Research benchmark pin scan prospective categorical report" not in adapter_table.read_text(encoding="utf-8"):
            raise RuntimeError("current source-table row missing")

        scan_before = tracked_scan_files(research)
        source_map_path = recipe / "scripts/ci/ni08_evl42_actual_source_map.json"
        if hashlib.sha256(source_map_path.read_bytes()).hexdigest() != SOURCE_MAP_SHA256:
            raise RuntimeError("frozen actual-scan source map differs")
        source_map = json.loads(source_map_path.read_text(encoding="utf-8"))
        if (set(source_map) != {"schema", "research_head", "research_files", "root_source_base", "root_files"}
                or source_map["schema"] != "epyc.ni08.evl42.actual_source_map.v1"
                or source_map["research_head"] != RESEARCH_PIN
                or source_map["root_source_base"] != ROOT_SOURCE_BASE):
            raise RuntimeError("frozen actual-scan source map schema/pin differs")
        for name, identity in source_map["root_files"].items():
            if file_identity(recipe / name) != identity:
                raise RuntimeError("ROOT source/import/config differs from frozen source map: " + name)
        frozen_files = source_map["research_files"]
        frozen_scan = {name: identity for name, identity in frozen_files.items()
                       if name.startswith("scripts/benchmark/") and name.endswith(".py")}
        if scan_before != frozen_scan:
            raise RuntimeError("actual scanner membership/bytes differ from frozen source map")
        for name in ("pyproject.toml", "uv.lock"):
            if file_identity(research / name) != frozen_files[name]:
                raise RuntimeError("Research config/lock differs from frozen source map: " + name)
        tracked_all = subprocess.check_output(["git", "-C", str(research), "ls-files", "-z"])
        reads = [recipe / "scripts/ci/pin_report_fixture.py",
                 source_map_path,
                 recipe / "tests/ci/test_pin_report_fixture.py",
                 recipe / "scripts/ci/native_conformance.py",
                 recipe / "scripts/ci/ni08_evl42_actual_scan_capture.py",
                 recipe / ".github/workflows/ni08-evl42-actual-scan.yml",
                 recipe / "scripts/ci/ni08_evl42_report_requirements.txt",
                 recipe / "tests/__init__.py",
                 recipe / "scripts/vidya/adapters/__init__.py",
                 recipe / "scripts/vidya/adapters/ci_conformance.py",
                 recipe / "scripts/vidya/claim_tuple.py",
                 recipe / "scripts/vidya/lattice.py",
                 recipe / "scripts/vidya/frames.py",
                 recipe / "scripts/vidya/canonical.py",
                 recipe / "scripts/vidya/adapters/README.md",
                 handoff,
                 research / "scripts/benchmark/check_pin_staleness.py",
                 research / "scripts/benchmark/tests/test_pin_staleness.py",
                 research / "pyproject.toml", research / "uv.lock", lock]
        reads.extend([install_log, pip_freeze])
        reads.extend(recipe / name for name in source_map["root_files"])
        reads.extend(research.joinpath(*PurePosixPath(name).parts) for name in scan_before)
        reads = list(dict.fromkeys(reads))
        if any(not path.is_file() or path.is_symlink() for path in reads):
            raise RuntimeError("declared exact source readset contains missing/nonregular inputs")
        versions = run / "python-environment.json"
        os.environ.update(ENVIRONMENT)
        os.environ["PYTHONPATH"] = str(recipe)
        os.environ["EPYC_INFERENCE_RESEARCH_REPO"] = str(research)
        checker_hash = hashlib.sha256((research / "scripts/benchmark/check_pin_staleness.py").read_bytes()).hexdigest()
        if checker_hash != CHECKER_SHA256:
            raise RuntimeError("unchanged Research checker bytes differ")
        versions.write_text(json.dumps({"pins": pins, "python": sys.version,
            "platform": platform.platform(), "installed": LOCKED_PACKAGES,
            "checker": "scripts/benchmark/check_pin_staleness.py", "checker_sha256": checker_hash,
            "tracked_scan_members_before": scan_before,
            "tracked_all_git_ls_files_sha256": hashlib.sha256(tracked_all).hexdigest(),
            "metric_scope": "native fixture execution only; scan statuses remain report data"},
            sort_keys=True, indent=2) + "\n")
        reads.append(versions)
        before = {str(path): file_identity(path) for path in reads}
        result = run / "result"
        result.mkdir()
        junit = result / "original-junit.xml"
        test = recipe / "tests/ci/test_pin_report_fixture.py"
        controls_junit = result / "controls-junit.xml"
        controls_select = [str(test) + "::" + name for name in CONTROL_CASES]
        controls_argv = [sys.executable, "-m", "pytest", "--noconftest", "-c", "/dev/null",
            "--import-mode=importlib", "--rootdir=" + str(recipe), "-o", "addopts=",
            "-p", "no:cacheprovider", "-q", *controls_select,
            "--basetemp=" + str(result / "controls-pytest-tmp"),
            "--junitxml=" + str(controls_junit)]
        controls = capture_fixture_execution(argv=controls_argv, cwd=recipe,
            junit=controls_junit, output=result / "controls-native",
            repositories={"recipe": recipe, "research": research, "lock-source": lock_source},
            read_paths=reads, selections=controls_select)
        controls_reopened, _ = read_receipt(result / "controls-native/receipt.json")
        if controls != controls_reopened or controls["fixture_execution_conformant"] is not True:
            raise RuntimeError("selected helper/reader controls did not pass original native capture")
        observed_controls = [(case.get("classname"), case.get("name"))
                             for case in controls["summary"]["cases"]]
        if (len(observed_controls) != CONTROL_CASE_COUNT
                or Counter(observed_controls) != Counter(EXPECTED_CONTROL_CASES)):
            raise RuntimeError("selected helper/reader JUnit identities differ")
        argv = [sys.executable, "-m", "pytest", "--noconftest", "-c", "/dev/null",
                "--import-mode=importlib", "--rootdir=" + str(recipe), "-o", "addopts=",
                "-p", "no:cacheprovider", "-q", str(test) + "::" + CASE,
                "--basetemp=" + str(result / "pytest-tmp"), "--junitxml=" + str(junit)]
        native_output = result / "native"
        record = capture_report_fixture(report_relative=REPORT_RELATIVE,
            additional_output_paths=[INVOCATION_RELATIVE], argv=argv, cwd=recipe,
            junit=junit, output=native_output, repositories={"recipe": recipe, "research": research,
            "lock-source": lock_source}, read_paths=reads,
            selections=[str(test) + "::" + CASE])
        receipt_path = native_output / "receipt.json"
        reopened, receipt_sha, report, invocation, stdout, stderr = read_scan_invocation_fixture(
            receipt_path, INVOCATION_RELATIVE, REPORT_RELATIVE)
        expected_scan_argv = [sys.executable,
            str(research / "scripts/benchmark/check_pin_staleness.py"),
            "--root", str(research), "--json"]
        expected_scan_env = {key: os.environ.get(key) for key in
            ("LANG", "LC_ALL", "PATH", "PYTHONHASHSEED", "PYTHONPATH", "PYTHONUTF8")}
        if (invocation["argv"] != expected_scan_argv or invocation["cwd"] != str(research)
                or invocation["environment"] != expected_scan_env):
            raise RuntimeError("original checker invocation identity differs")
        scan_after = tracked_scan_files(research)
        tracked_all_after = subprocess.check_output(["git", "-C", str(research), "ls-files", "-z"])
        if require_clean(research, "Research after scan") != RESEARCH_PIN:
            raise RuntimeError("Research checkout identity changed after scan")
        after = {str(path): file_identity(path) for path in reads}
        if scan_before != scan_after or before != after or tracked_all != tracked_all_after:
            raise RuntimeError("original exact source membership/readset changed during scan")
        output_files = {path.relative_to(recipe).as_posix() for path in
                        (recipe / "ci-capture-output").rglob("*") if path.is_file() or path.is_symlink()}
        expected_output_files = {INVOCATION_RELATIVE}
        if report is not None:
            expected_output_files.add(REPORT_RELATIVE)
        if output_files != expected_output_files:
            raise RuntimeError("actual scan output directory contains missing or undeclared files")
        if any(path.is_symlink() for path in (recipe / "ci-capture-output").rglob("*")):
            raise RuntimeError("actual scan output directory contains a symlink")
        output_identities = {relative: file_identity(recipe / relative)
                             for relative in sorted(output_files)}
        source_map_matches = report is None or report["source_file_identities"] == [
            {"path": name, "status": "read", "bytes": identity["bytes"],
             "sha256": identity["sha256"]} for name, identity in sorted(scan_before.items())]
        if report is not None and (report["tracked_python_files"] != len(scan_before) or not source_map_matches):
            raise RuntimeError("original report membership/byte identities differ from pinned scan inputs")
        if record != reopened:
            raise RuntimeError("original native receipt changed during strict reopen")
        from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
        from claim_tuple import grade
        rows = native_rows(receipt_path)
        grades = []
        for row in rows:
            claim = project_ci_conformance(row)
            quality, trust, reasons = grade(claim)
            grades.append({"measurement_id": claim.measurement_id, "Q": quality,
                           "T": trust, "reasons": reasons})
        summary = record.get("summary") or {}
        actual_cases = summary.get("cases") or []
        exact_case = (len(actual_cases) == 1 and actual_cases[0].get("name") == CASE
                      and actual_cases[0].get("classname") == "tests.ci.test_pin_report_fixture")
        metric = record.get("fixture_execution_conformant")
        status.update(state="captured", native_metric=metric, original_exit_code=record.get("exit_code"),
            controls_native_metric=controls["fixture_execution_conformant"],
            controls_case_count=len(observed_controls),
            original_case=actual_cases, exact_case=exact_case, report_present=report is not None,
            scan_return_code=invocation["return_code"], report_complete=(report or {}).get("complete"),
            report_counts=(report or {}).get("counts"), receipt_sha256=receipt_sha,
            stdout_sha256=hashlib.sha256(stdout).hexdigest(), stderr_sha256=hashlib.sha256(stderr).hexdigest(),
            source_membership_count=len(scan_before), source_map_matches=source_map_matches,
            generated_output_identities=output_identities,
            grades=grades, new_grade_authored=False)
        return 0 if (exact_case and record == reopened
                     and record.get("fixture_execution_conformant") is True
                     and report is not None) else 1
    except Exception as exc:
        status.update(state="capture_failed", error=type(exc).__name__ + ": " + str(exc))
        return 1
    finally:
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
