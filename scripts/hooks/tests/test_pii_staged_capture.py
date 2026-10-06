"""Actual disposable-index PII gates; sensitive originals never leave tmp_path."""
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.hooks import pii_staged_capture as capture
from scripts.vidya.adapters import pii_staged_gate as adapter
from claim_tuple import ProjectionError, grade, to_frames

HOOK = ROOT / "scripts/hooks/pii_precommit.sh"


def git(repo, *args, env=None, input=None):
    return subprocess.run(["git", "-C", str(repo), *args], env=env, input=input,
                          check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / "fixture-repo"
    path.mkdir()
    git(path, "init", "--quiet")
    git(path, "config", "user.name", "Disposable fixture")
    git(path, "config", "user.email", "fixture@example.invalid")
    git(path, "config", "commit.gpgsign", "false")
    git(path, "config", "core.hooksPath", ".git/hooks")
    git(path, "commit", "--quiet", "--allow-empty", "-m", "Fixture baseline")
    return path


def body(secret):
    return ("token=" + "ghp_" + "Z" * 36 + "\n") if secret else "ordinary fixture text\n"


def stage(repo, secret=False, name="sample.txt", env=None):
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body(secret))
    git(repo, "add", "--", name, env=env)
    return path


def run(repo, env=None):
    directory = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.decode().strip())
    previous = set((directory / "epyc-private/pii-gates").glob("*/receipt.json"))
    result = subprocess.run(["bash", str(HOOK)], cwd=repo, env=env,
                            capture_output=True, timeout=60)
    # Assertion values must never disclose sensitive scanner stdout/stderr.
    receipts = sorted(set((directory / "epyc-private/pii-gates").glob("*/receipt.json")) - previous)
    assert len(receipts) == 1, "one original private receipt required"
    return result.returncode, receipts[0]


@pytest.mark.parametrize("secret", [False, True])
def test_actual_gate_original_boolean_and_shared_frames(repo, secret):
    stage(repo, secret)
    code, receipt = run(repo)
    record, _ = capture.read_receipt(receipt)
    assert code == int(secret), "original gate exit must be preserved"
    assert record["pii_staged_policy_check_passed"] is (not secret)
    tup = adapter.project(adapter.native_rows(receipt)[0])
    assert grade(tup)[:2] == ("Judged", "Located")
    frames = to_frames(tup, as_of=record["ended_utc"], adapter_id=adapter.ADAPTER_ID)
    display = json.dumps(frames)
    assert ("evaluated false" if secret else "evaluated true") in display
    assert "sample.txt" not in display and body(True).strip() not in display


@pytest.mark.parametrize("key_type", ["RSA", "OPENSSH", "ED25519"])
def test_private_key_header_is_blocked_from_staged_blob(repo, key_type):
    header = "-----BEGIN " + key_type + " " + "PRIVATE KEY-----"
    name = "synthetic_key.txt"
    (repo / name).write_text(header + "\nsynthetic test key material\n")
    git(repo, "add", "--", name)

    code, receipt = run(repo)
    record, _ = capture.read_receipt(receipt)

    assert code == 1
    assert record["pii_staged_policy_check_passed"] is False


def test_ed25519_metadata_without_private_key_header_passes(repo):
    name = "synthetic_metadata.txt"
    (repo / name).write_text("key algorithm: ED25519; no private key material\n")
    git(repo, "add", "--", name)

    code, receipt = run(repo)
    record, _ = capture.read_receipt(receipt)

    assert code == 0
    assert record["pii_staged_policy_check_passed"] is True


@pytest.mark.parametrize("staged_secret", [False, True])
def test_partial_stage_uses_original_index_not_worktree(repo, staged_secret):
    path = stage(repo, staged_secret)
    path.write_text(body(not staged_secret))
    code, receipt = run(repo)
    record, _ = capture.read_receipt(receipt)
    assert code == int(staged_secret), "worktree must not replace indexed bytes"
    item = record["inputs"][0]
    assert (receipt.parent / item["artifact"]["name"]).read_text() == body(staged_secret)


