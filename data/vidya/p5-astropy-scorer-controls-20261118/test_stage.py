"""Software controls for the exact staged scorer and custody paths, with Docker stubbed."""

import ast
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import ModuleType, SimpleNamespace

import pytest

PACKET = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


STAGE = load("astropy_stage", PACKET / "stage.py")
HISTORICAL = STAGE.ROOT / "docs/reports/p5-gold-controls-20261104"


def iso(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat()


@pytest.fixture
def build(tmp_path):
    root = tmp_path / "builder"
    attempt = root / "official" / "build-test"
    attempt.mkdir(parents=True)
    manifest, launcher = b"build sources\n", b"build launcher\n"
    (root / "SOURCE.sha256").write_bytes(manifest)
    (root / "launch.sh").write_bytes(launcher)
    now = int(time.time())
    grant = f"regions=0-23 start={iso(now-1)} end={iso(now+299)} holds=q0\n".encode()
    log = b"synthetic successful builder log\n"
    (attempt / "rowflow.grant").write_bytes(grant)
    (attempt / "build.log").write_bytes(log)
    pins = json.loads((STAGE.SOURCE / "pins.json").read_bytes())
    receipt = {
        "schema": "epyc.p5.image-build-capture.v1", "id": STAGE.BUILD_ROW,
        "mode": "official", "status": "COMPLETE", "runner_rc": 0, "base_ref": STAGE.BASE_REF,
        "base_image_id": pins["base_image_id"], "dockerfile_sha256": pins["dockerfile_sha256"],
        "context_sha256": pins["build_context_seal_sha256"], "image_id": "sha256:" + "1" * 64,
        "build_log": str(attempt / "build.log"), "build_log_sha256": STAGE.sha(log),
        "grant_sha256": STAGE.sha(grant), "started_utc": iso(now), "completion_utc": iso(now+1),
        "actual_cpus": "0-23", "build_cpus": "0,1,2,3", "grant_start_epoch": now-1,
        "deadline_epoch": now+209, "launcher_sha256": STAGE.sha(launcher),
        "source_manifest_sha256": STAGE.sha(manifest),
    }
    (attempt / "image.iid").write_text(receipt["image_id"] + "\n")
    path = root / "official" / "RESULT.json"
    path.write_text(json.dumps(receipt))
    os.link(path, attempt / "receipt.json")
    return path, receipt


@pytest.fixture
def staged(tmp_path, build, monkeypatch):
    monkeypatch.setattr(STAGE, "SCRATCH_ROOT", tmp_path)
    dest = tmp_path / "native"
    STAGE.stage(dest, build[0])
    return dest


def test_stage_seals_sources_and_provenance(staged, build):
    assert (staged / "job.py").read_bytes() == (STAGE.SOURCE / "job.py").read_bytes()
    assert (staged / "historical-complete.py").read_bytes() == (STAGE.SOURCE / "complete.py").read_bytes()
    assert (staged / "build-receipt.json").read_bytes() == build[0].read_bytes()
    assert (staged / "build.grant").read_bytes() == Path(build[1]["build_log"]).with_name("rowflow.grant").read_bytes()
    assert json.loads((staged / "pins.json").read_bytes())["image_id"] == build[1]["image_id"]
    subprocess.run(["sha256sum", "-c", "--status", "SOURCE.sha256"], cwd=staged, check=True)
    for shell in ("launch.sh", "preflight.sh"):
        subprocess.run(["bash", "-n", str(staged / shell)], check=True)
    subprocess.run([sys.executable, "-B", str(staged / "run-controls.py")], cwd=staged, check=True)
    with pytest.raises(ValueError, match="exists"):
        STAGE.stage(staged, build[0])


@pytest.mark.parametrize("defect", ["smoke", "image", "base", "context", "log", "grant", "time", "source", "receipt", "iid"])
def test_build_receipt_refusals(tmp_path, build, monkeypatch, defect):
    path, receipt = build
    if defect == "smoke":
        receipt["mode"] = "smoke"
    elif defect == "image":
        receipt["image_id"] = receipt["base_image_id"]
    elif defect == "base":
        receipt["base_ref"] += "-different"
    elif defect == "context":
        receipt["context_sha256"] = "2" * 64
    elif defect == "log":
        Path(receipt["build_log"]).write_text("altered")
    elif defect == "grant":
        Path(receipt["build_log"]).with_name("rowflow.grant").write_text("altered")
    elif defect == "time":
        receipt["completion_utc"] = iso(receipt["deadline_epoch"])
    elif defect == "iid":
        Path(receipt["build_log"]).with_name("image.iid").write_text("changed")
    elif defect == "source":
        (path.parent.parent / "SOURCE.sha256").write_text("altered")
    if defect == "receipt":
        path.unlink()
    path.write_text(json.dumps(receipt))
    monkeypatch.setattr(STAGE, "SCRATCH_ROOT", tmp_path)
    with pytest.raises(ValueError):
        STAGE.stage(tmp_path / "native", path)
    assert not (tmp_path / "native").exists()


def test_source_anchor_drift_refused():
    original = (STAGE.SOURCE / "job.py").read_text()
    with pytest.raises(ValueError, match="anchor changed"):
        STAGE.native_scorer(original.replace("output=D/'RESULT.json'", "output=D/'different.json'"))


def capture(staged, monkeypatch, defect, smoke):
    validator = load("complete", staged / "complete.py")
    monkeypatch.setitem(sys.modules, "complete", validator)
    custody = load("astropy_custody", staged / "custody.py")
    now = int(time.time())
    grants = staged / "grants"
    grants.mkdir()
    fields = f"kind=rowflow-dryrun id={STAGE.ROW} " if smoke else ""
    grant = grants / (STAGE.ROW + ".grant")
    grant.write_text(fields + f"regions=0-3 start={iso(now-2)} end={iso(now+400)} holds=q0\n")
    env = {
        "FILLER_ID": STAGE.ROW, "FILLER_NEEDGPU": "0", "FILLER_CPUS": "0-3",
        "FILLER_DRYRUN": "1" if smoke else "0", "FILLER_SMOKE": "1" if smoke else "0",
        "FILLER_GRANTS_DIR": str(grants), "FILLER_DRYRUN_DIR": str(staged),
        "FILLER_DRYRUN_RESULT_PATH": str(staged / "publisher" / "RESULT.json"),
        "FILLER_STOPFILE": str(staged / "STOP"), "FILLER_DEADLINE": str(now+310),
        "P5_NATIVE_RESULT": "", "P5_INSTRUMENT_DEADLINE": "", "TMPDIR": "",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    if defect == "stop":
        (staged / "STOP").touch()
    actual = {0, 1} if defect == "affinity" else set(range(4))
    monkeypatch.setattr(custody.os, "sched_getaffinity", lambda _pid: actual)
    monkeypatch.setattr(custody.signal, "signal", lambda *_: None)
    monkeypatch.setattr(custody.subprocess, "run", lambda *_, **__: None)

    def scorer(*_, **__):
        parsed = ast.parse((staged / "scorer.py").read_text())
        loop = next(node for node in reversed(parsed.body) if isinstance(node, ast.Try))
        pins = json.loads((staged / "pins.json").read_bytes())
        case = json.loads((staged / "case.json").read_bytes())
        original = json.loads((HISTORICAL / "result.json").read_bytes())
        result = {key: original[key] for key in ("instance_id", "schema", "case_sha256", "wheel_manifest_sha256",
                                                 "script_binding", "checkout_proofs")}
        result.update(arms={}, arm_attempts={}, arm_container_ids={}, image_id=pins["image_id"],
                      image_build_log_sha256=pins["image_build_log_sha256"],
                      producer_source_manifest_sha256=custody.sha(staged / "SOURCE.sha256"),
                      producer_launcher_sha256=custody.sha(staged / "launch.sh"))
        result["script_binding"]["derived_image_id"] = pins["image_id"]
        owned = []
        statuses = {}

        def run(_spec, pred, _remove, _force, _client, run_id, *, timeout):
            arm = pred["model_name_or_path"]
            ident = list(result["checkout_proofs"])[len(owned)]
            result["arm_container_ids"][arm] = ident
            owned.append(SimpleNamespace(id=ident))
            fixture = "gold" if defect == "wrong-negative" and arm == "negative" else arm
            source = HISTORICAL / fixture
            folder = staged / "logs/run_evaluation" / run_id / arm / case["instance_id"]
            folder.mkdir(parents=True)
            for name in ("report.json", "test_output.txt"):
                (folder / name).write_bytes((source / name).read_bytes())
            statuses.clear()
            for field in validator.GROUPS:
                statuses.update(original["arms"][fixture][field])
            if defect == "missing-selector" and arm == "gold":
                statuses.pop(json.loads(case["FAIL_TO_PASS"])[0])
            if defect == "raw-mismatch" and arm == "gold":
                (folder / "test_output.txt").write_text("changed raw log")
            return {"completed": True}

        def cleanup():
            if defect == "cleanup":
                raise RuntimeError("cleanup refused")

        ns = dict(D=staged, Path=Path, os=custody.os, json=json, case=case,
                  arms=[("negative", case["negative_patch"]), ("gold", case["patch"])],
                  spec=None, client=None, result=result, deadline=now+270, time=time, owned=owned,
                  ev=SimpleNamespace(run_instance=run), get_logs_eval=lambda *_: (statuses.copy(), True),
                  cleanup=cleanup, diagnostic=validator.diagnostic)
        exec(compile(ast.Module(body=[loop], type_ignores=[]), "staged-scorer-loop", "exec"), ns)

    monkeypatch.setattr(custody.runpy, "run_path", scorer)
    rc = custody.run()
    path = custody.result_path()
    attempt, = path.parent.glob("attempt-*")
    return rc, custody, path, attempt, json.loads((attempt / "terminal.json").read_bytes())


@pytest.mark.parametrize(("defect", "smoke", "decision"), [(None, True, "PASS"), ("wrong-negative", False, "FAIL")])
def test_completed_diagnostic_and_tamper(staged, monkeypatch, defect, smoke, decision):
    rc, custody, path, attempt, terminal = capture(staged, monkeypatch, defect, smoke)
    assert rc == custody.complete() == 0 and terminal["status"] == "COMPLETE"
    assert terminal["decision"] == decision
    assert path.parent.name == ("publisher" if smoke else "official")
    assert terminal["grant"]["actual_cpus"] == [0, 1, 2, 3]
    raw = json.loads((attempt / "native.json").read_bytes())
    assert len(raw["arms"]["gold"]["PASS_TO_PASS"]) == 13
    assert len(raw["arms"]["negative"]["FAIL_TO_PASS"]) == 2
    (attempt / "negative-test_output.txt").write_text("changed raw artifact")
    with pytest.raises(ValueError, match="binding"):
        custody.complete()


@pytest.mark.parametrize("defect", ["missing-selector", "raw-mismatch", "cleanup"])
def test_failed_acquisition_retains_unknown(staged, monkeypatch, defect):
    rc, _, path, attempt, terminal = capture(staged, monkeypatch, defect, False)
    assert rc == 1 and not path.exists()
    assert terminal["status"] == "UNKNOWN" and terminal["completion_utc"]
    assert terminal.get("error") or terminal.get("capture_error")
    assert (attempt / "rowflow.grant").is_file()
    assert (attempt / "gold-test_output.txt").is_file()



@pytest.mark.parametrize(("defect", "expected_rc"), [("stop", 75), ("affinity", 1)])
def test_pre_arm_refusal_retains_original_grant(staged, monkeypatch, defect, expected_rc):
    rc, _, path, attempt, terminal = capture(staged, monkeypatch, defect, False)
    assert rc == expected_rc and not path.exists()
    assert terminal["status"] == "UNKNOWN" and terminal["completion_utc"]
    assert terminal["error"]
    assert (attempt / "rowflow.grant").is_file()
    assert not (attempt / "native.json").exists()
