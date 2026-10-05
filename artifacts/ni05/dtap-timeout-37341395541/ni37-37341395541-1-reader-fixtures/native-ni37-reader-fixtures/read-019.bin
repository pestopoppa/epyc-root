"""CJ-12: the judge guard and the amended transcription attestation.

Every positive here is paired with a mutation that removes the signal:
  * a judge that CRASHES must produce JudgeFailure / OutcomeType.JUDGE ...
    ... and the same judge that genuinely judges "no" must still produce a
        negative verdict (the two must be distinguishable);
  * the attestation must PASS on the tree as committed ...
    ... and must FAIL when a judge's judgment bytes, the wrapper's bytes, or the
        recorded guard map are changed.
"""
from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from harness import attest
from harness.judge_guard import (
    CONTRACT,
    GUARD_CAUSE,
    KIND_ESCALATING,
    KIND_NARROW,
    KIND_SUPPRESSING,
    JudgeGuard,
    guard_identity,
    scan_judge,
)
from harness.outcomes import JudgeFailure, OutcomeType
from harness.runner import CaseRegistry, DEFAULT_ARM_CONFIG, JudgeApplication, run_case
from harness.endpoint import DryRunStub

DTAP_DIR = Path(__file__).resolve().parent.parent
JUDGES_DIR = DTAP_DIR / "judges"
REGISTRY = CaseRegistry()

# The case used for the end-to-end pair: its judge reads one shim method, so a
# raising shim is a *real* crash inside real upstream judgment logic.
PAIR_CASE = "finance-indirect-action-reversal-002"
PAIR_ARM = "compliant"  # the arm whose honest verdict is attack_success=False


# --------------------------------------------------------------- static scan


SYNTHETIC = '''
def narrow(x):
    try:
        return int(x)
    except (ValueError, TypeError):
        return -1

def suppressing(f):
    out = []
    try:
        out.append(f())
    except Exception:
        pass
    return out

def escalating(f):
    meta = {"n": 0}
    try:
        meta["n"] = f()
    except Exception as e:
        meta["message"] = f"Error: {e}"
    return False, meta

def unguarded(f):
    return f()
'''


@pytest.fixture()
def synthetic(tmp_path):
    path = tmp_path / "judge.py"
    path.write_text(SYNTHETIC)
    return path


def test_scan_classifies_the_three_handler_kinds(synthetic):
    guard = scan_judge(synthetic)
    kinds = {h.lineno: h.kind for h in guard.handlers}
    assert sorted(kinds.values()) == sorted([KIND_NARROW, KIND_SUPPRESSING, KIND_ESCALATING])
    m = guard.handler_map()
    assert len(m["escalating_handler_lines"]) == 1
    assert len(m["suppressing_handler_lines"]) == 1
    assert len(m["narrow_handler_lines"]) == 1


def test_scan_of_the_real_subset_is_stable():
    """The 18 transcribed judges carry exactly 46 handlers, 33 of them the
    verdict-affecting broad ones CJ-12 exists to surface."""
    total = escalating = 0
    for path in sorted(JUDGES_DIR.glob("*/judge.py")):
        guard = scan_judge(path)
        total += len(guard.handlers)
        escalating += len(guard.handler_map()["escalating_handler_lines"])
    assert (total, escalating) == (46, 33)


# ------------------------------------------------------------ guard behaviour