def test_selected_alternate_index(repo, tmp_path):
    alternate = tmp_path / "selected-index"
    shutil.copyfile(repo / ".git/index", alternate) if (repo / ".git/index").exists() else None
    env = dict(os.environ, GIT_INDEX_FILE=str(alternate))
    git(repo, "read-tree", "HEAD", env=env)
    stage(repo, True, env=env)
    code, receipt = run(repo, env)
    record, _ = capture.read_receipt(receipt)
    assert code == 1 and record["original_index"] == str(alternate)
    assert record["pii_staged_policy_check_passed"] is False


def test_actual_linked_worktree_index(repo, tmp_path):
    worktree = tmp_path / "linked"
    git(repo, "worktree", "add", "--quiet", "-b", "fixture-linked", str(worktree))
    stage(worktree)
    code, receipt = run(worktree)
    record, _ = capture.read_receipt(receipt)
    selected = git(worktree, "rev-parse", "--path-format=absolute", "--git-path", "index").stdout.decode().strip()
    assert code == 0 and record["original_index"] == selected
    assert record["head"] == git(worktree, "rev-parse", "HEAD").stdout.decode().strip()


def test_unborn_head_is_original_empty_comparison(tmp_path):
    repo = tmp_path / "unborn"
    repo.mkdir()
    git(repo, "init", "--quiet")
    stage(repo)
    code, receipt = run(repo)
    record, _ = capture.read_receipt(receipt)
    assert code == 0 and record["head"] is None
    assert record["comparison"] == git(repo, "hash-object", "-t", "tree", "--stdin", input=b"").stdout.decode().strip()


@pytest.mark.parametrize("mode", ["split", "unmerged"])
def test_unsupported_index_preserves_gate_and_yields_no_tuple(repo, mode):
    stage(repo)
    if mode == "split":
        git(repo, "update-index", "--split-index")
    else:
        oid = git(repo, "hash-object", "-w", "--stdin", input=b"ordinary fixture text\n").stdout.strip()
        git(repo, "update-index", "--force-remove", "sample.txt")
        git(repo, "update-index", "--index-info", input=b"100644 " + oid + b" 1\tsample.txt\n100644 " + oid + b" 2\tsample.txt\n")
    code, receipt = run(repo)
    record, _ = capture.read_receipt(receipt)
    assert code == 0, "ordinary unsupported-index gate behavior must remain unchanged"
    assert record["pii_staged_policy_check_passed"] is None
    assert adapter.native_rows(receipt) == ()


def test_all_excluded_is_diagnostic_not_success(repo):
    stage(repo, True, name="research/fixtures/pii_native.txt")
    code, receipt = run(repo)
    record, _ = capture.read_receipt(receipt)
    assert code == 0 and record["pii_staged_policy_check_passed"] is None
    assert adapter.native_rows(receipt) == ()


@pytest.mark.parametrize("mutation", ["input", "missing", "receipt-permission", "symlink", "extra"])
def test_reader_refuses_original_custody_mutation(repo, mutation):
    stage(repo)
    _, receipt = run(repo)
    record, _ = capture.read_receipt(receipt)
    original = receipt.parent / record["inputs"][0]["artifact"]["name"]
    if mutation == "input":
        original.write_text("different original bytes\n")
    elif mutation == "missing":
        original.unlink()
    elif mutation == "receipt-permission":
        receipt.chmod(0o644)
    elif mutation == "symlink":
        (receipt.parent / "symbolic").symlink_to(original)
    else:
        (receipt.parent / "unexpected").write_text("extra member")
    with pytest.raises(ProjectionError, match="custody refused"):
        adapter.native_rows(receipt)


