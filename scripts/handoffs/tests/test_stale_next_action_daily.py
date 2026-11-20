"""C6 daily sample: --daily records at most one sample per UTC day; refresh_hub_view.sh calls it every pass."""
import datetime as dt
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import stale_next_action as S  # noqa: E402


def test_has_sample_today(tmp_path):
    led = tmp_path / "c6.jsonl"
    assert not S.has_sample_today(str(led))
    led.write_text(json.dumps({"at": "2020-01-01T00:00Z"}) + "\nnot json\n")
    assert not S.has_sample_today(str(led))
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    with open(led, "a") as fh:
        fh.write(json.dumps({"at": today}) + "\n")
    assert S.has_sample_today(str(led))


def test_daily_flag_skips_second_sample(tmp_path, monkeypatch):
    led = tmp_path / "c6.jsonl"
    calls = []
    monkeypatch.setattr(S, "compare_generated", lambda: calls.append(1) or {
        "at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "rows": 0, "agree": 0, "fresher": 0,
        "agree_or_fresher_share": None, "generated_lint_failing": [], "missing_row_domain_headers": [], "disagree": []})
    for _ in range(3):
        monkeypatch.setattr(sys, "argv", ["x", "--compare-generated", "--daily", "--quiet", "--ledger", str(led)])
        S.main()
    assert len(calls) == 1 and len(led.read_text().splitlines()) == 1


def test_hub_refresh_schedules_the_daily_sample():
    sh = (HERE.parents[1] / "scripts/dashboard/refresh_hub_view.sh").read_text()
    assert "stale_next_action.py" in sh and "--compare-generated --daily" in sh
