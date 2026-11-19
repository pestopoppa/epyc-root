"""Stage the preparation job from two already detached, pinned worktrees."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROW = "vb-q38-preflight-planner-20261118"
READER_COMMIT = "f36c26d6df868016be962a8b631a879ef311f2f6"
RESEARCH_COMMIT = "6decaeda4481a841b3a85b55b0be87a6963b3042"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scratch", type=Path)
    args = parser.parse_args()
    scratch = args.scratch.resolve(strict=True)
    pins = {"reader_commit": READER_COMMIT, "research_commit": RESEARCH_COMMIT, "files": {}}
    for role, commit in (("reader", READER_COMMIT), ("research", RESEARCH_COMMIT)):
        checkout = scratch / role
        git = ["git", "-C", str(checkout)]
        assert subprocess.check_output([*git, "rev-parse", "HEAD"], text=True).strip() == commit
        paths = subprocess.check_output([*git, "ls-files", "-z", "scripts", "agents/shared"]).decode()
        for name in filter(None, paths.split("\0")):
            source = checkout / name
            if source.is_file() and not source.is_symlink():
                pins["files"][f"{role}/{name}"] = sha(source)
    for name in ("probe.py", "job.py", "research-model-preflight.patch"):
        if (HERE / name).resolve() != (scratch / name).resolve():
            shutil.copyfile(HERE / name, scratch / name)
        pins["files"][name] = sha(scratch / name)
    for source in sorted((scratch / "fixture").rglob("*.json")):
        if source.is_file():
            pins["files"][str(source.relative_to(scratch))] = sha(source)
    manifest = scratch / "source-pins.json"
    manifest.write_text(json.dumps(pins, indent=2, sort_keys=True) + "\n")
    pin = sha(manifest)
    directory = scratch / "launcher"
    directory.mkdir(exist_ok=True)
    for name in ("official", "engine-work"):
        (scratch / name).mkdir(exist_ok=True)
    launcher = directory / "launch.sh"
    launcher.write_text(f"""#!/bin/bash
set -euo pipefail
D={scratch}
/usr/bin/sha256sum --check --status <<'SEAL'
{sha(scratch / 'job.py')}  {scratch}/job.py
{pin}  {scratch}/source-pins.json
SEAL
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id {ROW} --class cpu --role build --gpu-quiet none \\
  --min-window 120 --stop "$D/STOP" --workdir "$D/engine-work" \\
  --complete-cmd "/usr/bin/python3 -I -B $D/job.py complete --pins-sha256 {pin}" \\
  --cmd "/usr/bin/python3 -I -B $D/job.py run --pins-sha256 {pin}"
""")
    launcher.chmod(0o750)
    template = {"schema": "epyc.row.v3", "kind": "compute", "id": ROW,
                "lineage": "vidya-q38-preflight-planner", "lane": "cpu",
                "owner": "handoff-vidya-belief-substrate",
                "handoff_task": "vidya-belief-substrate-program.md:VB-MI210-PAIRED-DIAG-WIRE",
                "regions": "any-cpu-quarter", "shape": "sub-quarter", "estimate_s": 300,
                "min_window_s": 120, "max_window_s": 420, "first_progress_s": 120,
                "budget_gib": 0.01, "busy_fraction": 0.25, "ram_gib": 1,
                "dryrun_native_result": True, "total_units": 2, "unit_key": "control_count",
                "result_format": "json", "result_path": str(scratch / "official/RESULT.json"),
                "launcher": str(launcher), "scratch_root": str(scratch),
                "keep": ["reader/**", "research/**", "fixture/**", "launcher/**", "*.py",
                         "*.json", "*.patch", "official/**", "official-*/**", "publisher-smoke-*/**"],
                "decision_rule": ("control_count == 2 and baseline_visible == 0 and candidate_visible > 0 "
                                  "and native_q38_acceptance_count == 0 and refusal_count == 0"),
                "notes": ("Software-only on four granted CPUs. The real Research runner builds two planner "
                          "contexts from a pregrant synthetic file with and without the verified exact digest. "
                          "Pass count is higher-is-better. Checkpoint both actor receipts. Stop on answer "
                          "after both controls or on drift, refusal, STOP or the earlier of deadline and "
                          "300 seconds. Zero native model loads, GPU use, actor calls or native Q38 acceptance.")}
    (scratch / "spec.json").write_text(json.dumps(template, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