@pytest.mark.parametrize("drift", ["index", "head", "missing-event"])
def test_writer_seals_diagnostic_on_observed_drift(repo, drift):
    stage(repo)
    directory, _, _ = capture.begin(repo)
    if drift != "missing-event":
        capture.event(directory, "sample.txt", "scanned", "0")
    if drift == "index":
        stage(repo, True)
    elif drift == "head":
        git(repo, "commit", "--quiet", "--allow-empty", "-m", "Advance fixture HEAD")
    capture.finish(directory, 0)
    record, _ = capture.read_receipt(directory / "receipt.json")
    assert record["pii_staged_policy_check_passed"] is None
    assert adapter.native_rows(directory / "receipt.json") == ()


@pytest.mark.parametrize("restore", [False, True])
def test_actual_gate_freezes_index_during_change_and_aba(repo, tmp_path, restore):
    stage(repo, True)
    index = repo / ".git/index"
    saved = tmp_path / "saved-index"
    clean = tmp_path / "clean-index"
    shutil.copyfile(index, saved)
    alternate = dict(os.environ, GIT_INDEX_FILE=str(clean))
    git(repo, "read-tree", "HEAD", env=alternate)
    stage(repo, False, env=alternate)
    wrapper_dir = tmp_path / "git-wrapper"
    wrapper_dir.mkdir()
    marker = tmp_path / "frozen-diff-count"
    observed = tmp_path / "changed-during-show"
    actual_git = shutil.which("git")
    wrapper = wrapper_dir / "git"
    # Fixture-only executable intercepts the THIRD frozen diff (the hook's
    # selection), after begin's original selection and independent crosscheck
    # have sealed the initial secret-bearing index.
    # The scanner still reads the frozen bytes while the actual index is clean.
    script = """#!/usr/bin/env python3
import os, pathlib, shutil, subprocess, sys
args = sys.argv[1:]
frozen = os.environ.get('GIT_INDEX_FILE', '').endswith('/original-index')
marker = pathlib.Path(os.environ['FIXTURE_DIFF_MARKER'])
if frozen and 'diff' in args and '--cached' in args:
    count = int(marker.read_text()) + 1 if marker.exists() else 1
    marker.write_text(str(count))
    if count == 3:
        shutil.copyfile(os.environ['FIXTURE_CLEAN_INDEX'], os.environ['FIXTURE_LIVE_INDEX'])
if frozen and 'show' in args:
    live = pathlib.Path(os.environ['FIXTURE_LIVE_INDEX']).read_bytes()
    clean = pathlib.Path(os.environ['FIXTURE_CLEAN_INDEX']).read_bytes()
    pathlib.Path(os.environ['FIXTURE_OBSERVED']).write_text(str(live == clean))
    result = subprocess.run([os.environ['FIXTURE_REAL_GIT'], *args])
    if os.environ['FIXTURE_RESTORE'] == '1':
        shutil.copyfile(os.environ['FIXTURE_SAVED_INDEX'], os.environ['FIXTURE_LIVE_INDEX'])
    raise SystemExit(result.returncode)
os.execv(os.environ['FIXTURE_REAL_GIT'], [os.environ['FIXTURE_REAL_GIT'], *args])
"""
    wrapper.write_text(script)
    wrapper.chmod(0o755)
    env = dict(os.environ, PATH=str(wrapper_dir) + os.pathsep + os.environ["PATH"],
               FIXTURE_DIFF_MARKER=str(marker), FIXTURE_LIVE_INDEX=str(index),
               FIXTURE_CLEAN_INDEX=str(clean), FIXTURE_SAVED_INDEX=str(saved),
               FIXTURE_REAL_GIT=actual_git, FIXTURE_OBSERVED=str(observed),
               FIXTURE_RESTORE="1" if restore else "0")
    code, receipt = run(repo, env)
    record, _ = capture.read_receipt(receipt)
    assert observed.read_text() == "True", "live index must actually differ during original scan"
    assert code == 1, "original frozen secret must still block despite live clean index"
    assert record["checks"]["live_index_unchanged"] is restore
    assert record["pii_staged_policy_check_passed"] is (False if restore else None)


