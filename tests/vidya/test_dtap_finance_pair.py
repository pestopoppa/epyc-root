"""dtap-finance-pair: strict reader over a synthetic finance paired native record, tamper controls, CLI ingest."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/vidya"))
from adapters import dtap_finance_pair as adapter  # noqa: E402
from claim_tuple import ProjectionError, grade  # noqa: E402

PAYLOAD = "IMPORTANT SPECIAL HANDLING (POLICY TEST)"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def build(tmp_path, delivery="nondelivered", task_success=False):
    manifest = tmp_path / "source-files.sha256"
    manifest.write_bytes(b"x  file\n")
    msha = sha(manifest.read_bytes())
    arms, files = {}, {}
    for i, arm in enumerate(adapter.ARMS):
        events = [{"tool": "get_message", "attack_delivered": False, "result": "not found"}]
        if arm == "attack" and delivery == "delivered":
            events = [{"tool": "trade_stock", "attack_delivered": True, "result": PAYLOAD + " rest"}]
        judge = {"task_success": task_success, "attack_success": False, "error": None}
        row = {"arm": arm, "case": adapter.CASE, "seed": 42, "events": events, "native_judge": judge,
               "attack_delivery": delivery if arm == "attack" else "not-applicable",
               "runtime": {"source_manifest_sha256": msha, "model_sha256": "c" * 64, "grant": "g",
                           "upstream_commit": "e" * 40}}
        arms[arm] = row
        ident = {}
        for kind, body in (("result", {"native_judge": judge, "events": events}), ("setup", {"i": i}),
                           ("exposure", {"e": i})):
            p = tmp_path / f"{arm}.{kind}.json"
            p.write_text(json.dumps(body))
            ident[kind + "_path"], ident[kind + "_sha256"] = str(p), sha(p.read_bytes())
        files[arm] = ident
    record = {"schema": adapter.SCHEMA, "completed_at": "2026-10-31T02:03:57+00:00", "case": adapter.CASE,
              "scope": "s", "source_manifest_path": str(manifest), "source_manifest_sha256": msha,
              "case_source_sha256": "a" * 64, "injection_payload": PAYLOAD, "attack_delivery": delivery,
              "cleanup": "verified", "arms": arms, "files": files}
    path = tmp_path / "native-record.json"
    path.write_text(json.dumps(record))
    return path


def test_projects_one_baseline_tuple_and_never_an_attack_claim(tmp_path):
    (row,) = adapter.native_rows(build(tmp_path))
    claim = adapter.project(row)
    assert claim.metric == "legitimate_task_success" and claim.value == 0
    assert claim.extra["attack_delivery"] == "nondelivered"
    assert claim.extra["physical_authority"] == "UNKNOWN"
    assert grade(claim)[:2] == ("Judged", "Located")


def test_delivered_requires_native_witness(tmp_path):
    adapter.native_rows(build(tmp_path, delivery="delivered"))
    path = build(tmp_path)
    rec = json.loads(path.read_text())
    rec["attack_delivery"] = "delivered"
    rec["arms"]["attack"]["attack_delivery"] = "delivered"
    path.write_text(json.dumps(rec))
    with pytest.raises(ProjectionError):
        adapter.native_rows(path)


@pytest.mark.parametrize("victim", ["attack.result.json", "baseline.setup.json", "source-files.sha256"])
def test_tampered_custody_files_refuse(tmp_path, victim):
    path = build(tmp_path)
    (tmp_path / victim).write_bytes(b"tampered")
    with pytest.raises(ProjectionError):
        adapter.native_rows(path)


def test_unknown_schema_and_missing_judgment_refuse(tmp_path):
    path = build(tmp_path)
    rec = json.loads(path.read_text())
    rec["schema"] = "other"
    path.write_text(json.dumps(rec))
    with pytest.raises(ProjectionError):
        adapter.native_rows(path)
    path = build(tmp_path)
    rec = json.loads(path.read_text())
    del rec["arms"]["baseline"]["native_judge"]["error"]
    path.write_text(json.dumps(rec))
    with pytest.raises(ProjectionError):
        adapter.native_rows(path)


def test_cli_ingest_reports_zero_refused(tmp_path, capsys):
    import cli
    path = build(tmp_path)
    ledger = tmp_path / "ledger.jsonl"
    assert cli.main(["--ledger", str(ledger), "--json", "ingest", "dtap-finance-pair", "--path", str(path),
                     "--as-of", "2026-11-08T00:00:00+00:00"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["rows_projected"] == 1 and not report["refused"]
