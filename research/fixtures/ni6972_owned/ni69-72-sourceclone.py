"""PREP hosted-only owned committed data fixture; never import on the host."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def digest(path: Path) -> str:
    assert stat.S_ISREG(path.lstat().st_mode) and not path.is_symlink(), path
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    os.umask(0o077)
    source, scope, assets = map(lambda x: Path(x).resolve(strict=True), sys.argv[1:4])
    manifest = json.loads((assets / "ni69-72-sourceclone-manifest.json").read_text())
    assert git(source, "rev-parse", "HEAD") == os.environ["APP_SHA"]
    assert git(source, "rev-parse", "HEAD^") == manifest["source_parent"]
    assert not git(source, "status", "--porcelain=v1", "--untracked-files=all")
    assert set(git(source, "diff", "--name-only", "HEAD^", "HEAD").splitlines()) == set(
        manifest["canonical_candidate_test_overrides"]
    )
    pins = manifest["all_tracked_python_pins"]
    canonical_hashes = {}
    for name, pin in pins.items():
        expected = manifest["canonical_candidate_test_overrides"].get(name, pin["sha256"])
        assert digest(source / name) == expected, name
        canonical_hashes[name] = expected
    actual_python = {name for name in git(source, "ls-tree", "-r", "--name-only", "HEAD").splitlines()
                     if name.endswith(".py")}
    assert actual_python == set(pins)
    clone = scope / "fixture-app"
    assert not clone.exists() and not clone.is_symlink()
    subprocess.run(["git", "clone", "--no-local", "--no-hardlinks", "--no-checkout",
                    str(source), str(clone)], check=True)
    subprocess.run(["git", "-C", str(clone), "checkout", "--detach", os.environ["APP_SHA"]], check=True)
    clone.chmod(0o700)
    assert git(clone, "rev-parse", "HEAD") == os.environ["APP_SHA"]
    # A fresh clone must naturally have no configured active hooks; never bypass one.
    hook_config = subprocess.run(["git", "-C", str(clone), "config", "--get", "core.hooksPath"],
                                 capture_output=True, text=True)
    assert hook_config.returncode == 1 and not hook_config.stdout
    assert all(path.name.endswith(".sample") for path in (clone / ".git/hooks").iterdir())
    for item in manifest["owned_yaml_inputs"]:
        target = clone / item["path"]
        assert digest(source / item["path"]) == item["original_sha256"]
        assert digest(assets / item["fixture_asset"]) == item["fixture_sha256"]
        assert digest(target) == item["original_sha256"]
        target.write_bytes((assets / item["fixture_asset"]).read_bytes())
        target.chmod(0o600)
    changed = set(git(clone, "diff", "--name-only", "HEAD").splitlines())
    assert changed == set(manifest["approved_fixture_overlay_changed_paths"])
    for name, expected in canonical_hashes.items():
        assert digest(clone / name) == expected, name
    originals = scope / "originals"
    overlay = subprocess.check_output(["git", "-C", str(clone), "diff", "--binary", "HEAD"])
    (originals / "owned-data-overlay.diff").write_bytes(overlay)
    subprocess.run(["git", "-C", str(clone), "add", "--",
                    *manifest["approved_fixture_overlay_changed_paths"]], check=True)
    commit_env = dict(os.environ, GIT_AUTHOR_NAME="Owned fixture capture",
                      GIT_AUTHOR_EMAIL="owned-fixture@example.invalid",
                      GIT_COMMITTER_NAME="Owned fixture capture",
                      GIT_COMMITTER_EMAIL="owned-fixture@example.invalid")
    subprocess.run(["git", "-C", str(clone), "commit", "-m",
                    "Synthetic owned declaration input for bounded metadata controls"],
                   env=commit_env, check=True)
    fixture_sha = git(clone, "rev-parse", "HEAD")
    assert git(clone, "rev-parse", "HEAD^") == os.environ["APP_SHA"]
    assert set(git(clone, "diff", "--name-only", "HEAD^", "HEAD").splitlines()) == changed
    assert not git(clone, "status", "--porcelain=v1", "--untracked-files=all")
    subprocess.run(["git", "-C", str(clone), "ls-tree", "-r", "--full-tree", "HEAD"],
                   stdout=(originals / "fixture-full-ls-tree.txt").open("wb"), check=True)
    context = {"canonical_app_sha": os.environ["APP_SHA"], "fixture_sha": fixture_sha,
               "fixture_parent": os.environ["APP_SHA"], "fixture_path": str(clone),
               "synthetic_owned_yaml": True, "physical_memory_overridden": False,
               "runtime_source_changed": False, "configured_hooks_absent": True,
               "overlay_sha256": hashlib.sha256(overlay).hexdigest(),
               "overlay_changed_paths": sorted(changed),
               "canonical_python_hashes": canonical_hashes,
               "source_clone_manifest_sha256": digest(assets / "ni69-72-sourceclone-manifest.json"),
               "owned_yaml_inputs": manifest["owned_yaml_inputs"],
               "scope": "Synthetic declarations only; no production capacity claim"}
    (originals / "owned-clone-context.json").write_text(json.dumps(context, sort_keys=True) + "\n")
    with Path(os.environ["GITHUB_ENV"]).open("a") as output:
        output.write(f"FIXTURE_APP={clone}\nFIXTURE_SHA={fixture_sha}\n")


if __name__ == "__main__":
    main()
