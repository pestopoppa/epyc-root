"""Ensure canonical normal/cutoff qualification fixture imports as ordinary project code."""
from pathlib import Path
import sys

D = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(D))
from qualification.qual_entry import qualified_first_request, run


def test_real_qual_entry_and_first_request_controls_are_callable():
    assert callable(run)
    assert callable(qualified_first_request)
