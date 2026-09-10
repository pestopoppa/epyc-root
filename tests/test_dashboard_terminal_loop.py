"""Original terminal producer reports age without impersonating lost live work."""
import json
import time
from datetime import datetime, timezone

import pytest

from dashboard import campaign_status, loop_status
from tests.test_dashboard_runtime_js import _page_js, _run
from tests.test_dashboard_serial_loop import producer as producer
from tests.test_dashboard_serial_loop import sources as sources


@pytest.mark.parametrize("state", ["complete", "failed"])
@pytest.mark.parametrize("age", [30, 9000])
def test_actual_terminal_writer_reader_and_page(tmp_path, monkeypatch, producer, state, age):
    root = tmp_path / "store"
    producer.write(root, state=state, epoch="fixture", campaign_id="ak-loop",
        anchor_commit="a" * 40, surface="serving:fixture", pairs=5, noise_floor_pct=7.8,
        iterations_planned=5, outcomes=[{"status": "measured_null", "effect_fraction": 0.001}] * 5,
        step="[lane0] measuring A/B on the device", stale_after_s=180)
    path = root / "loop-status.json"
    original = path.read_bytes()
    # Date the read after the original writer's timestamp, without rewriting it.
    now = loop_status._stamp_epoch(json.loads(original)["generated_at"]) + age
    for name in (campaign_status.STORE_ROOT_ENV, campaign_status.CAMPAIGN_ID_ENV,
                 campaign_status.CONFIG_GENERATION_ENV, campaign_status.CONFIG_DIGEST_ENV):
        monkeypatch.delenv(name, raising=False)
    wire, observation = loop_status.snapshot(root, now=now)
    assert wire["freshness_state"] == ("fresh" if age == 30 else "stale")
    assert wire["age_s"] == age
    assert wire["display_step"] == f"Run {state} — final report"
    assert "no further heartbeat is expected" in wire["detail"]
    assert wire["loop"]["step"] == "[lane0] measuring A/B on the device"
    assert observation.producer_idle is (state == "complete")
    rendered = _run(_page_js(), wire, tmp_path, ["render"])
    assert not rendered["threw"]
    assert rendered["text_by_id"]["hdr-step"] == f"Run {state} — final report"
    badge = rendered["text_by_id"]["freshtxt"]
    assert ("FINAL REPORT" if state == "complete" else "FAILED REPORT") in badge
    assert "old" in badge and "STALE" not in badge
    assert "stale" not in rendered["class_by_id"]["fresh"]
    assert "5 / 5" in rendered["by_id"]["tiles"]
    assert "final report" in rendered["by_id"]["banner"].lower() or state == "failed"
    assert path.read_bytes() == original


@pytest.mark.parametrize("age,state", [(30, "running"), (9000, "running"),
                                       (-10000, "running"), (-10000, "complete")])
def test_running_and_invalid_clock_keep_original_heartbeat_rules(tmp_path, age, state):
    root = tmp_path / "store"
    root.mkdir()
    now = time.time()
    body = {"schema": loop_status.STATUS_SCHEMA, "state": state,
            "generated_at": datetime.fromtimestamp(now - age, timezone.utc).isoformat(),
            "stale_after_s": 180, "step": "[lane0] measuring A/B on the device"}
    (root / "loop-status.json").write_text(json.dumps(body))
    wire, _ = loop_status.snapshot(root, now=now)
    expected = "malformed" if age < 0 else "fresh" if age == 30 else "stale"
    assert wire["freshness_state"] == expected
    rendered = _run(_page_js(), wire, tmp_path, ["render"])
    assert not rendered["threw"]
    assert "REPORT" not in rendered["text_by_id"]["freshtxt"]
    if age == 9000:
        assert "STALE" in rendered["text_by_id"]["freshtxt"]
        assert wire["display_step"].startswith("Last reported step:")
    elif age < 0:
        assert wire["display_step"] is None
    else:
        assert wire["display_step"] == body["step"]


def test_completed_child_does_not_make_running_router_terminal(sources, tmp_path, producer):
    _canonical, _router, child, active, _routing = sources
    producer.write(child, state="complete", epoch="child", campaign_id="ak-loop",
        anchor_commit="b" * 40, surface="serving:fixture", pairs=5, noise_floor_pct=7.8,
        target={"selected_id": active["selected_id"]},
        batch={"output_dir": active["batch_dir"], "pid": active["pid"]},
        step="[lane0] measuring A/B on the device", stale_after_s=180)
    wire = loop_status.snapshot()[0]
    assert wire["serial"]["child"]["joined"]
    assert wire["loop"]["state"] == "running"
    assert wire["serial"]["child"]["loop"]["state"] == "complete"
    rendered = _run(_page_js(), wire, tmp_path, ["render"])
    assert not rendered["threw"]
    assert rendered["text_by_id"]["freshtxt"].startswith("fresh")
    assert rendered["text_by_id"]["hdr-state"] == "running"
    assert rendered["text_by_id"]["hdr-step"] == "Run complete — final report"
    assert "RUNNING" in rendered["by_id"]["serial"]
