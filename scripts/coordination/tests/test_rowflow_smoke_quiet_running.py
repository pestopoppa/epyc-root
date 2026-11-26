"""A live quiet quarter protects the host from CPU smokes, not the GPU queue."""
import os
from unittest import mock

import pytest

import test_rowflow_arming_park as harness
import rowflow as rf


@pytest.mark.parametrize("quiet", [
    {"quiet_sensitive": True},
    {"requires_quiet_host": True},
    {"shape": "quiet-host"},
    {"admission_class": "block-timing-quiet"},
    {"owner": "autokernel"},
])
def test_tick_holds_cpu_smokes_and_starts_gpu(quiet):
    fx = harness.Fixture(methodName="runTest")
    fx.setUp()
    try:
        rid = "quiet-row"
        row = fx.row(rid, 10, [{"q0"}], "quarter", regions="0-23")
        row.update(quiet)
        rf.atomic_json(rf.ready_path(fx.flags, rid), row)
        end = "2026-11-26T14:00:00Z"
        harness_path = os.path.join(fx.flags, "grants", rid + ".grant")
        with open(harness_path, "w") as f:
            f.write(f"regions=0-23 holds=q0 end={end}\n")
        for i in range(4):
            rf.atomic_json(os.path.join(rf.dry_dir(fx.flags, f"cpu-{i}"), "SMOKE-QUEUED.json"), {})
        rf.atomic_json(os.path.join(rf.dry_dir(fx.flags, "gpu-smoke"), "GPU-SMOKE-QUEUED.json"), {})
        with mock.patch.object(rf, "heal_grants", side_effect=lambda flags, grants, *a: grants), \
                mock.patch.object(rf, "hold_orphans", return_value=[]), \
                mock.patch.object(rf, "start_gpu_batch", return_value=True) as gpu, \
                mock.patch.object(rf.subprocess, "Popen") as popen:
            fx.tick()
        assert gpu.called
        popen.assert_not_called()
        for i in range(4):
            assert os.path.exists(os.path.join(rf.dry_dir(fx.flags, f"cpu-{i}"), "SMOKE-QUEUED.json"))
            assert any(f"SMOKE-WAIT cpu-{i}: quiet timing row {rid} running until {end}" in line for line in fx.lines)
    finally:
        fx.tearDown()


def test_nonquiet_grant_does_not_hold_cpu_smokes(tmp_path):
    for i in range(4):
        rf.atomic_json(os.path.join(rf.dry_dir(str(tmp_path), f"cpu-{i}"), "SMOKE-QUEUED.json"), {})
    free = rf.expand(set(rf.QUARTERS)) | set(rf.POCKET_TOKENS)
    assert rf.place_smokes(str(tmp_path), free, dry=True)
