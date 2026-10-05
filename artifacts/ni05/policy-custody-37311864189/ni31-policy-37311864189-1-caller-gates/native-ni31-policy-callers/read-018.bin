"""Real Git-index tests using unchanged original CI custody as test inputs.

Set NI31_NATIVE_ORIGINALS to downloaded ordinary-guards and unit-synthetic
prefixes from run 37299780302. Tests modify only fresh temporary copies; retained
original records are never changed or resealed. Missing inputs fail explicitly.
"""
from __future__ import annotations

import hashlib
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[3]
HOOK = ROOT / "scripts/hooks/pii_precommit.sh"
NATIVE_PATH = ROOT / "scripts/ci/native_conformance.py"
spec = importlib.util.spec_from_file_location("ni31_fixture_native", NATIVE_PATH)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True)


@pytest.fixture(scope="session")
def originals(tmp_path_factory):
    configured = os.environ.get("NI31_NATIVE_ORIGINALS")
    assert configured, "NI31_NATIVE_ORIGINALS must name the original downloaded CI prefixes"
    base = Path(configured)
    result = {}
    for phase in ("ordinary-guards", "unit-synthetic"):
        path = base / phase / f"native-{phase}"
        assert (path / "receipt.json").is_file(), f"missing original {phase} custody"
        # Commit only non-credential members through the ACTUAL selected hook.
        # Each test then stages the two reviewed blobs, so the scanner processes
        # a small real diff while the reader still verifies the full index view.
        # This is private fixture setup; no original bytes or public refs change.
        template = tmp_path_factory.mktemp(f"ni31-{phase}")
        git(template, "init", "--quiet")
        git(template, "config", "core.autocrlf", "false")
        git(template, "config", "core.excludesFile", "/dev/null")
        git(template, "config", "core.hooksPath", ".git/hooks")
        git(template, "config", "commit.gpgsign", "false")
        git(template, "config", "user.name", "NI31 fixture")
        git(template, "config", "user.email", "fixture@example.invalid")
        selected_hook = template / ".git/hooks/pre-commit"
        selected_hook.write_text("#!/bin/bash\nexec bash " + shlex.quote(str(HOOK)) + "\n")
        selected_hook.chmod(0o755)
        destination = template / "artifacts/ni05/provenance-fixture" / f"native-{phase}"
        shutil.copytree(path, destination)
        git(template, "add", "--all")
        git(template, "rm", "--cached", str((destination / "read-214.bin").relative_to(template)),
            str((destination / "read-454.bin").relative_to(template)))
        git(template, "commit", "--quiet", "-m", "Prepare non-credential staged fixture members")
        result[phase] = (template, path)
    return result


def bundle(tmp_path, originals, phase="ordinary-guards"):
    repo = tmp_path / "repo"
    template, original = originals[phase]
    subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", str(template), str(repo)],
                   check=True, capture_output=True, text=True)
    git(repo, "config", "core.autocrlf", "false")
    git(repo, "config", "core.excludesFile", "/dev/null")
    destination = repo / "artifacts/ni05/provenance-fixture" / f"native-{phase}"
    for name in ("read-214.bin", "read-454.bin"):
        shutil.copyfile(original / name, destination / name)
    git(repo, "add", "--all")
    return repo, destination


def hook(repo):
    return subprocess.run(["bash", str(HOOK)], cwd=repo,
                          capture_output=True, text=True, timeout=60)


def unregistered_key():
    return "ghp_" + "Z" * 36


def reseal_test_copy(container, mutate):
    """Make a coherent adversarial TEMP fixture, not a new historical record."""
    path = container / "receipt.json"
    record = json.loads(path.read_text())
    mutate(record)
    request_path = container / record["request"]["name"]
    request = json.loads(request_path.read_text())
    for field in request:
        if field in record:
            request[field] = record[field]
    request_path.write_bytes(native.canonical(request) + b"\n")
    record["request"]["sha256"] = hashlib.sha256(request_path.read_bytes()).hexdigest()
    if record["fixture_execution_conformant"] is not None:
        record["decided_proposition"] = native.proposition(record)
    record.pop("receipt_sha256")
    record["receipt_sha256"] = native.digest(native.canonical(record))
    path.write_bytes(native.canonical(record) + b"\n")


@pytest.mark.parametrize("phase", ["ordinary-guards", "unit-synthetic"])
def test_complete_original_staged_true_and_diagnostic_custody_pass(tmp_path, originals, phase):
    repo, _ = bundle(tmp_path, originals, phase)
    result = hook(repo)
    assert result.returncode == 0, result.stderr


def test_valid_index_remains_valid_when_worktree_fixture_is_changed(tmp_path, originals):
    repo, destination = bundle(tmp_path, originals)
    with (destination / "read-214.bin").open("ab") as output:
        output.write(("\n" + unregistered_key() + "\n").encode())
    result = hook(repo)
    assert result.returncode == 0, result.stderr


