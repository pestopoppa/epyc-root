import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import phase_a_replay as pa  # noqa: E402


def mk(flags, rid, smoke, grant, end, rc=0, pub="2026-11-05T10:00:00Z", first="2026-11-05T10:05:00Z"):
    d = Path(flags) / "dryrun" / rid
    d.mkdir(parents=True)
    (d / "PASS.json").write_text(json.dumps({"elapsed_s": smoke, "first_unit_at": first}))
    (d / "ended").write_text("rc=75 time=2026-01-01T00:00:00Z reason=smoke\n")  # smoke end: must be ignored
    g = Path(flags) / "grants"
    g.mkdir(exist_ok=True)
    (g / f"{rid}.ended").write_text(f"rc={rc} time={end} reason=x\njob_id={rid}\nstarted={grant}\n")
    (Path(flags) / "ready").mkdir(exist_ok=True)
    (Path(flags) / "ready" / f"{rid}.json").write_text(json.dumps({"published_at": pub, "lane": "cpu"}))


def test_fraction_and_stop_rule():
    f = tempfile.mkdtemp()
    mk(f, "a", 60, "2026-11-05T11:00:00Z", "2026-11-05T12:00:00Z")       # 60/(60+3600)
    mk(f, "b", 60, "2026-11-05T13:00:00Z", "2026-11-05T14:00:00Z")
    r = pa.replay(pa.load_rows(f))
    assert r["n_rows"] == 2 and r["verdict"].startswith("STOP")
    assert r["rows"][0]["publish_to_first_unit_s"] == 300.0
    assert r["saved_seconds_total"] == 120.0


def test_proceed_when_smoke_dominates_and_failures_excluded():
    f = tempfile.mkdtemp()
    mk(f, "a", 600, "2026-11-05T11:00:00Z", "2026-11-05T11:10:00Z")      # 0.5
    mk(f, "bad", 600, "2026-11-05T11:00:00Z", "2026-11-05T11:10:00Z", rc=75)
    r = pa.replay(pa.load_rows(f))
    assert r["n_rows"] == 1 and r["verdict"].startswith("PROCEED")


def test_missing_records_skipped_and_limit_takes_latest():
    f = tempfile.mkdtemp()
    (Path(f) / "dryrun" / "empty").mkdir(parents=True)
    for i in range(5):
        mk(f, f"r{i}", 10, f"2026-11-05T0{i}:00:00Z", f"2026-11-05T0{i}:30:00Z")
    r = pa.replay(pa.load_rows(f), limit=2)
    assert [x["id"] for x in r["rows"]] == ["r3", "r4"]
    assert pa.replay([])["verdict"] == "NO DATA"
