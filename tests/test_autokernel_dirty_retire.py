from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts/system/autokernel_dirty_retire.py"
SPEC = importlib.util.spec_from_file_location("autokernel_dirty_retire", SCRIPT)
assert SPEC and SPEC.loader
retire = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = retire
SPEC.loader.exec_module(retire)


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, text=True, capture_output=True, check=False)
    if check and result.returncode:
        raise AssertionError(
            f"command failed: {args}\nstdout={result.stdout}\nstderr={result.stderr}"
        )
    return result


def git(repo: Path, *args: str) -> str:
    return run("git", "-C", str(repo), *args).stdout.strip()


@pytest.fixture
def complete_probe(monkeypatch):
    snapshot = retire.sweep.ProcSnapshot("COMPLETE", {}, [])
    monkeypatch.setattr(
        retire.sweep, "probe_processes", lambda *_args, **_kwargs: snapshot
    )


def make_case(tmp_path: Path, *, unpushed_head: bool = False) -> dict:
    owner = tmp_path / "owner"
    owner.mkdir()
    git(owner, "init", "-b", "main")
    git(owner, "config", "user.name", "Retirement Test")
    git(owner, "config", "user.email", "retire@example.invalid")
    (owner / "tracked.txt").write_text("base\n")
    git(owner, "add", "tracked.txt")
    git(owner, "commit", "-m", "base")
    git(owner, "remote", "add", "origin", "https://example.invalid/owner.git")
    git(
        owner, "update-ref", "refs/remotes/origin/main", git(owner, "rev-parse", "HEAD")
    )

    allowed = tmp_path / "acceptance"
    allowed.mkdir()
    worktree = allowed / "dirty-case"
    git(owner, "worktree", "add", "-b", "dirty-case", str(worktree), "HEAD")
    if unpushed_head:
        (worktree / "tracked.txt").write_text("committed candidate\n")
        git(worktree, "add", "tracked.txt")
        git(worktree, "commit", "-m", "unpushed candidate")
    (worktree / "tracked.txt").write_text("dirty tracked\n")
    (worktree / "untracked.txt").write_text("unique evidence\n")

    row = {
        "path": str(worktree),
        "repo": str(owner),
        "kind": "git-worktree",
        "family": "worktree-root",
        "verdict": "KEEP-dirty",
        "head": git(worktree, "rev-parse", "HEAD"),
        "size_bytes": 1,
        "reason": "fixture",
        "reasons": {"KEEP-dirty": ["fixture"]},
    }
    manifest_value = {
        "schema": retire.sweep.SCHEMA,
        "generated_at": retire.sweep.now_utc().isoformat(),
        "params": {"allowed_root": [str(allowed)]},
        "rows": [row],
    }
    manifest_data = json.dumps(manifest_value, sort_keys=True).encode()
    manifest = tmp_path / "sweep.json"
    manifest.write_bytes(manifest_data)
    manifest_sha = hashlib.sha256(manifest_data).hexdigest()
    archive_root = tmp_path / "archives"
    result = retire.preserve.preserve_one(row, manifest_sha, archive_root, True)
    return {
        "owner": owner,
        "allowed": allowed,
        "worktree": worktree,
        "manifest": manifest,
        "manifest_sha": manifest_sha,
        "row": row,
        "record": Path(result["record"]),
        "archive": Path(result["archive"]),
        "receipts": tmp_path / "receipts",
        "unpushed": unpushed_head,
    }


def args(case: dict, *, apply: bool = False) -> list[str]:
    values = [
        "--manifest",
        str(case["manifest"]),
        "--manifest-sha",
        case["manifest_sha"],
        "--record",
        str(case["record"]),
        "--allowed-root",
        str(case["allowed"]),
        "--receipt-root",
        str(case["receipts"]),
    ]
    if apply:
        values.append("--apply")
    return values


def source_state(case: dict) -> tuple[str, str, bytes]:
    tree = case["worktree"]
    return (
        git(tree, "rev-parse", "HEAD"),
        git(tree, "status", "--porcelain=v2", "--untracked-files=all"),
        (tree / "untracked.txt").read_bytes(),
    )


