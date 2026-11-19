import json

import pytest

from scripts.vidya.canary.kvu19_context import MATRIX, SIDECAR, completed_capture


@pytest.mark.parametrize(("smoke", "partial", "count", "message"), [
    (True, False, 20, "non-smoke"),
    (False, True, 20, "partial"),
    (False, False, 19, "20 completed launches"),
    (False, False, 21, "20 completed launches"),
])
def test_canary_rejects_ineligible_completion_record(tmp_path, smoke, partial, count, message):
    sidecar = tmp_path / SIDECAR
    sidecar.touch()
    (tmp_path / "result.json").write_text(json.dumps({
        "schema": "kvu19a2.repeat-diagnostic.v1", "run_id": "fixture", "smoke": smoke,
        "measurement": False, "runs": [{}] * count,
    }))
    if partial:
        (tmp_path / "partial-result.json").touch()
    with pytest.raises(ValueError, match=message):
        completed_capture(sidecar)


def test_canary_rejects_20_launch_result_with_missing_native_row(tmp_path):
    sidecar = tmp_path / SIDECAR
    sidecar.write_text("{}\n" * (len(MATRIX) - 1))
    (tmp_path / "result.json").write_text(json.dumps({
        "schema": "kvu19a2.repeat-diagnostic.v1", "run_id": "fixture", "smoke": False,
        "measurement": False, "runs": [{}] * len(MATRIX),
    }))
    (tmp_path / "kvu19a2-native.json").write_text(json.dumps({
        "schema": "kvu19a2.native-run.v1", "run_id": "fixture", "observations": [{}] * len(MATRIX),
    }))
    with pytest.raises(ValueError, match="bind 20 native observations and rows"):
        completed_capture(sidecar)
