"""Unit tests for scripts/research/intake_dive_digests.py."""
import importlib.util
from pathlib import Path

import yaml

_P = Path(__file__).resolve().parents[1] / "scripts" / "research" / "intake_dive_digests.py"
_spec = importlib.util.spec_from_file_location("intake_dive_digests", _P)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def _e(n, date="2026-10-21", via="expansion", ver="dive-verified", **kw):
    d = {"id": f"intake-{n}", "title": f"T{n}", "url": f"u{n}", "ingested_date": date,
         "discovered_via": via, "verification": ver, "verdict": "worth_investigating",
         "categories": ["kv_cache"]}
    d.update(kw)
    return d


INDEX = [
    _e(10, via="input"), _e(11), _e(12, ver="stage1-unverified"),
    _e(13, via="input", key_claims=["see intake-5 and intake-6#02"],
       claim_anchors=[{"claim_index": 0, "locator": "a.md:1", "quote": "q"}],
       claim_corrections=[{"claim_index": 0, "effect": "narrowed", "note": "n"}],
       dive_corrections="fixed vs intake-7", handoffs_updated=["handoffs/active/x.md"]),
    _e(14, date="2026-10-22", ver="dive-overturned"),
]


def test_grouping_splits_on_date_and_new_input_batch():
    runs = mod.group_runs(mod.dive_entries(INDEX))
    assert [[mod._num(e) for e in r] for r in runs] == [[10, 11], [13], [14]]
    assert mod.run_slug(runs[0]) == "2026-10-21-intake-10-11"


def test_render_cites_record_form_and_carries_dive_fields():
    docs = mod.build(INDEX)
    text = docs["2026-10-21-intake-13-13"]
    assert "intake-5#record" in text and "intake-6#02" in text and "intake-7#record" in text
    assert "intake-12" not in text
    assert "anchor `a.md:1`" in text and "*narrowed*" in text and "handoffs/active/x.md" in text
    import re
    assert not re.search(r"intake-\d+(?![\d#])", text)


def test_idempotent(tmp_path):
    idx = tmp_path / "i.yaml"
    idx.write_text(yaml.safe_dump(INDEX))
    out = tmp_path / "o"
    assert mod.main(["--index", str(idx), "--out", str(out)]) == 0
    first = {p.name: p.read_text() for p in out.iterdir()}
    assert mod.main(["--index", str(idx), "--out", str(out), "--check"]) == 0
    assert {p.name: p.read_text() for p in out.iterdir()} == first


def test_long_digit_runs_are_grouped():
    n = 2_103_402_800 * 10**9 + 155_709_514  # an X status id
    assert mod._safe(f"status {n} x") == "status 2_103_402_800_155_709_514 x"
    assert mod._safe("abc 12345678901 x") == "abc 12345678901 x"