def test_invalid_index_is_not_rescued_by_valid_worktree_metadata(tmp_path, originals):
    repo, destination = bundle(tmp_path, originals)
    receipt = destination / "receipt.json"
    original = receipt.read_bytes()
    receipt.write_text("malformed native record")
    git(repo, "add", str(receipt.relative_to(repo)))
    receipt.write_bytes(original)
    result = hook(repo)
    assert result.returncode == 1
    assert "read-214.bin" in result.stderr


@pytest.mark.parametrize("damage", ["missing", "symlink", "traversal", "request-mismatch"])
def test_incomplete_or_malformed_index_falls_back_to_scanning(tmp_path, originals, damage):
    repo, destination = bundle(tmp_path, originals)
    if damage == "missing":
        (destination / "read-000.bin").unlink()
    elif damage == "symlink":
        (destination / "read-000.bin").unlink()
        (destination / "read-000.bin").symlink_to("read-001.bin")
    elif damage == "traversal":
        reseal_test_copy(destination, lambda row: row["readset"][0]["artifact"].update(name="../read-000.bin"))
    else:
        request = destination / "execution-request.json"
        row = json.loads(request.read_text())
        row["selections"] = ["different original request"]
        request.write_text(json.dumps(row))
    git(repo, "add", "--all")
    result = hook(repo)
    assert result.returncode == 1
    assert "read-214.bin" in result.stderr


@pytest.mark.parametrize("binding", ["source-path", "source-revision"])
def test_known_bytes_require_original_public_source_binding(tmp_path, originals, binding):
    repo, destination = bundle(tmp_path, originals)

    def mutate(row):
        if binding == "source-path":
            for item in row["readset"]:
                if item["artifact"]["name"] == "read-214.bin":
                    item["name"] = row["cwd"] + "/tests/unit/not_the_reviewed_fixture.py"
        else:
            row["repositories"]["orchestrator"] = "f" * 40

    reseal_test_copy(destination, mutate)
    git(repo, "add", "--all")
    result = hook(repo)
    assert result.returncode == 1
    assert "read-214.bin" in result.stderr


def test_changed_fixture_cannot_exempt_even_with_coherent_resealed_test_copy(tmp_path, originals):
    repo, destination = bundle(tmp_path, originals)
    path = destination / "read-214.bin"
    with path.open("ab") as output:
        output.write(("\n" + unregistered_key() + "\n").encode())

    def mutate(row):
        for item in row["readset"]:
            if item["artifact"]["name"] == path.name:
                item["artifact"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()

    reseal_test_copy(destination, mutate)
    git(repo, "add", "--all")
    result = hook(repo)
    assert result.returncode == 1
    assert "read-214.bin" in result.stderr


def test_duplicate_readset_member_rejects_coherently_resealed_test_copy(tmp_path, originals):
    repo, destination = bundle(tmp_path, originals)
    reseal_test_copy(destination, lambda row: row["readset"].append(copy.deepcopy(row["readset"][1])))
    git(repo, "add", "--all")
    result = hook(repo)
    assert result.returncode == 1
    assert "read-214.bin" in result.stderr


def test_other_member_still_scans_when_entire_test_copy_is_coherently_resealed(tmp_path, originals):
    repo, destination = bundle(tmp_path, originals)
    path = destination / "command.log"
    with path.open("ab") as output:
        output.write(("\n" + unregistered_key() + "\n").encode())
    reseal_test_copy(destination, lambda row: row["log"].update(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    git(repo, "add", "--all")
    result = hook(repo)
    assert result.returncode == 1
    assert "command.log" in result.stderr


@pytest.mark.parametrize("name", ["outside.bin", "outside-$(touch sentinel).bin"])
def test_exact_public_bytes_outside_bound_native_path_do_not_exempt(tmp_path, originals, name):
    repo, destination = bundle(tmp_path, originals)
    shutil.copyfile(destination / "read-214.bin", repo / name)
    git(repo, "add", "--all")
    result = hook(repo)
    assert result.returncode == 1
    assert name in result.stderr
    assert not (repo / "sentinel").exists()


def test_modified_book_fixture_account_number_is_not_exempt(tmp_path, originals):
    repo, destination = bundle(tmp_path, originals)
    with (destination / "read-454.bin").open("ab") as output:
        output.write(('\naccount_id="' + "2999" * 4 + '"\n').encode())
    git(repo, "add", "--all")
    result = hook(repo)
    assert result.returncode == 1
    assert "read-454.bin" in result.stderr


def test_existing_vendor_example_does_not_hide_an_unregistered_key(tmp_path, originals):
    repo, _ = bundle(tmp_path, originals)
    path = repo / "notes.txt"
    path.write_text("AKIAIOSFODNN7EXAMPLE\n")
    git(repo, "add", "--all")
    assert hook(repo).returncode == 0
    path.write_text("AKIAIOSFODNN7EXAMPLE " + unregistered_key() + "\n")
    git(repo, "add", "--all")
    result = hook(repo)
    assert result.returncode == 1
    assert "notes.txt" in result.stderr


if __name__ == "__main__":
    raise SystemExit("REFUSING: pytest-fixture suite; run: "
                     "python -m pytest scripts/hooks/tests/test_fixture_snapshot_provenance.py -q")
