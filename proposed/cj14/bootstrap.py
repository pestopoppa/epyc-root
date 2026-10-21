"""Only exact offline typed-redundancy leaf, fake primitives; no model transport."""
import sys
from pathlib import Path
import pytest
app = Path(sys.argv[2])
sys.path.insert(0, str(app))
raise SystemExit(pytest.main([str(app / "tests/unit/test_typed_decisions_judge_redundancy.py"), "-c", "/dev/null", "--rootdir", str(app), "--noconftest", "--import-mode=importlib", "--junitxml=" + sys.argv[1], "-q"]))
