import hashlib
import json

import natural_qualification as q
from paired_journal import create, encoded


def events():
    return [
        {"type": "kani_spawn", "id": "root", "depth": 0, "parent": None},
        {
            "type": "kani_message",
            "id": "root",
            "msg": {
                "role": "assistant",
                "tool_calls": [{"function": {"name": "delegate"}}],
            },
        },
        {"type": "kani_spawn", "id": "child", "depth": 1, "parent": "root"},
        {"type": "kani_delegated", "parent_id": "root", "child_id": "child"},
    ]


def test_natural_gate_requires_real_linked_call_and_spawn():
    good = events()
    assert q.event_qualification(good)
    assert not q.event_qualification([good[0]])
    assert not q.event_qualification([good[0], good[1]])
    assert not q.event_qualification([good[0], good[2], good[3]])
    assert not q.event_qualification(
        [good[0], good[1], dict(good[2], parent="other"), good[3]]
    )
    assert not q.event_qualification(
        [good[0], good[1], good[2], dict(good[3], child_id="other")]
    )
    assert not q.event_qualification([good[0], good[2], good[1], good[3]])


def test_control_sealed_identity_and_refusal(tmp_path):
    campaign = "a" * 64
    control = {"id": "case24"}
    prompt = "b" * 64
    identity = {
        "campaign_sha256": campaign,
        "id": control["id"],
        "arm": "redel_delegate_wait",
        "prompt_sha256": prompt,
    }
    key = hashlib.sha256(
        encoded(
            {"campaign_sha256": campaign, "id": control["id"], "arm": identity["arm"]}
        )
    ).hexdigest()
    assert not q.inspect_control(tmp_path, campaign, control, prompt)["qualified"]
    start = tmp_path / (key + ".start")
    create(start, {"identity": identity, "exposure": "unknown"})
    assert not q.inspect_control(tmp_path, campaign, control, prompt)["qualified"]
    end = tmp_path / (key + ".end")
    create(
        end,
        {
            "identity": identity,
            "start_sha256": hashlib.sha256(start.read_bytes()).hexdigest(),
            "status": "complete",
            "native": {
                "status": "complete",
                "flat_server_bound_attested": True,
                "native_events": events(),
            },
        },
    )
    assert q.inspect_control(tmp_path, campaign, control, prompt)["qualified"]
    record = json.loads(end.read_bytes())
    record["identity"]["id"] = "other"
    end.write_text(json.dumps(record))
    try:
        q.inspect_control(tmp_path, campaign, control, prompt)
    except ValueError:
        pass
    else:
        raise AssertionError("identity tamper accepted")


def test_pilot_refused_before_dataset_or_server(monkeypatch):
    import sys
    import pytest
    import campaign_job

    declaration = {"independent_smoke_control": {"id": "case24"}}
    monkeypatch.setattr(campaign_job, "identities", lambda: declaration)
    monkeypatch.setattr(campaign_job.c, "sha", lambda path: campaign_job.MANIFEST)
    monkeypatch.setattr(
        campaign_job, "inspect_control", lambda *args: {"qualified": False}
    )
    monkeypatch.setattr(
        campaign_job, "rows", lambda *args: pytest.fail("pilot data accessed")
    )
    monkeypatch.setattr(sys, "argv", ["campaign_job.py"])
    with pytest.raises(RuntimeError, match="pilot refused"):
        campaign_job.main()
