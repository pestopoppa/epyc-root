import dataclasses
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/vidya"))
from adapters import kvu19b_gap as adapter  # noqa: E402
import claim_tuple  # noqa: E402
import ingest_sources  # noqa: E402
import loop_beliefs  # noqa: E402
from ledger import Ledger  # noqa: E402

REAL = Path("/mnt/raid0/llm/tmp/kvu/kvu19b-gap-clean-20261104/run-8zokixki/belief_measurements.jsonl")
MODEL = "/synthetic/gemma-3-1b-it-Q8_0.gguf"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def make_run(tmp_path, n=2):
    run = tmp_path / "run-synth"
    run.mkdir()
    lines = []
    for i in range(n):
        kvu = i % 2
        out, err = run / f"{i:02d}-{kvu}.stdout", run / f"{i:02d}-{kvu}.stderr"
        out.write_bytes(b"ok %d" % i); err.write_bytes(b"")
        samples = [{"own_vram_b": 1000 + k, "gpu_bdf": "0000:43:00.0",
                    "mapped_libraries": {"libggml-hip.so.0.16.0": "abc", "libggml.so": "def"}} for k in range(3)]
        row = {"started_utc": "2026-11-04T19:53:05+00:00", "completed_utc": "2026-11-04T19:53:10+00:00", "index": i, "kvu": kvu,
               "rc": 0, "cleanup": {"verified_dead": True}, "samples": samples, "stdout": str(out), "stderr": str(err),
               "raw_sha256": {"stdout": sha(out.read_bytes()), "stderr": sha(err.read_bytes())},
               "metrics": {"ms_per_step": 7.5 + i}}
        assets = {"source_commit": "c" * 40, "model": {"path": MODEL, "sha256": "b" * 64}}
        child = run / f"child-{i:02d}.json"
        child.write_text(json.dumps({"schema": adapter.CHILD_SCHEMA, "row": row, "assets": assets}))
        tup = claim_tuple.ClaimTuple(
            measurement_id=f"run-synth:{i}:ms_per_step", metric=adapter.METRIC, value=row["metrics"]["ms_per_step"],
            date=row["completed_utc"], category="CANDIDATE" if kvu else "BASELINE", claim="synthetic p3batch step",
            metric_direction="lower_better", protocol_id="", reps=1, reps_basis="scored", unit="ms/step",
            attestation_path=str(child), attestation_sha256=sha(child.read_bytes()), attestation_present=True,
            attestation_verified=True, source_class="measurement",
            applicability={"model_file": MODEL, "model_sha256": "b" * 64, "backend": "HIP", "device": "0000:43:00.0",
                           "kernel": "c" * 40, "run_id": "run-synth", "np": 4, "scope_basis": "native",
                           "surface": "synthetic-p3batch", "knobs": {"kv_unified": kvu}})
        lines.append(json.dumps({"schema": adapter.RECORD_SCHEMA, "source_family": adapter.SOURCE_FAMILY,
                                 "authored_at": row["completed_utc"], "claim_tuple": dataclasses.asdict(tup)}))
    side = run / adapter.SIDECAR_NAME
    side.write_text("\n".join(lines) + "\n")
    return run, side


def test_projects_and_grades_as_observation(tmp_path):
    _, side = make_run(tmp_path)
    frames = adapter.frames_for_sidecar(side, as_of="2026-11-07T00:00:00Z")
    assert frames
    rows = adapter.native_rows(side)
    tup = adapter.project(rows[0])
    assert tup.applicability["model_file"] == "gemma-3-1b-it-Q8_0.gguf"
    q, t, reasons = claim_tuple.grade(tup)[:3]
    assert q != "Witnessed"          # no protocol: never decision-grade


@pytest.mark.parametrize("tamper", ["child", "stdout", "value", "protocol", "no_live_gpu", "cleanup", "family", "model"])
def test_negative_controls_refuse(tmp_path, tamper):
    run, side = make_run(tmp_path)
    child = run / "child-00.json"
    if tamper == "child":
        child.write_text(child.read_text() + " ")
    elif tamper == "stdout":
        (run / "00-0.stdout").write_bytes(b"changed")
    else:
        rec = json.loads(side.read_text().splitlines()[0])
        t = rec["claim_tuple"]
        if tamper == "value":
            t["value"] = 1.0
        elif tamper == "protocol":
            t["protocol_id"] = "P-1"
        elif tamper == "family":
            rec["source_family"] = "other"
        elif tamper == "model":
            t["applicability"]["model_sha256"] = "d" * 64
        else:
            c = json.loads(child.read_text())
            if tamper == "no_live_gpu":
                c["row"]["samples"][0]["own_vram_b"] = 0; c["row"]["samples"][1]["own_vram_b"] = 0
            else:
                c["row"]["cleanup"]["verified_dead"] = False
            child.write_text(json.dumps(c)); t["attestation_sha256"] = sha(child.read_bytes())
        side.write_text(json.dumps(rec) + "\n" + "\n".join(side.read_text().splitlines()[1:]) + "\n")
    with pytest.raises(claim_tuple.ProjectionError):
        adapter.native_rows(side)


def test_registered_source_ingests_and_reaches_planning_context(tmp_path):
    run, _ = make_run(tmp_path)
    ledger = Ledger(tmp_path / "ledger.jsonl")
    now = "2026-11-07T00:00:00Z"
    report = ingest_sources.ingest(ledger, "kvu19b-gap", [run], as_of=now)
    assert not report["refused"], report["refused"]
    assert report["rows_projected"] == 2

    class Sync:
        def status(self, *a, **k):
            return {"fresh": True, "lag_entries": 0, "index_max_id": 0, "synced_max_id": 0, "last_sync": now}
    config = tmp_path / "alarm.yaml"
    config.write_text("backend: file\nfile:\n  path: " + str(tmp_path / "alarms.jsonl") + "\n")

    def ctx(model, name):
        return loop_beliefs.prepare("kvu19b.synthetic." + name, {"model_file": model, "backend": "gpu"},
                                    ledger=ledger.path, index_path=tmp_path / "index", as_of=now, sync_module=Sync(),
                                    known_good=tmp_path / (name + "-kg.json"), alarm_state=tmp_path / (name + "-al.json"),
                                    alarm_config=config, read_log=tmp_path / (name + "-reads.jsonl"))
    assert len(ctx("gemma-3-1b-it-Q8_0.gguf", "hit")["evidence"]["claim_ids"]) == 2
    assert not ctx("unrelated.gguf", "miss").get("evidence", {}).get("claim_ids", [])
    (run / "00-0.stdout").write_bytes(b"x")
    assert ingest_sources.ingest(None, "kvu19b-gap", [run], as_of=now, dry_run=True)["refused"]


@pytest.mark.skipif(not REAL.is_file(), reason="real producer sidecar absent")
def test_real_producer_sidecar_ingests_with_zero_refused(tmp_path):
    ledger = Ledger(tmp_path / "ledger.jsonl")
    report = ingest_sources.ingest(ledger, "kvu19b-gap", [REAL.parent], as_of="2026-11-07T00:00:00Z")
    assert not report["refused"], report["refused"]
    assert report["rows_projected"] == 12
