"""Synthetic native-shaped records through the canonical CLI and planning reader."""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

import cli
import loop_beliefs
from adapters import mi210_paired_raw
from claim_tuple import grade
from ledger import Ledger
from scripts.vidya.producers import mi210_paired_capture as raw


def _capture(tmp_path, *, source="Q38P-3a", model_name="MOCK_ONLY.gguf",
             mode="measurement", state="complete", defect=None):
    path = tmp_path / "synthetic-run"
    path.mkdir()
    model = tmp_path / model_name
    model.write_bytes(b"synthetic weight identity, no GGUF or inference")
    digest = raw.carrier.file_sha256(model)
    arms = ["C", "B"] if source == "Q38P-3a" else ["cpu", "gpu_cpu"]
    recipe = {"arm_categories": dict(zip(arms, ("BASELINE", "CANDIDATE"))),
              "argv": {arm: ["llama-server", "-m", str(model), "-ngl", "all", "--device", "ROCm0"]
                       for arm in arms}}
    if defect == "scope":
        recipe["argv"][arms[-1]][-3] = "0"
    elif defect == "alias":
        recipe["argv"][arms[-1]].extend(["-dev", "none"])
    identities = [{"path": str(model), "sha256": digest, "error": None}]
    if source == "NPD1-STEP3":
        identities.append({"path": str(tmp_path / "MOCK_ONLY-MTP.gguf"), "sha256": "e" * 64})
    raw.begin(path, {"source": source, "mode": mode, "model": identities, "builds": None,
                     "recipe": recipe,
                     "order": [["p1", arm] for arm in arms], "grant": None,
                     "native_producer": {"path": __file__, "sha256": raw.carrier.file_sha256(Path(__file__))}})
    for index, arm in enumerate(arms):
        timings = {"predicted_n": 8, "predicted_ms": 100 * (index + 1),
                   "predicted_per_second": 80 / (index + 1)}
        if defect == "timing" and index == 1:
            timings["predicted_ms"] = 0
        raw.record(path, {"pair": "p1", "arm": arm, "state": "complete",
                          "requests": [{"timings": timings}], "actual_placement": None,
                          "residency_linkage": None, "grant": None, "stop": None,
                          "errors": None, "release": None})
    if state is not None:
        raw.finish(path, state)
    return path, digest


def _argv(ledger, path, as_of):
    return ["--ledger", str(ledger), "--json", "ingest", "mi210-paired-raw",
            "--path", str(path), "--as-of", as_of, "--only-new"]


@pytest.mark.parametrize(("source", "metric", "direction", "values"), [
    ("Q38P-3a", "native_request_decode_tps", "higher_better", [80, 40]),
    ("NPD1-STEP3", "native_request_tpot_ms", "lower_better", [12.5, 25]),
])
def test_canonical_cli_projects_with_shared_grade_and_retries(
        tmp_path, capsys, source, metric, direction, values):
    path, digest = _capture(tmp_path, source=source)
    ledger = Ledger(tmp_path / "ledger.jsonl")
    as_of = datetime.now(timezone.utc).isoformat()
    argv = _argv(ledger.path, path, as_of)
    shell_cli = Path(cli.__file__).resolve()
    first = subprocess.run([sys.executable, "-I", str(shell_cli), *argv], cwd=tmp_path,
                           capture_output=True, text=True, check=True)
    report = json.loads(first.stdout)
    assert (report["rows_projected"], report["frames_emitted"], report["refused"]) == (2, 6, [])
    rows = mi210_paired_raw.project(path)
    assert {grade(row)[:2] for row in rows} == {("Judged", "Located")}
    frames = [record.frame for record in ledger.read_all()]
    supported = [frame["assertion"] for frame in frames
                 if frame["frame_type"].endswith("evidence_supports_claim/v1")]
    assert [float(item["value"]) for item in supported] == values
    assert {item["metric"] for item in supported} == {metric}
    assert {item["metric_direction"] for item in supported} == {direction}
    assert {item["protocol_id"] for item in supported} == {""}
    assert [item["grade"] for item in supported] == [{"Q": "Judged", "T": "Located"}] * 2
    sources = [frame["assertion"] for frame in frames
               if frame["frame_type"].endswith("source_observed/v1")]
    if source == "Q38P-3a":
        assert [item["applicability"] for item in sources] == [
            {"model_sha256": digest, "backend": "gpu", "scope_basis": "native"}] * 2
    else:
        assert all("applicability" not in item for item in sources)
    assert cli.main(argv) == 0
    assert json.loads(capsys.readouterr().out)["frames_skipped"] == 6
    assert ledger.verify() == [] and len(ledger.read_all()) == 6