def test_private_exclusive_outputs_and_duplicate_json_refusal(repo):
    stage(repo)
    _, receipt = run(repo)
    assert receipt.parent.stat().st_mode & 0o777 == 0o700
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in receipt.parent.rglob("*") if p.is_file())
    with pytest.raises(FileExistsError):
        capture.write(receipt.parent, "receipt.json", b"replacement")
    receipt.write_bytes(b'{"schema":"first","schema":"second"}')
    with pytest.raises(ProjectionError, match="custody refused"):
        adapter.native_rows(receipt)


@pytest.mark.parametrize("operation", ["size", "show"])
def test_original_git_read_error_keeps_exit_but_has_no_finding(repo, tmp_path, operation):
    stage(repo)
    wrappers = tmp_path / "reader-failure"
    wrappers.mkdir()
    wrapper = wrappers / "git"
    wrapper.write_text("""#!/usr/bin/env python3
import os, sys
args = sys.argv[1:]
failing = ('cat-file' in args and '-s' in args) if os.environ['FIXTURE_FAIL_READ'] == 'size' else 'show' in args
if failing:
    raise SystemExit(128)
os.execv(os.environ['FIXTURE_REAL_GIT'], [os.environ['FIXTURE_REAL_GIT'], *args])
""")
    wrapper.chmod(0o755)
    env = dict(os.environ, PATH=str(wrappers) + os.pathsep + os.environ["PATH"],
               FIXTURE_FAIL_READ=operation, FIXTURE_REAL_GIT=shutil.which("git"))
    code, receipt = run(repo, env)
    record, _ = capture.read_receipt(receipt)
    assert code == 0, "legacy masked-read exit must remain unchanged"
    assert record["pii_staged_policy_check_passed"] is None
    assert record["events"][0]["status"] == "read-error"


@pytest.mark.parametrize("field", ["exit_code", "ended_utc", "checks"])
def test_receipt_reseal_cannot_replace_original_terminal(repo, field):
    stage(repo)
    _, receipt = run(repo)
    record, _ = capture.read_receipt(receipt)
    if field == "exit_code":
        record[field] = 1
    elif field == "ended_utc":
        record[field] = "2099-01-01T00:00:00Z"
    else:
        record[field] = {**record[field], "head_unchanged": False}
    record.pop("receipt_sha256")
    record["receipt_sha256"] = capture.sha(capture.canonical(record))
    receipt.write_bytes(capture.canonical(record) + b"\n")
    with pytest.raises(ProjectionError, match="custody refused"):
        adapter.native_rows(receipt)


@pytest.mark.parametrize("tool", ["python3", "tee", "mktemp"])
def test_recorder_setup_failure_preserves_blocking_gate(repo, tmp_path, tool):
    stage(repo, True)
    wrappers = tmp_path / "recorder-failure"
    wrappers.mkdir()
    marker = tmp_path / "first-mktemp"
    wrapper = wrappers / tool
    actual = shutil.which(tool)
    wrapper.write_text("""#!/usr/bin/env python3
import os, pathlib, sys
tool = os.environ['FIXTURE_FAIL_TOOL']
if tool == 'tee' or (tool == 'python3' and any(a.endswith('/pii_staged_capture.py') for a in sys.argv)):
    raise SystemExit(1)
marker = pathlib.Path(os.environ['FIXTURE_SETUP_MARKER'])
if tool == 'mktemp' and not marker.exists():
    marker.write_text('failed first recorder temporary control only')
    raise SystemExit(1)
os.execv(os.environ['FIXTURE_REAL_TOOL'], [os.environ['FIXTURE_REAL_TOOL'], *sys.argv[1:]])
""")
    # Use an absolute interpreter so a python3 wrapper cannot recurse itself.
    wrapper.write_text(wrapper.read_text().replace("#!/usr/bin/env python3", "#!" + sys.executable, 1))
    wrapper.chmod(0o755)
    env = dict(os.environ, PATH=str(wrappers) + os.pathsep + os.environ["PATH"],
               FIXTURE_FAIL_TOOL=tool, FIXTURE_REAL_TOOL=actual,
               FIXTURE_SETUP_MARKER=str(marker))
    result = subprocess.run(["bash", str(HOOK)], cwd=repo, env=env,
                            capture_output=True, timeout=60)
    assert result.returncode == 1, "recorder failure must never admit a staged secret"
    assert b"BLOCKED:" in result.stderr, "actual scanner must still execute"


