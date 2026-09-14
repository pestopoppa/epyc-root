"""Original status writer -> joined child reader -> existing page rendering."""
from datetime import datetime, timezone
import time

import pytest

from dashboard import loop_status
from tests import test_dashboard_serial_loop as serial_fixtures
from tests.test_dashboard_runtime_js import _page_js, _run

producer = serial_fixtures.producer
sources = serial_fixtures.sources
_rewrite = serial_fixtures._rewrite


def _runtime(now):
    return {"status": "original_frame_ready", "reason": "", "calibration_launches": 800,
            "selected_recipe": "threads=96 topology=taskset -c 0-95 · GLM depth3",
            "selected_execution_digest": "d" * 64, "selected_recipe_reference": None,
            "progress": {"observed_at": datetime.fromtimestamp(now - 3600, timezone.utc).isoformat(),
                "operation": "preparation", "phase": "calibration", "frame_digest": "f" * 64,
                "completed_launches": 17, "launch_limit": 800, "limit_is_upper_bound": False,
                "failed_launches": 2, "pending": ["aa", 8, "candidate"]}}


def _write(producer, child, row):
    old = producer.read(child)
    producer.write(child, state="running", epoch="child", campaign_id="ak-loop",
        anchor_commit="b" * 40, surface="serving:fixture", pairs=5, noise_floor_pct=7.801,
        target=old["target"], batch=old["batch"], runtime_preparation=row)


def test_original_progress_age_and_selection_survive_fresh_router_heartbeat(sources, producer, tmp_path):
    _canonical, _router, child, _active, _routing = sources
    now = time.time()
    row = _runtime(now)
    row["selected_recipe_reference"] = {"locator": "/original/retained-selection",
                                       "sha256": "a" * 64, "verified": True}
    _write(producer, child, row)
    wire = loop_status.snapshot(now=now)[0]
    view = wire["serial"]["child"]["runtime_preparation"]
    assert wire["freshness_state"] == wire["serial"]["child"]["freshness_state"] == "fresh"
    assert view["progress_age_s"] == 3600
    assert view["body"] == row
    rendered = _run(_page_js(), wire, tmp_path, ["render"])
    assert rendered["threw"] == []
    card = rendered["by_id"]["runtime-preparation"]
    assert "17 valid launches of 800" in card and "2 retained failed launches" in card
    assert "threads=96" in card and "GLM depth3" in card
    assert "1h" in card or "60m" in card
    assert "<details>" in card and "/original/retained-selection" in card
    assert rendered["by_id"]["champ"] and rendered["by_id"]["know"]
    # A new publisher timestamp does not move the old phase/count observation.
    _write(producer, child, row)
    later = loop_status.snapshot(now=now + 10)[0]["serial"]["child"]["runtime_preparation"]
    assert later["progress_age_s"] == 3610
    assert later["body"]["progress"] == row["progress"]


@pytest.mark.parametrize("case", ["not_reported", "clock_skew", "malformed", "unjoined"])
def test_missing_unknown_and_foreign_progress_never_become_current(sources, producer, tmp_path, case):
    _canonical, _router, child, _active, _routing = sources
    now = time.time()
    row = _runtime(now)
    if case == "not_reported":
        row["progress"] = None
    elif case == "clock_skew":
        row["progress"]["observed_at"] = datetime.fromtimestamp(now + 3600, timezone.utc).isoformat()
    elif case == "malformed":
        row["progress"]["completed_launches"] = True
    _write(producer, child, row)
    if case == "unjoined":
        _rewrite(child / "loop-status.json", lambda b: b["batch"].update(pid=999999))
    wire = loop_status.snapshot(now=now)[0]
    rendered = _run(_page_js(), wire, tmp_path, ["render"])
    assert rendered["threw"] == []
    card = rendered["by_id"]["runtime-preparation"]
    expected = {"not_reported": "No runtime launch progress reported",
                "clock_skew": "wall-clock skew; age unknown",
                "malformed": "Runtime progress unavailable"}
    if case == "unjoined":
        assert not wire["serial"]["child"]["joined"] and not card
    else:
        assert expected[case] in card


@pytest.mark.parametrize("key,value", [("runtime_preparation", []), ("status", []),
    ("selected_recipe", 1), ("selected_execution_digest", "bad"),
    ("selected_recipe_reference", {"locator": "/x", "sha256": "a"*64, "verified": "yes"})])
def test_malformed_small_optional_contract_is_visible(key, value):
    row = _runtime(time.time())
    if key == "runtime_preparation":
        row = value
    else:
        row[key] = value
    view = loop_status._runtime_preparation({"runtime_preparation": row})
    assert view["state"] == "malformed" and view["body"] is None