def configure_ignored(case: dict, exclude: Path, patterns: str) -> None:
    exclude.write_text(patterns)
    git(case["worktree"], "config", "core.excludesFile", str(exclude))


def test_default_dry_run_verifies_without_mutation_or_receipt(tmp_path, complete_probe):
    case = make_case(tmp_path)
    before = source_state(case)

    assert retire.main(args(case)) == 0

    assert source_state(case) == before
    assert not case["receipts"].exists()


def test_wrong_reviewed_manifest_sha_refuses(tmp_path, complete_probe, capsys):
    case = make_case(tmp_path)
    values = args(case)
    values[values.index("--manifest-sha") + 1] = "0" * 64

    assert retire.main(values) == 2
    assert "manifest sha256" in capsys.readouterr().err
    assert case["worktree"].exists()


def test_only_keep_dirty_rows_are_eligible(tmp_path, complete_probe, capsys):
    case = make_case(tmp_path)
    manifest = json.loads(case["manifest"].read_bytes())
    manifest["rows"][0]["verdict"] = "REMOVE"
    data = json.dumps(manifest, sort_keys=True).encode()
    case["manifest"].write_bytes(data)
    case["manifest_sha"] = hashlib.sha256(data).hexdigest()

    assert retire.main(args(case)) == 2
    assert "not KEEP-dirty" in capsys.readouterr().err


def test_target_must_be_directly_below_an_exact_allowed_root(
    tmp_path, complete_probe, capsys
):
    case = make_case(tmp_path)
    values = args(case)
    values[values.index("--allowed-root") + 1] = str(tmp_path)

    assert retire.main(values) == 2
    assert "outside exact allowed roots" in capsys.readouterr().err


def test_fresh_fingerprint_must_match_archive_record(tmp_path, complete_probe, capsys):
    case = make_case(tmp_path)
    (case["worktree"] / "tracked.txt").write_text("changed after archive\n")

    assert retire.main(args(case)) == 2
    assert "fingerprint" in capsys.readouterr().err
    assert case["worktree"].exists()


def test_archive_tamper_refuses(tmp_path, complete_probe, capsys):
    case = make_case(tmp_path)
    data = bytearray(case["archive"].read_bytes())
    data[700] ^= 1
    case["archive"].chmod(0o644)
    case["archive"].write_bytes(data)

    assert retire.main(args(case)) == 2
    assert "REFUSED" in capsys.readouterr().err
    assert case["worktree"].exists()


def test_apply_requires_complete_process_probe(tmp_path, monkeypatch, capsys):
    case = make_case(tmp_path)
    monkeypatch.setattr(
        retire.sweep,
        "probe_processes",
        lambda *_args, **_kwargs: retire.sweep.ProcSnapshot(
            "PARTIAL", {}, [{"pid": 9, "uid": 1}], error="fixture"
        ),
    )

    assert retire.main(args(case, apply=True)) == 2
    assert "not COMPLETE" in capsys.readouterr().err
    assert case["worktree"].exists()


def test_apply_refuses_live_holder(tmp_path, monkeypatch, capsys):
    case = make_case(tmp_path)
    proc = retire.sweep.Proc(
        pid=4242,
        ppid=1,
        uid=1000,
        args="fixture",
        cwd=str(case["worktree"]),
    )
    monkeypatch.setattr(
        retire.sweep,
        "probe_processes",
        lambda *_args, **_kwargs: retire.sweep.ProcSnapshot(
            "COMPLETE", {4242: proc}, []
        ),
    )

    assert retire.main(args(case, apply=True)) == 2
    assert "live holders" in capsys.readouterr().err
    assert case["worktree"].exists()