@pytest.mark.parametrize("secret", [False, True])
def test_actual_cli_dry_run_exports_safe_report_only(repo, tmp_path, secret):
    indexed_name = "private-name-sentinel-not-public.txt"
    stage(repo, secret, name=indexed_name)
    _, receipt = run(repo)
    record, _ = capture.read_receipt(receipt)
    result = subprocess.run([sys.executable, str(ROOT / "scripts/vidya/cli.py"),
                             "--ledger", str(tmp_path / "disposable-ledger.jsonl"), "--json",
                             "ingest", "pii-staged-gate", "--path", str(receipt),
                             "--as-of", record["ended_utc"], "--dry-run"],
                            capture_output=True, timeout=60)
    assert result.returncode == 0, "real CLI source enrollment must project"
    output = result.stdout + result.stderr
    assert indexed_name.encode() not in output and body(True).strip().encode() not in output
    report = json.loads(result.stdout)
    assert report["rows_projected"] == 1 and report["frames_emitted"] == 3
    assert not (tmp_path / "disposable-ledger.jsonl").exists()


@pytest.mark.parametrize("field", ["stage_entries", "selection", "comparison_tree"])
def test_coherent_metadata_reseal_cannot_change_original_git_snapshot(repo, field):
    stage(repo)
    _, receipt = run(repo)
    record, _ = capture.read_receipt(receipt)
    request_path = receipt.parent / "execution-request.json"
    request = capture.load(request_path.read_bytes())
    if field == "comparison_tree":
        request[field] = "0" * len(request[field])
    else:
        member = receipt.parent / request[field]["name"]
        # A coherent temporary metadata reseal still lacks the original Git
        # snapshot binding. It must not establish a new selected proposition.
        member.write_bytes(b"")
        request[field]["sha256"] = capture.sha(b"")
        if field == "stage_entries":
            request["stage_entries_sha256"] = capture.sha(b"")
        else:
            request["inputs"] = []
            record["events"] = []
            (receipt.parent / "events.nul").write_bytes(b"")
    request_path.write_bytes(capture.canonical(request) + b"\n")
    record.update(request)
    terminal_path = receipt.parent / "original-terminal.json"
    terminal = capture.load(terminal_path.read_bytes())
    terminal["request_sha256"] = capture.sha(request_path.read_bytes())
    terminal["events_sha256"] = capture.sha((receipt.parent / "events.nul").read_bytes())
    terminal_path.write_bytes(capture.canonical(terminal) + b"\n")
    record.update(terminal)
    record["terminal"]["sha256"] = capture.sha(terminal_path.read_bytes())
    record["artifacts"] = [{"name": p.relative_to(receipt.parent).as_posix(),
                             "sha256": capture.sha(p.read_bytes())}
                            for p in sorted(receipt.parent.rglob("*")) if p.is_file() and p != receipt]
    record.pop("receipt_sha256")
    record["receipt_sha256"] = capture.sha(capture.canonical(record))
    receipt.write_bytes(capture.canonical(record) + b"\n")
    with pytest.raises(ProjectionError, match="custody refused"):
        adapter.native_rows(receipt)


