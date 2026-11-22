"""Rule d (prose prerequisite) false-positive guards and `gate:` acceptance. AutoKernel report 2026-11-20."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts' / 'handoffs'))
import task_lint as T  # noqa: E402


def d(text):
    return 'd' in T.score2(text, 0)['fails']


NEG = [  # the four real first lines (trimmed to the spans that tripped d) must NOT fail d
    "- [ ] **RKA-A3B48-D-REMEASURE** [inference] Re-measure A3B CPU MTP draft length after the 2026-11-18 inversion analysis "
    "(research/deep-dives/a3b.md: bimodal). stop-on-answer after round 4: RECOMMEND_D2 iff gain >= 5%; stop-on-futility: < 3 valid rounds.",
    "- [ ] **GDN-VERIFY-BASE** [inference] Measure the GDN op. Stop with NO-GO if the op is < 3% of verify ms; "
    "only if >= 3%, author the fused variant and screen it; gate-class = futility-only.",
    "- [ ] **AKU-06l4** [non-inference] candidate feedback consumes the v2 prerequisite settlement and its enrollment reference",
    "- [ ] **AK-TRIM-OR-SPLIT-SMALL-20261119 — trim files.** [code, refactor] Tick a sub-item when its file is at or under its cap, or when a split lands:\n  - a.py · b.py",
    "- [ ] **X-NOTE-1** [non-inference] note: approval exists; no longer gated on it. done when: x",
]
POS = [  # real prose prerequisites must still fail d
    "- [ ] **Y** [non-inference] Wire the exporter after the new scheduler lands. done when: exporter runs",
    "- [ ] **Y** [non-inference] Do this once the v11 kernel is promoted. done when: ok",
    "- [ ] **Y** [non-inference] Requires the registry rebuild first. done when: ok",
    "- [ ] **Y** [non-inference] Only if validated on the 27B, port it. done when: ok",
    "- [ ] **Y** [non-inference] Start after 2099-01-01 data refresh completes? depends on upstream. done when: ok",
    "- [ ] **Y** [inference] Blocked by the drafter retrain; run when the retrain lands. done when: ok",
]


def test_negative_fixtures():
    for t in NEG:
        assert not d(t), t


def test_positive_fixtures():
    for t in POS:
        assert d(t), t


def test_gate_continuation_satisfies_d():
    base = "- [ ] **Y** [non-inference] Wire the exporter after the new scheduler lands. done when: exporter runs"
    assert d(base)
    assert not d(base + "\n      · gate: INF-48#rocm-verify-profile-backend, EVL-47")
    assert not d(base + "\n      · gate: AK-LOOP-3")
    assert d(base + "\n      · gate: none")
    assert d(base + "\n      · gate: the scheduler")
