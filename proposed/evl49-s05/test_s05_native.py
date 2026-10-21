"""One bounded original case; generation and harness dry only."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def run(argv, cwd, directory):
    directory.mkdir(parents=True, exist_ok=True)
    outcome = {"argv": argv, "cwd": str(cwd), "exit": None}
    try:
        result = subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        outcome["exit"] = result.returncode
        stdout, stderr = result.stdout, result.stderr
    except subprocess.TimeoutExpired as exc:
        stdout, stderr = exc.stdout or b"", exc.stderr or b""
        outcome["error"] = "timeout"
    for name, raw in (("stdout.raw", stdout), ("stderr.raw", stderr),
                      ("argv-exit.json", (json.dumps(outcome, indent=2) + "\n").encode())):
        with (directory / name).open("xb") as f:
            f.write(raw)
    print(json.dumps(outcome), stdout.decode(errors="replace"))
    print(stderr.decode(errors="replace"), file=sys.stderr)
    assert outcome["exit"] == 0, outcome
    return stdout


def test_corrected_roster_and_unchanged_dry_plan():
    research = Path(os.environ["S05_RESEARCH"])
    output = Path.cwd() / "s05-generated"
    assert not output.exists()
    run([sys.executable, "-B", "-m", "unittest", "-v", "test_s05_sourceprep"], HERE, output / "synthetic")
    run([sys.executable, "-B", str(HERE / "s05_sourceprep.py"), "generate", "--research-root", str(research),
         "--output-dir", str(output / "manifests"), "--write"], HERE, output / "generation")
    roster = json.loads((output / "manifests/ROSTER-MANIFEST.json").read_bytes())
    assert roster["candidate_cell_count"] == 33
    for row in roster["cells"]:
        raw = (output / "manifests" / row["path"]).read_bytes()
        assert len(raw) == row["bytes"] and hashlib.sha256(raw).hexdigest() == row["sha256"]
    for model, count, window in (("qwen36_q8_0", 16, "w1"), ("qwen3_next_80b", 17, "w4")):
        paths = sorted((output / "manifests" / model).glob("*.json"))
        assert len(paths) == count
        argv = [sys.executable, "-B", "scripts/benchmark/server_numa_np_sweep.py", "--llama-server",
                "/mnt/raid0/llm/kernels/production/cpu/llama-server"]
        for path in paths:
            argv += ["--cell-manifest", str(path)]
        argv += ["--question-pool", os.environ["S05_POOL"],
                 "--output-root", str(output / "dry"), "--run-id", window]
        assert "--execute" not in argv and "--i-have-operator-grant" not in argv
        stdout = run(argv, research, output / ("harness-" + window))
        assert b"no process spawned" in stdout
        record = json.loads((output / "dry" / window / "manifest.json").read_bytes())
        assert record["dry_run"] is True and record["decision_grade"] is False
        assert len(record["cells"]) == count
