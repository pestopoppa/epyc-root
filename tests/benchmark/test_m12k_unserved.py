"""Offline HTTP fixtures through the real row client, recorder and paired reducers."""
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import urllib.error

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "scripts/benchmark/m12k_frontdoor_memory_ab.py"
spec = importlib.util.spec_from_file_location("m12k_job", SOURCE)
job = importlib.util.module_from_spec(spec)
spec.loader.exec_module(job)


def item(i=0):
    return SimpleNamespace(item_id=f"i{i}", suite="s", prompt="Choose A or B", expected="B")


def payload(role="architect_general", reason="connection refused", **extra):
    # Put roles beyond the legacy 300-character error truncation.
    return dict(answer=f"[ERROR: {reason}] " + "x" * 350, routed_to=role,
                role_history=["frontdoor", role], routing_strategy="rules", **extra)


def http_fixture(monkeypatch, code, body):
    raw = body if isinstance(body, bytes) else json.dumps(body).encode()

    def urlopen(*args, **kwargs):
        raise urllib.error.HTTPError(job.API + "/chat", code, "fixture", {}, io.BytesIO(raw))

    monkeypatch.setattr(job.urllib.request, "urlopen", urlopen)


def no_scoring(_):
    pytest.fail("An infrastructure response must not reach the answer scorer")


@pytest.mark.parametrize("code,reason", [(502, "backend connection_error"),
                                         (504, "backend timeout"),
                                         (429, "backend admission queue full")])
@pytest.mark.parametrize("arm", ["ON", "OFF"])
def test_http_errors_void_both_arms_and_reach_futility(monkeypatch, code, reason, arm):
    http_fixture(monkeypatch, code, payload(reason=reason))
    bad = job.run_request(item(), arm, no_scoring, "ON")
    assert bad["unserved"] and bad["correct"] is None
    assert bad["http"] == code and bad["status"] == "http_error"
    assert bad["routed_to"] == "architect_general"
    assert bad["role_history"] == ["frontdoor", "architect_general"]
    assert len(bad["error"]) == 300  # Full payload was parsed before truncating receipt text.
    records = []
    for i in range(100):
        for a in ("ON", "OFF"):
            r = dict(item_id=f"i{i}", suite="s", arm=a, arm_first="ON", status="ok",
                     correct=True, unserved=False, routed_to="frontdoor",
                     routing_strategy="learned" if a == "ON" else "rules", wall_s=1)
            if i < 11:
                if a == arm:
                    r.update(bad, item_id=f"i{i}", unit_id=f"i{i}|{a}")
                else:
                    r["correct"] = False  # Must exclude the other arm's score too.
            records.append(r)
        records.append(dict(records[-2 if arm == "OFF" else -1], arm="ON2", correct=True))
    verdict, summary = job.decide_look(records, 100)
    assert verdict == "FUTILITY_UNSERVED_ROUTING"
    assert (summary["n_pairs"], summary["n_pairs_total"], summary["n_voided_unserved"]) == (89, 100, 11)
    assert summary["b"] == summary["c"] == 0
    assert summary["errors"] == {"ON": 0, "OFF": 0}
    final = job.final_result(records, {f"i{i}": {"suite": "s"} for i in range(100)})
    assert final["verdict"] == verdict and final["n_voided_unserved"] == 11
    assert final["ON"]["accuracy"] == final["OFF"]["accuracy"] == 1
    assert final["ON"]["wall_s"]["total"] == final["OFF"]["wall_s"]["total"] == 89
    assert final["aa_floor"]["n"] == 89
    # Exactly 10% voided does not cross the frozen strict >10% boundary.
    for r in records:
        if r["item_id"] == "i10":
            r.update(unserved=False, correct=True, status="ok", routed_to="frontdoor", wall_s=1)
    assert job.decide_look(records, 100)[0] is None


@pytest.mark.parametrize("code,body", [
    (429, {"detail": "admission queue full"}),
    (503, {"detail": "backend unavailable"}),
    (502, payload(role="frontdoor")),
    (504, payload(role="worker_general", reason="timeout")),
    (429, payload(reason="quota exceeded")),
    (502, b"<html>proxy failure</html>"),
    (504, b"not json"),
    (429, ["backend admission queue full"]),
    (502, {"routed_to": "architect_general", "answer": "The answer is B"}),
])
def test_status_alone_or_served_role_is_not_unserved(monkeypatch, code, body):
    http_fixture(monkeypatch, code, body)
    rec = job.run_request(item(), "ON", no_scoring, "ON")
    assert rec["unserved"] is False and rec["correct"] is False


def test_history_and_error_detail_are_preserved(monkeypatch):
    http_fixture(monkeypatch, 504, dict(answer="", routed_to="frontdoor",
                 role_history=["frontdoor", "coder_escalation"], error_detail="backend timeout"))
    rec = job.run_request(item(), "OFF", no_scoring, "OFF")
    assert rec["unserved"] and rec["error_detail"] == "backend timeout"


def test_http200_rules_and_success_scoring_unchanged(monkeypatch):
    assert job.is_unserved(True, "[ERROR: connection refused]", "coder_escalation", [])
    assert not job.is_unserved(True, "B", "coder_escalation", [])
    assert not job.is_unserved(True, "[ERROR: connection refused]", "frontdoor", [])
    monkeypatch.setattr(job, "post_chat", lambda _: dict(status="ok", http=200, wall_s=1,
                          payload=dict(answer="B", routed_to="frontdoor", role_history=[])))
    rec = job.run_request(item(), "ON", lambda _: "B", "ON")
    assert rec["correct"] is True and not rec["unserved"]


@pytest.mark.parametrize("unserved,expected_rc", [(True, 0), (False, 3)])
def test_smoke_reports_error_metadata_and_keeps_infra_failure(monkeypatch, tmp_path, unserved, expected_rc):
    http_fixture(monkeypatch, 429, payload(reason="backend admission queue full") if unserved
                 else {"detail": "admission queue full"})
    monkeypatch.setattr(job, "OUT", str(tmp_path))
    monkeypatch.setattr(job, "pin_cpus", lambda: "fixture")
    monkeypatch.setattr(job, "preflight", lambda: {"problems": []})
    monkeypatch.setattr(job, "episodic_count", lambda: {"rows": 64514})
    monkeypatch.setattr(job, "load_everything", lambda: ([], lambda: ([], {}),
                                                      lambda *args: [item(), item(1)], no_scoring))
    assert job.smoke() == expected_rc
    receipt = json.loads((tmp_path / "smoke" / f"{job.ID}.json").read_text())
    assert len(receipt["records"]) == 4
    assert all(r["http"] == 429 and r["error"] and r["unserved"] is unserved for r in receipt["records"])
    assert receipt["episodic_custody"]["unchanged"]
