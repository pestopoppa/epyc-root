import json
import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "rowflow" / "publish_and_clean.sh"


def setup_fake(tmp_path, fail=False):
    import shutil
    bindir = tmp_path / "bin"
    bindir.mkdir()
    script = bindir / "publish_and_clean.sh"
    shutil.copy(SCRIPT, script)
    (bindir / "rowflow.py").write_text("def parse_launcher(p): return {}\ndef referenced_paths(o): return []\n")
    (bindir / "publish_row.py").write_text('''import json, os, sys
if os.environ.get("FAIL_PUBLISH") == "1": sys.exit(2)
spec = json.load(open(sys.argv[1])); flags = sys.argv[sys.argv.index("--flags") + 1]
p = os.path.join(flags, "dryrun", spec["id"], "unpublished.json")
os.makedirs(os.path.dirname(p), exist_ok=True)
json.dump({"id": spec["id"], "scratch_root": spec["scratch_root"],
           "launcher": {"path": spec["scratch_root"] + "/launch.sh"}}, open(p, "w"))
''')
    repo = tmp_path / "repo"
    cleanup = repo / "scripts/system/scratch_cleanup.py"
    cleanup.parent.mkdir(parents=True)
    cleanup.write_text('import os,sys\nopen(os.environ["TEST_CLEAN_LOG"],"w").write("\\n".join(sys.argv[1:]))\n')
    spec = tmp_path / "spec.json"
    root = "/mnt/raid0/llm/tmp/cx7-test-live-row"
    spec.write_text(json.dumps({"id": "test-row", "scratch_root": root}))
    flags = tmp_path / "flags"
    env = dict(os.environ, ROWFLOW_REPO=str(repo), TEST_CLEAN_LOG=str(tmp_path / "clean.log"))
    if fail:
        env["FAIL_PUBLISH"] = "1"
    return script, spec, flags, env, root


def run(script, spec, flags, env, *args):
    return subprocess.run(["bash", str(script), str(spec), "--flags", str(flags), *args], env=env,
                          text=True, capture_output=True)


def test_failed_publish_never_cleans(tmp_path):
    script, spec, flags, env, root = setup_fake(tmp_path, fail=True)
    result = run(script, spec, flags, env, "--cleanup-root", "/mnt/raid0/llm/tmp/cx7-unrelated")
    assert result.returncode == 2
    assert not (tmp_path / "clean.log").exists()


def test_cleanup_refuses_live_row_overlap(tmp_path):
    script, spec, flags, env, root = setup_fake(tmp_path)
    result = run(script, spec, flags, env, "--cleanup-root", root)
    assert result.returncode == 2 and "overlaps" in result.stderr
    assert not (tmp_path / "clean.log").exists()


def test_cleanup_protects_all_manifests_for_the_row(tmp_path):
    script, spec, flags, env, root = setup_fake(tmp_path)
    other = "/mnt/raid0/llm/tmp/cx7-test-ready-row"
    ready = flags / "ready" / "test-row.json"
    ready.parent.mkdir(parents=True)
    ready.write_text(json.dumps({"id": "test-row", "scratch_root": other,
                                 "launcher": {"path": other + "/launch.sh"}}))
    result = run(script, spec, flags, env, "--cleanup-root", other)
    assert result.returncode == 2 and "overlaps" in result.stderr
    assert not (tmp_path / "clean.log").exists()


def test_explicit_unrelated_target_uses_guarded_tool(tmp_path):
    script, spec, flags, env, root = setup_fake(tmp_path)
    target = "/mnt/raid0/llm/tmp/cx7-unrelated"
    result = run(script, spec, flags, env, "--cleanup-root", target)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "clean.log").read_text().splitlines() == ["apply", "--root", target]


def test_cleanup_refuses_broad_or_glob_target(tmp_path):
    script, spec, flags, env, root = setup_fake(tmp_path)
    result = run(script, spec, flags, env, "--cleanup-worktree", "/mnt/raid0/llm/worktrees/*")
    assert result.returncode == 2
    assert not (tmp_path / "clean.log").exists()
