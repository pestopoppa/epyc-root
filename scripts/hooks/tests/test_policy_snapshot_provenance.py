"""Original ROOT policy custody controls; originals are never edited or resealed."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess

import pytest

spec = importlib.util.spec_from_file_location(
    "ni31_fixture_helpers", Path(__file__).with_name("test_fixture_snapshot_provenance.py"))
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
originals = helpers.originals


@pytest.fixture(scope="session")
def policy_originals(tmp_path_factory):
    configured = os.environ.get("NI31_POLICY_ORIGINALS")
    assert configured, "NI31_POLICY_ORIGINALS must contain unchanged run 37307260869 prefixes"
    result = {}
    for phase in ("fixture-custody", "caller-gates"):
        source = Path(configured) / phase / f"native-ni31-{phase}"
        assert (source / "receipt.json").is_file(), "missing original ROOT policy custody"
        template = tmp_path_factory.mktemp(f"ni31-policy-{phase}")
        helpers.git(template, "init", "--quiet")
        for key, value in (("core.autocrlf", "false"), ("core.excludesFile", "/dev/null"),
                           ("commit.gpgsign", "false"), ("user.name", "NI31 fixture"),
                           ("user.email", "fixture@example.invalid")):
            helpers.git(template, "config", key, value)
        # Normal selected-hook commit of non-credential members in a private
        # throwaway repo. Original policy bytes remain unstaged until each case.
        hook = template / ".git/hooks/pre-commit"
        hook.write_text("#!/bin/bash\nexec bash " + helpers.shlex.quote(str(helpers.HOOK)) + "\n")
        hook.chmod(0o755)
        destination = template / "artifacts/ni05/policy-fixture" / f"native-ni31-{phase}"
        shutil.copytree(source, destination)
        helpers.git(template, "add", "--all")
        helpers.git(template, "rm", "--cached", str((destination / "read-007.bin").relative_to(template)))
        helpers.git(template, "commit", "--quiet", "-m", "Prepare non-policy fixture members")
        result[phase] = (template, source)
    return result


def bundle(tmp_path, policy_originals, phase="fixture-custody"):
    template, original = policy_originals[phase]
    repo = tmp_path / "repo"
    subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", str(template), str(repo)],
                   check=True, capture_output=True, text=True)
    helpers.git(repo, "config", "core.autocrlf", "false")
    helpers.git(repo, "config", "core.excludesFile", "/dev/null")
    destination = repo / "artifacts/ni05/policy-fixture" / f"native-ni31-{phase}"
    shutil.copyfile(original / "read-007.bin", destination / "read-007.bin")
    helpers.git(repo, "add", "--all")
    return repo, destination


@pytest.mark.parametrize("phase", ["fixture-custody", "caller-gates"])
def test_original_root_policy_requires_and_has_complete_original_custody(tmp_path, policy_originals, phase):
    repo, _ = bundle(tmp_path, policy_originals, phase)
    assert helpers.hook(repo).returncode == 0


@pytest.mark.parametrize("edit", ["new-secret", "plain-source-edit"])
def test_changed_policy_snapshot_always_uses_ordinary_scanner(tmp_path, policy_originals, edit):
    repo, destination = bundle(tmp_path, policy_originals)
    addition = helpers.unregistered_key() if edit == "new-secret" else "# source fixture was edited"
    with (destination / "read-007.bin").open("ab") as output:
        output.write(("\n" + addition + "\n").encode())
    # Coherent TEMP fixture resealing cannot turn new bytes into the reviewed
    # exact original public source. The retained originals never change.
    helpers.reseal_test_copy(destination, lambda row: next(
        item["artifact"] for item in row["readset"] if item["artifact"]["name"] == "read-007.bin"
    ).update(sha256=helpers.hashlib.sha256((destination / "read-007.bin").read_bytes()).hexdigest()))
    helpers.git(repo, "add", "--all")
    assert helpers.hook(repo).returncode != 0


@pytest.mark.parametrize("binding", ["wrong-repository", "app-revision"])
def test_root_policy_does_not_borrow_app_source_authority(tmp_path, policy_originals, binding):
    repo, destination = bundle(tmp_path, policy_originals)
    def mutate(row):
        if binding == "wrong-repository":
            row["repositories"]["orchestrator"] = row["repositories"].pop("root_source")
        else:
            row["repositories"]["root_source"] = "def18591f813070a20906f9d228ddd9dd0da9fd3"
    helpers.reseal_test_copy(destination, mutate)
    helpers.git(repo, "add", "--all")
    assert helpers.hook(repo).returncode != 0


def test_corrupted_original_root_proof_falls_back_to_ordinary_scanning(tmp_path, policy_originals):
    repo, destination = bundle(tmp_path, policy_originals)
    with (destination / "original-junit.xml").open("ab") as output:
        output.write(b"broken original custody")
    helpers.git(repo, "add", "--all")
    assert helpers.hook(repo).returncode != 0


def test_app_fixture_does_not_borrow_root_policy_authority(tmp_path, originals):
    repo, destination = helpers.bundle(tmp_path, originals)
    helpers.reseal_test_copy(destination, lambda row: row["repositories"].update(
        orchestrator="4cc17080c6209e5d7f2a744807c9cf87ae0bf70f",
        root_source="4cc17080c6209e5d7f2a744807c9cf87ae0bf70f"))
    helpers.git(repo, "add", "--all")
    assert helpers.hook(repo).returncode != 0


if __name__ == "__main__":
    raise SystemExit("REFUSING: this pytest suite requires configured original capsules")
