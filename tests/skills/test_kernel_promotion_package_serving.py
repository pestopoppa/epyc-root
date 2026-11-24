"""package.sh must carry the champion serving config (PROMOTION-REGISTRY-SERVING-1).

`--check` fails when the serving-config artifact is missing (or changed since the package recorded it),
passes when it is present; assembling emits the registry diff and the scratch dry-run result into the
package. The registry logic lives in the orchestrator, so these tests point EPYC_ORCH at a stub that
returns canned sections: they pin package.sh's contract, not the orchestrator's.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml

SKILL = Path(__file__).resolve().parents[2] / ".claude" / "skills" / "kernel-promotion"
PACKAGE_SH = SKILL / "scripts" / "package.sh"
GATES = yaml.safe_load((SKILL / "promotion_gates.yaml").read_text())
REQUIRED = sorted(k for k, v in GATES["gates"].items() if isinstance(v, dict) and v.get("required"))
STORE = Path("/mnt/raid0/llm/kernels/production")
#: the REAL artifact (CHAMPION-SERVING-CONFIG-1); fixtures are copies of its shape, not a second schema
REAL_ARTIFACT = SKILL.parents[2] / "docs/reference/kernel-manifests/serving-configs/C22.serving-config.json"

STUB = textwrap.dedent('''\
    import argparse, hashlib, json, os, sys
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd"); ap.add_argument("--config"); ap.add_argument("--out")
    ap.add_argument("--master"); ap.add_argument("--no-dry-run", action="store_true")
    ap.add_argument("--validator", required=True)  # package.sh must hand over the root validator
    a = ap.parse_args()
    assert a.validator.endswith("scripts/champion/serving_config/validate_serving_config.py")
    sha = hashlib.sha256(open(a.config, "rb").read()).hexdigest()
    json.dump({
        "serving_config": {"path": a.config, "sha256": sha, "champion": "fixture"},
        "registry_diff": {"schema": "epyc.registry_serving_diff.v1", "ops": [{"op": "set"}],
                          "serving_config_sha256": sha},
        "registry_dry_run": ({"status": "skipped"} if a.no_dry_run
                             else {"status": os.environ.get("STUB_DRY", "pass"),
                                   "host_state_carve_out": {"excluded_steps": ["runtime_attestation"],
                                                            "failures_excluded": ["runtime_attestation"]}}),
    }, open(a.out, "w"))
''')


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _run(args: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    full = {k: v for k, v in os.environ.items() if k not in ("EPYC_ORCH", "EPYC_ORCH_PY")}
    full.update(env or {})
    return subprocess.run(["bash", str(PACKAGE_SH), *args], capture_output=True, text=True, env=full)


@pytest.fixture()
def artifact(tmp_path: Path) -> Path:
    p = tmp_path / "fixture.serving-config.json"
    p.write_text(REAL_ARTIFACT.read_text())
    return p


def _package(artifact: Path | None, **over) -> dict:
    pkg = {
        "schema": "epyc.kernel_promotion_package.v1",
        "candidate": {"commit": "abc"},
        "incumbent": {"version": "v10"},
        "store": {"cpu": {"resolves_to": "/x"}},
        "scope": {"derived_by": "scope.sh"},
        "gates": {g: {"status": "pass"} for g in REQUIRED},
        "rollback": {"regeneration_command": "stack_change_pipeline.py update"},
    }
    if artifact is not None:
        sha = _sha(artifact)
        pkg["serving_config"] = {"path": str(artifact), "sha256": sha, "champion": "fixture"}
        pkg["registry_diff"] = {"schema": "epyc.registry_serving_diff.v1", "ops": [], "serving_config_sha256": sha}
        pkg["registry_dry_run"] = {"status": "pass",
                                   "host_state_carve_out": {"excluded_steps": ["runtime_attestation"],
                                                            "failures_excluded": []}}
    pkg.update(over)
    return pkg


def _check(tmp_path: Path, pkg: dict) -> subprocess.CompletedProcess:
    f = tmp_path / "pkg.json"
    f.write_text(json.dumps(pkg))
    return _run(["--check", str(f)])


def test_check_passes_when_serving_config_present(tmp_path, artifact):
    r = _check(tmp_path, _package(artifact))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PACKAGE COMPLETE" in r.stdout


def test_check_fails_when_serving_config_section_missing(tmp_path):
    r = _check(tmp_path, _package(None))
    assert r.returncode == 1
    assert "serving-config artifact" in r.stdout and "incomplete" in r.stdout
    assert "registry_diff" in r.stdout and "registry_dry_run" in r.stdout


def test_check_fails_when_artifact_file_is_missing(tmp_path, artifact):
    pkg = _package(artifact)
    artifact.unlink()
    r = _check(tmp_path, pkg)
    assert r.returncode == 1 and "does not exist" in r.stdout


def test_check_fails_when_artifact_changed_after_assembly(tmp_path, artifact):
    pkg = _package(artifact)
    artifact.write_text(artifact.read_text() + " ")
    r = _check(tmp_path, pkg)
    assert r.returncode == 1 and "changed since the package recorded it" in r.stdout


def test_check_fails_when_the_artifact_does_not_validate(tmp_path, artifact):
    doc = json.loads(artifact.read_text())
    doc["servers"][0]["optimal"]["provenance"].pop("result_sha256")
    artifact.write_text(json.dumps(doc))
    r = _check(tmp_path, _package(artifact))
    assert r.returncode == 1 and "fails validate_serving_config.py" in r.stdout


def test_check_fails_without_an_explicit_host_state_carve_out_record(tmp_path, artifact):
    pkg = _package(artifact, registry_dry_run={"status": "pass"})
    r = _check(tmp_path, pkg)
    assert r.returncode == 1 and "host_state_carve_out" in r.stdout


def test_check_prints_the_carve_out_and_skipped_pending(tmp_path, artifact):
    pkg = _package(artifact)
    pkg["registry_dry_run"]["host_state_carve_out"]["failures_excluded"] = ["runtime_attestation"]
    r = _check(tmp_path, pkg)
    assert r.returncode == 0
    assert "CARVE-OUT" in r.stdout and "runtime_attestation" in r.stdout
    assert "pending entr" in r.stdout


def test_check_fails_when_diff_not_derived_from_the_artifact(tmp_path, artifact):
    pkg = _package(artifact)
    pkg["registry_diff"]["serving_config_sha256"] = "0" * 64
    r = _check(tmp_path, pkg)
    assert r.returncode == 1 and "not derived from" in r.stdout


def test_check_fails_when_dry_run_failed(tmp_path, artifact):
    r = _check(tmp_path, _package(artifact, registry_dry_run={"status": "fail", "error": "boom"}))
    assert r.returncode == 1 and "registry_dry_run status='fail'" in r.stdout


def test_check_resolves_a_relative_artifact_path_against_the_repo_root(tmp_path):
    root = SKILL.parents[2]
    rel = Path("docs/reference/kernel-manifests/serving-configs/__test_fixture__.serving-config.json")
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(REAL_ARTIFACT.read_text())
    try:
        pkg = _package(target)
        pkg["serving_config"]["path"] = str(rel)
        r = _check(tmp_path, pkg)
        assert r.returncode == 0, r.stdout
    finally:
        target.unlink()


# ----------------------------------------------------------------------------- assemble


@pytest.fixture()
def stub_orch(tmp_path: Path) -> Path:
    d = tmp_path / "orch" / "scripts" / "registry"
    d.mkdir(parents=True)
    (d / "serving_config_registry.py").write_text(STUB)
    return tmp_path / "orch"


@pytest.fixture()
def evidence(tmp_path: Path) -> Path:
    d = tmp_path / "evidence"
    d.mkdir()
    for g in REQUIRED:
        (d / f"{g}.json").write_text(json.dumps({"status": "pass"}))
    return d


needs_store = pytest.mark.skipif(not (STORE / "cpu").is_symlink(), reason="kernel store not on this host")


@needs_store
def test_assemble_emits_registry_diff_and_dry_run_into_the_package(tmp_path, artifact, stub_orch, evidence):
    out = tmp_path / "out.json"
    r = _run(["--candidate", "abc", "--out", str(out), "--evidence", str(evidence),
              "--serving-config", str(artifact)],
             {"EPYC_ORCH": str(stub_orch), "EPYC_ORCH_PY": "python3"})
    assert r.returncode == 0, r.stdout + r.stderr
    pkg = json.loads(out.read_text())
    assert pkg["serving_config"]["sha256"] == _sha(artifact)
    assert pkg["registry_diff"]["schema"] == "epyc.registry_serving_diff.v1"
    assert pkg["registry_dry_run"]["status"] == "pass"
    assert _run(["--check", str(out)]).returncode == 0  # the emitted package re-validates


@needs_store
def test_assemble_without_serving_config_is_incomplete(tmp_path, evidence):
    out = tmp_path / "out.json"
    r = _run(["--candidate", "abc", "--out", str(out), "--evidence", str(evidence)])
    assert r.returncode == 1 and "serving-config artifact" in r.stdout


@needs_store
def test_assemble_with_a_missing_artifact_is_incomplete(tmp_path, evidence):
    out = tmp_path / "out.json"
    r = _run(["--candidate", "abc", "--out", str(out), "--evidence", str(evidence),
              "--serving-config", str(tmp_path / "absent.json")])
    assert r.returncode == 1 and "does not exist" in r.stdout


@needs_store
def test_assemble_with_a_failing_dry_run_is_incomplete(tmp_path, artifact, stub_orch, evidence):
    r = _run(["--candidate", "abc", "--out", str(tmp_path / "o.json"), "--evidence", str(evidence),
              "--serving-config", str(artifact)],
             {"EPYC_ORCH": str(stub_orch), "EPYC_ORCH_PY": "python3", "STUB_DRY": "fail"})
    assert r.returncode == 1 and "registry_dry_run status='fail'" in r.stdout


@needs_store
def test_assemble_no_dry_run_is_incomplete(tmp_path, artifact, stub_orch, evidence):
    r = _run(["--candidate", "abc", "--out", str(tmp_path / "o.json"), "--evidence", str(evidence),
              "--serving-config", str(artifact), "--no-dry-run"],
             {"EPYC_ORCH": str(stub_orch), "EPYC_ORCH_PY": "python3"})
    assert r.returncode == 1 and "registry_dry_run status='skipped'" in r.stdout
