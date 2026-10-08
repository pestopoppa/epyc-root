"""Run the two whole ROOT reader/ingest modules with the exact stdlib APP writer; no APP project or conftest."""
import importlib
import os
import sys
from pathlib import Path

workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
recipe = workspace / "recipe"
writer = workspace / "app" / "src/runtime/hg5_request_event.py"
if os.environ.get("HG5_WRITER_SOURCE") != str(writer):
    raise RuntimeError("explicit exact APP writer source path required")
sys.path[:0] = [str(recipe), str(recipe / "scripts" / "vidya")]
modules = (
    "tests.test_hg5_request_event_reader",
    "tests.vidya.test_ingest_sources",
)
for name in modules:
    module = importlib.import_module(name)
    expected = (recipe / name.replace(".", "/")).with_suffix(".py")
    if Path(module.__file__).resolve() != expected.resolve():
        raise RuntimeError("selected ROOT module resolved outside exact checkout")
import pytest
raise SystemExit(pytest.main(["--pyargs", *modules, "-c", "/dev/null", "--rootdir", str(workspace),
    "--noconftest", "--import-mode=importlib", "-o", "consider_namespace_packages=True",
    "-o", "addopts=", "-p", "no:cacheprovider", "-q", "--junitxml=" + sys.argv[1]]))
