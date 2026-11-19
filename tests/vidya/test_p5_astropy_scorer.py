"""Original Astropy evidence, independent rederivation and exact context controls."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/vidya"))
from adapters import p5_astropy_scorer as adapter
from canary import p5_astropy_task_context as canary
from claim_tuple import ProjectionError, grade

PACKET = ROOT / "data/vidya/p5-astropy-native-20261118"
RESULT = "official/RESULT.json"


@pytest.fixture
def original_available():
    if not ((attempt(PACKET) / "native.json").is_file() or (adapter.PRIVATE_ROOT / "native.json").is_file()):
        pytest.skip("original Astropy native bytes require access to the private custody file")


@pytest.fixture
def packet(tmp_path, original_available):
    dest = tmp_path / "packet"
    shutil.copytree(PACKET, dest)
    native = attempt(dest) / "native.json"
    if not native.exists():
        terminal = json.loads((dest / RESULT).read_bytes())
        native.write_bytes(adapter.native_bytes(dest, attempt(dest), terminal["native_sha256"]))
    return dest


def attempt(packet):
    return next((packet / "official").glob("attempt-*"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_json(path, change):
    doc = json.loads(path.read_bytes())
    change(doc)
    path.write_text(json.dumps(doc))


def reseal(packet, change):
    result = packet / RESULT
    replace_json(result, change)
    shutil.copyfile(result, attempt(packet) / "terminal.json")
    return digest(result)


def test_original_observations(original_available):
    rows = adapter.native_rows(PACKET / RESULT)
    assert Counter((row["arm"], row["group"], row["status"]) for row in rows) == {
        ("gold", "FAIL_TO_PASS", "PASSED"): 2,
        ("gold", "PASS_TO_PASS", "PASSED"): 13,
        ("negative", "FAIL_TO_PASS", "FAILED"): 2,
        ("negative", "PASS_TO_PASS", "PASSED"): 13,
    }
    tuples = [adapter.project(row) for row in rows]
    assert len({claim.measurement_id for claim in tuples}) == 30
    assert all(grade(claim)[:2] == ("Judged", "Located") and not claim.applicability for claim in tuples)


@pytest.mark.parametrize("name", ["case.json", "pins.json", "build.log", "complete.py", "SOURCE.sha256", "launch.sh"])
def test_changed_source_refused(packet, name):
    path = packet / name
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ProjectionError):
        adapter.native_rows(packet / RESULT)


@pytest.mark.parametrize("name", ["native.json", "gold-report.json", "negative-report.json", "gold-test_output.txt",
                                  "negative-test_output.txt", "rowflow.grant", "controls.log", "terminal.json"])
def test_changed_native_artifact_refused(packet, name):
    path = attempt(packet) / name
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ProjectionError):
        adapter.native_rows(packet / RESULT)


def test_invented_row_and_post_read_loss_refused(packet):
    row = adapter.native_rows(packet / RESULT)[0]
    with pytest.raises(ProjectionError, match="row does not rederive"):
        adapter.project({**row, "status": "PASSED"})
    (attempt(packet) / "negative-report.json").unlink()
    with pytest.raises(ProjectionError, match="arm artifact changed"):
        adapter.project(row)


def test_coherent_reseal_refused(packet):
    raw = attempt(packet) / "native.json"
    replace_json(raw, lambda x: x.update(owned_containers_removed=False))
    reseal(packet, lambda doc: doc.update(native_sha256=digest(raw)))
    with pytest.raises(ProjectionError, match="terminal pin mismatch"):
        adapter.native_rows(packet / RESULT)


def test_private_manifest_rejects_another_path(tmp_path):
    dest = tmp_path / "packet"
    shutil.copytree(PACKET, dest)
    (attempt(dest) / "native.json").unlink(missing_ok=True)
    replace_json(dest / "PRIVATE-EVIDENCE.json", lambda item: item.update(path="/tmp/native.json"))
    with pytest.raises(ProjectionError, match="private native evidence manifest mismatch"):
        adapter.native_rows(dest / RESULT)


@pytest.mark.parametrize("present", [True, False])
def test_private_native_bytes_unavailable_or_changed_refused(packet, tmp_path, monkeypatch, present):
    private = tmp_path / "private"
    private.mkdir()
    native = attempt(packet) / "native.json"
    if present:
        (private / "native.json").write_bytes(native.read_bytes() + b" ")
    native.unlink()
    replace_json(packet / "PRIVATE-EVIDENCE.json", lambda item: item.update(path=str(private / "native.json")))
    monkeypatch.setattr(adapter, "PRIVATE_ROOT", private)
    with pytest.raises(ProjectionError, match="private native evidence unavailable or changed"):
        adapter.native_rows(packet / RESULT)


@pytest.mark.parametrize(("mutate", "reason"), [
    (lambda x: x.update(owned_containers_removed=False), "cleanup mismatch"),
    (lambda x: x["arm_container_ids"].update(gold=x["arm_container_ids"]["negative"]), "container binding mismatch"),
    (lambda x: x["script_binding"].update(setup_index=9), "harness script binding mismatch"),
    (lambda x: x["arms"]["gold"]["PASS_TO_PASS"].pop(next(iter(x["arms"]["gold"]["PASS_TO_PASS"]))),
     "selector coverage"),
])
def test_rederive_native_semantics_independently(packet, monkeypatch, mutate, reason):
    raw = attempt(packet) / "native.json"
    replace_json(raw, mutate)
    monkeypatch.setattr(adapter, "TERMINAL", reseal(packet, lambda doc: doc.update(native_sha256=digest(raw))))
    with pytest.raises(ProjectionError, match=reason):
        adapter.native_rows(packet / RESULT)


@pytest.mark.parametrize(("artifact", "reason"), [("gold-report.json", "report status mismatch"),
                                                 ("negative-test_output.txt", "test log status mismatch")])
def test_rederive_named_statuses_independent_of_artifact_hashes(packet, monkeypatch, artifact, reason):
    path = attempt(packet) / artifact
    if artifact.endswith(".json"):
        replace_json(path, lambda x: x[adapter.INSTANCE]["tests_status"]["PASS_TO_PASS"]["success"].clear())
    else:
        path.write_text(path.read_text().replace("\nFAILED astropy/", "\nPASSED astropy/", 1))
    terminal = reseal(packet, lambda doc: doc["arm_artifacts_sha256"].update({artifact: digest(path)}))
    monkeypatch.setattr(adapter, "TERMINAL", terminal)
    with pytest.raises(ProjectionError, match=reason):
        adapter.native_rows(packet / RESULT)


@pytest.mark.parametrize(("mutate", "reason"), [
    (lambda x: x.update(status="UNKNOWN"), "terminal identity"),
    (lambda x: x.update(mode="smoke"), "terminal identity"),
    (lambda x: x.update(instrument_deadline_epoch=0), "instrument window"),
    (lambda x: x["grant"].update(actual_cpus=[140]), "affinity"),
])
def test_rederive_terminal_semantics_independently(packet, monkeypatch, mutate, reason):
    monkeypatch.setattr(adapter, "TERMINAL", reseal(packet, mutate))
    with pytest.raises(ProjectionError, match=reason):
        adapter.native_rows(packet / RESULT)


def test_cli_dispatches_original_packet(tmp_path, original_available):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/vidya/cli.py"), "--ledger", str(tmp_path / "ledger.jsonl"),
         "--json", "ingest", adapter.SOURCE_KIND, "--path", str(PACKET / RESULT), "--as-of", canary.AS_OF,
         "--only-new"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    receipt = json.loads(result.stdout)
    assert receipt["rows_projected"] == 30 and receipt["frames_emitted"] == 90 and not receipt["refused"]


def test_exact_native_planning_context(tmp_path, original_available):
    receipt = canary.run(PACKET, tmp_path / "context")
    assert receipt["status"] == "PASS"
    assert receipt["cases"]["exact-task"]["eligible"] == 30
    assert receipt["cases"]["exact-task"]["shown"] == 16
    assert receipt["tamper_refusals"] == 1 and receipt["tamper_frames"] == 0
