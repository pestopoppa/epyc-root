"""EV-12 unit tests: execution-free patch verifier + schema alignment."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.verification import (  # noqa: E402
    FAIL,
    INCONCLUSIVE,
    PASS,
    PatchParseError,
    VerdictResult,
    parse_unified_diff,
    verify_patch,
)

SCHEMA_PATH = ROOT / "orchestration" / "verification_report.schema.json"


# ── fixtures (all patches are self-contained unified diffs) ───────────────

CLEAN_PATCH = (
    "--- a/mod.py\n"
    "+++ b/mod.py\n"
    "@@ -1,2 +1,2 @@\n"
    " def foo():\n"
    "-    return 1\n"
    "+    return 2\n"
)

NON_APPLYING_PATCH = (
    "--- a/mod.py\n"
    "+++ b/mod.py\n"
    "@@ -1,2 +1,2 @@\n"
    " def foo():\n"
    "-    return 999\n"
    "+    return 2\n"
)

SYNTAX_ERROR_PATCH = (
    "--- a/bad.py\n"
    "+++ b/bad.py\n"
    "@@ -1,1 +1,2 @@\n"
    " x = 1\n"
    "+def (:\n"
)

NEW_FILE_PATCH = (
    "new file mode 100644\n"
    "--- /dev/null\n"
    "+++ b/newmod.py\n"
    "@@ -0,0 +1,2 @@\n"
    "+def g():\n"
    "+    return 7\n"
)

UNRESOLVED_IMPORT_PATCH = (
    "--- a/imp.py\n"
    "+++ b/imp.py\n"
    "@@ -1,1 +1,2 @@\n"
    " x = 1\n"
    "+import nonexistent_xyz_pkg_9999\n"
)

MALFORMED_PATCH = "this is not a diff at all\nrandom prose line\n"

BASE = {"mod.py": "def foo():\n    return 1\n", "bad.py": "x = 1\n", "imp.py": "x = 1\n"}


def _check(result: VerdictResult, check_id: str):
    return next((c for c in result.checks if c.check_id == check_id), None)


# ── clean / passing ──────────────────────────────────────────────────────


def test_clean_patch_passes():
    r = verify_patch(CLEAN_PATCH, BASE, run_lint=False, use_git=False)
    assert r.is_pass
    assert r.verdict == PASS
    assert _check(r, "hunk_context").outcome == PASS
    assert _check(r, "syntax").outcome == PASS
    assert r.failing_check is None


def test_new_file_patch_passes():
    r = verify_patch(NEW_FILE_PATCH, {}, run_lint=False, use_git=False)
    assert r.is_pass
    assert _check(r, "syntax").outcome == PASS


# ── non-applying (hunk-context mismatch) → FAIL + certificate ─────────────


def test_non_applying_patch_fails_with_certificate():
    r = verify_patch(NON_APPLYING_PATCH, BASE, run_lint=False, use_git=False)
    assert r.is_fail
    hc = _check(r, "hunk_context")
    assert hc.outcome == FAIL
    assert hc.certificate is not None
    assert hc.certificate.type == "diff"
    assert hc.certificate.location.startswith("mod.py:")
    # syntax must NOT be a required signal when the patch did not apply.
    syn = _check(r, "syntax")
    assert syn.outcome == INCONCLUSIVE
    assert syn.required is False


# ── syntax error in resulting file → FAIL + certificate ───────────────────


def test_syntax_error_patch_fails_with_certificate():
    r = verify_patch(SYNTAX_ERROR_PATCH, BASE, run_lint=False, use_git=False)
    assert r.is_fail
    syn = _check(r, "syntax")
    assert syn.outcome == FAIL
    assert syn.certificate is not None
    assert syn.certificate.type == "stack_trace"
    assert "bad.py" in (syn.certificate.location or "")


# ── malformed / empty ─────────────────────────────────────────────────────


def test_malformed_patch_fails_with_certificate():
    r = verify_patch(MALFORMED_PATCH, BASE, run_lint=False, use_git=False)
    assert r.is_fail
    pp = _check(r, "patch_parse")
    assert pp.outcome == FAIL
    assert pp.certificate is not None
    assert pp.certificate.type == "diff"


def test_empty_patch_is_inconclusive():
    r = verify_patch("", BASE, run_lint=False, use_git=False)
    assert r.is_inconclusive
    assert _check(r, "patch_parse").inconclusive_reason


def test_whitespace_only_patch_is_inconclusive():
    r = verify_patch("   \n  \n", BASE, run_lint=False, use_git=False)
    assert r.is_inconclusive


def test_parse_raises_on_garbage():
    with pytest.raises(PatchParseError):
        parse_unified_diff("not a diff, no headers, has content")


# ── base unresolvable → INCONCLUSIVE ──────────────────────────────────────


def test_unresolvable_base_is_inconclusive(tmp_path):
    missing = tmp_path / "does_not_exist"
    r = verify_patch(CLEAN_PATCH, str(missing), run_lint=False, use_git=False)
    assert r.is_inconclusive
    assert _check(r, "base_resolution").outcome == INCONCLUSIVE


def test_modify_absent_file_fails():
    # mod.py present in a mapping that lacks it -> context can't match.
    r = verify_patch(CLEAN_PATCH, {"other.py": "x=1\n"}, run_lint=False, use_git=False)
    assert r.is_fail
    assert _check(r, "hunk_context").outcome == FAIL


# ── advisory import resolution never gates the verdict ────────────────────


def test_unresolved_import_is_advisory_only():
    r = verify_patch(UNRESOLVED_IMPORT_PATCH, BASE, run_lint=False, use_git=False)
    # compile() never imports, so an unknown module is syntactically fine.
    assert r.is_pass
    ir = _check(r, "import_resolution")
    assert ir.outcome == INCONCLUSIVE
    assert ir.required is False
    assert any("nonexistent_xyz_pkg_9999" in w for w in ir.warnings)


# ── schema alignment ──────────────────────────────────────────────────────


def test_to_report_conforms_to_verification_report_schema():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema = pytest.importorskip("jsonschema")
    for patch in (CLEAN_PATCH, NON_APPLYING_PATCH, SYNTAX_ERROR_PATCH, MALFORMED_PATCH):
        report = verify_patch(patch, BASE, run_lint=False, use_git=False).to_report()
        jsonschema.validate(report, schema)  # raises on nonconformance


def test_to_report_structural_shape():
    report = verify_patch(NON_APPLYING_PATCH, BASE, run_lint=False, use_git=False).to_report()
    assert report["schema_version"] == "1.0.0"
    assert report["report_id"]
    assert report["summary"]["conclusive_verdict"] == FAIL
    assert len(report["checks"]) >= 1
    # every FAIL check carries a certificate (schema invariant)
    for c in report["checks"]:
        if c["outcome"] == "fail":
            assert "certificate" in c
        if c["outcome"] == "inconclusive":
            assert "inconclusive_reason" in c


def test_to_check_single_signal_for_eval_tower_hook():
    r = verify_patch(NON_APPLYING_PATCH, BASE, run_lint=False, use_git=False)
    single = r.to_check("patch_verifier")
    assert single["check_id"] == "patch_verifier"
    assert single["kind"] == "gate"
    assert single["outcome"] == FAIL
    assert single["certificate"]["type"] == "diff"

    passing = verify_patch(CLEAN_PATCH, BASE, run_lint=False, use_git=False).to_check()
    assert passing["outcome"] == PASS
    assert "certificate" not in passing


def test_report_id_and_candidate_ref_passthrough():
    r = verify_patch(
        CLEAN_PATCH, BASE, run_lint=False, use_git=False,
        report_id="rid-1", candidate_ref="pkg-42",
    )
    assert r.report_id == "rid-1"
    rep = r.to_report()
    assert rep["report_id"] == "rid-1"
    assert rep["candidate_ref"] == "pkg-42"


# ── git apply --check path (subprocess; no execution of patched code) ─────


def _git_available() -> bool:
    try:
        return subprocess.run(
            ["git", "--version"], capture_output=True, timeout=10
        ).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


@pytest.mark.skipif(not _git_available(), reason="git not available")
def test_git_apply_check_pass_on_real_repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "mod.py").write_text("def foo():\n    return 1\n", encoding="utf-8")
    r = verify_patch(CLEAN_PATCH, str(tmp_path), run_lint=False, use_git=True)
    gac = _check(r, "git_apply_check")
    assert gac is not None
    assert gac.outcome == PASS
    assert r.is_pass


@pytest.mark.skipif(not _git_available(), reason="git not available")
def test_git_apply_check_fail_on_real_repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "mod.py").write_text("def foo():\n    return 1\n", encoding="utf-8")
    r = verify_patch(NON_APPLYING_PATCH, str(tmp_path), run_lint=False, use_git=True)
    gac = _check(r, "git_apply_check")
    assert gac is not None
    assert gac.outcome == FAIL
    assert gac.certificate is not None
    assert r.is_fail


# --------------------------------------------------------------------------- #
# CJ-8 — `inconclusive_reason` is a CLOSED cause code, not prose
# --------------------------------------------------------------------------- #
_CJ8_CAUSES = {
    "absent", "empty", "unparsed", "no_reference", "unsupported",
    "abstained", "checker_error", "timeout", "skipped", "insufficient_coverage",
}


def test_every_inconclusive_check_emits_a_closed_cause_code():
    """`verification_report.schema.json` closed this enum at 8b740065 and this
    module still wrote free text, so EVERY report containing an inconclusive
    check failed schema validation outright. The prose is preserved in
    `errors`; the code is what the schema reads."""
    from src.verification.patch_verifier import verify_patch

    scenarios = {
        "empty patch": ("", {"mod.py": "def f():\n    return 1\n"}),
        "unresolvable base": (
            "--- a/mod.py\n+++ b/mod.py\n@@ -1,2 +1,2 @@\n def f():\n-    return 1\n+    return 2\n",
            "/no/such/tree",
        ),
        "non-applying patch": (
            "--- a/mod.py\n+++ b/mod.py\n@@ -1,2 +1,2 @@\n def f():\n-    return 99\n+    return 2\n",
            {"mod.py": "def f():\n    return 1\n"},
        ),
    }
    seen_inconclusive = 0
    for label, (patch, base) in scenarios.items():
        result = verify_patch(patch, base)
        for check in (c.to_dict() for c in result.checks):
            if check["outcome"] != "inconclusive":
                continue
            seen_inconclusive += 1
            assert check["inconclusive_reason"] in _CJ8_CAUSES, (
                f"{label}/{check['check_id']}: "
                f"{check['inconclusive_reason']!r} is prose, not a cause code"
            )
            # The sentence is preserved, not discarded.
            assert check.get("errors"), f"{label}: the human reason was dropped"
    # Anti-vacuity: if no scenario produced an inconclusive check the loop above
    # would assert nothing at all.
    assert seen_inconclusive >= 3


def test_rolled_up_check_carries_a_cause_code_too():
    from src.verification.patch_verifier import verify_patch

    rolled = verify_patch("", {"mod.py": "def f():\n    return 1\n"}).to_check("gate")
    assert rolled["outcome"] == "inconclusive"
    assert rolled["inconclusive_reason"] == "empty"
    assert any("empty patch" in e for e in rolled["errors"])

    # Mutation guard: a DECIDED rollup carries no inconclusive_reason at all.
    clean = verify_patch(
        "--- a/mod.py\n+++ b/mod.py\n@@ -1,2 +1,2 @@\n def f():\n-    return 1\n+    return 2\n",
        {"mod.py": "def f():\n    return 1\n"},
    ).to_check("gate")
    assert clean["outcome"] == "pass"
    assert "inconclusive_reason" not in clean