def test_apply_requires_operator_confirmation(
    tmp_path, complete_probe, monkeypatch, capsys
):
    case = make_case(tmp_path)
    monkeypatch.setattr(retire, "operator_confirm", lambda *_args: False)
    before = source_state(case)

    assert retire.main(args(case, apply=True)) == 2

    assert "operator manual confirmation" in capsys.readouterr().err
    assert source_state(case) == before
    assert not case["receipts"].exists()


def test_generated_cache_and_build_ignored_files_are_inventoried_and_discarded(
    tmp_path, complete_probe, monkeypatch, capsys
):
    case = make_case(tmp_path)
    configure_ignored(
        case, tmp_path / "exclude", ".pytest_cache/\n.ruff_cache/\nbuild/\n"
    )
    files = {
        ".pytest_cache/v/cache/nodeids": b"[]\n",
        ".ruff_cache/index": b"ruff\n",
        "build/CMakeFiles/object.o": b"object\x00bytes",
    }
    for relative, payload in files.items():
        destination = case["worktree"] / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)

    assert retire.main(args(case)) == 0
    report = json.loads(capsys.readouterr().out)
    inventory = report["rows"][0]["ignored_inventory"]
    assert {item["path"] for item in inventory} == set(files)
    assert {item["type"] for item in inventory} == {"file"}
    assert report["rows"][0]["ignored_bytes"] == sum(map(len, files.values()))

    monkeypatch.setattr(retire, "operator_confirm", lambda *_args: True)
    assert retire.main(args(case, apply=True)) == 0
    capsys.readouterr()

    receipt_path = next(case["receipts"].rglob("*.json"))
    receipt = json.loads(receipt_path.read_bytes())
    assert receipt["state"] == "removed"
    assert {item["path"] for item in receipt["ignored_inventory"]} == set(files)
    events = [
        json.loads(line)["event"]
        for line in receipt_path.with_suffix(".jsonl").read_text().splitlines()
    ]
    assert "ignored-remove-authorized" in events
    assert "ignored-removed" in events


def test_ignored_evidence_pattern_is_refused(tmp_path, complete_probe, capsys):
    case = make_case(tmp_path)
    configure_ignored(case, tmp_path / "exclude", "cache/\n")
    evidence = case["worktree"] / "cache/VERDICT-run.json"
    evidence.parent.mkdir()
    evidence.write_text('{"keep": true}\n')

    assert retire.main(args(case)) == 2
    assert "durable evidence pattern" in capsys.readouterr().err
    assert evidence.exists()


def test_ignored_nested_repo_or_worktree_is_refused(tmp_path, complete_probe, capsys):
    case = make_case(tmp_path)
    configure_ignored(case, tmp_path / "exclude", "build/\n")
    marker = case["worktree"] / "build/nested/.git"
    marker.mkdir(parents=True)
    (marker / "config").write_text("[core]\n")

    assert retire.main(args(case)) == 2
    assert "nested repo/worktree" in capsys.readouterr().err
    assert marker.exists()


def test_ignored_symlink_escape_is_refused(tmp_path, complete_probe, capsys):
    case = make_case(tmp_path)
    configure_ignored(case, tmp_path / "exclude", "cache/\n")
    cache = case["worktree"] / "cache"
    cache.mkdir()
    outside = tmp_path / "outside.bin"
    outside.write_text("outside\n")
    os.symlink(outside, cache / "escape")

    assert retire.main(args(case)) == 2
    assert "symlink escapes" in capsys.readouterr().err
    assert outside.read_text() == "outside\n"


def test_ignored_special_file_is_refused(tmp_path, complete_probe, capsys):
    case = make_case(tmp_path)
    configure_ignored(case, tmp_path / "exclude", "cache/\n")
    cache = case["worktree"] / "cache"
    cache.mkdir()
    fifo = cache / "events.fifo"
    os.mkfifo(fifo)

    assert retire.main(args(case)) == 2
    assert "special file" in capsys.readouterr().err
    assert fifo.exists()


