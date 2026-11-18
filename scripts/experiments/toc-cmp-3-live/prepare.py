#!/usr/bin/env python3
"""Prepare the CMP-3 live packet without hashing weights or running inference."""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CMP4 = HERE.parent / "toc-cmp-4-live"
PATCH = HERE.parent / "toc-cmp-3-contract/orchestrator.patch"
SCRATCH = Path("/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp3-live")
SOURCE = SCRATCH / "source"
ORCH = Path("/mnt/raid0/llm/epyc-orchestrator")
PATCH_SHA = "1b679a01e14e631ea58e6bcfe94f15e59195245b2309aab072d0bbfaaffaa0c3"

sys.path.insert(0, str(CMP4))
import runner as live


def prepare():
    packet = SCRATCH / "packet"
    if packet.exists():
        if not SOURCE.exists():
            prepare_source(packet / "orchestrator.patch")
        subprocess.run([sys.executable, "-B", str(packet / "cmp3_live.py"), "verify"], check=True)
        archive_inputs(packet)
        return packet / "spec.json"

    receipt_path = live.SCRATCH / "packet/inputs.json"
    receipt_bytes = receipt_path.read_bytes()
    custody = json.loads(receipt_bytes)
    if (custody["source"] != live.SOURCE_SHA or custody["model_path"] != str(live.MODEL)
            or custody["model_sha256"] != live.MODEL_SHA or custody["template_sha256"] != live.TEMPLATE_SHA):
        raise ValueError("CMP-4 weight receipt pin mismatch")
    SCRATCH.mkdir(parents=True, exist_ok=True)
    staged_diff = prepare_source(PATCH)

    with tempfile.TemporaryDirectory(prefix="packet-", dir=SCRATCH) as temporary:
        staged_packet = Path(temporary) / "packet"
        staged_packet.mkdir()
        for name in ("cmp3_live.py", "trial.py", "spec.json", "launcher.sh", "cases.json", "README.md"):
            shutil.copy2(HERE / name, staged_packet)
        for name in ("graph_trial.py", "analysis.py"):
            shutil.copy2(CMP4 / name, staged_packet)
        shutil.copy2(CMP4 / "runner.py", staged_packet / "cmp4_runner.py")
        shutil.copy2(PATCH, staged_packet / "orchestrator.patch")
        shutil.copy2(live.LINKAGE, staged_packet / "verify_ggml_linkage.sh")
        live.atomic_json(staged_packet / "inputs.json", {
            "source": live.SOURCE_SHA,
            "source_diff_sha256": staged_diff,
            "candidate_patch_sha256": PATCH_SHA,
            "cmp4_weight_receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
            **{k: custody[k] for k in ("model_path", "model_sha256", "model_stat", "template_sha256", "build_sha256")},
            "packet_sha256": {p.name: live.digest(p) for p in sorted(staged_packet.iterdir())},
        })
        subprocess.run([sys.executable, "-B", str(staged_packet / "cmp3_live.py"), "verify"], check=True)
        archive_inputs(staged_packet)
        staged_packet.rename(packet)
    return packet / "spec.json"


def prepare_source(patch):
    if live.digest(patch) != PATCH_SHA:
        raise ValueError("CMP-3 candidate patch pin mismatch")
    if not SOURCE.exists():
        git_orch = ["git", "-C", str(ORCH), "worktree"]
        worktrees = subprocess.check_output([*git_orch, "list", "--porcelain"], text=True).splitlines()
        if f"worktree {SOURCE}" in worktrees:
            subprocess.run([*git_orch, "remove", "--force", str(SOURCE)], check=True)
        subprocess.run([*git_orch, "add", "--detach", str(SOURCE), live.SOURCE_SHA], check=True)

    def git(*args):
        return subprocess.check_output(["git", "-C", str(SOURCE), *args])

    if git("rev-parse", "HEAD").decode().strip() != live.SOURCE_SHA:
        raise ValueError("unexpected detached candidate base")
    if not git("status", "--porcelain"):
        git("apply", "--check", "--index", str(patch))
        git("apply", "--index", str(patch))
    git("apply", "--check", "--index", "--reverse", str(patch))
    staged_diff = hashlib.sha256(git("diff", "--cached", "--binary")).hexdigest()
    if staged_diff != PATCH_SHA or git("diff", "--name-only") or git("ls-files", "--others", "--exclude-standard"):
        raise ValueError("candidate contains changes outside the pinned patch")
    return staged_diff


def archive_inputs(packet):
    archive = SCRATCH / "native/prepared"
    archive.mkdir(parents=True, exist_ok=True)
    inputs = {name: (packet / name).read_bytes() for name in ("inputs.json", "orchestrator.patch", "cases.json")}
    for name, expected in inputs.items():
        path = archive / name
        if path.exists() and path.read_bytes() != expected:
            raise ValueError(f"prepared input archive conflicts: {path}")
    with tempfile.TemporaryDirectory(prefix="archive-", dir=archive) as temporary:
        for name, expected in inputs.items():
            staged, path = Path(temporary) / name, archive / name
            staged.write_bytes(expected)
            try:
                path.hardlink_to(staged)
            except FileExistsError:
                if path.read_bytes() != expected:
                    raise ValueError(f"prepared input archive conflicts: {path}") from None


if __name__ == "__main__":
    print(prepare())
