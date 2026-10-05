"""Guard: stale 0-3-scale baseline strings must not leak into planner prompts.

The corrupt 9.900 baseline (see test_baseline_scale_guard.py) left ~719 historical
journal failure_analysis / self_criticism strings reading "… vs baseline 9.900".
The planner ingests recent self_criticism as context and mis-cited 9.900 as a
current fact (trial 188). scrub_legacy_scale_text() redacts any field carrying an
impossible (>3.0) baseline/per-suite value so a corrected value is never re-surfaced.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "autopilot"))

from experiment_journal import (  # noqa: E402
    has_legacy_scale_failure_analysis,
    scrub_legacy_scale_text,
)

_STALE = (
    "What went wrong: Quality regression: 0.000 vs baseline 9.900 (-100.0%); "
    "Suite 'coder' regression: -9.900"
)
_CLEAN = "What went wrong: Quality regression: 1.050 vs baseline 1.160 (-9.5%)"


def test_detects_overscale_baseline():
    assert has_legacy_scale_failure_analysis(_STALE)
    assert not has_legacy_scale_failure_analysis(_CLEAN)


def test_scrub_redacts_stale_baseline():
    out = scrub_legacy_scale_text(_STALE)
    assert "9.900" not in out
    assert "legacy-scale" in out


def test_scrub_passes_clean_text_unchanged():
    assert scrub_legacy_scale_text(_CLEAN) == _CLEAN


def test_scrub_empty_is_safe():
    assert scrub_legacy_scale_text("") == ""
