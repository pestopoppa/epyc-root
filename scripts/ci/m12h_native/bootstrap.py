"""Original offhost eight-control module, exact Research checkout only."""
import importlib, os, sys
from pathlib import Path
workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
research = workspace / "research"
sys.path.insert(0, str(research))
name = "scripts.benchmark.test_m12h_ast_isolated"
module = importlib.import_module(name)
if Path(module.__file__).resolve() != (research / "scripts/benchmark/test_m12h_ast_isolated.py").resolve():
    raise RuntimeError("selected module is outside exact Research checkout")
import pytest
raise SystemExit(pytest.main(["--pyargs", name, "-c", "/dev/null", "--rootdir", str(workspace), "--noconftest", "--import-mode=importlib", "-o", "consider_namespace_packages=True", "-o", "addopts=", "-p", "no:cacheprovider", "-q", "--junitxml=" + sys.argv[1]]))
