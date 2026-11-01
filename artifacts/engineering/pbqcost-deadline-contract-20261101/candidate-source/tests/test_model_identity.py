"""Bounded read-only edge identity check; no GGUF full-file hashing or model invocation."""
import sys
from pathlib import Path

D = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(D))
from model_identity import verify_model_identity


def test_model_edges_match_recorded_identity():
    result = verify_model_identity()
    assert result['verified'] is True
    assert len(result['models']) == 2
