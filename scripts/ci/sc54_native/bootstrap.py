"""Run only the two complete ROOT SC54 source modules; no APP or conftest."""
import importlib
import os
import sys
from pathlib import Path

workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
recipe = workspace / "recipe"
sys.path[:0] = [str(recipe), str(recipe / "scripts" / "vidya")]
modules = (
    "tests.vidya.test_sc54_qwen4exp_quality_adapter",
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
