import pytest

import campaign_smoke


def test_default_and_explicit_calibration_limits():
    assert campaign_smoke.select_memory_limit([]) == 8 * 1024**3
    assert campaign_smoke.select_memory_limit(["--calibration-smoke48"]) == 48 * 1024**3
    with pytest.raises(ValueError):
        campaign_smoke.select_memory_limit(["--unknown"])


def test_smoke_uses_only_control_row(tmp_path, monkeypatch):
    import json

    import campaign_job

    control = {"id": "synthetic-control"}
    (tmp_path / "CONTROL-PRIVATE.json").write_text(json.dumps(control))
    monkeypatch.setattr(campaign_job, "D", tmp_path)
    assert campaign_job.rows({}, True) == [control]
