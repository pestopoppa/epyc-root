#!/usr/bin/env python3
"""Seal the TOC-MP-4 packet offline using existing weight custody."""
import argparse
import hashlib
import json
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRATCH = Path("/mnt/raid0/llm/tmp/delegation-context-preassembly/mp4")
SOURCE = SCRATCH / "source"
ORCH = Path("/mnt/raid0/llm/epyc-orchestrator")
REPORT = SCRATCH.parent / "mp4-preparation-report.json"
FLAGS = SCRATCH.parent.parent / "compute-flags"
HARNESS_REF = "ed0496bf38d9228bd8420f5b8c3fde238097de9f"
CMP3_REF = "ec229163159fd36a046808b6c84993257590fc17"
LOCAL_FILES = ("assessment.py", "runner.py", "trial.py", "launcher.sh", "spec.json", "README.md", "prepare.py")
HARNESS = {"graph_trial.py": "toc-cmp-4-live/graph_trial.py", "cmp4_runner.py": "toc-cmp-4-live/runner.py",
           "analysis.py": "toc-cmp-4-live/analysis.py", "cmp3_live.py": "toc-cmp-3-live/cmp3_live.py"}


def base_bytes(relative, ref):
    return subprocess.check_output(["git", "-C", str(HERE), "show",
                                    f"{ref}:scripts/experiments/{relative}"])


def prepare():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    packet = SCRATCH / "packet"
    if packet.exists():
        subprocess.run([sys.executable, "-B", str(packet / "runner.py"), "verify"], check=True)
        if any((HERE / name).read_bytes() != (packet / name).read_bytes() for name in LOCAL_FILES):
            raise ValueError("prepared packet differs from checkout")
        return packet / "spec.json"

    with tempfile.TemporaryDirectory(prefix="packet-", dir=SCRATCH) as temporary:
        staged = Path(temporary) / "packet"
        staged.mkdir()
        for name in LOCAL_FILES:
            shutil.copy2(HERE / name, staged)
        for name, path in HARNESS.items():
            ref = CMP3_REF if name == "cmp3_live.py" else HARNESS_REF
            (staged / name).write_bytes(base_bytes(path, ref))
        sys.path.insert(0, str(staged))
        import cmp4_runner as live
        import runner

        receipt_path = SCRATCH.parent / "cmp4-r2/packet/inputs.json"
        receipt_bytes = receipt_path.read_bytes()
        receipt = json.loads(receipt_bytes)
        if (hashlib.sha256(receipt_bytes).hexdigest() != runner.WEIGHT_RECEIPT_SHA
                or receipt["source"] != live.SOURCE_SHA or receipt["model_path"] != str(live.MODEL)
                or receipt["model_sha256"] != live.MODEL_SHA or receipt["template_sha256"] != live.TEMPLATE_SHA
                or receipt["model_stat"] != live.file_identity(live.MODEL)):
            raise ValueError("CMP-4 model receipt pin or current file identity mismatch")
        if not SOURCE.exists():
            subprocess.run(["git", "-C", str(ORCH), "worktree", "add", "--detach",
                            str(SOURCE), live.SOURCE_SHA], check=True)

        fixture_dir = SCRATCH / "prepared"
        fixture_dir.mkdir(mode=0o700, exist_ok=True)
        fixture = fixture_dir / "cases.json"
        if not fixture.exists():
            rng = secrets.SystemRandom()
            seeds = rng.sample(range(1, 2**31), 40)
            runner.seal(fixture, [{"label": f"archive-{index + 1:02}", "needle": secrets.token_hex(12),
                                   "seeds": seeds[2 * index:2 * index + 2]} for index in range(20)])
        shutil.copy2(fixture, staged / "cases.json")
        shutil.copy2(live.LINKAGE, staged / "verify_ggml_linkage.sh")
        live.atomic_json(staged / "schedule.json", runner.schedule(live.read_json(fixture)))
        live.atomic_json(staged / "inputs.json", {
            "source": live.SOURCE_SHA, "cmp4_weight_receipt_sha256": runner.WEIGHT_RECEIPT_SHA,
            "cmp4_harness_ref": HARNESS_REF, "cmp3_harness_ref": CMP3_REF,
            **{key: receipt[key] for key in ("model_path", "model_sha256", "model_stat",
                                             "template_sha256", "build_sha256")},
            "packet_sha256": {path.name: live.digest(path) for path in sorted(staged.iterdir()) if path.is_file()},
        })
        subprocess.run([sys.executable, "-B", str(staged / "runner.py"), "verify"], check=True)
        staged.rename(packet)
    return packet / "spec.json"


def resume_files(packet, round_number):
    base = json.loads((packet / "spec.json").read_text())
    base_id = base["id"]
    previous = base_id if round_number == 2 else f"{base_id}-r{round_number - 1}"
    row_id = f"{base_id}-r{round_number}"
    directory = packet.parent / "rounds" / row_id
    launcher = (packet / "launcher.sh").read_text().replace(f"--id {base_id} ", f"--id {row_id} ")
    launcher = launcher.replace('$R/STOP"', f'$R/STOP-r{round_number}"')
    spec = {**base, "id": row_id, "supersedes": [previous], "launcher": str(directory / "launcher.sh")}
    return directory, previous, spec, launcher


def prepare_next_round(round_number):
    if round_number < 2:
        raise ValueError("next round must be at least 2")
    packet = SCRATCH / "packet"
    subprocess.run([sys.executable, "-B", str(packet / "runner.py"), "verify"], check=True)
    directory, previous, spec, launcher = resume_files(packet, round_number)
    native = SCRATCH / "native"
    matrix = json.loads((native / "MATRIX.json").read_text())
    partial = json.loads((native / "PARTIAL.json").read_text())
    input_sha = hashlib.sha256((packet / "inputs.json").read_bytes()).hexdigest()
    if ((native / "RESULT.json").exists() or not (FLAGS / f"grants/{previous}.ended").is_file()
            or matrix["packet_sha256"] != input_sha or partial["packet_sha256"] != input_sha):
        raise ValueError("the predecessor must be ended with a partial result under the original packet")
    directory.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".resume-", dir=directory.parent) as temporary:
        staged = Path(temporary)
        (staged / "launcher.sh").write_text(launcher)
        (staged / "launcher.sh").chmod(0o755)
        (staged / "spec.json").write_text(json.dumps(spec, indent=2) + "\n")
        staged.rename(directory)
    return directory / "spec.json"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--next-round", type=int)
    options = parser.parse_args()
    if options.next_round is not None:
        print(prepare_next_round(options.next_round))
        sys.exit(0)
    try:
        spec = prepare()
    except Exception as exc:
        REPORT.write_text(json.dumps({"status": "failed", "reason": f"{type(exc).__name__}: {exc}"}, indent=2) + "\n")
        raise
    REPORT.write_text(json.dumps({"status": "sealed_offline", "spec": str(spec)}, indent=2) + "\n")
    print(spec)
