"""Whole native modules; no AST extraction, mocks beyond original test bodies, or dataset hydration."""
import importlib, os, sys
from pathlib import Path
workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
research = workspace / "research"
root = workspace / "context"
os.environ["EPYC_ROOT"] = str(root)
sys.path[:0] = [str(research), str(research / "scripts/benchmark")]
names = ["scripts.benchmark.test_score_tulving_run", "scripts.benchmark.test_tulving_srs_comparison"]
for name in names:
    module = importlib.import_module(name)
    expected = research / (name.replace(".", "/") + ".py")
    if Path(module.__file__).resolve() != expected.resolve():
        raise RuntimeError("native module resolved outside exact research checkout")
import pytest
raise SystemExit(pytest.main(["--pyargs", *names, "-c", "/dev/null", "--rootdir", str(workspace), "--noconftest", "--import-mode=importlib", "-o", "consider_namespace_packages=True", "-o", "addopts=", "-p", "no:cacheprovider", "-q", "--junitxml=" + sys.argv[1]]))
