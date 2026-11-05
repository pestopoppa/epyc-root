"""ROWFLOW-RESIDENCY-GPUQUIET-CPU: the dry-run VRAM residency check applies to rows that execute on the MI210,
not to rows that hold it only to keep it quiet (gpu_use "quiet-only")."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "rowflow"))
import rowflow  # noqa: E402


def test_gpu_row_requires_residency():
    assert rowflow.gpu_residency_required({"lane": "gpu"}, "mi210_0,184-191")


def test_quiet_only_row_is_exempt():
    assert not rowflow.gpu_residency_required({"lane": "gpu", "gpu_use": "quiet-only"}, "mi210_0,48-95,144-191")


def test_cpu_regions_never_require_residency():
    assert not rowflow.gpu_residency_required({"lane": "cpu"}, "48-95,144-191")


def test_missing_row_with_gpu_region_requires_residency():
    assert rowflow.gpu_residency_required(None, "mi210_0")
