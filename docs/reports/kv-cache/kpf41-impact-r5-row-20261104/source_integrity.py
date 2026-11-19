"""Fail-closed source identity checks for the KPF-41 impact row."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

D = Path(__file__).resolve().parent
TREE = Path("/mnt/raid0/llm/tmp/kvfork/kpf41-impact-r5-20261104/source")


def run(args):
    p = subprocess.run(args, cwd=TREE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode:
        raise RuntimeError(f"source integrity command failed ({p.returncode}): {args!r}")
    return p.stdout.decode().strip()


def verify():
    ident = json.loads((D / "identity.json").read_text())
    expected_runtime = os.environ.get("KPF41_RUNTIME_SHA256")
    if not expected_runtime:
        raise RuntimeError("launcher did not provide sealed runtime digest")
    runtime_path = D / "runtime.json"
    if hashlib.sha256(runtime_path.read_bytes()).hexdigest() != expected_runtime:
        raise RuntimeError("runtime manifest digest mismatch")
    runtime = json.loads(runtime_path.read_text())
    for rel, expected in runtime["sealed_files"].items():
        actual = hashlib.sha256((D / rel).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"runtime sealed file digest mismatch: {rel}")
    for rel, entry in runtime["external_files"].items():
        actual = hashlib.sha256(Path(entry["path"]).read_bytes()).hexdigest()
        if actual != entry["sha256"]:
            raise RuntimeError(f"runtime helper digest mismatch: {rel}")
    source_wrapper = hashlib.sha256((TREE / "scripts/gitnexus-analyze.sh").read_bytes()).hexdigest()
    if source_wrapper != runtime["source_analyzer_wrapper_sha256"]:
        raise RuntimeError("source analyzer wrapper digest mismatch")
    if run(["git", "rev-parse", "HEAD"]) != ident["head"]:
        raise RuntimeError("source HEAD drift")
    if run(["git", "rev-parse", "HEAD^{tree}"]) != ident["tree"]:
        raise RuntimeError("source tree drift")
    detached = subprocess.run(["git", "symbolic-ref", "-q", "HEAD"], cwd=TREE,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if ident["detached"] is not True or detached.returncode != 1:
        raise RuntimeError("source worktree must stay detached")
    if run(["git", "diff", "--name-only", "HEAD"]):
        raise RuntimeError("tracked source changes present")
    untracked = subprocess.run(["git", "ls-files", "--others", "--exclude-standard", "-z"],
                               cwd=TREE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if untracked.returncode:
        raise RuntimeError("untracked-file inventory failed")
    if any(untracked.stdout.split(b"\0")):
        raise RuntimeError("untracked source files present")
    files = run(["git", "ls-files", "-z"]).split("\0")
    files = [p for p in files if p]
    if len(files) != ident["tracked_files"]:
        raise RuntimeError("tracked-file coverage changed")
    flags = run(["git", "ls-files", "-v"]).splitlines()
    if len(flags) != ident["tracked_files"] or any(not x.startswith("H ") for x in flags):
        raise RuntimeError("assume-unchanged or skip-worktree index flags present")
    for rel, expected in ident["sha256"].items():
        actual = hashlib.sha256((TREE / rel).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"source digest mismatch: {rel}")
    for rel, expected in ident["packet_sha256"].items():
        actual = hashlib.sha256((D / rel).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"packet digest mismatch: {rel}")
    return ident
