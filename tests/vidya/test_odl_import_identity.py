"""ODL's CLI and package spellings must reuse the actual registered callable."""
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]

@pytest.mark.parametrize("first", ["adapters.odl_model_gated", "scripts.vidya.adapters.odl_model_gated"])
def test_odl_import_orders_reuse_initialized_module_and_refuse_different_function(first):
    script = r'''
import importlib
from pathlib import Path
import sys
sys.path.insert(0, str(Path.cwd() / "scripts" / "vidya"))
first = importlib.import_module(sys.argv[1])
other = ("scripts.vidya.adapters.odl_model_gated"
         if sys.argv[1] == "adapters.odl_model_gated" else "adapters.odl_model_gated")
second = importlib.import_module(other)
if sys.argv[1] == "adapters.odl_model_gated":
    from scripts.vidya.adapters import odl_model_gated as package_import
    assert package_import is first
    import scripts.vidya.adapters.odl_model_gated as dotted_import
    assert dotted_import is first
else:
    from adapters import odl_model_gated as direct_import
    assert direct_import is first
    import adapters.odl_model_gated as dotted_import
    assert dotted_import is first
from ingest_sources import SOURCES
import claim_tuple as ct
loaded = SOURCES["odl-unlimited-ocr-run"].load()
assert first is second is loaded
project = first.project_unlimited_ocr_run
assert ct.registered()["odl-unlimited-ocr-run"] is project
assert ct.register("odl-unlimited-ocr-run", source_class="measurement")(project) is project

def impostor(native):
    return project(native)
try:
    ct.register("odl-unlimited-ocr-run", source_class="measurement")(impostor)
except ct.ProjectionError as exc:
    assert "already registered" in str(exc)
else:
    raise AssertionError("different function registered under existing ODL projection")
assert ct.registered()["odl-unlimited-ocr-run"] is project
assert ct.source_classes()["odl-unlimited-ocr-run"] == "measurement"
'''
    result = subprocess.run([sys.executable, "-c", script, first], cwd=ROOT,
                            text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
