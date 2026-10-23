import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "mem_sampler", Path(__file__).resolve().parents[1] / "scripts/utils/mem_sampler.py")
ms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ms)

MEM = "MemTotal: 10 kB\nMemAvailable: 500 kB\nAnonPages: 100 kB\nCached: 200 kB\nMlocked: 7 kB\n"
PSI = "some avg10=1.50 avg60=0.50 avg300=0.10 total=9\nfull avg10=0.25 avg60=0.00 avg300=0.00 total=1\n"


def test_sample_fields(tmp_path):
    (tmp_path / "m").write_text(MEM)
    (tmp_path / "p").write_text(PSI)
    r = ms.sample(tmp_path / "m", tmp_path / "p", now=0)
    assert r["MemAvailable_kB"] == 500 and r["Mlocked_kB"] == 7 and "MemTotal_kB" not in r
    assert r["psi_some_avg10"] == 1.5 and r["psi_full_avg10"] == 0.25
    assert r["ts"] == "1970-01-01T00:00:00Z"


def test_missing_psi_recorded_not_zero(tmp_path):
    (tmp_path / "m").write_text(MEM)
    r = ms.sample(tmp_path / "m", tmp_path / "nope", now=0)
    assert "psi_some_avg10" not in r and r["missing"]


def test_rotation(tmp_path):
    log = tmp_path / "l.jsonl"
    for i in range(20):
        ms.append(log, {"i": i, "pad": "x" * 50}, 200, 2)
    assert log.exists() and (tmp_path / "l.jsonl.1").exists() and (tmp_path / "l.jsonl.2").exists()
    assert not (tmp_path / "l.jsonl.3").exists()
    json.loads(log.read_text().splitlines()[-1])


def test_once_live(tmp_path, monkeypatch):
    monkeypatch.setenv("MEM_SAMPLER_LOG", str(tmp_path / "t.jsonl"))
    assert ms.main(["--once"]) == 0
    assert "MemAvailable_kB" in json.loads((tmp_path / "t.jsonl").read_text())