@pytest.mark.parametrize(("case", "reason"), [
    ("smoke", "only complete measurement-scope"),
    ("partial", "only complete measurement-scope"),
    ("failed", "only complete measurement-scope"),
    ("stopped", "only complete measurement-scope"),
    ("interrupted", "only complete measurement-scope"),
    ("tamper", "digest mismatch"),
    ("timing", "native timing denominator"),
    ("legacy", "invalid capture path"),
])
def test_refused_unit_appends_no_frames(tmp_path, capsys, case, reason):
    if case == "legacy":
        path = tmp_path
        (path / "results.jsonl").write_text("{}\n")
    else:
        state = {"interrupted": None, "partial": "partial", "failed": "failed",
                 "stopped": "stopped"}.get(case, "complete")
        path, _ = _capture(tmp_path, mode="smoke" if case == "smoke" else "measurement",
                           state=state, defect=case)
        if case == "tamper":
            (path / "attempt-01.json").write_text('{}\n')
    ledger = Ledger(tmp_path / "ledger.jsonl")
    assert cli.main(_argv(ledger.path, path, datetime.now(timezone.utc).isoformat())) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["rows_projected"] == report["frames_emitted"] == 0
    assert len(report["refused"]) == 1 and reason in report["refused"][0]["reason"]
    assert not ledger.path.exists() or ledger.read_all() == []


@pytest.mark.parametrize("case", ["split", "scope", "alias"])
def test_split_weight_or_non_gpu_recipe_stays_unscoped(tmp_path, case):
    model_name = "MOCK_ONLY-00001-of-00003.gguf" if case == "split" else "MOCK_ONLY.gguf"
    path, _ = _capture(tmp_path, model_name=model_name, defect=case)
    assert all(row.applicability == {} for row in mi210_paired_raw.project(path))


def test_synthetic_exact_digest_context_canary(tmp_path, capsys):
    path, digest = _capture(tmp_path)
    ledger = tmp_path / "ledger.jsonl"
    as_of = datetime.now(timezone.utc).isoformat()
    assert cli.main(_argv(ledger, path, as_of)) == 0
    assert json.loads(capsys.readouterr().out)["rows_projected"] == 2
    sync = SimpleNamespace(status=lambda _ledger, _index: {"fresh": True, "last_sync": as_of})
    alarm_cfg = tmp_path / "alarm.yaml"
    alarm_cfg.write_text(f"backend: file\nfile:\n  path: {tmp_path / 'alarms.jsonl'}\n")

    def prepare(target_digest, backend="gpu"):
        return loop_beliefs.prepare(
            "test.mi210.synthetic", {"model_file": "MOCK_ONLY.gguf", "backend": backend,
                                    "model_sha256": target_digest},
            ledger=ledger, as_of=as_of, sync_module=sync,
            known_good=tmp_path / "known-good.json", alarm_state=tmp_path / "alarm.json",
            alarm_config=alarm_cfg, read_log=tmp_path / "reads.jsonl")

    matching = prepare(digest)
    assert matching["status"] == "ready"
    assert matching["evidence"]["status"] == "presented"
    assert len(matching["evidence"]["claim_ids"]) == 2
    for target_digest, backend in (("", "gpu"), ("f" * 64, "gpu"), (digest, "cpu")):
        other = prepare(target_digest, backend)
        assert other["status"] == "ready" and not other["evidence"]["claim_ids"]


def test_unscoped_native_tpot_is_background_for_autokernel_only(tmp_path):
    as_of = datetime.now(timezone.utc).isoformat()
    npd1, _ = _capture(tmp_path, source="NPD1-STEP3")
    other_dir = tmp_path / "other-source"
    other_dir.mkdir()
    q38, _ = _capture(other_dir, model_name="MOCK_ONLY-00001-of-00003.gguf")
    frames = [*mi210_paired_raw.emit(npd1, as_of=as_of),
              *mi210_paired_raw.emit(q38, as_of=as_of)]
    native_sources = [frame["assertion"] for frame in frames
                      if frame["frame_type"].endswith("source_observed/v1")]
    assert all("applicability" not in source for source in native_sources)
    for name in ("MOCK_ONLY.gguf", "UNRELATED.gguf"):
        targets = [loop_beliefs.Target.from_mapping({"model_file": name, "backend": "cpu"})]
        planner = loop_beliefs.evaluate_frames(
            frames, targets, as_of=as_of, consumer="autokernel.planner")
        assert {claim["value"] for claim in planner["claims"]} == {12.5, 25.0}
        assert all(claim["tier"] == "harness" and claim["not_evidence"]
                   and not claim["model_file"] for claim in planner["claims"])
        assert not planner["claim_ids"] and not planner["nonempty_target"]
        other = loop_beliefs.evaluate_frames(
            frames, targets, as_of=as_of, consumer="autopilot.planner")
        assert other["reasons"] == ["no_applicable_claims"] and not other["claims"]
    assert all("applicability" not in source for source in native_sources)
