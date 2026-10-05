"""Durability guard for baseline persistence (audit item A6).

Two failure modes are covered:

1. Torn writes — a crash mid-``save()`` used to truncate the YAML in place
   (``path.write_text`` truncates before it writes). ``Baseline.save`` and
   autopilot's ``_write_baseline_yaml_tiers`` now route through
   ``safety_gate._atomic_write_text`` (tmp + fsync + os.replace), so a partial
   file can never be observed.

2. Non-actionable startup crashes — a corrupt/empty/malformed baseline used to
   surface as an ``AttributeError`` (``None.get``) or a raw ``ParserError`` from
   deep inside ``SafetyGate.__init__``. ``Baseline.load`` now raises
   ``BaselineCorruptError`` with the offending path + remediation, and coerces
   out-of-domain speed/cost/reliability/quality scalars to safe defaults instead
   of letting a ``null``/string value blow up ``check()`` later.

Every file here lives under ``tmp_path``; the production
``orchestration/autopilot_baseline.yaml`` (and ``DEFAULT_BASELINE_PATH``) is
never read or written.
"""

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "autopilot"))

from safety_gate import (  # noqa: E402
    Baseline,
    BaselineCorruptError,
    _atomic_write_text,
)


def _write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "autopilot_baseline.yaml"
    p.write_text(body)
    return p


def test_save_is_atomic_and_versioned(tmp_path):
    path = tmp_path / "baseline.yaml"
    Baseline(quality=2.4, speed=15.0, cost=0.25, reliability=0.85).save(path)

    data = yaml.safe_load(path.read_text())
    assert isinstance(data, dict)
    assert data["schema_version"] == 1
    # No temp residue left behind by the atomic write.
    assert list(tmp_path.glob("*.tmp.*")) == []


def test_round_trip(tmp_path):
    path = tmp_path / "baseline.yaml"
    # quality kept well under the Pareto archive max so the (unrelated) load-side
    # archive-max guard does not coerce it — this test is about durability, not the
    # scale guard exercised in test_baseline_scale_guard.py.
    original = Baseline(
        quality=1.5,
        speed=15.5,
        cost=0.25,
        reliability=0.85,
        frontdoor_speed=12.0,
        per_suite_quality={"math": 2.5},
    )
    original.save(path)
    loaded = Baseline.load(path)

    # source_path is compare=False, so equality reflects the persisted fields.
    assert loaded == original
    assert loaded.quality == 1.5
    assert loaded.speed == 15.5
    assert loaded.cost == 0.25
    assert loaded.reliability == 0.85
    assert loaded.frontdoor_speed == 12.0
    assert loaded.per_suite_quality == {"math": 2.5}
    assert loaded.source_path == path  # remembered so save() cannot clobber DEFAULT


def test_empty_file_raises_actionable(tmp_path):
    path = _write(tmp_path, "")
    with pytest.raises(BaselineCorruptError) as exc:
        Baseline.load(path)
    msg = str(exc.value)
    assert str(path) in msg
    assert "checkpoint --production-best" in msg


def test_malformed_yaml_raises(tmp_path):
    path = _write(tmp_path, "{{{:not yaml")
    # Must be a BaselineCorruptError, NOT a raw yaml ParserError / AttributeError.
    with pytest.raises(BaselineCorruptError):
        Baseline.load(path)


def test_null_speed_falls_back(tmp_path):
    path = _write(
        tmp_path,
        "quality: 1.16\n"
        "speed: null\n"
        "frontdoor_speed: -5\n"
        'cost: "abc"\n'
        "reliability: 0.9\n"
        "per_suite_quality: {}\n",
    )
    b = Baseline.load(path)  # must not raise
    assert b.speed == 10.0
    assert b.frontdoor_speed == 10.0
    assert b.cost == 0.5


def test_string_quality_falls_back(tmp_path):
    path = _write(
        tmp_path,
        'quality: "abc"\nreliability: 0.9\nper_suite_quality: {}\n',
    )
    b = Baseline.load(path)  # must not raise TypeError
    assert b.quality == Baseline().quality


def test_missing_quality_key_warns_loudly_but_loads(caplog, tmp_path):
    """RC-12: a baseline file that never names a quality must not silently
    inherit the legacy calibration number — loud, with the same value."""
    path = _write(
        tmp_path,
        "reliability: 0.9\nper_suite_quality: {}\nbaselines_by_tier:\n  1: 1.82\n",
    )
    with caplog.at_level("WARNING"):
        b = Baseline.load(path)
    assert b.quality == Baseline().quality  # legacy fallback value, unchanged
    assert b.baselines_by_tier == {1: 1.82}
    assert any("no quality source" in rec.message for rec in caplog.records)
    assert str(path) in "\n".join(rec.message for rec in caplog.records)


def test_string_reliability_falls_back(tmp_path):
    path = _write(
        tmp_path,
        'quality: 1.16\nreliability: "high"\nper_suite_quality: {}\n',
    )
    b = Baseline.load(path)  # must not raise TypeError
    assert b.reliability == Baseline().reliability


def test_tier_writer_atomic(tmp_path):
    """autopilot leg: `_write_baseline_yaml_tiers` routes both writes through
    `_atomic_write_text`.

    Chosen approach: a direct call. Importing `autopilot` wholesale is cheap
    (~0.5s, no server side effects), so we exercise the real function rather
    than only monkeypatching. Covers BOTH replaced writes: the read-modify-write
    branch (path already exists) and the fresh-file branch (path absent).
    """
    import autopilot  # noqa: E402

    baseline = Baseline(quality=2.4, speed=15.0, cost=0.25, reliability=0.85)

    # Fresh-file branch (the yaml.safe_dump write).
    fresh = tmp_path / "fresh_baseline.yaml"
    autopilot._write_baseline_yaml_tiers(fresh, baseline)
    assert isinstance(yaml.safe_load(fresh.read_text()), dict)

    # Read-modify-write branch (existing file).
    existing = tmp_path / "existing_baseline.yaml"
    existing.write_text("quality: 1.16\n")
    autopilot._write_baseline_yaml_tiers(existing, baseline)
    assert isinstance(yaml.safe_load(existing.read_text()), dict)

    # Neither branch may leave temp residue.
    assert list(tmp_path.glob("*.tmp.*")) == []


def test_atomic_write_helper_no_residue(tmp_path):
    """The shared helper writes the target and leaves no temp file behind."""
    path = tmp_path / "sub" / "out.txt"  # parent does not exist yet
    _atomic_write_text(path, "hello world\n")
    assert path.read_text() == "hello world\n"
    assert list(path.parent.glob("*.tmp.*")) == []
