#!/usr/bin/env python3
"""Exercise the published-reference hook in isolated Git repositories."""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from contextlib import ExitStack
from pathlib import Path

PACKET = Path(__file__).resolve().parent
INDEX = "research/intake_index.yaml"


def main(work):
    sandbox = work.resolve() / "native-run"
    sandbox.mkdir()
    seed = sandbox / "seed"
    hook_host = sandbox / "hook-host"
    origin = sandbox / "origin.git"
    primary = sandbox / "primary"
    state = sandbox / "state"
    marker = state / "ledger.jsonl.sync.json"
    pins = json.loads((PACKET / "source-pins.json").read_text())
    source = Path(pins["source_repo"])
    revision = pins["source_commit"]
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("source pin must be a full commit ID")

    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    for key in ("VIDYA_LEDGER", "VIDYA_SCRATCH"):
        env.pop(key, None)
    env.update(
        GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull,
        GIT_AUTHOR_NAME="Native Test", GIT_AUTHOR_EMAIL="native@example.invalid",
        GIT_COMMITTER_NAME="Native Test", GIT_COMMITTER_EMAIL="native@example.invalid",
        GIT_TERMINAL_PROMPT="0", VIDYA_STATE_DIR=str(state),
        VIDYA_CONTROL_RECEIPTS=str(sandbox),
    )
    deadline = float(os.environ["VIDYA_CONTROL_DEADLINE"])
    stop = Path(os.environ["FILLER_STOPFILE"])

    def run(name, argv, cwd, *, command_env=env, capture_receipt=True, cleanup=False):
        remaining = deadline - time.monotonic()
        if not cleanup and (stop.exists() or remaining <= 12):
            raise RuntimeError("stopped or expired")
        timeout = 10 if cleanup else min(180, remaining - 12)
        result = subprocess.run(argv, cwd=cwd, env=command_env, capture_output=True,
                                text=True, timeout=timeout)
        if capture_receipt or result.returncode:
            (sandbox / (name + ".stdout")).write_text(result.stdout)
        (sandbox / (name + ".stderr")).write_text(result.stderr)
        (sandbox / (name + ".json")).write_text(json.dumps({
            "argv": list(map(str, argv)), "cwd": str(cwd), "exit": result.returncode,
        }, indent=2) + "\n")
        result.check_returncode()
        return result.stdout

    def git(name, cwd, *args, **kwargs):
        return run(name, ["git", *args], cwd, **kwargs)

    assert git("source_commit", source, "rev-parse", "--verify", revision + "^{commit}").strip() == revision
    objects = git("source_objects", source, "rev-parse", "--path-format=absolute", "--git-path", "objects").strip()
    scripts_tree = git("source_tree", source, "rev-parse", revision + ":scripts/vidya").strip()
    index = git("source_index", source, "show", f"{revision}:{INDEX}", capture_receipt=False)
    starts = [match.start() for match in re.finditer(r"^- id: intake-", index, re.M)]
    assert len(starts) >= 4

    git("init_origin", sandbox, "init", "--bare", "-b", "main", str(origin))
    # The unmodified installer resolves the first worktree, so give the private
    # repository a non-bare primary with the pinned scripts. Both experimental
    # checkouts are linked and detached from this repository.
    git("init_hook_host", sandbox, "init", "-b", "main", str(hook_host))
    git("bootstrap_hook_host", hook_host, "commit", "--allow-empty", "-m", "bootstrap fixture")

    def remove_worktree(receipt, checkout):
        if checkout.exists():
            git(receipt, hook_host, "worktree", "remove", "--force", str(checkout), cleanup=True)
        assert not checkout.exists()

    with ExitStack() as cleanup:
        cleanup.callback(remove_worktree, "seed_worktree_remove", seed)
        git("seed_worktree_add", hook_host, "worktree", "add", "--detach", str(seed), "HEAD")
        assert (seed / ".git").is_file()
        assert git("seed_detached", seed, "rev-parse", "--abbrev-ref", "HEAD").strip() == "HEAD"
        source_env = dict(env, GIT_ALTERNATE_OBJECT_DIRECTORIES=objects)
        git("seed_scripts", seed, "restore", "--source=" + revision, "--staged", "--worktree",
            "--", "scripts/vidya", command_env=source_env)
        (seed / INDEX).parent.mkdir()
        (seed / INDEX).write_text(index[starts[0]:starts[2]])
        git("seed_add", seed, "add", INDEX, command_env=source_env)
        git("seed_commit", seed, "commit", "-m", "seed", command_env=source_env)
        # The primary's tip stays empty relative to its parent so the
        # post-commit safety net cannot fetch an unpublished detached edit.
        git("seed_empty_tip", seed, "commit", "--allow-empty",
            "-m", "prepare native publication", command_env=source_env)
        seed_tip = git("seed_head", seed, "rev-parse", "HEAD").strip()
        git("materialize_hook_host", hook_host, "reset", "--hard", seed_tip, command_env=source_env)
        git("seed_repack", hook_host, "repack", "-a", command_env=source_env)
        assert git("seed_tree", seed, "rev-parse", "HEAD:scripts/vidya").strip() == scripts_tree
        first_worktree = git("hook_host_worktrees", hook_host, "worktree", "list", "--porcelain")
        assert first_worktree.splitlines()[0] == f"worktree {hook_host}"
        git("configure_origin", hook_host, "remote", "add", "origin", str(origin))
        git("seed_push", hook_host, "push", "-u", "origin", "main")

        hooks = hook_host / ".git/hooks"
        git("configure_common_hooks", hook_host, "config", "core.hooksPath", str(hooks))
        (hooks / "post-commit").write_text(
            '#!/bin/sh\nprintf original-hook-ran > "$VIDYA_CONTROL_RECEIPTS/original-hook-receipt"\n')
        (hooks / "post-commit").chmod(0o755)
        (hooks / "reference-transaction").write_text(
            '#!/bin/sh\ncat >> "$VIDYA_CONTROL_RECEIPTS/reference-hook-receipt"\n')
        (hooks / "reference-transaction").chmod(0o755)
        installer = ["bash", str(seed / "scripts/vidya/install_sync_hook.sh")]
        run("installer", installer, seed)
        assert run("installer_again", installer, seed) == ""

        cleanup.callback(remove_worktree, "worktree_remove", primary)
        git("worktree_add", hook_host, "worktree", "add", "--detach", "--no-checkout",
            str(primary), seed_tip)
        git("worktree_sparse", primary, "sparse-checkout", "set", "--no-cone", "/" + INDEX)
        git("worktree_checkout", primary, "read-tree", "-mu", "HEAD")
        assert (primary / ".git").is_file()
        assert (primary / INDEX).read_text() == index[starts[0]:starts[2]]
        (primary / INDEX).write_text(index[starts[0]:starts[3]])
        git("intake_add", primary, "add", INDEX)
        git("intake_commit", primary, "commit", "-m", "native intake update")
        assert (sandbox / "original-hook-receipt").read_text() == "original-hook-ran"
        assert not marker.exists()
        head = git("head_before_push", primary, "rev-parse", "HEAD")
        remote_before = git("remote_before_push", origin, "rev-parse", "refs/heads/main")
        git("ordinary_push", primary, "push", "origin", "HEAD:refs/heads/main")
        assert "refs/remotes/origin/main" in (sandbox / "reference-hook-receipt").read_text()
        status = json.loads(run("postpush_check", [
            sys.executable, str(seed / "scripts/vidya/cli.py"), "--json", "sync",
            "--check", "--no-fetch",
        ], seed))
        index_sha = hashlib.sha256((primary / INDEX).read_bytes()).hexdigest()
        marker_data = json.loads(marker.read_text())
        assert status["fresh"] and status["lag_entries"] == 0 and status["index"] == "origin/main"
        assert status["index_sha256"] == index_sha and index_sha in marker_data["seen_sha256"]
        (sandbox / "native-marker.json").write_bytes(marker.read_bytes())
        assert git("remote_after_push", origin, "rev-parse", "refs/heads/main") == head != remote_before

    (sandbox / "PASS.json").write_text(json.dumps({
        "scope": "disposable detached-worktree commit and push, reference hook and automatic origin/main fold",
        "source_commit": revision, "manual_sync": False, "production_acceptance": False,
        "postpush_status": status, "worktree_removed": True, "seed_worktree_removed": True,
    }, indent=2) + "\n")
    print(sandbox / "PASS.json")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