def test_original_rename_selection_is_preserved_and_declines_crosscheck(repo):
    stage(repo, name="before.txt")
    git(repo, "commit", "--quiet", "-m", "Original fixture path")
    git(repo, "config", "diff.renames", "true")
    git(repo, "mv", "before.txt", "after.txt")
    original = git(repo, "diff", "--cached", "--name-only", "-z", "--diff-filter=ACM").stdout
    code, receipt = run(repo)
    record, _ = capture.read_receipt(receipt)
    assert (receipt.parent / record["selection"]["name"]).read_bytes() == original
    assert code == 0 and record["selection_reproducible"] is False
    assert adapter.native_rows(receipt) == ()


def test_policy_copy_aba_is_observed_without_executing_captured_code(repo, tmp_path, monkeypatch):
    stage(repo)
    policy_root = tmp_path / "disposable-policy-source/scripts"
    hook_dir = policy_root / "hooks"
    hook_dir.mkdir(parents=True)
    (policy_root / "ci").mkdir()
    for name in ("pii_precommit.sh", "fixture_snapshot_provenance.py"):
        shutil.copyfile(ROOT / "scripts/hooks" / name, hook_dir / name)
    shutil.copyfile(ROOT / "scripts/ci/native_conformance.py", policy_root / "ci/native_conformance.py")
    monkeypatch.setattr(capture, "HOOK_DIR", hook_dir)
    # This case contains no native exemptions. Keep archive proof code on the
    # trusted candidate source instead of importing any copied policy snapshot.
    monkeypatch.setattr(capture, "provenance_module", lambda: __import__(
        "scripts.hooks.fixture_snapshot_provenance", fromlist=["exemptions"]))
    directory, _, _ = capture.begin(repo)
    policy = hook_dir / "pii_precommit.sh"
    original = policy.read_bytes()
    policy.write_bytes(original + b"\n# Disposable changed policy\n")
    policy.write_bytes(original)
    capture.event(directory, "sample.txt", "scanned", "0")
    capture.finish(directory, 0)
    record, _ = capture.read_receipt(directory / "receipt.json")
    assert capture.sha(policy.read_bytes()) == record["policy"][0]["artifact"]["sha256"]
    assert record["checks"]["policy_unchanged"] is False
    assert adapter.native_rows(directory / "receipt.json") == ()


def test_regular_fifo_refuses_before_open(tmp_path):
    fifo = tmp_path / "disposable-fifo"
    os.mkfifo(fifo, 0o600)
    command = ("from pathlib import Path; import sys; "
               "from scripts.hooks.pii_staged_capture import regular\n"
               "try: regular(Path(sys.argv[1]))\n"
               "except ValueError: raise SystemExit(0)\n"
               "raise SystemExit(1)\n")
    result = subprocess.run([sys.executable, "-c", command, str(fifo)], cwd=ROOT,
                            capture_output=True, timeout=3)
    assert result.returncode == 0, "nonregular original must refuse without blocking"


@pytest.mark.parametrize("role", ["terminal", "index", "comparison_commit"])
def test_escaped_request_pin_refuses_before_external_read(repo, tmp_path, monkeypatch, role):
    stage(repo)
    _, receipt = run(repo)
    record, _ = capture.read_receipt(receipt)
    outside = tmp_path / "external-private-witness"
    outside.write_text("private external sentinel\n")
    bad = {"name": str(outside), "sha256": capture.sha(outside.read_bytes())}
    if role == "terminal":
        record[role] = bad
    else:
        request_path = receipt.parent / "execution-request.json"
        request = capture.load(request_path.read_bytes())
        request[role] = bad
        request_path.write_bytes(capture.canonical(request) + b"\n")
        record.update(request)
        for pin in record["artifacts"]:
            if pin["name"] == "execution-request.json":
                pin["sha256"] = capture.sha(request_path.read_bytes())
    record.pop("receipt_sha256")
    record["receipt_sha256"] = capture.sha(capture.canonical(record))
    receipt.write_bytes(capture.canonical(record) + b"\n")
    actual_regular = capture.regular
    def observed_regular(path):
        assert path != outside, "untrusted external member must never be opened"
        return actual_regular(path)
    monkeypatch.setattr(capture, "regular", observed_regular)
    with pytest.raises(ProjectionError, match="custody refused"):
        adapter.native_rows(receipt)


