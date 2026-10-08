"""Pure temporary-fixture direct-library admission boundaries."""
import importlib.util
from pathlib import Path
import pytest

_spec = importlib.util.spec_from_file_location("m12f_capture_candidate", Path(__file__).with_name("tulving_episodic_capture.py"))
capture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(capture)

@pytest.mark.parametrize("version,definition", [(3,"epyc_v3_gt_ge2_partial_zero"),(3,None),(2,"unknown"),(2,"epyc_v3_gt_ge2_partial_zero"),(4,"v2_native")])
def test_direct_writer_refuses_unadmitted_cas_without_sidecar(tmp_path, version, definition):
    scored = tmp_path / "fake-scored.json"
    scored.write_text("{}")
    summary = {"scorer_version": version}
    if definition is not None:
        summary["cas_definition"] = definition
    with pytest.raises(capture.CaptureError, match="separate human protocol admission"):
        capture.write_belief_measurements(scored, summary=summary, run_id="fake", producer="fixture", arm="none", variant="Udefault_Sdefault_seed0", chapters=20)
    assert list(tmp_path.iterdir()) == [scored]

@pytest.mark.parametrize("definition", [None,"v2_native"])
def test_v2_reaches_existing_gold_binding_guard(tmp_path, definition):
    scored = tmp_path / "fake-scored.json"
    scored.write_text("{}")
    summary = {"scorer_version": 2}
    if definition is not None:
        summary["cas_definition"] = definition
    with pytest.raises(capture.CaptureError, match="gold_binding"):
        capture.write_belief_measurements(scored, summary=summary, run_id="fake", producer="fixture", arm="none", variant="Udefault_Sdefault_seed0", chapters=20)
    assert list(tmp_path.iterdir()) == [scored]
