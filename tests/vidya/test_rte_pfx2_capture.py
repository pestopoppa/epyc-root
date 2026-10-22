"""VB-RTEPFX2-WIRE: probe.json + RUN_HEADER.json -> chunk-kv carrier; fixture grades."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import chunk_kv, rte_pfx2_capture as m  # noqa: E402

WHEN = "2026-10-22T10:00:00Z"
WIN = {"window_id": "w-1", "region_lock_claim": "claim-1",
       "start_utc": "2026-10-22T09:00:00Z", "end_utc": "2026-10-22T09:40:00Z"}
EXPECTED = 1000
HEADER = {"schema": "epyc.rte_pfx2.header.v1", "argv": ["/k/llama-server", "-m", "/m/Q.gguf", "-np", "4"],
          "cache_ram_mib": "4096", "prefix_sha256": "b" * 64, "n": 4, "trials": 2, "seed": 1,
          "binary_mtime": "Wed Oct 21 10:00:00 2026"}


def trial(i, arm, sib_cache, sib_prompt):
    rows = [{"idx": 0, "prompt_n": 1100, "cache_n": 0, "ttft_ms": 1.0, "id_slot": 0}]
    rows += [{"idx": k + 1, "prompt_n": sib_prompt, "cache_n": sib_cache, "ttft_ms": 1.0, "id_slot": k + 1}
             for k in range(3)]
    return {"trial": i, "arm": arm, "rows": rows, "slots_during": {},
            "summary": {"total_uncached_prompt_tokens": sum(r["prompt_n"] for r in rows),
                        "siblings_on_cached_prefix": 3 if sib_cache >= 900 else 0}}


def probe():
    res = []
    for i in range(2):
        res += [trial(i, "simultaneous", 0, 1100), trial(i, "hold_first_tok", 0, 1100),
                trial(i, "hold_first_end", 1010, 90)]
    return {"schema": "epyc.rte_pfx2.v1", "server": "http://x", "n": 4, "props": {},
            "expected_prefix_tokens": EXPECTED, "hit_fraction": 0.9, "results": res}


def files(tmp_path, pr=None, hd=None):
    (tmp_path / "probe.json").write_text(json.dumps(pr or probe()))
    (tmp_path / "RUN_HEADER.json").write_text(json.dumps(hd or HEADER))
    return tmp_path / "probe.json", tmp_path / "RUN_HEADER.json"


def write(tmp_path, **kw):
    p, h = files(tmp_path, kw.pop("pr", None), kw.pop("hd", None))
    return m.write_belief_measurements(tmp_path, run_id="rtepfx2", producer="t", probe_path=p,
                                       header_path=h, role="frontdoor", window=WIN, emitted_at=WHEN)


def test_round_trip_grades_and_values(tmp_path):
    nat = chunk_kv.native_rows(write(tmp_path))
    assert len(nat) == 6
    for n in nat:
        assert ct.grade(chunk_kv.project(n)) == ("Witnessed", "Attested", [])
    by = {(n["row"]["extra"]["kind"], n["row"]["extra"]["detail"]["arm"]): n["row"] for n in nat}
    assert by[("uncached_prompt_tokens", "simultaneous")]["value"] == 4400
    assert by[("uncached_prompt_tokens", "hold_first_end")]["value"] == 1370
    assert by[("prefix_hit_share", "simultaneous")]["value"] == 0.0
    assert by[("prefix_hit_share", "hold_first_end")]["value"] == pytest.approx(1.0)  # capped at the prefix
    assert by[("prefix_hit_share", "simultaneous")]["category"] == "BASELINE"
    assert by[("prefix_hit_share", "hold_first_tok")]["category"] == "CANDIDATE"
    r = by[("prefix_hit_share", "hold_first_end")]
    assert r["extra"]["served_pin"]["model"] == "Q.gguf" and r["extra"]["window"] == WIN
    assert r["extra"]["detail"]["sibling_cache_n"] == [1010] * 6 and r["reps"] == 6000
    assert by[("uncached_prompt_tokens", "hold_first_tok")]["reps"] == 2
    assert len(chunk_kv.frames_for_sidecar(tmp_path / chunk_kv.SIDECAR_NAME, as_of="2026-10-22T11:00:00Z")) >= 6


def test_missing_server_timings_refused(tmp_path):
    pr = probe(); pr["results"][0]["rows"][1]["prompt_n"] = -1
    with pytest.raises(m.CaptureError):
        write(tmp_path, pr=pr)
    assert not (tmp_path / chunk_kv.SIDECAR_NAME).exists()


@pytest.mark.parametrize("hd", [{**HEADER, "schema": "x"}, {**HEADER, "argv": ["/k/s"]},
                                {k: v for k, v in HEADER.items() if k != "binary_mtime"}])
def test_bad_header_refused(tmp_path, hd):
    with pytest.raises(m.CaptureError):
        write(tmp_path, hd=hd)


def test_missing_window_field_refused(tmp_path):
    p, h = files(tmp_path)
    with pytest.raises(m.CaptureError):
        m.write_belief_measurements(tmp_path, run_id="r", producer="t", probe_path=p, header_path=h,
                                    role="frontdoor", window={"window_id": "w"}, emitted_at=WHEN)


def test_arm_missing_refused_and_tamper(tmp_path):
    pr = probe(); pr["results"] = [r for r in pr["results"] if r["arm"] != "hold_first_end"]
    with pytest.raises(m.CaptureError):
        write(tmp_path, pr=pr)
    sc = write(tmp_path)
    Path(json.loads(sc.read_text().splitlines()[0])["results_path"]).write_text("{}")
    assert ct.grade(chunk_kv.project(chunk_kv.native_rows(sc)[0]))[:2] != ("Witnessed", "Attested")
