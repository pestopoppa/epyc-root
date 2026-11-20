"""C2 (handoff standard Stage C, AK audit B13): done-when parsed and checked at tick time."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import done_when as D  # noqa: E402

AUDIT = "keep record has gpu_build_receipt.proven and recipe registered before build"


def test_audit_fixture_production_kernel_refused_loop_built_accepted():
    assert D.parse(AUDIT)["kind"] == "artifact_class"
    r, why = D.check(AUDIT, {"paths": ["kernels/production/gpu"], "verdict": "KEEP"})
    assert r == "fail" and "never loop-built" in why
    assert D.check(AUDIT, {"paths": ["artifacts/ak/champion-c14/gpu_build_receipt.json"]})[0] == "ok"
    assert D.check(AUDIT, {"paths": ["docs/x.md"]})[0] == "fail"


def test_cmd_needs_recorded_rc():
    dw = "`pytest scripts/handoffs/tests/test_x.py` passes"
    assert D.parse(dw) == {"kind": "cmd", "cmd": "pytest scripts/handoffs/tests/test_x.py", "text": dw}
    assert D.check(dw, {})[0] == "unchecked"
    assert D.check(dw, {"commands": [{"cmd": "pytest scripts/handoffs/tests/test_x.py", "rc": 1}]})[0] == "fail"
    assert D.check(dw, {"commands": [{"cmd": "pytest  scripts/handoffs/tests/test_x.py", "rc": 0}]})[0] == "ok"


def test_file_and_field(tmp_path):
    (tmp_path / "r.json").write_text(json.dumps({"a": {"proven": True}, "b": False}))
    assert D.check("file: r.json#a.proven", {}, str(tmp_path))[0] == "ok"
    assert D.check("file: r.json#b", {}, str(tmp_path))[0] == "fail"
    assert D.check("file: missing.json", {}, str(tmp_path))[0] == "fail"
    assert D.parse("the report `out/r.json#a.proven` exists")["kind"] == "file"


def test_verdict_and_row_pass():
    assert D.check("verdict: PASS|KEEP", {"verdict": "KEEP 1.2x"})[0] == "ok"
    assert D.check("verdict: PASS", {"verdict": "FAIL"})[0] == "fail"
    assert D.check("verdict: PASS", {})[0] == "fail"
    assert D.parse("row PASS on the smoke")["kind"] == "verdict"


def test_free_text_is_unchecked():
    assert D.check("the owner is happy with the wording", {})[0] == "unchecked"
    assert D.check(None, {})[0] == "unchecked"


def test_check_box_reads_own_block():
    lines = ["- [ ] **A-1** [non-inference] do it", "      · done when: verdict: PASS", "- [ ] **A-2** x"]
    assert D.check_box(lines, 0, {"verdict": "PASS"})[:2] == ("ok", "verdict 'PASS'")
    assert D.check_box(lines, 2, {})[0] == "unchecked"
