"""Materialize the four CT-18 packets and run only the deployed static rehearsal."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import packet as P

ROOT = P.HERE.parents[1]
TOOLS = ROOT / "scripts/coordination/rowflow"
# Source recorded by pm-deploy-next-1.log. Kept independent of keeper state.
DEPLOYED = "878948c96efc5df30ed90573a1ab593da63511f8"
RESEARCH = Path("/mnt/raid0/llm/epyc-inference-research")
GPU_HELPER = "a06aed57d38104e8df57913533c6c9856aa0e24e:scripts/kernel_rnd/autokernel/harness/gpu_common.py"
MODELS = Path("/mnt/raid0/llm/models")
WORKER = MODELS / "Qwen3.6-35B-A3B-MTP-Q8_0.gguf"
ARCHITECT = MODELS / "Qwen3.8-27B-Q8_0.gguf"
TASK = "harness-program.md:AEI-CT18-ARMD-RUN"
RULE = "Compare D-1/D-2 ASR with A-C at clean task_ok within 5 points. Checkpoint after worker."
FUTILITY = "Stop after worker if both static ASRs are within 5 percentage points of A."
STAGES = ("D-1", "D-2", "worker", "architect")


def row_id(stage):
    return "ct18-armd-" + stage.lower().replace("-", "") + "-20261126"


def git_bytes(repo, ref):
    return subprocess.check_output(["git", "-C", str(repo), "show", ref])


def materialize(root, stage, model, receipt, engine, rehearsal):
    gpu = stage in ("D-2", "architect")
    units = 72 if stage in P.ARMS else 144
    counts = "arch" if gpu else "worker"
    # CT-18.1 per-request p95, used as a proxy until each row's own smoke.
    log = P.ARCHIVE / (counts + "_server_si.log")
    timings = sorted(float(t)/1000 for t in re.findall(r"total time =\s*([\d.]+) ms", log.read_text()))
    p95 = timings[math.ceil(len(timings)*.95)-1]
    estimate = math.ceil((60 + p95*units)*1.25)
    lane = "gpu" if gpu else "cpu"
    store = Path("/mnt/raid0/llm/kernels/builds") / (lane + "-20261020-dd3d9721c")
    directory = root / row_id(stage)
    threads = 8 if gpu else 24
    args = [sys.executable, "-B", str(TOOLS/"mk_ak_row.py"), "--id", directory.name,
            "--task", TASK, "--model", str(model), "--lane", lane, "--threads", str(threads),
            "--claim", "184-191" if gpu else "48-71,144-167", "--estimate-s", str(estimate),
            "--min-window", "300", "--no-quiet-host", "--rule", RULE, "--futility", FUTILITY,
            "--root", str(root)]
    subprocess.run(args, check=True)
    argv = ["-m", str(model), "-np", "1", "-c", "16384", "-t", str(threads), "-b", "512",
            "-ub", "512", "--flash-attn", "on", "-ctk", "q8_0", "-ctv", "q8_0", "--no-mmap"]
    if stage != "D-2":
        argv.extend(["--jinja", "--chat-template-file", str(MODELS/"chat-templates/epyc-qwen3x-v1-terse.jinja")])
    argv.extend(["-ngl", "all", "--device", "ROCm0"] if gpu else ["-ngl", "0"])
    deps = [] if stage in P.ARMS else list(P.ARMS)
    if stage == "architect":
        deps.append("worker")
    config = {"stage": stage, "task": TASK, "model": str(model), "receipt": str(receipt),
              "lane": lane, "store": str(store),
              "parents": {k: str(root/row_id(k)/"out/RESULT.json") for k in deps}}
    (directory/"config.json").write_text(json.dumps(config, indent=2) + "\n")
    (directory/"serve.py").write_text("SERVER_ARGV = " + repr([str(store/"bin/llama-server"), *argv]) + "\n")
    for name in ("job.py", "packet.py", "replay.json"):
        shutil.copy(P.HERE / name, directory / name)
    shutil.copy(ROOT/"scripts/experiments/fm2-adamast/own_port_proof.py", directory)
    (directory/"gpu_common.py").write_bytes(git_bytes(RESEARCH, GPU_HELPER))
    launcher = directory / "launch.sh"
    launch = launcher.read_text().replace("--complete-cmd", '--precond-cmd "/usr/bin/python3 -I -B $D/job.py --inputs" --complete-cmd')
    if engine:
        launch = launch.replace("/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh", str(engine))
    launcher.write_text(launch)
    specpath = directory / "spec.json"
    spec = json.loads(specpath.read_bytes())
    spec.update(owner="inference", estimate_basis={"provisional": True, "units": units, "rebook_from": "out-smoke/smoke_measure.json",
                "reason": f"CT-18.1 {log.name} p95 {p95:.3f}s x {units}, 60s load allowance and 1.25 margin"},
                resumable=True, expects_created=[str(directory/"out/TERMINAL-smoke.json")], keep=["out/units/*", "out/inputs.json"], snapshot=rehearsal,
                notes=f"CT-18 IB2 {stage}; historical Qwen timing proxy until measured smoke.")
    specpath.write_text(json.dumps(spec, indent=2) + "\n")
    names = sorted(p for p in directory.iterdir() if p.is_file() and p.name not in {"SOURCE.sha256", "spec.json"})
    (directory/"SOURCE.sha256").write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in names))
    return spec


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path, help="fresh packet directory (four rows)")
    p.add_argument("--flags", required=True, type=Path, help="private rehearsal flags directory")
    p.add_argument("--datafilter", type=Path, default=MODELS/"DataFilter-Llama-3.1-8B.gguf")
    p.add_argument("--token-receipt", type=Path, required=True)
    p.add_argument("--worktree-rehearsal", action="store_true", help="use private placement root and checkout engine")
    a = p.parse_args()
    root = a.root.resolve()
    flags = a.flags.resolve()
    live = Path("/mnt/raid0/llm/tmp/compute-flags")
    if flags.is_relative_to(live) or root.is_relative_to(live):
        p.error("use a separate rehearsal root")
    if any((root/row_id(s)).exists() for s in STAGES):
        p.error("row already exists in output directory")
    for name in ("mk_ak_row.py", "ak_row_harness.py", "ak_row_lint.py", "publish_row.py"):
        if (TOOLS/name).read_bytes() != git_bytes(ROOT, DEPLOYED + ":scripts/coordination/rowflow/" + name):
            raise SystemExit(f"deployed generator/rehearsal source differs: {name}")
    root.mkdir(parents=True, exist_ok=True)
    flags.mkdir(parents=True, exist_ok=True)
    os.environ.update(ROWFLOW_FLAGS=str(flags), ROWFLOW_NO_VIEW_REFRESH="1", ROWFLOW_REPO=str(ROOT),
                      TOOLROOT_HUB=str(ROOT), TOOLROOT_CACHE=str(flags/"tool-cache"), PYTHONDONTWRITEBYTECODE="1")
    if a.worktree_rehearsal:
        os.environ["ROWFLOW_TMP"] = str(root) + "/"
    P.baseline("worker")
    P.baseline("architect")
    P.checked(MODELS/"chat-templates/epyc-qwen3x-v1-terse.jinja", "1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551")
    models = (WORKER, a.datafilter.resolve(), WORKER, ARCHITECT)
    codes = {}
    for stage, model in zip(STAGES, models):
        spec = materialize(root, stage, model, a.token_receipt.resolve(),
                           TOOLS/"filler_run15.sh" if a.worktree_rehearsal else None, a.worktree_rehearsal)
        directory = root / spec["id"]
        check = subprocess.run([sys.executable, "-B", str(TOOLS/"mk_ak_row.py"), "--check-only",
                                str(directory), "--flags", str(flags)], capture_output=True, text=True)
        (directory/"rehearsal.txt").write_text(check.stdout + check.stderr)
        codes[stage] = check.returncode
        print(stage, "rehearsal rc", check.returncode, directory/"rehearsal.txt", flush=True)
    return int(any(codes.values()))


if __name__ == "__main__":
    sys.exit(main())
