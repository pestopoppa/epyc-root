"""Hosted pure fixture checks; no model, dataset download, or transport."""
import os
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
research = here / "payload" / "research"
sys.path[:0] = [str(research), str(research / "scripts" / "benchmark")]
sys.path.append(str(here.parents[2] / "research" / "scripts" / "benchmark"))
os.environ["EPYC_ROOT"] = sys.argv[2]
import pyarrow
import pyarrow.parquet
import pytest

tests = [research / "scripts" / "benchmark" / name for name in
         ("test_beam_adapter.py", "test_judge_beam_run.py", "test_beam_judge_provenance.py")]
raise SystemExit(pytest.main([*[str(path) for path in tests], "-c", "/dev/null",
                             "--rootdir", str(research), "--noconftest",
                             "--import-mode=importlib", "--junitxml=" + sys.argv[1], "-q"]))
