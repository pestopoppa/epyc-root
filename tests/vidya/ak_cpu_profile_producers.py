"""Real research CPU-profile producers, one per capture version the strict reader accepts.

Each producer is the research tree's own fixture mode (synthetic perf, tiny HTTP server; no
inference): ``test_cpu_profile_runtime.fixture`` for the PROFILE_VERIFIED bundle and
``test_loop_cpu_profile.produce`` for the direct loop record. Pinned commits are read from the
configured research clone with ``git archive`` (read-only) into a pytest temp dir, so each
version is produced by the exact code its reader pins; ``live`` is the configured tree itself,
the conformance tripwire for the current research main. Each producer runs in its own
subprocess, so two trees never share an imported ``autokernel`` package.

The source-closure digests include the interpreter identity; they were pinned under
/usr/bin/python3.13, the interpreter this suite runs under on the EPYC host.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

from adapters import autokernel_profile as profile  # noqa: E402

# name -> (research commit or None for the configured live tree, version, pinned source digest)
PRODUCERS = {
    # Last legacy closure the reader pins (reproduces MATCHED_CPU_SOURCE_DIGEST).
    "legacy@83334d892": ("83334d89201889baa7dc40a35dbc0fc1538c53a6",
                         profile.LEGACY_CAPTURE, profile.MATCHED_CPU_SOURCE_DIGEST),
    # First sampled-CPU producer ("Capture sampled CPU topology ...", 2026-09-17).
    "sampled-cpu@07333b884": ("07333b88472fa2190bae23e93bbd4c3124674710",
                              profile.SAMPLED_CPU_CAPTURE,
                              profile.SAMPLED_CPU_SOURCE_DIGEST_07333B884),
    # Research main when the v2 reader was written (2026-10-22).
    "sampled-cpu@b93017dc9": ("b93017dc980438a837ad7fac0e8612760dc1ff0e",
                              profile.SAMPLED_CPU_CAPTURE,
                              profile.SAMPLED_CPU_SOURCE_DIGEST_MAIN_B93017DC9),
    # The configured research tree as it is now.
    "sampled-cpu@live": (None, profile.SAMPLED_CPU_CAPTURE, None),
}
_TREES: dict[str, Path] = {}

_BUNDLE = """
import json, sys
from pathlib import Path
from autokernel.loop.test_cpu_profile_runtime import _start, fixture
materialized, registry, _target, config, _events, _request = fixture(Path(sys.argv[1]))
controller, runtime = _start(materialized, registry)
try:
    runtime.tick()
    entries = controller._journal.read_all()
    terminal = next(item.envelope() for item in entries
        if item.kind == "WORKER_LIFECYCLE" and item.payload.get("event") == "WORKER_RESULT_ACCEPTED")
    published = next(item.envelope() for item in entries
        if item.kind == "ACTOR_PREPARATION" and item.payload.get("event") == "PROFILE_VERIFIED")
finally:
    runtime.close()
    controller.close()
print(json.dumps({"native": {"terminal": terminal, "profile": published},
                  "storage": str(config["storage"])}))
"""
_LOOP = """
import json, sys
from pathlib import Path
from autokernel.loop.test_loop_cpu_profile import produce
result, _, _ = produce(Path(sys.argv[1]))
print(json.dumps(result))
"""


def research_root() -> Path:
    configured = os.environ.get("EPYC_RESEARCH_ROOT")
    if not configured:
        pytest.skip("set EPYC_RESEARCH_ROOT for actual CPU profile producer conformance")
    return Path(configured).resolve()


def producer_tree(name: str, tmp_path_factory) -> Path:
    """The research tree for one producer; pinned commits are extracted once per session."""
    research = research_root()
    commit = PRODUCERS[name][0]
    if commit is None:
        return research
    if commit not in _TREES:
        dest = tmp_path_factory.mktemp("research-" + commit[:9])
        archive = subprocess.Popen(["git", "-C", str(research), "archive", commit, "scripts"],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            with tarfile.open(fileobj=archive.stdout, mode="r|") as stream:
                stream.extractall(dest, filter="data")
        except tarfile.ReadError:
            pass
        _, stderr = archive.communicate(timeout=120)
        if archive.returncode != 0:
            pytest.skip(f"research commit {commit[:9]} is not in {research}: {stderr[:200]!r}")
        _TREES[commit] = dest
    return _TREES[commit]


def _run(tree: Path, code: str, out: Path) -> dict:
    completed = subprocess.run([sys.executable, "-c", code, str(out)], cwd=tree,
        env={**os.environ, "PYTHONPATH": str(tree / "scripts" / "kernel_rnd")},
        capture_output=True, text=True, timeout=120, check=False)
    assert completed.returncode == 0, completed.stderr[-4000:]
    return json.loads(completed.stdout.strip().splitlines()[-1])


def produce_bundle(name: str, tmp_path_factory) -> tuple[dict, Path]:
    """One PROFILE_VERIFIED publication + accepted terminal from the named real producer."""
    tree = producer_tree(name, tmp_path_factory)
    result = _run(tree, _BUNDLE, tmp_path_factory.mktemp("cpu-profile-" + name.split("@")[1]))
    return result["native"], Path(result["storage"])


def produce_loop(name: str, tmp_path_factory) -> dict:
    """One direct original-request loop record from the named real producer."""
    tree = producer_tree(name, tmp_path_factory)
    return _run(tree, _LOOP, tmp_path_factory.mktemp("direct-cpu-profile-" + name.split("@")[1]))
