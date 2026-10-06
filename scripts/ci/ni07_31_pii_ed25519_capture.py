"""Off-host capture for staged PII private-key-header recognition."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import stat
import subprocess
import sys
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

EXPECTED = {
    "source": "77d0e5de9624ca8ebd4ce2cfcdbbc240bb470642",
    "carrier": "4c0c653baf1654c8c25c66433cf39c8faefd8e52",
}
CONFIG_NAMES = {"pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini", "uv.lock"}
SELECTIONS = (
    "scripts/hooks/tests/test_pii_staged_capture.py::test_private_key_header_is_blocked_from_staged_blob",
    "scripts/hooks/tests/test_pii_staged_capture.py::test_ed25519_metadata_without_private_key_header_passes",
    "scripts/hooks/tests/test_pii_staged_capture.py::test_actual_gate_original_boolean_and_shared_frames",
    "scripts/hooks/tests/test_pii_staged_capture.py::test_partial_stage_uses_original_index_not_worktree",
    "scripts/hooks/tests/test_pii_staged_capture.py::test_all_excluded_is_diagnostic_not_success",
)
EXPECTED_CASES = 9  # 3 headers + metadata + 2 actual outcomes + 2 partial-stage outcomes + exclusion.
PINNED_TEST_TOOLS = {"pytest": "9.0.3", "iniconfig": "2.3.0", "packaging": "26.0",
                    "pluggy": "1.6.0", "Pygments": "2.20.0"}


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tracked_manifest(repos: dict[str, Path], workflow: Path) -> list[dict]:
    records = []
    for label, repo in repos.items():
        names = subprocess.check_output(["git", "-C", str(repo), "ls-files", "-z"]).decode().split("\0")
        for name in sorted(n for n in names if n):
            path = repo / name
            if path.is_symlink():
                raise RuntimeError(f"tracked input is symlinked: {label}/{name}")
            if path.suffix.lower() != ".py" and path.name not in CONFIG_NAMES:
                continue
            raw = path.read_bytes()
            mode = git(repo, "ls-files", "--stage", "--", name).split()[0]
            records.append({"repo": label, "path": name, "mode": mode,
                            "size": len(raw), "sha256": sha(raw)})
    raw = workflow.read_bytes()
    records.append({"repo": "recipe", "path": ".github/workflows/ni07-31-pii-ed25519.yml",
                    "mode": "100644", "size": len(raw), "sha256": sha(raw), "explicit": True})
    hook = repos["source"] / "scripts/hooks/pii_precommit.sh"
    raw = hook.read_bytes()
    records.append({"repo": "source", "path": "scripts/hooks/pii_precommit.sh",
                    "mode": git(repos["source"], "ls-files", "--stage", "--", "scripts/hooks/pii_precommit.sh").split()[0],
                    "size": len(raw), "sha256": sha(raw), "explicit": True})
    return records


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    result = runner_temp / "ni07-31-pii-ed25519" / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status = {"state": "preparing", "job": "pii-ed25519", "exit_code": None}
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n")
    source, carrier, recipe = (workspace / key for key in ("source", "carrier", "recipe"))
    repos = {"source": source, "carrier": carrier, "recipe": recipe}
    tmp = result.parent / "runtime-context"
    tmp.mkdir(parents=True, exist_ok=True)
    context = {
        "python": sys.version,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "runner_context": os.environ["NI31_RUNNER_CONTEXT"],
        "source_pin": git(source, "rev-parse", "HEAD"),
        "carrier_pin": git(carrier, "rev-parse", "HEAD"),
        "recipe_pin": git(recipe, "rev-parse", "HEAD"),
        "install_command": os.environ["NI31_INSTALL_COMMAND"],
        "selected_tests": list(SELECTIONS),
        "expected_collected_cases": EXPECTED_CASES,
        "dependency_basis": "Exact pytest runtime closure only; selected ROOT hook fixtures use stdlib plus pytest. No APP/model/inference packages.",
    }
    (tmp / "environment.json").write_text(json.dumps(context, sort_keys=True, indent=2) + "\n")
    try:
        if os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD") != "1":
            raise RuntimeError("pytest plugin autoload must remain disabled")
        if os.environ.get("NI31_RUNNER_CONTEXT") != "ubuntu-latest":
            raise RuntimeError("runner context differs from reviewed recipe")
        if sys.version_info[:3] != (3, 13, 15):
            raise RuntimeError(f"Python {sys.version_info[:3]} differs from pinned runner")
        for label, repo in repos.items():
            expected = EXPECTED[label] if label in EXPECTED else os.environ["GITHUB_SHA"]
            if git(repo, "rev-parse", "HEAD") != expected:
                raise RuntimeError(f"{label} checkout differs from its reviewed pin")
            if git(repo, "status", "--porcelain", "--untracked-files=all"):
                raise RuntimeError(f"{label} checkout is dirty")
        for package, version in PINNED_TEST_TOOLS.items():
            if importlib.metadata.version(package) != version:
                raise RuntimeError(f"{package} is not the reviewed version {version}")
        (tmp / "pip-freeze.txt").write_bytes(subprocess.check_output([sys.executable, "-m", "pip", "freeze"]))
        manifest = tracked_manifest(repos, recipe / ".github/workflows/ni07-31-pii-ed25519.yml")
        for path in (tmp / "environment.json", tmp / "pip-freeze.txt"):
            raw = path.read_bytes()
            manifest.append({"repo": "runtime", "path": path.name,
                             "mode": format(stat.S_IMODE(path.stat().st_mode), "04o"),
                             "size": len(raw), "sha256": sha(raw), "explicit": True})
        manifest_doc = {"pins": {"source": EXPECTED["source"], "recipe": os.environ["GITHUB_SHA"],
                                 "carrier": EXPECTED["carrier"]}, "files": manifest}
        manifest_bytes = (json.dumps(manifest_doc, sort_keys=True, indent=2) + "\n").encode()
        (result / "source-manifest.json").write_bytes(manifest_bytes)
        (result / "source-manifest.sha256").write_text(sha(manifest_bytes) + "  source-manifest.json\n")
        readset = result / "readset"
        for item in manifest:
            if item["repo"] == "runtime":
                continue
            repo = repos[item["repo"]]
            original = repo / item["path"]
            destination = readset / item["repo"] / item["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(original.read_bytes())
        basetemp = tmp / "pytest-basetemp"
        env = dict(os.environ, TMPDIR=str(tmp), PYTHONPATH=str(source),
                   PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1")
        command = [sys.executable, "-m", "pytest", "--basetemp", str(basetemp),
                   "--junitxml", str(result / "junit.xml"), *SELECTIONS]
        code = subprocess.call(command, cwd=source, env=env)
        status.update(state="captured", exit_code=code)
        junit = ET.parse(result / "junit.xml").getroot()
        cases = int(junit.attrib.get("tests", "0"))
        if code == 0 and cases != EXPECTED_CASES:
            status.update(state="invalid_collection", error=f"JUnit cases {cases} != {EXPECTED_CASES}")
        receipts = sorted(basetemp.rglob("receipt.json"))
        if len(receipts) != EXPECTED_CASES:
            status.update(state="invalid_receipts", error=f"found {len(receipts)} receipts, expected {EXPECTED_CASES}")
        sys.path.insert(0, str(carrier))
        from scripts.vidya.adapters import pii_staged_gate as native_adapter
        from scripts.vidya.claim_tuple import grade
        grades = []
        outcomes = []
        diagnostics = 0
        for receipt in receipts:
            rows = native_adapter.native_rows(receipt)
            if rows:
                if len(rows) != 1:
                    raise RuntimeError("carrier returned unexpected PII row cardinality")
                claim = native_adapter.project(rows[0])
                quality, traceability, _ = grade(claim)
                outcomes.append(rows[0]["record"]["pii_staged_policy_check_passed"])
                grades.append({"quality": quality, "traceability": traceability})
            else:
                diagnostics += 1
        if len(grades) != 8 or diagnostics != 1:
            status.update(state="invalid_native_projection",
                          error=f"carrier produced {len(grades)} rows and {diagnostics} diagnostics")
        (result / "native-grades.json").write_text(json.dumps(
            {"carrier_pin": EXPECTED["carrier"], "rows": grades, "outcomes": outcomes,
             "diagnostics": diagnostics},
            sort_keys=True, indent=2) + "\n")
        # The API ZIP preserves the complete captured pytest temporary tree and context, including every
        # native private receipt member. It is synthetic fixture data only and is not a redaction claim.
        api_zip = result / "api.zip"
        with zipfile.ZipFile(api_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for root in (result / "readset", result / "source-manifest.json",
                         result / "source-manifest.sha256", tmp,
                         result / "junit.xml", result / "native-grades.json"):
                if not root.exists():
                    continue
                paths = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
                for path in paths:
                    archive.write(path, path.relative_to(result.parent).as_posix())
        with zipfile.ZipFile(api_zip) as archive:
            members = sorted((name, sha(archive.read(name))) for name in archive.namelist())
            if len({name for name, _ in members}) != len(members):
                raise RuntimeError("API ZIP has duplicate member names")
        member_bytes = (json.dumps({"members": [{"name": name, "sha256": digest}
                                               for name, digest in members]},
                                   sort_keys=True, indent=2) + "\n").encode()
        (result / "api-members.sha256.json").write_bytes(member_bytes)
        api_hash = sha(api_zip.read_bytes())
        (result / "api-zip.sha256").write_text(api_hash + "  api.zip\n")
        status["api_zip_sha256"] = api_hash
        status["junit_cases"] = cases
        status["receipt_files"] = len(receipts)
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n")
        return code if status.get("state") == "captured" else 1
    except Exception as exc:
        status.update(state="capture_error", error=f"{type(exc).__name__}: {exc}")
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