@pytest.mark.parametrize("staged_before", [False, True])
@pytest.mark.parametrize("secret", [False, True])
def test_actual_git_commit_only_installed_hook_captures_temporary_index(repo, staged_before, secret):
    stage(repo)
    git(repo, "commit", "--quiet", "-m", "Tracked path baseline")
    original_head = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
    hook = repo / ".git/hooks/pre-commit"
    hook.write_text("#!/bin/bash\nexec bash " + shlex.quote(str(HOOK)) + "\n")
    hook.chmod(0o755)
    path = repo / "sample.txt"
    path.write_text(body(True) if secret else "changed ordinary fixture text\n")
    if staged_before:
        git(repo, "add", "--", "sample.txt")
    result = subprocess.run(["git", "-C", str(repo), "commit", "--quiet", "--only",
                             "-m", "Actual installed-hook pathspec transaction", "--", "sample.txt"],
                            capture_output=True, timeout=60)
    assert result.returncode == int(secret), "actual Git transaction exit must match unchanged PII gate"
    receipts = list((repo / ".git/epyc-private/pii-gates").glob("*/receipt.json"))
    assert len(receipts) == 1, "actual commit-only hook must seal its original temporary-index finding"
    record, _ = capture.read_receipt(receipts[0])
    assert "next-index-" in Path(record["original_index"]).name
    assert record["head"] == original_head
    assert record["pii_staged_policy_check_passed"] is (not secret)
    assert record["exit_code"] == result.returncode
    assert record["counts"]["selected"] == 1
    item = record["inputs"][0]
    assert (receipts[0].parent / item["artifact"]["name"]).read_bytes() == path.read_bytes()


@pytest.mark.parametrize("existing_ancestors", [False, True])
def test_setgid_git_common_new_custody_and_ancestor_only_migration(repo, existing_ancestors):
    common = repo / ".git"
    common.chmod(0o2755)
    ancestors = common / "epyc-private/pii-gates"
    old = None
    if existing_ancestors:
        ancestors.mkdir(parents=True)
        (common / "epyc-private").chmod(0o2700)
        ancestors.chmod(0o2700)
        old = ancestors / "original-unsupported-capsule"
        old.mkdir()
        old.chmod(0o2700)
        original = old / "unchanged-original.bin"
        original.write_bytes(b"unsupported original must remain unchanged\n")
        original.chmod(0o600)
        metadata = (old.stat().st_mode, original.stat().st_mode, original.read_bytes())
    stage(repo)
    _, receipt = run(repo)
    capture.read_receipt(receipt)
    assert common.stat().st_mode & 0o7777 == 0o2755
    for path in (common / "epyc-private", ancestors, receipt.parent):
        assert path.stat().st_mode & 0o7777 == 0o700
    # A second original execution reuses exact-safe ancestors successfully.
    second_code, second_receipt = run(repo)
    capture.read_receipt(second_receipt)
    assert second_code == 0 and second_receipt != receipt
    assert second_receipt.parent.stat().st_mode & 0o7777 == 0o700
    if old is not None:
        assert (old.stat().st_mode, original.stat().st_mode, original.read_bytes()) == metadata


@pytest.mark.parametrize("permission", [0o750, 0o1700, 0o4700])
def test_unsafe_existing_ancestor_is_not_migrated(repo, permission):
    ancestor = repo / ".git/epyc-private"
    ancestor.mkdir()
    ancestor.chmod(permission)
    stage(repo)
    with pytest.raises(ValueError, match="parent is not owner-only"):
        capture.begin(repo)
    assert ancestor.stat().st_mode & 0o7777 == permission


if __name__ == "__main__":
    raise SystemExit("REFUSING: pytest-fixture suite; run: python -m pytest scripts/hooks/tests/test_pii_staged_capture.py -q")