def test_partial_ignored_discard_resumes_from_durable_inventory(
    tmp_path, complete_probe, monkeypatch
):
    case = make_case(tmp_path)
    configure_ignored(case, tmp_path / "exclude", "cache/\n")
    cache = case["worktree"] / "cache"
    cache.mkdir()
    (cache / "one.bin").write_bytes(b"one")
    (cache / "two.bin").write_bytes(b"two")
    monkeypatch.setattr(retire, "operator_confirm", lambda *_args: True)
    original = retire.remove_ignored

    def interrupt_after_one(target, authorized):
        (target / authorized[0]["path"]).unlink()
        raise retire.RetireError("simulated interruption during ignored discard")

    monkeypatch.setattr(retire, "remove_ignored", interrupt_after_one)
    assert retire.main(args(case, apply=True)) == 1
    receipt_path = next(case["receipts"].rglob("*.json"))
    receipt = json.loads(receipt_path.read_bytes())
    assert receipt["state"] == "ignored_remove_authorized"
    assert len(receipt["authorized_ignored"]) == 2
    assert case["worktree"].exists()

    monkeypatch.setattr(retire, "remove_ignored", original)
    assert retire.main(args(case, apply=True)) == 0
    assert not case["worktree"].exists()
    assert json.loads(receipt_path.read_bytes())["state"] == "removed"


def test_success_uses_exact_nonforce_worktree_remove_and_writes_receipt(
    tmp_path, complete_probe, monkeypatch
):
    case = make_case(tmp_path, unpushed_head=True)
    monkeypatch.setattr(retire, "operator_confirm", lambda *_args: True)
    commands = []
    original = retire.sweep.git

    def recording(repo, *git_args, **kwargs):
        commands.append((str(repo), git_args))
        return original(repo, *git_args, **kwargs)

    monkeypatch.setattr(retire.sweep, "git", recording)

    assert retire.main(args(case, apply=True)) == 0

    assert not case["worktree"].exists()
    removes = [
        command for command in commands if command[1][:2] == ("worktree", "remove")
    ]
    assert removes == [
        (str(case["owner"]), ("worktree", "remove", str(case["worktree"])))
    ]
    assert all("--force" not in command[1] for command in commands)
    receipts = list(case["receipts"].rglob("*.json"))
    assert len(receipts) == 1
    receipt = json.loads(receipts[0].read_bytes())
    assert receipt["state"] == "removed"
    assert receipt["unpushed_bundle_verified"] is True
    assert list(case["receipts"].rglob("*.jsonl"))


def test_interrupted_after_reset_resumes_from_durable_authorization(
    tmp_path, complete_probe, monkeypatch
):
    case = make_case(tmp_path)
    monkeypatch.setattr(retire, "operator_confirm", lambda *_args: True)
    original = retire.verify_reset_state
    calls = 0

    def fail_once(*call_args, **call_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise retire.RetireError("simulated interruption after reset")
        return original(*call_args, **call_kwargs)

    monkeypatch.setattr(retire, "verify_reset_state", fail_once)
    assert retire.main(args(case, apply=True)) == 1
    receipt_path = next(case["receipts"].rglob("*.json"))
    assert json.loads(receipt_path.read_bytes())["state"] == "reset_authorized"
    assert case["worktree"].exists()

    monkeypatch.setattr(retire, "verify_reset_state", original)
    assert retire.main(args(case, apply=True)) == 0
    assert not case["worktree"].exists()
    assert json.loads(receipt_path.read_bytes())["state"] == "removed"


def test_absent_unpushed_tree_resumes_after_remove_authorization(
    tmp_path, complete_probe, monkeypatch
):
    case = make_case(tmp_path, unpushed_head=True)
    monkeypatch.setattr(retire, "operator_confirm", lambda *_args: True)
    assert retire.main(args(case, apply=True)) == 0
    receipt_path = next(case["receipts"].rglob("*.json"))
    receipt = json.loads(receipt_path.read_bytes())
    receipt["state"] = "worktree_remove_authorized"
    retire.atomic_json(receipt_path, receipt)

    assert retire.main(args(case, apply=True)) == 0
    assert json.loads(receipt_path.read_bytes())["state"] == "removed"