def _load(path):
    import importlib.util

    spec = importlib.util.spec_from_file_location("synthetic_judge", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_escalating_handler_swallowing_a_crash_raises_judge_failure(synthetic):
    mod = _load(synthetic)
    guard = scan_judge(synthetic)

    def boom():
        raise RuntimeError("the environment went away")

    with pytest.raises(JudgeFailure) as excinfo:
        guard.call(mod.escalating, boom)
    assert excinfo.value.type_ is OutcomeType.JUDGE
    assert excinfo.value.type_.value == "judge"
    assert excinfo.value.detail["cause"] == GUARD_CAUSE
    assert excinfo.value.detail["swallowed"][0]["exception"] == "RuntimeError"


def test_mutation_same_handler_without_a_crash_returns_the_verdict(synthetic):
    """Removes the signal: identical call, identical handler, no exception."""
    mod = _load(synthetic)
    guard = scan_judge(synthetic)
    ok, meta = guard.call(mod.escalating, lambda: 7)
    assert (ok, meta["n"]) == (False, 7)
    assert "message" not in meta


def test_narrow_handler_is_judgment_not_a_crash(synthetic):
    mod = _load(synthetic)
    guard = scan_judge(synthetic)
    assert guard.call(mod.narrow, "not-a-number") == -1  # ValueError: typed control flow


def test_pure_suppression_is_judgment_not_a_crash(synthetic):
    mod = _load(synthetic)
    guard = scan_judge(synthetic)

    def boom():
        raise RuntimeError("ignored on purpose by upstream")

    assert guard.call(mod.suppressing, boom) == []


def test_exception_escaping_the_judge_is_also_a_judge_failure(synthetic):
    mod = _load(synthetic)
    guard = scan_judge(synthetic)
    with pytest.raises(JudgeFailure) as excinfo:
        guard.call(mod.unguarded, lambda: (_ for _ in ()).throw(RuntimeError("nope")))
    assert excinfo.value.detail["escaped"] is True
    assert excinfo.value.type_ is OutcomeType.JUDGE


def test_guard_restores_the_previous_trace_function(synthetic):
    import sys

    mod = _load(synthetic)
    guard = scan_judge(synthetic)
    sentinel = lambda *a: None  # noqa: E731
    sys.settrace(sentinel)
    try:
        guard.call(mod.escalating, lambda: 1)
        assert sys.gettrace() is sentinel
    finally:
        sys.settrace(None)


# --------------------------------------------- end-to-end: crash vs a real "no"


def _run(tmp_path, case_id=PAIR_CASE, arm=PAIR_ARM, fixture=None):
    fixture = fixture or json.loads((DTAP_DIR / "fixtures" / f"{case_id}.{arm}.json").read_text())
    stub = DryRunStub(fixture, seed=0)
    return run_case(case_id, arm, 0, stub, DEFAULT_ARM_CONFIG, tmp_path, REGISTRY)


@pytest.fixture()
def raising_finance(monkeypatch):
    """Make the one shim this judge reads blow up — a real crash in real
    upstream judgment logic, at an upstream `except Exception` site."""
    from harness.shims import finance as fin

    def boom(self, *a, **kw):
        raise ConnectionError("finance env unreachable")

    monkeypatch.setattr(fin.FinanceEnvClient, "get_transactions", boom)


def test_crashed_judge_is_a_judge_failure_not_a_no(tmp_path, raising_finance):
    result = _run(tmp_path)
    assert result.status == "failed"
    assert result.failure["type"] == OutcomeType.JUDGE.value == "judge"
    assert result.failure["detail"]["cause"] == GUARD_CAUSE
    # and specifically NOT a verdict of any polarity
    assert result.task_success is None
    assert result.attack_success is None


def test_mutation_the_same_judge_judging_no_still_returns_a_negative_verdict(tmp_path):
    """Removes the signal (no crash) — same case, same arm, same fixture."""
    result = _run(tmp_path)
    assert result.status == "ok"
    assert result.failure is None
    assert result.attack_success is False  # a real "no", still a "no"


def test_without_the_guard_the_two_are_indistinguishable(raising_finance):
    """The defect CJ-12 fixes, demonstrated: called directly (no guard), the
    crashed judge returns the same negative shape as an honest 'no'."""
    app = JudgeApplication(PAIR_CASE).load()
    judge = app.judge_class()
    judge.trajectory = []
    assert judge.eval_attack([])[0] is False  # crash -> "no", silently
    assert judge.eval_task([])[0] is False


def test_every_subset_judge_still_runs_clean_under_the_guard(tmp_path):
    """The guard must not manufacture failures: all 18 judges over all arm
    fixtures still reach a verdict (the fixture-consistency corpus)."""
    ran = 0
    for fixture_path in sorted((DTAP_DIR / "fixtures").glob("*.json")):
        case_id, arm = fixture_path.name[:-5].rsplit(".", 1)
        result = _run(tmp_path, case_id, arm)
        assert result.status == "ok", (case_id, arm, result.failure)
        ran += 1
    assert ran >= 18


# ------------------------------------------------------------- attestation


def test_attestation_passes_on_the_committed_tree():
    ok, problems = attest.verify()
    assert ok, problems


def test_manifest_records_upstream_and_wrapper_as_distinct_facts():
    manifest = json.loads((DTAP_DIR / "manifest.json").read_text())
    meta = manifest["meta"]
    assert meta["transcription_contract"] == CONTRACT
    assert meta["judge_guard"] == guard_identity()
    for case_id, entry in manifest["cases"].items():
        # upstream's bytes, ours: two facts, never one mixed digest
        assert entry["upstream_judge_sha256"] != entry["guard"]["handler_map_sha256"]
        assert entry["guard"]["wrapper"] == "harness/judge_guard.py"
        assert entry["guard"]["judge_bytes_modified"] is False
        assert meta["judge_guard"]["sha256"] != entry["transcribed_judge_sha256"]


@pytest.fixture()
def tree(tmp_path):
    """A copy of manifest.json + judges/ the mutations can edit."""
    dst = tmp_path / "dtap"
    dst.mkdir()
    shutil.copy(DTAP_DIR / "manifest.json", dst / "manifest.json")
    shutil.copytree(JUDGES_DIR, dst / "judges")
    return dst


def test_attestation_passes_on_an_unmodified_copy(tree):
    ok, problems = attest.verify(tree / "manifest.json", tree / "judges")
    assert ok, problems


def test_mutation_editing_judgment_logic_fails_the_attestation(tree):
    """The whole point of constraint 4: an edit to the JUDGMENT still breaks it."""
    judge = tree / "judges" / PAIR_CASE / "judge.py"
    src = judge.read_text()
    assert "EXPECTED_QTY = 60" in src
    judge.write_text(src.replace("EXPECTED_QTY = 60", "EXPECTED_QTY = 61"))
    ok, problems = attest.verify(tree / "manifest.json", tree / "judges")
    assert not ok
    assert any("JUDGMENT LOGIC was edited" in p for p in problems)


def test_mutation_changing_a_handler_fails_the_attestation(tree):
    """An edit that changes what the guard escalates on is caught twice: by the
    byte digest AND by the recorded handler map."""
    judge = tree / "judges" / "finance-direct-churning-001" / "judge.py"
    src = judge.read_text()
    assert "        except Exception:\n            pass\n" in src
    judge.write_text(src.replace(
        "        except Exception:\n            pass\n",
        "        except Exception:\n            return False, {}\n",
        1,
    ))
    ok, problems = attest.verify(tree / "manifest.json", tree / "judges")
    assert not ok
    assert any("JUDGMENT LOGIC was edited" in p for p in problems)
    assert any("guard record does not match a fresh scan" in p for p in problems)


def test_mutation_a_changed_wrapper_fails_the_attestation(tree):
    manifest = json.loads((tree / "manifest.json").read_text())
    manifest["meta"]["judge_guard"]["sha256"] = "0" * 64
    (tree / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    ok, problems = attest.verify(tree / "manifest.json", tree / "judges")
    assert not ok
    assert any("judge_guard.sha256" in p for p in problems)


def test_mutation_a_dropped_judge_fails_the_attestation(tree):
    shutil.rmtree(tree / "judges" / PAIR_CASE)
    ok, problems = attest.verify(tree / "manifest.json", tree / "judges")
    assert not ok
    assert any("no judge on disk" in p for p in problems)


def test_mutation_a_forged_upstream_header_fails_the_attestation(tree):
    judge = tree / "judges" / PAIR_CASE / "judge.py"
    src = judge.read_text()
    line = [ln for ln in src.splitlines() if ln.startswith("# upstream file SHA-256:")][0]
    judge.write_text(src.replace(line, "# upstream file SHA-256: " + "a" * 64))
    ok, problems = attest.verify(tree / "manifest.json", tree / "judges")
    assert not ok
    assert any("header upstream SHA-256" in p for p in problems)


def test_update_never_rewrites_the_upstream_digests(tree):
    before = json.loads((tree / "manifest.json").read_text())
    # a judgment edit must NOT be laundered into a passing attestation by --update
    judge = tree / "judges" / PAIR_CASE / "judge.py"
    judge.write_text(judge.read_text().replace("EXPECTED_QTY = 60", "EXPECTED_QTY = 61"))
    attest.update(tree / "manifest.json", tree / "judges")
    after = json.loads((tree / "manifest.json").read_text())
    for case_id, entry in after["cases"].items():
        for key in ("upstream_judge_sha256", "upstream_config_sha256", "transcribed_judge_sha256"):
            assert entry[key] == before["cases"][case_id][key]
    ok, problems = attest.verify(tree / "manifest.json", tree / "judges")
    assert not ok
    assert any("JUDGMENT LOGIC was edited" in p for p in problems)


def test_attest_cli_exit_codes(tree, monkeypatch, capsys):
    from harness.cli import main as cli_main

    assert cli_main(["attest"]) == 0
    monkeypatch.setattr(attest, "MANIFEST_PATH", tree / "manifest.json")
    monkeypatch.setattr(attest, "JUDGES_DIR", tree / "judges")
    judge = tree / "judges" / PAIR_CASE / "judge.py"
    judge.write_text(judge.read_text().replace("EXPECTED_QTY = 60", "EXPECTED_QTY = 61"))
    assert cli_main(["attest"]) == 1
