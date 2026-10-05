"""Regression guard for the corrupt/wrong-scale baseline bug.

Background: between 2026-05-27 and 2026-05-31 the autopilot safety gate ran with
an in-memory baseline.quality of 9.900 (and per-suite coder 9.900) — physically
impossible on the 0-3 quality scale. Every trial, including genuinely-good q=2.4
ones, failed the regression gate ("Quality regression: 2.400 vs baseline 9.900")
and was force-reverted for ~160 trials. Baseline.load() now rejects any quality
outside [0, QUALITY_MAX] and falls back to a safe default, so a corrupt baseline
file can never silently poison the gate again.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "autopilot"))

from safety_gate import Baseline, QUALITY_MAX  # noqa: E402


def _write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "autopilot_baseline.yaml"
    p.write_text(body)
    return p


def test_corrupt_overscale_quality_falls_back_to_default(tmp_path):
    p = _write(tmp_path, "quality: 9.9\nreliability: 0.9\nper_suite_quality: {}\n")
    b = Baseline.load(p)
    assert b.quality == Baseline().quality  # default, NOT 9.9
    assert b.quality <= QUALITY_MAX


def test_corrupt_overscale_per_suite_dropped_to_none(tmp_path):
    # coder=9.9 is impossible (per-suite max 3.0) → dropped to None so the
    # per-suite regression gate stays disabled; valid math=2.5 is preserved.
    p = _write(
        tmp_path,
        "quality: 1.16\nper_suite_quality:\n  coder: 9.9\n  math: 2.5\n",
    )
    b = Baseline.load(p)
    assert b.per_suite_quality.get("coder") is None
    assert b.per_suite_quality.get("math") == 2.5


def test_negative_quality_rejected(tmp_path):
    p = _write(tmp_path, "quality: -1.0\nper_suite_quality: {}\n")
    b = Baseline.load(p)
    assert b.quality == Baseline().quality


def test_valid_baseline_loads_unchanged(tmp_path):
    p = _write(
        tmp_path,
        "quality: 1.16\nspeed: 12.7\nreliability: 0.9\n"
        "per_suite_quality:\n  math: 2.5\n",
    )
    b = Baseline.load(p)
    assert b.quality == 1.16
    assert b.per_suite_quality.get("math") == 2.5


def test_none_per_suite_preserved(tmp_path):
    # "not yet populated" suites are null and must stay None (gate skips them).
    p = _write(tmp_path, "quality: 1.16\nper_suite_quality:\n  coder: null\n")
    b = Baseline.load(p)
    assert b.per_suite_quality.get("coder") is None


def test_save_writes_back_to_source_path_not_default(tmp_path):
    """A baseline loaded from a custom path must save() back to THAT path, never the
    production DEFAULT_BASELINE_PATH. Regression for 2026-05-31: update_baseline() on a
    test/tmp-configured gate wrote quality=2.9 to the real orchestration/autopilot_baseline.yaml
    (source_path was not remembered), gate-locking the live loop."""
    import safety_gate as sg
    custom = tmp_path / "my_baseline.yaml"
    custom.write_text("quality: 1.16\nper_suite_quality: {}\n")
    b = Baseline.load(custom)
    assert b.source_path == custom
    b.quality = 2.5
    b.save()  # no explicit path → must go to source_path, NOT DEFAULT_BASELINE_PATH
    assert "2.5" in custom.read_text()
    # production default must be untouched by this save
    assert not (sg.DEFAULT_BASELINE_PATH.exists() and "2.5" in sg.DEFAULT_BASELINE_PATH.read_text())
