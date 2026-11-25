"""package.sh: EPYC_ORCH defaults to a fresh read-only extract of orchestrator origin/main, not the live clone
(defect 2 residual, final-gate audit 2026-11-24). A throwaway git remote + clone stands in for the orchestrator."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from test_kernel_promotion_package_serving import (  # noqa: E402  (same directory, rootdir-relative import)
    PACKAGE_SH, STORE, STUB, REAL_ARTIFACT, REQUIRED,
)

needs_store = pytest.mark.skipif(not (STORE / "cpu").is_symlink(), reason="kernel store not on this host")

MARK = '\nimport sys\nprint("EXTRACT_SOURCE", __file__, file=sys.stderr)\nopen(os.environ["SEEN_FILE"], "w").write(__file__)\n'


def _git(cwd: Path, *a: str) -> str:
    return subprocess.run(["git", "-C", str(cwd), *a], check=True, capture_output=True, text=True,
                          env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}).stdout.strip()


@pytest.fixture()
def live_clone(tmp_path: Path) -> Path:
    bare = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    clone = tmp_path / "live"
    subprocess.run(["git", "clone", "-q", str(bare), str(clone)], check=True, capture_output=True)
    d = clone / "scripts" / "registry"
    d.mkdir(parents=True)
    (d / "serving_config_registry.py").write_text(STUB + MARK)
    _git(clone, "add", "-A")
    _git(clone, "commit", "-q", "-m", "stub")
    _git(clone, "push", "-q", "origin", "HEAD:main")
    # the LIVE working tree drifts from origin/main: its copy of the script is poisoned
    (d / "serving_config_registry.py").write_text("raise SystemExit('live working tree must not be used')\n")
    return clone


@needs_store
def test_default_orch_is_an_origin_main_extract_not_the_live_working_tree(tmp_path, live_clone):
    artifact = tmp_path / "fixture.serving-config.json"
    artifact.write_text(REAL_ARTIFACT.read_text())
    evid = tmp_path / "evidence"
    evid.mkdir()
    for g in REQUIRED:
        (evid / f"{g}.json").write_text(json.dumps({"status": "pass"}))
    seen = tmp_path / "seen.txt"
    env = {k: v for k, v in os.environ.items() if k not in ("EPYC_ORCH", "EPYC_ORCH_PY")}
    env.update({"EPYC_ORCH_LIVE": str(live_clone), "EPYC_ORCH_PY": "python3", "SEEN_FILE": str(seen),
                "TMPDIR": str(tmp_path)})
    out = tmp_path / "out.json"
    r = subprocess.run(["bash", str(PACKAGE_SH), "--candidate", "abc", "--out", str(out), "--evidence", str(evid),
                        "--serving-config", str(artifact)], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    sha = _git(live_clone, "rev-parse", "origin/main")
    assert f"origin/main {sha}" in r.stderr                                  # the commit used is printed
    used = Path(seen.read_text())
    assert used.parent.parent.parent.name.startswith("package-orch-") and not str(used).startswith(str(live_clone))
    assert not used.parent.parent.parent.exists()                           # removed on exit
    assert json.loads(out.read_text())["serving_config"]["sha256"]


@needs_store
def test_epyc_orch_override_is_used_as_given(tmp_path, live_clone):
    artifact = tmp_path / "fixture.serving-config.json"
    artifact.write_text(REAL_ARTIFACT.read_text())
    evid = tmp_path / "evidence"
    evid.mkdir()
    for g in REQUIRED:
        (evid / f"{g}.json").write_text(json.dumps({"status": "pass"}))
    orch = tmp_path / "override" / "scripts" / "registry"
    orch.mkdir(parents=True)
    (orch / "serving_config_registry.py").write_text(STUB)
    env = {k: v for k, v in os.environ.items() if k not in ("EPYC_ORCH", "EPYC_ORCH_PY")}
    env.update({"EPYC_ORCH": str(tmp_path / "override"), "EPYC_ORCH_PY": "python3", "EPYC_ORCH_LIVE": str(live_clone)})
    r = subprocess.run(["bash", str(PACKAGE_SH), "--candidate", "abc", "--out", str(tmp_path / "o.json"),
                        "--evidence", str(evid), "--serving-config", str(artifact)],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "fresh read-only extract" not in r.stderr
