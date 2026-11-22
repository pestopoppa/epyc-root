"""Rule d structural form: declaration is authoritative, digit-free gate ids, scoped prose scan.
Fixtures are the REAL boxes AutoKernel reported (tests/lint/fixtures/rule_d_real_boxes.json, copied from handoffs/active
2026-11-22); every one of them failed rule d before this change."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts' / 'handoffs'))
import task_lint as T  # noqa: E402

REAL = json.loads((Path(__file__).parent / 'fixtures' / 'rule_d_real_boxes.json').read_text(encoding='utf-8'))


def d(text):
    return 'd' in T.score2(text, 0)['fails']


def test_real_boxes_not_flagged():
    assert len(REAL) >= 20
    for k, v in REAL.items():
        assert not d(v['text']), k


def test_declared_boxes_satisfied_by_structure():
    for k in ('DTREE-ATTN-NP', 'SL-4-LC'):
        assert not d(REAL[k]['text']), k


BASE = "- [ ] **Y** [non-inference] Wire the exporter after the new scheduler lands. done when: exporter runs"


def test_digit_free_gate_id():
    assert not d(BASE + "\n      · gate: AK-SERVING-LONGCTX-DECODE-ONLY")
    assert T.L1.GATE_LINE_OK("x\n      · gate: AK-SERVING-LONGCTX-DECODE-ONLY")
    assert not d("- [ ] **Y** [non-inference] Wire the exporter after AK-SERVING-LONGCTX-DECODE-ONLY lands. done when: ok")


def test_class_field_declares():
    assert not d(BASE + "\n      · class: operator-decision")


def test_notes_and_rule_lines_not_scanned():
    assert not d(BASE.split(' after ')[0] + ". done when: ok\n  - 2026-11-20 (x) wait until the scheduler lands; requires the registry first.")
    assert not d("- [ ] **Y** [non-inference] Do the thing. done when: ok\n      · rule: only if the gain is large; after the rebuild completes")


def test_true_prereqs_without_declaration_still_fail():
    for t in (
        "- [ ] **Y** [non-inference] Wire the exporter after the new scheduler lands. done when: ok",
        "- [ ] **Y** [non-inference] Port it once the v11 kernel is promoted. done when: ok",
        "- [ ] **Y** [non-inference] Requires the registry rebuild first. done when: ok",
        "- [ ] **Y** [non-inference] Only if validated on the 27B, port it. done when: ok",
        "- [ ] **Y** [non-inference] Do the work.\n  Blocked by the drafter retrain; run when the retrain lands. done when: ok",
    ):
        assert d(t), t


def test_count_and_rule_prose_without_declaration():
    for t in (
        "- [ ] **Y** [non-inference] Each expert's weights are streamed exactly once per launch. done when: ok",
        "- [ ] **Y** [non-inference] Keep it only if gain improves by at least 3% in 4 of 5 pairs. done when: ok",
        "- [ ] **Y** [non-inference] Ship when it requires >= break-even on the sweep. done when: ok",
        "- [ ] **Y** [non-inference] Acceptance state is reset after a mid-draft rejection. done when: ok",
        "- [ ] **Y** [non-inference] Implement only if the operator authorizes the session. done when: ok",
        "- [ ] **Y** [non-inference] Dependent work requires the normal campaign authorization. done when: ok",
    ):
        assert not d(t), t
