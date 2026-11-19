"""sliders_phase0_job: the server-up record must count as the keeper smoke's first REAL progress (numeric field outside the
bookkeeping keys), because the first question outlasts first_progress_s on a smoke quarter
(sliders-phase0-fb5-coder30b-20261109: smoke FAIL, "1 new record(s) ignored: no numeric field outside the bookkeeping keys")."""
import importlib.util
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
os.environ.setdefault("FILLER_CPUS", "0")
PINS = Path("/mnt/raid0/llm/datasets/financebench-20261109/fb5_pins.json")
pytestmark = pytest.mark.skipif(not PINS.exists(), reason="FB5 pins not on this host")

sys.path.insert(0, str(ROOT / "scripts" / "coordination" / "rowflow"))
import rowflow as rf  # noqa: E402

_S = importlib.util.spec_from_file_location("sliders_job_t", ROOT / "scripts" / "row_jobs" / "sliders_phase0_job.py")
J = importlib.util.module_from_spec(_S)
_S.loader.exec_module(J)

REPLY = {"choices": [{"message": {"content": "OK"}}], "usage": {"completion_tokens": 2}}
IDENT = {"model_sha256": "x", "ts": "2026-11-09T00:00:00Z"}


def test_preflight_record_is_real_progress_for_the_keeper():
    rec = J.preflight_record(REPLY, IDENT, 7.04)
    assert rf._has_measurement(rec) is True
    assert rec["server_ready_s"] == 7.0 and rec["preflight_tokens"] == 2 and rec["n_questions_planned"] == len(J.PINS)


def test_old_string_only_record_was_not_progress():
    old = {"kind": "preflight", "unit": "preflight", "reply": "OK", "identity": IDENT, "ts": "2026-11-09T00:00:00Z"}
    assert rf._has_measurement(old) is False


def test_preflight_record_tolerates_missing_usage_and_none_content():
    rec = J.preflight_record({"choices": [{"message": {"content": None}}]}, IDENT, 1.0)
    assert rec["preflight_tokens"] == 0 and rec["reply"] == ""
